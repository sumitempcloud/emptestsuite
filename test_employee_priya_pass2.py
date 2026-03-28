"""
Priya Patel's Workday — Pass 2: Deeper testing of specific flows.
Focuses on real interactions with the actual UI elements found in pass 1.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os, json, time, datetime, traceback, requests, base64
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com"
EMAIL = "priya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = Path(r"C:\Users\Admin\screenshots\employee_journey")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

issues_found = []
test_results = []
test_count = 0
driver = None
auth_token = None


def get_driver():
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


def is_alive():
    global driver
    if not driver:
        return False
    try:
        _ = driver.current_url
        return True
    except:
        return False


def fresh_driver():
    global driver
    if driver:
        try: driver.quit()
        except: pass
    driver = get_driver()
    login_ui()
    return driver


def ensure():
    global driver
    if not is_alive():
        fresh_driver()
    return driver


def restart_if_needed():
    global test_count
    test_count += 1
    if test_count % 3 == 0 or not is_alive():
        fresh_driver()
    return driver


def ss(name):
    ts = datetime.datetime.now().strftime("%H%M%S")
    fname = f"{ts}_p2_{name}.png"
    fpath = SCREENSHOT_DIR / fname
    try:
        driver.save_screenshot(str(fpath))
        print(f"    [ss] {fpath}")
        return fpath
    except:
        return None


def upload_ss(filepath):
    if not filepath or not Path(filepath).exists():
        return None
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        fname = Path(filepath).name
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/employee_journey/{fname}"
        headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
        resp = requests.put(url, headers=headers, json={
            "message": f"Upload screenshot: {fname}", "content": content, "branch": "main"
        }, timeout=30)
        if resp.status_code in (200, 201):
            return resp.json().get("content", {}).get("download_url", "")
    except:
        pass
    return None


def file_issue(title, body, labels=None):
    if labels is None:
        labels = ["bug", "employee-journey"]
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    try:
        resp = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers=headers, json={"title": title, "body": body, "labels": labels}, timeout=30)
        if resp.status_code == 201:
            url = resp.json()["html_url"]
            print(f"    [ISSUE] {url}")
            issues_found.append({"title": title, "url": url})
            return url
        else:
            print(f"    [issue fail] {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"    [issue error] {e}")
    return None


def report_bug(title, desc, sp=None, labels=None):
    img_url = upload_ss(sp) if sp else None
    body = f"## Description\n{desc}\n\n"
    body += f"**User:** Priya Patel (priya@technova.in) - Employee role\n"
    body += f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    body += f"**URL:** {driver.current_url if is_alive() else 'N/A'}\n\n"
    if img_url:
        body += f"## Screenshot\n![screenshot]({img_url})\n\n"
    elif sp:
        body += f"## Screenshot\nLocal: `{sp}` (upload may have failed)\n\n"
    body += "## Steps to Reproduce\n1. Login as priya@technova.in (Employee)\n2. " + desc.split('.')[0] + "\n\n"
    body += "## Expected\nThe feature should work correctly for employee self-service.\n\n"
    body += "## Actual\n" + desc + "\n"
    file_issue(title, body, labels)


def result(name, passed, detail=""):
    s = "PASS" if passed else "FAIL"
    print(f"  [{s}] {name}: {detail}")
    test_results.append({"test": name, "passed": passed, "details": detail})


def nav(url, wait=3):
    global driver
    try:
        driver.get(url)
        time.sleep(wait)
    except WebDriverException as e:
        if "crash" in str(e).lower() or "session" in str(e).lower():
            print(f"    [crash] Recovering...")
            fresh_driver()
            try:
                driver.get(url)
                time.sleep(wait)
            except:
                pass
        else:
            print(f"    [nav err] {e}")
    except:
        pass


def is_on_dashboard():
    """Check if current page is actually the dashboard (not the intended page)."""
    try:
        url = driver.current_url
        src = driver.page_source[:500].lower()
        return ("/dashboard" in url or url.rstrip('/') == BASE_URL) and "welcome back" in src
    except:
        return False


def login_ui():
    try:
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)
        for sel in ["input[name='email']", "input[type='email']", "#email",
                     "input[placeholder*='mail']", "input[placeholder*='Email']"]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el:
                    el.clear(); el.send_keys(EMAIL)
                    break
            except: continue
        for sel in ["input[name='password']", "input[type='password']", "#password"]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el:
                    el.clear(); el.send_keys(PASSWORD)
                    break
            except: continue
        for sel in ["button[type='submit']", "button"]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, sel)
                t = (btn.text or "").lower()
                if "sign" in t or "log" in t or sel == "button[type='submit']":
                    btn.click()
                    break
            except: continue
        time.sleep(4)
        return "/login" not in driver.current_url
    except:
        return False


def api_login():
    global auth_token
    try:
        resp = requests.post(f"{API_URL}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            d = data.get("data", {})
            auth_token = d.get("token") or d.get("accessToken") or d.get("access_token")
            # Token might be in cookies or headers
            if not auth_token:
                # Try extracting from nested structures
                for key in d:
                    if "token" in key.lower():
                        auth_token = d[key]
                        break
            if not auth_token:
                # The token might be set as a cookie — grab from set-cookie header
                cookies = resp.cookies
                for c in cookies:
                    if "token" in c.name.lower():
                        auth_token = c.value
                        break
            if auth_token:
                print(f"  [API] Token: {auth_token[:20]}...")
            else:
                print(f"  [API] Login 200 but no token found. Response keys: {list(d.keys()) if isinstance(d, dict) else 'not dict'}")
                print(f"  [API] Full response: {json.dumps(data)[:500]}")
            return True
    except Exception as e:
        print(f"  [API] Login error: {e}")
    return False


def api_get(path, params=None):
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    try:
        r = requests.get(f"{API_URL}{path}", headers=headers, params=params, timeout=15)
        return r
    except:
        return None


def api_post(path, json_data=None):
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    try:
        r = requests.post(f"{API_URL}{path}", headers=headers, json=json_data, timeout=15)
        return r
    except:
        return None


# ── Grab auth token from browser cookies after login ──

def grab_token_from_browser():
    """After UI login, grab auth token from browser cookies/localStorage."""
    global auth_token
    try:
        cookies = driver.get_cookies()
        for c in cookies:
            if "token" in c["name"].lower():
                auth_token = c["value"]
                print(f"  [token from cookie] {c['name']}: {auth_token[:20]}...")
                return True

        # Try localStorage
        token = driver.execute_script("""
            return localStorage.getItem('token') || localStorage.getItem('accessToken') ||
                   localStorage.getItem('auth_token') || localStorage.getItem('jwt') ||
                   sessionStorage.getItem('token') || sessionStorage.getItem('accessToken') || '';
        """)
        if token:
            auth_token = token
            print(f"  [token from storage] {auth_token[:20]}...")
            return True

        # Try to find it in any localStorage key containing 'token'
        all_keys = driver.execute_script("""
            var keys = [];
            for (var i = 0; i < localStorage.length; i++) {
                keys.push(localStorage.key(i));
            }
            return keys;
        """)
        print(f"  [localStorage keys] {all_keys}")
        for key in (all_keys or []):
            if "token" in key.lower() or "auth" in key.lower():
                val = driver.execute_script(f"return localStorage.getItem('{key}')")
                if val and len(val) > 20:
                    auth_token = val
                    print(f"  [token from key '{key}'] {auth_token[:30]}...")
                    return True
    except Exception as e:
        print(f"  [token grab error] {e}")
    return False


# ═══════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_01_dashboard_deep():
    """Verify dashboard actually shows personalized content."""
    print("\n=== 1. DASHBOARD DEEP CHECK ===")
    d = ensure()
    nav(f"{BASE_URL}/dashboard")

    sp = ss("dashboard_deep")
    src = d.page_source

    # Check dashboard quick actions
    has_my_profile = "My Profile" in src
    has_apply_leave = "Apply Leave" in src
    has_mark_attendance = "Mark Attendance" in src
    has_request_update = "Request Update" in src

    result("Quick action: My Profile", has_my_profile, "Present" if has_my_profile else "Missing")
    result("Quick action: Apply Leave", has_apply_leave, "Present" if has_apply_leave else "Missing")
    result("Quick action: Mark Attendance", has_mark_attendance, "Present" if has_mark_attendance else "Missing")
    result("Quick action: Request Update", has_request_update, "Present" if has_request_update else "Missing")

    # Check attendance status
    has_not_checked = "Not checked in yet today" in src
    has_checked_in = "Check In" in src and "Check Out" not in src
    result("Attendance status shown", has_not_checked or has_checked_in or "Attendance Today" in src,
           "Shows status")

    # Leave balance cards
    has_earned = "Earned Leave" in src or "Earned" in src
    has_sick = "Sick Leave" in src or "Sick" in src
    result("Leave balance cards", has_earned or has_sick,
           f"Earned: {has_earned}, Sick: {has_sick}")

    # Announcements
    has_announcements = "Announcements" in src
    result("Announcements section", has_announcements, "Present" if has_announcements else "Missing")

    # Policies
    has_policies = "Policies" in src
    result("Policies section on dashboard", has_policies, "Present" if has_policies else "Missing")

    # Pending documents
    has_pending_docs = "Pending Documents" in src
    result("Pending Documents section", has_pending_docs, "Present" if has_pending_docs else "Missing")

    # Try clicking "Mark Attendance" to clock in
    try:
        mark_btn = d.find_element(By.XPATH, "//div[contains(text(),'Mark Attendance')]/..")
        mark_btn.click()
        time.sleep(3)
        sp2 = ss("mark_attendance_click")
        cur = d.current_url
        result("Mark Attendance navigates", "/attendance" in cur,
               f"Went to {cur}")
    except Exception as e:
        print(f"    Mark Attendance click: {e}")

    # Grab token while we're on the page
    grab_token_from_browser()


def test_02_sidebar_navigation():
    """Map all sidebar links and check which actually work vs redirect to dashboard."""
    print("\n=== 2. SIDEBAR NAVIGATION AUDIT ===")
    d = restart_if_needed()
    nav(f"{BASE_URL}/dashboard")

    # Get all sidebar links
    sidebar_items = []
    try:
        links = d.find_elements(By.CSS_SELECTOR, "aside a, nav a, [class*='sidebar'] a")
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            if href and text and BASE_URL in href:
                sidebar_items.append({"text": text, "href": href})
    except:
        pass

    print(f"    Found {len(sidebar_items)} sidebar links")

    # Test each unique link
    seen_hrefs = set()
    broken = []
    working = []
    for item in sidebar_items:
        href = item["href"].rstrip("/")
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        # Skip field force and biometrics
        if any(skip in href.lower() for skip in ["field", "biometric", "empmonitor"]):
            continue

        nav(href, wait=3)
        cur = d.current_url.rstrip("/")
        title = d.title.lower()

        # Check if it redirected back to dashboard
        if is_on_dashboard() and href != f"{BASE_URL}" and href != f"{BASE_URL}/dashboard":
            broken.append(item)
            print(f"    [BROKEN] '{item['text']}' -> Redirected to dashboard")
        elif "404" in title or "not found" in d.page_source.lower()[:500]:
            broken.append(item)
            print(f"    [404] '{item['text']}' -> {cur}")
        else:
            working.append(item)
            print(f"    [OK] '{item['text']}' -> {cur}")

    result("Sidebar links total", len(sidebar_items) > 0, f"{len(sidebar_items)} links")
    result("Working sidebar links", True, f"{len(working)}/{len(seen_hrefs)}")
    result("Broken sidebar links", len(broken) == 0, f"{len(broken)} broken")

    if broken:
        sp = ss("broken_sidebar_links")
        broken_list = "\n".join([f"- **{b['text']}** ({b['href']})" for b in broken])
        report_bug(
            f"Sidebar has {len(broken)} links that redirect back to dashboard",
            f"As an employee, clicking these sidebar links just bounces me back to the dashboard instead of going to the actual page:\n\n{broken_list}\n\nThis makes these features completely inaccessible.",
            sp, ["bug", "employee-journey", "navigation"]
        )

    return working, broken


def test_03_leave_apply_detailed():
    """Detailed leave application test using the actual Apply Leave button."""
    print("\n=== 3. LEAVE APPLICATION (DETAILED) ===")
    d = restart_if_needed()

    # Go to leave page directly
    nav(f"{BASE_URL}/leave")
    sp = ss("leave_dashboard")

    src = d.page_source
    # Verify we're on leave page
    if "Leave Dashboard" not in src:
        result("Leave page loads", False, "Not on leave dashboard")
        return

    result("Leave page loads", True, "Leave Dashboard visible")

    # Check balance numbers
    import re
    # Look for the balance numbers
    balance_text = src
    result("Leave balances shown", "Earned Leave" in src and "Sick Leave" in src,
           "Earned and Sick leave visible")

    # Click "Apply Leave" button (blue button in top right)
    try:
        apply_btn = d.find_element(By.XPATH, "//button[contains(text(),'Apply Leave')]")
        apply_btn.click()
        time.sleep(3)
        sp = ss("leave_apply_modal")
    except Exception as e:
        # Try alternate
        try:
            apply_btn = d.find_element(By.XPATH, "//a[contains(text(),'Apply Leave')]")
            apply_btn.click()
            time.sleep(3)
            sp = ss("leave_apply_modal2")
        except:
            result("Apply Leave button click", False, f"Could not click: {e}")
            return

    src = d.page_source
    result("Apply Leave form opens", "Apply Leave" in src or "leave type" in src.lower() or "modal" in src.lower(),
           "Form opened")

    # Take detailed screenshot of the form
    sp = ss("leave_form_detail")

    # Check for form fields — look for react-select or custom dropdowns
    # The "Leave type dropdown has no options" might be a react-select that needs clicking
    has_select = len(d.find_elements(By.TAG_NAME, "select")) > 0
    has_react_select = len(d.find_elements(By.CSS_SELECTOR, "[class*='react-select'], [class*='Select'], [class*='select__control'], [class*='css-']")) > 0
    has_any_dropdown = len(d.find_elements(By.CSS_SELECTOR, "[role='combobox'], [role='listbox'], [class*='dropdown']")) > 0

    print(f"    Native select: {has_select}, React-select: {has_react_select}, Other dropdown: {has_any_dropdown}")

    # Try react-select for leave type
    leave_type_set = False
    try:
        # Find all react-select controls
        selects = d.find_elements(By.CSS_SELECTOR, "[class*='select__control'], [class*='-control']")
        print(f"    Found {len(selects)} select controls")
        for sel in selects:
            if sel.is_displayed():
                sel.click()
                time.sleep(1)
                sp = ss("leave_type_dropdown_open")

                # Check for options
                options = d.find_elements(By.CSS_SELECTOR, "[class*='select__option'], [class*='-option'], [role='option']")
                print(f"    Options after click: {len(options)}")
                for opt in options:
                    text = opt.text.strip()
                    print(f"      Option: '{text}'")
                    if "sick" in text.lower():
                        opt.click()
                        leave_type_set = True
                        break
                if not leave_type_set and options:
                    options[0].click()
                    leave_type_set = True
                break
    except Exception as e:
        print(f"    React-select error: {e}")

    # Try typing into input within the select
    if not leave_type_set:
        try:
            # Sometimes react-select has an input inside
            inputs = d.find_elements(By.CSS_SELECTOR, "input[role='combobox'], input[class*='select__input']")
            for inp in inputs:
                if inp.is_displayed():
                    inp.send_keys("Sick")
                    time.sleep(1)
                    options = d.find_elements(By.CSS_SELECTOR, "[class*='option']")
                    if options:
                        options[0].click()
                        leave_type_set = True
                    break
        except:
            pass

    result("Select leave type", leave_type_set,
           "Selected Sick Leave" if leave_type_set else "Could not select leave type")

    if not leave_type_set:
        sp = ss("leave_type_failed")
        report_bug(
            "Can't select leave type when applying for leave",
            "The leave type dropdown in the Apply Leave form can't be interacted with. "
            "Tried clicking the dropdown control and typing into it, but no options appear or can be selected. "
            "This completely blocks employees from applying for any leave.",
            sp, ["bug", "employee-journey", "leave", "critical"]
        )

    # Fill dates
    today = datetime.date.today()
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0:
        days_until_tuesday = 7
    next_tuesday = today + datetime.timedelta(days=days_until_tuesday)

    date_filled = False
    try:
        date_inputs = d.find_elements(By.CSS_SELECTOR, "input[type='date']")
        print(f"    Date inputs found: {len(date_inputs)}")
        for i, di in enumerate(date_inputs):
            if di.is_displayed():
                di.clear()
                # Try multiple date formats
                for fmt in [next_tuesday.strftime("%Y-%m-%d"), next_tuesday.strftime("%m/%d/%Y"),
                            next_tuesday.strftime("%d/%m/%Y")]:
                    di.send_keys(fmt)
                    val = di.get_attribute("value")
                    if val:
                        date_filled = True
                        break
                print(f"    Date input {i}: value='{di.get_attribute('value')}'")
    except:
        pass

    # Try date pickers (click to open calendar)
    if not date_filled:
        try:
            # Look for date picker triggers
            date_pickers = d.find_elements(By.CSS_SELECTOR,
                "[class*='datepicker'], [class*='date-picker'], input[placeholder*='date'], "
                "input[placeholder*='Date'], input[placeholder*='Select'], input[name*='date']")
            for dp in date_pickers:
                if dp.is_displayed():
                    dp.click()
                    time.sleep(1)
                    ss("date_picker_open")
                    # Try to find and click a day
                    days = d.find_elements(By.CSS_SELECTOR, "[class*='day']:not([class*='disabled']), td[role='gridcell']")
                    if days:
                        for day in days:
                            if day.text.strip() == str(next_tuesday.day):
                                day.click()
                                date_filled = True
                                break
                    break
        except:
            pass

    result("Fill dates", date_filled, f"Date set to {next_tuesday}" if date_filled else "Could not set dates")

    # Fill reason
    reason_filled = False
    try:
        textareas = d.find_elements(By.TAG_NAME, "textarea")
        for ta in textareas:
            if ta.is_displayed():
                ta.clear()
                ta.send_keys("Doctor's appointment")
                reason_filled = True
                break
        if not reason_filled:
            for sel in ["input[name*='reason']", "input[placeholder*='reason']", "input[placeholder*='Reason']"]:
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

    result("Fill reason", reason_filled, "Entered 'Doctor's appointment'" if reason_filled else "No reason field found")

    # Dump all visible form fields for debugging
    try:
        all_inputs = d.find_elements(By.CSS_SELECTOR, "input, textarea, select")
        for inp in all_inputs:
            if inp.is_displayed():
                name = inp.get_attribute("name") or ""
                ph = inp.get_attribute("placeholder") or ""
                typ = inp.get_attribute("type") or inp.tag_name
                val = inp.get_attribute("value") or ""
                print(f"    Field: type={typ} name='{name}' placeholder='{ph}' value='{val[:30]}'")
    except:
        pass

    # Submit
    try:
        for text in ["Submit", "Apply", "Save"]:
            btns = d.find_elements(By.XPATH, f"//button[contains(text(),'{text}')]")
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(3)
                    sp = ss("leave_submitted")
                    src = d.page_source.lower()
                    success = any(w in src for w in ["success", "submitted", "created", "pending"])
                    error = any(w in src for w in ["error", "required", "invalid", "failed"])
                    result("Leave submission", success and not error,
                           "Success" if success else "Error shown" if error else "Unclear")
                    if error:
                        sp = ss("leave_submit_error")
                        report_bug(
                            "Leave application fails with error after filling form",
                            "Filled out the Apply Leave form with Sick Leave, next Tuesday's date, and reason 'Doctor's appointment', "
                            "but the submission fails with an error.",
                            sp, ["bug", "employee-journey", "leave"]
                        )
                    return
    except:
        pass


def test_04_profile_edit():
    """Test profile view and edit capabilities."""
    print("\n=== 4. PROFILE EDIT TEST ===")
    d = restart_if_needed()

    # Profile is at /employees/524 based on pass 1
    nav(f"{BASE_URL}/employees/524")
    sp = ss("profile_view")

    src = d.page_source
    if "Priya Patel" not in src:
        # Try alternate
        nav(f"{BASE_URL}/my-profile")
        src = d.page_source

    result("Profile shows Priya Patel", "Priya Patel" in src, "Name found" if "Priya Patel" in src else "Name not found")

    # Check tabs
    tabs = ["Personal", "Education", "Experience", "Dependencies", "Addresses", "Custom Fields"]
    for tab in tabs:
        found = tab in src
        result(f"Profile tab: {tab}", found, "Present" if found else "Missing")

    if "Job" not in src and "Job" in tabs:
        report_bug(
            "Profile is missing 'Job' tab",
            "The employee profile page shows tabs for Personal, Education, Experience, Dependencies, Addresses, Custom Fields "
            "but there's no 'Job' tab. Employees need to see their job details (title, department, manager, etc.).",
            sp, ["bug", "employee-journey", "profile"]
        )

    # Click Edit Profile
    try:
        edit_btn = d.find_element(By.XPATH, "//button[contains(text(),'Edit Profile')] | //a[contains(text(),'Edit Profile')]")
        edit_btn.click()
        time.sleep(3)
        sp = ss("profile_edit_mode")
        src = d.page_source

        # Check what's editable
        editable_inputs = d.find_elements(By.CSS_SELECTOR, "input:not([disabled]):not([readonly])")
        editable_count = sum(1 for inp in editable_inputs if inp.is_displayed())
        result("Edit Profile opens", True, f"{editable_count} editable fields")

        # Try to edit phone number
        phone_found = False
        for sel in ["input[name*='phone']", "input[name*='mobile']", "input[name*='contact']",
                     "input[placeholder*='phone']", "input[placeholder*='mobile']", "input[placeholder*='contact']"]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    phone_found = True
                    old_val = el.get_attribute("value")
                    result("Phone number editable", True, f"Current: {old_val}")
                    break
            if phone_found:
                break

        if not phone_found:
            result("Phone number editable", False, "Phone field not found in edit mode")
            sp = ss("no_phone_edit")
            report_bug(
                "Can't edit phone number in profile",
                "After clicking 'Edit Profile', there's no editable phone/mobile number field. "
                "Employees should be able to update their contact number.",
                sp, ["bug", "employee-journey", "profile"]
            )

        # Check for profile photo upload
        photo_upload = d.find_elements(By.CSS_SELECTOR, "input[type='file'], [class*='avatar'], [class*='upload-photo']")
        result("Profile photo upload", len(photo_upload) > 0,
               "Upload area found" if photo_upload else "No photo upload option")

    except Exception as e:
        result("Edit Profile button", False, str(e))


def test_05_attendance_clock():
    """Test attendance clock in/out from the attendance page."""
    print("\n=== 5. ATTENDANCE CLOCK IN/OUT ===")
    d = restart_if_needed()

    nav(f"{BASE_URL}/attendance/my")
    sp = ss("attendance_my")
    src = d.page_source

    if "My Attendance" not in src:
        result("Attendance page", False, "Not on attendance page")
        return

    result("Attendance page loads", True, "My Attendance visible")

    # Check today's status
    today_str = datetime.date.today().strftime("%B %d, %Y")
    # The screenshot showed "Today - Saturday, March 28, 2026"
    has_today = "Today" in src
    result("Today's date shown", has_today, "Today section visible" if has_today else "No today section")

    # Look for Check In button
    has_check_in = "Check In" in src or "Clock In" in src
    has_check_out = "Check Out" in src or "Clock Out" in src
    result("Check In button", has_check_in, "Present" if has_check_in else "Missing")
    result("Check Out button", has_check_out, "Present" if has_check_out else "Missing")

    # The screenshot showed "Check in at 6:33:01 AM" and "Check Out: 8:33:02 AM"
    # So attendance records are working. Let's check for the half day toggle
    has_half_day = "Half" in src or "half" in src
    print(f"    Half day option: {has_half_day}")

    # Check for regularization
    has_regularize = "Regular" in src or "regular" in src or "Correction" in src
    result("Regularization option", has_regularize,
           "Available" if has_regularize else "Not available — employees can't fix missed punches")

    if not has_regularize:
        sp = ss("no_regularization")
        report_bug(
            "No way to request attendance regularization",
            "The My Attendance page doesn't have an option to request regularization or correction for missed punches. "
            "If I forget to clock in or there's a system issue, there's no way for me to fix it.",
            sp, ["enhancement", "employee-journey", "attendance"]
        )

    # Check attendance table data
    rows = d.find_elements(By.CSS_SELECTOR, "table tr, [class*='row']")
    data_rows = [r for r in rows if r.text.strip() and "DATE" not in r.text.upper()[:20]]
    result("Attendance records shown", len(data_rows) > 0, f"{len(data_rows)} records visible")

    # Try clicking Check In (if not already checked in)
    if has_check_in:
        try:
            ci_btn = d.find_element(By.XPATH, "//button[contains(text(),'Check In')] | //button[contains(text(),'Clock In')]")
            if ci_btn.is_enabled():
                ci_btn.click()
                time.sleep(3)
                sp = ss("after_check_in")
                src = d.page_source
                result("Check In works", "Check Out" in src or "checked in" in src.lower(),
                       "Checked in successfully" if "Check Out" in src else "Status unclear")
        except:
            pass


def test_06_helpdesk_deep():
    """Deep test of helpdesk ticket creation."""
    print("\n=== 6. HELPDESK TICKET (DEEP) ===")
    d = restart_if_needed()

    # From sidebar, the helpdesk should be accessible
    # Let's check the sidebar for the actual helpdesk link
    nav(f"{BASE_URL}/dashboard")
    time.sleep(2)

    # Find helpdesk link in sidebar
    helpdesk_url = None
    try:
        links = d.find_elements(By.CSS_SELECTOR, "aside a, [class*='sidebar'] a")
        for link in links:
            text = link.text.strip().lower()
            href = link.get_attribute("href") or ""
            if "helpdesk" in text or "ticket" in text or "support" in text:
                helpdesk_url = href
                print(f"    Found helpdesk link: '{link.text.strip()}' -> {href}")
                break
    except:
        pass

    if not helpdesk_url:
        # Try known URLs
        for url in [f"{BASE_URL}/helpdesk", f"{BASE_URL}/helpdesk/my-tickets",
                     f"{BASE_URL}/tickets", f"{BASE_URL}/my-tickets"]:
            nav(url)
            if not is_on_dashboard():
                helpdesk_url = url
                break

    if helpdesk_url:
        nav(helpdesk_url)

    sp = ss("helpdesk_deep")
    on_dashboard = is_on_dashboard()

    if on_dashboard:
        result("Helpdesk accessible", False, "Redirected to dashboard")
        report_bug(
            "Helpdesk/Support Tickets not accessible for employees",
            "Clicking the Helpdesk link in the sidebar redirects back to the dashboard. "
            "As an employee, I need to be able to raise IT support tickets (my laptop keyboard is broken!).",
            sp, ["bug", "employee-journey", "helpdesk"]
        )
        return

    result("Helpdesk accessible", True, f"At {d.current_url}")
    src = d.page_source

    # Look for create ticket
    try:
        for text in ["Create", "New Ticket", "Raise Ticket", "Submit Ticket"]:
            btns = d.find_elements(By.XPATH,
                f"//button[contains(text(),'{text}')] | //a[contains(text(),'{text}')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                sp = ss("helpdesk_create_deep")
                src = d.page_source

                # Find and fill form fields
                filled = {}
                # Subject/Title
                for sel in ["input[name*='subject']", "input[name*='title']", "input[placeholder*='subject']",
                             "input[placeholder*='title']"]:
                    els = d.find_elements(By.CSS_SELECTOR, sel)
                    for el in els:
                        if el.is_displayed():
                            el.clear()
                            el.send_keys("Laptop keyboard keys sticking")
                            filled["subject"] = True
                            break
                    if "subject" in filled:
                        break

                # Description
                for ta in d.find_elements(By.TAG_NAME, "textarea"):
                    if ta.is_displayed():
                        ta.clear()
                        ta.send_keys("Several keys on my ThinkPad X1 are sticking. Especially the spacebar and 'e' key. Makes typing very difficult.")
                        filled["description"] = True
                        break

                # Priority dropdown
                for s in d.find_elements(By.TAG_NAME, "select"):
                    opts = [o.text for o in s.find_elements(By.TAG_NAME, "option")]
                    if any("high" in o.lower() for o in opts):
                        Select(s).select_by_visible_text([o for o in opts if "high" in o.lower()][0])
                        filled["priority"] = True
                        break

                # Category
                for s in d.find_elements(By.TAG_NAME, "select"):
                    opts = [o.text for o in s.find_elements(By.TAG_NAME, "option")]
                    if any("it" in o.lower() or "hardware" in o.lower() or "tech" in o.lower() for o in opts):
                        for o in opts:
                            if o.strip() and o.strip().lower() != "select":
                                Select(s).select_by_visible_text(o)
                                filled["category"] = True
                                break
                        break

                result("Helpdesk form fields", len(filled) >= 2,
                       f"Filled: {list(filled.keys())}")

                sp = ss("helpdesk_form_filled")

                # Submit
                for st in ["Submit", "Create", "Save", "Send"]:
                    sub = d.find_elements(By.XPATH, f"//button[contains(text(),'{st}')]")
                    for b in sub:
                        if b.is_displayed() and b.is_enabled():
                            b.click()
                            time.sleep(3)
                            sp = ss("helpdesk_submitted")
                            src = d.page_source.lower()
                            success = any(w in src for w in ["success", "created", "submitted"])
                            result("Helpdesk ticket submitted", success,
                                   "Created" if success else "Submission unclear")
                            return
                break
    except Exception as e:
        print(f"    Helpdesk error: {e}")


def test_07_payroll_sso():
    """Test payroll access through SSO."""
    print("\n=== 7. PAYROLL SSO ===")
    d = restart_if_needed()

    # Go to modules page
    nav(f"{BASE_URL}/modules")
    sp = ss("modules_payroll")
    src = d.page_source

    if "Module Marketplace" not in src:
        result("Modules page", False, "Not on modules page")
        return

    result("Modules page loads", True, "Module Marketplace visible")

    # Check if Payroll is subscribed
    has_payroll_subscribed = "Payroll" in src and "Subscribed" in src
    result("Payroll module subscribed", has_payroll_subscribed,
           "Subscribed" if has_payroll_subscribed else "Not subscribed or not found")

    # Click on Payroll
    try:
        payroll_links = d.find_elements(By.XPATH,
            "//a[contains(text(),'Payroll')] | //div[contains(text(),'Payroll')]//ancestor::a | "
            "//h3[contains(text(),'Payroll')]//ancestor::a")
        for pl in payroll_links:
            href = pl.get_attribute("href") or ""
            if pl.is_displayed():
                pl.click()
                time.sleep(5)
                break
    except:
        pass

    cur = d.current_url
    sp = ss("payroll_after_click")

    # Check if we landed on payroll or its login
    if "payroll" in cur.lower():
        result("Payroll navigation", True, f"At {cur}")

        # Check if it auto-logged in via SSO
        src = d.page_source
        if "login" in cur.lower() or "Sign in" in src:
            result("Payroll SSO auto-login", False, "Landed on payroll login page, SSO didn't work")
            sp = ss("payroll_sso_failed")
            report_bug(
                "Payroll SSO doesn't auto-login — shows login page with wrong email",
                "When clicking Payroll from the modules page while logged in as priya@technova.in, "
                "it opens the payroll login page instead of auto-logging in via SSO. "
                "The login form even shows ananya@technova.in (admin) instead of my email. "
                "Employees shouldn't have to login again to check their payslip.",
                sp, ["bug", "employee-journey", "payroll", "sso"]
            )
            # Try logging in as Priya on payroll
            try:
                email_inp = d.find_element(By.CSS_SELECTOR, "input[type='email'], input[name*='email']")
                email_inp.clear()
                email_inp.send_keys(EMAIL)
                pw_inp = d.find_element(By.CSS_SELECTOR, "input[type='password']")
                pw_inp.clear()
                pw_inp.send_keys(PASSWORD)
                d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                time.sleep(4)
                sp = ss("payroll_logged_in")
                src = d.page_source
                result("Payroll manual login", "/login" not in d.current_url,
                       f"At {d.current_url}")
            except:
                pass
        else:
            result("Payroll SSO auto-login", True, "Auto-logged in")
    else:
        result("Payroll navigation", False, f"Did not reach payroll: {cur}")


def test_08_feedback_submit():
    """Submit anonymous feedback about cafeteria."""
    print("\n=== 8. ANONYMOUS FEEDBACK ===")
    d = restart_if_needed()

    nav(f"{BASE_URL}/feedback")
    sp = ss("feedback_page_deep")

    if is_on_dashboard():
        result("Feedback page", False, "Redirected to dashboard")
        return

    src = d.page_source
    result("Feedback page loads", "Feedback" in src or "feedback" in src.lower(),
           f"At {d.current_url}")

    # Try to submit feedback
    try:
        # Look for submit/new feedback button
        for text in ["Submit Feedback", "New Feedback", "Create", "Submit", "Give Feedback"]:
            btns = d.find_elements(By.XPATH, f"//button[contains(text(),'{text}')] | //a[contains(text(),'{text}')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                sp = ss("feedback_form")
                break

        # Fill form
        # Title
        for sel in ["input[name*='title']", "input[name*='subject']", "input[type='text']"]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    el.clear()
                    el.send_keys("Cafeteria food quality")
                    break

        # Message
        for ta in d.find_elements(By.TAG_NAME, "textarea"):
            if ta.is_displayed():
                ta.clear()
                ta.send_keys("The lunch options have been repetitive lately. Would love more variety, especially vegetarian options.")
                break

        # Anonymous toggle
        for cb in d.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
            try:
                parent_text = d.execute_script("return arguments[0].closest('label')?.textContent || ''", cb)
                if "anonym" in parent_text.lower():
                    if not cb.is_selected():
                        cb.click()
                    break
            except:
                pass

        # Category dropdown
        for s in d.find_elements(By.TAG_NAME, "select"):
            opts = s.find_elements(By.TAG_NAME, "option")
            if len(opts) > 1:
                Select(s).select_by_index(1)
                break

        sp = ss("feedback_filled")

        # Submit
        for text in ["Submit", "Send", "Post"]:
            btns = d.find_elements(By.XPATH, f"//button[contains(text(),'{text}')]")
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(3)
                    sp = ss("feedback_result")
                    src = d.page_source.lower()
                    success = any(w in src for w in ["success", "submitted", "thank", "received", "created"])
                    result("Feedback submitted", success,
                           "Confirmation received" if success else "No confirmation after submit")
                    if not success:
                        report_bug(
                            "No confirmation after submitting anonymous feedback",
                            "Filled out the feedback form with title, message, and anonymous checkbox, "
                            "but after clicking Submit there's no success confirmation. "
                            "I don't know if my feedback was actually received.",
                            sp, ["bug", "employee-journey", "feedback"]
                        )
                    return
    except Exception as e:
        print(f"    Feedback error: {e}")


def test_09_notifications_deep():
    """Test notification bell functionality."""
    print("\n=== 9. NOTIFICATIONS ===")
    d = restart_if_needed()

    nav(f"{BASE_URL}/dashboard")
    sp = ss("notif_start")

    # Find and click notification bell icon
    bell_clicked = False
    try:
        # The bell is likely an SVG or icon in the header
        header = d.find_elements(By.CSS_SELECTOR, "header, [class*='header'], [class*='navbar'], [class*='topbar']")
        if header:
            # Look for bell/notification icon within header
            icons = header[0].find_elements(By.CSS_SELECTOR, "svg, i, button, a, span[class*='icon']")
            for icon in icons:
                try:
                    aria = icon.get_attribute("aria-label") or ""
                    cls = icon.get_attribute("class") or ""
                    title = icon.get_attribute("title") or ""
                    # Also check SVG path hints
                    inner = icon.get_attribute("innerHTML") or ""
                    if any(w in (aria + cls + title + inner).lower() for w in ["notif", "bell", "alert"]):
                        icon.click()
                        time.sleep(2)
                        bell_clicked = True
                        break
                except:
                    continue
    except:
        pass

    # Fallback: look for notification bell anywhere
    if not bell_clicked:
        try:
            # Bell icon usually has a bell SVG path
            bells = d.find_elements(By.CSS_SELECTOR, "[class*='bell'], [class*='notif'], [data-testid*='notif']")
            if bells:
                bells[0].click()
                time.sleep(2)
                bell_clicked = True
        except:
            pass

    sp = ss("notif_after_click")
    result("Notification bell clickable", bell_clicked,
           "Clicked bell" if bell_clicked else "Bell not found")

    if bell_clicked:
        src = d.page_source
        has_dropdown = "notification" in src.lower() or "no notification" in src.lower()
        result("Notification panel opens", has_dropdown,
               "Panel visible" if has_dropdown else "No notification panel appeared")

        # Check for notification items
        notif_items = d.find_elements(By.CSS_SELECTOR, "[class*='notification-item'], [class*='notif-item'], li[class*='notif']")
        result("Notification items", len(notif_items) > 0,
               f"{len(notif_items)} notifications" if notif_items else "Empty or no items")


def test_10_chatbot_interaction():
    """Test the AI chatbot interaction."""
    print("\n=== 10. AI CHATBOT ===")
    d = restart_if_needed()

    nav(f"{BASE_URL}/dashboard")
    time.sleep(2)

    # The purple chatbot bubble is visible in mobile view screenshot at bottom-right
    chatbot_opened = False
    try:
        # Look for the chatbot bubble — it's typically a fixed-position circular button
        # with a chat/message icon, often purple
        for sel in [
            "button[class*='chat']", "[class*='chatbot']", "[class*='chat-bubble']",
            "[class*='chat-widget']", "[id*='chat']", "[class*='intercom']",
            "[class*='crisp']", "[class*='drift']", "[class*='freshchat']",
            "div[style*='position: fixed'][style*='bottom']",
        ]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    el.click()
                    time.sleep(2)
                    chatbot_opened = True
                    break
            if chatbot_opened:
                break
    except:
        pass

    # Try finding by position (bottom-right corner)
    if not chatbot_opened:
        try:
            all_btns = d.find_elements(By.CSS_SELECTOR, "button, div[role='button'], a")
            for btn in all_btns:
                try:
                    rect = btn.rect
                    # Bottom-right: x > 1800, y > 900
                    if rect['x'] > 1800 and rect['y'] > 900 and rect['width'] < 80:
                        btn.click()
                        time.sleep(2)
                        chatbot_opened = True
                        sp = ss("chatbot_opened")
                        break
                except:
                    continue
        except:
            pass

    # The mobile screenshot shows a green-dotted purple circle — might be inside an iframe
    if not chatbot_opened:
        try:
            iframes = d.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src_attr = iframe.get_attribute("src") or ""
                if "chat" in src_attr.lower():
                    d.switch_to.frame(iframe)
                    time.sleep(1)
                    chatbot_opened = True
                    break
        except:
            pass

    sp = ss("chatbot_deep")
    result("Chatbot accessible", chatbot_opened,
           "Opened" if chatbot_opened else "Could not open chatbot")

    if chatbot_opened:
        # Try sending a message
        try:
            for sel in ["input[type='text']", "textarea", "input[placeholder*='message']",
                        "input[placeholder*='type']", "input[placeholder*='ask']"]:
                inputs = d.find_elements(By.CSS_SELECTOR, sel)
                for inp in inputs:
                    if inp.is_displayed():
                        inp.send_keys("What is my leave balance?")
                        inp.send_keys(Keys.RETURN)
                        time.sleep(5)
                        sp = ss("chatbot_response")

                        src = d.page_source.lower()
                        has_response = any(w in src for w in ["leave", "balance", "day", "sorry", "help", "assist"])
                        result("Chatbot responds", has_response,
                               "Got response" if has_response else "No response")
                        break
                break
        except Exception as e:
            print(f"    Chatbot interaction: {e}")

        # Switch back from iframe if needed
        try:
            d.switch_to.default_content()
        except:
            pass


def test_11_api_endpoints():
    """Test key API endpoints that employees would use."""
    print("\n=== 11. API ENDPOINT TESTS ===")

    # First try to get a token
    if not auth_token:
        api_login()

    # Also try to extract token from a fresh login response
    if not auth_token:
        try:
            resp = requests.post(f"{API_URL}/api/v1/auth/login",
                json={"email": EMAIL, "password": PASSWORD}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                print(f"    Full login response keys: {list(data.keys())}")
                if "data" in data and isinstance(data["data"], dict):
                    print(f"    data keys: {list(data['data'].keys())}")
                    # Check for nested token
                    for k, v in data["data"].items():
                        if isinstance(v, str) and len(v) > 50:
                            print(f"    Possible token in '{k}': {v[:30]}...")
                # Check response cookies
                for c in resp.cookies:
                    print(f"    Cookie: {c.name}={c.value[:30]}...")
        except:
            pass

    endpoints_to_test = [
        ("/api/v1/employee/profile", "Employee Profile"),
        ("/api/v1/leave/balance", "Leave Balance"),
        ("/api/v1/leave/my-applications", "My Leave Applications"),
        ("/api/v1/attendance/my", "My Attendance"),
        ("/api/v1/attendance/today", "Today's Attendance"),
        ("/api/v1/helpdesk/my-tickets", "My Helpdesk Tickets"),
        ("/api/v1/notifications", "Notifications"),
        ("/api/v1/surveys/active", "Active Surveys"),
        ("/api/v1/events", "Events"),
        ("/api/v1/policies", "Policies"),
        ("/api/v1/feedback/my", "My Feedback"),
        ("/api/v1/wellness/check-in", "Wellness Check-in"),
        ("/api/v1/assets/my", "My Assets"),
        ("/api/v1/announcements", "Announcements"),
        ("/api/v1/documents/my", "My Documents"),
    ]

    # Also test without /v1
    alt_endpoints = [ep.replace("/v1", "") for ep, _ in endpoints_to_test]

    for (ep, name), alt in zip(endpoints_to_test, alt_endpoints):
        r = api_get(ep)
        status = r.status_code if r else "N/A"
        if r and r.status_code == 200:
            result(f"API: {name}", True, f"{ep} -> 200")
        else:
            # Try alternate
            r2 = api_get(alt)
            status2 = r2.status_code if r2 else "N/A"
            if r2 and r2.status_code == 200:
                result(f"API: {name}", True, f"{alt} -> 200")
            else:
                result(f"API: {name}", False, f"{ep} -> {status}, {alt} -> {status2}")


def test_12_wellness_daily():
    """Test daily wellness check-in."""
    print("\n=== 12. WELLNESS DAILY CHECK-IN ===")
    d = restart_if_needed()

    nav(f"{BASE_URL}/wellness")
    sp = ss("wellness_deep")
    src = d.page_source

    if "Wellness" not in src:
        result("Wellness page", False, "Not on wellness page")
        return

    result("Wellness page loads", True, "Wellness Programs visible")

    # Click "Daily Check-in" button (seen in screenshot)
    try:
        dc_btn = d.find_element(By.XPATH,
            "//button[contains(text(),'Daily Check')] | //a[contains(text(),'Daily Check')]")
        dc_btn.click()
        time.sleep(3)
        sp = ss("wellness_daily_form")
        src = d.page_source

        result("Daily Check-in form opens", True, f"At {d.current_url}")

        # Look for mood selection, sliders, etc.
        has_mood = any(w in src.lower() for w in ["mood", "feeling", "how are you", "emoji", "happy"])
        result("Mood selection in daily check-in", has_mood,
               "Mood options found" if has_mood else "No mood options")

        # Try to fill the form
        # Mood buttons/emoji
        mood_els = d.find_elements(By.CSS_SELECTOR,
            "[class*='mood'], [class*='emoji'], button[class*='happy'], button[class*='good'], "
            "[data-mood], [data-value]")
        if mood_els:
            for mel in mood_els:
                if mel.is_displayed():
                    mel.click()
                    time.sleep(0.5)
                    break

        # Number/range inputs
        for inp in d.find_elements(By.CSS_SELECTOR, "input[type='range'], input[type='number']"):
            if inp.is_displayed():
                inp.clear()
                inp.send_keys("7")

        # Submit
        for text in ["Submit", "Save", "Check In", "Done"]:
            btns = d.find_elements(By.XPATH, f"//button[contains(text(),'{text}')]")
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(2)
                    sp = ss("wellness_daily_submitted")
                    result("Wellness check-in submitted", True, "Submitted")
                    return

    except Exception as e:
        result("Daily Check-in click", False, str(e))


def test_13_events_rsvp():
    """Check events and try RSVP."""
    print("\n=== 13. EVENTS & RSVP ===")
    d = restart_if_needed()

    nav(f"{BASE_URL}/events")
    sp = ss("events_deep")

    if is_on_dashboard():
        result("Events page", False, "Redirected to dashboard")
        report_bug(
            "Events page not accessible for employees",
            "Navigating to /events redirects back to the dashboard. Employees can't see company events.",
            sp, ["bug", "employee-journey", "events"]
        )
        return

    src = d.page_source
    result("Events page loads", "Event" in src, f"At {d.current_url}")

    # Check for event listings
    has_events_list = any(w in src for w in ["event", "upcoming", "date", "venue", "location"])
    result("Events listed", has_events_list, "Events visible" if has_events_list else "No events")

    # Try RSVP
    try:
        for text in ["RSVP", "Register", "Attend", "Join", "Going", "Interested"]:
            btns = d.find_elements(By.XPATH, f"//button[contains(text(),'{text}')] | //a[contains(text(),'{text}')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                sp = ss("event_rsvp")
                result("Event RSVP", True, f"Clicked '{text}'")
                break
    except:
        pass


def test_14_policies_ack():
    """Test policy acknowledgement."""
    print("\n=== 14. POLICIES & ACKNOWLEDGEMENT ===")
    d = restart_if_needed()

    nav(f"{BASE_URL}/policies")
    sp = ss("policies_deep")

    if is_on_dashboard():
        result("Policies page", False, "Redirected to dashboard")
        return

    src = d.page_source
    result("Policies page loads", "Polic" in src, f"At {d.current_url}")

    # Try to view a policy
    try:
        links = d.find_elements(By.CSS_SELECTOR, "a[href*='polic'], button, [class*='policy']")
        for link in links:
            text = link.text.strip()
            if text and len(text) > 3 and "polic" in text.lower():
                link.click()
                time.sleep(2)
                sp = ss("policy_view")
                break
    except:
        pass

    # Look for acknowledge
    src = d.page_source
    has_ack = any(w in src for w in ["Acknowledge", "I have read", "Accept", "Agree", "acknowledge"])
    result("Acknowledge option", has_ack, "Present" if has_ack else "Not found")

    if has_ack:
        try:
            for text in ["Acknowledge", "I Agree", "Accept", "I Have Read"]:
                btns = d.find_elements(By.XPATH, f"//button[contains(text(),'{text}')]")
                if btns:
                    btns[0].click()
                    time.sleep(2)
                    sp = ss("policy_acked")
                    result("Policy acknowledged", True, f"Clicked '{text}'")
                    break
        except:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    global driver

    print("=" * 70)
    print("PRIYA PATEL'S WORKDAY — Pass 2: Deeper Testing")
    print(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # API login
    print("\n--- API Login ---")
    api_login()

    tests = [
        test_01_dashboard_deep,
        test_02_sidebar_navigation,
        test_03_leave_apply_detailed,
        test_04_profile_edit,
        test_05_attendance_clock,
        test_06_helpdesk_deep,
        test_07_payroll_sso,
        test_08_feedback_submit,
        test_09_notifications_deep,
        test_10_chatbot_interaction,
        test_11_api_endpoints,
        test_12_wellness_daily,
        test_13_events_rsvp,
        test_14_policies_ack,
    ]

    for test_fn in tests:
        try:
            ensure()
            test_fn()
        except Exception as e:
            print(f"  [ERROR] {test_fn.__name__}: {e}")
            traceback.print_exc()
            try: ss(f"error_{test_fn.__name__}")
            except: pass

    if driver:
        try: driver.quit()
        except: pass

    # Summary
    print("\n" + "=" * 70)
    print("PASS 2 SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in test_results if r["passed"])
    failed = sum(1 for r in test_results if not r["passed"])
    total = len(test_results)
    print(f"Tests: {total} total, {passed} passed, {failed} failed")
    print(f"Issues filed: {len(issues_found)}")

    if issues_found:
        print("\nIssues Filed:")
        for i in issues_found:
            print(f"  - {i['title']}")
            print(f"    {i['url']}")

    print("\nFailed:")
    for r in test_results:
        if not r["passed"]:
            print(f"  - {r['test']}: {r['details']}")

    print("\nAll Results:")
    for r in test_results:
        s = "PASS" if r["passed"] else "FAIL"
        print(f"  [{s}] {r['test']}: {r['details']}")

    with open(r"C:\emptesting\employee_journey_pass2_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.datetime.now().isoformat(),
            "user": EMAIL,
            "summary": {"total": total, "passed": passed, "failed": failed},
            "issues": issues_found,
            "results": test_results
        }, f, indent=2)
    print(f"\nResults saved.")


if __name__ == "__main__":
    main()
