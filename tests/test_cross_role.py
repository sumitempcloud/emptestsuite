#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EMP Cloud HRMS - Cross-Role Comparison Test
Each page visit uses a fresh Chrome driver to avoid crash issues.
"""

import sys, os, json, time, traceback, requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import *

BASE_URL = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\cross_role"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
CHROMEDRIVER = r"C:\Users\Admin\.wdm\drivers\chromedriver\win64\146.0.7680.165\chromedriver-win32\chromedriver.exe"

ROLES = {
    "Super Admin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"},
    "Org Admin":   {"email": "ananya@technova.in", "password": "Welcome@123"},
    "Employee":    {"email": "priya@technova.in",  "password": "Welcome@123"},
    "Other Org":   {"email": "john@globaltech.com","password": "Welcome@123"},
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

results = {
    "sidebar_links": {},
    "page_access": {},
    "api_access": {},
    "data_isolation": {},
    "action_permissions": {},
    "bugs": [],
}


def make_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disable-default-apps")
    opts.add_argument("--disable-hang-monitor")
    opts.add_argument("--disable-popup-blocking")
    opts.add_argument("--disable-prompt-on-repost")
    opts.add_argument("--disable-sync")
    opts.add_argument("--disable-translate")
    opts.add_argument("--metrics-recording-only")
    opts.add_argument("--no-first-run")
    opts.add_argument("--safebrowsing-disable-auto-update")
    import tempfile, uuid
    user_data = os.path.join(tempfile.gettempdir(), f"chrome_{uuid.uuid4().hex[:8]}")
    opts.add_argument(f"--user-data-dir={user_data}")
    svc = Service(CHROMEDRIVER)
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(3)
    return d


def visit_page_as(email, password, page_path, role_name, retries=4):
    """
    Create fresh driver, login, visit page, collect data, quit.
    Returns dict with page info or None on total failure.
    """
    for attempt in range(retries):
        driver = None
        try:
            time.sleep(4 + attempt * 2)  # increasing gap between retries
            driver = make_driver()

            # Login
            driver.get(BASE_URL + "/login")
            time.sleep(3)

            # Fill form
            email_field = None
            for sel in ["input[type='email']", "input[name='email']", "input[type='text']"]:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    email_field = elems[0]
                    break

            if not email_field:
                if "/dashboard" in driver.current_url or "/admin" in driver.current_url:
                    pass  # already logged in somehow
                else:
                    raise Exception("No email field found")

            if email_field:
                email_field.clear()
                email_field.send_keys(email)
                pw = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                pw.clear()
                pw.send_keys(password)

                btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button")
                for b in btns:
                    t = b.text.strip().lower()
                    if t in ["login", "sign in", "log in", "submit", ""]:
                        b.click()
                        break

                WebDriverWait(driver, 12).until(
                    lambda d: "/login" not in d.current_url or
                              d.find_elements(By.CSS_SELECTOR, ".error, .alert-danger, [role='alert']")
                )
                time.sleep(2)

                if "/login" in driver.current_url:
                    raise Exception("Login failed - still on login page")

            # Now navigate to target page
            driver.get(BASE_URL + page_path)
            time.sleep(4)

            current_url = driver.current_url.replace(BASE_URL, "")
            body_text = ""
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text[:5000]
            except:
                pass

            denied = any(x in body_text.lower() for x in [
                "access denied", "unauthorized", "forbidden", "not authorized",
                "permission denied", "403", "you don't have"
            ])
            on_login = "/login" in current_url
            redirected = page_path not in current_url and not on_login

            if on_login:
                status = "redirected_to_login"
            elif denied:
                status = "access_denied"
            elif redirected:
                status = f"redirected:{current_url}"
            else:
                status = "accessible"

            table_rows = len(driver.find_elements(By.CSS_SELECTOR, "table tbody tr"))
            cards = len(driver.find_elements(By.CSS_SELECTOR, ".card, [class*='card']"))

            action_btns = []
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, "button, a.btn, [role='button']")
                for b in btns:
                    txt = b.text.strip().lower()
                    if any(kw in txt for kw in ["create", "add", "new", "approve", "reject", "edit", "delete", "invite"]):
                        action_btns.append(b.text.strip())
            except:
                pass
            action_btns = list(set(action_btns))

            # Sidebar links (only on first page or dashboard)
            sidebar_links = []
            if page_path in ["/dashboard", "/"]:
                for sel in ["nav a", ".sidebar a", "[class*='sidebar'] a", "aside a",
                            "[class*='drawer'] a", "[role='navigation'] a", ".menu a",
                            "[class*='sidenav'] a", "[class*='nav-'] a"]:
                    try:
                        elems = driver.find_elements(By.CSS_SELECTOR, sel)
                        for e in elems:
                            href = e.get_attribute("href") or ""
                            text = e.text.strip()
                            if not text:
                                inners = e.find_elements(By.CSS_SELECTOR, "span, p, div")
                                for i in inners:
                                    if i.text.strip():
                                        text = i.text.strip()
                                        break
                            if not text:
                                text = e.get_attribute("aria-label") or ""
                            if href and BASE_URL in href:
                                path = href.replace(BASE_URL, "")
                                if path and path != "/" and not path.startswith("#"):
                                    sidebar_links.append({"text": text, "href": path})
                    except:
                        continue

                # Deduplicate
                seen = set()
                deduped = []
                for lnk in sidebar_links:
                    if lnk["href"] not in seen:
                        seen.add(lnk["href"])
                        deduped.append(lnk)
                sidebar_links = deduped

            # Screenshot
            safe_name = f"{role_name}_{page_path}".replace(" ", "_").replace("/", "_")
            ss_path = os.path.join(SCREENSHOT_DIR, f"{safe_name}.png")
            try:
                driver.save_screenshot(ss_path)
            except:
                pass

            result = {
                "status": status,
                "current_url": current_url,
                "table_rows": table_rows,
                "cards": cards,
                "action_buttons": action_btns,
                "body_text": body_text,
                "sidebar_links": sidebar_links,
            }
            driver.quit()
            return result

        except Exception as e:
            if attempt < retries - 1:
                print(f"    [retry {attempt+1}] {str(e)[:80]}")
            else:
                print(f"    [FAIL] {str(e)[:100]}")
            try:
                if driver:
                    driver.quit()
            except:
                pass
            time.sleep(3)

    return None


def login_api(email, password):
    """Login via API, return (token, session)."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 EmpCloud-Test",
        "Origin": BASE_URL,
        "Referer": BASE_URL,
    })
    urls = [
        BASE_URL + "/api/v1/auth/login",
        BASE_URL + "/api/auth/login",
        BASE_URL + "/api/v1/login",
    ]
    for url in urls:
        for payload in [{"email": email, "password": password}, {"username": email, "password": password}]:
            try:
                resp = session.post(url, json=payload, timeout=15)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    token = (data.get("token") or data.get("accessToken") or
                             data.get("access_token") or
                             (data.get("data") or {}).get("token") or
                             (data.get("data") or {}).get("accessToken"))
                    if token:
                        return token, session
                    if session.cookies:
                        return "cookie", session
            except:
                continue
    return None, session


def extract_token_via_ui(email, password, role_name):
    """Login via UI and extract auth token from cookies/localStorage."""
    driver = None
    try:
        driver = make_driver()
        driver.get(BASE_URL + "/login")
        time.sleep(3)

        email_field = None
        for sel in ["input[type='email']", "input[name='email']", "input[type='text']"]:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                email_field = elems[0]
                break
        if not email_field:
            return None, requests.Session()

        email_field.clear()
        email_field.send_keys(email)
        pw = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pw.clear()
        pw.send_keys(password)

        btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button")
        for b in btns:
            t = b.text.strip().lower()
            if t in ["login", "sign in", "log in", "submit", ""]:
                b.click()
                break

        WebDriverWait(driver, 12).until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

        # Extract token from localStorage
        for key in ["token", "accessToken", "auth_token", "jwt", "access_token"]:
            try:
                val = driver.execute_script(f"return localStorage.getItem('{key}')")
                if val:
                    print(f"    Found localStorage token: {key}")
                    driver.quit()
                    return val, requests.Session()
            except:
                pass

        # Extract from cookies
        cookies = driver.get_cookies()
        session = requests.Session()
        for c in cookies:
            session.cookies.set(c["name"], c["value"], domain=c.get("domain"))
            if any(k in c["name"].lower() for k in ["token", "auth", "session", "jwt"]):
                print(f"    Found cookie token: {c['name']}")
                driver.quit()
                return c["value"], session

        # Return session with cookies even if no explicit token
        driver.quit()
        return "cookie", session

    except Exception as e:
        print(f"    UI token extraction failed: {e}")
        try:
            if driver:
                driver.quit()
        except:
            pass
        return None, requests.Session()


def file_github_issue(title, body, labels=None):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "EmpCloud-CrossRole-Test",
    }
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code in (201, 200):
            u = resp.json().get("html_url", "")
            print(f"  [ISSUE FILED] {u}")
            return u
        else:
            print(f"  [ISSUE FAIL] {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  [ISSUE ERROR] {e}")
    return None


# ============================================================
# TEST 1: SIDEBAR COMPARISON
# ============================================================
def test1_sidebar():
    print("\n" + "=" * 70)
    print("TEST 1: SIDEBAR COMPARISON")
    print("=" * 70)

    for role_name in ["Super Admin", "Org Admin", "Employee"]:
        creds = ROLES[role_name]
        print(f"\n--- {role_name} ---")

        info = visit_page_as(creds["email"], creds["password"], "/dashboard", role_name)
        if not info:
            # Retry with /
            info = visit_page_as(creds["email"], creds["password"], "/", role_name)

        if info and info["sidebar_links"]:
            results["sidebar_links"][role_name] = info["sidebar_links"]
            print(f"  Found {len(info['sidebar_links'])} sidebar links:")
            for lnk in info["sidebar_links"]:
                print(f"    {lnk['text']:35s} -> {lnk['href']}")
        else:
            results["sidebar_links"][role_name] = []
            print(f"  No sidebar links found (status: {info['status'] if info else 'FAIL'})")

    # Compare
    print("\n--- SIDEBAR COMPARISON ---")
    sa = set(l["href"] for l in results["sidebar_links"].get("Super Admin", []))
    oa = set(l["href"] for l in results["sidebar_links"].get("Org Admin", []))
    emp = set(l["href"] for l in results["sidebar_links"].get("Employee", []))

    print(f"\nSuper Admin only (vs Org Admin): {sa - oa or 'none'}")
    print(f"Org Admin only (vs Employee):    {oa - emp or 'none'}")
    print(f"Employee has, Org Admin doesn't: {emp - oa or 'none'}")
    print(f"Employee has, Super Admin doesn't: {emp - sa or 'none'}")

    # Flag suspicious employee access
    admin_kw = ["admin", "setting", "config", "audit", "role", "permission", "module", "billing"]
    suspicious = [l for l in results["sidebar_links"].get("Employee", [])
                  if any(k in l["href"].lower() or k in l["text"].lower() for k in admin_kw)]
    if suspicious:
        body = ("## Bug Report\n\n**Severity:** High\n**Type:** RBAC Violation\n\n"
                "Employee sees admin-level sidebar links:\n\n")
        for s in suspicious:
            body += f"- **{s['text']}** -> `{s['href']}`\n"
        body += f"\n**Employee:** priya@technova.in\n**Date:** {datetime.now().isoformat()}"
        results["bugs"].append({"title": "[RBAC] Employee sees admin-level sidebar links",
                                "body": body, "labels": ["RBAC", "bug"]})


# ============================================================
# TEST 2: SAME PAGE, DIFFERENT VIEWS
# ============================================================
def test2_page_views():
    print("\n" + "=" * 70)
    print("TEST 2: SAME PAGE, DIFFERENT VIEWS")
    print("=" * 70)

    pages = ["/employees", "/attendance", "/leave", "/documents",
             "/announcements", "/settings",
             "/admin", "/admin/modules", "/admin/organizations", "/admin/settings"]

    for role_name in ["Super Admin", "Org Admin", "Employee"]:
        creds = ROLES[role_name]
        print(f"\n--- {role_name} ---")
        results["page_access"][role_name] = {}

        for page in pages:
            print(f"  {page}...", end=" ", flush=True)
            info = visit_page_as(creds["email"], creds["password"], page, role_name)
            if info:
                results["page_access"][role_name][page] = info
                print(f"{info['status']} rows={info['table_rows']} actions={info['action_buttons'][:3]}")
            else:
                results["page_access"][role_name][page] = {"status": "error", "table_rows": 0, "action_buttons": []}
                print("FAILED")

    # Analyze
    print("\n--- PAGE COMPARISON ---")
    for page in pages:
        print(f"\n  {page}:")
        for r in ["Super Admin", "Org Admin", "Employee"]:
            i = results["page_access"].get(r, {}).get(page, {})
            print(f"    {r:15s}: {i.get('status','?'):30s} rows={i.get('table_rows','?')} actions={i.get('action_buttons',[])[:3]}")

    # Bugs
    emp = results["page_access"].get("Employee", {})
    for page in ["/settings", "/admin", "/admin/modules", "/admin/organizations", "/admin/settings"]:
        i = emp.get(page, {})
        if i.get("status") == "accessible":
            results["bugs"].append({
                "title": f"[RBAC] Employee can access {page}",
                "body": f"## Bug\n\nEmployee (priya@technova.in) can access `{page}` which should be restricted.\nStatus: {i.get('status')}\nRows: {i.get('table_rows')}\nDate: {datetime.now().isoformat()}",
                "labels": ["RBAC", "bug"],
            })

    oa = results["page_access"].get("Org Admin", {})
    for page in ["/admin", "/admin/modules", "/admin/organizations"]:
        i = oa.get(page, {})
        if i.get("status") == "accessible":
            results["bugs"].append({
                "title": f"[RBAC] Org Admin can access Super Admin page {page}",
                "body": f"## Bug\n\nOrg Admin can access `{page}` (Super Admin only).\nDate: {datetime.now().isoformat()}",
                "labels": ["RBAC", "bug"],
            })

    # Employee sees all employees (should see limited)
    emp_info = emp.get("/employees", {})
    sa_info = results["page_access"].get("Super Admin", {}).get("/employees", {})
    oa_info = results["page_access"].get("Org Admin", {}).get("/employees", {})
    if emp_info.get("status") == "accessible" and emp_info.get("table_rows", 0) > 0:
        oa_rows = oa_info.get("table_rows", 0) if oa_info.get("status") == "accessible" else 0
        emp_rows = emp_info.get("table_rows", 0)
        if oa_rows > 0 and emp_rows >= oa_rows:
            results["bugs"].append({
                "title": f"[RBAC] Employee sees same number of employees as Org Admin ({emp_rows} vs {oa_rows})",
                "body": f"## Bug\n\nEmployee sees {emp_rows} rows on /employees.\nOrg Admin sees {oa_rows}.\nEmployee should see limited view.\nDate: {datetime.now().isoformat()}",
                "labels": ["RBAC", "bug"],
            })


# ============================================================
# TEST 3: API ACCESS COMPARISON
# ============================================================
def test3_api():
    print("\n" + "=" * 70)
    print("TEST 3: API ACCESS COMPARISON")
    print("=" * 70)

    endpoints = [
        "/api/v1/users", "/api/v1/announcements", "/api/v1/documents",
        "/api/v1/events", "/api/v1/feedback", "/api/v1/audit", "/api/v1/modules",
    ]

    tokens = {}
    sessions = {}

    for role_name, creds in ROLES.items():
        print(f"\n--- {role_name} ---")
        token, session = login_api(creds["email"], creds["password"])
        if not token:
            print(f"  API login failed, trying UI extraction...")
            token, session = extract_token_via_ui(creds["email"], creds["password"], role_name)
        if token:
            print(f"  Token: {'cookie' if token == 'cookie' else token[:20]}...")
        else:
            print(f"  No token obtained")
        tokens[role_name] = token
        sessions[role_name] = session

    for role_name in ROLES:
        print(f"\n--- API endpoints: {role_name} ---")
        results["api_access"][role_name] = {}
        token = tokens[role_name]
        session = sessions[role_name]

        if not token:
            for ep in endpoints:
                results["api_access"][role_name][ep] = {"code": "no_auth", "count": None}
            print(f"  Skipping (no auth)")
            continue

        headers = {"User-Agent": "Mozilla/5.0 EmpCloud-Test", "Origin": BASE_URL, "Referer": BASE_URL}
        if token and token != "cookie":
            headers["Authorization"] = f"Bearer {token}"

        for ep in endpoints:
            try:
                if token == "cookie":
                    resp = session.get(BASE_URL + ep, headers=headers, timeout=15)
                else:
                    resp = requests.get(BASE_URL + ep, headers=headers, timeout=15)

                count = None
                if resp.status_code == 200:
                    try:
                        j = resp.json()
                        if isinstance(j, list):
                            count = len(j)
                        elif isinstance(j, dict):
                            for k in ["data", "items", "results", "users", "records"]:
                                if k in j and isinstance(j[k], list):
                                    count = len(j[k])
                                    break
                            if count is None:
                                count = len(j)
                    except:
                        pass

                results["api_access"][role_name][ep] = {"code": resp.status_code, "count": count}
                print(f"  {ep:30s} -> {resp.status_code} (n={count})")
            except Exception as e:
                results["api_access"][role_name][ep] = {"code": "error", "count": None}
                print(f"  {ep:30s} -> ERROR: {str(e)[:60]}")

    # Bug detection
    emp_api = results["api_access"].get("Employee", {})
    for ep in ["/api/v1/users", "/api/v1/audit"]:
        i = emp_api.get(ep, {})
        if i.get("code") == 200 and (i.get("count") or 0) > 1:
            results["bugs"].append({
                "title": f"[RBAC] Employee API access to {ep} returns {i['count']} records",
                "body": f"## Bug\n\nEmployee can call `{ep}` and gets {i['count']} records.\nShould be restricted.\nDate: {datetime.now().isoformat()}",
                "labels": ["RBAC", "bug"],
            })


# ============================================================
# TEST 4: DATA ISOLATION
# ============================================================
def test4_isolation():
    print("\n" + "=" * 70)
    print("TEST 4: DATA ISOLATION BETWEEN ORGS")
    print("=" * 70)

    org_data = {}
    org_creds = {
        "TechNova": ROLES["Org Admin"],
        "GlobalTech": ROLES["Other Org"],
    }

    for org, creds in org_creds.items():
        print(f"\n--- {org} ---")
        info = visit_page_as(creds["email"], creds["password"], "/employees", org)
        if info:
            # Extract employee names from body text
            body = info.get("body_text", "")
            org_data[org] = {
                "body_text": body,
                "table_rows": info.get("table_rows", 0),
            }
            print(f"  Status: {info['status']}, Rows: {info['table_rows']}")
            print(f"  Body preview: {body[:200]}")
        else:
            org_data[org] = {"body_text": "", "table_rows": 0}
            print("  FAILED to load")

    # Cross-org checks
    print("\n--- ISOLATION CHECK ---")
    tn = org_data.get("TechNova", {}).get("body_text", "").lower()
    gt = org_data.get("GlobalTech", {}).get("body_text", "").lower()

    tn_rows = org_data.get("TechNova", {}).get("table_rows", 0)
    gt_rows = org_data.get("GlobalTech", {}).get("table_rows", 0)
    print(f"  TechNova rows: {tn_rows}, GlobalTech rows: {gt_rows}")

    if "globaltech" in tn or "john@globaltech" in tn:
        print("  [DATA LEAK] TechNova sees GlobalTech data!")
        results["bugs"].append({
            "title": "[DATA LEAK] TechNova user sees GlobalTech data on employees page",
            "body": f"## Bug\n\nTechNova org admin sees GlobalTech references.\nDate: {datetime.now().isoformat()}",
            "labels": ["DATA LEAK", "bug"],
        })
    else:
        print("  TechNova does NOT see GlobalTech data - OK")

    if "technova" in gt or "ananya@technova" in gt:
        print("  [DATA LEAK] GlobalTech sees TechNova data!")
        results["bugs"].append({
            "title": "[DATA LEAK] GlobalTech user sees TechNova data on employees page",
            "body": f"## Bug\n\nGlobalTech sees TechNova references.\nDate: {datetime.now().isoformat()}",
            "labels": ["DATA LEAK", "bug"],
        })
    else:
        print("  GlobalTech does NOT see TechNova data - OK")

    # Also check announcements & documents isolation
    for page in ["/announcements", "/documents", "/events"]:
        for org, creds in org_creds.items():
            info = visit_page_as(creds["email"], creds["password"], page, org)
            if info:
                results["data_isolation"][f"{org}_{page}"] = {
                    "status": info["status"],
                    "rows": info.get("table_rows", 0),
                }
                print(f"  {org} {page}: {info['status']}, rows={info.get('table_rows',0)}")


# ============================================================
# TEST 5: ACTION PERMISSIONS
# ============================================================
def test5_actions():
    print("\n" + "=" * 70)
    print("TEST 5: ACTION PERMISSIONS")
    print("=" * 70)

    actions = {
        "Create Employee":    {"page": "/employees",    "kw": ["add", "create", "new", "invite"]},
        "Create Announcement":{"page": "/announcements","kw": ["add", "create", "new", "post"]},
        "Approve Leave":      {"page": "/leave",        "kw": ["approve", "reject"]},
        "Access Settings":    {"page": "/settings",     "check": "accessible"},
        "Access Admin":       {"page": "/admin",        "check": "accessible"},
        "Create Ticket":      {"page": "/helpdesk",     "kw": ["create", "new", "raise", "submit", "add"]},
    }

    for role_name in ["Super Admin", "Org Admin", "Employee"]:
        creds = ROLES[role_name]
        print(f"\n--- {role_name} ---")
        results["action_permissions"][role_name] = {}

        for action_name, cfg in actions.items():
            page = cfg["page"]
            print(f"  {action_name} ({page})...", end=" ", flush=True)

            info = visit_page_as(creds["email"], creds["password"], page, role_name)
            if not info:
                results["action_permissions"][role_name][action_name] = "FAILED"
                print("FAILED")
                continue

            status = info["status"]
            if cfg.get("check") == "accessible":
                if status == "accessible":
                    result = "ACCESSIBLE"
                elif "redirect" in status:
                    result = f"REDIRECTED"
                else:
                    result = "DENIED"
            else:
                if status != "accessible":
                    result = f"PAGE {status.upper()}"
                else:
                    btns = info.get("action_buttons", [])
                    found = [b for b in btns if any(k in b.lower() for k in cfg["kw"])]
                    if found:
                        result = f"CAN ({', '.join(found[:2])})"
                    else:
                        result = "NO BUTTON"

            results["action_permissions"][role_name][action_name] = result
            print(result)

    # Bug detection
    emp_perms = results["action_permissions"].get("Employee", {})
    for action in ["Create Employee", "Approve Leave", "Access Settings", "Access Admin"]:
        p = emp_perms.get(action, "")
        if "CAN" in p or p == "ACCESSIBLE":
            results["bugs"].append({
                "title": f"[RBAC] Employee can '{action}'",
                "body": f"## Bug\n\nEmployee can {action}: {p}\nDate: {datetime.now().isoformat()}",
                "labels": ["RBAC", "bug"],
            })


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 70)
    print("EMP CLOUD HRMS - CROSS-ROLE COMPARISON TEST")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    for name, fn in [
        ("Test 1: Sidebar", test1_sidebar),
        ("Test 2: Page Views", test2_page_views),
        ("Test 3: API Access", test3_api),
        ("Test 4: Data Isolation", test4_isolation),
        ("Test 5: Action Permissions", test5_actions),
    ]:
        try:
            fn()
        except Exception as e:
            print(f"\n[FATAL in {name}]: {e}")
            traceback.print_exc()

    # File bugs
    print("\n" + "=" * 70)
    print("FILING GITHUB ISSUES")
    print("=" * 70)

    seen = set()
    unique_bugs = []
    for b in results["bugs"]:
        if b["title"] not in seen:
            seen.add(b["title"])
            unique_bugs.append(b)
    results["bugs"] = unique_bugs

    filed = []
    for b in results["bugs"]:
        u = file_github_issue(b["title"], b["body"], b.get("labels"))
        if u:
            filed.append(u)

    if not results["bugs"]:
        print("  No bugs to file.")

    # ============================================================
    # PERMISSION MATRIX
    # ============================================================
    print("\n" + "=" * 70)
    print("COMPLETE PERMISSION MATRIX")
    print("=" * 70)

    roles3 = ["Super Admin", "Org Admin", "Employee"]

    # Sidebar
    print("\n--- SIDEBAR LINKS ---")
    all_hrefs = sorted(set(l["href"] for r in roles3 for l in results["sidebar_links"].get(r, [])))
    print(f"{'Link':45s} | {'Super Admin':12s} | {'Org Admin':12s} | {'Employee':12s}")
    print("-" * 90)
    for h in all_hrefs:
        row = f"{h:45s}"
        for r in roles3:
            has = h in set(l["href"] for l in results["sidebar_links"].get(r, []))
            row += f" | {'YES':12s}" if has else f" | {'---':12s}"
        print(row)

    # Page Access
    print("\n--- PAGE ACCESS ---")
    all_pages = sorted(set(p for r in roles3 for p in results["page_access"].get(r, {})))
    print(f"{'Page':35s} | {'Super Admin':25s} | {'Org Admin':25s} | {'Employee':25s}")
    print("-" * 120)
    for p in all_pages:
        row = f"{p:35s}"
        for r in roles3:
            i = results["page_access"].get(r, {}).get(p, {})
            s = str(i.get("status", "N/A"))[:25]
            row += f" | {s:25s}"
        print(row)

    # API Access
    print("\n--- API ACCESS ---")
    eps = ["/api/v1/users", "/api/v1/announcements", "/api/v1/documents",
           "/api/v1/events", "/api/v1/feedback", "/api/v1/audit", "/api/v1/modules"]
    all_roles = list(ROLES.keys())
    print(f"{'Endpoint':30s} | {'Super Admin':15s} | {'Org Admin':15s} | {'Employee':15s} | {'Other Org':15s}")
    print("-" * 100)
    for ep in eps:
        row = f"{ep:30s}"
        for r in all_roles:
            i = results["api_access"].get(r, {}).get(ep, {})
            c = i.get("code", "?")
            n = i.get("count", "?")
            row += f" | {str(c):5s}(n={str(n):4s})"
        print(row)

    # Action Permissions
    print("\n--- ACTION PERMISSIONS ---")
    all_actions = sorted(set(a for r in roles3 for a in results["action_permissions"].get(r, {})))
    print(f"{'Action':25s} | {'Super Admin':30s} | {'Org Admin':30s} | {'Employee':30s}")
    print("-" * 120)
    for a in all_actions:
        row = f"{a:25s}"
        for r in roles3:
            p = str(results["action_permissions"].get(r, {}).get(a, "N/A"))[:30]
            row += f" | {p:30s}"
        print(row)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Roles tested: {', '.join(roles3)}")
    print(f"  Sidebar links: {sum(len(v) for v in results['sidebar_links'].values())}")
    print(f"  Pages tested: {len(all_pages)}")
    print(f"  API endpoints: {len(eps)}")
    print(f"  Bugs found: {len(results['bugs'])}")
    print(f"  Issues filed: {len(filed)}")
    for u in filed:
        print(f"    - {u}")
    print(f"  Screenshots: {SCREENSHOT_DIR}")
    print(f"\nCompleted: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
