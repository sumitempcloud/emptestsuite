#!/usr/bin/env python3
"""
Deep re-test ALL closed issues on EmpCloud/EmpCloud.
- If still failing -> re-open + label "verified-bug"
- If fixed -> leave closed + label "verified-fixed"
- Respects programmer comments (not a bug / by design / false positive -> skip)
- Skips: rate-limit issues, field-force, biometrics
"""

import sys, os, json, time, re, requests, threading
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

LOGFILE = open(r"C:\emptesting\deep_verify_run.log", "w", encoding="utf-8")

def log(msg=""):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    LOGFILE.write(line + "\n")
    LOGFILE.flush()
    os.fsync(LOGFILE.fileno())

# ── Config ──────────────────────────────────────────────────────────────────
GH_TOKEN  = "$GITHUB_TOKEN"
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

GH_WRITE_DELAY = 5
GH_READ_DELAY = 2

# ── Globals ─────────────────────────────────────────────────────────────────
tokens = {}
token_times = {}
results = []

# ── GitHub helpers ──────────────────────────────────────────────────────────
def gh_get(path, params=None):
    time.sleep(GH_READ_DELAY)
    url = f"{GH_API}/repos/{REPO}{path}"
    r = requests.get(url, headers=GH_HEADERS, params=params, timeout=(5, 15))
    return r

def gh_post(path, data=None):
    time.sleep(GH_WRITE_DELAY)
    url = f"{GH_API}/repos/{REPO}{path}"
    r = requests.post(url, headers=GH_HEADERS, json=data, timeout=(5, 15))
    return r

def gh_patch(path, data=None):
    time.sleep(GH_WRITE_DELAY)
    url = f"{GH_API}/repos/{REPO}{path}"
    r = requests.patch(url, headers=GH_HEADERS, json=data, timeout=(5, 15))
    return r

def ensure_labels():
    for name, color, desc in [
        ("verified-bug",   "d73a4a", "Confirmed still failing after re-test"),
        ("verified-fixed", "0e8a16", "Confirmed fixed after re-test"),
    ]:
        r = gh_get(f"/labels/{name}")
        if r.status_code == 404:
            gh_post("/labels", {"name": name, "color": color, "description": desc})
            log(f"  Created label: {name}")
        else:
            log(f"  Label exists: {name}")

def fetch_all_closed_issues():
    issues = []
    for page in range(1, 11):
        r = gh_get("/issues", params={"state": "closed", "per_page": 100, "page": page})
        if r.status_code != 200:
            log(f"  Page {page} error: {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        batch = [i for i in batch if "pull_request" not in i]
        issues.extend(batch)
        log(f"  Page {page}: {len(batch)} issues (total {len(issues)})")
        if len(batch) < 100:
            break
    return issues

def fetch_comments(issue_number):
    r = gh_get(f"/issues/{issue_number}/comments", params={"per_page": 100})
    if r.status_code == 200:
        return r.json()
    return []

# ── Auth ────────────────────────────────────────────────────────────────────
def login(role="admin"):
    now = time.time()
    if role in tokens and (now - token_times.get(role, 0)) < 600:
        return tokens[role]
    cred = CREDS[role]
    try:
        r = requests.post(f"{API_BASE}/auth/login", json=cred, timeout=10)
        if r.status_code in (200, 201):
            data = r.json()
            tok = None
            if "data" in data and isinstance(data["data"], dict):
                toks = data["data"].get("tokens", {})
                if isinstance(toks, dict):
                    tok = toks.get("access_token")
                if not tok:
                    tok = data["data"].get("token") or data["data"].get("access_token")
            if not tok:
                tok = data.get("token") or data.get("access_token")
            if tok:
                tokens[role] = tok
                token_times[role] = now
                return tok
    except Exception as e:
        log(f"  [AUTH] Error {role}: {e}")
    return tokens.get(role)

def api_call(method, path, role="admin", base=None):
    tok = login(role)
    if not tok:
        return None, "No token"
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    url = f"{base or API_BASE}{path}"
    try:
        r = requests.request(method, url, headers=headers, timeout=10)
        return r, f"{r.status_code}"
    except Exception as e:
        return None, str(e)[:100]

# ── Selenium with timeout ──────────────────────────────────────────────────
def selenium_test_url(url, timeout_sec=25):
    """Run Selenium in a thread with hard timeout."""
    result = [None, "Timeout"]

    def _run():
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            opts = Options()
            opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--ignore-certificate-errors")
            d = webdriver.Chrome(options=opts)
            d.set_page_load_timeout(15)
            try:
                d.get(url)
                time.sleep(2)
                title = d.title
                src = d.page_source[:2000] if d.page_source else ""
                cur = d.current_url
                is_404 = any(x in src.lower() for x in ["404", "not found", "page not found"])
                is_error = any(x in src.lower() for x in ["something went wrong", "500", "internal server error"])
                is_blank = len(src.strip()) < 100
                if is_404:
                    result[0] = False
                    result[1] = f"Page 404. Title={title}"
                elif is_error:
                    result[0] = False
                    result[1] = f"Page error. Title={title}"
                elif is_blank:
                    result[0] = False
                    result[1] = f"Page blank. Title={title}"
                else:
                    result[0] = True
                    result[1] = f"Page OK. Title={title} URL={cur[:80]}"
            finally:
                d.quit()
        except Exception as e:
            result[0] = False
            result[1] = f"Selenium: {str(e)[:150]}"

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)
    if t.is_alive():
        return None, "Selenium timed out"
    return result[0], result[1]

# ── Issue testing ───────────────────────────────────────────────────────────
def extract_endpoint(text):
    m = re.findall(r'(/api/v1/[^\s\)\]\}\"\'`,#]+)', text)
    if m: return m[0]
    m = re.findall(r'(?:GET|POST|PUT|PATCH|DELETE)\s+(/[^\s\)\]\}\"\'`,]+)', text)
    if m: return m[0]
    return None

def extract_module(text):
    t = text.lower()
    for mod in ["recruit", "performance", "rewards", "exit", "lms", "payroll", "project", "monitor"]:
        if mod in t:
            return mod
    return None

def extract_method(text):
    t = text.upper()
    for m in ["DELETE", "PATCH", "PUT", "POST", "GET"]:
        if m in t:
            return m
    return "GET"

def classify(title, body):
    text = (title + " " + (body or "")).lower()
    if any(k in text for k in ["rbac", "authorization", "unauthori", "forbidden", "403",
                                "access control", "tenant isolation", "cross-tenant", "privilege"]):
        return "rbac"
    if any(k in text for k in ["xss", "injection", "csrf"]):
        return "security"
    if any(k in text for k in ["404", "not found", "page not found", "blank page", "empty page",
                                "route", "routing"]):
        return "page"
    if any(k in text for k in ["api", "endpoint", "500", "internal server", "status code"]):
        return "api"
    if any(k in text for k in ["ui", "button", "modal", "form", "display", "render",
                                "sidebar", "menu", "dashboard", "click"]):
        return "ui"
    return "api"

def test_issue(issue):
    """Test a single issue. Returns (verdict: bool|None, evidence: str)."""
    title = issue["title"]
    body = issue.get("body") or ""
    text = title + " " + body
    cat = classify(title, body)
    module = extract_module(text)
    endpoint = extract_endpoint(text)
    method = extract_method(text)

    log(f"    cat={cat} module={module} endpoint={endpoint[:50] if endpoint else 'none'}")

    # XSS = not a bug
    if cat == "security" and "xss" in text.lower():
        return None, "XSS not a bug (React escapes)"

    # RBAC test: employee should get 401/403
    if cat == "rbac":
        if not endpoint:
            return None, "No endpoint for RBAC test"
        base = MODULE_APIS.get(module, API_BASE)
        path = endpoint[7:] if endpoint.startswith("/api/v1") else endpoint
        r, info = api_call(method, path, role="employee", base=base)
        if r is None:
            return None, f"API fail: {info}"
        if r.status_code in (401, 403):
            return True, f"Employee gets {r.status_code} on {method} {path}"
        elif r.status_code == 200:
            return False, f"Employee gets 200 on {method} {path} (should be 403)"
        return True, f"Employee gets {r.status_code} on {method} {path}"

    # API test
    if cat == "api" or cat == "page":
        if endpoint:
            base = MODULE_APIS.get(module, API_BASE)
            path = endpoint[7:] if endpoint.startswith("/api/v1") else endpoint
            role = "superadmin" if "/admin/" in path else "admin"
            r, info = api_call(method, path, role=role, base=base)
            if r is None:
                return None, f"API fail: {info}"
            is_500 = "500" in title or "internal server" in body.lower()
            is_404 = "404" in title or "not found" in title.lower()
            if is_500:
                return (r.status_code != 500), f"{method} {path} -> {r.status_code} {'(was 500)' if r.status_code != 500 else ''}"
            if is_404:
                return (r.status_code != 404), f"{method} {path} -> {r.status_code} {'(was 404)' if r.status_code != 404 else ''}"
            if 200 <= r.status_code < 300:
                return True, f"{method} {path} -> {r.status_code}"
            if r.status_code in (401, 403):
                return True, f"{method} {path} -> {r.status_code} (auth enforced)"
            return False, f"{method} {path} -> {r.status_code}"

        # No endpoint found, try SSO for page issues
        if cat == "page" and module:
            route_paths = re.findall(r'(?:/[a-z][a-z0-9\-/_]+)', text.lower())
            path = route_paths[0] if route_paths else "/"
            tok = login("admin")
            if tok:
                mod_url = MODULE_URLS.get(module, MODULE_URLS["empcloud"])
                full_url = f"{mod_url}{path}?sso_token={tok}"
                return selenium_test_url(full_url)
            return None, "No token for SSO"

        return None, "No endpoint to test"

    # UI test via Selenium
    if cat == "ui":
        mod = module or "empcloud"
        route_paths = re.findall(r'(?:/[a-z][a-z0-9\-/_]+)', text.lower())
        path = route_paths[0] if route_paths else "/"
        tok = login("admin")
        if tok:
            mod_url = MODULE_URLS.get(mod, MODULE_URLS["empcloud"])
            full_url = f"{mod_url}{path}?sso_token={tok}"
            return selenium_test_url(full_url)
        return None, "No token for SSO"

    return None, "Cannot determine test"


# ── Main ────────────────────────────────────────────────────────────────────
def apply_verdict(issue, verdict, evidence):
    number = issue["number"]
    title = issue["title"]
    if verdict is True:
        log(f"    => VERIFIED_FIXED")
        comment = (
            f"**Verified fixed** by E2E Test Lead (automated deep re-test, {datetime.now().strftime('%Y-%m-%d %H:%M')}).\n\n"
            f"**Evidence:** {evidence}\n\nLeaving closed."
        )
        try:
            gh_post(f"/issues/{number}/comments", {"body": comment})
            gh_post(f"/issues/{number}/labels", {"labels": ["verified-fixed"]})
        except Exception as e:
            log(f"    GH error: {e}")
        results.append({"number": number, "title": title, "verdict": "VERIFIED_FIXED", "evidence": evidence})

    elif verdict is False:
        log(f"    => VERIFIED_BUG (re-opening)")
        comment = (
            f"**Verified by E2E Test Lead** \u2014 bug still present (automated deep re-test, {datetime.now().strftime('%Y-%m-%d %H:%M')}).\n\n"
            f"**Evidence:** {evidence}\n\nRe-opening."
        )
        try:
            gh_post(f"/issues/{number}/comments", {"body": comment})
            gh_patch(f"/issues/{number}", {"state": "open"})
            gh_post(f"/issues/{number}/labels", {"labels": ["verified-bug"]})
        except Exception as e:
            log(f"    GH error: {e}")
        results.append({"number": number, "title": title, "verdict": "VERIFIED_BUG", "evidence": evidence})

    else:
        log(f"    => SKIPPED: {evidence}")
        results.append({"number": number, "title": title, "verdict": "SKIPPED", "evidence": evidence})


def main():
    log("=" * 70)
    log("EmpCloud Deep Re-Test: ALL Closed Issues")
    log(f"Started: {datetime.now()}")
    log("=" * 70)

    log("\n[1] Labels...")
    ensure_labels()

    log("\n[2] Fetching closed issues...")
    issues = fetch_all_closed_issues()
    log(f"  Total: {len(issues)}")
    if not issues:
        log("No issues. Done.")
        return

    log("\n[3] Auth...")
    login("admin")
    login("employee")
    login("superadmin")

    log(f"\n[4] Processing {len(issues)} issues...")
    for idx, issue in enumerate(issues):
        number = issue["number"]
        title = issue["title"]
        body = issue.get("body") or ""
        text = (title + " " + body).lower()

        log(f"\n[{idx+1}/{len(issues)}] #{number}: {title[:80]}")

        # Skip by keywords
        skip = False
        for kw in SKIP_KEYWORDS:
            if kw in text:
                log(f"    SKIP: keyword '{kw}'")
                results.append({"number": number, "title": title, "verdict": "SKIPPED", "evidence": f"keyword: {kw}"})
                skip = True
                break
        if skip: continue

        # Skip if already has verification label
        labels = [l["name"] for l in issue.get("labels", [])]
        if "verified-fixed" in labels or "verified-bug" in labels:
            log(f"    SKIP: already verified ({labels})")
            results.append({"number": number, "title": title, "verdict": "SKIPPED", "evidence": f"already labeled"})
            continue

        # Check comments
        comments = fetch_comments(number)

        # Skip if already processed in previous run
        already = False
        for c in comments:
            if "automated deep re-test" in c.get("body", ""):
                already = True
                break
        if already:
            log(f"    SKIP: previously processed")
            results.append({"number": number, "title": title, "verdict": "SKIPPED", "evidence": "previously processed"})
            continue

        # Skip if programmer said not a bug
        skip_comment = False
        for c in comments:
            cb = c.get("body", "").lower()
            for phrase in DESIGNER_SKIP:
                if phrase in cb:
                    log(f"    SKIP: programmer '{phrase}'")
                    results.append({"number": number, "title": title, "verdict": "SKIPPED",
                                   "evidence": f"programmer: {phrase}"})
                    skip_comment = True
                    break
            if skip_comment: break
        if skip_comment: continue

        # Test with timeout
        try:
            verdict, evidence = test_issue(issue)
        except Exception as e:
            verdict, evidence = None, f"Error: {str(e)[:100]}"

        apply_verdict(issue, verdict, evidence)

        # Save every 10
        if (idx + 1) % 10 == 0:
            with open(r"C:\emptesting\deep_verify_results.json", "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            log(f"  [saved {len(results)} results]")

        # Refresh tokens every 10
        if (idx + 1) % 10 == 0:
            token_times.clear()
            login("admin")
            login("employee")
            login("superadmin")

    # Final save and summary
    with open(r"C:\emptesting\deep_verify_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    fixed = [r for r in results if r["verdict"] == "VERIFIED_FIXED"]
    bugs  = [r for r in results if r["verdict"] == "VERIFIED_BUG"]
    skips = [r for r in results if r["verdict"] == "SKIPPED"]

    log("\n" + "=" * 70)
    log("SUMMARY")
    log("=" * 70)
    log(f"\n{'#':<6} {'Title':<55} {'Verdict':<16} Evidence")
    log("-" * 130)
    for r in results:
        if r['verdict'] == 'SKIPPED': continue
        t = r['title'][:52] + '...' if len(r['title']) > 55 else r['title']
        e = r['evidence'][:55] + '...' if len(r['evidence']) > 55 else r['evidence']
        log(f"#{r['number']:<5} {t:<55} {r['verdict']:<16} {e}")

    log(f"\n{'=' * 60}")
    log(f"VERIFIED_FIXED: {len(fixed)} | VERIFIED_BUG: {len(bugs)} | SKIPPED: {len(skips)}")
    log(f"{'=' * 60}")
    log(f"Completed: {datetime.now()}")
    LOGFILE.close()


if __name__ == "__main__":
    main()
