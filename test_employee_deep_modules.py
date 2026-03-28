#!/usr/bin/env python3
"""
Deep employee testing of modules where direct login works:
- Payroll (testpayroll.empcloud.com) - Full employee portal
- Performance (test-performance.empcloud.com) - RBAC concerns
- Exit (test-exit.empcloud.com) - RBAC concerns (employee sees admin sidebar)
"""

import sys, os, time, json, ssl, re
import urllib.request, urllib.parse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\employee_modules_v2"
GH_PAT = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE
DRIVER_PATH = None

test_results = []
bugs_found = []

def ts(): return datetime.now().strftime("%Y%m%d_%H%M%S")
def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)
def result(n, s, d=""): test_results.append({"test":n,"status":s,"details":d}); print(f"  [{s}] {n}: {d}", flush=True)
def bug(t, d, sev="medium", sp=None): bugs_found.append({"title":t,"description":d,"severity":sev,"screenshot":sp}); print(f"  [BUG-{sev.upper()}] {t}", flush=True)

def shot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{ts()}.png")
    try: driver.save_screenshot(path)
    except: path = None
    return path

def create_driver():
    global DRIVER_PATH
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage","--disable-gpu",
              "--window-size=1920,1080","--ignore-certificate-errors"]:
        opts.add_argument(a)
    if not DRIVER_PATH:
        DRIVER_PATH = ChromeDriverManager().install()
    d = webdriver.Chrome(service=Service(DRIVER_PATH), options=opts)
    d.set_page_load_timeout(60); d.implicitly_wait(3)
    return d

def module_login(driver, module_url, email="priya@technova.in", password="Welcome@123"):
    driver.get(module_url + "/login")
    time.sleep(5)
    try:
        e = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        p = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        e.clear(); e.send_keys(email)
        p.clear(); p.send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except: return False
    time.sleep(6)
    return "/login" not in driver.current_url.lower()

def get_text(driver):
    try: return driver.find_element(By.TAG_NAME, "body").text
    except: return ""

def get_src(driver):
    try: return driver.page_source.lower()
    except: return ""

def upload_screenshot_github(filepath):
    if not filepath or not os.path.exists(filepath): return None
    fname = os.path.basename(filepath)
    import base64
    with open(filepath, "rb") as f: content = base64.b64encode(f.read()).decode()
    url = f"https://api.github.com/repos/{GH_REPO}/contents/screenshots/employee_modules_v2/{fname}"
    data = json.dumps({"message": f"Upload {fname}", "content": content, "branch": "main"}).encode()
    req = urllib.request.Request(url, data=data, method="PUT", headers={
        "Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-E2E", "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        return json.loads(r.read().decode()).get("content",{}).get("download_url","")
    except: return None

def file_github_issue(title, body, labels=None):
    if labels is None: labels = ["bug"]
    try:
        sq = urllib.parse.quote(title[:50])
        req = urllib.request.Request(
            f"https://api.github.com/search/issues?q=repo:{GH_REPO}+is:issue+in:title+{sq}",
            headers={"Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github+json", "User-Agent": "EmpCloud-E2E"})
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=15)
        res = json.loads(r.read().decode())
        if res.get("total_count", 0) > 0:
            log(f"  [GH-SKIP] Exists: #{res['items'][0]['number']}")
            return res["items"][0].get("html_url")
    except: pass
    url = f"https://api.github.com/repos/{GH_REPO}/issues"
    data = json.dumps({"title": title, "body": body, "labels": labels}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-E2E", "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        res = json.loads(r.read().decode())
        log(f"  [GH] #{res.get('number')} -> {res.get('html_url')}")
        return res.get("html_url")
    except Exception as e:
        log(f"  [GH-FAIL] {e}")
        return None


# ════════════════════════════════════════════════════════════
# PAYROLL — Deep Employee Test
# ════════════════════════════════════════════════════════════

def test_payroll_deep(driver):
    log("\n" + "=" * 70)
    log("PAYROLL — Deep Employee Test (Direct Login)")
    log("=" * 70)

    PAYROLL = "https://testpayroll.empcloud.com"
    ok = module_login(driver, PAYROLL)
    if not ok:
        result("Payroll-Login", "FAIL", "Cannot login")
        return

    result("Payroll-Login", "PASS", f"URL: {driver.current_url}")
    shot(driver, "payroll_emp_dashboard")

    # Dashboard content
    text = get_text(driver)
    log("  Dashboard:")
    for line in text.split('\n')[:25]:
        if line.strip(): log(f"    | {line.strip()}")

    # Check CTC display
    if "ctc" in text.lower() or "1,00,000" in text or "100000" in text:
        result("Payroll-CTC", "PASS", "Monthly CTC visible on dashboard")
    else:
        result("Payroll-CTC", "FAIL", "CTC not visible")

    # Check Net Pay
    src = get_src(driver)
    if "net pay" in src:
        result("Payroll-NetPay", "PASS", "Net pay visible on dashboard")
    else:
        result("Payroll-NetPay", "INFO", "Net pay not visible on dashboard")

    # ── My Payslips ──
    log("\n  --- My Payslips ---")
    driver.get(PAYROLL + "/my/payslips")
    time.sleep(4)
    sp_ps = shot(driver, "payroll_my_payslips")
    text = get_text(driver)
    src = get_src(driver)
    log("  My Payslips page:")
    for line in text.split('\n')[:20]:
        if line.strip(): log(f"    | {line.strip()}")

    if "payslip" in src or "salary slip" in src:
        result("Payroll-MyPayslips-Page", "PASS", "Payslips page loaded")
    else:
        result("Payroll-MyPayslips-Page", "FAIL", "Payslips page has no payslip content")

    # Check for download button
    download_found = False
    for el in driver.find_elements(By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'download')]"):
        download_found = True
        log(f"    Download element found: <{el.tag_name}> '{(el.text or '').strip()}'")
        break
    for el in driver.find_elements(By.CSS_SELECTOR, "[class*='download'], [title*='download'], [aria-label*='download']"):
        download_found = True
        break
    # Also check for PDF icon/button
    for el in driver.find_elements(By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'pdf')]"):
        download_found = True
        break
    if download_found:
        result("Payroll-DownloadPayslip", "PASS", "Download/PDF option found")
    else:
        result("Payroll-DownloadPayslip", "INFO", "No download button visible (may need payslip data)")

    # ── My Salary ──
    log("\n  --- My Salary ---")
    driver.get(PAYROLL + "/my/salary")
    time.sleep(4)
    sp_sal = shot(driver, "payroll_my_salary")
    text = get_text(driver)
    src = get_src(driver)
    log("  My Salary page:")
    for line in text.split('\n')[:25]:
        if line.strip(): log(f"    | {line.strip()}")

    sal_kw = ["basic", "hra", "deduction", "allowance", "gross", "net", "ctc"]
    found_sal = [kw for kw in sal_kw if kw in src]
    if found_sal:
        result("Payroll-SalaryBreakdown", "PASS", f"Salary components visible: {found_sal}")
    else:
        result("Payroll-SalaryBreakdown", "FAIL", "No salary breakdown visible")
        bug("Payroll — My Salary page shows no breakdown",
            "Employee navigated to /my/salary but no salary components (basic, HRA, deductions) visible.",
            "medium", sp_sal)

    # ── My Tax ──
    log("\n  --- My Tax ---")
    driver.get(PAYROLL + "/my/tax")
    time.sleep(4)
    sp_tax = shot(driver, "payroll_my_tax")
    text = get_text(driver)
    src = get_src(driver)
    log("  My Tax page:")
    for line in text.split('\n')[:25]:
        if line.strip(): log(f"    | {line.strip()}")

    tax_kw = ["tds", "tax", "regime", "income tax", "annual", "projected"]
    found_tax = [kw for kw in tax_kw if kw in src]
    if found_tax:
        result("Payroll-TaxDetails", "PASS", f"Tax info visible: {found_tax}")
    else:
        result("Payroll-TaxDetails", "FAIL", "No tax details visible")

    # ── Declarations (80C, HRA, etc.) ──
    log("\n  --- Declarations ---")
    driver.get(PAYROLL + "/my/declarations")
    time.sleep(4)
    sp_dec = shot(driver, "payroll_declarations")
    text = get_text(driver)
    src = get_src(driver)
    log("  Declarations page:")
    for line in text.split('\n')[:25]:
        if line.strip(): log(f"    | {line.strip()}")

    dec_kw = ["declaration", "80c", "hra", "section", "investment", "proof"]
    found_dec = [kw for kw in dec_kw if kw in src]
    if found_dec:
        result("Payroll-Declarations", "PASS", f"Declaration content: {found_dec}")
        # Check if submit button exists
        submit_found = False
        for el in driver.find_elements(By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit') or contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'declare') or contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'save')]"):
            submit_found = True
            break
        if submit_found:
            result("Payroll-Declarations-Submit", "PASS", "Submit/Save button found for declarations")
        else:
            result("Payroll-Declarations-Submit", "INFO", "No submit button visible")
    else:
        result("Payroll-Declarations", "FAIL", "No declaration content")

    # ── Reimbursements ──
    log("\n  --- Reimbursements ---")
    driver.get(PAYROLL + "/my/reimbursements")
    time.sleep(4)
    sp_reimb = shot(driver, "payroll_reimbursements")
    text = get_text(driver)
    src = get_src(driver)
    log("  Reimbursements page:")
    for line in text.split('\n')[:25]:
        if line.strip(): log(f"    | {line.strip()}")

    reimb_kw = ["reimbursement", "claim", "expense", "submit", "amount"]
    found_reimb = [kw for kw in reimb_kw if kw in src]
    if found_reimb:
        result("Payroll-Reimbursements", "PASS", f"Reimbursement content: {found_reimb}")
    else:
        result("Payroll-Reimbursements", "FAIL", "No reimbursement content")

    # ── RBAC: Admin Panel ──
    log("\n  --- RBAC: Admin Panel ---")
    driver.get(PAYROLL + "/admin")
    time.sleep(4)
    sp_admin = shot(driver, "payroll_admin_panel")
    text = get_text(driver)
    src = get_src(driver)
    log("  Admin Panel page:")
    for line in text.split('\n')[:25]:
        if line.strip(): log(f"    | {line.strip()}")

    current = driver.current_url.lower()
    admin_kw = ["employee list", "all employees", "payroll run", "salary structure", "bulk", "admin panel"]
    if any(kw in src for kw in admin_kw) and "admin" in current:
        result("Payroll-RBAC-AdminPanel", "FAIL", "Employee can access admin panel!")
        bug("Payroll — Employee can access Admin Panel (RBAC violation)",
            "Employee (priya@technova.in) can access the Admin Panel at /admin.\n"
            "This is visible in the sidebar navigation as 'Admin Panel' link.\n\n"
            "**Expected:** Employee should only see employee portal pages.\n"
            "**Actual:** Admin Panel is accessible and potentially shows all employee data.",
            "critical", sp_admin)
    elif "/my" in current or "/login" in current:
        result("Payroll-RBAC-AdminPanel", "PASS", f"Redirected to {current}")
    else:
        result("Payroll-RBAC-AdminPanel", "INFO", f"Admin URL: {current}")

    # Note: The sidebar showed "Admin Panel" as a link — this is already concerning
    # even if the page redirects, the link shouldn't be visible
    driver.get(PAYROLL + "/my")
    time.sleep(3)
    sidebar_text = get_text(driver)
    if "admin panel" in sidebar_text.lower():
        result("Payroll-RBAC-AdminLink", "FAIL", "Employee sidebar shows 'Admin Panel' link")
        bug("Payroll — Employee sidebar shows Admin Panel navigation link",
            "Employee (priya@technova.in) can see 'Admin Panel' in the payroll sidebar navigation.\n"
            "Even if the page restricts access, the link should not be visible to employees.\n\n"
            "**Sidebar items visible:** Dashboard, My Payslips, My Salary, My Tax, "
            "Declarations, My Leaves, Reimbursements, Profile, Admin Panel, Logout",
            "high")

    # ── RBAC: Can employee see other employees' salary? ──
    log("\n  --- RBAC: Other employees data ---")
    for path in ["/admin/employees", "/admin/payroll-runs", "/admin/salary-structures"]:
        driver.get(PAYROLL + path)
        time.sleep(3)
        sp_r = shot(driver, f"payroll_rbac{path.replace('/','_')}")
        text_r = get_text(driver)
        src_r = get_src(driver)
        if any(kw in src_r for kw in ["ananya", "employee list", "all employee", "salary structure"]):
            result(f"Payroll-RBAC-{path}", "FAIL", f"Admin data visible at {path}")
            bug(f"Payroll — Employee can access admin data at {path}",
                f"Employee can access {path} which may expose other employees' payroll data.",
                "critical", sp_r)
        else:
            result(f"Payroll-RBAC-{path}", "PASS", f"No admin data at {path}")

    shot(driver, "payroll_deep_done")


# ════════════════════════════════════════════════════════════
# PERFORMANCE — Deep Employee Test
# ════════════════════════════════════════════════════════════

def test_performance_deep(driver):
    log("\n" + "=" * 70)
    log("PERFORMANCE — Deep Employee Test (Direct Login)")
    log("=" * 70)

    PERF = "https://test-performance.empcloud.com"
    ok = module_login(driver, PERF)
    if not ok:
        result("Performance-Login", "FAIL", "Cannot login")
        return

    result("Performance-Login", "PASS", f"URL: {driver.current_url}")
    sp_dash = shot(driver, "perf_emp_dashboard")

    text = get_text(driver)
    log("  Dashboard:")
    for line in text.split('\n')[:30]:
        if line.strip(): log(f"    | {line.strip()}")

    # MAJOR RBAC CONCERN: Employee sees Review Cycles, PIPs, Analytics, Succession, Settings
    # These are typically admin-only features
    admin_sidebar_items = ["review cycles", "pips", "analytics", "9-box grid",
                           "skills gap", "succession", "settings", "competencies"]
    visible_admin = [item for item in admin_sidebar_items if item in text.lower()]

    if visible_admin:
        result("Performance-RBAC-Sidebar", "FAIL",
               f"Employee sees admin items in sidebar: {visible_admin}")
        bug("Performance — Employee can see admin-level navigation items (RBAC violation)",
            f"Employee (priya@technova.in) logged into Performance module sees these admin-level "
            f"sidebar items: {', '.join(visible_admin)}\n\n"
            "**Expected:** Employee should only see: My Reviews, My Goals, Self-Assessment, "
            "Feedback (give/receive), 1-on-1s\n\n"
            "**Actual sidebar shows:** Dashboard, Review Cycles, Goals, Goal Alignment, "
            "Competencies, PIPs, Career Paths, 1-on-1s, Feedback, Letters, Analytics, "
            "9-Box Grid, Skills Gap, Succession, Settings\n\n"
            "**Impact:** Employee may be able to access HR-only performance data including "
            "PIPs, 9-box grid, succession planning, and organizational analytics.",
            "critical", sp_dash)

    # ── Test each admin page ──
    admin_pages = {
        "/review-cycles": "Review Cycles",
        "/goals": "Goals",
        "/competencies": "Competencies",
        "/pips": "PIPs (Performance Improvement Plans)",
        "/career-paths": "Career Paths",
        "/one-on-ones": "1-on-1 Meetings",
        "/feedback": "Feedback",
        "/letters": "Letters",
        "/analytics": "Analytics",
        "/analytics/nine-box": "9-Box Grid",
        "/analytics/skills-gap": "Skills Gap Analysis",
        "/succession": "Succession Planning",
        "/settings": "Settings",
    }

    for path, name in admin_pages.items():
        driver.get(PERF + path)
        time.sleep(3)
        sp = shot(driver, f"perf_emp_{path.replace('/','_').strip('_')}")
        text = get_text(driver)
        src = get_src(driver)

        log(f"\n  --- {name} ({path}) ---")
        for line in text.split('\n')[:15]:
            if line.strip(): log(f"    | {line.strip()}")

        # Check if the page has real data or is restricted
        is_restricted = ("access denied" in src or "unauthorized" in src or
                        "forbidden" in src or "not authorized" in src)
        is_empty = len(text.strip()) < 100

        # Check specifically for other employees' data
        has_other_data = any(kw in src for kw in [
            "ananya", "other employee", "all employees", "team performance",
            "organization", "department review"
        ])

        if path in ["/analytics", "/analytics/nine-box", "/analytics/skills-gap",
                    "/succession", "/pips", "/settings"]:
            # These should NEVER be accessible to regular employees
            if not is_restricted and not is_empty:
                result(f"Performance-RBAC-{name}", "FAIL",
                       f"Employee can access {name} page with content")
                if path in ["/pips"]:
                    bug(f"Performance — Employee can access PIPs page",
                        f"Employee can access {path}. PIPs contain sensitive HR data.\n"
                        "**Expected:** Only HR/Manager should see PIPs.",
                        "critical", sp)
                elif path in ["/analytics", "/analytics/nine-box"]:
                    bug(f"Performance — Employee can access {name}",
                        f"Employee can access {path}. This shows org-wide performance analytics.\n"
                        "**Expected:** Only HR/Admin should see analytics.",
                        "critical", sp)
                elif path == "/succession":
                    bug(f"Performance — Employee can access Succession Planning",
                        f"Employee can access succession planning at {path}.\n"
                        "**Expected:** Only HR/Admin should see succession data.",
                        "critical", sp)
                elif path == "/settings":
                    bug(f"Performance — Employee can access module Settings",
                        f"Employee can access settings at {path}.\n"
                        "**Expected:** Only Admin should manage settings.",
                        "high", sp)
            else:
                result(f"Performance-RBAC-{name}", "PASS",
                       "Access restricted or page empty")
        elif path in ["/goals", "/feedback", "/one-on-ones"]:
            # These are expected for employees (own data)
            if not is_restricted:
                result(f"Performance-{name}", "PASS", f"Employee can access {name}")
            else:
                result(f"Performance-{name}", "FAIL", f"Employee cannot access {name}")

    # ── My Reviews ──
    log("\n  --- My Reviews ---")
    driver.get(PERF + "/review-cycles")
    time.sleep(3)
    sp_rev = shot(driver, "perf_my_reviews")
    text = get_text(driver)
    # Check if employee can see all review cycles or just their own
    if "create" in text.lower() or "new cycle" in text.lower():
        result("Performance-ReviewCycles-Create", "FAIL", "Employee can create review cycles")
        bug("Performance — Employee can create review cycles",
            "Employee sees 'Create' option on review cycles page.\n"
            "**Expected:** Only HR/Admin should manage review cycles.",
            "high", sp_rev)

    # ── Self Assessment ──
    log("\n  --- Self Assessment check ---")
    # Check if any review cycle has self-assessment for this employee
    src = get_src(driver)
    if "self" in src or "assessment" in src:
        result("Performance-SelfAssessment", "PASS", "Self-assessment references found")
    else:
        result("Performance-SelfAssessment", "INFO", "No self-assessment visible")

    # ── Can employee see OTHER employees' reviews? ──
    log("\n  --- RBAC: Other employees' data ---")
    # Check 9-box grid for other employee names
    driver.get(PERF + "/analytics/nine-box")
    time.sleep(3)
    sp_9box = shot(driver, "perf_9box_employee")
    text = get_text(driver)
    if "ananya" in text.lower() or "ravi" in text.lower():
        result("Performance-RBAC-OtherReviews", "FAIL",
               "Employee can see other employees on 9-box grid")
        bug("Performance — Employee can see other employees' performance data on 9-Box Grid",
            "Employee can access the 9-Box Grid at /analytics/nine-box which shows "
            "other employees' performance ratings.\n"
            "**Expected:** Employee should only see their own performance data.",
            "critical", sp_9box)

    shot(driver, "perf_deep_done")


# ════════════════════════════════════════════════════════════
# EXIT — Deep Employee Test
# ════════════════════════════════════════════════════════════

def test_exit_deep(driver):
    log("\n" + "=" * 70)
    log("EXIT — Deep Employee Test (Direct Login)")
    log("=" * 70)

    EXIT = "https://test-exit.empcloud.com"
    ok = module_login(driver, EXIT)
    if not ok:
        result("Exit-Login", "FAIL", "Cannot login")
        return

    result("Exit-Login", "PASS", f"URL: {driver.current_url}")
    sp_dash = shot(driver, "exit_emp_dashboard")

    text = get_text(driver)
    log("  Dashboard:")
    for line in text.split('\n')[:30]:
        if line.strip(): log(f"    | {line.strip()}")

    # MAJOR RBAC CONCERN: Employee sees full admin sidebar
    # Exits, Checklists, Clearance, Interviews, FnF, Notice Buyout, Assets, KT,
    # Letters, Alumni, Rehire, Analytics, Flight Risk, Settings
    admin_items = ["exits", "checklists", "clearance", "interviews", "fnf",
                   "notice buyout", "assets", "kt", "letters", "alumni",
                   "rehire", "analytics", "flight risk", "settings"]
    visible_admin = [item for item in admin_items if item in text.lower()]

    if len(visible_admin) > 5:
        result("Exit-RBAC-Sidebar", "FAIL",
               f"Employee sees admin sidebar: {visible_admin}")
        bug("Exit — Employee can see full admin navigation in Exit module (RBAC violation)",
            f"Employee (priya@technova.in) who is NOT in an exit process can see the full "
            f"admin sidebar: {', '.join(visible_admin)}\n\n"
            "**Expected:** Non-exiting employee should either:\n"
            "- Not have access to Exit module at all, OR\n"
            "- Only see 'Submit Resignation' option\n\n"
            "**Actual:** Full admin sidebar with Exits, Checklists, Clearance, FnF, "
            "Analytics, Flight Risk, Settings etc.\n\n"
            "**Impact:** Employee can potentially view other employees' exit data, "
            "FnF settlements, flight risk scores, and resignation details.",
            "critical", sp_dash)

    # ── Test each page ──
    exit_pages = {
        "/exits": "All Exits",
        "/checklists": "Checklists",
        "/clearance": "Clearance",
        "/interviews": "Exit Interviews",
        "/fnf": "Full and Final Settlement",
        "/buyout": "Notice Buyout",
        "/assets": "Assets Return",
        "/kt": "Knowledge Transfer",
        "/letters": "Letters",
        "/alumni": "Alumni Network",
        "/rehire": "Rehire",
        "/analytics": "Analytics",
        "/analytics/flight-risk": "Flight Risk",
        "/settings": "Settings",
    }

    for path, name in exit_pages.items():
        driver.get(EXIT + path)
        time.sleep(3)
        sp = shot(driver, f"exit_emp_{path.replace('/','_').strip('_')}")
        text = get_text(driver)
        src = get_src(driver)

        log(f"\n  --- {name} ({path}) ---")
        for line in text.split('\n')[:15]:
            if line.strip(): log(f"    | {line.strip()}")

        is_restricted = "access denied" in src or "unauthorized" in src or "forbidden" in src
        has_other_data = any(kw in src for kw in ["ananya", "other employee", "all employee"])

        if path in ["/exits", "/clearance", "/fnf", "/interviews", "/analytics",
                    "/analytics/flight-risk", "/settings", "/rehire"]:
            if not is_restricted:
                result(f"Exit-RBAC-{name}", "FAIL", f"Employee can access {name}")
                # Only file bug for the most critical ones to avoid spam
                if path == "/fnf":
                    bug("Exit — Employee can access Full and Final Settlement data",
                        f"Employee can access FnF page. This may show other employees' "
                        "settlement amounts.\n**Expected:** Only HR should access FnF.",
                        "critical", sp)
                elif path == "/analytics/flight-risk":
                    bug("Exit — Employee can access Flight Risk analytics",
                        f"Employee can access flight risk scores, which are sensitive "
                        "HR analytics.\n**Expected:** Only HR/Manager should see this.",
                        "critical", sp)
                elif path == "/exits":
                    bug("Exit — Employee can see all exit records",
                        f"Employee can access /exits showing all exit records.\n"
                        "**Expected:** Employee should only see their own exit if applicable.",
                        "critical", sp)
            else:
                result(f"Exit-RBAC-{name}", "PASS", "Restricted")

    shot(driver, "exit_deep_done")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    log("=" * 70)
    log("DEEP EMPLOYEE MODULE TESTS")
    log(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    # Test 1: Payroll
    driver = create_driver()
    try:
        test_payroll_deep(driver)
    except Exception as e:
        log(f"Payroll error: {e}")
        import traceback; traceback.print_exc()
    finally:
        driver.quit()

    # Test 2: Performance (fresh driver)
    driver = create_driver()
    try:
        test_performance_deep(driver)
    except Exception as e:
        log(f"Performance error: {e}")
        import traceback; traceback.print_exc()
    finally:
        driver.quit()

    # Test 3: Exit (fresh driver)
    driver = create_driver()
    try:
        test_exit_deep(driver)
    except Exception as e:
        log(f"Exit error: {e}")
        import traceback; traceback.print_exc()
    finally:
        driver.quit()

    # ── Summary ──
    log("\n" + "=" * 70)
    log("DEEP TEST RESULTS")
    log("=" * 70)

    passes = [r for r in test_results if r["status"] == "PASS"]
    fails = [r for r in test_results if r["status"] == "FAIL"]
    infos = [r for r in test_results if r["status"] == "INFO"]

    log(f"  PASS: {len(passes)}  |  FAIL: {len(fails)}  |  INFO: {len(infos)}")
    log(f"  Bugs: {len(bugs_found)}")

    for r in test_results:
        log(f"  [{r['status']}] {r['test']}: {r['details']}")

    log("\n  BUGS:")
    for b in bugs_found:
        log(f"  [{b['severity'].upper()}] {b['title']}")

    # Upload screenshots and file bugs
    log("\n--- Uploading & filing ---")
    uploaded = {}
    shots_to_upload = [f for f in os.listdir(SCREENSHOT_DIR) if f.endswith(".png") and
                       any(kw in f for kw in ["payroll_emp", "payroll_my", "payroll_admin",
                           "payroll_rbac", "perf_emp", "perf_9box", "perf_my",
                           "exit_emp", "exit_deep"])]
    for fname in shots_to_upload[:25]:
        fpath = os.path.join(SCREENSHOT_DIR, fname)
        url = upload_screenshot_github(fpath)
        if url:
            uploaded[fname] = url
        time.sleep(0.5)

    log(f"  Uploaded {len(uploaded)} screenshots")

    for b in bugs_found:
        body = b["description"] + "\n\n"
        body += f"**Severity:** {b['severity']}\n"
        body += f"**User:** priya@technova.in\n**Role:** Employee\n"
        body += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        if b.get("screenshot"):
            fname = os.path.basename(b["screenshot"])
            if fname in uploaded:
                body += f"\n**Screenshot:**\n![{fname}]({uploaded[fname]})\n"
        labels = ["bug"]
        if b["severity"] == "critical":
            labels.append("critical")
        file_github_issue(b["title"], body, labels)
        time.sleep(1)

    # Save results
    with open(os.path.join(SCREENSHOT_DIR, "deep_test_results.json"), "w") as f:
        json.dump({"test_results": test_results, "bugs_found": [
            {k:v for k,v in b.items() if k != "screenshot"} for b in bugs_found
        ]}, f, indent=2)

    log("\nDONE")


if __name__ == "__main__":
    main()
