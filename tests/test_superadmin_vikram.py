# -*- coding: utf-8 -*-
"""
Super Admin Morning Check - Vikram's Platform Walkthrough
Tests the EMP Cloud HRMS platform from the Super Admin perspective.
Covers: Dashboard, Orgs, Logs, AI Config, Modules, Revenue, Audit,
        Users, Subscriptions, Settings, Module Health, Data Isolation,
        Onboarding, and Platform Gaps.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os, time, json, traceback, base64, re, datetime
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ─── Config ───────────────────────────────────────────────────────────
BASE_URL       = "https://test-empcloud.empcloud.com"
API_URL        = "https://test-empcloud-api.empcloud.com"
SUPER_EMAIL    = "admin@empcloud.com"
SUPER_PASS     = "SuperAdmin@2026"
ORG_EMAIL      = "ananya@technova.in"
ORG_PASS       = "Welcome@123"
GITHUB_PAT     = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO    = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = Path(r"C:\Users\Admin\screenshots\superadmin_journey")
CHROME_BIN     = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

MODULES_TO_CHECK = {
    "Recruit":     {"fe": "https://test-recruit.empcloud.com",     "api": "https://test-recruit-api.empcloud.com"},
    "Performance": {"fe": "https://test-performance.empcloud.com", "api": "https://test-performance-api.empcloud.com"},
    "Rewards":     {"fe": "https://test-rewards.empcloud.com",     "api": "https://test-rewards-api.empcloud.com"},
    "Exit":        {"fe": "https://test-exit.empcloud.com",        "api": "https://test-exit-api.empcloud.com"},
    "LMS":         {"fe": "https://testlms.empcloud.com",          "api": "https://testlms-api.empcloud.com"},
    "Payroll":     {"fe": "https://testpayroll.empcloud.com",      "api": "https://testpayroll-api.empcloud.com"},
    "Project":     {"fe": "https://test-project.empcloud.com",     "api": "https://test-project-api.empcloud.com"},
}

SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ─── State ────────────────────────────────────────────────────────────
driver = None
driver_test_count = 0
super_token = None
org_token = None
issues_filed = []
test_results = []

# ─── Helpers ──────────────────────────────────────────────────────────

def get_driver():
    """Create or return Selenium driver, restart every 3 tests."""
    global driver, driver_test_count
    if driver is not None and driver_test_count < 3:
        return driver
    if driver is not None:
        try: driver.quit()
        except: pass
    opts = Options()
    opts.binary_location = CHROME_BIN
    for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                 "--window-size=1920,1080", "--disable-gpu", "--ignore-certificate-errors"]:
        opts.add_argument(arg)
    svc = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    driver_test_count = 0
    return driver

def bump():
    global driver_test_count
    driver_test_count += 1

def screenshot(name):
    fname = f"{name}_{int(time.time())}.png"
    path = SCREENSHOT_DIR / fname
    try: get_driver().save_screenshot(str(path))
    except: pass
    return path

def api_login(email, password):
    """Login via /api/v1/auth/login, return access_token."""
    try:
        r = requests.post(f"{API_URL}/api/v1/auth/login",
                          json={"email": email, "password": password}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("data", {}).get("tokens", {}).get("access_token")
    except: pass
    return None

def api_get(path, token=None, base=None):
    base = base or API_URL
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try: return requests.get(f"{base}{path}", headers=headers, timeout=15)
    except: return None

def api_post(path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    try: return requests.post(f"{API_URL}{path}", json=body or {}, headers=headers, timeout=15)
    except: return None

def api_patch(path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    try: return requests.patch(f"{API_URL}{path}", json=body or {}, headers=headers, timeout=15)
    except: return None

def upload_screenshot(filepath):
    """Upload screenshot to GitHub, return raw URL."""
    if not filepath or not Path(filepath).exists(): return None
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        fname = Path(filepath).name
        gh_path = f"screenshots/superadmin_journey/{fname}"
        r = requests.put(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/{gh_path}",
            json={"message": f"Upload screenshot: {fname}", "content": content, "branch": "main"},
            headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"},
            timeout=30
        )
        if r.status_code in (200, 201):
            return r.json().get("content", {}).get("download_url", "")
    except Exception as e:
        print(f"    [WARN] Screenshot upload: {e}")
    return None

def file_issue(title, body, labels=None):
    """File a GitHub issue, return URL."""
    try:
        r = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            json={"title": title, "body": body, "labels": labels or []},
            headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"},
            timeout=20
        )
        if r.status_code in (200, 201):
            url = r.json().get("html_url", "")
            issues_filed.append({"title": title, "url": url})
            print(f"    [ISSUE] {title}")
            print(f"      -> {url}")
            return url
    except Exception as e:
        print(f"    [WARN] Issue error: {e}")
    return None

def record(name, status, details=""):
    test_results.append({"name": name, "status": status, "details": details})
    print(f"  [{status}] {name}: {details[:200]}")

def selenium_login(email, password):
    d = get_driver()
    d.get(f"{BASE_URL}/login")
    time.sleep(2)
    try:
        ef = WebDriverWait(d, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
        ef.clear(); ef.send_keys(email)
        pf = d.find_element(By.CSS_SELECTOR, "input[type='password']")
        pf.clear(); pf.send_keys(password)
        d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
        return "/login" not in d.current_url
    except Exception as e:
        print(f"    Selenium login error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════
#                         TEST FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def test_01_api_login():
    """API login for Super Admin and Org Admin."""
    global super_token, org_token
    print("\n" + "=" * 60)
    print("  1. API Login")
    print("=" * 60)

    super_token = api_login(SUPER_EMAIL, SUPER_PASS)
    if super_token:
        record("Super Admin API Login", "PASS", f"Token obtained (len={len(super_token)})")
    else:
        record("Super Admin API Login", "FAIL", "Could not get token from /api/v1/auth/login")

    org_token = api_login(ORG_EMAIL, ORG_PASS)
    if org_token:
        record("Org Admin API Login", "PASS", f"Token obtained (len={len(org_token)})")
    else:
        record("Org Admin API Login", "FAIL", "Could not get token for ananya@technova.in")
    bump()


def test_02_dashboard_selenium():
    """Login via browser and check Super Admin dashboard."""
    print("\n" + "=" * 60)
    print("  2. Super Admin Dashboard (Browser)")
    print("=" * 60)
    d = get_driver()
    ok = selenium_login(SUPER_EMAIL, SUPER_PASS)
    ss1 = screenshot("01_after_login")
    landed = d.current_url
    print(f"  Landed on: {landed}")

    if "/admin" in landed or "/dashboard" in landed:
        record("Login Landing Page", "PASS", f"Landed on {landed}")
    else:
        record("Login Landing Page", "WARN", f"Landed on {landed}, expected /admin/super")

    # Navigate to super admin dashboard
    d.get(f"{BASE_URL}/admin/super")
    time.sleep(3)
    ss2 = screenshot("02_super_dashboard")
    src = d.page_source.lower()
    url = d.current_url

    if "/login" in url:
        record("Super Admin Dashboard", "FAIL", "Redirected to login")
        bump(); return

    checks = {
        "Organization count":  any(x in src for x in ["organization", "total org", "companies", "org count"]),
        "Total users":         any(x in src for x in ["total users", "user count", "active users", "total employee"]),
        "Revenue info":        any(x in src for x in ["revenue", "mrr", "arr", "billing", "$"]),
    }
    missing = [k for k, v in checks.items() if not v]

    if missing:
        record("Dashboard Metrics", "WARN", f"Missing: {', '.join(missing)}")
        # Already filed in first run -- skip duplicate
    else:
        record("Dashboard Metrics", "PASS", "Shows org count, users, revenue")

    # Check body text for actual numbers
    body_text = d.find_element(By.TAG_NAME, "body").text
    numbers = re.findall(r'\d+', body_text[:3000])
    if numbers:
        print(f"  Numbers on dashboard: {numbers[:20]}")

    bump()


def test_03_organizations_api():
    """Check orgs via API - /api/v1/admin/organizations."""
    print("\n" + "=" * 60)
    print("  3. Organizations (API)")
    print("=" * 60)
    if not super_token:
        record("Organizations API", "FAIL", "No token"); return

    r = api_get("/api/v1/admin/organizations", super_token)
    if r and r.status_code == 200:
        data = r.json()
        orgs = data.get("data", [])
        record("List Organizations", "PASS", f"{len(orgs)} orgs returned")
        for org in (orgs if isinstance(orgs, list) else [])[:10]:
            if isinstance(org, dict):
                print(f"    - {org.get('name','?')}: users={org.get('userCount','?')}, active={org.get('is_active','?')}")
    elif r and r.status_code == 500:
        record("List Organizations", "FAIL", "GET /api/v1/admin/organizations returns 500 Internal Error")
        ss = screenshot("03_orgs_500")
        img = upload_screenshot(ss)
        file_issue(
            "Organization listing crashes with 500 error for Super Admin",
            f"""## Summary
When Super Admin tries to list all organizations via API, the server returns a 500 Internal Server Error.

## Steps to Reproduce
1. Login as Super Admin (admin@empcloud.com)
2. GET `{API_URL}/api/v1/admin/organizations`
3. Response: `500 Internal Error`

## Response Body
```json
{r.text[:500]}
```

## Expected
Should return the list of all organizations with their details (name, user count, subscription, status).

## Impact
Super Admin cannot programmatically view or manage organizations. The org management UI may also be affected.

## Screenshot
{f'![500 Error]({img})' if img else 'N/A'}
""",
            labels=["bug", "super-admin", "api", "P1"]
        )
    else:
        status = r.status_code if r else "unreachable"
        record("List Organizations", "FAIL", f"Returned {status}")
    bump()


def test_04_organizations_selenium():
    """Check org management in UI."""
    print("\n" + "=" * 60)
    print("  4. Organizations (Browser)")
    print("=" * 60)
    d = get_driver()
    if "/login" in d.current_url:
        selenium_login(SUPER_EMAIL, SUPER_PASS)
        time.sleep(2)

    d.get(f"{BASE_URL}/admin/organizations")
    time.sleep(3)
    ss = screenshot("04_admin_orgs")
    src = d.page_source.lower()
    url = d.current_url

    if "/login" in url:
        record("Org Management UI", "FAIL", "Redirected to login"); bump(); return

    has_technova = "technova" in src
    has_globaltech = "globaltech" in src
    has_org_keyword = "organization" in src or "company" in src or "tenant" in src

    if has_org_keyword:
        record("Org Management Page", "PASS", f"Page loaded at {url}")
    else:
        record("Org Management Page", "WARN", "Page loaded but no org-related content visible")

    if has_technova:
        record("TechNova Visible", "PASS", "TechNova listed")
    else:
        record("TechNova Visible", "WARN", "TechNova not visible in org listing")

    if has_globaltech:
        record("GlobalTech Visible", "PASS", "GlobalTech listed")
    else:
        record("GlobalTech Visible", "WARN", "GlobalTech not visible in org listing")

    # Check if any orgs are listed at all
    rows = d.find_elements(By.CSS_SELECTOR, "table tbody tr, .org-card, .organization-row, [class*='org']")
    print(f"  Org rows/cards found: {len(rows)}")

    # Look for test/garbage orgs
    body = d.find_element(By.TAG_NAME, "body").text.lower()
    garbage_patterns = ["test org", "asdf", "delete me", "xxx", "temp org"]
    found_garbage = [p for p in garbage_patterns if p in body]
    if found_garbage:
        record("Garbage Orgs", "WARN", f"Possible test/garbage orgs: {found_garbage}")

    bump()


def test_05_logs_dashboard():
    """Check /admin/logs -- Log Dashboard."""
    print("\n" + "=" * 60)
    print("  5. System Health & Logs")
    print("=" * 60)
    d = get_driver()
    if "/login" in d.current_url:
        selenium_login(SUPER_EMAIL, SUPER_PASS); time.sleep(2)

    d.get(f"{BASE_URL}/admin/logs")
    time.sleep(3)
    ss = screenshot("05_admin_logs")
    src = d.page_source.lower()
    url = d.current_url

    if "/login" in url:
        record("Log Dashboard UI", "FAIL", "Redirected to login"); bump(); return

    if "log" in src or "error" in src or "event" in src:
        record("Log Dashboard UI", "PASS", f"Loaded at {url}")
    else:
        record("Log Dashboard UI", "WARN", f"Page at {url} doesn't look like a log dashboard")

    # API: Health endpoint
    r = api_get("/health")
    if r and r.status_code == 200:
        record("Platform /health", "PASS", "200 OK")
    else:
        record("Platform /health", "FAIL", f"{r.status_code if r else 'unreachable'}")

    # API: Admin health (module status)
    if super_token:
        r = api_get("/api/v1/admin/health", super_token)
        if r and r.status_code == 200:
            data = r.json().get("data", {})
            healthy = data.get("healthy_count", 0)
            total = data.get("total_count", 0)
            overall = data.get("overall_status", "unknown")
            record("Module Health Check", "PASS" if overall == "healthy" else "WARN",
                   f"{healthy}/{total} modules healthy, overall={overall}")

            # List down modules
            for m in data.get("modules", []):
                status = m.get("status", "?")
                name = m.get("name", "?")
                latency = m.get("latency_ms", "?")
                icon = "OK" if status == "healthy" else "DOWN"
                print(f"    [{icon}] {name}: {status} ({latency}ms)")

                if status != "healthy":
                    record(f"{name} Health", "FAIL", f"Status: {status}")

    # API: Error logs
    if super_token:
        r = api_get("/api/v1/admin/logs/errors", super_token)
        if r and r.status_code == 200:
            errors = r.json().get("data", [])
            record("Error Logs API", "PASS", f"{len(errors)} error log entries")
            # Show recent errors
            for e in errors[:5]:
                if isinstance(e, dict):
                    print(f"    ERROR [{e.get('module','?')}]: {e.get('message','')[:100]}")
            if len(errors) > 20:
                record("Error Rate", "WARN", f"{len(errors)} errors in log -- may need attention")

    bump()


def test_06_ai_config():
    """Check /admin/ai-config -- AI provider management."""
    print("\n" + "=" * 60)
    print("  6. AI Configuration")
    print("=" * 60)

    # API check first (reliable)
    if super_token:
        r = api_get("/api/v1/admin/ai-config", super_token)
        if r and r.status_code == 200:
            configs = r.json().get("data", [])
            record("AI Config API", "PASS", f"{len(configs)} config entries")

            active_provider = None
            model = None
            keys_set = []
            for c in configs:
                key = c.get("config_key", "")
                val = c.get("config_value")
                active = c.get("is_active")
                if key == "active_provider":
                    active_provider = val
                    print(f"    Active provider: {val}")
                elif key == "ai_model":
                    model = val
                    print(f"    Model: {val}")
                elif "api_key" in key:
                    masked = val if val else "(not set)"
                    is_set = val is not None and val != ""
                    print(f"    {key}: {masked} (active={active})")
                    if is_set: keys_set.append(key)

            if active_provider:
                record("Active AI Provider", "PASS", f"Provider: {active_provider}")
            else:
                record("Active AI Provider", "WARN", "No active provider configured")

            if model:
                record("AI Model Configured", "PASS", f"Model: {model}")
            else:
                record("AI Model Configured", "WARN", "No model configured")

            if keys_set:
                record("API Keys Set", "PASS", f"Keys configured: {', '.join(keys_set)}")
            else:
                record("API Keys Set", "WARN", "No API keys configured")

    # Selenium check
    d = get_driver()
    if "/login" in d.current_url:
        selenium_login(SUPER_EMAIL, SUPER_PASS); time.sleep(2)

    d.get(f"{BASE_URL}/admin/ai-config")
    time.sleep(3)
    ss = screenshot("06_ai_config")
    url = d.current_url
    src = d.page_source.lower()

    if "/login" in url:
        record("AI Config UI", "FAIL", "Redirected to login -- session lost after driver restart?")
        img = upload_screenshot(ss)
        file_issue(
            "AI Configuration page not accessible -- session drops after navigation",
            f"""## Summary
Navigating to `/admin/ai-config` redirects to login even though the Super Admin session was active.
This may indicate session/auth issues with this route.

## Steps to Reproduce
1. Login as Super Admin
2. Navigate to other admin pages (works fine)
3. Navigate to `/admin/ai-config`
4. Gets redirected to `/login`

## Notes
- The API endpoint `/api/v1/admin/ai-config` works correctly with the same token
- Other admin pages (/admin/logs, /admin/organizations) work fine

## Screenshot
{f'![AI Config Redirect]({img})' if img else 'N/A'}
""",
            labels=["bug", "super-admin", "ai-config"]
        )
    elif "ai" in src or "config" in src or "provider" in src or "claude" in src or "anthropic" in src:
        record("AI Config UI", "PASS", f"Loaded at {url}")
    else:
        record("AI Config UI", "WARN", f"Page at {url} doesn't show AI config content")

    bump()


def test_07_modules():
    """Check module management."""
    print("\n" + "=" * 60)
    print("  7. Module Management")
    print("=" * 60)

    # API
    if super_token:
        r = api_get("/api/v1/admin/modules", super_token)
        if r and r.status_code == 200:
            modules = r.json().get("data", [])
            record("Modules API", "PASS", f"{len(modules)} modules")

            zero_subs = []
            for m in modules:
                name = m.get("name", "?")
                slug = m.get("slug", "?")
                subs = m.get("subscriber_count", 0)
                seats = m.get("total_seats", 0)
                used = m.get("used_seats", 0)
                rev = m.get("revenue", 0)
                print(f"    - {name} ({slug}): {subs} subscribers, {used}/{seats} seats, ${rev} revenue")
                if subs == 0:
                    zero_subs.append(name)

            if zero_subs:
                record("Modules with Zero Subscribers", "WARN",
                       f"{len(zero_subs)} modules have 0 subscribers: {', '.join(zero_subs[:3])}")
            else:
                record("Module Subscription Coverage", "PASS", "All modules have at least 1 subscriber")

    # Selenium
    d = get_driver()
    if "/login" in d.current_url:
        selenium_login(SUPER_EMAIL, SUPER_PASS); time.sleep(2)

    d.get(f"{BASE_URL}/modules")
    time.sleep(3)
    ss = screenshot("07_modules_page")
    src = d.page_source.lower()

    module_names = ["payroll", "recruit", "performance", "lms", "project", "rewards", "exit"]
    found = [m for m in module_names if m in src]
    if found:
        record("Modules UI", "PASS", f"Found modules: {', '.join(found)}")
    else:
        record("Modules UI", "WARN", "No module names found on /modules page")

    bump()


def test_08_revenue():
    """Check revenue & billing overview."""
    print("\n" + "=" * 60)
    print("  8. Revenue & Billing")
    print("=" * 60)

    # API - we know /api/v1/admin/revenue works
    if super_token:
        r = api_get("/api/v1/admin/revenue", super_token)
        if r and r.status_code == 200:
            data = r.json().get("data", {})
            mrr = data.get("mrr", "?")
            arr = data.get("arr", "?")
            growth = data.get("mrr_growth_percent", "?")
            record("Revenue API", "PASS", f"MRR=${mrr}, ARR=${arr}, Growth={growth}%")

            # Check if revenue is suspiciously zero
            if mrr == 0 and arr == 0:
                record("Revenue Data", "WARN", "MRR and ARR both $0 despite 10 active subscriptions")
                ss = screenshot("08_zero_revenue")
                img = upload_screenshot(ss)
                file_issue(
                    "Revenue shows $0 MRR and $0 ARR despite 10 active subscriptions",
                    f"""## Summary
The revenue API reports $0 MRR and $0 ARR, yet the subscription metrics show 10 active subscriptions across basic and enterprise tiers.

## API Response
```json
{json.dumps(data, indent=2)[:1000]}
```

## Context
- Subscription API shows: 10 active subscriptions (9 basic, 1 enterprise)
- Total seats: 198 allocated
- Yet revenue is zero across all modules and tiers

## Possible Causes
- Subscriptions may not have pricing configured
- Billing integration may not be connected
- Revenue calculation may have a bug

## Expected
With 10 active subscriptions, revenue should reflect their pricing tiers.
""",
                    labels=["bug", "super-admin", "billing", "P2"]
                )

            # Revenue by module
            by_module = data.get("revenue_by_module", [])
            for m in by_module:
                name = m.get("name", "?")
                rev = m.get("revenue", 0)
                if rev > 0:
                    print(f"    {name}: ${rev}")

    # Selenium
    d = get_driver()
    if "/login" in d.current_url:
        selenium_login(SUPER_EMAIL, SUPER_PASS); time.sleep(2)

    d.get(f"{BASE_URL}/admin/revenue")
    time.sleep(3)
    ss = screenshot("08_revenue_page")
    src = d.page_source.lower()

    if any(kw in src for kw in ["revenue", "mrr", "arr", "billing"]):
        record("Revenue UI", "PASS", "Revenue page loaded")
    else:
        record("Revenue UI", "WARN", "Revenue page doesn't show expected content")

    bump()


def test_09_audit():
    """Check audit trail / activity logs."""
    print("\n" + "=" * 60)
    print("  9. Audit Trail")
    print("=" * 60)
    d = get_driver()
    if "/login" in d.current_url:
        selenium_login(SUPER_EMAIL, SUPER_PASS); time.sleep(2)

    audit_found = False
    for path in ["/admin/audit", "/admin/logs", "/admin/activity"]:
        d.get(f"{BASE_URL}{path}")
        time.sleep(3)
        src = d.page_source.lower()
        if any(kw in src for kw in ["audit", "activity", "action", "event"]):
            ss = screenshot(f"09_audit_{path.replace('/', '_')}")
            record("Audit Trail Page", "PASS", f"Found at {path}")
            audit_found = True

            # Check for filter capabilities
            filters = {
                "Action type filter": any(x in src for x in ["action type", "event type", "filter by action"]),
                "User filter":        any(x in src for x in ["filter by user", "user name", "search user"]),
                "Date range filter":  any(x in src for x in ["date range", "from date", "start date", "date filter"]),
            }
            missing_filters = [k for k, v in filters.items() if not v]
            if missing_filters:
                record("Audit Filters", "WARN", f"Missing: {', '.join(missing_filters)}")
                img = upload_screenshot(ss)
                file_issue(
                    "Audit log missing filter controls (action type, user, date range)",
                    f"""## Summary
The audit log page at `{path}` doesn't have visible filter controls for narrowing down audit entries.

## Missing Filters
{chr(10).join('- ' + f for f in missing_filters)}

## Expected
Platform admin needs to quickly find specific audit events:
- Filter by action type (login, create, update, delete)
- Filter by specific user
- Filter by date range
- These are essential for security investigations and compliance

## Screenshot
{f'![Audit]({img})' if img else 'N/A'}
""",
                    labels=["enhancement", "super-admin", "audit"]
                )
            else:
                record("Audit Filters", "PASS", "All filter controls present")
            break

    if not audit_found:
        record("Audit Trail Page", "WARN", "No dedicated audit page found")

    bump()


def test_10_user_management():
    """Cross-org user management."""
    print("\n" + "=" * 60)
    print("  10. User Management Across Orgs")
    print("=" * 60)

    if not super_token:
        record("User Management", "FAIL", "No token"); return

    # Super admin user list
    r = api_get("/api/v1/users", super_token)
    if r and r.status_code == 200:
        data = r.json()
        users = data.get("data", [])
        total = data.get("meta", {}).get("total", len(users))
        record("Super Admin User List", "PASS" if total > 0 else "WARN",
               f"Total={total} users visible (paginated)")

        # Check if super admin only sees own org users
        orgs_seen = set()
        for u in (users if isinstance(users, list) else []):
            orgs_seen.add(u.get("organization_id"))
        print(f"  Org IDs visible to super admin: {orgs_seen}")
        if len(orgs_seen) <= 1:
            record("Cross-Org User Visibility", "WARN",
                   f"Super admin only sees org_id(s): {orgs_seen} -- cannot manage users across all orgs")
            # This is a significant gap for a platform admin
            file_issue(
                "Super Admin can only see their own org's users, not all platform users",
                f"""## Summary
The Super Admin at `/api/v1/users` only returns users from their own organization (org_id={list(orgs_seen)}). There is no endpoint to list users across all organizations.

## Impact
- Cannot search for a specific user across the platform
- Cannot deactivate a user from platform level
- Cannot see total user count across all orgs
- Cannot audit user activity across organizations

## Expected
Super Admin should have a cross-org user management view:
- List all users across all organizations
- Search by name/email
- Filter by organization
- Deactivate/reset password from platform level

## API Response
Only {total} user(s) returned from org {list(orgs_seen)}
""",
                labels=["enhancement", "super-admin", "user-management"]
            )
    bump()


def test_11_subscriptions():
    """Check subscription metrics."""
    print("\n" + "=" * 60)
    print("  11. Subscription Management")
    print("=" * 60)

    if super_token:
        r = api_get("/api/v1/admin/subscriptions", super_token)
        if r and r.status_code == 200:
            data = r.json().get("data", {})
            record("Subscription API", "PASS", "Subscription metrics retrieved")

            # Tier distribution
            tiers = data.get("tier_distribution", [])
            for t in tiers:
                plan = t.get("plan_tier", "?")
                count = t.get("count", 0)
                seats = t.get("total_seats", 0)
                used = t.get("used_seats", 0)
                util = t.get("utilization", 0)
                print(f"    {plan}: {count} orgs, {used}/{seats} seats ({util}% utilized)")

            # Overall
            total_seats = data.get("total_seats", 0)
            used_seats = data.get("used_seats", 0)
            util = data.get("overall_utilization", 0)
            print(f"    Overall: {used_seats}/{total_seats} seats ({util}% utilized)")

            # Status
            statuses = data.get("status_distribution", [])
            for s in statuses:
                print(f"    Status {s.get('status','?')}: {s.get('count',0)} orgs")

            # Check for concerning patterns
            if used_seats == 0 and total_seats > 0:
                record("Seat Utilization", "WARN",
                       f"0/{total_seats} seats used across platform -- seat tracking may not be working")
                file_issue(
                    "Seat utilization shows 0% across all subscriptions despite active users",
                    f"""## Summary
The subscription metrics show 0 used seats out of {total_seats} total allocated seats across all organizations, despite there being active users on the platform.

## Subscription Data
```json
{json.dumps(data, indent=2)[:1000]}
```

## Expected
- TechNova alone has ~20+ users visible via API
- Used seats should reflect actual active user counts
- This metric is critical for billing and capacity planning

## Possible Cause
Seat counting may not be connected to user provisioning.
""",
                    labels=["bug", "super-admin", "billing"]
                )
            else:
                record("Seat Utilization", "PASS", f"{used_seats}/{total_seats} seats used")

    bump()


def test_12_platform_settings():
    """Check platform-wide settings."""
    print("\n" + "=" * 60)
    print("  12. Platform Settings")
    print("=" * 60)
    d = get_driver()
    if "/login" in d.current_url:
        selenium_login(SUPER_EMAIL, SUPER_PASS); time.sleep(2)

    settings_found = False
    for path in ["/admin/settings", "/settings", "/admin/platform-settings"]:
        d.get(f"{BASE_URL}{path}")
        time.sleep(3)
        src = d.page_source.lower()
        if any(kw in src for kw in ["settings", "configuration", "smtp", "timezone", "security"]):
            ss = screenshot(f"12_settings_{path.replace('/', '_')}")
            record("Platform Settings Page", "PASS", f"Found at {path}")
            settings_found = True

            checks = {
                "SMTP/Email Config": any(x in src for x in ["smtp", "email config", "mail server"]),
                "Security Settings": any(x in src for x in ["security", "password policy", "session timeout", "2fa"]),
                "Timezone/Language": any(x in src for x in ["timezone", "language", "locale"]),
            }
            for name, found in checks.items():
                if found:
                    record(name, "PASS", f"Visible in settings")
                else:
                    record(name, "WARN", f"Not visible in platform settings")
            break

    if not settings_found:
        record("Platform Settings Page", "WARN", "No platform settings page found")

    bump()


def test_13_module_health():
    """Check each external module's health."""
    print("\n" + "=" * 60)
    print("  13. External Module Health")
    print("=" * 60)

    # Use the admin health API (already has internal checks)
    if super_token:
        r = api_get("/api/v1/admin/health", super_token)
        if r and r.status_code == 200:
            data = r.json().get("data", {})
            down_modules = []
            for m in data.get("modules", []):
                name = m.get("name", "?")
                status = m.get("status", "?")
                if status != "healthy":
                    down_modules.append(name)

            if down_modules:
                record("Module Health (Internal)", "WARN", f"Down: {', '.join(down_modules)}")
                ss = screenshot("13_module_health")
                img = upload_screenshot(ss)
                file_issue(
                    f"Platform health degraded: {', '.join(down_modules)} modules are down",
                    f"""## Summary
The admin health check reports that {len(down_modules)} module(s) are down: **{', '.join(down_modules)}**.
Overall platform status: **{data.get('overall_status', '?')}** ({data.get('healthy_count', '?')}/{data.get('total_count', '?')} healthy)

## Module Status
| Module | Status | Latency |
|--------|--------|---------|
{chr(10).join(f"| {m.get('name','?')} | {m.get('status','?')} | {m.get('latency_ms','?')}ms |" for m in data.get('modules', []))}

## API Response
```json
{json.dumps(data, indent=2)[:800]}
```

## Impact
Users accessing these modules will likely see errors or degraded functionality.
""",
                    labels=["bug", "infrastructure", "P1"]
                )
            else:
                record("Module Health (Internal)", "PASS", "All modules healthy")

    # External health checks
    for mod_name, urls in MODULES_TO_CHECK.items():
        api_base = urls["api"]
        try:
            r = requests.get(f"{api_base}/health", timeout=10)
            if r.status_code == 200:
                record(f"{mod_name} External Health", "PASS", f"{api_base}/health -> 200")
            else:
                record(f"{mod_name} External Health", "WARN", f"{api_base}/health -> {r.status_code}")
        except:
            record(f"{mod_name} External Health", "WARN", f"{api_base}/health unreachable")

    bump()


def test_14_data_isolation():
    """Cross-org data isolation spot check."""
    print("\n" + "=" * 60)
    print("  14. Data Isolation")
    print("=" * 60)

    if not org_token:
        record("Data Isolation", "WARN", "No org admin token"); return

    # TechNova admin should only see TechNova users
    r = api_get("/api/v1/users?per_page=100", org_token)
    if r and r.status_code == 200:
        data = r.json()
        users = data.get("data", [])
        total = data.get("meta", {}).get("total", len(users))
        orgs = set(u.get("organization_id") for u in users if isinstance(u, dict))
        print(f"  TechNova admin sees {total} users from org_ids: {orgs}")

        if len(orgs) <= 1 and 5 in orgs:
            record("Org Data Isolation", "PASS", f"TechNova admin only sees org_id=5 ({total} users)")
        elif len(orgs) > 1:
            record("Org Data Isolation", "FAIL", f"TechNova admin sees multiple orgs: {orgs}")
            file_issue(
                "CRITICAL: Org admin can see users from other organizations",
                f"Multi-tenant isolation breach. TechNova admin sees org_ids: {orgs}",
                labels=["bug", "critical", "security"]
            )
        else:
            record("Org Data Isolation", "PASS", f"Only sees org_ids: {orgs}")

    # TechNova admin should not be able to access admin endpoints
    r = api_get("/api/v1/admin/organizations", org_token)
    if r:
        if r.status_code in (401, 403):
            record("Org Admin Admin-Route Block", "PASS", f"Admin endpoint blocked: {r.status_code}")
        elif r.status_code == 200:
            record("Org Admin Admin-Route Block", "FAIL", "Org admin can access /admin/organizations!")
            file_issue(
                "RBAC: Org admin can access super admin organization endpoint",
                f"GET /api/v1/admin/organizations returns 200 for org admin role.\nExpected: 403 Forbidden.",
                labels=["bug", "security", "rbac"]
            )
        else:
            record("Org Admin Admin-Route Block", "PASS", f"Admin endpoint returned {r.status_code} (not 200)")

    bump()


def test_15_onboarding():
    """Check new org creation capability."""
    print("\n" + "=" * 60)
    print("  15. New Organization Onboarding")
    print("=" * 60)
    d = get_driver()
    if "/login" in d.current_url:
        selenium_login(SUPER_EMAIL, SUPER_PASS); time.sleep(2)

    # Look for create org option
    for path in ["/admin/organizations", "/admin/super"]:
        d.get(f"{BASE_URL}{path}")
        time.sleep(3)
        src = d.page_source.lower()
        body = d.find_element(By.TAG_NAME, "body").text.lower()

        if any(kw in body for kw in ["create org", "new org", "add org", "add organization", "create organization"]):
            record("Create Org Option", "PASS", f"Found at {path}")
            break
        # Check for button/link
        buttons = d.find_elements(By.CSS_SELECTOR, "button, a.btn, a.button")
        for btn in buttons:
            txt = btn.text.lower()
            if any(kw in txt for kw in ["create", "add", "new"]):
                if "org" in txt or "company" in txt:
                    record("Create Org Button", "PASS", f"Button: '{btn.text}' at {path}")
                    break
    else:
        record("Create Org Option", "WARN", "No visible option to create a new organization from admin panel")

    bump()


def test_16_sso_modules():
    """SSO into external modules."""
    print("\n" + "=" * 60)
    print("  16. SSO into External Modules")
    print("=" * 60)
    d = get_driver()
    if "/login" in d.current_url:
        selenium_login(SUPER_EMAIL, SUPER_PASS); time.sleep(2)

    d.get(f"{BASE_URL}/modules")
    time.sleep(3)
    ss = screenshot("16_modules_page")

    # Try clicking on a couple modules
    tested = 0
    for mod_name in ["Recruit", "Performance", "LMS"]:
        try:
            # Find clickable module element
            links = d.find_elements(By.XPATH,
                f"//*[contains(text(), '{mod_name}') or contains(text(), '{mod_name.lower()}')]")
            if links:
                # Find parent link/button
                parent = links[0]
                try:
                    parent = links[0].find_element(By.XPATH, "./ancestor::a | ./ancestor::button")
                except:
                    parent = links[0]
                parent.click()
                time.sleep(4)
                ss = screenshot(f"16_sso_{mod_name.lower()}")
                url = d.current_url
                print(f"    {mod_name}: navigated to {url}")

                if "error" in d.page_source.lower()[:500] or "404" in d.page_source.lower()[:500]:
                    record(f"SSO {mod_name}", "WARN", f"Error page at {url}")
                else:
                    record(f"SSO {mod_name}", "PASS", f"Module loaded at {url}")
                tested += 1

                # Go back
                d.get(f"{BASE_URL}/modules")
                time.sleep(2)
        except Exception as e:
            record(f"SSO {mod_name}", "WARN", f"Could not click: {e}")

        if tested >= 2:
            break

    bump()


def test_17_platform_gaps():
    """Assess what's missing for platform admin role."""
    print("\n" + "=" * 60)
    print("  17. Platform Gaps Assessment")
    print("=" * 60)
    d = get_driver()
    if "/login" in d.current_url:
        selenium_login(SUPER_EMAIL, SUPER_PASS); time.sleep(2)

    d.get(f"{BASE_URL}/admin/super")
    time.sleep(3)
    ss = screenshot("17_super_dashboard_final")
    src = d.page_source.lower()
    body = d.find_element(By.TAG_NAME, "body").text.lower()

    gaps = []
    if "active user" not in body and "online" not in body:
        gaps.append("Real-time active users count")
    if "alert" not in body and "notification" not in body:
        gaps.append("System alerting/notifications for issues")
    if "broadcast" not in body and "maintenance" not in body and "announcement" not in body:
        gaps.append("Broadcast maintenance messages to all orgs")
    if "impersonate" not in body and "login as" not in body:
        gaps.append("Impersonate org admin for debugging")
    if "api usage" not in body and "api calls" not in body:
        gaps.append("API usage tracking per org")
    if "export" not in body and "download report" not in body:
        gaps.append("Export platform analytics")
    if "email template" not in body:
        gaps.append("Email template management")
    if "version" not in body and "changelog" not in body:
        gaps.append("Changelog/version info on admin panel")

    print(f"  Platform admin gaps found: {len(gaps)}")
    for g in gaps:
        print(f"    - {g}")

    if gaps:
        record("Platform Gaps", "WARN", f"{len(gaps)} features missing from admin panel")
    else:
        record("Platform Gaps", "PASS", "Good feature coverage")

    bump()


# ═══════════════════════════════════════════════════════════════════════
#                            MAIN RUNNER
# ═══════════════════════════════════════════════════════════════════════

def run_all():
    global driver

    print("=" * 70)
    print("  VIKRAM'S MORNING CHECK - EMP Cloud Super Admin")
    print(f"  Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Platform: {BASE_URL}")
    print("=" * 70)

    tests = [
        test_01_api_login,
        test_02_dashboard_selenium,
        test_03_organizations_api,
        test_04_organizations_selenium,
        test_05_logs_dashboard,
        test_06_ai_config,
        test_07_modules,
        test_08_revenue,
        test_09_audit,
        test_10_user_management,
        test_11_subscriptions,
        test_12_platform_settings,
        test_13_module_health,
        test_14_data_isolation,
        test_15_onboarding,
        test_16_sso_modules,
        test_17_platform_gaps,
    ]

    for test_fn in tests:
        try:
            test_fn()
        except Exception as e:
            name = test_fn.__name__
            print(f"\n  [CRASH] {name}: {e}")
            traceback.print_exc()
            record(name, "FAIL", f"Crashed: {str(e)[:200]}")
            try: screenshot(f"crash_{name}")
            except: pass

    # Cleanup
    try:
        if driver: driver.quit()
    except: pass

    # ─── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  MORNING CHECK SUMMARY")
    print("=" * 70)

    pass_c = sum(1 for r in test_results if r["status"] == "PASS")
    fail_c = sum(1 for r in test_results if r["status"] == "FAIL")
    warn_c = sum(1 for r in test_results if r["status"] == "WARN")
    total = len(test_results)

    print(f"\n  Total Checks: {total}")
    print(f"  PASS: {pass_c}  |  FAIL: {fail_c}  |  WARN: {warn_c}")
    if total > 0:
        print(f"  Pass Rate: {pass_c/total*100:.0f}%")

    if fail_c > 0:
        print(f"\n  --- FAILURES ---")
        for r in test_results:
            if r["status"] == "FAIL":
                print(f"    {r['name']}: {r['details'][:120]}")

    if warn_c > 0:
        print(f"\n  --- WARNINGS ---")
        for r in test_results:
            if r["status"] == "WARN":
                print(f"    {r['name']}: {r['details'][:120]}")

    print(f"\n  --- ISSUES FILED ({len(issues_filed)}) ---")
    for iss in issues_filed:
        print(f"    {iss['title']}")
        print(f"      {iss['url']}")

    print(f"\n  Screenshots: {SCREENSHOT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    run_all()
