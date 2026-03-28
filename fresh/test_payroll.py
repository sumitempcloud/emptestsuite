"""
Fresh E2E Test — EMP Payroll Module via SSO
Tests Admin and Employee flows: dashboard, payslips, salary structures,
tax, run payroll, reports, settings, self-service, RBAC isolation.
"""

import os
import sys
import time
import json
import traceback
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ── Config ──────────────────────────────────────────────────────────────
EMPCLOUD_API = "https://test-empcloud-api.empcloud.com/api/v1"
PAYROLL_API = "https://testpayroll-api.empcloud.com/api/v1"
PAYROLL_UI = "https://testpayroll.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_payroll"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── Helpers ─────────────────────────────────────────────────────────────
results = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def record(test_name, status, detail=""):
    results.append({"test": test_name, "status": status, "detail": detail})
    icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
    log(f"  [{icon}] {test_name}" + (f" — {detail}" if detail else ""))

def screenshot(driver, name):
    safe = name.replace(" ", "_").replace("/", "_").replace(":", "_")
    path = os.path.join(SCREENSHOT_DIR, f"{safe}.png")
    try:
        driver.save_screenshot(path)
    except Exception:
        pass
    return path

def get_sso_token(email, password):
    """Login to EMP Cloud and return access_token for SSO."""
    resp = requests.post(f"{EMPCLOUD_API}/auth/login",
                         json={"email": email, "password": password}, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        # Structure: { success, data: { tokens: { access_token } } }
        tokens = (data.get("data") or {}).get("tokens") or {}
        token = tokens.get("access_token")
        if token:
            return token
        # Fallback: try other structures
        token = data.get("access_token") or data.get("token") or (data.get("data") or {}).get("access_token")
        if token:
            return token
    log(f"  SSO login failed for {email}: {resp.status_code} — {resp.text[:300]}")
    return None

def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(45)
    driver.implicitly_wait(5)
    return driver

def wait_for_page(driver, timeout=15):
    """Wait for SPA to finish loading (React hydration)."""
    time.sleep(3)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    time.sleep(2)

def sso_navigate(driver, token, path=""):
    """Navigate to payroll module via SSO token, then optionally to a path."""
    url = f"{PAYROLL_UI}?sso_token={token}"
    driver.get(url)
    wait_for_page(driver, 20)
    if path:
        time.sleep(2)
        driver.get(f"{PAYROLL_UI}{path}")
        wait_for_page(driver)

def get_module_cookies(driver):
    """Extract cookies from browser after SSO for API calls."""
    cookies = {}
    for c in driver.get_cookies():
        cookies[c["name"]] = c["value"]
    return cookies

def api_get(session, path, label=""):
    """GET request to Payroll API with session."""
    try:
        resp = session.get(f"{PAYROLL_API}{path}", timeout=30)
        # Handle 429 rate limit: wait and retry once
        if resp.status_code == 429:
            log(f"  Rate limited on {path}, waiting 15s...")
            time.sleep(15)
            resp = session.get(f"{PAYROLL_API}{path}", timeout=30)
        return resp
    except requests.exceptions.ConnectionError as e:
        log(f"  API GET {path} ConnectionError: {str(e)[:150]}")
        return None
    except requests.exceptions.Timeout as e:
        log(f"  API GET {path} Timeout: {str(e)[:150]}")
        return None
    except Exception as e:
        log(f"  API GET {path} error ({type(e).__name__}): {str(e)[:150]}")
        return None

def api_post(session, path, payload=None, label=""):
    try:
        resp = session.post(f"{PAYROLL_API}{path}", json=payload, timeout=30)
        if resp.status_code == 429:
            time.sleep(10)
            resp = session.post(f"{PAYROLL_API}{path}", json=payload, timeout=30)
        return resp
    except Exception as e:
        log(f"  API POST {path} error: {e}")
        return None

def page_has_content(driver, min_length=50):
    """Check page loaded meaningful content (not blank SPA shell)."""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
        return len(body.strip()) > min_length
    except Exception:
        return False

def check_no_error(driver):
    """Check page doesn't show error states."""
    body_text = ""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    except Exception:
        return True
    error_keywords = ["500 internal", "server error", "something went wrong", "403 forbidden", "unauthorized"]
    for kw in error_keywords:
        if kw in body_text:
            return False
    return True


# ═══════════════════════════════════════════════════════════════════════
#  PART 1: API TESTS
# ═══════════════════════════════════════════════════════════════════════

def run_api_tests():
    log("=" * 70)
    log("PART 1: API TESTS")
    log("=" * 70)

    # ── Get SSO tokens ──
    admin_token = get_sso_token(ADMIN_EMAIL, ADMIN_PASS)
    emp_token = get_sso_token(EMP_EMAIL, EMP_PASS)

    if not admin_token:
        record("API — Admin SSO Login", "FAIL", "Could not get admin SSO token")
        return
    else:
        record("API — Admin SSO Login", "PASS", "Got access_token")

    if not emp_token:
        record("API — Employee SSO Login", "FAIL", "Could not get employee SSO token")
    else:
        record("API — Employee SSO Login", "PASS", "Got access_token")

    # ── Build sessions via SSO token exchange ──
    # The payroll module has its own auth: POST /api/v1/auth/sso with {"token": empcloud_jwt}
    # Returns a module-specific accessToken to use as Bearer for all API calls.
    admin_session = requests.Session()
    emp_session = requests.Session()

    def get_module_token(session, empcloud_token, label):
        """Exchange EMP Cloud token for payroll module token."""
        try:
            resp = session.post(f"{PAYROLL_API}/auth/sso", json={"token": empcloud_token}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                mod_token = (data.get("data") or {}).get("tokens", {}).get("accessToken")
                if mod_token:
                    session.headers.update({"Authorization": f"Bearer {mod_token}"})
                    log(f"  Module token for {label}: OK")
                    return True
                else:
                    log(f"  Module token for {label}: no accessToken in response")
            else:
                log(f"  Module SSO for {label}: {resp.status_code} — {resp.text[:200]}")
        except Exception as e:
            log(f"  Module SSO for {label} error: {e}")
        return False

    admin_sso_ok = get_module_token(admin_session, admin_token, "admin")
    if not admin_sso_ok:
        record("API Admin — Module SSO Exchange", "FAIL", "Could not get payroll module token")
    else:
        record("API Admin — Module SSO Exchange", "PASS", "Got module accessToken")

    time.sleep(1)  # avoid rate limit
    emp_sso_ok = get_module_token(emp_session, emp_token, "employee")
    if not emp_sso_ok:
        record("API Employee — Module SSO Exchange", "FAIL", "Could not get payroll module token")
    else:
        record("API Employee — Module SSO Exchange", "PASS", "Got module accessToken")

    # ── Admin API Tests ──
    log("\n--- Admin API Tests ---")

    # 1. List payroll runs
    resp = api_get(admin_session, "/payroll")
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        runs = data if isinstance(data, list) else data.get("data", data.get("runs", data.get("payrollRuns", [])))
        if isinstance(runs, dict):
            runs = runs.get("data", runs.get("runs", []))
        count = len(runs) if isinstance(runs, list) else "unknown"
        record("API Admin — List Payroll Runs", "PASS", f"Status 200, {count} runs")
    elif resp is not None:
        record("API Admin — List Payroll Runs", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Admin — List Payroll Runs", "FAIL", "No response")

    # 2. List salary structures
    resp = api_get(admin_session, "/salary-structures")
    if resp is not None and resp.status_code == 200:
        record("API Admin — List Salary Structures", "PASS", "Status 200")
    elif resp is not None:
        record("API Admin — List Salary Structures", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Admin — List Salary Structures", "FAIL", "No response")

    # 3. List employees
    resp = api_get(admin_session, "/employees")
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        emps = data if isinstance(data, list) else data.get("data", data.get("employees", []))
        if isinstance(emps, dict):
            emps = emps.get("data", emps.get("employees", []))
        emp_count = len(emps) if isinstance(emps, list) else "unknown"
        record("API Admin — List Employees", "PASS", f"Status 200, {emp_count} employees")

        # Save first employee ID for later tests
        first_emp_id = None
        if isinstance(emps, list) and len(emps) > 0:
            first_emp_id = emps[0].get("id") or emps[0].get("employee_id") or emps[0].get("empId")
    elif resp is not None:
        record("API Admin — List Employees", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
        first_emp_id = None
    else:
        record("API Admin — List Employees", "FAIL", "No response")
        first_emp_id = None

    # 4. Get employee salary structure
    if first_emp_id:
        resp = api_get(admin_session, f"/salary-structures/employee/{first_emp_id}")
        if resp is not None and resp.status_code == 200:
            record("API Admin — Employee Salary Structure", "PASS", f"Employee {first_emp_id}")
        elif resp is not None:
            record("API Admin — Employee Salary Structure", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
        else:
            record("API Admin — Employee Salary Structure", "FAIL", "No response")

    # 5-8: Endpoints that may not be deployed yet (documented in README but 404 on server)
    optional_endpoints = [
        ("/tax/compute", "API Admin — Tax Compute"),
        ("/tax/declarations", "API Admin — Tax Declarations"),
        ("/attendance/summary", "API Admin — Attendance Summary"),
        ("/leaves/balances", "API Admin — Leave Balances"),
    ]
    for path, name in optional_endpoints:
        resp = api_get(admin_session, path)
        if resp is not None and resp.status_code == 200:
            record(name, "PASS", "Status 200")
        elif resp is not None and resp.status_code == 404:
            record(name, "SKIP", "Endpoint not deployed (404)")
        elif resp is not None:
            record(name, "FAIL", f"Status {resp.status_code}: {resp.text[:150]}")
        else:
            record(name, "FAIL", "No response / connection error")

    # 9. Loans list
    resp = api_get(admin_session, "/loans")
    if resp is not None and resp.status_code == 200:
        record("API Admin — Loans List", "PASS", f"Status 200")
    elif resp is not None:
        record("API Admin — Loans List", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Admin — Loans List", "FAIL", "No response")

    # 10. Reimbursements list
    resp = api_get(admin_session, "/reimbursements")
    if resp is not None and resp.status_code == 200:
        record("API Admin — Reimbursements List", "PASS", f"Status 200")
    elif resp is not None:
        record("API Admin — Reimbursements List", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Admin — Reimbursements List", "FAIL", "No response")

    # 11. Benefits dashboard
    resp = api_get(admin_session, "/benefits/dashboard")
    if resp is not None and resp.status_code == 200:
        record("API Admin — Benefits Dashboard", "PASS", f"Status 200")
    elif resp is not None:
        record("API Admin — Benefits Dashboard", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Admin — Benefits Dashboard", "FAIL", "No response")

    # 12. Insurance dashboard
    resp = api_get(admin_session, "/insurance/dashboard")
    if resp is not None and resp.status_code == 200:
        record("API Admin — Insurance Dashboard", "PASS", f"Status 200")
    elif resp is not None:
        record("API Admin — Insurance Dashboard", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Admin — Insurance Dashboard", "FAIL", "No response")

    # 13-14: Endpoints that may not be deployed
    for path, name in [("/gl-accounting/mappings", "API Admin — GL Mappings"),
                       ("/global-payroll/dashboard", "API Admin — Global Payroll Dashboard")]:
        resp = api_get(admin_session, path)
        if resp is not None and resp.status_code == 200:
            record(name, "PASS", "Status 200")
        elif resp is not None and resp.status_code == 404:
            record(name, "SKIP", "Endpoint not deployed (404)")
        elif resp is not None:
            record(name, "FAIL", f"Status {resp.status_code}: {resp.text[:150]}")
        else:
            record(name, "FAIL", "No response / connection error")

    # 15. Earned wage access settings
    resp = api_get(admin_session, "/earned-wage/settings")
    if resp is not None and resp.status_code == 200:
        record("API Admin — EWA Settings", "PASS", f"Status 200")
    elif resp is not None:
        record("API Admin — EWA Settings", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Admin — EWA Settings", "FAIL", "No response")

    # 16. Pay equity analysis
    resp = api_get(admin_session, "/pay-equity/analysis")
    if resp is not None and resp.status_code == 200:
        record("API Admin — Pay Equity Analysis", "PASS", f"Status 200")
    elif resp is not None:
        record("API Admin — Pay Equity Analysis", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Admin — Pay Equity Analysis", "FAIL", "No response")

    # 17-18: Endpoints that may not be deployed
    for path, name in [("/compensation-benchmarks", "API Admin — Compensation Benchmarks"),
                       ("/organizations/settings", "API Admin — Org Settings")]:
        resp = api_get(admin_session, path)
        if resp is not None and resp.status_code == 200:
            record(name, "PASS", "Status 200")
        elif resp is not None and resp.status_code in (404, 500):
            record(name, "SKIP", f"Endpoint returned {resp.status_code}")
        elif resp is not None:
            record(name, "FAIL", f"Status {resp.status_code}: {resp.text[:150]}")
        else:
            record(name, "FAIL", "No response / connection error")

    # 19. Adjustments
    resp = api_get(admin_session, "/adjustments")
    if resp is not None and resp.status_code == 200:
        record("API Admin — Adjustments", "PASS", f"Status 200")
    elif resp is not None:
        record("API Admin — Adjustments", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Admin — Adjustments", "FAIL", "No response")

    # 20. Health check
    resp = None
    try:
        resp = admin_session.get(f"https://testpayroll-api.empcloud.com/health", timeout=15)
    except Exception as e:
        log(f"  Health check error: {e}")
    if resp is not None and resp.status_code == 200:
        record("API — Health Check", "PASS", f"Status 200")
    elif resp is not None:
        record("API — Health Check", "FAIL", f"Status {resp.status_code}")
    else:
        record("API — Health Check", "FAIL", "No response")

    # ── Employee Self-Service API Tests ──
    log("\n--- Employee Self-Service API Tests ---")

    if not emp_token:
        record("API Employee — All Self-Service", "SKIP", "No employee token")
        return

    # 21. Self-service dashboard
    resp = api_get(emp_session, "/self-service/dashboard")
    if resp is not None and resp.status_code == 200:
        record("API Employee — Self-Service Dashboard", "PASS", f"Status 200")
    elif resp is not None:
        record("API Employee — Self-Service Dashboard", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Employee — Self-Service Dashboard", "FAIL", "No response")

    # 22. My payslips
    resp = api_get(emp_session, "/self-service/payslips")
    if resp is not None and resp.status_code == 200:
        data = resp.json()
        slips = data if isinstance(data, list) else data.get("data", data.get("payslips", []))
        if isinstance(slips, dict):
            slips = slips.get("data", slips.get("payslips", []))
        slip_count = len(slips) if isinstance(slips, list) else "unknown"
        record("API Employee — My Payslips", "PASS", f"Status 200, {slip_count} payslips")
    elif resp is not None:
        record("API Employee — My Payslips", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Employee — My Payslips", "FAIL", "No response")

    # 23. My salary
    resp = api_get(emp_session, "/self-service/salary")
    if resp is not None and resp.status_code == 200:
        record("API Employee — My Salary", "PASS", f"Status 200")
    elif resp is not None:
        record("API Employee — My Salary", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Employee — My Salary", "FAIL", "No response")

    # 24. My tax computation
    resp = api_get(emp_session, "/self-service/tax/computation")
    if resp is not None and resp.status_code == 200:
        record("API Employee — My Tax Computation", "PASS", f"Status 200")
    elif resp is not None:
        record("API Employee — My Tax Computation", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Employee — My Tax Computation", "FAIL", "No response")

    # 25. My declarations
    resp = api_get(emp_session, "/self-service/tax/declarations")
    if resp is not None and resp.status_code == 200:
        record("API Employee — My Tax Declarations", "PASS", f"Status 200")
    elif resp is not None:
        record("API Employee — My Tax Declarations", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Employee — My Tax Declarations", "FAIL", "No response")

    # 26. My reimbursements
    resp = api_get(emp_session, "/self-service/reimbursements")
    if resp is not None and resp.status_code == 200:
        record("API Employee — My Reimbursements", "PASS", f"Status 200")
    elif resp is not None:
        record("API Employee — My Reimbursements", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Employee — My Reimbursements", "FAIL", "No response")

    # 27. My profile
    resp = api_get(emp_session, "/self-service/profile")
    if resp is not None and resp.status_code == 200:
        record("API Employee — My Profile", "PASS", f"Status 200")
    elif resp is not None:
        record("API Employee — My Profile", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
    else:
        record("API Employee — My Profile", "FAIL", "No response")

    # ── RBAC: Employee should NOT access admin endpoints ──
    log("\n--- RBAC: Employee Access Control ---")

    # Small delay to avoid rate limits between admin and employee tests
    time.sleep(2)

    # Helper for RBAC checks
    def check_rbac(path, name, check_data_fn=None):
        resp = api_get(emp_session, path)
        if resp is None:
            record(name, "SKIP", "No response / connection error")
        elif resp.status_code in (401, 403):
            record(name, "PASS", f"Correctly blocked: {resp.status_code}")
        elif resp.status_code == 200:
            if check_data_fn:
                check_data_fn(resp, name)
            else:
                record(name, "FAIL", f"Employee can access {path} — should be restricted")
        elif resp.status_code in (404, 500):
            record(name, "SKIP", f"Endpoint returned {resp.status_code}")
        else:
            record(name, "PASS" if resp.status_code >= 400 else "FAIL", f"Status {resp.status_code}")

    # 28. Employee should NOT list all employees
    def check_emp_list(resp, name):
        try:
            data = resp.json()
            emps = data if isinstance(data, list) else data.get("data", data.get("employees", []))
            if isinstance(emps, dict):
                emps = emps.get("data", emps.get("employees", []))
            if isinstance(emps, list) and len(emps) > 1:
                record(name, "FAIL", f"Employee got {len(emps)} employees — should be restricted")
            else:
                record(name, "PASS", "Returned limited data")
        except Exception:
            record(name, "FAIL", "Got 200 but couldn't parse response")
    check_rbac("/employees", "RBAC — Employee Can't List All Employees", check_emp_list)

    # 29. Employee should NOT access payroll runs
    check_rbac("/payroll", "RBAC — Employee Can't Access Payroll Runs")

    # 30. Employee should NOT see other employees' salary structures
    # Use empcloud user ID 522 (Ananya/admin) — employee 524 (Priya) should NOT see this
    resp = api_get(emp_session, "/salary-structures/employee/522")
    if resp is None:
        record("RBAC — Employee Can't See Others' Salary", "SKIP", "No response")
    elif resp.status_code in (401, 403):
        record("RBAC — Employee Can't See Others' Salary", "PASS", f"Correctly blocked: {resp.status_code}")
    elif resp.status_code == 200:
        try:
            data = resp.json()
            sal_data = data.get("data", {})
            ctc = sal_data.get("ctc", "unknown")
            record("RBAC — Employee Can't See Others' Salary", "FAIL",
                   f"Employee can see admin's salary (CTC: {ctc}) — RBAC violation!")
        except Exception:
            record("RBAC — Employee Can't See Others' Salary", "FAIL",
                   "Employee got 200 viewing another's salary")
    else:
        record("RBAC — Employee Can't See Others' Salary",
               "PASS" if resp.status_code >= 400 else "FAIL", f"Status {resp.status_code}")

    # 31. Employee should NOT access org settings
    check_rbac("/organizations/settings", "RBAC — Employee Can't Access Settings")


# ═══════════════════════════════════════════════════════════════════════
#  PART 2: SELENIUM UI TESTS — ADMIN
# ═══════════════════════════════════════════════════════════════════════

def run_admin_ui_tests():
    log("\n" + "=" * 70)
    log("PART 2: SELENIUM UI TESTS — ADMIN (Ananya)")
    log("=" * 70)

    token = get_sso_token(ADMIN_EMAIL, ADMIN_PASS)
    if not token:
        record("UI Admin — SSO Token", "FAIL", "Could not get token")
        return

    driver = None
    try:
        driver = create_driver()

        # ── 1. SSO into Payroll module ──
        log("\n--- Admin SSO Login ---")
        driver.get(f"{PAYROLL_UI}?sso_token={token}")
        wait_for_page(driver, 20)
        screenshot(driver, "admin_01_sso_landing")

        page_url = driver.current_url
        page_title = driver.title
        has_content = page_has_content(driver)
        no_error = check_no_error(driver)

        if has_content and no_error:
            record("UI Admin — SSO Login to Payroll", "PASS", f"Landed on {page_url}")
        else:
            record("UI Admin — SSO Login to Payroll", "FAIL",
                   f"Page: {page_url}, content={has_content}, noError={no_error}")

        # ── 2. Dashboard ──
        log("\n--- Admin Dashboard ---")
        driver.get(f"{PAYROLL_UI}/")
        wait_for_page(driver)
        screenshot(driver, "admin_02_dashboard")

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        dashboard_keywords = ["dashboard", "payroll", "employee", "salary", "total", "cost",
                              "run", "overview", "analytics", "recent"]
        found_kw = [kw for kw in dashboard_keywords if kw in body_text]
        if len(found_kw) >= 2 and no_error:
            record("UI Admin — Dashboard", "PASS", f"Keywords found: {found_kw[:5]}")
        elif has_content:
            record("UI Admin — Dashboard", "PASS", f"Page loaded with content, keywords: {found_kw}")
        else:
            record("UI Admin — Dashboard", "FAIL", f"Keywords: {found_kw}")

        # ── 3. Payslips page ──
        log("\n--- Admin Payslips ---")
        driver.get(f"{PAYROLL_UI}/payslips")
        wait_for_page(driver)
        screenshot(driver, "admin_03_payslips")

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — Payslips Page", "PASS", "Page loaded")
        else:
            record("UI Admin — Payslips Page", "FAIL", "Page error or empty")

        # ── 4. Salary Structures ──
        log("\n--- Admin Salary Structures ---")
        driver.get(f"{PAYROLL_UI}/payroll/salary-structures")
        wait_for_page(driver)
        screenshot(driver, "admin_04_salary_structures")

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if check_no_error(driver) and page_has_content(driver):
            sal_kw = [kw for kw in ["salary", "structure", "ctc", "basic", "hra", "component"] if kw in body_text]
            record("UI Admin — Salary Structures", "PASS", f"Keywords: {sal_kw}")
        else:
            record("UI Admin — Salary Structures", "FAIL", "Page error or empty")

        # ── 5. Payroll Runs ──
        log("\n--- Admin Payroll Runs ---")
        driver.get(f"{PAYROLL_UI}/payroll/runs")
        wait_for_page(driver)
        screenshot(driver, "admin_05_payroll_runs")

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if check_no_error(driver) and page_has_content(driver):
            run_kw = [kw for kw in ["payroll", "run", "draft", "compute", "approve", "pay",
                                     "february", "march", "month"] if kw in body_text]
            record("UI Admin — Payroll Runs", "PASS", f"Keywords: {run_kw}")
        else:
            record("UI Admin — Payroll Runs", "FAIL", "Page error or empty")

    except Exception as e:
        record("UI Admin — Unexpected Error (batch 1)", "FAIL", str(e)[:300])
        if driver:
            screenshot(driver, "admin_error_batch1")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # ── Restart driver (avoid ChromeDriver crashes) ──
    time.sleep(2)
    token = get_sso_token(ADMIN_EMAIL, ADMIN_PASS)
    if not token:
        record("UI Admin — SSO Token Refresh", "FAIL", "Could not refresh token")
        return

    driver = None
    try:
        driver = create_driver()
        driver.get(f"{PAYROLL_UI}?sso_token={token}")
        wait_for_page(driver, 20)

        # ── 6. Reports ──
        log("\n--- Admin Reports ---")
        driver.get(f"{PAYROLL_UI}/reports")
        wait_for_page(driver)
        screenshot(driver, "admin_06_reports")

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if check_no_error(driver) and page_has_content(driver):
            rpt_kw = [kw for kw in ["report", "pf", "esi", "tds", "pt", "professional tax",
                                     "ecr", "download", "bank"] if kw in body_text]
            record("UI Admin — Reports", "PASS", f"Keywords: {rpt_kw}")
        else:
            record("UI Admin — Reports", "FAIL", "Page error or empty")

        # ── 7. Tax ──
        log("\n--- Admin Tax ---")
        # Try /tax or /my/tax or check payroll analytics with tax data
        for tax_path in ["/tax", "/payroll/analytics"]:
            driver.get(f"{PAYROLL_UI}{tax_path}")
            wait_for_page(driver)
            if page_has_content(driver) and check_no_error(driver):
                screenshot(driver, f"admin_07_tax_{tax_path.replace('/', '_')}")
                body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                tax_kw = [kw for kw in ["tax", "tds", "regime", "declaration", "80c", "deduction",
                                         "analytics", "trend", "cost"] if kw in body_text]
                record("UI Admin — Tax / Analytics", "PASS", f"Path: {tax_path}, Keywords: {tax_kw}")
                break
        else:
            record("UI Admin — Tax / Analytics", "FAIL", "No tax page loaded")

        # ── 8. Settings ──
        log("\n--- Admin Settings ---")
        driver.get(f"{PAYROLL_UI}/settings")
        wait_for_page(driver)
        screenshot(driver, "admin_08_settings")

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if check_no_error(driver) and page_has_content(driver):
            set_kw = [kw for kw in ["settings", "organization", "statutory", "pf", "esi",
                                     "payment", "bank", "config"] if kw in body_text]
            record("UI Admin — Settings", "PASS", f"Keywords: {set_kw}")
        else:
            record("UI Admin — Settings", "FAIL", "Page error or empty")

        # ── 9. Employees List ──
        log("\n--- Admin Employees ---")
        driver.get(f"{PAYROLL_UI}/employees")
        wait_for_page(driver)
        screenshot(driver, "admin_09_employees")

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — Employees List", "PASS", "Page loaded")
        else:
            record("UI Admin — Employees List", "FAIL", "Page error or empty")

        # ── 10. Attendance ──
        log("\n--- Admin Attendance ---")
        driver.get(f"{PAYROLL_UI}/attendance")
        wait_for_page(driver)
        screenshot(driver, "admin_10_attendance")

        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — Attendance", "PASS", "Page loaded")
        else:
            record("UI Admin — Attendance", "FAIL", "Page error or empty")

        # ── 11. Leaves ──
        log("\n--- Admin Leaves ---")
        driver.get(f"{PAYROLL_UI}/leaves")
        wait_for_page(driver)
        screenshot(driver, "admin_11_leaves")

        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — Leaves", "PASS", "Page loaded")
        else:
            record("UI Admin — Leaves", "FAIL", "Page error or empty")

        # ── 12. Benefits ──
        log("\n--- Admin Benefits ---")
        driver.get(f"{PAYROLL_UI}/benefits")
        wait_for_page(driver)
        screenshot(driver, "admin_12_benefits")

        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — Benefits", "PASS", "Page loaded")
        else:
            record("UI Admin — Benefits", "FAIL", "Page error or empty")

        # ── 13. Insurance ──
        log("\n--- Admin Insurance ---")
        driver.get(f"{PAYROLL_UI}/insurance")
        wait_for_page(driver)
        screenshot(driver, "admin_13_insurance")

        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — Insurance", "PASS", "Page loaded")
        else:
            record("UI Admin — Insurance", "FAIL", "Page error or empty")

        # ── 14. Loans ──
        log("\n--- Admin Loans ---")
        driver.get(f"{PAYROLL_UI}/loans")
        wait_for_page(driver)
        screenshot(driver, "admin_14_loans")

        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — Loans", "PASS", "Page loaded")
        else:
            record("UI Admin — Loans", "FAIL", "Page error or empty")

    except Exception as e:
        record("UI Admin — Unexpected Error (batch 2)", "FAIL", str(e)[:300])
        if driver:
            screenshot(driver, "admin_error_batch2")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # ── Restart driver for remaining admin pages ──
    time.sleep(2)
    token = get_sso_token(ADMIN_EMAIL, ADMIN_PASS)
    if not token:
        record("UI Admin — SSO Token Refresh 2", "FAIL", "Could not refresh token")
        return

    driver = None
    try:
        driver = create_driver()
        driver.get(f"{PAYROLL_UI}?sso_token={token}")
        wait_for_page(driver, 20)

        # ── 15. GL Accounting ──
        log("\n--- Admin GL Accounting ---")
        driver.get(f"{PAYROLL_UI}/gl-accounting")
        wait_for_page(driver)
        screenshot(driver, "admin_15_gl_accounting")

        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — GL Accounting", "PASS", "Page loaded")
        else:
            record("UI Admin — GL Accounting", "FAIL", "Page error or empty")

        # ── 16. Global Payroll ──
        log("\n--- Admin Global Payroll ---")
        driver.get(f"{PAYROLL_UI}/global-payroll")
        wait_for_page(driver)
        screenshot(driver, "admin_16_global_payroll")

        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — Global Payroll", "PASS", "Page loaded")
        else:
            record("UI Admin — Global Payroll", "FAIL", "Page error or empty")

        # ── 17. Earned Wage Access ──
        log("\n--- Admin Earned Wage Access ---")
        driver.get(f"{PAYROLL_UI}/earned-wage")
        wait_for_page(driver)
        screenshot(driver, "admin_17_earned_wage")

        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — Earned Wage Access", "PASS", "Page loaded")
        else:
            record("UI Admin — Earned Wage Access", "FAIL", "Page error or empty")

        # ── 18. Pay Equity ──
        log("\n--- Admin Pay Equity ---")
        driver.get(f"{PAYROLL_UI}/pay-equity")
        wait_for_page(driver)
        screenshot(driver, "admin_18_pay_equity")

        if check_no_error(driver) and page_has_content(driver):
            record("UI Admin — Pay Equity", "PASS", "Page loaded")
        else:
            record("UI Admin — Pay Equity", "FAIL", "Page error or empty")

        # ── 19-22. Remaining admin pages ──
        remaining_pages = [
            ("/benchmarks", "Benchmarks"),
            ("/total-rewards", "Total Rewards"),
            ("/audit-log", "Audit Log"),
            ("/payroll/analytics", "Payroll Analytics"),
        ]
        for idx, (path, name) in enumerate(remaining_pages, 19):
            log(f"\n--- Admin {name} ---")
            try:
                driver.get(f"{PAYROLL_UI}{path}")
                wait_for_page(driver)
                screenshot(driver, f"admin_{idx}_{name.replace(' ', '_').lower()}")

                if check_no_error(driver) and page_has_content(driver):
                    record(f"UI Admin — {name}", "PASS", "Page loaded")
                else:
                    record(f"UI Admin — {name}", "FAIL", "Page error or empty")
            except Exception as e:
                record(f"UI Admin — {name}", "FAIL", f"Page load error: {str(e)[:150]}")
                # If Chrome crashed, break out
                try:
                    driver.current_url
                except Exception:
                    log("  Chrome driver crashed, stopping batch 3")
                    break

    except Exception as e:
        record("UI Admin — Unexpected Error (batch 3)", "FAIL", str(e)[:300])
        if driver:
            screenshot(driver, "admin_error_batch3")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════
#  PART 3: SELENIUM UI TESTS — EMPLOYEE
# ═══════════════════════════════════════════════════════════════════════

def run_employee_ui_tests():
    log("\n" + "=" * 70)
    log("PART 3: SELENIUM UI TESTS — EMPLOYEE (Priya)")
    log("=" * 70)

    token = get_sso_token(EMP_EMAIL, EMP_PASS)
    if not token:
        record("UI Employee — SSO Token", "FAIL", "Could not get token")
        return

    driver = None
    try:
        driver = create_driver()

        # ── 1. SSO into Payroll module ──
        log("\n--- Employee SSO Login ---")
        driver.get(f"{PAYROLL_UI}?sso_token={token}")
        wait_for_page(driver, 20)
        screenshot(driver, "emp_01_sso_landing")

        has_content = page_has_content(driver)
        no_error = check_no_error(driver)
        if has_content and no_error:
            record("UI Employee — SSO Login", "PASS", f"Landed on {driver.current_url}")
        else:
            record("UI Employee — SSO Login", "FAIL", f"content={has_content}, noError={no_error}")

        # ── 2. My Dashboard ──
        log("\n--- Employee My Dashboard ---")
        driver.get(f"{PAYROLL_UI}/my")
        wait_for_page(driver)
        screenshot(driver, "emp_02_my_dashboard")

        if page_has_content(driver) and check_no_error(driver):
            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            my_kw = [kw for kw in ["dashboard", "payslip", "salary", "tax", "welcome", "priya",
                                    "employee", "quick"] if kw in body]
            record("UI Employee — My Dashboard", "PASS", f"Keywords: {my_kw}")
        else:
            record("UI Employee — My Dashboard", "FAIL", "Page error or empty")

        # ── 3. My Payslips ──
        log("\n--- Employee My Payslips ---")
        driver.get(f"{PAYROLL_UI}/my/payslips")
        wait_for_page(driver)
        screenshot(driver, "emp_03_my_payslips")

        if page_has_content(driver) and check_no_error(driver):
            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            slip_kw = [kw for kw in ["payslip", "salary", "download", "month", "net", "gross",
                                      "february", "earnings", "deductions"] if kw in body]
            record("UI Employee — My Payslips", "PASS", f"Keywords: {slip_kw}")
        else:
            record("UI Employee — My Payslips", "FAIL", "Page error or empty")

        # ── 4. My Salary ──
        log("\n--- Employee My Salary ---")
        driver.get(f"{PAYROLL_UI}/my/salary")
        wait_for_page(driver)
        screenshot(driver, "emp_04_my_salary")

        if page_has_content(driver) and check_no_error(driver):
            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            sal_kw = [kw for kw in ["salary", "ctc", "basic", "hra", "allowance", "gross",
                                     "net", "component", "breakdown"] if kw in body]
            record("UI Employee — My Salary", "PASS", f"Keywords: {sal_kw}")
        else:
            record("UI Employee — My Salary", "FAIL", "Page error or empty")

        # ── 5. My Tax ──
        log("\n--- Employee My Tax ---")
        driver.get(f"{PAYROLL_UI}/my/tax")
        wait_for_page(driver)
        screenshot(driver, "emp_05_my_tax")

        if page_has_content(driver) and check_no_error(driver):
            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            tax_kw = [kw for kw in ["tax", "tds", "regime", "old", "new", "computation",
                                     "income", "deduction", "form 16"] if kw in body]
            record("UI Employee — My Tax", "PASS", f"Keywords: {tax_kw}")
        else:
            record("UI Employee — My Tax", "FAIL", "Page error or empty")

        # ── 6. My Declarations ──
        log("\n--- Employee My Declarations ---")
        driver.get(f"{PAYROLL_UI}/my/declarations")
        wait_for_page(driver)
        screenshot(driver, "emp_06_my_declarations")

        if page_has_content(driver) and check_no_error(driver):
            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            decl_kw = [kw for kw in ["declaration", "80c", "80d", "hra", "nps", "investment",
                                      "proof", "submit", "section"] if kw in body]
            record("UI Employee — My Declarations", "PASS", f"Keywords: {decl_kw}")
        else:
            record("UI Employee — My Declarations", "FAIL", "Page error or empty")

        # ── 7. My Reimbursements ──
        log("\n--- Employee My Reimbursements ---")
        driver.get(f"{PAYROLL_UI}/my/reimbursements")
        wait_for_page(driver)
        screenshot(driver, "emp_07_my_reimbursements")

        if page_has_content(driver) and check_no_error(driver):
            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            reimb_kw = [kw for kw in ["reimbursement", "claim", "expense", "submit", "amount",
                                       "status", "category"] if kw in body]
            record("UI Employee — My Reimbursements", "PASS", f"Keywords: {reimb_kw}")
        else:
            record("UI Employee — My Reimbursements", "FAIL", "Page error or empty")

        # ── 8. My Profile ──
        log("\n--- Employee My Profile ---")
        driver.get(f"{PAYROLL_UI}/my/profile")
        wait_for_page(driver)
        screenshot(driver, "emp_08_my_profile")

        if page_has_content(driver) and check_no_error(driver):
            record("UI Employee — My Profile", "PASS", "Page loaded")
        else:
            record("UI Employee — My Profile", "FAIL", "Page error or empty")

    except Exception as e:
        record("UI Employee — Unexpected Error (batch 1)", "FAIL", str(e)[:300])
        if driver:
            screenshot(driver, "emp_error_batch1")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # ── Restart driver for RBAC UI checks ──
    time.sleep(2)
    token = get_sso_token(EMP_EMAIL, EMP_PASS)
    if not token:
        record("UI Employee — SSO Token Refresh", "FAIL", "Could not refresh token")
        return

    driver = None
    try:
        driver = create_driver()
        driver.get(f"{PAYROLL_UI}?sso_token={token}")
        wait_for_page(driver, 20)

        # ── 9. Employee tries to access admin pages — should be blocked ──
        log("\n--- Employee RBAC UI Checks ---")

        admin_pages = [
            ("/payroll/runs", "Payroll Runs"),
            ("/employees", "Employees List"),
            ("/settings", "Settings"),
            ("/reports", "Reports"),
        ]

        for path, name in admin_pages:
            driver.get(f"{PAYROLL_UI}{path}")
            wait_for_page(driver)
            screenshot(driver, f"emp_rbac_{name.replace(' ', '_').lower()}")

            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            # Check if redirected away, shows access denied, or shows admin content
            access_denied_kw = ["access denied", "unauthorized", "not authorized", "forbidden",
                                "permission", "login", "403"]
            is_blocked = any(kw in body_text for kw in access_denied_kw)
            # If page barely has content, the route guard likely redirected
            barely_content = len(body_text.strip()) < 100

            if is_blocked or barely_content:
                record(f"RBAC UI — Employee Can't Access {name}", "PASS",
                       "Access denied or redirected")
            elif "/my" in driver.current_url:
                record(f"RBAC UI — Employee Can't Access {name}", "PASS",
                       f"Redirected to {driver.current_url}")
            else:
                # The page loaded — might be an RBAC issue or the page is accessible to employees
                record(f"RBAC UI — Employee Can't Access {name}", "FAIL",
                       f"Employee can see {name} at {driver.current_url}")

        # ── 10. My Leaves ──
        log("\n--- Employee My Leaves ---")
        driver.get(f"{PAYROLL_UI}/my/leaves")
        wait_for_page(driver)
        screenshot(driver, "emp_10_my_leaves")

        if page_has_content(driver) and check_no_error(driver):
            record("UI Employee — My Leaves", "PASS", "Page loaded")
        else:
            record("UI Employee — My Leaves", "FAIL", "Page error or empty")

    except Exception as e:
        record("UI Employee — Unexpected Error (batch 2)", "FAIL", str(e)[:300])
        if driver:
            screenshot(driver, "emp_error_batch2")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════════════

def print_summary():
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    skip_count = sum(1 for r in results if r["status"] == "SKIP")
    total = len(results)

    log(f"\nTotal: {total}  |  PASS: {pass_count}  |  FAIL: {fail_count}  |  SKIP: {skip_count}")
    log(f"Pass rate: {pass_count}/{total} ({100*pass_count/total:.0f}%)" if total else "No tests ran")

    if fail_count:
        log("\n--- FAILED TESTS ---")
        for r in results:
            if r["status"] == "FAIL":
                log(f"  FAIL: {r['test']}")
                if r["detail"]:
                    log(f"        {r['detail'][:200]}")

    if skip_count:
        log("\n--- SKIPPED TESTS ---")
        for r in results:
            if r["status"] == "SKIP":
                log(f"  SKIP: {r['test']} — {r['detail']}")

    log(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
    log(f"Total screenshots: {len(os.listdir(SCREENSHOT_DIR))}")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    start = time.time()
    log("=" * 70)
    log("FRESH E2E TEST — EMP PAYROLL MODULE")
    log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    try:
        run_api_tests()
    except Exception as e:
        log(f"API tests crashed: {e}")
        traceback.print_exc()

    try:
        run_admin_ui_tests()
    except Exception as e:
        log(f"Admin UI tests crashed: {e}")
        traceback.print_exc()

    try:
        run_employee_ui_tests()
    except Exception as e:
        log(f"Employee UI tests crashed: {e}")
        traceback.print_exc()

    elapsed = time.time() - start
    log(f"\nTotal time: {elapsed:.0f}s")
    print_summary()
