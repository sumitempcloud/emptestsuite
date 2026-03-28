"""
EMP Cloud HRMS — Full Employee Dashboard E2E Test
Tests all employee-accessible modules, self-service features, and RBAC restrictions.
Resilient to Chrome crashes with driver recovery.
"""

import os, sys, time, json, traceback, re, requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\full_dashboard_employee"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs = []
test_results = []
sidebar_links = []

# Global token cache
_tokens = {}
_user_data = {}
_org_data = {}

def ts():
    return datetime.now().strftime("%H:%M:%S")

def log(msg):
    print(f"[{ts()}] {msg}", flush=True)

def safe_screenshot(driver, name):
    try:
        safe = re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:80]
        path = os.path.join(SCREENSHOT_DIR, f"{safe}.png")
        driver.save_screenshot(path)
        return path
    except:
        return ""

def record(name, status, details="", ss_path=""):
    test_results.append({"test": name, "status": status, "details": details, "screenshot": ss_path})
    icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "WARN"
    log(f"  [{icon}] {name}: {details}")

def record_bug(title, body, severity="medium", ss_path=""):
    bugs.append({"title": title, "body": body, "severity": severity, "screenshot": ss_path})
    log(f"  [BUG] {title}")

def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-extensions")
    for attempt in range(3):
        try:
            d = webdriver.Chrome(options=opts)
            d.set_page_load_timeout(30)
            d.implicitly_wait(3)
            return d
        except Exception as e:
            log(f"  Driver attempt {attempt+1} failed: {str(e)[:80]}")
            time.sleep(3)
    raise Exception("Failed to create Chrome driver after 3 attempts")

def wait_for_page(driver, timeout=12):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except:
        pass
    time.sleep(1.5)

def is_driver_alive(driver):
    try:
        _ = driver.current_url
        return True
    except:
        return False

def get_api_tokens():
    """Get auth tokens from API (cached)."""
    global _tokens, _user_data, _org_data
    if _tokens:
        return _tokens, _user_data, _org_data
    resp = requests.post(f"{API_URL}/api/v1/auth/login",
                         json={"email": EMP_EMAIL, "password": EMP_PASS}, timeout=15)
    if resp.status_code != 200:
        raise Exception(f"API login failed: {resp.status_code}")
    data = resp.json()["data"]
    _tokens = data["tokens"]
    _user_data = data["user"]
    _org_data = data["org"]
    return _tokens, _user_data, _org_data

def login_driver(driver):
    """Login via UI using Enter key (most reliable method)."""
    driver.get(BASE_URL + "/login")
    time.sleep(3)
    wait_for_page(driver)

    email = driver.find_element(By.CSS_SELECTOR, "input[name='email']")
    email.clear()
    email.send_keys(EMP_EMAIL)

    pw = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
    pw.clear()
    pw.send_keys(EMP_PASS)
    time.sleep(0.5)

    # Submit via Enter key (button click is unreliable in headless)
    pw.send_keys(Keys.RETURN)
    time.sleep(6)
    wait_for_page(driver)

    cur = driver.current_url
    if "/login" in cur.split("?")[0].split("#")[0]:
        safe_screenshot(driver, "login_debug")
        raise Exception(f"Login failed, still at: {cur}")

    log(f"  Logged in: {cur}")
    return driver

def get_driver_logged_in():
    """Create a new driver and login."""
    d = create_driver()
    return login_driver(d)

def safe_get(driver, url):
    """Navigate to URL with crash recovery. Returns (driver, success)."""
    try:
        if not is_driver_alive(driver):
            raise Exception("Driver dead")
        driver.get(url)
        wait_for_page(driver)
        return driver, True
    except:
        log("  Driver crashed, recovering...")
        try:
            driver.quit()
        except:
            pass
        try:
            driver = get_driver_logged_in()
            driver.get(url)
            wait_for_page(driver)
            return driver, True
        except Exception as e:
            log(f"  Recovery failed: {str(e)[:100]}")
            return driver, False


def phase1_sidebar_mapping(driver):
    """Map the entire sidebar."""
    log("\n=== PHASE 1: EMPLOYEE SIDEBAR MAPPING ===")
    global sidebar_links

    driver, ok = safe_get(driver, BASE_URL + "/dashboard")
    if not ok:
        record("Sidebar Mapping", "FAIL", "Could not load dashboard")
        return driver

    time.sleep(2)
    safe_screenshot(driver, "02_sidebar_full")

    # Collect sidebar links
    link_elements = []
    for sel in ["nav a", ".sidebar a", "[class*='sidebar'] a", "[class*='Sidebar'] a",
                "aside a", "[role='navigation'] a", ".nav-menu a", ".side-nav a"]:
        try:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) > 3:
                link_elements = found
                break
        except:
            pass

    if not link_elements:
        all_a = driver.find_elements(By.TAG_NAME, "a")
        for a in all_a:
            try:
                loc = a.location
                if loc['x'] < 300 and a.is_displayed():
                    link_elements.append(a)
            except:
                pass

    seen_hrefs = set()
    for a in link_elements:
        try:
            href = a.get_attribute("href") or ""
            text = a.text.strip()
            if not text:
                text = a.get_attribute("aria-label") or a.get_attribute("title") or ""
            text = text.strip()
            if not text or not href:
                continue
            if href.startswith(BASE_URL):
                href_path = href.replace(BASE_URL, "")
            else:
                href_path = href
            if href_path in seen_hrefs:
                continue
            seen_hrefs.add(href_path)
            sidebar_links.append({"text": text, "href": href_path, "full_url": href})
        except:
            pass

    log(f"  Found {len(sidebar_links)} sidebar links:")
    for link in sidebar_links:
        log(f"    - {link['text']}: {link['href']}")

    admin_only = ["Settings", "Billing", "Super Admin", "AI Config", "Logs",
                  "Organization", "Permissions", "Payroll Settings", "Audit", "System"]
    visible_admin = [l['text'] for l in sidebar_links
                     if any(a.lower() in l['text'].lower() for a in admin_only)]

    if visible_admin:
        ss = safe_screenshot(driver, "03_admin_modules_visible")
        record("Sidebar RBAC", "FAIL", f"Admin modules visible: {visible_admin}", ss)
        record_bug(f"[Employee RBAC] Admin sidebar items visible: {', '.join(visible_admin)}",
                   f"Employee (priya@technova.in) sees admin items: {', '.join(visible_admin)}", "high", ss)
    else:
        record("Sidebar RBAC", "PASS", "No admin-only modules visible")

    record("Sidebar Mapping", "PASS", f"Mapped {len(sidebar_links)} links")
    return driver


def phase2_test_every_page(driver):
    """Visit each sidebar link."""
    log("\n=== PHASE 2: TEST EVERY EMPLOYEE PAGE ===")

    for i, link in enumerate(sidebar_links):
        name = link['text']
        href = link['full_url']
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name)[:40]

        log(f"  Testing [{i+1}/{len(sidebar_links)}]: {name} -> {link['href']}")

        if href and not href.startswith(BASE_URL) and "empcloud.com" not in href:
            record(f"Page: {name}", "SKIP", f"External: {href}")
            continue

        driver, ok = safe_get(driver, href)
        if not ok:
            record(f"Page: {name}", "FAIL", "Navigation failed (driver crash)")
            continue

        try:
            time.sleep(1)
            ss = safe_screenshot(driver, f"04_page_{i:02d}_{safe_name}")
            cur_url = driver.current_url
            page_src = driver.page_source[:5000].lower()
            body_text = driver.find_element(By.TAG_NAME, "body").text

            is_404 = "404" in driver.title.lower() or "not found" in page_src
            is_error = "500" in driver.title.lower() or "server error" in page_src
            is_blank = len(body_text.strip()) < 20

            # raw i18n
            raw_i18n = re.findall(r'\b(nav\.|page\.|label\.|btn\.|msg\.)[a-zA-Z.]+', body_text)

            if is_404:
                record(f"Page: {name}", "FAIL", f"404 at {cur_url}", ss)
                record_bug(f"[Employee] '{name}' returns 404", f"URL: {cur_url}", "high", ss)
            elif is_error:
                record(f"Page: {name}", "FAIL", f"Server error at {cur_url}", ss)
                record_bug(f"[Employee] '{name}' server error", f"URL: {cur_url}", "high", ss)
            elif is_blank:
                record(f"Page: {name}", "FAIL", f"Blank page at {cur_url}", ss)
                record_bug(f"[Employee] '{name}' blank page", f"URL: {cur_url}", "high", ss)
            else:
                det = f"OK at {cur_url}"
                if raw_i18n:
                    det += f" | i18n: {raw_i18n[:3]}"
                    record_bug(f"[Employee] Raw i18n keys on '{name}'", f"URL: {cur_url}\nKeys: {raw_i18n[:10]}", "low", ss)
                record(f"Page: {name}", "PASS", det, ss)
        except Exception as ex:
            record(f"Page: {name}", "FAIL", f"Error: {str(ex)[:150]}")

    return driver


def find_sidebar_url(keywords):
    """Find sidebar link URL matching any keyword."""
    for link in sidebar_links:
        for kw in keywords:
            if kw in link['text'].lower():
                return link['full_url']
    return None


def phase3a_dashboard(driver):
    log("\n=== PHASE 3A: EMPLOYEE DASHBOARD ===")
    driver, ok = safe_get(driver, BASE_URL + "/dashboard")
    if not ok:
        record("Dashboard", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "10_dashboard")
    body = driver.find_element(By.TAG_NAME, "body").text

    if "priya" in body.lower() or "Priya" in body:
        record("Dashboard: Employee Name", "PASS", "Priya visible on dashboard")
    else:
        record("Dashboard: Employee Name", "WARN", "Name not visible", ss)

    widgets = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='Card'], [class*='widget'], [class*='stat']")
    record("Dashboard: Widgets", "PASS" if widgets else "WARN",
           f"{len(widgets)} widgets found" if widgets else "No widgets found")

    quick_kws = ["apply leave", "check-in", "clock in", "mark attendance", "quick action"]
    has_quick = any(k in body.lower() for k in quick_kws)
    record("Dashboard: Quick Actions", "PASS" if has_quick else "WARN",
           "Quick actions found" if has_quick else "No quick action text found")

    i18n = re.findall(r'\b(nav\.|page\.|label\.|btn\.|msg\.)[a-zA-Z.]+', body)
    if i18n:
        record("Dashboard: i18n", "FAIL", f"Raw keys: {i18n[:5]}", ss)
        record_bug("[Dashboard] Raw i18n keys", f"Keys: {i18n[:10]}", "medium", ss)
    else:
        record("Dashboard: i18n", "PASS", "No raw i18n keys")

    return driver


def phase3b_my_profile(driver):
    log("\n=== PHASE 3B: MY PROFILE ===")
    url = find_sidebar_url(["profile"]) or BASE_URL + "/my-profile"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("My Profile", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "11_my_profile")
    body = driver.find_element(By.TAG_NAME, "body").text

    if "priya" in body.lower() or "technova" in body.lower():
        record("My Profile: Data", "PASS", "Employee data visible")
    else:
        record("My Profile: Data", "WARN", "Employee data not clearly visible", ss)

    tabs = driver.find_elements(By.CSS_SELECTOR, "[role='tab'], .MuiTab-root, [class*='tab-']")
    tab_texts = [t.text.strip() for t in tabs if t.text.strip()]
    if tab_texts:
        record("My Profile: Tabs", "PASS", f"Tabs: {tab_texts[:8]}")
        for tab in tabs[:5]:
            try:
                if tab.is_displayed():
                    tab.click()
                    time.sleep(1)
            except:
                pass
        safe_screenshot(driver, "11_profile_tabs")
    else:
        record("My Profile: Tabs", "WARN", "No tabs found", ss)

    edit_found = any("edit" in (b.text.lower() + (b.get_attribute("aria-label") or "").lower())
                     for b in driver.find_elements(By.CSS_SELECTOR, "button, a") if b.is_displayed())
    record("My Profile: Edit", "PASS" if edit_found else "WARN",
           "Edit available" if edit_found else "No edit button")

    i18n = re.findall(r'\b(nav\.|page\.|label\.|btn\.|msg\.)[a-zA-Z.]+', body)
    if i18n:
        record("My Profile: i18n", "FAIL", f"Raw keys: {i18n[:5]}", ss)
        record_bug("[My Profile] Raw i18n keys", f"Keys: {i18n[:10]}", "medium", ss)
    else:
        record("My Profile: i18n", "PASS", "No raw i18n keys")

    return driver


def phase3c_attendance(driver):
    log("\n=== PHASE 3C: MY ATTENDANCE ===")
    url = find_sidebar_url(["attendance"]) or BASE_URL + "/my-attendance"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("Attendance", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "12_my_attendance")
    body = driver.find_element(By.TAG_NAME, "body").text.lower()

    has_att = any(w in body for w in ["attendance", "check-in", "check in", "clock", "present", "absent", "punch"])
    record("Attendance: Content", "PASS" if has_att else "WARN",
           "Attendance content found" if has_att else "No attendance content", ss if not has_att else "")

    # Clock-in button
    clock_btn = None
    for b in driver.find_elements(By.CSS_SELECTOR, "button, a.btn"):
        bt = (b.text + " " + (b.get_attribute("aria-label") or "")).lower()
        if any(w in bt for w in ["clock in", "check-in", "check in", "punch in", "clock out", "check-out", "punch out"]):
            if b.is_displayed():
                clock_btn = b
                break

    if clock_btn:
        record("Attendance: Clock Button", "PASS", f"Found: {clock_btn.text.strip()}")
        try:
            clock_btn.click()
            time.sleep(2)
            safe_screenshot(driver, "12_attendance_clocked")
            record("Attendance: Clock Action", "PASS", "Clicked")
        except:
            record("Attendance: Clock Action", "WARN", "Click failed")
    else:
        record("Attendance: Clock Button", "WARN", "Not found", ss)

    calendar = driver.find_elements(By.CSS_SELECTOR, "[class*='calendar'], [class*='Calendar'], table, .fc")
    record("Attendance: Calendar", "PASS" if calendar else "WARN",
           "Calendar found" if calendar else "No calendar")

    return driver


def phase3d_leaves(driver):
    log("\n=== PHASE 3D: MY LEAVES ===")
    url = find_sidebar_url(["leave"]) or BASE_URL + "/my-leaves"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("Leaves", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "13_my_leaves")
    body = driver.find_element(By.TAG_NAME, "body").text

    balance = any(w in body.lower() for w in ["balance", "earned", "sick", "casual", "available", "remaining"])
    record("Leaves: Balance", "PASS" if balance else "WARN",
           "Balance info found" if balance else "No balance info", ss if not balance else "")

    # Apply leave
    apply_btn = None
    for b in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        if any(w in b.text.lower() for w in ["apply", "new leave", "request"]) and b.is_displayed():
            apply_btn = b
            break

    if apply_btn:
        record("Leaves: Apply Button", "PASS", f"Found: {apply_btn.text.strip()}")
        try:
            apply_btn.click()
            time.sleep(2)
            safe_screenshot(driver, "13_leave_form")

            # Fill leave type
            selects = driver.find_elements(By.CSS_SELECTOR, "select, [role='combobox'], [class*='Select']")
            if selects:
                try:
                    selects[0].click()
                    time.sleep(1)
                    opts = driver.find_elements(By.CSS_SELECTOR, "option, [role='option'], li[class*='option']")
                    for o in opts:
                        if o.is_displayed() and o.text.strip():
                            o.click()
                            time.sleep(0.5)
                            break
                except:
                    pass

            # Fill dates
            date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[placeholder*='date' i]")
            if date_inputs:
                d1 = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                d2 = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d")
                try:
                    date_inputs[0].clear()
                    date_inputs[0].send_keys(d1)
                    if len(date_inputs) > 1:
                        date_inputs[1].clear()
                        date_inputs[1].send_keys(d2)
                except:
                    pass

            # Reason
            for ta in driver.find_elements(By.CSS_SELECTOR, "textarea"):
                if ta.is_displayed():
                    try:
                        ta.clear()
                        ta.send_keys("E2E test leave - please ignore")
                        break
                    except:
                        pass

            safe_screenshot(driver, "13_leave_filled")

            # Submit
            for b in driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button"):
                if any(w in b.text.lower() for w in ["submit", "apply", "save"]) and b.is_displayed():
                    b.click()
                    time.sleep(3)
                    safe_screenshot(driver, "13_leave_submitted")
                    record("Leaves: Submit", "PASS", "Submitted")
                    break
        except Exception as ex:
            record("Leaves: Apply Flow", "WARN", f"Error: {str(ex)[:100]}")
    else:
        record("Leaves: Apply Button", "WARN", "Not found", ss)

    # History
    driver, _ = safe_get(driver, url)
    time.sleep(1)
    tables = driver.find_elements(By.CSS_SELECTOR, "table, [role='table'], [class*='list'], [class*='table']")
    record("Leaves: History", "PASS" if tables else "WARN",
           "Table found" if tables else "No history table")

    return driver


def phase3e_documents(driver):
    log("\n=== PHASE 3E: MY DOCUMENTS ===")
    url = find_sidebar_url(["document"]) or BASE_URL + "/my-documents"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("Documents", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "14_my_documents")
    body = driver.find_element(By.TAG_NAME, "body").text.lower()

    has_doc = any(w in body for w in ["document", "file", "upload", "mandatory", "download", "certificate", "pending"])
    record("Documents: Content", "PASS" if has_doc else "WARN",
           "Document content found" if has_doc else "No doc content", ss if not has_doc else "")

    dl_btns = [b for b in driver.find_elements(By.CSS_SELECTOR, "button, a")
               if "download" in (b.text + (b.get_attribute("title") or "")).lower() and b.is_displayed()]
    record("Documents: Download", "PASS" if dl_btns else "WARN",
           f"{len(dl_btns)} download buttons" if dl_btns else "No download buttons")

    return driver


def phase3f_assets(driver):
    log("\n=== PHASE 3F: MY ASSETS ===")
    url = find_sidebar_url(["asset"]) or BASE_URL + "/my-assets"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("Assets", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "15_my_assets")
    body = driver.find_element(By.TAG_NAME, "body").text.lower()

    has = any(w in body for w in ["asset", "laptop", "device", "equipment", "assigned", "no asset"])
    record("Assets: Content", "PASS" if has else "WARN",
           "Asset content found" if has else "No asset content (may be empty)", ss if not has else "")

    return driver


def phase3g_events(driver):
    log("\n=== PHASE 3G: MY EVENTS ===")
    url = find_sidebar_url(["event"]) or BASE_URL + "/my-events"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("Events", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "16_my_events")
    body = driver.find_element(By.TAG_NAME, "body").text.lower()

    has = any(w in body for w in ["event", "upcoming", "calendar", "rsvp", "no event"])
    record("Events: Content", "PASS" if has else "WARN",
           "Event content found" if has else "No event content", ss if not has else "")

    rsvp = None
    for b in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        if "rsvp" in b.text.lower() and b.is_displayed():
            rsvp = b
            break
    if rsvp:
        try:
            rsvp.click()
            time.sleep(2)
            safe_screenshot(driver, "16_events_rsvp")
            record("Events: RSVP", "PASS", "RSVP clicked")
        except:
            record("Events: RSVP", "WARN", "RSVP click failed")
    else:
        record("Events: RSVP", "WARN", "No RSVP button (may be no events)")

    return driver


def phase3h_wellness(driver):
    log("\n=== PHASE 3H: MY WELLNESS ===")
    url = find_sidebar_url(["wellness"]) or BASE_URL + "/my-wellness"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("Wellness", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "17_my_wellness")
    body = driver.find_element(By.TAG_NAME, "body").text.lower()

    has = any(w in body for w in ["wellness", "mood", "energy", "sleep", "check-in", "well-being", "health"])
    record("Wellness: Content", "PASS" if has else "WARN",
           "Wellness content found" if has else "No wellness content", ss if not has else "")

    # Try check-in
    checkin = None
    for b in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        bt = b.text.lower()
        if any(w in bt for w in ["check-in", "check in", "daily", "log mood", "submit"]) and b.is_displayed():
            checkin = b
            break

    if checkin:
        try:
            checkin.click()
            time.sleep(2)
            safe_screenshot(driver, "17_wellness_checkin")
            record("Wellness: Check-in", "PASS", f"Clicked: {checkin.text.strip()}")

            # Try mood selection
            for r in driver.find_elements(By.CSS_SELECTOR, "input[type='radio'], [role='radio'], [class*='emoji'], [class*='mood']")[:3]:
                try:
                    if r.is_displayed():
                        r.click()
                        time.sleep(0.5)
                except:
                    pass

            # Submit
            for sb in driver.find_elements(By.CSS_SELECTOR, "button"):
                if any(w in sb.text.lower() for w in ["submit", "save", "done"]) and sb.is_displayed():
                    sb.click()
                    time.sleep(2)
                    safe_screenshot(driver, "17_wellness_submitted")
                    record("Wellness: Submit", "PASS", "Submitted")
                    break
        except:
            record("Wellness: Check-in", "WARN", "Error during check-in")
    else:
        record("Wellness: Check-in", "WARN", "No check-in button", ss)

    return driver


def phase3i_feedback(driver):
    log("\n=== PHASE 3I: MY FEEDBACK ===")
    url = find_sidebar_url(["feedback"]) or BASE_URL + "/my-feedback"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("Feedback", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "18_my_feedback")
    body = driver.find_element(By.TAG_NAME, "body").text.lower()

    has = any(w in body for w in ["feedback", "suggestion", "review", "rate", "submit"])
    record("Feedback: Content", "PASS" if has else "WARN",
           "Feedback content found" if has else "No feedback content", ss if not has else "")

    # Try submitting
    for ta in driver.find_elements(By.CSS_SELECTOR, "textarea, input[type='text']"):
        if ta.is_displayed():
            try:
                ta.clear()
                ta.send_keys("E2E test feedback - please ignore")
                break
            except:
                pass

    for b in driver.find_elements(By.CSS_SELECTOR, "button"):
        if any(w in b.text.lower() for w in ["submit", "send", "save"]) and b.is_displayed():
            try:
                b.click()
                time.sleep(2)
                safe_screenshot(driver, "18_feedback_submitted")
                record("Feedback: Submit", "PASS", "Submitted")
            except:
                record("Feedback: Submit", "WARN", "Submit failed")
            break

    return driver


def phase3j_helpdesk(driver):
    log("\n=== PHASE 3J: HELPDESK ===")
    url = find_sidebar_url(["helpdesk", "ticket", "support"]) or BASE_URL + "/helpdesk"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("Helpdesk", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "19_helpdesk")
    body = driver.find_element(By.TAG_NAME, "body").text.lower()

    has = any(w in body for w in ["ticket", "helpdesk", "support", "issue", "request", "no ticket"])
    record("Helpdesk: Content", "PASS" if has else "WARN",
           "Helpdesk content found" if has else "No helpdesk content", ss if not has else "")

    # Create ticket
    create_btn = None
    for b in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        if any(w in b.text.lower() for w in ["new ticket", "create", "raise ticket", "add"]) and b.is_displayed():
            create_btn = b
            break

    if create_btn:
        try:
            create_btn.click()
            time.sleep(2)
            safe_screenshot(driver, "19_helpdesk_new")
            record("Helpdesk: Create Button", "PASS", f"Found: {create_btn.text.strip()}")

            for inp in driver.find_elements(By.CSS_SELECTOR, "input[type='text']"):
                if inp.is_displayed() and not inp.get_attribute("value"):
                    try:
                        inp.send_keys("E2E Test Ticket")
                        break
                    except:
                        pass

            for ta in driver.find_elements(By.CSS_SELECTOR, "textarea"):
                if ta.is_displayed():
                    try:
                        ta.send_keys("E2E test ticket - please ignore")
                        break
                    except:
                        pass

            safe_screenshot(driver, "19_helpdesk_filled")
        except:
            record("Helpdesk: Create Flow", "WARN", "Error in create flow")
    else:
        record("Helpdesk: Create Button", "WARN", "Not found", ss)

    return driver


def phase3k_announcements(driver):
    log("\n=== PHASE 3K: ANNOUNCEMENTS ===")
    url = find_sidebar_url(["announcement"]) or BASE_URL + "/announcements"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("Announcements", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "20_announcements")
    body = driver.find_element(By.TAG_NAME, "body").text.lower()

    has = any(w in body for w in ["announcement", "notice", "news", "update", "no announcement"])
    record("Announcements: Content", "PASS" if has else "WARN",
           "Content found" if has else "No content", ss if not has else "")

    create_btns = [b for b in driver.find_elements(By.CSS_SELECTOR, "button, a")
                   if any(w in b.text.lower() for w in ["create", "new", "add", "post"]) and b.is_displayed()]
    if create_btns:
        record("Announcements: RBAC", "WARN", "Employee sees create button", ss)
    else:
        record("Announcements: RBAC", "PASS", "No create button (correct)")

    return driver


def phase3l_policies(driver):
    log("\n=== PHASE 3L: POLICIES ===")
    url = find_sidebar_url(["polic"]) or BASE_URL + "/policies"
    driver, ok = safe_get(driver, url)
    if not ok:
        record("Policies", "FAIL", "Could not load")
        return driver

    time.sleep(2)
    ss = safe_screenshot(driver, "21_policies")
    body = driver.find_element(By.TAG_NAME, "body").text.lower()

    has = any(w in body for w in ["policy", "policies", "handbook", "guideline"])
    record("Policies: Content", "PASS" if has else "WARN",
           "Policy content found" if has else "No policy content", ss if not has else "")

    view_btns = [b for b in driver.find_elements(By.CSS_SELECTOR, "button, a")
                 if any(w in b.text.lower() for w in ["view", "read", "open", "download"]) and b.is_displayed()]
    if view_btns:
        try:
            view_btns[0].click()
            time.sleep(2)
            safe_screenshot(driver, "21_policy_view")
            record("Policies: View", "PASS", f"Clicked: {view_btns[0].text.strip()}")
        except:
            record("Policies: View", "WARN", "View click failed")
    else:
        record("Policies: View", "WARN", "No view button")

    return driver


def phase3m_chatbot(driver):
    log("\n=== PHASE 3M: AI CHATBOT ===")
    driver, ok = safe_get(driver, BASE_URL + "/dashboard")
    if not ok:
        record("Chatbot", "FAIL", "Could not load dashboard")
        return driver

    time.sleep(2)

    chatbot_btn = None
    for sel in ["[class*='chatbot']", "[class*='Chatbot']", "[class*='chat-bubble']",
                "[class*='chat-widget']", "[class*='ai-chat']", "[class*='fab']",
                "button[class*='chat']", "[id*='chat']", "[class*='assistant']",
                "[class*='float']"]:
        try:
            for e in driver.find_elements(By.CSS_SELECTOR, sel):
                if e.is_displayed():
                    chatbot_btn = e
                    break
            if chatbot_btn:
                break
        except:
            pass

    if not chatbot_btn:
        # Bottom-right positioned elements
        for b in driver.find_elements(By.CSS_SELECTOR, "button, div[role='button']"):
            try:
                if b.is_displayed() and b.location['x'] > 1500 and b.location['y'] > 700:
                    chatbot_btn = b
                    break
            except:
                pass

    if chatbot_btn:
        record("Chatbot: Button", "PASS", "Found chatbot bubble")
        try:
            chatbot_btn.click()
            time.sleep(2)
            safe_screenshot(driver, "22_chatbot_opened")

            chat_input = None
            for sel in ["input[placeholder*='message' i]", "input[placeholder*='ask' i]",
                        "input[placeholder*='type' i]", "textarea[placeholder*='message' i]",
                        "[class*='chat'] input", "[class*='chat'] textarea",
                        "textarea", "input[type='text']"]:
                try:
                    for e in driver.find_elements(By.CSS_SELECTOR, sel):
                        if e.is_displayed():
                            chat_input = e
                            break
                    if chat_input:
                        break
                except:
                    pass

            if chat_input:
                chat_input.clear()
                chat_input.send_keys("What is my leave balance?")
                chat_input.send_keys(Keys.RETURN)
                time.sleep(5)
                safe_screenshot(driver, "22_chatbot_response")
                record("Chatbot: Query", "PASS", "Sent question")
            else:
                record("Chatbot: Input", "WARN", "No chat input found")
        except Exception as ex:
            record("Chatbot: Interaction", "WARN", f"Error: {str(ex)[:100]}")
    else:
        ss = safe_screenshot(driver, "22_chatbot_not_found")
        record("Chatbot: Button", "WARN", "Not found", ss)

    return driver


def phase4_rbac(driver):
    log("\n=== PHASE 4: RBAC VERIFICATION ===")

    restricted = [
        ("/settings", "Settings"),
        ("/admin/super", "Super Admin"),
        ("/admin/ai-config", "AI Config"),
        ("/admin/logs", "Admin Logs"),
        ("/users", "Users"),
        ("/reports", "Reports"),
        ("/billing", "Billing"),
    ]

    for url_path, name in restricted:
        driver, ok = safe_get(driver, BASE_URL + url_path)
        if not ok:
            record(f"RBAC: {name}", "WARN", "Navigation failed")
            continue

        try:
            time.sleep(2)
            cur = driver.current_url
            page = driver.page_source.lower()

            redirected = url_path not in cur.replace(BASE_URL, "")
            denied = any(w in page for w in ["access denied", "unauthorized", "forbidden", "not authorized"])
            is_login = "/login" in cur

            ss = safe_screenshot(driver, f"30_rbac_{name.replace(' ', '_')}")

            if redirected or denied or is_login:
                record(f"RBAC: {name}", "PASS", f"Blocked -> {cur}")
            else:
                admin_kws = ["all employees", "manage users", "system settings", "billing plan",
                             "super admin", "organization settings", "ai configuration", "audit log"]
                has_admin = any(w in page for w in admin_kws)
                if has_admin:
                    record(f"RBAC: {name}", "FAIL", f"Employee can access {url_path}", ss)
                    record_bug(f"[RBAC] Employee accesses {name} ({url_path})",
                               f"Employee priya@technova.in can access {url_path}. URL: {cur}", "critical", ss)
                else:
                    record(f"RBAC: {name}", "PASS", f"Page loads but limited/empty view: {cur}")
        except:
            record(f"RBAC: {name}", "WARN", "Error testing")

    return driver


def file_github_issues():
    if not bugs:
        log("\nNo bugs to file.")
        return

    log(f"\n=== FILING {len(bugs)} GITHUB ISSUES ===")
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }

    existing = set()
    try:
        page = 1
        while True:
            r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                             headers=headers, params={"state": "all", "per_page": 100, "page": page})
            if r.status_code != 200 or not r.json():
                break
            for iss in r.json():
                existing.add(iss["title"].strip().lower())
            page += 1
    except:
        pass

    filed = skipped = 0
    for bug in bugs:
        if bug["title"].strip().lower() in existing:
            log(f"  SKIP (dup): {bug['title']}")
            skipped += 1
            continue

        labels = ["bug", f"severity:{bug['severity']}", "employee-role", "e2e-test"]
        body = f"""## Bug Report (Employee E2E)
**User:** priya@technova.in (Employee)
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Severity:** {bug['severity']}

## Description
{bug['body']}

## Screenshot
{('Saved: ' + bug['screenshot']) if bug['screenshot'] else 'N/A'}

## Steps
1. Login as employee (priya@technova.in)
2. Navigate to affected page
3. Observe issue

## Environment
- URL: {BASE_URL}
- Browser: Chrome (headless)
- Test: Automated E2E
"""
        try:
            r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                              headers=headers, json={"title": bug["title"], "body": body, "labels": labels})
            if r.status_code == 201:
                log(f"  FILED #{r.json()['number']}: {bug['title']}")
                filed += 1
            else:
                log(f"  FAIL: {bug['title']} -> {r.status_code} {r.text[:200]}")
        except Exception as ex:
            log(f"  ERROR: {bug['title']} -> {str(ex)[:100]}")
        time.sleep(1)

    log(f"\n  Filed: {filed}, Skipped: {skipped}, Total: {len(bugs)}")


def print_summary():
    log("\n" + "=" * 80)
    log("FULL EMPLOYEE DASHBOARD E2E TEST SUMMARY")
    log("=" * 80)

    passes = sum(1 for t in test_results if t["status"] == "PASS")
    fails = sum(1 for t in test_results if t["status"] == "FAIL")
    warns = sum(1 for t in test_results if t["status"] == "WARN")

    log(f"\nTotal: {len(test_results)}  PASS: {passes}  FAIL: {fails}  WARN: {warns}")
    log(f"Bugs: {len(bugs)}")

    log(f"\n--- SIDEBAR ({len(sidebar_links)} links) ---")
    for l in sidebar_links:
        log(f"  {l['text']:30s} -> {l['href']}")

    log(f"\n--- RESULTS ---")
    for t in test_results:
        icon = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN"}.get(t["status"], "?")
        log(f"  [{icon}] {t['test']}: {t['details'][:120]}")

    if bugs:
        log(f"\n--- BUGS ---")
        for b in bugs:
            log(f"  [{b['severity'].upper()}] {b['title']}")

    log(f"\nScreenshots: {SCREENSHOT_DIR}")
    log("=" * 80)


def main():
    log("Starting Full Employee Dashboard E2E Test...")
    driver = None
    try:
        # Get tokens first
        get_api_tokens()
        log(f"  API auth OK: {_user_data['first_name']} {_user_data['last_name']} ({_user_data['role']})")

        driver = get_driver_logged_in()
        safe_screenshot(driver, "01_login_success")

        driver = phase1_sidebar_mapping(driver)
        driver = phase2_test_every_page(driver)
        driver = phase3a_dashboard(driver)
        driver = phase3b_my_profile(driver)
        driver = phase3c_attendance(driver)
        driver = phase3d_leaves(driver)
        driver = phase3e_documents(driver)
        driver = phase3f_assets(driver)
        driver = phase3g_events(driver)
        driver = phase3h_wellness(driver)
        driver = phase3i_feedback(driver)
        driver = phase3j_helpdesk(driver)
        driver = phase3k_announcements(driver)
        driver = phase3l_policies(driver)
        driver = phase3m_chatbot(driver)
        driver = phase4_rbac(driver)

    except Exception as ex:
        log(f"FATAL: {str(ex)}")
        traceback.print_exc()
        if driver:
            safe_screenshot(driver, "FATAL_ERROR")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

    file_github_issues()
    print_summary()


if __name__ == "__main__":
    main()
