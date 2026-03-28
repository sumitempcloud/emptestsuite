"""
EMP Exit Management Module - Comprehensive SSO Test
Tests: dashboard, exits, clearance, fnf, interviews, analytics, alumni, settings, checklists
Also: initiate exit, clearance workflow, F&F settlement
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
import json
import os
from datetime import datetime

# --- Selenium setup ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_exit"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

LOGIN_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
EXIT_BASE = "https://test-exit.empcloud.com"
EXIT_API = "https://test-exit-api.empcloud.com/api/v1"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

bugs = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot saved: {name}.png")
    return path

def file_bug(title, body):
    bugs.append(title)
    log(f"  BUG: {title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github+json"
            },
            json={"title": title, "body": body, "labels": ["bug", "exit"]}
        )
        if resp.status_code == 201:
            log(f"  Filed issue #{resp.json()['number']}: {title}")
        else:
            log(f"  Failed to file issue ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        log(f"  Error filing bug: {e}")

# ============================
# STEP 1: SSO Login
# ============================
def get_sso_token():
    log("Logging in via API to get SSO token...")
    resp = requests.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200:
        log(f"  Login failed: {resp.status_code} - {resp.text[:300]}")
        sys.exit(1)
    data = resp.json()
    token = (
        data.get("data", {}).get("tokens", {}).get("access_token")
        or data.get("data", {}).get("token")
        or data.get("token")
    )
    if not token:
        log(f"  No token in response: {json.dumps(data)[:300]}")
        sys.exit(1)
    log(f"  Got SSO token: {token[:30]}...")
    return token

def create_driver():
    opts = Options()
    opts.binary_location = CHROME_PATH
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
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

def check_page_errors(driver, page_name):
    """Check for common error indicators on the page."""
    page_src = driver.page_source.lower() if driver.page_source else ""
    title = driver.title or ""

    # Check for error states
    error_indicators = [
        ("500", "Internal Server Error"),
        ("404", "Page Not Found"),
        ("403", "Forbidden / Access Denied"),
        ("error", "Error displayed on page"),
        ("something went wrong", "Something went wrong error"),
    ]

    for indicator, desc in error_indicators:
        if indicator in page_src and "error-boundary" not in page_src:
            # Check it's a real error, not just the word in normal content
            if indicator in ("500", "404", "403"):
                if f"<h1>{indicator}</h1>" in page_src or f"status {indicator}" in page_src or f"error {indicator}" in page_src:
                    return desc
            elif indicator == "something went wrong":
                return desc

    # Check for blank page
    body_text = ""
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body_text = body.text.strip()
    except:
        pass

    if len(body_text) < 10 and "login" not in page_src:
        return "Page appears blank/empty"

    return None

# ============================
# STEP 2: Navigate pages
# ============================
PAGES_TO_TEST = [
    ("dashboard", "/dashboard", "Exit Dashboard"),
    ("exits_list", "/exits", "Exit List"),
    ("clearance", "/clearance", "Clearance Config"),
    ("fnf", "/fnf", "F&F Management"),
    ("interviews", "/interviews", "Interview Templates"),
    ("analytics", "/analytics", "Exit Analytics"),
    ("alumni", "/alumni", "Alumni Directory"),
    ("settings", "/settings", "Exit Settings"),
    ("checklists", "/checklists", "Checklist Templates"),
    ("letters", "/letters", "Letter Templates"),
    ("rehire", "/rehire", "Rehire Management"),
    ("buyout", "/buyout", "Notice Buyout"),
    ("assets", "/assets", "Asset Returns"),
    ("self_service", "/my", "Self-Service Dashboard"),
    ("my_exit", "/my/exit", "My Exit"),
]

def test_all_pages(driver, token):
    log("\n=== TESTING ALL EXIT PAGES ===")
    results = {}

    for slug, path, label in PAGES_TO_TEST:
        log(f"\nNavigating to {label} ({path})...")
        try:
            url = f"{EXIT_BASE}{path}"
            if "?" in url:
                url += f"&sso_token={token}"
            else:
                url += f"?sso_token={token}"

            driver.get(url)
            wait_for_page(driver)

            # Take screenshot
            screenshot(driver, slug)

            # Check for errors
            error = check_page_errors(driver, label)
            if error:
                log(f"  ISSUE on {label}: {error}")
                file_bug(
                    f"[Exit] {label} page: {error}",
                    f"**Page**: `{path}`\n**URL**: `{url}`\n**Error**: {error}\n\n"
                    f"**Steps**:\n1. SSO login to Exit module\n2. Navigate to `{path}`\n3. Observe: {error}\n\n"
                    f"**Expected**: Page loads correctly with content.\n"
                    f"**Browser**: Chrome headless 1920x1080"
                )
                results[slug] = f"FAIL - {error}"
            else:
                log(f"  {label} loaded OK")
                results[slug] = "PASS"

        except Exception as e:
            log(f"  ERROR on {label}: {e}")
            try:
                screenshot(driver, f"{slug}_error")
            except:
                pass
            results[slug] = f"ERROR - {str(e)[:100]}"

    return results

# ============================
# STEP 3: Initiate an Exit
# ============================
def test_initiate_exit(driver, token):
    log("\n=== TEST: INITIATE EXIT ===")
    try:
        url = f"{EXIT_BASE}/exits/new?sso_token={token}"
        driver.get(url)
        wait_for_page(driver)
        screenshot(driver, "initiate_exit_form")

        error = check_page_errors(driver, "Initiate Exit")
        if error:
            log(f"  Initiate Exit page error: {error}")
            file_bug(
                f"[Exit] Initiate Exit form: {error}",
                f"**Page**: `/exits/new`\n**Error**: {error}\n\n"
                f"**Steps**:\n1. SSO login\n2. Navigate to /exits/new\n3. Observe: {error}\n\n"
                f"**Expected**: Exit initiation form loads with employee select, exit type, dates, reason fields."
            )
            return "FAIL"

        # Check for form elements
        page_src = driver.page_source.lower()
        form_indicators = ["employee", "type", "date", "reason", "resign", "terminat"]
        found = [f for f in form_indicators if f in page_src]
        log(f"  Form elements found: {found}")

        if len(found) < 2:
            log("  WARNING: Form may not have loaded fully")
            file_bug(
                "[Exit] Initiate Exit form may not render properly",
                "**Page**: `/exits/new`\n"
                f"**Found keywords**: {found}\n"
                "**Expected**: Form with employee select, exit type (resignation/termination/retirement/contract end), "
                "dates, reason fields."
            )
            return "WARN"

        # Try to interact with form - look for select/input elements
        try:
            selects = driver.find_elements(By.TAG_NAME, "select")
            inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea")
            buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button")
            log(f"  Found: {len(selects)} selects, {len(inputs)} inputs, {len(buttons)} buttons")
        except:
            pass

        log("  Initiate exit form loaded")
        return "PASS"

    except Exception as e:
        log(f"  ERROR: {e}")
        try:
            screenshot(driver, "initiate_exit_error")
        except:
            pass
        return f"ERROR - {e}"

# ============================
# STEP 4: Test Clearance Workflow
# ============================
def test_clearance_workflow(driver, token):
    log("\n=== TEST: CLEARANCE WORKFLOW ===")
    try:
        # Visit clearance config page
        url = f"{EXIT_BASE}/clearance?sso_token={token}"
        driver.get(url)
        wait_for_page(driver)
        screenshot(driver, "clearance_config")

        page_src = driver.page_source.lower()
        clearance_keywords = ["clearance", "department", "it", "finance", "hr", "admin", "manager", "approve", "pending"]
        found = [k for k in clearance_keywords if k in page_src]
        log(f"  Clearance keywords found: {found}")

        error = check_page_errors(driver, "Clearance")
        if error:
            file_bug(
                f"[Exit] Clearance config page: {error}",
                f"**Page**: `/clearance`\n**Error**: {error}\n\n"
                f"**Expected**: Clearance department configuration with IT, Finance, HR, Admin, Manager departments."
            )
            return "FAIL"

        # Try "my clearances" via API
        log("  Checking clearance API endpoints...")
        headers = {"Authorization": f"Bearer {token}"}

        # Try clearance departments
        try:
            resp = requests.get(f"{EXIT_API}/clearance-departments", headers=headers, timeout=10)
            log(f"  GET /clearance-departments: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                log(f"    Response: {json.dumps(data)[:300]}")
        except Exception as e:
            log(f"  API error: {e}")

        # Try my clearances
        try:
            resp = requests.get(f"{EXIT_API}/my-clearances", headers=headers, timeout=10)
            log(f"  GET /my-clearances: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                log(f"    Response: {json.dumps(data)[:300]}")
        except Exception as e:
            log(f"  API error: {e}")

        return "PASS"

    except Exception as e:
        log(f"  ERROR: {e}")
        return f"ERROR - {e}"

# ============================
# STEP 5: Test F&F Settlement
# ============================
def test_fnf_settlement(driver, token):
    log("\n=== TEST: F&F SETTLEMENT ===")
    try:
        url = f"{EXIT_BASE}/fnf?sso_token={token}"
        driver.get(url)
        wait_for_page(driver)
        screenshot(driver, "fnf_management")

        page_src = driver.page_source.lower()
        fnf_keywords = ["settlement", "salary", "leave", "gratuity", "deduction", "payable", "pending", "approved", "paid"]
        found = [k for k in fnf_keywords if k in page_src]
        log(f"  F&F keywords found: {found}")

        error = check_page_errors(driver, "F&F Settlement")
        if error:
            file_bug(
                f"[Exit] F&F Settlement page: {error}",
                f"**Page**: `/fnf`\n**Error**: {error}\n\n"
                f"**Expected**: Full & Final settlement management page showing pending salary, "
                f"leave encashment, gratuity, deductions, notice recovery."
            )
            return "FAIL"

        return "PASS"

    except Exception as e:
        log(f"  ERROR: {e}")
        return f"ERROR - {e}"

# ============================
# STEP 6: API Tests
# ============================
def test_exit_apis(token):
    log("\n=== API ENDPOINT TESTS ===")
    headers = {"Authorization": f"Bearer {token}"}
    results = {}

    endpoints = [
        ("GET", "/exits", "List exits"),
        ("GET", "/checklist-templates", "Checklist templates"),
        ("GET", "/clearance-departments", "Clearance departments"),
        ("GET", "/interview-templates", "Interview templates"),
        ("GET", "/letter-templates", "Letter templates"),
        ("GET", "/predictions/dashboard", "Flight risk dashboard"),
        ("GET", "/predictions/high-risk", "High risk employees"),
        ("GET", "/predictions/trends", "Attrition trends"),
        ("GET", "/nps/scores", "NPS scores"),
        ("GET", "/nps/trends", "NPS trends"),
        ("GET", "/nps/responses", "NPS responses"),
        ("GET", "/rehire", "Rehire list"),
        ("GET", "/rehire/eligible", "Rehire eligible"),
        ("GET", "/email-templates", "Email templates"),
        ("GET", "/self-service/my-exit", "My exit (self-service)"),
        ("GET", "/self-service/my-checklist", "My checklist (self-service)"),
        ("GET", "/health", "Health check"),
    ]

    for method, path, label in endpoints:
        try:
            url = f"{EXIT_API}{path}"
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            else:
                resp = requests.post(url, headers=headers, json={}, timeout=10)

            status = resp.status_code
            log(f"  {method} {path}: {status}")

            if status == 200:
                try:
                    data = resp.json()
                    log(f"    Preview: {json.dumps(data)[:200]}")
                except:
                    pass
                results[path] = "PASS"
            elif status in (401, 403):
                results[path] = f"AUTH-{status}"
            elif status == 404:
                results[path] = "NOT FOUND"
                file_bug(
                    f"[Exit] API {path} returns 404",
                    f"**Endpoint**: `{method} {path}`\n**Status**: 404\n\n"
                    f"**Expected**: Endpoint should exist per README docs."
                )
            elif status >= 500:
                results[path] = f"SERVER ERROR {status}"
                file_bug(
                    f"[Exit] API {path} returns {status}",
                    f"**Endpoint**: `{method} {path}`\n**Status**: {status}\n"
                    f"**Response**: {resp.text[:300]}\n\n"
                    f"**Expected**: Endpoint should return valid response."
                )
            else:
                results[path] = f"HTTP {status}"
        except requests.exceptions.Timeout:
            log(f"  {method} {path}: TIMEOUT")
            results[path] = "TIMEOUT"
        except Exception as e:
            log(f"  {method} {path}: ERROR - {e}")
            results[path] = f"ERROR"

    return results

# ============================
# STEP 7: Test exit detail page (if exits exist)
# ============================
def test_exit_detail(driver, token):
    log("\n=== TEST: EXIT DETAIL PAGE ===")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(f"{EXIT_API}/exits", headers=headers, timeout=10)
        if resp.status_code != 200:
            log(f"  Cannot fetch exits list: {resp.status_code}")
            return "SKIP"

        data = resp.json()
        exits = data.get("data", data) if isinstance(data, dict) else data
        if isinstance(exits, dict):
            exits = exits.get("exits", exits.get("rows", exits.get("items", [])))
        if not isinstance(exits, list) or len(exits) == 0:
            log("  No exits found to test detail page")
            return "SKIP - no exits"

        exit_item = exits[0]
        exit_id = exit_item.get("id") or exit_item.get("exit_id")
        log(f"  Testing exit detail for ID: {exit_id}")

        url = f"{EXIT_BASE}/exits/{exit_id}?sso_token={token}"
        driver.get(url)
        wait_for_page(driver)
        screenshot(driver, "exit_detail")

        error = check_page_errors(driver, "Exit Detail")
        if error:
            file_bug(
                f"[Exit] Exit detail page: {error}",
                f"**Page**: `/exits/{exit_id}`\n**Error**: {error}\n\n"
                f"**Expected**: Exit detail with tabs for Overview, Checklist, Clearance, Interview, F&F, Assets, KT, Letters, Buyout."
            )
            return "FAIL"

        # Check tabs
        page_src = driver.page_source.lower()
        tabs = ["overview", "checklist", "clearance", "interview", "settlement", "assets", "knowledge", "letter", "buyout"]
        found_tabs = [t for t in tabs if t in page_src]
        log(f"  Detail tabs found: {found_tabs}")

        # Also test clearance for this exit
        try:
            resp2 = requests.get(f"{EXIT_API}/exits/{exit_id}/clearance", headers=headers, timeout=10)
            log(f"  GET /exits/{exit_id}/clearance: {resp2.status_code}")
            if resp2.status_code == 200:
                log(f"    Clearance: {json.dumps(resp2.json())[:200]}")
        except:
            pass

        # Test F&F for this exit
        try:
            resp3 = requests.get(f"{EXIT_API}/exits/{exit_id}/fnf", headers=headers, timeout=10)
            log(f"  GET /exits/{exit_id}/fnf: {resp3.status_code}")
            if resp3.status_code == 200:
                log(f"    F&F: {json.dumps(resp3.json())[:200]}")
        except:
            pass

        # Test assets for this exit
        try:
            resp4 = requests.get(f"{EXIT_API}/exits/{exit_id}/assets", headers=headers, timeout=10)
            log(f"  GET /exits/{exit_id}/assets: {resp4.status_code}")
        except:
            pass

        return "PASS"

    except Exception as e:
        log(f"  ERROR: {e}")
        return f"ERROR - {e}"

# ============================
# STEP 8: Additional page tests
# ============================
def test_additional_pages(driver, token):
    log("\n=== ADDITIONAL PAGE TESTS ===")
    extra_pages = [
        ("predictions", "/predictions", "Flight Risk / Attrition"),
        ("nps", "/nps", "NPS Dashboard"),
        ("email_templates", "/email-templates", "Email Templates"),
        ("my_interview", "/my/exit/interview", "My Exit Interview"),
        ("my_kt", "/my/exit/kt", "My Knowledge Transfer"),
        ("my_buyout", "/my/exit/buyout", "My Buyout"),
        ("my_nps", "/my/exit/nps", "My NPS Survey"),
        ("my_letters", "/my/exit/letters", "My Letters"),
        ("my_alumni", "/my/alumni", "My Alumni Profile"),
    ]

    results = {}
    for slug, path, label in extra_pages:
        try:
            url = f"{EXIT_BASE}{path}?sso_token={token}"
            driver.get(url)
            wait_for_page(driver)
            screenshot(driver, slug)

            error = check_page_errors(driver, label)
            if error:
                log(f"  {label}: {error}")
                results[slug] = f"FAIL - {error}"
            else:
                log(f"  {label}: OK")
                results[slug] = "PASS"
        except Exception as e:
            log(f"  {label}: ERROR - {e}")
            results[slug] = f"ERROR"

    return results

# ============================
# MAIN
# ============================
def main():
    log("=" * 60)
    log("EMP EXIT MODULE - COMPREHENSIVE SSO TEST")
    log("=" * 60)

    # Step 1: Get token
    token = get_sso_token()

    # Step 2: Create browser
    driver = create_driver()

    all_results = {}

    try:
        # Step 3: SSO into Exit module & screenshot dashboard
        log("\n=== SSO INTO EXIT MODULE ===")
        sso_url = f"{EXIT_BASE}?sso_token={token}"
        driver.get(sso_url)
        wait_for_page(driver, timeout=15)
        screenshot(driver, "sso_landing")
        log(f"  Page title: {driver.title}")
        log(f"  Current URL: {driver.current_url}")

        # Step 4: Test all main pages
        page_results = test_all_pages(driver, token)
        all_results["pages"] = page_results

        # Step 5: Test initiate exit
        all_results["initiate_exit"] = test_initiate_exit(driver, token)

        # Step 6: Test clearance workflow
        all_results["clearance_workflow"] = test_clearance_workflow(driver, token)

        # Step 7: Test F&F settlement
        all_results["fnf_settlement"] = test_fnf_settlement(driver, token)

        # Step 8: Test exit detail
        all_results["exit_detail"] = test_exit_detail(driver, token)

        # Step 9: Test additional pages
        extra_results = test_additional_pages(driver, token)
        all_results["extra_pages"] = extra_results

        # Step 10: API tests
        api_results = test_exit_apis(token)
        all_results["api"] = api_results

    finally:
        driver.quit()

    # ============================
    # SUMMARY
    # ============================
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)

    # Pages
    log("\n--- Page Tests ---")
    if "pages" in all_results:
        for k, v in all_results["pages"].items():
            status = "PASS" if v == "PASS" else "FAIL"
            log(f"  [{status}] {k}: {v}")

    if "extra_pages" in all_results:
        for k, v in all_results["extra_pages"].items():
            status = "PASS" if v == "PASS" else "FAIL"
            log(f"  [{status}] {k}: {v}")

    log(f"\n  Initiate Exit: {all_results.get('initiate_exit', 'N/A')}")
    log(f"  Clearance Workflow: {all_results.get('clearance_workflow', 'N/A')}")
    log(f"  F&F Settlement: {all_results.get('fnf_settlement', 'N/A')}")
    log(f"  Exit Detail: {all_results.get('exit_detail', 'N/A')}")

    # API
    log("\n--- API Tests ---")
    if "api" in all_results:
        for k, v in all_results["api"].items():
            status = "PASS" if v == "PASS" else "FAIL"
            log(f"  [{status}] {k}: {v}")

    # Bugs
    log(f"\n--- Bugs Filed: {len(bugs)} ---")
    for b in bugs:
        log(f"  - {b}")

    # Counts
    total_pass = 0
    total_fail = 0
    for section in ["pages", "extra_pages", "api"]:
        if section in all_results and isinstance(all_results[section], dict):
            for v in all_results[section].values():
                if v == "PASS":
                    total_pass += 1
                else:
                    total_fail += 1

    for key in ["initiate_exit", "clearance_workflow", "fnf_settlement", "exit_detail"]:
        val = all_results.get(key, "")
        if val == "PASS":
            total_pass += 1
        elif "SKIP" not in str(val):
            total_fail += 1

    log(f"\nTOTAL: {total_pass} passed, {total_fail} failed, {len(bugs)} bugs filed")
    log("=" * 60)

if __name__ == "__main__":
    main()
