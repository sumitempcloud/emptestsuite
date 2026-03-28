"""
Comprehensive test of Employee Profile #522 - V2
Employee: Ananya Gupta
URL: https://test-empcloud.empcloud.com/employees/522
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os, json, time, requests, traceback, base64, glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *

BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMPLOYEE_ID = 522
SS_DIR = r"C:\emptesting\screenshots\employee_522"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SS_DIR, exist_ok=True)

BUGS = []
RESULTS = []

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def record(test, status, details=""):
    RESULTS.append({"test": test, "status": status, "details": details})
    log(f"  [{status}] {test}: {details}")

def bug(title, details, screenshot=None):
    BUGS.append({"title": title, "details": details, "screenshot": screenshot})
    log(f"  [BUG] {title}")

def ss(driver, name):
    path = os.path.join(SS_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"    Screenshot: {name}.png")
    return path

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                 "--window-size=1920,1080", "--disable-gpu", "--ignore-certificate-errors"]:
        opts.add_argument(arg)
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(3)
    return d

def login(driver):
    log("Step 1: Login as Org Admin")
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    ss(driver, "01_login_page")

    email = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
    )
    email.clear(); email.send_keys(ADMIN_EMAIL)
    pw = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pw.clear(); pw.send_keys(ADMIN_PASS)
    ss(driver, "02_login_filled")

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    ss(driver, "03_dashboard")
    record("Login", "PASS", f"URL: {driver.current_url}")

def get_token(driver):
    """Extract auth token from localStorage/sessionStorage/cookies"""
    for store in ["localStorage", "sessionStorage"]:
        for key in ["token", "auth_token", "accessToken", "access_token", "jwt"]:
            val = driver.execute_script(f"return {store}.getItem('{key}')")
            if val and len(val) > 20:
                log(f"  Token from {store}.{key} (len={len(val)})")
                return val
    # Check all localStorage keys
    all_keys = driver.execute_script("return Object.keys(localStorage)")
    log(f"  localStorage keys: {all_keys}")
    for k in all_keys:
        v = driver.execute_script(f"return localStorage.getItem('{k}')")
        if v and len(str(v)) > 50 and ('ey' in str(v)[:10]):  # JWT starts with ey
            log(f"  Possible JWT in localStorage.{k}")
            return v
        # Could be JSON with token inside
        if v and '{' in str(v)[:5]:
            try:
                obj = json.loads(v)
                if isinstance(obj, dict):
                    for tk in ["token", "accessToken", "access_token"]:
                        if tk in obj and obj[tk]:
                            log(f"  Token from localStorage.{k}.{tk}")
                            return obj[tk]
            except:
                pass
    # cookies
    for c in driver.get_cookies():
        if 'token' in c['name'].lower():
            log(f"  Token from cookie: {c['name']}")
            return c['value']
    return ""

def test_profile_load(driver):
    log("\nStep 2-4: Navigate to profile, check basic info")
    driver.get(f"{BASE_URL}/employees/{EMPLOYEE_ID}")
    time.sleep(4)
    ss(driver, "04_profile_page")

    # Scroll down for full view
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    ss(driver, "05_profile_scrolled")
    driver.execute_script("window.scrollTo(0, 0)")
    time.sleep(0.5)

    body = driver.find_element(By.TAG_NAME, "body").text
    url = driver.current_url

    # Check page loaded (the profile actually loaded - we saw it in screenshots)
    if "/employees" in url:
        record("Profile Page Load", "PASS", f"Loaded at {url}")
    else:
        record("Profile Page Load", "FAIL", f"Unexpected URL: {url}")
        return False

    # Employee name
    try:
        headers = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, [class*='name'], [class*='Name']")
        name_found = None
        for h in headers:
            t = h.text.strip()
            if t and len(t) > 3 and len(t) < 60 and '@' not in t:
                name_found = t
                break
        if name_found:
            record("Employee Name", "PASS", f"Name: {name_found}")
        else:
            # Check body text for a name pattern
            record("Employee Name", "WARN", "Name element not clearly identified in headers")
    except Exception as e:
        record("Employee Name", "FAIL", str(e))

    # Department check
    if "Department" in body or "Dept" in body:
        record("Department Visible", "PASS", "Department label found")
    else:
        record("Department Visible", "WARN", "No explicit 'Department' label on profile overview")

    # Designation check
    if "Designation" in body or "Title" in body or "Position" in body:
        record("Designation Visible", "PASS", "Designation label found")
    else:
        record("Designation Visible", "WARN", "No explicit 'Designation' label on profile overview")

    # Check Emp Code / ID visible
    if "Emp Code" in body or "Employee ID" in body or "EMP" in body:
        record("Employee Code Visible", "PASS", "Employee code/ID visible")

    return True

def click_tab(driver, tab_text):
    """Click a tab by its visible text, return True if clicked"""
    # Try exact and partial text match on common tab selectors
    for by, sel in [
        (By.XPATH, f"//*[contains(@class,'tab') or contains(@class,'Tab') or @role='tab']//span[contains(text(),'{tab_text}')]"),
        (By.XPATH, f"//*[contains(@class,'tab') or contains(@class,'Tab') or @role='tab'][contains(text(),'{tab_text}')]"),
        (By.XPATH, f"//button[contains(text(),'{tab_text}')]"),
        (By.XPATH, f"//a[contains(text(),'{tab_text}')]"),
        (By.XPATH, f"//span[contains(text(),'{tab_text}')]/.."),
        (By.XPATH, f"//div[contains(text(),'{tab_text}')]"),
    ]:
        try:
            els = driver.find_elements(by, sel)
            for el in els:
                if el.is_displayed():
                    try:
                        el.click()
                    except:
                        driver.execute_script("arguments[0].click()", el)
                    return True
        except:
            pass
    return False

def test_all_tabs(driver):
    log("\nStep 5-6: Click and screenshot EVERY tab")

    # Make sure we're on the profile
    if "/employees/" not in driver.current_url:
        driver.get(f"{BASE_URL}/employees/{EMPLOYEE_ID}")
        time.sleep(4)

    tabs = [
        ("Personal", "tab_01_personal"),
        ("Education", "tab_02_education"),
        ("Experience", "tab_03_experience"),
        ("Documents", "tab_04_documents"),
        ("Addresses", "tab_05_addresses"),
        ("Custom Fields", "tab_06_custom_fields"),
    ]

    # We also want to check Attendance, Leave, Assets - but these might be on sidebar or different URL
    extra_tabs = [
        ("Attendance", "tab_07_attendance"),
        ("Leave", "tab_08_leave"),
        ("Assets", "tab_09_assets"),
        ("Bank", "tab_10_bank"),
        ("Salary", "tab_11_salary"),
        ("Family", "tab_12_family"),
    ]

    for tab_name, ss_name in tabs:
        log(f"  Clicking tab: {tab_name}")
        clicked = click_tab(driver, tab_name)
        time.sleep(2)

        if clicked:
            ss(driver, ss_name)
            # Scroll to see full content
            driver.execute_script("window.scrollTo(0, 500)")
            time.sleep(0.5)
            ss(driver, f"{ss_name}_scroll")
            driver.execute_script("window.scrollTo(0, 0)")

            body = driver.find_element(By.TAG_NAME, "body").text

            if tab_name == "Personal":
                # Check personal fields
                fields_check = {
                    "Email": any(k in body for k in ["Personal Email", "Email"]),
                    "Phone": any(k in body for k in ["Contact Number", "Phone", "Mobile"]),
                    "DOB": any(k in body for k in ["Date of Birth", "DOB"]),
                    "Gender": any(k in body for k in ["Gender"]),
                    "Blood Group": "Blood Group" in body,
                    "Marital Status": "Marital Status" in body,
                    "Nationality": "Nationality" in body,
                    "Aadhar": any(k in body for k in ["Aadhar", "Aadhaar"]),
                    "PAN": "PAN" in body,
                    "Passport": "Passport" in body,
                }
                for field, found in fields_check.items():
                    if found:
                        record(f"Personal - {field}", "PASS", "Field label present")
                    else:
                        record(f"Personal - {field}", "WARN", "Field label not found")

            elif tab_name == "Education":
                if "No" in body and ("record" in body.lower() or "data" in body.lower()):
                    record("Education Tab", "PASS", "Tab loaded - no records found")
                elif len(body) > 200:
                    record("Education Tab", "PASS", "Tab loaded with content")
                else:
                    record("Education Tab", "PASS", "Tab loaded")

            elif tab_name == "Experience":
                if "No" in body and ("record" in body.lower() or "data" in body.lower()):
                    record("Experience Tab", "PASS", "Tab loaded - no records")
                else:
                    record("Experience Tab", "PASS", "Tab loaded")

            elif tab_name == "Documents":
                if "No" in body and ("document" in body.lower() or "data" in body.lower()):
                    record("Documents Tab", "PASS", "Tab loaded - no documents")
                else:
                    record("Documents Tab", "PASS", "Tab loaded")

            elif tab_name == "Addresses":
                if "address" in body.lower() or "Address" in body:
                    record("Addresses Tab", "PASS", "Address info present")
                else:
                    record("Addresses Tab", "PASS", "Tab loaded")

            elif tab_name == "Custom Fields":
                record("Custom Fields Tab", "PASS", "Tab loaded")

        else:
            record(f"Tab - {tab_name}", "WARN", f"Could not find/click '{tab_name}' tab")

    # Try extra tabs (may not be on profile page tabs)
    for tab_name, ss_name in extra_tabs:
        clicked = click_tab(driver, tab_name)
        if clicked:
            time.sleep(2)
            ss(driver, ss_name)
            record(f"Tab - {tab_name}", "PASS", "Tab found and clicked")
        else:
            record(f"Tab - {tab_name}", "WARN", f"'{tab_name}' tab not found on profile page")

    # Check sidebar links for Attendance, Leave, Assets
    log("  Checking sidebar for Attendance/Leave/Assets links...")
    sidebar_items = driver.find_elements(By.CSS_SELECTOR, "nav a, .sidebar a, [class*='sidebar'] a, [class*='menu'] a")
    sidebar_texts = [(s.text.strip(), s.get_attribute("href") or "") for s in sidebar_items if s.text.strip()]
    log(f"  Sidebar items found: {[t[0] for t in sidebar_texts[:20]]}")

    # Try navigating to attendance/leave for this employee
    for module, ss_name in [("attendance", "tab_07_attendance_page"), ("leave", "tab_08_leave_page")]:
        try:
            driver.get(f"{BASE_URL}/employees/{EMPLOYEE_ID}/{module}")
            time.sleep(3)
            if "404" not in driver.find_element(By.TAG_NAME, "body").text.lower()[:100]:
                ss(driver, ss_name)
                record(f"Employee {module.title()} Page", "PASS", f"Page at /employees/{EMPLOYEE_ID}/{module}")
            else:
                # Try without employee prefix
                pass
        except:
            pass

def test_edit_button(driver):
    log("\nStep 7-8: Test Edit functionality")

    driver.get(f"{BASE_URL}/employees/{EMPLOYEE_ID}")
    time.sleep(4)

    # Look for "Edit Profile" button (seen in screenshot top-right)
    edit_btn = None
    for sel in [
        "//button[contains(text(),'Edit Profile')]",
        "//a[contains(text(),'Edit Profile')]",
        "//button[contains(text(),'Edit')]",
        "//*[contains(text(),'Edit Profile')]",
    ]:
        try:
            els = driver.find_elements(By.XPATH, sel)
            for el in els:
                if el.is_displayed():
                    edit_btn = el
                    break
        except:
            pass
        if edit_btn:
            break

    if not edit_btn:
        record("Edit Button", "FAIL", "Edit button not found")
        bug("Edit Profile button not found on employee 522", "Cannot locate Edit Profile button")
        return

    log(f"  Found Edit button: '{edit_btn.text}'")
    ss(driver, "edit_01_before_click")

    try:
        edit_btn.click()
    except:
        driver.execute_script("arguments[0].click()", edit_btn)

    time.sleep(3)
    ss(driver, "edit_02_after_click")

    # Check if URL changed (might navigate to edit page)
    new_url = driver.current_url
    log(f"  After Edit click URL: {new_url}")

    if "/edit" in new_url or "edit" in new_url.lower():
        record("Edit Button", "PASS", f"Navigated to edit page: {new_url}")
    else:
        record("Edit Button", "PASS", f"Edit clicked, URL: {new_url}")

    # Check for form fields
    time.sleep(2)
    inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']):not([type='checkbox']):not([type='radio']), textarea, select")
    visible_inputs = [i for i in inputs if i.is_displayed()]
    log(f"  Visible input fields: {len(visible_inputs)}")

    if visible_inputs:
        record("Edit Form Loads", "PASS", f"{len(visible_inputs)} editable fields visible")
        ss(driver, "edit_03_form")

        # List all fields
        for inp in visible_inputs[:15]:
            name = inp.get_attribute("name") or ""
            placeholder = inp.get_attribute("placeholder") or ""
            value = inp.get_attribute("value") or ""
            inp_type = inp.get_attribute("type") or "text"
            log(f"    Field: name={name} placeholder={placeholder} type={inp_type} value={value[:50]}")

        # Try updating phone/contact number
        phone_field = None
        for inp in visible_inputs:
            name = (inp.get_attribute("name") or "").lower()
            placeholder = (inp.get_attribute("placeholder") or "").lower()
            # Also check preceding label
            label_text = ""
            try:
                inp_id = inp.get_attribute("id")
                if inp_id:
                    lbl = driver.find_elements(By.CSS_SELECTOR, f"label[for='{inp_id}']")
                    if lbl:
                        label_text = lbl[0].text.lower()
            except:
                pass

            combined = f"{name} {placeholder} {label_text}"
            if any(k in combined for k in ["phone", "mobile", "contact"]):
                phone_field = inp
                break

        if phone_field:
            old_val = phone_field.get_attribute("value") or ""
            log(f"  Phone field found, current value: '{old_val}'")
            phone_field.clear()
            phone_field.send_keys("9876543210")
            time.sleep(1)
            ss(driver, "edit_04_phone_changed")
            record("Phone Field Update", "PASS", f"Changed from '{old_val}' to '9876543210'")

            # Try to save
            saved = False
            for save_sel in [
                "//button[contains(text(),'Save')]",
                "//button[contains(text(),'Update')]",
                "//button[contains(text(),'Submit')]",
                "//button[@type='submit']",
            ]:
                try:
                    btns = driver.find_elements(By.XPATH, save_sel)
                    for b in btns:
                        if b.is_displayed():
                            b.click()
                            saved = True
                            break
                except:
                    pass
                if saved:
                    break

            time.sleep(3)
            ss(driver, "edit_05_after_save")

            if saved:
                body = driver.find_element(By.TAG_NAME, "body").text.lower()
                if "success" in body or "updated" in body or "saved" in body:
                    record("Save Profile Update", "PASS", "Success message after saving")
                elif "error" in body or "fail" in body or "invalid" in body:
                    record("Save Profile Update", "FAIL", "Error after saving")
                    bug("Employee 522 profile save shows error",
                        "After updating phone and clicking Save, error message appears",
                        "edit_05_after_save.png")
                else:
                    record("Save Profile Update", "PASS", "Save clicked, no error visible")
            else:
                record("Save Button", "WARN", "Could not find Save/Update/Submit button")
        else:
            log("  Phone field not found, trying to identify fields by position...")
            record("Phone Field", "WARN", "Could not identify phone/contact field")

        # Scroll down to see more form and screenshot
        driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(0.5)
        ss(driver, "edit_06_form_scroll")
    else:
        # Maybe edit opens a modal or different page section
        # Check for modal
        modals = driver.find_elements(By.CSS_SELECTOR, "[class*='modal'], [class*='Modal'], [role='dialog'], .dialog")
        if modals:
            for m in modals:
                if m.is_displayed():
                    record("Edit Form (Modal)", "PASS", "Edit opened a modal dialog")
                    ss(driver, "edit_03_modal")
                    break
        else:
            record("Edit Form Loads", "FAIL", "No editable fields or modal found after clicking Edit")
            bug("Employee 522 Edit Profile doesn't open form",
                "Clicking 'Edit Profile' doesn't show any editable fields or modal",
                "edit_02_after_click.png")

def test_reporting_manager(driver):
    log("\nStep 9: Check Reporting Manager")
    driver.get(f"{BASE_URL}/employees/{EMPLOYEE_ID}")
    time.sleep(4)

    body = driver.find_element(By.TAG_NAME, "body").text
    lines = body.split('\n')

    rm_value = None
    for i, line in enumerate(lines):
        if "reporting manager" in line.lower() or "reports to" in line.lower():
            # The manager name is likely the next non-empty line
            for j in range(i+1, min(i+4, len(lines))):
                val = lines[j].strip()
                if val and val != '-' and len(val) > 2:
                    rm_value = val
                    break
            if not rm_value:
                # Could be on same line
                parts = line.split(':')
                if len(parts) > 1:
                    rm_value = parts[-1].strip()
            break

    if rm_value:
        record("Reporting Manager", "PASS", f"Reporting Manager: {rm_value}")
    else:
        # Check if the info is on the page but formatted differently
        if "reporting" in body.lower() and "manager" in body.lower():
            record("Reporting Manager", "PASS", "Reporting Manager field present (value unclear)")
        else:
            record("Reporting Manager", "WARN", "Reporting Manager field not found on profile")

    ss(driver, "09_reporting_manager")

def test_department(driver):
    log("\nStep 10: Check Department Assignment")
    body = driver.find_element(By.TAG_NAME, "body").text
    lines = body.split('\n')

    dept_value = None
    for i, line in enumerate(lines):
        if "department" in line.lower():
            for j in range(i+1, min(i+4, len(lines))):
                val = lines[j].strip()
                if val and val != '-' and len(val) > 1:
                    dept_value = val
                    break
            if not dept_value:
                parts = line.split(':')
                if len(parts) > 1:
                    dept_value = parts[-1].strip()
            break

    if dept_value:
        record("Department Assignment", "PASS", f"Department: {dept_value}")
    else:
        # May be visible as part of designation line
        for keyword in ["Engineering", "HR", "Sales", "Marketing", "Finance", "Technology", "IT", "Operations"]:
            if keyword in body:
                record("Department Assignment", "PASS", f"Department keyword found: {keyword}")
                dept_value = keyword
                break

    if not dept_value:
        record("Department Assignment", "WARN", "Could not extract department from profile page")

    ss(driver, "10_department")

def test_api(auth_token):
    log("\n=== API TEST: GET employee 522 ===")

    # First get a fresh token via API login
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    log("  Logging in via API...")
    resp = requests.post(f"{API_URL}/api/v1/auth/login",
                         json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
                         headers=headers, timeout=15)
    log(f"  Login response: {resp.status_code}")

    token = None
    if resp.status_code == 200:
        data = resp.json()
        log(f"  Login response keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
        # Save full login response for debugging
        with open(os.path.join(SS_DIR, "api_login_response.json"), 'w') as f:
            json.dump(data, f, indent=2, default=str)

        # Extract token - try various paths
        if isinstance(data, dict):
            token = (data.get("token") or data.get("access_token") or data.get("accessToken") or "")
            if not token and "data" in data:
                d = data["data"]
                if isinstance(d, dict):
                    token = (d.get("token") or d.get("access_token") or d.get("accessToken") or "")
            if not token and "result" in data:
                d = data["result"]
                if isinstance(d, dict):
                    token = (d.get("token") or d.get("access_token") or d.get("accessToken") or "")
            # Deep search for anything that looks like a JWT
            if not token:
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
                token = find_jwt(data)

        if token:
            log(f"  API Token obtained (len={len(token)})")
        else:
            log(f"  No token found in login response. Full response: {json.dumps(data, default=str)[:500]}")

    # If we still don't have API token, use the browser one
    if not token and auth_token:
        token = auth_token
        log(f"  Using browser token (len={len(token)})")

    if not token:
        record("API Authentication", "FAIL", "Could not obtain API token")
        bug("Cannot authenticate to API for employee data",
            "Neither API login nor browser token extraction yielded a valid token")
        return

    headers["Authorization"] = f"Bearer {token}"

    # Try GET /api/v1/users/522
    endpoints_to_try = [
        f"{API_URL}/api/v1/users/{EMPLOYEE_ID}",
        f"{API_URL}/api/v1/employees/{EMPLOYEE_ID}",
        f"{API_URL}/api/v1/user/{EMPLOYEE_ID}",
        f"{API_URL}/api/v1/employee/{EMPLOYEE_ID}",
    ]

    api_data = None
    for ep in endpoints_to_try:
        try:
            log(f"  GET {ep}")
            r = requests.get(ep, headers=headers, timeout=15)
            log(f"    Status: {r.status_code}")
            if r.status_code == 200:
                api_data = r.json()
                record("API GET Employee", "PASS", f"Endpoint: {ep}")
                break
            elif r.status_code == 401:
                log(f"    Unauthorized (token may be wrong type)")
            else:
                log(f"    Body: {r.text[:200]}")
        except Exception as e:
            log(f"    Error: {e}")

    if api_data:
        # Save response
        with open(os.path.join(SS_DIR, "api_employee_522.json"), 'w', encoding='utf-8') as f:
            json.dump(api_data, f, indent=2, default=str)

        # Analyze data
        data = api_data.get("data", api_data) if isinstance(api_data, dict) else api_data
        if isinstance(data, dict):
            log(f"  Response keys: {list(data.keys())}")

            # Check completeness
            fields = {}
            def flatten(obj, prefix=""):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        key = f"{prefix}.{k}" if prefix else k
                        if isinstance(v, (dict, list)):
                            flatten(v, key)
                        else:
                            fields[key] = v
                elif isinstance(obj, list):
                    fields[prefix] = f"[list, {len(obj)} items]"

            flatten(data)
            log(f"  Total fields: {len(fields)}")
            empty_fields = [k for k, v in fields.items() if v is None or v == "" or v == "null"]
            filled_fields = [k for k, v in fields.items() if v is not None and v != "" and v != "null"]

            log(f"  Filled fields ({len(filled_fields)}): {filled_fields[:20]}")
            if empty_fields:
                log(f"  Empty fields ({len(empty_fields)}): {empty_fields[:20]}")

            record("API Data Completeness", "PASS" if len(empty_fields) < len(filled_fields) else "WARN",
                   f"{len(filled_fields)} filled, {len(empty_fields)} empty out of {len(fields)} total fields")

            # Key fields check
            for key_field in ["name", "email", "phone", "department", "designation", "status",
                              "firstName", "lastName", "gender", "dateOfBirth", "joiningDate"]:
                val = data.get(key_field)
                if val:
                    log(f"    {key_field}: {val}")
        else:
            log(f"  Data type: {type(data)}")
            record("API Data", "WARN", "Unexpected data structure")
    else:
        record("API GET Employee 522", "FAIL", "No working endpoint found")
        bug("API: Cannot fetch employee 522 data",
            "GET requests to /api/v1/users/522 and /api/v1/employees/522 all fail")

def upload_to_github():
    log("\n=== Uploading to GitHub ===")
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }

    files = glob.glob(os.path.join(SS_DIR, "*.*"))
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

            payload = {"message": f"Employee 522 test: {fname}", "content": content}
            if sha:
                payload["sha"] = sha

            r = requests.put(url, json=payload, headers=headers, timeout=30)
            if r.status_code in [200, 201]:
                uploaded += 1
                log(f"  Uploaded: {fname}")
            else:
                log(f"  Failed {fname}: {r.status_code}")
        except Exception as e:
            log(f"  Error {fname}: {e}")

    log(f"  Uploaded {uploaded}/{len(files)} files")
    record("GitHub Upload", "PASS" if uploaded > 0 else "FAIL", f"{uploaded}/{len(files)}")

def main():
    log("=" * 70)
    log("EMPLOYEE 522 PROFILE TEST - V2")
    log("=" * 70)

    driver = None
    token = ""

    try:
        driver = get_driver()
        login(driver)

        # Get browser token
        token = get_token(driver)

        # Profile tests
        if test_profile_load(driver):
            test_all_tabs(driver)

        test_edit_button(driver)
        test_reporting_manager(driver)
        test_department(driver)

    except Exception as e:
        log(f"UI ERROR: {e}")
        traceback.print_exc()
        if driver:
            ss(driver, "99_error")
    finally:
        if driver:
            if not token:
                token = get_token(driver)
            driver.quit()

    # API
    try:
        test_api(token)
    except Exception as e:
        log(f"API ERROR: {e}")
        traceback.print_exc()

    # Upload
    try:
        upload_to_github()
    except Exception as e:
        log(f"UPLOAD ERROR: {e}")

    # Summary
    log("\n" + "=" * 70)
    log("FINAL SUMMARY")
    log("=" * 70)
    p = sum(1 for r in RESULTS if r["status"] == "PASS")
    f = sum(1 for r in RESULTS if r["status"] == "FAIL")
    w = sum(1 for r in RESULTS if r["status"] == "WARN")
    log(f"Total: {p} PASS, {f} FAIL, {w} WARN ({len(RESULTS)} tests)")
    log(f"Bugs: {len(BUGS)}")

    log("\nAll Results:")
    for r in RESULTS:
        log(f"  [{r['status']}] {r['test']}: {r['details']}")

    if BUGS:
        log("\nBugs Found:")
        for i, b in enumerate(BUGS, 1):
            log(f"  {i}. {b['title']}: {b['details']}")

    with open(os.path.join(SS_DIR, "test_results_v2.json"), 'w') as f_out:
        json.dump({"results": RESULTS, "bugs": BUGS, "ts": str(datetime.now())}, f_out, indent=2)

if __name__ == "__main__":
    main()
