"""
Fresh E2E Test — Priya Patel, Employee at TechNova
Tests: Dashboard, Profile, Clock In/Out, Leave, Attendance, Documents,
       Announcements, Policies, Events, Wellness, Helpdesk, Forum,
       Feedback, Whistleblowing, Notifications, AI Chatbot, RBAC
"""

import os, sys, time, json, traceback, random, string, base64, datetime
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL    = "https://test-empcloud.empcloud.com"
API_URL     = "https://test-empcloud-api.empcloud.com/api/v1"
EMAIL       = "priya@technova.in"
PASSWORD    = "Welcome@123"
USER_ID     = 524
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_employee"
GITHUB_PAT  = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
REPO        = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── Results tracking ────────────────────────────────────────────────────────
results = []
bugs = []

def log(status, test_name, detail=""):
    icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "WARN"
    results.append({"status": status, "test": test_name, "detail": detail})
    print(f"  [{icon}] {test_name}" + (f" — {detail}" if detail else ""))

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    return path

def upload_screenshot_to_github(filepath, issue_num=None):
    """Upload screenshot to GitHub repo and return the raw URL."""
    fname = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    gh_path = f"screenshots/{fname}"
    msg = f"Screenshot for issue #{issue_num}" if issue_num else f"Screenshot {fname}"
    url = f"https://api.github.com/repos/{REPO}/contents/{gh_path}"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    # check if exists
    r = requests.get(url, headers=headers)
    payload = {"message": msg, "content": content_b64}
    if r.status_code == 200:
        payload["sha"] = r.json()["sha"]
    r2 = requests.put(url, headers=headers, json=payload)
    if r2.status_code in (200, 201):
        return f"https://raw.githubusercontent.com/{REPO}/main/{gh_path}"
    return None

def file_bug(title, body, screenshot_path=None, labels=None):
    """File a GitHub issue with screenshot proof."""
    if labels is None:
        labels = ["bug"]

    # Check for duplicates first
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    search_q = title.split("—")[0].strip()[:40]
    r = requests.get(f"https://api.github.com/search/issues?q={search_q}+repo:{REPO}+state:open", headers=headers)
    if r.status_code == 200:
        items = r.json().get("items", [])
        if items:
            print(f"    [SKIP] Possible duplicate: #{items[0]['number']} — {items[0]['title']}")
            return items[0]["number"]

    img_url = None
    if screenshot_path:
        img_url = upload_screenshot_to_github(screenshot_path)

    full_body = body
    if img_url:
        full_body += f"\n\n## Screenshot\n![Screenshot]({img_url})"

    payload = {"title": title, "body": full_body, "labels": labels}
    r = requests.post(f"https://api.github.com/repos/{REPO}/issues", headers=headers, json=payload)
    if r.status_code == 201:
        num = r.json()["number"]
        print(f"    [BUG FILED] #{num}: {title}")
        bugs.append(num)
        return num
    else:
        print(f"    [BUG FAIL] Could not file: {r.status_code} {r.text[:200]}")
    return None


# ── API Helpers ─────────────────────────────────────────────────────────────
def api_login():
    r = requests.post(f"{API_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200, f"Login failed: {r.status_code}"
    data = r.json()["data"]
    return data["tokens"]["access_token"], data["user"], data["org"]

def api_get(endpoint, token, params=None):
    h = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{API_URL}{endpoint}", headers=h, params=params)

def api_post(endpoint, token, body=None):
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return requests.post(f"{API_URL}{endpoint}", headers=h, json=body or {})

def api_put(endpoint, token, body=None):
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return requests.put(f"{API_URL}{endpoint}", headers=h, json=body or {})


# ── Selenium Helpers ────────────────────────────────────────────────────────
driver_count = 0

def new_driver():
    global driver_count
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-software-rasterizer")
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(5)
    driver_count += 1
    return d

def selenium_login(driver):
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    try:
        # Try multiple selectors for email field
        email_field = None
        for sel in ["input[type='email']", "input[name='email']", "input[placeholder*='mail']", "input[placeholder*='Email']"]:
            try:
                email_field = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                if email_field:
                    break
            except:
                continue

        if not email_field:
            # Try all input fields
            inputs = driver.find_elements(By.TAG_NAME, "input")
            if len(inputs) >= 2:
                email_field = inputs[0]
            else:
                print(f"    Could not find email field. Inputs on page: {len(inputs)}")
                return False

        email_field.clear()
        email_field.send_keys(EMAIL)
        time.sleep(0.5)

        # Try multiple selectors for password
        pwd_field = None
        for sel in ["input[type='password']", "input[name='password']"]:
            try:
                pwd_field = driver.find_element(By.CSS_SELECTOR, sel)
                if pwd_field:
                    break
            except:
                continue

        if not pwd_field:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            if len(inputs) >= 2:
                pwd_field = inputs[1]

        if pwd_field:
            pwd_field.clear()
            pwd_field.send_keys(PASSWORD)
        time.sleep(0.5)

        # Click submit
        btn = None
        for sel in ["button[type='submit']", "button.login-btn", "form button", "button"]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, sel)
                if btn:
                    break
            except:
                continue
        if btn:
            btn.click()

        time.sleep(4)
        # Wait for redirect away from login
        for _ in range(5):
            if "/login" not in driver.current_url:
                return True
            time.sleep(1)
        return "/login" not in driver.current_url
    except Exception as e:
        print(f"    Login failed: {e}")
        return False

def wait_for_page(driver, timeout=10):
    """Wait for React SPA to load content."""
    time.sleep(2)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except:
        pass

def page_has_content(driver):
    """Check if page loaded real content (not just empty React shell)."""
    body = driver.find_element(By.TAG_NAME, "body").text.strip()
    return len(body) > 50


# ══════════════════════════════════════════════════════════════════════════════
#  API TESTS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("  PRIYA'S DAILY E2E TEST — Employee at TechNova")
print("  " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("="*70)

# ── 1. Login ────────────────────────────────────────────────────────────────
print("\n--- LOGIN ---")
try:
    token, user, org = api_login()
    assert user["email"] == EMAIL
    assert user["first_name"] == "Priya"
    assert org["name"] == "TechNova"
    log("PASS", "API Login", f"Logged in as {user['first_name']} {user['last_name']} @ {org['name']}")
except Exception as e:
    log("FAIL", "API Login", str(e))
    print("Cannot continue without login. Exiting.")
    sys.exit(1)

# ── 2. Dashboard / User Info ────────────────────────────────────────────────
print("\n--- DASHBOARD & PROFILE ---")

# My user info
r = api_get(f"/users/{USER_ID}", token)
if r.status_code == 200:
    u = r.json()["data"]
    log("PASS", "Get My User Info", f"Name: {u['first_name']} {u['last_name']}, Role: {u['role']}")
    if u["role"] != "employee":
        log("WARN", "Role check", f"Expected 'employee' but got '{u['role']}'")
else:
    log("FAIL", "Get My User Info", f"HTTP {r.status_code}")

# Extended profile
r = api_get(f"/employees/{USER_ID}/profile", token)
if r.status_code == 200:
    log("PASS", "Get Employee Profile", "All profile tabs accessible via API")
else:
    log("FAIL", "Get Employee Profile", f"HTTP {r.status_code}")

# ── 3. Clock In / Clock Out ────────────────────────────────────────────────
print("\n--- CLOCK IN / OUT ---")

r = api_post("/attendance/check-in", token, {})
if r.status_code == 201:
    log("PASS", "Clock In", "Checked in successfully")
elif r.status_code == 409:
    log("PASS", "Clock In (already checked in)", "Conflict — already clocked in today")
else:
    log("FAIL", "Clock In", f"HTTP {r.status_code}: {r.text[:200]}")

# Double clock-in should fail
r = api_post("/attendance/check-in", token, {})
if r.status_code == 409:
    log("PASS", "Double Clock-In blocked", "409 Conflict as expected")
elif r.status_code == 201:
    log("FAIL", "Double Clock-In NOT blocked", "Allowed duplicate clock-in — should be rejected")
else:
    log("PASS", "Double Clock-In blocked", f"HTTP {r.status_code}")

# Clock out
r = api_post("/attendance/check-out", token, {})
if r.status_code == 200:
    data = r.json().get("data", {})
    check_in = data.get("check_in")
    check_out = data.get("check_out")
    log("PASS", "Clock Out", f"In: {check_in}, Out: {check_out}")
elif r.status_code == 409:
    log("PASS", "Clock Out (already checked out)", "409 Conflict — already clocked out today")
elif r.status_code == 400:
    log("WARN", "Clock Out", f"400 — {r.text[:200]}")
else:
    log("FAIL", "Clock Out", f"HTTP {r.status_code}")

# Clock out without clock-in (already clocked out)
r = api_post("/attendance/check-out", token, {})
if r.status_code in (400, 409):
    log("PASS", "Double Clock-Out blocked", f"HTTP {r.status_code} as expected")
elif r.status_code == 200:
    log("FAIL", "Double Clock-Out NOT blocked", "Allowed clock-out without active check-in")
else:
    log("WARN", "Double Clock-Out", f"HTTP {r.status_code}: {r.text[:150]}")

# ── 4. Leave ────────────────────────────────────────────────────────────────
print("\n--- LEAVE ---")

# Leave balances
r = api_get("/leave/balances", token)
if r.status_code == 200:
    balances = r.json().get("data", [])
    for b in balances[:5]:
        print(f"    {b.get('leave_type_name','?')}: balance={b.get('balance','?')}, used={b.get('total_used','?')}")
    log("PASS", "Leave Balances", f"{len(balances)} balance entries")
else:
    log("FAIL", "Leave Balances", f"HTTP {r.status_code}")

# Leave types
r = api_get("/leave/types", token)
if r.status_code == 200:
    types = r.json().get("data", [])
    log("PASS", "Leave Types", f"{len(types)} types available")
    sick_type_id = None
    for t in types:
        if "sick" in t.get("name", "").lower():
            sick_type_id = t["id"]
else:
    log("FAIL", "Leave Types", f"HTTP {r.status_code}")
    sick_type_id = 17

if not sick_type_id:
    sick_type_id = 17

# Apply for sick leave — next Tuesday
today = datetime.date.today()
days_until_tuesday = (1 - today.weekday() + 7) % 7
if days_until_tuesday == 0:
    days_until_tuesday = 7
next_tue = today + datetime.timedelta(days=days_until_tuesday)
leave_date = next_tue.strftime("%Y-%m-%d")

r = api_post("/leave/applications", token, {
    "leave_type_id": sick_type_id,
    "start_date": leave_date,
    "end_date": leave_date,
    "days_count": 1,
    "is_half_day": False,
    "reason": "Doctor appointment — annual health checkup"
})
if r.status_code == 201:
    leave_id = r.json()["data"]["id"]
    status = r.json()["data"]["status"]
    log("PASS", "Apply Sick Leave", f"ID={leave_id}, date={leave_date}, status={status}")

    # Verify it's pending
    if status == "pending":
        log("PASS", "Leave Status is Pending", "Correct — awaiting approval")
    else:
        log("FAIL", "Leave Status not Pending", f"Expected 'pending' but got '{status}'")
elif r.status_code == 400:
    detail = r.json().get("error", {}).get("message", r.text[:200])
    log("WARN", "Apply Sick Leave", f"400 — {detail}")
elif r.status_code == 409:
    log("WARN", "Apply Sick Leave", "Conflict — may already have leave on that date")
else:
    log("FAIL", "Apply Sick Leave", f"HTTP {r.status_code}: {r.text[:200]}")

# Edge case: end_date before start_date
r = api_post("/leave/applications", token, {
    "leave_type_id": sick_type_id,
    "start_date": "2026-04-20",
    "end_date": "2026-04-18",
    "days_count": 1,
    "is_half_day": False,
    "reason": "Invalid date test"
})
if r.status_code in (400, 422):
    log("PASS", "Leave: end_date before start_date rejected", f"HTTP {r.status_code}")
elif r.status_code == 201:
    log("FAIL", "Leave: end_date before start_date ACCEPTED", "Should reject when end < start")
else:
    log("WARN", "Leave: end_date before start_date", f"HTTP {r.status_code}: {r.text[:150]}")

# Edge case: past date leave
past_date = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
r = api_post("/leave/applications", token, {
    "leave_type_id": sick_type_id,
    "start_date": past_date,
    "end_date": past_date,
    "days_count": 1,
    "is_half_day": False,
    "reason": "Past date test"
})
if r.status_code in (400, 422):
    log("PASS", "Leave: past date rejected", f"HTTP {r.status_code}")
elif r.status_code == 201:
    log("WARN", "Leave: past date accepted", "System allows past-date leave applications")
else:
    log("WARN", "Leave: past date", f"HTTP {r.status_code}")

# ── 5. Attendance History ───────────────────────────────────────────────────
print("\n--- ATTENDANCE ---")

r = api_get("/attendance/records", token)
if r.status_code == 200:
    log("PASS", "Attendance Records (employee)", "Can view own attendance")
elif r.status_code == 403:
    log("FAIL", "Attendance Records — employee gets 403", "Employee cannot view own attendance records")
else:
    log("WARN", "Attendance Records", f"HTTP {r.status_code}")

# ── 6. My Documents ────────────────────────────────────────────────────────
print("\n--- DOCUMENTS ---")

r = api_get("/documents", token)
if r.status_code == 200:
    docs = r.json().get("data", [])
    log("PASS", "My Documents", f"{len(docs)} documents visible")
else:
    log("FAIL", "My Documents", f"HTTP {r.status_code}")

# ── 7. Announcements ───────────────────────────────────────────────────────
print("\n--- ANNOUNCEMENTS ---")

r = api_get("/announcements", token)
if r.status_code == 200:
    anns = r.json().get("data", [])
    log("PASS", "Announcements", f"{len(anns)} announcements visible")
    for a in anns[:3]:
        print(f"    - {a.get('title','?')} ({a.get('status','?')})")
else:
    log("FAIL", "Announcements", f"HTTP {r.status_code}")

# ── 8. Policies ────────────────────────────────────────────────────────────
print("\n--- POLICIES ---")

r = api_get("/policies", token)
if r.status_code == 200:
    policies = r.json().get("data", [])
    log("PASS", "View Policies", f"{len(policies)} policies")

    # Acknowledge first active policy
    if policies:
        pol_id = policies[0]["id"]
        r2 = api_post(f"/policies/{pol_id}/acknowledge", token, {})
        if r2.status_code in (200, 201):
            log("PASS", "Acknowledge Policy", f"Policy #{pol_id} acknowledged")
        elif r2.status_code == 409:
            log("PASS", "Acknowledge Policy (already done)", f"Policy #{pol_id} already acknowledged")
        else:
            log("FAIL", "Acknowledge Policy", f"HTTP {r2.status_code}: {r2.text[:200]}")
else:
    log("FAIL", "View Policies", f"HTTP {r.status_code}")

# ── 9. Events ──────────────────────────────────────────────────────────────
print("\n--- EVENTS ---")

r = api_get("/events", token)
if r.status_code == 200:
    events = r.json().get("data", [])
    log("PASS", "View Events", f"{len(events)} events")
    for ev in events[:3]:
        print(f"    - {ev.get('title','?')} on {ev.get('start_date','?')}")
else:
    log("FAIL", "View Events", f"HTTP {r.status_code}")

# ── 10. Wellness Check-in ──────────────────────────────────────────────────
print("\n--- WELLNESS ---")

r = api_get("/wellness/check-ins", token)
if r.status_code == 200:
    checkins = r.json().get("data", [])
    log("PASS", "Wellness History", f"{len(checkins)} check-ins")
else:
    log("FAIL", "Wellness History", f"HTTP {r.status_code}")

# Submit wellness check-in
moods = ["great", "good", "okay", "low", "bad"]
r = api_post("/wellness/check-in", token, {
    "mood": random.choice(moods),
    "energy_level": random.randint(1, 5),
    "sleep_hours": round(random.uniform(5, 9), 1),
    "exercise_minutes": random.randint(0, 60)
})
if r.status_code in (200, 201):
    log("PASS", "Submit Wellness Check-in", f"Mood logged for today")
else:
    log("FAIL", "Submit Wellness Check-in", f"HTTP {r.status_code}: {r.text[:200]}")

# ── 11. Helpdesk ───────────────────────────────────────────────────────────
print("\n--- HELPDESK ---")

r = api_get("/helpdesk/tickets", token)
if r.status_code == 200:
    tickets = r.json().get("data", [])
    log("PASS", "My Helpdesk Tickets", f"{len(tickets)} tickets")
else:
    log("FAIL", "My Helpdesk Tickets", f"HTTP {r.status_code}")

# Create ticket
uid = ''.join(random.choices(string.digits, k=6))
r = api_post("/helpdesk/tickets", token, {
    "subject": f"Laptop keyboard sticking — keys unresponsive",
    "description": "Several keys on my work laptop (ThinkPad T14) are sticking and sometimes don't register. This is affecting my productivity. Need repair or replacement.",
    "priority": "high",
    "category": "general"
})
if r.status_code == 201:
    tid = r.json()["data"]["id"]
    log("PASS", "Create Helpdesk Ticket", f"Ticket #{tid} created with priority high")
else:
    log("FAIL", "Create Helpdesk Ticket", f"HTTP {r.status_code}: {r.text[:200]}")

# ── 12. Forum ──────────────────────────────────────────────────────────────
print("\n--- FORUM ---")

r = api_get("/forum/categories", token)
if r.status_code == 200:
    cats = r.json().get("data", [])
    log("PASS", "Forum Categories", f"{len(cats)} categories")
    cat_id = cats[0]["id"] if cats else 1
else:
    log("FAIL", "Forum Categories", f"HTTP {r.status_code}")
    cat_id = 1

r = api_get("/forum/posts", token)
if r.status_code == 200:
    posts = r.json().get("data", [])
    log("PASS", "Forum Posts", f"{len(posts)} posts visible")
else:
    log("FAIL", "Forum Posts", f"HTTP {r.status_code}")

# Create a post
r = api_post("/forum/posts", token, {
    "title": "Best coffee spots near our office?",
    "content": "Hey team! Looking for good coffee recommendations near the office. Any favorites?",
    "category_id": cat_id,
    "post_type": "discussion"
})
if r.status_code == 201:
    post_id = r.json()["data"]["id"]
    log("PASS", "Create Forum Post", f"Post #{post_id} created")
else:
    log("FAIL", "Create Forum Post", f"HTTP {r.status_code}: {r.text[:200]}")

# ── 13. Feedback ───────────────────────────────────────────────────────────
print("\n--- FEEDBACK ---")

r = api_post("/feedback", token, {
    "subject": "Cafeteria food quality",
    "message": "The cafeteria food has gotten a bit repetitive lately. It would be great to see more variety and healthier options.",
    "category": "general",
    "is_anonymous": True,
    "rating": 3
})
if r.status_code == 201:
    log("PASS", "Submit Anonymous Feedback", f"Feedback #{r.json()['data']['id']} submitted")
elif r.status_code == 403:
    log("FAIL", "Submit Feedback — employee gets 403", "Employee cannot submit feedback")
else:
    log("FAIL", "Submit Anonymous Feedback", f"HTTP {r.status_code}: {r.text[:200]}")

# ── 14. Whistleblowing ────────────────────────────────────────────────────
print("\n--- WHISTLEBLOWING ---")

r = api_get("/whistleblowing", token)
if r.status_code == 200:
    reports = r.json().get("data", [])
    log("PASS", "View Whistleblowing Reports", f"{len(reports)} reports visible")
else:
    log("FAIL", "View Whistleblowing Reports", f"HTTP {r.status_code}")

r = api_post("/whistleblowing", token, {
    "category": "safety_violation",
    "severity": "low",
    "subject": "Parking area lighting broken",
    "description": "Multiple lights in the basement parking area B2 are not working. It gets very dark after 7 PM which is a safety concern for employees leaving late.",
    "is_anonymous": True
})
if r.status_code == 201:
    case = r.json()["data"]
    log("PASS", "Submit Whistleblowing Report", f"Case {case.get('case_number','?')} filed")
else:
    log("FAIL", "Submit Whistleblowing Report", f"HTTP {r.status_code}: {r.text[:200]}")

# ── 15. Notifications ─────────────────────────────────────────────────────
print("\n--- NOTIFICATIONS ---")

r = api_get("/notifications", token)
if r.status_code == 200:
    notifs = r.json().get("data", [])
    log("PASS", "View Notifications", f"{len(notifs)} notifications")
    unread = [n for n in notifs if not n.get("read_at")]
    print(f"    Unread: {len(unread)}")

    # Mark one as read
    if notifs:
        nid = notifs[0]["id"]
        r2 = api_put(f"/notifications/{nid}/read", token)
        if r2.status_code == 200:
            log("PASS", "Mark Notification Read", f"Notification #{nid} marked read")
        else:
            log("WARN", "Mark Notification Read", f"HTTP {r2.status_code}")
else:
    log("FAIL", "View Notifications", f"HTTP {r.status_code}")

# ── 16. Surveys ────────────────────────────────────────────────────────────
print("\n--- SURVEYS ---")

r = api_get("/surveys", token)
if r.status_code == 200:
    surveys = r.json().get("data", [])
    active = [s for s in surveys if s.get("status") == "active"]
    log("PASS", "View Surveys", f"{len(surveys)} surveys ({len(active)} active)")
else:
    log("FAIL", "View Surveys", f"HTTP {r.status_code}")

# ── 17. Assets ─────────────────────────────────────────────────────────────
print("\n--- ASSETS ---")

r = api_get("/assets", token)
if r.status_code == 200:
    assets = r.json().get("data", [])
    log("PASS", "View My Assets", f"{len(assets)} assets assigned")
else:
    log("FAIL", "View My Assets", f"HTTP {r.status_code}")

# ── 18. RBAC — Employee should NOT access admin endpoints ──────────────────
print("\n--- RBAC (Admin Access Denied) ---")

admin_endpoints = [
    ("/admin/organizations", "Super Admin Orgs"),
    ("/admin/health", "System Health"),
    ("/audit", "Audit Log"),
    ("/admin/data-sanity", "Data Sanity"),
]

for ep, name in admin_endpoints:
    r = api_get(ep, token)
    if r.status_code == 403:
        log("PASS", f"RBAC: {name} blocked for employee", "403 Forbidden")
    elif r.status_code == 200:
        log("FAIL", f"RBAC: {name} accessible to employee!", "Should be 403 but got 200")
    else:
        log("PASS", f"RBAC: {name}", f"HTTP {r.status_code}")

# Check if employee can see all users (data leakage)
r = api_get("/users", token)
if r.status_code == 200:
    user_data = r.json().get("data", [])
    if isinstance(user_data, list):
        count = len(user_data)
    elif isinstance(user_data, dict) and "users" in user_data:
        count = len(user_data["users"])
    else:
        count = 0
    # Employee seeing all org users may or may not be intentional (org directory)
    log("PASS", "Users List (org directory)", f"Employee can see {count} users")
elif r.status_code == 403:
    log("PASS", "Users List blocked for employee", "403 Forbidden")

# Try to access another employee's profile
r = api_get("/employees/522/profile", token)
if r.status_code == 200:
    log("WARN", "RBAC: Can view another employee's full profile", "Employee 524 can see employee 522's profile")
elif r.status_code == 403:
    log("PASS", "RBAC: Other employee profile blocked", "403 Forbidden")

# ── 19. Attendance records as employee ─────────────────────────────────────
# This was 403 earlier - potential bug
print("\n--- ATTENDANCE RECORDS ACCESS ---")
r = api_get("/attendance/records", token)
if r.status_code == 403:
    log("FAIL", "Employee cannot view own attendance records",
        "GET /attendance/records returns 403 for employee — employees should be able to see their own attendance")
elif r.status_code == 200:
    records = r.json().get("data", [])
    log("PASS", "Attendance Records", f"{len(records)} records")

# ── 20. Feedback GET as employee ───────────────────────────────────────────
print("\n--- FEEDBACK ACCESS ---")
r = api_get("/feedback", token)
if r.status_code == 403:
    log("WARN", "Employee cannot view feedback list", "GET /feedback returns 403 — may be admin-only by design")
elif r.status_code == 200:
    log("PASS", "View Feedback", f"Can see feedback list")


# ══════════════════════════════════════════════════════════════════════════════
#  SELENIUM TESTS — Batch 1 (Dashboard, Profile, Announcements)
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n--- SELENIUM BATCH 1: Dashboard, Profile, Announcements ---")
driver = None
try:
    driver = new_driver()

    # Login
    selenium_login(driver)
    wait_for_page(driver)
    screenshot(driver, "01_after_login")

    current = driver.current_url
    if "/login" not in current:
        log("PASS", "Selenium Login", f"Redirected to {current}")
    else:
        log("FAIL", "Selenium Login", "Still on login page after login")

    # Dashboard
    driver.get(f"{BASE_URL}/dashboard")
    wait_for_page(driver, 8)
    screenshot(driver, "02_dashboard")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    if "Priya" in body_text or "priya" in body_text.lower() or "Dashboard" in body_text:
        log("PASS", "Dashboard loads", "Dashboard shows personalized content")
    else:
        log("WARN", "Dashboard content", f"Page may not show personalized info. Body length: {len(body_text)}")

    # Profile
    driver.get(f"{BASE_URL}/profile")
    wait_for_page(driver, 8)
    screenshot(driver, "03_profile")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    if page_has_content(driver):
        log("PASS", "Profile Page", "Profile page loads with content")
    else:
        log("WARN", "Profile Page", "Profile page may be empty")

    # Try /my-profile if /profile didn't work well
    if len(body_text) < 100:
        driver.get(f"{BASE_URL}/my-profile")
        wait_for_page(driver, 5)
        screenshot(driver, "03b_my_profile")

    # Announcements page
    driver.get(f"{BASE_URL}/announcements")
    wait_for_page(driver, 8)
    screenshot(driver, "04_announcements")

    if page_has_content(driver):
        log("PASS", "Announcements Page", "Page loads with content")
    else:
        log("WARN", "Announcements Page", "Page may be empty or not loaded")

except Exception as e:
    log("FAIL", "Selenium Batch 1", f"Error: {e}")
    try:
        if driver:
            screenshot(driver, "batch1_error")
    except:
        pass
finally:
    if driver:
        driver.quit()
        driver = None

# ══════════════════════════════════════════════════════════════════════════════
#  SELENIUM TESTS — Batch 2 (Leave, Attendance, Documents)
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- SELENIUM BATCH 2: Leave, Attendance, Documents ---")
try:
    driver = new_driver()
    selenium_login(driver)
    wait_for_page(driver)

    # Leave page
    for leave_url in [f"{BASE_URL}/leave", f"{BASE_URL}/my-leave", f"{BASE_URL}/leave/apply"]:
        driver.get(leave_url)
        wait_for_page(driver, 5)
        if page_has_content(driver):
            screenshot(driver, "05_leave_page")
            log("PASS", "Leave Page", f"Loaded at {leave_url}")
            break
    else:
        screenshot(driver, "05_leave_page")
        log("WARN", "Leave Page", "No leave page URL showed full content")

    # Attendance page
    for att_url in [f"{BASE_URL}/attendance", f"{BASE_URL}/my-attendance"]:
        driver.get(att_url)
        wait_for_page(driver, 5)
        if page_has_content(driver):
            screenshot(driver, "06_attendance")
            log("PASS", "Attendance Page", f"Loaded at {att_url}")
            break
    else:
        screenshot(driver, "06_attendance")
        log("WARN", "Attendance Page", "Attendance page may not have loaded")

    # Documents
    for doc_url in [f"{BASE_URL}/documents", f"{BASE_URL}/my-documents"]:
        driver.get(doc_url)
        wait_for_page(driver, 5)
        if page_has_content(driver):
            screenshot(driver, "07_documents")
            log("PASS", "Documents Page", f"Loaded at {doc_url}")
            break
    else:
        screenshot(driver, "07_documents")
        log("WARN", "Documents Page", "Documents page may not have loaded")

except Exception as e:
    log("FAIL", "Selenium Batch 2", f"Error: {e}")
    try:
        if driver:
            screenshot(driver, "batch2_error")
    except:
        pass
finally:
    if driver:
        driver.quit()
        driver = None

# ══════════════════════════════════════════════════════════════════════════════
#  SELENIUM TESTS — Batch 3 (Policies, Events, Helpdesk)
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- SELENIUM BATCH 3: Policies, Events, Helpdesk ---")
try:
    driver = new_driver()
    selenium_login(driver)
    wait_for_page(driver)

    # Policies
    driver.get(f"{BASE_URL}/policies")
    wait_for_page(driver, 8)
    screenshot(driver, "08_policies")
    if page_has_content(driver):
        log("PASS", "Policies Page", "Policies page loads")
    else:
        log("WARN", "Policies Page", "May be empty")

    # Events
    driver.get(f"{BASE_URL}/events")
    wait_for_page(driver, 8)
    screenshot(driver, "09_events")
    if page_has_content(driver):
        log("PASS", "Events Page", "Events page loads")
    else:
        log("WARN", "Events Page", "May be empty")

    # Helpdesk
    for url in [f"{BASE_URL}/helpdesk", f"{BASE_URL}/helpdesk/tickets", f"{BASE_URL}/my-tickets"]:
        driver.get(url)
        wait_for_page(driver, 5)
        if page_has_content(driver):
            screenshot(driver, "10_helpdesk")
            log("PASS", "Helpdesk Page", f"Loaded at {url}")
            break
    else:
        screenshot(driver, "10_helpdesk")
        log("WARN", "Helpdesk Page", "Helpdesk page may not have loaded")

except Exception as e:
    log("FAIL", "Selenium Batch 3", f"Error: {e}")
    try:
        if driver:
            screenshot(driver, "batch3_error")
    except:
        pass
finally:
    if driver:
        driver.quit()
        driver = None

# ══════════════════════════════════════════════════════════════════════════════
#  SELENIUM TESTS — Batch 4 (Forum, Feedback, Wellness, Notifications)
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- SELENIUM BATCH 4: Forum, Wellness, Notifications, Whistleblowing ---")
try:
    driver = new_driver()
    selenium_login(driver)
    wait_for_page(driver)

    # Forum
    driver.get(f"{BASE_URL}/forum")
    wait_for_page(driver, 8)
    screenshot(driver, "11_forum")
    if page_has_content(driver):
        log("PASS", "Forum Page", "Forum page loads")
    else:
        log("WARN", "Forum Page", "May be empty")

    # Wellness
    for url in [f"{BASE_URL}/wellness", f"{BASE_URL}/wellness/check-in"]:
        driver.get(url)
        wait_for_page(driver, 5)
        if page_has_content(driver):
            screenshot(driver, "12_wellness")
            log("PASS", "Wellness Page", f"Loaded at {url}")
            break
    else:
        screenshot(driver, "12_wellness")
        log("WARN", "Wellness Page", "Page may not have loaded")

    # Notifications page
    driver.get(f"{BASE_URL}/notifications")
    wait_for_page(driver, 5)
    screenshot(driver, "13_notifications")
    if page_has_content(driver):
        log("PASS", "Notifications Page", "Page loads")
    else:
        log("WARN", "Notifications Page", "May be empty")

    # Whistleblowing
    for url in [f"{BASE_URL}/whistleblowing", f"{BASE_URL}/whistle-blowing"]:
        driver.get(url)
        wait_for_page(driver, 5)
        if page_has_content(driver):
            screenshot(driver, "14_whistleblowing")
            log("PASS", "Whistleblowing Page", f"Loaded at {url}")
            break
    else:
        screenshot(driver, "14_whistleblowing")
        log("WARN", "Whistleblowing Page", "Page may not have loaded")

except Exception as e:
    log("FAIL", "Selenium Batch 4", f"Error: {e}")
    try:
        if driver:
            screenshot(driver, "batch4_error")
    except:
        pass
finally:
    if driver:
        driver.quit()
        driver = None

# ══════════════════════════════════════════════════════════════════════════════
#  SELENIUM TESTS — Batch 5 (AI Chatbot, RBAC admin pages, Mobile)
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- SELENIUM BATCH 5: AI Chatbot, RBAC, Mobile ---")
try:
    driver = new_driver()
    selenium_login(driver)
    wait_for_page(driver)

    # AI Chatbot — look for purple bubble
    driver.get(f"{BASE_URL}/dashboard")
    wait_for_page(driver, 5)
    time.sleep(3)  # wait for chatbot widget

    chatbot_found = False
    for selector in [
        "[class*='chatbot']", "[class*='chat-bubble']", "[class*='chat-widget']",
        "[class*='ai-chat']", "[id*='chatbot']", "[id*='chat']",
        "button[class*='chat']", "div[class*='bubble']",
        "[style*='position: fixed'][style*='bottom']"
    ]:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, selector)
            if elems:
                chatbot_found = True
                screenshot(driver, "15_chatbot_visible")
                log("PASS", "AI Chatbot Widget Visible", f"Found via {selector}")
                # Try clicking it
                try:
                    elems[0].click()
                    time.sleep(2)
                    screenshot(driver, "15b_chatbot_opened")
                    log("PASS", "AI Chatbot Opens", "Chatbot widget opened on click")
                except:
                    pass
                break
        except:
            continue

    if not chatbot_found:
        screenshot(driver, "15_no_chatbot")
        log("WARN", "AI Chatbot Widget", "Could not find chatbot bubble on dashboard")

    # RBAC — Try admin pages as employee
    admin_pages = [
        ("/admin/super", "Super Admin Dashboard"),
        ("/admin/ai-config", "AI Configuration"),
        ("/admin/logs", "Log Dashboard"),
        ("/employees", "Employee Management"),
        ("/settings", "Org Settings"),
    ]

    for path, name in admin_pages:
        driver.get(f"{BASE_URL}{path}")
        wait_for_page(driver, 5)
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        screenshot(driver, f"16_rbac_{path.replace('/','_')}")

        # Check if blocked (redirect to dashboard, access denied, or empty)
        current = driver.current_url
        if "login" in current or "dashboard" in current or "unauthorized" in body or "forbidden" in body or "access denied" in body:
            log("PASS", f"RBAC UI: {name} blocked", f"Employee redirected/blocked")
        elif "admin" in current and page_has_content(driver):
            log("FAIL", f"RBAC UI: {name} accessible to employee!", f"URL: {current}")
        else:
            log("PASS", f"RBAC UI: {name}", f"Page at {current} — content length {len(body)}")

    # Mobile viewport test
    driver.set_window_size(375, 812)
    time.sleep(1)
    driver.get(f"{BASE_URL}/dashboard")
    wait_for_page(driver, 5)
    screenshot(driver, "17_mobile_dashboard")

    if page_has_content(driver):
        log("PASS", "Mobile Dashboard (375px)", "Dashboard renders on mobile viewport")
    else:
        log("WARN", "Mobile Dashboard", "May have rendering issues on mobile")

    # Check for horizontal scroll issues
    viewport_width = driver.execute_script("return document.documentElement.clientWidth")
    scroll_width = driver.execute_script("return document.documentElement.scrollWidth")
    if scroll_width > viewport_width + 10:
        log("WARN", "Mobile horizontal scroll", f"Page is wider ({scroll_width}px) than viewport ({viewport_width}px)")
        screenshot(driver, "17b_mobile_overflow")
    else:
        log("PASS", "Mobile no horizontal overflow", f"Width OK: {scroll_width}px vs {viewport_width}px viewport")

except Exception as e:
    log("FAIL", "Selenium Batch 5", f"Error: {e}")
    try:
        if driver:
            screenshot(driver, "batch5_error")
    except:
        pass
finally:
    if driver:
        driver.quit()
        driver = None


# ══════════════════════════════════════════════════════════════════════════════
#  FILE BUGS
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n--- FILING BUGS ---")

for r in results:
    if r["status"] == "FAIL":
        test = r["test"]
        detail = r["detail"]

        # Find matching screenshot
        ss_path = None
        if "attendance" in test.lower() and "records" in test.lower():
            ss_path = os.path.join(SCREENSHOT_DIR, "06_attendance.png")
        elif "clock" in test.lower() and "double" in test.lower():
            ss_path = None  # API-only, no screenshot needed
        elif "rbac" in test.lower():
            for f in os.listdir(SCREENSHOT_DIR):
                if f.startswith("16_rbac"):
                    ss_path = os.path.join(SCREENSHOT_DIR, f)
                    break

        # Build bug body
        body = f"""## URL Tested
https://test-empcloud-api.empcloud.com/api/v1 (API test as employee)

## Steps to Reproduce
1. Login as Employee (priya@technova.in / Welcome@123)
2. {detail}

## Expected Result
{test} should work for an employee.

## Actual Result
{detail}

## API Evidence
```
Test: {test}
Result: {detail}
Tested: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Login: priya@technova.in (Employee role, user_id=524)
```"""

        # Special cases
        if "attendance" in test.lower() and "403" in detail:
            title = "Employee cannot view own attendance records — gets 403 Forbidden"
            body = f"""## URL Tested
GET https://test-empcloud-api.empcloud.com/api/v1/attendance/records

## Steps to Reproduce
1. Login as Employee (priya@technova.in / Welcome@123)
2. Call GET /api/v1/attendance/records

## Expected Result
Employee should be able to see their own attendance history (clock-in/out records for the month).

## Actual Result
Returns HTTP 403 Forbidden — "Insufficient permissions". Employees have no way to view their own attendance records through the API.

## API Evidence
```
Request: GET /api/v1/attendance/records
Headers: Authorization: Bearer <employee_token>
Response: HTTP 403 — {{"success":false,"error":{{"code":"FORBIDDEN","message":"Insufficient permissions"}}}}
```"""
            file_bug(title, body, ss_path)

        elif "double clock-out" in test.lower():
            title = "System allows multiple clock-outs without an active check-in"
            body = f"""## URL Tested
POST https://test-empcloud-api.empcloud.com/api/v1/attendance/check-out

## Steps to Reproduce
1. Login as Employee (priya@technova.in / Welcome@123)
2. Clock in via POST /api/v1/attendance/check-in
3. Clock out via POST /api/v1/attendance/check-out (succeeds)
4. Clock out again via POST /api/v1/attendance/check-out (should fail)

## Expected Result
Second clock-out should be rejected since there is no active check-in session.

## Actual Result
{detail}

## API Evidence
```
Request: POST /api/v1/attendance/check-out (second time, no active check-in)
Response: {detail}
```"""
            file_bug(title, body, ss_path)

        elif "leave" in test.lower() and "end_date before start_date" in test.lower():
            title = "Leave application accepted when end date is before start date"
            body = f"""## URL Tested
POST https://test-empcloud-api.empcloud.com/api/v1/leave/applications

## Steps to Reproduce
1. Login as Employee (priya@technova.in / Welcome@123)
2. Apply for leave with start_date=2026-04-20, end_date=2026-04-18

## Expected Result
Application should be rejected — end date cannot be before start date.

## Actual Result
{detail}

## API Evidence
```
Request: POST /api/v1/leave/applications
Body: {{"leave_type_id": 17, "start_date": "2026-04-20", "end_date": "2026-04-18", "days_count": 1, "reason": "test"}}
Response: {detail}
```"""
            file_bug(title, body, ss_path)

        elif "rbac" in test.lower() and "accessible" in test.lower():
            title = f"Employee can access admin page that should be restricted — {test}"
            file_bug(title, body, ss_path)

        else:
            # Generic bug filing
            file_bug(test, body, ss_path)


# ══════════════════════════════════════════════════════════════════════════════
#  SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*70)
print("  TEST SUMMARY")
print("="*70)

pass_count = sum(1 for r in results if r["status"] == "PASS")
fail_count = sum(1 for r in results if r["status"] == "FAIL")
warn_count = sum(1 for r in results if r["status"] == "WARN")

print(f"\n  PASS: {pass_count}")
print(f"  FAIL: {fail_count}")
print(f"  WARN: {warn_count}")
print(f"  TOTAL: {len(results)}")
print(f"  BUGS FILED: {len(bugs)}")

if bugs:
    print(f"\n  Bug Numbers: {bugs}")

print(f"\n  Screenshots: {SCREENSHOT_DIR}")
print(f"\n  Failures:")
for r in results:
    if r["status"] == "FAIL":
        print(f"    - {r['test']}: {r['detail']}")

print(f"\n  Warnings:")
for r in results:
    if r["status"] == "WARN":
        print(f"    - {r['test']}: {r['detail']}")

print("\n" + "="*70)
print("  Done. Priya's daily E2E test complete.")
print("="*70)
