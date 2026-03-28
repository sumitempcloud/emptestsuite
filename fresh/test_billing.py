"""
Fresh E2E Test — Billing Section
Tests: /billing page, tabs, subscription costs, seat utilization,
       Super Admin revenue analytics, employee RBAC
Uses: API + Selenium
"""

import requests
import json
import time
import os
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ── Config ──────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com/api/v1"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_billing"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

CREDS = {
    "org_admin": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"},
    "employee": {"email": "priya@technova.in", "password": "Welcome@123"},
}

RESULTS = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    # Handle non-ASCII chars on Windows console
    safe_msg = str(msg).encode("ascii", "replace").decode("ascii")
    print(f"[{ts}] {safe_msg}")

def record(test_name, status, detail=""):
    RESULTS.append({"test": test_name, "status": status, "detail": detail})
    icon = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "WARN")
    log(f"  [{icon}] {test_name}: {detail}")


# ── API helpers ─────────────────────────────────────────────────────────
def api_login(role):
    cred = CREDS[role]
    r = requests.post(f"{API_URL}/auth/login",
                      json={"email": cred["email"], "password": cred["password"]},
                      timeout=15)
    data = r.json()
    # Token at data.tokens.access_token
    token = None
    d = data.get("data", {})
    if isinstance(d, dict):
        tokens = d.get("tokens", {})
        if isinstance(tokens, dict):
            token = tokens.get("access_token")
        if not token:
            token = d.get("access_token") or d.get("token")
    if not token:
        token = data.get("access_token") or data.get("token")
    return token, data

def api_get(endpoint, token, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_URL}{endpoint}", headers=headers, params=params, timeout=15)
    return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text


# ── Selenium helpers ────────────────────────────────────────────────────
def make_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(3)
    return driver

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"    Screenshot: {path}")
    return path

def selenium_login(driver, role):
    cred = CREDS[role]
    driver.get(f"{BASE_URL}/login")
    time.sleep(2)

    # Try to find email/password fields
    email_input = None
    for sel in ["input[name='email']", "input[type='email']", "#email", "input[name='username']"]:
        try:
            email_input = driver.find_element(By.CSS_SELECTOR, sel)
            break
        except NoSuchElementException:
            continue

    if not email_input:
        # Try by placeholder
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            ph = inp.get_attribute("placeholder") or ""
            if "email" in ph.lower() or "user" in ph.lower():
                email_input = inp
                break
        if not email_input and len(inputs) >= 2:
            email_input = inputs[0]

    pwd_input = None
    for sel in ["input[name='password']", "input[type='password']", "#password"]:
        try:
            pwd_input = driver.find_element(By.CSS_SELECTOR, sel)
            break
        except NoSuchElementException:
            continue

    if email_input and pwd_input:
        email_input.clear()
        email_input.send_keys(cred["email"])
        pwd_input.clear()
        pwd_input.send_keys(cred["password"])

        # Find submit button
        btn = None
        for sel in ["button[type='submit']", "button.login-btn", "button"]:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                for b in btns:
                    txt = b.text.lower()
                    if "login" in txt or "sign in" in txt or "log in" in txt or b.get_attribute("type") == "submit":
                        btn = b
                        break
                if btn:
                    break
            except:
                continue
        if not btn:
            btns = driver.find_elements(By.TAG_NAME, "button")
            if btns:
                btn = btns[-1]

        if btn:
            btn.click()
            time.sleep(3)
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════
# PART 1: API TESTS
# ═══════════════════════════════════════════════════════════════════════
def run_api_tests():
    log("=" * 60)
    log("PART 1: API TESTS")
    log("=" * 60)

    # ── 1A: Login as Org Admin ──────────────────────────────────────
    log("\n--- 1A: Org Admin login ---")
    org_token, org_login_data = api_login("org_admin")
    if org_token:
        record("API-login-org-admin", "PASS", "Token obtained")
    else:
        record("API-login-org-admin", "FAIL", f"No token: {json.dumps(org_login_data)[:200]}")
        return

    # ── 1B: GET /subscriptions ──────────────────────────────────────
    log("\n--- 1B: GET /subscriptions ---")
    status, data = api_get("/subscriptions", org_token)
    log(f"    Status: {status}, Response keys: {list(data.keys()) if isinstance(data, dict) else 'not-dict'}")
    log(f"    Full response (first 500): {json.dumps(data)[:500]}")

    if status == 200:
        record("API-get-subscriptions", "PASS", f"HTTP {status}")
        # Inspect subscription details
        sub_data = data.get("data") or data.get("subscription") or data.get("result") or data
        if isinstance(sub_data, list) and len(sub_data) > 0:
            sub = sub_data[0]
            record("API-subscriptions-has-data", "PASS", f"{len(sub_data)} subscription(s) found")
            log(f"    First subscription: {json.dumps(sub)[:500]}")

            # Check plan name
            plan = sub.get("plan_name") or sub.get("plan") or sub.get("name")
            if plan:
                record("API-subscription-plan-name", "PASS", f"Plan: {plan}")
            else:
                record("API-subscription-plan-name", "WARN", "No plan name field found")

            # Check cost/price
            cost = sub.get("price") or sub.get("cost") or sub.get("amount") or sub.get("monthly_cost")
            if cost is not None:
                record("API-subscription-cost", "PASS", f"Cost: {cost}")
            else:
                record("API-subscription-cost", "WARN", "No cost/price field found in subscription")

            # Seat utilization
            used = sub.get("used_seats") or sub.get("seats_used") or sub.get("active_users")
            total = sub.get("total_seats") or sub.get("max_seats") or sub.get("allowed_seats") or sub.get("seat_limit")
            if used is not None and total is not None:
                pct = (int(used) / int(total) * 100) if int(total) > 0 else 0
                if pct == 0 and int(used) == 0 and int(total) > 0:
                    record("API-seat-utilization", "FAIL", f"Seats used: {used}/{total} = 0% — no seats being used despite active org")
                else:
                    record("API-seat-utilization", "PASS", f"Seats: {used}/{total} = {pct:.0f}%")
            else:
                record("API-seat-utilization", "WARN", f"Seat fields not found. Keys: {list(sub.keys()) if isinstance(sub, dict) else 'N/A'}")

        elif isinstance(sub_data, dict):
            record("API-subscriptions-has-data", "PASS", "Single subscription object")
            log(f"    Subscription: {json.dumps(sub_data)[:500]}")
            plan = sub_data.get("plan_name") or sub_data.get("plan") or sub_data.get("name")
            record("API-subscription-plan-name", "PASS" if plan else "WARN", f"Plan: {plan}" if plan else "No plan name")

            used = sub_data.get("used_seats") or sub_data.get("seats_used") or sub_data.get("active_users")
            total = sub_data.get("total_seats") or sub_data.get("max_seats") or sub_data.get("seat_limit")
            if used is not None and total is not None:
                pct = (int(used) / int(total) * 100) if int(total) > 0 else 0
                if pct == 0:
                    record("API-seat-utilization", "FAIL", f"Seats used: {used}/{total} = 0%")
                else:
                    record("API-seat-utilization", "PASS", f"Seats: {used}/{total} = {pct:.0f}%")
            else:
                record("API-seat-utilization", "WARN", f"Seat fields missing. Keys: {list(sub_data.keys()) if isinstance(sub_data, dict) else 'N/A'}")
        else:
            record("API-subscriptions-has-data", "WARN", f"Unexpected shape: {type(sub_data)}")
    elif status == 404:
        record("API-get-subscriptions", "FAIL", "HTTP 404 — endpoint not found")
    else:
        record("API-get-subscriptions", "FAIL", f"HTTP {status}: {json.dumps(data)[:200]}")

    # ── 1C: Try billing-related endpoints ───────────────────────────
    log("\n--- 1C: Probing billing endpoints ---")
    billing_endpoints = [
        "/billing",
        "/billing/invoices",
        "/billing/payments",
        "/billing/overview",
        "/billing/subscription",
        "/invoices",
        "/payments",
        "/organizations/me/billing",
        "/organizations/me/subscription",
        "/organizations/me/invoices",
    ]
    for ep in billing_endpoints:
        status, data = api_get(ep, org_token)
        summary = json.dumps(data)[:150] if isinstance(data, (dict, list)) else str(data)[:150]
        if status == 200:
            record(f"API-probe{ep.replace('/', '-')}", "PASS", f"HTTP 200: {summary}")
        elif status == 404:
            record(f"API-probe{ep.replace('/', '-')}", "INFO", "HTTP 404")
        else:
            record(f"API-probe{ep.replace('/', '-')}", "INFO", f"HTTP {status}: {summary}")

    # ── 1D: Super Admin login + revenue analytics ───────────────────
    log("\n--- 1D: Super Admin revenue analytics ---")
    sa_token, sa_data = api_login("super_admin")
    if not sa_token:
        record("API-login-super-admin", "FAIL", f"No token: {json.dumps(sa_data)[:200]}")
    else:
        record("API-login-super-admin", "PASS", "Token obtained")

        # Try admin endpoints for revenue/billing
        admin_endpoints = [
            "/admin/organizations",
            "/admin/revenue",
            "/admin/billing",
            "/admin/subscriptions",
            "/admin/analytics",
            "/admin/metrics",
            "/admin/dashboard",
            "/admin/data-sanity",
        ]
        for ep in admin_endpoints:
            status, data = api_get(ep, sa_token)
            summary = json.dumps(data)[:200] if isinstance(data, (dict, list)) else str(data)[:200]
            if status == 200:
                record(f"API-superadmin{ep.replace('/', '-')}", "PASS", f"HTTP 200: {summary}")
            else:
                record(f"API-superadmin{ep.replace('/', '-')}", "INFO", f"HTTP {status}: {summary}")

        # Check org data for subscription/billing info
        status, orgs_data = api_get("/admin/organizations", sa_token)
        if status == 200:
            orgs = orgs_data.get("data") or orgs_data.get("organizations") or orgs_data
            if isinstance(orgs, list) and len(orgs) > 0:
                log(f"    Found {len(orgs)} organizations")
                for org in orgs[:3]:
                    org_name = org.get("name") or org.get("org_name", "Unknown")
                    sub_info = org.get("subscription") or org.get("plan") or org.get("billing")
                    seats = org.get("total_seats") or org.get("max_seats") or org.get("seat_limit")
                    used = org.get("used_seats") or org.get("active_users") or org.get("user_count")
                    log(f"    Org: {org_name}, sub: {sub_info}, seats: {used}/{seats}")
                record("API-superadmin-org-data", "PASS", f"{len(orgs)} orgs found")
            elif isinstance(orgs, dict):
                log(f"    Org data (dict keys): {list(orgs.keys())}")
                record("API-superadmin-org-data", "PASS", "Dict response")

    # ── 1E: Employee RBAC — should NOT access billing ───────────────
    log("\n--- 1E: Employee RBAC for billing ---")
    emp_token, emp_data = api_login("employee")
    if not emp_token:
        record("API-login-employee", "FAIL", f"No token: {json.dumps(emp_data)[:200]}")
    else:
        record("API-login-employee", "PASS", "Token obtained")

        rbac_endpoints = ["/subscriptions", "/billing", "/billing/invoices", "/organizations/me/billing"]
        for ep in rbac_endpoints:
            status, data = api_get(ep, emp_token)
            if status in (401, 403):
                record(f"API-RBAC-employee{ep.replace('/', '-')}", "PASS", f"Correctly blocked: HTTP {status}")
            elif status == 200:
                # Check if data is actually empty or restricted
                payload = data.get("data") or data
                if isinstance(payload, list) and len(payload) == 0:
                    record(f"API-RBAC-employee{ep.replace('/', '-')}", "PASS", "HTTP 200 but empty — acceptable")
                else:
                    record(f"API-RBAC-employee{ep.replace('/', '-')}", "FAIL",
                           f"Employee can access {ep}! HTTP 200 with data: {json.dumps(data)[:150]}")
            elif status == 404:
                record(f"API-RBAC-employee{ep.replace('/', '-')}", "INFO", "HTTP 404 — endpoint doesn't exist")
            else:
                record(f"API-RBAC-employee{ep.replace('/', '-')}", "INFO", f"HTTP {status}")


# ═══════════════════════════════════════════════════════════════════════
# PART 2: SELENIUM TESTS
# ═══════════════════════════════════════════════════════════════════════
def run_selenium_tests():
    log("\n" + "=" * 60)
    log("PART 2: SELENIUM TESTS")
    log("=" * 60)

    driver = None
    try:
        driver = make_driver()

        # ── 2A: Org Admin — Billing page ────────────────────────────
        log("\n--- 2A: Org Admin — /billing page ---")
        selenium_login(driver, "org_admin")
        screenshot(driver, "01_after_login")

        # Check we're logged in
        current = driver.current_url
        log(f"    After login URL: {current}")
        if "/login" in current:
            record("Selenium-org-admin-login", "FAIL", f"Still on login page: {current}")
            return
        record("Selenium-org-admin-login", "PASS", f"Redirected to {current}")

        # Navigate to /billing
        driver.get(f"{BASE_URL}/billing")
        time.sleep(3)
        screenshot(driver, "02_billing_page")

        page_text = driver.find_element(By.TAG_NAME, "body").text
        page_source = driver.page_source
        log(f"    URL: {driver.current_url}")
        log(f"    Page text (first 500): {page_text[:500]}")

        # Check if billing page loaded
        billing_keywords = ["billing", "subscription", "plan", "invoice", "payment", "seat", "usage"]
        found_keywords = [kw for kw in billing_keywords if kw.lower() in page_text.lower()]

        if found_keywords:
            record("Selenium-billing-page-loads", "PASS", f"Keywords found: {found_keywords}")
        elif "not found" in page_text.lower() or "404" in page_text:
            record("Selenium-billing-page-loads", "FAIL", "Page shows 404/not found")
        elif len(page_text.strip()) < 50:
            record("Selenium-billing-page-loads", "FAIL", "Page appears blank/empty")
        else:
            record("Selenium-billing-page-loads", "WARN", f"No billing keywords found. Text: {page_text[:300]}")

        # ── 2B: Check for tabs ──────────────────────────────────────
        log("\n--- 2B: Billing tabs ---")
        tab_names = ["subscriptions", "invoices", "payments", "overview"]

        # Find tab elements — various strategies
        tabs_found = []
        tab_elements = []

        # Strategy 1: role=tab
        tab_els = driver.find_elements(By.CSS_SELECTOR, "[role='tab']")
        if tab_els:
            for t in tab_els:
                txt = t.text.strip().lower()
                tabs_found.append(txt)
                tab_elements.append(t)

        # Strategy 2: common tab selectors
        if not tab_elements:
            for sel in [".tab", ".tabs button", ".tabs a", ".tab-item",
                        "[class*='tab']", "nav a", ".nav-link",
                        "button[class*='tab']", "[data-tab]"]:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els and len(els) >= 2:
                    for e in els:
                        txt = e.text.strip().lower()
                        if txt and any(tn in txt for tn in tab_names):
                            tabs_found.append(txt)
                            tab_elements.append(e)
                    if tabs_found:
                        break

        # Strategy 3: Look for links/buttons with tab-like text
        if not tab_elements:
            all_buttons = driver.find_elements(By.CSS_SELECTOR, "button, a")
            for btn in all_buttons:
                txt = btn.text.strip().lower()
                if txt in tab_names or any(tn in txt for tn in tab_names):
                    tabs_found.append(txt)
                    tab_elements.append(btn)

        if tabs_found:
            record("Selenium-billing-tabs-found", "PASS", f"Tabs: {tabs_found}")
        else:
            record("Selenium-billing-tabs-found", "FAIL", "No billing tabs found on page")
            screenshot(driver, "02b_no_tabs")

        # ── 2C: Click each tab ──────────────────────────────────────
        log("\n--- 2C: Click each tab ---")
        for i, (tab_el, tab_text) in enumerate(zip(tab_elements, tabs_found)):
            try:
                # Scroll into view and click
                driver.execute_script("arguments[0].scrollIntoView(true);", tab_el)
                time.sleep(0.5)
                tab_el.click()
                time.sleep(2)

                ss_name = f"03_tab_{tab_text.replace(' ', '_')}_{i}"
                screenshot(driver, ss_name)

                body_text = driver.find_element(By.TAG_NAME, "body").text
                new_url = driver.current_url

                # Check if content changed
                is_active = False
                try:
                    classes = tab_el.get_attribute("class") or ""
                    aria = tab_el.get_attribute("aria-selected") or ""
                    is_active = "active" in classes or "selected" in classes or aria == "true"
                except:
                    pass

                # Check for content in the tab panel
                content_indicators = {
                    "subscriptions": ["plan", "subscription", "module", "seats", "active"],
                    "invoices": ["invoice", "amount", "date", "paid", "pending", "no invoice"],
                    "payments": ["payment", "transaction", "amount", "date", "no payment"],
                    "overview": ["overview", "usage", "cost", "total", "billing"]
                }

                matched_tab = None
                for tn in tab_names:
                    if tn in tab_text:
                        matched_tab = tn
                        break

                if matched_tab and matched_tab in content_indicators:
                    content_found = [kw for kw in content_indicators[matched_tab] if kw in body_text.lower()]
                    if content_found:
                        record(f"Selenium-tab-{matched_tab}-content", "PASS",
                               f"Tab clicked, content keywords: {content_found}")
                    else:
                        record(f"Selenium-tab-{matched_tab}-content", "WARN",
                               f"Tab clicked but no expected content. Active: {is_active}. Text: {body_text[:200]}")
                else:
                    record(f"Selenium-tab-click-{i}", "PASS" if is_active else "WARN",
                           f"Tab '{tab_text}' clicked. Active: {is_active}")

            except Exception as e:
                record(f"Selenium-tab-click-{tab_text}", "FAIL", f"Click failed: {e}")
                screenshot(driver, f"03_tab_error_{i}")

        # ── 2D: Subscription details ────────────────────────────────
        log("\n--- 2D: Subscription details on page ---")
        body_text = driver.find_element(By.TAG_NAME, "body").text

        # Look for plan info
        plan_keywords = ["enterprise", "professional", "basic", "starter", "pro", "business", "free", "trial"]
        plan_found = [pk for pk in plan_keywords if pk in body_text.lower()]
        if plan_found:
            record("Selenium-plan-visible", "PASS", f"Plan keywords: {plan_found}")
        else:
            record("Selenium-plan-visible", "WARN", "No plan tier names visible")

        # Check for cost/price display
        import re
        price_patterns = [r'\$\d+', r'₹\s*[\d,]+', r'\d+\s*/\s*month', r'\d+\s*/\s*year', r'per\s+seat', r'per\s+user']
        price_found = []
        for pp in price_patterns:
            m = re.search(pp, body_text, re.IGNORECASE)
            if m:
                price_found.append(m.group())
        if price_found:
            record("Selenium-pricing-visible", "PASS", f"Prices: {price_found}")
        else:
            record("Selenium-pricing-visible", "WARN", "No pricing info visible on billing page")

        # Look for seat utilization display
        seat_patterns = [r'(\d+)\s*/\s*(\d+)\s*seat', r'(\d+)\s+of\s+(\d+)', r'seat.*?(\d+)', r'(\d+)\s*%']
        seat_found = []
        for sp in seat_patterns:
            m = re.search(sp, body_text, re.IGNORECASE)
            if m:
                seat_found.append(m.group())
        if seat_found:
            # Check if 0%
            zero_pct = any("0%" in s or "0 /" in s or "0 of" in s for s in seat_found)
            if zero_pct:
                record("Selenium-seat-utilization", "FAIL", f"Seat utilization shows 0%: {seat_found}")
            else:
                record("Selenium-seat-utilization", "PASS", f"Seat info: {seat_found}")
        else:
            record("Selenium-seat-utilization", "WARN", "No seat utilization display found")

        # ── 2E: Invoices check ──────────────────────────────────────
        log("\n--- 2E: Invoices ---")
        # Try to click invoices tab if we found tabs
        for tab_el, tab_text in zip(tab_elements, tabs_found):
            if "invoice" in tab_text:
                try:
                    tab_el.click()
                    time.sleep(2)
                except:
                    pass
                break

        body_text = driver.find_element(By.TAG_NAME, "body").text
        screenshot(driver, "04_invoices_tab")

        if "no invoice" in body_text.lower() or "no data" in body_text.lower() or "no records" in body_text.lower():
            record("Selenium-invoices-empty", "WARN", "No invoices found (may be expected in test env)")
        elif "invoice" in body_text.lower():
            record("Selenium-invoices-content", "PASS", "Invoice content present")
        else:
            record("Selenium-invoices-content", "WARN", "Cannot determine invoice state")

        driver.quit()
        driver = None

        # ── 2F: Super Admin — Revenue/Billing ───────────────────────
        log("\n--- 2F: Super Admin billing/revenue ---")
        driver = make_driver()
        selenium_login(driver, "super_admin")
        time.sleep(2)
        screenshot(driver, "05_superadmin_login")

        current = driver.current_url
        log(f"    SA URL after login: {current}")

        if "/login" in current:
            record("Selenium-super-admin-login", "FAIL", "Still on login page")
        else:
            record("Selenium-super-admin-login", "PASS", f"Logged in: {current}")

            # Navigate to admin/super
            driver.get(f"{BASE_URL}/admin/super")
            time.sleep(3)
            screenshot(driver, "06_super_admin_dashboard")
            body_text = driver.find_element(By.TAG_NAME, "body").text
            log(f"    Super Admin page text (first 500): {body_text[:500]}")

            # Check revenue info
            revenue_kw = ["revenue", "mrr", "arr", "billing", "subscription", "income",
                          "total revenue", "monthly", "annual"]
            rev_found = [kw for kw in revenue_kw if kw in body_text.lower()]
            if rev_found:
                record("Selenium-SA-revenue-visible", "PASS", f"Revenue keywords: {rev_found}")
            else:
                record("Selenium-SA-revenue-visible", "WARN", f"No revenue keywords on SA dashboard")

            # Check org counts / user metrics
            org_kw = ["organization", "total users", "active users", "total org"]
            org_found = [kw for kw in org_kw if kw in body_text.lower()]
            if org_found:
                record("Selenium-SA-org-metrics", "PASS", f"Org metrics: {org_found}")
            else:
                record("Selenium-SA-org-metrics", "WARN", "No org metrics visible")

            # Try /billing as super admin
            driver.get(f"{BASE_URL}/billing")
            time.sleep(3)
            screenshot(driver, "07_sa_billing_page")
            body_text = driver.find_element(By.TAG_NAME, "body").text
            log(f"    SA /billing text (first 300): {body_text[:300]}")

        driver.quit()
        driver = None

        # ── 2G: Employee RBAC — should NOT see billing ──────────────
        log("\n--- 2G: Employee RBAC — billing blocked ---")
        driver = make_driver()
        selenium_login(driver, "employee")
        time.sleep(2)
        screenshot(driver, "08_employee_login")

        current = driver.current_url
        if "/login" in current:
            record("Selenium-employee-login", "FAIL", "Login failed")
        else:
            record("Selenium-employee-login", "PASS", f"Logged in: {current}")

            # Try navigating to /billing
            driver.get(f"{BASE_URL}/billing")
            time.sleep(3)
            screenshot(driver, "09_employee_billing_attempt")

            body_text = driver.find_element(By.TAG_NAME, "body").text
            final_url = driver.current_url
            log(f"    Employee /billing URL: {final_url}")
            log(f"    Employee /billing text: {body_text[:300]}")

            # Check if redirected away or access denied
            if "/billing" not in final_url:
                record("Selenium-RBAC-employee-billing", "PASS",
                       f"Redirected away from /billing to {final_url}")
            elif "access denied" in body_text.lower() or "unauthorized" in body_text.lower() or "not authorized" in body_text.lower() or "permission" in body_text.lower():
                record("Selenium-RBAC-employee-billing", "PASS", "Access denied message shown")
            elif "billing" in body_text.lower() and ("plan" in body_text.lower() or "subscription" in body_text.lower()):
                record("Selenium-RBAC-employee-billing", "FAIL",
                       "Employee CAN see billing page content — RBAC not enforced!")
            else:
                # Check sidebar for billing link
                sidebar_text = ""
                for sel in ["nav", ".sidebar", "[class*='sidebar']", "[class*='nav']", "aside"]:
                    try:
                        el = driver.find_element(By.CSS_SELECTOR, sel)
                        sidebar_text += el.text.lower() + " "
                    except:
                        pass

                if "billing" in sidebar_text:
                    record("Selenium-RBAC-employee-billing-sidebar", "FAIL",
                           "Billing link visible in employee sidebar")
                else:
                    record("Selenium-RBAC-employee-billing-sidebar", "PASS",
                           "Billing link NOT in employee sidebar")

                record("Selenium-RBAC-employee-billing", "WARN",
                       f"Page loaded but unclear if billing data shown. URL: {final_url}")

        if driver:
            driver.quit()

    except Exception as e:
        record("Selenium-unexpected-error", "FAIL", f"{e}\n{traceback.format_exc()}")
        if driver:
            try:
                screenshot(driver, "99_error")
            except:
                pass
            driver.quit()


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
def print_summary():
    log("\n" + "=" * 70)
    log("BILLING TEST SUMMARY")
    log("=" * 70)

    passes = sum(1 for r in RESULTS if r["status"] == "PASS")
    fails = sum(1 for r in RESULTS if r["status"] == "FAIL")
    warns = sum(1 for r in RESULTS if r["status"] == "WARN")
    infos = sum(1 for r in RESULTS if r["status"] == "INFO")

    log(f"PASS: {passes}  |  FAIL: {fails}  |  WARN: {warns}  |  INFO: {infos}")
    log("-" * 70)

    if fails:
        log("\nFAILURES:")
        for r in RESULTS:
            if r["status"] == "FAIL":
                log(f"  FAIL: {r['test']}")
                log(f"        {r['detail']}")

    if warns:
        log("\nWARNINGS:")
        for r in RESULTS:
            if r["status"] == "WARN":
                log(f"  WARN: {r['test']}")
                log(f"        {r['detail']}")

    log(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
    log("=" * 70)


if __name__ == "__main__":
    log("Starting fresh billing E2E test")
    log(f"Timestamp: {datetime.now().isoformat()}")

    run_api_tests()
    run_selenium_tests()
    print_summary()
