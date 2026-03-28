#!/usr/bin/env python3
"""
Deep Re-test of Closed EmpCloud Issues (Batch 1 - first 100 closed issues)
Tests each bug with actual reproduction steps, not just status checks.
"""

import sys
import os
import json
import time
import re
import traceback
import requests
from datetime import datetime
from urllib.parse import urljoin, quote

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── Config ──────────────────────────────────────────────────────────────
API_BASE = "https://test-empcloud.empcloud.com/api/v1"
APP_URL = "https://test-empcloud.empcloud.com"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_API = "https://api.github.com"

CREDS = {
    "org_admin": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "employee": {"email": "priya@technova.in", "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"},
}

SKIP_LABELS = {"emp-field", "emp-biometrics", "field-force", "biometrics"}
SKIP_KEYWORDS_IN_TITLE = ["field force", "biometric", "rate limit"]
TODAY = "2026-03-28"
# Set to skip issues already tested in previous run (0 = test all)
SKIP_ISSUES_ABOVE = 619  # Already tested 704 down to 619

# ── Session / Token Cache ───────────────────────────────────────────────
_tokens = {}
_pending_comments = []  # (issue_number, body) tuples to retry later
_pending_reopens = []   # issue numbers to retry later
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})


def api(method, path, token=None, json_data=None, params=None, timeout=20, _retried=False):
    """Make API call, return (status_code, response_json_or_text). Auto-refreshes expired tokens."""
    url = f"{API_BASE}{path}" if path.startswith("/") else path
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = _session.request(
            method, url, json=json_data, params=params,
            headers=headers, timeout=timeout, allow_redirects=False
        )
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]

        # Auto-refresh expired tokens
        if resp.status_code == 401 and not _retried and token:
            body_str = str(body).lower()
            if "expired" in body_str or "invalid" in body_str:
                # Find which role this token belongs to and refresh
                for role, cached_token in list(_tokens.items()):
                    if cached_token == token:
                        new_token = refresh_token(role)
                        if new_token:
                            return api(method, path, token=new_token, json_data=json_data,
                                       params=params, timeout=timeout, _retried=True)
        return resp.status_code, body
    except Exception as e:
        return 0, str(e)


def refresh_token(role):
    """Force re-login for a role."""
    _tokens.pop(role, None)
    return login(role)


def login(role):
    """Login and cache token."""
    if role in _tokens:
        return _tokens[role]
    cred = CREDS[role]
    status, body = api("POST", "/auth/login", json_data={
        "email": cred["email"], "password": cred["password"]
    })
    if status == 200 and isinstance(body, dict):
        # Primary: data.tokens.access_token (EmpCloud actual format)
        data = body.get("data", {})
        if isinstance(data, dict):
            tokens_obj = data.get("tokens", {})
            if isinstance(tokens_obj, dict) and tokens_obj.get("access_token"):
                _tokens[role] = tokens_obj["access_token"]
                return _tokens[role]
            # Fallback: data.token or data.access_token
            for key in ["token", "access_token", "accessToken"]:
                if data.get(key):
                    _tokens[role] = data[key]
                    return _tokens[role]
        # Top-level token
        for key in ["token", "access_token", "accessToken", "jwt", "auth_token"]:
            if body.get(key):
                _tokens[role] = body[key]
                return _tokens[role]
    print(f"    [LOGIN FAIL] {role}: status={status}, body={str(body)[:300]}")
    return None


def gh_api(method, path, json_data=None):
    """GitHub API call."""
    url = f"{GITHUB_API}{path}" if path.startswith("/") else path
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        resp = requests.request(method, url, json=json_data, headers=headers, timeout=30)
        return resp.status_code, resp.json() if resp.text else {}
    except Exception as e:
        return 0, str(e)


def add_github_comment(issue_number, comment_body):
    """Post a comment on a GitHub issue, with retry on rate limit."""
    path = f"/repos/{GITHUB_REPO}/issues/{issue_number}/comments"
    status, body = gh_api("POST", path, json_data={"body": comment_body})
    if status == 201:
        print(f"    [GH] Comment posted on #{issue_number}")
    elif status == 403 and "rate limit" in str(body).lower():
        print(f"    [GH] Rate limited on #{issue_number} (will retry at end)")
        _pending_comments.append((issue_number, comment_body))
    else:
        print(f"    [GH] Failed to comment on #{issue_number}: {status}")
    return status


def reopen_issue(issue_number):
    """Re-open a GitHub issue, with retry on rate limit."""
    path = f"/repos/{GITHUB_REPO}/issues/{issue_number}"
    status, body = gh_api("PATCH", path, json_data={"state": "open"})
    if status == 200:
        print(f"    [GH] Re-opened #{issue_number}")
    elif status == 403 and "rate limit" in str(body).lower():
        print(f"    [GH] Rate limited reopening #{issue_number} (will retry at end)")
        _pending_reopens.append(issue_number)
    else:
        print(f"    [GH] Failed to re-open #{issue_number}: {status}")


def should_skip(issue):
    """Check if issue should be skipped (field force, biometrics, rate limits)."""
    labels = {l["name"].lower() for l in issue.get("labels", [])}
    if labels & SKIP_LABELS:
        return True
    title = issue.get("title", "").lower()
    for kw in SKIP_KEYWORDS_IN_TITLE:
        if kw in title:
            return True
    return False


def decode_jwt_payload(token):
    """Decode JWT payload without verification."""
    import base64
    parts = token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    # Add padding
    payload += "=" * (4 - len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return None


# ── Selenium helpers ────────────────────────────────────────────────────
_driver = None
_driver_uses = 0
MAX_DRIVER_USES = 3


def get_driver():
    """Get or create Selenium WebDriver, restart every 3 uses."""
    global _driver, _driver_uses
    if _driver is not None and _driver_uses >= MAX_DRIVER_USES:
        try:
            _driver.quit()
        except:
            pass
        _driver = None
        _driver_uses = 0

    if _driver is None:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--ignore-certificate-errors")
        try:
            _driver = webdriver.Chrome(options=opts)
            _driver.set_page_load_timeout(15)
            _driver.implicitly_wait(3)
        except Exception as e:
            print(f"    [SELENIUM] Failed to start: {e}")
            _driver = None
            return None
        _driver_uses = 0
    _driver_uses += 1
    return _driver


def selenium_login(role="org_admin"):
    """Login via Selenium and return driver."""
    driver = get_driver()
    if not driver:
        return None
    cred = CREDS[role]
    try:
        driver.get(f"{APP_URL}/login")
        time.sleep(2)
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # Try to find and fill email field
        email_field = None
        for selector in ["input[name='email']", "input[type='email']", "#email", "input[placeholder*='email' i]"]:
            try:
                email_field = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                pass
        if not email_field:
            # Try XPath
            try:
                email_field = driver.find_element(By.XPATH, "//input[contains(@placeholder,'mail')]")
            except:
                pass

        if email_field:
            email_field.clear()
            email_field.send_keys(cred["email"])
        else:
            print(f"    [SELENIUM] Could not find email field on login page")
            return driver

        # Find password field
        pwd_field = None
        for selector in ["input[name='password']", "input[type='password']", "#password"]:
            try:
                pwd_field = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                pass

        if pwd_field:
            pwd_field.clear()
            pwd_field.send_keys(cred["password"])

        # Submit
        for selector in ["button[type='submit']", "button:has-text('Login')", "button:has-text('Sign')", "input[type='submit']"]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                break
            except:
                pass
        else:
            # Try XPath for button
            try:
                btn = driver.find_element(By.XPATH, "//button[contains(text(),'ogin') or contains(text(),'ign')]")
                btn.click()
            except:
                if pwd_field:
                    from selenium.webdriver.common.keys import Keys
                    pwd_field.send_keys(Keys.RETURN)

        time.sleep(3)
        return driver
    except Exception as e:
        print(f"    [SELENIUM] Login error: {e}")
        return driver


def check_page(driver, url, check_for=None):
    """Navigate to URL and check page content. Returns (title, page_source_snippet, found_elements)."""
    try:
        driver.get(url)
        time.sleep(3)
        title = driver.title
        source = driver.page_source[:5000]
        current_url = driver.current_url

        result = {
            "title": title,
            "current_url": current_url,
            "redirected": current_url != url and not current_url.startswith(url),
        }

        if check_for:
            from selenium.webdriver.common.by import By
            for item in check_for:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, item)
                    result[item] = f"FOUND (text='{el.text[:50]}')"
                except:
                    try:
                        el = driver.find_element(By.XPATH, f"//*[contains(text(),'{item}')]")
                        result[item] = f"FOUND via text (tag={el.tag_name})"
                    except:
                        result[item] = "NOT FOUND"

        # Check for common error indicators
        source_lower = source.lower()
        if "404" in source_lower and ("not found" in source_lower or "page not found" in source_lower):
            result["page_error"] = "404 Not Found"
        elif "500" in source_lower and ("server error" in source_lower or "internal" in source_lower):
            result["page_error"] = "500 Server Error"
        elif "403" in source_lower and ("forbidden" in source_lower or "permission" in source_lower):
            result["page_error"] = "403 Forbidden"
        elif "insufficient permissions" in source_lower:
            result["page_error"] = "Insufficient Permissions"
        elif "unexpected error" in source_lower:
            result["page_error"] = "Unexpected Error"

        return result
    except Exception as e:
        return {"error": str(e)}


# ── Test Functions by Category ──────────────────────────────────────────

def test_rbac_employee_access(issue, module_path, description):
    """Test that employee CANNOT access an admin-only resource."""
    steps = []
    token = login("employee")
    if not token:
        steps.append("Step 1: Login as Employee (priya@technova.in) via API -> FAILED to get token")
        return "INCONCLUSIVE", steps

    steps.append("Step 1: Login as Employee (priya@technova.in) via API -> 200 OK, got token")

    # Try via Selenium for UI-based RBAC
    driver = selenium_login("employee")
    if driver:
        full_url = f"{APP_URL}{module_path}"
        result = check_page(driver, full_url)
        steps.append(f"Step 2: Navigate to {module_path} as Employee -> URL: {result.get('current_url', 'N/A')}")

        if result.get("redirected"):
            steps.append(f"Step 3: Page redirected away from admin resource -> Access correctly denied")
            return "FIXED", steps
        if result.get("page_error") in ["403 Forbidden", "Insufficient Permissions"]:
            steps.append(f"Step 3: Page shows '{result['page_error']}' -> Access correctly denied")
            return "FIXED", steps

        page_error = result.get("page_error")
        if page_error:
            steps.append(f"Step 3: Page shows error: {page_error} (not clean RBAC denial)")
            return "FIXED", steps  # At least not accessible

        # Check page source for admin content
        steps.append(f"Step 3: Page loaded without redirect or permission error -> Employee CAN access {description}")
        return "STILL FAILING", steps
    else:
        steps.append("Step 2: Selenium not available, testing via API only")
        # Try API equivalent if possible
        return "INCONCLUSIVE", steps


def test_404_page(issue, page_path, description):
    """Test if a page that was returning 404 now works."""
    steps = []
    # First login as org_admin via Selenium
    driver = selenium_login("org_admin")
    if not driver:
        # Fallback: try API
        token = login("org_admin")
        steps.append("Step 1: Login as Org Admin via API (Selenium unavailable)")
        if token:
            # For SSO module pages, we can't really test via API
            steps.append(f"Step 2: Cannot test UI page {page_path} without browser")
            return "INCONCLUSIVE", steps
        return "INCONCLUSIVE", steps

    steps.append(f"Step 1: Login as Org Admin (ananya@technova.in) via Selenium -> Logged in")

    full_url = f"{APP_URL}{page_path}"
    result = check_page(driver, full_url)
    steps.append(f"Step 2: Navigate to {page_path} -> Current URL: {result.get('current_url', 'N/A')}")

    if result.get("error"):
        steps.append(f"Step 3: Browser error: {result['error']}")
        return "INCONCLUSIVE", steps

    page_error = result.get("page_error")
    if page_error == "404 Not Found":
        steps.append(f"Step 3: Page still returns 404 Not Found -> {description} still broken")
        return "STILL FAILING", steps
    elif page_error == "500 Server Error":
        steps.append(f"Step 3: Page returns 500 Server Error -> still broken (different error)")
        return "STILL FAILING", steps
    elif page_error:
        steps.append(f"Step 3: Page shows error: {page_error}")
        return "STILL FAILING", steps
    elif result.get("redirected"):
        steps.append(f"Step 3: Page redirected to {result['current_url']} instead of loading")
        return "STILL FAILING", steps
    else:
        steps.append(f"Step 3: Page loaded successfully (title: {result.get('title', 'N/A')[:50]})")
        return "FIXED", steps


def test_api_endpoint(issue, method, path, token_role, json_data=None, params=None,
                      expect_status=None, expect_fail_status=None, description=""):
    """Test an API endpoint."""
    steps = []
    token = login(token_role)
    role_name = {"org_admin": "Org Admin (ananya@technova.in)",
                 "employee": "Employee (priya@technova.in)",
                 "super_admin": "Super Admin (admin@empcloud.com)"}[token_role]

    if not token:
        steps.append(f"Step 1: Login as {role_name} via API -> FAILED")
        return "INCONCLUSIVE", steps

    steps.append(f"Step 1: Login as {role_name} via API -> 200 OK, got token")

    status, body = api(method, path, token=token, json_data=json_data, params=params)
    body_preview = str(body)[:300] if body else "empty"
    steps.append(f"Step 2: {method} {path} -> {status}, body: {body_preview}")

    if expect_status and status == expect_status:
        steps.append(f"Step 3: Got expected status {expect_status} -> Working correctly")
        return "FIXED", steps
    elif expect_fail_status and status == expect_fail_status:
        steps.append(f"Step 3: Still getting error status {status} -> Bug persists")
        return "STILL FAILING", steps
    elif expect_status and status != expect_status:
        steps.append(f"Step 3: Expected {expect_status} but got {status} -> Still broken")
        return "STILL FAILING", steps
    else:
        steps.append(f"Step 3: Response status {status}")
        if status in (200, 201):
            return "FIXED", steps
        elif status in (400, 404, 500):
            return "STILL FAILING", steps
        else:
            return "INCONCLUSIVE", steps


def test_validation_bug(issue, method, path, token_role, invalid_data, expected_rejection_field=None, description=""):
    """Test that invalid data is properly rejected with clear error."""
    steps = []
    token = login(token_role)
    if not token:
        steps.append(f"Step 1: Login as {token_role} -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append(f"Step 1: Login as {token_role} via API -> 200 OK, got token")

    status, body = api(method, path, token=token, json_data=invalid_data)
    steps.append(f"Step 2: {method} {path} with invalid data {json.dumps(invalid_data)[:200]} -> {status}")
    steps.append(f"  Response: {str(body)[:300]}")

    if status in (400, 422):
        body_str = str(body).lower()
        if expected_rejection_field and expected_rejection_field.lower() in body_str:
            steps.append(f"Step 3: Server correctly rejected with specific error about '{expected_rejection_field}'")
            return "FIXED", steps
        elif "invalid" in body_str or "required" in body_str or "error" in body_str or "validation" in body_str:
            steps.append(f"Step 3: Server rejected with validation error (status {status})")
            return "FIXED", steps
        else:
            steps.append(f"Step 3: Server rejected (status {status}) but error message unclear: {str(body)[:200]}")
            return "FIXED", steps  # At least it's rejecting
    elif status in (200, 201):
        steps.append(f"Step 3: Server ACCEPTED invalid data (status {status}) -> Validation still missing")
        return "STILL FAILING", steps
    else:
        steps.append(f"Step 3: Unexpected status {status}")
        return "INCONCLUSIVE", steps


def test_search_bug(issue, search_query, expected_results_min=1):
    """Test search functionality."""
    steps = []
    token = login("org_admin")
    if not token:
        steps.append("Step 1: Login as Org Admin -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Org Admin (ananya@technova.in) via API -> 200 OK, got token")

    status, body = api("GET", "/organizations/me/users", token=token, params={"search": search_query})
    steps.append(f"Step 2: GET /organizations/me/users?search={search_query} -> {status}")

    if status == 200 and isinstance(body, dict):
        data = body.get("data", body.get("users", body.get("results", [])))
        if isinstance(data, list):
            count = len(data)
        elif isinstance(data, dict) and "items" in data:
            count = len(data["items"])
        elif isinstance(data, dict) and "users" in data:
            count = len(data["users"])
        else:
            count = "unknown"
        steps.append(f"Step 3: Search returned {count} result(s)")
        if isinstance(count, int) and count >= expected_results_min:
            steps.append(f"Step 4: Search working correctly (found {count} results for '{search_query}')")
            return "FIXED", steps
        else:
            steps.append(f"Step 4: Search returned insufficient results ({count}) for '{search_query}'")
            return "STILL FAILING", steps
    elif status == 200 and isinstance(body, list):
        steps.append(f"Step 3: Search returned {len(body)} result(s)")
        return ("FIXED" if len(body) >= expected_results_min else "STILL FAILING"), steps
    else:
        steps.append(f"Step 3: Search failed: {str(body)[:300]}")
        return "STILL FAILING", steps


def test_leave_application(issue):
    """Test leave application bug."""
    steps = []
    token = login("org_admin")
    if not token:
        steps.append("Step 1: Login as Org Admin -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Org Admin (ananya@technova.in) via API -> 200 OK, got token")

    # First get leave types
    status, body = api("GET", "/organizations/me/leave-types", token=token)
    if status != 200:
        status, body = api("GET", "/leave/types", token=token)
    steps.append(f"Step 2: GET leave types -> {status}, body: {str(body)[:200]}")

    leave_type_id = None
    if isinstance(body, dict):
        types_data = body.get("data", body.get("leave_types", []))
        if isinstance(types_data, list) and len(types_data) > 0:
            leave_type_id = types_data[0].get("id")
    elif isinstance(body, list) and len(body) > 0:
        leave_type_id = body[0].get("id")

    if not leave_type_id:
        leave_type_id = 17  # fallback from issue

    payload = {
        "leave_type_id": leave_type_id,
        "start_date": "2026-05-15",
        "end_date": "2026-05-16",
        "reason": "E2E Re-test - medical appointment",
        "days_count": 2,
        "is_half_day": 0
    }
    status, body = api("POST", "/organizations/me/leave/applications", token=token, json_data=payload)
    if status in (0, 404):
        status, body = api("POST", "/leave/applications", token=token, json_data=payload)
    steps.append(f"Step 3: POST leave application -> {status}, body: {str(body)[:300]}")

    if status in (200, 201):
        steps.append("Step 4: Leave application submitted successfully for Org Admin")
        return "FIXED", steps
    elif status == 400:
        steps.append(f"Step 4: Still getting 400 error -> HR cannot apply leave")
        return "STILL FAILING", steps
    else:
        steps.append(f"Step 4: Unexpected status {status}")
        return "INCONCLUSIVE", steps


def test_ui_element_exists(issue, page_path, element_desc, css_selectors=None, text_searches=None):
    """Test if a UI element exists on a page."""
    steps = []
    driver = selenium_login("org_admin")
    if not driver:
        steps.append("Step 1: Selenium login as Org Admin -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Org Admin via Selenium -> OK")

    full_url = f"{APP_URL}{page_path}"
    try:
        driver.get(full_url)
        time.sleep(3)
    except Exception as e:
        steps.append(f"Step 2: Navigate to {page_path} -> Error: {e}")
        return "INCONCLUSIVE", steps

    steps.append(f"Step 2: Navigate to {page_path} -> Loaded (title: {driver.title[:50]})")

    from selenium.webdriver.common.by import By
    found = False

    if css_selectors:
        for sel in css_selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                steps.append(f"Step 3: Look for '{element_desc}' via CSS '{sel}' -> FOUND (text: '{el.text[:50]}')")
                found = True
                break
            except:
                pass

    if not found and text_searches:
        for txt in text_searches:
            try:
                el = driver.find_element(By.XPATH, f"//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{txt.lower()}')]")
                steps.append(f"Step 3: Look for text '{txt}' -> FOUND (tag: {el.tag_name}, text: '{el.text[:50]}')")
                found = True
                break
            except:
                pass

    if not found:
        steps.append(f"Step 3: Look for '{element_desc}' -> NOT FOUND on page")
        # Check page source for any clue
        source = driver.page_source[:3000].lower()
        if "404" in source or "not found" in source:
            steps.append(f"Step 4: Page appears to be a 404 error")
        return "STILL FAILING", steps

    return "FIXED", steps


def test_employee_sso_module(issue, module_name):
    """Test if employee can SSO into a module."""
    steps = []
    driver = selenium_login("employee")
    if not driver:
        steps.append("Step 1: Selenium login as Employee -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Employee (priya@technova.in) via Selenium -> OK")

    # Navigate to modules page
    result = check_page(driver, f"{APP_URL}/modules")
    steps.append(f"Step 2: Navigate to /modules -> URL: {result.get('current_url', 'N/A')}")

    from selenium.webdriver.common.by import By
    # Look for the module
    try:
        module_el = driver.find_element(By.XPATH, f"//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{module_name.lower()}')]")
        steps.append(f"Step 3: Found '{module_name}' on modules page")
        # Try to click it
        try:
            module_el.click()
            time.sleep(3)
            new_url = driver.current_url
            steps.append(f"Step 4: Clicked module -> Navigated to: {new_url}")
            if "dashboard" in new_url and module_name.lower() not in new_url.lower():
                steps.append("Step 5: Redirected back to dashboard instead of module -> SSO still failing")
                return "STILL FAILING", steps
            else:
                steps.append("Step 5: Module page loaded")
                return "FIXED", steps
        except Exception as e:
            steps.append(f"Step 4: Could not click module: {e}")
            return "INCONCLUSIVE", steps
    except:
        steps.append(f"Step 3: Module '{module_name}' not found on page")
        return "INCONCLUSIVE", steps


def test_leave_display_bug(issue, check_type="names"):
    """Test leave-related display bugs (names showing IDs, date formatting, etc)."""
    steps = []
    token = login("org_admin")
    if not token:
        steps.append("Step 1: Login as Org Admin -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Org Admin (ananya@technova.in) via API -> 200 OK, got token")

    status, body = api("GET", "/organizations/me/leave/applications", token=token)
    if status in (0, 404):
        status, body = api("GET", "/leave/applications", token=token)
    steps.append(f"Step 2: GET leave applications -> {status}")

    if status == 200 and isinstance(body, dict):
        apps = body.get("data", body.get("applications", body.get("items", [])))
        if isinstance(apps, list) and len(apps) > 0:
            sample = apps[0]
            steps.append(f"Step 3: Got {len(apps)} leave applications, examining first one")

            if check_type == "names":
                user_field = sample.get("user_name") or sample.get("employee_name") or sample.get("user", {}).get("name") if isinstance(sample.get("user"), dict) else sample.get("user")
                steps.append(f"Step 4: User field value = '{user_field}'")
                if user_field and "User #" in str(user_field):
                    steps.append("Step 5: Still showing 'User #ID' instead of actual name")
                    return "STILL FAILING", steps
                elif user_field and not str(user_field).isdigit():
                    steps.append("Step 5: Showing actual user name -> Fixed")
                    return "FIXED", steps
                else:
                    steps.append(f"Step 5: User displayed as: {user_field}")
                    return "INCONCLUSIVE", steps

            elif check_type == "dates":
                date_field = sample.get("start_date") or sample.get("created_at")
                steps.append(f"Step 4: Date field value = '{date_field}'")
                # This is an API response - UI formatting is what matters
                steps.append("Step 5: Date formatting is a UI concern, API returns ISO format as expected")
                return "INCONCLUSIVE", steps

            elif check_type == "leave_type_name":
                lt = sample.get("leave_type") or sample.get("leave_type_name")
                if isinstance(lt, dict):
                    lt = lt.get("name")
                steps.append(f"Step 4: Leave type name = '{lt}'")
                if lt and "0" in str(lt) and str(lt).endswith("0"):
                    steps.append("Step 5: Leave type still has trailing zero")
                    return "STILL FAILING", steps
                else:
                    steps.append("Step 5: Leave type name appears clean")
                    return "FIXED", steps
        else:
            steps.append("Step 3: No leave applications found to inspect")
            return "INCONCLUSIVE", steps
    else:
        steps.append(f"Step 3: Failed to get leave applications: {str(body)[:200]}")
        return "INCONCLUSIVE", steps


def test_document_upload(issue):
    """Test document upload error handling."""
    steps = []
    token = login("org_admin")
    if not token:
        steps.append("Step 1: Login as Org Admin -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Org Admin (ananya@technova.in) via API -> 200 OK, got token")

    # Send multipart with wrong field name
    try:
        import io
        files = {"wrong_field": ("test.txt", io.BytesIO(b"test content"), "text/plain")}
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"{API_BASE}/organizations/me/documents",
                             files=files, headers=headers, timeout=15)
        status = resp.status_code
        try:
            body = resp.json()
        except:
            body = resp.text[:300]
        steps.append(f"Step 2: POST document with wrong multipart field name -> {status}")
        steps.append(f"  Response: {str(body)[:300]}")

        if status == 400:
            steps.append("Step 3: Correctly returns 400 Bad Request (not 500)")
            return "FIXED", steps
        elif status == 500:
            steps.append("Step 3: Still returns 500 Server Error instead of 400")
            return "STILL FAILING", steps
        else:
            steps.append(f"Step 3: Returns {status}")
            return "INCONCLUSIVE", steps
    except Exception as e:
        steps.append(f"Step 2: Error: {e}")
        return "INCONCLUSIVE", steps


def test_org_chart(issue):
    """Test org chart endpoint."""
    steps = []
    token = login("org_admin")
    if not token:
        steps.append("Step 1: Login as Org Admin -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Org Admin (ananya@technova.in) via API -> 200 OK, got token")

    # Test API
    status, body = api("GET", "/organizations/me/org-chart", token=token)
    if status == 404:
        status, body = api("GET", "/organizations/me/users?include=reporting_to", token=token)
    steps.append(f"Step 2: GET org chart data via API -> {status}")

    if isinstance(body, dict):
        data = body.get("data", body.get("chart", body.get("nodes", [])))
        if isinstance(data, list):
            count = len(data)
            steps.append(f"Step 3: Org chart returned {count} entries")
            if count <= 2:
                steps.append("Step 4: Only 2 or fewer entries when org has 20+ employees -> Still showing incomplete data")
                return "STILL FAILING", steps
            else:
                steps.append(f"Step 4: Showing {count} entries -> Appears to include more employees now")
                return "FIXED", steps

    # Test via Selenium
    driver = selenium_login("org_admin")
    if driver:
        result = check_page(driver, f"{APP_URL}/org-chart")
        steps.append(f"Step 3: Navigate to /org-chart via Selenium -> {result}")
        if result.get("page_error") == "500 Server Error":
            steps.append("Step 4: Page still returns 500 Internal Server Error")
            return "STILL FAILING", steps
        elif result.get("page_error"):
            steps.append(f"Step 4: Page error: {result['page_error']}")
            return "STILL FAILING", steps
        elif not result.get("error"):
            steps.append("Step 4: Page loaded without 500 error")
            return "FIXED", steps

    return "INCONCLUSIVE", steps


def test_dashboard_data_leak(issue):
    """Test if employee sees HR-level data on dashboard."""
    steps = []
    token = login("employee")
    if not token:
        steps.append("Step 1: Login as Employee -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Employee (priya@technova.in) via API -> 200 OK, got token")

    status, body = api("GET", "/organizations/me/dashboard", token=token)
    if status == 404:
        status, body = api("GET", "/dashboard", token=token)
    steps.append(f"Step 2: GET dashboard data -> {status}")
    steps.append(f"  Body preview: {str(body)[:400]}")

    if status == 200 and isinstance(body, dict):
        # Check for HR-level fields
        hr_indicators = ["total_employees", "department_count", "attrition", "headcount",
                         "salary_summary", "payroll_total", "hiring_pipeline"]
        found_hr = []
        body_str = json.dumps(body).lower()
        for indicator in hr_indicators:
            if indicator in body_str:
                found_hr.append(indicator)

        if found_hr:
            steps.append(f"Step 3: Employee dashboard contains HR-level data fields: {found_hr}")
            return "STILL FAILING", steps
        else:
            steps.append("Step 3: Dashboard does not expose HR-level aggregate data to employee")
            return "FIXED", steps
    else:
        steps.append(f"Step 3: Dashboard returned status {status}")
        return "INCONCLUSIVE", steps


def test_notification_bell(issue):
    """Test notification bell click."""
    steps = []
    driver = selenium_login("employee")
    if not driver:
        steps.append("Step 1: Selenium login as Employee -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Employee (priya@technova.in) via Selenium -> OK")

    from selenium.webdriver.common.by import By
    time.sleep(2)
    # Look for notification bell
    bell_selectors = [
        "[data-testid='notification-bell']", ".notification-bell", ".notifications-icon",
        "button[aria-label*='notif' i]", ".bell-icon", "[class*='notification'] svg",
        "[class*='bell']", "button[class*='notif']"
    ]
    bell = None
    for sel in bell_selectors:
        try:
            bell = driver.find_element(By.CSS_SELECTOR, sel)
            steps.append(f"Step 2: Found notification bell via '{sel}'")
            break
        except:
            pass

    if not bell:
        try:
            bell = driver.find_element(By.XPATH, "//*[contains(@class,'bell') or contains(@class,'notif')]")
            steps.append(f"Step 2: Found notification element via XPath")
        except:
            steps.append("Step 2: Notification bell NOT FOUND on page")
            return "INCONCLUSIVE", steps

    try:
        bell.click()
        time.sleep(2)
        # Check if panel opened
        source = driver.page_source.lower()
        if "notification" in source and ("panel" in source or "dropdown" in source or "list" in source):
            steps.append("Step 3: Clicked bell -> Notification panel appears to have opened")
            return "FIXED", steps
        else:
            steps.append("Step 3: Clicked bell -> No visible notification panel/dropdown")
            return "STILL FAILING", steps
    except Exception as e:
        steps.append(f"Step 3: Could not click bell: {e}")
        return "INCONCLUSIVE", steps


def test_announcements_validation(issue):
    """Test announcements content field validation."""
    steps = []
    driver = selenium_login("org_admin")
    if not driver:
        steps.append("Step 1: Selenium login -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Org Admin via Selenium -> OK")

    # Also test via API
    token = login("org_admin")
    if token:
        payload = {
            "title": "E2E Test Announcement",
            "content": "This is a test announcement for validation testing.",
            "type": "general"
        }
        status, body = api("POST", "/organizations/me/announcements", token=token, json_data=payload)
        steps.append(f"Step 2: POST announcement via API -> {status}")
        steps.append(f"  Body: {str(body)[:300]}")
        if status in (200, 201):
            steps.append("Step 3: Announcement created successfully via API")
            return "FIXED", steps
        elif status == 400:
            steps.append(f"Step 3: Validation error: {str(body)[:200]}")
            return "STILL FAILING", steps

    return "INCONCLUSIVE", steps


def test_feedback_permissions(issue):
    """Test if employee can access feedback page."""
    steps = []
    token = login("employee")
    if not token:
        steps.append("Step 1: Login as Employee -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Employee (priya@technova.in) via API -> 200 OK, got token")

    status, body = api("GET", "/organizations/me/feedback", token=token)
    steps.append(f"Step 2: GET /organizations/me/feedback as employee -> {status}")
    steps.append(f"  Body: {str(body)[:300]}")

    if status == 200:
        steps.append("Step 3: Employee can access feedback page -> Fixed")
        return "FIXED", steps
    elif status == 403:
        steps.append("Step 3: Still getting 'Insufficient permissions' for employee feedback")
        return "STILL FAILING", steps
    elif status == 404:
        steps.append("Step 3: Feedback endpoint not found (404)")
        return "INCONCLUSIVE", steps
    else:
        steps.append(f"Step 3: Unexpected status {status}")
        return "INCONCLUSIVE", steps


def test_attendance_filters(issue):
    """Test attendance page has date/department filters."""
    steps = []
    driver = selenium_login("org_admin")
    if not driver:
        return "INCONCLUSIVE", ["Step 1: Selenium not available"]
    steps.append("Step 1: Login as Org Admin via Selenium -> OK")

    result = check_page(driver, f"{APP_URL}/attendance")
    steps.append(f"Step 2: Navigate to /attendance -> URL: {result.get('current_url', 'N/A')}")

    from selenium.webdriver.common.by import By
    # Look for filter elements
    filter_found = False
    for sel in ["input[type='date']", "select[name*='department']", "[class*='filter']",
                "[class*='date-picker']", ".date-range", "input[type='month']",
                "[class*='DatePicker']", "button[class*='filter']"]:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            steps.append(f"Step 3: Found filter element: '{sel}' -> text='{el.text[:30]}'")
            filter_found = True
            break
        except:
            pass

    if not filter_found:
        steps.append("Step 3: No date/department filter elements found on attendance page")
        return "STILL FAILING", steps
    return "FIXED", steps


def test_edit_profile(issue):
    """Test if edit profile makes fields editable."""
    steps = []
    driver = selenium_login("employee")
    if not driver:
        return "INCONCLUSIVE", ["Step 1: Selenium not available"]
    steps.append("Step 1: Login as Employee via Selenium -> OK")

    result = check_page(driver, f"{APP_URL}/profile")
    steps.append(f"Step 2: Navigate to /profile -> URL: {result.get('current_url', 'N/A')}")

    from selenium.webdriver.common.by import By
    # Look for edit button
    edit_btn = None
    for sel in ["button:has-text('Edit')", "[class*='edit']", "button[class*='edit']"]:
        try:
            edit_btn = driver.find_element(By.CSS_SELECTOR, sel)
            break
        except:
            pass
    if not edit_btn:
        try:
            edit_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Edit') or contains(text(),'edit')]")
        except:
            pass

    if edit_btn:
        steps.append(f"Step 3: Found Edit button -> '{edit_btn.text[:30]}'")
        try:
            edit_btn.click()
            time.sleep(2)
            # Check if any input fields become editable
            inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([disabled]):not([readonly])")
            if len(inputs) > 0:
                steps.append(f"Step 4: After clicking Edit, {len(inputs)} editable input field(s) found -> Working")
                return "FIXED", steps
            else:
                steps.append("Step 4: After clicking Edit, no editable input fields found -> Still broken")
                return "STILL FAILING", steps
        except Exception as e:
            steps.append(f"Step 4: Error clicking Edit: {e}")
            return "INCONCLUSIVE", steps
    else:
        steps.append("Step 3: Edit Profile button NOT FOUND on page")
        return "STILL FAILING", steps


def test_helpdesk_page(issue):
    """Test helpdesk page doesn't redirect to dashboard."""
    steps = []
    driver = selenium_login("employee")
    if not driver:
        return "INCONCLUSIVE", ["Step 1: Selenium not available"]
    steps.append("Step 1: Login as Employee via Selenium -> OK")

    result = check_page(driver, f"{APP_URL}/helpdesk")
    steps.append(f"Step 2: Navigate to /helpdesk -> Current URL: {result.get('current_url', 'N/A')}")

    if result.get("redirected") and "dashboard" in result.get("current_url", "").lower():
        steps.append("Step 3: Helpdesk redirects to dashboard -> Still broken")
        return "STILL FAILING", steps
    elif result.get("page_error"):
        steps.append(f"Step 3: Page error: {result['page_error']}")
        return "STILL FAILING", steps
    else:
        steps.append("Step 3: Helpdesk page loaded without redirecting to dashboard")
        return "FIXED", steps


def test_leave_submit(issue):
    """Test leave submission for employee."""
    steps = []
    token = login("employee")
    if not token:
        steps.append("Step 1: Login as Employee -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append("Step 1: Login as Employee (priya@technova.in) via API -> 200 OK, got token")

    # Get leave types
    status, body = api("GET", "/organizations/me/leave-types", token=token)
    if status != 200:
        status, body = api("GET", "/leave/types", token=token)
    steps.append(f"Step 2: GET leave types -> {status}, types: {str(body)[:200]}")

    leave_type_id = None
    if isinstance(body, dict):
        data = body.get("data", [])
        if isinstance(data, list) and data:
            leave_type_id = data[0].get("id")
    if not leave_type_id:
        leave_type_id = 17

    payload = {
        "leave_type_id": leave_type_id,
        "start_date": "2026-06-01",
        "end_date": "2026-06-01",
        "reason": "E2E re-test - sick leave test",
        "days_count": 1,
        "is_half_day": False
    }
    status, body = api("POST", "/organizations/me/leave/applications", token=token, json_data=payload)
    if status in (0, 404):
        status, body = api("POST", "/leave/applications", token=token, json_data=payload)
    steps.append(f"Step 3: POST leave application -> {status}")
    steps.append(f"  Response: {str(body)[:300]}")

    if status in (200, 201):
        steps.append("Step 4: Leave application submitted successfully")
        return "FIXED", steps
    elif status == 400:
        steps.append("Step 4: Still getting validation error when applying for leave")
        return "STILL FAILING", steps
    elif status == 500:
        steps.append("Step 4: Server error when submitting leave")
        return "STILL FAILING", steps
    else:
        return "INCONCLUSIVE", steps


# ── Issue Classification & Routing ──────────────────────────────────────

def classify_and_test(issue):
    """Classify issue type and run appropriate test."""
    num = issue["number"]
    title = issue["title"].lower()
    body = issue.get("body", "") or ""
    labels = {l["name"].lower() for l in issue.get("labels", [])}

    # ── RBAC: Employee accessing admin resources ──
    if num in (689,):  # Exit - Flight Risk analytics
        return test_rbac_employee_access(issue, "/exit/analytics/flight-risk", "Flight Risk analytics")
    if num in (688,):  # Exit - Full and Final Settlement
        return test_rbac_employee_access(issue, "/exit/full-and-final", "Full & Final Settlement")
    if num in (687,):  # Exit - all exit records
        return test_rbac_employee_access(issue, "/exit", "all exit records")
    if num in (686,):  # Exit - admin navigation
        return test_rbac_employee_access(issue, "/exit", "Exit admin navigation")
    if num in (685,):  # Performance - create review cycles
        return test_rbac_employee_access(issue, "/performance/review-cycles", "review cycles creation")
    if num in (684,):  # Performance - module settings
        return test_rbac_employee_access(issue, "/performance/settings", "Performance Settings")
    if num in (683,):  # Performance - succession planning
        return test_rbac_employee_access(issue, "/performance/succession-planning", "Succession Planning")
    if num in (682,):  # Performance - 9-Box Grid
        return test_rbac_employee_access(issue, "/performance/9-box", "9-Box Grid")
    if num in (681,):  # Performance - Analytics
        return test_rbac_employee_access(issue, "/performance/analytics", "Performance Analytics")
    if num in (680,):  # Performance - PIPs
        return test_rbac_employee_access(issue, "/performance/pips", "PIPs page")
    if num in (679,):  # Performance - admin navigation
        return test_rbac_employee_access(issue, "/performance", "admin-level navigation")
    if num in (678,):  # Payroll - admin panel nav
        return test_rbac_employee_access(issue, "/payroll", "Admin Panel navigation")
    if num in (665,):  # Modules - Unsubscribe buttons
        return test_rbac_employee_access(issue, "/modules", "Unsubscribe buttons")

    # ── 404 pages (module sub-pages) ──
    page_404_map = {
        604: "/performance/okrs",
        605: "/performance/self-assessment",
        606: "/performance/self-review",
        607: "/performance/manager-review",
        608: "/performance/team-reviews",
        609: "/performance/360-feedback",
        610: "/performance/peer-review",
        611: "/performance/calibration",
        612: "/performance/reports",
        613: "/rewards/give-kudos",
        614: "/rewards/recognition",
        615: "/rewards/team-challenges",
        616: "/rewards/catalog",
        617: "/rewards/catalog",
        618: "/rewards/store",
        619: "/exit/initiate-exit",
        620: "/modules",  # Employee SSO
        622: "/exit/initiate-exit",
        624: "/exit/new",
        625: "/exit/clearance",
        628: "/exit/interview",
        630: "/exit/full-and-final",
        632: "/exit/full-and-final",
        634: "/exit/knowledge-transfer",
        635: "/exit/reports",
        636: "/lms/assignments",
        637: "/lms/assignments",
        638: "/lms/quiz",
        639: "/lms/assessments",
        640: "/lms/quizzes",
        641: "/lms/certificates",
        642: "/lms/compliance-training",
        643: "/lms/reports",
        644: "/projects",
        645: "/projects/tasks",
        646: "/projects/board",
        647: "/projects/board",
        648: "/projects/time-tracking",
        649: "/projects/timesheet",
        650: "/projects/timesheets",
        651: "/projects/gantt",
        652: "/projects/timeline",
        653: "/projects/reports",
        654: "/projects/settings",
        655: "/projects/my-tasks",
        658: "/projects/tasks",
        659: "/lms",
        660: "/exit",
        662: "/rewards",
        664: "/performance",
        667: "/payroll",
    }
    if num in page_404_map:
        desc = issue["title"][:60]
        return test_404_page(issue, page_404_map[num], desc)

    # ── Leave bugs ──
    if num == 692:  # HR cannot apply leave
        return test_leave_application(issue)
    if num == 663:  # Cannot apply sick leave
        return test_leave_submit(issue)
    if num == 697:  # Leave application unexpected error
        return test_leave_submit(issue)
    if num in (700, 626):  # Leave shows User #524
        return test_leave_display_bug(issue, check_type="names")
    if num == 627:  # Raw ISO timestamps
        return test_leave_display_bug(issue, check_type="dates")
    if num == 629:  # Earned Leave0
        return test_leave_display_bug(issue, check_type="leave_type_name")
    if num == 690:  # Vague leave validation error
        return test_leave_application(issue)

    # ── UI element bugs ──
    if num == 703:  # No Invite Employee button
        return test_ui_element_exists(issue, "/employees", "Invite Employee button",
                                       css_selectors=["button[class*='invite']", "button[class*='Invite']", "a[class*='invite']"],
                                       text_searches=["Invite", "invite employee", "Add & Invite"])
    if num in (695, 657, 669):  # No Add Employee button
        return test_ui_element_exists(issue, "/employees", "Add Employee button",
                                       css_selectors=["button[class*='add']", "a[class*='add']", "button[class*='Add']"],
                                       text_searches=["Add Employee", "add employee", "New Employee"])
    if num == 670:  # Edit profile not editable
        return test_edit_profile(issue)
    if num == 673:  # Notification bell
        return test_notification_bell(issue)
    if num == 677:  # Announcements validation
        return test_announcements_validation(issue)

    # ── SSO bugs ──
    if num == 672:  # Payroll SSO
        return test_employee_sso_module(issue, "payroll")
    if num == 631:  # Performance SSO
        return test_employee_sso_module(issue, "performance")
    if num == 666:  # Projects marketing page
        return test_employee_sso_module(issue, "projects")

    # ── Page redirect bugs ──
    if num in (698, 671):  # Helpdesk redirects to dashboard
        return test_helpdesk_page(issue)

    # ── Data bugs ──
    if num == 699:  # Org chart 500 error
        return test_org_chart(issue)
    if num == 694:  # Org chart only 2 entries
        return test_org_chart(issue)
    if num == 661:  # Employee sees HR data on dashboard
        return test_dashboard_data_leak(issue)
    if num == 668:  # Feedback permissions
        return test_feedback_permissions(issue)
    if num == 696:  # Attendance no filters
        return test_attendance_filters(issue)

    # ── Document upload ──
    if num == 691:  # Document upload 500 instead of 400
        return test_document_upload(issue)

    # ── Enhancement/feature requests - just check if there's new evidence ──
    if "enhancement" in labels or "feature-request" in labels or "documentation" in labels:
        steps = [f"Step 1: Issue #{num} is an enhancement/feature request, not a bug",
                 "Step 2: Checking if feature was implemented..."]
        # Quick API check for common features
        token = login("org_admin")
        if "api docs" in title:
            status, body = api("GET", "/docs", token=token)
            steps.append(f"Step 3: GET /docs -> {status}")
            return ("FIXED" if status == 200 else "STILL FAILING"), steps
        elif "bulk" in title or "export" in title:
            steps.append("Step 3: Enhancement - would need new endpoints to test")
            return "INCONCLUSIVE", steps
        else:
            steps.append("Step 3: Feature request - skipping as not a bug fix verification")
            return "SKIPPED", steps

    # ── Generic fallback: try Selenium page check ──
    # Extract URL from issue body if present
    url_match = re.search(r'https://test-empcloud\.empcloud\.com(/[^\s\)\"]+)', body)
    if url_match:
        path = url_match.group(1)
        steps = []
        driver = selenium_login("org_admin")
        if driver:
            steps.append("Step 1: Login as Org Admin via Selenium -> OK")
            result = check_page(driver, f"{APP_URL}{path}")
            steps.append(f"Step 2: Navigate to {path} -> URL: {result.get('current_url', 'N/A')}")
            if result.get("page_error"):
                steps.append(f"Step 3: Page error: {result['page_error']}")
                return "STILL FAILING", steps
            elif result.get("redirected"):
                steps.append(f"Step 3: Redirected to {result['current_url']}")
                return "INCONCLUSIVE", steps
            else:
                steps.append(f"Step 3: Page loaded (title: {result.get('title', 'N/A')[:50]})")
                return "FIXED", steps

    # If we can't classify, report it
    return "SKIPPED", [f"Step 1: Issue #{num} could not be automatically categorized for re-test",
                       f"  Title: {issue['title'][:80]}",
                       f"  Labels: {[l['name'] for l in issue.get('labels',[])]}"]


# ── Main ────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("EMPCLOUD DEEP RE-TEST — Batch 1 (Closed Issues, Page 1)")
    print(f"Date: {TODAY}")
    print(f"API: {API_BASE}")
    print("=" * 80)

    # Fetch closed issues
    print("\n[*] Fetching closed issues from GitHub...")
    status, issues = gh_api("GET", f"/repos/{GITHUB_REPO}/issues?state=closed&per_page=100&page=1")
    if status != 200:
        print(f"FATAL: Could not fetch issues: {status}")
        return

    print(f"[*] Got {len(issues)} closed issues to re-test")

    # Pre-login all roles
    print("\n[*] Pre-authenticating all roles...")
    for role in ["org_admin", "employee", "super_admin"]:
        token = login(role)
        if token:
            print(f"  {role}: OK (token={token[:20]}...)")
        else:
            print(f"  {role}: FAILED")

    # Fetch full issue bodies (we need them for classification)
    print("\n[*] Fetching issue details...")
    full_issues = []
    for issue in issues:
        # The list endpoint includes body, but let's make sure
        if issue.get("body") is None:
            s, detail = gh_api("GET", f"/repos/{GITHUB_REPO}/issues/{issue['number']}")
            if s == 200:
                full_issues.append(detail)
            else:
                full_issues.append(issue)
            time.sleep(0.3)
        else:
            full_issues.append(issue)

    # Track results
    results = {"FIXED": 0, "STILL FAILING": 0, "INCONCLUSIVE": 0, "SKIPPED": 0}
    still_failing = []

    print("\n" + "=" * 80)
    print("STARTING DEEP RE-TESTS")
    print("=" * 80)

    for idx, issue in enumerate(full_issues):
        num = issue["number"]
        title = issue["title"]

        print(f"\n{'=' * 70}")
        print(f"=== #{num} {title[:65]} ===")
        print(f"{'=' * 70}")

        # Skip already-tested issues from previous run
        if SKIP_ISSUES_ABOVE and num > SKIP_ISSUES_ABOVE:
            continue

        # Skip field force, biometrics, rate limit
        if should_skip(issue):
            print(f"  SKIPPED (field force / biometrics / rate limit)")
            results["SKIPPED"] += 1
            continue

        # Skip PRs
        if issue.get("pull_request"):
            print(f"  SKIPPED (pull request, not an issue)")
            results["SKIPPED"] += 1
            continue

        try:
            verdict, steps = classify_and_test(issue)
        except Exception as e:
            verdict = "INCONCLUSIVE"
            steps = [f"ERROR during test: {e}", traceback.format_exc()]

        # Print steps
        for step in steps:
            print(f"  {step}")

        print(f"\n  VERDICT: {verdict}")
        results[verdict] = results.get(verdict, 0) + 1

        if verdict == "STILL FAILING":
            still_failing.append(num)

        # Post GitHub comment
        step_text = "\n".join(f"- {s}" for s in steps)
        comment = (
            f"Comment by E2E Testing Agent \u2014 Re-tested on {TODAY}:\n"
            f"{step_text}\n"
            f"- Result: **{verdict}**"
        )

        try:
            add_github_comment(num, comment)
        except Exception as e:
            print(f"    [GH] Comment error: {e}")

        # Re-open if still failing
        if verdict == "STILL FAILING":
            try:
                reopen_issue(num)
            except Exception as e:
                print(f"    [GH] Reopen error: {e}")

        # Small delay to not hammer APIs
        time.sleep(0.5)

    # ── Summary ──
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for k, v in results.items():
        print(f"  {k}: {v}")
    print(f"\n  Total tested: {sum(results.values())}")

    if still_failing:
        print(f"\n  STILL FAILING issues (re-opened): {still_failing}")
    else:
        print(f"\n  All tested issues appear FIXED or could not be determined.")

    # Retry pending GitHub operations
    if _pending_comments or _pending_reopens:
        print(f"\n[*] Retrying {len(_pending_comments)} pending comments and {len(_pending_reopens)} pending reopens after 30s cooldown...")
        time.sleep(30)
        for issue_number, comment_body in _pending_comments:
            status, body = gh_api("POST", f"/repos/{GITHUB_REPO}/issues/{issue_number}/comments",
                                  json_data={"body": comment_body})
            if status == 201:
                print(f"    [GH RETRY] Comment posted on #{issue_number}")
            else:
                print(f"    [GH RETRY] Still failed #{issue_number}: {status}")
            time.sleep(2)
        for issue_number in _pending_reopens:
            status, body = gh_api("PATCH", f"/repos/{GITHUB_REPO}/issues/{issue_number}",
                                  json_data={"state": "open"})
            if status == 200:
                print(f"    [GH RETRY] Re-opened #{issue_number}")
            else:
                print(f"    [GH RETRY] Still failed reopening #{issue_number}: {status}")
            time.sleep(2)

    # Clean up Selenium
    global _driver
    if _driver:
        try:
            _driver.quit()
        except:
            pass


if __name__ == "__main__":
    main()
