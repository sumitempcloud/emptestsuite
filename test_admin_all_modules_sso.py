#!/usr/bin/env python3
"""
EMP Cloud HRMS — Full SSO Module Workflow Testing (All 7 Modules)
Login at dashboard, navigate to /modules, SSO into each external module, test every page.
Restart driver every 2 modules to avoid crashes.
"""

import sys, os, time, json, traceback, base64, requests, re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────
BASE = "https://test-empcloud.empcloud.com"
SSDIR = r"C:\emptesting\screenshots\admin_all_modules"
GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
os.makedirs(SSDIR, exist_ok=True)

results = []
bugs = []
feature_requests = []
screenshots_taken = []
module_count = 0
driver = None
DRIVER_PATH = None

def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def log(m):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)

# ── Driver management ──────────────────────────────────────────
def create_driver():
    global driver, DRIVER_PATH
    if driver:
        try: driver.quit()
        except: pass
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage",
              "--window-size=1920,1080","--disable-gpu","--disable-extensions",
              "--ignore-certificate-errors","--disable-blink-features=AutomationControlled"]:
        opts.add_argument(a)
    if not DRIVER_PATH:
        DRIVER_PATH = ChromeDriverManager().install()
    svc = Service(DRIVER_PATH)
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.set_page_load_timeout(45)
    driver.implicitly_wait(2)
    log("Driver created/restarted.")
    return driver

def restart_if_needed():
    """Restart driver every 2 modules."""
    global module_count
    module_count += 1
    if module_count > 1 and module_count % 2 == 0:
        log(f"=== Restarting driver after {module_count} modules ===")
        create_driver()
        login()
        return True
    return False

def safe_click(el):
    try:
        el.click()
    except:
        driver.execute_script("arguments[0].click();", el)

def ss(name):
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:80]
    p = os.path.join(SSDIR, f"{safe}_{ts()}.png")
    try:
        driver.save_screenshot(p)
        screenshots_taken.append(p)
        return p
    except:
        return None

def add_result(module, page, status, detail="", ssp=None):
    results.append({"module": module, "page": page, "status": status, "detail": detail, "ss": ssp})
    icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "WARN"
    log(f"  [{icon}] {module} > {page}: {detail[:120]}")

def add_bug(title, desc, ssp=None):
    bugs.append({"title": title, "desc": desc, "ss": ssp})
    log(f"  [BUG] {title}")

def add_feature(title, desc, ssp=None):
    feature_requests.append({"title": title, "desc": desc, "ss": ssp})
    log(f"  [FEATURE] {title}")

def wait_for(css, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css))
        )
    except:
        return None

def wait_visible(css, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css))
        )
    except:
        return None

def find_els(css):
    try:
        return driver.find_elements(By.CSS_SELECTOR, css)
    except:
        return []

def find_el(css):
    try:
        return driver.find_element(By.CSS_SELECTOR, css)
    except:
        return None

def page_text():
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""

def page_has(*keywords):
    """Check if page contains any of the keywords (case-insensitive)."""
    text = page_text().lower()
    return any(kw.lower() in text for kw in keywords)

def check_page_loaded(module_name, page_name, expected_keywords=None, url_contains=None):
    """Generic page load checker. Returns True if page looks good."""
    time.sleep(2)
    ssp = ss(f"{module_name}_{page_name}")
    cur = driver.current_url
    text = page_text()

    # Check for error pages
    if any(err in text.lower() for err in ["404", "not found", "500", "server error", "something went wrong"]):
        if "404" in text.lower() or "not found" in text.lower():
            add_result(module_name, page_name, "FAIL", f"Page shows 404/Not Found at {cur}", ssp)
            add_bug(f"{module_name} \u2014 {page_name} page returns 404",
                    f"**URL:** {cur}\n**Steps:** Navigate to {page_name}\n**Expected:** Page loads with content\n**Actual:** 404 Not Found error", ssp)
            return False
        if "500" in text.lower() or "server error" in text.lower():
            add_result(module_name, page_name, "FAIL", f"Server error at {cur}", ssp)
            add_bug(f"{module_name} \u2014 {page_name} page shows server error",
                    f"**URL:** {cur}\n**Steps:** Navigate to {page_name}\n**Expected:** Page loads normally\n**Actual:** 500/Server error", ssp)
            return False

    # Check URL if specified
    if url_contains and url_contains not in cur:
        add_result(module_name, page_name, "WARN", f"URL mismatch: expected '{url_contains}' in {cur}", ssp)

    # Check keywords
    if expected_keywords:
        found = [kw for kw in expected_keywords if kw.lower() in text.lower()]
        missing = [kw for kw in expected_keywords if kw.lower() not in text.lower()]
        if found:
            add_result(module_name, page_name, "PASS", f"Found: {', '.join(found[:5])}", ssp)
            return True
        else:
            add_result(module_name, page_name, "WARN", f"No expected keywords found. Missing: {', '.join(missing[:5])}", ssp)
            return False
    else:
        # Just check it's not blank
        if len(text.strip()) > 50:
            add_result(module_name, page_name, "PASS", f"Page loaded ({len(text)} chars)", ssp)
            return True
        else:
            add_result(module_name, page_name, "WARN", f"Page appears mostly empty ({len(text)} chars)", ssp)
            return False

# ── Login ──────────────────────────────────────────────────────
def login():
    log(f"Logging in as {ADMIN_EMAIL}...")
    driver.get(f"{BASE}/login")
    try:
        wait = WebDriverWait(driver, 15)
        em = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='email']")))
        em.clear(); em.send_keys(ADMIN_EMAIL)
        pw = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        pw.clear(); pw.send_keys(ADMIN_PASS)
        time.sleep(0.3)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(driver, 15).until(lambda d: "/login" not in d.current_url)
        time.sleep(3)
        log(f"  Logged in -> {driver.current_url}")
        ss("01_login_success")
        return True
    except Exception as e:
        log(f"  Login FAILED: {e}")
        ss("01_login_fail")
        return False

# ── SSO Navigation ─────────────────────────────────────────────
def navigate_to_modules_page():
    """Go to /modules page on the dashboard."""
    log("Navigating to /modules page...")
    driver.get(f"{BASE}/modules")
    time.sleep(3)
    ssp = ss("02_modules_page")
    text = page_text()
    if "module" in text.lower() or "payroll" in text.lower() or "recruit" in text.lower():
        log(f"  Modules page loaded: {driver.current_url}")
        return True
    log(f"  Modules page may not have loaded properly: {driver.current_url}")
    return True  # Continue anyway

def sso_into_module(module_name, target_domain):
    """
    From the /modules page, click the module card/link to SSO into the external module.
    Returns True if we land on the target domain.
    """
    log(f"SSO into {module_name} ({target_domain})...")
    driver.get(f"{BASE}/modules")
    time.sleep(3)

    # Try to find and click the module card/link
    # Look for links containing the module name or targeting the domain
    clicked = False

    # Strategy 1: Find a link/button with the module name text
    try:
        links = driver.find_elements(By.XPATH,
            f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{module_name.lower()}')] | "
            f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{module_name.lower()}')] | "
            f"//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{module_name.lower()}')]//a | "
            f"//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{module_name.lower()}')]//button"
        )
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            if target_domain in href or "launch" in text.lower() or "open" in text.lower() or module_name.lower() in text.lower():
                log(f"  Found link: '{text}' -> {href}")
                safe_click(link)
                clicked = True
                break
    except:
        pass

    # Strategy 2: Find any link pointing to the target domain
    if not clicked:
        try:
            domain_links = driver.find_elements(By.CSS_SELECTOR, f"a[href*='{target_domain}']")
            if domain_links:
                safe_click(domain_links[0])
                clicked = True
                log(f"  Clicked domain link to {target_domain}")
        except:
            pass

    # Strategy 3: Look for "Launch" buttons near the module name
    if not clicked:
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='module'], [class*='Card'], [class*='Module']")
            for card in cards:
                if module_name.lower() in card.text.lower():
                    btns = card.find_elements(By.TAG_NAME, "button") + card.find_elements(By.TAG_NAME, "a")
                    for btn in btns:
                        if any(w in btn.text.lower() for w in ["launch", "open", "go", "visit", "manage"]):
                            safe_click(btn)
                            clicked = True
                            log(f"  Clicked '{btn.text}' in {module_name} card")
                            break
                    if not clicked and btns:
                        safe_click(btns[0])
                        clicked = True
                        log(f"  Clicked first button in {module_name} card")
                    break
        except:
            pass

    if not clicked:
        log(f"  Could not find SSO link for {module_name}, trying direct URL with token...")
        # Fallback: navigate directly but try to carry auth
        # First get token from localStorage
        try:
            token = driver.execute_script("return localStorage.getItem('token') || localStorage.getItem('authToken') || localStorage.getItem('access_token') || ''")
            if token:
                driver.get(f"https://{target_domain}/auth/sso?token={token}")
            else:
                driver.get(f"https://{target_domain}")
        except:
            driver.get(f"https://{target_domain}")

    time.sleep(5)

    # Handle new tabs - switch to the newest tab
    handles = driver.window_handles
    if len(handles) > 1:
        driver.switch_to.window(handles[-1])
        log(f"  Switched to new tab: {driver.current_url}")

    cur = driver.current_url
    ssp = ss(f"sso_{module_name}")

    # Check if we're on the target domain or got redirected to login
    if target_domain in cur:
        if "/login" in cur:
            log(f"  SSO landed on login page of {target_domain} - trying login there")
            try:
                em = wait_visible("input[name='email']", 5)
                if em:
                    em.clear(); em.send_keys(ADMIN_EMAIL)
                    pw = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
                    pw.clear(); pw.send_keys(ADMIN_PASS)
                    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                    time.sleep(5)
            except:
                pass
        log(f"  SSO success: {driver.current_url}")
        return True
    elif "/login" in cur:
        log(f"  Got redirected to main login - SSO may have failed")
        add_bug(f"{module_name} \u2014 SSO from modules page redirects to login instead of module",
                f"**URL:** {BASE}/modules\n**Steps:** Click {module_name} module card\n**Expected:** SSO redirects to {target_domain}\n**Actual:** Redirected to login page at {cur}", ssp)
        # Try direct navigation
        driver.get(f"https://{target_domain}")
        time.sleep(5)
        return target_domain in driver.current_url
    else:
        log(f"  Unexpected URL after SSO: {cur}")
        return True  # Continue testing anyway


def close_extra_tabs():
    """Close all tabs except the first one."""
    handles = driver.window_handles
    if len(handles) > 1:
        for h in handles[1:]:
            driver.switch_to.window(h)
            driver.close()
        driver.switch_to.window(handles[0])

def go_back_to_dashboard():
    """Return to the main dashboard."""
    close_extra_tabs()
    driver.get(BASE)
    time.sleep(2)

# ── Module navigation helpers ──────────────────────────────────
def nav_module_page(domain, path, module_name, page_name, keywords=None):
    """Navigate to a page within a module and check it loaded."""
    url = f"https://{domain}{path}"
    try:
        driver.get(url)
        time.sleep(3)
    except TimeoutException:
        ss(f"{module_name}_{page_name}_timeout")
        add_result(module_name, page_name, "WARN", f"Page load timeout at {url}")
        return False
    return check_page_loaded(module_name, page_name, keywords)

def find_and_click_sidebar(text_match):
    """Try to click a sidebar/nav link by text."""
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "nav a, aside a, [class*='sidebar'] a, [class*='Sidebar'] a, [class*='menu'] a, [class*='Menu'] a, [role='navigation'] a")
        for link in links:
            if text_match.lower() in link.text.lower():
                safe_click(link)
                time.sleep(2)
                return True
    except:
        pass
    return False

def try_click_button(text_match):
    """Try to click a button by text content."""
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button, a.btn, [role='button'], a[class*='button'], a[class*='Button']")
        for btn in buttons:
            if text_match.lower() in btn.text.lower():
                safe_click(btn)
                time.sleep(2)
                return True
    except:
        pass
    return False

def check_form_exists(module_name, page_name):
    """Check if a form exists on the page."""
    forms = find_els("form")
    inputs = find_els("input, textarea, select")
    if forms or len(inputs) > 1:
        return True
    return False

def check_table_or_list(module_name, page_name):
    """Check if there's a table or list with data."""
    tables = find_els("table")
    lists = find_els("[class*='list'], [class*='List'], [role='list'], ul.list-group")
    cards = find_els("[class*='card'], [class*='Card']")
    if tables:
        rows = find_els("table tbody tr")
        return len(rows)
    if lists or cards:
        return len(lists) + len(cards)
    return 0

def check_download_button():
    """Check if download/export buttons exist."""
    btns = find_els("button, a")
    for btn in btns:
        txt = btn.text.lower()
        if any(w in txt for w in ["download", "export", "pdf", "csv", "print"]):
            return True
    return False


# ══════════════════════════════════════════════════════════════════
# MODULE 1: PAYROLL
# ══════════════════════════════════════════════════════════════════
def test_payroll():
    MOD = "Payroll"
    DOMAIN = "testpayroll.empcloud.com"
    log(f"\n{'='*60}\nTESTING MODULE: {MOD}\n{'='*60}")

    if not sso_into_module("Payroll", DOMAIN):
        add_result(MOD, "SSO", "FAIL", "Could not access payroll module")
        return

    # Dashboard
    nav_module_page(DOMAIN, "/", MOD, "Dashboard",
        ["dashboard", "payroll", "ctc", "net pay", "salary", "tax", "employee"])

    # Check CTC breakdown visibility
    text = page_text()
    for kw in ["ctc", "net pay", "tax regime"]:
        if kw in text.lower():
            add_result(MOD, f"Dashboard - {kw}", "PASS", f"'{kw}' visible on dashboard")
        else:
            add_result(MOD, f"Dashboard - {kw}", "WARN", f"'{kw}' not visible on dashboard")

    # My Payslips
    nav_module_page(DOMAIN, "/payslips", MOD, "My Payslips",
        ["payslip", "salary", "month", "download", "pay"])
    if not nav_module_page(DOMAIN, "/my-payslips", MOD, "My Payslips (alt)",
        ["payslip", "salary", "month", "download", "pay"]):
        pass

    # Check PDF download
    if check_download_button():
        add_result(MOD, "Payslip Download", "PASS", "Download button found")
    else:
        add_result(MOD, "Payslip Download", "WARN", "No download/PDF button found on payslips page")
        add_bug(f"Payroll \u2014 Cannot download payslip PDF",
                f"**URL:** https://{DOMAIN}/payslips\n**Steps:** Navigate to My Payslips\n**Expected:** Download/PDF button available for each payslip\n**Actual:** No download button visible",
                ss(f"{MOD}_no_download"))

    # My Salary
    nav_module_page(DOMAIN, "/salary", MOD, "My Salary",
        ["salary", "basic", "hra", "da", "component", "structure", "allowance", "deduction"])
    nav_module_page(DOMAIN, "/my-salary", MOD, "My Salary (alt)",
        ["salary", "basic", "hra", "structure"])
    nav_module_page(DOMAIN, "/salary-structure", MOD, "Salary Structure",
        ["salary", "basic", "hra", "component"])

    # My Tax
    nav_module_page(DOMAIN, "/tax", MOD, "My Tax",
        ["tax", "tds", "regime", "computation", "old", "new", "section"])
    nav_module_page(DOMAIN, "/my-tax", MOD, "My Tax (alt)",
        ["tax", "tds", "regime"])

    # Declarations
    nav_module_page(DOMAIN, "/declarations", MOD, "Declarations",
        ["declaration", "investment", "80c", "80d", "hra", "section", "proof"])
    nav_module_page(DOMAIN, "/tax-declarations", MOD, "Tax Declarations (alt)",
        ["declaration", "investment", "80c"])

    # Reimbursements
    nav_module_page(DOMAIN, "/reimbursements", MOD, "Reimbursements",
        ["reimbursement", "claim", "submit", "history", "amount", "expense"])
    # Try to check form
    text = page_text()
    if "submit" in text.lower() or "claim" in text.lower() or "new" in text.lower():
        add_result(MOD, "Reimbursement Submit", "PASS", "Submit option appears available")
    else:
        add_feature(f"[Feature Request] Payroll \u2014 No way to submit reimbursement claims",
                    f"**URL:** https://{DOMAIN}/reimbursements\n**Expected:** Button/form to submit a new reimbursement claim\n**Actual:** No submit functionality found")

    # Run Payroll (admin feature)
    nav_module_page(DOMAIN, "/run-payroll", MOD, "Run Payroll",
        ["run", "payroll", "process", "month", "employee"])
    nav_module_page(DOMAIN, "/payroll-run", MOD, "Run Payroll (alt)",
        ["run", "payroll", "process"])
    nav_module_page(DOMAIN, "/admin/payroll", MOD, "Admin Payroll",
        ["run", "payroll", "process", "salary"])

    # Payroll Reports
    nav_module_page(DOMAIN, "/reports", MOD, "Payroll Reports",
        ["report", "summary", "payroll", "month", "employee"])
    nav_module_page(DOMAIN, "/payroll-reports", MOD, "Payroll Reports (alt)",
        ["report", "summary"])

    # Employee-wise salary
    nav_module_page(DOMAIN, "/employees", MOD, "Employee Salary Details",
        ["employee", "salary", "name", "department"])
    nav_module_page(DOMAIN, "/employee-salary", MOD, "Employee Salary (alt)",
        ["employee", "salary"])

    # Settings
    nav_module_page(DOMAIN, "/settings", MOD, "Payroll Settings",
        ["setting", "config", "component", "formula", "template"])

    go_back_to_dashboard()
    log(f"Completed {MOD} testing.\n")


# ══════════════════════════════════════════════════════════════════
# MODULE 2: RECRUITMENT
# ══════════════════════════════════════════════════════════════════
def test_recruitment():
    MOD = "Recruitment"
    DOMAIN = "test-recruit.empcloud.com"
    log(f"\n{'='*60}\nTESTING MODULE: {MOD}\n{'='*60}")

    if not sso_into_module("Recruitment", DOMAIN):
        add_result(MOD, "SSO", "FAIL", "Could not access recruitment module")
        return

    # Dashboard
    nav_module_page(DOMAIN, "/", MOD, "Dashboard",
        ["dashboard", "recruitment", "job", "candidate", "pipeline", "open", "hired"])

    # Job Postings
    nav_module_page(DOMAIN, "/jobs", MOD, "Job Postings",
        ["job", "position", "title", "department", "status", "create", "add"])
    nav_module_page(DOMAIN, "/job-postings", MOD, "Job Postings (alt)",
        ["job", "position", "title"])

    # Try creating a job
    if try_click_button("create") or try_click_button("add") or try_click_button("new job"):
        time.sleep(2)
        ssp = ss(f"{MOD}_create_job_form")
        if check_form_exists(MOD, "Create Job"):
            add_result(MOD, "Create Job Form", "PASS", "Job creation form available")
        else:
            add_result(MOD, "Create Job Form", "WARN", "Clicked create but no form appeared")
        driver.back()
        time.sleep(2)

    # Candidates
    nav_module_page(DOMAIN, "/candidates", MOD, "Candidates",
        ["candidate", "name", "resume", "status", "stage", "email", "applied"])

    # Try adding candidate
    if try_click_button("add") or try_click_button("new candidate") or try_click_button("create"):
        time.sleep(2)
        ssp = ss(f"{MOD}_add_candidate")
        if check_form_exists(MOD, "Add Candidate"):
            add_result(MOD, "Add Candidate Form", "PASS", "Candidate form available")
        driver.back()
        time.sleep(2)

    # Interview
    nav_module_page(DOMAIN, "/interviews", MOD, "Interviews",
        ["interview", "schedule", "feedback", "scorecard", "candidate", "date"])
    nav_module_page(DOMAIN, "/interview", MOD, "Interview (alt)",
        ["interview", "schedule"])

    # Offers
    nav_module_page(DOMAIN, "/offers", MOD, "Offers",
        ["offer", "letter", "candidate", "send", "status", "package", "salary"])

    # Onboarding
    nav_module_page(DOMAIN, "/onboarding", MOD, "Onboarding",
        ["onboarding", "template", "task", "checklist", "new hire", "welcome"])

    # Analytics
    nav_module_page(DOMAIN, "/analytics", MOD, "Analytics",
        ["analytics", "metric", "time", "hire", "source", "report", "funnel"])
    nav_module_page(DOMAIN, "/reports", MOD, "Reports",
        ["report", "analytics", "metric"])

    # Settings
    nav_module_page(DOMAIN, "/settings", MOD, "Settings",
        ["setting", "career", "template", "pipeline", "email", "config"])

    go_back_to_dashboard()
    log(f"Completed {MOD} testing.\n")


# ══════════════════════════════════════════════════════════════════
# MODULE 3: PERFORMANCE
# ══════════════════════════════════════════════════════════════════
def test_performance():
    MOD = "Performance"
    DOMAIN = "test-performance.empcloud.com"
    log(f"\n{'='*60}\nTESTING MODULE: {MOD}\n{'='*60}")

    if not sso_into_module("Performance", DOMAIN):
        add_result(MOD, "SSO", "FAIL", "Could not access performance module")
        return

    # Dashboard
    nav_module_page(DOMAIN, "/", MOD, "Dashboard",
        ["dashboard", "performance", "review", "cycle", "goal", "rating"])

    # Reviews
    nav_module_page(DOMAIN, "/reviews", MOD, "Reviews",
        ["review", "cycle", "date", "status", "assign", "period"])
    nav_module_page(DOMAIN, "/review-cycles", MOD, "Review Cycles",
        ["review", "cycle", "create"])

    # Try creating review cycle
    if try_click_button("create") or try_click_button("new") or try_click_button("add"):
        time.sleep(2)
        ssp = ss(f"{MOD}_create_review")
        if check_form_exists(MOD, "Create Review"):
            add_result(MOD, "Create Review Cycle", "PASS", "Review creation form available")
        driver.back()
        time.sleep(2)

    # Goals/OKRs
    nav_module_page(DOMAIN, "/goals", MOD, "Goals",
        ["goal", "okr", "objective", "key result", "progress", "target", "completion"])
    nav_module_page(DOMAIN, "/okrs", MOD, "OKRs",
        ["okr", "objective", "key result"])

    # Self Assessment
    nav_module_page(DOMAIN, "/self-assessment", MOD, "Self Assessment",
        ["self", "assessment", "review", "form", "rating", "comment"])
    nav_module_page(DOMAIN, "/self-review", MOD, "Self Review",
        ["self", "review"])

    # Manager Review
    nav_module_page(DOMAIN, "/manager-review", MOD, "Manager Review",
        ["manager", "review", "team", "rate", "member", "employee"])
    nav_module_page(DOMAIN, "/team-reviews", MOD, "Team Reviews",
        ["team", "review"])

    # 360 Feedback
    nav_module_page(DOMAIN, "/360-feedback", MOD, "360 Feedback",
        ["360", "feedback", "peer", "review", "configure"])
    nav_module_page(DOMAIN, "/peer-review", MOD, "Peer Review",
        ["peer", "review", "feedback"])

    # Calibration
    nav_module_page(DOMAIN, "/calibration", MOD, "Calibration",
        ["calibration", "distribution", "rating", "bell curve", "normalize"])

    # Analytics
    nav_module_page(DOMAIN, "/analytics", MOD, "Analytics",
        ["analytics", "trend", "performance", "report", "metric"])
    nav_module_page(DOMAIN, "/reports", MOD, "Reports",
        ["report", "analytics"])

    # Settings
    nav_module_page(DOMAIN, "/settings", MOD, "Settings",
        ["setting", "config", "template", "rating scale"])

    go_back_to_dashboard()
    log(f"Completed {MOD} testing.\n")


# ══════════════════════════════════════════════════════════════════
# MODULE 4: REWARDS
# ══════════════════════════════════════════════════════════════════
def test_rewards():
    MOD = "Rewards"
    DOMAIN = "test-rewards.empcloud.com"
    log(f"\n{'='*60}\nTESTING MODULE: {MOD}\n{'='*60}")

    if not sso_into_module("Rewards", DOMAIN):
        add_result(MOD, "SSO", "FAIL", "Could not access rewards module")
        return

    # Dashboard
    nav_module_page(DOMAIN, "/", MOD, "Dashboard",
        ["dashboard", "recognition", "kudos", "badge", "reward", "leaderboard", "points"])

    # Give Kudos
    nav_module_page(DOMAIN, "/kudos", MOD, "Kudos",
        ["kudos", "send", "give", "recognize", "message", "employee", "appreciation"])
    nav_module_page(DOMAIN, "/give-kudos", MOD, "Give Kudos (alt)",
        ["kudos", "send", "give"])
    nav_module_page(DOMAIN, "/recognition", MOD, "Recognition",
        ["recognition", "kudos", "appreciate"])

    # Try sending kudos
    if try_click_button("give") or try_click_button("send") or try_click_button("kudos"):
        time.sleep(2)
        ssp = ss(f"{MOD}_give_kudos_form")
        if check_form_exists(MOD, "Give Kudos"):
            add_result(MOD, "Give Kudos Form", "PASS", "Kudos form available")
        driver.back()
        time.sleep(2)

    # Badges
    nav_module_page(DOMAIN, "/badges", MOD, "Badges",
        ["badge", "award", "earn", "achievement", "icon"])

    # Leaderboard
    nav_module_page(DOMAIN, "/leaderboard", MOD, "Leaderboard",
        ["leaderboard", "rank", "point", "top", "score", "employee"])

    # Team Challenges
    nav_module_page(DOMAIN, "/challenges", MOD, "Team Challenges",
        ["challenge", "team", "compete", "goal", "create", "active"])
    nav_module_page(DOMAIN, "/team-challenges", MOD, "Team Challenges (alt)",
        ["challenge", "team"])

    # Celebrations
    nav_module_page(DOMAIN, "/celebrations", MOD, "Celebrations",
        ["birthday", "anniversary", "celebration", "wish", "milestone"])

    # Rewards Catalog
    nav_module_page(DOMAIN, "/catalog", MOD, "Rewards Catalog",
        ["catalog", "redeem", "reward", "point", "gift", "voucher"])
    nav_module_page(DOMAIN, "/rewards-catalog", MOD, "Rewards Catalog (alt)",
        ["catalog", "redeem", "reward"])
    nav_module_page(DOMAIN, "/store", MOD, "Rewards Store",
        ["store", "redeem", "reward", "point"])

    # Settings
    nav_module_page(DOMAIN, "/settings", MOD, "Settings",
        ["setting", "config", "point", "badge"])

    go_back_to_dashboard()
    log(f"Completed {MOD} testing.\n")


# ══════════════════════════════════════════════════════════════════
# MODULE 5: EXIT MANAGEMENT
# ══════════════════════════════════════════════════════════════════
def test_exit():
    MOD = "Exit Management"
    DOMAIN = "test-exit.empcloud.com"
    log(f"\n{'='*60}\nTESTING MODULE: {MOD}\n{'='*60}")

    if not sso_into_module("Exit", DOMAIN):
        add_result(MOD, "SSO", "FAIL", "Could not access exit module")
        return

    # Dashboard
    nav_module_page(DOMAIN, "/", MOD, "Dashboard",
        ["dashboard", "exit", "offboarding", "active", "recent", "resignation", "status"])

    # Initiate Exit
    nav_module_page(DOMAIN, "/initiate", MOD, "Initiate Exit",
        ["initiate", "exit", "offboard", "employee", "reason", "date", "resignation"])
    nav_module_page(DOMAIN, "/initiate-exit", MOD, "Initiate Exit (alt)",
        ["initiate", "exit", "offboard"])
    nav_module_page(DOMAIN, "/new", MOD, "New Exit",
        ["initiate", "new", "exit", "offboard"])

    # Clearance
    nav_module_page(DOMAIN, "/clearance", MOD, "Clearance",
        ["clearance", "checklist", "it", "finance", "hr", "admin", "pending", "approved"])
    nav_module_page(DOMAIN, "/exit-clearance", MOD, "Exit Clearance (alt)",
        ["clearance", "checklist"])

    # Exit Interview
    nav_module_page(DOMAIN, "/exit-interview", MOD, "Exit Interview",
        ["interview", "schedule", "record", "feedback", "reason", "question"])
    nav_module_page(DOMAIN, "/interviews", MOD, "Exit Interviews (alt)",
        ["interview", "exit"])

    # Full & Final Settlement
    nav_module_page(DOMAIN, "/settlement", MOD, "Full & Final Settlement",
        ["settlement", "final", "dues", "calculate", "payment", "fnf", "full"])
    nav_module_page(DOMAIN, "/fnf", MOD, "FnF (alt)",
        ["settlement", "final", "fnf"])
    nav_module_page(DOMAIN, "/full-final", MOD, "Full & Final (alt)",
        ["settlement", "full", "final"])

    # Knowledge Transfer
    nav_module_page(DOMAIN, "/knowledge-transfer", MOD, "Knowledge Transfer",
        ["knowledge", "transfer", "kt", "task", "assign", "handover"])
    nav_module_page(DOMAIN, "/kt", MOD, "KT (alt)",
        ["knowledge", "transfer", "kt"])

    # Analytics
    nav_module_page(DOMAIN, "/analytics", MOD, "Analytics",
        ["analytics", "attrition", "trend", "report", "reason", "department"])
    nav_module_page(DOMAIN, "/reports", MOD, "Reports",
        ["report", "analytics", "attrition"])

    # Settings
    nav_module_page(DOMAIN, "/settings", MOD, "Settings",
        ["setting", "config", "template", "checklist"])

    go_back_to_dashboard()
    log(f"Completed {MOD} testing.\n")


# ══════════════════════════════════════════════════════════════════
# MODULE 6: LMS
# ══════════════════════════════════════════════════════════════════
def test_lms():
    MOD = "LMS"
    DOMAIN = "testlms.empcloud.com"
    log(f"\n{'='*60}\nTESTING MODULE: {MOD}\n{'='*60}")

    if not sso_into_module("LMS", DOMAIN):
        add_result(MOD, "SSO", "FAIL", "Could not access LMS module")
        return

    # Dashboard
    nav_module_page(DOMAIN, "/", MOD, "Dashboard",
        ["dashboard", "learning", "course", "assign", "progress", "training"])

    # Courses
    nav_module_page(DOMAIN, "/courses", MOD, "Courses",
        ["course", "title", "create", "category", "duration", "status", "module"])

    # Try creating course
    if try_click_button("create") or try_click_button("add") or try_click_button("new course"):
        time.sleep(2)
        ssp = ss(f"{MOD}_create_course")
        if check_form_exists(MOD, "Create Course"):
            add_result(MOD, "Create Course Form", "PASS", "Course creation form available")
        driver.back()
        time.sleep(2)

    # Assign Course
    nav_module_page(DOMAIN, "/assign", MOD, "Assign Course",
        ["assign", "employee", "department", "course", "deadline", "mandatory"])
    nav_module_page(DOMAIN, "/assignments", MOD, "Assignments",
        ["assign", "course", "employee"])

    # Quiz/Assessment
    nav_module_page(DOMAIN, "/quiz", MOD, "Quiz/Assessment",
        ["quiz", "assessment", "question", "score", "create", "test"])
    nav_module_page(DOMAIN, "/assessments", MOD, "Assessments",
        ["assessment", "quiz", "test"])
    nav_module_page(DOMAIN, "/quizzes", MOD, "Quizzes",
        ["quiz", "assessment"])

    # Certifications
    nav_module_page(DOMAIN, "/certifications", MOD, "Certifications",
        ["certificate", "certification", "issue", "view", "download", "completed"])
    nav_module_page(DOMAIN, "/certificates", MOD, "Certificates",
        ["certificate", "certification"])

    # Compliance Training
    nav_module_page(DOMAIN, "/compliance", MOD, "Compliance Training",
        ["compliance", "mandatory", "training", "track", "status", "overdue"])
    nav_module_page(DOMAIN, "/compliance-training", MOD, "Compliance Training (alt)",
        ["compliance", "mandatory"])

    # Analytics
    nav_module_page(DOMAIN, "/analytics", MOD, "Analytics",
        ["analytics", "completion", "rate", "progress", "learner", "report"])
    nav_module_page(DOMAIN, "/reports", MOD, "Reports",
        ["report", "analytics", "completion"])

    # My Learning
    nav_module_page(DOMAIN, "/my-learning", MOD, "My Learning",
        ["my", "learning", "course", "progress", "enrolled"])

    # Settings
    nav_module_page(DOMAIN, "/settings", MOD, "Settings",
        ["setting", "config", "template"])

    go_back_to_dashboard()
    log(f"Completed {MOD} testing.\n")


# ══════════════════════════════════════════════════════════════════
# MODULE 7: PROJECTS
# ══════════════════════════════════════════════════════════════════
def test_projects():
    MOD = "Projects"
    DOMAIN = "test-project.empcloud.com"
    log(f"\n{'='*60}\nTESTING MODULE: {MOD}\n{'='*60}")

    if not sso_into_module("Projects", DOMAIN):
        add_result(MOD, "SSO", "FAIL", "Could not access projects module")
        return

    # Dashboard
    nav_module_page(DOMAIN, "/", MOD, "Dashboard",
        ["dashboard", "project", "active", "task", "team", "overview", "progress"])

    # Projects list
    nav_module_page(DOMAIN, "/projects", MOD, "Projects List",
        ["project", "name", "status", "date", "team", "create"])

    # Try creating project
    if try_click_button("create") or try_click_button("add") or try_click_button("new project"):
        time.sleep(2)
        ssp = ss(f"{MOD}_create_project")
        if check_form_exists(MOD, "Create Project"):
            add_result(MOD, "Create Project Form", "PASS", "Project creation form available")
        driver.back()
        time.sleep(2)

    # Tasks
    nav_module_page(DOMAIN, "/tasks", MOD, "Tasks",
        ["task", "assign", "priority", "status", "due", "create", "title"])

    # Kanban Board
    nav_module_page(DOMAIN, "/kanban", MOD, "Kanban Board",
        ["kanban", "board", "todo", "in progress", "done", "drag", "column", "task"])
    nav_module_page(DOMAIN, "/board", MOD, "Board (alt)",
        ["board", "kanban", "column", "task"])

    # Time Tracking
    nav_module_page(DOMAIN, "/time-tracking", MOD, "Time Tracking",
        ["time", "tracking", "log", "hours", "task", "project", "entry"])
    nav_module_page(DOMAIN, "/timesheet", MOD, "Timesheet",
        ["timesheet", "time", "log", "hours"])
    nav_module_page(DOMAIN, "/timesheets", MOD, "Timesheets",
        ["timesheet", "time", "log"])

    # Gantt Chart
    nav_module_page(DOMAIN, "/gantt", MOD, "Gantt Chart",
        ["gantt", "timeline", "chart", "project", "task", "schedule"])
    nav_module_page(DOMAIN, "/timeline", MOD, "Timeline",
        ["timeline", "gantt", "schedule"])

    # Reports
    nav_module_page(DOMAIN, "/reports", MOD, "Reports",
        ["report", "progress", "time", "project", "summary", "analytics"])

    # Settings
    nav_module_page(DOMAIN, "/settings", MOD, "Settings",
        ["setting", "config", "project", "status"])

    # My Tasks
    nav_module_page(DOMAIN, "/my-tasks", MOD, "My Tasks",
        ["my", "task", "assigned", "todo"])

    go_back_to_dashboard()
    log(f"Completed {MOD} testing.\n")


# ══════════════════════════════════════════════════════════════════
# GitHub: Upload screenshots & file issues
# ══════════════════════════════════════════════════════════════════
def upload_screenshot_to_github(filepath):
    """Upload a screenshot to the repo and return the raw URL."""
    if not filepath or not os.path.exists(filepath):
        return None
    try:
        fname = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        path = f"test-screenshots/admin-modules-sso/{fname}"
        url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
        headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        # Check if exists
        r = requests.get(url, headers=headers, timeout=10)
        data = {"message": f"Add screenshot {fname}", "content": content}
        if r.status_code == 200:
            data["sha"] = r.json().get("sha")
        r = requests.put(url, headers=headers, json=data, timeout=30)
        if r.status_code in (200, 201):
            return r.json().get("content", {}).get("download_url", "")
    except Exception as e:
        log(f"  Screenshot upload failed: {e}")
    return None

def file_github_issue(title, body, labels=None):
    """File a GitHub issue."""
    url = f"https://api.github.com/repos/{GH_REPO}/issues"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"title": title, "body": body}
    if labels:
        data["labels"] = labels
    try:
        r = requests.post(url, headers=headers, json=data, timeout=30)
        if r.status_code == 201:
            issue_url = r.json().get("html_url", "")
            log(f"  Filed issue: {title} -> {issue_url}")
            return issue_url
        else:
            log(f"  Failed to file issue (HTTP {r.status_code}): {r.text[:200]}")
    except Exception as e:
        log(f"  Failed to file issue: {e}")
    return None

def check_existing_issues():
    """Get existing open issues to avoid duplicates."""
    url = f"https://api.github.com/repos/{GH_REPO}/issues"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    existing = set()
    page = 1
    while True:
        r = requests.get(url, headers=headers, params={"state": "open", "per_page": 100, "page": page}, timeout=30)
        if r.status_code != 200:
            break
        issues = r.json()
        if not issues:
            break
        for issue in issues:
            existing.add(issue["title"].strip().lower())
        page += 1
    return existing

def file_all_issues():
    """File all bugs and feature requests as GitHub issues."""
    log(f"\n{'='*60}\nFILING GITHUB ISSUES\n{'='*60}")
    existing = check_existing_issues()
    log(f"Found {len(existing)} existing open issues.")

    filed = 0
    skipped = 0

    # File bugs
    for bug in bugs:
        title = bug["title"]
        if title.strip().lower() in existing:
            log(f"  SKIP (duplicate): {title}")
            skipped += 1
            continue

        body = bug["desc"]
        # Upload screenshot if available
        if bug.get("ss"):
            img_url = upload_screenshot_to_github(bug["ss"])
            if img_url:
                body += f"\n\n**Screenshot:**\n![screenshot]({img_url})"

        body += "\n\n---\n*Filed by automated SSO module testing*"
        result = file_github_issue(title, body, labels=["bug"])
        if result:
            filed += 1

    # File feature requests
    for feat in feature_requests:
        title = feat["title"]
        if title.strip().lower() in existing:
            log(f"  SKIP (duplicate): {title}")
            skipped += 1
            continue

        body = feat["desc"]
        if feat.get("ss"):
            img_url = upload_screenshot_to_github(feat["ss"])
            if img_url:
                body += f"\n\n**Screenshot:**\n![screenshot]({img_url})"

        body += "\n\n---\n*Filed by automated SSO module testing*"
        result = file_github_issue(title, body, labels=["enhancement"])
        if result:
            filed += 1

    log(f"\nFiled {filed} issues, skipped {skipped} duplicates.")


# ══════════════════════════════════════════════════════════════════
# Main execution
# ══════════════════════════════════════════════════════════════════
def print_summary():
    log(f"\n{'='*60}")
    log(f"TEST SUMMARY")
    log(f"{'='*60}")

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    warn_count = sum(1 for r in results if r["status"] == "WARN")

    log(f"Total checks: {len(results)}")
    log(f"  PASS: {pass_count}")
    log(f"  FAIL: {fail_count}")
    log(f"  WARN: {warn_count}")
    log(f"Bugs found: {len(bugs)}")
    log(f"Feature requests: {len(feature_requests)}")
    log(f"Screenshots taken: {len(screenshots_taken)}")

    if bugs:
        log(f"\nBUGS:")
        for b in bugs:
            log(f"  - {b['title']}")

    if feature_requests:
        log(f"\nFEATURE REQUESTS:")
        for f in feature_requests:
            log(f"  - {f['title']}")

    # Save results to JSON
    with open(r"C:\emptesting\admin_modules_sso_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {"pass": pass_count, "fail": fail_count, "warn": warn_count,
                        "bugs": len(bugs), "features": len(feature_requests)},
            "results": results,
            "bugs": bugs,
            "feature_requests": feature_requests
        }, f, indent=2, ensure_ascii=False)
    log(f"Results saved to admin_modules_sso_results.json")


def main():
    global module_count
    log("Starting EMP Cloud Full SSO Module Workflow Testing")
    log(f"Base URL: {BASE}")
    log(f"User: {ADMIN_EMAIL}")

    create_driver()

    if not login():
        log("FATAL: Cannot login. Aborting.")
        driver.quit()
        return

    # Navigate to modules page first
    navigate_to_modules_page()

    # Test each module with driver restart every 2 modules
    modules_to_test = [
        ("Payroll", test_payroll),
        ("Recruitment", test_recruitment),
        # Restart driver here (after 2 modules)
        ("Performance", test_performance),
        ("Rewards", test_rewards),
        # Restart driver here (after 4 modules)
        ("Exit Management", test_exit),
        ("LMS", test_lms),
        # Restart driver here (after 6 modules)
        ("Projects", test_projects),
    ]

    for i, (name, test_fn) in enumerate(modules_to_test):
        # Restart driver every 2 modules
        if i > 0 and i % 2 == 0:
            log(f"\n=== Restarting driver (after {i} modules) ===\n")
            create_driver()
            if not login():
                log(f"FATAL: Cannot re-login after driver restart. Aborting remaining tests.")
                break

        try:
            test_fn()
        except Exception as e:
            log(f"ERROR testing {name}: {e}")
            traceback.print_exc()
            ss(f"error_{name}")
            add_result(name, "Module Test", "FAIL", f"Unhandled error: {str(e)[:200]}")
            # Try to recover
            try:
                go_back_to_dashboard()
            except:
                create_driver()
                login()

    # Print summary
    print_summary()

    # Upload screenshots and file issues
    try:
        file_all_issues()
    except Exception as e:
        log(f"Error filing issues: {e}")
        traceback.print_exc()

    # Cleanup
    try:
        driver.quit()
    except:
        pass

    log("\nDone!")


if __name__ == "__main__":
    main()
