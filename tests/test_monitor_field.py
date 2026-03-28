"""
E2E Tests: Employee Monitoring, Field Force Management, and Biometrics
EMP Cloud HRMS - Cross-module testing with RBAC and API validation
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import traceback
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# =============================================================================
# CONFIG
# =============================================================================
MONITOR_URL = "https://test-empmonitor.empcloud.com"
FIELD_URL = "https://test-field.empcloud.com"
MAIN_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud.empcloud.com/api/v1"

CREDS = {
    "org_admin": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "employee": {"email": "priya@technova.in", "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"},
}

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\monitor_field"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# =============================================================================
# HELPERS
# =============================================================================
bugs_found = []
test_results = []

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-web-security")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def screenshot(driver, name):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{name}_{ts}.png"
    path = os.path.join(SCREENSHOT_DIR, fname)
    driver.save_screenshot(path)
    print(f"  [SCREENSHOT] {path}")
    return path


def record(name, status, details=""):
    test_results.append({"test": name, "status": status, "details": details})
    icon = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "INFO")
    print(f"  [{icon}] {name}: {details}")


def file_github_issue(title, body, severity, screenshot_path=None):
    """File a GitHub issue for a bug."""
    labels = ["bug", f"severity:{severity}"]
    if "monitor" in title.lower():
        labels.append("module:monitoring")
    if "field" in title.lower():
        labels.append("module:field-force")
    if "biometric" in title.lower():
        labels.append("module:biometrics")
    if "api" in title.lower() or "rbac" in title.lower():
        labels.append("security")

    full_body = f"{body}\n\n**Severity:** {severity}\n**Date:** {datetime.now().isoformat()}\n"
    if screenshot_path:
        full_body += f"\n**Screenshot:** `{screenshot_path}`\n"

    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {"title": title, "body": full_body, "labels": labels}

    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers=headers, json=payload, timeout=15
        )
        if resp.status_code == 201:
            url = resp.json().get("html_url", "")
            print(f"  [GITHUB] Issue created: {url}")
            return url
        else:
            print(f"  [GITHUB] Failed ({resp.status_code}): {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"  [GITHUB] Error filing issue: {e}")
        return None


def log_bug(driver, title, body, severity):
    spath = screenshot(driver, title.replace(" ", "_").replace("/","_")[:60])
    bugs_found.append({
        "title": title, "body": body, "severity": severity, "screenshot": spath
    })
    issue_url = file_github_issue(title, body, severity, spath)
    return spath, issue_url


def wait_find(driver, by, value, timeout=12):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))


def wait_clickable(driver, by, value, timeout=12):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))


def safe_click(driver, by, value, timeout=10):
    el = wait_clickable(driver, by, value, timeout)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.3)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)
    return el


def check_page_loads(driver, url, label, timeout=15):
    """Navigate to URL and check if it loads (not error page)."""
    driver.get(url)
    time.sleep(2)
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    page_src = driver.page_source.lower()
    title = driver.title
    current = driver.current_url

    # Check for common error indicators
    error_indicators = [
        "502 bad gateway", "503 service unavailable", "404 not found",
        "500 internal server", "application error", "this site can",
        "err_connection", "page not found", "server error"
    ]
    for err in error_indicators:
        if err in page_src:
            return False, f"Error page detected: '{err}' at {current} (title: {title})"

    return True, f"Page loaded: {current} (title: {title})"


def attempt_login(driver, url, email, password, role_label):
    """Try to login at a given URL. Returns (success, details)."""
    driver.get(url)
    time.sleep(2)

    # Check if page loads at all
    page_src = driver.page_source.lower()
    current = driver.current_url

    # If redirected to main login or shows login form
    login_selectors = [
        (By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[id='email']"),
        (By.CSS_SELECTOR, "input[type='text'][placeholder*='email' i], input[type='text'][placeholder*='user' i]"),
        (By.XPATH, "//input[contains(@placeholder,'mail') or contains(@placeholder,'user') or contains(@name,'login')]"),
    ]

    email_field = None
    for by, sel in login_selectors:
        try:
            email_field = WebDriverWait(driver, 8).until(EC.presence_of_element_located((by, sel)))
            break
        except TimeoutException:
            continue

    if not email_field:
        # Maybe there's a login button/link to click first
        try:
            login_btns = driver.find_elements(By.XPATH,
                "//a[contains(text(),'Login') or contains(text(),'Sign In')] | "
                "//button[contains(text(),'Login') or contains(text(),'Sign In')]"
            )
            if login_btns:
                login_btns[0].click()
                time.sleep(2)
                for by, sel in login_selectors:
                    try:
                        email_field = WebDriverWait(driver, 5).until(EC.presence_of_element_located((by, sel)))
                        break
                    except TimeoutException:
                        continue
        except Exception:
            pass

    if not email_field:
        return False, f"No login form found at {current} (title: {driver.title})"

    email_field.clear()
    email_field.send_keys(email)
    time.sleep(0.3)

    # Find password field
    pw_selectors = [
        (By.CSS_SELECTOR, "input[type='password']"),
        (By.CSS_SELECTOR, "input[name='password']"),
    ]
    pw_field = None
    for by, sel in pw_selectors:
        try:
            pw_field = driver.find_element(by, sel)
            break
        except NoSuchElementException:
            continue

    if not pw_field:
        return False, "Password field not found"

    pw_field.clear()
    pw_field.send_keys(password)
    time.sleep(0.3)

    # Click submit
    submit_selectors = [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button[contains(text(),'Login') or contains(text(),'Sign In') or contains(text(),'Submit')]"),
        (By.CSS_SELECTOR, "input[type='submit']"),
    ]
    submitted = False
    for by, sel in submit_selectors:
        try:
            btn = driver.find_element(by, sel)
            driver.execute_script("arguments[0].click();", btn)
            submitted = True
            break
        except NoSuchElementException:
            continue

    if not submitted:
        from selenium.webdriver.common.keys import Keys
        pw_field.send_keys(Keys.RETURN)

    time.sleep(3)

    # Check for login errors
    page_src = driver.page_source.lower()
    error_texts = ["invalid credentials", "incorrect password", "login failed",
                   "account not found", "invalid email", "unauthorized"]
    for et in error_texts:
        if et in page_src:
            return False, f"Login rejected: '{et}' found on page"

    # Check if still on login page
    new_url = driver.current_url
    return True, f"Login attempted. Now at: {new_url} (title: {driver.title})"


def find_elements_with_text(driver, texts, tag="*"):
    """Find elements containing any of the given texts."""
    found = []
    for text in texts:
        try:
            els = driver.find_elements(By.XPATH, f"//{tag}[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{text.lower()}')]")
            found.extend(els)
        except Exception:
            pass
    return found


def check_dashboard_elements(driver, expected_sections, module_name):
    """Check for expected dashboard sections/widgets."""
    page_src = driver.page_source.lower()
    found_sections = []
    missing_sections = []
    for section in expected_sections:
        if section.lower() in page_src:
            found_sections.append(section)
        else:
            missing_sections.append(section)
    return found_sections, missing_sections


# =============================================================================
# MODULE 1: EMPLOYEE MONITORING
# =============================================================================
def test_monitoring_module():
    print("\n" + "="*70)
    print("MODULE 1: EMPLOYEE MONITORING")
    print("="*70)
    driver = get_driver()

    try:
        # 1.1 Check if monitoring site loads
        print("\n--- 1.1 Monitoring Site Accessibility ---")
        loaded, detail = check_page_loads(driver, MONITOR_URL, "Monitor Home")
        screenshot(driver, "monitor_home")
        if not loaded:
            record("Monitor Site Load", "FAIL", detail)
            log_bug(driver, "[Monitor] Site not accessible",
                    f"The monitoring module at {MONITOR_URL} is not loading properly.\n\n{detail}",
                    "critical")
        else:
            record("Monitor Site Load", "PASS", detail)

        # 1.2 Login as Org Admin
        print("\n--- 1.2 Org Admin Login to Monitor ---")
        creds = CREDS["org_admin"]
        success, detail = attempt_login(driver, MONITOR_URL, creds["email"], creds["password"], "Org Admin")
        screenshot(driver, "monitor_admin_login")
        if success:
            record("Monitor Org Admin Login", "PASS", detail)
        else:
            record("Monitor Org Admin Login", "FAIL", detail)
            log_bug(driver, "[Monitor] Org Admin login failed",
                    f"Cannot login to monitoring module as Org Admin.\n\nEmail: {creds['email']}\n{detail}",
                    "critical")
            # Try login via main app then navigate
            print("  Trying login via main app...")
            success2, detail2 = attempt_login(driver, MAIN_URL, creds["email"], creds["password"], "Org Admin (Main)")
            screenshot(driver, "monitor_admin_login_via_main")
            record("Monitor Login via Main App", "PASS" if success2 else "FAIL", detail2)
            if success2:
                driver.get(MONITOR_URL)
                time.sleep(3)
                screenshot(driver, "monitor_after_main_login")

        # 1.3 Check monitoring dashboard sections
        print("\n--- 1.3 Monitoring Dashboard ---")
        monitoring_sections = [
            "dashboard", "activity", "screenshot", "app usage", "productivity",
            "tracking", "monitor", "report", "time track", "idle", "active",
            "attendance", "timeline", "usage"
        ]
        found, missing = check_dashboard_elements(driver, monitoring_sections, "Monitoring")
        screenshot(driver, "monitor_dashboard")
        if found:
            record("Monitor Dashboard Sections", "PASS", f"Found: {', '.join(found)}")
        else:
            record("Monitor Dashboard Sections", "FAIL", "No expected monitoring sections found")
            log_bug(driver, "[Monitor] Dashboard sections missing",
                    f"Monitoring dashboard at {driver.current_url} does not show expected sections.\n\n"
                    f"Expected: {', '.join(monitoring_sections[:6])}\nPage title: {driver.title}",
                    "high")

        # 1.4 Check specific monitoring pages
        print("\n--- 1.4 Monitoring Sub-pages ---")
        monitor_paths = [
            "/dashboard", "/activity", "/screenshots", "/apps", "/app-usage",
            "/productivity", "/reports", "/tracking", "/timeline", "/employees",
            "/settings", "/time-tracking", "/idle-time"
        ]
        accessible_pages = []
        for path in monitor_paths:
            full_url = MONITOR_URL + path
            driver.get(full_url)
            time.sleep(1.5)
            page_src = driver.page_source.lower()
            cur_url = driver.current_url
            has_error = any(e in page_src for e in ["404", "not found", "error", "cannot get"])
            if not has_error and len(page_src) > 500:
                accessible_pages.append(path)
                screenshot(driver, f"monitor_page_{path.strip('/').replace('/','_')}")

        record("Monitor Accessible Pages", "INFO",
               f"Found {len(accessible_pages)} pages: {', '.join(accessible_pages) if accessible_pages else 'None'}")

        # 1.5 Check activity tracking
        print("\n--- 1.5 Activity Tracking ---")
        activity_urls = [MONITOR_URL + p for p in ["/activity", "/dashboard", "/tracking", "/"]]
        activity_found = False
        for aurl in activity_urls:
            driver.get(aurl)
            time.sleep(2)
            page_src = driver.page_source.lower()
            if any(kw in page_src for kw in ["active time", "idle time", "activity", "mouse", "keyboard", "screenshot"]):
                activity_found = True
                screenshot(driver, "monitor_activity_tracking")
                record("Activity Tracking", "PASS", f"Activity tracking elements found at {aurl}")
                break
        if not activity_found:
            record("Activity Tracking", "FAIL", "No activity tracking features found")
            log_bug(driver, "[Monitor] Activity tracking not visible",
                    "Cannot find activity tracking features (active/idle time, screenshots, etc.) on monitoring dashboard.",
                    "high")

        # 1.6 Check productivity reports
        print("\n--- 1.6 Productivity Reports ---")
        report_urls = [MONITOR_URL + p for p in ["/reports", "/productivity", "/analytics", "/report"]]
        report_found = False
        for rurl in report_urls:
            driver.get(rurl)
            time.sleep(2)
            page_src = driver.page_source.lower()
            if any(kw in page_src for kw in ["productivity", "report", "analytics", "chart", "graph", "performance"]):
                report_found = True
                screenshot(driver, "monitor_productivity_reports")
                record("Productivity Reports", "PASS", f"Reports found at {rurl}")
                break
        if not report_found:
            record("Productivity Reports", "FAIL", "No productivity reports found")
            log_bug(driver, "[Monitor] Productivity reports missing",
                    "Cannot find productivity reports section in monitoring module.",
                    "medium")

        # 1.7 Login as Employee
        print("\n--- 1.7 Employee Login to Monitor ---")
        driver.delete_all_cookies()
        emp_creds = CREDS["employee"]
        success, detail = attempt_login(driver, MONITOR_URL, emp_creds["email"], emp_creds["password"], "Employee")
        screenshot(driver, "monitor_employee_login")
        if success:
            record("Monitor Employee Login", "PASS", detail)
        else:
            record("Monitor Employee Login", "FAIL", detail)
            # Try via main app
            success2, detail2 = attempt_login(driver, MAIN_URL, emp_creds["email"], emp_creds["password"], "Employee (Main)")
            if success2:
                driver.get(MONITOR_URL)
                time.sleep(3)
            screenshot(driver, "monitor_employee_after_login")

        # 1.8 RBAC - Check what employee can see
        print("\n--- 1.8 RBAC: Employee View in Monitor ---")
        page_src = driver.page_source.lower()
        employee_visible = []
        if "screenshot" in page_src:
            employee_visible.append("screenshots")
        if "other" in page_src or "all employee" in page_src or "team" in page_src:
            employee_visible.append("other_employees_data")
        if any(kw in page_src for kw in ["admin", "settings", "configuration", "manage"]):
            employee_visible.append("admin_features")

        screenshot(driver, "monitor_employee_view")
        record("Employee Monitor View", "INFO", f"Employee can see: {', '.join(employee_visible) if employee_visible else 'Limited/Own data only'}")

        # 1.9 RBAC - Can employee see others' monitoring data?
        print("\n--- 1.9 RBAC: Employee Access to Others' Data ---")
        rbac_violation = False
        # Try accessing monitoring data for other employees
        test_urls = [
            MONITOR_URL + "/employees",
            MONITOR_URL + "/all-activity",
            MONITOR_URL + "/team",
            MONITOR_URL + "/admin",
            MONITOR_URL + "/settings",
        ]
        for turl in test_urls:
            driver.get(turl)
            time.sleep(1.5)
            psrc = driver.page_source.lower()
            # Check if employee can see other employees' data
            if any(kw in psrc for kw in ["ananya", "all employees", "employee list", "team activity"]):
                rbac_violation = True
                screenshot(driver, f"monitor_rbac_violation_{turl.split('/')[-1]}")
                record("RBAC Violation", "FAIL", f"Employee can see other employees' data at {turl}")
                log_bug(driver, "[Monitor][RBAC] Employee can access others' monitoring data",
                        f"Employee ({emp_creds['email']}) can view other employees' monitoring data at {turl}.\n\n"
                        "This is a privacy/security violation. Employees should only see their own data.",
                        "critical")

        if not rbac_violation:
            record("RBAC Monitor Check", "PASS", "Employee cannot access others' monitoring data")

    except Exception as e:
        screenshot(driver, "monitor_error")
        record("Monitor Module Error", "FAIL", f"Exception: {str(e)}")
        traceback.print_exc()
    finally:
        driver.quit()


# =============================================================================
# MODULE 2: FIELD FORCE MANAGEMENT
# =============================================================================
def test_field_force_module():
    print("\n" + "="*70)
    print("MODULE 2: FIELD FORCE MANAGEMENT")
    print("="*70)
    driver = get_driver()

    try:
        # 2.1 Check if field force site loads
        print("\n--- 2.1 Field Force Site Accessibility ---")
        loaded, detail = check_page_loads(driver, FIELD_URL, "Field Force Home")
        screenshot(driver, "field_home")
        if not loaded:
            record("Field Force Site Load", "FAIL", detail)
            log_bug(driver, "[Field Force] Site not accessible",
                    f"The field force module at {FIELD_URL} is not loading properly.\n\n{detail}",
                    "critical")
        else:
            record("Field Force Site Load", "PASS", detail)

        # 2.2 Login as Org Admin
        print("\n--- 2.2 Org Admin Login to Field Force ---")
        creds = CREDS["org_admin"]
        success, detail = attempt_login(driver, FIELD_URL, creds["email"], creds["password"], "Org Admin")
        screenshot(driver, "field_admin_login")
        if success:
            record("Field Admin Login", "PASS", detail)
        else:
            record("Field Admin Login", "FAIL", detail)
            log_bug(driver, "[Field Force] Org Admin login failed",
                    f"Cannot login to field force module as Org Admin.\n\nEmail: {creds['email']}\n{detail}",
                    "critical")
            # Try via main app
            print("  Trying login via main app...")
            success2, detail2 = attempt_login(driver, MAIN_URL, creds["email"], creds["password"], "Org Admin (Main)")
            screenshot(driver, "field_admin_login_via_main")
            if success2:
                driver.get(FIELD_URL)
                time.sleep(3)
                screenshot(driver, "field_after_main_login")

        # 2.3 Check field force dashboard
        print("\n--- 2.3 Field Force Dashboard ---")
        ff_sections = [
            "dashboard", "field", "force", "employee", "track", "gps",
            "location", "route", "check-in", "check-out", "visit",
            "attendance", "task", "map", "geofence"
        ]
        found, missing = check_dashboard_elements(driver, ff_sections, "Field Force")
        screenshot(driver, "field_dashboard")
        if found:
            record("Field Dashboard Sections", "PASS", f"Found: {', '.join(found)}")
        else:
            record("Field Dashboard Sections", "FAIL", "No expected field force sections found")
            log_bug(driver, "[Field Force] Dashboard sections missing",
                    f"Field force dashboard at {driver.current_url} does not show expected sections.\n\n"
                    f"Expected: {', '.join(ff_sections[:6])}\nPage title: {driver.title}",
                    "high")

        # 2.4 Check field force sub-pages
        print("\n--- 2.4 Field Force Sub-pages ---")
        ff_paths = [
            "/dashboard", "/tracking", "/gps", "/location", "/routes",
            "/route-optimization", "/check-in", "/checkin", "/visits",
            "/tasks", "/employees", "/geofence", "/map", "/reports",
            "/settings", "/attendance", "/field-employees"
        ]
        accessible_pages = []
        for path in ff_paths:
            full_url = FIELD_URL + path
            driver.get(full_url)
            time.sleep(1.5)
            page_src = driver.page_source.lower()
            has_error = any(e in page_src for e in ["404", "not found", "cannot get"])
            if not has_error and len(page_src) > 500:
                accessible_pages.append(path)
                screenshot(driver, f"field_page_{path.strip('/').replace('/','_')}")

        record("Field Accessible Pages", "INFO",
               f"Found {len(accessible_pages)} pages: {', '.join(accessible_pages) if accessible_pages else 'None'}")

        # 2.5 GPS Tracking Features
        print("\n--- 2.5 GPS Tracking ---")
        gps_urls = [FIELD_URL + p for p in ["/tracking", "/gps", "/location", "/map", "/dashboard"]]
        gps_found = False
        for gurl in gps_urls:
            driver.get(gurl)
            time.sleep(2)
            page_src = driver.page_source.lower()
            if any(kw in page_src for kw in ["gps", "location", "map", "latitude", "longitude", "track", "geofence"]):
                gps_found = True
                screenshot(driver, "field_gps_tracking")
                record("GPS Tracking", "PASS", f"GPS tracking features found at {gurl}")
                break
        if not gps_found:
            record("GPS Tracking", "FAIL", "No GPS tracking features found")
            log_bug(driver, "[Field Force] GPS tracking not available",
                    "Cannot find GPS tracking features in field force module.",
                    "high")

        # 2.6 Route Optimization
        print("\n--- 2.6 Route Optimization ---")
        route_urls = [FIELD_URL + p for p in ["/routes", "/route-optimization", "/route", "/plan"]]
        route_found = False
        for rurl in route_urls:
            driver.get(rurl)
            time.sleep(2)
            page_src = driver.page_source.lower()
            if any(kw in page_src for kw in ["route", "optimization", "path", "direction", "waypoint", "plan"]):
                route_found = True
                screenshot(driver, "field_route_optimization")
                record("Route Optimization", "PASS", f"Route features found at {rurl}")
                break
        if not route_found:
            record("Route Optimization", "FAIL", "No route optimization features found")
            log_bug(driver, "[Field Force] Route optimization missing",
                    "Cannot find route optimization features in field force module.",
                    "medium")

        # 2.7 Check-in/Check-out
        print("\n--- 2.7 Check-in/Check-out ---")
        checkin_urls = [FIELD_URL + p for p in ["/check-in", "/checkin", "/check-out", "/attendance", "/visits", "/dashboard"]]
        checkin_found = False
        for curl in checkin_urls:
            driver.get(curl)
            time.sleep(2)
            page_src = driver.page_source.lower()
            if any(kw in page_src for kw in ["check-in", "check in", "check-out", "check out", "checkin", "checkout", "punch"]):
                checkin_found = True
                screenshot(driver, "field_checkin_checkout")
                record("Check-in/Check-out", "PASS", f"Check-in/out features found at {curl}")
                break
        if not checkin_found:
            record("Check-in/Check-out", "FAIL", "No check-in/check-out features found")
            log_bug(driver, "[Field Force] Check-in/Check-out missing",
                    "Cannot find check-in/check-out features for field employees.",
                    "high")

    except Exception as e:
        screenshot(driver, "field_error")
        record("Field Force Module Error", "FAIL", f"Exception: {str(e)}")
        traceback.print_exc()
    finally:
        driver.quit()


# =============================================================================
# MODULE 3: BIOMETRICS
# =============================================================================
def test_biometrics_module():
    print("\n" + "="*70)
    print("MODULE 3: BIOMETRICS")
    print("="*70)
    driver = get_driver()

    try:
        # 3.1 Login to main app
        print("\n--- 3.1 Login to Main App ---")
        creds = CREDS["org_admin"]
        success, detail = attempt_login(driver, MAIN_URL, creds["email"], creds["password"], "Org Admin")
        screenshot(driver, "biometric_main_login")
        if success:
            record("Biometric Main Login", "PASS", detail)
        else:
            record("Biometric Main Login", "FAIL", detail)
            log_bug(driver, "[Biometrics] Cannot login to main app",
                    f"Cannot login to main app to access biometrics.\n{detail}",
                    "critical")

        # 3.2 Navigate to biometric pages
        print("\n--- 3.2 Biometric Pages ---")
        bio_paths = [
            "/biometrics", "/biometric", "/biometric-devices", "/devices",
            "/face-enrollment", "/face-recognition", "/biometric-logs",
            "/biometric-settings", "/fingerprint", "/attendance/biometric",
            "/hr/biometrics", "/admin/biometrics", "/settings/biometrics",
            "/biometric/devices", "/biometric/logs", "/biometric/enrollment"
        ]
        accessible_bio = []
        for path in bio_paths:
            full_url = MAIN_URL + path
            driver.get(full_url)
            time.sleep(1.5)
            page_src = driver.page_source.lower()
            cur_url = driver.current_url
            # Not a 404 or error, and has meaningful content
            has_error = any(e in page_src for e in ["404", "not found", "cannot get"])
            if not has_error and len(page_src) > 500:
                accessible_bio.append(path)
                screenshot(driver, f"biometric_page_{path.strip('/').replace('/','_')}")

        record("Biometric Pages Found", "INFO",
               f"Found {len(accessible_bio)} pages: {', '.join(accessible_bio) if accessible_bio else 'None'}")

        # 3.3 Look for biometric links in navigation
        print("\n--- 3.3 Biometric Navigation Links ---")
        driver.get(MAIN_URL + "/dashboard")
        time.sleep(3)
        page_src = driver.page_source.lower()

        bio_keywords = ["biometric", "face", "fingerprint", "device management", "enrollment", "biolog"]
        bio_nav_found = []
        for kw in bio_keywords:
            if kw in page_src:
                bio_nav_found.append(kw)

        screenshot(driver, "biometric_nav_check")
        if bio_nav_found:
            record("Biometric Navigation", "PASS", f"Found references: {', '.join(bio_nav_found)}")
        else:
            record("Biometric Navigation", "FAIL", "No biometric references found in navigation")
            log_bug(driver, "[Biometrics] No biometric section found in main app",
                    "Cannot find biometric management section in the main application navigation or by direct URL access.\n\n"
                    f"Tried paths: {', '.join(bio_paths[:6])}",
                    "medium")

        # 3.4 Search for biometric links via sidebar/menu
        print("\n--- 3.4 Sidebar/Menu Biometric Links ---")
        try:
            # Click on sidebar menu items that might contain biometric
            sidebar_items = driver.find_elements(By.CSS_SELECTOR,
                "nav a, .sidebar a, .menu a, .nav-link, [class*='sidebar'] a, [class*='menu'] a")
            bio_links = []
            for item in sidebar_items:
                text = item.text.strip().lower()
                href = item.get_attribute("href") or ""
                if any(kw in text or kw in href.lower() for kw in ["biometric", "device", "face", "attendance"]):
                    bio_links.append({"text": text, "href": href})

            if bio_links:
                record("Biometric Sidebar Links", "PASS",
                       f"Found {len(bio_links)} links: {', '.join(l['text'] for l in bio_links[:5])}")
                # Click first biometric link
                for bl in bio_links:
                    if "biometric" in bl["text"] or "biometric" in bl["href"]:
                        driver.get(bl["href"])
                        time.sleep(2)
                        screenshot(driver, "biometric_page_from_nav")
                        break
            else:
                record("Biometric Sidebar Links", "INFO", "No biometric links found in sidebar")
        except Exception as e:
            record("Biometric Sidebar Search", "INFO", f"Sidebar search: {str(e)}")

        # 3.5 Device Management
        print("\n--- 3.5 Device Management ---")
        device_paths = ["/devices", "/biometric-devices", "/biometric/devices",
                        "/settings/devices", "/admin/devices", "/device-management"]
        device_found = False
        for dp in device_paths:
            driver.get(MAIN_URL + dp)
            time.sleep(1.5)
            psrc = driver.page_source.lower()
            if any(kw in psrc for kw in ["device", "biometric device", "add device", "register"]):
                device_found = True
                screenshot(driver, "biometric_device_management")
                record("Device Management", "PASS", f"Device management found at {dp}")
                break
        if not device_found:
            record("Device Management", "FAIL", "Device management page not found")

        # 3.6 Face Enrollment
        print("\n--- 3.6 Face Enrollment ---")
        face_paths = ["/face-enrollment", "/face-recognition", "/enrollment",
                      "/biometric/enrollment", "/biometric/face"]
        face_found = False
        for fp in face_paths:
            driver.get(MAIN_URL + fp)
            time.sleep(1.5)
            psrc = driver.page_source.lower()
            if any(kw in psrc for kw in ["face", "enrollment", "enroll", "recognition", "camera", "photo"]):
                face_found = True
                screenshot(driver, "biometric_face_enrollment")
                record("Face Enrollment", "PASS", f"Face enrollment found at {fp}")
                break
        if not face_found:
            record("Face Enrollment", "FAIL", "Face enrollment page not found")

        # 3.7 Biometric Logs
        print("\n--- 3.7 Biometric Logs ---")
        log_paths = ["/biometric-logs", "/biometric/logs", "/attendance/logs",
                     "/logs", "/biometric-attendance"]
        log_found = False
        for lp in log_paths:
            driver.get(MAIN_URL + lp)
            time.sleep(1.5)
            psrc = driver.page_source.lower()
            if any(kw in psrc for kw in ["log", "biometric", "punch", "attendance", "timestamp", "entry"]):
                log_found = True
                screenshot(driver, "biometric_logs")
                record("Biometric Logs", "PASS", f"Biometric logs found at {lp}")
                break
        if not log_found:
            record("Biometric Logs", "FAIL", "Biometric logs page not found")

    except Exception as e:
        screenshot(driver, "biometric_error")
        record("Biometrics Module Error", "FAIL", f"Exception: {str(e)}")
        traceback.print_exc()
    finally:
        driver.quit()


# =============================================================================
# MODULE 4: CROSS-MODULE API TESTS
# =============================================================================
def test_cross_module_api():
    print("\n" + "="*70)
    print("MODULE 4: CROSS-MODULE API TESTS")
    print("="*70)
    driver = None

    try:
        # 4.1 Get auth tokens for different roles
        print("\n--- 4.1 Obtain Auth Tokens ---")
        tokens = {}
        for role, cred in CREDS.items():
            login_endpoints = [
                f"{API_URL}/auth/login",
                f"{API_URL}/login",
                f"{API_URL}/auth/signin",
                f"{API_URL}/users/login",
                f"{MAIN_URL}/api/auth/login",
                f"{MAIN_URL}/api/v1/auth/login",
            ]
            for ep in login_endpoints:
                try:
                    resp = requests.post(ep, json={
                        "email": cred["email"],
                        "password": cred["password"]
                    }, timeout=10, verify=False)
                    if resp.status_code == 200:
                        data = resp.json()
                        token = (data.get("token") or data.get("access_token") or
                                 data.get("data", {}).get("token") or
                                 data.get("data", {}).get("access_token") or
                                 data.get("result", {}).get("token") or "")
                        if token:
                            tokens[role] = token
                            record(f"API Token {role}", "PASS", f"Token obtained via {ep}")
                            break
                        else:
                            # Check cookies
                            cookies = resp.cookies.get_dict()
                            if cookies:
                                tokens[role] = f"cookie:{json.dumps(cookies)}"
                                record(f"API Token {role}", "PASS", f"Cookie auth via {ep}")
                                break
                    elif resp.status_code in [401, 403]:
                        record(f"API Token {role} at {ep}", "INFO", f"Auth rejected: {resp.status_code}")
                except requests.exceptions.ConnectionError:
                    continue
                except Exception as e:
                    continue

            if role not in tokens:
                record(f"API Token {role}", "FAIL", f"Could not obtain token for {role}")

        # 4.2 Test monitoring API endpoints
        print("\n--- 4.2 Monitoring API Endpoints ---")
        monitor_apis = [
            "/monitoring/dashboard", "/monitoring/activities", "/monitoring/screenshots",
            "/monitoring/app-usage", "/monitoring/productivity", "/monitoring/reports",
            "/employees/monitoring", "/monitor/activity", "/monitor/screenshots",
            "/employee-monitoring", "/tracking/activity"
        ]

        admin_token = tokens.get("org_admin", "")
        headers_admin = {"Authorization": f"Bearer {admin_token}"} if admin_token and not admin_token.startswith("cookie:") else {}

        api_results = {"accessible": [], "forbidden": [], "not_found": [], "error": []}
        for ep in monitor_apis:
            for base in [API_URL, MAIN_URL + "/api/v1", MAIN_URL + "/api"]:
                full = base + ep
                try:
                    r = requests.get(full, headers=headers_admin, timeout=8, verify=False)
                    if r.status_code == 200:
                        api_results["accessible"].append(f"{ep} ({base})")
                        record(f"Monitor API {ep}", "PASS", f"Accessible: {r.status_code}")
                        break
                    elif r.status_code in [401, 403]:
                        api_results["forbidden"].append(ep)
                    elif r.status_code == 404:
                        api_results["not_found"].append(ep)
                    else:
                        api_results["error"].append(f"{ep}: {r.status_code}")
                except Exception:
                    continue

        record("Monitor APIs Summary", "INFO",
               f"Accessible: {len(api_results['accessible'])}, "
               f"Forbidden: {len(api_results['forbidden'])}, "
               f"Not Found: {len(api_results['not_found'])}")

        # 4.3 Test field force API endpoints
        print("\n--- 4.3 Field Force API Endpoints ---")
        field_apis = [
            "/field/dashboard", "/field/tracking", "/field/gps",
            "/field/routes", "/field/check-in", "/field/visits",
            "/field-force/employees", "/field-force/tracking",
            "/gps/tracking", "/location/employees"
        ]
        for ep in field_apis:
            for base in [API_URL, MAIN_URL + "/api/v1", FIELD_URL + "/api"]:
                full = base + ep
                try:
                    r = requests.get(full, headers=headers_admin, timeout=8, verify=False)
                    if r.status_code == 200:
                        record(f"Field API {ep}", "PASS", f"Accessible: {r.status_code}")
                        break
                    elif r.status_code in [401, 403]:
                        record(f"Field API {ep}", "INFO", f"Auth required: {r.status_code}")
                        break
                except Exception:
                    continue

        # 4.4 Test biometric API endpoints
        print("\n--- 4.4 Biometric API Endpoints ---")
        bio_apis = [
            "/biometric/devices", "/biometric/logs", "/biometric/enrollment",
            "/biometrics", "/biometric/attendance", "/biometric/settings",
            "/attendance/biometric", "/devices/biometric"
        ]
        for ep in bio_apis:
            for base in [API_URL, MAIN_URL + "/api/v1"]:
                full = base + ep
                try:
                    r = requests.get(full, headers=headers_admin, timeout=8, verify=False)
                    if r.status_code == 200:
                        record(f"Bio API {ep}", "PASS", f"Accessible: {r.status_code}")
                        break
                    elif r.status_code in [401, 403]:
                        record(f"Bio API {ep}", "INFO", f"Auth required: {r.status_code}")
                        break
                except Exception:
                    continue

        # 4.5 RBAC: Employee token accessing admin-only monitoring data
        print("\n--- 4.5 RBAC: Employee Access to Admin-only APIs ---")
        emp_token = tokens.get("employee", "")
        headers_emp = {"Authorization": f"Bearer {emp_token}"} if emp_token and not emp_token.startswith("cookie:") else {}

        admin_only_endpoints = [
            "/monitoring/all-employees", "/monitoring/screenshots/all",
            "/employees/monitoring", "/admin/monitoring",
            "/field/all-employees", "/admin/dashboard",
            "/biometric/devices/manage", "/settings/monitoring",
            "/reports/all-employees", "/monitoring/employee/",
        ]

        rbac_violations = []
        for ep in admin_only_endpoints:
            for base in [API_URL, MAIN_URL + "/api/v1"]:
                full = base + ep
                try:
                    r = requests.get(full, headers=headers_emp, timeout=8, verify=False)
                    if r.status_code == 200:
                        # Employee got 200 on admin endpoint - potential violation
                        try:
                            data = r.json()
                            if isinstance(data, dict) and (data.get("data") or data.get("employees") or data.get("results")):
                                rbac_violations.append(f"{ep}: returned data with 200")
                                record(f"RBAC Violation {ep}", "FAIL", "Employee can access admin-only data!")
                        except Exception:
                            pass
                    elif r.status_code in [401, 403]:
                        record(f"RBAC Check {ep}", "PASS", f"Properly blocked: {r.status_code}")
                        break
                except Exception:
                    continue

        if rbac_violations:
            driver = get_driver()
            log_bug(driver, "[API][RBAC] Employee can access admin-only monitoring endpoints",
                    f"Employee token can access admin-only API endpoints:\n\n" +
                    "\n".join(f"- {v}" for v in rbac_violations) +
                    "\n\nThis is a data leak / privilege escalation vulnerability.",
                    "critical")
            driver.quit()
            driver = None
        else:
            record("RBAC API Check", "PASS", "No RBAC violations found in API layer")

        # 4.6 Check for data leaks between modules
        print("\n--- 4.6 Cross-Module Data Leak Check ---")
        # Try using monitor token on field force and vice versa
        leak_found = False
        if admin_token:
            cross_urls = [
                (FIELD_URL + "/api/v1/monitoring/data", "Field accessing Monitor data"),
                (MONITOR_URL + "/api/v1/field/data", "Monitor accessing Field data"),
            ]
            for curl, desc in cross_urls:
                try:
                    r = requests.get(curl, headers=headers_admin, timeout=8, verify=False)
                    if r.status_code == 200:
                        try:
                            data = r.json()
                            if data and isinstance(data, dict) and len(str(data)) > 50:
                                leak_found = True
                                record(f"Cross-Module Leak: {desc}", "FAIL", f"Data returned: {str(data)[:200]}")
                        except Exception:
                            pass
                except Exception:
                    continue

        if not leak_found:
            record("Cross-Module Data Leak", "PASS", "No cross-module data leaks detected")

        # 4.7 Test unauthenticated access
        print("\n--- 4.7 Unauthenticated Access Check ---")
        unauth_endpoints = [
            API_URL + "/monitoring/dashboard",
            API_URL + "/field/tracking",
            API_URL + "/biometric/logs",
            API_URL + "/employees",
            MAIN_URL + "/api/v1/monitoring/dashboard",
        ]
        for ep in unauth_endpoints:
            try:
                r = requests.get(ep, timeout=8, verify=False)
                if r.status_code == 200:
                    try:
                        data = r.json()
                        if data and isinstance(data, dict) and (data.get("data") or data.get("employees")):
                            record(f"Unauth Access {ep}", "FAIL", "Data accessible without auth!")
                            if not driver:
                                driver = get_driver()
                            log_bug(driver, f"[API][Security] Unauthenticated access to {ep.split('/')[-1]}",
                                    f"Endpoint {ep} returns data without authentication.\n\nResponse: {str(data)[:300]}",
                                    "critical")
                    except Exception:
                        pass
                elif r.status_code in [401, 403]:
                    record(f"Unauth Check {ep}", "PASS", f"Properly blocked: {r.status_code}")
            except Exception:
                continue

    except Exception as e:
        record("API Module Error", "FAIL", f"Exception: {str(e)}")
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()


# =============================================================================
# MAIN EXECUTION
# =============================================================================
def print_summary():
    print("\n" + "="*70)
    print("TEST EXECUTION SUMMARY")
    print("="*70)

    pass_count = sum(1 for r in test_results if r["status"] == "PASS")
    fail_count = sum(1 for r in test_results if r["status"] == "FAIL")
    info_count = sum(1 for r in test_results if r["status"] == "INFO")

    print(f"\nTotal: {len(test_results)} | PASS: {pass_count} | FAIL: {fail_count} | INFO: {info_count}")

    if fail_count > 0:
        print("\n--- FAILURES ---")
        for r in test_results:
            if r["status"] == "FAIL":
                print(f"  FAIL: {r['test']} - {r['details']}")

    if bugs_found:
        print(f"\n--- BUGS FILED: {len(bugs_found)} ---")
        for b in bugs_found:
            print(f"  [{b['severity'].upper()}] {b['title']}")
            if b.get('screenshot'):
                print(f"    Screenshot: {b['screenshot']}")

    print("\n" + "="*70)


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    start = time.time()
    print(f"EMP Cloud E2E Tests - Monitor, Field Force, Biometrics")
    print(f"Started: {datetime.now().isoformat()}")

    test_monitoring_module()
    test_field_force_module()
    test_biometrics_module()
    test_cross_module_api()

    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed:.1f}s")
    print_summary()
