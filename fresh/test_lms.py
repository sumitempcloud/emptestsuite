"""
EMP Cloud LMS Module - Fresh E2E Test Suite
Tests admin and employee flows: dashboard, courses, learning paths,
certifications, compliance, analytics, settings, quizzes, RBAC.
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
LMS_URL = "https://testlms.empcloud.com"
MAIN_API = "https://test-empcloud-api.empcloud.com"
LMS_API = "https://testlms-api.empcloud.com"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_lms"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ==============================================================================
# GLOBALS
# ==============================================================================
bugs_found = []
test_results = []
chromedriver_path = None


# ==============================================================================
# HELPERS
# ==============================================================================
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
    icon = {"PASS": "+", "FAIL": "X", "WARN": "!", "SKIP": "-"}.get(status, "?")
    print(f"  [{icon} {status:4s}] {module} > {test_name}: {details}")
    if status == "FAIL" and severity:
        bugs_found.append({
            "module": module, "test": test_name, "details": details,
            "severity": severity, "screenshot": snap or ""
        })


def safe_click(driver, el):
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)


def check_page_error(driver):
    src = driver.page_source.lower()
    for e in ["500 internal", "502 bad gateway", "503 service", "404 not found",
              "something went wrong", "server error", "page not found"]:
        if e in src:
            return e
    return None


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


def navigate_to_page(driver, path, base=LMS_URL):
    """Navigate to a specific LMS page path."""
    url = base.rstrip("/") + "/" + path.lstrip("/")
    safe_get(driver, url)
    time.sleep(3)


def count_table_rows(driver):
    """Count visible rows in the first table or list on the page."""
    for sel in ["table tbody tr", "[role='row']", ".list-item", "li.course-item"]:
        rows = driver.find_elements(By.CSS_SELECTOR, sel)
        visible = [r for r in rows if r.is_displayed()]
        if visible:
            return len(visible)
    return 0


def find_form_inputs(driver):
    """Find visible form inputs on the page."""
    inputs = driver.find_elements(By.CSS_SELECTOR,
        "input:not([type='hidden']), select, textarea")
    return [i for i in inputs if i.is_displayed()]


# ==============================================================================
# LOGIN
# ==============================================================================
def login_to_app(driver, url, email, password, label):
    safe_get(driver, url)
    time.sleep(4)

    cur = driver.current_url.lower()
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

    pass_el = None
    try:
        pass_el = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    except:
        print(f"    No password field")
        return False

    # React JS native setter + keyboard fallback
    try:
        driver.execute_script("""
            var emailEl = arguments[0], passEl = arguments[1];
            var email = arguments[2], pass_ = arguments[3];
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            emailEl.focus();
            setter.call(emailEl, '');
            emailEl.dispatchEvent(new Event('input', {bubbles:true}));
            setter.call(emailEl, email);
            emailEl.dispatchEvent(new Event('input', {bubbles:true}));
            emailEl.dispatchEvent(new Event('change', {bubbles:true}));
            emailEl.dispatchEvent(new Event('blur', {bubbles:true}));
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

    try:
        cur_val = email_el.get_attribute("value")
        if not cur_val or cur_val != email:
            print(f"    JS setter didn't stick, using send_keys")
            email_el.clear()
            email_el.send_keys(email)
            pass_el.clear()
            pass_el.send_keys(password)
            time.sleep(0.5)
    except: pass

    ss(driver, f"{label}_filled")

    btn = None
    for sel in [
        (By.XPATH, "//button[contains(text(),'Sign in')]"),
        (By.XPATH, "//button[contains(text(),'Sign In')]"),
        (By.XPATH, "//button[contains(text(),'Login')]"),
        (By.XPATH, "//button[contains(text(),'Log in')]"),
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

    src = driver.page_source.lower()
    if "invalid" in src or "incorrect" in src or "error" in src:
        print(f"    Login rejected (invalid credentials)")
    else:
        print(f"    Still on login page: {driver.current_url}")
    return False


def login_via_sso(driver, email, password, label):
    """Login to main EmpCloud, find SSO token for LMS, navigate."""
    print(f"    SSO via main app for testlms.empcloud.com...")

    if not login_to_app(driver, MAIN_URL + "/login", email, password, f"{label}_sso_main"):
        return False

    safe_get(driver, MAIN_URL)
    time.sleep(3)
    src = driver.page_source

    # Look for SSO URL in page source
    pattern = r'https?://testlms\.empcloud\.com[^"\'<>\s]*sso_token=[^"\'<>\s]*'
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
                if "testlms.empcloud.com" in href and "sso_token" in href:
                    safe_get(driver, href)
                    time.sleep(5)
                    if "login" not in driver.current_url.lower():
                        return True
                    break
            except: continue
        print(f"    No SSO URL found for testlms.empcloud.com in page source")

    print(f"    SSO via page source failed")
    return False


def wait_for_rate_limit():
    """Check rate limit and wait if needed."""
    try:
        r = requests.post(
            LMS_API + "/api/v1/auth/sso",
            json={"token": "check"},
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        if r.status_code == 429:
            reset = int(r.headers.get("x-ratelimit-reset", 0))
            remaining = int(r.headers.get("x-ratelimit-remaining", 0))
            if reset > 0:
                import time as _time
                now = int(_time.time())
                wait_secs = max(reset - now + 2, 0)
                if wait_secs > 0 and wait_secs < 120:
                    print(f"    Rate limited. Waiting {wait_secs}s for reset...")
                    time.sleep(wait_secs)
                    return True
                elif wait_secs >= 120:
                    print(f"    Rate limit resets in {wait_secs}s (too long, skipping)")
                    return False
        return True  # Not rate limited
    except:
        return True


def get_sso_token_from_main(email, password):
    """Login to main EmpCloud API and get SSO token for LMS."""
    try:
        for ep in ["/api/v1/auth/login", "/api/auth/login"]:
            try:
                r = requests.post(
                    MAIN_API + ep,
                    json={"email": email, "password": password},
                    timeout=10, headers={"Content-Type": "application/json"}
                )
                if r.status_code in (200, 201):
                    data = r.json()
                    # Handle nested data.tokens structure (camelCase and snake_case)
                    token = ""
                    if "data" in data and isinstance(data["data"], dict):
                        tokens = data["data"].get("tokens", {})
                        if isinstance(tokens, dict):
                            token = (tokens.get("accessToken", "") or
                                     tokens.get("access_token", "") or
                                     tokens.get("token", ""))
                        if not token:
                            token = (data["data"].get("accessToken", "") or
                                     data["data"].get("access_token", "") or
                                     data["data"].get("token", ""))
                    if not token:
                        token = (data.get("accessToken", "") or
                                 data.get("access_token", "") or
                                 data.get("token", ""))
                    if token:
                        print(f"    Got main API token ({len(token)} chars) from {ep}")
                        return token
            except: continue
    except: pass
    return None


def sso_token_exchange(driver, main_token, label):
    """Exchange main EmpCloud token with LMS via /auth/sso API, set in browser."""
    print(f"    Trying SSO token exchange via LMS API...")
    # Wait for rate limit if needed
    if not wait_for_rate_limit():
        print(f"    Rate limit too long, skipping SSO exchange")
        return False
    for attempt in range(2):
        if attempt > 0:
            if not wait_for_rate_limit():
                return False
        for ep in ["/api/v1/auth/sso"]:
            try:
                r = requests.post(
                    LMS_API + ep,
                    json={"token": main_token, "sso_token": main_token},
                    timeout=15,
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {main_token}"}
                )
                if r.status_code in (200, 201):
                    data = r.json()
                    print(f"    SSO exchange {ep} success! Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                    lms_token = ""
                    # Deep search for token in response (handles both camelCase and snake_case)
                    if isinstance(data, dict):
                        d = data.get("data", {})
                        if isinstance(d, dict):
                            tokens = d.get("tokens", {})
                            if isinstance(tokens, dict):
                                lms_token = (tokens.get("accessToken", "") or
                                             tokens.get("access_token", "") or
                                             tokens.get("token", ""))
                            if not lms_token:
                                lms_token = (d.get("accessToken", "") or
                                             d.get("access_token", "") or
                                             d.get("token", ""))
                        if not lms_token:
                            lms_token = (data.get("accessToken", "") or
                                         data.get("access_token", "") or
                                         data.get("token", ""))
                    if lms_token:
                        print(f"    Got LMS token from {ep} ({len(lms_token)} chars)")
                        return inject_token_to_browser(driver, lms_token)
                    else:
                        print(f"    SSO exchange {ep}: success but no token found in: {json.dumps(data)[:300]}")
                elif r.status_code == 429:
                    print(f"    SSO exchange {ep}: rate limited (attempt {attempt+1})")
                    break  # Go to next attempt with longer wait
                elif r.status_code == 400:
                    print(f"    SSO exchange {ep}: bad request - {r.text[:150]}")
                else:
                    print(f"    SSO exchange {ep}: {r.status_code} - {r.text[:100]}")
            except Exception as e:
                print(f"    SSO exchange {ep} error: {e}")
    return False


def inject_token_to_browser(driver, token, user_data=None):
    """Inject a JWT token into the LMS browser session.
    The LMS uses Zustand auth store with access_token + user in localStorage."""
    safe_get(driver, LMS_URL)
    time.sleep(2)

    # Build user JSON from JWT payload if not provided
    user_json = "{}"
    if user_data:
        user_json = json.dumps(user_data)
    else:
        # Try to decode JWT payload to extract user info
        try:
            import base64
            parts = token.split(".")
            if len(parts) >= 2:
                payload = parts[1]
                # Add padding
                payload += "=" * (4 - len(payload) % 4)
                decoded = json.loads(base64.urlsafe_b64decode(payload))
                user_json = json.dumps({
                    "empcloudUserId": decoded.get("empcloudUserId", decoded.get("sub", 0)),
                    "empcloudOrgId": decoded.get("empcloudOrgId", decoded.get("org_id", 0)),
                    "role": decoded.get("role", "employee"),
                    "email": decoded.get("email", ""),
                    "firstName": decoded.get("firstName", decoded.get("first_name", "")),
                    "lastName": decoded.get("lastName", decoded.get("last_name", "")),
                    "orgName": decoded.get("orgName", decoded.get("org_name", "")),
                })
                print(f"    Decoded JWT: role={decoded.get('role')}, email={decoded.get('email')}")
        except Exception as e:
            print(f"    JWT decode error: {e}")

    # Set localStorage items as the LMS auth store expects
    driver.execute_script("""
        localStorage.setItem('access_token', arguments[0]);
        localStorage.setItem('refresh_token', '');
        localStorage.setItem('user', arguments[1]);
    """, token, user_json)

    safe_get(driver, LMS_URL + "/dashboard")
    time.sleep(3)
    if "login" not in driver.current_url.lower():
        print(f"    Token injection success -> {driver.current_url}")
        return True
    # Try a page reload
    driver.refresh()
    time.sleep(3)
    if "login" not in driver.current_url.lower():
        print(f"    Token injection success after refresh -> {driver.current_url}")
        return True
    print(f"    Token injection failed, still at: {driver.current_url}")
    return False


prefetched_tokens = {"admin": None, "employee": None}

def full_login(driver, email, password, label):
    """Try: pre-fetched token -> SSO -> SSO exchange -> direct login."""
    global prefetched_tokens

    # Strategy 0: Use pre-fetched LMS token if available
    role_key = "admin" if email == ADMIN_EMAIL else "employee"
    pf_token = prefetched_tokens.get(role_key)
    pf_user = prefetched_tokens.get(f"{role_key}_user")
    if pf_token:
        print(f"  [0] Using pre-fetched LMS token ({len(pf_token)} chars)")
        if inject_token_to_browser(driver, pf_token, user_data=pf_user):
            return True
        print(f"    Pre-fetched token injection failed")

    # Strategy 1: SSO via main app page scraping (works reliably when not rate limited)
    print(f"  [1] SSO via main app page")
    if login_via_sso(driver, email, password, label):
        return True

    # Strategy 2: Get main API token and exchange with LMS SSO
    print(f"  [2] SSO token exchange via API")
    main_token = get_sso_token_from_main(email, password)
    if main_token:
        # Try SSO exchange (with rate limit retries)
        if sso_token_exchange(driver, main_token, label):
            return True

        # Try injecting the main token directly into browser
        print(f"    Trying main token directly in browser...")
        if inject_token_to_browser(driver, main_token):
            return True

        # Try SSO URL pattern with main token
        print(f"    Trying SSO URL with main token...")
        safe_get(driver, f"{LMS_URL}?sso_token={main_token}")
        time.sleep(5)
        if "login" not in driver.current_url.lower():
            print(f"    SSO URL with main token success -> {driver.current_url}")
            return True

    # Strategy 3: Direct login at LMS URL (LMS has its own login form)
    print(f"  [3] Direct login to {LMS_URL}")
    if login_to_app(driver, LMS_URL + "/login", email, password, f"{label}_direct"):
        return True

    return False


# ==============================================================================
# LMS ADMIN TESTS
# ==============================================================================
def test_lms_admin(driver):
    print("\n" + "=" * 70)
    print("LMS MODULE - ORG ADMIN (ananya@technova.in)")
    print("=" * 70)

    # ------ Login ------
    print("\n[Test] Admin Login via SSO")
    ok = full_login(driver, ADMIN_EMAIL, ADMIN_PASS, "lms_admin")
    if ok:
        log("LMS", "Admin Login", "PASS", f"Logged in at {driver.current_url}")
    else:
        snap = ss(driver, "lms_admin_login_fail")
        log("LMS", "Admin Login", "FAIL",
            f"Cannot login to LMS. URL: {driver.current_url}",
            severity="Critical", snap=snap)
        return

    # ------ Dashboard ------
    print("\n[Test] Admin Dashboard")
    navigate_to_page(driver, "/dashboard")
    snap = ss(driver, "lms_admin_dashboard")
    err = check_page_error(driver)
    if err:
        log("LMS", "Admin Dashboard", "FAIL", f"Page error: {err}",
            severity="Critical", snap=snap)
    else:
        src = driver.page_source.lower()
        metrics = [m for m in [
            "total courses", "active learners", "completion rate", "enrollment",
            "course", "learner", "progress", "overview", "dashboard",
            "certificates", "compliance"
        ] if m in src]
        log("LMS", "Admin Dashboard", "PASS" if len(metrics) >= 2 else "WARN",
            f"Title: {driver.title}. Metrics found: {metrics[:8]}")

    # ------ Navigation check ------
    print("\n[Test] Admin Navigation/Sidebar")
    nav = get_nav_texts(driver)
    print(f"    Sidebar items: {nav[:20]}")
    expected_nav = ["Dashboard", "Course Catalog", "Learning Paths", "Certifications",
                    "Compliance", "Analytics", "Settings"]
    found_nav = [s for s in expected_nav if any(s.lower() in n.lower() for n in nav)]
    missing_nav = [s for s in expected_nav if s not in found_nav]
    if len(found_nav) >= 5:
        log("LMS", "Admin Navigation", "PASS",
            f"Found {len(found_nav)}/{len(expected_nav)}: {found_nav}")
    elif len(found_nav) >= 3:
        log("LMS", "Admin Navigation", "WARN",
            f"Found {len(found_nav)}/{len(expected_nav)}: {found_nav}. Missing: {missing_nav}")
    else:
        snap = ss(driver, "lms_admin_nav_missing")
        log("LMS", "Admin Navigation", "FAIL",
            f"Only {len(found_nav)}/{len(expected_nav)} nav items found: {found_nav}. Missing: {missing_nav}",
            severity="Medium", snap=snap)

    # ------ Courses List ------
    print("\n[Test] Courses Page")
    navigate_to_page(driver, "/courses")
    time.sleep(2)
    snap = ss(driver, "lms_admin_courses")
    err = check_page_error(driver)
    if err:
        log("LMS", "Courses Page", "FAIL", f"Error: {err}", severity="High", snap=snap)
    else:
        src = driver.page_source.lower()
        has_courses = any(k in src for k in ["course", "training", "module", "lesson"])
        rows = count_table_rows(driver)
        # Check for search/filter
        search = driver.find_elements(By.CSS_SELECTOR,
            "input[type='search'], input[placeholder*='search' i], input[placeholder*='filter' i]")
        log("LMS", "Courses Page", "PASS" if has_courses else "WARN",
            f"At {driver.current_url}. Course content: {has_courses}. Rows: {rows}. Search: {len(search) > 0}")

    # ------ Create Course ------
    print("\n[Test] Create Course")
    src = driver.page_source.lower()
    # Check if page shows "Coming soon" or similar placeholder
    if "coming soon" in src:
        log("LMS", "Create Course", "WARN",
            "Course Catalog page shows 'Coming soon' - feature not yet implemented")
        # Skip further create course testing since the page is not built yet
        btn = None
    else:
        # Look for create button on course catalog page
        print(f"    Checking for create/add buttons...")
        btn = None
        for text in ["Create Course", "Add Course", "New Course", "Create New", "Create", "Add New"]:
            btn = find_button_by_text(driver, text)
            if btn:
                break
        # Also look for icon buttons or links to course creation
        if not btn:
            for sel in [
                "a[href*='create']", "a[href*='new']",
                "button[aria-label*='create' i]", "button[aria-label*='add' i]",
                "[data-testid*='create']", "[data-testid*='add']",
                ".create-btn", ".add-btn",
            ]:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, sel)
                    for el in els:
                        if el.is_displayed():
                            btn = el
                            break
                except: continue
                if btn:
                    break

    if btn:
        print(f"    Clicking: '{btn.text.strip()}'")
        safe_click(driver, btn)
        time.sleep(3)
        snap = ss(driver, "lms_create_course_form")

        inputs = find_form_inputs(driver)
        print(f"    Found {len(inputs)} visible form inputs")

        if inputs:
            # Fill course name
            text_inputs = [i for i in inputs
                           if i.get_attribute("type") in ("text", None, "")
                           or i.tag_name == "input"]
            if text_inputs:
                ts = datetime.now().strftime("%H%M%S")
                name = f"E2E Test Course {ts}"
                try:
                    text_inputs[0].click()
                    text_inputs[0].send_keys(Keys.CONTROL, "a")
                    text_inputs[0].send_keys(name)
                    time.sleep(0.5)
                except: pass
                ss(driver, "lms_course_name_filled")

            # Fill description if textarea present
            textareas = [i for i in inputs if i.tag_name == "textarea"]
            if textareas:
                try:
                    textareas[0].click()
                    textareas[0].send_keys("E2E automated test course description")
                except: pass

            # Try to save
            save_btn = (find_button_by_text(driver, "Save") or
                        find_button_by_text(driver, "Create") or
                        find_button_by_text(driver, "Submit") or
                        find_button_by_text(driver, "Next"))
            if save_btn:
                print(f"    Clicking save: '{save_btn.text.strip()}'")
                safe_click(driver, save_btn)
                time.sleep(3)
                snap = ss(driver, "lms_course_saved")
                post_src = driver.page_source.lower()
                if any(k in post_src for k in ["success", "created", "saved", "course detail"]):
                    log("LMS", "Create Course", "PASS",
                        f"Course creation form submitted. At {driver.current_url}")
                elif check_page_error(driver):
                    log("LMS", "Create Course", "FAIL",
                        f"Error after save: {check_page_error(driver)}",
                        severity="High", snap=snap)
                else:
                    # Could be validation error or redirect
                    log("LMS", "Create Course", "WARN",
                        f"Form submitted, result unclear. At {driver.current_url}")
            else:
                log("LMS", "Create Course", "WARN",
                    f"Form opened with {len(inputs)} inputs but no Save button found")
        else:
            log("LMS", "Create Course", "WARN",
                f"Create clicked but no form inputs visible. URL: {driver.current_url}")
    else:
        snap = ss(driver, "lms_no_create_course_btn")
        log("LMS", "Create Course", "FAIL",
            "No Create Course button found on courses page",
            severity="Medium", snap=snap)

    # ------ Learning Paths ------
    print("\n[Test] Learning Paths")
    navigate_to_page(driver, "/learning-paths")
    time.sleep(2)
    snap = ss(driver, "lms_admin_learning_paths")
    err = check_page_error(driver)
    if err:
        log("LMS", "Learning Paths", "FAIL", f"Error: {err}",
            severity="High", snap=snap)
    else:
        src = driver.page_source.lower()
        has_content = any(k in src for k in ["learning path", "path", "sequence", "curriculum"])
        rows = count_table_rows(driver)
        create_btn = (find_button_by_text(driver, "Create Path") or
                      find_button_by_text(driver, "Create Learning Path") or
                      find_button_by_text(driver, "Add Path") or
                      find_button_by_text(driver, "Create"))
        log("LMS", "Learning Paths", "PASS" if has_content else "WARN",
            f"At {driver.current_url}. Content: {has_content}. Rows: {rows}. Create btn: {create_btn is not None}")

    # ------ Certifications ------
    print("\n[Test] Certifications (Admin)")
    navigate_to_page(driver, "/certifications")
    time.sleep(2)
    snap = ss(driver, "lms_admin_certifications")
    err = check_page_error(driver)
    if err:
        log("LMS", "Certifications (Admin)", "FAIL", f"Error: {err}",
            severity="High", snap=snap)
    else:
        src = driver.page_source.lower()
        has_certs = any(k in src for k in ["certificate", "template", "issued", "verify"])
        log("LMS", "Certifications (Admin)", "PASS" if has_certs else "WARN",
            f"At {driver.current_url}. Cert content: {has_certs}")

    # ------ Compliance Training ------
    print("\n[Test] Compliance Training")
    navigate_to_page(driver, "/compliance")
    time.sleep(2)
    snap = ss(driver, "lms_admin_compliance")
    err = check_page_error(driver)
    if err:
        log("LMS", "Compliance Training", "FAIL", f"Error: {err}",
            severity="High", snap=snap)
    else:
        src = driver.page_source.lower()
        has_compliance = any(k in src for k in [
            "compliance", "mandatory", "overdue", "assigned", "training",
            "due date", "completion"
        ])
        rows = count_table_rows(driver)
        log("LMS", "Compliance Training", "PASS" if has_compliance else "WARN",
            f"At {driver.current_url}. Compliance content: {has_compliance}. Rows: {rows}")

    # ------ Analytics ------
    print("\n[Test] Analytics")
    navigate_to_page(driver, "/analytics")
    time.sleep(2)
    snap = ss(driver, "lms_admin_analytics")
    err = check_page_error(driver)
    if err:
        log("LMS", "Analytics", "FAIL", f"Error: {err}",
            severity="High", snap=snap)
    else:
        src = driver.page_source.lower()
        has_analytics = any(k in src for k in [
            "analytics", "overview", "completion", "enrollment", "trend",
            "chart", "report", "export", "csv"
        ])
        # Check for charts (Recharts renders SVG)
        charts = driver.find_elements(By.CSS_SELECTOR, "svg.recharts-surface, .recharts-wrapper, canvas")
        log("LMS", "Analytics", "PASS" if has_analytics else "WARN",
            f"At {driver.current_url}. Analytics content: {has_analytics}. Charts: {len(charts)}")

    # ------ ILT Sessions ------
    print("\n[Test] ILT Sessions")
    navigate_to_page(driver, "/ilt")
    time.sleep(2)
    snap = ss(driver, "lms_admin_ilt")
    err = check_page_error(driver)
    if err:
        log("LMS", "ILT Sessions", "FAIL", f"Error: {err}",
            severity="Medium", snap=snap)
    else:
        src = driver.page_source.lower()
        has_ilt = any(k in src for k in [
            "instructor", "session", "training", "virtual", "in-person",
            "ilt", "schedule", "registration"
        ])
        log("LMS", "ILT Sessions", "PASS" if has_ilt else "WARN",
            f"At {driver.current_url}. ILT content: {has_ilt}")

    # ------ Leaderboard / Gamification ------
    print("\n[Test] Leaderboard / Gamification")
    navigate_to_page(driver, "/leaderboard")
    time.sleep(2)
    snap = ss(driver, "lms_admin_leaderboard")
    err = check_page_error(driver)
    if err:
        log("LMS", "Leaderboard", "FAIL", f"Error: {err}",
            severity="Medium", snap=snap)
    else:
        src = driver.page_source.lower()
        has_lb = any(k in src for k in [
            "leaderboard", "points", "badge", "rank", "gamification"
        ])
        log("LMS", "Leaderboard", "PASS" if has_lb else "WARN",
            f"At {driver.current_url}. Leaderboard content: {has_lb}")

    # ------ Settings ------
    print("\n[Test] Settings")
    navigate_to_page(driver, "/settings")
    time.sleep(2)
    snap = ss(driver, "lms_admin_settings")
    err = check_page_error(driver)
    if err:
        log("LMS", "Settings", "FAIL", f"Error: {err}",
            severity="Medium", snap=snap)
    else:
        src = driver.page_source.lower()
        has_settings = any(k in src for k in [
            "settings", "configuration", "category", "template", "general",
            "notification", "preference"
        ])
        inputs = find_form_inputs(driver)
        log("LMS", "Settings", "PASS" if has_settings else "WARN",
            f"At {driver.current_url}. Settings content: {has_settings}. Form inputs: {len(inputs)}")

    # ------ SCORM (may be embedded in course detail, not a standalone page) ------
    print("\n[Test] SCORM Support")
    # Check if SCORM is mentioned anywhere on the courses page
    navigate_to_page(driver, "/courses")
    time.sleep(2)
    src = driver.page_source.lower()
    has_scorm_ref = any(k in src for k in ["scorm", "xapi", "package"])
    if has_scorm_ref:
        log("LMS", "SCORM Support", "PASS",
            f"SCORM references found on courses page")
    else:
        # SCORM might not have a dedicated frontend page (per sidebar - not listed)
        log("LMS", "SCORM Support", "WARN",
            "SCORM not visible on courses page. May be API-only or in course builder.")

    # ------ Marketplace ------
    print("\n[Test] Content Marketplace")
    navigate_to_page(driver, "/marketplace")
    time.sleep(2)
    snap = ss(driver, "lms_admin_marketplace")
    err = check_page_error(driver)
    if err:
        log("LMS", "Content Marketplace", "FAIL", f"Error: {err}",
            severity="Medium", snap=snap)
    else:
        src = driver.page_source.lower()
        has_market = any(k in src for k in ["marketplace", "content", "library", "browse", "import"])
        log("LMS", "Content Marketplace", "PASS" if has_market else "WARN",
            f"At {driver.current_url}. Marketplace content: {has_market}")

    # ------ Quizzes (admin view) ------
    print("\n[Test] Quizzes (Admin)")
    # Navigate via sidebar first (URL might differ from /quizzes)
    navigate_to_page(driver, "/dashboard")
    time.sleep(1)
    clicked = click_sidebar_link(driver, "Quizzes")
    if not clicked:
        navigate_to_page(driver, "/quizzes")
    time.sleep(2)
    snap = ss(driver, "lms_admin_quizzes")
    err = check_page_error(driver)
    if err:
        log("LMS", "Quizzes (Admin)", "FAIL", f"Error on quizzes page: {err}. URL: {driver.current_url}",
            severity="Medium", snap=snap)
    else:
        src = driver.page_source.lower()
        has_quizzes = any(k in src for k in [
            "quiz", "question", "attempt", "assessment", "test"
        ])
        log("LMS", "Quizzes (Admin)", "PASS" if has_quizzes else "WARN",
            f"At {driver.current_url}. Quiz content: {has_quizzes}")

    # ------ API Health Check ------
    print("\n[Test] LMS API Health")
    try:
        r = requests.get(LMS_API + "/health", timeout=10)
        if r.status_code == 200:
            log("LMS", "API Health Check", "PASS", f"Status {r.status_code}: {r.text[:150]}")
        else:
            log("LMS", "API Health Check", "WARN", f"Status {r.status_code}: {r.text[:150]}")
    except Exception as e:
        log("LMS", "API Health Check", "FAIL", f"Health endpoint error: {e}",
            severity="High")


# ==============================================================================
# LMS EMPLOYEE TESTS
# ==============================================================================
def test_lms_employee(driver):
    print("\n" + "=" * 70)
    print("LMS MODULE - EMPLOYEE (priya@technova.in)")
    print("=" * 70)

    # ------ Login ------
    print("\n[Test] Employee Login via SSO")
    ok = full_login(driver, EMP_EMAIL, EMP_PASS, "lms_emp")
    if ok:
        log("LMS-Emp", "Employee Login", "PASS", f"Logged in at {driver.current_url}")
    else:
        snap = ss(driver, "lms_emp_login_fail")
        log("LMS-Emp", "Employee Login", "FAIL",
            f"Cannot login to LMS. URL: {driver.current_url}",
            severity="Critical", snap=snap)
        return

    # ------ Dashboard / My Learning ------
    print("\n[Test] Employee Dashboard / My Learning")
    navigate_to_page(driver, "/dashboard")
    time.sleep(2)
    snap = ss(driver, "lms_emp_dashboard")
    err = check_page_error(driver)
    if err:
        log("LMS-Emp", "Employee Dashboard", "FAIL", f"Error: {err}",
            severity="Critical", snap=snap)
    else:
        src = driver.page_source.lower()
        metrics = [m for m in [
            "my learning", "enrolled", "in progress", "completed", "course",
            "progress", "continue", "dashboard", "upcoming", "deadline"
        ] if m in src]
        log("LMS-Emp", "Employee Dashboard", "PASS" if len(metrics) >= 2 else "WARN",
            f"Title: {driver.title}. Content: {metrics[:8]}")

    # ------ Employee Nav check ------
    print("\n[Test] Employee Navigation")
    nav = get_nav_texts(driver)
    print(f"    Sidebar items: {nav[:20]}")
    expected_emp_nav = ["Dashboard", "Courses", "Learning Paths", "Certifications",
                        "Compliance", "Leaderboard"]
    found_emp_nav = [s for s in expected_emp_nav if any(s.lower() in n.lower() for n in nav)]

    # Check admin-only items are NOT visible (RBAC)
    admin_only = ["Settings", "Analytics"]
    admin_visible = [s for s in admin_only if any(s.lower() in n.lower() for n in nav)]

    rbac_ok = len(admin_visible) == 0
    log("LMS-Emp", "Employee Navigation", "PASS" if len(found_emp_nav) >= 3 else "WARN",
        f"Found {len(found_emp_nav)}/{len(expected_emp_nav)}: {found_emp_nav}")

    if admin_visible:
        snap = ss(driver, "lms_emp_rbac_leak")
        log("LMS-Emp", "RBAC - Admin Items Visible to Employee", "FAIL",
            f"Admin-only items visible to employee: {admin_visible}",
            severity="High", snap=snap)
    else:
        log("LMS-Emp", "RBAC - Admin Items Hidden", "PASS",
            "Admin-only items (Settings, Analytics) not visible to employee")

    # ------ Courses / My Courses ------
    print("\n[Test] Employee Courses / Course Catalog")
    navigate_to_page(driver, "/courses")
    time.sleep(2)
    snap = ss(driver, "lms_emp_courses")
    err = check_page_error(driver)
    if err:
        log("LMS-Emp", "Courses Catalog", "FAIL", f"Error: {err}",
            severity="High", snap=snap)
    else:
        src = driver.page_source.lower()
        has_courses = any(k in src for k in ["course", "enroll", "start", "continue", "catalog"])
        # Employee should NOT see admin buttons
        create_btn = find_button_by_text(driver, "Create Course")
        if create_btn:
            snap = ss(driver, "lms_emp_create_course_visible")
            log("LMS-Emp", "RBAC - Create Course Button", "FAIL",
                "Employee can see Create Course button (admin-only)",
                severity="High", snap=snap)
        else:
            log("LMS-Emp", "RBAC - Create Course Button", "PASS",
                "Create Course button not visible to employee")
        log("LMS-Emp", "Courses Catalog", "PASS" if has_courses else "WARN",
            f"At {driver.current_url}. Course content: {has_courses}")

    # ------ Assigned / Enrolled Courses ------
    print("\n[Test] My Enrollments")
    # Try navigating to enrollment-related URLs
    for path in ["/enrollments/my", "/my-learning", "/dashboard"]:
        navigate_to_page(driver, path)
        time.sleep(2)
        src = driver.page_source.lower()
        if any(k in src for k in ["enrolled", "in progress", "my learning", "continue"]):
            break

    snap = ss(driver, "lms_emp_enrollments")
    err = check_page_error(driver)
    if err:
        log("LMS-Emp", "My Enrollments", "FAIL", f"Error: {err}",
            severity="High", snap=snap)
    else:
        src = driver.page_source.lower()
        has_enrollments = any(k in src for k in [
            "enrolled", "in progress", "completed", "my learning", "continue learning"
        ])
        log("LMS-Emp", "My Enrollments", "PASS" if has_enrollments else "WARN",
            f"At {driver.current_url}. Enrollment content: {has_enrollments}")

    # ------ Try Accessing a Course Detail ------
    print("\n[Test] Course Detail Page")
    navigate_to_page(driver, "/courses")
    time.sleep(2)
    # Click on first course link
    course_clicked = False
    for sel in [
        "a[href*='/courses/']",
        ".course-card a", ".course-item a",
        "table tbody tr a", "[role='row'] a",
    ]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                href = el.get_attribute("href") or ""
                if "/courses/" in href and el.is_displayed():
                    safe_get(driver, href)
                    time.sleep(3)
                    course_clicked = True
                    break
        except: continue
        if course_clicked:
            break

    if not course_clicked:
        # Try clicking any card/item
        for xpath in [
            "//div[contains(@class,'course')]//a",
            "//a[contains(@href,'course')]",
        ]:
            try:
                els = driver.find_elements(By.XPATH, xpath)
                for el in els:
                    if el.is_displayed():
                        href = el.get_attribute("href") or ""
                        if href and "course" in href.lower():
                            safe_get(driver, href)
                            time.sleep(3)
                            course_clicked = True
                            break
            except: continue
            if course_clicked:
                break

    if course_clicked:
        snap = ss(driver, "lms_emp_course_detail")
        err = check_page_error(driver)
        if err:
            log("LMS-Emp", "Course Detail", "FAIL", f"Error: {err}",
                severity="High", snap=snap)
        else:
            src = driver.page_source.lower()
            has_detail = any(k in src for k in [
                "module", "lesson", "enroll", "start", "progress",
                "description", "instructor", "content", "quiz"
            ])
            log("LMS-Emp", "Course Detail", "PASS" if has_detail else "WARN",
                f"At {driver.current_url}. Detail content: {has_detail}")
    else:
        log("LMS-Emp", "Course Detail", "SKIP",
            "No course link found to click")

    # ------ Quizzes ------
    print("\n[Test] Quizzes / Take Quiz")
    navigate_to_page(driver, "/quizzes")
    time.sleep(2)
    snap = ss(driver, "lms_emp_quizzes")
    err = check_page_error(driver)
    if err:
        log("LMS-Emp", "Quizzes Page", "FAIL", f"Error: {err}",
            severity="Medium", snap=snap)
    else:
        src = driver.page_source.lower()
        has_quizzes = any(k in src for k in [
            "quiz", "attempt", "take quiz", "start quiz", "assessment", "question"
        ])
        log("LMS-Emp", "Quizzes Page", "PASS" if has_quizzes else "WARN",
            f"At {driver.current_url}. Quiz content: {has_quizzes}")

        # Try to start a quiz
        start_btn = (find_button_by_text(driver, "Start Quiz") or
                     find_button_by_text(driver, "Take Quiz") or
                     find_button_by_text(driver, "Begin") or
                     find_button_by_text(driver, "Start"))
        if start_btn:
            safe_click(driver, start_btn)
            time.sleep(3)
            snap = ss(driver, "lms_emp_quiz_started")
            quiz_src = driver.page_source.lower()
            has_questions = any(k in quiz_src for k in [
                "question", "choice", "select", "answer", "true", "false",
                "submit", "next", "multiple"
            ])
            log("LMS-Emp", "Take Quiz", "PASS" if has_questions else "WARN",
                f"Quiz started. Question content visible: {has_questions}")
        else:
            log("LMS-Emp", "Take Quiz", "SKIP", "No Start Quiz button found")

    # ------ Certifications (Employee) ------
    print("\n[Test] My Certifications")
    navigate_to_page(driver, "/certifications")
    time.sleep(2)
    snap = ss(driver, "lms_emp_certifications")
    err = check_page_error(driver)
    if err:
        log("LMS-Emp", "My Certifications", "FAIL", f"Error: {err}",
            severity="Medium", snap=snap)
    else:
        src = driver.page_source.lower()
        has_certs = any(k in src for k in [
            "certificate", "download", "verify", "issued", "earned",
            "no certificate", "not earned"
        ])
        log("LMS-Emp", "My Certifications", "PASS" if has_certs else "WARN",
            f"At {driver.current_url}. Cert content: {has_certs}")

    # ------ Compliance (Employee) ------
    print("\n[Test] My Compliance")
    navigate_to_page(driver, "/compliance")
    time.sleep(2)
    snap = ss(driver, "lms_emp_compliance")
    err = check_page_error(driver)
    if err:
        log("LMS-Emp", "My Compliance", "FAIL", f"Error: {err}",
            severity="Medium", snap=snap)
    else:
        src = driver.page_source.lower()
        has_compliance = any(k in src for k in [
            "compliance", "mandatory", "due", "assigned", "training", "complete"
        ])
        log("LMS-Emp", "My Compliance", "PASS" if has_compliance else "WARN",
            f"At {driver.current_url}. Compliance content: {has_compliance}")

    # ------ Learning Paths (Employee) ------
    print("\n[Test] Learning Paths (Employee)")
    navigate_to_page(driver, "/learning-paths")
    time.sleep(2)
    snap = ss(driver, "lms_emp_learning_paths")
    err = check_page_error(driver)
    if err:
        log("LMS-Emp", "Learning Paths (Employee)", "FAIL", f"Error: {err}",
            severity="Medium", snap=snap)
    else:
        src = driver.page_source.lower()
        has_paths = any(k in src for k in ["learning path", "path", "enroll", "sequence"])
        log("LMS-Emp", "Learning Paths (Employee)", "PASS" if has_paths else "WARN",
            f"At {driver.current_url}. Path content: {has_paths}")

    # ------ Leaderboard (Employee) ------
    print("\n[Test] Leaderboard (Employee)")
    navigate_to_page(driver, "/leaderboard")
    time.sleep(2)
    snap = ss(driver, "lms_emp_leaderboard")
    err = check_page_error(driver)
    if err:
        log("LMS-Emp", "Leaderboard (Employee)", "FAIL", f"Error: {err}",
            severity="Low", snap=snap)
    else:
        src = driver.page_source.lower()
        has_lb = any(k in src for k in ["leaderboard", "points", "badge", "rank"])
        log("LMS-Emp", "Leaderboard (Employee)", "PASS" if has_lb else "WARN",
            f"At {driver.current_url}. Leaderboard content: {has_lb}")

    # ------ RBAC: Admin-only pages should block employee ------
    print("\n[Test] RBAC - Admin Pages Blocked")
    admin_pages = [
        ("/settings", "Settings"),
        ("/analytics", "Analytics"),
    ]
    for path, name in admin_pages:
        navigate_to_page(driver, path)
        time.sleep(2)
        src = driver.page_source.lower()
        url = driver.current_url.lower()
        # Should redirect to dashboard or show unauthorized
        blocked = ("unauthorized" in src or "forbidden" in src or "access denied" in src
                   or "not authorized" in src or "permission" in src
                   or "login" in url or "dashboard" in url)
        # Also check if it just shows the admin content (which would be a bug)
        has_admin_content = any(k in src for k in ["settings", "configuration", "analytics overview"])

        if blocked:
            log("LMS-Emp", f"RBAC - {name} Blocked", "PASS",
                f"Employee correctly blocked from {name}")
        elif has_admin_content:
            snap = ss(driver, f"lms_emp_rbac_{name.lower()}")
            log("LMS-Emp", f"RBAC - {name} Accessible", "FAIL",
                f"Employee can access admin-only {name} page",
                severity="High", snap=snap)
        else:
            log("LMS-Emp", f"RBAC - {name} Check", "WARN",
                f"Cannot determine if {name} is properly blocked. URL: {driver.current_url}")


# ==============================================================================
# LMS API TESTS
# ==============================================================================
def test_lms_api(driver):
    """Test key LMS API endpoints directly."""
    print("\n" + "=" * 70)
    print("LMS MODULE - API ENDPOINT TESTS")
    print("=" * 70)

    # Get auth token - try pre-fetched first, then main EmpCloud API
    token = prefetched_tokens.get("admin")
    if token:
        print(f"    Using pre-fetched admin LMS token ({len(token)} chars)")
        log("LMS-API", "Auth Token", "PASS", f"Using pre-fetched LMS token ({len(token)} chars)")

    # Method 1: Get main token and use for SSO exchange with LMS
    main_token = get_sso_token_from_main(ADMIN_EMAIL, ADMIN_PASS) if not token else None
    if main_token:
        print(f"    Got main EmpCloud token, trying SSO exchange...")
        wait_for_rate_limit()
        for ep in ["/api/v1/auth/sso"]:
            try:
                r = requests.post(
                    LMS_API + ep,
                    json={"token": main_token, "sso_token": main_token},
                    timeout=10,
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {main_token}"}
                )
                if r.status_code in (200, 201):
                    data = r.json()
                    if "data" in data and isinstance(data["data"], dict):
                        tokens = data["data"].get("tokens", {})
                        if isinstance(tokens, dict):
                            token = (tokens.get("accessToken", "") or
                                     tokens.get("access_token", "") or
                                     tokens.get("token", ""))
                        if not token:
                            token = (data["data"].get("accessToken", "") or
                                     data["data"].get("access_token", "") or
                                     data["data"].get("token", ""))
                    if not token:
                        token = (data.get("accessToken", "") or
                                 data.get("access_token", "") or
                                 data.get("token", ""))
                    if token:
                        print(f"    Got LMS token via SSO exchange ({len(token)} chars)")
                        break
                elif r.status_code == 429:
                    print(f"    LMS API rate limited, using main token directly...")
                    token = main_token  # Use main token as fallback
                    break
                else:
                    print(f"    SSO exchange {ep}: {r.status_code}")
            except Exception as e:
                print(f"    SSO exchange error: {e}")

        if not token:
            token = main_token  # Use main token directly as fallback
            print(f"    Using main EmpCloud token as fallback for API tests")

    # Method 2: Direct LMS login
    if not token:
        time.sleep(5)
        for endpoint in ["/api/v1/auth/login", "/api/auth/login"]:
            try:
                r = requests.post(
                    LMS_API + endpoint,
                    json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
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
                        break
                elif r.status_code == 429:
                    print(f"    Rate limited on {endpoint}")
                    time.sleep(5)
            except: continue

    if not token:
        log("LMS-API", "Auth Token", "FAIL",
            "Cannot obtain API token for endpoint testing",
            severity="Critical")
        return

    log("LMS-API", "Auth Token", "PASS", f"Obtained API auth token ({len(token)} chars)")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Test various endpoints
    api_tests = [
        ("GET", "/api/v1/courses", "Courses List"),
        ("GET", "/api/v1/learning-paths", "Learning Paths List"),
        ("GET", "/api/v1/compliance/dashboard", "Compliance Dashboard"),
        ("GET", "/api/v1/analytics/overview", "Analytics Overview"),
        ("GET", "/api/v1/gamification/leaderboard", "Leaderboard"),
        ("GET", "/api/v1/notifications", "Notifications"),
        ("GET", "/api/v1/certificates/my", "My Certificates"),
        ("GET", "/api/v1/enrollments/my", "My Enrollments"),
        ("GET", "/api/v1/ilt", "ILT Sessions"),
        ("GET", "/api/v1/marketplace", "Marketplace"),
    ]

    for idx, (method, path, name) in enumerate(api_tests):
        if idx > 0:
            time.sleep(2)  # Avoid rate limiting
        print(f"\n[Test] API: {name}")
        try:
            url = LMS_API + path
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=10)
            else:
                r = requests.post(url, headers=headers, timeout=10)

            if r.status_code in (200, 201):
                try:
                    data = r.json()
                    count = ""
                    if isinstance(data, list):
                        count = f" ({len(data)} items)"
                    elif isinstance(data, dict):
                        for k in ["data", "results", "items"]:
                            if k in data and isinstance(data[k], list):
                                count = f" ({len(data[k])} items)"
                                break
                    log("LMS-API", name, "PASS", f"Status {r.status_code}{count}")
                except:
                    log("LMS-API", name, "PASS", f"Status {r.status_code}")
            elif r.status_code in (401, 403):
                log("LMS-API", name, "WARN", f"Status {r.status_code} - auth issue")
            elif r.status_code == 404:
                log("LMS-API", name, "WARN", f"Status {r.status_code} - endpoint not found")
            else:
                log("LMS-API", name, "FAIL",
                    f"Status {r.status_code}: {r.text[:150]}",
                    severity="Medium")
        except Exception as e:
            log("LMS-API", name, "FAIL", f"Request error: {e}",
                severity="Medium")


# ==============================================================================
# GITHUB ISSUE FILING
# ==============================================================================
def file_github_issues():
    if not bugs_found:
        print("\nNo bugs to file.")
        return

    print(f"\n{'=' * 70}")
    print(f"FILING {len(bugs_found)} GITHUB ISSUES")
    print("=" * 70)

    for bug in bugs_found:
        title = f"[{bug['severity']}][LMS] {bug['test']}"
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
1. Navigate to the LMS module ({LMS_URL})
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
- Module: EMP LMS (testlms.empcloud.com)
"""
        labels = ["bug", "automated-test", "emp-lms"]
        if bug["severity"] == "Critical":
            labels.append("priority:critical")
        elif bug["severity"] == "High":
            labels.append("priority:high")

        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        gh_headers = {"Authorization": f"token {GITHUB_PAT}",
                      "Accept": "application/vnd.github.v3+json"}
        try:
            r = requests.post(url, headers=gh_headers,
                              json={"title": title, "body": body, "labels": labels},
                              timeout=15)
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
    print("=" * 70)
    print("EMP CLOUD - LMS MODULE FRESH E2E TEST SUITE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"LMS URL: {LMS_URL}")
    print(f"LMS API: {LMS_API}")
    print("=" * 70)

    # Pre-fetch employee and admin LMS tokens before rate limits kick in
    print("\n[Pre-fetch] Getting LMS tokens via SSO exchange...")

    def prefetch_lms_token(email, password, role_label):
        """Get main token then exchange for LMS token."""
        main_token = get_sso_token_from_main(email, password)
        if not main_token:
            print(f"  Cannot get main token for {role_label}")
            return None, None
        print(f"  Got {role_label} main token ({len(main_token)} chars)")
        time.sleep(1)
        try:
            r = requests.post(
                LMS_API + "/api/v1/auth/sso",
                json={"token": main_token, "sso_token": main_token},
                timeout=15,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {main_token}"}
            )
            if r.status_code in (200, 201):
                data = r.json()
                d = data.get("data", {})
                if isinstance(d, dict):
                    user = d.get("user", {})
                    tokens = d.get("tokens", {})
                    lms_token = (tokens.get("accessToken", "") or
                                 tokens.get("access_token", "") or
                                 tokens.get("token", ""))
                    if lms_token:
                        print(f"  Got {role_label} LMS token ({len(lms_token)} chars)")
                        return lms_token, user
                    print(f"  SSO succeeded but no token: {json.dumps(data)[:200]}")
            elif r.status_code == 429:
                print(f"  Rate limited on {role_label} SSO exchange")
            else:
                print(f"  {role_label} SSO exchange: {r.status_code}")
        except Exception as e:
            print(f"  {role_label} SSO exchange error: {e}")
        return None, None

    emp_lms_token, emp_user = prefetch_lms_token(EMP_EMAIL, EMP_PASS, "employee")
    admin_lms_token, admin_user = prefetch_lms_token(ADMIN_EMAIL, ADMIN_PASS, "admin")

    # Store pre-fetched tokens and user data globally
    prefetched_tokens["admin"] = admin_lms_token
    prefetched_tokens["employee"] = emp_lms_token
    prefetched_tokens["admin_user"] = admin_user
    prefetched_tokens["employee_user"] = emp_user

    tests = [
        ("LMS Admin", test_lms_admin),
        ("LMS Employee", test_lms_employee),
        ("LMS API", test_lms_api),
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
                ss(driver, f"fatal_{name.replace(' ', '_').lower()}")
        finally:
            if driver:
                try:
                    driver.quit()
                except: pass
                import subprocess
                subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"],
                               capture_output=True, timeout=5)
            time.sleep(3)

    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)

    p = sum(1 for r in test_results if r["status"] == "PASS")
    f = sum(1 for r in test_results if r["status"] == "FAIL")
    w = sum(1 for r in test_results if r["status"] == "WARN")
    s = sum(1 for r in test_results if r["status"] == "SKIP")
    total = len(test_results)

    print(f"\n  PASS: {p}  |  FAIL: {f}  |  WARN: {w}  |  SKIP: {s}  |  TOTAL: {total}")
    print(f"  Pass Rate: {p/total*100:.1f}%" if total else "  No tests ran")

    print(f"\n{'─' * 70}")
    for r in test_results:
        icon = {"PASS": "+", "FAIL": "X", "WARN": "!", "SKIP": "-"}.get(r["status"], "?")
        print(f"  [{icon}] {r['module']:12s} | {r['test']:40s} | {r['status']}")
    print(f"{'─' * 70}")

    if bugs_found:
        print(f"\n  BUGS FOUND: {len(bugs_found)}")
        for b in bugs_found:
            print(f"    [{b['severity']:8s}] {b['module']} > {b['test']}: {b['details'][:80]}")

    # File GitHub issues for bugs
    file_github_issues()

    print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
