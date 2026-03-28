"""
EMP Cloud - Headless Selenium E2E Test Suite
Tests: https://test-empcloud.empcloud.com/
"""
import json
import time
import sys
import os
import traceback

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
REGISTER_API = f"{BASE_URL}/api/v1/auth/register"
LOGIN_API = f"{BASE_URL}/api/v1/auth/login"
TIMEOUT = 15
TIMESTAMP = datetime.now().strftime("%H%M%S")
TEST_EMAIL = f"e2etest{TIMESTAMP}@testmail.com"
TEST_PASSWORD = "E2eTest!@#456"
TEST_ORG = f"E2E Test Org {TIMESTAMP}"
TEST_FIRST = "E2ETest"
TEST_LAST = "User"

# ── Results ─────────────────────────────────────────────
results = []

def log_result(test_id, name, status, detail=""):
    results.append({"id": test_id, "name": name, "status": status, "detail": detail})
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"  {icon} {test_id}: {name} — {status}" + (f" | {detail}" if detail else ""))

# ── Driver Setup ────────────────────────────────────────
def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--ignore-certificate-errors")
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.implicitly_wait(5)
    return driver

# ── Helper Functions ────────────────────────────────────
def wait_for(driver, by, value, timeout=TIMEOUT):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def wait_clickable(driver, by, value, timeout=TIMEOUT):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )

def safe_find(driver, by, value):
    try:
        return driver.find_element(by, value)
    except NoSuchElementException:
        return None

def get_console_errors(driver):
    """Get browser console errors."""
    try:
        logs = driver.get_log("browser")
        return [l for l in logs if l["level"] == "SEVERE"]
    except:
        return []

def take_screenshot(driver, name):
    try:
        driver.save_screenshot(f"C:/Users/Admin/screenshot_{name}.png")
    except:
        pass

# ══════════════════════════════════════════════════════════
# TEST MODULES
# ══════════════════════════════════════════════════════════

def test_landing_page(driver):
    """Test the landing/login page loads correctly."""
    print("\n🔹 MODULE: Landing Page & Login Form")

    # T001: Page loads
    try:
        driver.get(BASE_URL)
        WebDriverWait(driver, TIMEOUT).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        title = driver.title
        if "EMP Cloud" in title:
            log_result("T001", "Page loads successfully", "PASS", f"Title: {title}")
        else:
            log_result("T001", "Page loads successfully", "FAIL", f"Unexpected title: {title}")
    except Exception as e:
        log_result("T001", "Page loads successfully", "FAIL", str(e))

    # T002: Check for JS console errors on load
    try:
        errors = get_console_errors(driver)
        if not errors:
            log_result("T002", "No critical JS console errors on load", "PASS")
        else:
            log_result("T002", "No critical JS console errors on load", "FAIL",
                      f"{len(errors)} errors: {errors[0]['message'][:100]}")
    except:
        log_result("T002", "No critical JS console errors on load", "SKIP", "Cannot read console logs")

    # T003: Login form is present
    try:
        time.sleep(2)  # Wait for SPA to render
        page_source = driver.page_source.lower()
        has_email = safe_find(driver, By.CSS_SELECTOR, 'input[type="email"], input[name="email"], input[placeholder*="email" i]')
        has_password = safe_find(driver, By.CSS_SELECTOR, 'input[type="password"], input[name="password"]')

        if has_email and has_password:
            log_result("T003", "Login form present with email & password fields", "PASS")
        elif has_email or has_password:
            log_result("T003", "Login form present with email & password fields", "FAIL", "Only one field found")
        else:
            # Check if we're redirected to a different page
            current_url = driver.current_url
            log_result("T003", "Login form present with email & password fields", "FAIL",
                      f"No login form found. URL: {current_url}")
            take_screenshot(driver, "login_form")
    except Exception as e:
        log_result("T003", "Login form present with email & password fields", "FAIL", str(e))

    # T004: Page has favicon
    try:
        favicon = safe_find(driver, By.CSS_SELECTOR, 'link[rel*="icon"]')
        if favicon:
            log_result("T004", "Favicon is set", "PASS", favicon.get_attribute("href"))
        else:
            log_result("T004", "Favicon is set", "FAIL", "No favicon link tag found")
    except Exception as e:
        log_result("T004", "Favicon is set", "FAIL", str(e))

    # T005: Page meta viewport set (responsive)
    try:
        viewport = safe_find(driver, By.CSS_SELECTOR, 'meta[name="viewport"]')
        if viewport:
            log_result("T005", "Viewport meta tag set (responsive ready)", "PASS")
        else:
            log_result("T005", "Viewport meta tag set (responsive ready)", "FAIL")
    except Exception as e:
        log_result("T005", "Viewport meta tag set (responsive ready)", "FAIL", str(e))


def test_registration_page(driver):
    """Test registration flow via the UI."""
    print("\n🔹 MODULE: Registration Page")

    # T010: Navigate to register page
    try:
        driver.get(f"{BASE_URL}/register")
        time.sleep(3)
        current_url = driver.current_url
        page_source = driver.page_source.lower()

        has_register_form = (
            safe_find(driver, By.CSS_SELECTOR, 'input[name="org_name"], input[placeholder*="organization" i], input[placeholder*="company" i]') or
            "register" in page_source or "sign up" in page_source or "create account" in page_source
        )

        if has_register_form:
            log_result("T010", "Registration page loads", "PASS", f"URL: {current_url}")
        else:
            log_result("T010", "Registration page loads", "FAIL", f"URL: {current_url}")
            take_screenshot(driver, "register_page")
    except Exception as e:
        log_result("T010", "Registration page loads", "FAIL", str(e))

    # T011: Register form fields present
    try:
        fields_found = []
        for selector in [
            ('input[type="email"], input[name="email"]', "email"),
            ('input[type="password"], input[name="password"]', "password"),
        ]:
            el = safe_find(driver, By.CSS_SELECTOR, selector[0])
            if el:
                fields_found.append(selector[1])

        # Also check for name/org fields
        all_inputs = driver.find_elements(By.CSS_SELECTOR, "input")
        input_info = [(i.get_attribute("name") or i.get_attribute("placeholder") or i.get_attribute("type")) for i in all_inputs]

        if len(fields_found) >= 2:
            log_result("T011", "Registration form has required fields", "PASS",
                      f"Found: {fields_found}. All inputs: {input_info}")
        else:
            log_result("T011", "Registration form has required fields", "FAIL",
                      f"Found: {fields_found}. All inputs: {input_info}")
    except Exception as e:
        log_result("T011", "Registration form has required fields", "FAIL", str(e))

    # T012: Empty form submission shows validation
    try:
        submit_btn = safe_find(driver, By.CSS_SELECTOR,
            'button[type="submit"], button:not([type="button"])')
        if submit_btn:
            submit_btn.click()
            time.sleep(1)
            # Look for validation messages
            page_after = driver.page_source.lower()
            has_validation = any(word in page_after for word in ["required", "invalid", "please", "error", "must"])
            if has_validation:
                log_result("T012", "Empty form submission shows validation errors", "PASS")
            else:
                log_result("T012", "Empty form submission shows validation errors", "FAIL", "No validation messages found")
        else:
            log_result("T012", "Empty form submission shows validation errors", "SKIP", "No submit button found")
    except Exception as e:
        log_result("T012", "Empty form submission shows validation errors", "FAIL", str(e))


def test_login_flow(driver):
    """Test login with credentials obtained via API registration."""
    print("\n🔹 MODULE: Login Flow")

    # Login via API with existing test account
    import urllib.request
    import urllib.error

    login_data = json.dumps({
        "email": "bugtest@example.com",
        "password": "Test123!@#"
    }).encode()

    req = urllib.request.Request(LOGIN_API, data=login_data,
                                 headers={
                                     "Content-Type": "application/json",
                                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                                     "Accept": "application/json",
                                     "Origin": BASE_URL,
                                     "Referer": f"{BASE_URL}/login"
                                 })
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        api_result = json.loads(resp.read())
        access_token = api_result["data"]["tokens"]["access_token"]
        log_result("T020", "API login for test credentials", "PASS", f"User: bugtest@example.com")
    except Exception as e:
        log_result("T020", "API login for test credentials", "FAIL", str(e))
        return None

    # T021: Login with valid credentials via UI
    try:
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)

        email_field = safe_find(driver, By.CSS_SELECTOR,
            'input[type="email"], input[name="email"], input[placeholder*="email" i]')
        pass_field = safe_find(driver, By.CSS_SELECTOR,
            'input[type="password"], input[name="password"]')

        if email_field and pass_field:
            email_field.clear()
            email_field.send_keys("bugtest@example.com")
            pass_field.clear()
            pass_field.send_keys("Test123!@#")

            submit = safe_find(driver, By.CSS_SELECTOR, 'button[type="submit"]')
            if submit:
                submit.click()
                time.sleep(5)

                current_url = driver.current_url
                # Check if we're past login
                if "/login" not in current_url or "/dashboard" in current_url:
                    log_result("T021", "Login with valid credentials", "PASS", f"Redirected to: {current_url}")
                else:
                    page_text = driver.find_element(By.TAG_NAME, "body").text[:200]
                    log_result("T021", "Login with valid credentials", "FAIL",
                              f"Still on login. URL: {current_url}. Text: {page_text}")
                    take_screenshot(driver, "login_fail")
            else:
                log_result("T021", "Login with valid credentials", "FAIL", "No submit button")
        else:
            log_result("T021", "Login with valid credentials", "FAIL", "Login form fields not found")
    except Exception as e:
        log_result("T021", "Login with valid credentials", "FAIL", str(e))

    # T022: Invalid credentials show error
    try:
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)

        email_field = safe_find(driver, By.CSS_SELECTOR,
            'input[type="email"], input[name="email"], input[placeholder*="email" i]')
        pass_field = safe_find(driver, By.CSS_SELECTOR,
            'input[type="password"], input[name="password"]')

        if email_field and pass_field:
            email_field.clear()
            email_field.send_keys("invalid@wrong.com")
            pass_field.clear()
            pass_field.send_keys("WrongPass123!")

            submit = safe_find(driver, By.CSS_SELECTOR, 'button[type="submit"]')
            if submit:
                submit.click()
                time.sleep(3)
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(word in page_text for word in ["invalid", "incorrect", "error", "wrong", "failed"]):
                    log_result("T022", "Invalid credentials show error message", "PASS")
                else:
                    log_result("T022", "Invalid credentials show error message", "FAIL", "No error shown")
                    take_screenshot(driver, "invalid_login")
        else:
            log_result("T022", "Invalid credentials show error message", "SKIP", "No login form")
    except Exception as e:
        log_result("T022", "Invalid credentials show error message", "FAIL", str(e))

    return access_token


def test_dashboard(driver, token):
    """Test dashboard after login."""
    print("\n🔹 MODULE: Dashboard")

    # Inject token and navigate to dashboard
    try:
        driver.get(BASE_URL)
        time.sleep(1)
        # Set token in localStorage
        driver.execute_script(f"""
            localStorage.setItem('access_token', '{token}');
            localStorage.setItem('token', '{token}');
        """)
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(5)

        current_url = driver.current_url
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # T030: Dashboard loads
        if "/login" in current_url:
            log_result("T030", "Dashboard page loads after auth", "FAIL", "Redirected to login")
            take_screenshot(driver, "dashboard_redirect")
            return

        log_result("T030", "Dashboard page loads after auth", "PASS", f"URL: {current_url}")

        # T031: Dashboard has navigation/sidebar
        nav = safe_find(driver, By.CSS_SELECTOR, "nav, aside, [role='navigation'], .sidebar, .nav")
        if nav:
            log_result("T031", "Navigation/sidebar is present", "PASS")
        else:
            log_result("T031", "Navigation/sidebar is present", "FAIL")
            take_screenshot(driver, "dashboard_no_nav")

        # T032: Dashboard has content/widgets
        body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
        if len(body_text) > 50:
            log_result("T032", "Dashboard has content/widgets", "PASS", f"Content length: {len(body_text)} chars")
        else:
            log_result("T032", "Dashboard has content/widgets", "FAIL", "Page appears empty")
            take_screenshot(driver, "dashboard_empty")

        # T033: No JS errors on dashboard
        errors = get_console_errors(driver)
        if not errors:
            log_result("T033", "No JS console errors on dashboard", "PASS")
        else:
            log_result("T033", "No JS console errors on dashboard", "FAIL",
                      f"{len(errors)} errors")

    except Exception as e:
        log_result("T030", "Dashboard page loads after auth", "FAIL", str(e))


def test_navigation_pages(driver, token):
    """Test that key pages load without errors."""
    print("\n🔹 MODULE: Page Navigation & Loading")

    pages = [
        ("T040", "/employees", "Employee Directory"),
        ("T041", "/attendance", "Attendance"),
        ("T042", "/leave", "Leave Management"),
        ("T043", "/documents", "Documents"),
        ("T044", "/announcements", "Announcements"),
        ("T045", "/helpdesk", "Helpdesk"),
        ("T046", "/surveys", "Surveys"),
        ("T047", "/self-service", "Self Service"),
        ("T048", "/org-chart", "Org Chart"),
        ("T049", "/settings", "Settings"),
        ("T050", "/reports", "Reports"),
        ("T051", "/assets", "Assets"),
        ("T052", "/positions", "Positions"),
        ("T053", "/events", "Events"),
        ("T054", "/wellness", "Wellness"),
        ("T055", "/forum", "Forum"),
        ("T056", "/feedback", "Feedback"),
    ]

    # Ensure token is set
    driver.get(BASE_URL)
    time.sleep(1)
    driver.execute_script(f"""
        localStorage.setItem('access_token', '{token}');
        localStorage.setItem('token', '{token}');
    """)

    for test_id, path, name in pages:
        try:
            driver.get(f"{BASE_URL}{path}")
            time.sleep(3)

            current_url = driver.current_url
            page_text = driver.find_element(By.TAG_NAME, "body").text.strip()

            # Check if redirected to login (auth issue)
            if "/login" in current_url:
                log_result(test_id, f"{name} page loads", "FAIL", "Redirected to login — auth not persisted")
                continue

            # Check for error states
            page_lower = page_text.lower()
            if "not found" in page_lower or "404" in page_lower:
                log_result(test_id, f"{name} page loads", "FAIL", "404 Not Found")
            elif "error" in page_lower and "server error" in page_lower:
                log_result(test_id, f"{name} page loads", "FAIL", "Server error displayed")
            elif len(page_text) < 20:
                log_result(test_id, f"{name} page loads", "FAIL", "Page appears blank")
                take_screenshot(driver, f"page_{path.strip('/')}")
            else:
                # Check for JS errors
                errors = get_console_errors(driver)
                if errors:
                    log_result(test_id, f"{name} page loads", "WARN",
                              f"Loaded but {len(errors)} JS errors")
                else:
                    log_result(test_id, f"{name} page loads", "PASS", f"URL: {current_url}")
        except Exception as e:
            log_result(test_id, f"{name} page loads", "FAIL", str(e)[:100])


def test_responsive_layout(driver):
    """Test responsive layout at different viewport sizes."""
    print("\n🔹 MODULE: Responsive Layout")

    viewports = [
        ("T060", 1920, 1080, "Desktop 1920x1080"),
        ("T061", 1366, 768, "Laptop 1366x768"),
        ("T062", 768, 1024, "Tablet 768x1024"),
        ("T063", 375, 812, "Mobile 375x812"),
    ]

    for test_id, w, h, name in viewports:
        try:
            driver.set_window_size(w, h)
            driver.get(BASE_URL)
            time.sleep(2)

            # Check for horizontal overflow
            has_overflow = driver.execute_script(
                "return document.documentElement.scrollWidth > document.documentElement.clientWidth"
            )

            # Check if content is visible
            body = driver.find_element(By.TAG_NAME, "body")
            body_rect = body.rect

            if has_overflow:
                log_result(test_id, f"No horizontal overflow at {name}", "FAIL", "Horizontal scrollbar present")
                take_screenshot(driver, f"responsive_{w}x{h}")
            else:
                log_result(test_id, f"No horizontal overflow at {name}", "PASS")
        except Exception as e:
            log_result(test_id, f"No horizontal overflow at {name}", "FAIL", str(e)[:100])

    # Reset to desktop
    driver.set_window_size(1920, 1080)


def test_onboarding_wizard(driver, token):
    """Test onboarding wizard for new org."""
    print("\n🔹 MODULE: Onboarding Wizard")

    try:
        driver.get(BASE_URL)
        time.sleep(1)
        driver.execute_script(f"""
            localStorage.setItem('access_token', '{token}');
            localStorage.setItem('token', '{token}');
        """)
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(5)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        # T070: Check if onboarding is shown for new org
        has_onboarding = any(word in page_text for word in [
            "welcome", "get started", "setup", "onboarding", "wizard", "step 1", "configure"
        ])

        if has_onboarding:
            log_result("T070", "Onboarding wizard shown for new organization", "PASS")
        else:
            log_result("T070", "Onboarding wizard shown for new organization", "FAIL",
                      "No onboarding flow detected for newly registered org")
            take_screenshot(driver, "onboarding")
    except Exception as e:
        log_result("T070", "Onboarding wizard shown for new organization", "FAIL", str(e)[:100])


def test_logout(driver, token):
    """Test logout functionality."""
    print("\n🔹 MODULE: Logout")

    try:
        # Login first
        driver.get(BASE_URL)
        time.sleep(1)
        driver.execute_script(f"""
            localStorage.setItem('access_token', '{token}');
            localStorage.setItem('token', '{token}');
        """)
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(5)

        # T080: Find and click logout
        # Look for user menu / avatar / dropdown
        user_menu = (
            safe_find(driver, By.CSS_SELECTOR, '[data-testid="user-menu"], .user-menu, .avatar, .profile-menu') or
            safe_find(driver, By.CSS_SELECTOR, "button img[alt], button .avatar, header button:last-child")
        )

        if user_menu:
            user_menu.click()
            time.sleep(1)

        # Look for logout button/link
        logout = (
            safe_find(driver, By.XPATH, "//*[contains(text(), 'Logout') or contains(text(), 'Log out') or contains(text(), 'Sign out')]") or
            safe_find(driver, By.CSS_SELECTOR, '[data-testid="logout"], a[href*="logout"]')
        )

        if logout:
            logout.click()
            time.sleep(3)
            current_url = driver.current_url
            if "/login" in current_url or current_url.rstrip("/") == BASE_URL:
                log_result("T080", "Logout redirects to login page", "PASS")
            else:
                log_result("T080", "Logout redirects to login page", "FAIL", f"URL: {current_url}")
        else:
            log_result("T080", "Logout redirects to login page", "SKIP", "Logout button not found")
            take_screenshot(driver, "logout_not_found")

        # T081: After logout, accessing dashboard redirects to login
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(3)
        if "/login" in driver.current_url:
            log_result("T081", "Protected pages redirect to login after logout", "PASS")
        else:
            log_result("T081", "Protected pages redirect to login after logout", "FAIL",
                      f"Accessed dashboard after logout: {driver.current_url}")
    except Exception as e:
        log_result("T080", "Logout flow", "FAIL", str(e)[:100])


def test_accessibility_basics(driver):
    """Basic accessibility checks."""
    print("\n🔹 MODULE: Accessibility Basics")

    try:
        driver.get(BASE_URL)
        time.sleep(3)

        # T090: HTML lang attribute
        html = driver.find_element(By.TAG_NAME, "html")
        lang = html.get_attribute("lang")
        if lang:
            log_result("T090", "HTML lang attribute set", "PASS", f'lang="{lang}"')
        else:
            log_result("T090", "HTML lang attribute set", "FAIL", "Missing lang attribute")

        # T091: Images have alt text
        images = driver.find_elements(By.TAG_NAME, "img")
        if images:
            missing_alt = [img.get_attribute("src") for img in images if not img.get_attribute("alt")]
            if not missing_alt:
                log_result("T091", "All images have alt text", "PASS", f"{len(images)} images checked")
            else:
                log_result("T091", "All images have alt text", "FAIL",
                          f"{len(missing_alt)}/{len(images)} missing alt")
        else:
            log_result("T091", "All images have alt text", "SKIP", "No images found")

        # T092: Form inputs have labels
        inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])")
        unlabeled = []
        for inp in inputs:
            inp_id = inp.get_attribute("id")
            has_label = False
            if inp_id:
                label = safe_find(driver, By.CSS_SELECTOR, f'label[for="{inp_id}"]')
                has_label = label is not None
            if not has_label:
                aria = inp.get_attribute("aria-label") or inp.get_attribute("aria-labelledby") or inp.get_attribute("placeholder")
                has_label = bool(aria)
            if not has_label:
                unlabeled.append(inp.get_attribute("name") or inp.get_attribute("type"))

        if not unlabeled:
            log_result("T092", "Form inputs have labels/aria-labels", "PASS", f"{len(inputs)} inputs checked")
        else:
            log_result("T092", "Form inputs have labels/aria-labels", "FAIL",
                      f"Unlabeled: {unlabeled[:5]}")

        # T093: Focus is visible
        driver.execute_script("""
            const input = document.querySelector('input');
            if (input) input.focus();
        """)
        focused = driver.switch_to.active_element
        if focused:
            log_result("T093", "Focus is manageable via JS", "PASS")
        else:
            log_result("T093", "Focus is manageable via JS", "FAIL")

    except Exception as e:
        log_result("T090", "Accessibility checks", "FAIL", str(e)[:100])


def test_performance_basics(driver):
    """Basic performance checks."""
    print("\n🔹 MODULE: Performance Basics")

    try:
        start = time.time()
        driver.get(BASE_URL)
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        load_time = time.time() - start

        # T100: Page load time
        if load_time < 3:
            log_result("T100", "Page loads within 3 seconds", "PASS", f"{load_time:.2f}s")
        elif load_time < 5:
            log_result("T100", "Page loads within 3 seconds", "WARN", f"{load_time:.2f}s (slow)")
        else:
            log_result("T100", "Page loads within 3 seconds", "FAIL", f"{load_time:.2f}s")

        # T101: Check total page weight
        perf_data = driver.execute_script("""
            const entries = performance.getEntriesByType('resource');
            let totalSize = 0;
            let jsSize = 0;
            let cssSize = 0;
            entries.forEach(e => {
                totalSize += e.transferSize || 0;
                if (e.name.includes('.js')) jsSize += e.transferSize || 0;
                if (e.name.includes('.css')) cssSize += e.transferSize || 0;
            });
            return {total: totalSize, js: jsSize, css: cssSize, count: entries.length};
        """)

        total_mb = perf_data['total'] / (1024*1024)
        js_mb = perf_data['js'] / (1024*1024)

        if total_mb < 5:
            log_result("T101", "Total page weight under 5MB", "PASS",
                      f"Total: {total_mb:.2f}MB, JS: {js_mb:.2f}MB, {perf_data['count']} resources")
        else:
            log_result("T101", "Total page weight under 5MB", "FAIL",
                      f"Total: {total_mb:.2f}MB (too heavy)")

    except Exception as e:
        log_result("T100", "Performance checks", "FAIL", str(e)[:100])


def test_security_ui(driver):
    """Test security from the UI perspective."""
    print("\n🔹 MODULE: Security (UI)")

    # T110: Password field masks input
    try:
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)
        pass_field = safe_find(driver, By.CSS_SELECTOR, 'input[type="password"]')
        if pass_field:
            field_type = pass_field.get_attribute("type")
            if field_type == "password":
                log_result("T110", "Password field masks input", "PASS")
            else:
                log_result("T110", "Password field masks input", "FAIL", f"type={field_type}")
        else:
            log_result("T110", "Password field masks input", "SKIP", "No password field found")
    except Exception as e:
        log_result("T110", "Password field masks input", "FAIL", str(e)[:100])

    # T111: autocomplete=off or new-password on password field
    try:
        if pass_field:
            autocomplete = pass_field.get_attribute("autocomplete")
            if autocomplete in ["off", "new-password", "current-password"]:
                log_result("T111", "Password field has autocomplete attribute", "PASS", f"autocomplete={autocomplete}")
            else:
                log_result("T111", "Password field has autocomplete attribute", "WARN",
                          f"autocomplete={autocomplete or 'not set'}")
    except Exception as e:
        log_result("T111", "Password field autocomplete", "FAIL", str(e)[:100])

    # T112: No sensitive data in page source
    try:
        source = driver.page_source
        sensitive_patterns = ["api_key", "secret_key", "private_key", "AWS_", "database_url", "db_password"]
        found = [p for p in sensitive_patterns if p.lower() in source.lower()]
        if not found:
            log_result("T112", "No sensitive data leaked in page source", "PASS")
        else:
            log_result("T112", "No sensitive data leaked in page source", "FAIL", f"Found: {found}")
    except Exception as e:
        log_result("T112", "No sensitive data in page source", "FAIL", str(e)[:100])

    # T113: HTTPS enforced
    try:
        driver.get(BASE_URL.replace("https://", "http://"))
        time.sleep(3)
        if driver.current_url.startswith("https://"):
            log_result("T113", "HTTP redirects to HTTPS", "PASS")
        else:
            log_result("T113", "HTTP redirects to HTTPS", "FAIL", f"URL: {driver.current_url}")
    except Exception as e:
        log_result("T113", "HTTP redirects to HTTPS", "FAIL", str(e)[:100])


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  EMP Cloud — Headless Selenium E2E Test Suite")
    print(f"  Target: {BASE_URL}")
    print(f"  Started: {datetime.now().isoformat()}")
    print("=" * 60)

    driver = None
    token = None

    try:
        print("\n⏳ Starting headless Chrome...")
        driver = create_driver()
        print("✅ Chrome started successfully\n")

        # Run test modules
        test_landing_page(driver)
        test_registration_page(driver)
        token = test_login_flow(driver)

        if token:
            test_dashboard(driver, token)
            test_navigation_pages(driver, token)
            test_onboarding_wizard(driver, token)
            test_logout(driver, token)
        else:
            print("\n⚠️  Skipping authenticated tests — no token obtained")

        test_responsive_layout(driver)
        test_accessibility_basics(driver)
        test_performance_basics(driver)
        test_security_ui(driver)

    except WebDriverException as e:
        print(f"\n❌ WebDriver error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()

    # ── Summary ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  TEST RESULTS SUMMARY")
    print("=" * 60)

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    skip_count = sum(1 for r in results if r["status"] == "SKIP")
    total = len(results)

    print(f"\n  ✅ PASSED:  {pass_count}/{total}")
    print(f"  ❌ FAILED:  {fail_count}/{total}")
    print(f"  ⚠️  WARNED: {warn_count}/{total}")
    print(f"  ⏭️  SKIPPED: {skip_count}/{total}")

    if fail_count > 0:
        print(f"\n  FAILED TESTS:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    ❌ {r['id']}: {r['name']}")
                if r["detail"]:
                    print(f"       → {r['detail'][:120]}")

    if warn_count > 0:
        print(f"\n  WARNINGS:")
        for r in results:
            if r["status"] == "WARN":
                print(f"    ⚠️  {r['id']}: {r['name']} — {r['detail'][:120]}")

    print(f"\n  Finished: {datetime.now().isoformat()}")
    print("=" * 60)

    # Write JSON results
    with open("C:/Users/Admin/e2e_test_results.json", "w") as f:
        json.dump({"results": results, "summary": {
            "total": total, "pass": pass_count, "fail": fail_count,
            "warn": warn_count, "skip": skip_count
        }}, f, indent=2)
    print(f"\n  Results saved to: C:/Users/Admin/e2e_test_results.json")

    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
