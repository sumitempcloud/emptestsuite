"""
Fresh E2E Test -- New Joiner (Priya) and Manager (Ananya) Experience.
Tests onboarding, profile setup, policies, first leave, helpdesk (joiner)
and /manager page, team attendance, approvals, team calendar (manager).
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import traceback
import requests
import base64
from pathlib import Path
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
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com"

JOINER_EMAIL = "priya@technova.in"
JOINER_PASS = "Welcome@123"
MANAGER_EMAIL = "ananya@technova.in"
MANAGER_PASS = "Welcome@123"

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = Path(r"C:\Users\Admin\screenshots\fresh_joiner_manager")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

test_results = []
bugs_found = []
driver = None

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


def screenshot(name):
    ts = datetime.now().strftime("%H%M%S")
    fname = f"{ts}_{name}.png"
    fpath = SCREENSHOT_DIR / fname
    try:
        driver.save_screenshot(str(fpath))
        print(f"    [screenshot] {fpath}")
        return fpath
    except Exception as e:
        print(f"    [screenshot failed] {e}")
        return None


def upload_screenshot(filepath):
    if not filepath or not Path(filepath).exists():
        return None
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        fname = Path(filepath).name
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/fresh_joiner_manager/{fname}"
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
        return None
    except Exception as e:
        print(f"    [upload error] {e}")
        return None


def file_bug(title, description, screenshot_path=None, labels=None):
    """File a bug on GitHub with duplicate check."""
    if labels is None:
        labels = ["bug", "e2e-test", "fresh-test"]
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }
    # Check for duplicates
    try:
        search_resp = requests.get(
            "https://api.github.com/search/issues",
            headers=headers,
            params={"q": f'repo:{GITHUB_REPO} is:issue state:open "{title[:60]}"'},
            timeout=15
        )
        if search_resp.status_code == 200:
            items = search_resp.json().get("items", [])
            if items:
                print(f"    [issue exists] {items[0]['html_url']}")
                bugs_found.append({"title": title, "url": items[0]["html_url"], "existing": True})
                return items[0]["html_url"]
    except:
        pass

    img_md = ""
    if screenshot_path:
        img_url = upload_screenshot(screenshot_path)
        if img_url:
            img_md = f"\n\n## Screenshot\n![screenshot]({img_url})"

    try:
        current_url = driver.current_url if driver else "N/A"
    except:
        current_url = "N/A"
    body = (
        f"## Bug Report -- Fresh E2E Test\n\n"
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**URL:** {current_url}\n\n"
        f"### Description\n{description}"
        f"{img_md}\n\n"
        f"### Steps to Reproduce\n1. Login with appropriate credentials\n"
        f"2. See description above\n\n"
        f"### Expected Behavior\nFeature should work correctly for end users.\n\n"
        f"### Environment\n- Browser: Chrome (headless)\n- Resolution: 1920x1080\n"
    )
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers=headers, json={"title": title, "body": body, "labels": labels},
            timeout=30
        )
        if resp.status_code == 201:
            issue_url = resp.json()["html_url"]
            print(f"    [issue filed] {issue_url}")
            bugs_found.append({"title": title, "url": issue_url})
            return issue_url
        else:
            print(f"    [issue failed] HTTP {resp.status_code}")
    except Exception as e:
        print(f"    [issue error] {e}")
    return None


def record(test_name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {test_name}: {details}")
    test_results.append({"test": test_name, "passed": passed, "details": details})


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


def safe_nav(url, wait_secs=3):
    try:
        driver.get(url)
        time.sleep(wait_secs)
    except Exception as e:
        print(f"    [nav error] {url}: {e}")


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


# ── API Helpers ─────────────────────────────────────────────────────────────

def api_login(email, password):
    """Login via API and return (token, user_id)."""
    try:
        resp = requests.post(f"{API_URL}/api/v1/auth/login", json={
            "email": email, "password": password
        }, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            d = data.get("data", {}) or {}
            tokens = d.get("tokens", {}) or {}
            token = (tokens.get("access_token") or tokens.get("accessToken") or
                     d.get("token") or d.get("accessToken") or d.get("access_token") or
                     data.get("token") or data.get("accessToken"))
            user = d.get("user", {}) or {}
            user_id = user.get("id") or user.get("_id")
            if token:
                print(f"  [API] Login OK for {email}, token: {str(token)[:30]}..., user_id: {user_id}")
                return token, user_id
            else:
                print(f"  [API] Login OK but no token. Keys: {list(data.keys())}, data keys: {list(d.keys())}")
                return None, None
        else:
            print(f"  [API] Login failed for {email}: {resp.status_code}")
            return None, None
    except Exception as e:
        print(f"  [API] Login error: {e}")
        return None, None


def api_get(token, path, params=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = requests.get(f"{API_URL}{path}", headers=headers, params=params, timeout=15)
        return resp
    except Exception as e:
        print(f"  [API GET error] {path}: {e}")
        return None


def api_post(token, path, json_data=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = requests.post(f"{API_URL}{path}", headers=headers, json=json_data, timeout=15)
        return resp
    except Exception as e:
        print(f"  [API POST error] {path}: {e}")
        return None


def api_put(token, path, json_data=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = requests.put(f"{API_URL}{path}", headers=headers, json=json_data, timeout=15)
        return resp
    except Exception as e:
        print(f"  [API PUT error] {path}: {e}")
        return None


# ── UI Login ────────────────────────────────────────────────────────────────

def login_ui(email, password):
    """Login via the UI. Returns True on success."""
    try:
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)
        email_input = None
        for sel in ["input[name='email']", "input[type='email']", "#email",
                     "input[placeholder*='mail']", "input[placeholder*='Email']"]:
            try:
                email_input = driver.find_element(By.CSS_SELECTOR, sel)
                if email_input:
                    break
            except:
                continue
        if not email_input:
            for inp in driver.find_elements(By.TAG_NAME, "input"):
                t = inp.get_attribute("type") or ""
                if t in ("email", "text"):
                    email_input = inp
                    break
        if not email_input:
            print("  [login] Cannot find email input")
            return False

        email_input.clear()
        email_input.send_keys(email)
        time.sleep(0.5)

        pass_input = None
        for sel in ["input[name='password']", "input[type='password']", "#password"]:
            try:
                pass_input = driver.find_element(By.CSS_SELECTOR, sel)
                if pass_input:
                    break
            except:
                continue
        if not pass_input:
            print("  [login] Cannot find password input")
            return False

        pass_input.clear()
        pass_input.send_keys(password)
        time.sleep(0.5)

        submit = None
        for sel in ["button[type='submit']", "button.login-btn", "button.btn-primary",
                     "input[type='submit']"]:
            try:
                submit = driver.find_element(By.CSS_SELECTOR, sel)
                if submit:
                    break
            except:
                continue
        if not submit:
            for btn in driver.find_elements(By.TAG_NAME, "button"):
                txt = btn.text.lower()
                if "log in" in txt or "login" in txt or "sign in" in txt:
                    submit = btn
                    break
        if submit:
            try:
                submit.click()
            except:
                driver.execute_script("arguments[0].click();", submit)
        else:
            pass_input.send_keys(Keys.RETURN)

        time.sleep(4)
        current = driver.current_url
        if "/login" not in current or "/dashboard" in current:
            print(f"  [login] Success for {email} -> {current}")
            return True
        else:
            print(f"  [login] May have failed for {email}, still at {current}")
            return False
    except Exception as e:
        print(f"  [login] Error: {e}")
        return False


# =============================================================================
# PART 1: NEW JOINER EXPERIENCE (priya@technova.in)
# =============================================================================

def test_joiner_onboarding_welcome():
    """Day 1: Check for onboarding wizard / welcome message / getting started guide."""
    print("\n--- Joiner: Onboarding Welcome ---")
    safe_nav(f"{BASE_URL}/dashboard", 4)
    screenshot("joiner_dashboard")
    text = page_text()
    src = page_source()

    has_welcome = any(w in text for w in ["welcome", "getting started", "onboarding",
                                           "new joiner", "first steps", "setup guide"])
    has_wizard = any(w in src for w in ["onboarding", "wizard", "getting-started",
                                         "welcome-modal", "tour", "walkthrough"])
    record("Joiner: Welcome/Onboarding on Dashboard",
           has_welcome or has_wizard,
           f"Welcome text found: {has_welcome}, Wizard/tour: {has_wizard}")

    if not has_welcome and not has_wizard:
        sp = screenshot("joiner_no_welcome")
        file_bug(
            "No onboarding welcome or getting started guide for new joiners",
            "When a new employee logs in for the first time, there is no welcome message, "
            "onboarding wizard, getting started checklist, or guided tour. New joiners have "
            "no idea where to start.",
            sp, ["bug", "e2e-test", "fresh-test", "new-joiner-ux"]
        )


def url_changed_from_base(specific_keywords=None):
    """Check if the current URL indicates we actually landed on a specific page, not just base."""
    cur = driver.current_url.rstrip("/")
    base = BASE_URL.rstrip("/")
    if cur == base or cur == base + "#" or cur == base + "/#":
        return False
    if specific_keywords:
        return any(kw in cur for kw in specific_keywords)
    return True


def test_joiner_profile_check():
    """Day 1: Check profile completeness, missing fields."""
    print("\n--- Joiner: Profile Check ---")
    profile_found = False
    for url in ["/profile", "/my-profile", "/employee/profile", "/self-service/profile",
                "/settings/profile", "/emp/profile"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["profile", "personal", "employee details", "my info",
                                    "phone", "email", "address", "emergency"]):
            if url_changed_from_base(["profile", "self-service", "settings"]):
                profile_found = True
                screenshot("joiner_profile")
                break

    if not profile_found:
        # Try sidebar navigation
        safe_nav(f"{BASE_URL}/dashboard", 3)
        src = page_source()
        for keyword in ["profile", "my info", "my details", "self-service"]:
            links = driver.find_elements(By.PARTIAL_LINK_TEXT, keyword.title())
            links += driver.find_elements(By.PARTIAL_LINK_TEXT, keyword)
            for link in links:
                try:
                    link.click()
                    time.sleep(3)
                    if "profile" in page_text() or "personal" in page_text():
                        profile_found = True
                        screenshot("joiner_profile_nav")
                        break
                except:
                    continue
            if profile_found:
                break

    record("Joiner: Profile Page Accessible", profile_found,
           f"Found at: {driver.current_url}" if profile_found else "Could not find profile page")

    if not profile_found:
        sp = screenshot("joiner_no_profile")
        file_bug(
            "New joiner cannot easily find or access profile page",
            "Tried multiple URLs (/profile, /my-profile, /employee/profile, /self-service/profile) "
            "and sidebar navigation. Could not locate a clear profile page for self-service.",
            sp, ["bug", "e2e-test", "fresh-test", "new-joiner-ux"]
        )
    return profile_found


def test_joiner_profile_update(token, user_id):
    """Day 2: Can joiner update phone, emergency contact, address via API?"""
    print("\n--- Joiner: Profile Update (API) ---")
    # Try to get current profile using user id from login
    profile_resp = None
    paths_to_try = [f"/api/v1/employees/{user_id}"] if user_id else []
    paths_to_try += ["/api/v1/employee/profile", "/api/v1/employees/me", "/api/v1/profile",
                     "/api/v1/employee/me", "/api/v1/user/profile", "/api/v1/self-service/profile"]

    for path in paths_to_try:
        r = api_get(token, path)
        if r and r.status_code == 200:
            profile_resp = r
            print(f"  [API] Profile found at {path}")
            break

    if profile_resp:
        profile_data = profile_resp.json()
        data_obj = profile_data.get("data", profile_data)
        if isinstance(data_obj, dict):
            fields = list(data_obj.keys())
            print(f"  [API] Profile fields: {fields[:20]}")
            record("Joiner: API Profile Fetch", True, f"Fields: {len(fields)}")
        else:
            record("Joiner: API Profile Fetch", True, "Got profile but unexpected format")
    else:
        record("Joiner: API Profile Fetch", False, "Could not find profile API endpoint")


def test_joiner_find_policies():
    """Day 1: Where are company policies? Leave policy, attendance policy, code of conduct."""
    print("\n--- Joiner: Finding Policies ---")
    policies_found = False
    policy_urls = ["/policies", "/company-policies", "/documents", "/company/policies",
                   "/hr-policies", "/policy", "/document-center", "/knowledge-base",
                   "/resources", "/handbook"]

    for url in policy_urls:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["policy", "policies", "leave policy", "attendance policy",
                                    "code of conduct", "handbook", "document"]):
            if "404" not in text and "not found" not in text:
                policies_found = True
                screenshot("joiner_policies")
                break

    if not policies_found:
        # Try sidebar nav
        safe_nav(f"{BASE_URL}/dashboard", 3)
        for keyword in ["policies", "documents", "resources", "handbook"]:
            links = driver.find_elements(By.PARTIAL_LINK_TEXT, keyword.title())
            links += driver.find_elements(By.PARTIAL_LINK_TEXT, keyword)
            for link in links:
                try:
                    link.click()
                    time.sleep(3)
                    text = page_text()
                    if "policy" in text or "document" in text:
                        policies_found = True
                        screenshot("joiner_policies_nav")
                        break
                except:
                    continue
            if policies_found:
                break

    record("Joiner: Company Policies Accessible", policies_found,
           f"Found at: {driver.current_url}" if policies_found else "Could not find policies")

    if not policies_found:
        sp = screenshot("joiner_no_policies")
        file_bug(
            "New joiner cannot find company policies (leave, attendance, code of conduct)",
            "Searched for policies at multiple URLs and through sidebar navigation. "
            "No clear 'Policies' or 'Documents' section found for new employees.",
            sp, ["bug", "e2e-test", "fresh-test", "new-joiner-ux"]
        )


def test_joiner_find_policies_api(token):
    """Check policies via API."""
    print("\n--- Joiner: Policies API ---")
    for path in ["/api/v1/policies", "/api/v1/company-policies", "/api/v1/documents",
                 "/api/v1/hr-policies", "/api/v1/policy/list", "/api/v1/document/list"]:
        r = api_get(token, path)
        if r and r.status_code == 200:
            data = r.json()
            items = data.get("data", data)
            count = len(items) if isinstance(items, list) else "unknown"
            record("Joiner: Policies API", True, f"Found at {path}, count: {count}")
            return
    record("Joiner: Policies API", False, "No policies endpoint found")


def test_joiner_org_chart():
    """Day 1: Where's the org chart? Who's your manager? Teammates?"""
    print("\n--- Joiner: Org Chart / Team ---")
    org_found = False
    for url in ["/org-chart", "/organization", "/team", "/my-team", "/orgchart",
                "/org", "/people", "/directory", "/employees"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["org chart", "organization", "team", "reporting to",
                                    "manager", "hierarchy", "department", "directory"]):
            if "404" not in text and "not found" not in text:
                org_found = True
                screenshot("joiner_orgchart")
                break

    record("Joiner: Org Chart / Team Page", org_found,
           f"Found at: {driver.current_url}" if org_found else "Not found")

    if not org_found:
        sp = screenshot("joiner_no_orgchart")
        file_bug(
            "No org chart or team directory accessible for new joiners",
            "New employee cannot find an org chart, team directory, or see who their manager "
            "and teammates are. Tried /org-chart, /team, /directory, /people.",
            sp, ["bug", "e2e-test", "fresh-test", "new-joiner-ux"]
        )


def test_joiner_attendance():
    """Day 2: How to mark attendance? Clock-in button obvious?"""
    print("\n--- Joiner: Attendance / Clock In ---")
    safe_nav(f"{BASE_URL}/dashboard", 3)
    text = page_text()
    src = page_source()

    clock_in_found = any(w in text for w in ["clock in", "clock-in", "punch in", "check in",
                                              "mark attendance", "start day"])
    clock_in_btn = any(w in src for w in ["clock-in", "clockin", "punch-in", "check-in",
                                           "mark-attendance", "attendance-button"])

    screenshot("joiner_dashboard_attendance")
    record("Joiner: Clock-in Button on Dashboard", clock_in_found or clock_in_btn,
           f"Text: {clock_in_found}, Button: {clock_in_btn}")

    # Also check attendance page
    attendance_found = False
    for url in ["/attendance", "/my-attendance", "/employee/attendance",
                "/self-service/attendance", "/emp/attendance"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["attendance", "clock", "present", "absent", "working hours"]):
            if "404" not in text:
                attendance_found = True
                screenshot("joiner_attendance_page")
                break

    record("Joiner: Attendance Page Accessible", attendance_found,
           f"Found at: {driver.current_url}" if attendance_found else "Not found")


def test_joiner_helpdesk():
    """Day 2: How to raise IT ticket? Helpdesk accessible?"""
    print("\n--- Joiner: Helpdesk / Ticket ---")
    helpdesk_found = False
    for url in ["/helpdesk", "/help-desk", "/tickets", "/support", "/it-support",
                "/raise-ticket", "/help", "/service-desk"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["helpdesk", "help desk", "ticket", "support",
                                    "raise", "submit", "request"]):
            if "404" not in text and url_changed_from_base(["helpdesk", "help", "ticket", "support"]):
                helpdesk_found = True
                screenshot("joiner_helpdesk")
                break

    record("Joiner: Helpdesk Page Accessible", helpdesk_found,
           f"Found at: {driver.current_url}" if helpdesk_found else "Not found")

    if not helpdesk_found:
        sp = screenshot("joiner_no_helpdesk")
        file_bug(
            "New joiner cannot find helpdesk to raise IT/support tickets",
            "New employee needs to raise IT ticket (laptop setup, email access, VPN) but "
            "cannot find helpdesk or ticket-raising section. Tried /helpdesk, /tickets, /support.",
            sp, ["bug", "e2e-test", "fresh-test", "new-joiner-ux"]
        )


def test_joiner_helpdesk_api(token):
    """Check helpdesk API."""
    print("\n--- Joiner: Helpdesk API ---")
    for path in ["/api/v1/helpdesk", "/api/v1/helpdesk/tickets", "/api/v1/tickets",
                 "/api/v1/support/tickets", "/api/v1/helpdesk/my-tickets"]:
        r = api_get(token, path)
        if r and r.status_code == 200:
            record("Joiner: Helpdesk API", True, f"Found at {path}")
            return
    record("Joiner: Helpdesk API", False, "No helpdesk API endpoint found")


def test_joiner_apply_leave():
    """Day 3: How to apply for leave? How many days available?"""
    print("\n--- Joiner: Apply Leave ---")
    leave_found = False
    for url in ["/leave", "/leaves", "/my-leaves", "/leave/apply", "/employee/leave",
                "/self-service/leave", "/leave-management", "/emp/leave"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["leave", "apply", "balance", "casual", "sick",
                                    "annual", "earned", "available"]):
            if "404" not in text:
                leave_found = True
                screenshot("joiner_leave_page")
                break

    record("Joiner: Leave Page Accessible", leave_found,
           f"Found at: {driver.current_url}" if leave_found else "Not found")

    # Check for apply button
    if leave_found:
        text = page_text()
        src = page_source()
        apply_btn = any(w in text for w in ["apply", "request leave", "new leave"])
        apply_in_src = any(w in src for w in ["apply-leave", "new-leave", "request-leave",
                                               "apply_leave"])
        record("Joiner: Apply Leave Button Visible", apply_btn or apply_in_src,
               f"Text: {apply_btn}, Source: {apply_in_src}")


def test_joiner_leave_api(token):
    """Check leave balance and apply via API."""
    print("\n--- Joiner: Leave API ---")
    # Check leave balance
    balance_found = False
    for path in ["/api/v1/leave/balances", "/api/v1/leave/balance", "/api/v1/leaves/balance",
                 "/api/v1/employee/leave-balance", "/api/v1/leave/my-balance", "/api/v1/leave-balance"]:
        r = api_get(token, path)
        if r and r.status_code == 200:
            data = r.json()
            print(f"  [API] Leave balance response: {json.dumps(data)[:300]}")
            record("Joiner: Leave Balance API", True, f"Found at {path}")
            balance_found = True
            break

    if not balance_found:
        record("Joiner: Leave Balance API", False, "No leave balance endpoint found")

    # Check leave types
    for path in ["/api/v1/leave/types", "/api/v1/leave-types", "/api/v1/leaves/types"]:
        r = api_get(token, path)
        if r and r.status_code == 200:
            data = r.json()
            items = data.get("data", data)
            if isinstance(items, list):
                types = [i.get("name", i.get("type", "?")) for i in items[:10]]
                record("Joiner: Leave Types API", True, f"Types: {types}")
            else:
                record("Joiner: Leave Types API", True, f"Found at {path}")
            break


def test_joiner_notifications():
    """Day 3: What notifications does the joiner get?"""
    print("\n--- Joiner: Notifications ---")
    safe_nav(f"{BASE_URL}/dashboard", 3)

    # Look for notification bell/icon
    src = page_source()
    notif_icon = any(w in src for w in ["notification", "bell", "badge", "alert-icon",
                                         "notif-count"])
    record("Joiner: Notification Icon Present", notif_icon,
           "Notification icon/bell found in page source" if notif_icon else "No notification icon found")

    # Try notification page
    for url in ["/notifications", "/alerts", "/inbox"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["notification", "alert", "inbox", "message"]):
            if "404" not in text:
                screenshot("joiner_notifications")
                record("Joiner: Notifications Page", True, f"Found at {driver.current_url}")
                return
    record("Joiner: Notifications Page", False, "No notifications page found")


def test_joiner_community():
    """Day 2: How to access community forum?"""
    print("\n--- Joiner: Community Forum ---")
    for url in ["/community", "/forum", "/social", "/feed", "/wall", "/announcements"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["community", "forum", "post", "announcement",
                                    "social", "feed", "wall", "discussion"]):
            if "404" not in text and url_changed_from_base(["community", "forum", "social", "feed", "wall", "announcement"]):
                screenshot("joiner_community")
                record("Joiner: Community/Forum Accessible", True, f"Found at {driver.current_url}")
                return
    record("Joiner: Community/Forum Accessible", False, "Not found")


def test_joiner_documents():
    """Day 1: Where are joining documents? Offer letter, NDA, appointment letter?"""
    print("\n--- Joiner: Joining Documents ---")
    docs_found = False
    for url in ["/documents", "/my-documents", "/employee/documents", "/document-center",
                "/letters", "/offer-letter", "/self-service/documents"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["document", "letter", "offer", "appointment",
                                    "nda", "contract", "certificate"]):
            if "404" not in text:
                docs_found = True
                screenshot("joiner_documents")
                break

    record("Joiner: Joining Documents Page", docs_found,
           f"Found at: {driver.current_url}" if docs_found else "Not found")

    if not docs_found:
        sp = screenshot("joiner_no_documents")
        file_bug(
            "New joiner cannot find joining documents (offer letter, NDA, appointment letter)",
            "New employee looking for their joining documents (offer letter, NDA, appointment letter) "
            "cannot find a clear 'Documents' or 'My Documents' section.",
            sp, ["bug", "e2e-test", "fresh-test", "new-joiner-ux"]
        )


# =============================================================================
# PART 2: MANAGER EXPERIENCE (ananya@technova.in)
# =============================================================================

def test_manager_dashboard():
    """Manager dashboard - My Team section, quick links."""
    print("\n--- Manager: Dashboard / My Team ---")
    safe_nav(f"{BASE_URL}/dashboard", 4)
    screenshot("manager_dashboard")
    text = page_text()
    src = page_source()

    has_team = any(w in text for w in ["my team", "team", "direct reports", "reportees",
                                        "team members"])
    record("Manager: My Team Section on Dashboard", has_team,
           "Team section found" if has_team else "No team section visible on dashboard")


def test_manager_page():
    """Check /manager page."""
    print("\n--- Manager: /manager Page ---")
    safe_nav(f"{BASE_URL}/manager", 4)
    screenshot("manager_page")
    text = page_text()
    src = page_source()

    is_manager_page = any(w in text for w in ["manager", "team", "approval", "report",
                                               "attendance", "leave"])
    is_404 = "404" in text or "not found" in text

    if is_404:
        record("Manager: /manager Page Exists", False, "Got 404 / not found")
        file_bug(
            "/manager page returns 404 or redirects away",
            "Navigating to /manager returns a 404 or redirects. Managers need a dedicated "
            "management dashboard for team operations.",
            screenshot("manager_page_404"),
            ["bug", "e2e-test", "fresh-test", "manager-experience"]
        )
    else:
        record("Manager: /manager Page Exists", is_manager_page,
               f"Content found: {is_manager_page}")


def test_manager_team_attendance():
    """Team attendance today - who's present, absent, late."""
    print("\n--- Manager: Team Attendance ---")
    found = False
    for url in ["/manager/attendance", "/team-attendance", "/manager/team-attendance",
                "/attendance/team", "/my-team/attendance"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["attendance", "present", "absent", "late", "team"]):
            if "404" not in text and url_changed_from_base(["attendance", "manager", "team"]):
                found = True
                screenshot("manager_team_attendance")
                break

    record("Manager: Team Attendance Page", found,
           f"Found at: {driver.current_url}" if found else "Not found via URL")

    if not found:
        # Try dashboard section
        safe_nav(f"{BASE_URL}/dashboard", 3)
        text = page_text()
        has_attendance = any(w in text for w in ["team attendance", "present today",
                                                  "absent today", "on leave"])
        record("Manager: Team Attendance on Dashboard", has_attendance,
               "Attendance info on dashboard" if has_attendance else "No team attendance widget")


def test_manager_team_attendance_api(token):
    """Check team attendance via API."""
    print("\n--- Manager: Team Attendance API ---")
    today = datetime.now().strftime("%Y-%m-%d")
    for path in ["/api/v1/attendance/team", "/api/v1/manager/team-attendance",
                 "/api/v1/team/attendance", f"/api/v1/attendance/team?date={today}",
                 "/api/v1/manager/attendance"]:
        r = api_get(token, path)
        if r and r.status_code == 200:
            data = r.json()
            items = data.get("data", data)
            count = len(items) if isinstance(items, list) else "N/A"
            record("Manager: Team Attendance API", True, f"Found at {path}, records: {count}")
            return
    record("Manager: Team Attendance API", False, "No team attendance API endpoint found")


def test_manager_pending_approvals():
    """Pending leave approvals - count, details, approve/reject."""
    print("\n--- Manager: Pending Leave Approvals ---")
    found = False
    for url in ["/manager/approvals", "/approvals", "/leave/approvals",
                "/manager/leave-approvals", "/pending-approvals", "/leave/pending"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["approval", "pending", "approve", "reject",
                                    "leave request"]):
            if "404" not in text and url_changed_from_base(["approval", "pending", "leave"]):
                found = True
                screenshot("manager_approvals")
                break

    record("Manager: Leave Approvals Page", found,
           f"Found at: {driver.current_url}" if found else "Not found")


def test_manager_approvals_api(token):
    """Check pending approvals via API and try approve/reject."""
    print("\n--- Manager: Approvals API ---")
    pending = None
    pending_path = None
    for path in ["/api/v1/leave/pending-approvals", "/api/v1/manager/leave-approvals",
                 "/api/v1/leave/approvals", "/api/v1/manager/pending",
                 "/api/v1/leave/team-requests", "/api/v1/manager/approvals"]:
        r = api_get(token, path)
        if r and r.status_code == 200:
            data = r.json()
            items = data.get("data", data)
            if isinstance(items, list):
                pending = items
                pending_path = path
                print(f"  [API] Pending approvals at {path}: {len(items)} items")
                record("Manager: Pending Approvals API", True,
                       f"Found at {path}, pending: {len(items)}")
            else:
                record("Manager: Pending Approvals API", True, f"Found at {path}")
            break

    if pending is None:
        record("Manager: Pending Approvals API", False, "No pending approvals endpoint found")
        return

    # Try to approve or reject if there are any
    if pending and len(pending) > 0:
        first = pending[0]
        leave_id = first.get("id") or first.get("_id") or first.get("leaveId")
        if leave_id:
            print(f"  [API] Found pending leave: {leave_id}")
            # Try approve
            for approve_path in [f"/api/v1/leave/{leave_id}/approve",
                                  f"/api/v1/manager/leave/{leave_id}/approve",
                                  f"/api/v1/leave/approve/{leave_id}"]:
                r = api_post(token, approve_path, {"status": "approved", "reason": "E2E test approval"})
                if r and r.status_code in (200, 201):
                    record("Manager: Approve Leave API", True,
                           f"Approved {leave_id} at {approve_path}")
                    return
                r2 = api_put(token, approve_path, {"status": "approved", "reason": "E2E test approval"})
                if r2 and r2.status_code in (200, 201):
                    record("Manager: Approve Leave API", True,
                           f"Approved {leave_id} at {approve_path} (PUT)")
                    return

            record("Manager: Approve Leave API", False,
                   f"Could not find approve endpoint for leave {leave_id}")
        else:
            record("Manager: Approve Leave API", False,
                   "Pending leave found but no ID field")
    else:
        record("Manager: Approve Leave API", True, "No pending leaves to approve (0 items)")


def test_manager_team_leave_balances(token):
    """Team leave balances - who's running low."""
    print("\n--- Manager: Team Leave Balances ---")
    for path in ["/api/v1/manager/team-leave-balance", "/api/v1/leave/team-balance",
                 "/api/v1/team/leave-balance", "/api/v1/manager/leave-balances"]:
        r = api_get(token, path)
        if r and r.status_code == 200:
            data = r.json()
            record("Manager: Team Leave Balances API", True, f"Found at {path}")
            return
    record("Manager: Team Leave Balances API", False, "No team leave balance API found")


def test_manager_team_calendar():
    """Team calendar - who's on leave when."""
    print("\n--- Manager: Team Calendar ---")
    found = False
    for url in ["/manager/calendar", "/team-calendar", "/calendar", "/leave-calendar",
                "/manager/team-calendar", "/team/calendar"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        src = page_source()
        if any(w in text for w in ["calendar", "schedule"]) or "calendar" in src:
            if "404" not in text and url_changed_from_base(["calendar", "schedule"]):
                found = True
                screenshot("manager_team_calendar")
                break

    record("Manager: Team Calendar Page", found,
           f"Found at: {driver.current_url}" if found else "Not found")

    if not found:
        sp = screenshot("manager_no_calendar")
        file_bug(
            "No team calendar with leave overlay for managers",
            "Manager cannot find a team calendar showing who is on leave and when. "
            "Tried /calendar, /team-calendar, /manager/calendar. This is essential for "
            "planning and resource management.",
            sp, ["bug", "e2e-test", "fresh-test", "manager-experience"]
        )


def test_manager_team_members():
    """View team member profiles."""
    print("\n--- Manager: Team Members ---")
    found = False
    for url in ["/manager/team", "/my-team", "/team", "/manager/my-team",
                "/team-members", "/direct-reports"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["team", "member", "employee", "report"]):
            if "404" not in text and url_changed_from_base(["team", "manager", "member", "report"]):
                found = True
                screenshot("manager_team_members")
                break

    record("Manager: Team Members Page", found,
           f"Found at: {driver.current_url}" if found else "Not found")


def test_manager_team_members_api(token):
    """Check team members via API."""
    print("\n--- Manager: Team Members API ---")
    for path in ["/api/v1/manager/team", "/api/v1/team/members", "/api/v1/manager/direct-reports",
                 "/api/v1/my-team", "/api/v1/manager/team-members", "/api/v1/employees/team"]:
        r = api_get(token, path)
        if r and r.status_code == 200:
            data = r.json()
            items = data.get("data", data)
            count = len(items) if isinstance(items, list) else "N/A"
            record("Manager: Team Members API", True, f"Found at {path}, count: {count}")
            return
    record("Manager: Team Members API", False, "No team members API found")


def test_manager_team_helpdesk(token):
    """See team's helpdesk tickets."""
    print("\n--- Manager: Team Helpdesk ---")
    for path in ["/api/v1/manager/helpdesk", "/api/v1/helpdesk/team",
                 "/api/v1/manager/team-tickets", "/api/v1/helpdesk/team-tickets"]:
        r = api_get(token, path)
        if r and r.status_code == 200:
            record("Manager: Team Helpdesk API", True, f"Found at {path}")
            return
    record("Manager: Team Helpdesk API", False, "No team helpdesk API found")


def test_manager_rewards(token):
    """Recommend someone for reward/kudos."""
    print("\n--- Manager: Rewards / Kudos ---")
    for url in ["/rewards", "/kudos", "/recognition"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["reward", "kudos", "recognition", "nominate", "appreciate"]):
            if "404" not in text and url_changed_from_base(["reward", "kudos", "recognition"]):
                screenshot("manager_rewards")
                record("Manager: Rewards/Kudos Page", True, f"Found at {driver.current_url}")
                return
    record("Manager: Rewards/Kudos Page", False, "Not found via URL")


def test_manager_reports(token):
    """Generate team attendance/leave report."""
    print("\n--- Manager: Team Reports ---")
    for path in ["/api/v1/manager/reports", "/api/v1/reports/team",
                 "/api/v1/manager/attendance-report", "/api/v1/reports/attendance",
                 "/api/v1/manager/leave-report"]:
        r = api_get(token, path)
        if r and r.status_code == 200:
            record("Manager: Team Reports API", True, f"Found at {path}")
            return
    record("Manager: Team Reports API", False, "No team reports API found")

    # UI check
    for url in ["/reports", "/manager/reports", "/analytics", "/team-reports"]:
        safe_nav(f"{BASE_URL}{url}", 3)
        text = page_text()
        if any(w in text for w in ["report", "analytics", "download", "export"]):
            if "404" not in text and url_changed_from_base(["report", "analytics"]):
                screenshot("manager_reports")
                record("Manager: Reports Page", True, f"Found at {driver.current_url}")
                return
    record("Manager: Reports Page", False, "Not found")


# =============================================================================
# MAIN
# =============================================================================

def main():
    global driver

    print("=" * 70)
    print("FRESH E2E TEST -- New Joiner & Manager Experience")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ── PART 1: NEW JOINER ──
    print("\n" + "=" * 70)
    print("PART 1: NEW JOINER EXPERIENCE (priya@technova.in)")
    print("=" * 70)

    # API login first
    joiner_token, joiner_user_id = api_login(JOINER_EMAIL, JOINER_PASS)

    # Selenium
    driver = get_driver()
    try:
        logged_in = login_ui(JOINER_EMAIL, JOINER_PASS)
        if logged_in:
            screenshot("joiner_logged_in")
            test_joiner_onboarding_welcome()
            test_joiner_profile_check()
            test_joiner_find_policies()
            test_joiner_documents()
            test_joiner_org_chart()
            test_joiner_attendance()
            test_joiner_helpdesk()
            test_joiner_apply_leave()
            test_joiner_notifications()
            test_joiner_community()
        else:
            sp = screenshot("joiner_login_fail")
            record("Joiner: Login", False, "UI Login failed")
            file_bug("Employee login fails for priya@technova.in",
                     "Cannot login with priya@technova.in / Welcome@123. New joiner cannot access the system at all.",
                     sp)

        # API-only tests
        if joiner_token:
            test_joiner_profile_update(joiner_token, joiner_user_id)
            test_joiner_find_policies_api(joiner_token)
            test_joiner_helpdesk_api(joiner_token)
            test_joiner_leave_api(joiner_token)
        else:
            record("Joiner: API Login", False, "Could not get API token")

    except Exception as e:
        print(f"\n[ERROR] Joiner tests crashed: {e}")
        traceback.print_exc()
        screenshot("joiner_crash")
    finally:
        try:
            driver.quit()
        except:
            pass

    # ── PART 2: MANAGER ──
    print("\n" + "=" * 70)
    print("PART 2: MANAGER EXPERIENCE (ananya@technova.in)")
    print("=" * 70)

    manager_token, manager_user_id = api_login(MANAGER_EMAIL, MANAGER_PASS)

    driver = get_driver()
    try:
        logged_in = login_ui(MANAGER_EMAIL, MANAGER_PASS)
        if logged_in:
            screenshot("manager_logged_in")
            test_manager_dashboard()
            test_manager_page()
            test_manager_team_attendance()
            test_manager_pending_approvals()
            test_manager_team_calendar()
            test_manager_team_members()
            test_manager_rewards(manager_token)
        else:
            sp = screenshot("manager_login_fail")
            record("Manager: Login", False, "UI Login failed")
            file_bug("Manager login fails for ananya@technova.in",
                     "Cannot login with ananya@technova.in / Welcome@123.",
                     sp, ["bug", "e2e-test", "fresh-test", "manager-experience"])

        # API-only tests
        if manager_token:
            test_manager_team_attendance_api(manager_token)
            test_manager_approvals_api(manager_token)
            test_manager_team_leave_balances(manager_token)
            test_manager_team_members_api(manager_token)
            test_manager_team_helpdesk(manager_token)
            test_manager_reports(manager_token)
        else:
            record("Manager: API Login", False, "Could not get API token")

    except Exception as e:
        print(f"\n[ERROR] Manager tests crashed: {e}")
        traceback.print_exc()
        screenshot("manager_crash")
    finally:
        try:
            driver.quit()
        except:
            pass

    # ── SUMMARY ──
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for t in test_results if t["passed"])
    failed = sum(1 for t in test_results if not t["passed"])
    total = len(test_results)

    print(f"\nTotal: {total}  |  Passed: {passed}  |  Failed: {failed}")
    print(f"Bugs filed/found: {len(bugs_found)}")

    print("\n--- PASS ---")
    for t in test_results:
        if t["passed"]:
            print(f"  [PASS] {t['test']}: {t['details']}")

    print("\n--- FAIL ---")
    for t in test_results:
        if not t["passed"]:
            print(f"  [FAIL] {t['test']}: {t['details']}")

    if bugs_found:
        print("\n--- BUGS ---")
        for b in bugs_found:
            existing = " (existing)" if b.get("existing") else ""
            print(f"  {b['title']}{existing}: {b.get('url', 'N/A')}")

    # Save results
    results_path = SCREENSHOT_DIR / "test_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {"total": total, "passed": passed, "failed": failed},
            "results": test_results,
            "bugs": bugs_found
        }, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {results_path}")
    print(f"Screenshots in {SCREENSHOT_DIR}")


if __name__ == "__main__":
    main()
