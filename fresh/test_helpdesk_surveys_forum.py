"""
Fresh E2E Tests: Helpdesk, Surveys, Forum
Tests API + Selenium for EMP Cloud HRMS
Discovered correct endpoints:
- Helpdesk: POST /helpdesk/tickets {subject, description, priority, category:"general"}
- Helpdesk: PUT /helpdesk/tickets/:id {status, resolution}
- Surveys: POST /surveys {title, description, type, questions:[{question_text, question_type, is_required, sort_order}]}
- Surveys: POST /surveys/:id/publish
- Surveys: POST /surveys/:id/respond {answers:[{question_id, answer}]}
- Forum: POST /forum/posts {title, content, category_id}
- Forum: POST /forum/posts/:id/reply {content}
"""

import requests
import json
import time
import os
import traceback
import uuid
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# =============================================================================
# CONFIG
# =============================================================================
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
FRONTEND_URL = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_helpdesk_surveys"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

RESULTS = []
BUGS = []
UNIQUE = uuid.uuid4().hex[:6]


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def record(test_name, status, detail=""):
    RESULTS.append({"test": test_name, "status": status, "detail": detail})
    icon = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "SKIP")
    log(f"  [{icon}] {test_name} -- {detail[:140]}")


def bug(title, detail):
    BUGS.append({"title": title, "detail": detail})
    log(f"  [BUG] {title}")


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    try:
        driver.save_screenshot(path)
    except Exception:
        pass
    return path


# =============================================================================
# API HELPERS
# =============================================================================
def api_login(email, password):
    r = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code == 200:
        data = r.json()
        token = None
        d = data.get("data", {})
        if isinstance(d, dict):
            tokens = d.get("tokens", {})
            if isinstance(tokens, dict):
                token = tokens.get("access_token")
            if not token:
                token = d.get("access_token") or d.get("token")
        if not token:
            token = data.get("access_token") or data.get("token")
        return token, data
    return None, r.text


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def api_get(token, path, params=None):
    return requests.get(f"{API_BASE}{path}", headers=auth_headers(token), params=params, timeout=30)


def api_post(token, path, data=None):
    return requests.post(f"{API_BASE}{path}", headers=auth_headers(token), json=data, timeout=30)


def api_put(token, path, data=None):
    return requests.put(f"{API_BASE}{path}", headers=auth_headers(token), json=data, timeout=30)


def api_delete(token, path):
    return requests.delete(f"{API_BASE}{path}", headers=auth_headers(token), timeout=30)


# =============================================================================
# SELENIUM HELPERS
# =============================================================================
def create_driver():
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    return driver


def selenium_login(driver, email, password):
    driver.get(f"{FRONTEND_URL}/login")
    time.sleep(2)
    try:
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail']"))
        )
        email_input.clear()
        email_input.send_keys(email)
        pass_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        pass_input.clear()
        pass_input.send_keys(password)
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        btn.click()
        time.sleep(3)
        return True
    except Exception as e:
        log(f"  Selenium login failed: {e}")
        return False


def wait_for_dashboard(driver, timeout=10):
    """Wait until we're past the login page."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: "/login" not in d.current_url
        )
        return True
    except TimeoutException:
        return False


# =============================================================================
# HELPDESK API TESTS
# =============================================================================
def test_helpdesk_api(admin_token, emp_token):
    log("\n========== HELPDESK API TESTS ==========")

    # 1. List tickets as admin
    r = api_get(admin_token, "/helpdesk/tickets")
    if r.status_code == 200:
        data = r.json().get("data", {})
        ticket_list = data.get("tickets", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        record("Helpdesk -- Admin list tickets", "PASS", f"HTTP 200, {len(ticket_list)} tickets")
    else:
        record("Helpdesk -- Admin list tickets", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # 2. Create ticket as employee (correct payload: subject, description, priority, category)
    ticket_data = {
        "subject": f"Laptop keyboard sticking - {UNIQUE}",
        "description": "Several keys on my laptop keyboard are sticking. Need replacement or repair. Affecting productivity.",
        "priority": "high",
        "category": "general"
    }
    r = api_post(emp_token, "/helpdesk/tickets", ticket_data)
    created_ticket_id = None
    if r.status_code in [200, 201]:
        d = r.json().get("data", {})
        created_ticket_id = d.get("id")
        record("Helpdesk -- Employee create ticket", "PASS",
               f"HTTP {r.status_code}, id={created_ticket_id}, SLA resp={d.get('sla_response_hours')}h, resol={d.get('sla_resolution_hours')}h")
    else:
        record("Helpdesk -- Employee create ticket", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # 3. View ticket detail
    if created_ticket_id:
        r = api_get(emp_token, f"/helpdesk/tickets/{created_ticket_id}")
        if r.status_code == 200:
            d = r.json().get("data", {})
            has_sla = bool(d.get("sla_response_hours") or d.get("sla_response_due"))
            record("Helpdesk -- View ticket detail", "PASS", f"status={d.get('status')}, SLA present={has_sla}")

            # Check SLA tracking
            if has_sla:
                record("Helpdesk -- SLA tracking fields present", "PASS",
                       f"resp_hours={d.get('sla_response_hours')}, resol_hours={d.get('sla_resolution_hours')}, resp_due={d.get('sla_response_due')}")
            else:
                record("Helpdesk -- SLA tracking fields present", "SKIP", "No SLA fields in ticket data")
        else:
            record("Helpdesk -- View ticket detail", "FAIL", f"HTTP {r.status_code}")

    # 4. Admin updates ticket status to in_progress
    if created_ticket_id:
        r = api_put(admin_token, f"/helpdesk/tickets/{created_ticket_id}", {"status": "in_progress"})
        if r.status_code == 200:
            record("Helpdesk -- Admin update status to in_progress", "PASS", "Status updated")
        else:
            record("Helpdesk -- Admin update status to in_progress", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # 5. BUSINESS RULE: Try to close ticket WITHOUT resolution
    if created_ticket_id:
        r = api_put(admin_token, f"/helpdesk/tickets/{created_ticket_id}", {"status": "closed"})
        if r.status_code in [400, 422]:
            record("Helpdesk -- Can't close without resolution", "PASS", f"Correctly blocked: HTTP {r.status_code}")
        elif r.status_code == 200:
            record("Helpdesk -- Can't close without resolution", "FAIL",
                   "BUG: Ticket closed without resolution note -- should require resolution before closing")
            bug("Helpdesk ticket can be closed without providing a resolution",
                f"PUT /helpdesk/tickets/{created_ticket_id} with status=closed (no resolution) returned 200. "
                "Business rule requires a resolution note before a ticket can be closed.")
            # Reset status back
            api_put(admin_token, f"/helpdesk/tickets/{created_ticket_id}", {"status": "in_progress"})
        else:
            record("Helpdesk -- Can't close without resolution", "FAIL", f"Unexpected HTTP {r.status_code}")

    # 6. Resolve ticket WITH resolution
    if created_ticket_id:
        r = api_put(admin_token, f"/helpdesk/tickets/{created_ticket_id}",
                    {"status": "resolved", "resolution": "Keyboard replaced with new one. Issue resolved."})
        if r.status_code == 200:
            d = r.json().get("data", {})
            record("Helpdesk -- Resolve ticket with resolution", "PASS",
                   f"status={d.get('status')}, resolved_at={d.get('resolved_at')}")
        else:
            record("Helpdesk -- Resolve ticket with resolution", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # 7. Knowledge Base
    r = api_get(admin_token, "/helpdesk/knowledge-base")
    if r.status_code == 200:
        record("Helpdesk -- Knowledge base listing", "PASS", f"HTTP 200")
    else:
        record("Helpdesk -- Knowledge base listing", "SKIP", f"HTTP {r.status_code}")

    # 8. Employee list their tickets
    r = api_get(emp_token, "/helpdesk/tickets")
    if r.status_code == 200:
        record("Helpdesk -- Employee list own tickets", "PASS", "HTTP 200")
    else:
        record("Helpdesk -- Employee list own tickets", "FAIL", f"HTTP {r.status_code}")

    return created_ticket_id


# =============================================================================
# SURVEYS API TESTS
# =============================================================================
def test_surveys_api(admin_token, emp_token):
    log("\n========== SURVEYS API TESTS ==========")

    # 1. List surveys
    r = api_get(admin_token, "/surveys")
    if r.status_code == 200:
        record("Surveys -- Admin list surveys", "PASS", "HTTP 200")
    else:
        record("Surveys -- Admin list surveys", "FAIL", f"HTTP {r.status_code}")

    # 2. Create survey WITH questions (correct format)
    survey_data = {
        "title": f"Employee Satisfaction Q1 {UNIQUE}",
        "description": "Quarterly employee satisfaction survey for all departments",
        "type": "engagement",
        "questions": [
            {"question_text": "How satisfied are you with your work environment?",
             "question_type": "rating_1_5", "is_required": True, "sort_order": 0},
            {"question_text": "What improvements would you suggest for the workplace?",
             "question_type": "text", "is_required": False, "sort_order": 1},
            {"question_text": "Rate your team collaboration on a scale of 1-5",
             "question_type": "rating_1_5", "is_required": True, "sort_order": 2}
        ]
    }
    r = api_post(admin_token, "/surveys", survey_data)
    created_survey_id = None
    question_ids = []
    if r.status_code in [200, 201]:
        d = r.json().get("data", {})
        created_survey_id = d.get("id")
        qs = d.get("questions", [])
        question_ids = [q["id"] for q in qs]
        record("Surveys -- Create survey with questions", "PASS",
               f"id={created_survey_id}, questions={len(qs)}")
    else:
        record("Surveys -- Create survey with questions", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # 3. Date validation: end_date before start_date
    bad_survey = {
        "title": f"Bad Date Survey {UNIQUE}",
        "description": "Should fail validation",
        "type": "engagement",
        "start_date": "2026-12-31",
        "end_date": "2026-01-01",  # end before start
    }
    r = api_post(admin_token, "/surveys", bad_survey)
    if r.status_code in [400, 422]:
        record("Surveys -- Date validation (end < start)", "PASS", f"Correctly rejected: HTTP {r.status_code}")
    elif r.status_code in [200, 201]:
        record("Surveys -- Date validation (end < start)", "FAIL",
               "BUG: Survey created with end_date before start_date -- should be rejected")
        bug("Survey accepts end date before start date",
            f"POST /surveys with start_date=2026-12-31 and end_date=2026-01-01 returned {r.status_code}. "
            "The system should reject surveys where end date is before start date.")
    else:
        record("Surveys -- Date validation (end < start)", "FAIL", f"Unexpected HTTP {r.status_code}")

    # 4. Publish survey
    if created_survey_id:
        r = api_post(admin_token, f"/surveys/{created_survey_id}/publish", {})
        if r.status_code == 200:
            d = r.json().get("data", {})
            record("Surveys -- Publish survey", "PASS", f"status={d.get('status')}")
        else:
            record("Surveys -- Publish survey", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # 5. Employee responds to survey
    responded = False
    if created_survey_id and question_ids:
        response_data = {
            "answers": [
                {"question_id": question_ids[0], "answer": "4"},
                {"question_id": question_ids[1], "answer": "Better cafeteria options and more team events"},
                {"question_id": question_ids[2], "answer": "5"},
            ]
        }
        r = api_post(emp_token, f"/surveys/{created_survey_id}/respond", response_data)
        if r.status_code in [200, 201]:
            record("Surveys -- Employee respond to survey", "PASS", f"HTTP {r.status_code}")
            responded = True
        else:
            record("Surveys -- Employee respond to survey", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # 6. BUSINESS RULE: Double submission should be blocked
    if responded and created_survey_id:
        r = api_post(emp_token, f"/surveys/{created_survey_id}/respond", response_data)
        if r.status_code in [400, 403, 409, 422]:
            record("Surveys -- Double submission blocked", "PASS", f"Correctly rejected: HTTP {r.status_code}")
        elif r.status_code in [200, 201]:
            record("Surveys -- Double submission blocked", "FAIL",
                   "BUG: Employee could submit survey response twice -- should be blocked")
            bug("Employee can submit survey response twice",
                f"POST /surveys/{created_survey_id}/respond returned 201 on second submission. "
                "Business rule: survey should only allow one response per employee.")
        else:
            record("Surveys -- Double submission blocked", "FAIL", f"Unexpected HTTP {r.status_code}")

    # 7. View survey results (admin)
    if created_survey_id:
        r = api_get(admin_token, f"/surveys/{created_survey_id}/results")
        if r.status_code == 200:
            d = r.json().get("data", {})
            record("Surveys -- View results", "PASS",
                   f"response_count={d.get('response_count')}")
        else:
            record("Surveys -- View results", "FAIL", f"HTTP {r.status_code}")

    # 8. Anonymous survey -- verify respondent identity hidden
    anon_survey = {
        "title": f"Anonymous Feedback {UNIQUE}",
        "description": "Anonymous survey -- respondents should not be identifiable",
        "type": "engagement",
        "is_anonymous": True,
        "questions": [
            {"question_text": "Rate management effectiveness honestly", "question_type": "rating_1_5",
             "is_required": True, "sort_order": 0}
        ]
    }
    r = api_post(admin_token, "/surveys", anon_survey)
    anon_id = None
    anon_q_ids = []
    if r.status_code in [200, 201]:
        d = r.json().get("data", {})
        anon_id = d.get("id")
        anon_q_ids = [q["id"] for q in d.get("questions", [])]
        record("Surveys -- Create anonymous survey", "PASS", f"id={anon_id}, is_anonymous={d.get('is_anonymous')}")
    else:
        record("Surveys -- Create anonymous survey", "FAIL", f"HTTP {r.status_code}")

    if anon_id and anon_q_ids:
        # Publish
        api_post(admin_token, f"/surveys/{anon_id}/publish", {})

        # Employee respond
        r = api_post(emp_token, f"/surveys/{anon_id}/respond",
                     {"answers": [{"question_id": anon_q_ids[0], "answer": "2"}]})
        if r.status_code in [200, 201]:
            # Check results for identity leakage
            r2 = api_get(admin_token, f"/surveys/{anon_id}/results")
            if r2.status_code == 200:
                result_text = r2.text.lower()
                if "priya" in result_text or EMP_EMAIL.lower() in result_text:
                    record("Surveys -- Anonymous hides respondent", "FAIL",
                           "BUG: Anonymous survey exposes respondent identity in results")
                    bug("Anonymous survey reveals respondent identity",
                        f"GET /surveys/{anon_id}/results contains employee name/email for an anonymous survey. "
                        "Anonymous survey responses should not reveal who responded.")
                else:
                    record("Surveys -- Anonymous hides respondent", "PASS",
                           "Respondent identity not visible in anonymous results")
            else:
                record("Surveys -- Anonymous hides respondent", "SKIP", f"Could not fetch results: HTTP {r2.status_code}")
        else:
            record("Surveys -- Anonymous response", "SKIP", f"Could not respond: HTTP {r.status_code}")

    return created_survey_id


# =============================================================================
# FORUM API TESTS
# =============================================================================
def test_forum_api(admin_token, emp_token):
    log("\n========== FORUM API TESTS ==========")

    # 1. List categories
    r = api_get(admin_token, "/forum/categories")
    categories = []
    if r.status_code == 200:
        data = r.json().get("data", {})
        categories = data.get("categories", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        record("Forum -- List categories", "PASS", f"{len(categories)} categories")
    else:
        record("Forum -- List categories", "FAIL", f"HTTP {r.status_code}")

    # 2. List posts
    r = api_get(emp_token, "/forum/posts")
    if r.status_code == 200:
        record("Forum -- List posts", "PASS", "HTTP 200")
    else:
        record("Forum -- List posts", "FAIL", f"HTTP {r.status_code}")

    # 3. Employee create post
    category_id = categories[0].get("id") if categories else None
    post_data = {
        "title": f"Best coffee spots near office {UNIQUE}",
        "content": "Looking for recommendations for good coffee places within walking distance of the office. Any suggestions?",
        "category_id": category_id,
    }
    r = api_post(emp_token, "/forum/posts", post_data)
    emp_post_id = None
    if r.status_code in [200, 201]:
        d = r.json().get("data", {})
        emp_post_id = d.get("id")
        record("Forum -- Employee create post", "PASS", f"id={emp_post_id}")
    else:
        record("Forum -- Employee create post", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # 4. Reply to post (correct endpoint: POST /forum/posts/:id/reply)
    if emp_post_id:
        r = api_post(admin_token, f"/forum/posts/{emp_post_id}/reply",
                     {"content": "I recommend the Blue Tokai cafe, about 5 mins walk from the office!"})
        if r.status_code in [200, 201]:
            d = r.json().get("data", {})
            record("Forum -- Reply to post", "PASS", f"reply_id={d.get('id')}")
        else:
            record("Forum -- Reply to post", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # 5. View post detail (should include replies)
    if emp_post_id:
        r = api_get(emp_token, f"/forum/posts/{emp_post_id}")
        if r.status_code == 200:
            d = r.json().get("data", {})
            replies = d.get("replies", [])
            record("Forum -- View post with replies", "PASS",
                   f"reply_count={d.get('reply_count')}, replies_loaded={len(replies)}")
        else:
            record("Forum -- View post with replies", "FAIL", f"HTTP {r.status_code}")

    # 6. Employee edit own post
    if emp_post_id:
        r = api_put(emp_token, f"/forum/posts/{emp_post_id}",
                    {"title": f"Best coffee AND tea spots near office {UNIQUE}",
                     "content": "Updated: Looking for coffee AND tea places near office. Suggestions welcome!"})
        if r.status_code == 200:
            record("Forum -- Employee edit own post", "PASS", "Updated successfully")
        else:
            record("Forum -- Employee edit own post", "FAIL", f"HTTP {r.status_code}")

    # 7. Admin creates a post
    admin_post_data = {
        "title": f"Office maintenance notice {UNIQUE}",
        "content": "Important: Office closed this Friday for maintenance. Please plan accordingly.",
        "category_id": category_id,
    }
    r = api_post(admin_token, "/forum/posts", admin_post_data)
    admin_post_id = None
    if r.status_code in [200, 201]:
        d = r.json().get("data", {})
        admin_post_id = d.get("id")
        record("Forum -- Admin create post", "PASS", f"id={admin_post_id}")
    else:
        record("Forum -- Admin create post", "FAIL", f"HTTP {r.status_code}")

    # 8. BUSINESS RULE: Employee can NOT delete admin's post
    if admin_post_id:
        r = api_delete(emp_token, f"/forum/posts/{admin_post_id}")
        if r.status_code in [403, 401]:
            record("Forum -- Employee can't delete other's post", "PASS",
                   f"Correctly denied: HTTP {r.status_code}")
        elif r.status_code == 200:
            record("Forum -- Employee can't delete other's post", "FAIL",
                   "BUG: Employee deleted admin's forum post -- should be forbidden")
            bug("Employee can delete another user's forum post",
                f"DELETE /forum/posts/{admin_post_id} as employee returned 200. "
                "Employees should only be able to delete their own posts.")
        else:
            record("Forum -- Employee can't delete other's post", "FAIL",
                   f"Unexpected HTTP {r.status_code}: {r.text[:200]}")

    # 9. Employee can delete OWN post
    if emp_post_id:
        r = api_delete(emp_token, f"/forum/posts/{emp_post_id}")
        if r.status_code == 200:
            record("Forum -- Employee delete own post", "PASS", "Deleted successfully")
        else:
            record("Forum -- Employee delete own post", "FAIL", f"HTTP {r.status_code}")

    # 10. Empty post rejected
    r = api_post(emp_token, "/forum/posts", {"title": "", "content": ""})
    if r.status_code in [400, 422]:
        record("Forum -- Empty post rejected", "PASS", f"Correctly rejected: HTTP {r.status_code}")
    elif r.status_code in [200, 201]:
        record("Forum -- Empty post rejected", "FAIL",
               "BUG: Forum post with empty title/content was accepted")
        bug("Forum allows creating post with empty title and content",
            "POST /forum/posts with empty title and content returned 201. "
            "Posts should require at least a title and content.")
    else:
        record("Forum -- Empty post rejected", "FAIL", f"HTTP {r.status_code}")

    # 11. Employee cannot edit admin's post
    if admin_post_id:
        r = api_put(emp_token, f"/forum/posts/{admin_post_id}",
                    {"title": "Hacked!", "content": "This post has been modified"})
        if r.status_code in [403, 401]:
            record("Forum -- Employee can't edit other's post", "PASS",
                   f"Correctly denied: HTTP {r.status_code}")
        elif r.status_code == 200:
            record("Forum -- Employee can't edit other's post", "FAIL",
                   "BUG: Employee edited admin's forum post")
            bug("Employee can edit another user's forum post",
                f"PUT /forum/posts/{admin_post_id} as employee returned 200. "
                "Employees should only be able to edit their own posts.")
        else:
            record("Forum -- Employee can't edit other's post", "FAIL", f"HTTP {r.status_code}")

    return admin_post_id


# =============================================================================
# SELENIUM TESTS
# =============================================================================
def test_selenium_all():
    log("\n========== SELENIUM TESTS ==========")
    driver = None
    try:
        driver = create_driver()

        # --- ADMIN LOGIN ---
        selenium_login(driver, ADMIN_EMAIL, ADMIN_PASS)
        if not wait_for_dashboard(driver):
            screenshot(driver, "00_login_stuck")
            record("Selenium -- Admin login", "FAIL", "Stuck on login page")
            return
        screenshot(driver, "01_admin_dashboard")
        record("Selenium -- Admin login", "PASS", f"URL: {driver.current_url}")
        time.sleep(2)

        # Use helper to navigate safely (ChromeDriver can crash on Windows)
        def safe_get(drv, url, wait=3):
            try:
                drv.get(url)
                time.sleep(wait)
                return True
            except Exception as e:
                log(f"  Navigation error for {url}: {str(e)[:80]}")
                return False

        # --- SURVEYS PAGE (admin) ---
        if safe_get(driver, f"{FRONTEND_URL}/surveys"):
            screenshot(driver, "02_admin_surveys")
            if "survey" in driver.page_source.lower():
                record("Selenium -- Admin surveys page", "PASS", "Surveys page loaded")
            else:
                record("Selenium -- Admin surveys page", "FAIL", "No survey content found")
        else:
            record("Selenium -- Admin surveys page", "SKIP", "Navigation failed")

        # --- FORUM PAGE (admin) ---
        if safe_get(driver, f"{FRONTEND_URL}/community"):
            screenshot(driver, "03_admin_forum")
            page_src = driver.page_source.lower()
            if "forum" in page_src or "community" in page_src:
                record("Selenium -- Admin forum page", "PASS", "Forum page loaded")
            else:
                record("Selenium -- Admin forum page", "FAIL", "No forum content found")
        else:
            record("Selenium -- Admin forum page", "SKIP", "Navigation failed")

        # --- HELPDESK PAGE (admin) ---
        helpdesk_found = False
        for path in ["/helpdesk", "/support", "/helpdesk/tickets", "/tickets"]:
            if safe_get(driver, f"{FRONTEND_URL}{path}"):
                page_text = driver.page_source.lower()
                if any(w in page_text for w in ["helpdesk", "ticket", "support request"]):
                    screenshot(driver, "05_admin_helpdesk")
                    record("Selenium -- Admin helpdesk page", "PASS", f"Found at {path}")
                    helpdesk_found = True
                    break

        if not helpdesk_found:
            screenshot(driver, "05_admin_helpdesk_fail")
            record("Selenium -- Admin helpdesk page", "FAIL",
                   "Helpdesk page not found at /helpdesk, /support, /tickets")

        try:
            driver.quit()
        except Exception:
            pass
        driver = None

        # --- EMPLOYEE SESSION ---
        driver = create_driver()
        selenium_login(driver, EMP_EMAIL, EMP_PASS)
        if not wait_for_dashboard(driver):
            screenshot(driver, "06_emp_login_stuck")
            record("Selenium -- Employee login", "FAIL", "Stuck on login page")
            return
        screenshot(driver, "06_emp_dashboard")
        record("Selenium -- Employee login", "PASS", f"URL: {driver.current_url}")
        time.sleep(2)

        # --- EMPLOYEE SURVEYS ---
        if safe_get(driver, f"{FRONTEND_URL}/surveys"):
            screenshot(driver, "07_emp_surveys")
            if "survey" in driver.page_source.lower():
                record("Selenium -- Employee surveys page", "PASS", "Surveys visible to employee")
            else:
                record("Selenium -- Employee surveys page", "FAIL", "Employee can't see surveys page")
        else:
            record("Selenium -- Employee surveys page", "SKIP", "Navigation failed")

        # --- EMPLOYEE FORUM ---
        forum_found = False
        for forum_path in ["/community", "/forum"]:
            if safe_get(driver, f"{FRONTEND_URL}{forum_path}"):
                page_text = driver.page_source.lower()
                if "forum" in page_text or "community" in page_text or "post" in page_text:
                    screenshot(driver, "08_emp_forum")
                    record("Selenium -- Employee forum page", "PASS", f"Found at {forum_path}")
                    forum_found = True
                    break
        if not forum_found:
            screenshot(driver, "08_emp_forum_fail")
            record("Selenium -- Employee forum page", "FAIL", "Employee can't see forum")

        # --- EMPLOYEE HELPDESK ---
        hd_found = False
        for path in ["/helpdesk", "/support", "/helpdesk/tickets"]:
            if safe_get(driver, f"{FRONTEND_URL}{path}"):
                if "helpdesk" in driver.page_source.lower() or "ticket" in driver.page_source.lower():
                    screenshot(driver, "09_emp_helpdesk")
                    record("Selenium -- Employee helpdesk page", "PASS", f"Found at {path}")
                    hd_found = True
                    break
        if not hd_found:
            screenshot(driver, "09_emp_helpdesk_fail")
            record("Selenium -- Employee helpdesk page", "FAIL", "Helpdesk not found for employee")

    except Exception as e:
        record("Selenium tests", "FAIL", f"Exception: {e}")
        traceback.print_exc()
        if driver:
            screenshot(driver, "99_selenium_error")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# =============================================================================
# MAIN
# =============================================================================
def main():
    log("=" * 70)
    log("FRESH E2E TEST: Helpdesk, Surveys, Forum")
    log(f"Run ID: {UNIQUE} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    # --- API LOGIN ---
    log("\nLogging in via API...")
    admin_token, _ = api_login(ADMIN_EMAIL, ADMIN_PASS)
    emp_token, _ = api_login(EMP_EMAIL, EMP_PASS)

    if not admin_token:
        record("API Login -- Admin", "FAIL", "Could not get token")
        return
    if not emp_token:
        record("API Login -- Employee", "FAIL", "Could not get token")
        return

    record("API Login -- Admin (ananya)", "PASS", "Token obtained")
    record("API Login -- Employee (priya)", "PASS", "Token obtained")

    # --- API TESTS ---
    try:
        test_helpdesk_api(admin_token, emp_token)
    except Exception as e:
        record("Helpdesk API tests", "FAIL", f"Exception: {e}")
        traceback.print_exc()

    try:
        test_surveys_api(admin_token, emp_token)
    except Exception as e:
        record("Surveys API tests", "FAIL", f"Exception: {e}")
        traceback.print_exc()

    try:
        test_forum_api(admin_token, emp_token)
    except Exception as e:
        record("Forum API tests", "FAIL", f"Exception: {e}")
        traceback.print_exc()

    # --- SELENIUM TESTS ---
    try:
        test_selenium_all()
    except Exception as e:
        record("Selenium tests", "FAIL", f"Exception: {e}")
        traceback.print_exc()

    # --- SUMMARY ---
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)
    passes = sum(1 for r in RESULTS if r["status"] == "PASS")
    fails = sum(1 for r in RESULTS if r["status"] == "FAIL")
    skips = sum(1 for r in RESULTS if r["status"] == "SKIP")

    log(f"Total: {len(RESULTS)} | PASS: {passes} | FAIL: {fails} | SKIP: {skips}")

    if BUGS:
        log(f"\nBUGS FOUND: {len(BUGS)}")
        for b in BUGS:
            log(f"  [BUG] {b['title']}")
            log(f"        {b['detail'][:200]}")

    if fails > 0:
        log("\nFAILURES:")
        for r in RESULTS:
            if r["status"] == "FAIL":
                log(f"  FAIL: {r['test']} -- {r['detail'][:150]}")

    if skips > 0:
        log("\nSKIPPED:")
        for r in RESULTS:
            if r["status"] == "SKIP":
                log(f"  SKIP: {r['test']} -- {r['detail'][:150]}")

    log("\nPASSED:")
    for r in RESULTS:
        if r["status"] == "PASS":
            log(f"  PASS: {r['test']}")

    log(f"\nScreenshots: {SCREENSHOT_DIR}")
    log("=" * 70)


if __name__ == "__main__":
    main()
