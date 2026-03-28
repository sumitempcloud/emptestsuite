import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import traceback
import subprocess
import base64
import urllib.request
import urllib.error
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
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──
BASE_URL = "https://test-empcloud.empcloud.com"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots"
GITHUB_TOKEN = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_found = []


def take_screenshot(driver, name):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{ts}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    driver.save_screenshot(filepath)
    print(f"  [SCREENSHOT] {filepath}")
    return filepath


def upload_screenshot_to_github(filepath, token, repo):
    """Upload screenshot to the repo and return the raw URL."""
    try:
        filename = os.path.basename(filepath)
        path_in_repo = f"screenshots/{filename}"
        with open(filepath, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode("utf-8")

        url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
        payload = json.dumps({
            "message": f"Upload screenshot {filename}",
            "content": content_b64,
            "branch": "main"
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, method="PUT")
        req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("Content-Type", "application/json")

        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        download_url = data.get("content", {}).get("download_url", "")
        print(f"  [UPLOAD] {download_url}")
        return download_url
    except Exception as e:
        print(f"  [UPLOAD FAILED] {e}")
        return None


def create_github_issue(title, body, token, repo):
    """Create an issue on GitHub."""
    try:
        url = f"https://api.github.com/repos/{repo}/issues"
        payload = json.dumps({
            "title": title,
            "body": body,
            "labels": ["bug", "e2e-test"]
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("Content-Type", "application/json")

        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        issue_url = data.get("html_url", "")
        print(f"  [ISSUE CREATED] {issue_url}")
        return issue_url
    except Exception as e:
        print(f"  [ISSUE CREATION FAILED] {e}")
        return None


def file_bug(driver, title, description, screenshot_path=None):
    """Record a bug and create a GitHub issue with screenshot."""
    print(f"  [BUG] {title}")
    img_md = ""
    if screenshot_path:
        img_url = upload_screenshot_to_github(screenshot_path, GITHUB_TOKEN, GITHUB_REPO)
        if img_url:
            img_md = f"\n\n### Screenshot\n![screenshot]({img_url})"

    body = (
        f"## Bug Report (Automated E2E Test)\n\n"
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**User:** {EMP_EMAIL} (Employee)\n"
        f"**URL:** {driver.current_url}\n\n"
        f"### Description\n{description}"
        f"{img_md}\n\n"
        f"### Steps to Reproduce\n"
        f"1. Log in as employee ({EMP_EMAIL})\n"
        f"2. See description above\n\n"
        f"### Expected Behavior\nPage/feature should load and function correctly.\n\n"
        f"### Environment\n- Browser: Chrome (headless)\n- Resolution: 1920x1080\n"
    )
    issue_url = create_github_issue(title, body, GITHUB_TOKEN, GITHUB_REPO)
    bugs_found.append({"title": title, "issue_url": issue_url})


def wait_for_page_ready(driver, timeout=15):
    """Wait for Angular/page to settle."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except:
        pass
    time.sleep(2)


def safe_click(driver, element):
    """Click an element, falling back to JS click."""
    try:
        element.click()
    except (ElementClickInterceptedException, WebDriverException):
        driver.execute_script("arguments[0].click();", element)


def navigate_to(driver, path, label="page"):
    """Navigate to a path and wait for load."""
    url = f"{BASE_URL}{path}"
    print(f"  Navigating to {url}")
    driver.get(url)
    wait_for_page_ready(driver)
    time.sleep(2)


def check_page_loaded(driver, path, identifiers, label):
    """
    Check if a page loaded by looking for any of the identifier texts/elements.
    Returns True if page seems loaded, False if it looks like an error.
    """
    page_source = driver.page_source.lower()
    current_url = driver.current_url.lower()

    # Check for common error indicators
    error_signs = ["404", "not found", "access denied", "forbidden", "error", "unauthorized"]
    found_error = None
    for sign in error_signs:
        if sign in page_source and sign not in label.lower():
            # Check more carefully - look in headings / prominent text
            try:
                headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, .error, .not-found")
                for h in headings:
                    if sign in h.text.lower():
                        found_error = sign
                        break
            except:
                pass

    # Check if we got redirected back to login
    if "/login" in current_url and "/login" not in path:
        return False, "Redirected to login page - possible auth issue"

    # Check for blank page
    body_text = ""
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body_text = body.text.strip()
    except:
        pass

    if len(body_text) < 20 and "login" not in path:
        return False, "Page appears blank or has minimal content"

    return True, "OK"


def setup_driver():
    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--ignore-certificate-errors")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.implicitly_wait(5)
    return driver


def login(driver):
    print("\n[LOGIN] Logging in as employee...")
    driver.get(f"{BASE_URL}/login")
    wait_for_page_ready(driver)
    time.sleep(2)

    take_screenshot(driver, "01_login_page")

    # Find email/password fields
    email_field = None
    pass_field = None

    # Try multiple selectors
    for sel in [
        "input[type='email']", "input[name='email']", "input[formcontrolname='email']",
        "input[placeholder*='mail']", "input[placeholder*='Mail']",
        "input[type='text']", "#email", "#username"
    ]:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                email_field = elems[0]
                break
        except:
            pass

    for sel in [
        "input[type='password']", "input[name='password']",
        "input[formcontrolname='password']", "#password"
    ]:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                pass_field = elems[0]
                break
        except:
            pass

    if not email_field or not pass_field:
        print("  [ERROR] Could not find login fields!")
        take_screenshot(driver, "01_login_fields_not_found")
        # Try looking at all inputs
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"  Found {len(inputs)} input elements:")
        for i, inp in enumerate(inputs):
            print(f"    [{i}] type={inp.get_attribute('type')} name={inp.get_attribute('name')} placeholder={inp.get_attribute('placeholder')}")
        if len(inputs) >= 2:
            email_field = inputs[0]
            pass_field = inputs[1]
        else:
            raise Exception("Cannot find login fields")

    email_field.clear()
    email_field.send_keys(EMP_EMAIL)
    time.sleep(0.5)
    pass_field.clear()
    pass_field.send_keys(EMP_PASS)
    time.sleep(0.5)

    take_screenshot(driver, "01_login_filled")

    # Click login button
    login_btn = None
    for sel in [
        "button[type='submit']", "button.login-btn", "button.btn-primary",
        "button[color='primary']", "button.mat-raised-button"
    ]:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                login_btn = elems[0]
                break
        except:
            pass

    if not login_btn:
        # Try finding by text
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            txt = btn.text.lower()
            if "login" in txt or "sign in" in txt or "log in" in txt:
                login_btn = btn
                break

    if login_btn:
        safe_click(driver, login_btn)
    else:
        pass_field.send_keys(Keys.RETURN)

    print("  Waiting for login to complete...")
    time.sleep(5)
    wait_for_page_ready(driver)

    take_screenshot(driver, "01_login_result")

    current_url = driver.current_url
    print(f"  Current URL after login: {current_url}")

    if "/login" in current_url.lower():
        # Check for error messages
        try:
            errors = driver.find_elements(By.CSS_SELECTOR, ".error, .alert, .mat-error, .toast-error, .snackbar")
            for err in errors:
                if err.text.strip():
                    print(f"  [LOGIN ERROR] {err.text.strip()}")
        except:
            pass
        print("  [WARNING] Still on login page - login may have failed")
        ss = take_screenshot(driver, "01_login_failed")
        file_bug(driver, "Employee Login: Login may have failed",
                 "After entering credentials and clicking login, the page remained on the login URL. "
                 "This could indicate invalid credentials, a server error, or a UI issue.", ss)
        return False

    print("  [OK] Login appears successful")
    return True


def test_self_service(driver):
    print("\n" + "=" * 60)
    print("[MODULE] Self-Service Dashboard")
    print("=" * 60)

    navigate_to(driver, "/self-service", "Self-Service")
    ss = take_screenshot(driver, "02_self_service_dashboard")

    loaded, msg = check_page_loaded(driver, "/self-service", [], "Self-Service")
    if not loaded:
        print(f"  [FAIL] Self-Service dashboard did not load: {msg}")
        file_bug(driver, "Self-Service: Dashboard fails to load",
                 f"Navigating to /self-service failed. {msg}", ss)
        return

    print(f"  Current URL: {driver.current_url}")
    body_text = driver.find_element(By.TAG_NAME, "body").text

    # Check for key self-service elements
    checks = {
        "profile": ["profile", "my profile", "personal", "employee info"],
        "leave_balance": ["leave", "balance", "time off", "pto"],
        "attendance": ["attendance", "check-in", "check in", "clock", "punch"],
    }

    body_lower = body_text.lower()
    for feature, keywords in checks.items():
        found = any(kw in body_lower for kw in keywords)
        if found:
            print(f"  [OK] Found '{feature}' related content")
        else:
            print(f"  [INFO] '{feature}' content not visible on this view")

    # Try to find cards or sections
    cards = driver.find_elements(By.CSS_SELECTOR, ".card, .mat-card, .widget, .dashboard-card, .panel, mat-card")
    print(f"  Found {len(cards)} card/panel elements")

    # Look for navigation items in self-service
    nav_items = driver.find_elements(By.CSS_SELECTOR, "a[href*='self-service'], .nav-item, .menu-item, mat-list-item")
    print(f"  Found {len(nav_items)} navigation items")

    # Check for leave balance specifically
    navigate_to(driver, "/self-service/leave", "Self-Service Leave")
    time.sleep(2)
    ss_leave = take_screenshot(driver, "02_self_service_leave")

    navigate_to(driver, "/self-service/attendance", "Self-Service Attendance")
    time.sleep(2)
    ss_att = take_screenshot(driver, "02_self_service_attendance")

    # Check profile
    navigate_to(driver, "/self-service/profile", "Self-Service Profile")
    time.sleep(2)
    ss_profile = take_screenshot(driver, "02_self_service_profile")

    print("  [DONE] Self-Service module tested")


def test_wellness(driver):
    print("\n" + "=" * 60)
    print("[MODULE] Wellness")
    print("=" * 60)

    navigate_to(driver, "/wellness", "Wellness")
    ss = take_screenshot(driver, "03_wellness_page")

    loaded, msg = check_page_loaded(driver, "/wellness", [], "Wellness")
    if not loaded:
        print(f"  [FAIL] Wellness page did not load: {msg}")
        file_bug(driver, "Wellness: Page fails to load",
                 f"Navigating to /wellness failed. {msg}", ss)
        return

    print(f"  Current URL: {driver.current_url}")
    body_text = driver.find_element(By.TAG_NAME, "body").text
    body_lower = body_text.lower()

    # Check for daily check-in feature
    checkin_keywords = ["check-in", "check in", "checkin", "daily", "how are you", "mood", "feeling", "wellness"]
    found_checkin = any(kw in body_lower for kw in checkin_keywords)

    if found_checkin:
        print("  [OK] Found check-in / wellness related content")
    else:
        print("  [INFO] No obvious check-in content found on wellness page")

    # Try to interact with daily check-in
    checkin_btns = []
    for sel in [
        "button", ".checkin-btn", ".check-in", "[class*='checkin']",
        "[class*='check-in']", "mat-button-toggle", ".mood-btn", ".emoji"
    ]:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            checkin_btns.extend(elems)
        except:
            pass

    # Look for mood/emoji selectors or rating elements
    mood_elements = driver.find_elements(By.CSS_SELECTOR,
        ".mood, .emoji, .rating, [class*='mood'], [class*='emoji'], mat-icon, .face-icon, .smiley")
    if mood_elements:
        print(f"  Found {len(mood_elements)} mood/emoji elements")
        try:
            safe_click(driver, mood_elements[0])
            time.sleep(2)
            take_screenshot(driver, "03_wellness_checkin_click")
        except Exception as e:
            print(f"  Could not click mood element: {e}")

    # Try navigating to check-in sub-path
    navigate_to(driver, "/wellness/check-in", "Wellness Check-in")
    time.sleep(2)
    ss2 = take_screenshot(driver, "03_wellness_checkin_page")

    navigate_to(driver, "/wellness/daily-checkin", "Wellness Daily Check-in")
    time.sleep(2)
    ss3 = take_screenshot(driver, "03_wellness_daily_checkin")

    print("  [DONE] Wellness module tested")


def test_events(driver):
    print("\n" + "=" * 60)
    print("[MODULE] Events")
    print("=" * 60)

    navigate_to(driver, "/events", "Events")
    ss = take_screenshot(driver, "04_events_page")

    loaded, msg = check_page_loaded(driver, "/events", [], "Events")
    if not loaded:
        print(f"  [FAIL] Events page did not load: {msg}")
        file_bug(driver, "Events: Page fails to load",
                 f"Navigating to /events failed. {msg}", ss)
        return

    print(f"  Current URL: {driver.current_url}")
    body_text = driver.find_element(By.TAG_NAME, "body").text
    body_lower = body_text.lower()

    event_keywords = ["event", "calendar", "upcoming", "past", "my events", "schedule"]
    found = any(kw in body_lower for kw in event_keywords)
    if found:
        print("  [OK] Found event-related content")
    else:
        print("  [INFO] No obvious event content found")

    # Check my-events view
    navigate_to(driver, "/events/my-events", "My Events")
    time.sleep(2)
    ss2 = take_screenshot(driver, "04_events_my_events")

    # Try /my-events as alternate path
    navigate_to(driver, "/my-events", "My Events (alt path)")
    time.sleep(2)
    take_screenshot(driver, "04_my_events_alt")

    print("  [DONE] Events module tested")


def test_assets(driver):
    print("\n" + "=" * 60)
    print("[MODULE] Assets")
    print("=" * 60)

    navigate_to(driver, "/assets", "Assets")
    ss = take_screenshot(driver, "05_assets_page")

    loaded, msg = check_page_loaded(driver, "/assets", [], "Assets")
    if not loaded:
        print(f"  [FAIL] Assets page did not load: {msg}")
        file_bug(driver, "Assets: Page fails to load",
                 f"Navigating to /assets failed. {msg}", ss)

    print(f"  Current URL: {driver.current_url}")

    # Also try my-assets
    navigate_to(driver, "/my-assets", "My Assets")
    time.sleep(2)
    ss2 = take_screenshot(driver, "05_my_assets")

    navigate_to(driver, "/assets/my-assets", "My Assets (nested)")
    time.sleep(2)
    take_screenshot(driver, "05_assets_my_assets")

    print("  [DONE] Assets module tested")


def test_feedback(driver):
    print("\n" + "=" * 60)
    print("[MODULE] Feedback")
    print("=" * 60)

    navigate_to(driver, "/feedback", "Feedback")
    ss = take_screenshot(driver, "06_feedback_page")

    loaded, msg = check_page_loaded(driver, "/feedback", [], "Feedback")
    if not loaded:
        print(f"  [FAIL] Feedback page did not load: {msg}")
        file_bug(driver, "Feedback: Page fails to load",
                 f"Navigating to /feedback failed. {msg}", ss)
        return

    print(f"  Current URL: {driver.current_url}")
    body_text = driver.find_element(By.TAG_NAME, "body").text
    body_lower = body_text.lower()

    feedback_keywords = ["feedback", "submit", "review", "rating", "comment", "peer", "360"]
    found = any(kw in body_lower for kw in feedback_keywords)
    if found:
        print("  [OK] Found feedback-related content")
    else:
        print("  [INFO] No obvious feedback content found")

    # Try to find and click a "Give Feedback" or "Submit" button
    for text_match in ["give feedback", "new feedback", "submit feedback", "add feedback", "create", "new", "give"]:
        try:
            buttons = driver.find_elements(By.XPATH,
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text_match}')]")
            if buttons:
                print(f"  Found button: '{buttons[0].text}'")
                safe_click(driver, buttons[0])
                time.sleep(3)
                take_screenshot(driver, "06_feedback_new_form")
                break
        except:
            pass

    # Look for any text areas to submit feedback
    textareas = driver.find_elements(By.CSS_SELECTOR, "textarea, input[type='text'], mat-form-field input")
    if textareas:
        print(f"  Found {len(textareas)} input fields for feedback")
        try:
            textareas[0].clear()
            textareas[0].send_keys("This is an automated test feedback entry.")
            time.sleep(1)
            take_screenshot(driver, "06_feedback_filled")
        except Exception as e:
            print(f"  Could not fill feedback form: {e}")

    # Look for submit button
    for sel in ["button[type='submit']", "button.submit", "button.mat-raised-button"]:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                if "submit" in btn.text.lower() or "send" in btn.text.lower() or "save" in btn.text.lower():
                    print(f"  Found submit button: '{btn.text}'")
                    # Don't actually submit to avoid polluting data
                    take_screenshot(driver, "06_feedback_ready_submit")
                    break
        except:
            pass

    print("  [DONE] Feedback module tested")


def test_positions(driver):
    print("\n" + "=" * 60)
    print("[MODULE] Positions")
    print("=" * 60)

    navigate_to(driver, "/positions", "Positions")
    ss = take_screenshot(driver, "07_positions_page")

    loaded, msg = check_page_loaded(driver, "/positions", [], "Positions")
    if not loaded:
        print(f"  [FAIL] Positions page did not load: {msg}")
        file_bug(driver, "Positions: Page fails to load",
                 f"Navigating to /positions failed. {msg}", ss)

    print(f"  Current URL: {driver.current_url}")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    body_lower = body_text.lower()

    pos_keywords = ["position", "job", "opening", "vacancy", "role", "designation"]
    found = any(kw in body_lower for kw in pos_keywords)
    if found:
        print("  [OK] Found positions-related content")
    else:
        print("  [INFO] No obvious positions content found")

    # Try alternate paths
    navigate_to(driver, "/positions/open", "Open Positions")
    time.sleep(2)
    take_screenshot(driver, "07_positions_open")

    print("  [DONE] Positions module tested")


def test_ai_chatbot(driver):
    print("\n" + "=" * 60)
    print("[MODULE] AI Chatbot")
    print("=" * 60)

    # Go to dashboard first so chatbot bubble is visible
    navigate_to(driver, "/dashboard", "Dashboard")
    time.sleep(3)

    # Look for the purple chatbot bubble (typically bottom-right)
    chatbot_selectors = [
        ".chatbot-bubble", ".chat-bubble", ".chat-btn", ".chat-fab",
        ".chatbot-fab", ".chatbot-icon", ".ai-chat", ".chat-widget",
        "[class*='chatbot']", "[class*='chat-bot']", "[class*='chat-bubble']",
        "[class*='chat-widget']", "[class*='ai-chat']", "[class*='assistant']",
        "button[class*='chat']", "div[class*='chat-float']",
        ".fab-chat", ".floating-chat", "#chatbot", "#chat-widget",
        "mat-icon[class*='chat']", ".bot-icon",
        # Common chatbot widget selectors
        "iframe[title*='chat']", "#intercom-container",
        ".crisp-client", "#hubspot-messages-iframe-container"
    ]

    chatbot_elem = None
    for sel in chatbot_selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                for elem in elems:
                    if elem.is_displayed():
                        chatbot_elem = elem
                        print(f"  Found chatbot element with selector: {sel}")
                        break
            if chatbot_elem:
                break
        except:
            pass

    # Also try finding by position - look for fixed/floating elements at bottom-right
    if not chatbot_elem:
        try:
            all_fixed = driver.execute_script("""
                var elems = document.querySelectorAll('*');
                var results = [];
                for (var i = 0; i < elems.length; i++) {
                    var style = window.getComputedStyle(elems[i]);
                    if ((style.position === 'fixed' || style.position === 'absolute') &&
                        parseInt(style.bottom) < 100 && parseInt(style.right) < 100 &&
                        elems[i].offsetWidth > 30 && elems[i].offsetWidth < 120) {
                        results.push({
                            tag: elems[i].tagName,
                            className: elems[i].className,
                            id: elems[i].id,
                            text: elems[i].innerText.substring(0, 50)
                        });
                    }
                }
                return results;
            """)
            if all_fixed:
                print(f"  Found {len(all_fixed)} fixed elements near bottom-right:")
                for elem_info in all_fixed:
                    print(f"    {elem_info}")
        except Exception as e:
            print(f"  Error scanning for fixed elements: {e}")

    # Try finding by looking at bottom-right area with broader approach
    if not chatbot_elem:
        try:
            # Look for any clickable elements with chat-like attributes
            elems = driver.find_elements(By.XPATH,
                "//*[contains(@class,'chat') or contains(@class,'bot') or contains(@class,'assistant') or contains(@class,'bubble') or contains(@class,'fab')]")
            for elem in elems:
                if elem.is_displayed():
                    chatbot_elem = elem
                    print(f"  Found potential chatbot: tag={elem.tag_name}, class={elem.get_attribute('class')}")
                    break
        except:
            pass

    ss = take_screenshot(driver, "08_chatbot_search")

    if not chatbot_elem:
        print("  [INFO] Chatbot bubble not found on dashboard, trying other pages...")
        # Try from self-service page
        for path in ["/self-service", "/", "/home"]:
            navigate_to(driver, path, "page")
            time.sleep(3)
            for sel in chatbot_selectors[:10]:
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                    if elems:
                        for elem in elems:
                            if elem.is_displayed():
                                chatbot_elem = elem
                                break
                    if chatbot_elem:
                        break
                except:
                    pass
            if chatbot_elem:
                break

    if not chatbot_elem:
        print("  [WARN] Could not find chatbot bubble element")
        ss = take_screenshot(driver, "08_chatbot_not_found")
        file_bug(driver, "AI Chatbot: Chatbot bubble not found or not visible",
                 "The purple AI chatbot bubble expected at the bottom-right corner was not found "
                 "on the dashboard, self-service, or home pages. The chatbot may not be enabled "
                 "for employee users or the element selector may have changed.", ss)
        return

    # Click the chatbot
    try:
        safe_click(driver, chatbot_elem)
        time.sleep(3)
        take_screenshot(driver, "08_chatbot_opened")
        print("  [OK] Chatbot clicked")
    except Exception as e:
        print(f"  [ERROR] Could not click chatbot: {e}")
        ss = take_screenshot(driver, "08_chatbot_click_failed")
        file_bug(driver, "AI Chatbot: Could not open chatbot",
                 f"Found the chatbot element but clicking it failed: {e}", ss)
        return

    # Try to find the chat input
    chat_input = None
    for sel in [
        "input[placeholder*='message']", "input[placeholder*='type']", "input[placeholder*='chat']",
        "input[placeholder*='ask']", "textarea[placeholder*='message']", "textarea[placeholder*='type']",
        ".chat-input input", ".chat-input textarea", ".chatbot-input input",
        "[class*='chat'] input", "[class*='chat'] textarea",
        "input[type='text']", "textarea"
    ]:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                if elem.is_displayed():
                    chat_input = elem
                    break
            if chat_input:
                break
        except:
            pass

    if chat_input:
        print("  [OK] Found chat input field")
        try:
            chat_input.clear()
            chat_input.send_keys("What is my leave balance?")
            time.sleep(1)
            take_screenshot(driver, "08_chatbot_message_typed")

            # Send the message
            chat_input.send_keys(Keys.RETURN)
            time.sleep(5)  # Wait for AI response

            take_screenshot(driver, "08_chatbot_response")
            print("  [OK] Message sent and response captured")
        except Exception as e:
            print(f"  [ERROR] Could not type in chatbot: {e}")
            ss = take_screenshot(driver, "08_chatbot_type_failed")
            file_bug(driver, "AI Chatbot: Cannot type message in chatbot",
                     f"Found chatbot input but could not type message: {e}", ss)
    else:
        print("  [WARN] Could not find chat input field")
        ss = take_screenshot(driver, "08_chatbot_no_input")
        file_bug(driver, "AI Chatbot: No input field found after opening chatbot",
                 "After clicking the chatbot bubble, no text input field was found to type a message.", ss)

    print("  [DONE] AI Chatbot module tested")


def main():
    print("=" * 60)
    print("EMP Cloud HRMS - Employee E2E Test Suite")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"User: {EMP_EMAIL}")
    print("=" * 60)

    driver = setup_driver()
    try:
        # Login
        login_ok = login(driver)
        if not login_ok:
            print("\n[WARN] Login may have failed but continuing tests...")

        # Run all module tests
        test_self_service(driver)
        test_wellness(driver)
        test_events(driver)
        test_assets(driver)
        test_feedback(driver)
        test_positions(driver)
        test_ai_chatbot(driver)

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        traceback.print_exc()
        take_screenshot(driver, "99_fatal_error")
    finally:
        driver.quit()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total bugs filed: {len(bugs_found)}")
    for i, bug in enumerate(bugs_found, 1):
        print(f"  {i}. {bug['title']}")
        if bug.get('issue_url'):
            print(f"     Issue: {bug['issue_url']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
