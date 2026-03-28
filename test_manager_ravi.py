"""
Ravi Kumar's Manager Day — EMP Cloud Manager Experience Test
Simulates a Team Lead/Manager's daily interactions with the HRMS:
 - Dashboard "My Team" section
 - Team attendance & leave approvals
 - Team member profiles, leave balances
 - Performance reviews (SSO), Rewards, Events, Helpdesk
 - Comp-off approvals, team reports, whistleblowing
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import json
import time
import datetime
import traceback
import requests
import base64
from pathlib import Path
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

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL  = "https://test-empcloud-api.empcloud.com"
EMAIL    = "ananya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT  = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = Path(r"C:\Users\Admin\screenshots\manager_ravi")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

# SSO modules
PERFORMANCE_URL = "https://test-performance.empcloud.com"
REWARDS_URL     = "https://test-rewards.empcloud.com"
PROJECT_URL     = "https://test-project.empcloud.com"

issues_found = []
test_results = []
test_count = 0
driver = None
auth_token = None

# ── Helpers ─────────────────────────────────────────────────────────────────

def get_driver():
    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    svc = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(5)
    return d


def restart_driver_if_needed():
    global driver, test_count
    test_count += 1
    if test_count % 3 == 0 and driver:
        try:
            driver.quit()
        except:
            pass
        driver = get_driver()
        login_ui(driver)
    return driver


def ensure_driver():
    global driver
    if driver is None:
        driver = get_driver()
    return driver


def screenshot(name):
    ts = datetime.datetime.now().strftime("%H%M%S")
    fname = f"{ts}_{name}.png"
    fpath = SCREENSHOT_DIR / fname
    try:
        driver.save_screenshot(str(fpath))
        print(f"    [screenshot] {fpath}")
        return fpath
    except Exception as e:
        print(f"    [screenshot failed] {e}")
        return None


def upload_screenshot_to_github(filepath):
    if not filepath or not Path(filepath).exists():
        return None
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        fname = Path(filepath).name
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/manager_ravi/{fname}"
        headers = {
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json"
        }
        resp = requests.put(url, headers=headers, json={
            "message": f"Upload screenshot: {fname}",
            "content": content,
            "branch": "main"
        }, timeout=30)
        if resp.status_code in (200, 201):
            return resp.json().get("content", {}).get("download_url", "")
        else:
            print(f"    [upload] HTTP {resp.status_code}")
            return None
    except Exception as e:
        print(f"    [upload error] {e}")
        return None


def file_github_issue(title, body, labels=None):
    if labels is None:
        labels = ["bug", "manager-experience"]
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }
    # Check for duplicates first
    try:
        search_resp = requests.get(
            f"https://api.github.com/search/issues",
            headers=headers,
            params={"q": f'repo:{GITHUB_REPO} is:issue state:open "{title[:60]}"'},
            timeout=15
        )
        if search_resp.status_code == 200:
            items = search_resp.json().get("items", [])
            if items:
                print(f"    [issue exists] {items[0]['html_url']}")
                issues_found.append({"title": title, "url": items[0]["html_url"], "existing": True})
                return items[0]["html_url"]
    except:
        pass

    payload = {"title": title, "body": body, "labels": labels}
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers=headers, json=payload, timeout=30
        )
        if resp.status_code == 201:
            issue_url = resp.json()["html_url"]
            print(f"    [issue filed] {issue_url}")
            issues_found.append({"title": title, "url": issue_url})
            return issue_url
        else:
            print(f"    [issue failed] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"    [issue error] {e}")
    return None


def record_issue(title, description, screenshot_path=None, labels=None):
    img_url = upload_screenshot_to_github(screenshot_path) if screenshot_path else None
    body = f"## Description\n{description}\n\n"
    body += f"**User:** Ananya (ananya@technova.in) acting as Manager/Team Lead\n"
    body += f"**Persona:** Ravi Kumar — Team Lead at TechNova Solutions\n"
    body += f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    body += f"**URL:** {driver.current_url if driver else 'N/A'}\n\n"
    if img_url:
        body += f"## Screenshot\n![screenshot]({img_url})\n\n"
    elif screenshot_path:
        body += f"## Screenshot\nLocal: `{screenshot_path}` (upload failed)\n\n"
    body += "## Steps to Reproduce\n1. Login as ananya@technova.in (org admin / manager)\n2. Navigate to the relevant section\n3. Observe the issue\n\n"
    body += "## Expected\nManagers should be able to manage their team efficiently.\n\n"
    body += "## Actual\n" + description + "\n"
    if labels is None:
        labels = ["bug", "manager-experience"]
    file_github_issue(title, body, labels)


def record_result(test_name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {test_name}: {details}")
    test_results.append({"test": test_name, "passed": passed, "details": details})


def wait_click(by, value, timeout=10):
    el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)
    return el


def wait_find(by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))


def wait_finds(by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located((by, value)))


def safe_navigate(url, wait_secs=3):
    try:
        driver.get(url)
        time.sleep(wait_secs)
    except Exception as e:
        print(f"    [nav error] {url}: {e}")


def page_text():
    try:
        return driver.find_element(By.TAG_NAME, "body").text.lower()
    except:
        return ""


def page_source():
    try:
        return driver.page_source.lower()
    except:
        return ""


# ── API Login ───────────────────────────────────────────────────────────────

def api_login():
    global auth_token
    try:
        resp = requests.post(f"{API_URL}/api/auth/login", json={
            "email": EMAIL, "password": PASSWORD
        }, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            auth_token = data.get("token") or data.get("data", {}).get("token") or data.get("accessToken")
            if not auth_token and isinstance(data.get("data"), dict):
                auth_token = data["data"].get("accessToken") or data["data"].get("access_token")
            print(f"  [API] Login OK, token: {str(auth_token)[:20]}...")
            return True
        else:
            print(f"  [API] Login failed: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  [API] Login error: {e}")
        return False


def api_get(path, params=None):
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    try:
        resp = requests.get(f"{API_URL}{path}", headers=headers, params=params, timeout=15)
        return resp
    except Exception as e:
        print(f"  [API GET error] {path}: {e}")
        return None


def api_post(path, json_data=None):
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    try:
        resp = requests.post(f"{API_URL}{path}", headers=headers, json=json_data, timeout=15)
        return resp
    except Exception as e:
        print(f"  [API POST error] {path}: {e}")
        return None


def api_put(path, json_data=None):
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    try:
        resp = requests.put(f"{API_URL}{path}", headers=headers, json=json_data, timeout=15)
        return resp
    except Exception as e:
        print(f"  [API PUT error] {path}: {e}")
        return None


# ── UI Login ────────────────────────────────────────────────────────────────

def login_ui(d):
    try:
        d.get(f"{BASE_URL}/login")
        time.sleep(3)
        email_input = None
        for sel in ["input[name='email']", "input[type='email']", "#email",
                     "input[placeholder*='mail']", "input[placeholder*='Email']"]:
            try:
                email_input = d.find_element(By.CSS_SELECTOR, sel)
                if email_input:
                    break
            except:
                continue

        if not email_input:
            inputs = d.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                t = inp.get_attribute("type") or ""
                if t in ("email", "text"):
                    email_input = inp
                    break

        if not email_input:
            print("  [login] Cannot find email input")
            return False

        email_input.clear()
        email_input.send_keys(EMAIL)
        time.sleep(0.5)

        pwd_input = None
        for sel in ["input[name='password']", "input[type='password']", "#password"]:
            try:
                pwd_input = d.find_element(By.CSS_SELECTOR, sel)
                if pwd_input:
                    break
            except:
                continue

        if pwd_input:
            pwd_input.clear()
            pwd_input.send_keys(PASSWORD)
            time.sleep(0.5)

        # Submit
        for sel in ["button[type='submit']", "button:not([type='button'])",
                     "input[type='submit']"]:
            try:
                btn = d.find_element(By.CSS_SELECTOR, sel)
                btn.click()
                break
            except:
                continue

        time.sleep(4)
        if "/login" not in d.current_url:
            print(f"  [login] OK — {d.current_url}")
            return True
        else:
            print("  [login] Still on login page")
            return False
    except Exception as e:
        print(f"  [login error] {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
#  TEST FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def test_01_login_and_dashboard_my_team():
    """Login — is there a 'My Team' section on dashboard?"""
    print("\n=== TEST 01: Login & Dashboard 'My Team' Section ===")
    global driver
    ensure_driver()
    ok = login_ui(driver)
    if not ok:
        record_result("Login", False, "Cannot login")
        return

    record_result("Login", True, f"Logged in at {driver.current_url}")
    shot = screenshot("01_dashboard")

    # Check for My Team / Team section on dashboard
    body = page_text()
    src = page_source()
    has_team_section = False
    team_keywords = ["my team", "team overview", "direct reports", "team members",
                     "team dashboard", "team summary", "team attendance",
                     "reporting to", "my reportees"]
    for kw in team_keywords:
        if kw in body or kw in src:
            has_team_section = True
            print(f"    Found team keyword: '{kw}'")
            break

    # Also look for team-related UI components
    team_elements = []
    for sel in [
        "[class*='team']", "[class*='Team']", "[id*='team']",
        "[data-testid*='team']", ".my-team", "#myTeam",
        "[class*='report']", "[class*='direct']"
    ]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                team_elements.extend(els)
        except:
            pass

    if has_team_section or team_elements:
        record_result("Dashboard My Team Section", True,
                      f"Found team section: {len(team_elements)} elements")
        shot2 = screenshot("01_team_section")
    else:
        record_result("Dashboard My Team Section", False,
                      "No 'My Team' or direct reports section visible on dashboard")
        shot = screenshot("01_no_team_section")
        record_issue(
            "Dashboard missing 'My Team' section for managers",
            "When a manager logs in, the dashboard does not display a 'My Team' section "
            "showing direct reports at a glance. Managers need quick visibility into their "
            "team's status (present/absent/on-leave) without navigating away from the dashboard.",
            shot
        )

    # Check for any quick stats — team attendance, pending approvals etc
    pending_keywords = ["pending", "approval", "request", "leave request"]
    found_pending = any(kw in body for kw in pending_keywords)
    if found_pending:
        record_result("Dashboard Pending Approvals", True, "Pending items visible on dashboard")
    else:
        record_result("Dashboard Pending Approvals", False, "No pending approval count on dashboard")


def test_02_manager_page():
    """Check /manager page — team members and today's attendance."""
    print("\n=== TEST 02: Manager Page ===")
    restart_driver_if_needed()

    # Try various manager-related URLs
    manager_urls = [
        f"{BASE_URL}/manager",
        f"{BASE_URL}/manager/dashboard",
        f"{BASE_URL}/my-team",
        f"{BASE_URL}/team",
        f"{BASE_URL}/team/dashboard",
        f"{BASE_URL}/manager/team",
    ]

    found_manager_page = False
    for url in manager_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        # Check if we got redirected back to login or got a 404-like page
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url

        if "/login" not in current and "404" not in body and "not found" not in body:
            found_manager_page = True
            print(f"    Manager page found at: {url} -> {current}")
            shot = screenshot("02_manager_page")
            break

    if not found_manager_page:
        record_result("Manager Page Exists", False, "No dedicated /manager page found")
        shot = screenshot("02_no_manager_page")
        record_issue(
            "No dedicated manager page or /manager route",
            "Navigating to /manager, /my-team, /team, or /manager/dashboard does not "
            "load a dedicated manager view. Managers need a central page to see their "
            "team members, today's attendance, and pending approvals.",
            shot
        )
        return

    # Check for team members list
    body = page_text()
    has_members = any(kw in body for kw in ["team member", "employee", "reportee", "member"])
    has_attendance = any(kw in body for kw in ["attendance", "present", "absent", "check-in",
                                                "checkin", "clock in", "on time", "late"])

    record_result("Manager Page Team Members", has_members,
                  "Team members visible" if has_members else "No team member list found")
    record_result("Manager Page Team Attendance", has_attendance,
                  "Attendance info visible" if has_attendance else "No attendance data on manager page")


def test_03_pending_leave_approvals():
    """Pending leave approvals — count, details, approve/reject."""
    print("\n=== TEST 03: Pending Leave Approvals ===")
    restart_driver_if_needed()

    # Try UI: navigate to leave approval pages
    leave_urls = [
        f"{BASE_URL}/leave/approvals",
        f"{BASE_URL}/leave/pending",
        f"{BASE_URL}/manager/leave-approvals",
        f"{BASE_URL}/leave/requests",
        f"{BASE_URL}/leave-management/approvals",
        f"{BASE_URL}/leaves/approval",
        f"{BASE_URL}/leave/approval",
    ]

    found_approvals = False
    for url in leave_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url
        if "/login" not in current and "404" not in body:
            # Check if it has relevant content
            if any(kw in body for kw in ["approval", "leave", "pending", "request", "approve", "reject"]):
                found_approvals = True
                print(f"    Leave approvals at: {current}")
                shot = screenshot("03_leave_approvals")
                break

    # Also try API
    api_approval_paths = [
        "/api/leave/approvals",
        "/api/leave/pending-approvals",
        "/api/leave/requests",
        "/api/v1/leave/approvals",
        "/api/v1/leave/pending",
        "/api/leaves/approval",
        "/api/leaves/pending",
        "/api/manager/leave-requests",
    ]
    api_approval_data = None
    for path in api_approval_paths:
        resp = api_get(path)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                print(f"    API {path}: {json.dumps(data)[:200]}")
                api_approval_data = data
                break
            except:
                pass

    if found_approvals:
        record_result("Leave Approvals Page", True, "Page found")

        # Check for approve/reject buttons
        body = page_text()
        src = page_source()
        has_approve_btn = "approve" in body or "approve" in src
        has_reject_btn = "reject" in body or "decline" in body or "reject" in src
        record_result("Leave Approve/Reject Buttons", has_approve_btn or has_reject_btn,
                      f"Approve: {has_approve_btn}, Reject: {has_reject_btn}")

        # Check for leave details (who, dates, type, reason)
        detail_keywords = {"name": False, "date": False, "type": False, "reason": False}
        for kw in detail_keywords:
            if kw in body:
                detail_keywords[kw] = True
        missing = [k for k, v in detail_keywords.items() if not v]
        if missing:
            record_result("Leave Request Details", False, f"Missing: {', '.join(missing)}")
        else:
            record_result("Leave Request Details", True, "All details visible")
    else:
        record_result("Leave Approvals Page", False, "No leave approvals page found")
        shot = screenshot("03_no_leave_approvals")
        record_issue(
            "Manager cannot find leave approvals page",
            "No accessible leave approval page found at common routes (/leave/approvals, "
            "/leave/pending, etc). Managers need to view, approve, or reject pending leave "
            "requests from their team.",
            shot
        )

    if api_approval_data:
        record_result("Leave Approvals API", True, f"API returned data")
    else:
        record_result("Leave Approvals API", False, "No working leave approval API endpoint found")


def test_04_team_attendance():
    """Team attendance — present, absent, late, date filter."""
    print("\n=== TEST 04: Team Attendance ===")
    restart_driver_if_needed()

    attendance_urls = [
        f"{BASE_URL}/attendance/team",
        f"{BASE_URL}/team/attendance",
        f"{BASE_URL}/manager/attendance",
        f"{BASE_URL}/attendance/report",
        f"{BASE_URL}/attendance",
    ]

    found_attendance = False
    for url in attendance_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url
        if "/login" not in current and "404" not in body:
            if any(kw in body for kw in ["attendance", "present", "absent", "check-in",
                                          "punch", "clock", "work hours"]):
                found_attendance = True
                print(f"    Team attendance at: {current}")
                shot = screenshot("04_team_attendance")
                break

    # API check
    att_api_paths = [
        "/api/attendance/team",
        "/api/v1/attendance/team",
        "/api/attendance/report",
        "/api/v1/attendance/report",
        "/api/manager/team-attendance",
        "/api/attendance",
    ]
    api_att_data = None
    today = datetime.date.today().isoformat()
    for path in att_api_paths:
        resp = api_get(path, params={"date": today})
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                print(f"    API {path}: {json.dumps(data)[:200]}")
                api_att_data = data
                break
            except:
                pass

    if found_attendance:
        record_result("Team Attendance Page", True, "Found")
        body = page_text()

        # Check for present/absent/late indicators
        has_status = any(kw in body for kw in ["present", "absent", "late", "on time", "half day"])
        record_result("Attendance Status Indicators", has_status,
                      "Status shown" if has_status else "No present/absent/late indicators")

        # Check for date filter
        src = page_source()
        has_date_filter = ("date" in src and ("input" in src or "picker" in src or "filter" in src))
        try:
            date_inputs = driver.find_elements(By.CSS_SELECTOR,
                "input[type='date'], input[class*='date'], input[placeholder*='date'], "
                ".date-picker, [class*='datepicker'], [class*='DatePicker']")
            if date_inputs:
                has_date_filter = True
        except:
            pass
        record_result("Attendance Date Filter", has_date_filter,
                      "Date filter found" if has_date_filter else "No date range filter")
        if not has_date_filter:
            record_issue(
                "Team attendance page missing date range filter",
                "The team attendance page does not have an obvious date range filter. "
                "Managers need to filter attendance data by date range to spot patterns.",
                screenshot("04_no_date_filter")
            )
    else:
        record_result("Team Attendance Page", False, "No team attendance page found")
        shot = screenshot("04_no_attendance")
        record_issue(
            "Manager cannot access team attendance view",
            "No team attendance page found at common routes. Managers need to see who is "
            "present, absent, or late today and filter by date range.",
            shot
        )

    if api_att_data:
        record_result("Team Attendance API", True, "API returned data")
    else:
        record_result("Team Attendance API", False, "No working team attendance API")


def test_05_team_leave_balances():
    """Can manager see team's leave balances? Who's running low?"""
    print("\n=== TEST 05: Team Leave Balances ===")
    restart_driver_if_needed()

    balance_urls = [
        f"{BASE_URL}/leave/team-balance",
        f"{BASE_URL}/leave/balances",
        f"{BASE_URL}/manager/leave-balances",
        f"{BASE_URL}/leave/team",
        f"{BASE_URL}/leave",
    ]

    found_balances = False
    for url in balance_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url
        if "/login" not in current and "404" not in body:
            if any(kw in body for kw in ["balance", "remaining", "available", "leave quota",
                                          "entitled", "used", "leave type"]):
                found_balances = True
                print(f"    Leave balances at: {current}")
                shot = screenshot("05_leave_balances")
                break

    # API
    balance_api_paths = [
        "/api/leave/team-balance",
        "/api/v1/leave/team-balance",
        "/api/leave/balances",
        "/api/v1/leave/balances",
        "/api/manager/leave-balances",
    ]
    api_balance_data = None
    for path in balance_api_paths:
        resp = api_get(path)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                print(f"    API {path}: {json.dumps(data)[:200]}")
                api_balance_data = data
                break
            except:
                pass

    if found_balances:
        record_result("Team Leave Balances", True, "Balance info visible")
    else:
        record_result("Team Leave Balances", False, "No team leave balance view found")
        shot = screenshot("05_no_balances")
        record_issue(
            "Manager cannot view team leave balances",
            "No page or section shows team members' leave balances. Managers need to "
            "see who is running low on leave to plan coverage and encourage time off.",
            shot
        )


def test_06_team_member_profiles():
    """Can manager view team member profiles? Click through to details?"""
    print("\n=== TEST 06: Team Member Profiles ===")
    restart_driver_if_needed()

    # Navigate to employee/team list
    team_urls = [
        f"{BASE_URL}/employees",
        f"{BASE_URL}/team/members",
        f"{BASE_URL}/my-team",
        f"{BASE_URL}/manager/team",
        f"{BASE_URL}/people",
        f"{BASE_URL}/directory",
    ]

    found_list = False
    for url in team_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url
        if "/login" not in current and "404" not in body:
            if any(kw in body for kw in ["employee", "member", "name", "email", "department"]):
                found_list = True
                print(f"    Team/employee list at: {current}")
                shot = screenshot("06_team_list")
                break

    if found_list:
        record_result("Team Member List", True, "Found")

        # Try clicking on a member to see profile
        try:
            # Look for clickable rows or links to profiles
            profile_links = driver.find_elements(By.CSS_SELECTOR,
                "a[href*='employee'], a[href*='profile'], a[href*='user'], "
                "tr[class*='clickable'], tr[role='button'], "
                "table tbody tr, .employee-card, [class*='member-card']")
            if profile_links:
                first = profile_links[0]
                try:
                    first.click()
                except:
                    driver.execute_script("arguments[0].click();", first)
                time.sleep(3)
                body2 = page_text()
                has_profile = any(kw in body2 for kw in ["profile", "details", "phone",
                                                          "address", "designation", "department",
                                                          "joining", "personal", "employment"])
                if has_profile:
                    record_result("Member Profile Click-Through", True, "Profile details accessible")
                    screenshot("06_member_profile")
                else:
                    record_result("Member Profile Click-Through", False,
                                  "Clicked but no profile details shown")
            else:
                record_result("Member Profile Click-Through", False, "No clickable employee entries")
        except Exception as e:
            record_result("Member Profile Click-Through", False, f"Error: {e}")
    else:
        record_result("Team Member List", False, "No team/employee list accessible")
        shot = screenshot("06_no_team_list")
        record_issue(
            "Manager cannot view team member profiles",
            "No accessible team/employee list found. Managers should be able to browse "
            "their direct reports and click through to view detailed profiles.",
            shot
        )


def test_07_performance_reviews_sso():
    """Performance reviews — SSO access, pending reviews."""
    print("\n=== TEST 07: Performance Reviews (SSO) ===")
    restart_driver_if_needed()

    # First try SSO link from main app
    safe_navigate(f"{BASE_URL}/performance")
    time.sleep(3)
    body = page_text()
    current = driver.current_url
    shot1 = screenshot("07_performance_from_main")

    # Check if redirected to performance module
    on_perf = "performance" in current.lower()

    # Try direct performance module
    safe_navigate(PERFORMANCE_URL)
    time.sleep(4)
    body = page_text()
    current = driver.current_url
    shot2 = screenshot("07_performance_direct")

    # Check for SSO - might land on login or might auto-login
    if "/login" in current:
        # Try SSO login
        login_ui(driver)
        safe_navigate(PERFORMANCE_URL)
        time.sleep(3)

    body = page_text()
    has_reviews = any(kw in body for kw in ["review", "performance", "appraisal", "goal",
                                             "rating", "assessment", "kpi", "okr", "feedback"])
    has_pending = any(kw in body for kw in ["pending", "due", "overdue", "to complete",
                                             "assigned", "in progress"])

    if has_reviews:
        record_result("Performance Module Access", True, f"At {driver.current_url}")
        record_result("Pending Reviews", has_pending,
                      "Pending reviews visible" if has_pending else "No pending reviews indicator")
        screenshot("07_performance_reviews")
    else:
        record_result("Performance Module Access", False, "Cannot access performance reviews")
        shot = screenshot("07_no_performance")
        record_issue(
            "Manager cannot access performance reviews via SSO",
            "Navigating to the Performance module does not SSO the manager in. "
            "Managers need seamless SSO access to review their team's performance.",
            shot
        )


def test_08_assign_tasks_projects():
    """Can manager assign tasks/projects to team members?"""
    print("\n=== TEST 08: Assign Tasks/Projects ===")
    restart_driver_if_needed()

    # Try Project module
    safe_navigate(PROJECT_URL)
    time.sleep(4)
    body = page_text()
    current = driver.current_url
    shot1 = screenshot("08_project_module")

    if "/login" in current:
        login_ui(driver)
        safe_navigate(PROJECT_URL)
        time.sleep(3)
        body = page_text()

    has_projects = any(kw in body for kw in ["project", "task", "assign", "board", "kanban",
                                              "sprint", "backlog", "milestone"])

    # Also check main app for task assignment
    safe_navigate(f"{BASE_URL}/tasks")
    time.sleep(2)
    body2 = page_text()
    safe_navigate(f"{BASE_URL}/projects")
    time.sleep(2)
    body3 = page_text()

    has_tasks_main = any(kw in body2 + body3 for kw in ["task", "project", "assign", "create"])

    if has_projects or has_tasks_main:
        record_result("Task/Project Assignment", True, "Task or project module accessible")
        screenshot("08_tasks_available")

        # Check for assign functionality
        assign_found = any(kw in (body + body2 + body3).lower()
                           for kw in ["assign", "assignee", "assign to", "delegate"])
        record_result("Assign to Team Member", assign_found,
                      "Assign functionality found" if assign_found else "No assign button/field")
    else:
        record_result("Task/Project Assignment", False, "No task/project functionality")
        shot = screenshot("08_no_tasks")
        record_issue(
            "Manager cannot assign tasks or projects to team members",
            "No task/project assignment feature found in the main app or Project module. "
            "Managers need to assign and track work for their team.",
            shot
        )


def test_09_team_calendar():
    """Team calendar — who's on leave when? Plan around absences."""
    print("\n=== TEST 09: Team Calendar ===")
    restart_driver_if_needed()

    calendar_urls = [
        f"{BASE_URL}/calendar",
        f"{BASE_URL}/team/calendar",
        f"{BASE_URL}/leave/calendar",
        f"{BASE_URL}/manager/calendar",
        f"{BASE_URL}/holidays",
    ]

    found_calendar = False
    for url in calendar_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url
        if "/login" not in current and "404" not in body:
            if any(kw in body for kw in ["calendar", "schedule", "holiday", "leave",
                                          "january", "february", "march", "april",
                                          "mon", "tue", "wed", "thu", "fri",
                                          "week", "month"]):
                found_calendar = True
                print(f"    Calendar at: {current}")
                shot = screenshot("09_team_calendar")
                break

    if found_calendar:
        record_result("Team Calendar", True, "Calendar view found")

        # Check if it shows team leave/absence info
        body = page_text()
        has_team_leave = any(kw in body for kw in ["leave", "absence", "off", "vacation",
                                                    "team", "member"])
        record_result("Calendar Shows Team Absences", has_team_leave,
                      "Team leave shown" if has_team_leave else "Calendar may not show team absences")
    else:
        record_result("Team Calendar", False, "No team calendar view found")
        shot = screenshot("09_no_calendar")
        record_issue(
            "No team calendar for managers to plan around absences",
            "No calendar view found showing team member leaves/absences. Managers need "
            "a visual calendar to see who is on leave when and plan work accordingly.",
            shot
        )


def test_10_rewards_kudos():
    """Can manager recommend someone for a reward/kudos?"""
    print("\n=== TEST 10: Rewards & Kudos ===")
    restart_driver_if_needed()

    # Try Rewards module via SSO
    safe_navigate(REWARDS_URL)
    time.sleep(4)
    body = page_text()
    current = driver.current_url
    shot1 = screenshot("10_rewards_module")

    if "/login" in current:
        login_ui(driver)
        safe_navigate(REWARDS_URL)
        time.sleep(3)
        body = page_text()

    has_rewards = any(kw in body for kw in ["reward", "kudos", "recognition", "appreciate",
                                             "nominate", "badge", "point", "star",
                                             "shout out", "well done"])

    # Also check main app
    safe_navigate(f"{BASE_URL}/rewards")
    time.sleep(2)
    body2 = page_text()
    has_rewards_main = any(kw in body2 for kw in ["reward", "kudos", "recognition", "nominate"])

    if has_rewards or has_rewards_main:
        record_result("Rewards Module Access", True, "Rewards accessible")
        screenshot("10_rewards_accessible")

        combined = body + body2
        can_nominate = any(kw in combined for kw in ["nominate", "recommend", "give",
                                                      "send", "create", "new reward"])
        record_result("Can Nominate for Reward", can_nominate,
                      "Nomination possible" if can_nominate else "No nomination action found")
    else:
        record_result("Rewards Module Access", False, "Cannot access rewards")
        shot = screenshot("10_no_rewards")
        record_issue(
            "Manager cannot access Rewards module to give kudos",
            "Navigating to the Rewards module does not provide access. Managers should "
            "be able to nominate or give kudos/rewards to team members for good work.",
            shot
        )


def test_11_create_team_event():
    """Can manager create an event for team (meeting, 1-on-1)?"""
    print("\n=== TEST 11: Create Team Event ===")
    restart_driver_if_needed()

    event_urls = [
        f"{BASE_URL}/events",
        f"{BASE_URL}/events/create",
        f"{BASE_URL}/calendar/events",
        f"{BASE_URL}/meetings",
    ]

    found_events = False
    for url in event_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url
        if "/login" not in current and "404" not in body:
            if any(kw in body for kw in ["event", "meeting", "schedule", "create",
                                          "announcement", "invite"]):
                found_events = True
                print(f"    Events at: {current}")
                shot = screenshot("11_events_page")
                break

    # Check via API
    event_api_paths = [
        "/api/events",
        "/api/v1/events",
        "/api/meetings",
        "/api/v1/meetings",
        "/api/calendar/events",
    ]
    api_event_data = None
    for path in event_api_paths:
        resp = api_get(path)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                print(f"    API {path}: {json.dumps(data)[:200]}")
                api_event_data = data
                break
            except:
                pass

    if found_events:
        record_result("Events Page", True, "Found")
        body = page_text()
        can_create = any(kw in body for kw in ["create", "add", "new event", "schedule",
                                                "new meeting"])
        record_result("Create Event Action", can_create,
                      "Create action available" if can_create else "No create event button")
    else:
        record_result("Events Page", False, "No events page found")
        shot = screenshot("11_no_events")
        record_issue(
            "Manager cannot create team events or meetings",
            "No events/meetings section found. Managers should be able to create "
            "team events (team meetings, 1-on-1s, etc.) and invite team members.",
            shot
        )


def test_12_helpdesk_team_tickets():
    """Helpdesk — can manager see tickets raised by team?"""
    print("\n=== TEST 12: Helpdesk Team Tickets ===")
    restart_driver_if_needed()

    helpdesk_urls = [
        f"{BASE_URL}/helpdesk",
        f"{BASE_URL}/helpdesk/tickets",
        f"{BASE_URL}/support",
        f"{BASE_URL}/tickets",
    ]

    found_helpdesk = False
    for url in helpdesk_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url
        if "/login" not in current and "404" not in body:
            if any(kw in body for kw in ["helpdesk", "ticket", "support", "query",
                                          "issue", "request", "complaint"]):
                found_helpdesk = True
                print(f"    Helpdesk at: {current}")
                shot = screenshot("12_helpdesk")
                break

    if found_helpdesk:
        record_result("Helpdesk Access", True, "Found")

        # Check if manager can see team tickets (not just own)
        body = page_text()
        src = page_source()
        team_filter = any(kw in body + src for kw in ["team", "my team", "reportee",
                                                       "all tickets", "assigned to me",
                                                       "department"])
        record_result("Helpdesk Team Ticket View", team_filter,
                      "Team filter/view available" if team_filter else "No team ticket filter")
        if not team_filter:
            record_issue(
                "Helpdesk lacks team ticket view for managers",
                "The helpdesk page does not provide a way for managers to see tickets "
                "raised by their team members. Managers need visibility into their team's issues.",
                screenshot("12_no_team_filter")
            )
    else:
        record_result("Helpdesk Access", False, "No helpdesk page found")


def test_13_compoff_approval():
    """Comp-off — can team members request comp-off? Can manager approve?"""
    print("\n=== TEST 13: Comp-Off Requests & Approval ===")
    restart_driver_if_needed()

    # Check leave pages for comp-off category
    compoff_urls = [
        f"{BASE_URL}/leave/comp-off",
        f"{BASE_URL}/comp-off",
        f"{BASE_URL}/leave/compensatory",
        f"{BASE_URL}/leave/approvals",
        f"{BASE_URL}/leave",
    ]

    found_compoff = False
    for url in compoff_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url
        if "/login" not in current:
            if any(kw in body for kw in ["comp off", "comp-off", "compensatory",
                                          "compoff", "compensation leave"]):
                found_compoff = True
                print(f"    Comp-off at: {current}")
                shot = screenshot("13_compoff")
                break

    # API check
    compoff_api_paths = [
        "/api/leave/comp-off",
        "/api/v1/leave/comp-off",
        "/api/compoff",
        "/api/v1/compoff",
        "/api/leave/types",
        "/api/v1/leave/types",
    ]
    api_compoff_data = None
    for path in compoff_api_paths:
        resp = api_get(path)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                data_str = json.dumps(data)
                if "comp" in data_str.lower() or "compensat" in data_str.lower():
                    print(f"    API {path}: comp-off found")
                    api_compoff_data = data
                    break
                elif path.endswith("types"):
                    print(f"    API {path}: {data_str[:200]}")
                    api_compoff_data = data
            except:
                pass

    if found_compoff:
        record_result("Comp-Off Feature", True, "Found in UI")
    elif api_compoff_data:
        record_result("Comp-Off Feature", True, "Found via API leave types")
    else:
        record_result("Comp-Off Feature", False, "No comp-off feature found")
        shot = screenshot("13_no_compoff")
        record_issue(
            "No comp-off request/approval workflow for managers",
            "No compensatory off (comp-off) feature found. Team members who work on "
            "holidays/weekends should be able to request comp-off, and managers should approve.",
            shot
        )


def test_14_team_reports():
    """Can manager generate attendance/leave report for team?"""
    print("\n=== TEST 14: Team Reports ===")
    restart_driver_if_needed()

    report_urls = [
        f"{BASE_URL}/reports",
        f"{BASE_URL}/reports/attendance",
        f"{BASE_URL}/reports/leave",
        f"{BASE_URL}/attendance/report",
        f"{BASE_URL}/manager/reports",
        f"{BASE_URL}/analytics",
    ]

    found_reports = False
    for url in report_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url
        if "/login" not in current and "404" not in body:
            if any(kw in body for kw in ["report", "analytics", "export", "download",
                                          "generate", "summary", "statistics"]):
                found_reports = True
                print(f"    Reports at: {current}")
                shot = screenshot("14_reports")
                break

    if found_reports:
        record_result("Team Reports", True, "Report section found")

        body = page_text()
        can_export = any(kw in body for kw in ["export", "download", "csv", "excel", "pdf",
                                                "generate report"])
        record_result("Export/Download Report", can_export,
                      "Export available" if can_export else "No export/download option")

        has_team_filter = any(kw in body for kw in ["team", "department", "employee",
                                                     "filter", "select"])
        record_result("Team Filter in Reports", has_team_filter,
                      "Team filter found" if has_team_filter else "No team filter in reports")
    else:
        record_result("Team Reports", False, "No reports section found")
        shot = screenshot("14_no_reports")
        record_issue(
            "Manager cannot generate team attendance or leave reports",
            "No reports section found. Managers need to generate and export team "
            "attendance/leave reports for planning and compliance.",
            shot
        )


def test_15_whistleblowing():
    """Whistleblowing — if a team member reports something, does it come to manager?"""
    print("\n=== TEST 15: Whistleblowing Channel ===")
    restart_driver_if_needed()

    whistle_urls = [
        f"{BASE_URL}/whistleblowing",
        f"{BASE_URL}/whistle-blowing",
        f"{BASE_URL}/complaints",
        f"{BASE_URL}/grievance",
        f"{BASE_URL}/anonymous-report",
        f"{BASE_URL}/ethics",
    ]

    found_whistle = False
    for url in whistle_urls:
        safe_navigate(url)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(url)
            body = page_text()
            current = driver.current_url
        if "/login" not in current and "404" not in body:
            if any(kw in body for kw in ["whistl", "anonymous", "grievance", "complaint",
                                          "report", "ethics", "misconduct"]):
                found_whistle = True
                print(f"    Whistleblowing at: {current}")
                shot = screenshot("15_whistleblowing")
                break

    if found_whistle:
        record_result("Whistleblowing Access", True, "Found")
    else:
        record_result("Whistleblowing Access", False, "No whistleblowing feature found")
        # This is informational; whistleblowing typically goes to HR/Ethics, not direct manager
        print("    Note: Whistleblowing typically goes to HR/Ethics committee, not direct manager")


def test_api_manager_endpoints():
    """Probe API for manager-specific endpoints."""
    print("\n=== TEST API: Manager-Specific Endpoints ===")

    endpoints = [
        ("/api/v1/manager/team", "Team list"),
        ("/api/v1/manager/dashboard", "Manager dashboard"),
        ("/api/v1/manager/attendance", "Team attendance"),
        ("/api/v1/manager/leave-requests", "Leave requests"),
        ("/api/v1/manager/leave-approvals", "Leave approvals"),
        ("/api/v1/team/members", "Team members"),
        ("/api/v1/team/attendance", "Team attendance v2"),
        ("/api/v1/team/leave-balance", "Team leave balances"),
        ("/api/v1/employees", "Employee list"),
        ("/api/v1/leave/pending", "Pending leaves"),
        ("/api/v1/leave/approvals", "Leave approvals v2"),
        ("/api/v1/attendance/team", "Team attendance v3"),
        ("/api/v1/attendance/report", "Attendance report"),
        ("/api/v1/reports/attendance", "Attendance report v2"),
        ("/api/v1/reports/leave", "Leave report"),
        ("/api/employees", "Employees"),
        ("/api/leave/approvals", "Leave approvals v3"),
        ("/api/leave/pending", "Pending leaves v2"),
        ("/api/attendance/team", "Team attendance v4"),
        ("/api/manager/team", "Manager team v2"),
        ("/api/team", "Team endpoint"),
    ]

    working_endpoints = []
    for path, desc in endpoints:
        resp = api_get(path)
        if resp:
            status = resp.status_code
            if status == 200:
                try:
                    data = resp.json()
                    print(f"    [200] {path} ({desc}): {json.dumps(data)[:150]}")
                    working_endpoints.append((path, desc))
                except:
                    print(f"    [200] {path} ({desc}): non-JSON response")
            elif status in (401, 403):
                print(f"    [{status}] {path} ({desc}): auth issue")
            elif status == 404:
                pass  # Expected for many
            else:
                print(f"    [{status}] {path} ({desc})")

    record_result("Manager API Endpoints", len(working_endpoints) > 0,
                  f"{len(working_endpoints)} working endpoints found: "
                  + ", ".join(d for _, d in working_endpoints[:5]))


# ═══════════════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION CHECK
# ═══════════════════════════════════════════════════════════════════════════

def test_sidebar_navigation():
    """Check sidebar/nav for manager-relevant links."""
    print("\n=== TEST: Sidebar Navigation for Manager ===")
    global driver
    ensure_driver()
    safe_navigate(BASE_URL)
    time.sleep(3)

    if "/login" in driver.current_url:
        login_ui(driver)
        safe_navigate(BASE_URL)
        time.sleep(2)

    shot = screenshot("sidebar_nav")

    # Collect all nav/sidebar links
    nav_links = []
    for sel in [
        "nav a", "aside a", ".sidebar a", "[class*='sidebar'] a",
        "[class*='nav'] a", "[class*='menu'] a", ".menu-item a",
        "[role='navigation'] a", "[class*='drawer'] a"
    ]:
        try:
            links = driver.find_elements(By.CSS_SELECTOR, sel)
            for link in links:
                text = link.text.strip()
                href = link.get_attribute("href") or ""
                if text:
                    nav_links.append({"text": text, "href": href})
        except:
            pass

    # Deduplicate
    seen = set()
    unique_links = []
    for link in nav_links:
        key = (link["text"].lower(), link["href"])
        if key not in seen:
            seen.add(key)
            unique_links.append(link)

    print(f"    Found {len(unique_links)} navigation links:")
    manager_relevant = []
    for link in unique_links:
        print(f"      - {link['text']} -> {link['href']}")
        text_lower = link['text'].lower()
        if any(kw in text_lower for kw in ["team", "manager", "approval", "attendance",
                                            "leave", "performance", "report", "reward",
                                            "helpdesk", "calendar", "event", "project",
                                            "task", "employee", "directory", "people"]):
            manager_relevant.append(link)

    print(f"\n    Manager-relevant links: {len(manager_relevant)}")
    for link in manager_relevant:
        print(f"      * {link['text']} -> {link['href']}")

    record_result("Sidebar Manager Links", len(manager_relevant) > 0,
                  f"{len(manager_relevant)} relevant links found")

    return unique_links


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    global driver, auth_token

    print("=" * 70)
    print("  RAVI KUMAR'S MANAGER DAY — EMP Cloud Manager Experience Test")
    print(f"  Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  User: {EMAIL} (Org Admin / Manager persona)")
    print("=" * 70)

    # API login first
    print("\n--- API Login ---")
    api_login()

    # Start browser
    print("\n--- Browser Setup ---")
    driver = get_driver()

    try:
        # Sidebar nav check first
        test_sidebar_navigation()

        # All 15 test scenarios
        test_01_login_and_dashboard_my_team()
        test_02_manager_page()
        test_03_pending_leave_approvals()
        test_04_team_attendance()
        test_05_team_leave_balances()
        test_06_team_member_profiles()
        test_07_performance_reviews_sso()
        test_08_assign_tasks_projects()
        test_09_team_calendar()
        test_10_rewards_kudos()
        test_11_create_team_event()
        test_12_helpdesk_team_tickets()
        test_13_compoff_approval()
        test_14_team_reports()
        test_15_whistleblowing()

        # API endpoint discovery
        test_api_manager_endpoints()

    except Exception as e:
        print(f"\n[FATAL] {e}")
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in test_results if r["passed"])
    failed = sum(1 for r in test_results if not r["passed"])
    total = len(test_results)

    print(f"\n  Total: {total}  |  PASSED: {passed}  |  FAILED: {failed}")
    print(f"  Pass rate: {passed/total*100:.1f}%" if total > 0 else "  No tests ran")

    print(f"\n  Issues filed: {len(issues_found)}")
    for issue in issues_found:
        existing = " (existing)" if issue.get("existing") else ""
        print(f"    - {issue['title']}{existing}")
        print(f"      {issue.get('url', 'N/A')}")

    print("\n  Detailed Results:")
    for r in test_results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"    [{status}] {r['test']}: {r['details']}")

    # Save results to file
    results_path = Path(r"C:\emptesting\manager_ravi_results.json")
    with open(results_path, "w") as f:
        json.dump({
            "date": datetime.datetime.now().isoformat(),
            "user": EMAIL,
            "persona": "Ravi Kumar — Team Lead",
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "issues_filed": len(issues_found),
            "results": test_results,
            "issues": issues_found
        }, f, indent=2)
    print(f"\n  Results saved to: {results_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
