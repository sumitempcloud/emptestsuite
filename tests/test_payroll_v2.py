#!/usr/bin/env python3
"""
EMP Cloud HRMS - Payroll Module E2E Test Suite v2
Thorough testing of payroll subdomain, SSO, sidebar pages, RBAC, API.
"""

import sys
import os
import time
import json
import traceback
import ssl
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# -- Config -------------------------------------------------------------------
MAIN_URL = "https://test-empcloud.empcloud.com"
PAYROLL_URL = "https://testpayroll.empcloud.com"
API_BASE = "https://test-empcloud.empcloud.com/api/v1"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\payroll"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

CREDS = {
    "org_admin": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"},
    "employee": {"email": "priya@technova.in", "password": "Welcome@123"},
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_found = []
test_results = []
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def shot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{ts()}.png")
    driver.save_screenshot(path)
    print(f"    [SCREENSHOT] {path}")
    return path


def log_result(name, status, details=""):
    test_results.append({"test": name, "status": status, "details": details})
    icon = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN"}[status]
    print(f"  [{icon}] {name}: {details}")


def record_bug(title, description, severity, screenshot_path=None):
    bugs_found.append({
        "title": title, "description": description,
        "severity": severity, "screenshot": screenshot_path,
    })
    print(f"  [BUG-{severity.upper()}] {title}")


def file_github_issue(title, body, labels=None):
    if labels is None:
        labels = ["bug"]
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    payload = json.dumps({"title": title, "body": body, "labels": labels}).encode()
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-E2E-Tester",
        "Content-Type": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        result = json.loads(resp.read().decode())
        print(f"    [GITHUB] Issue #{result.get('number')} -> {result.get('html_url')}")
        return result
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else ""
        print(f"    [GITHUB-ERR] {e.code}: {err[:300]}")
    except Exception as e:
        print(f"    [GITHUB-ERR] {e}")
    return None


def api_request(url, token=None, method="GET"):
    headers = {
        "User-Agent": "EmpCloud-E2E-Tester",
        "Origin": MAIN_URL,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body
    except Exception as e:
        return 0, str(e)


def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                 "--disable-gpu", "--window-size=1920,1080",
                 "--ignore-certificate-errors", "--disable-web-security"]:
        opts.add_argument(arg)
    svc = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(45)
    d.implicitly_wait(3)
    return d


def do_login(driver, base_url, email, password, label=""):
    """Login on the main app. Returns True on success."""
    print(f"    Logging in as {email} on {base_url} ...")
    driver.get(base_url + "/login")
    time.sleep(3)

    # Find fields
    email_el = None
    for sel in [(By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='company']"),
                (By.CSS_SELECTOR, "input[placeholder*='mail']"),
                (By.NAME, "email"), (By.ID, "email")]:
        try:
            el = driver.find_element(*sel)
            if el.is_displayed():
                email_el = el
                break
        except NoSuchElementException:
            continue

    pass_el = None
    for sel in [(By.CSS_SELECTOR, "input[type='password']"),
                (By.NAME, "password"), (By.ID, "password")]:
        try:
            el = driver.find_element(*sel)
            if el.is_displayed():
                pass_el = el
                break
        except NoSuchElementException:
            continue

    if not email_el or not pass_el:
        print(f"    No login fields found at {driver.current_url}")
        shot(driver, f"no_login_fields_{label}")
        return False

    email_el.clear(); email_el.send_keys(email)
    pass_el.clear(); pass_el.send_keys(password)
    shot(driver, f"pre_submit_{label}")

    # Submit
    for sel in [(By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(),'Sign')]"),
                (By.XPATH, "//button[contains(text(),'Log')]")]:
        try:
            btn = driver.find_element(*sel)
            if btn.is_displayed():
                btn.click()
                break
        except NoSuchElementException:
            continue

    time.sleep(6)
    shot(driver, f"post_login_{label}")
    url_after = driver.current_url
    print(f"    Post-login URL: {url_after}")
    return "/login" not in url_after.lower()


def extract_token(driver):
    """Extract JWT from localStorage."""
    try:
        keys = driver.execute_script("return Object.keys(localStorage);")
        for k in (keys or []):
            val = driver.execute_script(f"return localStorage.getItem('{k}');")
            if val and any(t in k.lower() for t in ["auth", "token"]):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        state = parsed.get("state", parsed)
                        tok = state.get("accessToken") or state.get("token") or state.get("access_token")
                        if tok:
                            print(f"    Token from localStorage['{k}']: {str(tok)[:50]}...")
                            return tok
                except (json.JSONDecodeError, TypeError):
                    if val.startswith("ey"):
                        return val
    except Exception as e:
        print(f"    Token extraction error: {e}")
    return None


def get_sso_payroll_link(driver):
    """Find the SSO link to payroll subdomain from the main app sidebar."""
    try:
        links = driver.find_elements(By.TAG_NAME, "a")
        for a in links:
            href = a.get_attribute("href") or ""
            if "testpayroll.empcloud.com" in href and "sso_token" in href:
                return href
    except Exception:
        pass
    return None


# -- Tests --------------------------------------------------------------------

def test_orgadmin_payroll_subdomain():
    """T1: Org Admin -> main app -> SSO into payroll subdomain -> explore all pages."""
    print("\n" + "=" * 70)
    print("  T1: Org Admin - Payroll Subdomain via SSO")
    print("=" * 70)

    driver = create_driver()
    try:
        creds = CREDS["org_admin"]
        ok = do_login(driver, MAIN_URL, creds["email"], creds["password"], "oa")
        if not ok:
            log_result("T1-OA-Login", "FAIL", "Org Admin cannot log in")
            sp = shot(driver, "T1_oa_login_fail")
            record_bug("[Payroll] Org Admin cannot log in to main app",
                       f"Login failed for {creds['email']} at {MAIN_URL}", "critical", sp)
            return

        log_result("T1-OA-Login", "PASS", f"URL: {driver.current_url}")
        token = extract_token(driver)

        # Get SSO link to payroll
        sso_link = get_sso_payroll_link(driver)
        if sso_link:
            print(f"    Found SSO payroll link: {sso_link[:100]}...")
            log_result("T1-SSOLink", "PASS", "SSO payroll link found in sidebar")
        else:
            log_result("T1-SSOLink", "WARN", "No SSO payroll link found")
            # Fallback: go directly
            sso_link = PAYROLL_URL

        # Navigate to payroll subdomain
        driver.get(sso_link)
        time.sleep(5)
        shot(driver, "T1_payroll_home")
        payroll_url = driver.current_url
        print(f"    Payroll subdomain URL: {payroll_url}")
        page_src = driver.page_source

        if "welcome" in page_src.lower() or "payroll" in driver.title.lower():
            log_result("T1-PayrollHome", "PASS", f"Payroll dashboard loaded. Title: {driver.title}")
        else:
            log_result("T1-PayrollHome", "FAIL", "Payroll dashboard did not load")
            sp = shot(driver, "T1_payroll_home_fail")
            record_bug("[Payroll] Payroll dashboard does not load via SSO",
                       f"After SSO, payroll page shows: {driver.title}", "high", sp)

        # -- Explore sidebar pages on payroll subdomain --
        # From the screenshot we saw: My Payslips, My Salary, My Tax, Declarations, My Leaves, Profile, Admin Panel
        payroll_sidebar_pages = {
            "Dashboard": ["/my", "/dashboard", "/"],
            "My Payslips": ["/my-payslips", "/my/payslips", "/payslips", "/my-payslip"],
            "My Salary": ["/my-salary", "/my/salary", "/salary"],
            "My Tax": ["/my-tax", "/my/tax", "/tax"],
            "Declarations": ["/declarations", "/my/declarations", "/my-declarations"],
            "My Leaves": ["/my-leaves", "/my/leaves", "/leaves"],
            "Profile": ["/profile", "/my/profile", "/my-profile"],
            "Admin Panel": ["/admin", "/admin-panel", "/admin/dashboard"],
        }

        # First try clicking sidebar links directly
        print("\n    -- Exploring payroll sidebar links --")
        sidebar_links_found = {}
        try:
            all_links = driver.find_elements(By.CSS_SELECTOR, "a, button, [role='menuitem'], nav a")
            for el in all_links:
                text = (el.text or "").strip()
                href = el.get_attribute("href") or ""
                if text and len(text) < 50:
                    for page_name in payroll_sidebar_pages:
                        if page_name.lower() in text.lower():
                            sidebar_links_found[page_name] = href
        except Exception as e:
            print(f"    Error scanning sidebar: {e}")

        print(f"    Sidebar links found: {list(sidebar_links_found.keys())}")

        pages_visited = {}
        # Click each sidebar link
        for page_name, href in sidebar_links_found.items():
            if href and href.startswith("http"):
                try:
                    driver.get(href)
                    time.sleep(3)
                    sp = shot(driver, f"T1_payroll_{page_name.replace(' ','_')}")
                    pages_visited[page_name] = {
                        "url": driver.current_url,
                        "title": driver.title,
                        "content_len": len(driver.page_source),
                        "screenshot": sp,
                    }
                    print(f"      [OK] {page_name}: {driver.current_url}")
                except Exception as e:
                    print(f"      [ERR] {page_name}: {e}")

        # Also try URL paths for pages not yet visited
        for page_name, paths in payroll_sidebar_pages.items():
            if page_name in pages_visited:
                continue
            for path in paths:
                url = PAYROLL_URL + path
                try:
                    driver.get(url)
                    time.sleep(2)
                    final = driver.current_url
                    src_lower = driver.page_source.lower()
                    if (len(driver.page_source) > 2000
                            and "404" not in src_lower
                            and "not found" not in src_lower):
                        sp = shot(driver, f"T1_payroll_{page_name.replace(' ','_')}")
                        pages_visited[page_name] = {
                            "url": final, "title": driver.title,
                            "content_len": len(driver.page_source), "screenshot": sp,
                        }
                        print(f"      [OK] {page_name} via {path}: {final}")
                        break
                except Exception:
                    continue

        log_result("T1-PayrollPages", "PASS" if len(pages_visited) >= 3 else "WARN",
                   f"Visited {len(pages_visited)} payroll pages: {list(pages_visited.keys())}")

        # Check salary data visibility on dashboard
        print("\n    -- Checking salary data on dashboard --")
        driver.get(sso_link)
        time.sleep(4)
        src = driver.page_source
        # Look for salary figures
        salary_indicators = ["monthly ctc", "net pay", "gross", "basic", "deduction",
                             "payslip", "salary breakdown", "tax computation"]
        found_salary_data = [ind for ind in salary_indicators if ind in src.lower()]
        if found_salary_data:
            print(f"      Salary data found on dashboard: {found_salary_data}")
            log_result("T1-SalaryDataVisible", "PASS", f"Dashboard shows: {found_salary_data}")
        else:
            log_result("T1-SalaryDataVisible", "WARN", "No salary data found on payroll dashboard")

        # -- Check Admin Panel access --
        print("\n    -- Testing Admin Panel --")
        admin_paths = ["/admin", "/admin-panel", "/admin/dashboard",
                       "/admin/employees", "/admin/payroll", "/admin/settings",
                       "/admin/pay-runs", "/admin/salary-structure"]
        admin_pages_ok = []
        for path in admin_paths:
            url = PAYROLL_URL + path
            try:
                driver.get(url)
                time.sleep(2)
                src_lower = driver.page_source.lower()
                if (len(driver.page_source) > 2000
                        and "404" not in src_lower
                        and "not found" not in src_lower
                        and "unauthorized" not in src_lower):
                    admin_pages_ok.append(path)
                    sp = shot(driver, f"T1_admin_{path.replace('/','_')}")
                    print(f"      [OK] Admin: {path} -> {driver.current_url}")
            except Exception:
                pass

        if admin_pages_ok:
            log_result("T1-AdminPanel", "PASS", f"Admin pages accessible: {admin_pages_ok}")
        else:
            log_result("T1-AdminPanel", "WARN", "No admin pages found on payroll subdomain")

        return token, sso_link

    except Exception as e:
        print(f"  [ERROR] {e}")
        traceback.print_exc()
        return None, None
    finally:
        driver.quit()


def test_employee_payroll():
    """T2: Employee login -> payroll access -> RBAC check."""
    print("\n" + "=" * 70)
    print("  T2: Employee - Payroll Access & RBAC")
    print("=" * 70)

    driver = create_driver()
    try:
        creds = CREDS["employee"]
        ok = do_login(driver, MAIN_URL, creds["email"], creds["password"], "emp")
        if not ok:
            log_result("T2-EmpLogin", "FAIL", "Employee cannot log in")
            sp = shot(driver, "T2_emp_login_fail")
            record_bug("[Payroll] Employee (priya@technova.in) cannot log in",
                       f"Employee login failed at {MAIN_URL}/login. URL after: {driver.current_url}",
                       "high", sp)
            return

        log_result("T2-EmpLogin", "PASS", f"Employee logged in: {driver.current_url}")
        emp_token = extract_token(driver)

        # Get SSO link to payroll for employee
        sso_link = get_sso_payroll_link(driver)
        if sso_link:
            print(f"    Employee SSO payroll link found")
            log_result("T2-EmpSSOLink", "PASS", "Employee has payroll SSO link")
        else:
            # Try direct URL
            sso_link = PAYROLL_URL
            log_result("T2-EmpSSOLink", "WARN", "No SSO link; trying direct URL")

        driver.get(sso_link)
        time.sleep(5)
        sp = shot(driver, "T2_emp_payroll_home")
        src = driver.page_source
        print(f"    Employee payroll URL: {driver.current_url}")
        print(f"    Page title: {driver.title}")

        # Can employee view their own payslip?
        payslip_keywords = ["payslip", "net pay", "gross", "salary", "ctc", "deduction"]
        found = [kw for kw in payslip_keywords if kw in src.lower()]
        if found:
            log_result("T2-EmpOwnPayslip", "PASS", f"Employee sees own payroll data: {found}")
        else:
            log_result("T2-EmpOwnPayslip", "WARN", "Employee payroll page has no salary keywords")
            sp = shot(driver, "T2_emp_no_payslip")
            record_bug("[Payroll] Employee cannot view own payslip data",
                       "After logging in and accessing payroll, employee sees no salary/payslip information.",
                       "high", sp)

        # Try accessing My Payslips, My Salary pages
        emp_pages = ["/my-payslips", "/my/payslips", "/payslips",
                     "/my-salary", "/my/salary", "/salary", "/my", "/my-tax"]
        for path in emp_pages:
            url = PAYROLL_URL + path
            try:
                driver.get(url)
                time.sleep(2)
                if len(driver.page_source) > 2000 and "404" not in driver.page_source.lower():
                    sp = shot(driver, f"T2_emp_{path.replace('/','_')}")
                    print(f"      [OK] Employee -> {path}: {driver.current_url}")
            except Exception:
                pass

        # -- RBAC: Employee should NOT access Admin Panel --
        print("\n    -- RBAC: Employee trying admin pages --")
        admin_paths = ["/admin", "/admin/employees", "/admin/payroll",
                       "/admin/pay-runs", "/admin/settings", "/admin/salary-structure",
                       "/admin/dashboard"]
        rbac_violations = []
        for path in admin_paths:
            url = PAYROLL_URL + path
            try:
                driver.get(url)
                time.sleep(2)
                src_lower = driver.page_source.lower()
                final = driver.current_url
                # Check if admin content is shown (employee, salary list, etc.)
                admin_indicators = ["employee list", "all employees", "pay run", "salary structure",
                                    "admin panel", "admin dashboard", "manage"]
                has_admin = any(ind in src_lower for ind in admin_indicators)
                not_blocked = ("403" not in src_lower
                              and "unauthorized" not in src_lower
                              and "access denied" not in src_lower
                              and "login" not in final.lower()
                              and "404" not in src_lower)
                if not_blocked and len(driver.page_source) > 3000:
                    sp = shot(driver, f"T2_rbac_{path.replace('/','_')}")
                    rbac_violations.append({
                        "path": path, "url": final,
                        "has_admin_content": has_admin, "screenshot": sp
                    })
                    print(f"      [VIOLATION] Employee can access {path} -> {final} (admin_content={has_admin})")
                else:
                    print(f"      [OK-BLOCKED] {path} properly restricted")
            except Exception as e:
                print(f"      [ERR] {path}: {e}")

        if rbac_violations:
            log_result("T2-RBAC-Admin", "FAIL", f"{len(rbac_violations)} admin pages accessible to employee")
            desc = "Employee role can access admin-only payroll pages:\n\n"
            for v in rbac_violations:
                desc += f"- `{v['path']}` -> `{v['url']}` (admin_content: {v['has_admin_content']})\n"
            record_bug(
                "[Payroll][Security] Employee can access admin payroll pages (RBAC violation)",
                desc + "\nEmployee should only see their own payslip/salary, not admin panels.",
                "critical", rbac_violations[0].get("screenshot"),
            )
        else:
            log_result("T2-RBAC-Admin", "PASS", "Employee properly blocked from admin pages")

        # -- RBAC: Check if employee can see OTHER employees' data --
        print("\n    -- RBAC: Checking if employee can see others' salary --")
        # Try API if we have a token
        if emp_token:
            sensitive_endpoints = [
                f"{API_BASE}/payroll/employees",
                f"{API_BASE}/employees",
                f"{API_BASE}/payroll",
                f"{API_BASE}/salaries",
                f"{API_BASE}/payslips",
            ]
            api_violations = []
            for ep_url in sensitive_endpoints:
                status, body = api_request(ep_url, emp_token)
                if status == 200:
                    # Check if it returns multiple employees' data
                    try:
                        data = json.loads(body)
                        if isinstance(data, list) and len(data) > 1:
                            api_violations.append({"url": ep_url, "count": len(data)})
                            print(f"      [API-VIOLATION] {ep_url}: returns {len(data)} records")
                        elif isinstance(data, dict) and "data" in data:
                            inner = data["data"]
                            if isinstance(inner, list) and len(inner) > 1:
                                api_violations.append({"url": ep_url, "count": len(inner)})
                                print(f"      [API-VIOLATION] {ep_url}: returns {len(inner)} records")
                    except json.JSONDecodeError:
                        pass
                else:
                    print(f"      [{status}] {ep_url}")

            if api_violations:
                log_result("T2-API-RBAC", "FAIL", f"Employee can see {len(api_violations)} multi-record endpoints")
                record_bug(
                    "[Payroll][Security] Employee API token returns other employees' salary data",
                    "Employee token returns multiple employees' data:\n" +
                    "\n".join(f"- {v['url']}: {v['count']} records" for v in api_violations),
                    "critical",
                )
            else:
                log_result("T2-API-RBAC", "PASS", "Employee API access properly scoped")

    except Exception as e:
        print(f"  [ERROR] {e}")
        traceback.print_exc()
    finally:
        driver.quit()


def test_superadmin_payroll():
    """T3: Super Admin login and payroll access."""
    print("\n" + "=" * 70)
    print("  T3: Super Admin - Payroll Access")
    print("=" * 70)

    driver = create_driver()
    try:
        creds = CREDS["super_admin"]
        ok = do_login(driver, MAIN_URL, creds["email"], creds["password"], "sa")
        if not ok:
            log_result("T3-SA-Login", "FAIL", "Super Admin cannot log in")
            sp = shot(driver, "T3_sa_login_fail")
            record_bug("[Payroll] Super Admin cannot log in",
                       f"Super Admin ({creds['email']}) login failed at {MAIN_URL}. "
                       f"URL after attempt: {driver.current_url}",
                       "critical", sp)
            return

        log_result("T3-SA-Login", "PASS", f"URL: {driver.current_url}")
        sa_token = extract_token(driver)

        # Check for payroll nav
        sso_link = get_sso_payroll_link(driver)
        if sso_link:
            log_result("T3-SA-PayrollLink", "PASS", "Super Admin has payroll SSO link")
            driver.get(sso_link)
            time.sleep(5)
            shot(driver, "T3_sa_payroll")
            print(f"    SA Payroll URL: {driver.current_url}, Title: {driver.title}")
        else:
            log_result("T3-SA-PayrollLink", "WARN", "No SSO payroll link for Super Admin")
            shot(driver, "T3_sa_no_payroll")

    except Exception as e:
        print(f"  [ERROR] {e}")
        traceback.print_exc()
    finally:
        driver.quit()


def test_payroll_api_auth():
    """T4: API auth tests - unauthenticated access, token validity."""
    print("\n" + "=" * 70)
    print("  T4: Payroll API Authentication Tests")
    print("=" * 70)

    # Try getting a token via API login
    print("    Attempting API login for org admin...")
    login_endpoints = [
        f"{MAIN_URL}/api/v1/auth/login",
        f"{MAIN_URL}/api/auth/login",
        f"{API_BASE}/auth/login",
        f"{API_BASE}/login",
    ]
    oa_token = None
    creds = CREDS["org_admin"]
    payload = json.dumps({"email": creds["email"], "password": creds["password"]}).encode()

    for ep in login_endpoints:
        try:
            req = urllib.request.Request(ep, data=payload, method="POST", headers={
                "User-Agent": "EmpCloud-E2E-Tester", "Origin": MAIN_URL,
                "Content-Type": "application/json", "Accept": "application/json",
            })
            resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
            body = json.loads(resp.read().decode())
            # Dig for token
            for key_path in [["token"], ["access_token"], ["accessToken"],
                             ["data", "token"], ["data", "access_token"],
                             ["data", "accessToken"]]:
                obj = body
                for k in key_path:
                    if isinstance(obj, dict):
                        obj = obj.get(k)
                    else:
                        obj = None
                        break
                if obj and isinstance(obj, str):
                    oa_token = obj
                    break
            if oa_token:
                print(f"    Got OA token via {ep}: {oa_token[:50]}...")
                break
            else:
                print(f"    {ep} responded but no token. Keys: {list(body.keys()) if isinstance(body, dict) else 'N/A'}")
        except urllib.error.HTTPError as e:
            print(f"    {ep} -> HTTP {e.code}")
        except Exception as e:
            print(f"    {ep} -> {e}")

    if not oa_token:
        log_result("T4-APILogin", "WARN", "Could not get API token via login endpoints")
    else:
        log_result("T4-APILogin", "PASS", "Got API token")

    # Test payroll API on the payroll subdomain too
    payroll_api_bases = [
        API_BASE,
        f"{PAYROLL_URL}/api",
        f"{PAYROLL_URL}/api/v1",
        PAYROLL_URL,
    ]
    api_paths = [
        "/payroll", "/payroll/employees", "/payroll/payslips",
        "/payroll/salary", "/payroll/settings", "/payroll/pay-runs",
        "/employees", "/salary", "/payslips",
    ]

    print("\n    -- Unauthenticated API access test --")
    unauth_exposed = []
    for base in payroll_api_bases:
        for path in api_paths:
            url = base + path
            status, body = api_request(url, token=None)
            if status == 200 and len(body) > 50:
                unauth_exposed.append({"url": url, "preview": body[:200]})
                print(f"      [EXPOSED] {url} -> 200 ({len(body)} bytes)")
            elif status not in (0, 404, 405):
                pass  # silently skip

    if unauth_exposed:
        log_result("T4-UnauthExposure", "FAIL", f"{len(unauth_exposed)} endpoints exposed without auth")
        desc = "Payroll API endpoints accessible without authentication:\n\n"
        for ep in unauth_exposed:
            desc += f"- `{ep['url']}`\n  Preview: `{ep['preview'][:100]}`\n"
        record_bug(
            "[Payroll][Security] Payroll API endpoints exposed without authentication",
            desc, "critical",
        )
    else:
        log_result("T4-UnauthExposure", "PASS", "No payroll endpoints exposed without auth")

    # Test with token if we have one
    if oa_token:
        print("\n    -- Authenticated API test --")
        for base in payroll_api_bases:
            for path in api_paths:
                url = base + path
                status, body = api_request(url, oa_token)
                if status == 200:
                    print(f"      [200] {url}: {body[:120]}")


def test_payroll_direct_no_sso():
    """T5: Try accessing payroll subdomain directly without SSO - should require auth."""
    print("\n" + "=" * 70)
    print("  T5: Payroll Subdomain - Direct Access Without SSO")
    print("=" * 70)

    driver = create_driver()
    try:
        # Go directly to payroll subdomain without logging in
        driver.get(PAYROLL_URL)
        time.sleep(4)
        sp = shot(driver, "T5_payroll_no_auth")
        url_after = driver.current_url
        src = driver.page_source.lower()
        print(f"    Direct access URL: {url_after}")
        print(f"    Title: {driver.title}")

        # Check if it shows salary data without auth
        salary_kw = ["monthly ctc", "net pay", "gross pay", "salary breakdown",
                     "payslip", "deduction", "basic pay"]
        exposed = [kw for kw in salary_kw if kw in src]

        if exposed and "login" not in url_after.lower():
            log_result("T5-DirectAccess", "FAIL", f"Salary data visible without auth: {exposed}")
            record_bug(
                "[Payroll][Security] Payroll subdomain shows salary data without authentication",
                f"Accessing {PAYROLL_URL} directly without login shows salary data: {exposed}",
                "critical", sp,
            )
        elif "login" in url_after.lower() or "sign in" in src or len(driver.page_source) < 2000:
            log_result("T5-DirectAccess", "PASS", "Payroll subdomain redirects to login without auth")
        else:
            log_result("T5-DirectAccess", "PASS", "Payroll subdomain does not expose data without auth")

        # Try sensitive paths directly
        sensitive_paths = ["/admin", "/admin/employees", "/admin/payroll",
                          "/my-payslips", "/my-salary", "/my"]
        for path in sensitive_paths:
            driver.get(PAYROLL_URL + path)
            time.sleep(2)
            src_check = driver.page_source.lower()
            if any(kw in src_check for kw in salary_kw) and "login" not in driver.current_url.lower():
                sp2 = shot(driver, f"T5_exposed_{path.replace('/','_')}")
                print(f"      [EXPOSED] {path} shows salary data without auth!")
                record_bug(
                    f"[Payroll][Security] {path} accessible without authentication",
                    f"Accessing {PAYROLL_URL}{path} directly exposes salary data without login.",
                    "critical", sp2,
                )

    except Exception as e:
        print(f"  [ERROR] {e}")
        traceback.print_exc()
    finally:
        driver.quit()


def test_billing_page():
    """T6: Test billing page access from main app."""
    print("\n" + "=" * 70)
    print("  T6: Billing Page Test")
    print("=" * 70)

    driver = create_driver()
    try:
        creds = CREDS["org_admin"]
        ok = do_login(driver, MAIN_URL, creds["email"], creds["password"], "billing")
        if not ok:
            log_result("T6-Login", "FAIL", "Cannot login for billing test")
            return

        driver.get(MAIN_URL + "/billing")
        time.sleep(3)
        sp = shot(driver, "T6_billing_page")
        url_after = driver.current_url
        src = driver.page_source
        print(f"    Billing page: {url_after}, title: {driver.title}")
        print(f"    Content length: {len(src)} chars")

        billing_kw = ["billing", "invoice", "subscription", "plan", "payment", "amount"]
        found = [kw for kw in billing_kw if kw in src.lower()]
        if found:
            log_result("T6-BillingPage", "PASS", f"Billing page shows: {found}")
        elif "404" in src.lower() or "not found" in src.lower():
            log_result("T6-BillingPage", "FAIL", "Billing page returns 404")
            record_bug("[Payroll] Billing page returns 404",
                       f"Navigating to {MAIN_URL}/billing returns 404 or not found.",
                       "medium", sp)
        else:
            log_result("T6-BillingPage", "WARN", "Billing page loaded but no billing keywords found")

    except Exception as e:
        print(f"  [ERROR] {e}")
    finally:
        driver.quit()


# -- File all bugs to GitHub --------------------------------------------------
def file_all_bugs():
    if not bugs_found:
        print("\n  No bugs to file.")
        return
    print(f"\n  Filing {len(bugs_found)} GitHub issues...")
    for bug in bugs_found:
        labels = ["bug", "payroll"]
        sev = bug["severity"].lower()
        if sev in ("critical", "high", "medium", "low"):
            labels.append(f"priority:{sev}")

        body = f"## Bug Report (Automated E2E Test)\n\n"
        body += f"**Severity:** {bug['severity'].upper()}\n"
        body += f"**Module:** Payroll\n"
        body += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        body += f"### Description\n{bug['description']}\n\n"
        if bug.get("screenshot"):
            body += f"### Screenshot\nSaved locally: `{bug['screenshot']}`\n\n"
        body += "### Steps to Reproduce\n1. Run automated E2E payroll test suite\n2. See details above\n\n"
        body += "---\n*Filed by EMP Cloud E2E Test Suite*"

        file_github_issue(bug["title"], body, labels)
        time.sleep(1)


# -- Main ---------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  EMP Cloud HRMS - Payroll Module E2E Test Suite v2")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Each test gets its own fresh driver to avoid session bleed
    test_orgadmin_payroll_subdomain()
    test_employee_payroll()
    test_superadmin_payroll()
    test_payroll_api_auth()
    test_payroll_direct_no_sso()
    test_billing_page()

    # File bugs
    file_all_bugs()

    # Summary
    print("\n" + "=" * 70)
    print("  FINAL TEST SUMMARY")
    print("=" * 70)
    passes = sum(1 for r in test_results if r["status"] == "PASS")
    fails = sum(1 for r in test_results if r["status"] == "FAIL")
    warns = sum(1 for r in test_results if r["status"] == "WARN")
    print(f"  PASS: {passes}  |  FAIL: {fails}  |  WARN: {warns}  |  BUGS FILED: {len(bugs_found)}")
    print()
    for r in test_results:
        icon = {"PASS": " OK ", "FAIL": "FAIL", "WARN": "WARN"}[r["status"]]
        print(f"  [{icon}] {r['test']}: {r['details']}")
    if bugs_found:
        print(f"\n  BUGS ({len(bugs_found)}):")
        for b in bugs_found:
            print(f"    [{b['severity'].upper()}] {b['title']}")
    print("\n" + "=" * 70)
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
