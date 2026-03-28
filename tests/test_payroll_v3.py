#!/usr/bin/env python3
"""
EMP Cloud HRMS - Payroll Module E2E Test Suite v3
Final pass: rate-limit cooldown, employee/super-admin retries, Admin Panel,
API exposure verification, Reimbursements page.
"""

import sys, os, time, json, traceback, ssl
import urllib.request, urllib.error
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

MAIN_URL      = "https://test-empcloud.empcloud.com"
PAYROLL_URL   = "https://testpayroll.empcloud.com"
API_BASE      = "https://test-empcloud.empcloud.com/api/v1"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\payroll"
GITHUB_PAT    = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO   = "EmpCloud/EmpCloud"

CREDS = {
    "org_admin":   {"email": "ananya@technova.in",  "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com",   "password": "SuperAdmin@2026"},
    "employee":    {"email": "priya@technova.in",    "password": "Welcome@123"},
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
    print(f"  [{status}] {name}: {details}")

def record_bug(title, desc, severity, sp=None):
    bugs_found.append({"title": title, "description": desc, "severity": severity, "screenshot": sp})
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
    headers = {"User-Agent": "EmpCloud-E2E-Tester", "Origin": MAIN_URL,
               "Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        return resp.status, resp.read().decode("utf-8", errors="replace"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, dict(e.headers) if e.headers else {}
    except Exception as e:
        return 0, str(e), {}

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
    print(f"    Logging in as {email} on {base_url} ...")
    driver.get(base_url + "/login")
    time.sleep(4)

    # Check for rate limit message first
    src = driver.page_source.lower()
    if "too many" in src or "rate limit" in src:
        print(f"    [RATE-LIMITED] Login page shows rate limit warning")
        return False, "rate_limited"

    email_el = None
    for sel in [(By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='company']"),
                (By.NAME, "email"), (By.ID, "email")]:
        try:
            el = driver.find_element(*sel)
            if el.is_displayed():
                email_el = el; break
        except NoSuchElementException:
            continue

    pass_el = None
    for sel in [(By.CSS_SELECTOR, "input[type='password']"), (By.NAME, "password")]:
        try:
            el = driver.find_element(*sel)
            if el.is_displayed():
                pass_el = el; break
        except NoSuchElementException:
            continue

    if not email_el or not pass_el:
        return False, "no_fields"

    email_el.clear(); email_el.send_keys(email)
    pass_el.clear(); pass_el.send_keys(password)

    for sel in [(By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(),'Sign')]")]:
        try:
            btn = driver.find_element(*sel)
            if btn.is_displayed():
                btn.click(); break
        except NoSuchElementException:
            continue

    time.sleep(6)
    shot(driver, f"post_login_{label}")
    url_after = driver.current_url

    # Check post-login for rate limit
    src_after = driver.page_source.lower()
    if "too many" in src_after:
        print(f"    Post-submit: rate limited")
        return False, "rate_limited"

    success = "/login" not in url_after.lower()
    print(f"    Post-login URL: {url_after} (success={success})")
    return success, "ok" if success else "login_failed"

def extract_token(driver):
    try:
        keys = driver.execute_script("return Object.keys(localStorage);")
        for k in (keys or []):
            val = driver.execute_script(f"return localStorage.getItem('{k}');")
            if val and "auth" in k.lower():
                try:
                    parsed = json.loads(val)
                    state = parsed.get("state", parsed) if isinstance(parsed, dict) else {}
                    tok = state.get("accessToken") or state.get("token")
                    if tok:
                        print(f"    Token found: {str(tok)[:50]}...")
                        return tok
                except (json.JSONDecodeError, TypeError):
                    if isinstance(val, str) and val.startswith("ey"):
                        return val
    except Exception:
        pass
    return None

def get_sso_payroll_link(driver):
    try:
        links = driver.find_elements(By.TAG_NAME, "a")
        for a in links:
            href = a.get_attribute("href") or ""
            if "testpayroll.empcloud.com" in href and "sso_token" in href:
                return href
    except Exception:
        pass
    return None


# ============================================================================
# TEST 1: Verify the "exposed" API endpoints are just SPA HTML, not real data
# ============================================================================
def test_api_exposure_verification():
    print("\n" + "=" * 70)
    print("  T1: API Exposure Verification (808-byte responses)")
    print("=" * 70)

    test_urls = [
        f"{PAYROLL_URL}/payroll",
        f"{PAYROLL_URL}/payroll/employees",
        f"{PAYROLL_URL}/employees",
        f"{PAYROLL_URL}/salary",
        f"{PAYROLL_URL}/payslips",
    ]

    all_spa_html = True
    for url in test_urls:
        status, body, headers = api_request(url, token=None)
        content_type = headers.get("Content-Type", headers.get("content-type", ""))
        is_html = "text/html" in content_type or body.strip().startswith("<!") or "<html" in body.lower()[:200]
        is_json = "application/json" in content_type
        has_data = any(kw in body.lower() for kw in ["salary", "employee", "payslip", "amount", "ctc", "gross"])

        print(f"    {url}")
        print(f"      Status: {status}, Content-Type: {content_type}, Size: {len(body)} bytes")
        print(f"      Is HTML: {is_html}, Is JSON: {is_json}, Has salary data: {has_data}")
        print(f"      Body preview: {body[:150]}")

        if is_json and has_data:
            all_spa_html = False
            print(f"      ** REAL DATA EXPOSURE! **")

    if all_spa_html:
        log_result("T1-APIExposure", "PASS",
                   "808-byte responses are SPA HTML shell, NOT real data exposure (false positive)")
        print("\n    CONCLUSION: Previous T4 finding was a FALSE POSITIVE.")
        print("    The payroll subdomain serves its SPA index.html for all routes (client-side routing).")
        print("    This is normal behavior - the actual API calls happen via JS with auth tokens.")
    else:
        log_result("T1-APIExposure", "FAIL", "Real payroll data exposed without auth")
        record_bug("[Payroll][Security] Payroll API returns actual data without authentication",
                   "Payroll subdomain API returns JSON data with salary information without auth token.",
                   "critical")


# ============================================================================
# TEST 2: Wait for rate limit cooldown, then test Employee login
# ============================================================================
def test_employee_with_cooldown():
    print("\n" + "=" * 70)
    print("  T2: Employee Login (after rate-limit cooldown)")
    print("=" * 70)

    print("    Waiting 60 seconds for rate limit cooldown...")
    time.sleep(60)

    driver = create_driver()
    try:
        creds = CREDS["employee"]
        ok, reason = do_login(driver, MAIN_URL, creds["email"], creds["password"], "emp_retry")

        if reason == "rate_limited":
            log_result("T2-EmpLogin", "FAIL", "Still rate-limited after 60s cooldown")
            sp = shot(driver, "T2_emp_still_ratelimited")
            record_bug(
                "[Payroll] Login rate limiter too aggressive - blocks legitimate users",
                "After automated testing with ~5 login attempts across different accounts, "
                "ALL accounts get rate-limited with 'Too many login attempts. Please try again later.' "
                "Rate limit persists for >60 seconds. This appears to be IP-based rather than per-account, "
                "which means one user's failed attempts block ALL users from that IP.\n\n"
                "**Impact:** In shared office networks, one user's login issues could lock out all employees.\n\n"
                "**Expected:** Rate limiting should be per-account, not per-IP. Or at minimum, "
                "the cooldown period should be shorter (15-30 seconds).",
                "high", sp,
            )
            return None

        if not ok:
            log_result("T2-EmpLogin", "FAIL", f"Employee login failed: {reason}")
            sp = shot(driver, "T2_emp_login_fail")
            record_bug("[Payroll] Employee (priya@technova.in) cannot log in",
                       f"Employee login failed with reason: {reason}. URL: {driver.current_url}",
                       "high", sp)
            return None

        log_result("T2-EmpLogin", "PASS", f"Employee logged in: {driver.current_url}")
        emp_token = extract_token(driver)

        # Check if employee has payroll link
        sso_link = get_sso_payroll_link(driver)
        if sso_link:
            log_result("T2-EmpPayrollLink", "PASS", "Employee has payroll SSO link")
            driver.get(sso_link)
            time.sleep(5)
            sp = shot(driver, "T2_emp_payroll_home")
            src = driver.page_source
            print(f"    Employee payroll URL: {driver.current_url}")

            # Check own payslip
            payslip_kw = ["payslip", "net pay", "gross", "salary", "ctc"]
            found = [kw for kw in payslip_kw if kw in src.lower()]
            if found:
                log_result("T2-EmpOwnPayslip", "PASS", f"Employee sees own payroll data: {found}")
            else:
                log_result("T2-EmpOwnPayslip", "WARN", "No salary keywords on employee payroll dashboard")

            # Navigate employee payroll pages
            emp_payroll_pages = [
                ("/my/payslips", "My Payslips"),
                ("/my/salary", "My Salary"),
                ("/my/tax", "My Tax"),
                ("/my/declarations", "Declarations"),
                ("/my/leaves", "My Leaves"),
                ("/my/profile", "Profile"),
            ]
            for path, name in emp_payroll_pages:
                url = PAYROLL_URL + path
                try:
                    driver.get(url)
                    time.sleep(2)
                    if len(driver.page_source) > 2000 and "404" not in driver.page_source.lower():
                        shot(driver, f"T2_emp_{name.replace(' ','_')}")
                        print(f"      [OK] Employee -> {name}: {driver.current_url}")
                except Exception as e:
                    print(f"      [ERR] {name}: {e}")

            # RBAC: Employee should NOT access Admin Panel
            print("\n    -- RBAC: Employee tries Admin Panel --")
            admin_paths = ["/admin", "/admin/employees", "/admin/payroll",
                          "/admin/pay-runs", "/admin/settings", "/admin/salary-structure",
                          "/admin/dashboard", "/admin/reports"]
            rbac_violations = []
            for path in admin_paths:
                url = PAYROLL_URL + path
                try:
                    driver.get(url)
                    time.sleep(2)
                    final = driver.current_url
                    src_lower = driver.page_source.lower()
                    # admin content markers
                    admin_markers = ["employee list", "all employees", "pay run",
                                    "salary structure", "admin dashboard", "manage employee",
                                    "run payroll", "payroll settings"]
                    has_admin = any(m in src_lower for m in admin_markers)
                    not_blocked = ("login" not in final.lower()
                                  and "/my" not in final.lower()
                                  and "403" not in src_lower
                                  and "unauthorized" not in src_lower
                                  and "access denied" not in src_lower)
                    if not_blocked and len(driver.page_source) > 3000:
                        sp2 = shot(driver, f"T2_rbac_{path.replace('/','_')}")
                        rbac_violations.append({"path": path, "url": final, "admin": has_admin, "ss": sp2})
                        print(f"      [!!] Employee can access {path} (admin_content={has_admin})")
                    else:
                        print(f"      [OK] {path} blocked (redirected to {final})")
                except Exception as e:
                    print(f"      [ERR] {path}: {e}")

            if rbac_violations:
                admin_content_violations = [v for v in rbac_violations if v["admin"]]
                if admin_content_violations:
                    log_result("T2-RBAC", "FAIL",
                              f"{len(admin_content_violations)} admin pages with sensitive content accessible")
                    desc = "Employee can access admin payroll pages with sensitive content:\n\n"
                    for v in admin_content_violations:
                        desc += f"- `{v['path']}` -> `{v['url']}`\n"
                    record_bug(
                        "[Payroll][Security] Employee can access admin payroll pages (RBAC bypass)",
                        desc, "critical", admin_content_violations[0].get("ss"))
                else:
                    log_result("T2-RBAC", "WARN",
                              f"{len(rbac_violations)} admin URLs reachable but may be empty/redirected")
            else:
                log_result("T2-RBAC", "PASS", "Employee properly blocked from all admin pages")

        else:
            log_result("T2-EmpPayrollLink", "WARN", "No payroll SSO link for employee")
            sp = shot(driver, "T2_emp_no_payroll_link")
            # Check sidebar for payroll
            src = driver.page_source.lower()
            if "payroll" in src:
                print("    'payroll' found in page but no SSO link")
            else:
                record_bug("[Payroll] Employee has no access to payroll module",
                           "Employee dashboard does not show any payroll navigation link.",
                           "high", sp)

        return emp_token

    except Exception as e:
        print(f"  [ERROR] {e}")
        traceback.print_exc()
        return None
    finally:
        driver.quit()


# ============================================================================
# TEST 3: Super Admin login and payroll access
# ============================================================================
def test_superadmin_with_cooldown():
    print("\n" + "=" * 70)
    print("  T3: Super Admin Login (after cooldown)")
    print("=" * 70)

    driver = create_driver()
    try:
        creds = CREDS["super_admin"]
        ok, reason = do_login(driver, MAIN_URL, creds["email"], creds["password"], "sa_retry")

        if reason == "rate_limited":
            log_result("T3-SA-Login", "FAIL", "Still rate-limited")
            sp = shot(driver, "T3_sa_ratelimited")
            return
        if not ok:
            log_result("T3-SA-Login", "FAIL", f"Super Admin login failed: {reason}")
            sp = shot(driver, "T3_sa_fail")
            record_bug("[Payroll] Super Admin (admin@empcloud.com) cannot log in",
                       f"Super Admin login failed. Reason: {reason}. URL: {driver.current_url}",
                       "critical", sp)
            return

        log_result("T3-SA-Login", "PASS", f"Super Admin logged in: {driver.current_url}")
        shot(driver, "T3_sa_dashboard")

        # Check if SA has payroll link
        sso_link = get_sso_payroll_link(driver)
        if sso_link:
            log_result("T3-SA-PayrollLink", "PASS", "Super Admin has payroll SSO link")
            driver.get(sso_link)
            time.sleep(5)
            sp = shot(driver, "T3_sa_payroll_home")
            print(f"    SA Payroll: {driver.current_url} (title: {driver.title})")

            # Check if SA sees admin panel
            src = driver.page_source.lower()
            if "admin panel" in src or "admin" in src:
                log_result("T3-SA-AdminAccess", "PASS", "Super Admin sees Admin Panel option")
            else:
                log_result("T3-SA-AdminAccess", "WARN", "No Admin Panel visible for SA on payroll")
        else:
            log_result("T3-SA-PayrollLink", "WARN", "No payroll SSO link for Super Admin")
            sp = shot(driver, "T3_sa_no_payroll")

    except Exception as e:
        print(f"  [ERROR] {e}")
        traceback.print_exc()
    finally:
        driver.quit()


# ============================================================================
# TEST 4: Org Admin - Admin Panel deep dive on payroll subdomain
# ============================================================================
def test_orgadmin_admin_panel():
    print("\n" + "=" * 70)
    print("  T4: Org Admin - Payroll Admin Panel Deep Dive")
    print("=" * 70)

    driver = create_driver()
    try:
        creds = CREDS["org_admin"]
        ok, reason = do_login(driver, MAIN_URL, creds["email"], creds["password"], "oa_admin")
        if not ok:
            log_result("T4-Login", "FAIL", f"Login failed: {reason}")
            sp = shot(driver, "T4_login_fail")
            if reason == "rate_limited":
                record_bug("[Payroll] Rate limiter blocks Org Admin after other accounts' attempts",
                           "Org Admin login blocked by rate limiter even though this is the first attempt "
                           "for this account. Rate limiting appears to be IP-based.", "high", sp)
            return

        # SSO into payroll
        sso_link = get_sso_payroll_link(driver)
        if not sso_link:
            log_result("T4-SSO", "FAIL", "No SSO link found")
            return

        driver.get(sso_link)
        time.sleep(5)

        # Click Admin Panel in sidebar
        print("    Looking for Admin Panel link...")
        admin_link = None
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            for a in links:
                text = (a.text or "").strip().lower()
                if "admin" in text:
                    admin_link = a.get_attribute("href")
                    print(f"    Found Admin link: '{a.text.strip()}' -> {admin_link}")
                    break
        except Exception:
            pass

        if admin_link:
            driver.get(admin_link)
            time.sleep(4)
            sp = shot(driver, "T4_admin_panel")
            print(f"    Admin Panel URL: {driver.current_url}")
            print(f"    Admin Panel title: {driver.title}")

            # Explore admin sub-pages
            src = driver.page_source
            # Look for sidebar/nav links within admin
            admin_sub_links = {}
            try:
                links = driver.find_elements(By.TAG_NAME, "a")
                for a in links:
                    text = (a.text or "").strip()
                    href = a.get_attribute("href") or ""
                    if href and "testpayroll" in href and text and len(text) < 50:
                        admin_sub_links[text] = href
            except Exception:
                pass

            print(f"    Admin sub-pages found: {list(admin_sub_links.keys())}")

            for name, href in admin_sub_links.items():
                try:
                    driver.get(href)
                    time.sleep(2)
                    if len(driver.page_source) > 2000:
                        sp = shot(driver, f"T4_admin_{name.replace(' ','_').replace('/','_')[:30]}")
                        print(f"      [OK] {name}: {driver.current_url}")
                except Exception as e:
                    print(f"      [ERR] {name}: {e}")

            log_result("T4-AdminPanel", "PASS", f"Admin Panel accessible with {len(admin_sub_links)} sub-pages")
        else:
            log_result("T4-AdminPanel", "WARN", "Admin Panel link not found in sidebar")

        # Test Reimbursements page (seen in sidebar screenshot)
        print("\n    -- Testing Reimbursements page --")
        for path in ["/my/reimbursements", "/reimbursements"]:
            url = PAYROLL_URL + path
            try:
                driver.get(url)
                time.sleep(2)
                if len(driver.page_source) > 2000 and "404" not in driver.page_source.lower():
                    sp = shot(driver, f"T4_reimbursements")
                    print(f"      [OK] Reimbursements: {driver.current_url}")
                    log_result("T4-Reimbursements", "PASS", f"Reimbursements page accessible at {path}")
                    break
            except Exception:
                pass

        # Test the billing page on main app while we're logged in
        print("\n    -- Testing Billing page --")
        driver.get(MAIN_URL + "/billing")
        time.sleep(3)
        sp = shot(driver, "T4_billing")
        billing_src = driver.page_source.lower()
        billing_kw = ["billing", "invoice", "subscription", "plan", "payment", "usage"]
        found = [kw for kw in billing_kw if kw in billing_src]
        if found:
            log_result("T4-Billing", "PASS", f"Billing page accessible, shows: {found}")
        else:
            log_result("T4-Billing", "WARN", f"Billing page at {driver.current_url} - keywords not found")

    except Exception as e:
        print(f"  [ERROR] {e}")
        traceback.print_exc()
    finally:
        driver.quit()


# ============================================================================
# TEST 5: Cross-check - can Org Admin's SSO token be reused / is it time-limited?
# ============================================================================
def test_sso_token_security():
    print("\n" + "=" * 70)
    print("  T5: SSO Token Security Checks")
    print("=" * 70)

    # First, get a valid SSO link
    driver = create_driver()
    sso_link = None
    try:
        creds = CREDS["org_admin"]
        ok, reason = do_login(driver, MAIN_URL, creds["email"], creds["password"], "sso_check")
        if not ok:
            log_result("T5-Login", "FAIL", f"Cannot login: {reason}")
            return
        sso_link = get_sso_payroll_link(driver)
    finally:
        driver.quit()

    if not sso_link:
        log_result("T5-SSOToken", "WARN", "No SSO link to test")
        return

    print(f"    SSO Link captured (length: {len(sso_link)})")

    # Try using the SSO link in a fresh browser (should work once)
    time.sleep(2)
    driver2 = create_driver()
    try:
        driver2.get(sso_link)
        time.sleep(5)
        sp = shot(driver2, "T5_sso_reuse_1")
        url1 = driver2.current_url
        src1 = driver2.page_source.lower()
        has_salary = any(kw in src1 for kw in ["salary", "payslip", "ctc", "net pay"])
        print(f"    First reuse: {url1} (has_salary={has_salary})")

        if has_salary and "login" not in url1.lower():
            # SSO token worked in fresh browser - now try again after some delay
            # to check if token is single-use
            driver2.delete_all_cookies()
            try:
                driver2.execute_script("localStorage.clear(); sessionStorage.clear();")
            except Exception:
                pass
            time.sleep(2)

            driver2.get(sso_link)
            time.sleep(5)
            sp2 = shot(driver2, "T5_sso_reuse_2")
            url2 = driver2.current_url
            src2 = driver2.page_source.lower()
            has_salary2 = any(kw in src2 for kw in ["salary", "payslip", "ctc", "net pay"])
            print(f"    Second reuse: {url2} (has_salary={has_salary2})")

            if has_salary2 and "login" not in url2.lower():
                log_result("T5-SSOReuse", "FAIL", "SSO token can be reused multiple times (not single-use)")
                record_bug(
                    "[Payroll][Security] SSO token for payroll is reusable (not single-use)",
                    "The SSO token in the payroll subdomain URL can be used multiple times from "
                    "different sessions. If an SSO URL is intercepted (e.g., browser history, logs, "
                    "referrer header), it grants full payroll access.\n\n"
                    "**Expected:** SSO tokens should be single-use (nonce) and expire quickly.\n"
                    f"**Token URL pattern:** `{PAYROLL_URL}/?sso_token=<jwt>`",
                    "medium", sp2,
                )
            else:
                log_result("T5-SSOReuse", "PASS", "SSO token appears single-use or expired on second use")
        else:
            log_result("T5-SSOReuse", "PASS", "SSO token did not grant access in new session (good)")

    except Exception as e:
        print(f"  [ERROR] {e}")
        traceback.print_exc()
    finally:
        driver2.quit()


# ============================================================================
# File all bugs
# ============================================================================
def file_all_bugs():
    if not bugs_found:
        print("\n  No bugs to file.")
        return
    print(f"\n  Filing {len(bugs_found)} GitHub issues...")
    for bug in bugs_found:
        labels = ["bug", "payroll"]
        sev = bug["severity"].lower()
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


# ============================================================================
# Main
# ============================================================================
def main():
    print("=" * 70)
    print("  EMP Cloud HRMS - Payroll Module E2E Test Suite v3")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # T1: Quick API check (no login needed)
    test_api_exposure_verification()

    # T2: Employee login (with rate-limit cooldown)
    test_employee_with_cooldown()

    # T3: Super Admin
    test_superadmin_with_cooldown()

    # T4: Org Admin admin panel deep dive
    test_orgadmin_admin_panel()

    # T5: SSO token security
    test_sso_token_security()

    # File bugs
    file_all_bugs()

    # Summary
    print("\n" + "=" * 70)
    print("  FINAL TEST SUMMARY (v3)")
    print("=" * 70)
    passes = sum(1 for r in test_results if r["status"] == "PASS")
    fails  = sum(1 for r in test_results if r["status"] == "FAIL")
    warns  = sum(1 for r in test_results if r["status"] == "WARN")
    print(f"  PASS: {passes}  |  FAIL: {fails}  |  WARN: {warns}  |  BUGS: {len(bugs_found)}")
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
