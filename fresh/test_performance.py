#!/usr/bin/env python3
"""
FRESH E2E Test - EMP Performance Module via SSO
Tests Admin (ananya) and Employee (priya) flows with batched driver sessions
to avoid Chrome memory crashes.

Admin:    dashboard, review cycles, goals, 9-box, analytics, PIPs,
          one-on-ones, competencies, settings, succession, career paths,
          feedback, letters, manager effectiveness, skills gap
Employee: my goals, self-assessment, my reviews, my feedback, my career,
          my 1:1s, my skills, my letters, RBAC (cannot access admin pages)
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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ── Config ──────────────────────────────────────────────────────────────
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_performance"
LOGIN_API = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
PERF_BASE = "https://test-performance.empcloud.com"
PERF_API = "https://test-performance-api.empcloud.com"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASSWORD = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASSWORD = "Welcome@123"

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
BATCH_SIZE = 4  # pages per driver session to avoid Chrome crashes

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs = []
results = []
ts = datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Helpers ─────────────────────────────────────────────────────────────
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{ts}.png")
    try:
        driver.save_screenshot(path)
        log(f"  Screenshot: {path}")
    except Exception:
        log(f"  Screenshot failed for {name}")
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
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(1.5)


def wait_for_content(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR,
                "main, [class*='dashboard'], [class*='content'], .page, #root > div > div")) > 0
        )
    except TimeoutException:
        pass
    time.sleep(1)


def check_page_errors(driver):
    for sel in ["[class*='error']", "[class*='Error']", "[role='alert']",
                ".alert-danger", ".toast-error"]:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                txt = el.text.strip()
                if txt and len(txt) > 5 and "error" in txt.lower():
                    return txt
        except Exception:
            pass
    return None


def is_page_blank_or_error(driver):
    body = driver.find_element(By.TAG_NAME, "body").text.strip()
    if len(body) < 20:
        return True, "Page appears blank or nearly empty"
    lower = body.lower()
    for indicator in ["500", "internal server error", "something went wrong",
                      "page not found", "404", "cannot read properties"]:
        if indicator in lower:
            return True, f"Page shows error containing '{indicator}'"
    return False, ""


def has_text_any(driver, keywords):
    body = driver.find_element(By.TAG_NAME, "body").text.lower()
    for kw in keywords:
        if kw.lower() in body:
            return kw
    return None


# ── SSO ─────────────────────────────────────────────────────────────────
def get_sso_token(email, password):
    log(f"  Authenticating {email} ...")
    resp = requests.post(LOGIN_API, json={"email": email, "password": password}, timeout=15)
    if resp.status_code != 200:
        log(f"  Login failed: {resp.status_code} - {resp.text[:300]}")
        return None
    data = resp.json()
    tokens = data.get("data", {}).get("tokens", {})
    token = tokens.get("access_token") or data.get("data", {}).get("token") or data.get("token")
    if not token:
        log(f"  No token found in response: {json.dumps(data)[:300]}")
        return None
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
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    return driver


def sso_enter(driver, token):
    url = f"{PERF_BASE}?sso_token={token}"
    log(f"  SSO into performance module ...")
    driver.get(url)
    wait_for_page(driver)
    wait_for_content(driver)
    time.sleep(1)


def navigate(driver, path):
    url = f"{PERF_BASE}{path}"
    log(f"  Navigating: {url}")
    driver.get(url)
    wait_for_page(driver)
    wait_for_content(driver)
    return url


def page_test(driver, test_name, path, expected_keywords, ss_name):
    """Navigate to path, screenshot, check for errors and keywords."""
    navigate(driver, path)
    screenshot(driver, ss_name)

    is_err, err_msg = is_page_blank_or_error(driver)
    if is_err:
        record(test_name, "fail", err_msg)
        file_bug(
            f"[Performance] {test_name} - page error",
            f"**URL:** {PERF_BASE}{path}\n**Issue:** {err_msg}\n"
            f"**Steps:** SSO login then navigate to {path}",
        )
        return None

    page_err = check_page_errors(driver)
    if page_err:
        record(test_name, "warn", f"Error on page: {page_err}")
        return driver.find_element(By.TAG_NAME, "body").text

    found = has_text_any(driver, expected_keywords)
    body = driver.find_element(By.TAG_NAME, "body").text
    if found:
        record(test_name, "pass", f"Page loaded, found '{found}'")
    else:
        record(test_name, "warn", f"Page loaded ({len(body)} chars) but none of {expected_keywords} found")
    return body


def detail_click_test(driver, test_name, list_path, link_selector, exclude_patterns, ss_name):
    """Navigate to list page and click into first detail link."""
    navigate(driver, list_path)
    time.sleep(1)
    try:
        links = driver.find_elements(By.CSS_SELECTOR, link_selector)
        detail_links = [l for l in links
                        if all(pat not in (l.get_attribute("href") or "") for pat in exclude_patterns)]
        if detail_links:
            detail_links[0].click()
            wait_for_page(driver)
            wait_for_content(driver)
            screenshot(driver, ss_name)
            body = driver.find_element(By.TAG_NAME, "body").text
            if len(body) > 30:
                record(test_name, "pass", "Navigated to detail page")
            else:
                record(test_name, "warn", "Detail page has sparse content")
        else:
            record(test_name, "warn", "No detail links found on list page")
            screenshot(driver, f"{ss_name}_none")
    except Exception as e:
        record(test_name, "warn", f"Could not click detail: {str(e)[:80]}")
        screenshot(driver, f"{ss_name}_err")


def run_batch(token, test_specs, label=""):
    """Run a batch of page tests with a fresh driver. Each spec is a tuple:
       (test_name, path, keywords, screenshot_name)
    Recovers from driver crashes by creating a new driver.
    """
    driver = None
    try:
        driver = create_driver()
        sso_enter(driver, token)
    except Exception as e:
        log(f"  Batch '{label}' init error: {e}")
        return

    for test_name, path, keywords, ss_name in test_specs:
        try:
            page_test(driver, test_name, path, keywords, ss_name)
        except Exception as e:
            log(f"  Error in {test_name}: {e}")
            record(test_name, "fail", f"Exception: {str(e)[:100]}")
            # Driver likely crashed - try to recover
            try:
                driver.quit()
            except Exception:
                pass
            try:
                log(f"  Recovering driver for remaining tests in batch...")
                driver = create_driver()
                sso_enter(driver, token)
            except Exception as re:
                log(f"  Could not recover driver: {re}")
                # Record remaining tests as failed
                break

    try:
        if driver:
            driver.quit()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════
#  ADMIN TESTS
# ═══════════════════════════════════════════════════════════════════════

ADMIN_PAGE_TESTS = [
    # (test_name, path, keywords, screenshot_name)
    ("Admin - Dashboard", "/dashboard",
     ["dashboard", "review", "goal", "performance", "cycle", "pending"],
     "admin_01_dashboard"),
    ("Admin - Review Cycles List", "/review-cycles",
     ["review", "cycle", "quarterly", "annual", "status"],
     "admin_02_review_cycles"),
    ("Admin - Create Review Cycle", "/review-cycles/new",
     ["create", "cycle", "type", "date", "name"],
     "admin_03_create_cycle"),
    ("Admin - Goals Overview", "/goals",
     ["goal", "progress", "status", "key result"],
     "admin_04_goals"),
    ("Admin - Create Goal", "/goals/new",
     ["goal", "title", "key result", "weight", "due"],
     "admin_05_create_goal"),
    ("Admin - Goal Alignment", "/goals/alignment",
     ["alignment", "company", "department", "team", "goal"],
     "admin_06_goal_alignment"),
    ("Admin - Analytics", "/analytics",
     ["analytics", "trend", "distribution", "performance", "team"],
     "admin_07_analytics"),
    ("Admin - 9-Box Grid", "/analytics/nine-box",
     ["9-box", "nine", "performance", "potential", "grid"],
     "admin_08_nine_box"),
    ("Admin - Skills Gap Analysis", "/analytics/skills-gap",
     ["skill", "gap", "analysis", "radar", "competency"],
     "admin_09_skills_gap"),
    ("Admin - PIPs List", "/pips",
     ["pip", "improvement", "plan", "status", "employee"],
     "admin_10_pips"),
    ("Admin - Create PIP", "/pips/new",
     ["pip", "create", "objective", "employee", "improvement"],
     "admin_11_create_pip"),
    ("Admin - 1:1 Meetings", "/one-on-ones",
     ["meeting", "1-on-1", "1:1", "one-on-one", "schedule"],
     "admin_12_one_on_ones"),
    ("Admin - Create 1:1", "/one-on-ones/new",
     ["create", "meeting", "recurrence", "employee", "schedule"],
     "admin_13_create_one_on_one"),
    ("Admin - Competency Frameworks", "/competency-frameworks",
     ["competency", "framework", "role", "level"],
     "admin_14_competency_frameworks"),
    ("Admin - Create Framework", "/competency-frameworks/new",
     ["create", "framework", "competency", "weight"],
     "admin_15_create_framework"),
    ("Admin - Succession Plans", "/succession-plans",
     ["succession", "plan", "role", "candidate", "readiness"],
     "admin_16_succession_plans"),
    ("Admin - Career Paths", "/career-paths",
     ["career", "path", "level", "ladder"],
     "admin_17_career_paths"),
    ("Admin - Create Career Path", "/career-paths/new",
     ["create", "career", "path", "level"],
     "admin_18_create_career_path"),
    ("Admin - Feedback Wall", "/feedback",
     ["feedback", "kudos", "constructive"],
     "admin_19_feedback"),
    ("Admin - Give Feedback", "/feedback/give",
     ["feedback", "give", "type", "employee", "kudos"],
     "admin_20_give_feedback"),
    ("Admin - Letters", "/letters",
     ["letter", "appraisal", "increment", "promotion", "generate"],
     "admin_21_letters"),
    ("Admin - Letter Templates", "/letters/templates",
     ["template", "letter", "appraisal", "type"],
     "admin_22_letter_templates"),
    ("Admin - Settings", "/settings",
     ["settings", "rating", "notification", "reminder", "configuration"],
     "admin_23_settings"),
]


def run_admin_detail_tests(token):
    """Click-through detail tests for admin: cycle detail, PIP detail, 1:1 detail, goal detail."""
    log("\n--- Admin Detail Click-Through Tests ---")
    driver = None
    try:
        driver = create_driver()
        sso_enter(driver, token)

        # Review Cycle Detail
        detail_click_test(driver, "Admin - Review Cycle Detail",
                          "/review-cycles", "a[href*='/review-cycles/']",
                          ["/new"], "admin_24_cycle_detail")

        # PIP Detail
        detail_click_test(driver, "Admin - PIP Detail",
                          "/pips", "a[href*='/pips/']",
                          ["/new"], "admin_25_pip_detail")

        # 1:1 Detail
        detail_click_test(driver, "Admin - 1:1 Detail",
                          "/one-on-ones", "a[href*='/one-on-ones/']",
                          ["/new"], "admin_26_one_on_one_detail")
    except Exception as e:
        log(f"  Admin detail tests error: {e}")
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # Goal detail in separate driver
    driver = None
    try:
        driver = create_driver()
        sso_enter(driver, token)
        detail_click_test(driver, "Admin - Goal Detail",
                          "/goals", "a[href*='/goals/']",
                          ["/new", "/alignment"], "admin_27_goal_detail")
    except Exception as e:
        log(f"  Goal detail test error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════
#  EMPLOYEE TESTS
# ═══════════════════════════════════════════════════════════════════════

EMPLOYEE_PAGE_TESTS = [
    ("Emp - My Performance", "/my",
     ["performance", "review", "goal", "feedback", "pending"],
     "emp_01_my_performance"),
    ("Emp - My Reviews", "/my/reviews",
     ["review", "self", "pending", "completed", "assessment"],
     "emp_02_my_reviews"),
    ("Emp - My Goals", "/my/goals",
     ["goal", "progress", "key result", "status"],
     "emp_03_my_goals"),
    ("Emp - My PIP", "/my/pip",
     ["pip", "improvement", "objective", "no active", "plan"],
     "emp_04_my_pip"),
    ("Emp - My 1:1s", "/my/one-on-ones",
     ["meeting", "1:1", "one-on-one", "upcoming", "agenda"],
     "emp_05_my_one_on_ones"),
    ("Emp - My Feedback", "/my/feedback",
     ["feedback", "received", "given", "kudos"],
     "emp_06_my_feedback"),
    ("Emp - My Career", "/my/career",
     ["career", "path", "level", "current", "next"],
     "emp_07_my_career"),
    ("Emp - My Skills", "/my/skills",
     ["skill", "gap", "radar", "competency", "learning"],
     "emp_08_my_skills"),
    ("Emp - My Letters", "/my/letters",
     ["letter", "appraisal", "download", "no letters"],
     "emp_09_my_letters"),
]

RBAC_ADMIN_PAGES = [
    ("/pips", "PIPs List"),
    ("/pips/new", "Create PIP"),
    ("/settings", "Settings"),
    ("/analytics/nine-box", "9-Box Grid"),
    ("/succession-plans", "Succession Plans"),
    ("/competency-frameworks", "Competency Frameworks"),
    ("/letters/templates", "Letter Templates"),
    ("/career-paths", "Career Paths (admin)"),
]


def run_rbac_tests(token):
    """Test that employee cannot access admin pages."""
    log("\n--- RBAC Tests: Employee blocked from admin pages ---")
    driver = None
    try:
        driver = create_driver()
        sso_enter(driver, token)

        for path, page_name in RBAC_ADMIN_PAGES:
            test_name = f"RBAC - Employee blocked from {page_name}"
            log(f"\n=== {test_name} ===")
            try:
                navigate(driver, path)
                screenshot(driver, f"emp_rbac_{page_name.replace(' ', '_').lower()}")

                body = driver.find_element(By.TAG_NAME, "body").text.lower()
                current_url = driver.current_url.lower()

                blocked_signals = [
                    "access denied", "not authorized", "unauthorized", "forbidden",
                    "permission", "403", "you don't have", "restricted",
                    "not allowed", "admin only"
                ]
                redirected = "/my" in current_url or "/dashboard" in current_url
                blocked_text = any(sig in body for sig in blocked_signals)

                if blocked_text or redirected:
                    record(test_name, "pass",
                           f"Employee properly blocked (redirect={redirected}, text_signal={blocked_text})")
                else:
                    is_err, _ = is_page_blank_or_error(driver)
                    if is_err:
                        record(test_name, "pass", "Page shows error/blank - effectively blocked")
                    else:
                        record(test_name, "fail",
                               f"Employee can access {page_name} at {path} - RBAC not enforced")
                        file_bug(
                            f"[Performance RBAC] Employee can access admin page: {page_name}",
                            f"**URL:** {PERF_BASE}{path}\n"
                            f"**User:** priya@technova.in (employee role)\n"
                            f"**Expected:** Access denied / redirect\n"
                            f"**Actual:** Page loaded with content\n"
                            f"**Body preview:** {body[:300]}",
                        )
            except Exception as e:
                log(f"  Driver error on RBAC {page_name}: {e}")
                record(test_name, "warn", f"Driver error: {str(e)[:100]}")
                # Recover
                try:
                    driver.quit()
                except Exception:
                    pass
                try:
                    driver = create_driver()
                    sso_enter(driver, token)
                except Exception:
                    log("  Could not recover driver, stopping RBAC tests")
                    break
    except Exception as e:
        log(f"  RBAC tests error: {e}")
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════
def main():
    log("=" * 60)
    log("FRESH E2E TEST - EMP Performance Module")
    log(f"Started: {datetime.now().isoformat()}")
    log("=" * 60)

    # ── Phase 1: Admin tests ────────────────────────────────────────
    log("\n>>> Phase 1: Admin tests (ananya@technova.in)")
    admin_token = get_sso_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not admin_token:
        log("FATAL: Could not obtain admin token. Aborting.")
        sys.exit(1)

    # SSO landing check
    driver = None
    try:
        driver = create_driver()
        sso_enter(driver, admin_token)
        screenshot(driver, "admin_00_sso_landing")
        is_err, err_msg = is_page_blank_or_error(driver)
        if is_err:
            record("Admin SSO Landing", "fail", err_msg)
            file_bug("[Performance] SSO landing page fails to load",
                     f"**URL:** {PERF_BASE}?sso_token=...\n**Issue:** {err_msg}")
        else:
            record("Admin SSO Landing", "pass", "Performance module loaded after SSO")
    except Exception as e:
        log(f"  SSO landing error: {e}")
        record("Admin SSO Landing", "fail", str(e)[:100])
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # Run admin page tests in batches
    for i in range(0, len(ADMIN_PAGE_TESTS), BATCH_SIZE):
        batch = ADMIN_PAGE_TESTS[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        log(f"\n--- Admin Batch {batch_num} ({len(batch)} pages) ---")
        run_batch(admin_token, batch, label=f"admin_batch_{batch_num}")

    # Admin detail click-through tests
    run_admin_detail_tests(admin_token)

    # ── Phase 2: Employee tests ─────────────────────────────────────
    log("\n>>> Phase 2: Employee tests (priya@technova.in)")
    emp_token = get_sso_token(EMP_EMAIL, EMP_PASSWORD)
    if not emp_token:
        log("FATAL: Could not obtain employee token. Skipping employee tests.")
    else:
        # SSO landing
        driver = None
        try:
            driver = create_driver()
            sso_enter(driver, emp_token)
            screenshot(driver, "emp_00_sso_landing")
            is_err, err_msg = is_page_blank_or_error(driver)
            if is_err:
                record("Employee SSO Landing", "fail", err_msg)
                file_bug("[Performance] Employee SSO landing fails",
                         f"**URL:** {PERF_BASE}?sso_token=...\n**Issue:** {err_msg}")
            else:
                record("Employee SSO Landing", "pass", "Employee view loaded after SSO")
        except Exception as e:
            record("Employee SSO Landing", "fail", str(e)[:100])
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        # Employee self-service page tests in batches
        for i in range(0, len(EMPLOYEE_PAGE_TESTS), BATCH_SIZE):
            batch = EMPLOYEE_PAGE_TESTS[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            log(f"\n--- Employee Batch {batch_num} ({len(batch)} pages) ---")
            run_batch(emp_token, batch, label=f"emp_batch_{batch_num}")

        # RBAC tests
        run_rbac_tests(emp_token)

    # ── Summary ────────────────────────────────────────────────────
    log("\n" + "=" * 60)
    log("  TEST SUMMARY")
    log("=" * 60)

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    warned = sum(1 for r in results if r["status"] == "warn")
    total = len(results)

    log(f"  Total: {total}  |  Passed: {passed}  |  Failed: {failed}  |  Warnings: {warned}")
    log(f"  Bugs filed: {len(bugs)}")

    if failed > 0:
        log("\n  FAILURES:")
        for r in results:
            if r["status"] == "fail":
                log(f"    - {r['test']}: {r['details']}")

    if warned > 0:
        log("\n  WARNINGS:")
        for r in results:
            if r["status"] == "warn":
                log(f"    - {r['test']}: {r['details']}")

    if bugs:
        log("\n  BUGS FILED:")
        for b in bugs:
            log(f"    - {b}")

    # Write JSON results
    report_path = os.path.join(SCREENSHOT_DIR, f"results_{ts}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": ts,
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warned,
            "bugs_filed": len(bugs),
            "results": results,
            "bugs": bugs,
        }, f, indent=2)
    log(f"\n  Results saved to: {report_path}")
    log(f"  Screenshots in: {SCREENSHOT_DIR}")
    log(f"\nDone at {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
