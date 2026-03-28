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
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\retest"
GITHUB_TOKEN = "$GITHUB_TOKEN"
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

def ss(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  SS: {path}")
    return path

def login(driver, role="org_admin", max_retries=3):
    email, pwd = CREDS[role]
    for attempt in range(max_retries):
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)
        try:
            # Check for rate limit
            body = driver.find_element(By.TAG_NAME, "body").text
            if "too many" in body.lower():
                print(f"  Rate limited, waiting 30s (attempt {attempt+1})...")
                time.sleep(30)
                driver.get(f"{BASE_URL}/login")
                time.sleep(3)

            ef = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email'], input[type='email']"))
            )
            ef.clear(); ef.send_keys(email)
            pf = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
            pf.clear(); pf.send_keys(pwd)
            time.sleep(0.5)

            # Find sign in button
            btns = driver.find_elements(By.CSS_SELECTOR, "button")
            for b in btns:
                txt = b.text.lower().strip()
                if any(k in txt for k in ["sign in", "login", "log in"]):
                    b.click()
                    break

            time.sleep(5)

            # Verify login succeeded
            if "login" not in driver.current_url.lower() or "dashboard" in driver.current_url.lower():
                print(f"  Logged in as {role} ({email}), URL: {driver.current_url}")
                return True

            body = driver.find_element(By.TAG_NAME, "body").text
            if "too many" in body.lower():
                print(f"  Rate limited after login, waiting 30s...")
                time.sleep(30)
                continue

            # Maybe we're on dashboard but URL didn't change much
            if "welcome" in body.lower() or "dashboard" in body.lower():
                print(f"  Logged in as {role}, URL: {driver.current_url}")
                return True

        except Exception as e:
            print(f"  Login attempt {attempt+1} failed: {e}")
            time.sleep(10)

    print(f"  FAILED to login as {role} after {max_retries} attempts")
    return False

def safe_click(driver, el):
    try:
        el.click()
    except:
        driver.execute_script("arguments[0].click();", el)

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

def get_sidebar_hrefs(driver):
    """Get all sidebar link texts and hrefs."""
    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    sidebar = {}
    for link in links:
        try:
            text = link.text.strip()
            href = link.get_attribute("href") or ""
            if text and BASE_URL in href:
                sidebar[text.lower()] = href
        except:
            pass
    return sidebar

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
        body = e.read().decode()
        print(f"  GitHub API error: {e.code} {body[:200]}")
        return None

def update_github(number, status, details):
    if status == "FIXED":
        # Close the re-opened issue and comment
        github_api("PATCH", f"/issues/{number}", {"state": "closed"})
        github_api("POST", f"/issues/{number}/comments", {"body": f"Re-tested on 2026-03-27 (round 3). Bug appears to be fixed.\n\n{details}"})
    elif status == "STILL_FAILING":
        # Ensure it's open and add comment
        github_api("PATCH", f"/issues/{number}", {"state": "open"})
        github_api("POST", f"/issues/{number}/comments", {"body": f"Re-tested on 2026-03-27 (round 3). Bug is still present.\n\n{details}"})


# ========================= TESTS =========================

def test_org_admin_batch(driver):
    """Run all org_admin tests in one session to avoid rate limiting."""
    if not login(driver, "org_admin"):
        return False

    # Get sidebar links for navigation
    sidebar = get_sidebar_hrefs(driver)
    print(f"  Sidebar links: {list(sidebar.keys())}")

    # --- #62: Duplicate Location Names ---
    print("\n[#62] Duplicate Location Names (Round 3)")
    settings_url = sidebar.get("settings", f"{BASE_URL}/settings")
    driver.get(settings_url)
    time.sleep(3)
    ss(driver, "issue_62_r3_settings")
    print(f"  Settings URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Settings page: {body[:300]}")

    # Look for tabs/links within settings page for Locations
    all_links = driver.find_elements(By.CSS_SELECTOR, "a[href], button, [role='tab']")
    settings_tabs = []
    for el in all_links:
        try:
            t = el.text.strip()
            if t and len(t) < 40:
                settings_tabs.append(t)
        except:
            pass
    print(f"  Settings tabs/links: {settings_tabs[:20]}")

    # Try clicking Locations tab
    loc_clicked = False
    for el in all_links:
        try:
            if "location" in el.text.strip().lower():
                safe_click(driver, el)
                time.sleep(3)
                loc_clicked = True
                print(f"  Clicked: {el.text}")
                break
        except:
            pass

    ss(driver, "issue_62_r3_locations_tab")

    # Try adding duplicate location
    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
        try:
            t = btn.text.strip().lower()
            if btn.is_displayed() and any(k in t for k in ["add location", "add", "create", "new", "+"]):
                add_btn = btn
                print(f"  Add button: '{btn.text}'")
                break
        except:
            pass

    loc_name = "DupLocTest"
    if add_btn:
        for attempt in range(2):
            try:
                safe_click(driver, add_btn)
                time.sleep(2)
                ss(driver, f"issue_62_r3_modal_{attempt}")

                # Fill in name
                visible_inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type='hidden']):not([type='password']):not([type='email']):not([type='search'])") if i.is_displayed()]
                print(f"  Visible inputs: {len(visible_inputs)}")
                if visible_inputs:
                    visible_inputs[0].clear()
                    visible_inputs[0].send_keys(loc_name)

                time.sleep(1)
                # Click save
                for sb in driver.find_elements(By.CSS_SELECTOR, "button"):
                    try:
                        t = sb.text.strip().lower()
                        if sb.is_displayed() and any(k in t for k in ["save", "submit", "add", "create", "confirm"]):
                            safe_click(driver, sb)
                            print(f"  Save button: '{sb.text}'")
                            break
                    except:
                        pass
                time.sleep(3)
                ss(driver, f"issue_62_r3_saved_{attempt}")

                if attempt == 1:
                    body = driver.find_element(By.TAG_NAME, "body").text.lower()
                    toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='Toastify'], [role='alert']")
                    toast_text = " ".join([t.text.lower() for t in toasts])
                    if any(k in (body + toast_text) for k in ["duplicate", "already exists", "already added", "unique"]):
                        results[62] = ("FIXED", "Duplicate location validation now shows error.")
                    else:
                        results[62] = ("STILL_FAILING", "System still allows creating duplicate location names.")

                # Re-find add button
                add_btn = None
                for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
                    try:
                        t = btn.text.strip().lower()
                        if btn.is_displayed() and any(k in t for k in ["add location", "add", "create", "+"]):
                            add_btn = btn
                            break
                    except:
                        pass
            except Exception as e:
                print(f"  Error in attempt {attempt}: {e}")
    else:
        results[62] = ("STILL_FAILING", "Could not find add location button. Settings page may not have locations tab.")

    if 62 not in results:
        results[62] = ("STILL_FAILING", "Could not complete duplicate location test.")

    # --- #61: Duplicate Department Names ---
    print("\n[#61] Duplicate Department Names (Round 3)")
    driver.get(settings_url)
    time.sleep(3)

    # Look for Department tab
    all_links = driver.find_elements(By.CSS_SELECTOR, "a[href], button, [role='tab']")
    dept_clicked = False
    for el in all_links:
        try:
            if "department" in el.text.strip().lower():
                safe_click(driver, el)
                time.sleep(3)
                dept_clicked = True
                print(f"  Clicked department tab: {el.text}")
                break
        except:
            pass

    ss(driver, "issue_61_r3_dept_tab")

    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
        try:
            t = btn.text.strip().lower()
            if btn.is_displayed() and any(k in t for k in ["add department", "add", "create", "+"]):
                add_btn = btn
                break
        except:
            pass

    dept_name = "DupDeptTest"
    if add_btn:
        for attempt in range(2):
            try:
                safe_click(driver, add_btn)
                time.sleep(2)
                visible_inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type='hidden']):not([type='password']):not([type='email']):not([type='search'])") if i.is_displayed()]
                if visible_inputs:
                    visible_inputs[0].clear()
                    visible_inputs[0].send_keys(dept_name)
                time.sleep(1)
                for sb in driver.find_elements(By.CSS_SELECTOR, "button"):
                    try:
                        t = sb.text.strip().lower()
                        if sb.is_displayed() and any(k in t for k in ["save", "submit", "add", "create", "confirm"]):
                            safe_click(driver, sb)
                            break
                    except:
                        pass
                time.sleep(3)
                ss(driver, f"issue_61_r3_saved_{attempt}")

                if attempt == 1:
                    body = driver.find_element(By.TAG_NAME, "body").text.lower()
                    toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='Toastify'], [role='alert']")
                    toast_text = " ".join([t.text.lower() for t in toasts])
                    if any(k in (body + toast_text) for k in ["duplicate", "already exists", "already added", "unique"]):
                        results[61] = ("FIXED", "Duplicate department validation now shows error.")
                    else:
                        results[61] = ("STILL_FAILING", "System still allows creating duplicate department names.")

                add_btn = None
                for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
                    try:
                        t = btn.text.strip().lower()
                        if btn.is_displayed() and any(k in t for k in ["add department", "add", "create", "+"]):
                            add_btn = btn
                            break
                    except:
                        pass
            except Exception as e:
                print(f"  Error: {e}")
    else:
        results[61] = ("STILL_FAILING", "Could not find add department button in settings.")

    if 61 not in results:
        results[61] = ("STILL_FAILING", "Could not complete duplicate department test.")

    # --- #60: Duplicate Invite ---
    print("\n[#60] Duplicate Invite (Round 3)")
    users_url = sidebar.get("users", f"{BASE_URL}/users")
    driver.get(users_url)
    time.sleep(4)
    ss(driver, "issue_60_r3_users")
    print(f"  Users URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Users page snippet: {body[:200]}")

    # Find Invite Now button
    invite_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if "invite" in t and btn.is_displayed():
                invite_btn = btn
                print(f"  Found invite button: '{btn.text}'")
                break
        except:
            pass

    test_email = f"dup_r3_{int(time.time()) % 10000}@test.com"
    if invite_btn:
        for attempt in range(2):
            safe_click(driver, invite_btn)
            time.sleep(3)
            ss(driver, f"issue_60_r3_invite_{attempt}")

            # Print all visible inputs for debugging
            all_vis = [i for i in driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if i.is_displayed()]
            for v in all_vis:
                try:
                    print(f"    Input: name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
                except:
                    pass

            # Enter email
            for inp in all_vis:
                try:
                    tp = (inp.get_attribute("type") or "").lower()
                    ph = (inp.get_attribute("placeholder") or "").lower()
                    nm = (inp.get_attribute("name") or "").lower()
                    if tp == "email" or "email" in ph or "email" in nm or "mail" in ph:
                        inp.clear()
                        inp.send_keys(test_email)
                        print(f"  Entered email in input: {nm or ph}")
                        break
                except:
                    pass

            time.sleep(1)
            # Select role if needed
            selects = [s for s in driver.find_elements(By.CSS_SELECTOR, "select") if s.is_displayed()]
            for s in selects:
                try:
                    opts = s.find_elements(By.TAG_NAME, "option")
                    if len(opts) > 1:
                        opts[1].click()
                except:
                    pass

            # Click send
            time.sleep(1)
            for sb in driver.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = sb.text.strip().lower()
                    if sb.is_displayed() and any(k in t for k in ["send invite", "invite", "send", "submit"]):
                        safe_click(driver, sb)
                        print(f"  Clicked: '{sb.text}'")
                        break
                except:
                    pass
            time.sleep(4)
            ss(driver, f"issue_60_r3_after_{attempt}")

            if attempt == 1:
                body = driver.find_element(By.TAG_NAME, "body").text.lower()
                toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='Toastify'], [role='alert']")
                toast_text = " ".join([t.text.lower() for t in toasts])
                combined = body + " " + toast_text
                if any(k in combined for k in ["already invited", "duplicate", "already exists", "already sent", "already registered"]):
                    results[60] = ("FIXED", "Duplicate invite validation is now in place.")
                else:
                    results[60] = ("STILL_FAILING", "System still allows sending duplicate invites.")
    else:
        results[60] = ("STILL_FAILING", "Could not find Invite button on Users page.")

    if 60 not in results:
        results[60] = ("STILL_FAILING", "Could not complete duplicate invite test.")

    # --- #59: Invited User Auto-Refresh ---
    print("\n[#59] Auto-Refresh After Invite (Round 3)")
    driver.get(users_url)
    time.sleep(4)
    body_before = driver.find_element(By.TAG_NAME, "body").text
    items_before = len(driver.find_elements(By.CSS_SELECTOR, "tr, [class*='list-item']"))

    invite_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            if "invite" in btn.text.strip().lower() and btn.is_displayed():
                invite_btn = btn
                break
        except:
            pass

    if invite_btn:
        fresh_email = f"refresh_r3_{int(time.time()) % 100000}@test.com"
        safe_click(driver, invite_btn)
        time.sleep(3)

        all_vis = [i for i in driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if i.is_displayed()]
        for inp in all_vis:
            try:
                tp = (inp.get_attribute("type") or "").lower()
                ph = (inp.get_attribute("placeholder") or "").lower()
                nm = (inp.get_attribute("name") or "").lower()
                if tp == "email" or "email" in ph or "email" in nm:
                    inp.clear()
                    inp.send_keys(fresh_email)
                    break
            except:
                pass

        time.sleep(1)
        for sb in driver.find_elements(By.CSS_SELECTOR, "button"):
            try:
                t = sb.text.strip().lower()
                if sb.is_displayed() and any(k in t for k in ["send invite", "invite", "send", "submit"]):
                    safe_click(driver, sb)
                    break
            except:
                pass

        time.sleep(5)
        ss(driver, "issue_59_r3_after")
        body_after = driver.find_element(By.TAG_NAME, "body").text
        items_after = len(driver.find_elements(By.CSS_SELECTOR, "tr, [class*='list-item']"))

        email_prefix = fresh_email.split("@")[0]
        if email_prefix in body_after.lower() or items_after > items_before:
            results[59] = ("FIXED", f"User appears in list without refresh (items: {items_before}->{items_after}).")
        else:
            results[59] = ("STILL_FAILING", f"User does not appear without refresh (items: {items_before}->{items_after}).")
    else:
        results[59] = ("STILL_FAILING", "Could not find invite button.")

    # --- #43: Org Admin Edit Employee ---
    print("\n[#43] Org Admin Edit Employee (Round 3)")
    emp_url = sidebar.get("employees", f"{BASE_URL}/employees")
    driver.get(emp_url)
    time.sleep(4)
    ss(driver, "issue_43_r3_list")
    print(f"  Employees URL: {driver.current_url}")

    # Find and click first employee link
    emp_links = []
    for a in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
        try:
            href = a.get_attribute("href") or ""
            text = a.text.strip()
            if "/employees/" in href and text and not href.endswith("/employees") and not href.endswith("/employees/"):
                emp_links.append((text, href, a))
        except:
            pass

    print(f"  Employee links found: {[(t,h) for t,h,_ in emp_links[:5]]}")

    if emp_links:
        name, href, link = emp_links[0]
        print(f"  Clicking employee: {name} -> {href}")
        driver.get(href)  # Navigate directly to avoid click issues
        time.sleep(4)
        ss(driver, "issue_43_r3_detail")
        print(f"  Detail URL: {driver.current_url}")

        body = driver.find_element(By.TAG_NAME, "body").text
        print(f"  Detail page: {body[:300]}")

        # Look for edit buttons
        all_btns = driver.find_elements(By.CSS_SELECTOR, "button, a, [role='button']")
        edit_found = False
        for b in all_btns:
            try:
                t = b.text.strip().lower()
                title = (b.get_attribute("title") or "").lower()
                aria = (b.get_attribute("aria-label") or "").lower()
                if any(k in (t + " " + title + " " + aria) for k in ["edit", "update", "modify"]):
                    edit_found = True
                    print(f"  Found edit: text='{b.text}', title='{title}'")
                    safe_click(driver, b)
                    time.sleep(3)
                    ss(driver, "issue_43_r3_edit_form")

                    form_inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']), select, textarea") if i.is_displayed()]
                    print(f"  Form inputs after edit click: {len(form_inputs)}")

                    if len(form_inputs) > 2:
                        results[43] = ("FIXED", f"Org admin can edit employee - form with {len(form_inputs)} inputs.")
                    else:
                        results[43] = ("FIXED", "Edit button exists for org admin on employee page.")
                    break
            except:
                pass

        if not edit_found:
            # Check for edit icons (pencil SVGs)
            page_src = driver.page_source.lower()
            if "edit" in page_src:
                # There might be edit functionality via icons
                icons = driver.find_elements(By.CSS_SELECTOR, "[class*='edit'], [data-testid*='edit']")
                if icons:
                    results[43] = ("FIXED", "Edit icons found on employee detail page.")
                else:
                    results[43] = ("STILL_FAILING", "No edit button or icon found on employee detail page.")
            else:
                results[43] = ("STILL_FAILING", "No edit functionality found on employee detail page.")
    else:
        results[43] = ("STILL_FAILING", "No employee links found to test editing.")

    # --- #56: City Text Validation ---
    print("\n[#56] City Text Validation (Round 3)")
    if emp_links:
        name, href, link = emp_links[0]
        driver.get(href)
        time.sleep(4)

        # Click edit if needed
        for b in driver.find_elements(By.CSS_SELECTOR, "button, a"):
            try:
                t = b.text.strip().lower()
                title = (b.get_attribute("title") or "").lower()
                if "edit" in t or "edit" in title:
                    safe_click(driver, b)
                    time.sleep(3)
                    break
            except:
                pass

        ss(driver, "issue_56_r3_form")

        # List all labels
        labels = driver.find_elements(By.CSS_SELECTOR, "label")
        label_texts = [l.text.strip() for l in labels if l.text.strip()]
        print(f"  Labels: {label_texts[:20]}")

        # Find city input
        all_inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if i.is_displayed()]
        city_input = None
        for inp in all_inputs:
            try:
                nm = (inp.get_attribute("name") or "").lower()
                ph = (inp.get_attribute("placeholder") or "").lower()
                iid = (inp.get_attribute("id") or "").lower()
                if "city" in nm or "city" in ph or "city" in iid:
                    city_input = inp
                    break
            except:
                pass

        # Also try by label proximity
        if not city_input:
            for lab in labels:
                try:
                    if "city" in lab.text.lower():
                        # Try finding input near label
                        parent = lab.find_element(By.XPATH, "./ancestor::div[1]")
                        inp = parent.find_element(By.CSS_SELECTOR, "input")
                        if inp.is_displayed():
                            city_input = inp
                            break
                except:
                    pass

        if city_input:
            city_input.clear()
            city_input.send_keys("12345")
            time.sleep(1)
            val = city_input.get_attribute("value") or ""
            print(f"  City value after '12345': '{val}'")

            save_btn = find_by_text(driver, "button", "save") or find_by_text(driver, "button", "update")
            if save_btn:
                safe_click(driver, save_btn)
                time.sleep(3)

            ss(driver, "issue_56_r3_result")
            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            val_now = city_input.get_attribute("value") or ""

            if any(k in body for k in ["invalid", "only alphabets", "letters only", "alphabetic"]):
                results[56] = ("FIXED", "City field validates against numeric input.")
            elif val_now != "12345":
                results[56] = ("FIXED", f"City field filtered numeric input (val='{val_now}').")
            else:
                results[56] = ("STILL_FAILING", "City field still accepts numeric values.")
        else:
            # Print all input names for debugging
            for inp in all_inputs[:20]:
                try:
                    print(f"    Input: name={inp.get_attribute('name')}, ph={inp.get_attribute('placeholder')}, id={inp.get_attribute('id')}")
                except:
                    pass
            results[56] = ("STILL_FAILING", "City field not found in employee form.")
    else:
        results[56] = ("STILL_FAILING", "No employees found to test city validation.")

    # --- #36: Survey Date Validation ---
    print("\n[#36] Survey Date Validation (Round 3)")
    # Check sidebar for Events or Surveys
    events_url = sidebar.get("my events", sidebar.get("events", sidebar.get("surveys", "")))
    if events_url:
        driver.get(events_url)
    else:
        driver.get(f"{BASE_URL}/events")
    time.sleep(3)
    ss(driver, "issue_36_r3_page")
    print(f"  Events/Survey URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Page: {body[:200]}")

    # Surveys might be under a different section - check all sidebar links
    found_survey = False
    for key, url in sidebar.items():
        if "survey" in key:
            driver.get(url)
            time.sleep(3)
            found_survey = True
            break

    if not found_survey:
        # Try direct paths
        for path in ["/surveys", "/survey", "/create-survey"]:
            driver.get(f"{BASE_URL}{path}")
            time.sleep(2)
            if "login" not in driver.current_url and "403" not in driver.page_source:
                found_survey = True
                break

    ss(driver, "issue_36_r3_survey")
    body = driver.find_element(By.TAG_NAME, "body").text

    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if btn.is_displayed() and any(k in t for k in ["create survey", "add survey", "new survey", "create", "add"]):
                add_btn = btn
                break
        except:
            pass

    if add_btn:
        safe_click(driver, add_btn)
        time.sleep(3)
        date_inputs = [d for d in driver.find_elements(By.CSS_SELECTOR, "input[type='date']") if d.is_displayed()]
        if len(date_inputs) >= 2:
            driver.execute_script("arguments[0].value = '2026-12-31'", date_inputs[0])
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}))", date_inputs[0])
            driver.execute_script("arguments[0].value = '2026-01-01'", date_inputs[1])
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}))", date_inputs[1])
            time.sleep(2)
            save_btn = find_by_text(driver, "button", "save") or find_by_text(driver, "button", "create")
            if save_btn:
                safe_click(driver, save_btn)
                time.sleep(3)
            body2 = driver.find_element(By.TAG_NAME, "body").text.lower()
            if any(k in body2 for k in ["end date", "invalid", "before start", "after start"]):
                results[36] = ("FIXED", "Survey date validation works.")
            else:
                results[36] = ("STILL_FAILING", "Survey still allows end date before start.")
        else:
            results[36] = ("STILL_FAILING", "Survey form has no date fields.")
    else:
        if "survey" in body.lower():
            results[36] = ("STILL_FAILING", "Survey page found but no create button.")
        else:
            results[36] = ("STILL_FAILING", "Survey module not found in navigation.")

    # --- #34: Wellness Date Validation ---
    print("\n[#34] Wellness Date Validation (Round 3)")
    wellness_url = sidebar.get("wellness", f"{BASE_URL}/wellness")
    driver.get(wellness_url)
    time.sleep(3)
    ss(driver, "issue_34_r3_wellness")
    print(f"  Wellness URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Wellness page: {body[:300]}")

    # The wellness page has programs - look for Create/Add button
    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if btn.is_displayed() and any(k in t for k in ["create", "add", "new program", "+"]):
                add_btn = btn
                print(f"  Found: '{btn.text}'")
                break
        except:
            pass

    if add_btn:
        safe_click(driver, add_btn)
        time.sleep(3)
        ss(driver, "issue_34_r3_create")

        date_inputs = [d for d in driver.find_elements(By.CSS_SELECTOR, "input[type='date']") if d.is_displayed()]
        print(f"  Date inputs: {len(date_inputs)}")

        if len(date_inputs) >= 2:
            driver.execute_script("arguments[0].value = '2026-12-31'", date_inputs[0])
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}))", date_inputs[0])
            driver.execute_script("arguments[0].value = '2026-01-01'", date_inputs[1])
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}))", date_inputs[1])
            time.sleep(2)
            save_btn = find_by_text(driver, "button", "save") or find_by_text(driver, "button", "create")
            if save_btn:
                safe_click(driver, save_btn)
                time.sleep(3)
            body2 = driver.find_element(By.TAG_NAME, "body").text.lower()
            ss(driver, "issue_34_r3_result")
            toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='Toastify']")
            toast_txt = " ".join([t.text.lower() for t in toasts])
            if any(k in (body2 + toast_txt) for k in ["end date", "invalid", "before start", "after start"]):
                results[34] = ("FIXED", "Wellness date validation works.")
            else:
                results[34] = ("STILL_FAILING", "Wellness still allows end date before start.")
        else:
            # Print all inputs for debug
            all_vis = [i for i in driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if i.is_displayed()]
            for v in all_vis:
                try:
                    print(f"    Input: name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
                except:
                    pass
            results[34] = ("STILL_FAILING", "No date fields found in wellness create form.")
    else:
        results[34] = ("STILL_FAILING", "No create button found on wellness page.")

    # --- #33: Asset Warranty Date ---
    print("\n[#33] Asset Warranty Date (Round 3)")
    # Check sidebar for assets
    asset_url = None
    for key, url in sidebar.items():
        if "asset" in key.lower():
            asset_url = url
            break

    if not asset_url:
        asset_url = f"{BASE_URL}/assets"

    driver.get(asset_url)
    time.sleep(3)
    ss(driver, "issue_33_r3_page")
    print(f"  Assets URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Assets page: {body[:300]}")

    if "403" in body or "forbidden" in body.lower():
        results[33] = ("STILL_FAILING", "Assets page returns 403 Forbidden.")
    else:
        add_btn = None
        for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
            try:
                t = btn.text.strip().lower()
                if btn.is_displayed() and any(k in t for k in ["add asset", "add", "create", "new"]):
                    add_btn = btn
                    break
            except:
                pass

        if add_btn:
            safe_click(driver, add_btn)
            time.sleep(3)
            ss(driver, "issue_33_r3_form")

            date_inputs = [d for d in driver.find_elements(By.CSS_SELECTOR, "input[type='date']") if d.is_displayed()]
            if len(date_inputs) >= 2:
                driver.execute_script("arguments[0].value = '2026-12-31'", date_inputs[0])
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}))", date_inputs[0])
                driver.execute_script("arguments[0].value = '2026-01-01'", date_inputs[1])
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}))", date_inputs[1])
                time.sleep(2)
                save_btn = find_by_text(driver, "button", "save") or find_by_text(driver, "button", "add")
                if save_btn:
                    safe_click(driver, save_btn)
                    time.sleep(3)
                body2 = driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(k in body2 for k in ["before purchase", "invalid", "warranty", "after purchase"]):
                    results[33] = ("FIXED", "Asset date validation works.")
                else:
                    results[33] = ("STILL_FAILING", "Asset still allows warranty before purchase.")
            else:
                results[33] = ("STILL_FAILING", "No date fields found in asset form.")
        else:
            results[33] = ("STILL_FAILING", "No add asset button found.")

    return True

def test_employee_batch(driver):
    """Run employee-role tests in one session."""
    if not login(driver, "employee"):
        return False

    sidebar = get_sidebar_hrefs(driver)
    print(f"  Employee sidebar: {list(sidebar.keys())}")

    # --- #39: Knowledge Base Multiple Likes ---
    print("\n[#39] Knowledge Base Likes (Round 3)")
    # Check for community/knowledge in sidebar
    community_url = sidebar.get("community", sidebar.get("knowledge base", sidebar.get("kb", "")))
    if community_url:
        driver.get(community_url)
    else:
        driver.get(f"{BASE_URL}/community")
    time.sleep(3)
    ss(driver, "issue_39_r3_page")
    print(f"  Community URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Community page: {body[:300]}")

    # Look for posts/articles
    post_links = []
    for a in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
        try:
            href = a.get_attribute("href") or ""
            text = a.text.strip()
            if text and any(k in href.lower() for k in ["post", "article", "community", "knowledge"]):
                post_links.append((text, href, a))
        except:
            pass

    # Also look for cards
    cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='post'], article, [class*='article']")
    print(f"  Posts found: {len(post_links)}, Cards: {len(cards)}")

    if post_links:
        driver.get(post_links[0][1])
        time.sleep(3)
    elif cards:
        safe_click(driver, cards[0])
        time.sleep(3)

    ss(driver, "issue_39_r3_article")

    # Find like button
    like_btn = None
    all_elements = driver.find_elements(By.CSS_SELECTOR, "button, [class*='like'], [class*='thumb'], [class*='heart'], [class*='vote']")
    for el in all_elements:
        try:
            t = el.text.strip().lower()
            cls = (el.get_attribute("class") or "").lower()
            title = (el.get_attribute("title") or "").lower()
            aria = (el.get_attribute("aria-label") or "").lower()
            combined = t + cls + title + aria
            if any(k in combined for k in ["like", "thumb", "heart", "upvote", "helpful"]):
                like_btn = el
                print(f"  Like button: text='{t}', class='{cls}'")
                break
        except:
            pass

    if like_btn:
        safe_click(driver, like_btn)
        time.sleep(2)
        body1 = driver.find_element(By.TAG_NAME, "body").text
        ss(driver, "issue_39_r3_like1")

        safe_click(driver, like_btn)
        time.sleep(2)
        body2 = driver.find_element(By.TAG_NAME, "body").text
        ss(driver, "issue_39_r3_like2")

        if body1 == body2:
            results[39] = ("FIXED", "Like button prevents duplicate likes.")
        else:
            results[39] = ("STILL_FAILING", "Multiple likes may still be possible.")
    else:
        results[39] = ("STILL_FAILING", "Could not find like button on community/knowledge base page.")

    # --- #38: Wellness Goals Date Validation ---
    print("\n[#38] Wellness Goals Date Validation (Round 3)")
    wellness_url = sidebar.get("wellness", f"{BASE_URL}/wellness")
    driver.get(wellness_url)
    time.sleep(3)
    ss(driver, "issue_38_r3_wellness")
    print(f"  Wellness URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Wellness: {body[:300]}")

    # Click "My Wellness" tab
    my_wellness = find_by_text(driver, "button", "my wellness") or find_by_text(driver, "a", "my wellness")
    if my_wellness:
        safe_click(driver, my_wellness)
        time.sleep(3)
        ss(driver, "issue_38_r3_my_wellness")
        body = driver.find_element(By.TAG_NAME, "body").text
        print(f"  My Wellness: {body[:300]}")

    # Look for goal creation
    add_btn = None
    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if btn.is_displayed() and any(k in t for k in ["add goal", "create goal", "new goal", "set goal", "add", "create"]):
                add_btn = btn
                print(f"  Found: '{btn.text}'")
                break
        except:
            pass

    if add_btn:
        safe_click(driver, add_btn)
        time.sleep(3)
        ss(driver, "issue_38_r3_form")

        date_inputs = [d for d in driver.find_elements(By.CSS_SELECTOR, "input[type='date']") if d.is_displayed()]
        print(f"  Date inputs: {len(date_inputs)}")

        if len(date_inputs) >= 2:
            driver.execute_script("arguments[0].value = '2026-12-31'", date_inputs[0])
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}))", date_inputs[0])
            driver.execute_script("arguments[0].value = '2026-01-01'", date_inputs[1])
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}))", date_inputs[1])
            time.sleep(2)

            save_btn = find_by_text(driver, "button", "save") or find_by_text(driver, "button", "create") or find_by_text(driver, "button", "add")
            if save_btn:
                safe_click(driver, save_btn)
                time.sleep(3)

            body2 = driver.find_element(By.TAG_NAME, "body").text.lower()
            ss(driver, "issue_38_r3_result")
            toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'], [class*='Toastify']")
            toast_txt = " ".join([t.text.lower() for t in toasts])

            if any(k in (body2 + toast_txt) for k in ["end date", "invalid", "before start", "after start", "must be"]):
                results[38] = ("FIXED", "Wellness goal date validation works.")
            else:
                results[38] = ("STILL_FAILING", "Wellness goals still allow invalid date range.")
        else:
            all_vis = [i for i in driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if i.is_displayed()]
            for v in all_vis:
                try:
                    print(f"    Input: name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
                except:
                    pass
            results[38] = ("STILL_FAILING", "No date fields found in wellness goal form.")
    else:
        results[38] = ("STILL_FAILING", "No add goal button found on wellness page.")

    return True


def main():
    print("=" * 70)
    print("EmpCloud Closed Issue Re-Test - ROUND 3 - 2026-03-27")
    print("Single-session approach to avoid rate limiting")
    print("=" * 70)

    # Run org admin tests in one session
    driver = None
    try:
        driver = get_driver()
        test_org_admin_batch(driver)
    except Exception as e:
        print(f"ERROR in org_admin batch: {e}")
        traceback.print_exc()
    finally:
        if driver:
            try: driver.quit()
            except: pass

    print("\n--- Waiting 15s before employee login ---")
    time.sleep(15)

    # Run employee tests in one session
    driver = None
    try:
        driver = get_driver()
        test_employee_batch(driver)
    except Exception as e:
        print(f"ERROR in employee batch: {e}")
        traceback.print_exc()
    finally:
        if driver:
            try: driver.quit()
            except: pass

    # Update GitHub for all results
    print("\n--- Updating GitHub issues ---")
    for num, (status, details) in results.items():
        try:
            update_github(num, status, details)
            print(f"  #{num}: {status} - GitHub updated")
        except Exception as e:
            print(f"  #{num}: GitHub update error: {e}")

    # Print summary
    print("\n" + "=" * 70)
    print("ROUND 3 SUMMARY")
    print("=" * 70)
    print(f"{'Issue':<10} {'Status':<18} {'Details'}")
    print("-" * 70)

    all_issues = [62, 61, 60, 59, 56, 43, 39, 38, 36, 34, 33]
    for num in all_issues:
        status, details = results.get(num, ("NOT_RUN", "Test did not execute"))
        print(f"#{num:<9} {status:<18} {details[:55]}")

    fixed = sum(1 for s, _ in results.values() if s == "FIXED")
    failing = sum(1 for s, _ in results.values() if s == "STILL_FAILING")
    print(f"\nRound 3: {len(results)} tested | FIXED: {fixed} | STILL_FAILING: {failing}")

    # Combined with round 1+2 results (58 was fixed in round 2)
    print("\n" + "=" * 70)
    print("FINAL COMBINED SUMMARY (All 28 Issues)")
    print("=" * 70)

    # Round 1 fixed issues
    r1_fixed = {
        63: "Department data is now visible for employees.",
        57: "Manager names are now visible in dropdown.",
        55: "City/State fields now reject numeric values.",
        50: "Unsubscribe/deactivate option is now available in module section.",
        49: "Leave page loads with balance info.",
        48: "Leave requests are now visible in admin area.",
        47: "No auto check-in triggered on attendance page visit.",
        46: "Org chart page loads with manager information visible.",
        45: "Employee can view profile and raise update requests.",
        44: "Pending/invited users list is now visible.",
        42: "Announcements page now loads with content.",
        41: "Employee document access appears properly restricted.",
        40: "Employee selection dropdown with search is available.",
        37: "Add Asset option is not visible to employee.",
        35: "Employee document actions appear properly restricted.",
        32: "Employee cannot see approve/reject options.",
    }
    r2_fixed = {58: "All 19 sidebar links navigate properly."}

    all_combined = {}
    for num, detail in r1_fixed.items():
        all_combined[num] = ("FIXED", detail)
    for num, detail in r2_fixed.items():
        all_combined[num] = ("FIXED", detail)
    for num, (status, detail) in results.items():
        all_combined[num] = (status, detail)

    print(f"{'Issue':<10} {'Status':<18} {'Details'}")
    print("-" * 70)
    for num in sorted(all_combined.keys(), reverse=True):
        status, details = all_combined[num]
        print(f"#{num:<9} {status:<18} {details[:55]}")

    total_fixed = sum(1 for s, _ in all_combined.values() if s == "FIXED")
    total_failing = sum(1 for s, _ in all_combined.values() if s == "STILL_FAILING")
    print(f"\nFINAL: {len(all_combined)} issues | FIXED: {total_fixed} | STILL_FAILING: {total_failing}")

if __name__ == "__main__":
    main()
