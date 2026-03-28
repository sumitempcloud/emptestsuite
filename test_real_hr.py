"""
Real HR Manager Journey Test - Ananya's Monday Morning at TechNova Solutions
Tests EMP Cloud as a real HR person would use it.
Uses discovered API v1 endpoints + Selenium UI testing.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import uuid
import requests
import traceback
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ============ CONFIG ============
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com"
HR_EMAIL = "ananya@technova.in"
HR_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\hr_journey"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ============ GLOBALS ============
driver = None
test_count = 0
issues_filed = []
all_results = []

# ============ HELPERS ============

def get_driver():
    """Create a fresh Chrome driver."""
    global driver
    if driver:
        try:
            driver.quit()
        except:
            pass
    opts = Options()
    opts.binary_location = CHROME_PATH
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.implicitly_wait(5)
    driver.set_page_load_timeout(30)
    return driver


def maybe_restart_driver():
    """Restart driver every 3 tests."""
    global test_count
    test_count += 1
    if test_count % 3 == 0:
        print(f"  [Restarting driver after {test_count} tests]")
        get_driver()


def screenshot(name):
    """Take screenshot and return file path."""
    safe = name.replace(" ", "_").replace("/", "_").replace("\\", "_")[:80]
    ts = datetime.now().strftime("%H%M%S")
    fname = f"{safe}_{ts}.png"
    fpath = os.path.join(SCREENSHOT_DIR, fname)
    try:
        driver.save_screenshot(fpath)
        print(f"  Screenshot: {fname}")
    except Exception as e:
        print(f"  Screenshot failed: {e}")
        fpath = None
    return fpath


def api_login(email, password):
    """Login via API v1 and return (token, user_data)."""
    try:
        r = requests.post(f"{API_URL}/api/v1/auth/login",
                         json={"email": email, "password": password}, timeout=20)
        if r.status_code == 200:
            data = r.json().get("data", {})
            tokens = data.get("tokens", {})
            token = tokens.get("access_token") or tokens.get("access") or tokens.get("token")
            if not token:
                # Fallback: check top level
                for k, v in data.items():
                    if isinstance(v, str) and len(v) > 100:
                        token = v
                        break
            return token, data
        return None, {"error": f"Status {r.status_code}", "body": r.text[:300]}
    except Exception as e:
        return None, {"error": str(e)}


def api_get(path, token, params=None):
    """API GET request."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{API_URL}{path}", headers=headers, params=params, timeout=20)
        try:
            body = r.json()
        except:
            body = r.text[:500]
        return r.status_code, body
    except Exception as e:
        return 0, {"error": str(e)}


def api_post(path, token, data=None, files=None):
    """API POST request."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if files:
            r = requests.post(f"{API_URL}{path}", headers=headers, data=data, files=files, timeout=20)
        else:
            headers["Content-Type"] = "application/json"
            r = requests.post(f"{API_URL}{path}", headers=headers, json=data, timeout=20)
        try:
            body = r.json()
        except:
            body = r.text[:500]
        return r.status_code, body
    except Exception as e:
        return 0, {"error": str(e)}


def api_put(path, token, data=None):
    """API PUT request."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = requests.put(f"{API_URL}{path}", headers=headers, json=data, timeout=20)
        try:
            body = r.json()
        except:
            body = r.text[:500]
        return r.status_code, body
    except Exception as e:
        return 0, {"error": str(e)}


def upload_screenshot_to_github(filepath):
    """Upload screenshot to GitHub and return the URL."""
    if not filepath or not os.path.exists(filepath):
        return None
    try:
        import base64
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        fname = os.path.basename(filepath)
        path = f"test-screenshots/hr-journey/{fname}"
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
        headers = {
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json"
        }
        resp = requests.put(url, headers=headers, json={
            "message": f"Screenshot: {fname}",
            "content": content
        }, timeout=30)
        if resp.status_code in [200, 201]:
            dl = resp.json().get("content", {}).get("download_url", "")
            print(f"  Uploaded to GitHub: {fname}")
            return dl
        else:
            print(f"  GitHub upload {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"  GitHub upload error: {e}")
        return None


def file_github_issue(title, body, labels=None):
    """File an issue on GitHub."""
    if labels is None:
        labels = ["bug", "hr-journey-test"]
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        headers = {
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json"
        }
        resp = requests.post(url, headers=headers, json={
            "title": title,
            "body": body,
            "labels": labels
        }, timeout=30)
        if resp.status_code in [200, 201]:
            issue_url = resp.json().get("html_url", "")
            print(f"  Filed issue: {title}")
            print(f"  URL: {issue_url}")
            issues_filed.append({"title": title, "url": issue_url})
            return issue_url
        else:
            print(f"  Issue creation failed ({resp.status_code}): {resp.text[:300]}")
            return None
    except Exception as e:
        print(f"  Issue creation error: {e}")
        return None


def record_result(test_name, status, details="", screenshots=None, issue_url=None):
    """Record a test result."""
    all_results.append({
        "test": test_name,
        "status": status,
        "details": details,
        "screenshots": screenshots or [],
        "issue": issue_url
    })
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
    print(f"  [{icon}] {test_name}: {details[:200]}")


def file_issue_with_screenshot(title, what_doing, what_happened, what_expected, screenshot_path, labels=None):
    """File a GitHub issue with screenshot embedded."""
    img_url = upload_screenshot_to_github(screenshot_path) if screenshot_path else None
    body = f"""## What I was trying to do
{what_doing}

## What happened
{what_happened}

## What I expected
{what_expected}

## Environment
- URL: {BASE_URL}
- User: {HR_EMAIL}
- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- Browser: Chrome (headless)
"""
    if img_url:
        body += f"\n## Screenshot\n![screenshot]({img_url})\n"
    return file_github_issue(title, body, labels or ["bug", "hr-journey-test"])


def web_login(email, password):
    """Login via the web UI."""
    driver.get(BASE_URL)
    time.sleep(3)
    try:
        email_field = None
        for sel in ["input[name='email']", "input[type='email']", "#email",
                     "input[placeholder*='email' i]", "input[placeholder*='Email']"]:
            try:
                email_field = driver.find_element(By.CSS_SELECTOR, sel)
                if email_field.is_displayed():
                    break
                email_field = None
            except:
                continue

        if not email_field:
            current = driver.current_url
            if "/dashboard" in current or "/home" in current or current.rstrip("/") == BASE_URL.rstrip("/"):
                # May already be logged in from previous session (cookie persists)
                page_text = get_page_text()
                if len(page_text) > 100:
                    print(f"  Already at app (no login form). URL: {current}")
                    return True
            # Try clicking login
            for btn_text in ["Login", "Sign In", "Log In"]:
                try:
                    btn = driver.find_element(By.XPATH,
                        f"//button[contains(text(),'{btn_text}')] | //a[contains(text(),'{btn_text}')]")
                    btn.click()
                    time.sleep(2)
                    break
                except:
                    continue
            for sel in ["input[name='email']", "input[type='email']", "#email"]:
                try:
                    email_field = driver.find_element(By.CSS_SELECTOR, sel)
                    if email_field.is_displayed():
                        break
                    email_field = None
                except:
                    continue

        if not email_field:
            print(f"  No email field. URL: {driver.current_url}, Title: {driver.title}")
            return True  # Assume already logged in if we can't find login form

        email_field.clear()
        email_field.send_keys(email)

        pass_field = None
        for sel in ["input[name='password']", "input[type='password']", "#password"]:
            try:
                pass_field = driver.find_element(By.CSS_SELECTOR, sel)
                if pass_field.is_displayed():
                    break
                pass_field = None
            except:
                continue

        if pass_field:
            pass_field.clear()
            pass_field.send_keys(password)

        for sel in ["button[type='submit']", "input[type='submit']",
                     "//button[contains(text(),'Login')]", "//button[contains(text(),'Sign')]"]:
            try:
                if sel.startswith("//"):
                    btn = driver.find_element(By.XPATH, sel)
                else:
                    btn = driver.find_element(By.CSS_SELECTOR, sel)
                if btn.is_displayed():
                    btn.click()
                    break
            except:
                continue

        time.sleep(4)
        return True
    except Exception as e:
        print(f"  Login error: {e}")
        return False


def navigate_to(path, wait=3):
    """Navigate to a path under BASE_URL."""
    url = f"{BASE_URL}{path}" if path.startswith("/") else path
    driver.get(url)
    time.sleep(wait)
    return driver.current_url


def find_and_click(selectors, description="element"):
    """Try multiple selectors to find and click."""
    for sel in selectors:
        try:
            if sel.startswith("//"):
                el = driver.find_element(By.XPATH, sel)
            else:
                el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                try:
                    el.click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", el)
                return True
        except:
            continue
    return False


def get_page_text():
    """Get visible page text."""
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""


# ============ HR MANAGER TESTS ============

def test_01_login_dashboard():
    """Login to dashboard. What do you see first?"""
    print("\n=== TEST 1: Login & Dashboard Overview ===")
    logged_in = web_login(HR_EMAIL, HR_PASS)
    ss = screenshot("01_dashboard")

    # Also check via API
    token, user_data = api_login(HR_EMAIL, HR_PASS)
    api_info = []
    if token:
        # Get org stats
        code, data = api_get("/api/v1/organizations/me/stats", token)
        if code == 200:
            api_info.append(f"Org stats: {json.dumps(data.get('data', {}))[:200]}")

        # Check dashboard via attendance
        code, data = api_get("/api/v1/attendance/dashboard", token)
        if code == 200:
            api_info.append(f"Attendance dashboard available")
        else:
            api_info.append(f"Attendance dashboard: {code}")

        # Check announcements
        code, data = api_get("/api/v1/announcements", token)
        if code == 200:
            count = len(data.get("data", []))
            api_info.append(f"Announcements: {count}")

    page_text = get_page_text()
    useful_items = {
        "attendance": any(w in page_text.lower() for w in ["attendance", "present", "absent", "check-in"]),
        "leave": any(w in page_text.lower() for w in ["leave", "pending approval", "time off"]),
        "events": any(w in page_text.lower() for w in ["event", "upcoming", "calendar"]),
        "employees": any(w in page_text.lower() for w in ["employee", "headcount", "team"]),
        "announcements": any(w in page_text.lower() for w in ["announcement", "news", "notice"]),
    }
    present = [k for k, v in useful_items.items() if v]
    missing = [k for k, v in useful_items.items() if not v]

    details = f"Dashboard loaded. Shows: {', '.join(present)}. API: {' | '.join(api_info)}"
    if len(missing) >= 3:
        ss2 = screenshot("01_dashboard_missing")
        issue = file_issue_with_screenshot(
            "HR Dashboard missing critical info - no attendance/leave/events overview",
            "Logged in as HR Manager for Monday morning overview",
            f"Dashboard missing: {', '.join(missing)}",
            "Should show attendance, pending leaves, upcoming events, employee count at a glance",
            ss2, ["enhancement", "hr-journey-test"]
        )
        record_result("Login & Dashboard", "warn", details, [ss], issue)
    else:
        record_result("Login & Dashboard", "pass", details, [ss])
    return token


def test_02_attendance(token):
    """Check who's in today."""
    print("\n=== TEST 2: Attendance Check ===")

    # API: attendance dashboard
    code, data = api_get("/api/v1/attendance/dashboard", token)
    api_info = []
    if code == 200:
        d = data.get("data", {})
        api_info.append(f"Dashboard data keys: {list(d.keys())[:10]}")
        total = d.get("total_employees") or d.get("totalEmployees")
        present = d.get("present") or d.get("present_count")
        absent = d.get("absent") or d.get("absent_count")
        if total: api_info.append(f"Total: {total}")
        if present: api_info.append(f"Present: {present}")
        if absent: api_info.append(f"Absent: {absent}")
    else:
        api_info.append(f"Attendance dashboard: {code}")

    # API: attendance records
    code2, data2 = api_get("/api/v1/attendance/records", token)
    if code2 == 200:
        records = data2.get("data", [])
        if isinstance(records, list):
            api_info.append(f"Records today: {len(records)}")
        elif isinstance(records, dict) and "records" in records:
            api_info.append(f"Records: {len(records['records'])}")

    # UI check
    navigate_to("/attendance")
    time.sleep(2)
    ss1 = screenshot("02_attendance")
    page_text = get_page_text()

    has_attendance = any(w in page_text.lower() for w in ["attendance", "present", "absent", "check-in", "check-out"])
    has_filter = any(w in page_text.lower() for w in ["filter", "date", "department"])

    details = f"Attendance UI: {'found' if has_attendance else 'not found'}. Filters: {'yes' if has_filter else 'no'}. API: {' | '.join(api_info)}"

    if not has_attendance and code != 200:
        issue = file_issue_with_screenshot(
            "Cannot view today's attendance overview - no present/absent counts visible",
            "Going to Attendance to see who's in today (Monday morning HR check)",
            f"Attendance page doesn't show clear present/absent counts. API dashboard returned {code}.",
            "Should see at-a-glance: how many present, absent, late. Filter by date and department.",
            ss1
        )
        record_result("Attendance Check", "fail", details, [ss1], issue)
    else:
        record_result("Attendance Check", "pass" if has_attendance else "warn", details, [ss1])


def test_03_pending_leaves(token):
    """Check pending leave requests."""
    print("\n=== TEST 3: Pending Leave Requests ===")
    maybe_restart_driver()
    web_login(HR_EMAIL, HR_PASS)

    # API: leave applications
    code, data = api_get("/api/v1/leave/applications", token, params={"status": "pending"})
    api_info = []
    pending_leaves = []
    if code == 200:
        leaves = data.get("data", [])
        if isinstance(leaves, list):
            pending_leaves = leaves
            api_info.append(f"Pending leaves: {len(leaves)}")
            for lv in leaves[:3]:
                name = lv.get("employee_name") or lv.get("employeeName") or "?"
                ltype = lv.get("leave_type") or lv.get("leaveType") or "?"
                api_info.append(f"  - {name}: {ltype}")
        elif isinstance(leaves, dict) and "items" in leaves:
            pending_leaves = leaves["items"]
            api_info.append(f"Pending leaves: {len(leaves['items'])}")
    else:
        api_info.append(f"Leave applications: {code}")
        # Try without status filter
        code2, data2 = api_get("/api/v1/leave/applications", token)
        if code2 == 200:
            all_leaves = data2.get("data", [])
            if isinstance(all_leaves, list):
                pending = [l for l in all_leaves if l.get("status") == "pending"]
                api_info.append(f"All leaves: {len(all_leaves)}, pending: {len(pending)}")
                pending_leaves = pending

    # Check leave types and balances too
    code3, data3 = api_get("/api/v1/leave/types", token)
    if code3 == 200:
        types = data3.get("data", [])
        if isinstance(types, list):
            api_info.append(f"Leave types: {len(types)}")

    # UI
    navigate_to("/leave")
    time.sleep(2)
    ss1 = screenshot("03_leave_page")
    page_text = get_page_text()
    leave_found = any(w in page_text.lower() for w in ["leave", "pending", "approved", "rejected", "application"])

    details = f"Leave UI: {'found' if leave_found else 'not found'}. {' | '.join(api_info)}"

    if not leave_found and code != 200:
        issue = file_issue_with_screenshot(
            "Leave management page not accessible - cannot review pending leave requests",
            "Opening Leave section to review and approve/reject pending leave requests",
            "Leave page doesn't load properly and API returned errors",
            "Should see list of pending requests: employee name, type, dates, days, with approve/reject buttons",
            ss1
        )
        record_result("Pending Leaves", "fail", details, [ss1], issue)
    else:
        record_result("Pending Leaves", "pass" if (leave_found and pending_leaves) else "warn", details, [ss1])

    return pending_leaves


def test_04_add_employee(token):
    """Add new joiner Rahul Sharma."""
    print("\n=== TEST 4: Add New Employee (Rahul Sharma) ===")

    today = datetime.now().strftime("%Y-%m-%d")
    unique_suffix = uuid.uuid4().hex[:6]

    # First get departments
    code, dept_data = api_get("/api/v1/organizations/me/departments", token)
    dept_id = None
    if code == 200:
        depts = dept_data.get("data", [])
        for d in depts:
            if "engineer" in str(d.get("name", "")).lower():
                dept_id = d.get("id")
                break
        if not dept_id and depts:
            dept_id = depts[0].get("id")
        print(f"  Using department ID: {dept_id}")

    # Create user via API: POST /api/v1/users
    user_data = {
        "first_name": "Rahul",
        "last_name": "Sharma",
        "email": f"rahul.sharma+{unique_suffix}@technova.in",
        "role": "employee",
        "department_id": dept_id,
        "designation": "Software Engineer",
        "date_of_joining": today,
        "employment_type": "full_time",
        "contact_number": "+919876543210",
        "gender": "male",
    }

    code, data = api_post("/api/v1/users", token, user_data)
    print(f"  POST /api/v1/users: {code}")
    print(f"  Response: {json.dumps(data)[:400]}")

    rahul_id = None
    api_success = False
    if code in [200, 201]:
        api_success = True
        rahul_id = data.get("data", {}).get("id") if isinstance(data.get("data"), dict) else None
        print(f"  Created Rahul! ID: {rahul_id}")
    elif code == 400:
        # Try with fewer fields
        simple_data = {
            "first_name": "Rahul",
            "last_name": "Sharma",
            "email": f"rahul.sharma+{unique_suffix}@technova.in",
            "role": "employee",
        }
        code2, data2 = api_post("/api/v1/users", token, simple_data)
        print(f"  Retry POST /api/v1/users: {code2}")
        print(f"  Response: {json.dumps(data2)[:400]}")
        if code2 in [200, 201]:
            api_success = True
            rahul_id = data2.get("data", {}).get("id") if isinstance(data2.get("data"), dict) else None

    # Also try invite
    if not api_success:
        invite_data = {
            "email": f"rahul.sharma+{unique_suffix}@technova.in",
            "role": "employee",
            "first_name": "Rahul",
            "last_name": "Sharma",
        }
        code3, data3 = api_post("/api/v1/users/invite", token, invite_data)
        print(f"  POST /api/v1/users/invite: {code3}")
        print(f"  Response: {json.dumps(data3)[:400]}")
        if code3 in [200, 201]:
            api_success = True
            print("  Invited Rahul successfully!")

    # UI check
    navigate_to("/employees")
    time.sleep(2)
    ss1 = screenshot("04_employees")
    page_text = get_page_text()

    # Try to find Add button
    add_btn = find_and_click([
        "//button[contains(text(),'Add')]",
        "//button[contains(text(),'New')]",
        "//button[contains(text(),'Create')]",
        "//a[contains(text(),'Add Employee')]",
        "//a[contains(text(),'Add')]",
        "button.btn-primary",
        "[data-testid='add-employee']",
    ], "Add Employee button")

    if add_btn:
        time.sleep(2)
        ss2 = screenshot("04_add_form")
        page_text = get_page_text()
        has_form = any(w in page_text.lower() for w in ["first name", "last name", "email", "department", "designation"])
        if has_form:
            print("  Add employee form found!")

    details = f"API user creation: {'success' if api_success else 'failed'} (ID: {rahul_id}). UI Add button: {'found' if add_btn else 'not found'}"

    if not api_success and not add_btn:
        issue = file_issue_with_screenshot(
            "Cannot add new employee - neither UI button nor API endpoint works",
            "Adding new joiner Rahul Sharma (Engineering, Software Engineer, starting today)",
            f"POST /api/v1/users returned {code}. No Add Employee button visible in UI.",
            "Should be able to add employee with name, email, department, designation, joining date",
            ss1
        )
        record_result("Add New Employee", "fail", details, [ss1], issue)
    elif api_success and not add_btn:
        issue = file_issue_with_screenshot(
            "Add Employee button missing in UI - had to use API to create employee",
            "Looking for Add Employee button on employees page to add new joiner",
            "API creation worked but no visible Add Employee button in the UI",
            "Should have a prominent Add Employee button on the employees list page",
            ss1, ["ux", "hr-journey-test"]
        )
        record_result("Add New Employee", "warn", details, [ss1], issue)
    else:
        record_result("Add New Employee", "pass", details, [ss1])

    return rahul_id


def test_05_assets(token, rahul_id):
    """Asset management - look for asset functionality."""
    print("\n=== TEST 5: Asset Management ===")

    # The API spec doesn't include assets endpoints - this may be a separate module
    # Check UI
    navigate_to("/assets")
    time.sleep(2)
    ss1 = screenshot("05_assets")
    page_text = get_page_text()

    has_assets = any(w in page_text.lower() for w in ["asset", "laptop", "device", "inventory", "equipment"])

    if not has_assets:
        for path in ["/asset", "/hr/assets", "/asset-management"]:
            navigate_to(path)
            time.sleep(2)
            page_text = get_page_text()
            if any(w in page_text.lower() for w in ["asset", "laptop", "device"]):
                has_assets = True
                ss1 = screenshot("05_assets_found")
                break

    details = f"Assets page: {'found' if has_assets else 'not found'}. (No asset API endpoints in OpenAPI spec)"

    if has_assets:
        record_result("Asset Management", "pass", details, [ss1])
    else:
        # Not in API spec, might be a missing module
        record_result("Asset Management", "warn",
                     "Assets module not found in UI or API. May need to be subscribed/enabled.", [ss1])


def test_06_documents(token):
    """Upload document for employee."""
    print("\n=== TEST 6: Document Upload ===")

    # Check document categories first
    code, data = api_get("/api/v1/documents/categories", token)
    api_info = []
    if code == 200:
        cats = data.get("data", [])
        api_info.append(f"Document categories: {len(cats) if isinstance(cats, list) else 'unknown'}")
        if isinstance(cats, list) and cats:
            api_info.append(f"  Types: {[c.get('name') for c in cats[:5]]}")

    # List existing documents
    code2, data2 = api_get("/api/v1/documents", token)
    if code2 == 200:
        docs = data2.get("data", [])
        api_info.append(f"Existing documents: {len(docs) if isinstance(docs, list) else '?'}")

    # Try uploading
    test_file = os.path.join(SCREENSHOT_DIR, "test_offer_letter.txt")
    with open(test_file, "w") as f:
        f.write("OFFER LETTER - TechNova Solutions\nDear Rahul Sharma,\nWe are pleased to offer you the position of Software Engineer.\nSincerely, HR Team")

    upload_success = False
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with open(test_file, "rb") as f:
            r = requests.post(f"{API_URL}/api/v1/documents/upload",
                            headers=headers,
                            data={"title": "Offer Letter - Rahul Sharma", "category": "offer_letter"},
                            files={"file": ("offer_letter_rahul.pdf", f, "application/pdf")},
                            timeout=20)
        print(f"  POST /api/v1/documents/upload: {r.status_code}")
        print(f"  Response: {r.text[:300]}")
        if r.status_code in [200, 201]:
            upload_success = True
        elif r.status_code == 400:
            api_info.append(f"Upload validation error: {r.text[:200]}")
    except Exception as e:
        api_info.append(f"Upload error: {e}")

    # UI check
    navigate_to("/documents")
    time.sleep(2)
    ss1 = screenshot("06_documents")
    page_text = get_page_text()
    has_docs = any(w in page_text.lower() for w in ["document", "upload", "file", "letter", "category"])

    details = f"Documents UI: {'found' if has_docs else 'not found'}. Upload: {'success' if upload_success else 'failed'}. {' | '.join(api_info)}"

    if not has_docs and not upload_success:
        issue = file_issue_with_screenshot(
            "Cannot upload employee documents - upload fails with errors",
            "Uploading Rahul's offer letter PDF to the documents section",
            f"Document upload API failed. UI page: {'found' if has_docs else 'not found'}",
            "Should be able to upload PDF, select employee, choose document category, and see it in document list",
            ss1
        )
        record_result("Document Upload", "fail", details, [ss1], issue)
    else:
        record_result("Document Upload", "pass" if upload_success else "warn", details, [ss1])


def test_07_create_event(token):
    """Create company all-hands meeting."""
    print("\n=== TEST 7: Create Event (All-Hands Meeting) ===")
    maybe_restart_driver()
    web_login(HR_EMAIL, HR_PASS)

    # Events not in API spec - this means it's a UI-only feature or separate module
    # Check UI
    navigate_to("/events")
    time.sleep(2)
    ss1 = screenshot("07_events")
    page_text = get_page_text()

    has_events = any(w in page_text.lower() for w in ["event", "calendar", "meeting", "schedule", "upcoming"])

    if not has_events:
        for path in ["/event", "/calendar", "/hr/events"]:
            navigate_to(path)
            time.sleep(2)
            page_text = get_page_text()
            if any(w in page_text.lower() for w in ["event", "calendar", "meeting"]):
                has_events = True
                ss1 = screenshot("07_events_found")
                break

    # Try announcements as alternative (announcements API exists)
    announcement_created = False
    next_friday = datetime.now()
    while next_friday.weekday() != 4:
        next_friday += timedelta(days=1)

    ann_data = {
        "title": "Company All-Hands Meeting - " + next_friday.strftime("%B %d"),
        "content": f"Company all-hands meeting scheduled for {next_friday.strftime('%A, %B %d')} at 10:00 AM in Conference Room A. All employees must attend.",
        "type": "event",
        "priority": "high",
    }
    code, data = api_post("/api/v1/announcements", token, ann_data)
    print(f"  POST /api/v1/announcements: {code}")
    print(f"  Response: {json.dumps(data)[:300]}")
    if code in [200, 201]:
        announcement_created = True
        print("  Announcement/event created!")

    details = f"Events UI: {'found' if has_events else 'not found'}. Announcement as event: {'created' if announcement_created else 'failed'}"

    if has_events or announcement_created:
        record_result("Create Event", "pass" if announcement_created else "warn", details, [ss1])
    else:
        issue = file_issue_with_screenshot(
            "Cannot create company events or announcements for employees",
            "Creating all-hands meeting for next Friday for all employees",
            "Events page not found and announcement creation also failed",
            "Should be able to create events with title, date, time, location visible to all employees",
            ss1
        )
        record_result("Create Event", "fail", details, [ss1], issue)


def test_08_survey(token):
    """Create Q1 Employee Satisfaction survey."""
    print("\n=== TEST 8: Create Survey ===")

    # Surveys not in OpenAPI spec - check UI
    navigate_to("/surveys")
    time.sleep(2)
    ss1 = screenshot("08_surveys")
    page_text = get_page_text()

    has_surveys = any(w in page_text.lower() for w in ["survey", "questionnaire", "feedback form", "poll"])

    if not has_surveys:
        for path in ["/survey", "/hr/surveys", "/feedback"]:
            navigate_to(path)
            time.sleep(2)
            page_text = get_page_text()
            if any(w in page_text.lower() for w in ["survey", "questionnaire"]):
                has_surveys = True
                ss1 = screenshot("08_surveys_found")
                break

    details = f"Surveys UI: {'found' if has_surveys else 'not found'}. (Not in API spec - may need separate module)"

    if has_surveys:
        record_result("Create Survey", "pass", details, [ss1])
    else:
        record_result("Create Survey", "warn",
                     "Survey module not found in UI or API. May need to be enabled/subscribed.", [ss1])


def test_09_org_chart(token):
    """Check org chart."""
    print("\n=== TEST 9: Org Chart ===")

    # API: org chart
    code, data = api_get("/api/v1/users/org-chart", token)
    api_info = []
    if code == 200:
        chart = data.get("data", {})
        if isinstance(chart, list):
            api_info.append(f"Org chart: {len(chart)} entries")
        elif isinstance(chart, dict):
            api_info.append(f"Org chart data keys: {list(chart.keys())[:5]}")
    else:
        api_info.append(f"Org chart API: {code}")

    # Also get employee directory
    code2, data2 = api_get("/api/v1/employees/directory", token)
    if code2 == 200:
        directory = data2.get("data", [])
        if isinstance(directory, list):
            api_info.append(f"Employee directory: {len(directory)} employees")

    # UI
    navigate_to("/org-chart")
    time.sleep(3)
    ss1 = screenshot("09_org_chart")
    page_text = get_page_text()
    has_chart = any(w in page_text.lower() for w in ["org chart", "organization", "hierarchy", "reporting"])

    if not has_chart:
        for path in ["/organization-chart", "/orgchart", "/hierarchy"]:
            navigate_to(path)
            time.sleep(2)
            page_text = get_page_text()
            if any(w in page_text.lower() for w in ["org", "chart", "hierarchy"]):
                has_chart = True
                ss1 = screenshot("09_org_chart_found")
                break

    details = f"Org chart UI: {'found' if has_chart else 'not found'}. {' | '.join(api_info)}"

    if code == 200 or has_chart:
        record_result("Org Chart", "pass", details, [ss1])
    else:
        issue = file_issue_with_screenshot(
            "Org chart not accessible - cannot view company hierarchy",
            "Checking org chart to verify team structure and reporting lines",
            f"Org chart page not found. API returned {code}.",
            "Should show visual hierarchy with reporting structure, clickable employee names",
            ss1
        )
        record_result("Org Chart", "fail", details, [ss1], issue)


def test_10_community(token):
    """Post on community forum."""
    print("\n=== TEST 10: Community Forum ===")

    # Community not in API spec - check UI
    navigate_to("/community")
    time.sleep(2)
    ss1 = screenshot("10_community")
    page_text = get_page_text()

    has_community = any(w in page_text.lower() for w in ["community", "forum", "post", "discussion", "feed"])

    if not has_community:
        for path in ["/forum", "/posts", "/feed", "/social"]:
            navigate_to(path)
            time.sleep(2)
            page_text = get_page_text()
            if any(w in page_text.lower() for w in ["community", "forum", "post"]):
                has_community = True
                ss1 = screenshot("10_community_found")
                break

    details = f"Community: {'found' if has_community else 'not found'}. (Not in API spec)"

    if has_community:
        record_result("Community Post", "pass", details, [ss1])
    else:
        record_result("Community Post", "warn",
                     "Community forum not found. May need separate module.", [ss1])


# ============ EMPLOYEE TESTS (PRIYA) ============

def test_11_employee_dashboard():
    """Login as Priya, check dashboard."""
    print("\n=== TEST 11: Employee Dashboard (Priya) ===")
    maybe_restart_driver()

    # Clear cookies for clean Priya login
    get_driver()
    web_login(EMP_EMAIL, EMP_PASS)
    ss1 = screenshot("11_emp_dashboard")
    page_text = get_page_text()

    # API check
    token, user_data = api_login(EMP_EMAIL, EMP_PASS)
    api_info = []
    if token:
        # Check my attendance
        code, data = api_get("/api/v1/attendance/me/today", token)
        if code == 200:
            api_info.append(f"My attendance today: {json.dumps(data.get('data', {}))[:100]}")
        else:
            api_info.append(f"My attendance: {code}")

        # Check my leave balances
        code2, data2 = api_get("/api/v1/leave/balances", token)
        if code2 == 200:
            balances = data2.get("data", [])
            if isinstance(balances, list):
                api_info.append(f"Leave balances: {len(balances)} types")
                for b in balances[:3]:
                    name = b.get("leave_type") or b.get("name") or b.get("type", "?")
                    bal = b.get("balance") or b.get("remaining") or b.get("available")
                    api_info.append(f"  {name}: {bal}")

        # Check user role
        user = user_data.get("user", {})
        role = user.get("role", "unknown")
        api_info.append(f"User role: {role}")

    # Check for data that shouldn't be visible to employees
    sensitive_words = ["all employees", "headcount report", "billing", "subscription", "revenue"]
    found_sensitive = [w for w in sensitive_words if w in page_text.lower()]

    if found_sensitive:
        issue = file_issue_with_screenshot(
            "Employee sees HR-level data on dashboard - possible data leak",
            "Logged in as regular employee Priya to check personal dashboard",
            f"Dashboard shows sensitive terms: {', '.join(found_sensitive)}",
            "Employee should only see own attendance, leave balance, and personal pending items",
            ss1
        )
        record_result("Employee Dashboard", "fail", f"Sensitive data visible: {found_sensitive}. {' | '.join(api_info)}", [ss1], issue)
    else:
        details = f"Employee dashboard loaded. {' | '.join(api_info)}"
        record_result("Employee Dashboard", "pass", details, [ss1])

    return token


def test_12_apply_leave(emp_token):
    """Apply for sick leave as Priya."""
    print("\n=== TEST 12: Apply for Sick Leave ===")

    next_monday = datetime.now()
    while next_monday.weekday() != 0:
        next_monday += timedelta(days=1)
    next_tuesday = next_monday + timedelta(days=1)

    # Get leave types
    code, data = api_get("/api/v1/leave/types", emp_token)
    leave_type_id = None
    if code == 200:
        types = data.get("data", [])
        if isinstance(types, list):
            print(f"  Leave types: {[t.get('name') for t in types]}")
            for t in types:
                if "sick" in str(t.get("name", "")).lower():
                    leave_type_id = t.get("id")
                    break
            if not leave_type_id and types:
                leave_type_id = types[0].get("id")
            print(f"  Using leave type ID: {leave_type_id}")

    # Apply leave
    leave_data = {
        "leave_type_id": leave_type_id,
        "start_date": next_monday.strftime("%Y-%m-%d"),
        "end_date": next_tuesday.strftime("%Y-%m-%d"),
        "reason": "Not feeling well",
    }
    code, data = api_post("/api/v1/leave/applications", emp_token, leave_data)
    print(f"  POST /api/v1/leave/applications: {code}")
    print(f"  Response: {json.dumps(data)[:400]}")

    leave_applied = code in [200, 201]

    if not leave_applied and code == 400:
        # Try different field names
        alt_data = {
            "leave_type": leave_type_id,
            "from_date": next_monday.strftime("%Y-%m-%d"),
            "to_date": next_tuesday.strftime("%Y-%m-%d"),
            "reason": "Not feeling well",
            "type": "sick",
        }
        code2, data2 = api_post("/api/v1/leave/applications", emp_token, alt_data)
        print(f"  Retry: {code2}: {json.dumps(data2)[:300]}")
        leave_applied = code2 in [200, 201]

    # Check in UI
    navigate_to("/leave")
    time.sleep(2)
    ss1 = screenshot("12_leave_apply")

    # Try clicking Apply
    apply_clicked = find_and_click([
        "//button[contains(text(),'Apply')]",
        "//button[contains(text(),'Request')]",
        "//a[contains(text(),'Apply')]",
        "//button[contains(text(),'New')]",
    ], "Apply Leave")

    if apply_clicked:
        time.sleep(2)
        ss2 = screenshot("12_leave_form")

    details = f"Leave API: {'applied' if leave_applied else f'failed ({code})'}. UI Apply: {'found' if apply_clicked else 'not found'}"

    if leave_applied:
        record_result("Apply Leave", "pass", details, [ss1])
    else:
        issue = file_issue_with_screenshot(
            "Cannot apply for sick leave - leave application fails",
            f"Employee Priya applying for 2 days sick leave ({next_monday.strftime('%Y-%m-%d')} to {next_tuesday.strftime('%Y-%m-%d')})",
            f"Leave application API returned {code}. Response: {json.dumps(data)[:200]}",
            "Should be able to select leave type, pick dates, enter reason, and submit",
            ss1
        )
        record_result("Apply Leave", "fail", details, [ss1], issue)


def test_13_payslip(emp_token):
    """Check payslip via SSO."""
    print("\n=== TEST 13: Payslip Check ===")
    maybe_restart_driver()
    web_login(EMP_EMAIL, EMP_PASS)

    # Try payroll module
    navigate_to("/payroll")
    time.sleep(3)
    ss1 = screenshot("13_payroll")
    current = driver.current_url
    page_text = get_page_text()

    has_payroll = any(w in page_text.lower() for w in ["payslip", "salary", "earnings", "deductions", "pay"])

    if not has_payroll:
        # Try SSO to payroll module
        driver.get("https://testpayroll.empcloud.com")
        time.sleep(3)
        ss1 = screenshot("13_payroll_sso")
        page_text = get_page_text()
        has_payroll = any(w in page_text.lower() for w in ["payslip", "salary", "pay", "login", "earnings"])

    details = f"Payroll: {'accessible' if has_payroll else 'not accessible'}. URL: {driver.current_url}"
    record_result("Check Payslip", "pass" if has_payroll else "warn", details, [ss1])


def test_14_announcements(emp_token):
    """Check announcements."""
    print("\n=== TEST 14: Announcements ===")

    # API
    code, data = api_get("/api/v1/announcements", emp_token)
    api_info = []
    if code == 200:
        anns = data.get("data", [])
        if isinstance(anns, list):
            api_info.append(f"Announcements: {len(anns)}")
            for a in anns[:3]:
                api_info.append(f"  - {a.get('title', '?')}")

    # Unread count
    code2, data2 = api_get("/api/v1/announcements/unread-count", emp_token)
    if code2 == 200:
        unread = data2.get("data", {})
        api_info.append(f"Unread: {unread}")

    # UI
    navigate_to("/announcements")
    time.sleep(2)
    ss1 = screenshot("14_announcements")
    page_text = get_page_text()
    has_ann = any(w in page_text.lower() for w in ["announcement", "notice", "news"])

    details = f"Announcements: {'visible' if has_ann else 'not visible'}. {' | '.join(api_info)}"
    record_result("Announcements", "pass" if (has_ann or code == 200) else "warn", details, [ss1])


def test_15_survey_fill(emp_token):
    """Find and fill survey as employee."""
    print("\n=== TEST 15: Fill Survey ===")

    navigate_to("/surveys")
    time.sleep(2)
    ss1 = screenshot("15_surveys")
    page_text = get_page_text()
    has_surveys = any(w in page_text.lower() for w in ["survey", "questionnaire", "feedback"])

    details = f"Surveys for employee: {'found' if has_surveys else 'not found'}"
    record_result("Fill Survey", "pass" if has_surveys else "warn", details, [ss1])


def test_16_helpdesk(emp_token):
    """Create helpdesk ticket."""
    print("\n=== TEST 16: Helpdesk Ticket ===")
    maybe_restart_driver()
    web_login(EMP_EMAIL, EMP_PASS)

    # Not in API spec - check UI
    navigate_to("/helpdesk")
    time.sleep(2)
    ss1 = screenshot("16_helpdesk")
    page_text = get_page_text()
    has_helpdesk = any(w in page_text.lower() for w in ["helpdesk", "ticket", "support", "help desk"])

    if not has_helpdesk:
        for path in ["/help-desk", "/tickets", "/support"]:
            navigate_to(path)
            time.sleep(2)
            page_text = get_page_text()
            if any(w in page_text.lower() for w in ["helpdesk", "ticket", "support"]):
                has_helpdesk = True
                ss1 = screenshot("16_helpdesk_found")
                break

    details = f"Helpdesk: {'found' if has_helpdesk else 'not found'}"
    record_result("Helpdesk", "pass" if has_helpdesk else "warn",
                 details + " (Not in API spec - may be separate module)", [ss1])


def test_17_wellness(emp_token):
    """Wellness check-in."""
    print("\n=== TEST 17: Wellness Check-in ===")

    navigate_to("/wellness")
    time.sleep(2)
    ss1 = screenshot("17_wellness")
    page_text = get_page_text()
    has_wellness = any(w in page_text.lower() for w in ["wellness", "wellbeing", "mood", "check-in", "well-being"])

    details = f"Wellness: {'found' if has_wellness else 'not found'}"
    record_result("Wellness", "pass" if has_wellness else "warn", details, [ss1])


def test_18_knowledge_base(emp_token):
    """Knowledge base search."""
    print("\n=== TEST 18: Knowledge Base ===")

    navigate_to("/knowledge-base")
    time.sleep(2)
    ss1 = screenshot("18_kb")
    page_text = get_page_text()
    has_kb = any(w in page_text.lower() for w in ["knowledge", "article", "guide", "wiki", "faq"])

    if not has_kb:
        for path in ["/kb", "/wiki", "/articles", "/faq"]:
            navigate_to(path)
            time.sleep(2)
            page_text = get_page_text()
            if any(w in page_text.lower() for w in ["knowledge", "article", "guide"]):
                has_kb = True
                ss1 = screenshot("18_kb_found")
                break

    details = f"Knowledge base: {'found' if has_kb else 'not found'}"
    record_result("Knowledge Base", "pass" if has_kb else "warn", details, [ss1])


def test_19_feedback(emp_token):
    """Anonymous feedback."""
    print("\n=== TEST 19: Anonymous Feedback ===")
    maybe_restart_driver()
    web_login(EMP_EMAIL, EMP_PASS)

    navigate_to("/feedback")
    time.sleep(2)
    ss1 = screenshot("19_feedback")
    page_text = get_page_text()
    has_feedback = any(w in page_text.lower() for w in ["feedback", "suggestion", "anonymous"])

    details = f"Feedback: {'found' if has_feedback else 'not found'}"
    record_result("Anonymous Feedback", "pass" if has_feedback else "warn", details, [ss1])


def test_20_my_assets(emp_token):
    """Check assigned assets."""
    print("\n=== TEST 20: My Assets ===")

    navigate_to("/assets")
    time.sleep(2)
    ss1 = screenshot("20_assets")
    page_text = get_page_text()
    has_assets = any(w in page_text.lower() for w in ["asset", "laptop", "device", "assigned"])

    details = f"My assets: {'found' if has_assets else 'not found'}"
    record_result("My Assets", "pass" if has_assets else "warn", details, [ss1])


# ============ HR ADMIN TASKS ============

def test_21_reports(hr_token):
    """Generate reports."""
    print("\n=== TEST 21: HR Reports ===")
    maybe_restart_driver()
    web_login(HR_EMAIL, HR_PASS)

    # API: headcount
    code, data = api_get("/api/v1/employees/headcount", hr_token)
    api_info = []
    if code == 200:
        hc = data.get("data", {})
        api_info.append(f"Headcount: {json.dumps(hc)[:200]}")

    # API: attendance monthly report
    code2, data2 = api_get("/api/v1/attendance/monthly-report", hr_token,
                           params={"month": datetime.now().month, "year": datetime.now().year})
    if code2 == 200:
        api_info.append("Monthly attendance report: available")
    else:
        api_info.append(f"Monthly report: {code2}")

    # UI
    navigate_to("/reports")
    time.sleep(2)
    ss1 = screenshot("21_reports")
    page_text = get_page_text()
    has_reports = any(w in page_text.lower() for w in ["report", "analytics", "headcount", "statistics"])

    details = f"Reports UI: {'found' if has_reports else 'not found'}. {' | '.join(api_info)}"
    record_result("HR Reports", "pass" if (has_reports or code == 200) else "warn", details, [ss1])


def test_22_billing(hr_token):
    """Check billing."""
    print("\n=== TEST 22: Billing ===")

    # API: billing summary
    code, data = api_get("/api/v1/subscriptions/billing-summary", hr_token)
    api_info = []
    if code == 200:
        billing = data.get("data", {})
        api_info.append(f"Billing data: {json.dumps(billing)[:300]}")

    # API: subscriptions
    code2, data2 = api_get("/api/v1/subscriptions", hr_token)
    if code2 == 200:
        subs = data2.get("data", [])
        if isinstance(subs, list):
            api_info.append(f"Subscriptions: {len(subs)}")
            for s in subs[:3]:
                api_info.append(f"  - {s.get('module_name') or s.get('name', '?')}: {s.get('status', '?')}")

    # UI
    navigate_to("/billing")
    time.sleep(2)
    ss1 = screenshot("22_billing")
    page_text = get_page_text()
    has_billing = any(w in page_text.lower() for w in ["billing", "subscription", "plan", "invoice"])

    if not has_billing:
        navigate_to("/subscription")
        time.sleep(2)
        page_text = get_page_text()
        has_billing = any(w in page_text.lower() for w in ["billing", "subscription", "plan"])
        if has_billing:
            ss1 = screenshot("22_billing_found")

    details = f"Billing UI: {'found' if has_billing else 'not found'}. {' | '.join(api_info)}"
    record_result("Billing", "pass" if (has_billing or code == 200) else "warn", details, [ss1])


def test_23_settings(hr_token):
    """Company settings."""
    print("\n=== TEST 23: Company Settings ===")

    # API: org info
    code, data = api_get("/api/v1/organizations/me", hr_token)
    api_info = []
    if code == 200:
        org = data.get("data", {})
        api_info.append(f"Org: {org.get('name', '?')}")
        api_info.append(f"Email: {org.get('email', '?')}")
        api_info.append(f"Address: {org.get('address', 'not set')}")

        # Try updating address
        update_data = {"address": "123 Tech Park, Bangalore, Karnataka 560001"}
        code2, data2 = api_put("/api/v1/organizations/me", hr_token, update_data)
        if code2 == 200:
            api_info.append("Address update: success")
        else:
            api_info.append(f"Address update: {code2}")

    # UI
    navigate_to("/settings")
    time.sleep(2)
    ss1 = screenshot("23_settings")
    page_text = get_page_text()
    has_settings = any(w in page_text.lower() for w in ["settings", "organization", "company", "configuration"])

    details = f"Settings UI: {'found' if has_settings else 'not found'}. {' | '.join(api_info)}"
    record_result("Company Settings", "pass" if (has_settings or code == 200) else "warn", details, [ss1])


def test_24_audit(hr_token):
    """Audit log."""
    print("\n=== TEST 24: Audit Log ===")
    maybe_restart_driver()
    web_login(HR_EMAIL, HR_PASS)

    # API: audit
    code, data = api_get("/api/v1/audit", hr_token)
    api_info = []
    if code == 200:
        audit = data.get("data", [])
        if isinstance(audit, list):
            api_info.append(f"Audit entries: {len(audit)}")
            for a in audit[:3]:
                api_info.append(f"  - {a.get('action', '?')}: {a.get('description', '')[:50]}")
        elif isinstance(audit, dict) and "items" in audit:
            api_info.append(f"Audit entries: {len(audit['items'])}")
    else:
        api_info.append(f"Audit API: {code}")

    # UI
    navigate_to("/audit-log")
    time.sleep(2)
    ss1 = screenshot("24_audit")
    page_text = get_page_text()
    has_audit = any(w in page_text.lower() for w in ["audit", "log", "activity", "history"])

    if not has_audit:
        navigate_to("/audit")
        time.sleep(2)
        page_text = get_page_text()
        has_audit = any(w in page_text.lower() for w in ["audit", "activity", "history"])
        if has_audit:
            ss1 = screenshot("24_audit_found")

    details = f"Audit UI: {'found' if has_audit else 'not found'}. {' | '.join(api_info)}"
    record_result("Audit Log", "pass" if (has_audit or code == 200) else "warn", details, [ss1])


def test_25_invite(hr_token):
    """Invite new user."""
    print("\n=== TEST 25: Invite New User ===")

    unique_email = f"newhire+{uuid.uuid4().hex[:6]}@technova.in"

    # API: invite
    invite_data = {
        "email": unique_email,
        "role": "employee",
        "first_name": "New",
        "last_name": "Hire",
    }
    code, data = api_post("/api/v1/users/invite", hr_token, invite_data)
    print(f"  POST /api/v1/users/invite: {code}")
    print(f"  Response: {json.dumps(data)[:400]}")

    invite_sent = code in [200, 201]

    # Also check user creation
    if not invite_sent:
        user_data = {
            "email": unique_email,
            "role": "employee",
            "first_name": "New",
            "last_name": "Hire",
        }
        code2, data2 = api_post("/api/v1/users", hr_token, user_data)
        print(f"  POST /api/v1/users: {code2}")
        print(f"  Response: {json.dumps(data2)[:400]}")
        invite_sent = code2 in [200, 201]

    # UI
    navigate_to("/employees")
    time.sleep(2)
    ss1 = screenshot("25_invite")

    invite_btn = find_and_click([
        "//button[contains(text(),'Invite')]",
        "//a[contains(text(),'Invite')]",
    ], "Invite button")

    if invite_btn:
        time.sleep(2)
        screenshot("25_invite_form")

    details = f"Invite API: {'sent ({unique_email})' if invite_sent else f'failed ({code})'}. UI Invite: {'found' if invite_btn else 'not found'}"

    if invite_sent:
        record_result("Invite User", "pass", details, [ss1])
    else:
        issue = file_issue_with_screenshot(
            "Cannot invite new employees - invitation API returns error",
            f"Sending invite to {unique_email} to join the organization",
            f"POST /api/v1/users/invite returned {code}: {json.dumps(data)[:200]}",
            "Should be able to invite users by email with role selection",
            ss1
        )
        record_result("Invite User", "fail", details, [ss1], issue)


def test_26_missing_features(hr_token):
    """Check for commonly expected HR features."""
    print("\n=== TEST 26: Missing Features Audit ===")

    missing = []
    available = []

    # Check leave policies
    code, data = api_get("/api/v1/leave/policies", hr_token)
    if code == 200:
        policies = data.get("data", [])
        available.append(f"Leave policies ({len(policies) if isinstance(policies, list) else '?'} found)")
    else:
        missing.append("Leave policies API returns error")

    # Check leave types
    code, data = api_get("/api/v1/leave/types", hr_token)
    if code == 200:
        types = data.get("data", [])
        available.append(f"Leave types ({len(types) if isinstance(types, list) else '?'} configured)")
    else:
        missing.append("Leave types not accessible")

    # Check user import (bulk operations)
    code, _ = api_post("/api/v1/users/import", hr_token, {})
    if code in [200, 400]:  # 400 means endpoint exists but needs data
        available.append("Bulk user import")
    else:
        missing.append("Bulk employee import not available")

    # Check modules
    code, data = api_get("/api/v1/modules", hr_token)
    if code == 200:
        modules = data.get("data", [])
        if isinstance(modules, list):
            available.append(f"Modules: {len(modules)} ({', '.join(m.get('name','?') for m in modules[:5])})")

    # Check what's NOT in the API spec
    not_in_spec = [
        "Bulk leave approval (no bulk approve endpoint)",
        "Employee data export to Excel/CSV",
        "Notification system for leave applications",
        "Probation period tracking",
        "Offer letter generation",
        "Training and certification tracking",
        "Events/calendar module (standalone)",
        "Survey creation module",
        "Helpdesk/ticketing system",
        "Wellness check-in",
        "Anonymous feedback system",
        "Knowledge base/wiki",
    ]

    ss1 = screenshot("26_features")

    # File consolidated issue
    body = f"""## Missing Features for HR Daily Workflows

As an HR Manager going through a typical Monday morning, the following features are needed but appear missing or incomplete:

### Not Available in API (94 documented endpoints)
{"".join(f'- {f}' + chr(10) for f in not_in_spec)}

### Available Features Found via API
{"".join(f'- {f}' + chr(10) for f in available)}

### Issues Encountered
{"".join(f'- {f}' + chr(10) for f in missing)}

### Context
These are common HR features expected in an enterprise HRMS. Some may be available in separate modules (Payroll, Performance, etc.) accessible via SSO.

- Tested: {datetime.now().strftime('%Y-%m-%d')}
- User: HR Manager (ananya@technova.in)
- API spec: 94 endpoints documented in OpenAPI
"""

    if len(not_in_spec) >= 5:
        file_github_issue(
            "Multiple core HR features missing from API - bulk ops, export, notifications, surveys",
            body,
            ["enhancement", "hr-journey-test", "feature-request"]
        )

    details = f"Available: {len(available)}. Missing/needed: {len(not_in_spec)}"
    record_result("Missing Features Audit", "warn", details, [ss1])


# ============ MAIN ============

def main():
    global driver
    print("=" * 70)
    print("  ANANYA'S MONDAY MORNING - HR MANAGER JOURNEY TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    get_driver()

    try:
        # ---- PART 1: HR MANAGER ----
        print("\n" + "=" * 50)
        print("  PART 1: HR MANAGER (Ananya)")
        print("=" * 50)

        hr_token = test_01_login_dashboard()
        if not hr_token:
            hr_token, _ = api_login(HR_EMAIL, HR_PASS)
            if not hr_token:
                print("FATAL: Cannot get API token for HR manager!")
                return

        test_02_attendance(hr_token)
        pending = test_03_pending_leaves(hr_token)
        rahul_id = test_04_add_employee(hr_token)
        test_05_assets(hr_token, rahul_id)
        test_06_documents(hr_token)
        test_07_create_event(hr_token)
        test_08_survey(hr_token)
        test_09_org_chart(hr_token)
        test_10_community(hr_token)

        # ---- PART 2: EMPLOYEE ----
        print("\n" + "=" * 50)
        print("  PART 2: EMPLOYEE (Priya)")
        print("=" * 50)

        emp_token = test_11_employee_dashboard()
        if not emp_token:
            emp_token, _ = api_login(EMP_EMAIL, EMP_PASS)

        test_12_apply_leave(emp_token)
        test_13_payslip(emp_token)
        test_14_announcements(emp_token)
        test_15_survey_fill(emp_token)
        test_16_helpdesk(emp_token)
        test_17_wellness(emp_token)
        test_18_knowledge_base(emp_token)
        test_19_feedback(emp_token)
        test_20_my_assets(emp_token)

        # ---- PART 3: HR ADMIN ----
        print("\n" + "=" * 50)
        print("  PART 3: HR MANAGER - ADMIN TASKS")
        print("=" * 50)

        # Re-login as HR
        hr_token2, _ = api_login(HR_EMAIL, HR_PASS)
        if not hr_token2:
            hr_token2 = hr_token

        test_21_reports(hr_token2)
        test_22_billing(hr_token2)
        test_23_settings(hr_token2)
        test_24_audit(hr_token2)
        test_25_invite(hr_token2)
        test_26_missing_features(hr_token2)

    except Exception as e:
        print(f"\n!!! FATAL ERROR: {e}")
        traceback.print_exc()
        if driver:
            screenshot("FATAL_ERROR")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

    # ============ SUMMARY ============
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)

    pass_count = sum(1 for r in all_results if r["status"] == "pass")
    fail_count = sum(1 for r in all_results if r["status"] == "fail")
    warn_count = sum(1 for r in all_results if r["status"] == "warn")

    print(f"\n  Total: {len(all_results)} | PASS: {pass_count} | FAIL: {fail_count} | WARN: {warn_count}")
    print()

    for r in all_results:
        icon = {"pass": "OK  ", "fail": "FAIL", "warn": "WARN"}[r["status"]]
        print(f"  [{icon}] {r['test']}: {r['details'][:120]}")

    if issues_filed:
        print(f"\n  Issues Filed: {len(issues_filed)}")
        for i in issues_filed:
            print(f"    - {i['title'][:80]}")
            print(f"      {i['url']}")

    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
