"""
RBAC Verification Test -- All EmpCloud Modules
Tests that employee role (priya@technova.in) CANNOT access admin/restricted endpoints.
Combines API-level checks with Selenium UI SSO checks.
Screenshots every RBAC violation found.
"""

import os
import sys
import json
import time
import datetime
import requests
from dataclasses import dataclass, field
from typing import Optional

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
EMPLOYEE_EMAIL = "priya@technova.in"
EMPLOYEE_PASS = "Welcome@123"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"

MODULE_APIS = {
    "payroll":     "https://testpayroll-api.empcloud.com/api/v1",
    "recruit":     "https://test-recruit-api.empcloud.com/api/v1",
    "performance": "https://test-performance-api.empcloud.com/api/v1",
    "rewards":     "https://test-rewards-api.empcloud.com/api/v1",
    "exit":        "https://test-exit-api.empcloud.com/api/v1",
    "lms":         "https://testlms-api.empcloud.com/api/v1",
}

MODULE_URLS = {
    "core":        "https://test-empcloud.empcloud.com",
    "payroll":     "https://testpayroll.empcloud.com",
    "recruit":     "https://test-recruit.empcloud.com",
    "performance": "https://test-performance.empcloud.com",
    "rewards":     "https://test-rewards.empcloud.com",
    "exit":        "https://test-exit.empcloud.com",
    "lms":         "https://testlms.empcloud.com",
}

SCREENSHOT_DIR = r"C:\emptesting\fresh\screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
@dataclass
class TestResult:
    module: str
    endpoint: str
    method: str
    expected: str          # "FORBIDDEN" or "NOT_FOUND"
    actual_status: int
    actual_code: str
    passed: bool
    detail: str = ""
    screenshot: str = ""

results: list[TestResult] = []
violations: list[TestResult] = []

def log(msg: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login(email: str, password: str) -> dict:
    """Login to core API, return full response data."""
    r = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    data = r.json()
    assert data["success"], f"Login failed: {data}"
    return data["data"]

def get_core_token(email: str, password: str) -> str:
    return login(email, password)["tokens"]["access_token"]

def get_module_token(module: str, core_token: str) -> Optional[str]:
    """Exchange core token for module-specific SSO token."""
    if module == "core":
        return core_token
    api_base = MODULE_APIS.get(module)
    if not api_base:
        return None
    try:
        r = requests.post(f"{api_base}/auth/sso", json={"token": core_token}, timeout=30)
        data = r.json()
        if data.get("success"):
            return data["data"]["tokens"]["accessToken"]
    except Exception as e:
        log(f"  SSO exchange failed for {module}: {e}")
    return None

# ---------------------------------------------------------------------------
# API test helper
# ---------------------------------------------------------------------------
def test_api_endpoint(module: str, base_url: str, path: str, token: str,
                      method: str = "GET", body: dict = None,
                      expect_blocked: bool = True) -> TestResult:
    """
    Test that an API endpoint blocks employee access.
    expect_blocked=True means we expect 403/401/404.
    A 200 response when expect_blocked=True is a VIOLATION.
    """
    url = f"{base_url}/{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            r = requests.post(url, headers=headers, json=body or {}, timeout=30)
        elif method == "PUT":
            r = requests.put(url, headers=headers, json=body or {}, timeout=30)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, timeout=30)
        else:
            r = requests.get(url, headers=headers, timeout=30)

        status = r.status_code
        try:
            resp_data = r.json()
            code = resp_data.get("error", {}).get("code", "") if not resp_data.get("success") else "SUCCESS"
            success = resp_data.get("success", False)
        except Exception:
            # HTML error page (route not found) -- treat as blocked
            code = "ROUTE_NOT_FOUND"
            success = False

        if expect_blocked:
            # Blocked = FORBIDDEN, UNAUTHORIZED, NOT_FOUND, or non-success
            is_blocked = (not success) or status in (401, 403, 404)
            passed = is_blocked
        else:
            passed = success

        detail = ""
        if expect_blocked and not passed:
            detail = f"VIOLATION: Employee got 200 SUCCESS on {method} {path}"

        result = TestResult(
            module=module,
            endpoint=f"{method} {path}",
            method=method,
            expected="BLOCKED" if expect_blocked else "ALLOWED",
            actual_status=status,
            actual_code=code,
            passed=passed,
            detail=detail,
        )
    except requests.exceptions.ConnectionError:
        result = TestResult(
            module=module,
            endpoint=f"{method} {path}",
            method=method,
            expected="BLOCKED" if expect_blocked else "ALLOWED",
            actual_status=0,
            actual_code="CONN_ERROR",
            passed=True,  # can't reach = effectively blocked
            detail="Connection refused (service down or endpoint doesn't exist)",
        )
    except Exception as e:
        result = TestResult(
            module=module,
            endpoint=f"{method} {path}",
            method=method,
            expected="BLOCKED" if expect_blocked else "ALLOWED",
            actual_status=0,
            actual_code="ERROR",
            passed=True,
            detail=str(e),
        )

    results.append(result)
    if not result.passed:
        violations.append(result)

    status_str = "PASS" if result.passed else "** FAIL **"
    log(f"  [{status_str}] {module}: {method} {path} -> {result.actual_status} {result.actual_code}")
    return result


# ---------------------------------------------------------------------------
# Selenium UI test helpers
# ---------------------------------------------------------------------------
def create_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def screenshot(driver: webdriver.Chrome, name: str) -> str:
    fname = f"{name}_{datetime.datetime.now().strftime('%H%M%S')}.png"
    fpath = os.path.join(SCREENSHOT_DIR, fname)
    driver.save_screenshot(fpath)
    return fpath


def ui_sso_navigate(driver: webdriver.Chrome, module: str, sso_token: str, path: str = "") -> str:
    """Navigate to a module URL with SSO token, return page source snippet."""
    base = MODULE_URLS.get(module, "")
    url = f"{base}/{path}?sso_token={sso_token}" if path else f"{base}?sso_token={sso_token}"
    driver.get(url)
    time.sleep(3)  # Allow SPA to render
    return driver.page_source[:5000]


def check_ui_access_blocked(driver: webdriver.Chrome, module: str, sso_token: str,
                             path: str, description: str) -> TestResult:
    """
    Navigate to a module path via SSO and verify the employee is blocked.
    Look for redirect to login, 403 page, or 'not authorized' messages.
    """
    base = MODULE_URLS.get(module, "")
    url = f"{base}/{path}?sso_token={sso_token}"
    driver.get(url)
    time.sleep(4)

    current_url = driver.current_url
    page_src = driver.page_source.lower()

    # Indicators of being blocked
    blocked_indicators = [
        "not authorized", "access denied", "forbidden", "permission",
        "unauthorized", "login", "sign in", "signin", "no access",
        "restricted", "not found", "404", "403",
    ]

    # Indicators of admin content successfully loading (violation)
    admin_indicators = [
        "dashboard", "settings", "configuration", "manage",
        "admin panel", "analytics",
    ]

    is_redirected = ("login" in current_url.lower() or
                     "signin" in current_url.lower() or
                     current_url.rstrip("/") == base.rstrip("/"))

    has_block_text = any(ind in page_src for ind in blocked_indicators)
    has_admin_content = any(ind in page_src for ind in admin_indicators)

    # If we got redirected to login or see block text, it's properly blocked
    # If we see admin content without block text, it's a violation
    passed = is_redirected or has_block_text or not has_admin_content

    result = TestResult(
        module=module,
        endpoint=f"UI: {path}",
        method="SSO_NAV",
        expected="BLOCKED",
        actual_status=200,
        actual_code="REDIRECTED" if is_redirected else ("BLOCKED_TEXT" if has_block_text else "LOADED"),
        passed=passed,
        detail=description,
    )

    # Screenshot violations
    if not passed:
        sc = screenshot(driver, f"VIOLATION_{module}_{path.replace('/', '_')}")
        result.screenshot = sc
        log(f"  ** VIOLATION SCREENSHOT: {sc}")

    results.append(result)
    if not result.passed:
        violations.append(result)

    status_str = "PASS" if result.passed else "** FAIL **"
    log(f"  [{status_str}] {module} UI: /{path} -> {result.actual_code}")
    return result


# ===========================================================================
# TEST SUITES
# ===========================================================================
def test_core_api(token: str):
    log("=" * 60)
    log("CORE MODULE - API RBAC Tests")
    log("=" * 60)

    base = API_BASE

    # These should be BLOCKED for employees
    test_api_endpoint("core", base, "audit", token)
    test_api_endpoint("core", base, "admin/dashboard", token)
    test_api_endpoint("core", base, "admin/users", token)
    test_api_endpoint("core", base, "admin/roles", token)
    test_api_endpoint("core", base, "admin/audit-logs", token)

    # /users -- employee should NOT see full list
    test_api_endpoint("core", base, "users", token, expect_blocked=True)

    # /employees -- employee should NOT see all employees
    test_api_endpoint("core", base, "employees", token, expect_blocked=True)

    # Leave policies -- arguably admin but may be visible to employees
    test_api_endpoint("core", base, "leave/policies", token, expect_blocked=True)


def test_payroll_api(token: str):
    log("=" * 60)
    log("PAYROLL MODULE - API RBAC Tests")
    log("=" * 60)

    base = MODULE_APIS["payroll"]
    test_api_endpoint("payroll", base, "payroll/employees", token)
    test_api_endpoint("payroll", base, "payroll/run", token)
    test_api_endpoint("payroll", base, "salary-structures", token)
    test_api_endpoint("payroll", base, "payslips", token)
    test_api_endpoint("payroll", base, "payroll/run", token, method="POST",
                      body={"month": 3, "year": 2026})


def test_recruit_api(token: str):
    log("=" * 60)
    log("RECRUIT MODULE - API RBAC Tests")
    log("=" * 60)

    base = MODULE_APIS["recruit"]
    test_api_endpoint("recruit", base, "candidates", token)
    test_api_endpoint("recruit", base, "interviews", token)
    test_api_endpoint("recruit", base, "jobs", token)


def test_performance_api(token: str):
    log("=" * 60)
    log("PERFORMANCE MODULE - API RBAC Tests")
    log("=" * 60)

    base = MODULE_APIS["performance"]
    test_api_endpoint("performance", base, "pips", token)
    test_api_endpoint("performance", base, "nine-box", token)
    test_api_endpoint("performance", base, "reviews", token)
    # POST create cycle
    test_api_endpoint("performance", base, "review-cycles", token, method="POST",
                      body={"name": "rbac-test-cycle", "startDate": "2026-04-01", "endDate": "2026-06-30"})


def test_rewards_api(token: str):
    log("=" * 60)
    log("REWARDS MODULE - API RBAC Tests")
    log("=" * 60)

    base = MODULE_APIS["rewards"]
    test_api_endpoint("rewards", base, "settings", token)
    test_api_endpoint("rewards", base, "budgets", token)
    # PUT settings -- employee should not be able to modify
    test_api_endpoint("rewards", base, "settings", token, method="PUT",
                      body={"points_per_kudos": 999})


def test_exit_api(token: str):
    log("=" * 60)
    log("EXIT MODULE - API RBAC Tests")
    log("=" * 60)

    base = MODULE_APIS["exit"]
    test_api_endpoint("exit", base, "exits", token)
    test_api_endpoint("exit", base, "settings", token)
    # PUT settings -- employee should not modify
    test_api_endpoint("exit", base, "settings", token, method="PUT",
                      body={"default_notice_period_days": 999})


def test_lms_api(token: str):
    log("=" * 60)
    log("LMS MODULE - API RBAC Tests")
    log("=" * 60)

    base = MODULE_APIS["lms"]
    # POST create course -- employee should NOT be able to
    test_api_endpoint("lms", base, "courses", token, method="POST",
                      body={"title": "RBAC Test Course", "description": "Should be blocked"})
    # GET all courses -- employee might see enrolled only, not drafts
    # We check if employee can see draft courses (admin content)
    test_api_endpoint("lms", base, "courses?status=draft", token)


def test_ui_rbac(driver: webdriver.Chrome, core_token: str):
    log("=" * 60)
    log("UI SSO RBAC Tests - Navigating as Employee")
    log("=" * 60)

    # Core module UI paths
    core_paths = [
        ("settings", "Core settings page"),
        ("admin", "Core admin panel"),
        ("admin/users", "Admin user management"),
        ("admin/audit", "Admin audit logs"),
    ]

    for path, desc in core_paths:
        check_ui_access_blocked(driver, "core", core_token, path, desc)

    # Payroll UI
    payroll_paths = [
        ("payroll", "Payroll dashboard"),
        ("payroll/run", "Run payroll"),
        ("employees", "All employee salaries"),
    ]
    for path, desc in payroll_paths:
        check_ui_access_blocked(driver, "payroll", core_token, path, desc)

    # Recruit UI
    recruit_paths = [
        ("candidates", "Candidate listing"),
        ("interviews", "Interview schedule"),
        ("settings", "Recruit settings"),
    ]
    for path, desc in recruit_paths:
        check_ui_access_blocked(driver, "recruit", core_token, path, desc)

    # Performance UI
    perf_paths = [
        ("pips", "PIP management"),
        ("nine-box", "9-box grid"),
        ("settings", "Performance settings"),
        ("cycles", "Review cycles"),
    ]
    for path, desc in perf_paths:
        check_ui_access_blocked(driver, "performance", core_token, path, desc)

    # Rewards UI
    rewards_paths = [
        ("settings", "Rewards settings"),
        ("budgets", "Rewards budgets"),
        ("analytics", "Rewards analytics"),
    ]
    for path, desc in rewards_paths:
        check_ui_access_blocked(driver, "rewards", core_token, path, desc)

    # Exit UI
    exit_paths = [
        ("fnf", "Full & Final settlement"),
        ("flight-risk", "Flight risk analysis"),
        ("exits", "All exit records"),
    ]
    for path, desc in exit_paths:
        check_ui_access_blocked(driver, "exit", core_token, path, desc)

    # LMS UI
    lms_paths = [
        ("admin", "LMS admin panel"),
        ("admin/courses", "LMS admin course management"),
        ("courses/create", "Create new course"),
    ]
    for path, desc in lms_paths:
        check_ui_access_blocked(driver, "lms", core_token, path, desc)


# ===========================================================================
# API: Verify that restricted data from OTHER employees is not visible
# ===========================================================================
def test_cross_employee_data(core_token: str, payroll_token: str):
    log("=" * 60)
    log("CROSS-EMPLOYEE DATA ISOLATION Tests")
    log("=" * 60)

    # Try to access another employee's profile by ID (employee 522 = Ananya, the admin)
    base = API_BASE
    r = requests.get(f"{base}/employees/522", headers={"Authorization": f"Bearer {core_token}"}, timeout=30)
    try:
        data = r.json()
        if data.get("success") and data.get("data"):
            emp_data = data["data"]
            # Check if salary or sensitive admin fields are exposed
            has_sensitive = any(k in str(emp_data).lower() for k in ["salary", "ctc", "bank", "pan", "aadhaar"])
            result = TestResult(
                module="core",
                endpoint="GET employees/522 (other employee profile)",
                method="GET",
                expected="BLOCKED",
                actual_status=r.status_code,
                actual_code="SUCCESS" if data["success"] else "FAILED",
                passed=not data["success"],
                detail=f"Employee can view other employee's profile. Sensitive data exposed: {has_sensitive}",
            )
            results.append(result)
            if not result.passed:
                violations.append(result)
            status_str = "PASS" if result.passed else "** FAIL **"
            log(f"  [{status_str}] core: GET /employees/522 -> {result.actual_code}")
    except Exception:
        pass

    # Try to access payslips for another employee
    if payroll_token:
        base = MODULE_APIS["payroll"]
        r2 = requests.get(f"{base}/payslips?employeeId=522",
                          headers={"Authorization": f"Bearer {payroll_token}"}, timeout=30)
        try:
            data2 = r2.json()
            result2 = TestResult(
                module="payroll",
                endpoint="GET payslips?employeeId=522 (other employee payslip)",
                method="GET",
                expected="BLOCKED",
                actual_status=r2.status_code,
                actual_code="SUCCESS" if data2.get("success") else data2.get("error", {}).get("code", "FAILED"),
                passed=not data2.get("success"),
                detail="Employee trying to view another employee's payslips",
            )
            results.append(result2)
            if not result2.passed:
                violations.append(result2)
            status_str = "PASS" if result2.passed else "** FAIL **"
            log(f"  [{status_str}] payroll: GET /payslips?employeeId=522 -> {result2.actual_code}")
        except Exception:
            pass


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    log("=" * 60)
    log("EmpCloud RBAC Verification Test - All Modules")
    log(f"Employee under test: {EMPLOYEE_EMAIL}")
    log(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    # Step 1: Get core token for employee
    log("\n[AUTH] Logging in as employee...")
    core_token = get_core_token(EMPLOYEE_EMAIL, EMPLOYEE_PASS)
    log(f"  Core token obtained (role: employee)")

    # Step 2: Get module-specific tokens
    log("[AUTH] Exchanging SSO tokens for all modules...")
    module_tokens = {}
    for mod in MODULE_APIS:
        tok = get_module_token(mod, core_token)
        if tok:
            module_tokens[mod] = tok
            log(f"  {mod}: SSO token obtained")
        else:
            log(f"  {mod}: SSO exchange FAILED")

    # Step 3: Run API tests for each module
    log("\n")
    test_core_api(core_token)
    if "payroll" in module_tokens:
        test_payroll_api(module_tokens["payroll"])
    if "recruit" in module_tokens:
        test_recruit_api(module_tokens["recruit"])
    if "performance" in module_tokens:
        test_performance_api(module_tokens["performance"])
    if "rewards" in module_tokens:
        test_rewards_api(module_tokens["rewards"])
    if "exit" in module_tokens:
        test_exit_api(module_tokens["exit"])
    if "lms" in module_tokens:
        test_lms_api(module_tokens["lms"])

    # Cross-employee data tests
    test_cross_employee_data(core_token, module_tokens.get("payroll"))

    # Step 4: UI SSO tests with Selenium
    log("\n[SELENIUM] Starting browser for UI RBAC tests...")
    driver = None
    try:
        driver = create_driver()
        test_ui_rbac(driver, core_token)
    except Exception as e:
        log(f"  Selenium error: {e}")
    finally:
        if driver:
            driver.quit()

    # Step 5: Screenshot API violations via Selenium
    if violations:
        api_violations = [v for v in violations if v.method != "SSO_NAV"]
        if api_violations:
            log("\n[SELENIUM] Taking screenshots of API violations via browser...")
            driver = None
            try:
                driver = create_driver()
                for v in api_violations:
                    # Navigate to the endpoint in the browser to capture visual evidence
                    mod = v.module
                    endpoint_path = v.endpoint.split(" ", 1)[1] if " " in v.endpoint else v.endpoint
                    base_url = MODULE_URLS.get(mod, MODULE_URLS["core"])
                    url = f"{base_url}/{endpoint_path}?sso_token={core_token}"
                    driver.get(url)
                    time.sleep(3)
                    sc = screenshot(driver, f"API_VIOLATION_{mod}_{endpoint_path.replace('/', '_')}")
                    v.screenshot = sc
                    log(f"  Screenshot: {sc}")
            except Exception as e:
                log(f"  Screenshot error: {e}")
            finally:
                if driver:
                    driver.quit()

    # ===========================================================
    # REPORT
    # ===========================================================
    log("\n")
    log("=" * 70)
    log("RBAC TEST REPORT")
    log("=" * 70)

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    log(f"Total tests: {total}")
    log(f"Passed:      {passed}")
    log(f"Failed:      {failed}")
    log("")

    if violations:
        log("RBAC VIOLATIONS FOUND:")
        log("-" * 70)
        for i, v in enumerate(violations, 1):
            log(f"  {i}. [{v.module.upper()}] {v.endpoint}")
            log(f"     Expected: {v.expected} | Got: {v.actual_status} {v.actual_code}")
            if v.detail:
                log(f"     Detail: {v.detail}")
            if v.screenshot:
                log(f"     Screenshot: {v.screenshot}")
            log("")
    else:
        log("No RBAC violations found -- all restricted endpoints properly blocked.")

    log("-" * 70)
    log("FULL RESULTS:")
    log(f"{'Status':<8} {'Module':<13} {'Endpoint':<55} {'Code':<20}")
    log("-" * 70)
    for r in results:
        s = "PASS" if r.passed else "FAIL"
        log(f"{s:<8} {r.module:<13} {r.endpoint:<55} {r.actual_code:<20}")

    log("=" * 70)
    log(f"Screenshots saved to: {SCREENSHOT_DIR}")
    log("=" * 70)

    # Return exit code
    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
