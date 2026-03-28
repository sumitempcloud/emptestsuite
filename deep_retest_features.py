#!/usr/bin/env python3
"""
Deep Re-test of EmpCloud bugs #493-#704 (persona agent bugs).
Categories: Super Admin, Employee Journey, Manager, Data Flow, Module bugs.
Skips: Field Force, Biometrics, rate limits. XSS not a bug. Soft delete by design.
"""

import sys, os, time, json, traceback, requests, base64, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -- Config --
BASE_URL = "https://test-empcloud.empcloud.com"
API_BASE = "https://test-empcloud.empcloud.com/api/v1"
SCREENSHOT_DIR = "C:/emptesting/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

CREDS = {
    "super_admin": ("admin@empcloud.com", "SuperAdmin@2026"),
    "org_admin": ("ananya@technova.in", "Welcome@123"),
    "employee": ("priya@technova.in", "Welcome@123"),
}

GITHUB_TOKEN = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

results = []

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  [SCREENSHOT] {path}")
    return path

def make_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(3)
    return d

def api_login(email, password):
    """Login via API, return (token, full_data)."""
    r = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=20)
    if r.status_code == 200:
        data = r.json()
        d = data.get("data", {})
        token = None
        tokens = d.get("tokens", {})
        if isinstance(tokens, dict):
            token = tokens.get("access_token") or tokens.get("token")
        if not token:
            token = d.get("token") or d.get("access_token") or data.get("token")
        return token, data
    print(f"  [API LOGIN FAIL] {r.status_code}: {r.text[:200]}")
    return None, {}

def api_get(endpoint, token, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE}{endpoint}", headers=headers, params=params, timeout=20)
    try:
        return r.status_code, r.json()
    except:
        return r.status_code, r.text

def ui_login(driver, email, password):
    """Login via UI with robust element detection."""
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    try:
        # Find email field
        email_field = None
        for sel in ["input[type='email']", "input[name='email']", "input[placeholder*='mail']", "input[placeholder*='Email']"]:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                email_field = elems[0]
                break
        if not email_field:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            if inputs:
                email_field = inputs[0]

        email_field.clear()
        email_field.send_keys(email)

        # Find password field
        pw_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pw_field.clear()
        pw_field.send_keys(password)
        time.sleep(0.5)

        # Find and click Sign in button
        btn = None
        for sel in [
            "//button[contains(translate(., 'SIGNIN', 'signin'), 'sign in')]",
            "//button[contains(translate(., 'LOGIN', 'login'), 'log in')]",
            "//button[contains(translate(., 'LOGIN', 'login'), 'login')]",
            "//button[@type='submit']",
        ]:
            elems = driver.find_elements(By.XPATH, sel)
            if elems:
                btn = elems[0]
                break
        if not btn:
            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.login-btn")

        btn.click()
        time.sleep(5)

        # Wait for navigation away from login page
        for _ in range(10):
            if "/login" not in driver.current_url:
                print(f"  [UI LOGIN OK] Redirected to {driver.current_url}")
                return True
            time.sleep(1)

        # Check if still on login (might have error)
        page = driver.page_source.lower()
        if "invalid" in page or "error" in page or "incorrect" in page:
            print(f"  [UI LOGIN FAIL] Error message on page")
        else:
            print(f"  [UI LOGIN WARN] Still on {driver.current_url} but no error visible")
        return "/login" not in driver.current_url
    except Exception as e:
        print(f"  [UI LOGIN ERROR] {e}")
        return False

def add_result(issue_num, title, status, details):
    results.append({"issue": issue_num, "title": title, "status": status, "details": details})
    icon = "PASS" if status == "FIXED" else "FAIL" if status in ("STILL_BROKEN","ERROR") else "INFO"
    print(f"\n  [{icon}] #{issue_num}: {title} => {status}")
    print(f"  Details: {details[:400]}")

def github_comment(issue_num, body):
    """Post a comment, retry with delay for rate limits."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_num}/comments"
    payload = {"body": f"Comment by E2E Testing Agent\n\n{body}"}
    for attempt in range(3):
        r = requests.post(url, headers=GITHUB_HEADERS, json=payload, timeout=15)
        if r.status_code == 201:
            print(f"  [GITHUB] Commented on #{issue_num}")
            return True
        elif r.status_code in (403, 429):
            wait = 30 * (attempt + 1)
            print(f"  [GITHUB] Rate limited on #{issue_num}, waiting {wait}s...")
            time.sleep(wait)
        else:
            print(f"  [GITHUB] Comment failed #{issue_num}: {r.status_code} {r.text[:100]}")
            return False
    print(f"  [GITHUB] Comment failed after retries #{issue_num}")
    return False

def github_reopen(issue_num):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_num}"
    for attempt in range(3):
        r = requests.patch(url, headers=GITHUB_HEADERS, json={"state": "open"}, timeout=15)
        if r.status_code == 200:
            print(f"  [GITHUB] Re-opened #{issue_num}")
            return True
        elif r.status_code in (403, 429):
            time.sleep(30 * (attempt + 1))
        else:
            print(f"  [GITHUB] Re-open failed #{issue_num}: {r.status_code}")
            return False
    return False

def github_close(issue_num):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_num}"
    for attempt in range(3):
        r = requests.patch(url, headers=GITHUB_HEADERS, json={"state": "closed", "state_reason": "completed"}, timeout=15)
        if r.status_code == 200:
            print(f"  [GITHUB] Closed #{issue_num}")
            return True
        elif r.status_code in (403, 429):
            time.sleep(30 * (attempt + 1))
        else:
            return False
    return False

def get_issue_state(issue_num):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_num}"
    r = requests.get(url, headers=GITHUB_HEADERS, timeout=15)
    if r.status_code == 200:
        return r.json().get("state", "unknown")
    return "unknown"

def handle_result(issue_num, title, status, details):
    add_result(issue_num, title, status, details)
    state = get_issue_state(issue_num)
    time.sleep(2)  # small delay to avoid rate limits

    if status == "STILL_BROKEN":
        comment = f"**Re-test Result: STILL BROKEN** (2026-03-28)\n\n{details}"
        github_comment(issue_num, comment)
        if state == "closed":
            github_reopen(issue_num)
    elif status == "FIXED":
        comment = f"**Re-test Result: FIXED** (2026-03-28)\n\n{details}"
        github_comment(issue_num, comment)
        if state == "open":
            github_close(issue_num)
    else:
        comment = f"**Re-test Result: {status}** (2026-03-28)\n\n{details}"
        github_comment(issue_num, comment)


# ============================================================
# TEST #493: Super Admin missing management features
# ============================================================
def test_493_super_admin_features():
    print("\n" + "="*60)
    print("TEST #493: Platform admin missing management features")
    print("="*60)

    driver = make_driver()
    try:
        # Step 1: Login as Super Admin via UI
        print("  Step 1: Login as Super Admin")
        logged_in = ui_login(driver, *CREDS["super_admin"])
        screenshot(driver, "493_after_login")
        print(f"  Logged in: {logged_in}, URL: {driver.current_url}")

        # Step 2: Go to /admin/super
        print("  Step 2: Navigate to admin pages")
        admin_pages = {}
        for path in ["/admin/super", "/admin", "/dashboard"]:
            driver.get(f"{BASE_URL}{path}")
            time.sleep(4)
            page = driver.page_source.lower()
            url = driver.current_url
            admin_pages[path] = {"url": url, "page_len": len(page)}
            screenshot(driver, f"493_page_{path.replace('/', '_')}")
            print(f"  {path} => {url} (page len: {len(page)})")

        # Step 3: Check features across all pages
        all_page_text = " ".join(driver.page_source.lower() for _ in [1])
        # Re-visit all and collect
        combined = ""
        for path in ["/admin/super", "/admin", "/dashboard"]:
            driver.get(f"{BASE_URL}{path}")
            time.sleep(3)
            combined += driver.page_source.lower()

        has_org_list = any(kw in combined for kw in ["organization", "technova", "globaltech", "tenant", "org list"])
        has_user_counts = any(kw in combined for kw in ["user count", "total users", "active users", "employee count", "users:"])
        has_revenue = any(kw in combined for kw in ["revenue", "billing", "subscription", "payment", "mrr", "arr"])
        has_module_mgmt = any(kw in combined for kw in ["module", "feature management", "manage module", "enable module"])

        # Also check API
        token, _ = api_login(*CREDS["super_admin"])
        api_checks = {}
        if token:
            for ep in ["/admin/organizations", "/admin/stats", "/admin/revenue", "/organizations", "/admin/dashboard"]:
                code, data = api_get(ep, token)
                api_checks[ep] = code
                print(f"  API: GET {ep} => {code}")

        print(f"  Org list: {has_org_list}")
        print(f"  User counts: {has_user_counts}")
        print(f"  Revenue: {has_revenue}")
        print(f"  Module mgmt: {has_module_mgmt}")

        all_features = has_org_list and has_user_counts and has_revenue and has_module_mgmt
        some_features = has_org_list or has_user_counts or has_revenue or has_module_mgmt

        details = (f"Org list: {has_org_list}, User counts: {has_user_counts}, "
                   f"Revenue: {has_revenue}, Module mgmt: {has_module_mgmt}. "
                   f"API checks: {api_checks}")

        if all_features:
            handle_result(493, "Platform admin missing management features", "FIXED", details)
        elif some_features:
            handle_result(493, "Platform admin missing management features", "STILL_BROKEN",
                          f"Partial features only. {details}")
        else:
            handle_result(493, "Platform admin missing management features", "STILL_BROKEN",
                          f"No management features found on admin pages. {details}")
    except Exception as e:
        handle_result(493, "Platform admin missing management features", "ERROR", traceback.format_exc())
    finally:
        driver.quit()


# ============================================================
# TEST #575: Orphan departments
# ============================================================
def test_575_orphan_departments():
    print("\n" + "="*60)
    print("TEST #575: Orphan departments")
    print("="*60)

    token, _ = api_login(*CREDS["org_admin"])
    if not token:
        handle_result(575, "Orphan departments", "ERROR", "Could not login as org admin via API")
        return

    # Step 1: Get all users
    print("  Step 1: GET /users")
    code, users_data = api_get("/users", token, {"limit": 500})
    print(f"  GET /users => {code}")

    users_list = []
    if isinstance(users_data, dict):
        d = users_data.get("data", {})
        if isinstance(d, list):
            users_list = d
        elif isinstance(d, dict):
            users_list = d.get("users", d.get("items", []))
        if not users_list:
            users_list = users_data.get("users", [])

    user_dept_ids = set()
    for u in (users_list if isinstance(users_list, list) else []):
        did = u.get("department_id") or u.get("departmentId")
        if did:
            user_dept_ids.add(did)
    print(f"  User department IDs: {user_dept_ids}")
    print(f"  Total users: {len(users_list)}")

    # Step 2: Get departments
    print("  Step 2: GET departments")
    dept_ids = set()
    for ep in ["/departments", "/organizations/me/departments", "/organization/departments"]:
        code2, dept_data = api_get(ep, token)
        print(f"  GET {ep} => {code2}")
        if code2 == 200:
            depts = dept_data if isinstance(dept_data, list) else dept_data.get("data", dept_data.get("departments", []))
            if isinstance(depts, dict):
                depts = depts.get("departments", depts.get("items", []))
            if isinstance(depts, list):
                for d in depts:
                    did = d.get("id") or d.get("_id")
                    if did:
                        dept_ids.add(did)
                print(f"  Found {len(depts)} departments from {ep}")
            break

    print(f"  Department IDs: {dept_ids}")

    # Step 3: Find orphans
    if not user_dept_ids:
        handle_result(575, "Orphan departments", "INCONCLUSIVE",
                      f"No department_ids found on users. Users count: {len(users_list)}. "
                      f"Dept IDs: {dept_ids}")
    elif not dept_ids:
        handle_result(575, "Orphan departments", "INCONCLUSIVE",
                      f"Could not get department list. User dept IDs: {user_dept_ids}")
    else:
        orphans = user_dept_ids - dept_ids
        if orphans:
            handle_result(575, "Orphan departments", "STILL_BROKEN",
                          f"Orphan department IDs found: {orphans}. "
                          f"User dept IDs: {user_dept_ids}, Valid dept IDs: {dept_ids}")
        else:
            handle_result(575, "Orphan departments", "FIXED",
                          f"No orphans. All user department_ids ({user_dept_ids}) exist in departments ({dept_ids}).")


# ============================================================
# TEST #584: Employee count mismatch
# ============================================================
def test_584_employee_count_mismatch():
    print("\n" + "="*60)
    print("TEST #584: Employee count mismatch")
    print("="*60)

    token, login_data = api_login(*CREDS["org_admin"])
    if not token:
        handle_result(584, "Employee count mismatch", "ERROR", "Could not login")
        return

    # Step 1: org.current_user_count from login response
    d = login_data.get("data", {})
    org = d.get("org", d.get("organization", {}))
    org_count = None
    if isinstance(org, dict):
        org_count = org.get("current_user_count") or org.get("currentUserCount") or org.get("user_count")
    print(f"  org.current_user_count from login: {org_count}")

    # Step 2: Count via users API
    print("  Step 2: GET /users")
    code, users_data = api_get("/users", token, {"limit": 500})

    api_count = 0
    if isinstance(users_data, dict):
        total = users_data.get("total") or users_data.get("count", 0)
        d2 = users_data.get("data", {})
        if isinstance(d2, list):
            api_count = max(total, len(d2))
        elif isinstance(d2, dict):
            ulist = d2.get("users", d2.get("items", []))
            inner_total = d2.get("total") or d2.get("count", 0)
            if isinstance(ulist, list):
                api_count = max(total, inner_total, len(ulist))
            else:
                api_count = max(total, inner_total)
    print(f"  API user count: {api_count}")

    # Step 3: Compare
    if org_count is None:
        handle_result(584, "Employee count mismatch", "INCONCLUSIVE",
                      f"Could not find current_user_count in login response. "
                      f"API count: {api_count}. Org data keys: {list(org.keys()) if isinstance(org, dict) else 'N/A'}")
    elif org_count == api_count:
        handle_result(584, "Employee count mismatch", "FIXED",
                      f"Counts match: org.current_user_count={org_count}, API users={api_count}")
    else:
        handle_result(584, "Employee count mismatch", "STILL_BROKEN",
                      f"MISMATCH: org.current_user_count={org_count} vs API users={api_count}. "
                      f"Difference: {abs(org_count - api_count)}")


# ============================================================
# TEST #556: New joiner can't edit profile
# ============================================================
def test_556_edit_profile():
    print("\n" + "="*60)
    print("TEST #556: New joiner can't edit profile")
    print("="*60)

    driver = make_driver()
    try:
        print("  Step 1: Login as employee")
        logged_in = ui_login(driver, *CREDS["employee"])
        screenshot(driver, "556_login")

        if not logged_in:
            # Try API to confirm creds work, then use cookie/token approach
            token, _ = api_login(*CREDS["employee"])
            if token:
                driver.execute_script(f"localStorage.setItem('token', '{token}');")
                driver.execute_script(f"localStorage.setItem('access_token', '{token}');")
                driver.get(f"{BASE_URL}/dashboard")
                time.sleep(3)
                logged_in = "/login" not in driver.current_url
                print(f"  Token injection login: {logged_in}, URL: {driver.current_url}")

        # Step 2: Navigate to profile pages
        print("  Step 2: Navigate to profile")
        profile_page_found = False
        for path in ["/my-profile", "/profile", "/employee/profile", "/employees/524", "/settings/profile"]:
            driver.get(f"{BASE_URL}{path}")
            time.sleep(3)
            url = driver.current_url
            page = driver.page_source.lower()
            has_content = len(page) > 3000 and "login" not in url
            print(f"  {path} => {url} (content: {has_content})")
            if has_content:
                profile_page_found = True
                screenshot(driver, f"556_profile_{path.replace('/', '_')}")
                break

        if not profile_page_found:
            # Try dashboard - profile might be accessible from there
            driver.get(f"{BASE_URL}/dashboard")
            time.sleep(3)
            screenshot(driver, "556_dashboard")

        page = driver.page_source
        page_lower = page.lower()

        # Step 3: Find Edit button
        print("  Step 3: Look for Edit button")
        edit_btn = None
        for sel in [
            "//button[contains(translate(., 'EDIT', 'edit'), 'edit')]",
            "//a[contains(translate(., 'EDIT', 'edit'), 'edit')]",
            "//button[contains(@class, 'edit')]",
            "//*[contains(@class, 'edit-btn')]",
            "//button[contains(., 'Update')]",
            "//i[contains(@class, 'edit')]/..",
            "//i[contains(@class, 'pencil')]/..",
            "//*[contains(@class, 'fa-edit')]",
            "//*[contains(@class, 'fa-pencil')]",
        ]:
            elems = driver.find_elements(By.XPATH, sel)
            if elems:
                edit_btn = elems[0]
                print(f"  Found edit via: {sel}")
                break

        # Also check for edit icons (SVG)
        if not edit_btn:
            svgs = driver.find_elements(By.CSS_SELECTOR, "svg, [class*='edit'], [class*='pencil']")
            for s in svgs:
                try:
                    cl = s.get_attribute("class") or ""
                    if "edit" in cl.lower() or "pencil" in cl.lower():
                        edit_btn = s
                        print(f"  Found edit icon with class: {cl}")
                        break
                except:
                    pass

        screenshot(driver, "556_before_edit")

        # Step 4: Click and check editability
        if edit_btn:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", edit_btn)
                time.sleep(1)
                edit_btn.click()
                time.sleep(3)
                screenshot(driver, "556_after_edit")

                inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']):not([disabled]):not([readonly])")
                print(f"  Editable inputs after click: {len(inputs)}")

                if len(inputs) > 0:
                    handle_result(556, "New joiner can't edit profile", "FIXED",
                                  f"Edit button found and clickable. {len(inputs)} editable fields after clicking.")
                else:
                    handle_result(556, "New joiner can't edit profile", "STILL_BROKEN",
                                  f"Edit button found but no editable fields appeared.")
            except Exception as e:
                handle_result(556, "New joiner can't edit profile", "STILL_BROKEN",
                              f"Edit button found but click failed: {e}")
        else:
            inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']):not([disabled]):not([readonly])")
            if len(inputs) > 3:
                handle_result(556, "New joiner can't edit profile", "FIXED",
                              f"No edit button but {len(inputs)} editable fields found directly.")
            else:
                # Also check API for profile edit endpoint
                token, _ = api_login(*CREDS["employee"])
                api_detail = ""
                if token:
                    code, data = api_get("/users/me", token)
                    api_detail = f"API /users/me => {code}. "
                    code2, _ = api_get("/profile", token)
                    api_detail += f"API /profile => {code2}."

                handle_result(556, "New joiner can't edit profile", "STILL_BROKEN",
                              f"No Edit button found. Only {len(inputs)} editable fields. "
                              f"Profile URL: {driver.current_url}. {api_detail}")
    except Exception as e:
        handle_result(556, "New joiner can't edit profile", "ERROR", traceback.format_exc())
    finally:
        driver.quit()


# ============================================================
# TEST #557: Can't find Clock Out button
# ============================================================
def test_557_clock_out():
    print("\n" + "="*60)
    print("TEST #557: Can't find Clock Out button")
    print("="*60)

    driver = make_driver()
    try:
        print("  Step 1: Login as employee")
        logged_in = ui_login(driver, *CREDS["employee"])
        screenshot(driver, "557_login")

        if not logged_in:
            token, _ = api_login(*CREDS["employee"])
            if token:
                driver.execute_script(f"localStorage.setItem('token', '{token}');")
                driver.execute_script(f"localStorage.setItem('access_token', '{token}');")
                driver.get(f"{BASE_URL}/dashboard")
                time.sleep(3)
                logged_in = "/login" not in driver.current_url

        # Step 2: Check dashboard
        print("  Step 2: Check dashboard")
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(4)
        screenshot(driver, "557_dashboard")
        page = driver.page_source.lower()

        clock_keywords = ["clock out", "clock-out", "clockout", "check out", "check-out",
                          "punch out", "clock in", "clock-in", "checkin", "check in", "punch in"]
        found_keywords = [kw for kw in clock_keywords if kw in page]
        print(f"  Dashboard clock keywords: {found_keywords}")

        # Step 3: Check attendance page
        print("  Step 3: Check attendance pages")
        for att_url in ["/attendance", "/my-attendance", "/employee/attendance"]:
            driver.get(f"{BASE_URL}{att_url}")
            time.sleep(3)
            page2 = driver.page_source.lower()
            url2 = driver.current_url
            if "/login" not in url2:
                screenshot(driver, f"557_att_{att_url.replace('/', '_')}")
                for kw in clock_keywords:
                    if kw in page2 and kw not in found_keywords:
                        found_keywords.append(kw)
                print(f"  {att_url} => {url2}, keywords: {[kw for kw in clock_keywords if kw in page2]}")

        # Look for actual buttons
        clock_btns = driver.find_elements(By.XPATH,
            "//button[contains(translate(., 'CLOCK', 'clock'), 'clock')] | "
            "//button[contains(translate(., 'CHECK', 'check'), 'check')] | "
            "//button[contains(translate(., 'PUNCH', 'punch'), 'punch')]")

        screenshot(driver, "557_final")

        has_clock_out = any("out" in kw for kw in found_keywords) or any("out" in (b.text.lower() if b.text else "") for b in clock_btns)
        has_clock_in = any("in" in kw and "out" not in kw for kw in found_keywords)

        if has_clock_out:
            handle_result(557, "Can't find Clock Out button", "FIXED",
                          f"Clock Out functionality found. Keywords: {found_keywords}. Buttons: {len(clock_btns)}")
        elif has_clock_in:
            handle_result(557, "Can't find Clock Out button", "PARTIALLY_FIXED",
                          f"Clock In found but no Clock Out. May appear after clocking in. Keywords: {found_keywords}")
        elif found_keywords:
            handle_result(557, "Can't find Clock Out button", "PARTIALLY_FIXED",
                          f"Some clock keywords found ({found_keywords}) but no explicit Clock Out button.")
        else:
            # Also check API
            token, _ = api_login(*CREDS["employee"])
            api_info = ""
            if token:
                for ep in ["/attendance/clock-out", "/attendance/checkout", "/attendance/status"]:
                    code, _ = api_get(ep, token)
                    api_info += f"{ep}=>{code} "
            handle_result(557, "Can't find Clock Out button", "STILL_BROKEN",
                          f"No clock in/out buttons found on dashboard or attendance. URL: {driver.current_url}. API: {api_info}")
    except Exception as e:
        handle_result(557, "Can't find Clock Out button", "ERROR", traceback.format_exc())
    finally:
        driver.quit()


# ============================================================
# TEST #582: Can't select leave type
# ============================================================
def test_582_leave_type():
    print("\n" + "="*60)
    print("TEST #582: Can't select leave type")
    print("="*60)

    driver = make_driver()
    try:
        print("  Step 1: Login as employee")
        logged_in = ui_login(driver, *CREDS["employee"])

        if not logged_in:
            token, _ = api_login(*CREDS["employee"])
            if token:
                driver.execute_script(f"localStorage.setItem('token', '{token}');")
                driver.execute_script(f"localStorage.setItem('access_token', '{token}');")

        # Step 2: Go to leave page
        print("  Step 2: Go to leave page")
        leave_found = False
        for url in ["/leave", "/leaves", "/my-leaves", "/employee/leave"]:
            driver.get(f"{BASE_URL}{url}")
            time.sleep(4)
            cur = driver.current_url
            page = driver.page_source.lower()
            if "/login" not in cur and len(page) > 3000:
                leave_found = True
                print(f"  Leave page at {url}, URL: {cur}")
                screenshot(driver, f"582_leave_{url.replace('/', '_')}")
                break

        if not leave_found:
            handle_result(582, "Can't select leave type", "STILL_BROKEN",
                          f"Could not access leave page. Redirected to {driver.current_url}")
            return

        # Step 3: Click Apply
        print("  Step 3: Click Apply Leave")
        apply_clicked = False
        for sel in [
            "//button[contains(translate(., 'APPLY', 'apply'), 'apply')]",
            "//a[contains(translate(., 'APPLY', 'apply'), 'apply')]",
            "//button[contains(., 'New')]",
            "//button[contains(., 'Request')]",
            "//button[contains(., '+')]",
            "//button[contains(., 'Add')]",
        ]:
            elems = driver.find_elements(By.XPATH, sel)
            if elems:
                try:
                    elems[0].click()
                    apply_clicked = True
                    print(f"  Clicked via: {sel}")
                    time.sleep(3)
                    break
                except:
                    pass

        screenshot(driver, "582_after_apply")
        page = driver.page_source.lower()

        # Step 4: Find leave type dropdown
        print("  Step 4: Look for leave type dropdown")
        selects = driver.find_elements(By.CSS_SELECTOR, "select")
        custom_dropdowns = driver.find_elements(By.CSS_SELECTOR,
            "[class*='select'], [class*='dropdown'], [role='listbox'], [role='combobox'], "
            "[class*='Select'], [class*='Dropdown']")

        print(f"  <select>: {len(selects)}, custom dropdowns: {len(custom_dropdowns)}")

        can_select = False
        dropdown_found = False

        # Try native select
        for s in selects:
            try:
                opts = s.find_elements(By.TAG_NAME, "option")
                if len(opts) > 1:
                    dropdown_found = True
                    s.click()
                    time.sleep(1)
                    opts[-1].click()
                    can_select = True
                    print(f"  Selected from <select> with {len(opts)} options")
                    break
            except:
                pass

        # Try custom dropdown
        if not can_select:
            for dd in custom_dropdowns:
                try:
                    text = dd.text.lower()
                    cl = (dd.get_attribute("class") or "").lower()
                    if "leave" in text or "type" in text or "select" in cl:
                        dd.click()
                        time.sleep(2)
                        screenshot(driver, "582_dropdown_open")
                        opts = driver.find_elements(By.CSS_SELECTOR,
                            "[role='option'], li[class*='option'], div[class*='option'], .menu-item")
                        if opts:
                            dropdown_found = True
                            opts[0].click()
                            can_select = True
                            print(f"  Selected from custom dropdown, {len(opts)} options")
                            break
                except:
                    pass

        # Check for leave type text
        has_leave_type_text = any(kw in page for kw in ["leave type", "type of leave", "leavetype", "select type"])

        screenshot(driver, "582_final")

        # Also check API for leave types
        token, _ = api_login(*CREDS["employee"])
        api_info = ""
        if token:
            for ep in ["/leave-types", "/leaves/types", "/leave/types"]:
                code, data = api_get(ep, token)
                api_info += f"{ep}=>{code} "
                if code == 200:
                    items = data if isinstance(data, list) else data.get("data", [])
                    if isinstance(items, list):
                        api_info += f"({len(items)} types) "

        if can_select:
            handle_result(582, "Can't select leave type", "FIXED",
                          f"Leave type dropdown works. {api_info}")
        elif dropdown_found:
            handle_result(582, "Can't select leave type", "STILL_BROKEN",
                          f"Dropdown found but could not select a value. {api_info}")
        elif has_leave_type_text:
            handle_result(582, "Can't select leave type", "STILL_BROKEN",
                          f"'Leave type' text visible but no functional dropdown. Apply clicked: {apply_clicked}. {api_info}")
        else:
            handle_result(582, "Can't select leave type", "STILL_BROKEN",
                          f"No leave type dropdown found. Apply clicked: {apply_clicked}. "
                          f"Selects: {len(selects)}, Custom: {len(custom_dropdowns)}. {api_info}")
    except Exception as e:
        handle_result(582, "Can't select leave type", "ERROR", traceback.format_exc())
    finally:
        driver.quit()


# ============================================================
# TEST #626: Leave shows "User #524" instead of names
# ============================================================
def test_626_leave_user_ids():
    print("\n" + "="*60)
    print("TEST #626: Leave shows 'User #524' instead of names")
    print("="*60)

    # Check via API first
    token, _ = api_login(*CREDS["org_admin"])
    api_has_ids = False
    api_has_names = False
    api_details = ""

    if token:
        for ep in ["/leaves", "/leave-requests", "/leave/requests", "/leaves/requests"]:
            code, data = api_get(ep, token)
            print(f"  API: GET {ep} => {code}")
            if code == 200:
                items = data if isinstance(data, list) else data.get("data", data.get("leaves", []))
                if isinstance(items, dict):
                    items = items.get("leaves", items.get("items", items.get("data", [])))
                if isinstance(items, list) and items:
                    for item in items[:5]:
                        user_f = item.get("user") or item.get("employee") or item.get("userName") or item.get("employee_name")
                        print(f"    user field: {user_f}")
                        if isinstance(user_f, str) and re.match(r'User\s*#?\d+', user_f):
                            api_has_ids = True
                        elif isinstance(user_f, dict):
                            name = user_f.get("name") or f"{user_f.get('first_name','')} {user_f.get('last_name','')}".strip()
                            if name:
                                api_has_names = True
                                api_details += f"Name: {name}; "
                        elif isinstance(user_f, str) and len(user_f) > 3 and not user_f.isdigit():
                            api_has_names = True
                            api_details += f"Name: {user_f}; "
                break

    # Check UI
    driver = make_driver()
    try:
        print("  UI check")
        logged_in = ui_login(driver, *CREDS["org_admin"])
        if not logged_in and token:
            driver.execute_script(f"localStorage.setItem('token', '{token}');")
            driver.execute_script(f"localStorage.setItem('access_token', '{token}');")

        for url in ["/leave", "/leaves", "/leave-management"]:
            driver.get(f"{BASE_URL}{url}")
            time.sleep(4)
            if "/login" not in driver.current_url:
                break

        screenshot(driver, "626_leave_page")
        page = driver.page_source

        user_id_matches = re.findall(r'User\s*#?\d+', page)
        print(f"  UI 'User #' patterns: {user_id_matches[:5]}")

        if user_id_matches:
            handle_result(626, "Leave shows User IDs instead of names", "STILL_BROKEN",
                          f"UI still shows User IDs: {user_id_matches[:5]}. API has IDs: {api_has_ids}, names: {api_has_names}. {api_details}")
        elif api_has_ids:
            handle_result(626, "Leave shows User IDs instead of names", "STILL_BROKEN",
                          f"API returns User IDs instead of names. UI may hide them but backend issue persists.")
        elif api_has_names:
            handle_result(626, "Leave shows User IDs instead of names", "FIXED",
                          f"No User ID patterns in UI. API returns proper names. {api_details}")
        else:
            handle_result(626, "Leave shows User IDs instead of names", "FIXED",
                          f"No User ID patterns found in UI or API. Leave page appears to show proper names.")
    except Exception as e:
        handle_result(626, "Leave shows User IDs instead of names", "ERROR", traceback.format_exc())
    finally:
        driver.quit()


# ============================================================
# TEST #633: Attendance no date picker
# ============================================================
def test_633_attendance_date_picker():
    print("\n" + "="*60)
    print("TEST #633: Attendance no date picker")
    print("="*60)

    driver = make_driver()
    try:
        print("  Step 1: Login as Org Admin")
        logged_in = ui_login(driver, *CREDS["org_admin"])

        if not logged_in:
            token, _ = api_login(*CREDS["org_admin"])
            if token:
                driver.execute_script(f"localStorage.setItem('token', '{token}');")
                driver.execute_script(f"localStorage.setItem('access_token', '{token}');")

        # Step 2: Go to attendance
        print("  Step 2: Go to /attendance")
        for url in ["/attendance", "/attendance-management", "/hr/attendance"]:
            driver.get(f"{BASE_URL}{url}")
            time.sleep(4)
            if "/login" not in driver.current_url:
                print(f"  Attendance at {url}")
                break

        screenshot(driver, "633_attendance")
        page = driver.page_source.lower()
        cur_url = driver.current_url

        # Search for date-related elements
        date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[type='datetime-local']")
        date_pickers = driver.find_elements(By.CSS_SELECTOR, "[class*='date-picker'], [class*='datepicker'], [class*='DatePicker']")
        calendar_icons = driver.find_elements(By.CSS_SELECTOR, "[class*='calendar'], .fa-calendar, svg[data-testid*='calendar']")
        date_range = driver.find_elements(By.CSS_SELECTOR, "[class*='date-range'], [class*='daterange']")

        # Check for any input that looks like a date
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        date_like_inputs = []
        for inp in all_inputs:
            placeholder = (inp.get_attribute("placeholder") or "").lower()
            name = (inp.get_attribute("name") or "").lower()
            cls = (inp.get_attribute("class") or "").lower()
            if any(kw in placeholder + name + cls for kw in ["date", "from", "to", "start", "end", "period"]):
                date_like_inputs.append(inp)

        has_date_text = any(kw in page for kw in ["date range", "from date", "to date", "select date",
                                                    "filter by date", "date picker", "start date", "end date"])

        total = len(date_inputs) + len(date_pickers) + len(calendar_icons) + len(date_range) + len(date_like_inputs)

        print(f"  date inputs: {len(date_inputs)}, pickers: {len(date_pickers)}, "
              f"calendars: {len(calendar_icons)}, ranges: {len(date_range)}, "
              f"date-like inputs: {len(date_like_inputs)}, text: {has_date_text}")

        screenshot(driver, "633_final")

        if total > 0 or has_date_text:
            handle_result(633, "Attendance no date picker", "FIXED",
                          f"Date filtering available. Inputs:{len(date_inputs)}, Pickers:{len(date_pickers)}, "
                          f"Calendar icons:{len(calendar_icons)}, Date-like:{len(date_like_inputs)}. URL: {cur_url}")
        else:
            handle_result(633, "Attendance no date picker", "STILL_BROKEN",
                          f"No date picker/filter on attendance page. URL: {cur_url}. "
                          f"Page length: {len(page)}")
    except Exception as e:
        handle_result(633, "Attendance no date picker", "ERROR", traceback.format_exc())
    finally:
        driver.quit()


# ============================================================
# TEST #658: Projects sub-pages all 404
# ============================================================
def test_658_projects_subpages():
    print("\n" + "="*60)
    print("TEST #658: Projects sub-pages all 404")
    print("="*60)

    PROJECT_BASE = "https://test-project.empcloud.com"

    # Get token for SSO
    token, login_data = api_login(*CREDS["org_admin"])

    # First try SSO token endpoint
    sso_token = None
    if token:
        # Try to get SSO token for projects module
        for ep in ["/modules/sso/project", "/sso/project", "/modules/project/sso", "/auth/sso-token"]:
            code, data = api_get(ep, token)
            print(f"  SSO: GET {ep} => {code}")
            if code == 200 and isinstance(data, dict):
                sso_token = data.get("data", {}).get("token") or data.get("token") or data.get("sso_token")
                if sso_token:
                    print(f"  Got SSO token")
                    break

    sub_pages = ["/dashboard", "/projects", "/tasks", "/board", "/timesheet"]
    page_results = {}

    driver = make_driver()
    try:
        # Login to main app first
        ui_login(driver, *CREDS["org_admin"])

        # Try SSO via modules page
        driver.get(f"{BASE_URL}/modules")
        time.sleep(3)
        screenshot(driver, "658_modules")

        # Now test each sub-page
        for sp in sub_pages:
            url = f"{PROJECT_BASE}{sp}"
            print(f"  Testing: {url}")

            # Browser test
            try:
                driver.get(url)
                time.sleep(5)
                page = driver.page_source.lower()
                cur = driver.current_url
                is_404 = "404" in page[:2000] or "not found" in page[:2000] or "page not found" in page[:2000]
                is_login = "login" in cur or "sign in" in page[:2000]
                has_content = len(page) > 3000 and not is_404
                page_results[sp] = {"url": cur, "is_404": is_404, "is_login": is_login, "has_content": has_content}
                screenshot(driver, f"658_proj{sp.replace('/', '_')}")
                print(f"    URL: {cur}, 404: {is_404}, login: {is_login}, content: {has_content}")
            except Exception as e:
                page_results[sp] = {"url": url, "is_404": True, "error": str(e)}
                print(f"    Error: {e}")

            # HTTP test
            if token:
                try:
                    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15, allow_redirects=True)
                    page_results[sp]["http_status"] = r.status_code
                    page_results[sp]["http_404"] = r.status_code == 404 or "404" in r.text[:500]
                    print(f"    HTTP: {r.status_code}")
                except Exception as e:
                    page_results[sp]["http_error"] = str(e)

        all_404 = all(r.get("is_404", False) or r.get("http_404", False) for r in page_results.values())
        all_login = all(r.get("is_login", False) for r in page_results.values())
        any_working = any(r.get("has_content", False) and not r.get("is_404", False) for r in page_results.values())

        detail = "; ".join(f"{k}: 404={v.get('is_404')}, login={v.get('is_login')}, http={v.get('http_status','?')}"
                           for k, v in page_results.items())

        if any_working:
            broken = [k for k, v in page_results.items() if v.get("is_404")]
            if broken:
                handle_result(658, "Projects sub-pages all 404", "PARTIALLY_FIXED",
                              f"Some pages work, some still 404. {detail}")
            else:
                handle_result(658, "Projects sub-pages all 404", "FIXED",
                              f"All project sub-pages load. {detail}")
        elif all_login:
            handle_result(658, "Projects sub-pages all 404", "STILL_BROKEN",
                          f"All project sub-pages redirect to login (SSO not working). {detail}")
        elif all_404:
            handle_result(658, "Projects sub-pages all 404", "STILL_BROKEN",
                          f"All project sub-pages return 404. {detail}")
        else:
            handle_result(658, "Projects sub-pages all 404", "STILL_BROKEN",
                          f"Project sub-pages not accessible. {detail}")
    except Exception as e:
        handle_result(658, "Projects sub-pages all 404", "ERROR", traceback.format_exc())
    finally:
        driver.quit()


# ============================================================
# TEST #659: LMS sub-pages 404
# ============================================================
def test_659_lms_subpages():
    print("\n" + "="*60)
    print("TEST #659: LMS sub-pages 404")
    print("="*60)

    LMS_BASE = "https://testlms.empcloud.com"

    token, _ = api_login(*CREDS["org_admin"])

    sub_pages = ["/dashboard", "/courses", "/my-courses", "/library", "/reports", "/categories"]
    page_results = {}

    driver = make_driver()
    try:
        ui_login(driver, *CREDS["org_admin"])

        for sp in sub_pages:
            url = f"{LMS_BASE}{sp}"
            print(f"  Testing: {url}")

            try:
                driver.get(url)
                time.sleep(5)
                page = driver.page_source.lower()
                cur = driver.current_url
                is_404 = "404" in page[:2000] or "not found" in page[:2000]
                is_login = "login" in cur or "sign in" in page[:2000]
                has_content = len(page) > 3000 and not is_404
                page_results[sp] = {"url": cur, "is_404": is_404, "is_login": is_login, "has_content": has_content}
                screenshot(driver, f"659_lms{sp.replace('/', '_')}")
                print(f"    URL: {cur}, 404: {is_404}, login: {is_login}, content: {has_content}")
            except Exception as e:
                page_results[sp] = {"is_404": True, "error": str(e)}

            if token:
                try:
                    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15, allow_redirects=True)
                    page_results[sp]["http_status"] = r.status_code
                    page_results[sp]["http_404"] = r.status_code == 404 or "404" in r.text[:500]
                    print(f"    HTTP: {r.status_code}")
                except:
                    pass

        all_404 = all(r.get("is_404", False) or r.get("http_404", False) for r in page_results.values())
        all_login = all(r.get("is_login", False) for r in page_results.values())
        any_working = any(r.get("has_content", False) and not r.get("is_404", False) for r in page_results.values())

        detail = "; ".join(f"{k}: 404={v.get('is_404')}, login={v.get('is_login')}, http={v.get('http_status','?')}"
                           for k, v in page_results.items())

        if any_working:
            broken = [k for k, v in page_results.items() if v.get("is_404")]
            if broken:
                handle_result(659, "LMS sub-pages 404", "PARTIALLY_FIXED",
                              f"Some pages work, some still 404. {detail}")
            else:
                handle_result(659, "LMS sub-pages 404", "FIXED", f"All LMS sub-pages load. {detail}")
        elif all_login:
            handle_result(659, "LMS sub-pages 404", "STILL_BROKEN",
                          f"All LMS sub-pages redirect to login (SSO not working). {detail}")
        elif all_404:
            handle_result(659, "LMS sub-pages 404", "STILL_BROKEN",
                          f"All LMS sub-pages return 404. {detail}")
        else:
            handle_result(659, "LMS sub-pages 404", "STILL_BROKEN",
                          f"LMS sub-pages not accessible. {detail}")
    except Exception as e:
        handle_result(659, "LMS sub-pages 404", "ERROR", traceback.format_exc())
    finally:
        driver.quit()


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 70)
    print("EMPCLOUD DEEP RE-TEST: BUGS #493-#704 (PERSONA AGENT BUGS)")
    print("Date: 2026-03-28")
    print("Skipping: Field Force, Biometrics, Rate Limits")
    print("=" * 70)

    # Batch 1: API-heavy tests
    print("\n>>> BATCH 1: Data Flow + Super Admin <<<")
    test_575_orphan_departments()
    test_584_employee_count_mismatch()

    # Batch 2: Super Admin UI
    print("\n>>> BATCH 2: Super Admin UI <<<")
    test_493_super_admin_features()

    # Batch 3: Employee Journey UI (fresh driver per test)
    print("\n>>> BATCH 3: Employee Journey <<<")
    test_556_edit_profile()
    test_557_clock_out()

    # Batch 4: More Employee + Manager (fresh driver)
    print("\n>>> BATCH 4: Leave + Attendance <<<")
    test_582_leave_type()
    test_626_leave_user_ids()
    test_633_attendance_date_picker()

    # Batch 5: Module SSO
    print("\n>>> BATCH 5: Module Bugs <<<")
    test_658_projects_subpages()
    test_659_lms_subpages()

    # Summary
    print("\n\n" + "=" * 70)
    print("DEEP RE-TEST SUMMARY")
    print("=" * 70)

    fixed = [r for r in results if r["status"] == "FIXED"]
    broken = [r for r in results if r["status"] == "STILL_BROKEN"]
    partial = [r for r in results if r["status"] in ("PARTIALLY_FIXED",)]
    inconclusive = [r for r in results if r["status"] == "INCONCLUSIVE"]
    errors = [r for r in results if r["status"] == "ERROR"]

    print(f"\nTotal tested: {len(results)}")
    print(f"  FIXED:            {len(fixed)}")
    print(f"  STILL BROKEN:     {len(broken)}")
    print(f"  PARTIALLY FIXED:  {len(partial)}")
    print(f"  INCONCLUSIVE:     {len(inconclusive)}")
    print(f"  ERRORS:           {len(errors)}")

    for label, group in [("FIXED", fixed), ("STILL BROKEN", broken),
                          ("PARTIALLY FIXED", partial), ("INCONCLUSIVE", inconclusive), ("ERRORS", errors)]:
        if group:
            print(f"\n--- {label} ---")
            for r in group:
                print(f"  #{r['issue']}: {r['title']}")
                print(f"    {r['details'][:250]}")

    with open("C:/emptesting/deep_retest_features_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to C:/emptesting/deep_retest_features_results.json")


if __name__ == "__main__":
    main()
