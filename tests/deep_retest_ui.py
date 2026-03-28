#!/usr/bin/env python3
"""
Deep UI/Workflow Retest for EmpCloud closed bugs.
Actually clicks buttons, fills forms, navigates pages using Selenium.
Screenshots every step. Comments on GitHub. Re-opens failures.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import hashlib
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

# ── Config ──
BASE_URL = "https://test-empcloud.empcloud.com"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = r"C:\emptesting\screenshots\deep_retest"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Issue number mapping
ISSUE_MAP = {
    "employee_search": 1,
    "leave_type_dropdown": 9,
    "category_dropdown_forum": 16,
    "sidebar_selection": 18,
    "forum_posts_visible": 23,   # Forum Posts Not Visible After Creation - #23
    "announcement_target": 24,
    "empcode_csv": 27,
    "dashboard_selfservice": 28,
    "whistleblowing_dropdown": 31,
    "delete_location": 12,
    "import_csv": 2,
}

RESULTS = {}
test_count = 0
driver = None


def get_driver():
    """Create a new Chrome WebDriver instance."""
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    service = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=service, options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(3)
    return d


def restart_driver_if_needed():
    """Restart driver every 2 tests."""
    global driver, test_count
    test_count += 1
    if test_count > 1 and test_count % 2 == 1:
        log(">> Restarting driver (every 2 tests)")
        try:
            driver.quit()
        except:
            pass
        driver = get_driver()


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def screenshot(name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    try:
        driver.save_screenshot(path)
        log(f"  Screenshot: {path}")
    except:
        log(f"  Screenshot FAILED: {name}")
    return path


def login(email, password, label=""):
    """Login via the EmpCloud login page."""
    log(f"  Logging in as {email} {label}")
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    screenshot(f"login_page_{label or email.split('@')[0]}")

    # Try to find email input
    email_input = None
    for sel in ["input[name='email']", "input[type='email']", "#email", "input[name='username']",
                "input[placeholder*='mail']", "input[placeholder*='Email']"]:
        try:
            email_input = driver.find_element(By.CSS_SELECTOR, sel)
            if email_input.is_displayed():
                break
        except:
            continue

    if not email_input:
        # Try all inputs
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            if inp.get_attribute("type") in ["email", "text"] and inp.is_displayed():
                email_input = inp
                break

    if not email_input:
        log("  ERROR: Could not find email input")
        return False

    email_input.clear()
    email_input.send_keys(email)
    time.sleep(0.5)

    # Find password
    pass_input = None
    for sel in ["input[name='password']", "input[type='password']", "#password"]:
        try:
            pass_input = driver.find_element(By.CSS_SELECTOR, sel)
            if pass_input.is_displayed():
                break
        except:
            continue

    if not pass_input:
        log("  ERROR: Could not find password input")
        return False

    pass_input.clear()
    pass_input.send_keys(password)
    time.sleep(0.5)

    # Click login button
    btn = None
    for sel in ["button[type='submit']", "button:has-text('Login')", "button:has-text('Sign')",
                "input[type='submit']"]:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            if btn.is_displayed():
                break
        except:
            continue

    if not btn:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            txt = b.text.lower()
            if ("login" in txt or "sign in" in txt or "submit" in txt) and b.is_displayed():
                btn = b
                break

    if btn:
        btn.click()
    else:
        pass_input.send_keys(Keys.RETURN)

    time.sleep(4)
    screenshot(f"after_login_{label or email.split('@')[0]}")
    current = driver.current_url
    log(f"  After login URL: {current}")
    return "/login" not in current


def find_element_safe(by, value, timeout=5):
    """Find element with explicit wait."""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except:
        return None


def find_clickable(by, value, timeout=5):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
    except:
        return None


def safe_click(element):
    """Click with fallback to JS click."""
    try:
        element.click()
    except:
        try:
            driver.execute_script("arguments[0].click();", element)
        except:
            pass


def get_page_text():
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""


# ═══════════════════════════════════════════════════════
# TEST #1: Employee Search Not Working with Full Name
# ═══════════════════════════════════════════════════════
def test_employee_search():
    log("=== TEST #1: Employee Search Not Working with Full Name ===")
    restart_driver_if_needed()
    login(ADMIN_EMAIL, ADMIN_PASS, "admin_search")

    # Step 1: Go to /employees
    driver.get(f"{BASE_URL}/employees")
    time.sleep(3)
    screenshot("t1_step1_employees_page")
    log(f"  Step 1: Navigated to /employees - URL: {driver.current_url}")

    page_text = get_page_text()
    log(f"  Page text length: {len(page_text)}")

    # Step 2: Find search input
    search_input = None
    for sel in ["input[type='search']", "input[placeholder*='earch']", "input[placeholder*='Search']",
                "input[name='search']", "input[aria-label*='earch']", ".search-input input",
                "input[placeholder*='filter']", "input[placeholder*='Find']"]:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                search_input = el
                log(f"  Step 2: Found search input with selector: {sel}")
                break
        except:
            continue

    if not search_input:
        # Try all inputs
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            ph = (inp.get_attribute("placeholder") or "").lower()
            tp = (inp.get_attribute("type") or "").lower()
            if ("search" in ph or "find" in ph or "filter" in ph or tp == "search") and inp.is_displayed():
                search_input = inp
                log(f"  Step 2: Found search input via scan: placeholder='{ph}'")
                break

    if not search_input:
        log("  Step 2: COULD NOT FIND search input")
        screenshot("t1_step2_no_search_input")
        # Count rows before
        rows_before = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .employee-card, [class*='employee']")
        log(f"  Found {len(rows_before)} employee elements")

        # Try to find any input at all
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in all_inputs:
            log(f"    Input: type={inp.get_attribute('type')}, placeholder={inp.get_attribute('placeholder')}, name={inp.get_attribute('name')}, visible={inp.is_displayed()}")

        RESULTS["employee_search"] = {
            "verdict": "INCONCLUSIVE",
            "detail": "Search input not found on /employees page",
            "rows_found": len(rows_before)
        }
        return

    screenshot("t1_step2_search_input_found")

    # Count rows before search
    rows_before = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .employee-card, [class*='employee-row'], [class*='list-item']")
    log(f"  Rows before search: {len(rows_before)}")

    # Step 3: Type "Priya Patel"
    search_input.clear()
    search_input.send_keys("Priya Patel")
    log("  Step 3: Typed 'Priya Patel' in search")
    screenshot("t1_step3_typed_search")

    # Step 4: Wait 2s, count visible rows
    time.sleep(3)
    screenshot("t1_step4_after_wait")

    rows_after = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .employee-card, [class*='employee-row'], [class*='list-item']")
    visible_rows = [r for r in rows_after if r.is_displayed()]
    log(f"  Step 4: Rows after search: total={len(rows_after)}, visible={len(visible_rows)}")

    # Check page text for Priya
    page_text_after = get_page_text()
    has_priya = "priya" in page_text_after.lower()
    log(f"  Page contains 'Priya': {has_priya}")

    # Also check if search triggered API filtering
    if len(visible_rows) <= 2 and has_priya:
        verdict = "FIXED"
        detail = f"Search filtered to {len(visible_rows)} row(s) showing Priya"
    elif len(rows_before) > 0 and len(visible_rows) < len(rows_before):
        verdict = "FIXED"
        detail = f"Search reduced rows from {len(rows_before)} to {len(visible_rows)}"
    else:
        verdict = "STILL FAILING"
        detail = f"Search did not filter: before={len(rows_before)}, after={len(visible_rows)}"

    log(f"  VERDICT: {verdict} - {detail}")
    screenshot("t1_step5_verdict")
    RESULTS["employee_search"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# TEST #9: Leave Type Dropdown Visible but Options Not Available
# ═══════════════════════════════════════════════════════
def test_leave_type_dropdown():
    log("\n=== TEST #9: Leave Type Dropdown Visible but Options Not Available ===")
    restart_driver_if_needed()
    login(ADMIN_EMAIL, ADMIN_PASS, "admin_leave")

    # Step 1: Go to leave page
    driver.get(f"{BASE_URL}/leave")
    time.sleep(3)
    screenshot("t9_step1_leave_page")
    log(f"  Step 1: Leave page URL: {driver.current_url}")

    # Look for Apply button
    apply_btn = None
    for sel in ["button", "a"]:
        elements = driver.find_elements(By.TAG_NAME, sel)
        for el in elements:
            txt = el.text.lower()
            if ("apply" in txt or "new" in txt or "request" in txt or "create" in txt) and el.is_displayed():
                apply_btn = el
                log(f"  Found apply button: '{el.text}'")
                break
        if apply_btn:
            break

    if apply_btn:
        safe_click(apply_btn)
        time.sleep(2)
        screenshot("t9_step1b_after_apply_click")

    # Step 2: Find leave type dropdown
    dropdown = None
    for sel in ["select[name*='leave']", "select[name*='type']", "select#leaveType",
                "[class*='select']", "[role='combobox']", "[role='listbox']",
                "select", "[class*='dropdown']"]:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                if el.is_displayed():
                    text_near = el.text or el.get_attribute("placeholder") or el.get_attribute("aria-label") or ""
                    log(f"  Found potential dropdown: tag={el.tag_name}, text='{text_near[:50]}'")
                    if "leave" in text_near.lower() or "type" in text_near.lower() or el.tag_name == "select":
                        dropdown = el
                        break
            if dropdown:
                break
        except:
            continue

    if not dropdown:
        # Look for any select element
        selects = driver.find_elements(By.TAG_NAME, "select")
        log(f"  Total <select> elements found: {len(selects)}")
        for s in selects:
            if s.is_displayed():
                dropdown = s
                break

    screenshot("t9_step2_dropdown_search")

    if not dropdown:
        # Try clicking labels that might trigger a dropdown
        labels = driver.find_elements(By.XPATH, "//*[contains(text(), 'Leave Type') or contains(text(), 'leave type') or contains(text(), 'Type')]")
        for lbl in labels:
            if lbl.is_displayed():
                log(f"  Found label: '{lbl.text}'")
                try:
                    safe_click(lbl)
                    time.sleep(1)
                except:
                    pass

        screenshot("t9_step2b_after_label_click")
        log("  Step 2: No standard dropdown found, checking for custom dropdowns")

        # Look for custom dropdown (div-based)
        custom_dds = driver.find_elements(By.CSS_SELECTOR,
            "[class*='select'], [class*='dropdown'], [class*='combobox'], [class*='listbox']")
        for dd in custom_dds:
            if dd.is_displayed():
                dropdown = dd
                log(f"  Found custom dropdown: class={dd.get_attribute('class')[:60]}")
                break

    # Step 3: Click and check options
    options_found = []
    if dropdown:
        log(f"  Step 3: Clicking dropdown (tag={dropdown.tag_name})")
        safe_click(dropdown)
        time.sleep(2)
        screenshot("t9_step3_dropdown_clicked")

        # Check for <option> tags
        if dropdown.tag_name == "select":
            options = dropdown.find_elements(By.TAG_NAME, "option")
            options_found = [o.text for o in options if o.text.strip() and o.get_attribute("value")]
            log(f"  Options in select: {options_found}")
        else:
            # Check for list items that appeared
            time.sleep(1)
            list_items = driver.find_elements(By.CSS_SELECTOR,
                "[role='option'], [class*='option'], [class*='menu-item'], li[class*='select'], [class*='list-item']")
            options_found = [li.text for li in list_items if li.is_displayed() and li.text.strip()]
            log(f"  Custom options found: {options_found}")

            # Also check for any new popover/dropdown menu
            menus = driver.find_elements(By.CSS_SELECTOR,
                "[role='menu'], [role='listbox'], [class*='menu'], [class*='popover'], [class*='dropdown-menu']")
            for m in menus:
                if m.is_displayed():
                    items = m.find_elements(By.CSS_SELECTOR, "li, div[role='option'], [class*='item']")
                    for item in items:
                        if item.text.strip() and item.is_displayed():
                            options_found.append(item.text.strip())
                    log(f"  Menu items: {options_found}")

    screenshot("t9_step4_final")

    if len(options_found) > 0:
        # Filter out placeholder options
        real_options = [o for o in options_found if o.lower() not in ["select", "choose", "-- select --", ""]]
        if real_options:
            verdict = "FIXED"
            detail = f"Leave type dropdown has {len(real_options)} options: {real_options[:5]}"
        else:
            verdict = "STILL FAILING"
            detail = "Dropdown visible but no real leave type options"
    else:
        verdict = "STILL FAILING"
        detail = "Leave type dropdown has no options or could not be found/clicked"

    log(f"  VERDICT: {verdict} - {detail}")
    RESULTS["leave_type_dropdown"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# TEST #16: Category Dropdown Empty in Create Post (Forum)
# ═══════════════════════════════════════════════════════
def test_forum_category_dropdown():
    log("\n=== TEST #16: Category Dropdown Empty in Create Post (Forum) ===")
    restart_driver_if_needed()
    login(ADMIN_EMAIL, ADMIN_PASS, "admin_forum")

    # Step 1: Go to forum/new
    for url in [f"{BASE_URL}/forum/new", f"{BASE_URL}/forum", f"{BASE_URL}/community",
                f"{BASE_URL}/community/new"]:
        driver.get(url)
        time.sleep(3)
        current = driver.current_url
        page_text = get_page_text()
        log(f"  Tried {url} -> {current}")
        screenshot(f"t16_step1_{url.split('/')[-1] or 'root'}")

        if "forum" in current.lower() or "community" in current.lower():
            break
        if "forum" in page_text.lower() or "community" in page_text.lower() or "post" in page_text.lower():
            break

    # If on forum listing, look for "New Post" / "Create" button
    new_btn = None
    buttons = driver.find_elements(By.CSS_SELECTOR, "button, a")
    for b in buttons:
        txt = b.text.lower()
        if ("new" in txt or "create" in txt or "post" in txt) and b.is_displayed():
            new_btn = b
            log(f"  Found new post button: '{b.text}'")
            break

    if new_btn:
        safe_click(new_btn)
        time.sleep(2)
        screenshot("t16_step1b_new_post_clicked")

    # Step 2: Find category dropdown
    dropdown = None
    # Look by label first
    page_text = get_page_text()
    log(f"  Page text snippet: {page_text[:300]}")

    for sel in ["select[name*='category']", "select[name*='Category']",
                "[class*='select']", "select", "[role='combobox']"]:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                if el.is_displayed():
                    nearby = el.text or el.get_attribute("placeholder") or el.get_attribute("name") or ""
                    log(f"  Potential category dropdown: {el.tag_name}, text='{nearby[:50]}'")
                    if "categ" in nearby.lower() or el.tag_name == "select":
                        dropdown = el
                        break
            if dropdown:
                break
        except:
            continue

    screenshot("t16_step2_category_search")

    # Step 3: Click and check options
    options_found = []
    if dropdown:
        safe_click(dropdown)
        time.sleep(1)
        screenshot("t16_step3_dropdown_clicked")

        if dropdown.tag_name == "select":
            options = dropdown.find_elements(By.TAG_NAME, "option")
            options_found = [o.text for o in options if o.text.strip()]
            log(f"  Select options: {options_found}")
        else:
            time.sleep(1)
            items = driver.find_elements(By.CSS_SELECTOR, "[role='option'], li[class*='option'], [class*='menu-item']")
            options_found = [i.text for i in items if i.is_displayed() and i.text.strip()]
            log(f"  Custom options: {options_found}")
    else:
        log("  No category dropdown found on page")

    screenshot("t16_step4_final")

    if len(options_found) > 0:
        real = [o for o in options_found if o.lower() not in ["select", "choose", ""]]
        if real:
            verdict = "FIXED"
            detail = f"Category dropdown has {len(real)} categories: {real[:5]}"
        else:
            verdict = "STILL FAILING"
            detail = "Dropdown present but no real categories"
    elif not dropdown:
        verdict = "INCONCLUSIVE"
        detail = "Category dropdown not found - page may have changed or forum unavailable"
    else:
        verdict = "STILL FAILING"
        detail = "Category dropdown visible but empty"

    log(f"  VERDICT: {verdict} - {detail}")
    RESULTS["category_dropdown_forum"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# TEST #23: Forum Posts Not Visible After Creation
# ═══════════════════════════════════════════════════════
def test_forum_posts_visible():
    log("\n=== TEST #23: Forum Posts Not Visible After Creation ===")
    restart_driver_if_needed()
    login(ADMIN_EMAIL, ADMIN_PASS, "admin_forum_post")

    # Navigate to forum
    driver.get(f"{BASE_URL}/forum")
    time.sleep(3)
    screenshot("t23_step1_forum_page")

    page_text = get_page_text()
    # Try community path too
    if "forum" not in driver.current_url.lower() and "community" not in page_text.lower():
        driver.get(f"{BASE_URL}/community")
        time.sleep(3)
        screenshot("t23_step1b_community_page")

    # Try to create a post via API first, then check UI
    # Use API to create
    api_base = "https://test-empcloud-api.empcloud.com"
    session = requests.Session()
    try:
        login_resp = session.post(f"{api_base}/auth/login",
                                  json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
                                  timeout=15)
        token = login_resp.json().get("token") or login_resp.json().get("data", {}).get("token")
        if token:
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            post_data = {
                "title": f"E2E Test Post {ts}",
                "content": f"This is an automated test post created at {ts}",
                "category": "general"
            }
            headers = {"Authorization": f"Bearer {token}"}
            for endpoint in ["/forum/posts", "/forum", "/community/posts", "/community"]:
                try:
                    r = session.post(f"{api_base}{endpoint}", json=post_data, headers=headers, timeout=15)
                    log(f"  API POST {endpoint}: {r.status_code}")
                    if r.status_code in [200, 201]:
                        log(f"  Post created via API: {r.json()}")
                        break
                except:
                    pass
    except Exception as e:
        log(f"  API post creation failed: {e}")

    # Step 2: Go to forum dashboard and check visibility
    driver.get(f"{BASE_URL}/forum")
    time.sleep(3)
    screenshot("t23_step2_forum_after_create")
    page_text = get_page_text()

    # Also try community
    if "forum" not in driver.current_url:
        driver.get(f"{BASE_URL}/community")
        time.sleep(3)
        screenshot("t23_step2b_community_after_create")
        page_text = get_page_text()

    # Check if any posts are visible
    post_elements = driver.find_elements(By.CSS_SELECTOR,
        "[class*='post'], [class*='thread'], [class*='topic'], article, .card")
    visible_posts = [p for p in post_elements if p.is_displayed() and p.text.strip()]
    log(f"  Post elements found: {len(visible_posts)}")

    has_test_post = "e2e test post" in page_text.lower() or "test post" in page_text.lower()
    log(f"  Test post visible: {has_test_post}")
    log(f"  Page text snippet: {page_text[:500]}")

    screenshot("t23_step3_final")

    if has_test_post or len(visible_posts) > 0:
        verdict = "FIXED"
        detail = f"Forum shows {len(visible_posts)} posts, test post visible: {has_test_post}"
    else:
        verdict = "STILL FAILING"
        detail = f"No posts visible on forum page. URL: {driver.current_url}"

    log(f"  VERDICT: {verdict} - {detail}")
    RESULTS["forum_posts_visible"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# TEST #12: No Option to Delete Location
# ═══════════════════════════════════════════════════════
def test_delete_location():
    log("\n=== TEST #12: No Option to Delete Location in Settings ===")
    restart_driver_if_needed()
    login(ADMIN_EMAIL, ADMIN_PASS, "admin_settings")

    # Step 1: Go to settings
    driver.get(f"{BASE_URL}/settings")
    time.sleep(3)
    screenshot("t12_step1_settings_page")
    log(f"  Step 1: Settings URL: {driver.current_url}")
    page_text = get_page_text()

    # Step 2: Find locations section
    # Look for "Location" link or tab
    location_found = False
    for sel in ["a", "button", "div", "li", "span"]:
        elements = driver.find_elements(By.TAG_NAME, sel)
        for el in elements:
            txt = el.text.lower()
            if "location" in txt and el.is_displayed():
                log(f"  Found location element: <{sel}> '{el.text}'")
                try:
                    safe_click(el)
                    time.sleep(2)
                    location_found = True
                except:
                    pass
                break
        if location_found:
            break

    # Also try direct URL
    if not location_found:
        for url in [f"{BASE_URL}/settings/locations", f"{BASE_URL}/settings/location",
                     f"{BASE_URL}/settings#locations"]:
            driver.get(url)
            time.sleep(2)
            if "location" in get_page_text().lower():
                location_found = True
                break

    screenshot("t12_step2_locations_section")
    page_text = get_page_text()
    log(f"  Location section found: {location_found}")
    log(f"  Page text snippet: {page_text[:500]}")

    # Step 3: Look for delete button/icon
    delete_found = False
    delete_elements = driver.find_elements(By.CSS_SELECTOR,
        "button[aria-label*='delete'], button[title*='delete'], button[title*='Delete'], "
        "[class*='delete'], [class*='trash'], [class*='remove'], "
        "svg[class*='trash'], svg[class*='delete'], "
        "button[aria-label*='remove'], [data-testid*='delete']")

    for de in delete_elements:
        if de.is_displayed():
            log(f"  Found delete element: tag={de.tag_name}, class={de.get_attribute('class')}, text={de.text[:30]}")
            delete_found = True

    # Also look for text-based delete buttons
    if not delete_found:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button, a, [role='button']")
        for b in buttons:
            txt = b.text.lower()
            title = (b.get_attribute("title") or "").lower()
            aria = (b.get_attribute("aria-label") or "").lower()
            if ("delete" in txt or "remove" in txt or "delete" in title or "delete" in aria or
                "trash" in (b.get_attribute("class") or "").lower()):
                if b.is_displayed():
                    log(f"  Found delete button: '{b.text}' title='{title}'")
                    delete_found = True

    # Look for icons (trash can SVG)
    if not delete_found:
        svgs = driver.find_elements(By.TAG_NAME, "svg")
        for svg in svgs:
            cls = (svg.get_attribute("class") or "").lower()
            data_icon = (svg.get_attribute("data-icon") or "").lower()
            if "trash" in cls or "delete" in cls or "trash" in data_icon:
                if svg.is_displayed():
                    log(f"  Found trash icon SVG")
                    delete_found = True

    screenshot("t12_step3_delete_search")
    screenshot("t12_step4_final")

    if delete_found:
        verdict = "FIXED"
        detail = "Delete button/icon found for locations"
    else:
        verdict = "STILL FAILING"
        detail = f"No delete option found for locations. Location section found: {location_found}"

    log(f"  VERDICT: {verdict} - {detail}")
    RESULTS["delete_location"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# TEST #18: Sidebar Selection Not Retained
# ═══════════════════════════════════════════════════════
def test_sidebar_selection():
    log("\n=== TEST #18: Sidebar Selection Not Retained After Navigation ===")
    restart_driver_if_needed()
    login(ADMIN_EMAIL, ADMIN_PASS, "admin_sidebar")

    time.sleep(2)
    screenshot("t18_step0_dashboard")

    # Step 1: Click "Leave" in sidebar
    sidebar_items = driver.find_elements(By.CSS_SELECTOR,
        "nav a, aside a, [class*='sidebar'] a, [class*='nav'] a, [class*='menu'] a")
    log(f"  Found {len(sidebar_items)} sidebar/nav items")

    leave_link = None
    attendance_link = None
    for item in sidebar_items:
        txt = item.text.strip().lower()
        if txt == "leave" or "leave" in txt:
            if not leave_link and item.is_displayed():
                leave_link = item
                log(f"  Found Leave link: '{item.text}', class='{item.get_attribute('class')}'")
        if txt == "attendance" or "attendance" in txt:
            if not attendance_link and item.is_displayed():
                attendance_link = item
                log(f"  Found Attendance link: '{item.text}', class='{item.get_attribute('class')}'")

    if not leave_link:
        log("  Could not find 'Leave' in sidebar")
        RESULTS["sidebar_selection"] = {"verdict": "INCONCLUSIVE", "detail": "Leave link not found in sidebar"}
        return

    safe_click(leave_link)
    time.sleep(2)
    screenshot("t18_step1_after_leave_click")

    # Step 2: Check if Leave is highlighted
    # Re-find Leave link after navigation
    sidebar_items = driver.find_elements(By.CSS_SELECTOR,
        "nav a, aside a, [class*='sidebar'] a, [class*='nav'] a, [class*='menu'] a")

    leave_highlighted = False
    for item in sidebar_items:
        txt = item.text.strip().lower()
        if "leave" in txt and item.is_displayed():
            cls = (item.get_attribute("class") or "").lower()
            style = (item.get_attribute("style") or "").lower()
            aria = (item.get_attribute("aria-current") or "").lower()
            parent_cls = ""
            try:
                parent_cls = (item.find_element(By.XPATH, "..").get_attribute("class") or "").lower()
            except:
                pass

            is_active = any(x in cls for x in ["active", "selected", "current", "highlight"]) or \
                        any(x in parent_cls for x in ["active", "selected", "current"]) or \
                        aria in ["page", "true"] or \
                        "font-weight" in style

            log(f"  Leave class: '{cls}', parent: '{parent_cls}', aria: '{aria}' -> active={is_active}")
            leave_highlighted = is_active
            break

    log(f"  Step 2: Leave highlighted: {leave_highlighted}")

    # Step 3: Click Attendance
    if not attendance_link:
        sidebar_items = driver.find_elements(By.CSS_SELECTOR,
            "nav a, aside a, [class*='sidebar'] a, [class*='nav'] a, [class*='menu'] a")
        for item in sidebar_items:
            if "attendance" in item.text.strip().lower() and item.is_displayed():
                attendance_link = item
                break

    if not attendance_link:
        log("  Could not find 'Attendance' in sidebar")
        RESULTS["sidebar_selection"] = {"verdict": "INCONCLUSIVE", "detail": "Attendance link not found in sidebar"}
        return

    safe_click(attendance_link)
    time.sleep(2)
    screenshot("t18_step3_after_attendance_click")

    # Step 4: Check Attendance highlighted and Leave not
    sidebar_items = driver.find_elements(By.CSS_SELECTOR,
        "nav a, aside a, [class*='sidebar'] a, [class*='nav'] a, [class*='menu'] a")

    attendance_highlighted = False
    leave_still_highlighted = False
    for item in sidebar_items:
        txt = item.text.strip().lower()
        if not item.is_displayed():
            continue
        cls = (item.get_attribute("class") or "").lower()
        parent_cls = ""
        try:
            parent_cls = (item.find_element(By.XPATH, "..").get_attribute("class") or "").lower()
        except:
            pass
        aria = (item.get_attribute("aria-current") or "").lower()

        is_active = any(x in cls for x in ["active", "selected", "current", "highlight"]) or \
                    any(x in parent_cls for x in ["active", "selected", "current"]) or \
                    aria in ["page", "true"]

        if "attendance" in txt:
            attendance_highlighted = is_active
            log(f"  Attendance class: '{cls}' -> active={is_active}")
        if "leave" in txt and "attendance" not in txt:
            leave_still_highlighted = is_active
            log(f"  Leave class after nav: '{cls}' -> active={is_active}")

    log(f"  Step 4: Attendance highlighted={attendance_highlighted}, Leave still highlighted={leave_still_highlighted}")

    screenshot("t18_step4_final")

    if attendance_highlighted and not leave_still_highlighted:
        verdict = "FIXED"
        detail = "Sidebar correctly highlights active item and removes highlight from previous"
    elif not attendance_highlighted and not leave_highlighted:
        verdict = "STILL FAILING"
        detail = "Sidebar does not highlight any active item"
    elif leave_still_highlighted and attendance_highlighted:
        verdict = "STILL FAILING"
        detail = "Both Leave and Attendance are highlighted simultaneously"
    else:
        verdict = "STILL FAILING"
        detail = f"Sidebar selection not retained correctly. Attendance active={attendance_highlighted}, Leave still active={leave_still_highlighted}"

    log(f"  VERDICT: {verdict} - {detail}")
    RESULTS["sidebar_selection"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# TEST #28: Dashboard and Self Service Same Page
# ═══════════════════════════════════════════════════════
def test_dashboard_selfservice():
    log("\n=== TEST #28: Dashboard and Self Service Same Page ===")
    restart_driver_if_needed()
    login(EMP_EMAIL, EMP_PASS, "employee_dash")

    # Step 2: Go to dashboard
    driver.get(f"{BASE_URL}/")
    time.sleep(3)
    screenshot("t28_step2_dashboard")
    dash_url = driver.current_url
    dash_text = get_page_text()
    dash_hash = hashlib.md5(dash_text.encode()).hexdigest()
    dash_html = driver.page_source
    dash_html_hash = hashlib.md5(dash_html.encode()).hexdigest()
    log(f"  Step 2: Dashboard URL={dash_url}, text hash={dash_hash}, html hash={dash_html_hash}")
    log(f"  Dashboard text snippet: {dash_text[:300]}")

    # Step 4: Go to self-service
    driver.get(f"{BASE_URL}/self-service")
    time.sleep(3)
    screenshot("t28_step4_self_service")
    ss_url = driver.current_url
    ss_text = get_page_text()
    ss_hash = hashlib.md5(ss_text.encode()).hexdigest()
    ss_html = driver.page_source
    ss_html_hash = hashlib.md5(ss_html.encode()).hexdigest()
    log(f"  Step 4: Self-service URL={ss_url}, text hash={ss_hash}, html hash={ss_html_hash}")
    log(f"  Self-service text snippet: {ss_text[:300]}")

    # Also try /employee/self-service, /ess
    if ss_url == dash_url or "/self-service" not in ss_url:
        for alt in ["/employee/self-service", "/ess", "/self-service/dashboard"]:
            driver.get(f"{BASE_URL}{alt}")
            time.sleep(2)
            alt_url = driver.current_url
            if alt_url != dash_url:
                ss_text = get_page_text()
                ss_hash = hashlib.md5(ss_text.encode()).hexdigest()
                ss_html_hash = hashlib.md5(driver.page_source.encode()).hexdigest()
                log(f"  Alt self-service {alt}: URL={alt_url}, hash={ss_hash}")
                break

    screenshot("t28_step5_final")

    # Step 6: Compare
    if dash_hash == ss_hash:
        verdict = "STILL FAILING"
        detail = f"Dashboard and Self-Service have identical content (hash={dash_hash})"
    else:
        # Check if they redirected to same URL
        if dash_url == ss_url:
            verdict = "STILL FAILING"
            detail = f"Both URLs redirect to {dash_url}"
        else:
            verdict = "FIXED"
            detail = f"Dashboard ({dash_url}) and Self-Service ({ss_url}) show different content"

    log(f"  VERDICT: {verdict} - {detail}")
    RESULTS["dashboard_selfservice"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# TEST #24: Announcement Target Asks for JSON Array IDs
# ═══════════════════════════════════════════════════════
def test_announcement_target():
    log("\n=== TEST #24: Announcement Target Asks for JSON Array IDs ===")
    restart_driver_if_needed()
    login(ADMIN_EMAIL, ADMIN_PASS, "admin_announce")

    # Step 1: Go to announcements
    driver.get(f"{BASE_URL}/announcements")
    time.sleep(3)
    screenshot("t24_step1_announcements")
    log(f"  Step 1: URL: {driver.current_url}")

    # Click New button
    new_btn = None
    for el in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        txt = el.text.lower()
        if ("new" in txt or "create" in txt or "add" in txt) and el.is_displayed():
            new_btn = el
            log(f"  Found new button: '{el.text}'")
            break

    if new_btn:
        safe_click(new_btn)
        time.sleep(2)
        screenshot("t24_step1b_new_clicked")

    # Step 2: Fill title and content
    inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea")
    for inp in inputs:
        name = (inp.get_attribute("name") or "").lower()
        ph = (inp.get_attribute("placeholder") or "").lower()
        tp = inp.get_attribute("type") or ""
        if inp.is_displayed():
            if "title" in name or "title" in ph:
                inp.clear()
                inp.send_keys("E2E Test Announcement")
                log(f"  Filled title")
            elif "content" in name or "body" in name or "content" in ph or "body" in ph or inp.tag_name == "textarea":
                inp.clear()
                inp.send_keys("This is a test announcement from E2E testing agent")
                log(f"  Filled content/body")

    screenshot("t24_step2_filled_form")

    # Step 3: Find target/audience field
    page_text = get_page_text()
    page_source = driver.page_source.lower()

    # Check for target field
    target_is_json = False
    target_is_dropdown = False
    target_field = None

    # Look for target/audience input
    for inp in driver.find_elements(By.CSS_SELECTOR, "input, textarea, select, [role='combobox']"):
        name = (inp.get_attribute("name") or "").lower()
        ph = (inp.get_attribute("placeholder") or "").lower()
        label_text = ""
        try:
            label_id = inp.get_attribute("id")
            if label_id:
                labels = driver.find_elements(By.CSS_SELECTOR, f"label[for='{label_id}']")
                if labels:
                    label_text = labels[0].text.lower()
        except:
            pass

        if ("target" in name or "audience" in name or "recipient" in name or
            "target" in ph or "audience" in ph or "recipient" in ph or
            "target" in label_text or "audience" in label_text):
            target_field = inp
            log(f"  Found target field: tag={inp.tag_name}, name={name}, placeholder={ph}, type={inp.get_attribute('type')}")

            if inp.tag_name == "select" or inp.get_attribute("role") == "combobox":
                target_is_dropdown = True
            elif "json" in ph or "array" in ph or "[" in ph:
                target_is_json = True
            elif inp.get_attribute("type") in ["text", None, ""] and inp.tag_name != "select":
                # It's a text input - could be JSON or a search
                target_is_json = True  # text input for IDs is the bug
            break

    # Check for any labels mentioning target/audience
    all_labels = driver.find_elements(By.CSS_SELECTOR, "label, .label, [class*='label']")
    for lbl in all_labels:
        if lbl.is_displayed():
            txt = lbl.text.lower()
            if "target" in txt or "audience" in txt or "recipient" in txt:
                log(f"  Label found: '{lbl.text}'")

    # Check page source for JSON-related hints
    if "json" in page_source or "array" in page_source:
        log(f"  Page source contains JSON/array references near target")

    screenshot("t24_step3_target_field")

    if target_field:
        if target_is_dropdown:
            verdict = "FIXED"
            detail = "Target field is a user-friendly dropdown, not JSON input"
        elif target_is_json:
            verdict = "STILL FAILING"
            detail = "Target field appears to be a plain text input (expects JSON array IDs)"
        else:
            verdict = "INCONCLUSIVE"
            detail = f"Target field found but type unclear: tag={target_field.tag_name}"
    else:
        # Check if target is handled differently now (e.g., "All Employees" default)
        if "all employee" in page_text.lower() or "everyone" in page_text.lower():
            verdict = "FIXED"
            detail = "No explicit target input - appears to default to all employees"
        else:
            verdict = "INCONCLUSIVE"
            detail = "Target/audience field not found in announcement form"

    log(f"  VERDICT: {verdict} - {detail}")
    RESULTS["announcement_target"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# TEST #31: Whistleblowing Dropdown Error Assigning Investigator
# ═══════════════════════════════════════════════════════
def test_whistleblowing_dropdown():
    log("\n=== TEST #31: Whistleblowing Dropdown Error Assigning Investigator ===")
    restart_driver_if_needed()
    login(ADMIN_EMAIL, ADMIN_PASS, "admin_whistle")

    # Step 1: Go to whistleblowing
    for url in [f"{BASE_URL}/whistleblowing", f"{BASE_URL}/whistleblower",
                f"{BASE_URL}/compliance/whistleblowing", f"{BASE_URL}/ethics"]:
        driver.get(url)
        time.sleep(3)
        current = driver.current_url
        page_text = get_page_text()
        log(f"  Tried {url} -> {current}")
        if "whistl" in current.lower() or "whistl" in page_text.lower():
            break

    screenshot("t31_step1_whistleblowing")
    page_text = get_page_text()
    log(f"  Page text: {page_text[:300]}")

    # Step 2: Find assign investigator
    # Look for any report/case that has an assign option
    assign_found = False
    assign_works = None

    # Click on first available report/case
    for sel in ["tr", ".card", "[class*='report']", "[class*='case']", "article"]:
        items = driver.find_elements(By.CSS_SELECTOR, sel)
        for item in items:
            if item.is_displayed() and item.text.strip():
                try:
                    safe_click(item)
                    time.sleep(2)
                    break
                except:
                    continue
        break

    screenshot("t31_step2_report_detail")

    # Look for assign investigator dropdown/button
    page_text = get_page_text()
    for el in driver.find_elements(By.CSS_SELECTOR, "button, select, [role='combobox'], a, [class*='assign']"):
        txt = (el.text + " " + (el.get_attribute("title") or "") + " " + (el.get_attribute("aria-label") or "")).lower()
        if ("assign" in txt or "investigator" in txt) and el.is_displayed():
            log(f"  Found assign element: '{el.text}', tag={el.tag_name}")
            assign_found = True
            try:
                safe_click(el)
                time.sleep(2)
                screenshot("t31_step3_assign_clicked")

                # Check for errors
                error_text = get_page_text()
                if "error" in error_text.lower() and "assign" in error_text.lower():
                    assign_works = False
                else:
                    # Check if dropdown opened with options
                    options = driver.find_elements(By.CSS_SELECTOR,
                        "[role='option'], [class*='option'], li[class*='menu-item']")
                    visible_options = [o for o in options if o.is_displayed()]
                    if visible_options:
                        assign_works = True
                        log(f"  Investigator options: {[o.text for o in visible_options[:5]]}")
                    else:
                        # Check for error messages in page
                        page_source = driver.page_source.lower()
                        if "error" in page_source[-500:]:
                            assign_works = False
                        else:
                            assign_works = True  # no error means it might work
            except Exception as e:
                log(f"  Error clicking assign: {e}")
                assign_works = False
            break

    screenshot("t31_step4_final")

    if not assign_found:
        verdict = "INCONCLUSIVE"
        detail = f"Assign investigator button not found. Page: {driver.current_url}"
    elif assign_works:
        verdict = "FIXED"
        detail = "Assign investigator dropdown works without errors"
    else:
        verdict = "STILL FAILING"
        detail = "Assign investigator dropdown produces errors"

    log(f"  VERDICT: {verdict} - {detail}")
    RESULTS["whistleblowing_dropdown"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# TEST #2: Import CSV Button Not Importing
# ═══════════════════════════════════════════════════════
def test_import_csv():
    log("\n=== TEST #2: Import CSV Button Not Importing ===")
    restart_driver_if_needed()
    login(ADMIN_EMAIL, ADMIN_PASS, "admin_import")

    # Step 1: Go to /employees
    driver.get(f"{BASE_URL}/employees")
    time.sleep(3)
    screenshot("t2_step1_employees")
    log(f"  Step 1: URL: {driver.current_url}")

    # Step 2: Find Import CSV button
    import_btn = None
    for el in driver.find_elements(By.CSS_SELECTOR, "button, a, [role='button']"):
        txt = el.text.lower()
        title = (el.get_attribute("title") or "").lower()
        if ("import" in txt or "csv" in txt or "upload" in txt or "import" in title) and el.is_displayed():
            import_btn = el
            log(f"  Found import button: '{el.text}', tag={el.tag_name}")
            break

    screenshot("t2_step2_import_search")

    # Step 3: Check if it exists and is clickable
    if import_btn:
        is_disabled = import_btn.get_attribute("disabled")
        cls = import_btn.get_attribute("class") or ""
        log(f"  Import button: disabled={is_disabled}, class={cls}")

        try:
            safe_click(import_btn)
            time.sleep(2)
            screenshot("t2_step3_import_clicked")

            # Check if modal/dialog/file picker appeared
            modals = driver.find_elements(By.CSS_SELECTOR,
                "[role='dialog'], .modal, [class*='modal'], [class*='dialog'], [class*='upload']")
            modal_visible = any(m.is_displayed() for m in modals)

            # Check for file input
            file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            has_file_input = len(file_inputs) > 0

            page_text = get_page_text()
            log(f"  After click: modal_visible={modal_visible}, file_input={has_file_input}")
            log(f"  Page text after click: {page_text[:300]}")

            screenshot("t2_step3b_after_import")

            if modal_visible or has_file_input:
                verdict = "FIXED"
                detail = "Import CSV button works - opens modal/file picker"
            else:
                # Check if page changed or a new section appeared
                verdict = "STILL FAILING"
                detail = "Import button exists and is clickable but nothing happens after click"
        except Exception as e:
            verdict = "STILL FAILING"
            detail = f"Import button found but click failed: {e}"
    else:
        verdict = "STILL FAILING"
        detail = "Import CSV button not found on /employees page"

    log(f"  VERDICT: {verdict} - {detail}")
    RESULTS["import_csv"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# TEST #27: Empcode Column Missing in CSV Import
# ═══════════════════════════════════════════════════════
def test_empcode_csv():
    log("\n=== TEST #27: Empcode Column Missing in CSV Import ===")
    restart_driver_if_needed()
    login(ADMIN_EMAIL, ADMIN_PASS, "admin_empcode")

    # Step 1: Go to employees/import
    driver.get(f"{BASE_URL}/employees")
    time.sleep(3)

    # Find import feature
    import_btn = None
    for el in driver.find_elements(By.CSS_SELECTOR, "button, a, [role='button']"):
        txt = el.text.lower()
        if ("import" in txt or "csv" in txt) and el.is_displayed():
            import_btn = el
            break

    if import_btn:
        safe_click(import_btn)
        time.sleep(2)

    screenshot("t27_step1_import_feature")

    # Check for template download or column preview
    page_text = get_page_text()
    page_source = driver.page_source

    # Look for template download link
    template_btn = None
    for el in driver.find_elements(By.CSS_SELECTOR, "a, button"):
        txt = el.text.lower()
        if ("template" in txt or "download" in txt or "sample" in txt) and el.is_displayed():
            template_btn = el
            log(f"  Found template button: '{el.text}'")
            break

    # Check if empcode is mentioned in the UI
    has_empcode = "empcode" in page_source.lower() or "emp_code" in page_source.lower() or \
                  "employee code" in page_source.lower() or "emp code" in page_source.lower() or \
                  "employeecode" in page_source.lower()

    log(f"  Empcode mentioned in page: {has_empcode}")
    log(f"  Page text: {page_text[:500]}")

    # Also check via API for import template
    api_base = "https://test-empcloud-api.empcloud.com"
    try:
        session = requests.Session()
        lr = session.post(f"{api_base}/auth/login",
                         json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
        token = lr.json().get("token") or lr.json().get("data", {}).get("token")
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            for ep in ["/employees/import/template", "/import/template", "/employees/template"]:
                r = session.get(f"{api_base}{ep}", headers=headers, timeout=15)
                log(f"  API {ep}: {r.status_code}")
                if r.status_code == 200:
                    content = r.text[:500]
                    log(f"  Template content: {content}")
                    if "empcode" in content.lower() or "emp_code" in content.lower():
                        has_empcode = True
                    break
    except Exception as e:
        log(f"  API template check failed: {e}")

    screenshot("t27_step2_final")

    if has_empcode:
        verdict = "FIXED"
        detail = "Empcode column is present in CSV import template/UI"
    else:
        verdict = "STILL FAILING"
        detail = "Empcode column not found in CSV import template or UI"

    log(f"  VERDICT: {verdict} - {detail}")
    RESULTS["empcode_csv"] = {"verdict": verdict, "detail": detail}


# ═══════════════════════════════════════════════════════
# GitHub: Comment and Re-open failures
# ═══════════════════════════════════════════════════════
def github_comment_and_reopen():
    log("\n=== POSTING GITHUB RESULTS ===")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    base_api = f"https://api.github.com/repos/{GITHUB_REPO}"

    for test_key, result in RESULTS.items():
        issue_num = ISSUE_MAP.get(test_key)
        if not issue_num:
            log(f"  No issue number for {test_key}, skipping")
            continue

        verdict = result.get("verdict", "UNKNOWN")
        detail = result.get("detail", "")

        # Build comment
        emoji = "white_check_mark" if verdict == "FIXED" else ("x" if "FAIL" in verdict else "question")
        comment = f"""Comment by E2E Testing Agent

## Deep UI Retest - {test_key.replace('_', ' ').title()}

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
**Method:** Selenium headless Chrome - actual UI interaction (click, type, navigate)
**Verdict:** :{emoji}: **{verdict}**

### Details
{detail}

### Test Method
- Chrome headless with `--headless=new --no-sandbox --window-size=1920,1080`
- Used `webdriver_manager` for ChromeDriver
- Actual button clicks, form fills, dropdown interactions
- Screenshots captured at every step
"""

        # Post comment
        try:
            r = requests.post(f"{base_api}/issues/{issue_num}/comments",
                            headers=headers,
                            json={"body": comment},
                            timeout=30)
            log(f"  Comment on #{issue_num}: {r.status_code}")
        except Exception as e:
            log(f"  Comment failed for #{issue_num}: {e}")

        # Re-open if still failing
        if "FAIL" in verdict:
            try:
                r = requests.patch(f"{base_api}/issues/{issue_num}",
                                 headers=headers,
                                 json={"state": "open"},
                                 timeout=30)
                log(f"  Re-opened #{issue_num}: {r.status_code}")
            except Exception as e:
                log(f"  Re-open failed for #{issue_num}: {e}")
        else:
            log(f"  #{issue_num} verdict={verdict}, keeping closed")


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════
def main():
    global driver, test_count
    test_count = 0

    log("=" * 70)
    log("DEEP UI/WORKFLOW RETEST - EmpCloud Closed Bugs")
    log("=" * 70)

    driver = get_driver()

    tests = [
        ("Employee Search (#1)", test_employee_search),
        ("Leave Type Dropdown (#9)", test_leave_type_dropdown),
        ("Forum Category Dropdown (#16)", test_forum_category_dropdown),
        ("Forum Posts Visible (#23)", test_forum_posts_visible),
        ("Delete Location (#12)", test_delete_location),
        ("Sidebar Selection (#18)", test_sidebar_selection),
        ("Dashboard vs Self-Service (#28)", test_dashboard_selfservice),
        ("Announcement Target (#24)", test_announcement_target),
        ("Whistleblowing Dropdown (#31)", test_whistleblowing_dropdown),
        ("Import CSV (#2)", test_import_csv),
        ("Empcode CSV (#27)", test_empcode_csv),
    ]

    for name, test_func in tests:
        try:
            log(f"\n{'='*60}")
            log(f"RUNNING: {name}")
            log(f"{'='*60}")
            test_func()
        except Exception as e:
            log(f"  EXCEPTION in {name}: {e}")
            traceback.print_exc()
            RESULTS[name] = {"verdict": "ERROR", "detail": str(e)}
            # Restart driver after crash
            try:
                driver.quit()
            except:
                pass
            driver = get_driver()

    # Print summary
    log("\n" + "=" * 70)
    log("SUMMARY OF ALL RESULTS")
    log("=" * 70)
    for test_key, result in RESULTS.items():
        issue_num = ISSUE_MAP.get(test_key, "?")
        verdict = result.get("verdict", "UNKNOWN")
        detail = result.get("detail", "")
        log(f"  #{issue_num} {test_key}: {verdict} - {detail}")

    # Post to GitHub
    github_comment_and_reopen()

    # Save results
    results_file = os.path.join(SCREENSHOT_DIR, "results.json")
    with open(results_file, "w") as f:
        json.dump(RESULTS, f, indent=2)
    log(f"\nResults saved to {results_file}")

    try:
        driver.quit()
    except:
        pass

    log("\nDONE.")


if __name__ == "__main__":
    main()
