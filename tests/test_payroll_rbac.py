#!/usr/bin/env python3
"""
EMP Cloud HRMS - Payroll RBAC & Remaining Tests
1. Employee payroll access + RBAC (can see own, cannot see others)
2. Super Admin payroll access (blank page bug)
3. Org Admin Admin Panel on payroll subdomain
4. Admin panel /admin paths exploration
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

MAIN_URL       = "https://test-empcloud.empcloud.com"
PAYROLL_URL    = "https://testpayroll.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\payroll"
GITHUB_PAT     = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO    = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
bugs_found = []
test_results = []
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def ts(): return datetime.now().strftime("%Y%m%d_%H%M%S")
def shot(d, n):
    p = os.path.join(SCREENSHOT_DIR, f"{n}_{ts()}.png")
    d.save_screenshot(p); print(f"    [SS] {p}"); return p
def log_result(n, s, d=""):
    test_results.append({"test":n,"status":s,"details":d})
    print(f"  [{s}] {n}: {d}")
def record_bug(t, d, sev, sp=None):
    bugs_found.append({"title":t,"description":d,"severity":sev,"screenshot":sp})
    print(f"  [BUG-{sev.upper()}] {t}")

def file_github_issue(title, body, labels=None):
    if labels is None: labels = ["bug"]
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    data = json.dumps({"title":title,"body":body,"labels":labels}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization":f"token {GITHUB_PAT}","Accept":"application/vnd.github+json",
        "User-Agent":"EmpCloud-E2E","Content-Type":"application/json"})
    try:
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        res = json.loads(r.read().decode())
        print(f"    [GITHUB] Issue #{res.get('number')} -> {res.get('html_url')}")
        return res
    except Exception as e:
        print(f"    [GITHUB-ERR] {e}")
    return None

def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage",
              "--disable-gpu","--window-size=1920,1080","--ignore-certificate-errors"]:
        opts.add_argument(a)
    svc = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(45); d.implicitly_wait(3)
    return d

def do_login(driver, email, password, label=""):
    print(f"    Login: {email}")
    driver.get(MAIN_URL + "/login")
    time.sleep(4)
    src = driver.page_source.lower()
    if "too many" in src: return False, "rate_limited"
    try:
        e = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        p = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        e.clear(); e.send_keys(email); p.clear(); p.send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except Exception as ex:
        return False, f"field_error: {ex}"
    time.sleep(6)
    shot(driver, f"login_{label}")
    url = driver.current_url
    if "login failed" in driver.page_source.lower(): return False, "invalid_credentials"
    if "too many" in driver.page_source.lower(): return False, "rate_limited"
    ok = "/login" not in url.lower()
    print(f"    -> {url} ok={ok}")
    return ok, "ok" if ok else "unknown"

def get_sso_link(driver):
    try:
        for a in driver.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href") or ""
            if "testpayroll.empcloud.com" in href and "sso_token" in href:
                return href
    except: pass
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
                if tok: return tok
    except: pass
    return None


# ============================================================================
# T1: Employee payroll access and RBAC
# ============================================================================
def test_employee_payroll_rbac():
    print("\n" + "="*70)
    print("  T1: Employee Payroll Access & RBAC")
    print("="*70)

    driver = create_driver()
    try:
        ok, reason = do_login(driver, "priya@technova.in", "Welcome@123", "emp_rbac")
        if not ok:
            log_result("T1-EmpLogin", "FAIL", f"Employee login failed: {reason}")
            return
        log_result("T1-EmpLogin", "PASS", f"Logged in: {driver.current_url}")

        # Check employee dashboard for payroll link
        shot(driver, "T1_emp_dashboard")
        sso_link = get_sso_link(driver)

        if sso_link:
            log_result("T1-EmpPayrollAccess", "PASS", "Employee has payroll SSO link")
            driver.get(sso_link)
            time.sleep(5)
            sp = shot(driver, "T1_emp_payroll_home")
            src = driver.page_source

            # What does the employee see?
            print(f"    Employee payroll URL: {driver.current_url}")
            print(f"    Page title: {driver.title}")
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                # Print first 500 chars of visible text
                for line in body_text.split('\n')[:30]:
                    line = line.strip()
                    if line and len(line) > 2:
                        print(f"      | {line}")
            except: pass

            # Check own payslip
            has_payslip = any(kw in src.lower() for kw in ["payslip", "net pay", "gross", "salary", "ctc"])
            if has_payslip:
                log_result("T1-EmpOwnPayslip", "PASS", "Employee can see own payroll data")
            else:
                log_result("T1-EmpOwnPayslip", "WARN", "No payroll data visible on employee dashboard")

            # Visit employee payroll pages
            emp_pages = [
                ("/my/payslips", "My Payslips"),
                ("/my/salary", "My Salary"),
                ("/my/tax", "My Tax"),
                ("/my/declarations", "Declarations"),
                ("/my/reimbursements", "Reimbursements"),
            ]
            for path, name in emp_pages:
                try:
                    driver.get(PAYROLL_URL + path)
                    time.sleep(2)
                    if len(driver.page_source) > 2000 and "404" not in driver.page_source.lower():
                        sp = shot(driver, f"T1_emp_{name.replace(' ','_')}")
                        print(f"      [OK] {name}: {driver.current_url}")
                except Exception as e:
                    print(f"      [ERR] {name}: {e}")

            # ── RBAC: Check sidebar - does employee see "Admin Panel"? ──
            print("\n    -- RBAC: Checking if employee sees Admin Panel --")
            driver.get(PAYROLL_URL + "/my")
            time.sleep(3)
            sidebar_text = ""
            try:
                # Get all sidebar text
                sidebar_els = driver.find_elements(By.CSS_SELECTOR, "nav, aside, [class*='sidebar'], [class*='Sidebar']")
                for el in sidebar_els:
                    sidebar_text += " " + (el.text or "")
                if not sidebar_text.strip():
                    sidebar_text = driver.find_element(By.TAG_NAME, "body").text
            except: pass

            has_admin_link = "admin panel" in sidebar_text.lower() or "admin" in sidebar_text.lower()
            print(f"    Employee sidebar has 'Admin': {has_admin_link}")

            if has_admin_link:
                log_result("T1-EmpAdminVisible", "WARN", "Employee sees 'Admin' in sidebar (checking access...)")
            else:
                log_result("T1-EmpAdminVisible", "PASS", "Employee does NOT see Admin Panel in sidebar")

            # ── RBAC: Try admin pages directly ──
            print("\n    -- RBAC: Employee trying admin URLs --")
            admin_paths = ["/admin", "/admin/dashboard", "/admin/employees",
                          "/admin/payroll", "/admin/pay-runs", "/admin/settings",
                          "/admin/salary-structure", "/admin/reports"]
            rbac_violations = []
            for path in admin_paths:
                try:
                    driver.get(PAYROLL_URL + path)
                    time.sleep(3)
                    final_url = driver.current_url
                    src_lower = driver.page_source.lower()
                    page_len = len(driver.page_source)

                    # Check if redirected away from admin
                    redirected_to_my = "/my" in final_url and "/admin" not in final_url
                    redirected_to_login = "login" in final_url.lower()
                    has_403 = "403" in src_lower or "forbidden" in src_lower or "unauthorized" in src_lower
                    has_admin_content = any(kw in src_lower for kw in [
                        "employee list", "all employees", "pay run", "salary structure",
                        "run payroll", "payroll settings", "manage", "total employees"])

                    if redirected_to_my or redirected_to_login or has_403:
                        print(f"      [BLOCKED] {path} -> {final_url}")
                    elif has_admin_content and page_len > 3000:
                        sp3 = shot(driver, f"T1_rbac_violation_{path.replace('/','_')}")
                        rbac_violations.append({"path": path, "url": final_url, "ss": sp3})
                        print(f"      [VIOLATION!] {path} -> {final_url} (has admin content)")
                    elif page_len > 3000 and "/admin" in final_url:
                        sp3 = shot(driver, f"T1_rbac_check_{path.replace('/','_')}")
                        print(f"      [CHECK] {path} -> {final_url} ({page_len} bytes, checking content...)")
                        # Could be an empty admin shell
                        try:
                            visible = driver.find_element(By.TAG_NAME, "body").text.strip()
                            if len(visible) < 100:
                                print(f"        -> Minimal visible text ({len(visible)} chars), likely empty shell")
                            else:
                                print(f"        -> Visible text: {visible[:200]}")
                                rbac_violations.append({"path": path, "url": final_url, "ss": sp3})
                        except: pass
                    else:
                        print(f"      [OK] {path} -> {final_url} ({page_len} bytes)")
                except Exception as e:
                    print(f"      [ERR] {path}: {e}")

            if rbac_violations:
                log_result("T1-RBAC-Admin", "FAIL",
                          f"{len(rbac_violations)} admin pages accessible to employee")
                desc = "Employee can access admin payroll pages:\n\n"
                for v in rbac_violations:
                    desc += f"- `{v['path']}` -> `{v['url']}`\n"
                desc += "\nEmployee should NOT have access to admin payroll functionality."
                record_bug(
                    "[Payroll][Security] Employee role can access admin payroll pages (RBAC bypass)",
                    desc, "critical", rbac_violations[0].get("ss"))
            else:
                log_result("T1-RBAC-Admin", "PASS", "Employee properly blocked from all admin pages")

        else:
            log_result("T1-EmpPayrollAccess", "WARN", "Employee has no payroll SSO link in main app sidebar")
            sp = shot(driver, "T1_emp_no_payroll")
            # Check if payroll link might be elsewhere
            src = driver.page_source.lower()
            if "payroll" in src:
                print("    'payroll' text found in page source but no SSO link")

    except Exception as e:
        print(f"  [ERROR] {e}"); traceback.print_exc()
    finally:
        driver.quit()


# ============================================================================
# T2: Super Admin - payroll access & blank page bug
# ============================================================================
def test_superadmin_payroll():
    print("\n" + "="*70)
    print("  T2: Super Admin Payroll Access")
    print("="*70)

    driver = create_driver()
    try:
        ok, reason = do_login(driver, "admin@empcloud.com", "SuperAdmin@2026", "sa_rbac")
        if not ok:
            log_result("T2-SA-Login", "FAIL", f"Super Admin login failed: {reason}")
            return
        log_result("T2-SA-Login", "PASS", f"Logged in: {driver.current_url}")

        # Check what SA sees
        sp = shot(driver, "T2_sa_post_login")
        sa_url = driver.current_url
        src = driver.page_source

        # Check if it's a blank page
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
            print(f"    SA page visible text length: {len(body_text)}")
            if len(body_text) < 50:
                print(f"    SA page is effectively BLANK")
                log_result("T2-SA-BlankPage", "FAIL", f"Super Admin dashboard at {sa_url} is blank")
                record_bug(
                    "[Payroll] Super Admin dashboard shows blank page after login",
                    f"After logging in as Super Admin (admin@empcloud.com), the page at "
                    f"`{sa_url}` is completely blank - no content, no navigation, no sidebar.\n\n"
                    f"**Page HTML size:** {len(src)} bytes\n"
                    f"**Visible text:** '{body_text[:100]}'\n\n"
                    f"**Expected:** Super Admin should see an admin dashboard with "
                    f"organization management, payroll oversight, and system settings.",
                    "high", sp)
            else:
                print(f"    SA page text: {body_text[:300]}")
                log_result("T2-SA-Page", "PASS", f"SA dashboard has content ({len(body_text)} chars)")
        except Exception as e:
            print(f"    Error checking SA page: {e}")

        # Check for payroll link
        sso_link = get_sso_link(driver)
        if sso_link:
            log_result("T2-SA-PayrollLink", "PASS", "Super Admin has payroll SSO link")
            driver.get(sso_link)
            time.sleep(5)
            sp2 = shot(driver, "T2_sa_payroll")
            print(f"    SA payroll: {driver.current_url}")
        else:
            log_result("T2-SA-PayrollLink", "WARN", "No payroll SSO link for Super Admin")

        # Navigate SA main app
        sa_pages = ["/admin/super", "/admin", "/dashboard", "/billing",
                    "/settings", "/admin/organizations"]
        for path in sa_pages:
            try:
                driver.get(MAIN_URL + path)
                time.sleep(2)
                if len(driver.page_source) > 2000:
                    sp3 = shot(driver, f"T2_sa_{path.replace('/','_')}")
                    btext = driver.find_element(By.TAG_NAME, "body").text.strip()
                    print(f"      {path}: {driver.current_url} ({len(btext)} chars visible)")
            except: pass

    except Exception as e:
        print(f"  [ERROR] {e}"); traceback.print_exc()
    finally:
        driver.quit()


# ============================================================================
# T3: Org Admin - Admin Panel deep dive on payroll
# ============================================================================
def test_orgadmin_admin_panel():
    print("\n" + "="*70)
    print("  T3: Org Admin - Payroll Admin Panel")
    print("="*70)

    driver = create_driver()
    try:
        ok, _ = do_login(driver, "ananya@technova.in", "Welcome@123", "oa_ap")
        if not ok:
            log_result("T3-Login", "FAIL", "Login failed")
            return
        sso_link = get_sso_link(driver)
        if not sso_link:
            log_result("T3-SSO", "FAIL", "No SSO link")
            return

        driver.get(sso_link)
        time.sleep(5)

        # Find and click Admin Panel
        print("    Looking for Admin Panel link...")
        admin_href = None
        admin_text = ""
        try:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for a in all_links:
                text = (a.text or "").strip()
                href = a.get_attribute("href") or ""
                if "admin" in text.lower() and href:
                    admin_href = href
                    admin_text = text
                    print(f"    Found: '{text}' -> {href}")
                    break
        except: pass

        if not admin_href:
            # Try by scanning all clickable elements
            try:
                for el in driver.find_elements(By.CSS_SELECTOR, "a, button, [role='link']"):
                    t = (el.text or "").strip().lower()
                    if "admin" in t:
                        admin_href = el.get_attribute("href") or "click"
                        admin_text = el.text
                        if admin_href == "click":
                            el.click()
                            time.sleep(4)
                            admin_href = driver.current_url
                        break
            except: pass

        if admin_href and admin_href != "click":
            driver.get(admin_href)
            time.sleep(4)

        sp = shot(driver, "T3_admin_panel")
        admin_url = driver.current_url
        print(f"    Admin Panel URL: {admin_url}")

        # Gather all visible text
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"    Admin Panel visible text ({len(body_text)} chars):")
            for line in body_text.split('\n')[:40]:
                line = line.strip()
                if line and len(line) > 2:
                    print(f"      | {line}")
        except: pass

        # Find all navigation in admin panel
        admin_nav = {}
        try:
            for a in driver.find_elements(By.TAG_NAME, "a"):
                text = (a.text or "").strip()
                href = a.get_attribute("href") or ""
                if href and "testpayroll" in href and text and len(text) < 60:
                    if text not in admin_nav:
                        admin_nav[text] = href
        except: pass

        print(f"\n    Admin Panel navigation ({len(admin_nav)} items):")
        for name, href in admin_nav.items():
            print(f"      - {name}: {href}")

        # Visit each admin sub-page
        for name, href in list(admin_nav.items()):
            if "/my/" in href and "/admin" not in href:
                continue  # Skip employee-side pages
            try:
                driver.get(href)
                time.sleep(3)
                sp2 = shot(driver, f"T3_ap_{name.replace(' ','_').replace('/','')[:25]}")
                try:
                    btext = driver.find_element(By.TAG_NAME, "body").text
                    content_lines = [l.strip() for l in btext.split('\n') if l.strip() and len(l.strip()) > 3]
                    print(f"      [OK] {name}: {driver.current_url}")
                    for line in content_lines[:5]:
                        print(f"           | {line}")
                except: pass
            except Exception as e:
                print(f"      [ERR] {name}: {e}")

        if admin_nav:
            log_result("T3-AdminPanel", "PASS", f"Admin Panel accessible, {len(admin_nav)} navigation items found")
        else:
            log_result("T3-AdminPanel", "WARN", "Admin Panel loaded but no navigation items found")
            # Still screenshot what we see
            print("    Trying direct admin paths...")
            for path in ["/admin/employees", "/admin/payroll", "/admin/pay-runs",
                        "/admin/salary-structure", "/admin/settings", "/admin/reports",
                        "/admin/reimbursements", "/admin/tax"]:
                try:
                    driver.get(PAYROLL_URL + path)
                    time.sleep(2)
                    if len(driver.page_source) > 2000 and "404" not in driver.page_source.lower():
                        sp3 = shot(driver, f"T3_direct_{path.replace('/','_')}")
                        btext = driver.find_element(By.TAG_NAME, "body").text.strip()
                        print(f"      [OK] {path}: {driver.current_url} ({len(btext)} chars)")
                        for line in btext.split('\n')[:5]:
                            if line.strip(): print(f"           | {line.strip()}")
                except: pass

    except Exception as e:
        print(f"  [ERROR] {e}"); traceback.print_exc()
    finally:
        driver.quit()


# ============================================================================
def file_all_bugs():
    if not bugs_found:
        print("\n  No new bugs to file.")
        return
    print(f"\n  Filing {len(bugs_found)} GitHub issues...")
    for bug in bugs_found:
        labels = ["bug", "payroll", f"priority:{bug['severity']}"]
        body = (f"## Bug Report (E2E Test)\n\n**Severity:** {bug['severity'].upper()}\n"
                f"**Module:** Payroll\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                f"### Description\n{bug['description']}\n\n")
        if bug.get("screenshot"):
            body += f"### Screenshot\n`{bug['screenshot']}`\n\n"
        body += "---\n*Filed by EMP Cloud E2E Test Suite*"
        file_github_issue(bug["title"], body, labels)
        time.sleep(1)

def main():
    print("="*70)
    print("  EMP Cloud - Payroll RBAC & Admin Panel Tests")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    test_employee_payroll_rbac()
    test_superadmin_payroll()
    test_orgadmin_admin_panel()

    file_all_bugs()

    print("\n" + "="*70)
    print("  SUMMARY")
    print("="*70)
    p = sum(1 for r in test_results if r["status"]=="PASS")
    f = sum(1 for r in test_results if r["status"]=="FAIL")
    w = sum(1 for r in test_results if r["status"]=="WARN")
    print(f"  PASS: {p}  |  FAIL: {f}  |  WARN: {w}  |  BUGS: {len(bugs_found)}")
    for r in test_results:
        icon = {"PASS":" OK ","FAIL":"FAIL","WARN":"WARN"}[r["status"]]
        print(f"  [{icon}] {r['test']}: {r['details']}")
    if bugs_found:
        print(f"\n  BUGS ({len(bugs_found)}):")
        for b in bugs_found:
            print(f"    [{b['severity'].upper()}] {b['title']}")
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
