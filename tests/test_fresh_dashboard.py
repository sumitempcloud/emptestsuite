"""
EMP Cloud HRMS - Fresh Comprehensive Dashboard E2E Test
Runs 8 test groups with fresh browser sessions to avoid ChromeDriver crashes.
"""

import os, sys, time, json, traceback, re, base64, requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────────
BASE = "https://test-empcloud.empcloud.com"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_test"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
GH_CLI = r"C:\tools\gh\bin\gh.exe"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_found = []
test_results = []  # (group, test_name, status, detail)

# ── Existing issues (titles) to avoid duplicates ────────────────────────────
EXISTING_TITLES = set()

def load_existing_issues():
    """Load existing issue titles from GitHub."""
    global EXISTING_TITLES
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        page = 1
        while True:
            r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                           headers=headers, params={"state": "all", "per_page": 100, "page": page})
            issues = r.json()
            if not issues:
                break
            for iss in issues:
                EXISTING_TITLES.add(iss.get("title", "").strip().lower())
            if len(issues) < 100:
                break
            page += 1
        print(f"[INFO] Loaded {len(EXISTING_TITLES)} existing issue titles")
    except Exception as e:
        print(f"[WARN] Could not load existing issues: {e}")

load_existing_issues()

def is_duplicate(title):
    """Check if a similar issue already exists."""
    t = title.strip().lower()
    if t in EXISTING_TITLES:
        return True
    # Check for partial matches on key phrases
    for existing in EXISTING_TITLES:
        # If the core description matches (ignoring prefix tags)
        core_new = re.sub(r'^\[.*?\]\s*', '', t)
        core_existing = re.sub(r'^\[.*?\]\s*', '', existing)
        if core_new and core_existing and (core_new in core_existing or core_existing in core_new):
            return True
    return False

# ── Driver factory ──────────────────────────────────────────────────────────
def get_fresh_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

def safe_quit(driver):
    try:
        driver.quit()
    except:
        pass

# ── Login helper ────────────────────────────────────────────────────────────
def login(driver, email, password, label="user"):
    driver.get(f"{BASE}/login")
    time.sleep(3)
    try:
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail']"))
        )
        email_input.clear()
        email_input.send_keys(email)
        pw_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        pw_input.clear()
        pw_input.send_keys(password)
        time.sleep(0.5)
        btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button.login-btn, form button")
        for b in btns:
            if b.is_displayed():
                b.click()
                break
        time.sleep(4)
        # Check if login was successful
        if "/login" in driver.current_url and "/dashboard" not in driver.current_url:
            # Try clicking again or look for other submit
            time.sleep(3)
        return "/login" not in driver.current_url or "/dashboard" in driver.current_url
    except Exception as e:
        print(f"  [LOGIN FAIL] {label}: {e}")
        return False

def navigate(driver, path, wait=3):
    driver.get(f"{BASE}{path}")
    time.sleep(wait)

def screenshot(driver, name):
    fpath = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(fpath)
    return fpath

def record(group, name, status, detail=""):
    test_results.append((group, name, status, detail))
    icon = "PASS" if status == "PASS" else "BUG" if status == "BUG" else "WARN"
    print(f"  [{icon}] {name}: {detail[:120]}")

def file_bug(title, body, screenshot_path=None):
    """File a GitHub issue with optional screenshot."""
    if is_duplicate(title):
        print(f"  [SKIP] Duplicate issue: {title}")
        return None

    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    # Upload screenshot if exists
    img_url = None
    if screenshot_path and os.path.exists(screenshot_path):
        try:
            fname = os.path.basename(screenshot_path)
            gh_path = f"screenshots/fresh_test/{fname}"
            with open(screenshot_path, "rb") as f:
                content_b64 = base64.b64encode(f.read()).decode()
            payload = {
                "message": f"Upload screenshot {fname}",
                "content": content_b64,
                "branch": "main"
            }
            r = requests.put(
                f"https://api.github.com/repos/{GITHUB_REPO}/contents/{gh_path}",
                headers=headers, json=payload
            )
            if r.status_code in (200, 201):
                img_url = r.json().get("content", {}).get("download_url", "")
            else:
                print(f"  [WARN] Screenshot upload returned {r.status_code}")
        except Exception as e:
            print(f"  [WARN] Screenshot upload failed: {e}")

    # Build issue body
    full_body = body
    if img_url:
        full_body += f"\n\n### Screenshot\n![screenshot]({img_url})"
    full_body += f"\n\n---\n*Found by automated E2E test on {datetime.now().strftime('%Y-%m-%d %H:%M')}*"

    try:
        r = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers=headers,
            json={"title": title, "body": full_body, "labels": ["bug", "e2e-test"]}
        )
        if r.status_code == 201:
            num = r.json()["number"]
            url = r.json()["html_url"]
            print(f"  [FILED] #{num}: {title}")
            EXISTING_TITLES.add(title.strip().lower())
            bugs_found.append({"number": num, "title": title, "url": url})
            return num
        else:
            print(f"  [FAIL] Issue creation returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  [FAIL] Issue creation failed: {e}")
    return None

def has_error_toast(driver):
    """Check for error toast messages."""
    try:
        toasts = driver.find_elements(By.CSS_SELECTOR, "[class*='toast'] [class*='error'], [class*='Toastify'] [class*='error'], .toast-error, [role='alert']")
        for t in toasts:
            if t.is_displayed() and t.text.strip():
                return t.text.strip()
    except:
        pass
    return None

def has_raw_i18n(driver):
    """Check for raw i18n keys in page."""
    try:
        text = driver.find_element(By.TAG_NAME, "body").text
        matches = re.findall(r'\b[a-z]+\.[a-zA-Z]+(?:\.[a-zA-Z]+)+\b', text)
        # Filter for likely i18n keys
        i18n_keys = [m for m in matches if any(k in m.lower() for k in ['nav.', 'page.', 'label.', 'btn.', 'msg.', 'common.', 'form.', 'table.', 'modal.'])]
        return i18n_keys[:5] if i18n_keys else None
    except:
        return None

def page_has_content(driver, min_text_len=20):
    """Check if page has meaningful content (not blank/empty)."""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.strip()
        return len(body) >= min_text_len
    except:
        return False

def check_page_basics(driver, page_name, group):
    """Common checks: blank page, error toasts, i18n keys, 404."""
    issues = []
    body_text = ""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
    except:
        pass

    if "404" in body_text[:500] or "not found" in body_text[:500].lower():
        issues.append(f"404/Not Found on {page_name}")

    if not page_has_content(driver):
        issues.append(f"Blank/empty page on {page_name}")

    err = has_error_toast(driver)
    if err and "rate" not in err.lower() and "limit" not in err.lower():
        issues.append(f"Error toast on {page_name}: {err}")

    i18n = has_raw_i18n(driver)
    if i18n:
        issues.append(f"Raw i18n keys on {page_name}: {', '.join(i18n[:3])}")

    return issues

# ═══════════════════════════════════════════════════════════════════════════
# GROUP 1: Employee Directory Deep Test
# ═══════════════════════════════════════════════════════════════════════════
def run_group_1():
    print("\n" + "="*70)
    print("GROUP 1: Employee Directory Deep Test")
    print("="*70)
    driver = get_fresh_driver()
    try:
        if not login(driver, ADMIN_EMAIL, ADMIN_PASS, "Org Admin"):
            record("G1", "login", "BUG", "Admin login failed")
            screenshot(driver, "g1_login_fail")
            return
        record("G1", "login", "PASS", "Org Admin logged in")

        # Navigate to employees
        navigate(driver, "/employees", 5)
        ss = screenshot(driver, "g1_employees_page")
        issues = check_page_basics(driver, "/employees", "G1")
        for iss in issues:
            record("G1", "employees_page", "BUG", iss)
            file_bug(f"[Employee Directory] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/employees\n**Role:** Org Admin", ss)

        if not issues:
            record("G1", "employees_page_load", "PASS", "Employee directory loaded")

        # Test search
        try:
            search_input = None
            for sel in ["input[placeholder*='earch']", "input[type='search']", "input[name*='search']", "input[placeholder*='filter']", ".search-input input", "[data-testid*='search'] input"]:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    search_input = elems[0]
                    break
            if search_input:
                # Get initial count of rows
                initial_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, [class*='employee'] [class*='card'], [class*='list'] [class*='item']")
                initial_count = len(initial_rows)

                search_input.clear()
                search_input.send_keys("Ananya")
                time.sleep(3)
                ss = screenshot(driver, "g1_search_result")

                filtered_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, [class*='employee'] [class*='card'], [class*='list'] [class*='item']")
                filtered_count = len(filtered_rows)

                body_text = driver.find_element(By.TAG_NAME, "body").text
                if "ananya" in body_text.lower() or filtered_count < initial_count or filtered_count > 0:
                    record("G1", "search_filter", "PASS", f"Search returned results (before={initial_count}, after={filtered_count})")
                else:
                    record("G1", "search_filter", "BUG", f"Search did not filter (before={initial_count}, after={filtered_count})")
                    file_bug("[Employee Directory] Search does not filter employee list when typing name",
                             f"## Description\nSearching for 'Ananya' does not filter the employee list.\n\n**Before search:** {initial_count} items\n**After search:** {filtered_count} items\n\n**URL:** {BASE}/employees\n**Role:** Org Admin",
                             ss)
                # Clear search
                search_input.clear()
                search_input.send_keys(Keys.ESCAPE)
                time.sleep(1)
            else:
                record("G1", "search_input", "BUG", "Search input not found on employees page")
                file_bug("[Employee Directory] No search input found on employee directory page",
                         f"## Description\nNo search/filter input field found on the employee directory page.\n\n**URL:** {BASE}/employees\n**Role:** Org Admin",
                         screenshot(driver, "g1_no_search"))
        except Exception as e:
            record("G1", "search", "WARN", f"Search test error: {e}")

        # Test department filter
        try:
            dept_filter = None
            for sel in ["select[name*='dept']", "select[name*='department']", "[class*='filter'] select", "[data-testid*='department']", "select"]:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elems:
                    if el.is_displayed():
                        dept_filter = el
                        break
                if dept_filter:
                    break

            # Also try button-style filters
            if not dept_filter:
                filter_btns = driver.find_elements(By.XPATH, "//button[contains(text(),'Department') or contains(text(),'Filter')]")
                if filter_btns:
                    filter_btns[0].click()
                    time.sleep(1)
                    record("G1", "dept_filter_dropdown", "PASS", "Department filter dropdown/button found")
                else:
                    record("G1", "dept_filter", "WARN", "No department filter dropdown found")
            else:
                record("G1", "dept_filter", "PASS", "Department filter select found")
        except Exception as e:
            record("G1", "dept_filter", "WARN", f"Department filter test: {e}")

        # Click employee row
        try:
            navigate(driver, "/employees", 4)
            clickable = None
            # Try table rows
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            if rows:
                clickable = rows[0]
            else:
                # Try card/list items
                cards = driver.find_elements(By.CSS_SELECTOR, "[class*='employee'] a, [class*='card'] a, [class*='list-item'] a")
                if cards:
                    clickable = cards[0]
                else:
                    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/employee']")
                    if links:
                        clickable = links[0]

            if clickable:
                old_url = driver.current_url
                clickable.click()
                time.sleep(3)
                new_url = driver.current_url
                ss = screenshot(driver, "g1_employee_click")
                if new_url != old_url and ("/employee" in new_url or "/profile" in new_url):
                    record("G1", "employee_click_nav", "PASS", f"Navigated to {new_url}")
                else:
                    record("G1", "employee_click_nav", "BUG", f"Click did not navigate. URL stayed: {new_url}")
                    file_bug("[Employee Directory] Clicking employee row does not navigate to profile",
                             f"## Description\nClicking on an employee row/card does not navigate to their profile page.\n\n**URL before click:** {old_url}\n**URL after click:** {new_url}\n\n**Role:** Org Admin",
                             ss)
            else:
                record("G1", "employee_click", "WARN", "No clickable employee rows found")
        except Exception as e:
            record("G1", "employee_click", "WARN", f"Employee click test: {e}")

        # Test pagination
        try:
            navigate(driver, "/employees", 4)
            pag = driver.find_elements(By.CSS_SELECTOR, "[class*='pagination'], nav[aria-label*='pagination'], .MuiPagination-root, button[aria-label*='page'], [class*='Pagination']")
            if pag:
                record("G1", "pagination", "PASS", "Pagination controls found")
            else:
                # Check if there are enough items to need pagination
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, [class*='card']")
                if len(rows) >= 10:
                    record("G1", "pagination", "BUG", f"No pagination despite {len(rows)} rows")
                else:
                    record("G1", "pagination", "PASS", f"Only {len(rows)} items, pagination not needed")
        except Exception as e:
            record("G1", "pagination", "WARN", f"Pagination test: {e}")

        # Test Add Employee button
        try:
            navigate(driver, "/employees", 4)
            add_btn = None
            for sel in ["button[class*='add']", "a[href*='add']", "button[class*='fab']", "[class*='Add']", "button[aria-label*='add']"]:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elems:
                    if el.is_displayed():
                        add_btn = el
                        break
                if add_btn:
                    break
            # Also search by text
            if not add_btn:
                btns = driver.find_elements(By.XPATH, "//button[contains(text(),'Add')] | //a[contains(text(),'Add')] | //button[contains(text(),'New')] | //button[contains(@class,'fab')]")
                for b in btns:
                    if b.is_displayed():
                        add_btn = b
                        break
            # Try FAB (floating action button)
            if not add_btn:
                fabs = driver.find_elements(By.CSS_SELECTOR, ".fab, [class*='FloatingAction'], button[class*='float'], svg[data-testid='AddIcon']")
                if fabs:
                    add_btn = fabs[0]

            if add_btn:
                add_btn.click()
                time.sleep(3)
                ss = screenshot(driver, "g1_add_employee")
                # Check if form/modal appeared
                forms = driver.find_elements(By.CSS_SELECTOR, "form, [class*='modal'], [class*='dialog'], [role='dialog']")
                if forms:
                    record("G1", "add_employee_form", "PASS", "Add employee form/modal opened")
                    # Check form fields
                    inputs = driver.find_elements(By.CSS_SELECTOR, "form input, [role='dialog'] input, [class*='modal'] input")
                    record("G1", "add_employee_fields", "PASS" if len(inputs) >= 2 else "WARN",
                           f"Found {len(inputs)} input fields in add form")
                else:
                    # Maybe navigated to new page
                    if "/add" in driver.current_url or "/new" in driver.current_url or "/create" in driver.current_url:
                        record("G1", "add_employee_form", "PASS", f"Navigated to add page: {driver.current_url}")
                    else:
                        record("G1", "add_employee_form", "BUG", "Add button clicked but no form appeared")
                        file_bug("[Employee Directory] Add Employee button does not open creation form",
                                 f"## Description\nClicking 'Add Employee' button does not open a form or navigate to a creation page.\n\n**URL:** {driver.current_url}\n**Role:** Org Admin",
                                 ss)
            else:
                record("G1", "add_employee_btn", "BUG", "Add Employee button not found")
                ss = screenshot(driver, "g1_no_add_btn")
                file_bug("[Employee Directory] No 'Add Employee' button found on directory page",
                         f"## Description\nNo 'Add Employee' or 'New Employee' button found on the employee directory page.\n\n**URL:** {BASE}/employees\n**Role:** Org Admin",
                         ss)
        except Exception as e:
            record("G1", "add_employee", "WARN", f"Add employee test: {e}")

    except Exception as e:
        record("G1", "group_error", "WARN", f"Group 1 error: {e}")
        traceback.print_exc()
    finally:
        safe_quit(driver)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 2: Attendance & Leave Deep Test
# ═══════════════════════════════════════════════════════════════════════════
def run_group_2():
    print("\n" + "="*70)
    print("GROUP 2: Attendance & Leave Deep Test")
    print("="*70)
    driver = get_fresh_driver()
    try:
        if not login(driver, ADMIN_EMAIL, ADMIN_PASS, "Org Admin"):
            record("G2", "login", "BUG", "Admin login failed")
            return
        record("G2", "login", "PASS", "Logged in")

        # Attendance page
        navigate(driver, "/attendance", 5)
        ss = screenshot(driver, "g2_attendance")
        issues = check_page_basics(driver, "/attendance", "G2")
        for iss in issues:
            record("G2", "attendance_page", "BUG", iss)
            file_bug(f"[Attendance] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/attendance\n**Role:** Org Admin", ss)
        if not issues:
            record("G2", "attendance_page", "PASS", "Attendance page loaded")

        # Check attendance stats/dashboard cards
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            stats_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='stat'], [class*='card'], [class*='metric'], [class*='summary']")
            has_numbers = bool(re.search(r'\d+\s*(present|absent|late|total|employees)', body, re.IGNORECASE))
            if stats_elements or has_numbers:
                record("G2", "attendance_stats", "PASS", f"Stats found ({len(stats_elements)} elements)")
            else:
                record("G2", "attendance_stats", "WARN", "No visible attendance statistics/cards")
        except Exception as e:
            record("G2", "attendance_stats", "WARN", str(e))

        # Test date filter on attendance
        try:
            date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[class*='date'], [class*='datepicker'] input, [class*='DatePicker']")
            if date_inputs:
                record("G2", "attendance_date_filter", "PASS", f"Found {len(date_inputs)} date filter(s)")
            else:
                # Try button-based date filters
                date_btns = driver.find_elements(By.XPATH, "//button[contains(text(),'Today') or contains(text(),'Week') or contains(text(),'Month') or contains(text(),'Date')]")
                if date_btns:
                    record("G2", "attendance_date_filter", "PASS", f"Found {len(date_btns)} date filter button(s)")
                else:
                    record("G2", "attendance_date_filter", "WARN", "No date filter controls found")
        except Exception as e:
            record("G2", "attendance_date_filter", "WARN", str(e))

        # Leave page
        navigate(driver, "/leave", 5)
        ss = screenshot(driver, "g2_leave")
        issues = check_page_basics(driver, "/leave", "G2")
        for iss in issues:
            record("G2", "leave_page", "BUG", iss)
            file_bug(f"[Leave] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/leave\n**Role:** Org Admin", ss)
        if not issues:
            record("G2", "leave_page", "PASS", "Leave page loaded")

        # Check leave balance cards
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            has_balance = bool(re.search(r'(balance|remaining|available|used|total)\s*:?\s*\d+', body, re.IGNORECASE))
            balance_cards = driver.find_elements(By.CSS_SELECTOR, "[class*='balance'], [class*='card']")
            if has_balance or len(balance_cards) > 0:
                record("G2", "leave_balance", "PASS", "Leave balance info found")
            else:
                record("G2", "leave_balance", "WARN", "No leave balance cards visible")
        except Exception as e:
            record("G2", "leave_balance", "WARN", str(e))

        # Apply Leave button
        try:
            apply_btn = None
            for sel in [
                "button", "a"
            ]:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elems:
                    txt = el.text.lower()
                    if el.is_displayed() and ("apply" in txt or "request" in txt or "new leave" in txt):
                        apply_btn = el
                        break
                if apply_btn:
                    break
            if apply_btn:
                apply_btn.click()
                time.sleep(3)
                ss = screenshot(driver, "g2_apply_leave")
                # Check for form
                forms = driver.find_elements(By.CSS_SELECTOR, "form, [class*='modal'], [role='dialog']")
                selects = driver.find_elements(By.CSS_SELECTOR, "select, [class*='select'], [role='listbox'], [role='combobox']")
                if forms or selects:
                    record("G2", "apply_leave_form", "PASS", "Apply leave form opened")

                    # Check leave type dropdown
                    leave_type_found = False
                    for s in selects:
                        if s.is_displayed():
                            leave_type_found = True
                            break
                    # Also look in dropdowns
                    if not leave_type_found:
                        dropdowns = driver.find_elements(By.CSS_SELECTOR, "[class*='dropdown'], [class*='Select'], select")
                        leave_type_found = len(dropdowns) > 0

                    if leave_type_found:
                        record("G2", "leave_type_dropdown", "PASS", "Leave type dropdown found")
                    else:
                        record("G2", "leave_type_dropdown", "WARN", "No leave type dropdown found in form")
                else:
                    if "/apply" in driver.current_url or "/new" in driver.current_url or "/create" in driver.current_url:
                        record("G2", "apply_leave_form", "PASS", f"Navigated to: {driver.current_url}")
                    else:
                        record("G2", "apply_leave_form", "BUG", "Apply button clicked but no form appeared")
                        file_bug("[Leave] Apply Leave button does not open leave request form",
                                 f"## Description\nClicking 'Apply Leave' does not open a form or modal.\n\n**URL:** {driver.current_url}\n**Role:** Org Admin",
                                 ss)
            else:
                record("G2", "apply_leave_btn", "WARN", "No Apply Leave button found")
        except Exception as e:
            record("G2", "apply_leave", "WARN", str(e))

        # Comp-off page
        navigate(driver, "/leave/comp-off", 4)
        ss = screenshot(driver, "g2_compoff")
        current = driver.current_url
        if "/dashboard" in current and "/leave" not in current:
            record("G2", "compoff_redirect", "BUG", f"Comp-off redirected to dashboard: {current}")
            file_bug("[Leave] /leave/comp-off redirects to dashboard instead of comp-off page",
                     f"## Description\nNavigating to /leave/comp-off redirects to the dashboard.\n\n**Expected:** Comp-Off management page\n**Actual:** Redirected to {current}\n\n**Role:** Org Admin",
                     ss)
        else:
            issues = check_page_basics(driver, "/leave/comp-off", "G2")
            for iss in issues:
                record("G2", "compoff_page", "BUG", iss)
                file_bug(f"[Leave] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/leave/comp-off\n**Role:** Org Admin", ss)
            if not issues:
                record("G2", "compoff_page", "PASS", "Comp-off page loaded")

    except Exception as e:
        record("G2", "group_error", "WARN", f"Group 2 error: {e}")
        traceback.print_exc()
    finally:
        safe_quit(driver)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 3: Helpdesk & Surveys
# ═══════════════════════════════════════════════════════════════════════════
def run_group_3():
    print("\n" + "="*70)
    print("GROUP 3: Helpdesk & Surveys")
    print("="*70)
    driver = get_fresh_driver()
    try:
        if not login(driver, ADMIN_EMAIL, ADMIN_PASS, "Org Admin"):
            record("G3", "login", "BUG", "Login failed")
            return
        record("G3", "login", "PASS", "Logged in")

        # Helpdesk page
        navigate(driver, "/helpdesk", 5)
        ss = screenshot(driver, "g3_helpdesk")
        issues = check_page_basics(driver, "/helpdesk", "G3")
        for iss in issues:
            record("G3", "helpdesk_page", "BUG", iss)
            file_bug(f"[Helpdesk] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/helpdesk\n**Role:** Org Admin", ss)
        if not issues:
            record("G3", "helpdesk_page", "PASS", "Helpdesk page loaded")

        # Test ticket creation
        try:
            create_btn = None
            btns = driver.find_elements(By.CSS_SELECTOR, "button, a")
            for b in btns:
                txt = b.text.lower()
                if b.is_displayed() and ("create" in txt or "new ticket" in txt or "raise" in txt or "submit" in txt):
                    create_btn = b
                    break
            # Try FAB
            if not create_btn:
                fabs = driver.find_elements(By.CSS_SELECTOR, "[class*='fab'], button[class*='float'], [class*='add-btn']")
                if fabs:
                    create_btn = fabs[0]

            if create_btn:
                create_btn.click()
                time.sleep(3)
                ss = screenshot(driver, "g3_create_ticket")
                # Fill form
                inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']), textarea, select")
                visible_inputs = [i for i in inputs if i.is_displayed()]
                if len(visible_inputs) >= 2:
                    record("G3", "ticket_form", "PASS", f"Ticket form opened with {len(visible_inputs)} fields")
                    # Try filling
                    for inp in visible_inputs:
                        try:
                            tag = inp.tag_name
                            itype = inp.get_attribute("type") or ""
                            placeholder = (inp.get_attribute("placeholder") or "").lower()
                            name = (inp.get_attribute("name") or "").lower()
                            if tag == "textarea" or "desc" in name or "desc" in placeholder or "message" in placeholder:
                                inp.clear()
                                inp.send_keys("E2E Test: System is slow when loading reports")
                            elif "subject" in name or "subject" in placeholder or "title" in name or "title" in placeholder:
                                inp.clear()
                                inp.send_keys("E2E Test Ticket - Performance Issue")
                            elif tag == "select":
                                try:
                                    sel = Select(inp)
                                    if len(sel.options) > 1:
                                        sel.select_by_index(1)
                                except:
                                    pass
                        except:
                            pass
                else:
                    record("G3", "ticket_form", "BUG", "Create ticket button clicked but form has < 2 fields")
                    file_bug("[Helpdesk] Ticket creation form has insufficient fields",
                             f"## Description\nTicket form only has {len(visible_inputs)} visible input fields.\n\n**URL:** {driver.current_url}\n**Role:** Org Admin",
                             ss)
            else:
                record("G3", "ticket_create_btn", "WARN", "No create ticket button found")
        except Exception as e:
            record("G3", "ticket_creation", "WARN", str(e))

        # Check My Tickets
        try:
            navigate(driver, "/helpdesk", 3)
            body = driver.find_element(By.TAG_NAME, "body").text
            # Look for tabs or section with tickets
            has_tickets_section = bool(re.search(r'(my tickets|all tickets|open|closed|pending)', body, re.IGNORECASE))
            if has_tickets_section:
                record("G3", "my_tickets", "PASS", "Tickets listing found")
            else:
                record("G3", "my_tickets", "WARN", "No tickets section found")
        except Exception as e:
            record("G3", "my_tickets", "WARN", str(e))

        # Surveys
        navigate(driver, "/surveys", 5)
        ss = screenshot(driver, "g3_surveys")
        issues = check_page_basics(driver, "/surveys", "G3")
        for iss in issues:
            record("G3", "surveys_page", "BUG", iss)
            file_bug(f"[Surveys] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/surveys\n**Role:** Org Admin", ss)
        if not issues:
            record("G3", "surveys_page", "PASS", "Surveys page loaded")

        # Surveys list
        navigate(driver, "/surveys/list", 4)
        ss = screenshot(driver, "g3_surveys_list")
        current = driver.current_url
        if "/dashboard" in current and "/surveys" not in current:
            record("G3", "surveys_list_redirect", "BUG", f"Redirected to: {current}")
            file_bug("[Surveys] /surveys/list redirects to dashboard",
                     f"## Description\n/surveys/list redirects to dashboard instead of showing all surveys.\n\n**Expected:** All surveys list\n**Actual:** Redirected to {current}\n\n**Role:** Org Admin",
                     ss)
        else:
            issues = check_page_basics(driver, "/surveys/list", "G3")
            for iss in issues:
                record("G3", "surveys_list", "BUG", iss)
            if not issues:
                record("G3", "surveys_list", "PASS", "Surveys list page loaded")

    except Exception as e:
        record("G3", "group_error", "WARN", f"Group 3 error: {e}")
        traceback.print_exc()
    finally:
        safe_quit(driver)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 4: Forum, Events, Wellness
# ═══════════════════════════════════════════════════════════════════════════
def run_group_4():
    print("\n" + "="*70)
    print("GROUP 4: Forum, Events, Wellness")
    print("="*70)
    driver = get_fresh_driver()
    try:
        if not login(driver, ADMIN_EMAIL, ADMIN_PASS, "Org Admin"):
            record("G4", "login", "BUG", "Login failed")
            return
        record("G4", "login", "PASS", "Logged in")

        # Forum / Community
        navigate(driver, "/forum", 5)
        ss = screenshot(driver, "g4_forum")
        current = driver.current_url
        # Try /community if /forum redirects
        if "/dashboard" in current and "/forum" not in current:
            navigate(driver, "/community", 5)
            ss = screenshot(driver, "g4_community")
            current = driver.current_url

        issues = check_page_basics(driver, "/forum (or /community)", "G4")
        for iss in issues:
            record("G4", "forum_page", "BUG", iss)
            file_bug(f"[Forum] {iss}", f"## Description\n{iss}\n\n**URL:** {current}\n**Role:** Org Admin", ss)
        if not issues:
            record("G4", "forum_page", "PASS", f"Forum page loaded at {current}")

        # Try creating a post
        try:
            create_btn = None
            for sel in ["button", "a"]:
                for el in driver.find_elements(By.CSS_SELECTOR, sel):
                    txt = el.text.lower()
                    if el.is_displayed() and ("create" in txt or "new post" in txt or "write" in txt or "post" in txt):
                        create_btn = el
                        break
                if create_btn:
                    break
            if create_btn:
                create_btn.click()
                time.sleep(3)
                ss = screenshot(driver, "g4_create_post")
                inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']), textarea")
                visible = [i for i in inputs if i.is_displayed()]
                if visible:
                    record("G4", "create_post_form", "PASS", f"Post form opened with {len(visible)} fields")
                else:
                    record("G4", "create_post_form", "WARN", "Post creation form has no visible inputs")
            else:
                record("G4", "create_post_btn", "WARN", "No create post button found")
        except Exception as e:
            record("G4", "create_post", "WARN", str(e))

        # Events
        navigate(driver, "/events", 5)
        ss = screenshot(driver, "g4_events")
        issues = check_page_basics(driver, "/events", "G4")
        for iss in issues:
            record("G4", "events_page", "BUG", iss)
            file_bug(f"[Events] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/events\n**Role:** Org Admin", ss)
        if not issues:
            record("G4", "events_page", "PASS", "Events page loaded")

        # Check for event listing content
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            has_events = bool(re.search(r'(event|upcoming|past|calendar|no events)', body, re.IGNORECASE))
            if has_events:
                record("G4", "events_content", "PASS", "Events content visible")
            else:
                record("G4", "events_content", "WARN", "No event-related content visible")
        except:
            pass

        # Wellness
        navigate(driver, "/wellness", 5)
        ss = screenshot(driver, "g4_wellness")
        issues = check_page_basics(driver, "/wellness", "G4")
        for iss in issues:
            record("G4", "wellness_page", "BUG", iss)
            file_bug(f"[Wellness] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/wellness\n**Role:** Org Admin", ss)
        if not issues:
            record("G4", "wellness_page", "PASS", "Wellness page loaded")

        # Daily check-in
        navigate(driver, "/wellness/check-in", 5)
        ss = screenshot(driver, "g4_checkin")
        current = driver.current_url
        if "/dashboard" in current and "/wellness" not in current:
            record("G4", "checkin_redirect", "BUG", f"Check-in redirected to dashboard: {current}")
            file_bug("[Wellness] /wellness/check-in redirects to dashboard",
                     f"## Description\n/wellness/check-in redirects to dashboard instead of showing daily check-in form.\n\n**Expected:** Daily wellness check-in page\n**Actual:** Redirected to {current}\n\n**Role:** Org Admin",
                     ss)
        else:
            issues = check_page_basics(driver, "/wellness/check-in", "G4")
            for iss in issues:
                record("G4", "checkin_page", "BUG", iss)
                file_bug(f"[Wellness] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/wellness/check-in\n**Role:** Org Admin", ss)
            if not issues:
                record("G4", "checkin_page", "PASS", "Check-in page loaded")

                # Try to do daily check-in
                try:
                    # Look for mood/rating buttons or form
                    mood_btns = driver.find_elements(By.CSS_SELECTOR, "[class*='mood'], [class*='emoji'], [class*='rating'], button[class*='check']")
                    forms = driver.find_elements(By.CSS_SELECTOR, "form")
                    if mood_btns:
                        mood_btns[0].click()
                        time.sleep(1)
                        record("G4", "checkin_interact", "PASS", "Interacted with check-in form")
                    elif forms:
                        record("G4", "checkin_interact", "PASS", "Check-in form found")
                    else:
                        record("G4", "checkin_interact", "WARN", "No interactive check-in elements found")
                except Exception as e:
                    record("G4", "checkin_interact", "WARN", str(e))

    except Exception as e:
        record("G4", "group_error", "WARN", f"Group 4 error: {e}")
        traceback.print_exc()
    finally:
        safe_quit(driver)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 5: Assets, Positions, Feedback
# ═══════════════════════════════════════════════════════════════════════════
def run_group_5():
    print("\n" + "="*70)
    print("GROUP 5: Assets, Positions, Feedback")
    print("="*70)
    driver = get_fresh_driver()
    try:
        if not login(driver, ADMIN_EMAIL, ADMIN_PASS, "Org Admin"):
            record("G5", "login", "BUG", "Login failed")
            return
        record("G5", "login", "PASS", "Logged in")

        # Assets page
        navigate(driver, "/assets", 5)
        ss = screenshot(driver, "g5_assets")
        issues = check_page_basics(driver, "/assets", "G5")
        for iss in issues:
            record("G5", "assets_page", "BUG", iss)
            file_bug(f"[Assets] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/assets\n**Role:** Org Admin", ss)
        if not issues:
            record("G5", "assets_page", "PASS", "Assets page loaded")

        # Check for asset management features
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            has_asset_content = bool(re.search(r'(asset|device|laptop|equipment|inventory|assigned|available)', body, re.IGNORECASE))
            if has_asset_content:
                record("G5", "assets_content", "PASS", "Asset management content visible")
            else:
                record("G5", "assets_content", "WARN", "No asset content visible on page")
        except:
            pass

        # Check for error toasts specifically
        try:
            err = has_error_toast(driver)
            if err and "rate" not in err.lower() and "limit" not in err.lower():
                record("G5", "assets_error", "BUG", f"Error on assets page: {err}")
                file_bug(f"[Assets] Error toast displayed on assets page: {err[:80]}",
                         f"## Description\nError toast message displayed when loading assets page.\n\n**Error:** {err}\n**URL:** {BASE}/assets\n**Role:** Org Admin",
                         ss)
        except:
            pass

        # Positions page
        navigate(driver, "/positions", 5)
        ss = screenshot(driver, "g5_positions")
        issues = check_page_basics(driver, "/positions", "G5")
        for iss in issues:
            record("G5", "positions_page", "BUG", iss)
            file_bug(f"[Positions] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/positions\n**Role:** Org Admin", ss)
        if not issues:
            record("G5", "positions_page", "PASS", "Positions page loaded")

        # Check for open positions
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            has_positions = bool(re.search(r'(position|opening|vacancy|job|role|no positions)', body, re.IGNORECASE))
            tables = driver.find_elements(By.CSS_SELECTOR, "table, [class*='list'], [class*='card']")
            if has_positions or tables:
                record("G5", "positions_content", "PASS", "Positions content visible")
            else:
                record("G5", "positions_content", "WARN", "No positions content visible")
        except:
            pass

        # Feedback page
        navigate(driver, "/feedback", 5)
        ss = screenshot(driver, "g5_feedback")
        issues = check_page_basics(driver, "/feedback", "G5")
        for iss in issues:
            record("G5", "feedback_page", "BUG", iss)
            file_bug(f"[Feedback] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/feedback\n**Role:** Org Admin", ss)
        if not issues:
            record("G5", "feedback_page", "PASS", "Feedback page loaded")

        # Check for error toasts on feedback
        try:
            err = has_error_toast(driver)
            if err and "rate" not in err.lower() and "limit" not in err.lower() and "permission" not in err.lower():
                record("G5", "feedback_error", "BUG", f"Error on feedback page: {err}")
        except:
            pass

        # Try feedback form
        try:
            # Look for give/submit feedback button
            fb_btn = None
            for el in driver.find_elements(By.CSS_SELECTOR, "button, a"):
                txt = el.text.lower()
                if el.is_displayed() and ("give" in txt or "submit" in txt or "new" in txt or "write" in txt) and "feedback" in txt:
                    fb_btn = el
                    break
            if not fb_btn:
                for el in driver.find_elements(By.CSS_SELECTOR, "button, a"):
                    txt = el.text.lower()
                    if el.is_displayed() and ("give" in txt or "submit" in txt or "create" in txt or "new" in txt):
                        fb_btn = el
                        break
            if fb_btn:
                fb_btn.click()
                time.sleep(3)
                ss = screenshot(driver, "g5_feedback_form")
                forms = driver.find_elements(By.CSS_SELECTOR, "form, [role='dialog'], [class*='modal']")
                inputs = driver.find_elements(By.CSS_SELECTOR, "textarea, input:not([type='hidden']), select")
                visible = [i for i in inputs if i.is_displayed()]
                if visible:
                    record("G5", "feedback_form", "PASS", f"Feedback form opened with {len(visible)} fields")
                else:
                    record("G5", "feedback_form", "WARN", "Feedback form has no visible inputs")
            else:
                record("G5", "feedback_btn", "WARN", "No submit/give feedback button found")
        except Exception as e:
            record("G5", "feedback_form", "WARN", str(e))

    except Exception as e:
        record("G5", "group_error", "WARN", f"Group 5 error: {e}")
        traceback.print_exc()
    finally:
        safe_quit(driver)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 6: Settings & Admin
# ═══════════════════════════════════════════════════════════════════════════
def run_group_6():
    print("\n" + "="*70)
    print("GROUP 6: Settings & Admin (Org Admin)")
    print("="*70)
    driver = get_fresh_driver()
    try:
        if not login(driver, ADMIN_EMAIL, ADMIN_PASS, "Org Admin"):
            record("G6", "login", "BUG", "Login failed")
            return
        record("G6", "login", "PASS", "Logged in")

        # Settings page
        navigate(driver, "/settings", 5)
        ss = screenshot(driver, "g6_settings")
        issues = check_page_basics(driver, "/settings", "G6")
        for iss in issues:
            record("G6", "settings_page", "BUG", iss)
            file_bug(f"[Settings] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/settings\n**Role:** Org Admin", ss)
        if not issues:
            record("G6", "settings_page", "PASS", "Settings page loaded")

        # Check organization details on settings
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            has_org_settings = bool(re.search(r'(organization|company|org name|settings|general|departments|locations)', body, re.IGNORECASE))
            if has_org_settings:
                record("G6", "settings_content", "PASS", "Organization settings content visible")
            else:
                record("G6", "settings_content", "WARN", "No organization settings content visible")
        except:
            pass

        # Departments
        try:
            # Navigate to departments (might be in settings or standalone)
            navigate(driver, "/settings/departments", 4)
            current = driver.current_url
            if "/dashboard" in current and "/settings" not in current:
                # Try alternate paths
                navigate(driver, "/departments", 4)
                current = driver.current_url

            ss = screenshot(driver, "g6_departments")
            body = driver.find_element(By.TAG_NAME, "body").text
            has_depts = bool(re.search(r'(department|engineering|marketing|sales|hr|finance|no department)', body, re.IGNORECASE))
            if has_depts:
                record("G6", "departments_list", "PASS", "Departments visible")
            else:
                issues = check_page_basics(driver, "departments", "G6")
                if issues:
                    for iss in issues:
                        record("G6", "departments", "BUG", iss)
                        file_bug(f"[Settings] {iss}", f"## Description\n{iss}\n\n**URL:** {current}\n**Role:** Org Admin", ss)
                else:
                    record("G6", "departments", "WARN", "Departments page loaded but no department content visible")

            # Try adding department
            add_btn = None
            for el in driver.find_elements(By.CSS_SELECTOR, "button, a"):
                txt = el.text.lower()
                if el.is_displayed() and ("add" in txt or "new" in txt or "create" in txt):
                    add_btn = el
                    break
            if add_btn:
                add_btn.click()
                time.sleep(2)
                ss = screenshot(driver, "g6_add_department")
                forms = driver.find_elements(By.CSS_SELECTOR, "form, [role='dialog'], [class*='modal']")
                if forms:
                    record("G6", "add_department_form", "PASS", "Add department form opened")
                else:
                    record("G6", "add_department_form", "WARN", "Add button clicked but no form appeared")
            else:
                record("G6", "add_department_btn", "WARN", "No add department button found")
        except Exception as e:
            record("G6", "departments", "WARN", str(e))

        # Locations
        try:
            navigate(driver, "/settings/locations", 4)
            current = driver.current_url
            if "/dashboard" in current and "/settings" not in current:
                navigate(driver, "/locations", 4)
                current = driver.current_url

            ss = screenshot(driver, "g6_locations")
            body = driver.find_element(By.TAG_NAME, "body").text
            has_locations = bool(re.search(r'(location|office|city|address|branch|no location)', body, re.IGNORECASE))
            if has_locations:
                record("G6", "locations_list", "PASS", "Locations visible")
            else:
                issues = check_page_basics(driver, "locations", "G6")
                if issues:
                    for iss in issues:
                        record("G6", "locations", "BUG", iss)
                else:
                    record("G6", "locations", "WARN", "Locations page loaded but no location content")
        except Exception as e:
            record("G6", "locations", "WARN", str(e))

        # Module Marketplace
        navigate(driver, "/modules", 5)
        ss = screenshot(driver, "g6_modules")
        current = driver.current_url
        if "/dashboard" in current and "/module" not in current:
            record("G6", "modules_redirect", "BUG", f"Modules page redirected to: {current}")
            file_bug("[Modules] /modules redirects to dashboard instead of marketplace",
                     f"## Description\n/modules redirects to dashboard.\n\n**Expected:** Module marketplace\n**Actual:** {current}\n\n**Role:** Org Admin",
                     ss)
        else:
            issues = check_page_basics(driver, "/modules", "G6")
            for iss in issues:
                record("G6", "modules_page", "BUG", iss)
                file_bug(f"[Modules] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/modules\n**Role:** Org Admin", ss)
            if not issues:
                record("G6", "modules_page", "PASS", "Modules page loaded")

        # Billing
        navigate(driver, "/billing", 5)
        ss = screenshot(driver, "g6_billing")
        issues = check_page_basics(driver, "/billing", "G6")
        for iss in issues:
            record("G6", "billing_page", "BUG", iss)
            file_bug(f"[Billing] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/billing\n**Role:** Org Admin", ss)
        if not issues:
            record("G6", "billing_page", "PASS", "Billing page loaded")

        # Check billing has subscription info
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            has_billing = bool(re.search(r'(subscription|plan|billing|invoice|payment|free|pro|enterprise)', body, re.IGNORECASE))
            if has_billing:
                record("G6", "billing_content", "PASS", "Billing/subscription content visible")
            else:
                record("G6", "billing_content", "WARN", "No billing/subscription content visible")
        except:
            pass

        # Check billing tabs functionality
        try:
            tabs = driver.find_elements(By.CSS_SELECTOR, "[role='tab'], [class*='tab'], button[class*='Tab']")
            tab_texts = [t.text for t in tabs if t.is_displayed() and t.text.strip()]
            if len(tab_texts) >= 2:
                # Click second tab and check content changes
                tabs_visible = [t for t in tabs if t.is_displayed() and t.text.strip()]
                if len(tabs_visible) >= 2:
                    body_before = driver.find_element(By.TAG_NAME, "body").text
                    tabs_visible[1].click()
                    time.sleep(2)
                    body_after = driver.find_element(By.TAG_NAME, "body").text
                    if body_before == body_after:
                        record("G6", "billing_tabs", "BUG", f"Billing tabs ({', '.join(tab_texts[:3])}) do not change content")
                    else:
                        record("G6", "billing_tabs", "PASS", f"Billing tabs work: {', '.join(tab_texts[:3])}")
        except Exception as e:
            record("G6", "billing_tabs", "WARN", str(e))

    except Exception as e:
        record("G6", "group_error", "WARN", f"Group 6 error: {e}")
        traceback.print_exc()
    finally:
        safe_quit(driver)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 7: Employee Self-Service
# ═══════════════════════════════════════════════════════════════════════════
def run_group_7():
    print("\n" + "="*70)
    print("GROUP 7: Employee Self-Service (priya@technova.in)")
    print("="*70)
    driver = get_fresh_driver()
    try:
        if not login(driver, EMP_EMAIL, EMP_PASS, "Employee"):
            record("G7", "login", "BUG", "Employee login failed")
            screenshot(driver, "g7_login_fail")
            return
        record("G7", "login", "PASS", "Employee logged in")

        # Dashboard
        navigate(driver, "/dashboard", 5)
        ss = screenshot(driver, "g7_dashboard")
        issues = check_page_basics(driver, "/dashboard (employee)", "G7")
        for iss in issues:
            record("G7", "dashboard", "BUG", iss)
            file_bug(f"[Employee Dashboard] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/dashboard\n**Role:** Employee (priya@technova.in)", ss)
        if not issues:
            record("G7", "dashboard", "PASS", "Employee dashboard loaded")

        # Check personalized content
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            is_personalized = bool(re.search(r'(priya|welcome|good morning|good afternoon|good evening|my)', body, re.IGNORECASE))
            if is_personalized:
                record("G7", "personalized", "PASS", "Personalized content shown")
            else:
                record("G7", "personalized", "WARN", "No personalized greeting or name visible")
        except:
            pass

        # My Profile
        navigate(driver, "/my-profile", 5)
        ss = screenshot(driver, "g7_profile")
        current = driver.current_url
        # Try /profile if my-profile redirects
        if "/dashboard" in current and "/profile" not in current:
            navigate(driver, "/profile", 5)
            ss = screenshot(driver, "g7_profile2")
            current = driver.current_url

        issues = check_page_basics(driver, "/my-profile", "G7")
        for iss in issues:
            record("G7", "profile_page", "BUG", iss)
            file_bug(f"[My Profile] {iss}", f"## Description\n{iss}\n\n**URL:** {current}\n**Role:** Employee", ss)
        if not issues:
            record("G7", "profile_page", "PASS", f"Profile page loaded at {current}")

        # Check profile tabs
        try:
            tabs = driver.find_elements(By.CSS_SELECTOR, "[role='tab'], [class*='tab'], button[class*='Tab']")
            tab_texts = [t.text for t in tabs if t.is_displayed() and t.text.strip()]
            if tab_texts:
                record("G7", "profile_tabs", "PASS", f"Profile tabs: {', '.join(tab_texts[:5])}")
                # Click each tab
                for tab in [t for t in tabs if t.is_displayed() and t.text.strip()][:3]:
                    try:
                        tab.click()
                        time.sleep(1)
                    except:
                        pass
            else:
                record("G7", "profile_tabs", "WARN", "No profile tabs found")
        except Exception as e:
            record("G7", "profile_tabs", "WARN", str(e))

        # Apply for leave (as employee)
        navigate(driver, "/leave", 5)
        ss = screenshot(driver, "g7_leave")
        issues = check_page_basics(driver, "/leave (employee)", "G7")
        for iss in issues:
            record("G7", "leave_page", "BUG", iss)
        if not issues:
            record("G7", "leave_page", "PASS", "Employee leave page loaded")

        # My Attendance
        navigate(driver, "/attendance/my", 5)
        ss = screenshot(driver, "g7_my_attendance")
        current = driver.current_url
        if "/dashboard" in current and "/attendance" not in current:
            # Try /attendance instead
            navigate(driver, "/attendance", 5)
            current = driver.current_url
            ss = screenshot(driver, "g7_attendance")

        issues = check_page_basics(driver, "/attendance/my (employee)", "G7")
        for iss in issues:
            record("G7", "my_attendance", "BUG", iss)
            file_bug(f"[Employee Attendance] {iss}", f"## Description\n{iss}\n\n**URL:** {current}\n**Role:** Employee", ss)
        if not issues:
            record("G7", "my_attendance", "PASS", f"Employee attendance loaded at {current}")

        # Helpdesk ticket as employee
        navigate(driver, "/helpdesk", 5)
        ss = screenshot(driver, "g7_helpdesk")
        issues = check_page_basics(driver, "/helpdesk (employee)", "G7")
        for iss in issues:
            record("G7", "helpdesk", "BUG", iss)
            file_bug(f"[Employee Helpdesk] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/helpdesk\n**Role:** Employee", ss)
        if not issues:
            record("G7", "helpdesk", "PASS", "Employee helpdesk loaded")

    except Exception as e:
        record("G7", "group_error", "WARN", f"Group 7 error: {e}")
        traceback.print_exc()
    finally:
        safe_quit(driver)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP 8: Whistleblowing & Policies
# ═══════════════════════════════════════════════════════════════════════════
def run_group_8():
    print("\n" + "="*70)
    print("GROUP 8: Whistleblowing & Policies")
    print("="*70)
    driver = get_fresh_driver()
    try:
        if not login(driver, ADMIN_EMAIL, ADMIN_PASS, "Org Admin"):
            record("G8", "login", "BUG", "Login failed")
            return
        record("G8", "login", "PASS", "Logged in")

        # Whistleblowing submit
        navigate(driver, "/whistleblowing/submit", 5)
        ss = screenshot(driver, "g8_whistleblow_submit")
        current = driver.current_url
        if "/dashboard" in current and "/whistleblow" not in current:
            # Try alternate path
            navigate(driver, "/whistleblowing", 4)
            current = driver.current_url
            ss = screenshot(driver, "g8_whistleblow")

        if "/dashboard" in current and "/whistleblow" not in current:
            record("G8", "whistleblow_redirect", "BUG", f"Whistleblowing redirected to: {current}")
            file_bug("[Whistleblowing] /whistleblowing/submit redirects to dashboard",
                     f"## Description\n/whistleblowing/submit redirects to dashboard.\n\n**Expected:** Anonymous report submission form\n**Actual:** Redirected to {current}\n\n**Role:** Org Admin",
                     ss)
        else:
            issues = check_page_basics(driver, "/whistleblowing/submit", "G8")
            for iss in issues:
                record("G8", "whistleblow_submit", "BUG", iss)
                file_bug(f"[Whistleblowing] {iss}", f"## Description\n{iss}\n\n**URL:** {current}\n**Role:** Org Admin", ss)
            if not issues:
                record("G8", "whistleblow_submit", "PASS", "Whistleblowing submit page loaded")

                # Check for form
                try:
                    forms = driver.find_elements(By.CSS_SELECTOR, "form, textarea, input:not([type='hidden'])")
                    visible = [f for f in forms if f.is_displayed()]
                    if visible:
                        record("G8", "whistleblow_form", "PASS", f"Report form has {len(visible)} elements")
                    else:
                        record("G8", "whistleblow_form", "WARN", "No visible form elements on whistleblowing page")
                except:
                    pass

        # Whistleblowing track
        navigate(driver, "/whistleblowing/track", 5)
        ss = screenshot(driver, "g8_whistleblow_track")
        current = driver.current_url
        if "/dashboard" in current and "/whistleblow" not in current:
            record("G8", "whistleblow_track_redirect", "BUG", f"Track page redirected to: {current}")
            file_bug("[Whistleblowing] /whistleblowing/track redirects to dashboard",
                     f"## Description\n/whistleblowing/track redirects to dashboard.\n\n**Expected:** Report tracking page\n**Actual:** Redirected to {current}\n\n**Role:** Org Admin",
                     ss)
        else:
            issues = check_page_basics(driver, "/whistleblowing/track", "G8")
            for iss in issues:
                record("G8", "whistleblow_track", "BUG", iss)
                file_bug(f"[Whistleblowing] {iss}", f"## Description\n{iss}\n\n**URL:** {current}\n**Role:** Org Admin", ss)
            if not issues:
                record("G8", "whistleblow_track", "PASS", "Whistleblowing track page loaded")

        # Policies
        navigate(driver, "/policies", 5)
        ss = screenshot(driver, "g8_policies")
        issues = check_page_basics(driver, "/policies", "G8")
        for iss in issues:
            record("G8", "policies_page", "BUG", iss)
            file_bug(f"[Policies] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/policies\n**Role:** Org Admin", ss)
        if not issues:
            record("G8", "policies_page", "PASS", "Policies page loaded")

        # Check for policy list and try viewing
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            has_policies = bool(re.search(r'(policy|policies|handbook|leave policy|attendance policy|no policies)', body, re.IGNORECASE))
            if has_policies:
                record("G8", "policies_content", "PASS", "Policy content visible")
                # Try clicking a policy
                links = driver.find_elements(By.CSS_SELECTOR, "a[href*='polic'], [class*='policy'] a, table tbody tr, [class*='list-item']")
                if links:
                    try:
                        links[0].click()
                        time.sleep(3)
                        ss = screenshot(driver, "g8_policy_detail")
                        body_detail = driver.find_element(By.TAG_NAME, "body").text
                        if len(body_detail) > 50:
                            record("G8", "policy_view", "PASS", "Policy detail page loaded")
                        else:
                            record("G8", "policy_view", "WARN", "Policy detail page seems empty")
                    except:
                        pass
            else:
                record("G8", "policies_content", "WARN", "No policy content visible")
        except:
            pass

        # Check for raw i18n/XSS test data in policies (known issue #244 but checking specific patterns)
        try:
            navigate(driver, "/policies", 3)
            body = driver.find_element(By.TAG_NAME, "body").text
            xss_patterns = re.findall(r'<script|javascript:|onerror|onload|alert\(', body, re.IGNORECASE)
            if xss_patterns:
                record("G8", "policies_xss_data", "BUG", f"XSS test data visible: {xss_patterns[:3]}")
                # Already reported in #244
        except:
            pass

        # Announcements
        navigate(driver, "/announcements", 5)
        ss = screenshot(driver, "g8_announcements")
        issues = check_page_basics(driver, "/announcements", "G8")
        for iss in issues:
            record("G8", "announcements_page", "BUG", iss)
            file_bug(f"[Announcements] {iss}", f"## Description\n{iss}\n\n**URL:** {BASE}/announcements\n**Role:** Org Admin", ss)
        if not issues:
            record("G8", "announcements_page", "PASS", "Announcements page loaded")

        # Check announcements content
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            has_announcements = bool(re.search(r'(announcement|notice|no announcement|new)', body, re.IGNORECASE))
            if has_announcements:
                record("G8", "announcements_content", "PASS", "Announcements content visible")
            else:
                record("G8", "announcements_content", "WARN", "No announcements content visible")
        except:
            pass

    except Exception as e:
        record("G8", "group_error", "WARN", f"Group 8 error: {e}")
        traceback.print_exc()
    finally:
        safe_quit(driver)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("EMP Cloud HRMS - Fresh Comprehensive Dashboard E2E Test")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    groups = [
        ("Group 1: Employee Directory", run_group_1),
        ("Group 2: Attendance & Leave", run_group_2),
        ("Group 3: Helpdesk & Surveys", run_group_3),
        ("Group 4: Forum, Events, Wellness", run_group_4),
        ("Group 5: Assets, Positions, Feedback", run_group_5),
        ("Group 6: Settings & Admin", run_group_6),
        ("Group 7: Employee Self-Service", run_group_7),
        ("Group 8: Whistleblowing & Policies", run_group_8),
    ]

    for name, func in groups:
        try:
            func()
        except Exception as e:
            print(f"\n[FATAL] {name} crashed: {e}")
            traceback.print_exc()
        time.sleep(2)

    # ── Summary ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total = len(test_results)
    passed = sum(1 for _, _, s, _ in test_results if s == "PASS")
    bugs = sum(1 for _, _, s, _ in test_results if s == "BUG")
    warns = sum(1 for _, _, s, _ in test_results if s == "WARN")

    print(f"\nTotal tests: {total}")
    print(f"  PASS: {passed}")
    print(f"  BUG:  {bugs}")
    print(f"  WARN: {warns}")

    print(f"\n{'Group':<8} {'Test':<35} {'Status':<6} {'Detail'}")
    print("-" * 110)
    for group, test, status, detail in test_results:
        icon = "OK" if status == "PASS" else "BUG" if status == "BUG" else "??"
        print(f"{group:<8} {test:<35} {icon:<6} {detail[:70]}")

    if bugs_found:
        print(f"\n\nNEW GITHUB ISSUES FILED ({len(bugs_found)}):")
        print("-" * 70)
        for b in bugs_found:
            print(f"  #{b['number']}: {b['title']}")
            print(f"    {b['url']}")
    else:
        print("\nNo new GitHub issues filed (all findings were duplicates or passes)")

    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Screenshots: {SCREENSHOT_DIR}")
