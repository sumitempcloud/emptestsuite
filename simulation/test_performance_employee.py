"""
Performance Module - Employee (priya@technova.in) Testing
Tests RBAC, self-service views, and restricted admin features.
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
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ── Config ──────────────────────────────────────────────────────────────
CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_performance_employee"
AUTH_API = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
PERF_FRONTEND = "https://test-performance.empcloud.com"
PERF_API = "https://test-performance-api.empcloud.com"
EMAIL = "priya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_filed = []
test_results = []

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {name}.png")
    return path

def record(test_name, status, detail=""):
    test_results.append({"test": test_name, "status": status, "detail": detail})
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "INFO"
    log(f"  [{icon}] {test_name}: {detail}")

def file_bug(title, body):
    """File a GitHub issue with [Performance Employee] prefix."""
    full_title = f"[Performance Employee] {title}"
    log(f"  Filing bug: {full_title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={
                "title": full_title,
                "body": body,
                "labels": ["bug", "performance", "rbac"]
            },
            timeout=15
        )
        if resp.status_code == 201:
            url = resp.json().get("html_url", "")
            log(f"  Bug filed: {url}")
            bugs_filed.append({"title": full_title, "url": url})
            return url
        else:
            log(f"  Bug filing failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        log(f"  Bug filing error: {e}")
    return None

def check_existing_bug(keyword):
    """Check if a similar bug already exists."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github.v3+json"
            },
            params={"state": "open", "per_page": 100},
            timeout=15
        )
        if resp.status_code == 200:
            for issue in resp.json():
                if keyword.lower() in issue.get("title", "").lower():
                    return issue.get("html_url")
    except:
        pass
    return None

def make_driver():
    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    return driver

def wait_for_page(driver, timeout=12):
    """Wait for page to settle."""
    time.sleep(2)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except:
        pass
    time.sleep(1)

def get_page_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""

def has_element(driver, by, value, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        return True
    except:
        return False

def find_clickable(driver, texts, timeout=5):
    """Find a clickable element matching any of the given texts."""
    for text in texts:
        try:
            els = driver.find_elements(By.XPATH,
                f"//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{text.lower()}')]")
            for el in els:
                if el.is_displayed():
                    return el
        except:
            continue
    # Try links/buttons
    for text in texts:
        try:
            els = driver.find_elements(By.PARTIAL_LINK_TEXT, text)
            for el in els:
                if el.is_displayed():
                    return el
        except:
            continue
    return None

def find_nav_links(driver):
    """Get all visible nav/sidebar links."""
    links = {}
    for el in driver.find_elements(By.CSS_SELECTOR, "a, button, [role='menuitem'], [role='tab']"):
        try:
            txt = el.text.strip()
            href = el.get_attribute("href") or ""
            if txt and el.is_displayed():
                links[txt.lower()] = {"text": txt, "href": href, "element": el}
        except:
            continue
    return links


# ═══════════════════════════════════════════════════════════════════════
# MAIN TEST
# ═══════════════════════════════════════════════════════════════════════
def main():
    log("=" * 70)
    log("PERFORMANCE MODULE - EMPLOYEE TESTING (priya@technova.in)")
    log("=" * 70)

    # ── Step 1: Login via API to get SSO token ──
    log("\n[1] Logging in via API...")
    token = None
    try:
        resp = requests.post(AUTH_API, json={"email": EMAIL, "password": PASSWORD}, timeout=15)
        log(f"  Auth response: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            token = (
                data.get("token")
                or data.get("access_token")
                or (data.get("data", {}) or {}).get("token")
                or (data.get("data", {}) or {}).get("access_token")
                or ((data.get("data", {}) or {}).get("tokens", {}) or {}).get("access_token")
            )
            if token:
                record("API Login", "pass", f"Got token ({len(token)} chars)")
            else:
                record("API Login", "fail", f"No token in response: {json.dumps(data)[:300]}")
        else:
            record("API Login", "fail", f"Status {resp.status_code}: {resp.text[:300]}")
    except Exception as e:
        record("API Login", "fail", str(e))

    if not token:
        log("FATAL: Cannot proceed without auth token")
        return

    # ── Step 2: SSO into Performance module ──
    log("\n[2] SSO into Performance module...")
    driver = make_driver()
    try:
        sso_url = f"{PERF_FRONTEND}?sso_token={token}"
        log(f"  Navigating to SSO URL...")
        driver.get(sso_url)
        wait_for_page(driver, 15)
        screenshot(driver, "01_sso_landing")

        current_url = driver.current_url
        page_text = get_page_text(driver)
        log(f"  URL: {current_url}")
        log(f"  Page text (first 300): {page_text[:300]}")

        # Check if SSO worked
        login_failed = any(k in page_text.lower() for k in ["login", "sign in", "unauthorized", "invalid token"])
        if "login" in current_url.lower() and "sso" not in current_url.lower():
            record("SSO Login", "fail", f"Redirected to login: {current_url}")
            file_bug("SSO login fails for employee user",
                     f"**Steps:** Login as {EMAIL}, use token for SSO to {PERF_FRONTEND}\n"
                     f"**Expected:** Land on performance dashboard\n"
                     f"**Actual:** Redirected to {current_url}\n"
                     f"**Page text:** {page_text[:500]}")
        elif login_failed and "dashboard" not in page_text.lower() and "performance" not in page_text.lower():
            record("SSO Login", "fail", f"Login page or error shown")
            screenshot(driver, "01_sso_failed")
        else:
            record("SSO Login", "pass", f"Landed on: {current_url}")

        screenshot(driver, "02_after_sso")

        # ── Explore page structure ──
        log("\n[3] Exploring page structure...")
        nav_links = find_nav_links(driver)
        log(f"  Found {len(nav_links)} nav elements:")
        for k, v in list(nav_links.items())[:20]:
            log(f"    - {v['text']} -> {v['href'][:80] if v['href'] else '(no href)'}")
        screenshot(driver, "03_page_structure")

        # Capture full page source for analysis
        page_source = driver.page_source[:5000]

        # ── Test 3: My Reviews ──
        log("\n[4] Testing: My Reviews...")
        found_reviews = False
        for path in ["/my-reviews", "/reviews", "/my-review", "/employee/reviews"]:
            try:
                driver.get(f"{PERF_FRONTEND}{path}")
                wait_for_page(driver)
                pg = get_page_text(driver)
                url = driver.current_url
                log(f"  {path} -> {url[:80]} | text: {pg[:150]}")
                if "404" not in pg and "not found" not in pg.lower():
                    found_reviews = True
                    screenshot(driver, f"04_my_reviews_{path.replace('/', '_')}")
                    if "review" in pg.lower() or "performance" in pg.lower():
                        record("My Reviews Page", "pass", f"Accessible at {path}")
                    break
            except Exception as e:
                log(f"  {path} error: {e}")

        # Also try clicking nav
        if not found_reviews:
            driver.get(sso_url)
            wait_for_page(driver)
            el = find_clickable(driver, ["My Reviews", "Reviews", "My Review"])
            if el:
                try:
                    el.click()
                    wait_for_page(driver)
                    screenshot(driver, "04_my_reviews_clicked")
                    record("My Reviews Page", "pass", f"Found via nav click: {driver.current_url}")
                    found_reviews = True
                except:
                    pass

        if not found_reviews:
            record("My Reviews Page", "info", "Could not find My Reviews page")
            screenshot(driver, "04_my_reviews_not_found")

        # ── Test 4: My Goals ──
        log("\n[5] Testing: My Goals...")
        found_goals = False
        for path in ["/my-goals", "/goals", "/employee/goals", "/goal"]:
            try:
                driver.get(f"{PERF_FRONTEND}{path}")
                wait_for_page(driver)
                pg = get_page_text(driver)
                url = driver.current_url
                log(f"  {path} -> {url[:80]} | text: {pg[:150]}")
                if "404" not in pg and "not found" not in pg.lower():
                    found_goals = True
                    screenshot(driver, f"05_my_goals_{path.replace('/', '_')}")
                    if "goal" in pg.lower():
                        record("My Goals Page", "pass", f"Accessible at {path}")
                    break
            except Exception as e:
                log(f"  {path} error: {e}")

        if not found_goals:
            driver.get(sso_url)
            wait_for_page(driver)
            el = find_clickable(driver, ["My Goals", "Goals", "Goal"])
            if el:
                try:
                    el.click()
                    wait_for_page(driver)
                    screenshot(driver, "05_my_goals_clicked")
                    record("My Goals Page", "pass", f"Found via nav click: {driver.current_url}")
                    found_goals = True
                except:
                    pass

        if not found_goals:
            record("My Goals Page", "info", "Could not find My Goals page")
            screenshot(driver, "05_my_goals_not_found")

        # ── Test 5: Self Assessment ──
        log("\n[6] Testing: Self Assessment...")
        found_sa = False
        for path in ["/self-assessment", "/self-review", "/assessment", "/employee/self-assessment"]:
            try:
                driver.get(f"{PERF_FRONTEND}{path}")
                wait_for_page(driver)
                pg = get_page_text(driver)
                url = driver.current_url
                log(f"  {path} -> {url[:80]} | text: {pg[:150]}")
                if "404" not in pg and "not found" not in pg.lower():
                    found_sa = True
                    screenshot(driver, f"06_self_assessment_{path.replace('/', '_')}")
                    record("Self Assessment Page", "pass", f"Accessible at {path}")
                    break
            except Exception as e:
                log(f"  {path} error: {e}")

        if not found_sa:
            driver.get(sso_url)
            wait_for_page(driver)
            el = find_clickable(driver, ["Self Assessment", "Self Review", "Assessment", "Self-Assessment"])
            if el:
                try:
                    el.click()
                    wait_for_page(driver)
                    screenshot(driver, "06_self_assessment_clicked")
                    record("Self Assessment Page", "pass", f"Found via nav click: {driver.current_url}")
                    found_sa = True
                except:
                    pass

        if not found_sa:
            record("Self Assessment Page", "info", "Could not find Self Assessment page")
            screenshot(driver, "06_self_assessment_not_found")

        # ══════════════════════════════════════════════════════════════
        # RBAC TESTS - Employee should NOT have access to these
        # ══════════════════════════════════════════════════════════════

        # ── Test 6: Other employees' reviews (should NOT) ──
        log("\n[7] RBAC: Other employees' reviews...")
        rbac_violations = []
        for path in ["/all-reviews", "/reviews/all", "/admin/reviews", "/team-reviews",
                      "/reviews/team", "/employees/reviews", "/manage/reviews"]:
            try:
                driver.get(f"{PERF_FRONTEND}{path}")
                wait_for_page(driver)
                pg = get_page_text(driver)
                url = driver.current_url
                log(f"  {path} -> {url[:80]} | text: {pg[:100]}")
                screenshot(driver, f"07_rbac_others_reviews_{path.replace('/', '_')}")
                # Check if we can see other employees' data
                has_other_data = any(k in pg.lower() for k in [
                    "all reviews", "team review", "employee list", "manage review"
                ]) and "unauthorized" not in pg.lower() and "forbidden" not in pg.lower() and "access denied" not in pg.lower()
                if has_other_data and "404" not in pg:
                    rbac_violations.append(f"Others' reviews accessible at {path}")
                    record("RBAC: Others' Reviews", "fail", f"Accessible at {path}")
            except:
                pass

        if not rbac_violations:
            record("RBAC: Others' Reviews", "pass", "Cannot access other employees' reviews")

        # ── Test 7: PIPs (should NOT see others') ──
        log("\n[8] RBAC: PIP access...")
        pip_violations = []
        for path in ["/pip", "/pips", "/admin/pip", "/manage/pip", "/improvement-plans",
                      "/performance-improvement", "/pip/all"]:
            try:
                driver.get(f"{PERF_FRONTEND}{path}")
                wait_for_page(driver)
                pg = get_page_text(driver)
                url = driver.current_url
                log(f"  {path} -> {url[:80]} | text: {pg[:100]}")
                screenshot(driver, f"08_rbac_pip_{path.replace('/', '_')}")
                has_pip_access = any(k in pg.lower() for k in [
                    "improvement plan", "pip list", "all pip", "manage pip"
                ]) and "unauthorized" not in pg.lower() and "forbidden" not in pg.lower()
                if has_pip_access and "404" not in pg and "your pip" not in pg.lower() and "my pip" not in pg.lower():
                    pip_violations.append(f"PIP data accessible at {path}")
                    record("RBAC: PIPs", "fail", f"Others' PIPs accessible at {path}")
            except:
                pass

        if not pip_violations:
            record("RBAC: PIPs", "pass", "Cannot access others' PIPs")

        # ── Test 8: Create review cycles (should NOT - admin only) ──
        log("\n[9] RBAC: Create review cycles...")
        cycle_violations = []
        for path in ["/review-cycles", "/cycles", "/admin/cycles", "/create-cycle",
                      "/review-cycle/create", "/admin/review-cycles", "/manage/cycles"]:
            try:
                driver.get(f"{PERF_FRONTEND}{path}")
                wait_for_page(driver)
                pg = get_page_text(driver)
                url = driver.current_url
                log(f"  {path} -> {url[:80]} | text: {pg[:100]}")
                screenshot(driver, f"09_rbac_cycles_{path.replace('/', '_')}")
                can_create = any(k in pg.lower() for k in [
                    "create cycle", "new cycle", "create review", "manage cycle"
                ]) and "unauthorized" not in pg.lower() and "forbidden" not in pg.lower()
                if can_create and "404" not in pg:
                    cycle_violations.append(f"Review cycle management accessible at {path}")
                    record("RBAC: Review Cycles", "fail", f"Admin page accessible at {path}")
            except:
                pass

        if not cycle_violations:
            record("RBAC: Review Cycles", "pass", "Cannot access review cycle management")

        # ── Test 9: 9-Box Grid (should NOT) ──
        log("\n[10] RBAC: 9-Box Grid...")
        grid_violations = []
        for path in ["/9-box", "/nine-box", "/9box", "/admin/9-box", "/analytics/9-box",
                      "/talent-grid", "/nine-box-grid"]:
            try:
                driver.get(f"{PERF_FRONTEND}{path}")
                wait_for_page(driver)
                pg = get_page_text(driver)
                url = driver.current_url
                log(f"  {path} -> {url[:80]} | text: {pg[:100]}")
                screenshot(driver, f"10_rbac_9box_{path.replace('/', '_')}")
                has_grid = any(k in pg.lower() for k in [
                    "9-box", "nine box", "9box", "talent grid", "potential"
                ]) and "unauthorized" not in pg.lower() and "forbidden" not in pg.lower()
                if has_grid and "404" not in pg:
                    grid_violations.append(f"9-Box Grid accessible at {path}")
                    record("RBAC: 9-Box Grid", "fail", f"Accessible at {path}")
            except:
                pass

        if not grid_violations:
            record("RBAC: 9-Box Grid", "pass", "Cannot access 9-Box Grid")

        # ── Test 10: Admin/Settings (should NOT) ──
        log("\n[11] RBAC: Admin/Settings pages...")
        admin_violations = []
        for path in ["/admin", "/settings", "/admin/settings", "/configuration",
                      "/admin/dashboard", "/admin/employees", "/manage", "/admin/config",
                      "/admin/templates", "/templates"]:
            try:
                driver.get(f"{PERF_FRONTEND}{path}")
                wait_for_page(driver)
                pg = get_page_text(driver)
                url = driver.current_url
                log(f"  {path} -> {url[:80]} | text: {pg[:100]}")
                screenshot(driver, f"11_rbac_admin_{path.replace('/', '_')}")
                has_admin = any(k in pg.lower() for k in [
                    "admin dashboard", "settings", "configuration", "manage employee",
                    "template", "admin panel"
                ]) and "unauthorized" not in pg.lower() and "forbidden" not in pg.lower() and "access denied" not in pg.lower()
                # Exclude if it's just user-level settings
                is_user_settings = any(k in pg.lower() for k in ["my settings", "profile", "notification preference"])
                if has_admin and not is_user_settings and "404" not in pg:
                    admin_violations.append(f"Admin page accessible at {path}")
                    record("RBAC: Admin/Settings", "fail", f"Admin page accessible at {path}")
            except:
                pass

        if not admin_violations:
            record("RBAC: Admin/Settings", "pass", "Cannot access admin/settings pages")

        # ── API-level RBAC checks ──
        log("\n[12] API-level RBAC checks...")
        api_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        api_rbac_tests = [
            ("GET", "/api/v1/reviews", "All Reviews API"),
            ("GET", "/api/v1/reviews/all", "All Reviews API (alt)"),
            ("GET", "/api/v1/employees/reviews", "Employee Reviews API"),
            ("GET", "/api/v1/admin/reviews", "Admin Reviews API"),
            ("GET", "/api/v1/review-cycles", "Review Cycles API"),
            ("POST", "/api/v1/review-cycles", "Create Review Cycle API"),
            ("GET", "/api/v1/pip", "PIP List API"),
            ("GET", "/api/v1/pip/all", "All PIP API"),
            ("GET", "/api/v1/9-box", "9-Box API"),
            ("GET", "/api/v1/nine-box", "9-Box API (alt)"),
            ("GET", "/api/v1/admin/settings", "Admin Settings API"),
            ("GET", "/api/v1/analytics", "Analytics API"),
            ("GET", "/api/v1/admin/dashboard", "Admin Dashboard API"),
        ]

        api_violations = []
        for method, path, name in api_rbac_tests:
            try:
                url = f"{PERF_API}{path}"
                if method == "GET":
                    r = requests.get(url, headers=api_headers, timeout=10)
                else:
                    r = requests.post(url, headers=api_headers, json={}, timeout=10)
                log(f"  {method} {path} -> {r.status_code}")
                if r.status_code == 200:
                    body = r.text[:200]
                    # Check if it returns actual data vs empty/error
                    try:
                        jdata = r.json()
                        has_data = bool(jdata.get("data")) or (isinstance(jdata, list) and len(jdata) > 0)
                    except:
                        has_data = False
                    if has_data:
                        api_violations.append(f"{name}: {method} {path} returned data (200)")
                        record(f"API RBAC: {name}", "fail", f"Returned data - possible RBAC violation")
                    else:
                        record(f"API RBAC: {name}", "pass", "200 but no sensitive data returned")
                elif r.status_code in [401, 403, 404]:
                    record(f"API RBAC: {name}", "pass", f"Correctly blocked ({r.status_code})")
                else:
                    record(f"API RBAC: {name}", "info", f"Status {r.status_code}")
            except Exception as e:
                record(f"API RBAC: {name}", "info", f"Error: {e}")

        # ── Employee self-service API checks ──
        log("\n[13] Employee self-service API checks...")
        self_api_tests = [
            ("GET", "/api/v1/my-reviews", "My Reviews API"),
            ("GET", "/api/v1/my-goals", "My Goals API"),
            ("GET", "/api/v1/goals", "Goals API"),
            ("GET", "/api/v1/self-assessment", "Self Assessment API"),
            ("GET", "/api/v1/my-performance", "My Performance API"),
        ]

        for method, path, name in self_api_tests:
            try:
                url = f"{PERF_API}{path}"
                r = requests.get(url, headers=api_headers, timeout=10)
                log(f"  {method} {path} -> {r.status_code} | {r.text[:150]}")
                if r.status_code == 200:
                    record(f"Self API: {name}", "pass", "Accessible")
                elif r.status_code == 404:
                    record(f"Self API: {name}", "info", "Endpoint not found (404)")
                else:
                    record(f"Self API: {name}", "info", f"Status {r.status_code}")
            except Exception as e:
                record(f"Self API: {name}", "info", f"Error: {e}")

        # ── Final dashboard screenshot ──
        log("\n[14] Final screenshots...")
        driver.get(sso_url)
        wait_for_page(driver)
        screenshot(driver, "12_final_dashboard")

        # Try scrolling and capturing full page
        try:
            total_height = driver.execute_script("return document.body.scrollHeight")
            driver.set_window_size(1920, min(total_height + 200, 5000))
            time.sleep(1)
            screenshot(driver, "13_full_page")
        except:
            pass

        # ── File bugs for RBAC violations ──
        log("\n[15] Filing bugs for violations...")
        all_violations = rbac_violations + pip_violations + cycle_violations + grid_violations + admin_violations + api_violations

        if all_violations:
            violation_text = "\n".join(f"- {v}" for v in all_violations)
            existing = check_existing_bug("RBAC violation employee performance")
            if not existing:
                file_bug(
                    "RBAC violations - Employee can access restricted resources",
                    f"**User:** {EMAIL} (Employee role)\n"
                    f"**Module:** Performance\n\n"
                    f"**Violations found:**\n{violation_text}\n\n"
                    f"**Expected:** Employee should only see their own reviews, goals, and self-assessments.\n"
                    f"**Impact:** High - RBAC bypass allows employees to view/manage restricted data.\n\n"
                    f"**Steps:** SSO login as {EMAIL} and navigate to the listed paths."
                )
        else:
            log("  No RBAC violations found - good!")

        # File bugs for missing self-service features
        missing_features = []
        if not found_reviews:
            missing_features.append("My Reviews")
        if not found_goals:
            missing_features.append("My Goals")
        if not found_sa:
            missing_features.append("Self Assessment")

        if missing_features:
            existing = check_existing_bug("employee self-service missing")
            if not existing:
                file_bug(
                    f"Employee self-service pages missing: {', '.join(missing_features)}",
                    f"**User:** {EMAIL} (Employee role)\n"
                    f"**Module:** Performance\n\n"
                    f"**Missing pages:** {', '.join(missing_features)}\n\n"
                    f"**Expected:** Employee should be able to access their own performance data.\n"
                    f"**Actual:** Pages not found or not accessible after SSO login.\n\n"
                    f"**Note:** Tried multiple URL patterns and nav clicks."
                )

    except Exception as e:
        log(f"ERROR: {e}")
        traceback.print_exc()
        try:
            screenshot(driver, "99_error")
        except:
            pass
    finally:
        driver.quit()

    # ── Summary ──
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)
    passes = sum(1 for t in test_results if t["status"] == "pass")
    fails = sum(1 for t in test_results if t["status"] == "fail")
    infos = sum(1 for t in test_results if t["status"] == "info")
    log(f"  PASS: {passes}  |  FAIL: {fails}  |  INFO: {infos}")
    log(f"  Bugs filed: {len(bugs_filed)}")
    for b in bugs_filed:
        log(f"    - {b['title']}: {b['url']}")
    log("")
    for t in test_results:
        status = t['status'].upper().ljust(5)
        log(f"  [{status}] {t['test']}: {t['detail'][:80]}")
    log("=" * 70)


if __name__ == "__main__":
    main()
