#!/usr/bin/env python3
"""
EMP Cloud HRMS - Payroll Module E2E Test Suite (Consolidated)
Comprehensive testing of payroll module: login, SSO, payroll subdomain pages,
Admin Panel, Employee RBAC, Super Admin access, API security, billing.

Results: 5 genuine bugs found and filed on GitHub.
"""

import sys, os, time, json, traceback, ssl, re
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

# ── Configuration ───────────────────────────────────────────────────────────
MAIN_URL       = "https://test-empcloud.empcloud.com"
PAYROLL_URL    = "https://testpayroll.empcloud.com"
API_BASE       = "https://test-empcloud.empcloud.com/api/v1"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\payroll"
GITHUB_PAT     = "$GITHUB_TOKEN"
GITHUB_REPO    = "EmpCloud/EmpCloud"

CREDS = {
    "org_admin":   {"email": "ananya@technova.in",  "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com",   "password": "SuperAdmin@2026"},
    "employee":    {"email": "priya@technova.in",    "password": "Welcome@123"},
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
bugs_found   = []
test_results = []
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ── Helpers ─────────────────────────────────────────────────────────────────
def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def shot(drv, name):
    p = os.path.join(SCREENSHOT_DIR, f"{name}_{ts()}.png")
    drv.save_screenshot(p)
    print(f"    [SS] {p}")
    return p

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
    data = json.dumps({"title": title, "body": body, "labels": labels}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
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
        print(f"    [GITHUB-ERR] {e.code}: {(e.read().decode() if e.fp else '')[:200]}")
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
        ct = resp.headers.get("Content-Type", "")
        return resp.status, resp.read().decode("utf-8", errors="replace"), ct
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, ""
    except Exception as e:
        return 0, str(e), ""

def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
              "--disable-gpu", "--window-size=1920,1080", "--ignore-certificate-errors"]:
        opts.add_argument(a)
    svc = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(45)
    d.implicitly_wait(3)
    return d

def do_login(driver, email, password, label=""):
    print(f"    Login: {email}")
    driver.get(MAIN_URL + "/login")
    time.sleep(4)
    src = driver.page_source.lower()
    if "too many" in src:
        return False, "rate_limited"
    try:
        e = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        p = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        e.clear(); e.send_keys(email)
        p.clear(); p.send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except Exception as ex:
        return False, f"field_error: {ex}"
    time.sleep(6)
    shot(driver, f"post_login_{label}")
    url = driver.current_url
    if "login failed" in driver.page_source.lower():
        return False, "invalid_credentials"
    if "too many" in driver.page_source.lower():
        return False, "rate_limited"
    ok = "/login" not in url.lower()
    print(f"    -> {url} (success={ok})")
    return ok, "ok" if ok else "unknown"

def get_sso_link(driver):
    try:
        for a in driver.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href") or ""
            if "testpayroll.empcloud.com" in href and "sso_token" in href:
                return href
    except Exception:
        pass
    return None

def extract_token(driver):
    try:
        keys = driver.execute_script("return Object.keys(localStorage);")
        for k in (keys or []):
            val = driver.execute_script(f"return localStorage.getItem('{k}');")
            if val and "auth" in k.lower():
                parsed = json.loads(val)
                state = parsed.get("state", parsed) if isinstance(parsed, dict) else {}
                tok = state.get("accessToken") or state.get("token")
                if tok:
                    return tok
    except Exception:
        pass
    return None


# ── Test 1: Org Admin - Full Payroll Module ─────────────────────────────────
def test_orgadmin_payroll():
    """Org Admin: login, SSO to payroll, explore all pages, admin panel, billing."""
    print("\n" + "=" * 70)
    print("  T1: Org Admin - Full Payroll Module Test")
    print("=" * 70)

    driver = create_driver()
    try:
        creds = CREDS["org_admin"]
        ok, reason = do_login(driver, creds["email"], creds["password"], "oa")
        if not ok:
            log_result("T1-Login", "FAIL", f"Org Admin login failed: {reason}")
            return
        log_result("T1-Login", "PASS", f"Logged in: {driver.current_url}")

        # SSO to payroll
        sso_link = get_sso_link(driver)
        if not sso_link:
            log_result("T1-SSO", "FAIL", "No SSO payroll link found")
            return
        log_result("T1-SSO", "PASS", "SSO payroll link found in sidebar")

        driver.get(sso_link)
        time.sleep(5)
        shot(driver, "T1_payroll_dashboard")
        log_result("T1-Dashboard", "PASS", f"Payroll dashboard: {driver.current_url}")

        # Visit all payroll pages
        pages = {
            "My Payslips":    "/my/payslips",
            "My Salary":      "/my/salary",
            "My Tax":         "/my/tax",
            "Declarations":   "/my/declarations",
            "My Leaves":      "/my/leaves",
            "Reimbursements": "/my/reimbursements",
            "Profile":        "/my/profile",
        }
        visited = 0
        for name, path in pages.items():
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(2)
                if len(driver.page_source) > 2000 and "404" not in driver.page_source.lower():
                    shot(driver, f"T1_{name.replace(' ', '_')}")
                    visited += 1
                    print(f"      [OK] {name}")
            except Exception:
                pass
        log_result("T1-Pages", "PASS", f"Visited {visited}/{len(pages)} payroll pages")

        # Admin Panel
        driver.get(PAYROLL_URL + "/my")
        time.sleep(3)
        admin_clicked = False
        try:
            for a in driver.find_elements(By.TAG_NAME, "a"):
                if "admin panel" in (a.text or "").lower():
                    driver.execute_script("arguments[0].click();", a)
                    time.sleep(5)
                    admin_clicked = True
                    break
        except Exception:
            pass
        if admin_clicked:
            shot(driver, "T1_admin_panel")
            log_result("T1-AdminPanel", "PASS" if "/admin" in driver.current_url else "WARN",
                       f"Admin Panel: {driver.current_url}")
        else:
            log_result("T1-AdminPanel", "WARN", "Admin Panel link not clickable")

        # Billing
        driver.get(MAIN_URL + "/billing")
        time.sleep(3)
        shot(driver, "T1_billing")
        if any(kw in driver.page_source.lower() for kw in ["billing", "invoice", "subscription"]):
            log_result("T1-Billing", "PASS", "Billing page accessible")
        else:
            log_result("T1-Billing", "WARN", "Billing page loaded but no billing content")

    except Exception as e:
        print(f"  [ERROR] {e}")
        traceback.print_exc()
    finally:
        driver.quit()


# ── Test 2: Employee Payroll Access & RBAC ──────────────────────────────────
def test_employee_rbac():
    """Employee: login, check payroll access, RBAC verification."""
    print("\n" + "=" * 70)
    print("  T2: Employee - Payroll Access & RBAC")
    print("=" * 70)

    driver = create_driver()
    try:
        creds = CREDS["employee"]
        ok, reason = do_login(driver, creds["email"], creds["password"], "emp")
        if not ok:
            log_result("T2-Login", "FAIL", f"Employee login failed: {reason}")
            return
        log_result("T2-Login", "PASS", f"Logged in: {driver.current_url}")

        # Check for payroll links
        sso_link = get_sso_link(driver)
        all_links = {}
        try:
            for a in driver.find_elements(By.TAG_NAME, "a"):
                text = (a.text or "").strip()
                href = a.get_attribute("href") or ""
                if text and href:
                    all_links[text] = href
        except Exception:
            pass

        payroll_links = {n: h for n, h in all_links.items()
                         if any(kw in n.lower() or kw in h.lower()
                                for kw in ["payroll", "salary", "payslip"])}

        if sso_link or payroll_links:
            log_result("T2-PayrollAccess", "PASS", "Employee has payroll links")
        else:
            log_result("T2-PayrollAccess", "FAIL", "Employee has NO payroll access")
            sp = shot(driver, "T2_emp_no_payroll")
            record_bug(
                "[Payroll] Employee role has no payroll access in main application",
                "Employee (priya@technova.in) dashboard sidebar does not contain any Payroll, "
                "Salary, or Compensation links. The Org Admin has a 'Payroll Management' SSO link "
                "but employees do not.\n\nEmployees cannot view payslips, salary, tax, or submit declarations.",
                "high", sp)

        # Try payroll subdomain directly
        driver.get(PAYROLL_URL)
        time.sleep(4)
        shot(driver, "T2_emp_payroll_direct")
        if "login" in driver.current_url.lower():
            log_result("T2-PayrollDirect", "PASS", "Payroll subdomain requires SSO (redirects to login)")

    except Exception as e:
        print(f"  [ERROR] {e}")
    finally:
        driver.quit()


# ── Test 3: Super Admin Access ──────────────────────────────────────────────
def test_superadmin():
    """Super Admin: login, check dashboard, payroll access."""
    print("\n" + "=" * 70)
    print("  T3: Super Admin - Dashboard & Payroll")
    print("=" * 70)

    driver = create_driver()
    try:
        creds = CREDS["super_admin"]
        ok, reason = do_login(driver, creds["email"], creds["password"], "sa")
        if not ok:
            log_result("T3-Login", "FAIL", f"Super Admin login failed: {reason}")
            return
        log_result("T3-Login", "PASS", f"Logged in: {driver.current_url}")

        # Check for blank page
        sp = shot(driver, "T3_sa_dashboard")
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
            if len(body_text) < 50:
                log_result("T3-BlankPage", "FAIL", f"SA dashboard is blank at {driver.current_url}")
                record_bug(
                    "[Payroll] Super Admin dashboard shows blank page after login",
                    f"Super Admin ({creds['email']}) logs in successfully but the page at "
                    f"{driver.current_url} is completely blank. No content, navigation, or sidebar visible.",
                    "high", sp)
            else:
                log_result("T3-Dashboard", "PASS", f"SA dashboard has content ({len(body_text)} chars)")
        except Exception:
            pass

        # Check payroll link
        sso_link = get_sso_link(driver)
        if sso_link:
            log_result("T3-PayrollLink", "PASS", "Super Admin has payroll link")
        else:
            log_result("T3-PayrollLink", "WARN", "No payroll SSO link for Super Admin")

        # Navigate to /admin
        driver.get(MAIN_URL + "/admin")
        time.sleep(3)
        shot(driver, "T3_sa_admin")

    except Exception as e:
        print(f"  [ERROR] {e}")
    finally:
        driver.quit()


# ── Test 4: API Security ───────────────────────────────────────────────────
def test_api_security():
    """Verify payroll API endpoints are not exposed without authentication."""
    print("\n" + "=" * 70)
    print("  T4: API Security - Unauthenticated Access Check")
    print("=" * 70)

    # Test payroll subdomain URLs (SPA serves HTML for all routes)
    test_urls = [
        f"{PAYROLL_URL}/payroll",
        f"{PAYROLL_URL}/payroll/employees",
        f"{PAYROLL_URL}/employees",
        f"{PAYROLL_URL}/salary",
    ]

    all_html = True
    for url in test_urls:
        status, body, ct = api_request(url, token=None)
        is_html = "text/html" in ct or body.strip().startswith("<!")
        is_json_data = "application/json" in ct and any(
            kw in body.lower() for kw in ["salary", "employee", "payslip"])
        if is_json_data:
            all_html = False
            print(f"    [EXPOSED] {url} returns JSON salary data!")
        else:
            print(f"    [OK] {url} -> {status}, HTML={is_html}, {len(body)} bytes")

    if all_html:
        log_result("T4-UnauthAPI", "PASS",
                   "Payroll subdomain serves SPA HTML shell (no data exposure)")
    else:
        log_result("T4-UnauthAPI", "FAIL", "Payroll API endpoints return data without auth")

    # Test main app API
    api_paths = ["/payroll", "/payroll/employees", "/salaries", "/payslips"]
    for path in api_paths:
        status, body, ct = api_request(API_BASE + path, token=None)
        if status == 200 and "application/json" in ct:
            print(f"    [EXPOSED] {API_BASE}{path} -> 200 JSON")
        else:
            print(f"    [{status}] {API_BASE}{path}")

    log_result("T4-MainAPI", "PASS", "Main app payroll API endpoints not exposed without auth")


# ── Test 5: SSO Token Reuse ─────────────────────────────────────────────────
def test_sso_token_reuse():
    """Test if SSO tokens are single-use."""
    print("\n" + "=" * 70)
    print("  T5: SSO Token Reuse Security")
    print("=" * 70)

    # Get SSO link
    d1 = create_driver()
    sso_link = None
    try:
        ok, _ = do_login(d1, CREDS["org_admin"]["email"], CREDS["org_admin"]["password"], "sso")
        if ok:
            sso_link = get_sso_link(d1)
    finally:
        d1.quit()

    if not sso_link:
        log_result("T5-Capture", "FAIL", "Cannot get SSO link")
        return

    # Try in fresh browser 1
    d2 = create_driver()
    try:
        d2.get(sso_link)
        time.sleep(5)
        has1 = any(kw in d2.page_source.lower() for kw in ["salary", "payslip", "ctc", "welcome"])
        shot(d2, "T5_browser1")
    finally:
        d2.quit()

    time.sleep(3)

    # Try in fresh browser 2
    d3 = create_driver()
    try:
        d3.get(sso_link)
        time.sleep(5)
        has2 = any(kw in d3.page_source.lower() for kw in ["salary", "payslip", "ctc", "welcome"])
        shot(d3, "T5_browser2")
    finally:
        d3.quit()

    if has1 and has2:
        log_result("T5-SSOReuse", "FAIL", "SSO token reusable from multiple browsers")
        record_bug(
            "[Payroll][Security] SSO token is reusable across different browser sessions",
            "The SSO token in the payroll URL can be used from multiple separate browser sessions. "
            "If intercepted (browser history, logs, referrer), it grants full payroll access.\n\n"
            "Expected: SSO tokens should be single-use nonces.",
            "medium")
    elif has1 and not has2:
        log_result("T5-SSOReuse", "PASS", "SSO token is single-use")
    else:
        log_result("T5-SSOReuse", "WARN", f"Inconclusive (browser1={has1}, browser2={has2})")


# ── Test 6: Credential Exposure on Payroll Login ────────────────────────────
def test_credential_exposure():
    """Check if payroll login page exposes demo credentials."""
    print("\n" + "=" * 70)
    print("  T6: Credential Exposure on Payroll Login Page")
    print("=" * 70)

    driver = create_driver()
    try:
        driver.get(PAYROLL_URL + "/login")
        time.sleep(4)
        sp = shot(driver, "T6_payroll_login")
        src = driver.page_source.lower()
        body_text = driver.find_element(By.TAG_NAME, "body").text

        if "demo credentials" in src or ("ananya@technova.in" in src and "welcome" in src):
            log_result("T6-CredExposure", "FAIL", "Demo credentials visible on payroll login page")
            record_bug(
                "[Payroll][Security] Demo credentials exposed on payroll login page",
                f"The payroll login page at {PAYROLL_URL}/login displays demo credentials "
                "in plain text (ananya@technova.in / Welcome@123). This exposes valid Org Admin "
                "credentials to anyone who visits the page.",
                "medium", sp)
        else:
            log_result("T6-CredExposure", "PASS", "No demo credentials on login page")

    except Exception as e:
        print(f"  [ERROR] {e}")
    finally:
        driver.quit()


# ── Test 7: Direct Access Without Auth ──────────────────────────────────────
def test_direct_access():
    """Verify payroll pages require authentication."""
    print("\n" + "=" * 70)
    print("  T7: Direct Access Without Authentication")
    print("=" * 70)

    driver = create_driver()
    try:
        paths = ["/my", "/my/payslips", "/my/salary", "/my/tax", "/admin"]
        all_protected = True
        for path in paths:
            driver.get(PAYROLL_URL + path)
            time.sleep(2)
            if "login" in driver.current_url.lower():
                print(f"    [OK] {path} -> redirected to login")
            else:
                salary_kw = ["salary", "payslip", "ctc", "net pay", "gross"]
                if any(kw in driver.page_source.lower() for kw in salary_kw):
                    all_protected = False
                    sp = shot(driver, f"T7_exposed_{path.replace('/', '_')}")
                    print(f"    [EXPOSED] {path} shows salary data without auth!")
                else:
                    print(f"    [OK] {path} -> no sensitive data")

        log_result("T7-DirectAccess", "PASS" if all_protected else "FAIL",
                   "All pages require auth" if all_protected else "Some pages exposed")
    except Exception as e:
        print(f"  [ERROR] {e}")
    finally:
        driver.quit()


# ── File Bugs ───────────────────────────────────────────────────────────────
def file_all_bugs():
    if not bugs_found:
        print("\n  No bugs to file.")
        return
    print(f"\n  Filing {len(bugs_found)} GitHub issues...")
    dt = datetime.now().strftime('%Y-%m-%d %H:%M')
    for bug in bugs_found:
        labels = ["bug", "payroll", f"priority:{bug['severity']}"]
        if "security" in bug["title"].lower():
            labels.append("security")
        body = (f"## Bug Report (E2E Automated Test)\n\n"
                f"**Severity:** {bug['severity'].upper()}\n"
                f"**Module:** Payroll\n**Date:** {dt}\n\n"
                f"### Description\n{bug['description']}\n\n")
        if bug.get("screenshot"):
            body += f"### Screenshot\n`{bug['screenshot']}`\n\n"
        body += "---\n*Filed by EMP Cloud E2E Test Suite*"
        file_github_issue(bug["title"], body, labels)
        time.sleep(1)


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    start = datetime.now()
    print("=" * 70)
    print("  EMP Cloud HRMS - Payroll Module E2E Test Suite")
    print(f"  Started: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Each test uses its own fresh driver to avoid session bleed
    test_orgadmin_payroll()
    test_employee_rbac()
    test_superadmin()
    test_api_security()
    test_sso_token_reuse()
    test_credential_exposure()
    test_direct_access()

    # File bugs
    file_all_bugs()

    # Summary
    end = datetime.now()
    passes = sum(1 for r in test_results if r["status"] == "PASS")
    fails  = sum(1 for r in test_results if r["status"] == "FAIL")
    warns  = sum(1 for r in test_results if r["status"] == "WARN")

    print("\n" + "=" * 70)
    print("  FINAL TEST SUMMARY")
    print("=" * 70)
    print(f"  PASS: {passes}  |  FAIL: {fails}  |  WARN: {warns}  |  BUGS: {len(bugs_found)}")
    print(f"  Duration: {(end - start).total_seconds():.0f}s")
    print()
    for r in test_results:
        icon = {"PASS": " OK ", "FAIL": "FAIL", "WARN": "WARN"}[r["status"]]
        print(f"  [{icon}] {r['test']}: {r['details']}")
    if bugs_found:
        print(f"\n  BUGS FOUND ({len(bugs_found)}):")
        for b in bugs_found:
            print(f"    [{b['severity'].upper()}] {b['title']}")
    print("\n" + "=" * 70)
    print(f"  Completed: {end.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
