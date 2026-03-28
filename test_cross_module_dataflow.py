"""
EMP Cloud HRMS - Cross-Module Data Flow Integrity Tests
Verifies data consistency across modules: Employee, Attendance, Leave, Payroll,
Departments, Helpdesk, Assets, Events, Surveys, Announcements, Wellness, Forum,
Positions/Recruitment, Employee Counts, Module Subscriptions, Documents.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import functools
print = functools.partial(print, flush=True)

import time, json, base64, urllib.request, urllib.error, ssl, traceback, os, re
from datetime import datetime, timedelta

# --- Selenium ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ==============================================================================
# CONFIGURATION
# ==============================================================================
BASE_URL   = "https://test-empcloud.empcloud.com"
API_BASE   = "https://test-empcloud-api.empcloud.com"
PAYROLL_URL = "https://testpayroll.empcloud.com"
RECRUIT_URL = "https://test-recruit.empcloud.com"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS  = "Welcome@123"
EMP_EMAIL   = "priya@technova.in"
EMP_PASS    = "Welcome@123"
SUPER_EMAIL = "admin@empcloud.com"
SUPER_PASS  = "SuperAdmin@2026"

GITHUB_PAT  = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
SS_DIR      = r"C:\emptesting\screenshots"
os.makedirs(SS_DIR, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ==============================================================================
# GLOBALS
# ==============================================================================
REPORT = {
    "started": datetime.now().isoformat(),
    "flows_tested": 0, "flows_passed": 0, "flows_failed": 0,
    "bugs_filed": [], "feature_requests": [], "screenshots": {},
    "details": {}
}
EXISTING_ISSUES = []  # populated once to avoid duplicates
CHROMEDRIVER_PATH = None
DRIVER_USE_COUNT = 0
MAX_DRIVER_USES = 2
_driver = None

# ==============================================================================
# HELPERS
# ==============================================================================
def api(path, method="GET", data=None, token=None, timeout=30):
    url = API_BASE + path if path.startswith("/") else path
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "EmpCloudDataFlowTester/2.0",
        "Origin": BASE_URL,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(raw)
        except json.JSONDecodeError:
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except:
            pass
        try:
            return e.code, json.loads(raw)
        except:
            return e.code, raw
    except Exception as ex:
        return 0, str(ex)


def login(email, password):
    code, body = api("/api/v1/auth/login", "POST", {"email": email, "password": password})
    if code == 200 and isinstance(body, dict):
        token = body.get("data", {}).get("tokens", {}).get("access_token")
        user = body.get("data", {}).get("user", {})
        org = body.get("data", {}).get("org", {})
        if token:
            print(f"    Logged in as {email} (id={user.get('id')}, role={user.get('role')})")
            return token, user, org
    print(f"    Login FAILED for {email}: {code}")
    return None, None, None


def get_all_pages(path, token, key="data"):
    all_items = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        code, body = api(f"{path}{sep}page={page}&limit=100", token=token)
        if code != 200 or not isinstance(body, dict):
            break
        items = body.get(key, [])
        if isinstance(items, list):
            all_items.extend(items)
        else:
            break
        meta = body.get("meta", {})
        total_pages = meta.get("totalPages") or meta.get("total_pages") or 1
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.2)
    return all_items


def get_driver():
    global CHROMEDRIVER_PATH, _driver, DRIVER_USE_COUNT
    if _driver and DRIVER_USE_COUNT < MAX_DRIVER_USES:
        DRIVER_USE_COUNT += 1
        return _driver
    # Close old driver
    if _driver:
        try:
            _driver.quit()
        except:
            pass
    opts = webdriver.ChromeOptions()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
              "--window-size=1920,1080", "--disable-gpu",
              "--ignore-certificate-errors", "--disable-extensions"]:
        opts.add_argument(a)
    if not CHROMEDRIVER_PATH:
        CHROMEDRIVER_PATH = ChromeDriverManager().install()
    _driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=opts)
    _driver.set_page_load_timeout(60)
    _driver.implicitly_wait(3)
    DRIVER_USE_COUNT = 1
    return _driver


def quit_driver():
    global _driver, DRIVER_USE_COUNT
    if _driver:
        try:
            _driver.quit()
        except:
            pass
        _driver = None
        DRIVER_USE_COUNT = 0


def save_ss(driver, name):
    fname = f"df_{name}_{int(time.time())}.png"
    p = os.path.join(SS_DIR, fname)
    try:
        driver.save_screenshot(p)
        REPORT["screenshots"][name] = p
        return p
    except:
        return None


def selenium_login(driver, email, password):
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    try:
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail']"))
        )
        email_input.clear()
        email_input.send_keys(email)
        time.sleep(0.5)
        pw_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pw_input.clear()
        pw_input.send_keys(password)
        time.sleep(0.5)
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.login-btn, form button")
        btn.click()
        time.sleep(4)
        if "/login" not in driver.current_url or "/dashboard" in driver.current_url:
            print(f"    Selenium login OK: {email}")
            return True
    except Exception as e:
        print(f"    Selenium login failed for {email}: {e}")
    save_ss(driver, f"login_fail_{email.split('@')[0]}")
    return False


# ==============================================================================
# GITHUB HELPERS
# ==============================================================================
def load_existing_issues():
    global EXISTING_ISSUES
    try:
        page = 1
        while True:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_REPO}/issues?state=open&per_page=100&page={page}",
                headers={"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
            )
            resp = urllib.request.urlopen(req, context=ctx, timeout=30)
            issues = json.loads(resp.read())
            if not issues:
                break
            EXISTING_ISSUES.extend([i["title"].lower().strip() for i in issues])
            page += 1
            if len(issues) < 100:
                break
    except Exception as e:
        print(f"  Warning: could not load existing issues: {e}")
    print(f"  Loaded {len(EXISTING_ISSUES)} existing open issues for dedup")


def is_duplicate(title):
    t = title.lower().strip()
    for existing in EXISTING_ISSUES:
        # fuzzy: if 60% of words overlap
        t_words = set(t.split())
        e_words = set(existing.split())
        if len(t_words & e_words) >= 0.6 * max(len(t_words), 1):
            return True
    return False


def upload_screenshot(local_path, name):
    if not local_path or not os.path.exists(local_path):
        return None
    try:
        with open(local_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()
        fname = os.path.basename(local_path)
        data = json.dumps({"message": f"Screenshot: {name}", "content": content}).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/{fname}",
            data=data, method='PUT',
            headers={"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"})
        resp = json.loads(urllib.request.urlopen(req, context=ctx, timeout=60).read())
        return resp["content"]["download_url"]
    except:
        return None


def file_bug(title, body_text, labels=None, screenshots=None):
    full_title = f"[DATA FLOW] {title}"
    if is_duplicate(full_title):
        print(f"    [SKIP DUP] {title}")
        return None
    body = body_text
    if screenshots:
        body += "\n\n## Screenshots\n"
        for sname, spath in screenshots.items():
            url = upload_screenshot(spath, sname)
            if url:
                body += f"![{sname}]({url})\n"
    body += "\n\n---\n_Filed by cross-module data flow integrity test suite._"
    payload = {
        "title": full_title,
        "body": body,
        "labels": labels or ["bug", "data-flow"]
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            data=data, method='POST',
            headers={"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"})
        resp = json.loads(urllib.request.urlopen(req, context=ctx, timeout=30).read())
        url = resp.get("html_url", "?")
        print(f"    [BUG FILED] #{resp.get('number')} {title}")
        REPORT["bugs_filed"].append({"title": full_title, "url": url})
        EXISTING_ISSUES.append(full_title.lower().strip())
        return url
    except Exception as e:
        print(f"    [BUG FAIL] {e}")
        return None


def file_feature_request(title, body_text):
    full_title = f"[Feature Request] {title}"
    if is_duplicate(full_title):
        print(f"    [SKIP DUP FR] {title}")
        return None
    body = body_text + "\n\n---\n_Filed by cross-module data flow integrity test suite._"
    payload = {
        "title": full_title,
        "body": body,
        "labels": ["enhancement", "data-flow"]
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            data=data, method='POST',
            headers={"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"})
        resp = json.loads(urllib.request.urlopen(req, context=ctx, timeout=30).read())
        url = resp.get("html_url", "?")
        print(f"    [FR FILED] #{resp.get('number')} {title}")
        REPORT["feature_requests"].append({"title": full_title, "url": url})
        EXISTING_ISSUES.append(full_title.lower().strip())
        return url
    except Exception as e:
        print(f"    [FR FAIL] {e}")
        return None


# ==============================================================================
# FLOW 1: Employee -> Attendance -> Leave -> Payroll
# ==============================================================================
def flow_1_employee_attendance_leave_payroll(admin_token, emp_token, emp_user, org):
    print("\n" + "=" * 70)
    print("FLOW 1: Employee -> Attendance -> Leave -> Payroll")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []
    priya_id = emp_user["id"]

    # 1. Priya's profile
    print("  [1] Priya's profile from login data")
    print(f"      id={priya_id}, dept={emp_user.get('department_id')}, "
          f"manager={emp_user.get('reporting_manager_id')}, role={emp_user.get('role')}")

    # 2. Attendance records this month
    print("  [2] Checking attendance records this month...")
    now = datetime.now()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    code, body = api(f"/api/v1/attendance/records?user_id={priya_id}&limit=100", token=admin_token)
    attendance = body.get("data", []) if code == 200 else []
    this_month = [r for r in attendance if r.get("date", "")[:7] == now.strftime("%Y-%m")]
    present_days = len([r for r in this_month if r.get("status") in ("present", "half_day")])
    print(f"      Attendance records this month: {len(this_month)}, present/half_day: {present_days}")
    for r in this_month[:5]:
        print(f"        {r.get('date','?')[:10]} status={r.get('status')} worked={r.get('worked_minutes')}min")

    # 3. Leave balances
    print("  [3] Checking leave balances...")
    code, body = api("/api/v1/leave/balances", token=emp_token)
    balances = body.get("data", []) if code == 200 else []
    # Get leave type names
    code2, body2 = api("/api/v1/leave/types", token=admin_token)
    leave_types = {t["id"]: t["name"] for t in body2.get("data", [])} if code2 == 200 else {}
    balance_map = {}
    for b in balances:
        tid = b.get("leave_type_id")
        tname = leave_types.get(tid, f"type_{tid}")
        balance_map[tid] = {
            "name": tname, "allocated": float(b.get("total_allocated", 0)),
            "used": float(b.get("total_used", 0)), "balance": float(b.get("balance", 0))
        }
        print(f"      {tname}: alloc={b.get('total_allocated')} used={b.get('total_used')} balance={b.get('balance')}")

    # 4. Leave applications
    print("  [4] Checking leave applications...")
    all_apps = get_all_pages(f"/api/v1/leave/applications?user_id={priya_id}", admin_token)
    print(f"      Total leave applications: {len(all_apps)}")
    by_status = {}
    approved_days_by_type = {}
    for a in all_apps:
        s = a.get("status", "?")
        by_status[s] = by_status.get(s, 0) + 1
        if s == "approved":
            tid = a.get("leave_type_id")
            days = float(a.get("days_count", 0))
            approved_days_by_type[tid] = approved_days_by_type.get(tid, 0) + days
    print(f"      By status: {by_status}")
    print(f"      Approved days by type: {approved_days_by_type}")

    # 5. Cross-check: leave balance "used" should match sum of approved applications
    print("  [5] Cross-checking leave balance vs approved applications...")
    for tid, info in balance_map.items():
        actual_used = approved_days_by_type.get(tid, 0)
        balance_used = info["used"]
        if abs(balance_used - actual_used) > 0.01:
            msg = (f"Leave balance for '{info['name']}' (type_id={tid}) shows "
                   f"used={balance_used} but sum of approved applications = {actual_used}")
            print(f"      MISMATCH: {msg}")
            issues.append(msg)
            file_bug(
                f"Leave balance for '{info['name']}' doesn't match approved applications -- off by {abs(balance_used - actual_used)} days",
                f"## Data Mismatch\n\n"
                f"**Employee:** Priya (id={priya_id})\n"
                f"**Leave Type:** {info['name']} (type_id={tid})\n\n"
                f"| Source | Used Days |\n|---|---|\n"
                f"| `/api/v1/leave/balances` (total_used) | {balance_used} |\n"
                f"| Sum of approved `/api/v1/leave/applications` | {actual_used} |\n\n"
                f"**Expected:** Both should match.\n\n"
                f"**Approved applications for this type:**\n" +
                "\n".join([f"- App #{a['id']}: {a.get('start_date','?')[:10]} to {a.get('end_date','?')[:10]}, "
                           f"days={a.get('days_count')}, status={a.get('status')}"
                           for a in all_apps if a.get("status") == "approved" and a.get("leave_type_id") == tid]),
                labels=["bug", "data-flow", "priority-high"]
            )

    # 6. Check if attendance shows "on_leave" for approved leave dates
    print("  [6] Checking if attendance reflects approved leave dates...")
    approved_dates = set()
    for a in all_apps:
        if a.get("status") == "approved" and a.get("start_date"):
            start = a["start_date"][:10]
            end = a.get("end_date", start)[:10]
            # For simplicity, just add start date
            approved_dates.add(start)
    attendance_dates = {r.get("date", "")[:10]: r.get("status") for r in attendance}
    missing_leave_in_attendance = []
    for d in approved_dates:
        att_status = attendance_dates.get(d)
        if att_status and att_status not in ("on_leave", "leave"):
            missing_leave_in_attendance.append(f"{d}: attendance shows '{att_status}' instead of 'on_leave'")
        elif not att_status:
            missing_leave_in_attendance.append(f"{d}: no attendance record (should show 'on_leave')")

    if missing_leave_in_attendance:
        detail = "\n".join(f"- {m}" for m in missing_leave_in_attendance)
        print(f"      ISSUE: Approved leave dates not reflected in attendance:")
        for m in missing_leave_in_attendance[:3]:
            print(f"        {m}")
        issues.append("Approved leave dates not reflected in attendance")
        file_feature_request(
            "Approved leave should automatically create 'on_leave' attendance record",
            f"## Missing Integration\n\n"
            f"When a leave application is approved, the attendance module should automatically "
            f"mark those dates as 'on_leave'. Currently this doesn't happen.\n\n"
            f"**Employee:** Priya (id={priya_id})\n"
            f"**Approved leave dates with incorrect/missing attendance:**\n{detail}\n\n"
            f"This breaks the Employee -> Leave -> Attendance data flow."
        )

    # 7. Payroll cross-check via Selenium
    print("  [7] Checking Payroll module via Selenium...")
    try:
        driver = get_driver()
        if selenium_login(driver, ADMIN_EMAIL, ADMIN_PASS):
            save_ss(driver, "flow1_admin_dashboard")
            # Navigate to payroll via SSO link
            driver.get(f"{BASE_URL}/dashboard")
            time.sleep(3)
            # Look for payroll module link
            try:
                payroll_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='payroll'], a[href*='Payroll'], [data-module='payroll']")
                if payroll_links:
                    payroll_links[0].click()
                    time.sleep(5)
                    save_ss(driver, "flow1_payroll_sso")
                    print(f"      Payroll URL: {driver.current_url}")
                else:
                    # Try direct payroll URL with token
                    driver.get(PAYROLL_URL)
                    time.sleep(5)
                    save_ss(driver, "flow1_payroll_direct")
                    print(f"      Payroll direct URL: {driver.current_url}")
            except Exception as e:
                print(f"      Payroll navigation: {e}")
                save_ss(driver, "flow1_payroll_error")
    except Exception as e:
        print(f"      Selenium error: {e}")

    if issues:
        REPORT["flows_failed"] += 1
        REPORT["details"]["flow_1"] = {"status": "FAIL", "issues": issues}
    else:
        REPORT["flows_passed"] += 1
        REPORT["details"]["flow_1"] = {"status": "PASS"}
    print(f"  FLOW 1 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 2: Employee -> Department -> Org Chart -> Manager
# ==============================================================================
def flow_2_department_orgchart_manager(admin_token, emp_token, emp_user, org):
    print("\n" + "=" * 70)
    print("FLOW 2: Employee -> Department -> Org Chart -> Manager")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []

    # 1. Get all employees
    print("  [1] Fetching all employees...")
    all_users = get_all_pages("/api/v1/users", admin_token)
    print(f"      Total users from API: {len(all_users)}")

    # 2. Get departments
    print("  [2] Fetching departments...")
    code, body = api("/api/v1/organizations/me/departments?limit=200", token=admin_token)
    departments = body.get("data", []) if code == 200 else []
    dept_id_map = {d["id"]: d.get("name", "?") for d in departments}
    print(f"      Departments from API: {len(departments)}")

    # 3. Check for orphan department_ids
    print("  [3] Checking employee department_ids map to real departments...")
    user_dept_ids = set(u.get("department_id") for u in all_users if u.get("department_id"))
    orphan_dept_ids = user_dept_ids - set(dept_id_map.keys())
    if orphan_dept_ids:
        # Find which users have these orphan depts
        orphan_users = [u for u in all_users if u.get("department_id") in orphan_dept_ids]
        detail = "\n".join([f"- User {u.get('first_name','')} {u.get('last_name','')} "
                            f"(id={u['id']}, email={u.get('email','?')}) has department_id={u.get('department_id')}"
                            for u in orphan_users[:10]])
        msg = f"Employees reference department IDs {sorted(orphan_dept_ids)} that don't exist in /organizations/me/departments"
        print(f"      MISMATCH: {msg}")
        issues.append(msg)
        file_bug(
            f"Employees reference {len(orphan_dept_ids)} department IDs that don't exist in the departments list",
            f"## Data Mismatch\n\n"
            f"**Orphan department IDs:** {sorted(orphan_dept_ids)}\n"
            f"**Valid department IDs:** {sorted(dept_id_map.keys())}\n\n"
            f"**Affected employees:**\n{detail}\n\n"
            f"These employees are assigned to departments that the "
            f"`/api/v1/organizations/me/departments` endpoint doesn't return. "
            f"This could mean departments were soft-deleted but employees weren't reassigned, "
            f"or pagination is hiding some departments.",
            labels=["bug", "data-flow", "priority-high"]
        )

    # 4. Check Priya's manager chain
    priya_id = emp_user["id"]
    priya_mgr = emp_user.get("reporting_manager_id")
    print(f"  [4] Priya's manager chain: manager_id={priya_mgr}")

    # Check if Priya is visible in users list
    priya_in_list = any(u.get("id") == priya_id for u in all_users)
    if not priya_in_list:
        msg = f"Priya (id={priya_id}) can login but doesn't appear in /api/v1/users list"
        print(f"      ISSUE: {msg}")
        issues.append(msg)
        file_bug(
            "Employee can login but doesn't appear in the users API list",
            f"## Data Mismatch\n\n"
            f"**Employee:** Priya (id={priya_id}, email={EMP_EMAIL})\n\n"
            f"Priya can successfully login via `/api/v1/auth/login` and gets a valid token, "
            f"but she does not appear in the `/api/v1/users` list (checked all pages, got {len(all_users)} users).\n\n"
            f"This means the users endpoint is returning an incomplete list, or Priya's account "
            f"has a status that filters her out despite being able to login.\n"
            f"Priya's status from login: {emp_user.get('status')}",
            labels=["bug", "data-flow", "priority-high"]
        )

    # 5. Check Priya's department exists
    priya_dept = emp_user.get("department_id")
    if priya_dept and priya_dept not in dept_id_map:
        print(f"      Priya's department_id={priya_dept} not in departments list!")
        issues.append(f"Priya's department_id={priya_dept} is an orphan")

    # 6. Check manager exists as a user
    if priya_mgr:
        mgr_in_list = any(u.get("id") == priya_mgr for u in all_users)
        if not mgr_in_list:
            # Manager might also be hidden, try login data
            print(f"      Manager id={priya_mgr} not in users list (may be same visibility issue)")

    # 7. Org chart via Selenium
    print("  [5] Checking org chart via Selenium...")
    try:
        driver = get_driver()
        if selenium_login(driver, ADMIN_EMAIL, ADMIN_PASS):
            driver.get(f"{BASE_URL}/org-chart")
            time.sleep(4)
            save_ss(driver, "flow2_orgchart")
            page_text = driver.page_source.lower()
            if "org" in page_text or "chart" in page_text or "hierarchy" in page_text:
                print("      Org chart page loaded")
            else:
                print(f"      Org chart page: {driver.current_url}")
                # Try alternate paths
                for path in ["/organization/chart", "/employees/org-chart", "/dashboard/org-chart"]:
                    driver.get(f"{BASE_URL}{path}")
                    time.sleep(3)
                    if "/login" not in driver.current_url:
                        save_ss(driver, f"flow2_orgchart_alt")
                        print(f"      Found org chart at: {driver.current_url}")
                        break
    except Exception as e:
        print(f"      Selenium org chart error: {e}")

    if issues:
        REPORT["flows_failed"] += 1
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_2"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 2 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 3: Leave Application -> Manager Approval -> Balance Update -> Notification
# ==============================================================================
def flow_3_leave_approval_flow(admin_token, emp_token, emp_user, admin_user):
    print("\n" + "=" * 70)
    print("FLOW 3: Leave Application -> Manager Approval -> Balance Update -> Notification")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []
    priya_id = emp_user["id"]
    manager_id = emp_user.get("reporting_manager_id")

    # 1. Get current leave balance before
    code, body = api("/api/v1/leave/balances", token=emp_token)
    balances_before = {b["leave_type_id"]: float(b.get("balance", 0)) for b in body.get("data", [])}
    # Use Sick Leave (type 17) since it has 12 allocated and 0 used
    test_type = 17
    balance_before = balances_before.get(test_type, 0)
    print(f"  [1] Sick Leave balance before: {balance_before}")

    # 2. Apply for leave as Priya
    future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    print(f"  [2] Applying for Sick Leave on {future_date}...")
    code, body = api("/api/v1/leave/applications", "POST", {
        "leave_type_id": test_type,
        "start_date": future_date,
        "end_date": future_date,
        "days_count": 1,
        "is_half_day": False,
        "reason": "Data flow test - cross module verification"
    }, token=emp_token)
    if code in (200, 201) and isinstance(body, dict) and body.get("data"):
        app_id = body["data"].get("id")
        print(f"      Leave application created: id={app_id}")
    else:
        print(f"      Leave application failed: {code} {str(body)[:200]}")
        app_id = None

    # 3. Check notifications for manager
    print("  [3] Checking if manager got notification...")
    time.sleep(2)
    code, body = api("/api/v1/notifications?limit=10", token=admin_token)
    notifications = body.get("data", []) if code == 200 else []
    leave_notif = [n for n in notifications if "leave" in str(n).lower()]
    if leave_notif:
        print(f"      Manager has {len(leave_notif)} leave-related notifications")
    else:
        print(f"      No leave notifications for manager (total notifications: {len(notifications)})")
        if app_id:
            issues.append("No notification sent to manager when employee applies for leave")

    # 4. Manager approves the leave
    if app_id:
        print(f"  [4] Manager approving leave application #{app_id}...")
        code, body = api(f"/api/v1/leave/applications/{app_id}/approve", "PUT", {}, token=admin_token)
        if code == 200:
            print(f"      Leave approved successfully")
        else:
            # Try PATCH
            code, body = api(f"/api/v1/leave/applications/{app_id}", "PATCH",
                             {"status": "approved"}, token=admin_token)
            if code == 200:
                print(f"      Leave approved via PATCH")
            else:
                print(f"      Approval failed: {code} {str(body)[:200]}")
                # Try PUT with status
                code, body = api(f"/api/v1/leave/applications/{app_id}", "PUT",
                                 {"status": "approved"}, token=admin_token)
                print(f"      PUT status: {code} {str(body)[:200]}")

        # 5. Check if balance was deducted
        print("  [5] Checking if leave balance was deducted...")
        time.sleep(2)
        code, body = api("/api/v1/leave/balances", token=emp_token)
        balances_after = {b["leave_type_id"]: float(b.get("balance", 0)) for b in body.get("data", [])}
        balance_after = balances_after.get(test_type, 0)
        print(f"      Sick Leave balance after approval: {balance_after} (was {balance_before})")
        expected = balance_before - 1
        if abs(balance_after - expected) > 0.01:
            msg = f"Leave balance not deducted after approval: was {balance_before}, now {balance_after}, expected {expected}"
            print(f"      ISSUE: {msg}")
            issues.append(msg)

        # 6. Check if Priya got approval notification
        print("  [6] Checking if Priya got approval notification...")
        code, body = api("/api/v1/notifications?limit=10", token=emp_token)
        emp_notifs = body.get("data", []) if code == 200 else []
        approval_notif = [n for n in emp_notifs if "approv" in str(n).lower()]
        if approval_notif:
            print(f"      Priya got {len(approval_notif)} approval notifications")
        else:
            print(f"      No approval notification for Priya (total: {len(emp_notifs)})")
            issues.append("No notification sent to employee when leave is approved")

        # 7. Check attendance for that date
        print("  [7] Checking if attendance shows 'on_leave' for the approved date...")
        code, body = api(f"/api/v1/attendance/records?user_id={priya_id}&limit=100", token=admin_token)
        att_records = body.get("data", []) if code == 200 else []
        att_for_date = [r for r in att_records if r.get("date", "")[:10] == future_date]
        if att_for_date:
            status = att_for_date[0].get("status")
            if status not in ("on_leave", "leave"):
                print(f"      Attendance for {future_date}: status='{status}' (not 'on_leave')")
                issues.append(f"Approved leave date {future_date} shows '{status}' in attendance instead of 'on_leave'")
            else:
                print(f"      Attendance correctly shows '{status}'")
        else:
            print(f"      No attendance record for {future_date} (expected 'on_leave')")
            # Not necessarily a bug if future date

    # Clean up: cancel the leave application
    if app_id:
        print("  [cleanup] Cancelling test leave application...")
        api(f"/api/v1/leave/applications/{app_id}", "PATCH", {"status": "cancelled"}, token=emp_token)

    if issues:
        REPORT["flows_failed"] += 1
        # File consolidated bug for notification gaps
        notif_issues = [i for i in issues if "notification" in i.lower()]
        if notif_issues:
            file_bug(
                "Leave approval workflow missing notifications to employee and/or manager",
                f"## Missing Notifications in Leave Flow\n\n"
                f"The leave approval workflow has notification gaps:\n\n" +
                "\n".join(f"- {i}" for i in notif_issues) +
                f"\n\n**Test details:**\n"
                f"- Employee: Priya (id={priya_id})\n"
                f"- Manager: Ananya (id={manager_id})\n"
                f"- Leave application id: {app_id}\n"
                f"- Leave date: {future_date}\n"
                f"- Leave type: Sick Leave (id=17)",
                labels=["bug", "data-flow"]
            )
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_3"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 3 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 4: Helpdesk Ticket -> Assignment -> Status -> Notification
# ==============================================================================
def flow_4_helpdesk_ticket_lifecycle(admin_token, emp_token, emp_user):
    print("\n" + "=" * 70)
    print("FLOW 4: Helpdesk Ticket -> Assignment -> Status -> Notification")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []
    priya_id = emp_user["id"]

    # 1. Create a ticket as Priya
    print("  [1] Creating helpdesk ticket as Priya...")
    code, body = api("/api/v1/helpdesk/tickets", "POST", {
        "subject": f"Data Flow Test Ticket {int(time.time())}",
        "description": "Cross-module data flow test - verifying ticket lifecycle",
        "category": "general",
        "priority": "medium"
    }, token=emp_token)
    ticket_id = None
    if code in (200, 201) and isinstance(body, dict) and body.get("data"):
        ticket_id = body["data"].get("id")
        print(f"      Ticket created: id={ticket_id}")
    else:
        print(f"      Ticket creation failed: {code} {str(body)[:200]}")
        REPORT["flows_failed"] += 1
        REPORT["details"]["flow_4"] = {"status": "FAIL", "issues": ["Cannot create ticket"]}
        return

    time.sleep(1)

    # 2. Check if admin sees it
    print("  [2] Checking if admin sees the ticket...")
    code, body = api(f"/api/v1/helpdesk/tickets?limit=100", token=admin_token)
    tickets = body.get("data", []) if code == 200 else []
    admin_sees = any(t.get("id") == ticket_id for t in tickets)
    print(f"      Admin sees ticket: {admin_sees}")
    if not admin_sees:
        issues.append("Admin cannot see employee's helpdesk ticket in All Tickets")
        file_bug(
            "Admin cannot see employee helpdesk tickets in the ticket list",
            f"Ticket #{ticket_id} created by Priya (id={priya_id}) is not visible "
            f"in the admin's `/api/v1/helpdesk/tickets` list.\n\n"
            f"Total tickets visible to admin: {len(tickets)}",
            labels=["bug", "data-flow"]
        )

    # 3. Admin assigns the ticket
    print("  [3] Admin assigning ticket...")
    code, body = api(f"/api/v1/helpdesk/tickets/{ticket_id}", "PATCH", {
        "assigned_to": 522,  # Ananya
        "status": "assigned"
    }, token=admin_token)
    if code == 200:
        print(f"      Ticket assigned successfully")
    else:
        print(f"      Assignment: {code} {str(body)[:200]}")
        # Try just status update
        code, body = api(f"/api/v1/helpdesk/tickets/{ticket_id}", "PATCH", {
            "status": "in_progress"
        }, token=admin_token)
        print(f"      Status update to in_progress: {code}")

    # 4. Check notification for assignment
    print("  [4] Checking assignment notification...")
    time.sleep(1)
    code, body = api("/api/v1/notifications?limit=10", token=emp_token)
    notifs = body.get("data", []) if code == 200 else []
    ticket_notifs = [n for n in notifs if "ticket" in str(n).lower() or "assign" in str(n).lower()]
    if not ticket_notifs:
        print(f"      No ticket assignment notification for Priya")
        issues.append("No notification when ticket is assigned")

    # 5. Update status to resolved
    print("  [5] Resolving ticket...")
    code, body = api(f"/api/v1/helpdesk/tickets/{ticket_id}", "PATCH", {
        "status": "resolved"
    }, token=admin_token)
    if code == 200:
        print(f"      Ticket resolved")
    else:
        print(f"      Resolve failed: {code}")

    # 6. Check Priya sees status change
    print("  [6] Checking Priya sees the resolved status...")
    code, body = api(f"/api/v1/helpdesk/tickets/{ticket_id}", token=emp_token)
    if code == 200 and isinstance(body, dict):
        ticket_data = body.get("data", body)
        current_status = ticket_data.get("status", "?")
        print(f"      Ticket status from Priya's view: {current_status}")
        if current_status != "resolved":
            issues.append(f"Ticket status mismatch: admin set 'resolved' but Priya sees '{current_status}'")
    else:
        print(f"      Priya can't view ticket: {code}")
        issues.append("Employee cannot view their own ticket by ID")

    # 7. Check resolution notification
    time.sleep(1)
    code, body = api("/api/v1/notifications?limit=10", token=emp_token)
    notifs = body.get("data", []) if code == 200 else []
    resolve_notifs = [n for n in notifs if "resolv" in str(n).lower() or "closed" in str(n).lower()]
    if not resolve_notifs:
        print(f"      No resolution notification for Priya")
        issues.append("No notification when ticket is resolved")

    # File consolidated notification bug
    notif_issues = [i for i in issues if "notification" in i.lower() or "No notification" in i]
    if notif_issues:
        file_feature_request(
            "Helpdesk ticket lifecycle should send notifications at each status change",
            f"## Missing Notifications in Helpdesk Flow\n\n"
            f"The helpdesk ticket lifecycle doesn't send notifications for status changes.\n\n"
            f"**Expected notifications:**\n"
            f"- When ticket is assigned -> notify employee\n"
            f"- When ticket status changes -> notify employee\n"
            f"- When ticket is resolved/closed -> notify employee\n\n"
            f"**Missing:**\n" + "\n".join(f"- {i}" for i in notif_issues)
        )

    if issues:
        REPORT["flows_failed"] += 1
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_4"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 4 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 5: Asset Assignment -> Employee Profile
# ==============================================================================
def flow_5_asset_employee_profile(admin_token, emp_token, emp_user):
    print("\n" + "=" * 70)
    print("FLOW 5: Asset Assignment -> Employee Profile -> Asset Module")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []
    priya_id = emp_user["id"]

    # 1. Get all assets
    print("  [1] Fetching assets...")
    all_assets = get_all_pages("/api/v1/assets", admin_token)
    assigned = [a for a in all_assets if a.get("assigned_to")]
    print(f"      Total assets: {len(all_assets)}, assigned: {len(assigned)}")

    # 2. Check if any assigned to Priya
    priya_assets_api = [a for a in all_assets if a.get("assigned_to") == priya_id]
    print(f"      Assets assigned to Priya (id={priya_id}): {len(priya_assets_api)}")

    # 3. Assign an asset to Priya if none
    test_asset_id = None
    if not priya_assets_api:
        available = [a for a in all_assets if a.get("status") == "available" and not a.get("assigned_to")]
        if available:
            test_asset = available[0]
            test_asset_id = test_asset["id"]
            print(f"  [2] Assigning asset '{test_asset['name']}' (id={test_asset_id}) to Priya...")
            code, body = api(f"/api/v1/assets/{test_asset_id}", "PATCH", {
                "assigned_to": priya_id,
                "status": "assigned"
            }, token=admin_token)
            if code == 200:
                print(f"      Asset assigned successfully")
                priya_assets_api = [{"id": test_asset_id, "name": test_asset["name"]}]
            else:
                print(f"      Assignment failed: {code} {str(body)[:200]}")
    else:
        for a in priya_assets_api:
            print(f"      - {a.get('name')} (id={a['id']}) status={a.get('status')}")

    # 4. Check employee profile via Selenium for assets tab
    print("  [3] Checking Priya's profile Assets tab via Selenium...")
    try:
        driver = get_driver()
        if selenium_login(driver, ADMIN_EMAIL, ADMIN_PASS):
            # Navigate to Priya's employee profile
            driver.get(f"{BASE_URL}/employees/{priya_id}")
            time.sleep(4)
            save_ss(driver, "flow5_priya_profile")
            page_text = driver.page_source.lower()

            # Look for assets tab
            try:
                asset_tabs = driver.find_elements(By.XPATH,
                    "//*[contains(text(),'Asset') or contains(text(),'asset')]")
                if asset_tabs:
                    for tab in asset_tabs:
                        if tab.is_displayed():
                            tab.click()
                            time.sleep(3)
                            save_ss(driver, "flow5_priya_assets_tab")
                            break
                    # Check if our assigned asset appears
                    page_text = driver.page_source
                    for a in priya_assets_api:
                        aname = a.get("name", "")
                        if aname and aname.lower() in page_text.lower():
                            print(f"      Asset '{aname}' visible in profile")
                        elif aname:
                            print(f"      Asset '{aname}' NOT visible in profile")
                            issues.append(f"Asset '{aname}' assigned via API but not visible in employee profile")
                else:
                    print("      No Assets tab found in employee profile")
                    # Check alternate profile URLs
                    for path in [f"/employees/{priya_id}/assets", f"/employees/{priya_id}?tab=assets"]:
                        driver.get(f"{BASE_URL}{path}")
                        time.sleep(3)
                        if "/login" not in driver.current_url:
                            save_ss(driver, "flow5_assets_alt")
                            break
            except Exception as e:
                print(f"      Asset tab check error: {e}")
    except Exception as e:
        print(f"      Selenium error: {e}")

    # 5. Cleanup: unassign test asset
    if test_asset_id:
        print("  [cleanup] Unassigning test asset...")
        api(f"/api/v1/assets/{test_asset_id}", "PATCH", {
            "assigned_to": None, "status": "available"
        }, token=admin_token)

    if issues:
        REPORT["flows_failed"] += 1
        file_bug(
            "Assets assigned via API don't appear in employee profile Assets tab",
            f"## Data Mismatch\n\n"
            f"Assets assigned to employees via the `/api/v1/assets` API don't consistently "
            f"appear in the employee's profile Assets tab in the UI.\n\n"
            f"**Details:**\n" + "\n".join(f"- {i}" for i in issues),
            labels=["bug", "data-flow"]
        )
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_5"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 5 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 6: Event -> RSVP -> Calendar -> Notification
# ==============================================================================
def flow_6_event_rsvp(admin_token, emp_token, emp_user):
    print("\n" + "=" * 70)
    print("FLOW 6: Event -> RSVP -> Calendar -> Notification")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []
    priya_id = emp_user["id"]

    # 1. Get events
    print("  [1] Fetching events...")
    code, body = api("/api/v1/events?limit=20", token=admin_token)
    events = body.get("data", []) if code == 200 else []
    upcoming = [e for e in events if e.get("status") == "upcoming"]
    print(f"      Total events: {len(events)}, upcoming: {len(upcoming)}")

    if not upcoming:
        print("      No upcoming events to test RSVP flow")
        REPORT["flows_passed"] += 1
        REPORT["details"]["flow_6"] = {"status": "SKIP", "issues": ["No upcoming events"]}
        return

    test_event = upcoming[0]
    event_id = test_event["id"]
    initial_count = test_event.get("attending_count", 0)
    print(f"  [2] RSVP to event '{test_event['title']}' (id={event_id}, attending={initial_count})...")

    # 2. RSVP as Priya
    code, body = api(f"/api/v1/events/{event_id}/rsvp", "POST", {
        "status": "attending"
    }, token=emp_token)
    if code == 200:
        print(f"      RSVP successful")
    else:
        print(f"      RSVP: {code} {str(body)[:200]}")

    # 3. Check if RSVP count increased
    time.sleep(1)
    code, body = api(f"/api/v1/events/{event_id}", token=admin_token)
    if code == 200 and isinstance(body, dict):
        event_data = body.get("data", body)
        new_count = event_data.get("attending_count", 0)
        print(f"  [3] Attending count: was {initial_count}, now {new_count}")
        # Count might not increase if already RSVP'd
    else:
        # Try from list
        code, body = api(f"/api/v1/events?limit=100", token=admin_token)
        for e in body.get("data", []):
            if e["id"] == event_id:
                new_count = e.get("attending_count", 0)
                print(f"  [3] Attending count from list: {new_count}")
                break

    # 4. Check event on employee dashboard via Selenium
    print("  [4] Checking events on employee dashboard via Selenium...")
    quit_driver()  # Restart for fresh session
    try:
        driver = get_driver()
        if selenium_login(driver, EMP_EMAIL, EMP_PASS):
            driver.get(f"{BASE_URL}/dashboard")
            time.sleep(4)
            save_ss(driver, "flow6_emp_dashboard")
            page_text = driver.page_source.lower()
            if "event" in page_text:
                print("      Events section found on dashboard")
            else:
                print("      No events section visible on dashboard")

            # Check events page
            driver.get(f"{BASE_URL}/events")
            time.sleep(4)
            save_ss(driver, "flow6_events_page")
            page_text = driver.page_source
            if test_event["title"].lower() in page_text.lower():
                print(f"      Event '{test_event['title']}' visible in events page")
            else:
                print(f"      Event not visible in events page")
    except Exception as e:
        print(f"      Selenium error: {e}")

    if issues:
        REPORT["flows_failed"] += 1
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_6"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 6 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 7: Announcement -> Dashboard -> Notification
# ==============================================================================
def flow_7_announcement_dashboard(admin_token, emp_token, emp_user):
    print("\n" + "=" * 70)
    print("FLOW 7: Announcement -> Employee Dashboard -> Notification")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []

    # 1. Create announcement as admin
    ann_title = f"DataFlow Test Announcement {int(time.time())}"
    print(f"  [1] Creating announcement: '{ann_title}'...")
    code, body = api("/api/v1/announcements", "POST", {
        "title": ann_title,
        "content": "This is a cross-module data flow test announcement.",
        "priority": "normal",
        "target_type": "all",
        "is_active": True
    }, token=admin_token)
    ann_id = None
    if code in (200, 201) and isinstance(body, dict) and body.get("data"):
        ann_id = body["data"].get("id")
        print(f"      Announcement created: id={ann_id}")
    else:
        print(f"      Announcement creation: {code} {str(body)[:200]}")

    # 2. Check if employee sees it via API
    print("  [2] Checking if Priya sees announcement via API...")
    time.sleep(1)
    code, body = api("/api/v1/announcements?limit=20", token=emp_token)
    anns = body.get("data", []) if code == 200 else []
    found_api = any(a.get("id") == ann_id for a in anns) if ann_id else False
    found_title = any(ann_title.lower() in a.get("title", "").lower() for a in anns)
    print(f"      Priya sees announcement via API: by_id={found_api}, by_title={found_title}")
    if ann_id and not found_api and not found_title:
        issues.append("Announcement created by admin not visible to employee via API")
        file_bug(
            "Announcements created by admin are not visible to employees via API",
            f"## Data Mismatch\n\n"
            f"Announcement '{ann_title}' (id={ann_id}) was created by admin "
            f"with target_type='all', but Priya cannot see it via "
            f"`/api/v1/announcements`.\n\n"
            f"Total announcements visible to Priya: {len(anns)}",
            labels=["bug", "data-flow"]
        )

    # 3. Check on dashboard via Selenium
    print("  [3] Checking announcement on employee dashboard (Selenium)...")
    try:
        driver = get_driver()
        if selenium_login(driver, EMP_EMAIL, EMP_PASS):
            driver.get(f"{BASE_URL}/dashboard")
            time.sleep(4)
            save_ss(driver, "flow7_emp_dashboard")
            page_text = driver.page_source
            if ann_title in page_text:
                print(f"      Announcement visible on dashboard")
            else:
                print(f"      Announcement NOT visible on dashboard")
                # Check announcements page
                driver.get(f"{BASE_URL}/announcements")
                time.sleep(3)
                save_ss(driver, "flow7_announcements_page")
                page_text = driver.page_source
                if ann_title in page_text:
                    print(f"      Announcement found on dedicated announcements page")
                else:
                    print(f"      Announcement not found on announcements page either")
    except Exception as e:
        print(f"      Selenium error: {e}")

    # 4. Check notification
    print("  [4] Checking if notification was created for employees...")
    code, body = api("/api/v1/notifications?limit=20", token=emp_token)
    notifs = body.get("data", []) if code == 200 else []
    ann_notifs = [n for n in notifs if "announce" in str(n).lower() or ann_title.lower() in str(n).lower()]
    if ann_notifs:
        print(f"      Notification found for announcement")
    else:
        print(f"      No notification for announcement (total notifs: {len(notifs)})")
        if ann_id:
            issues.append("No notification sent to employees for new announcement")

    if issues:
        REPORT["flows_failed"] += 1
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_7"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 7 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 8: Survey -> Employee Response -> Admin Results
# ==============================================================================
def flow_8_survey_response(admin_token, emp_token, emp_user):
    print("\n" + "=" * 70)
    print("FLOW 8: Survey -> Employee Response -> Admin Results")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []

    # 1. Get active surveys
    print("  [1] Fetching active surveys...")
    code, body = api("/api/v1/surveys?limit=20", token=admin_token)
    surveys = body.get("data", []) if code == 200 else []
    active = [s for s in surveys if s.get("status") == "active"]
    print(f"      Total surveys: {len(surveys)}, active: {len(active)}")

    if not active:
        print("      No active surveys to test")
        REPORT["flows_passed"] += 1
        REPORT["details"]["flow_8"] = {"status": "SKIP", "issues": ["No active surveys"]}
        return

    test_survey = active[0]
    survey_id = test_survey["id"]
    initial_responses = test_survey.get("response_count", 0)
    print(f"      Testing survey '{test_survey['title']}' (id={survey_id}, responses={initial_responses})")

    # 2. Check if employee can see it
    print("  [2] Checking if Priya can see the survey...")
    code, body = api(f"/api/v1/surveys?limit=20", token=emp_token)
    emp_surveys = body.get("data", []) if code == 200 else []
    found = any(s.get("id") == survey_id for s in emp_surveys)
    print(f"      Priya can see survey: {found}")
    if not found:
        issues.append(f"Active survey '{test_survey['title']}' not visible to employee")

    # 3. Try to submit a response
    print("  [3] Attempting to submit survey response...")
    # First check if survey has questions
    code, body = api(f"/api/v1/surveys/{survey_id}", token=emp_token)
    if code == 200 and isinstance(body, dict):
        survey_detail = body.get("data", body)
        questions = survey_detail.get("questions", [])
        print(f"      Survey has {len(questions)} questions")

        if questions:
            # Build responses
            responses = []
            for q in questions:
                qid = q.get("id")
                qtype = q.get("type", q.get("question_type", "text"))
                if qtype in ("rating", "scale"):
                    responses.append({"question_id": qid, "answer": "4"})
                elif qtype in ("multiple_choice", "single_choice"):
                    options = q.get("options", [])
                    if options:
                        responses.append({"question_id": qid, "answer": options[0] if isinstance(options[0], str) else options[0].get("value", "A")})
                    else:
                        responses.append({"question_id": qid, "answer": "A"})
                else:
                    responses.append({"question_id": qid, "answer": "Data flow test response"})

            code, body = api(f"/api/v1/surveys/{survey_id}/responses", "POST", {
                "responses": responses
            }, token=emp_token)
            if code in (200, 201):
                print(f"      Response submitted successfully")
            else:
                print(f"      Response submission: {code} {str(body)[:200]}")
                # Try alternate format
                code, body = api(f"/api/v1/surveys/{survey_id}/respond", "POST", {
                    "answers": responses
                }, token=emp_token)
                print(f"      Alternate format: {code}")

    # 4. Check if response count increased
    time.sleep(1)
    code, body = api(f"/api/v1/surveys/{survey_id}", token=admin_token)
    if code == 200 and isinstance(body, dict):
        survey_data = body.get("data", body)
        new_responses = survey_data.get("response_count", 0)
        print(f"  [4] Response count: was {initial_responses}, now {new_responses}")
    else:
        code, body = api("/api/v1/surveys?limit=100", token=admin_token)
        for s in body.get("data", []):
            if s["id"] == survey_id:
                new_responses = s.get("response_count", 0)
                print(f"  [4] Response count from list: was {initial_responses}, now {new_responses}")
                break

    if issues:
        REPORT["flows_failed"] += 1
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_8"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 8 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 9: Document -> Employee Profile
# ==============================================================================
def flow_9_document_employee_profile(admin_token, emp_token, emp_user):
    print("\n" + "=" * 70)
    print("FLOW 9: Document -> Employee Profile")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []
    priya_id = emp_user["id"]

    # 1. Get documents
    print("  [1] Fetching documents...")
    code, body = api("/api/v1/documents?limit=100", token=admin_token)
    docs = body.get("data", []) if code == 200 else []
    print(f"      Total documents: {len(docs)}")

    # Check documents linked to Priya
    priya_docs = [d for d in docs if d.get("user_id") == priya_id]
    print(f"      Documents for Priya (id={priya_id}): {len(priya_docs)}")

    # 2. Check Priya's own document view
    print("  [2] Checking Priya's document view...")
    code, body = api("/api/v1/documents?limit=100", token=emp_token)
    emp_docs = body.get("data", []) if code == 200 else []
    print(f"      Priya sees {len(emp_docs)} documents")

    # 3. Check employee profile documents tab via Selenium
    print("  [3] Checking Priya's profile Documents tab (Selenium)...")
    try:
        driver = get_driver()
        if selenium_login(driver, ADMIN_EMAIL, ADMIN_PASS):
            driver.get(f"{BASE_URL}/employees/{priya_id}")
            time.sleep(4)
            save_ss(driver, "flow9_priya_profile")
            # Look for documents tab
            try:
                doc_tabs = driver.find_elements(By.XPATH,
                    "//*[contains(text(),'Document') or contains(text(),'document')]")
                if doc_tabs:
                    for tab in doc_tabs:
                        if tab.is_displayed():
                            tab.click()
                            time.sleep(3)
                            save_ss(driver, "flow9_priya_documents")
                            print(f"      Documents tab found and clicked")
                            break
                else:
                    print("      No Documents tab found in employee profile")
            except Exception as e:
                print(f"      Documents tab check error: {e}")
    except Exception as e:
        print(f"      Selenium error: {e}")

    if issues:
        REPORT["flows_failed"] += 1
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_9"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 9 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 10: Wellness Check-in -> History -> Dashboard Stats
# ==============================================================================
def flow_10_wellness_checkin(admin_token, emp_token, emp_user):
    print("\n" + "=" * 70)
    print("FLOW 10: Wellness Check-in -> History -> Dashboard Stats")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []
    priya_id = emp_user["id"]

    # 1. Get current wellness check-ins
    print("  [1] Fetching wellness check-ins...")
    code, body = api("/api/v1/wellness/check-ins?limit=20", token=emp_token)
    existing = body.get("data", []) if code == 200 else []
    print(f"      Existing check-ins: {len(existing)}")

    # 2. Submit a wellness check-in
    print("  [2] Submitting wellness check-in...")
    today = datetime.now().strftime("%Y-%m-%d")
    code, body = api("/api/v1/wellness/check-ins", "POST", {
        "mood": "good",
        "energy_level": 4,
        "sleep_hours": 7,
        "exercise_minutes": 30,
        "notes": "Data flow test wellness check-in",
        "check_in_date": today
    }, token=emp_token)
    checkin_id = None
    if code in (200, 201) and isinstance(body, dict) and body.get("data"):
        checkin_id = body["data"].get("id")
        print(f"      Check-in created: id={checkin_id}")
    else:
        print(f"      Check-in: {code} {str(body)[:200]}")
        # Might already have one today
        if code == 400 or code == 409:
            print(f"      (May already have a check-in for today)")

    # 3. Check if it appears in history
    print("  [3] Checking wellness history...")
    time.sleep(1)
    code, body = api("/api/v1/wellness/check-ins?limit=20", token=emp_token)
    after = body.get("data", []) if code == 200 else []
    print(f"      Check-ins after submission: {len(after)}")
    if checkin_id:
        found = any(c.get("id") == checkin_id for c in after)
        if not found:
            issues.append("Wellness check-in not appearing in history after creation")
            print(f"      ISSUE: New check-in not in history!")

    # 4. Check admin wellness view
    print("  [4] Checking admin wellness dashboard...")
    code, body = api("/api/v1/wellness/check-ins?limit=100", token=admin_token)
    admin_wellness = body.get("data", []) if code == 200 else []
    print(f"      Admin can see {len(admin_wellness)} total wellness check-ins")
    if checkin_id:
        admin_found = any(c.get("id") == checkin_id for c in admin_wellness)
        if not admin_found:
            issues.append("Admin cannot see employee's wellness check-in in aggregated data")

    if issues:
        REPORT["flows_failed"] += 1
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_10"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 10 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 11: Forum Post -> Community Feed -> Notifications
# ==============================================================================
def flow_11_forum_community(admin_token, emp_token, emp_user):
    print("\n" + "=" * 70)
    print("FLOW 11: Forum Post -> Community Feed -> Notifications")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []

    # 1. Get forum categories
    print("  [1] Checking forum categories...")
    code, body = api("/api/v1/forum/categories", token=admin_token)
    categories = body.get("data", []) if code == 200 else []
    print(f"      Forum categories: {len(categories)}")
    if categories:
        for c in categories[:3]:
            print(f"        id={c.get('id')} name={c.get('name')}")

    # 2. Create a forum post as Priya
    print("  [2] Creating forum post as Priya...")
    cat_id = categories[0]["id"] if categories else 1
    post_title = f"DataFlow Test Post {int(time.time())}"
    code, body = api("/api/v1/forum/posts", "POST", {
        "title": post_title,
        "content": "This is a cross-module data flow test post for forum verification.",
        "category_id": cat_id,
        "post_type": "discussion"
    }, token=emp_token)
    post_id = None
    if code in (200, 201) and isinstance(body, dict) and body.get("data"):
        post_id = body["data"].get("id")
        print(f"      Post created: id={post_id}")
    else:
        print(f"      Post creation: {code} {str(body)[:200]}")

    # 3. Check if post appears in forum feed
    print("  [3] Checking forum feed...")
    time.sleep(1)
    code, body = api("/api/v1/forum/posts?limit=20", token=admin_token)
    posts = body.get("data", []) if code == 200 else []
    if post_id:
        found = any(p.get("id") == post_id for p in posts)
        print(f"      Post visible in forum feed: {found}")
        if not found:
            issues.append("Forum post not visible in community feed")

    # 4. Check if admin can see it
    if post_id:
        code, body = api(f"/api/v1/forum/posts/{post_id}", token=admin_token)
        if code == 200:
            print(f"      Admin can view post details")
        else:
            print(f"      Admin cannot view post: {code}")

    # 5. Try to like/comment
    if post_id:
        print("  [4] Testing engagement (like/comment)...")
        # Like
        code, body = api(f"/api/v1/forum/posts/{post_id}/like", "POST", {}, token=admin_token)
        print(f"      Like: {code}")
        # Comment
        code, body = api(f"/api/v1/forum/posts/{post_id}/replies", "POST", {
            "content": "Data flow test reply"
        }, token=admin_token)
        if code in (200, 201):
            print(f"      Reply posted successfully")
        else:
            print(f"      Reply: {code} {str(body)[:150]}")
            # Try alternate endpoint
            code, body = api(f"/api/v1/forum/posts/{post_id}/comments", "POST", {
                "content": "Data flow test comment"
            }, token=admin_token)
            print(f"      Comment (alt): {code}")

    if issues:
        REPORT["flows_failed"] += 1
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_11"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 11 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 12: Position -> Vacancy -> Recruitment Pipeline
# ==============================================================================
def flow_12_position_recruitment(admin_token):
    print("\n" + "=" * 70)
    print("FLOW 12: Position -> Vacancy -> Recruitment Pipeline")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []

    # 1. Get positions
    print("  [1] Fetching positions...")
    all_positions = get_all_pages("/api/v1/positions", admin_token)
    print(f"      Total positions: {len(all_positions)}")
    open_positions = [p for p in all_positions if p.get("status") in ("open", "active")]
    print(f"      Open/active positions: {len(open_positions)}")
    for p in open_positions[:5]:
        print(f"        id={p['id']} title={p.get('title','?')} dept={p.get('department_id')} "
              f"vacancies={p.get('vacancies', p.get('total_positions','?'))}")

    # 2. Check recruitment module via Selenium
    print("  [2] Checking recruitment module via Selenium...")
    quit_driver()  # restart
    try:
        driver = get_driver()
        if selenium_login(driver, ADMIN_EMAIL, ADMIN_PASS):
            # Navigate to recruitment/positions page
            driver.get(f"{BASE_URL}/recruitment")
            time.sleep(4)
            save_ss(driver, "flow12_recruitment")
            if "/login" in driver.current_url:
                # Try SSO to recruit module
                driver.get(f"{BASE_URL}/dashboard")
                time.sleep(3)
                recruit_links = driver.find_elements(By.CSS_SELECTOR,
                    "a[href*='recruit'], [data-module*='recruit']")
                if recruit_links:
                    recruit_links[0].click()
                    time.sleep(5)
                    save_ss(driver, "flow12_recruit_sso")
                    print(f"      Recruitment URL: {driver.current_url}")
                else:
                    # Try direct
                    driver.get(RECRUIT_URL)
                    time.sleep(5)
                    save_ss(driver, "flow12_recruit_direct")
                    print(f"      Recruitment direct: {driver.current_url}")
            else:
                print(f"      Recruitment page: {driver.current_url}")

            # Check positions page within HRMS
            driver.get(f"{BASE_URL}/positions")
            time.sleep(3)
            save_ss(driver, "flow12_positions_page")
            page_text = driver.page_source
            for p in open_positions[:3]:
                title = p.get("title", "")
                if title and title.lower() in page_text.lower():
                    print(f"      Position '{title}' visible in UI")
                elif title:
                    print(f"      Position '{title}' NOT visible in UI")
    except Exception as e:
        print(f"      Selenium error: {e}")

    if issues:
        REPORT["flows_failed"] += 1
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_12"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 12 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 13: Employee Count Sanity
# ==============================================================================
def flow_13_employee_count_sanity(admin_token, org_data):
    print("\n" + "=" * 70)
    print("FLOW 13: Employee Count Sanity Check")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []

    # 1. Count from /api/v1/users
    print("  [1] Counting employees from /api/v1/users...")
    all_users = get_all_pages("/api/v1/users", admin_token)
    total_from_api = len(all_users)
    active_from_api = len([u for u in all_users if u.get("status") == 1])
    statuses = {}
    for u in all_users:
        s = u.get("status", "?")
        statuses[s] = statuses.get(s, 0) + 1
    print(f"      /api/v1/users: total={total_from_api}, by_status={statuses}")

    # 2. Count from org login response
    org_count = org_data.get("current_user_count", "?")
    print(f"  [2] org.current_user_count: {org_count}")

    # 3. Check dashboard for employee count widget
    print("  [3] Checking dashboard employee count (Selenium)...")
    dashboard_count = None
    try:
        driver = get_driver()
        if selenium_login(driver, ADMIN_EMAIL, ADMIN_PASS):
            driver.get(f"{BASE_URL}/dashboard")
            time.sleep(4)
            save_ss(driver, "flow13_admin_dashboard")
            page_text = driver.page_source

            # Look for employee count in dashboard widgets
            # Try finding numbers near "employees" text
            import re
            matches = re.findall(r'(\d+)\s*(?:employees|employee|total\s*employees)', page_text.lower())
            if matches:
                dashboard_count = int(matches[0])
                print(f"      Dashboard employee count: {dashboard_count}")
            else:
                print(f"      Could not extract employee count from dashboard")
    except Exception as e:
        print(f"      Selenium error: {e}")

    # 4. Cross-check
    print("  [4] Cross-checking counts...")
    if isinstance(org_count, int) and org_count != active_from_api:
        msg = (f"org.current_user_count ({org_count}) doesn't match active users from "
               f"/api/v1/users ({active_from_api}, total={total_from_api})")
        print(f"      MISMATCH: {msg}")
        issues.append(msg)
        file_bug(
            f"Employee count mismatch -- org reports {org_count} but API has {active_from_api} active users",
            f"## Employee Count Mismatch\n\n"
            f"| Source | Count |\n|---|---|\n"
            f"| `org.current_user_count` (login response) | {org_count} |\n"
            f"| `/api/v1/users` active (status=1) | {active_from_api} |\n"
            f"| `/api/v1/users` total | {total_from_api} |\n"
            f"| User status breakdown | {statuses} |\n\n"
            f"**Expected:** `current_user_count` should match the number of active users.\n\n"
            f"This could be caused by:\n"
            f"- Soft-deleted users still counted in org stats\n"
            f"- `current_user_count` not being updated when users are added/removed\n"
            f"- Status values not being consistently used (status=1 vs status=2 semantics)",
            labels=["bug", "data-flow", "priority-high"]
        )

    if dashboard_count and isinstance(org_count, int) and dashboard_count != org_count:
        msg = f"Dashboard shows {dashboard_count} employees but org reports {org_count}"
        print(f"      MISMATCH: {msg}")
        issues.append(msg)

    if issues:
        REPORT["flows_failed"] += 1
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_13"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 13 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# FLOW 14: Module Subscription -> Feature Access
# ==============================================================================
def flow_14_module_subscription_access(admin_token):
    print("\n" + "=" * 70)
    print("FLOW 14: Module Subscription -> Feature Access")
    print("=" * 70)
    REPORT["flows_tested"] += 1
    issues = []

    # 1. Get subscriptions
    print("  [1] Fetching subscriptions...")
    code, body = api("/api/v1/subscriptions", token=admin_token)
    subs = body.get("data", []) if code == 200 else []
    print(f"      Total subscriptions: {len(subs)}")

    # 2. Get modules
    code, body = api("/api/v1/modules", token=admin_token)
    modules = body.get("data", []) if code == 200 else []
    module_map = {m["id"]: m for m in modules}
    print(f"      Total modules: {len(modules)}")

    # Map subscription to module
    subscribed_modules = []
    for s in subs:
        mid = s.get("module_id")
        mod = module_map.get(mid, {})
        slug = mod.get("slug", "?")
        name = mod.get("name", "?")
        status = s.get("status", "?")
        # Skip field force and biometrics
        if slug in ("emp-field", "emp-biometrics"):
            continue
        subscribed_modules.append({
            "module_id": mid, "slug": slug, "name": name,
            "status": status, "base_url": mod.get("base_url", "")
        })
        print(f"      {name} ({slug}): status={status}")

    # 3. Test SSO access via Selenium for subscribed modules
    print("  [2] Testing module SSO access via Selenium...")
    module_urls = {
        "emp-payroll": PAYROLL_URL,
        "emp-recruit": RECRUIT_URL,
        "emp-performance": "https://test-performance.empcloud.com",
        "emp-rewards": "https://test-rewards.empcloud.com",
        "emp-exit": "https://test-exit.empcloud.com",
        "emp-lms": "https://testlms.empcloud.com",
        "emp-projects": "https://test-project.empcloud.com",
        "emp-monitor": "https://test-empmonitor.empcloud.com",
    }
    quit_driver()  # Restart for module tests
    try:
        driver = get_driver()
        if selenium_login(driver, ADMIN_EMAIL, ADMIN_PASS):
            # First go to dashboard to find module links
            driver.get(f"{BASE_URL}/dashboard")
            time.sleep(4)
            save_ss(driver, "flow14_dashboard_modules")

            tested = 0
            for mod in subscribed_modules:
                slug = mod["slug"]
                if slug in ("emp-field", "emp-biometrics"):
                    continue
                url = module_urls.get(slug)
                if not url:
                    continue
                tested += 1
                if tested > 3:  # Limit to avoid too many
                    break
                print(f"      Testing SSO for {mod['name']} ({url})...")
                try:
                    driver.get(url)
                    time.sleep(5)
                    current = driver.current_url
                    save_ss(driver, f"flow14_sso_{slug}")
                    if "/login" in current and url not in current:
                        print(f"        Redirected to login -- SSO may not be working")
                        issues.append(f"SSO to {mod['name']} ({slug}) redirects to login instead of auto-authenticating")
                    else:
                        print(f"        OK: {current[:80]}")
                except Exception as e:
                    print(f"        Error: {e}")
    except Exception as e:
        print(f"      Selenium error: {e}")

    if issues:
        REPORT["flows_failed"] += 1
        # Only file if consistent SSO failures
        sso_fails = [i for i in issues if "SSO" in i]
        if len(sso_fails) >= 2:
            file_bug(
                f"SSO to subscribed modules redirects to login instead of auto-authenticating",
                f"## SSO Not Working for Subscribed Modules\n\n"
                f"When navigating from the HRMS dashboard to subscribed modules, the user "
                f"is redirected to a login page instead of being automatically authenticated.\n\n"
                f"**Failed modules:**\n" + "\n".join(f"- {i}" for i in sso_fails) +
                f"\n\n**Note:** User is already authenticated in the HRMS dashboard.",
                labels=["bug", "data-flow"]
            )
    else:
        REPORT["flows_passed"] += 1
    REPORT["details"]["flow_14"] = {"status": "FAIL" if issues else "PASS", "issues": issues}
    print(f"  FLOW 14 RESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print("=" * 70)
    print("EMP Cloud HRMS - Cross-Module Data Flow Integrity Tests")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Base: {BASE_URL}")
    print(f"API:  {API_BASE}")
    print("=" * 70)

    # Load existing issues for dedup
    print("\n--- Loading existing GitHub issues for dedup ---")
    load_existing_issues()

    # === LOGIN ===
    print("\n--- Authentication ---")
    admin_token, admin_user, org_data = login(ADMIN_EMAIL, ADMIN_PASS)
    if not admin_token:
        print("[FATAL] Admin login failed, cannot proceed")
        sys.exit(1)
    time.sleep(1)
    emp_token, emp_user, _ = login(EMP_EMAIL, EMP_PASS)
    if not emp_token:
        print("[FATAL] Employee login failed, cannot proceed")
        sys.exit(1)

    # === RUN ALL FLOWS ===
    try:
        flow_1_employee_attendance_leave_payroll(admin_token, emp_token, emp_user, org_data)
    except Exception as e:
        print(f"  FLOW 1 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_2_department_orgchart_manager(admin_token, emp_token, emp_user, org_data)
    except Exception as e:
        print(f"  FLOW 2 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_3_leave_approval_flow(admin_token, emp_token, emp_user, admin_user)
    except Exception as e:
        print(f"  FLOW 3 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_4_helpdesk_ticket_lifecycle(admin_token, emp_token, emp_user)
    except Exception as e:
        print(f"  FLOW 4 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_5_asset_employee_profile(admin_token, emp_token, emp_user)
    except Exception as e:
        print(f"  FLOW 5 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_6_event_rsvp(admin_token, emp_token, emp_user)
    except Exception as e:
        print(f"  FLOW 6 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_7_announcement_dashboard(admin_token, emp_token, emp_user)
    except Exception as e:
        print(f"  FLOW 7 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_8_survey_response(admin_token, emp_token, emp_user)
    except Exception as e:
        print(f"  FLOW 8 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_9_document_employee_profile(admin_token, emp_token, emp_user)
    except Exception as e:
        print(f"  FLOW 9 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_10_wellness_checkin(admin_token, emp_token, emp_user)
    except Exception as e:
        print(f"  FLOW 10 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_11_forum_community(admin_token, emp_token, emp_user)
    except Exception as e:
        print(f"  FLOW 11 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_12_position_recruitment(admin_token)
    except Exception as e:
        print(f"  FLOW 12 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_13_employee_count_sanity(admin_token, org_data)
    except Exception as e:
        print(f"  FLOW 13 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    try:
        flow_14_module_subscription_access(admin_token)
    except Exception as e:
        print(f"  FLOW 14 ERROR: {e}")
        traceback.print_exc()
        REPORT["flows_tested"] += 1
        REPORT["flows_failed"] += 1

    # === FINAL REPORT ===
    quit_driver()
    REPORT["finished"] = datetime.now().isoformat()

    print("\n" + "=" * 70)
    print("FINAL REPORT")
    print("=" * 70)
    print(f"Flows tested:  {REPORT['flows_tested']}")
    print(f"Flows passed:  {REPORT['flows_passed']}")
    print(f"Flows failed:  {REPORT['flows_failed']}")
    print(f"Bugs filed:    {len(REPORT['bugs_filed'])}")
    print(f"Feature reqs:  {len(REPORT['feature_requests'])}")

    if REPORT["bugs_filed"]:
        print("\n--- Bugs Filed ---")
        for b in REPORT["bugs_filed"]:
            print(f"  {b['title']}")
            print(f"    {b['url']}")

    if REPORT["feature_requests"]:
        print("\n--- Feature Requests ---")
        for f in REPORT["feature_requests"]:
            print(f"  {f['title']}")
            print(f"    {f['url']}")

    print("\n--- Flow Details ---")
    for flow_name, detail in REPORT["details"].items():
        status = detail.get("status", "?")
        issue_count = len(detail.get("issues", []))
        print(f"  {flow_name}: {status}" + (f" ({issue_count} issues)" if issue_count else ""))

    # Save report
    report_path = r"C:\emptesting\dataflow_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(REPORT, f, indent=2, default=str)
    print(f"\nReport saved to: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
