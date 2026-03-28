import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

BASE_URL = "https://test-empcloud-api.empcloud.com/api/v1"
LOGIN_URL = "https://test-empcloud.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

# ============================================================
# PART 1: API-based SSO discovery
# ============================================================
print("=" * 80)
print("PART 1: API-BASED SSO DISCOVERY")
print("=" * 80)

session = requests.Session()
session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

# Step 1: Login
print("\n[1] Logging in via API...")
login_resp = session.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
print(f"  Status: {login_resp.status_code}")
login_data = login_resp.json()
token = login_data.get("data", {}).get("token") or login_data.get("token")
if not token:
    # Try nested
    for key in login_data:
        if isinstance(login_data[key], dict) and "token" in login_data[key]:
            token = login_data[key]["token"]
            break
print(f"  Token obtained: {bool(token)}")
if token:
    print(f"  Token prefix: {token[:40]}...")
    session.headers.update({"Authorization": f"Bearer {token}"})

# Helper to try endpoints
def try_endpoint(method, path, label, body=None):
    print(f"\n[API] {label}: {method} {path}")
    try:
        if method == "GET":
            r = session.get(f"{BASE_URL}{path}", timeout=15)
        else:
            r = session.post(f"{BASE_URL}{path}", json=body or {}, timeout=15)
        print(f"  Status: {r.status_code}")
        try:
            data = r.json()
            text = json.dumps(data, indent=2, default=str)
            # Print full if small, truncated if large
            if len(text) < 3000:
                print(f"  Response:\n{text}")
            else:
                print(f"  Response (first 3000 chars):\n{text[:3000]}...")
            # Search for SSO-related keys
            sso_keys = []
            def find_sso_keys(obj, prefix=""):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        kl = k.lower()
                        if any(x in kl for x in ['sso', 'launch', 'url', 'redirect', 'token_url', 'module_url', 'link']):
                            sso_keys.append((f"{prefix}.{k}" if prefix else k, v))
                        find_sso_keys(v, f"{prefix}.{k}" if prefix else k)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        find_sso_keys(item, f"{prefix}[{i}]")
            find_sso_keys(data)
            if sso_keys:
                print(f"\n  *** SSO-RELATED KEYS FOUND ***")
                for key_path, val in sso_keys:
                    print(f"    {key_path} = {val}")
        except:
            print(f"  Raw response: {r.text[:1000]}")
    except Exception as e:
        print(f"  Error: {e}")

# Step 2: Try various API endpoints
print("\n" + "-" * 60)
print("TRYING API ENDPOINTS")
print("-" * 60)

try_endpoint("GET", "/modules", "Get modules list")
try_endpoint("GET", "/subscriptions", "Get subscriptions")
try_endpoint("GET", "/user/modules", "Get user modules")
try_endpoint("GET", "/dashboard", "Get dashboard")
try_endpoint("GET", "/dashboard/modules", "Get dashboard modules")
try_endpoint("GET", "/me", "Get current user profile")
try_endpoint("GET", "/user/profile", "Get user profile")
try_endpoint("POST", "/auth/sso/generate", "Generate SSO token")
try_endpoint("POST", "/auth/sso/token", "Get SSO token")
try_endpoint("GET", "/auth/sso/url", "Get SSO URL")
try_endpoint("POST", "/sso/generate", "Generate SSO (alt)")
try_endpoint("GET", "/sso/token", "Get SSO token (alt)")

# If modules returns data, try launch/sso per module
print("\n" + "-" * 60)
print("TRYING PER-MODULE ENDPOINTS")
print("-" * 60)

try:
    mod_resp = session.get(f"{BASE_URL}/modules", timeout=15)
    mod_data = mod_resp.json()
    modules = []
    if isinstance(mod_data, list):
        modules = mod_data
    elif isinstance(mod_data, dict):
        for key in ['data', 'modules', 'items', 'results']:
            if key in mod_data and isinstance(mod_data[key], list):
                modules = mod_data[key]
                break

    print(f"Found {len(modules)} modules")
    for mod in modules[:10]:  # Try first 10
        mod_id = mod.get('id') or mod.get('_id') or mod.get('module_id')
        mod_name = mod.get('name') or mod.get('module_name') or mod.get('title', 'unknown')
        slug = mod.get('slug') or mod.get('code') or mod.get('key', '')
        print(f"\n  Module: {mod_name} (id={mod_id}, slug={slug})")

        # Print all fields of this module
        for k, v in mod.items():
            print(f"    {k}: {v}")

        if mod_id:
            try_endpoint("GET", f"/modules/{mod_id}/launch", f"Launch module {mod_name}")
            try_endpoint("GET", f"/modules/{mod_id}/sso", f"SSO for module {mod_name}")
            try_endpoint("POST", f"/modules/{mod_id}/launch", f"POST Launch module {mod_name}")
            try_endpoint("POST", f"/modules/{mod_id}/sso", f"POST SSO for module {mod_name}")
            try_endpoint("GET", f"/modules/{mod_id}/url", f"URL for module {mod_name}")
except Exception as e:
    print(f"Error processing modules: {e}")

# Try subscriptions similarly
print("\n" + "-" * 60)
print("TRYING PER-SUBSCRIPTION ENDPOINTS")
print("-" * 60)

try:
    sub_resp = session.get(f"{BASE_URL}/subscriptions", timeout=15)
    sub_data = sub_resp.json()
    subs = []
    if isinstance(sub_data, list):
        subs = sub_data
    elif isinstance(sub_data, dict):
        for key in ['data', 'subscriptions', 'items', 'results']:
            if key in sub_data and isinstance(sub_data[key], list):
                subs = sub_data[key]
                break

    print(f"Found {len(subs)} subscriptions")
    for sub in subs[:10]:
        sub_id = sub.get('id') or sub.get('_id') or sub.get('subscription_id')
        sub_name = sub.get('name') or sub.get('module_name') or sub.get('title', 'unknown')
        print(f"\n  Subscription: {sub_name} (id={sub_id})")
        for k, v in sub.items():
            print(f"    {k}: {v}")

        if sub_id:
            try_endpoint("GET", f"/subscriptions/{sub_id}/launch", f"Launch sub {sub_name}")
            try_endpoint("GET", f"/subscriptions/{sub_id}/sso", f"SSO for sub {sub_name}")
except Exception as e:
    print(f"Error processing subscriptions: {e}")

# ============================================================
# PART 2: Selenium with network capture
# ============================================================
print("\n\n" + "=" * 80)
print("PART 2: SELENIUM NETWORK CAPTURE & PAGE INSPECTION")
print("=" * 80)

chrome_options = Options()
chrome_options.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-dev-shm-usage")

# Enable performance logging for network capture
chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"})

driver = webdriver.Chrome(options=chrome_options)
driver.set_page_load_timeout(30)
wait = WebDriverWait(driver, 20)

try:
    # Enable CDP Network
    driver.execute_cdp_cmd('Network.enable', {})

    # Step 1: Login via Selenium
    print("\n[SELENIUM] Navigating to login page...")
    driver.get(LOGIN_URL)
    time.sleep(3)

    print(f"  Current URL: {driver.current_url}")
    print(f"  Title: {driver.title}")

    # Find and fill login form
    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail']")))
    email_field.clear()
    email_field.send_keys(EMAIL)

    pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
    pass_field.clear()
    pass_field.send_keys(PASSWORD)

    # Submit
    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.login-btn, button.btn-primary, input[type='submit']")
    submit_btn.click()
    print("  Submitted login form...")
    time.sleep(5)

    print(f"  Post-login URL: {driver.current_url}")

    # Step 2: Check localStorage and sessionStorage
    print("\n[STORAGE] Checking localStorage and sessionStorage...")
    ls = driver.execute_script("return JSON.stringify(localStorage)")
    ss = driver.execute_script("return JSON.stringify(sessionStorage)")
    print(f"  localStorage keys: {list(json.loads(ls).keys()) if ls and ls != '{}' else 'empty'}")
    print(f"  sessionStorage keys: {list(json.loads(ss).keys()) if ss and ss != '{}' else 'empty'}")

    # Print full storage contents
    if ls and ls != '{}':
        ls_data = json.loads(ls)
        for k, v in ls_data.items():
            val_str = str(v)
            if len(val_str) > 500:
                val_str = val_str[:500] + "..."
            print(f"  LS[{k}] = {val_str}")

    if ss and ss != '{}':
        ss_data = json.loads(ss)
        for k, v in ss_data.items():
            val_str = str(v)
            if len(val_str) > 500:
                val_str = val_str[:500] + "..."
            print(f"  SS[{k}] = {val_str}")

    # Step 3: Check cookies
    print("\n[COOKIES] All cookies:")
    for cookie in driver.get_cookies():
        print(f"  {cookie['name']} = {str(cookie['value'])[:200]} (domain={cookie.get('domain')})")

    # Step 4: Search page source for SSO patterns
    print("\n[SOURCE] Searching page source for SSO patterns...")
    source = driver.page_source

    sso_patterns = re.findall(r'sso[_-]?token|sso[_-]?url|launch[_-]?url|module[_-]?url|sso[_-]?redirect|sso[_-]?login|generateSso|ssoGenerate|launchModule|openModule', source, re.I)
    print(f"  SSO patterns found: {sso_patterns}")

    module_urls = re.findall(r'https?://test[a-z0-9-]*\.empcloud\.com[^\s"\'<>]*', source)
    for url in set(module_urls):
        print(f"  MODULE URL: {url}")

    # Search for API endpoint patterns
    api_patterns = re.findall(r'/api/v1/[a-zA-Z0-9/_-]+', source)
    for p in set(api_patterns):
        print(f"  API ENDPOINT in source: {p}")

    # Search for any URL construction with sso/launch/token
    url_constructions = re.findall(r'["\']([^"\']*(?:sso|launch|token|redirect)[^"\']*)["\']', source, re.I)
    for uc in set(url_constructions):
        print(f"  URL CONSTRUCTION: {uc}")

    # Step 5: Get all JS bundle URLs and search them
    print("\n[JS BUNDLES] Finding JavaScript bundles...")
    scripts = driver.find_elements(By.TAG_NAME, "script")
    js_urls = []
    for s in scripts:
        src = s.get_attribute("src")
        if src:
            js_urls.append(src)
            print(f"  Script: {src}")

    # Fetch and search JS bundles for SSO-related code
    for js_url in js_urls:
        if 'chunk' in js_url or 'main' in js_url or 'app' in js_url or 'bundle' in js_url:
            print(f"\n[JS SEARCH] Fetching {js_url}...")
            try:
                js_resp = requests.get(js_url, timeout=15)
                js_text = js_resp.text

                # Search for SSO patterns in JS
                sso_in_js = re.findall(r'.{0,80}(?:sso|SSO|launch_url|launchUrl|module_url|moduleUrl|generateToken|ssoToken).{0,80}', js_text)
                for match in sso_in_js[:30]:
                    print(f"  JS SSO MATCH: {match.strip()}")

                # Search for API paths
                api_in_js = re.findall(r'["\'](/api/v[12]/[a-zA-Z0-9/_-]+)["\']', js_text)
                for ap in set(api_in_js):
                    print(f"  JS API PATH: {ap}")

                # Search for subdomain patterns
                subdomain_in_js = re.findall(r'["\']([a-z-]*\.empcloud\.com)["\']', js_text)
                for sd in set(subdomain_in_js):
                    print(f"  JS SUBDOMAIN: {sd}")

            except Exception as e:
                print(f"  Error fetching JS: {e}")

    # Step 6: Look for module cards on dashboard and capture clicks
    print("\n[MODULES] Looking for module cards on dashboard...")
    time.sleep(2)

    # Find clickable module elements
    cards = driver.find_elements(By.CSS_SELECTOR, ".module-card, .app-card, [class*='module'], [class*='card'], a[href*='module'], a[href*='launch']")
    print(f"  Found {len(cards)} potential module cards")
    for card in cards[:15]:
        tag = card.tag_name
        cls = card.get_attribute("class") or ""
        href = card.get_attribute("href") or ""
        text = card.text[:100] if card.text else ""
        onclick = card.get_attribute("onclick") or ""
        print(f"  Card: tag={tag}, class={cls[:80]}, href={href}, text={text}, onclick={onclick}")

    # Step 7: Capture performance logs
    print("\n[NETWORK] Checking performance logs...")
    try:
        logs = driver.get_log("performance")
        print(f"  Total performance log entries: {len(logs)}")
        for log_entry in logs:
            msg = json.loads(log_entry["message"])["message"]
            method = msg.get("method", "")
            if method in ["Network.requestWillBeSent", "Network.responseReceived"]:
                params = msg.get("params", {})
                url = ""
                if method == "Network.requestWillBeSent":
                    url = params.get("request", {}).get("url", "")
                elif method == "Network.responseReceived":
                    url = params.get("response", {}).get("url", "")

                if url and any(kw in url.lower() for kw in ['sso', 'token', 'launch', 'module', 'auth', 'redirect']):
                    print(f"  NETWORK [{method}]: {url}")
                    if method == "Network.requestWillBeSent":
                        post_data = params.get("request", {}).get("postData", "")
                        if post_data:
                            print(f"    POST DATA: {post_data[:300]}")
    except Exception as e:
        print(f"  Error reading performance logs: {e}")

    # Step 8: Try clicking a module card and capture network
    print("\n[CLICK TEST] Trying to click a module card...")
    try:
        # Clear logs first
        driver.get_log("performance")

        # Look for specific module links
        all_links = driver.find_elements(By.TAG_NAME, "a")
        module_links = []
        for link in all_links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            if text and len(text) > 2:
                module_links.append((text, href, link))

        print(f"  All links on page ({len(module_links)}):")
        for text, href, _ in module_links[:30]:
            print(f"    [{text[:50]}] -> {href}")

        # Try to find and click something that looks like a module
        clickable = None
        for text, href, link in module_links:
            if any(kw in text.lower() for kw in ['payroll', 'leave', 'attendance', 'hrms', 'employee', 'core']):
                clickable = (text, link)
                break

        if not clickable:
            # Try clicking any card-like element
            card_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='module'], [class*='app-item']")
            for el in card_elements:
                if el.text.strip() and el.is_displayed():
                    clickable = (el.text.strip()[:30], el)
                    break

        if clickable:
            print(f"\n  Clicking: '{clickable[0]}'")
            # Use JS click to avoid interception issues
            driver.execute_script("arguments[0].click();", clickable[1])
            time.sleep(3)

            print(f"  URL after click: {driver.current_url}")

            # Check for new windows/tabs
            handles = driver.window_handles
            print(f"  Window handles: {len(handles)}")
            if len(handles) > 1:
                driver.switch_to.window(handles[-1])
                print(f"  New tab URL: {driver.current_url}")
                driver.switch_to.window(handles[0])

            # Check network logs after click
            logs = driver.get_log("performance")
            print(f"  Performance logs after click: {len(logs)}")
            for log_entry in logs:
                msg = json.loads(log_entry["message"])["message"]
                method = msg.get("method", "")
                if method == "Network.requestWillBeSent":
                    url = msg.get("params", {}).get("request", {}).get("url", "")
                    req_method = msg.get("params", {}).get("request", {}).get("method", "")
                    if url and ('empcloud' in url or 'sso' in url.lower() or 'token' in url.lower() or 'launch' in url.lower()):
                        print(f"  REQUEST: {req_method} {url}")
                        headers = msg.get("params", {}).get("request", {}).get("headers", {})
                        post_data = msg.get("params", {}).get("request", {}).get("postData", "")
                        if post_data:
                            print(f"    POST DATA: {post_data[:500]}")
                elif method == "Network.responseReceived":
                    url = msg.get("params", {}).get("response", {}).get("url", "")
                    status = msg.get("params", {}).get("response", {}).get("status", "")
                    if url and ('empcloud' in url or 'sso' in url.lower() or 'token' in url.lower()):
                        print(f"  RESPONSE: {status} {url}")
        else:
            print("  No clickable module found")

    except Exception as e:
        print(f"  Error during click test: {e}")
        import traceback
        traceback.print_exc()

    # Step 9: Try intercepting JS function calls
    print("\n[JS INTERCEPT] Checking for Angular/React router and module-related functions...")
    try:
        # Check what framework is used
        framework_check = driver.execute_script("""
            var info = {};
            if (window.angular) info.angular = true;
            if (window.ng) info.ng = true;
            if (window.__NEXT_DATA__) info.next = true;
            if (window.__NUXT__) info.nuxt = true;
            if (document.querySelector('[ng-version]')) info.angular_version = document.querySelector('[ng-version]').getAttribute('ng-version');
            if (document.querySelector('#__next')) info.nextjs = true;
            if (document.querySelector('[data-reactroot]')) info.react = true;

            // Check for global app state
            var keys = Object.keys(window).filter(k => !k.startsWith('webkit') && !k.startsWith('chrome'));
            info.window_keys = keys.slice(0, 50);

            return JSON.stringify(info);
        """)
        print(f"  Framework info: {framework_check}")

        # Check for Angular services/state
        ng_state = driver.execute_script("""
            try {
                var el = document.querySelector('app-root') || document.querySelector('[ng-version]') || document.body;
                var ng = window.ng;
                if (ng && ng.getComponent) {
                    var comp = ng.getComponent(el);
                    return JSON.stringify({component: comp ? Object.keys(comp) : 'none'});
                }
                return 'ng not available';
            } catch(e) { return 'Error: ' + e.message; }
        """)
        print(f"  Angular state: {ng_state}")

        # Try to find Redux/NgRx store
        store_check = driver.execute_script("""
            try {
                // Check for any state management
                var results = [];
                if (window.__REDUX_DEVTOOLS_EXTENSION__) results.push('redux_devtools');
                if (window.store) results.push('window.store');
                if (window.__store) results.push('window.__store');

                // Look for environment config
                var metas = document.querySelectorAll('meta');
                metas.forEach(m => {
                    if (m.name && m.content) results.push('meta:' + m.name + '=' + m.content);
                });

                return JSON.stringify(results);
            } catch(e) { return 'Error: ' + e.message; }
        """)
        print(f"  Store/meta check: {store_check}")

        # Check window.__env or similar config
        env_check = driver.execute_script("""
            var envVars = {};
            ['__env', '__config', 'env', 'config', 'appConfig', 'APP_CONFIG', 'environment'].forEach(k => {
                if (window[k]) envVars[k] = window[k];
            });
            return JSON.stringify(envVars, null, 2);
        """)
        print(f"  Environment config: {env_check}")

    except Exception as e:
        print(f"  Error in JS intercept: {e}")

    # Step 10: Check all XHR/fetch requests by monkey-patching
    print("\n[XHR INTERCEPT] Installing XHR/fetch interceptor and re-checking dashboard...")
    try:
        driver.execute_script("""
            window.__captured_requests = [];

            // Intercept fetch
            var origFetch = window.fetch;
            window.fetch = function() {
                var url = arguments[0];
                if (typeof url === 'object') url = url.url;
                var opts = arguments[1] || {};
                window.__captured_requests.push({
                    type: 'fetch',
                    url: url,
                    method: opts.method || 'GET',
                    body: opts.body ? opts.body.toString().substring(0, 500) : null,
                    timestamp: Date.now()
                });
                return origFetch.apply(this, arguments);
            };

            // Intercept XMLHttpRequest
            var origOpen = XMLHttpRequest.prototype.open;
            var origSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function(method, url) {
                this._intercepted = {method: method, url: url};
                return origOpen.apply(this, arguments);
            };
            XMLHttpRequest.prototype.send = function(body) {
                if (this._intercepted) {
                    window.__captured_requests.push({
                        type: 'xhr',
                        url: this._intercepted.url,
                        method: this._intercepted.method,
                        body: body ? body.toString().substring(0, 500) : null,
                        timestamp: Date.now()
                    });
                }
                return origSend.apply(this, arguments);
            };

            // Intercept window.open
            var origWindowOpen = window.open;
            window.open = function(url) {
                window.__captured_requests.push({
                    type: 'window.open',
                    url: url,
                    timestamp: Date.now()
                });
                return origWindowOpen.apply(this, arguments);
            };

            // Intercept location changes
            window.__location_changes = [];
        """)

        # Now try clicking module cards again
        time.sleep(1)

        # Navigate to dashboard again to trigger fresh requests
        driver.get(driver.current_url)
        time.sleep(5)

        # Get captured requests
        captured = driver.execute_script("return JSON.stringify(window.__captured_requests || [])")
        reqs = json.loads(captured)
        print(f"  Captured {len(reqs)} requests after page load:")
        for req in reqs:
            print(f"    [{req.get('type')}] {req.get('method')} {req.get('url')}")
            if req.get('body'):
                print(f"      Body: {req['body']}")

        # Now try to click on a module
        time.sleep(2)
        cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='module'], a")
        for card in cards:
            text = card.text.strip()
            if text and any(kw in text.lower() for kw in ['payroll', 'leave', 'attendance', 'hrms', 'employee', 'core', 'expense']):
                print(f"\n  Clicking module: '{text[:40]}'")
                driver.execute_script("""
                    window.__captured_requests = [];  // Reset
                """)
                driver.execute_script("arguments[0].click();", card)
                time.sleep(3)

                captured = driver.execute_script("return JSON.stringify(window.__captured_requests || [])")
                reqs = json.loads(captured)
                print(f"  Captured {len(reqs)} requests after clicking '{text[:40]}':")
                for req in reqs:
                    print(f"    [{req.get('type')}] {req.get('method')} {req.get('url')}")
                    if req.get('body'):
                        print(f"      Body: {req['body']}")

                print(f"  URL after click: {driver.current_url}")
                handles = driver.window_handles
                if len(handles) > 1:
                    for h in handles[1:]:
                        driver.switch_to.window(h)
                        print(f"  New tab URL: {driver.current_url}")
                    driver.switch_to.window(handles[0])
                break

    except Exception as e:
        print(f"  Error in XHR intercept: {e}")
        import traceback
        traceback.print_exc()

finally:
    driver.quit()

print("\n" + "=" * 80)
print("DONE - SSO DISCOVERY COMPLETE")
print("=" * 80)
