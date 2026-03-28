#!/usr/bin/env python3
"""
Final pass: Employee payroll access check + file bugs for missing access.
"""

import sys, os, time, json, ssl
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
GITHUB_PAT     = "$GITHUB_TOKEN"
GITHUB_REPO    = "EmpCloud/EmpCloud"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
bugs_found = []
test_results = []
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def ts(): return datetime.now().strftime("%Y%m%d_%H%M%S")
def shot(d, n):
    p = os.path.join(SCREENSHOT_DIR, f"{n}_{ts()}.png"); d.save_screenshot(p); print(f"    [SS] {p}"); return p
def log_result(n, s, d=""):
    test_results.append({"test":n,"status":s,"details":d}); print(f"  [{s}] {n}: {d}")
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
    except Exception as e:
        print(f"    [GITHUB-ERR] {e}")

def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage",
              "--disable-gpu","--window-size=1920,1080","--ignore-certificate-errors"]:
        opts.add_argument(a)
    svc = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=svc, options=opts); d.set_page_load_timeout(45); d.implicitly_wait(3)
    return d

def do_login(driver, email, password, label=""):
    driver.get(MAIN_URL + "/login"); time.sleep(4)
    src = driver.page_source.lower()
    if "too many" in src: return False
    try:
        e = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        p = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        e.clear(); e.send_keys(email); p.clear(); p.send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except: return False
    time.sleep(6)
    return "/login" not in driver.current_url.lower()


def test_employee_payroll_detailed():
    print("\n" + "="*70)
    print("  Employee Payroll Detailed Check")
    print("="*70)

    driver = create_driver()
    try:
        ok = do_login(driver, "priya@technova.in", "Welcome@123", "emp")
        if not ok:
            log_result("EmpLogin", "FAIL", "Cannot log in")
            shot(driver, "emp_login_fail")
            return
        log_result("EmpLogin", "PASS", f"URL: {driver.current_url}")

        # Capture full sidebar text
        print("\n    -- Employee sidebar items --")
        shot(driver, "emp_full_dashboard")
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            for line in body_text.split('\n')[:50]:
                line = line.strip()
                if line and len(line) > 1:
                    print(f"      | {line}")
        except: pass

        # Find ALL links in the page
        print("\n    -- All navigation links --")
        all_links = {}
        try:
            for a in driver.find_elements(By.TAG_NAME, "a"):
                text = (a.text or "").strip()
                href = a.get_attribute("href") or ""
                if text and href and len(text) < 80:
                    all_links[text] = href
        except: pass

        for name, href in all_links.items():
            is_payroll = any(kw in name.lower() or kw in href.lower()
                           for kw in ["payroll", "salary", "pay", "compensation"])
            marker = " ** PAYROLL **" if is_payroll else ""
            print(f"      {name}: {href}{marker}")

        payroll_links = {n:h for n,h in all_links.items()
                        if any(kw in n.lower() or kw in h.lower()
                              for kw in ["payroll", "salary", "pay", "compensation"])}

        if payroll_links:
            log_result("EmpPayrollLink", "PASS", f"Employee has payroll links: {list(payroll_links.keys())}")
            for name, href in payroll_links.items():
                driver.get(href)
                time.sleep(4)
                sp = shot(driver, f"emp_payroll_{name.replace(' ','_')[:20]}")
                print(f"    Navigated to '{name}': {driver.current_url}")
                # Check for salary data
                src = driver.page_source.lower()
                has_salary = any(kw in src for kw in ["salary", "payslip", "ctc", "net pay", "gross"])
                print(f"    Has salary data: {has_salary}")
        else:
            log_result("EmpPayrollLink", "FAIL", "Employee has NO payroll/salary links in dashboard")
            sp = shot(driver, "emp_no_payroll_link")
            record_bug(
                "[Payroll] Employee (priya@technova.in) has no payroll access in main app",
                "After logging in as Employee (priya@technova.in), the main app dashboard sidebar "
                "does not contain any Payroll, Salary, or Compensation links.\n\n"
                "**Sidebar items visible:** Dashboard, AI Assistant, My Team, Attendance, "
                "Leave, Comp Off, Events, Policies, Create Post, My Events, Submit Request, "
                "Pay Fuel, Sign out\n\n"
                "**Missing:** Payroll Management link (which Org Admin has in their sidebar)\n\n"
                "**Impact:** Employees cannot view their payslips, salary details, tax info, "
                "or submit declarations through the main application.\n\n"
                "**Note:** The Org Admin (ananya@technova.in) sees a 'Payroll Management' link "
                "with SSO to testpayroll.empcloud.com, but this link is absent for employees. "
                "Either the employee role lacks the payroll module entitlement, or there's a "
                "configuration issue preventing employees from accessing payroll self-service.",
                "high", sp)

        # Even if no link, try SSO URL directly
        print("\n    -- Trying payroll subdomain directly for employee --")
        driver.get(PAYROLL_URL)
        time.sleep(4)
        sp2 = shot(driver, "emp_payroll_direct")
        print(f"    Direct payroll URL: {driver.current_url}")
        if "login" in driver.current_url.lower():
            print("    -> Redirected to payroll login (no SSO session for employee)")

        # Check if employee can access payroll with Org Admin's SSO token pattern
        # This tests if the payroll subdomain properly validates the user role
        # We won't actually forge tokens, just try the direct URL
        for path in ["/my", "/my/payslips", "/my/salary"]:
            driver.get(PAYROLL_URL + path)
            time.sleep(2)
            if "login" not in driver.current_url.lower():
                sp3 = shot(driver, f"emp_payroll_{path.replace('/','_')}")
                print(f"    [NOTE] {path} -> {driver.current_url}")
            else:
                print(f"    [OK] {path} -> redirected to login")

    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback; traceback.print_exc()
    finally:
        driver.quit()


def test_orgadmin_admin_panel_click():
    """Actually click the Admin Panel link on payroll subdomain."""
    print("\n" + "="*70)
    print("  Org Admin - Click Admin Panel Link")
    print("="*70)

    driver = create_driver()
    try:
        ok = do_login(driver, "ananya@technova.in", "Welcome@123", "oa_click")
        if not ok:
            log_result("OA-Login", "FAIL", "Cannot log in")
            return

        # Get SSO link
        sso_link = None
        for a in driver.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href") or ""
            if "testpayroll.empcloud.com" in href and "sso_token" in href:
                sso_link = href; break
        if not sso_link:
            log_result("OA-SSO", "FAIL", "No SSO link"); return

        driver.get(sso_link)
        time.sleep(5)

        # Click Admin Panel link specifically
        print("    Looking for 'Admin Panel' link...")
        admin_clicked = False
        try:
            for a in driver.find_elements(By.TAG_NAME, "a"):
                if "admin panel" in (a.text or "").lower():
                    href = a.get_attribute("href")
                    print(f"    Found 'Admin Panel': href={href}")
                    a.click()
                    time.sleep(5)
                    admin_clicked = True
                    break
        except Exception as e:
            print(f"    Click error: {e}")

        if admin_clicked:
            sp = shot(driver, "oa_admin_panel_clicked")
            print(f"    After clicking Admin Panel: {driver.current_url}")

            # Get body text
            try:
                body = driver.find_element(By.TAG_NAME, "body").text
                print(f"    Page text ({len(body)} chars):")
                for line in body.split('\n')[:40]:
                    line = line.strip()
                    if line and len(line) > 1:
                        print(f"      | {line}")
            except: pass

            # Find all links on admin page
            print("\n    All links on admin page:")
            try:
                for a in driver.find_elements(By.TAG_NAME, "a"):
                    text = (a.text or "").strip()
                    href = a.get_attribute("href") or ""
                    if text and href and "testpayroll" in href:
                        print(f"      {text}: {href}")
            except: pass

            # Navigate admin sub-pages
            admin_urls_to_try = []
            try:
                for a in driver.find_elements(By.TAG_NAME, "a"):
                    href = a.get_attribute("href") or ""
                    if "/admin" in href and "testpayroll" in href and href not in admin_urls_to_try:
                        admin_urls_to_try.append(href)
            except: pass

            for url in admin_urls_to_try[:10]:
                try:
                    driver.get(url)
                    time.sleep(3)
                    sp2 = shot(driver, f"oa_admin_{url.split('/')[-1][:20]}")
                    body = driver.find_element(By.TAG_NAME, "body").text
                    print(f"\n      Admin page: {driver.current_url}")
                    for line in body.split('\n')[:10]:
                        if line.strip(): print(f"        | {line.strip()}")
                except Exception as e:
                    print(f"      Error: {e}")

            log_result("OA-AdminPanel", "PASS", f"Admin Panel accessed, {len(admin_urls_to_try)} admin URLs found")
        else:
            # Try direct URL
            print("    Could not click Admin Panel, trying /admin directly")
            driver.get(PAYROLL_URL + "/admin")
            time.sleep(4)
            sp = shot(driver, "oa_admin_direct")
            print(f"    /admin -> {driver.current_url}")
            body = driver.find_element(By.TAG_NAME, "body").text
            print(f"    Body text ({len(body)} chars):")
            for line in body.split('\n')[:20]:
                if line.strip(): print(f"      | {line.strip()}")

    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback; traceback.print_exc()
    finally:
        driver.quit()


def file_all_bugs():
    if not bugs_found:
        print("\n  No new bugs to file."); return
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
    print("  EMP Cloud - Employee Payroll & Admin Panel Final Tests")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    test_employee_payroll_detailed()
    test_orgadmin_admin_panel_click()

    file_all_bugs()

    print("\n" + "="*70)
    print("  RESULTS")
    print("="*70)
    for r in test_results:
        icon = {"PASS":" OK ","FAIL":"FAIL","WARN":"WARN"}[r["status"]]
        print(f"  [{icon}] {r['test']}: {r['details']}")
    if bugs_found:
        print(f"\n  BUGS ({len(bugs_found)}):")
        for b in bugs_found:
            print(f"    [{b['severity'].upper()}] {b['title']}")
    print("="*70)

if __name__ == "__main__":
    main()
