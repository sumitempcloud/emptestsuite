"""
RECRUITMENT MODULE - Employee Perspective Testing (priya@technova.in)
Tests: SSO, internal job postings, referrals, internal applications,
       and verifies restricted access to pipeline/feedback/admin.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

# ── Config ──────────────────────────────────────────────────────────────
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_recruit_employee"
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
LOGIN_API = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
RECRUIT_URL = "https://test-recruit.empcloud.com"
RECRUIT_API = "https://test-recruit-api.empcloud.com"
EMAIL = "priya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── Helpers ─────────────────────────────────────────────────────────────
results = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {name}.png")
    return path

def record(test_id, title, status, details=""):
    results.append({"id": test_id, "title": title, "status": status, "details": details})
    icon = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "BUG")
    log(f"  [{icon}] {test_id}: {title} — {details}")

def file_bug(title, body):
    """File a GitHub issue."""
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github+json",
            },
            json={
                "title": f"[Recruit Employee] {title}",
                "body": body,
                "labels": ["bug", "recruitment", "employee"],
            },
            timeout=15,
        )
        if resp.status_code in (201, 200):
            url = resp.json().get("html_url", "")
            log(f"  BUG FILED: {url}")
            return url
        else:
            log(f"  Bug filing failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        log(f"  Bug filing error: {e}")
    return None

def make_driver():
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
    driver.implicitly_wait(3)
    return driver

def wait_for_page(driver, timeout=12):
    """Wait for page to fully load."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        pass
    time.sleep(1.5)

def safe_find_elements(driver, by, value):
    try:
        return driver.find_elements(by, value)
    except Exception:
        return []

def get_page_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text.lower()
    except Exception:
        return ""

# ── STEP 0: Authenticate via API ───────────────────────────────────────
log("=" * 60)
log("RECRUITMENT MODULE — EMPLOYEE TESTING (priya@technova.in)")
log("=" * 60)

log("\n[STEP 0] Authenticating via API...")
token = None
try:
    resp = requests.post(
        LOGIN_API,
        json={"email": EMAIL, "password": PASSWORD},
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    log(f"  Login API status: {resp.status_code}")
    data = resp.json()

    # Try to extract token from various response shapes
    tokens_obj = data.get("data", {}).get("tokens", {})
    token = (
        tokens_obj.get("access_token")
        or tokens_obj.get("token")
        or data.get("token")
        or data.get("data", {}).get("token")
        or data.get("access_token")
        or data.get("data", {}).get("access_token")
        or data.get("result", {}).get("token")
    )

    if token:
        log(f"  Token obtained: {token[:30]}...")
    else:
        log(f"  No token found in response keys: {list(data.keys())}")
        if "data" in data and isinstance(data["data"], dict):
            log(f"  data sub-keys: {list(data['data'].keys())}")
except Exception as e:
    log(f"  Login error: {e}")

# ── STEP 1: SSO into Recruit ───────────────────────────────────────────
driver = make_driver()
try:
    log("\n[TEST 1] SSO into Recruitment module")
    if token:
        sso_url = f"{RECRUIT_URL}?sso_token={token}"
        log(f"  Navigating to SSO URL...")
        driver.get(sso_url)
        wait_for_page(driver, 15)
        screenshot(driver, "01_sso_landing")

        current = driver.current_url
        page_text = get_page_text(driver)
        log(f"  Current URL: {current}")
        log(f"  Page title: {driver.title}")

        # Check for login redirect or error
        is_login_page = any(k in current.lower() for k in ["login", "signin", "auth"])
        has_error = any(k in page_text for k in ["unauthorized", "invalid token", "access denied", "403", "error"])
        has_dashboard = any(k in page_text for k in ["dashboard", "recruit", "jobs", "welcome", "home", "career", "posting", "position"])

        if is_login_page:
            record("T1", "SSO Login", "FAIL", f"Redirected to login page: {current}")
            file_bug(
                "SSO redirect fails for employee — redirected to login",
                f"**Steps:**\n1. Login as {EMAIL} via API\n2. Navigate to `{RECRUIT_URL}?sso_token={{token}}`\n\n"
                f"**Expected:** Land on recruit dashboard as employee\n"
                f"**Actual:** Redirected to login page ({current})\n\n"
                f"**Role:** Employee\n**URL:** {current}"
            )
        elif has_error:
            record("T1", "SSO Login", "FAIL", f"Error displayed on page")
            screenshot(driver, "01_sso_error")
            file_bug(
                "SSO shows error for employee user",
                f"**Steps:**\n1. Login as {EMAIL} via API\n2. Navigate with sso_token\n\n"
                f"**Expected:** Successful SSO login\n**Actual:** Error page\n**URL:** {current}"
            )
        else:
            record("T1", "SSO Login", "PASS", f"Landed on: {current}")
            screenshot(driver, "01_sso_success")
    else:
        record("T1", "SSO Login", "FAIL", "No token obtained from login API")
        # Try direct navigation anyway
        driver.get(RECRUIT_URL)
        wait_for_page(driver)
        screenshot(driver, "01_no_token_direct")

    # ── STEP 2: Check open job postings (internal mobility) ─────────
    log("\n[TEST 2] Can employee see open job postings?")
    time.sleep(2)
    screenshot(driver, "02_current_page_state")
    page_text = get_page_text(driver)

    # Try to find jobs/postings navigation
    job_links_found = False
    for selector_text in ["jobs", "job posting", "openings", "careers", "internal jobs",
                          "positions", "vacancies", "opportunities"]:
        links = safe_find_elements(driver, By.PARTIAL_LINK_TEXT, selector_text.title())
        links += safe_find_elements(driver, By.PARTIAL_LINK_TEXT, selector_text.upper())
        links += safe_find_elements(driver, By.PARTIAL_LINK_TEXT, selector_text)
        if links:
            try:
                links[0].click()
                wait_for_page(driver)
                job_links_found = True
                log(f"  Clicked link containing '{selector_text}'")
                break
            except Exception:
                pass

    if not job_links_found:
        # Try common URL paths
        for path in ["/jobs", "/job-postings", "/openings", "/careers",
                     "/internal-jobs", "/positions", "/employee/jobs"]:
            try:
                driver.get(f"{RECRUIT_URL}{path}")
                wait_for_page(driver)
                txt = get_page_text(driver)
                if "404" not in txt and "not found" not in txt:
                    job_links_found = True
                    log(f"  Found page at {path}")
                    break
            except Exception:
                pass

    screenshot(driver, "02_job_postings")
    page_text = get_page_text(driver)
    has_jobs = any(k in page_text for k in ["job", "position", "opening", "posting",
                                              "vacancy", "career", "apply"])
    if has_jobs:
        record("T2", "View open job postings", "PASS", "Job postings visible to employee")
    else:
        record("T2", "View open job postings", "FAIL",
               "No job postings visible — internal mobility may not be enabled")
        file_bug(
            "Employee cannot view internal job postings",
            f"**Steps:**\n1. SSO as employee {EMAIL}\n2. Look for internal job postings\n\n"
            f"**Expected:** Employee can see open internal job postings for internal mobility\n"
            f"**Actual:** No job postings page or content found\n**URL:** {driver.current_url}"
        )

    # ── STEP 3: Can employee refer someone? ─────────────────────────
    log("\n[TEST 3] Can employee refer someone?")
    referral_found = False
    for selector_text in ["refer", "referral", "recommend"]:
        links = safe_find_elements(driver, By.PARTIAL_LINK_TEXT, selector_text.title())
        links += safe_find_elements(driver, By.PARTIAL_LINK_TEXT, selector_text)
        if links:
            try:
                links[0].click()
                wait_for_page(driver)
                referral_found = True
                log(f"  Clicked referral link")
                break
            except Exception:
                pass

    if not referral_found:
        for path in ["/referrals", "/refer", "/employee/referrals",
                     "/employee/refer", "/referral"]:
            try:
                driver.get(f"{RECRUIT_URL}{path}")
                wait_for_page(driver)
                txt = get_page_text(driver)
                if "404" not in txt and "not found" not in txt:
                    referral_found = True
                    log(f"  Found referral page at {path}")
                    break
            except Exception:
                pass

    screenshot(driver, "03_referral_page")
    page_text = get_page_text(driver)
    has_referral = any(k in page_text for k in ["refer", "referral", "recommend", "nominate"])
    if has_referral:
        record("T3", "Employee referral", "PASS", "Referral feature accessible")
    else:
        record("T3", "Employee referral", "FAIL", "No referral feature found")
        file_bug(
            "Employee cannot access referral feature",
            f"**Steps:**\n1. SSO as {EMAIL}\n2. Navigate to referral section\n\n"
            f"**Expected:** Employee can refer candidates\n"
            f"**Actual:** No referral page/feature found\n**URL:** {driver.current_url}"
        )

    # ── STEP 4: Can employee apply for internal positions? ──────────
    log("\n[TEST 4] Can employee apply for internal positions?")
    apply_found = False
    for path in ["/jobs", "/internal-jobs", "/openings", "/careers",
                 "/employee/jobs", "/positions"]:
        try:
            driver.get(f"{RECRUIT_URL}{path}")
            wait_for_page(driver)
            txt = get_page_text(driver)
            if "404" not in txt and "not found" not in txt and len(txt) > 50:
                # Look for apply button
                apply_btns = safe_find_elements(driver, By.XPATH,
                    "//*[contains(translate(text(),'APPLY','apply'),'apply')]")
                if apply_btns:
                    apply_found = True
                    log(f"  Found apply button(s) at {path}")
                break
        except Exception:
            pass

    screenshot(driver, "04_internal_apply")
    page_text = get_page_text(driver)
    has_apply = any(k in page_text for k in ["apply", "application", "submit resume",
                                               "submit cv", "interested"])
    if has_apply or apply_found:
        record("T4", "Apply for internal positions", "PASS", "Apply option available")
    else:
        record("T4", "Apply for internal positions", "FAIL",
               "No apply option found for internal positions")
        file_bug(
            "Employee cannot apply for internal positions",
            f"**Steps:**\n1. SSO as {EMAIL}\n2. Browse job postings\n3. Try to apply\n\n"
            f"**Expected:** Employee can apply for internal positions\n"
            f"**Actual:** No apply option found\n**URL:** {driver.current_url}"
        )

    # ── STEP 5: Can employee see candidate pipeline? (should NOT) ──
    log("\n[TEST 5] Candidate pipeline access (should be restricted)")
    pipeline_accessible = False
    for path in ["/pipeline", "/candidates", "/candidate-pipeline",
                 "/admin/pipeline", "/hiring/pipeline", "/applicants"]:
        try:
            driver.get(f"{RECRUIT_URL}{path}")
            wait_for_page(driver)
            txt = get_page_text(driver)
            is_blocked = any(k in txt for k in ["unauthorized", "forbidden", "access denied",
                                                  "403", "not authorized", "permission"])
            is_404 = "404" in txt or "not found" in txt
            has_pipeline_data = any(k in txt for k in ["pipeline", "candidate", "applicant",
                                                         "screening", "shortlist", "stage"])
            if has_pipeline_data and not is_blocked and not is_404:
                pipeline_accessible = True
                log(f"  WARNING: Pipeline accessible at {path}!")
                screenshot(driver, f"05_pipeline_exposed_{path.replace('/', '_')}")
                break
        except Exception:
            pass

    screenshot(driver, "05_pipeline_access")
    if pipeline_accessible:
        record("T5", "Candidate pipeline restricted", "FAIL",
               "SECURITY: Employee can access candidate pipeline!")
        file_bug(
            "SECURITY: Employee can access candidate pipeline",
            f"**Severity:** HIGH\n\n"
            f"**Steps:**\n1. SSO as employee {EMAIL}\n2. Navigate to pipeline URL\n\n"
            f"**Expected:** Access denied — employees should NOT see candidate pipeline\n"
            f"**Actual:** Pipeline data is accessible to employee role\n"
            f"**URL:** {driver.current_url}\n\n"
            f"**Security Impact:** Employee can see all candidates and their stages"
        )
    else:
        record("T5", "Candidate pipeline restricted", "PASS",
               "Pipeline not accessible to employee (correct)")

    # ── STEP 6: Can employee see interview feedback? (should NOT) ──
    log("\n[TEST 6] Interview feedback access (should be restricted)")
    feedback_accessible = False
    for path in ["/feedback", "/interview-feedback", "/interviews",
                 "/admin/feedback", "/evaluations", "/scorecards"]:
        try:
            driver.get(f"{RECRUIT_URL}{path}")
            wait_for_page(driver)
            txt = get_page_text(driver)
            is_blocked = any(k in txt for k in ["unauthorized", "forbidden", "access denied",
                                                  "403", "not authorized", "permission"])
            is_404 = "404" in txt or "not found" in txt
            has_feedback = any(k in txt for k in ["feedback", "interview", "evaluation",
                                                    "scorecard", "rating", "review"])
            if has_feedback and not is_blocked and not is_404:
                feedback_accessible = True
                log(f"  WARNING: Feedback accessible at {path}!")
                screenshot(driver, f"06_feedback_exposed_{path.replace('/', '_')}")
                break
        except Exception:
            pass

    screenshot(driver, "06_feedback_access")
    if feedback_accessible:
        record("T6", "Interview feedback restricted", "FAIL",
               "SECURITY: Employee can access interview feedback!")
        file_bug(
            "SECURITY: Employee can access interview feedback",
            f"**Severity:** HIGH\n\n"
            f"**Steps:**\n1. SSO as employee {EMAIL}\n2. Navigate to feedback URL\n\n"
            f"**Expected:** Access denied — employees should NOT see interview feedback\n"
            f"**Actual:** Interview feedback is accessible to employee role\n"
            f"**URL:** {driver.current_url}\n\n"
            f"**Security Impact:** Employee can see confidential interview evaluations"
        )
    else:
        record("T6", "Interview feedback restricted", "PASS",
               "Feedback not accessible to employee (correct)")

    # ── STEP 7: Can employee access admin/settings? (should NOT) ──
    log("\n[TEST 7] Admin/settings access (should be restricted)")
    admin_accessible = False
    for path in ["/admin", "/settings", "/admin/settings", "/admin/dashboard",
                 "/configuration", "/admin/users", "/admin/roles",
                 "/hiring-team", "/admin/jobs"]:
        try:
            driver.get(f"{RECRUIT_URL}{path}")
            wait_for_page(driver)
            txt = get_page_text(driver)
            is_blocked = any(k in txt for k in ["unauthorized", "forbidden", "access denied",
                                                  "403", "not authorized", "permission"])
            is_404 = "404" in txt or "not found" in txt
            is_login = any(k in driver.current_url.lower() for k in ["login", "signin"])
            has_admin = any(k in txt for k in ["settings", "configuration", "admin panel",
                                                 "manage users", "roles", "permissions"])
            if has_admin and not is_blocked and not is_404 and not is_login:
                admin_accessible = True
                log(f"  WARNING: Admin page accessible at {path}!")
                screenshot(driver, f"07_admin_exposed_{path.replace('/', '_')}")
                break
        except Exception:
            pass

    screenshot(driver, "07_admin_access")
    if admin_accessible:
        record("T7", "Admin/settings restricted", "FAIL",
               "SECURITY: Employee can access admin/settings!")
        file_bug(
            "SECURITY: Employee can access admin/settings in Recruit module",
            f"**Severity:** HIGH\n\n"
            f"**Steps:**\n1. SSO as employee {EMAIL}\n2. Navigate to admin/settings URL\n\n"
            f"**Expected:** Access denied — employees should NOT see admin/settings\n"
            f"**Actual:** Admin/settings page is accessible to employee role\n"
            f"**URL:** {driver.current_url}\n\n"
            f"**Security Impact:** Employee can access admin configuration"
        )
    else:
        record("T7", "Admin/settings restricted", "PASS",
               "Admin/settings not accessible to employee (correct)")

    # ── Also test API-level access restrictions ─────────────────────
    log("\n[TEST 7b] API-level access checks")
    if token:
        api_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        restricted_endpoints = [
            ("/api/v1/candidates", "Candidates list"),
            ("/api/v1/pipeline", "Pipeline data"),
            ("/api/v1/interviews/feedback", "Interview feedback"),
            ("/api/v1/admin/settings", "Admin settings"),
            ("/api/v1/jobs/manage", "Job management"),
        ]
        for endpoint, desc in restricted_endpoints:
            try:
                r = requests.get(f"{RECRUIT_API}{endpoint}",
                                 headers=api_headers, timeout=10)
                if r.status_code in (200,) and "error" not in r.text.lower()[:100]:
                    log(f"  WARNING: API {endpoint} returned 200 — {desc}")
                    record(f"T7b-{endpoint}", f"API {desc} restricted", "FAIL",
                           f"API returned 200 for employee")
                else:
                    log(f"  API {endpoint}: {r.status_code} (OK, restricted)")
            except Exception as e:
                log(f"  API {endpoint}: Error — {e}")

    # ── Final screenshot of current state ───────────────────────────
    screenshot(driver, "08_final_state")

except Exception as e:
    log(f"\nFATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    try:
        screenshot(driver, "99_error")
    except Exception:
        pass

finally:
    driver.quit()
    log("\nBrowser closed.")

# ── Summary ─────────────────────────────────────────────────────────────
log("\n" + "=" * 60)
log("TEST RESULTS SUMMARY")
log("=" * 60)
pass_count = sum(1 for r in results if r["status"] == "PASS")
fail_count = sum(1 for r in results if r["status"] == "FAIL")
total = len(results)
for r in results:
    icon = "PASS" if r["status"] == "PASS" else "FAIL"
    log(f"  [{icon}] {r['id']}: {r['title']} — {r['details']}")
log(f"\nTotal: {total} | Passed: {pass_count} | Failed: {fail_count}")
log("Screenshots saved to: " + SCREENSHOT_DIR)
log("=" * 60)
