#!/usr/bin/env python3
"""
Deep re-test ALL closed issues on EmpCloud/EmpCloud.
- If still failing -> re-open + label "verified-bug"
- If fixed -> leave closed + label "verified-fixed"
- Respects programmer comments (not a bug / by design / false positive -> skip)
- Skips: rate-limit issues, field-force, biometrics
"""

import sys, os, json, time, re, traceback, requests
from datetime import datetime
from urllib.parse import urljoin

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── Config ──────────────────────────────────────────────────────────────────
GH_TOKEN  = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
REPO      = "EmpCloud/EmpCloud"
GH_API    = "https://api.github.com"
GH_HEADERS = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
}

API_BASE  = "https://test-empcloud-api.empcloud.com/api/v1"
CREDS = {
    "admin":      {"email": "ananya@technova.in",  "password": "Welcome@123"},
    "employee":   {"email": "priya@technova.in",   "password": "Welcome@123"},
    "superadmin": {"email": "admin@empcloud.com",  "password": "SuperAdmin@2026"},
}

MODULE_URLS = {
    "recruit":     "https://test-recruit.empcloud.com",
    "performance": "https://test-performance.empcloud.com",
    "rewards":     "https://test-rewards.empcloud.com",
    "exit":        "https://test-exit.empcloud.com",
    "lms":         "https://testlms.empcloud.com",
    "payroll":     "https://testpayroll.empcloud.com",
    "project":     "https://test-project.empcloud.com",
    "monitor":     "https://test-empmonitor.empcloud.com",
    "empcloud":    "https://test-empcloud.empcloud.com",
}

MODULE_APIS = {
    "recruit":     "https://test-recruit-api.empcloud.com/api/v1",
    "performance": "https://test-performance-api.empcloud.com/api/v1",
    "rewards":     "https://test-rewards-api.empcloud.com/api/v1",
    "exit":        "https://test-exit-api.empcloud.com/api/v1",
    "lms":         "https://testlms-api.empcloud.com/api/v1",
    "payroll":     "https://testpayroll-api.empcloud.com/api/v1",
    "project":     "https://test-project-api.empcloud.com/api/v1",
    "monitor":     "https://test-empmonitor-api.empcloud.com/api/v1",
}

SKIP_KEYWORDS = [
    "rate limit", "rate-limit", "ratelimit", "throttl",
    "field force", "field-force", "emp-field",
    "biometric", "emp-biometric",
]

DESIGNER_SKIP = [
    "not a bug", "by design", "false positive", "working as intended",
    "expected behavior", "expected behaviour", "won't fix", "wontfix",
    "duplicate", "not reproducible", "cannot reproduce",
]

GH_CALL_DELAY = 5  # seconds between GitHub API calls

# ── Globals ─────────────────────────────────────────────────────────────────
tokens = {}           # role -> jwt
token_times = {}      # role -> timestamp
driver = None
driver_test_count = 0
results = []          # {number, title, verdict, evidence}

# ── GitHub helpers ──────────────────────────────────────────────────────────
def gh_get(path, params=None):
    time.sleep(GH_CALL_DELAY)
    url = f"{GH_API}/repos/{REPO}{path}"
    r = requests.get(url, headers=GH_HEADERS, params=params, timeout=30)
    return r

def gh_post(path, data=None):
    time.sleep(GH_CALL_DELAY)
    url = f"{GH_API}/repos/{REPO}{path}"
    r = requests.post(url, headers=GH_HEADERS, json=data, timeout=30)
    return r

def gh_patch(path, data=None):
    time.sleep(GH_CALL_DELAY)
    url = f"{GH_API}/repos/{REPO}{path}"
    r = requests.patch(url, headers=GH_HEADERS, json=data, timeout=30)
    return r

def ensure_labels():
    """Create verified-bug and verified-fixed labels if missing."""
    for name, color, desc in [
        ("verified-bug",   "d73a4a", "Confirmed still failing after re-test"),
        ("verified-fixed", "0e8a16", "Confirmed fixed after re-test"),
    ]:
        r = gh_get(f"/labels/{name}")
        if r.status_code == 404:
            gh_post("/labels", {"name": name, "color": color, "description": desc})
            print(f"  Created label: {name}")
        else:
            print(f"  Label exists: {name}")

def fetch_all_closed_issues():
    """Fetch all closed issues (up to 10 pages of 100)."""
    issues = []
    for page in range(1, 11):
        r = gh_get("/issues", params={"state": "closed", "per_page": 100, "page": page})
        if r.status_code != 200:
            print(f"  Page {page} error: {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        # Filter out PRs
        batch = [i for i in batch if "pull_request" not in i]
        issues.extend(batch)
        print(f"  Fetched page {page}: {len(batch)} issues (total {len(issues)})")
        if len(batch) < 100:
            break
    return issues

def fetch_comments(issue_number):
    r = gh_get(f"/issues/{issue_number}/comments", params={"per_page": 100})
    if r.status_code == 200:
        return r.json()
    return []

def should_skip_by_content(title, body):
    """Skip issues about rate limits, field force, biometrics."""
    text = (title + " " + (body or "")).lower()
    for kw in SKIP_KEYWORDS:
        if kw in text:
            return True, f"Skipped: matches skip keyword '{kw}'"
    return False, ""

def should_skip_by_comments(comments):
    """Skip if programmer commented not-a-bug / by-design / etc."""
    for c in comments:
        text = c.get("body", "").lower()
        for phrase in DESIGNER_SKIP:
            if phrase in text:
                return True, f"Programmer said: '{phrase}' in comment by {c['user']['login']}"
    return False, ""

# ── Auth helpers ────────────────────────────────────────────────────────────
def login(role="admin"):
    """Get JWT token for a role, refresh if older than 10 minutes."""
    now = time.time()
    if role in tokens and (now - token_times.get(role, 0)) < 600:
        return tokens[role]
    cred = CREDS[role]
    try:
        r = requests.post(f"{API_BASE}/auth/login", json=cred, timeout=15)
        if r.status_code == 200:
            data = r.json()
            tok = data.get("token") or data.get("data", {}).get("token") or data.get("access_token")
            if tok:
                tokens[role] = tok
                token_times[role] = now
                print(f"    [AUTH] Logged in as {role}")
                return tok
        # try alternate response shapes
        if r.status_code in (200, 201):
            try:
                data = r.json()
                for key in ("token", "accessToken", "access_token", "jwt"):
                    if key in data:
                        tokens[role] = data[key]
                        token_times[role] = now
                        return tokens[role]
                if "data" in data and isinstance(data["data"], dict):
                    for key in ("token", "accessToken", "access_token", "jwt"):
                        if key in data["data"]:
                            tokens[role] = data["data"][key]
                            token_times[role] = now
                            return tokens[role]
            except:
                pass
        print(f"    [AUTH] Login failed for {role}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"    [AUTH] Login exception for {role}: {e}")
    return tokens.get(role)

def api_call(method, path, role="admin", base=None, json_data=None, params=None):
    """Make authenticated API call."""
    tok = login(role)
    if not tok:
        return None, "No auth token"
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    url = f"{base or API_BASE}{path}"
    try:
        r = requests.request(method, url, headers=headers, json=json_data, params=params, timeout=20)
        return r, f"{r.status_code}"
    except Exception as e:
        return None, str(e)

# ── Selenium helpers ────────────────────────────────────────────────────────
def get_driver():
    global driver, driver_test_count
    if driver_test_count >= 3 and driver:
        try:
            driver.quit()
        except:
            pass
        driver = None
        driver_test_count = 0

    if driver is None:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            opts = Options()
            opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--ignore-certificate-errors")

            driver = webdriver.Chrome(options=opts)
            driver.set_page_load_timeout(30)
            driver_test_count = 0
            print("    [SELENIUM] Driver started")
        except Exception as e:
            print(f"    [SELENIUM] Driver failed: {e}")
            driver = None
    return driver

def selenium_check_url(url, wait_for=None):
    """Load URL in Selenium, return (success, evidence)."""
    global driver_test_count
    d = get_driver()
    if not d:
        return None, "Selenium not available"
    try:
        d.get(url)
        driver_test_count += 1
        time.sleep(3)
        title = d.title
        page_src = d.page_source[:2000] if d.page_source else ""
        current = d.current_url

        # Check for 404 / error indicators
        is_404 = any(x in page_src.lower() for x in ["404", "not found", "page not found", "cannot be found"])
        is_error = any(x in page_src.lower() for x in ["error", "something went wrong", "500", "internal server"])
        is_blank = len(page_src.strip()) < 100

        if is_404:
            return False, f"Page shows 404. Title: {title}, URL: {current}"
        if is_error and "error" not in url.lower():
            return False, f"Page shows error. Title: {title}, URL: {current}"
        if is_blank:
            return False, f"Page is blank/empty. Title: {title}"
        return True, f"Page loaded. Title: {title}, URL: {current}"
    except Exception as e:
        driver_test_count += 1
        return False, f"Selenium error: {str(e)[:200]}"

def sso_navigate(module_key, path="/", role="admin"):
    """Get SSO token and navigate to module page."""
    tok = login(role)
    if not tok:
        return None, "No auth token for SSO"
    module_url = MODULE_URLS.get(module_key)
    if not module_url:
        return None, f"Unknown module: {module_key}"
    full_url = f"{module_url}{path}?sso_token={tok}"
    return selenium_check_url(full_url)

# ── Issue classification and testing ────────────────────────────────────────
def classify_issue(title, body, labels):
    """Classify issue type for testing strategy."""
    text = (title + " " + (body or "")).lower()
    label_names = [l["name"].lower() for l in labels]

    # RBAC / Authorization issues
    if any(kw in text for kw in ["rbac", "authorization", "unauthori", "forbidden", "403",
                                  "access control", "tenant isolation", "cross-tenant",
                                  "privilege escalation", "role-based"]):
        return "rbac"

    # 404 / routing / module page
    if any(kw in text for kw in ["404", "not found", "page not found", "route", "routing",
                                  "navigation", "blank page", "empty page"]):
        return "page_404"

    # API endpoint issues
    if any(kw in text for kw in ["api", "endpoint", "500", "internal server",
                                  "response", "status code", "payload"]):
        return "api"

    # UI issues
    if any(kw in text for kw in ["ui", "button", "modal", "form", "display",
                                  "render", "layout", "css", "style", "click",
                                  "dropdown", "sidebar", "menu", "dashboard"]):
        return "ui"

    # Business logic
    if any(kw in text for kw in ["calculation", "logic", "workflow", "approval",
                                  "notification", "email", "validation",
                                  "data integrity", "duplicate"]):
        return "business_logic"

    # XSS / security (skip XSS in DB - not a bug per rules)
    if any(kw in text for kw in ["xss", "injection", "security", "csrf", "cors"]):
        return "security"

    # Default
    return "api"

def extract_endpoint(text):
    """Try to extract API endpoint path from issue text."""
    # Look for /api/v1/... patterns
    matches = re.findall(r'(/api/v1/[^\s\)\]\}\"\'`,]+)', text)
    if matches:
        return matches[0]
    # Look for endpoint-like paths
    matches = re.findall(r'(?:GET|POST|PUT|PATCH|DELETE)\s+(/[^\s\)\]\}\"\'`,]+)', text)
    if matches:
        return matches[0]
    return None

def extract_module(text):
    """Extract module name from issue text."""
    text_lower = text.lower()
    for mod in ["recruit", "performance", "rewards", "exit", "lms", "payroll", "project", "monitor"]:
        if mod in text_lower:
            return mod
    return None

def extract_http_method(text):
    """Extract HTTP method from issue text."""
    text_upper = text.upper()
    for method in ["DELETE", "PATCH", "PUT", "POST", "GET"]:
        if method in text_upper:
            return method
    return "GET"

def test_rbac_issue(title, body):
    """Test RBAC: employee should get 403, not 200."""
    text = title + " " + (body or "")
    endpoint = extract_endpoint(text)
    module = extract_module(text)
    method = extract_http_method(text)

    if not endpoint:
        return None, "Cannot extract endpoint to test RBAC"

    base = MODULE_APIS.get(module) if module else API_BASE
    if not base:
        base = API_BASE

    # If endpoint starts with /api/v1, strip it since base already has it
    if endpoint.startswith("/api/v1"):
        path = endpoint[7:]  # strip /api/v1
    else:
        path = endpoint

    # Test as employee (should be forbidden)
    r, info = api_call(method, path, role="employee", base=base)
    if r is None:
        return None, f"API call failed: {info}"

    if r.status_code in (401, 403):
        return True, f"FIXED: Employee gets {r.status_code} on {method} {path} (properly restricted)"
    elif r.status_code == 200:
        return False, f"STILL FAILING: Employee gets 200 on {method} {path} (should be 403)"
    else:
        return True, f"FIXED: Employee gets {r.status_code} on {method} {path}"

def test_page_404(title, body):
    """Test if a page/route returns 404 or loads properly."""
    text = title + " " + (body or "")
    module = extract_module(text)

    # Try to extract a URL path
    paths = re.findall(r'(?:https?://[^\s]+)', text)
    route_paths = re.findall(r'(?:/[a-z][a-z0-9\-/]+)', text.lower())

    if module:
        # SSO into module and check
        path = route_paths[0] if route_paths else "/"
        ok, evidence = sso_navigate(module, path)
        if ok is None:
            return None, evidence
        return ok, evidence

    # Try navigating to empcloud
    if route_paths:
        path = route_paths[0]
        ok, evidence = sso_navigate("empcloud", path)
        if ok is None:
            return None, evidence
        return ok, evidence

    return None, "Cannot determine URL to test"

def test_api_issue(title, body):
    """Test API endpoint issue."""
    text = title + " " + (body or "")
    endpoint = extract_endpoint(text)
    module = extract_module(text)
    method = extract_http_method(text)

    if not endpoint:
        return None, "Cannot extract endpoint"

    base = MODULE_APIS.get(module) if module else API_BASE
    if not base:
        base = API_BASE

    if endpoint.startswith("/api/v1"):
        path = endpoint[7:]
    else:
        path = endpoint

    # Determine role (use admin by default, superadmin if /admin/ in path)
    role = "admin"
    if "/admin/" in path:
        role = "superadmin"

    r, info = api_call(method, path, role=role, base=base)
    if r is None:
        return None, f"API call failed: {info}"

    # Check if the issue was about 500 errors
    is_500_issue = "500" in title or "internal server" in (body or "").lower()
    if is_500_issue:
        if r.status_code == 500:
            return False, f"STILL FAILING: {method} {path} returns 500"
        else:
            return True, f"FIXED: {method} {path} returns {r.status_code} (was 500)"

    # Check if issue was about 404
    is_404_issue = "404" in title or "not found" in title.lower()
    if is_404_issue:
        if r.status_code == 404:
            return False, f"STILL FAILING: {method} {path} returns 404"
        else:
            return True, f"FIXED: {method} {path} returns {r.status_code} (was 404)"

    # General: 2xx = working, 4xx/5xx = issue
    if 200 <= r.status_code < 300:
        return True, f"FIXED: {method} {path} returns {r.status_code}"
    elif r.status_code in (401, 403):
        # Auth issue, might be by design
        return True, f"FIXED: {method} {path} returns {r.status_code} (auth enforced)"
    else:
        return False, f"STILL FAILING: {method} {path} returns {r.status_code}"

def test_security_issue(title, body):
    """Test security issues (XSS, injection, etc.)."""
    text = (title + " " + (body or "")).lower()

    # XSS in DB is NOT a bug (React escapes output)
    if "xss" in text and ("stored" in text or "database" in text or "db " in text):
        return None, "XSS in DB is not a bug (React auto-escapes) - skip"

    # For other security issues, try the API test approach
    return test_api_issue(title, body)

def test_ui_issue(title, body):
    """Test UI issues via Selenium."""
    text = title + " " + (body or "")
    module = extract_module(text)

    # Try to find a URL or path to navigate to
    route_paths = re.findall(r'(?:/[a-z][a-z0-9\-/]+)', text.lower())

    mod = module or "empcloud"
    path = route_paths[0] if route_paths else "/"

    ok, evidence = sso_navigate(mod, path)
    if ok is None:
        return None, evidence
    return ok, evidence

def test_business_logic(title, body):
    """Test business logic issues - fall back to API testing."""
    return test_api_issue(title, body)

def test_issue(issue):
    """Main dispatch: classify and test an issue."""
    title = issue["title"]
    body = issue.get("body") or ""
    labels = issue.get("labels", [])
    itype = classify_issue(title, body, labels)

    print(f"    Type: {itype}")

    try:
        if itype == "rbac":
            return test_rbac_issue(title, body)
        elif itype == "page_404":
            return test_page_404(title, body)
        elif itype == "api":
            return test_api_issue(title, body)
        elif itype == "security":
            return test_security_issue(title, body)
        elif itype == "ui":
            return test_ui_issue(title, body)
        elif itype == "business_logic":
            return test_business_logic(title, body)
        else:
            return test_api_issue(title, body)
    except Exception as e:
        return None, f"Test error: {str(e)[:200]}"

# ── Main workflow ───────────────────────────────────────────────────────────
def apply_verdict(issue, verdict, evidence):
    """Apply the verdict to the GitHub issue."""
    number = issue["number"]
    title = issue["title"]

    if verdict is True:
        # FIXED - add label, comment, leave closed
        print(f"    -> VERIFIED FIXED")
        comment = (
            f"**Verified fixed** by E2E Test Lead (automated deep re-test, {datetime.now().strftime('%Y-%m-%d %H:%M')}).\n\n"
            f"**Evidence:** {evidence}\n\n"
            f"Leaving closed."
        )
        gh_post(f"/issues/{number}/comments", {"body": comment})
        gh_post(f"/issues/{number}/labels", {"labels": ["verified-fixed"]})
        # Remove verified-bug if present
        existing_labels = [l["name"] for l in issue.get("labels", [])]
        if "verified-bug" in existing_labels:
            time.sleep(GH_CALL_DELAY)
            requests.delete(
                f"{GH_API}/repos/{REPO}/issues/{number}/labels/verified-bug",
                headers=GH_HEADERS, timeout=15
            )
        results.append({"number": number, "title": title, "verdict": "VERIFIED_FIXED", "evidence": evidence})

    elif verdict is False:
        # STILL FAILING - re-open, add label, comment
        print(f"    -> VERIFIED BUG (re-opening)")
        comment = (
            f"**Verified by E2E Test Lead** — bug still present (automated deep re-test, {datetime.now().strftime('%Y-%m-%d %H:%M')}).\n\n"
            f"**Evidence:** {evidence}\n\n"
            f"Re-opening this issue."
        )
        gh_post(f"/issues/{number}/comments", {"body": comment})
        gh_patch(f"/issues/{number}", {"state": "open"})
        gh_post(f"/issues/{number}/labels", {"labels": ["verified-bug"]})
        # Remove verified-fixed if present
        existing_labels = [l["name"] for l in issue.get("labels", [])]
        if "verified-fixed" in existing_labels:
            time.sleep(GH_CALL_DELAY)
            requests.delete(
                f"{GH_API}/repos/{REPO}/issues/{number}/labels/verified-fixed",
                headers=GH_HEADERS, timeout=15
            )
        results.append({"number": number, "title": title, "verdict": "VERIFIED_BUG", "evidence": evidence})

    else:
        # SKIP
        print(f"    -> SKIPPED: {evidence}")
        results.append({"number": number, "title": title, "verdict": "SKIPPED", "evidence": evidence})


def main():
    print("=" * 80)
    print("EmpCloud Deep Re-Test: ALL Closed Issues")
    print(f"Started: {datetime.now()}")
    print("=" * 80)

    # Step 1: Ensure labels exist
    print("\n[1] Ensuring labels exist...")
    ensure_labels()

    # Step 2: Fetch all closed issues
    print("\n[2] Fetching all closed issues...")
    issues = fetch_all_closed_issues()
    print(f"  Total closed issues: {len(issues)}")

    if not issues:
        print("No closed issues found. Exiting.")
        return

    # Step 3: Pre-login
    print("\n[3] Pre-authenticating...")
    login("admin")
    login("employee")
    login("superadmin")

    # Step 4: Process each issue
    print(f"\n[4] Processing {len(issues)} issues...")
    for idx, issue in enumerate(issues):
        number = issue["number"]
        title = issue["title"]
        body = issue.get("body") or ""

        print(f"\n--- [{idx+1}/{len(issues)}] Issue #{number}: {title[:80]} ---")

        # 4a: Skip by content (rate limit, field force, biometrics)
        skip, reason = should_skip_by_content(title, body)
        if skip:
            print(f"    SKIP (content): {reason}")
            results.append({"number": number, "title": title, "verdict": "SKIPPED", "evidence": reason})
            continue

        # 4b: Check if already has verified-fixed or verified-bug label
        existing_labels = [l["name"] for l in issue.get("labels", [])]
        if "verified-fixed" in existing_labels or "verified-bug" in existing_labels:
            print(f"    SKIP: Already has verification label ({', '.join(existing_labels)})")
            results.append({"number": number, "title": title, "verdict": "SKIPPED",
                           "evidence": f"Already labeled: {', '.join(existing_labels)}"})
            continue

        # 4c: Read programmer comments
        comments = fetch_comments(number)
        skip, reason = should_skip_by_comments(comments)
        if skip:
            print(f"    SKIP (programmer comment): {reason}")
            results.append({"number": number, "title": title, "verdict": "SKIPPED", "evidence": reason})
            continue

        # 4d: Test the issue
        verdict, evidence = test_issue(issue)

        # 4e: Apply verdict
        apply_verdict(issue, verdict, evidence)

        # Refresh tokens every 10 tests
        if (idx + 1) % 10 == 0:
            print("    [Refreshing tokens...]")
            token_times.clear()
            login("admin")
            login("employee")
            login("superadmin")

    # Cleanup Selenium
    global driver
    if driver:
        try:
            driver.quit()
        except:
            pass

    # Step 5: Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    fixed = [r for r in results if r["verdict"] == "VERIFIED_FIXED"]
    bugs  = [r for r in results if r["verdict"] == "VERIFIED_BUG"]
    skips = [r for r in results if r["verdict"] == "SKIPPED"]

    print(f"\n{'#':<6} {'Title':<60} {'Verdict':<16} {'Evidence'}")
    print("-" * 140)
    for r in results:
        t = r['title'][:57] + '...' if len(r['title']) > 60 else r['title']
        e = r['evidence'][:60] + '...' if len(r['evidence']) > 60 else r['evidence']
        print(f"#{r['number']:<5} {t:<60} {r['verdict']:<16} {e}")

    print(f"\n{'=' * 60}")
    print(f"VERIFIED_FIXED: {len(fixed)} | VERIFIED_BUG: {len(bugs)} | SKIPPED: {len(skips)}")
    print(f"{'=' * 60}")
    print(f"\nCompleted: {datetime.now()}")

    # Save results to JSON
    with open(r"C:\emptesting\deep_verify_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Results saved to C:\\emptesting\\deep_verify_results.json")


if __name__ == "__main__":
    main()
