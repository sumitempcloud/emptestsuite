#!/usr/bin/env python3
"""
README vs Reality: Fetch every EmpCloud GitHub README live, parse endpoints,
test them against the running test environment, and produce a coverage report.
"""

import sys, os, json, re, time, traceback, datetime, ssl
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import urllib.request, urllib.error, urllib.parse
from collections import defaultdict

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
CORE_API    = "https://test-empcloud-api.empcloud.com/api/v1"
OUTPUT_FILE = r"C:\emptesting\simulation\readme_vs_reality.json"
SCREENSHOT_DIR = r"C:\emptesting\simulation\screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

REPOS = [
    ("EmpCloud",        "core",        CORE_API),
    ("emp-payroll",     "payroll",     "https://testpayroll-api.empcloud.com/api/v1"),
    ("emp-recruit",     "recruit",     "https://test-recruit-api.empcloud.com/api/v1"),
    ("emp-performance", "performance", "https://test-performance-api.empcloud.com/api/v1"),
    ("emp-rewards",     "rewards",     "https://test-rewards-api.empcloud.com/api/v1"),
    ("emp-exit",        "exit",        "https://test-exit-api.empcloud.com/api/v1"),
    ("emp-lms",         "lms",         "https://testlms-api.empcloud.com/api/v1"),
    ("emp-billing",     "billing",     None),
    ("emp-project",     "project",     "https://test-project-api.empcloud.com/api/v1"),
    ("emp-monitor",     "monitor",     "https://test-empmonitor-api.empcloud.com/api/v1"),
]

MODULE_FRONTEND = {
    "payroll":     "https://testpayroll.empcloud.com",
    "recruit":     "https://test-recruit.empcloud.com",
    "performance": "https://test-performance.empcloud.com",
    "rewards":     "https://test-rewards.empcloud.com",
    "exit":        "https://test-exit.empcloud.com",
    "lms":         "https://testlms.empcloud.com",
    "project":     "https://test-project.empcloud.com",
    "monitor":     "https://test-empmonitor.empcloud.com",
}

# Browser User-Agent to pass Cloudflare
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# SSL context that doesn't verify (test env)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# HTTP Helper
# ---------------------------------------------------------------------------
def http_request(url, method="GET", headers=None, data=None, timeout=20):
    """Generic HTTP helper returning (status_code, body_dict_or_str, error_str)."""
    hdrs = dict(headers or {})
    hdrs.setdefault("User-Agent", UA)
    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body_bytes, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(raw), None
        except Exception:
            return resp.status, raw, None
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        try:
            body = json.loads(raw)
        except Exception:
            body = raw
        return e.code, body, str(e)
    except Exception as e:
        return 0, None, str(e)


def login_core(email, password):
    """Login to core API and return token."""
    status, body, err = http_request(
        f"{CORE_API}/auth/login",
        method="POST",
        data={"email": email, "password": password},
    )
    if status == 200 and isinstance(body, dict):
        d = body.get("data", {}) or {}
        # Token can be in data.tokens.access_token, data.tokens.accessToken, etc.
        tokens = d.get("tokens", {}) or {}
        token = (tokens.get("access_token") or tokens.get("accessToken") or tokens.get("token") or
                 d.get("token") or d.get("access_token") or d.get("accessToken") or
                 body.get("token") or body.get("access_token") or body.get("accessToken"))
        return token
    print(f"  [LOGIN FAIL] {email}: status={status} body={str(body)[:200]}")
    return None


def fetch_github_readme(repo_name):
    """Fetch raw README from GitHub."""
    url = f"https://api.github.com/repos/EmpCloud/{repo_name}/readme"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github.raw",
        "User-Agent": "EmpCloudTester/1.0",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=30, context=ctx)
        return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  [GITHUB] Could not fetch README for {repo_name}: {e.code}")
        try:
            print(f"    {e.read().decode()[:300]}")
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"  [GITHUB] Error fetching {repo_name}: {e}")
        return None


# ---------------------------------------------------------------------------
# README Parser — handles both formats:
#   1. EmpCloud core: table rows like | Name | `/api/v1/auth` | Description |
#   2. Module READMEs: section headers like ### Auth (`/api/v1/auth`)
#      followed by table rows: | POST | `/login` | Description |
# ---------------------------------------------------------------------------
def parse_readme(content, repo_name=""):
    """Parse README and return structured info with endpoints."""
    endpoints = []
    seen = set()

    def add_ep(method, path):
        key = f"{method} {path}"
        if key not in seen:
            seen.add(key)
            endpoints.append({"method": method, "path": path})

    lines = content.split('\n')

    # ------- Strategy A: Section-based parsing (module READMEs) -------
    # Two sub-formats:
    #   A1: ### Section Name (`/api/v1/base`)   -> base from header
    #   A2: "All endpoints under `/api/v1/`"    -> base = /api/v1, relative paths like `/auth/sso`
    #       ### Section Name (no base in header)
    #       | METHOD | `/path` | Description |
    section_base_re = re.compile(r'^###?\s+.*?\(`(/api/v\d+/[\w\-/]+)`\)')
    # "All endpoints under /api/v1/" or similar
    global_base_re = re.compile(r'(?:all|every)\s+endpoints?\s+(?:are\s+)?under\s+`(/api/v\d+/?)`', re.IGNORECASE)
    table_row_re = re.compile(
        r'\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`?(/[\w\-/:{}]+)`?\s*\|',
        re.IGNORECASE
    )

    current_base = None
    global_base = None
    in_api_section = False

    for line in lines:
        # Check for global base declaration
        gm = global_base_re.search(line)
        if gm:
            global_base = gm.group(1).rstrip('/')
            in_api_section = True
            continue

        # Detect ## API Endpoints section
        if re.match(r'^##\s+API\s+Endpoints', line, re.IGNORECASE):
            in_api_section = True
            continue

        # Detect end of API section (next ## that's not API)
        if re.match(r'^##\s+', line) and not re.match(r'^###', line) and in_api_section:
            if 'API' not in line and 'Endpoint' not in line:
                in_api_section = False
                current_base = None
                continue

        # Check for section header with base path
        sm = section_base_re.search(line)
        if sm:
            current_base = sm.group(1).rstrip('/')
            continue

        # Check for a new ### section without base path (reset base to global)
        if re.match(r'^###\s+', line) and '`/api/' not in line:
            if in_api_section and global_base:
                current_base = global_base  # Reset to global base for next section
            elif not in_api_section:
                current_base = None
            continue

        # Check for table rows with METHOD | endpoint
        tm = table_row_re.search(line)
        if tm:
            method = tm.group(1).upper()
            relative = tm.group(2).strip().rstrip(')')
            # Replace :param with {param}
            relative = re.sub(r':(\w+)', r'{\1}', relative)

            base = current_base or global_base
            if base:
                if relative == '/':
                    full_path = base
                elif relative.startswith('/api/v'):
                    full_path = relative  # Already absolute
                else:
                    full_path = base + relative
            else:
                # No base context — treat as absolute if starts with /api/
                if relative.startswith('/api/'):
                    full_path = relative
                else:
                    full_path = '/api/v1' + relative
            add_ep(method, full_path)

    # ------- Strategy B: Core-style table: | Name | `/api/v1/path` | Description |
    core_table_re = re.compile(
        r'\|\s*[\w\s]+\|\s*`(/api/v\d+/[\w\-/]+)`\s*\|',
    )
    for line in lines:
        cm = core_table_re.search(line)
        if cm:
            base_path = cm.group(1).rstrip('/')
            # For core, add common CRUD methods for each base path
            add_ep("GET", base_path)

    # ------- Strategy C: Inline patterns like POST /api/v1/auth/sso/validate
    inline_re = re.compile(
        r'(?:^|\s|`)(GET|POST|PUT|PATCH|DELETE)\s+(?:\w+\.com)?(/api/v\d+/[\w\-/{}:]+)',
        re.IGNORECASE
    )
    for m in inline_re.finditer(content):
        method = m.group(1).upper()
        path = m.group(2).rstrip(')')
        path = re.sub(r':(\w+)', r'{\1}', path)
        add_ep(method, path)

    # ------- Strategy D: Raw /api/v1/ paths not yet captured
    raw_path_re = re.compile(r'`(/api/v\d+/[\w\-/]+)`')
    for m in raw_path_re.finditer(content):
        path = m.group(1).rstrip('/')
        if f"GET {path}" not in seen:
            add_ep("GET", path)

    # Required fields
    required_fields = []
    req_re = re.compile(r'\|\s*`?(\w+)`?\s*\|\s*(\w+)\s*\|\s*(?:Yes|Required|true)\s*\|', re.IGNORECASE)
    for m in req_re.finditer(content):
        required_fields.append({"field": m.group(1), "type": m.group(2)})

    # Roles
    role_re = re.compile(r'(?:role|permission|access)[:\s]*(admin|hr|employee|manager|super\s*admin)', re.IGNORECASE)
    roles = list(set(m.group(1).strip().lower() for m in role_re.finditer(content)))

    # Feature sections (## headers)
    features = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)

    return {
        "endpoints": endpoints,
        "required_fields": required_fields,
        "roles": roles,
        "features": features,
        "readme_length": len(content),
    }


# ---------------------------------------------------------------------------
# Endpoint tester
# ---------------------------------------------------------------------------
def normalize_path_for_test(path):
    """Replace {param} style params with real test values."""
    path = re.sub(r'\{(organization_?id|org_?id)\}', '5', path)
    path = re.sub(r'\{(employee_?id|emp_?id|user_?id|empId)\}', '1', path)
    path = re.sub(r'\{(department_?id|dept_?id)\}', '72', path)
    path = re.sub(r'\{(id|[a-z_]+Id|[a-z_]+_id)\}', '1', path)
    path = path.split('?')[0]
    return path


def test_endpoint(base_url, method, path, token, test_data=None):
    """Test a single endpoint. Returns result dict."""
    real_path = normalize_path_for_test(path)

    # Build full URL
    if real_path.startswith('http'):
        url = real_path
    elif real_path.startswith('/api/v1'):
        suffix = real_path[len('/api/v1'):]
        url = base_url.rstrip('/') + suffix
    elif real_path.startswith('/'):
        url = base_url.rstrip('/') + real_path
    else:
        url = base_url.rstrip('/') + '/' + real_path

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None
    if method in ("POST", "PUT", "PATCH"):
        data = test_data or {}

    status, body, err = http_request(url, method=method, headers=headers, data=data, timeout=15)

    result = {
        "method": method,
        "path": path,
        "tested_url": url,
        "status": status,
        "error": err,
    }

    if status == 0:
        result["verdict"] = "unreachable"
    elif status == 404:
        result["verdict"] = "missing_404"
    elif status == 405:
        result["verdict"] = "method_not_allowed"
    elif 500 <= status < 600:
        result["verdict"] = "server_error"
    elif status in (401, 403):
        result["verdict"] = "auth_error"
    elif status == 429:
        result["verdict"] = "rate_limited"
    elif 200 <= status < 300:
        result["verdict"] = "working"
    elif status in (400, 422):
        result["verdict"] = "working_validation"
    else:
        result["verdict"] = f"other_{status}"

    if isinstance(body, dict):
        result["response_preview"] = str(body)[:300]
    elif isinstance(body, str):
        result["response_preview"] = body[:300]

    return result


# ---------------------------------------------------------------------------
# Selenium SSO helper for external modules
# ---------------------------------------------------------------------------
selenium_driver = None
selenium_count = 0

def get_selenium_driver(force_new=False):
    """Get or create a Selenium WebDriver. Restart every 2 modules."""
    global selenium_driver
    if force_new and selenium_driver:
        try:
            selenium_driver.quit()
        except Exception:
            pass
        selenium_driver = None

    if selenium_driver is None:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            opts = Options()
            opts.binary_location = CHROME_PATH
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-gpu")
            opts.add_argument(f"--user-agent={UA}")

            selenium_driver = webdriver.Chrome(options=opts)
            selenium_driver.set_page_load_timeout(30)
            selenium_driver.implicitly_wait(10)
            print("    [SELENIUM] Browser started")
        except Exception as e:
            print(f"    [SELENIUM] Failed to start: {e}")
            selenium_driver = None
    return selenium_driver


def selenium_sso_login(module_key):
    """Login via Selenium SSO: login to core, navigate to modules, launch target module."""
    driver = get_selenium_driver()
    if not driver:
        return None

    try:
        # Step 1: Go to core login page
        print("    [SSO] Navigating to core login...")
        driver.get("https://test-empcloud.empcloud.com/login")
        time.sleep(2)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # Fill login form
        try:
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
            )
            email_field.clear()
            email_field.send_keys("ananya@technova.in")

            pwd_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
            pwd_field.clear()
            pwd_field.send_keys("Welcome@123")

            # Click submit
            submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit.click()
            time.sleep(3)
        except Exception as e:
            print(f"    [SSO] Login form error: {e}")
            driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"sso_login_error_{module_key}.png"))
            return None

        # Step 2: Navigate to modules page
        print("    [SSO] Navigating to modules page...")
        driver.get("https://test-empcloud.empcloud.com/modules")
        time.sleep(2)

        # Screenshot modules page
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"modules_page_{module_key}.png"))

        # Step 3: Find and click Launch for the module
        frontend_url = MODULE_FRONTEND.get(module_key, "")
        if not frontend_url:
            return None

        # Try clicking a launch link/button for this module
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.lower()
                if frontend_url.split("//")[1].split(".")[0].replace("test-", "").replace("test", "") in href.lower() or \
                   module_key in text:
                    print(f"    [SSO] Clicking launch link: {href}")
                    link.click()
                    time.sleep(3)
                    break
        except Exception as e:
            print(f"    [SSO] Could not find launch link: {e}")
            # Try direct navigation
            driver.get(frontend_url)
            time.sleep(3)

        # Step 4: Try to extract token from cookies or localStorage
        current_url = driver.current_url
        print(f"    [SSO] Current URL after SSO: {current_url}")
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"sso_landed_{module_key}.png"))

        # Try extracting token from localStorage
        try:
            token = driver.execute_script(
                "return localStorage.getItem('token') || localStorage.getItem('access_token') || "
                "localStorage.getItem('auth_token') || sessionStorage.getItem('token') || "
                "sessionStorage.getItem('access_token') || '';"
            )
            if token:
                print(f"    [SSO] Got token from storage: {token[:20]}...")
                return token
        except Exception:
            pass

        # Try from cookies
        cookies = driver.get_cookies()
        for c in cookies:
            if 'token' in c['name'].lower():
                print(f"    [SSO] Got token from cookie {c['name']}: {c['value'][:20]}...")
                return c['value']

        print("    [SSO] Could not extract token from browser")
        return None

    except Exception as e:
        print(f"    [SSO] Error: {e}")
        try:
            driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"sso_error_{module_key}.png"))
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Bug filing helper
# ---------------------------------------------------------------------------
bugs_found = []

def file_bug(module, title, description):
    """Record a bug (print and collect)."""
    bug = {
        "module": module,
        "title": f"[30-Day Sim] {title}",
        "description": description,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    bugs_found.append(bug)
    print(f"  [BUG] {bug['title']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global selenium_count

    print("=" * 70)
    print("README vs REALITY -- EmpCloud Full Module Test")
    print(f"Started: {datetime.datetime.now().isoformat()}")
    print("=" * 70)

    # Login to get core token
    print("\n[AUTH] Logging in as TechNova admin...")
    core_token = login_core("ananya@technova.in", "Welcome@123")
    if core_token:
        print(f"  Token obtained: {core_token[:20]}...")
    else:
        print("  FATAL: Could not get core token")
        return

    all_results = {}
    summary_lines = []
    modules_tested_with_selenium = 0

    for repo_name, module_key, api_base in REPOS:
        print(f"\n{'=' * 60}")
        print(f"MODULE: {repo_name} ({module_key})")
        print('=' * 60)

        # ----- Step 1: Fetch README live from GitHub -----
        print(f"  Fetching README from GitHub...")
        readme = fetch_github_readme(repo_name)
        if not readme:
            print(f"  SKIPPED: No README available")
            all_results[module_key] = {
                "repo": repo_name,
                "readme_fetched": False,
                "error": "Could not fetch README from GitHub",
            }
            summary_lines.append(f"=== {module_key} === SKIPPED (no README)")
            continue

        print(f"  README fetched: {len(readme)} chars")

        # ----- Step 2: Parse README -----
        parsed = parse_readme(readme, repo_name)
        ep_count = len(parsed["endpoints"])
        print(f"  Endpoints found: {ep_count}")
        print(f"  Required fields: {len(parsed['required_fields'])}")
        print(f"  Roles mentioned: {parsed['roles']}")
        print(f"  Feature sections: {len(parsed['features'])}")

        if parsed["features"]:
            for f in parsed["features"][:10]:
                print(f"    - {f}")

        if ep_count > 0:
            print(f"  Sample endpoints:")
            for ep in parsed["endpoints"][:8]:
                print(f"    {ep['method']} {ep['path']}")
            if ep_count > 8:
                print(f"    ... and {ep_count - 8} more")

        # ----- Step 3: Test endpoints -----
        if not api_base:
            print(f"  No API base URL configured (internal module), skipping endpoint tests")
            all_results[module_key] = {
                "repo": repo_name,
                "readme_fetched": True,
                "readme_chars": len(readme),
                "parsed": {
                    "endpoint_count": ep_count,
                    "required_fields": parsed["required_fields"],
                    "roles": parsed["roles"],
                    "features": parsed["features"],
                },
                "note": "No API base -- internal module",
            }
            summary_lines.append(f"=== {module_key} === Internal module, no API testing")
            continue

        # Determine the auth token to use
        token = core_token

        if module_key != "core":
            # Try direct login to module API first
            print(f"  Attempting module login at {api_base}...")
            login_url = f"{api_base}/auth/login"
            s, b, e = http_request(
                login_url, method="POST",
                data={"email": "ananya@technova.in", "password": "Welcome@123"},
                timeout=15,
            )
            if s == 200 and isinstance(b, dict):
                d = (b.get("data") or {})
                toks = (d.get("tokens") or {})
                mod_token = (toks.get("access_token") or toks.get("accessToken") or toks.get("token") or
                             d.get("token") or d.get("access_token") or d.get("accessToken") or
                             b.get("token") or b.get("access_token") or b.get("accessToken"))
                if mod_token:
                    token = mod_token
                    print(f"  Module token obtained: {mod_token[:20]}...")
            else:
                # Try SSO endpoint with core token
                print(f"  Direct login returned {s}. Trying SSO API...")
                sso_url = f"{api_base}/auth/sso"
                s2, b2, e2 = http_request(
                    sso_url, method="POST",
                    headers={"Authorization": f"Bearer {core_token}"},
                    data={"token": core_token},
                    timeout=15,
                )
                if s2 == 200 and isinstance(b2, dict):
                    d2 = (b2.get("data") or {})
                    toks2 = (d2.get("tokens") or {})
                    sso_token = (toks2.get("access_token") or toks2.get("accessToken") or toks2.get("token") or
                                 d2.get("token") or d2.get("access_token") or d2.get("accessToken") or
                                 b2.get("token") or b2.get("access_token") or b2.get("accessToken"))
                    if sso_token:
                        token = sso_token
                        print(f"  SSO token obtained: {sso_token[:20]}...")
                else:
                    print(f"  SSO API returned {s2}. Trying Selenium SSO...")
                    # Restart Selenium every 2 modules
                    if modules_tested_with_selenium > 0 and modules_tested_with_selenium % 2 == 0:
                        print("    [SELENIUM] Restarting browser (every 2 modules)...")
                        get_selenium_driver(force_new=True)

                    sso_token = selenium_sso_login(module_key)
                    modules_tested_with_selenium += 1
                    if sso_token:
                        token = sso_token
                    else:
                        print(f"  Using core token (may get auth errors on module endpoints)")

        # Test each endpoint
        tested = 0
        working = 0
        missing = 0
        broken = 0
        auth_err = 0
        other = 0
        endpoint_results = []

        for ep in parsed["endpoints"]:
            method = ep["method"]
            path = ep["path"]
            print(f"  Testing: {method} {path} ...", end=" ", flush=True)

            result = test_endpoint(api_base, method, path, token)
            endpoint_results.append(result)
            tested += 1

            v = result["verdict"]
            if v == "working":
                working += 1
                print(f"OK ({result['status']})")
            elif v == "working_validation":
                working += 1
                print(f"OK-validation ({result['status']})")
            elif v == "missing_404":
                missing += 1
                print(f"MISSING (404)")
                file_bug(module_key,
                         f"README says {method} {path} exists but returns 404",
                         f"Module: {repo_name}\nEndpoint: {method} {path}\n"
                         f"Tested URL: {result['tested_url']}\n"
                         f"The README documents this endpoint but it returns 404.")
            elif v == "server_error":
                broken += 1
                print(f"BROKEN ({result['status']})")
                file_bug(module_key,
                         f"{method} {path} returns server error {result['status']}",
                         f"Module: {repo_name}\nEndpoint: {method} {path}\n"
                         f"Tested URL: {result['tested_url']}\n"
                         f"Server error: {result.get('response_preview', '')[:200]}")
            elif v == "auth_error":
                auth_err += 1
                print(f"AUTH ({result['status']})")
            elif v == "rate_limited":
                other += 1
                print(f"RATE-LIMITED (429)")
            elif v == "unreachable":
                other += 1
                print(f"UNREACHABLE")
            elif v == "method_not_allowed":
                other += 1
                print(f"METHOD-NOT-ALLOWED (405)")
                file_bug(module_key,
                         f"README says {method} {path} but server returns 405",
                         f"Module: {repo_name}\nEndpoint: {method} {path}\n"
                         f"The README documents this method but the server rejects it with 405.")
            else:
                other += 1
                print(f"{v} ({result['status']})")

            time.sleep(0.15)

        # ----- Step 4: Check required fields -----
        if parsed["required_fields"] and token:
            print(f"\n  Checking required field validation...")
            post_eps = [ep for ep in parsed["endpoints"] if ep["method"] == "POST"]
            for ep in post_eps[:3]:
                result_empty = test_endpoint(api_base, "POST", ep["path"], token, {})
                if result_empty["verdict"] == "working":
                    for rf in parsed["required_fields"][:5]:
                        file_bug(module_key,
                                 f"README says {rf['field']} is required for {ep['path']} but API accepts without it",
                                 f"Module: {repo_name}\nEndpoint: POST {ep['path']}\n"
                                 f"Field: {rf['field']} (type: {rf['type']})\n"
                                 f"Sending empty body returns 200, so required field validation is missing.")
                        break
                time.sleep(0.1)

        # Coverage = working / tested
        coverage = (working / tested * 100) if tested > 0 else 0

        module_result = {
            "repo": repo_name,
            "readme_fetched": True,
            "readme_chars": len(readme),
            "parsed": {
                "endpoint_count": ep_count,
                "required_fields": parsed["required_fields"],
                "roles": parsed["roles"],
                "features": parsed["features"],
            },
            "test_results": {
                "endpoints_in_readme": ep_count,
                "endpoints_tested": tested,
                "working": working,
                "missing_404": missing,
                "broken_500": broken,
                "auth_errors": auth_err,
                "other": other,
                "coverage_pct": round(coverage, 1),
            },
            "endpoint_details": endpoint_results,
        }
        all_results[module_key] = module_result

        summary = (
            f"=== {module_key} ({repo_name}) ===\n"
            f"  Endpoints in README: {ep_count}\n"
            f"  Endpoints tested:    {tested}\n"
            f"  Working:             {working}\n"
            f"  Missing (404):       {missing}\n"
            f"  Broken (5xx):        {broken}\n"
            f"  Auth errors:         {auth_err}\n"
            f"  Other:               {other}\n"
            f"  Coverage:            {coverage:.1f}%"
        )
        summary_lines.append(summary)
        print(f"\n{summary}")

    # Close Selenium
    global selenium_driver
    if selenium_driver:
        try:
            selenium_driver.quit()
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # Step 5: Print final coverage report
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("FINAL COVERAGE REPORT")
    print("=" * 70)

    total_in_readme = 0
    total_tested = 0
    total_working = 0
    total_missing = 0
    total_broken = 0

    for line in summary_lines:
        print(line)

    for mk, mr in all_results.items():
        tr = mr.get("test_results", {})
        total_in_readme += tr.get("endpoints_in_readme", 0)
        total_tested += tr.get("endpoints_tested", 0)
        total_working += tr.get("working", 0)
        total_missing += tr.get("missing_404", 0)
        total_broken += tr.get("broken_500", 0)

    overall_cov = (total_working / total_tested * 100) if total_tested > 0 else 0
    print(f"\n--- TOTALS ---")
    print(f"  Total endpoints in READMEs: {total_in_readme}")
    print(f"  Total tested:               {total_tested}")
    print(f"  Total working:              {total_working}")
    print(f"  Total missing (404):        {total_missing}")
    print(f"  Total broken (5xx):         {total_broken}")
    print(f"  Overall coverage:           {overall_cov:.1f}%")

    print(f"\n--- Bugs Found: {len(bugs_found)} ---")
    for b in bugs_found:
        print(f"  [{b['module']}] {b['title']}")

    # Save results
    output = {
        "timestamp": datetime.datetime.now().isoformat(),
        "modules": all_results,
        "bugs": bugs_found,
        "summary": summary_lines,
        "totals": {
            "endpoints_in_readmes": total_in_readme,
            "endpoints_tested": total_tested,
            "working": total_working,
            "missing_404": total_missing,
            "broken_500": total_broken,
            "overall_coverage_pct": round(overall_cov, 1),
        }
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResults saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
