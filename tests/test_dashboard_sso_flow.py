#!/usr/bin/env python3
"""
EMP Cloud HRMS — Dashboard & SSO Flow Functional Testing
All 4 phases: Login & Map, Sidebar Core Modules, External SSO Modules, Employee Role
"""

import sys, os, time, json, traceback, base64, requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────
BASE = "https://test-empcloud.empcloud.com"
SSDIR = r"C:\Users\Admin\screenshots\dashboard_sso"
GH_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GH_REPO = "EmpCloud/EmpCloud"
ADMIN = ("ananya@technova.in", "Welcome@123")
EMP = ("priya@technova.in", "Welcome@123")
os.makedirs(SSDIR, exist_ok=True)

results = []
bugs = []
test_count = 0
driver = None
DRIVER_PATH = None

def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def log(m):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)

# ── Sidebar pages (discovered from dashboard) ──────────────────
SIDEBAR_PAGES = [
    ("Dashboard", "/"),
    ("Modules", "/modules"),
    ("Billing", "/billing"),
    ("Users", "/users"),
    ("Employees", "/employees"),
    ("Org Chart", "/org-chart"),
    ("AI Assistant", "/chatbot"),
    ("My Team", "/manager"),
    ("Attendance", "/attendance"),
    ("Leave", "/leave"),
    ("Comp-Off", "/leave/comp-off"),
    ("Documents", "/documents"),
    ("Announcements", "/announcements"),
    ("Policies", "/policies"),
    ("Settings", "/settings"),
    ("Custom Fields", "/custom-fields"),
    ("Audit Log", "/audit"),
    ("Positions Dashboard", "/positions"),
    ("Positions List", "/positions/list"),
    ("Vacancies", "/positions/vacancies"),
    ("Headcount Plans", "/positions/headcount-plans"),
    ("Community", "/forum"),
    ("Create Post", "/forum/new"),
    ("Forum Dashboard", "/forum/dashboard"),
    ("Events", "/events"),
    ("My Events", "/events/my"),
    ("Event Dashboard", "/events/dashboard"),
    ("Whistleblowing Submit", "/whistleblowing/submit"),
    ("Whistleblowing Track", "/whistleblowing/track"),
    ("Whistleblowing Dashboard", "/whistleblowing/dashboard"),
    ("All Reports", "/whistleblowing/reports"),
    ("My Tickets", "/helpdesk/my-tickets"),
    ("All Tickets", "/helpdesk/tickets"),
    ("Helpdesk Dashboard", "/helpdesk/dashboard"),
    ("Knowledge Base", "/helpdesk/kb"),
    ("Survey Dashboard", "/surveys/dashboard"),
    ("All Surveys", "/surveys/list"),
    ("Active Surveys", "/surveys/respond"),
    ("Wellness", "/wellness"),
    ("My Wellness", "/wellness/my"),
    ("Daily Check-in", "/wellness/check-in"),
    ("Wellness Dashboard", "/wellness/dashboard"),
    ("Asset Dashboard", "/assets/dashboard"),
    ("All Assets", "/assets"),
    ("Asset Categories", "/assets/categories"),
    ("Submit Feedback", "/feedback/submit"),
    ("My Feedback", "/feedback/my"),
    ("All Feedback", "/feedback"),
    ("Feedback Dashboard", "/feedback/dashboard"),
]

# External SSO module names and their subdomain patterns (from dashboard "Launch" links)
SSO_MODULES = [
    ("Rewards & Recognition", "test-rewards.empcloud.com"),
    ("Recruitment", "test-recruit.empcloud.com"),
    ("Projects", "test-project.empcloud.com"),
    ("Performance", "test-performance.empcloud.com"),
    ("Payroll", "testpayroll.empcloud.com"),
    ("LMS", "testlms.empcloud.com"),
    ("Exit Management", "test-exit.empcloud.com"),
    ("Employee Monitoring", "test-empmonitor.empcloud.com"),
]

SKIP_SSO = ["Field Force", "Biometric"]

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
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(2)
    return driver

def maybe_restart():
    global test_count
    test_count += 1
    if test_count % 5 == 0:
        log(f"--- Restarting driver (test #{test_count}) ---")
        create_driver()
        return True
    return False

def safe_click(el):
    try: el.click()
    except: driver.execute_script("arguments[0].click();", el)

def ss(name):
    safe = name.replace(" ","_").replace("/","_").replace("\\","_")[:70]
    p = os.path.join(SSDIR, f"{safe}_{ts()}.png")
    try:
        driver.save_screenshot(p)
        return p
    except:
        return None

def add_result(page, status, detail="", ssp=None):
    results.append({"page":page,"status":status,"detail":detail,"ss":ssp})

def add_bug(title, desc, ssp=None):
    bugs.append({"title":title,"desc":desc,"ss":ssp})

# ── Login ──────────────────────────────────────────────────────
def login(email, password, label=""):
    log(f"Logging in as {email} ({label})...")
    driver.get(f"{BASE}/login")
    try:
        wait = WebDriverWait(driver, 15)
        em = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='email']")))
        em.clear(); em.send_keys(email)
        pw = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        pw.clear(); pw.send_keys(password)
        time.sleep(0.3)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        # Wait for redirect away from /login
        WebDriverWait(driver, 15).until(lambda d: "/login" not in d.current_url)
        time.sleep(3)
        log(f"  Logged in -> {driver.current_url}")
        add_result(f"Login ({label})", "PASS", driver.current_url)
        return True
    except Exception as e:
        log(f"  Login failed: {e}")
        ss(f"login_fail_{label}")
        add_result(f"Login ({label})", "FAIL", str(e))
        return False

def close_overlays():
    for sel in [".Toastify__close-button","button.close",".modal .btn-close","[aria-label='Close']"]:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed(): safe_click(el); time.sleep(0.2)
        except: pass

# ── Page checker ──────────────────────────────────────────────
def check_page(name, url=None):
    time.sleep(2)
    close_overlays()
    cur = driver.current_url
    body = ""
    try: body = driver.find_element(By.TAG_NAME, "body").text[:2000]
    except: pass

    errors_found = []
    for pat in ["500 Internal Server Error","404 Not Found","403 Forbidden",
                "Something went wrong","Page not found","Server Error",
                "Cannot read properties","Application error"]:
        if pat.lower() in body.lower():
            errors_found.append(pat)

    if len(body.strip()) < 20:
        errors_found.append("Page blank/empty")

    ssp = ss(f"page_{name}")

    if errors_found:
        detail = "; ".join(errors_found)
        add_result(name, "FAIL", f"{cur} | {detail}", ssp)
        add_bug(f"[FUNCTIONAL] {name}: {errors_found[0]}",
                f"**Page:** {name}\n**URL:** {cur}\n**Errors:** {detail}\n**Preview:** {body[:300]}", ssp)
        return False
    else:
        add_result(name, "PASS", f"{cur} | content loaded", ssp)
        return True

def check_crud(name):
    findings = []
    # Table rows
    for sel in ["table tbody tr",".list-item","[class*='Table'] tr"]:
        try:
            rows = [r for r in driver.find_elements(By.CSS_SELECTOR, sel) if r.is_displayed()]
            if rows:
                findings.append(f"List: {len(rows)} rows")
                break
        except: pass

    # Add/Create button
    add_btn = None
    for xp in ["//button[contains(text(),'Add')]","//button[contains(text(),'Create')]",
               "//button[contains(text(),'New')]","//a[contains(text(),'Add')]",
               "//button[contains(text(),'Invite')]","//a[contains(text(),'Create')]",
               "//button[contains(text(),'Submit')]","//a[contains(text(),'New')]",
               "//button[contains(text(),'Apply')]"]:
        try:
            el = driver.find_element(By.XPATH, xp)
            if el.is_displayed():
                add_btn = el
                findings.append(f"Button: '{el.text.strip()[:30]}'")
                break
        except: pass

    if add_btn:
        try:
            safe_click(add_btn)
            time.sleep(2)
            close_overlays()
            form = False
            for sel in ["form","[role='dialog']",".modal.show","[class*='Modal']",
                        "[class*='Drawer']","[class*='dialog']"]:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    if el.is_displayed(): form = True; break
                except: pass
            if form:
                findings.append("Form opens")
                ss(f"crud_form_{name}")
            else:
                if driver.current_url != f"{BASE}{name}":
                    findings.append("Navigated to new page")
                    ss(f"crud_nav_{name}")
                    driver.back(); time.sleep(2)
            # Try to close modal
            for sel in ["//button[contains(text(),'Cancel')]","//button[contains(text(),'Close')]",
                        ".modal .btn-close","button[aria-label='Close']"]:
                try:
                    if sel.startswith("//"): el = driver.find_element(By.XPATH, sel)
                    else: el = driver.find_element(By.CSS_SELECTOR, sel)
                    if el.is_displayed(): safe_click(el); time.sleep(0.5); break
                except: pass
        except Exception as e:
            findings.append(f"Click error: {e}")

    # Search
    for sel in ["input[type='search']","input[placeholder*='earch']","input[placeholder*='filter']"]:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed(): findings.append("Search available"); break
        except: pass

    # Edit / View / Delete
    for label, xpaths in [
        ("Edit/View", ["//button[contains(text(),'Edit')]","//a[contains(text(),'Edit')]",
                       "//button[contains(text(),'View')]","//a[contains(text(),'View')]"]),
        ("Delete", ["//button[contains(text(),'Delete')]","[aria-label='Delete']"])
    ]:
        for xp in xpaths:
            try:
                if xp.startswith("//"): el = driver.find_element(By.XPATH, xp)
                else: el = driver.find_element(By.CSS_SELECTOR, xp)
                if el.is_displayed(): findings.append(f"{label} available"); break
            except: pass

    detail = " | ".join(findings) if findings else "No CRUD elements"
    log(f"  CRUD [{name}]: {detail}")
    return detail

# ── GitHub helpers ─────────────────────────────────────────────
def gh_upload(filepath):
    if not filepath or not os.path.exists(filepath): return None
    fn = os.path.basename(filepath)
    with open(filepath,"rb") as f: content = base64.b64encode(f.read()).decode()
    url = f"https://api.github.com/repos/{GH_REPO}/contents/test-screenshots/dashboard-sso/{fn}"
    h = {"Authorization":f"token {GH_TOKEN}","Accept":"application/vnd.github.v3+json"}
    r = requests.put(url, json={"message":f"Add screenshot: {fn}","content":content,"branch":"main"}, headers=h)
    if r.status_code in (200,201):
        dl = r.json().get("content",{}).get("download_url","")
        log(f"  Uploaded: {fn}")
        return dl
    else:
        log(f"  Upload failed ({r.status_code})")
        return None

def gh_issue(title, body, ss_url=None):
    if ss_url: body += f"\n\n**Screenshot:**\n![screenshot]({ss_url})"
    url = f"https://api.github.com/repos/{GH_REPO}/issues"
    h = {"Authorization":f"token {GH_TOKEN}","Accept":"application/vnd.github.v3+json"}
    r = requests.post(url, json={"title":title,"body":body,"labels":["bug","functional-test","dashboard-sso"]}, headers=h)
    if r.status_code == 201:
        iu = r.json().get("html_url","")
        log(f"  Issue: {iu}")
        return iu
    log(f"  Issue failed ({r.status_code})")
    return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 1: LOGIN & MAP DASHBOARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def phase1():
    log("="*60)
    log("PHASE 1: LOGIN & MAP DASHBOARD (Org Admin)")
    log("="*60)
    create_driver()
    if not login(*ADMIN, "OrgAdmin"):
        return

    # Screenshot dashboard
    ssp = ss("admin_dashboard")
    add_result("Admin Dashboard", "PASS", "Dashboard loaded", ssp)

    # Scroll to capture module insights
    driver.execute_script("window.scrollTo(0, 600)")
    time.sleep(1)
    ss("dashboard_module_insights")

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    ss("dashboard_your_modules")

    # Log sidebar links
    log("\nSidebar links discovered:")
    for name, path in SIDEBAR_PAGES:
        log(f"  {name}: {BASE}{path}")
    log(f"\nSSO modules:")
    for name, dom in SSO_MODULES:
        log(f"  {name}: {dom}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 2: TEST ALL SIDEBAR PAGES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def phase2():
    log("="*60)
    log("PHASE 2: TEST CORE MODULES VIA SIDEBAR (Org Admin)")
    log("="*60)

    for i, (name, path) in enumerate(SIDEBAR_PAGES):
        log(f"\n--- [{i+1}/{len(SIDEBAR_PAGES)}] {name} ({path}) ---")

        need_login = maybe_restart()
        if need_login:
            if not login(*ADMIN, "OrgAdmin"):
                add_result(name, "BLOCKED", "Re-login failed")
                continue

        try:
            driver.get(f"{BASE}{path}")
            time.sleep(3)
            ok = check_page(name)
            if ok:
                crud_detail = check_crud(name)
                add_result(f"CRUD: {name}", "INFO", crud_detail)
        except Exception as e:
            log(f"  Error: {e}")
            ssp = ss(f"error_{name}")
            add_result(name, "ERROR", str(e), ssp)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 3: EXTERNAL SSO MODULES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def phase3():
    log("="*60)
    log("PHASE 3: TEST EXTERNAL MODULES VIA SSO")
    log("="*60)

    create_driver()
    if not login(*ADMIN, "OrgAdmin"):
        add_result("SSO Phase", "BLOCKED", "Login failed")
        return

    for name, domain in SSO_MODULES:
        if any(s in name for s in SKIP_SSO):
            log(f"  Skipping {name}")
            continue

        log(f"\n--- SSO: {name} ({domain}) ---")

        need_login = maybe_restart()
        if need_login:
            if not login(*ADMIN, "OrgAdmin"):
                add_result(f"SSO: {name}", "BLOCKED", "Re-login failed")
                continue

        try:
            # Go to dashboard to get fresh SSO tokens
            driver.get(BASE)
            time.sleep(4)

            # Scroll to module section and find the Launch link
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            # Find link containing the module domain
            clicked = False
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                if domain in href and text == "Launch":
                    log(f"  Clicking Launch for {name}...")
                    safe_click(link)
                    time.sleep(5)
                    clicked = True
                    break

            if not clicked:
                # Try View Details links from Module Insights
                for link in links:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()
                    if domain in href:
                        log(f"  Clicking '{text}' link...")
                        safe_click(link)
                        time.sleep(5)
                        clicked = True
                        break

            if not clicked:
                add_result(f"SSO: {name}", "SKIP", f"No link found for {domain}")
                continue

            cur = driver.current_url
            log(f"  Landed at: {cur}")

            # Wait for SPA to render
            time.sleep(4)
            body = ""
            try: body = driver.find_element(By.TAG_NAME, "body").text[:1500]
            except: pass

            ssp = ss(f"sso_{name}")

            # Check for errors
            errors = []
            for pat in ["404","Not Found","Error","Forbidden","Something went wrong",
                        "Application error","Server Error"]:
                if pat.lower() in body.lower()[:200]:
                    errors.append(pat)

            if len(body.strip()) < 20:
                errors.append("Blank page")

            if errors:
                add_result(f"SSO: {name}", "FAIL", f"{cur} | {'; '.join(errors)}", ssp)
                add_bug(f"[FUNCTIONAL] SSO {name}: {errors[0]}",
                        f"**Module:** {name}\n**URL:** {cur}\n**Body:** {body[:300]}", ssp)
            else:
                add_result(f"SSO: {name}", "PASS", f"{cur} | Loaded OK", ssp)
                log(f"  Content preview: {body[:150]}")

                # Test basic navigation within module
                try:
                    nav_links = driver.find_elements(By.TAG_NAME, "a")
                    internal_links = [l for l in nav_links if domain in (l.get_attribute("href") or "")]
                    if internal_links:
                        first = internal_links[0]
                        ft = first.text.strip()[:30]
                        if ft:
                            log(f"  Testing internal nav: '{ft}'")
                            safe_click(first)
                            time.sleep(3)
                            ss(f"sso_nav_{name}")
                            add_result(f"SSO Nav: {name}", "PASS", f"Navigated to '{ft}'")
                except Exception as e:
                    log(f"  Internal nav error: {e}")

        except Exception as e:
            log(f"  SSO Error: {e}")
            ssp = ss(f"sso_error_{name}")
            add_result(f"SSO: {name}", "ERROR", str(e), ssp)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 4: EMPLOYEE TESTING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def phase4():
    log("="*60)
    log("PHASE 4: TEST AS EMPLOYEE")
    log("="*60)

    create_driver()
    if not login(*EMP, "Employee"):
        add_result("Employee Phase", "BLOCKED", "Login failed")
        return

    # Dashboard
    ssp = ss("employee_dashboard")
    check_page("Emp: Dashboard")

    # Map what sidebar links employee sees
    body = driver.find_element(By.TAG_NAME, "body").text[:3000]
    log(f"  Employee dashboard preview:\n{body[:500]}")

    # Collect links
    emp_links = []
    for link in driver.find_elements(By.TAG_NAME, "a"):
        href = link.get_attribute("href") or ""
        text = link.text.strip()
        if BASE in href and text and len(text) < 60 and href != BASE + "/":
            path = href.replace(BASE, "")
            if path and not any(s in text.lower() for s in ["field force","biometric"]):
                emp_links.append((text, path))

    seen = set()
    unique_links = []
    for t, p in emp_links:
        if p not in seen:
            seen.add(p)
            unique_links.append((t, p))

    log(f"  Employee has {len(unique_links)} sidebar/nav links")

    # Test each employee page
    for i, (name, path) in enumerate(unique_links):
        # Skip SSO module links (external domains handled separately)
        if "sso_token" in path:
            continue

        log(f"\n--- Emp [{i+1}/{len(unique_links)}] {name} ({path}) ---")

        need_login = maybe_restart()
        if need_login:
            if not login(*EMP, "Employee"):
                add_result(f"Emp: {name}", "BLOCKED", "Re-login failed")
                continue

        try:
            driver.get(f"{BASE}{path}")
            time.sleep(3)
            check_page(f"Emp: {name}")
        except Exception as e:
            log(f"  Error: {e}")
            add_result(f"Emp: {name}", "ERROR", str(e))

    # Employee SSO modules
    log("\n--- Employee SSO Modules ---")
    need_login = maybe_restart()
    if need_login:
        login(*EMP, "Employee")

    try:
        driver.get(BASE)
        time.sleep(4)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

        # Find Launch links
        links = driver.find_elements(By.TAG_NAME, "a")
        for name, domain in SSO_MODULES[:5]:  # Test a subset
            if any(s in name for s in SKIP_SSO):
                continue
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                if domain in href and text == "Launch":
                    log(f"  Emp SSO: {name}")
                    safe_click(link)
                    time.sleep(5)
                    ssp = ss(f"emp_sso_{name}")
                    cur = driver.current_url
                    body = ""
                    try: body = driver.find_element(By.TAG_NAME, "body").text[:500]
                    except: pass
                    if len(body.strip()) < 20:
                        add_result(f"Emp SSO: {name}", "FAIL", "Blank page", ssp)
                    else:
                        add_result(f"Emp SSO: {name}", "PASS", f"{cur}", ssp)
                    # Go back
                    driver.get(BASE)
                    time.sleep(3)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)
                    links = driver.find_elements(By.TAG_NAME, "a")
                    break
    except Exception as e:
        log(f"  Emp SSO error: {e}")

# ── Report ─────────────────────────────────────────────────────
def report():
    log("\n" + "="*70)
    log("FINAL TEST REPORT -- EMP Cloud Dashboard & SSO Testing")
    log("="*70)
    p = sum(1 for r in results if r["status"]=="PASS")
    f = sum(1 for r in results if r["status"]=="FAIL")
    e = sum(1 for r in results if r["status"]=="ERROR")
    s = sum(1 for r in results if r["status"]=="SKIP")
    info = sum(1 for r in results if r["status"]=="INFO")
    blk = sum(1 for r in results if r["status"]=="BLOCKED")

    log(f"\nSummary: {p} PASS | {f} FAIL | {e} ERROR | {s} SKIP | {blk} BLOCKED | {info} INFO")
    log(f"Bugs found: {len(bugs)}\n")
    log(f"{'Page':<45} {'Status':<10} Details")
    log("-"*120)
    for r in results:
        pg = r["page"][:44]
        st = r["status"]
        dt = r["detail"][:70] if r["detail"] else ""
        log(f"{pg:<45} {st:<10} {dt}")
    log("-"*120)

    if bugs:
        log(f"\n{'='*70}")
        log("BUGS TO FILE:")
        log(f"{'='*70}")
        for b in bugs:
            log(f"  {b['title']}")
    return p, f, e

def file_bugs():
    if not bugs:
        log("No bugs to file.")
        return
    log(f"\n--- Filing {len(bugs)} bugs on GitHub ---")
    for b in bugs:
        ss_url = gh_upload(b["ss"]) if b.get("ss") else None
        gh_issue(b["title"], b["desc"], ss_url)
        time.sleep(1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    t0 = time.time()
    log("Starting EMP Cloud Dashboard & SSO Flow Testing")
    log(f"Base: {BASE}")

    try:
        phase1()
        phase2()
        phase3()
        phase4()
    except Exception as e:
        log(f"FATAL: {e}")
        traceback.print_exc()
    finally:
        if driver:
            try: driver.quit()
            except: pass

    p, f, e = report()
    file_bugs()

    elapsed = time.time() - t0
    log(f"\nTotal time: {elapsed:.0f}s")
    log(f"Final: {p} PASS, {f} FAIL, {e} ERRORS, {len(bugs)} bugs filed")
    log("DONE")
