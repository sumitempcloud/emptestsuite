#!/usr/bin/env python3
"""
Comprehensive Performance Module Test via SSO
Tests: dashboard, review-cycles, goals, analytics, nine-box, pips,
       one-on-ones, competencies, succession-plans, and CRUD operations.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import json
import time
import requests
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ── Config ──────────────────────────────────────────────────────────────
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_performance"
LOGIN_API = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
PERF_BASE = "https://test-performance.empcloud.com"
PERF_API = "https://test-performance-api.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs = []
results = []
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{timestamp}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {path}")
    return path


def record(test_name, status, details=""):
    results.append({"test": test_name, "status": status, "details": details})
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
    log(f"  [{icon}] {test_name}: {details}")


def file_bug(title, body):
    bugs.append(title)
    log(f"  BUG: {title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github+json",
            },
            json={
                "title": title,
                "body": body,
                "labels": ["bug", "performance"],
            },
            timeout=15,
        )
        if resp.status_code == 201:
            log(f"  Bug filed: {resp.json().get('html_url')}")
        else:
            log(f"  Bug filing failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        log(f"  Bug filing error: {e}")


def wait_for_page(driver, timeout=15):
    """Wait for page to fully load."""
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(2)  # extra settle time for SPA rendering


def wait_for_content(driver, timeout=12):
    """Wait until body has meaningful content (not just loading spinners)."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "main, [class*='dashboard'], [class*='content'], .page, #root > div > div")) > 0
        )
    except TimeoutException:
        pass
    time.sleep(1.5)


def check_page_errors(driver, page_name):
    """Check for visible error messages on the page."""
    error_selectors = [
        "[class*='error']", "[class*='Error']",
        "[role='alert']", ".alert-danger", ".toast-error",
    ]
    for sel in error_selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elems:
                txt = el.text.strip()
                if txt and len(txt) > 5 and "error" in txt.lower():
                    return txt
        except:
            pass
    return None


def is_page_blank_or_error(driver):
    """Check if page is blank or shows a major error."""
    body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
    if len(body_text) < 20:
        return True, "Page appears blank or nearly empty"
    error_indicators = ["500", "internal server error", "something went wrong", "page not found", "404", "cannot read properties"]
    lower = body_text.lower()
    for ind in error_indicators:
        if ind in lower:
            return True, f"Page shows error: {ind}"
    return False, ""


# ── SSO Login ───────────────────────────────────────────────────────────
def sso_login():
    log("Step 1: Authenticating via Login API...")
    resp = requests.post(LOGIN_API, json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    if resp.status_code != 200:
        log(f"  Login failed: {resp.status_code} - {resp.text[:300]}")
        sys.exit(1)

    data = resp.json()
    tokens = data.get("data", {}).get("tokens", {})
    token = tokens.get("access_token") or data.get("data", {}).get("token") or data.get("token")
    if not token:
        log(f"  No token in response: {json.dumps(data)[:300]}")
        sys.exit(1)

    log(f"  Token obtained (length={len(token)})")
    return token


def create_driver():
    opts = Options()
    opts.binary_location = CHROME_PATH
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    return driver


def navigate(driver, path, name):
    """Navigate to a page and wait for it to load."""
    url = f"{PERF_BASE}{path}"
    log(f"  Navigating to {url}")
    driver.get(url)
    wait_for_page(driver)
    wait_for_content(driver)
    return url


# ── Test Functions ──────────────────────────────────────────────────────

def test_dashboard(driver):
    log("\n=== Test: Dashboard ===")
    navigate(driver, "/dashboard", "dashboard")
    screenshot(driver, "01_dashboard")

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        record("Dashboard Load", "fail", err_msg)
        file_bug(
            "[Performance] Dashboard fails to load or shows error",
            f"**URL:** {PERF_BASE}/dashboard\n**Issue:** {err_msg}\n**Steps:** SSO login then navigate to /dashboard"
        )
        return

    body = driver.find_element(By.TAG_NAME, "body").text
    page_err = check_page_errors(driver, "dashboard")
    if page_err:
        record("Dashboard Load", "warn", f"Error on page: {page_err}")
    else:
        record("Dashboard Load", "pass", f"Dashboard loaded ({len(body)} chars)")

    # Check for key dashboard elements
    dashboard_keywords = ["review", "goal", "performance", "cycle", "pending", "active"]
    found = [kw for kw in dashboard_keywords if kw.lower() in body.lower()]
    if found:
        record("Dashboard Content", "pass", f"Found keywords: {', '.join(found)}")
    else:
        record("Dashboard Content", "warn", "No expected performance keywords found on dashboard")


def test_review_cycles(driver):
    log("\n=== Test: Review Cycles ===")
    navigate(driver, "/review-cycles", "review_cycles")
    screenshot(driver, "02_review_cycles")

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        record("Review Cycles Page", "fail", err_msg)
        file_bug(
            "[Performance] Review Cycles page fails to load",
            f"**URL:** {PERF_BASE}/review-cycles\n**Issue:** {err_msg}"
        )
        return

    body = driver.find_element(By.TAG_NAME, "body").text
    record("Review Cycles Page", "pass", f"Page loaded ({len(body)} chars)")

    # Check for table/list
    tables = driver.find_elements(By.CSS_SELECTOR, "table, [class*='table'], [class*='list'], [class*='grid']")
    if tables:
        record("Review Cycles Table", "pass", f"Found {len(tables)} table/list element(s)")
    else:
        record("Review Cycles Table", "warn", "No table/list found on review cycles page")


def test_create_review_cycle(driver):
    log("\n=== Test: Create Review Cycle ===")
    navigate(driver, "/review-cycles/new", "create_review_cycle")
    screenshot(driver, "03_create_review_cycle")

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        record("Create Review Cycle Page", "fail", err_msg)
        file_bug(
            "[Performance] Create Review Cycle page fails to load",
            f"**URL:** {PERF_BASE}/review-cycles/new\n**Issue:** {err_msg}"
        )
        return

    body = driver.find_element(By.TAG_NAME, "body").text
    # Look for form elements
    inputs = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea, [class*='form'], button[type='submit']")
    if inputs:
        record("Create Review Cycle Form", "pass", f"Found {len(inputs)} form element(s)")
    else:
        record("Create Review Cycle Form", "warn", "No form elements found")

    # Try to interact with the form
    try:
        # Look for name/title input
        name_input = None
        for inp in driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type])"):
            placeholder = inp.get_attribute("placeholder") or ""
            name_attr = inp.get_attribute("name") or ""
            if any(kw in (placeholder + name_attr).lower() for kw in ["name", "title", "cycle"]):
                name_input = inp
                break
        if not name_input and driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type])"):
            name_input = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type])")[0]

        if name_input:
            name_input.clear()
            name_input.send_keys("Q1 2026 Test Cycle")
            record("Review Cycle Name Input", "pass", "Entered cycle name")
            screenshot(driver, "03b_review_cycle_form_filled")
        else:
            record("Review Cycle Name Input", "warn", "Could not find name input field")
    except Exception as e:
        record("Review Cycle Form Interaction", "warn", str(e)[:100])


def test_goals(driver):
    log("\n=== Test: Goals ===")
    navigate(driver, "/goals", "goals")
    screenshot(driver, "04_goals")

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        record("Goals Page", "fail", err_msg)
        file_bug(
            "[Performance] Goals page fails to load",
            f"**URL:** {PERF_BASE}/goals\n**Issue:** {err_msg}"
        )
        return

    body = driver.find_element(By.TAG_NAME, "body").text
    record("Goals Page", "pass", f"Page loaded ({len(body)} chars)")

    # Check for goal-related content
    goal_keywords = ["goal", "okr", "key result", "progress", "objective", "target"]
    found = [kw for kw in goal_keywords if kw.lower() in body.lower()]
    if found:
        record("Goals Content", "pass", f"Found: {', '.join(found)}")
    else:
        record("Goals Content", "warn", "No goal-related keywords found")


def test_create_goal(driver):
    log("\n=== Test: Create Goal ===")
    navigate(driver, "/goals/new", "create_goal")
    screenshot(driver, "05_create_goal")

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        record("Create Goal Page", "fail", err_msg)
        file_bug(
            "[Performance] Create Goal page fails to load",
            f"**URL:** {PERF_BASE}/goals/new\n**Issue:** {err_msg}"
        )
        return

    inputs = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea, [class*='form']")
    if inputs:
        record("Create Goal Form", "pass", f"Found {len(inputs)} form element(s)")
    else:
        record("Create Goal Form", "warn", "No form elements found")

    # Try filling the form
    try:
        text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type]), textarea")
        if text_inputs:
            text_inputs[0].clear()
            text_inputs[0].send_keys("Improve Team Performance Q1 2026")
            record("Goal Title Input", "pass", "Entered goal title")
            # Fill description if available
            if len(text_inputs) > 1:
                text_inputs[1].clear()
                text_inputs[1].send_keys("Increase team output by 20% through process improvements")
                record("Goal Description Input", "pass", "Entered goal description")
            screenshot(driver, "05b_goal_form_filled")
        else:
            record("Goal Title Input", "warn", "No text inputs found")
    except Exception as e:
        record("Goal Form Interaction", "warn", str(e)[:100])


def test_analytics(driver):
    log("\n=== Test: Analytics ===")
    navigate(driver, "/analytics", "analytics")
    screenshot(driver, "06_analytics")

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        record("Analytics Page", "fail", err_msg)
        file_bug(
            "[Performance] Analytics page fails to load",
            f"**URL:** {PERF_BASE}/analytics\n**Issue:** {err_msg}"
        )
        return

    body = driver.find_element(By.TAG_NAME, "body").text
    record("Analytics Page", "pass", f"Page loaded ({len(body)} chars)")

    # Check for chart/analytics elements
    charts = driver.find_elements(By.CSS_SELECTOR, "svg, canvas, [class*='chart'], [class*='graph'], [class*='recharts']")
    if charts:
        record("Analytics Charts", "pass", f"Found {len(charts)} chart element(s)")
    else:
        record("Analytics Charts", "warn", "No chart elements found on analytics page")


def test_nine_box(driver):
    log("\n=== Test: 9-Box Grid ===")
    # Try both possible paths
    navigate(driver, "/analytics/nine-box", "nine_box")
    screenshot(driver, "07_nine_box_grid")

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        # Try alternate path
        navigate(driver, "/nine-box", "nine_box_alt")
        is_err2, err_msg2 = is_page_blank_or_error(driver)
        if is_err2:
            record("9-Box Grid Page", "fail", f"Both /analytics/nine-box and /nine-box failed: {err_msg}")
            file_bug(
                "[Performance] 9-Box Grid page fails to load",
                f"**URL:** {PERF_BASE}/analytics/nine-box and /nine-box\n**Issue:** {err_msg}"
            )
            screenshot(driver, "07_nine_box_grid_alt")
            return
        screenshot(driver, "07_nine_box_grid_alt")

    body = driver.find_element(By.TAG_NAME, "body").text
    record("9-Box Grid Page", "pass", f"Page loaded ({len(body)} chars)")

    # Check for grid elements
    grid_keywords = ["performance", "potential", "star", "consistent", "enigma", "high", "medium", "low"]
    found = [kw for kw in grid_keywords if kw.lower() in body.lower()]
    if found:
        record("9-Box Grid Content", "pass", f"Found: {', '.join(found)}")
    else:
        record("9-Box Grid Content", "warn", "No 9-box specific keywords found")

    # Look for the actual grid
    grid_elems = driver.find_elements(By.CSS_SELECTOR, "[class*='grid'], [class*='nine-box'], [class*='ninebox'], [class*='matrix'], table")
    if grid_elems:
        record("9-Box Grid Element", "pass", f"Found {len(grid_elems)} grid element(s)")
    else:
        record("9-Box Grid Element", "warn", "No grid element found")


def test_pips(driver):
    log("\n=== Test: PIPs ===")
    navigate(driver, "/pips", "pips")
    screenshot(driver, "08_pips")

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        record("PIPs Page", "fail", err_msg)
        file_bug(
            "[Performance] PIPs page fails to load",
            f"**URL:** {PERF_BASE}/pips\n**Issue:** {err_msg}"
        )
        return

    body = driver.find_element(By.TAG_NAME, "body").text
    record("PIPs Page", "pass", f"Page loaded ({len(body)} chars)")

    # Try the create PIP page
    navigate(driver, "/pips/new", "create_pip")
    screenshot(driver, "08b_create_pip")

    is_err2, err_msg2 = is_page_blank_or_error(driver)
    if is_err2:
        record("Create PIP Page", "fail", err_msg2)
    else:
        inputs = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea")
        record("Create PIP Page", "pass", f"Page loaded with {len(inputs)} form elements")


def test_one_on_ones(driver):
    log("\n=== Test: 1-on-1 Meetings ===")
    navigate(driver, "/one-on-ones", "one_on_ones")
    screenshot(driver, "09_one_on_ones")

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        record("1-on-1 Meetings Page", "fail", err_msg)
        file_bug(
            "[Performance] 1-on-1 Meetings page fails to load",
            f"**URL:** {PERF_BASE}/one-on-ones\n**Issue:** {err_msg}"
        )
        return

    body = driver.find_element(By.TAG_NAME, "body").text
    record("1-on-1 Meetings Page", "pass", f"Page loaded ({len(body)} chars)")

    # Check for meeting content
    meeting_keywords = ["meeting", "1-on-1", "one-on-one", "agenda", "schedule", "upcoming"]
    found = [kw for kw in meeting_keywords if kw.lower() in body.lower()]
    if found:
        record("1-on-1 Content", "pass", f"Found: {', '.join(found)}")


def test_competencies(driver):
    log("\n=== Test: Competency Frameworks ===")
    # Try multiple possible routes
    for path in ["/competencies", "/competency-frameworks"]:
        navigate(driver, path, "competencies")
        is_err, err_msg = is_page_blank_or_error(driver)
        if not is_err:
            break

    screenshot(driver, "10_competencies")

    if is_err:
        record("Competencies Page", "fail", err_msg)
        file_bug(
            "[Performance] Competency Frameworks page fails to load",
            f"**URL:** Tried /competencies and /competency-frameworks\n**Issue:** {err_msg}"
        )
        return

    body = driver.find_element(By.TAG_NAME, "body").text
    record("Competencies Page", "pass", f"Page loaded ({len(body)} chars)")

    competency_keywords = ["competency", "framework", "skill", "weight", "rating"]
    found = [kw for kw in competency_keywords if kw.lower() in body.lower()]
    if found:
        record("Competencies Content", "pass", f"Found: {', '.join(found)}")


def test_succession_plans(driver):
    log("\n=== Test: Succession Plans ===")
    navigate(driver, "/succession-plans", "succession_plans")
    screenshot(driver, "11_succession_plans")

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        record("Succession Plans Page", "fail", err_msg)
        file_bug(
            "[Performance] Succession Plans page fails to load",
            f"**URL:** {PERF_BASE}/succession-plans\n**Issue:** {err_msg}"
        )
        return

    body = driver.find_element(By.TAG_NAME, "body").text
    record("Succession Plans Page", "pass", f"Page loaded ({len(body)} chars)")

    plan_keywords = ["succession", "plan", "candidate", "readiness", "role", "critical"]
    found = [kw for kw in plan_keywords if kw.lower() in body.lower()]
    if found:
        record("Succession Plans Content", "pass", f"Found: {', '.join(found)}")


def test_additional_pages(driver):
    """Test additional pages: feedback, career paths, letters, settings, self-service."""
    extra_pages = [
        ("/feedback", "12_feedback", "Feedback Wall"),
        ("/career-paths", "13_career_paths", "Career Paths"),
        ("/letters", "14_letters", "Performance Letters"),
        ("/letters/templates", "15_letter_templates", "Letter Templates"),
        ("/settings", "16_settings", "Settings"),
        ("/goals/alignment", "17_goal_alignment", "Goal Alignment Tree"),
        ("/analytics/skills-gap", "18_skills_gap", "Skills Gap Analysis"),
        ("/my", "19_my_performance", "My Performance (Self-Service)"),
        ("/my/reviews", "20_my_reviews", "My Reviews"),
        ("/my/goals", "21_my_goals", "My Goals"),
        ("/my/feedback", "22_my_feedback", "My Feedback"),
        ("/my/career", "23_my_career", "My Career Path"),
    ]

    log("\n=== Test: Additional Pages ===")
    for path, ss_name, page_name in extra_pages:
        try:
            navigate(driver, path, page_name.lower().replace(" ", "_"))
            screenshot(driver, ss_name)

            is_err, err_msg = is_page_blank_or_error(driver)
            if is_err:
                record(f"{page_name} Page", "fail", err_msg)
                file_bug(
                    f"[Performance] {page_name} page fails to load",
                    f"**URL:** {PERF_BASE}{path}\n**Issue:** {err_msg}"
                )
            else:
                body_len = len(driver.find_element(By.TAG_NAME, "body").text)
                page_err = check_page_errors(driver, page_name)
                if page_err:
                    record(f"{page_name} Page", "warn", f"Page loaded but has error: {page_err}")
                else:
                    record(f"{page_name} Page", "pass", f"Loaded ({body_len} chars)")
        except Exception as e:
            record(f"{page_name} Page", "fail", str(e)[:100])


def test_api_health(token):
    """Test API endpoints directly."""
    log("\n=== Test: API Health & Endpoints ===")

    # Health check
    try:
        resp = requests.get(f"{PERF_API}/health", timeout=10)
        if resp.status_code == 200:
            record("API Health Check", "pass", f"Status 200: {resp.text[:100]}")
        else:
            record("API Health Check", "fail", f"Status {resp.status_code}")
    except Exception as e:
        record("API Health Check", "fail", str(e)[:100])

    headers = {"Authorization": f"Bearer {token}"}

    # SSO exchange
    try:
        resp = requests.post(
            f"{PERF_API}/api/v1/auth/sso",
            json={"token": token},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            perf_token = data.get("data", {}).get("token") or data.get("token")
            if perf_token:
                record("SSO Token Exchange", "pass", f"Got performance token (len={len(perf_token)})")
                headers = {"Authorization": f"Bearer {perf_token}"}
            else:
                record("SSO Token Exchange", "warn", f"200 but no token in response: {json.dumps(data)[:200]}")
        else:
            record("SSO Token Exchange", "warn", f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        record("SSO Token Exchange", "warn", str(e)[:100])

    # Test key API endpoints
    api_tests = [
        ("GET", "/api/v1/review-cycles", "Review Cycles API"),
        ("GET", "/api/v1/goals", "Goals API"),
        ("GET", "/api/v1/pips", "PIPs API"),
        ("GET", "/api/v1/one-on-ones", "One-on-Ones API"),
        ("GET", "/api/v1/competency-frameworks", "Competency Frameworks API"),
        ("GET", "/api/v1/succession-plans", "Succession Plans API"),
        ("GET", "/api/v1/feedback", "Feedback API"),
        ("GET", "/api/v1/analytics/overview", "Analytics Overview API"),
        ("GET", "/api/v1/nine-box", "9-Box Grid API"),
        ("GET", "/api/v1/career-paths", "Career Paths API"),
        ("GET", "/api/v1/letter-templates", "Letter Templates API"),
    ]

    for method, path, name in api_tests:
        try:
            url = f"{PERF_API}{path}"
            resp = requests.request(method, url, headers=headers, timeout=10)
            if resp.status_code in (200, 201):
                record(name, "pass", f"Status {resp.status_code}")
            elif resp.status_code == 401:
                record(name, "warn", "Unauthorized (401) - token may not have performance access")
            elif resp.status_code == 403:
                record(name, "warn", "Forbidden (403) - insufficient permissions")
            else:
                record(name, "fail", f"Status {resp.status_code}: {resp.text[:150]}")
        except Exception as e:
            record(name, "fail", str(e)[:100])


# ── Main ────────────────────────────────────────────────────────────────

def main():
    log("=" * 70)
    log("PERFORMANCE MODULE - COMPREHENSIVE SSO TEST")
    log("=" * 70)

    # Step 1: Get auth token
    token = sso_login()

    # Step 2: Test API endpoints
    test_api_health(token)

    # Step 3: Browser tests via SSO
    log("\nStep 2: Launching Chrome for SSO browser testing...")
    driver = create_driver()

    try:
        # SSO into performance module
        sso_url = f"{PERF_BASE}?sso_token={token}"
        log(f"  SSO URL: {PERF_BASE}?sso_token=<token>")
        driver.get(sso_url)
        wait_for_page(driver)
        wait_for_content(driver)

        # Check if SSO worked
        current = driver.current_url
        log(f"  Current URL after SSO: {current}")
        screenshot(driver, "00_sso_landing")

        body = driver.find_element(By.TAG_NAME, "body").text
        if "login" in current.lower() and "sso" not in body.lower():
            record("SSO Login", "fail", "Redirected to login page - SSO may have failed")
            file_bug(
                "[Performance] SSO token not accepted - redirects to login",
                f"**URL:** {PERF_BASE}?sso_token=<valid_token>\n**Issue:** SSO redirects to login page instead of authenticating"
            )
        else:
            record("SSO Login", "pass", f"Landed on: {current}")

        # Run all page tests
        test_dashboard(driver)
        test_review_cycles(driver)
        test_create_review_cycle(driver)
        test_goals(driver)
        test_create_goal(driver)
        test_analytics(driver)
        test_nine_box(driver)
        test_pips(driver)
        test_one_on_ones(driver)
        test_competencies(driver)
        test_succession_plans(driver)
        test_additional_pages(driver)

    except Exception as e:
        log(f"  CRITICAL ERROR: {e}")
        traceback.print_exc()
        screenshot(driver, "ERROR_critical")
    finally:
        driver.quit()

    # ── Summary ─────────────────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)

    pass_count = sum(1 for r in results if r["status"] == "pass")
    fail_count = sum(1 for r in results if r["status"] == "fail")
    warn_count = sum(1 for r in results if r["status"] == "warn")

    log(f"  PASS: {pass_count}  |  FAIL: {fail_count}  |  WARN: {warn_count}  |  TOTAL: {len(results)}")
    log(f"  Bugs filed: {len(bugs)}")

    if bugs:
        log("\n  Bugs:")
        for b in bugs:
            log(f"    - {b}")

    if fail_count > 0:
        log("\n  Failures:")
        for r in results:
            if r["status"] == "fail":
                log(f"    - {r['test']}: {r['details']}")

    log(f"\n  Screenshots saved to: {SCREENSHOT_DIR}")
    log("=" * 70)


if __name__ == "__main__":
    main()
