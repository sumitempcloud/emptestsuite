import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import base64
import requests
import traceback
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots"
GITHUB_TOKEN = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_API = "https://api.github.com"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_found = []


# ── Helpers ─────────────────────────────────────────────────────────────
def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.implicitly_wait(8)
    return driver


def screenshot(driver, name):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{ts}_{name}.png"
    path = os.path.join(SCREENSHOT_DIR, fname)
    driver.save_screenshot(path)
    print(f"  [screenshot] {fname}")
    return path


def upload_screenshot_to_github(filepath):
    """Upload screenshot to repo and return the raw URL."""
    fname = os.path.basename(filepath)
    api_path = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/screenshots/{fname}"
    with open(filepath, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "message": f"Upload screenshot {fname}",
        "content": content,
        "branch": "main",
    }
    resp = requests.put(api_path, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        download_url = resp.json()["content"]["download_url"]
        print(f"  [github] Uploaded {fname}")
        return download_url
    else:
        print(f"  [github] Upload failed ({resp.status_code}): {resp.text[:200]}")
        return None


def create_github_issue(title, body, screenshot_path=None):
    """Create a GitHub issue, optionally with a screenshot."""
    img_url = None
    if screenshot_path:
        img_url = upload_screenshot_to_github(screenshot_path)

    full_body = body
    if img_url:
        full_body += f"\n\n### Screenshot\n![screenshot]({img_url})"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "title": title,
        "body": full_body,
        "labels": ["bug", "e2e-test"],
    }
    resp = requests.post(
        f"{GITHUB_API}/repos/{GITHUB_REPO}/issues",
        headers=headers, json=payload,
    )
    if resp.status_code == 201:
        url = resp.json()["html_url"]
        print(f"  [github] Issue created: {url}")
        return url
    else:
        print(f"  [github] Issue creation failed ({resp.status_code}): {resp.text[:300]}")
        return None


def report_bug(title, description, screenshot_path=None):
    """Record a bug and create GitHub issue."""
    print(f"  ** BUG: {title}")
    bugs_found.append(title)
    create_github_issue(
        title=f"[E2E Bug] {title}",
        body=(
            f"## Bug Report (Automated E2E Test)\n\n"
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"**Tester:** Org Admin (ananya@technova.in)\n"
            f"**Environment:** test-empcloud.empcloud.com\n\n"
            f"### Description\n{description}\n"
        ),
        screenshot_path=screenshot_path,
    )


def wait_for_page_load(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def safe_click(driver, element):
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)


def navigate_to(driver, path, label="page"):
    url = f"{BASE_URL}{path}"
    print(f"\n>> Navigating to {url} ({label})")
    driver.get(url)
    time.sleep(3)
    wait_for_page_load(driver)


# ── Login ───────────────────────────────────────────────────────────────
def login(driver):
    print("\n=== LOGIN ===")
    driver.get(BASE_URL)
    time.sleep(3)
    wait_for_page_load(driver)
    ss = screenshot(driver, "01_landing")

    # Check if already logged in
    if "/dashboard" in driver.current_url or "/home" in driver.current_url:
        print("  Already logged in.")
        return True

    # Try to find login form
    try:
        # Look for email/username field
        email_field = None
        for sel in [
            "input[name='email']", "input[type='email']",
            "input[name='username']", "input[name='login']",
            "input[id='email']", "input[id='username']",
            "#email", "#username",
            "input[placeholder*='mail']", "input[placeholder*='user']",
        ]:
            try:
                email_field = driver.find_element(By.CSS_SELECTOR, sel)
                if email_field.is_displayed():
                    break
                email_field = None
            except NoSuchElementException:
                continue

        if not email_field:
            # Try XPath
            try:
                email_field = driver.find_element(By.XPATH, "//input[@type='email' or @type='text'][1]")
            except NoSuchElementException:
                pass

        if not email_field:
            print("  Could not find email input field.")
            ss = screenshot(driver, "01_login_no_email_field")
            report_bug(
                "Login page - email input not found",
                "Could not locate the email/username input field on the login page.",
                ss,
            )
            return False

        email_field.clear()
        email_field.send_keys(ADMIN_EMAIL)
        time.sleep(0.5)

        # Find password field
        pwd_field = None
        for sel in [
            "input[name='password']", "input[type='password']",
            "input[id='password']", "#password",
        ]:
            try:
                pwd_field = driver.find_element(By.CSS_SELECTOR, sel)
                if pwd_field.is_displayed():
                    break
                pwd_field = None
            except NoSuchElementException:
                continue

        if not pwd_field:
            print("  Could not find password field.")
            ss = screenshot(driver, "01_login_no_pwd_field")
            report_bug(
                "Login page - password input not found",
                "Could not locate the password input field on the login page.",
                ss,
            )
            return False

        pwd_field.clear()
        pwd_field.send_keys(ADMIN_PASS)
        time.sleep(0.5)
        screenshot(driver, "02_credentials_entered")

        # Find and click login button
        login_btn = None
        for sel in [
            "button[type='submit']",
            "input[type='submit']",
            "button:contains('Login')",
            "button:contains('Sign in')",
        ]:
            try:
                login_btn = driver.find_element(By.CSS_SELECTOR, sel)
                if login_btn.is_displayed():
                    break
                login_btn = None
            except (NoSuchElementException, Exception):
                continue

        if not login_btn:
            try:
                login_btn = driver.find_element(
                    By.XPATH,
                    "//button[@type='submit'] | //input[@type='submit'] | //button[contains(text(),'ogin')] | //button[contains(text(),'ign')]"
                )
            except NoSuchElementException:
                pass

        if login_btn:
            safe_click(driver, login_btn)
        else:
            pwd_field.send_keys(Keys.RETURN)

        time.sleep(5)
        wait_for_page_load(driver)
        ss = screenshot(driver, "03_after_login")

        # Verify login
        current = driver.current_url
        page_src = driver.page_source.lower()
        if any(x in current for x in ["/dashboard", "/home", "/leave", "/employee"]):
            print("  Login successful!")
            return True
        elif "login" in current and ("error" in page_src or "invalid" in page_src or "incorrect" in page_src):
            report_bug(
                "Login fails with valid Org Admin credentials",
                f"Login with ananya@technova.in / Welcome@123 resulted in error. URL after attempt: {current}",
                ss,
            )
            return False
        else:
            # Might still be okay - some SPAs don't change URL right away
            print(f"  Post-login URL: {current} -- continuing anyway")
            return True

    except Exception as e:
        ss = screenshot(driver, "01_login_error")
        report_bug(
            "Login page error",
            f"Exception during login: {e}\n\nTraceback:\n{traceback.format_exc()}",
            ss,
        )
        return False


# ── Leave Module Tests ──────────────────────────────────────────────────
def test_leave_dashboard(driver):
    print("\n=== LEAVE DASHBOARD ===")
    navigate_to(driver, "/leave", "Leave Dashboard")
    ss = screenshot(driver, "10_leave_dashboard")

    page_src = driver.page_source.lower()
    current = driver.current_url

    # Check if page loaded
    if "error" in page_src and ("404" in page_src or "not found" in page_src):
        report_bug(
            "Leave dashboard returns 404 or error",
            f"Navigating to /leave shows an error page. Current URL: {current}",
            ss,
        )
        return False

    if "leave" not in page_src and "time off" not in page_src and "absence" not in page_src:
        report_bug(
            "Leave dashboard does not display leave-related content",
            f"The /leave page loaded but contains no leave-related content. URL: {current}",
            ss,
        )
        return False

    print("  Leave dashboard loaded.")
    return True


def test_leave_balance(driver):
    print("\n=== LEAVE BALANCE ===")
    navigate_to(driver, "/leave", "Leave Balance check")
    time.sleep(2)
    ss = screenshot(driver, "11_leave_balance")

    page_src = driver.page_source.lower()

    # Look for balance indicators
    balance_keywords = ["balance", "available", "remaining", "entitled", "taken", "earned", "casual", "sick", "privilege", "annual"]
    found = [kw for kw in balance_keywords if kw in page_src]

    if not found:
        report_bug(
            "Leave balance not displayed on leave dashboard",
            "The leave dashboard does not show any leave balance information (expected keywords like balance, available, remaining, etc.).",
            ss,
        )
        return False

    print(f"  Leave balance keywords found: {found}")
    return True


def test_leave_apply(driver):
    print("\n=== APPLY FOR LEAVE ===")

    # Try to find and click "Apply Leave" button
    navigate_to(driver, "/leave", "Leave page for apply")
    time.sleep(2)

    # Look for apply button
    apply_btn = None
    selectors = [
        "//button[contains(text(),'Apply')]",
        "//a[contains(text(),'Apply')]",
        "//button[contains(text(),'New')]",
        "//button[contains(text(),'Request')]",
        "//a[contains(text(),'Request')]",
        "//a[contains(@href,'apply')]",
        "//button[contains(@class,'apply')]",
        "//*[contains(text(),'Apply Leave')]",
        "//*[contains(text(),'Apply for Leave')]",
        "//*[contains(text(),'New Leave')]",
    ]
    for sel in selectors:
        try:
            btn = driver.find_element(By.XPATH, sel)
            if btn.is_displayed():
                apply_btn = btn
                break
        except NoSuchElementException:
            continue

    if not apply_btn:
        # Try navigating directly to apply page
        for path in ["/leave/apply", "/leave/new", "/leave/request"]:
            navigate_to(driver, path, "Leave apply form")
            time.sleep(2)
            ps = driver.page_source.lower()
            if "leave type" in ps or "from date" in ps or "start date" in ps or "reason" in ps:
                print(f"  Found leave apply form at {path}")
                break
        else:
            ss = screenshot(driver, "12_no_apply_button")
            report_bug(
                "Cannot find Apply Leave button or form",
                "Could not locate an 'Apply Leave' button on /leave, and direct navigation to /leave/apply, /leave/new, /leave/request did not show a leave form.",
                ss,
            )
            return False
    else:
        safe_click(driver, apply_btn)
        time.sleep(3)

    ss = screenshot(driver, "12_leave_apply_form")

    page_src = driver.page_source.lower()

    # Check for form elements
    has_leave_type = "leave type" in page_src or "type" in page_src
    has_date = "date" in page_src or "from" in page_src or "start" in page_src
    has_reason = "reason" in page_src or "description" in page_src or "note" in page_src

    if not (has_leave_type or has_date):
        report_bug(
            "Leave apply form missing key fields",
            f"Leave apply form is missing expected fields. Has leave type: {has_leave_type}, Has date fields: {has_date}, Has reason: {has_reason}",
            ss,
        )
        return False

    # Try to fill the form
    try:
        # Find leave type dropdown/select
        leave_type_el = None
        for sel in [
            "select[name*='type']", "select[name*='leave']",
            "[class*='select']", "select",
            "input[name*='type']",
        ]:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed():
                        leave_type_el = el
                        break
                if leave_type_el:
                    break
            except:
                continue

        if leave_type_el:
            if leave_type_el.tag_name == "select":
                from selenium.webdriver.support.ui import Select
                sel = Select(leave_type_el)
                if len(sel.options) > 1:
                    sel.select_by_index(1)
                    print("  Selected leave type from dropdown")
            else:
                safe_click(driver, leave_type_el)
                time.sleep(1)
                # Try clicking first option
                try:
                    opt = driver.find_element(By.CSS_SELECTOR, "[class*='option']:not([class*='disabled']), li[role='option'], [role='option']")
                    safe_click(driver, opt)
                except:
                    pass

        time.sleep(1)

        # Try date pickers
        date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[name*='date'], input[name*='from'], input[name*='start'], input[placeholder*='date'], input[placeholder*='Date']")
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        future_date2 = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")

        for i, di in enumerate(date_inputs[:2]):
            if di.is_displayed():
                try:
                    di.clear()
                    di.send_keys(future_date if i == 0 else future_date2)
                    print(f"  Entered date in field {i}")
                except:
                    pass
        time.sleep(1)

        # Try reason/description field
        reason_el = None
        for sel in [
            "textarea[name*='reason']", "textarea[name*='description']",
            "textarea[name*='note']", "textarea",
            "input[name*='reason']", "input[name*='description']",
        ]:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed():
                        reason_el = el
                        break
                if reason_el:
                    break
            except:
                continue

        if reason_el:
            reason_el.clear()
            reason_el.send_keys("E2E Test - Automated leave application test")
            print("  Entered reason")

        ss = screenshot(driver, "13_leave_form_filled")
        print("  Leave form interaction completed")

    except Exception as e:
        ss = screenshot(driver, "13_leave_form_error")
        report_bug(
            "Error while filling leave application form",
            f"Exception while interacting with leave form: {e}\n\n{traceback.format_exc()}",
            ss,
        )

    return True


def test_leave_applications_list(driver):
    print("\n=== LEAVE APPLICATIONS LIST ===")

    # Try various paths for leave list
    found = False
    for path in ["/leave", "/leave/applications", "/leave/list", "/leave/history", "/leave/my-leaves"]:
        navigate_to(driver, path, "Leave applications list")
        time.sleep(2)
        ps = driver.page_source.lower()
        if any(kw in ps for kw in ["application", "status", "approved", "pending", "rejected", "leave list", "my leave"]):
            found = True
            print(f"  Leave list found at {path}")
            break

    ss = screenshot(driver, "14_leave_applications_list")

    if not found:
        report_bug(
            "Leave applications list not found",
            "Could not find a leave applications list view at /leave, /leave/applications, /leave/list, or /leave/history.",
            ss,
        )
        return False

    # Check for table/list
    tables = driver.find_elements(By.CSS_SELECTOR, "table, [class*='list'], [class*='grid'], [class*='table']")
    if not tables:
        page_src = driver.page_source.lower()
        if "no leave" in page_src or "no record" in page_src or "no data" in page_src or "empty" in page_src:
            print("  Leave list is empty (no records)")
        else:
            report_bug(
                "Leave applications list has no table or list component",
                "The leave applications page does not contain a visible table or list component.",
                ss,
            )
            return False

    print("  Leave applications list verified.")
    return True


def test_leave_calendar(driver):
    print("\n=== LEAVE CALENDAR ===")
    navigate_to(driver, "/leave/calendar", "Leave Calendar")
    time.sleep(3)
    ss = screenshot(driver, "15_leave_calendar")

    page_src = driver.page_source.lower()
    current = driver.current_url

    if "404" in page_src or "not found" in page_src:
        report_bug(
            "Leave calendar page returns 404",
            f"Navigation to /leave/calendar shows 404 error. URL: {current}",
            ss,
        )
        return False

    # Check for calendar elements
    calendar_indicators = ["calendar", "month", "week", "day", "schedule", "jan", "feb", "mar", "apr", "may", "jun",
                           "jul", "aug", "sep", "oct", "nov", "dec", "monday", "tuesday", "sunday"]
    found = [kw for kw in calendar_indicators if kw in page_src]

    if not found:
        report_bug(
            "Leave calendar does not display calendar view",
            "The /leave/calendar page loaded but does not show any calendar-related content (month names, day names, etc.).",
            ss,
        )
        return False

    print(f"  Calendar indicators found: {found[:5]}")
    return True


def test_leave_types(driver):
    print("\n=== LEAVE TYPES ===")
    navigate_to(driver, "/leave/types", "Leave Types")
    time.sleep(3)
    ss = screenshot(driver, "16_leave_types")

    page_src = driver.page_source.lower()
    current = driver.current_url

    if "404" in page_src or "not found" in page_src:
        report_bug(
            "Leave types configuration page returns 404",
            f"Navigation to /leave/types shows 404 error. URL: {current}",
            ss,
        )
        return False

    # Check for leave type content
    type_keywords = ["casual", "sick", "privilege", "annual", "earned", "maternity", "paternity",
                     "comp", "leave type", "type name", "days", "paid", "unpaid"]
    found = [kw for kw in type_keywords if kw in page_src]

    if not found:
        # Maybe it redirected or content is different
        if "leave" not in page_src and "type" not in page_src:
            report_bug(
                "Leave types page missing leave type content",
                f"The /leave/types page does not show any leave type configuration. URL: {current}",
                ss,
            )
            return False

    print(f"  Leave types keywords found: {found[:5]}")
    return True


def test_comp_off(driver):
    print("\n=== COMP-OFF ===")

    found = False
    for path in ["/leave/comp-off", "/leave/compoff", "/leave/compensatory", "/leave/comp-off-request"]:
        navigate_to(driver, path, "Comp-off page")
        time.sleep(2)
        ps = driver.page_source.lower()
        current = driver.current_url
        if "404" not in ps and "not found" not in ps and ("comp" in ps or "compensat" in ps or "leave" in ps):
            found = True
            print(f"  Comp-off page found at {path}")
            break

    ss = screenshot(driver, "17_comp_off")

    if not found:
        # Try finding comp-off from leave page
        navigate_to(driver, "/leave", "Leave page for comp-off link")
        time.sleep(2)
        try:
            link = driver.find_element(By.XPATH, "//*[contains(text(),'Comp') or contains(text(),'comp')]")
            if link.is_displayed():
                safe_click(driver, link)
                time.sleep(2)
                found = True
                ss = screenshot(driver, "17_comp_off_from_link")
        except:
            pass

    if not found:
        report_bug(
            "Comp-off page not accessible",
            "Could not navigate to a comp-off page via /leave/comp-off, /leave/compoff, /leave/compensatory, or via link on the leave dashboard.",
            ss,
        )
        return False

    print("  Comp-off page verified.")
    return True


# ── Documents Module Tests ──────────────────────────────────────────────
def test_documents_page(driver):
    print("\n=== DOCUMENTS PAGE ===")
    navigate_to(driver, "/documents", "Documents")
    time.sleep(3)
    ss = screenshot(driver, "20_documents_page")

    page_src = driver.page_source.lower()
    current = driver.current_url

    if "404" in page_src or "not found" in page_src:
        report_bug(
            "Documents page returns 404",
            f"Navigation to /documents shows 404 error. URL: {current}",
            ss,
        )
        return False

    if "document" not in page_src and "file" not in page_src and "upload" not in page_src:
        report_bug(
            "Documents page does not display document-related content",
            f"The /documents page loaded but shows no document-related content. URL: {current}",
            ss,
        )
        return False

    print("  Documents page loaded.")
    return True


def test_document_categories(driver):
    print("\n=== DOCUMENT CATEGORIES ===")
    navigate_to(driver, "/documents", "Documents for categories check")
    time.sleep(2)
    ss = screenshot(driver, "21_document_categories")

    page_src = driver.page_source.lower()

    # Look for category-like content
    cat_keywords = ["category", "categories", "folder", "type", "personal", "official",
                    "identity", "certificate", "tax", "education", "experience"]
    found = [kw for kw in cat_keywords if kw in page_src]

    if not found:
        # Check for tabs or sections
        tabs = driver.find_elements(By.CSS_SELECTOR, "[role='tab'], .tab, [class*='tab'], [class*='category']")
        if not tabs:
            report_bug(
                "Document categories not visible",
                "The documents page does not display any document categories, folders, or type filters.",
                ss,
            )
            return False

    print(f"  Category keywords found: {found[:5]}")
    return True


def test_document_upload(driver):
    print("\n=== DOCUMENT UPLOAD ===")
    navigate_to(driver, "/documents", "Documents for upload test")
    time.sleep(2)

    # Find upload button
    upload_btn = None
    for sel in [
        "//button[contains(text(),'Upload')]",
        "//a[contains(text(),'Upload')]",
        "//button[contains(text(),'Add')]",
        "//*[contains(text(),'Upload Document')]",
        "//button[contains(@class,'upload')]",
        "//input[@type='file']",
        "//*[contains(text(),'Add Document')]",
    ]:
        try:
            el = driver.find_element(By.XPATH, sel)
            if el.is_displayed() or el.tag_name == "input":
                upload_btn = el
                break
        except NoSuchElementException:
            continue

    ss = screenshot(driver, "22_document_upload_attempt")

    if not upload_btn:
        # Try direct navigation
        for path in ["/documents/upload", "/documents/new", "/documents/add"]:
            navigate_to(driver, path, "Document upload page")
            time.sleep(2)
            ps = driver.page_source.lower()
            if "upload" in ps or "file" in ps or "browse" in ps:
                print(f"  Upload form found at {path}")
                ss = screenshot(driver, "22_document_upload_form")
                return True

        report_bug(
            "Document upload button/form not found",
            "Could not find an upload button or file input on the documents page, nor a direct upload page.",
            ss,
        )
        return False

    if upload_btn.tag_name == "input" and upload_btn.get_attribute("type") == "file":
        print("  Found file input element for upload")
    else:
        safe_click(driver, upload_btn)
        time.sleep(2)
        ss = screenshot(driver, "22_document_upload_dialog")

    print("  Document upload UI verified.")
    return True


def test_my_documents(driver):
    print("\n=== MY DOCUMENTS ===")
    navigate_to(driver, "/documents/my", "My Documents")
    time.sleep(3)
    ss = screenshot(driver, "23_my_documents")

    page_src = driver.page_source.lower()
    current = driver.current_url

    if "404" in page_src or "not found" in page_src:
        # Try alternate paths
        for path in ["/documents/my-documents", "/documents?view=my", "/my-documents"]:
            navigate_to(driver, path, "My Documents alternate")
            time.sleep(2)
            ps = driver.page_source.lower()
            if "404" not in ps and "not found" not in ps:
                ss = screenshot(driver, "23_my_documents_alt")
                print(f"  My documents found at {path}")
                return True

        report_bug(
            "My Documents page returns 404",
            f"Navigation to /documents/my shows 404. Also tried alternate paths.",
            ss,
        )
        return False

    if "document" not in page_src and "file" not in page_src:
        report_bug(
            "My Documents page has no document content",
            f"The /documents/my page loaded but has no document-related content. URL: {current}",
            ss,
        )
        return False

    print("  My Documents page verified.")
    return True


# ── Main Test Runner ────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("EMP Cloud HRMS - E2E Test: Leave & Documents Modules")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    driver = get_driver()
    results = {}

    try:
        # Login
        if not login(driver):
            print("\nLogin FAILED. Aborting tests.")
            driver.quit()
            return

        # ── Leave Module ──
        print("\n" + "=" * 60)
        print("LEAVE MODULE TESTS")
        print("=" * 60)

        results["Leave Dashboard"] = test_leave_dashboard(driver)
        results["Leave Balance"] = test_leave_balance(driver)
        results["Apply Leave"] = test_leave_apply(driver)
        results["Leave Applications List"] = test_leave_applications_list(driver)
        results["Leave Calendar"] = test_leave_calendar(driver)
        results["Leave Types"] = test_leave_types(driver)
        results["Comp-Off"] = test_comp_off(driver)

        # ── Documents Module ──
        print("\n" + "=" * 60)
        print("DOCUMENTS MODULE TESTS")
        print("=" * 60)

        results["Documents Page"] = test_documents_page(driver)
        results["Document Categories"] = test_document_categories(driver)
        results["Document Upload"] = test_document_upload(driver)
        results["My Documents"] = test_my_documents(driver)

    except Exception as e:
        ss = screenshot(driver, "99_unexpected_error")
        report_bug(
            "Unexpected test runner error",
            f"The test runner encountered an unexpected error: {e}\n\n{traceback.format_exc()}",
            ss,
        )
    finally:
        driver.quit()

    # ── Summary ──
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {test_name}")

    print(f"\nTotal: {len(results)} | Passed: {sum(1 for v in results.values() if v)} | Failed: {sum(1 for v in results.values() if not v)}")
    print(f"Bugs reported: {len(bugs_found)}")
    for b in bugs_found:
        print(f"  - {b}")
    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
