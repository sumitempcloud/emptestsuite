"""
EMP LMS Module - Comprehensive SSO Test
Tests: Dashboard, Courses, My Learning, Certifications, Learning Paths,
       Compliance, Analytics, Settings, Course Creation, Enrollment
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import urllib.request
import urllib.error
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ──────────────────────────────────────────────────────────────
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_lms"
EMPCLOUD_LOGIN_API = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
LMS_BASE = "https://testlms.empcloud.com"
LMS_API = "https://testlms-api.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
API_DELAY = 3  # seconds between API calls to avoid rate limits

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
bugs_filed = []
test_results = []

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {name}.png")
    return path

def record(name, status, details=""):
    test_results.append({"test": name, "status": status, "details": details})
    log(f"  [{status.upper()}] {name}: {details}")

def file_bug(title, body):
    if "rate limit" in title.lower():
        return None
    full_title = f"[LMS] {title}"
    bugs_filed.append(full_title)
    try:
        data = json.dumps({"title": full_title, "body": body, "labels": ["bug", "lms"]}).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            data=data, headers={"Authorization": f"token {GITHUB_PAT}", "Content-Type": "application/json",
                                "User-Agent": UA}, method="POST"
        )
        resp = json.loads(urllib.request.urlopen(req).read())
        log(f"  Filed bug #{resp['number']}: {full_title}")
        return resp['number']
    except Exception as e:
        log(f"  Failed to file bug: {e}")
        return None

def api_get(url, token=None):
    """Gentle API GET with delay to avoid rate limits."""
    time.sleep(API_DELAY)
    headers = {"Accept": "application/json", "User-Agent": UA}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: bd = json.loads(e.read())
        except: bd = {"error": str(e)}
        return e.code, bd
    except Exception as e:
        return 0, {"error": str(e)}

def api_post(url, data, token=None):
    """Gentle API POST with delay to avoid rate limits."""
    time.sleep(API_DELAY)
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: bd = json.loads(e.read())
        except: bd = {"error": str(e)}
        return e.code, bd
    except Exception as e:
        return 0, {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════
log("=" * 70)
log("EMP LMS MODULE - COMPREHENSIVE TEST")
log("=" * 70)

# ── Step 1: Get EmpCloud SSO token ─────────────────────────────────────
log("\n[1] Authenticating via EmpCloud API...")
status, resp = api_post(EMPCLOUD_LOGIN_API, {"email": EMAIL, "password": PASSWORD})

empcloud_token = None
if status == 200 and isinstance(resp, dict):
    d = resp.get("data", resp)
    t = d.get("tokens", d)
    empcloud_token = t.get("access_token") or t.get("token") or resp.get("token")

if not empcloud_token:
    log(f"  EmpCloud login failed: status={status}")
    sys.exit(1)

log(f"  EmpCloud token obtained ({len(empcloud_token)} chars)")
record("EmpCloud Login", "pass", "Got access_token")

user_info = resp.get("data", {}).get("user", {})
log(f"  User: {user_info.get('first_name','')} {user_info.get('last_name','')} ({user_info.get('email','')}) - {user_info.get('role','')}")


# ── Step 2: Exchange for LMS token via /auth/sso ───────────────────────
log("\n[2] Exchanging for LMS token via /auth/sso...")
time.sleep(3)  # Extra pause before SSO exchange
lms_token = None

status, data = api_post(f"{LMS_API}/api/v1/auth/sso", {"token": empcloud_token})
log(f"  SSO exchange: status={status}, keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}")

if status == 200 and isinstance(data, dict):
    # Try various nested structures
    for path in [
        lambda d: d.get("token"),
        lambda d: d.get("access_token"),
        lambda d: d.get("accessToken"),
        lambda d: d.get("data", {}).get("token"),
        lambda d: d.get("data", {}).get("access_token"),
        lambda d: d.get("data", {}).get("accessToken"),
        lambda d: d.get("data", {}).get("tokens", {}).get("access_token"),
        lambda d: d.get("data", {}).get("tokens", {}).get("accessToken"),
        lambda d: d.get("data", {}).get("tokens", {}).get("token"),
    ]:
        try:
            v = path(data)
            if v and isinstance(v, str) and len(v) > 20:
                lms_token = v
                break
        except: pass

if lms_token:
    log(f"  LMS token obtained ({len(lms_token)} chars)")
    record("LMS SSO Token Exchange", "pass", "Got LMS-local token")
else:
    log(f"  SSO exchange response: {str(data)[:300]}")
    record("LMS SSO Token Exchange", "warn", f"status={status}, will try browser login")


# ── Step 3: Setup Chrome ───────────────────────────────────────────────
log("\n[3] Setting up Chrome...")
opts = Options()
opts.binary_location = CHROME_PATH
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")
opts.add_argument("--disable-gpu")
opts.add_argument("--ignore-certificate-errors")

driver = webdriver.Chrome(options=opts)
driver.set_page_load_timeout(30)
wait = WebDriverWait(driver, 10)

try:
    # ── Step 4: SSO into LMS via browser ────────────────────────────────
    log("\n[4] SSO into LMS via browser...")
    driver.get(f"{LMS_BASE}?sso_token={empcloud_token}")
    time.sleep(5)

    current_url = driver.current_url
    log(f"  Landed at: {current_url}")
    log(f"  Title: {driver.title}")

    # If SSO failed and we're on login page, log in directly via the form
    if "/login" in current_url.lower():
        log("  SSO redirected to login page. Trying direct login via form...")
        # The login page shows demo creds. Try our credentials first via the LMS login API
        time.sleep(2)
        status_login, data_login = api_post(f"{LMS_API}/api/v1/auth/login", {"email": EMAIL, "password": PASSWORD})
        log(f"  LMS direct login API: status={status_login}")

        if status_login == 200 and isinstance(data_login, dict):
            for path in [
                lambda d: d.get("token"),
                lambda d: d.get("access_token"),
                lambda d: d.get("data", {}).get("token"),
                lambda d: d.get("data", {}).get("access_token"),
                lambda d: d.get("data", {}).get("tokens", {}).get("access_token"),
            ]:
                try:
                    v = path(data_login)
                    if v and isinstance(v, str) and len(v) > 20:
                        lms_token = v
                        break
                except: pass
            if lms_token:
                log(f"  Got LMS token from direct login ({len(lms_token)} chars)")
                # Inject token into browser localStorage and reload
                driver.execute_script(f"""
                    localStorage.setItem('token', '{lms_token}');
                    localStorage.setItem('auth-storage', JSON.stringify({{
                        state: {{ token: '{lms_token}', isAuthenticated: true }}
                    }}));
                """)
                driver.get(f"{LMS_BASE}/dashboard")
                time.sleep(4)
                current_url = driver.current_url
                log(f"  After token injection: {current_url}")

        # If still on login page, try the login form
        if "/login" in driver.current_url.lower():
            log("  Trying login via form fields...")
            try:
                email_input = driver.find_element(By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail']")
                pwd_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
                email_input.clear()
                email_input.send_keys(EMAIL)
                pwd_input.clear()
                pwd_input.send_keys(PASSWORD)
                # Find and click submit
                submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button:not([type])")
                submit_btn.click()
                time.sleep(5)
                current_url = driver.current_url
                log(f"  After form login: {current_url}")
            except Exception as e:
                log(f"  Form login error: {e}")

    screenshot(driver, "01_lms_dashboard")
    body_text = driver.find_element(By.TAG_NAME, "body").text

    if "/login" not in driver.current_url.lower():
        record("LMS Login", "pass", f"Authenticated, at {driver.current_url}")
        # Extract token from browser for API testing
        if not lms_token:
            try:
                extracted = driver.execute_script("""
                    for (var i = 0; i < localStorage.length; i++) {
                        var k = localStorage.key(i);
                        var v = localStorage.getItem(k);
                        if (v && v.includes('eyJ')) {
                            try {
                                var p = JSON.parse(v);
                                if (p.token) return p.token;
                                if (p.state && p.state.token) return p.state.token;
                                if (p.state && p.state.accessToken) return p.state.accessToken;
                            } catch(e) { if (v.startsWith('eyJ')) return v; }
                        }
                    }
                    return localStorage.getItem('token') || localStorage.getItem('access_token') || null;
                """)
                if extracted:
                    lms_token = extracted
                    log(f"  Extracted LMS token from browser ({len(lms_token)} chars)")
            except: pass
    else:
        record("LMS Login", "fail", "Could not authenticate - stuck on login page")
        file_bug("SSO and direct login both fail - cannot access LMS",
                 f"**Steps:**\n"
                 f"1. SSO via `?sso_token=<empcloud_token>` -> redirects to /login\n"
                 f"2. LMS /auth/sso endpoint -> returns non-token response\n"
                 f"3. LMS /auth/login with credentials -> attempted\n"
                 f"4. Login form submission -> still on /login\n\n"
                 f"**Login page shows demo creds:** `admin@demo.com / demo1234` and `learner@demo.com / demo1234`\n"
                 f"**Expected:** SSO with EmpCloud token should authenticate user\n"
                 f"**Body:** {body_text[:300]}")

    dashboard_kw = ["course", "learning", "enrolled", "welcome", "dashboard", "training"]
    found_kw = [k for k in dashboard_kw if k in body_text.lower()]
    log(f"  Dashboard keywords: {found_kw}")
    log(f"  Body preview: {body_text[:300]}")

    # ── Determine if we're authenticated ────────────────────────────────
    authenticated = "/login" not in driver.current_url.lower()

    if not authenticated:
        log("\n  WARNING: Not authenticated. Will test pages but all will redirect to login.")
        log("  Testing what we can in unauthenticated state...")

    # ── Step 5-15: Test all frontend pages ──────────────────────────────
    pages = [
        ("/courses",        "02_courses",        "Courses Page",        ["course", "catalog", "search"]),
        ("/my-learning",    "03_my_learning",    "My Learning Page",    ["learning", "enrolled", "progress"]),
        ("/certifications", "04_certifications", "Certifications Page", ["certificate", "certification"]),
        ("/learning-paths", "05_learning_paths", "Learning Paths Page", ["learning path", "path"]),
        ("/compliance",     "06_compliance",     "Compliance Page",     ["compliance", "training", "mandatory"]),
        ("/analytics",      "07_analytics",      "Analytics Page",      ["analytics", "overview", "completion"]),
        ("/settings",       "08_settings",       "Settings Page",       ["settings", "categories", "template"]),
        ("/quizzes",        "09_quizzes",        "Quizzes Page",        ["quiz", "question", "assessment"]),
        ("/ilt",            "10_ilt",            "ILT Sessions Page",   ["session", "instructor", "ilt"]),
        ("/leaderboard",    "11_leaderboard",    "Leaderboard Page",    ["leaderboard", "points", "rank"]),
        ("/marketplace",    "12_marketplace",    "Marketplace Page",    ["marketplace", "content", "catalog"]),
        ("/scorm",          "13_scorm",          "SCORM Page",          ["scorm", "package", "player"]),
    ]

    step = 5
    pages_404 = []
    pages_ok = []
    pages_login_redirect = []

    for path, ss_name, test_name, keywords in pages:
        log(f"\n[{step}] Testing {path}...")
        driver.get(f"{LMS_BASE}{path}")
        time.sleep(3)
        screenshot(driver, ss_name)
        body = driver.find_element(By.TAG_NAME, "body").text
        cur = driver.current_url

        if "/login" in cur.lower() and path != "/login":
            pages_login_redirect.append(path)
            if authenticated:
                record(test_name, "fail", "Redirected to login despite being authenticated")
            else:
                record(test_name, "warn", "Redirected to login (not authenticated)")
        elif "404" in body or "not found" in body.lower():
            pages_404.append(path)
            record(test_name, "fail", f"404 at {cur}")
        else:
            found = [kw for kw in keywords if kw in body.lower()]
            if found:
                pages_ok.append(path)
                record(test_name, "pass", f"Keywords: {found}")
            else:
                record(test_name, "warn", f"Loaded at {cur}, content: {body[:150]}")
        step += 1


    # ── Step 17: Test LMS API with delays ───────────────────────────────
    log(f"\n[{step}] Testing LMS API endpoints...")
    step += 1

    if lms_token:
        log(f"  Using token ({len(lms_token)} chars)")
    else:
        log("  No LMS token available, using EmpCloud token as fallback")
        lms_token = empcloud_token

    api_endpoints = [
        ("/api/v1/courses",                 "API Courses"),
        ("/api/v1/enrollments/my",           "API My Enrollments"),
        ("/api/v1/certificates/my",          "API My Certificates"),
        ("/api/v1/learning-paths",           "API Learning Paths"),
        ("/api/v1/compliance/my",            "API My Compliance"),
        ("/api/v1/analytics/overview",       "API Analytics"),
        ("/api/v1/gamification/leaderboard", "API Leaderboard"),
        ("/api/v1/gamification/my",          "API My Gamification"),
        ("/api/v1/notifications",            "API Notifications"),
        ("/api/v1/ilt",                      "API ILT Sessions"),
        ("/api/v1/marketplace",              "API Marketplace"),
        ("/api/v1/recommendations",          "API Recommendations"),
    ]

    available_courses = []
    api_401_count = 0
    api_429_count = 0

    for endpoint, test_name in api_endpoints:
        s, d = api_get(f"{LMS_API}{endpoint}", lms_token)
        if s == 200:
            preview = str(d)[:120]
            record(test_name, "pass", preview)
            if endpoint == "/api/v1/courses":
                cl = d if isinstance(d, list) else d.get("data", d.get("courses", []))
                if isinstance(cl, list):
                    available_courses = cl
                    log(f"    Found {len(cl)} courses")
        elif s == 401:
            api_401_count += 1
            record(test_name, "fail", "401 INVALID_TOKEN")
        elif s == 429:
            api_429_count += 1
            record(test_name, "warn", "429 Rate Limited")
            time.sleep(3)  # Extra backoff
        elif s == 403:
            record(test_name, "warn", "403 Forbidden")
        elif s == 404:
            record(test_name, "fail", "404 Not Found")
        else:
            record(test_name, "fail", f"Status {s}: {str(d)[:120]}")

    # File consolidated bug for API auth if needed
    if api_401_count >= 5:
        file_bug("LMS API rejects EmpCloud SSO token on all endpoints",
                 f"**Issue:** All LMS API endpoints return `401 INVALID_TOKEN` when called with the EmpCloud access_token.\n\n"
                 f"**Steps:**\n"
                 f"1. `POST /api/v1/auth/login` on EmpCloud -> get `access_token`\n"
                 f"2. `POST /api/v1/auth/sso` on LMS API with that token -> does not return a usable LMS token\n"
                 f"3. Any LMS API call with `Authorization: Bearer <empcloud_token>` -> 401\n\n"
                 f"**Expected:** The /auth/sso endpoint should exchange the EmpCloud RS256 JWT for an LMS-local HS256 JWT.\n"
                 f"**Actual:** SSO exchange does not return a usable token; direct token use returns INVALID_TOKEN.\n\n"
                 f"**Note:** The frontend SSO (`?sso_token=`) may also be affected - it sometimes works and sometimes redirects to /login.\n"
                 f"**Affected:** {api_401_count} of {len(api_endpoints)} endpoints tested")


    # ── Step 18: Try creating a course ──────────────────────────────────
    log(f"\n[{step}] Testing course creation...")
    step += 1

    course_payload = {
        "title": f"LMS Test Course {datetime.now().strftime('%H%M%S')}",
        "description": "Automated test course",
        "status": "draft",
        "difficulty": "beginner",
    }
    s, d = api_post(f"{LMS_API}/api/v1/courses", course_payload, lms_token)
    if s in [200, 201]:
        created = d.get("data", d.get("course", d))
        record("Create Course API", "pass", f"Created: {str(created)[:150]}")
    elif s == 401:
        record("Create Course API", "fail", "401 - token not accepted")
    elif s == 403:
        record("Create Course API", "warn", "403 - need admin/instructor role")
    elif s == 429:
        record("Create Course API", "warn", "429 Rate Limited")
    else:
        record("Create Course API", "fail", f"Status {s}: {str(d)[:150]}")

    # Try via UI
    if authenticated:
        log("  Testing course creation via UI...")
        driver.get(f"{LMS_BASE}/courses")
        time.sleep(3)
        try:
            btns = driver.find_elements(By.XPATH,
                "//*[contains(text(),'Create') or contains(text(),'New Course') or contains(text(),'Add Course') or contains(text(),'+ Course')]")
            if btns:
                log(f"  Found button: '{btns[0].text}'")
                btns[0].click()
                time.sleep(3)
                screenshot(driver, "14_create_course_form")
                body = driver.find_element(By.TAG_NAME, "body").text
                if any(kw in body.lower() for kw in ["title", "description", "create", "form", "new course"]):
                    record("Create Course UI", "pass", "Course creation form accessible")

                    # Try filling the form
                    try:
                        title_input = driver.find_element(By.CSS_SELECTOR, "input[name='title'], input[placeholder*='itle'], #title")
                        title_input.clear()
                        title_input.send_keys(f"UI Test Course {datetime.now().strftime('%H%M%S')}")
                        desc_fields = driver.find_elements(By.CSS_SELECTOR, "textarea[name='description'], textarea, [contenteditable='true']")
                        if desc_fields:
                            desc_fields[0].clear()
                            desc_fields[0].send_keys("Test course created via automated UI testing")
                        screenshot(driver, "14b_create_course_filled")
                        log("  Filled course creation form")
                    except Exception as e:
                        log(f"  Could not fill form: {e}")
                else:
                    record("Create Course UI", "warn", f"Clicked but got: {body[:150]}")
            else:
                record("Create Course UI", "warn", "No create button found")
                screenshot(driver, "14_courses_no_create")
        except Exception as e:
            record("Create Course UI", "fail", f"Error: {e}")


    # ── Step 19: Try enrolling ──────────────────────────────────────────
    log(f"\n[{step}] Testing enrollment...")
    step += 1

    if available_courses and lms_token:
        target = available_courses[0]
        tid = target.get("id")
        log(f"  Enrolling in: {target.get('title', tid)}")
        s, d = api_post(f"{LMS_API}/api/v1/enrollments", {"course_id": tid}, lms_token)
        if s in [200, 201]:
            record("Enrollment API", "pass", f"Enrolled in course {tid}")
        elif s == 409 or "already" in str(d).lower():
            record("Enrollment API", "pass", "Already enrolled")
        elif s == 401:
            record("Enrollment API", "fail", "401 token rejected")
        elif s == 429:
            record("Enrollment API", "warn", "429 rate limited")
        else:
            record("Enrollment API", "fail", f"Status {s}: {d}")
    else:
        record("Enrollment API", "warn", "No courses available or no token")

    # UI enrollment
    if authenticated:
        driver.get(f"{LMS_BASE}/courses")
        time.sleep(3)
        try:
            enroll_btns = driver.find_elements(By.XPATH,
                "//*[contains(text(),'Enroll') or contains(text(),'Start Learning')]")
            if enroll_btns:
                enroll_btns[0].click()
                time.sleep(3)
                screenshot(driver, "15_enrollment_result")
                record("Enrollment UI", "pass", f"Clicked Enroll button: '{enroll_btns[0].text}'")
            else:
                # Try clicking into a course first
                links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/courses/']")
                filtered = [l for l in links if l.get_attribute('href') != f"{LMS_BASE}/courses" and '/courses/' in l.get_attribute('href')]
                if filtered:
                    filtered[0].click()
                    time.sleep(3)
                    screenshot(driver, "15_course_detail_ui")
                    enroll2 = driver.find_elements(By.XPATH, "//*[contains(text(),'Enroll')]")
                    if enroll2:
                        enroll2[0].click()
                        time.sleep(2)
                        screenshot(driver, "15b_enrollment_clicked")
                        record("Enrollment UI", "pass", "Enrolled via course detail page")
                    else:
                        record("Enrollment UI", "warn", "No enroll button on detail page")
                else:
                    record("Enrollment UI", "warn", "No courses to click into")
        except Exception as e:
            record("Enrollment UI", "warn", f"Error: {e}")


    # ── Step 20: Check certifications ───────────────────────────────────
    log(f"\n[{step}] Checking certifications...")
    step += 1

    if authenticated:
        driver.get(f"{LMS_BASE}/certifications")
        time.sleep(3)
        screenshot(driver, "16_certifications_detail")
        body = driver.find_element(By.TAG_NAME, "body").text
        if "no certificate" in body.lower() or "don't have" in body.lower() or "empty" in body.lower():
            record("Certifications UI", "pass", "No certificates yet (expected for this user)")
        elif "certificate" in body.lower():
            record("Certifications UI", "pass", f"Certificates page: {body[:150]}")
        else:
            record("Certifications UI", "warn", f"Content: {body[:150]}")

    if lms_token:
        s, d = api_get(f"{LMS_API}/api/v1/certificates/my", lms_token)
        if s == 200:
            record("Certifications API", "pass", str(d)[:120])
        elif s == 429:
            record("Certifications API", "warn", "429 rate limited")
        else:
            record("Certifications API", "fail", f"Status {s}")


    # ── Step 21: Course detail page ─────────────────────────────────────
    log(f"\n[{step}] Testing course detail page...")
    step += 1

    if authenticated:
        driver.get(f"{LMS_BASE}/courses")
        time.sleep(2)
        try:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/courses/']")
            filtered = [l for l in links if l.get_attribute('href') != f"{LMS_BASE}/courses"]
            if filtered:
                href = filtered[0].get_attribute('href')
                driver.get(href)
                time.sleep(3)
                screenshot(driver, "17_course_detail")
                body = driver.find_element(By.TAG_NAME, "body").text
                kw = ["module", "lesson", "description", "enroll", "instructor", "content", "quiz", "discussion", "rating"]
                found = [k for k in kw if k in body.lower()]
                record("Course Detail UI", "pass" if found else "warn",
                       f"Keywords: {found}" if found else body[:150])
            else:
                record("Course Detail UI", "warn", "No course links found")
        except Exception as e:
            record("Course Detail UI", "fail", f"Error: {e}")


    # ── Step 22: Final dashboard ────────────────────────────────────────
    log(f"\n[{step}] Final dashboard screenshot...")
    step += 1

    driver.get(f"{LMS_BASE}/dashboard")
    time.sleep(3)
    screenshot(driver, "18_final_dashboard")
    body = driver.find_element(By.TAG_NAME, "body").text
    log(f"  Body: {body[:400]}")

    stats_kw = ["total courses", "enrollments", "completed", "certificates", "compliance"]
    found_stats = [k for k in stats_kw if k in body.lower()]
    if found_stats:
        record("Dashboard Stats", "pass", f"Stats: {found_stats}")
    elif "dashboard" in body.lower():
        record("Dashboard Stats", "warn", f"Dashboard loaded but stats unclear")
    else:
        record("Dashboard Stats", "warn", f"Not on dashboard: {body[:100]}")


    # ── File bugs for 404 pages ─────────────────────────────────────────
    if pages_404:
        file_bug(f"Frontend pages return 404: {', '.join(pages_404)}",
                 f"**Issue:** The following LMS frontend routes return 404:\n\n"
                 + "\n".join(f"- `{LMS_BASE}{p}`" for p in pages_404) +
                 f"\n\n**Expected:** Each page should render its respective content\n"
                 f"**Actual:** 404 / Not Found\n\n"
                 f"**Pages that DO work:** {', '.join(pages_ok) if pages_ok else 'None tested successfully'}")


finally:
    driver.quit()
    log("\n  Browser closed.")

# ── Summary ─────────────────────────────────────────────────────────────
log("\n" + "=" * 70)
log("TEST SUMMARY")
log("=" * 70)

passed = sum(1 for r in test_results if r["status"] == "pass")
failed = sum(1 for r in test_results if r["status"] == "fail")
warned = sum(1 for r in test_results if r["status"] == "warn")

log(f"\nTotal: {len(test_results)} | Passed: {passed} | Failed: {failed} | Warnings: {warned}")
log(f"\nBugs filed ({len(bugs_filed)}):")
for b in bugs_filed:
    log(f"  - {b}")
log(f"\nAll results:")
for r in test_results:
    log(f"  [{r['status'].upper():4s}] {r['test']}: {r['details']}")
log(f"\nScreenshots: {SCREENSHOT_DIR}")
log("=" * 70)
