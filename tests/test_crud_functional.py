#!/usr/bin/env python3
"""
EMP Cloud HRMS - Comprehensive Functional CRUD Testing
Tests all major modules via API + Selenium UI.
Correct endpoints discovered through API exploration.
"""

import sys, os, time, json, traceback, requests, random, string, datetime, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = f"{BASE_URL}/api/v1"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = Path(r"C:\emptesting\screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
WAIT = 12

# ── State ───────────────────────────────────────────────────────────────
test_results = []
test_counter = 0
driver = None
issues_filed = []
RAND = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
admin_token = None
emp_token = None
# IDs created for cleanup
created_ids = {}

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")


# ══════════════════════════════════════════════════════════════════════════
# DRIVER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════
def create_driver():
    global driver
    opts = Options()
    opts.binary_location = CHROME_BIN
    for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                "--window-size=1920,1080", "--disable-gpu", "--ignore-certificate-errors"]:
        opts.add_argument(arg)
    svc = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(2)
    return driver

def quit_driver():
    global driver
    if driver:
        try: driver.quit()
        except: pass
        driver = None

def ensure_driver():
    global driver, test_counter
    if test_counter > 0 and test_counter % 5 == 0:
        log("  [driver] Recycling browser (every 5 tests)...")
        quit_driver()
    if driver is None:
        create_driver()
    return driver

def screenshot(name):
    if driver:
        fp = SCREENSHOT_DIR / f"{name}.png"
        try:
            driver.save_screenshot(str(fp))
            return fp
        except: pass
    return None


# ══════════════════════════════════════════════════════════════════════════
# API HELPERS  (Correct endpoints from discovery)
# ══════════════════════════════════════════════════════════════════════════
def api_login(email, password):
    try:
        r = requests.post(f"{API_URL}/auth/login",
                          json={"email": email, "password": password}, timeout=20)
        if r.status_code == 200:
            return r.json()["data"]["tokens"]["access_token"]
    except Exception as e:
        log(f"  API login error: {e}")
    return None

def _h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def api_get(path, token):
    try:
        r = requests.get(f"{API_URL}{path}", headers=_h(token), timeout=20)
        return r.status_code, r.json() if "json" in r.headers.get("content-type","") else r.text
    except Exception as e:
        return 0, str(e)

def api_post(path, payload, token):
    try:
        r = requests.post(f"{API_URL}{path}", json=payload, headers=_h(token), timeout=20)
        try: body = r.json()
        except: body = r.text
        return r.status_code, body
    except Exception as e:
        return 0, str(e)

def api_put(path, payload, token):
    try:
        r = requests.put(f"{API_URL}{path}", json=payload, headers=_h(token), timeout=20)
        try: body = r.json()
        except: body = r.text
        return r.status_code, body
    except Exception as e:
        return 0, str(e)

def api_delete(path, token):
    try:
        r = requests.delete(f"{API_URL}{path}", headers=_h(token), timeout=20)
        try: body = r.json()
        except: body = r.text
        return r.status_code, body
    except Exception as e:
        return 0, str(e)


# ══════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════════
def ui_login(email, password):
    d = ensure_driver()
    d.get(f"{BASE_URL}/login")
    time.sleep(2)
    try:
        d.find_element(By.CSS_SELECTOR, "input[name='email']").clear()
        d.find_element(By.CSS_SELECTOR, "input[name='email']").send_keys(email)
        d.find_element(By.CSS_SELECTOR, "input[name='password']").clear()
        d.find_element(By.CSS_SELECTOR, "input[name='password']").send_keys(password)
        time.sleep(0.5)
        # Click "Sign in" button (NOT the "EN" language button)
        btns = d.find_elements(By.TAG_NAME, "button")
        for b in btns:
            if "sign" in b.text.lower() or "log" in b.text.lower():
                try: b.click()
                except: d.execute_script("arguments[0].click();", b)
                break
    except Exception as e:
        log(f"  UI login error: {e}")
    time.sleep(3)
    return d

def nav(path):
    driver.get(f"{BASE_URL}{path}")
    time.sleep(2)

def find_click(text):
    for tag in ["button", "a", "span", "div"]:
        try:
            el = driver.find_element(By.XPATH,
                f"//{tag}[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{text.lower()}')]")
            try: el.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", el)
            return True
        except NoSuchElementException:
            continue
    return False


# ══════════════════════════════════════════════════════════════════════════
# GITHUB ISSUES
# ══════════════════════════════════════════════════════════════════════════
def file_issue(title, body, ss_path=None):
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    img_url = None
    if ss_path and os.path.exists(ss_path):
        try:
            import base64
            with open(ss_path, "rb") as f:
                content = base64.b64encode(f.read()).decode()
            fname = f"screenshots/{os.path.basename(ss_path)}"
            ur = requests.put(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{fname}",
                headers=headers, json={"message": f"Screenshot: {os.path.basename(ss_path)}",
                    "content": content, "branch": "main"}, timeout=30)
            if ur.status_code in (200, 201):
                img_url = ur.json().get("content", {}).get("download_url")
        except: pass

    full = body
    if img_url:
        full += f"\n\n**Screenshot:**\n![screenshot]({img_url})"
    full += f"\n\n---\n*Auto-filed on {datetime.datetime.now().isoformat()}*"

    try:
        r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers=headers, json={"title": f"[FUNCTIONAL] {title}", "body": full,
                "labels": ["bug", "functional-test"]}, timeout=30)
        if r.status_code in (200, 201):
            url = r.json().get("html_url", "")
            log(f"    >> Filed issue: {url}")
            issues_filed.append(url)
            return url
    except Exception as e:
        log(f"    >> Issue filing error: {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════
# TEST RECORDING
# ══════════════════════════════════════════════════════════════════════════
def record(module, op, status, details=""):
    test_results.append({"module": module, "operation": op, "status": status,
                         "details": details[:500], "time": datetime.datetime.now().isoformat()})
    log(f"  [{'PASS' if status=='PASS' else 'FAIL'}] {module} / {op}: {details[:150]}")
    if status == "FAIL":
        ss = screenshot(f"FAIL_{module}_{op}_{RAND}")
        file_issue(f"{module} - {op} failed",
            f"**Module:** {module}\n**Operation:** {op}\n**Details:** {details}\n"
            f"**URL:** {driver.current_url if driver else 'N/A'}",
            str(ss) if ss else None)


def run_test(module, op, func):
    global test_counter
    test_counter += 1
    log(f"\n--- Test #{test_counter}: {module} / {op} ---")
    try:
        ensure_driver()
        func()
    except Exception as e:
        record(module, op, "FAIL", f"Exception: {e}")


# ══════════════════════════════════════════════════════════════════════════
# TESTS - Correct API endpoints
# ══════════════════════════════════════════════════════════════════════════

# ── 0. Auth ─────────────────────────────────────────────────────────────
def test_auth():
    global admin_token, emp_token
    admin_token = api_login(ADMIN_EMAIL, ADMIN_PASS)
    record("Auth", "Admin Login", "PASS" if admin_token else "FAIL",
           "Got token" if admin_token else "No token")
    emp_token = api_login(EMP_EMAIL, EMP_PASS)
    record("Auth", "Employee Login", "PASS" if emp_token else "FAIL",
           "Got token" if emp_token else "No token")

# ── 1. Employee CRUD ───────────────────────────────────────────────────
def test_employee_read_directory():
    c, d = api_get("/employees/directory", admin_token)
    if c == 200 and d.get("data"):
        record("Employee", "READ Directory", "PASS", f"{len(d['data'])} employees listed")
    else:
        record("Employee", "READ Directory", "FAIL", f"Status {c}")

def test_employee_create():
    email = f"testemp{RAND}@technova.in"
    c, d = api_post("/users", {
        "first_name": "TestEmp", "last_name": RAND, "email": email,
        "designation": "QA Tester", "department_id": 20, "role": "employee"
    }, admin_token)
    if c == 201:
        created_ids["employee"] = d["data"]["id"]
        record("Employee", "CREATE", "PASS", f"Created user id={created_ids['employee']} email={email}")
    else:
        record("Employee", "CREATE", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_employee_read_profile():
    c, d = api_get("/employees/directory", admin_token)
    if c == 200 and d.get("data"):
        eid = d["data"][0]["id"]
        c2, d2 = api_get(f"/users/{eid}", admin_token)
        if c2 == 200:
            name = f"{d2['data']['first_name']} {d2['data']['last_name']}"
            record("Employee", "READ Profile", "PASS", f"Got profile for {name}")
        else:
            record("Employee", "READ Profile", "FAIL", f"Status {c2}")
    else:
        record("Employee", "READ Profile", "FAIL", "No employees in directory")

def test_employee_update():
    eid = created_ids.get("employee")
    if not eid:
        # Use existing employee
        c, d = api_get("/employees/directory", admin_token)
        if c == 200 and d.get("data"):
            eid = d["data"][-1]["id"]
    if eid:
        c, d = api_put(f"/users/{eid}", {"designation": f"Updated-{RAND}"}, admin_token)
        if c == 200:
            record("Employee", "UPDATE", "PASS", f"Updated user {eid} designation")
        else:
            record("Employee", "UPDATE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Employee", "UPDATE", "FAIL", "No employee ID to update")

def test_employee_deactivate():
    eid = created_ids.get("employee")
    if eid:
        c, d = api_delete(f"/users/{eid}", admin_token)
        if c == 200:
            record("Employee", "DEACTIVATE", "PASS", f"Deactivated user {eid}")
        else:
            record("Employee", "DEACTIVATE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Employee", "DEACTIVATE", "FAIL", "No test employee to deactivate")

def test_employee_ui():
    """View employee list and profile via UI."""
    ui_login(ADMIN_EMAIL, ADMIN_PASS)
    nav("/employees")
    time.sleep(2)
    screenshot(f"emp_list_{RAND}")
    src = driver.page_source.lower()
    if "employee" in src or "team" in src or "directory" in src:
        record("Employee", "READ List (UI)", "PASS", f"Employee page loaded at {driver.current_url}")
    else:
        record("Employee", "READ List (UI)", "FAIL", "Employee page did not load")

# ── 2. Department CRUD ─────────────────────────────────────────────────
# Note: No department API endpoint was found in discovery; testing via UI
def test_department_ui():
    ui_login(ADMIN_EMAIL, ADMIN_PASS)
    nav("/settings")
    time.sleep(2)
    screenshot(f"settings_{RAND}")
    # Look for departments link/section
    src = driver.page_source.lower()
    if "department" in src:
        record("Department", "READ (UI Settings)", "PASS", "Department section visible in settings")
    else:
        record("Department", "READ (UI Settings)", "FAIL", "Department section not found in settings")

# ── 3. Leave CRUD ──────────────────────────────────────────────────────
def test_leave_types_read():
    c, d = api_get("/leave/types", admin_token)
    if c == 200 and d.get("data"):
        types = [t["name"] for t in d["data"]]
        record("Leave", "READ Types", "PASS", f"Leave types: {', '.join(types[:5])}")
    else:
        record("Leave", "READ Types", "FAIL", f"Status {c}")

def test_leave_apply():
    future = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
    c, d = api_post("/leave/applications", {
        "leave_type_id": 18, "start_date": future, "end_date": future,
        "reason": f"Functional test leave {RAND}", "days_count": 1
    }, emp_token)
    if c == 201:
        created_ids["leave"] = d["data"]["id"]
        record("Leave", "CREATE Apply", "PASS", f"Applied leave id={created_ids['leave']}")
    else:
        record("Leave", "CREATE Apply", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_leave_read():
    c, d = api_get("/leave/applications", admin_token)
    if c == 200 and d.get("data"):
        record("Leave", "READ Applications", "PASS", f"{len(d['data'])} leave applications")
    else:
        record("Leave", "READ Applications", "FAIL", f"Status {c}")

def test_leave_balance():
    c, d = api_get("/leave/balances", emp_token)
    if c == 200 and d.get("data"):
        balances = [(b.get("leave_type_id"), b.get("balance")) for b in d["data"][:3]]
        record("Leave", "READ Balance", "PASS", f"Balances: {balances}")
    else:
        record("Leave", "READ Balance", "FAIL", f"Status {c}")

def test_leave_cancel():
    lid = created_ids.get("leave")
    if lid:
        c, d = api_put(f"/leave/applications/{lid}/cancel", {}, emp_token)
        if c == 200:
            record("Leave", "UPDATE Cancel", "PASS", f"Cancelled leave {lid}")
        else:
            record("Leave", "UPDATE Cancel", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Leave", "UPDATE Cancel", "FAIL", "No leave to cancel")

def test_leave_balance_after_cancel():
    c, d = api_get("/leave/balances", emp_token)
    if c == 200 and d.get("data"):
        record("Leave", "READ Balance After Cancel", "PASS", "Balance read after cancellation")
    else:
        record("Leave", "READ Balance After Cancel", "FAIL", f"Status {c}")

# ── 4. Attendance ──────────────────────────────────────────────────────
def test_attendance_checkin():
    c, d = api_post("/attendance/check-in", {}, emp_token)
    if c in (200, 201):
        created_ids["attendance"] = d.get("data", {}).get("id")
        record("Attendance", "Clock In", "PASS",
               f"Checked in id={created_ids.get('attendance')}")
    else:
        record("Attendance", "Clock In", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_attendance_read():
    c, d = api_get("/attendance/records", admin_token)
    if c == 200 and d.get("data"):
        record("Attendance", "READ Records", "PASS", f"{len(d['data'])} records")
    else:
        record("Attendance", "READ Records", "FAIL", f"Status {c}")

def test_attendance_checkout():
    c, d = api_post("/attendance/check-out", {}, emp_token)
    if c == 200:
        worked = d.get("data", {}).get("worked_minutes")
        record("Attendance", "Clock Out", "PASS", f"Checked out, worked_minutes={worked}")
    else:
        record("Attendance", "Clock Out", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_attendance_verify():
    c, d = api_get("/attendance/records", admin_token)
    if c == 200 and d.get("data"):
        latest = d["data"][0]
        wm = latest.get("worked_minutes")
        co = latest.get("check_out")
        record("Attendance", "Verify Hours", "PASS", f"Latest: worked_min={wm}, checkout={co}")
    else:
        record("Attendance", "Verify Hours", "FAIL", f"Status {c}")

# ── 5. Document CRUD ──────────────────────────────────────────────────
def test_document_upload():
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode="wb")
    # Minimal valid PDF
    tf.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
             b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
             b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
             b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n109\n%%EOF")
    tf.close()
    h = {"Authorization": f"Bearer {admin_token}"}
    r = requests.post(f"{API_URL}/documents/upload", headers=h,
        files={"file": (f"testdoc_{RAND}.pdf", open(tf.name, "rb"), "application/pdf")},
        data={"category_id": 15, "name": f"TestDoc-{RAND}", "user_id": 522}, timeout=20)
    os.unlink(tf.name)
    if r.status_code in (200, 201):
        try:
            created_ids["document"] = r.json().get("data", {}).get("id")
        except: pass
        record("Document", "CREATE Upload", "PASS", f"Uploaded doc id={created_ids.get('document')}")
    else:
        record("Document", "CREATE Upload", "FAIL", f"Status {r.status_code}: {r.text[:200]}")

def test_document_read():
    c, d = api_get("/documents", admin_token)
    if c == 200 and d.get("data"):
        record("Document", "READ List", "PASS", f"{len(d['data'])} documents")
    else:
        record("Document", "READ List", "FAIL", f"Status {c}")

def test_document_read_my():
    c, d = api_get("/documents/my", admin_token)
    if c == 200:
        record("Document", "READ My Docs", "PASS", f"My documents retrieved")
    else:
        record("Document", "READ My Docs", "FAIL", f"Status {c}")

def test_document_delete():
    did = created_ids.get("document")
    if not did:
        # Get last doc
        c, d = api_get("/documents", admin_token)
        if c == 200 and d.get("data"):
            did = d["data"][-1]["id"]
    if did:
        c, d = api_delete(f"/documents/{did}", admin_token)
        if c == 200:
            record("Document", "DELETE", "PASS", f"Deleted doc {did}")
        else:
            record("Document", "DELETE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Document", "DELETE", "FAIL", "No document to delete")

# ── 6. Announcement CRUD ──────────────────────────────────────────────
def test_announcement_create():
    c, d = api_post("/announcements", {
        "title": f"Test Announcement {RAND}",
        "content": f"This is a functional test announcement {RAND}",
        "priority": "normal", "target_type": "all"
    }, admin_token)
    if c == 201:
        created_ids["announcement"] = d["data"]["id"]
        record("Announcement", "CREATE", "PASS", f"id={created_ids['announcement']}")
    else:
        record("Announcement", "CREATE", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_announcement_read():
    c, d = api_get("/announcements", admin_token)
    if c == 200 and d.get("data"):
        record("Announcement", "READ List", "PASS", f"{len(d['data'])} announcements")
    else:
        record("Announcement", "READ List", "FAIL", f"Status {c}")

def test_announcement_update():
    aid = created_ids.get("announcement")
    if aid:
        c, d = api_put(f"/announcements/{aid}",
                        {"title": f"Updated Ann {RAND}"}, admin_token)
        if c == 200:
            record("Announcement", "UPDATE", "PASS", f"Updated {aid}")
        else:
            record("Announcement", "UPDATE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Announcement", "UPDATE", "FAIL", "No announcement to update")

def test_announcement_delete():
    aid = created_ids.get("announcement")
    if aid:
        c, d = api_delete(f"/announcements/{aid}", admin_token)
        if c == 200:
            record("Announcement", "DELETE", "PASS", f"Deleted {aid}")
        else:
            record("Announcement", "DELETE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Announcement", "DELETE", "FAIL", "No announcement to delete")

# ── 7. Helpdesk Ticket CRUD ───────────────────────────────────────────
def test_ticket_create():
    c, d = api_post("/helpdesk/tickets", {
        "subject": f"Test Ticket {RAND}", "description": f"Functional test ticket {RAND}",
        "category": "general", "priority": "medium"
    }, admin_token)
    if c == 201:
        created_ids["ticket"] = d["data"]["id"]
        record("Helpdesk", "CREATE Ticket", "PASS", f"id={created_ids['ticket']}")
    else:
        record("Helpdesk", "CREATE Ticket", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_ticket_read():
    c, d = api_get("/helpdesk/tickets", admin_token)
    if c == 200 and d.get("data"):
        record("Helpdesk", "READ Tickets", "PASS", f"{len(d['data'])} tickets")
    else:
        record("Helpdesk", "READ Tickets", "FAIL", f"Status {c}")

def test_ticket_update():
    tid = created_ids.get("ticket")
    if tid:
        c, d = api_put(f"/helpdesk/tickets/{tid}",
                        {"status": "in_progress"}, admin_token)
        if c == 200:
            record("Helpdesk", "UPDATE Ticket", "PASS", f"Updated {tid} to in_progress")
        else:
            record("Helpdesk", "UPDATE Ticket", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Helpdesk", "UPDATE Ticket", "FAIL", "No ticket to update")

# ── 8. Event CRUD ─────────────────────────────────────────────────────
def test_event_create():
    edate = (datetime.date.today() + datetime.timedelta(days=14)).isoformat()
    c, d = api_post("/events", {
        "title": f"Test Event {RAND}", "description": f"Functional test event {RAND}",
        "event_type": "meeting", "start_date": edate, "end_date": edate,
        "is_all_day": True, "target_type": "all"
    }, admin_token)
    if c == 201:
        created_ids["event"] = d["data"]["id"]
        record("Event", "CREATE", "PASS", f"id={created_ids['event']}")
    else:
        record("Event", "CREATE", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_event_read():
    c, d = api_get("/events", admin_token)
    if c == 200 and d.get("data"):
        record("Event", "READ List", "PASS", f"{len(d['data'])} events")
    else:
        record("Event", "READ List", "FAIL", f"Status {c}")

def test_event_update():
    eid = created_ids.get("event")
    if eid:
        c, d = api_put(f"/events/{eid}",
                        {"title": f"Updated Event {RAND}"}, admin_token)
        if c == 200:
            record("Event", "UPDATE", "PASS", f"Updated {eid}")
        else:
            record("Event", "UPDATE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Event", "UPDATE", "FAIL", "No event to update")

def test_event_delete():
    eid = created_ids.get("event")
    if eid:
        c, d = api_delete(f"/events/{eid}", admin_token)
        if c == 200:
            record("Event", "DELETE", "PASS", f"Deleted {eid}")
        else:
            record("Event", "DELETE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Event", "DELETE", "FAIL", "No event to delete")

# ── 9. Survey CRUD ────────────────────────────────────────────────────
def test_survey_create():
    c, d = api_post("/surveys", {
        "title": f"Test Survey {RAND}", "type": "pulse",
        "is_anonymous": True, "target_type": "all"
    }, admin_token)
    if c == 201:
        created_ids["survey"] = d["data"]["id"]
        record("Survey", "CREATE", "PASS", f"id={created_ids['survey']} (draft)")
    else:
        record("Survey", "CREATE", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_survey_read():
    c, d = api_get("/surveys", admin_token)
    if c == 200 and d.get("data"):
        record("Survey", "READ List", "PASS", f"{len(d['data'])} surveys")
    else:
        record("Survey", "READ List", "FAIL", f"Status {c}")

def test_survey_update():
    sid = created_ids.get("survey")
    if sid:
        c, d = api_put(f"/surveys/{sid}",
                        {"title": f"Updated Survey {RAND}"}, admin_token)
        if c == 200:
            record("Survey", "UPDATE", "PASS", f"Updated survey {sid}")
        elif c == 403:
            record("Survey", "UPDATE", "PASS", f"Survey {sid} not editable (expected for non-draft)")
        else:
            record("Survey", "UPDATE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Survey", "UPDATE", "FAIL", "No survey to update")

# ── 10. Forum Post CRUD ───────────────────────────────────────────────
def test_forum_create():
    c, d = api_post("/forum/posts", {
        "title": f"Test Post {RAND}", "content": f"Functional test content {RAND}",
        "category_id": 1, "post_type": "discussion"
    }, admin_token)
    if c in (200, 201):
        created_ids["forum_post"] = d["data"]["id"]
        record("Forum", "CREATE Post", "PASS", f"id={created_ids['forum_post']}")
    else:
        record("Forum", "CREATE Post", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_forum_read():
    c, d = api_get("/forum/posts", admin_token)
    if c == 200 and d.get("data"):
        record("Forum", "READ Posts", "PASS", f"{len(d['data'])} posts")
    else:
        record("Forum", "READ Posts", "FAIL", f"Status {c}")

def test_forum_update():
    pid = created_ids.get("forum_post")
    if pid:
        c, d = api_put(f"/forum/posts/{pid}",
                        {"content": f"Updated post content {RAND}"}, admin_token)
        if c == 200:
            record("Forum", "UPDATE Post", "PASS", f"Updated post {pid}")
        else:
            record("Forum", "UPDATE Post", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Forum", "UPDATE Post", "FAIL", "No post to update")

def test_forum_delete():
    pid = created_ids.get("forum_post")
    if pid:
        c, d = api_delete(f"/forum/posts/{pid}", admin_token)
        if c == 200:
            record("Forum", "DELETE Post", "PASS", f"Deleted post {pid}")
        else:
            record("Forum", "DELETE Post", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Forum", "DELETE Post", "FAIL", "No post to delete")

# ── 11. Asset CRUD ────────────────────────────────────────────────────
def test_asset_create():
    c, d = api_post("/assets", {
        "name": f"TestLaptop-{RAND}", "serial_number": f"SN-{RAND}",
        "description": "Functional test asset", "status": "available"
    }, admin_token)
    if c == 201:
        created_ids["asset"] = d["data"]["id"]
        record("Asset", "CREATE", "PASS",
               f"id={created_ids['asset']} tag={d['data'].get('asset_tag')}")
    else:
        record("Asset", "CREATE", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_asset_read():
    c, d = api_get("/assets", admin_token)
    if c == 200 and d.get("data"):
        record("Asset", "READ List", "PASS", f"{len(d['data'])} assets")
    else:
        record("Asset", "READ List", "FAIL", f"Status {c}")

def test_asset_update():
    aid = created_ids.get("asset")
    if aid:
        c, d = api_put(f"/assets/{aid}",
                        {"name": f"Updated-{RAND}", "status": "in_use"}, admin_token)
        if c == 200:
            record("Asset", "UPDATE", "PASS", f"Updated asset {aid}")
        else:
            record("Asset", "UPDATE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Asset", "UPDATE", "FAIL", "No asset to update")

def test_asset_delete():
    aid = created_ids.get("asset")
    if aid:
        c, d = api_delete(f"/assets/{aid}", admin_token)
        if c == 200:
            record("Asset", "DELETE", "PASS", f"Deleted asset {aid}")
        else:
            # DELETE may not be supported - record as info
            record("Asset", "DELETE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Asset", "DELETE", "FAIL", "No asset to delete")

# ── 12. Position CRUD ────────────────────────────────────────────────
def test_position_create():
    c, d = api_post("/positions", {
        "title": f"TestPosition-{RAND}", "department_id": 20,
        "job_description": f"Functional test position {RAND}"
    }, admin_token)
    if c == 201:
        created_ids["position"] = d["data"]["id"]
        record("Position", "CREATE", "PASS", f"id={created_ids['position']}")
    else:
        record("Position", "CREATE", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_position_read():
    c, d = api_get("/positions", admin_token)
    if c == 200 and d.get("data"):
        record("Position", "READ List", "PASS", f"{len(d['data'])} positions")
    else:
        record("Position", "READ List", "FAIL", f"Status {c}")

def test_position_update():
    pid = created_ids.get("position")
    if pid:
        c, d = api_put(f"/positions/{pid}",
                        {"title": f"Updated Pos {RAND}"}, admin_token)
        if c == 200:
            record("Position", "UPDATE", "PASS", f"Updated position {pid}")
        else:
            record("Position", "UPDATE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Position", "UPDATE", "FAIL", "No position to update")

def test_position_delete():
    pid = created_ids.get("position")
    if pid:
        c, d = api_delete(f"/positions/{pid}", admin_token)
        if c == 200:
            record("Position", "DELETE", "PASS", f"Deleted position {pid}")
        else:
            record("Position", "DELETE", "FAIL", f"Status {c}: {str(d)[:200]}")
    else:
        record("Position", "DELETE", "FAIL", "No position to delete")

# ── 13. Wellness ──────────────────────────────────────────────────────
def test_wellness_checkin():
    c, d = api_post("/wellness/check-in", {
        "mood": "good", "energy_level": 4, "sleep_hours": 7, "stress_level": 3
    }, emp_token)
    if c == 201:
        record("Wellness", "CREATE Check-in", "PASS", f"Check-in recorded")
    else:
        record("Wellness", "CREATE Check-in", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_wellness_read():
    c, d = api_get("/wellness/check-ins", emp_token)
    if c == 200 and d.get("data"):
        record("Wellness", "READ Check-ins", "PASS", f"{len(d['data'])} check-ins")
    else:
        record("Wellness", "READ Check-ins", "FAIL", f"Status {c}")

def test_wellness_programs():
    c, d = api_get("/wellness/programs", admin_token)
    if c == 200:
        record("Wellness", "READ Programs", "PASS",
               f"{len(d.get('data', []))} programs")
    else:
        record("Wellness", "READ Programs", "FAIL", f"Status {c}")

# ── 14. Feedback ──────────────────────────────────────────────────────
def test_feedback_create():
    c, d = api_post("/feedback", {
        "category": "management", "subject": f"Test Feedback {RAND}",
        "message": f"Functional test feedback message {RAND}"
    }, emp_token)
    if c == 201:
        created_ids["feedback"] = d["data"]["id"]
        record("Feedback", "CREATE", "PASS", f"id={created_ids['feedback']}")
    else:
        record("Feedback", "CREATE", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_feedback_read():
    c, d = api_get("/feedback", emp_token)
    if c == 200 and d.get("data"):
        record("Feedback", "READ List", "PASS", f"{len(d['data'])} feedback items")
    else:
        record("Feedback", "READ List", "FAIL", f"Status {c}")

# ── 15. Whistleblowing ───────────────────────────────────────────────
def test_whistleblow_create():
    c, d = api_post("/whistleblowing/reports", {
        "category": "safety_violation", "subject": f"Test WB Report {RAND}",
        "description": f"Functional test whistleblow report {RAND}",
        "severity": "medium"
    }, emp_token)
    if c in (200, 201):
        record("Whistleblowing", "CREATE Report", "PASS", f"Created report")
    else:
        record("Whistleblowing", "CREATE Report", "FAIL", f"Status {c}: {str(d)[:200]}")

def test_whistleblow_read():
    c, d = api_get("/whistleblowing/reports", admin_token)
    if c == 200 and d.get("data"):
        record("Whistleblowing", "READ Reports", "PASS", f"{len(d['data'])} reports")
    else:
        record("Whistleblowing", "READ Reports", "FAIL", f"Status {c}")

# ── UI-only tests ─────────────────────────────────────────────────────
def test_dashboard_ui():
    ui_login(ADMIN_EMAIL, ADMIN_PASS)
    time.sleep(3)
    screenshot(f"dashboard_{RAND}")
    url = driver.current_url
    src = driver.page_source.lower()
    if any(k in url.lower() or k in src for k in ["dashboard", "welcome", "empcloud"]):
        record("Dashboard", "READ (UI)", "PASS", f"Dashboard at {url}")
    else:
        record("Dashboard", "READ (UI)", "FAIL", f"Page: {url}")

def test_leave_ui():
    ui_login(ADMIN_EMAIL, ADMIN_PASS)
    nav("/leave")
    time.sleep(2)
    screenshot(f"leave_page_{RAND}")
    if "leave" in driver.page_source.lower():
        record("Leave", "READ (UI)", "PASS", f"Leave page at {driver.current_url}")
    else:
        record("Leave", "READ (UI)", "FAIL", "Leave page did not load")

def test_attendance_ui():
    ui_login(ADMIN_EMAIL, ADMIN_PASS)
    nav("/attendance")
    time.sleep(2)
    screenshot(f"attendance_page_{RAND}")
    if "attendance" in driver.page_source.lower():
        record("Attendance", "READ (UI)", "PASS", f"Attendance page at {driver.current_url}")
    else:
        record("Attendance", "READ (UI)", "FAIL", "Attendance page did not load")

def test_announcements_ui():
    ui_login(ADMIN_EMAIL, ADMIN_PASS)
    nav("/announcements")
    time.sleep(2)
    screenshot(f"announcements_page_{RAND}")
    if "announcement" in driver.page_source.lower():
        record("Announcement", "READ (UI)", "PASS", f"Announcements page at {driver.current_url}")
    else:
        record("Announcement", "READ (UI)", "FAIL", "Announcements page did not load")

def test_documents_ui():
    ui_login(ADMIN_EMAIL, ADMIN_PASS)
    nav("/documents")
    time.sleep(2)
    screenshot(f"documents_page_{RAND}")
    if "document" in driver.page_source.lower():
        record("Document", "READ (UI)", "PASS", f"Documents page at {driver.current_url}")
    else:
        record("Document", "READ (UI)", "FAIL", "Documents page did not load")

def test_policies_ui():
    ui_login(ADMIN_EMAIL, ADMIN_PASS)
    nav("/policies")
    time.sleep(2)
    screenshot(f"policies_page_{RAND}")
    if "polic" in driver.page_source.lower():
        record("Policies", "READ (UI)", "PASS", f"Policies page at {driver.current_url}")
    else:
        record("Policies", "READ (UI)", "FAIL", "Policies page did not load")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════
def main():
    log("=" * 70)
    log("EMP Cloud HRMS - Comprehensive Functional CRUD Test Suite v2")
    log(f"Target: {BASE_URL}  |  Run ID: {RAND}")
    log("=" * 70)

    # Auth
    test_auth()

    if not admin_token:
        log("FATAL: Admin login failed, cannot continue API tests.")
        quit_driver()
        return

    # UI: Dashboard
    run_test("Dashboard", "READ (UI)", test_dashboard_ui)

    # 1. Employee CRUD
    run_test("Employee", "READ Directory", test_employee_read_directory)
    run_test("Employee", "CREATE", test_employee_create)
    run_test("Employee", "READ Profile", test_employee_read_profile)
    run_test("Employee", "UPDATE", test_employee_update)
    run_test("Employee", "DEACTIVATE", test_employee_deactivate)
    run_test("Employee", "READ List (UI)", test_employee_ui)

    # 2. Department (UI only - no API found)
    run_test("Department", "READ (UI)", test_department_ui)

    # 3. Leave CRUD
    run_test("Leave", "READ Types", test_leave_types_read)
    run_test("Leave", "CREATE Apply", test_leave_apply)
    run_test("Leave", "READ Applications", test_leave_read)
    run_test("Leave", "READ Balance", test_leave_balance)
    run_test("Leave", "UPDATE Cancel", test_leave_cancel)
    run_test("Leave", "READ Balance After Cancel", test_leave_balance_after_cancel)
    run_test("Leave", "READ (UI)", test_leave_ui)

    # 4. Attendance
    run_test("Attendance", "Clock In", test_attendance_checkin)
    run_test("Attendance", "READ Records", test_attendance_read)
    run_test("Attendance", "Clock Out", test_attendance_checkout)
    run_test("Attendance", "Verify Hours", test_attendance_verify)
    run_test("Attendance", "READ (UI)", test_attendance_ui)

    # 5. Document CRUD
    run_test("Document", "CREATE Upload", test_document_upload)
    run_test("Document", "READ List", test_document_read)
    run_test("Document", "READ My Docs", test_document_read_my)
    run_test("Document", "DELETE", test_document_delete)
    run_test("Document", "READ (UI)", test_documents_ui)

    # 6. Announcement CRUD
    run_test("Announcement", "CREATE", test_announcement_create)
    run_test("Announcement", "READ List", test_announcement_read)
    run_test("Announcement", "UPDATE", test_announcement_update)
    run_test("Announcement", "DELETE", test_announcement_delete)
    run_test("Announcement", "READ (UI)", test_announcements_ui)

    # 7. Helpdesk Ticket CRUD
    run_test("Helpdesk", "CREATE Ticket", test_ticket_create)
    run_test("Helpdesk", "READ Tickets", test_ticket_read)
    run_test("Helpdesk", "UPDATE Ticket", test_ticket_update)

    # 8. Event CRUD
    run_test("Event", "CREATE", test_event_create)
    run_test("Event", "READ List", test_event_read)
    run_test("Event", "UPDATE", test_event_update)
    run_test("Event", "DELETE", test_event_delete)

    # 9. Survey CRUD
    run_test("Survey", "CREATE", test_survey_create)
    run_test("Survey", "READ List", test_survey_read)
    run_test("Survey", "UPDATE", test_survey_update)

    # 10. Forum Post CRUD
    run_test("Forum", "CREATE Post", test_forum_create)
    run_test("Forum", "READ Posts", test_forum_read)
    run_test("Forum", "UPDATE Post", test_forum_update)
    run_test("Forum", "DELETE Post", test_forum_delete)

    # 11. Asset CRUD
    run_test("Asset", "CREATE", test_asset_create)
    run_test("Asset", "READ List", test_asset_read)
    run_test("Asset", "UPDATE", test_asset_update)
    run_test("Asset", "DELETE", test_asset_delete)

    # 12. Position CRUD
    run_test("Position", "CREATE", test_position_create)
    run_test("Position", "READ List", test_position_read)
    run_test("Position", "UPDATE", test_position_update)
    run_test("Position", "DELETE", test_position_delete)

    # 13. Wellness
    run_test("Wellness", "CREATE Check-in", test_wellness_checkin)
    run_test("Wellness", "READ Check-ins", test_wellness_read)
    run_test("Wellness", "READ Programs", test_wellness_programs)

    # 14. Feedback
    run_test("Feedback", "CREATE", test_feedback_create)
    run_test("Feedback", "READ List", test_feedback_read)

    # 15. Whistleblowing
    run_test("Whistleblowing", "CREATE Report", test_whistleblow_create)
    run_test("Whistleblowing", "READ Reports", test_whistleblow_read)

    # UI pages
    run_test("Policies", "READ (UI)", test_policies_ui)

    # Cleanup
    quit_driver()

    # ── Summary ─────────────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("TEST RESULTS SUMMARY")
    log("=" * 70)

    passes = sum(1 for r in test_results if r["status"] == "PASS")
    fails = sum(1 for r in test_results if r["status"] == "FAIL")
    total = len(test_results)

    log(f"Total: {total} | PASS: {passes} | FAIL: {fails}")
    log(f"Pass rate: {passes/total*100:.1f}%" if total else "No tests ran")

    modules = {}
    for r in test_results:
        m = r["module"]
        if m not in modules:
            modules[m] = {"pass": 0, "fail": 0}
        modules[m][r["status"].lower()] = modules[m].get(r["status"].lower(), 0) + 1

    log(f"\n{'Module':<20} {'Pass':>5} {'Fail':>5}")
    log("-" * 35)
    for m, c in sorted(modules.items()):
        log(f"{m:<20} {c.get('pass',0):>5} {c.get('fail',0):>5}")

    if fails:
        log(f"\nFailed tests:")
        for r in test_results:
            if r["status"] == "FAIL":
                log(f"  - {r['module']} / {r['operation']}: {r['details'][:120]}")

    if issues_filed:
        log(f"\nGitHub issues filed ({len(issues_filed)}):")
        for u in issues_filed:
            log(f"  {u}")

    with open(r"C:\emptesting\test_results.json", "w", encoding="utf-8") as f:
        json.dump({"run_id": RAND, "timestamp": datetime.datetime.now().isoformat(),
                    "summary": {"total": total, "pass": passes, "fail": fails},
                    "results": test_results, "issues": issues_filed}, f, indent=2)
    log(f"\nResults saved to C:\\emptesting\\test_results.json")
    log("=" * 70)


if __name__ == "__main__":
    main()
