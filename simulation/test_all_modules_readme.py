#!/usr/bin/env python3
"""
EMP Cloud — Comprehensive All-Module API + Selenium SSO Test
Tests EVERY endpoint from EMPCLOUD_API_REFERENCE.md across all modules.
Files GitHub bugs for failures with [30-Day Sim SSO] prefix.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import time
import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
CORE_API = "https://test-empcloud-api.empcloud.com"
PAYROLL_API = "https://testpayroll-api.empcloud.com"
RECRUIT_API = "https://test-recruit-api.empcloud.com"
PERFORMANCE_API = "https://test-performance-api.empcloud.com"
REWARDS_API = "https://test-rewards-api.empcloud.com"
EXIT_API = "https://test-exit-api.empcloud.com"
LMS_API = "https://testlms-api.empcloud.com"
PROJECT_API = "https://test-project-api.empcloud.com"
MONITOR_API = "https://test-empmonitor-api.empcloud.com"

CORE_FE = "https://test-empcloud.empcloud.com"
PAYROLL_FE = "https://testpayroll.empcloud.com"
RECRUIT_FE = "https://test-recruit.empcloud.com"
PERFORMANCE_FE = "https://test-performance.empcloud.com"
REWARDS_FE = "https://test-rewards.empcloud.com"
EXIT_FE = "https://test-exit.empcloud.com"
LMS_FE = "https://testlms.empcloud.com"
PROJECT_FE = "https://test-project.empcloud.com"
MONITOR_FE = "https://test-empmonitor.empcloud.com"

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_API = "https://api.github.com"

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = Path(r"C:\emptesting\simulation\screenshots_readme")
SCREENSHOT_DIR.mkdir(exist_ok=True)

CREDS = {
    "technova": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "globaltech": {"email": "john@globaltech.com", "password": "Welcome@123"},
    "innovate": {"email": "hr@innovate.io", "password": "Welcome@123"},
}

# Known IDs from setup_data.json
TECHNOVA_ORG_ID = 5
TECHNOVA_DEPT_ID = 72
TECHNOVA_DEPT_SALES_ID = 73
TECHNOVA_EMP_ID = 663
TECHNOVA_LEAVE_TYPE_ID = 31
TECHNOVA_SHIFT_ID = 10

TIMEOUT = 15
results = []
bugs_to_file = []
tokens = {}
module_sso_tokens = {}

# ============================================================
# HELPERS
# ============================================================
def login(cred_key):
    """Login and cache token."""
    if cred_key in tokens and tokens[cred_key]:
        return tokens[cred_key]
    cred = CREDS[cred_key]
    try:
        r = requests.post(f"{CORE_API}/api/v1/auth/login",
                          json={"email": cred["email"], "password": cred["password"]},
                          timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            token = extract_token(data)
            tokens[cred_key] = token
            return token
        else:
            print(f"  [LOGIN FAIL] {cred_key}: {r.status_code}")
            return None
    except Exception as e:
        print(f"  [LOGIN ERROR] {cred_key}: {e}")
        return None


def auth_headers(token):
    if not token:
        return {"Content-Type": "application/json"}
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def extract_token(data):
    if not isinstance(data, dict):
        return None
    d = data.get("data", {}) or {}
    t = (d.get("tokens", {}) or {}) if isinstance(d, dict) else {}
    return (t.get("access_token") or t.get("accessToken") or t.get("token")
            or (d.get("token") if isinstance(d, dict) else None)
            or (d.get("accessToken") if isinstance(d, dict) else None)
            or (d.get("access_token") if isinstance(d, dict) else None)
            or data.get("token") or data.get("accessToken") or data.get("access_token"))


def test_endpoint(module, method, url, description, token=None, body=None,
                  expected_codes=None, ref_section="API Reference"):
    """Test a single endpoint and record result."""
    if expected_codes is None:
        expected_codes = [200, 201, 204, 301, 302, 304]

    try:
        headers = auth_headers(token)
        kwargs = {"headers": headers, "timeout": (5, 10)}
        if body is not None:
            kwargs["json"] = body

        if method == "GET":
            r = requests.get(url, **kwargs)
        elif method == "POST":
            r = requests.post(url, **kwargs)
        elif method == "PUT":
            r = requests.put(url, **kwargs)
        elif method == "PATCH":
            r = requests.patch(url, **kwargs)
        elif method == "DELETE":
            r = requests.delete(url, **kwargs)
        else:
            r = requests.get(url, **kwargs)

        status = r.status_code
        ok = status in expected_codes

        # 401/403 for destructive endpoints is acceptable (permission denied but endpoint exists)
        endpoint_exists = status not in [404, 502, 503, 504]

        result = {
            "module": module,
            "method": method,
            "url": url,
            "description": description,
            "status": status,
            "passed": ok,
            "endpoint_exists": endpoint_exists,
            "ref_section": ref_section,
        }
        results.append(result)

        status_icon = "PASS" if ok else ("WARN" if endpoint_exists else "FAIL")
        print(f"  [{status_icon}] {method} {url.split('.com')[-1][:60]:60s} -> {status} | {description}")
        sys.stdout.flush()

        if not endpoint_exists:
            bugs_to_file.append({
                "module": module,
                "method": method,
                "path": url.split(".com")[-1],
                "description": description,
                "status": status,
                "ref_section": ref_section,
            })

        return r
    except Exception as e:
        result = {
            "module": module,
            "method": method,
            "url": url,
            "description": description,
            "status": f"ERROR: {str(e)[:80]}",
            "passed": False,
            "endpoint_exists": False,
            "ref_section": ref_section,
        }
        results.append(result)
        print(f"  [ERROR] {method} {url.split('.com')[-1][:60]:60s} -> {str(e)[:60]}")
        sys.stdout.flush()
        bugs_to_file.append({
            "module": module,
            "method": method,
            "path": url.split(".com")[-1],
            "description": description,
            "status": f"ERROR: {str(e)[:80]}",
            "ref_section": ref_section,
        })
        return None


def file_github_bug(title, body, labels=None):
    """File a GitHub issue."""
    if labels is None:
        labels = ["bug", "30-day-sim"]
    try:
        r = requests.post(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={"title": title, "body": body, "labels": labels},
            timeout=30,
        )
        if r.status_code == 201:
            url = r.json().get("html_url", "")
            print(f"    -> Bug filed: {url}")
            return url
        else:
            print(f"    -> Bug filing failed: {r.status_code} {r.text[:100]}")
            return None
    except Exception as e:
        print(f"    -> Bug filing error: {e}")
        return None


def get_existing_issues():
    """Get existing issues to avoid duplicates."""
    try:
        issues = []
        page = 1
        while page <= 5:
            r = requests.get(
                f"{GITHUB_API}/repos/{GITHUB_REPO}/issues",
                headers={"Authorization": f"token {GITHUB_PAT}"},
                params={"state": "all", "per_page": 100, "page": page},
                timeout=30,
            )
            if r.status_code != 200:
                break
            batch = r.json()
            if not batch:
                break
            issues.extend([i["title"] for i in batch])
            page += 1
        return issues
    except:
        return []


# ============================================================
# SELENIUM SSO HELPERS
# ============================================================
def get_selenium_driver():
    """Create a headless Chrome driver."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        options = Options()
        options.binary_location = CHROME_PATH
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--ignore-certificate-errors")

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        print(f"  [SELENIUM ERROR] Cannot create driver: {e}")
        return None


def selenium_login(driver, email="ananya@technova.in", password="Welcome@123"):
    """Login to EMP Cloud via Selenium."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        driver.get(f"{CORE_FE}/login")
        time.sleep(3)

        # Try different selectors for email
        for sel in ['input[name="email"]', 'input[type="email"]', '#email', 'input[placeholder*="email" i]']:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                el.clear()
                el.send_keys(email)
                break
            except:
                continue

        # Password
        for sel in ['input[name="password"]', 'input[type="password"]', '#password']:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                el.clear()
                el.send_keys(password)
                break
            except:
                continue

        # Submit
        for sel in ['button[type="submit"]', 'button:has-text("Login")', 'button:has-text("Sign in")',
                     'button.login-btn', 'form button']:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                el.click()
                break
            except:
                continue

        time.sleep(5)
        return True
    except Exception as e:
        print(f"  [SELENIUM LOGIN ERROR] {e}")
        return False


def selenium_sso_to_module(driver, module_name, module_fe_url):
    """Navigate to a module via SSO from dashboard."""
    from selenium.webdriver.common.by import By

    try:
        # Try navigating to modules page
        driver.get(f"{CORE_FE}/modules")
        time.sleep(3)

        # Take screenshot of modules page
        sshot_path = str(SCREENSHOT_DIR / f"{module_name}_modules_page.png")
        driver.save_screenshot(sshot_path)

        # Try to find and click the module launch button
        found = False
        for text_match in [module_name.lower(), module_name.replace("-", " ").lower()]:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='module'], [class*='Card']")
                for card in cards:
                    if text_match in card.text.lower():
                        # Find launch button within card
                        btns = card.find_elements(By.CSS_SELECTOR, "a, button")
                        for btn in btns:
                            if any(kw in btn.text.lower() for kw in ["launch", "open", "go", "access"]):
                                btn.click()
                                found = True
                                break
                        if found:
                            break
            except:
                continue
            if found:
                break

        if not found:
            # Fallback: direct navigation
            driver.get(module_fe_url)

        time.sleep(5)

        # Take screenshot of module landing
        sshot_path = str(SCREENSHOT_DIR / f"{module_name}_landing.png")
        driver.save_screenshot(sshot_path)

        return driver.current_url
    except Exception as e:
        print(f"  [SSO ERROR] {module_name}: {e}")
        return None


def selenium_navigate_and_screenshot(driver, module_name, pages):
    """Navigate to module pages and take screenshots."""
    from selenium.webdriver.common.by import By

    results_sso = []
    for page_name, page_url in pages.items():
        try:
            driver.get(page_url)
            time.sleep(3)
            sshot_file = f"{module_name}_{page_name.replace(' ', '_').replace('/', '_')}.png"
            sshot_path = str(SCREENSHOT_DIR / sshot_file)
            driver.save_screenshot(sshot_path)

            # Check if page loaded (not error page)
            title = driver.title or ""
            body_text = ""
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
            except:
                pass

            has_error = any(kw in (title + body_text).lower() for kw in
                          ["404", "not found", "error", "cannot", "refused", "500"])

            results_sso.append({
                "module": module_name,
                "page": page_name,
                "url": page_url,
                "current_url": driver.current_url,
                "passed": not has_error,
                "screenshot": sshot_path,
            })

            status = "PASS" if not has_error else "FAIL"
            print(f"  [{status}] SSO {module_name} -> {page_name} | {driver.current_url[:80]}")
        except Exception as e:
            print(f"  [ERROR] SSO {module_name} -> {page_name}: {e}")
            results_sso.append({
                "module": module_name,
                "page": page_name,
                "url": page_url,
                "passed": False,
                "error": str(e),
            })
    return results_sso


# ============================================================
# STEP 2: TEST ALL CORE HRMS ENDPOINTS
# ============================================================
def test_core_hrms():
    """Test every core EMP Cloud endpoint."""
    print("\n" + "="*80)
    print("STEP 2: TESTING ALL CORE HRMS ENDPOINTS")
    print("="*80)

    token = login("technova")
    if not token:
        print("FATAL: Cannot login as TechNova admin")
        return

    B = CORE_API
    h = auth_headers(token)

    # ----- AUTH -----
    print("\n--- Auth ---")
    test_endpoint("Core", "POST", f"{B}/api/v1/auth/login", "Login",
                  body={"email": "ananya@technova.in", "password": "Welcome@123"},
                  ref_section="Auth")
    test_endpoint("Core", "POST", f"{B}/api/v1/auth/register", "Register (expect validation)",
                  body={"email": "test_reg@test.com", "password": "Test@12345", "name": "Test Reg"},
                  expected_codes=[200, 201, 400, 409, 422], ref_section="Auth")
    test_endpoint("Core", "POST", f"{B}/api/v1/auth/password-reset", "Password reset",
                  body={"email": "ananya@technova.in"},
                  expected_codes=[200, 201, 400, 404, 422], ref_section="Auth")
    test_endpoint("Core", "POST", f"{B}/api/v1/auth/sso/validate", "SSO validate (expect error w/o token)",
                  body={"sso_token": "fake_token"},
                  expected_codes=[200, 400, 401, 422], ref_section="Auth")

    # ----- OAUTH / OIDC -----
    print("\n--- OAuth/OIDC ---")
    test_endpoint("Core", "GET", f"{B}/.well-known/openid-configuration", "OIDC discovery",
                  ref_section="OAuth")
    test_endpoint("Core", "GET", f"{B}/oauth/jwks", "JWKS",
                  ref_section="OAuth")
    test_endpoint("Core", "POST", f"{B}/oauth/token", "Token exchange (expect error)",
                  body={"grant_type": "authorization_code", "code": "fake"},
                  expected_codes=[200, 400, 401], ref_section="OAuth")
    test_endpoint("Core", "POST", f"{B}/oauth/revoke", "Token revoke",
                  body={"token": "fake"},
                  expected_codes=[200, 400, 401], ref_section="OAuth")
    test_endpoint("Core", "POST", f"{B}/oauth/introspect", "Token introspect",
                  body={"token": token},
                  expected_codes=[200, 400, 401], ref_section="OAuth")

    # ----- ORGANIZATIONS -----
    print("\n--- Organizations ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/organizations/me", "Get current org",
                  token=token, ref_section="Organizations")
    test_endpoint("Core", "PUT", f"{B}/api/v1/organizations/me", "Update org (no change)",
                  token=token, body={"name": "TechNova"},
                  expected_codes=[200, 400], ref_section="Organizations")
    test_endpoint("Core", "GET", f"{B}/api/v1/organizations/me/departments", "List departments",
                  token=token, ref_section="Organizations")
    test_endpoint("Core", "POST", f"{B}/api/v1/organizations/me/departments", "Create department",
                  token=token, body={"name": f"TestDept_{int(time.time())}"},
                  expected_codes=[200, 201, 400, 409], ref_section="Organizations")
    test_endpoint("Core", "GET", f"{B}/api/v1/organizations/me/locations", "List locations",
                  token=token, ref_section="Organizations")
    test_endpoint("Core", "POST", f"{B}/api/v1/organizations/me/locations", "Create location",
                  token=token, body={"name": f"TestLoc_{int(time.time())}", "address": "Test Addr"},
                  expected_codes=[200, 201, 400, 409], ref_section="Organizations")

    # ----- USERS -----
    print("\n--- Users ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/users", "List users",
                  token=token, ref_section="Users")
    test_endpoint("Core", "POST", f"{B}/api/v1/users/invite", "Invite user",
                  token=token, body={"email": f"invite_{int(time.time())}@test.com", "role": "employee"},
                  expected_codes=[200, 201, 400, 409, 422], ref_section="Users")

    # Get user list for ID
    r = requests.get(f"{B}/api/v1/users", headers=h, timeout=TIMEOUT)
    user_id = None
    if r.status_code == 200:
        data = r.json().get("data", [])
        if isinstance(data, list) and len(data) > 0:
            user_id = data[0].get("id")
        elif isinstance(data, dict):
            users_list = data.get("users", data.get("items", []))
            if users_list and len(users_list) > 0:
                user_id = users_list[0].get("id")

    if user_id:
        test_endpoint("Core", "GET", f"{B}/api/v1/users/{user_id}", "Get user detail",
                      token=token, ref_section="Users")
        test_endpoint("Core", "PUT", f"{B}/api/v1/users/{user_id}", "Update user",
                      token=token, body={"name": "Test Update"},
                      expected_codes=[200, 400, 403], ref_section="Users")
        test_endpoint("Core", "PUT", f"{B}/api/v1/users/{user_id}/roles", "Assign roles",
                      token=token, body={"roles": ["employee"]},
                      expected_codes=[200, 400, 403], ref_section="Users")

    # ----- MODULES & SUBSCRIPTIONS -----
    print("\n--- Modules & Subscriptions ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/modules", "List modules",
                  token=token, ref_section="Modules")
    test_endpoint("Core", "GET", f"{B}/api/v1/modules/1", "Get module detail",
                  token=token, expected_codes=[200, 404], ref_section="Modules")
    test_endpoint("Core", "GET", f"{B}/api/v1/subscriptions", "List subscriptions",
                  token=token, ref_section="Subscriptions")

    # ----- EMPLOYEES -----
    print("\n--- Employees ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/employees", "Employee directory",
                  token=token, ref_section="Employees")

    emp_id = TECHNOVA_EMP_ID
    test_endpoint("Core", "GET", f"{B}/api/v1/employees/{emp_id}", "Employee profile",
                  token=token, ref_section="Employees")
    test_endpoint("Core", "GET", f"{B}/api/v1/employees/{emp_id}/profile", "Extended profile",
                  token=token, ref_section="Employees")
    test_endpoint("Core", "GET", f"{B}/api/v1/employees/{emp_id}/addresses", "Addresses",
                  token=token, ref_section="Employees")
    test_endpoint("Core", "GET", f"{B}/api/v1/employees/{emp_id}/education", "Education",
                  token=token, ref_section="Employees")
    test_endpoint("Core", "GET", f"{B}/api/v1/employees/{emp_id}/experience", "Experience",
                  token=token, ref_section="Employees")
    test_endpoint("Core", "GET", f"{B}/api/v1/employees/{emp_id}/dependents", "Dependents",
                  token=token, ref_section="Employees")
    test_endpoint("Core", "GET", f"{B}/api/v1/employees/{emp_id}/photo", "Photo",
                  token=token, expected_codes=[200, 404], ref_section="Employees")
    test_endpoint("Core", "GET", f"{B}/api/v1/employees/org-chart", "Org chart",
                  token=token, ref_section="Employees")

    # ----- ATTENDANCE -----
    print("\n--- Attendance ---")
    test_endpoint("Core", "POST", f"{B}/api/v1/attendance/check-in", "Check-in",
                  token=token, body={"timestamp": datetime.now().isoformat()},
                  expected_codes=[200, 201, 400, 409], ref_section="Attendance")
    test_endpoint("Core", "POST", f"{B}/api/v1/attendance/check-out", "Check-out",
                  token=token, body={"timestamp": datetime.now().isoformat()},
                  expected_codes=[200, 201, 400, 409], ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/records", "Records",
                  token=token, ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/records?department_id={TECHNOVA_DEPT_ID}",
                  "Records by department", token=token, ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/records?date=2026-03-28",
                  "Records by date", token=token, ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/dashboard", "Dashboard",
                  token=token, ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/reports", "Reports",
                  token=token, ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/export", "Export CSV",
                  token=token, ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/shifts", "List shifts",
                  token=token, ref_section="Attendance")
    test_endpoint("Core", "POST", f"{B}/api/v1/attendance/shifts", "Create shift",
                  token=token, body={"name": f"TestShift_{int(time.time())}", "start_time": "09:00", "end_time": "17:00"},
                  expected_codes=[200, 201, 400, 409], ref_section="Attendance")
    test_endpoint("Core", "PUT", f"{B}/api/v1/attendance/shifts/{TECHNOVA_SHIFT_ID}", "Update shift",
                  token=token, body={"name": "General Shift"},
                  expected_codes=[200, 400], ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/shift-assignments", "Shift assignments",
                  token=token, ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/geo-fences", "Geo-fences",
                  token=token, ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/regularizations", "Regularizations",
                  token=token, ref_section="Attendance")
    test_endpoint("Core", "GET", f"{B}/api/v1/attendance/schedule", "Schedule",
                  token=token, ref_section="Attendance")

    # ----- LEAVE -----
    print("\n--- Leave ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/leave/types", "Leave types",
                  token=token, ref_section="Leave")
    test_endpoint("Core", "GET", f"{B}/api/v1/leave/policies", "Leave policies",
                  token=token, ref_section="Leave")
    test_endpoint("Core", "GET", f"{B}/api/v1/leave/balances", "Leave balances",
                  token=token, ref_section="Leave")
    test_endpoint("Core", "GET", f"{B}/api/v1/leave/applications", "Applications",
                  token=token, ref_section="Leave")
    test_endpoint("Core", "POST", f"{B}/api/v1/leave/applications", "Apply for leave",
                  token=token, body={
                      "leave_type_id": TECHNOVA_LEAVE_TYPE_ID,
                      "start_date": "2026-04-15",
                      "end_date": "2026-04-15",
                      "reason": "API test leave"
                  }, expected_codes=[200, 201, 400, 409, 422], ref_section="Leave")
    test_endpoint("Core", "GET", f"{B}/api/v1/leave/calendar", "Calendar",
                  token=token, ref_section="Leave")
    test_endpoint("Core", "GET", f"{B}/api/v1/leave/comp-off", "Comp-off",
                  token=token, ref_section="Leave")
    test_endpoint("Core", "GET", f"{B}/api/v1/leave/dashboard", "Dashboard",
                  token=token, ref_section="Leave")

    # ----- DOCUMENTS -----
    print("\n--- Documents ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/documents", "List documents",
                  token=token, ref_section="Documents")
    test_endpoint("Core", "GET", f"{B}/api/v1/documents/categories", "Categories",
                  token=token, ref_section="Documents")
    test_endpoint("Core", "GET", f"{B}/api/v1/documents/my", "My documents",
                  token=token, ref_section="Documents")
    test_endpoint("Core", "GET", f"{B}/api/v1/documents/mandatory", "Mandatory docs",
                  token=token, ref_section="Documents")
    test_endpoint("Core", "GET", f"{B}/api/v1/documents/expiry-alerts", "Expiry alerts",
                  token=token, ref_section="Documents")

    # ----- ANNOUNCEMENTS -----
    print("\n--- Announcements ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/announcements", "List announcements",
                  token=token, ref_section="Announcements")
    test_endpoint("Core", "POST", f"{B}/api/v1/announcements", "Create announcement",
                  token=token, body={
                      "title": f"Test Announcement {int(time.time())}",
                      "content": "API reference test",
                  }, expected_codes=[200, 201, 400], ref_section="Announcements")
    test_endpoint("Core", "GET", f"{B}/api/v1/announcements/unread-count", "Unread count",
                  token=token, ref_section="Announcements")

    # ----- POLICIES -----
    print("\n--- Policies ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/policies", "List policies",
                  token=token, ref_section="Policies")
    test_endpoint("Core", "POST", f"{B}/api/v1/policies", "Create policy",
                  token=token, body={
                      "title": f"Test Policy {int(time.time())}",
                      "content": "Test policy content",
                  }, expected_codes=[200, 201, 400], ref_section="Policies")
    test_endpoint("Core", "GET", f"{B}/api/v1/policies/pending", "Pending acknowledgments",
                  token=token, ref_section="Policies")

    # ----- NOTIFICATIONS -----
    print("\n--- Notifications ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/notifications", "List notifications",
                  token=token, ref_section="Notifications")
    test_endpoint("Core", "POST", f"{B}/api/v1/notifications/read-all", "Mark all read",
                  token=token, expected_codes=[200, 201, 204], ref_section="Notifications")
    test_endpoint("Core", "GET", f"{B}/api/v1/notifications/unread-count", "Unread count",
                  token=token, ref_section="Notifications")
    test_endpoint("Core", "GET", f"{B}/api/v1/notifications/preferences", "Preferences",
                  token=token, ref_section="Notifications")

    # ----- DASHBOARD -----
    print("\n--- Dashboard ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/dashboard/widgets", "Widgets",
                  token=token, ref_section="Dashboard")
    test_endpoint("Core", "GET", f"{B}/api/v1/dashboard/module-summaries", "Module summaries",
                  token=token, ref_section="Dashboard")
    test_endpoint("Core", "GET", f"{B}/api/v1/dashboard/module-insights", "Module insights",
                  token=token, ref_section="Dashboard")

    # ----- BILLING -----
    print("\n--- Billing ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/billing/invoices", "Invoices",
                  token=token, ref_section="Billing")

    # ----- AI / CHATBOT -----
    print("\n--- AI / Chatbot ---")
    test_endpoint("Core", "POST", f"{B}/api/v1/chatbot/message", "Send message",
                  token=token, body={"message": "Hello, what modules are available?"},
                  expected_codes=[200, 201, 400, 500, 503], ref_section="AI Agent")
    test_endpoint("Core", "GET", f"{B}/api/v1/chatbot/conversations", "Conversations",
                  token=token, ref_section="AI Agent")
    test_endpoint("Core", "GET", f"{B}/api/v1/ai-config", "AI config",
                  token=token, ref_section="AI Config")

    # ----- ADMIN -----
    print("\n--- Admin (may require super admin) ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/admin/organizations", "List all orgs",
                  token=token, expected_codes=[200, 401, 403], ref_section="Admin")
    test_endpoint("Core", "GET", f"{B}/api/v1/admin/health", "Service health",
                  token=token, expected_codes=[200, 401, 403], ref_section="Admin")
    test_endpoint("Core", "GET", f"{B}/api/v1/admin/data-sanity", "Data sanity",
                  token=token, expected_codes=[200, 401, 403], ref_section="Admin")
    test_endpoint("Core", "GET", f"{B}/api/v1/admin/stats", "Platform stats",
                  token=token, expected_codes=[200, 401, 403], ref_section="Admin")

    # ----- LOGS -----
    print("\n--- Logs ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/logs", "Query logs",
                  token=token, expected_codes=[200, 401, 403], ref_section="Logs")
    test_endpoint("Core", "GET", f"{B}/api/v1/logs/analysis", "Log analysis",
                  token=token, expected_codes=[200, 401, 403], ref_section="Logs")

    # ----- HELPDESK -----
    print("\n--- Helpdesk ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/helpdesk/tickets", "List tickets",
                  token=token, ref_section="Helpdesk")
    test_endpoint("Core", "POST", f"{B}/api/v1/helpdesk/tickets", "Create ticket",
                  token=token, body={
                      "subject": f"Test Ticket {int(time.time())}",
                      "description": "API test ticket",
                      "priority": "medium",
                  }, expected_codes=[200, 201, 400], ref_section="Helpdesk")
    test_endpoint("Core", "GET", f"{B}/api/v1/helpdesk/categories", "Categories",
                  token=token, ref_section="Helpdesk")
    test_endpoint("Core", "GET", f"{B}/api/v1/helpdesk/knowledge-base", "Knowledge base",
                  token=token, ref_section="Helpdesk")

    # ----- SURVEYS -----
    print("\n--- Surveys ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/surveys", "List surveys",
                  token=token, ref_section="Surveys")
    test_endpoint("Core", "POST", f"{B}/api/v1/surveys", "Create survey",
                  token=token, body={
                      "title": f"Test Survey {int(time.time())}",
                      "questions": [{"text": "How are you?", "type": "text"}],
                  }, expected_codes=[200, 201, 400], ref_section="Surveys")

    # ----- ASSETS -----
    print("\n--- Assets ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/assets", "List assets",
                  token=token, ref_section="Assets")
    test_endpoint("Core", "POST", f"{B}/api/v1/assets", "Create asset",
                  token=token, body={
                      "name": f"Test Laptop {int(time.time())}",
                      "type": "laptop",
                      "serial_number": f"SN{int(time.time())}",
                  }, expected_codes=[200, 201, 400], ref_section="Assets")
    test_endpoint("Core", "GET", f"{B}/api/v1/assets/categories", "Asset categories",
                  token=token, ref_section="Assets")
    test_endpoint("Core", "GET", f"{B}/api/v1/assets/my", "My assets",
                  token=token, ref_section="Assets")

    # ----- POSITIONS -----
    print("\n--- Positions ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/positions", "List positions",
                  token=token, ref_section="Positions")
    test_endpoint("Core", "POST", f"{B}/api/v1/positions", "Create position",
                  token=token, body={
                      "title": f"Test Position {int(time.time())}",
                      "department_id": TECHNOVA_DEPT_ID,
                  }, expected_codes=[200, 201, 400], ref_section="Positions")
    test_endpoint("Core", "GET", f"{B}/api/v1/positions/headcount", "Headcount",
                  token=token, ref_section="Positions")

    # ----- FORUM -----
    print("\n--- Forum ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/forum/categories", "Forum categories",
                  token=token, ref_section="Forum")
    test_endpoint("Core", "GET", f"{B}/api/v1/forum/posts", "Forum posts",
                  token=token, ref_section="Forum")
    test_endpoint("Core", "POST", f"{B}/api/v1/forum/posts", "Create post",
                  token=token, body={
                      "title": f"Test Post {int(time.time())}",
                      "content": "API reference test post",
                  }, expected_codes=[200, 201, 400], ref_section="Forum")

    # ----- EVENTS -----
    print("\n--- Events ---")
    test_endpoint("Core", "GET", f"{B}/api/v1/events", "List events",
                  token=token, ref_section="Events")
    test_endpoint("Core", "POST", f"{B}/api/v1/events", "Create event",
                  token=token, body={
                      "title": f"Test Event {int(time.time())}",
                      "date": "2026-04-15",
                      "location": "Conference Room A",
                  }, expected_codes=[200, 201, 400], ref_section="Events")
    test_endpoint("Core", "GET", f"{B}/api/v1/events/calendar", "Events calendar",
                  token=token, ref_section="Events")

    # ----- WELLNESS -----
    try:
        print("\n--- Wellness ---")
        sys.stdout.flush()
        test_endpoint("Core", "GET", f"{B}/api/v1/wellness/dashboard", "Dashboard",
                      token=token, ref_section="Wellness")
        test_endpoint("Core", "POST", f"{B}/api/v1/wellness/check-in", "Check-in",
                      token=token, body={"mood": "good", "energy": 4},
                      expected_codes=[200, 201, 400], ref_section="Wellness")
        test_endpoint("Core", "GET", f"{B}/api/v1/wellness/goals", "Goals",
                      token=token, ref_section="Wellness")
    except Exception as e:
        print(f"  [SECTION ERROR] Wellness: {e}")

    # ----- FEEDBACK -----
    try:
        print("\n--- Feedback ---")
        sys.stdout.flush()
        test_endpoint("Core", "POST", f"{B}/api/v1/feedback", "Submit feedback",
                      token=token, body={"message": "API reference test feedback"},
                      expected_codes=[200, 201, 400], ref_section="Feedback")
        test_endpoint("Core", "GET", f"{B}/api/v1/feedback", "List feedback",
                      token=token, ref_section="Feedback")
    except Exception as e:
        print(f"  [SECTION ERROR] Feedback: {e}")

    # ----- WHISTLEBLOWING -----
    try:
        print("\n--- Whistleblowing ---")
        sys.stdout.flush()
        test_endpoint("Core", "POST", f"{B}/api/v1/whistleblowing", "Submit report",
                      token=token, body={"description": "API test report", "category": "test"},
                      expected_codes=[200, 201, 400], ref_section="Whistleblowing")
        test_endpoint("Core", "GET", f"{B}/api/v1/whistleblowing", "List reports",
                      token=token, ref_section="Whistleblowing")
    except Exception as e:
        print(f"  [SECTION ERROR] Whistleblowing: {e}")

    # ----- CUSTOM FIELDS -----
    try:
        print("\n--- Custom Fields ---")
        sys.stdout.flush()
        test_endpoint("Core", "GET", f"{B}/api/v1/custom-fields/definitions", "Definitions",
                      token=token, ref_section="Custom Fields")
        test_endpoint("Core", "GET", f"{B}/api/v1/custom-fields/values/employee/{emp_id}", "Values",
                      token=token, ref_section="Custom Fields")
    except Exception as e:
        print(f"  [SECTION ERROR] Custom Fields: {e}")

    # ----- BIOMETRICS -----
    try:
        print("\n--- Biometrics ---")
        sys.stdout.flush()
        test_endpoint("Core", "GET", f"{B}/api/v1/biometrics/devices", "Devices",
                      token=token, ref_section="Biometrics")
        test_endpoint("Core", "POST", f"{B}/api/v1/biometrics/qr/generate", "QR generate",
                      token=token, body={},
                      expected_codes=[200, 201, 400], ref_section="Biometrics")
    except Exception as e:
        print(f"  [SECTION ERROR] Biometrics: {e}")

    # ----- MANAGER -----
    try:
        print("\n--- Manager ---")
        sys.stdout.flush()
        test_endpoint("Core", "GET", f"{B}/api/v1/manager/dashboard", "Manager dashboard",
                      token=token, expected_codes=[200, 401, 403], ref_section="Manager")
        test_endpoint("Core", "GET", f"{B}/api/v1/manager/team", "Team",
                      token=token, expected_codes=[200, 401, 403], ref_section="Manager")
    except Exception as e:
        print(f"  [SECTION ERROR] Manager: {e}")

    # ----- IMPORT -----
    try:
        print("\n--- Import ---")
        sys.stdout.flush()
        test_endpoint("Core", "GET", f"{B}/api/v1/import/history", "Import history",
                      token=token, ref_section="Import")
    except Exception as e:
        print(f"  [SECTION ERROR] Import: {e}")

    # ----- AUDIT -----
    try:
        print("\n--- Audit ---")
        sys.stdout.flush()
        test_endpoint("Core", "GET", f"{B}/api/v1/audit", "Audit log",
                      token=token, ref_section="Audit")
    except Exception as e:
        print(f"  [SECTION ERROR] Audit: {e}")

    # ----- SYSTEM -----
    try:
        print("\n--- System ---")
        sys.stdout.flush()
        test_endpoint("Core", "GET", f"{B}/health", "Health check",
                      ref_section="System")
        test_endpoint("Core", "GET", f"{B}/api/docs", "Swagger UI",
                      expected_codes=[200, 301, 302], ref_section="System")
    except Exception as e:
        print(f"  [SECTION ERROR] System: {e}")


# ============================================================
# STEP 2b: TEST ALL PAYROLL ENDPOINTS (via API)
# ============================================================
def test_payroll_api():
    """Test Payroll module endpoints via direct API."""
    print("\n" + "="*80)
    print("TESTING PAYROLL MODULE API ENDPOINTS")
    print("="*80)

    B = PAYROLL_API

    # Login to payroll
    print("\n--- Payroll Auth ---")
    r = test_endpoint("Payroll", "POST", f"{B}/api/v1/auth/login", "Login",
                      body={"email": "ananya@technova.in", "password": "Welcome@123"},
                      ref_section="Payroll Auth")

    pay_token = None
    if r and r.status_code == 200:
        pay_token = extract_token(r.json())

    if not pay_token:
        print("  [WARN] No payroll token, using core token for API probing")
        pay_token = login("technova")

    # Employees
    print("\n--- Payroll Employees ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/employees", "List employees",
                  token=pay_token, ref_section="Payroll Employees")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/employees/export", "Export CSV",
                  token=pay_token, ref_section="Payroll Employees")

    # Payroll Runs
    print("\n--- Payroll Runs ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/payroll", "List runs",
                  token=pay_token, ref_section="Payroll Runs")
    test_endpoint("Payroll", "POST", f"{B}/api/v1/payroll", "Create run",
                  token=pay_token, body={
                      "month": 3, "year": 2026,
                      "name": f"Test Run {int(time.time())}"
                  }, expected_codes=[200, 201, 400, 409], ref_section="Payroll Runs")

    # Salary Structures
    print("\n--- Salary Structures ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/salary-structures", "List structures",
                  token=pay_token, ref_section="Salary Structures")

    # Benefits
    print("\n--- Benefits ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/benefits/dashboard", "Dashboard",
                  token=pay_token, ref_section="Benefits")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/benefits/plans", "Plans",
                  token=pay_token, ref_section="Benefits")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/benefits/my", "My benefits",
                  token=pay_token, ref_section="Benefits")

    # Insurance
    print("\n--- Insurance ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/insurance/dashboard", "Dashboard",
                  token=pay_token, ref_section="Insurance")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/insurance/policies", "Policies",
                  token=pay_token, ref_section="Insurance")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/insurance/claims", "Claims",
                  token=pay_token, ref_section="Insurance")

    # GL Accounting
    print("\n--- GL Accounting ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/gl-accounting/mappings", "Mappings",
                  token=pay_token, ref_section="GL Accounting")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/gl-accounting/journal-entries", "Entries",
                  token=pay_token, ref_section="GL Accounting")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/gl-accounting/period-summary", "Period summary",
                  token=pay_token, ref_section="GL Accounting")

    # Global Payroll
    print("\n--- Global Payroll ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/global-payroll/dashboard", "Dashboard",
                  token=pay_token, ref_section="Global Payroll")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/global-payroll/countries", "Countries",
                  token=pay_token, ref_section="Global Payroll")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/global-payroll/employees", "Employees",
                  token=pay_token, ref_section="Global Payroll")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/global-payroll/compliance", "Compliance",
                  token=pay_token, ref_section="Global Payroll")

    # Earned Wage Access
    print("\n--- Earned Wage Access ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/earned-wage/settings", "Settings",
                  token=pay_token, ref_section="EWA")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/earned-wage/requests", "Requests",
                  token=pay_token, ref_section="EWA")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/earned-wage/my/eligibility", "My eligibility",
                  token=pay_token, ref_section="EWA")

    # Pay Equity
    print("\n--- Pay Equity ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/pay-equity/analysis", "Analysis",
                  token=pay_token, ref_section="Pay Equity")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/pay-equity/compliance-report", "Report",
                  token=pay_token, ref_section="Pay Equity")

    # Compensation Benchmarks
    print("\n--- Compensation Benchmarks ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/compensation-benchmarks", "List",
                  token=pay_token, ref_section="Compensation Benchmarks")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/compensation-benchmarks/comparison", "Comparison",
                  token=pay_token, ref_section="Compensation Benchmarks")

    # Self-Service
    print("\n--- Self-Service ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/self-service/dashboard", "Dashboard",
                  token=pay_token, ref_section="Self-Service")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/self-service/payslips", "Payslips",
                  token=pay_token, ref_section="Self-Service")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/self-service/salary", "Salary",
                  token=pay_token, ref_section="Self-Service")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/self-service/tax/computation", "Tax computation",
                  token=pay_token, ref_section="Self-Service")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/self-service/tax/declarations", "Declarations",
                  token=pay_token, ref_section="Self-Service")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/self-service/tax/form16", "Form 16",
                  token=pay_token, ref_section="Self-Service")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/self-service/reimbursements", "Reimbursements",
                  token=pay_token, ref_section="Self-Service")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/self-service/profile", "Profile",
                  token=pay_token, ref_section="Self-Service")

    # Other
    print("\n--- Other Payroll ---")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/attendance", "Attendance summary",
                  token=pay_token, ref_section="Payroll Other")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/leaves", "Leave balances",
                  token=pay_token, ref_section="Payroll Other")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/loans", "Loans",
                  token=pay_token, ref_section="Payroll Other")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/reimbursements", "Reimbursements",
                  token=pay_token, ref_section="Payroll Other")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/adjustments", "Adjustments",
                  token=pay_token, ref_section="Payroll Other")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/announcements", "Announcements",
                  token=pay_token, ref_section="Payroll Other")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/organizations", "Org settings",
                  token=pay_token, ref_section="Payroll Other")
    test_endpoint("Payroll", "GET", f"{B}/health", "Health",
                  ref_section="Payroll System")
    test_endpoint("Payroll", "GET", f"{B}/api/v1/docs/openapi.json", "OpenAPI spec",
                  ref_section="Payroll System")


# ============================================================
# TEST MODULE ENDPOINTS (Recruit, Performance, Rewards, Exit, LMS)
# ============================================================
def test_module_api(module_name, base_url, endpoints):
    """Generic module API tester."""
    print(f"\n{'='*80}")
    print(f"TESTING {module_name.upper()} MODULE API ENDPOINTS")
    print(f"{'='*80}")

    # Try SSO auth first
    core_token = login("technova")
    mod_token = core_token  # fallback

    # Try module-specific auth
    print(f"\n--- {module_name} Auth ---")
    for auth_path in ["/api/v1/auth/sso", "/api/v1/auth/login"]:
        if "sso" in auth_path:
            body = {"sso_token": "test"}
        else:
            body = {"email": "ananya@technova.in", "password": "Welcome@123"}
        r = test_endpoint(module_name, "POST", f"{base_url}{auth_path}", f"{module_name} auth",
                          body=body, expected_codes=[200, 201, 400, 401, 422],
                          ref_section=f"{module_name} Auth")
        if r and r.status_code == 200:
            t = extract_token(r.json())
            if t:
                mod_token = t
                break

    for ep in endpoints:
        method = ep.get("method", "GET")
        path = ep["path"]
        desc = ep.get("desc", path)
        body = ep.get("body", None)
        codes = ep.get("codes", None)
        section = ep.get("section", module_name)

        test_endpoint(module_name, method, f"{base_url}{path}", desc,
                      token=mod_token, body=body,
                      expected_codes=codes, ref_section=section)


def test_recruit_api():
    recruit_endpoints = [
        # Jobs
        {"method": "GET", "path": "/api/v1/jobs", "desc": "List jobs", "section": "Recruit Jobs"},
        {"method": "POST", "path": "/api/v1/jobs", "desc": "Create job", "body": {
            "title": f"Test Engineer {int(time.time())}", "department": "Engineering",
            "description": "API test job", "location": "Remote"
        }, "codes": [200, 201, 400, 401], "section": "Recruit Jobs"},
        # JD Generator
        {"method": "POST", "path": "/api/v1/job-descriptions/generate", "desc": "Generate AI JD",
         "body": {"title": "Senior Engineer", "department": "Engineering"},
         "codes": [200, 201, 400, 401, 500], "section": "Recruit AI JD"},
        {"method": "GET", "path": "/api/v1/job-descriptions/templates", "desc": "JD templates", "section": "Recruit AI JD"},
        # Candidates
        {"method": "GET", "path": "/api/v1/candidates", "desc": "List candidates", "section": "Recruit Candidates"},
        {"method": "POST", "path": "/api/v1/candidates", "desc": "Create candidate",
         "body": {"name": "Test Candidate", "email": f"cand_{int(time.time())}@test.com"},
         "codes": [200, 201, 400, 401], "section": "Recruit Candidates"},
        # Applications
        {"method": "GET", "path": "/api/v1/applications", "desc": "List applications", "section": "Recruit ATS"},
        # Interviews
        {"method": "GET", "path": "/api/v1/interviews", "desc": "List interviews", "section": "Recruit Interviews"},
        # Pipeline
        {"method": "GET", "path": "/api/v1/pipeline-stages", "desc": "Pipeline stages", "section": "Recruit Pipeline"},
        # AI
        {"method": "POST", "path": "/api/v1/ai/score-resume", "desc": "Score resume",
         "body": {"resume_text": "Test resume", "job_id": 1},
         "codes": [200, 201, 400, 401, 500], "section": "Recruit AI"},
        {"method": "POST", "path": "/api/v1/ai/batch-score", "desc": "Batch score",
         "body": {"job_id": 1, "candidate_ids": [1]},
         "codes": [200, 201, 400, 401, 500], "section": "Recruit AI"},
        # Background Checks
        {"method": "GET", "path": "/api/v1/background-checks/candidate/1", "desc": "Background checks",
         "codes": [200, 400, 401, 404], "section": "Recruit BGC"},
        # Onboarding
        {"method": "GET", "path": "/api/v1/onboarding/templates", "desc": "Templates", "section": "Recruit Onboarding"},
        # Portal
        {"method": "POST", "path": "/api/v1/portal/send-magic-link", "desc": "Magic link",
         "body": {"email": "test@test.com"}, "codes": [200, 201, 400, 401], "section": "Recruit Portal"},
        # Public
        {"method": "GET", "path": "/api/v1/public/careers/technova", "desc": "Public career page",
         "codes": [200, 404], "section": "Recruit Public"},
        # Surveys
        {"method": "GET", "path": "/api/v1/surveys/1", "desc": "Survey", "codes": [200, 404, 401], "section": "Recruit Surveys"},
        # Assessments
        {"method": "GET", "path": "/api/v1/assessments/1", "desc": "Assessment", "codes": [200, 404, 401], "section": "Recruit Assessments"},
        # Health
        {"method": "GET", "path": "/health", "desc": "Health check", "section": "Recruit System"},
        {"method": "GET", "path": "/api/docs", "desc": "Swagger UI", "codes": [200, 301, 302], "section": "Recruit System"},
    ]
    test_module_api("Recruit", RECRUIT_API, recruit_endpoints)


def test_performance_api():
    perf_endpoints = [
        # Review Cycles
        {"method": "GET", "path": "/api/v1/review-cycles", "desc": "List cycles", "section": "Perf Cycles"},
        {"method": "POST", "path": "/api/v1/review-cycles", "desc": "Create cycle",
         "body": {"name": f"Test Cycle {int(time.time())}", "type": "annual",
                  "start_date": "2026-04-01", "end_date": "2026-06-30"},
         "codes": [200, 201, 400, 401], "section": "Perf Cycles"},
        # Reviews
        {"method": "GET", "path": "/api/v1/reviews", "desc": "List reviews", "section": "Perf Reviews"},
        # Goals
        {"method": "GET", "path": "/api/v1/goals", "desc": "List goals", "section": "Perf Goals"},
        {"method": "POST", "path": "/api/v1/goals", "desc": "Create goal",
         "body": {"title": f"Test Goal {int(time.time())}", "description": "API test",
                  "type": "individual", "due_date": "2026-06-30"},
         "codes": [200, 201, 400, 401], "section": "Perf Goals"},
        # Goal Alignment
        {"method": "GET", "path": "/api/v1/goal-alignment/tree", "desc": "Alignment tree", "section": "Perf Goals"},
        # 9-Box
        {"method": "GET", "path": "/api/v1/nine-box", "desc": "9-box grid", "section": "Perf 9-Box"},
        # Succession
        {"method": "GET", "path": "/api/v1/succession-plans", "desc": "List plans", "section": "Perf Succession"},
        # Skills Gap
        {"method": "GET", "path": f"/api/v1/skills-gap/{TECHNOVA_EMP_ID}", "desc": "Employee gap",
         "codes": [200, 404, 401], "section": "Perf Skills"},
        # Manager Effectiveness
        {"method": "GET", "path": "/api/v1/manager-effectiveness", "desc": "All managers", "section": "Perf Manager"},
        # Competency
        {"method": "GET", "path": "/api/v1/competency-frameworks", "desc": "Frameworks", "section": "Perf Competency"},
        # PIPs
        {"method": "GET", "path": "/api/v1/pips", "desc": "List PIPs", "section": "Perf PIPs"},
        # Career Paths
        {"method": "GET", "path": "/api/v1/career-paths", "desc": "List paths", "section": "Perf Career"},
        # One-on-Ones
        {"method": "GET", "path": "/api/v1/one-on-ones", "desc": "List meetings", "section": "Perf 1on1"},
        # Feedback
        {"method": "GET", "path": "/api/v1/feedback", "desc": "List feedback", "section": "Perf Feedback"},
        {"method": "POST", "path": "/api/v1/feedback", "desc": "Give feedback",
         "body": {"to_employee_id": TECHNOVA_EMP_ID, "message": "Great work", "type": "praise"},
         "codes": [200, 201, 400, 401], "section": "Perf Feedback"},
        # Peer Reviews
        {"method": "GET", "path": "/api/v1/peer-reviews/nominations", "desc": "Nominations", "section": "Perf Peer"},
        # Letters
        {"method": "GET", "path": "/api/v1/letter-templates", "desc": "Templates", "section": "Perf Letters"},
        # Analytics
        {"method": "GET", "path": "/api/v1/analytics/overview", "desc": "Overview", "section": "Perf Analytics"},
        {"method": "GET", "path": "/api/v1/analytics/ratings-distribution", "desc": "Ratings", "section": "Perf Analytics"},
        {"method": "GET", "path": "/api/v1/analytics/team-comparison", "desc": "Team comparison", "section": "Perf Analytics"},
        {"method": "GET", "path": "/api/v1/analytics/trends", "desc": "Trends", "section": "Perf Analytics"},
        {"method": "GET", "path": "/api/v1/analytics/goal-completion", "desc": "Goal completion", "section": "Perf Analytics"},
        {"method": "GET", "path": "/api/v1/analytics/top-performers", "desc": "Top performers", "section": "Perf Analytics"},
        # Notifications
        {"method": "GET", "path": "/api/v1/notifications/settings", "desc": "Notification settings", "section": "Perf Notifications"},
        {"method": "GET", "path": "/api/v1/notifications/pending", "desc": "Pending", "section": "Perf Notifications"},
        # Health
        {"method": "GET", "path": "/health", "desc": "Health check", "section": "Perf System"},
        {"method": "GET", "path": "/api/docs", "desc": "Swagger UI", "codes": [200, 301, 302], "section": "Perf System"},
    ]
    test_module_api("Performance", PERFORMANCE_API, perf_endpoints)


def test_rewards_api():
    rewards_endpoints = [
        # Kudos
        {"method": "GET", "path": "/api/v1/kudos", "desc": "Public feed", "section": "Rewards Kudos"},
        {"method": "POST", "path": "/api/v1/kudos", "desc": "Send kudos",
         "body": {"to_employee_id": TECHNOVA_EMP_ID, "message": "Great work!", "category": "teamwork"},
         "codes": [200, 201, 400, 401], "section": "Rewards Kudos"},
        {"method": "GET", "path": "/api/v1/kudos/received", "desc": "My received", "section": "Rewards Kudos"},
        {"method": "GET", "path": "/api/v1/kudos/sent", "desc": "My sent", "section": "Rewards Kudos"},
        # Points
        {"method": "GET", "path": "/api/v1/points/balance", "desc": "Balance", "section": "Rewards Points"},
        {"method": "GET", "path": "/api/v1/points/transactions", "desc": "Transactions", "section": "Rewards Points"},
        # Badges
        {"method": "GET", "path": "/api/v1/badges", "desc": "List badges", "section": "Rewards Badges"},
        {"method": "GET", "path": "/api/v1/badges/my", "desc": "My badges", "section": "Rewards Badges"},
        # Rewards Catalog
        {"method": "GET", "path": "/api/v1/rewards", "desc": "Catalog", "section": "Rewards Catalog"},
        # Redemptions
        {"method": "GET", "path": "/api/v1/redemptions", "desc": "List", "section": "Rewards Redemptions"},
        {"method": "GET", "path": "/api/v1/redemptions/my", "desc": "My redemptions", "section": "Rewards Redemptions"},
        # Nominations
        {"method": "GET", "path": "/api/v1/nominations/programs", "desc": "Programs", "section": "Rewards Nominations"},
        # Leaderboard
        {"method": "GET", "path": "/api/v1/leaderboard", "desc": "Org leaderboard", "section": "Rewards Leaderboard"},
        {"method": "GET", "path": f"/api/v1/leaderboard/department/{TECHNOVA_DEPT_ID}", "desc": "Dept leaderboard",
         "codes": [200, 404, 401], "section": "Rewards Leaderboard"},
        {"method": "GET", "path": "/api/v1/leaderboard/my-rank", "desc": "My rank", "section": "Rewards Leaderboard"},
        # Celebrations
        {"method": "GET", "path": "/api/v1/celebrations", "desc": "Upcoming", "section": "Rewards Celebrations"},
        {"method": "GET", "path": "/api/v1/celebrations/feed", "desc": "Feed", "section": "Rewards Celebrations"},
        # Challenges
        {"method": "GET", "path": "/api/v1/challenges", "desc": "List", "section": "Rewards Challenges"},
        # Milestones
        {"method": "GET", "path": "/api/v1/milestones/rules", "desc": "Rules", "section": "Rewards Milestones"},
        {"method": "GET", "path": "/api/v1/milestones/history", "desc": "History", "section": "Rewards Milestones"},
        # Manager
        {"method": "GET", "path": "/api/v1/manager/dashboard", "desc": "Manager dashboard",
         "codes": [200, 401, 403], "section": "Rewards Manager"},
        {"method": "GET", "path": "/api/v1/manager/team-comparison", "desc": "Team comparison",
         "codes": [200, 401, 403], "section": "Rewards Manager"},
        {"method": "GET", "path": "/api/v1/manager/recommendations", "desc": "AI recs",
         "codes": [200, 401, 403], "section": "Rewards Manager"},
        # Slack
        {"method": "GET", "path": "/api/v1/slack/config", "desc": "Slack config", "section": "Rewards Slack"},
        # Teams
        {"method": "GET", "path": "/api/v1/teams", "desc": "Teams config", "section": "Rewards Teams"},
        # Push
        {"method": "GET", "path": "/api/v1/push/vapid-key", "desc": "VAPID key", "section": "Rewards Push"},
        # Integration
        {"method": "GET", "path": f"/api/v1/integration/user/1/summary", "desc": "User summary",
         "codes": [200, 404, 401], "section": "Rewards Integration"},
        # Health
        {"method": "GET", "path": "/health", "desc": "Health check", "section": "Rewards System"},
        {"method": "GET", "path": "/api/docs", "desc": "Swagger UI", "codes": [200, 301, 302], "section": "Rewards System"},
    ]
    test_module_api("Rewards", REWARDS_API, rewards_endpoints)


def test_exit_api():
    exit_endpoints = [
        # Exits
        {"method": "GET", "path": "/api/v1/exits", "desc": "List exits", "section": "Exit Requests"},
        # Self-Service
        {"method": "GET", "path": "/api/v1/self-service/my-exit", "desc": "My exit",
         "codes": [200, 404, 401], "section": "Exit Self-Service"},
        {"method": "GET", "path": "/api/v1/self-service/my-checklist", "desc": "My checklist",
         "codes": [200, 404, 401], "section": "Exit Self-Service"},
        # Checklists
        {"method": "GET", "path": "/api/v1/checklist-templates", "desc": "Templates", "section": "Exit Checklists"},
        # Clearance
        {"method": "GET", "path": "/api/v1/clearance-departments", "desc": "Departments", "section": "Exit Clearance"},
        {"method": "GET", "path": "/api/v1/my-clearances", "desc": "My clearances",
         "codes": [200, 404, 401], "section": "Exit Clearance"},
        # Interviews
        {"method": "GET", "path": "/api/v1/interview-templates", "desc": "Templates", "section": "Exit Interviews"},
        # Letters
        {"method": "GET", "path": "/api/v1/letter-templates", "desc": "Letter templates", "section": "Exit Letters"},
        # Predictions
        {"method": "GET", "path": "/api/v1/predictions/dashboard", "desc": "Predictions dashboard", "section": "Exit Predictions"},
        {"method": "GET", "path": "/api/v1/predictions/high-risk", "desc": "High risk", "section": "Exit Predictions"},
        {"method": "GET", "path": "/api/v1/predictions/trends", "desc": "Trends", "section": "Exit Predictions"},
        # Email Templates
        {"method": "GET", "path": "/api/v1/email-templates", "desc": "Email templates", "section": "Exit Emails"},
        # Rehire
        {"method": "GET", "path": "/api/v1/rehire", "desc": "List", "section": "Exit Rehire"},
        {"method": "GET", "path": "/api/v1/rehire/eligible", "desc": "Eligible alumni", "section": "Exit Rehire"},
        # NPS
        {"method": "GET", "path": "/api/v1/nps/scores", "desc": "NPS scores", "section": "Exit NPS"},
        {"method": "GET", "path": "/api/v1/nps/trends", "desc": "NPS trends", "section": "Exit NPS"},
        {"method": "GET", "path": "/api/v1/nps/responses", "desc": "NPS responses", "section": "Exit NPS"},
        # Health
        {"method": "GET", "path": "/health", "desc": "Health check", "section": "Exit System"},
        {"method": "GET", "path": "/api/docs", "desc": "Swagger UI", "codes": [200, 301, 302], "section": "Exit System"},
    ]
    test_module_api("Exit", EXIT_API, exit_endpoints)


def test_lms_api():
    lms_endpoints = [
        # Courses
        {"method": "GET", "path": "/api/v1/courses", "desc": "List courses", "section": "LMS Courses"},
        {"method": "POST", "path": "/api/v1/courses", "desc": "Create course",
         "body": {"title": f"Test Course {int(time.time())}", "description": "API test"},
         "codes": [200, 201, 400, 401], "section": "LMS Courses"},
        # Enrollments
        {"method": "GET", "path": "/api/v1/enrollments/my", "desc": "My enrollments", "section": "LMS Enrollments"},
        # Learning Paths
        {"method": "GET", "path": "/api/v1/learning-paths", "desc": "List paths", "section": "LMS Paths"},
        # Certificates
        {"method": "GET", "path": "/api/v1/certificates/my", "desc": "My certs", "section": "LMS Certs"},
        # Compliance
        {"method": "GET", "path": "/api/v1/compliance/my", "desc": "My compliance", "section": "LMS Compliance"},
        {"method": "GET", "path": "/api/v1/compliance/dashboard", "desc": "Dashboard", "section": "LMS Compliance"},
        {"method": "GET", "path": "/api/v1/compliance/overdue", "desc": "Overdue", "section": "LMS Compliance"},
        # ILT
        {"method": "GET", "path": "/api/v1/ilt", "desc": "ILT sessions", "section": "LMS ILT"},
        # Gamification
        {"method": "GET", "path": "/api/v1/gamification/leaderboard", "desc": "Leaderboard", "section": "LMS Gamification"},
        {"method": "GET", "path": "/api/v1/gamification/my", "desc": "My points", "section": "LMS Gamification"},
        {"method": "GET", "path": "/api/v1/gamification/badges", "desc": "Badges", "section": "LMS Gamification"},
        # Discussions
        {"method": "GET", "path": "/api/v1/discussions", "desc": "Discussions", "section": "LMS Discussions"},
        # Ratings
        {"method": "GET", "path": "/api/v1/ratings", "desc": "Ratings", "section": "LMS Ratings"},
        # Analytics
        {"method": "GET", "path": "/api/v1/analytics/overview", "desc": "Overview", "section": "LMS Analytics"},
        {"method": "GET", "path": "/api/v1/analytics/courses", "desc": "Course analytics", "section": "LMS Analytics"},
        {"method": "GET", "path": "/api/v1/analytics/users", "desc": "User analytics", "section": "LMS Analytics"},
        # Recommendations
        {"method": "GET", "path": "/api/v1/recommendations", "desc": "AI recs", "section": "LMS AI"},
        # Marketplace
        {"method": "GET", "path": "/api/v1/marketplace", "desc": "Marketplace", "section": "LMS Marketplace"},
        # Notifications
        {"method": "GET", "path": "/api/v1/notifications", "desc": "Notifications", "section": "LMS Notifications"},
        # Health
        {"method": "GET", "path": "/health", "desc": "Health check", "section": "LMS System"},
    ]
    test_module_api("LMS", LMS_API, lms_endpoints)


def test_project_api():
    """Test EMP Project endpoints (uses /v1/ not /api/v1/)."""
    print(f"\n{'='*80}")
    print("TESTING PROJECT MODULE API ENDPOINTS")
    print(f"{'='*80}")

    B = PROJECT_API
    token = login("technova")

    # Project uses /v1/ prefix per the reference
    project_paths = [
        ("GET", "/v1/projects", "List projects"),
        ("GET", "/v1/tasks", "List tasks"),
        ("GET", "/v1/users", "List users"),
        ("GET", "/health", "Health check"),
        ("GET", "/explorer", "Swagger explorer"),
        # Also try /api/v1/ in case
        ("GET", "/api/v1/projects", "List projects (api/v1)"),
    ]

    for method, path, desc in project_paths:
        test_endpoint("Project", method, f"{B}{path}", desc,
                      token=token, expected_codes=[200, 301, 302, 401, 403],
                      ref_section="Project")


# ============================================================
# STEP 3: SELENIUM SSO MODULE TESTING
# ============================================================
def test_modules_via_selenium():
    """Test module frontends via Selenium SSO."""
    print(f"\n{'='*80}")
    print("STEP 3: TESTING MODULES VIA SELENIUM SSO")
    print(f"{'='*80}")

    sso_results = []
    module_tests = [
        ("payroll", PAYROLL_FE, {
            "dashboard": f"{PAYROLL_FE}/dashboard",
            "salary_structures": f"{PAYROLL_FE}/salary-structures",
            "payroll_runs": f"{PAYROLL_FE}/payroll",
            "payslips": f"{PAYROLL_FE}/payslips",
            "self_service": f"{PAYROLL_FE}/self-service",
            "reports": f"{PAYROLL_FE}/reports",
            "loans": f"{PAYROLL_FE}/loans",
            "benefits": f"{PAYROLL_FE}/benefits",
        }),
        ("recruit", RECRUIT_FE, {
            "dashboard": f"{RECRUIT_FE}/dashboard",
            "jobs": f"{RECRUIT_FE}/jobs",
            "candidates": f"{RECRUIT_FE}/candidates",
            "applications": f"{RECRUIT_FE}/applications",
            "interviews": f"{RECRUIT_FE}/interviews",
            "offers": f"{RECRUIT_FE}/offers",
            "pipeline": f"{RECRUIT_FE}/pipeline",
            "onboarding": f"{RECRUIT_FE}/onboarding",
            "analytics": f"{RECRUIT_FE}/analytics",
        }),
        ("performance", PERFORMANCE_FE, {
            "dashboard": f"{PERFORMANCE_FE}/dashboard",
            "review_cycles": f"{PERFORMANCE_FE}/review-cycles",
            "goals": f"{PERFORMANCE_FE}/goals",
            "nine_box": f"{PERFORMANCE_FE}/nine-box",
            "pips": f"{PERFORMANCE_FE}/pips",
            "succession": f"{PERFORMANCE_FE}/succession-plans",
            "one_on_ones": f"{PERFORMANCE_FE}/one-on-ones",
            "competency": f"{PERFORMANCE_FE}/competency-frameworks",
            "analytics": f"{PERFORMANCE_FE}/analytics",
        }),
        ("rewards", REWARDS_FE, {
            "dashboard": f"{REWARDS_FE}/dashboard",
            "kudos": f"{REWARDS_FE}/kudos",
            "badges": f"{REWARDS_FE}/badges",
            "leaderboard": f"{REWARDS_FE}/leaderboard",
            "challenges": f"{REWARDS_FE}/challenges",
            "celebrations": f"{REWARDS_FE}/celebrations",
            "catalog": f"{REWARDS_FE}/rewards",
            "milestones": f"{REWARDS_FE}/milestones",
        }),
        ("exit", EXIT_FE, {
            "dashboard": f"{EXIT_FE}/dashboard",
            "exits": f"{EXIT_FE}/exits",
            "clearance": f"{EXIT_FE}/clearance",
            "interviews": f"{EXIT_FE}/interviews",
            "fnf": f"{EXIT_FE}/fnf",
            "predictions": f"{EXIT_FE}/predictions",
            "rehire": f"{EXIT_FE}/rehire",
            "alumni": f"{EXIT_FE}/alumni",
        }),
        ("lms", LMS_FE, {
            "dashboard": f"{LMS_FE}/dashboard",
            "courses": f"{LMS_FE}/courses",
            "learning_paths": f"{LMS_FE}/learning-paths",
            "certifications": f"{LMS_FE}/certificates",
            "compliance": f"{LMS_FE}/compliance",
            "gamification": f"{LMS_FE}/gamification",
            "discussions": f"{LMS_FE}/discussions",
            "analytics": f"{LMS_FE}/analytics",
        }),
    ]

    driver = None
    modules_tested = 0

    for mod_name, mod_fe, pages in module_tests:
        # Restart driver every 2 modules
        if modules_tested % 2 == 0:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            driver = get_selenium_driver()
            if not driver:
                print(f"  [SKIP] Cannot create Selenium driver for {mod_name}")
                continue
            # Re-login
            if not selenium_login(driver):
                print(f"  [SKIP] Cannot login for {mod_name}")
                continue

        print(f"\n--- SSO to {mod_name.upper()} ---")

        # SSO to module
        landing = selenium_sso_to_module(driver, mod_name, mod_fe)
        print(f"  SSO landed at: {landing}")

        # Navigate pages
        page_results = selenium_navigate_and_screenshot(driver, mod_name, pages)
        sso_results.extend(page_results)

        modules_tested += 1

    # Cleanup
    if driver:
        try:
            driver.quit()
        except:
            pass

    return sso_results


# ============================================================
# STEP 4: FILE BUGS
# ============================================================
def file_bugs():
    """File GitHub bugs for failures."""
    print(f"\n{'='*80}")
    print("STEP 4: FILING BUGS")
    print(f"{'='*80}")

    existing = get_existing_issues()
    filed_count = 0

    # Group bugs by module
    from collections import defaultdict
    module_bugs = defaultdict(list)
    for bug in bugs_to_file:
        module_bugs[bug["module"]].append(bug)

    for module, bugs in module_bugs.items():
        if len(bugs) == 0:
            continue

        # File one consolidated bug per module if many failures
        if len(bugs) > 10:
            title = f"[30-Day Sim SSO] {module}: {len(bugs)} endpoints returning errors"
            if any(title[:60] in t for t in existing):
                print(f"  [SKIP] Already exists: {title[:60]}...")
                continue

            body_lines = [
                f"## {module} API Endpoint Failures",
                f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"**Total failures**: {len(bugs)}",
                f"**Reference**: EMPCLOUD_API_REFERENCE.md",
                "",
                "### Failed Endpoints",
                "| Method | Path | Status | Section |",
                "|--------|------|--------|---------|",
            ]
            for b in bugs[:30]:
                body_lines.append(f"| {b['method']} | `{b['path']}` | {b['status']} | {b['ref_section']} |")
            if len(bugs) > 30:
                body_lines.append(f"| ... | ... | ... | ({len(bugs)-30} more) |")

            file_github_bug(title, "\n".join(body_lines))
            filed_count += 1
        else:
            for bug in bugs:
                title = f"[30-Day Sim SSO] {module}: {bug['method']} {bug['path']} -> {bug['status']}"
                if len(title) > 120:
                    title = title[:117] + "..."

                if any(title[:50] in t for t in existing):
                    print(f"  [SKIP] Already exists: {title[:50]}...")
                    continue

                body = (
                    f"## Endpoint Failure\n"
                    f"**Module**: {module}\n"
                    f"**Method**: {bug['method']}\n"
                    f"**Path**: `{bug['path']}`\n"
                    f"**Status**: {bug['status']}\n"
                    f"**Reference Section**: {bug['ref_section']}\n"
                    f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"Endpoint documented in EMPCLOUD_API_REFERENCE.md ({bug['ref_section']}) "
                    f"but returned {bug['status']} instead of expected success response."
                )
                file_github_bug(title, body)
                filed_count += 1
                time.sleep(1)  # Rate limiting

    print(f"\n  Total bugs filed: {filed_count}")


# ============================================================
# COVERAGE MATRIX
# ============================================================
def print_coverage_matrix(sso_results=None):
    """Print complete coverage matrix."""
    print(f"\n{'='*80}")
    print("COMPLETE COVERAGE MATRIX")
    print(f"{'='*80}")

    # Group by module
    from collections import defaultdict
    module_stats = defaultdict(lambda: {"total": 0, "passed": 0, "exists": 0, "failed": 0})

    for r in results:
        mod = r["module"]
        module_stats[mod]["total"] += 1
        if r["passed"]:
            module_stats[mod]["passed"] += 1
        if r.get("endpoint_exists", False):
            module_stats[mod]["exists"] += 1
        if not r.get("endpoint_exists", False):
            module_stats[mod]["failed"] += 1

    print(f"\n{'Module':<20} {'Total':<8} {'Pass':<8} {'Exists':<8} {'404/5xx':<8} {'Pass %':<8}")
    print("-" * 60)

    grand_total = grand_pass = grand_exists = grand_fail = 0
    for mod in sorted(module_stats.keys()):
        s = module_stats[mod]
        pct = f"{s['passed']/s['total']*100:.1f}%" if s['total'] > 0 else "N/A"
        print(f"{mod:<20} {s['total']:<8} {s['passed']:<8} {s['exists']:<8} {s['failed']:<8} {pct:<8}")
        grand_total += s['total']
        grand_pass += s['passed']
        grand_exists += s['exists']
        grand_fail += s['failed']

    print("-" * 60)
    gpct = f"{grand_pass/grand_total*100:.1f}%" if grand_total > 0 else "N/A"
    print(f"{'TOTAL':<20} {grand_total:<8} {grand_pass:<8} {grand_exists:<8} {grand_fail:<8} {gpct:<8}")

    # SSO results
    if sso_results:
        print(f"\n\n{'='*80}")
        print("SELENIUM SSO MODULE COVERAGE")
        print(f"{'='*80}")

        sso_stats = defaultdict(lambda: {"total": 0, "passed": 0})
        for r in sso_results:
            mod = r["module"]
            sso_stats[mod]["total"] += 1
            if r.get("passed"):
                sso_stats[mod]["passed"] += 1

        print(f"\n{'Module':<20} {'Pages':<8} {'Loaded':<8} {'Pass %':<8}")
        print("-" * 40)
        for mod in sorted(sso_stats.keys()):
            s = sso_stats[mod]
            pct = f"{s['passed']/s['total']*100:.1f}%" if s['total'] > 0 else "N/A"
            print(f"{mod:<20} {s['total']:<8} {s['passed']:<8} {pct:<8}")

    # Detailed failures
    failed = [r for r in results if not r.get("endpoint_exists", False)]
    if failed:
        print(f"\n\n{'='*80}")
        print(f"DETAILED FAILURES ({len(failed)} endpoints)")
        print(f"{'='*80}")
        for r in failed[:50]:
            print(f"  {r['module']:15s} {r['method']:6s} {r['url'].split('.com')[-1][:55]:55s} -> {r['status']} [{r['ref_section']}]")
        if len(failed) > 50:
            print(f"  ... and {len(failed)-50} more")

    # Section coverage
    print(f"\n\n{'='*80}")
    print("COVERAGE BY API REFERENCE SECTION")
    print(f"{'='*80}")

    section_stats = defaultdict(lambda: {"total": 0, "passed": 0})
    for r in results:
        sec = r.get("ref_section", "Unknown")
        section_stats[sec]["total"] += 1
        if r["passed"]:
            section_stats[sec]["passed"] += 1

    print(f"\n{'Section':<35} {'Total':<8} {'Pass':<8} {'Rate':<8}")
    print("-" * 55)
    for sec in sorted(section_stats.keys()):
        s = section_stats[sec]
        pct = f"{s['passed']/s['total']*100:.0f}%" if s['total'] > 0 else "N/A"
        print(f"{sec:<35} {s['total']:<8} {s['passed']:<8} {pct:<8}")


# ============================================================
# MAIN
# ============================================================
def main():
    start = time.time()
    print(f"EMP Cloud Full Module Test -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing ALL endpoints from EMPCLOUD_API_REFERENCE.md")
    print(f"{'='*80}")
    sys.stdout.flush()

    # Step 2: Core HRMS
    try:
        test_core_hrms()
    except Exception as e:
        print(f"\n[CORE ERROR] {e}")
        traceback.print_exc()
    sys.stdout.flush()

    # Step 2b: Module APIs
    for test_fn, name in [
        (test_payroll_api, "Payroll"),
        (test_recruit_api, "Recruit"),
        (test_performance_api, "Performance"),
        (test_rewards_api, "Rewards"),
        (test_exit_api, "Exit"),
        (test_lms_api, "LMS"),
        (test_project_api, "Project"),
    ]:
        try:
            test_fn()
        except Exception as e:
            print(f"\n[{name.upper()} ERROR] {e}")
            traceback.print_exc()
        sys.stdout.flush()

    # Step 3: Selenium SSO
    sso_results = []
    try:
        sso_results = test_modules_via_selenium()
    except Exception as e:
        print(f"\n[SELENIUM ERROR] {e}")
        traceback.print_exc()
    sys.stdout.flush()

    # Step 4: File bugs
    try:
        file_bugs()
    except Exception as e:
        print(f"\n[BUG FILING ERROR] {e}")
        traceback.print_exc()
    sys.stdout.flush()

    # Coverage matrix
    try:
        print_coverage_matrix(sso_results)
    except Exception as e:
        print(f"\n[MATRIX ERROR] {e}")
        traceback.print_exc()
    sys.stdout.flush()

    elapsed = time.time() - start
    print(f"\n\nTotal time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"Total API endpoints tested: {len(results)}")
    print(f"Total bugs to file: {len(bugs_to_file)}")

    # Save results to JSON
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_endpoints": len(results),
        "total_bugs": len(bugs_to_file),
        "results": results,
        "bugs": bugs_to_file,
    }
    with open(r"C:\emptesting\simulation\test_all_modules_readme_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to C:\\emptesting\\simulation\\test_all_modules_readme_results.json")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
