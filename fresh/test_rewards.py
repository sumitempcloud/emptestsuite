"""
Fresh E2E Test -- EMP Rewards Module via SSO
Admin (ananya@technova.in): dashboard, kudos, badges, leaderboard, challenges, celebrations, settings, budgets
Employee (priya@technova.in): give kudos, view badges/leaderboard, RBAC (cannot access settings/budgets/analytics)
Screenshots to C:/Users/Admin/screenshots/fresh_rewards/
Bugs filed to EmpCloud/EmpCloud with [Rewards] prefix.
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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ── Config ──────────────────────────────────────────────────────────
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_rewards"
LOGIN_API = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
REWARDS_BASE = "https://test-rewards.empcloud.com"
REWARDS_API = "https://test-rewards-api.empcloud.com"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_found = []
test_results = []

# ── Helpers ─────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {name}.png")
    return path


def record(name, status, details=""):
    test_results.append({"test": name, "status": status, "details": details})
    icon = {"pass": "PASS", "fail": "FAIL", "warn": "WARN"}.get(status, "INFO")
    log(f"  [{icon}] {name} -- {details}")


def file_bug(title, body):
    """File a GitHub issue with [Rewards] prefix."""
    bugs_found.append(title)
    full_title = f"[Rewards] {title}"
    log(f"  BUG: {full_title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={"title": full_title, "body": body, "labels": ["bug"]},
            timeout=15,
        )
        if resp.status_code == 201:
            url = resp.json().get("html_url", "")
            log(f"  Issue filed: {url}")
            return url
        else:
            log(f"  Failed to file issue: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log(f"  Error filing issue: {e}")
    return None


def get_sso_token(email, password, label=""):
    """Login to EmpCloud API and return an SSO/access token."""
    log(f"Getting SSO token for {email} ({label})...")
    resp = requests.post(LOGIN_API, json={"email": email, "password": password}, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        d = data.get("data", {})
        tokens = d.get("tokens", {})
        token = (
            tokens.get("access_token")
            or tokens.get("token")
            or d.get("token")
            or d.get("access_token")
            or data.get("token")
        )
        if token:
            log(f"  Token obtained (len={len(token)})")
            return token
        else:
            log(f"  Token key not found. data keys: {list(d.keys())}")
    else:
        log(f"  Login failed: {resp.status_code} {resp.text[:300]}")
    return None


def create_driver():
    opts = Options()
    opts.binary_location = CHROME_PATH
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(3)
    return driver


def wait_page(driver, timeout=12):
    time.sleep(2)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    time.sleep(1)


def is_login_page(driver):
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        return "sign in" in body and "password" in body
    except Exception:
        return False


def do_form_login(driver, email, password):
    log(f"  Attempting form login as {email}...")
    try:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        email_inp = pass_inp = None
        for inp in inputs:
            itype = (inp.get_attribute("type") or "").lower()
            iname = (inp.get_attribute("name") or "").lower()
            iph = (inp.get_attribute("placeholder") or "").lower()
            if itype == "email" or "email" in iname or "email" in iph:
                email_inp = inp
            elif itype == "password" or "password" in iname or "password" in iph:
                pass_inp = inp
        if email_inp and pass_inp:
            email_inp.clear(); email_inp.send_keys(email)
            time.sleep(0.3)
            pass_inp.clear(); pass_inp.send_keys(password)
            time.sleep(0.3)
            for btn in driver.find_elements(By.TAG_NAME, "button"):
                if any(kw in btn.text.lower() for kw in ["sign in", "login", "log in"]):
                    btn.click()
                    time.sleep(5)
                    wait_page(driver)
                    return True
            email_inp.submit()
            time.sleep(5)
            wait_page(driver)
            return True
        else:
            log(f"  Could not find email/password fields")
    except Exception as e:
        log(f"  Form login error: {e}")
    return False


def sso_login(driver, token, email, password, label=""):
    """SSO via query-param token; fallback to form login."""
    url = f"{REWARDS_BASE}?sso_token={token}"
    log(f"SSO login ({label})...")
    driver.get(url)
    wait_page(driver, timeout=15)
    time.sleep(5)
    log(f"  URL after SSO: {driver.current_url}")

    if is_login_page(driver):
        log("  Landed on login page -- trying form login...")
        do_form_login(driver, email, password)
        time.sleep(3)
        log(f"  URL after form login: {driver.current_url}")

    return driver.current_url


def check_errors(driver):
    issues = []
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        for phrase in [
            "500 internal server error", "404 not found", "something went wrong",
            "page not found", "application error", "unexpected error",
            "cannot read properties", "uncaught", "failed to fetch",
        ]:
            if phrase in body:
                issues.append(f"Error: '{phrase}'")
        if len(body.strip()) < 5:
            time.sleep(3)
            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            if len(body.strip()) < 5:
                issues.append("Page blank/empty")
    except Exception:
        pass
    return issues


def get_body(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return ""


def navigate(driver, path, email, password):
    """Navigate to a Rewards page; handle auth redirect."""
    driver.get(f"{REWARDS_BASE}{path}")
    wait_page(driver)
    if is_login_page(driver):
        do_form_login(driver, email, password)
        driver.get(f"{REWARDS_BASE}{path}")
        wait_page(driver)


# ── API Tests ───────────────────────────────────────────────────────

def api_get(token, path, name):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.get(f"{REWARDS_API}{path}", headers=headers, timeout=10)
        log(f"  GET {path}: {resp.status_code}")
        if resp.status_code in (200, 201):
            record(f"API {name}", "pass", f"{resp.status_code}")
            return resp
        elif resp.status_code == 401:
            record(f"API {name}", "fail", "401 Unauthorized")
        elif resp.status_code == 403:
            record(f"API {name}", "fail", "403 Forbidden")
        elif resp.status_code == 404:
            record(f"API {name}", "fail", "404 Not Found")
            file_bug(f"API {path} returns 404",
                     f"**Endpoint:** GET {REWARDS_API}{path}\n**Expected:** 200\n**Got:** 404\n```\n{resp.text[:500]}\n```")
        elif resp.status_code >= 500:
            record(f"API {name}", "fail", f"{resp.status_code} Server Error")
            file_bug(f"API {path} returns {resp.status_code}",
                     f"**Endpoint:** GET {REWARDS_API}{path}\n**Status:** {resp.status_code}\n```\n{resp.text[:500]}\n```")
        else:
            record(f"API {name}", "fail", f"{resp.status_code}: {resp.text[:150]}")
        return resp
    except Exception as e:
        record(f"API {name}", "fail", str(e))
        return None


def test_admin_api(token):
    log("\n=== Admin API Tests ===")
    # Health
    try:
        r = requests.get(f"{REWARDS_API}/health", timeout=10)
        log(f"  /health: {r.status_code}")
        record("API Health", "pass" if r.status_code == 200 else "fail", f"{r.status_code}")
    except Exception as e:
        record("API Health", "fail", str(e))

    endpoints = [
        ("/api/v1/kudos", "Kudos Feed"),
        ("/api/v1/kudos/received", "Received Kudos"),
        ("/api/v1/kudos/sent", "Sent Kudos"),
        ("/api/v1/points/balance", "Points Balance"),
        ("/api/v1/points/transactions", "Points Transactions"),
        ("/api/v1/badges", "Badge Definitions"),
        ("/api/v1/badges/my", "My Badges"),
        ("/api/v1/leaderboard", "Leaderboard"),
        ("/api/v1/leaderboard/my-rank", "My Rank"),
        ("/api/v1/celebrations", "Celebrations"),
        ("/api/v1/celebrations/feed", "Celebrations Feed"),
        ("/api/v1/challenges", "Challenges"),
        ("/api/v1/rewards", "Reward Catalog"),
        ("/api/v1/nominations/programs", "Nomination Programs"),
        ("/api/v1/milestones/rules", "Milestone Rules"),
        ("/api/v1/manager/dashboard", "Manager Dashboard"),
    ]
    for path, name in endpoints:
        api_get(token, path, f"Admin {name}")


def test_give_kudos_api(token, label="Admin"):
    log(f"\n=== {label}: Give Kudos via API ===")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payloads = [
        {"recipientId": 2, "message": f"Great work! (test {label})", "category": "teamwork", "points": 10, "isPublic": True},
        {"recipient_id": 2, "message": f"Great work! (test {label})", "category": "teamwork", "points": 10, "is_public": True},
    ]
    for payload in payloads:
        try:
            resp = requests.post(f"{REWARDS_API}/api/v1/kudos", headers=headers, json=payload, timeout=15)
            log(f"  POST /kudos: {resp.status_code} -- {resp.text[:300]}")
            if resp.status_code in (200, 201):
                record(f"{label} Give Kudos API", "pass", f"{resp.status_code}")
                return True
        except Exception as e:
            log(f"  Error: {e}")
    record(f"{label} Give Kudos API", "fail", "Could not send kudos")
    return False


# ── UI Page Test ────────────────────────────────────────────────────

def test_page(driver, path, page_name, ss_prefix, keywords, email, password):
    log(f"\n--- {ss_prefix} {page_name} ({path}) ---")
    navigate(driver, path, email, password)
    screenshot(driver, f"{ss_prefix}_{page_name.lower().replace(' ', '_')}")

    issues = check_errors(driver)
    body = get_body(driver)
    still_login = is_login_page(driver)
    if still_login:
        issues.append("Redirected to login (auth not persisting)")

    found_kw = [kw for kw in keywords if kw in body.lower()]
    if issues:
        record(f"{ss_prefix} {page_name}", "fail", "; ".join(issues))
        file_bug(f"{page_name} page: {'; '.join(issues)}",
                 f"**URL:** {REWARDS_BASE}{path}\n**Issues:**\n" +
                 "\n".join(f"- {i}" for i in issues) +
                 f"\n\n**Page text (first 500):**\n```\n{body[:500]}\n```")
    elif found_kw:
        record(f"{ss_prefix} {page_name}", "pass", f"Keywords: {found_kw}")
    else:
        record(f"{ss_prefix} {page_name}", "warn", f"Expected {keywords}, body: {body[:300]}")
    return body


# ── RBAC Check ──────────────────────────────────────────────────────

def test_rbac_blocked(driver, path, page_name, ss_prefix, email, password):
    """Employee should NOT be able to access this page (settings, budgets, analytics)."""
    log(f"\n--- RBAC {ss_prefix} {page_name} ({path}) ---")
    navigate(driver, path, email, password)
    screenshot(driver, f"{ss_prefix}_rbac_{page_name.lower().replace(' ', '_')}")

    body = get_body(driver).lower()
    url = driver.current_url

    # Considered blocked if: redirected away, 403 text, access denied, or no admin content rendered
    blocked_signals = [
        "access denied", "unauthorized", "forbidden", "not authorized",
        "permission", "you do not have", "403",
    ]
    redirected_away = path not in url.split("?")[0]
    has_block_text = any(sig in body for sig in blocked_signals)
    on_login = is_login_page(driver)

    if redirected_away or has_block_text or on_login:
        record(f"RBAC {page_name}", "pass", "Correctly blocked for employee")
    else:
        # Check if page actually rendered admin content
        admin_keywords = {
            "/settings": ["configuration", "category", "slack", "recognition settings"],
            "/budgets": ["budget", "allocation", "department budget"],
            "/analytics": ["analytics", "trend", "chart", "department participation"],
        }
        kws = admin_keywords.get(path, [])
        has_admin = any(kw in body for kw in kws)
        if has_admin:
            record(f"RBAC {page_name}", "fail", "Employee can access admin page!")
            file_bug(f"RBAC: Employee can access {page_name}",
                     f"**URL:** {REWARDS_BASE}{path}\n\n"
                     f"**Expected:** Access denied / redirect for employee role\n"
                     f"**Actual:** Page renders admin content\n"
                     f"**User:** {email}")
        else:
            record(f"RBAC {page_name}", "warn",
                   f"Page loaded but no admin content found. URL: {url}, body: {body[:200]}")


# ── Main ────────────────────────────────────────────────────────────

def main():
    log("=" * 70)
    log("FRESH E2E TEST -- EMP REWARDS MODULE")
    log("=" * 70)

    # ── Tokens ──
    admin_token = get_sso_token(ADMIN_EMAIL, ADMIN_PASS, "Admin")
    emp_token = get_sso_token(EMP_EMAIL, EMP_PASS, "Employee")
    if not admin_token:
        log("FATAL: No admin token. Aborting.")
        return
    if not emp_token:
        log("WARNING: No employee token. Employee tests will be skipped.")

    # ═══════════════════════════════════════════════════════════════
    # PART 1 -- ADMIN (ananya)
    # ═══════════════════════════════════════════════════════════════
    log("\n" + "=" * 70)
    log("PART 1: ADMIN TESTS (ananya@technova.in)")
    log("=" * 70)

    # 1A. Admin API
    test_admin_api(admin_token)
    test_give_kudos_api(admin_token, "Admin")

    # 1B. Admin Browser
    driver = None
    try:
        driver = create_driver()
        sso_login(driver, admin_token, ADMIN_EMAIL, ADMIN_PASS, "Admin")
        screenshot(driver, "A00_after_sso")

        if is_login_page(driver):
            record("Admin SSO Login", "fail", "Still on login page")
            file_bug("Admin SSO token not accepted",
                     "GET test-rewards.empcloud.com?sso_token=<token> shows login form instead of dashboard.")
        else:
            record("Admin SSO Login", "pass", f"URL: {driver.current_url}")

        admin_pages = [
            ("/dashboard", "Dashboard", "A01", ["kudos", "points", "recognition", "dashboard", "welcome", "send"]),
            ("/kudos", "Kudos", "A02", ["kudos", "recognition", "send", "feed"]),
            ("/badges", "Badges", "A03", ["badge", "achievement", "earned", "definition"]),
            ("/leaderboard", "Leaderboard", "A04", ["leaderboard", "rank", "top", "points"]),
            ("/challenges", "Challenges", "A05", ["challenge", "competition", "team", "active"]),
            ("/celebrations", "Celebrations", "A06", ["celebration", "birthday", "anniversary", "wish"]),
            ("/settings", "Settings", "A07", ["settings", "configuration", "category", "point"]),
            ("/budgets", "Budgets", "A08", ["budget", "allocation", "spend", "department"]),
            ("/analytics", "Analytics", "A09", ["analytics", "trend", "chart", "department"]),
            ("/feed", "Social Feed", "A10", ["feed", "kudos", "celebration"]),
            ("/rewards", "Reward Catalog", "A11", ["reward", "catalog", "redeem"]),
            ("/nominations", "Nominations", "A12", ["nomination", "program"]),
            ("/redemptions", "Redemptions", "A13", ["redemption", "approve"]),
            ("/milestones", "Milestones", "A14", ["milestone", "rule", "trigger"]),
        ]

        login_redirects = 0
        for path, name, prefix, kws in admin_pages:
            test_page(driver, path, name, prefix, kws, ADMIN_EMAIL, ADMIN_PASS)
            if is_login_page(driver):
                login_redirects += 1
                if login_redirects >= 3:
                    file_bug("Admin session not persisting across pages",
                             f"After SSO/form login, {login_redirects}+ pages redirect to login.")
                    break

        # Admin self-service pages
        for path, name, prefix, kws in [
            ("/my", "My Summary", "A20", ["point", "badge", "kudos"]),
            ("/my/kudos", "My Kudos", "A21", ["kudos", "sent", "received"]),
            ("/my/badges", "My Badges", "A22", ["badge", "earned"]),
        ]:
            test_page(driver, path, name, prefix, kws, ADMIN_EMAIL, ADMIN_PASS)

        # Give kudos via UI
        log("\n--- Admin: Give Kudos UI ---")
        navigate(driver, "/kudos", ADMIN_EMAIL, ADMIN_PASS)
        screenshot(driver, "A30_kudos_page")
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            links = driver.find_elements(By.TAG_NAME, "a")
            send_btn = None
            for el in buttons + links:
                txt = el.text.lower()
                if any(kw in txt for kw in ["send", "give", "new kudos", "recognize", "create"]):
                    send_btn = el
                    break
            if send_btn:
                send_btn.click()
                time.sleep(3)
                screenshot(driver, "A31_kudos_dialog")
                record("Admin Kudos UI button", "pass", f"Button '{send_btn.text}' found & clicked")
                # Try filling form
                for ta in driver.find_elements(By.TAG_NAME, "textarea"):
                    ph = (ta.get_attribute("placeholder") or "").lower()
                    if any(kw in ph for kw in ["message", "kudos", "write", "recognition", ""]):
                        ta.send_keys("Outstanding teamwork on the quarterly review!")
                        screenshot(driver, "A32_kudos_form")
                        break
            else:
                btn_texts = [b.text for b in buttons[:15] if b.text.strip()]
                record("Admin Kudos UI button", "warn", f"No send button. Buttons: {btn_texts}")
        except Exception as e:
            record("Admin Kudos UI", "fail", str(e))

    except Exception as e:
        log(f"ADMIN BROWSER ERROR: {e}")
        traceback.print_exc()
        if driver:
            screenshot(driver, "A_error")
    finally:
        if driver:
            driver.quit()
            log("Admin browser closed.")

    # ═══════════════════════════════════════════════════════════════
    # PART 2 -- EMPLOYEE (priya)
    # ═══════════════════════════════════════════════════════════════
    if not emp_token:
        log("\nSkipping employee tests (no token).")
    else:
        log("\n" + "=" * 70)
        log("PART 2: EMPLOYEE TESTS (priya@technova.in)")
        log("=" * 70)

        # 2A. Employee API -- Give kudos
        test_give_kudos_api(emp_token, "Employee")

        # 2B. Employee Browser
        driver = None
        try:
            driver = create_driver()
            sso_login(driver, emp_token, EMP_EMAIL, EMP_PASS, "Employee")
            screenshot(driver, "E00_after_sso")

            if is_login_page(driver):
                record("Employee SSO Login", "fail", "Still on login page")
            else:
                record("Employee SSO Login", "pass", f"URL: {driver.current_url}")

            # Employee accessible pages
            emp_pages = [
                ("/my", "My Summary", "E01", ["point", "badge", "kudos"]),
                ("/my/kudos", "My Kudos", "E02", ["kudos", "sent", "received"]),
                ("/my/badges", "My Badges", "E03", ["badge", "earned"]),
                ("/my/rewards", "My Rewards", "E04", ["reward", "catalog", "redeem"]),
                ("/my/redemptions", "My Redemptions", "E05", ["redemption", "status"]),
                ("/my/notifications", "Notifications", "E06", ["notification"]),
                ("/leaderboard", "Leaderboard", "E07", ["leaderboard", "rank", "top"]),
                ("/badges", "Badges View", "E08", ["badge", "achievement"]),
                ("/feed", "Social Feed", "E09", ["feed", "kudos"]),
                ("/celebrations", "Celebrations", "E10", ["celebration", "birthday", "anniversary"]),
                ("/challenges", "Challenges", "E11", ["challenge", "team"]),
                ("/dashboard", "Dashboard", "E12", ["kudos", "points", "dashboard"]),
            ]
            for path, name, prefix, kws in emp_pages:
                test_page(driver, path, name, prefix, kws, EMP_EMAIL, EMP_PASS)

            # Employee give kudos UI
            log("\n--- Employee: Give Kudos UI ---")
            navigate(driver, "/my/kudos", EMP_EMAIL, EMP_PASS)
            screenshot(driver, "E20_my_kudos")
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                links = driver.find_elements(By.TAG_NAME, "a")
                send_btn = None
                for el in buttons + links:
                    txt = el.text.lower()
                    if any(kw in txt for kw in ["send", "give", "new kudos", "recognize", "create"]):
                        send_btn = el
                        break
                if send_btn:
                    send_btn.click()
                    time.sleep(3)
                    screenshot(driver, "E21_kudos_dialog")
                    record("Employee Kudos UI button", "pass", f"Button '{send_btn.text}' found")
                else:
                    # Try from /kudos page too
                    navigate(driver, "/kudos", EMP_EMAIL, EMP_PASS)
                    for el in driver.find_elements(By.TAG_NAME, "button") + driver.find_elements(By.TAG_NAME, "a"):
                        txt = el.text.lower()
                        if any(kw in txt for kw in ["send", "give", "new kudos", "recognize", "create"]):
                            send_btn = el
                            break
                    if send_btn:
                        send_btn.click()
                        time.sleep(3)
                        screenshot(driver, "E21_kudos_dialog")
                        record("Employee Kudos UI button", "pass", f"Button '{send_btn.text}' found on /kudos")
                    else:
                        btn_texts = [b.text for b in buttons[:15] if b.text.strip()]
                        record("Employee Kudos UI button", "warn", f"No send button. Buttons: {btn_texts}")
            except Exception as e:
                record("Employee Kudos UI", "fail", str(e))

            # ── RBAC: Employee must NOT access these admin pages ──
            log("\n--- RBAC: Employee blocked from admin pages ---")
            rbac_pages = [
                ("/settings", "Settings"),
                ("/budgets", "Budgets"),
                ("/analytics", "Analytics"),
            ]
            for path, name in rbac_pages:
                test_rbac_blocked(driver, path, name, "E_RBAC", EMP_EMAIL, EMP_PASS)

        except Exception as e:
            log(f"EMPLOYEE BROWSER ERROR: {e}")
            traceback.print_exc()
            if driver:
                screenshot(driver, "E_error")
        finally:
            if driver:
                driver.quit()
                log("Employee browser closed.")

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)
    passed = sum(1 for t in test_results if t["status"] == "pass")
    failed = sum(1 for t in test_results if t["status"] == "fail")
    warned = sum(1 for t in test_results if t["status"] == "warn")
    log(f"Total: {len(test_results)} | PASS: {passed} | FAIL: {failed} | WARN: {warned}")
    log(f"Bugs filed: {len(bugs_found)}")

    if failed:
        log("\nFAILED:")
        for t in test_results:
            if t["status"] == "fail":
                log(f"  X {t['test']}: {t['details'][:150]}")
    if warned:
        log("\nWARNINGS:")
        for t in test_results:
            if t["status"] == "warn":
                log(f"  ! {t['test']}: {t['details'][:150]}")
    if bugs_found:
        log("\nBUGS FILED:")
        for b in bugs_found:
            log(f"  - [Rewards] {b}")

    # Write JSON results
    results_path = os.path.join(SCREENSHOT_DIR, "results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({"tests": test_results, "bugs": bugs_found,
                    "summary": {"total": len(test_results), "pass": passed, "fail": failed, "warn": warned}},
                   f, indent=2)
    log(f"\nResults written to {results_path}")
    log("Done.")


if __name__ == "__main__":
    main()
