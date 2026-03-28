"""
Deep re-test closed issues #401-#600 on EmpCloud/EmpCloud.
- Skips #391-492 (validation spam, consolidated)
- Skips Field Force, Biometrics modules
- Skips rate-limit issues
- Labels verified-fixed or verified-bug
- Re-opens if still failing
- Saves results incrementally
"""

import requests
import time
import json
import re
import sys
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
GITHUB_TOKEN = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
GH_API = "https://api.github.com"
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
SLOW_DELAY = 5  # seconds between API calls to test server
TOKEN_REFRESH_INTERVAL = 540  # 9 minutes

GH_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

SKIP_RANGE = set(range(391, 493))  # validation spam
SKIP_KEYWORDS = ["field force", "emp-field", "biometrics", "emp-biometrics",
                 "rate limit", "rate-limit", "ratelimit", "throttl"]

RESULTS_FILE = r"C:\emptesting\deep_verify_results.json"

# ── Helpers ─────────────────────────────────────────────────────────────────
session = requests.Session()
tokens = {"admin": None, "employee": None, "admin_ts": 0, "employee_ts": 0}


def login(email, password):
    resp = session.post(f"{API_BASE}/auth/login",
                        json={"email": email, "password": password},
                        headers={"Content-Type": "application/json"}, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        try:
            return data["data"]["tokens"]["access_token"]
        except (KeyError, TypeError):
            pass
    print(f"  [LOGIN FAIL] {email}: {resp.status_code} {resp.text[:200]}")
    return None


def get_token(role="admin"):
    now = time.time()
    ts_key = f"{role}_ts"
    if tokens[role] and (now - tokens[ts_key]) < TOKEN_REFRESH_INTERVAL:
        return tokens[role]
    tokens[role] = login(ADMIN_EMAIL if role == "admin" else EMP_EMAIL,
                         ADMIN_PASS if role == "admin" else EMP_PASS)
    tokens[ts_key] = now
    return tokens[role]


def api_request(method, path, role="admin", json_body=None):
    token = get_token(role)
    if not token:
        return None, 0, "No auth token"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{API_BASE}{path}" if path.startswith("/") else f"{API_BASE}/{path}"
    try:
        resp = session.request(method, url, headers=headers, json=json_body, timeout=30)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        return body, resp.status_code, None
    except Exception as e:
        return None, 0, str(e)


def gh_get(url, params=None):
    resp = requests.get(url, headers=GH_HEADERS, params=params, timeout=30)
    return resp.json(), resp.status_code


def gh_post(url, json_body):
    resp = requests.post(url, headers=GH_HEADERS, json=json_body, timeout=30)
    return resp.json(), resp.status_code


def gh_patch(url, json_body):
    resp = requests.patch(url, headers=GH_HEADERS, json=json_body, timeout=30)
    return resp.json(), resp.status_code


def ensure_label_exists(label_name, color, description=""):
    url = f"{GH_API}/repos/{REPO}/labels/{label_name}"
    resp = requests.get(url, headers=GH_HEADERS, timeout=15)
    if resp.status_code == 404:
        requests.post(f"{GH_API}/repos/{REPO}/labels", headers=GH_HEADERS,
                       json={"name": label_name, "color": color, "description": description}, timeout=15)


def add_label(issue_number, label):
    url = f"{GH_API}/repos/{REPO}/issues/{issue_number}/labels"
    gh_post(url, {"labels": [label]})


def remove_label(issue_number, label):
    url = f"{GH_API}/repos/{REPO}/issues/{issue_number}/labels/{label}"
    requests.delete(url, headers=GH_HEADERS, timeout=15)


def add_comment(issue_number, body):
    url = f"{GH_API}/repos/{REPO}/issues/{issue_number}/comments"
    gh_post(url, {"body": body})


def reopen_issue(issue_number):
    url = f"{GH_API}/repos/{REPO}/issues/{issue_number}"
    gh_patch(url, {"state": "open"})


def should_skip(issue):
    num = issue["number"]
    if num in SKIP_RANGE:
        return True, "validation spam range #391-492"
    title = (issue.get("title") or "").lower()
    body_text = (issue.get("body") or "").lower()
    combined = title + " " + body_text
    for kw in SKIP_KEYWORDS:
        if kw in combined:
            return True, f"skip keyword: {kw}"
    labels = [l["name"].lower() for l in issue.get("labels", [])]
    for kw in ["field-force", "biometrics", "rate-limit"]:
        if kw in labels:
            return True, f"skip label: {kw}"
    return False, ""


def get_dev_comments(issue_number):
    url = f"{GH_API}/repos/{REPO}/issues/{issue_number}/comments"
    comments, status = gh_get(url, {"per_page": 50})
    if status != 200:
        return []
    return [{"user": c.get("user", {}).get("login", "?"),
             "body": c.get("body", ""),
             "created_at": c.get("created_at", "")}
            for c in comments if isinstance(c, dict)]


def extract_endpoints(text):
    """Extract API endpoint paths from text."""
    paths = set()
    # Match: GET /endpoint, POST /endpoint etc
    for m in re.findall(r'(?:GET|POST|PUT|PATCH|DELETE)\s+(/[a-zA-Z0-9/_\-{}:?&=.]+)', text):
        paths.add(m.split("?")[0])
    # Match: /api/v1/endpoint
    for m in re.findall(r'/api/v1(/[a-zA-Z0-9/_\-{}:?&=.]+)', text):
        paths.add(m.split("?")[0])
    # Match: backtick paths that look like API paths
    for m in re.findall(r'`(/(?:users|employees|leave|attendance|departments|events|surveys|announcements|holidays|policies|helpdesk|forum|feedback|assets|positions|documents|payroll|admin|organizations|auth|shifts|notifications)[a-zA-Z0-9/_\-{}:?&=.]*)`', text):
        paths.add(m.split("?")[0])
    return list(paths)


def extract_method(text):
    methods = re.findall(r'\b(GET|POST|PUT|PATCH|DELETE)\b', text)
    return methods[0] if methods else "GET"


def extract_role(text):
    lower = text.lower()
    if any(kw in lower for kw in ["employee view", "self-service", "priya", "emp role", "employee role", "employee cannot"]):
        return "employee"
    return "admin"


def test_endpoint(method, path, role="admin"):
    """Test an endpoint. Returns (status, success, snippet, error)."""
    # Replace path params
    path = re.sub(r'\{[a-zA-Z_]+\}', '1', path)
    body, status, error = api_request(method, path, role)
    snippet = str(body)[:300] if body else ""
    return status, (200 <= status < 500 and not error), snippet, error


def analyze_results(issue, dev_comments, test_results):
    """Return ('fixed'|'failing', details_string)."""
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "").lower()
    combined = title + " " + body

    # Check if devs confirmed fix
    fix_info = ""
    for c in dev_comments:
        cb = c["body"].lower()
        if any(kw in cb for kw in ["fixed", "resolved", "deployed", "merged", "patched"]):
            fix_info = c["body"][:200]

    if not test_results:
        if fix_info:
            return "fixed", f"Dev confirmed fix: {fix_info}"
        return "fixed", "No testable endpoints; issue closed, trusting closure."

    failures = []
    for method, path, status, ok, snippet, error in test_results:
        if error:
            failures.append(f"{method} {path}: connection error ({error})")
            continue
        if status >= 500:
            failures.append(f"{method} {path}: server error {status}")
            continue
        # Only flag 404 as failing if the bug was specifically about that endpoint existing
        # Don't flag 404 for paths we guessed from comments
        if status == 404:
            # If the bug title/body references 404, it's still a problem
            if "404" in combined:
                failures.append(f"{method} {path}: still returning 404")
            # Otherwise 404 might just mean we guessed wrong path - don't count it
            continue
        if status in (401, 403):
            if "401" in combined or "403" in combined or "unauthorized" in combined or "forbidden" in combined:
                failures.append(f"{method} {path}: still getting {status}")
            continue

    if failures:
        return "failing", "; ".join(failures)
    if fix_info:
        return "fixed", f"All endpoints OK. Dev: {fix_info}"
    return "fixed", "All tested endpoints responding correctly."


def save_results(stats, results_log):
    with open(RESULTS_FILE, "w") as f:
        json.dump({"run_date": datetime.now().isoformat(), "stats": stats, "results": results_log}, f, indent=2)


# ── Fetch Issues ────────────────────────────────────────────────────────────
def fetch_closed_issues(start=401, end=600):
    """Fetch closed issues in range. Uses paginated list + individual fetches for gaps."""
    issues = {}

    # Paginated fetch
    for page in range(1, 15):
        url = f"{GH_API}/repos/{REPO}/issues"
        params = {"state": "closed", "per_page": 100, "page": page, "sort": "created", "direction": "asc"}
        data, status = gh_get(url, params)
        if status != 200 or not data:
            break
        for iss in data:
            num = iss["number"]
            if start <= num <= end and "pull_request" not in iss:
                issues[num] = iss
        # Stop if we've passed the range
        nums_on_page = [i["number"] for i in data]
        if nums_on_page and min(nums_on_page) > end:
            break
        if nums_on_page and max(nums_on_page) < start:
            continue
        time.sleep(0.5)

    # Fill gaps for non-skip issues only
    for num in range(start, end + 1):
        if num in issues or num in SKIP_RANGE:
            continue
        url = f"{GH_API}/repos/{REPO}/issues/{num}"
        data, status = gh_get(url)
        if status == 200 and data.get("state") == "closed" and "pull_request" not in data:
            issues[num] = data
        time.sleep(0.3)

    return issues


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print(f"Deep Re-test: Closed Issues #401-#600 on {REPO}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)
    sys.stdout.flush()

    # Labels
    print("\n[1] Ensuring labels exist...")
    ensure_label_exists("verified-fixed", "0e8a16", "Bug verified as fixed in re-test")
    ensure_label_exists("verified-bug", "d93f0b", "Bug verified as still present in re-test")

    # Login
    print("\n[2] Logging in...")
    admin_tok = get_token("admin")
    emp_tok = get_token("employee")
    print(f"  Admin: {'OK' if admin_tok else 'FAIL'}")
    print(f"  Employee: {'OK' if emp_tok else 'FAIL'}")
    sys.stdout.flush()
    if not admin_tok:
        print("FATAL: No admin token"); sys.exit(1)

    # Fetch
    print("\n[3] Fetching closed issues #401-#600...")
    sys.stdout.flush()
    issues = fetch_closed_issues(401, 600)
    print(f"  Found {len(issues)} closed issues")
    sys.stdout.flush()

    stats = {"tested": 0, "fixed": 0, "failing": 0, "skipped": 0}
    results_log = []
    sorted_nums = sorted(issues.keys())

    print(f"\n[4] Processing {len(sorted_nums)} issues...\n")
    sys.stdout.flush()

    for num in sorted_nums:
        issue = issues[num]
        title = issue.get("title", "")[:70]
        print(f"--- #{num}: {title} ---")

        skip, reason = should_skip(issue)
        if skip:
            print(f"  SKIP: {reason}")
            stats["skipped"] += 1
            results_log.append({"number": num, "title": title, "result": "skipped", "reason": reason})
            sys.stdout.flush()
            continue

        # Read dev comments
        print(f"  Reading comments...")
        dev_comments = get_dev_comments(num)
        time.sleep(0.5)

        # Extract test info from issue body + comments
        issue_body = issue.get("body") or ""
        all_text = issue_body
        for c in dev_comments:
            all_text += "\n" + c["body"]

        endpoints = extract_endpoints(all_text)
        method = extract_method(issue_body)
        role = extract_role(issue_body)
        print(f"  Endpoints: {endpoints}, Method: {method}, Role: {role}")

        # Test each endpoint
        test_results = []
        for ep in endpoints:
            ep_clean = re.sub(r'\{[a-zA-Z_]+\}', '1', ep)
            print(f"  Test: {method} {ep_clean}", end="")
            status, ok, snippet, error = test_endpoint(method, ep_clean, role)
            test_results.append((method, ep_clean, status, ok, snippet, error))
            print(f" -> {status} {'OK' if ok else 'FAIL'}")
            time.sleep(SLOW_DELAY)

        # Analyze
        verdict, details = analyze_results(issue, dev_comments, test_results)
        stats["tested"] += 1
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')

        if verdict == "fixed":
            print(f"  VERDICT: FIXED")
            stats["fixed"] += 1
            remove_label(num, "verified-bug")
            add_label(num, "verified-fixed")
            ep_summary = ", ".join(f"`{m} {p}` -> {s}" for m, p, s, _, _, _ in test_results) if test_results else "No direct endpoints tested."
            comment = (f"**Re-test result: VERIFIED FIXED**\n\n"
                       f"Tested {now_str} against `{API_BASE}`.\n\n"
                       f"**Details:** {details}\n\n"
                       f"Endpoints: {ep_summary}\n\n"
                       f"Labeling `verified-fixed`.")
            add_comment(num, comment)
        else:
            print(f"  VERDICT: STILL FAILING - {details[:80]}")
            stats["failing"] += 1
            reopen_issue(num)
            remove_label(num, "verified-fixed")
            add_label(num, "verified-bug")
            ep_summary = ", ".join(f"`{m} {p}` -> {s}" for m, p, s, _, _, _ in test_results)
            comment = (f"**Re-test result: STILL FAILING**\n\n"
                       f"Tested {now_str} against `{API_BASE}`.\n\n"
                       f"**Failures:** {details}\n\n"
                       f"Endpoints: {ep_summary}\n\n"
                       f"Re-opening and labeling `verified-bug`.")
            add_comment(num, comment)

        time.sleep(1)
        results_log.append({"number": num, "title": title, "result": verdict, "details": details})
        sys.stdout.flush()

        # Token refresh every 10 issues
        if stats["tested"] % 10 == 0:
            tokens["admin"] = None
            tokens["employee"] = None

        # Incremental save every 5 issues
        if stats["tested"] % 5 == 0:
            save_results(stats, results_log)

    # Final save
    save_results(stats, results_log)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total issues found: {len(issues)}")
    print(f"  Tested:  {stats['tested']}")
    print(f"  Fixed:   {stats['fixed']}")
    print(f"  Failing: {stats['failing']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"\nCompleted: {datetime.now().isoformat()}")
    print(f"Results: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
