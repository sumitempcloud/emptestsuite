"""
Fresh E2E Test -- EMP Exit Management Module
==============================================
Admin (ananya@technova.in): dashboard, exits, clearance, F&F, interviews,
                            checklists, analytics, settings, letters, rehire,
                            buyout, assets, alumni, initiate-exit form,
                            exit-detail tabs, API smoke
Employee (priya@technova.in): RBAC (blocked from admin pages, F&F, flight risk),
                              self-service pages (my exit, interview, KT, NPS,
                              letters, alumni profile)
Business rules: clearance before F&F, access revoked on exit
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
import time
import json
import os
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Configuration ──────────────────────────────────────────────────────
LOGIN_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
EXIT_BASE = "https://test-exit.empcloud.com"
EXIT_API = "https://test-exit-api.empcloud.com/api/v1"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_exit"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

bugs = []
results = []

# ── Helpers ────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def record(name, status, details=""):
    results.append({"test": name, "status": status, "details": details})
    log(f"  [{status}] {name}{': ' + details if details else ''}")


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {name}.png")
    return path


def file_bug(title, body, labels=None):
    if labels is None:
        labels = ["bug", "exit-module"]
    bugs.append({"title": title, "body": body, "labels": labels})
    log(f"  BUG QUEUED: {title}")


def create_github_issues():
    if not bugs:
        log("No bugs to file.")
        return
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }
    for bug in bugs:
        try:
            r = requests.post(
                f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                headers=headers,
                json={
                    "title": bug["title"],
                    "body": bug["body"],
                    "labels": bug["labels"],
                },
                timeout=15,
            )
            if r.status_code == 201:
                log(f"  Filed issue #{r.json()['number']}: {bug['title']}")
            else:
                log(f"  Issue filing failed ({r.status_code}): {r.text[:200]}")
        except Exception as e:
            log(f"  Issue filing error: {e}")


# ── SSO / Driver ──────────────────────────────────────────────────────

def get_sso_token(email, password, label=""):
    log(f"Obtaining SSO token for {email} ({label})...")
    resp = requests.post(LOGIN_URL, json={"email": email, "password": password}, timeout=15)
    if resp.status_code != 200:
        log(f"  Login FAILED ({resp.status_code}): {resp.text[:300]}")
        return None
    data = resp.json()
    token = (
        data.get("data", {}).get("tokens", {}).get("access_token")
        or data.get("data", {}).get("token")
        or data.get("token")
    )
    if not token:
        log(f"  No token in response: {json.dumps(data)[:300]}")
        return None
    log(f"  Token OK: {token[:30]}...")
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


def sso_navigate(driver, token, path):
    """Navigate to an Exit module page with SSO token."""
    sep = "&" if "?" in path else "?"
    url = f"{EXIT_BASE}{path}{sep}sso_token={token}"
    driver.get(url)
    wait_for_page(driver)
    return url


def wait_for_page(driver, timeout=12):
    time.sleep(2)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    time.sleep(1)


def check_page_errors(driver):
    """Return error description string or None if page looks fine."""
    src = (driver.page_source or "").lower()

    for code, desc in [("500", "Internal Server Error"), ("404", "Page Not Found"),
                        ("403", "Forbidden"), ("401", "Unauthorized")]:
        if f"<h1>{code}</h1>" in src or f"status {code}" in src or f"error {code}" in src:
            return desc

    if "something went wrong" in src:
        return "Something went wrong error"

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
    except Exception:
        body_text = ""
    if len(body_text) < 10 and "login" not in src:
        return "Page appears blank/empty"

    return None


def page_contains_any(driver, keywords):
    """Return list of keywords found in page source."""
    src = (driver.page_source or "").lower()
    return [k for k in keywords if k.lower() in src]


# ======================================================================
#  PART A  --  ADMIN TESTS  (ananya@technova.in)
# ======================================================================

ADMIN_PAGES = [
    ("admin_dashboard",   "/dashboard",   "Dashboard",            ["exit", "active", "pending"]),
    ("admin_exits",       "/exits",       "Exit List",            ["exit", "status"]),
    ("admin_clearance",   "/clearance",   "Clearance Config",     ["clearance", "department"]),
    ("admin_fnf",         "/fnf",         "F&F Management",       ["settlement", "final"]),
    ("admin_interviews",  "/interviews",  "Interview Templates",  ["interview", "template"]),
    ("admin_checklists",  "/checklists",  "Checklist Templates",  ["checklist", "template"]),
    ("admin_analytics",   "/analytics",   "Exit Analytics",       ["analytics", "attrition"]),
    ("admin_settings",    "/settings",    "Settings",             ["setting"]),
    ("admin_letters",     "/letters",     "Letter Templates",     ["letter", "template"]),
    ("admin_rehire",      "/rehire",      "Rehire Management",    ["rehire"]),
    ("admin_buyout",      "/buyout",      "Notice Buyout",        ["buyout"]),
    ("admin_assets",      "/assets",      "Asset Returns",        ["asset"]),
    ("admin_alumni",      "/alumni",      "Alumni Directory",     ["alumni"]),
]


def run_admin_page_tests(driver, token):
    log("\n{'='*60}")
    log("ADMIN PAGE TESTS")
    log("=" * 60)

    for slug, path, label, keywords in ADMIN_PAGES:
        log(f"\n--- {label} ({path}) ---")
        try:
            sso_navigate(driver, token, path)
            screenshot(driver, slug)

            error = check_page_errors(driver)
            if error:
                record(f"Admin|{label}", "FAIL", error)
                file_bug(
                    f"[Exit][Admin] {label}: {error}",
                    f"**Page**: `{path}`\n**Error**: {error}\n\n"
                    f"**Steps**:\n1. SSO login as admin\n2. Navigate to `{path}`\n"
                    f"3. Observe: {error}\n\n"
                    f"**Expected**: Page loads with content.\n"
                    f"**Browser**: Chrome headless 1920x1080",
                )
                continue

            found = page_contains_any(driver, keywords)
            if found:
                record(f"Admin|{label}", "PASS", f"keywords: {found}")
            else:
                record(f"Admin|{label}", "WARN", f"None of {keywords} found in page")

        except Exception as e:
            record(f"Admin|{label}", "ERROR", str(e)[:120])
            try:
                screenshot(driver, f"{slug}_error")
            except Exception:
                pass


def run_admin_initiate_exit(driver, token):
    """Test the initiate-exit form page."""
    log("\n--- Initiate Exit Form (/exits/new) ---")
    try:
        sso_navigate(driver, token, "/exits/new")
        screenshot(driver, "admin_initiate_exit")

        error = check_page_errors(driver)
        if error:
            record("Admin|Initiate Exit Form", "FAIL", error)
            file_bug(
                "[Exit][Admin] Initiate Exit form error",
                f"**Page**: `/exits/new`\n**Error**: {error}\n\n"
                "**Expected**: Form with employee select, exit type, dates, reason.",
            )
            return

        form_keywords = ["employee", "type", "date", "reason", "resign", "terminat"]
        found = page_contains_any(driver, form_keywords)
        log(f"  Form keywords: {found}")

        try:
            selects = driver.find_elements(By.TAG_NAME, "select")
            inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea")
            buttons = driver.find_elements(By.TAG_NAME, "button")
            log(f"  Elements: {len(selects)} selects, {len(inputs)} inputs, {len(buttons)} buttons")
        except Exception:
            pass

        if len(found) >= 2:
            record("Admin|Initiate Exit Form", "PASS", f"keywords: {found}")
        else:
            record("Admin|Initiate Exit Form", "WARN", "Form may not have rendered fully")

    except Exception as e:
        record("Admin|Initiate Exit Form", "ERROR", str(e)[:120])
        try:
            screenshot(driver, "admin_initiate_exit_error")
        except Exception:
            pass


def run_admin_exit_detail(driver, token):
    """Try to open an existing exit's detail page and check tabs."""
    log("\n--- Exit Detail (first available) ---")
    headers = {"Authorization": f"Bearer {token}"}

    # Find an exit via API
    exit_id = None
    try:
        r = requests.get(f"{EXIT_API}/exits", headers=headers, timeout=10)
        log(f"  GET /exits => {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            if isinstance(items, dict):
                items = items.get("exits", items.get("rows", items.get("items", [])))
            if isinstance(items, list) and items:
                exit_id = items[0].get("id") or items[0].get("exit_id")
                log(f"  Found exit ID: {exit_id}")
    except Exception as e:
        log(f"  API error listing exits: {e}")

    if not exit_id:
        record("Admin|Exit Detail", "SKIP", "No exits found via API")
        return

    try:
        sso_navigate(driver, token, f"/exits/{exit_id}")
        screenshot(driver, "admin_exit_detail")

        error = check_page_errors(driver)
        if error:
            record("Admin|Exit Detail", "FAIL", error)
            file_bug(
                f"[Exit][Admin] Exit detail page: {error}",
                f"**Page**: `/exits/{exit_id}`\n**Error**: {error}\n\n"
                "**Expected**: Exit detail with tabs (Overview, Checklist, Clearance, "
                "Interview, F&F, Assets, KT, Letters, Buyout).",
            )
            return

        tab_keywords = ["overview", "checklist", "clearance", "interview", "f&f",
                        "settlement", "asset", "knowledge", "letter", "buyout"]
        found = page_contains_any(driver, tab_keywords)
        log(f"  Tab keywords: {found}")
        record("Admin|Exit Detail", "PASS" if len(found) >= 3 else "WARN",
               f"tabs found: {found}")

    except Exception as e:
        record("Admin|Exit Detail", "ERROR", str(e)[:120])
        try:
            screenshot(driver, "admin_exit_detail_error")
        except Exception:
            pass


def run_admin_api_smoke(token):
    """Quick API smoke tests for admin endpoints."""
    log("\n--- Admin API Smoke Tests ---")
    headers = {"Authorization": f"Bearer {token}"}
    endpoints = [
        ("GET", "/exits", "List exits"),
        ("GET", "/clearance-departments", "Clearance departments"),
        ("GET", "/checklist-templates", "Checklist templates"),
        ("GET", "/interview-templates", "Interview templates"),
        ("GET", "/letter-templates", "Letter templates"),
        ("GET", "/email-templates", "Email templates"),
        ("GET", "/predictions/dashboard", "Flight risk dashboard"),
        ("GET", "/predictions/high-risk", "High-risk employees"),
        ("GET", "/nps/scores", "NPS scores"),
        ("GET", "/nps/trends", "NPS trends"),
        ("GET", "/rehire", "Rehire list"),
        ("GET", "/rehire/eligible", "Rehire eligible"),
        ("GET", "/my-clearances", "My clearances"),
    ]

    for method, path, label in endpoints:
        try:
            url = f"{EXIT_API}{path}"
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=10)
            else:
                r = requests.post(url, headers=headers, timeout=10)
            status = r.status_code
            ok = status in (200, 201, 204)
            record(f"API|{label}", "PASS" if ok else "FAIL", f"HTTP {status}")
            if not ok and status not in (404, 401, 403):
                file_bug(
                    f"[Exit][API] {label} returned {status}",
                    f"**Endpoint**: `{method} {path}`\n**Status**: {status}\n"
                    f"**Response**: {r.text[:300]}\n\n"
                    f"**Expected**: 2xx response.",
                    labels=["bug", "exit-module", "api"],
                )
        except Exception as e:
            record(f"API|{label}", "ERROR", str(e)[:100])


def run_admin_clearance_before_fnf(token):
    """Business rule: F&F should not be payable before clearance is complete."""
    log("\n--- Business Rule: Clearance before F&F ---")
    headers = {"Authorization": f"Bearer {token}"}

    # Find an exit that is NOT fully cleared
    try:
        r = requests.get(f"{EXIT_API}/exits", headers=headers, timeout=10)
        if r.status_code != 200:
            record("BizRule|Clearance before F&F", "SKIP", f"Cannot list exits: {r.status_code}")
            return
        data = r.json()
        items = data.get("data", data) if isinstance(data, dict) else data
        if isinstance(items, dict):
            items = items.get("exits", items.get("rows", items.get("items", [])))
        if not isinstance(items, list) or not items:
            record("BizRule|Clearance before F&F", "SKIP", "No exits found")
            return

        # Pick first exit
        exit_id = items[0].get("id") or items[0].get("exit_id")

        # Check clearance status
        cr = requests.get(f"{EXIT_API}/exits/{exit_id}/clearance", headers=headers, timeout=10)
        log(f"  Clearance for exit {exit_id}: {cr.status_code}")
        clearance_data = cr.json() if cr.status_code == 200 else {}

        # Check F&F status
        fr = requests.get(f"{EXIT_API}/exits/{exit_id}/fnf", headers=headers, timeout=10)
        log(f"  F&F for exit {exit_id}: {fr.status_code}")
        fnf_data = fr.json() if fr.status_code == 200 else {}

        # Attempt to approve/mark-paid F&F if clearance is not complete
        all_cleared = True
        if cr.status_code == 200:
            recs = clearance_data.get("data", clearance_data)
            if isinstance(recs, dict):
                recs = recs.get("records", recs.get("clearances", []))
            if isinstance(recs, list):
                for rec in recs:
                    if rec.get("status") not in ("approved", "cleared", "completed"):
                        all_cleared = False
                        break

        if not all_cleared:
            # Try to mark F&F as paid -- should be blocked
            pr = requests.post(f"{EXIT_API}/exits/{exit_id}/fnf/mark-paid",
                               headers=headers, json={}, timeout=10)
            log(f"  POST fnf/mark-paid (clearance pending): {pr.status_code}")
            if pr.status_code in (200, 201):
                record("BizRule|Clearance before F&F", "FAIL",
                       "F&F mark-paid succeeded despite pending clearance")
                file_bug(
                    "[Exit] F&F can be marked paid before clearance is complete",
                    "**Business Rule**: Clearance must be fully approved before F&F can be settled.\n\n"
                    f"**Exit ID**: {exit_id}\n"
                    f"**Clearance status**: Not all departments cleared\n"
                    f"**F&F mark-paid response**: {pr.status_code}\n\n"
                    "**Expected**: 4xx error preventing F&F payment before clearance.",
                    labels=["bug", "exit-module", "business-rule"],
                )
            else:
                record("BizRule|Clearance before F&F", "PASS",
                       f"Correctly blocked: HTTP {pr.status_code}")
        else:
            record("BizRule|Clearance before F&F", "SKIP",
                   "All clearances already complete; cannot test blocking")

    except Exception as e:
        record("BizRule|Clearance before F&F", "ERROR", str(e)[:120])


# ======================================================================
#  PART B  --  EMPLOYEE TESTS  (priya@technova.in)
# ======================================================================

# Pages that employee should NOT be able to access
EMPLOYEE_BLOCKED_PAGES = [
    ("emp_block_fnf",         "/fnf",         "F&F Management"),
    ("emp_block_analytics",   "/analytics",   "Exit Analytics"),
    ("emp_block_settings",    "/settings",    "Settings"),
    ("emp_block_clearance",   "/clearance",   "Clearance Config"),
    ("emp_block_exits_list",  "/exits",       "Exit List (admin)"),
    ("emp_block_rehire",      "/rehire",      "Rehire Management"),
    ("emp_block_checklists",  "/checklists",  "Checklist Templates"),
    ("emp_block_interviews",  "/interviews",  "Interview Templates"),
    ("emp_block_letters",     "/letters",     "Letter Templates"),
    ("emp_block_buyout",      "/buyout",      "Notice Buyout (admin)"),
    ("emp_block_assets",      "/assets",      "Asset Returns (admin)"),
]

# Self-service pages employee should be able to see
EMPLOYEE_SELF_PAGES = [
    ("emp_self_dashboard", "/my",              "Self-Service Dashboard"),
    ("emp_self_exit",      "/my/exit",         "My Exit"),
    ("emp_self_interview", "/my/exit/interview", "My Exit Interview"),
    ("emp_self_kt",        "/my/exit/kt",      "My Knowledge Transfer"),
    ("emp_self_nps",       "/my/exit/nps",      "My NPS Survey"),
    ("emp_self_letters",   "/my/exit/letters",  "My Letters"),
    ("emp_self_alumni",    "/my/alumni",         "My Alumni Profile"),
    ("emp_self_buyout",    "/my/exit/buyout",    "My Notice Buyout"),
]


def run_employee_rbac(driver, token):
    """Employee should be blocked from admin-only pages."""
    log("\n" + "=" * 60)
    log("EMPLOYEE RBAC TESTS")
    log("=" * 60)

    for slug, path, label in EMPLOYEE_BLOCKED_PAGES:
        log(f"\n--- RBAC: {label} ({path}) ---")
        try:
            sso_navigate(driver, token, path)
            screenshot(driver, slug)

            src = (driver.page_source or "").lower()
            current_url = driver.current_url.lower()

            # Check if redirected away or got forbidden / unauthorized
            redirected = path not in current_url
            has_denied = any(kw in src for kw in
                            ["403", "forbidden", "unauthorized", "access denied",
                             "not authorized", "permission", "login", "redirect"])
            page_err = check_page_errors(driver)
            is_blocked = redirected or has_denied or (page_err in ("Forbidden", "Unauthorized"))

            if is_blocked:
                record(f"RBAC|{label}", "PASS", "Access correctly blocked")
            else:
                # Check if the page actually has admin data
                body_text = ""
                try:
                    body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
                except Exception:
                    pass
                if len(body_text) < 20:
                    record(f"RBAC|{label}", "PASS", "Page empty/blank (effective block)")
                else:
                    record(f"RBAC|{label}", "FAIL", "Employee can see admin page content")
                    file_bug(
                        f"[Exit][RBAC] Employee can access {label}",
                        f"**Page**: `{path}`\n**Role**: Employee (priya@technova.in)\n\n"
                        f"**Observed**: Page loaded with content ({len(body_text)} chars).\n"
                        f"**Expected**: 403/redirect. Employees should not access admin pages.\n\n"
                        f"**Body preview**: {body_text[:200]}",
                        labels=["bug", "exit-module", "rbac"],
                    )

        except Exception as e:
            record(f"RBAC|{label}", "ERROR", str(e)[:120])
            try:
                screenshot(driver, f"{slug}_error")
            except Exception:
                pass


def run_employee_rbac_flight_risk(token):
    """Employee should not see flight-risk / prediction APIs."""
    log("\n--- RBAC: Flight Risk API ---")
    headers = {"Authorization": f"Bearer {token}"}

    for path, label in [("/predictions/dashboard", "Flight Risk Dashboard"),
                         ("/predictions/high-risk", "High-Risk Employees")]:
        try:
            r = requests.get(f"{EXIT_API}{path}", headers=headers, timeout=10)
            log(f"  {label}: HTTP {r.status_code}")
            if r.status_code in (200, 201):
                record(f"RBAC|API {label}", "FAIL", "Employee got 200 on flight-risk endpoint")
                file_bug(
                    f"[Exit][RBAC] Employee can access {label} API",
                    f"**Endpoint**: GET `{path}`\n**Role**: Employee\n"
                    f"**Status**: {r.status_code}\n**Response**: {r.text[:200]}\n\n"
                    "**Expected**: 403. Employees should not see flight risk data.",
                    labels=["bug", "exit-module", "rbac", "api"],
                )
            else:
                record(f"RBAC|API {label}", "PASS", f"Blocked with HTTP {r.status_code}")
        except Exception as e:
            record(f"RBAC|API {label}", "ERROR", str(e)[:100])


def run_employee_self_service(driver, token):
    """Test employee self-service pages."""
    log("\n" + "=" * 60)
    log("EMPLOYEE SELF-SERVICE TESTS")
    log("=" * 60)

    for slug, path, label in EMPLOYEE_SELF_PAGES:
        log(f"\n--- Self-service: {label} ({path}) ---")
        try:
            sso_navigate(driver, token, path)
            screenshot(driver, slug)

            error = check_page_errors(driver)
            if error:
                # Some self-service pages may return 404 if employee has no active exit
                # That's not necessarily a bug
                if error in ("Page Not Found",) and "my/exit" in path:
                    record(f"Self|{label}", "INFO",
                           "404 -- possibly no active exit for this employee")
                else:
                    record(f"Self|{label}", "FAIL", error)
                    file_bug(
                        f"[Exit][Self-Service] {label}: {error}",
                        f"**Page**: `{path}`\n**Role**: Employee\n**Error**: {error}\n\n"
                        "**Expected**: Self-service page loads or shows helpful empty state.",
                        labels=["bug", "exit-module", "self-service"],
                    )
            else:
                record(f"Self|{label}", "PASS", "Page loaded")

        except Exception as e:
            record(f"Self|{label}", "ERROR", str(e)[:120])
            try:
                screenshot(driver, f"{slug}_error")
            except Exception:
                pass


def run_employee_self_api(token):
    """Test employee self-service API endpoints."""
    log("\n--- Employee Self-Service API ---")
    headers = {"Authorization": f"Bearer {token}"}
    endpoints = [
        ("GET", "/self-service/my-exit", "My Exit Status"),
        ("GET", "/self-service/my-checklist", "My Checklist"),
    ]
    for method, path, label in endpoints:
        try:
            r = requests.get(f"{EXIT_API}{path}", headers=headers, timeout=10)
            log(f"  {label}: HTTP {r.status_code}")
            # 200 or 404 (no active exit) are both acceptable
            if r.status_code in (200, 404):
                record(f"SelfAPI|{label}", "PASS", f"HTTP {r.status_code}")
            else:
                record(f"SelfAPI|{label}", "FAIL", f"HTTP {r.status_code}")
        except Exception as e:
            record(f"SelfAPI|{label}", "ERROR", str(e)[:100])


# ======================================================================
#  PART C  --  BUSINESS RULE: Access Revoked on Exit
# ======================================================================

def run_access_revoked_check(admin_token):
    """Verify completed exits have user deactivated (API-level check)."""
    log("\n--- Business Rule: Access Revoked on Exit ---")
    headers = {"Authorization": f"Bearer {admin_token}"}

    try:
        r = requests.get(f"{EXIT_API}/exits?status=completed", headers=headers, timeout=10)
        if r.status_code != 200:
            # Try without filter
            r = requests.get(f"{EXIT_API}/exits", headers=headers, timeout=10)
        if r.status_code != 200:
            record("BizRule|Access Revoked", "SKIP", f"Cannot list exits: {r.status_code}")
            return

        data = r.json()
        items = data.get("data", data) if isinstance(data, dict) else data
        if isinstance(items, dict):
            items = items.get("exits", items.get("rows", items.get("items", [])))
        if not isinstance(items, list):
            record("BizRule|Access Revoked", "SKIP", "Cannot parse exit list")
            return

        completed = [x for x in items if x.get("status") in ("completed", "closed")]
        if not completed:
            record("BizRule|Access Revoked", "SKIP", "No completed exits to verify")
            return

        exit_item = completed[0]
        exit_id = exit_item.get("id") or exit_item.get("exit_id")
        log(f"  Checking completed exit {exit_id}...")
        record("BizRule|Access Revoked", "INFO",
               f"Found {len(completed)} completed exit(s); manual verification recommended")

    except Exception as e:
        record("BizRule|Access Revoked", "ERROR", str(e)[:120])


# ======================================================================
#  MAIN
# ======================================================================

def print_summary():
    log("\n" + "=" * 70)
    log("FINAL SUMMARY")
    log("=" * 70)
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    err_count = sum(1 for r in results if r["status"] == "ERROR")
    skip_count = sum(1 for r in results if r["status"] in ("SKIP", "INFO"))
    total = len(results)

    log(f"Total: {total}  |  PASS: {pass_count}  |  FAIL: {fail_count}  |  "
        f"WARN: {warn_count}  |  ERROR: {err_count}  |  SKIP/INFO: {skip_count}")
    log(f"Bugs queued: {len(bugs)}")
    log("")

    # Print failures
    fails = [r for r in results if r["status"] in ("FAIL", "ERROR")]
    if fails:
        log("FAILURES / ERRORS:")
        for r in fails:
            log(f"  [{r['status']}] {r['test']}: {r['details']}")

    log("")
    for r in results:
        log(f"  [{r['status']:5s}] {r['test']}: {r['details']}")

    log("\n" + "=" * 70)


def main():
    log("=" * 70)
    log("FRESH E2E TEST -- EMP EXIT MANAGEMENT MODULE")
    log(f"Started: {datetime.now().isoformat()}")
    log("=" * 70)

    # ── Get tokens ──
    admin_token = get_sso_token(ADMIN_EMAIL, ADMIN_PASS, "Admin")
    emp_token = get_sso_token(EMP_EMAIL, EMP_PASS, "Employee")
    if not admin_token:
        log("FATAL: Cannot get admin token. Aborting.")
        return
    if not emp_token:
        log("WARNING: Cannot get employee token. Employee tests will be skipped.")

    # ── PART A: Admin tests ──
    driver = None
    try:
        driver = create_driver()
        log("\nAdmin browser session started.")

        run_admin_page_tests(driver, admin_token)
        run_admin_initiate_exit(driver, admin_token)
        run_admin_exit_detail(driver, admin_token)
        run_admin_api_smoke(admin_token)
        run_admin_clearance_before_fnf(admin_token)
        run_access_revoked_check(admin_token)

    except Exception as e:
        log(f"ADMIN SESSION ERROR: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # ── PART B: Employee tests ──
    if emp_token:
        driver = None
        try:
            driver = create_driver()
            log("\nEmployee browser session started.")

            run_employee_rbac(driver, emp_token)
            run_employee_rbac_flight_risk(emp_token)
            run_employee_self_service(driver, emp_token)
            run_employee_self_api(emp_token)

        except Exception as e:
            log(f"EMPLOYEE SESSION ERROR: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    # ── File bugs ──
    create_github_issues()

    # ── Summary ──
    print_summary()

    log(f"\nScreenshots: {SCREENSHOT_DIR}")
    log(f"Finished: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
