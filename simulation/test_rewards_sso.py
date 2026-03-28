"""
Thorough testing of the EMP Rewards module via SSO.
Tests: dashboard, kudos, badges, leaderboard, challenges, celebrations, catalog, settings,
       give kudos, check points balance, check badges.
Screenshots every page. Files bugs with [Rewards] prefix on EmpCloud/EmpCloud repo.
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
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# -- Config --
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_rewards"
LOGIN_API = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
REWARDS_BASE = "https://test-rewards.empcloud.com"
REWARDS_API = "https://test-rewards-api.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_found = []
test_results = []


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {name}.png")
    return path


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
                "Accept": "application/vnd.github.v3+json"
            },
            json={"title": full_title, "body": body, "labels": ["bug"]},
            timeout=15
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


def record_test(name, status, details=""):
    test_results.append({"test": name, "status": status, "details": details})
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
    log(f"  [{icon}] {name} - {details}")


def get_sso_token():
    """Login to EmpCloud API and get SSO token."""
    log("Logging in to get SSO token...")
    resp = requests.post(LOGIN_API, json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        d = data.get("data", {})
        tokens = d.get("tokens", {})
        token = (tokens.get("access_token") or tokens.get("token")
                 or d.get("token") or d.get("access_token") or data.get("token"))
        if token:
            log(f"  SSO token obtained (len={len(token)})")
            return token
        else:
            log(f"  Token not found. Response keys: {list(data.keys())}")
            if "data" in data and isinstance(data["data"], dict):
                log(f"    data keys: {list(data['data'].keys())}")
    else:
        log(f"  Login failed: {resp.status_code} {resp.text[:300]}")
    return None


def create_driver():
    """Create headless Chrome driver."""
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


def wait_for_page(driver, timeout=12):
    """Wait for page to settle."""
    time.sleep(2)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except:
        pass
    time.sleep(1)


def extract_local_storage_token(driver):
    """Extract auth token from localStorage after SSO."""
    try:
        keys_script = """
        var keys = [];
        for (var i = 0; i < localStorage.length; i++) {
            var key = localStorage.key(i);
            keys.push(key + ' = ' + localStorage.getItem(key).substring(0, 100));
        }
        return keys;
        """
        items = driver.execute_script(keys_script)
        log(f"  localStorage entries ({len(items)}):")
        for item in items:
            log(f"    {item}")

        # Try common token keys
        for key in ["token", "access_token", "auth_token", "sso_token",
                     "rewards_token", "jwt", "authToken", "accessToken",
                     "emp_token", "user_token"]:
            val = driver.execute_script(f"return localStorage.getItem('{key}')")
            if val:
                log(f"  Found token in localStorage['{key}'] (len={len(val)})")
                return val

        # Check for JSON objects that might contain tokens
        for key_name in ["auth", "user", "session", "state", "persist:root",
                         "persist:auth", "rewards-auth", "emp-auth"]:
            val = driver.execute_script(f"return localStorage.getItem('{key_name}')")
            if val:
                try:
                    obj = json.loads(val)
                    for tk in ["token", "access_token", "accessToken", "jwt"]:
                        if tk in obj:
                            log(f"  Found token in localStorage['{key_name}'].{tk}")
                            return obj[tk]
                except:
                    pass
    except Exception as e:
        log(f"  Error extracting localStorage: {e}")
    return None


def extract_cookies(driver):
    """Extract and log all cookies."""
    try:
        cookies = driver.get_cookies()
        log(f"  Cookies ({len(cookies)}):")
        for c in cookies:
            log(f"    {c['name']} = {str(c['value'])[:80]} (domain={c.get('domain','')})")
        return cookies
    except Exception as e:
        log(f"  Error getting cookies: {e}")
        return []


def inject_token_and_navigate(driver, token, path):
    """Set token in localStorage and navigate to page."""
    # First ensure we're on the rewards domain
    if "test-rewards.empcloud.com" not in driver.current_url:
        driver.get(REWARDS_BASE)
        wait_for_page(driver)

    # Inject token into localStorage with various key names
    driver.execute_script(f"""
        localStorage.setItem('token', '{token}');
        localStorage.setItem('access_token', '{token}');
        localStorage.setItem('authToken', '{token}');
        localStorage.setItem('sso_token', '{token}');
    """)

    driver.get(f"{REWARDS_BASE}{path}")
    wait_for_page(driver)


def check_page_errors(driver, page_name):
    """Check for visible error indicators on the page."""
    issues = []
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        error_phrases = [
            "500 internal server error", "404 not found", "something went wrong",
            "page not found", "application error", "unexpected error",
            "cannot read properties", "uncaught", "failed to fetch"
        ]
        for phrase in error_phrases:
            if phrase in body_text:
                issues.append(f"Error text found: '{phrase}'")
    except:
        pass

    try:
        body = driver.find_element(By.TAG_NAME, "body")
        if len(body.text.strip()) < 5:
            time.sleep(3)
            body = driver.find_element(By.TAG_NAME, "body")
            if len(body.text.strip()) < 5:
                issues.append("Page appears blank or empty")
    except:
        pass

    return issues


def is_on_login_page(driver):
    """Check if we're stuck on the login page."""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        return "sign in" in body and "email address" in body and "password" in body
    except:
        return False


def do_form_login(driver):
    """If stuck on login page, try filling in credentials and submitting."""
    log("  Attempting form-based login...")
    try:
        # Find email and password fields
        inputs = driver.find_elements(By.TAG_NAME, "input")
        email_input = None
        pass_input = None
        for inp in inputs:
            inp_type = inp.get_attribute("type") or ""
            inp_name = (inp.get_attribute("name") or "").lower()
            inp_placeholder = (inp.get_attribute("placeholder") or "").lower()
            if inp_type == "email" or "email" in inp_name or "email" in inp_placeholder:
                email_input = inp
            elif inp_type == "password" or "password" in inp_name or "password" in inp_placeholder:
                pass_input = inp

        if email_input and pass_input:
            email_input.clear()
            email_input.send_keys(EMAIL)
            time.sleep(0.5)
            pass_input.clear()
            pass_input.send_keys(PASSWORD)
            time.sleep(0.5)

            # Find submit button
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if "sign in" in btn.text.lower() or "login" in btn.text.lower():
                    btn.click()
                    log("  Clicked sign-in button")
                    time.sleep(5)
                    wait_for_page(driver)
                    return True

            # Try submitting the form
            email_input.submit()
            time.sleep(5)
            wait_for_page(driver)
            return True
        else:
            log(f"  Could not find email/password fields. Inputs: {len(inputs)}")
    except Exception as e:
        log(f"  Form login error: {e}")
    return False


def sso_login(driver, token):
    """Perform SSO login via URL with token, handle fallback to form login."""
    url = f"{REWARDS_BASE}?sso_token={token}"
    log(f"SSO login to Rewards module...")
    driver.get(url)
    wait_for_page(driver, timeout=15)
    time.sleep(5)  # Extra wait for SSO processing

    current_url = driver.current_url
    log(f"  After SSO, URL: {current_url}")

    # Check if SSO worked
    if is_on_login_page(driver):
        log("  SSO landed on login page. Trying form login...")
        do_form_login(driver)
        time.sleep(3)
        current_url = driver.current_url
        log(f"  After form login, URL: {current_url}")

    # Extract token from localStorage/cookies for API use
    rewards_token = extract_local_storage_token(driver)
    extract_cookies(driver)

    return current_url, rewards_token


def test_page(driver, token, path, page_name, screenshot_name, expected_keywords):
    """Navigate to page, screenshot, check for errors/content. Uses token injection if needed."""
    log(f"\n=== Testing {page_name} ({path}) ===")

    driver.get(f"{REWARDS_BASE}{path}")
    wait_for_page(driver)

    # If on login page, try form login
    if is_on_login_page(driver):
        log(f"  Redirected to login for {path}, trying form login...")
        do_form_login(driver)
        # After login, navigate to desired page
        driver.get(f"{REWARDS_BASE}{path}")
        wait_for_page(driver)

    screenshot(driver, screenshot_name)

    issues = check_page_errors(driver, page_name)
    body_text = driver.find_element(By.TAG_NAME, "body").text
    found_kw = [kw for kw in expected_keywords if kw in body_text.lower()]

    still_on_login = is_on_login_page(driver)
    if still_on_login:
        issues.append("Redirected to login page (auth not persisting)")

    if issues:
        record_test(f"{page_name} page loads", "fail", "; ".join(issues))
        file_bug(f"{page_name} page: {'; '.join(issues)}",
                 f"**URL:** {REWARDS_BASE}{path}\n\n**Issues:**\n" +
                 "\n".join(f"- {i}" for i in issues) +
                 f"\n\n**Page text (first 500 chars):**\n```\n{body_text[:500]}\n```")
    elif len(found_kw) >= 1:
        record_test(f"{page_name} page loads", "pass", f"Found: {found_kw}")
    else:
        record_test(f"{page_name} page loads", "warn",
                     f"Expected keywords {expected_keywords} not found. Body: {body_text[:300]}")
    return body_text


def test_api_endpoints(token):
    """Test key API endpoints. Try both EmpCloud token and check for Rewards-specific auth."""
    log("\n=== Testing API Endpoints ===")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # First check health
    try:
        resp = requests.get(f"{REWARDS_API}/health", timeout=10)
        log(f"  GET /health: {resp.status_code} - {resp.text[:200]}")
        if resp.status_code == 200:
            record_test("API: Health", "pass", "Server is running")
        else:
            record_test("API: Health", "fail", f"Status {resp.status_code}")
    except Exception as e:
        record_test("API: Health", "fail", str(e))

    endpoints = [
        ("GET", "/api/v1/kudos", "Kudos Feed"),
        ("GET", "/api/v1/kudos/received", "Received Kudos"),
        ("GET", "/api/v1/kudos/sent", "Sent Kudos"),
        ("GET", "/api/v1/points/balance", "Points Balance"),
        ("GET", "/api/v1/points/transactions", "Points Transactions"),
        ("GET", "/api/v1/badges", "Badge Definitions"),
        ("GET", "/api/v1/badges/my", "My Badges"),
        ("GET", "/api/v1/leaderboard", "Leaderboard"),
        ("GET", "/api/v1/leaderboard/my-rank", "My Rank"),
        ("GET", "/api/v1/celebrations", "Celebrations"),
        ("GET", "/api/v1/celebrations/feed", "Celebrations Feed"),
        ("GET", "/api/v1/challenges", "Challenges"),
        ("GET", "/api/v1/rewards", "Reward Catalog"),
        ("GET", "/api/v1/nominations/programs", "Nomination Programs"),
        ("GET", "/api/v1/milestones/rules", "Milestone Rules"),
        ("GET", "/api/v1/milestones/history", "Milestone History"),
        ("GET", "/api/v1/manager/dashboard", "Manager Dashboard"),
        ("GET", "/api/v1/manager/team-comparison", "Manager Team Comparison"),
        ("GET", "/api/v1/manager/recommendations", "Manager Recommendations"),
    ]

    for method, path, name in endpoints:
        try:
            url = f"{REWARDS_API}{path}"
            resp = requests.get(url, headers=headers, timeout=10)
            log(f"  {method} {path}: {resp.status_code}")
            if resp.status_code in [200, 201]:
                record_test(f"API: {name}", "pass", f"Status {resp.status_code}")
                # Log first bit of data for key endpoints
                if name in ["Points Balance", "Kudos Feed", "Leaderboard", "My Badges"]:
                    log(f"    Data: {resp.text[:250]}")
            elif resp.status_code == 401:
                record_test(f"API: {name}", "fail", f"401 Unauthorized - token not accepted by Rewards API")
            elif resp.status_code == 404:
                record_test(f"API: {name}", "fail", f"404 Not Found")
                file_bug(f"API endpoint {path} returns 404",
                         f"**Endpoint:** {method} {REWARDS_API}{path}\n\n"
                         f"**Expected:** 200 OK\n**Got:** 404\n**Response:**\n```\n{resp.text[:500]}\n```")
            elif resp.status_code >= 500:
                record_test(f"API: {name}", "fail", f"Status {resp.status_code}")
                file_bug(f"API endpoint {path} returns {resp.status_code} server error",
                         f"**Endpoint:** {method} {REWARDS_API}{path}\n\n"
                         f"**Status:** {resp.status_code}\n**Response:**\n```\n{resp.text[:500]}\n```")
            else:
                record_test(f"API: {name}", "fail", f"Status {resp.status_code}: {resp.text[:150]}")
        except Exception as e:
            record_test(f"API: {name}", "fail", str(e))

    return headers


def test_give_kudos_api(token):
    """Test giving kudos via API."""
    log("\n=== Testing: Give Kudos via API ===")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payloads = [
        {
            "recipientId": 2,
            "message": "Great work on the Q1 report! Thorough analysis.",
            "category": "teamwork",
            "points": 10,
            "isPublic": True
        },
        {
            "recipient_id": 2,
            "message": "Great work on the Q1 report! Thorough analysis.",
            "category": "teamwork",
            "points": 10,
            "is_public": True
        },
    ]

    for payload in payloads:
        try:
            resp = requests.post(f"{REWARDS_API}/api/v1/kudos", headers=headers,
                                json=payload, timeout=15)
            log(f"  POST /kudos: {resp.status_code} - {resp.text[:300]}")
            if resp.status_code in [200, 201]:
                record_test("Give Kudos API", "pass", f"Status {resp.status_code}")
                return True
        except Exception as e:
            log(f"  Error: {e}")

    record_test("Give Kudos API", "fail", "Could not send kudos (401 or other error)")
    return False


def test_give_kudos_ui(driver):
    """Test giving kudos via the UI."""
    log("\n=== Testing: Give Kudos via UI ===")
    try:
        driver.get(f"{REWARDS_BASE}/kudos")
        wait_for_page(driver)

        if is_on_login_page(driver):
            do_form_login(driver)
            driver.get(f"{REWARDS_BASE}/kudos")
            wait_for_page(driver)

        screenshot(driver, "09_kudos_give_attempt")
        body_text = driver.find_element(By.TAG_NAME, "body").text

        # Look for send/give kudos button
        buttons = driver.find_elements(By.TAG_NAME, "button")
        links = driver.find_elements(By.TAG_NAME, "a")
        all_clickables = buttons + links
        send_btn = None
        for el in all_clickables:
            txt = el.text.lower()
            if any(kw in txt for kw in ["send", "give", "new kudos", "recognize", "create"]):
                send_btn = el
                log(f"  Found button: '{el.text}'")
                break

        if send_btn:
            try:
                send_btn.click()
                time.sleep(3)
                screenshot(driver, "09b_kudos_dialog")
                record_test("Kudos UI - Send button", "pass", f"Button '{send_btn.text}' clickable")

                # Try to fill in the kudos form
                inputs = driver.find_elements(By.TAG_NAME, "input")
                textareas = driver.find_elements(By.TAG_NAME, "textarea")
                log(f"  Form has {len(inputs)} inputs, {len(textareas)} textareas")

                # Fill message if textarea found
                for ta in textareas:
                    placeholder = ta.get_attribute("placeholder") or ""
                    if any(kw in placeholder.lower() for kw in ["message", "kudos", "recognition", "write"]):
                        ta.send_keys("Excellent teamwork on the project!")
                        log(f"  Filled message textarea")
                        break

                screenshot(driver, "09c_kudos_form_filled")
            except Exception as e:
                record_test("Kudos UI - Send button", "warn", f"Click failed: {e}")
        else:
            btn_texts = [b.text for b in buttons[:20] if b.text.strip()]
            record_test("Kudos UI - Send button", "warn", f"No send button found. Buttons: {btn_texts}")
    except Exception as e:
        record_test("Kudos UI", "fail", str(e))


def test_points_balance_ui(driver):
    """Check points balance on UI."""
    log("\n=== Testing: Points Balance UI ===")
    try:
        # Try dashboard first (often shows points)
        driver.get(f"{REWARDS_BASE}/dashboard")
        wait_for_page(driver)
        if is_on_login_page(driver):
            do_form_login(driver)
            driver.get(f"{REWARDS_BASE}/dashboard")
            wait_for_page(driver)

        body = driver.find_element(By.TAG_NAME, "body").text
        screenshot(driver, "10_points_dashboard")
        if any(kw in body.lower() for kw in ["point", "balance", "earned", "redeemable"]):
            record_test("Points Balance UI (dashboard)", "pass", "Points info visible")
        else:
            record_test("Points Balance UI (dashboard)", "warn",
                         f"No points keywords on dashboard. Body: {body[:300]}")

        # Try /my page
        driver.get(f"{REWARDS_BASE}/my")
        wait_for_page(driver)
        if is_on_login_page(driver):
            do_form_login(driver)
            driver.get(f"{REWARDS_BASE}/my")
            wait_for_page(driver)

        body = driver.find_element(By.TAG_NAME, "body").text
        screenshot(driver, "10b_my_summary")
        issues = check_page_errors(driver, "My Summary")
        if issues:
            record_test("My Summary page", "fail", "; ".join(issues))
        elif any(kw in body.lower() for kw in ["point", "badge", "kudos", "summary"]):
            record_test("My Summary page", "pass", "Content found")
        else:
            record_test("My Summary page", "warn", f"Body: {body[:300]}")
    except Exception as e:
        record_test("Points Balance UI", "fail", str(e))


def test_badges_ui(driver):
    """Check badges on UI."""
    log("\n=== Testing: Badges UI ===")
    try:
        driver.get(f"{REWARDS_BASE}/badges")
        wait_for_page(driver)
        if is_on_login_page(driver):
            do_form_login(driver)
            driver.get(f"{REWARDS_BASE}/badges")
            wait_for_page(driver)

        screenshot(driver, "11_badges_page")
        body = driver.find_element(By.TAG_NAME, "body").text
        if any(kw in body.lower() for kw in ["badge", "achievement", "earned", "award"]):
            record_test("Badges page content", "pass", "Badge content visible")
        else:
            record_test("Badges page content", "warn", f"Body: {body[:300]}")

        # My badges
        driver.get(f"{REWARDS_BASE}/my/badges")
        wait_for_page(driver)
        if is_on_login_page(driver):
            do_form_login(driver)
            driver.get(f"{REWARDS_BASE}/my/badges")
            wait_for_page(driver)

        screenshot(driver, "11b_my_badges")
        body = driver.find_element(By.TAG_NAME, "body").text
        issues = check_page_errors(driver, "My Badges")
        if issues:
            record_test("My Badges page", "fail", "; ".join(issues))
        else:
            record_test("My Badges page", "pass" if "badge" in body.lower() else "warn",
                         f"Body: {body[:200]}")
    except Exception as e:
        record_test("Badges UI", "fail", str(e))


def main():
    log("=" * 60)
    log("EMP REWARDS MODULE - THOROUGH SSO TESTING")
    log("=" * 60)

    # Step 1: Get SSO token
    token = get_sso_token()
    if not token:
        log("FATAL: Could not obtain SSO token. Aborting.")
        return

    # Step 2: Test API endpoints
    test_api_endpoints(token)

    # Step 3: Test Give Kudos via API
    test_give_kudos_api(token)

    # Step 4: Browser-based tests
    driver = None
    rewards_token = None
    try:
        driver = create_driver()

        # SSO Login
        final_url, rewards_token = sso_login(driver, token)
        screenshot(driver, "00_after_sso")

        if is_on_login_page(driver):
            record_test("SSO Login", "fail", f"Still on login page after SSO + form login")
            file_bug("SSO token not accepted - falls back to login page",
                     f"**Steps:**\n1. GET {REWARDS_BASE}?sso_token=<valid_token>\n\n"
                     f"**Expected:** Auto-login and redirect to dashboard\n"
                     f"**Actual:** Shows login form\n\n"
                     f"The SSO token from EmpCloud API is not being processed by the Rewards module frontend.")
        else:
            record_test("SSO Login", "pass", f"Landed on: {final_url}")

        # If we got a rewards-specific token, re-test API with it
        if rewards_token and rewards_token != token:
            log(f"\n  Found Rewards-specific token, re-testing API...")
            test_api_endpoints(rewards_token)

        # Test all main pages
        pages_to_test = [
            ("/dashboard", "Dashboard", "01_dashboard",
             ["kudos", "points", "recognition", "badge", "recent", "send", "welcome", "dashboard"]),
            ("/kudos", "Kudos", "02_kudos",
             ["kudos", "recognition", "send", "received", "sent", "feed"]),
            ("/badges", "Badges", "03_badges",
             ["badge", "achievement", "earned", "award", "definition"]),
            ("/leaderboard", "Leaderboard", "04_leaderboard",
             ["leaderboard", "rank", "top", "points", "recognition"]),
            ("/challenges", "Challenges", "05_challenges",
             ["challenge", "competition", "team", "active", "participate"]),
            ("/celebrations", "Celebrations", "06_celebrations",
             ["celebration", "birthday", "anniversary", "wish", "upcoming"]),
            ("/rewards", "Reward Catalog", "07_catalog",
             ["reward", "catalog", "points", "redeem", "gift"]),
            ("/settings", "Settings", "08_settings",
             ["settings", "configuration", "category", "point", "slack", "teams"]),
            ("/feed", "Social Feed", "12_feed",
             ["feed", "kudos", "celebration", "recognition", "recent"]),
            ("/analytics", "Analytics", "13_analytics",
             ["analytics", "trend", "chart", "department", "recognition"]),
            ("/nominations", "Nominations", "14_nominations",
             ["nomination", "program", "employee"]),
            ("/redemptions", "Redemptions", "15_redemptions",
             ["redemption", "reward", "status", "approve"]),
            ("/budgets", "Budgets", "16_budgets",
             ["budget", "allocation", "spend", "department"]),
            ("/milestones", "Milestones", "17_milestones",
             ["milestone", "rule", "trigger", "anniversary", "automated"]),
        ]

        # Track if auth is persisting
        login_redirect_count = 0

        for path, name, ss_name, keywords in pages_to_test:
            test_page(driver, token, path, name, ss_name, keywords)
            if is_on_login_page(driver):
                login_redirect_count += 1
                if login_redirect_count >= 3:
                    # Auth clearly not persisting, file one consolidated bug
                    break

        if login_redirect_count >= 3:
            log(f"\n  Auth not persisting across pages ({login_redirect_count} redirects to login)")
            file_bug("Session not persisting - protected pages redirect to login",
                     f"**Steps:**\n1. SSO login via ?sso_token= or form login\n"
                     f"2. Navigate to any protected page (e.g., /kudos, /badges, /settings)\n\n"
                     f"**Expected:** Pages load with authenticated content\n"
                     f"**Actual:** Pages redirect to login form\n\n"
                     f"Affected pages: {login_redirect_count}+ pages tested.\n"
                     f"Session/auth token does not persist across navigation.")

        # Self-service pages
        self_service_pages = [
            ("/my", "My Summary", "20_my_summary",
             ["point", "badge", "kudos", "summary"]),
            ("/my/kudos", "My Kudos", "21_my_kudos",
             ["kudos", "sent", "received", "send"]),
            ("/my/badges", "My Badges", "22_my_badges",
             ["badge", "earned", "progress"]),
            ("/my/rewards", "My Rewards", "23_my_rewards",
             ["reward", "catalog", "redeem"]),
            ("/my/redemptions", "My Redemptions", "24_my_redemptions",
             ["redemption", "status"]),
            ("/my/notifications", "My Notifications", "25_my_notifications",
             ["notification"]),
        ]

        for path, name, ss_name, keywords in self_service_pages:
            test_page(driver, token, path, name, ss_name, keywords)

        # Functional UI tests
        test_give_kudos_ui(driver)
        test_points_balance_ui(driver)
        test_badges_ui(driver)

    except Exception as e:
        log(f"BROWSER ERROR: {e}")
        traceback.print_exc()
        if driver:
            screenshot(driver, "error_state")
    finally:
        if driver:
            driver.quit()
            log("Browser closed.")

    # Summary
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    passed = sum(1 for t in test_results if t["status"] == "pass")
    failed = sum(1 for t in test_results if t["status"] == "fail")
    warned = sum(1 for t in test_results if t["status"] == "warn")
    log(f"Total: {len(test_results)} | PASS: {passed} | FAIL: {failed} | WARN: {warned}")
    log(f"Bugs filed: {len(bugs_found)}")

    if failed > 0:
        log("\nFAILED TESTS:")
        for t in test_results:
            if t["status"] == "fail":
                log(f"  X {t['test']}: {t['details'][:150]}")

    if warned > 0:
        log("\nWARNINGS:")
        for t in test_results:
            if t["status"] == "warn":
                log(f"  ! {t['test']}: {t['details'][:150]}")

    if bugs_found:
        log("\nBUGS FILED:")
        for b in bugs_found:
            log(f"  - [Rewards] {b}")

    log("\nDone.")


if __name__ == "__main__":
    main()
