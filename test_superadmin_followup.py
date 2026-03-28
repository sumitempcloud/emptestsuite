"""
Follow-up Super Admin test:
- Better sidebar mapping (wait for React render)
- Fix API auth (inspect token format)
- File additional bugs found from screenshots
- Deeper testing of org/audit/subscriptions pages
"""

import os, time, json, requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *

BASE_URL = "https://test-empcloud.empcloud.com"
EMAIL = "admin@empcloud.com"
PASSW = "SuperAdmin@2026"
SS_DIR = r"C:\Users\Admin\screenshots\full_dashboard_superadmin"
GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"

os.makedirs(SS_DIR, exist_ok=True)
bugs_filed = []


def mk_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--ignore-certificate-errors")
    opts.page_load_strategy = "normal"
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(3)
    return d


def ss(d, name):
    p = os.path.join(SS_DIR, f"{name}.png")
    try:
        d.save_screenshot(p)
        print(f"  [SS] {name}.png")
    except:
        print(f"  [SS-FAIL] {name}.png")
        p = None
    return p


def safe_click(d, el):
    try:
        el.click()
    except:
        d.execute_script("arguments[0].click();", el)


def gh_issue(title, desc, sev, labels_extra=None):
    labels = ["bug", "super-admin", "e2e-test"]
    if sev == "critical": labels.append("critical")
    elif sev == "high": labels.append("high-priority")
    if labels_extra: labels.extend(labels_extra)
    body = f"""## Bug Report (Automated E2E Test)
**Severity:** {sev}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Role:** Super Admin (admin@empcloud.com)

### Description
{desc}

### Environment
- URL: {BASE_URL}
- Browser: Chrome headless
"""
    try:
        r = requests.post(f"https://api.github.com/repos/{GH_REPO}/issues",
            headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"},
            json={"title": f"[Super Admin E2E] {title}", "body": body, "labels": labels}, timeout=15)
        if r.status_code == 201:
            url = r.json().get("html_url", "")
            print(f"  [GH] Filed: {url}")
            bugs_filed.append({"title": title, "sev": sev, "url": url})
            return url
        else:
            print(f"  [GH] Failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"  [GH] Error: {e}")
    return None


def driver_ok(d):
    try:
        _ = d.current_url
        return True
    except:
        return False


def login(d):
    d.get(f"{BASE_URL}/login")
    time.sleep(3)
    body = d.find_element(By.TAG_NAME, "body").text.lower()
    if "too many" in body or "try again" in body:
        print("  Rate limited, waiting 60s...")
        d.quit()
        time.sleep(60)
        d = mk_driver()
        d.get(f"{BASE_URL}/login")
        time.sleep(3)
        body = d.find_element(By.TAG_NAME, "body").text.lower()
        if "too many" in body:
            print("  Still limited, waiting 90s...")
            d.quit()
            time.sleep(90)
            d = mk_driver()
            d.get(f"{BASE_URL}/login")
            time.sleep(3)

    ef = WebDriverWait(d, 10).until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
    ef.clear(); ef.send_keys(EMAIL)
    pf = d.find_element(By.CSS_SELECTOR, "input[type='password']")
    pf.clear(); pf.send_keys(PASSW)
    time.sleep(0.5)
    # Click the Sign In button (not the EN language button)
    for b in d.find_elements(By.CSS_SELECTOR, "button[type='submit'], button"):
        if b.is_displayed() and "sign" in b.text.lower():
            safe_click(d, b); break
    time.sleep(5)
    return d, "/login" not in d.current_url


def get_driver(d):
    if driver_ok(d): return d
    print("  Recreating driver...")
    try: d.quit()
    except: pass
    d = mk_driver()
    d, _ = login(d)
    return d


def main():
    print("=" * 70)
    print("SUPER ADMIN FOLLOW-UP TESTS")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    d = mk_driver()
    d, ok = login(d)
    if not ok:
        print("LOGIN FAILED")
        d.quit()
        return
    print(f"  Logged in -> {d.current_url}")

    # ================================================================
    # 1. EXTRACT TOKEN PROPERLY
    # ================================================================
    print("\n" + "=" * 70)
    print("1. TOKEN EXTRACTION & ANALYSIS")
    print("=" * 70)

    auth_token = None
    token_key = None
    try:
        ls = d.execute_script("""
            var r = {};
            for (var i = 0; i < localStorage.length; i++) {
                var k = localStorage.key(i);
                r[k] = localStorage.getItem(k);
            }
            return r;
        """)
        print(f"  localStorage keys: {list(ls.keys())}")
        for k, v in ls.items():
            print(f"    {k}: {v[:100]}..." if len(str(v)) > 100 else f"    {k}: {v}")
            if "token" in k.lower() or "auth" in k.lower() or "user" in k.lower():
                token_key = k
                # Try parsing as JSON
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, dict):
                        print(f"    -> Parsed JSON keys: {list(parsed.keys())}")
                        auth_token = parsed.get("token") or parsed.get("access_token") or parsed.get("accessToken")
                        # Check nested 'state' object (Zustand/Redux pattern)
                        if not auth_token and "state" in parsed and isinstance(parsed["state"], dict):
                            state = parsed["state"]
                            print(f"    -> state keys: {list(state.keys())}")
                            auth_token = state.get("accessToken") or state.get("token") or state.get("access_token")
                        if not auth_token:
                            for sk, sv in parsed.items():
                                if isinstance(sv, str) and len(sv) > 50:
                                    print(f"      Candidate token in '{sk}': {sv[:60]}...")
                                    if not auth_token:
                                        auth_token = sv
                    elif isinstance(parsed, str) and len(parsed) > 50:
                        auth_token = parsed
                except (json.JSONDecodeError, ValueError):
                    if len(v) > 50:
                        auth_token = v

        cookies = d.get_cookies()
        print(f"\n  Cookies ({len(cookies)}):")
        for c in cookies:
            print(f"    {c['name']}: {str(c['value'])[:80]}...")
            if not auth_token and ("token" in c["name"].lower() or "session" in c["name"].lower()):
                auth_token = c["value"]

        if auth_token:
            print(f"\n  Auth token found (len={len(auth_token)})")
            print(f"  Token prefix: {auth_token[:50]}...")
            # Check if JWT
            if auth_token.count('.') == 2:
                print("  Token appears to be JWT")
                import base64
                try:
                    parts = auth_token.split('.')
                    # Decode payload
                    payload = parts[1]
                    padding = 4 - len(payload) % 4
                    if padding != 4:
                        payload += '=' * padding
                    decoded = base64.urlsafe_b64decode(payload)
                    payload_json = json.loads(decoded)
                    print(f"  JWT payload: {json.dumps(payload_json, indent=2)[:500]}")
                except Exception as e:
                    print(f"  JWT decode error: {e}")
        else:
            print("\n  No auth token found!")

    except Exception as e:
        print(f"  Token extraction error: {e}")

    # ================================================================
    # 2. SIDEBAR MAPPING (wait for React hydration)
    # ================================================================
    print("\n" + "=" * 70)
    print("2. SIDEBAR MAPPING (with React wait)")
    print("=" * 70)

    # Go to /admin which we know renders properly
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin")
    time.sleep(5)  # Extra wait for React

    # Wait for sidebar to render
    try:
        WebDriverWait(d, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "nav, aside, [class*='sidebar'], [class*='Sidebar']"))
        )
    except:
        print("  No sidebar container found via wait")

    ss(d, "20_sidebar_admin")

    # Get sidebar using multiple strategies
    sidebar_items = []

    # Strategy 1: Direct link extraction from sidebar area
    for container_sel in ["aside", "nav", "[class*='sidebar']", "[class*='Sidebar']",
                          "[class*='sidenav']", "[class*='SideNav']"]:
        try:
            containers = d.find_elements(By.CSS_SELECTOR, container_sel)
            for container in containers:
                links = container.find_elements(By.TAG_NAME, "a")
                for link in links:
                    try:
                        text = link.text.strip()
                        href = link.get_attribute("href") or ""
                        if text and href:
                            sidebar_items.append({"text": text, "href": href})
                    except:
                        continue
        except:
            continue

    # Strategy 2: Use JavaScript to get all nav links
    if not sidebar_items:
        try:
            js_items = d.execute_script("""
                var items = [];
                // Look for sidebar/nav containers
                var selectors = ['aside a', 'nav a', '[class*="sidebar"] a', '[class*="Sidebar"] a',
                                 '[class*="drawer"] a', '[class*="menu"] a'];
                var seen = new Set();
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        var text = el.textContent.trim();
                        var href = el.href || '';
                        if (text && href && !seen.has(href)) {
                            seen.add(href);
                            items.push({text: text, href: href});
                        }
                    });
                });
                return items;
            """)
            sidebar_items = js_items or []
        except Exception as e:
            print(f"  JS sidebar extraction error: {e}")

    # Strategy 3: Get full page structure
    if not sidebar_items:
        try:
            all_links = d.execute_script("""
                var items = [];
                document.querySelectorAll('a').forEach(function(el) {
                    var text = el.textContent.trim();
                    var href = el.href || '';
                    var rect = el.getBoundingClientRect();
                    if (text && href && rect.x < 250) {  // Left side = sidebar
                        items.push({text: text, href: href, x: rect.x, y: rect.y});
                    }
                });
                return items;
            """)
            sidebar_items = all_links or []
        except Exception as e:
            print(f"  Position-based extraction error: {e}")

    # Deduplicate
    seen = set()
    unique_items = []
    for item in sidebar_items:
        key = item["href"]
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    sidebar_items = unique_items

    print(f"\n  SIDEBAR ITEMS ({len(sidebar_items)}):")
    admin_kws = ["/admin", "/super", "/system", "/config", "/logs", "/audit",
                 "/module", "/org", "/revenue", "/billing", "/ai", "/subscription"]
    admin_items = []
    for item in sidebar_items:
        path = item["href"].replace(BASE_URL, "")
        is_admin = any(kw in path.lower() for kw in admin_kws)
        tag = " [ADMIN-ONLY]" if is_admin else ""
        print(f"    {item['text']}: {path}{tag}")
        if is_admin:
            admin_items.append(item)

    print(f"\n  Admin-only sections: {len(admin_items)}")
    for a in admin_items:
        print(f"    * {a['text']}")

    # Also get the section headers
    try:
        headers = d.execute_script("""
            var h = [];
            document.querySelectorAll('aside *, nav *, [class*="sidebar"] *, [class*="Sidebar"] *').forEach(function(el) {
                var text = el.textContent.trim();
                var tag = el.tagName.toLowerCase();
                var cls = el.className || '';
                if (text && (tag === 'h1' || tag === 'h2' || tag === 'h3' || tag === 'h4' ||
                    cls.toLowerCase().includes('header') || cls.toLowerCase().includes('section') ||
                    cls.toLowerCase().includes('label') || cls.toLowerCase().includes('group'))) {
                    var rect = el.getBoundingClientRect();
                    if (rect.x < 250) {
                        h.push({text: text.substring(0, 80), tag: tag, cls: cls.substring(0, 60)});
                    }
                }
            });
            return h;
        """)
        if headers:
            print(f"\n  Sidebar section headers:")
            for h in headers[:10]:
                print(f"    [{h['tag']}] {h['text']}")
    except:
        pass

    # ================================================================
    # 3. DEEPER PAGE TESTING
    # ================================================================
    print("\n" + "=" * 70)
    print("3. DEEPER PAGE TESTING")
    print("=" * 70)

    # 3a. /admin/super - blank page (confirmed bug)
    print("\n  --- /admin/super (blank page bug) ---")
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin/super")
    time.sleep(5)
    pg_text = d.find_element(By.TAG_NAME, "body").text.strip()
    pg_src = d.page_source
    ss(d, "21_admin_super_deep")
    print(f"  Body text length: {len(pg_text)}")
    print(f"  Body text: '{pg_text[:200]}'")
    # Check console errors
    try:
        logs = d.get_log('browser')
        if logs:
            print(f"  Console logs ({len(logs)}):")
            for log in logs[:10]:
                print(f"    [{log.get('level','')}] {log.get('message','')[:150]}")
    except:
        pass

    # Check if there's a React root that's empty
    try:
        react_root = d.execute_script("""
            var root = document.getElementById('root') || document.getElementById('__next') || document.getElementById('app');
            if (root) return {id: root.id, innerHTML_len: root.innerHTML.length, childCount: root.childElementCount};
            return null;
        """)
        if react_root:
            print(f"  React root: id={react_root['id']}, innerHTML={react_root['innerHTML_len']}, children={react_root['childCount']}")
    except:
        pass

    # 3b. Organizations page - "No organizations found" + errors
    print("\n  --- /admin/organizations (0 orgs + errors) ---")
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin/organizations")
    time.sleep(5)
    ss(d, "22_orgs_deep")
    pg = d.find_element(By.TAG_NAME, "body").text
    print(f"  Content: {pg[:300]}")

    # Check for error toasts
    toasts = d.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='Toast'], [role='alert'], [class*='notification'], [class*='Notification'], [class*='error'], [class*='Error']")
    for t in toasts:
        txt = t.text.strip()
        if txt:
            print(f"  Toast/Error: {txt}")

    if "no organizations found" in pg.lower() or "0 organizations" in pg.lower():
        print("  BUG: Organizations page shows 0 orgs for Super Admin")
        sp = ss(d, "22_orgs_zero_bug")
        gh_issue("Organizations page shows 0 organizations for Super Admin",
                 "The /admin/organizations page shows '0 organizations registered on the platform' and 'No organizations found' for the Super Admin user. "
                 "The platform dashboard at /admin shows 32 organizations exist, but the organization list page fails to load them. "
                 "Error toasts 'An unexpected error occurred' are also visible at the bottom of the page. "
                 "This likely indicates a backend API error when fetching the organization list.",
                 "critical")

    if "unexpected error" in pg.lower():
        print("  BUG: Unexpected error visible on orgs page")

    # 3c. Audit page - blank content area
    print("\n  --- /admin/audit (blank content) ---")
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin/audit")
    time.sleep(5)
    ss(d, "23_audit_deep")
    pg = d.find_element(By.TAG_NAME, "body").text.strip()
    print(f"  Content: '{pg[:300]}'")

    # Check if audit content area is empty
    main_content = d.execute_script("""
        var main = document.querySelector('main, [class*="content"], [class*="Content"]');
        if (main) return main.textContent.trim();
        return '';
    """)
    print(f"  Main content: '{str(main_content)[:200]}'")

    # The sidebar is visible but content area is blank
    sidebar_text = ""
    try:
        sb = d.find_elements(By.CSS_SELECTOR, "aside, nav, [class*='sidebar'], [class*='Sidebar']")
        for s in sb:
            sidebar_text += s.text.strip() + " "
    except: pass

    content_minus_sidebar = pg.replace(sidebar_text.strip(), "").strip() if sidebar_text else pg
    print(f"  Content minus sidebar: '{content_minus_sidebar[:200]}'")

    if len(content_minus_sidebar) < 30:
        print("  BUG: Audit page has blank content area")
        sp = ss(d, "23_audit_blank_bug")
        gh_issue("Audit Logs page (/admin/audit) has blank content area",
                 "The /admin/audit page loads with the sidebar visible but the main content area is completely empty. "
                 "No audit log entries, filters, or table are rendered. Only the sidebar navigation is visible. "
                 "Expected: Audit log entries with timestamps, user actions, IP addresses, etc.",
                 "high")

    # 3d. Module Analytics - shows 0 for everything
    print("\n  --- /admin/modules (Module Analytics - all zeros) ---")
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin/modules")
    time.sleep(5)
    ss(d, "24_modules_deep")
    pg = d.find_element(By.TAG_NAME, "body").text
    print(f"  Content: {pg[:400].encode('ascii','replace').decode()}")

    # Check if all metrics are 0
    if "active modules" in pg.lower() and "no module data" in pg.lower():
        print("  WARN: Module analytics shows no data")

    # 3e. Revenue Analytics - all zeros
    print("\n  --- /admin/revenue (Revenue Analytics) ---")
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin/revenue")
    time.sleep(5)
    ss(d, "25_revenue_deep")
    pg = d.find_element(By.TAG_NAME, "body").text
    print(f"  Content: {pg[:400].encode('ascii','replace').decode()}")

    # 3f. Subscriptions page
    print("\n  --- /admin/subscriptions ---")
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin/subscriptions")
    time.sleep(5)
    ss(d, "26_subscriptions")
    pg = d.find_element(By.TAG_NAME, "body").text
    print(f"  Content: {pg[:400].encode('ascii','replace').decode()}")

    # 3g. Log Dashboard tabs
    print("\n  --- /admin/logs (tab details) ---")
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin/logs")
    time.sleep(5)
    ss(d, "27_logs_overview")
    pg = d.find_element(By.TAG_NAME, "body").text
    print(f"  Overview content: {pg[:400]}")

    # Click each tab
    tabs = d.find_elements(By.CSS_SELECTOR, "[role='tab'], button[class*='tab'], button[class*='Tab']")
    for tab in tabs:
        try:
            txt = tab.text.strip()
            if txt:
                safe_click(d, tab)
                time.sleep(2)
                ss(d, f"27_logs_{txt.lower().replace(' ','_')[:20]}")
                tab_content = d.find_element(By.TAG_NAME, "body").text
                print(f"\n  Tab '{txt}': {tab_content[:200]}")
        except: pass

    # ================================================================
    # 4. API TESTING WITH PROPER TOKEN
    # ================================================================
    print("\n" + "=" * 70)
    print("4. API TESTING")
    print("=" * 70)

    # Try API login first to get a clean token
    api_token = None
    for ep in ["/api/v1/auth/login", "/api/auth/login", "/api/v1/auth/signin"]:
        try:
            r = requests.post(f"{BASE_URL}{ep}",
                json={"email": EMAIL, "password": PASSW},
                headers={"Content-Type": "application/json"},
                timeout=10)
            print(f"  Login {ep}: {r.status_code}")
            if r.status_code == 429:
                print("    Rate limited, skip")
                continue
            if r.status_code == 200:
                data = r.json()
                print(f"    Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                if isinstance(data, dict):
                    api_token = data.get("token") or data.get("access_token") or data.get("accessToken")
                    if not api_token and "data" in data and isinstance(data["data"], dict):
                        api_token = data["data"].get("token") or data["data"].get("access_token") or data["data"].get("accessToken")
                        print(f"    data keys: {list(data['data'].keys())}")
                    if not api_token:
                        # Print all string values
                        for k, v in data.items():
                            if isinstance(v, str) and len(v) > 50:
                                print(f"    Possible token in '{k}': {v[:60]}...")
                                api_token = v
                                break
                if api_token:
                    print(f"    Got API token (len={len(api_token)})")
                    break
            elif r.status_code in [200, 201]:
                print(f"    Body: {r.text[:200]}")
        except Exception as e:
            print(f"  {ep}: {e}")

    # Use browser token if API login failed
    if not api_token and auth_token:
        api_token = auth_token
        print(f"  Using browser token (len={len(api_token)})")

    if not api_token:
        print("  NO TOKEN AVAILABLE")
    else:
        # Test various header formats
        for auth_format, auth_value in [
            ("Bearer", f"Bearer {api_token}"),
            ("Token", f"Token {api_token}"),
            ("Raw", api_token),
        ]:
            hdrs = {"Accept": "application/json", "Authorization": auth_value}
            r = None
            try:
                r = requests.get(f"{BASE_URL}/api/v1/users", headers=hdrs, timeout=10)
                if r.status_code == 429:
                    print(f"  {auth_format}: 429 skip")
                    continue
                print(f"  {auth_format} format: {r.status_code}")
                if r.status_code == 200:
                    print(f"    Working! Response: {r.text[:200]}")
                    break
                elif r.status_code == 401:
                    print(f"    Unauthorized: {r.text[:150]}")
            except Exception as e:
                print(f"  {auth_format}: {e}")

        # Try cookie-based auth
        print("\n  Trying cookie-based API calls...")
        d = get_driver(d)
        cookies = d.get_cookies()
        session = requests.Session()
        for c in cookies:
            session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))

        for name, ep in [
            ("Users", "/api/v1/users"),
            ("Modules", "/api/v1/modules"),
            ("Audit", "/api/v1/audit"),
            ("Orgs", "/api/v1/organizations"),
            ("Me", "/api/v1/auth/me"),
        ]:
            try:
                r = session.get(f"{BASE_URL}{ep}", timeout=10,
                    headers={"Accept": "application/json"})
                if r.status_code == 429:
                    print(f"    {name}: 429 skip")
                    continue
                print(f"    {name} ({ep}): {r.status_code}")
                if r.status_code == 200:
                    try:
                        data = r.json()
                        if isinstance(data, list):
                            print(f"      {len(data)} items")
                        elif isinstance(data, dict):
                            print(f"      Keys: {list(data.keys())[:10]}")
                            for k in ["data", "users", "modules"]:
                                if k in data and isinstance(data[k], list):
                                    print(f"      {k}: {len(data[k])} items")
                    except:
                        print(f"      Not JSON: {r.text[:100]}")
                elif r.status_code == 401:
                    print(f"      Unauth: {r.text[:100]}")
            except Exception as e:
                print(f"    {name}: {e}")

        # Try using browser fetch via selenium
        print("\n  Trying fetch via browser context...")
        d = get_driver(d)
        for name, ep in [("Users", "/api/v1/users"), ("Orgs", "/api/v1/organizations"),
                          ("Modules", "/api/v1/modules"), ("Me", "/api/v1/auth/me")]:
            try:
                result = d.execute_script(f"""
                    var result = await fetch('{BASE_URL}{ep}', {{
                        credentials: 'include',
                        headers: {{'Accept': 'application/json'}}
                    }});
                    var status = result.status;
                    var text = await result.text();
                    return {{status: status, body: text.substring(0, 500)}};
                """)
                print(f"    {name}: status={result['status']}")
                if result['status'] == 200:
                    try:
                        body = json.loads(result['body'])
                        if isinstance(body, dict):
                            print(f"      Keys: {list(body.keys())[:10]}")
                            for k in ["data", "users", "modules", "organizations"]:
                                if k in body and isinstance(body[k], list):
                                    print(f"      {k}: {len(body[k])} items")
                        elif isinstance(body, list):
                            print(f"      {len(body)} items")
                    except:
                        print(f"      Body: {result['body'][:150]}")
                else:
                    print(f"      Body: {result['body'][:150]}")
            except Exception as e:
                print(f"    {name}: {e}")

    # ================================================================
    # 5. FILE ADDITIONAL BUGS FROM SCREENSHOTS
    # ================================================================
    print("\n" + "=" * 70)
    print("5. FILING ADDITIONAL BUGS")
    print("=" * 70)

    # Bug: /admin/super blank - already filed as #205

    # Bug: Module Analytics shows 0 active modules, 0 subscribers, 0 total usage
    # but /admin dashboard shows 10 active subscriptions
    print("\n  Checking Module Analytics discrepancy...")
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin/modules")
    time.sleep(4)
    mod_pg = d.find_element(By.TAG_NAME, "body").text
    if "0" in mod_pg and ("active module" in mod_pg.lower() or "total subscriber" in mod_pg.lower()):
        # Check if dashboard shows different numbers
        d.get(f"{BASE_URL}/admin")
        time.sleep(4)
        dash_pg = d.find_element(By.TAG_NAME, "body").text
        if "10" in dash_pg or "subscription" in dash_pg.lower():
            sp = ss(d, "28_module_zero_bug")
            gh_issue("Module Analytics shows all zeros despite active subscriptions",
                     "The Module Analytics page at /admin/modules shows 0 Active Modules, 0 Total Subscribers, "
                     "0 Total Usage, while the Overview Dashboard at /admin shows active subscription data (10 Total Subscriptions). "
                     "The 'Revenue by Module' and 'Subscriber Distribution' charts show 'No module data' and 'No subscriber data'. "
                     "This suggests the Module Analytics page is not properly fetching or displaying module statistics.",
                     "high")

    # Bug: Revenue Analytics shows $0 for MRR and ARR
    print("\n  Checking Revenue Analytics...")
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin/revenue")
    time.sleep(4)
    rev_pg = d.find_element(By.TAG_NAME, "body").text
    ss(d, "29_revenue_check")
    if "$0" in rev_pg or "₹0" in rev_pg or ("0%" in rev_pg and "churn" in rev_pg.lower()):
        sp = ss(d, "29_revenue_zero_bug")
        gh_issue("Revenue Analytics shows $0 MRR/ARR despite active subscriptions",
                 "The Revenue Analytics page at /admin/revenue shows $0 Monthly Recurring Revenue, $0 Annual Recurring Revenue, "
                 "0% Churn Rate, and 1 Paying Customer. All revenue charts (Revenue Trend, Revenue by Module, "
                 "Revenue by Plan Tier, Billing Cycle Distribution) appear empty. "
                 "Given the dashboard shows 32 organizations and 10 subscriptions, revenue data should be populated.",
                 "medium")

    # Bug: Log Dashboard shows 835 total errors and 1776 file errors
    print("\n  Checking Log Dashboard error counts...")
    d = get_driver(d)
    d.get(f"{BASE_URL}/admin/logs")
    time.sleep(4)
    log_pg = d.find_element(By.TAG_NAME, "body").text
    ss(d, "30_logs_errors")
    # These are informational, not bugs themselves - the errors shown in the logs are the bugs
    print(f"  Log page content: {log_pg[:300]}")

    # Check error details from logs page
    if "errors per module" in log_pg.lower():
        print("  Log dashboard shows errors per module - checking details")

    # ================================================================
    # 6. CROSS-ORG VISIBILITY DEEP TEST
    # ================================================================
    print("\n" + "=" * 70)
    print("6. CROSS-ORG VISIBILITY")
    print("=" * 70)

    d = get_driver(d)
    d.get(f"{BASE_URL}/admin")
    time.sleep(4)
    dash = d.find_element(By.TAG_NAME, "body").text
    print(f"  Dashboard shows: {dash[:300]}")

    # Check if the "32 Organizations" link goes to org list
    try:
        org_links = d.find_elements(By.PARTIAL_LINK_TEXT, "Organization")
        if not org_links:
            org_links = d.find_elements(By.PARTIAL_LINK_TEXT, "organization")
        for link in org_links[:3]:
            print(f"  Found org link: {link.text} -> {link.get_attribute('href')}")
    except: pass

    # Navigate to org details
    d.get(f"{BASE_URL}/admin/organizations")
    time.sleep(4)
    org_pg = d.find_element(By.TAG_NAME, "body").text
    ss(d, "31_org_crosscheck")
    print(f"  Org page: {org_pg[:200]}")

    # Dashboard says 32 orgs but org list says 0 - this is the bug we already filed

    # ================================================================
    # SUMMARY
    # ================================================================
    print("\n" + "=" * 70)
    print("FOLLOW-UP SUMMARY")
    print("=" * 70)

    print(f"\nBugs filed: {len(bugs_filed)}")
    for b in bugs_filed:
        print(f"  [{b['sev'].upper()}] {b['title']}")
        print(f"    {b['url']}")

    print(f"\nDone: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try: d.quit()
    except: pass


if __name__ == "__main__":
    main()
