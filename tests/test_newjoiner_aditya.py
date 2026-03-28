"""
New Joiner Experience Test — Aditya Joshi's First Week at TechNova Solutions
Tests the HRMS from a brand new employee's perspective.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import base64
import urllib.request
import urllib.error
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_found = []
test_results = []
test_count = 0
driver = None
auth_token = None


# ── Helpers ──
def take_screenshot(drv, name):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"newjoiner_{name}_{ts}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    drv.save_screenshot(filepath)
    print(f"    [SCREENSHOT] {filepath}")
    return filepath


def upload_screenshot(filepath):
    try:
        filename = os.path.basename(filepath)
        path_in_repo = f"screenshots/{filename}"
        with open(filepath, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode("utf-8")
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path_in_repo}"
        payload = json.dumps({
            "message": f"Upload screenshot {filename}",
            "content": content_b64,
            "branch": "main"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="PUT")
        req.add_header("Authorization", f"token {GITHUB_TOKEN}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        dl_url = data.get("content", {}).get("download_url", "")
        print(f"    [UPLOADED] {dl_url}")
        return dl_url
    except Exception as e:
        print(f"    [UPLOAD FAILED] {e}")
        return None


def check_existing_issue(title_keywords):
    """Check if a similar issue already exists."""
    try:
        query = "+".join(title_keywords.split()[:5])
        url = f"https://api.github.com/search/issues?q={query}+repo:{GITHUB_REPO}+state:open"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"token {GITHUB_TOKEN}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        if data.get("total_count", 0) > 0:
            return data["items"][0]["html_url"]
    except:
        pass
    return None


def file_bug(drv, title, description, screenshot_path=None):
    """File a bug on GitHub with screenshot."""
    # Check for duplicate
    existing = check_existing_issue(title)
    if existing:
        print(f"    [SKIP] Similar issue exists: {existing}")
        bugs_found.append({"title": title, "issue_url": existing, "duplicate": True})
        return existing

    print(f"    [BUG] {title}")
    img_md = ""
    if screenshot_path:
        img_url = upload_screenshot(screenshot_path)
        if img_url:
            img_md = f"\n\n### Screenshot\n![screenshot]({img_url})"

    current_url = drv.current_url if drv else "N/A"
    body = (
        f"## Bug Report — New Joiner Experience Test\n\n"
        f"**Persona:** Aditya Joshi — brand new employee, first week at TechNova\n"
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**User:** {EMP_EMAIL} (Employee)\n"
        f"**URL:** {current_url}\n\n"
        f"### Description\n{description}"
        f"{img_md}\n\n"
        f"### Steps to Reproduce\n"
        f"1. Log in as a new employee ({EMP_EMAIL})\n"
        f"2. See description above\n\n"
        f"### Expected Behavior\nA new joiner should be able to easily find and use this feature.\n\n"
        f"### Impact\nNew employee onboarding experience is degraded.\n\n"
        f"### Environment\n- Browser: Chrome (headless)\n- Resolution: 1920x1080\n"
    )
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        payload = json.dumps({
            "title": title,
            "body": body,
            "labels": ["bug", "e2e-test", "new-joiner-ux"]
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Authorization", f"token {GITHUB_TOKEN}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        issue_url = data.get("html_url", "")
        print(f"    [ISSUE CREATED] {issue_url}")
        bugs_found.append({"title": title, "issue_url": issue_url})
        return issue_url
    except Exception as e:
        print(f"    [ISSUE FAILED] {e}")
        bugs_found.append({"title": title, "issue_url": None})
        return None


def record_test(name, status, details=""):
    test_results.append({"test": name, "status": status, "details": details})
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "SKIP"
    print(f"  [{icon}] {name}: {details}")


def api_call(method, endpoint, data=None, token=None):
    """Make API call, return (status_code, response_data)."""
    url = f"{API_URL}/api/v1{endpoint}"
    payload = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=payload, method=method)
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req)
        body = json.loads(resp.read().decode("utf-8"))
        return resp.status, body
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except:
            body = {"error": str(e)}
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}


def create_driver():
    """Create a fresh Chrome driver."""
    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    service = Service(ChromeDriverManager().install())
    drv = webdriver.Chrome(service=service, options=opts)
    drv.set_page_load_timeout(30)
    drv.implicitly_wait(5)
    return drv


def login_ui(drv):
    """Login via UI."""
    print("  Logging in via UI...")
    drv.get(f"{BASE_URL}/login")
    time.sleep(3)

    try:
        # Wait for page ready
        WebDriverWait(drv, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)

        # Find email field with multiple selectors
        email_field = None
        for sel in [
            "input[type='email']", "input[name='email']", "input[formcontrolname='email']",
            "input[placeholder*='mail']", "input[placeholder*='Mail']",
            "input[type='text']", "#email", "#username"
        ]:
            try:
                elems = drv.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    email_field = elems[0]
                    break
            except:
                pass

        # Find password field
        pass_field = None
        for sel in [
            "input[type='password']", "input[name='password']",
            "input[formcontrolname='password']", "#password"
        ]:
            try:
                elems = drv.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    pass_field = elems[0]
                    break
            except:
                pass

        if not email_field or not pass_field:
            # Fallback: try all inputs
            inputs = drv.find_elements(By.TAG_NAME, "input")
            print(f"    Found {len(inputs)} input elements:")
            for i, inp in enumerate(inputs):
                print(f"      [{i}] type={inp.get_attribute('type')} name={inp.get_attribute('name')} placeholder={inp.get_attribute('placeholder')}")
            if len(inputs) >= 2:
                email_field = inputs[0]
                pass_field = inputs[1]
            else:
                print("    Cannot find login fields!")
                take_screenshot(drv, "login_failed")
                return False

        email_field.clear()
        email_field.send_keys(EMP_EMAIL)
        time.sleep(0.5)
        pass_field.clear()
        pass_field.send_keys(EMP_PASS)
        time.sleep(0.5)

        # Click login button
        login_btn = None
        for sel in [
            "button[type='submit']", "button.login-btn", "button.btn-primary",
            "button[color='primary']", "button.mat-raised-button"
        ]:
            try:
                elems = drv.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    login_btn = elems[0]
                    break
            except:
                pass

        if not login_btn:
            buttons = drv.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                txt = btn.text.lower()
                if "login" in txt or "sign in" in txt or "log in" in txt:
                    login_btn = btn
                    break

        if login_btn:
            try:
                login_btn.click()
            except:
                drv.execute_script("arguments[0].click();", login_btn)
        else:
            pass_field.send_keys(Keys.RETURN)

        print("    Waiting for login to complete...")
        time.sleep(5)
        WebDriverWait(drv, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)

        current_url = drv.current_url
        print(f"    Current URL after login: {current_url}")

        if "/login" in current_url.lower():
            print("    Still on login page — login may have failed")
            take_screenshot(drv, "login_still_on_login")
            return False

        print(f"  Logged in. URL: {drv.current_url}")
        return True
    except Exception as e:
        print(f"  Login failed: {e}")
        traceback.print_exc()
        try:
            take_screenshot(drv, "login_error")
        except:
            pass
        return False


def wait_ready(drv, t=3):
    try:
        WebDriverWait(drv, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
    except:
        pass
    time.sleep(t)


def nav(drv, path, label="page"):
    url = f"{BASE_URL}{path}"
    print(f"    Navigating to {url}")
    drv.get(url)
    wait_ready(drv)
    return drv


def get_page_text(drv):
    try:
        return drv.find_element(By.TAG_NAME, "body").text.lower()
    except:
        return drv.page_source.lower()


def find_elements_safe(drv, css):
    try:
        return drv.find_elements(By.CSS_SELECTOR, css)
    except:
        return []


# ═══════════════════════════════════════════════════════════════
# API EXPLORATION — "I'm a new joiner, let me see what's here"
# ═══════════════════════════════════════════════════════════════
def test_api_exploration():
    global auth_token
    print("\n" + "=" * 70)
    print("PHASE 0: API Login & Exploration")
    print("=" * 70)

    # Login via API
    status, data = api_call("POST", "/auth/login", {"email": EMP_EMAIL, "password": EMP_PASS})
    tokens = data.get("data", {}).get("tokens", {})
    if status == 200 and (tokens.get("access_token") or data.get("data", {}).get("token")):
        auth_token = tokens.get("access_token") or data["data"]["token"]
        user_info = data.get("data", {}).get("user", {})
        print(f"  API login OK. User: {user_info.get('first_name', '?')} {user_info.get('last_name', '?')}")
        print(f"  Role: {user_info.get('role', '?')}, Dept: {user_info.get('department', {}).get('name', '?') if isinstance(user_info.get('department'), dict) else '?'}")
        record_test("API Login", "pass", f"Logged in as {user_info.get('email', '?')}")
    else:
        print(f"  API login failed: {status} - {data}")
        record_test("API Login", "fail", f"Status {status}")
        return

    # Check profile completeness
    print("\n  --- Checking my profile via API ---")
    status, data = api_call("GET", "/auth/me", token=auth_token)
    if status == 200:
        user = data.get("data", {})
        missing = []
        fields_to_check = {
            "contact_number": "Phone number",
            "emergency_contact_name": "Emergency contact name",
            "emergency_contact_number": "Emergency contact number",
            "address": "Address",
            "date_of_birth": "Date of birth",
            "blood_group": "Blood group",
            "personal_email": "Personal email",
            "designation": "Designation",
            "reporting_manager_id": "Manager assigned",
        }
        for field, label in fields_to_check.items():
            val = user.get(field)
            if not val or val == "" or val is None:
                missing.append(label)
        if missing:
            print(f"  Missing profile fields: {', '.join(missing)}")
            record_test("Profile Completeness (API)", "fail", f"Missing: {', '.join(missing)}")
        else:
            record_test("Profile Completeness (API)", "pass", "All key fields populated")
    else:
        record_test("Profile Completeness (API)", "fail", f"GET /auth/me returned {status}")

    # Check leave balance
    print("\n  --- Checking leave balance via API ---")
    status, data = api_call("GET", "/leave/balance", token=auth_token)
    if status == 200:
        balances = data.get("data", [])
        if isinstance(balances, list) and len(balances) > 0:
            for b in balances[:5]:
                lt = b.get("leave_type", {})
                name = lt.get("name", "?") if isinstance(lt, dict) else "?"
                bal = b.get("balance", "?")
                print(f"    {name}: {bal} days")
            record_test("Leave Balance (API)", "pass", f"{len(balances)} leave types found")
        else:
            record_test("Leave Balance (API)", "fail", "No leave balances returned")
    else:
        record_test("Leave Balance (API)", "fail", f"Status {status}")

    # Check documents
    print("\n  --- Checking my documents via API ---")
    status, data = api_call("GET", "/documents", token=auth_token)
    if status == 200:
        docs = data.get("data", [])
        if isinstance(docs, list) and len(docs) > 0:
            for d in docs[:5]:
                print(f"    Doc: {d.get('title', d.get('name', '?'))}")
            record_test("Documents (API)", "pass", f"{len(docs)} documents found")
        else:
            record_test("Documents (API)", "fail", "No documents found — new joiner has no offer letter/NDA")
    else:
        record_test("Documents (API)", "fail", f"Status {status}")

    # Check announcements
    print("\n  --- Checking announcements via API ---")
    status, data = api_call("GET", "/announcements", token=auth_token)
    if status == 200:
        anns = data.get("data", [])
        if isinstance(anns, list):
            print(f"    {len(anns)} announcements found")
            record_test("Announcements (API)", "pass" if len(anns) > 0 else "fail",
                        f"{len(anns)} announcements" if len(anns) > 0 else "No announcements for new joiner")
        else:
            record_test("Announcements (API)", "fail", "Unexpected format")
    else:
        record_test("Announcements (API)", "fail", f"Status {status}")

    # Check events
    print("\n  --- Checking events via API ---")
    status, data = api_call("GET", "/events", token=auth_token)
    if status == 200:
        events = data.get("data", [])
        if isinstance(events, list):
            print(f"    {len(events)} events found")
            record_test("Events (API)", "pass" if len(events) > 0 else "fail",
                        f"{len(events)} events" if len(events) > 0 else "No events visible")
    else:
        record_test("Events (API)", "fail", f"Status {status}")

    # Check helpdesk
    print("\n  --- Checking helpdesk tickets via API ---")
    status, data = api_call("GET", "/helpdesk/tickets", token=auth_token)
    if status == 200:
        record_test("Helpdesk (API)", "pass", "Endpoint accessible")
    else:
        record_test("Helpdesk (API)", "fail", f"Status {status}")

    # Check policies
    print("\n  --- Checking company policies via API ---")
    status, data = api_call("GET", "/policies", token=auth_token)
    if status == 200:
        policies = data.get("data", [])
        if isinstance(policies, list):
            print(f"    {len(policies)} policies found")
            for p in policies[:5]:
                print(f"      - {p.get('title', '?')} ({p.get('category', '?')})")
            record_test("Policies (API)", "pass" if len(policies) > 0 else "fail",
                        f"{len(policies)} policies" if len(policies) > 0 else "No policies found")
    else:
        record_test("Policies (API)", "fail", f"Status {status}")

    # Check forum
    print("\n  --- Checking community forum via API ---")
    status, data = api_call("GET", "/forum/posts", token=auth_token)
    if status == 200:
        record_test("Forum (API)", "pass", "Endpoint accessible")
    else:
        record_test("Forum (API)", "fail", f"Status {status}")

    # Check wellness
    print("\n  --- Checking wellness via API ---")
    status, data = api_call("GET", "/wellness", token=auth_token)
    if status == 200:
        record_test("Wellness (API)", "pass", "Endpoint accessible")
    else:
        record_test("Wellness (API)", "fail", f"Status {status}")

    # Check org chart / employees
    print("\n  --- Checking org chart / teammates via API ---")
    status, data = api_call("GET", "/users", token=auth_token)
    if status == 200:
        users = data.get("data", [])
        if isinstance(users, list):
            print(f"    Can see {len(users)} users")
            record_test("Org Chart / Users (API)", "pass", f"{len(users)} users visible")
        else:
            record_test("Org Chart / Users (API)", "fail", "Unexpected format")
    else:
        record_test("Org Chart / Users (API)", "fail", f"Status {status}")


# ═══════════════════════════════════════════════════════════════
# UI TESTS — Selenium
# ═══════════════════════════════════════════════════════════════

def restart_driver():
    global driver, test_count
    if driver:
        try:
            driver.quit()
        except:
            pass
    driver = create_driver()
    login_ui(driver)
    test_count = 0
    return driver


def maybe_restart():
    global test_count
    test_count += 1
    if test_count >= 3:
        print("\n  [RESTART] Restarting driver after 3 tests...")
        restart_driver()


# ─── Test 1: First Login — Onboarding Experience ───
def test_01_first_login_dashboard():
    """What does a new joiner see after first login? Any welcome/onboarding?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 01: First Login — Dashboard & Onboarding")
    print("-" * 60)

    ss = take_screenshot(driver, "01_dashboard_first_view")
    page_text = get_page_text(driver)
    current_url = driver.current_url

    # Look for onboarding indicators
    onboarding_keywords = ["onboarding", "welcome", "getting started", "first steps",
                           "setup", "complete your profile", "new joiner", "induction",
                           "welcome aboard", "get started"]
    found_onboarding = []
    for kw in onboarding_keywords:
        if kw in page_text:
            found_onboarding.append(kw)

    if found_onboarding:
        record_test("Onboarding Wizard/Welcome", "pass", f"Found: {', '.join(found_onboarding)}")
    else:
        record_test("Onboarding Wizard/Welcome", "fail",
                     "No onboarding wizard, welcome message, or getting-started guide on first login")
        file_bug(driver,
                 "New joiner has no onboarding guide after first login",
                 "After logging in as a new employee for the first time, there is no onboarding wizard, "
                 "welcome message, or 'getting started' guide. A new joiner sees the regular dashboard with "
                 "no guidance on what to do first (complete profile, read policies, apply for ID card, etc.). "
                 "This makes the first-day experience confusing.\n\n"
                 "**What's missing:**\n"
                 "- No welcome banner or greeting\n"
                 "- No onboarding checklist (complete profile, read handbook, etc.)\n"
                 "- No 'getting started' wizard\n"
                 "- No pointer to important first-day tasks",
                 ss)

    # Check for quick actions / widgets on dashboard
    widgets_found = []
    widget_selectors = [
        (".widget", "widget"), (".card", "card"), ("[class*='quick']", "quick-action"),
        ("[class*='shortcut']", "shortcut"), ("[class*='todo']", "todo"),
        ("[class*='task']", "task"), ("[class*='pending']", "pending"),
    ]
    for sel, name in widget_selectors:
        els = find_elements_safe(driver, sel)
        if els:
            widgets_found.append(f"{name}({len(els)})")

    if widgets_found:
        record_test("Dashboard Widgets", "pass", f"Found: {', '.join(widgets_found)}")
    else:
        record_test("Dashboard Widgets", "fail", "No recognizable widgets/cards on dashboard")

    maybe_restart()


# ─── Test 2: Profile Check ───
def test_02_profile_completeness():
    """Check profile page — is it complete? Can you update it?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 02: My Profile — Completeness & Edit Ability")
    print("-" * 60)

    # Try various profile paths
    profile_paths = ["/profile", "/my-profile", "/employees/me", "/settings/profile", "/account"]
    profile_loaded = False

    for path in profile_paths:
        nav(driver, path, "profile")
        page_text = get_page_text(driver)
        if "profile" in page_text or "personal" in page_text or "priya" in page_text.lower():
            profile_loaded = True
            break

    # Also try clicking on profile/avatar in nav
    if not profile_loaded:
        try:
            avatar = driver.find_elements(By.CSS_SELECTOR,
                "[class*='avatar'], [class*='profile'], .user-menu, .user-icon, img.rounded-circle")
            if avatar:
                avatar[0].click()
                time.sleep(2)
                # Look for profile link in dropdown
                profile_links = driver.find_elements(By.XPATH,
                    "//a[contains(text(),'Profile') or contains(text(),'My Profile')]")
                if profile_links:
                    profile_links[0].click()
                    time.sleep(3)
                    profile_loaded = True
        except:
            pass

    ss = take_screenshot(driver, "02_profile")
    page_text = get_page_text(driver)

    if not profile_loaded:
        record_test("Profile Page Access", "fail", "Could not find profile page")
        file_bug(driver,
                 "New joiner can't find their profile page",
                 "Tried /profile, /my-profile, /employees/me, /settings/profile, /account — none loaded a profile page. "
                 "Also tried clicking on avatar/user menu. A new joiner wouldn't know where to view or update their profile.",
                 ss)
    else:
        record_test("Profile Page Access", "pass", f"Profile loaded at {driver.current_url}")

        # Check for edit capability
        edit_btns = driver.find_elements(By.XPATH,
            "//button[contains(text(),'Edit') or contains(text(),'Update')] | //a[contains(text(),'Edit')]")
        edit_icons = find_elements_safe(driver, "[class*='edit'], .fa-edit, .fa-pencil, svg[class*='edit']")

        if edit_btns or edit_icons:
            record_test("Profile Edit Button", "pass", "Edit/Update button found")
        else:
            record_test("Profile Edit Button", "fail", "No edit button visible on profile")

        # Check for key profile sections
        key_sections = ["phone", "emergency", "address", "contact", "personal"]
        found_sections = [s for s in key_sections if s in page_text]
        if found_sections:
            record_test("Profile Sections", "pass", f"Found: {', '.join(found_sections)}")
        else:
            record_test("Profile Sections", "fail", "No personal info sections (phone, address, emergency) visible")

        # File bug if both edit and sections are missing
        if not (edit_btns or edit_icons) or not found_sections:
            file_bug(driver,
                     "New joiner can't edit profile — no edit button and missing personal info sections",
                     "On the profile page, there is no visible Edit/Update button and key personal "
                     "information sections (phone, emergency contact, address) are not displayed. "
                     "A new employee needs to:\n"
                     "- Update their phone number\n"
                     "- Add emergency contact details\n"
                     "- Verify/update their address\n\n"
                     "None of these actions appear possible from the profile page.",
                     ss)

    maybe_restart()


# ─── Test 3: Joining Documents ───
def test_03_joining_documents():
    """Where are offer letter, NDA, appointment letter?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 03: Joining Documents — Offer Letter, NDA, Appointment")
    print("-" * 60)

    doc_paths = ["/documents", "/my-documents", "/document", "/files"]
    doc_loaded = False

    for path in doc_paths:
        nav(driver, path, "documents")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["document", "file", "upload", "download"]):
            doc_loaded = True
            break

    # Also try sidebar navigation
    if not doc_loaded:
        try:
            sidebar_links = driver.find_elements(By.XPATH,
                "//a[contains(text(),'Document') or contains(@href,'document')]")
            if sidebar_links:
                sidebar_links[0].click()
                time.sleep(3)
                doc_loaded = True
        except:
            pass

    ss = take_screenshot(driver, "03_documents")
    page_text = get_page_text(driver)

    if not doc_loaded:
        record_test("Documents Page", "fail", "Could not find documents section")
        file_bug(driver,
                 "New joiner can't find Documents section for offer letter and NDA",
                 "Tried /documents, /my-documents, /document, /files — none loaded a documents page. "
                 "A new joiner expects to find their offer letter, appointment letter, and NDA in a Documents section, "
                 "but there's no obvious way to access it.",
                 ss)
    else:
        record_test("Documents Page", "pass", f"Documents at {driver.current_url}")

        # Check for joining documents
        joining_keywords = ["offer", "appointment", "nda", "non-disclosure", "joining", "welcome kit"]
        found_docs = [kw for kw in joining_keywords if kw in page_text]
        if found_docs:
            record_test("Joining Documents Present", "pass", f"Found: {', '.join(found_docs)}")
        else:
            record_test("Joining Documents Present", "fail",
                         "No joining documents (offer letter, NDA, appointment letter) found")
            file_bug(driver,
                     "No joining documents uploaded for new employee — offer letter, NDA missing",
                     "The Documents section exists but contains no joining documents. "
                     "A new employee expects to find:\n"
                     "- Offer letter\n- Appointment letter\n- NDA / Non-disclosure agreement\n"
                     "- Employee handbook\n\n"
                     "None of these are present. The new joiner has no way to access their employment documents.",
                     ss)

    maybe_restart()


# ─── Test 4: Company Policies ───
def test_04_company_policies():
    """Can I find leave policy, attendance policy, code of conduct?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 04: Company Policies — Leave, Attendance, Code of Conduct")
    print("-" * 60)

    policy_paths = ["/policies", "/policy", "/company-policies", "/handbook"]
    policy_loaded = False

    for path in policy_paths:
        nav(driver, path, "policies")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["policy", "policies", "handbook", "guideline"]):
            policy_loaded = True
            break

    ss = take_screenshot(driver, "04_policies")
    page_text = get_page_text(driver)

    if not policy_loaded:
        record_test("Policies Page", "fail", "Could not find policies section")
        file_bug(driver,
                 "New joiner can't find company policies — no leave or attendance policy visible",
                 "Tried /policies, /policy, /company-policies, /handbook — none loaded. "
                 "A new employee needs to know leave policy, attendance rules, and code of conduct "
                 "but there's no obvious way to find them.",
                 ss)
    else:
        record_test("Policies Page", "pass", f"Policies at {driver.current_url}")

        # Check for specific policy types
        policy_types = ["leave", "attendance", "code of conduct", "work from home", "wfh", "dress code"]
        found = [p for p in policy_types if p in page_text]
        if found:
            record_test("Key Policies Present", "pass", f"Found: {', '.join(found)}")
        else:
            record_test("Key Policies Present", "fail",
                         "No specific leave/attendance/conduct policies found")

    maybe_restart()


# ─── Test 5: Apply for Leave ───
def test_05_apply_leave():
    """Is it obvious how to apply for leave? How many days do I have?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 05: Apply for Leave — Can I find it? How many days?")
    print("-" * 60)

    leave_paths = ["/leave", "/leaves", "/leave/apply", "/my-leaves", "/leave-management"]
    leave_loaded = False

    for path in leave_paths:
        nav(driver, path, "leave")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["leave", "balance", "apply", "casual", "sick", "annual"]):
            leave_loaded = True
            break

    ss = take_screenshot(driver, "05_leave")
    page_text = get_page_text(driver)

    if not leave_loaded:
        record_test("Leave Page", "fail", "Could not find leave section")
        file_bug(driver,
                 "New joiner can't find how to apply for leave",
                 "Tried /leave, /leaves, /leave/apply, /my-leaves — none loaded a leave management page. "
                 "A new employee doesn't know how to check leave balance or apply for time off.",
                 ss)
    else:
        record_test("Leave Page", "pass", f"Leave at {driver.current_url}")

        # Check for leave balance display
        balance_keywords = ["balance", "available", "remaining", "entitled", "days"]
        found_bal = [k for k in balance_keywords if k in page_text]
        if found_bal:
            record_test("Leave Balance Visible", "pass", f"Balance info: {', '.join(found_bal)}")
        else:
            record_test("Leave Balance Visible", "fail", "No leave balance/entitlement shown")

        # Check for apply button
        apply_btns = driver.find_elements(By.XPATH,
            "//button[contains(text(),'Apply')] | //a[contains(text(),'Apply')]")
        if apply_btns:
            record_test("Apply Leave Button", "pass", "Apply button found")
        else:
            record_test("Apply Leave Button", "fail", "No 'Apply' button for leave")

    maybe_restart()


# ─── Test 6: Org Chart & Manager ───
def test_06_org_chart():
    """Who's my manager? Where's the org chart?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 06: Org Chart — Who's my manager? Teammates?")
    print("-" * 60)

    org_paths = ["/org-chart", "/organization", "/org", "/team", "/directory", "/employees"]
    org_loaded = False

    for path in org_paths:
        nav(driver, path, "org chart")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["org", "chart", "team", "manager", "employee", "directory", "department"]):
            org_loaded = True
            break

    ss = take_screenshot(driver, "06_org_chart")
    page_text = get_page_text(driver)

    if not org_loaded:
        record_test("Org Chart", "fail", "Could not find org chart or directory")
        file_bug(driver,
                 "New joiner can't find org chart — no way to see manager or teammates",
                 "Tried /org-chart, /organization, /team, /directory, /employees — none loaded an org chart. "
                 "A new employee doesn't know who their manager is or who their teammates are.",
                 ss)
    else:
        record_test("Org Chart / Directory", "pass", f"Loaded at {driver.current_url}")

        # Check if manager info visible
        if "manager" in page_text or "reporting" in page_text:
            record_test("Manager Info Visible", "pass", "Manager/reporting info found")
        else:
            record_test("Manager Info Visible", "fail", "No manager/reporting info on page")

    maybe_restart()


# ─── Test 7: Helpdesk / IT Ticket ───
def test_07_helpdesk():
    """How do I raise an IT ticket? Laptop, email, VPN?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 07: Helpdesk — Raise IT ticket for laptop/email/VPN")
    print("-" * 60)

    help_paths = ["/helpdesk", "/tickets", "/support", "/it-support", "/helpdesk/tickets"]
    help_loaded = False

    for path in help_paths:
        nav(driver, path, "helpdesk")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["helpdesk", "ticket", "support", "request", "issue"]):
            help_loaded = True
            break

    ss = take_screenshot(driver, "07_helpdesk")
    page_text = get_page_text(driver)

    if not help_loaded:
        record_test("Helpdesk Page", "fail", "Could not find helpdesk")
        file_bug(driver,
                 "New joiner can't find helpdesk to request laptop or email setup",
                 "Tried /helpdesk, /tickets, /support, /it-support — none loaded. "
                 "A new employee needs to request a laptop, email access, VPN, and ID card "
                 "but there's no visible helpdesk or IT ticketing system.",
                 ss)
    else:
        record_test("Helpdesk Page", "pass", f"Helpdesk at {driver.current_url}")

        # Can we create a new ticket?
        create_btns = driver.find_elements(By.XPATH,
            "//button[contains(text(),'New') or contains(text(),'Create') or contains(text(),'Raise')] | "
            "//a[contains(text(),'New') or contains(text(),'Create') or contains(text(),'Raise')]")
        if create_btns:
            record_test("Create Ticket Button", "pass", "New/Create ticket button found")
        else:
            record_test("Create Ticket Button", "fail", "No way to create a new ticket")

    maybe_restart()


# ─── Test 8: Training / Onboarding Tasks ───
def test_08_training():
    """Any training or onboarding tasks assigned?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 08: Training & Onboarding Tasks")
    print("-" * 60)

    training_paths = ["/training", "/lms", "/learning", "/onboarding", "/tasks"]
    training_loaded = False

    for path in training_paths:
        nav(driver, path, "training")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["training", "course", "learning", "module", "task", "onboarding"]):
            training_loaded = True
            break

    ss = take_screenshot(driver, "08_training")
    page_text = get_page_text(driver)

    if not training_loaded:
        record_test("Training/Onboarding Tasks", "fail", "No training or task section found")
        file_bug(driver,
                 "No onboarding tasks or training modules assigned to new joiner",
                 "Tried /training, /lms, /learning, /onboarding, /tasks — none loaded a training page. "
                 "A new employee typically needs to complete mandatory training (security awareness, "
                 "company values, compliance). No training tasks are assigned or visible.",
                 ss)
    else:
        record_test("Training/Onboarding Tasks", "pass", f"Training at {driver.current_url}")

    maybe_restart()


# ─── Test 9: Attendance / Clock In ───
def test_09_attendance():
    """How do I mark attendance? Clock-in button?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 09: Attendance — Clock In/Out")
    print("-" * 60)

    # First check dashboard for clock-in
    nav(driver, "/dashboard", "dashboard")
    ss_dash = take_screenshot(driver, "09_attendance_dash")
    page_text = get_page_text(driver)

    clock_keywords = ["clock in", "clock-in", "clockin", "punch in", "check in", "mark attendance",
                      "start work", "time in"]
    found_clock = [kw for kw in clock_keywords if kw in page_text]

    if found_clock:
        record_test("Clock In on Dashboard", "pass", f"Found: {', '.join(found_clock)}")
    else:
        record_test("Clock In on Dashboard", "fail", "No clock-in button on dashboard")

    # Try attendance page
    att_paths = ["/attendance", "/my-attendance", "/attendance/mark"]
    att_loaded = False

    for path in att_paths:
        nav(driver, path, "attendance")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["attendance", "clock", "punch", "check in", "present"]):
            att_loaded = True
            break

    ss = take_screenshot(driver, "09_attendance_page")

    if att_loaded:
        record_test("Attendance Page", "pass", f"Attendance at {driver.current_url}")
    else:
        record_test("Attendance Page", "fail", "Could not find attendance page")

    if not found_clock and not att_loaded:
        file_bug(driver,
                 "New joiner doesn't know how to mark attendance — no clock-in button visible",
                 "Checked dashboard and tried /attendance, /my-attendance, /attendance/mark — "
                 "no clock-in/punch-in button visible anywhere. A new employee on their first day "
                 "wouldn't know how to mark their attendance.",
                 ss)

    maybe_restart()


# ─── Test 10: Company Events ───
def test_10_events():
    """Team outings, meetings, events?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 10: Company Events — Team Outings, Meetings")
    print("-" * 60)

    event_paths = ["/events", "/calendar", "/company-events"]
    event_loaded = False

    for path in event_paths:
        nav(driver, path, "events")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["event", "calendar", "meeting", "outing", "upcoming"]):
            event_loaded = True
            break

    ss = take_screenshot(driver, "10_events")

    if event_loaded:
        record_test("Events Page", "pass", f"Events at {driver.current_url}")
    else:
        record_test("Events Page", "fail", "Could not find events or calendar")
        file_bug(driver,
                 "New joiner can't find company events or team calendar",
                 "Tried /events, /calendar, /company-events — none loaded an events page. "
                 "A new employee wants to see upcoming team outings, company events, or meetings.",
                 ss)

    maybe_restart()


# ─── Test 11: Buddy / Mentor ───
def test_11_buddy_mentor():
    """Is there a buddy system or mentor assigned?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 11: Buddy System / Mentor Assignment")
    print("-" * 60)

    # Check dashboard, profile, and various paths
    pages_to_check = ["/dashboard", "/profile", "/onboarding", "/buddy", "/mentor"]
    found_buddy = False

    for path in pages_to_check:
        nav(driver, path, "buddy/mentor")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["buddy", "mentor", "onboarding partner", "assigned mentor"]):
            found_buddy = True
            break

    ss = take_screenshot(driver, "11_buddy")

    if found_buddy:
        record_test("Buddy/Mentor System", "pass", "Buddy or mentor info found")
    else:
        record_test("Buddy/Mentor System", "fail", "No buddy or mentor system found")
        # This is a feature gap but worth noting
        file_bug(driver,
                 "No buddy or mentor assigned for new joiner — no onboarding support person",
                 "Checked dashboard, profile, and various paths — no buddy/mentor system exists. "
                 "New employees benefit greatly from having an assigned buddy or mentor who can "
                 "guide them through their first weeks. No such feature is visible in the HRMS.",
                 ss)

    maybe_restart()


# ─── Test 12: Community Forum ───
def test_12_forum():
    """Can I access the forum? Post questions?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 12: Community Forum — Post Questions")
    print("-" * 60)

    forum_paths = ["/forum", "/community", "/discussions", "/forum/posts"]
    forum_loaded = False

    for path in forum_paths:
        nav(driver, path, "forum")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["forum", "post", "discussion", "community", "question", "topic"]):
            forum_loaded = True
            break

    ss = take_screenshot(driver, "12_forum")

    if forum_loaded:
        record_test("Community Forum", "pass", f"Forum at {driver.current_url}")

        # Can we post?
        post_btns = driver.find_elements(By.XPATH,
            "//button[contains(text(),'Post') or contains(text(),'New') or contains(text(),'Ask')] | "
            "//a[contains(text(),'Post') or contains(text(),'New') or contains(text(),'Ask')]")
        if post_btns:
            record_test("Forum Post Button", "pass", "Can create new post")
        else:
            record_test("Forum Post Button", "fail", "No button to create new post/question")
    else:
        record_test("Community Forum", "fail", "Could not find community forum")
        file_bug(driver,
                 "New joiner can't find community forum to ask questions",
                 "Tried /forum, /community, /discussions, /forum/posts — none loaded. "
                 "A new employee who has questions about processes, tools, or culture has no forum to ask.",
                 ss)

    maybe_restart()


# ─── Test 13: Wellness Check-in ───
def test_13_wellness():
    """Wellness check-in — is it visible? Mandatory?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 13: Wellness Check-in")
    print("-" * 60)

    wellness_paths = ["/wellness", "/wellbeing", "/health", "/wellness/check-in"]
    wellness_loaded = False

    for path in wellness_paths:
        nav(driver, path, "wellness")
        page_text = get_page_text(driver)
        if any(kw in page_text for kw in ["wellness", "wellbeing", "health", "mood", "check-in", "how are you"]):
            wellness_loaded = True
            break

    ss = take_screenshot(driver, "13_wellness")

    if wellness_loaded:
        record_test("Wellness Check-in", "pass", f"Wellness at {driver.current_url}")
    else:
        record_test("Wellness Check-in", "fail", "Could not find wellness check-in")

    maybe_restart()


# ─── Test 14: Notifications ───
def test_14_notifications():
    """What notifications does a new joiner get?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 14: Notifications for New Joiner")
    print("-" * 60)

    nav(driver, "/dashboard", "dashboard")

    # Look for notification bell/icon
    notif_els = find_elements_safe(driver, "[class*='notif'], [class*='bell'], .fa-bell, svg[class*='bell'], [aria-label*='notif']")
    if notif_els:
        try:
            notif_els[0].click()
            time.sleep(2)
        except:
            driver.execute_script("arguments[0].click();", notif_els[0])
            time.sleep(2)

    ss = take_screenshot(driver, "14_notifications")
    page_text = get_page_text(driver)

    if notif_els:
        record_test("Notification Bell", "pass", "Notification icon found")

        # Check for welcome/onboarding notifications
        notif_keywords = ["welcome", "onboarding", "profile", "complete", "new"]
        found = [kw for kw in notif_keywords if kw in page_text]
        if found:
            record_test("Onboarding Notifications", "pass", f"Found: {', '.join(found)}")
        else:
            record_test("Onboarding Notifications", "fail", "No onboarding-related notifications for new joiner")
    else:
        record_test("Notification Bell", "fail", "No notification icon found")

    # Also try /notifications
    nav(driver, "/notifications", "notifications")
    ss2 = take_screenshot(driver, "14_notifications_page")
    page_text = get_page_text(driver)

    if "notification" in page_text or "alert" in page_text:
        record_test("Notifications Page", "pass", "Notifications page accessible")
    else:
        record_test("Notifications Page", "fail", "No dedicated notifications page")
        file_bug(driver,
                 "No dedicated notifications page — new joiner can't review past notifications",
                 "Navigating to /notifications does not load a notifications page. While there is a notification "
                 "bell icon on the dashboard, there is no full-page view where a new employee can see all their "
                 "notifications history (welcome messages, pending tasks, approvals, etc.). "
                 "The bell dropdown alone is insufficient for reviewing older notifications.",
                 ss2)

    maybe_restart()


# ─── Test 15: Mobile View ───
def test_15_mobile_view():
    """Is the mobile view usable at 375px width?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST 15: Mobile View (375px width)")
    print("-" * 60)

    # Resize to mobile
    driver.set_window_size(375, 812)
    time.sleep(2)

    nav(driver, "/dashboard", "dashboard mobile")
    time.sleep(3)
    ss1 = take_screenshot(driver, "15_mobile_dashboard")
    page_text = get_page_text(driver)

    # Check for horizontal overflow
    has_overflow = driver.execute_script("""
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    """)

    if has_overflow:
        record_test("Mobile - No Horizontal Overflow", "fail", "Page has horizontal scroll at 375px")
        file_bug(driver,
                 "Dashboard has horizontal overflow on mobile (375px) — content not responsive",
                 "At 375px viewport width (iPhone SE/standard mobile), the dashboard has horizontal scroll. "
                 "Content is not properly responsive for mobile users.",
                 ss1)
    else:
        record_test("Mobile - No Horizontal Overflow", "pass", "No horizontal scroll at 375px")

    # Check navigation accessibility
    hamburger = find_elements_safe(driver, "[class*='hamburger'], [class*='toggle'], .navbar-toggler, [class*='menu-btn'], button[aria-label*='menu']")
    if hamburger:
        record_test("Mobile - Hamburger Menu", "pass", "Mobile menu toggle found")
        try:
            hamburger[0].click()
            time.sleep(2)
            ss2 = take_screenshot(driver, "15_mobile_menu")
        except:
            pass
    else:
        record_test("Mobile - Hamburger Menu", "fail", "No hamburger/mobile menu toggle")
        file_bug(driver,
                 "No hamburger menu on mobile view — sidebar navigation inaccessible at 375px",
                 "At 375px viewport width (mobile), there is no hamburger/toggle button to open the sidebar navigation. "
                 "The sidebar either overlaps the content or disappears entirely, leaving a new employee with no way "
                 "to navigate to Leave, Attendance, Documents, or other sections on their phone.\n\n"
                 "**Tested at:** 375x812 (iPhone SE / standard mobile)",
                 ss1)

    # Check readability
    tiny_text = driver.execute_script("""
        var tiny = 0;
        document.querySelectorAll('p, span, a, td, li, label').forEach(function(el) {
            var size = parseFloat(window.getComputedStyle(el).fontSize);
            if (size < 12 && el.textContent.trim().length > 0) tiny++;
        });
        return tiny;
    """)

    if tiny_text > 10:
        record_test("Mobile - Text Readability", "fail", f"{tiny_text} elements with font-size < 12px")
    else:
        record_test("Mobile - Text Readability", "pass", f"Only {tiny_text} tiny text elements")

    # Test a key action on mobile - leave page
    nav(driver, "/leave", "leave mobile")
    time.sleep(2)
    ss3 = take_screenshot(driver, "15_mobile_leave")

    # Reset window size
    driver.set_window_size(1920, 1080)
    time.sleep(1)

    maybe_restart()


# ─── Test: Navigation Discoverability ───
def test_navigation_discoverability():
    """Can a new joiner find things in the navigation?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST: Navigation Discoverability")
    print("-" * 60)

    nav(driver, "/dashboard", "dashboard")
    time.sleep(2)

    # Get all sidebar/nav links
    nav_links = driver.find_elements(By.CSS_SELECTOR,
        "nav a, .sidebar a, [class*='sidebar'] a, [class*='nav'] a, .menu a, [class*='menu'] a")

    link_texts = []
    for link in nav_links:
        try:
            txt = link.text.strip()
            href = link.get_attribute("href") or ""
            if txt and len(txt) > 1:
                link_texts.append(f"{txt} -> {href}")
        except:
            pass

    print(f"    Found {len(link_texts)} navigation links:")
    for lt in link_texts[:30]:
        print(f"      - {lt}")

    ss = take_screenshot(driver, "nav_sidebar")

    # Key sections a new joiner needs
    needed = {
        "dashboard": False,
        "leave": False,
        "attendance": False,
        "profile": False,
        "documents": False,
        "helpdesk": False,
        "policies": False,
        "events": False,
    }

    all_text = " ".join(link_texts).lower()
    for key in needed:
        if key in all_text:
            needed[key] = True

    missing_nav = [k for k, v in needed.items() if not v]
    if missing_nav:
        record_test("Navigation Completeness", "fail", f"Missing from nav: {', '.join(missing_nav)}")
        file_bug(driver,
                 f"Key sections missing from navigation — new joiner can't find {', '.join(missing_nav)}",
                 f"A new employee looking at the sidebar/navigation cannot find links to: {', '.join(missing_nav)}. "
                 f"These are essential for day-to-day use. Navigation links found: {'; '.join(link_texts[:15])}",
                 ss)
    else:
        record_test("Navigation Completeness", "pass", "All key sections visible in nav")

    maybe_restart()


# ─── Test: AI Chatbot ───
def test_ai_chatbot():
    """Is the AI chatbot visible? Can new joiner ask questions?"""
    global driver
    print("\n" + "-" * 60)
    print("TEST: AI Chatbot — Can I ask questions?")
    print("-" * 60)

    nav(driver, "/dashboard", "dashboard")
    time.sleep(3)

    # Look for chatbot bubble
    chatbot = find_elements_safe(driver, "[class*='chatbot'], [class*='chat-bubble'], [class*='ai-assistant'], "
                                          "[class*='support-chat'], [id*='chatbot'], [class*='floating']")
    # Also look for a purple/floating button at bottom-right
    floating_btns = driver.execute_script("""
        var btns = [];
        document.querySelectorAll('button, div, a').forEach(function(el) {
            var rect = el.getBoundingClientRect();
            var style = window.getComputedStyle(el);
            if (rect.bottom > window.innerHeight - 100 && rect.right > window.innerWidth - 100
                && rect.width < 100 && rect.height < 100) {
                btns.push(el.className + ' | ' + el.textContent.substring(0, 30));
            }
        });
        return btns;
    """)

    ss = take_screenshot(driver, "ai_chatbot")

    if chatbot or floating_btns:
        record_test("AI Chatbot", "pass", f"Found chatbot/floating elements: {floating_btns[:3] if floating_btns else 'CSS match'}")
    else:
        record_test("AI Chatbot", "fail", "No AI chatbot or help bubble visible")

    maybe_restart()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    global driver

    print("=" * 70)
    print("  ADITYA JOSHI'S FIRST WEEK — New Joiner Experience Test")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("  Hi, I'm Aditya. Just joined TechNova last week.")
    print("  Let me figure out this HRMS system...\n")

    # Phase 0: API exploration
    try:
        test_api_exploration()
    except Exception as e:
        print(f"  [ERROR] API exploration: {e}")
        traceback.print_exc()

    # Phase 1: UI Tests with Selenium
    print("\n" + "=" * 70)
    print("PHASE 1: UI — First Login Experience")
    print("=" * 70)

    try:
        driver = create_driver()
        if not login_ui(driver):
            print("  FATAL: Cannot login. Aborting UI tests.")
            return

        tests = [
            test_01_first_login_dashboard,
            test_02_profile_completeness,
            test_03_joining_documents,
            test_04_company_policies,
            test_05_apply_leave,
            test_06_org_chart,
            test_07_helpdesk,
            test_08_training,
            test_09_attendance,
            test_10_events,
            test_11_buddy_mentor,
            test_12_forum,
            test_13_wellness,
            test_14_notifications,
            test_15_mobile_view,
            test_navigation_discoverability,
            test_ai_chatbot,
        ]

        for test_fn in tests:
            try:
                test_fn()
            except Exception as e:
                test_name = test_fn.__name__
                print(f"  [ERROR] {test_name}: {e}")
                traceback.print_exc()
                record_test(test_name, "fail", f"Exception: {str(e)[:100]}")
                # Try to recover
                try:
                    take_screenshot(driver, f"error_{test_name}")
                except:
                    pass

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

    # ── Summary ──
    print("\n" + "=" * 70)
    print("  SUMMARY — Aditya's First Week Experience")
    print("=" * 70)

    passed = sum(1 for t in test_results if t["status"] == "pass")
    failed = sum(1 for t in test_results if t["status"] == "fail")
    skipped = sum(1 for t in test_results if t["status"] == "skip")

    print(f"\n  Total Tests: {len(test_results)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")

    if failed > 0:
        print(f"\n  FAILED TESTS:")
        for t in test_results:
            if t["status"] == "fail":
                print(f"    - {t['test']}: {t['details']}")

    print(f"\n  BUGS FILED: {len(bugs_found)}")
    for b in bugs_found:
        dup = " (DUPLICATE)" if b.get("duplicate") else ""
        print(f"    - {b['title']}{dup}")
        if b.get("issue_url"):
            print(f"      {b['issue_url']}")

    # Save results
    results_file = os.path.join(r"C:\emptesting", "newjoiner_results.json")
    with open(results_file, "w") as f:
        json.dump({
            "persona": "Aditya Joshi — New Joiner",
            "timestamp": datetime.now().isoformat(),
            "summary": {"total": len(test_results), "passed": passed, "failed": failed, "skipped": skipped},
            "tests": test_results,
            "bugs": bugs_found
        }, f, indent=2)
    print(f"\n  Results saved to {results_file}")


if __name__ == "__main__":
    main()
