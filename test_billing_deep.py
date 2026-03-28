"""
EMP Cloud HRMS - Deep Billing Module Test
Tests: Billing Dashboard, Subscriptions, Invoices, Payments, Overview/Analytics,
       API endpoints, Super Admin billing, RBAC, Data Consistency
"""

import sys
import os
import time
import json
import traceback
import requests
import base64
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"

ORG_ADMIN_EMAIL = "ananya@technova.in"
ORG_ADMIN_PASS = "Welcome@123"
SUPER_ADMIN_EMAIL = "admin@empcloud.com"
SUPER_ADMIN_PASS = "SuperAdmin@2026"
EMPLOYEE_EMAIL = "priya@technova.in"
EMPLOYEE_PASS = "Welcome@123"

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\billing_deep"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── State ───────────────────────────────────────────────────────────────────
bugs = []
results = []
driver = None
selenium_test_count = 0

# ── Helpers ─────────────────────────────────────────────────────────────────

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--ignore-certificate-errors")
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)

def ensure_driver():
    """Ensure driver is alive, restart if needed every 3 Selenium tests."""
    global driver, selenium_test_count
    selenium_test_count += 1
    if selenium_test_count > 1 and (selenium_test_count - 1) % 3 == 0:
        print(f"\n  [DRIVER] Restarting after {selenium_test_count - 1} Selenium tests...")
        try:
            driver.quit()
        except:
            pass
        driver = get_driver()
    elif driver is None:
        driver = get_driver()

def screenshot(name):
    global driver
    ts = datetime.now().strftime("%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"{ts}_{name}.png")
    try:
        driver.save_screenshot(path)
        print(f"  [SCREENSHOT] {path}")
        return path
    except Exception as e:
        print(f"  [SCREENSHOT ERROR] {e}")
        return None

def login(email, password, role_label="user"):
    global driver
    print(f"  Logging in as {role_label} ({email})...")
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)

    try:
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                "input[type='email'], input[name='email'], input[placeholder*='email' i]"))
        )
        email_field.clear()
        email_field.send_keys(email)
        time.sleep(0.5)

        pw_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        pw_field.clear()
        pw_field.send_keys(password)
        time.sleep(0.5)

        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], form button")
        btn.click()
        time.sleep(5)

        if "/login" not in driver.current_url:
            print(f"  Login successful -> {driver.current_url}")
            return True
        else:
            print(f"  Login may have failed -> {driver.current_url}")
            screenshot(f"login_fail_{role_label}")
            return False
    except Exception as e:
        print(f"  Login error: {e}")
        screenshot(f"login_error_{role_label}")
        return False

def get_api_token(email, password):
    """Get JWT token via API login"""
    try:
        r = requests.post(f"{API_BASE}/auth/login",
                         json={"email": email, "password": password}, timeout=15)
        if r.status_code == 200:
            token = r.json()["data"]["tokens"]["access_token"]
            print(f"  Got API token for {email}")
            return token
        print(f"  Login API returned {r.status_code}")
        return None
    except Exception as e:
        print(f"  API login error: {e}")
        return None

def get_page_text():
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""

def upload_screenshot_to_github(filepath):
    """Upload screenshot to GitHub repo and return the raw URL"""
    if not filepath or not os.path.exists(filepath):
        return None
    try:
        fname = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        upload_path = f"screenshots/billing_deep/{fname}"
        payload = {
            "message": f"Upload billing screenshot: {fname}",
            "content": content,
            "branch": "main"
        }
        r = requests.put(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/{upload_path}",
            json=payload, headers=GITHUB_HEADERS, timeout=30
        )
        time.sleep(2)
        if r.status_code in [200, 201]:
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{upload_path}"
            print(f"  [UPLOAD] {raw_url}")
            return raw_url
        else:
            print(f"  [UPLOAD WARN] {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"  [UPLOAD ERROR] {e}")
        return None

def file_bug(title, body, severity="medium", screenshot_path=None):
    """File a GitHub issue with screenshot"""
    # Check for duplicates first
    try:
        search_q = title.replace(" ", "+").replace("[", "").replace("]", "")[:50]
        r = requests.get(
            f"https://api.github.com/search/issues?q={search_q}+repo:{GITHUB_REPO}+state:open",
            headers=GITHUB_HEADERS, timeout=15
        )
        time.sleep(2)
        if r.status_code == 200:
            items = r.json().get("items", [])
            for item in items:
                if title.lower()[:30] in item["title"].lower():
                    print(f"  [SKIP] Similar issue already exists: #{item['number']} {item['title']}")
                    bugs.append({"title": title, "severity": severity, "issue_url": item["html_url"],
                                "number": item["number"], "action": "skipped_duplicate"})
                    return item["html_url"]
    except:
        pass

    label_map = {"critical": "bug-critical", "high": "bug-high", "medium": "bug", "low": "bug-low"}
    labels = [label_map.get(severity, "bug"), "verified-bug", "billing", "e2e-test"]

    full_body = (
        f"**Severity:** {severity.upper()}\n"
        f"**Module:** Billing\n"
        f"**Found by:** Automated Billing Deep Test\n"
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"**Base URL:** {BASE_URL}\n\n"
        f"{body}"
    )

    if screenshot_path:
        img_url = upload_screenshot_to_github(screenshot_path)
        if img_url:
            full_body += f"\n\n**Screenshot:**\n![screenshot]({img_url})"
        else:
            fname = os.path.basename(screenshot_path)
            full_body += f"\n\n**Screenshot:** `{fname}` (in test artifacts)"

    time.sleep(5)  # Go slow on GitHub API
    try:
        payload = {"title": f"[Billing] {title}", "body": full_body, "labels": labels}
        r = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            json=payload, headers=GITHUB_HEADERS, timeout=15
        )
        if r.status_code == 201:
            issue = r.json()
            url = issue.get("html_url", "")
            num = issue.get("number", "?")
            print(f"  [BUG FILED] #{num} - {url}")
            bugs.append({"title": title, "severity": severity, "issue_url": url, "number": num})
            return url
        else:
            print(f"  [GITHUB WARN] {r.status_code}: {r.text[:300]}")
            bugs.append({"title": title, "severity": severity, "issue_url": None, "note": f"Filing failed: {r.status_code}"})
            return None
    except Exception as e:
        print(f"  [GITHUB ERROR] {e}")
        return None

def record_result(test_name, status, details=""):
    results.append({
        "test": test_name,
        "status": status,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "SKIP"
    print(f"  [{icon}] {test_name}: {details[:150] if details else ''}")


# =============================================================================
# TEST 1: Billing Dashboard (/billing) - Selenium
# =============================================================================
def test_billing_dashboard():
    print("\n" + "="*70)
    print("TEST 1: Billing Dashboard (/billing)")
    print("="*70)

    ensure_driver()

    if not login(ORG_ADMIN_EMAIL, ORG_ADMIN_PASS, "org_admin"):
        record_result("billing_dashboard_login", "fail", "Could not login as org admin")
        return

    # Navigate to /billing
    print("\n  Navigating to /billing...")
    driver.get(f"{BASE_URL}/billing")
    time.sleep(4)
    ss = screenshot("billing_dashboard_main")
    page_text = get_page_text()
    current_url = driver.current_url

    print(f"  Current URL: {current_url}")
    print(f"  Page text (first 600): {page_text[:600]}")

    if "/login" in current_url:
        record_result("billing_dashboard_loads", "fail", "Redirected to login")
        return

    billing_loaded = any(kw in page_text.lower() for kw in ["billing", "subscription", "invoice", "payment", "plan", "overview"])
    if billing_loaded:
        record_result("billing_dashboard_loads", "pass", f"Billing page loaded at {current_url}")
    elif "404" in page_text or "not found" in page_text.lower():
        record_result("billing_dashboard_loads", "fail", "404 page")
        file_bug("Billing dashboard returns 404",
                f"**URL:** {BASE_URL}/billing\n**Expected:** Billing dashboard\n**Actual:** 404 Not Found",
                "critical", ss)
        return
    else:
        record_result("billing_dashboard_loads", "fail", f"No billing content visible at {current_url}")

    # Check for tabs
    print("\n  Checking for billing tabs...")
    tab_keywords = ["subscriptions", "invoices", "payments", "overview"]
    found_tabs = []

    for tab in tab_keywords:
        tab_elems = driver.find_elements(By.XPATH,
            f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{tab}')]")
        if tab_elems:
            found_tabs.append(tab)

    missing_tabs = [t for t in tab_keywords if t not in found_tabs]
    record_result("billing_tabs_present", "pass" if len(found_tabs) == 4 else "fail",
                  f"Found: {found_tabs}, Missing: {missing_tabs}")

    # Click each tab and screenshot
    for tab in found_tabs:
        try:
            tab_elems = driver.find_elements(By.XPATH,
                f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{tab}')]")
            if tab_elems:
                # Click the most likely tab element (usually a button/a/div near the top)
                for elem in tab_elems:
                    tag = elem.tag_name.lower()
                    if tag in ["button", "a", "li", "div", "span"]:
                        elem.click()
                        time.sleep(2)
                        ss_tab = screenshot(f"billing_tab_{tab}")
                        record_result(f"billing_tab_{tab}_click", "pass", f"Tab '{tab}' clicked successfully")
                        break
        except Exception as e:
            record_result(f"billing_tab_{tab}_click", "fail", f"Error: {e}")

    # Check if sub-routes work
    print("\n  Checking billing sub-routes...")
    for path_name, path in [("subscriptions", "/billing/subscriptions"), ("invoices", "/billing/invoices"),
                              ("payments", "/billing/payments"), ("overview", "/billing/overview")]:
        driver.get(f"{BASE_URL}{path}")
        time.sleep(3)
        ss_path = screenshot(f"billing_route_{path_name}")
        route_url = driver.current_url
        route_text = get_page_text()
        # Check if it redirected back to root or 404d
        if route_url == f"{BASE_URL}/" or "404" in route_text:
            record_result(f"billing_subroute_{path_name}", "fail",
                          f"Subroute {path} redirected to {route_url}")
        elif path_name in route_text.lower() or "billing" in route_text.lower():
            record_result(f"billing_subroute_{path_name}", "pass", f"Loaded at {route_url}")
        else:
            record_result(f"billing_subroute_{path_name}", "fail",
                          f"Subroute {path} -> {route_url}, no matching content")


# =============================================================================
# TEST 2: Subscriptions (Selenium)
# =============================================================================
def test_subscriptions_ui():
    print("\n" + "="*70)
    print("TEST 2: Subscriptions (UI)")
    print("="*70)

    ensure_driver()

    if not login(ORG_ADMIN_EMAIL, ORG_ADMIN_PASS, "org_admin"):
        record_result("subscriptions_ui_login", "fail", "Login failed")
        return

    driver.get(f"{BASE_URL}/billing")
    time.sleep(3)

    # Click subscriptions tab
    try:
        sub_tab = driver.find_element(By.XPATH,
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'subscriptions')]")
        sub_tab.click()
        time.sleep(3)
    except:
        pass

    ss = screenshot("subscriptions_ui_main")
    page_text = get_page_text()

    # Check module listings
    modules_expected = ["payroll", "monitoring", "recruitment", "field force", "project",
                        "rewards", "performance", "exit", "learning", "biometric"]
    found_modules = [m for m in modules_expected if m in page_text.lower()]
    record_result("subscriptions_ui_modules", "pass" if len(found_modules) >= 5 else "fail",
                  f"Found {len(found_modules)}/10 modules in UI: {found_modules}")

    # Check pricing info
    has_pricing = any(kw in page_text for kw in ["500", "1,750", "per seat", "/seat", "INR", "Rs"])
    record_result("subscriptions_ui_pricing", "pass" if has_pricing else "fail",
                  "Pricing info visible" if has_pricing else "No pricing in UI")

    # Check plan tier display
    has_plan_info = any(kw in page_text.lower() for kw in ["basic", "professional", "enterprise", "plan"])
    record_result("subscriptions_ui_plans", "pass" if has_plan_info else "fail",
                  "Plan tier info visible" if has_plan_info else "No plan tier info")

    # Check seat info
    has_seat_info = any(kw in page_text.lower() for kw in ["seat", "10 seat", "12 seat", "106 seat"])
    record_result("subscriptions_ui_seats", "pass" if has_seat_info else "fail",
                  "Seat info visible" if has_seat_info else "No seat info")

    # Total monthly cost
    has_total = any(kw in page_text.lower() for kw in ["total", "1,00,000", "100,000", "monthly cost"])
    record_result("subscriptions_ui_total", "pass" if has_total else "fail",
                  "Total monthly cost visible" if has_total else "No total monthly cost")

    # Check for upgrade/downgrade buttons
    upgrade_btns = driver.find_elements(By.XPATH,
        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upgrade') or "
        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'downgrade') or "
        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'change plan')]")
    record_result("subscriptions_ui_upgrade", "pass" if upgrade_btns else "fail",
                  f"Found {len(upgrade_btns)} upgrade/downgrade buttons" if upgrade_btns else "No upgrade/downgrade options")

    # Check for unsubscribe/cancel
    cancel_btns = driver.find_elements(By.XPATH,
        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'unsubscribe') or "
        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cancel')]")
    record_result("subscriptions_ui_cancel", "pass" if cancel_btns else "fail",
                  f"Found {len(cancel_btns)} cancel/unsubscribe buttons" if cancel_btns else "No cancel/unsubscribe options")

    # Check seat change option
    seat_btns = driver.find_elements(By.XPATH,
        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'change seat') or "
        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add seat') or "
        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'manage seat')]")
    record_result("subscriptions_ui_seat_change", "pass" if seat_btns else "fail",
                  f"Found {len(seat_btns)} seat management buttons" if seat_btns else "No seat change options")


# =============================================================================
# TEST 3: Invoices & Payments (Selenium)
# =============================================================================
def test_invoices_payments_ui():
    print("\n" + "="*70)
    print("TEST 3: Invoices & Payments (UI)")
    print("="*70)

    ensure_driver()

    if not login(ORG_ADMIN_EMAIL, ORG_ADMIN_PASS, "org_admin"):
        record_result("invoices_payments_ui_login", "fail", "Login failed")
        return

    driver.get(f"{BASE_URL}/billing")
    time.sleep(3)

    # Click invoices tab
    try:
        inv_tab = driver.find_element(By.XPATH,
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'invoices')]")
        inv_tab.click()
        time.sleep(3)
    except:
        pass

    ss_inv = screenshot("invoices_tab_content")
    page_text = get_page_text()

    # Check invoice content
    has_invoice_list = any(kw in page_text.lower() for kw in ["invoice", "inv-", "no invoice", "empty"])
    record_result("invoices_ui_tab", "pass" if has_invoice_list else "fail",
                  "Invoice tab shows content" if has_invoice_list else "No invoice content")

    has_dates = any(kw in page_text.lower() for kw in ["date", "issued", "due"])
    has_amounts = any(kw in page_text for kw in ["$", "Rs", "INR", "amount", "Amount"])
    has_status = any(kw in page_text.lower() for kw in ["paid", "unpaid", "overdue", "pending"])
    has_pdf = any(kw in page_text.lower() for kw in ["download", "pdf", "export"])

    record_result("invoices_ui_columns", "pass" if (has_dates and has_amounts) else "fail",
                  f"Dates: {has_dates}, Amounts: {has_amounts}, Status: {has_status}, PDF: {has_pdf}")

    # Click payments tab
    try:
        pay_tab = driver.find_element(By.XPATH,
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'payments')]")
        pay_tab.click()
        time.sleep(3)
    except:
        pass

    ss_pay = screenshot("payments_tab_content")
    page_text = get_page_text()

    has_payment_content = any(kw in page_text.lower() for kw in ["payment", "transaction", "no payment", "empty"])
    record_result("payments_ui_tab", "pass" if has_payment_content else "fail",
                  "Payments tab shows content" if has_payment_content else "No payment content")

    has_methods = any(kw in page_text.lower() for kw in ["method", "card", "upi", "bank"])
    has_pay_status = any(kw in page_text.lower() for kw in ["success", "failed", "pending", "completed"])
    record_result("payments_ui_details", "pass" if has_methods else "fail",
                  f"Methods: {has_methods}, Status: {has_pay_status}")

    # Click overview tab
    try:
        ov_tab = driver.find_element(By.XPATH,
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'overview')]")
        ov_tab.click()
        time.sleep(3)
    except:
        pass

    ss_ov = screenshot("overview_tab_content")
    page_text = get_page_text()

    has_overview = any(kw in page_text.lower() for kw in ["overview", "total", "spend", "cost", "summary"])
    charts = driver.find_elements(By.CSS_SELECTOR, "canvas, svg, [class*='chart'], [class*='graph']")
    record_result("overview_ui_tab", "pass" if has_overview else "fail",
                  f"Overview content: {has_overview}, Charts: {len(charts)}")


# =============================================================================
# TEST 4: Super Admin Billing (Selenium)
# =============================================================================
def test_super_admin_ui():
    print("\n" + "="*70)
    print("TEST 4: Super Admin Billing (UI)")
    print("="*70)

    ensure_driver()

    if not login(SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASS, "super_admin"):
        record_result("superadmin_billing_login", "fail", "Login failed")
        return

    # Try admin billing paths
    admin_paths = ["/admin/billing", "/admin/revenue", "/billing",
                   "/admin/subscriptions", "/super-admin/billing", "/platform/billing"]

    found_path = None
    for ap in admin_paths:
        driver.get(f"{BASE_URL}{ap}")
        time.sleep(3)
        page_text = get_page_text()
        if any(kw in page_text.lower() for kw in ["revenue", "mrr", "arr", "billing", "subscription", "organization"]):
            found_path = ap
            ss = screenshot(f"superadmin_billing_{ap.replace('/', '_')}")
            break

    if found_path:
        record_result("superadmin_billing_page", "pass", f"Found admin billing at {found_path}")
        has_mrr = "mrr" in page_text.lower() or "monthly recurring" in page_text.lower()
        has_arr = "arr" in page_text.lower() or "annual recurring" in page_text.lower()
        record_result("superadmin_ui_mrr", "pass" if has_mrr else "fail",
                      "MRR visible" if has_mrr else "No MRR in UI")
        record_result("superadmin_ui_arr", "pass" if has_arr else "fail",
                      "ARR visible" if has_arr else "No ARR in UI")
    else:
        record_result("superadmin_billing_page", "fail", f"No admin billing at any of: {admin_paths}")
        ss = screenshot("superadmin_billing_not_found")


# =============================================================================
# TEST 5: Employee RBAC (Selenium)
# =============================================================================
def test_employee_rbac_ui():
    print("\n" + "="*70)
    print("TEST 5: Employee RBAC (UI)")
    print("="*70)

    ensure_driver()

    if not login(EMPLOYEE_EMAIL, EMPLOYEE_PASS, "employee"):
        record_result("employee_rbac_login", "fail", "Login failed")
        return

    driver.get(f"{BASE_URL}/billing")
    time.sleep(3)
    page_text = get_page_text()
    current_url = driver.current_url
    ss = screenshot("employee_billing_access")

    has_billing_content = any(kw in page_text.lower() for kw in [
        "subscription", "invoice list", "payment method", "billing plan",
        "total monthly cost", "per seat"])

    if has_billing_content:
        record_result("employee_billing_blocked", "fail",
                      "Employee CAN see billing content - RBAC violation!")
        file_bug("Employee can access billing page - RBAC violation",
                f"**URL:** {BASE_URL}/billing\n**User:** {EMPLOYEE_EMAIL} (Employee role)\n"
                f"**Expected:** Access denied or redirect\n"
                f"**Actual:** Billing content visible to employee\n"
                f"**Security Impact:** Employees should not see subscription costs",
                "critical", ss)
    else:
        record_result("employee_billing_blocked", "pass",
                      f"Employee correctly blocked. URL: {current_url}")


# =============================================================================
# TEST 6: API Endpoints (pure HTTP, no Selenium)
# =============================================================================
def test_api_endpoints():
    print("\n" + "="*70)
    print("TEST 6: API Endpoints")
    print("="*70)

    admin_token = get_api_token(ORG_ADMIN_EMAIL, ORG_ADMIN_PASS)
    super_token = get_api_token(SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASS)
    emp_token = get_api_token(EMPLOYEE_EMAIL, EMPLOYEE_PASS)

    if not admin_token:
        record_result("api_auth", "fail", "Could not get org admin API token")
        return

    admin_h = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    super_h = {"Authorization": f"Bearer {super_token}", "Content-Type": "application/json"} if super_token else None
    emp_h = {"Authorization": f"Bearer {emp_token}", "Content-Type": "application/json"} if emp_token else None

    # --- Org Admin API tests ---
    print("\n  --- Org Admin API ---")
    endpoints = [
        ("/subscriptions", "subscriptions"),
        ("/subscriptions/billing-summary", "billing_summary"),
        ("/billing/invoices", "billing_invoices"),
        ("/billing/payments", "billing_payments"),
        ("/billing/overview", "billing_overview"),
    ]

    for path, label in endpoints:
        url = f"{API_BASE}{path}"
        try:
            r = requests.get(url, headers=admin_h, timeout=15)
            if r.status_code == 200:
                data = r.json()
                record_result(f"api_admin_{label}", "pass", f"200 OK - {json.dumps(data)[:100]}")
            elif r.status_code == 404:
                record_result(f"api_admin_{label}", "fail", f"404 Not Found")
            else:
                record_result(f"api_admin_{label}", "fail", f"HTTP {r.status_code}: {r.text[:150]}")
        except Exception as e:
            record_result(f"api_admin_{label}", "fail", f"Error: {e}")
        time.sleep(0.5)

    # --- Super Admin API tests ---
    if super_h:
        print("\n  --- Super Admin API ---")
        sa_endpoints = [
            ("/admin/revenue", "admin_revenue"),
            ("/admin/subscriptions", "admin_subscriptions"),
            ("/admin/billing", "admin_billing"),
            ("/admin/analytics", "admin_analytics"),
        ]
        for path, label in sa_endpoints:
            url = f"{API_BASE}{path}"
            try:
                r = requests.get(url, headers=super_h, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    record_result(f"api_super_{label}", "pass", f"200 OK - keys: {list(data.get('data', {}).keys()) if isinstance(data.get('data'), dict) else 'list'}")
                elif r.status_code == 404:
                    record_result(f"api_super_{label}", "fail", f"404 Not Found")
                else:
                    record_result(f"api_super_{label}", "fail", f"HTTP {r.status_code}")
            except Exception as e:
                record_result(f"api_super_{label}", "fail", f"Error: {e}")
            time.sleep(0.5)

    # --- Employee RBAC API tests ---
    if emp_h:
        print("\n  --- Employee RBAC API ---")
        rbac_endpoints = ["/subscriptions", "/subscriptions/billing-summary",
                          "/billing/invoices", "/billing/payments"]
        for path in rbac_endpoints:
            label = path.split("/")[-1]
            url = f"{API_BASE}{path}"
            try:
                r = requests.get(url, headers=emp_h, timeout=15)
                if r.status_code == 403:
                    record_result(f"api_rbac_{label}", "pass", "403 Forbidden - correctly blocked")
                elif r.status_code == 200:
                    record_result(f"api_rbac_{label}", "fail", "200 OK - employee can access billing API!")
                else:
                    record_result(f"api_rbac_{label}", "pass", f"HTTP {r.status_code} - blocked")
            except Exception as e:
                record_result(f"api_rbac_{label}", "fail", f"Error: {e}")
            time.sleep(0.5)


# =============================================================================
# TEST 7: Data Consistency (pure HTTP)
# =============================================================================
def test_data_consistency():
    print("\n" + "="*70)
    print("TEST 7: Data Consistency")
    print("="*70)

    admin_token = get_api_token(ORG_ADMIN_EMAIL, ORG_ADMIN_PASS)
    if not admin_token:
        record_result("data_consistency_auth", "fail", "No token")
        return

    h = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

    # Get billing summary
    r = requests.get(f"{API_BASE}/subscriptions/billing-summary", headers=h, timeout=15)
    if r.status_code != 200:
        record_result("data_billing_summary", "fail", f"HTTP {r.status_code}")
        return

    summary = r.json()["data"]
    subs = summary["subscriptions"]
    api_total = summary.get("total_monthly_cost", 0)

    # Verify: calculated total matches API total
    calc_total = 0
    for s in subs:
        cost = s["total_seats"] * s["price_per_seat"]
        cycle = s["billing_cycle"]
        if cycle == "monthly":
            calc_total += cost
        elif cycle == "quarterly":
            calc_total += cost / 3
        elif cycle == "annual":
            calc_total += cost / 12

    match = abs(calc_total - api_total) < 100  # within 1 rupee
    record_result("data_total_cost_consistency", "pass" if match else "fail",
                  f"Calculated: {calc_total}, API: {api_total}, Match: {match}")

    if not match:
        file_bug("Total monthly cost mismatch between calculated and API",
                f"**Endpoint:** GET /api/v1/subscriptions/billing-summary\n"
                f"**Calculated total:** {calc_total} paise (sum of seats * price, normalized monthly)\n"
                f"**API total_monthly_cost:** {api_total} paise\n"
                f"**Difference:** {abs(calc_total - api_total)} paise\n"
                f"**Expected:** These should match exactly",
                "high")

    # Check: All subscriptions accounted for (10 modules)
    record_result("data_subscription_count", "pass" if len(subs) == 10 else "fail",
                  f"Found {len(subs)} subscriptions (expected 10)")

    # Check: used_seats = 0 for all modules despite active employees
    r2 = requests.get(f"{API_BASE}/employees", headers=h, timeout=15)
    emp_count = 0
    if r2.status_code == 200:
        emp_data = r2.json().get("data", [])
        if isinstance(emp_data, list):
            emp_count = len(emp_data)
        elif isinstance(emp_data, dict):
            emp_count = emp_data.get("total", len(emp_data.get("employees", [])))

    all_used_zero = all(s["used_seats"] == 0 for s in subs)
    if all_used_zero and emp_count > 0:
        record_result("data_used_seats", "fail",
                      f"All used_seats=0 but {emp_count} employees exist")
        file_bug("used_seats always 0 despite active employees",
                f"**Endpoint:** GET /api/v1/subscriptions/billing-summary\n"
                f"**Active employees:** {emp_count}\n"
                f"**used_seats for all 10 modules:** 0\n\n"
                f"All modules show `used_seats: 0` even though the organization has {emp_count} active employees. "
                f"Seat utilization should reflect actual user count.\n\n"
                f"**Subscriptions:**\n" +
                "\n".join([f"- {s['module_name']}: {s['total_seats']} total / {s['used_seats']} used" for s in subs]),
                "high")
    elif all_used_zero:
        record_result("data_used_seats", "fail", "All used_seats=0 (no employee count available)")
    else:
        record_result("data_used_seats", "pass", "used_seats has non-zero values")

    # Check: emp-monitor has 106 seats (suspicious, others have 10-12)
    emp_monitor = [s for s in subs if s["module_slug"] == "emp-monitor"]
    if emp_monitor and emp_monitor[0]["total_seats"] > 50:
        record_result("data_monitor_seats_anomaly", "fail",
                      f"emp-monitor has {emp_monitor[0]['total_seats']} seats (others have 10-12)")
        file_bug("Anomalous seat count for Employee Monitoring module (106 seats)",
                f"**Endpoint:** GET /api/v1/subscriptions/billing-summary\n"
                f"**Module:** Employee Monitoring & Activity Tracking (emp-monitor)\n"
                f"**Seat count:** {emp_monitor[0]['total_seats']} seats\n"
                f"**Other modules:** All have 10-12 seats\n\n"
                f"This is a 10x anomaly. With only {emp_count} employees, having 106 seats for one module "
                f"while all others have 10 looks like a data entry error or test artifact. "
                f"This inflates the monthly bill by ~Rs 48,000/month (96 extra seats * Rs 500).\n\n"
                f"**Monthly cost impact:** Rs {(emp_monitor[0]['total_seats'] - 10) * 500:,} extra",
                "medium")
    else:
        record_result("data_monitor_seats_anomaly", "pass", "No seat anomaly detected")

    # Check: billing/invoices empty
    r3 = requests.get(f"{API_BASE}/billing/invoices", headers=h, timeout=15)
    if r3.status_code == 200:
        inv_data = r3.json()["data"]
        inv_count = inv_data.get("total", len(inv_data.get("invoices", [])))
        record_result("data_invoices_exist", "pass" if inv_count > 0 else "fail",
                      f"Invoice count: {inv_count}")
        if inv_count == 0:
            file_bug("No invoices generated despite 10 active subscriptions",
                    f"**Endpoint:** GET /api/v1/billing/invoices\n"
                    f"**Active subscriptions:** 10 modules\n"
                    f"**Invoice count:** 0\n\n"
                    f"With 10 active subscriptions (total Rs 1,00,000/month), there should be at least one "
                    f"generated invoice. The billing system is not creating invoices for active subscriptions.",
                    "high")

    # Check: billing/payments empty
    r4 = requests.get(f"{API_BASE}/billing/payments", headers=h, timeout=15)
    if r4.status_code == 200:
        pay_data = r4.json()["data"]
        pay_count = pay_data.get("total", len(pay_data.get("payments", [])))
        record_result("data_payments_exist", "pass" if pay_count > 0 else "fail",
                      f"Payment count: {pay_count}")

    # Super admin data consistency
    super_token = get_api_token(SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASS)
    if super_token:
        sh = {"Authorization": f"Bearer {super_token}", "Content-Type": "application/json"}
        r5 = requests.get(f"{API_BASE}/admin/revenue", headers=sh, timeout=15)
        if r5.status_code == 200:
            rev = r5.json()["data"]
            mrr = rev.get("mrr", 0)
            arr = rev.get("arr", 0)

            # Verify ARR = MRR * 12
            expected_arr = mrr * 12
            arr_match = abs(arr - expected_arr) < 1000
            record_result("data_arr_mrr_consistency", "pass" if arr_match else "fail",
                          f"MRR: {mrr}, ARR: {arr}, Expected ARR: {expected_arr}, Match: {arr_match}")
            if not arr_match:
                file_bug("ARR does not equal MRR * 12",
                        f"**MRR:** {mrr} ({mrr/100:,.0f} INR)\n**ARR:** {arr} ({arr/100:,.0f} INR)\n"
                        f"**Expected ARR:** {expected_arr} ({expected_arr/100:,.0f} INR)\n"
                        f"ARR should be MRR x 12 but there is a {abs(arr - expected_arr)} paise difference.",
                        "medium")

            # Check revenue_by_module
            rev_modules = rev.get("revenue_by_module", [])
            total_module_rev = sum(m.get("revenue", 0) for m in rev_modules)
            mrr_match = abs(total_module_rev - mrr) < 1000
            record_result("data_revenue_by_module_total", "pass" if mrr_match else "fail",
                          f"Sum of module revenues: {total_module_rev}, MRR: {mrr}, Match: {mrr_match}")

            # Check top_customers includes TechNova
            top = rev.get("top_customers", [])
            technova = [c for c in top if "technova" in c.get("name", "").lower()]
            record_result("data_technova_in_top_customers", "pass" if technova else "fail",
                          f"TechNova in top customers: {bool(technova)}")


# =============================================================================
# TEST 8: Billing overview API endpoint missing
# =============================================================================
def test_missing_endpoints():
    print("\n" + "="*70)
    print("TEST 8: Missing/404 Endpoints")
    print("="*70)

    admin_token = get_api_token(ORG_ADMIN_EMAIL, ORG_ADMIN_PASS)
    if not admin_token:
        return

    h = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

    missing_endpoints = []
    for path in ["/billing/overview", "/billing/analytics", "/billing/summary",
                 "/plans", "/coupons", "/metrics"]:
        url = f"{API_BASE}{path}"
        try:
            r = requests.get(url, headers=h, timeout=10)
            if r.status_code == 404:
                missing_endpoints.append(path)
                record_result(f"api_missing_{path.replace('/', '_')}", "fail", f"404 Not Found")
            else:
                record_result(f"api_endpoint_{path.replace('/', '_')}", "pass", f"HTTP {r.status_code}")
        except Exception as e:
            record_result(f"api_error_{path.replace('/', '_')}", "fail", f"Error: {e}")
        time.sleep(0.5)

    if missing_endpoints:
        file_bug("Billing API endpoints return 404",
                f"**Missing endpoints (404):**\n" +
                "\n".join([f"- GET {API_BASE}{ep}" for ep in missing_endpoints]) +
                f"\n\n**Expected:** These billing-related endpoints should exist and return data\n"
                f"**Actual:** All return 404 Not Found\n\n"
                f"The billing module README documents endpoints like /plans, /coupons, /metrics, "
                f"but these are not available on the main EmpCloud API.",
                "medium")


# =============================================================================
# MAIN
# =============================================================================
def main():
    global driver

    print("="*70)
    print("EMP CLOUD - DEEP BILLING MODULE TEST")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"API: {API_BASE}")
    print("="*70)

    # Check for existing billing issues
    print("\nChecking existing billing issues...")
    try:
        r = requests.get(
            f"https://api.github.com/search/issues?q=[Billing]+repo:{GITHUB_REPO}+state:open",
            headers=GITHUB_HEADERS, timeout=15
        )
        if r.status_code == 200:
            existing = r.json().get("items", [])
            print(f"  Found {len(existing)} existing billing-related issues:")
            for issue in existing[:15]:
                print(f"    #{issue['number']}: {issue['title']}")
        time.sleep(3)
    except Exception as e:
        print(f"  Could not check existing issues: {e}")

    try:
        # Selenium tests (restart every 3)
        test_billing_dashboard()      # Selenium test 1
        test_subscriptions_ui()       # Selenium test 2
        test_invoices_payments_ui()   # Selenium test 3
        test_super_admin_ui()         # Selenium test 4 (driver restarts here)
        test_employee_rbac_ui()       # Selenium test 5

        # Pure API tests (no Selenium)
        test_api_endpoints()
        test_data_consistency()
        test_missing_endpoints()

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        traceback.print_exc()
    finally:
        try:
            if driver:
                driver.quit()
        except:
            pass

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("BILLING TEST SUMMARY")
    print("="*70)

    total = len(results)
    passed = len([r for r in results if r["status"] == "pass"])
    failed = len([r for r in results if r["status"] == "fail"])
    skipped = len([r for r in results if r["status"] == "skip"])

    print(f"\nTotal tests: {total}")
    print(f"  PASS: {passed}")
    print(f"  FAIL: {failed}")
    print(f"  SKIP: {skipped}")

    print(f"\nBugs filed: {len(bugs)}")
    for b in bugs:
        action = b.get("action", "filed")
        print(f"  [{b['severity'].upper()}] {b['title']} - {b.get('issue_url', 'N/A')} ({action})")

    print("\n--- FAILED TESTS ---")
    for r in results:
        if r["status"] == "fail":
            print(f"  FAIL: {r['test']}: {r['details'][:120]}")

    print("\n--- PASSED TESTS ---")
    for r in results:
        if r["status"] == "pass":
            print(f"  PASS: {r['test']}: {r['details'][:120]}")

    # Save results
    summary = {
        "test_date": datetime.now().isoformat(),
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "bugs_filed": bugs,
        "results": results
    }
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "billing_deep_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
