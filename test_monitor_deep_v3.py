"""
EMP Monitor Module - Deep Test v3 (follow-up)
Tests DLP sub-menus, Settings sub-menus, Employees sub-menu, Behaviour, Recorder
Files additional bugs found in v2 visual inspection.
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
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_monitor"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

LOGIN_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
MONITOR_BASE = "https://test-empmonitor.empcloud.com"

ADMIN_EMAIL = "ananya@technova.in"
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
    url = f"{MONITOR_BASE}?sso_token={token}"
    driver.get(url)
    time.sleep(5)
    return driver.current_url

def navigate_to(driver, path):
    url = f"{MONITOR_BASE}{path}"
    driver.get(url)
    time.sleep(4)
    return driver.current_url

def get_body_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""

def click_sidebar_item(driver, text_to_find):
    """Click sidebar item that contains the given text"""
    try:
        xpaths = [
            f"//*[contains(@class,'sidebar') or contains(@class,'nav') or contains(@class,'menu')]//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text_to_find.lower()}')]",
            f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text_to_find.lower()}')]",
            f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text_to_find.lower()}')]",
        ]
        for xpath in xpaths:
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                if el.is_displayed() and el.size.get('height', 0) > 0:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.3)
                    try:
                        el.click()
                    except:
                        driver.execute_script("arguments[0].click();", el)
                    time.sleep(2)
                    return True
        return False
    except:
        return False


def main():
    log("="*70)
    log("EMP MONITOR - DEEP TEST v3 (Sub-menus, DLP, Settings, Behaviour)")
    log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("="*70)

    admin_token = get_sso_token(ADMIN_EMAIL, PASSWORD)
    if not admin_token:
        log("FATAL: No admin token")
        sys.exit(1)

    driver = make_driver()
    try:
        # SSO in
        log("\n--- SSO Login ---")
        landing = sso_login(driver, admin_token)
        log(f"  Landed: {landing}")

        if "/admin/dashboard" not in landing:
            log("FATAL: Did not reach admin dashboard")
            driver.quit()
            return

        # ---- Discover ALL sidebar items including sub-items ----
        log("\n--- Full Sidebar Discovery ---")

        # First, get all sidebar text content before clicking
        body = get_body_text(driver)
        screenshot(driver, "V3_01_sidebar_initial")

        # Get all sidebar elements
        all_sidebar = driver.find_elements(By.CSS_SELECTOR,
            "nav a, nav span, aside a, aside span, [class*='sidebar'] a, [class*='sidebar'] span, "
            "[class*='menu'] a, [class*='menu'] span, [class*='nav-item'], [class*='menu-item']"
        )
        sidebar_items = []
        for el in all_sidebar:
            txt = el.text.strip()
            href = el.get_attribute("href") or ""
            if txt and 1 < len(txt) < 50 and txt not in [s["text"] for s in sidebar_items]:
                sidebar_items.append({"text": txt, "href": href})

        log(f"  Sidebar items ({len(sidebar_items)}):")
        for item in sidebar_items:
            log(f"    '{item['text']}' -> {item['href'][:60] if item['href'] else '(no href)'}")

        # ---- Click on expandable menus to reveal sub-items ----
        expandable_items = ["Employees", "DLP", "Settings"]
        for item_text in expandable_items:
            log(f"\n  Expanding sidebar: {item_text}")
            if click_sidebar_item(driver, item_text):
                time.sleep(2)
                screenshot(driver, f"V3_02_sidebar_{item_text}")
                # Re-scan sidebar for new sub-items
                new_items = driver.find_elements(By.CSS_SELECTOR,
                    "nav a, aside a, [class*='sidebar'] a, [class*='menu'] a, [class*='sub'] a"
                )
                for el in new_items:
                    txt = el.text.strip()
                    href = el.get_attribute("href") or ""
                    if txt and 1 < len(txt) < 50 and txt not in [s["text"] for s in sidebar_items]:
                        sidebar_items.append({"text": txt, "href": href})
                        log(f"    NEW sub-item: '{txt}' -> {href[:60] if href else ''}")

        log(f"\n  Total sidebar items after expansion: {len(sidebar_items)}")

        # ---- Test Employees sub-pages ----
        log("\n--- Employees Sub-Menu ---")
        emp_paths = ["/admin/employees", "/admin/employee", "/admin/employee-list",
                     "/admin/employee-details", "/admin/users"]
        for path in emp_paths:
            url = navigate_to(driver, path)
            if "/login" not in driver.current_url:
                body = get_body_text(driver)
                screenshot(driver, f"V3_03_emp{path.replace('/admin','').replace('/','_')}")
                log(f"  {path}: loaded at {driver.current_url[:60]} ({len(body)} chars)")
                record(f"Employees ({path})", "pass", f"Loaded with {len(body)} chars")
                break
        else:
            # Try clicking sidebar
            navigate_to(driver, "/admin/dashboard")
            time.sleep(2)
            if click_sidebar_item(driver, "employees"):
                time.sleep(3)
                screenshot(driver, "V3_03_employees_sidebar")
                body = get_body_text(driver)
                url = driver.current_url
                log(f"  Employees via sidebar: {url[:60]} ({len(body)} chars)")
                if "/login" not in url:
                    record("Employees (via sidebar)", "pass", f"At {url}")

        # ---- Test DLP Sub-pages ----
        log("\n--- DLP Sub-Menu Pages ---")
        # From screenshot we saw: Manage Alerts, Productivity Rules, Role & Permissions
        dlp_sub_paths = [
            "/admin/dlp", "/admin/dlp/alerts", "/admin/dlp/manage-alerts",
            "/admin/manage-alerts", "/admin/alerts",
            "/admin/dlp/rules", "/admin/dlp/productivity-rules",
            "/admin/productivity-rules",
            "/admin/dlp/roles", "/admin/dlp/permissions",
            "/admin/role-permissions", "/admin/roles-permissions",
        ]
        for path in dlp_sub_paths:
            url = navigate_to(driver, path)
            curr = driver.current_url
            if "/login" not in curr:
                body = get_body_text(driver)
                screenshot(driver, f"V3_04_dlp{path.replace('/admin','').replace('/','_')}")
                log(f"  DLP {path}: {curr[:60]} ({len(body)} chars)")
                record(f"DLP Sub ({path})", "pass", f"Loaded with {len(body)} chars")

        # Navigate back and click DLP sidebar to expand then click sub-items
        navigate_to(driver, "/admin/dashboard")
        time.sleep(2)
        log("\n  Expanding DLP sidebar and clicking sub-items...")
        if click_sidebar_item(driver, "dlp"):
            time.sleep(2)
            screenshot(driver, "V3_04b_dlp_expanded")
            body_after_dlp = get_body_text(driver)

            # Now try sub-items
            sub_items = ["manage alert", "productivity rule", "role", "permission"]
            for sub in sub_items:
                if click_sidebar_item(driver, sub):
                    time.sleep(3)
                    ss_name = f"V3_04c_dlp_{sub.replace(' ','_')}"
                    screenshot(driver, ss_name)
                    body = get_body_text(driver)
                    url = driver.current_url
                    log(f"  DLP > {sub}: {url[:60]} ({len(body)} chars)")
                    if "/login" not in url:
                        record(f"DLP > {sub}", "pass", f"Loaded at {url}")
                    # Go back to dashboard and re-expand
                    navigate_to(driver, "/admin/dashboard")
                    time.sleep(1)
                    click_sidebar_item(driver, "dlp")
                    time.sleep(1)

        # ---- Test Settings Sub-pages ----
        log("\n--- Settings Sub-Menu Pages ---")
        settings_sub_paths = [
            "/admin/settings", "/admin/settings/monitoring", "/admin/settings/schedules",
            "/admin/settings/general", "/admin/configuration", "/admin/preferences",
        ]
        for path in settings_sub_paths:
            url = navigate_to(driver, path)
            curr = driver.current_url
            if "/login" not in curr:
                body = get_body_text(driver)
                screenshot(driver, f"V3_05_settings{path.replace('/admin','').replace('/','_')}")
                log(f"  Settings {path}: {curr[:60]} ({len(body)} chars)")
                record(f"Settings Sub ({path})", "pass", f"Loaded with {len(body)} chars")

        # Click Settings sidebar
        navigate_to(driver, "/admin/dashboard")
        time.sleep(2)
        log("\n  Expanding Settings sidebar...")
        if click_sidebar_item(driver, "settings"):
            time.sleep(2)
            screenshot(driver, "V3_05b_settings_expanded")
            # Try sub-items visible from screenshot analysis
            settings_subs = ["manage alert", "productivity", "role", "permission", "general", "schedule"]
            for sub in settings_subs:
                if click_sidebar_item(driver, sub):
                    time.sleep(3)
                    screenshot(driver, f"V3_05c_settings_{sub.replace(' ','_')}")
                    body = get_body_text(driver)
                    url = driver.current_url
                    log(f"  Settings > {sub}: {url[:60]} ({len(body)} chars)")
                    if "/login" not in url:
                        record(f"Settings > {sub}", "pass", f"Loaded at {url}")
                    navigate_to(driver, "/admin/dashboard")
                    time.sleep(1)
                    click_sidebar_item(driver, "settings")
                    time.sleep(1)

        # ---- Test Behaviour page ----
        log("\n--- Behaviour Page ---")
        beh_paths = ["/admin/behaviour", "/admin/behavior", "/admin/behavioural"]
        for path in beh_paths:
            url = navigate_to(driver, path)
            if "/login" not in driver.current_url:
                body = get_body_text(driver)
                screenshot(driver, f"V3_06_behaviour{path.replace('/admin','').replace('/','_')}")
                log(f"  Behaviour {path}: {driver.current_url[:60]} ({len(body)} chars)")
                record(f"Behaviour ({path})", "pass", f"Loaded")
                break
        else:
            navigate_to(driver, "/admin/dashboard")
            time.sleep(2)
            if click_sidebar_item(driver, "behaviour"):
                time.sleep(3)
                screenshot(driver, "V3_06_behaviour_sidebar")
                body = get_body_text(driver)
                log(f"  Behaviour via sidebar: {driver.current_url[:60]} ({len(body)} chars)")
                record("Behaviour (sidebar)", "pass" if len(body) > 50 else "warn", f"{len(body)} chars")

        # ---- Test Schedule Task page ----
        log("\n--- Schedule Task Page ---")
        sched_paths = ["/admin/scheduletask", "/admin/schedule-task", "/admin/schedule",
                       "/admin/scheduled-tasks"]
        for path in sched_paths:
            url = navigate_to(driver, path)
            if "/login" not in driver.current_url:
                body = get_body_text(driver)
                screenshot(driver, f"V3_07_schedule{path.replace('/admin','').replace('/','_')}")
                log(f"  Schedule {path}: {driver.current_url[:60]} ({len(body)} chars)")
                record(f"Schedule Task ({path})", "pass", f"Loaded")
                break
        else:
            navigate_to(driver, "/admin/dashboard")
            time.sleep(2)
            if click_sidebar_item(driver, "schedule"):
                time.sleep(3)
                screenshot(driver, "V3_07_schedule_sidebar")
                body = get_body_text(driver)
                log(f"  Schedule via sidebar: {driver.current_url[:60]} ({len(body)} chars)")
                record("Schedule Task (sidebar)", "pass" if len(body) > 50 else "warn", f"{len(body)} chars")

        # ---- Test Recorder page ----
        log("\n--- Recorder Page ---")
        rec_paths = ["/admin/recorder", "/admin/recording", "/admin/recordings"]
        for path in rec_paths:
            url = navigate_to(driver, path)
            if "/login" not in driver.current_url:
                body = get_body_text(driver)
                screenshot(driver, f"V3_08_recorder{path.replace('/admin','').replace('/','_')}")
                log(f"  Recorder {path}: {driver.current_url[:60]} ({len(body)} chars)")
                record(f"Recorder ({path})", "pass", f"Loaded")
                break
        else:
            navigate_to(driver, "/admin/dashboard")
            time.sleep(2)
            if click_sidebar_item(driver, "recorder"):
                time.sleep(3)
                screenshot(driver, "V3_08_recorder_sidebar")
                body = get_body_text(driver)
                log(f"  Recorder via sidebar: {driver.current_url[:60]} ({len(body)} chars)")
                record("Recorder (sidebar)", "pass" if len(body) > 50 else "warn", f"{len(body)} chars")

        # ---- Test Reports / Insights page deeper ----
        log("\n--- Reports/Insights Deep ---")
        navigate_to(driver, "/admin/insights")
        time.sleep(3)
        body = get_body_text(driver)
        screenshot(driver, "V3_09_insights")

        if "/login" not in driver.current_url:
            # Check for filters, date selectors, export
            filters = driver.find_elements(By.CSS_SELECTOR, "select, [class*='filter'], [class*='dropdown']")
            log(f"  Insights filters: {len(filters)}")
            date_els = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], [class*='date']")
            log(f"  Date elements: {len(date_els)}")
            export_els = driver.find_elements(By.XPATH, "//*[contains(text(),'Download') or contains(text(),'Export') or contains(text(),'CSV')]")
            log(f"  Export buttons: {len(export_els)}")

            # Check chart types
            charts = driver.find_elements(By.CSS_SELECTOR, "canvas, svg[class*='chart'], [class*='recharts']")
            log(f"  Chart elements: {len(charts)}")

            # Scroll to see more
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            screenshot(driver, "V3_09_insights_bottom")

            record("Reports/Insights", "pass", f"Page loaded with {len(body)} chars, {len(filters)} filters, {len(charts)} charts")

        # ---- Console error analysis ----
        log("\n--- Console Error Analysis ---")
        try:
            logs = driver.get_log("browser")
            severe = [l for l in logs if l.get("level") == "SEVERE"]
            log(f"  Total SEVERE errors: {len(severe)}")

            # Categorize errors
            api_errors = [l for l in severe if "api" in l.get("message", "").lower()]
            resource_errors = [l for l in severe if "failed to load resource" in l.get("message", "").lower()]
            js_errors = [l for l in severe if "error" in l.get("message", "").lower() and "api" not in l.get("message", "").lower()]

            log(f"  API errors: {len(api_errors)}")
            log(f"  Resource load failures: {len(resource_errors)}")
            log(f"  JS errors: {len(js_errors)}")

            # Check for dev.empmonitor.com calls (wrong env)
            dev_calls = [l for l in severe if "dev.empmonitor.com" in l.get("message", "")]
            if dev_calls:
                log(f"  Calls to dev.empmonitor.com (WRONG ENV): {len(dev_calls)}")
                file_bug(
                    "[Monitor] Frontend makes API calls to dev.empmonitor.com instead of test environment",
                    f"**Steps:** Login as admin, open browser console\n\n"
                    f"**Expected:** API calls should go to test-empmonitor-api.empcloud.com or similar test endpoint\n\n"
                    f"**Actual:** {len(dev_calls)} API calls are made to `service.dev.empmonitor.com` which is a "
                    f"development server, not the test environment.\n\n"
                    f"**Sample errors:**\n"
                    + "\n".join(f"- `{l['message'][:150]}`" for l in dev_calls[:5])
                    + f"\n\n**Impact:** Data may come from wrong environment; API calls fail with errors, "
                    f"causing missing data in dashboard widgets (Activity Breakdown, Departments, Locations etc.)\n\n"
                    f"**Root cause:** Likely hardcoded API base URL pointing to dev instead of using environment config"
                )
                record("Console: Dev API calls", "fail", f"{len(dev_calls)} calls to dev.empmonitor.com")

            # Unique error domains
            error_domains = set()
            for l in severe[:50]:
                msg = l.get("message", "")
                if "http" in msg:
                    import re
                    urls = re.findall(r'https?://[^\s"\']+', msg)
                    for u in urls:
                        try:
                            from urllib.parse import urlparse
                            domain = urlparse(u).netloc
                            error_domains.add(domain)
                        except:
                            pass
            log(f"  Error domains: {error_domains}")

        except Exception as e:
            log(f"  Console log error: {e}")

        # ---- Activity Breakdown bug check ----
        log("\n--- Dashboard Data Checks ---")
        navigate_to(driver, "/admin/dashboard")
        time.sleep(4)
        body = get_body_text(driver)
        screenshot(driver, "V3_10_dashboard_data_check")

        # Check if dashboard shows "No Activity Data" everywhere
        if "no activity data" in body.lower():
            log("  Dashboard shows 'No Activity Data' - may be expected if no agents connected")
            record("Dashboard: Activity Data", "warn", "No activity data shown")

        # Check if "No employees found" appears
        if "no employees found" in body.lower():
            log("  'No employees found' in productive/non-productive sections")
            record("Dashboard: Employee Lists", "warn", "No employees found for selected filters")

        # ---- Live Monitoring deeper check ----
        log("\n--- Live Monitoring Deep Check ---")
        navigate_to(driver, "/admin/livemonitoring")
        time.sleep(4)
        body = get_body_text(driver)
        screenshot(driver, "V3_11_livemon_deep")

        if "no agents found" in body.lower() or "no active" in body.lower():
            record("Live Monitoring: Agents", "warn", "No agents/active employees found")
        elif "live recording" in body.lower():
            record("Live Monitoring: Page Title", "pass", "Live Recording page loaded")

        # Check search functionality
        search = driver.find_elements(By.CSS_SELECTOR, "input[type='search'], input[placeholder*='search'], [class*='search'] input")
        if search:
            record("Live Monitoring: Search", "pass", f"{len(search)} search inputs")
        else:
            record("Live Monitoring: Search", "warn", "No search input found")

        # Check department/employee filters
        dept_filters = driver.find_elements(By.CSS_SELECTOR, "select, [class*='department'], [class*='filter']")
        log(f"  Department/filter elements: {len(dept_filters)}")

        # ---- Check Timesheets data quality ----
        log("\n--- Timesheets Deep Check ---")
        navigate_to(driver, "/admin/timesheets")
        time.sleep(4)
        body = get_body_text(driver)
        screenshot(driver, "V3_12_timesheets_deep")

        # Check table headers
        expected_cols = ["email", "emp code", "location", "department", "shift",
                        "clock in", "clock out", "total hours", "office hours",
                        "active hours", "productive", "unproductive"]
        found_cols = [col for col in expected_cols if col in body.lower()]
        log(f"  Timesheet columns found: {found_cols}")
        record("Timesheets: Column Headers", "pass" if len(found_cols) > 5 else "warn",
               f"{len(found_cols)}/{len(expected_cols)} expected columns found")

        # Check pagination
        pagination = driver.find_elements(By.CSS_SELECTOR, "[class*='pagination'], [class*='pager'], nav[aria-label='pagination']")
        log(f"  Pagination elements: {len(pagination)}")

        # Check download/export
        export_btns = driver.find_elements(By.XPATH,
            "//*[contains(text(),'Download') or contains(text(),'Export') or contains(text(),'CSV') or contains(@class,'export') or contains(@class,'download')]"
        )
        if export_btns:
            record("Timesheets: Export", "pass", f"{len(export_btns)} export options")
        else:
            record("Timesheets: Export", "warn", "No export/download button found")

        # ---- Time Claim checks ----
        log("\n--- Time Claim Deep Check ---")
        navigate_to(driver, "/admin/timeclaim")
        time.sleep(4)
        body = get_body_text(driver)
        screenshot(driver, "V3_13_timeclaim_deep")

        # Check for Create Request button
        create_btns = driver.find_elements(By.XPATH, "//*[contains(text(),'Create Request') or contains(text(),'New Request')]")
        if create_btns:
            record("Time Claim: Create Request", "pass", "Create Request button present")
        else:
            record("Time Claim: Create Request", "warn", "No Create Request button")

        # Check status filters
        status_els = driver.find_elements(By.XPATH, "//*[contains(text(),'Status') or contains(@class,'status')]")
        log(f"  Status elements: {len(status_els)}")

        # Check auto-approve toggle
        auto_approve = driver.find_elements(By.XPATH, "//*[contains(text(),'Auto Approve') or contains(text(),'auto')]")
        if auto_approve:
            record("Time Claim: Auto Approve", "pass", "Auto Approve option present")
        else:
            record("Time Claim: Auto Approve", "warn", "No Auto Approve option")

        # Check date range, request type filters
        if "request type" in body.lower():
            record("Time Claim: Request Type Filter", "pass", "Request Type filter present")

        # ---- Attendance Deep Check ----
        log("\n--- Attendance Deep Check ---")
        navigate_to(driver, "/admin/attendance")
        time.sleep(4)
        body = get_body_text(driver)
        screenshot(driver, "V3_14_attendance_deep")

        if "/login" not in driver.current_url:
            record("Attendance Page", "pass", f"Loaded ({len(body)} chars)")

            # Check calendar grid (numbered 1-31)
            calendar_nums = driver.find_elements(By.XPATH, "//*[text()='1' or text()='15' or text()='28' or text()='30']")
            log(f"  Calendar date elements: {len(calendar_nums)}")

            # Check for P/A/D status indicators
            if any(x in body for x in ["Present", "Absent", "Half-Day", " P ", " A ", " D "]):
                record("Attendance: Status Indicators", "pass", "P/A/D status indicators present")

            # Check department/location filters
            if "department" in body.lower():
                record("Attendance: Department Filter", "pass", "Department filter present")
            if "location" in body.lower():
                record("Attendance: Location Filter", "pass", "Location filter present")

            # Export check
            export = driver.find_elements(By.XPATH, "//*[contains(text(),'Export') or contains(text(),'Download')]")
            if export:
                record("Attendance: Export", "pass", "Export button present")
        else:
            record("Attendance Page", "fail", "Redirected to login")

        # ---- Final full sidebar check with all items visible ----
        log("\n--- Final Sidebar Enumeration ---")
        navigate_to(driver, "/admin/dashboard")
        time.sleep(3)

        # Click all expandable items to show everything
        for item in ["employees", "dlp", "settings"]:
            click_sidebar_item(driver, item)
            time.sleep(1)

        time.sleep(1)
        screenshot(driver, "V3_15_full_sidebar_expanded")

        # Get all links
        all_links = driver.find_elements(By.CSS_SELECTOR, "a")
        sidebar_hrefs = []
        for link in all_links:
            href = link.get_attribute("href") or ""
            txt = link.text.strip()
            if "/admin/" in href and txt:
                sidebar_hrefs.append({"text": txt, "href": href})

        log(f"\n  All admin links found:")
        for item in sidebar_hrefs:
            log(f"    '{item['text']}' -> {item['href']}")

    except Exception as e:
        log(f"ERROR: {e}")
        traceback.print_exc()
        screenshot(driver, "V3_error")
    finally:
        driver.quit()

    # ---- Summary ----
    log("\n" + "="*70)
    log("V3 TEST SUMMARY")
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

    log(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
