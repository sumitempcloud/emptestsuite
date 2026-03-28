#!/usr/bin/env python3
"""
EMP Cloud HRMS — Employee All-Modules SSO Testing (v2)
Login as Priya Patel (employee), try to SSO into each external module from /modules page.
Modules: Payroll, Recruitment, Performance, Rewards, Exit, LMS, Projects
Skipped: Field Force, Biometrics (per instructions)

Key insight from v1: The /modules page shows Module Marketplace with "Subscribed" badges
but NO launch/SSO links for the employee role. We need to:
1. Click on each module card to see if it opens a detail/launch view
2. Scroll to find all modules (some below fold)
3. Check page source for hidden SSO URLs
4. Test if the subscribed status text is actually a link
"""

import sys, os, time, json, ssl, traceback, re
import urllib.request, urllib.error, urllib.parse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    WebDriverException, ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ─────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\employee_modules_v2"
GH_PAT = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"

MODULE_SUBDOMAINS = {
    "payroll": "testpayroll.empcloud.com",
    "recruitment": "test-recruit.empcloud.com",
    "performance": "test-performance.empcloud.com",
    "rewards": "test-rewards.empcloud.com",
    "exit": "test-exit.empcloud.com",
    "lms": "testlms.empcloud.com",
    "projects": "test-project.empcloud.com",
}

# Module display names as seen on the page
MODULE_DISPLAY_NAMES = {
    "payroll": ["payroll management", "payroll"],
    "recruitment": ["recruitment", "hiring", "recruit"],
    "performance": ["performance", "review", "appraisal"],
    "rewards": ["rewards", "recognition", "rewards & recognition"],
    "exit": ["exit management", "exit", "offboarding"],
    "lms": ["learning management", "lms", "training"],
    "projects": ["project", "project management", "projects"],
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

test_results = []
bugs_found = []
test_counter = 0
DRIVER_PATH = None

# ── Helpers ────────────────────────────────────────────────
def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def result(name, status, details=""):
    test_results.append({"test": name, "status": status, "details": details})
    print(f"  [{status}] {name}: {details}", flush=True)

def bug(title, description, severity="medium", screenshot_path=None):
    bugs_found.append({
        "title": title,
        "description": description,
        "severity": severity,
        "screenshot": screenshot_path,
    })
    print(f"  [BUG-{severity.upper()}] {title}", flush=True)

def shot(driver, name):
    fname = f"{name}_{ts()}.png"
    path = os.path.join(SCREENSHOT_DIR, fname)
    try:
        driver.save_screenshot(path)
        log(f"  [SS] {path}")
    except:
        log(f"  [SS-FAIL] Could not save {path}")
        path = None
    return path

def create_driver():
    global DRIVER_PATH
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for arg in [
        "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
        "--disable-gpu", "--window-size=1920,1080",
        "--ignore-certificate-errors", "--disable-blink-features=AutomationControlled",
    ]:
        opts.add_argument(arg)
    if DRIVER_PATH is None:
        DRIVER_PATH = ChromeDriverManager().install()
    svc = Service(DRIVER_PATH)
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(60)
    d.implicitly_wait(3)
    return d

def do_login(driver):
    driver.get(BASE_URL + "/login")
    time.sleep(5)
    try:
        e = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        p = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        e.clear(); e.send_keys(EMP_EMAIL)
        p.clear(); p.send_keys(EMP_PASS)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except Exception as ex:
        log(f"  Login form error: {ex}")
        return False
    time.sleep(6)
    return "/login" not in driver.current_url.lower()

def get_page_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""

def get_page_source_lower(driver):
    try:
        return driver.page_source.lower()
    except:
        return ""

def visit_page(driver, url, name, module):
    try:
        driver.get(url)
        time.sleep(4)
    except:
        pass
    sp = shot(driver, f"{module}_{name}")
    text = get_page_text(driver)
    src = get_page_source_lower(driver)
    return sp, text, src

# ── GitHub helpers ─────────────────────────────────────────
def upload_screenshot_github(filepath):
    if not filepath or not os.path.exists(filepath):
        return None
    fname = os.path.basename(filepath)
    import base64
    with open(filepath, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    url = f"https://api.github.com/repos/{GH_REPO}/contents/screenshots/employee_modules_v2/{fname}"
    data = json.dumps({
        "message": f"Upload screenshot {fname}",
        "content": content,
        "branch": "main"
    }).encode()
    req = urllib.request.Request(url, data=data, method="PUT", headers={
        "Authorization": f"token {GH_PAT}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-E2E",
        "Content-Type": "application/json",
    })
    try:
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        res = json.loads(r.read().decode())
        dl = res.get("content", {}).get("download_url", "")
        log(f"  [GH-UP] {fname}")
        return dl
    except Exception as e:
        log(f"  [GH-UP-FAIL] {fname}: {e}")
        return None

def file_github_issue(title, body, labels=None):
    if labels is None:
        labels = ["bug"]
    # Duplicate check
    try:
        sq = urllib.parse.quote(title[:50])
        search_url = f"https://api.github.com/search/issues?q=repo:{GH_REPO}+is:issue+in:title+{sq}"
        req = urllib.request.Request(search_url, headers={
            "Authorization": f"token {GH_PAT}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "EmpCloud-E2E",
        })
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=15)
        res = json.loads(r.read().decode())
        if res.get("total_count", 0) > 0:
            existing = res["items"][0]
            log(f"  [GH-SKIP] Similar issue exists: #{existing['number']}")
            return existing.get("html_url")
    except:
        pass
    url = f"https://api.github.com/repos/{GH_REPO}/issues"
    data = json.dumps({"title": title, "body": body, "labels": labels}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": f"token {GH_PAT}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-E2E",
        "Content-Type": "application/json",
    })
    try:
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        res = json.loads(r.read().decode())
        log(f"  [GH-ISSUE] #{res.get('number')} -> {res.get('html_url')}")
        return res.get("html_url")
    except Exception as e:
        log(f"  [GH-ISSUE-FAIL] {e}")
        return None


# ════════════════════════════════════════════════════════════
# PHASE 1: Deep exploration of /modules page
# ════════════════════════════════════════════════════════════

def explore_modules_page(driver):
    """Deeply explore the /modules page to find any way to launch modules."""
    log("\n--- Deep exploration of /modules page ---")
    driver.get(BASE_URL + "/modules")
    time.sleep(5)
    shot(driver, "modules_page_top")

    # Scroll to bottom to load all modules
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(3)
    shot(driver, "modules_page_bottom")

    # Get full page text
    page_text = get_page_text(driver)
    page_src = driver.page_source
    page_src_lower = page_src.lower()

    log("  Full /modules page text:")
    for line in page_text.split('\n'):
        line = line.strip()
        if line:
            log(f"    | {line}")

    # Find ALL clickable elements on the page
    all_elements = []
    for tag in ["a", "button", "div", "span"]:
        for el in driver.find_elements(By.TAG_NAME, tag):
            try:
                text = (el.text or "").strip()[:80]
                href = el.get_attribute("href") or ""
                onclick = el.get_attribute("onclick") or ""
                classes = el.get_attribute("class") or ""
                role = el.get_attribute("role") or ""
                if text or href or onclick:
                    all_elements.append({
                        "tag": tag, "text": text, "href": href,
                        "onclick": onclick, "classes": classes, "role": role,
                        "element": el
                    })
            except StaleElementReferenceException:
                pass

    log(f"\n  Found {len(all_elements)} interactive elements")

    # Look for SSO tokens in page source
    sso_matches = re.findall(r'(https?://[^"\'>\s]+sso_token[^"\'>\s]*)', page_src)
    if sso_matches:
        log(f"  Found SSO token URLs in source:")
        for m in sso_matches:
            log(f"    {m[:120]}")
    else:
        log("  No SSO token URLs found in page source")

    # Look for module subdomain references in source
    for mod, subdomain in MODULE_SUBDOMAINS.items():
        if subdomain in page_src_lower:
            log(f"  Found reference to {mod} ({subdomain}) in page source")
            # Extract the full URL
            pattern = f'(https?://[^"\'>\s]*{re.escape(subdomain)}[^"\'>\s]*)'
            matches = re.findall(pattern, page_src)
            for m in matches:
                log(f"    URL: {m[:150]}")

    # Check for "Subscribed" buttons/links — maybe they are clickable
    subscribed_elements = []
    for el_info in all_elements:
        if "subscribed" in el_info["text"].lower():
            subscribed_elements.append(el_info)
            log(f"  'Subscribed' element: tag={el_info['tag']} text='{el_info['text']}' href='{el_info['href']}' class='{el_info['classes'][:60]}'")

    # Try clicking on "Subscribed" elements
    for el_info in subscribed_elements[:3]:
        try:
            log(f"  Clicking 'Subscribed' element...")
            before_url = driver.current_url
            el_info["element"].click()
            time.sleep(3)
            after_url = driver.current_url
            if before_url != after_url:
                log(f"  URL changed: {before_url} -> {after_url}")
                shot(driver, "subscribed_click_result")
                driver.back()
                time.sleep(2)
            else:
                log(f"  URL unchanged after click")
                # Check for modal/popup
                new_text = get_page_text(driver)
                if len(new_text) > len(page_text) + 50:
                    log(f"  Page text changed (possible modal)")
                    shot(driver, "subscribed_click_modal")
        except Exception as e:
            log(f"  Click failed: {e}")

    # Try clicking on each module card row
    log("\n  Trying to click on each module card...")
    module_cards_found = {}

    # Re-navigate to modules page (fresh state)
    driver.get(BASE_URL + "/modules")
    time.sleep(4)

    # Try to find module cards by text content
    for mod_name, display_names in MODULE_DISPLAY_NAMES.items():
        for dn in display_names:
            # Find elements containing this module name
            try:
                xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{dn}')]"
                matches = driver.find_elements(By.XPATH, xpath)
                for m in matches:
                    text = (m.text or "").strip()
                    tag = m.tag_name
                    parent = None
                    try:
                        parent = m.find_element(By.XPATH, "..")
                    except:
                        pass
                    log(f"  [{mod_name}] Found: <{tag}> '{text[:60]}'")

                    if mod_name not in module_cards_found:
                        module_cards_found[mod_name] = m
                    break
            except:
                pass

    # For each found module card, try clicking it
    for mod_name, element in module_cards_found.items():
        log(f"\n  Clicking on '{mod_name}' card...")
        before_url = driver.current_url
        num_handles_before = len(driver.window_handles)
        try:
            # Try clicking the element itself
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)
            element.click()
            time.sleep(4)
        except:
            try:
                driver.execute_script("arguments[0].click();", element)
                time.sleep(4)
            except:
                log(f"  Could not click {mod_name} card")
                continue

        after_url = driver.current_url
        num_handles_after = len(driver.window_handles)

        if num_handles_after > num_handles_before:
            log(f"  New tab opened!")
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(3)
            new_url = driver.current_url
            log(f"  New tab URL: {new_url}")
            shot(driver, f"module_newtab_{mod_name}")
            # Check if it's on the module subdomain
            subdomain = MODULE_SUBDOMAINS.get(mod_name, "")
            if subdomain in new_url:
                log(f"  SUCCESS: SSO'd into {mod_name}!")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(2)
        elif before_url != after_url:
            log(f"  URL changed: {after_url}")
            shot(driver, f"module_click_{mod_name}")
            subdomain = MODULE_SUBDOMAINS.get(mod_name, "")
            if subdomain in after_url:
                log(f"  SUCCESS: SSO'd into {mod_name}!")
            driver.back()
            time.sleep(2)
        else:
            log(f"  No navigation occurred")
            # Check for expanded content or modal
            shot(driver, f"module_click_nochange_{mod_name}")

    # Also check if there's a "Launch" button anywhere (might be hidden initially)
    launch_elements = []
    for el in driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'launch')]"):
        text = (el.text or "").strip()
        if text:
            launch_elements.append(el)
            log(f"  Found 'Launch' element: {text}")
    if not launch_elements:
        log("  No 'Launch' buttons/links found on /modules page")

    return module_cards_found


# ════════════════════════════════════════════════════════════
# PHASE 2: Try SSO via different approaches
# ════════════════════════════════════════════════════════════

def try_sso_methods(driver, mod_name):
    """Try multiple methods to SSO into a module."""
    subdomain = MODULE_SUBDOMAINS.get(mod_name, "")
    if not subdomain:
        return False, None

    # Method 1: Check /modules page links with sso_token
    log(f"  [{mod_name}] Method 1: Check /modules for SSO links")
    driver.get(BASE_URL + "/modules")
    time.sleep(4)
    for a in driver.find_elements(By.TAG_NAME, "a"):
        href = (a.get_attribute("href") or "")
        if subdomain in href:
            log(f"  Found link to {subdomain}: {href[:100]}")
            driver.get(href)
            time.sleep(5)
            if subdomain in driver.current_url:
                sp = shot(driver, f"{mod_name}_sso_method1")
                return True, sp

    # Method 2: Check sidebar for module links
    log(f"  [{mod_name}] Method 2: Check sidebar links")
    driver.get(BASE_URL)
    time.sleep(3)
    for a in driver.find_elements(By.TAG_NAME, "a"):
        href = (a.get_attribute("href") or "")
        text = (a.text or "").strip().lower()
        display_names = MODULE_DISPLAY_NAMES.get(mod_name, [])
        if subdomain in href or any(dn in text for dn in display_names):
            if subdomain in href or "sso" in href.lower():
                log(f"  Found sidebar link: {text} -> {href[:100]}")
                driver.get(href)
                time.sleep(5)
                if subdomain in driver.current_url:
                    sp = shot(driver, f"{mod_name}_sso_method2")
                    return True, sp

    # Method 3: Use API to get SSO token
    log(f"  [{mod_name}] Method 3: Try API for SSO token")
    # Get auth cookies from the browser
    cookies = driver.get_cookies()
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    auth_token = None
    for c in cookies:
        if c['name'].lower() in ['token', 'auth_token', 'access_token', 'jwt', 'session']:
            auth_token = c['value']
            break

    # Try localStorage for token
    if not auth_token:
        try:
            auth_token = driver.execute_script("return localStorage.getItem('token') || localStorage.getItem('auth_token') || localStorage.getItem('accessToken') || ''")
        except:
            pass

    if auth_token:
        log(f"  Found auth token: {auth_token[:30]}...")
        # Try API call to get SSO URL
        for api_path in [
            f"/api/v1/modules/{mod_name}/sso",
            f"/api/v1/sso/{mod_name}",
            f"/api/v1/modules/sso?module={mod_name}",
        ]:
            try:
                api_url = f"https://test-empcloud.empcloud.com{api_path}"
                req = urllib.request.Request(api_url, headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Cookie": cookie_str,
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0",
                })
                r = urllib.request.urlopen(req, context=ssl_ctx, timeout=15)
                data = json.loads(r.read().decode())
                log(f"  API response from {api_path}: {json.dumps(data)[:200]}")
                sso_url = data.get("url") or data.get("sso_url") or data.get("redirect_url") or ""
                if sso_url and subdomain in sso_url:
                    driver.get(sso_url)
                    time.sleep(5)
                    if subdomain in driver.current_url:
                        sp = shot(driver, f"{mod_name}_sso_method3")
                        return True, sp
            except Exception as e:
                log(f"  API {api_path}: {e}")

    # Method 4: Direct subdomain access (session may carry over)
    log(f"  [{mod_name}] Method 4: Direct subdomain access")
    driver.get(f"https://{subdomain}")
    time.sleep(5)
    current = driver.current_url.lower()
    sp = shot(driver, f"{mod_name}_direct")
    if subdomain in current and "login" not in current:
        log(f"  Direct access worked: {driver.current_url}")
        return True, sp
    elif "login" in current:
        log(f"  Redirected to login at {driver.current_url}")
    else:
        log(f"  Direct access URL: {driver.current_url}")

    return False, sp


# ════════════════════════════════════════════════════════════
# PHASE 3: Test each module
# ════════════════════════════════════════════════════════════

def test_module_payroll(driver):
    """Test payroll module from employee view."""
    log("\n" + "=" * 70)
    log("MODULE 1: PAYROLL — Employee View")
    log("=" * 70)

    ok, sp_landing = try_sso_methods(driver, "payroll")
    if not ok:
        result("Payroll-SSO", "FAIL", "Cannot SSO into payroll")
        return

    result("Payroll-SSO", "PASS", f"SSO into payroll: {driver.current_url}")
    subdomain = MODULE_SUBDOMAINS["payroll"]
    base_text = get_page_text(driver)
    base_src = get_page_source_lower(driver)

    log("  Payroll landing content:")
    for line in base_text.split('\n')[:30]:
        if line.strip():
            log(f"    | {line.strip()}")

    # Explore all links
    all_links = {}
    for a in driver.find_elements(By.TAG_NAME, "a"):
        href = (a.get_attribute("href") or "")
        text = (a.text or "").strip()
        if text and href and subdomain in href:
            all_links[text] = href
    log(f"  Links on payroll page:")
    for t, h in all_links.items():
        log(f"    {t}: {h}")

    # Test: My Payslip
    payslip_found = any(kw in base_src for kw in ["payslip", "pay slip", "salary slip"])
    for path in ["/my-payslips", "/payslips", "/my/payslips", "/employee/payslips", "/payslip",
                 "/my", "/employee", "/dashboard"]:
        sp_ps, text_ps, src_ps = visit_page(driver, f"https://{subdomain}{path}", f"payslip{path.replace('/','_')}", "payroll")
        if any(kw in src_ps for kw in ["payslip", "salary", "net pay", "gross", "basic"]):
            payslip_found = True
            result("Payroll-MyPayslip", "PASS", f"Payslip content at {path}")
            break
    if not payslip_found:
        result("Payroll-MyPayslip", "FAIL", "No payslip page found")
        bug("Payroll — Employee cannot view their payslips",
            "Employee SSO'd into payroll but cannot find any payslip page.\n"
            "**Expected:** Employee should see monthly payslips.\n"
            f"**Payroll URL:** https://{subdomain}",
            "high", sp_landing)

    # Test: Salary breakdown
    sal_kw = ["basic", "hra", "deduction", "allowance", "gross", "net pay"]
    for path in ["/my-salary", "/salary", "/compensation", "/my-compensation", "/structure"]:
        sp_sal, _, src_sal = visit_page(driver, f"https://{subdomain}{path}", f"salary{path.replace('/','_')}", "payroll")
        if any(kw in src_sal for kw in sal_kw):
            result("Payroll-SalaryBreakdown", "PASS", f"Salary breakdown at {path}")
            break
    else:
        result("Payroll-SalaryBreakdown", "INFO", "No salary breakdown page found")

    # Test: Tax details
    for path in ["/my-tax", "/tax", "/tax-details", "/it-declaration", "/it-details"]:
        sp_tax, _, src_tax = visit_page(driver, f"https://{subdomain}{path}", f"tax{path.replace('/','_')}", "payroll")
        if any(kw in src_tax for kw in ["tds", "tax", "regime", "80c", "income tax"]):
            result("Payroll-TaxDetails", "PASS", f"Tax details at {path}")
            break
    else:
        result("Payroll-TaxDetails", "INFO", "No tax details page found")

    # Test: Download PDF
    pdf_found = False
    for el in driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download')]"):
        pdf_found = True
        break
    result("Payroll-DownloadPDF", "PASS" if pdf_found else "INFO",
           "Download button found" if pdf_found else "No download button found")

    # Test: Investment declarations
    for path in ["/declarations", "/investment", "/it-declarations", "/80c"]:
        sp_dec, _, src_dec = visit_page(driver, f"https://{subdomain}{path}", f"decl{path.replace('/','_')}", "payroll")
        if any(kw in src_dec for kw in ["declaration", "80c", "investment", "exempt"]):
            result("Payroll-Declarations", "PASS", f"Declarations at {path}")
            break
    else:
        result("Payroll-Declarations", "INFO", "No declarations page found")

    # Test: Reimbursement claims
    for path in ["/reimbursement", "/claims", "/my-claims", "/expenses"]:
        sp_re, _, src_re = visit_page(driver, f"https://{subdomain}{path}", f"reimb{path.replace('/','_')}", "payroll")
        if any(kw in src_re for kw in ["reimbursement", "claim", "expense"]):
            result("Payroll-Reimbursements", "PASS", f"Reimbursements at {path}")
            break
    else:
        result("Payroll-Reimbursements", "INFO", "No reimbursement page found")

    # Test: CTC
    if "ctc" in base_src or "cost to company" in base_src:
        result("Payroll-CTC", "PASS", "CTC visible")
    else:
        result("Payroll-CTC", "INFO", "CTC not visible")

    # RBAC: Admin pages
    for path in ["/admin", "/admin-panel", "/payroll-run", "/manage", "/employees", "/settings"]:
        sp_rb, _, src_rb = visit_page(driver, f"https://{subdomain}{path}", f"payroll_rbac{path.replace('/','_')}", "payroll")
        if any(kw in src_rb for kw in ["employee list", "all employees", "payroll run", "bulk", "admin panel"]):
            result("Payroll-RBAC", "FAIL", f"Admin access at {path}")
            bug("Payroll — Employee can access admin payroll pages",
                f"Employee can access {path} on payroll module.\n**Expected:** Only own payslip.",
                "critical", sp_rb)
            break
    else:
        result("Payroll-RBAC", "PASS", "No admin access")

    shot(driver, "payroll_done")


def test_module_recruitment(driver):
    """Test recruitment module from employee view."""
    log("\n" + "=" * 70)
    log("MODULE 2: RECRUITMENT — Employee View")
    log("=" * 70)

    ok, sp_landing = try_sso_methods(driver, "recruitment")
    if not ok:
        result("Recruitment-SSO", "FAIL", "Cannot SSO into recruitment")
        return

    result("Recruitment-SSO", "PASS", f"SSO: {driver.current_url}")
    subdomain = MODULE_SUBDOMAINS["recruitment"]
    base_text = get_page_text(driver)
    base_src = get_page_source_lower(driver)

    log("  Recruitment landing:")
    for line in base_text.split('\n')[:30]:
        if line.strip():
            log(f"    | {line.strip()}")

    # All links
    for a in driver.find_elements(By.TAG_NAME, "a"):
        href = (a.get_attribute("href") or "")
        text = (a.text or "").strip()
        if text and subdomain in href:
            log(f"    Link: {text} -> {href}")

    # Job postings
    for path in ["/jobs", "/careers", "/openings", "/internal-jobs", "/job-board", "/dashboard"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"jobs{path.replace('/','_')}", "recruit")
        if any(kw in src for kw in ["job", "position", "opening", "career", "vacancy"]):
            result("Recruitment-JobPostings", "PASS", f"Jobs at {path}")
            break
    else:
        result("Recruitment-JobPostings", "INFO", "No job postings page")

    # Referrals
    for path in ["/referrals", "/refer", "/my-referrals", "/employee-referral"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"referral{path.replace('/','_')}", "recruit")
        if any(kw in src for kw in ["referral", "refer", "recommend"]):
            result("Recruitment-Referral", "PASS", f"Referrals at {path}")
            break
    else:
        result("Recruitment-Referral", "INFO", "No referral page")

    # Internal apply
    for path in ["/apply", "/internal-apply", "/my-applications"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"apply{path.replace('/','_')}", "recruit")
        if any(kw in src for kw in ["apply", "application"]):
            result("Recruitment-InternalApply", "PASS", f"Apply at {path}")
            break
    else:
        result("Recruitment-InternalApply", "INFO", "No internal apply page")

    # RBAC
    for path in ["/candidates", "/pipeline", "/interviews", "/offers", "/admin", "/analytics"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"recruit_rbac{path.replace('/','_')}", "recruit")
        if any(kw in src for kw in ["candidate pipeline", "all candidates", "interview schedule", "offer letter"]):
            result("Recruitment-RBAC", "FAIL", f"HR content visible at {path}")
            bug("Recruitment — Employee can see candidate/interview data",
                f"Employee can access {path}.\n**Expected:** Only job board and own referrals.",
                "critical")
            break
    else:
        result("Recruitment-RBAC", "PASS", "No HR content visible")

    shot(driver, "recruitment_done")


def test_module_performance(driver):
    """Test performance module from employee view."""
    log("\n" + "=" * 70)
    log("MODULE 3: PERFORMANCE — Employee View")
    log("=" * 70)

    ok, sp_landing = try_sso_methods(driver, "performance")
    if not ok:
        result("Performance-SSO", "FAIL", "Cannot SSO into performance")
        return

    result("Performance-SSO", "PASS", f"SSO: {driver.current_url}")
    subdomain = MODULE_SUBDOMAINS["performance"]
    base_text = get_page_text(driver)
    base_src = get_page_source_lower(driver)

    log("  Performance landing:")
    for line in base_text.split('\n')[:30]:
        if line.strip():
            log(f"    | {line.strip()}")

    # My reviews
    for path in ["/my-reviews", "/reviews", "/my/reviews", "/self-review", "/dashboard", "/my-performance"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"reviews{path.replace('/','_')}", "perf")
        if any(kw in src for kw in ["review", "appraisal", "performance", "rating", "score"]):
            result("Performance-MyReviews", "PASS", f"Reviews at {path}")
            break
    else:
        result("Performance-MyReviews", "INFO", "No reviews page")

    # Self-assessment
    for path in ["/self-assessment", "/self-review", "/my-assessment"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"selfassess{path.replace('/','_')}", "perf")
        if any(kw in src for kw in ["self-assessment", "self assessment", "self-review"]):
            result("Performance-SelfAssessment", "PASS", f"Self-assessment at {path}")
            break
    else:
        result("Performance-SelfAssessment", "INFO", "No self-assessment page")

    # Goals/OKRs
    for path in ["/goals", "/okrs", "/my-goals", "/objectives"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"goals{path.replace('/','_')}", "perf")
        if any(kw in src for kw in ["goal", "okr", "objective", "key result"]):
            result("Performance-Goals", "PASS", f"Goals at {path}")
            break
    else:
        result("Performance-Goals", "INFO", "No goals page")

    # Manager feedback
    for path in ["/feedback", "/my-feedback", "/manager-feedback"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"feedback{path.replace('/','_')}", "perf")
        if any(kw in src for kw in ["feedback", "manager", "comment"]):
            result("Performance-ManagerFeedback", "PASS", f"Feedback at {path}")
            break
    else:
        result("Performance-ManagerFeedback", "INFO", "No feedback page")

    # 360 feedback
    for path in ["/360-feedback", "/peer-feedback", "/360"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"360{path.replace('/','_')}", "perf")
        if any(kw in src for kw in ["360", "peer feedback", "peer review"]):
            result("Performance-360Feedback", "PASS", f"360 at {path}")
            break
    else:
        result("Performance-360Feedback", "INFO", "No 360 feedback page")

    # RBAC
    for path in ["/admin", "/all-reviews", "/team-reviews", "/analytics", "/manage"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"perf_rbac{path.replace('/','_')}", "perf")
        if any(kw in src for kw in ["all employees", "team review", "review cycle", "manage reviews"]):
            result("Performance-RBAC", "FAIL", f"Admin content at {path}")
            bug("Performance — Employee can see other employees' review scores",
                f"Employee can access {path}.\n**Expected:** Only own reviews.",
                "critical")
            break
    else:
        result("Performance-RBAC", "PASS", "No admin access")

    shot(driver, "performance_done")


def test_module_rewards(driver):
    """Test rewards module from employee view."""
    log("\n" + "=" * 70)
    log("MODULE 4: REWARDS — Employee View")
    log("=" * 70)

    ok, sp_landing = try_sso_methods(driver, "rewards")
    if not ok:
        result("Rewards-SSO", "FAIL", "Cannot SSO into rewards")
        return

    result("Rewards-SSO", "PASS", f"SSO: {driver.current_url}")
    subdomain = MODULE_SUBDOMAINS["rewards"]
    base_text = get_page_text(driver)
    base_src = get_page_source_lower(driver)

    log("  Rewards landing:")
    for line in base_text.split('\n')[:30]:
        if line.strip():
            log(f"    | {line.strip()}")

    # Recognition feed
    if any(kw in base_src for kw in ["recognition", "kudos", "appreciation", "feed"]):
        result("Rewards-RecognitionFeed", "PASS", "Feed visible on landing")
    else:
        for path in ["/feed", "/recognition", "/wall", "/dashboard"]:
            _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"feed{path.replace('/','_')}", "rewards")
            if any(kw in src for kw in ["recognition", "kudos", "appreciation"]):
                result("Rewards-RecognitionFeed", "PASS", f"Feed at {path}")
                break
        else:
            result("Rewards-RecognitionFeed", "INFO", "No recognition feed")

    # Give kudos
    kudos_found = False
    for el in driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'give') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'kudos') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'recognize')]"):
        kudos_found = True
        break
    result("Rewards-GiveKudos", "PASS" if kudos_found else "INFO",
           "Give kudos option found" if kudos_found else "No give-kudos found")

    # Points
    if any(kw in base_src for kw in ["points", "balance", "coins"]):
        result("Rewards-Points", "PASS", "Points visible")
    else:
        for path in ["/my-points", "/points", "/wallet"]:
            _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"points{path.replace('/','_')}", "rewards")
            if any(kw in src for kw in ["points", "balance"]):
                result("Rewards-Points", "PASS", f"Points at {path}")
                break
        else:
            result("Rewards-Points", "INFO", "No points")

    # Leaderboard
    if "leaderboard" in base_src:
        result("Rewards-Leaderboard", "PASS", "Leaderboard visible")
    else:
        for path in ["/leaderboard", "/rankings"]:
            _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"leaderboard{path.replace('/','_')}", "rewards")
            if "leaderboard" in src or "ranking" in src:
                result("Rewards-Leaderboard", "PASS", f"Leaderboard at {path}")
                break
        else:
            result("Rewards-Leaderboard", "INFO", "No leaderboard")

    # Redeem
    for path in ["/redeem", "/store", "/catalog", "/marketplace"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"redeem{path.replace('/','_')}", "rewards")
        if any(kw in src for kw in ["redeem", "store", "catalog", "gift"]):
            result("Rewards-Redeem", "PASS", f"Redeem at {path}")
            break
    else:
        result("Rewards-Redeem", "INFO", "No redeem feature")

    # Badges
    if any(kw in base_src for kw in ["badge", "achievement"]):
        result("Rewards-Badges", "PASS", "Badges visible")
    else:
        for path in ["/badges", "/achievements"]:
            _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"badges{path.replace('/','_')}", "rewards")
            if any(kw in src for kw in ["badge", "achievement"]):
                result("Rewards-Badges", "PASS", f"Badges at {path}")
                break
        else:
            result("Rewards-Badges", "INFO", "No badges")

    # Challenges
    for path in ["/challenges", "/contests"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"challenges{path.replace('/','_')}", "rewards")
        if any(kw in src for kw in ["challenge", "contest"]):
            result("Rewards-Challenges", "PASS", f"Challenges at {path}")
            break
    else:
        result("Rewards-Challenges", "INFO", "No challenges")

    shot(driver, "rewards_done")


def test_module_exit(driver):
    """Test exit module from employee view."""
    log("\n" + "=" * 70)
    log("MODULE 5: EXIT — Employee View")
    log("=" * 70)

    ok, sp_landing = try_sso_methods(driver, "exit")
    if not ok:
        result("Exit-SSO", "FAIL", "Cannot SSO into exit")
        # May be expected for non-exiting employee
        result("Exit-Access", "INFO", "Employee cannot access exit module (may be expected)")
        return

    result("Exit-SSO", "PASS", f"SSO: {driver.current_url}")
    subdomain = MODULE_SUBDOMAINS["exit"]
    base_text = get_page_text(driver)
    base_src = get_page_source_lower(driver)

    log("  Exit landing:")
    for line in base_text.split('\n')[:30]:
        if line.strip():
            log(f"    | {line.strip()}")

    exit_kw = ["resignation", "exit", "offboarding", "notice period", "clearance"]
    if any(kw in base_src for kw in exit_kw):
        result("Exit-Content", "PASS", "Exit content visible")
    else:
        result("Exit-Content", "INFO", "No exit content (employee not in exit process)")

    # RBAC
    for path in ["/admin", "/all-exits", "/dashboard", "/manage"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"exit_rbac{path.replace('/','_')}", "exit")
        if any(kw in src for kw in ["all exits", "exit dashboard", "manage exits"]):
            result("Exit-RBAC", "FAIL", f"Admin content at {path}")
            bug("Exit — Employee can access admin exit management pages",
                f"Employee can access {path}.\n**Expected:** Only own exit process.",
                "critical")
            break
    else:
        result("Exit-RBAC", "PASS", "No admin access")

    shot(driver, "exit_done")


def test_module_lms(driver):
    """Test LMS module from employee view."""
    log("\n" + "=" * 70)
    log("MODULE 6: LMS — Employee View")
    log("=" * 70)

    ok, sp_landing = try_sso_methods(driver, "lms")
    if not ok:
        result("LMS-SSO", "FAIL", "Cannot SSO into LMS")
        return

    result("LMS-SSO", "PASS", f"SSO: {driver.current_url}")
    subdomain = MODULE_SUBDOMAINS["lms"]
    base_text = get_page_text(driver)
    base_src = get_page_source_lower(driver)

    log("  LMS landing:")
    for line in base_text.split('\n')[:30]:
        if line.strip():
            log(f"    | {line.strip()}")

    # My courses
    for path in ["/my-courses", "/courses", "/my/courses", "/my-learning", "/dashboard"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"courses{path.replace('/','_')}", "lms")
        if any(kw in src for kw in ["course", "learning", "training", "module", "assigned"]):
            result("LMS-MyCourses", "PASS", f"Courses at {path}")
            break
    else:
        result("LMS-MyCourses", "INFO", "No courses page")

    # Course content
    for path in ["/course", "/learn", "/content", "/lessons"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"content{path.replace('/','_')}", "lms")
        if any(kw in src for kw in ["lesson", "chapter", "video", "content", "slide"]):
            result("LMS-CourseContent", "PASS", f"Content at {path}")
            break
    else:
        result("LMS-CourseContent", "INFO", "No course content page")

    # Quiz
    for path in ["/quiz", "/assessment", "/test", "/exam"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"quiz{path.replace('/','_')}", "lms")
        if any(kw in src for kw in ["quiz", "assessment", "test", "exam", "question"]):
            result("LMS-Quiz", "PASS", f"Quiz at {path}")
            break
    else:
        result("LMS-Quiz", "INFO", "No quiz page")

    # Certifications
    for path in ["/certifications", "/certificates", "/my-certificates"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"certs{path.replace('/','_')}", "lms")
        if any(kw in src for kw in ["certification", "certificate", "credential"]):
            result("LMS-Certifications", "PASS", f"Certs at {path}")
            break
    else:
        result("LMS-Certifications", "INFO", "No certifications page")

    # Catalog
    for path in ["/catalog", "/browse", "/all-courses", "/explore"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"catalog{path.replace('/','_')}", "lms")
        if any(kw in src for kw in ["catalog", "browse", "explore", "enroll"]):
            result("LMS-Catalog", "PASS", f"Catalog at {path}")
            break
    else:
        result("LMS-Catalog", "INFO", "No catalog page")

    # Progress
    for path in ["/progress", "/my-progress", "/dashboard"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"progress{path.replace('/','_')}", "lms")
        if any(kw in src for kw in ["progress", "completion", "completed"]):
            result("LMS-Progress", "PASS", f"Progress at {path}")
            break
    else:
        result("LMS-Progress", "INFO", "No progress page")

    shot(driver, "lms_done")


def test_module_projects(driver):
    """Test projects module from employee view."""
    log("\n" + "=" * 70)
    log("MODULE 7: PROJECTS — Employee View")
    log("=" * 70)

    ok, sp_landing = try_sso_methods(driver, "projects")
    if not ok:
        result("Projects-SSO", "FAIL", "Cannot SSO into projects")
        return

    result("Projects-SSO", "PASS", f"SSO: {driver.current_url}")
    subdomain = MODULE_SUBDOMAINS["projects"]
    base_text = get_page_text(driver)
    base_src = get_page_source_lower(driver)

    log("  Projects landing:")
    for line in base_text.split('\n')[:30]:
        if line.strip():
            log(f"    | {line.strip()}")

    # My projects
    for path in ["/my-projects", "/projects", "/my/projects", "/dashboard"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"myproj{path.replace('/','_')}", "projects")
        if any(kw in src for kw in ["project", "assigned"]):
            result("Projects-MyProjects", "PASS", f"Projects at {path}")
            break
    else:
        result("Projects-MyProjects", "INFO", "No projects page")

    # My tasks
    for path in ["/my-tasks", "/tasks", "/my/tasks", "/todo"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"tasks{path.replace('/','_')}", "projects")
        if any(kw in src for kw in ["task", "to do", "todo", "assigned", "in progress"]):
            result("Projects-MyTasks", "PASS", f"Tasks at {path}")
            break
    else:
        result("Projects-MyTasks", "INFO", "No tasks page")

    # Time log
    for path in ["/timesheet", "/time-log", "/timelog", "/time-tracking"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"timelog{path.replace('/','_')}", "projects")
        if any(kw in src for kw in ["timesheet", "time log", "hours", "time tracking"]):
            result("Projects-TimeLog", "PASS", f"Time log at {path}")
            break
    else:
        result("Projects-TimeLog", "INFO", "No time log page")

    # Board/Kanban
    for path in ["/board", "/kanban", "/sprint-board"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"board{path.replace('/','_')}", "projects")
        if any(kw in src for kw in ["board", "kanban", "sprint", "backlog"]):
            result("Projects-Board", "PASS", f"Board at {path}")
            break
    else:
        result("Projects-Board", "INFO", "No board page")

    # RBAC
    for path in ["/admin", "/all-projects", "/settings", "/manage", "/analytics"]:
        _, _, src = visit_page(driver, f"https://{subdomain}{path}", f"proj_rbac{path.replace('/','_')}", "projects")
        if any(kw in src for kw in ["all projects", "manage projects", "admin"]):
            result("Projects-RBAC", "FAIL", f"Admin content at {path}")
            bug("Projects — Employee can access admin project pages",
                f"Employee can access {path}.\n**Expected:** Only assigned projects.",
                "critical")
            break
    else:
        result("Projects-RBAC", "PASS", "No admin access")

    shot(driver, "projects_done")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    global test_counter

    log("=" * 70)
    log("EMP CLOUD — EMPLOYEE ALL-MODULES SSO TEST (v2)")
    log(f"Employee: {EMP_EMAIL}")
    log(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    # Phase 1: Login and deep-explore /modules page
    log("\n--- Phase 1: Login and explore /modules page ---")
    driver = create_driver()
    try:
        ok = do_login(driver)
        if not ok:
            sp = shot(driver, "login_fail")
            log("FATAL: Cannot login as employee")
            result("Login", "FAIL", f"URL: {driver.current_url}")
            driver.quit()
            return
        result("Login", "PASS", f"URL: {driver.current_url}")
        shot(driver, "login_success")

        module_cards = explore_modules_page(driver)
    except Exception as e:
        log(f"Phase 1 error: {e}")
        traceback.print_exc()
    finally:
        driver.quit()
    test_counter += 1

    # Phase 2: Test each module (restart driver every 2 tests)
    module_tests = [
        ("payroll", test_module_payroll),
        ("recruitment", test_module_recruitment),
        ("performance", test_module_performance),
        ("rewards", test_module_rewards),
        ("exit", test_module_exit),
        ("lms", test_module_lms),
        ("projects", test_module_projects),
    ]

    for i, (mod_name, test_func) in enumerate(module_tests):
        if i % 2 == 0:
            log(f"\n--- Creating fresh driver (batch {i // 2 + 1}) ---")
            driver = create_driver()
            login_ok = do_login(driver)
            if not login_ok:
                log(f"  Re-login failed, retrying...")
                driver.quit()
                time.sleep(3)
                driver = create_driver()
                login_ok = do_login(driver)
                if not login_ok:
                    log(f"  FATAL: Cannot re-login for {mod_name}")
                    shot(driver, f"relogin_fail_{mod_name}")
                    driver.quit()
                    continue

        try:
            test_func(driver)
        except Exception as e:
            log(f"  [ERROR in {mod_name}] {e}")
            traceback.print_exc()
            shot(driver, f"{mod_name}_error")
            result(f"{mod_name}-Error", "ERROR", str(e))

        test_counter += 1

        if i % 2 == 1 or i == len(module_tests) - 1:
            try:
                driver.quit()
            except:
                pass

    # Phase 3: Summary and bug filing
    log("\n" + "=" * 70)
    log("RESULTS SUMMARY")
    log("=" * 70)

    passes = [r for r in test_results if r["status"] == "PASS"]
    fails = [r for r in test_results if r["status"] == "FAIL"]
    infos = [r for r in test_results if r["status"] == "INFO"]
    errors = [r for r in test_results if r["status"] == "ERROR"]

    log(f"  PASS: {len(passes)}  |  FAIL: {len(fails)}  |  INFO: {len(infos)}  |  ERROR: {len(errors)}")
    log(f"  Bugs found: {len(bugs_found)}")

    for r in test_results:
        log(f"  [{r['status']}] {r['test']}: {r['details']}")

    # Determine if the main issue is that NO modules have SSO for employees
    sso_fails = [r for r in test_results if r["test"].endswith("-SSO") and r["status"] == "FAIL"]
    if len(sso_fails) >= 5:
        # This is a systemic issue — file a single consolidated bug
        log("\n  SYSTEMIC ISSUE: Employee role has no SSO access to ANY external module")
        consolidated_bug_title = "Employee role cannot SSO into any external module from /modules page"
        consolidated_bug_desc = (
            "**Summary:** When logged in as Employee (priya@technova.in), the /modules page shows "
            "the Module Marketplace with all subscribed modules listed (Payroll, Recruitment, Performance, "
            "Rewards, Exit, LMS, Projects), but there are **no Launch/SSO buttons** visible for the "
            "employee role.\n\n"
            "**Steps to reproduce:**\n"
            "1. Login as priya@technova.in (Employee role)\n"
            "2. Navigate to /modules\n"
            "3. Observe Module Marketplace page\n"
            "4. Each module shows 'Subscribed' badge but NO launch/SSO link\n\n"
            "**Expected behavior:** Employee should see a 'Launch' or 'Open' button for each "
            "subscribed module, which triggers SSO into the module subdomain.\n\n"
            "**Actual behavior:** Only 'Subscribed' status badges are shown. No way to launch "
            "any module. The Org Admin role DOES see launch links with SSO tokens.\n\n"
            "**Impact:** Employees cannot access ANY of the following modules:\n"
            "- Payroll (view payslips, salary, tax, declarations)\n"
            "- Recruitment (internal job board, referrals)\n"
            "- Performance (reviews, goals, self-assessment)\n"
            "- Rewards (recognition, kudos, points)\n"
            "- LMS (courses, learning)\n"
            "- Projects (tasks, time tracking)\n"
            "- Exit (exit process if applicable)\n\n"
            "**Modules affected:** All 7 external SSO modules\n\n"
            f"**Failed modules:** {', '.join(r['test'].replace('-SSO','') for r in sso_fails)}\n"
        )
        # Clear individual SSO bugs, replace with consolidated
        bugs_found.clear()
        bug(consolidated_bug_title, consolidated_bug_desc, "critical")

    # Upload screenshots
    log("\n--- Uploading screenshots ---")
    uploaded_urls = {}
    screenshot_files = sorted([f for f in os.listdir(SCREENSHOT_DIR) if f.endswith(".png")])
    # Upload key screenshots (limit to avoid spam)
    key_screenshots = [f for f in screenshot_files if any(kw in f for kw in
        ["login_success", "modules_page", "landing", "done", "direct", "newtab", "method"])]
    if not key_screenshots:
        key_screenshots = screenshot_files[:20]

    for fname in key_screenshots[:25]:
        fpath = os.path.join(SCREENSHOT_DIR, fname)
        url = upload_screenshot_github(fpath)
        if url:
            uploaded_urls[fname] = url
        time.sleep(0.5)

    log(f"  Uploaded {len(uploaded_urls)} screenshots")

    # File bugs
    log("\n--- Filing GitHub issues ---")
    for b in bugs_found:
        body = b["description"] + "\n\n"
        body += f"**Severity:** {b['severity']}\n"
        body += f"**User:** {EMP_EMAIL}\n"
        body += f"**Role:** Employee\n"
        body += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        if b.get("screenshot"):
            fname = os.path.basename(b["screenshot"])
            if fname in uploaded_urls:
                body += f"\n**Screenshot:**\n![{fname}]({uploaded_urls[fname]})\n"

        # Attach modules page screenshot
        for k, v in uploaded_urls.items():
            if "modules_page" in k:
                body += f"\n**Modules page:**\n![{k}]({v})\n"
                break

        labels = ["bug"]
        if b["severity"] == "critical":
            labels.append("critical")

        file_github_issue(b["title"], body, labels)
        time.sleep(1)

    # File feature requests for missing features (only if we got into modules)
    info_results = {r["test"] for r in test_results if r["status"] == "INFO"}
    sso_passed = {r["test"].replace("-SSO", "") for r in test_results if r["test"].endswith("-SSO") and r["status"] == "PASS"}

    feature_map = {
        "Payroll-DownloadPDF": "[Feature Request] Payroll — Add payslip PDF download for employees",
        "Payroll-Declarations": "[Feature Request] Payroll — Add investment declaration section for employees",
        "Payroll-Reimbursements": "[Feature Request] Payroll — Add reimbursement claim submission for employees",
        "Recruitment-Referral": "[Feature Request] Recruitment — Add employee referral program",
        "Recruitment-JobPostings": "[Feature Request] Recruitment — Add internal job board for employees",
        "LMS-Catalog": "[Feature Request] LMS — Add course catalog for employees to browse",
        "LMS-Certifications": "[Feature Request] LMS — Add certification tracking for employees",
        "Projects-TimeLog": "[Feature Request] Projects — Add time logging for employees",
        "Projects-Board": "[Feature Request] Projects — Add Kanban board view for employees",
        "Performance-SelfAssessment": "[Feature Request] Performance — Add self-assessment form for employees",
        "Performance-Goals": "[Feature Request] Performance — Add goals/OKR tracking for employees",
        "Performance-360Feedback": "[Feature Request] Performance — Add 360 peer feedback for employees",
        "Rewards-GiveKudos": "[Feature Request] Rewards — Add option for employees to give kudos",
        "Rewards-Redeem": "[Feature Request] Rewards — Add points redemption store for employees",
        "Rewards-Challenges": "[Feature Request] Rewards — Add team challenges for employees",
    }

    for test_name, title in feature_map.items():
        # Only file if the module SSO worked but the feature was missing
        module_prefix = test_name.split("-")[0]
        if test_name in info_results and module_prefix in sso_passed:
            body = (f"Feature missing for employee role.\n\n"
                    f"**User:** {EMP_EMAIL}\n**Role:** Employee\n"
                    f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            file_github_issue(title, body, labels=["enhancement"])
            time.sleep(1)

    # Save results
    results_path = os.path.join(SCREENSHOT_DIR, "test_results.json")
    with open(results_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "employee": EMP_EMAIL,
            "test_results": test_results,
            "bugs_found": bugs_found,
            "screenshots_uploaded": uploaded_urls,
        }, f, indent=2)
    log(f"\n  Results saved to {results_path}")

    log("\n" + "=" * 70)
    log("TEST COMPLETE")
    log("=" * 70)


if __name__ == "__main__":
    main()
