#!/usr/bin/env python3
"""Discover the actual API structure and UI layout of EMP Cloud HRMS."""
import sys, time, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE = "https://test-empcloud.empcloud.com"
API = f"{BASE}/api/v1"

# --- Try to discover API auth ---
print("=== API Discovery ===")
sess = requests.Session()

# Try login
for ep in ["/auth/login", "/auth/signin", "/login", "/auth/authenticate", "/users/login",
           "/auth/local", "/auth/email", "/signin"]:
    for payload_fmt in [
        {"email": "ananya@technova.in", "password": "Welcome@123"},
        {"username": "ananya@technova.in", "password": "Welcome@123"},
        {"email": "ananya@technova.in", "password": "Welcome@123", "organization": "technova"},
    ]:
        try:
            r = sess.post(f"{API}{ep}", json=payload_fmt, timeout=10)
            print(f"  POST {API}{ep} -> {r.status_code}")
            if r.status_code != 404:
                try:
                    print(f"    Response: {json.dumps(r.json(), indent=2)[:500]}")
                except:
                    print(f"    Response: {r.text[:300]}")
            if r.status_code in (200, 201):
                print(f"    *** FOUND LOGIN ENDPOINT ***")
                break
        except Exception as e:
            print(f"  POST {API}{ep} -> ERROR: {e}")
    else:
        continue
    break

# Try base API without auth to see if endpoints exist
print("\n=== Checking known endpoints ===")
for ep in ["/", "/health", "/status", "/me", "/profile",
           "/employees", "/departments", "/leaves", "/attendance",
           "/documents", "/announcements", "/events", "/surveys",
           "/tickets", "/assets", "/positions", "/forum",
           "/wellness", "/feedback", "/whistleblowing",
           "/organization", "/company", "/settings"]:
    try:
        r = sess.get(f"{API}{ep}", timeout=8)
        status = r.status_code
        if status != 404:
            try:
                body = r.json()
                print(f"  GET {ep} -> {status}: {json.dumps(body)[:200]}")
            except:
                print(f"  GET {ep} -> {status}: {r.text[:100]}")
    except Exception as e:
        print(f"  GET {ep} -> ERROR: {e}")

# --- Selenium: discover the app cookies/tokens and actual page structure ---
print("\n=== UI Discovery ===")
opts = Options()
opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")
opts.add_argument("--disable-gpu")
opts.add_argument("--ignore-certificate-errors")

svc = Service(ChromeDriverManager().install())
d = webdriver.Chrome(service=svc, options=opts)
d.set_page_load_timeout(30)

try:
    # Login via UI
    d.get(f"{BASE}/login")
    time.sleep(3)
    print(f"Login page URL: {d.current_url}")
    print(f"Login page title: {d.title}")

    # Find all inputs
    inputs = d.find_elements(By.TAG_NAME, "input")
    print(f"Found {len(inputs)} input fields:")
    for inp in inputs:
        attrs = {}
        for a in ["type", "name", "placeholder", "id", "class"]:
            v = inp.get_attribute(a)
            if v:
                attrs[a] = v
        print(f"  <input {attrs}>")

    # Fill login
    for inp in inputs:
        t = inp.get_attribute("type") or ""
        n = inp.get_attribute("name") or ""
        p = inp.get_attribute("placeholder") or ""
        if t == "email" or "email" in n.lower() or "email" in p.lower():
            inp.clear()
            inp.send_keys("ananya@technova.in")
        elif t == "password" or "password" in n.lower():
            inp.clear()
            inp.send_keys("Welcome@123")

    # Find submit button
    buttons = d.find_elements(By.TAG_NAME, "button")
    for b in buttons:
        print(f"  Button: text='{b.text}' type='{b.get_attribute('type')}'")
        if b.get_attribute("type") == "submit" or "log" in b.text.lower() or "sign" in b.text.lower():
            try:
                b.click()
            except:
                d.execute_script("arguments[0].click();", b)
            break

    time.sleep(5)
    print(f"\nAfter login URL: {d.current_url}")
    print(f"After login title: {d.title}")

    # Get cookies and local storage
    cookies = d.get_cookies()
    print(f"\nCookies ({len(cookies)}):")
    for c in cookies:
        print(f"  {c['name']}: {str(c['value'])[:80]}")

    # Check local storage for tokens
    try:
        ls_keys = d.execute_script("return Object.keys(localStorage);")
        print(f"\nLocalStorage keys: {ls_keys}")
        for k in ls_keys[:10]:
            v = d.execute_script(f"return localStorage.getItem('{k}');")
            print(f"  {k}: {str(v)[:200]}")
    except Exception as e:
        print(f"LocalStorage error: {e}")

    # Check session storage
    try:
        ss_keys = d.execute_script("return Object.keys(sessionStorage);")
        print(f"\nSessionStorage keys: {ss_keys}")
        for k in ss_keys[:10]:
            v = d.execute_script(f"return sessionStorage.getItem('{k}');")
            print(f"  {k}: {str(v)[:200]}")
    except Exception as e:
        print(f"SessionStorage error: {e}")

    # Get all navigation links
    print("\n=== Navigation structure ===")
    all_links = d.find_elements(By.TAG_NAME, "a")
    seen = set()
    for link in all_links:
        href = link.get_attribute("href") or ""
        text = link.text.strip()
        if href and text and href not in seen and BASE in href:
            seen.add(href)
            print(f"  {text}: {href}")

    # Screenshot the dashboard
    d.save_screenshot(r"C:\emptesting\screenshots\dashboard_discovery.png")

    # Try navigating to employees page and inspect
    print("\n=== Employees page ===")
    d.get(f"{BASE}/employees")
    time.sleep(3)
    print(f"URL: {d.current_url}")
    d.save_screenshot(r"C:\emptesting\screenshots\employees_page.png")

    # Look for buttons and interactive elements
    btns = d.find_elements(By.TAG_NAME, "button")
    print(f"Found {len(btns)} buttons:")
    for b in btns[:20]:
        print(f"  Button: text='{b.text.strip()[:50]}' class='{b.get_attribute('class')[:80]}' disabled={b.get_attribute('disabled')}")

    # Check for table/list
    tables = d.find_elements(By.TAG_NAME, "table")
    print(f"Found {len(tables)} tables")

    # Intercept network requests - check API calls the app makes
    print("\n=== Checking XHR/API patterns from page source ===")
    src = d.page_source
    # Look for API patterns
    import re
    api_patterns = re.findall(r'/api/v\d+/[a-zA-Z_/\-]+', src)
    if api_patterns:
        for p in set(api_patterns):
            print(f"  Found API pattern: {p}")

    # Also check for fetch/axios patterns
    fetch_patterns = re.findall(r'fetch\(["\']([^"\']+)', src)
    for p in set(fetch_patterns)[:20]:
        print(f"  Found fetch URL: {p}")

    # Navigate to several key pages
    for path in ["/attendance", "/leave", "/documents", "/announcements", "/settings",
                 "/leave/comp-off", "/policies", "/org-chart", "/chatbot", "/manager"]:
        d.get(f"{BASE}{path}")
        time.sleep(2)
        print(f"\n  Page {path}: URL={d.current_url}, title={d.title}")
        btns = d.find_elements(By.TAG_NAME, "button")
        for b in btns[:5]:
            if b.text.strip():
                print(f"    Button: '{b.text.strip()[:40]}'")
        d.save_screenshot(f"C:\\emptesting\\screenshots\\page_{path.replace('/', '_')}.png")

    # Try to get token from cookie for API calls
    print("\n=== Trying authenticated API calls with session cookies ===")
    token = None
    for c in cookies:
        if "token" in c["name"].lower() or "auth" in c["name"].lower() or "session" in c["name"].lower():
            token = c["value"]
            print(f"  Using cookie '{c['name']}' as token")
            break

    # Also try localStorage token
    try:
        for k in ls_keys:
            if "token" in k.lower() or "auth" in k.lower():
                token = d.execute_script(f"return localStorage.getItem('{k}');")
                print(f"  Using localStorage '{k}' as token")
                break
    except:
        pass

    if token:
        headers = {"Authorization": f"Bearer {token}"}
        for ep in ["/employees", "/departments", "/leaves", "/attendance", "/documents",
                   "/announcements", "/events", "/me", "/profile", "/organization",
                   "/company/employees", "/hrms/employees", "/user/me"]:
            try:
                r = requests.get(f"{API}{ep}", headers=headers, timeout=8)
                if r.status_code != 404:
                    print(f"  GET {ep} with token -> {r.status_code}: {r.text[:150]}")
            except:
                pass

    # Try using the session cookies directly
    print("\n=== Trying API calls with session cookies ===")
    cookie_sess = requests.Session()
    for c in cookies:
        cookie_sess.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))

    for ep in ["/employees", "/departments", "/leaves", "/attendance", "/me",
               "/profile", "/documents", "/announcements", "/user", "/auth/me",
               "/auth/session", "/auth/profile"]:
        try:
            r = cookie_sess.get(f"{API}{ep}", timeout=8)
            if r.status_code not in (404, 405):
                print(f"  GET {ep} with cookies -> {r.status_code}: {r.text[:200]}")
        except:
            pass

finally:
    d.quit()
