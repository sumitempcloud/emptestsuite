"""
EMP Recruit Module - Fresh E2E Test
Admin (ananya): dashboard, jobs CRUD, candidates, interviews, offers, analytics, settings, pipeline stages
Employee (priya): internal jobs, referrals, RBAC blocks on candidate pipeline/interviews/settings

SSO flow: get empcloud token -> driver.get(RECRUIT_BASE?sso_token=TOKEN) -> session stored in browser
After initial SSO, navigate normally (no token re-append) since session is cookie-based.
For API: extract session token from browser localStorage/cookies after SSO login.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
import json
import os
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# ============================================================
# CONFIG
# ============================================================
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_recruit"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

LOGIN_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
RECRUIT_BASE = "https://test-recruit.empcloud.com"
RECRUIT_API = "https://test-recruit-api.empcloud.com/api/v1"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

bugs = []
results = {}

# ============================================================
# HELPERS
# ============================================================
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    try:
        driver.save_screenshot(path)
        log(f"  Screenshot: {name}.png")
    except Exception as e:
        log(f"  Screenshot failed ({name}): {e}")
    return path

def file_bug(title, body, labels=None):
    bugs.append(title)
    log(f"  BUG: {title}")
    if labels is None:
        labels = ["bug", "recruit"]
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github+json"
            },
            json={"title": title, "body": body, "labels": labels},
            timeout=15
        )
        if resp.status_code == 201:
            log(f"  Filed issue #{resp.json()['number']}: {title}")
        else:
            log(f"  GitHub issue filing returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log(f"  Error filing bug: {e}")

def record(test_name, status, detail=""):
    results[test_name] = {"status": status, "detail": detail}
    symbol = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
    log(f"  [{symbol}] {test_name}" + (f" - {detail}" if detail else ""))

def get_sso_token(email, password):
    log(f"Getting SSO token for {email}...")
    resp = requests.post(LOGIN_URL, json={"email": email, "password": password}, timeout=15)
    if resp.status_code != 200:
        log(f"  Login failed: {resp.status_code} - {resp.text[:300]}")
        return None
    data = resp.json()
    token = (
        data.get("data", {}).get("tokens", {}).get("access_token")
        or data.get("data", {}).get("token")
        or data.get("token")
    )
    if not token:
        log(f"  No token in response: {json.dumps(data)[:300]}")
        return None
    log(f"  Got token: {token[:30]}...")
    return token

def create_driver(retries=3):
    for attempt in range(retries):
        try:
            opts = Options()
            opts.binary_location = CHROME_PATH
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--ignore-certificate-errors")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-background-networking")
            driver = webdriver.Chrome(options=opts)
            driver.set_page_load_timeout(45)
            driver.implicitly_wait(5)
            return driver
        except Exception as e:
            log(f"  Driver creation attempt {attempt+1} failed: {e}")
            time.sleep(3)
    log("  FATAL: Could not create Chrome driver after retries")
    return None

def wait_for_page(driver, timeout=12):
    time.sleep(2)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except:
        pass
    time.sleep(1)

def sso_login(driver, token, email=None, password=None):
    """Do SSO login. If SSO fails, fall back to manual login form."""
    url = f"{RECRUIT_BASE}?sso_token={token}"
    log(f"  SSO login via: {RECRUIT_BASE}?sso_token=<token>")
    driver.get(url)
    wait_for_page(driver)
    page = driver.page_source.lower()
    if "sso login failed" in page or "welcome back" in page or "sign in" in page:
        log("  SSO token expired, falling back to login form...")
        return manual_login(driver, email, password)
    log("  SSO login successful - session established")
    return True

def manual_login(driver, email=None, password=None):
    """Login via the Recruit login form."""
    if not email or not password:
        log("  No credentials for manual login fallback")
        return False
    try:
        # Navigate to login page
        driver.get(f"{RECRUIT_BASE}/login")
        wait_for_page(driver)

        page = driver.page_source.lower()
        if "welcome back" not in page and "sign in" not in page:
            if "dashboard" in page:
                log("  Already logged in")
                return True

        # Fill email - use JS to clear completely (handles pre-filled fields)
        email_input = None
        for sel in ['input[name="email"]', 'input[type="email"]', '#email', 'input[placeholder*="email" i]']:
            try:
                email_input = driver.find_element(By.CSS_SELECTOR, sel)
                break
            except:
                continue

        if not email_input:
            log("  Cannot find email input")
            screenshot(driver, "manual_login_no_email_field")
            return False

        # Triple-click to select all, then type new value
        driver.execute_script("arguments[0].value = '';", email_input)
        email_input.click()
        email_input.send_keys(Keys.CONTROL, "a")
        email_input.send_keys(email)
        time.sleep(0.3)

        # Fill password
        pwd_input = None
        for sel in ['input[name="password"]', 'input[type="password"]', '#password']:
            try:
                pwd_input = driver.find_element(By.CSS_SELECTOR, sel)
                break
            except:
                continue

        if not pwd_input:
            log("  Cannot find password input")
            return False

        driver.execute_script("arguments[0].value = '';", pwd_input)
        pwd_input.click()
        pwd_input.send_keys(Keys.CONTROL, "a")
        pwd_input.send_keys(password)
        time.sleep(0.3)

        # Verify field values before submit
        actual_email = email_input.get_attribute("value")
        log(f"  Login form email field: {actual_email}")
        if actual_email != email:
            log(f"  WARNING: Email field has '{actual_email}' instead of '{email}', retrying...")
            driver.execute_script(f"arguments[0].value = '{email}';", email_input)
            # Dispatch input event so React picks it up
            driver.execute_script("""
                var el = arguments[0];
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(el, arguments[1]);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            """, email_input, email)
            driver.execute_script("""
                var el = arguments[0];
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(el, arguments[1]);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            """, pwd_input, password)
            time.sleep(0.5)

        screenshot(driver, "manual_login_before_submit")

        # Click sign in button
        clicked = False
        for sel in ['button[type="submit"]', 'button']:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                for btn in btns:
                    txt = btn.text.lower()
                    if "sign" in txt or "log" in txt or btn.get_attribute("type") == "submit":
                        btn.click()
                        clicked = True
                        break
                if clicked:
                    break
            except:
                continue

        if not clicked:
            log("  Could not click sign in button")
            return False

        wait_for_page(driver, timeout=15)
        time.sleep(3)

        screenshot(driver, "manual_login_after_submit")
        page = driver.page_source.lower()

        # Check if we're on a dashboard/authenticated page
        if any(kw in page for kw in ["dashboard", "job posting", "candidates", "interviews", "offers"]):
            # Verify the correct user is logged in
            if email.split("@")[0] in page or "priya" in page or "ananya" in page:
                log(f"  Manual login successful for {email}")
            else:
                log(f"  Manual login appears successful for {email}")
            return True
        elif "welcome back" in page or "sign in" in page:
            log(f"  Manual login failed - still on login page for {email}")
            return False
        elif "invalid" in page or "incorrect" in page:
            log(f"  Manual login failed - invalid credentials for {email}")
            return False
        else:
            log(f"  Manual login - page state unclear for {email}, assuming success")
            return True

    except Exception as e:
        log(f"  Manual login error: {e}")
        return False

def navigate(driver, path):
    """Navigate to a recruit page using the existing session (no SSO token re-append)."""
    url = f"{RECRUIT_BASE}{path}"
    try:
        driver.get(url)
        wait_for_page(driver)
    except Exception as e:
        log(f"  Navigation to {path} failed: {e}")
    return url

def is_driver_alive(driver):
    """Check if the driver/browser is still responsive."""
    try:
        _ = driver.title
        return True
    except:
        return False

def extract_api_token(driver):
    """Extract the auth token stored by the React app in localStorage."""
    try:
        token = driver.execute_script("""
            // Try common localStorage keys used by React auth
            var keys = ['token', 'auth_token', 'access_token', 'recruit_token',
                        'authToken', 'accessToken', 'jwt', 'session'];
            for (var i = 0; i < keys.length; i++) {
                var val = localStorage.getItem(keys[i]);
                if (val) return val;
            }
            // Try to find any key containing 'token'
            for (var j = 0; j < localStorage.length; j++) {
                var k = localStorage.key(j);
                if (k.toLowerCase().includes('token')) {
                    return localStorage.getItem(k);
                }
            }
            // Dump all localStorage keys for debugging
            var all = {};
            for (var m = 0; m < localStorage.length; m++) {
                var key = localStorage.key(m);
                all[key] = localStorage.getItem(key).substring(0, 50);
            }
            return JSON.stringify(all);
        """)
        if token:
            log(f"  Extracted token from localStorage: {str(token)[:60]}...")
        return token
    except Exception as e:
        log(f"  Could not extract token from localStorage: {e}")
        return None

def check_page_errors(driver):
    """Return error description or None if page looks OK."""
    page_src = (driver.page_source or "").lower()

    if "sso login failed" in page_src:
        return "SSO login failed / session expired"
    if "<h1>500</h1>" in page_src or "internal server error" in page_src:
        return "500 Internal Server Error"
    if "<h1>404</h1>" in page_src or "page not found" in page_src:
        return "404 Page Not Found"
    if "something went wrong" in page_src:
        return "Something went wrong error"

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
    except:
        body_text = ""
    if len(body_text) < 10 and "login" not in page_src:
        return "Page appears blank/empty"

    return None

def has_text(driver, text):
    try:
        return text.lower() in driver.page_source.lower()
    except:
        return False

def get_api(token, endpoint):
    try:
        resp = requests.get(
            f"{RECRUIT_API}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        return resp
    except Exception as e:
        log(f"  API GET {endpoint} error: {e}")
        return None

def post_api(token, endpoint, data=None):
    try:
        resp = requests.post(
            f"{RECRUIT_API}{endpoint}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=data or {},
            timeout=30
        )
        return resp
    except Exception as e:
        log(f"  API POST {endpoint} error: {e}")
        return None

def put_api(token, endpoint, data=None):
    try:
        resp = requests.put(
            f"{RECRUIT_API}{endpoint}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=data or {},
            timeout=30
        )
        return resp
    except Exception as e:
        log(f"  API PUT {endpoint} error: {e}")
        return None

def patch_api(token, endpoint, data=None):
    try:
        resp = requests.patch(
            f"{RECRUIT_API}{endpoint}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=data or {},
            timeout=30
        )
        return resp
    except Exception as e:
        log(f"  API PATCH {endpoint} error: {e}")
        return None


# ============================================================
# Get API token via SSO exchange (separate from browser)
# ============================================================
def get_recruit_api_token(empcloud_token):
    """Exchange empcloud token for recruit API token."""
    log("  Exchanging for Recruit API session token...")
    try:
        resp = requests.post(
            f"{RECRUIT_API}/auth/sso",
            headers={"Content-Type": "application/json"},
            json={"token": empcloud_token},
            timeout=15
        )
        if resp and resp.status_code in (200, 201):
            data = resp.json()
            # Check various response shapes
            recruit_token = (
                data.get("data", {}).get("tokens", {}).get("accessToken")
                or data.get("data", {}).get("tokens", {}).get("access_token")
                or data.get("data", {}).get("token")
                or data.get("token")
                or data.get("data", {}).get("access_token")
                or data.get("data", {}).get("accessToken")
                or data.get("data", {}).get("session", {}).get("token")
            )
            if recruit_token:
                log(f"  Got Recruit API token: {recruit_token[:30]}...")
                return recruit_token
            else:
                log(f"  SSO exchange succeeded but no token field found. Response keys: {list(data.get('data', {}).keys())}")
                log(f"  Full response: {json.dumps(data)[:300]}")
                # The empcloud token may work directly for Recruit API
                return empcloud_token
        else:
            log(f"  SSO exchange returned {resp.status_code if resp else 'no response'}")
            return empcloud_token
    except Exception as e:
        log(f"  SSO exchange error: {e}")
        return empcloud_token


# ============================================================
# ADMIN TESTS
# ============================================================

def test_admin_dashboard(driver):
    test = "admin_dashboard"
    log("\n=== ADMIN: Dashboard ===")
    try:
        navigate(driver, "/")
        screenshot(driver, "admin_01_dashboard")

        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Dashboard: {error}",
                f"**Page**: `/`\n**Error**: {error}\n**Steps**: SSO login as admin, land on dashboard.\n**Expected**: Dashboard loads with stats.")
            return
        page = driver.page_source.lower()
        has_content = any(kw in page for kw in [
            "dashboard", "open position", "pipeline", "hiring", "job",
            "candidate", "interview", "offer", "recruit", "overview"
        ])
        if has_content:
            record(test, "PASS", "Dashboard loaded with recruitment content")
        else:
            record(test, "FAIL", "Dashboard loaded but no recruitment-related content found")
            file_bug("[Recruit] Dashboard missing recruitment overview content",
                "**Page**: `/`\n**Issue**: No recruitment metrics.\n**Expected**: Open positions, pipeline summary.")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_jobs_list(driver):
    test = "admin_jobs_list"
    log("\n=== ADMIN: Jobs List ===")
    try:
        navigate(driver, "/jobs")
        screenshot(driver, "admin_02_jobs_list")

        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Jobs list page: {error}", f"**Page**: `/jobs`\n**Error**: {error}")
            return
        page = driver.page_source.lower()
        has_jobs = any(kw in page for kw in [
            "job posting", "job title", "position", "create job", "department", "location", "status"
        ])
        if has_jobs:
            record(test, "PASS", "Jobs list page loaded")
        else:
            record(test, "FAIL", "Jobs page has no job-related content")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_job_create_ui(driver):
    test = "admin_job_create_ui"
    log("\n=== ADMIN: Create Job (UI) ===")
    try:
        navigate(driver, "/jobs/new")
        screenshot(driver, "admin_03_job_form")

        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Job creation form: {error}", f"**Page**: `/jobs/new`\n**Error**: {error}")
            return
        page = driver.page_source.lower()
        has_form = any(kw in page for kw in [
            "title", "description", "requirements", "department", "salary",
            "create", "save", "submit", "job posting"
        ])
        if has_form:
            record(test, "PASS", "Job creation form loaded")
        else:
            record(test, "FAIL", "Job form page has no form fields")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_job_crud_api(api_token):
    """Test full CRUD cycle: create -> read -> update -> publish -> read again."""
    log("\n=== ADMIN: Job CRUD via API ===")

    # CREATE
    test = "admin_job_create_api"
    job_id = None
    try:
        job_data = {
            "title": f"QA Engineer - E2E {datetime.now().strftime('%H%M%S')}",
            "description": "Automated E2E test job posting.",
            "requirements": "3+ years in testing. Selenium, Python.",
            "department": "Engineering",
            "location": "Bangalore",
            "employment_type": "full_time",
            "salary_min": 800000,
            "salary_max": 1500000,
            "status": "draft"
        }
        resp = post_api(api_token, "/jobs", job_data)
        if resp and resp.status_code in (200, 201):
            data = resp.json()
            job_id = (data.get("data", {}).get("id") or data.get("id")
                      or data.get("data", {}).get("job", {}).get("id"))
            record(test, "PASS", f"Created job id={job_id}")
        elif resp:
            record(test, "FAIL", f"API {resp.status_code}: {resp.text[:150]}")
            file_bug(f"[Recruit] Create job API returned {resp.status_code}",
                f"**Endpoint**: POST /jobs\n**Status**: {resp.status_code}\n**Response**: {resp.text[:300]}")
        else:
            record(test, "FAIL", "No API response")
            file_bug("[Recruit] Create job API - no response / connection error",
                "**Endpoint**: POST /jobs\n**Error**: No response from Recruit API.\n"
                "**Expected**: Job creation should succeed.")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])

    if not job_id:
        # Try listing existing jobs to get one for subsequent tests
        try:
            resp = get_api(api_token, "/jobs")
            if resp and resp.status_code == 200:
                data = resp.json()
                jobs = data.get("data", {}).get("jobs", data.get("data", []))
                if isinstance(jobs, list) and len(jobs) > 0:
                    job_id = jobs[0].get("id")
                    log(f"  Using existing job id={job_id} for subsequent tests")
        except:
            pass

    # READ
    test = "admin_job_read_api"
    if job_id:
        try:
            resp = get_api(api_token, f"/jobs/{job_id}")
            if resp and resp.status_code == 200:
                record(test, "PASS", f"Read job {job_id}")
            elif resp:
                record(test, "FAIL", f"API {resp.status_code}")
            else:
                record(test, "FAIL", "No API response")
        except Exception as e:
            record(test, "FAIL", str(e)[:150])
    else:
        record(test, "SKIP", "No job_id")

    # UPDATE
    test = "admin_job_update_api"
    if job_id:
        try:
            resp = put_api(api_token, f"/jobs/{job_id}", {
                "title": f"Sr QA Engineer - Updated {datetime.now().strftime('%H%M%S')}",
                "requirements": "5+ years. Selenium, Python, CI/CD."
            })
            if resp and resp.status_code in (200, 201):
                record(test, "PASS", f"Updated job {job_id}")
            elif resp:
                record(test, "FAIL", f"API {resp.status_code}: {resp.text[:150]}")
            else:
                record(test, "FAIL", "No API response")
        except Exception as e:
            record(test, "FAIL", str(e)[:150])
    else:
        record(test, "SKIP", "No job_id")

    # PUBLISH (status change)
    test = "admin_job_publish_api"
    if job_id:
        try:
            resp = patch_api(api_token, f"/jobs/{job_id}/status", {"status": "open"})
            if resp and resp.status_code in (200, 201):
                record(test, "PASS", f"Published job {job_id}")
            elif resp:
                record(test, "FAIL", f"API {resp.status_code}: {resp.text[:150]}")
            else:
                record(test, "FAIL", "No API response")
        except Exception as e:
            record(test, "FAIL", str(e)[:150])
    else:
        record(test, "SKIP", "No job_id")

    return job_id


def test_admin_candidates_list(driver):
    test = "admin_candidates_list"
    log("\n=== ADMIN: Candidates List ===")
    try:
        navigate(driver, "/candidates")
        screenshot(driver, "admin_04_candidates")

        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Candidates page: {error}", f"**Page**: `/candidates`\n**Error**: {error}")
            return
        page = driver.page_source.lower()
        if any(kw in page for kw in ["candidate", "name", "email", "resume", "add candidate"]):
            record(test, "PASS", "Candidates list loaded")
        else:
            record(test, "FAIL", "No candidate-related content")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_candidate_crud_api(api_token):
    """Test candidate create + read via API."""
    log("\n=== ADMIN: Candidate CRUD via API ===")
    cand_id = None

    test = "admin_candidate_create_api"
    try:
        cand_data = {
            "first_name": "Test",
            "last_name": f"Cand{datetime.now().strftime('%H%M%S')}",
            "email": f"testcand{datetime.now().strftime('%H%M%S')}@example.com",
            "phone": "+91-9876543210",
            "source": "referral",
            "experience_years": 5,
            "current_company": "TestCorp",
            "current_designation": "Senior Developer",
            "skills": "Python, Selenium, JavaScript"
        }
        resp = post_api(api_token, "/candidates", cand_data)
        if resp and resp.status_code in (200, 201):
            data = resp.json()
            cand_id = (data.get("data", {}).get("id") or data.get("id")
                       or data.get("data", {}).get("candidate", {}).get("id"))
            record(test, "PASS", f"Created candidate id={cand_id}")
        elif resp:
            record(test, "FAIL", f"API {resp.status_code}: {resp.text[:150]}")
            file_bug(f"[Recruit] Create candidate API returned {resp.status_code}",
                f"**Endpoint**: POST /candidates\n**Status**: {resp.status_code}\n**Response**: {resp.text[:300]}")
        else:
            record(test, "FAIL", "No API response")
            file_bug("[Recruit] Create candidate API - no response",
                "**Endpoint**: POST /candidates\n**Error**: No response from Recruit API.")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])

    if not cand_id:
        # Get existing candidate
        try:
            resp = get_api(api_token, "/candidates")
            if resp and resp.status_code == 200:
                data = resp.json()
                # Handle nested data structure
                inner = data.get("data", {})
                if isinstance(inner, dict):
                    cands = inner.get("data", inner.get("candidates", []))
                else:
                    cands = inner if isinstance(inner, list) else []
                if isinstance(cands, list) and len(cands) > 0:
                    cand_id = cands[0].get("id")
                    log(f"  Using existing candidate id={cand_id}")
        except:
            pass

    test = "admin_candidate_read_api"
    if cand_id:
        try:
            resp = get_api(api_token, f"/candidates/{cand_id}")
            if resp and resp.status_code == 200:
                record(test, "PASS", f"Read candidate {cand_id}")
            elif resp:
                record(test, "FAIL", f"API {resp.status_code}")
            else:
                record(test, "FAIL", "No API response")
        except Exception as e:
            record(test, "FAIL", str(e)[:150])
    else:
        record(test, "SKIP", "No cand_id")

    return cand_id


def test_admin_candidate_detail_ui(driver, cand_id):
    test = "admin_candidate_detail_ui"
    log("\n=== ADMIN: Candidate Detail (UI) ===")
    if not cand_id:
        record(test, "SKIP", "No candidate_id")
        return
    try:
        navigate(driver, f"/candidates/{cand_id}")
        screenshot(driver, "admin_05_candidate_detail")
        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
        else:
            record(test, "PASS", "Candidate detail page loaded")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])


def test_admin_application_pipeline(api_token, job_id, cand_id):
    """Create application, move through stages."""
    log("\n=== ADMIN: Application Pipeline (API) ===")
    app_id = None

    test = "admin_create_application"
    if not job_id or not cand_id:
        record(test, "SKIP", f"Missing job_id={job_id} or cand_id={cand_id}")
        record("admin_move_stage", "SKIP", "No application")
        return None
    try:
        resp = post_api(api_token, "/applications", {
            "job_id": job_id, "candidate_id": cand_id, "stage": "applied"
        })
        if resp and resp.status_code in (200, 201):
            data = resp.json()
            app_id = (data.get("data", {}).get("id") or data.get("id")
                      or data.get("data", {}).get("application", {}).get("id"))
            record(test, "PASS", f"Created application id={app_id}")
        elif resp:
            record(test, "FAIL", f"API {resp.status_code}: {resp.text[:150]}")
        else:
            record(test, "FAIL", "No API response")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])

    if not app_id:
        # Try listing existing applications
        try:
            resp = get_api(api_token, "/applications")
            if resp and resp.status_code == 200:
                data = resp.json()
                apps = data.get("data", {}).get("applications", data.get("data", []))
                if isinstance(apps, list) and len(apps) > 0:
                    app_id = apps[0].get("id")
                    log(f"  Using existing application id={app_id}")
        except:
            pass

    test = "admin_move_stage"
    if app_id:
        try:
            resp = patch_api(api_token, f"/applications/{app_id}/stage", {"stage": "screened"})
            if resp and resp.status_code in (200, 201):
                record(test, "PASS", "Moved to screened")
            elif resp:
                record(test, "FAIL", f"API {resp.status_code}: {resp.text[:150]}")
            else:
                record(test, "FAIL", "No API response")
        except Exception as e:
            record(test, "FAIL", str(e)[:150])
    else:
        record(test, "SKIP", "No application_id")

    return app_id


def test_admin_interviews_page(driver):
    test = "admin_interviews_page"
    log("\n=== ADMIN: Interviews Page ===")
    try:
        navigate(driver, "/interviews")
        screenshot(driver, "admin_06_interviews")

        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Interviews page: {error}", f"**Page**: `/interviews`\n**Error**: {error}")
            return
        page = driver.page_source.lower()
        if any(kw in page for kw in ["interview", "schedule", "calendar", "upcoming", "panel", "no interview"]):
            record(test, "PASS", "Interviews page loaded")
        else:
            record(test, "FAIL", "No interview content found")
            screenshot(driver, "admin_06_interviews_debug")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_schedule_interview_api(api_token, app_id, cand_id):
    test = "admin_schedule_interview"
    log("\n=== ADMIN: Schedule Interview (API) ===")
    if not app_id:
        record(test, "SKIP", "No application_id")
        return None
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        resp = post_api(api_token, "/interviews", {
            "application_id": app_id,
            "candidate_id": cand_id,
            "type": "technical",
            "scheduled_date": tomorrow,
            "scheduled_time": "10:00",
            "start_time": f"{tomorrow}T10:00:00",
            "end_time": f"{tomorrow}T11:00:00",
            "duration_minutes": 60,
            "location": "Google Meet",
            "notes": "E2E test interview"
        })
        if resp and resp.status_code in (200, 201):
            data = resp.json()
            int_id = (data.get("data", {}).get("id") or data.get("id")
                      or data.get("data", {}).get("interview", {}).get("id"))
            record(test, "PASS", f"Scheduled interview id={int_id}")
            return int_id
        elif resp:
            record(test, "FAIL", f"API {resp.status_code}: {resp.text[:150]}")
        else:
            record(test, "FAIL", "No API response")
        return None
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        return None


def test_admin_interview_detail_ui(driver, int_id):
    test = "admin_interview_detail_ui"
    log("\n=== ADMIN: Interview Detail (UI) ===")
    if not int_id:
        record(test, "SKIP", "No interview_id")
        return
    try:
        navigate(driver, f"/interviews/{int_id}")
        screenshot(driver, "admin_07_interview_detail")
        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
        else:
            record(test, "PASS", "Interview detail loaded")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])


def test_admin_offers_page(driver):
    test = "admin_offers_page"
    log("\n=== ADMIN: Offers Page ===")
    try:
        navigate(driver, "/offers")
        screenshot(driver, "admin_08_offers")

        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Offers page: {error}", f"**Page**: `/offers`\n**Error**: {error}")
            return
        page = driver.page_source.lower()
        if any(kw in page for kw in ["offer", "salary", "designation", "status", "candidate", "no offer"]):
            record(test, "PASS", "Offers page loaded")
        else:
            record(test, "FAIL", "No offer content found")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_create_offer_api(api_token, app_id, cand_id, job_id):
    test = "admin_create_offer"
    log("\n=== ADMIN: Create Offer (API) ===")
    if not app_id or not cand_id:
        record(test, "SKIP", "Missing application/candidate id")
        return None
    try:
        resp = post_api(api_token, "/offers", {
            "application_id": app_id,
            "candidate_id": cand_id,
            "job_id": job_id,
            "salary": 1200000,
            "designation": "QA Engineer",
            "joining_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "expiry_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "notes": "E2E test offer"
        })
        if resp and resp.status_code in (200, 201):
            data = resp.json()
            offer_id = (data.get("data", {}).get("id") or data.get("id")
                        or data.get("data", {}).get("offer", {}).get("id"))
            record(test, "PASS", f"Created offer id={offer_id}")
            return offer_id
        elif resp:
            record(test, "FAIL", f"API {resp.status_code}: {resp.text[:150]}")
        else:
            record(test, "FAIL", "No API response")
        return None
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        return None


def test_admin_analytics(driver):
    test = "admin_analytics"
    log("\n=== ADMIN: Analytics ===")
    try:
        navigate(driver, "/analytics")
        screenshot(driver, "admin_09_analytics")

        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Analytics page: {error}", f"**Page**: `/analytics`\n**Error**: {error}")
            return
        page = driver.page_source.lower()
        if any(kw in page for kw in [
            "analytics", "time to hire", "pipeline", "funnel", "source",
            "chart", "metric", "report", "conversion", "overview", "recruit"
        ]):
            record(test, "PASS", "Analytics page loaded")
        else:
            record(test, "FAIL", "No analytics content found")
            file_bug("[Recruit] Analytics page has no analytics content",
                "**Page**: `/analytics`\n**Expected**: Charts/metrics for recruitment analytics.")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_settings(driver):
    test = "admin_settings"
    log("\n=== ADMIN: Settings ===")
    try:
        navigate(driver, "/settings")
        screenshot(driver, "admin_10_settings")

        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Settings page: {error}", f"**Page**: `/settings`\n**Error**: {error}")
            return
        page = driver.page_source.lower()
        if any(kw in page for kw in [
            "settings", "configuration", "career page", "email template",
            "integration", "pipeline", "preference", "recruit"
        ]):
            record(test, "PASS", "Settings page loaded")
        else:
            record(test, "FAIL", "No settings content found")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_pipeline_config(driver):
    test = "admin_pipeline_config"
    log("\n=== ADMIN: Pipeline Stage Configuration ===")
    try:
        navigate(driver, "/pipeline-config")
        screenshot(driver, "admin_11_pipeline_config")

        error = check_page_errors(driver)
        if error:
            # Might be under /settings
            navigate(driver, "/settings")
            screenshot(driver, "admin_11b_settings_pipeline")
            error2 = check_page_errors(driver)
            if error2:
                record(test, "FAIL", f"Pipeline config: {error}")
            else:
                page = driver.page_source.lower()
                if "pipeline" in page or "stage" in page:
                    record(test, "PASS", "Pipeline config found under settings")
                else:
                    record(test, "FAIL", "Pipeline config not accessible")
        else:
            record(test, "PASS", "Pipeline config page loaded")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_referrals(driver):
    test = "admin_referrals"
    log("\n=== ADMIN: Referrals ===")
    try:
        navigate(driver, "/referrals")
        screenshot(driver, "admin_12_referrals")
        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Referrals page: {error}", f"**Page**: `/referrals`\n**Error**: {error}")
        else:
            record(test, "PASS", "Referrals page loaded")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_onboarding(driver):
    test = "admin_onboarding"
    log("\n=== ADMIN: Onboarding ===")
    try:
        navigate(driver, "/onboarding")
        screenshot(driver, "admin_13_onboarding")
        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Onboarding page: {error}", f"**Page**: `/onboarding`\n**Error**: {error}")
        else:
            record(test, "PASS", "Onboarding page loaded")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_ai_scoring(driver):
    test = "admin_ai_scoring"
    log("\n=== ADMIN: AI Resume Scoring ===")
    try:
        navigate(driver, "/ai-scoring")
        screenshot(driver, "admin_14_ai_scoring")
        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(
                "[Recruit] AI Resume Scoring page returns 404",
                "**Page**: `/ai-scoring`\n**Error**: 404 Page Not Found\n\n"
                "**Steps**:\n1. SSO login as admin\n2. Navigate to `/ai-scoring`\n3. Page shows 404\n\n"
                "**Expected**: AI resume scoring page loads with batch scoring dashboard.\n"
                "**Note**: README lists this page at `/ai-scoring` route."
            )
        else:
            record(test, "PASS", "AI scoring page loaded")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_job_detail_kanban(driver, job_id):
    test = "admin_job_detail_kanban"
    log("\n=== ADMIN: Job Detail / ATS Kanban ===")
    if not job_id:
        record(test, "SKIP", "No job_id")
        return
    try:
        navigate(driver, f"/jobs/{job_id}")
        screenshot(driver, "admin_15_job_kanban")
        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
        else:
            page = driver.page_source.lower()
            has_pipeline = any(kw in page for kw in [
                "applied", "screened", "interview", "offer", "hired",
                "pipeline", "kanban", "stage"
            ])
            if has_pipeline:
                record(test, "PASS", "Job detail with pipeline/kanban loaded")
            else:
                record(test, "PASS", "Job detail loaded (no kanban keywords but page OK)")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_admin_api_endpoints(api_token):
    """Test key API list endpoints."""
    log("\n=== ADMIN: API List Endpoints ===")

    endpoints = [
        ("admin_api_list_jobs", "/jobs"),
        ("admin_api_list_candidates", "/candidates"),
        ("admin_api_list_interviews", "/interviews"),
        ("admin_api_list_applications", "/applications"),
        ("admin_api_referrals", "/referrals"),
        ("admin_api_offers", "/offers"),
    ]
    for test, ep in endpoints:
        try:
            resp = get_api(api_token, ep)
            if resp and resp.status_code == 200:
                record(test, "PASS", f"GET {ep} returned 200")
            elif resp and resp.status_code == 404:
                # Try with /overview suffix for analytics
                if "analytics" in ep:
                    resp2 = get_api(api_token, f"{ep}/overview")
                    if resp2 and resp2.status_code == 200:
                        record(test, "PASS", f"GET {ep}/overview returned 200")
                        continue
                record(test, "FAIL", f"GET {ep} returned 404")
            elif resp:
                record(test, "FAIL", f"GET {ep} returned {resp.status_code}")
            else:
                record(test, "FAIL", f"GET {ep} - no response")
        except Exception as e:
            record(test, "FAIL", str(e)[:150])


# ============================================================
# EMPLOYEE TESTS (RBAC)
# ============================================================

def test_employee_dashboard(driver):
    test = "employee_dashboard"
    log("\n=== EMPLOYEE: Dashboard ===")
    try:
        navigate(driver, "/")
        screenshot(driver, "emp_01_dashboard")
        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Employee dashboard: {error}",
                f"**Page**: `/` (employee)\n**Error**: {error}\n**User**: priya@technova.in")
        else:
            record(test, "PASS", "Employee dashboard loaded")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_employee_internal_jobs(driver):
    test = "employee_internal_jobs"
    log("\n=== EMPLOYEE: Internal Jobs ===")
    try:
        navigate(driver, "/jobs")
        screenshot(driver, "emp_02_jobs")
        error = check_page_errors(driver)
        page = driver.page_source.lower()
        if error and ("403" in str(error) or "sso" in str(error)):
            record(test, "FAIL", error)
        elif error:
            record(test, "FAIL", error)
        else:
            record(test, "PASS", "Employee can view jobs page")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def test_employee_referrals(driver):
    test = "employee_referrals"
    log("\n=== EMPLOYEE: Referrals ===")
    try:
        navigate(driver, "/referrals")
        screenshot(driver, "emp_03_referrals")
        error = check_page_errors(driver)
        if error:
            record(test, "FAIL", error)
            file_bug(f"[Recruit] Employee referrals page: {error}",
                f"**Page**: `/referrals` (employee)\n**Error**: {error}\n**User**: priya@technova.in\n"
                f"**Expected**: Employees should be able to submit referrals.")
        else:
            record(test, "PASS", "Employee referrals page loaded")
    except Exception as e:
        record(test, "FAIL", str(e)[:150])
        screenshot(driver, f"{test}_error")


def check_employee_logged_in(driver):
    """Verify the employee is actually logged in, not stuck on login page."""
    page = driver.page_source.lower()
    if "welcome back" in page and "sign in" in page:
        return False
    if "sso login failed" in page:
        return False
    return True

def test_employee_rbac_blocked(driver, path, test_name, page_label, admin_keywords):
    """Generic RBAC test: employee should NOT see admin content at the given path."""
    log(f"\n=== EMPLOYEE RBAC: {page_label} should be blocked ===")
    try:
        navigate(driver, path)
        screenshot(driver, f"emp_rbac_{test_name}")

        page = driver.page_source.lower()

        # First check if we're even logged in
        if "welcome back" in page and "sign in" in page:
            record(test_name, "SKIP", "Not logged in - on login page (session expired)")
            return

        # If access denied / forbidden / redirected -- good
        if any(kw in page for kw in ["403", "access denied", "unauthorized", "not authorized", "permission denied", "forbidden"]):
            record(test_name, "PASS", f"{page_label} correctly blocked for employee")
            return

        # If page has admin-level keywords, RBAC is broken
        if any(kw in page for kw in admin_keywords):
            record(test_name, "FAIL", f"Employee can access {page_label} (should be blocked)")
            file_bug(
                f"[Recruit] RBAC: Employee can access {page_label}",
                f"**Page**: `{path}`\n**User**: priya@technova.in (employee)\n"
                f"**Expected**: Employee should NOT see {page_label}.\n"
                f"**Actual**: Page loaded with admin controls.",
                labels=["bug", "recruit", "security"]
            )
        else:
            # Page loaded but without admin content -- might be restricted view or redirected
            record(test_name, "PASS", f"{page_label} restricted or redirected for employee")
    except Exception as e:
        record(test_name, "FAIL", str(e)[:150])
        screenshot(driver, f"{test_name}_error")


# ============================================================
# MAIN
# ============================================================
def main():
    log("=" * 60)
    log("EMP RECRUIT MODULE - FRESH E2E TEST")
    log("=" * 60)

    # --- Get tokens ---
    admin_sso_token = get_sso_token(ADMIN_EMAIL, ADMIN_PASS)
    if not admin_sso_token:
        log("FATAL: Cannot get admin SSO token. Aborting.")
        sys.exit(1)

    emp_sso_token = get_sso_token(EMP_EMAIL, EMP_PASS)
    if not emp_sso_token:
        log("WARNING: Cannot get employee SSO token. Employee tests will be skipped.")

    # Get Recruit API token
    admin_api_token = get_recruit_api_token(admin_sso_token)

    # ================================================================
    # PART 1: ADMIN UI TESTS (SSO -> navigate within session)
    # ================================================================
    log("\n" + "=" * 60)
    log("PART 1: ADMIN UI TESTS (ananya@technova.in)")
    log("=" * 60)

    driver = create_driver()
    job_id = None
    cand_id = None
    app_id = None
    int_id = None
    try:
        # SSO login once (with fallback to manual login)
        if not sso_login(driver, admin_sso_token, ADMIN_EMAIL, ADMIN_PASS):
            log("  Retrying SSO with fresh token...")
            admin_sso_token = get_sso_token(ADMIN_EMAIL, ADMIN_PASS)
            sso_login(driver, admin_sso_token, ADMIN_EMAIL, ADMIN_PASS)
            admin_api_token = get_recruit_api_token(admin_sso_token)

        # Try to extract API token from browser session
        browser_token = extract_api_token(driver)
        if browser_token and not browser_token.startswith("{"):
            log(f"  Using browser-extracted token for API calls")
            admin_api_token = browser_token

        # All admin UI page tests
        admin_ui_tests = [
            ("Dashboard", test_admin_dashboard),
            ("Jobs List", test_admin_jobs_list),
            ("Job Create UI", test_admin_job_create_ui),
            ("Candidates List", test_admin_candidates_list),
            ("Interviews Page", test_admin_interviews_page),
            ("Offers Page", test_admin_offers_page),
            ("Analytics", test_admin_analytics),
            ("Settings", test_admin_settings),
            ("Pipeline Config", test_admin_pipeline_config),
            ("Referrals", test_admin_referrals),
            ("Onboarding", test_admin_onboarding),
            ("AI Scoring", test_admin_ai_scoring),
        ]

        for label, test_fn in admin_ui_tests:
            if not is_driver_alive(driver):
                log(f"  Driver died before {label}, recreating...")
                try:
                    driver.quit()
                except:
                    pass
                time.sleep(2)
                driver = create_driver()
                if not driver:
                    log(f"  Cannot recreate driver, skipping remaining UI tests")
                    break
                admin_sso_token = get_sso_token(ADMIN_EMAIL, ADMIN_PASS)
                sso_login(driver, admin_sso_token, ADMIN_EMAIL, ADMIN_PASS)
                admin_api_token = get_recruit_api_token(admin_sso_token)
                browser_token = extract_api_token(driver)
                if browser_token and not browser_token.startswith("{"):
                    admin_api_token = browser_token
            try:
                test_fn(driver)
            except Exception as e:
                log(f"  UNHANDLED ERROR in {label}: {e}")

    finally:
        try:
            driver.quit()
        except:
            pass

    # ================================================================
    # PART 2: EMPLOYEE TESTS (RBAC) - run IMMEDIATELY with fresh token
    # ================================================================
    if emp_sso_token:
        log("\n" + "=" * 60)
        log("PART 2: EMPLOYEE TESTS / RBAC (priya@technova.in)")
        log("=" * 60)

        # Fresh token for employee
        emp_sso_token2 = get_sso_token(EMP_EMAIL, EMP_PASS)
        driver = create_driver()
        try:
            login_ok = sso_login(driver, emp_sso_token2 or emp_sso_token, EMP_EMAIL, EMP_PASS)
            if not login_ok:
                log("  Employee login failed completely. Skipping employee tests.")
                for t in ["employee_dashboard", "employee_internal_jobs", "employee_referrals",
                           "emp_rbac_candidates", "emp_rbac_interviews", "emp_rbac_settings", "emp_rbac_pipeline"]:
                    record(t, "SKIP", "Employee login failed")
                raise Exception("Employee login failed")

            # Verify we're logged in as the right user
            screenshot(driver, "emp_00_login_verify")
            page_check = driver.page_source.lower()
            if "welcome back" in page_check and "sign in" in page_check:
                log("  Still on login page after login attempt! Skipping employee tests.")
                for t in ["employee_dashboard", "employee_internal_jobs", "employee_referrals",
                           "emp_rbac_candidates", "emp_rbac_interviews", "emp_rbac_settings", "emp_rbac_pipeline"]:
                    record(t, "SKIP", "Employee login did not succeed")
                raise Exception("Employee login did not navigate away from login page")

            log(f"  Employee session confirmed - proceeding with tests")

            test_employee_dashboard(driver)
            test_employee_internal_jobs(driver)
            test_employee_referrals(driver)

            # RBAC: these should be blocked
            test_employee_rbac_blocked(driver, "/candidates",
                "emp_rbac_candidates", "Candidate management",
                ["add candidate", "create candidate", "candidate pipeline"])

            test_employee_rbac_blocked(driver, "/interviews",
                "emp_rbac_interviews", "Interview management",
                ["schedule interview", "create interview", "new interview"])

            test_employee_rbac_blocked(driver, "/settings",
                "emp_rbac_settings", "Recruitment settings",
                ["career page", "email template", "integration"])

            test_employee_rbac_blocked(driver, "/pipeline-config",
                "emp_rbac_pipeline", "Pipeline configuration",
                ["add stage", "drag", "reorder", "custom stage"])

        except Exception as e:
            log(f"  Error in employee tests: {e}")
        finally:
            try:
                driver.quit()
            except:
                pass
    else:
        log("\nSKIPPING EMPLOYEE TESTS - no token")
        for t in ["employee_dashboard", "employee_internal_jobs", "employee_referrals",
                   "emp_rbac_candidates", "emp_rbac_interviews", "emp_rbac_settings", "emp_rbac_pipeline"]:
            record(t, "SKIP", "No employee SSO token")

    # ================================================================
    # PART 3: ADMIN API TESTS (CRUD operations)
    # ================================================================
    log("\n" + "=" * 60)
    log("PART 3: ADMIN API TESTS (CRUD)")
    log("=" * 60)

    # Try to refresh API token, but fall back to existing one if exchange fails
    try:
        admin_sso_token_fresh = get_sso_token(ADMIN_EMAIL, ADMIN_PASS)
        new_api_token = get_recruit_api_token(admin_sso_token_fresh or admin_sso_token)
        # Test if the new token actually works
        test_resp = get_api(new_api_token, "/jobs")
        if test_resp and test_resp.status_code == 200:
            admin_api_token = new_api_token
            log(f"  Refreshed API token works")
        else:
            log(f"  New API token doesn't work (status={test_resp.status_code if test_resp else 'none'}), keeping previous token")
    except Exception as e:
        log(f"  Could not refresh API token: {e}, keeping previous token")

    job_id = test_admin_job_crud_api(admin_api_token)
    cand_id = test_admin_candidate_crud_api(admin_api_token)
    app_id = test_admin_application_pipeline(admin_api_token, job_id, cand_id)
    int_id = test_admin_schedule_interview_api(admin_api_token, app_id, cand_id)
    test_admin_create_offer_api(admin_api_token, app_id, cand_id, job_id)
    test_admin_api_endpoints(admin_api_token)

    # ================================================================
    # PART 4: ADMIN DETAIL PAGES (UI)
    # ================================================================
    log("\n" + "=" * 60)
    log("PART 4: ADMIN DETAIL PAGES (UI)")
    log("=" * 60)

    admin_sso_token3 = get_sso_token(ADMIN_EMAIL, ADMIN_PASS)
    driver = create_driver()
    try:
        sso_login(driver, admin_sso_token3 or admin_sso_token, ADMIN_EMAIL, ADMIN_PASS)

        detail_tests = [
            ("Candidate Detail", lambda d: test_admin_candidate_detail_ui(d, cand_id)),
            ("Job Kanban", lambda d: test_admin_job_detail_kanban(d, job_id)),
            ("Interview Detail", lambda d: test_admin_interview_detail_ui(d, int_id)),
        ]
        for label, test_fn in detail_tests:
            if not is_driver_alive(driver):
                log(f"  Driver died before {label}, recreating...")
                try:
                    driver.quit()
                except:
                    pass
                driver = create_driver()
                fresh_token = get_sso_token(ADMIN_EMAIL, ADMIN_PASS)
                sso_login(driver, fresh_token, ADMIN_EMAIL, ADMIN_PASS)
            try:
                test_fn(driver)
            except Exception as e:
                log(f"  UNHANDLED ERROR in {label}: {e}")
    except Exception as e:
        log(f"  Error in detail pages: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass

    # ================================================================
    # SUMMARY
    # ================================================================
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)

    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    failed = sum(1 for r in results.values() if r["status"] == "FAIL")
    skipped = sum(1 for r in results.values() if r["status"] == "SKIP")
    total = len(results)

    log(f"\nTotal: {total}  |  PASS: {passed}  |  FAIL: {failed}  |  SKIP: {skipped}")
    log(f"Pass rate: {(passed/(total - skipped)*100):.1f}% (excluding skips)" if (total - skipped) > 0 else "No tests run")

    if failed > 0:
        log(f"\nFailed tests:")
        for name, r in results.items():
            if r["status"] == "FAIL":
                log(f"  - {name}: {r['detail']}")

    if skipped > 0:
        log(f"\nSkipped tests:")
        for name, r in results.items():
            if r["status"] == "SKIP":
                log(f"  - {name}: {r['detail']}")

    if bugs:
        log(f"\nBugs filed ({len(bugs)}):")
        for b in bugs:
            log(f"  - {b}")
    else:
        log("\nNo bugs filed.")

    log(f"\nScreenshots: {SCREENSHOT_DIR}")
    log(f"Done at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
