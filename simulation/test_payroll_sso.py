"""
Payroll Module - Comprehensive SSO Test
Tests all self-service and admin pages, payroll operations, payslip details, PDF download, tax computation.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import requests
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------- Config ----------
BASE_URL = "https://testpayroll.empcloud.com"
API_URL = "https://testpayroll-api.empcloud.com"
AUTH_API = "https://test-empcloud-api.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_payroll"
TOKEN_FILE = r"C:\emptesting\simulation\current_token.txt"
LOGIN_EMAIL = "ananya@technova.in"
LOGIN_PASS = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs = []
test_results = []
payroll_api_token = None  # token for the payroll API (separate from SSO)


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def screenshot(driver, name):
    fname = name.replace("/", "_").replace("\\", "_").replace("?", "_").replace(" ", "_")
    path = os.path.join(SCREENSHOT_DIR, f"{fname}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {path}")
    return path


def record(test_name, status, detail=""):
    test_results.append({"test": test_name, "status": status, "detail": detail})
    symbol = "PASS" if status == "pass" else "FAIL"
    log(f"  [{symbol}] {test_name}: {detail}")


def file_bug(title, body):
    bugs.append(title)
    log(f"  BUG: {title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github+v3+json",
            },
            json={
                "title": f"[Payroll] {title}",
                "body": body,
                "labels": ["bug", "payroll"],
            },
            timeout=15,
        )
        if resp.status_code == 201:
            log(f"  Filed issue: {resp.json().get('html_url')}")
        else:
            log(f"  Issue filing failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        log(f"  Issue filing error: {e}")


def get_sso_token():
    """Get SSO token from EmpCloud auth API."""
    log("Getting SSO token from EmpCloud auth...")
    try:
        resp = requests.post(
            f"{AUTH_API}/api/v1/auth/login",
            json={"email": LOGIN_EMAIL, "password": LOGIN_PASS},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            d = data.get("data", {})
            tokens = d.get("tokens", {})
            token = tokens.get("access_token") or tokens.get("token") or tokens.get("accessToken")
            if token:
                with open(TOKEN_FILE, "w") as f:
                    f.write(token)
                log(f"  SSO token obtained (len={len(token)})")
                return token
        log(f"  SSO login failed: {resp.status_code}")
        return None
    except Exception as e:
        log(f"  SSO login error: {e}")
        return None


def get_payroll_api_token():
    """Get token from the payroll API's own auth endpoint."""
    global payroll_api_token
    log("Getting payroll API token...")
    try:
        resp = requests.post(
            f"{API_URL}/api/v1/auth/login",
            json={"email": LOGIN_EMAIL, "password": LOGIN_PASS},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            d = data.get("data", {})
            tokens = d.get("tokens", {})
            token = tokens.get("accessToken") or tokens.get("access_token") or tokens.get("token")
            if token:
                payroll_api_token = token
                log(f"  Payroll API token obtained (len={len(token)})")
                return token
        log(f"  Payroll API login status: {resp.status_code}")
        return None
    except Exception as e:
        log(f"  Payroll API login error: {e}")
        return None


def api_headers():
    """Get headers for payroll API calls, refreshing token if needed."""
    global payroll_api_token
    if not payroll_api_token:
        get_payroll_api_token()
    return {"Authorization": f"Bearer {payroll_api_token}"}


def api_get(path, retry=True):
    """Make a GET to payroll API with auto-refresh on 401."""
    global payroll_api_token
    resp = requests.get(f"{API_URL}{path}", headers=api_headers(), timeout=15)
    if resp.status_code == 401 and retry:
        get_payroll_api_token()
        resp = requests.get(f"{API_URL}{path}", headers=api_headers(), timeout=15)
    return resp


def read_token():
    try:
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    except:
        return None


def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    return driver


def wait_for_page(driver, timeout=12):
    time.sleep(2)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except:
        pass
    time.sleep(1)


def sso_login(driver, token):
    url = f"{BASE_URL}?sso_token={token}"
    log(f"SSO navigating to payroll...")
    driver.get(url)
    wait_for_page(driver, 15)
    return driver


def check_page_loaded(driver, page_name):
    body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
    page_source = driver.page_source
    error_indicators = [
        "500 Internal Server Error", "502 Bad Gateway", "503 Service Unavailable",
        "404 Not Found", "Application Error", "Something went wrong", "ERR_CONNECTION",
    ]
    for err in error_indicators:
        if err.lower() in page_source.lower():
            return False, f"Error found: {err}"
    if len(body_text) < 10 and "login" not in page_source.lower():
        return False, "Page appears blank"
    return True, "OK"


def navigate_to(driver, path, page_name):
    url = f"{BASE_URL}{path}"
    log(f"Navigating to {page_name} ({path})...")
    driver.get(url)
    wait_for_page(driver)
    ss = screenshot(driver, f"payroll_{page_name}")
    ok, detail = check_page_loaded(driver, page_name)
    return ok, detail, ss


# ============================================================
# MAIN TEST
# ============================================================
def run_tests():
    log("=" * 60)
    log("PAYROLL MODULE - COMPREHENSIVE TEST")
    log("=" * 60)

    # --- Get tokens ---
    sso_token = get_sso_token()
    if not sso_token:
        sso_token = read_token()
    if not sso_token:
        log("FATAL: Cannot obtain SSO token.")
        return

    # Get payroll API token separately
    get_payroll_api_token()

    driver = create_driver()
    try:
        # --- SSO Login ---
        sso_login(driver, sso_token)
        screenshot(driver, "payroll_01_sso_landing")

        # Check if SSO worked
        page_src = driver.page_source.lower()
        current_url = driver.current_url
        if "login" in current_url.lower() and "sso" not in current_url.lower():
            log("Token may be expired, retrying...")
            sso_token = get_sso_token()
            if sso_token:
                sso_login(driver, sso_token)
                screenshot(driver, "payroll_01_sso_retry")

        # ============================================================
        # DASHBOARD
        # ============================================================
        log("\n--- DASHBOARD ---")
        ok, detail, _ = navigate_to(driver, "/", "dashboard")
        screenshot(driver, "payroll_02_dashboard")
        if ok:
            record("Dashboard loads", "pass", detail)
        else:
            record("Dashboard loads", "fail", detail)
            file_bug("Dashboard fails to load", f"Navigating to / shows: {detail}")

        # ============================================================
        # SELF-SERVICE PAGES
        # ============================================================
        self_service_pages = [
            ("/my", "My Dashboard"),
            ("/my/payslips", "My Payslips"),
            ("/my/salary", "My Salary"),
            ("/my/tax", "My Tax"),
            ("/my/declarations", "My Declarations"),
            ("/my/reimbursements", "My Reimbursements"),
        ]

        log("\n--- SELF-SERVICE PAGES ---")
        for path, name in self_service_pages:
            ok, detail, _ = navigate_to(driver, path, name.replace(" ", "_"))
            if ok:
                record(f"Self-Service: {name}", "pass", detail)
            else:
                record(f"Self-Service: {name}", "fail", detail)
                file_bug(f"{name} page fails to load", f"Path {path} shows: {detail}")

        # ============================================================
        # PAYSLIP DETAILS (gross, net, deductions)
        # ============================================================
        log("\n--- PAYSLIP DETAILS ---")
        driver.get(f"{BASE_URL}/my/payslips")
        wait_for_page(driver)
        screenshot(driver, "payroll_10_payslips_list")

        try:
            payslip_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='payslip'], tr[class*='cursor'], table tbody tr, .card, [class*='slip']")
            if payslip_links:
                log(f"  Found {len(payslip_links)} potential payslip elements")
                try:
                    payslip_links[0].click()
                    wait_for_page(driver)
                    screenshot(driver, "payroll_11_payslip_detail")
                except:
                    log("  Could not click payslip element")

            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            has_gross = "gross" in body
            has_net = "net" in body
            has_deductions = "deduction" in body

            if has_gross or has_net or has_deductions:
                record("Payslip details visible", "pass",
                       f"Gross:{has_gross}, Net:{has_net}, Deductions:{has_deductions}")
            else:
                record("Payslip details visible", "fail", "No gross/net/deduction text found")
                file_bug("Payslip page missing salary breakdown",
                         "The payslips page does not show gross pay, net pay, or deductions breakdown")
        except Exception as e:
            record("Payslip details check", "fail", str(e))

        # ============================================================
        # PAYSLIP PDF DOWNLOAD (via payroll API)
        # ============================================================
        log("\n--- PAYSLIP PDF DOWNLOAD ---")
        try:
            resp = api_get("/api/v1/self-service/payslips")
            log(f"  Payslips API: {resp.status_code}")
            if resp.status_code == 200:
                payslips_data = resp.json()
                payslip_list = payslips_data if isinstance(payslips_data, list) else payslips_data.get("data", payslips_data.get("payslips", []))
                log(f"  Payslips count: {len(payslip_list) if isinstance(payslip_list, list) else '?'}")

                if payslip_list and isinstance(payslip_list, list) and len(payslip_list) > 0:
                    first = payslip_list[0]
                    payslip_id = first.get("id") or first.get("payslip_id") or first.get("payslipId")
                    log(f"  First payslip ID: {payslip_id}, keys: {list(first.keys())[:10]}")

                    if payslip_id:
                        pdf_resp = api_get(f"/api/v1/self-service/payslips/{payslip_id}/pdf")
                        log(f"  PDF download status: {pdf_resp.status_code}, type: {pdf_resp.headers.get('content-type','')}")
                        if pdf_resp.status_code == 200:
                            pdf_path = os.path.join(SCREENSHOT_DIR, f"payslip_{payslip_id}.pdf")
                            with open(pdf_path, "wb") as f:
                                f.write(pdf_resp.content)
                            record("Payslip PDF download", "pass", f"Downloaded {len(pdf_resp.content)} bytes")
                        else:
                            record("Payslip PDF download", "fail", f"Status {pdf_resp.status_code}: {pdf_resp.text[:200]}")
                            file_bug("Payslip PDF download returns error",
                                     f"GET /api/v1/self-service/payslips/{payslip_id}/pdf returned {pdf_resp.status_code}.\n{pdf_resp.text[:500]}")
                    else:
                        record("Payslip PDF download", "fail", "No payslip ID found")
                else:
                    record("Payslip PDF download", "fail", f"No payslips returned. Data type: {type(payslip_list).__name__}")
            else:
                record("Payslip PDF download", "fail", f"Payslips API: {resp.status_code}: {resp.text[:200]}")
                file_bug("Self-service payslips API returns error",
                         f"GET /api/v1/self-service/payslips returned {resp.status_code}: {resp.text[:500]}")
        except Exception as e:
            record("Payslip PDF download", "fail", str(e))

        # ============================================================
        # TAX COMPUTATION
        # ============================================================
        log("\n--- TAX COMPUTATION ---")
        ok, detail, _ = navigate_to(driver, "/my/tax", "tax_computation")
        screenshot(driver, "payroll_12_tax_computation")

        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        tax_keywords = ["tax", "income", "tds", "computation", "regime", "old", "new", "deduction", "80c", "hra"]
        found_tax = [kw for kw in tax_keywords if kw in body]
        if ok and len(found_tax) >= 2:
            record("Tax computation page", "pass", f"Found: {found_tax}")
        elif ok:
            record("Tax computation page", "pass", f"Page loaded, limited tax info: {found_tax}")
        else:
            record("Tax computation page", "fail", detail)
            file_bug("Tax computation page not loading", f"/my/tax shows: {detail}")

        # Tax API check
        try:
            resp = api_get("/api/v1/self-service/tax/computation")
            log(f"  Tax computation API: {resp.status_code}")
            if resp.status_code == 200:
                tax_data = resp.json()
                keys = list(tax_data.keys()) if isinstance(tax_data, dict) else "list"
                record("Tax computation API", "pass", f"Keys: {keys}")
            else:
                record("Tax computation API", "fail", f"Status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            record("Tax computation API", "fail", str(e))

        # ============================================================
        # ADMIN PAGES
        # ============================================================
        admin_pages = [
            ("/", "Admin_Dashboard"),
            ("/employees", "Admin_Employees"),
            ("/payroll/runs", "Admin_Payroll_Runs"),
            ("/payroll/salary-structures", "Admin_Salary_Structures"),
            ("/settings", "Admin_Settings"),
            ("/payroll/analytics", "Payroll_Analytics"),
            ("/payslips", "All_Payslips"),
            ("/attendance", "Attendance"),
            ("/reports", "Reports"),
            ("/benefits", "Benefits"),
            ("/insurance", "Insurance"),
            ("/gl-accounting", "GL_Accounting"),
            ("/global-payroll", "Global_Payroll"),
            ("/earned-wage", "Earned_Wage_Access"),
            ("/pay-equity", "Pay_Equity"),
            ("/benchmarks", "Compensation_Benchmarks"),
            ("/loans", "Loans"),
            ("/leaves", "Leaves"),
        ]

        log("\n--- ADMIN PAGES ---")
        for path, name in admin_pages:
            ok, detail, _ = navigate_to(driver, path, name)
            if ok:
                record(f"Admin: {name}", "pass", detail)
            else:
                record(f"Admin: {name}", "fail", detail)
                file_bug(f"{name} page fails to load", f"Path {path}: {detail}")

        # ============================================================
        # RUN PAYROLL BUTTON
        # ============================================================
        log("\n--- RUN PAYROLL ---")
        driver.get(f"{BASE_URL}/payroll/runs")
        wait_for_page(driver)
        screenshot(driver, "payroll_20_payroll_runs")

        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text

            # Try clicking "Admin Panel" first if self-service is showing
            try:
                admin_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Admin Panel')] | //a[contains(text(), 'Admin Panel')]")
                if admin_btn:
                    log("  Found 'Admin Panel' button, clicking to switch to admin view...")
                    admin_btn.click()
                    wait_for_page(driver)
                    screenshot(driver, "payroll_20b_after_admin_click")
                    # Now navigate to payroll/runs in admin context
                    driver.get(f"{BASE_URL}/payroll/runs")
                    wait_for_page(driver)
                    screenshot(driver, "payroll_20c_payroll_runs_admin")
            except:
                pass

            # Now look for Run Payroll button
            run_btn = None
            selectors = [
                "//button[contains(text(), 'Run Payroll')]",
                "//button[contains(text(), 'run payroll')]",
                "//button[contains(text(), 'New Run')]",
                "//button[contains(text(), 'Create')]",
                "//a[contains(text(), 'Run Payroll')]",
                "//button[contains(text(), 'New Payroll')]",
                "//button[contains(text(), 'Start')]",
                "//button[contains(text(), 'Create Run')]",
                "//button[contains(text(), 'New')]",
            ]
            for sel in selectors:
                elems = driver.find_elements(By.XPATH, sel)
                if elems:
                    run_btn = elems[0]
                    log(f"  Found button via: {sel} -> '{run_btn.text}'")
                    break

            if run_btn:
                screenshot(driver, "payroll_21_run_payroll_button")
                record("Run Payroll button found", "pass", run_btn.text)
                try:
                    run_btn.click()
                    wait_for_page(driver)
                    screenshot(driver, "payroll_22_run_payroll_clicked")
                    record("Run Payroll button clickable", "pass", "Clicked successfully")
                except Exception as e:
                    record("Run Payroll button clickable", "fail", str(e))
            else:
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                btn_texts = [b.text for b in all_buttons[:15] if b.text.strip()]
                all_links = driver.find_elements(By.TAG_NAME, "a")
                link_texts = [a.text for a in all_links[:15] if a.text.strip()]
                record("Run Payroll button found", "fail",
                       f"Buttons: {btn_texts}, Links: {link_texts}")
                file_bug("Run Payroll button not found on payroll runs page",
                         f"Navigated to /payroll/runs but no Run Payroll button.\nButtons: {btn_texts}\nLinks: {link_texts}\nPage text (first 500): {body_text[:500]}")
        except Exception as e:
            record("Run Payroll", "fail", str(e))
            screenshot(driver, "payroll_22_error")

        # ============================================================
        # PAYROLL RUN DETAIL via API
        # ============================================================
        log("\n--- PAYROLL RUN DETAIL ---")
        try:
            resp = api_get("/api/v1/payroll")
            log(f"  Payroll runs API: {resp.status_code}")
            if resp.status_code == 200:
                runs_data = resp.json()
                runs = runs_data if isinstance(runs_data, list) else runs_data.get("data", runs_data.get("runs", []))
                if runs and isinstance(runs, list) and len(runs) > 0:
                    run_id = runs[0].get("id") or runs[0].get("run_id") or runs[0].get("runId")
                    log(f"  First run ID: {run_id}, keys: {list(runs[0].keys())[:8]}")

                    ok, detail, _ = navigate_to(driver, f"/payroll/runs/{run_id}", f"payroll_run_{run_id}")
                    screenshot(driver, f"payroll_23_run_detail")
                    if ok:
                        record("Payroll run detail page", "pass", f"Run ID {run_id}")
                    else:
                        record("Payroll run detail page", "fail", detail)
                else:
                    record("Payroll run detail page", "fail", "No payroll runs found in API")
            else:
                record("Payroll run detail page", "fail", f"API {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            record("Payroll run detail page", "fail", str(e))

        # ============================================================
        # EMPLOYEE DETAIL via API + UI
        # ============================================================
        log("\n--- EMPLOYEE DETAIL ---")
        try:
            resp = api_get("/api/v1/employees")
            log(f"  Employees API: {resp.status_code}")
            if resp.status_code == 200:
                emp_data = resp.json()
                emps = emp_data if isinstance(emp_data, list) else emp_data.get("data", emp_data.get("employees", []))
                if emps and isinstance(emps, list) and len(emps) > 0:
                    emp_id = emps[0].get("id") or emps[0].get("employee_id") or emps[0].get("employeeId")
                    log(f"  First employee ID: {emp_id}, name: {emps[0].get('firstName', emps[0].get('first_name', ''))}")
                    ok, detail, _ = navigate_to(driver, f"/employees/{emp_id}", f"employee_{emp_id}")
                    if ok:
                        record("Employee detail page", "pass", f"Employee ID {emp_id}")
                    else:
                        record("Employee detail page", "fail", detail)
                else:
                    record("Employee detail page", "fail", "No employees in API response")
            else:
                record("Employee detail page", "fail", f"API {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            record("Employee detail page", "fail", str(e))

        # ============================================================
        # SALARY STRUCTURES API
        # ============================================================
        log("\n--- SALARY STRUCTURES ---")
        try:
            resp = api_get("/api/v1/salary-structures")
            log(f"  Salary structures API: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                structs = data if isinstance(data, list) else data.get("data", data.get("structures", []))
                count = len(structs) if isinstance(structs, list) else "?"
                record("Salary structures API", "pass", f"Found {count} structures")
            else:
                record("Salary structures API", "fail", f"Status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            record("Salary structures API", "fail", str(e))

        # ============================================================
        # MY SALARY API
        # ============================================================
        log("\n--- MY SALARY API ---")
        try:
            resp = api_get("/api/v1/self-service/salary")
            log(f"  My salary API: {resp.status_code}")
            if resp.status_code == 200:
                sal = resp.json()
                record("My salary API", "pass", f"Keys: {list(sal.keys()) if isinstance(sal, dict) else type(sal).__name__}")
            else:
                record("My salary API", "fail", f"Status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            record("My salary API", "fail", str(e))

        # ============================================================
        # ORG CHART
        # ============================================================
        log("\n--- ORG CHART ---")
        ok, detail, _ = navigate_to(driver, "/employees/org-chart", "org_chart")
        if ok:
            record("Org Chart", "pass", detail)
        else:
            record("Org Chart", "fail", detail)

        # ============================================================
        # EXTRA PAGES
        # ============================================================
        extra_pages = [
            ("/total-rewards", "Total_Rewards"),
            ("/audit-log", "Audit_Log"),
            ("/global-payroll/employees", "Global_Employees"),
            ("/global-payroll/invoices", "Contractor_Invoices"),
            ("/global-payroll/compliance", "Country_Compliance"),
        ]
        log("\n--- EXTRA PAGES ---")
        for path, name in extra_pages:
            ok, detail, _ = navigate_to(driver, path, name)
            if ok:
                record(f"Extra: {name}", "pass", detail)
            else:
                record(f"Extra: {name}", "fail", detail)

        # ============================================================
        # MY PROFILE
        # ============================================================
        log("\n--- MY PROFILE ---")
        ok, detail, _ = navigate_to(driver, "/my/profile", "My_Profile")
        if ok:
            record("My Profile", "pass", detail)
        else:
            record("My Profile", "fail", detail)

        # ============================================================
        # MY LEAVES
        # ============================================================
        log("\n--- MY LEAVES ---")
        ok, detail, _ = navigate_to(driver, "/my/leaves", "My_Leaves")
        if ok:
            record("My Leaves", "pass", detail)
        else:
            record("My Leaves", "fail", detail)

    except Exception as e:
        log(f"FATAL ERROR: {e}")
        traceback.print_exc()
        screenshot(driver, "payroll_FATAL_ERROR")
    finally:
        driver.quit()

    # ============================================================
    # SUMMARY
    # ============================================================
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    passed = sum(1 for r in test_results if r["status"] == "pass")
    failed = sum(1 for r in test_results if r["status"] == "fail")
    total = len(test_results)
    log(f"Total: {total}  |  Passed: {passed}  |  Failed: {failed}")
    log(f"Bugs filed: {len(bugs)}")

    if failed > 0:
        log("\nFailed tests:")
        for r in test_results:
            if r["status"] == "fail":
                log(f"  FAIL: {r['test']} - {r['detail']}")

    if bugs:
        log("\nBugs filed:")
        for b in bugs:
            log(f"  - [Payroll] {b}")

    log("\nDone.")


if __name__ == "__main__":
    run_tests()
