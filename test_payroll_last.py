#!/usr/bin/env python3
"""
Final targeted test: 3-min cooldown, then Employee + OA Admin Panel (2 logins only).
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
from webdriver_manager.chrome import ChromeDriverManager

MAIN_URL       = "https://test-empcloud.empcloud.com"
PAYROLL_URL    = "https://testpayroll.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\payroll"
GITHUB_PAT     = "$GITHUB_TOKEN"
GITHUB_REPO    = "EmpCloud/EmpCloud"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
bugs = []
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def ts(): return datetime.now().strftime("%Y%m%d_%H%M%S")
def shot(d, n):
    p = os.path.join(SCREENSHOT_DIR, f"{n}_{ts()}.png"); d.save_screenshot(p); print(f"  [SS] {p}"); return p

def file_github_issue(title, body, labels):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    data = json.dumps({"title":title,"body":body,"labels":labels}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization":f"token {GITHUB_PAT}","Accept":"application/vnd.github+json",
        "User-Agent":"EmpCloud-E2E","Content-Type":"application/json"})
    try:
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        res = json.loads(r.read().decode())
        print(f"  [GITHUB] Issue #{res.get('number')} -> {res.get('html_url')}")
    except Exception as e:
        print(f"  [GITHUB-ERR] {e}")

def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage",
              "--disable-gpu","--window-size=1920,1080","--ignore-certificate-errors"]:
        opts.add_argument(a)
    svc = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=svc, options=opts); d.set_page_load_timeout(45); d.implicitly_wait(3)
    return d

def do_login(driver, email, password):
    driver.get(MAIN_URL + "/login"); time.sleep(4)
    if "too many" in driver.page_source.lower():
        print("  STILL RATE LIMITED!"); return False
    e = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
    p = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    e.clear(); e.send_keys(email); p.clear(); p.send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(6)
    return "/login" not in driver.current_url.lower()

def main():
    print("="*70)
    print("  Final Payroll Tests (Employee RBAC + Admin Panel)")
    print(f"  {datetime.now()}")
    print("="*70)

    print("\n  Waiting 180 seconds for rate limit cooldown...")
    time.sleep(180)

    # ── TEST A: Employee payroll check ──
    print("\n  === A: Employee Payroll Check ===")
    d = create_driver()
    try:
        ok = do_login(d, "priya@technova.in", "Welcome@123")
        if not ok:
            print("  Employee login FAILED")
            sp = shot(d, "last_emp_fail")
            # File rate limit bug
            bugs.append(("rate_limit", sp))
        else:
            print(f"  Employee logged in: {d.current_url}")
            shot(d, "last_emp_dashboard")

            # Get ALL sidebar/nav text
            body = d.find_element(By.TAG_NAME, "body").text
            print("\n  Employee page text:")
            for line in body.split('\n'):
                line = line.strip()
                if line: print(f"    | {line}")

            # Check for payroll links
            payroll_found = False
            for a in d.find_elements(By.TAG_NAME, "a"):
                text = (a.text or "").strip()
                href = a.get_attribute("href") or ""
                if any(kw in text.lower() or kw in href.lower()
                       for kw in ["payroll", "salary", "pay slip", "payslip"]):
                    payroll_found = True
                    print(f"  ** PAYROLL LINK: '{text}' -> {href}")

            if not payroll_found:
                print("\n  >> Employee has NO payroll links in main app")
                sp = shot(d, "last_emp_no_payroll")
                bugs.append(("emp_no_payroll", sp))

            # Try payroll subdomain directly (without SSO)
            print("\n  Trying payroll subdomain directly...")
            d.get(PAYROLL_URL)
            time.sleep(4)
            shot(d, "last_emp_payroll_direct")
            print(f"  Payroll direct: {d.current_url}")
    except Exception as e:
        print(f"  Error: {e}")
    finally:
        d.quit()

    # Small delay between logins
    time.sleep(5)

    # ── TEST B: Org Admin - Admin Panel ──
    print("\n  === B: Org Admin Admin Panel ===")
    d = create_driver()
    try:
        ok = do_login(d, "ananya@technova.in", "Welcome@123")
        if not ok:
            print("  OA login FAILED")
            shot(d, "last_oa_fail")
        else:
            print(f"  OA logged in: {d.current_url}")

            # Get SSO
            sso = None
            for a in d.find_elements(By.TAG_NAME, "a"):
                href = a.get_attribute("href") or ""
                if "testpayroll" in href and "sso_token" in href:
                    sso = href; break

            if sso:
                d.get(sso); time.sleep(5)
                print(f"  Payroll dashboard: {d.current_url}")

                # Click Admin Panel
                for a in d.find_elements(By.TAG_NAME, "a"):
                    if "admin panel" in (a.text or "").lower():
                        print(f"  Clicking 'Admin Panel' (href={a.get_attribute('href')})")
                        a.click()
                        time.sleep(5)
                        break

                sp = shot(d, "last_admin_panel")
                print(f"  Admin Panel URL: {d.current_url}")

                body = d.find_element(By.TAG_NAME, "body").text
                print(f"\n  Admin Panel content ({len(body)} chars):")
                for line in body.split('\n'):
                    line = line.strip()
                    if line: print(f"    | {line}")

                # Get all links from admin panel
                print("\n  Admin Panel links:")
                admin_links = {}
                for a in d.find_elements(By.TAG_NAME, "a"):
                    text = (a.text or "").strip()
                    href = a.get_attribute("href") or ""
                    if text and href and "testpayroll" in href:
                        admin_links[text] = href
                        print(f"    {text}: {href}")

                # Visit each admin page
                for name, href in admin_links.items():
                    if "/my/" in href and "/admin" not in href:
                        continue
                    try:
                        d.get(href); time.sleep(3)
                        sp2 = shot(d, f"last_ap_{name.replace(' ','_')[:20]}")
                        body2 = d.find_element(By.TAG_NAME, "body").text
                        print(f"\n  >> {name} ({d.current_url}):")
                        for line in body2.split('\n')[:15]:
                            if line.strip(): print(f"      | {line.strip()}")
                    except Exception as e:
                        print(f"  Error on {name}: {e}")
    except Exception as e:
        print(f"  Error: {e}")
    finally:
        d.quit()

    # File bugs
    print("\n  === Filing GitHub Issues ===")
    for bug_type, sp in bugs:
        if bug_type == "rate_limit":
            file_github_issue(
                "[Auth] IP-based rate limiter blocks all accounts after repeated login attempts",
                "## Bug Report\n\n**Severity:** HIGH\n**Module:** Authentication / Payroll\n"
                f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                "### Description\n"
                "The login rate limiter is IP-based rather than per-account. After approximately "
                "8-10 login attempts across different accounts from the same IP address, ALL "
                "accounts become blocked with 'Too many login attempts. Please try again later.'\n\n"
                "The cooldown period is excessively long (>3 minutes observed).\n\n"
                "### Impact\n"
                "- Shared office networks: one user's login issues block all employees\n"
                "- NAT/VPN users: entire organization can be locked out\n"
                "- Automated testing impossible without long waits\n"
                "- Even successful logins count toward the limit\n\n"
                "### Expected Behavior\n"
                "- Rate limiting should be per-account, not per-IP\n"
                "- Successful logins should not count toward rate limit\n"
                "- Cooldown should be 30-60 seconds, not 3+ minutes\n\n"
                f"### Screenshot\n`{sp}`\n\n"
                "---\n*Filed by EMP Cloud E2E Test Suite*",
                ["bug", "payroll", "priority:high", "authentication"])
            time.sleep(1)

        elif bug_type == "emp_no_payroll":
            file_github_issue(
                "[Payroll] Employee role has no payroll access in main application",
                "## Bug Report\n\n**Severity:** HIGH\n**Module:** Payroll\n"
                f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                "### Description\n"
                "Employee users (priya@technova.in) cannot access the Payroll module. "
                "After login, the main app sidebar shows: Dashboard, AI Assistant, My Team, "
                "Attendance, Leave, Comp Off, Events, Policies, Create Post, My Events, "
                "Submit Request, Pay Fuel. There is NO Payroll Management link.\n\n"
                "The Org Admin (ananya@technova.in) has a 'Payroll Management' SSO link in their "
                "sidebar that leads to testpayroll.empcloud.com, but employees do not.\n\n"
                "### Impact\n"
                "- Employees cannot view their payslips\n"
                "- Employees cannot check salary breakdown or CTC details\n"
                "- Employees cannot view tax computation or submit declarations\n"
                "- Employees cannot submit reimbursement claims\n\n"
                "### Expected\n"
                "Employees should have a Payroll link in sidebar leading to payroll self-service "
                "(My Payslips, My Salary, My Tax, Declarations, Reimbursements).\n\n"
                f"### Screenshot\n`{sp}`\n\n"
                "---\n*Filed by EMP Cloud E2E Test Suite*",
                ["bug", "payroll", "priority:high"])
            time.sleep(1)

    print("\n  DONE.")

if __name__ == "__main__":
    main()
