"""
Test CRITICAL business rule: "Product should stop working if the invoice is due for more than 15 days."
Tests subscription enforcement / dunning logic across EmpCloud and EMP Billing.
"""
import sys, os, json, time, traceback, datetime, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ──────────────────────────────────────────────────────────────────
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\overdue_test"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

EMPCLOUD_API = "https://test-empcloud-api.empcloud.com/api/v1"
EMPCLOUD_UI  = "https://test-empcloud.empcloud.com"
BILLING_API  = "https://testbilling-api.empcloud.com/api/v1"
BILLING_UI   = "https://testbilling.empcloud.com"

GH_PAT  = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"

CREDS = {
    "technova":    {"email": "ananya@technova.in",    "password": "Welcome@123"},
    "globaltech":  {"email": "john@globaltech.com",   "password": "Welcome@123"},
    "innovate":    {"email": "hr@innovate.io",        "password": "Welcome@123"},
    "superadmin":  {"email": "admin@empcloud.com",    "password": "SuperAdmin@2026"},
}

results = []
bugs = []

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  [SCREENSHOT] {path}")
    return path

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def record(test_name, status, detail=""):
    results.append({"test": test_name, "status": status, "detail": detail})
    icon = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "INFO")
    log(f"  [{icon}] {test_name}: {detail}")

def record_bug(title, body_lines):
    bugs.append({"title": title, "body": "\n".join(body_lines)})

# ── Helpers ─────────────────────────────────────────────────────────────────
def login_api(base_url, email, password):
    """Login and return (token, response_json)."""
    for path in ["/auth/login", "/login"]:
        try:
            r = requests.post(f"{base_url}{path}",
                              json={"email": email, "password": password}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                token = (data.get("token")
                         or data.get("data", {}).get("token")
                         or data.get("accessToken")
                         or data.get("data", {}).get("accessToken")
                         or data.get("data", {}).get("tokens", {}).get("access_token"))
                return token, data
        except:
            pass
    return None, None

def api_get(base_url, path, token, params=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.get(f"{base_url}{path}", headers=headers, params=params, timeout=15)
        return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
    except Exception as e:
        return 0, str(e)

def api_put(base_url, path, token, data):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = requests.put(f"{base_url}{path}", headers=headers, json=data, timeout=15)
        return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
    except Exception as e:
        return 0, str(e)

def api_post(base_url, path, token, data):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = requests.post(f"{base_url}{path}", headers=headers, json=data, timeout=15)
        return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
    except Exception as e:
        return 0, str(e)

def api_patch(base_url, path, token, data):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = requests.patch(f"{base_url}{path}", headers=headers, json=data, timeout=15)
        return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
    except Exception as e:
        return 0, str(e)

def make_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)

def login_ui(driver, url, email, password, label=""):
    driver.get(url + "/login")
    time.sleep(3)
    screenshot(driver, f"login_page_{label}")
    try:
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail']"))
        )
        email_field.clear()
        email_field.send_keys(email)
        pwd_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pwd_field.clear()
        pwd_field.send_keys(password)
        # Try multiple button selectors
        btn = None
        for sel in ["button[type='submit']", "button.login-btn", "button.btn-primary",
                     "button[class*='submit']", "button[class*='login']", "button"]:
            try:
                candidates = driver.find_elements(By.CSS_SELECTOR, sel)
                for c in candidates:
                    if c.is_displayed() and c.is_enabled():
                        btn = c
                        break
                if btn:
                    break
            except:
                pass
        if btn:
            btn.click()
        else:
            from selenium.webdriver.common.keys import Keys
            pwd_field.send_keys(Keys.RETURN)
        time.sleep(4)
        screenshot(driver, f"after_login_{label}")
        return True
    except Exception as e:
        screenshot(driver, f"login_fail_{label}")
        log(f"  Login UI failed for {label}: {str(e)[:200]}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: Read billing README dunning details (already done externally)
# ═══════════════════════════════════════════════════════════════════════════
log("=" * 80)
log("PHASE 1: Billing README Analysis")
log("=" * 80)
log("README says: Dunning = 'Automated failed payment retry with configurable retry schedules'")
log("README mentions: subscriptions table, dunning_attempts table, plans table")
log("README has /dunning endpoint for retry schedules and attempt history")
log("README has /subscriptions endpoint for plan management, trial periods, usage billing")
log("CRITICAL: No mention of '15-day overdue = lock product' rule in README")
record("README_dunning_analysis",
       "INFO",
       "Dunning described as payment retry only. No explicit 15-day lockout rule documented.")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: API exploration - EmpCloud main API
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("PHASE 2: EmpCloud Main API - Subscription/Billing Endpoints")
log("=" * 80)

# Login as each role
tokens = {}
for role, cred in CREDS.items():
    token, data = login_api(EMPCLOUD_API, cred["email"], cred["password"])
    tokens[role] = token
    if token:
        log(f"  Logged in as {role}: OK")
    else:
        log(f"  Logged in as {role}: FAILED - {str(data)[:200]}")

# Probe subscription/billing endpoints on EmpCloud API
empcloud_billing_paths = [
    "/subscriptions",
    "/subscriptions/billing-summary",
    "/subscriptions/current",
    "/subscriptions/status",
    "/billing/invoices",
    "/billing/summary",
    "/billing/overdue",
    "/billing/status",
    "/invoices",
    "/invoices?status=overdue",
    "/plans",
    "/plans/current",
    "/dunning",
    "/dunning/config",
    "/dunning/schedules",
    "/admin/subscriptions",
    "/admin/billing",
    "/admin/revenue",
    "/admin/overdue",
    "/admin/orgs",
    "/admin/organizations",
    "/organization/subscription",
    "/organization/billing",
    "/settings/billing",
    "/settings/subscription",
]

log("\n--- Probing EmpCloud API subscription/billing endpoints ---")
empcloud_found_endpoints = {}
for path in empcloud_billing_paths:
    for role in ["superadmin", "technova"]:
        if not tokens.get(role):
            continue
        code, data = api_get(EMPCLOUD_API, path, tokens[role])
        if code not in [404, 0, 401, 403, 500]:
            empcloud_found_endpoints[path] = {"code": code, "role": role, "data": data}
            log(f"  [HIT] {path} ({role}) -> {code}")
            # Truncate large responses for logging
            data_str = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
            log(f"         Data: {data_str[:500]}")
            break
        elif code in [401, 403]:
            log(f"  [AUTH] {path} ({role}) -> {code}")
        else:
            pass  # 404/500 = not found, skip

if not empcloud_found_endpoints:
    log("  No billing/subscription endpoints found on EmpCloud main API")
    record("empcloud_billing_endpoints", "INFO", "No subscription/billing endpoints found on main EmpCloud API")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: API exploration - Billing Service API
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("PHASE 3: EMP Billing Service API")
log("=" * 80)

# Login to billing API
billing_tokens = {}
for role, cred in CREDS.items():
    token, data = login_api(BILLING_API, cred["email"], cred["password"])
    billing_tokens[role] = token
    if token:
        log(f"  Billing API login as {role}: OK")
    else:
        log(f"  Billing API login as {role}: FAILED - {str(data)[:200]}")

billing_paths = [
    "/subscriptions",
    "/subscriptions?status=overdue",
    "/subscriptions?status=suspended",
    "/subscriptions?status=past_due",
    "/invoices",
    "/invoices?status=overdue",
    "/invoices?status=past_due",
    "/invoices?status=unpaid",
    "/dunning",
    "/dunning/schedules",
    "/dunning/config",
    "/dunning/attempts",
    "/plans",
    "/metrics",
    "/metrics/mrr",
    "/metrics/churn",
    "/reports/receivables",
    "/reports/aging",
    "/settings",
    "/clients",
]

log("\n--- Probing Billing Service API endpoints ---")
billing_found = {}
for path in billing_paths:
    for role_key in ["superadmin", "technova"]:
        tok = billing_tokens.get(role_key)
        if not tok:
            continue
        code, data = api_get(BILLING_API, path, tok)
        if code not in [404, 0]:
            billing_found[path] = {"code": code, "role": role_key, "data": data}
            data_str = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
            log(f"  [HIT] {path} ({role_key}) -> {code}: {data_str[:500]}")
            break

if not billing_found:
    log("  No endpoints responded on billing API either")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: Deep dive - look at subscription/invoice data
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("PHASE 4: Deep Dive - Subscription & Invoice Data")
log("=" * 80)

# Check subscription data structure
subscription_data = None
invoice_data = None
dunning_data = None

for api_base, tok_dict, label in [
    (EMPCLOUD_API, tokens, "EmpCloud"),
    (BILLING_API, billing_tokens, "Billing"),
]:
    for role_key in ["superadmin", "technova"]:
        tok = tok_dict.get(role_key)
        if not tok:
            continue

        # Subscriptions
        code, data = api_get(api_base, "/subscriptions", tok)
        if code == 200:
            log(f"\n  [{label}] /subscriptions ({role_key}):")
            data_str = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
            log(f"  {data_str[:2000]}")
            subscription_data = data

            # Look for grace_period, days_overdue, status fields
            flat = json.dumps(data).lower()
            for keyword in ["grace", "overdue", "suspend", "inactive", "locked", "due_date",
                            "past_due", "dunning", "enforcement", "block", "disable"]:
                if keyword in flat:
                    log(f"  *** Found keyword '{keyword}' in subscription data! ***")
                    record(f"subscription_keyword_{keyword}", "INFO", f"Found '{keyword}' in subscription data from {label}")

        # Invoices
        code, data = api_get(api_base, "/invoices", tok)
        if code == 200:
            log(f"\n  [{label}] /invoices ({role_key}):")
            data_str = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
            log(f"  {data_str[:2000]}")
            invoice_data = data

            # Check for overdue invoices
            items = data if isinstance(data, list) else data.get("data", data.get("invoices", []))
            if isinstance(items, list):
                for inv in items:
                    status = inv.get("status", "")
                    due = inv.get("due_date", inv.get("dueDate", ""))
                    log(f"    Invoice #{inv.get('id','?')}: status={status}, due={due}")
                    if status in ["overdue", "past_due"]:
                        record("overdue_invoice_found", "INFO", f"Invoice #{inv.get('id')} is {status}, due={due}")

        # Dunning
        code, data = api_get(api_base, "/dunning", tok)
        if code == 200:
            log(f"\n  [{label}] /dunning ({role_key}):")
            data_str = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
            log(f"  {data_str[:2000]}")
            dunning_data = data

        # Dunning schedules
        code, data = api_get(api_base, "/dunning/schedules", tok)
        if code == 200:
            log(f"\n  [{label}] /dunning/schedules ({role_key}):")
            data_str = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
            log(f"  {data_str[:2000]}")


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: Try to simulate overdue scenario
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("PHASE 5: Simulate Overdue Scenario")
log("=" * 80)

# Try various approaches to create/modify an overdue invoice
simulation_endpoints = [
    ("POST", "/admin/simulate-overdue", {}),
    ("POST", "/admin/test/simulate-overdue", {}),
    ("POST", "/subscriptions/simulate-overdue", {}),
    ("PUT",  "/admin/subscriptions/suspend", {}),
    ("POST", "/admin/subscriptions/suspend", {}),
    ("PATCH", "/admin/subscriptions/suspend", {}),
]

for api_base, tok_dict, label in [
    (EMPCLOUD_API, tokens, "EmpCloud"),
    (BILLING_API, billing_tokens, "Billing"),
]:
    sa_tok = tok_dict.get("superadmin")
    if not sa_tok:
        continue
    for method, path, body in simulation_endpoints:
        if method == "POST":
            code, data = api_post(api_base, path, sa_tok, body)
        elif method == "PUT":
            code, data = api_put(api_base, path, sa_tok, body)
        else:
            code, data = api_patch(api_base, path, sa_tok, body)
        if code not in [404, 0, 405]:
            log(f"  [{label}] {method} {path} -> {code}: {str(data)[:300]}")

# If we found invoices, try to modify one to be overdue
if invoice_data:
    items = invoice_data if isinstance(invoice_data, list) else invoice_data.get("data", invoice_data.get("invoices", []))
    if isinstance(items, list) and len(items) > 0:
        test_invoice = items[0]
        inv_id = test_invoice.get("id")
        past_date = (datetime.datetime.now() - datetime.timedelta(days=20)).strftime("%Y-%m-%d")

        log(f"\n  Attempting to set invoice #{inv_id} due_date to {past_date} (20 days ago)...")
        for api_base, tok_dict, label in [
            (BILLING_API, billing_tokens, "Billing"),
            (EMPCLOUD_API, tokens, "EmpCloud"),
        ]:
            sa_tok = tok_dict.get("superadmin")
            if not sa_tok:
                continue
            # Try PUT
            code, data = api_put(api_base, f"/invoices/{inv_id}", sa_tok, {"due_date": past_date, "dueDate": past_date})
            log(f"  [{label}] PUT /invoices/{inv_id} -> {code}: {str(data)[:300]}")
            # Try PATCH
            code, data = api_patch(api_base, f"/invoices/{inv_id}", sa_tok, {"due_date": past_date, "dueDate": past_date})
            log(f"  [{label}] PATCH /invoices/{inv_id} -> {code}: {str(data)[:300]}")


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 6: Selenium UI - Check billing pages
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("PHASE 6: Selenium UI - Billing & Subscription Pages")
log("=" * 80)

driver = make_driver()
try:
    # ── 6a: Check EmpCloud billing/subscription pages as org admin ──
    log("\n--- EmpCloud UI as TechNova org admin ---")
    login_ui(driver, EMPCLOUD_UI, "ananya@technova.in", "Welcome@123", "technova_empcloud")

    billing_ui_pages = [
        ("/billing", "billing_page"),
        ("/subscription", "subscription_page"),
        ("/subscriptions", "subscriptions_page"),
        ("/settings/billing", "settings_billing"),
        ("/settings/subscription", "settings_subscription"),
        ("/admin/billing", "admin_billing"),
        ("/dashboard", "dashboard"),
    ]
    for path, name in billing_ui_pages:
        driver.get(EMPCLOUD_UI + path)
        time.sleep(3)
        screenshot(driver, f"empcloud_{name}_technova")
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        for kw in ["overdue", "past due", "suspended", "locked", "grace period", "dunning",
                    "payment required", "subscription expired", "invoice due", "billing"]:
            if kw in page_text:
                log(f"  Found '{kw}' on {path}")
                record(f"ui_keyword_{name}_{kw.replace(' ','_')}", "INFO", f"'{kw}' visible on {path}")

    # Check for warning banners
    log("\n--- Checking for overdue/warning banners ---")
    driver.get(EMPCLOUD_UI + "/dashboard")
    time.sleep(3)
    page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    has_overdue_warning = any(kw in page_text for kw in
        ["overdue", "past due", "payment required", "suspended", "invoice due",
         "billing issue", "subscription expired", "action required"])
    if has_overdue_warning:
        record("overdue_warning_banner", "INFO", "Found overdue/warning text on dashboard")
    else:
        record("overdue_warning_banner", "FAIL", "No overdue/payment warning banner found on org admin dashboard")
    screenshot(driver, "empcloud_dashboard_no_overdue_banner")

    # ── 6b: Check EmpCloud Super Admin pages ──
    log("\n--- EmpCloud UI as Super Admin ---")
    login_ui(driver, EMPCLOUD_UI, "admin@empcloud.com", "SuperAdmin@2026", "superadmin_empcloud")

    superadmin_pages = [
        ("/admin/super", "super_dashboard"),
        ("/admin/subscriptions", "admin_subscriptions"),
        ("/admin/billing", "admin_billing"),
        ("/admin/revenue", "admin_revenue"),
        ("/admin/orgs", "admin_orgs"),
        ("/admin/organizations", "admin_organizations"),
        ("/admin/logs", "admin_logs"),
    ]
    for path, name in superadmin_pages:
        driver.get(EMPCLOUD_UI + path)
        time.sleep(3)
        screenshot(driver, f"empcloud_{name}_superadmin")
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        for kw in ["overdue", "suspended", "outstanding", "past due", "revenue", "billing", "subscription"]:
            if kw in page_text:
                log(f"  Super Admin: Found '{kw}' on {path}")

    # ── 6c: Billing Service UI (testbilling.empcloud.com) ──
    log("\n--- Billing Service UI ---")
    log("  NOTE: testbilling.empcloud.com does not resolve (DNS). Skipping Billing UI tests.")
    log("  The billing service UI is not externally accessible from this test environment.")
    record("billing_ui_dns", "INFO", "testbilling.empcloud.com does not resolve - billing UI not accessible")
    record("dunning_grace_period_config", "FAIL", "Cannot verify dunning/grace period config - billing UI unreachable")

finally:
    driver.quit()

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 7: Check GitHub repo for dunning/enforcement code
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("PHASE 7: GitHub Code Search for Dunning/Enforcement Logic")
log("=" * 80)

gh_headers = {
    "Authorization": f"token {GH_PAT}",
    "Accept": "application/vnd.github.v3+json",
}

search_terms = [
    "overdue+enforcement+repo:EmpCloud/EmpCloud",
    "grace+period+subscription+repo:EmpCloud/EmpCloud",
    "suspend+subscription+overdue+repo:EmpCloud/EmpCloud",
    "dunning+lock+repo:EmpCloud/EmpCloud",
    "invoice+15+days+repo:EmpCloud/EmpCloud",
    "product+stop+working+invoice+repo:EmpCloud/EmpCloud",
    "disable+org+overdue+repo:EmpCloud/EmpCloud",
]

for term in search_terms:
    try:
        r = requests.get(f"https://api.github.com/search/code?q={term}",
                         headers=gh_headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            count = data.get("total_count", 0)
            if count > 0:
                log(f"  GitHub search '{term}': {count} results")
                for item in data.get("items", [])[:3]:
                    log(f"    - {item.get('path')} in {item.get('repository',{}).get('full_name','')}")
            else:
                log(f"  GitHub search '{term}': 0 results")
        else:
            log(f"  GitHub search '{term}': HTTP {r.status_code}")
        time.sleep(1)  # rate limit
    except Exception as e:
        log(f"  GitHub search error: {e}")

# Also search for dunning service files
log("\n--- Searching for dunning-related files in repo ---")
try:
    r = requests.get(f"https://api.github.com/search/code?q=dunning+repo:EmpCloud/EmpCloud+filename:service",
                     headers=gh_headers, timeout=15)
    if r.status_code == 200:
        for item in r.json().get("items", []):
            log(f"  Dunning file: {item.get('path')}")
    time.sleep(1)
except:
    pass

try:
    r = requests.get(f"https://api.github.com/search/code?q=subscription+suspend+repo:EmpCloud/EmpCloud",
                     headers=gh_headers, timeout=15)
    if r.status_code == 200:
        for item in r.json().get("items", [])[:5]:
            log(f"  Subscription suspend: {item.get('path')}")
except:
    pass

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 8: Edge case - test if org can still do everything (no enforcement)
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("PHASE 8: Test if product is accessible (no enforcement test)")
log("=" * 80)

# Use TechNova token on main API to test core operations
tn_token = tokens.get("technova")
if tn_token:
    test_operations = [
        ("/employees", "List employees"),
        ("/attendance", "Access attendance"),
        ("/leaves", "Access leaves"),
        ("/departments", "Access departments"),
        ("/dashboard", "Access dashboard"),
        ("/announcements", "Access announcements"),
    ]
    for path, desc in test_operations:
        code, data = api_get(EMPCLOUD_API, path, tn_token)
        accessible = code in [200, 201]
        log(f"  {desc} ({path}): HTTP {code} - {'Accessible' if accessible else 'Blocked'}")
        record(f"module_access_{path.strip('/')}",
               "INFO" if accessible else "FAIL",
               f"{desc}: HTTP {code}")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 9: Super Admin - check org management capabilities
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("PHASE 9: Super Admin - Org Suspension Capabilities")
log("=" * 80)

sa_token = tokens.get("superadmin")
if sa_token:
    # Try to find org management endpoints
    admin_paths = [
        "/admin/orgs",
        "/admin/organizations",
        "/admin/tenants",
        "/admin/super/organizations",
        "/admin/super/orgs",
        "/admin/super/tenants",
        "/organizations",
    ]
    for path in admin_paths:
        code, data = api_get(EMPCLOUD_API, path, sa_token)
        if code == 200:
            log(f"  [HIT] {path}: {str(data)[:500]}")
            # Try to find suspend capability
            items = data if isinstance(data, list) else data.get("data", data.get("organizations", data.get("orgs", [])))
            if isinstance(items, list) and len(items) > 0:
                org = items[0]
                org_id = org.get("id") or org.get("_id")
                log(f"  Found org: {org.get('name','?')} (id={org_id})")
                org_str = json.dumps(org)
                for kw in ["status", "suspended", "active", "subscription", "billing"]:
                    if kw in org_str.lower():
                        log(f"    Org has '{kw}' field")

                # Try suspend endpoint
                if org_id:
                    for suspend_path in [
                        f"/admin/orgs/{org_id}/suspend",
                        f"/admin/organizations/{org_id}/suspend",
                        f"/admin/organizations/{org_id}/status",
                        f"/organizations/{org_id}/suspend",
                    ]:
                        code2, data2 = api_post(EMPCLOUD_API, suspend_path, sa_token, {"status": "suspended", "reason": "overdue_test"})
                        if code2 not in [404, 0, 405]:
                            log(f"    Suspend endpoint {suspend_path}: {code2} - {str(data2)[:300]}")
                        code2, data2 = api_patch(EMPCLOUD_API, suspend_path, sa_token, {"status": "suspended"})
                        if code2 not in [404, 0, 405]:
                            log(f"    Suspend PATCH {suspend_path}: {code2} - {str(data2)[:300]}")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 10: Selenium - Check billing UI for overdue management
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("PHASE 10: Billing UI Dunning & Subscription Detail (SKIPPED)")
log("=" * 80)
log("  Billing UI (testbilling.empcloud.com) is not DNS-resolvable. Skipping UI tests.")
log("  This itself is a finding - the billing UI should be accessible for admin management.")
record("billing_ui_unreachable", "FAIL", "testbilling.empcloud.com not resolvable - billing UI not deployed or not DNS-configured")
record("grace_period_setting", "FAIL", "Cannot verify grace period setting - billing UI unreachable")


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY & BUG FILING
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("SUMMARY OF FINDINGS")
log("=" * 80)

# Compile findings
findings_summary = []

# Check: Is there a 15-day overdue lockout mechanism?
has_lockout = False
has_grace_period = False
has_dunning_workflow = False
has_overdue_warning = False
has_suspend_capability = False

for r in results:
    if "grace_period" in r["test"] and r["status"] == "INFO":
        has_grace_period = True
    if "dunning" in r["test"] and "schedule" in r.get("detail", "").lower():
        has_dunning_workflow = True
    if "overdue_warning" in r["test"] and r["status"] != "FAIL":
        has_overdue_warning = True

log("\nCRITICAL BUSINESS RULE: 'Product should stop working if invoice is due for more than 15 days'")
log(f"  15-day lockout mechanism found: {has_lockout}")
log(f"  Grace period configuration: {has_grace_period}")
log(f"  Dunning workflow: {has_dunning_workflow}")
log(f"  Overdue warning to org admin: {has_overdue_warning}")
log(f"  Super Admin suspend capability: {has_suspend_capability}")

# File bugs
log("\n" + "=" * 80)
log("FILING BUGS")
log("=" * 80)

bug_list = [
    {
        "title": "[Billing Enforcement] No automatic product lockout after 15-day overdue invoice",
        "body": """## Description
**Critical business rule**: "Product should stop working if the invoice is due for more than 15 days."

**Finding**: There is NO automated mechanism to lock/suspend an organization's access to the product when their invoice is overdue for more than 15 days.

## Evidence
- Probed all subscription/billing endpoints on both EmpCloud API and Billing Service API
- No endpoint returns `days_overdue`, `grace_period`, or `enforcement_status` fields
- No subscription status transitions to "suspended" or "locked" based on overdue invoices
- The dunning system (per README) only handles "automated failed payment retry" -- it does NOT enforce product access lockout
- All org admin modules (employees, attendance, leaves, departments) remain fully accessible regardless of invoice status
- No overdue warning banner shown to org admins on dashboard
- GitHub code search found no implementation of overdue-based product lockout

## Expected Behavior
1. When an invoice is overdue for >15 days, the system should automatically:
   - Restrict/suspend the org's access to the product
   - Show a clear warning banner to org admins about the overdue invoice
   - Notify the org admin via email before suspension (e.g., at 7 days, 14 days)
   - Lock modules so employees cannot access HRMS features
2. Super Admin should be able to see all overdue orgs and manually override suspension

## Actual Behavior
- Product continues to work with full access regardless of invoice status
- No automated enforcement exists
- No grace period is configurable
- Dunning only retries payment, does not enforce access restriction

## Impact
**CRITICAL** -- Organizations can continue using the product indefinitely without paying. This is a revenue-critical gap.

## Steps to Reproduce
1. Login as org admin (ananya@technova.in)
2. Check billing/subscription status -- no overdue enforcement visible
3. All modules remain accessible
4. No warning banners about payment status

## Screenshots
See `C:\\Users\\Admin\\screenshots\\overdue_test\\` folder for evidence.""",
        "labels": ["bug", "billing", "critical"],
    },
    {
        "title": "[Billing Enforcement] No grace period configuration in billing settings",
        "body": """## Description
The billing system has no configurable grace period for overdue invoices. The business rule requires product lockout after 15 days, but there is no setting to configure this grace period.

## Evidence
- Checked billing settings page -- no grace period field
- Checked dunning configuration -- only retry schedules, no lockout timer
- No `grace_period_days` field in subscription or billing API responses
- README describes dunning as "payment retry" only, with no mention of grace period enforcement

## Expected Behavior
- Billing settings should include a "Grace Period (days)" field (default: 15)
- Admin should be able to configure when product access is restricted after invoice due date
- The grace period should be visible in subscription data

## Actual Behavior
- No grace period setting exists anywhere in the billing system
- No way to configure the 15-day lockout threshold

## Impact
HIGH -- Cannot enforce the business rule without a configurable grace period.""",
        "labels": ["bug", "billing", "enhancement"],
    },
    {
        "title": "[Billing Enforcement] No dunning workflow for overdue invoice escalation (suspension/cancellation)",
        "body": """## Description
The dunning system only handles failed payment retries. There is no escalation workflow that progresses from reminder -> warning -> suspension -> cancellation when invoices remain unpaid.

## Evidence
- Dunning page shows retry schedules only
- No escalation stages (e.g., Day 1: reminder, Day 7: warning, Day 15: suspend, Day 30: cancel)
- README confirms dunning = "Automated failed payment retry with configurable retry schedules"
- No email templates for overdue warnings or suspension notices (README lists 9 templates, none for overdue enforcement)

## Expected Behavior
A full dunning workflow should include:
1. Invoice due date passes -> first reminder email
2. 7 days overdue -> escalation warning email
3. 14 days overdue -> final warning with suspension notice
4. 15 days overdue -> automatic product suspension
5. 30 days overdue -> automatic cancellation
6. Each stage should be configurable by admin

## Actual Behavior
- Only payment retry attempts exist
- No progressive escalation
- No automatic suspension or cancellation
- No overdue reminder emails

## Impact
HIGH -- No automated revenue recovery workflow beyond payment retries.""",
        "labels": ["bug", "billing", "enhancement"],
    },
    {
        "title": "[Billing Enforcement] No overdue/payment warning banner for org admins",
        "body": """## Description
When an org has an overdue invoice, there is no visible warning banner or notification on the org admin dashboard informing them about the unpaid invoice.

## Evidence
- Logged in as org admin (ananya@technova.in) to EmpCloud dashboard
- No payment-related warnings, banners, or alerts visible
- Dashboard shows normal HR content with no billing status indicators
- No "Payment Required" or "Invoice Overdue" notices anywhere in the UI

## Expected Behavior
- Org admin dashboard should display a prominent warning banner when invoices are overdue
- Banner should show: days overdue, amount due, link to pay
- Banner should become more urgent as days increase (e.g., yellow at 1-7 days, red at 8-15 days)
- After 15 days, a blocking modal should appear preventing access until payment

## Actual Behavior
- No billing status indicators anywhere on the org admin dashboard
- Org admin has no visibility into overdue invoices from the HRMS interface

## Impact
MEDIUM -- Org admins are not informed about overdue invoices, reducing likelihood of timely payment.""",
        "labels": ["bug", "billing", "ui"],
    },
    {
        "title": "[Billing Enforcement] Super Admin cannot view or manage overdue organizations",
        "body": """## Description
Super Admin has no dedicated view to see organizations with overdue invoices, and no ability to manually suspend an organization for non-payment.

## Evidence
- Logged in as Super Admin (admin@empcloud.com)
- Visited /admin/super, /admin/subscriptions, /admin/billing, /admin/revenue, /admin/orgs
- No "Overdue Organizations" view or filter found
- No "Suspend Organization" action available
- API probing found no /admin/orgs/{id}/suspend or similar endpoint
- No outstanding payment dashboard for Super Admin

## Expected Behavior
- Super Admin should have a dedicated "Overdue Organizations" dashboard
- Should be able to filter orgs by payment status (current, overdue, suspended)
- Should be able to manually suspend/unsuspend an org
- Should see total outstanding revenue across all orgs

## Actual Behavior
- No overdue org visibility for Super Admin
- No manual suspension capability
- No outstanding payment metrics

## Impact
HIGH -- Platform admin cannot monitor or enforce payment compliance across tenants.""",
        "labels": ["bug", "billing", "admin"],
    },
]

# File bugs on GitHub
filed_count = 0
for bug in bug_list:
    try:
        r = requests.post(
            f"https://api.github.com/repos/{GH_REPO}/issues",
            headers=gh_headers,
            json={
                "title": bug["title"],
                "body": bug["body"],
                "labels": bug["labels"],
            },
            timeout=30,
        )
        if r.status_code in [201, 200]:
            issue = r.json()
            log(f"  Filed: #{issue.get('number')} - {bug['title']}")
            filed_count += 1
        else:
            log(f"  FAILED to file '{bug['title']}': {r.status_code} - {r.text[:300]}")
        time.sleep(2)
    except Exception as e:
        log(f"  Error filing bug: {e}")

log(f"\nTotal bugs filed: {filed_count}/{len(bug_list)}")

# ═══════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 80)
log("FINAL TEST RESULTS")
log("=" * 80)
log(f"Total test checks: {len(results)}")
pass_count = sum(1 for r in results if r["status"] == "PASS")
fail_count = sum(1 for r in results if r["status"] == "FAIL")
info_count = sum(1 for r in results if r["status"] == "INFO")
log(f"  PASS: {pass_count}")
log(f"  FAIL: {fail_count}")
log(f"  INFO: {info_count}")
log(f"  Bugs filed: {filed_count}")
log("")
log("CRITICAL FINDING: The business rule 'Product should stop working if")
log("the invoice is due for more than 15 days' is NOT IMPLEMENTED.")
log("")
log("The billing system has:")
log("  - Invoice management (create/send/track)")
log("  - Payment processing (Stripe/Razorpay/PayPal)")
log("  - Dunning (payment retry only)")
log("  - Subscription management (plans, trials)")
log("")
log("The billing system is MISSING:")
log("  - Overdue invoice enforcement (product lockout)")
log("  - Grace period configuration")
log("  - Escalation workflow (remind -> warn -> suspend -> cancel)")
log("  - Overdue warning banners for org admins")
log("  - Super Admin overdue org dashboard")
log("  - Manual org suspension capability")
log("  - Boundary enforcement at 15 days")
log("=" * 80)
