"""
Deep dive: Employee can see full admin navigation and pages in Exit module.
Screenshot each sidebar page the employee can access.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

LOGIN_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
EXIT_FRONTEND = "https://test-exit.empcloud.com"
EXIT_API = "https://test-exit-api.empcloud.com"
EMAIL = "priya@technova.in"
PASSWORD = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_exit_employee"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

bugs = []

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {path}")

def file_bug(title, body):
    bugs.append({"title": title, "body": body})
    log(f"  BUG: {title}")

def create_github_issues():
    if not bugs:
        return
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    for bug in bugs:
        payload = {"title": bug["title"], "body": bug["body"], "labels": ["bug", "exit-module", "rbac", "employee"]}
        try:
            r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues", headers=headers, json=payload, timeout=15)
            if r.status_code == 201:
                log(f"  Issue created: {r.json().get('html_url')}")
            else:
                log(f"  Issue failed ({r.status_code}): {r.text[:200]}")
        except Exception as e:
            log(f"  Issue error: {e}")

# Login
resp = requests.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD}, timeout=15)
data = resp.json()
token = data["data"]["tokens"]["access_token"]
api_headers = {"Authorization": f"Bearer {token}"}
log(f"Token obtained: {token[:30]}...")

# Browser
opts = Options()
opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")
opts.add_argument("--disable-gpu")
opts.add_argument("--ignore-certificate-errors")
driver = webdriver.Chrome(options=opts)
driver.set_page_load_timeout(30)

# SSO in
driver.get(f"{EXIT_FRONTEND}?sso_token={token}")
time.sleep(4)
log(f"Landed on: {driver.current_url}")

# Check every sidebar page an employee can reach
sidebar_pages = [
    ("dashboard", "Dashboard"),
    ("exits", "Exits List"),
    ("checklists", "Checklists"),
    ("clearance", "Clearance"),
    ("interviews", "Exit Interviews"),
    ("fnf", "FnF Settlements"),
    ("notice-buyout", "Notice Buyout"),
    ("assets", "Assets"),
    ("kt", "Knowledge Transfer"),
    ("letters", "Letters"),
    ("alumni", "Alumni"),
    ("rehire", "Rehire"),
    ("analytics", "Analytics"),
    ("flight-risk", "Flight Risk"),
    ("settings", "Settings"),
]

admin_only_pages = ["analytics", "flight-risk", "settings", "fnf", "exits", "checklists", "clearance", "interviews", "notice-buyout", "assets", "kt", "letters", "alumni", "rehire"]

rbac_violations = []

for path, label in sidebar_pages:
    url = f"{EXIT_FRONTEND}/{path}"
    try:
        driver.get(url)
        time.sleep(3)
        curr = driver.current_url
        body = driver.find_element(By.TAG_NAME, "body").text
        screenshot(driver, f"deep_{path}")
        log(f"\n--- {label} ({url}) ---")
        log(f"  URL: {curr}")
        log(f"  Content (300 chars): {body[:300]}")

        # Is this an admin-only page?
        is_admin_page = path in admin_only_pages
        is_accessible = (
            "Page Not Found" not in body
            and "not authorized" not in body.lower()
            and "access denied" not in body.lower()
            and "login" not in curr.lower().split(EXIT_FRONTEND.lower())[-1]
            and len(body.strip()) > 100
        )

        if is_admin_page and is_accessible:
            log(f"  ** RBAC VIOLATION: Employee can access {label} page! **")
            rbac_violations.append((path, label, body[:500]))
    except Exception as e:
        log(f"  Error on {url}: {e}")

# Also test via API with the employee token - hit the exit-api
log("\n\n=== API DEEP DIVE WITH EMPLOYEE TOKEN ===")

api_endpoints = [
    ("GET", "/api/v1/exits", "All exits"),
    ("GET", "/api/v1/exits?page=1&limit=10", "Exits paginated"),
    ("GET", "/api/v1/analytics/dashboard", "Analytics dashboard"),
    ("GET", "/api/v1/analytics/attrition", "Attrition analytics"),
    ("GET", "/api/v1/analytics/trends", "Trends"),
    ("GET", "/api/v1/flight-risk/scores", "Flight risk scores"),
    ("GET", "/api/v1/fnf/list", "FnF list"),
    ("GET", "/api/v1/fnf/pending", "FnF pending"),
    ("GET", "/api/v1/clearance/all", "All clearance"),
    ("GET", "/api/v1/interviews/all", "All interviews"),
    ("GET", "/api/v1/settings", "Settings"),
    ("GET", "/api/v1/checklists", "Checklists"),
    ("GET", "/api/v1/assets/return", "Asset returns"),
    ("GET", "/api/v1/kt/all", "KT sessions"),
    ("GET", "/api/v1/letters/generate", "Letter generation"),
    ("GET", "/api/v1/alumni", "Alumni network"),
    ("GET", "/api/v1/rehire/eligible", "Rehire eligible"),
    ("GET", "/api/v1/notice-buyout", "Notice buyout"),
]

api_violations = []
for method, endpoint, desc in api_endpoints:
    try:
        r = requests.get(f"{EXIT_API}{endpoint}", headers=api_headers, timeout=10)
        log(f"  {desc} ({endpoint}): {r.status_code}")
        if r.status_code == 200:
            try:
                d = r.json()
                dstr = json.dumps(d)[:500]
                log(f"    Data: {dstr[:300]}")
                # Check if it has actual data
                records = d.get("data") or d.get("results") or d.get("items") or d.get("list") or d.get("exits") or []
                if isinstance(records, list) and len(records) > 0:
                    api_violations.append((endpoint, desc, len(records), json.dumps(records[0])[:300]))
                    log(f"    ** API RBAC VIOLATION: {len(records)} records returned **")
                elif isinstance(d, dict) and d.get("data") and isinstance(d["data"], dict) and len(d["data"]) > 2:
                    api_violations.append((endpoint, desc, 1, json.dumps(d["data"])[:300]))
                    log(f"    ** API RBAC VIOLATION: Dashboard/analytics data returned **")
            except:
                pass
    except Exception as e:
        log(f"  {desc} error: {e}")

driver.quit()

# File consolidated bug for UI RBAC violations
if rbac_violations:
    pages_list = "\n".join([f"- `/{path}` ({label})" for path, label, _ in rbac_violations])
    file_bug(
        "[Exit Employee] CRITICAL RBAC: Employee has full admin navigation and page access",
        f"**Severity:** Critical\n\n"
        f"**Steps:**\n1. Login as employee ({EMAIL}) via SSO\n2. Navigate to Exit module dashboard\n\n"
        f"**Expected:** Employee should see limited self-service view (own resignation status, if any). "
        f"Should NOT see admin navigation sidebar with all management pages.\n\n"
        f"**Actual:** Employee sees full admin sidebar navigation with ALL pages accessible:\n{pages_list}\n\n"
        f"The dashboard shows admin metrics (Active Exits, Clearance Pending, FnF Pending, etc.) and "
        f"the employee can navigate to every admin page including Flight Risk scores and Analytics.\n\n"
        f"**Impact:** CRITICAL RBAC violation. An employee can:\n"
        f"- View all exit/resignation data for other employees\n"
        f"- Access Flight Risk scores (highly confidential HR analytics)\n"
        f"- View FnF settlement details\n"
        f"- Access Analytics dashboard with attrition data\n"
        f"- View clearance, KT, asset return status for all employees\n\n"
        f"**Screenshots:** Available in module_exit_employee folder."
    )

# File bug for API violations if any
if api_violations:
    endpoints_list = "\n".join([f"- `{ep}` ({desc}): {count} records" for ep, desc, count, _ in api_violations])
    file_bug(
        "[Exit Employee] CRITICAL RBAC: Employee token can access admin API endpoints",
        f"**Severity:** Critical\n\n"
        f"**Steps:** Login as employee, use Bearer token against Exit API endpoints\n\n"
        f"**Actual:** Following endpoints return data to employee role:\n{endpoints_list}\n\n"
        f"**Impact:** API-level RBAC bypass. Employee can programmatically access confidential exit data."
    )

log(f"\n=== SUMMARY ===")
log(f"UI RBAC violations: {len(rbac_violations)} pages accessible to employee")
log(f"API RBAC violations: {len(api_violations)} endpoints leaking data")

if bugs:
    log(f"\nFiling {len(bugs)} consolidated bug(s)...")
    create_github_issues()

log("Done.")
