import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import traceback
import requests
from datetime import datetime
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

BASE_URL = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots"
GITHUB_TOKEN = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

BUGS_FOUND = []


def get_driver():
    chrome_options = Options()
    chrome_options.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(5)
    return driver


def screenshot(driver, name):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{ts}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    driver.save_screenshot(filepath)
    print(f"  [Screenshot] {filepath}")
    return filepath


def report_bug(title, description, screenshot_path=None, labels=None):
    """Record a bug and create a GitHub issue with screenshot."""
    bug = {"title": title, "description": description, "screenshot": screenshot_path}
    BUGS_FOUND.append(bug)
    print(f"\n  *** BUG FOUND: {title} ***\n")

    # Upload screenshot if available
    image_url = None
    if screenshot_path and os.path.exists(screenshot_path):
        image_url = upload_screenshot_to_github(screenshot_path)

    # Create GitHub issue
    body = f"## Bug Report\n\n**Description:**\n{description}\n\n"
    body += f"**URL:** {BASE_URL}\n"
    body += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    body += f"**Found by:** Automated E2E Test\n\n"
    if image_url:
        body += f"## Screenshot\n![Screenshot]({image_url})\n\n"
    elif screenshot_path:
        body += f"## Screenshot\nScreenshot saved locally at: `{screenshot_path}`\n\n"
    body += "## Steps to Reproduce\nSee description above.\n"

    issue_labels = labels or ["bug", "e2e-test"]
    create_github_issue(title, body, issue_labels)


def upload_screenshot_to_github(filepath):
    """Upload screenshot to GitHub repo and return the raw URL."""
    import base64
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
        filename = os.path.basename(filepath)
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/{filename}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "message": f"Upload screenshot {filename}",
            "content": content,
            "branch": "main"
        }
        resp = requests.put(api_url, headers=headers, json=data, timeout=30)
        if resp.status_code in (200, 201):
            download_url = resp.json().get("content", {}).get("download_url", "")
            print(f"  [Upload] Screenshot uploaded: {download_url}")
            return download_url
        else:
            print(f"  [Upload] Failed to upload screenshot: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"  [Upload] Error uploading screenshot: {e}")
        return None


def create_github_issue(title, body, labels):
    """Create a GitHub issue."""
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "title": title,
            "body": body,
            "labels": labels
        }
        resp = requests.post(api_url, headers=headers, json=data, timeout=30)
        if resp.status_code == 201:
            issue_url = resp.json().get("html_url", "")
            print(f"  [GitHub Issue] Created: {issue_url}")
        else:
            print(f"  [GitHub Issue] Failed to create: {resp.status_code} {resp.text[:300]}")
    except Exception as e:
        print(f"  [GitHub Issue] Error: {e}")


def login(driver, email, password, role="user"):
    """Login to EMP Cloud."""
    print(f"\n{'='*60}")
    print(f"LOGGING IN AS: {email} ({role})")
    print(f"{'='*60}")

    driver.get(BASE_URL)
    time.sleep(3)
    screenshot(driver, f"login_page_{role}")

    # Check current URL to understand login flow
    current = driver.current_url
    print(f"  Current URL after loading: {current}")

    # Try to find login form
    try:
        # Look for email/username input
        email_input = None
        for selector in [
            "input[type='email']", "input[name='email']", "input[name='username']",
            "input[placeholder*='mail']", "input[placeholder*='Email']",
            "input[placeholder*='user']", "input[type='text']",
            "#email", "#username", "#login-email"
        ]:
            try:
                email_input = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if email_input:
                    print(f"  Found email input with selector: {selector}")
                    break
            except TimeoutException:
                continue

        if not email_input:
            # Try by finding all inputs
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"  Found {len(inputs)} input elements")
            for inp in inputs:
                inp_type = inp.get_attribute("type")
                inp_name = inp.get_attribute("name")
                inp_placeholder = inp.get_attribute("placeholder")
                print(f"    Input: type={inp_type}, name={inp_name}, placeholder={inp_placeholder}")
                if inp_type in ("email", "text") and email_input is None:
                    email_input = inp

        if not email_input:
            screenshot(driver, f"login_no_email_field_{role}")
            report_bug(
                f"Login page - cannot find email input field ({role})",
                "The login page does not have a recognizable email/username input field.",
                screenshot(driver, f"bug_login_no_email_{role}")
            )
            return False

        email_input.clear()
        email_input.send_keys(email)
        time.sleep(0.5)

        # Find password field
        pwd_input = None
        for selector in [
            "input[type='password']", "input[name='password']",
            "#password", "input[placeholder*='assword']"
        ]:
            try:
                pwd_input = driver.find_element(By.CSS_SELECTOR, selector)
                if pwd_input:
                    break
            except NoSuchElementException:
                continue

        if not pwd_input:
            screenshot(driver, f"login_no_pwd_field_{role}")
            report_bug(
                f"Login page - cannot find password field ({role})",
                "The login page does not have a recognizable password input field.",
                screenshot(driver, f"bug_login_no_pwd_{role}")
            )
            return False

        pwd_input.clear()
        pwd_input.send_keys(password)
        time.sleep(0.5)

        screenshot(driver, f"login_filled_{role}")

        # Find and click login button
        login_btn = None
        for selector in [
            "button[type='submit']", "input[type='submit']",
            "button:contains('Login')", "button:contains('Sign')",
            "button.login", "#login-btn", "button"
        ]:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    txt = el.text.lower()
                    if any(kw in txt for kw in ["log in", "login", "sign in", "submit", "continue"]):
                        login_btn = el
                        break
                    if el.get_attribute("type") == "submit":
                        login_btn = el
                        break
                if login_btn:
                    break
            except Exception:
                continue

        if not login_btn:
            # Fallback: just find first submit-type button
            try:
                login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            except NoSuchElementException:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                if buttons:
                    login_btn = buttons[0]

        if login_btn:
            print(f"  Clicking login button: text='{login_btn.text}'")
            login_btn.click()
        else:
            # Try pressing Enter
            pwd_input.send_keys(Keys.RETURN)

        time.sleep(5)
        screenshot(driver, f"login_after_submit_{role}")

        current = driver.current_url
        print(f"  URL after login attempt: {current}")
        page_text = driver.find_element(By.TAG_NAME, "body").text[:500]

        # Check for error messages
        error_indicators = ["invalid", "incorrect", "wrong", "failed", "error", "not found"]
        page_lower = page_text.lower()
        if any(ei in page_lower for ei in error_indicators):
            # Could be an error but also could be normal page text
            for ei in error_indicators:
                if ei in page_lower:
                    print(f"  Warning: found '{ei}' in page text")

        # Check if we're still on login page
        if "/login" in current or "/signin" in current:
            report_bug(
                f"Login failed for {email} ({role})",
                f"After submitting credentials, still on login page. URL: {current}\nPage text snippet: {page_text[:300]}",
                screenshot(driver, f"bug_login_failed_{role}")
            )
            return False

        print(f"  Login appears successful. Current URL: {current}")
        return True

    except Exception as e:
        screenshot(driver, f"login_error_{role}")
        print(f"  Login error: {e}")
        traceback.print_exc()
        return False


def safe_navigate(driver, path, page_name):
    """Navigate to a path and return True if page loads."""
    url = f"{BASE_URL}{path}"
    print(f"\n  Navigating to: {url}")
    try:
        driver.get(url)
        time.sleep(4)
        current = driver.current_url
        print(f"  Loaded URL: {current}")
        return True
    except Exception as e:
        print(f"  Navigation error: {e}")
        return False


def check_page_errors(driver, page_name, role):
    """Check for common page errors and report bugs."""
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text
        current_url = driver.current_url

        # Check for various error states
        error_patterns = [
            ("404", "Page not found (404)"),
            ("500", "Internal server error (500)"),
            ("502", "Bad gateway (502)"),
            ("503", "Service unavailable (503)"),
            ("not found", "Page not found"),
            ("something went wrong", "Application error"),
            ("unexpected error", "Unexpected error"),
            ("access denied", "Access denied"),
            ("forbidden", "Forbidden"),
            ("unauthorized", "Unauthorized access"),
        ]

        for pattern, desc in error_patterns:
            if pattern.lower() in page_text.lower()[:2000]:
                # Avoid false positives from normal content
                if pattern in ("not found", "500") and len(page_text) > 1000:
                    continue
                scr = screenshot(driver, f"bug_{page_name}_{role}")
                report_bug(
                    f"[{role.upper()}] {page_name}: {desc}",
                    f"When navigating to {page_name} ({current_url}), encountered: {desc}\nPage snippet: {page_text[:500]}",
                    scr,
                    ["bug", "e2e-test"]
                )
                return True

        # Check if page is mostly blank
        visible_text = page_text.strip()
        if len(visible_text) < 20:
            scr = screenshot(driver, f"bug_blank_{page_name}_{role}")
            report_bug(
                f"[{role.upper()}] {page_name}: Page appears blank/empty",
                f"The page at {current_url} appears blank with minimal content.\nVisible text: '{visible_text}'",
                scr,
                ["bug", "e2e-test"]
            )
            return True

        return False
    except Exception as e:
        print(f"  Error checking page: {e}")
        return False


def find_and_click(driver, selectors, description="element", timeout=5):
    """Try multiple selectors to find and click an element."""
    for selector_type, selector_value in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((selector_type, selector_value))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.5)
            try:
                el.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", el)
            print(f"  Clicked {description} via ({selector_type}, {selector_value})")
            return True
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            continue
    print(f"  Could not find/click {description}")
    return False


def find_element_safe(driver, selectors, timeout=5):
    """Try multiple selectors to find an element."""
    for selector_type, selector_value in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((selector_type, selector_value))
            )
            return el
        except (TimeoutException, NoSuchElementException):
            continue
    return None


# ============================================================
# TEST: HELPDESK MODULE
# ============================================================
def test_helpdesk(driver, role):
    print(f"\n{'='*60}")
    print(f"TESTING HELPDESK MODULE ({role})")
    print(f"{'='*60}")

    # 1. Navigate to helpdesk dashboard
    print("\n[Step 1] Navigate to /helpdesk")
    if not safe_navigate(driver, "/helpdesk", "Helpdesk"):
        report_bug(
            f"[{role.upper()}] Helpdesk: Failed to navigate to /helpdesk",
            "Navigation to /helpdesk failed completely.",
            screenshot(driver, f"bug_helpdesk_nav_{role}")
        )
        return

    scr = screenshot(driver, f"helpdesk_dashboard_{role}")
    page_err = check_page_errors(driver, "Helpdesk Dashboard", role)

    # Check dashboard elements
    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    helpdesk_keywords = ["helpdesk", "ticket", "support", "help desk", "issue", "request", "query"]
    found_keywords = [kw for kw in helpdesk_keywords if kw in body_text]
    print(f"  Helpdesk keywords found: {found_keywords}")

    if not found_keywords and not page_err:
        report_bug(
            f"[{role.upper()}] Helpdesk Dashboard may not have loaded properly",
            f"No helpdesk-related keywords found on /helpdesk page. URL: {driver.current_url}\nPage text snippet: {body_text[:500]}",
            scr
        )

    # 2. Check ticket list
    print("\n[Step 2] Check ticket list")
    time.sleep(2)
    # Look for ticket list/table
    tickets_found = False
    for selector in ["table", "[class*='ticket']", "[class*='list']", ".card", "[class*='row']"]:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"  Found {len(elements)} elements matching '{selector}'")
                tickets_found = True
                break
        except Exception:
            continue

    scr = screenshot(driver, f"helpdesk_tickets_{role}")
    if not tickets_found:
        print("  No ticket list elements found")

    # 3. Try creating a new ticket
    print("\n[Step 3] Try creating a new ticket")
    create_clicked = find_and_click(driver, [
        (By.XPATH, "//button[contains(text(),'Create')]"),
        (By.XPATH, "//button[contains(text(),'New')]"),
        (By.XPATH, "//a[contains(text(),'Create')]"),
        (By.XPATH, "//a[contains(text(),'New')]"),
        (By.XPATH, "//button[contains(text(),'Add')]"),
        (By.XPATH, "//a[contains(text(),'Add')]"),
        (By.XPATH, "//button[contains(text(),'Raise')]"),
        (By.XPATH, "//a[contains(text(),'Raise')]"),
        (By.XPATH, "//*[contains(text(),'Create Ticket')]"),
        (By.XPATH, "//*[contains(text(),'New Ticket')]"),
        (By.XPATH, "//*[contains(text(),'Raise Ticket')]"),
        (By.CSS_SELECTOR, "button.create, button.new, a.create, a.new"),
        (By.CSS_SELECTOR, "[class*='create'], [class*='add-new']"),
        (By.CSS_SELECTOR, "button[class*='primary']"),
        (By.CSS_SELECTOR, "a[href*='create'], a[href*='new']"),
    ], "Create Ticket button", timeout=5)

    time.sleep(3)
    scr = screenshot(driver, f"helpdesk_create_ticket_{role}")

    if create_clicked:
        # Try to fill in ticket form
        print("  Attempting to fill ticket form...")
        try:
            # Look for subject/title field
            subject_input = find_element_safe(driver, [
                (By.CSS_SELECTOR, "input[name*='subject']"),
                (By.CSS_SELECTOR, "input[name*='title']"),
                (By.CSS_SELECTOR, "input[placeholder*='ubject']"),
                (By.CSS_SELECTOR, "input[placeholder*='itle']"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ])
            if subject_input:
                subject_input.clear()
                subject_input.send_keys("E2E Test Ticket - Automated Testing")
                print("  Filled subject field")

            # Look for description/body textarea
            desc_input = find_element_safe(driver, [
                (By.CSS_SELECTOR, "textarea[name*='desc']"),
                (By.CSS_SELECTOR, "textarea[name*='body']"),
                (By.CSS_SELECTOR, "textarea[name*='content']"),
                (By.CSS_SELECTOR, "textarea[placeholder*='escri']"),
                (By.CSS_SELECTOR, "textarea"),
                (By.CSS_SELECTOR, "[contenteditable='true']"),
                (By.CSS_SELECTOR, ".ql-editor"),
            ])
            if desc_input:
                desc_input.clear()
                desc_input.send_keys("This is an automated test ticket created by E2E testing.")
                print("  Filled description field")

            screenshot(driver, f"helpdesk_ticket_form_filled_{role}")

            # Try submitting
            submit_clicked = find_and_click(driver, [
                (By.XPATH, "//button[contains(text(),'Submit')]"),
                (By.XPATH, "//button[contains(text(),'Create')]"),
                (By.XPATH, "//button[contains(text(),'Save')]"),
                (By.XPATH, "//button[contains(text(),'Send')]"),
                (By.CSS_SELECTOR, "button[type='submit']"),
            ], "Submit ticket button", timeout=3)

            time.sleep(3)
            screenshot(driver, f"helpdesk_ticket_submitted_{role}")
        except Exception as e:
            print(f"  Error filling ticket form: {e}")
    else:
        print("  Could not find create ticket button")

    # 4. View ticket details
    print("\n[Step 4] View ticket details")
    safe_navigate(driver, "/helpdesk", "Helpdesk")
    time.sleep(3)

    detail_clicked = find_and_click(driver, [
        (By.CSS_SELECTOR, "table tbody tr:first-child"),
        (By.CSS_SELECTOR, "[class*='ticket-item']"),
        (By.CSS_SELECTOR, "[class*='ticket'] a"),
        (By.CSS_SELECTOR, ".card a"),
        (By.XPATH, "//a[contains(@href,'ticket')]"),
    ], "First ticket in list", timeout=5)

    time.sleep(3)
    scr = screenshot(driver, f"helpdesk_ticket_detail_{role}")
    if detail_clicked:
        check_page_errors(driver, "Ticket Detail", role)

    # 5. Check knowledge base
    print("\n[Step 5] Check knowledge base")
    kb_navigated = False
    # Try direct navigation to knowledge base paths
    for path in ["/helpdesk/knowledge-base", "/knowledge-base", "/helpdesk/kb", "/kb"]:
        if safe_navigate(driver, path, "Knowledge Base"):
            time.sleep(3)
            current = driver.current_url
            body = driver.find_element(By.TAG_NAME, "body").text
            if len(body.strip()) > 20 and "404" not in body[:100]:
                kb_navigated = True
                scr = screenshot(driver, f"helpdesk_kb_{role}")
                check_page_errors(driver, "Knowledge Base", role)
                break

    if not kb_navigated:
        # Try finding KB link from helpdesk page
        safe_navigate(driver, "/helpdesk", "Helpdesk")
        time.sleep(2)
        kb_clicked = find_and_click(driver, [
            (By.XPATH, "//a[contains(text(),'Knowledge')]"),
            (By.XPATH, "//a[contains(text(),'KB')]"),
            (By.XPATH, "//*[contains(text(),'Knowledge Base')]"),
            (By.CSS_SELECTOR, "a[href*='knowledge']"),
            (By.CSS_SELECTOR, "a[href*='kb']"),
        ], "Knowledge Base link", timeout=5)

        time.sleep(3)
        scr = screenshot(driver, f"helpdesk_kb_nav_{role}")
        if kb_clicked:
            check_page_errors(driver, "Knowledge Base", role)

    print(f"\n  Helpdesk module testing complete for {role}")


# ============================================================
# TEST: ANNOUNCEMENTS & POLICIES
# ============================================================
def test_announcements_policies(driver, role):
    print(f"\n{'='*60}")
    print(f"TESTING ANNOUNCEMENTS & POLICIES ({role})")
    print(f"{'='*60}")

    # 1. Navigate to announcements
    print("\n[Step 1] Navigate to /announcements")
    if not safe_navigate(driver, "/announcements", "Announcements"):
        report_bug(
            f"[{role.upper()}] Announcements: Failed to navigate",
            "Navigation to /announcements failed.",
            screenshot(driver, f"bug_announcements_nav_{role}")
        )
        return

    time.sleep(3)
    scr = screenshot(driver, f"announcements_page_{role}")
    check_page_errors(driver, "Announcements", role)

    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    ann_keywords = ["announcement", "notice", "bulletin", "post", "news"]
    found_kw = [kw for kw in ann_keywords if kw in body_text]
    print(f"  Announcement keywords found: {found_kw}")

    # Check for existing announcements
    print("\n[Step 2] Check existing announcements")
    announcements = driver.find_elements(By.CSS_SELECTOR, "[class*='announcement'], .card, article, [class*='post'], [class*='notice']")
    print(f"  Found {len(announcements)} potential announcement elements")
    screenshot(driver, f"announcements_list_{role}")

    # 3. Try creating announcement
    print("\n[Step 3] Try creating a new announcement")
    create_clicked = find_and_click(driver, [
        (By.XPATH, "//button[contains(text(),'Create')]"),
        (By.XPATH, "//button[contains(text(),'New')]"),
        (By.XPATH, "//button[contains(text(),'Add')]"),
        (By.XPATH, "//a[contains(text(),'Create')]"),
        (By.XPATH, "//a[contains(text(),'New')]"),
        (By.XPATH, "//*[contains(text(),'Create Announcement')]"),
        (By.XPATH, "//*[contains(text(),'New Announcement')]"),
        (By.XPATH, "//*[contains(text(),'Add Announcement')]"),
        (By.CSS_SELECTOR, "button[class*='primary']"),
        (By.CSS_SELECTOR, "a[href*='create'], a[href*='new']"),
        (By.CSS_SELECTOR, "[class*='create'], [class*='add']"),
    ], "Create Announcement button", timeout=5)

    time.sleep(3)
    scr = screenshot(driver, f"announcements_create_{role}")

    if create_clicked:
        print("  Attempting to fill announcement form...")
        try:
            title_input = find_element_safe(driver, [
                (By.CSS_SELECTOR, "input[name*='title']"),
                (By.CSS_SELECTOR, "input[name*='subject']"),
                (By.CSS_SELECTOR, "input[placeholder*='itle']"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ])
            if title_input:
                title_input.clear()
                title_input.send_keys("E2E Test Announcement")
                print("  Filled title")

            desc_input = find_element_safe(driver, [
                (By.CSS_SELECTOR, "textarea"),
                (By.CSS_SELECTOR, "[contenteditable='true']"),
                (By.CSS_SELECTOR, ".ql-editor"),
                (By.CSS_SELECTOR, "[class*='editor']"),
            ])
            if desc_input:
                desc_input.click()
                desc_input.send_keys("This is an automated test announcement.")
                print("  Filled description")

            screenshot(driver, f"announcements_form_filled_{role}")
        except Exception as e:
            print(f"  Error filling form: {e}")
    else:
        if role == "org_admin":
            print("  WARNING: Org Admin cannot find create announcement button")

    # 4. Navigate to policies
    print("\n[Step 4] Navigate to /policies")
    if not safe_navigate(driver, "/policies", "Policies"):
        report_bug(
            f"[{role.upper()}] Policies: Failed to navigate",
            "Navigation to /policies failed.",
            screenshot(driver, f"bug_policies_nav_{role}")
        )
        return

    time.sleep(3)
    scr = screenshot(driver, f"policies_page_{role}")
    check_page_errors(driver, "Policies", role)

    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    pol_keywords = ["policy", "policies", "document", "handbook", "guideline"]
    found_kw = [kw for kw in pol_keywords if kw in body_text]
    print(f"  Policy keywords found: {found_kw}")

    print(f"\n  Announcements & Policies testing complete for {role}")


# ============================================================
# TEST: SURVEYS
# ============================================================
def test_surveys(driver, role):
    print(f"\n{'='*60}")
    print(f"TESTING SURVEYS MODULE ({role})")
    print(f"{'='*60}")

    # 1. Navigate to surveys
    print("\n[Step 1] Navigate to /surveys")
    if not safe_navigate(driver, "/surveys", "Surveys"):
        report_bug(
            f"[{role.upper()}] Surveys: Failed to navigate",
            "Navigation to /surveys failed.",
            screenshot(driver, f"bug_surveys_nav_{role}")
        )
        return

    time.sleep(3)
    scr = screenshot(driver, f"surveys_page_{role}")
    check_page_errors(driver, "Surveys", role)

    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    survey_keywords = ["survey", "questionnaire", "poll", "feedback", "form"]
    found_kw = [kw for kw in survey_keywords if kw in body_text]
    print(f"  Survey keywords found: {found_kw}")

    # 2. Try creating a survey
    print("\n[Step 2] Try creating a new survey")
    create_clicked = find_and_click(driver, [
        (By.XPATH, "//button[contains(text(),'Create')]"),
        (By.XPATH, "//button[contains(text(),'New')]"),
        (By.XPATH, "//button[contains(text(),'Add')]"),
        (By.XPATH, "//a[contains(text(),'Create')]"),
        (By.XPATH, "//a[contains(text(),'New')]"),
        (By.XPATH, "//*[contains(text(),'Create Survey')]"),
        (By.XPATH, "//*[contains(text(),'New Survey')]"),
        (By.CSS_SELECTOR, "button[class*='primary']"),
        (By.CSS_SELECTOR, "a[href*='create'], a[href*='new']"),
    ], "Create Survey button", timeout=5)

    time.sleep(3)
    scr = screenshot(driver, f"surveys_create_{role}")

    if create_clicked:
        print("  Attempting to fill survey form...")
        try:
            title_input = find_element_safe(driver, [
                (By.CSS_SELECTOR, "input[name*='title']"),
                (By.CSS_SELECTOR, "input[name*='name']"),
                (By.CSS_SELECTOR, "input[placeholder*='itle']"),
                (By.CSS_SELECTOR, "input[placeholder*='ame']"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ])
            if title_input:
                title_input.clear()
                title_input.send_keys("E2E Test Survey")
                print("  Filled title")

            desc_input = find_element_safe(driver, [
                (By.CSS_SELECTOR, "textarea"),
                (By.CSS_SELECTOR, "[contenteditable='true']"),
                (By.CSS_SELECTOR, ".ql-editor"),
            ])
            if desc_input:
                desc_input.click()
                desc_input.send_keys("Automated test survey description.")
                print("  Filled description")

            screenshot(driver, f"surveys_form_filled_{role}")
        except Exception as e:
            print(f"  Error filling form: {e}")
    else:
        if role == "org_admin":
            print("  Note: Could not find create survey button")

    print(f"\n  Surveys testing complete for {role}")


# ============================================================
# TEST: FORUM
# ============================================================
def test_forum(driver, role):
    print(f"\n{'='*60}")
    print(f"TESTING FORUM MODULE ({role})")
    print(f"{'='*60}")

    # 1. Navigate to forum
    print("\n[Step 1] Navigate to /forum")
    if not safe_navigate(driver, "/forum", "Forum"):
        report_bug(
            f"[{role.upper()}] Forum: Failed to navigate",
            "Navigation to /forum failed.",
            screenshot(driver, f"bug_forum_nav_{role}")
        )
        return

    time.sleep(3)
    scr = screenshot(driver, f"forum_page_{role}")
    check_page_errors(driver, "Forum", role)

    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    forum_keywords = ["forum", "discussion", "post", "topic", "thread", "community"]
    found_kw = [kw for kw in forum_keywords if kw in body_text]
    print(f"  Forum keywords found: {found_kw}")

    # 2. Try creating a post
    print("\n[Step 2] Try creating a new post")
    create_clicked = find_and_click(driver, [
        (By.XPATH, "//button[contains(text(),'Create')]"),
        (By.XPATH, "//button[contains(text(),'New')]"),
        (By.XPATH, "//button[contains(text(),'Add')]"),
        (By.XPATH, "//button[contains(text(),'Post')]"),
        (By.XPATH, "//a[contains(text(),'Create')]"),
        (By.XPATH, "//a[contains(text(),'New')]"),
        (By.XPATH, "//*[contains(text(),'Create Post')]"),
        (By.XPATH, "//*[contains(text(),'New Post')]"),
        (By.XPATH, "//*[contains(text(),'New Topic')]"),
        (By.XPATH, "//*[contains(text(),'Start Discussion')]"),
        (By.CSS_SELECTOR, "button[class*='primary']"),
        (By.CSS_SELECTOR, "a[href*='create'], a[href*='new']"),
    ], "Create Post button", timeout=5)

    time.sleep(3)
    scr = screenshot(driver, f"forum_create_{role}")

    if create_clicked:
        print("  Attempting to fill post form...")
        try:
            title_input = find_element_safe(driver, [
                (By.CSS_SELECTOR, "input[name*='title']"),
                (By.CSS_SELECTOR, "input[name*='subject']"),
                (By.CSS_SELECTOR, "input[placeholder*='itle']"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ])
            if title_input:
                title_input.clear()
                title_input.send_keys("E2E Test Forum Post")
                print("  Filled title")

            body_input = find_element_safe(driver, [
                (By.CSS_SELECTOR, "textarea"),
                (By.CSS_SELECTOR, "[contenteditable='true']"),
                (By.CSS_SELECTOR, ".ql-editor"),
            ])
            if body_input:
                body_input.click()
                body_input.send_keys("This is an automated test forum post.")
                print("  Filled body")

            screenshot(driver, f"forum_post_form_filled_{role}")
        except Exception as e:
            print(f"  Error filling form: {e}")
    else:
        print("  Could not find create post button")

    print(f"\n  Forum testing complete for {role}")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("EMP CLOUD HRMS - E2E TEST")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}")
    print("=" * 60)

    # Test as Org Admin
    driver = get_driver()
    try:
        logged_in = login(driver, "ananya@technova.in", "Welcome@123", "org_admin")
        if logged_in:
            test_helpdesk(driver, "org_admin")
            test_announcements_policies(driver, "org_admin")
            test_surveys(driver, "org_admin")
            test_forum(driver, "org_admin")
        else:
            print("\n  *** Org Admin login failed - skipping tests ***")
    except Exception as e:
        print(f"\nFatal error during Org Admin tests: {e}")
        traceback.print_exc()
        screenshot(driver, "fatal_error_org_admin")
    finally:
        driver.quit()

    # Test as Employee
    driver = get_driver()
    try:
        logged_in = login(driver, "priya@technova.in", "Welcome@123", "employee")
        if logged_in:
            test_helpdesk(driver, "employee")
            test_announcements_policies(driver, "employee")
            test_surveys(driver, "employee")
            test_forum(driver, "employee")
        else:
            print("\n  *** Employee login failed - skipping tests ***")
    except Exception as e:
        print(f"\nFatal error during Employee tests: {e}")
        traceback.print_exc()
        screenshot(driver, "fatal_error_employee")
    finally:
        driver.quit()

    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total bugs found: {len(BUGS_FOUND)}")
    for i, bug in enumerate(BUGS_FOUND, 1):
        print(f"  {i}. {bug['title']}")
    print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
    print("Done!")


if __name__ == "__main__":
    main()
