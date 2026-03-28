"""
Test EXIT Module as EMPLOYEE (priya@technova.in)
Tests RBAC, visibility restrictions, and resignation flow for employee role.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ──────────────────────────────────────────────────────────────
LOGIN_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
EXIT_FRONTEND = "https://test-exit.empcloud.com"
EXIT_API = "https://test-exit-api.empcloud.com"
EMAIL = "priya@technova.in"
PASSWORD = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_exit_employee"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs = []
test_results = []


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {path}")
    return path


def record(test_name, status, details=""):
    test_results.append({"test": test_name, "status": status, "details": details})
    icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "INFO"
    log(f"  [{icon}] {test_name}: {details}")


def file_bug(title, body):
    bugs.append({"title": title, "body": body})
    log(f"  BUG: {title}")


def create_github_issues():
    if not bugs:
        log("No bugs to file.")
        return
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }
    for bug in bugs:
        payload = {
            "title": bug["title"],
            "body": bug["body"],
            "labels": ["bug", "exit-module", "rbac", "employee"],
        }
        try:
            r = requests.post(
                f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                headers=headers,
                json=payload,
                timeout=15,
            )
            if r.status_code == 201:
                log(f"  Issue created: {r.json().get('html_url')}")
            else:
                log(f"  Issue creation failed ({r.status_code}): {r.text[:200]}")
        except Exception as e:
            log(f"  Issue creation error: {e}")


def get_driver():
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
    return driver


# ── Step 1: Authenticate via API ────────────────────────────────────────
log("=" * 70)
log("EXIT MODULE - EMPLOYEE TESTING (priya@technova.in)")
log("=" * 70)

log("\n[1] Authenticating via API...")
try:
    resp = requests.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    log(f"  Login response: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        token = (
            data.get("token")
            or data.get("access_token")
            or (data.get("data", {}) or {}).get("token")
            or (data.get("data", {}) or {}).get("access_token")
            or ((data.get("data", {}) or {}).get("tokens", {}) or {}).get("access_token")
        )
        if not token:
            # Try nested structures
            for key in ["data", "result", "response"]:
                if isinstance(data.get(key), dict):
                    token = data[key].get("token") or data[key].get("access_token") or data[key].get("sso_token")
                    if not token and isinstance(data[key].get("tokens"), dict):
                        token = data[key]["tokens"].get("access_token")
                    if token:
                        break
        if token:
            log(f"  Token obtained: {token[:30]}...")
            record("API Login", "PASS", "Got auth token")
        else:
            log(f"  Response body: {json.dumps(data, indent=2)[:500]}")
            record("API Login", "FAIL", "No token in response")
            token = None
    else:
        log(f"  Response: {resp.text[:300]}")
        record("API Login", "FAIL", f"Status {resp.status_code}")
        token = None
except Exception as e:
    log(f"  Login error: {e}")
    record("API Login", "FAIL", str(e))
    token = None

# ── Step 2: SSO into Exit module via browser ────────────────────────────
log("\n[2] SSO into Exit module...")
driver = get_driver()
try:
    sso_url = f"{EXIT_FRONTEND}?sso_token={token}" if token else EXIT_FRONTEND
    log(f"  Navigating to: {sso_url[:80]}...")
    driver.get(sso_url)
    time.sleep(4)
    screenshot(driver, "01_sso_landing")

    page_title = driver.title
    current_url = driver.current_url
    page_source_snippet = driver.page_source[:2000]
    log(f"  Page title: {page_title}")
    log(f"  Current URL: {current_url}")

    # Check if SSO worked - are we on exit module or login page?
    if "login" in current_url.lower() or "sign" in current_url.lower():
        record("SSO Login", "FAIL", f"Redirected to login: {current_url}")
        file_bug(
            "[Exit Employee] SSO token not accepted by Exit module",
            f"**Steps:** Login via API as employee, use sso_token to access Exit module.\n"
            f"**Expected:** SSO should authenticate employee into Exit module.\n"
            f"**Actual:** Redirected to login page: {current_url}\n"
            f"**User:** {EMAIL}\n**URL:** {sso_url[:80]}...",
        )
    else:
        record("SSO Login", "PASS", f"Landed on: {current_url}")

    screenshot(driver, "02_after_sso")

except Exception as e:
    log(f"  SSO error: {e}")
    screenshot(driver, "02_sso_error")
    record("SSO Login", "FAIL", str(e))

# ── Step 3: What does a non-exiting employee see? ───────────────────────
log("\n[3] Checking what non-exiting employee sees...")
try:
    time.sleep(2)
    body_text = driver.find_element(By.TAG_NAME, "body").text
    screenshot(driver, "03_employee_main_view")
    log(f"  Page text (first 500 chars): {body_text[:500]}")

    # Check for dashboard/admin elements that shouldn't be visible
    has_content = len(body_text.strip()) > 50
    if has_content:
        record("Employee View", "INFO", f"Employee sees content: {body_text[:200]}")
    else:
        record("Employee View", "INFO", "Employee sees minimal/empty page")

    # Look for navigation items
    nav_items = driver.find_elements(By.CSS_SELECTOR, "nav a, .sidebar a, .menu-item, .nav-item, [role='menuitem']")
    nav_texts = [n.text.strip() for n in nav_items if n.text.strip()]
    log(f"  Nav items visible: {nav_texts[:20]}")
    screenshot(driver, "03b_nav_items")

    if nav_texts:
        record("Employee Navigation", "INFO", f"Visible nav: {', '.join(nav_texts[:15])}")

except Exception as e:
    log(f"  Error checking view: {e}")
    screenshot(driver, "03_error")

# ── Step 4: Try accessing other employees' exit details ─────────────────
log("\n[4] Checking if employee can see other employees' exit details...")

# Try various API endpoints that should be restricted
api_headers = {"Authorization": f"Bearer {token}"} if token else {}

exit_api_endpoints = [
    ("/api/v1/exits", "List all exits"),
    ("/api/v1/exit/list", "Exit list"),
    ("/api/v1/employees/exits", "Employee exits"),
    ("/api/v1/exit/all", "All exits"),
    ("/api/v1/separations", "Separations list"),
    ("/api/v1/separation/list", "Separation list"),
    ("/api/v1/resignations", "All resignations"),
    ("/api/v1/resignation/list", "Resignation list"),
    ("/api/v1/exit-interviews", "Exit interviews"),
    ("/api/v1/exit-interview/list", "Exit interview list"),
    ("/api/v1/offboarding", "Offboarding list"),
    ("/api/v1/offboarding/list", "Offboarding list alt"),
]

for endpoint, desc in exit_api_endpoints:
    try:
        r = requests.get(f"{EXIT_API}{endpoint}", headers=api_headers, timeout=10)
        log(f"  {desc} ({endpoint}): {r.status_code}")
        if r.status_code == 200:
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            # Check if response contains other employees' data
            data_str = json.dumps(data)[:1000]
            has_records = False
            records = data.get("data") or data.get("results") or data.get("items") or data.get("list") or []
            if isinstance(records, list) and len(records) > 0:
                has_records = True
                log(f"    Found {len(records)} records")
                log(f"    Sample: {json.dumps(records[0])[:300]}")
            elif isinstance(data, list) and len(data) > 0:
                has_records = True
                records = data
                log(f"    Found {len(data)} records (array)")

            if has_records:
                record(f"API {desc}", "FAIL", f"Employee can see {len(records)} records via {endpoint}")
                file_bug(
                    f"[Exit Employee] RBAC: Employee can access {desc} ({endpoint})",
                    f"**Severity:** High\n"
                    f"**Steps:** Login as employee ({EMAIL}), call GET {EXIT_API}{endpoint}\n"
                    f"**Expected:** Employee should NOT see other employees' exit data.\n"
                    f"**Actual:** Returns {len(records)} records. Sample: {json.dumps(records[0])[:300] if records else 'N/A'}\n"
                    f"**Impact:** RBAC violation - employee can view confidential exit information.",
                )
            else:
                record(f"API {desc}", "PASS", f"200 but empty/no records")
        elif r.status_code in (401, 403, 404):
            record(f"API {desc}", "PASS", f"Correctly blocked: {r.status_code}")
        else:
            record(f"API {desc}", "INFO", f"Status: {r.status_code}")
    except Exception as e:
        log(f"  {desc} error: {e}")

# ── Step 5: Check F&F (Full & Final) settlements ────────────────────────
log("\n[5] Checking if employee can see F&F settlements...")

fnf_endpoints = [
    ("/api/v1/fnf", "F&F list"),
    ("/api/v1/fnf/list", "F&F list alt"),
    ("/api/v1/full-and-final", "Full and Final"),
    ("/api/v1/settlements", "Settlements"),
    ("/api/v1/settlement/list", "Settlement list"),
    ("/api/v1/fnf/settlements", "F&F settlements"),
    ("/api/v1/exit/fnf", "Exit F&F"),
]

for endpoint, desc in fnf_endpoints:
    try:
        r = requests.get(f"{EXIT_API}{endpoint}", headers=api_headers, timeout=10)
        log(f"  {desc} ({endpoint}): {r.status_code}")
        if r.status_code == 200:
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            records = data.get("data") or data.get("results") or data.get("items") or data.get("list") or []
            if isinstance(records, list) and len(records) > 0:
                record(f"API {desc}", "FAIL", f"Employee can see {len(records)} F&F records")
                file_bug(
                    f"[Exit Employee] RBAC: Employee can access F&F settlements ({endpoint})",
                    f"**Severity:** Critical\n"
                    f"**Steps:** Login as employee ({EMAIL}), call GET {EXIT_API}{endpoint}\n"
                    f"**Expected:** Employee should NOT see F&F settlement data.\n"
                    f"**Actual:** Returns {len(records)} F&F records.\n"
                    f"**Impact:** Financial data exposure - RBAC violation.",
                )
            elif isinstance(data, list) and len(data) > 0:
                record(f"API {desc}", "FAIL", f"Employee can see {len(data)} F&F records")
                file_bug(
                    f"[Exit Employee] RBAC: Employee can access F&F settlements ({endpoint})",
                    f"**Severity:** Critical\n"
                    f"**Steps:** Login as employee ({EMAIL}), call GET {EXIT_API}{endpoint}\n"
                    f"**Expected:** Employee should NOT see F&F settlement data.\n"
                    f"**Actual:** Returns {len(data)} F&F records.\n"
                    f"**Impact:** Financial data exposure - RBAC violation.",
                )
            else:
                record(f"API {desc}", "PASS", f"200 but no records exposed")
        elif r.status_code in (401, 403, 404):
            record(f"API {desc}", "PASS", f"Correctly blocked: {r.status_code}")
        else:
            record(f"API {desc}", "INFO", f"Status: {r.status_code}")
    except Exception as e:
        log(f"  {desc} error: {e}")

# ── Step 6: Check flight risk scores ────────────────────────────────────
log("\n[6] Checking if employee can see flight risk scores (CRITICAL RBAC)...")

risk_endpoints = [
    ("/api/v1/flight-risk", "Flight risk scores"),
    ("/api/v1/flight-risk/list", "Flight risk list"),
    ("/api/v1/risk-scores", "Risk scores"),
    ("/api/v1/risk/scores", "Risk scores alt"),
    ("/api/v1/attrition/risk", "Attrition risk"),
    ("/api/v1/attrition-risk", "Attrition risk alt"),
    ("/api/v1/analytics/flight-risk", "Analytics flight risk"),
    ("/api/v1/employees/risk", "Employee risk"),
    ("/api/v1/exit/risk-analysis", "Exit risk analysis"),
    ("/api/v1/predictions/attrition", "Attrition predictions"),
]

for endpoint, desc in risk_endpoints:
    try:
        r = requests.get(f"{EXIT_API}{endpoint}", headers=api_headers, timeout=10)
        log(f"  {desc} ({endpoint}): {r.status_code}")
        if r.status_code == 200:
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            data_str = json.dumps(data)[:500]
            records = data.get("data") or data.get("results") or data.get("items") or data.get("list") or data.get("scores") or []
            if isinstance(records, list) and len(records) > 0:
                record(f"API {desc}", "FAIL", f"CRITICAL: Employee sees {len(records)} risk records!")
                file_bug(
                    f"[Exit Employee] CRITICAL RBAC: Employee can access flight risk scores ({endpoint})",
                    f"**Severity:** Critical\n"
                    f"**Steps:** Login as employee ({EMAIL}), call GET {EXIT_API}{endpoint}\n"
                    f"**Expected:** Employee must NOT see flight risk / attrition prediction data.\n"
                    f"**Actual:** Returns {len(records)} risk score records.\n"
                    f"**Sample:** {json.dumps(records[0])[:300] if records else 'N/A'}\n"
                    f"**Impact:** CRITICAL - Employees can see who is flagged as flight risk. "
                    f"This is highly confidential HR analytics data.",
                )
            elif isinstance(data, list) and len(data) > 0:
                record(f"API {desc}", "FAIL", f"CRITICAL: Employee sees {len(data)} risk records!")
                file_bug(
                    f"[Exit Employee] CRITICAL RBAC: Employee can access flight risk scores ({endpoint})",
                    f"**Severity:** Critical\n"
                    f"**Steps:** Login as employee ({EMAIL}), call GET {EXIT_API}{endpoint}\n"
                    f"**Expected:** Employee must NOT see flight risk data.\n"
                    f"**Actual:** Returns {len(data)} risk records.\n"
                    f"**Impact:** CRITICAL RBAC violation.",
                )
            else:
                record(f"API {desc}", "PASS", f"200 but no risk data exposed")
        elif r.status_code in (401, 403, 404):
            record(f"API {desc}", "PASS", f"Correctly blocked: {r.status_code}")
        else:
            record(f"API {desc}", "INFO", f"Status: {r.status_code}")
    except Exception as e:
        log(f"  {desc} error: {e}")

# ── Step 7: Check admin dashboard access ────────────────────────────────
log("\n[7] Checking if employee can access admin dashboard...")

admin_urls = [
    f"{EXIT_FRONTEND}/admin",
    f"{EXIT_FRONTEND}/admin/dashboard",
    f"{EXIT_FRONTEND}/dashboard",
    f"{EXIT_FRONTEND}/admin/exits",
    f"{EXIT_FRONTEND}/admin/separations",
    f"{EXIT_FRONTEND}/admin/settings",
    f"{EXIT_FRONTEND}/admin/reports",
    f"{EXIT_FRONTEND}/analytics",
    f"{EXIT_FRONTEND}/reports",
]

for url in admin_urls:
    try:
        driver.get(url)
        time.sleep(3)
        curr = driver.current_url
        body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
        page_name = url.replace(EXIT_FRONTEND, "")
        safe_name = page_name.replace("/", "_").strip("_") or "root"
        screenshot(driver, f"07_admin_{safe_name}")
        log(f"  {url} -> {curr}")
        log(f"    Content: {body_text[:200]}")

        # Check if blocked
        blocked = (
            "login" in curr.lower()
            or "unauthorized" in body_text.lower()
            or "403" in body_text
            or "access denied" in body_text.lower()
            or "not authorized" in body_text.lower()
            or "permission" in body_text.lower()
            or curr.rstrip("/") == EXIT_FRONTEND.rstrip("/")  # redirected to home
        )

        if not blocked and len(body_text.strip()) > 50:
            # Check for admin-specific content
            admin_keywords = ["dashboard", "all employees", "reports", "analytics", "settings", "configuration", "manage"]
            has_admin_content = any(kw in body_text.lower() for kw in admin_keywords)
            if has_admin_content:
                record(f"Admin Access {page_name}", "FAIL", f"Employee can access admin page!")
                file_bug(
                    f"[Exit Employee] RBAC: Employee can access admin page {page_name}",
                    f"**Severity:** High\n"
                    f"**Steps:** Login as employee ({EMAIL}) via SSO, navigate to {url}\n"
                    f"**Expected:** Employee should be blocked from admin pages.\n"
                    f"**Actual:** Page loads with admin content.\n"
                    f"**Content snippet:** {body_text[:300]}\n"
                    f"**Impact:** RBAC violation - employee accessing admin functionality.",
                )
            else:
                record(f"Admin Access {page_name}", "INFO", f"Page loads but may not have admin content")
        else:
            record(f"Admin Access {page_name}", "PASS", f"Blocked/redirected appropriately")
    except Exception as e:
        log(f"  Error on {url}: {e}")

# Also check admin API endpoints
admin_api_endpoints = [
    ("/api/v1/admin/dashboard", "Admin dashboard API"),
    ("/api/v1/admin/exits", "Admin exits API"),
    ("/api/v1/admin/reports", "Admin reports API"),
    ("/api/v1/admin/settings", "Admin settings API"),
    ("/api/v1/dashboard/stats", "Dashboard stats"),
    ("/api/v1/dashboard", "Dashboard"),
    ("/api/v1/reports/exit", "Exit reports"),
    ("/api/v1/analytics/exit", "Exit analytics"),
]

for endpoint, desc in admin_api_endpoints:
    try:
        r = requests.get(f"{EXIT_API}{endpoint}", headers=api_headers, timeout=10)
        log(f"  {desc} ({endpoint}): {r.status_code}")
        if r.status_code == 200:
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            data_str = json.dumps(data)[:500]
            if data and not (isinstance(data, dict) and len(data) <= 1 and "message" in data):
                record(f"API {desc}", "FAIL", f"Employee can access admin API endpoint")
                file_bug(
                    f"[Exit Employee] RBAC: Employee can access {desc} ({endpoint})",
                    f"**Severity:** High\n"
                    f"**Steps:** Login as employee ({EMAIL}), call GET {EXIT_API}{endpoint}\n"
                    f"**Expected:** Employee should NOT access admin endpoints.\n"
                    f"**Actual:** Returns data: {data_str[:300]}\n"
                    f"**Impact:** Admin data exposed to employee role.",
                )
            else:
                record(f"API {desc}", "PASS", f"200 but no substantial data")
        elif r.status_code in (401, 403, 404):
            record(f"API {desc}", "PASS", f"Correctly blocked: {r.status_code}")
        else:
            record(f"API {desc}", "INFO", f"Status: {r.status_code}")
    except Exception as e:
        log(f"  {desc} error: {e}")

# ── Step 8: Check if employee can initiate resignation ──────────────────
log("\n[8] Checking if employee can initiate resignation...")

# Try via UI
try:
    driver.get(f"{EXIT_FRONTEND}?sso_token={token}" if token else EXIT_FRONTEND)
    time.sleep(3)

    # Look for resignation-related buttons/links
    resign_selectors = [
        "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'resign')]",
        "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'resign')]",
        "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'initiate')]",
        "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'separation')]",
        "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'exit')]",
        "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'apply for resignation')]",
        "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit resignation')]",
    ]

    found_resign = False
    for sel in resign_selectors:
        try:
            elements = driver.find_elements(By.XPATH, sel)
            for el in elements:
                if el.is_displayed():
                    log(f"  Found resignation element: '{el.text}' ({el.tag_name})")
                    found_resign = True
                    screenshot(driver, "08_resignation_button_found")
        except:
            pass

    if found_resign:
        record("Resignation Initiation UI", "PASS", "Resignation option found for employee")
    else:
        record("Resignation Initiation UI", "INFO", "No resignation button/link found on main page")
        # Try navigating to potential resignation pages
        resign_pages = [
            f"{EXIT_FRONTEND}/resignation",
            f"{EXIT_FRONTEND}/resign",
            f"{EXIT_FRONTEND}/my-resignation",
            f"{EXIT_FRONTEND}/employee/resign",
            f"{EXIT_FRONTEND}/self-service/resignation",
            f"{EXIT_FRONTEND}/separation/initiate",
        ]
        for rp in resign_pages:
            try:
                driver.get(rp)
                time.sleep(2)
                body = driver.find_element(By.TAG_NAME, "body").text[:300]
                curr = driver.current_url
                safe = rp.replace(EXIT_FRONTEND, "").replace("/", "_").strip("_")
                screenshot(driver, f"08_resign_{safe}")
                log(f"  {rp} -> {curr} | Content: {body[:150]}")
                if len(body.strip()) > 50 and "login" not in curr.lower():
                    record(f"Resignation Page {rp.replace(EXIT_FRONTEND,'')}", "INFO", f"Page accessible")
            except Exception as e:
                log(f"  {rp} error: {e}")

except Exception as e:
    log(f"  Resignation UI check error: {e}")
    screenshot(driver, "08_resign_error")

# Try resignation via API
resign_api_endpoints = [
    ("GET", "/api/v1/resignation/my", "My resignation status"),
    ("GET", "/api/v1/my-resignation", "My resignation alt"),
    ("GET", "/api/v1/employee/resignation", "Employee resignation"),
    ("GET", "/api/v1/self/resignation", "Self resignation"),
    ("GET", "/api/v1/exit/my-status", "My exit status"),
]

for method, endpoint, desc in resign_api_endpoints:
    try:
        r = requests.get(f"{EXIT_API}{endpoint}", headers=api_headers, timeout=10)
        log(f"  {desc} ({endpoint}): {r.status_code}")
        if r.status_code == 200:
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            log(f"    Response: {json.dumps(data)[:300]}")
            record(f"API {desc}", "INFO", f"Endpoint exists, status 200")
        elif r.status_code in (401, 403):
            record(f"API {desc}", "INFO", f"Blocked: {r.status_code}")
        elif r.status_code == 404:
            record(f"API {desc}", "INFO", f"Not found (404)")
        else:
            record(f"API {desc}", "INFO", f"Status: {r.status_code}")
    except Exception as e:
        log(f"  {desc} error: {e}")

# ── Final screenshot of all pages visited ───────────────────────────────
log("\n[9] Final page state...")
try:
    screenshot(driver, "09_final_state")
except:
    pass

# ── Cleanup ─────────────────────────────────────────────────────────────
try:
    driver.quit()
except:
    pass

# ── Summary ─────────────────────────────────────────────────────────────
log("\n" + "=" * 70)
log("TEST SUMMARY")
log("=" * 70)

pass_count = sum(1 for t in test_results if t["status"] == "PASS")
fail_count = sum(1 for t in test_results if t["status"] == "FAIL")
info_count = sum(1 for t in test_results if t["status"] == "INFO")

log(f"  PASS: {pass_count} | FAIL: {fail_count} | INFO: {info_count}")
log(f"  Bugs to file: {len(bugs)}")

for t in test_results:
    icon = "PASS" if t["status"] == "PASS" else "FAIL" if t["status"] == "FAIL" else "INFO"
    log(f"  [{icon}] {t['test']}: {t['details'][:100]}")

# ── File bugs ───────────────────────────────────────────────────────────
if bugs:
    log(f"\nFiling {len(bugs)} bug(s) to GitHub...")
    create_github_issues()

log("\nDone.")
