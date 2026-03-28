"""
Explore SSO mechanism for all EmpCloud modules:
Performance, Rewards, Exit, Recruit, LMS

Key finding from Phase 1: SSO links with ?sso_token=<JWT> are on the DASHBOARD (root /),
not the /modules page. The dashboard loads module data via:
  - GET /api/v1/modules
  - GET /api/v1/subscriptions
Then renders <a> links with SSO tokens embedded in href.

This script:
1. Logs in -> dashboard -> finds SSO links -> decodes JWT
2. Clicks each module's SSO link -> screenshots the result
3. Checks direct access without SSO token
4. Calls the /api/v1/modules and /api/v1/subscriptions APIs directly
5. Full network capture of the SSO flow
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import base64
import traceback
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "https://test-empcloud.empcloud.com"
LOGIN_EMAIL = "ananya@technova.in"
LOGIN_PASSWORD = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_explore_all_modules"

MODULES = {
    "Performance": {"subdomain": "https://test-performance.empcloud.com"},
    "Rewards":     {"subdomain": "https://test-rewards.empcloud.com"},
    "Exit":        {"subdomain": "https://test-exit.empcloud.com"},
    "Recruit":     {"subdomain": "https://test-recruit.empcloud.com"},
    "LMS":         {"subdomain": "https://testlms.empcloud.com"},
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
step = [0]

def decode_jwt(token):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        hdr = parts[0] + "=" * (4 - len(parts[0]) % 4)
        pay = parts[1] + "=" * (4 - len(parts[1]) % 4)
        header = json.loads(base64.urlsafe_b64decode(hdr))
        payload = json.loads(base64.urlsafe_b64decode(pay))
        return {"header": header, "payload": payload}
    except Exception as e:
        return {"error": str(e)}


def make_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--ignore-certificate-errors")
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"})
    driver = webdriver.Chrome(service=Service(), options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(3)
    return driver


def ss(driver, name):
    step[0] += 1
    safe = name.replace(" ", "_").replace("/", "_").replace(":", "_")
    path = os.path.join(SCREENSHOT_DIR, f"{step[0]:02d}_{safe}.png")
    driver.save_screenshot(path)
    print(f"  [SS] {path}")
    return path


def login(driver):
    driver.get(BASE_URL + "/login")
    time.sleep(3)
    ss(driver, "login_page")

    email_input = None
    for sel in ["input[name='email']", "input[type='email']", "#email"]:
        try:
            email_input = driver.find_element(By.CSS_SELECTOR, sel)
            if email_input: break
        except:
            pass
    if not email_input:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        if inputs: email_input = inputs[0]

    email_input.clear()
    email_input.send_keys(LOGIN_EMAIL)
    pwd = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pwd.clear()
    pwd.send_keys(LOGIN_PASSWORD)

    btns = driver.find_elements(By.TAG_NAME, "button")
    for b in btns:
        if any(w in b.text.lower() for w in ["login", "sign in"]):
            b.click()
            break
    else:
        if btns: btns[-1].click()

    time.sleep(5)
    ss(driver, "after_login_dashboard")
    print(f"  Logged in -> {driver.current_url}")


def extract_sso_links(driver):
    """Extract all SSO links from current page."""
    sso_links = {}
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        href = link.get_attribute("href") or ""
        text = link.text.strip()
        if "sso_token=" in href:
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            token = params.get("sso_token", [""])[0]
            domain = f"{parsed.scheme}://{parsed.netloc}"
            for mod_name, mod_info in MODULES.items():
                if mod_info["subdomain"].rstrip("/") == domain.rstrip("/"):
                    if mod_name not in sso_links or text == "Launch":
                        sso_links[mod_name] = {
                            "url": href,
                            "token": token,
                            "text": text,
                            "domain": domain,
                        }
    return sso_links


def main():
    start = datetime.now()
    print(f"SSO Module Exploration - {start}")
    print(f"Screenshots: {SCREENSHOT_DIR}\n")

    driver = make_driver()

    try:
        # ============================================================
        # STEP 1: Login
        # ============================================================
        print("=" * 70)
        print("STEP 1: Login to EmpCloud")
        print("=" * 70)
        login(driver)

        # ============================================================
        # STEP 2: Read auth token from localStorage
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 2: Auth token in localStorage")
        print("=" * 70)

        storage_raw = driver.execute_script("return localStorage.getItem('empcloud-auth');")
        if storage_raw:
            auth_data = json.loads(storage_raw)
            access_token = auth_data.get("state", {}).get("accessToken", "")
            refresh_token = auth_data.get("state", {}).get("refreshToken", "")

            print(f"\n  localStorage key: 'empcloud-auth'")
            print(f"  accessToken present: {bool(access_token)} (len={len(access_token)})")
            print(f"  refreshToken present: {bool(refresh_token)}")

            if access_token:
                decoded = decode_jwt(access_token)
                print(f"\n  Auth JWT Header: {json.dumps(decoded.get('header', {}), indent=4)}")
                print(f"  Auth JWT Payload: {json.dumps(decoded.get('payload', {}), indent=4)}")
        else:
            print("  No empcloud-auth in localStorage!")

        # ============================================================
        # STEP 3: Dashboard - find SSO links
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 3: Dashboard SSO links")
        print("=" * 70)

        # The dashboard (root /) has module cards with SSO links
        driver.get(BASE_URL + "/")
        time.sleep(5)
        ss(driver, "dashboard_full")

        sso_links = extract_sso_links(driver)
        print(f"\n  Found {len(sso_links)} SSO links on dashboard:")
        for mod, info in sso_links.items():
            print(f"    {mod}: [{info['text']}] -> {info['domain']}/?sso_token=<JWT>")

        # Decode one SSO token
        if sso_links:
            first = list(sso_links.values())[0]
            decoded = decode_jwt(first["token"])
            print(f"\n  SSO JWT Header: {json.dumps(decoded.get('header', {}), indent=4)}")
            print(f"  SSO JWT Payload: {json.dumps(decoded.get('payload', {}), indent=4)}")

        # ============================================================
        # STEP 4: /modules page
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 4: /modules page (dedicated modules view)")
        print("=" * 70)

        driver.get(BASE_URL + "/modules")
        time.sleep(4)
        ss(driver, "modules_page")

        modules_sso = extract_sso_links(driver)
        if modules_sso:
            print(f"  Found {len(modules_sso)} SSO links on /modules page")
            for mod, info in modules_sso.items():
                print(f"    {mod}: [{info['text']}]")
        else:
            print("  /modules page has NO SSO links (it shows subscription management, not launch links)")

        # Get /modules page HTML structure
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text[:2000]
            print(f"\n  /modules page content preview:\n{body_text[:1000]}")
        except:
            pass

        # ============================================================
        # STEP 5: Call /api/v1/modules and /api/v1/subscriptions
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 5: API calls that generate SSO data")
        print("=" * 70)

        # Use same-origin API (the frontend proxy)
        api_endpoints = [
            "/api/v1/modules",
            "/api/v1/subscriptions",
            "/api/v1/modules/sso",
            "/api/v1/sso/token",
        ]

        for ep in api_endpoints:
            try:
                result = driver.execute_script(f"""
                    try {{
                        const resp = await fetch("{BASE_URL}{ep}", {{
                            method: 'GET',
                            headers: {{ 'Content-Type': 'application/json' }},
                            credentials: 'include'
                        }});
                        const text = await resp.text();
                        return JSON.stringify({{status: resp.status, body: text.substring(0, 5000)}});
                    }} catch(e) {{
                        return JSON.stringify({{error: e.message}});
                    }}
                """)
                resp = json.loads(result)
                status = resp.get("status", "error")
                body = resp.get("body", resp.get("error", ""))

                if status == 200:
                    print(f"\n  [200] GET {ep}")
                    try:
                        parsed = json.loads(body)
                        formatted = json.dumps(parsed, indent=2)
                        # Print first 2000 chars
                        print(f"  Response ({len(formatted)} chars):")
                        for line in formatted[:3000].split('\n'):
                            print(f"    {line}")
                        if len(formatted) > 3000:
                            print(f"    ... (truncated, {len(formatted)} total chars)")
                    except:
                        print(f"  Response: {body[:1000]}")
                elif status == 404:
                    print(f"  [404] GET {ep} - Not found")
                else:
                    print(f"  [{status}] GET {ep}: {body[:300]}")
            except Exception as e:
                print(f"  Error on {ep}: {e}")

        ss(driver, "api_results")

        # ============================================================
        # STEP 6: Network capture - reload dashboard and watch requests
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 6: Network capture during dashboard load")
        print("=" * 70)

        try:
            driver.execute_cdp_cmd('Network.enable', {})
        except:
            pass

        # Clear perf logs
        try: driver.get_log("performance")
        except: pass

        driver.get(BASE_URL + "/")
        time.sleep(5)

        try:
            logs = driver.get_log("performance")
            api_reqs = []
            for entry in logs:
                try:
                    msg = json.loads(entry["message"])["message"]
                    if msg["method"] == "Network.requestWillBeSent":
                        url = msg["params"]["request"]["url"]
                        method = msg["params"]["request"]["method"]
                        if "/api/" in url:
                            api_reqs.append(f"  {method} {url}")
                    elif msg["method"] == "Network.responseReceived":
                        url = msg["params"]["response"]["url"]
                        status = msg["params"]["response"]["status"]
                        if "/api/" in url:
                            api_reqs.append(f"  RESP[{status}] {url}")
                except:
                    pass

            print(f"  API requests during dashboard load ({len(api_reqs)}):")
            for r in api_reqs:
                print(f"  {r}")
        except Exception as e:
            print(f"  Error reading network logs: {e}")

        ss(driver, "network_capture")

        # ============================================================
        # STEP 7: For each module - SSO click-through
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 7: SSO click-through for each module")
        print("=" * 70)

        for module_name, mod_info in MODULES.items():
            print(f"\n{'=' * 50}")
            print(f"  MODULE: {module_name}")
            print(f"  Subdomain: {mod_info['subdomain']}")
            print(f"{'=' * 50}")

            # Go back to dashboard to get fresh SSO links
            driver.get(BASE_URL + "/")
            time.sleep(5)
            ss(driver, f"{module_name}_dashboard")

            # Extract fresh SSO links
            fresh_links = extract_sso_links(driver)

            if module_name in fresh_links:
                sso_url = fresh_links[module_name]["url"]
                token = fresh_links[module_name]["token"]
                decoded = decode_jwt(token)

                print(f"\n  SSO URL: {mod_info['subdomain']}/?sso_token=<JWT>")
                print(f"  JWT alg: {decoded.get('header', {}).get('alg', '?')}")
                print(f"  JWT typ: {decoded.get('header', {}).get('typ', '?')}")
                print(f"  JWT kid: {decoded.get('header', {}).get('kid', '?')}")
                payload = decoded.get('payload', {})
                print(f"  JWT claims:")
                for k, v in payload.items():
                    print(f"    {k}: {v}")

                # Clear perf logs before SSO navigation
                try: driver.get_log("performance")
                except: pass

                # Navigate to SSO URL
                print(f"\n  [Navigating to SSO URL...]")
                driver.get(sso_url)
                time.sleep(6)

                final_url = driver.current_url
                print(f"  Final URL: {final_url}")

                # Check SSO token consumption
                if "sso_token" in final_url:
                    print(f"  Token status: Still in URL")
                else:
                    print(f"  Token status: Consumed/stripped from URL")

                ss(driver, f"{module_name}_after_sso")

                # Check authentication status
                try:
                    page_title = driver.title
                    body_text = driver.find_element(By.TAG_NAME, "body").text[:300]
                    print(f"  Page title: {page_title}")
                    print(f"  Page preview: {body_text[:200]}")

                    if "/login" in final_url.lower() and "dashboard" not in body_text.lower():
                        print(f"  AUTH: NOT authenticated (redirected to login)")
                    else:
                        print(f"  AUTH: AUTHENTICATED on {module_name}")
                except:
                    pass

                # Check module cookies
                cookies = driver.get_cookies()
                if cookies:
                    print(f"  Cookies ({len(cookies)}):")
                    for c in cookies:
                        print(f"    {c['name']} = {c['value'][:60]}... (domain={c.get('domain', '')})")

                # Check module localStorage
                try:
                    mod_storage = driver.execute_script("""
                        var items = {};
                        for (var i = 0; i < localStorage.length; i++) {
                            var key = localStorage.key(i);
                            items[key] = localStorage.getItem(key).substring(0, 200);
                        }
                        return items;
                    """)
                    if mod_storage:
                        print(f"  Module localStorage:")
                        for k, v in mod_storage.items():
                            print(f"    {k}: {v[:120]}")
                except:
                    pass

                # Network requests during SSO
                try:
                    logs = driver.get_log("performance")
                    sso_reqs = []
                    for entry in logs:
                        try:
                            msg = json.loads(entry["message"])["message"]
                            if msg["method"] == "Network.requestWillBeSent":
                                url = msg["params"]["request"]["url"]
                                method = msg["params"]["request"]["method"]
                                if any(t in url.lower() for t in ["sso", "token", "auth", "/api/"]):
                                    sso_reqs.append(f"{method} {url[:200]}")
                            elif msg["method"] == "Network.responseReceived":
                                url = msg["params"]["response"]["url"]
                                status = msg["params"]["response"]["status"]
                                if any(t in url.lower() for t in ["sso", "token", "auth", "/api/"]):
                                    sso_reqs.append(f"RESP[{status}] {url[:200]}")
                        except:
                            pass
                    if sso_reqs:
                        print(f"  Network during SSO:")
                        for r in sso_reqs:
                            print(f"    {r}")
                except:
                    pass

                ss(driver, f"{module_name}_authenticated")

            else:
                print(f"  WARNING: No SSO link found for {module_name} on dashboard!")

            # Test direct access without SSO token
            print(f"\n  [Testing direct subdomain access (no SSO token)...]")
            driver.delete_all_cookies()  # Clear cookies first
            driver.get(mod_info["subdomain"])
            time.sleep(4)
            direct_url = driver.current_url
            print(f"  Direct access result: {direct_url}")
            ss(driver, f"{module_name}_direct_no_sso")

            if "/login" in direct_url.lower():
                print(f"  Direct access: BLOCKED -> redirected to login")
            else:
                print(f"  Direct access: ALLOWED (landed on: {direct_url})")

        # ============================================================
        # STEP 8: Token freshness test
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 8: Token freshness test")
        print("=" * 70)

        # Re-login
        login(driver)

        driver.get(BASE_URL + "/")
        time.sleep(5)
        tokens1 = {}
        for mod, info in extract_sso_links(driver).items():
            tokens1[mod] = info["token"]

        time.sleep(3)
        driver.get(BASE_URL + "/")
        time.sleep(5)
        tokens2 = {}
        for mod, info in extract_sso_links(driver).items():
            tokens2[mod] = info["token"]

        for mod in MODULES:
            t1 = tokens1.get(mod, "")
            t2 = tokens2.get(mod, "")
            if t1 and t2:
                same = t1 == t2
                print(f"  {mod}: Tokens {'SAME' if same else 'DIFFERENT'} between page loads")
                if not same:
                    # Decode both to compare
                    d1 = decode_jwt(t1)
                    d2 = decode_jwt(t2)
                    iat1 = d1.get("payload", {}).get("iat", 0)
                    iat2 = d2.get("payload", {}).get("iat", 0)
                    exp1 = d1.get("payload", {}).get("exp", 0)
                    exp2 = d2.get("payload", {}).get("exp", 0)
                    print(f"    Load 1: iat={iat1}, exp={exp1}")
                    print(f"    Load 2: iat={iat2}, exp={exp2}")
            else:
                print(f"  {mod}: Could not compare (t1={'yes' if t1 else 'no'}, t2={'yes' if t2 else 'no'})")

        ss(driver, "token_freshness_test")

        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        print("\n" + "=" * 70)
        print("COMPLETE SSO MECHANISM SUMMARY")
        print("=" * 70)

        print("""
EXACT SSO MECHANISM:
====================

1. LOGIN:
   - POST credentials to https://test-empcloud.empcloud.com/login
   - Server returns JWT access token (RS256, kid=MjjnAEAPSQoO04cD)
   - Token stored in localStorage['empcloud-auth'].state.accessToken
   - JWT claims: sub (user_id=522), org_id (5), email, role, org_name

2. SSO TOKEN GENERATION:
   - When dashboard loads, frontend calls:
     GET /api/v1/modules -> list of available modules
     GET /api/v1/subscriptions -> which modules org has subscribed to
   - The server generates SSO JWT tokens for each subscribed module
   - These tokens are embedded directly in <a href> links on the page
   - NO separate API call needed to get SSO URLs

3. SSO URL PATTERN:
   https://<module-subdomain>/?sso_token=<JWT>

4. PER-MODULE SSO URLs:
   Performance: https://test-performance.empcloud.com/?sso_token=<JWT>
   Rewards:     https://test-rewards.empcloud.com/?sso_token=<JWT>
   Exit:        https://test-exit.empcloud.com/?sso_token=<JWT>
   Recruit:     https://test-recruit.empcloud.com/?sso_token=<JWT>
   LMS:         https://testlms.empcloud.com/?sso_token=<JWT>

5. SSO JWT STRUCTURE:
   - Algorithm: RS256 (asymmetric RSA)
   - Key ID (kid): MjjnAEAPSQoO04cD
   - Issuer: https://test-empcloud-api.empcloud.com
   - Claims: sub, org_id, email, role, first_name, last_name, org_name, scope, client_id, jti, iat, exp

6. MODULE AUTHENTICATION:
   - Module subdomain reads ?sso_token from URL
   - Validates JWT signature using public key (kid match)
   - Creates local session/auth state
   - Strips sso_token from URL
   - Direct access without sso_token -> redirects to /login

7. WHERE TO FIND SSO LINKS:
   - Dashboard (root / page): "Launch" buttons and module name links
   - NOT on /modules page (that's for subscription management)

8. AUTOMATION PATTERN:
   driver.get("https://test-empcloud.empcloud.com/login")
   # ... login ...
   driver.get("https://test-empcloud.empcloud.com/")  # dashboard
   time.sleep(5)
   link = driver.find_element(By.XPATH,
       "//a[contains(@href,'test-performance.empcloud.com') and contains(@href,'sso_token')]")
   sso_url = link.get_attribute("href")
   driver.get(sso_url)  # Now on Performance module, authenticated
""")

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        ss(driver, "fatal_error")
    finally:
        driver.quit()

    end = datetime.now()
    print(f"\nCompleted in {end - start}")
    print(f"Screenshots: {SCREENSHOT_DIR}")


if __name__ == "__main__":
    main()
