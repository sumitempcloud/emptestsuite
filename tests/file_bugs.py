#!/usr/bin/env python3
"""File bugs for confirmed issues found during testing."""
import sys, os, json, urllib.request, urllib.error, ssl, base64, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\full_coverage"
BASE_URL = "https://test-empcloud.empcloud.com"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def upload_screenshot(local_path, remote_name):
    if not local_path or not os.path.exists(local_path):
        return None
    try:
        with open(local_path, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        path = f"screenshots/full_coverage/{remote_name}"
        data = json.dumps({"message": f"Upload test screenshot: {remote_name}", "content": content, "branch": "main"}).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}",
            data=data,
            headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json", "User-Agent": "EmpCloudTest/1.0"},
            method="PUT"
        )
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        result = json.loads(resp.read().decode())
        url = result.get("content", {}).get("download_url", "")
        print(f"  Uploaded: {url}")
        return url
    except Exception as e:
        print(f"  Upload failed: {e}")
        return None

def create_issue(title, body):
    try:
        data = json.dumps({"title": title, "body": body, "labels": ["bug", "functional-test"]}).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            data=data,
            headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json", "User-Agent": "EmpCloudTest/1.0"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        result = json.loads(resp.read().decode())
        url = result.get("html_url", "")
        print(f"  Issue created: {url}")
        return url
    except Exception as e:
        print(f"  Issue creation failed: {e}")
        return None

# Find screenshot files
def find_ss(prefix):
    files = sorted([f for f in os.listdir(SCREENSHOT_DIR) if f.startswith(prefix) and f.endswith(".png")])
    return os.path.join(SCREENSHOT_DIR, files[-1]) if files else None

bugs = [
    {
        "title": "[Bug] Assets module returns 403 Forbidden for org admin",
        "screenshot": find_ss("m11_dashboard"),
        "screenshot_name": "bug_assets_403_forbidden.png",
        "url": f"{BASE_URL}/assets",
        "steps": "1. Navigate to https://test-empcloud.empcloud.com/login\n2. Login as Org Admin (ananya@technova.in / Welcome@123)\n3. Navigate to the Assets module via sidebar or URL /assets\n4. Observe the page",
        "expected": "The Assets dashboard/list should load showing organization assets.",
        "actual": "Page returns '403 Forbidden' (nginx/1.18.0 Ubuntu). Org admin cannot access the Assets module at all."
    },
    {
        "title": "[Bug] /employees/add URL shows 'Invalid Employee' error instead of add form",
        "screenshot": find_ss("m1_add_employee_form"),
        "screenshot_name": "bug_employees_add_invalid.png",
        "url": f"{BASE_URL}/employees/add",
        "steps": "1. Navigate to https://test-empcloud.empcloud.com/login\n2. Login as Org Admin (ananya@technova.in / Welcome@123)\n3. Navigate to /employees/add directly\n4. Observe the page",
        "expected": "An 'Add Employee' form should be displayed to create a new employee.",
        "actual": "Page shows 'Invalid Employee - The employee ID in the URL is missing or invalid' with a link back to Employee Directory. The URL /employees/add is treated as looking up an employee with ID 'add' rather than showing a creation form."
    },
    {
        "title": "[Bug] External module direct URLs (/payroll, /recruitment, etc.) all return 404",
        "screenshot": find_ss("m23_payroll"),
        "screenshot_name": "bug_external_modules_404.png",
        "url": f"{BASE_URL}/payroll",
        "steps": "1. Navigate to https://test-empcloud.empcloud.com/login\n2. Login as Org Admin (ananya@technova.in / Welcome@123)\n3. Try accessing /payroll, /recruitment, /performance, /rewards, /exit-management, /lms, /projects\n4. Observe each page",
        "expected": "External modules should either redirect to the SSO URL or show the module content.",
        "actual": "All external module direct URLs return 404/not found. These modules are only accessible through SSO from the /modules marketplace page, but there is no URL-based routing for them."
    },
    {
        "title": "[Bug] API v1 authentication endpoint fails - cannot login via REST API",
        "screenshot": None,
        "screenshot_name": None,
        "url": f"{BASE_URL}/api/v1/auth/login",
        "steps": "1. Send POST to https://test-empcloud.empcloud.com/api/v1/auth/login\n2. Body: {\"email\": \"ananya@technova.in\", \"password\": \"Welcome@123\"}\n3. Headers: Content-Type: application/json",
        "expected": "API should return a valid authentication token.",
        "actual": "API login request fails. No auth token returned. All subsequent API CRUD operations are blocked."
    },
]

print("=" * 60)
print("FILING CONFIRMED BUGS")
print("=" * 60)

for i, bug in enumerate(bugs):
    print(f"\n--- Bug {i+1}: {bug['title']} ---")
    img_url = ""
    if bug["screenshot"] and bug["screenshot_name"]:
        img_url = upload_screenshot(bug["screenshot"], bug["screenshot_name"]) or ""

    body = f"""## URL Tested
{bug['url']}

## Steps to Reproduce
{bug['steps']}

## Expected Result
{bug['expected']}

## Actual Result
{bug['actual']}

## Screenshot
{'![Bug Screenshot](' + img_url + ')' if img_url else 'No screenshot available (API-only test)'}
"""
    create_issue(bug["title"], body)
    time.sleep(2)

print("\nDone.")
