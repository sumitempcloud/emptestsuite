"""
Add detailed screenshots and steps-to-reproduce to all open GitHub issues
on EmpCloud/EmpCloud that are missing them.
"""
import sys, os, json, time, base64, urllib.request, urllib.error, traceback, tempfile

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
REPO = "EmpCloud/EmpCloud"
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com/api/v1"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
DATE = "2026-03-28"
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOTS_DIR = os.path.join(tempfile.gettempdir(), "empcloud_screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# ---------- GitHub helpers ----------
def gh_request(url, method='GET', data=None):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    if data is not None:
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        print(f"  GitHub API error {e.code}: {body[:200]}")
        raise

def fetch_open_issues():
    issues = []
    page = 1
    while True:
        result = gh_request(f"https://api.github.com/repos/{REPO}/issues?state=open&per_page=100&page={page}")
        if not result:
            break
        issues.extend(result)
        if len(result) < 100:
            break
        page += 1
    return issues

def upload_screenshot(filepath, issue_num):
    with open(filepath, 'rb') as f:
        content = base64.b64encode(f.read()).decode()
    filename = f"screenshots/issue_{issue_num}_{int(time.time())}.png"
    data = {"message": f"Screenshot for issue #{issue_num}", "content": content}
    resp = gh_request(f"https://api.github.com/repos/{REPO}/contents/{filename}", method='PUT', data=data)
    return resp["content"]["download_url"]

def update_issue(issue_num, new_body):
    gh_request(f"https://api.github.com/repos/{REPO}/issues/{issue_num}", method='PATCH', data={"body": new_body})

# ---------- API helpers ----------
def api_login(email, password):
    data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(f"{API_URL}/auth/login", data=data, method='POST',
                                headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        token = result.get("data", {}).get("access_token") or result.get("access_token") or result.get("token")
        if not token and isinstance(result.get("data"), dict):
            token = result["data"].get("token")
        return token, result
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        return None, json.loads(body) if body else {}

def api_call(method, endpoint, token, body=None):
    """Make an API call and return (status_code, response_dict, raw_text)"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
               "Accept": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(f"{API_URL}{endpoint}", data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        raw = resp.read().decode(errors='replace')
        return resp.status, json.loads(raw) if raw else {}, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors='replace')
        try:
            return e.code, json.loads(raw), raw
        except:
            return e.code, {}, raw

# ---------- Selenium helpers ----------
_driver = None
_driver_use_count = 0

def get_driver():
    global _driver, _driver_use_count
    if _driver is not None:
        return _driver
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    opts = Options()
    opts.binary_location = CHROME_PATH
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    service = Service(ChromeDriverManager().install())
    _driver = webdriver.Chrome(service=service, options=opts)
    _driver.set_page_load_timeout(30)
    _driver_use_count = 0
    return _driver

def quit_driver():
    global _driver, _driver_use_count
    if _driver:
        try:
            _driver.quit()
        except:
            pass
        _driver = None
        _driver_use_count = 0

def bump_driver():
    global _driver_use_count
    _driver_use_count += 1
    if _driver_use_count >= 3:
        quit_driver()

def selenium_login(email, password):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    driver = get_driver()
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    try:
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='email' i], input[placeholder*='Email']"))
        )
        email_input.clear()
        email_input.send_keys(email)
    except:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        if len(inputs) >= 1:
            inputs[0].clear()
            inputs[0].send_keys(email)
    try:
        pass_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[name='password']"))
        )
        pass_input.clear()
        pass_input.send_keys(password)
    except:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        if len(inputs) >= 2:
            inputs[1].clear()
            inputs[1].send_keys(password)
    try:
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        btn.click()
    except:
        btns = driver.find_elements(By.TAG_NAME, "button")
        for b in btns:
            if 'login' in b.text.lower() or 'sign in' in b.text.lower():
                b.click()
                break
    time.sleep(4)

def take_screenshot(filename):
    driver = get_driver()
    path = os.path.join(SCREENSHOTS_DIR, filename)
    driver.save_screenshot(path)
    return path

def save_api_response_as_screenshot(text, filename):
    """Save API response text as an image using Selenium."""
    driver = get_driver()
    # Render JSON as an HTML page and screenshot it
    truncated = text[:3000]  # limit length
    import html as htmlmod
    escaped = htmlmod.escape(truncated)
    html_content = f"""<html><head><style>
        body {{ font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; white-space: pre-wrap; word-wrap: break-word; font-size: 14px; }}
        h2 {{ color: #569cd6; }}
    </style></head><body><h2>API Response</h2><pre>{escaped}</pre></body></html>"""
    # Write to temp file
    html_path = os.path.join(SCREENSHOTS_DIR, "api_resp.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    driver.get(f"file:///{html_path.replace(os.sep, '/')}")
    time.sleep(1)
    path = os.path.join(SCREENSHOTS_DIR, filename)
    driver.save_screenshot(path)
    return path

# ---------- Issue processing definitions ----------

# Map each issue to a test function that returns (screenshot_path, steps_md)
# API issues: login, call endpoint, capture response
# UI issues: navigate with selenium, capture screenshot

def process_api_issue_317():
    """Token valid after logout"""
    token, _ = api_login(ADMIN_EMAIL, ADMIN_PASS)
    # Verify token works
    s1, r1, raw1 = api_call('GET', '/users', token)
    # Logout
    s2, r2, raw2 = api_call('POST', '/auth/logout', token)
    # Try using token again
    s3, r3, raw3 = api_call('GET', '/users', token)
    combined = f"Step 1 - GET /users before logout: Status {s1}\n{json.dumps(r1, indent=2)[:500]}\n\nStep 2 - POST /auth/logout: Status {s2}\n{json.dumps(r2, indent=2)[:300]}\n\nStep 3 - GET /users AFTER logout: Status {s3}\n{json.dumps(r3, indent=2)[:500]}"
    ss = save_api_response_as_screenshot(combined, "issue_317.png")
    steps = f"""## Steps to Reproduce
1. Login as Org Admin ({ADMIN_EMAIL}) via `POST {API_URL}/auth/login`
2. Verify token works: `GET {API_URL}/users` returns 200
3. Logout: `POST {API_URL}/auth/logout`
4. Use the SAME token again: `GET {API_URL}/users`

## Expected Result
After logout, the token should be invalidated. Subsequent API calls should return 401 Unauthorized.

## Actual Result
Token still works after logout. GET /users returns status {s3} instead of 401.

## API Request
- Method: POST (logout), then GET (verify)
- Endpoint: /api/v1/auth/logout, then /api/v1/users
- Headers: Authorization: Bearer [token]

## API Response
- Logout Status: {s2}
- Post-logout GET /users Status: {s3}
- Body: {json.dumps(r3, indent=2)[:300]}"""
    return ss, steps

def process_api_issue_316():
    """Employee can access /users/id"""
    token, _ = api_login(EMP_EMAIL, EMP_PASS)
    # Try accessing a few user IDs
    results = []
    for uid in [1, 2, 3, 500, 524]:
        s, r, raw = api_call('GET', f'/users/{uid}', token)
        results.append(f"GET /users/{uid}: Status {s}")
        if s == 200:
            results.append(f"  -> Exposed fields: {list(r.get('data', r).keys())[:10]}")
    combined = "\n".join(results)
    ss = save_api_response_as_screenshot(combined, "issue_316.png")
    steps = f"""## Steps to Reproduce
1. Login as Employee ({EMP_EMAIL}) via `POST {API_URL}/auth/login`
2. Call `GET {API_URL}/users/1` (or any user ID)
3. Observe that the response returns full user profile data

## Expected Result
Employee should only be able to view their own profile. Requests to other user IDs should return 403 Forbidden.

## Actual Result
Employee can access any user's profile data including sensitive fields like organization_id, role, email, etc.

## API Request
- Method: GET
- Endpoint: /api/v1/users/{{id}}
- Headers: Authorization: Bearer [employee_token]

## API Response
{combined[:500]}"""
    return ss, steps

def process_api_issue_315():
    """Employee can view all comp-off requests"""
    token, _ = api_login(EMP_EMAIL, EMP_PASS)
    s, r, raw = api_call('GET', '/leave/comp-off', token)
    summary = f"GET /leave/comp-off: Status {s}\n{json.dumps(r, indent=2)[:1500]}"
    ss = save_api_response_as_screenshot(summary, "issue_315.png")
    steps = f"""## Steps to Reproduce
1. Login as Employee ({EMP_EMAIL}) via `POST {API_URL}/auth/login`
2. Call `GET {API_URL}/leave/comp-off`
3. Observe the response contains comp-off requests from OTHER employees

## Expected Result
Employee should only see their own comp-off requests.

## Actual Result
Employee can see all comp-off requests in the organization, including those belonging to other employees. Status: {s}.

## API Request
- Method: GET
- Endpoint: /api/v1/leave/comp-off
- Headers: Authorization: Bearer [employee_token]

## API Response
- Status: {s}
- Body: {json.dumps(r, indent=2)[:400]}"""
    return ss, steps

def process_api_issue_313():
    """Stored XSS in /policies"""
    token, _ = api_login(ADMIN_EMAIL, ADMIN_PASS)
    xss_payload = '<script>alert("XSS")</script><img src=x onerror=alert(1)>'
    body = {"title": xss_payload, "content": xss_payload, "status": "draft"}
    s, r, raw = api_call('POST', '/policies', token, body)
    # Also try GET to verify it's stored
    s2, r2, raw2 = api_call('GET', '/policies', token)
    combined = f"POST /policies with XSS payload: Status {s}\n{json.dumps(r, indent=2)[:600]}\n\nGET /policies: Status {s2}\n{json.dumps(r2, indent=2)[:800]}"
    ss = save_api_response_as_screenshot(combined, "issue_313.png")
    steps = f"""## Steps to Reproduce
1. Login as Org Admin ({ADMIN_EMAIL}) via `POST {API_URL}/auth/login`
2. Create policy with XSS payload: `POST {API_URL}/policies`
3. Body: `{{"title": "<script>alert(\\"XSS\\")</script>", "content": "<script>alert(\\"XSS\\")</script>"}}`
4. Retrieve policies: `GET {API_URL}/policies`
5. Observe the XSS payload is stored and returned without sanitization

## Expected Result
The API should sanitize or reject HTML/JavaScript in input fields. Script tags should be stripped or escaped.

## Actual Result
The XSS payload is accepted and stored as-is. When retrieved, the unsanitized HTML/JS is returned, creating a stored XSS vulnerability.

## API Request
- Method: POST
- Endpoint: /api/v1/policies
- Headers: Authorization: Bearer [admin_token], Content-Type: application/json
- Body: {{"title": "<script>alert(\\"XSS\\")</script>", "content": "<script>alert(\\"XSS\\")</script>"}}

## API Response
- Status: {s}
- Body: {json.dumps(r, indent=2)[:400]}"""
    return ss, steps

def process_api_issue_287():
    """Employee can view draft surveys"""
    token, _ = api_login(EMP_EMAIL, EMP_PASS)
    s, r, raw = api_call('GET', '/surveys', token)
    # Find drafts
    surveys = r.get('data', r) if isinstance(r, dict) else r
    if isinstance(surveys, dict):
        surveys = surveys.get('surveys', surveys.get('items', []))
    drafts = [sv for sv in (surveys if isinstance(surveys, list) else []) if sv.get('status') == 'draft']
    combined = f"GET /surveys as employee: Status {s}\nTotal surveys: {len(surveys) if isinstance(surveys, list) else 'N/A'}\nDraft surveys visible: {len(drafts)}\n\n{json.dumps(drafts[:3], indent=2)[:800]}"
    ss = save_api_response_as_screenshot(combined, "issue_287.png")
    steps = f"""## Steps to Reproduce
1. Login as Employee ({EMP_EMAIL}) via `POST {API_URL}/auth/login`
2. Call `GET {API_URL}/surveys`
3. Filter results by status = "draft"
4. Observe that draft surveys (admin-only) are visible to the employee

## Expected Result
Employees should only see published surveys. Draft surveys should not be accessible to non-admin users.

## Actual Result
Employee can see all surveys including draft surveys. {len(drafts)} draft survey(s) visible.

## API Request
- Method: GET
- Endpoint: /api/v1/surveys
- Headers: Authorization: Bearer [employee_token]

## API Response
- Status: {s}
- Drafts visible: {len(drafts)}"""
    return ss, steps

def process_api_issue_286():
    """Employee can view other employees' leave applications"""
    token, _ = api_login(EMP_EMAIL, EMP_PASS)
    s, r, raw = api_call('GET', '/leave/applications', token)
    combined = f"GET /leave/applications as employee: Status {s}\n{json.dumps(r, indent=2)[:1500]}"
    ss = save_api_response_as_screenshot(combined, "issue_286.png")
    steps = f"""## Steps to Reproduce
1. Login as Employee ({EMP_EMAIL}, user ID 524) via `POST {API_URL}/auth/login`
2. Call `GET {API_URL}/leave/applications`
3. Observe that leave applications from OTHER employees are visible

## Expected Result
Employee should only see their own leave applications.

## Actual Result
Employee can see all leave applications in the organization, including those belonging to other employees. Status: {s}.

## API Request
- Method: GET
- Endpoint: /api/v1/leave/applications
- Headers: Authorization: Bearer [employee_token]

## API Response
- Status: {s}
- Body: {json.dumps(r, indent=2)[:400]}"""
    return ss, steps

def process_api_issue_285():
    """SQL injection payload stored in /assets"""
    token, _ = api_login(ADMIN_EMAIL, ADMIN_PASS)
    sqli_payload = "'; DROP TABLE users; --"
    body = {"name": sqli_payload, "category_id": 1, "serial_number": f"SQLI-TEST-{int(time.time())}", "status": "available"}
    s, r, raw = api_call('POST', '/assets', token, body)
    combined = f"POST /assets with SQL injection payload: Status {s}\n{json.dumps(r, indent=2)[:800]}"
    ss = save_api_response_as_screenshot(combined, "issue_285.png")
    steps = f"""## Steps to Reproduce
1. Login as Org Admin ({ADMIN_EMAIL}) via `POST {API_URL}/auth/login`
2. Create asset with SQL injection payload: `POST {API_URL}/assets`
3. Body: `{{"name": "'; DROP TABLE users; --", "category_id": 1, "serial_number": "SQLI-TEST-001", "status": "available"}}`
4. Observe the payload is stored without sanitization

## Expected Result
The API should sanitize or reject SQL injection payloads. Input should be parameterized/escaped.

## Actual Result
The SQL injection payload is accepted and stored as-is in the database. Status: {s}.

## API Request
- Method: POST
- Endpoint: /api/v1/assets
- Headers: Authorization: Bearer [admin_token], Content-Type: application/json
- Body: {{"name": "'; DROP TABLE users; --", "category_id": 1, "serial_number": "SQLI-TEST-001", "status": "available"}}

## API Response
- Status: {s}
- Body: {json.dumps(r, indent=2)[:400]}"""
    return ss, steps

def process_api_issue_284():
    """Stored XSS in /assets"""
    token, _ = api_login(ADMIN_EMAIL, ADMIN_PASS)
    xss_payload = '<script>alert("XSS")</script><img src=x onerror=alert(1)>'
    body = {"name": xss_payload, "category_id": 1, "serial_number": f"XSS-TEST-{int(time.time())}", "status": "available"}
    s, r, raw = api_call('POST', '/assets', token, body)
    combined = f"POST /assets with XSS payload: Status {s}\n{json.dumps(r, indent=2)[:800]}"
    ss = save_api_response_as_screenshot(combined, "issue_284.png")
    steps = f"""## Steps to Reproduce
1. Login as Org Admin ({ADMIN_EMAIL}) via `POST {API_URL}/auth/login`
2. Create asset with XSS payload: `POST {API_URL}/assets`
3. Body: `{{"name": "<script>alert(\\"XSS\\")</script>", "category_id": 1}}`
4. Observe the payload is stored and returned unsanitized

## Expected Result
The API should sanitize or reject HTML/JavaScript in input fields.

## Actual Result
The XSS payload is accepted and stored as-is. Status: {s}.

## API Request
- Method: POST
- Endpoint: /api/v1/assets
- Headers: Authorization: Bearer [admin_token], Content-Type: application/json
- Body: {{"name": "<script>alert(\\"XSS\\")</script><img src=x onerror=alert(1)>", "category_id": 1}}

## API Response
- Status: {s}
- Body: {json.dumps(r, indent=2)[:400]}"""
    return ss, steps

def process_api_issue_272():
    """XSS in /announcements"""
    token, _ = api_login(ADMIN_EMAIL, ADMIN_PASS)
    xss_payload = '<script>alert("XSS")</script><img src=x onerror=alert(1)>'
    body = {"name": xss_payload, "title": xss_payload, "description": xss_payload, "target": "all"}
    s, r, raw = api_call('POST', '/announcements', token, body)
    combined = f"POST /announcements with XSS payload: Status {s}\n{json.dumps(r, indent=2)[:800]}"
    ss = save_api_response_as_screenshot(combined, "issue_272.png")
    steps = f"""## Steps to Reproduce
1. Login as Org Admin ({ADMIN_EMAIL}) via `POST {API_URL}/auth/login`
2. Create announcement with XSS payload: `POST {API_URL}/announcements`
3. Body: `{{"name": "<script>alert(\\"XSS\\")</script>", "title": "<script>alert(\\"XSS\\")</script>"}}`
4. Observe the payload is stored without sanitization

## Expected Result
The API should sanitize or reject HTML/JavaScript in input fields.

## Actual Result
The XSS payload is accepted and stored as-is. Status: {s}.

## API Request
- Method: POST
- Endpoint: /api/v1/announcements
- Headers: Authorization: Bearer [admin_token], Content-Type: application/json
- Body: {{"name": "<script>alert(\\"XSS\\")</script>", "title": "<script>alert(\\"XSS\\")</script>"}}

## API Response
- Status: {s}
- Body: {json.dumps(r, indent=2)[:400]}"""
    return ss, steps

# UI issues
def process_ui_issue_31():
    """Whistleblowing dropdown error"""
    selenium_login(ADMIN_EMAIL, ADMIN_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/whistleblowing")
    time.sleep(3)
    ss = take_screenshot("issue_31.png")
    # Try to navigate to all reports
    try:
        from selenium.webdriver.common.by import By
        links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Report")
        if links:
            links[0].click()
            time.sleep(2)
        ss = take_screenshot("issue_31.png")
    except:
        pass
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Org Admin ({ADMIN_EMAIL})
3. Navigate to Whistleblowing module > All Reports
4. Select a specific case/report
5. Attempt to assign an investigator using the dropdown

## Expected Result
The investigator dropdown should display a list of available users to assign as investigators.

## Actual Result
The dropdown for assigning an investigator has a UI issue - it does not function correctly or displays an error."""
    return ss, steps

def process_ui_issue_28():
    """Dashboard and Self Service same page"""
    selenium_login(EMP_EMAIL, EMP_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/dashboard")
    time.sleep(3)
    ss1 = take_screenshot("issue_28_dashboard.png")
    driver.get(f"{BASE_URL}/self-service")
    time.sleep(3)
    ss2 = take_screenshot("issue_28.png")
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Employee ({EMP_EMAIL})
3. Click on "Dashboard" in the sidebar - observe the page content
4. Click on "Self Service" in the sidebar - observe the page content
5. Compare both pages

## Expected Result
Dashboard and Self Service should show different content. Dashboard should show an overview/summary, while Self Service should show employee self-service options.

## Actual Result
Both "Dashboard" and "Self Service" display the same page/content in the Employee Dashboard."""
    return ss2, steps

def process_ui_issue_27():
    """Empcode column missing in CSV import"""
    selenium_login(ADMIN_EMAIL, ADMIN_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/users")
    time.sleep(3)
    ss = take_screenshot("issue_27.png")
    # Try to find import button
    try:
        from selenium.webdriver.common.by import By
        btns = driver.find_elements(By.XPATH, "//*[contains(text(), 'Import') or contains(text(), 'CSV')]")
        if btns:
            btns[0].click()
            time.sleep(2)
            ss = take_screenshot("issue_27.png")
    except:
        pass
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Org Admin ({ADMIN_EMAIL})
3. Navigate to Users module
4. Click "Import CSV" option
5. Download the CSV template
6. Observe the columns in the template

## Expected Result
The CSV template should contain an "empcode" column so that imported users have their employee codes set correctly.

## Actual Result
The CSV template does not contain the empcode column, resulting in missing employee codes for all users imported via this method."""
    return ss, steps

def process_ui_issue_24():
    """Announcement target asks for JSON array"""
    selenium_login(ADMIN_EMAIL, ADMIN_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/announcements")
    time.sleep(3)
    # Try to create announcement
    try:
        from selenium.webdriver.common.by import By
        btns = driver.find_elements(By.XPATH, "//*[contains(text(), 'Create') or contains(text(), 'Add') or contains(text(), 'New')]")
        if btns:
            btns[0].click()
            time.sleep(2)
    except:
        pass
    ss = take_screenshot("issue_24.png")
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Org Admin ({ADMIN_EMAIL})
3. Navigate to Announcements
4. Click "Create Announcement"
5. Select a targeted audience (departments or roles)
6. Observe the "Target IDs" field

## Expected Result
The Target IDs field should provide a user-friendly dropdown or multi-select to choose departments/roles, not require manual JSON input.

## Actual Result
The Target IDs field asks users to enter JSON arrays (e.g., [1, 2, 3]) for target IDs, which is not user-friendly and error-prone."""
    return ss, steps

def process_ui_issue_23():
    """Forum posts not visible after creation"""
    selenium_login(ADMIN_EMAIL, ADMIN_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/forum")
    time.sleep(3)
    ss = take_screenshot("issue_23.png")
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Org Admin ({ADMIN_EMAIL})
3. Navigate to Forum / Community section
4. Create a new post
5. Return to the Forum dashboard
6. Observe the post count and post list

## Expected Result
Newly created posts should be visible and clickable on the forum dashboard.

## Actual Result
After creating a post, the post count updates (shows correct number) but the posts are not visible or clickable on the forum dashboard."""
    return ss, steps

def process_ui_issue_18():
    """Sidebar selection not retained"""
    selenium_login(ADMIN_EMAIL, ADMIN_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/dashboard")
    time.sleep(3)
    # Click a sidebar item
    try:
        from selenium.webdriver.common.by import By
        sidebar_items = driver.find_elements(By.CSS_SELECTOR, "nav a, .sidebar a, aside a")
        if len(sidebar_items) > 3:
            sidebar_items[3].click()
            time.sleep(2)
    except:
        pass
    ss = take_screenshot("issue_18.png")
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Org Admin ({ADMIN_EMAIL})
3. Click on any option in the left sidebar (e.g., Users, Leave, etc.)
4. Observe the sidebar after the page loads

## Expected Result
The selected sidebar item should remain highlighted/active, and the sidebar scroll position should be maintained.

## Actual Result
After clicking a sidebar option, the correct page opens but the sidebar does not retain the selected/active state. It resets and scrolls back to the top, appearing as if the sidebar has reloaded."""
    return ss, steps

def process_ui_issue_16():
    """Category dropdown empty in Create Post / Event date validation"""
    selenium_login(ADMIN_EMAIL, ADMIN_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/events")
    time.sleep(3)
    try:
        from selenium.webdriver.common.by import By
        btns = driver.find_elements(By.XPATH, "//*[contains(text(), 'Create') or contains(text(), 'Add') or contains(text(), 'New')]")
        if btns:
            btns[0].click()
            time.sleep(2)
    except:
        pass
    ss = take_screenshot("issue_16.png")
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Org Admin ({ADMIN_EMAIL})
3. Navigate to Events Dashboard
4. Click "Create Event"
5. Set start date to a later date (e.g., 27th)
6. Set end date to an earlier date (e.g., 26th)
7. Submit the form

## Expected Result
The system should validate that end date cannot be earlier than start date and show an error message preventing event creation.

## Actual Result
The system allows creating an event with an end date earlier than the start date without any validation error. The category dropdown in the Community Create Post section is also empty."""
    return ss, steps

def process_ui_issue_15():
    """Search user not working with full name"""
    selenium_login(ADMIN_EMAIL, ADMIN_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/recruit/vacancies")
    time.sleep(3)
    ss = take_screenshot("issue_15.png")
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Org Admin ({ADMIN_EMAIL})
3. Navigate to Recruit > Vacancies
4. Click on a vacancy and select "Assign Employee"
5. In the "Search User" field, type a full name (e.g., "Priya Sharma")
6. Observe the search results

## Expected Result
The search should return matching users when searching by full name.

## Actual Result
No results are displayed when searching with a full name. The search only works with partial names or first name only."""
    return ss, steps

def process_ui_issue_12():
    """No option to delete location"""
    selenium_login(ADMIN_EMAIL, ADMIN_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/settings")
    time.sleep(3)
    # Try to navigate to location settings
    try:
        from selenium.webdriver.common.by import By
        links = driver.find_elements(By.XPATH, "//*[contains(text(), 'Location')]")
        if links:
            links[0].click()
            time.sleep(2)
    except:
        pass
    ss = take_screenshot("issue_12.png")
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Org Admin ({ADMIN_EMAIL})
3. Navigate to Settings > Location
4. Observe the location list
5. Look for a delete option for existing locations

## Expected Result
There should be a delete/remove option for each location entry, allowing admins to remove locations that are no longer needed.

## Actual Result
There is an option to add new locations but no option to delete or remove existing locations."""
    return ss, steps

def process_ui_issue_9():
    """Leave type dropdown empty"""
    selenium_login(EMP_EMAIL, EMP_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/leave")
    time.sleep(3)
    # Try to click Apply Leave
    try:
        from selenium.webdriver.common.by import By
        btns = driver.find_elements(By.XPATH, "//*[contains(text(), 'Apply') or contains(text(), 'Leave')]")
        for b in btns:
            if 'apply' in b.text.lower():
                b.click()
                time.sleep(2)
                break
    except:
        pass
    ss = take_screenshot("issue_9.png")
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Employee ({EMP_EMAIL})
3. Navigate to Leave section
4. Click "Apply Leave"
5. Click on the "Leave Type" dropdown

## Expected Result
The Leave Type dropdown should display available leave types (e.g., Casual Leave, Sick Leave, etc.).

## Actual Result
The Leave Type dropdown is visible but no options are displayed when clicking on it, preventing users from selecting a leave type and submitting a leave application."""
    return ss, steps

def process_ui_issue_2():
    """Import CSV not working"""
    selenium_login(ADMIN_EMAIL, ADMIN_PASS)
    driver = get_driver()
    driver.get(f"{BASE_URL}/users")
    time.sleep(3)
    # Try to find import button
    try:
        from selenium.webdriver.common.by import By
        btns = driver.find_elements(By.XPATH, "//*[contains(text(), 'Import') or contains(text(), 'CSV')]")
        if btns:
            btns[0].click()
            time.sleep(2)
    except:
        pass
    ss = take_screenshot("issue_2.png")
    steps = f"""## Steps to Reproduce
1. Navigate to {BASE_URL}/login
2. Login as Org Admin ({ADMIN_EMAIL})
3. Navigate to Users module
4. Click "Import CSV" button
5. Upload a valid CSV file with correct user data format
6. Observe the import result

## Expected Result
The system should successfully import user data from the valid CSV file and display the newly imported users in the user list.

## Actual Result
The Import CSV button does not import the data successfully. Despite the file format and data being correct, the system fails to process the CSV import."""
    return ss, steps

# ---------- Main ----------
ISSUE_PROCESSORS = {
    317: process_api_issue_317,
    316: process_api_issue_316,
    315: process_api_issue_315,
    313: process_api_issue_313,
    287: process_api_issue_287,
    286: process_api_issue_286,
    285: process_api_issue_285,
    284: process_api_issue_284,
    272: process_api_issue_272,
    31: process_ui_issue_31,
    28: process_ui_issue_28,
    27: process_ui_issue_27,
    24: process_ui_issue_24,
    23: process_ui_issue_23,
    18: process_ui_issue_18,
    16: process_ui_issue_16,
    15: process_ui_issue_15,
    12: process_ui_issue_12,
    9: process_ui_issue_9,
    2: process_ui_issue_2,
}

# Skip keywords
SKIP_KEYWORDS = ['rate limit', 'field force', 'biometrics', 'emp-field', 'emp-biometrics']

def should_skip(issue):
    title = (issue.get('title') or '').lower()
    body = (issue.get('body') or '').lower()
    for kw in SKIP_KEYWORDS:
        if kw in title or kw in body:
            return True
    # Skip if already has screenshot
    if 'raw.githubusercontent.com' in (issue.get('body') or ''):
        return True
    return False

def build_updated_body(issue, steps_md, screenshot_url):
    original_body = issue.get('body') or ''
    title = issue.get('title') or ''
    number = issue['number']

    # Determine if API or UI issue
    is_api = '[API]' in title or number in [317, 316, 315, 313, 287, 286, 285, 284, 272]

    new_body = f"""## Bug Description
{original_body}

{steps_md}

## Screenshot
![Bug Screenshot]({screenshot_url})

## Environment
- URL: {BASE_URL}
- Browser: Chrome (headless)
- Date: {DATE}
"""
    return new_body

def main():
    print("Fetching open issues...")
    issues = fetch_open_issues()
    print(f"Found {len(issues)} open issues")

    updated_count = 0
    skipped = []
    errors = []

    # Filter to only issues we can process
    to_process = []
    for issue in issues:
        num = issue['number']
        if should_skip(issue):
            skipped.append(f"#{num} (already has screenshot or skip keyword)")
            continue
        if num not in ISSUE_PROCESSORS:
            skipped.append(f"#{num} (no processor defined)")
            continue
        to_process.append(issue)

    print(f"Will process {len(to_process)} issues, skipping {len(skipped)}")

    batch_count = 0
    for issue in to_process:
        num = issue['number']
        title = issue.get('title', '')
        print(f"\nProcessing #{num}: {title[:70]}...")

        try:
            processor = ISSUE_PROCESSORS[num]
            screenshot_path, steps_md = processor()
            bump_driver()
            batch_count += 1

            # Upload screenshot
            print(f"  Uploading screenshot for #{num}...")
            screenshot_url = upload_screenshot(screenshot_path, num)
            print(f"  Screenshot uploaded: {screenshot_url}")

            # Build updated body
            new_body = build_updated_body(issue, steps_md, screenshot_url)

            # Update issue
            print(f"  Updating issue #{num}...")
            update_issue(num, new_body)
            print(f"Updated issue #{num} with screenshot and steps")
            updated_count += 1

            # Rate limit courtesy
            time.sleep(1)

            # Quit driver every 3 UI issues to avoid crashes
            if batch_count % 3 == 0:
                quit_driver()

        except Exception as e:
            print(f"  ERROR processing #{num}: {e}")
            traceback.print_exc()
            errors.append(f"#{num}: {e}")
            # Try to recover
            try:
                quit_driver()
            except:
                pass

    quit_driver()

    print(f"\n{'='*50}")
    print(f"Updated {updated_count} issues with screenshots")
    if skipped:
        print(f"Skipped {len(skipped)} issues")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors:
            print(f"  {e}")

if __name__ == '__main__':
    main()
