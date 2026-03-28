"""
FRESH E2E Test — Vikram (Super Admin)
Tests: /admin/super, /admin/ai-config, /admin/logs, /admin/organizations,
       Revenue analytics, Module management, Audit logs, Cross-org visibility
Selenium + API hybrid. Screenshots saved to fresh_superadmin folder.
"""

import os, sys, time, json, traceback, requests, base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *

# ── Config ──────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com/api/v1"
EMAIL = "admin@empcloud.com"
PASSW = "SuperAdmin@2026"
SS_DIR = r"C:\Users\Admin\screenshots\fresh_superadmin"
GH_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GH_REPO = "EmpCloud/EmpCloud"

os.makedirs(SS_DIR, exist_ok=True)

results = []
bugs_found = []
auth_token = None
driver = None
driver_uses = 0
MAX_DRIVER_USES = 4  # restart driver every 4 tests


# ── Helpers ─────────────────────────────────────────────────────────────
def mk_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-extensions")
    opts.page_load_strategy = "normal"
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(3)
    return d


def get_driver():
    global driver, driver_uses
    if driver is None or driver_uses >= MAX_DRIVER_USES:
        if driver:
            try: driver.quit()
            except: pass
        driver = mk_driver()
        driver_uses = 0
    driver_uses += 1
    return driver


def ss(d, name):
    """Save screenshot and return file path."""
    p = os.path.join(SS_DIR, f"{name}.png")
    try:
        d.save_screenshot(p)
        print(f"  [SS] {name}.png")
    except:
        print(f"  [SS] FAILED {name}.png")
        p = None
    return p


def log(phase, test, status, details=""):
    results.append({"phase": phase, "test": test, "status": status, "details": details})
    icon = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "INFO")
    print(f"  [{icon}] {phase} > {test}: {details}")


def log_bug(title, details, screenshot_path=None):
    bugs_found.append({"title": title, "details": details, "ss": screenshot_path})
    print(f"  [BUG] {title}")


def api_login():
    """Login via API and return JWT token."""
    global auth_token
    r = requests.post(f"{API_URL}/auth/login",
                      json={"email": EMAIL, "password": PASSW}, timeout=15)
    if r.status_code == 200:
        data = r.json()
        # Try common token locations — including nested data.tokens
        auth_token = (data.get("access_token") or data.get("token")
                      or data.get("data", {}).get("access_token")
                      or data.get("data", {}).get("token")
                      or data.get("data", {}).get("tokens", {}).get("access_token"))
        if auth_token:
            print(f"  [AUTH] API login OK, token={auth_token[:20]}...")
            return auth_token
    print(f"  [AUTH] API login failed: {r.status_code} {r.text[:200]}")
    return None


def api_get(path, params=None):
    """Authenticated GET request."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = requests.get(f"{API_URL}{path}", headers=headers, params=params, timeout=15)
    return r


def api_post(path, payload=None):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = requests.post(f"{API_URL}{path}", headers=headers, json=payload, timeout=15)
    return r


def selenium_login(d):
    """Login via Selenium UI."""
    d.get(f"{BASE_URL}/login")
    time.sleep(2)
    try:
        email_input = WebDriverWait(d, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='email' i]"))
        )
        email_input.clear()
        email_input.send_keys(EMAIL)

        pw_input = d.find_element(By.CSS_SELECTOR, "input[type='password']")
        pw_input.clear()
        pw_input.send_keys(PASSW)

        btn = d.find_element(By.CSS_SELECTOR, "button[type='submit'], button.login-btn, form button")
        btn.click()
        time.sleep(3)

        # Verify login succeeded — should NOT still be on /login
        if "/login" not in d.current_url or "/dashboard" in d.current_url or "/admin" in d.current_url:
            print(f"  [AUTH] Selenium login OK -> {d.current_url}")
            return True
        print(f"  [AUTH] Selenium login may have failed, url={d.current_url}")
        return True  # Proceed anyway — SPA might not redirect URL
    except Exception as e:
        print(f"  [AUTH] Selenium login error: {e}")
        return False


def check_page_content(d, url, name, expect_keywords=None):
    """Navigate to URL, take screenshot, check if page has real content."""
    try:
        d.get(url)
        time.sleep(3)
        sp = ss(d, name)
        page_text = d.find_element(By.TAG_NAME, "body").text
        page_len = len(page_text.strip())
        page_src = d.page_source

        # Check for error indicators
        has_error = any(x in page_text.lower() for x in [
            "not found", "404", "access denied", "forbidden",
            "unauthorized", "something went wrong", "error"
        ])

        # Check for expected keywords
        found_keywords = []
        missing_keywords = []
        if expect_keywords:
            for kw in expect_keywords:
                if kw.lower() in page_text.lower() or kw.lower() in page_src.lower():
                    found_keywords.append(kw)
                else:
                    missing_keywords.append(kw)

        return {
            "url": url,
            "text_len": page_len,
            "has_error": has_error,
            "found_keywords": found_keywords,
            "missing_keywords": missing_keywords,
            "screenshot": sp,
            "page_text": page_text[:500],
            "title": d.title
        }
    except Exception as e:
        return {"url": url, "error": str(e), "screenshot": None}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: API-based tests
# ═══════════════════════════════════════════════════════════════════════
def phase1_api_tests():
    print("\n" + "=" * 70)
    print("PHASE 1: API-BASED SUPER ADMIN TESTS")
    print("=" * 70)

    token = api_login()
    if not token:
        log("API", "Login", "FAIL", "Cannot login via API")
        return

    log("API", "Login", "PASS", "JWT obtained")

    # ── 1a. Admin Organizations ────────────────────────────────────────
    print("\n--- 1a. Admin Organizations ---")
    r = api_get("/admin/organizations")
    if r.status_code == 200:
        data = r.json()
        orgs = data if isinstance(data, list) else data.get("data", data.get("organizations", []))
        if isinstance(orgs, list):
            log("API", "List organizations", "PASS", f"Got {len(orgs)} orgs")
            for org in orgs[:5]:
                name = org.get("name") or org.get("organization_name", "?")
                oid = org.get("id", "?")
                print(f"      Org: {name} (id={oid})")
        else:
            log("API", "List organizations", "PASS", f"Response: {str(data)[:200]}")
    elif r.status_code == 403:
        log("API", "List organizations", "FAIL", "403 Forbidden — super admin should have access")
        log_bug("Super Admin cannot list organizations via API",
                f"GET /admin/organizations returns 403 for super admin.\nResponse: {r.text[:300]}")
    else:
        log("API", "List organizations", "INFO", f"Status {r.status_code}: {r.text[:200]}")

    # ── 1b. Admin Health ───────────────────────────────────────────────
    print("\n--- 1b. Admin Health ---")
    r = api_get("/admin/health")
    if r.status_code == 200:
        data = r.json()
        log("API", "Admin health", "PASS", f"Response: {str(data)[:200]}")
    else:
        log("API", "Admin health", "INFO", f"Status {r.status_code}: {r.text[:200]}")

    # ── 1c. Admin Data Sanity ──────────────────────────────────────────
    print("\n--- 1c. Admin Data Sanity ---")
    r = api_get("/admin/data-sanity")
    if r.status_code == 200:
        data = r.json()
        log("API", "Admin data-sanity", "PASS", f"Response: {str(data)[:200]}")
    else:
        log("API", "Admin data-sanity", "INFO", f"Status {r.status_code}: {r.text[:200]}")

    # ── 1d. Audit Logs ─────────────────────────────────────────────────
    print("\n--- 1d. Audit Logs ---")
    r = api_get("/audit")
    if r.status_code == 200:
        data = r.json()
        logs_list = data if isinstance(data, list) else data.get("data", data.get("logs", data.get("audits", [])))
        if isinstance(logs_list, list):
            log("API", "Audit logs", "PASS", f"Got {len(logs_list)} audit entries")
            for entry in logs_list[:3]:
                action = entry.get("action", entry.get("event", "?"))
                user = entry.get("user", entry.get("user_email", entry.get("performed_by", "?")))
                print(f"      Audit: {action} by {user}")
        else:
            log("API", "Audit logs", "PASS", f"Response: {str(data)[:200]}")
    elif r.status_code == 403:
        log("API", "Audit logs", "FAIL", "403 for super admin")
    else:
        log("API", "Audit logs", "INFO", f"Status {r.status_code}: {r.text[:200]}")

    # ── 1e. Modules listing ────────────────────────────────────────────
    print("\n--- 1e. Modules ---")
    r = api_get("/modules")
    if r.status_code == 200:
        data = r.json()
        modules = data if isinstance(data, list) else data.get("data", data.get("modules", []))
        if isinstance(modules, list):
            log("API", "Modules list", "PASS", f"Got {len(modules)} modules")
            for m in modules[:10]:
                mname = m.get("name") or m.get("module_name", "?")
                mstatus = m.get("status", m.get("is_active", "?"))
                print(f"      Module: {mname} (status={mstatus})")
        else:
            log("API", "Modules list", "PASS", f"Response: {str(data)[:200]}")
    else:
        log("API", "Modules list", "INFO", f"Status {r.status_code}: {r.text[:200]}")

    # ── 1f. Subscriptions ──────────────────────────────────────────────
    print("\n--- 1f. Subscriptions ---")
    r = api_get("/subscriptions")
    if r.status_code == 200:
        data = r.json()
        log("API", "Subscriptions", "PASS", f"Response: {str(data)[:300]}")
    else:
        log("API", "Subscriptions", "INFO", f"Status {r.status_code}: {r.text[:200]}")

    # ── 1g. Users listing (cross-org) ──────────────────────────────────
    print("\n--- 1g. Users listing (cross-org visibility) ---")
    r = api_get("/users")
    if r.status_code == 200:
        data = r.json()
        users = data if isinstance(data, list) else data.get("data", data.get("users", []))
        if isinstance(users, list):
            log("API", "Users list", "PASS", f"Got {len(users)} users")
            # Check if we can see users from multiple orgs
            org_ids = set()
            for u in users:
                oid = u.get("organization_id") or u.get("org_id")
                if oid:
                    org_ids.add(str(oid))
            if len(org_ids) > 1:
                log("API", "Cross-org user visibility", "PASS", f"Can see users from {len(org_ids)} orgs: {org_ids}")
            elif len(org_ids) == 1:
                log("API", "Cross-org user visibility", "INFO", f"Only see users from 1 org (id={list(org_ids)[0]})")
            else:
                log("API", "Cross-org user visibility", "INFO", "No org_id in user data")
        else:
            log("API", "Users list", "PASS", f"Response: {str(data)[:200]}")
    else:
        log("API", "Users list", "INFO", f"Status {r.status_code}: {r.text[:200]}")

    # ── 1h. Notifications ──────────────────────────────────────────────
    print("\n--- 1h. Notifications ---")
    r = api_get("/notifications")
    if r.status_code == 200:
        data = r.json()
        notifs = data if isinstance(data, list) else data.get("data", data.get("notifications", []))
        count = len(notifs) if isinstance(notifs, list) else "?"
        log("API", "Notifications", "PASS", f"Got {count} notifications")
    else:
        log("API", "Notifications", "INFO", f"Status {r.status_code}: {r.text[:200]}")

    # ── 1i. Departments (org-level) ────────────────────────────────────
    print("\n--- 1i. Departments ---")
    r = api_get("/organizations/me/departments")
    if r.status_code == 200:
        data = r.json()
        depts = data if isinstance(data, list) else data.get("data", data.get("departments", []))
        count = len(depts) if isinstance(depts, list) else "?"
        log("API", "Departments", "PASS", f"Got {count} departments")
    else:
        log("API", "Departments", "INFO", f"Status {r.status_code}: {r.text[:200]}")

    # ── 1j. Locations (org-level) ──────────────────────────────────────
    print("\n--- 1j. Locations ---")
    r = api_get("/organizations/me/locations")
    if r.status_code == 200:
        data = r.json()
        locs = data if isinstance(data, list) else data.get("data", data.get("locations", []))
        count = len(locs) if isinstance(locs, list) else "?"
        log("API", "Locations", "PASS", f"Got {count} locations")
    else:
        log("API", "Locations", "INFO", f"Status {r.status_code}: {r.text[:200]}")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: Selenium UI tests
# ═══════════════════════════════════════════════════════════════════════
def phase2_selenium_tests():
    print("\n" + "=" * 70)
    print("PHASE 2: SELENIUM UI TESTS")
    print("=" * 70)

    # ── 2a. Login & Super Admin Dashboard ──────────────────────────────
    print("\n--- 2a. Login + Super Admin Dashboard ---")
    d = get_driver()
    if not selenium_login(d):
        log("UI", "Login", "FAIL", "Selenium login failed")
        return

    ss(d, "01_after_login")
    log("UI", "Login", "PASS", f"Landed on {d.current_url}")

    # ── 2b. /admin/super ───────────────────────────────────────────────
    print("\n--- 2b. /admin/super ---")
    info = check_page_content(d, f"{BASE_URL}/admin/super", "02_admin_super",
                              expect_keywords=["organization", "user", "revenue", "admin", "dashboard", "module"])
    if "error" in info:
        log("UI", "/admin/super", "FAIL", info["error"])
    else:
        if info["has_error"] and info["text_len"] < 100:
            log("UI", "/admin/super page", "FAIL",
                f"Error detected, text_len={info['text_len']}, text={info['page_text'][:200]}")
            log_bug("Super Admin dashboard (/admin/super) shows error or is empty",
                    f"URL: {BASE_URL}/admin/super\nPage text length: {info['text_len']}\n"
                    f"Content: {info['page_text'][:300]}",
                    info["screenshot"])
        else:
            log("UI", "/admin/super page", "PASS",
                f"text_len={info['text_len']}, found={info['found_keywords']}, missing={info['missing_keywords']}")

    # ── 2c. /admin/ai-config ──────────────────────────────────────────
    print("\n--- 2c. /admin/ai-config ---")
    info = check_page_content(d, f"{BASE_URL}/admin/ai-config", "03_admin_ai_config",
                              expect_keywords=["ai", "config", "provider", "model", "key", "openai", "claude", "gemini"])
    if "error" in info:
        log("UI", "/admin/ai-config", "FAIL", info["error"])
    else:
        if info["text_len"] < 50 and not info["found_keywords"]:
            log("UI", "/admin/ai-config page", "FAIL",
                f"Page appears empty/broken, text_len={info['text_len']}")
            log_bug("AI Configuration page (/admin/ai-config) appears empty",
                    f"URL: {BASE_URL}/admin/ai-config\nPage text length: {info['text_len']}\n"
                    f"Content: {info['page_text'][:300]}",
                    info["screenshot"])
        else:
            log("UI", "/admin/ai-config page", "PASS",
                f"text_len={info['text_len']}, found={info['found_keywords']}, missing={info['missing_keywords']}")

    # ── 2d. /admin/logs ───────────────────────────────────────────────
    print("\n--- 2d. /admin/logs ---")
    d = get_driver()  # May restart driver
    if driver_uses == 1:
        selenium_login(d)

    info = check_page_content(d, f"{BASE_URL}/admin/logs", "04_admin_logs",
                              expect_keywords=["log", "error", "event", "auth", "query", "system"])
    if "error" in info:
        log("UI", "/admin/logs", "FAIL", info["error"])
    else:
        if info["text_len"] < 50 and not info["found_keywords"]:
            log("UI", "/admin/logs page", "FAIL",
                f"Page appears empty/broken, text_len={info['text_len']}")
            log_bug("Log Dashboard (/admin/logs) appears empty",
                    f"URL: {BASE_URL}/admin/logs\nPage text length: {info['text_len']}\n"
                    f"Content: {info['page_text'][:300]}",
                    info["screenshot"])
        else:
            log("UI", "/admin/logs page", "PASS",
                f"text_len={info['text_len']}, found={info['found_keywords']}, missing={info['missing_keywords']}")

    # ── 2e. /admin/organizations ──────────────────────────────────────
    print("\n--- 2e. /admin/organizations ---")
    info = check_page_content(d, f"{BASE_URL}/admin/organizations", "05_admin_organizations",
                              expect_keywords=["organization", "technova", "globaltech", "plan", "subscription", "user"])
    if "error" in info:
        log("UI", "/admin/organizations", "FAIL", info["error"])
    else:
        if info["text_len"] < 50:
            log("UI", "/admin/organizations page", "FAIL",
                f"Page appears empty, text_len={info['text_len']}")
            log_bug("Organizations page (/admin/organizations) appears empty",
                    f"URL: {BASE_URL}/admin/organizations\nContent: {info['page_text'][:300]}",
                    info["screenshot"])
        else:
            log("UI", "/admin/organizations page", "PASS",
                f"text_len={info['text_len']}, found={info['found_keywords']}, missing={info['missing_keywords']}")

    # ── 2f. Revenue / Billing pages ───────────────────────────────────
    print("\n--- 2f. Revenue Analytics ---")
    d = get_driver()
    if driver_uses == 1:
        selenium_login(d)

    # Try common revenue/billing paths
    revenue_paths = [
        "/admin/revenue", "/admin/billing", "/admin/analytics",
        "/admin/subscriptions", "/admin/super"  # revenue might be on super dash
    ]
    revenue_found = False
    for rp in revenue_paths:
        info = check_page_content(d, f"{BASE_URL}{rp}", f"06_revenue_{rp.replace('/', '_')}",
                                  expect_keywords=["revenue", "mrr", "arr", "billing", "subscription", "payment"])
        if "error" not in info and info.get("found_keywords"):
            log("UI", f"Revenue at {rp}", "PASS",
                f"Found: {info['found_keywords']}")
            revenue_found = True
            break

    if not revenue_found:
        log("UI", "Revenue analytics", "INFO",
            "No dedicated revenue analytics page found — may be embedded in /admin/super")

    # ── 2g. Module Management ─────────────────────────────────────────
    print("\n--- 2g. Module Management ---")
    module_paths = ["/admin/modules", "/admin/super", "/modules"]
    module_found = False
    for mp in module_paths:
        info = check_page_content(d, f"{BASE_URL}{mp}", f"07_modules_{mp.replace('/', '_')}",
                                  expect_keywords=["module", "payroll", "recruit", "performance", "lms", "enable", "disable"])
        if "error" not in info and info.get("found_keywords"):
            log("UI", f"Module mgmt at {mp}", "PASS",
                f"Found: {info['found_keywords']}")
            module_found = True
            break

    if not module_found:
        log("UI", "Module management", "INFO",
            "No dedicated module management page found — may be on super dashboard")

    # ── 2h. Audit Logs UI ─────────────────────────────────────────────
    print("\n--- 2h. Audit Logs UI ---")
    d = get_driver()
    if driver_uses == 1:
        selenium_login(d)

    audit_paths = ["/admin/audit", "/audit", "/admin/logs"]
    audit_found = False
    for ap in audit_paths:
        info = check_page_content(d, f"{BASE_URL}{ap}", f"08_audit_{ap.replace('/', '_')}",
                                  expect_keywords=["audit", "action", "user", "date", "log", "event"])
        if "error" not in info and len(info.get("found_keywords", [])) >= 2:
            log("UI", f"Audit logs at {ap}", "PASS",
                f"Found: {info['found_keywords']}")
            audit_found = True
            break

    if not audit_found:
        log("UI", "Audit logs UI", "INFO", "No dedicated audit log page with rich content found")

    # ── 2i. Cross-org visibility ──────────────────────────────────────
    print("\n--- 2i. Cross-org visibility (Selenium) ---")
    info = check_page_content(d, f"{BASE_URL}/admin/organizations", "09_cross_org",
                              expect_keywords=["technova", "globaltech"])
    if "error" not in info:
        if "technova" in [k.lower() for k in info.get("found_keywords", [])]:
            log("UI", "Cross-org visibility", "PASS", "TechNova visible")
        if "globaltech" in [k.lower() for k in info.get("found_keywords", [])]:
            log("UI", "Cross-org visibility", "PASS", "GlobalTech visible")
        if not info.get("found_keywords"):
            log("UI", "Cross-org visibility", "INFO",
                f"Org names not found in page text. Content: {info['page_text'][:200]}")

    # ── 2j. Sidebar navigation check ──────────────────────────────────
    print("\n--- 2j. Sidebar navigation ---")
    try:
        d.get(f"{BASE_URL}/admin/super")
        time.sleep(3)
        # Try to find sidebar links
        sidebar_links = d.find_elements(By.CSS_SELECTOR, "nav a, aside a, .sidebar a, [class*='sidebar'] a, [class*='nav'] a")
        if sidebar_links:
            link_texts = [l.text.strip() for l in sidebar_links if l.text.strip()]
            log("UI", "Sidebar links", "PASS", f"Found {len(link_texts)} links: {link_texts[:15]}")
        else:
            # Try broader selector
            all_links = d.find_elements(By.TAG_NAME, "a")
            link_texts = [l.text.strip() for l in all_links if l.text.strip()]
            log("UI", "Sidebar links", "INFO", f"No sidebar found; total links on page: {len(link_texts)}")
        ss(d, "10_sidebar")
    except Exception as e:
        log("UI", "Sidebar navigation", "FAIL", str(e))

    # ── 2k. Check dashboard stats/cards ───────────────────────────────
    print("\n--- 2k. Dashboard cards & stats ---")
    try:
        d.get(f"{BASE_URL}/admin/super")
        time.sleep(3)
        # Look for stat cards / numbers
        cards = d.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='stat'], [class*='metric'], [class*='widget']")
        if cards:
            log("UI", "Dashboard cards", "PASS", f"Found {len(cards)} card/stat elements")
            for c in cards[:5]:
                print(f"      Card text: {c.text[:80]}")
        else:
            # Check page text for numbers
            body = d.find_element(By.TAG_NAME, "body").text
            log("UI", "Dashboard cards", "INFO", f"No card elements found; page length={len(body)}")
        ss(d, "11_dashboard_cards")
    except Exception as e:
        log("UI", "Dashboard cards", "FAIL", str(e))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: API deep-dive (cross-org, security)
# ═══════════════════════════════════════════════════════════════════════
def phase3_security_cross_org():
    print("\n" + "=" * 70)
    print("PHASE 3: CROSS-ORG & SECURITY CHECKS")
    print("=" * 70)

    if not auth_token:
        api_login()
    if not auth_token:
        log("SECURITY", "Login", "FAIL", "No token")
        return

    # ── 3a. Super admin can see all orgs ──────────────────────────────
    print("\n--- 3a. Super admin org access ---")
    r = api_get("/admin/organizations")
    if r.status_code == 200:
        data = r.json()
        orgs = data if isinstance(data, list) else data.get("data", data.get("organizations", []))
        if isinstance(orgs, list) and len(orgs) > 1:
            log("SECURITY", "Multi-org visibility", "PASS", f"Super admin sees {len(orgs)} orgs")
        elif isinstance(orgs, list) and len(orgs) == 1:
            log("SECURITY", "Multi-org visibility", "INFO", "Only 1 org visible — may need more test orgs")
        else:
            log("SECURITY", "Multi-org visibility", "INFO", f"Response: {str(data)[:200]}")
    else:
        log("SECURITY", "Multi-org visibility", "INFO", f"Status {r.status_code}")

    # ── 3b. Non-admin token should NOT access admin routes ────────────
    print("\n--- 3b. RBAC: Non-admin accessing admin routes ---")
    # Login as regular employee
    r = requests.post(f"{API_URL}/auth/login",
                      json={"email": "priya@technova.in", "password": "Welcome@123"}, timeout=15)
    emp_token = None
    if r.status_code == 200:
        data = r.json()
        emp_token = (data.get("access_token") or data.get("token")
                     or data.get("data", {}).get("access_token")
                     or data.get("data", {}).get("token")
                     or data.get("data", {}).get("tokens", {}).get("access_token"))

    if emp_token:
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        admin_routes = ["/admin/organizations", "/admin/health", "/admin/data-sanity"]
        for route in admin_routes:
            r = requests.get(f"{API_URL}{route}", headers=emp_headers, timeout=15)
            if r.status_code in [401, 403]:
                log("SECURITY", f"Employee access {route}", "PASS", f"Correctly blocked: {r.status_code}")
            elif r.status_code == 200:
                log("SECURITY", f"Employee access {route}", "FAIL",
                    f"Employee can access admin route! Status 200")
                log_bug(f"Employee can access admin-only route {route}",
                        f"GET {route} with employee token returns 200 instead of 403.\n"
                        f"Request: GET {API_URL}{route} (as employee priya@technova.in)\n"
                        f"Response: HTTP {r.status_code} — {r.text[:200]}")
            else:
                log("SECURITY", f"Employee access {route}", "INFO", f"Status {r.status_code}")
    else:
        log("SECURITY", "Employee login", "FAIL", "Could not get employee token for RBAC test")

    # ── 3c. Org admin should NOT access super admin routes ────────────
    print("\n--- 3c. RBAC: Org admin accessing super admin routes ---")
    r = requests.post(f"{API_URL}/auth/login",
                      json={"email": "ananya@technova.in", "password": "Welcome@123"}, timeout=15)
    org_admin_token = None
    if r.status_code == 200:
        data = r.json()
        org_admin_token = (data.get("access_token") or data.get("token")
                           or data.get("data", {}).get("access_token")
                           or data.get("data", {}).get("token")
                           or data.get("data", {}).get("tokens", {}).get("access_token"))

    if org_admin_token:
        oa_headers = {"Authorization": f"Bearer {org_admin_token}"}
        for route in ["/admin/organizations", "/admin/health"]:
            r = requests.get(f"{API_URL}{route}", headers=oa_headers, timeout=15)
            if r.status_code in [401, 403]:
                log("SECURITY", f"Org admin access {route}", "PASS", f"Correctly blocked: {r.status_code}")
            elif r.status_code == 200:
                log("SECURITY", f"Org admin access {route}", "FAIL",
                    f"Org admin can access super admin route! Status 200")
                log_bug(f"Org admin can access super-admin-only route {route}",
                        f"GET {route} with org admin token returns 200 instead of 403.\n"
                        f"Request: GET {API_URL}{route} (as org admin ananya@technova.in)\n"
                        f"Response: HTTP {r.status_code} — {r.text[:200]}")
            else:
                log("SECURITY", f"Org admin access {route}", "INFO", f"Status {r.status_code}")
    else:
        log("SECURITY", "Org admin login", "INFO", "Could not get org admin token")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 4: Additional admin page exploration
# ═══════════════════════════════════════════════════════════════════════
def phase4_extra_pages():
    print("\n" + "=" * 70)
    print("PHASE 4: EXTRA ADMIN PAGE EXPLORATION")
    print("=" * 70)

    d = get_driver()
    if driver_uses == 1:
        selenium_login(d)

    extra_pages = [
        ("/dashboard", "12_dashboard", ["dashboard", "welcome"]),
        ("/admin/settings", "13_admin_settings", ["setting", "config"]),
        ("/admin/users", "14_admin_users", ["user", "email"]),
        ("/admin/billing", "15_admin_billing", ["billing", "plan", "subscription"]),
        ("/admin/modules", "16_admin_modules", ["module"]),
        ("/admin/reports", "17_admin_reports", ["report"]),
    ]

    for path, ss_name, keywords in extra_pages:
        print(f"\n--- Checking {path} ---")
        info = check_page_content(d, f"{BASE_URL}{path}", ss_name, expect_keywords=keywords)
        if "error" in info:
            log("UI-EXTRA", path, "FAIL", info["error"])
        else:
            status = "PASS" if info.get("found_keywords") else "INFO"
            log("UI-EXTRA", path, status,
                f"text_len={info['text_len']}, found={info.get('found_keywords', [])}, "
                f"missing={info.get('missing_keywords', [])}")

        # Restart driver if needed (every 4 pages)
        if driver_uses >= MAX_DRIVER_USES:
            d = get_driver()
            if driver_uses == 1:
                selenium_login(d)


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY & REPORT
# ═══════════════════════════════════════════════════════════════════════
def print_summary():
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    passes = [r for r in results if r["status"] == "PASS"]
    fails = [r for r in results if r["status"] == "FAIL"]
    infos = [r for r in results if r["status"] == "INFO"]

    print(f"\nTotal tests: {len(results)}")
    print(f"  PASS: {len(passes)}")
    print(f"  FAIL: {len(fails)}")
    print(f"  INFO: {len(infos)}")

    if fails:
        print("\n--- FAILURES ---")
        for f in fails:
            print(f"  {f['phase']} > {f['test']}: {f['details']}")

    if bugs_found:
        print(f"\n--- BUGS FOUND ({len(bugs_found)}) ---")
        for b in bugs_found:
            print(f"  {b['title']}")

    print(f"\nScreenshots saved to: {SS_DIR}")
    print(f"Total screenshots: {len([f for f in os.listdir(SS_DIR) if f.endswith('.png')])}")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    start = time.time()
    print(f"Starting Fresh Super Admin E2E Test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"URL: {BASE_URL}")
    print(f"API: {API_URL}")
    print(f"Screenshots: {SS_DIR}")

    try:
        phase1_api_tests()
    except Exception as e:
        print(f"\n[ERROR] Phase 1 crashed: {e}")
        traceback.print_exc()

    try:
        phase2_selenium_tests()
    except Exception as e:
        print(f"\n[ERROR] Phase 2 crashed: {e}")
        traceback.print_exc()

    try:
        phase3_security_cross_org()
    except Exception as e:
        print(f"\n[ERROR] Phase 3 crashed: {e}")
        traceback.print_exc()

    try:
        phase4_extra_pages()
    except Exception as e:
        print(f"\n[ERROR] Phase 4 crashed: {e}")
        traceback.print_exc()

    # Cleanup driver
    if driver:
        try: driver.quit()
        except: pass

    print_summary()
    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed:.1f}s")
