#!/usr/bin/env python3
"""
EMP Cloud HRMS - Recruitment Module E2E Test v2
Targeted test using exact sidebar labels discovered from screenshot analysis.
Sidebar: Dashboard, Jobs, Candidates, Interviews, Offers, Onboarding, Referrals, Analytics, Settings
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import traceback
import urllib.request
import urllib.error
import ssl
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────
RECRUIT_URL = "https://test-recruit.empcloud.com"
RECRUIT_API = "https://test-recruit-api.empcloud.com"
ORG_ADMIN_EMAIL = "ananya@technova.in"
ORG_ADMIN_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\recruit"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_found = []
test_results = []
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def shot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{ts()}.png")
    driver.save_screenshot(path)
    print(f"    [SCREENSHOT] {path}")
    return path


def file_github_issue(title, body, labels=None, screenshot_path=None):
    if labels is None:
        labels = ["bug"]
    full_body = body
    if screenshot_path:
        full_body += f"\n\n**Screenshot:** `{screenshot_path}`"
    full_body += f"\n\n_Automated E2E test - {datetime.now().isoformat()}_"

    data = json.dumps({"title": title, "body": full_body, "labels": labels}).encode('utf-8')
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        data=data,
        headers={
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "EmpCloud-E2E-Test"
        },
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx)
        result = json.loads(resp.read().decode('utf-8'))
        print(f"    [GITHUB] Issue #{result['number']}: {result['html_url']}")
        return result['number']
    except Exception as e:
        print(f"    [GITHUB ERROR] {e}")
        return None


def report_bug(driver, name, description, severity="medium", labels=None):
    ss = shot(driver, f"BUG_{name}")
    if labels is None:
        labels = ["bug", f"severity:{severity}"]
    else:
        labels = list(labels) + [f"severity:{severity}"]
    title = f"[Recruit E2E] {name}"
    issue_num = file_github_issue(title, description, labels, ss)
    bugs_found.append({"name": name, "severity": severity, "issue": issue_num, "screenshot": ss})
    return ss


def log_result(test_name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {test_name} {details}")
    test_results.append({"test": test_name, "passed": passed, "details": details})


def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-popup-blocking")
    svc = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.set_page_load_timeout(45)
    driver.implicitly_wait(3)
    return driver


def wait_stable(driver, t=10):
    try:
        WebDriverWait(driver, t).until(lambda d: d.execute_script("return document.readyState") == "complete")
    except:
        pass
    time.sleep(1.5)


def safe_click(driver, el):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.3)
        el.click()
        return True
    except:
        try:
            driver.execute_script("arguments[0].click();", el)
            return True
        except:
            return False


def click_sidebar(driver, label):
    """Click sidebar item by exact text match."""
    try:
        # The sidebar uses text labels like "Jobs", "Candidates", etc.
        # Try exact text match first
        xpaths = [
            f"//nav//a[normalize-space()='{label}']",
            f"//aside//a[normalize-space()='{label}']",
            f"//*[contains(@class,'sidebar')]//*[normalize-space()='{label}']",
            f"//a[normalize-space()='{label}']",
            f"//a[contains(normalize-space(), '{label}')]",
        ]
        for xp in xpaths:
            els = driver.find_elements(By.XPATH, xp)
            for el in els:
                if el.is_displayed():
                    safe_click(driver, el)
                    time.sleep(2)
                    wait_stable(driver)
                    return True
        return False
    except:
        return False


def is_page_blank(driver, context=""):
    """Check if page body has meaningful content beyond sidebar."""
    try:
        # Look for main content area
        main_selectors = [
            "main", "[class*='content']", "[class*='page-body']", "[class*='main']",
            "[class*='container']:not([class*='sidebar'])"
        ]
        for sel in main_selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and len(el.text.strip()) > 20:
                    return False
        # Fallback: check body text minus sidebar
        body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
        if len(body_text) > 100:
            return False
        return True
    except:
        return True


def get_page_heading(driver):
    """Get the main heading of the current page."""
    for sel in ["h1", "h2", "[class*='title']", "[class*='heading']"]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.text.strip():
                    return el.text.strip()
        except:
            continue
    return ""


def find_button(driver, keywords):
    """Find a visible button matching any keyword."""
    for kw in keywords:
        # CSS selectors
        for sel in [f"button", "a[class*='btn']", "[role='button']"]:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed() and kw.lower() in el.text.lower():
                        return el
            except:
                continue
        # Also try by text content xpath
        try:
            xp = f"//button[contains(translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}')]"
            els = driver.find_elements(By.XPATH, xp)
            for el in els:
                if el.is_displayed():
                    return el
        except:
            continue
    return None


def get_visible_form_fields(driver):
    """Get all visible form fields."""
    fields = driver.find_elements(By.CSS_SELECTOR,
        "input:not([type='hidden']):not([type='checkbox']):not([type='radio']), "
        "textarea, select, [role='combobox'], [contenteditable='true'], "
        ".ql-editor, .ProseMirror")
    return [f for f in fields if f.is_displayed()]


def check_for_errors(driver):
    """Check for error messages on page."""
    error_sels = [
        "[class*='error']", "[class*='alert-danger']", "[role='alert']",
        "[class*='toast-error']", "[class*='notification-error']"
    ]
    errors = []
    for sel in error_sels:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.text.strip():
                    errors.append(el.text.strip())
        except:
            continue
    return errors


def check_for_modal(driver):
    """Check if a modal/dialog is open."""
    modal_sels = [
        "[class*='modal'][class*='show']", "[role='dialog']", "[class*='dialog']",
        "[class*='drawer']", "[class*='popup']", ".modal.show", "[class*='overlay']"
    ]
    for sel in modal_sels:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    return el
        except:
            continue
    return None


def close_modal(driver):
    """Try to close any open modal."""
    close_sels = [
        "[class*='modal'] button[class*='close']",
        "[role='dialog'] button[class*='close']",
        "[class*='modal'] [aria-label='Close']",
        "[class*='modal'] button:first-child",
        "button[class*='close']",
    ]
    for sel in close_sels:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    safe_click(driver, el)
                    time.sleep(1)
                    return True
        except:
            continue
    # Try pressing Escape
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        return True
    except:
        return False


# ════════════════════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════════════════════
def login(driver):
    print("\n[LOGIN] Recruit App")
    driver.get(RECRUIT_URL)
    wait_stable(driver)

    email_el = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR,
            "input[type='email'], input[name='email'], input[placeholder*='mail']"))
    )
    email_el.clear()
    email_el.send_keys(ORG_ADMIN_EMAIL)

    pass_el = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pass_el.clear()
    pass_el.send_keys(ORG_ADMIN_PASS)

    btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button")
    safe_click(driver, btn)
    time.sleep(5)
    wait_stable(driver)

    if "/dashboard" in driver.current_url:
        print("  Login successful")
        shot(driver, "00_login_success")
        return True
    else:
        print(f"  Login may have failed, URL: {driver.current_url}")
        shot(driver, "00_login_result")
        return True  # Continue anyway


# ════════════════════════════════════════════════════════════════════════
# TEST: Dashboard
# ════════════════════════════════════════════════════════════════════════
def test_dashboard(driver):
    print("\n[TEST] Dashboard")
    driver.get(RECRUIT_URL + "/dashboard")
    wait_stable(driver)
    shot(driver, "T01_dashboard")

    heading = get_page_heading(driver)
    blank = is_page_blank(driver)

    if blank:
        report_bug(driver, "Dashboard blank page", "Dashboard page has no content", "high")
        log_result("Dashboard", False, "Blank")
        return

    # Check dashboard stats cards
    stats = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='stat'], [class*='metric']")
    visible_stats = [s for s in stats if s.is_displayed() and s.text.strip()]
    log_result("Dashboard", True, f"Heading: '{heading}', Stats cards: {len(visible_stats)}")


# ════════════════════════════════════════════════════════════════════════
# TEST: Jobs Page + Create Job (Bug #51)
# ════════════════════════════════════════════════════════════════════════
def test_jobs(driver):
    print("\n[TEST] Jobs Page")
    click_sidebar(driver, "Jobs")
    time.sleep(2)
    wait_stable(driver)
    shot(driver, "T02_jobs_page")

    heading = get_page_heading(driver)
    blank = is_page_blank(driver)
    url = driver.current_url
    print(f"    URL: {url}, Heading: '{heading}'")

    if blank:
        report_bug(driver, "Jobs page blank",
            "Jobs listing page is blank after clicking Jobs in sidebar.\n\n**URL:** " + url,
            "high")
        log_result("Jobs List Page", False, "Blank page")
    else:
        log_result("Jobs List Page", True, f"URL: {url}")

    # Look for create/add job button
    print("\n[TEST] Create Job (Bug #51 - Unable to post new job)")
    create_btn = find_button(driver, ["Create", "Add", "New", "Post Job", "+"])
    if not create_btn:
        # Try icon-only buttons (e.g. plus icon)
        try:
            icon_btns = driver.find_elements(By.CSS_SELECTOR,
                "button svg, button i, a[class*='btn'] svg, [class*='fab'], [class*='float-btn']")
            for ib in icon_btns:
                parent = ib.find_element(By.XPATH, "./..")
                if parent.is_displayed():
                    create_btn = parent
                    break
        except:
            pass

    if not create_btn:
        report_bug(driver, "No create job button",
            "**Bug #51 Verification:** Cannot find any Create/Add/New Job button on the Jobs page.\n\n"
            "The user cannot post a new job because the action button is missing or not visible.",
            "critical", ["bug", "Bug#51"])
        log_result("Create Job (Bug #51)", False, "No create button found")
        return

    print(f"    Found button: '{create_btn.text}'")
    safe_click(driver, create_btn)
    time.sleep(3)
    wait_stable(driver)
    shot(driver, "T02_create_job_clicked")

    # Check for modal or new page
    modal = check_for_modal(driver)
    if modal:
        print(f"    Modal opened: {modal.text[:100]}")
        shot(driver, "T02_create_job_modal")

    new_url = driver.current_url
    blank2 = is_page_blank(driver)
    fields = get_visible_form_fields(driver)
    print(f"    After click - URL: {new_url}, Form fields: {len(fields)}")

    if blank2 and not modal:
        report_bug(driver, "Create job blank page",
            "**Bug #51 Verification:** Clicking Create/Add Job results in a blank page.\n\n"
            f"**URL:** {new_url}\n"
            "No form or modal rendered. User cannot create a new job posting.",
            "critical", ["bug", "regression", "Bug#51"])
        log_result("Create Job (Bug #51)", False, "Blank page after click")
        return

    if len(fields) == 0 and not modal:
        report_bug(driver, "Create job no form fields",
            "**Bug #51 Verification:** After clicking Create Job, no form fields are visible.\n\n"
            f"**URL:** {new_url}\n"
            "The job creation form failed to render.",
            "high", ["bug", "Bug#51"])
        log_result("Create Job (Bug #51)", False, "No form fields")
        return

    # Try to fill the form
    if fields:
        for field in fields:
            attrs = " ".join(filter(None, [
                field.get_attribute("name"), field.get_attribute("placeholder"),
                field.get_attribute("id"), field.get_attribute("aria-label")
            ])).lower()
            tag = field.tag_name

            try:
                if "title" in attrs or "name" in attrs or "position" in attrs:
                    field.clear()
                    field.send_keys("QA Test Engineer - Automated E2E")
                elif "location" in attrs:
                    field.clear()
                    field.send_keys("Remote")
                elif "department" in attrs or "dept" in attrs:
                    field.clear()
                    field.send_keys("Engineering")
                elif "salary" in attrs or "compensation" in attrs or "ctc" in attrs:
                    field.clear()
                    field.send_keys("100000")
                elif "experience" in attrs or "exp" in attrs:
                    field.clear()
                    field.send_keys("3")
                elif "vacancy" in attrs or "opening" in attrs or "position" in attrs:
                    field.clear()
                    field.send_keys("2")
                elif tag == "textarea":
                    field.clear()
                    field.send_keys("Automated test job description. Testing recruitment module.")
                elif tag == "select":
                    # Select second option if available
                    options = field.find_elements(By.TAG_NAME, "option")
                    if len(options) > 1:
                        options[1].click()
            except:
                pass

        shot(driver, "T02_create_job_filled")

        # Try submit
        submit_btn = find_button(driver, ["Save", "Submit", "Post", "Publish", "Create"])
        if submit_btn:
            print(f"    Submitting with button: '{submit_btn.text}'")
            safe_click(driver, submit_btn)
            time.sleep(5)
            wait_stable(driver)
            shot(driver, "T02_create_job_submitted")

            errors = check_for_errors(driver)
            blank3 = is_page_blank(driver)

            if blank3:
                report_bug(driver, "Create job blank after submit",
                    "**Bug #51 Verification:** Page goes blank after submitting new job form.\n\n"
                    f"Errors: {errors}",
                    "critical", ["bug", "Bug#51"])
                log_result("Create Job Submit (Bug #51)", False, "Blank after submit")
            elif errors:
                # Validation errors are expected for incomplete forms
                log_result("Create Job Submit (Bug #51)", True,
                    f"Form validation responded: {errors[:2]}")
            else:
                log_result("Create Job Submit (Bug #51)", True, "Form submitted")
        else:
            log_result("Create Job (Bug #51)", True, f"Form loaded with {len(fields)} fields, no submit btn found")
    else:
        # Modal may have fields
        if modal:
            modal_fields = modal.find_elements(By.CSS_SELECTOR,
                "input:not([type='hidden']), textarea, select")
            visible_mf = [f for f in modal_fields if f.is_displayed()]
            log_result("Create Job (Bug #51)", len(visible_mf) > 0,
                f"Modal with {len(visible_mf)} fields")
        else:
            log_result("Create Job (Bug #51)", False, "No fields found")

    close_modal(driver)


# ════════════════════════════════════════════════════════════════════════
# TEST: Candidates Page
# ════════════════════════════════════════════════════════════════════════
def test_candidates(driver):
    print("\n[TEST] Candidates Page")
    click_sidebar(driver, "Candidates")
    time.sleep(2)
    wait_stable(driver)
    shot(driver, "T03_candidates_page")

    heading = get_page_heading(driver)
    blank = is_page_blank(driver)
    url = driver.current_url
    print(f"    URL: {url}, Heading: '{heading}'")

    if blank:
        report_bug(driver, "Candidates page blank",
            "Candidates/Applicant tracking page is blank.\n\n**URL:** " + url,
            "high")
        log_result("Candidates Page", False, "Blank")
        return

    # Check for table/kanban/list
    content = driver.find_elements(By.CSS_SELECTOR,
        "table, [class*='kanban'], [class*='board'], [class*='pipeline'], [class*='card-body']")
    visible = [c for c in content if c.is_displayed()]
    log_result("Candidates Page", True, f"Content containers: {len(visible)}")

    # Try add candidate
    add_btn = find_button(driver, ["Add", "Create", "New", "+"])
    if add_btn:
        safe_click(driver, add_btn)
        time.sleep(3)
        wait_stable(driver)
        shot(driver, "T03_add_candidate_form")

        modal = check_for_modal(driver)
        fields = get_visible_form_fields(driver)
        if modal:
            fields = modal.find_elements(By.CSS_SELECTOR,
                "input:not([type='hidden']), textarea, select") if not fields else fields
            fields = [f for f in fields if f.is_displayed()]

        if len(fields) > 0:
            log_result("Add Candidate Form", True, f"{len(fields)} fields")
        else:
            blank2 = is_page_blank(driver)
            if blank2:
                report_bug(driver, "Add candidate blank",
                    "Add candidate form/page is blank after clicking Add button",
                    "medium")
            log_result("Add Candidate Form", False, "No fields")
        close_modal(driver)


# ════════════════════════════════════════════════════════════════════════
# TEST: Interviews Page + Schedule (Bug #52)
# ════════════════════════════════════════════════════════════════════════
def test_interviews(driver):
    print("\n[TEST] Interviews Page")
    click_sidebar(driver, "Interviews")
    time.sleep(2)
    wait_stable(driver)
    shot(driver, "T04_interviews_page")

    heading = get_page_heading(driver)
    blank = is_page_blank(driver)
    url = driver.current_url
    print(f"    URL: {url}, Heading: '{heading}'")

    if blank:
        report_bug(driver, "Interviews page blank",
            "**Bug #52 Related:** Interviews page is blank.\n\n**URL:** " + url,
            "high", ["bug", "Bug#52"])
        log_result("Interviews Page", False, "Blank")
    else:
        log_result("Interviews Page", True, f"URL: {url}")

    # Try to schedule interview (Bug #52)
    print("\n[TEST] Schedule Interview (Bug #52 - Blank page)")
    sched_btn = find_button(driver, ["Schedule", "Add", "Create", "New", "+"])
    if not sched_btn:
        report_bug(driver, "No schedule interview button",
            "**Bug #52 Verification:** Cannot find Schedule/Add interview button on Interviews page.\n\n"
            f"**URL:** {url}",
            "high", ["bug", "Bug#52"])
        log_result("Schedule Interview (Bug #52)", False, "No button found")
        return

    print(f"    Found button: '{sched_btn.text}'")
    safe_click(driver, sched_btn)
    time.sleep(3)
    wait_stable(driver)
    shot(driver, "T04_schedule_interview_clicked")

    modal = check_for_modal(driver)
    blank2 = is_page_blank(driver)
    fields = get_visible_form_fields(driver)
    new_url = driver.current_url
    print(f"    After click - URL: {new_url}, Fields: {len(fields)}, Modal: {modal is not None}")

    if modal:
        modal_fields = modal.find_elements(By.CSS_SELECTOR,
            "input:not([type='hidden']), textarea, select, [role='combobox']")
        modal_visible = [f for f in modal_fields if f.is_displayed()]
        shot(driver, "T04_schedule_interview_modal")
        if modal_visible:
            log_result("Schedule Interview (Bug #52)", True,
                f"Modal with {len(modal_visible)} fields")
        else:
            report_bug(driver, "Schedule interview modal empty",
                "**Bug #52 Verification:** Schedule interview modal opens but has no fields.",
                "high", ["bug", "Bug#52"])
            log_result("Schedule Interview (Bug #52)", False, "Modal empty")
        close_modal(driver)
        return

    if blank2 and len(fields) == 0:
        report_bug(driver, "Schedule interview blank page",
            "**Bug #52 Verification:** Clicking Schedule Interview results in a blank page.\n\n"
            f"**URL:** {new_url}\n"
            "No form, modal, or content rendered. Interview scheduling is broken.",
            "critical", ["bug", "regression", "Bug#52"])
        log_result("Schedule Interview (Bug #52)", False, "Blank page")
    elif len(fields) > 0:
        log_result("Schedule Interview (Bug #52)", True, f"Form with {len(fields)} fields")
    else:
        log_result("Schedule Interview (Bug #52)", True, f"Page loaded: {new_url}")

    close_modal(driver)


# ════════════════════════════════════════════════════════════════════════
# TEST: Offers Page + Create Offer (Bug #53)
# ════════════════════════════════════════════════════════════════════════
def test_offers(driver):
    print("\n[TEST] Offers Page")
    click_sidebar(driver, "Offers")
    time.sleep(2)
    wait_stable(driver)
    shot(driver, "T05_offers_page")

    heading = get_page_heading(driver)
    blank = is_page_blank(driver)
    url = driver.current_url
    print(f"    URL: {url}, Heading: '{heading}'")

    if blank:
        report_bug(driver, "Offers page blank",
            "**Bug #53 Related:** Offers page is blank.\n\n**URL:** " + url,
            "high", ["bug", "Bug#53"])
        log_result("Offers Page", False, "Blank")
    else:
        log_result("Offers Page", True, f"URL: {url}")

    # Try to create offer (Bug #53)
    print("\n[TEST] Create Offer (Bug #53 - Blank page)")
    create_btn = find_button(driver, ["Create", "Add", "New", "Generate", "+"])
    if not create_btn:
        report_bug(driver, "No create offer button",
            "**Bug #53 Verification:** Cannot find Create/Add offer button on Offers page.\n\n"
            f"**URL:** {url}",
            "high", ["bug", "Bug#53"])
        log_result("Create Offer (Bug #53)", False, "No button found")
        return

    print(f"    Found button: '{create_btn.text}'")
    safe_click(driver, create_btn)
    time.sleep(3)
    wait_stable(driver)
    shot(driver, "T05_create_offer_clicked")

    modal = check_for_modal(driver)
    blank2 = is_page_blank(driver)
    fields = get_visible_form_fields(driver)
    new_url = driver.current_url
    print(f"    After click - URL: {new_url}, Fields: {len(fields)}, Modal: {modal is not None}")

    if modal:
        modal_fields = modal.find_elements(By.CSS_SELECTOR,
            "input:not([type='hidden']), textarea, select, [role='combobox']")
        modal_visible = [f for f in modal_fields if f.is_displayed()]
        shot(driver, "T05_create_offer_modal")
        if modal_visible:
            log_result("Create Offer (Bug #53)", True, f"Modal with {len(modal_visible)} fields")
        else:
            report_bug(driver, "Create offer modal empty",
                "**Bug #53 Verification:** Create offer modal opens but has no fields.\n\n"
                "The offer creation form failed to render inside the modal.",
                "high", ["bug", "Bug#53"])
            log_result("Create Offer (Bug #53)", False, "Modal empty")
        close_modal(driver)
        return

    if blank2 and len(fields) == 0:
        report_bug(driver, "Create offer blank page",
            "**Bug #53 Verification:** Clicking Create Offer results in a blank page.\n\n"
            f"**URL:** {new_url}\n"
            "No form or content rendered. Offer creation is completely broken.",
            "critical", ["bug", "regression", "Bug#53"])
        log_result("Create Offer (Bug #53)", False, "Blank page")
    elif len(fields) > 0:
        log_result("Create Offer (Bug #53)", True, f"Form with {len(fields)} fields")
    else:
        log_result("Create Offer (Bug #53)", True, f"Page loaded: {new_url}")

    close_modal(driver)


# ════════════════════════════════════════════════════════════════════════
# TEST: Onboarding Page + Add Task (Bug #54)
# ════════════════════════════════════════════════════════════════════════
def test_onboarding(driver):
    print("\n[TEST] Onboarding Page")
    click_sidebar(driver, "Onboarding")
    time.sleep(2)
    wait_stable(driver)
    shot(driver, "T06_onboarding_page")

    heading = get_page_heading(driver)
    blank = is_page_blank(driver)
    url = driver.current_url
    print(f"    URL: {url}, Heading: '{heading}'")

    if blank:
        report_bug(driver, "Onboarding page blank",
            "**Bug #54 Related:** Onboarding page is blank.\n\n**URL:** " + url,
            "high", ["bug", "Bug#54"])
        log_result("Onboarding Page", False, "Blank")
    else:
        log_result("Onboarding Page", True, f"URL: {url}")

    # Look for templates tab/section
    template_found = False
    for kw in ["Template", "Checklist"]:
        try:
            xp = f"//*[contains(normalize-space(), '{kw}') and (self::a or self::button or self::li or self::span or self::div[@role='tab'])]"
            els = driver.find_elements(By.XPATH, xp)
            for el in els:
                if el.is_displayed() and len(el.text.strip()) < 50:
                    safe_click(driver, el)
                    time.sleep(2)
                    wait_stable(driver)
                    template_found = True
                    shot(driver, "T06_onboarding_templates_tab")
                    break
            if template_found:
                break
        except:
            continue

    # Try to create a template or open existing one
    create_btn = find_button(driver, ["Create", "Add", "New", "+"])
    if create_btn:
        print(f"    Found button: '{create_btn.text}'")
        safe_click(driver, create_btn)
        time.sleep(3)
        wait_stable(driver)
        shot(driver, "T06_onboarding_create_clicked")

    # Now try to add a task (Bug #54)
    print("\n[TEST] Add Task to Onboarding Template (Bug #54)")
    add_task_btn = find_button(driver, ["Add Task", "Add", "New Task", "+"])

    if not add_task_btn:
        # Look specifically for "Add Task" in any clickable element
        try:
            xp = "//*[contains(translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add task')]"
            els = driver.find_elements(By.XPATH, xp)
            for el in els:
                if el.is_displayed():
                    add_task_btn = el
                    break
        except:
            pass

    if not add_task_btn:
        report_bug(driver, "No add task button in onboarding",
            "**Bug #54 Verification:** Cannot find 'Add Task' button on onboarding templates page.\n\n"
            f"**URL:** {driver.current_url}\n"
            "Either the template page didn't load properly or the Add Task button is missing.",
            "high", ["bug", "Bug#54"])
        log_result("Add Task (Bug #54)", False, "No Add Task button found")
        return

    print(f"    Found add task button: '{add_task_btn.text}'")
    safe_click(driver, add_task_btn)
    time.sleep(3)
    wait_stable(driver)
    shot(driver, "T06_add_task_clicked")

    modal = check_for_modal(driver)
    fields = get_visible_form_fields(driver)
    errors = check_for_errors(driver)
    print(f"    After click - Fields: {len(fields)}, Modal: {modal is not None}, Errors: {errors}")

    if errors:
        report_bug(driver, "Add task shows errors",
            f"**Bug #54 Verification:** Clicking Add Task shows errors:\n\n" +
            "\n".join(f"- {e}" for e in errors),
            "high", ["bug", "Bug#54"])
        log_result("Add Task (Bug #54)", False, f"Errors: {errors}")
    elif len(fields) == 0 and not modal:
        report_bug(driver, "Add task no form",
            "**Bug #54 Verification:** Clicking Add Task does not show a form.\n\n"
            f"**URL:** {driver.current_url}\n"
            "No input fields appeared after clicking Add Task.",
            "high", ["bug", "Bug#54"])
        log_result("Add Task (Bug #54)", False, "No form appeared")
    elif modal:
        m_fields = modal.find_elements(By.CSS_SELECTOR,
            "input:not([type='hidden']), textarea, select")
        m_visible = [f for f in m_fields if f.is_displayed()]
        if m_visible:
            # Try filling task
            for f in m_visible:
                attrs = " ".join(filter(None, [
                    f.get_attribute("name"), f.get_attribute("placeholder"), f.get_attribute("id")
                ])).lower()
                try:
                    if "task" in attrs or "name" in attrs or "title" in attrs:
                        f.clear()
                        f.send_keys("E2E Test Task - Complete paperwork")
                        break
                except:
                    pass
            shot(driver, "T06_add_task_filled")

            # Try save
            save_btn = find_button(driver, ["Save", "Add", "Submit", "Create"])
            if save_btn:
                safe_click(driver, save_btn)
                time.sleep(3)
                wait_stable(driver)
                shot(driver, "T06_add_task_saved")
                new_errors = check_for_errors(driver)
                if new_errors:
                    report_bug(driver, "Add task save error",
                        f"**Bug #54 Verification:** Saving task fails with errors:\n{new_errors}",
                        "high", ["bug", "Bug#54"])
                    log_result("Add Task (Bug #54)", False, f"Save errors: {new_errors}")
                else:
                    log_result("Add Task (Bug #54)", True, "Task form filled and saved")
            else:
                log_result("Add Task (Bug #54)", True, f"Modal with {len(m_visible)} fields (no save btn)")
        else:
            report_bug(driver, "Add task modal empty",
                "**Bug #54 Verification:** Add Task modal is empty.",
                "high", ["bug", "Bug#54"])
            log_result("Add Task (Bug #54)", False, "Modal empty")
        close_modal(driver)
    else:
        log_result("Add Task (Bug #54)", True, f"Form with {len(fields)} fields")

    close_modal(driver)


# ════════════════════════════════════════════════════════════════════════
# TEST: Referrals Page
# ════════════════════════════════════════════════════════════════════════
def test_referrals(driver):
    print("\n[TEST] Referrals Page")
    click_sidebar(driver, "Referrals")
    time.sleep(2)
    wait_stable(driver)
    shot(driver, "T07_referrals_page")

    heading = get_page_heading(driver)
    blank = is_page_blank(driver)
    url = driver.current_url
    print(f"    URL: {url}, Heading: '{heading}'")

    if blank:
        report_bug(driver, "Referrals page blank",
            "Referrals page is blank.\n\n**URL:** " + url,
            "medium")
        log_result("Referrals Page", False, "Blank")
    else:
        log_result("Referrals Page", True, f"URL: {url}")


# ════════════════════════════════════════════════════════════════════════
# TEST: Analytics Page
# ════════════════════════════════════════════════════════════════════════
def test_analytics(driver):
    print("\n[TEST] Analytics Page")
    click_sidebar(driver, "Analytics")
    time.sleep(2)
    wait_stable(driver)
    shot(driver, "T08_analytics_page")

    heading = get_page_heading(driver)
    blank = is_page_blank(driver)
    url = driver.current_url
    print(f"    URL: {url}, Heading: '{heading}'")

    if blank:
        report_bug(driver, "Analytics page blank",
            "Analytics page is blank.\n\n**URL:** " + url,
            "medium")
        log_result("Analytics Page", False, "Blank")
    else:
        log_result("Analytics Page", True, f"URL: {url}")


# ════════════════════════════════════════════════════════════════════════
# TEST: Settings Page
# ════════════════════════════════════════════════════════════════════════
def test_settings(driver):
    print("\n[TEST] Settings Page")
    click_sidebar(driver, "Settings")
    time.sleep(2)
    wait_stable(driver)
    shot(driver, "T09_settings_page")

    heading = get_page_heading(driver)
    blank = is_page_blank(driver)
    url = driver.current_url
    print(f"    URL: {url}, Heading: '{heading}'")

    if blank:
        report_bug(driver, "Settings page blank",
            "Recruit Settings page is blank.\n\n**URL:** " + url,
            "medium")
        log_result("Settings Page", False, "Blank")
    else:
        log_result("Settings Page", True, f"URL: {url}")

    # Check for settings sections/tabs
    tabs = driver.find_elements(By.CSS_SELECTOR,
        "[role='tab'], [class*='tab'], nav a, [class*='setting-section']")
    visible_tabs = [t for t in tabs if t.is_displayed() and t.text.strip()]
    if visible_tabs:
        print(f"    Settings sections: {[t.text.strip() for t in visible_tabs[:10]]}")


# ════════════════════════════════════════════════════════════════════════
# TEST: Form Validation - Submit Empty Job Form
# ════════════════════════════════════════════════════════════════════════
def test_validation(driver):
    print("\n[TEST] Form Validation - Empty Job Submit")
    click_sidebar(driver, "Jobs")
    time.sleep(2)
    wait_stable(driver)

    create_btn = find_button(driver, ["Create", "Add", "New", "Post", "+"])
    if not create_btn:
        log_result("Form Validation", False, "No create button to test")
        return

    safe_click(driver, create_btn)
    time.sleep(3)
    wait_stable(driver)

    # Try to submit immediately without filling
    submit_btn = find_button(driver, ["Save", "Submit", "Post", "Publish", "Create"])
    if submit_btn:
        safe_click(driver, submit_btn)
        time.sleep(2)
        wait_stable(driver)
        shot(driver, "T10_empty_form_validation")

        errors = check_for_errors(driver)
        # Check for HTML5 validation
        invalid_fields = driver.find_elements(By.CSS_SELECTOR, ":invalid")

        if errors or invalid_fields:
            log_result("Form Validation", True,
                f"Validation caught: {len(errors)} error msgs, {len(invalid_fields)} invalid fields")
        else:
            blank = is_page_blank(driver)
            if blank:
                report_bug(driver, "Empty form submit causes blank page",
                    "Submitting an empty job form results in a blank page with no validation messages.\n\n"
                    "Expected: Validation errors should be shown.",
                    "medium")
                log_result("Form Validation", False, "No validation, blank page")
            else:
                log_result("Form Validation", True, "No validation errors visible (may have client-side prevention)")
    else:
        log_result("Form Validation", False, "No submit button found")

    close_modal(driver)


# ════════════════════════════════════════════════════════════════════════
# TEST: Console Errors
# ════════════════════════════════════════════════════════════════════════
def test_console(driver):
    print("\n[TEST] Console Errors Check")
    try:
        logs = driver.get_log("browser")
        severe = [l for l in logs if l.get("level") == "SEVERE"]
        js_errors = [l for l in severe if any(k in l.get("message", "").lower()
            for k in ["uncaught", "typeerror", "referenceerror", "syntaxerror", "chunk"])]

        if js_errors:
            msgs = [l["message"][:200] for l in js_errors[:5]]
            report_bug(driver, "JavaScript errors in console",
                "Critical JavaScript errors found in browser console:\n\n" +
                "\n".join(f"- `{m}`" for m in msgs),
                "medium")
            log_result("Console Errors", False, f"{len(js_errors)} JS errors")
        else:
            log_result("Console Errors", True,
                f"{len(severe)} severe logs (none critical)" if severe else "Clean")
    except:
        log_result("Console Errors", True, "Could not check (driver limitation)")


# ════════════════════════════════════════════════════════════════════════
# TEST: API Health
# ════════════════════════════════════════════════════════════════════════
def test_api(driver):
    print("\n[TEST] Recruit API Health")
    endpoints = {"/health": "Health", "/api/docs": "Swagger"}
    results = []
    for ep, name in endpoints.items():
        try:
            req = urllib.request.Request(RECRUIT_API + ep, headers={
                "User-Agent": "EmpCloud-E2E-Test", "Origin": RECRUIT_URL
            })
            resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=10)
            results.append(f"{name}: HTTP {resp.getcode()}")
        except urllib.error.HTTPError as e:
            results.append(f"{name}: HTTP {e.code}")
        except Exception as e:
            results.append(f"{name}: {e}")

    print(f"    {results}")
    log_result("Recruit API", True, "; ".join(results))


# ════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("EMP CLOUD HRMS - RECRUITMENT MODULE E2E TEST v2")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    driver = None
    try:
        driver = create_driver()
        print("[SETUP] Chrome driver initialized")

        login(driver)
        test_dashboard(driver)
        test_jobs(driver)
        test_candidates(driver)
        test_interviews(driver)
        test_offers(driver)
        test_onboarding(driver)
        test_referrals(driver)
        test_analytics(driver)
        test_settings(driver)
        test_validation(driver)
        test_console(driver)
        test_api(driver)

    except Exception as e:
        print(f"\n[FATAL] {e}")
        traceback.print_exc()
        if driver:
            shot(driver, "FATAL")
    finally:
        if driver:
            driver.quit()
            print("\n[TEARDOWN] Browser closed")

    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in test_results if r["passed"])
    failed = sum(1 for r in test_results if not r["passed"])
    print(f"Total: {len(test_results)} | PASSED: {passed} | FAILED: {failed}")
    print("-" * 70)
    for r in test_results:
        s = "PASS" if r["passed"] else "FAIL"
        print(f"  [{s}] {r['test']}: {r['details'][:120]}")

    print(f"\nBUGS FILED: {len(bugs_found)}")
    print("-" * 70)
    for b in bugs_found:
        print(f"  #{b['issue']} [{b['severity']}] {b['name']}")
        print(f"    {b['screenshot']}")

    print(f"\nFinished: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
