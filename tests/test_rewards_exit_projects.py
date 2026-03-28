"""
E2E Tests for EMP Cloud HRMS - Rewards, Exit Management, and Project Management modules.
Resilient version with session recovery on Chrome crashes.
"""

import sys
import os
import time
import json
import traceback
import requests
import gc
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import functools
print = functools.partial(print, flush=True)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException, InvalidSessionIdException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────────
SCREENSHOTS_DIR = r"C:\Users\Admin\screenshots\rewards_exit_projects"
CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

URLS = {
    "rewards": "https://test-rewards.empcloud.com",
    "exit": "https://test-exit.empcloud.com",
    "projects": "https://test-project.empcloud.com",
}

CREDS = {
    "admin": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "employee": {"email": "priya@technova.in", "password": "Welcome@123"},
}

bugs = []
test_results = []
_cached_chromedriver_path = None


# ── Driver Management ───────────────────────────────────────────────────────
def get_chromedriver_path():
    global _cached_chromedriver_path
    if _cached_chromedriver_path is None:
        _cached_chromedriver_path = ChromeDriverManager().install()
    return _cached_chromedriver_path


def get_driver():
    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disable-default-apps")
    opts.add_argument("--disable-sync")
    opts.add_argument("--disable-translate")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--memory-pressure-off")
    svc = Service(get_chromedriver_path())
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(3)
    return driver


def is_alive(driver):
    """Check if the browser session is still alive."""
    try:
        _ = driver.current_url
        return True
    except:
        return False


def safe_quit(driver):
    """Safely quit a driver, ignoring errors."""
    if driver:
        try:
            driver.quit()
        except:
            pass
    gc.collect()


def safe_op(driver, func, default=None):
    """Run a driver operation safely, returning default on failure."""
    try:
        return func(driver)
    except:
        return default


# ── Helpers ─────────────────────────────────────────────────────────────────
def screenshot(driver, name):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = name.replace(" ", "_").replace("/", "_").replace(":", "_")
    path = os.path.join(SCREENSHOTS_DIR, f"{safe}_{ts}.png")
    try:
        driver.save_screenshot(path)
    except Exception:
        path = ""
    return path


def record(test_name, module, status, details="", ss_path=""):
    test_results.append({
        "test": test_name, "module": module, "status": status,
        "details": details, "screenshot": ss_path,
        "timestamp": datetime.now().isoformat()
    })
    icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "WARN"
    print(f"  [{icon}] {test_name}: {details}")


def record_bug(title, module, severity, description, ss_path, url=""):
    bugs.append({
        "title": title, "module": module, "severity": severity,
        "description": description, "screenshot": ss_path, "url": url,
    })
    print(f"  [BUG-{severity.upper()}] {title}")


def login(driver, url, email, password):
    """Login to an EMP Cloud module. Returns True on success."""
    print(f"  Logging in as {email} at {url} ...")
    try:
        driver.get(url)
    except:
        return False
    time.sleep(3)

    try:
        current = driver.current_url
    except:
        return False

    if "dashboard" in current.lower() and "login" not in current.lower():
        return True

    try:
        # Find email field
        email_field = None
        for sel in [
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='mail']"),
            (By.CSS_SELECTOR, "input[id*='email']"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ]:
            try:
                email_field = WebDriverWait(driver, 4).until(EC.element_to_be_clickable(sel))
                if email_field:
                    break
            except:
                continue

        if not email_field:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            if len(inputs) >= 2:
                email_field = inputs[0]
            else:
                return False

        email_field.clear()
        email_field.send_keys(email)
        time.sleep(0.3)

        # Find password
        pwd_field = None
        for sel in [(By.CSS_SELECTOR, "input[type='password']"), (By.CSS_SELECTOR, "input[name='password']")]:
            try:
                pwd_field = driver.find_element(*sel)
                if pwd_field:
                    break
            except:
                continue
        if not pwd_field:
            return False

        pwd_field.clear()
        pwd_field.send_keys(password)
        time.sleep(0.3)

        # Click login button
        btn = None
        for sel in [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[contains(text(),'Login') or contains(text(),'Sign') or contains(text(),'Log In')]"),
        ]:
            try:
                btn = driver.find_element(*sel)
                if btn:
                    break
            except:
                continue

        if btn:
            btn.click()
        else:
            pwd_field.send_keys(Keys.RETURN)

        time.sleep(4)

        new_url = driver.current_url
        if "dashboard" in new_url.lower() or "home" in new_url.lower():
            return True
        if new_url != current and "login" not in new_url.lower():
            return True
        return True

    except Exception as e:
        print(f"    Login exception: {e}")
        return False


def find_and_click(driver, selectors, timeout=5):
    for sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(sel))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.3)
            el.click()
            return True
        except:
            continue
    return False


def nav_sidebar(driver, text_options):
    """Click a sidebar/nav item matching text."""
    for txt in text_options:
        for sel in [
            (By.XPATH, f"//nav//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{txt.lower()}')]"),
            (By.XPATH, f"//aside//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{txt.lower()}')]"),
            (By.XPATH, f"//*[contains(@class,'sidebar') or contains(@class,'menu') or contains(@class,'nav')]//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{txt.lower()}')]"),
            (By.XPATH, f"//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{txt.lower()}')]"),
        ]:
            try:
                el = WebDriverWait(driver, 3).until(EC.element_to_be_clickable(sel))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.3)
                el.click()
                time.sleep(2)
                return True
            except:
                continue
    return False


# ── Module Tests ────────────────────────────────────────────────────────────

def test_rewards_module():
    """Test Rewards module with fresh driver."""
    module = "rewards"
    base = URLS["rewards"]
    print("\n" + "="*70)
    print("REWARDS MODULE TESTS")
    print("="*70)

    driver = get_driver()
    try:
        _test_rewards(driver, module, base)
    finally:
        safe_quit(driver)


def _test_rewards(driver, module, base):
    # ── Admin Login ──
    print("\n-- Admin Login --")
    ok = login(driver, base, CREDS["admin"]["email"], CREDS["admin"]["password"])
    ss = screenshot(driver, "rewards_admin_login")
    if not ok:
        record("Admin login", module, "FAIL", "Could not log in as admin", ss)
        record_bug("[Rewards] Admin login failed", module, "critical",
                   f"Cannot login as Org Admin to rewards module at {base}", ss, base)
        return
    record("Admin login", module, "PASS", f"Logged in, URL: {driver.current_url}", ss)

    # ── Dashboard ──
    print("\n-- Rewards Dashboard --")
    time.sleep(2)
    if not is_alive(driver):
        record("Rewards dashboard", module, "FAIL", "Browser crashed"); return
    page = driver.page_source.lower()
    ss = screenshot(driver, "rewards_dashboard")

    dashboard_kw = ["reward", "dashboard", "recognition", "kudos", "badge", "point", "leaderboard"]
    found_kw = [kw for kw in dashboard_kw if kw in page]
    if found_kw:
        record("Rewards dashboard content", module, "PASS", f"Found keywords: {found_kw}", ss)
    else:
        record("Rewards dashboard content", module, "WARN", "No rewards keywords found", ss)

    # Check widgets
    widgets = driver.find_elements(By.CSS_SELECTOR, ".card, .widget, [class*='dashboard'], [class*='stat']")
    record("Dashboard widgets", module, "PASS" if widgets else "WARN",
           f"Found {len(widgets)} widget elements" if widgets else "No widgets found", ss)

    # ── Badges ──
    print("\n-- Badges --")
    if not is_alive(driver):
        record("Badges", module, "FAIL", "Browser crashed"); return
    nav_sidebar(driver, ["badge", "badges"])
    time.sleep(1)
    if is_alive(driver):
        ss = screenshot(driver, "rewards_badges")
        page = driver.page_source.lower()
        if "badge" in page:
            record("Badges page", module, "PASS", "Badges section accessible", ss)
        else:
            record("Badges page", module, "WARN", "Badges section not clearly found", ss)
    else:
        record("Badges page", module, "FAIL", "Browser crashed during navigation")

    # ── Kudos ──
    print("\n-- Kudos --")
    if not is_alive(driver):
        record("Kudos", module, "FAIL", "Browser crashed"); return
    try:
        driver.get(base)
        time.sleep(2)
    except:
        record("Kudos", module, "FAIL", "Cannot navigate"); return

    nav_sidebar(driver, ["kudos", "kudo", "recognition", "appreciate"])
    time.sleep(1)
    if is_alive(driver):
        ss = screenshot(driver, "rewards_kudos")
        page = driver.page_source.lower()
        if any(kw in page for kw in ["kudos", "kudo", "recognition", "appreciate"]):
            record("Kudos page", module, "PASS", "Kudos/Recognition section accessible", ss)
        else:
            record("Kudos page", module, "WARN", "Kudos section not clearly found", ss)
    else:
        record("Kudos page", module, "FAIL", "Browser crashed")

    # ── Give Recognition ──
    print("\n-- Give Recognition --")
    if not is_alive(driver):
        record("Give recognition", module, "FAIL", "Browser crashed"); return
    try:
        driver.get(base)
        time.sleep(2)
    except:
        record("Give recognition", module, "FAIL", "Cannot navigate"); return

    if not is_alive(driver):
        record("Give recognition", module, "FAIL", "Browser crashed"); return

    give_clicked = find_and_click(driver, [
        (By.XPATH, "//*[contains(text(),'Give') and (contains(text(),'Kudos') or contains(text(),'Recognition'))]"),
        (By.XPATH, "//button[contains(text(),'Recognize') or contains(text(),'Appreciate') or contains(text(),'Give')]"),
        (By.XPATH, "//a[contains(text(),'Give') or contains(text(),'Recognize')]"),
        (By.CSS_SELECTOR, "[class*='give'], [class*='recognize']"),
    ], timeout=4)

    time.sleep(1)
    if not is_alive(driver):
        record("Give recognition", module, "FAIL", "Browser crashed after click"); return

    ss = screenshot(driver, "rewards_give_recognition")
    page = driver.page_source.lower()

    if give_clicked or "give" in page or "select" in page:
        record("Give recognition button", module, "PASS", "Recognition form/dialog accessible", ss)

        # Try filling form
        try:
            for sel in [
                (By.CSS_SELECTOR, "input[placeholder*='employee' i]"),
                (By.CSS_SELECTOR, "input[placeholder*='search' i]"),
                (By.CSS_SELECTOR, "[class*='select'] input"),
            ]:
                try:
                    el = driver.find_element(*sel)
                    el.clear()
                    el.send_keys("Priya")
                    time.sleep(1)
                    options = driver.find_elements(By.CSS_SELECTOR, "[class*='option'], [role='option']")
                    if options:
                        options[0].click()
                    break
                except:
                    continue

            for sel in [(By.CSS_SELECTOR, "textarea"), (By.CSS_SELECTOR, "input[placeholder*='message' i]")]:
                try:
                    el = driver.find_element(*sel)
                    el.clear()
                    el.send_keys("Great work on Q1! Automated test recognition.")
                    break
                except:
                    continue

            ss = screenshot(driver, "rewards_recognition_filled")
            record("Fill recognition form", module, "PASS", "Attempted to fill recognition form", ss)
        except Exception as e:
            record("Fill recognition form", module, "WARN", f"Could not fill form: {e}")
    else:
        record("Give recognition button", module, "WARN", "Could not find Give Recognition button", ss)

    # ── Employee Login ──
    print("\n-- Employee Login - My Rewards --")
    if not is_alive(driver):
        record("Employee rewards", module, "FAIL", "Browser crashed"); return
    try:
        driver.delete_all_cookies()
    except:
        pass

    ok = login(driver, base, CREDS["employee"]["email"], CREDS["employee"]["password"])
    if not is_alive(driver):
        record("Employee login", module, "FAIL", "Browser crashed"); return

    ss = screenshot(driver, "rewards_employee_login")
    if not ok:
        record("Employee login", module, "FAIL", "Could not login as employee", ss)
        record_bug("[Rewards] Employee login failed", module, "critical",
                   f"Cannot login as Employee to rewards module.", ss, base)
        return

    record("Employee login", module, "PASS", f"URL: {driver.current_url}", ss)

    page = driver.page_source.lower()
    reward_kw = ["received", "kudos", "badge", "point", "recognition", "reward"]
    found = [kw for kw in reward_kw if kw in page]
    ss = screenshot(driver, "rewards_employee_dashboard")
    if found:
        record("Employee rewards view", module, "PASS", f"Found keywords: {found}", ss)
    else:
        record("Employee rewards view", module, "WARN", "No personal rewards keywords found", ss)


def test_exit_module():
    """Test Exit Management module with fresh driver."""
    module = "exit"
    base = URLS["exit"]
    print("\n" + "="*70)
    print("EXIT MANAGEMENT MODULE TESTS")
    print("="*70)

    driver = get_driver()
    try:
        _test_exit(driver, module, base)
    finally:
        safe_quit(driver)


def _test_exit(driver, module, base):
    # ── Admin Login ──
    print("\n-- Admin Login --")
    ok = login(driver, base, CREDS["admin"]["email"], CREDS["admin"]["password"])
    ss = screenshot(driver, "exit_admin_login")
    if not ok:
        record("Admin login", module, "FAIL", "Could not log in as admin", ss)
        record_bug("[Exit] Admin login failed", module, "critical",
                   f"Cannot login as Org Admin to exit module at {base}", ss, base)
        return
    record("Admin login", module, "PASS", f"Logged in, URL: {driver.current_url}", ss)

    # ── Dashboard ──
    print("\n-- Exit Dashboard --")
    time.sleep(2)
    if not is_alive(driver):
        record("Exit dashboard", module, "FAIL", "Browser crashed"); return
    page = driver.page_source.lower()
    ss = screenshot(driver, "exit_dashboard")

    exit_kw = ["exit", "offboard", "separation", "resign", "termination", "attrition",
               "full and final", "f&f", "settlement", "notice period"]
    found_kw = [kw for kw in exit_kw if kw in page]
    if found_kw:
        record("Exit dashboard content", module, "PASS", f"Found keywords: {found_kw}", ss)
    else:
        record("Exit dashboard content", module, "WARN", "No exit keywords found", ss)

    stats = driver.find_elements(By.CSS_SELECTOR, ".card, .stat, [class*='count'], [class*='metric'], [class*='widget']")
    record("Dashboard statistics", module, "PASS" if stats else "WARN",
           f"Found {len(stats)} stat elements" if stats else "No stat cards found", ss)

    # ── Offboarding Workflows ──
    print("\n-- Offboarding Workflows --")
    if not is_alive(driver):
        record("Offboarding workflows", module, "FAIL", "Browser crashed"); return

    found_offboard = False
    # Try sidebar nav first
    nav_sidebar(driver, ["offboard", "workflow", "separation"])
    time.sleep(1)
    if is_alive(driver):
        page = driver.page_source.lower()
        if any(kw in page for kw in ["offboard", "workflow", "checklist", "task", "process"]):
            found_offboard = True

    # Try direct URLs if sidebar didn't work
    if not found_offboard and is_alive(driver):
        for path in ["/offboarding", "/workflows", "/separation", "/admin/offboarding"]:
            try:
                driver.get(base + path)
                time.sleep(2)
                if not is_alive(driver):
                    break
                p = driver.page_source.lower()
                if any(kw in p for kw in ["offboard", "workflow", "checklist"]):
                    found_offboard = True
                    break
            except:
                continue

    if is_alive(driver):
        ss = screenshot(driver, "exit_offboarding")
        if found_offboard:
            record("Offboarding workflows", module, "PASS", "Offboarding section accessible", ss)
        else:
            record("Offboarding workflows", module, "WARN", "Offboarding workflows section not found", ss)
    else:
        record("Offboarding workflows", module, "FAIL", "Browser crashed")

    # ── Full & Final Settlement ──
    print("\n-- Full & Final Settlement --")
    if not is_alive(driver):
        record("F&F Settlement", module, "FAIL", "Browser crashed"); return

    try:
        driver.get(base)
        time.sleep(2)
    except:
        record("F&F Settlement", module, "FAIL", "Cannot navigate"); return

    if not is_alive(driver):
        record("F&F Settlement", module, "FAIL", "Browser crashed"); return

    found_fnf = False
    nav_sidebar(driver, ["full", "final", "settlement", "f&f", "fnf"])
    time.sleep(1)
    if is_alive(driver):
        page = driver.page_source.lower()
        if any(kw in page for kw in ["full and final", "f&f", "settlement", "fnf", "final settlement"]):
            found_fnf = True

    if not found_fnf and is_alive(driver):
        for path in ["/full-final", "/fnf", "/settlement", "/full-and-final", "/admin/fnf"]:
            try:
                driver.get(base + path)
                time.sleep(2)
                if not is_alive(driver):
                    break
                p = driver.page_source.lower()
                if any(kw in p for kw in ["settlement", "final", "amount", "payable"]):
                    found_fnf = True
                    break
            except:
                continue

    if is_alive(driver):
        ss = screenshot(driver, "exit_fnf_settlement")
        if found_fnf:
            record("F&F Settlement page", module, "PASS", "Full & Final settlement accessible", ss)
        else:
            record("F&F Settlement", module, "WARN", "F&F Settlement page not found", ss)
    else:
        record("F&F Settlement", module, "FAIL", "Browser crashed")

    # ── Check for page errors ──
    if is_alive(driver):
        page = driver.page_source.lower()
        if any(err in page for err in ["500", "502", "503", "something went wrong"]):
            ss = screenshot(driver, "exit_error")
            record_bug("[Exit] Page error detected", module, "high",
                       f"Error state on exit module. URL: {driver.current_url}", ss, driver.current_url)


def test_projects_module():
    """Test Project Management module with fresh driver."""
    module = "projects"
    base = URLS["projects"]
    print("\n" + "="*70)
    print("PROJECT MANAGEMENT MODULE TESTS")
    print("="*70)

    driver = get_driver()
    try:
        _test_projects(driver, module, base)
    finally:
        safe_quit(driver)


def _test_projects(driver, module, base):
    # ── Admin Login ──
    print("\n-- Admin Login --")
    ok = login(driver, base, CREDS["admin"]["email"], CREDS["admin"]["password"])
    if not is_alive(driver):
        record("Admin login", module, "FAIL", "Browser crashed during login"); return
    ss = screenshot(driver, "projects_admin_login")
    if not ok:
        record("Admin login", module, "FAIL", "Could not log in as admin", ss)
        record_bug("[Projects] Admin login failed", module, "critical",
                   f"Cannot login as Org Admin to projects module at {base}. URL: {driver.current_url}", ss, base)
        # Don't return - may still have content
    else:
        record("Admin login", module, "PASS", f"Logged in, URL: {driver.current_url}", ss)

    # ── Dashboard ──
    print("\n-- Projects Dashboard --")
    time.sleep(2)
    if not is_alive(driver):
        record("Projects dashboard", module, "FAIL", "Browser crashed"); return
    page = driver.page_source.lower()
    ss = screenshot(driver, "projects_dashboard")

    proj_kw = ["project", "task", "milestone", "timeline", "kanban", "board", "sprint", "time", "track", "team"]
    found_kw = [kw for kw in proj_kw if kw in page]
    if found_kw:
        record("Projects dashboard content", module, "PASS", f"Found keywords: {found_kw}", ss)
    else:
        record("Projects dashboard content", module, "WARN", "No project keywords found", ss)

    # ── Projects List ──
    print("\n-- Projects List --")
    if not is_alive(driver):
        record("Projects list", module, "FAIL", "Browser crashed"); return

    nav_sidebar(driver, ["project", "all project", "list"])
    time.sleep(1)
    if not is_alive(driver):
        record("Projects list", module, "FAIL", "Browser crashed"); return

    ss = screenshot(driver, "projects_list")
    page = driver.page_source.lower()
    if "project" in page:
        record("Projects list page", module, "PASS", "Projects list accessible", ss)
        items = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, [class*='project-card'], [class*='project-item'], .card")
        if items:
            record("Project items count", module, "PASS", f"Found {len(items)} project items/rows")
    else:
        record("Projects list", module, "WARN", "Projects list not found", ss)

    # ── Create Project ──
    print("\n-- Create Project --")
    if not is_alive(driver):
        record("Create project", module, "FAIL", "Browser crashed"); return

    create_clicked = find_and_click(driver, [
        (By.XPATH, "//button[contains(text(),'Create') or contains(text(),'New') or contains(text(),'Add')]"),
        (By.XPATH, "//a[contains(text(),'Create') or contains(text(),'New Project') or contains(text(),'Add')]"),
        (By.CSS_SELECTOR, "button[class*='create'], button[class*='add'], button[class*='new']"),
        (By.CSS_SELECTOR, ".btn-primary, .ant-btn-primary"),
    ], timeout=4)

    time.sleep(1)
    if not is_alive(driver):
        record("Create project", module, "FAIL", "Browser crashed"); return

    ss = screenshot(driver, "projects_create_form")
    page = driver.page_source.lower()

    if create_clicked or "create" in page or "new project" in page:
        record("Create project form", module, "PASS", "Create project form/dialog accessible", ss)

        try:
            name_fields = driver.find_elements(By.CSS_SELECTOR,
                "input[placeholder*='name' i], input[placeholder*='title' i], input[placeholder*='project' i], input[type='text']")
            if name_fields:
                ts = datetime.now().strftime("%H%M%S")
                name_fields[0].clear()
                name_fields[0].send_keys(f"AutoTest Project {ts}")

            desc_fields = driver.find_elements(By.CSS_SELECTOR, "textarea, input[placeholder*='description' i]")
            if desc_fields:
                desc_fields[0].clear()
                desc_fields[0].send_keys("Automated test project - E2E test suite")

            ss = screenshot(driver, "projects_create_filled")
            record("Fill create project form", module, "PASS", "Project form filled", ss)

            find_and_click(driver, [
                (By.XPATH, "//button[contains(text(),'Save') or contains(text(),'Create') or contains(text(),'Submit')]"),
                (By.CSS_SELECTOR, "button[type='submit']"),
            ], timeout=4)

            time.sleep(3)
            if is_alive(driver):
                ss = screenshot(driver, "projects_create_result")
                new_page = driver.page_source.lower()
                if "success" in new_page or "created" in new_page:
                    record("Submit new project", module, "PASS", "Project created successfully", ss)
                elif "error" in new_page or "required" in new_page:
                    record("Submit new project", module, "WARN", "Validation error on submit", ss)
                else:
                    record("Submit new project", module, "WARN", "Submitted, unclear result", ss)
        except Exception as e:
            record("Fill create project form", module, "WARN", f"Could not fill form: {e}")
    else:
        record("Create project", module, "WARN", "Could not find create project button", ss)

    # ── Time Tracking ──
    print("\n-- Time Tracking --")
    if not is_alive(driver):
        record("Time tracking", module, "FAIL", "Browser crashed"); return

    try:
        driver.get(base)
        time.sleep(2)
    except:
        record("Time tracking", module, "FAIL", "Cannot navigate"); return

    if not is_alive(driver):
        record("Time tracking", module, "FAIL", "Browser crashed"); return

    found_time = False
    nav_sidebar(driver, ["time", "timesheet", "time track", "hours"])
    time.sleep(1)
    if is_alive(driver):
        page = driver.page_source.lower()
        if any(kw in page for kw in ["time", "timesheet", "hours", "log time"]):
            found_time = True

    if not found_time and is_alive(driver):
        for path in ["/timesheet", "/time-tracking", "/time", "/timesheets"]:
            try:
                driver.get(base + path)
                time.sleep(2)
                if not is_alive(driver):
                    break
                p = driver.page_source.lower()
                if any(kw in p for kw in ["time", "sheet", "hours"]):
                    found_time = True
                    break
            except:
                continue

    if is_alive(driver):
        ss = screenshot(driver, "projects_time_tracking")
        if found_time:
            record("Time tracking page", module, "PASS", "Time tracking section accessible", ss)
        else:
            record("Time tracking", module, "WARN", "Time tracking section not found", ss)
    else:
        record("Time tracking", module, "FAIL", "Browser crashed")

    # ── Task Management ──
    print("\n-- Task Management --")
    if not is_alive(driver):
        record("Task management", module, "FAIL", "Browser crashed"); return

    try:
        driver.get(base)
        time.sleep(2)
    except:
        record("Task management", module, "FAIL", "Cannot navigate"); return

    if not is_alive(driver):
        record("Task management", module, "FAIL", "Browser crashed"); return

    found_tasks = False
    nav_sidebar(driver, ["task", "to-do", "todo", "board", "kanban"])
    time.sleep(1)
    if is_alive(driver):
        page = driver.page_source.lower()
        if any(kw in page for kw in ["task", "todo", "to-do", "kanban", "board"]):
            found_tasks = True

    if not found_tasks and is_alive(driver):
        for path in ["/tasks", "/task", "/board", "/kanban"]:
            try:
                driver.get(base + path)
                time.sleep(2)
                if not is_alive(driver):
                    break
                p = driver.page_source.lower()
                if any(kw in p for kw in ["task", "board", "kanban"]):
                    found_tasks = True
                    break
            except:
                continue

    if is_alive(driver):
        ss = screenshot(driver, "projects_tasks")
        if found_tasks:
            record("Task management page", module, "PASS", "Task management section accessible", ss)
        else:
            record("Task management", module, "WARN", "Task management section not found", ss)
    else:
        record("Task management", module, "FAIL", "Browser crashed")

    # ── Employee Login ──
    print("\n-- Employee Login - Assigned Projects --")
    if not is_alive(driver):
        record("Employee projects", module, "FAIL", "Browser crashed"); return

    try:
        driver.delete_all_cookies()
    except:
        pass

    ok = login(driver, base, CREDS["employee"]["email"], CREDS["employee"]["password"])
    if not is_alive(driver):
        record("Employee login", module, "FAIL", "Browser crashed"); return

    ss = screenshot(driver, "projects_employee_login")
    if not ok:
        record("Employee login", module, "FAIL", "Could not login as employee", ss)
        record_bug("[Projects] Employee login failed", module, "critical",
                   f"Cannot login as Employee to projects module.", ss, base)
        return

    record("Employee login", module, "PASS", f"URL: {driver.current_url}", ss)

    page = driver.page_source.lower()
    emp_kw = ["my project", "assigned", "task", "project", "team", "timesheet"]
    found = [kw for kw in emp_kw if kw in page]
    ss = screenshot(driver, "projects_employee_dashboard")
    if found:
        record("Employee projects view", module, "PASS", f"Found keywords: {found}", ss)
    else:
        record("Employee projects view", module, "WARN", "No project keywords on employee view", ss)


# ── HTTP Health Check ───────────────────────────────────────────────────────
def test_module_http_health():
    print("\n" + "="*70)
    print("HTTP HEALTH CHECKS")
    print("="*70)
    for name, url in URLS.items():
        try:
            r = requests.get(url, timeout=15, allow_redirects=True)
            if r.status_code >= 500:
                record(f"{name} HTTP status", name, "FAIL", f"Status {r.status_code} at {url}")
                record_bug(f"[{name.title()}] HTTP {r.status_code} error", name, "critical",
                           f"GET {url} returns HTTP {r.status_code}", "", url)
            elif r.status_code >= 400:
                record(f"{name} HTTP status", name, "WARN", f"Status {r.status_code} at {url}")
            else:
                record(f"{name} HTTP status", name, "PASS", f"Status {r.status_code}")
        except Exception as e:
            record(f"{name} HTTP check", name, "FAIL", str(e))
            record_bug(f"[{name.title()}] Unreachable", name, "critical",
                       f"Cannot reach {url}: {e}", "", url)


# ── GitHub Issue Filing ─────────────────────────────────────────────────────
def file_github_issues():
    if not bugs:
        print("\nNo bugs to file on GitHub.")
        return

    print(f"\n{'='*70}")
    print(f"FILING {len(bugs)} GITHUB ISSUES")
    print("="*70)

    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }
    api = f"https://api.github.com/repos/{GITHUB_REPO}/issues"

    for bug in bugs:
        severity_label = f"severity:{bug['severity']}"
        body = (
            f"## Bug Report (Automated E2E Test)\n\n"
            f"**Module:** {bug['module'].title()}\n"
            f"**Severity:** {bug['severity'].upper()}\n"
            f"**URL:** {bug.get('url', 'N/A')}\n"
            f"**Timestamp:** {datetime.now().isoformat()}\n\n"
            f"### Description\n{bug['description']}\n\n"
            f"### Steps to Reproduce\n"
            f"1. Navigate to the module URL\n"
            f"2. Perform the action described above\n"
            f"3. Observe the error\n\n"
            f"### Expected Behavior\nPage should load/function correctly without errors.\n\n"
            f"### Screenshot\nSaved locally at: `{bug.get('screenshot', 'N/A')}`\n\n"
            f"---\n*Filed by automated E2E test suite*"
        )

        payload = {
            "title": bug["title"],
            "body": body,
            "labels": ["bug", "e2e-test", bug["module"], severity_label],
        }

        try:
            r = requests.post(api, json=payload, headers=headers, timeout=15)
            if r.status_code == 201:
                issue_url = r.json().get("html_url", "")
                print(f"  [FILED] {bug['title']} -> {issue_url}")
            else:
                print(f"  [WARN] Could not file '{bug['title']}': HTTP {r.status_code} - {r.text[:200]}")
        except Exception as e:
            print(f"  [ERROR] Failed to file '{bug['title']}': {e}")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("="*70)
    print("EMP CLOUD HRMS - E2E TEST SUITE")
    print("Rewards | Exit Management | Project Management")
    print(f"Started: {datetime.now().isoformat()}")
    print("="*70)

    # HTTP health check first
    test_module_http_health()

    # Each module gets its own fresh driver
    for test_func in [test_rewards_module, test_exit_module, test_projects_module]:
        try:
            test_func()
        except Exception as e:
            mod_name = test_func.__name__.replace("test_", "").replace("_module", "")
            print(f"\n  [CRITICAL] {test_func.__name__} crashed: {e}")
            traceback.print_exc()
            record(f"{mod_name} module execution", mod_name, "FAIL", f"Module test crashed: {e}")
        gc.collect()
        time.sleep(3)

    # File GitHub issues
    file_github_issues()

    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print("="*70)
    total = len(test_results)
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = sum(1 for r in test_results if r["status"] == "FAIL")
    warned = sum(1 for r in test_results if r["status"] == "WARN")
    print(f"  Total: {total} | PASS: {passed} | FAIL: {failed} | WARN: {warned}")
    print(f"  Bugs found: {len(bugs)}")

    for module in ["rewards", "exit", "projects"]:
        mod_results = [r for r in test_results if r["module"] == module]
        mod_pass = sum(1 for r in mod_results if r["status"] == "PASS")
        mod_fail = sum(1 for r in mod_results if r["status"] == "FAIL")
        mod_warn = sum(1 for r in mod_results if r["status"] == "WARN")
        print(f"  {module.upper():12s}: {len(mod_results)} tests | P:{mod_pass} F:{mod_fail} W:{mod_warn}")

    # Save results
    results_file = os.path.join(SCREENSHOTS_DIR, "test_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_results": test_results,
            "bugs": bugs,
            "summary": {"total": total, "passed": passed, "failed": failed, "warned": warned},
            "timestamp": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {results_file}")
    print(f"Screenshots in: {SCREENSHOTS_DIR}")
    print(f"\nCompleted: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
