"""
LMS Module - Employee Perspective Test (priya@technova.in)
Tests: SSO login, assigned courses, learning paths, certifications,
       compliance training, take a course, verify no admin access
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
import json
import os
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_lms_employee"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

LOGIN_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
LMS_BASE = "https://testlms.empcloud.com"
LMS_API = "https://testlms-api.empcloud.com/api/v1"
EMAIL = "priya@technova.in"
PASSWORD = "Welcome@123"

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

bugs = []
test_results = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {name}.png")
    return path

def record(test_name, status, details=""):
    test_results.append({"test": test_name, "status": status, "details": details})
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
    log(f"  [{icon}] {test_name}: {details}")

def file_bug(title, body):
    bugs.append(title)
    log(f"  BUG: {title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github+json"
            },
            json={"title": title, "body": body, "labels": ["bug", "lms"]}
        )
        if resp.status_code == 201:
            log(f"  Filed issue #{resp.json()['number']}: {title}")
        else:
            log(f"  Failed to file issue ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        log(f"  Error filing bug: {e}")

def create_driver():
    opts = Options()
    opts.binary_location = CHROME_PATH
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    return driver

# ============================
# STEP 1: API Login + SSO Token
# ============================
def get_sso_token():
    log("Logging in as employee (priya@technova.in) via API...")
    resp = requests.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD})
    log(f"  Login status: {resp.status_code}")
    if resp.status_code != 200:
        log(f"  Login failed: {resp.text[:500]}")
        return None, None
    data = resp.json()
    log(f"  Login response keys: {list(data.keys())}")
    if "data" in data:
        log(f"  data keys: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data'])}")

    token = (
        data.get("data", {}).get("tokens", {}).get("access_token")
        or data.get("data", {}).get("token")
        or data.get("token")
    )
    if not token:
        log(f"  Could not extract token. Full response: {json.dumps(data)[:800]}")
        return None, data
    log(f"  Got token: {token[:30]}...")
    return token, data

# ============================
# STEP 2: SSO into LMS
# ============================
def test_sso_login(driver, token):
    log("\n=== TEST: SSO Login to LMS as Employee ===")
    sso_url = f"{LMS_BASE}?sso_token={token}"
    log(f"  Navigating to: {LMS_BASE}?sso_token=<token>")

    try:
        driver.get(sso_url)
        time.sleep(5)
        screenshot(driver, "01_sso_landing")

        current_url = driver.current_url
        page_title = driver.title
        log(f"  Current URL: {current_url}")
        log(f"  Page title: {page_title}")

        # Get page source snippet for debugging
        body_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
        log(f"  Page body (first 1000 chars): {body_text[:500]}")

        # Check for common failure indicators
        page_lower = body_text.lower()
        if "login" in current_url.lower() and "sso" not in current_url.lower():
            record("SSO Login", "fail", f"Redirected to login page: {current_url}")
            file_bug(
                "[LMS Employee] SSO login fails for employee user",
                f"**Steps:** Login as priya@technova.in, get SSO token, navigate to LMS with sso_token param.\n\n"
                f"**Expected:** Employee dashboard loads.\n\n"
                f"**Actual:** Redirected to login page: {current_url}\n\n"
                f"**Page text:** {body_text[:500]}\n\n"
                f"**Note:** Admin SSO was also reported as failing for LMS."
            )
            return False
        elif "error" in page_lower or "unauthorized" in page_lower or "invalid" in page_lower:
            record("SSO Login", "fail", f"Error on page: {body_text[:200]}")
            file_bug(
                "[LMS Employee] SSO login shows error for employee user",
                f"**Steps:** Login as priya@technova.in, navigate to LMS with sso_token.\n\n"
                f"**Expected:** Dashboard loads.\n\n"
                f"**Actual:** Error shown: {body_text[:300]}\n\n"
                f"**URL:** {current_url}"
            )
            return False
        elif "not found" in page_lower or "404" in page_lower:
            record("SSO Login", "fail", f"404 or not found: {body_text[:200]}")
            file_bug(
                "[LMS Employee] LMS returns 404 after SSO login as employee",
                f"**URL:** {current_url}\n**Page:** {body_text[:300]}"
            )
            return False
        else:
            record("SSO Login", "pass", f"Landed on: {current_url}")
            return True

    except Exception as e:
        screenshot(driver, "01_sso_error")
        record("SSO Login", "fail", f"Exception: {e}")
        file_bug(
            "[LMS Employee] SSO login throws exception for employee",
            f"**Error:** {str(e)}\n\n**URL attempted:** {sso_url}"
        )
        return False

# ============================
# STEP 3: Explore LMS pages
# ============================
def test_lms_pages(driver, token):
    log("\n=== TEST: Explore LMS Employee Pages ===")

    # Pages an employee might see
    employee_pages = [
        ("dashboard", "/dashboard", "Employee Dashboard"),
        ("my_courses", "/my-courses", "My Courses"),
        ("courses", "/courses", "Course Catalog"),
        ("learning_paths", "/learning-paths", "Learning Paths"),
        ("certifications", "/certifications", "Certifications"),
        ("compliance", "/compliance", "Compliance Training"),
        ("my_learning", "/my-learning", "My Learning"),
        ("calendar", "/calendar", "Training Calendar"),
        ("reports", "/reports", "Reports"),
    ]

    # Admin/restricted pages employee should NOT access
    admin_pages = [
        ("admin_settings", "/settings", "Settings (Admin)"),
        ("admin_courses_create", "/courses/create", "Create Course (Admin)"),
        ("admin_manage", "/admin", "Admin Panel"),
        ("admin_users", "/users", "User Management"),
        ("admin_analytics", "/analytics", "Analytics (Admin)"),
    ]

    accessible_pages = []

    log("\n--- Employee pages ---")
    for slug, path, label in employee_pages:
        try:
            url = f"{LMS_BASE}{path}"
            driver.get(url)
            time.sleep(3)
            screenshot(driver, f"02_page_{slug}")

            current_url = driver.current_url
            body_text = driver.find_element(By.TAG_NAME, "body").text[:800]
            page_lower = body_text.lower()

            log(f"  [{slug}] URL: {current_url}")
            log(f"  [{slug}] Content preview: {body_text[:200]}")

            if "login" in current_url.lower() and "sso" not in current_url.lower():
                record(f"Page: {label}", "fail", "Redirected to login")
            elif "404" in page_lower or "not found" in page_lower:
                record(f"Page: {label}", "warn", "Page not found / 404")
            elif "unauthorized" in page_lower or "forbidden" in page_lower or "access denied" in page_lower:
                record(f"Page: {label}", "warn", "Access denied")
            else:
                record(f"Page: {label}", "pass", f"Accessible at {current_url}")
                accessible_pages.append(slug)
        except Exception as e:
            screenshot(driver, f"02_page_{slug}_error")
            record(f"Page: {label}", "fail", f"Error: {e}")

    log("\n--- Admin pages (should be restricted) ---")
    for slug, path, label in admin_pages:
        try:
            url = f"{LMS_BASE}{path}"
            driver.get(url)
            time.sleep(3)
            screenshot(driver, f"03_admin_{slug}")

            current_url = driver.current_url
            body_text = driver.find_element(By.TAG_NAME, "body").text[:800]
            page_lower = body_text.lower()

            log(f"  [{slug}] URL: {current_url}")
            log(f"  [{slug}] Content preview: {body_text[:200]}")

            # Check if employee can access admin pages (they shouldn't)
            is_blocked = (
                "login" in current_url.lower()
                or "unauthorized" in page_lower
                or "forbidden" in page_lower
                or "access denied" in page_lower
                or "not found" in page_lower
                or "404" in page_lower
                or path not in current_url.lower()  # redirected away
            )

            if is_blocked:
                record(f"Admin Restriction: {label}", "pass", "Correctly restricted")
            else:
                record(f"Admin Restriction: {label}", "fail", f"Employee CAN access {label}!")
                file_bug(
                    f"[LMS Employee] Employee can access admin page: {label}",
                    f"**Steps:** Login as employee (priya@technova.in), navigate to {url}\n\n"
                    f"**Expected:** Access denied or redirect.\n\n"
                    f"**Actual:** Page loads with content: {body_text[:300]}\n\n"
                    f"**Security Impact:** Employee should not have admin access."
                )
        except Exception as e:
            screenshot(driver, f"03_admin_{slug}_error")
            record(f"Admin Restriction: {label}", "warn", f"Error: {e}")

    return accessible_pages

# ============================
# STEP 4: LMS API exploration
# ============================
def test_lms_api(token):
    log("\n=== TEST: LMS API Endpoints as Employee ===")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    api_endpoints = [
        ("GET", "/courses", "List courses"),
        ("GET", "/my-courses", "My assigned courses"),
        ("GET", "/learning-paths", "Learning paths"),
        ("GET", "/certifications", "Certifications"),
        ("GET", "/compliance", "Compliance training"),
        ("GET", "/dashboard", "Dashboard data"),
        ("GET", "/profile", "User profile"),
        ("GET", "/notifications", "Notifications"),
        ("GET", "/categories", "Course categories"),
    ]

    admin_api_endpoints = [
        ("POST", "/courses", "Create course (admin)", {"title": "Test", "description": "Test"}),
        ("GET", "/users", "List users (admin)"),
        ("GET", "/settings", "Settings (admin)"),
        ("GET", "/analytics", "Analytics (admin)"),
        ("GET", "/reports/admin", "Admin reports"),
    ]

    log("\n--- Employee API endpoints ---")
    for item in api_endpoints:
        method, path, label = item[0], item[1], item[2]
        try:
            url = f"{LMS_API}{path}"
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=15)
            else:
                resp = requests.post(url, headers=headers, json=item[3] if len(item) > 3 else {}, timeout=15)

            log(f"  [{method} {path}] Status: {resp.status_code}")
            try:
                data = resp.json()
                log(f"  [{method} {path}] Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                if resp.status_code == 200:
                    record(f"API: {label}", "pass", f"200 OK")
                    # Log some detail
                    if isinstance(data, dict) and "data" in data:
                        inner = data["data"]
                        if isinstance(inner, list):
                            log(f"    Found {len(inner)} items")
                        elif isinstance(inner, dict):
                            log(f"    Data keys: {list(inner.keys())[:10]}")
                elif resp.status_code in (401, 403):
                    record(f"API: {label}", "warn", f"{resp.status_code} - may need different auth")
                elif resp.status_code == 404:
                    record(f"API: {label}", "warn", f"404 - endpoint may not exist")
                else:
                    record(f"API: {label}", "warn", f"Status {resp.status_code}")
            except:
                log(f"  [{method} {path}] Non-JSON response: {resp.text[:200]}")
                record(f"API: {label}", "warn", f"Status {resp.status_code}, non-JSON response")
        except Exception as e:
            record(f"API: {label}", "fail", f"Error: {e}")

    log("\n--- Admin API endpoints (should be restricted for employee) ---")
    for item in admin_api_endpoints:
        method, path, label = item[0], item[1], item[2]
        payload = item[3] if len(item) > 3 else {}
        try:
            url = f"{LMS_API}{path}"
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=15)
            else:
                resp = requests.post(url, headers=headers, json=payload, timeout=15)

            log(f"  [{method} {path}] Status: {resp.status_code}")

            if resp.status_code in (401, 403):
                record(f"Admin API Restriction: {label}", "pass", f"Correctly blocked ({resp.status_code})")
            elif resp.status_code == 404:
                record(f"Admin API Restriction: {label}", "pass", f"Endpoint not found (404)")
            elif resp.status_code == 200:
                try:
                    data = resp.json()
                    log(f"    Response: {json.dumps(data)[:300]}")
                except:
                    pass
                record(f"Admin API Restriction: {label}", "fail", f"Employee got 200 on admin endpoint!")
                file_bug(
                    f"[LMS Employee] Employee can access admin API: {method} {path}",
                    f"**Steps:** Login as employee, call {method} {url}\n\n"
                    f"**Expected:** 401/403 Forbidden.\n\n"
                    f"**Actual:** 200 OK returned.\n\n"
                    f"**Security Impact:** Employee should not access admin APIs."
                )
            else:
                record(f"Admin API Restriction: {label}", "warn", f"Status {resp.status_code}")
        except Exception as e:
            record(f"Admin API Restriction: {label}", "warn", f"Error: {e}")

# ============================
# STEP 5: Try to take a course
# ============================
def test_take_course(driver, token):
    log("\n=== TEST: Can Employee Take a Course? ===")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # First try to find courses via API
    try:
        resp = requests.get(f"{LMS_API}/courses", headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            courses = data.get("data", []) if isinstance(data.get("data"), list) else []
            if not courses and isinstance(data, list):
                courses = data
            log(f"  Found {len(courses)} courses via API")

            if courses:
                course = courses[0]
                course_id = course.get("id") or course.get("_id")
                course_title = course.get("title") or course.get("name") or "Unknown"
                log(f"  First course: {course_title} (ID: {course_id})")

                # Try to enroll / start the course
                for enroll_path in [
                    f"/courses/{course_id}/enroll",
                    f"/courses/{course_id}/start",
                    f"/enrollments",
                ]:
                    try:
                        enroll_url = f"{LMS_API}{enroll_path}"
                        enroll_payload = {"course_id": course_id} if "enrollments" in enroll_path else {}
                        enroll_resp = requests.post(enroll_url, headers=headers, json=enroll_payload, timeout=15)
                        log(f"  Enroll [{enroll_path}]: {enroll_resp.status_code} - {enroll_resp.text[:200]}")
                        if enroll_resp.status_code in (200, 201):
                            record("Enroll in Course", "pass", f"Enrolled in '{course_title}'")
                            break
                    except Exception as e:
                        log(f"  Enroll error: {e}")
                else:
                    record("Enroll in Course", "warn", "Could not find working enroll endpoint")

                # Try navigating to course in browser
                for course_url_pattern in [
                    f"{LMS_BASE}/courses/{course_id}",
                    f"{LMS_BASE}/course/{course_id}",
                    f"{LMS_BASE}/my-courses/{course_id}",
                ]:
                    driver.get(course_url_pattern)
                    time.sleep(3)
                    screenshot(driver, f"04_course_detail")
                    body = driver.find_element(By.TAG_NAME, "body").text[:500]
                    log(f"  Course page [{course_url_pattern}]: {body[:200]}")
                    if "404" not in body.lower() and "not found" not in body.lower():
                        record("View Course Detail", "pass", f"Course page loaded for '{course_title}'")
                        break
                else:
                    record("View Course Detail", "warn", "No course detail page found")
            else:
                record("Course Catalog", "warn", "No courses found in catalog")
        else:
            log(f"  Courses API returned {resp.status_code}: {resp.text[:300]}")
            record("Course Catalog", "warn", f"Courses API returned {resp.status_code}")
    except Exception as e:
        record("Course Access", "fail", f"Error: {e}")

    # Try via browser - navigate to courses page and look for course links
    try:
        driver.get(f"{LMS_BASE}/courses")
        time.sleep(3)
        screenshot(driver, "04_courses_page")

        driver.get(f"{LMS_BASE}/my-courses")
        time.sleep(3)
        screenshot(driver, "04_my_courses_page")

        driver.get(f"{LMS_BASE}/my-learning")
        time.sleep(3)
        screenshot(driver, "04_my_learning_page")
    except Exception as e:
        log(f"  Browser course exploration error: {e}")

# ============================
# STEP 6: Compliance training
# ============================
def test_compliance(driver, token):
    log("\n=== TEST: Compliance Training Status ===")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # API check
    for path in ["/compliance", "/compliance/my", "/my-compliance", "/training/compliance"]:
        try:
            resp = requests.get(f"{LMS_API}{path}", headers=headers, timeout=15)
            log(f"  Compliance [{path}]: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                log(f"  Compliance data: {json.dumps(data)[:400]}")
                record("Compliance API", "pass", f"Endpoint {path} returned data")
                break
        except Exception as e:
            log(f"  Error: {e}")
    else:
        record("Compliance API", "warn", "No compliance endpoint found")

    # Browser check
    for path in ["/compliance", "/my-compliance", "/training/compliance"]:
        try:
            driver.get(f"{LMS_BASE}{path}")
            time.sleep(3)
            screenshot(driver, f"05_compliance")
            body = driver.find_element(By.TAG_NAME, "body").text[:500]
            log(f"  Compliance page [{path}]: {body[:200]}")
            if "404" not in body.lower() and "not found" not in body.lower():
                record("Compliance Page", "pass", f"Accessible at {path}")
                break
        except Exception as e:
            log(f"  Error: {e}")
    else:
        record("Compliance Page", "warn", "No compliance page found")

# ============================
# STEP 7: Create course attempt (should fail)
# ============================
def test_create_course_blocked(token):
    log("\n=== TEST: Employee Cannot Create Course ===")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    course_data = {
        "title": "SECURITY TEST - Employee Created Course",
        "description": "This should not be allowed",
        "category": "test",
        "type": "online"
    }

    for path in ["/courses", "/courses/create", "/admin/courses"]:
        try:
            resp = requests.post(f"{LMS_API}{path}", headers=headers, json=course_data, timeout=15)
            log(f"  POST {path}: {resp.status_code} - {resp.text[:200]}")
            if resp.status_code in (200, 201):
                record(f"Create Course Block ({path})", "fail", "Employee could create a course!")
                file_bug(
                    f"[LMS Employee] Employee can create courses via POST {path}",
                    f"**Steps:** Login as employee, POST to {LMS_API}{path} with course data.\n\n"
                    f"**Expected:** 401/403.\n\n"
                    f"**Actual:** {resp.status_code} - Course creation succeeded.\n\n"
                    f"**Security Impact:** Critical - employees should not create courses."
                )
            else:
                record(f"Create Course Block ({path})", "pass", f"Correctly blocked ({resp.status_code})")
        except Exception as e:
            record(f"Create Course Block ({path})", "warn", f"Error: {e}")

# ============================
# MAIN
# ============================
def main():
    log("=" * 70)
    log("LMS MODULE - EMPLOYEE PERSPECTIVE TEST")
    log(f"User: {EMAIL}")
    log("=" * 70)

    # Step 1: Get SSO token
    token, login_data = get_sso_token()
    if not token:
        record("Login", "fail", "Could not get SSO token")
        file_bug(
            "[LMS Employee] Cannot login as employee to get SSO token",
            f"**Steps:** POST to {LOGIN_URL} with employee credentials.\n\n"
            f"**Expected:** Token returned.\n\n"
            f"**Actual:** Login failed.\n\n"
            f"**Response:** {json.dumps(login_data)[:500] if login_data else 'None'}"
        )
        print_summary()
        return

    record("Login", "pass", "Got SSO token")

    # Step 2: SSO into LMS via browser
    driver = create_driver()
    try:
        sso_ok = test_sso_login(driver, token)

        if not sso_ok:
            log("\nSSO failed - attempting direct URL navigation with token injection...")
            # Even if SSO landing failed, try navigating pages (cookie/token may still work)
            # Also try setting token in localStorage
            try:
                driver.get(LMS_BASE)
                time.sleep(2)
                driver.execute_script(f"""
                    localStorage.setItem('token', '{token}');
                    localStorage.setItem('access_token', '{token}');
                    localStorage.setItem('auth_token', '{token}');
                """)
                driver.get(LMS_BASE)
                time.sleep(3)
                screenshot(driver, "01b_after_token_inject")
                body = driver.find_element(By.TAG_NAME, "body").text[:500]
                log(f"  After token injection: {body[:200]}")
            except Exception as e:
                log(f"  Token injection failed: {e}")

        # Step 3: Explore pages
        accessible = test_lms_pages(driver, token)

        # Step 4: API tests
        test_lms_api(token)

        # Step 5: Try to take a course
        test_take_course(driver, token)

        # Step 6: Compliance training
        test_compliance(driver, token)

        # Step 7: Create course attempt
        test_create_course_blocked(token)

        # Final screenshot of whatever state we're in
        screenshot(driver, "99_final_state")

    except Exception as e:
        log(f"FATAL ERROR: {e}")
        try:
            screenshot(driver, "99_fatal_error")
        except:
            pass
    finally:
        driver.quit()

    print_summary()

def print_summary():
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)

    pass_count = sum(1 for r in test_results if r["status"] == "pass")
    fail_count = sum(1 for r in test_results if r["status"] == "fail")
    warn_count = sum(1 for r in test_results if r["status"] == "warn")

    for r in test_results:
        icon = "PASS" if r["status"] == "pass" else "FAIL" if r["status"] == "fail" else "WARN"
        log(f"  [{icon}] {r['test']}: {r['details']}")

    log(f"\nTotals: {pass_count} passed, {fail_count} failed, {warn_count} warnings")
    log(f"Bugs filed: {len(bugs)}")
    for b in bugs:
        log(f"  - {b}")
    log(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
    log("=" * 70)

if __name__ == "__main__":
    main()
