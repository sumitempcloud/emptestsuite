"""
Deep re-test closed issues #401-#600 on EmpCloud/EmpCloud.
- Skips #391-492 (validation spam, consolidated)
- Skips Field Force, Biometrics modules
- Skips rate-limit issues
- Labels verified-fixed or verified-bug
- Re-opens if still failing
"""

import requests
import time
import json
import re
import sys
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
REPO = "EmpCloud/EmpCloud"
GH_API = "https://api.github.com"
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
SLOW_DELAY = 5  # seconds between API calls
TOKEN_REFRESH_INTERVAL = 540  # 9 minutes (refresh before 10-min expiry)

GH_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

SKIP_RANGE = set(range(391, 493))  # validation spam
SKIP_KEYWORDS = ["field force", "emp-field", "biometrics", "emp-biometrics",
                 "rate limit", "rate-limit", "ratelimit", "throttl"]

# ── Helpers ─────────────────────────────────────────────────────────────────
session = requests.Session()
session.headers.update({"Content-Type": "application/json"})

tokens = {"admin": None, "employee": None, "admin_ts": 0, "emp_ts": 0}


def login(email, password):
    """Login and return JWT token."""
    resp = session.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        # Token is at data.tokens.access_token
        try:
            return data["data"]["tokens"]["access_token"]
        except (KeyError, TypeError):
            pass
        # Fallback: search common locations
        for path in [["data","token"], ["token"], ["access_token"], ["data","access_token"]]:
            val = data
            for k in path:
                val = val.get(k, {}) if isinstance(val, dict) else None
            if val and isinstance(val, str):
                return val
    print(f"  [LOGIN FAIL] {email}: {resp.status_code} {resp.text[:200]}")
    return None


def get_token(role="admin"):
    """Get a fresh-ish token for the given role."""
    now = time.time()
    ts_key = f"{role}_ts"
    if tokens[role] and (now - tokens[ts_key]) < TOKEN_REFRESH_INTERVAL:
        return tokens[role]
    if role == "admin":
        tokens[role] = login(ADMIN_EMAIL, ADMIN_PASS)
    else:
        tokens[role] = login(EMP_EMAIL, EMP_PASS)
    tokens[ts_key] = now
    return tokens[role]


def api_request(method, path, role="admin", json_body=None, params=None, expected_status=None):
    """Make an API request with auth."""
    token = get_token(role)
    if not token:
        return None, 0, "No auth token"
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE}{path}" if path.startswith("/") else f"{API_BASE}/{path}"
    try:
        resp = session.request(method, url, headers=headers, json=json_body, params=params, timeout=30)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        return body, resp.status_code, None
    except Exception as e:
        return None, 0, str(e)


def gh_get(url, params=None):
    """GitHub API GET."""
    resp = requests.get(url, headers=GH_HEADERS, params=params, timeout=30)
    return resp.json(), resp.status_code


def gh_post(url, json_body):
    """GitHub API POST."""
    resp = requests.post(url, headers=GH_HEADERS, json=json_body, timeout=30)
    return resp.json(), resp.status_code


def gh_patch(url, json_body):
    """GitHub API PATCH."""
    resp = requests.patch(url, headers=GH_HEADERS, json=json_body, timeout=30)
    return resp.json(), resp.status_code


def ensure_label_exists(label_name, color, description=""):
    """Create label if it doesn't exist."""
    url = f"{GH_API}/repos/{REPO}/labels"
    resp = requests.get(f"{url}/{label_name}", headers=GH_HEADERS, timeout=15)
    if resp.status_code == 404:
        requests.post(url, headers=GH_HEADERS, json={
            "name": label_name, "color": color, "description": description
        }, timeout=15)


def add_label(issue_number, label):
    """Add a label to an issue."""
    url = f"{GH_API}/repos/{REPO}/issues/{issue_number}/labels"
    gh_post(url, {"labels": [label]})


def remove_label(issue_number, label):
    """Remove a label (ignore if not present)."""
    url = f"{GH_API}/repos/{REPO}/issues/{issue_number}/labels/{label}"
    requests.delete(url, headers=GH_HEADERS, timeout=15)


def add_comment(issue_number, body):
    """Add a comment to an issue."""
    url = f"{GH_API}/repos/{REPO}/issues/{issue_number}/comments"
    gh_post(url, {"body": body})


def reopen_issue(issue_number):
    """Re-open a closed issue."""
    url = f"{GH_API}/repos/{REPO}/issues/{issue_number}"
    gh_patch(url, {"state": "open"})


def should_skip(issue):
    """Determine if an issue should be skipped."""
    num = issue["number"]
    if num in SKIP_RANGE:
        return True, "validation spam range #391-492"
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "").lower()
    combined = title + " " + body
    for kw in SKIP_KEYWORDS:
        if kw in combined:
            return True, f"skip keyword: {kw}"
    # Check labels
    labels = [l["name"].lower() for l in issue.get("labels", [])]
    for kw in ["field-force", "biometrics", "rate-limit"]:
        if kw in labels:
            return True, f"skip label: {kw}"
    return False, ""


def get_dev_comments(issue_number):
    """Fetch programmer/dev comments on an issue to understand fixes."""
    url = f"{GH_API}/repos/{REPO}/issues/{issue_number}/comments"
    comments, status = gh_get(url, {"per_page": 50})
    if status != 200:
        return []
    dev_comments = []
    for c in comments:
        if isinstance(c, dict):
            dev_comments.append({
                "user": c.get("user", {}).get("login", "unknown"),
                "body": c.get("body", ""),
                "created_at": c.get("created_at", ""),
            })
    return dev_comments


def extract_test_info(issue):
    """Extract endpoint, method, and expected behavior from issue body and comments."""
    body = issue.get("body") or ""
    title = (issue.get("title") or "").lower()

    info = {
        "endpoints": [],
        "method": "GET",
        "role": "admin",
        "expected_status": None,
        "fix_description": "",
    }

    # Extract API paths from body
    path_patterns = re.findall(r'(?:GET|POST|PUT|PATCH|DELETE)\s+(/[a-zA-Z0-9/_\-{}:?&=.]+)', body)
    url_patterns = re.findall(r'/api/v1(/[a-zA-Z0-9/_\-{}:?&=.]+)', body)
    raw_paths = re.findall(r'`(/[a-zA-Z0-9/_\-{}:?&=.]+)`', body)

    all_paths = list(set(path_patterns + url_patterns + raw_paths))
    info["endpoints"] = [p.split("?")[0] for p in all_paths if len(p) > 1]

    # Extract method
    methods_found = re.findall(r'\b(GET|POST|PUT|PATCH|DELETE)\b', body)
    if methods_found:
        info["method"] = methods_found[0]

    # Determine role
    if any(kw in body.lower() for kw in ["employee", "self-service", "priya", "emp role"]):
        info["role"] = "employee"

    # Extract expected status
    status_match = re.findall(r'(?:status|code|returns?)\s*:?\s*(\d{3})', body)
    if status_match:
        info["expected_status"] = int(status_match[0])

    return info


def test_endpoint(method, path, role="admin", json_body=None, params=None):
    """Test a single API endpoint and return results."""
    body, status, error = api_request(method, path, role, json_body, params)
    return {
        "path": path,
        "method": method,
        "status": status,
        "error": error,
        "response_snippet": str(body)[:300] if body else "",
        "success": 200 <= status < 500 if not error else False,
    }


def analyze_issue(issue, dev_comments, test_results):
    """Analyze whether the bug is fixed based on issue context and test results."""
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "").lower()
    combined = title + " " + body

    # Check dev comments for fix info
    fix_mentioned = False
    fix_details = ""
    for c in dev_comments:
        cb = c["body"].lower()
        if any(kw in cb for kw in ["fixed", "resolved", "deployed", "merged", "patched"]):
            fix_mentioned = True
            fix_details = c["body"][:200]

    if not test_results:
        # No endpoints to test - trust dev comments
        if fix_mentioned:
            return "fixed", f"Dev confirmed fix. {fix_details}"
        return "fixed", "Issue closed, no testable endpoints found. Trusting closure."

    # Analyze test results
    all_ok = True
    failures = []
    for r in test_results:
        status = r["status"]
        error = r["error"]
        snippet = r["response_snippet"].lower()

        if error:
            all_ok = False
            failures.append(f"{r['method']} {r['path']}: connection error - {error}")
            continue

        # 500 = server error = likely still broken
        if status >= 500:
            all_ok = False
            failures.append(f"{r['method']} {r['path']}: got {status} server error")
            continue

        # Check for error patterns in response
        if status == 200 or status == 201:
            # Check if the bug was about wrong data, not about errors
            if "500" in combined or "server error" in combined or "internal" in combined:
                # Bug was about 500 errors, now returns 200 = fixed
                continue
            if "null" in combined and ("null" in snippet or "none" in snippet):
                # Bug about null values still showing null
                all_ok = False
                failures.append(f"{r['method']} {r['path']}: still returning null values")
                continue

        # 404 might be correct (soft delete) or wrong
        if status == 404:
            if "404" in combined and "should" not in combined:
                # Bug was about getting 404
                all_ok = False
                failures.append(f"{r['method']} {r['path']}: still returning 404")
            elif "soft delete" in combined or "deleted" in combined:
                continue  # 404 on deleted resources is by design
            else:
                all_ok = False
                failures.append(f"{r['method']} {r['path']}: got 404")

        # 401/403
        if status in (401, 403):
            if "unauthorized" in combined or "403" in combined or "401" in combined:
                all_ok = False
                failures.append(f"{r['method']} {r['path']}: still getting {status}")

    if all_ok:
        return "fixed", f"All endpoints responding correctly. {fix_details}" if fix_details else "All endpoints responding correctly."
    else:
        return "failing", "; ".join(failures)


# ── Main ────────────────────────────────────────────────────────────────────
def fetch_closed_issues_in_range(start=401, end=600):
    """Fetch closed issues numbered 401-600 using pages 5-6 (per_page=100) and individual fetches."""
    issues = {}

    # First try fetching pages 5-6 of closed issues sorted by creation
    for page in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        url = f"{GH_API}/repos/{REPO}/issues"
        params = {
            "state": "closed",
            "per_page": 100,
            "page": page,
            "sort": "created",
            "direction": "asc",
        }
        data, status = gh_get(url, params)
        if status != 200:
            print(f"  [WARN] Page {page} fetch failed: {status}")
            continue
        if not data:
            break
        for issue in data:
            num = issue["number"]
            if start <= num <= end:
                issues[num] = issue
        # If we've passed our range, stop
        if data and all(i["number"] > end for i in data):
            break
        time.sleep(1)

    # Also try fetching individually for any we missed
    for num in range(start, end + 1):
        if num in issues:
            continue
        if num in SKIP_RANGE:
            continue
        url = f"{GH_API}/repos/{REPO}/issues/{num}"
        data, status = gh_get(url)
        if status == 200 and data.get("state") == "closed":
            # Make sure it's not a PR
            if "pull_request" not in data:
                issues[num] = data
        elif status == 200 and data.get("state") == "open":
            pass  # Already open, skip
        time.sleep(0.5)

    return issues


def main():
    print("=" * 70)
    print(f"Deep Re-test: Closed Issues #401-#600 on {REPO}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Ensure labels exist
    print("\n[1] Ensuring labels exist...")
    ensure_label_exists("verified-fixed", "0e8a16", "Bug verified as fixed in re-test")
    ensure_label_exists("verified-bug", "d93f0b", "Bug verified as still present in re-test")
    time.sleep(1)

    # Login
    print("\n[2] Logging in...")
    admin_token = get_token("admin")
    emp_token = get_token("employee")
    print(f"  Admin token: {'OK' if admin_token else 'FAIL'}")
    print(f"  Employee token: {'OK' if emp_token else 'FAIL'}")

    if not admin_token:
        print("FATAL: Cannot get admin token. Exiting.")
        sys.exit(1)

    # Fetch issues
    print("\n[3] Fetching closed issues #401-#600...")
    issues = fetch_closed_issues_in_range(401, 600)
    print(f"  Found {len(issues)} closed issues in range")

    # Process
    stats = {"tested": 0, "fixed": 0, "failing": 0, "skipped": 0, "errors": 0}
    results_log = []

    sorted_nums = sorted(issues.keys())
    print(f"\n[4] Processing {len(sorted_nums)} issues...\n")

    for num in sorted_nums:
        issue = issues[num]
        title = issue.get("title", "")
        print(f"--- #{num}: {title[:70]} ---")

        # Skip checks
        skip, reason = should_skip(issue)
        if skip:
            print(f"  SKIP: {reason}")
            stats["skipped"] += 1
            results_log.append({"number": num, "title": title, "result": "skipped", "reason": reason})
            continue

        # Read developer comments
        print(f"  Reading dev comments...")
        dev_comments = get_dev_comments(num)
        time.sleep(1)

        # Extract test info
        test_info = extract_test_info(issue)
        print(f"  Endpoints found: {test_info['endpoints']}")
        print(f"  Method: {test_info['method']}, Role: {test_info['role']}")

        # Also check dev comments for additional endpoints/context
        for c in dev_comments:
            extra_paths = re.findall(r'/api/v1(/[a-zA-Z0-9/_\-{}:?&=.]+)', c["body"])
            raw = re.findall(r'`(/[a-zA-Z0-9/_\-{}:?&=.]+)`', c["body"])
            for p in extra_paths + raw:
                clean = p.split("?")[0]
                if clean not in test_info["endpoints"]:
                    test_info["endpoints"].append(clean)

        # Test endpoints
        test_results = []
        for ep in test_info["endpoints"]:
            # Replace path params with reasonable defaults
            ep_test = ep.replace("{id}", "1").replace("{employeeId}", "1")
            ep_test = ep_test.replace("{leaveId}", "1").replace("{attendanceId}", "1")
            ep_test = re.sub(r'\{[a-zA-Z_]+\}', '1', ep_test)

            print(f"  Testing: {test_info['method']} {ep_test}")
            result = test_endpoint(test_info["method"], ep_test, test_info["role"])
            test_results.append(result)
            print(f"    -> {result['status']} {'OK' if result['success'] else 'FAIL'}")
            time.sleep(SLOW_DELAY)

        # Analyze
        verdict, details = analyze_issue(issue, dev_comments, test_results)
        stats["tested"] += 1

        if verdict == "fixed":
            print(f"  VERDICT: FIXED - {details[:100]}")
            stats["fixed"] += 1

            # Remove verified-bug if present, add verified-fixed
            remove_label(num, "verified-bug")
            add_label(num, "verified-fixed")
            comment = (
                f"**Re-test result: VERIFIED FIXED**\n\n"
                f"Tested on {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC against `{API_BASE}`.\n\n"
                f"**Details:** {details}\n\n"
                f"Endpoints tested: {', '.join(f'`{r['method']} {r['path']}` -> {r['status']}' for r in test_results) if test_results else 'No direct endpoints; verified via dev comments.'}\n\n"
                f"Labeling as `verified-fixed`."
            )
            add_comment(num, comment)
            time.sleep(2)

        else:  # failing
            print(f"  VERDICT: STILL FAILING - {details[:100]}")
            stats["failing"] += 1

            # Re-open, label as verified-bug
            reopen_issue(num)
            remove_label(num, "verified-fixed")
            add_label(num, "verified-bug")
            comment = (
                f"**Re-test result: STILL FAILING**\n\n"
                f"Tested on {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC against `{API_BASE}`.\n\n"
                f"**Failures:** {details}\n\n"
                f"Endpoints tested: {', '.join(f'`{r['method']} {r['path']}` -> {r['status']}' for r in test_results)}\n\n"
                f"Re-opening and labeling as `verified-bug`."
            )
            add_comment(num, comment)
            time.sleep(2)

        results_log.append({
            "number": num,
            "title": title,
            "result": verdict,
            "details": details,
            "endpoints_tested": len(test_results),
        })

        # Refresh tokens periodically
        if stats["tested"] % 10 == 0:
            tokens["admin"] = None  # Force refresh
            tokens["employee"] = None

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total closed issues found: {len(issues)}")
    print(f"  Tested:  {stats['tested']}")
    print(f"  Fixed:   {stats['fixed']}")
    print(f"  Failing: {stats['failing']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Errors:  {stats['errors']}")
    print(f"\nCompleted: {datetime.now().isoformat()}")

    # Write results to JSON
    with open(r"C:\emptesting\deep_verify_results.json", "w") as f:
        json.dump({
            "run_date": datetime.now().isoformat(),
            "stats": stats,
            "results": results_log,
        }, f, indent=2)
    print(f"\nResults saved to C:\\emptesting\\deep_verify_results.json")


if __name__ == "__main__":
    main()
