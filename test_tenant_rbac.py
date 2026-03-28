import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import time
import os
import urllib.request
import urllib.error
import ssl
import base64
import traceback
from datetime import datetime

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
API_BASE = f"{BASE_URL}/api/v1"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

CREDS = {
    "ananya": {"email": "ananya@technova.in", "password": "Welcome@123", "role": "org_admin", "org": "TechNova"},
    "priya":  {"email": "priya@technova.in",  "password": "Welcome@123", "role": "employee",  "org": "TechNova"},
    "john":   {"email": "john@globaltech.com", "password": "Welcome@123", "role": "org_admin", "org": "GlobalTech"},
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Disable SSL verification for test environment
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ── Results tracking ────────────────────────────────────────────────────────
bugs_found = []
test_results = []

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def record_test(name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    log(f"  [{status}] {name}" + (f" - {details}" if details else ""))

def record_bug(title, severity, description, steps, expected, actual):
    bugs_found.append({
        "title": title,
        "severity": severity,
        "description": description,
        "steps": steps,
        "expected": expected,
        "actual": actual,
    })
    log(f"  [BUG-{severity.upper()}] {title}")

# ── API helpers ─────────────────────────────────────────────────────────────
def api_request(method, path, token=None, data=None, expect_fail=False, retries=3):
    """Make API request with retry on 429. Returns (status_code, response_body_dict_or_str)."""
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data else None

    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
            if e.code == 429 and attempt < retries - 1:
                wait = 15 * (attempt + 1)
                log(f"  Rate limited (429) on {method} {path}, waiting {wait}s...")
                time.sleep(wait)
                continue
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, raw
        except Exception as e:
            return 0, str(e)
    return 429, "Rate limited after retries"


def login_api(email, password):
    """Login and return (token, user_info_dict)."""
    # Try common login endpoints (only use the known working one)
    for endpoint in ["/auth/login"]:
        status, body = api_request("POST", endpoint, data={"email": email, "password": password})
        if status == 200 and isinstance(body, dict):
            # Search for token in nested structures
            token = body.get("token") or body.get("access_token") or body.get("accessToken")
            if not token and "data" in body:
                d = body["data"]
                token = d.get("token") or d.get("access_token") or d.get("accessToken")
                # Check data.tokens.access_token
                if not token and isinstance(d.get("tokens"), dict):
                    token = d["tokens"].get("access_token") or d["tokens"].get("token") or d["tokens"].get("accessToken")
            if token:
                log(f"  Logged in {email} via {endpoint} (status={status})")
                return token, body
            log(f"  {endpoint} returned 200 but no token found. Keys: {list(body.keys()) if isinstance(body, dict) else 'N/A'}")
        else:
            log(f"  {endpoint} -> status={status}")
    return None, None


def decode_jwt_payload(token):
    """Decode JWT payload without verification."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        # Add padding
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        log(f"  JWT decode error: {e}")
        return {}


def tamper_jwt(token, overrides):
    """Tamper with JWT payload fields. Returns modified token (invalid signature)."""
    try:
        parts = token.split(".")
        payload = parts[1]
        payload += "=" * (4 - len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload))
        decoded.update(overrides)
        new_payload = base64.urlsafe_b64encode(json.dumps(decoded).encode()).rstrip(b"=").decode()
        return f"{parts[0]}.{new_payload}.{parts[2]}"
    except Exception as e:
        log(f"  JWT tamper error: {e}")
        return token


# ── GitHub issue creation ───────────────────────────────────────────────────
def create_github_issue(title, body, labels=None):
    """Create a GitHub issue."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "EmpCloud-E2E-Tester",
    }
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        result = json.loads(resp.read().decode())
        log(f"  Created GitHub issue #{result.get('number')}: {result.get('html_url')}")
        return result
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        log(f"  GitHub issue creation failed: {e.code} - {raw}")
        return None
    except Exception as e:
        log(f"  GitHub issue creation error: {e}")
        return None


def file_bug_on_github(bug):
    """File a single bug as a GitHub issue."""
    severity = bug["severity"]
    label_map = {"critical": "severity:critical", "high": "severity:high", "medium": "severity:medium", "low": "severity:low"}
    labels = ["bug", label_map.get(severity, "severity:medium")]

    body = f"""## Bug Report (Automated E2E Test)

**Severity:** {severity.upper()}

### Description
{bug['description']}

### Steps to Reproduce
{bug['steps']}

### Expected Behavior
{bug['expected']}

### Actual Behavior
{bug['actual']}

---
*Reported by automated tenant isolation / RBAC / API security test suite.*
*Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    return create_github_issue(f"[{severity.upper()}] {bug['title']}", body, labels)


# ── Selenium helper ─────────────────────────────────────────────────────────
def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    return driver


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot saved: {path}")
    return path


def selenium_login(driver, email, password):
    """Login via the UI."""
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    screenshot(driver, f"login_page_{email.split('@')[0]}")

    # Try to find email/password fields
    for selector in [
        ("input[name='email']", "input[name='password']"),
        ("input[type='email']", "input[type='password']"),
        ("#email", "#password"),
        ("input[placeholder*='mail']", "input[placeholder*='assword']"),
    ]:
        try:
            email_el = driver.find_element(By.CSS_SELECTOR, selector[0])
            pass_el = driver.find_element(By.CSS_SELECTOR, selector[1])
            email_el.clear()
            email_el.send_keys(email)
            pass_el.clear()
            pass_el.send_keys(password)
            break
        except NoSuchElementException:
            continue
    else:
        # Fallback: find all input fields
        inputs = driver.find_elements(By.TAG_NAME, "input")
        log(f"  Found {len(inputs)} input fields, trying first two")
        if len(inputs) >= 2:
            inputs[0].clear()
            inputs[0].send_keys(email)
            inputs[1].clear()
            inputs[1].send_keys(password)

    time.sleep(1)

    # Click login button
    for btn_sel in [
        "button[type='submit']",
        "button:not([type='button'])",
        "input[type='submit']",
        "button",
    ]:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, btn_sel)
            for btn in btns:
                txt = btn.text.lower()
                if any(w in txt for w in ["login", "sign in", "log in", "submit", ""]):
                    btn.click()
                    break
            break
        except Exception:
            continue

    time.sleep(4)
    screenshot(driver, f"after_login_{email.split('@')[0]}")
    return driver


# ═══════════════════════════════════════════════════════════════════════════
#  TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════

def test_tenant_isolation():
    """Test cross-org data leakage."""
    log("\n" + "=" * 70)
    log("TENANT ISOLATION TESTS")
    log("=" * 70)

    # Step 1: Login as Ananya (TechNova org admin)
    log("\n[1] Logging in as Ananya (TechNova)...")
    ananya_token, ananya_resp = login_api(CREDS["ananya"]["email"], CREDS["ananya"]["password"])
    if not ananya_token:
        record_test("Login Ananya", False, "Could not login")
        return
    record_test("Login Ananya", True)

    ananya_jwt = decode_jwt_payload(ananya_token)
    ananya_org_id = ananya_jwt.get("org_id") or ananya_jwt.get("orgId") or ananya_jwt.get("organization_id") or ananya_jwt.get("tenant_id")
    log(f"  Ananya JWT payload keys: {list(ananya_jwt.keys())}")
    log(f"  Ananya org_id: {ananya_org_id}")

    # Get TechNova user list for comparison
    log("\n[1b] Getting TechNova user list...")
    status, technova_users = api_request("GET", "/users", token=ananya_token)
    log(f"  TechNova /users -> status={status}")
    technova_emails = []
    if isinstance(technova_users, dict):
        user_list = technova_users.get("data") or technova_users.get("users") or technova_users.get("results") or []
        if isinstance(user_list, list):
            technova_emails = [u.get("email", "") for u in user_list if isinstance(u, dict)]
            log(f"  TechNova emails: {technova_emails}")
    elif isinstance(technova_users, list):
        technova_emails = [u.get("email", "") for u in technova_users if isinstance(u, dict)]
        log(f"  TechNova emails: {technova_emails}")

    # Get TechNova announcements for comparison
    time.sleep(2)
    status_a, technova_ann = api_request("GET", "/announcements", token=ananya_token)
    log(f"  TechNova /announcements -> status={status_a}")

    # Step 2: Login as John (GlobalTech org admin)
    log("\n  Waiting 10s before next login to avoid rate limiting...")
    time.sleep(10)
    log("\n[2] Logging in as John (GlobalTech)...")
    john_token, john_resp = login_api(CREDS["john"]["email"], CREDS["john"]["password"])
    if not john_token:
        record_test("Login John", False, "Could not login")
        return
    record_test("Login John", True)

    john_jwt = decode_jwt_payload(john_token)
    john_org_id = john_jwt.get("org_id") or john_jwt.get("orgId") or john_jwt.get("organization_id") or john_jwt.get("tenant_id")
    log(f"  John JWT payload keys: {list(john_jwt.keys())}")
    log(f"  John org_id: {john_org_id}")

    # Step 3: Cross-org access tests using John's token
    log("\n[3] Testing cross-org data access with John's token...")

    # Test /users
    status, john_users = api_request("GET", "/users", token=john_token)
    log(f"  John /users -> status={status}")
    leaked_users = False
    if status == 200:
        user_list = []
        if isinstance(john_users, dict):
            user_list = john_users.get("data") or john_users.get("users") or john_users.get("results") or []
        elif isinstance(john_users, list):
            user_list = john_users

        if isinstance(user_list, list):
            john_emails = [u.get("email", "") for u in user_list if isinstance(u, dict)]
            log(f"  GlobalTech user emails: {john_emails}")
            technova_in_john = [e for e in john_emails if "technova" in e.lower()]
            if technova_in_john:
                leaked_users = True
                record_test("Tenant Isolation - Users", False,
                            f"TechNova emails found in GlobalTech response: {technova_in_john}")
                record_bug(
                    "Cross-Tenant Data Leak: TechNova users visible to GlobalTech admin",
                    "critical",
                    "When logged in as GlobalTech org admin, the /users endpoint returns TechNova user data, violating tenant isolation.",
                    "1. Login as john@globaltech.com\n2. GET /api/v1/users\n3. Observe TechNova emails in response",
                    "Only GlobalTech users should be returned",
                    f"TechNova emails found: {technova_in_john}"
                )
            else:
                record_test("Tenant Isolation - Users", True, "No cross-org user leak")
        else:
            record_test("Tenant Isolation - Users", True, f"Response not a user list, status={status}")
    else:
        record_test("Tenant Isolation - Users", True, f"Endpoint returned {status} (not 200)")

    # Test /announcements
    time.sleep(2)
    status, john_ann = api_request("GET", "/announcements", token=john_token)
    log(f"  John /announcements -> status={status}")
    if status == 200 and isinstance(john_ann, (dict, list)):
        ann_list = john_ann if isinstance(john_ann, list) else (john_ann.get("data") or john_ann.get("announcements") or [])
        if isinstance(ann_list, list):
            # Check for TechNova org references
            ann_str = json.dumps(ann_list).lower()
            if "technova" in ann_str:
                record_test("Tenant Isolation - Announcements", False, "TechNova data found in GlobalTech announcements")
                record_bug(
                    "Cross-Tenant Data Leak: TechNova announcements visible to GlobalTech",
                    "critical",
                    "GlobalTech admin can see TechNova announcements.",
                    "1. Login as john@globaltech.com\n2. GET /api/v1/announcements\n3. Observe TechNova data in response",
                    "Only GlobalTech announcements",
                    f"TechNova data found in response"
                )
            else:
                record_test("Tenant Isolation - Announcements", True, f"No cross-org leak ({len(ann_list)} announcements)")
        else:
            record_test("Tenant Isolation - Announcements", True, "No list data")
    else:
        record_test("Tenant Isolation - Announcements", True, f"Status={status}")

    # Test /documents
    time.sleep(2)
    status, john_docs = api_request("GET", "/documents", token=john_token)
    log(f"  John /documents -> status={status}")
    if status == 200 and isinstance(john_docs, (dict, list)):
        doc_list = john_docs if isinstance(john_docs, list) else (john_docs.get("data") or john_docs.get("documents") or [])
        if isinstance(doc_list, list):
            doc_str = json.dumps(doc_list).lower()
            if "technova" in doc_str:
                record_test("Tenant Isolation - Documents", False, "TechNova data found in GlobalTech documents")
                record_bug(
                    "Cross-Tenant Data Leak: TechNova documents visible to GlobalTech",
                    "high",
                    "GlobalTech admin can see TechNova documents.",
                    "1. Login as john@globaltech.com\n2. GET /api/v1/documents",
                    "Only GlobalTech documents",
                    "TechNova data found in response"
                )
            else:
                record_test("Tenant Isolation - Documents", True, f"No cross-org leak ({len(doc_list)} docs)")
        else:
            record_test("Tenant Isolation - Documents", True, "No list data")
    else:
        record_test("Tenant Isolation - Documents", True, f"Status={status}")

    # Test /events
    time.sleep(2)
    status, john_events = api_request("GET", "/events", token=john_token)
    log(f"  John /events -> status={status}")
    if status == 200 and isinstance(john_events, (dict, list)):
        evt_list = john_events if isinstance(john_events, list) else (john_events.get("data") or john_events.get("events") or [])
        if isinstance(evt_list, list):
            evt_str = json.dumps(evt_list).lower()
            if "technova" in evt_str:
                record_test("Tenant Isolation - Events", False, "TechNova data found in GlobalTech events")
                record_bug(
                    "Cross-Tenant Data Leak: TechNova events visible to GlobalTech",
                    "high",
                    "GlobalTech admin can see TechNova events.",
                    "1. Login as john@globaltech.com\n2. GET /api/v1/events",
                    "Only GlobalTech events",
                    "TechNova data found in response"
                )
            else:
                record_test("Tenant Isolation - Events", True, f"No cross-org leak ({len(evt_list)} events)")
        else:
            record_test("Tenant Isolation - Events", True, "No list data")
    else:
        record_test("Tenant Isolation - Events", True, f"Status={status}")

    # Step 4: Try accessing TechNova data directly with John's token using org_id
    if ananya_org_id and john_org_id and ananya_org_id != john_org_id:
        log(f"\n[4] Trying direct org_id access: John's token with TechNova org_id ({ananya_org_id})...")
        for path in [f"/users?org_id={ananya_org_id}", f"/users?orgId={ananya_org_id}",
                      f"/organizations/{ananya_org_id}/users", f"/org/{ananya_org_id}/users"]:
            status, resp = api_request("GET", path, token=john_token)
            if status == 200:
                resp_str = json.dumps(resp).lower() if isinstance(resp, (dict, list)) else str(resp).lower()
                if "technova" in resp_str or (technova_emails and any(e.lower() in resp_str for e in technova_emails)):
                    record_test(f"Tenant Isolation - Direct org access {path}", False,
                                "Cross-org data accessible via direct org_id parameter")
                    record_bug(
                        f"Cross-Tenant Access via org_id Parameter: {path}",
                        "critical",
                        f"Using {path} with another tenant's org_id returns their data.",
                        f"1. Login as john@globaltech.com\n2. GET /api/v1{path}\n3. Observe TechNova data",
                        "403 Forbidden or empty result",
                        f"Status {status}, TechNova data returned"
                    )
                else:
                    record_test(f"Tenant Isolation - Direct org access {path}", True, f"Status {status} but no cross-org data")
            else:
                record_test(f"Tenant Isolation - Direct org access {path}", True, f"Denied with status {status}")

    return ananya_token, john_token, ananya_org_id, john_org_id


def test_rbac():
    """Test Role-Based Access Control."""
    log("\n" + "=" * 70)
    log("RBAC TESTS")
    log("=" * 70)

    # Login as employee Priya
    log("\n[1] Logging in as Priya (TechNova employee)...")
    priya_token, priya_resp = login_api(CREDS["priya"]["email"], CREDS["priya"]["password"])
    if not priya_token:
        record_test("Login Priya", False, "Could not login")
        return None
    record_test("Login Priya", True)

    priya_jwt = decode_jwt_payload(priya_token)
    log(f"  Priya JWT keys: {list(priya_jwt.keys())}")
    priya_user_id = priya_jwt.get("id") or priya_jwt.get("user_id") or priya_jwt.get("userId") or priya_jwt.get("sub")
    log(f"  Priya user_id: {priya_user_id}")

    # Also login as admin for comparison (with delay to avoid rate limit)
    time.sleep(5)
    ananya_token, _ = login_api(CREDS["ananya"]["email"], CREDS["ananya"]["password"])

    # Test 1: GET /users as employee
    log("\n[2] Testing admin-only operations with employee token...")

    status, resp = api_request("GET", "/users", token=priya_token)
    log(f"  Employee GET /users -> status={status}")
    if status == 200:
        user_list = []
        if isinstance(resp, dict):
            user_list = resp.get("data") or resp.get("users") or resp.get("results") or []
        elif isinstance(resp, list):
            user_list = resp
        if isinstance(user_list, list) and len(user_list) > 1:
            emails = [u.get("email", "") for u in user_list if isinstance(u, dict)]
            log(f"  Employee can see users: {emails}")
            # If employee can see ALL users, that's a bug
            record_test("RBAC - Employee GET /users", False,
                         f"Employee can list all users ({len(user_list)} users visible)")
            record_bug(
                "RBAC Violation: Employee can list all organization users",
                "high",
                "An employee-role user can access GET /api/v1/users and see all org users.",
                "1. Login as priya@technova.in (employee role)\n2. GET /api/v1/users",
                "403 Forbidden or only own profile returned",
                f"Status 200, {len(user_list)} users returned: {emails}"
            )
        else:
            record_test("RBAC - Employee GET /users", True, "Limited or no user data returned")
    elif status in (401, 403):
        record_test("RBAC - Employee GET /users", True, f"Properly denied ({status})")
    else:
        record_test("RBAC - Employee GET /users", True, f"Status {status}")

    # Test 2: POST /announcements as employee
    time.sleep(2)
    status, resp = api_request("POST", "/announcements", token=priya_token,
                               data={"title": "RBAC Test", "content": "This should be denied", "type": "general"})
    log(f"  Employee POST /announcements -> status={status}")
    if status in (200, 201):
        record_test("RBAC - Employee POST /announcements", False,
                     "Employee can create announcements (admin-only)")
        record_bug(
            "RBAC Violation: Employee can create announcements",
            "high",
            "Employee-role user can POST to /api/v1/announcements (admin-only operation).",
            "1. Login as priya@technova.in\n2. POST /api/v1/announcements with announcement data",
            "403 Forbidden",
            f"Status {status}, announcement created"
        )
    else:
        record_test("RBAC - Employee POST /announcements", True, f"Denied ({status})")

    # Test 3: GET /audit as employee
    time.sleep(2)
    for audit_path in ["/audit", "/audit-logs", "/audit/logs"]:
        status, resp = api_request("GET", audit_path, token=priya_token)
        log(f"  Employee GET {audit_path} -> status={status}")
        if status == 200:
            record_test(f"RBAC - Employee GET {audit_path}", False,
                         "Employee can access audit logs (admin-only)")
            record_bug(
                f"RBAC Violation: Employee can access audit logs ({audit_path})",
                "high",
                f"Employee-role user can access GET /api/v1{audit_path}.",
                f"1. Login as priya@technova.in\n2. GET /api/v1{audit_path}",
                "403 Forbidden",
                f"Status 200, audit data returned"
            )
        else:
            record_test(f"RBAC - Employee GET {audit_path}", True, f"Denied ({status})")

    # Test 4: Privilege escalation - PUT self to org_admin
    time.sleep(2)
    if priya_user_id:
        for path in [f"/users/{priya_user_id}", f"/user/{priya_user_id}", f"/users/profile/{priya_user_id}"]:
            status, resp = api_request("PUT", path, token=priya_token,
                                       data={"role": "org_admin"})
            log(f"  Employee PUT {path} role->org_admin -> status={status}")
            if status == 200:
                # Check if role actually changed
                resp_role = None
                if isinstance(resp, dict):
                    resp_role = resp.get("role") or (resp.get("data", {}) or {}).get("role")
                if resp_role == "org_admin":
                    record_test(f"RBAC - Privilege Escalation via {path}", False,
                                 "Employee escalated own role to org_admin!")
                    record_bug(
                        "CRITICAL: Privilege Escalation - Employee can self-promote to org_admin",
                        "critical",
                        f"Employee can PUT /api/v1{path} with role=org_admin to escalate privileges.",
                        f"1. Login as priya@technova.in\n2. PUT /api/v1{path} with {{\"role\": \"org_admin\"}}",
                        "403 Forbidden",
                        f"Status 200, role changed to org_admin"
                    )
                else:
                    record_test(f"RBAC - Privilege Escalation via {path}", True,
                                 f"Status 200 but role not changed (role={resp_role})")
            else:
                record_test(f"RBAC - Privilege Escalation via {path}", True, f"Denied ({status})")

    # Test 5: DELETE /users as employee
    # Use a fake ID to avoid actually deleting
    for fake_id in ["000000000000000000000000", "nonexistent-id", "99999"]:
        status, resp = api_request("DELETE", f"/users/{fake_id}", token=priya_token)
        log(f"  Employee DELETE /users/{fake_id} -> status={status}")
        # 403/401 = properly denied, 404 = might mean auth passed but user not found (still a bug)
        if status == 404:
            record_test(f"RBAC - Employee DELETE /users/{fake_id}", False,
                         "Got 404 (not 403) - auth check may be missing, endpoint processed request")
            record_bug(
                "RBAC Weakness: DELETE /users returns 404 instead of 403 for employee",
                "medium",
                "Employee gets 404 (Not Found) instead of 403 (Forbidden) when trying to delete a user. This suggests the authorization check happens after the lookup, or is missing entirely.",
                f"1. Login as priya@technova.in\n2. DELETE /api/v1/users/{fake_id}",
                "403 Forbidden",
                f"Status 404 - request was processed without auth check"
            )
            break
        elif status in (200, 204):
            record_test(f"RBAC - Employee DELETE /users/{fake_id}", False,
                         "Employee can delete users!")
            record_bug(
                "CRITICAL: Employee can delete users",
                "critical",
                "Employee-role user can DELETE /api/v1/users/{id}.",
                f"1. Login as priya@technova.in\n2. DELETE /api/v1/users/{fake_id}",
                "403 Forbidden",
                f"Status {status}"
            )
            break
        elif status in (401, 403):
            record_test(f"RBAC - Employee DELETE /users/{fake_id}", True, f"Properly denied ({status})")
            break
        else:
            record_test(f"RBAC - Employee DELETE /users/{fake_id}", True, f"Status {status}")

    return priya_token


def test_api_security(ananya_token=None, john_token=None, ananya_org_id=None, john_org_id=None):
    """Test API security: invalid tokens, tampered JWT, etc."""
    log("\n" + "=" * 70)
    log("API SECURITY TESTS")
    log("=" * 70)

    # Test 1: Expired/invalid token
    log("\n[1] Testing with invalid/expired tokens...")
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEyMyIsIm9yZ0lkIjoiZmFrZSIsImV4cCI6MTAwMDAwMDAwMH0.fake_signature_here"
    status, resp = api_request("GET", "/users", token=fake_token)
    log(f"  Invalid token GET /users -> status={status}")
    if status == 200:
        record_test("API Security - Invalid Token", False, "API accepted completely invalid JWT")
        record_bug(
            "API accepts invalid/forged JWT tokens",
            "critical",
            "The API accepted a request with a completely invalid JWT token and returned data.",
            "1. Send GET /api/v1/users with a forged JWT\n2. Observe response",
            "401 Unauthorized",
            f"Status {status}, data returned"
        )
    elif status in (401, 403):
        record_test("API Security - Invalid Token", True, f"Rejected ({status})")
    else:
        record_test("API Security - Invalid Token", True, f"Status {status}")

    # Empty bearer
    status, resp = api_request("GET", "/users", token="")
    log(f"  Empty token GET /users -> status={status}")
    if status == 200:
        record_test("API Security - Empty Token", False, "API accepted empty bearer token")
        record_bug("API accepts empty bearer token", "critical",
                    "GET /users returns data with empty bearer token.",
                    "1. GET /api/v1/users with Authorization: Bearer (empty)",
                    "401", f"Status {status}")
    else:
        record_test("API Security - Empty Token", True, f"Status {status}")

    # No auth header at all
    status, resp = api_request("GET", "/users")
    log(f"  No token GET /users -> status={status}")
    if status == 200:
        record_test("API Security - No Auth", False, "API returned data without any auth")
        record_bug("API exposes data without authentication", "critical",
                    "GET /users returns data with no Authorization header.",
                    "1. GET /api/v1/users without auth header",
                    "401", f"Status {status}")
    else:
        record_test("API Security - No Auth", True, f"Status {status}")

    # Test 2: Tampered JWT (modify org_id)
    log("\n[2] Testing with tampered JWT (modified org_id)...")
    if john_token and ananya_org_id:
        tampered = tamper_jwt(john_token, {
            "org_id": ananya_org_id,
            "orgId": ananya_org_id,
            "organization_id": ananya_org_id,
            "tenant_id": ananya_org_id,
        })
        status, resp = api_request("GET", "/users", token=tampered)
        log(f"  Tampered JWT (John->TechNova org) GET /users -> status={status}")
        if status == 200:
            resp_str = json.dumps(resp).lower() if isinstance(resp, (dict, list)) else str(resp).lower()
            if "technova" in resp_str:
                record_test("API Security - Tampered JWT org_id", False,
                             "Tampered JWT with different org_id returns cross-org data!")
                record_bug(
                    "CRITICAL: JWT org_id tampering allows cross-tenant access",
                    "critical",
                    "Modifying the org_id in a JWT payload (without re-signing) returns data from another tenant.",
                    "1. Login as john@globaltech.com, get JWT\n2. Modify org_id in JWT payload to TechNova's org_id\n3. GET /users",
                    "401 Unauthorized (invalid signature)",
                    f"Status 200, TechNova data returned"
                )
            else:
                record_test("API Security - Tampered JWT org_id", False,
                             f"API accepted tampered JWT (status 200) but no cross-org data visible")
                record_bug(
                    "API accepts JWT with tampered payload (invalid signature)",
                    "high",
                    "API does not verify JWT signature - accepts tokens with modified payload.",
                    "1. Take valid JWT, modify org_id in payload\n2. GET /users",
                    "401 Unauthorized (invalid signature)",
                    f"Status 200 accepted"
                )
        elif status in (401, 403):
            record_test("API Security - Tampered JWT org_id", True, f"Properly rejected ({status})")
        else:
            record_test("API Security - Tampered JWT org_id", True, f"Status {status}")

    # Test 3: Tamper JWT role
    log("\n[3] Testing JWT role tampering...")
    priya_token, _ = login_api(CREDS["priya"]["email"], CREDS["priya"]["password"])
    if priya_token:
        tampered_role = tamper_jwt(priya_token, {"role": "org_admin", "is_admin": True, "admin": True})
        status, resp = api_request("GET", "/users", token=tampered_role)
        log(f"  Tampered JWT (priya role->org_admin) GET /users -> status={status}")
        if status == 200:
            user_list = []
            if isinstance(resp, dict):
                user_list = resp.get("data") or resp.get("users") or resp.get("results") or []
            elif isinstance(resp, list):
                user_list = resp
            if isinstance(user_list, list) and len(user_list) > 1:
                record_test("API Security - JWT Role Tampering", False,
                             "Tampered JWT role escalation accepted!")
                record_bug(
                    "JWT role tampering allows privilege escalation",
                    "critical",
                    "Modifying the role field in JWT from employee to org_admin grants admin access without signature verification.",
                    "1. Login as priya@technova.in (employee)\n2. Modify role in JWT to org_admin\n3. GET /users returns all users",
                    "401 Unauthorized",
                    f"Status 200, {len(user_list)} users returned"
                )
            else:
                record_test("API Security - JWT Role Tampering", True,
                             f"Status 200 but limited data (may trust DB role, not JWT)")
        elif status in (401, 403):
            record_test("API Security - JWT Role Tampering", True, f"Rejected ({status})")
        else:
            record_test("API Security - JWT Role Tampering", True, f"Status {status}")


def test_rbac_ui():
    """Test RBAC via Selenium UI."""
    log("\n" + "=" * 70)
    log("RBAC UI TESTS (Selenium)")
    log("=" * 70)

    driver = None
    try:
        driver = get_driver()

        # Login as Priya (employee)
        log("\n[1] Logging in as Priya via UI...")
        selenium_login(driver, CREDS["priya"]["email"], CREDS["priya"]["password"])

        current_url = driver.current_url
        log(f"  Current URL after login: {current_url}")
        screenshot(driver, "priya_dashboard")

        # Check page title/content
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text[:500]
            log(f"  Page text (first 500 chars): {page_text[:200]}...")
        except Exception:
            pass

        # Test: Navigate to /settings
        log("\n[2] Navigating to /settings as employee...")
        driver.get(f"{BASE_URL}/settings")
        time.sleep(3)
        screenshot(driver, "priya_settings_page")
        settings_url = driver.current_url
        log(f"  URL after /settings: {settings_url}")
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
            if any(w in body_text.lower() for w in ["denied", "forbidden", "unauthorized", "not allowed", "access denied"]):
                record_test("RBAC UI - Employee /settings", True, "Access properly denied")
            elif "settings" in settings_url.lower() and "login" not in settings_url.lower():
                record_test("RBAC UI - Employee /settings", False,
                             f"Employee can access settings page at {settings_url}")
                record_bug(
                    "RBAC UI: Employee can access /settings page",
                    "medium",
                    "Employee-role user can navigate to /settings in the UI.",
                    "1. Login as priya@technova.in\n2. Navigate to /settings",
                    "Redirect to dashboard or access denied",
                    f"Settings page loaded at {settings_url}"
                )
            else:
                record_test("RBAC UI - Employee /settings", True,
                             f"Redirected away from settings to {settings_url}")
        except Exception as e:
            record_test("RBAC UI - Employee /settings", True, f"Could not read page: {e}")

        # Test: Navigate to /admin/super
        log("\n[3] Navigating to /admin/super as employee...")
        driver.get(f"{BASE_URL}/admin/super")
        time.sleep(3)
        screenshot(driver, "priya_admin_super_page")
        admin_url = driver.current_url
        log(f"  URL after /admin/super: {admin_url}")
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
            if any(w in body_text.lower() for w in ["denied", "forbidden", "unauthorized", "not allowed", "not found"]):
                record_test("RBAC UI - Employee /admin/super", True, "Access properly denied")
            elif "admin" in admin_url.lower() and "login" not in admin_url.lower():
                record_test("RBAC UI - Employee /admin/super", False,
                             f"Employee can access admin/super at {admin_url}")
                record_bug(
                    "RBAC UI: Employee can access /admin/super page",
                    "high",
                    "Employee-role user can navigate to /admin/super in the UI.",
                    "1. Login as priya@technova.in\n2. Navigate to /admin/super",
                    "Redirect or access denied",
                    f"Admin page loaded at {admin_url}"
                )
            else:
                record_test("RBAC UI - Employee /admin/super", True,
                             f"Redirected to {admin_url}")
        except Exception as e:
            record_test("RBAC UI - Employee /admin/super", True, f"Could not read page: {e}")

        # Test additional admin-like paths
        for admin_path in ["/admin", "/admin/users", "/organization/settings"]:
            log(f"\n[4] Navigating to {admin_path} as employee...")
            driver.get(f"{BASE_URL}{admin_path}")
            time.sleep(3)
            screenshot(driver, f"priya_{admin_path.replace('/', '_')}")
            nav_url = driver.current_url
            log(f"  URL after {admin_path}: {nav_url}")

    except Exception as e:
        log(f"  Selenium error: {e}")
        traceback.print_exc()
        if driver:
            screenshot(driver, "selenium_error")
    finally:
        if driver:
            driver.quit()


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    log("=" * 70)
    log("EMP Cloud HRMS - Tenant Isolation, RBAC & API Security Test Suite")
    log("=" * 70)

    # Run tenant isolation tests
    result = test_tenant_isolation()
    ananya_token, john_token, ananya_org_id, john_org_id = result if result else (None, None, None, None)

    # Run RBAC API tests
    log("\nWaiting 10s before RBAC tests...")
    time.sleep(10)
    priya_token = test_rbac()

    # Run API security tests
    log("\nWaiting 10s before API security tests...")
    time.sleep(10)
    test_api_security(ananya_token, john_token, ananya_org_id, john_org_id)

    # Run Selenium UI tests
    log("\nWaiting 15s before Selenium UI tests...")
    time.sleep(15)
    test_rbac_ui()

    # ── Summary ─────────────────────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)
    passed = sum(1 for t in test_results if t["passed"])
    failed = sum(1 for t in test_results if not t["passed"])
    log(f"Total: {len(test_results)} | Passed: {passed} | Failed: {failed}")
    log(f"Bugs found: {len(bugs_found)}")

    if failed:
        log("\nFailed tests:")
        for t in test_results:
            if not t["passed"]:
                log(f"  FAIL: {t['name']} - {t['details']}")

    if bugs_found:
        log(f"\nBugs found ({len(bugs_found)}):")
        for b in bugs_found:
            log(f"  [{b['severity'].upper()}] {b['title']}")

    # File bugs on GitHub
    if bugs_found:
        log("\n" + "=" * 70)
        log("FILING GITHUB ISSUES")
        log("=" * 70)
        for bug in bugs_found:
            file_bug_on_github(bug)

    log("\nDone.")


if __name__ == "__main__":
    main()
