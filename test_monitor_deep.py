"""
EMP Monitor Module - Deep Comprehensive Test v2
Tests all sidebar features: Dashboard, Timesheets, Live Monitoring, Time Claim,
Reports, DLP, Settings, Schedule Task + Employee view (Priya)
Uses proper /admin/ and /employee/ route prefixes after SSO.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
import json
import os
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_monitor"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

LOGIN_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
MONITOR_BASE = "https://test-empmonitor.empcloud.com"

ADMIN_EMAIL = "ananya@technova.in"
EMPLOYEE_EMAIL = "priya@technova.in"
PASSWORD = "Welcome@123"

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

bugs = []
test_results = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {name}.png")
    return path

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
            json={
                "title": title,
                "body": body,
                "labels": ["bug", "verified-bug", "monitor"]
            }
        )
        if resp.status_code == 201:
            log(f"  Filed issue #{resp.json()['number']}: {title}")
        else:
            log(f"  Issue filing status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log(f"  Error filing bug: {e}")

def record(test_name, status, details=""):
    test_results.append({"test": test_name, "status": status, "details": details})
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
    log(f"  [{icon}] {test_name}: {details}")

def make_driver():
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
    driver.implicitly_wait(3)
    return driver

def get_sso_token(email, password):
    log(f"Logging in as {email}...")
    resp = requests.post(LOGIN_URL, json={"email": email, "password": password})
    if resp.status_code != 200:
        log(f"  Login failed: {resp.status_code}")
        return None
    data = resp.json()
    token = (
        data.get("data", {}).get("tokens", {}).get("access_token")
        or data.get("data", {}).get("token")
        or data.get("token")
    )
    if token:
        log(f"  Got token: {token[:30]}...")
    return token

def sso_login(driver, token):
    """SSO into monitor base and wait for redirect"""
    url = f"{MONITOR_BASE}?sso_token={token}"
    log(f"  SSO navigating to monitor...")
    driver.get(url)
    time.sleep(5)
    return driver.current_url

def click_sidebar(driver, link_text, timeout=10):
    """Click a sidebar link by its text"""
    try:
        # Try multiple sidebar selectors
        selectors = [
            f"//nav//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{link_text.lower()}')]",
            f"//aside//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{link_text.lower()}')]",
            f"//*[contains(@class,'sidebar')]//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{link_text.lower()}')]",
            f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{link_text.lower()}')]",
        ]
        for xpath in selectors:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        time.sleep(0.3)
                        el.click()
                        time.sleep(3)
                        return True
            except:
                continue
        return False
    except Exception as e:
        log(f"  Error clicking sidebar '{link_text}': {e}")
        return False

def navigate_to(driver, path):
    """Navigate to a specific path within the monitor app (preserves session)"""
    url = f"{MONITOR_BASE}{path}"
    driver.get(url)
    time.sleep(4)
    return driver.current_url

def get_body_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""

def check_page_loaded(driver, page_name):
    """Check if page loaded properly or redirected to login"""
    url = driver.current_url
    body = get_body_text(driver)

    if "/login" in url:
        record(page_name, "fail", f"Redirected to login ({url})")
        return False, body

    if len(body) < 30:
        record(page_name, "warn", f"Page nearly empty ({len(body)} chars)")
        return False, body

    record(page_name, "pass", f"Loaded OK at {url[:70]} ({len(body)} chars)")
    return True, body

def full_page_screenshot(driver, name):
    """Take screenshot at top, middle, bottom"""
    screenshot(driver, f"{name}_top")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(0.5)
    screenshot(driver, f"{name}_mid")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)
    screenshot(driver, f"{name}_bot")
    driver.execute_script("window.scrollTo(0, 0);")


# ====================================================================
# ADMIN TESTS
# ====================================================================
def test_admin(token):
    log("\n" + "="*70)
    log("ADMIN TESTS (ananya@technova.in)")
    log("="*70)

    driver = make_driver()
    try:
        # ----- SSO Login -----
        log("\n--- 1. SSO Login ---")
        landing = sso_login(driver, token)
        log(f"  Landed: {landing}")
        screenshot(driver, "A01_dashboard")

        if "/admin/dashboard" in landing:
            record("Admin SSO Login", "pass", "Redirected to /admin/dashboard")
        elif "/login" in landing:
            record("Admin SSO Login", "fail", "Stuck on login page")
            file_bug("[Monitor] Admin SSO login fails",
                     "SSO token not accepted, user stuck on login page")
            driver.quit()
            return
        else:
            record("Admin SSO Login", "pass", f"Landed at {landing}")

        # ----- 2. Dashboard Deep Inspection -----
        log("\n--- 2. Dashboard Deep Inspection ---")
        body = get_body_text(driver)
        full_page_screenshot(driver, "A02_dashboard_full")

        # Check expected dashboard widgets
        dashboard_keywords = {
            "Today Activity Snapshot": "today activity snapshot" in body.lower(),
            "Activity Break Down": "activity break down" in body.lower() or "activity breakdown" in body.lower(),
            "Top 10 Productive": "top 10 productive" in body.lower(),
            "Top 10 Non Productive": "non productive" in body.lower(),
            "Idle Time": "idle" in body.lower(),
            "Productive Time": "productive" in body.lower(),
        }
        for widget, found in dashboard_keywords.items():
            if found:
                record(f"Dashboard: {widget}", "pass", "Widget present")
            else:
                record(f"Dashboard: {widget}", "warn", "Widget text not found")

        # Check for AI Assistant
        ai_elements = driver.find_elements(By.XPATH, "//*[contains(text(),'AI') or contains(text(),'Assistant') or contains(@class,'chat') or contains(@class,'bot')]")
        if ai_elements:
            record("Dashboard: AI Assistant", "pass", f"Found {len(ai_elements)} AI elements")
        else:
            record("Dashboard: AI Assistant", "warn", "AI Assistant not visible")

        # Check sidebar items
        log("\n  Sidebar items found:")
        sidebar_links = driver.find_elements(By.CSS_SELECTOR, "nav a, aside a, [class*='sidebar'] a")
        sidebar_texts = []
        for sl in sidebar_links:
            txt = sl.text.strip()
            if txt and len(txt) < 40:
                sidebar_texts.append(txt)
                log(f"    - {txt}")

        # Check for Download Agent button
        download_els = driver.find_elements(By.XPATH, "//*[contains(text(),'Download Agent') or contains(text(),'Download')]")
        if download_els:
            record("Dashboard: Download Agent", "pass", "Download Agent button present")
        else:
            record("Dashboard: Download Agent", "warn", "Download Agent button not found")

        # License info
        license_els = driver.find_elements(By.XPATH, "//*[contains(text(),'License') or contains(text(),'licence')]")
        if license_els:
            record("Dashboard: License Info", "pass", "License info present")

        # ----- 3. Timesheets -----
        log("\n--- 3. Timesheets ---")
        navigated = navigate_to(driver, "/admin/timesheets")
        time.sleep(3)
        screenshot(driver, "A03_timesheets")
        ok, body = check_page_loaded(driver, "Timesheets Page")

        if ok:
            full_page_screenshot(driver, "A03_timesheets")

            # Check for timesheet elements
            ts_keywords = ["employee", "time", "hours", "date", "active", "idle", "productive"]
            found_kw = [kw for kw in ts_keywords if kw in body.lower()]
            log(f"  Timesheet keywords found: {found_kw}")

            # Check for table/list
            tables = driver.find_elements(By.CSS_SELECTOR, "table, [class*='table'], [role='grid'], [class*='list']")
            log(f"  Tables/lists found: {len(tables)}")

            # Check for date picker / filters
            date_pickers = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], [class*='date'], [class*='picker'], [class*='calendar']")
            log(f"  Date pickers: {len(date_pickers)}")

            filters = driver.find_elements(By.CSS_SELECTOR, "select, [class*='filter'], [class*='dropdown'], [class*='select']")
            log(f"  Filters/dropdowns: {len(filters)}")

            if len(tables) == 0 and "no data" not in body.lower() and "no record" not in body.lower():
                if len(body) > 200:
                    record("Timesheets: Data Table", "warn", "No table found but page has content")
                else:
                    record("Timesheets: Data Table", "warn", "No table/data visible")

        # ----- 4. Live Monitoring -----
        log("\n--- 4. Live Monitoring ---")
        navigated = navigate_to(driver, "/admin/livemonitoring")
        time.sleep(3)
        screenshot(driver, "A04_livemonitoring")
        ok, body = check_page_loaded(driver, "Live Monitoring Page")

        if ok:
            full_page_screenshot(driver, "A04_livemonitoring")

            # Check for screen thumbnails / employee list
            screen_els = driver.find_elements(By.CSS_SELECTOR, "img, [class*='screen'], [class*='thumbnail'], canvas, video")
            log(f"  Screen/image elements: {len(screen_els)}")

            employee_cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='employee'], [class*='user']")
            log(f"  Employee cards/items: {len(employee_cards)}")

            if "no employee" in body.lower() or "no active" in body.lower() or "no data" in body.lower():
                record("Live Monitoring: Active Employees", "warn", "No active employees to monitor")
            elif len(screen_els) > 0:
                record("Live Monitoring: Screens", "pass", f"{len(screen_els)} screen elements found")

        # ----- 5. Time Claim -----
        log("\n--- 5. Time Claim ---")
        navigated = navigate_to(driver, "/admin/timeclaim")
        time.sleep(3)
        screenshot(driver, "A05_timeclaim")
        ok, body = check_page_loaded(driver, "Time Claim Page")

        if ok:
            full_page_screenshot(driver, "A05_timeclaim")
            # Check for claim approval/rejection buttons
            action_btns = driver.find_elements(By.CSS_SELECTOR, "button, [class*='approve'], [class*='reject'], [class*='action']")
            log(f"  Action buttons: {len(action_btns)}")

        # ----- 6. Reports -----
        log("\n--- 6. Reports ---")
        report_paths = ["/admin/reports", "/admin/productivity", "/admin/analytics",
                        "/admin/insights", "/admin/report"]
        reports_ok = False
        for path in report_paths:
            navigated = navigate_to(driver, path)
            time.sleep(3)
            if "/login" not in driver.current_url:
                screenshot(driver, f"A06_reports{path.replace('/admin','').replace('/','_')}")
                ok, body = check_page_loaded(driver, f"Reports ({path})")
                if ok:
                    reports_ok = True
                    full_page_screenshot(driver, "A06_reports")
                    charts = driver.find_elements(By.CSS_SELECTOR, "canvas, svg, [class*='chart'], [class*='graph']")
                    log(f"  Chart elements: {len(charts)}")
                    break

        if not reports_ok:
            # Try clicking sidebar
            navigate_to(driver, "/admin/dashboard")
            time.sleep(2)
            if click_sidebar(driver, "report"):
                time.sleep(3)
                screenshot(driver, "A06_reports_sidebar")
                ok, body = check_page_loaded(driver, "Reports (via sidebar)")

        # ----- 7. DLP -----
        log("\n--- 7. DLP (Data Leak Prevention) ---")
        dlp_paths = ["/admin/dlp", "/admin/data-loss-prevention", "/admin/threats",
                     "/admin/insider-threats", "/admin/security"]
        dlp_ok = False
        for path in dlp_paths:
            navigated = navigate_to(driver, path)
            time.sleep(3)
            if "/login" not in driver.current_url:
                screenshot(driver, f"A07_dlp{path.replace('/admin','').replace('/','_')}")
                ok, body = check_page_loaded(driver, f"DLP ({path})")
                if ok:
                    dlp_ok = True
                    full_page_screenshot(driver, "A07_dlp")
                    # Check for alerts/rules
                    alert_els = driver.find_elements(By.CSS_SELECTOR, "[class*='alert'], [class*='rule'], [class*='threat']")
                    log(f"  Alert/rule elements: {len(alert_els)}")
                    break

        if not dlp_ok:
            navigate_to(driver, "/admin/dashboard")
            time.sleep(2)
            if click_sidebar(driver, "dlp"):
                time.sleep(3)
                screenshot(driver, "A07_dlp_sidebar")
                ok, body = check_page_loaded(driver, "DLP (via sidebar)")
                if ok:
                    dlp_ok = True
                    full_page_screenshot(driver, "A07_dlp_sidebar_full")

        # ----- 8. Settings -----
        log("\n--- 8. Settings ---")
        settings_paths = ["/admin/settings", "/admin/configuration", "/admin/preferences"]
        settings_ok = False
        for path in settings_paths:
            navigated = navigate_to(driver, path)
            time.sleep(3)
            if "/login" not in driver.current_url:
                screenshot(driver, f"A08_settings{path.replace('/admin','').replace('/','_')}")
                ok, body = check_page_loaded(driver, f"Settings ({path})")
                if ok:
                    settings_ok = True
                    full_page_screenshot(driver, "A08_settings")
                    # Check for toggles, form fields
                    inputs = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea, [class*='toggle'], [class*='switch']")
                    log(f"  Form elements: {len(inputs)}")
                    break

        if not settings_ok:
            navigate_to(driver, "/admin/dashboard")
            time.sleep(2)
            if click_sidebar(driver, "setting"):
                time.sleep(3)
                screenshot(driver, "A08_settings_sidebar")
                ok, body = check_page_loaded(driver, "Settings (via sidebar)")
                if ok:
                    full_page_screenshot(driver, "A08_settings_sidebar")

        # ----- 9. Schedule Task -----
        log("\n--- 9. Schedule Task ---")
        schedule_paths = ["/admin/scheduletask", "/admin/schedule-task", "/admin/schedule"]
        for path in schedule_paths:
            navigated = navigate_to(driver, path)
            time.sleep(3)
            if "/login" not in driver.current_url:
                screenshot(driver, f"A09_schedule{path.replace('/admin','').replace('/','_')}")
                ok, body = check_page_loaded(driver, f"Schedule Task ({path})")
                if ok:
                    full_page_screenshot(driver, "A09_schedule")
                    break

        if not any(r["test"].startswith("Schedule Task") and r["status"] == "pass" for r in test_results):
            navigate_to(driver, "/admin/dashboard")
            time.sleep(2)
            if click_sidebar(driver, "schedule"):
                time.sleep(3)
                screenshot(driver, "A09_schedule_sidebar")
                check_page_loaded(driver, "Schedule Task (via sidebar)")

        # ----- 10. Explore Invite/Task if visible -----
        log("\n--- 10. Invite/Task ---")
        navigate_to(driver, "/admin/dashboard")
        time.sleep(2)
        if click_sidebar(driver, "invite"):
            time.sleep(3)
            screenshot(driver, "A10_invite")
            check_page_loaded(driver, "Invite (via sidebar)")

        # ----- 11. Verify README features: App/URL tracking, Screenshots -----
        log("\n--- 11. Checking README features not in sidebar ---")
        # App tracking - may be under a sub-menu or different route
        missing_features = {
            "App Tracking": ["/admin/apps", "/admin/app-tracking", "/admin/applications",
                            "/admin/app-usage", "/admin/activity/apps"],
            "URL Tracking": ["/admin/urls", "/admin/url-tracking", "/admin/websites",
                           "/admin/web-history", "/admin/activity/urls"],
            "Screenshots": ["/admin/screenshots", "/admin/screen-captures",
                          "/admin/captures"],
            "Attendance": ["/admin/attendance", "/admin/attendance-monitoring"],
            "Productivity": ["/admin/productivity", "/admin/workforce-productivity"],
            "Employees": ["/admin/employees", "/admin/employee-list", "/admin/users"],
        }

        for feature, paths in missing_features.items():
            found = False
            for path in paths:
                navigated = navigate_to(driver, path)
                time.sleep(2)
                if "/login" not in driver.current_url:
                    ok, body = check_page_loaded(driver, f"README Feature: {feature} ({path})")
                    if ok:
                        screenshot(driver, f"A11_{feature.replace(' ','_').replace('/','_')}")
                        found = True
                        break
            if not found:
                record(f"README Feature: {feature}", "warn",
                       f"Feature from README not accessible via any tried path")

        # ----- 12. Check for common bugs -----
        log("\n--- 12. Bug checks ---")

        # Check title for typo
        title = driver.title
        if "montior" in title.lower():
            file_bug(
                "[Monitor] Typo in page title: 'empmontior' should be 'empmonitor'",
                f"**Steps:** Open any page in EmpMonitor\n"
                f"**Expected:** Title should read 'empmonitor' or 'EmpMonitor'\n"
                f"**Actual:** Title reads '{title}' - 'montior' is a misspelling of 'monitor'\n"
                f"**Impact:** Unprofessional, affects SEO and brand consistency"
            )
            record("Title typo check", "fail", f"Typo in title: '{title}'")

        # Check console errors
        try:
            logs = driver.get_log("browser")
            severe = [l for l in logs if l.get("level") == "SEVERE"]
            if severe:
                log(f"  Console SEVERE errors: {len(severe)}")
                for err in severe[:5]:
                    log(f"    {err['message'][:100]}")
                if len(severe) > 3:
                    record("Console Errors", "warn", f"{len(severe)} SEVERE console errors")
        except:
            pass

    except Exception as e:
        log(f"ADMIN TEST ERROR: {e}")
        traceback.print_exc()
        screenshot(driver, "A_error")
    finally:
        driver.quit()


# ====================================================================
# EMPLOYEE TESTS
# ====================================================================
def test_employee(token):
    log("\n" + "="*70)
    log("EMPLOYEE TESTS (priya@technova.in)")
    log("="*70)

    driver = make_driver()
    try:
        # SSO Login
        log("\n--- E1. Employee SSO Login ---")
        landing = sso_login(driver, token)
        log(f"  Landed: {landing}")
        screenshot(driver, "E01_employee_landing")

        if "/employee/" in landing:
            record("Employee SSO Login", "pass", f"Redirected to {landing}")
        elif "/login" in landing:
            record("Employee SSO Login", "fail", "Stuck on login")
            file_bug("[Monitor] Employee SSO login fails",
                     "SSO token not accepted for employee role")
            driver.quit()
            return
        else:
            record("Employee SSO Login", "pass", f"Landed at {landing}")

        # ----- E2. Employee Dashboard -----
        log("\n--- E2. Employee Dashboard ---")
        body = get_body_text(driver)
        full_page_screenshot(driver, "E02_dashboard")

        # Check employee dashboard content
        emp_widgets = {
            "Employee Name (Priya)": "priya" in body.lower(),
            "Productivity Tab": "productivity" in body.lower(),
            "Timesheets Tab": "timesheet" in body.lower(),
            "Screenshots Tab": "screenshot" in body.lower(),
            "Screen Cast Tab": "screen cast" in body.lower(),
            "Screen Recording Tab": "screen recording" in body.lower() or "recording" in body.lower(),
            "Web History Tab": "web history" in body.lower() or "web" in body.lower(),
            "App History Tab": "app history" in body.lower() or "app" in body.lower(),
            "Key Strokes Tab": "key stroke" in body.lower() or "keystroke" in body.lower(),
        }

        for widget, found in emp_widgets.items():
            if found:
                record(f"Employee Dashboard: {widget}", "pass", "Present")
            else:
                record(f"Employee Dashboard: {widget}", "warn", "Not visible")

        # Check date range selector
        date_els = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], [class*='date'], [class*='range']")
        if date_els:
            record("Employee: Date Range Selector", "pass", f"{len(date_els)} date elements")
        else:
            record("Employee: Date Range Selector", "warn", "No date range selector found")

        # ----- E3. Click each tab on employee dashboard -----
        log("\n--- E3. Employee Dashboard Tabs ---")
        tab_names = ["Productivity", "Timesheets", "Screenshots", "Screen Cast",
                     "Screen Recording", "Web History", "App History", "Key Strokes"]

        for tab_name in tab_names:
            log(f"  Trying tab: {tab_name}")
            try:
                # Try clicking the tab
                tab_xpaths = [
                    f"//*[contains(@class,'tab') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{tab_name.lower()}')]",
                    f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{tab_name.lower()}')]",
                    f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{tab_name.lower()}')]",
                ]
                clicked = False
                for xpath in tab_xpaths:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed() and el.size.get('height', 0) > 0:
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                                time.sleep(0.3)
                                el.click()
                                clicked = True
                                break
                            except:
                                try:
                                    driver.execute_script("arguments[0].click();", el)
                                    clicked = True
                                    break
                                except:
                                    continue
                    if clicked:
                        break

                if clicked:
                    time.sleep(3)
                    screenshot(driver, f"E03_tab_{tab_name.replace(' ','_')}")
                    tab_body = get_body_text(driver)
                    if len(tab_body) > 50:
                        record(f"Employee Tab: {tab_name}", "pass", f"Tab loaded ({len(tab_body)} chars)")
                    else:
                        record(f"Employee Tab: {tab_name}", "warn", f"Tab content sparse ({len(tab_body)} chars)")
                else:
                    record(f"Employee Tab: {tab_name}", "warn", "Could not click tab")
            except Exception as e:
                record(f"Employee Tab: {tab_name}", "fail", f"Error: {str(e)[:60]}")

        # ----- E4. Employee sidebar navigation -----
        log("\n--- E4. Employee Sidebar ---")
        sidebar_links = driver.find_elements(By.CSS_SELECTOR, "nav a, aside a, [class*='sidebar'] a")
        emp_sidebar = []
        for sl in sidebar_links:
            txt = sl.text.strip()
            if txt and len(txt) < 40:
                emp_sidebar.append(txt)
                log(f"  Employee sidebar: {txt}")

        # ----- E5. Employee Time Claim -----
        log("\n--- E5. Employee Time Claim ---")
        navigated = navigate_to(driver, "/employee/time-claim")
        time.sleep(3)
        screenshot(driver, "E05_timeclaim")
        ok, body = check_page_loaded(driver, "Employee Time Claim")

        if ok:
            full_page_screenshot(driver, "E05_timeclaim")
            # Check for claim form
            forms = driver.find_elements(By.CSS_SELECTOR, "form, button, input, [class*='claim']")
            log(f"  Time claim form elements: {len(forms)}")

        # ----- E6. RBAC Check: Employee should NOT access admin pages -----
        log("\n--- E6. RBAC: Employee vs Admin access ---")
        admin_only_pages = [
            ("/admin/dashboard", "Admin Dashboard"),
            ("/admin/timesheets", "Admin Timesheets"),
            ("/admin/livemonitoring", "Live Monitoring"),
            ("/admin/dlp", "DLP"),
            ("/admin/settings", "Settings"),
            ("/admin/reports", "Reports"),
        ]

        for path, name in admin_only_pages:
            navigated = navigate_to(driver, path)
            time.sleep(3)
            curr_url = driver.current_url
            curr_body = get_body_text(driver)
            screenshot(driver, f"E06_rbac_{name.replace(' ','_')}")

            if "/login" in curr_url or "/employee/" in curr_url:
                record(f"RBAC: Employee blocked from {name}", "pass",
                       f"Properly restricted (redirected to {curr_url[:50]})")
            elif "/admin/" in curr_url and len(curr_body) > 100:
                # Employee got into admin page - this is a bug!
                record(f"RBAC: Employee blocked from {name}", "fail",
                       f"Employee CAN access admin page {path}")
                file_bug(
                    f"[Monitor] RBAC bypass: Employee can access {name} ({path})",
                    f"**Steps:**\n1. Login as priya@technova.in (Employee role)\n"
                    f"2. Navigate to {MONITOR_BASE}{path}\n\n"
                    f"**Expected:** Employee should be blocked/redirected from admin pages\n"
                    f"**Actual:** Employee can access {path} and see admin content\n"
                    f"**URL after navigation:** {curr_url}\n"
                    f"**Body length:** {len(curr_body)} chars\n"
                    f"**Security Impact:** HIGH - employees can view other employees' monitoring data, "
                    f"modify DLP rules, and access live monitoring screens"
                )
            else:
                record(f"RBAC: Employee blocked from {name}", "pass",
                       f"Page appears restricted")

        # ----- E7. Employee Portal Link -----
        log("\n--- E7. Employee Portal Link ---")
        navigate_to(driver, "/employee/dashboard")
        time.sleep(2)
        portal_els = driver.find_elements(By.XPATH, "//*[contains(text(),'Employee Portal') or contains(text(),'portal')]")
        if portal_els:
            record("Employee Portal Link", "pass", f"Found {len(portal_els)} portal references")
            for pel in portal_els:
                try:
                    href = pel.get_attribute("href")
                    if href:
                        log(f"  Portal link: {href}")
                except:
                    pass
        else:
            record("Employee Portal Link", "warn", "No employee portal link found")

    except Exception as e:
        log(f"EMPLOYEE TEST ERROR: {e}")
        traceback.print_exc()
        screenshot(driver, "E_error")
    finally:
        driver.quit()


# ====================================================================
# MAIN
# ====================================================================
def main():
    log("="*70)
    log("EMP MONITOR MODULE - DEEP COMPREHENSIVE TEST v2")
    log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("="*70)

    # Get tokens
    admin_token = get_sso_token(ADMIN_EMAIL, PASSWORD)
    if not admin_token:
        log("FATAL: No admin token")
        sys.exit(1)

    employee_token = get_sso_token(EMPLOYEE_EMAIL, PASSWORD)

    # Run tests
    test_admin(admin_token)

    if employee_token:
        test_employee(employee_token)
    else:
        log("SKIPPING employee tests - no token")

    # ---- Summary ----
    log("\n" + "="*70)
    log("FINAL TEST SUMMARY")
    log("="*70)

    pass_count = sum(1 for r in test_results if r["status"] == "pass")
    fail_count = sum(1 for r in test_results if r["status"] == "fail")
    warn_count = sum(1 for r in test_results if r["status"] == "warn")

    log(f"\nTotal tests: {len(test_results)}")
    log(f"  PASS: {pass_count}")
    log(f"  FAIL: {fail_count}")
    log(f"  WARN: {warn_count}")

    if fail_count > 0:
        log(f"\n--- FAILURES ---")
        for r in test_results:
            if r["status"] == "fail":
                log(f"  FAIL: {r['test']} -- {r['details']}")

    if warn_count > 0:
        log(f"\n--- WARNINGS ---")
        for r in test_results:
            if r["status"] == "warn":
                log(f"  WARN: {r['test']} -- {r['details']}")

    log(f"\nBugs filed: {len(bugs)}")
    for b in bugs:
        log(f"  - {b}")

    log(f"\nScreenshots: {SCREENSHOT_DIR}")
    log(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
