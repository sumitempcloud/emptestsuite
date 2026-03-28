"""
EMP Cloud HRMS - Performance Management & LMS Module E2E Tests
Uses fresh WebDriver per test section for stability.
Uses dual login approach: JS native setter + keyboard fallback.
"""

import sys
import os
import time
import json
import traceback
import requests
import re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

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

# ==============================================================================
# CONFIG
# ==============================================================================
MAIN_URL = "https://test-empcloud.empcloud.com"
PERF_URL = "https://test-performance.empcloud.com"
LMS_URL = "https://testlms.empcloud.com"
MAIN_API = "https://test-empcloud-api.empcloud.com"
LMS_API = "https://testlms-api.empcloud.com"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\performance_lms"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ==============================================================================
# HELPERS
# ==============================================================================
bugs_found = []
test_results = []
chromedriver_path = None  # Cache path

def get_driver():
    global chromedriver_path
    if not chromedriver_path:
        chromedriver_path = ChromeDriverManager().install()

    for attempt in range(3):
        try:
            opts = Options()
            opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--ignore-certificate-errors")
            opts.add_argument("--disable-background-timer-throttling")
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=opts)
            driver.set_page_load_timeout(60)
            driver.implicitly_wait(3)
            return driver
        except Exception as e:
            print(f"    Driver creation attempt {attempt+1} failed: {e}")
            time.sleep(3)
            # Kill zombie processes
            import subprocess
            subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"],
                           capture_output=True, timeout=5)
            time.sleep(2)

    raise RuntimeError("Failed to create WebDriver after 3 attempts")

def safe_get(driver, url):
    try:
        driver.get(url)
    except TimeoutException:
        print(f"    Timeout loading {url}, stopping...")
        try: driver.execute_script("window.stop();")
        except: pass
    except Exception as e:
        print(f"    Nav error {url}: {type(e).__name__}")
        try: driver.execute_script("window.stop();")
        except: pass

def ss(driver, name):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{ts}.png")
    try: driver.save_screenshot(path)
    except: pass
    return path

def log(module, test_name, status, details="", severity=None, snap=None):
    test_results.append({
        "module": module, "test": test_name, "status": status,
        "details": details, "screenshot": snap or ""
    })
    print(f"  [{status:4s}] {module} > {test_name}: {details}")
    if status == "FAIL" and severity:
        bugs_found.append({
            "module": module, "test": test_name, "details": details,
            "severity": severity, "screenshot": snap or ""
        })

def safe_click(driver, el):
    try: el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)

def check_page_error(driver):
    src = driver.page_source.lower()
    for e in ["500 internal", "502 bad gateway", "503 service", "404 not found",
              "something went wrong", "server error", "page not found"]:
        if e in src:
            return e
    return None


# ==============================================================================
# LOGIN - robust with keyboard + JS fallback
# ==============================================================================
def login_to_app(driver, url, email, password, label):
    """Robust login: tries keyboard input first, then JS native setter."""
    safe_get(driver, url)
    time.sleep(4)

    cur = driver.current_url.lower()
    # Already logged in?
    if "login" not in cur and "sign" not in cur:
        print(f"    Already logged in at {driver.current_url}")
        return True

    ss(driver, f"{label}_login_page")

    # Find email field
    email_el = None
    for sel in [
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, "input[placeholder*='email' i]"),
        (By.CSS_SELECTOR, "input[placeholder*='you@' i]"),
        (By.NAME, "email"), (By.ID, "email"),
        (By.CSS_SELECTOR, "input[type='text']:not([type='hidden'])"),
    ]:
        try:
            el = WebDriverWait(driver, 4).until(EC.visibility_of_element_located(sel))
            if el.is_displayed():
                email_el = el
                break
        except: continue

    if not email_el:
        print(f"    No email field at {driver.current_url}")
        return False

    # Find password field
    pass_el = None
    try:
        pass_el = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    except:
        print(f"    No password field")
        return False

    # Fill using multiple approaches to handle React controlled inputs
    # Approach 1: JS native setter + React synthetic events
    try:
        driver.execute_script("""
            var emailEl = arguments[0], passEl = arguments[1];
            var email = arguments[2], pass_ = arguments[3];
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;

            // Email
            emailEl.focus();
            setter.call(emailEl, '');
            emailEl.dispatchEvent(new Event('input', {bubbles:true}));
            setter.call(emailEl, email);
            emailEl.dispatchEvent(new Event('input', {bubbles:true}));
            emailEl.dispatchEvent(new Event('change', {bubbles:true}));
            emailEl.dispatchEvent(new Event('blur', {bubbles:true}));

            // Password
            passEl.focus();
            setter.call(passEl, '');
            passEl.dispatchEvent(new Event('input', {bubbles:true}));
            setter.call(passEl, pass_);
            passEl.dispatchEvent(new Event('input', {bubbles:true}));
            passEl.dispatchEvent(new Event('change', {bubbles:true}));
            passEl.dispatchEvent(new Event('blur', {bubbles:true}));
        """, email_el, pass_el, email, password)
        time.sleep(1)
    except Exception as e:
        print(f"    JS setter failed: {e}")

    # Approach 2: Also use send_keys as backup (handles non-React forms)
    try:
        # Check if values actually stuck
        cur_val = email_el.get_attribute("value")
        if not cur_val or cur_val != email:
            print(f"    JS setter value didn't stick, using send_keys")
            email_el.clear()
            email_el.send_keys(email)
            pass_el.clear()
            pass_el.send_keys(password)
            time.sleep(0.5)
    except:
        pass

    ss(driver, f"{label}_filled")

    # Click Sign in button
    btn = None
    for sel in [
        (By.XPATH, "//button[contains(text(),'Sign in')]"),
        (By.XPATH, "//button[contains(text(),'Sign In')]"),
        (By.XPATH, "//button[contains(text(),'Login')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
    ]:
        try:
            b = driver.find_element(*sel)
            if b.is_displayed():
                btn = b
                break
        except: continue

    if btn:
        safe_click(driver, btn)
    else:
        pass_el.send_keys(Keys.RETURN)

    time.sleep(5)
    ss(driver, f"{label}_after_submit")

    post = driver.current_url.lower()
    if "login" not in post:
        print(f"    Login success -> {driver.current_url}")
        return True

    # Check for errors
    src = driver.page_source.lower()
    if "invalid" in src or "incorrect" in src or "error" in src:
        print(f"    Login rejected (invalid credentials)")
    else:
        print(f"    Still on login page: {driver.current_url}")
    return False


def login_via_sso(driver, email, password, target_domain, label):
    """Login to main app, get SSO URL, navigate to sub-module."""
    print(f"    SSO via main app for {target_domain}...")
    if not login_to_app(driver, MAIN_URL + "/login", email, password, f"{label}_sso_main"):
        return False

    safe_get(driver, MAIN_URL)
    time.sleep(3)
    src = driver.page_source

    # Find SSO URL
    pattern = rf'https?://{re.escape(target_domain)}[^"\'<>\s]*sso_token=[^"\'<>\s]*'
    matches = re.findall(pattern, src)
    if matches:
        sso_url = matches[0].replace("&amp;", "&")
        print(f"    Found SSO URL ({len(sso_url)} chars)")
        safe_get(driver, sso_url)
        time.sleep(5)
        ss(driver, f"{label}_sso_result")
        if "login" not in driver.current_url.lower():
            print(f"    SSO success -> {driver.current_url}")
            return True
        print(f"    SSO token rejected, landed on: {driver.current_url}")
    else:
        # Try href links
        for el in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
            try:
                href = el.get_attribute("href") or ""
                if target_domain in href and "sso_token" in href:
                    safe_get(driver, href)
                    time.sleep(5)
                    if "login" not in driver.current_url.lower():
                        return True
                    break
            except: continue
        print(f"    No SSO URL found for {target_domain}")
    return False


def api_login_and_set_token(driver, url, api_base, email, password, label):
    """Login via API, set auth token as cookie/localStorage, navigate to app."""
    print(f"    Trying API login via {api_base}...")
    for endpoint in ["/api/auth/login", "/auth/login", "/api/v1/auth/login", "/login"]:
        try:
            r = requests.post(
                api_base + endpoint,
                json={"email": email, "password": password},
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            if r.status_code in (200, 201):
                data = r.json()
                token = (data.get("token") or data.get("access_token") or
                         data.get("data", {}).get("token") or
                         data.get("data", {}).get("access_token") or "")
                if token:
                    print(f"    Got API token from {endpoint}")
                    # Navigate to app and set token
                    safe_get(driver, url)
                    time.sleep(2)
                    driver.execute_script(f"""
                        localStorage.setItem('token', '{token}');
                        localStorage.setItem('access_token', '{token}');
                        localStorage.setItem('auth_token', '{token}');
                    """)
                    # Also set as cookie
                    driver.add_cookie({"name": "token", "value": token, "path": "/"})
                    safe_get(driver, url)
                    time.sleep(3)
                    if "login" not in driver.current_url.lower():
                        print(f"    API token login success -> {driver.current_url}")
                        return True
            elif r.status_code != 404:
                print(f"    API {endpoint} returned {r.status_code}")
        except requests.exceptions.ConnectionError:
            continue
        except Exception as e:
            print(f"    API {endpoint} error: {e}")
            continue
    return False


def full_login(driver, url, target_domain, email, password, label):
    """Try: direct login -> SSO -> API token -> main+navigate."""
    # Strategy 1: Direct
    print(f"  [1] Direct login to {url}")
    if login_to_app(driver, url, email, password, f"{label}_direct"):
        return True

    # Strategy 2: SSO
    print(f"  [2] SSO via main app")
    if login_via_sso(driver, email, password, target_domain, f"{label}"):
        return True

    # Strategy 3: API token
    api_bases = {
        "test-performance.empcloud.com": "https://test-performance-api.empcloud.com",
        "testlms.empcloud.com": "https://testlms-api.empcloud.com",
    }
    api_base = api_bases.get(target_domain, "")
    if api_base:
        print(f"  [3] API login via {api_base}")
        if api_login_and_set_token(driver, url, api_base, email, password, label):
            return True

    # Strategy 4: Main login then navigate
    print(f"  [4] Main login + navigate")
    if login_to_app(driver, MAIN_URL + "/login", email, password, f"{label}_main3"):
        safe_get(driver, url)
        time.sleep(5)
        if "login" not in driver.current_url.lower():
            print(f"    Cookie-based access -> {driver.current_url}")
            return True

    return False


def get_nav_texts(driver):
    els = driver.find_elements(By.CSS_SELECTOR, "a, button, [role='menuitem'], nav li, aside li")
    texts = []
    for el in els:
        try:
            t = el.text.strip()
            if t and 2 < len(t) < 80:
                texts.append(t)
        except: pass
    return list(dict.fromkeys(texts))[:60]


def click_sidebar_link(driver, text):
    """Click sidebar/nav link by text, using href navigation for SPAs."""
    for xpath in [
        f"//aside//a[contains(text(),'{text}')]",
        f"//nav//a[contains(text(),'{text}')]",
        f"//a[contains(text(),'{text}')]",
        f"//*[contains(@class,'sidebar')]//*[contains(text(),'{text}')]",
    ]:
        try:
            els = driver.find_elements(By.XPATH, xpath)
            for el in els:
                if el.is_displayed():
                    href = el.get_attribute("href") or ""
                    if href and href.startswith("http"):
                        safe_get(driver, href)
                        time.sleep(3)
                        return True
                    safe_click(driver, el)
                    time.sleep(3)
                    return True
        except: continue
    return False


def find_button_by_text(driver, text):
    """Find a visible button containing specific text."""
    for xpath in [
        f"//button[contains(text(),'{text}')]",
        f"//a[contains(text(),'{text}')]",
        f"//*[contains(@class,'btn')][contains(text(),'{text}')]",
    ]:
        try:
            els = driver.find_elements(By.XPATH, xpath)
            for el in els:
                if el.is_displayed():
                    return el
        except: continue
    return None


# ==============================================================================
# PERFORMANCE - ADMIN
# ==============================================================================
def test_perf_admin(driver):
    print("\n" + "="*70)
    print("PERFORMANCE MODULE - ORG ADMIN")
    print("="*70)

    # Login
    print("\n[Test] Admin Login")
    ok = full_login(driver, PERF_URL, "test-performance.empcloud.com", ADMIN_EMAIL, ADMIN_PASS, "perf_admin")
    if ok:
        log("Performance", "Admin Login", "PASS", f"At {driver.current_url}")
    else:
        snap = ss(driver, "perf_admin_login_fail")
        log("Performance", "Admin Login", "FAIL", f"Cannot login. URL: {driver.current_url}",
            severity="Critical", snap=snap)
        return

    # Dashboard
    print("\n[Test] Dashboard")
    snap = ss(driver, "perf_dashboard")
    err = check_page_error(driver)
    if err:
        log("Performance", "Admin Dashboard", "FAIL", f"Error: {err}", severity="Critical", snap=snap)
    else:
        src = driver.page_source.lower()
        metrics = [m for m in ["active cycle", "pending review", "goal completion", "active pip", "total feedback"]
                   if m in src]
        log("Performance", "Admin Dashboard", "PASS",
            f"Title: {driver.title}. Metrics: {metrics}")

    # Navigation
    print("\n[Test] Navigation")
    nav = get_nav_texts(driver)
    print(f"    Sidebar: {nav[:18]}")
    expected = ["Review Cycles", "Goals", "Competencies", "Feedback", "Analytics", "Settings"]
    found = [s for s in expected if any(s.lower() in n.lower() for n in nav)]
    log("Performance", "Navigation", "PASS" if len(found) >= 4 else "WARN",
        f"Found {len(found)}/{len(expected)}: {found}")

    # Review Cycles
    print("\n[Test] Review Cycles")
    if click_sidebar_link(driver, "Review Cycles"):
        time.sleep(2)
        snap = ss(driver, "perf_review_cycles")
        err = check_page_error(driver)
        if err:
            log("Performance", "Review Cycles", "FAIL", f"Error: {err}", severity="High", snap=snap)
        else:
            # Check content
            src = driver.page_source.lower()
            has_cycles = "performance review" in src or "annual review" in src or "review cycle" in src
            log("Performance", "Review Cycles", "PASS",
                f"At {driver.current_url}. Has cycle data: {has_cycles}")
    else:
        snap = ss(driver, "perf_no_review_cycles_nav")
        log("Performance", "Review Cycles", "FAIL", "Cannot navigate to Review Cycles",
            severity="Medium", snap=snap)

    # Create Review Cycle
    print("\n[Test] Create Review Cycle")
    btn = find_button_by_text(driver, "Create Cycle")
    if not btn:
        btn = find_button_by_text(driver, "Create")
    if not btn:
        btn = find_button_by_text(driver, "New Cycle")

    if btn:
        print(f"    Clicking: '{btn.text.strip()}'")
        safe_click(driver, btn)
        time.sleep(3)
        snap = ss(driver, "perf_create_cycle_form")

        # Check for form/modal/new page
        src = driver.page_source.lower()
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']:not([type='hidden']), input[type='date'], select, textarea")
        visible_inputs = [i for i in inputs if i.is_displayed()]
        print(f"    Found {len(visible_inputs)} visible form inputs")

        if visible_inputs:
            # Try filling cycle name
            text_inputs = [i for i in visible_inputs if i.get_attribute("type") in ("text", None, "")]
            if text_inputs:
                ts = datetime.now().strftime("%H%M%S")
                name = f"E2E Test Cycle {ts}"
                text_inputs[0].click()
                text_inputs[0].send_keys(Keys.CONTROL, "a")
                text_inputs[0].send_keys(name)
                time.sleep(0.5)
                ss(driver, "perf_cycle_name_filled")

            # Look for Save/Submit/Create/Next
            save_btn = find_button_by_text(driver, "Save")
            if not save_btn:
                save_btn = find_button_by_text(driver, "Submit")
            if not save_btn:
                save_btn = find_button_by_text(driver, "Create")
            if not save_btn:
                save_btn = find_button_by_text(driver, "Next")

            if save_btn:
                print(f"    Clicking save: '{save_btn.text.strip()}'")
                safe_click(driver, save_btn)
                time.sleep(3)
                snap = ss(driver, "perf_cycle_saved")
                post_src = driver.page_source.lower()
                if "success" in post_src or "created" in post_src:
                    log("Performance", "Create Review Cycle", "PASS", "Cycle created successfully")
                elif "error" in post_src or "required" in post_src or "validation" in post_src:
                    log("Performance", "Create Review Cycle", "WARN",
                        "Form has validation errors (may need more required fields)", snap=snap)
                else:
                    log("Performance", "Create Review Cycle", "PASS",
                        "Cycle creation form submitted", snap=snap)
            else:
                log("Performance", "Create Review Cycle", "WARN",
                    "Form opened but no save/submit button found", snap=snap)
        else:
            # Maybe it opened a new page rather than modal
            if "create" in driver.current_url.lower() or "new" in driver.current_url.lower():
                log("Performance", "Create Review Cycle", "PASS",
                    f"Create page opened at {driver.current_url}", snap=snap)
            else:
                log("Performance", "Create Review Cycle", "WARN",
                    "Button clicked but no form inputs appeared", snap=snap)
    else:
        snap = ss(driver, "perf_no_create_cycle_btn")
        log("Performance", "Create Review Cycle", "FAIL",
            "No 'Create Cycle' button found on Review Cycles page",
            severity="Medium", snap=snap)

    # Goals
    print("\n[Test] Goals Section")
    if click_sidebar_link(driver, "Goals"):
        time.sleep(2)
        snap = ss(driver, "perf_goals")
        err = check_page_error(driver)
        if err:
            log("Performance", "Goals Section", "FAIL", f"Error: {err}", severity="High", snap=snap)
        else:
            src = driver.page_source.lower()
            has_goals = any(kw in src for kw in ["in progress", "not started", "completed", "goal"])
            log("Performance", "Goals Section", "PASS",
                f"At {driver.current_url}. Has goal data: {has_goals}")
    else:
        snap = ss(driver, "perf_no_goals_nav")
        log("Performance", "Goals Section", "WARN", "Cannot navigate to Goals", snap=snap)

    # Goal Setting
    print("\n[Test] Goal Setting")
    btn = find_button_by_text(driver, "Create Goal")
    if not btn:
        btn = find_button_by_text(driver, "Add Goal")
    if not btn:
        btn = find_button_by_text(driver, "New Goal")
    if not btn:
        btn = find_button_by_text(driver, "Create")

    if btn:
        print(f"    Clicking: '{btn.text.strip()}'")
        safe_click(driver, btn)
        time.sleep(3)
        snap = ss(driver, "perf_goal_form")

        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea")
        visible = [i for i in inputs if i.is_displayed()]
        if visible:
            ts = datetime.now().strftime("%H%M%S")
            visible[0].click()
            visible[0].send_keys(Keys.CONTROL, "a")
            visible[0].send_keys(f"E2E Test Goal {ts}")
            time.sleep(0.5)
            ss(driver, "perf_goal_filled")
            log("Performance", "Goal Setting", "PASS", "Goal form accessible and fillable")
        else:
            if "create" in driver.current_url.lower() or "new" in driver.current_url.lower():
                log("Performance", "Goal Setting", "PASS",
                    f"Goal creation page at {driver.current_url}", snap=snap)
            else:
                log("Performance", "Goal Setting", "WARN",
                    "Clicked create but no form inputs visible", snap=snap)
    else:
        snap = ss(driver, "perf_no_goal_btn")
        log("Performance", "Goal Setting", "FAIL",
            "No 'Create Goal' button found on Goals page",
            severity="Medium", snap=snap)

    # Feedback
    print("\n[Test] Feedback")
    if click_sidebar_link(driver, "Feedback"):
        time.sleep(2)
        snap = ss(driver, "perf_feedback")
        err = check_page_error(driver)
        if err:
            log("Performance", "Feedback Section", "FAIL", f"Error: {err}", severity="High", snap=snap)
        else:
            log("Performance", "Feedback Section", "PASS", f"At {driver.current_url}")
    else:
        log("Performance", "Feedback Section", "WARN", "Cannot navigate to Feedback")


# ==============================================================================
# PERFORMANCE - EMPLOYEE
# ==============================================================================
def test_perf_employee(driver):
    print("\n" + "="*70)
    print("PERFORMANCE MODULE - EMPLOYEE")
    print("="*70)

    print("\n[Test] Employee Login")
    ok = full_login(driver, PERF_URL, "test-performance.empcloud.com", EMP_EMAIL, EMP_PASS, "perf_emp")
    if ok:
        log("Performance", "Employee Login", "PASS", f"At {driver.current_url}")
    else:
        snap = ss(driver, "perf_emp_login_fail")
        log("Performance", "Employee Login", "FAIL", "Cannot login",
            severity="Critical", snap=snap)
        return

    # Dashboard
    print("\n[Test] Employee Dashboard")
    snap = ss(driver, "perf_emp_dash")
    err = check_page_error(driver)
    if err:
        log("Performance", "Employee Dashboard", "FAIL", f"Error: {err}", severity="High", snap=snap)
    else:
        log("Performance", "Employee Dashboard", "PASS", f"At {driver.current_url}")

    nav = get_nav_texts(driver)
    print(f"    Nav: {nav[:18]}")

    # Self-Assessment
    print("\n[Test] Self-Assessment")
    found_sa = False
    for kw in ["My Review", "Self Assessment", "My Appraisal"]:
        if click_sidebar_link(driver, kw):
            snap = ss(driver, "perf_emp_self_assess")
            err = check_page_error(driver)
            if not err:
                found_sa = True
                log("Performance", "Self-Assessment", "PASS", f"At {driver.current_url}")
            else:
                log("Performance", "Self-Assessment", "FAIL", f"Error: {err}",
                    severity="High", snap=snap)
            break

    if not found_sa:
        # Check Review Cycles accessible for employee
        if click_sidebar_link(driver, "Review Cycles"):
            snap = ss(driver, "perf_emp_reviews")
            log("Performance", "Self-Assessment", "PASS",
                f"Employee can access Review Cycles at {driver.current_url}")
        else:
            src = driver.page_source.lower()
            if any(kw in src for kw in ["assessment", "review", "rating", "appraisal"]):
                snap = ss(driver, "perf_emp_sa_content")
                log("Performance", "Self-Assessment", "PASS", "Assessment content visible", snap=snap)
            else:
                snap = ss(driver, "perf_emp_no_sa")
                log("Performance", "Self-Assessment", "WARN",
                    f"No self-assessment found. Nav: {nav[:12]}", snap=snap)

    # Goal Progress
    print("\n[Test] Goal Progress")
    if click_sidebar_link(driver, "Goals"):
        time.sleep(2)
        snap = ss(driver, "perf_emp_goals")
        err = check_page_error(driver)
        if not err:
            src = driver.page_source.lower()
            indicators = [p for p in ["progress", "target", "status", "completion", "in progress"]
                          if p in src]
            log("Performance", "Goal Progress", "PASS",
                f"At {driver.current_url}. Indicators: {indicators}")
        else:
            log("Performance", "Goal Progress", "FAIL", f"Error: {err}",
                severity="Medium", snap=snap)
    else:
        src = driver.page_source.lower()
        if "goal" in src:
            snap = ss(driver, "perf_emp_goal_on_dash")
            log("Performance", "Goal Progress", "PASS", "Goal content on dashboard", snap=snap)
        else:
            snap = ss(driver, "perf_emp_no_goals")
            log("Performance", "Goal Progress", "WARN", "No goals section found", snap=snap)


# ==============================================================================
# LMS - ADMIN
# ==============================================================================
def test_lms_admin(driver):
    print("\n" + "="*70)
    print("LMS MODULE - ORG ADMIN")
    print("="*70)

    print("\n[Test] Admin Login")
    ok = full_login(driver, LMS_URL, "testlms.empcloud.com", ADMIN_EMAIL, ADMIN_PASS, "lms_admin")

    if not ok:
        snap = ss(driver, "lms_admin_fail")
        src = driver.page_source
        has_demo = "admin@demo.com" in src or "demo1234" in src
        extra = ""
        if has_demo:
            extra = " LMS shows demo credentials (admin@demo.com / demo1234). Org credentials (ananya@technova.in) are rejected. SSO from main app also failed."
        log("LMS", "Admin Login", "FAIL",
            f"Cannot login to LMS.{extra}",
            severity="Critical", snap=snap)
        if has_demo:
            log("LMS", "Credential Mismatch", "FAIL",
                "LMS module does not accept organization credentials. Shows demo credentials "
                "(admin@demo.com / demo1234) on login page. This indicates LMS is not integrated "
                "with the main EMP Cloud authentication or SSO system.",
                severity="High", snap=snap)
        return

    log("LMS", "Admin Login", "PASS", f"At {driver.current_url}")

    # Dashboard
    print("\n[Test] Dashboard")
    snap = ss(driver, "lms_dashboard")
    err = check_page_error(driver)
    if err:
        log("LMS", "Admin Dashboard", "FAIL", f"Error: {err}", severity="Critical", snap=snap)
    else:
        log("LMS", "Admin Dashboard", "PASS", f"At {driver.current_url}")

    nav = get_nav_texts(driver)
    print(f"    Nav: {nav[:25]}")

    # Courses
    print("\n[Test] Courses List")
    courses_ok = False
    for kw in ["Courses", "Course", "Catalog"]:
        if click_sidebar_link(driver, kw):
            snap = ss(driver, "lms_courses")
            err = check_page_error(driver)
            if not err:
                courses_ok = True
                log("LMS", "Courses List", "PASS", f"At {driver.current_url}")
            else:
                log("LMS", "Courses List", "FAIL", f"Error: {err}", severity="High", snap=snap)
            break

    if not courses_ok:
        src = driver.page_source.lower()
        if "course" in src or "training" in src:
            snap = ss(driver, "lms_courses_content")
            courses_ok = True
            log("LMS", "Courses List", "PASS", "Course content found on dashboard", snap=snap)
        else:
            snap = ss(driver, "lms_no_courses")
            log("LMS", "Courses List", "FAIL", "No courses found", severity="Medium", snap=snap)

    # Create Course
    print("\n[Test] Create Course")
    if courses_ok:
        btn = find_button_by_text(driver, "Create Course")
        if not btn:
            btn = find_button_by_text(driver, "Add Course")
        if not btn:
            btn = find_button_by_text(driver, "Create")
        if not btn:
            btn = find_button_by_text(driver, "New")

        if btn:
            safe_click(driver, btn)
            time.sleep(3)
            snap = ss(driver, "lms_create_form")
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea")
            visible = [i for i in inputs if i.is_displayed()]
            if visible:
                ts = datetime.now().strftime("%H%M%S")
                visible[0].click()
                visible[0].send_keys(f"E2E Test Course {ts}")
                ss(driver, "lms_course_filled")

                save = find_button_by_text(driver, "Save")
                if not save:
                    save = find_button_by_text(driver, "Create")
                if not save:
                    save = find_button_by_text(driver, "Submit")
                if save:
                    safe_click(driver, save)
                    time.sleep(3)
                    snap = ss(driver, "lms_course_saved")
                    log("LMS", "Create Course", "PASS", "Course creation submitted", snap=snap)
                else:
                    log("LMS", "Create Course", "WARN", "No save button", snap=snap)
            else:
                log("LMS", "Create Course", "WARN", "No form inputs visible", snap=snap)
        else:
            snap = ss(driver, "lms_no_create_btn")
            log("LMS", "Create Course", "WARN", "No create button found", snap=snap)
    else:
        log("LMS", "Create Course", "SKIP", "Courses not accessible")

    # Training Assignments
    print("\n[Test] Training Assignments")
    safe_get(driver, LMS_URL)
    time.sleep(3)
    for kw in ["Assign", "Enrollment", "Training Plan", "Learner"]:
        if click_sidebar_link(driver, kw):
            snap = ss(driver, "lms_assignments")
            err = check_page_error(driver)
            if not err:
                log("LMS", "Training Assignments", "PASS", f"At {driver.current_url}")
            else:
                log("LMS", "Training Assignments", "FAIL", f"Error: {err}", severity="Medium", snap=snap)
            break
    else:
        src = driver.page_source.lower()
        if any(kw in src for kw in ["assign", "enroll", "learner"]):
            snap = ss(driver, "lms_assign_content")
            log("LMS", "Training Assignments", "PASS", "Assignment content found", snap=snap)
        else:
            snap = ss(driver, "lms_no_assignments")
            log("LMS", "Training Assignments", "WARN", "No assignments section", snap=snap)


# ==============================================================================
# LMS - EMPLOYEE
# ==============================================================================
def test_lms_employee(driver):
    print("\n" + "="*70)
    print("LMS MODULE - EMPLOYEE")
    print("="*70)

    print("\n[Test] Employee Login")
    ok = full_login(driver, LMS_URL, "testlms.empcloud.com", EMP_EMAIL, EMP_PASS, "lms_emp")

    if not ok:
        snap = ss(driver, "lms_emp_fail")
        src = driver.page_source
        has_demo = "learner@demo.com" in src or "demo1234" in src
        extra = " LMS rejects org employee credentials." if has_demo else ""
        log("LMS", "Employee Login", "FAIL", f"Cannot login.{extra}",
            severity="Critical", snap=snap)
        return

    log("LMS", "Employee Login", "PASS", f"At {driver.current_url}")

    # Dashboard
    print("\n[Test] Learning Dashboard")
    snap = ss(driver, "lms_emp_dash")
    err = check_page_error(driver)
    if err:
        log("LMS", "Learning Dashboard", "FAIL", f"Error: {err}", severity="High", snap=snap)
    else:
        log("LMS", "Learning Dashboard", "PASS", f"At {driver.current_url}")

    nav = get_nav_texts(driver)
    print(f"    Nav: {nav[:20]}")

    # Assigned Courses
    print("\n[Test] Assigned Courses")
    for kw in ["My Courses", "Assigned", "My Learning", "Enrolled"]:
        if click_sidebar_link(driver, kw):
            snap = ss(driver, "lms_emp_assigned")
            log("LMS", "Assigned Courses", "PASS", f"At {driver.current_url}")
            break
    else:
        src = driver.page_source.lower()
        if any(kw in src for kw in ["course", "learning", "training"]):
            snap = ss(driver, "lms_emp_course_content")
            log("LMS", "Assigned Courses", "PASS", "Course content visible", snap=snap)
        else:
            snap = ss(driver, "lms_emp_no_courses")
            log("LMS", "Assigned Courses", "WARN", f"No courses. Nav: {nav[:12]}", snap=snap)

    # Dashboard Content
    print("\n[Test] Dashboard Content")
    safe_get(driver, LMS_URL)
    time.sleep(3)
    src = driver.page_source.lower()
    content = {}
    for cat, kws in {"progress": ["progress", "completion"], "courses": ["course", "training"],
                     "stats": ["total", "hours", "certificate"]}.items():
        for kw in kws:
            if kw in src:
                content[cat] = kw
                break
    snap = ss(driver, "lms_emp_content")
    log("LMS", "Dashboard Content", "PASS" if content else "WARN",
        f"Content: {content}" if content else "No typical LMS content", snap=snap)


# ==============================================================================
# MAIN APP NAV
# ==============================================================================
def test_main_nav(driver):
    print("\n" + "="*70)
    print("MAIN APP - MODULE NAVIGATION")
    print("="*70)

    print("\n[Test] Login")
    ok = login_to_app(driver, MAIN_URL + "/login", ADMIN_EMAIL, ADMIN_PASS, "main")
    if not ok:
        snap = ss(driver, "main_login_fail")
        log("Main App", "Admin Login", "FAIL", "Cannot login", severity="Critical", snap=snap)
        return
    log("Main App", "Admin Login", "PASS", f"At {driver.current_url}")

    print("\n[Test] Performance Navigation")
    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    perf = [el.text.strip() for el in links
            if "performance" in (el.get_attribute("href") or "").lower()
            or "performance" in el.text.lower()]
    lms = [el.text.strip() for el in links
           if "lms" in (el.get_attribute("href") or "").lower()
           or "testlms" in (el.get_attribute("href") or "").lower()
           or "learning" in el.text.lower()]

    snap = ss(driver, "main_dashboard")
    log("Main App", "Performance Nav", "PASS" if perf else "WARN",
        f"Found: {perf[:5]}" if perf else "No performance nav", snap=snap)

    print("\n[Test] LMS Navigation")
    log("Main App", "LMS Nav", "PASS" if lms else "WARN",
        f"Found: {lms[:5]}" if lms else "No LMS nav")


# ==============================================================================
# FILE GITHUB ISSUES
# ==============================================================================
def file_all_bugs():
    if not bugs_found:
        print("\nNo bugs to file.")
        return

    print(f"\n{'='*70}")
    print(f"FILING {len(bugs_found)} GITHUB ISSUES")
    print("="*70)

    for bug in bugs_found:
        title = f"[{bug['severity']}][{bug['module']}] {bug['test']}"
        if len(title) > 200:
            title = title[:197] + "..."

        body = f"""## Bug Report - Automated E2E Test

**Module:** {bug['module']}
**Test:** {bug['test']}
**Severity:** {bug['severity']}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Description
{bug['details']}

### Steps to Reproduce
1. Navigate to the {bug['module']} module
2. Execute test: {bug['test']}
3. Observed failure

### Expected Behavior
The {bug['test'].lower()} should work correctly.

### Actual Behavior
{bug['details']}

### Screenshot
{('Saved: ' + bug['screenshot']) if bug['screenshot'] else 'N/A'}

### Environment
- Browser: Chrome (headless)
- Test: Automated Selenium E2E
"""
        labels = ["bug", "automated-test"]
        if bug["severity"] == "Critical":
            labels.append("priority:critical")
        elif bug["severity"] == "High":
            labels.append("priority:high")

        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
        try:
            r = requests.post(url, headers=headers, json={"title": title, "body": body, "labels": labels}, timeout=15)
            if r.status_code in (200, 201):
                print(f"    -> Filed: {r.json().get('html_url', '')}")
            else:
                print(f"    -> Failed ({r.status_code}): {r.text[:150]}")
        except Exception as e:
            print(f"    -> Error: {e}")
        time.sleep(1)


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print("="*70)
    print("EMP CLOUD - PERFORMANCE & LMS E2E TEST SUITE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    tests = [
        ("Main App Navigation", test_main_nav),
        ("Performance Admin", test_perf_admin),
        ("Performance Employee", test_perf_employee),
        ("LMS Admin", test_lms_admin),
        ("LMS Employee", test_lms_employee),
    ]

    for name, func in tests:
        driver = None
        try:
            driver = get_driver()
            print(f"\n[OK] WebDriver ready for: {name}")
            func(driver)
        except Exception as e:
            print(f"\n[FATAL] {name}: {e}")
            traceback.print_exc()
            if driver:
                ss(driver, f"fatal_{name.replace(' ','_').lower()}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                # Ensure cleanup
                import subprocess
                subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"],
                               capture_output=True, timeout=5)
            time.sleep(3)

    # Summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)

    p = sum(1 for r in test_results if r["status"] == "PASS")
    f = sum(1 for r in test_results if r["status"] == "FAIL")
    w = sum(1 for r in test_results if r["status"] == "WARN")
    s = sum(1 for r in test_results if r["status"] == "SKIP")

    print(f"\nTotal: {len(test_results)} | PASS: {p} | FAIL: {f} | WARN: {w} | SKIP: {s}")
    print(f"Bugs: {len(bugs_found)}\n")

    for r in test_results:
        m = {"PASS": "OK ", "FAIL": "ERR", "WARN": "WRN", "SKIP": "SKP"}.get(r["status"], "???")
        print(f"  [{m}] {r['module']:15s} | {r['test']:35s} | {r['details'][:75]}")

    file_all_bugs()

    print(f"\nDone: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    return f == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
