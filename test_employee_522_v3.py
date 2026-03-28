"""
Employee 522 Profile Test - V3 (Focused)
Fixes: proper tab clicking with content change detection, Edit button deep investigation
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os, json, time, requests, traceback, base64, glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_ID = 522
SS_DIR = r"C:\emptesting\screenshots\employee_522"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SS_DIR, exist_ok=True)
BUGS = []
RESULTS = []

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def record(test, status, details=""):
    RESULTS.append({"test": test, "status": status, "details": details})
    log(f"  [{status}] {test}: {details}")

def bug(title, details, ss=None):
    BUGS.append({"title": title, "details": details, "screenshot": ss})
    log(f"  [BUG] {title}")

def ss(driver, name):
    p = os.path.join(SS_DIR, f"{name}.png")
    driver.save_screenshot(p)
    log(f"    SS: {name}.png")
    return p

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage","--window-size=1920,1080","--disable-gpu","--ignore-certificate-errors"]:
        opts.add_argument(a)
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(2)
    return d

def login(driver):
    log("Login...")
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))).send_keys(ADMIN_EMAIL)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(ADMIN_PASS)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    log(f"  Logged in: {driver.current_url}")

def go_profile(driver):
    driver.get(f"{BASE_URL}/employees/{EMP_ID}")
    time.sleep(4)

def get_main_content_text(driver):
    """Get the text from the main content area (not sidebar)"""
    try:
        # Try to get just the main content panel, not the full body
        for sel in ["main", "[class*='content']", "[class*='main']", ".page-content", "#content"]:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                t = el.text
                if len(t) > 100:
                    return t
    except:
        pass
    return driver.find_element(By.TAG_NAME, "body").text

def test_tabs(driver):
    log("\n=== TAB TESTING (with content verification) ===")
    go_profile(driver)

    # First, get the page source to understand tab structure
    page_src = driver.page_source

    # Find all tab-like elements and dump their info
    log("  Analyzing tab elements...")
    tab_candidates = driver.find_elements(By.CSS_SELECTOR,
        "button, a, span, div, li")

    tab_texts_found = []
    target_tabs = ["personal", "education", "experience", "documents", "document",
                   "address", "custom", "dependents", "dependencies"]

    for el in tab_candidates:
        try:
            txt = el.text.strip().lower()
            if txt and any(t in txt for t in target_tabs) and len(txt) < 30:
                tag = el.tag_name
                cls = el.get_attribute("class") or ""
                role = el.get_attribute("role") or ""
                href = el.get_attribute("href") or ""
                aria = el.get_attribute("aria-selected") or ""
                tab_texts_found.append({
                    "text": el.text.strip(), "tag": tag, "class": cls[:80],
                    "role": role, "href": href[:80], "aria_selected": aria,
                    "displayed": el.is_displayed(), "enabled": el.is_enabled()
                })
        except:
            pass

    log(f"  Tab-like elements found: {len(tab_texts_found)}")
    for t in tab_texts_found:
        log(f"    '{t['text']}' tag={t['tag']} class={t['class'][:50]} role={t['role']} displayed={t['displayed']}")

    # Screenshot current state (Personal tab should be default)
    ss(driver, "v3_01_personal_default")
    initial_content = get_main_content_text(driver)
    log(f"  Initial content length: {len(initial_content)}")
    log(f"  Initial content preview: {initial_content[:200]}")

    # Now click each tab carefully
    tabs_to_click = ["Education", "Experience", "Documents", "Dependents", "Addresses", "Custom Fields"]

    for tab_name in tabs_to_click:
        log(f"\n  --- Clicking: {tab_name} ---")
        go_profile(driver)  # Reset to profile page each time to avoid stale state
        time.sleep(2)

        # Find the tab element more precisely
        clicked = False
        click_el = None

        # Strategy 1: Find by exact/partial text in elements near the tab bar area
        all_els = driver.find_elements(By.XPATH, f"//*[normalize-space(text())='{tab_name}' or contains(text(),'{tab_name}')]")
        for el in all_els:
            try:
                if el.is_displayed() and el.text.strip():
                    tag = el.tag_name
                    log(f"    Found '{el.text.strip()}' ({tag}) - clicking...")

                    # Scroll into view first
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.5)

                    # Get content before click
                    before = get_main_content_text(driver)[:300]

                    # Click
                    try:
                        el.click()
                    except:
                        driver.execute_script("arguments[0].click();", el)

                    time.sleep(3)

                    # Get content after click
                    after = get_main_content_text(driver)[:300]

                    content_changed = (before != after)
                    log(f"    Content changed after click: {content_changed}")
                    if not content_changed:
                        log(f"    Before: {before[:100]}")
                        log(f"    After:  {after[:100]}")

                    ss_name = f"v3_tab_{tab_name.lower().replace(' ','_')}"
                    ss(driver, ss_name)

                    # Scroll down for full view
                    driver.execute_script("window.scrollTo(0, 400)")
                    time.sleep(0.5)
                    ss(driver, f"{ss_name}_scroll")
                    driver.execute_script("window.scrollTo(0, 0)")

                    if content_changed:
                        record(f"Tab - {tab_name}", "PASS", f"Tab clicked, content changed")
                    else:
                        record(f"Tab - {tab_name}", "WARN", f"Tab clicked but content appears unchanged")

                    clicked = True
                    break
            except Exception as e:
                log(f"    Click error: {e}")

        if not clicked:
            record(f"Tab - {tab_name}", "WARN", f"Could not find/click '{tab_name}'")

def test_edit_deep(driver):
    log("\n=== EDIT BUTTON DEEP INVESTIGATION ===")
    go_profile(driver)

    # Capture all buttons on page
    buttons = driver.find_elements(By.TAG_NAME, "button")
    log(f"  All buttons on page: {len(buttons)}")
    for b in buttons:
        try:
            if b.is_displayed():
                txt = b.text.strip()
                cls = (b.get_attribute("class") or "")[:60]
                log(f"    Button: '{txt}' class='{cls}'")
        except:
            pass

    # Find Edit Profile specifically
    edit_btn = None
    for b in buttons:
        try:
            if b.is_displayed() and "edit" in (b.text or "").lower():
                edit_btn = b
                break
        except:
            pass

    if not edit_btn:
        # Try links
        links = driver.find_elements(By.TAG_NAME, "a")
        for a in links:
            try:
                if a.is_displayed() and "edit" in (a.text or "").lower():
                    edit_btn = a
                    log(f"  Found edit as link: '{a.text}' href='{a.get_attribute('href')}'")
                    break
            except:
                pass

    if not edit_btn:
        record("Edit Button", "FAIL", "No edit button found")
        return

    log(f"  Edit button: '{edit_btn.text}' tag={edit_btn.tag_name}")
    log(f"  Edit button class: {edit_btn.get_attribute('class')}")
    log(f"  Edit button onclick: {edit_btn.get_attribute('onclick')}")

    # Get page state before
    before_url = driver.current_url
    before_html_len = len(driver.page_source)
    before_inputs = len(driver.find_elements(By.CSS_SELECTOR, "input, textarea, select"))

    ss(driver, "v3_edit_01_before")

    # Click with JS event listener check
    driver.execute_script("""
        var btn = arguments[0];
        console.log('Clicking edit button:', btn.textContent);
        btn.click();
    """, edit_btn)

    time.sleep(4)
    ss(driver, "v3_edit_02_after_click")

    after_url = driver.current_url
    after_html_len = len(driver.page_source)
    after_inputs = len(driver.find_elements(By.CSS_SELECTOR, "input, textarea, select"))

    log(f"  URL: {before_url} -> {after_url}")
    log(f"  HTML length: {before_html_len} -> {after_html_len}")
    log(f"  Input count: {before_inputs} -> {after_inputs}")

    # Check for modals
    modals = driver.find_elements(By.CSS_SELECTOR, "[class*='modal'], [class*='Modal'], [role='dialog'], [class*='drawer'], [class*='Drawer']")
    visible_modals = [m for m in modals if m.is_displayed()]
    log(f"  Visible modals/dialogs: {len(visible_modals)}")

    if visible_modals:
        for m in visible_modals:
            ss(driver, "v3_edit_03_modal")
            record("Edit Modal/Dialog", "PASS", "Edit opened a modal/dialog")
            # Check for inputs in modal
            modal_inputs = m.find_elements(By.CSS_SELECTOR, "input, textarea, select")
            log(f"  Inputs in modal: {len(modal_inputs)}")

    # Check if any new visible inputs appeared
    all_inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']), textarea, select")
    visible = [i for i in all_inputs if i.is_displayed() and i.is_enabled()]
    log(f"  Visible+enabled inputs after edit: {len(visible)}")

    for inp in visible[:10]:
        name = inp.get_attribute("name") or ""
        ph = inp.get_attribute("placeholder") or ""
        val = inp.get_attribute("value") or ""
        typ = inp.get_attribute("type") or ""
        log(f"    Input: name='{name}' placeholder='{ph}' type='{typ}' value='{val[:30]}'")

    if len(visible) > before_inputs:
        record("Edit Form", "PASS", f"New input fields appeared ({before_inputs} -> {len(visible)})")
    elif after_url != before_url:
        record("Edit Navigation", "PASS", f"Navigated to: {after_url}")
        ss(driver, "v3_edit_03_new_page")
    else:
        # Maybe it switches the profile to inline edit mode
        # Wait longer
        time.sleep(3)
        ss(driver, "v3_edit_03_wait")
        late_inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']), textarea, select") if i.is_displayed()]
        log(f"  After extra wait, visible inputs: {len(late_inputs)}")

        if len(late_inputs) > before_inputs:
            record("Edit Form (Delayed)", "PASS", f"Edit form appeared after delay")
        else:
            record("Edit Form", "FAIL", "Edit button click produces no visible change - no form, no modal, no navigation")
            bug("Employee 522: Edit Profile button non-functional",
                f"Clicking 'Edit Profile' on /employees/{EMP_ID} does not open an edit form, modal, or navigate to edit page. "
                f"Button is visible and clickable but produces no UI change. Inputs before={before_inputs} after={len(late_inputs)} "
                f"URL unchanged at {after_url}",
                "v3_edit_02_after_click.png")

def test_personal_tab_data(driver):
    log("\n=== PERSONAL TAB DATA VERIFICATION ===")
    go_profile(driver)

    body = driver.find_element(By.TAG_NAME, "body").text
    lines = body.split('\n')

    # Parse key-value pairs from the page
    log("  Page text lines (relevant):")
    fields_found = {}
    target_labels = ["Personal Email", "Contact Number", "Gender", "Date of Birth",
                     "Blood Group", "Marital Status", "Nationality", "Aadhar Number",
                     "PAN Number", "Passport Number", "Passport Expiry", "Visa Status",
                     "Visa Expiry", "Reporting Manager", "Emp Code", "Designation"]

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped == '-':
            continue
        for label in target_labels:
            if label.lower() in stripped.lower():
                # Value is likely on the same line after label, or next non-empty line
                value = stripped.replace(label, "").strip()
                if not value or value == '-':
                    for j in range(i+1, min(i+3, len(lines))):
                        v = lines[j].strip()
                        if v and v != '-':
                            value = v
                            break
                fields_found[label] = value if value and value != '-' else "(empty)"
                break

    log(f"  Fields found on Personal tab:")
    for k, v in fields_found.items():
        log(f"    {k}: {v}")

    # Cross-check with API data
    api_data = {
        "first_name": "Ananya", "last_name": "Gupta",
        "email": "ananya@technova.in", "emp_code": "TN-001",
        "contact_number": "+91 7885781382",
        "date_of_birth": "1990-05-15", "gender": "female",
        "designation": "Tech Lead", "reporting_manager_id": 524
    }

    # Verify contact number
    if "Contact Number" in fields_found:
        ui_phone = fields_found["Contact Number"]
        api_phone = api_data["contact_number"]
        if api_phone in ui_phone or ui_phone in api_phone:
            record("Data Match - Phone", "PASS", f"UI='{ui_phone}' matches API='{api_phone}'")
        else:
            if ui_phone != "(empty)":
                record("Data Match - Phone", "WARN", f"UI='{ui_phone}' vs API='{api_phone}'")

    # Verify gender
    if "Gender" in fields_found:
        ui_gender = fields_found["Gender"].lower()
        if api_data["gender"] in ui_gender or ui_gender in api_data["gender"]:
            record("Data Match - Gender", "PASS", f"Gender: {ui_gender}")

    # Verify Reporting Manager shows
    if "Reporting Manager" in fields_found:
        record("Reporting Manager", "PASS", f"RM: {fields_found['Reporting Manager']}")

    # Verify Emp Code
    if "Emp Code" in fields_found:
        record("Emp Code", "PASS", f"Emp Code: {fields_found['Emp Code']}")

    ss(driver, "v3_personal_data_verified")

def upload_to_github():
    log("\n=== Upload to GitHub ===")
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    files = glob.glob(os.path.join(SS_DIR, "v3_*.*"))
    uploaded = 0
    for fpath in files:
        fname = os.path.basename(fpath)
        gh_path = f"test-artifacts/employee-522/{fname}"
        try:
            with open(fpath, "rb") as f:
                content = base64.b64encode(f.read()).decode()
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{gh_path}"
            check = requests.get(url, headers=headers, timeout=10)
            sha = check.json().get("sha") if check.status_code == 200 else None
            payload = {"message": f"Employee 522 v3: {fname}", "content": content}
            if sha:
                payload["sha"] = sha
            r = requests.put(url, json=payload, headers=headers, timeout=30)
            if r.status_code in [200, 201]:
                uploaded += 1
            else:
                log(f"  Failed {fname}: {r.status_code}")
        except Exception as e:
            log(f"  Error {fname}: {e}")
    log(f"  Uploaded {uploaded}/{len(files)} v3 files")

def main():
    log("=" * 60)
    log("EMPLOYEE 522 PROFILE TEST - V3 (FOCUSED)")
    log("=" * 60)

    driver = None
    try:
        driver = get_driver()
        login(driver)

        test_personal_tab_data(driver)
        test_tabs(driver)
        test_edit_deep(driver)

    except Exception as e:
        log(f"ERROR: {e}")
        traceback.print_exc()
        if driver:
            ss(driver, "v3_99_error")
    finally:
        if driver:
            driver.quit()

    upload_to_github()

    # Summary
    log("\n" + "=" * 60)
    log("V3 SUMMARY")
    log("=" * 60)
    p = sum(1 for r in RESULTS if r["status"] == "PASS")
    f = sum(1 for r in RESULTS if r["status"] == "FAIL")
    w = sum(1 for r in RESULTS if r["status"] == "WARN")
    log(f"Total: {p} PASS, {f} FAIL, {w} WARN ({len(RESULTS)})")
    log(f"Bugs: {len(BUGS)}")
    for r in RESULTS:
        log(f"  [{r['status']}] {r['test']}: {r['details']}")
    if BUGS:
        log("\nBugs:")
        for b in BUGS:
            log(f"  - {b['title']}: {b['details'][:120]}")

    with open(os.path.join(SS_DIR, "test_results_v3.json"), 'w') as f_out:
        json.dump({"results": RESULTS, "bugs": BUGS}, f_out, indent=2)

if __name__ == "__main__":
    main()
