"""
Priya Patel's Workday — EMP Cloud Employee Journey Test
Simulates a real employee's daily interactions with the HRMS.
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
API_URL = "https://test-empcloud-api.empcloud.com"
EMAIL = "priya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = Path(r"C:\Users\Admin\screenshots\employee_journey")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

# Track issues found
issues_found = []
test_results = []
test_count = 0
driver = None
auth_token = None


# ── Helpers ─────────────────────────────────────────────────────────────────

def get_driver():
    """Create a fresh Chrome WebDriver."""
    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--remote-debugging-port=0")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--crash-dumps-dir=/tmp/chrome-crashes")
    opts.add_argument("--disable-features=VizDisplayCompositor")
    svc = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(45)
    d.implicitly_wait(5)
    return d


def restart_driver_if_needed():
    """Restart driver every 3 tests or if crashed."""
    global driver, test_count
    test_count += 1
    if test_count % 3 == 0 or not is_driver_alive():
        if driver:
            try:
                driver.quit()
            except:
                pass
        driver = get_driver()
        login_ui(driver)
    return driver


def is_driver_alive():
    """Check if the current driver session is still usable."""
    global driver
    if driver is None:
        return False
    try:
        _ = driver.current_url
        return True
    except:
        return False


def ensure_driver():
    global driver
    if not is_driver_alive():
        if driver:
            try:
                driver.quit()
            except:
                pass
        driver = get_driver()
        login_ui(driver)
    return driver


def screenshot(name):
    """Save screenshot and return the path."""
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
    """Upload screenshot to GitHub and return the URL."""
    if not filepath or not Path(filepath).exists():
        return None
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        fname = Path(filepath).name
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/employee_journey/{fname}"
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
    """File a GitHub issue with screenshot."""
    if labels is None:
        labels = ["bug", "employee-journey"]
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }
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
    """Record an issue, upload screenshot, file on GitHub."""
    img_url = upload_screenshot_to_github(screenshot_path) if screenshot_path else None
    body = f"## Description\n{description}\n\n"
    body += f"**User:** Priya Patel (priya@technova.in) — Employee\n"
    body += f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    body += f"**URL:** {driver.current_url if driver else 'N/A'}\n\n"
    if img_url:
        body += f"## Screenshot\n![screenshot]({img_url})\n\n"
    elif screenshot_path:
        body += f"## Screenshot\nLocal: `{screenshot_path}` (upload failed)\n\n"
    body += "## Steps to Reproduce\n1. Login as priya@technova.in\n2. Navigate to the relevant section\n3. Observe the issue\n\n"
    body += "## Expected\nThe feature should work correctly for self-service employee usage.\n\n"
    body += "## Actual\n" + description + "\n"
    file_github_issue(title, body, labels)


def record_result(test_name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {test_name}: {details}")
    test_results.append({"test": test_name, "passed": passed, "details": details})


def wait_click(by, value, timeout=10):
    """Wait for element and click it."""
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
    """Navigate and wait for page to settle. Recover from crashes."""
    global driver
    try:
        driver.get(url)
        time.sleep(wait_secs)
    except WebDriverException as e:
        if "tab crashed" in str(e).lower() or "not reachable" in str(e).lower() or "session" in str(e).lower():
            print(f"    [crash recovery] Restarting driver after crash at {url}")
            try:
                driver.quit()
            except:
                pass
            driver = get_driver()
            login_ui(driver)
            try:
                driver.get(url)
                time.sleep(wait_secs)
            except Exception as e2:
                print(f"    [nav error after recovery] {url}: {e2}")
        else:
            print(f"    [nav error] {url}: {e}")
    except Exception as e:
        print(f"    [nav error] {url}: {e}")


# ── API Login ───────────────────────────────────────────────────────────────

def api_login():
    """Get auth token via API — try multiple endpoints."""
    global auth_token
    endpoints = [
        "/api/auth/login",
        "/api/v1/auth/login",
        "/auth/login",
        "/api/login",
        "/api/users/login",
        "/api/employee/login",
    ]
    payloads = [
        {"email": EMAIL, "password": PASSWORD},
        {"username": EMAIL, "password": PASSWORD},
    ]
    for ep in endpoints:
        for payload in payloads:
            try:
                resp = requests.post(f"{API_URL}{ep}", json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    auth_token = (data.get("token") or data.get("accessToken") or
                                  data.get("access_token") or "")
                    if not auth_token and isinstance(data.get("data"), dict):
                        auth_token = (data["data"].get("token") or
                                      data["data"].get("accessToken") or
                                      data["data"].get("access_token") or "")
                    if auth_token:
                        print(f"  [API] Login OK at {ep}, token: {str(auth_token)[:20]}...")
                        return True
                    else:
                        print(f"  [API] 200 at {ep} but no token in response: {str(data)[:200]}")
                else:
                    print(f"  [API] {ep}: {resp.status_code}")
            except Exception as e:
                print(f"  [API] {ep} error: {e}")
    print("  [API] All login endpoints failed — continuing with UI-only testing")
    return False


def api_get(path, params=None):
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    try:
        resp = requests.get(f"{API_URL}{path}", headers=headers, params=params, timeout=15)
        return resp
    except Exception as e:
        print(f"  [API GET error] {path}: {e}")
        return None


def api_post(path, data=None, json_data=None):
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    try:
        resp = requests.post(f"{API_URL}{path}", headers=headers, data=data, json=json_data, timeout=15)
        return resp
    except Exception as e:
        print(f"  [API POST error] {path}: {e}")
        return None


# ── UI Login ────────────────────────────────────────────────────────────────

def login_ui(d):
    """Login via UI as Priya."""
    try:
        d.get(f"{BASE_URL}/login")
        time.sleep(3)

        # Try to find email input
        email_input = None
        for sel in ["input[name='email']", "input[type='email']", "#email", "input[placeholder*='mail']",
                     "input[placeholder*='Email']"]:
            try:
                email_input = d.find_element(By.CSS_SELECTOR, sel)
                if email_input:
                    break
            except:
                continue

        if not email_input:
            # Maybe already logged in or different page
            inputs = d.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                t = inp.get_attribute("type") or ""
                if t in ("email", "text"):
                    email_input = inp
                    break

        if email_input:
            email_input.clear()
            email_input.send_keys(EMAIL)
        else:
            print("  [login] Could not find email input")
            return False

        # Password
        pw_input = None
        for sel in ["input[name='password']", "input[type='password']", "#password"]:
            try:
                pw_input = d.find_element(By.CSS_SELECTOR, sel)
                if pw_input:
                    break
            except:
                continue

        if pw_input:
            pw_input.clear()
            pw_input.send_keys(PASSWORD)
        else:
            print("  [login] Could not find password input")
            return False

        # Submit
        for sel in ["button[type='submit']", "button:not([type='button'])", ".login-btn",
                     "button"]:
            try:
                btn = d.find_element(By.CSS_SELECTOR, sel)
                text = (btn.text or "").lower()
                if "sign" in text or "log" in text or "submit" in text or sel == "button[type='submit']":
                    btn.click()
                    break
            except:
                continue

        time.sleep(4)
        current = d.current_url
        if "/login" not in current or "/dashboard" in current:
            print("  [login] UI login appears successful")
            return True
        else:
            print(f"  [login] Still on login page: {current}")
            return False
    except Exception as e:
        print(f"  [login error] {e}")
        return False


# ── Test Functions ──────────────────────────────────────────────────────────

def test_01_morning_login_dashboard():
    """Morning — Login and check dashboard."""
    print("\n=== 1. MORNING LOGIN & DASHBOARD ===")
    d = ensure_driver()
    logged_in = login_ui(d)

    if not logged_in:
        sp = screenshot("login_failed")
        record_result("Login", False, "Could not login as Priya")
        record_issue("Cannot login as employee — stuck on login page",
                     "Logging in as priya@technova.in with correct credentials doesn't redirect to dashboard.",
                     sp)
        return False

    screenshot("dashboard_after_login")

    # Check personalization — is Priya's name visible?
    page_src = d.page_source.lower()
    has_name = "priya" in page_src
    record_result("Dashboard shows employee name", has_name,
                  "Found 'Priya' on dashboard" if has_name else "Name not visible on dashboard")
    if not has_name:
        sp = screenshot("dashboard_no_name")
        record_issue("Dashboard doesn't show my name after login",
                     "After logging in as priya@technova.in, the dashboard doesn't display the employee's name. "
                     "As an employee, I expect to see a personalized greeting or my name somewhere on the dashboard.",
                     sp, ["bug", "employee-journey", "dashboard"])

    # Check for department, leave balance
    has_dept = any(w in page_src for w in ["department", "engineering", "technova", "hr", "finance", "it"])
    record_result("Dashboard shows department info", has_dept,
                  "Department info found" if has_dept else "No department info visible")

    has_leave = any(w in page_src for w in ["leave", "balance", "casual", "sick", "annual"])
    record_result("Dashboard shows leave balance", has_leave,
                  "Leave info found" if has_leave else "No leave balance on dashboard")

    # Look for Clock In button
    has_clock = any(w in page_src for w in ["clock in", "check in", "punch in", "mark attendance", "check-in"])
    record_result("Clock In button visible", has_clock,
                  "Clock-in option found" if has_clock else "No clock-in button on dashboard")
    if not has_clock:
        sp = screenshot("no_clock_in")
        record_issue("No quick 'Clock In' button on employee dashboard",
                     "The dashboard doesn't have a visible Clock In / Check In button. "
                     "Employees should be able to quickly mark attendance from the dashboard.",
                     sp, ["enhancement", "employee-journey", "dashboard"])

    # Try to click clock in if found
    try:
        for text in ["Clock In", "Check In", "Punch In", "Mark Attendance"]:
            btns = d.find_elements(By.XPATH, f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                screenshot("clock_in_clicked")
                record_result("Clock In click", True, f"Clicked '{text}'")
                break
    except Exception as e:
        print(f"    Clock-in click attempt: {e}")

    # Check for announcements
    has_announcements = any(w in page_src for w in ["announcement", "notice", "news", "update"])
    record_result("Announcements section", has_announcements,
                  "Announcements area found" if has_announcements else "No announcements visible")

    # Check for pending tasks
    has_pending = any(w in page_src for w in ["pending", "task", "approval", "action", "to-do", "todo"])
    record_result("Pending tasks/actions", has_pending,
                  "Pending items found" if has_pending else "No pending tasks section")

    return logged_in


def test_02_check_profile():
    """Check My Profile — personal info, tabs, edit capabilities."""
    print("\n=== 2. CHECK MY PROFILE ===")
    d = restart_driver_if_needed()

    # Navigate to profile
    profile_urls = [
        f"{BASE_URL}/my-profile", f"{BASE_URL}/profile", f"{BASE_URL}/employee/profile",
        f"{BASE_URL}/self-service/profile", f"{BASE_URL}/my-info"
    ]

    found_profile = False
    for url in profile_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["profile", "personal", "employee info", "my info"]) and "404" not in d.title.lower():
            found_profile = True
            break

    # Also try sidebar navigation
    if not found_profile:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for link_text in ["My Profile", "Profile", "My Info", "Personal Info"]:
                links = d.find_elements(By.XPATH, f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{link_text.lower()}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found_profile = True
                    break
        except:
            pass

    sp = screenshot("profile_page")
    record_result("Profile page accessible", found_profile,
                  f"At {d.current_url}" if found_profile else "Could not find profile page")

    if not found_profile:
        record_issue("Can't find My Profile page",
                     "Navigated through various URLs and sidebar links but couldn't find the My Profile page. "
                     "An employee should be able to easily access their profile.",
                     sp, ["bug", "employee-journey", "profile"])
        return

    page = d.page_source.lower()

    # Check for tabs
    tabs_expected = ["personal", "job", "education", "experience", "address", "document"]
    tabs_found = [t for t in tabs_expected if t in page]
    record_result("Profile tabs present", len(tabs_found) >= 2,
                  f"Tabs found: {tabs_found}")

    # Try clicking each tab
    for tab_name in tabs_expected:
        try:
            tab_els = d.find_elements(By.XPATH,
                f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{tab_name}')]"
                f"[self::a or self::button or self::li or self::div[contains(@class,'tab')]]")
            if tab_els:
                tab_els[0].click()
                time.sleep(1)
                screenshot(f"profile_tab_{tab_name}")
        except:
            pass

    # Check if phone number is editable
    phone_editable = False
    try:
        phone_fields = d.find_elements(By.CSS_SELECTOR,
            "input[name*='phone'], input[name*='mobile'], input[placeholder*='phone'], input[placeholder*='mobile']")
        for pf in phone_fields:
            if pf.is_enabled() and pf.is_displayed():
                phone_editable = True
                break
    except:
        pass
    record_result("Phone number editable", phone_editable,
                  "Phone field is editable" if phone_editable else "Phone field not found or not editable")

    # Profile photo area
    has_photo_area = False
    try:
        photo_els = d.find_elements(By.CSS_SELECTOR,
            "img[class*='avatar'], img[class*='profile'], .avatar, .profile-photo, .profile-image, "
            "img[alt*='profile'], img[alt*='avatar'], .user-avatar")
        has_photo_area = len(photo_els) > 0
    except:
        pass
    record_result("Profile photo area", has_photo_area,
                  "Photo area found" if has_photo_area else "No profile photo area")

    # Check for Priya's info
    has_priya = "priya" in page
    record_result("Profile shows Priya's info", has_priya,
                  "Name found in profile" if has_priya else "Name not found in profile")


def test_03_apply_leave():
    """Apply for sick leave next Tuesday."""
    print("\n=== 3. APPLY FOR LEAVE ===")
    d = restart_driver_if_needed()

    # First check balance via API
    if auth_token:
        bal_resp = api_get("/api/leave/balance")
        if bal_resp and bal_resp.status_code == 200:
            print(f"    [API] Leave balance: {bal_resp.text[:300]}")
            record_result("Leave balance API", True, "API returned balance data")
        else:
            st = bal_resp.status_code if bal_resp else "N/A"
            print(f"    [API] Leave balance failed: {st}")

            # Try alternate endpoints
            for ep in ["/api/leaves/balance", "/api/employee/leave-balance", "/api/v1/leave/balance",
                       "/api/leaves/my-balance"]:
                r = api_get(ep)
                if r and r.status_code == 200:
                    print(f"    [API] Balance found at {ep}: {r.text[:200]}")
                    break

    # Navigate to leave section
    leave_urls = [
        f"{BASE_URL}/leave", f"{BASE_URL}/leaves", f"{BASE_URL}/my-leaves",
        f"{BASE_URL}/leave/apply", f"{BASE_URL}/self-service/leave",
        f"{BASE_URL}/employee/leave"
    ]

    found_leave = False
    for url in leave_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["leave", "balance", "apply", "casual", "sick"]) and "404" not in d.title.lower():
            found_leave = True
            break

    # Try sidebar
    if not found_leave:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Leave", "My Leave", "Leaves", "Apply Leave"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found_leave = True
                    break
        except:
            pass

    sp = screenshot("leave_page")
    record_result("Leave page accessible", found_leave,
                  f"At {d.current_url}" if found_leave else "Could not find leave page")

    if not found_leave:
        record_issue("Can't find the Leave section",
                     "Tried multiple URLs and sidebar links but couldn't find where to apply for leave. "
                     "This is a core HR function that every employee needs.",
                     sp, ["bug", "employee-journey", "leave"])
        return

    # Check leave balance display
    page = d.page_source.lower()
    has_balance = any(w in page for w in ["balance", "available", "remaining", "entitled"])
    record_result("Leave balance visible", has_balance,
                  "Balance info shown" if has_balance else "No balance information visible")
    if not has_balance:
        sp = screenshot("leave_no_balance")
        record_issue("Leave page doesn't show my leave balance",
                     "The leave page doesn't display how many leave days I have remaining. "
                     "I need to know my balance before applying.",
                     sp, ["bug", "employee-journey", "leave"])

    # Try to click Apply Leave
    apply_clicked = False
    try:
        for text in ["Apply Leave", "Apply", "New Leave", "Request Leave", "Apply for Leave", "New Application"]:
            btns = d.find_elements(By.XPATH,
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')] | "
                f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                apply_clicked = True
                screenshot("leave_apply_form")
                break
    except Exception as e:
        print(f"    Apply button error: {e}")

    record_result("Apply Leave button works", apply_clicked,
                  "Apply form opened" if apply_clicked else "Could not open apply leave form")

    if not apply_clicked:
        sp = screenshot("leave_no_apply_btn")
        record_issue("Can't find 'Apply Leave' button",
                     "There's no visible 'Apply Leave' button on the leave page. "
                     "I need to be able to submit a leave request.",
                     sp, ["bug", "employee-journey", "leave"])
        return

    # Try to fill the leave form
    # Select leave type
    leave_type_selected = False
    try:
        selects = d.find_elements(By.TAG_NAME, "select")
        for s in selects:
            options = s.find_elements(By.TAG_NAME, "option")
            option_texts = [o.text.lower() for o in options]
            if any("sick" in t or "casual" in t or "leave" in t for t in option_texts):
                sel = Select(s)
                for opt in options:
                    if "sick" in opt.text.lower():
                        sel.select_by_visible_text(opt.text)
                        leave_type_selected = True
                        break
                if not leave_type_selected:
                    # Select first non-empty option
                    for opt in options:
                        if opt.text.strip() and opt.text.strip() != "Select":
                            sel.select_by_visible_text(opt.text)
                            leave_type_selected = True
                            break
                break
    except:
        pass

    # Try dropdown divs (custom dropdowns)
    if not leave_type_selected:
        try:
            dropdowns = d.find_elements(By.CSS_SELECTOR,
                "[class*='select'], [class*='dropdown'], [role='combobox'], [role='listbox']")
            for dd in dropdowns:
                text = dd.text.lower()
                if "type" in text or "select" in text or "leave" in text:
                    dd.click()
                    time.sleep(1)
                    options = d.find_elements(By.CSS_SELECTOR,
                        "[role='option'], .option, li[class*='option'], div[class*='option']")
                    for opt in options:
                        if "sick" in opt.text.lower():
                            opt.click()
                            leave_type_selected = True
                            break
                    if not leave_type_selected and options:
                        options[0].click()
                        leave_type_selected = True
                    break
        except:
            pass

    record_result("Leave type dropdown has options", leave_type_selected,
                  "Selected leave type" if leave_type_selected else "Dropdown empty or not found")
    if not leave_type_selected:
        sp = screenshot("leave_empty_dropdown")
        record_issue("Leave type dropdown has no options or can't select",
                     "When trying to apply for leave, the leave type dropdown either has no options "
                     "or I can't select a type. This blocks the entire leave application flow.",
                     sp, ["bug", "employee-journey", "leave"])

    # Pick dates — next Tuesday
    today = datetime.date.today()
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0:
        days_until_tuesday = 7
    next_tuesday = today + datetime.timedelta(days=days_until_tuesday)
    date_str = next_tuesday.strftime("%Y-%m-%d")
    alt_date_str = next_tuesday.strftime("%m/%d/%Y")
    display_date_str = next_tuesday.strftime("%d-%m-%Y")

    date_filled = False
    try:
        date_inputs = d.find_elements(By.CSS_SELECTOR,
            "input[type='date'], input[name*='date'], input[placeholder*='date'], "
            "input[name*='from'], input[name*='start']")
        for di in date_inputs:
            if di.is_displayed():
                di.clear()
                di.send_keys(date_str)
                date_filled = True
                break
    except:
        pass

    # Fill end date
    try:
        end_inputs = d.find_elements(By.CSS_SELECTOR,
            "input[name*='end'], input[name*='to'], input[placeholder*='end']")
        for ei in end_inputs:
            if ei.is_displayed():
                ei.clear()
                ei.send_keys(date_str)
                break
    except:
        pass

    # Fill reason
    reason_filled = False
    try:
        for sel in ["textarea", "input[name*='reason']", "input[placeholder*='reason']",
                     "textarea[name*='reason']", "textarea[placeholder*='reason']"]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    el.clear()
                    el.send_keys("Doctor's appointment")
                    reason_filled = True
                    break
            if reason_filled:
                break
    except:
        pass

    record_result("Fill leave reason", reason_filled,
                  "Reason entered" if reason_filled else "Could not find reason field")

    # Submit
    submitted = False
    try:
        for text in ["Submit", "Apply", "Save", "Send", "Request"]:
            btns = d.find_elements(By.XPATH,
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
            if btns:
                for btn in btns:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        time.sleep(3)
                        submitted = True
                        break
            if submitted:
                break
    except:
        pass

    sp = screenshot("leave_after_submit")
    page_after = d.page_source.lower()
    has_confirmation = any(w in page_after for w in ["success", "submitted", "pending", "created", "applied"])
    has_error = any(w in page_after for w in ["error", "failed", "invalid", "required"])

    record_result("Leave submission", submitted and (has_confirmation or not has_error),
                  "Submitted successfully" if has_confirmation else "Submitted but no confirmation" if submitted else "Could not submit")

    if submitted and has_error and not has_confirmation:
        sp = screenshot("leave_submit_error")
        record_issue("Leave application shows error after submitting",
                     "Filled out the leave form (Sick Leave, next Tuesday, 'Doctor's appointment') "
                     "but got an error when submitting.",
                     sp, ["bug", "employee-journey", "leave"])

    # Also try via API
    if auth_token:
        api_leave = api_post("/api/leave/apply", json_data={
            "leaveType": "sick",
            "startDate": date_str,
            "endDate": date_str,
            "reason": "Doctor's appointment (API test)"
        })
        if api_leave:
            print(f"    [API] Leave apply: {api_leave.status_code} {api_leave.text[:200]}")

        # Try alternate endpoint
        if not api_leave or api_leave.status_code >= 400:
            api_leave2 = api_post("/api/leaves/apply", json_data={
                "leave_type": "sick_leave",
                "from_date": date_str,
                "to_date": date_str,
                "reason": "Doctor's appointment (API test)"
            })
            if api_leave2:
                print(f"    [API alt] Leave apply: {api_leave2.status_code} {api_leave2.text[:200]}")


def test_04_attendance_history():
    """Check attendance history for this month."""
    print("\n=== 4. ATTENDANCE HISTORY ===")
    d = restart_driver_if_needed()

    att_urls = [
        f"{BASE_URL}/attendance", f"{BASE_URL}/my-attendance", f"{BASE_URL}/attendance/my",
        f"{BASE_URL}/self-service/attendance", f"{BASE_URL}/employee/attendance"
    ]

    found = False
    for url in att_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["attendance", "check-in", "check in", "punch", "clock"]) and "404" not in d.title.lower():
            found = True
            break

    if not found:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Attendance", "My Attendance", "Time", "Clock"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found = True
                    break
        except:
            pass

    sp = screenshot("attendance_page")
    record_result("Attendance page accessible", found,
                  f"At {d.current_url}" if found else "Attendance page not found")

    if not found:
        record_issue("Can't find My Attendance page",
                     "Couldn't navigate to attendance history. I need to check my attendance records.",
                     sp, ["bug", "employee-journey", "attendance"])
        return

    page = d.page_source.lower()

    # Calendar view
    has_calendar = any(w in page for w in ["calendar", "month", "week", "grid"])
    record_result("Calendar view available", has_calendar,
                  "Calendar view found" if has_calendar else "No calendar view")

    # Check-in/out times
    has_times = any(w in page for w in ["check-in", "check-out", "clock-in", "clock-out", "in time", "out time",
                                        "punch in", "punch out", "entry", "exit"])
    record_result("Check-in/out times shown", has_times,
                  "Time records visible" if has_times else "No time records")

    if not has_times:
        sp = screenshot("attendance_no_records")
        record_issue("Attendance page shows no check-in/out records",
                     "My Attendance page doesn't show any time records. "
                     "Expected to see daily check-in and check-out times for this month.",
                     sp, ["bug", "employee-journey", "attendance"])

    # Regularization option
    has_regularize = any(w in page for w in ["regulariz", "request", "correction", "missed punch"])
    record_result("Regularization option", has_regularize,
                  "Regularization available" if has_regularize else "No regularization option")

    # API check
    if auth_token:
        now = datetime.datetime.now()
        for ep in ["/api/attendance/my", "/api/attendance", "/api/employee/attendance",
                   "/api/v1/attendance/my"]:
            r = api_get(ep, {"month": now.month, "year": now.year})
            if r and r.status_code == 200:
                print(f"    [API] Attendance at {ep}: {r.text[:200]}")
                break


def test_05_helpdesk_ticket():
    """Raise a helpdesk ticket about broken keyboard."""
    print("\n=== 5. RAISE HELPDESK TICKET ===")
    d = restart_driver_if_needed()

    hd_urls = [
        f"{BASE_URL}/helpdesk", f"{BASE_URL}/helpdesk/my-tickets", f"{BASE_URL}/tickets",
        f"{BASE_URL}/my-tickets", f"{BASE_URL}/helpdesk/create",
        f"{BASE_URL}/support", f"{BASE_URL}/self-service/helpdesk"
    ]

    found = False
    for url in hd_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["ticket", "helpdesk", "support", "issue", "request"]) and "404" not in d.title.lower():
            found = True
            break

    if not found:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Helpdesk", "Support", "Tickets", "My Tickets", "Raise Ticket"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found = True
                    break
        except:
            pass

    sp = screenshot("helpdesk_page")
    record_result("Helpdesk page accessible", found,
                  f"At {d.current_url}" if found else "Helpdesk page not found")

    if not found:
        record_issue("Can't find Helpdesk / Support Tickets section",
                     "Couldn't find the helpdesk to raise a ticket about my broken laptop keyboard. "
                     "Employees need an easy way to get IT support.",
                     sp, ["bug", "employee-journey", "helpdesk"])
        return

    # Click create ticket
    create_clicked = False
    try:
        for text in ["Create Ticket", "Raise Ticket", "New Ticket", "Submit Ticket", "Create", "New"]:
            btns = d.find_elements(By.XPATH,
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')] | "
                f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                create_clicked = True
                break
    except:
        pass

    screenshot("helpdesk_create_form")
    record_result("Create Ticket button", create_clicked,
                  "Form opened" if create_clicked else "No create button found")

    if not create_clicked:
        sp = screenshot("helpdesk_no_create")
        record_issue("No 'Create Ticket' or 'Raise Ticket' button in Helpdesk",
                     "The helpdesk page doesn't have a visible button to create a new ticket.",
                     sp, ["bug", "employee-journey", "helpdesk"])
        return

    # Fill the form
    # Subject
    subject_filled = False
    try:
        for sel in ["input[name*='subject']", "input[name*='title']", "input[placeholder*='subject']",
                     "input[placeholder*='title']", "input[type='text']"]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    el.clear()
                    el.send_keys("Laptop keyboard keys sticking")
                    subject_filled = True
                    break
            if subject_filled:
                break
    except:
        pass

    # Description
    desc_filled = False
    try:
        for sel in ["textarea", "textarea[name*='desc']", "textarea[name*='message']",
                     "[contenteditable='true']"]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    el.clear()
                    el.send_keys("Several keys on my ThinkPad X1 are sticking. Especially the spacebar and 'e' key. Makes typing very difficult.")
                    desc_filled = True
                    break
            if desc_filled:
                break
    except:
        pass

    # Priority
    priority_set = False
    try:
        selects = d.find_elements(By.TAG_NAME, "select")
        for s in selects:
            opts = [o.text.lower() for o in s.find_elements(By.TAG_NAME, "option")]
            if any("high" in o or "priority" in o or "medium" in o for o in opts):
                sel = Select(s)
                for opt in s.find_elements(By.TAG_NAME, "option"):
                    if "high" in opt.text.lower():
                        sel.select_by_visible_text(opt.text)
                        priority_set = True
                        break
                break
    except:
        pass

    record_result("Ticket form fillable", subject_filled and desc_filled,
                  f"Subject: {subject_filled}, Desc: {desc_filled}, Priority: {priority_set}")

    if not priority_set:
        sp = screenshot("helpdesk_no_priority")
        # Only report if we found the form but no priority
        if subject_filled:
            record_issue("Helpdesk ticket form is missing priority field",
                         "The ticket creation form doesn't have a priority dropdown. "
                         "I need to mark my broken keyboard as High priority.",
                         sp, ["bug", "employee-journey", "helpdesk"])

    # Submit
    submitted = False
    try:
        for text in ["Submit", "Create", "Save", "Send", "Raise"]:
            btns = d.find_elements(By.XPATH,
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(3)
                    submitted = True
                    break
            if submitted:
                break
    except:
        pass

    sp = screenshot("helpdesk_after_submit")
    page_after = d.page_source.lower()
    success = any(w in page_after for w in ["success", "created", "submitted", "ticket"])

    record_result("Ticket submitted", submitted and success,
                  "Ticket created successfully" if success else "Submission unclear")

    # API test
    if auth_token:
        for ep in ["/api/helpdesk/tickets", "/api/tickets", "/api/helpdesk/create"]:
            r = api_post(ep, json_data={
                "subject": "Laptop keyboard keys sticking (API test)",
                "description": "Several keys on my ThinkPad X1 are sticking. Especially the spacebar and 'e' key.",
                "priority": "high"
            })
            if r and r.status_code in (200, 201):
                print(f"    [API] Ticket created at {ep}: {r.text[:200]}")
                break
            elif r:
                print(f"    [API] Ticket at {ep}: {r.status_code}")


def test_06_payslip():
    """Check payslip via payroll SSO."""
    print("\n=== 6. CHECK PAYSLIP ===")
    d = restart_driver_if_needed()

    # Try to find payroll link on modules page
    safe_navigate(f"{BASE_URL}/modules")
    time.sleep(3)
    sp = screenshot("modules_page")
    page = d.page_source.lower()

    has_payroll = "payroll" in page
    record_result("Payroll link on modules page", has_payroll,
                  "Payroll link found" if has_payroll else "No payroll link visible")

    # Try clicking payroll
    payroll_clicked = False
    try:
        for text in ["Payroll", "Salary", "Pay", "Payslip"]:
            links = d.find_elements(By.XPATH,
                f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')] | "
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')] | "
                f"//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
            for link in links:
                if link.is_displayed():
                    link.click()
                    time.sleep(4)
                    payroll_clicked = True
                    break
            if payroll_clicked:
                break
    except:
        pass

    sp = screenshot("payroll_page")
    current = d.current_url
    record_result("Payroll SSO navigation", payroll_clicked or "payroll" in current.lower(),
                  f"At {current}")

    # Also try direct payroll URL
    if "payroll" not in current.lower():
        safe_navigate("https://testpayroll.empcloud.com")
        time.sleep(4)
        sp = screenshot("payroll_direct")
        current = d.current_url
        record_result("Direct payroll URL", "payroll" in current.lower() or "login" not in current.lower(),
                      f"At {current}")

    page = d.page_source.lower()
    has_salary = any(w in page for w in ["salary", "payslip", "basic", "gross", "net", "deduction", "earning"])
    record_result("Salary information visible", has_salary,
                  "Salary data found" if has_salary else "No salary info visible")

    has_download = any(w in page for w in ["download", "pdf", "print", "export"])
    record_result("Payslip download option", has_download,
                  "Download available" if has_download else "No download option")

    has_tax = any(w in page for w in ["tax", "tds", "pf", "provident", "esi", "income tax"])
    record_result("Tax deductions visible", has_tax,
                  "Tax info found" if has_tax else "No tax deduction info")


def test_07_survey():
    """Fill out a company survey."""
    print("\n=== 7. COMPANY SURVEY ===")
    d = restart_driver_if_needed()

    survey_urls = [
        f"{BASE_URL}/surveys", f"{BASE_URL}/survey", f"{BASE_URL}/surveys/active",
        f"{BASE_URL}/self-service/surveys", f"{BASE_URL}/employee/surveys"
    ]

    found = False
    for url in survey_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["survey", "questionnaire", "feedback form"]) and "404" not in d.title.lower():
            found = True
            break

    if not found:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Survey", "Surveys", "Active Surveys"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found = True
                    break
        except:
            pass

    sp = screenshot("survey_page")
    record_result("Survey page accessible", found,
                  f"At {d.current_url}" if found else "Survey page not found")

    if not found:
        record_issue("Can't find Surveys section",
                     "Couldn't find any surveys page. If there are company surveys, they should be easy to find.",
                     sp, ["bug", "employee-journey", "survey"])
        return

    # Check for active surveys
    page = d.page_source.lower()
    has_active = any(w in page for w in ["active", "pending", "fill", "take survey", "start"])
    record_result("Active surveys available", has_active,
                  "Active surveys found" if has_active else "No active surveys")

    # Try to open a survey
    try:
        for text in ["Take Survey", "Start", "Fill", "Open", "View"]:
            btns = d.find_elements(By.XPATH,
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')] | "
                f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
            if btns:
                btns[0].click()
                time.sleep(3)
                screenshot("survey_questions")

                # Try to answer questions
                page = d.page_source.lower()
                if "question" in page or "?" in page:
                    record_result("Survey questions displayed", True, "Questions visible")

                    # Try radio buttons, text inputs
                    radios = d.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    if radios:
                        radios[0].click()

                    textareas = d.find_elements(By.TAG_NAME, "textarea")
                    for ta in textareas:
                        if ta.is_displayed():
                            ta.send_keys("Good experience overall")
                            break

                    # Submit survey
                    for st in ["Submit", "Complete", "Finish", "Done"]:
                        sub_btns = d.find_elements(By.XPATH, f"//button[contains(text(), '{st}')]")
                        if sub_btns:
                            sub_btns[0].click()
                            time.sleep(2)
                            screenshot("survey_submitted")
                            break
                break
    except Exception as e:
        print(f"    Survey interaction error: {e}")

    # API check
    if auth_token:
        for ep in ["/api/surveys", "/api/surveys/active", "/api/survey/active"]:
            r = api_get(ep)
            if r and r.status_code == 200:
                print(f"    [API] Surveys at {ep}: {r.text[:200]}")
                break


def test_08_wellness_checkin():
    """Daily wellness check-in."""
    print("\n=== 8. WELLNESS CHECK-IN ===")
    d = restart_driver_if_needed()

    wellness_urls = [
        f"{BASE_URL}/wellness", f"{BASE_URL}/wellness/daily", f"{BASE_URL}/wellness/check-in",
        f"{BASE_URL}/self-service/wellness", f"{BASE_URL}/employee/wellness"
    ]

    found = False
    for url in wellness_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["wellness", "mood", "check-in", "well-being", "health"]) and "404" not in d.title.lower():
            found = True
            break

    if not found:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Wellness", "Well-being", "Daily Check-in", "Health"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found = True
                    break
        except:
            pass

    sp = screenshot("wellness_page")
    record_result("Wellness page accessible", found,
                  f"At {d.current_url}" if found else "Wellness page not found")

    if not found:
        return

    page = d.page_source.lower()
    has_mood = any(w in page for w in ["mood", "feeling", "how are you", "emoji", "happy", "sad", "good"])
    record_result("Mood selection available", has_mood,
                  "Mood options found" if has_mood else "No mood selection")

    # Try to do check-in
    try:
        for text in ["Check In", "Daily Check", "Submit", "Start Check-in"]:
            btns = d.find_elements(By.XPATH,
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')] | "
                f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                screenshot("wellness_checkin_form")
                break
    except:
        pass

    # Try mood buttons/icons
    try:
        mood_els = d.find_elements(By.CSS_SELECTOR,
            "[class*='mood'], [class*='emoji'], [class*='feeling'], [data-mood], "
            "button[class*='happy'], button[class*='good']")
        if mood_els:
            mood_els[0].click()
            time.sleep(1)
    except:
        pass

    # Try sliders or number inputs for energy/sleep
    try:
        range_inputs = d.find_elements(By.CSS_SELECTOR, "input[type='range'], input[type='number']")
        for ri in range_inputs:
            if ri.is_displayed():
                ri.clear()
                ri.send_keys("7")
    except:
        pass

    # Submit
    try:
        for text in ["Submit", "Save", "Check In", "Done"]:
            btns = d.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(2)
                    screenshot("wellness_submitted")
                    break
    except:
        pass

    # API
    if auth_token:
        for ep in ["/api/wellness/check-in", "/api/wellness/daily", "/api/wellness"]:
            r = api_post(ep, json_data={
                "mood": "good",
                "energy": 7,
                "sleep_hours": 7,
                "exercise": True,
                "exercise_duration": 30,
                "notes": "30 min walk"
            })
            if r and r.status_code in (200, 201):
                print(f"    [API] Wellness check-in at {ep}: {r.text[:200]}")
                break
            elif r:
                print(f"    [API] Wellness at {ep}: {r.status_code}")


def test_09_my_assets():
    """Check assigned assets."""
    print("\n=== 9. MY ASSETS ===")
    d = restart_driver_if_needed()

    asset_urls = [
        f"{BASE_URL}/assets", f"{BASE_URL}/my-assets", f"{BASE_URL}/assets/my",
        f"{BASE_URL}/self-service/assets", f"{BASE_URL}/employee/assets"
    ]

    found = False
    for url in asset_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["asset", "equipment", "device", "laptop", "assigned"]) and "404" not in d.title.lower():
            found = True
            break

    if not found:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Assets", "My Assets", "Equipment", "Devices"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found = True
                    break
        except:
            pass

    sp = screenshot("assets_page")
    record_result("Assets page accessible", found,
                  f"At {d.current_url}" if found else "Assets page not found")

    if found:
        page = d.page_source.lower()
        has_items = any(w in page for w in ["laptop", "monitor", "phone", "keyboard", "mouse",
                                            "serial", "category", "assigned", "asset"])
        record_result("Asset items visible", has_items,
                      "Assets displayed" if has_items else "No assets shown")

    # API
    if auth_token:
        for ep in ["/api/assets/my", "/api/assets", "/api/employee/assets"]:
            r = api_get(ep)
            if r and r.status_code == 200:
                print(f"    [API] Assets at {ep}: {r.text[:200]}")
                break


def test_10_policies():
    """Read and acknowledge company policies."""
    print("\n=== 10. COMPANY POLICIES ===")
    d = restart_driver_if_needed()

    policy_urls = [
        f"{BASE_URL}/policies", f"{BASE_URL}/policy", f"{BASE_URL}/company-policies",
        f"{BASE_URL}/self-service/policies", f"{BASE_URL}/employee/policies"
    ]

    found = False
    for url in policy_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["policy", "policies", "handbook", "guideline"]) and "404" not in d.title.lower():
            found = True
            break

    if not found:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Policies", "Policy", "Company Policies", "Handbook"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found = True
                    break
        except:
            pass

    sp = screenshot("policies_page")
    record_result("Policies page accessible", found,
                  f"At {d.current_url}" if found else "Policies page not found")

    if not found:
        return

    page = d.page_source.lower()

    # Try to view a policy
    try:
        links = d.find_elements(By.XPATH, "//a[contains(@href, 'polic')]")
        if links:
            links[0].click()
            time.sleep(2)
            screenshot("policy_detail")
    except:
        pass

    # Look for acknowledge button
    has_ack = any(w in page for w in ["acknowledge", "accept", "agree", "i have read", "confirm"])
    record_result("Acknowledge button", has_ack,
                  "Acknowledge option found" if has_ack else "No acknowledge button")

    if has_ack:
        try:
            for text in ["Acknowledge", "Accept", "I Agree", "Confirm", "I Have Read"]:
                btns = d.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                if btns:
                    btns[0].click()
                    time.sleep(2)
                    screenshot("policy_acknowledged")
                    record_result("Policy acknowledgement", True, "Acknowledged a policy")
                    break
        except:
            pass


def test_11_events():
    """Check upcoming events and RSVP."""
    print("\n=== 11. EVENTS ===")
    d = restart_driver_if_needed()

    event_urls = [
        f"{BASE_URL}/events", f"{BASE_URL}/event", f"{BASE_URL}/company-events",
        f"{BASE_URL}/self-service/events"
    ]

    found = False
    for url in event_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["event", "upcoming", "rsvp", "meeting", "celebration"]) and "404" not in d.title.lower():
            found = True
            break

    if not found:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Events", "Event", "Calendar", "Upcoming Events"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found = True
                    break
        except:
            pass

    sp = screenshot("events_page")
    record_result("Events page accessible", found,
                  f"At {d.current_url}" if found else "Events page not found")

    if found:
        page = d.page_source.lower()
        has_events = any(w in page for w in ["event", "date", "time", "location", "venue"])
        record_result("Events listed", has_events,
                      "Events displayed" if has_events else "No events visible")

        # Try RSVP
        try:
            for text in ["RSVP", "Register", "Join", "Attend", "Going"]:
                btns = d.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                if btns:
                    btns[0].click()
                    time.sleep(2)
                    screenshot("event_rsvp")
                    record_result("RSVP functionality", True, f"Clicked '{text}'")
                    break
        except:
            pass

    # API
    if auth_token:
        for ep in ["/api/events", "/api/events/upcoming", "/api/company-events"]:
            r = api_get(ep)
            if r and r.status_code == 200:
                print(f"    [API] Events at {ep}: {r.text[:200]}")
                break


def test_12_anonymous_feedback():
    """Submit anonymous feedback about cafeteria."""
    print("\n=== 12. ANONYMOUS FEEDBACK ===")
    d = restart_driver_if_needed()

    fb_urls = [
        f"{BASE_URL}/feedback", f"{BASE_URL}/feedback/submit", f"{BASE_URL}/my-feedback",
        f"{BASE_URL}/self-service/feedback", f"{BASE_URL}/employee/feedback"
    ]

    found = False
    for url in fb_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["feedback", "suggestion", "anonymous", "submit feedback"]) and "404" not in d.title.lower():
            found = True
            break

    if not found:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Feedback", "Submit Feedback", "Suggestions", "Anonymous Feedback"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found = True
                    break
        except:
            pass

    sp = screenshot("feedback_page")
    record_result("Feedback page accessible", found,
                  f"At {d.current_url}" if found else "Feedback page not found")

    if not found:
        return

    # Fill feedback form
    # Category
    try:
        selects = d.find_elements(By.TAG_NAME, "select")
        for s in selects:
            opts = [o.text.lower() for o in s.find_elements(By.TAG_NAME, "option")]
            if any("general" in o or "category" in o or "other" in o for o in opts):
                sel = Select(s)
                for opt in s.find_elements(By.TAG_NAME, "option"):
                    if "general" in opt.text.lower():
                        sel.select_by_visible_text(opt.text)
                        break
                break
    except:
        pass

    # Title
    try:
        for sel in ["input[name*='title']", "input[name*='subject']", "input[placeholder*='title']",
                     "input[placeholder*='subject']", "input[type='text']"]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    el.clear()
                    el.send_keys("Cafeteria food quality")
                    break
    except:
        pass

    # Message
    try:
        textareas = d.find_elements(By.TAG_NAME, "textarea")
        for ta in textareas:
            if ta.is_displayed():
                ta.clear()
                ta.send_keys("The lunch options have been repetitive lately. Would love more variety, especially vegetarian options.")
                break
    except:
        pass

    # Anonymous checkbox
    try:
        checkboxes = d.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        for cb in checkboxes:
            label = d.execute_script(
                "return arguments[0].closest('label')?.textContent || "
                "document.querySelector('label[for=\"' + arguments[0].id + '\"]')?.textContent || ''", cb)
            if "anonym" in (label or "").lower():
                if not cb.is_selected():
                    cb.click()
                break
    except:
        pass

    # Submit
    submitted = False
    try:
        for text in ["Submit", "Send", "Post", "Save"]:
            btns = d.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(3)
                    submitted = True
                    break
            if submitted:
                break
    except:
        pass

    sp = screenshot("feedback_submitted")
    page_after = d.page_source.lower()
    success = any(w in page_after for w in ["success", "submitted", "thank", "received"])
    record_result("Feedback submission", submitted,
                  "Submitted" + (" with confirmation" if success else " (no confirmation)"))

    # API
    if auth_token:
        for ep in ["/api/feedback", "/api/feedback/submit", "/api/feedbacks"]:
            r = api_post(ep, json_data={
                "category": "general",
                "title": "Cafeteria food quality (API test)",
                "message": "The lunch options have been repetitive lately. Would love more variety, especially vegetarian options.",
                "anonymous": True
            })
            if r and r.status_code in (200, 201):
                print(f"    [API] Feedback at {ep}: {r.text[:200]}")
                break
            elif r:
                print(f"    [API] Feedback at {ep}: {r.status_code}")


def test_13_community_forum():
    """Post in community forum."""
    print("\n=== 13. COMMUNITY FORUM ===")
    d = restart_driver_if_needed()

    forum_urls = [
        f"{BASE_URL}/forum", f"{BASE_URL}/community", f"{BASE_URL}/discussions",
        f"{BASE_URL}/social", f"{BASE_URL}/posts"
    ]

    found = False
    for url in forum_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["forum", "community", "discussion", "post", "thread", "topic"]) and "404" not in d.title.lower():
            found = True
            break

    if not found:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Forum", "Community", "Discussions", "Social", "Posts"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found = True
                    break
        except:
            pass

    sp = screenshot("forum_page")
    record_result("Forum/Community page accessible", found,
                  f"At {d.current_url}" if found else "Forum page not found")

    if not found:
        return

    # Create a post
    try:
        for text in ["New Post", "Create Post", "New Topic", "New Discussion", "Write", "Post"]:
            btns = d.find_elements(By.XPATH,
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')] | "
                f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                screenshot("forum_new_post")

                # Title
                for sel in ["input[name*='title']", "input[placeholder*='title']", "input[type='text']"]:
                    els = d.find_elements(By.CSS_SELECTOR, sel)
                    for el in els:
                        if el.is_displayed():
                            el.clear()
                            el.send_keys("Best coffee spots near office?")
                            break

                # Content
                textareas = d.find_elements(By.TAG_NAME, "textarea")
                for ta in textareas:
                    if ta.is_displayed():
                        ta.clear()
                        ta.send_keys("Looking for good coffee places within walking distance. Any recommendations?")
                        break

                # Submit
                for st in ["Submit", "Post", "Publish", "Create", "Send"]:
                    sub_btns = d.find_elements(By.XPATH, f"//button[contains(text(), '{st}')]")
                    for btn in sub_btns:
                        if btn.is_displayed() and btn.is_enabled():
                            btn.click()
                            time.sleep(2)
                            screenshot("forum_posted")
                            record_result("Forum post created", True, "Post submitted")
                            break
                break
    except Exception as e:
        print(f"    Forum post error: {e}")


def test_14_whistleblowing():
    """Submit an anonymous whistleblowing report."""
    print("\n=== 14. WHISTLEBLOWING REPORT ===")
    d = restart_driver_if_needed()

    wb_urls = [
        f"{BASE_URL}/whistleblowing", f"{BASE_URL}/whistleblower", f"{BASE_URL}/ethics",
        f"{BASE_URL}/report", f"{BASE_URL}/anonymous-report"
    ]

    found = False
    for url in wb_urls:
        safe_navigate(url)
        page = d.page_source.lower()
        if any(w in page for w in ["whistleblow", "report", "ethics", "anonymous report", "concern"]) and "404" not in d.title.lower():
            found = True
            break

    if not found:
        safe_navigate(f"{BASE_URL}/dashboard")
        time.sleep(2)
        try:
            for lt in ["Whistleblowing", "Ethics", "Report Concern", "Anonymous Report"]:
                links = d.find_elements(By.XPATH, f"//a[contains(text(), '{lt}')]")
                if links:
                    links[0].click()
                    time.sleep(3)
                    found = True
                    break
        except:
            pass

    sp = screenshot("whistleblowing_page")
    record_result("Whistleblowing page accessible", found,
                  f"At {d.current_url}" if found else "Whistleblowing page not found")

    if not found:
        return

    # Fill report form
    try:
        # Try to find and click submit report
        for text in ["Submit Report", "New Report", "File Report", "Report", "Submit"]:
            btns = d.find_elements(By.XPATH,
                f"//button[contains(text(), '{text}')] | //a[contains(text(), '{text}')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                break

        # Fill fields
        textareas = d.find_elements(By.TAG_NAME, "textarea")
        for ta in textareas:
            if ta.is_displayed():
                ta.send_keys("Test report: This is a confidential test submission for the whistleblowing system verification.")
                break

        inputs = d.find_elements(By.CSS_SELECTOR, "input[type='text']")
        for inp in inputs:
            if inp.is_displayed() and inp.is_enabled():
                inp.send_keys("System test - please ignore")
                break

        # Anonymous checkbox
        checkboxes = d.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        for cb in checkboxes:
            if not cb.is_selected():
                cb.click()
                break

        # Submit
        for text in ["Submit", "Send", "Report"]:
            btns = d.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(2)
                    screenshot("whistleblowing_submitted")
                    record_result("Whistleblowing report submitted", True, "Report submitted")
                    break
    except Exception as e:
        print(f"    Whistleblowing error: {e}")

    # Check tracking
    try:
        for text in ["Track", "My Reports", "Status", "View Reports"]:
            links = d.find_elements(By.XPATH, f"//a[contains(text(), '{text}')] | //button[contains(text(), '{text}')]")
            if links:
                links[0].click()
                time.sleep(2)
                screenshot("whistleblowing_tracking")
                record_result("Whistleblowing tracking", True, "Tracking page accessible")
                break
    except:
        pass


def test_15_notifications():
    """Check notification bell."""
    print("\n=== 15. NOTIFICATIONS ===")
    d = restart_driver_if_needed()

    safe_navigate(f"{BASE_URL}/dashboard")
    time.sleep(3)

    # Find notification bell
    bell_found = False
    try:
        for sel in ["[class*='notification'], [class*='bell'], [aria-label*='notification'], "
                     "[data-testid*='notification'], .notification-bell, .notifications, "
                     "svg[class*='bell'], i[class*='bell'], button[class*='notif']"]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            if els:
                for el in els:
                    if el.is_displayed():
                        el.click()
                        time.sleep(2)
                        bell_found = True
                        break
            if bell_found:
                break
    except:
        pass

    # Also try by badge/icon
    if not bell_found:
        try:
            icons = d.find_elements(By.CSS_SELECTOR, "svg, i, span[class*='icon']")
            for icon in icons:
                title = icon.get_attribute("title") or icon.get_attribute("aria-label") or ""
                if "notif" in title.lower() or "bell" in title.lower():
                    icon.click()
                    time.sleep(2)
                    bell_found = True
                    break
        except:
            pass

    sp = screenshot("notifications")
    record_result("Notification bell accessible", bell_found,
                  "Bell clicked" if bell_found else "Notification bell not found")

    if bell_found:
        page = d.page_source.lower()
        has_notifs = any(w in page for w in ["notification", "no notification", "mark as read", "read all", "unread"])
        record_result("Notifications display", has_notifs,
                      "Notification area visible" if has_notifs else "No notification content")

        # Try mark as read
        try:
            for text in ["Mark as Read", "Mark All Read", "Read All", "Clear"]:
                btns = d.find_elements(By.XPATH, f"//button[contains(text(), '{text}')] | //a[contains(text(), '{text}')]")
                if btns:
                    btns[0].click()
                    time.sleep(1)
                    record_result("Mark notifications read", True, "Clicked mark as read")
                    break
        except:
            pass

    # API
    if auth_token:
        for ep in ["/api/notifications", "/api/notifications/my", "/api/notification"]:
            r = api_get(ep)
            if r and r.status_code == 200:
                print(f"    [API] Notifications at {ep}: {r.text[:200]}")
                break


def test_16_ai_chatbot():
    """Test the AI chatbot."""
    print("\n=== 16. AI CHATBOT ===")
    d = restart_driver_if_needed()

    safe_navigate(f"{BASE_URL}/dashboard")
    time.sleep(3)

    # Find chatbot bubble (purple, bottom-right)
    chatbot_found = False
    try:
        for sel in ["[class*='chatbot'], [class*='chat-bot'], [class*='chat-bubble'], "
                     "[class*='floating'], [class*='assistant'], [id*='chatbot'], [id*='chat'], "
                     ".chat-widget, .chatbot-bubble, button[class*='chat']"]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    el.click()
                    time.sleep(2)
                    chatbot_found = True
                    break
            if chatbot_found:
                break
    except:
        pass

    # Try fixed position elements at bottom right
    if not chatbot_found:
        try:
            all_els = d.find_elements(By.CSS_SELECTOR, "button, div[role='button']")
            for el in all_els:
                try:
                    pos = el.location
                    size = el.size
                    if pos['x'] > 1700 and pos['y'] > 800:
                        el.click()
                        time.sleep(2)
                        chatbot_found = True
                        break
                except:
                    continue
        except:
            pass

    sp = screenshot("chatbot")
    record_result("AI Chatbot accessible", chatbot_found,
                  "Chatbot opened" if chatbot_found else "Chatbot bubble not found")

    if chatbot_found:
        # Try sending a message
        try:
            for sel in ["input[placeholder*='message'], input[placeholder*='type'], "
                        "input[placeholder*='ask'], textarea[placeholder*='message'], "
                        "textarea, input[type='text']"]:
                inputs = d.find_elements(By.CSS_SELECTOR, sel)
                for inp in inputs:
                    if inp.is_displayed():
                        inp.send_keys("What is my leave balance?")
                        inp.send_keys(Keys.RETURN)
                        time.sleep(5)
                        screenshot("chatbot_leave_question")

                        # Check for response
                        page = d.page_source.lower()
                        has_response = any(w in page for w in ["leave", "balance", "day", "sorry", "help"])
                        record_result("Chatbot responds to leave query", has_response,
                                      "Got a response" if has_response else "No response")

                        # Ask another question
                        time.sleep(1)
                        inp.clear()
                        inp.send_keys("How do I apply for leave?")
                        inp.send_keys(Keys.RETURN)
                        time.sleep(5)
                        screenshot("chatbot_apply_question")
                        break
                break
        except Exception as e:
            print(f"    Chatbot interaction error: {e}")


def test_17_clock_out():
    """End of day — clock out."""
    print("\n=== 17. CLOCK OUT ===")
    d = restart_driver_if_needed()

    safe_navigate(f"{BASE_URL}/dashboard")
    time.sleep(3)

    # Try clock out button
    clocked_out = False
    try:
        for text in ["Clock Out", "Check Out", "Punch Out", "Mark Out"]:
            btns = d.find_elements(By.XPATH,
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')] | "
                f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                clocked_out = True
                screenshot("clock_out")
                break
    except:
        pass

    # Also try attendance page
    if not clocked_out:
        for url in [f"{BASE_URL}/attendance", f"{BASE_URL}/my-attendance"]:
            safe_navigate(url)
            time.sleep(2)
            try:
                for text in ["Clock Out", "Check Out", "Punch Out"]:
                    btns = d.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                    if btns:
                        btns[0].click()
                        time.sleep(2)
                        clocked_out = True
                        screenshot("clock_out_attendance")
                        break
            except:
                pass
            if clocked_out:
                break

    record_result("Clock out", clocked_out,
                  "Clocked out successfully" if clocked_out else "Could not find clock out button")

    if not clocked_out:
        sp = screenshot("no_clock_out")
        record_issue("Can't find 'Clock Out' button at end of day",
                     "After a full day of work, I can't find how to clock out. "
                     "There should be a clear Clock Out button on the dashboard or attendance page.",
                     sp, ["bug", "employee-journey", "attendance"])

    # API clock out
    if auth_token:
        for ep in ["/api/attendance/clock-out", "/api/attendance/check-out", "/api/attendance/punch-out"]:
            r = api_post(ep)
            if r and r.status_code in (200, 201):
                print(f"    [API] Clock out at {ep}: {r.text[:200]}")
                break


def test_18_ux_frustrations():
    """Test for UX issues that would frustrate a real employee."""
    print("\n=== 18. UX & NAVIGATION CHECK ===")
    d = restart_driver_if_needed()

    safe_navigate(f"{BASE_URL}/dashboard")
    time.sleep(3)

    # Check sidebar links
    sidebar_links = []
    try:
        nav_links = d.find_elements(By.CSS_SELECTOR, "nav a, aside a, .sidebar a, [class*='sidebar'] a, [class*='nav'] a")
        for link in nav_links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            if href and text:
                sidebar_links.append({"text": text, "href": href})
    except:
        pass

    print(f"    Found {len(sidebar_links)} sidebar links")
    record_result("Sidebar navigation", len(sidebar_links) > 0,
                  f"{len(sidebar_links)} links found")

    # Check for dead links (sample a few)
    dead_links = []
    checked = 0
    for link_info in sidebar_links[:15]:
        href = link_info["href"]
        if not href.startswith("http"):
            continue
        # Skip external/field/biometrics
        if any(skip in href.lower() for skip in ["field", "biometric", "empmonitor"]):
            continue
        try:
            safe_navigate(href, wait_secs=4)
            page = d.page_source.lower()
            title = d.title.lower()
            if "404" in title or "not found" in page or "error" in title:
                dead_links.append(link_info)
                screenshot(f"dead_link_{checked}")
            checked += 1
        except:
            pass
        if checked >= 8:
            break

    if dead_links:
        sp = screenshot("dead_links_found")
        links_text = "\n".join([f"- {l['text']}: {l['href']}" for l in dead_links])
        record_issue("Dead links in sidebar navigation",
                     f"Found {len(dead_links)} dead/broken links in the sidebar:\n{links_text}\n\n"
                     "These lead to 404 or error pages.",
                     sp, ["bug", "employee-journey", "navigation"])
    record_result("Dead links check", len(dead_links) == 0,
                  f"{len(dead_links)} dead links found" if dead_links else "No dead links")

    # Mobile responsiveness test
    safe_navigate(f"{BASE_URL}/dashboard")
    time.sleep(2)
    try:
        d.set_window_size(375, 812)  # iPhone X size
        time.sleep(2)
        sp = screenshot("mobile_view_375")

        # Check if content is visible and not broken
        page = d.page_source.lower()
        # Look for overlapping/hidden elements
        body = d.find_element(By.TAG_NAME, "body")
        body_width = body.size["width"]
        has_horizontal_scroll = d.execute_script("return document.documentElement.scrollWidth > document.documentElement.clientWidth")

        record_result("Mobile view (375px)", not has_horizontal_scroll,
                      "No horizontal scroll" if not has_horizontal_scroll else "Has horizontal scroll — content overflows")

        if has_horizontal_scroll:
            record_issue("Dashboard overflows on mobile view (375px wide)",
                         "When viewing the dashboard on a mobile-sized screen (375px), "
                         "the content overflows horizontally. This makes it very difficult to use on a phone.",
                         sp, ["bug", "employee-journey", "responsive"])

        # Reset to desktop
        d.set_window_size(1920, 1080)
        time.sleep(1)
    except Exception as e:
        print(f"    Mobile test error: {e}")
        d.set_window_size(1920, 1080)

    # Page load time check
    safe_navigate(f"{BASE_URL}/dashboard")
    start_time = time.time()
    try:
        WebDriverWait(d, 10).until(
            lambda x: x.execute_script("return document.readyState") == "complete"
        )
    except:
        pass
    load_time = time.time() - start_time
    record_result("Dashboard load time", load_time < 5,
                  f"Loaded in {load_time:.1f}s")
    if load_time > 5:
        record_issue("Dashboard takes too long to load",
                     f"The dashboard took {load_time:.1f} seconds to load. "
                     "That's too slow for daily use.",
                     None, ["performance", "employee-journey", "dashboard"])


# ── Main Runner ─────────────────────────────────────────────────────────────

def main():
    global driver, auth_token

    print("=" * 70)
    print("PRIYA PATEL'S WORKDAY — EMP Cloud Employee Journey")
    print(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # API login first
    print("\n--- API Login ---")
    api_login()

    # Run all tests
    tests = [
        test_01_morning_login_dashboard,
        test_02_check_profile,
        test_03_apply_leave,
        test_04_attendance_history,
        test_05_helpdesk_ticket,
        test_06_payslip,
        test_07_survey,
        test_08_wellness_checkin,
        test_09_my_assets,
        test_10_policies,
        test_11_events,
        test_12_anonymous_feedback,
        test_13_community_forum,
        test_14_whistleblowing,
        test_15_notifications,
        test_16_ai_chatbot,
        test_17_clock_out,
        test_18_ux_frustrations,
    ]

    for test_fn in tests:
        try:
            ensure_driver()
            test_fn()
        except Exception as e:
            print(f"  [ERROR] {test_fn.__name__}: {e}")
            traceback.print_exc()
            try:
                screenshot(f"error_{test_fn.__name__}")
            except:
                pass

    # Cleanup
    if driver:
        try:
            driver.quit()
        except:
            pass

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in test_results if r["passed"])
    failed = sum(1 for r in test_results if not r["passed"])
    total = len(test_results)
    print(f"Tests: {total} total, {passed} passed, {failed} failed")
    print(f"Issues filed: {len(issues_found)}")

    if issues_found:
        print("\nIssues Filed on GitHub:")
        for issue in issues_found:
            print(f"  - {issue['title']}")
            print(f"    {issue['url']}")

    print("\nFailed Tests:")
    for r in test_results:
        if not r["passed"]:
            print(f"  - {r['test']}: {r['details']}")

    print("\nAll Test Results:")
    for r in test_results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['test']}: {r['details']}")

    # Save results
    results_path = r"C:\emptesting\employee_journey_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.datetime.now().isoformat(),
            "user": "priya@technova.in",
            "summary": {"total": total, "passed": passed, "failed": failed},
            "issues_filed": issues_found,
            "results": test_results
        }, f, indent=2)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
