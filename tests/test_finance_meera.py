#!/usr/bin/env python3
"""
EMP Cloud HRMS - Finance Manager (Meera Sharma) Month-End Test Suite
=====================================================================
Persona: Meera Sharma, Finance Manager at TechNova Solutions
Focus: Payroll processing, billing, tax compliance, reimbursements,
       full & final settlement, statutory compliance, audit trails.

Tests both UI (Selenium + SSO) and API endpoints.
Files GitHub issues for every genuine bug found.
"""

import sys, os, time, json, traceback, ssl, re, base64
import urllib.request, urllib.error, urllib.parse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Configuration ────────────────────────────────────────────────────────────
MAIN_URL       = "https://test-empcloud.empcloud.com"
PAYROLL_URL    = "https://testpayroll.empcloud.com"
PAYROLL_API    = "https://testpayroll-api.empcloud.com"
MAIN_API       = "https://test-empcloud-api.empcloud.com"
SCREENSHOT_DIR = r"C:\emptesting\screenshots\finance_meera"
GITHUB_PAT     = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO    = "EmpCloud/EmpCloud"

CREDS = {
    "org_admin":   {"email": "ananya@technova.in",  "password": "Welcome@123"},
    "employee":    {"email": "priya@technova.in",    "password": "Welcome@123"},
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
bugs_found   = []
test_results = []
driver_count = 0
MAX_TESTS_PER_DRIVER = 3

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ── Helpers ──────────────────────────────────────────────────────────────────
def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def shot(drv, name):
    p = os.path.join(SCREENSHOT_DIR, f"{name}_{ts()}.png")
    try:
        drv.save_screenshot(p)
        print(f"    [SS] {p}")
        return p
    except Exception:
        return None

def log_result(name, status, details=""):
    test_results.append({"test": name, "status": status, "details": details})
    icon = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "SKIP")
    print(f"  [{icon}] {name}: {details}")

def record_bug(title, desc, severity, sp=None):
    bugs_found.append({
        "title": title, "description": desc,
        "severity": severity, "screenshot": sp
    })
    print(f"  [BUG-{severity.upper()}] {title}")

def upload_screenshot_to_github(filepath):
    """Upload screenshot to repo and return markdown image link."""
    if not filepath or not os.path.isfile(filepath):
        return ""
    try:
        fname = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        path = f"screenshots/finance_meera/{fname}"
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
        data = json.dumps({
            "message": f"Screenshot: {fname}",
            "content": content,
            "branch": "main"
        }).encode()
        req = urllib.request.Request(url, data=data, method="PUT", headers={
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "EmpCloud-Finance-Tester",
            "Content-Type": "application/json",
        })
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        result = json.loads(resp.read().decode())
        dl = result.get("content", {}).get("download_url", "")
        if dl:
            return f"\n\n**Screenshot:**\n![{fname}]({dl})"
    except Exception as e:
        print(f"    [SS-UPLOAD] Failed: {e}")
    return ""

def file_github_issue(title, body, labels=None):
    if labels is None:
        labels = ["bug"]
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    data = json.dumps({"title": title, "body": body, "labels": labels}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-Finance-Tester",
        "Content-Type": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        result = json.loads(resp.read().decode())
        print(f"    [GITHUB] Issue #{result.get('number')} -> {result.get('html_url')}")
        return result
    except urllib.error.HTTPError as e:
        print(f"    [GITHUB-ERR] {e.code}: {(e.read().decode() if e.fp else '')[:300]}")
    except Exception as e:
        print(f"    [GITHUB-ERR] {e}")
    return None

def api_get(url, token=None):
    headers = {
        "User-Agent": "EmpCloud-Finance-Tester",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        return resp.status, json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:500]}
    except Exception as e:
        return 0, {"error": str(e)}

def api_post(url, payload, token=None):
    headers = {
        "User-Agent": "EmpCloud-Finance-Tester",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        return resp.status, json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:500]}
    except Exception as e:
        return 0, {"error": str(e)}

def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in [
        "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
        "--disable-gpu", "--window-size=1920,1080",
        "--ignore-certificate-errors",
    ]:
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
    if "login" in url.lower() and "/login" in url.lower():
        return False, "still_on_login"
    return True, "ok"

def extract_token(driver):
    """Extract auth token from localStorage."""
    try:
        keys = driver.execute_script("return Object.keys(localStorage);")
        for k in (keys or []):
            val = driver.execute_script(f"return localStorage.getItem('{k}');")
            if val and ("auth" in k.lower() or "token" in k.lower() or "user" in k.lower()):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        state = parsed.get("state", parsed)
                        if isinstance(state, dict):
                            tok = (state.get("accessToken") or state.get("token")
                                   or state.get("access_token"))
                            if tok and len(tok) > 20:
                                return tok
                except (json.JSONDecodeError, AttributeError):
                    if len(val) > 50 and val.count('.') == 2:
                        return val
    except Exception:
        pass
    return None

def get_cookies_dict(driver):
    """Get cookies as dict for session transfer."""
    return {c['name']: c['value'] for c in driver.get_cookies()}

def find_sso_payroll_link(driver):
    """Find SSO link to payroll module from the main dashboard sidebar."""
    try:
        links = driver.find_elements(By.TAG_NAME, "a")
        for a in links:
            href = a.get_attribute("href") or ""
            if "testpayroll" in href and "sso_token" in href:
                return href
            if "payroll" in href.lower():
                text = a.text.strip()
                if text:
                    return href
    except Exception:
        pass
    return None

def search_page_for(driver, keywords):
    """Search page source for keywords, return dict of found/not-found."""
    src = driver.page_source.lower()
    results = {}
    for kw in keywords:
        results[kw] = kw.lower() in src
    return results

def safe_find_elements(driver, by, value):
    try:
        return driver.find_elements(by, value)
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST BATCH 1: Payroll Module SSO + Dashboard (uses driver #1)
# ═══════════════════════════════════════════════════════════════════════════════

def batch1_payroll_sso_and_dashboard():
    """
    T1: SSO to Payroll from main dashboard
    T2: Payroll dashboard - salary details visibility
    T3: Run Payroll button / process
    """
    print("\n" + "=" * 70)
    print("  BATCH 1: Payroll SSO, Dashboard, Run Payroll")
    print("=" * 70)

    driver = create_driver()
    payroll_token = None
    try:
        # ── T1: Login + SSO to Payroll ──
        ok, reason = do_login(driver, CREDS["org_admin"]["email"],
                              CREDS["org_admin"]["password"], "finance_oa")
        if not ok:
            log_result("T1-Login", "FAIL", f"Login failed: {reason}")
            return None
        log_result("T1-Login", "PASS", "Org admin logged in")

        main_token = extract_token(driver)
        print(f"    Main token: {'found' if main_token else 'NOT found'}")

        # Look for payroll SSO link
        sso_link = find_sso_payroll_link(driver)
        sp1 = shot(driver, "T1_main_dashboard")

        if sso_link:
            log_result("T1-SSO-Link", "PASS", f"Payroll link found: {sso_link[:80]}")
            driver.get(sso_link)
            time.sleep(6)
            sp2 = shot(driver, "T1_payroll_after_sso")
            cur = driver.current_url
            src_lower = driver.page_source.lower()

            # Check if we actually landed on payroll
            if "testpayroll" in cur:
                log_result("T1-SSO-Navigate", "PASS", f"On payroll: {cur}")
                payroll_token = extract_token(driver)

                # Check for error pages
                if "not found" in src_lower or "404" in src_lower or "error" in src_lower:
                    log_result("T1-SSO-Content", "FAIL", "Payroll page shows error")
                    record_bug(
                        "Payroll module SSO lands on error page",
                        "**Persona:** Meera Sharma, Finance Manager\n\n"
                        "**Steps:**\n1. Login as org admin\n2. Click Payroll SSO link from sidebar\n3. Page loads with error\n\n"
                        f"**URL:** {cur}\n"
                        f"**Expected:** Payroll dashboard with salary overview\n"
                        f"**Actual:** Error page displayed",
                        "high", sp2
                    )
            else:
                log_result("T1-SSO-Navigate", "FAIL", f"Not on payroll: {cur}")
        else:
            log_result("T1-SSO-Link", "FAIL", "No payroll SSO link found in sidebar")
            # Try direct navigation
            driver.get(PAYROLL_URL)
            time.sleep(5)
            sp2 = shot(driver, "T1_payroll_direct")
            cur = driver.current_url
            if "login" in cur.lower():
                log_result("T1-Payroll-Direct", "FAIL", "Redirected to login -- no SSO")

        # ── T2: Check salary details visibility ──
        print("\n  -- T2: Salary Details Visibility --")
        # Try payroll pages
        payroll_pages = [
            ("/dashboard", "Dashboard"),
            ("/employees", "Employee Salary List"),
            ("/payslips", "Payslips"),
            ("/salary-structure", "Salary Structure"),
            ("/salary-components", "Salary Components"),
            ("/my/salary", "My Salary"),
            ("/my/payslips", "My Payslips"),
            ("/pay-runs", "Pay Runs"),
            ("/run-payroll", "Run Payroll"),
            ("/payroll/run", "Payroll Run"),
            ("/admin/payroll", "Admin Payroll"),
        ]

        pages_accessible = 0
        salary_data_found = False
        run_payroll_found = False

        for path, name in payroll_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                cur = driver.current_url
                src = driver.page_source
                src_lower = src.lower()
                sp = shot(driver, f"T2_payroll_{name.replace(' ','_')}")

                is_error = ("404" in src_lower or "not found" in src_lower
                           or "unauthorized" in src_lower or "forbidden" in src_lower)

                if not is_error and "login" not in cur.lower():
                    pages_accessible += 1
                    print(f"    [OK] {name}: {cur}")

                    # Check for salary data
                    salary_keywords = ["basic", "hra", "gross", "net", "ctc",
                                      "salary", "deduction", "allowance", "payslip"]
                    for kw in salary_keywords:
                        if kw in src_lower:
                            salary_data_found = True
                            break

                    # Check for run payroll
                    if ("run payroll" in src_lower or "process payroll" in src_lower
                        or "generate payroll" in src_lower):
                        run_payroll_found = True
                        print(f"    >>> FOUND 'Run Payroll' on {name}")
                else:
                    print(f"    [--] {name}: error or redirect ({cur})")
            except Exception as ex:
                print(f"    [ERR] {name}: {ex}")

        if pages_accessible == 0:
            log_result("T2-Salary-Visibility", "FAIL", "No payroll pages accessible")
            record_bug(
                "Finance Manager cannot access any payroll pages via SSO",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin (ananya@technova.in)\n2. SSO to payroll module\n3. Navigate to dashboard, employees, payslips pages\n\n"
                "**Expected:** Payroll pages should load with salary data for all employees\n"
                "**Actual:** No payroll pages are accessible. All return errors or redirect to login.\n\n"
                "**Impact:** Finance manager cannot view or process payroll at all. Month-end payroll processing is blocked.",
                "critical", sp1
            )
        else:
            log_result("T2-Salary-Visibility", "PASS" if salary_data_found else "FAIL",
                       f"{pages_accessible} pages accessible, salary data: {salary_data_found}")

        if not salary_data_found and pages_accessible > 0:
            record_bug(
                "Payroll pages load but show no salary data for employees",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll module\n3. Check dashboard, employee salary, payslips pages\n\n"
                "**Expected:** Salary details (basic, HRA, gross, net, deductions) visible for employees\n"
                "**Actual:** Pages load but contain no salary data. Cannot verify employee compensation.\n\n"
                "**Impact:** Finance team cannot review salary structures or validate payroll data.",
                "high", sp2 if 'sp2' in dir() else sp1
            )

        # ── T3: Run Payroll ──
        print("\n  -- T3: Run Payroll Process --")
        if not run_payroll_found:
            log_result("T3-RunPayroll", "FAIL", "No 'Run Payroll' button/link found on any page")
            record_bug(
                "Cannot run monthly payroll -- no Run Payroll button found",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll module\n3. Check all payroll pages: dashboard, pay-runs, run-payroll, admin/payroll\n\n"
                "**Expected:** A 'Run Payroll' or 'Process Payroll' button to initiate monthly payroll processing\n"
                "**Actual:** No such button exists on any payroll page. Month-end payroll cannot be initiated.\n\n"
                f"**Pages checked:** {', '.join([p[1] for p in payroll_pages])}\n\n"
                "**Impact:** Critical blocker for Finance -- monthly payroll processing is impossible.",
                "critical", sp1
            )
        else:
            log_result("T3-RunPayroll", "PASS", "Run Payroll option found")

        return payroll_token or main_token

    except Exception as ex:
        print(f"  [EXCEPTION] Batch 1: {ex}")
        traceback.print_exc()
        shot(driver, "batch1_exception")
        return None
    finally:
        driver.quit()


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST BATCH 2: Payslips, Tax, Leave Impact (uses driver #2)
# ═══════════════════════════════════════════════════════════════════════════════

def batch2_payslips_tax_leave():
    """
    T4: Individual payslips -- gross, net, deductions, tax
    T5: Tax computation -- TDS, PF, ESI
    T6: Leave impact on payroll -- LOP deductions
    """
    print("\n" + "=" * 70)
    print("  BATCH 2: Payslips, Tax Computation, Leave Impact")
    print("=" * 70)

    driver = create_driver()
    try:
        ok, reason = do_login(driver, CREDS["org_admin"]["email"],
                              CREDS["org_admin"]["password"], "finance_b2")
        if not ok:
            log_result("T4-Login", "FAIL", f"Login failed: {reason}")
            return
        log_result("T4-Login", "PASS", "Logged in for batch 2")

        token = extract_token(driver)

        # SSO to payroll
        sso = find_sso_payroll_link(driver)
        if sso:
            driver.get(sso)
            time.sleep(5)
        else:
            driver.get(PAYROLL_URL)
            time.sleep(5)

        # ── T4: Individual Payslips ──
        print("\n  -- T4: Individual Payslips --")
        payslip_pages = ["/my/payslips", "/payslips", "/pay-slips",
                         "/payslips/list", "/employee/payslips"]
        payslip_found = False
        payslip_has_components = False

        for path in payslip_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T4_payslip_{path.replace('/','_')}")

                if "404" not in src and "not found" not in src:
                    payslip_found = True
                    # Check for payslip components
                    components = {
                        "gross": "gross" in src,
                        "net": "net" in src or "take home" in src,
                        "basic": "basic" in src,
                        "deduction": "deduction" in src,
                        "tax": "tax" in src or "tds" in src,
                        "pf": "pf" in src or "provident" in src,
                    }
                    found_components = [k for k, v in components.items() if v]
                    if found_components:
                        payslip_has_components = True
                        print(f"    Payslip components found: {found_components}")
                    break
            except Exception:
                pass

        if not payslip_found:
            log_result("T4-Payslips", "FAIL", "No payslip page accessible")
            record_bug(
                "Individual payslips not accessible -- no payslip page found",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll\n3. Navigate to payslip pages\n\n"
                "**Expected:** List of employee payslips with gross, net, deductions, tax breakdown\n"
                "**Actual:** No payslip page found or accessible.\n\n"
                "**Impact:** Cannot verify individual employee compensation. Employees cannot view their payslips.",
                "high", sp
            )
        elif not payslip_has_components:
            log_result("T4-Payslips", "FAIL", "Payslip page exists but no salary components shown")
            record_bug(
                "Payslip page missing salary components -- no gross, net, deductions breakdown",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll\n3. Open payslips page\n\n"
                "**Expected:** Payslips showing gross salary, net salary, basic, HRA, deductions, tax\n"
                "**Actual:** Payslip page loads but shows no salary component breakdown.\n\n"
                "**Impact:** Finance team cannot validate payroll accuracy. Employees cannot verify their pay.",
                "high", sp
            )
        else:
            log_result("T4-Payslips", "PASS", f"Payslip with components: {found_components}")

        # ── T5: Tax Computation (TDS, PF, ESI) ──
        print("\n  -- T5: Tax Computation --")
        tax_pages = ["/my/tax", "/tax", "/tax-computation", "/tds",
                     "/statutory", "/compliance", "/settings/statutory"]
        tax_found = False
        tax_details = {}

        for path in tax_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T5_tax_{path.replace('/','_')}")

                if "404" not in src and "not found" not in src and "error" not in src[:200]:
                    tax_found = True
                    tax_details = {
                        "tds": "tds" in src or "tax deducted" in src,
                        "pf": "pf" in src or "provident fund" in src or "epf" in src,
                        "esi": "esi" in src or "employee state insurance" in src,
                        "pt": "professional tax" in src or "pt" in src,
                        "slabs": "slab" in src or "regime" in src,
                    }
                    found_tax = [k for k, v in tax_details.items() if v]
                    if found_tax:
                        print(f"    Tax details found: {found_tax}")
                        break
            except Exception:
                pass

        if not tax_found:
            log_result("T5-TaxComputation", "FAIL", "No tax computation page accessible")
            record_bug(
                "Tax computation page missing -- cannot verify TDS, PF, ESI calculations",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll\n3. Navigate to tax/statutory pages\n\n"
                "**Expected:** Tax computation page showing TDS calculation, PF/ESI rates, slabs\n"
                "**Actual:** No tax computation page accessible.\n\n"
                "**Impact:** Cannot verify statutory compliance. TDS, PF, ESI calculations cannot be audited.\n"
                "Finance team needs this to ensure correct deductions before filing returns.",
                "high", sp
            )
        else:
            found_tax = [k for k, v in tax_details.items() if v]
            if not found_tax:
                log_result("T5-TaxComputation", "FAIL", "Tax page exists but no TDS/PF/ESI details")
            else:
                log_result("T5-TaxComputation", "PASS", f"Tax details: {found_tax}")

        # ── T6: Leave Impact on Payroll (LOP) ──
        print("\n  -- T6: Leave Impact on Payroll (LOP) --")
        lop_pages = ["/my/leaves", "/leaves", "/leave-impact",
                     "/attendance/leave", "/payroll/leave-impact"]
        lop_found = False

        for path in lop_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T6_lop_{path.replace('/','_')}")

                if "404" not in src and "not found" not in src:
                    lop_keywords = ["loss of pay", "lop", "leave without pay", "lwp",
                                   "unpaid leave", "leave deduction", "leave impact"]
                    for kw in lop_keywords:
                        if kw in src:
                            lop_found = True
                            print(f"    LOP related content found: '{kw}'")
                            break
            except Exception:
                pass

        if not lop_found:
            log_result("T6-LOPImpact", "FAIL", "No LOP/leave impact on payroll visible")
            record_bug(
                "Leave impact on payroll not visible -- LOP salary deduction unclear",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll\n3. Look for leave impact / LOP deductions in payroll\n\n"
                "**Expected:** LOP (Loss of Pay) leaves should show corresponding salary deductions in payroll.\n"
                "Per-day rate should be visible and deduction amount should match leave days.\n"
                "**Actual:** No leave-impact-on-payroll section found. Cannot verify if LOP deductions are applied.\n\n"
                "**Impact:** Employees on unpaid leave may get full salary. Finance cannot cross-verify leave vs payroll.",
                "medium", sp
            )
        else:
            log_result("T6-LOPImpact", "PASS", "LOP/leave impact content visible")

    except Exception as ex:
        print(f"  [EXCEPTION] Batch 2: {ex}")
        traceback.print_exc()
        shot(driver, "batch2_exception")
    finally:
        driver.quit()


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST BATCH 3: OT, Billing, Module Costs (uses driver #3)
# ═══════════════════════════════════════════════════════════════════════════════

def batch3_overtime_billing_costs():
    """
    T7: Overtime pay
    T8: Billing/subscription costs
    T9: Module-wise cost breakdown
    """
    print("\n" + "=" * 70)
    print("  BATCH 3: Overtime, Billing, Module Costs")
    print("=" * 70)

    driver = create_driver()
    try:
        ok, reason = do_login(driver, CREDS["org_admin"]["email"],
                              CREDS["org_admin"]["password"], "finance_b3")
        if not ok:
            log_result("T7-Login", "FAIL", f"Login failed: {reason}")
            return
        log_result("T7-Login", "PASS", "Logged in for batch 3")

        token = extract_token(driver)

        # SSO to payroll
        sso = find_sso_payroll_link(driver)
        if sso:
            driver.get(sso)
            time.sleep(5)

        # ── T7: Overtime Pay ──
        print("\n  -- T7: Overtime Pay --")
        ot_pages = ["/overtime", "/ot", "/attendance/overtime",
                    "/payroll/overtime", "/my/overtime"]
        ot_found = False

        for path in ot_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T7_ot_{path.replace('/','_')}")
                if "overtime" in src or "ot " in src or "extra hours" in src:
                    ot_found = True
                    print(f"    OT content found on {path}")
                    break
            except Exception:
                pass

        # Also check main payroll dashboard for OT
        if not ot_found:
            try:
                driver.get(PAYROLL_URL + "/dashboard")
                time.sleep(3)
                src = driver.page_source.lower()
                if "overtime" in src:
                    ot_found = True
            except Exception:
                pass

        if not ot_found:
            log_result("T7-OvertimePay", "FAIL", "No overtime pay section found in payroll")
            record_bug(
                "No overtime pay tracking in payroll -- OT hours not reflected in salary",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll\n3. Search for overtime/OT section in payroll pages\n\n"
                "**Expected:** Overtime section showing OT hours, rates, and additions to salary\n"
                "**Actual:** No overtime tracking found in payroll module.\n\n"
                "**Impact:** Employees working overtime are not getting compensated. "
                "Finance cannot track OT costs against department budgets.",
                "medium", sp
            )
        else:
            log_result("T7-OvertimePay", "PASS", "Overtime section found")

        # ── T8: Billing / Subscription Costs ──
        print("\n  -- T8: Billing / Subscription Costs --")
        # Navigate back to main app for billing
        driver.get(MAIN_URL)
        time.sleep(4)
        do_login(driver, CREDS["org_admin"]["email"],
                 CREDS["org_admin"]["password"], "finance_billing")
        time.sleep(3)

        billing_pages = [
            (MAIN_URL + "/billing", "Billing"),
            (MAIN_URL + "/subscription", "Subscription"),
            (MAIN_URL + "/settings/billing", "Settings Billing"),
            (MAIN_URL + "/admin/billing", "Admin Billing"),
            (MAIN_URL + "/marketplace", "Marketplace"),
            (MAIN_URL + "/settings/subscription", "Settings Subscription"),
        ]

        billing_found = False
        cost_visible = False

        for url, name in billing_pages:
            try:
                driver.get(url)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T8_billing_{name.replace(' ','_')}")

                if "404" not in src and "not found" not in src:
                    cost_keywords = ["plan", "price", "cost", "subscription",
                                    "billing", "invoice", "amount", "$", "inr", "per month",
                                    "per user", "annual", "monthly"]
                    for kw in cost_keywords:
                        if kw in src:
                            billing_found = True
                            if kw in ["$", "inr", "amount", "price", "cost", "per month", "per user"]:
                                cost_visible = True
                            break
                    if billing_found:
                        print(f"    Billing content found on {name}")
                        break
            except Exception:
                pass

        # Also try API
        if token:
            for endpoint in ["/billing", "/subscription", "/subscriptions",
                            "/billing/invoices", "/billing/plan"]:
                code, data = api_get(MAIN_API + "/api/v1" + endpoint, token)
                if code == 200:
                    billing_found = True
                    print(f"    API {endpoint}: {json.dumps(data)[:200]}")
                    break
                code2, data2 = api_get(PAYROLL_API + "/api/v1" + endpoint, token)
                if code2 == 200:
                    billing_found = True
                    print(f"    Payroll API {endpoint}: {json.dumps(data2)[:200]}")
                    break

        if not billing_found:
            log_result("T8-Billing", "FAIL", "No billing/subscription page found")
            record_bug(
                "Cannot view billing or subscription costs -- no billing page accessible",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. Navigate to billing, subscription, marketplace pages\n3. Also checked via API\n\n"
                "**Expected:** Billing page showing TechNova's subscription plan, cost, and payment history\n"
                "**Actual:** No billing page found. Cannot determine how much TechNova is paying for EMP Cloud.\n\n"
                f"**Pages checked:** {', '.join([p[1] for p in billing_pages])}\n\n"
                "**Impact:** Finance cannot track SaaS subscription costs or plan renewals.",
                "high", sp
            )
        elif not cost_visible:
            log_result("T8-Billing", "FAIL", "Billing page found but no cost/pricing visible")
        else:
            log_result("T8-Billing", "PASS", "Billing with cost info visible")

        # ── T9: Module-wise Cost Breakdown ──
        print("\n  -- T9: Module-wise Cost Breakdown --")
        module_cost_found = False

        # Check marketplace for per-module pricing
        try:
            driver.get(MAIN_URL + "/marketplace")
            time.sleep(4)
            src = driver.page_source.lower()
            sp = shot(driver, "T9_marketplace")

            modules_with_price = []
            module_names = ["payroll", "recruit", "performance", "rewards",
                           "exit", "lms", "project", "monitor"]
            for mod in module_names:
                if mod in src:
                    # Check if there's a price near it
                    idx = src.find(mod)
                    nearby = src[max(0,idx-100):idx+200]
                    if any(p in nearby for p in ["$", "inr", "price", "per user", "per month", "free"]):
                        modules_with_price.append(mod)
                        module_cost_found = True

            if modules_with_price:
                print(f"    Modules with pricing: {modules_with_price}")
                log_result("T9-ModuleCosts", "PASS", f"Module pricing found: {modules_with_price}")
            else:
                log_result("T9-ModuleCosts", "FAIL", "No per-module cost breakdown visible")
        except Exception as ex:
            log_result("T9-ModuleCosts", "FAIL", f"Error checking marketplace: {ex}")

    except Exception as ex:
        print(f"  [EXCEPTION] Batch 3: {ex}")
        traceback.print_exc()
        shot(driver, "batch3_exception")
    finally:
        driver.quit()


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST BATCH 4: Reports, Bank Details, Reimbursements (uses driver #4)
# ═══════════════════════════════════════════════════════════════════════════════

def batch4_reports_bank_reimbursements():
    """
    T10: Download payroll reports (Excel/CSV export)
    T11: Employee bank details
    T12: Reimbursement claims
    """
    print("\n" + "=" * 70)
    print("  BATCH 4: Reports Export, Bank Details, Reimbursements")
    print("=" * 70)

    driver = create_driver()
    try:
        ok, reason = do_login(driver, CREDS["org_admin"]["email"],
                              CREDS["org_admin"]["password"], "finance_b4")
        if not ok:
            log_result("T10-Login", "FAIL", f"Login failed: {reason}")
            return
        log_result("T10-Login", "PASS", "Logged in for batch 4")

        token = extract_token(driver)

        # SSO to payroll
        sso = find_sso_payroll_link(driver)
        if sso:
            driver.get(sso)
            time.sleep(5)

        # ── T10: Download Payroll Reports ──
        print("\n  -- T10: Payroll Reports Export --")
        report_pages = ["/reports", "/payroll/reports", "/my/reports",
                       "/admin/reports", "/export", "/downloads"]
        export_found = False

        for path in report_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T10_report_{path.replace('/','_')}")

                if "404" not in src and "not found" not in src:
                    export_keywords = ["export", "download", "csv", "excel", "pdf",
                                      "report", "generate report"]
                    for kw in export_keywords:
                        if kw in src:
                            export_found = True
                            print(f"    Export option found: '{kw}' on {path}")
                            break
                if export_found:
                    break
            except Exception:
                pass

        # Also check buttons on main payroll pages
        if not export_found:
            for path in ["/dashboard", "/payslips", "/employees"]:
                try:
                    driver.get(PAYROLL_URL + path)
                    time.sleep(3)
                    src = driver.page_source.lower()
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        txt = btn.text.lower()
                        if any(kw in txt for kw in ["export", "download", "csv", "excel"]):
                            export_found = True
                            print(f"    Export button found: '{btn.text}' on {path}")
                            break
                    if export_found:
                        break
                except Exception:
                    pass

        if not export_found:
            log_result("T10-ReportsExport", "FAIL", "No payroll report export/download option found")
            record_bug(
                "Cannot download payroll reports -- no export to Excel or CSV option",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll\n3. Check reports, dashboard, payslips pages for export option\n\n"
                "**Expected:** Option to export payroll data to Excel/CSV/PDF for month-end reporting\n"
                "**Actual:** No export, download, or report generation option found anywhere in payroll module.\n\n"
                f"**Pages checked:** {', '.join([p for p in [pp for pp in ['/reports','/payroll/reports','/dashboard','/payslips','/employees']]])}\n\n"
                "**Impact:** Finance team cannot generate payroll reports for management or auditors. "
                "Manual data extraction required.",
                "high", sp
            )
        else:
            log_result("T10-ReportsExport", "PASS", "Export option available")

        # ── T11: Employee Bank Details ──
        print("\n  -- T11: Employee Bank Details --")
        bank_pages = ["/bank-details", "/employee/bank", "/my/bank",
                     "/settings/bank", "/employees"]
        bank_found = False

        for path in bank_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T11_bank_{path.replace('/','_')}")

                bank_keywords = ["bank", "account number", "ifsc", "branch",
                                "bank name", "account holder", "upi"]
                for kw in bank_keywords:
                    if kw in src:
                        bank_found = True
                        print(f"    Bank details found: '{kw}' on {path}")
                        break
                if bank_found:
                    break
            except Exception:
                pass

        # Also check main app employee profiles
        if not bank_found and token:
            code, data = api_get(MAIN_API + "/api/v1/employees", token)
            if code == 200 and isinstance(data, (list, dict)):
                employees = data if isinstance(data, list) else data.get("data", data.get("employees", []))
                if isinstance(employees, list) and employees:
                    emp_id = employees[0].get("id") or employees[0].get("_id")
                    if emp_id:
                        code2, emp = api_get(MAIN_API + f"/api/v1/employees/{emp_id}", token)
                        if code2 == 200:
                            emp_data = emp if isinstance(emp, dict) else {}
                            bank_keys = ["bank", "account", "ifsc", "bank_name", "bank_details"]
                            for bk in bank_keys:
                                if bk in str(emp_data).lower():
                                    bank_found = True
                                    print(f"    Bank data in employee API: {bk}")
                                    break

        if not bank_found:
            log_result("T11-BankDetails", "FAIL", "No employee bank details found")
            record_bug(
                "Employee bank details not stored or accessible -- payroll disbursement blocked",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. Check payroll module and employee profiles for bank details\n3. Also checked API employee endpoints\n\n"
                "**Expected:** Employee bank account details (account number, IFSC, bank name) stored for salary disbursement\n"
                "**Actual:** No bank detail fields found in payroll module or employee profiles.\n\n"
                "**Impact:** Cannot process salary payments. Bank transfer files cannot be generated.",
                "high", sp
            )
        else:
            log_result("T11-BankDetails", "PASS", "Bank details accessible")

        # ── T12: Reimbursement Claims ──
        print("\n  -- T12: Reimbursement Claims --")
        reimb_pages = ["/reimbursements", "/claims", "/my/reimbursements",
                      "/my/claims", "/expense", "/expenses",
                      "/reimbursement/claims", "/my/expenses"]
        reimb_found = False

        for path in reimb_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T12_reimb_{path.replace('/','_')}")

                reimb_keywords = ["reimbursement", "claim", "expense",
                                 "receipt", "submit claim", "approve"]
                for kw in reimb_keywords:
                    if kw in src:
                        reimb_found = True
                        print(f"    Reimbursement content found: '{kw}' on {path}")
                        break
                if reimb_found:
                    break
            except Exception:
                pass

        # Also check main app
        if not reimb_found:
            for path in ["/reimbursements", "/claims", "/expenses"]:
                try:
                    driver.get(MAIN_URL + path)
                    time.sleep(3)
                    src = driver.page_source.lower()
                    if "reimbursement" in src or "claim" in src or "expense" in src:
                        reimb_found = True
                        break
                except Exception:
                    pass

        if not reimb_found:
            log_result("T12-Reimbursements", "FAIL", "No reimbursement/claims section found")
            record_bug(
                "No reimbursement claims module -- employees cannot submit expense claims",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. Check payroll and main app for reimbursement/claims/expense pages\n\n"
                "**Expected:** Reimbursement module where employees submit claims and finance processes them\n"
                "**Actual:** No reimbursement or expense claims module found.\n\n"
                "**Impact:** Employees have no way to submit travel, medical, or other expense claims. "
                "Finance cannot process reimbursements through the system.",
                "medium", sp
            )
        else:
            log_result("T12-Reimbursements", "PASS", "Reimbursement section found")

    except Exception as ex:
        print(f"  [EXCEPTION] Batch 4: {ex}")
        traceback.print_exc()
        shot(driver, "batch4_exception")
    finally:
        driver.quit()


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST BATCH 5: F&F Settlement, Statutory, History, Audit (uses driver #5)
# ═══════════════════════════════════════════════════════════════════════════════

def batch5_fnf_statutory_history_audit():
    """
    T13: Full & Final settlement
    T14: Statutory compliance (PF, ESI, PT)
    T15: Payroll history
    T16: Audit trail
    """
    print("\n" + "=" * 70)
    print("  BATCH 5: F&F, Statutory, History, Audit Trail")
    print("=" * 70)

    driver = create_driver()
    try:
        ok, reason = do_login(driver, CREDS["org_admin"]["email"],
                              CREDS["org_admin"]["password"], "finance_b5")
        if not ok:
            log_result("T13-Login", "FAIL", f"Login failed: {reason}")
            return
        log_result("T13-Login", "PASS", "Logged in for batch 5")

        token = extract_token(driver)

        # SSO to payroll
        sso = find_sso_payroll_link(driver)
        if sso:
            driver.get(sso)
            time.sleep(5)

        # ── T13: Full & Final Settlement ──
        print("\n  -- T13: Full & Final Settlement --")
        fnf_pages = ["/fnf", "/full-and-final", "/settlement",
                    "/exit-settlement", "/separation", "/my/fnf"]
        fnf_found = False

        for path in fnf_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T13_fnf_{path.replace('/','_')}")

                fnf_keywords = ["full and final", "fnf", "settlement",
                               "final settlement", "separation", "exit pay"]
                for kw in fnf_keywords:
                    if kw in src:
                        fnf_found = True
                        print(f"    F&F content found: '{kw}' on {path}")
                        break
                if fnf_found:
                    break
            except Exception:
                pass

        # Also check exit module
        if not fnf_found:
            try:
                driver.get("https://test-exit.empcloud.com")
                time.sleep(4)
                src = driver.page_source.lower()
                if "settlement" in src or "fnf" in src or "full and final" in src:
                    fnf_found = True
                    print("    F&F found in exit module")
            except Exception:
                pass

        if not fnf_found:
            log_result("T13-FnF", "FAIL", "No Full & Final settlement feature found")
            record_bug(
                "No Full and Final settlement calculation for exiting employees",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. Check payroll module for F&F / settlement pages\n3. Also checked exit module\n\n"
                "**Expected:** Full & Final settlement calculator showing pending salary, leave encashment, "
                "gratuity, deductions for exiting employees\n"
                "**Actual:** No F&F settlement feature found in payroll or exit module.\n\n"
                "**Impact:** Finance cannot calculate final dues for departing employees. "
                "Manual calculations needed, risking compliance issues.",
                "medium", sp
            )
        else:
            log_result("T13-FnF", "PASS", "F&F settlement feature found")

        # ── T14: Statutory Compliance Configuration ──
        print("\n  -- T14: Statutory Compliance (PF, ESI, PT) --")
        stat_pages = ["/settings", "/settings/statutory", "/statutory",
                     "/compliance", "/admin/settings", "/settings/pf",
                     "/settings/esi", "/admin/statutory"]
        statutory_found = False
        statutory_details = {}

        for path in stat_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T14_stat_{path.replace('/','_')}")

                if "404" not in src and "not found" not in src:
                    statutory_details = {
                        "pf_config": "pf" in src or "provident fund" in src or "epf" in src,
                        "esi_config": "esi" in src or "employee state insurance" in src,
                        "pt_config": "professional tax" in src or "pt" in src,
                        "tds_config": "tds" in src or "tax deducted" in src,
                    }
                    found = [k for k, v in statutory_details.items() if v]
                    if found:
                        statutory_found = True
                        print(f"    Statutory config found: {found}")
                        break
            except Exception:
                pass

        if not statutory_found:
            log_result("T14-Statutory", "FAIL", "No statutory compliance configuration found")
            record_bug(
                "Statutory compliance not configured -- PF, ESI, PT deduction settings missing",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll\n3. Check settings, statutory, compliance pages\n\n"
                "**Expected:** Configuration page for PF (12% employer + 12% employee), "
                "ESI (3.25% employer + 0.75% employee), Professional Tax rates\n"
                "**Actual:** No statutory compliance configuration found.\n\n"
                "**Impact:** Payroll deductions for PF, ESI, PT may not be calculated correctly. "
                "Organization risks non-compliance with labor laws.",
                "high", sp
            )
        else:
            log_result("T14-Statutory", "PASS", f"Statutory config: {[k for k,v in statutory_details.items() if v]}")

        # ── T15: Payroll History ──
        print("\n  -- T15: Payroll History (Previous Months) --")
        history_pages = ["/history", "/payroll-history", "/pay-runs",
                        "/payroll/history", "/archives", "/past-payrolls"]
        history_found = False

        for path in history_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T15_history_{path.replace('/','_')}")

                if "404" not in src and "not found" not in src:
                    hist_keywords = ["history", "previous", "past", "archive",
                                   "january", "february", "march", "2025", "2026",
                                   "month", "pay run", "processed"]
                    for kw in hist_keywords:
                        if kw in src:
                            history_found = True
                            print(f"    History content found: '{kw}' on {path}")
                            break
                if history_found:
                    break
            except Exception:
                pass

        if not history_found:
            log_result("T15-History", "FAIL", "No payroll history / previous months found")
            record_bug(
                "Cannot view payroll history -- no previous months' payroll records accessible",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll\n3. Look for history, pay-runs, archives pages\n\n"
                "**Expected:** Payroll history showing previous months' processed payrolls with amounts and status\n"
                "**Actual:** No payroll history accessible.\n\n"
                "**Impact:** Finance cannot reference previous payroll data for variance analysis, audits, or queries.",
                "medium", sp
            )
        else:
            log_result("T15-History", "PASS", "Payroll history accessible")

        # ── T16: Audit Trail ──
        print("\n  -- T16: Audit Trail for Payroll --")
        audit_pages = ["/audit", "/audit-trail", "/logs", "/activity",
                      "/admin/audit", "/payroll/audit"]
        audit_found = False

        for path in audit_pages:
            try:
                driver.get(PAYROLL_URL + path)
                time.sleep(3)
                src = driver.page_source.lower()
                sp = shot(driver, f"T16_audit_{path.replace('/','_')}")

                if "404" not in src and "not found" not in src:
                    audit_keywords = ["audit", "trail", "log", "activity",
                                    "who processed", "changed", "modified",
                                    "action", "timestamp"]
                    for kw in audit_keywords:
                        if kw in src:
                            audit_found = True
                            print(f"    Audit content found: '{kw}' on {path}")
                            break
                if audit_found:
                    break
            except Exception:
                pass

        if not audit_found:
            log_result("T16-AuditTrail", "FAIL", "No payroll audit trail found")
            record_bug(
                "No audit trail for payroll changes -- cannot track who processed or modified payroll",
                "**Persona:** Meera Sharma, Finance Manager\n\n"
                "**Steps:**\n1. Login as org admin\n2. SSO to payroll\n3. Look for audit trail, logs, activity pages\n\n"
                "**Expected:** Audit trail showing: who processed payroll, when, what changes were made, "
                "salary modifications, approvals\n"
                "**Actual:** No audit trail or activity log found in payroll module.\n\n"
                "**Impact:** No accountability for payroll changes. Auditors cannot verify payroll processing integrity. "
                "Compliance risk for SOC/ISO audits.",
                "medium", sp
            )
        else:
            log_result("T16-AuditTrail", "PASS", "Audit trail found")

    except Exception as ex:
        print(f"  [EXCEPTION] Batch 5: {ex}")
        traceback.print_exc()
        shot(driver, "batch5_exception")
    finally:
        driver.quit()


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST BATCH 6: API-based financial data integrity checks
# ═══════════════════════════════════════════════════════════════════════════════

def batch6_api_financial_integrity():
    """
    T17: API health and payroll endpoints
    T18: Employee salary data via API
    T19: Payroll totals consistency
    """
    print("\n" + "=" * 70)
    print("  BATCH 6: API Financial Data Integrity")
    print("=" * 70)

    # First get a token via login
    driver = create_driver()
    token = None
    try:
        ok, reason = do_login(driver, CREDS["org_admin"]["email"],
                              CREDS["org_admin"]["password"], "finance_api")
        if ok:
            token = extract_token(driver)
            print(f"    Token: {'found' if token else 'NOT found'}")
    finally:
        driver.quit()

    if not token:
        log_result("T17-APIToken", "FAIL", "Could not get auth token for API tests")
        return

    # ── T17: Payroll API Health ──
    print("\n  -- T17: Payroll API Endpoints --")
    payroll_endpoints = [
        (PAYROLL_API, "/api/v1/health", "Payroll Health"),
        (PAYROLL_API, "/api/v1/payroll", "Payroll List"),
        (PAYROLL_API, "/api/v1/payslips", "Payslips"),
        (PAYROLL_API, "/api/v1/salary-structures", "Salary Structures"),
        (PAYROLL_API, "/api/v1/salary-components", "Salary Components"),
        (PAYROLL_API, "/api/v1/employees", "Payroll Employees"),
        (PAYROLL_API, "/api/v1/pay-runs", "Pay Runs"),
        (PAYROLL_API, "/api/v1/tax", "Tax"),
        (PAYROLL_API, "/api/v1/statutory", "Statutory"),
        (PAYROLL_API, "/api/v1/reimbursements", "Reimbursements"),
        (MAIN_API, "/api/v1/employees", "Main Employees"),
        (MAIN_API, "/api/v1/payroll", "Main Payroll"),
        (MAIN_API, "/api/v1/salary", "Main Salary"),
    ]

    api_results = {}
    working_endpoints = 0

    for base, path, name in payroll_endpoints:
        code, data = api_get(base + path, token)
        api_results[name] = {"code": code, "data": data}
        status = "OK" if code == 200 else f"HTTP {code}"
        print(f"    {name}: {status} -> {json.dumps(data)[:150]}")
        if code == 200:
            working_endpoints += 1

    if working_endpoints == 0:
        log_result("T17-PayrollAPI", "FAIL", "All payroll API endpoints failed")
        record_bug(
            "Payroll API completely non-functional -- all endpoints return errors",
            "**Persona:** Meera Sharma, Finance Manager\n\n"
            "**Details:** Tested 13 payroll API endpoints. None returned 200 OK.\n\n"
            "**Endpoints tested:**\n" +
            "\n".join([f"- `{base}{path}` -> HTTP {api_results[name]['code']}"
                      for base, path, name in payroll_endpoints]) +
            "\n\n**Impact:** No payroll data accessible via API. Integrations with accounting software, "
            "bank payment systems, and reporting tools are all broken.",
            "critical"
        )
    else:
        log_result("T17-PayrollAPI", "PASS", f"{working_endpoints}/{len(payroll_endpoints)} endpoints working")

    # ── T18: Employee Salary Data via API ──
    print("\n  -- T18: Employee Salary Data --")
    employees_data = api_results.get("Main Employees", {}).get("data")
    if isinstance(employees_data, dict):
        employees_data = employees_data.get("data", employees_data.get("employees", []))

    salary_data_found = False
    if isinstance(employees_data, list) and employees_data:
        print(f"    Found {len(employees_data)} employees via API")
        for emp in employees_data[:3]:
            emp_id = emp.get("id") or emp.get("_id")
            if not emp_id:
                continue
            # Try to get salary details
            for endpoint in [f"/api/v1/employees/{emp_id}/salary",
                           f"/api/v1/employees/{emp_id}/payslips",
                           f"/api/v1/salary/{emp_id}",
                           f"/api/v1/employees/{emp_id}"]:
                code, data = api_get(MAIN_API + endpoint, token)
                if code == 200:
                    data_str = json.dumps(data).lower()
                    if any(kw in data_str for kw in ["salary", "basic", "gross", "ctc", "compensation"]):
                        salary_data_found = True
                        print(f"    Salary data for emp {emp_id}: found via {endpoint}")
                        break
                code2, data2 = api_get(PAYROLL_API + endpoint, token)
                if code2 == 200:
                    data_str2 = json.dumps(data2).lower()
                    if any(kw in data_str2 for kw in ["salary", "basic", "gross", "ctc"]):
                        salary_data_found = True
                        print(f"    Salary data for emp {emp_id}: found via payroll API {endpoint}")
                        break
            if salary_data_found:
                break

    if not salary_data_found:
        log_result("T18-SalaryDataAPI", "FAIL", "No salary data accessible via API")
    else:
        log_result("T18-SalaryDataAPI", "PASS", "Salary data accessible")

    # ── T19: Payroll Totals Consistency ──
    print("\n  -- T19: Payroll Totals Consistency --")
    # Check if pay-runs or payroll summary has totals
    payroll_data = api_results.get("Payroll List", {}).get("data")
    payslips_data = api_results.get("Payslips", {}).get("data")

    if payroll_data and payslips_data:
        # Try to compare totals
        print(f"    Payroll data: {json.dumps(payroll_data)[:200]}")
        print(f"    Payslips data: {json.dumps(payslips_data)[:200]}")
        log_result("T19-Consistency", "INFO",
                   "Payroll and payslip data available -- manual comparison needed")
    else:
        log_result("T19-Consistency", "SKIP",
                   "Cannot verify -- payroll/payslip API data not available")


# ═══════════════════════════════════════════════════════════════════════════════
#  FILE ALL BUGS TO GITHUB
# ═══════════════════════════════════════════════════════════════════════════════

def file_all_bugs():
    print("\n" + "=" * 70)
    print(f"  FILING {len(bugs_found)} BUGS TO GITHUB")
    print("=" * 70)

    filed = 0
    for bug in bugs_found:
        title = bug["title"]
        desc = bug["description"]

        # Upload screenshot if available
        ss_md = ""
        if bug.get("screenshot"):
            ss_md = upload_screenshot_to_github(bug["screenshot"])

        body = (
            f"{desc}{ss_md}\n\n"
            f"---\n"
            f"**Severity:** {bug['severity']}\n"
            f"**Tested by:** Meera Sharma (Finance Manager persona)\n"
            f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"**Module:** Payroll / Finance\n"
        )

        labels = ["bug"]
        if bug["severity"] == "critical":
            labels.append("critical")
        elif bug["severity"] == "high":
            labels.append("high")

        result = file_github_issue(title, body, labels)
        if result:
            filed += 1
        time.sleep(1)  # Rate limit courtesy

    print(f"\n  Filed {filed}/{len(bugs_found)} bugs to GitHub")
    return filed


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  EMP Cloud HRMS - Finance Manager (Meera Sharma) Month-End Tests")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Org: TechNova Solutions | Role: Finance Manager")
    print("=" * 70)

    start = time.time()

    # Run all batches (driver restarts every 3 tests)
    batch1_payroll_sso_and_dashboard()
    batch2_payslips_tax_leave()
    batch3_overtime_billing_costs()
    batch4_reports_bank_reimbursements()
    batch5_fnf_statutory_history_audit()
    batch6_api_financial_integrity()

    # File bugs
    filed = file_all_bugs()

    # Summary
    elapsed = time.time() - start
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = sum(1 for r in test_results if r["status"] == "FAIL")
    skipped = sum(1 for r in test_results if r["status"] not in ("PASS", "FAIL"))
    print(f"  Total tests: {len(test_results)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped/Other: {skipped}")
    print(f"  Bugs found: {len(bugs_found)}")
    print(f"  Bugs filed: {filed}")
    print(f"  Duration: {elapsed:.0f}s")
    print()

    for r in test_results:
        icon = "PASS" if r["status"] == "PASS" else ("FAIL" if r["status"] == "FAIL" else "----")
        print(f"  [{icon}] {r['test']}: {r['details'][:80]}")

    print("\n" + "=" * 70)
    if bugs_found:
        print("  BUGS FILED:")
        for b in bugs_found:
            print(f"    [{b['severity'].upper()}] {b['title']}")
    print("=" * 70)

    # Save results
    results_file = os.path.join(SCREENSHOT_DIR, "test_results.json")
    with open(results_file, "w") as f:
        json.dump({
            "persona": "Meera Sharma - Finance Manager",
            "date": datetime.now().isoformat(),
            "tests": test_results,
            "bugs": [{"title": b["title"], "severity": b["severity"]} for b in bugs_found],
            "summary": {
                "total": len(test_results),
                "passed": passed,
                "failed": failed,
                "bugs_found": len(bugs_found),
                "bugs_filed": filed,
                "duration_seconds": elapsed,
            }
        }, f, indent=2)
    print(f"  Results saved to: {results_file}")


if __name__ == "__main__":
    main()
