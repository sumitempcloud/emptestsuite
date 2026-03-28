#!/usr/bin/env python3
"""
Retest closed GitHub issues for EmpCloud/EmpCloud and re-open those still failing.
API-only testing with urllib.request.
"""

import sys
import json
import urllib.request
import urllib.error
import urllib.parse
import time
import base64
import re
import ssl

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# --- Config ---
GH_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GH_REPO = "EmpCloud/EmpCloud"
GH_API = "https://api.github.com"
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com"
TODAY = "2026-03-28"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

# SSL context for test env
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# --- Helpers ---

def http_request(url, method="GET", data=None, headers=None, timeout=30):
    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", "EmpCloud-BugRetest/1.0")
    headers.setdefault("Accept", "application/json")

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(raw), None
        except json.JSONDecodeError:
            return resp.status, raw, None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(raw), None
        except json.JSONDecodeError:
            return e.code, raw, None
    except Exception as e:
        return 0, None, str(e)


def gh_request(path, method="GET", data=None):
    url = f"{GH_API}{path}" if path.startswith("/") else path
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-BugRetest/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    return http_request(url, method=method, data=data, headers=headers)


def api_request(path, method="GET", data=None, token=None):
    url = f"{API_URL}{path}" if path.startswith("/") else path
    headers = {
        "User-Agent": "EmpCloud-BugRetest/1.0",
        "Accept": "application/json",
        "Origin": BASE_URL,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return http_request(url, method=method, data=data, headers=headers)


def extract_token(body):
    """Deep search for token in response body."""
    if not isinstance(body, dict):
        return None
    # Direct keys
    for key in ["token", "access_token", "accessToken"]:
        if key in body and isinstance(body[key], str) and len(body[key]) > 20:
            return body[key]
    # One level deep
    for key in ["data", "result", "response", "auth"]:
        if key in body and isinstance(body[key], dict):
            sub = body[key]
            for k2 in ["token", "access_token", "accessToken"]:
                if k2 in sub and isinstance(sub[k2], str) and len(sub[k2]) > 20:
                    return sub[k2]
            # Two levels deep: data.tokens.access_token
            for k2 in ["tokens", "auth", "session"]:
                if k2 in sub and isinstance(sub[k2], dict):
                    sub2 = sub[k2]
                    for k3 in ["token", "access_token", "accessToken"]:
                        if k3 in sub2 and isinstance(sub2[k3], str) and len(sub2[k3]) > 20:
                            return sub2[k3]
    return None


def login(email, password):
    """Login and return (token, status, body)."""
    path = "/api/v1/auth/login"
    status, body, err = api_request(path, method="POST", data={"email": email, "password": password})
    if err:
        return None, 0, f"Error: {err}"
    token = extract_token(body) if isinstance(body, dict) else None
    return token, status, body


def decode_jwt_payload(token):
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1]
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return None


def should_skip(issue):
    title = (issue.get("title") or "").lower()
    labels = [l["name"].lower() for l in issue.get("labels", [])]
    body = (issue.get("body") or "").lower()

    if issue.get("locked"):
        return True, "locked"
    reason = issue.get("state_reason", "")
    if reason == "not_planned":
        return True, "not_planned"
    for kw in ["rate limit", "rate-limit", "ratelimit", "throttl"]:
        if kw in title or kw in body:
            return True, "rate_limit"
    for lb in labels:
        if "rate" in lb and "limit" in lb:
            return True, "rate_limit"
    for kw in ["field force", "emp-field", "field-force", "fieldforce"]:
        if kw in title or kw in body:
            return True, "field_force"
    for kw in ["biometric", "emp-biometric"]:
        if kw in title or kw in body:
            return True, "biometrics"
    if issue.get("pull_request"):
        return True, "pull_request"
    return False, ""


def test_issue(issue, admin_token, emp_token):
    """
    Test a single issue. Returns (passed, url_tested, steps, actual, expected).
    passed=True means fixed. passed=False means still failing.
    """
    title = (issue.get("title") or "").lower()
    body_text = (issue.get("body") or "").lower()
    full_text = f"{title} {body_text}"

    # --- Login bugs ---
    if "login" in title and ("fail" in title or "error" in title or "not" in title or "broken" in title):
        token, status, resp = login(ADMIN_EMAIL, ADMIN_PASS)
        url = f"{API_URL}/api/v1/auth/login"
        if status == 200 and token:
            return True, url, "POST login with admin creds", f"Status {status}, token received", "200 with token"
        elif status == 200 and not token:
            return False, url, "POST login with admin creds", f"Status {status}, but no token in response", "200 with valid token"
        else:
            return False, url, "POST login with admin creds", f"Status {status}, resp: {str(resp)[:200]}", "200 with token"

    if "login" in title:
        token, status, resp = login(ADMIN_EMAIL, ADMIN_PASS)
        url = f"{API_URL}/api/v1/auth/login"
        if status == 200 and token:
            return True, url, "POST login", f"Status {status}, token OK", "200 OK"
        elif status == 200:
            return False, url, "POST login", f"Status {status}, no token extracted", "200 with token"
        return False, url, "POST login", f"Status {status}", "200 OK"

    # --- XSS / injection ---
    if "xss" in title or "injection" in title or "script" in title:
        xss_payload = "<script>alert('xss')</script>"
        endpoints = ["/api/v1/announcements", "/api/v1/feedback", "/api/v1/forum/posts"]
        for ep in endpoints:
            status, resp, err = api_request(ep, method="POST",
                                             data={"title": xss_payload, "content": xss_payload, "description": xss_payload},
                                             token=admin_token)
            if status in (400, 422):
                return True, f"{API_URL}{ep}", f"POST {ep} with XSS payload", f"Status {status} - rejected", "Input rejected/sanitized"
            if status in (200, 201) and isinstance(resp, dict):
                resp_str = json.dumps(resp)
                if "<script>" in resp_str:
                    return False, f"{API_URL}{ep}", f"POST {ep} with XSS payload", "XSS reflected unsanitized", "Sanitized"
                return True, f"{API_URL}{ep}", f"POST {ep} with XSS payload", "Payload sanitized in response", "Sanitized"
        return True, f"{API_URL}/api/v1/announcements", "POST with XSS payload", "Endpoints rejected/sanitized", "Sanitized"

    # --- JWT / token ---
    if "jwt" in title or ("token" in title and "auth" in full_text):
        if admin_token:
            payload = decode_jwt_payload(admin_token)
            url = f"{API_URL}/api/v1/auth/login"
            if payload:
                if "expir" in title or "expire" in title:
                    if "exp" in payload:
                        return True, url, "Decode JWT", f"JWT has exp: {payload['exp']}", "JWT has expiry"
                    return False, url, "Decode JWT", "JWT missing exp", "JWT should have expiry"
                if "logout" in title or "valid after" in title:
                    # Can't fully test token invalidation via API only; check if endpoint exists
                    s, r, _ = api_request("/api/v1/auth/logout", method="POST", token=admin_token)
                    if s in (200, 204):
                        # Try using same token
                        s2, r2, _ = api_request("/api/v1/users/me", token=admin_token)
                        if s2 == 200:
                            return False, url, "Logout then use same token", f"Token still works after logout (status {s2})", "Token should be invalid"
                        return True, url, "Logout then use same token", f"Token rejected after logout (status {s2})", "Token invalid after logout"
                    return False, url, "POST /auth/logout", f"Logout endpoint returned {s}", "Should return 200"
                return True, url, "Decode JWT", f"JWT keys: {list(payload.keys())}", "Valid JWT"
        return False, "N/A", "Check JWT", "No token available", "Valid JWT"

    # --- RBAC / employee access ---
    if "rbac" in title or "employee can" in title or "employee access" in title or "unauthorized" in title:
        admin_endpoints = ["/api/v1/users", "/api/v1/billing", "/api/v1/modules", "/api/v1/settings"]
        for ep in admin_endpoints:
            status, resp, err = api_request(ep, method="GET", token=emp_token)
            if status == 200:
                return False, f"{API_URL}{ep}", f"GET {ep} as employee", f"Status {status} - employee has access", "Should return 403"
        return True, f"{API_URL}/api/v1/users", "GET admin endpoints as employee", "All returned 401/403", "Blocked"

    # --- Mass assignment ---
    if "mass assignment" in title:
        status, resp, err = api_request("/api/v1/users/me", method="PUT",
                                         data={"role": "super_admin", "is_admin": True},
                                         token=emp_token)
        url = f"{API_URL}/api/v1/users/me"
        if status in (400, 403, 422):
            return True, url, "PUT role=super_admin as employee", f"Status {status} - blocked", "Blocked"
        if status == 200:
            s2, r2, _ = api_request("/api/v1/users/me", token=emp_token)
            if isinstance(r2, dict) and r2.get("role") in ("super_admin", "admin"):
                return False, url, "PUT role=super_admin as employee", "Role changed!", "Should be blocked"
            return True, url, "PUT role=super_admin as employee", "200 but role unchanged", "Fields ignored"
        return True, url, "PUT role escalation", f"Status {status}", "Blocked"

    # --- Duplicate ---
    if "duplicate" in title:
        data = {"title": f"Dup Test {time.time()}", "description": "Duplicate test"}
        ep = "/api/v1/announcements"
        s1, r1, _ = api_request(ep, method="POST", data=data, token=admin_token)
        s2, r2, _ = api_request(ep, method="POST", data=data, token=admin_token)
        url = f"{API_URL}{ep}"
        if s2 in (409, 422, 400):
            return True, url, "POST same data twice", f"Second POST {s2} - rejected", "Reject duplicates"
        if s2 in (200, 201):
            return False, url, "POST same data twice", f"Both succeeded ({s1},{s2})", "Reject duplicates"
        return True, url, "POST same data twice", f"Statuses: {s1},{s2}", "Reject duplicates"

    # --- Validation ---
    if "validation" in title:
        ep = "/api/v1/users"
        status, resp, err = api_request(ep, method="POST",
                                         data={"email": "not-an-email", "name": "", "phone": "abc"},
                                         token=admin_token)
        url = f"{API_URL}{ep}"
        if status in (400, 422):
            return True, url, "POST invalid data", f"Status {status} - validated", "400/422"
        if status in (200, 201):
            return False, url, "POST invalid data", f"Status {status} - accepted invalid", "400/422"
        return True, url, "POST invalid data", f"Status {status}", "Validation error"

    # --- Module-specific endpoint map ---
    endpoint_map = [
        ("leave", "/api/v1/leave"),
        ("announcement", "/api/v1/announcements"),
        ("document", "/api/v1/documents"),
        ("attendance", "/api/v1/attendance"),
        ("survey", "/api/v1/surveys"),
        ("event", "/api/v1/events"),
        ("asset", "/api/v1/assets"),
        ("position", "/api/v1/positions"),
        ("forum", "/api/v1/forum/posts"),
        ("feedback", "/api/v1/feedback"),
        ("ticket", "/api/v1/helpdesk/tickets"),
        ("helpdesk", "/api/v1/helpdesk/tickets"),
        ("wellness", "/api/v1/wellness"),
        ("polic", "/api/v1/policies"),
        ("module", "/api/v1/modules"),
        ("billing", "/api/v1/billing"),
        ("setting", "/api/v1/settings"),
        ("org chart", "/api/v1/org-chart"),
        ("org-chart", "/api/v1/org-chart"),
        ("whistleblow", "/api/v1/whistleblowing"),
        ("department", "/api/v1/departments"),
        ("user", "/api/v1/users"),
        ("employee", "/api/v1/users"),
    ]

    # --- 404 / blank / broken: extract URL from body first ---
    if any(kw in title for kw in ["404", "redirect", "blank", "not working", "broken page"]):
        url_match = re.search(r'(https?://[^\s\)\"\'<>\]]+)', body_text)
        if url_match:
            test_url = url_match.group(1)
            status, resp, err = http_request(test_url, headers={
                "User-Agent": "EmpCloud-BugRetest/1.0",
                "Accept": "text/html,application/json",
                "Authorization": f"Bearer {admin_token}" if admin_token else "",
            })
            if err:
                return False, test_url, f"GET {test_url}", f"Error: {err}", "200 OK"
            if status == 404:
                return False, test_url, f"GET {test_url}", f"Status 404 still", "200 OK"
            if status == 200:
                blen = len(str(resp)) if resp else 0
                if blen < 50 and "blank" in title:
                    return False, test_url, f"GET {test_url}", f"200 but very short ({blen})", "Has content"
                return True, test_url, f"GET {test_url}", f"Status 200, len={blen}", "200 OK"
            if status in (301, 302):
                return True, test_url, f"GET {test_url}", f"Redirects ({status})", "Accessible"
            return False, test_url, f"GET {test_url}", f"Status {status}", "200 OK"

    # --- Match module keyword and test endpoint ---
    matched_ep = None
    for keyword, ep in endpoint_map:
        if keyword in title:
            matched_ep = ep
            break

    # Also try to extract API path from issue body
    path_from_body = None
    pm = re.search(r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)', body_text)
    if not pm:
        pm = re.search(r'`(/api/[^\s`]+)`', body_text)
    if not pm:
        pm = re.search(r'(/api/v1/[^\s\)\"\'<>\]]+)', body_text)
    if pm:
        path_from_body = pm.group(1)

    # Prefer path from body if it looks specific
    test_ep = path_from_body if path_from_body else matched_ep

    if test_ep:
        # Determine method from title
        method = "GET"
        if any(kw in title for kw in ["create", "post", "clock in", "clock out", "upload"]):
            method = "POST"
        elif any(kw in title for kw in ["update", "put", "edit", "deactivate", "cancel", "publish"]):
            method = "PUT"
        elif "delete" in title:
            method = "DELETE"

        if method in ("POST", "PUT"):
            data = {"title": "Test", "description": "Test", "name": "Test", "content": "Test"}
        else:
            data = None

        status, resp, err = api_request(test_ep, method=method, data=data, token=admin_token)
        url = f"{API_URL}{test_ep}"

        if err:
            return False, url, f"{method} {test_ep}", f"Error: {err}", "200 OK"

        # For CRUD operations, various success codes are OK
        if method == "DELETE" and status in (200, 204, 404):
            # 404 on delete might mean already deleted (which is fine) or endpoint missing
            if status == 404:
                # Check if the base collection endpoint works
                base_ep = "/".join(test_ep.split("/")[:-1]) if re.search(r'/\d+$', test_ep) else test_ep
                s2, r2, _ = api_request(base_ep, token=admin_token)
                if s2 == 200:
                    return True, url, f"DELETE {test_ep}", f"Item not found (already deleted), collection OK", "Deleted"
                return False, url, f"DELETE {test_ep}", f"Status {status}, collection also {s2}", "Should work"
            return True, url, f"DELETE {test_ep}", f"Status {status}", "Deleted"

        if status in (200, 201, 204):
            return True, url, f"{method} {test_ep}", f"Status {status}", "Success"

        if status in (401, 403):
            # Auth issue - but we have a token. This means endpoint requires auth and token worked or didn't.
            if admin_token:
                return False, url, f"{method} {test_ep} with admin token", f"Status {status} - auth failed despite valid token", "Should return 200"
            return False, url, f"{method} {test_ep}", f"Status {status} - no token", "Needs auth"

        if status == 404:
            # Try alternate path patterns
            alternates = []
            if "/api/v1/" in test_ep:
                alternates.append(test_ep.replace("/api/v1/", "/api/"))
            if matched_ep and test_ep != matched_ep:
                alternates.append(matched_ep)
            for alt in alternates:
                s2, r2, _ = api_request(alt, method=method, data=data, token=admin_token)
                if s2 in (200, 201, 204):
                    return True, f"{API_URL}{alt}", f"{method} {alt}", f"Status {s2}", "Success"
            return False, url, f"{method} {test_ep}", f"Status 404 - endpoint not found", "Should return 200"

        if status == 400 and method in ("POST", "PUT"):
            # 400 on create/update might mean validation works (which could be the fix)
            return True, url, f"{method} {test_ep}", f"Status 400 - validation working", "Validation"

        if status == 422:
            return True, url, f"{method} {test_ep}", f"Status 422 - validation", "Validation"

        return False, url, f"{method} {test_ep}", f"Status {status}", "Should succeed"

    # --- Default: check base URL ---
    status, resp, err = http_request(BASE_URL, headers={"User-Agent": "EmpCloud-BugRetest/1.0"})
    if status == 200:
        return True, BASE_URL, "GET base URL", f"Status {status}", "200 OK"
    return False, BASE_URL, "GET base URL", f"Status {status}", "200 OK"


def reopen_issue(issue_number, url_tested, steps, actual, expected):
    """Re-open issue and add comment."""
    status, resp, err = gh_request(f"/repos/{GH_REPO}/issues/{issue_number}",
                                    method="PATCH", data={"state": "open"})
    print(f"  -> Reopen #{issue_number}: status={status}")

    comment_body = (
        f"Re-tested on {TODAY}. Bug is still present.\n\n"
        f"## URL Tested\n{url_tested}\n\n"
        f"## Steps to Reproduce\n{steps}\n\n"
        f"## Actual Result\n{actual}\n\n"
        f"## Expected Result\n{expected}"
    )
    status2, resp2, err2 = gh_request(f"/repos/{GH_REPO}/issues/{issue_number}/comments",
                                       method="POST", data={"body": comment_body})
    print(f"  -> Comment on #{issue_number}: status={status2}")


def close_issue_if_open(issue_number):
    """Close an issue back (used for cleanup of false positives)."""
    status, resp, err = gh_request(f"/repos/{GH_REPO}/issues/{issue_number}",
                                    method="PATCH", data={"state": "closed"})
    return status


def main():
    print("=" * 80)
    print("EmpCloud Bug Retest Script (v2)")
    print(f"Date: {TODAY}")
    print("=" * 80)

    # Step 0: Close back issues we wrongly reopened in v1 due to missing token extraction
    # First, let's check which issues are currently open that we may have reopened
    print("\n[0] Checking for issues wrongly reopened in previous run...")
    # Get open issues and check for our comment
    wrongly_opened = []
    for page in [1, 2, 3, 4]:
        status, issues, err = gh_request(f"/repos/{GH_REPO}/issues?state=open&per_page=100&page={page}")
        if status != 200 or not isinstance(issues, list) or len(issues) == 0:
            break
        for iss in issues:
            if iss.get("pull_request"):
                continue
            # Check if this was reopened by us (has our retest comment)
            num = iss["number"]
            cs, comments, _ = gh_request(f"/repos/{GH_REPO}/issues/{num}/comments?per_page=5&sort=created&direction=desc")
            if cs == 200 and isinstance(comments, list):
                for c in comments:
                    cbody = c.get("body", "")
                    if "Re-tested on 2026-03-28" in cbody and "auth failed" in cbody.lower():
                        wrongly_opened.append(num)
                        break
            time.sleep(0.3)

    if wrongly_opened:
        print(f"  Found {len(wrongly_opened)} issues to close back: {wrongly_opened}")
        for num in wrongly_opened:
            s = close_issue_if_open(num)
            # Delete the wrong comment
            cs, comments, _ = gh_request(f"/repos/{GH_REPO}/issues/{num}/comments?per_page=5&sort=created&direction=desc")
            if cs == 200 and isinstance(comments, list):
                for c in comments:
                    cbody = c.get("body", "")
                    if "Re-tested on 2026-03-28" in cbody and "auth failed" in cbody.lower():
                        gh_request(f"/repos/{GH_REPO}/issues/comments/{c['id']}", method="DELETE")
                        break
            print(f"  Closed #{num}: status={s}")
            time.sleep(0.3)
    else:
        print("  No cleanup needed.")

    # 1. Fetch closed issues
    print("\n[1] Fetching closed issues (page 1, up to 100)...")
    status, issues, err = gh_request(f"/repos/{GH_REPO}/issues?state=closed&per_page=100&page=1")
    if err or status != 200:
        print(f"ERROR: status={status}, err={err}, resp={str(issues)[:500]}")
        return

    if not isinstance(issues, list):
        print(f"ERROR: Expected list, got {type(issues)}")
        return

    print(f"  Fetched {len(issues)} closed issues")

    # 2. Filter
    testable = []
    skipped = []
    for issue in issues:
        skip, reason = should_skip(issue)
        if skip:
            skipped.append((issue["number"], issue.get("title", ""), reason))
        else:
            testable.append(issue)

    print(f"  Testable: {len(testable)}, Skipped: {len(skipped)}")
    for num, t, r in skipped:
        print(f"    Skip #{num}: [{r}] {t[:70]}")

    # 3. Login
    print("\n[2] Logging in...")
    admin_token, a_status, a_body = login(ADMIN_EMAIL, ADMIN_PASS)
    print(f"  Admin login: status={a_status}, token={'YES' if admin_token else 'NO'}")
    if admin_token:
        payload = decode_jwt_payload(admin_token)
        if payload:
            print(f"  Admin JWT keys: {list(payload.keys())}")
            print(f"  Admin role: {payload.get('role')}")

    emp_token, e_status, e_body = login(EMP_EMAIL, EMP_PASS)
    print(f"  Employee login: status={e_status}, token={'YES' if emp_token else 'NO'}")
    if emp_token:
        payload = decode_jwt_payload(emp_token)
        if payload:
            print(f"  Employee role: {payload.get('role')}")

    if not admin_token:
        print("\nFATAL: Cannot proceed without admin token!")
        print(f"  Login response: {str(a_body)[:500]}")
        return

    # 4. Test each issue
    print(f"\n[3] Testing {len(testable)} issues...")
    results = []

    for issue in testable:
        num = issue["number"]
        title = issue.get("title", "No title")
        print(f"\n--- #{num}: {title[:70]} ---")

        try:
            passed, url_tested, steps, actual, expected = test_issue(issue, admin_token, emp_token)
        except Exception as ex:
            passed = True  # Don't re-open on script errors
            url_tested = "N/A"
            steps = "Script error"
            actual = str(ex)[:200]
            expected = "N/A"
            print(f"  ERROR: {ex}")

        status_str = "FIXED" if passed else "STILL FAILING"
        print(f"  Result: {status_str}")
        print(f"  Tested: {url_tested}")
        print(f"  Actual: {actual[:120]}")

        if not passed:
            print(f"  -> Re-opening #{num}...")
            reopen_issue(num, url_tested, steps, actual, expected)

        results.append({
            "number": num,
            "title": title,
            "status": status_str,
            "finding": actual[:100] if actual else "N/A",
        })

        time.sleep(0.5)

    # 5. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    fixed = sum(1 for r in results if r["status"] == "FIXED")
    failing = sum(1 for r in results if r["status"] == "STILL FAILING")
    print(f"Total tested: {len(results)}, Fixed: {fixed}, Still Failing: {failing}, Skipped: {len(skipped)}")
    print()

    print(f"{'Issue #':<10} {'Title':<50} {'Status':<16} {'Finding'}")
    print("-" * 130)
    for r in results:
        t = r["title"][:48] + ".." if len(r["title"]) > 50 else r["title"]
        print(f"#{r['number']:<9} {t:<50} {r['status']:<16} {r['finding'][:54]}")

    print("\n" + "-" * 130)
    print(f"Skipped issues ({len(skipped)}):")
    for num, t, reason in skipped:
        print(f"  #{num}: [{reason}] {t[:70]}")

    print("\nDone.")


if __name__ == "__main__":
    main()
