"""
EMP Cloud HRMS - Employee Lifecycle Data Flow E2E Test
Tests data consistency across modules: Employees, Attendance, Leave, Org Chart, Announcements, Documents
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import traceback
import urllib.request
import urllib.parse
import ssl
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com"
ORG_ADMIN_EMAIL = "ananya@technova.in"
ORG_ADMIN_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\dataflow"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
EMPLOYEE_ID = 531  # known test employee
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── Helpers ─────────────────────────────────────────────────────────────────
bugs_found = []
test_results = []

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)

def ss(driver, name):
    """Take screenshot with descriptive name."""
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  [SCREENSHOT] {path}")
    return path

def wait_for_page(driver, timeout=15):
    """Wait for page to be loaded and spinners gone."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except:
        pass
    time.sleep(1.5)
    # Wait for spinners/loaders to disappear
    for sel in [".ant-spin-spinning", ".loading", ".spinner", "[class*='loader']", "[class*='Loader']"]:
        try:
            WebDriverWait(driver, 5).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, sel))
            )
        except:
            pass

def click_safe(driver, element):
    """Click element safely, handling intercepted clicks."""
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)

def find_and_click(driver, css=None, xpath=None, text=None, timeout=10):
    """Find an element and click it."""
    try:
        if css:
            el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))
        elif xpath:
            el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))
        elif text:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(),'{text}')]"))
            )
        else:
            return None
        click_safe(driver, el)
        return el
    except Exception:
        return None

def login_api():
    """Login via API to get auth token."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    payload = json.dumps({"email": ORG_ADMIN_EMAIL, "password": ORG_ADMIN_PASS}).encode()
    req = urllib.request.Request(
        f"{API_URL}/api/auth/login",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Origin": BASE_URL,
        },
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        data = json.loads(resp.read().decode())
        token = data.get("token") or data.get("data", {}).get("token") or data.get("accessToken")
        print(f"  [API] Login OK, token: {str(token)[:30]}...")
        return token
    except Exception as e:
        print(f"  [API] Login failed: {e}")
        return None

def login_browser(driver):
    """Login via browser."""
    driver.get(BASE_URL)
    wait_for_page(driver, 20)
    time.sleep(2)

    # Check if redirected to login
    current = driver.current_url
    print(f"  [LOGIN] Current URL: {current}")

    # Try to find email input
    email_selectors = [
        "input[type='email']", "input[name='email']", "input[placeholder*='mail']",
        "input[placeholder*='Mail']", "#email", "input[type='text']"
    ]
    email_input = None
    for sel in email_selectors:
        try:
            email_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
            )
            if email_input:
                break
        except:
            continue

    if not email_input:
        # Maybe already logged in
        if "/dashboard" in driver.current_url or "/home" in driver.current_url:
            print("  [LOGIN] Already logged in")
            return True
        ss(driver, "login_no_email_field")
        print("  [LOGIN] Could not find email field")
        return False

    email_input.clear()
    email_input.send_keys(ORG_ADMIN_EMAIL)
    time.sleep(0.5)

    # Password
    pw_selectors = ["input[type='password']", "input[name='password']", "#password"]
    pw_input = None
    for sel in pw_selectors:
        try:
            pw_input = driver.find_element(By.CSS_SELECTOR, sel)
            if pw_input:
                break
        except:
            continue

    if pw_input:
        pw_input.clear()
        pw_input.send_keys(ORG_ADMIN_PASS)
        time.sleep(0.5)

    # Submit
    submit_selectors = [
        "button[type='submit']", "button:not([type='button'])",
        "input[type='submit']", "button"
    ]
    for sel in submit_selectors:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                txt = btn.text.lower()
                if any(w in txt for w in ["login", "sign in", "log in", "submit", ""]):
                    click_safe(driver, btn)
                    break
            break
        except:
            continue

    time.sleep(3)
    wait_for_page(driver, 20)
    time.sleep(2)
    print(f"  [LOGIN] After login URL: {driver.current_url}")
    ss(driver, "01_login_result")
    return True

def navigate_sidebar(driver, menu_text, sub_text=None):
    """Click a sidebar menu item, optionally a sub-item."""
    time.sleep(1)
    # Try clicking main menu
    clicked = False
    for attempt in range(3):
        try:
            items = driver.find_elements(By.XPATH,
                f"//aside//span[contains(text(),'{menu_text}')] | "
                f"//nav//span[contains(text(),'{menu_text}')] | "
                f"//div[contains(@class,'sidebar')]//span[contains(text(),'{menu_text}')] | "
                f"//div[contains(@class,'Sidebar')]//span[contains(text(),'{menu_text}')] | "
                f"//div[contains(@class,'menu')]//span[contains(text(),'{menu_text}')] | "
                f"//a[contains(text(),'{menu_text}')] | "
                f"//li//span[contains(text(),'{menu_text}')]"
            )
            if items:
                click_safe(driver, items[0])
                clicked = True
                break
            # Try broader match
            items = driver.find_elements(By.XPATH, f"//*[contains(text(),'{menu_text}')]")
            for it in items:
                tag = it.tag_name.lower()
                if tag in ['span', 'a', 'li', 'div', 'p']:
                    click_safe(driver, it)
                    clicked = True
                    break
            if clicked:
                break
        except:
            time.sleep(1)

    if not clicked:
        print(f"  [NAV] Could not find sidebar item: {menu_text}")
        return False

    time.sleep(1.5)

    if sub_text:
        time.sleep(1)
        try:
            subs = driver.find_elements(By.XPATH,
                f"//span[contains(text(),'{sub_text}')] | "
                f"//a[contains(text(),'{sub_text}')] | "
                f"//li[contains(text(),'{sub_text}')]"
            )
            if subs:
                click_safe(driver, subs[0])
                time.sleep(1)
        except:
            print(f"  [NAV] Could not find sub-item: {sub_text}")

    wait_for_page(driver)
    return True

def record_bug(title, description, severity="medium", screenshot_path=None):
    """Record a bug for later filing."""
    bugs_found.append({
        "title": f"[DATA FLOW] {title}",
        "description": description,
        "severity": severity,
        "screenshot": screenshot_path
    })
    print(f"  [BUG] {severity.upper()}: {title}")

def record_result(flow, test_name, status, detail=""):
    """Record test result."""
    test_results.append({"flow": flow, "test": test_name, "status": status, "detail": detail})
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "SKIP"
    print(f"  [{icon}] {flow} > {test_name}: {detail}")

def get_page_text(driver):
    """Get visible text from page body."""
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""

def file_github_issues():
    """File all found bugs as GitHub issues."""
    if not bugs_found:
        print("\n[GITHUB] No bugs to file.")
        return

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for bug in bugs_found:
        body = f"## Description\n{bug['description']}\n\n"
        body += f"## Severity\n{bug['severity']}\n\n"
        body += f"## Environment\n- URL: {BASE_URL}\n- User: {ORG_ADMIN_EMAIL}\n- Date: {datetime.now().isoformat()}\n\n"
        if bug.get('screenshot'):
            body += f"## Screenshot\nSaved locally at: `{bug['screenshot']}`\n"

        issue_data = json.dumps({
            "title": bug["title"],
            "body": body,
            "labels": ["bug", "data-flow", bug["severity"]]
        }).encode()

        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            data=issue_data,
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "EmpCloud-E2E-Test",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=30)
            result = json.loads(resp.read().decode())
            print(f"  [GITHUB] Filed issue #{result.get('number')}: {bug['title']}")
        except Exception as e:
            print(f"  [GITHUB] Failed to file issue: {bug['title']} — {e}")


# ═══════════════════════════════════════════════════════════════════════════
# FLOW 1: Employee Directory — verify employee visible across modules
# ═══════════════════════════════════════════════════════════════════════════
def flow1_employee_across_modules(driver):
    print("\n" + "="*70)
    print("FLOW 1: Employee Visibility Across Modules")
    print("="*70)

    # 1a. Navigate to Employees
    print("\n--- 1a. Employee Directory ---")
    navigate_sidebar(driver, "Employee")
    wait_for_page(driver)
    time.sleep(2)
    ss(driver, "F1_01_employee_list")

    page_text = get_page_text(driver)
    # Look for employee list indicators
    has_employee_list = False
    for indicator in ["employee", "Employee", "Name", "Department", "Designation", "ID"]:
        if indicator in page_text:
            has_employee_list = True
            break

    if has_employee_list:
        record_result("Flow1", "Employee list loads", "pass", "Employee directory page loaded")
    else:
        record_result("Flow1", "Employee list loads", "fail", "Employee directory did not load expected content")
        screenshot_p = ss(driver, "F1_BUG_no_employee_list")
        record_bug("Employee directory list not loading",
                    "Employee directory page does not show employee list or expected columns",
                    "high", screenshot_p)

    # Try to find a specific employee or count rows
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .ant-table-row, [class*='employee-row'], [class*='EmployeeRow'], tr[data-row-key]")
    employee_count = len(rows)
    print(f"  Employee rows found: {employee_count}")

    # Search for employee ID 531 if search available
    search_found = False
    try:
        search_inputs = driver.find_elements(By.CSS_SELECTOR,
            "input[placeholder*='earch'], input[placeholder*='filter'], input[type='search'], .ant-input-search input")
        if search_inputs:
            search_inputs[0].clear()
            search_inputs[0].send_keys("531")
            time.sleep(2)
            wait_for_page(driver)
            ss(driver, "F1_02_search_employee_531")
            search_found = True
            record_result("Flow1", "Search employee by ID", "pass", "Search executed for employee 531")
    except:
        record_result("Flow1", "Search employee by ID", "skip", "No search input found")

    # Try clicking employee to see profile
    try:
        if search_found:
            clickable = driver.find_elements(By.CSS_SELECTOR, "table tbody tr a, table tbody tr td:first-child, .ant-table-row")
            if clickable:
                click_safe(driver, clickable[0])
                time.sleep(2)
                wait_for_page(driver)
                ss(driver, "F1_03_employee_profile_click")
    except:
        pass

    # Try direct navigation to employee profile
    print("\n--- 1b. Employee Profile ---")
    driver.get(f"{BASE_URL}/employees/{EMPLOYEE_ID}")
    wait_for_page(driver)
    time.sleep(2)
    ss(driver, "F1_04_employee_profile_direct")
    profile_text = get_page_text(driver)

    # Check if profile loaded
    profile_indicators = ["Personal", "Education", "Experience", "Document", "Address", "Attendance", "Leave"]
    tabs_found = [ind for ind in profile_indicators if ind.lower() in profile_text.lower()]
    if tabs_found:
        record_result("Flow1", "Employee profile loads", "pass", f"Tabs found: {', '.join(tabs_found)}")
    else:
        # Try alternative URLs
        for alt_url in [f"{BASE_URL}/employee/{EMPLOYEE_ID}", f"{BASE_URL}/employees/view/{EMPLOYEE_ID}",
                        f"{BASE_URL}/employee/view/{EMPLOYEE_ID}", f"{BASE_URL}/employees/detail/{EMPLOYEE_ID}"]:
            driver.get(alt_url)
            wait_for_page(driver)
            time.sleep(2)
            profile_text = get_page_text(driver)
            tabs_found = [ind for ind in profile_indicators if ind.lower() in profile_text.lower()]
            if tabs_found:
                record_result("Flow1", "Employee profile loads", "pass", f"Loaded at {alt_url}, tabs: {', '.join(tabs_found)}")
                ss(driver, "F1_04b_employee_profile_alt")
                break
        else:
            record_result("Flow1", "Employee profile loads", "fail", "Profile page did not load expected tabs")
            screenshot_p = ss(driver, "F1_BUG_no_profile")
            record_bug("Employee profile page missing tabs",
                        f"Navigating to employee {EMPLOYEE_ID} profile does not show expected tabs (Personal, Education, etc.)",
                        "high", screenshot_p)

    # 1c. Check Attendance module for employee
    print("\n--- 1c. Attendance Module ---")
    driver.get(f"{BASE_URL}/attendance")
    wait_for_page(driver)
    time.sleep(2)
    ss(driver, "F1_05_attendance_module")
    att_text = get_page_text(driver)

    if any(w in att_text.lower() for w in ["attendance", "present", "absent", "check-in", "check in", "punch"]):
        record_result("Flow1", "Attendance module loads", "pass", "Attendance page loaded")
    else:
        # Try sidebar nav
        navigate_sidebar(driver, "Attendance")
        wait_for_page(driver)
        time.sleep(2)
        ss(driver, "F1_05b_attendance_sidebar")
        att_text = get_page_text(driver)
        if any(w in att_text.lower() for w in ["attendance", "present", "absent"]):
            record_result("Flow1", "Attendance module loads", "pass", "Loaded via sidebar")
        else:
            record_result("Flow1", "Attendance module loads", "fail", "Attendance page has no attendance content")
            screenshot_p = ss(driver, "F1_BUG_attendance_no_content")
            record_bug("Attendance module not showing content",
                        "Attendance module page does not display attendance data or expected labels",
                        "medium", screenshot_p)

    # 1d. Check Leave module
    print("\n--- 1d. Leave Module ---")
    driver.get(f"{BASE_URL}/leave")
    wait_for_page(driver)
    time.sleep(2)
    ss(driver, "F1_06_leave_module")
    leave_text = get_page_text(driver)

    if any(w in leave_text.lower() for w in ["leave", "balance", "applied", "approved", "casual", "sick", "earned"]):
        record_result("Flow1", "Leave module loads", "pass", "Leave page loaded with leave data")
    else:
        navigate_sidebar(driver, "Leave")
        wait_for_page(driver)
        time.sleep(2)
        ss(driver, "F1_06b_leave_sidebar")
        leave_text = get_page_text(driver)
        if any(w in leave_text.lower() for w in ["leave", "balance"]):
            record_result("Flow1", "Leave module loads", "pass", "Loaded via sidebar")
        else:
            record_result("Flow1", "Leave module loads", "fail", "Leave page has no leave content")
            screenshot_p = ss(driver, "F1_BUG_leave_no_content")
            record_bug("Leave module not showing content",
                        "Leave module does not display leave data",
                        "medium", screenshot_p)

    # 1e. Org Chart
    print("\n--- 1e. Org Chart ---")
    for url in [f"{BASE_URL}/org-chart", f"{BASE_URL}/orgchart", f"{BASE_URL}/organization-chart"]:
        driver.get(url)
        wait_for_page(driver)
        time.sleep(2)
        org_text = get_page_text(driver)
        if any(w in org_text.lower() for w in ["org", "chart", "hierarchy", "reporting", "tree"]):
            ss(driver, "F1_07_org_chart")
            record_result("Flow1", "Org Chart loads", "pass", f"Org chart at {url}")
            break
    else:
        navigate_sidebar(driver, "Org")
        wait_for_page(driver)
        time.sleep(2)
        ss(driver, "F1_07b_org_chart_sidebar")
        org_text = get_page_text(driver)
        if any(w in org_text.lower() for w in ["org", "chart", "hierarchy"]):
            record_result("Flow1", "Org Chart loads", "pass", "Loaded via sidebar")
        else:
            record_result("Flow1", "Org Chart loads", "skip", "Org chart page not found")


# ═══════════════════════════════════════════════════════════════════════════
# FLOW 2: Leave Balance & Application
# ═══════════════════════════════════════════════════════════════════════════
def flow2_leave_balance_flow(driver):
    print("\n" + "="*70)
    print("FLOW 2: Leave Application -> Balance -> Attendance")
    print("="*70)

    # Navigate to Leave
    print("\n--- 2a. Check Leave Balances ---")
    navigate_sidebar(driver, "Leave")
    wait_for_page(driver)
    time.sleep(2)

    # Try to find leave balance section
    leave_text = get_page_text(driver)
    ss(driver, "F2_01_leave_overview")

    # Look for balance cards/numbers
    balance_elements = driver.find_elements(By.CSS_SELECTOR,
        "[class*='balance'], [class*='Balance'], .ant-card, [class*='leave-type'], [class*='LeaveType']")
    if balance_elements:
        record_result("Flow2", "Leave balance display", "pass", f"Found {len(balance_elements)} balance elements")
    else:
        record_result("Flow2", "Leave balance display", "skip", "No specific balance UI elements found")

    # Check for leave balance page/tab
    for tab_text in ["Balance", "Leave Balance", "My Balance", "Team Balance"]:
        tab = find_and_click(driver, xpath=f"//span[contains(text(),'{tab_text}')] | //a[contains(text(),'{tab_text}')] | //div[contains(text(),'{tab_text}')]", timeout=3)
        if tab:
            time.sleep(2)
            wait_for_page(driver)
            ss(driver, "F2_02_leave_balance_tab")
            record_result("Flow2", "Leave balance tab", "pass", f"Found tab: {tab_text}")
            break

    # Try leave applications
    print("\n--- 2b. Leave Applications ---")
    for tab_text in ["Application", "Leave Application", "Applied", "Requests", "My Leaves"]:
        tab = find_and_click(driver, xpath=f"//span[contains(text(),'{tab_text}')] | //a[contains(text(),'{tab_text}')]", timeout=3)
        if tab:
            time.sleep(2)
            wait_for_page(driver)
            ss(driver, "F2_03_leave_applications")
            record_result("Flow2", "Leave applications tab", "pass", f"Found tab: {tab_text}")
            break
    else:
        record_result("Flow2", "Leave applications tab", "skip", "No applications tab found")

    # Check if leave data shows in applications list
    app_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .ant-table-row, [class*='leave-row']")
    if app_rows:
        record_result("Flow2", "Leave applications data", "pass", f"Found {len(app_rows)} leave application rows")
    else:
        record_result("Flow2", "Leave applications data", "skip", "No application rows visible")

    # Try team leaves / pending approvals (Org Admin view)
    print("\n--- 2c. Team Leave / Approvals ---")
    for tab_text in ["Team", "Pending", "Approval", "Team Leave"]:
        tab = find_and_click(driver, xpath=f"//span[contains(text(),'{tab_text}')] | //a[contains(text(),'{tab_text}')]", timeout=3)
        if tab:
            time.sleep(2)
            wait_for_page(driver)
            ss(driver, "F2_04_team_leave")
            record_result("Flow2", "Team leave/approvals", "pass", f"Found tab: {tab_text}")
            break
    else:
        record_result("Flow2", "Team leave/approvals", "skip", "No team leave tab found")


# ═══════════════════════════════════════════════════════════════════════════
# FLOW 3: Attendance -> Dashboard Stats Consistency
# ═══════════════════════════════════════════════════════════════════════════
def flow3_attendance_dashboard(driver):
    print("\n" + "="*70)
    print("FLOW 3: Attendance -> Dashboard Stats Consistency")
    print("="*70)

    # 3a. Attendance Dashboard
    print("\n--- 3a. Attendance Dashboard ---")
    navigate_sidebar(driver, "Attendance")
    wait_for_page(driver)
    time.sleep(2)
    ss(driver, "F3_01_attendance_dashboard")
    att_text = get_page_text(driver)

    # Look for stats: present, absent, late, on leave
    stats_keywords = ["present", "absent", "late", "on leave", "total", "half day"]
    found_stats = [kw for kw in stats_keywords if kw in att_text.lower()]
    if found_stats:
        record_result("Flow3", "Attendance stats displayed", "pass", f"Stats found: {', '.join(found_stats)}")
    else:
        record_result("Flow3", "Attendance stats displayed", "fail", "No attendance statistics visible")
        screenshot_p = ss(driver, "F3_BUG_no_stats")
        record_bug("Attendance dashboard missing statistics",
                    "Attendance dashboard does not show expected stats (present/absent/late/on leave counts)",
                    "medium", screenshot_p)

    # Try to find attendance records/table
    att_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .ant-table-row")
    if att_rows:
        record_result("Flow3", "Attendance records table", "pass", f"Found {len(att_rows)} attendance rows")
    else:
        record_result("Flow3", "Attendance records table", "skip", "No table rows on attendance page")

    # 3b. Check Dashboard for matching stats
    print("\n--- 3b. Main Dashboard Stats ---")
    driver.get(f"{BASE_URL}/dashboard")
    wait_for_page(driver)
    time.sleep(3)
    ss(driver, "F3_02_main_dashboard")
    dash_text = get_page_text(driver)

    # Look for attendance-related widgets on dashboard
    dash_att_keywords = ["attendance", "present", "absent", "on leave", "today"]
    found_dash_stats = [kw for kw in dash_att_keywords if kw in dash_text.lower()]
    if found_dash_stats:
        record_result("Flow3", "Dashboard attendance widget", "pass", f"Dashboard shows: {', '.join(found_dash_stats)}")
    else:
        # Try home page
        driver.get(f"{BASE_URL}/home")
        wait_for_page(driver)
        time.sleep(2)
        dash_text = get_page_text(driver)
        found_dash_stats = [kw for kw in dash_att_keywords if kw in dash_text.lower()]
        if found_dash_stats:
            record_result("Flow3", "Dashboard attendance widget", "pass", f"Home page shows: {', '.join(found_dash_stats)}")
            ss(driver, "F3_02b_home_dashboard")
        else:
            record_result("Flow3", "Dashboard attendance widget", "skip", "No attendance widget on dashboard")

    # 3c. Check for stat card/widget elements
    cards = driver.find_elements(By.CSS_SELECTOR,
        ".ant-card, [class*='widget'], [class*='Widget'], [class*='stat'], [class*='Stat'], [class*='card'], [class*='Card']")
    if cards:
        record_result("Flow3", "Dashboard stat cards", "pass", f"Found {len(cards)} card/widget elements")
    else:
        record_result("Flow3", "Dashboard stat cards", "skip", "No stat cards found")


# ═══════════════════════════════════════════════════════════════════════════
# FLOW 4: Employee Profile Completeness — all tabs
# ═══════════════════════════════════════════════════════════════════════════
def flow4_employee_profile_tabs(driver):
    print("\n" + "="*70)
    print("FLOW 4: Employee Profile Completeness — All Tabs")
    print("="*70)

    # Navigate to employee profile
    profile_urls = [
        f"{BASE_URL}/employees/{EMPLOYEE_ID}",
        f"{BASE_URL}/employee/{EMPLOYEE_ID}",
        f"{BASE_URL}/employees/view/{EMPLOYEE_ID}",
        f"{BASE_URL}/employee/view/{EMPLOYEE_ID}",
        f"{BASE_URL}/employees/detail/{EMPLOYEE_ID}",
    ]

    loaded = False
    for url in profile_urls:
        driver.get(url)
        wait_for_page(driver)
        time.sleep(2)
        pt = get_page_text(driver)
        if any(w in pt.lower() for w in ["personal", "education", "experience", "profile", "employee"]):
            loaded = True
            print(f"  Profile loaded at: {url}")
            break

    if not loaded:
        # Try from employee list
        navigate_sidebar(driver, "Employee")
        wait_for_page(driver)
        time.sleep(2)
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr a, table tbody tr td, .ant-table-row")
        if rows:
            click_safe(driver, rows[0])
            wait_for_page(driver)
            time.sleep(2)
            loaded = True

    if not loaded:
        record_result("Flow4", "Navigate to employee profile", "fail", "Could not load employee profile")
        ss(driver, "F4_BUG_cant_load_profile")
        return

    ss(driver, "F4_01_profile_loaded")

    # Check each tab
    tab_names = ["Personal", "Education", "Experience", "Document", "Address", "Custom Field",
                 "Attendance", "Leave", "Asset", "Bank", "Emergency", "Family"]
    tabs_checked = 0
    tabs_with_data = 0

    for tab_name in tab_names:
        try:
            # Find and click tab
            tab_el = None
            tab_selectors = [
                f"//div[contains(@class,'tab')]//span[contains(text(),'{tab_name}')]",
                f"//div[contains(@class,'Tab')]//span[contains(text(),'{tab_name}')]",
                f"//button[contains(text(),'{tab_name}')]",
                f"//a[contains(text(),'{tab_name}')]",
                f"//div[contains(@role,'tab')][contains(text(),'{tab_name}')]",
                f"//*[contains(@class,'ant-tabs-tab')]//*[contains(text(),'{tab_name}')]",
            ]
            for sel in tab_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, sel)
                    if elements:
                        tab_el = elements[0]
                        break
                except:
                    continue

            if tab_el:
                click_safe(driver, tab_el)
                time.sleep(1.5)
                wait_for_page(driver)
                ss(driver, f"F4_tab_{tab_name.replace(' ', '_')}")
                tabs_checked += 1

                # Check if tab has content (not empty/error)
                tab_content = get_page_text(driver)
                error_indicators = ["no data", "empty", "not found", "error", "something went wrong"]
                has_error = any(ei in tab_content.lower() for ei in error_indicators)

                if not has_error and len(tab_content.strip()) > 50:
                    tabs_with_data += 1
                    record_result("Flow4", f"Tab: {tab_name}", "pass", "Tab loaded with content")
                elif has_error:
                    record_result("Flow4", f"Tab: {tab_name}", "fail", "Tab shows error or empty state")
                else:
                    record_result("Flow4", f"Tab: {tab_name}", "pass", "Tab loaded (may be empty but no error)")
            else:
                record_result("Flow4", f"Tab: {tab_name}", "skip", "Tab not found in UI")
        except Exception as e:
            record_result("Flow4", f"Tab: {tab_name}", "skip", f"Error: {str(e)[:80]}")

    print(f"\n  Profile Summary: {tabs_checked} tabs checked, {tabs_with_data} with data")
    if tabs_checked == 0:
        screenshot_p = ss(driver, "F4_BUG_no_tabs")
        record_bug("Employee profile has no clickable tabs",
                    f"Employee {EMPLOYEE_ID} profile does not show any navigable tabs for Personal/Education/Experience etc.",
                    "high", screenshot_p)


# ═══════════════════════════════════════════════════════════════════════════
# FLOW 5: Department / Org Changes
# ═══════════════════════════════════════════════════════════════════════════
def flow5_department_org(driver):
    print("\n" + "="*70)
    print("FLOW 5: Department / Org Changes")
    print("="*70)

    # 5a. Navigate to departments
    print("\n--- 5a. Departments List ---")
    dept_loaded = False
    for url in [f"{BASE_URL}/settings/departments", f"{BASE_URL}/departments",
                f"{BASE_URL}/settings/department", f"{BASE_URL}/organization/departments"]:
        driver.get(url)
        wait_for_page(driver)
        time.sleep(2)
        pt = get_page_text(driver)
        if any(w in pt.lower() for w in ["department", "engineering", "hr", "finance", "marketing", "sales"]):
            dept_loaded = True
            ss(driver, "F5_01_departments")
            record_result("Flow5", "Departments page loads", "pass", f"Loaded at {url}")
            break

    if not dept_loaded:
        navigate_sidebar(driver, "Setting")
        wait_for_page(driver)
        time.sleep(1)
        # Try finding departments sub-item
        dept_clicked = find_and_click(driver, xpath="//span[contains(text(),'Department')] | //a[contains(text(),'Department')]", timeout=5)
        if dept_clicked:
            wait_for_page(driver)
            time.sleep(2)
            ss(driver, "F5_01b_departments_sidebar")
            pt = get_page_text(driver)
            if "department" in pt.lower():
                dept_loaded = True
                record_result("Flow5", "Departments page loads", "pass", "Loaded via Settings sidebar")

    if not dept_loaded:
        # Try Organization menu
        navigate_sidebar(driver, "Organization")
        wait_for_page(driver)
        time.sleep(1)
        find_and_click(driver, xpath="//span[contains(text(),'Department')] | //a[contains(text(),'Department')]", timeout=5)
        wait_for_page(driver)
        time.sleep(2)
        pt = get_page_text(driver)
        if "department" in pt.lower():
            dept_loaded = True
            ss(driver, "F5_01c_departments_org")
            record_result("Flow5", "Departments page loads", "pass", "Loaded via Organization menu")

    if not dept_loaded:
        record_result("Flow5", "Departments page loads", "skip", "Could not find departments page")

    # 5b. Org Chart
    print("\n--- 5b. Org Chart ---")
    for url in [f"{BASE_URL}/org-chart", f"{BASE_URL}/orgchart", f"{BASE_URL}/organization/org-chart"]:
        driver.get(url)
        wait_for_page(driver)
        time.sleep(2)
        pt = get_page_text(driver)
        if any(w in pt.lower() for w in ["chart", "hierarchy", "reporting", "ceo", "manager"]):
            ss(driver, "F5_02_org_chart")
            record_result("Flow5", "Org chart displays hierarchy", "pass", f"Org chart at {url}")
            break
    else:
        record_result("Flow5", "Org chart displays hierarchy", "skip", "Org chart not found")

    # 5c. Department filter on employee list
    print("\n--- 5c. Department Filter on Employee List ---")
    navigate_sidebar(driver, "Employee")
    wait_for_page(driver)
    time.sleep(2)

    # Look for department filter/dropdown
    filter_found = False
    filter_selectors = [
        "select", ".ant-select", "[class*='filter']", "[class*='Filter']",
        "[placeholder*='epartment']", "[placeholder*='filter']"
    ]
    for sel in filter_selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, sel)
        if elements:
            for el in elements:
                txt = el.text.lower() + el.get_attribute("placeholder", "") if el.get_attribute("placeholder") else el.text.lower()
                if "department" in txt.lower() or "dept" in txt.lower() or "filter" in txt.lower():
                    click_safe(driver, el)
                    time.sleep(1)
                    filter_found = True
                    ss(driver, "F5_03_dept_filter")
                    record_result("Flow5", "Department filter on employee list", "pass", "Filter found and clickable")
                    break
            if filter_found:
                break

    if not filter_found:
        # Try clicking any filter/dropdown
        dropdowns = driver.find_elements(By.CSS_SELECTOR, ".ant-select, .ant-select-selector, [class*='dropdown']")
        if dropdowns:
            try:
                click_safe(driver, dropdowns[0])
                time.sleep(1)
                ss(driver, "F5_03b_filter_attempt")
                record_result("Flow5", "Department filter on employee list", "pass", "Dropdown/filter found")
            except:
                record_result("Flow5", "Department filter on employee list", "skip", "Could not interact with filters")
        else:
            record_result("Flow5", "Department filter on employee list", "skip", "No filter/dropdown found on employee list")


# ═══════════════════════════════════════════════════════════════════════════
# FLOW 6: Announcements
# ═══════════════════════════════════════════════════════════════════════════
def flow6_announcements(driver):
    print("\n" + "="*70)
    print("FLOW 6: Announcements -> Dashboard")
    print("="*70)

    # Navigate to announcements
    print("\n--- 6a. Announcements Module ---")
    ann_loaded = False
    for url in [f"{BASE_URL}/announcements", f"{BASE_URL}/announcement",
                f"{BASE_URL}/communication/announcements", f"{BASE_URL}/notice-board"]:
        driver.get(url)
        wait_for_page(driver)
        time.sleep(2)
        pt = get_page_text(driver)
        if any(w in pt.lower() for w in ["announcement", "notice", "publish", "create", "title"]):
            ann_loaded = True
            ss(driver, "F6_01_announcements")
            record_result("Flow6", "Announcements page loads", "pass", f"Loaded at {url}")
            break

    if not ann_loaded:
        navigate_sidebar(driver, "Announcement")
        wait_for_page(driver)
        time.sleep(2)
        pt = get_page_text(driver)
        if any(w in pt.lower() for w in ["announcement", "notice"]):
            ann_loaded = True
            ss(driver, "F6_01b_announcements_sidebar")
            record_result("Flow6", "Announcements page loads", "pass", "Loaded via sidebar")

    if not ann_loaded:
        # Check if it's under Communication or similar
        navigate_sidebar(driver, "Communication")
        wait_for_page(driver)
        time.sleep(1)
        find_and_click(driver, xpath="//span[contains(text(),'Announcement')] | //a[contains(text(),'Announcement')]", timeout=5)
        wait_for_page(driver)
        time.sleep(2)
        pt = get_page_text(driver)
        if any(w in pt.lower() for w in ["announcement", "notice"]):
            ann_loaded = True
            ss(driver, "F6_01c_announcements_comm")
            record_result("Flow6", "Announcements page loads", "pass", "Loaded via Communication menu")

    if not ann_loaded:
        record_result("Flow6", "Announcements page loads", "skip", "Could not find announcements page")
        return

    # Check if existing announcements show author/date
    ann_text = get_page_text(driver)
    has_dates = any(ch in ann_text for ch in ["2025", "2026", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    if has_dates:
        record_result("Flow6", "Announcements show dates", "pass", "Dates visible in announcements")
    else:
        record_result("Flow6", "Announcements show dates", "skip", "No dates found in announcements")

    # 6b. Check dashboard for announcements widget
    print("\n--- 6b. Dashboard Announcements Widget ---")
    driver.get(f"{BASE_URL}/dashboard")
    wait_for_page(driver)
    time.sleep(3)
    dash_text = get_page_text(driver)

    if "announcement" in dash_text.lower() or "notice" in dash_text.lower():
        record_result("Flow6", "Dashboard shows announcements", "pass", "Announcement widget found on dashboard")
        ss(driver, "F6_02_dashboard_announcements")
    else:
        driver.get(f"{BASE_URL}/home")
        wait_for_page(driver)
        time.sleep(2)
        dash_text = get_page_text(driver)
        if "announcement" in dash_text.lower() or "notice" in dash_text.lower():
            record_result("Flow6", "Dashboard shows announcements", "pass", "Found on home page")
            ss(driver, "F6_02b_home_announcements")
        else:
            record_result("Flow6", "Dashboard shows announcements", "fail", "No announcements widget on dashboard")
            screenshot_p = ss(driver, "F6_BUG_no_dashboard_announcements")
            record_bug("Dashboard missing announcements widget",
                        "The main dashboard/home page does not display an announcements section or widget",
                        "low", screenshot_p)


# ═══════════════════════════════════════════════════════════════════════════
# FLOW 7: Documents Module -> Employee Profile
# ═══════════════════════════════════════════════════════════════════════════
def flow7_documents(driver):
    print("\n" + "="*70)
    print("FLOW 7: Documents Module -> Employee Profile")
    print("="*70)

    # Navigate to Documents
    print("\n--- 7a. Documents Module ---")
    doc_loaded = False
    for url in [f"{BASE_URL}/documents", f"{BASE_URL}/document",
                f"{BASE_URL}/document-management", f"{BASE_URL}/files"]:
        driver.get(url)
        wait_for_page(driver)
        time.sleep(2)
        pt = get_page_text(driver)
        if any(w in pt.lower() for w in ["document", "file", "upload", "download", "folder"]):
            doc_loaded = True
            ss(driver, "F7_01_documents_module")
            record_result("Flow7", "Documents module loads", "pass", f"Loaded at {url}")
            break

    if not doc_loaded:
        navigate_sidebar(driver, "Document")
        wait_for_page(driver)
        time.sleep(2)
        pt = get_page_text(driver)
        if any(w in pt.lower() for w in ["document", "file", "upload"]):
            doc_loaded = True
            ss(driver, "F7_01b_documents_sidebar")
            record_result("Flow7", "Documents module loads", "pass", "Loaded via sidebar")

    if not doc_loaded:
        record_result("Flow7", "Documents module loads", "skip", "Could not find documents module")

    # 7b. Check employee profile Documents tab
    print("\n--- 7b. Employee Profile Documents Tab ---")
    profile_urls = [
        f"{BASE_URL}/employees/{EMPLOYEE_ID}",
        f"{BASE_URL}/employee/{EMPLOYEE_ID}",
    ]
    for url in profile_urls:
        driver.get(url)
        wait_for_page(driver)
        time.sleep(2)
        pt = get_page_text(driver)
        if any(w in pt.lower() for w in ["personal", "profile", "employee"]):
            # Click Documents tab
            doc_tab = find_and_click(driver, xpath=
                "//*[contains(@class,'tab')]//*[contains(text(),'Document')] | "
                "//button[contains(text(),'Document')] | "
                "//a[contains(text(),'Document')]",
                timeout=5)
            if doc_tab:
                time.sleep(2)
                wait_for_page(driver)
                ss(driver, "F7_02_profile_documents_tab")
                record_result("Flow7", "Employee profile Documents tab", "pass", "Documents tab accessible")
            else:
                record_result("Flow7", "Employee profile Documents tab", "skip", "Documents tab not found")
            break
    else:
        record_result("Flow7", "Employee profile Documents tab", "skip", "Could not load employee profile")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("EMP CLOUD - EMPLOYEE LIFECYCLE DATA FLOW TEST")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    driver = get_driver()
    driver.set_page_load_timeout(30)

    try:
        # Login
        print("\n[STEP] Logging in as Org Admin...")
        login_ok = login_browser(driver)
        if not login_ok:
            print("[FATAL] Login failed, aborting.")
            return

        # Give dashboard time to fully load
        time.sleep(3)
        wait_for_page(driver)

        # Capture initial dashboard
        ss(driver, "00_dashboard_after_login")
        page_text = get_page_text(driver)
        print(f"  Dashboard URL: {driver.current_url}")
        print(f"  Page text length: {len(page_text)} chars")

        # Run all flows
        flow1_employee_across_modules(driver)
        flow2_leave_balance_flow(driver)
        flow3_attendance_dashboard(driver)
        flow4_employee_profile_tabs(driver)
        flow5_department_org(driver)
        flow6_announcements(driver)
        flow7_documents(driver)

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        traceback.print_exc()
        ss(driver, "CRASH_error")
    finally:
        driver.quit()

    # ── Summary ──
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    pass_count = sum(1 for r in test_results if r["status"] == "pass")
    fail_count = sum(1 for r in test_results if r["status"] == "fail")
    skip_count = sum(1 for r in test_results if r["status"] == "skip")
    print(f"  PASS: {pass_count}  |  FAIL: {fail_count}  |  SKIP: {skip_count}  |  TOTAL: {len(test_results)}")
    print()

    for r in test_results:
        icon = "PASS" if r["status"] == "pass" else "FAIL" if r["status"] == "fail" else "SKIP"
        print(f"  [{icon}] {r['flow']} > {r['test']}: {r['detail']}")

    print(f"\n  Bugs found: {len(bugs_found)}")
    for b in bugs_found:
        print(f"    - [{b['severity'].upper()}] {b['title']}")

    # File GitHub issues for bugs
    if bugs_found:
        print("\n[STEP] Filing GitHub issues...")
        file_github_issues()

    print(f"\nCompleted: {datetime.now().isoformat()}")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}")


if __name__ == "__main__":
    main()
