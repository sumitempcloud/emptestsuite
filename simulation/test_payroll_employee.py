"""
PAYROLL MODULE - EMPLOYEE ROLE TEST (priya@technova.in)
Tests: SSO login, My Payslips, My Salary, My Tax, Declarations, Reimbursements,
       Access control (no other employees' data, no admin pages)

Strategy: SSO login, then click sidebar links (not direct URL navigation which loses session).
Re-authenticate if session drops.
"""

import sys, os, time, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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
screenshots_taken = []

def ss(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    screenshots_taken.append(path)
    print(f"  [SCREENSHOT] {name}.png")
    return path

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
    return (data.get("data", {}).get("tokens", {}).get("access_token")
            or data.get("token") or data.get("access_token")
            or data.get("data", {}).get("token") or data.get("data", {}).get("access_token"))

def sso_navigate(driver, token=None):
    """Navigate to payroll with SSO. Returns new token if re-auth needed."""
    if not token:
        token = get_token()
    if not token:
        print("  FATAL: Cannot get auth token")
        return None
    driver.get(f"{PAYROLL_URL}?sso_token={token}")
    time.sleep(4)
    try:
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
    except:
        pass
    time.sleep(2)
    return token

def is_logged_in(driver):
    """Check if still on authenticated page (not login page)."""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        url = driver.current_url.lower()
        # Login page has "sign in" button text and "welcome back" heading
        if "sign in to manage your payroll" in body or (url.endswith("/login") or url == PAYROLL_URL + "/"):
            return False
        if "welcome, priya" in body or "/my" in url:
            return True
        return True  # assume logged in if not obviously on login page
    except:
        return False

def ensure_logged_in(driver):
    """Re-SSO if session dropped."""
    if not is_logged_in(driver):
        print("  Session lost, re-authenticating...")
        return sso_navigate(driver)
    return True

def click_sidebar_link(driver, link_text_contains):
    """Click a sidebar/nav link by partial text match. Returns True if found and clicked."""
    selectors = [
        "nav a", ".sidebar a", "[class*='sidebar'] a", "[class*='nav'] a",
        "[class*='menu'] a", "aside a", "[role='navigation'] a"
    ]
    for sel in selectors:
        try:
            links = driver.find_elements(By.CSS_SELECTOR, sel)
            for link in links:
                txt = link.text.strip().lower()
                if link_text_contains.lower() in txt:
                    print(f"  Clicking sidebar: '{link.text.strip()}'")
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(3)
                    try:
                        WebDriverWait(driver, 8).until(lambda d: d.execute_script("return document.readyState") == "complete")
                    except:
                        pass
                    time.sleep(2)
                    return True
        except:
            continue

    # Also try all <a> tags
    try:
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            txt = link.text.strip().lower()
            if link_text_contains.lower() in txt:
                print(f"  Clicking link: '{link.text.strip()}'")
                driver.execute_script("arguments[0].click();", link)
                time.sleep(3)
                try:
                    WebDriverWait(driver, 8).until(lambda d: d.execute_script("return document.readyState") == "complete")
                except:
                    pass
                time.sleep(2)
                return True
    except:
        pass
    return False

def get_body_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""

def test_payroll_employee():
    driver = get_driver()
    try:
        # =====================================================
        # TEST 1: SSO Login
        # =====================================================
        print("\n" + "="*60)
        print("[TEST 1] SSO Login as Employee (priya@technova.in)")
        print("="*60)
        token = get_token()
        if not token:
            print("  FATAL: Login API failed")
            file_bug("[Payroll Employee] SSO login API fails", "Cannot get token for priya@technova.in")
            return
        print(f"  Token obtained: {token[:30]}...")

        sso_navigate(driver, token)
        ss(driver, "01_sso_landing")

        url = driver.current_url
        body = get_body_text(driver)
        print(f"  URL after SSO: {url}")

        if "welcome, priya" in body.lower() or "/my" in url:
            print("  PASS: SSO login successful - Employee dashboard visible")
        else:
            print(f"  UNCERTAIN: Page content: {body[:300]}")
            file_bug("[Payroll Employee] SSO login may not work for employee",
                     f"URL: {url}\nBody: {body[:500]}")

        # Get sidebar navigation items
        all_nav = []
        for link in driver.find_elements(By.TAG_NAME, "a"):
            try:
                t = link.text.strip()
                h = link.get_attribute("href") or ""
                if t:
                    all_nav.append(f"{t} -> {h}")
            except:
                pass
        print(f"  Nav items found: {all_nav}")

        # =====================================================
        # TEST 2: My Payslips
        # =====================================================
        print("\n" + "="*60)
        print("[TEST 2] My Payslips - Can Priya see her payslips?")
        print("="*60)
        ensure_logged_in(driver)

        found = click_sidebar_link(driver, "payslip")
        if not found:
            found = click_sidebar_link(driver, "pay slip")

        ss(driver, "02_my_payslips")
        body = get_body_text(driver)
        url = driver.current_url
        print(f"  URL: {url}")
        print(f"  Body (first 500): {body[:500]}")

        if any(k in body.lower() for k in ["payslip", "pay slip", "net pay", "gross", "earning", "february", "march", "january"]):
            print("  PASS: Payslip content visible")
        elif found:
            print("  WARN: Clicked payslip link but no payslip data found")
        else:
            print("  FAIL: Could not find payslip page")
            file_bug("[Payroll Employee] Cannot find or access My Payslips page",
                     f"Employee {EMAIL} cannot access payslip page. Sidebar link not found or no payslip data displayed.\nURL: {url}")

        # =====================================================
        # TEST 3: My Salary
        # =====================================================
        print("\n" + "="*60)
        print("[TEST 3] My Salary - Salary breakdown visible?")
        print("="*60)
        # Re-SSO to ensure fresh session
        sso_navigate(driver)
        time.sleep(2)

        found = click_sidebar_link(driver, "my salary")
        if not found:
            found = click_sidebar_link(driver, "salary")

        ss(driver, "03_my_salary")
        body = get_body_text(driver)
        url = driver.current_url
        print(f"  URL: {url}")
        print(f"  Body (first 500): {body[:500]}")

        if any(k in body.lower() for k in ["basic", "hra", "ctc", "gross", "deduction", "allowance", "salary structure", "net salary", "component"]):
            print("  PASS: Salary breakdown visible")
        elif found:
            print("  WARN: Clicked salary link but no salary breakdown data found")
        else:
            print("  FAIL: Could not find salary page")

        # =====================================================
        # TEST 4: My Tax
        # =====================================================
        print("\n" + "="*60)
        print("[TEST 4] My Tax - TDS details and tax regime")
        print("="*60)
        sso_navigate(driver)
        time.sleep(2)

        found = click_sidebar_link(driver, "my tax")
        if not found:
            found = click_sidebar_link(driver, "tax")

        ss(driver, "04_my_tax")
        body = get_body_text(driver)
        url = driver.current_url
        print(f"  URL: {url}")
        print(f"  Body (first 500): {body[:500]}")

        if any(k in body.lower() for k in ["tds", "regime", "old regime", "new regime", "income tax", "taxable"]):
            print("  PASS: Tax details visible")
        elif found:
            print("  WARN: Clicked tax link but no TDS/regime data found")
        else:
            print("  FAIL: Could not find tax page")

        # =====================================================
        # TEST 5: Declarations
        # =====================================================
        print("\n" + "="*60)
        print("[TEST 5] Declarations - Can she submit 80C, HRA?")
        print("="*60)
        sso_navigate(driver)
        time.sleep(2)

        found = click_sidebar_link(driver, "declaration")

        ss(driver, "05_declarations")
        body = get_body_text(driver)
        url = driver.current_url
        print(f"  URL: {url}")
        print(f"  Body (first 500): {body[:500]}")

        if any(k in body.lower() for k in ["80c", "hra", "declaration", "investment", "80d", "section 80", "proof", "submit declaration"]):
            print("  PASS: Declarations page accessible")
        elif found:
            print("  WARN: Clicked declaration link but no declaration content found")
        else:
            print("  FAIL: Could not find declarations page")

        # =====================================================
        # TEST 6: Reimbursements
        # =====================================================
        print("\n" + "="*60)
        print("[TEST 6] Reimbursements - Can she submit a claim?")
        print("="*60)
        sso_navigate(driver)
        time.sleep(2)

        found = click_sidebar_link(driver, "reimbursement")
        if not found:
            found = click_sidebar_link(driver, "claim")
        if not found:
            found = click_sidebar_link(driver, "expense")

        ss(driver, "06_reimbursements")
        body = get_body_text(driver)
        url = driver.current_url
        print(f"  URL: {url}")
        print(f"  Body (first 500): {body[:500]}")

        if any(k in body.lower() for k in ["reimbursement", "claim", "expense", "submit claim", "new claim", "amount"]):
            print("  PASS: Reimbursements page accessible")
        elif found:
            print("  WARN: Clicked reimbursement link but no content found")
        else:
            print("  FAIL: Could not find reimbursements page")

        # =====================================================
        # TEST 7: Cannot see other employees' salary
        # =====================================================
        print("\n" + "="*60)
        print("[TEST 7] Access Control - Cannot see other employees' salary")
        print("="*60)
        sso_navigate(driver)
        time.sleep(2)

        # Check if "Admin Panel" link is visible and accessible
        admin_link_found = click_sidebar_link(driver, "admin")
        ss(driver, "07_admin_panel_click")
        body = get_body_text(driver)
        url = driver.current_url
        print(f"  URL after admin click: {url}")
        print(f"  Body (first 500): {body[:500]}")

        if admin_link_found:
            # Check what's visible
            if any(k in body.lower() for k in ["all employees", "employee list", "manage employee", "salary list"]):
                # Check if other names are visible
                other_names = ["ananya", "john", "rahul"]
                visible_others = [n for n in other_names if n in body.lower()]
                if visible_others:
                    print(f"  FAIL: Employee can see other employees: {visible_others}")
                    ss(driver, "07_SECURITY_other_employees_visible")
                    file_bug(
                        "[Payroll Employee] Employee can see other employees' data via admin panel",
                        f"Employee {EMAIL} can access admin panel and see other employees: {visible_others}\nURL: {url}\nThis is a security/authorization issue."
                    )
                else:
                    print("  WARN: Admin panel accessible but no other employee data visible")
            else:
                print("  Admin link exists but content may be restricted")
        else:
            print("  PASS: No admin link visible for employee role")

        # Also check API endpoints
        headers = {"Authorization": f"Bearer {get_token()}"}
        api_checks = [
            "/api/v1/salaries", "/api/v1/employees", "/api/v1/admin/salaries",
            "/api/v1/payroll/employees", "/api/v1/all-employees"
        ]
        for api_path in api_checks:
            try:
                r = requests.get(f"{PAYROLL_API}{api_path}", headers=headers, timeout=10)
                print(f"  API {api_path}: {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    items = data if isinstance(data, list) else data.get("data", data.get("employees", data.get("results", [])))
                    if isinstance(items, list) and len(items) > 1:
                        print(f"  SECURITY: API returned {len(items)} records")
                        file_bug(
                            f"[Payroll Employee] Employee API {api_path} returns multiple employees' data",
                            f"GET {PAYROLL_API}{api_path} with employee token returns {len(items)} records."
                        )
            except Exception as e:
                print(f"  API {api_path}: error - {e}")

        # =====================================================
        # TEST 8: Cannot access admin pages
        # =====================================================
        print("\n" + "="*60)
        print("[TEST 8] Access Control - Admin page restrictions")
        print("="*60)
        # From the dashboard screenshot, there IS an "Admin Panel" link in the sidebar
        # Let's check what happens when employee accesses it
        sso_navigate(driver)
        time.sleep(2)

        # Click Admin Panel
        admin_clicked = click_sidebar_link(driver, "admin panel")
        if not admin_clicked:
            admin_clicked = click_sidebar_link(driver, "admin")

        ss(driver, "08_admin_panel")
        body = get_body_text(driver)
        url = driver.current_url
        print(f"  URL: {url}")
        print(f"  Body (first 800): {body[:800]}")

        # Check if employee can see admin features
        admin_features = ["run payroll", "salary structure", "manage components", "payroll settings",
                          "employee salaries", "process payroll", "manage salary", "tax settings"]
        found_admin = [f for f in admin_features if f in body.lower()]
        if found_admin:
            print(f"  FAIL: Employee can see admin features: {found_admin}")
            ss(driver, "08_SECURITY_admin_features_visible")
            file_bug(
                "[Payroll Employee] Employee can access admin payroll features",
                f"Employee {EMAIL} can see admin features after clicking Admin Panel:\n"
                f"Features visible: {found_admin}\nURL: {url}\n"
                f"Expected: Access denied or redirect to employee dashboard."
            )
        elif admin_clicked:
            print(f"  Admin Panel clicked - checking content...")
            if "access denied" in body.lower() or "unauthorized" in body.lower() or "403" in body.lower():
                print("  PASS: Admin panel properly blocked")
            else:
                print(f"  UNCERTAIN: Admin panel accessible but no obvious admin features visible")
        else:
            print("  Note: No Admin Panel link found in sidebar")

        # =====================================================
        # TEST 9: Deep-dive screenshots of each section
        # =====================================================
        print("\n" + "="*60)
        print("[TEST 9] Comprehensive screenshots of all accessible pages")
        print("="*60)

        sections = [
            ("my payslip", "09a_payslips_detail"),
            ("my salary", "09b_salary_detail"),
            ("my tax", "09c_tax_detail"),
            ("declaration", "09d_declarations_detail"),
            ("reimbursement", "09e_reimbursements_detail"),
            ("my leaves", "09f_leaves"),
            ("profile", "09g_profile"),
        ]

        for link_text, screenshot_name in sections:
            sso_navigate(driver)
            time.sleep(1)
            clicked = click_sidebar_link(driver, link_text)
            if clicked:
                ss(driver, screenshot_name)
                body = get_body_text(driver)
                print(f"  {link_text}: URL={driver.current_url}")
                print(f"    Content preview: {body[:300]}")
            else:
                print(f"  {link_text}: Sidebar link not found")

        # Final dashboard
        sso_navigate(driver)
        time.sleep(2)
        ss(driver, "10_final_dashboard")

        # Also capture the quick-action cards
        body = get_body_text(driver)
        print(f"\n  Final dashboard content:\n{body[:1500]}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        try:
            ss(driver, "ERROR_screenshot")
        except:
            pass
    finally:
        driver.quit()

    # =====================================================
    # SUMMARY
    # =====================================================
    print("\n" + "="*60)
    print("PAYROLL EMPLOYEE TEST SUMMARY")
    print("="*60)
    print(f"  Total bugs filed: {len(bugs)}")
    for b in bugs:
        print(f"    - {b}")
    print(f"  Total screenshots: {len(screenshots_taken)}")
    print(f"  Screenshot dir: {SCREENSHOT_DIR}")
    print("="*60)


if __name__ == "__main__":
    test_payroll_employee()
