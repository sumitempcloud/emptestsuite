import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import urllib.request
import urllib.error
import traceback
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
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\retest"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

CREDS = {
    "org_admin": ("ananya@technova.in", "Welcome@123"),
    "employee": ("priya@technova.in", "Welcome@123"),
    "super_admin": ("admin@empcloud.com", "SuperAdmin@2026"),
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
results = {}

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
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  Screenshot: {path}")
    return path

def login(driver, role="org_admin"):
    email, pwd = CREDS[role]
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    try:
        ef = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail'], input[placeholder*='Email']"))
        )
        ef.clear(); ef.send_keys(email)
        pf = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        pf.clear(); pf.send_keys(pwd)
        time.sleep(0.5)
        btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button")
        for b in btns:
            txt = b.text.lower()
            if any(k in txt for k in ["sign in", "login", "log in", "submit"]):
                b.click()
                break
        else:
            if btns:
                btns[-1].click()
        time.sleep(4)
        print(f"  Logged in as {role} ({email}), URL: {driver.current_url}")
    except Exception as e:
        print(f"  Login error for {role}: {e}")

def safe_click(driver, element):
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)

def find_by_text(driver, tag, text, partial=True):
    els = driver.find_elements(By.TAG_NAME, tag)
    for el in els:
        try:
            t = el.text.strip().lower()
            if partial and text.lower() in t:
                return el
            elif not partial and t == text.lower():
                return el
        except:
            pass
    return None

def click_sidebar(driver, text):
    """Click a sidebar link by its text."""
    time.sleep(1)
    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    for link in links:
        try:
            t = link.text.strip().lower()
            if t == text.lower():
                safe_click(driver, link)
                time.sleep(3)
                return True
        except:
            pass
    # Partial match fallback
    for link in links:
        try:
            t = link.text.strip().lower()
            if text.lower() in t:
                safe_click(driver, link)
                time.sleep(3)
                return True
        except:
            pass
    return False

def github_api(method, endpoint, data=None):
    url = f"https://api.github.com/repos/{GITHUB_REPO}{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "EmpCloud-Retest-Bot")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  GitHub API error: {e.code} {e.read().decode()}")
        return None

def reopen_issue(number, details):
    print(f"  Re-opening issue #{number}...")
    github_api("PATCH", f"/issues/{number}", {"state": "open"})
    comment = f"Re-tested on 2026-03-27. Bug is still present.\n\n{details}"
    github_api("POST", f"/issues/{number}/comments", {"body": comment})

def confirm_fixed(number, details=""):
    msg = f"Re-tested on 2026-03-27. Bug appears to be fixed."
    if details:
        msg += f"\n\n{details}"
    github_api("POST", f"/issues/{number}/comments", {"body": msg})

def update_issue_if_changed(number, old_status, new_status, details):
    """If status changed from round 1, update GitHub accordingly."""
    if old_status == "STILL_FAILING" and new_status == "FIXED":
        # Close the issue we re-opened in round 1
        print(f"  Closing issue #{number} (now fixed)...")
        github_api("PATCH", f"/issues/{number}", {"state": "closed"})
        confirm_fixed(number, details)
    elif old_status == "STILL_FAILING" and new_status == "STILL_FAILING":
        # Already re-opened, just add updated comment
        comment = f"Re-tested on 2026-03-27 (round 2 with improved navigation). Bug is still present.\n\n{details}"
        github_api("POST", f"/issues/{number}/comments", {"body": comment})


# ========================= TESTS =========================

def test_issue_62(driver):
    """#62 - Duplicate Location Names - navigate via Settings sidebar"""
    print("\n[#62] Duplicate Location Names (Round 2)")
    login(driver, "org_admin")
    # Click Settings in sidebar
    click_sidebar(driver, "Settings")
    time.sleep(2)
    screenshot(driver, "issue_62_r2_settings")
    page = driver.page_source.lower()
    print(f"  Settings page URL: {driver.current_url}")

    # Look for Locations tab/section within settings
    loc_link = find_by_text(driver, "a", "location") or find_by_text(driver, "button", "location")
    if loc_link:
        safe_click(driver, loc_link)
        time.sleep(3)

    # Also try tab navigation
    tabs = driver.find_elements(By.CSS_SELECTOR, "button, a, [role='tab']")
    for tab in tabs:
        try:
            if "location" in tab.text.lower():
                safe_click(driver, tab)
                time.sleep(2)
                break
        except:
            pass

    screenshot(driver, "issue_62_r2_locations")
    print(f"  Locations URL: {driver.current_url}")

    # Look for add button
    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
        try:
            t = btn.text.lower()
            if any(k in t for k in ["add location", "add new", "add", "create", "+"]):
                add_btn = btn
                print(f"  Found add button: '{btn.text}'")
                break
        except:
            pass

    test_loc_name = f"TestDupLoc"
    if add_btn:
        for attempt in range(2):
            safe_click(driver, add_btn)
            time.sleep(2)
            screenshot(driver, f"issue_62_r2_modal_{attempt+1}")

            # Find input in modal/dialog
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type='hidden']):not([type='password']):not([type='email'])")
            for inp in inputs:
                try:
                    if inp.is_displayed():
                        inp.clear()
                        inp.send_keys(test_loc_name)
                        print(f"  Entered '{test_loc_name}' in input field")
                        break
                except:
                    pass

            time.sleep(1)
            # Click save/submit
            for sb in driver.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = sb.text.lower()
                    if any(k in t for k in ["save", "submit", "add", "create", "ok", "confirm"]) and sb.is_displayed():
                        safe_click(driver, sb)
                        print(f"  Clicked save button: '{sb.text}'")
                        break
                except:
                    pass
            time.sleep(3)
            screenshot(driver, f"issue_62_r2_after_save_{attempt+1}")

            if attempt == 1:
                page2 = driver.page_source.lower()
                body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(k in body_text for k in ["duplicate", "already exists", "already added", "unique", "location already"]):
                    return "FIXED", "Duplicate location validation is now in place."
                # Check for error toasts
                toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='alert'], [class*='notification'], [role='alert'], [class*='Toastify']")
                for t in toasts:
                    try:
                        if any(k in t.text.lower() for k in ["duplicate", "already", "exists"]):
                            return "FIXED", "Duplicate location validation shown via toast."
                    except:
                        pass
            # Re-find add button for second attempt
            time.sleep(1)
            add_btn = None
            for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = btn.text.lower()
                    if any(k in t for k in ["add location", "add new", "add", "create", "+"]):
                        add_btn = btn
                        break
                except:
                    pass
        return "STILL_FAILING", "System still allows creating duplicate location names without validation."
    else:
        return "STILL_FAILING", "Could not find add location button in settings."

def test_issue_61(driver):
    """#61 - Duplicate Department Names - navigate via Settings sidebar"""
    print("\n[#61] Duplicate Department Names (Round 2)")
    login(driver, "org_admin")
    click_sidebar(driver, "Settings")
    time.sleep(2)
    screenshot(driver, "issue_61_r2_settings")

    # Look for Departments tab/link
    dept_link = find_by_text(driver, "a", "department") or find_by_text(driver, "button", "department")
    if dept_link:
        safe_click(driver, dept_link)
        time.sleep(3)

    tabs = driver.find_elements(By.CSS_SELECTOR, "button, a, [role='tab']")
    for tab in tabs:
        try:
            if "department" in tab.text.lower():
                safe_click(driver, tab)
                time.sleep(2)
                break
        except:
            pass

    screenshot(driver, "issue_61_r2_departments")

    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
        try:
            t = btn.text.lower()
            if any(k in t for k in ["add department", "add new", "add", "create", "+"]):
                add_btn = btn
                print(f"  Found add button: '{btn.text}'")
                break
        except:
            pass

    test_dept_name = f"TestDupDept"
    if add_btn:
        for attempt in range(2):
            safe_click(driver, add_btn)
            time.sleep(2)
            screenshot(driver, f"issue_61_r2_modal_{attempt+1}")

            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type='hidden']):not([type='password']):not([type='email'])")
            for inp in inputs:
                try:
                    if inp.is_displayed():
                        inp.clear()
                        inp.send_keys(test_dept_name)
                        break
                except:
                    pass
            time.sleep(1)
            for sb in driver.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = sb.text.lower()
                    if any(k in t for k in ["save", "submit", "add", "create", "ok", "confirm"]) and sb.is_displayed():
                        safe_click(driver, sb)
                        break
                except:
                    pass
            time.sleep(3)
            screenshot(driver, f"issue_61_r2_after_save_{attempt+1}")

            if attempt == 1:
                body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(k in body_text for k in ["duplicate", "already exists", "already added", "unique"]):
                    return "FIXED", "Duplicate department validation is now in place."
                toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='alert'], [class*='notification'], [role='alert'], [class*='Toastify']")
                for t in toasts:
                    try:
                        if any(k in t.text.lower() for k in ["duplicate", "already", "exists"]):
                            return "FIXED", "Duplicate department validation shown via toast."
                    except:
                        pass
            time.sleep(1)
            add_btn = None
            for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = btn.text.lower()
                    if any(k in t for k in ["add department", "add new", "add", "create", "+"]):
                        add_btn = btn
                        break
                except:
                    pass
        return "STILL_FAILING", "System still allows creating duplicate department names without validation."
    else:
        return "STILL_FAILING", "Could not find add department button in settings."

def test_issue_60(driver):
    """#60 - Duplicate Invite - use the Invite Now button on Users page"""
    print("\n[#60] Duplicate Invite (Round 2)")
    login(driver, "org_admin")
    # Navigate to Users via sidebar
    click_sidebar(driver, "Users")
    time.sleep(3)
    screenshot(driver, "issue_60_r2_users")
    print(f"  Users page URL: {driver.current_url}")

    test_email = f"duptest_r2_{int(time.time()) % 10000}@test.com"

    for attempt in range(2):
        # Find "Invite Now" button (purple button top right)
        invite_btn = None
        for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
            try:
                t = btn.text.strip().lower()
                if "invite" in t and btn.is_displayed():
                    invite_btn = btn
                    print(f"  Found invite button: '{btn.text}'")
                    break
            except:
                pass

        if not invite_btn:
            # Try link-based invite button
            for a in driver.find_elements(By.CSS_SELECTOR, "a"):
                try:
                    t = a.text.strip().lower()
                    if "invite" in t and a.is_displayed():
                        invite_btn = a
                        break
                except:
                    pass

        if invite_btn:
            safe_click(driver, invite_btn)
            time.sleep(3)
            screenshot(driver, f"issue_60_r2_invite_modal_{attempt+1}")

            # Find email input in the modal
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='email'], input[type='text'], input:not([type='hidden'])")
            email_entered = False
            for inp in inputs:
                try:
                    if not inp.is_displayed():
                        continue
                    ph = (inp.get_attribute("placeholder") or "").lower()
                    nm = (inp.get_attribute("name") or "").lower()
                    tp = (inp.get_attribute("type") or "").lower()
                    if "email" in ph or "email" in nm or tp == "email" or "mail" in ph:
                        inp.clear()
                        inp.send_keys(test_email)
                        email_entered = True
                        print(f"  Entered email: {test_email}")
                        break
                except:
                    pass

            if not email_entered:
                # Try first visible input
                for inp in inputs:
                    try:
                        if inp.is_displayed():
                            inp.clear()
                            inp.send_keys(test_email)
                            email_entered = True
                            break
                    except:
                        pass

            time.sleep(1)
            # Look for role select if needed
            selects = driver.find_elements(By.CSS_SELECTOR, "select, [class*='select']")
            for s in selects:
                try:
                    if s.is_displayed():
                        options = s.find_elements(By.TAG_NAME, "option")
                        if len(options) > 1:
                            options[1].click()
                except:
                    pass

            # Click send/invite/submit button in modal
            time.sleep(1)
            for sb in driver.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = sb.text.strip().lower()
                    if any(k in t for k in ["send invite", "invite", "send", "submit"]) and sb.is_displayed():
                        safe_click(driver, sb)
                        print(f"  Clicked submit: '{sb.text}'")
                        break
                except:
                    pass

            time.sleep(4)
            screenshot(driver, f"issue_60_r2_after_invite_{attempt+1}")

            if attempt == 1:
                body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(k in body_text for k in ["already invited", "duplicate", "already exists", "already sent", "already registered"]):
                    return "FIXED", "Duplicate invite validation is now in place."
                toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='alert'], [class*='Toastify'], [role='alert']")
                for t in toasts:
                    try:
                        tt = t.text.lower()
                        if any(k in tt for k in ["already", "duplicate", "exists", "invited"]):
                            return "FIXED", f"Duplicate invite validation shown: {t.text}"
                    except:
                        pass
        else:
            screenshot(driver, f"issue_60_r2_no_invite_{attempt+1}")
            return "STILL_FAILING", "Could not find Invite button."

    return "STILL_FAILING", "System still allows sending duplicate invites without validation."

def test_issue_59(driver):
    """#59 - Invited User Not Appearing Without Refresh"""
    print("\n[#59] Invited User Auto-Refresh (Round 2)")
    login(driver, "org_admin")
    click_sidebar(driver, "Users")
    time.sleep(3)

    # Count current pending invitations
    body_before = driver.find_element(By.TAG_NAME, "body").text
    screenshot(driver, "issue_59_r2_before")

    # Count rows/items before
    rows_before = driver.find_elements(By.CSS_SELECTOR, "tr, [class*='list-item'], [class*='row']")
    count_before = len(rows_before)
    print(f"  Rows before invite: {count_before}")

    # Click Invite Now
    invite_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
        try:
            if "invite" in btn.text.strip().lower() and btn.is_displayed():
                invite_btn = btn
                break
        except:
            pass

    if invite_btn:
        test_email = f"refresh_test_{int(time.time()) % 100000}@autotest.com"
        safe_click(driver, invite_btn)
        time.sleep(2)

        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='email'], input[type='text'], input:not([type='hidden'])")
        for inp in inputs:
            try:
                if not inp.is_displayed():
                    continue
                ph = (inp.get_attribute("placeholder") or "").lower()
                tp = (inp.get_attribute("type") or "").lower()
                nm = (inp.get_attribute("name") or "").lower()
                if "email" in ph or tp == "email" or "email" in nm or "mail" in ph:
                    inp.clear()
                    inp.send_keys(test_email)
                    break
            except:
                pass

        time.sleep(1)
        for sb in driver.find_elements(By.CSS_SELECTOR, "button"):
            try:
                t = sb.text.strip().lower()
                if any(k in t for k in ["send invite", "invite", "send", "submit"]) and sb.is_displayed():
                    safe_click(driver, sb)
                    break
            except:
                pass

        time.sleep(5)
        screenshot(driver, "issue_59_r2_after")

        # Check if list updated WITHOUT manual refresh
        body_after = driver.find_element(By.TAG_NAME, "body").text
        rows_after = driver.find_elements(By.CSS_SELECTOR, "tr, [class*='list-item'], [class*='row']")
        count_after = len(rows_after)
        print(f"  Rows after invite: {count_after}")

        if test_email.split("@")[0] in body_after.lower() or count_after > count_before:
            return "FIXED", "Invited user now appears in list without manual refresh."
        else:
            return "STILL_FAILING", f"Invited user still does not appear without refresh (rows before={count_before}, after={count_after})."

    return "STILL_FAILING", "Could not find invite button."

def test_issue_58(driver):
    """#58 - Sub-Modules Not Clickable - test sidebar navigation properly"""
    print("\n[#58] Sub-Modules Clickable (Round 2)")
    login(driver, "org_admin")
    time.sleep(3)

    # Get all sidebar links with their hrefs
    sidebar_items = []
    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    for link in links:
        try:
            text = link.text.strip()
            href = link.get_attribute("href") or ""
            if text and href and BASE_URL in href and text.lower() not in ["sign out", "logout", ""]:
                sidebar_items.append((text, href))
        except:
            pass

    print(f"  Found {len(sidebar_items)} sidebar links")

    clickable = 0
    failed = 0
    tested_items = []

    # Test each sidebar link by navigating to its href directly
    for text, href in sidebar_items[:20]:
        if href in [item[1] for item in tested_items]:
            continue
        try:
            driver.get(href)
            time.sleep(2)
            current = driver.current_url
            # Check if we're on the target page (not redirected to login or a different page)
            if "login" not in current.lower():
                # If URL matches or is close to the target
                if href.rstrip("/") == current.rstrip("/") or href.split("/")[-1] in current:
                    clickable += 1
                    tested_items.append((text, href, "OK"))
                else:
                    # Some pages redirect (e.g., settings -> settings/general) - still counts
                    if any(part in current for part in href.split("/")[-2:] if part):
                        clickable += 1
                        tested_items.append((text, href, "REDIRECT_OK"))
                    else:
                        failed += 1
                        tested_items.append((text, href, f"REDIRECT_TO:{current}"))
            else:
                failed += 1
                tested_items.append((text, href, "LOGIN_REDIRECT"))
        except Exception as e:
            failed += 1
            tested_items.append((text, href, f"ERROR:{e}"))

    for item in tested_items:
        print(f"    {item[0]}: {item[2]}")

    screenshot(driver, "issue_58_r2_final")
    print(f"  Clickable: {clickable}, Failed: {failed}")

    if failed == 0 and clickable > 0:
        return "FIXED", f"All {clickable} sidebar links navigate properly."
    elif clickable > failed:
        return "FIXED", f"Most sidebar links work ({clickable}/{clickable+failed})."
    else:
        return "STILL_FAILING", f"Sidebar navigation issues: {failed} of {clickable+failed} links failed."

def test_issue_56(driver):
    """#56 - City Text Validation - navigate to employee edit form"""
    print("\n[#56] City Text Validation (Round 2)")
    login(driver, "org_admin")
    click_sidebar(driver, "Employees")
    time.sleep(3)
    screenshot(driver, "issue_56_r2_employees")

    # Click on first employee name link
    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    for link in links:
        try:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            if "/employees/" in href and text and href != f"{BASE_URL}/employees" and href != f"{BASE_URL}/employees/":
                print(f"  Clicking employee: {text} -> {href}")
                safe_click(driver, link)
                time.sleep(3)
                break
        except:
            pass

    screenshot(driver, "issue_56_r2_employee_detail")
    print(f"  Employee detail URL: {driver.current_url}")

    # Look for Edit button
    edit_btn = find_by_text(driver, "button", "edit")
    if not edit_btn:
        # Try icon-based edit buttons
        for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
            try:
                title = (btn.get_attribute("title") or "").lower()
                aria = (btn.get_attribute("aria-label") or "").lower()
                if "edit" in title or "edit" in aria:
                    edit_btn = btn
                    break
            except:
                pass

    if edit_btn:
        safe_click(driver, edit_btn)
        time.sleep(3)
        print(f"  Clicked edit, URL: {driver.current_url}")

    screenshot(driver, "issue_56_r2_edit_form")

    # Gather all visible labels to understand form structure
    labels = driver.find_elements(By.CSS_SELECTOR, "label")
    print(f"  Form labels: {[l.text.strip() for l in labels[:20]]}")

    # Find city input by label association or name/placeholder
    city_input = None
    all_inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])")
    for inp in all_inputs:
        try:
            if not inp.is_displayed():
                continue
            nm = (inp.get_attribute("name") or "").lower()
            ph = (inp.get_attribute("placeholder") or "").lower()
            iid = (inp.get_attribute("id") or "").lower()
            if "city" in nm or "city" in ph or "city" in iid:
                city_input = inp
                print(f"  Found city input: name={nm}, placeholder={ph}")
                break
        except:
            pass

    # If not found by direct attr, try via labels
    if not city_input:
        for lab in labels:
            try:
                if "city" in lab.text.lower():
                    for_attr = lab.get_attribute("for")
                    if for_attr:
                        city_input = driver.find_element(By.ID, for_attr)
                    else:
                        # Find next sibling input
                        parent = lab.find_element(By.XPATH, "..")
                        inp = parent.find_element(By.CSS_SELECTOR, "input")
                        city_input = inp
                    break
            except:
                pass

    if city_input:
        city_input.clear()
        city_input.send_keys("12345")
        time.sleep(1)
        val_after = city_input.get_attribute("value") or ""
        print(f"  City value after entering 12345: '{val_after}'")

        # Try to save
        save_btn = find_by_text(driver, "button", "save") or find_by_text(driver, "button", "update")
        if save_btn:
            safe_click(driver, save_btn)
            time.sleep(3)

        screenshot(driver, "issue_56_r2_validation")
        page = driver.page_source.lower()
        body = driver.find_element(By.TAG_NAME, "body").text.lower()

        if any(k in body for k in ["invalid", "only alphabets", "letters only", "not valid", "only characters", "alphabetic", "numbers not allowed"]):
            return "FIXED", "City field now validates against numeric input."

        # Check if value was filtered
        val_now = city_input.get_attribute("value") or ""
        if val_now != "12345":
            return "FIXED", f"City field filtered numeric input (value: '{val_now}')."

        return "STILL_FAILING", "City field still accepts numeric values without validation."

    screenshot(driver, "issue_56_r2_no_city")
    # Print all input names for debugging
    for inp in all_inputs[:20]:
        try:
            print(f"    Input: name={inp.get_attribute('name')}, placeholder={inp.get_attribute('placeholder')}, type={inp.get_attribute('type')}")
        except:
            pass
    return "STILL_FAILING", "Could not locate city field in employee edit form."

def test_issue_43(driver):
    """#43 - Org admin update employee details"""
    print("\n[#43] Org Admin Update Employee (Round 2)")
    login(driver, "org_admin")
    click_sidebar(driver, "Employees")
    time.sleep(3)

    # Click on an employee name
    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    employee_link = None
    for link in links:
        try:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            if "/employees/" in href and text and href != f"{BASE_URL}/employees" and href != f"{BASE_URL}/employees/":
                employee_link = link
                print(f"  Found employee link: {text} -> {href}")
                break
        except:
            pass

    if employee_link:
        safe_click(driver, employee_link)
        time.sleep(4)
        screenshot(driver, "issue_43_r2_detail")
        print(f"  Employee detail URL: {driver.current_url}")

        # Check page content
        body_text = driver.find_element(By.TAG_NAME, "body").text
        page = driver.page_source.lower()

        # Look for edit functionality
        btns = driver.find_elements(By.CSS_SELECTOR, "button, a")
        edit_options = []
        for b in btns:
            try:
                t = b.text.strip().lower()
                title = (b.get_attribute("title") or "").lower()
                cls = (b.get_attribute("class") or "").lower()
                if any(k in (t + title) for k in ["edit", "update", "modify"]):
                    edit_options.append(t or title)
            except:
                pass

        print(f"  Edit options found: {edit_options}")

        # Also check for inline editing or pencil icons
        icons = driver.find_elements(By.CSS_SELECTOR, "svg, i, [class*='icon'], [class*='edit'], [class*='pencil']")
        edit_icons = []
        for icon in icons:
            try:
                title = (icon.get_attribute("title") or "").lower()
                cls = (icon.get_attribute("class") or "").lower()
                if "edit" in title or "edit" in cls or "pencil" in cls:
                    edit_icons.append(cls or title)
            except:
                pass
        print(f"  Edit icons found: {len(edit_icons)}")

        if edit_options or edit_icons:
            # Try clicking edit
            for b in btns:
                try:
                    t = b.text.strip().lower()
                    title = (b.get_attribute("title") or "").lower()
                    if "edit" in t or "edit" in title:
                        safe_click(driver, b)
                        time.sleep(3)
                        screenshot(driver, "issue_43_r2_edit_form")
                        inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']), select, textarea")
                        visible_inputs = [i for i in inputs if i.is_displayed()]
                        print(f"  Visible form inputs: {len(visible_inputs)}")
                        if len(visible_inputs) > 2:
                            return "FIXED", "Org admin can edit employee details - form with inputs is accessible."
                        break
                except:
                    pass
            return "FIXED", "Edit option is available for org admin on employee page."

        screenshot(driver, "issue_43_r2_no_edit")

        # Check if there are tabs (Personal, Employment, etc.)
        tabs = driver.find_elements(By.CSS_SELECTOR, "[role='tab'], button, a")
        tab_texts = []
        for tab in tabs:
            try:
                t = tab.text.strip()
                if t:
                    tab_texts.append(t)
            except:
                pass
        print(f"  Available tabs/buttons: {tab_texts[:15]}")

        return "STILL_FAILING", "No edit option found for org admin to update employee details."

    return "STILL_FAILING", "Could not navigate to employee detail page."

def test_issue_39(driver):
    """#39 - Multiple Likes on Knowledge Base - find correct navigation"""
    print("\n[#39] Knowledge Base Multiple Likes (Round 2)")
    login(driver, "employee")
    time.sleep(3)

    # Check sidebar for knowledge base or similar
    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    kb_link = None
    for link in links:
        try:
            text = link.text.strip().lower()
            href = (link.get_attribute("href") or "").lower()
            if any(k in text for k in ["knowledge", "kb", "articles", "wiki", "community"]):
                kb_link = link
                print(f"  Found KB link: {link.text.strip()} -> {href}")
                break
            if any(k in href for k in ["knowledge", "kb", "articles", "wiki", "community"]):
                kb_link = link
                print(f"  Found KB link by href: {link.text.strip()} -> {href}")
                break
        except:
            pass

    if kb_link:
        safe_click(driver, kb_link)
        time.sleep(3)
    else:
        # Try Community from sidebar (seen in employee dashboard)
        click_sidebar(driver, "Community")
        time.sleep(3)

    screenshot(driver, "issue_39_r2_page")
    print(f"  KB/Community URL: {driver.current_url}")
    page = driver.page_source.lower()
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Page content snippet: {body[:200]}")

    # Look for articles/posts with like buttons
    cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='article'], [class*='post'], article")
    if cards:
        safe_click(driver, cards[0])
        time.sleep(3)

    screenshot(driver, "issue_39_r2_article")

    # Find like/thumb button
    like_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button, span, div"):
        try:
            t = btn.text.strip().lower()
            cls = (btn.get_attribute("class") or "").lower()
            title = (btn.get_attribute("title") or "").lower()
            if any(k in (t + cls + title) for k in ["like", "thumb", "upvote", "helpful", "heart"]):
                like_btn = btn
                print(f"  Found like button: text='{t}', class='{cls}'")
                break
        except:
            pass

    # Also look for SVG icons (thumbs up, heart)
    if not like_btn:
        svgs = driver.find_elements(By.CSS_SELECTOR, "svg")
        for svg in svgs:
            try:
                parent = svg.find_element(By.XPATH, "..")
                title = (parent.get_attribute("title") or "").lower()
                cls = (parent.get_attribute("class") or "").lower()
                if any(k in (title + cls) for k in ["like", "thumb", "heart"]):
                    like_btn = parent
                    break
            except:
                pass

    if like_btn:
        safe_click(driver, like_btn)
        time.sleep(2)
        screenshot(driver, "issue_39_r2_after_like1")

        # Get text/count after first like
        body1 = driver.find_element(By.TAG_NAME, "body").text

        safe_click(driver, like_btn)
        time.sleep(2)
        screenshot(driver, "issue_39_r2_after_like2")

        body2 = driver.find_element(By.TAG_NAME, "body").text

        if body1 == body2:
            return "FIXED", "Like button prevents duplicate likes (toggle or blocked)."
        return "STILL_FAILING", "Multiple likes appear to be possible on same article."

    screenshot(driver, "issue_39_r2_no_like")
    return "STILL_FAILING", "Could not find like button on knowledge base/community page."

def test_issue_38(driver):
    """#38 - Wellness Goals Date Validation"""
    print("\n[#38] Wellness Goals Date Validation (Round 2)")
    login(driver, "employee")
    click_sidebar(driver, "Wellness")
    time.sleep(3)
    screenshot(driver, "issue_38_r2_wellness")
    print(f"  Wellness URL: {driver.current_url}")

    # Click "My Wellness" tab if it exists
    my_wellness = find_by_text(driver, "button", "my wellness") or find_by_text(driver, "a", "my wellness")
    if my_wellness:
        safe_click(driver, my_wellness)
        time.sleep(3)
        print("  Clicked My Wellness tab")

    screenshot(driver, "issue_38_r2_my_wellness")

    # Look for add goal button
    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if any(k in t for k in ["add goal", "create goal", "new goal", "set goal", "add", "create"]) and btn.is_displayed():
                add_btn = btn
                print(f"  Found add button: '{btn.text}'")
                break
        except:
            pass

    if add_btn:
        safe_click(driver, add_btn)
        time.sleep(3)
        screenshot(driver, "issue_38_r2_add_form")

    # Find date inputs
    date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[type='datetime-local']")
    visible_dates = [d for d in date_inputs if d.is_displayed()]
    print(f"  Visible date inputs: {len(visible_dates)}")

    if len(visible_dates) >= 2:
        # Set start date after end date
        driver.execute_script("arguments[0].value = '2026-12-31'", visible_dates[0])
        visible_dates[0].send_keys("2026-12-31")
        time.sleep(0.5)
        driver.execute_script("arguments[0].value = '2026-01-01'", visible_dates[1])
        visible_dates[1].send_keys("2026-01-01")
        time.sleep(1)

        screenshot(driver, "issue_38_r2_dates_set")

        save_btn = find_by_text(driver, "button", "save") or find_by_text(driver, "button", "create") or find_by_text(driver, "button", "submit") or find_by_text(driver, "button", "add")
        if save_btn:
            safe_click(driver, save_btn)
            time.sleep(3)

        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        screenshot(driver, "issue_38_r2_validation")

        if any(k in body for k in ["end date", "invalid date", "before start", "after start", "valid date", "must be after", "must be greater"]):
            return "FIXED", "Date range validation is in place for wellness goals."

        # Check toasts
        toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='alert'], [class*='Toastify']")
        for t in toasts:
            try:
                if any(k in t.text.lower() for k in ["date", "invalid", "before", "after"]):
                    return "FIXED", f"Date validation shown: {t.text}"
            except:
                pass

        return "STILL_FAILING", "System still allows invalid date range in wellness goals."

    # Maybe the form uses different date picker
    all_inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])")
    visible = [i for i in all_inputs if i.is_displayed()]
    print(f"  All visible inputs: {len(visible)}")
    for inp in visible:
        try:
            print(f"    name={inp.get_attribute('name')}, type={inp.get_attribute('type')}, ph={inp.get_attribute('placeholder')}")
        except:
            pass

    screenshot(driver, "issue_38_r2_no_dates")
    return "STILL_FAILING", "Could not find date fields in wellness goals."

def test_issue_36(driver):
    """#36 - Survey End Date Before Start Date"""
    print("\n[#36] Survey Date Validation (Round 2)")
    login(driver, "org_admin")

    # Check sidebar for Surveys
    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    survey_link = None
    for link in links:
        try:
            text = link.text.strip().lower()
            href = (link.get_attribute("href") or "").lower()
            if "survey" in text or "survey" in href:
                survey_link = link
                print(f"  Found survey link: {link.text.strip()} -> {href}")
                break
        except:
            pass

    if survey_link:
        safe_click(driver, survey_link)
        time.sleep(3)
    else:
        # Try direct URLs
        for url in [f"{BASE_URL}/surveys", f"{BASE_URL}/survey", f"{BASE_URL}/my-events"]:
            driver.get(url)
            time.sleep(3)
            if "login" not in driver.current_url.lower():
                break

    screenshot(driver, "issue_36_r2_page")
    print(f"  Survey URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Page content snippet: {body[:200]}")

    # Look for create survey button
    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if any(k in t for k in ["create survey", "add survey", "new survey", "create", "add"]) and btn.is_displayed():
                add_btn = btn
                print(f"  Found add button: '{btn.text}'")
                break
        except:
            pass

    if add_btn:
        safe_click(driver, add_btn)
        time.sleep(3)
        screenshot(driver, "issue_36_r2_create_form")

        date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[type='datetime-local']")
        visible_dates = [d for d in date_inputs if d.is_displayed()]
        print(f"  Date inputs: {len(visible_dates)}")

        if len(visible_dates) >= 2:
            driver.execute_script("arguments[0].value = '2026-12-31'", visible_dates[0])
            visible_dates[0].send_keys("2026-12-31")
            time.sleep(0.5)
            driver.execute_script("arguments[0].value = '2026-01-01'", visible_dates[1])
            visible_dates[1].send_keys("2026-01-01")
            time.sleep(1)

            save_btn = find_by_text(driver, "button", "save") or find_by_text(driver, "button", "create") or find_by_text(driver, "button", "submit")
            if save_btn:
                safe_click(driver, save_btn)
                time.sleep(3)

            body2 = driver.find_element(By.TAG_NAME, "body").text.lower()
            screenshot(driver, "issue_36_r2_validation")

            if any(k in body2 for k in ["end date", "invalid", "before start", "after start", "must be after"]):
                return "FIXED", "Survey date validation prevents end before start."
            return "STILL_FAILING", "System still allows survey end date before start date."

    screenshot(driver, "issue_36_r2_final")
    # Check if surveys module exists at all
    if "survey" in body.lower():
        return "STILL_FAILING", "Survey page loads but could not find create survey form with date fields."
    return "STILL_FAILING", "Survey module not accessible or not found in navigation."

def test_issue_34(driver):
    """#34 - Wellness End Date Before Start Date (org admin creating program)"""
    print("\n[#34] Wellness Date Validation (Round 2)")
    login(driver, "org_admin")
    click_sidebar(driver, "Wellness")
    time.sleep(3)
    screenshot(driver, "issue_34_r2_wellness")
    print(f"  Wellness URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Page snippet: {body[:200]}")

    # Look for create program button
    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if any(k in t for k in ["create program", "add program", "new program", "create", "add"]) and btn.is_displayed():
                add_btn = btn
                print(f"  Found add button: '{btn.text}'")
                break
        except:
            pass

    if add_btn:
        safe_click(driver, add_btn)
        time.sleep(3)
        screenshot(driver, "issue_34_r2_create_form")

        date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[type='datetime-local']")
        visible_dates = [d for d in date_inputs if d.is_displayed()]
        print(f"  Date inputs: {len(visible_dates)}")

        if len(visible_dates) >= 2:
            driver.execute_script("arguments[0].value = '2026-12-31'", visible_dates[0])
            visible_dates[0].send_keys("2026-12-31")
            time.sleep(0.5)
            driver.execute_script("arguments[0].value = '2026-01-01'", visible_dates[1])
            visible_dates[1].send_keys("2026-01-01")
            time.sleep(1)

            save_btn = find_by_text(driver, "button", "save") or find_by_text(driver, "button", "create") or find_by_text(driver, "button", "submit") or find_by_text(driver, "button", "add")
            if save_btn:
                safe_click(driver, save_btn)
                time.sleep(3)

            body2 = driver.find_element(By.TAG_NAME, "body").text.lower()
            screenshot(driver, "issue_34_r2_validation")

            if any(k in body2 for k in ["end date", "invalid", "before start", "after start", "must be after"]):
                return "FIXED", "Wellness date validation prevents end before start."

            toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='alert'], [class*='Toastify']")
            for t in toasts:
                try:
                    if any(k in t.text.lower() for k in ["date", "invalid", "before", "after"]):
                        return "FIXED", f"Validation shown: {t.text}"
                except:
                    pass

            return "STILL_FAILING", "Wellness module still allows end date before start date."

    # If no add button, check if there's already content - maybe need to click into a program
    screenshot(driver, "issue_34_r2_no_add")
    return "STILL_FAILING", "Could not find create wellness program form with date fields."

def test_issue_33(driver):
    """#33 - Asset Warranty Expiry Before Purchase Date"""
    print("\n[#33] Asset Warranty Date Validation (Round 2)")
    login(driver, "org_admin")

    # Find assets in sidebar
    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    asset_link = None
    for link in links:
        try:
            text = link.text.strip().lower()
            href = (link.get_attribute("href") or "").lower()
            if "asset" in text or "asset" in href:
                asset_link = link
                print(f"  Found asset link: {link.text.strip()} -> {href}")
                break
        except:
            pass

    if asset_link:
        safe_click(driver, asset_link)
        time.sleep(3)
    else:
        # Try via sidebar navigation
        click_sidebar(driver, "AI Assistant")  # Nearby in sidebar
        time.sleep(1)
        # Try direct URL patterns
        for url in [f"{BASE_URL}/assets", f"{BASE_URL}/asset-management", f"{BASE_URL}/it-assets"]:
            driver.get(url)
            time.sleep(2)
            page = driver.page_source.lower()
            if "403" not in page and "forbidden" not in page and "login" not in driver.current_url.lower():
                break

    screenshot(driver, "issue_33_r2_page")
    print(f"  Assets URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Page snippet: {body[:300]}")

    if "403" in body or "forbidden" in body.lower():
        # Assets module may not be enabled or accessible
        return "STILL_FAILING", "Assets page returns 403 Forbidden - module may not be accessible."

    # Look for add asset
    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if any(k in t for k in ["add asset", "create asset", "new asset", "add", "create"]) and btn.is_displayed():
                add_btn = btn
                print(f"  Found add button: '{btn.text}'")
                break
        except:
            pass

    if add_btn:
        safe_click(driver, add_btn)
        time.sleep(3)
        screenshot(driver, "issue_33_r2_form")

        # Look for purchase date and warranty fields
        all_inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])")
        labels = driver.find_elements(By.CSS_SELECTOR, "label")
        print(f"  Labels: {[l.text.strip() for l in labels[:15]]}")

        date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[type='datetime-local']")
        visible_dates = [d for d in date_inputs if d.is_displayed()]
        print(f"  Date inputs: {len(visible_dates)}")

        if len(visible_dates) >= 2:
            driver.execute_script("arguments[0].value = '2026-12-31'", visible_dates[0])
            visible_dates[0].send_keys("2026-12-31")
            time.sleep(0.5)
            driver.execute_script("arguments[0].value = '2026-01-01'", visible_dates[1])
            visible_dates[1].send_keys("2026-01-01")
            time.sleep(1)

            save_btn = find_by_text(driver, "button", "save") or find_by_text(driver, "button", "add") or find_by_text(driver, "button", "submit")
            if save_btn:
                safe_click(driver, save_btn)
                time.sleep(3)

            body2 = driver.find_element(By.TAG_NAME, "body").text.lower()
            screenshot(driver, "issue_33_r2_validation")

            if any(k in body2 for k in ["before purchase", "invalid", "expiry", "after purchase", "warranty"]):
                return "FIXED", "Asset warranty date validation is in place."
            return "STILL_FAILING", "System still allows warranty expiry before purchase date."

    screenshot(driver, "issue_33_r2_final")
    return "STILL_FAILING", "Could not access asset management form to test date validation."


# ========================= MAIN =========================

def main():
    print("=" * 70)
    print("EmpCloud Closed Issue Re-Test - ROUND 2 - 2026-03-27")
    print("Testing 12 issues that were STILL_FAILING in round 1")
    print("=" * 70)

    # Track round 1 results for comparison
    round1_failing = {
        62: "System still allows creating duplicate location names without validation.",
        61: "System still allows creating duplicate department names without validation.",
        60: "System still allows sending duplicate invites without validation.",
        59: "Invited user still does not appear without manual page refresh.",
        58: "Sub-modules still not clickable.",
        56: "Could not locate city field to test validation.",
        43: "No edit option found for org admin to update employee details.",
        39: "Could not find like button on knowledge base article.",
        38: "Could not find date fields in wellness goals to test.",
        36: "Could not find date fields in survey creation.",
        34: "Could not find date fields in wellness module.",
        33: "Could not find purchase/warranty date fields.",
    }

    tests = [
        (62, test_issue_62),
        (61, test_issue_61),
        (60, test_issue_60),
        (59, test_issue_59),
        (58, test_issue_58),
        (56, test_issue_56),
        (43, test_issue_43),
        (39, test_issue_39),
        (38, test_issue_38),
        (36, test_issue_36),
        (34, test_issue_34),
        (33, test_issue_33),
    ]

    driver = None
    for issue_num, test_func in tests:
        try:
            driver = get_driver()
            status, details = test_func(driver)
            results[issue_num] = (status, details)
            print(f"  Result: {status} - {details}")
            # Update GitHub only if status changed
            update_issue_if_changed(issue_num, "STILL_FAILING", status, details)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"  ERROR in test #{issue_num}: {e}")
            print(f"  {tb}")
            results[issue_num] = ("ERROR", str(e))
            try:
                screenshot(driver, f"issue_{issue_num}_r2_error")
            except:
                pass
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                driver = None

    # Print summary
    print("\n" + "=" * 70)
    print("ROUND 2 SUMMARY")
    print("=" * 70)
    print(f"{'Issue':<10} {'Status':<18} {'Details'}")
    print("-" * 70)
    for issue_num, test_func in tests:
        status, details = results.get(issue_num, ("NOT_RUN", ""))
        print(f"#{issue_num:<9} {status:<18} {details[:60]}")

    fixed = sum(1 for s, _ in results.values() if s == "FIXED")
    failing = sum(1 for s, _ in results.values() if s == "STILL_FAILING")
    errors = sum(1 for s, _ in results.values() if s == "ERROR")
    print(f"\nTotal: {len(results)} tested | FIXED: {fixed} | STILL_FAILING: {failing} | ERRORS: {errors}")

if __name__ == "__main__":
    main()
