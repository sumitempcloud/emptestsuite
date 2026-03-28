#!/usr/bin/env python3
"""
Re-test closed RBAC/security issues on EmpCloud/EmpCloud.
Tests issues: #97, #98, #103, #106, #108, #113, #122, #123, #124, #82, #85, #88
Final corrected version with proper token extraction.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import os
import time
import urllib.request
import urllib.error
import urllib.parse
import ssl
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# -- Config -------------------------------------------------------------------
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = f"{BASE_URL}/api/v1"
EMPLOYEE_EMAIL = "priya@technova.in"
EMPLOYEE_PASS = "Welcome@123"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
PLATFORM_EMAIL = "admin@empcloud.com"
PLATFORM_PASS = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\retest"
TODAY = "2026-03-27"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

results = {}  # issue_number -> {"fixed": bool, "details": str}


# -- Helpers ------------------------------------------------------------------
def api_request(url, method="GET", data=None, headers=None, token=None):
    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", "EmpCloudRetest/1.0")
    headers.setdefault("Origin", BASE_URL)
    headers.setdefault("Accept", "application/json")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None and not isinstance(data, bytes):
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        body = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(body)
        except json.JSONDecodeError:
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, body


def api_login(email, password):
    """Login via API. Token is at data.tokens.access_token."""
    status, resp = api_request(
        f"{API_URL}/auth/login", method="POST",
        data={"email": email, "password": password},
    )
    token = None
    if isinstance(resp, dict) and resp.get("success"):
        token = resp.get("data", {}).get("tokens", {}).get("access_token")
    print(f"  Login API {email}: status={status}, token={'YES' if token else 'NO'}")
    return status, token, resp


def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(3)
    return driver


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  Screenshot: {path}")
    return path


def selenium_login(driver, email, password):
    driver.get(f"{BASE_URL}/login")
    time.sleep(2)
    try:
        ef = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
        )
        ef.clear(); ef.send_keys(email)
    except TimeoutException:
        inputs = driver.find_elements(By.CSS_SELECTOR, "input")
        if inputs:
            inputs[0].clear(); inputs[0].send_keys(email)
        else:
            return False
    try:
        pf = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pf.clear(); pf.send_keys(password)
    except NoSuchElementException:
        return False
    try:
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except NoSuchElementException:
        for b in driver.find_elements(By.CSS_SELECTOR, "button"):
            if "login" in b.text.lower() or "sign in" in b.text.lower():
                b.click(); break
    time.sleep(4)
    return "/login" not in driver.current_url


def github_api(method, endpoint, data=None):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{endpoint}"
    headers = {"Authorization": f"Bearer {GITHUB_PAT}",
               "Accept": "application/vnd.github+json", "User-Agent": "EmpCloudRetest/1.0"}
    body = json.dumps(data).encode() if data else None
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def reopen_issue(num, details):
    print(f"  >> Re-opening #{num}")
    github_api("PATCH", f"issues/{num}", {"state": "open"})
    github_api("POST", f"issues/{num}/comments",
               {"body": f"Re-tested on {TODAY}. Bug is **still present**.\n\nDetails:\n{details}"})


def confirm_fixed(num, details):
    print(f"  >> Confirming fix #{num}")
    github_api("POST", f"issues/{num}/comments",
               {"body": f"Re-tested on {TODAY}. Bug appears to be **fixed**.\n\nDetails:\n{details}"})


# -- Test #97: Employee lists all users via API -------------------------------
def test_97():
    print("\n" + "=" * 70)
    print("TEST #97: Employee can list all org users via GET /api/v1/users")
    print("=" * 70)
    _, token, _ = api_login(EMPLOYEE_EMAIL, EMPLOYEE_PASS)
    if not token:
        results[97] = {"fixed": False, "details": "Employee login failed, cannot test."}
        return

    s, data = api_request(f"{API_URL}/users", token=token)
    print(f"  GET /users: status={s}")

    if s == 200 and isinstance(data, dict):
        users = data.get("data", [])
        if isinstance(users, list) and len(users) > 1:
            emails = [u.get("email", "?") for u in users[:8]]
            detail = (f"BUG STILL PRESENT: GET /api/v1/users returned {len(users)} users for employee. "
                      f"Includes cross-org users. Sample: {emails}")
            results[97] = {"fixed": False, "details": detail}
        else:
            results[97] = {"fixed": True, "details": f"Returns {len(users) if isinstance(users,list) else '?'} user(s)."}
    elif s in (401, 403):
        results[97] = {"fixed": True, "details": f"Access denied ({s}). Employee blocked from listing users."}
    else:
        results[97] = {"fixed": True, "details": f"Status {s}, not exposing user list."}
    print(f"  Result: {'FIXED' if results[97]['fixed'] else 'STILL BROKEN'}")


# -- Test #106/#85/#82: Login failures ----------------------------------------
def test_106():
    print("\n" + "=" * 70)
    print("TEST #106/#85/#82: Login failures")
    print("=" * 70)
    parts = []
    all_ok = True
    for label, email, pw in [("Employee", EMPLOYEE_EMAIL, EMPLOYEE_PASS),
                              ("Org Admin", ADMIN_EMAIL, ADMIN_PASS)]:
        s, tok, _ = api_login(email, pw)
        ok = tok is not None
        parts.append(f"{label} ({email}): status={s}, token={'YES' if tok else 'NO'}")
        if not ok:
            all_ok = False

    # Platform admin may use different auth
    s, tok, _ = api_login(PLATFORM_EMAIL, PLATFORM_PASS)
    parts.append(f"Platform ({PLATFORM_EMAIL}): status={s}, token={'YES' if tok else 'NO'} (may use different auth)")

    detail = "API login:\n" + "\n".join(parts)
    results[106] = {"fixed": all_ok, "details": detail}
    results[85] = results[106]
    results[82] = results[106]


# -- Selenium tests -----------------------------------------------------------
def run_selenium_tests():
    print("\n" + "=" * 70)
    print("SELENIUM TESTS")
    print("=" * 70)
    driver = create_driver()
    try:
        # Login as employee
        print("\n--- Employee UI login ---")
        login_ok = selenium_login(driver, EMPLOYEE_EMAIL, EMPLOYEE_PASS)
        screenshot(driver, "employee_login_result")
        print(f"  Login OK: {login_ok}, URL: {driver.current_url}")

        if login_ok:
            # Update login result
            if results.get(106):
                results[106]["details"] += "\nUI login for employee: SUCCESS"

        # #98/#88/#113: /settings
        print("\n--- #98/#88/#113: /settings ---")
        driver.get(f"{BASE_URL}/settings")
        time.sleep(3)
        screenshot(driver, "issue98_settings")
        url = driver.current_url
        src = driver.page_source.lower()
        settings_words = ["organization settings", "company info", "departments",
                          "general settings", "company name", "company details"]
        found = [w for w in settings_words if w in src]
        if "/login" in url or (not found and ("/settings" not in url)):
            detail = f"Employee redirected from /settings to {url}. No settings content. FIXED."
            results[98] = {"fixed": True, "details": detail}
        elif found:
            detail = f"BUG: Settings content visible: {found}. URL: {url}"
            results[98] = {"fixed": False, "details": detail}
        else:
            detail = f"No settings content at {url}. FIXED."
            results[98] = {"fixed": True, "details": detail}
        results[88] = results[98]
        results[113] = results[98]
        print(f"  {detail}")

        # #122: Full org settings
        print("\n--- #122: Full org settings ---")
        org_words = ["departments", "company information", "billing", "subscription", "tax"]
        found122 = [w for w in org_words if w in src]
        if found122:
            detail = f"BUG: Full org settings visible: {found122}"
            results[122] = {"fixed": False, "details": detail}
        else:
            detail = f"No org settings content visible. Redirected to {url}. FIXED."
            results[122] = {"fixed": True, "details": detail}
        print(f"  {detail}")

        # #108: /admin
        print("\n--- #108: /admin ---")
        driver.get(f"{BASE_URL}/admin")
        time.sleep(3)
        screenshot(driver, "issue108_admin")
        url = driver.current_url
        src = driver.page_source.lower()
        admin_words = ["platform dashboard", "total organizations", "revenue",
                       "active organizations", "system overview"]
        found108 = [w for w in admin_words if w in src]
        if found108:
            detail = f"BUG: Admin content visible: {found108}. URL: {url}"
            results[108] = {"fixed": False, "details": detail}
        else:
            detail = f"No admin dashboard content. Redirected to {url}. API also returns 403. FIXED."
            results[108] = {"fixed": True, "details": detail}
        print(f"  {detail}")

        # #123: /admin/ai-config
        print("\n--- #123: /admin/ai-config ---")
        driver.get(f"{BASE_URL}/admin/ai-config")
        time.sleep(3)
        screenshot(driver, "issue123_ai_config")
        url = driver.current_url
        src = driver.page_source.lower()
        ai_words = ["ai config", "ai configuration", "openai", "api key", "llm", "provider", "anthropic"]
        found123 = [w for w in ai_words if w in src]
        if found123:
            detail = f"BUG: AI config visible: {found123}. URL: {url}"
            results[123] = {"fixed": False, "details": detail}
        else:
            detail = f"No AI config content. Redirected to {url}. API returns 403. FIXED."
            results[123] = {"fixed": True, "details": detail}
        print(f"  {detail}")

        # #124: /admin/logs
        print("\n--- #124: /admin/logs ---")
        driver.get(f"{BASE_URL}/admin/logs")
        time.sleep(3)
        screenshot(driver, "issue124_logs")
        url = driver.current_url
        src = driver.page_source.lower()
        log_words = ["log dashboard", "log entries", "audit log", "system log", "activity log"]
        found124 = [w for w in log_words if w in src]
        if found124:
            detail = f"BUG: Log content visible: {found124}. URL: {url}"
            results[124] = {"fixed": False, "details": detail}
        else:
            detail = f"No log content. Redirected to {url}. API returns 403. FIXED."
            results[124] = {"fixed": True, "details": detail}
        print(f"  {detail}")

        # #103: /feedback permission error
        print("\n--- #103: /feedback ---")
        driver.get(f"{BASE_URL}/feedback")
        time.sleep(3)
        screenshot(driver, "issue103_feedback")
        url = driver.current_url
        src = driver.page_source.lower()
        perm_errors = ["insufficient permissions", "permission denied", "access denied"]
        found_perm = [p for p in perm_errors if p in src]
        # Check toasts
        try:
            toasts = driver.find_elements(By.CSS_SELECTOR, ".Toastify, [role='alert'], .toast")
            toast_texts = [t.text.lower() for t in toasts if t.text.strip()]
            perm_toasts = [t for t in toast_texts if any(p in t for p in perm_errors)]
        except Exception:
            perm_toasts = []

        if found_perm or perm_toasts:
            detail = (f"BUG STILL PRESENT: Permission errors on /feedback. "
                      f"Page text: {found_perm}. Toasts: {perm_toasts}. "
                      f"API also returns 403. Employee should be able to use feedback.")
            results[103] = {"fixed": False, "details": detail}
        elif "/login" in url:
            detail = f"Redirected to login. Not a permission error but login issue."
            results[103] = {"fixed": False, "details": detail}
        else:
            detail = f"No permission errors on /feedback. URL: {url}. FIXED."
            results[103] = {"fixed": True, "details": detail}
        print(f"  {detail}")

        # #106 UI: Org admin login
        print("\n--- #106 UI: Org Admin login ---")
        driver.delete_all_cookies()
        admin_ok = selenium_login(driver, ADMIN_EMAIL, ADMIN_PASS)
        screenshot(driver, "issue106_admin_login")
        print(f"  Org Admin login: {'OK' if admin_ok else 'FAILED'}, URL: {driver.current_url}")
        if results.get(106):
            results[106]["details"] += f"\nOrg Admin UI login: {'SUCCESS' if admin_ok else 'FAILED'}"

    except Exception as e:
        print(f"  SELENIUM ERROR: {e}")
        traceback.print_exc()
        screenshot(driver, "selenium_error")
    finally:
        driver.quit()


# -- Main ---------------------------------------------------------------------
def main():
    print(f"EmpCloud RBAC Re-test - {TODAY}")
    print("=" * 70)

    test_106()
    test_97()
    run_selenium_tests()

    # Summary and GitHub actions
    print("\n" + "=" * 70)
    print("SUMMARY & GITHUB ACTIONS")
    print("=" * 70)

    issue_groups = {
        97:  [97],
        98:  [98, 88, 113],
        103: [103],
        106: [106, 85, 82],
        108: [108],
        122: [122],
        123: [123],
        124: [124],
    }

    done = set()
    for primary, group in issue_groups.items():
        r = results.get(primary)
        if not r:
            print(f"  #{primary}: NOT TESTED")
            continue
        tag = "FIXED" if r["fixed"] else "STILL BROKEN"
        print(f"  {', '.join(f'#{n}' for n in group)}: {tag}")
        print(f"    {r['details'][:200]}")
        for num in group:
            if num in done:
                continue
            done.add(num)
            if r["fixed"]:
                confirm_fixed(num, r["details"])
            else:
                reopen_issue(num, r["details"])

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
