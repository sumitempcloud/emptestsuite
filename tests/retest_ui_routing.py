import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import urllib.request
import urllib.error
import ssl
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

# ── Config ──────────────────────────────────────────────────────────────
BASE       = "https://test-empcloud.empcloud.com"
API_BASE   = "https://test-empcloud-api.empcloud.com/api"
ORG_ADMIN  = {"email": "ananya@technova.in", "password": "Welcome@123"}
SUPER_ADMIN = {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"}
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\retest"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO  = "EmpCloud/EmpCloud"
TODAY = "2026-03-27"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── Results tracking ────────────────────────────────────────────────────
results = []  # list of dicts: {issues, title, status, detail, screenshot}


def make_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36")
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    return path


def api_login(email, password):
    """Login via API, return JWT token."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/auth/login",
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": BASE,
            "Referer": f"{BASE}/",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            body = json.loads(resp.read())
            token = body.get("token") or body.get("data", {}).get("token") or body.get("accessToken") or body.get("data", {}).get("accessToken")
            return token
    except Exception as e:
        print(f"  [API login error] {e}")
        return None


def inject_token(driver, token, email):
    """Navigate to base and inject auth token into localStorage, then reload."""
    driver.get(BASE + "/login")
    time.sleep(2)
    # Try setting various possible localStorage keys
    driver.execute_script(f"""
        localStorage.setItem('token', '{token}');
        localStorage.setItem('accessToken', '{token}');
        localStorage.setItem('auth_token', '{token}');
        localStorage.setItem('jwt', '{token}');
        localStorage.setItem('user_token', '{token}');
    """)
    driver.get(BASE + "/dashboard")
    time.sleep(3)


def selenium_login(driver, email, password):
    """Login via the UI form as fallback."""
    driver.get(BASE + "/login")
    time.sleep(3)
    screenshot(driver, "login_page")
    try:
        email_field = None
        for sel in ["input[name='email']", "input[type='email']", "#email", "input[name='username']"]:
            try:
                email_field = driver.find_element(By.CSS_SELECTOR, sel)
                break
            except NoSuchElementException:
                continue
        if not email_field:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            if inputs:
                email_field = inputs[0]
        if email_field:
            email_field.clear()
            email_field.send_keys(email)

        pw_field = None
        for sel in ["input[name='password']", "input[type='password']", "#password"]:
            try:
                pw_field = driver.find_element(By.CSS_SELECTOR, sel)
                break
            except NoSuchElementException:
                continue
        if pw_field:
            pw_field.clear()
            pw_field.send_keys(password)

        btn = None
        for sel in ["button[type='submit']", "button.login", "button"]:
            try:
                candidates = driver.find_elements(By.CSS_SELECTOR, sel)
                for c in candidates:
                    txt = c.text.lower()
                    if any(w in txt for w in ["login", "sign in", "log in", "submit"]):
                        btn = c
                        break
                if btn:
                    break
            except:
                continue
        if not btn:
            btns = driver.find_elements(By.TAG_NAME, "button")
            if btns:
                btn = btns[-1]
        if btn:
            btn.click()
        time.sleep(4)
    except Exception as e:
        print(f"  [Selenium login error] {e}")


def do_login(driver, creds):
    """Login: try API token injection first, fall back to Selenium UI login."""
    email, password = creds["email"], creds["password"]
    print(f"  Logging in as {email}...")
    token = api_login(email, password)
    if token:
        print(f"  Got API token, injecting...")
        inject_token(driver, token, email)
    else:
        print(f"  API login failed, using Selenium form...")
        selenium_login(driver, email, password)
    # Verify login
    time.sleep(2)
    url = driver.current_url
    page = driver.page_source.lower() if driver.page_source else ""
    if "/login" in url and "dashboard" not in url:
        # still on login, try selenium anyway
        print(f"  Still on login page, trying form login...")
        selenium_login(driver, email, password)
        time.sleep(3)
    screenshot(driver, f"after_login_{email.split('@')[0]}")
    print(f"  Current URL after login: {driver.current_url}")


def check_page_has_content(driver, bad_keywords=None, good_keywords=None):
    """Check if the page loaded with actual content (not blank/error)."""
    src = driver.page_source or ""
    src_lower = src.lower()
    url = driver.current_url

    issues = []
    if bad_keywords:
        for kw in bad_keywords:
            if kw.lower() in src_lower:
                issues.append(f"Found '{kw}' on page")
    if good_keywords:
        found_any = False
        for kw in good_keywords:
            if kw.lower() in src_lower:
                found_any = True
                break
        if not found_any:
            issues.append(f"None of expected keywords found: {good_keywords}")
    return issues


def wait_for_page(driver, timeout=8):
    """Wait for page to stabilize."""
    time.sleep(timeout)


def record(issues, title, status, detail, ss_path=""):
    r = {"issues": issues, "title": title, "status": status, "detail": detail, "screenshot": ss_path}
    results.append(r)
    mark = "PASS" if status == "FIXED" else "FAIL"
    print(f"  [{mark}] {title} (issues {issues}): {detail}")


# ═══════════════════════════════════════════════════════════════════════
#  TEST FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def test_employee_link_navigation(driver):
    """#129/#115/#109 - Employee link click navigates to profile"""
    print("\n=== Test: Employee link navigation (#129/#115/#109) ===")
    driver.get(BASE + "/employees")
    wait_for_page(driver, 6)
    ss = screenshot(driver, "employees_list")
    url = driver.current_url

    # Check if we're on employees page
    if "/employees" not in url:
        record([129,115,109], "Employee link navigation", "STILL FAILING",
               f"Redirected away from /employees to {url}", ss)
        return

    # Try to find and click an employee link
    clicked = False
    final_url = url
    try:
        # Look for clickable employee rows/links
        selectors = [
            "table tbody tr td a",
            "a[href*='/employees/']",
            "table tbody tr",
            "[class*='employee'] a",
            "[class*='Employee'] a",
            ".MuiTableBody-root tr",
            "tbody tr",
        ]
        for sel in selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                href = elem.get_attribute("href") or ""
                text = elem.text.strip()
                if text and len(text) > 1 and text.lower() not in ["edit", "delete", "view", "action", "actions"]:
                    try:
                        elem.click()
                        time.sleep(4)
                        final_url = driver.current_url
                        clicked = True
                        break
                    except (ElementClickInterceptedException, StaleElementReferenceException):
                        continue
            if clicked:
                break
    except Exception as e:
        print(f"  Error clicking employee: {e}")

    ss2 = screenshot(driver, "employee_profile_after_click")

    if clicked and "/employees/" in final_url and final_url != url:
        # Check it's a real profile page, not just /employees/
        parts = final_url.rstrip("/").split("/")
        if len(parts) > len(BASE.split("/")) + 1:
            record([129,115,109], "Employee link navigation", "FIXED",
                   f"Clicked employee, navigated to {final_url}", ss2)
            return

    record([129,115,109], "Employee link navigation", "STILL FAILING",
           f"Click did not navigate to profile. clicked={clicked}, url={final_url}", ss2)


def test_employee_search(driver):
    """#128/#114/#107 - Employee search filters results"""
    print("\n=== Test: Employee search (#128/#114/#107) ===")
    driver.get(BASE + "/employees")
    wait_for_page(driver, 6)

    # Count initial rows
    initial_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .MuiTableBody-root tr, [class*='list'] [class*='item'], [class*='employee-card']")
    initial_count = len(initial_rows)
    print(f"  Initial row/item count: {initial_count}")

    # Find search input
    search = None
    for sel in ["input[type='search']", "input[placeholder*='earch']", "input[placeholder*='filter']",
                "input[name='search']", "input[aria-label*='earch']", "[class*='search'] input", "input[type='text']"]:
        elems = driver.find_elements(By.CSS_SELECTOR, sel)
        for e in elems:
            if e.is_displayed():
                search = e
                break
        if search:
            break

    if not search:
        ss = screenshot(driver, "employee_search_no_input")
        record([128,114,107], "Employee search", "STILL FAILING",
               "No search input found on /employees", ss)
        return

    search.clear()
    search.send_keys("an")  # partial name likely to match some
    time.sleep(4)

    ss = screenshot(driver, "employee_search_filtered")
    after_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .MuiTableBody-root tr, [class*='list'] [class*='item'], [class*='employee-card']")
    after_count = len(after_rows)
    print(f"  After search row/item count: {after_count}")

    page_src = driver.page_source.lower()
    # If the list changed or we can see filtered results
    if after_count != initial_count and after_count > 0:
        record([128,114,107], "Employee search", "FIXED",
               f"Search filtered: {initial_count} -> {after_count} items", ss)
    elif initial_count == 0 and after_count == 0:
        record([128,114,107], "Employee search", "STILL FAILING",
               "No employee rows visible at all", ss)
    elif "no results" in page_src or "no employees" in page_src or "not found" in page_src:
        # Search returned "no results" - may mean search works but no match
        record([128,114,107], "Employee search", "FIXED",
               "Search shows 'no results' - filtering works", ss)
    else:
        record([128,114,107], "Employee search", "STILL FAILING",
               f"Search did not change results: before={initial_count}, after={after_count}", ss)


def test_add_employee_fab(driver):
    """#130/#110 - Add Employee FAB opens form"""
    print("\n=== Test: Add Employee FAB (#130/#110) ===")
    driver.get(BASE + "/employees")
    wait_for_page(driver, 6)

    btn = None
    for sel in ["button[aria-label*='add']", "button[aria-label*='Add']", "a[href*='add']",
                "a[href*='new']", "button.fab", "[class*='fab']", "[class*='Fab']",
                "button[class*='add']", "button[class*='Add']",
                "a[href='/employees/add']", "a[href='/employees/new']"]:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in elems:
                if e.is_displayed():
                    btn = e
                    break
        except:
            continue
        if btn:
            break

    # Also try finding by text
    if not btn:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button, a.btn, a[class*='button']")
        for b in buttons:
            txt = b.text.strip().lower()
            if any(w in txt for w in ["add employee", "new employee", "add", "create", "+"]):
                if b.is_displayed():
                    btn = b
                    break

    # Try FAB (floating action button usually has + icon)
    if not btn:
        fabs = driver.find_elements(By.CSS_SELECTOR, "button[class*='MuiFab'], .MuiFab-root, button svg, button[style*='position: fixed']")
        if fabs:
            btn = fabs[0]

    if not btn:
        ss = screenshot(driver, "add_employee_no_button")
        record([130,110], "Add Employee FAB", "STILL FAILING",
               "No add/FAB button found on /employees", ss)
        return

    try:
        btn.click()
        time.sleep(4)
    except Exception as e:
        ss = screenshot(driver, "add_employee_click_fail")
        record([130,110], "Add Employee FAB", "STILL FAILING",
               f"Could not click button: {e}", ss)
        return

    ss = screenshot(driver, "add_employee_after_click")
    url = driver.current_url
    page = driver.page_source.lower()

    # Check if form/dialog opened
    form_indicators = ["add employee", "new employee", "create employee", "first name", "last name",
                       "employee form", "personal details", "email", "department"]
    dialog = driver.find_elements(By.CSS_SELECTOR, "[role='dialog'], .MuiDialog-root, .modal, [class*='modal'], [class*='dialog'], form")

    found_form = any(kw in page for kw in form_indicators)
    found_dialog = len(dialog) > 0
    navigated = "/add" in url or "/new" in url or "/create" in url

    if found_form or found_dialog or navigated:
        record([130,110], "Add Employee FAB", "FIXED",
               f"Form opened. url={url}, dialog={found_dialog}, form_words={found_form}", ss)
    else:
        record([130,110], "Add Employee FAB", "STILL FAILING",
               f"No form after click. url={url}", ss)


def test_super_admin_dashboard(driver):
    """#116/#112/#93 - Super Admin Dashboard renders"""
    print("\n=== Test: Super Admin Dashboard (#116/#112/#93) ===")
    do_login(driver, SUPER_ADMIN)
    driver.get(BASE + "/admin/super")
    wait_for_page(driver, 8)
    ss = screenshot(driver, "super_admin_dashboard")
    url = driver.current_url
    page = driver.page_source or ""
    page_lower = page.lower()

    # Check for blank page
    body_text = ""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
    except:
        pass

    is_blank = len(body_text) < 50
    has_content_keywords = any(kw in page_lower for kw in ["organization", "tenant", "admin", "dashboard", "manage", "users", "super"])
    redirected = "/admin/super" not in url

    if redirected:
        record([116,112,93], "Super Admin Dashboard", "STILL FAILING",
               f"Redirected to {url}", ss)
    elif is_blank and not has_content_keywords:
        record([116,112,93], "Super Admin Dashboard", "STILL FAILING",
               f"Page appears blank. Body text length: {len(body_text)}", ss)
    else:
        record([116,112,93], "Super Admin Dashboard", "FIXED",
               f"Page rendered with content. Body length: {len(body_text)}", ss)


def test_route(driver, path, issue_nums, title, alt_paths=None, good_kw=None):
    """Generic route test: go to path, check not redirected/blank/404/error."""
    print(f"\n=== Test: {title} ({issue_nums}) ===")
    paths_to_try = [path] + (alt_paths or [])
    best_url = ""
    best_ss = ""
    best_status = "STILL FAILING"
    best_detail = ""

    for p in paths_to_try:
        full = BASE + p
        driver.get(full)
        wait_for_page(driver, 6)
        url = driver.current_url
        page_lower = (driver.page_source or "").lower()
        body_text = ""
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
        except:
            pass

        ss = screenshot(driver, f"route_{p.replace('/', '_').strip('_')}")

        # Determine outcome
        on_dashboard = url.rstrip("/").endswith("/dashboard") or url.rstrip("/") == BASE
        on_login = "/login" in url
        is_404 = "404" in page_lower or "not found" in page_lower
        is_403 = "403" in page_lower or "forbidden" in page_lower
        is_blank = len(body_text) < 30
        has_error = "invalid" in page_lower and "parameter" in page_lower
        stayed = p in url.replace(BASE, "")

        if good_kw:
            has_good = any(kw.lower() in page_lower for kw in good_kw)
        else:
            has_good = not is_blank

        if stayed and not is_404 and not is_403 and not has_error and has_good and not is_blank:
            record(issue_nums, title, "FIXED",
                   f"Route {p} loaded OK. URL={url}", ss)
            return
        else:
            problems = []
            if not stayed and on_dashboard:
                problems.append("redirected to dashboard")
            if not stayed and on_login:
                problems.append("redirected to login")
            if is_404:
                problems.append("404 Not Found")
            if is_403:
                problems.append("403 Forbidden")
            if has_error:
                problems.append("Invalid parameter error")
            if is_blank:
                problems.append("page blank")
            best_detail = f"Route {p}: {', '.join(problems) if problems else 'issue detected'}. URL={url}"
            best_ss = ss

    record(issue_nums, title, "STILL FAILING", best_detail, best_ss)


def test_pending_leave_names(driver):
    """#94 - Pending Leave Requests show names not user IDs"""
    print("\n=== Test: Pending Leave names (#94) ===")
    driver.get(BASE + "/leave")
    wait_for_page(driver, 6)
    ss = screenshot(driver, "leave_pending")
    page = driver.page_source or ""
    body = ""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
    except:
        pass

    if "User #" in body or "user #" in body or "User#" in body:
        record([94], "Pending Leave shows user IDs", "STILL FAILING",
               "Found 'User #' pattern - IDs shown instead of names", ss)
    elif "/login" in driver.current_url:
        record([94], "Pending Leave shows user IDs", "STILL FAILING",
               "Redirected to login", ss)
    else:
        record([94], "Pending Leave shows user IDs", "FIXED",
               "No 'User #' pattern found", ss)


def test_documents_warning(driver):
    """#95 - Documents shows 49 missing mandatory docs warning"""
    print("\n=== Test: Documents mandatory warning (#95) ===")
    for p in ["/documents", "/my-documents", "/documents/my"]:
        driver.get(BASE + p)
        wait_for_page(driver, 5)

    ss = screenshot(driver, "documents_warning")
    page = driver.page_source or ""
    body = ""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
    except:
        pass

    if "49" in body and "missing" in body.lower():
        record([95], "Documents 49 missing mandatory", "STILL FAILING",
               "Still shows 49 missing mandatory documents", ss)
    elif "missing mandatory" in body.lower() and any(str(n) in body for n in range(10, 100)):
        record([95], "Documents missing mandatory", "STILL FAILING",
               "Still shows missing mandatory documents warning", ss)
    elif "404" in page.lower() or "not found" in page.lower():
        record([95], "Documents 49 missing mandatory", "STILL FAILING",
               "Documents page returns 404", ss)
    else:
        record([95], "Documents 49 missing mandatory", "FIXED",
               "No excessive missing mandatory documents warning", ss)


def test_i18n_keys(driver):
    """#126/#104 - Raw i18n key 'nav.myProfile' in sidebar"""
    print("\n=== Test: i18n keys in sidebar (#126/#104) ===")
    driver.get(BASE + "/dashboard")
    wait_for_page(driver, 5)
    ss = screenshot(driver, "sidebar_i18n")
    page = driver.page_source or ""
    body = ""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
    except:
        pass

    raw_keys = ["nav.myProfile", "nav.dashboard", "nav.leave", "nav.attendance",
                "nav.employees", "nav.settings", "nav.", "sidebar."]
    found = [k for k in raw_keys if k in body or k in page]

    if found:
        record([126,104], "Raw i18n keys in sidebar", "STILL FAILING",
               f"Found raw translation keys: {found}", ss)
    else:
        record([126,104], "Raw i18n keys in sidebar", "FIXED",
               "No raw i18n keys detected in sidebar", ss)


def test_chatbot(driver):
    """#96 - AI Chatbot has no input field"""
    print("\n=== Test: AI Chatbot input (#96) ===")
    driver.get(BASE + "/dashboard")
    wait_for_page(driver, 5)

    # Find chatbot bubble/icon
    chat_btn = None
    for sel in ["[class*='chat']", "[class*='Chat']", "[aria-label*='chat']",
                "[id*='chat']", "button[class*='bot']", "[class*='chatbot']",
                "[class*='widget']", "iframe[src*='chat']"]:
        elems = driver.find_elements(By.CSS_SELECTOR, sel)
        for e in elems:
            if e.is_displayed():
                chat_btn = e
                break
        if chat_btn:
            break

    if not chat_btn:
        # Look for floating buttons at bottom-right
        buttons = driver.find_elements(By.CSS_SELECTOR, "button, div[role='button']")
        for b in buttons:
            try:
                loc = b.location
                size = b.size
                if loc['x'] > 1600 and loc['y'] > 800:
                    chat_btn = b
                    break
            except:
                continue

    ss1 = screenshot(driver, "chatbot_before_click")

    if not chat_btn:
        record([96], "AI Chatbot input field", "STILL FAILING",
               "No chatbot button/bubble found", ss1)
        return

    try:
        chat_btn.click()
        time.sleep(3)
    except:
        try:
            driver.execute_script("arguments[0].click();", chat_btn)
            time.sleep(3)
        except Exception as e:
            record([96], "AI Chatbot input field", "STILL FAILING",
                   f"Could not click chatbot: {e}", ss1)
            return

    ss2 = screenshot(driver, "chatbot_after_click")

    # Look for input in chat
    chat_input = None
    for sel in ["[class*='chat'] input", "[class*='chat'] textarea", "[class*='Chat'] input",
                "[class*='Chat'] textarea", "input[placeholder*='type']", "input[placeholder*='message']",
                "textarea[placeholder*='type']", "textarea[placeholder*='message']",
                "[class*='chatbot'] input", "[class*='chatbot'] textarea"]:
        elems = driver.find_elements(By.CSS_SELECTOR, sel)
        for e in elems:
            if e.is_displayed():
                chat_input = e
                break
        if chat_input:
            break

    # Also check iframes
    if not chat_input:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                for sel in ["input", "textarea"]:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                    if elems:
                        chat_input = elems[0]
                        break
                driver.switch_to.default_content()
                if chat_input:
                    break
            except:
                driver.switch_to.default_content()

    if chat_input:
        record([96], "AI Chatbot input field", "FIXED",
               "Chatbot has input field", ss2)
    else:
        record([96], "AI Chatbot input field", "STILL FAILING",
               "Chatbot opened but no input field found", ss2)


# ═══════════════════════════════════════════════════════════════════════
#  GITHUB API
# ═══════════════════════════════════════════════════════════════════════

def github_api(method, endpoint, data=None):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = f"https://api.github.com{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-RetestBot",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        print(f"  [GitHub API {e.code}] {endpoint}: {err_body[:200]}")
        return None
    except Exception as e:
        print(f"  [GitHub API error] {endpoint}: {e}")
        return None


def reopen_issue(issue_num, detail):
    print(f"  Re-opening issue #{issue_num}...")
    github_api("PATCH", f"/repos/{GITHUB_REPO}/issues/{issue_num}",
               {"state": "open"})
    comment = f"Re-tested on {TODAY}. Bug is still present. {detail}"
    github_api("POST", f"/repos/{GITHUB_REPO}/issues/{issue_num}/comments",
               {"body": comment})


def comment_fixed(issue_num):
    print(f"  Commenting fixed on #{issue_num}...")
    github_api("POST", f"/repos/{GITHUB_REPO}/issues/{issue_num}/comments",
               {"body": f"Re-tested on {TODAY}. Verified this bug is now fixed."})


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("EmpCloud Closed Issue Re-Test")
    print("=" * 70)

    driver = make_driver()
    try:
        # ── ORG ADMIN tests ──────────────────────────────────────────
        print("\n>>> Logging in as Org Admin <<<")
        do_login(driver, ORG_ADMIN)

        test_employee_link_navigation(driver)
        test_employee_search(driver)
        test_add_employee_fab(driver)

        # #121 - /reports
        test_route(driver, "/reports", [121], "Reports route",
                   good_kw=["report", "analytics", "generate"])

        # #117,119,120 - Settings routes
        test_route(driver, "/settings/organization", [117], "Settings Organization route",
                   good_kw=["organization", "company", "settings"])
        test_route(driver, "/settings/modules", [119], "Settings Modules route",
                   good_kw=["module", "settings", "enable"])
        test_route(driver, "/settings/custom-fields", [120], "Settings Custom Fields route",
                   good_kw=["custom", "field", "settings"])

        # #84 - /leave/types
        test_route(driver, "/leave/types", [84], "Leave Types route",
                   good_kw=["leave type", "casual", "sick", "earned", "type"])

        # #92 - Comp-Off routes
        test_route(driver, "/leave/comp-off", [92], "Comp-Off route",
                   alt_paths=["/comp-off"],
                   good_kw=["comp-off", "compensatory", "comp off"])

        # #91 - Shifts
        test_route(driver, "/shifts", [91], "Shifts page",
                   alt_paths=["/attendance/shifts"],
                   good_kw=["shift", "schedule", "timing"])

        # #131/#111/#90 - Attendance regularization
        test_route(driver, "/attendance/regularizations", [131,111,90],
                   "Attendance Regularization",
                   alt_paths=["/regularizations", "/attendance/regularization"],
                   good_kw=["regulariz", "attendance", "request"])

        # #105 - Wellness daily check-in
        test_route(driver, "/wellness/daily-checkin", [105], "Wellness Daily Check-in",
                   alt_paths=["/wellness/check-in", "/wellness/daily-check-in"],
                   good_kw=["wellness", "check-in", "checkin", "daily", "mood"])

        # #99, #101, #102 - "Invalid ID parameter" routes
        test_route(driver, "/events/my-events", [99], "My Events route",
                   good_kw=["event", "calendar", "upcoming"])
        test_route(driver, "/assets/my-assets", [101], "My Assets route",
                   good_kw=["asset", "device", "assigned"])
        test_route(driver, "/positions/open", [102], "Open Positions route",
                   good_kw=["position", "opening", "job", "apply"])

        # #100 - /assets 403
        test_route(driver, "/assets", [100], "Assets page (403 check)",
                   good_kw=["asset", "device", "inventory"])

        # #94 - Pending leave names
        test_pending_leave_names(driver)

        # #95 - Documents warning
        test_documents_warning(driver)

        # #126/#104 - i18n keys
        test_i18n_keys(driver)

        # #96 - Chatbot
        test_chatbot(driver)

        # #89 - Attendance page 404
        test_route(driver, "/attendance", [89], "Attendance page",
                   alt_paths=["/attendance/dashboard"],
                   good_kw=["attendance", "check-in", "present", "absent", "clock"])

        # #83 - Leave calendar 404
        test_route(driver, "/leave/calendar", [83], "Leave Calendar",
                   alt_paths=["/leave-calendar"],
                   good_kw=["calendar", "leave", "month", "week"])

        # #86/#87 - Documents 404
        test_route(driver, "/documents", [86,87], "Documents / My Documents",
                   alt_paths=["/my-documents", "/documents/my"],
                   good_kw=["document", "upload", "file"])

        # ── SUPER ADMIN tests ────────────────────────────────────────
        print("\n>>> Testing Super Admin Dashboard <<<")
        # Create fresh driver for super admin
        driver.delete_all_cookies()
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        test_super_admin_dashboard(driver)

    finally:
        driver.quit()

    # ── Summary & GitHub actions ─────────────────────────────────────
    print("\n" + "=" * 70)
    print("RE-TEST RESULTS SUMMARY")
    print("=" * 70)

    fixed_count = 0
    failing_count = 0

    for r in results:
        issues_str = ", ".join(f"#{i}" for i in r["issues"])
        mark = "FIXED" if r["status"] == "FIXED" else "STILL FAILING"
        print(f"  [{mark}] {issues_str} - {r['title']}: {r['detail'][:100]}")

        if r["status"] == "FIXED":
            fixed_count += 1
            for inum in r["issues"]:
                comment_fixed(inum)
        else:
            failing_count += 1
            for inum in r["issues"]:
                reopen_issue(inum, r["detail"][:200])

    print(f"\nTotal: {len(results)} tests | FIXED: {fixed_count} | STILL FAILING: {failing_count}")
    print("=" * 70)


if __name__ == "__main__":
    main()
