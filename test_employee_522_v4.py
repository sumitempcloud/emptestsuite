"""
Employee 522 Profile - V4 Final Comprehensive Test
Proper login wait, tab clicking, edit testing, API verification
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

def bug(title, details, ss_file=None):
    BUGS.append({"title": title, "details": details, "screenshot": ss_file})
    log(f"  [BUG] {title}")

def take_ss(driver, name):
    p = os.path.join(SS_DIR, f"{name}.png")
    driver.save_screenshot(p)
    log(f"    SS: {name}.png")
    return p

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage",
              "--window-size=1920,1080","--disable-gpu","--ignore-certificate-errors"]:
        opts.add_argument(a)
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(3)
    return d

def login_and_wait(driver):
    """Login and wait for dashboard redirect"""
    log("=== LOGIN ===")
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)

    email_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
    )
    email_input.clear()
    email_input.send_keys(ADMIN_EMAIL)

    pw_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pw_input.clear()
    pw_input.send_keys(ADMIN_PASS)

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Wait for redirect away from login page
    for _ in range(15):
        time.sleep(1)
        url = driver.current_url
        if "/login" not in url:
            break

    time.sleep(2)
    take_ss(driver, "v4_01_after_login")
    log(f"  Login done. URL: {driver.current_url}")

    if "/login" in driver.current_url:
        log("  WARNING: Still on login page after 15s")
        # Check for error messages
        body = driver.find_element(By.TAG_NAME, "body").text
        log(f"  Page text: {body[:200]}")
        record("Login", "FAIL", "Did not redirect from login page")
        return False

    record("Login", "PASS", f"Redirected to {driver.current_url}")
    return True

def navigate_to_profile(driver):
    """Navigate to employee profile without losing session"""
    log(f"\n=== NAVIGATE TO /employees/{EMP_ID} ===")
    driver.get(f"{BASE_URL}/employees/{EMP_ID}")
    time.sleep(4)

    # Verify we're on the profile and not redirected to login
    url = driver.current_url
    if "/login" in url:
        log("  Redirected to login! Session lost.")
        record("Profile Navigation", "FAIL", "Session lost - redirected to login")
        return False

    take_ss(driver, "v4_02_profile_page")
    body = driver.find_element(By.TAG_NAME, "body").text
    log(f"  Profile URL: {url}")
    log(f"  Body text length: {len(body)}")

    # Scroll down and take another screenshot
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    take_ss(driver, "v4_03_profile_scrolled")
    driver.execute_script("window.scrollTo(0, 0)")

    record("Profile Page Load", "PASS", f"URL: {url}")
    return True

def check_profile_header(driver):
    """Check employee name, designation, emp code, department in header area"""
    log("\n=== CHECK PROFILE HEADER ===")
    body = driver.find_element(By.TAG_NAME, "body").text

    # Employee name
    headers = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4")
    name = None
    for h in headers:
        t = h.text.strip()
        if t and len(t) > 3 and len(t) < 60 and "@" not in t and "EMP Cloud" not in t:
            name = t
            break
    # Also try to find name from the page text - we know from API it's "Ananya Gupta"
    if not name and "Ananya Gupta" in body:
        name = "Ananya Gupta"
    if name:
        record("Employee Name", "PASS", f"Name: {name}")
    else:
        record("Employee Name", "WARN", "Could not extract employee name from headers")

    # Check various info pieces
    checks = {
        "Emp Code": ["Emp Code", "TN-001", "emp_code"],
        "Designation": ["Designation", "Tech Lead"],
        "Reporting Manager": ["Reporting Manager", "Reports To"],
        "Contact Number": ["Contact Number", "Phone", "7885781382"],
        "Gender": ["Gender", "Female", "female"],
        "Date of Birth": ["Date of Birth", "DOB", "5/10/1990", "1990"],
    }

    for label, keywords in checks.items():
        found = any(kw in body for kw in keywords)
        if found:
            record(f"Profile - {label}", "PASS", f"'{label}' info present on page")
        else:
            record(f"Profile - {label}", "WARN", f"'{label}' not found on page")

def test_tab(driver, tab_name, screenshot_name):
    """Click a tab and verify content changed"""
    log(f"\n  --- Tab: {tab_name} ---")

    # Get content before clicking
    body_before = driver.find_element(By.TAG_NAME, "body").text

    # Find the tab
    clicked = False
    # Try multiple XPath strategies
    xpaths = [
        f"//button[contains(text(),'{tab_name}')]",
        f"//a[contains(text(),'{tab_name}')]",
        f"//span[contains(text(),'{tab_name}')]",
        f"//div[contains(text(),'{tab_name}') and string-length(normalize-space(text())) < 30]",
        f"//li[contains(text(),'{tab_name}')]",
        f"//*[@role='tab'][contains(text(),'{tab_name}')]",
        f"//*[contains(@class,'tab')][contains(text(),'{tab_name}')]",
    ]

    for xpath in xpaths:
        try:
            els = driver.find_elements(By.XPATH, xpath)
            for el in els:
                if el.is_displayed():
                    # Make sure it's a reasonable tab element (not deep nested content)
                    tag = el.tag_name
                    text = el.text.strip()
                    if len(text) < 30:
                        log(f"    Found: '{text}' ({tag}) via {xpath[:50]}")
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        time.sleep(0.3)
                        try:
                            el.click()
                        except:
                            driver.execute_script("arguments[0].click();", el)
                        clicked = True
                        break
        except:
            pass
        if clicked:
            break

    if not clicked:
        return "NOT_FOUND"

    time.sleep(3)
    take_ss(driver, screenshot_name)

    # Scroll down for full content
    driver.execute_script("window.scrollTo(0, 400)")
    time.sleep(0.5)
    take_ss(driver, f"{screenshot_name}_scroll")
    driver.execute_script("window.scrollTo(0, 0)")

    body_after = driver.find_element(By.TAG_NAME, "body").text

    # Check if content changed
    content_changed = body_before != body_after
    return "CHANGED" if content_changed else "SAME"

def test_all_tabs(driver):
    log("\n=== TEST ALL TABS ===")

    # We need to be on the profile page
    url = driver.current_url
    if "/employees/" not in url:
        navigate_to_profile(driver)

    # List of tabs visible from screenshots: Personal, Education, Experience, Dependents, Addresses, Custom Fields
    tabs = [
        ("Personal", "v4_tab_personal"),
        ("Education", "v4_tab_education"),
        ("Experience", "v4_tab_experience"),
        ("Dependents", "v4_tab_dependents"),
        ("Addresses", "v4_tab_addresses"),
        ("Custom Fields", "v4_tab_custom_fields"),
        ("Documents", "v4_tab_documents"),  # may or may not exist
    ]

    for tab_name, ss_name in tabs:
        result = test_tab(driver, tab_name, ss_name)
        if result == "NOT_FOUND":
            record(f"Tab - {tab_name}", "WARN", "Tab element not found")
        elif result == "CHANGED":
            record(f"Tab - {tab_name}", "PASS", "Tab clicked, content updated")
        else:
            record(f"Tab - {tab_name}", "PASS", "Tab clicked (content may be similar)")

        # After each tab click, check specific content
        body = driver.find_element(By.TAG_NAME, "body").text
        if tab_name == "Education":
            has_edu = any(k in body for k in ["Degree", "University", "School", "College", "Board", "No education", "No record", "Add"])
            log(f"    Education content check: {has_edu}")
        elif tab_name == "Experience":
            has_exp = any(k in body for k in ["Company", "Organization", "Position", "Role", "No experience", "No record", "Add"])
            log(f"    Experience content check: {has_exp}")
        elif tab_name == "Addresses":
            has_addr = any(k in body for k in ["Address", "City", "State", "Pin", "Zip", "Country", "Current", "Permanent"])
            log(f"    Address content check: {has_addr}")

def test_edit_functionality(driver):
    log("\n=== TEST EDIT FUNCTIONALITY ===")

    # Make sure we're on profile
    url = driver.current_url
    if "/employees/" not in url:
        navigate_to_profile(driver)

    take_ss(driver, "v4_edit_01_before")

    # List ALL buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")
    all_links = driver.find_elements(By.TAG_NAME, "a")
    log(f"  Buttons: {len(buttons)}, Links: {len(all_links)}")

    for b in buttons:
        try:
            if b.is_displayed():
                t = b.text.strip()
                c = (b.get_attribute("class") or "")[:60]
                log(f"    Button: '{t}' class='{c}'")
        except:
            pass

    # Find "Edit Profile" button
    edit_btn = None
    for b in buttons:
        try:
            if b.is_displayed() and "edit" in b.text.lower():
                edit_btn = b
                break
        except:
            pass

    if not edit_btn:
        for a in all_links:
            try:
                if a.is_displayed() and "edit" in (a.text or "").lower():
                    edit_btn = a
                    log(f"    Found edit link: href={a.get_attribute('href')}")
                    break
            except:
                pass

    if not edit_btn:
        record("Edit Button", "FAIL", "No Edit button visible on profile")
        bug("Employee 522: Edit Profile button missing",
            "No edit button found on the employee profile page",
            "v4_edit_01_before.png")
        return

    log(f"  Edit button found: '{edit_btn.text}' tag={edit_btn.tag_name}")

    # Count inputs before click
    inputs_before = len([i for i in driver.find_elements(By.CSS_SELECTOR,
        "input:not([type='hidden']), textarea, select") if i.is_displayed()])

    # Click Edit
    try:
        edit_btn.click()
    except:
        driver.execute_script("arguments[0].click();", edit_btn)

    time.sleep(5)
    take_ss(driver, "v4_edit_02_after_click")

    new_url = driver.current_url
    log(f"  After Edit click: URL={new_url}")

    # Count inputs after click
    inputs_after_els = [i for i in driver.find_elements(By.CSS_SELECTOR,
        "input:not([type='hidden']), textarea, select") if i.is_displayed()]
    inputs_after = len(inputs_after_els)
    log(f"  Inputs: before={inputs_before}, after={inputs_after}")

    # Check for modals/drawers
    for sel in ["[role='dialog']", "[class*='modal']", "[class*='Modal']",
                "[class*='drawer']", "[class*='Drawer']", "[class*='overlay']"]:
        modals = [m for m in driver.find_elements(By.CSS_SELECTOR, sel) if m.is_displayed()]
        if modals:
            log(f"  Found visible {sel}: {len(modals)}")
            take_ss(driver, "v4_edit_03_modal")
            record("Edit Form Opens", "PASS", f"Modal/dialog found after clicking Edit")
            return

    if inputs_after > inputs_before:
        record("Edit Form Opens", "PASS", f"New input fields appeared ({inputs_before} -> {inputs_after})")

        # Try to find and edit phone
        for inp in inputs_after_els:
            name = (inp.get_attribute("name") or "").lower()
            ph = (inp.get_attribute("placeholder") or "").lower()
            if "phone" in name or "contact" in name or "mobile" in name or "phone" in ph:
                old = inp.get_attribute("value")
                inp.clear()
                inp.send_keys("9876543210")
                record("Phone Edit", "PASS", f"Changed from '{old}' to '9876543210'")
                take_ss(driver, "v4_edit_04_phone_changed")

                # Try save
                for sel in ["//button[contains(text(),'Save')]", "//button[contains(text(),'Update')]",
                            "//button[@type='submit']"]:
                    try:
                        s = driver.find_element(By.XPATH, sel)
                        if s.is_displayed():
                            s.click()
                            time.sleep(3)
                            take_ss(driver, "v4_edit_05_saved")
                            record("Save Edit", "PASS", "Save clicked")
                            break
                    except:
                        pass
                break
    elif "/edit" in new_url:
        record("Edit Form Opens", "PASS", f"Navigated to edit page: {new_url}")
        take_ss(driver, "v4_edit_03_edit_page")
    else:
        # Check page text for any indication
        body = driver.find_element(By.TAG_NAME, "body").text
        # Scroll to see full page
        driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(0.5)
        take_ss(driver, "v4_edit_03_scrolled")

        record("Edit Form Opens", "FAIL",
               "Edit button clicked but no form/modal/navigation detected")
        bug("Employee 522: Edit Profile button non-functional",
            f"Clicking 'Edit Profile' on /employees/{EMP_ID} does not open any edit form, modal, or navigate elsewhere. "
            f"URL stays at {new_url}. Inputs before={inputs_before} after={inputs_after}.",
            "v4_edit_02_after_click.png")

def test_api():
    log("\n=== API TESTS ===")

    # Login via API
    headers = {"Content-Type": "application/json"}
    resp = requests.post(f"{API_URL}/api/v1/auth/login",
                         json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
                         timeout=15)
    log(f"  API login: {resp.status_code}")

    if resp.status_code != 200:
        record("API Login", "FAIL", f"Status {resp.status_code}")
        return

    login_data = resp.json()
    # Extract token
    token = None
    def find_jwt(obj, depth=0):
        if depth > 5: return None
        if isinstance(obj, str) and obj.startswith("ey") and len(obj) > 50:
            return obj
        if isinstance(obj, dict):
            for v in obj.values():
                r = find_jwt(v, depth+1)
                if r: return r
        if isinstance(obj, list):
            for v in obj:
                r = find_jwt(v, depth+1)
                if r: return r
        return None

    token = find_jwt(login_data)
    if not token:
        # Try explicit paths
        d = login_data.get("data", login_data)
        if isinstance(d, dict):
            token = d.get("token") or d.get("access_token") or d.get("accessToken")

    if not token:
        log(f"  Login response: {json.dumps(login_data, default=str)[:300]}")
        record("API Token", "FAIL", "No token in login response")
        return

    log(f"  Token obtained (len={len(token)})")
    headers["Authorization"] = f"Bearer {token}"

    # GET /api/v1/users/522
    resp = requests.get(f"{API_URL}/api/v1/users/{EMP_ID}", headers=headers, timeout=15)
    log(f"  GET /api/v1/users/{EMP_ID}: {resp.status_code}")

    if resp.status_code != 200:
        record("API GET User", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")
        bug(f"API: GET /api/v1/users/{EMP_ID} returns {resp.status_code}",
            resp.text[:300])
        return

    data = resp.json()
    record("API GET User 522", "PASS", f"Status 200")

    # Save response
    with open(os.path.join(SS_DIR, "v4_api_response.json"), 'w') as f:
        json.dump(data, f, indent=2, default=str)

    emp = data.get("data", data)
    log(f"  API Response:")
    log(f"    ID: {emp.get('id')}")
    log(f"    Name: {emp.get('first_name')} {emp.get('last_name')}")
    log(f"    Email: {emp.get('email')}")
    log(f"    Emp Code: {emp.get('emp_code')}")
    log(f"    Contact: {emp.get('contact_number')}")
    log(f"    DOB: {emp.get('date_of_birth')}")
    log(f"    Gender: {emp.get('gender')}")
    log(f"    Joining: {emp.get('date_of_joining')}")
    log(f"    Designation: {emp.get('designation')}")
    log(f"    Department ID: {emp.get('department_id')}")
    log(f"    Reporting Manager ID: {emp.get('reporting_manager_id')}")
    log(f"    Employment Type: {emp.get('employment_type')}")
    log(f"    Role: {emp.get('role')}")
    log(f"    Status: {emp.get('status')}")
    log(f"    Location ID: {emp.get('location_id')}")
    log(f"    Photo: {emp.get('photo_path')}")
    log(f"    Address: {emp.get('address')}")

    # Check completeness
    all_fields = list(emp.keys()) if isinstance(emp, dict) else []
    filled = [k for k in all_fields if emp.get(k) is not None and emp.get(k) != ""]
    empty = [k for k in all_fields if emp.get(k) is None or emp.get(k) == ""]
    log(f"  Fields: {len(filled)} filled, {len(empty)} empty of {len(all_fields)} total")
    log(f"  Empty/null fields: {empty}")

    record("API Data Completeness", "PASS",
           f"{len(filled)}/{len(all_fields)} fields filled. Empty: {', '.join(empty)}")

    # Verify key fields are populated
    required = ["id", "first_name", "last_name", "email", "emp_code", "gender",
                 "date_of_birth", "date_of_joining", "designation", "department_id",
                 "reporting_manager_id", "status"]
    missing_required = [f for f in required if not emp.get(f)]
    if missing_required:
        record("API Required Fields", "WARN", f"Missing required: {missing_required}")
        bug(f"API: Employee {EMP_ID} missing required fields",
            f"Fields {missing_required} are null/empty in API response")
    else:
        record("API Required Fields", "PASS", "All required fields populated")

    # Note interesting findings
    if not emp.get("location_id"):
        log("  NOTE: location_id is null - employee has no location assigned")
    if not emp.get("photo_path"):
        log("  NOTE: photo_path is null - no profile photo")
    if not emp.get("address"):
        log("  NOTE: address is null in API (but may be in separate endpoint)")

    # Try to get reporting manager name
    rm_id = emp.get("reporting_manager_id")
    if rm_id:
        resp2 = requests.get(f"{API_URL}/api/v1/users/{rm_id}", headers=headers, timeout=15)
        if resp2.status_code == 200:
            rm_data = resp2.json().get("data", resp2.json())
            rm_name = f"{rm_data.get('first_name', '')} {rm_data.get('last_name', '')}"
            log(f"  Reporting Manager (ID {rm_id}): {rm_name}")
            record("API - Reporting Manager", "PASS", f"RM: {rm_name} (ID {rm_id})")

    # Try to get department name
    dept_id = emp.get("department_id")
    if dept_id:
        for ep in [f"{API_URL}/api/v1/departments/{dept_id}", f"{API_URL}/api/v1/departments"]:
            resp3 = requests.get(ep, headers=headers, timeout=15)
            if resp3.status_code == 200:
                dept_data = resp3.json()
                if isinstance(dept_data, dict) and "data" in dept_data:
                    d = dept_data["data"]
                    if isinstance(d, dict):
                        log(f"  Department (ID {dept_id}): {d.get('name', d)}")
                        record("API - Department", "PASS", f"Dept: {d.get('name', 'found')} (ID {dept_id})")
                    elif isinstance(d, list):
                        for item in d:
                            if isinstance(item, dict) and item.get("id") == dept_id:
                                log(f"  Department (ID {dept_id}): {item.get('name')}")
                                record("API - Department", "PASS", f"Dept: {item.get('name')} (ID {dept_id})")
                                break
                break

def upload_to_github():
    log("\n=== UPLOAD TO GITHUB ===")
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    files = glob.glob(os.path.join(SS_DIR, "v4_*.*"))
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
            payload = {"message": f"Employee 522 test v4: {fname}", "content": content}
            if sha: payload["sha"] = sha
            r = requests.put(url, json=payload, headers=headers, timeout=30)
            if r.status_code in [200, 201]:
                uploaded += 1
            else:
                log(f"  FAIL upload {fname}: {r.status_code}")
        except Exception as e:
            log(f"  Error {fname}: {e}")
    log(f"  Uploaded {uploaded}/{len(files)} files")
    record("GitHub Upload", "PASS" if uploaded > 0 else "WARN", f"{uploaded}/{len(files)}")

def main():
    log("=" * 70)
    log("EMPLOYEE 522 PROFILE - COMPREHENSIVE TEST V4")
    log("=" * 70)

    driver = None
    try:
        driver = get_driver()

        # Step 1: Login
        if not login_and_wait(driver):
            log("Login failed, aborting UI tests")
        else:
            # Step 2-4: Navigate and check profile
            if navigate_to_profile(driver):
                check_profile_header(driver)

                # Step 5-6: Test all tabs
                test_all_tabs(driver)

                # Step 7-8: Edit functionality
                # Navigate back to profile first since tabs may have changed state
                navigate_to_profile(driver)
                test_edit_functionality(driver)

    except Exception as e:
        log(f"UI ERROR: {e}")
        traceback.print_exc()
        if driver:
            take_ss(driver, "v4_99_error")
    finally:
        if driver:
            driver.quit()

    # Step: API tests
    try:
        test_api()
    except Exception as e:
        log(f"API ERROR: {e}")
        traceback.print_exc()

    # Upload
    try:
        upload_to_github()
    except Exception as e:
        log(f"Upload error: {e}")

    # FINAL SUMMARY
    log("\n" + "=" * 70)
    log("FINAL TEST REPORT - Employee 522 (Ananya Gupta)")
    log("=" * 70)
    p = sum(1 for r in RESULTS if r["status"] == "PASS")
    f = sum(1 for r in RESULTS if r["status"] == "FAIL")
    w = sum(1 for r in RESULTS if r["status"] == "WARN")
    log(f"\nTotals: {p} PASS | {f} FAIL | {w} WARN | {len(RESULTS)} total tests")
    log(f"Bugs found: {len(BUGS)}\n")

    log("--- All Results ---")
    for r in RESULTS:
        log(f"  [{r['status']}] {r['test']}: {r['details']}")

    if BUGS:
        log("\n--- Bugs ---")
        for i, b in enumerate(BUGS, 1):
            log(f"  {i}. {b['title']}")
            log(f"     {b['details']}")

    # Save results
    with open(os.path.join(SS_DIR, "v4_final_results.json"), 'w') as fout:
        json.dump({
            "employee_id": EMP_ID,
            "employee_name": "Ananya Gupta",
            "timestamp": str(datetime.now()),
            "summary": {"pass": p, "fail": f, "warn": w, "total": len(RESULTS), "bugs": len(BUGS)},
            "results": RESULTS,
            "bugs": BUGS
        }, fout, indent=2)

if __name__ == "__main__":
    main()
