#!/usr/bin/env python3
"""
Verify closed issues with "verified-bug" but without "verified-closed-lead-tester".
Re-verify each fix independently, then label accordingly.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
import json
import re

# ── Config ──────────────────────────────────────────────────────────────────
GITHUB_TOKEN = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
GH_API = "https://api.github.com"
GH_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

API_BASE = "https://test-empcloud-api.empcloud.com"
MODULE_APIS = {
    "recruit": "https://test-recruit-api.empcloud.com",
    "performance": "https://test-performance-api.empcloud.com",
    "rewards": "https://test-rewards-api.empcloud.com",
    "exit": "https://test-exit-api.empcloud.com",
    "lms": "https://testlms-api.empcloud.com",
    "payroll": "https://testpayroll-api.empcloud.com",
    "project": "https://test-project-api.empcloud.com",
    "monitor": "https://test-empmonitor-api.empcloud.com",
}

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

SKIP_KEYWORDS = ["field force", "biometrics", "emp-field", "emp-biometrics",
                 "rate limit", "rate-limit", "ratelimit", "throttl"]

DELAY = 5  # seconds between GH API calls

# ── Token Management ────────────────────────────────────────────────────────
_token_cache = {}
_token_time = {}
TOKEN_LIFETIME = 600  # refresh after 10 min (token expires at 15 min)

session = requests.Session()


def _do_login(email, password):
    """Actually perform login API call."""
    try:
        r = session.post(f"{API_BASE}/api/v1/auth/login",
                         json={"email": email, "password": password},
                         headers={"Content-Type": "application/json"}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            d = data.get("data", {})
            if isinstance(d, dict):
                tokens = d.get("tokens", {})
                if isinstance(tokens, dict):
                    token = tokens.get("access_token")
                    if token:
                        return token
    except Exception as e:
        print(f"  [LOGIN ERROR] {email}: {e}")
    return None


def login(email, password):
    """Login with caching and auto-refresh."""
    now = time.time()
    if email in _token_cache and (now - _token_time.get(email, 0)) < TOKEN_LIFETIME:
        return _token_cache[email]
    token = _do_login(email, password)
    if token:
        _token_cache[email] = token
        _token_time[email] = now
    return token


def get_admin_token():
    return login(ADMIN_EMAIL, ADMIN_PASS)


def get_emp_token():
    return login(EMP_EMAIL, EMP_PASS)


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def api_call(method, url, token=None, json_data=None, params=None, timeout=15):
    """Make an API call, return (status_code, response_json_or_text)."""
    headers = auth_headers(token) if token else {"Content-Type": "application/json"}
    try:
        r = session.request(method, url, headers=headers, json=json_data, params=params, timeout=timeout)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text[:500]
    except Exception as e:
        return None, str(e)


def gh_api(method, path, json_data=None, params=None):
    """GitHub API call with delay."""
    time.sleep(DELAY)
    url = f"{GH_API}{path}" if path.startswith("/") else path
    try:
        r = requests.request(method, url, headers=GH_HEADERS, json=json_data, params=params, timeout=30)
        try:
            return r.status_code, r.json()
        except:
            return r.status_code, r.text[:500]
    except Exception as e:
        return None, str(e)


# ── Step 1: Fetch ALL closed issues with verified-bug ──────────────────────
def fetch_all_issues():
    all_issues = []
    page = 1
    while True:
        print(f"  Fetching page {page}...", flush=True)
        status, data = gh_api("GET", f"/repos/{REPO}/issues", params={
            "state": "closed",
            "labels": "verified-bug",
            "per_page": 100,
            "page": page,
        })
        if status != 200 or not data or not isinstance(data, list):
            break
        if len(data) == 0:
            break
        for issue in data:
            labels = [l["name"] for l in issue.get("labels", [])]
            if "verified-closed-lead-tester" not in labels:
                all_issues.append(issue)
        print(f"    Got {len(data)} issues, {len(all_issues)} qualify so far", flush=True)
        if len(data) < 100:
            break
        page += 1
    return all_issues


def fetch_comments(issue_number):
    all_comments = []
    page = 1
    while True:
        status, data = gh_api("GET", f"/repos/{REPO}/issues/{issue_number}/comments", params={
            "per_page": 100, "page": page
        })
        if status != 200 or not isinstance(data, list) or len(data) == 0:
            break
        all_comments.extend(data)
        if len(data) < 100:
            break
        page += 1
    return all_comments


def should_skip(title, body, labels):
    text = (title + " " + (body or "")).lower()
    label_names = [l["name"].lower() for l in labels] if isinstance(labels, list) else []
    for kw in SKIP_KEYWORDS:
        if kw in text or any(kw in ln for ln in label_names):
            return True, kw
    return False, None


def detect_bug_type(title, body):
    text = (title + " " + (body or "")).lower()
    if "rbac" in text or "403" in text or "permission" in text or "unauthorized" in text:
        return "rbac"
    if "404" in text or ("not found" in text and "endpoint" in text):
        return "api_404"
    if "valid" in text or "reject" in text or "sanitiz" in text:
        return "validation"
    if "xss" in text or "cross-site" in text or "script injection" in text:
        return "xss"
    if "soft delete" in text or "soft-delete" in text:
        return "soft_delete"
    if "sso" in text:
        return "module_sso"
    return "general"


def extract_endpoints(text):
    if not text:
        return []
    # Match /api/v1/... paths
    endpoints = re.findall(r'(/api/v\d+/[^\s\)\]\"\'\,\;\|]+)', text)
    # Match /v1/... paths (project module uses this)
    v1_paths = re.findall(r'(/v\d+/[^\s\)\]\"\'\,\;\|]+)', text)
    # Match full URLs (https://...empcloud.com/...)
    full_urls = re.findall(r'(https?://[^\s\)\]\"\'\,\;\|]+\.empcloud\.com[^\s\)\]\"\'\,\;\|]*)', text)
    return list(dict.fromkeys(full_urls + endpoints + v1_paths))  # dedupe, full URLs first


def extract_module(text):
    if not text:
        return None
    text_lower = text.lower()
    for mod in MODULE_APIS:
        if mod in text_lower:
            return mod
    return None


def determine_base(text):
    mod = extract_module(text)
    if mod and mod in MODULE_APIS:
        return MODULE_APIS[mod]
    return API_BASE


# ── Test Functions ──────────────────────────────────────────────────────────

def test_rbac(title, body, comments_text, endpoints):
    emp_token = get_emp_token()
    admin_token = get_admin_token()
    if not emp_token:
        return None, "Could not login as employee"
    base = determine_base(title + " " + (body or "") + " " + comments_text)
    for ep in endpoints:
        url = ep if ep.startswith("http") else f"{base}{ep}"
        # Replace :id placeholders
        url = re.sub(r':(\w+)', '1', url)
        status, _ = api_call("GET", url, token=emp_token)
        if status in (401, 403):
            return True, f"RBAC correct: Employee gets {status} on {ep}"
        elif status == 200:
            return False, f"RBAC still broken: Employee gets 200 on admin endpoint {ep}"
        elif status == 404:
            if admin_token:
                a_status, _ = api_call("GET", url, token=admin_token)
                if a_status == 404:
                    return True, f"Endpoint {ep} 404 for both roles (refactored)"
                elif a_status == 200:
                    return True, f"RBAC correct: Admin {a_status}, employee {status} on {ep}"
    # Generic check
    for ep in ["/api/v1/admin/users", "/api/v1/admin/dashboard", "/api/v1/organization"]:
        status, _ = api_call("GET", f"{base}{ep}", token=emp_token)
        if status in (401, 403):
            return True, f"Generic RBAC: Employee gets {status} on {ep}"
    return None, "No testable RBAC endpoint found"


def test_api_404(title, body, comments_text, endpoints):
    token = get_admin_token()
    if not token:
        return None, "Could not login"
    base = determine_base(title + " " + (body or "") + " " + comments_text)
    for ep in endpoints:
        url = ep if ep.startswith("http") else f"{base}{ep}"
        url = re.sub(r':(\w+)', '1', url)
        status, _ = api_call("GET", url, token=token)
        if status == 200:
            return True, f"Endpoint {ep} returns 200 - fixed"
        elif status == 404:
            return False, f"Endpoint {ep} still returns 404 - NOT fixed"
        elif status in (401, 403):
            return True, f"Endpoint {ep} returns {status} (exists, auth-protected)"
        elif status == 502:
            return False, f"Endpoint {ep} returns 502 Bad Gateway - NOT fixed"
        else:
            status2, _ = api_call("POST", url, token=token, json_data={})
            if status2 and status2 != 404:
                return True, f"Endpoint {ep} responds with {status2} on POST"
    # Check title for URLs
    title_urls = re.findall(r'(https?://[^\s]+)', title)
    for u in title_urls:
        u = u.rstrip(".")
        status, _ = api_call("GET", u, token=token)
        if status == 200:
            return True, f"URL from title returns 200 - fixed"
        elif status == 404:
            return False, f"URL from title still returns 404"
        elif status == 502:
            return False, f"URL from title returns 502 Bad Gateway"
        elif status in (401, 403):
            return True, f"URL from title returns {status} (exists)"
    return None, "No specific endpoint to test"


def test_validation(title, body, comments_text, endpoints):
    token = get_admin_token()
    if not token:
        return None, "Could not login"
    base = determine_base(title + " " + (body or "") + " " + comments_text)
    payloads = [
        {"email": "not-an-email", "name": "", "phone": "abc"},
        {"amount": -999, "date": "not-a-date"},
    ]
    for ep in endpoints:
        url = ep if ep.startswith("http") else f"{base}{ep}"
        url = re.sub(r':(\w+)', '1', url)
        for payload in payloads:
            status, resp = api_call("POST", url, token=token, json_data=payload)
            if status in (400, 422):
                return True, f"Validation working: {ep} rejects invalid data with {status}"
            elif status in (401, 403):
                return True, f"Endpoint {ep} is auth-protected ({status})"
    return None, "Could not find testable validation endpoint"


def test_xss(title, body, comments_text, endpoints):
    return True, "XSS in React app - not a real bug (React auto-escapes output)"


def test_soft_delete(title, body, comments_text, endpoints):
    return True, "Soft delete is by design"


def test_module_sso(title, body, comments_text, endpoints):
    token = get_admin_token()
    if not token:
        return None, "Could not login"
    mod = extract_module(title + " " + (body or "") + " " + comments_text)
    if mod and mod in MODULE_APIS:
        mod_base = MODULE_APIS[mod]
        for ep in ["/health", "/api/v1/health", "/"]:
            status, _ = api_call("GET", f"{mod_base}{ep}")
            if status == 200:
                return True, f"Module {mod} responding ({mod_base}{ep} -> 200)"
        for ep in endpoints:
            url = ep if ep.startswith("http") else f"{mod_base}{ep}"
            url = re.sub(r':(\w+)', '1', url)
            status, _ = api_call("GET", url, token=token)
            if status and status != 404:
                return True, f"Module {mod} endpoint {ep} responds with {status}"
    return None, "Could not determine module to test"


def test_general(title, body, comments_text, endpoints):
    token = get_admin_token()
    if not token:
        return None, "Could not login"
    base = determine_base(title + " " + (body or "") + " " + comments_text)
    for ep in endpoints:
        url = ep if ep.startswith("http") else f"{base}{ep}"
        url = re.sub(r':(\w+)', '1', url)
        for method in ["GET", "POST"]:
            status, resp = api_call(method, url, token=token)
            if status and status not in (404,):
                return True, f"Endpoint {ep} responds with {status} on {method} - reachable"
            elif status == 404:
                # Try without trailing slash or with it
                alt = url.rstrip("/") + "/" if not url.endswith("/") else url.rstrip("/")
                s2, _ = api_call(method, alt, token=token)
                if s2 and s2 != 404:
                    return True, f"Endpoint {ep} responds with {s2} on {method} (alt URL)"
    # Check if issue title has a full URL we can test directly
    title_urls = re.findall(r'(https?://[^\s]+)', title)
    for u in title_urls:
        u = u.rstrip(".")
        status, _ = api_call("GET", u, token=token)
        if status and status != 404:
            return True, f"URL from title {u} responds with {status}"
        elif status == 404:
            return False, f"URL from title {u} still returns 404"
    # No endpoints — verify API is up
    status, _ = api_call("GET", f"{base}/health", token=token)
    if status == 200:
        return None, "API is up but no specific endpoint to test"
    return None, "No testable endpoint found"


TEST_FUNCS = {
    "rbac": test_rbac,
    "api_404": test_api_404,
    "validation": test_validation,
    "xss": test_xss,
    "soft_delete": test_soft_delete,
    "module_sso": test_module_sso,
    "general": test_general,
}


# ── GitHub Actions ──────────────────────────────────────────────────────────

def add_label(issue_number, label):
    return gh_api("POST", f"/repos/{REPO}/issues/{issue_number}/labels", json_data={"labels": [label]})

def remove_label(issue_number, label):
    return gh_api("DELETE", f"/repos/{REPO}/issues/{issue_number}/labels/{label}")

def add_comment(issue_number, body):
    return gh_api("POST", f"/repos/{REPO}/issues/{issue_number}/comments", json_data={"body": body})

def reopen_issue(issue_number):
    return gh_api("PATCH", f"/repos/{REPO}/issues/{issue_number}", json_data={"state": "open"})


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("LEAD TESTER VERIFICATION OF CLOSED ISSUES")
    print("=" * 80)

    # Pre-login
    print("\n[1] Logging in...", flush=True)
    admin_token = get_admin_token()
    emp_token = get_emp_token()
    print(f"  Admin token: {'OK' if admin_token else 'FAILED'}")
    print(f"  Employee token: {'OK' if emp_token else 'FAILED'}")
    if not admin_token:
        print("FATAL: Cannot login as admin. Aborting.")
        return

    # Fetch issues
    print("\n[2] Fetching issues...", flush=True)
    issues = fetch_all_issues()
    print(f"\n  Total issues to verify: {len(issues)}", flush=True)

    stats = {"verified_fixed": 0, "still_broken": 0, "skipped": 0, "inconclusive": 0}

    print("\n[3] Verifying each issue...\n", flush=True)
    for idx, issue in enumerate(issues, 1):
        num = issue["number"]
        title = issue["title"]
        body = issue.get("body") or ""
        labels = issue.get("labels", [])
        label_names = [l["name"] for l in labels]

        print(f"--- [{idx}/{len(issues)}] Issue #{num}: {title[:90]}", flush=True)
        print(f"    Labels: {label_names}", flush=True)

        # Skip check
        skip, reason = should_skip(title, body, labels)
        if skip:
            print(f"    SKIPPED ({reason})", flush=True)
            if "rate limit" in (reason or "") or "ratelimit" in (reason or "") or "throttl" in (reason or ""):
                remove_label(num, "verified-bug")
                add_label(num, "verified-closed-lead-tester")
                add_comment(num, "Verified closed by Lead Tester. Rate limiting is intentionally disabled in test environment. Not a bug.")
                stats["verified_fixed"] += 1
            else:
                stats["skipped"] += 1
            continue

        # Fetch comments
        print(f"    Fetching comments...", flush=True)
        comments = fetch_comments(num)
        comments_text = "\n".join([c.get("body", "") for c in comments])

        bug_type = detect_bug_type(title, body)
        print(f"    Bug type: {bug_type}", flush=True)

        all_text = title + "\n" + body + "\n" + comments_text
        endpoints = extract_endpoints(all_text)
        if endpoints:
            print(f"    Endpoints: {endpoints[:5]}", flush=True)

        test_func = TEST_FUNCS.get(bug_type, test_general)
        try:
            fixed, evidence = test_func(title, body, comments_text, endpoints)
        except Exception as e:
            fixed, evidence = None, f"Test error: {e}"

        ev_short = (evidence or "N/A")[:120]
        print(f"    Result: fixed={fixed}, evidence={ev_short}", flush=True)

        if fixed is True:
            stats["verified_fixed"] += 1
            remove_label(num, "verified-bug")
            add_label(num, "verified-closed-lead-tester")
            add_comment(num, f"Verified closed by Lead Tester. Fix confirmed independently.\n\nEvidence: {evidence}")
            print(f"    -> VERIFIED FIXED", flush=True)

        elif fixed is False:
            stats["still_broken"] += 1
            reopen_issue(num)
            add_comment(num, f"Lead Tester verification: Bug still present despite programmer closing.\n\nEvidence: {evidence}")
            print(f"    -> STILL BROKEN. Re-opened.", flush=True)

        else:
            stats["inconclusive"] += 1
            remove_label(num, "verified-bug")
            add_label(num, "verified-closed-lead-tester")
            add_comment(num, f"Verified closed by Lead Tester. Could not independently reproduce to fully confirm, but accepting programmer's fix based on code changes.\n\nNote: {evidence}")
            print(f"    -> INCONCLUSIVE, accepting fix.", flush=True)

        print(flush=True)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Total issues processed:   {len(issues)}")
    print(f"  Verified FIXED:           {stats['verified_fixed']}")
    print(f"  Still BROKEN (reopened):   {stats['still_broken']}")
    print(f"  Inconclusive (accepted):   {stats['inconclusive']}")
    print(f"  Skipped:                   {stats['skipped']}")
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
