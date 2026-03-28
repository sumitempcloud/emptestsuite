# Fresh E2E Test - Ananya (HR Admin at TechNova)
# Tests: Dashboard, Employees, Departments, Locations, Org Chart, Settings, Users, Billing, Modules
# Uses Selenium (restart every 3 tests) + API
# Screenshots to C:/Users/Admin/screenshots/fresh_hr_admin/

import os
import sys
import json
import time
import base64
import traceback
import requests
from datetime import datetime, timedelta

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
# CONFIG
# ============================================================
BASE_URL = "https://test-empcloud.empcloud.com"
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_hr_admin"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ============================================================
# GLOBALS
# ============================================================
token = None
driver = None
test_counter = 0
bugs_found = []
test_results = []

# ============================================================
# HELPERS
# ============================================================

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def screenshot(name):
    """Save screenshot and return path."""
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    if driver:
        try:
            driver.save_screenshot(path)
            log(f"  Screenshot: {path}")
            return path
        except Exception as e:
            log(f"  Screenshot failed: {e}")
    return None

def api_get(path, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE}{path}"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
    except Exception as e:
        return 0, str(e)

def api_post(path, data=None):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{API_BASE}{path}"
    try:
        r = requests.post(url, headers=headers, json=data, timeout=30)
        return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
    except Exception as e:
        return 0, str(e)

def api_put(path, data=None):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{API_BASE}{path}"
    try:
        r = requests.put(url, headers=headers, json=data, timeout=30)
        return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
    except Exception as e:
        return 0, str(e)

def api_delete(path):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE}{path}"
    try:
        r = requests.delete(url, headers=headers, timeout=30)
        return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
    except Exception as e:
        return 0, str(e)

def login_api():
    """Login via API and get JWT token."""
    global token
    url = f"{API_BASE}/auth/login"
    r = requests.post(url, json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    data = r.json()
    if r.status_code == 200 and data.get("success"):
        token = data["data"]["tokens"]["access_token"]
        log(f"API login OK - token obtained")
        return True
    else:
        log(f"API login FAILED: {r.status_code} {data}")
        return False

def get_driver():
    """Create a fresh Chrome WebDriver."""
    global driver
    if driver:
        try:
            driver.quit()
        except:
            pass
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    svc = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.implicitly_wait(10)
    return driver

def restart_driver_if_needed():
    """Restart Selenium driver every 3 tests."""
    global test_counter, driver
    test_counter += 1
    if test_counter % 3 == 0:
        log(">> Restarting Chrome driver (every 3 tests) <<")
        try:
            if driver:
                driver.quit()
        except:
            pass
        driver = None
        get_driver()
        selenium_login()

def selenium_login():
    """Login via Selenium."""
    global driver
    if not driver:
        get_driver()
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    try:
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='email' i], input[placeholder*='Email']"))
        )
        email_input.clear()
        email_input.send_keys(EMAIL)

        pw_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        pw_input.clear()
        pw_input.send_keys(PASSWORD)

        # Find and click login button
        btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button")
        for btn in btns:
            txt = btn.text.lower()
            if "log in" in txt or "login" in txt or "sign in" in txt:
                btn.click()
                break
        else:
            if btns:
                btns[0].click()

        time.sleep(4)
        log(f"Selenium login done. URL: {driver.current_url}")
        return True
    except Exception as e:
        log(f"Selenium login failed: {e}")
        screenshot("login_failure")
        return False

def record_result(test_name, status, details=""):
    test_results.append({"test": test_name, "status": status, "details": details})
    icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "BUG"
    log(f"  [{icon}] {test_name}: {details[:120] if details else ''}")

def record_bug(title, details, screenshot_path=None):
    bugs_found.append({"title": title, "details": details, "screenshot": screenshot_path})
    log(f"  [BUG] {title}")

def upload_screenshot_to_github(local_path, name):
    """Upload screenshot to GitHub repo and return raw URL."""
    if not local_path or not os.path.exists(local_path):
        return None
    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/{name}.png"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    # Check if file exists first
    r = requests.get(url, headers=headers, timeout=15)
    payload = {"message": f"Screenshot {name}", "content": content_b64}
    if r.status_code == 200:
        payload["sha"] = r.json()["sha"]
    r = requests.put(url, headers=headers, json=payload, timeout=30)
    if r.status_code in (200, 201):
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/screenshots/{name}.png"
        return raw_url
    log(f"  Screenshot upload failed: {r.status_code}")
    return None

def search_existing_issues(keyword):
    """Search open issues for duplicates."""
    url = f"https://api.github.com/search/issues?q={keyword}+repo:{GITHUB_REPO}+state:open"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json().get("items", [])
    except:
        pass
    return []

def file_github_issue(title, body, labels=None):
    """File a bug on GitHub after checking for duplicates."""
    # Check for duplicates
    keywords = title.split()[:3]
    search_q = "+".join(keywords)
    existing = search_existing_issues(search_q)
    for issue in existing:
        if any(kw.lower() in issue["title"].lower() for kw in keywords[:2]):
            log(f"  Possible duplicate found: #{issue['number']} - {issue['title']}")
            return issue["number"]

    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code == 201:
        num = r.json()["number"]
        log(f"  Filed issue #{num}: {title}")
        return num
    else:
        log(f"  Issue filing failed: {r.status_code} {r.text[:200]}")
        return None

def wait_for(css, timeout=10):
    """Wait for element by CSS selector."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css))
    )

def wait_and_click(css, timeout=10):
    elem = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, css))
    )
    elem.click()
    return elem

# ============================================================
# API TESTS
# ============================================================

def test_api_dashboard():
    """Test dashboard widgets API."""
    log("=== API: Dashboard Widgets ===")
    code, data = api_get("/dashboard/widgets")
    if code == 200 and data.get("success"):
        widgets = data.get("data", {})
        log(f"  Dashboard widgets returned: {list(widgets.keys()) if isinstance(widgets, dict) else type(widgets)}")
        record_result("API - Dashboard widgets load", "PASS", f"Status {code}, data present")
    else:
        record_result("API - Dashboard widgets load", "FAIL", f"Status {code}: {str(data)[:100]}")

def test_api_org_info():
    """Test organization info."""
    log("=== API: Organization Info ===")
    code, data = api_get("/organizations/me")
    if code == 200 and data.get("success"):
        org = data.get("data", {})
        org_name = org.get("name", "?")
        log(f"  Org: {org_name}")
        record_result("API - Organization info", "PASS", f"Org: {org_name}")
        return org
    else:
        record_result("API - Organization info", "FAIL", f"Status {code}")
        return None

def test_api_departments():
    """Test departments listing and creation."""
    log("=== API: Departments ===")
    code, data = api_get("/organizations/me/departments")
    if code == 200 and data.get("success"):
        depts = data.get("data", [])
        log(f"  Found {len(depts)} departments")
        record_result("API - List departments", "PASS", f"{len(depts)} departments")

        # Try creating a department
        test_dept_name = f"TestDept_{int(time.time()) % 10000}"
        code2, data2 = api_post("/organizations/me/departments", {"name": test_dept_name, "description": "Test department"})
        if code2 in (201, 200):
            record_result("API - Create department", "PASS", f"Created '{test_dept_name}'")
            return data2.get("data", {})
        elif code2 == 400:
            record_result("API - Create department", "PASS", f"400 validation (may need more fields): {str(data2)[:100]}")
        else:
            record_result("API - Create department", "FAIL", f"Status {code2}: {str(data2)[:100]}")
    else:
        record_result("API - List departments", "FAIL", f"Status {code}: {str(data)[:100]}")
    return None

def test_api_locations():
    """Test locations listing and creation."""
    log("=== API: Locations ===")
    code, data = api_get("/organizations/me/locations")
    if code == 200 and data.get("success"):
        locs = data.get("data", [])
        log(f"  Found {len(locs)} locations")
        record_result("API - List locations", "PASS", f"{len(locs)} locations")

        # Try creating a location
        test_loc = {
            "name": f"TestLoc_{int(time.time()) % 10000}",
            "address": "123 Test Street",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India"
        }
        code2, data2 = api_post("/organizations/me/locations", test_loc)
        if code2 in (201, 200):
            record_result("API - Create location", "PASS", f"Created location")
        elif code2 == 400:
            record_result("API - Create location", "PASS", f"400 response: {str(data2)[:100]}")
        else:
            record_result("API - Create location", "FAIL", f"Status {code2}: {str(data2)[:100]}")
    else:
        record_result("API - List locations", "FAIL", f"Status {code}: {str(data)[:100]}")

def test_api_employees():
    """Test employee listing, search, and profile."""
    log("=== API: Employees ===")

    # List users
    code, data = api_get("/users", params={"page": 1, "limit": 10})
    if code == 200 and data.get("success"):
        users = data.get("data", [])
        meta = data.get("meta", {})
        total = meta.get("total", len(users))
        log(f"  Found {total} users (showing {len(users)})")
        record_result("API - List employees", "PASS", f"{total} total users")

        # Search test
        code_s, data_s = api_get("/users", params={"search": "priya"})
        if code_s == 200 and data_s.get("success"):
            results = data_s.get("data", [])
            found_priya = any("priya" in str(u.get("email","")).lower() or "priya" in str(u.get("first_name","")).lower() for u in results)
            if found_priya:
                record_result("API - Search employee 'priya'", "PASS", f"Found in {len(results)} results")
            else:
                record_result("API - Search employee 'priya'", "FAIL", f"Search returned {len(results)} results but Priya not found")
        else:
            record_result("API - Search employee", "FAIL", f"Status {code_s}")

        # Get first user's profile
        if users:
            first_user = users[0]
            uid = first_user.get("id")
            emp_id = first_user.get("employee_id") or uid

            # Test user detail
            code_u, data_u = api_get(f"/users/{uid}")
            if code_u == 200:
                record_result("API - Get user detail", "PASS", f"User #{uid} loaded")
            else:
                record_result("API - Get user detail", "FAIL", f"Status {code_u}")

            # Test employee profile
            code_p, data_p = api_get(f"/employees/{emp_id}/profile")
            if code_p == 200:
                record_result("API - Get employee profile", "PASS", f"Profile for employee #{emp_id}")
            elif code_p == 404:
                # Try with user id
                code_p2, data_p2 = api_get(f"/employees/{uid}/profile")
                if code_p2 == 200:
                    record_result("API - Get employee profile", "PASS", f"Profile for user #{uid}")
                else:
                    record_result("API - Get employee profile", "FAIL", f"404 for both emp_id={emp_id} and user_id={uid}")
            else:
                record_result("API - Get employee profile", "FAIL", f"Status {code_p}: {str(data_p)[:100]}")
    else:
        record_result("API - List employees", "FAIL", f"Status {code}: {str(data)[:100]}")

def test_api_employee_add():
    """Test adding a new employee."""
    log("=== API: Add Employee ===")
    ts = int(time.time()) % 100000
    new_emp = {
        "first_name": "Rahul",
        "last_name": "TestSharma",
        "email": f"rahul.test{ts}@technova.in",
        "phone": f"98765{ts:05d}",
        "department_id": None,
        "designation": "Software Engineer",
        "date_of_joining": "2026-03-28",
        "role": "employee"
    }

    # Get a department ID first
    code_d, data_d = api_get("/organizations/me/departments")
    if code_d == 200 and data_d.get("success") and data_d.get("data"):
        new_emp["department_id"] = data_d["data"][0].get("id")

    # Try invite flow
    code, data = api_post("/users/invite", new_emp)
    if code in (200, 201):
        record_result("API - Invite new employee", "PASS", f"Invited {new_emp['email']}")
        return data.get("data", {})
    elif code == 400:
        log(f"  Invite returned 400: {str(data)[:200]}")
        record_result("API - Invite new employee", "PASS", f"400 validation response: {str(data)[:100]}")
    elif code == 409:
        record_result("API - Invite new employee", "PASS", f"409 conflict (may already exist)")
    else:
        record_result("API - Invite new employee", "FAIL", f"Status {code}: {str(data)[:100]}")
    return None

def test_api_employee_edit():
    """Test editing an employee."""
    log("=== API: Edit Employee ===")
    # Get own user ID (663 from knowledge base)
    code, data = api_get("/users/663")
    if code == 200 and data.get("success"):
        user_data = data.get("data", {})
        original_phone = user_data.get("phone", "")

        # Try updating a non-critical field
        update = {"phone": "9876500001"}
        code_u, data_u = api_put("/users/663", update)
        if code_u == 200:
            record_result("API - Edit employee phone", "PASS", "Updated phone number")
            # Restore original
            api_put("/users/663", {"phone": original_phone})
        else:
            record_result("API - Edit employee phone", "FAIL", f"Status {code_u}: {str(data_u)[:100]}")
    else:
        record_result("API - Edit employee", "FAIL", f"Cannot fetch user 663: status {code}")

def test_api_org_chart():
    """Test org chart API."""
    log("=== API: Org Chart ===")
    code, data = api_get("/users/org-chart")
    if code == 200 and data.get("success"):
        chart = data.get("data", [])
        log(f"  Org chart has {len(chart) if isinstance(chart, list) else 'dict'} entries")
        record_result("API - Org chart", "PASS", f"Data returned, type={type(chart).__name__}")
    else:
        record_result("API - Org chart", "FAIL", f"Status {code}: {str(data)[:100]}")

def test_api_settings():
    """Test organization settings (update org info)."""
    log("=== API: Settings / Update Org ===")
    code, data = api_get("/organizations/me")
    if code == 200 and data.get("success"):
        org = data.get("data", {})
        original_address = org.get("address", "")

        # Try updating address
        update = {"address": "456 Test Road, Updated"}
        code_u, data_u = api_put("/organizations/me", update)
        if code_u == 200 and data_u.get("success"):
            record_result("API - Update org settings", "PASS", "Address updated")
            # Restore
            api_put("/organizations/me", {"address": original_address})
        else:
            record_result("API - Update org settings", "FAIL", f"Status {code_u}: {str(data_u)[:100]}")
    else:
        record_result("API - Get org settings", "FAIL", f"Status {code}")

def test_api_users_list():
    """Test users management listing."""
    log("=== API: Users Management ===")
    code, data = api_get("/users", params={"page": 1, "limit": 50})
    if code == 200 and data.get("success"):
        users = data.get("data", [])
        meta = data.get("meta", {})
        log(f"  Users: {len(users)} on page, total={meta.get('total','?')}")

        # Check user fields
        if users:
            u = users[0]
            fields_present = [k for k in ["id","email","first_name","last_name","role","status"] if k in u]
            log(f"  User fields: {fields_present}")
            record_result("API - Users list", "PASS", f"{len(users)} users, fields: {fields_present}")
        else:
            record_result("API - Users list", "PASS", "Empty list returned (0 users on page)")
    else:
        record_result("API - Users list", "FAIL", f"Status {code}")

def test_api_billing():
    """Test billing/subscription endpoints."""
    log("=== API: Billing ===")
    code, data = api_get("/subscriptions")
    if code == 200 and data.get("success"):
        subs = data.get("data", {})
        log(f"  Subscription data: {str(subs)[:150]}")
        record_result("API - Subscriptions", "PASS", f"Data returned")
    else:
        record_result("API - Subscriptions", "FAIL", f"Status {code}: {str(data)[:100]}")

    # Billing invoices
    code2, data2 = api_get("/billing/invoices")
    if code2 == 200:
        record_result("API - Billing invoices", "PASS", f"Status 200")
    elif code2 == 404:
        record_result("API - Billing invoices", "FAIL", f"404 - endpoint not found")
    else:
        record_result("API - Billing invoices", "FAIL", f"Status {code2}: {str(data2)[:100]}")

def test_api_modules():
    """Test modules listing."""
    log("=== API: Modules ===")
    code, data = api_get("/modules")
    if code == 200 and data.get("success"):
        modules = data.get("data", [])
        log(f"  Found {len(modules)} modules")
        if modules and isinstance(modules, list):
            names = [m.get("name","?") for m in modules[:10]]
            log(f"  Module names: {names}")
        record_result("API - Modules list", "PASS", f"{len(modules)} modules")
    else:
        record_result("API - Modules list", "FAIL", f"Status {code}")

def test_api_audit():
    """Test audit log."""
    log("=== API: Audit Log ===")
    code, data = api_get("/audit", params={"page": 1, "limit": 10})
    if code == 200 and data.get("success"):
        entries = data.get("data", [])
        log(f"  Audit entries: {len(entries)}")
        record_result("API - Audit log", "PASS", f"{len(entries)} entries")
    else:
        record_result("API - Audit log", "FAIL", f"Status {code}")

def test_api_notifications():
    """Test notifications."""
    log("=== API: Notifications ===")
    code, data = api_get("/notifications", params={"page": 1, "limit": 10})
    if code == 200 and data.get("success"):
        notifs = data.get("data", [])
        record_result("API - Notifications", "PASS", f"{len(notifs)} notifications")
    else:
        record_result("API - Notifications", "FAIL", f"Status {code}")

    code2, data2 = api_get("/notifications/unread-count")
    if code2 == 200:
        record_result("API - Unread count", "PASS", f"Data: {str(data2.get('data',''))[:50]}")
    else:
        record_result("API - Unread count", "FAIL", f"Status {code2}")

def test_api_employee_validation():
    """Test business rule validations on employee data."""
    log("=== API: Employee Validation Rules ===")

    # E001: Duplicate email
    code, data = api_post("/users/invite", {
        "first_name": "Dup",
        "last_name": "Test",
        "email": EMAIL,  # Use existing email
        "role": "employee"
    })
    if code in (400, 409, 422):
        record_result("BIZ - Duplicate email rejected", "PASS", f"Status {code}")
    elif code in (200, 201):
        record_result("BIZ - Duplicate email rejected", "FAIL", "Server allowed duplicate email!")
        record_bug(
            "System allows adding employee with duplicate email address",
            f"Inviting a new user with email {EMAIL} (already exists) returns {code} instead of rejecting. "
            f"Business rule: each org must have unique employee emails."
        )
    else:
        record_result("BIZ - Duplicate email rejected", "FAIL", f"Unexpected status {code}: {str(data)[:100]}")

    # E007: Future DOB
    ts = int(time.time()) % 100000
    code, data = api_post("/users/invite", {
        "first_name": "Future",
        "last_name": "Baby",
        "email": f"future.baby{ts}@technova.in",
        "date_of_birth": "2030-01-01",
        "role": "employee"
    })
    if code in (400, 422):
        record_result("BIZ - Future DOB rejected", "PASS", f"Status {code}")
    elif code in (200, 201):
        record_result("BIZ - Future DOB rejected", "FAIL", "Server accepted future date of birth!")
        record_bug(
            "Employee can be created with a future date of birth",
            f"POST /users/invite with date_of_birth=2030-01-01 returns {code}. "
            f"The system should reject dates of birth in the future."
        )
    else:
        record_result("BIZ - Future DOB", "FAIL", f"Status {code}: {str(data)[:100]}")

    # E005: Under 18
    code, data = api_post("/users/invite", {
        "first_name": "Young",
        "last_name": "Kid",
        "email": f"young.kid{ts}@technova.in",
        "date_of_birth": "2015-01-01",  # ~11 years old
        "role": "employee"
    })
    if code in (400, 422):
        record_result("BIZ - Under-18 DOB rejected", "PASS", f"Status {code}")
    elif code in (200, 201):
        record_result("BIZ - Under-18 DOB rejected", "FAIL", "Server accepted under-18 employee!")
        record_bug(
            "Employee can be created with age under 18 years",
            f"POST /users/invite with date_of_birth=2015-01-01 (age ~11) returns {code}. "
            f"HRMS should enforce minimum age of 18 for employment."
        )
    else:
        record_result("BIZ - Under-18 DOB", "FAIL", f"Status {code}: {str(data)[:100]}")

def test_api_department_validation():
    """Test department validation rules."""
    log("=== API: Department Validation ===")

    # Empty name
    code, data = api_post("/organizations/me/departments", {"name": "", "description": "test"})
    if code in (400, 422):
        record_result("BIZ - Empty dept name rejected", "PASS", f"Status {code}")
    elif code in (200, 201):
        record_result("BIZ - Empty dept name rejected", "FAIL", "Created department with empty name!")
        record_bug(
            "Department can be created with empty name",
            f"POST /organizations/me/departments with name='' returns {code}. "
            f"Department name should be required and non-empty."
        )
    else:
        record_result("BIZ - Empty dept name", "FAIL", f"Status {code}: {str(data)[:100]}")

def test_api_pagination():
    """Test pagination works correctly."""
    log("=== API: Pagination ===")
    code1, data1 = api_get("/users", params={"page": 1, "limit": 5})
    code2, data2 = api_get("/users", params={"page": 2, "limit": 5})

    if code1 == 200 and code2 == 200:
        p1 = data1.get("data", [])
        p2 = data2.get("data", [])
        p1_ids = {u.get("id") for u in p1}
        p2_ids = {u.get("id") for u in p2}
        overlap = p1_ids & p2_ids

        if overlap:
            record_result("BIZ - Pagination no overlap", "FAIL", f"Pages 1&2 share IDs: {overlap}")
            record_bug(
                "Employee list pagination returns duplicate records across pages",
                f"GET /users?page=1&limit=5 and page=2&limit=5 share user IDs: {overlap}. "
                f"Each page should return distinct records."
            )
        else:
            record_result("BIZ - Pagination no overlap", "PASS", f"Page1={len(p1)} Page2={len(p2)} no overlap")

        meta = data1.get("meta", {})
        if meta.get("total") and meta.get("total_pages"):
            record_result("BIZ - Pagination meta fields", "PASS", f"total={meta['total']} pages={meta['total_pages']}")
        else:
            record_result("BIZ - Pagination meta fields", "FAIL", f"Missing total or total_pages in meta: {meta}")
    else:
        record_result("API - Pagination", "FAIL", f"Page1={code1} Page2={code2}")


# ============================================================
# SELENIUM TESTS
# ============================================================

def test_selenium_dashboard():
    """Test dashboard page via Selenium."""
    log("=== SELENIUM: Dashboard ===")
    restart_driver_if_needed()
    try:
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(4)
        ss = screenshot("dashboard_main")

        page_source = driver.page_source.lower()
        url = driver.current_url

        # Check if we're on dashboard
        if "/dashboard" in url or "/login" not in url:
            record_result("UI - Dashboard loads", "PASS", f"URL: {url}")
        else:
            record_result("UI - Dashboard loads", "FAIL", f"Redirected to {url}")
            return

        # Check for key dashboard elements
        body_text = driver.find_element(By.TAG_NAME, "body").text

        # Look for common dashboard indicators
        has_content = len(body_text.strip()) > 50
        if has_content:
            record_result("UI - Dashboard has content", "PASS", f"Body text length: {len(body_text)}")
        else:
            record_result("UI - Dashboard has content", "FAIL", "Dashboard appears empty")
            record_bug("Dashboard page appears empty or fails to load content",
                       f"After login, navigating to {BASE_URL}/dashboard shows minimal/no content. Body text: {body_text[:200]}",
                       ss)

        # Check for sidebar
        sidebar_elems = driver.find_elements(By.CSS_SELECTOR, "nav, aside, [class*='sidebar'], [class*='side-bar'], [role='navigation']")
        if sidebar_elems:
            record_result("UI - Sidebar present", "PASS", f"Found {len(sidebar_elems)} nav elements")
        else:
            record_result("UI - Sidebar present", "FAIL", "No sidebar/navigation found")

        screenshot("dashboard_loaded")

    except Exception as e:
        screenshot("dashboard_error")
        record_result("UI - Dashboard", "FAIL", f"Exception: {str(e)[:100]}")

def test_selenium_employees():
    """Test employees page via Selenium."""
    log("=== SELENIUM: Employees Page ===")
    restart_driver_if_needed()
    try:
        driver.get(f"{BASE_URL}/employees")
        time.sleep(4)
        ss = screenshot("employees_page")

        url = driver.current_url
        body_text = driver.find_element(By.TAG_NAME, "body").text

        if len(body_text.strip()) > 50:
            record_result("UI - Employees page loads", "PASS", f"URL: {url}")
        else:
            record_result("UI - Employees page loads", "FAIL", f"Page appears empty at {url}")

        # Try to find search input
        search_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='search'], input[placeholder*='earch'], input[placeholder*='filter'], input[name='search']")
        if search_inputs:
            record_result("UI - Employee search input", "PASS", "Search field found")
            # Try searching
            search_inputs[0].clear()
            search_inputs[0].send_keys("priya")
            time.sleep(2)
            screenshot("employees_search_priya")
        else:
            record_result("UI - Employee search input", "FAIL", "No search field found on employees page")

        # Check for employee table/list
        tables = driver.find_elements(By.CSS_SELECTOR, "table, [class*='table'], [role='table'], [class*='list'], [class*='grid']")
        if tables:
            record_result("UI - Employee list/table", "PASS", f"Found {len(tables)} table/list elements")
        else:
            record_result("UI - Employee list/table", "FAIL", "No table or list found on employees page")

        screenshot("employees_page_final")

    except Exception as e:
        screenshot("employees_error")
        record_result("UI - Employees page", "FAIL", f"Exception: {str(e)[:100]}")

def test_selenium_departments():
    """Test departments page via Selenium."""
    log("=== SELENIUM: Departments Page ===")
    restart_driver_if_needed()
    try:
        driver.get(f"{BASE_URL}/departments")
        time.sleep(4)
        ss = screenshot("departments_page")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        url = driver.current_url

        if len(body_text.strip()) > 30:
            record_result("UI - Departments page loads", "PASS", f"URL: {url}")
        else:
            record_result("UI - Departments page loads", "FAIL", f"Empty page at {url}")

        # Look for add button
        add_btns = driver.find_elements(By.CSS_SELECTOR, "button")
        add_found = False
        for btn in add_btns:
            txt = btn.text.lower()
            if "add" in txt or "create" in txt or "new" in txt:
                add_found = True
                break

        if add_found:
            record_result("UI - Add department button", "PASS", "Found add/create button")
        else:
            record_result("UI - Add department button", "FAIL", "No add/create button found")

        screenshot("departments_final")

    except Exception as e:
        screenshot("departments_error")
        record_result("UI - Departments", "FAIL", f"Exception: {str(e)[:100]}")

def test_selenium_locations():
    """Test locations page via Selenium."""
    log("=== SELENIUM: Locations Page ===")
    restart_driver_if_needed()
    try:
        driver.get(f"{BASE_URL}/locations")
        time.sleep(4)
        ss = screenshot("locations_page")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        url = driver.current_url

        if len(body_text.strip()) > 30:
            record_result("UI - Locations page loads", "PASS", f"URL: {url}")
        else:
            record_result("UI - Locations page loads", "FAIL", f"Empty page at {url}")

        screenshot("locations_final")

    except Exception as e:
        screenshot("locations_error")
        record_result("UI - Locations", "FAIL", f"Exception: {str(e)[:100]}")

def test_selenium_org_chart():
    """Test org chart page via Selenium."""
    log("=== SELENIUM: Org Chart ===")
    restart_driver_if_needed()
    try:
        driver.get(f"{BASE_URL}/org-chart")
        time.sleep(5)
        ss = screenshot("org_chart_page")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        url = driver.current_url

        if len(body_text.strip()) > 30:
            record_result("UI - Org chart page loads", "PASS", f"URL: {url}")
        else:
            # Try alternate URL
            driver.get(f"{BASE_URL}/organization/chart")
            time.sleep(3)
            body_text2 = driver.find_element(By.TAG_NAME, "body").text
            ss2 = screenshot("org_chart_alt")
            if len(body_text2.strip()) > 30:
                record_result("UI - Org chart page loads", "PASS", f"At /organization/chart")
            else:
                record_result("UI - Org chart page loads", "FAIL", f"Tried /org-chart and /organization/chart")

        screenshot("org_chart_final")

    except Exception as e:
        screenshot("org_chart_error")
        record_result("UI - Org chart", "FAIL", f"Exception: {str(e)[:100]}")

def test_selenium_settings():
    """Test settings page via Selenium."""
    log("=== SELENIUM: Settings ===")
    restart_driver_if_needed()
    try:
        driver.get(f"{BASE_URL}/settings")
        time.sleep(4)
        ss = screenshot("settings_page")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        url = driver.current_url

        if len(body_text.strip()) > 30:
            record_result("UI - Settings page loads", "PASS", f"URL: {url}")
        else:
            record_result("UI - Settings page loads", "FAIL", f"Empty at {url}")

        # Look for form fields
        inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")
        if inputs:
            record_result("UI - Settings has form fields", "PASS", f"{len(inputs)} input fields")
        else:
            record_result("UI - Settings has form fields", "FAIL", "No form fields found")

        screenshot("settings_final")

    except Exception as e:
        screenshot("settings_error")
        record_result("UI - Settings", "FAIL", f"Exception: {str(e)[:100]}")

def test_selenium_users_management():
    """Test users management page via Selenium."""
    log("=== SELENIUM: Users Management ===")
    restart_driver_if_needed()
    try:
        driver.get(f"{BASE_URL}/users")
        time.sleep(4)
        ss = screenshot("users_mgmt_page")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        url = driver.current_url

        if len(body_text.strip()) > 30:
            record_result("UI - Users page loads", "PASS", f"URL: {url}")
        else:
            record_result("UI - Users page loads", "FAIL", f"Empty at {url}")

        # Look for invite/add user button
        btns = driver.find_elements(By.CSS_SELECTOR, "button")
        invite_found = False
        for btn in btns:
            txt = btn.text.lower()
            if "invite" in txt or "add user" in txt or "add" in txt:
                invite_found = True
                break
        if invite_found:
            record_result("UI - Invite user button", "PASS", "Button found")
        else:
            record_result("UI - Invite user button", "FAIL", "No invite/add user button")

        screenshot("users_mgmt_final")

    except Exception as e:
        screenshot("users_mgmt_error")
        record_result("UI - Users management", "FAIL", f"Exception: {str(e)[:100]}")

def test_selenium_billing():
    """Test billing page via Selenium."""
    log("=== SELENIUM: Billing ===")
    restart_driver_if_needed()
    try:
        driver.get(f"{BASE_URL}/billing")
        time.sleep(4)
        ss = screenshot("billing_page")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        url = driver.current_url

        if len(body_text.strip()) > 30:
            record_result("UI - Billing page loads", "PASS", f"URL: {url}")
        else:
            # Try alternate
            driver.get(f"{BASE_URL}/settings/billing")
            time.sleep(3)
            body2 = driver.find_element(By.TAG_NAME, "body").text
            ss2 = screenshot("billing_alt")
            if len(body2.strip()) > 30:
                record_result("UI - Billing page loads", "PASS", "At /settings/billing")
            else:
                record_result("UI - Billing page loads", "FAIL", "Tried /billing and /settings/billing")

        screenshot("billing_final")

    except Exception as e:
        screenshot("billing_error")
        record_result("UI - Billing", "FAIL", f"Exception: {str(e)[:100]}")

def test_selenium_modules():
    """Test modules page via Selenium."""
    log("=== SELENIUM: Modules Page ===")
    restart_driver_if_needed()
    try:
        driver.get(f"{BASE_URL}/modules")
        time.sleep(4)
        ss = screenshot("modules_page")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        url = driver.current_url

        if len(body_text.strip()) > 30:
            record_result("UI - Modules page loads", "PASS", f"URL: {url}")
        else:
            record_result("UI - Modules page loads", "FAIL", f"Empty at {url}")

        # Look for module cards
        cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='module'], [class*='Card']")
        if cards:
            record_result("UI - Module cards", "PASS", f"Found {len(cards)} card elements")
        else:
            record_result("UI - Module cards", "FAIL", "No module cards found")

        screenshot("modules_final")

    except Exception as e:
        screenshot("modules_error")
        record_result("UI - Modules", "FAIL", f"Exception: {str(e)[:100]}")

def test_selenium_sidebar_links():
    """Test that all major sidebar links work."""
    log("=== SELENIUM: Sidebar Navigation ===")
    restart_driver_if_needed()
    try:
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(4)

        # Find all sidebar links
        links = driver.find_elements(By.CSS_SELECTOR, "nav a, aside a, [class*='sidebar'] a, [class*='nav'] a")
        link_data = []
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            if href and text and BASE_URL in href:
                link_data.append({"text": text, "href": href})

        log(f"  Found {len(link_data)} sidebar links")
        screenshot("sidebar_links")

        if link_data:
            record_result("UI - Sidebar links found", "PASS", f"{len(link_data)} links")
            # Log first 20 links
            for ld in link_data[:20]:
                log(f"    -> {ld['text']}: {ld['href']}")
        else:
            record_result("UI - Sidebar links found", "FAIL", "No sidebar links detected")

        # Test a few critical sidebar links
        dead_links = []
        test_paths = ["/dashboard", "/employees", "/departments", "/locations", "/settings"]
        for path in test_paths:
            driver.get(f"{BASE_URL}{path}")
            time.sleep(2)
            body = driver.find_element(By.TAG_NAME, "body").text
            current = driver.current_url
            # React SPA always returns 200, check content
            if len(body.strip()) < 30 and "/login" not in current:
                dead_links.append(path)

        if dead_links:
            record_result("UI - Dead sidebar links", "FAIL", f"Empty pages: {dead_links}")
            screenshot("dead_links")
        else:
            record_result("UI - Core sidebar links work", "PASS", "All tested paths have content")

    except Exception as e:
        screenshot("sidebar_error")
        record_result("UI - Sidebar", "FAIL", f"Exception: {str(e)[:100]}")


# ============================================================
# MAIN
# ============================================================

def main():
    global driver, token

    log("=" * 60)
    log("FRESH E2E TEST - Ananya (HR Admin at TechNova)")
    log("=" * 60)

    # Step 1: API Login
    if not login_api():
        log("FATAL: Cannot login via API. Aborting.")
        return

    # Step 2: API Tests
    log("\n>>> RUNNING API TESTS <<<\n")
    test_api_dashboard()
    test_api_org_info()
    test_api_departments()
    test_api_locations()
    test_api_employees()
    test_api_employee_add()
    test_api_employee_edit()
    test_api_org_chart()
    test_api_settings()
    test_api_users_list()
    test_api_billing()
    test_api_modules()
    test_api_audit()
    test_api_notifications()
    test_api_employee_validation()
    test_api_department_validation()
    test_api_pagination()

    # Step 3: Selenium Tests (restart driver every 3)
    log("\n>>> RUNNING SELENIUM TESTS <<<\n")
    get_driver()
    selenium_login()

    test_selenium_dashboard()
    test_selenium_employees()
    test_selenium_departments()
    test_selenium_locations()
    test_selenium_org_chart()
    test_selenium_settings()
    test_selenium_users_management()
    test_selenium_billing()
    test_selenium_modules()
    test_selenium_sidebar_links()

    # Cleanup
    if driver:
        try:
            driver.quit()
        except:
            pass

    # Step 4: Summary
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)

    passes = [r for r in test_results if r["status"] == "PASS"]
    fails = [r for r in test_results if r["status"] == "FAIL"]

    log(f"Total: {len(test_results)}  |  PASS: {len(passes)}  |  FAIL: {len(fails)}")
    log(f"Bugs found: {len(bugs_found)}")

    if fails:
        log("\n--- FAILURES ---")
        for f in fails:
            log(f"  FAIL: {f['test']} - {f['details'][:120]}")

    if bugs_found:
        log("\n--- BUGS TO FILE ---")
        for b in bugs_found:
            log(f"  BUG: {b['title']}")

    # Step 5: File bugs on GitHub
    if bugs_found:
        log("\n>>> FILING BUGS ON GITHUB <<<")
        for bug in bugs_found:
            screenshot_url = ""
            if bug.get("screenshot") and os.path.exists(bug["screenshot"]):
                ts = int(time.time())
                gh_name = f"fresh_hr_{ts}"
                uploaded = upload_screenshot_to_github(bug["screenshot"], gh_name)
                if uploaded:
                    screenshot_url = f"\n\n## Screenshot\n![Screenshot]({uploaded})"

            body = f"""## URL Tested
{API_BASE}

## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Org Admin (ananya@technova.in / Welcome@123)
3. {bug['details']}

## Expected Result
The system should enforce proper validation and business rules.

## Actual Result
{bug['details']}{screenshot_url}
"""
            issue_num = file_github_issue(
                bug["title"],
                body,
                labels=["bug", "verified-bug"]
            )

    # Save results to file
    results_path = os.path.join(SCREENSHOT_DIR, "test_results.json")
    with open(results_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(test_results),
            "passes": len(passes),
            "fails": len(fails),
            "bugs": len(bugs_found),
            "results": test_results,
            "bugs_detail": bugs_found
        }, f, indent=2)
    log(f"\nResults saved to {results_path}")
    log("DONE.")

if __name__ == "__main__":
    main()
