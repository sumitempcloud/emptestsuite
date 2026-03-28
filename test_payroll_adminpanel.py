#!/usr/bin/env python3
"""
Final: Admin Panel JS click + file remaining bugs (credential exposure, XSS in policies).
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
    if "too many" in driver.page_source.lower(): return False
    e = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
    p = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    e.clear(); e.send_keys(email); p.clear(); p.send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(6)
    return "/login" not in driver.current_url.lower()

def main():
    print("="*70)
    print("  Admin Panel + Bug Filing")
    print(f"  {datetime.now()}")
    print("="*70)

    # ── Admin Panel via JS click and href exploration ──
    print("\n  === Org Admin: Admin Panel ===")
    d = create_driver()
    try:
        ok = do_login(d, "ananya@technova.in", "Welcome@123")
        if not ok:
            print("  OA login failed (likely rate limited)")
            shot(d, "ap_login_fail")
            # Skip to bug filing
            d.quit()
            d = None
        else:
            # SSO
            sso = None
            for a in d.find_elements(By.TAG_NAME, "a"):
                href = a.get_attribute("href") or ""
                if "testpayroll" in href and "sso_token" in href:
                    sso = href; break
            if sso:
                d.get(sso); time.sleep(5)
                print(f"  On payroll: {d.current_url}")

                # Find Admin Panel - try multiple approaches
                # 1. Get href of Admin Panel link
                admin_href = None
                try:
                    links = d.find_elements(By.TAG_NAME, "a")
                    for a in links:
                        txt = (a.text or "").strip()
                        href = a.get_attribute("href") or ""
                        if "admin" in txt.lower():
                            admin_href = href
                            print(f"  Admin link: text='{txt}', href='{href}'")
                            # Also get onclick
                            onclick = a.get_attribute("onclick") or ""
                            print(f"  onclick: {onclick}")
                            # Try JS click
                            d.execute_script("arguments[0].click();", a)
                            time.sleep(5)
                            print(f"  After JS click: {d.current_url}")
                            shot(d, "ap_js_click")
                            break
                except Exception as e:
                    print(f"  Error finding admin link: {e}")

                # If still on /my, try navigating by URL
                if "/my" in d.current_url and "/admin" not in d.current_url:
                    # Try admin href directly
                    if admin_href and admin_href.startswith("http"):
                        d.get(admin_href)
                        time.sleep(4)
                        print(f"  Direct admin href: {d.current_url}")
                        shot(d, "ap_direct_href")

                    # Try common admin paths
                    for path in ["/admin", "/admin/dashboard", "/admin/employees",
                                "/admin/payroll", "/admin/pay-runs", "/admin/salary-structure"]:
                        d.get(PAYROLL_URL + path)
                        time.sleep(3)
                        body = d.find_element(By.TAG_NAME, "body").text.strip()
                        if len(body) > 50 and "login" not in d.current_url.lower():
                            sp = shot(d, f"ap_{path.replace('/','_')}")
                            print(f"\n  {path} -> {d.current_url} ({len(body)} chars):")
                            for line in body.split('\n')[:20]:
                                if line.strip(): print(f"    | {line.strip()}")
                            break
                        else:
                            print(f"  {path} -> {d.current_url} (empty/redirect)")

                # Try full page source inspection for admin routes
                d.get(PAYROLL_URL + "/my")
                time.sleep(3)
                # Check all href values in page source
                page_src = d.page_source
                import re
                hrefs = re.findall(r'href="([^"]*admin[^"]*)"', page_src, re.IGNORECASE)
                print(f"\n  Admin hrefs in page source: {hrefs}")
                for href in hrefs:
                    if href.startswith("/"):
                        full = PAYROLL_URL + href
                    elif href.startswith("http"):
                        full = href
                    else:
                        continue
                    d.get(full)
                    time.sleep(3)
                    body = d.find_element(By.TAG_NAME, "body").text.strip()
                    if len(body) > 50:
                        sp = shot(d, f"ap_href_{href.replace('/','_')[:20]}")
                        print(f"\n  Admin href '{href}' -> {d.current_url}:")
                        for line in body.split('\n')[:15]:
                            if line.strip(): print(f"    | {line.strip()}")

    except Exception as e:
        print(f"  Error: {e}")
        import traceback; traceback.print_exc()
    finally:
        if d: d.quit()

    # ── File remaining bugs ──
    print("\n  === Filing Remaining Bugs ===")
    dt = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Bug 1: Credential exposure on payroll login page
    file_github_issue(
        "[Payroll][Security] Demo credentials exposed on payroll login page",
        f"## Bug Report\n\n**Severity:** MEDIUM\n**Module:** Payroll\n**Date:** {dt}\n\n"
        "### Description\n"
        f"The payroll subdomain login page at `{PAYROLL_URL}/login` displays demo credentials "
        "in plain text: `ananya@technova.in / Welcome@123`.\n\n"
        "This exposes valid login credentials to anyone who visits the payroll login page, "
        "even unauthenticated users.\n\n"
        "### Steps to Reproduce\n"
        f"1. Navigate to {PAYROLL_URL}/login\n"
        "2. Below the login form, visible text reads: 'Demo credentials: ananya@technova.in / Welcome@123'\n\n"
        "### Impact\n"
        "- Valid Org Admin credentials are publicly exposed\n"
        "- Anyone can log in as Org Admin and access all employee payroll data\n"
        "- This grants access to salary, tax, and personal financial information\n\n"
        "### Expected\n"
        "Demo credentials should be removed from the login page, especially in test/staging environments "
        "that may contain real employee data.\n\n"
        f"### Screenshot\n`C:\\Users\\Admin\\screenshots\\payroll\\last_emp_payroll_direct_20260327_234804.png`\n\n"
        "---\n*Filed by EMP Cloud E2E Test Suite*",
        ["bug", "payroll", "priority:medium", "security"])
    time.sleep(1)

    # Bug 2: Rate limiter (already filed #239 for emp_no_payroll, file rate limiter separately)
    file_github_issue(
        "[Auth] Aggressive IP-based rate limiter blocks all accounts (not per-account)",
        f"## Bug Report\n\n**Severity:** HIGH\n**Module:** Authentication\n**Date:** {dt}\n\n"
        "### Description\n"
        "The login rate limiter is IP-based rather than per-account. After approximately 8-10 "
        "login attempts across different user accounts from the same IP address, ALL accounts "
        "become blocked with the message: 'Too many login attempts. Please try again later.'\n\n"
        "The cooldown period is 2-3 minutes, during which no user from that IP can log in.\n\n"
        "### Steps to Reproduce\n"
        "1. Attempt to log in with different accounts (org admin, employee, super admin)\n"
        "2. After ~8-10 total attempts (even successful ones), all accounts are rate-limited\n"
        "3. Wait 2-3 minutes before any account can log in again\n\n"
        "### Impact\n"
        "- **Shared offices:** One user's login issues block ALL employees at that location\n"
        "- **NAT/VPN:** Entire organizations behind a single IP can be locked out\n"
        "- **Automated testing:** E2E test suites are severely impacted\n"
        "- **Successful logins count:** Even valid, successful logins count toward the limit\n\n"
        "### Expected Behavior\n"
        "- Rate limiting should be per-account (email), not per-IP\n"
        "- Successful logins should not increment the rate limit counter\n"
        "- Cooldown should be 30-60 seconds maximum\n"
        "- Consider implementing CAPTCHA instead of hard lockout\n\n"
        f"### Screenshot\n`C:\\Users\\Admin\\screenshots\\payroll\\emp_login_fail_20260327_234322.png`\n\n"
        "---\n*Filed by EMP Cloud E2E Test Suite*",
        ["bug", "authentication", "priority:high"])

    print("\n  DONE.")

if __name__ == "__main__":
    main()
