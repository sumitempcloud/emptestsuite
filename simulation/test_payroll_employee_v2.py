"""
PAYROLL MODULE - EMPLOYEE ROLE TEST v2 (follow-up)
Focus: Admin Panel access, remaining screenshots, deeper checks
"""

import sys, os, time, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_payroll_employee"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
PAYROLL_URL = "https://testpayroll.empcloud.com"
PAYROLL_API = "https://testpayroll-api.empcloud.com"
EMAIL = "priya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

bugs = []

def ss(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  [SS] {name}.png")

def file_bug(title, body):
    bugs.append(title)
    print(f"  [BUG] {title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"},
            json={"title": title, "body": body, "labels": ["bug"]}
        )
        if resp.status_code == 201:
            print(f"  [GITHUB] Issue #{resp.json().get('number')}: {resp.json().get('html_url')}")
        else:
            print(f"  [GITHUB] Failed: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"  [GITHUB] Error: {e}")

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(3)
    return driver

def get_token():
    resp = requests.post(f"{API_BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("data", {}).get("tokens", {}).get("access_token")

def sso_login(driver):
    token = get_token()
    if not token:
        print("  FATAL: Cannot get token")
        return False
    driver.get(f"{PAYROLL_URL}?sso_token={token}")
    time.sleep(5)
    try:
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
    except:
        pass
    time.sleep(2)
    body = driver.find_element(By.TAG_NAME, "body").text.lower()
    if "welcome" in body or "/my" in driver.current_url:
        return True
    # Retry once
    print("  First SSO attempt failed, retrying...")
    token = get_token()
    driver.get(f"{PAYROLL_URL}?sso_token={token}")
    time.sleep(5)
    return "/my" in driver.current_url or "welcome" in driver.find_element(By.TAG_NAME, "body").text.lower()

def click_link(driver, text_match):
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        try:
            if text_match.lower() in link.text.strip().lower():
                driver.execute_script("arguments[0].click();", link)
                time.sleep(3)
                WebDriverWait(driver, 8).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(2)
                return True
        except:
            continue
    return False

def get_body(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""

def run():
    driver = get_driver()
    try:
        # =====================================================
        # PART A: Admin Panel investigation
        # =====================================================
        print("\n" + "="*60)
        print("PART A: Admin Panel Access Investigation")
        print("="*60)

        if not sso_login(driver):
            print("  FATAL: SSO login failed")
            ss(driver, "v2_sso_failed")
            return

        print(f"  Logged in. URL: {driver.current_url}")
        ss(driver, "v2_01_dashboard")

        # Check if Admin Panel link exists
        links = driver.find_elements(By.TAG_NAME, "a")
        admin_link = None
        for link in links:
            try:
                if "admin" in link.text.strip().lower():
                    admin_link = link
                    href = link.get_attribute("href") or ""
                    print(f"  Found admin link: '{link.text.strip()}' -> {href}")
                    break
            except:
                continue

        if admin_link:
            print("  FINDING: 'Admin Panel' link visible to employee in sidebar")
            # Click it
            try:
                href = admin_link.get_attribute("href") or ""
                driver.execute_script("arguments[0].click();", admin_link)
                time.sleep(4)
                WebDriverWait(driver, 8).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(2)
            except:
                pass

            ss(driver, "v2_02_admin_panel_clicked")
            url = driver.current_url
            body = get_body(driver)
            print(f"  URL after click: {url}")
            print(f"  Body (500 chars): {body[:500]}")

            # Check if admin content is accessible
            admin_keywords = ["run payroll", "manage employee", "salary component", "payroll settings",
                              "all employees", "employee list", "process payroll", "dashboard",
                              "salary structure", "configuration", "settings"]
            found_admin_content = [k for k in admin_keywords if k in body.lower()]

            if found_admin_content:
                print(f"  SECURITY BUG: Employee can access admin features: {found_admin_content}")
                ss(driver, "v2_02_SECURITY_admin_access")
                file_bug(
                    "[Payroll Employee] Employee can access Admin Panel with admin features visible",
                    f"**Severity: High**\n\n"
                    f"Employee `{EMAIL}` (role: employee) can click 'Admin Panel' in the sidebar and access admin features.\n\n"
                    f"**Steps to reproduce:**\n"
                    f"1. Login as employee `{EMAIL}`\n"
                    f"2. Click 'Admin Panel' in sidebar\n"
                    f"3. Admin features visible: {found_admin_content}\n\n"
                    f"**URL:** {url}\n\n"
                    f"**Expected:** Admin Panel link should not be visible to employee role, or clicking it should show access denied.\n\n"
                    f"**Actual:** Admin features are accessible."
                )

                # Try to navigate to specific admin pages
                admin_pages = ["/dashboard", "/employees", "/salary-structures", "/run-payroll",
                               "/settings", "/components", "/payroll"]
                for page in admin_pages:
                    full_url = url.rstrip("/") + page if "/admin" in url else f"{PAYROLL_URL}/admin{page}"
                    driver.get(full_url)
                    time.sleep(3)
                    ss(driver, f"v2_03_admin{page.replace('/','_')}")
                    pbody = get_body(driver)
                    print(f"  Admin page {page}: {driver.current_url} - {pbody[:200]}")
            elif "access denied" in body.lower() or "unauthorized" in body.lower() or "not authorized" in body.lower():
                print("  Admin Panel click resulted in access denied - GOOD")
                # But link is still visible which is a minor UI issue
                file_bug(
                    "[Payroll Employee] Admin Panel link visible in sidebar for employee role",
                    f"Employee `{EMAIL}` can see an 'Admin Panel' link in the sidebar navigation.\n\n"
                    f"While clicking it does show access denied, the link should be hidden for employee role users "
                    f"to avoid confusion and follow principle of least privilege.\n\n"
                    f"**Steps to reproduce:**\n"
                    f"1. Login as employee `{EMAIL}` to payroll module\n"
                    f"2. Observe sidebar navigation\n"
                    f"3. 'Admin Panel' link is visible\n\n"
                    f"**Expected:** Link should be hidden for employee role.\n"
                    f"**Actual:** Link is visible (though access may be denied on click)."
                )
            else:
                # Link visible, clicked somewhere, check what happened
                if "/my" in url or "login" in url.lower():
                    print("  Admin Panel redirected to dashboard/login - partially OK but link should be hidden")
                    file_bug(
                        "[Payroll Employee] Admin Panel link visible in sidebar for employee role",
                        f"Employee `{EMAIL}` can see an 'Admin Panel' link in the sidebar navigation.\n\n"
                        f"Clicking it redirects to `{url}` (employee dashboard or login), but the link should be "
                        f"hidden for employee role users to follow principle of least privilege.\n\n"
                        f"**Steps to reproduce:**\n"
                        f"1. Login as employee `{EMAIL}` to payroll module\n"
                        f"2. Observe sidebar -- 'Admin Panel' link visible at bottom\n\n"
                        f"**Expected:** Link hidden for employee role.\n"
                        f"**Actual:** Link visible."
                    )
                else:
                    print(f"  Admin Panel went to: {url}")
                    print(f"  Content: {body[:300]}")
        else:
            print("  PASS: No Admin Panel link visible to employee")

        # =====================================================
        # PART B: Direct admin URL access attempts
        # =====================================================
        print("\n" + "="*60)
        print("PART B: Direct Admin URL Access Attempts")
        print("="*60)

        sso_login(driver)
        admin_urls = [
            "/admin", "/admin/dashboard", "/admin/employees", "/admin/salary-structures",
            "/admin/run-payroll", "/admin/settings", "/admin/components",
            "/admin/payroll", "/admin/tax-settings"
        ]
        for path in admin_urls:
            url = f"{PAYROLL_URL}{path}"
            driver.get(url)
            time.sleep(3)
            current = driver.current_url
            body = get_body(driver).lower()
            redirected = current != url
            has_admin_content = any(k in body for k in ["run payroll", "manage employee", "salary component", "all employees", "process payroll"])
            safe_name = path.replace("/", "_")
            ss(driver, f"v2_04_direct{safe_name}")

            status = "BLOCKED" if (redirected or "access denied" in body or "unauthorized" in body or "login" in body[:200]) else "ACCESSIBLE"
            if has_admin_content:
                status = "SECURITY_ISSUE"

            print(f"  {path}: {status} (url={current[:60]})")
            if status == "SECURITY_ISSUE":
                file_bug(
                    f"[Payroll Employee] Employee can directly access admin URL: {path}",
                    f"Employee `{EMAIL}` can access `{url}` and see admin content.\n"
                    f"This is an authorization bypass vulnerability."
                )

        # =====================================================
        # PART C: Detailed screenshots of employee pages
        # =====================================================
        print("\n" + "="*60)
        print("PART C: Detailed Employee Page Screenshots")
        print("="*60)

        # Payslips detail view
        sso_login(driver)
        click_link(driver, "my payslips")
        ss(driver, "v2_05_payslips_list")
        body = get_body(driver)
        print(f"  Payslips page: {driver.current_url}")
        print(f"  Content: {body[:400]}")

        # Click Details on first payslip
        details_clicked = click_link(driver, "details")
        if details_clicked:
            ss(driver, "v2_05_payslip_detail")
            body = get_body(driver)
            print(f"  Payslip detail: {body[:500]}")
        else:
            # Try button
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if "detail" in btn.text.lower():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
                    ss(driver, "v2_05_payslip_detail")
                    print(f"  Payslip detail (btn): {get_body(driver)[:500]}")
                    break

        # Tax page - Form 16
        sso_login(driver)
        click_link(driver, "my tax")
        ss(driver, "v2_06_tax_page")
        body = get_body(driver)
        print(f"  Tax page: {body[:600]}")

        # Check if Form 16 download is available
        form16_found = False
        links = driver.find_elements(By.TAG_NAME, "a") + driver.find_elements(By.TAG_NAME, "button")
        for el in links:
            try:
                if "form 16" in el.text.lower() or "form16" in el.text.lower():
                    print(f"  Found Form 16 button: '{el.text.strip()}'")
                    form16_found = True
                    break
            except:
                continue
        if form16_found:
            print("  PASS: Form 16 download available")
        else:
            print("  INFO: Form 16 button/link not found (may not be generated yet)")

        # Declarations - try submitting
        sso_login(driver)
        click_link(driver, "declarations")
        ss(driver, "v2_07_declarations_page")
        body = get_body(driver)
        print(f"  Declarations: {body[:500]}")

        # Check for New Declaration button
        new_decl = False
        for el in driver.find_elements(By.TAG_NAME, "button") + driver.find_elements(By.TAG_NAME, "a"):
            try:
                if any(k in el.text.lower() for k in ["new declaration", "add declaration", "submit", "quick declare"]):
                    print(f"  Found declaration button: '{el.text.strip()}'")
                    new_decl = True
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(3)
                    ss(driver, "v2_07_new_declaration_form")
                    body = get_body(driver)
                    print(f"  Declaration form: {body[:500]}")
                    break
            except:
                continue
        if not new_decl:
            print("  INFO: No 'New Declaration' button found")

        # Reimbursements
        sso_login(driver)
        click_link(driver, "reimbursements")
        ss(driver, "v2_08_reimbursements_page")
        body = get_body(driver)
        print(f"  Reimbursements: {body[:400]}")

        # Check for New Claim button
        for el in driver.find_elements(By.TAG_NAME, "button") + driver.find_elements(By.TAG_NAME, "a"):
            try:
                if any(k in el.text.lower() for k in ["new claim", "submit claim", "add claim"]):
                    print(f"  Found claim button: '{el.text.strip()}'")
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(3)
                    ss(driver, "v2_08_new_claim_form")
                    body = get_body(driver)
                    print(f"  Claim form: {body[:500]}")
                    break
            except:
                continue

        # Leaves page
        sso_login(driver)
        click_link(driver, "my leaves")
        ss(driver, "v2_09_leaves_page")
        print(f"  Leaves: {get_body(driver)[:300]}")

        # Profile page
        sso_login(driver)
        click_link(driver, "profile")
        ss(driver, "v2_10_profile_page")
        body = get_body(driver)
        print(f"  Profile: {body[:400]}")

        # Check profile doesn't show other employees
        if any(name in body.lower() for name in ["ananya", "john@", "admin@"]):
            print("  WARNING: Other employee data visible on profile page")

        # =====================================================
        # PART D: API Security checks
        # =====================================================
        print("\n" + "="*60)
        print("PART D: API Security Checks")
        print("="*60)

        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Try payroll API endpoints that should be admin-only
        api_tests = [
            ("GET", "/api/v1/employees", "List all employees"),
            ("GET", "/api/v1/payroll/employees", "All employee payroll"),
            ("GET", "/api/v1/payroll/run", "Run payroll"),
            ("GET", "/api/v1/salary-structures", "Salary structures"),
            ("GET", "/api/v1/salary-components", "Salary components"),
            ("GET", "/api/v1/payroll/settings", "Payroll settings"),
            ("GET", "/api/v1/admin/dashboard", "Admin dashboard"),
            ("GET", "/api/v1/payslips", "All payslips"),
            ("GET", "/api/v1/my/payslips", "My payslips"),
            ("GET", "/api/v1/my/salary", "My salary"),
            ("GET", "/api/v1/my/tax", "My tax"),
            ("GET", "/api/v1/my/declarations", "My declarations"),
            ("GET", "/api/v1/my/reimbursements", "My reimbursements"),
        ]

        for method, path, desc in api_tests:
            try:
                url = f"{PAYROLL_API}{path}"
                if method == "GET":
                    r = requests.get(url, headers=headers, timeout=10)
                else:
                    r = requests.post(url, headers=headers, timeout=10)
                status = r.status_code
                body_preview = r.text[:200]
                print(f"  {method} {path}: {status} - {desc}")
                if status == 200:
                    print(f"    Response: {body_preview}")
                    # Check if admin endpoints return data
                    if "employees" in path and "my" not in path:
                        data = r.json()
                        items = data if isinstance(data, list) else data.get("data", [])
                        if isinstance(items, list) and len(items) > 1:
                            file_bug(
                                f"[Payroll Employee] Employee can access admin API: {path}",
                                f"GET {url} with employee token returns {len(items)} records.\n"
                                f"Expected: 401/403. Actual: 200 with data."
                            )
            except Exception as e:
                print(f"  {method} {path}: Error - {e}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        try:
            ss(driver, "v2_ERROR")
        except:
            pass
    finally:
        try:
            driver.quit()
        except:
            pass

    # Summary
    print("\n" + "="*60)
    print("TEST v2 SUMMARY")
    print("="*60)
    print(f"  Bugs filed: {len(bugs)}")
    for b in bugs:
        print(f"    - {b}")
    print(f"  Screenshots: {SCREENSHOT_DIR}")
    print("="*60)


if __name__ == "__main__":
    run()
