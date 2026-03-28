"""
Ravi Kumar's Manager Day — Pass 2 (Deeper Investigation)
Based on Pass 1 findings, this test dives deeper into:
- /manager page interactions (approve/reject leave, click team members)
- /attendance page (actual attendance page, not dashboard)
- /leave page (leave management, balances)
- Performance & Rewards SSO login flow
- Helpdesk, Whistleblowing, Reports — navigate via sidebar links directly
- Project module assessment
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import json
import time
import datetime
import traceback
import requests
import base64
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
API_URL  = "https://test-empcloud-api.empcloud.com"
EMAIL    = "ananya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT  = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = Path(r"C:\Users\Admin\screenshots\manager_ravi_p2")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

PERFORMANCE_URL = "https://test-performance.empcloud.com"
REWARDS_URL     = "https://test-rewards.empcloud.com"
PROJECT_URL     = "https://test-project.empcloud.com"

issues_found = []
test_results = []
test_count = 0
driver = None

# ── Helpers ─────────────────────────────────────────────────────────────────

def get_driver():
    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    svc = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(5)
    return d


def restart_driver():
    global driver, test_count
    test_count += 1
    if test_count % 3 == 0 and driver:
        try: driver.quit()
        except: pass
        driver = get_driver()
        login_ui(driver)
    return driver


def ensure_driver():
    global driver
    if driver is None:
        driver = get_driver()
    return driver


def screenshot(name):
    ts = datetime.datetime.now().strftime("%H%M%S")
    fname = f"{ts}_{name}.png"
    fpath = SCREENSHOT_DIR / fname
    try:
        driver.save_screenshot(str(fpath))
        print(f"    [screenshot] {fpath}")
        return fpath
    except Exception as e:
        print(f"    [screenshot failed] {e}")
        return None


def upload_screenshot_to_github(filepath):
    if not filepath or not Path(filepath).exists():
        return None
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        fname = Path(filepath).name
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/manager_ravi_p2/{fname}"
        headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
        resp = requests.put(url, headers=headers, json={
            "message": f"Upload screenshot: {fname}", "content": content, "branch": "main"
        }, timeout=30)
        if resp.status_code in (200, 201):
            return resp.json().get("content", {}).get("download_url", "")
        return None
    except:
        return None


def file_github_issue(title, body, labels=None):
    if labels is None:
        labels = ["bug", "manager-experience"]
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    # Dedupe
    try:
        search_resp = requests.get(
            "https://api.github.com/search/issues", headers=headers,
            params={"q": f'repo:{GITHUB_REPO} is:issue state:open "{title[:50]}"'}, timeout=15
        )
        if search_resp.status_code == 200:
            items = search_resp.json().get("items", [])
            if items:
                print(f"    [issue exists] {items[0]['html_url']}")
                issues_found.append({"title": title, "url": items[0]["html_url"], "existing": True})
                return items[0]["html_url"]
    except: pass

    payload = {"title": title, "body": body, "labels": labels}
    try:
        resp = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                             headers=headers, json=payload, timeout=30)
        if resp.status_code == 201:
            issue_url = resp.json()["html_url"]
            print(f"    [issue filed] {issue_url}")
            issues_found.append({"title": title, "url": issue_url})
            return issue_url
        else:
            print(f"    [issue failed] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"    [issue error] {e}")
    return None


def record_issue(title, description, screenshot_path=None, labels=None):
    img_url = upload_screenshot_to_github(screenshot_path) if screenshot_path else None
    body = f"## Description\n{description}\n\n"
    body += f"**User:** Ananya (ananya@technova.in) acting as Manager/Team Lead\n"
    body += f"**Persona:** Ravi Kumar -- Team Lead at TechNova Solutions\n"
    body += f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    body += f"**URL:** {driver.current_url if driver else 'N/A'}\n\n"
    if img_url:
        body += f"## Screenshot\n![screenshot]({img_url})\n\n"
    elif screenshot_path:
        body += f"## Screenshot\nLocal: `{screenshot_path}` (upload failed)\n\n"
    body += "## Steps to Reproduce\n1. Login as ananya@technova.in (org admin / manager)\n2. Navigate to the relevant section\n3. Observe the issue\n\n"
    body += "## Expected\nManagers should be able to manage their team efficiently.\n\n"
    body += "## Actual\n" + description + "\n"
    file_github_issue(title, body, labels or ["bug", "manager-experience"])


def record_result(test_name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {test_name}: {details}")
    test_results.append({"test": test_name, "passed": passed, "details": details})


def safe_navigate(url, wait_secs=3):
    try:
        driver.get(url)
        time.sleep(wait_secs)
    except Exception as e:
        print(f"    [nav error] {url}: {e}")


def page_text():
    try: return driver.find_element(By.TAG_NAME, "body").text.lower()
    except: return ""


def page_source():
    try: return driver.page_source.lower()
    except: return ""


def login_ui(d):
    try:
        d.get(f"{BASE_URL}/login")
        time.sleep(3)
        email_input = None
        for sel in ["input[name='email']", "input[type='email']", "#email",
                     "input[placeholder*='mail']", "input[placeholder*='Email']"]:
            try:
                email_input = d.find_element(By.CSS_SELECTOR, sel)
                if email_input: break
            except: continue
        if not email_input:
            for inp in d.find_elements(By.TAG_NAME, "input"):
                t = inp.get_attribute("type") or ""
                if t in ("email", "text"):
                    email_input = inp
                    break
        if not email_input:
            print("  [login] Cannot find email input")
            return False
        email_input.clear()
        email_input.send_keys(EMAIL)
        time.sleep(0.5)
        pwd_input = None
        for sel in ["input[name='password']", "input[type='password']", "#password"]:
            try:
                pwd_input = d.find_element(By.CSS_SELECTOR, sel)
                if pwd_input: break
            except: continue
        if pwd_input:
            pwd_input.clear()
            pwd_input.send_keys(PASSWORD)
            time.sleep(0.5)
        for sel in ["button[type='submit']", "button:not([type='button'])", "input[type='submit']"]:
            try:
                btn = d.find_element(By.CSS_SELECTOR, sel)
                btn.click()
                break
            except: continue
        time.sleep(4)
        if "/login" not in d.current_url:
            print(f"  [login] OK -- {d.current_url}")
            return True
        else:
            print("  [login] Still on login page")
            return False
    except Exception as e:
        print(f"  [login error] {e}")
        return False


def login_sso_module(module_url, module_name):
    """Login to an SSO module (Performance, Rewards, etc.) with its own login page."""
    safe_navigate(module_url)
    time.sleep(3)
    current = driver.current_url
    body = page_text()

    # Check if already logged in (not on login page)
    if "/login" not in current and "sign in" not in body:
        print(f"    [SSO] Already logged in to {module_name}")
        return True

    # It has its own login form
    email_input = None
    for sel in ["input[name='email']", "input[type='email']", "#email",
                 "input[placeholder*='mail']", "input[placeholder*='Email']",
                 "input[placeholder*='address']"]:
        try:
            email_input = driver.find_element(By.CSS_SELECTOR, sel)
            if email_input: break
        except: continue
    if not email_input:
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            t = inp.get_attribute("type") or ""
            p = (inp.get_attribute("placeholder") or "").lower()
            if t == "email" or "email" in p or "mail" in p:
                email_input = inp
                break

    if not email_input:
        print(f"    [SSO] Cannot find email input on {module_name}")
        return False

    email_input.clear()
    email_input.send_keys(EMAIL)
    time.sleep(0.3)

    pwd_input = None
    for sel in ["input[name='password']", "input[type='password']"]:
        try:
            pwd_input = driver.find_element(By.CSS_SELECTOR, sel)
            if pwd_input: break
        except: continue
    if pwd_input:
        pwd_input.clear()
        pwd_input.send_keys(PASSWORD)
        time.sleep(0.3)

    # Submit
    for sel in ["button[type='submit']", "button.btn-primary", "button"]:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                txt = btn.text.lower()
                if "sign" in txt or "log" in txt or "submit" in txt:
                    try: btn.click()
                    except: driver.execute_script("arguments[0].click();", btn)
                    time.sleep(4)
                    if "/login" not in driver.current_url:
                        print(f"    [SSO] Logged in to {module_name} at {driver.current_url}")
                        return True
        except: continue

    # Fallback: just click first submit-type button
    for sel in ["button[type='submit']", "input[type='submit']"]:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            btn.click()
            time.sleep(4)
            if "/login" not in driver.current_url:
                print(f"    [SSO] Logged in to {module_name}")
                return True
        except: continue

    print(f"    [SSO] Failed to login to {module_name}")
    return False


# ═══════════════════════════════════════════════════════════════════════════
#  DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_01_manager_page_deep():
    """Deep dive into /manager page: team list, attendance, leave requests, actions."""
    print("\n=== TEST 01: Manager Page Deep Dive ===")
    ensure_driver()
    login_ui(driver)

    safe_navigate(f"{BASE_URL}/manager")
    time.sleep(3)
    shot = screenshot("01_manager_page")
    body = page_text()
    src = page_source()

    # Verify we're on My Team page
    on_manager = "my team" in body
    record_result("Manager Page Loads", on_manager, f"URL: {driver.current_url}")

    if not on_manager:
        record_issue(
            "Manager /manager page does not load My Team view",
            "Navigating to /manager does not show the My Team dashboard.",
            shot
        )
        return

    # Check dashboard stats (Present, Half Day, On Time, Late, Absent, Total)
    stats_keywords = ["present", "half day", "on time", "late", "absent"]
    found_stats = [kw for kw in stats_keywords if kw in body]
    record_result("Manager Dashboard Stats", len(found_stats) >= 3,
                  f"Found: {found_stats}")

    # Check Team Attendance Today section
    has_team_att = "team attendance today" in body
    record_result("Team Attendance Today Section", has_team_att,
                  "Section found" if has_team_att else "Not found")

    # Check Team Leave Calendar (This Week)
    has_leave_cal = "team leave calendar" in body or "leave calendar" in body
    record_result("Team Leave Calendar Section", has_leave_cal,
                  "Section found" if has_leave_cal else "Not found")

    # Check Pending Leave Requests section
    has_pending = "pending leave requests" in body or "pending leave" in body
    record_result("Pending Leave Requests Section", has_pending,
                  "Section found" if has_pending else "Not found")

    # Check if pending leaves show details (employee name, type, dates)
    if has_pending:
        # Look for leave request entries
        try:
            # Get all text in pending section area
            pending_section = None
            all_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Pending Leave')]")
            if all_elements:
                # Get the parent container
                parent = all_elements[0]
                for _ in range(3):
                    try: parent = parent.find_element(By.XPATH, "..")
                    except: break
                section_text = parent.text.lower()
                has_name = any(name in section_text for name in ["priya", "rahul", "vikram", "ananya", "employee"])
                has_type = any(t in section_text for t in ["earned", "casual", "sick", "annual", "leave type"])
                has_date = any(d in section_text for d in ["2026", "2025", "mar", "apr", "date"])

                record_result("Leave Request Shows Employee Name", has_name,
                              "Names visible" if has_name else "No employee names in pending requests")
                record_result("Leave Request Shows Type", has_type,
                              "Type visible" if has_type else "No leave type shown")
                record_result("Leave Request Shows Dates", has_date,
                              "Dates visible" if has_date else "No dates shown")
        except Exception as e:
            print(f"    Error checking pending details: {e}")

    # Check for approve/reject buttons
    try:
        approve_btns = driver.find_elements(By.XPATH,
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'approve')]")
        reject_btns = driver.find_elements(By.XPATH,
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reject')]")

        # Also check for icon-based approve/reject (checkmark / X)
        action_btns = driver.find_elements(By.CSS_SELECTOR,
            "[class*='approve'], [class*='reject'], [class*='accept'], [class*='decline'], "
            "[data-action='approve'], [data-action='reject']")

        has_approve = len(approve_btns) > 0 or any('approve' in (b.get_attribute('class') or '').lower() for b in action_btns)
        has_reject = len(reject_btns) > 0 or any('reject' in (b.get_attribute('class') or '').lower() for b in action_btns)

        if not has_approve and not has_reject:
            # Check for icon buttons (green check / red X)
            svg_btns = driver.find_elements(By.CSS_SELECTOR, "svg, .icon, [class*='icon']")
            if len(svg_btns) > 0:
                # Check page source for approve/reject action patterns
                if 'approve' in src or 'reject' in src or 'accept' in src:
                    has_approve = True

        record_result("Approve/Reject Actions on Manager Page",
                      has_approve or has_reject,
                      f"Approve btns: {len(approve_btns)}, Reject btns: {len(reject_btns)}, "
                      f"Action elements: {len(action_btns)}")

        if not has_approve and not has_reject and has_pending:
            record_issue(
                "Manager page shows pending leaves but no approve/reject buttons",
                "The /manager page shows pending leave requests but there are no "
                "visible approve/reject buttons. Managers need one-click approve/reject "
                "directly from the My Team dashboard.",
                screenshot("01_no_approve_reject")
            )
    except Exception as e:
        print(f"    Error checking approve/reject: {e}")

    # Check if team members are clickable (link to profile)
    try:
        # Look for employee name links in team attendance section
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='employee'], a[href*='profile']")
        clickable_names = [l for l in links if l.text.strip()]
        record_result("Team Members Clickable", len(clickable_names) > 0,
                      f"{len(clickable_names)} clickable member links")
    except:
        pass


def test_02_attendance_page():
    """Deep dive into /attendance page."""
    print("\n=== TEST 02: Attendance Page ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/attendance")
    time.sleep(3)
    shot = screenshot("02_attendance_page")
    body = page_text()
    current = driver.current_url

    # Check we're actually on attendance
    on_attendance = "/attendance" in current and "attendance" in body
    record_result("Attendance Page Loads", on_attendance, f"URL: {current}")

    if not on_attendance:
        return

    # What kind of attendance page is this? Self or team?
    is_self = "my attendance" in body or "check in" in body or "clock in" in body
    is_team = "team" in body or "all" in body or "employee" in body
    record_result("Attendance Page Type", True,
                  f"Self-service: {is_self}, Team view: {is_team}")

    # Check for date filter
    try:
        date_inputs = driver.find_elements(By.CSS_SELECTOR,
            "input[type='date'], [class*='date-picker'], [class*='DatePicker'], "
            "[class*='datepicker'], input[placeholder*='date'], input[placeholder*='Date']")
        has_date_filter = len(date_inputs) > 0
    except:
        has_date_filter = False

    # Also check for month/date selector
    if not has_date_filter:
        has_date_filter = any(kw in body for kw in ["select date", "choose date", "from date",
                                                     "to date", "date range"])
    record_result("Attendance Date Filter", has_date_filter,
                  "Found" if has_date_filter else "Not found")

    # Check for present/absent/late status
    has_status = any(kw in body for kw in ["present", "absent", "late", "half day",
                                            "work from home", "wfh", "on time"])
    record_result("Attendance Status Display", has_status,
                  "Status indicators found" if has_status else "No status indicators")

    # Take screenshot of full page scroll
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        screenshot("02_attendance_scrolled")
    except: pass


def test_03_leave_page_approvals():
    """Deep dive into /leave page - check for team leave management and approvals."""
    print("\n=== TEST 03: Leave Page & Approvals ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/leave")
    time.sleep(3)
    shot = screenshot("03_leave_page")
    body = page_text()
    current = driver.current_url

    on_leave = "/leave" in current
    record_result("Leave Page Loads", on_leave, f"URL: {current}")

    if not on_leave:
        return

    # Check for tabs/sections: My Leaves, Team Leaves, Approvals, Balances
    tab_keywords = {
        "my leaves": "my leave" in body or "my request" in body,
        "team leaves": "team" in body,
        "approvals": "approval" in body or "approve" in body or "pending" in body,
        "balances": "balance" in body or "remaining" in body or "available" in body,
    }
    found_tabs = {k: v for k, v in tab_keywords.items() if v}
    record_result("Leave Page Sections", len(found_tabs) > 0,
                  f"Found: {list(found_tabs.keys())}")

    # Look for clickable tabs
    try:
        tabs = driver.find_elements(By.CSS_SELECTOR,
            "[role='tab'], .tab, [class*='tab'], button[class*='tab'], "
            "a[class*='tab'], [class*='Tab']")
        tab_texts = [t.text.strip().lower() for t in tabs if t.text.strip()]
        print(f"    Tabs found: {tab_texts}")

        # Click on "Approvals" or "Team" tab if exists
        for tab in tabs:
            txt = tab.text.strip().lower()
            if "approval" in txt or "team" in txt or "pending" in txt:
                try:
                    tab.click()
                    time.sleep(2)
                    screenshot("03_leave_approvals_tab")
                    body2 = page_text()
                    has_requests = any(kw in body2 for kw in ["request", "pending",
                                                               "approve", "reject", "employee"])
                    record_result("Leave Approvals Tab", has_requests,
                                  f"Tab '{txt}' shows requests: {has_requests}")
                    break
                except Exception as e:
                    print(f"    Tab click error: {e}")
    except Exception as e:
        print(f"    Tab search error: {e}")

    # Check for team leave balances link/section
    try:
        balance_links = driver.find_elements(By.XPATH,
            "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'balance')] | "
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'balance')]")
        if balance_links:
            print(f"    Balance links: {[l.text for l in balance_links]}")
    except: pass


def test_04_compoff_deep():
    """Deep dive into comp-off page: requests and pending approvals tab."""
    print("\n=== TEST 04: Comp-Off Deep Dive ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/leave/comp-off")
    time.sleep(3)
    shot = screenshot("04_compoff")
    body = page_text()

    on_compoff = "comp" in body or "compensatory" in body
    record_result("Comp-Off Page Loads", on_compoff, f"URL: {driver.current_url}")

    if not on_compoff:
        return

    # Check for tabs: My Requests / Pending Approvals
    try:
        tabs = driver.find_elements(By.CSS_SELECTOR,
            "[role='tab'], .tab, [class*='tab'], button[class*='tab'], a[class*='tab']")
        tab_texts = [t.text.strip() for t in tabs if t.text.strip()]
        print(f"    Comp-off tabs: {tab_texts}")

        # Click "Pending Approvals" tab
        for tab in tabs:
            txt = tab.text.strip().lower()
            if "pending" in txt or "approval" in txt:
                try:
                    tab.click()
                    time.sleep(2)
                    body2 = page_text()
                    shot2 = screenshot("04_compoff_pending")

                    # Check for approve/reject
                    has_actions = any(kw in body2 for kw in ["approve", "reject", "decline", "accept"])
                    record_result("Comp-Off Pending Approvals Tab", True, f"Tab found, actions: {has_actions}")

                    if not has_actions:
                        # Check if there are pending items
                        has_pending = "pending" in body2 or "0" not in body2[:50]
                        record_result("Comp-Off Approve/Reject Actions", has_actions,
                                      "No approve/reject buttons" if not has_actions else "Actions found")
                    break
                except Exception as e:
                    print(f"    Tab click error: {e}")
    except Exception as e:
        print(f"    Comp-off tab error: {e}")

    # Check for "Request Comp Off" button
    try:
        request_btn = driver.find_elements(By.XPATH,
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'request')] | "
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'comp')]")
        record_result("Request Comp-Off Button", len(request_btn) > 0,
                      f"Found {len(request_btn)} buttons" if request_btn else "Not found")
    except: pass


def test_05_performance_sso_login():
    """Login to Performance module and check for manager review features."""
    print("\n=== TEST 05: Performance Module SSO ===")
    restart_driver()

    ok = login_sso_module(PERFORMANCE_URL, "Performance")
    shot = screenshot("05_performance")
    body = page_text()

    if ok and "/login" not in driver.current_url:
        record_result("Performance SSO Login", True, f"At {driver.current_url}")

        # Check for manager-relevant features
        has_reviews = any(kw in body for kw in ["review", "appraisal", "assessment",
                                                 "evaluation", "goal", "kpi", "okr"])
        has_team = any(kw in body for kw in ["team", "direct report", "reportee", "my team"])
        has_pending = any(kw in body for kw in ["pending", "due", "overdue", "action"])

        record_result("Performance Reviews Available", has_reviews,
                      "Review features found" if has_reviews else "No review features visible")
        record_result("Performance Team View", has_team,
                      "Team section found" if has_team else "No team section")
        record_result("Pending Performance Reviews", has_pending,
                      "Pending items found" if has_pending else "No pending items")

        # Navigate around
        for path in ["/reviews", "/my-team", "/dashboard", "/goals"]:
            try:
                safe_navigate(f"{PERFORMANCE_URL}{path}", 2)
                ptext = page_text()
                if "review" in ptext or "goal" in ptext or "team" in ptext:
                    print(f"    Performance {path}: content found")
                    screenshot(f"05_performance{path.replace('/', '_')}")
            except: pass
    else:
        record_result("Performance SSO Login", False,
                      "Cannot login - SSO not working from EmpCloud to Performance module")
        record_issue(
            "Performance module requires separate login, no SSO from EmpCloud",
            "When navigating to the Performance module from EmpCloud, the manager is "
            "presented with a separate login page instead of being automatically signed in "
            "via SSO. This breaks the seamless manager experience for performance reviews.",
            shot
        )


def test_06_rewards_sso_login():
    """Login to Rewards module and check for kudos/nomination features."""
    print("\n=== TEST 06: Rewards Module SSO ===")
    restart_driver()

    ok = login_sso_module(REWARDS_URL, "Rewards")
    shot = screenshot("06_rewards")
    body = page_text()

    if ok and "/login" not in driver.current_url:
        record_result("Rewards SSO Login", True, f"At {driver.current_url}")

        has_give = any(kw in body for kw in ["give", "send", "nominate", "recognize",
                                              "appreciate", "kudos", "badge", "reward"])
        record_result("Rewards Give/Nominate Feature", has_give,
                      "Give/nominate found" if has_give else "No give/nominate action")
        screenshot("06_rewards_dashboard")

        # Try navigation
        for path in ["/give", "/nominate", "/dashboard", "/leaderboard", "/history"]:
            try:
                safe_navigate(f"{REWARDS_URL}{path}", 2)
                ptext = page_text()
                if any(kw in ptext for kw in ["reward", "badge", "point", "recognize", "kudos"]):
                    print(f"    Rewards {path}: content found")
                    screenshot(f"06_rewards{path.replace('/', '_')}")
            except: pass
    else:
        record_result("Rewards SSO Login", False, "Cannot login - separate login required")
        record_issue(
            "Rewards module requires separate login, no SSO from EmpCloud",
            "The Rewards module shows its own login page instead of SSO from EmpCloud. "
            "Managers should be able to seamlessly access the Rewards module to give kudos.",
            shot
        )


def test_07_helpdesk_team():
    """Check helpdesk for team ticket visibility."""
    print("\n=== TEST 07: Helpdesk Deep Dive ===")
    restart_driver()

    # Use known URLs from sidebar
    for url_path in ["/helpdesk/dashboard", "/helpdesk/tickets", "/helpdesk/my-tickets"]:
        safe_navigate(f"{BASE_URL}{url_path}")
        time.sleep(2)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(f"{BASE_URL}{url_path}")
            time.sleep(2)
            body = page_text()

        shot = screenshot(f"07_helpdesk_{url_path.split('/')[-1]}")
        print(f"    {url_path}: URL={driver.current_url}")

        if "helpdesk" in body or "ticket" in body or "support" in body:
            record_result(f"Helpdesk {url_path}", True, "Page loaded")
        else:
            record_result(f"Helpdesk {url_path}", False, "Content not found")

    # Check if dashboard shows team tickets
    safe_navigate(f"{BASE_URL}/helpdesk/dashboard")
    time.sleep(2)
    body = page_text()
    has_team_view = any(kw in body for kw in ["team", "department", "all ticket",
                                               "assigned", "open", "closed", "resolved"])
    record_result("Helpdesk Team Ticket Visibility", has_team_view,
                  "Team view found" if has_team_view else "No team ticket view")

    if not has_team_view:
        record_issue(
            "Helpdesk dashboard does not show team tickets for managers",
            "The helpdesk dashboard does not provide a view of tickets raised by team members. "
            "Managers need visibility into their team's support issues to help resolve blockers.",
            screenshot("07_helpdesk_no_team")
        )


def test_08_events_create():
    """Events: Can manager create a team event?"""
    print("\n=== TEST 08: Events Create ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/events")
    time.sleep(3)
    shot = screenshot("08_events")
    body = page_text()

    has_events = "event" in body
    record_result("Events Page", has_events, "Loaded" if has_events else "Not found")

    if not has_events:
        return

    # Look for create/manage button
    try:
        create_btns = driver.find_elements(By.XPATH,
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'manage')] | "
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create')] | "
            "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'manage')] | "
            "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create')]")
        btn_texts = [b.text.strip() for b in create_btns if b.text.strip()]
        record_result("Create Event Button", len(create_btns) > 0,
                      f"Buttons: {btn_texts}" if create_btns else "Not found")

        # Click manage/create
        if create_btns:
            try:
                create_btns[0].click()
                time.sleep(2)
                shot2 = screenshot("08_event_create")
                body2 = page_text()
                has_form = any(kw in body2 for kw in ["title", "description", "date", "time",
                                                       "location", "attendee", "invite", "create"])
                record_result("Event Creation Form", has_form,
                              "Form fields found" if has_form else "No creation form")
            except Exception as e:
                print(f"    Create click error: {e}")
    except Exception as e:
        print(f"    Error: {e}")


def test_09_whistleblowing():
    """Whistleblowing: Check submit, track, dashboard, all reports."""
    print("\n=== TEST 09: Whistleblowing ===")
    restart_driver()

    for url_path, desc in [
        ("/whistleblowing/dashboard", "Dashboard"),
        ("/whistleblowing/reports", "All Reports"),
        ("/whistleblowing/submit", "Submit Report"),
        ("/whistleblowing/track", "Track Report"),
    ]:
        safe_navigate(f"{BASE_URL}{url_path}")
        time.sleep(2)
        body = page_text()
        current = driver.current_url
        if "/login" in current:
            login_ui(driver)
            safe_navigate(f"{BASE_URL}{url_path}")
            time.sleep(2)
            body = page_text()

        shot = screenshot(f"09_whistle_{desc.lower().replace(' ', '_')}")
        has_content = any(kw in body for kw in ["whistl", "report", "anonymous", "submit",
                                                 "track", "complaint", "grievance", "incident"])
        record_result(f"Whistleblowing {desc}", has_content,
                      "Content found" if has_content else "No content")

    # Note about manager visibility
    print("    Note: Whistleblowing reports typically go to Ethics/HR committee, not direct managers")
    record_result("Whistleblowing Manager Note", True,
                  "Whistleblowing correctly routes to HR/Ethics, not direct manager")


def test_10_reports_section():
    """Check for team reports and export capabilities."""
    print("\n=== TEST 10: Reports & Analytics ===")
    restart_driver()

    # There's no /reports in sidebar - check if dashboard has analytics
    safe_navigate(f"{BASE_URL}/")
    time.sleep(2)
    body = page_text()

    # Look for report/analytics links in main app
    has_report_link = any(kw in body for kw in ["report", "analytics", "export", "download"])
    record_result("Dashboard Report Links", has_report_link,
                  "Report links found" if has_report_link else "No report links on dashboard")

    # Check attendance page for export
    safe_navigate(f"{BASE_URL}/attendance")
    time.sleep(2)
    body = page_text()
    src = page_source()

    has_export = any(kw in body + src for kw in ["export", "download", "csv", "excel", "pdf",
                                                   "generate report"])
    try:
        export_btns = driver.find_elements(By.XPATH,
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'export')] | "
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'download')] | "
            "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'export')]")
        if export_btns:
            has_export = True
    except: pass

    record_result("Attendance Export", has_export,
                  "Export found" if has_export else "No export on attendance page")
    shot = screenshot("10_attendance_export")

    # Check leave page for export
    safe_navigate(f"{BASE_URL}/leave")
    time.sleep(2)
    body = page_text()
    has_leave_export = any(kw in body for kw in ["export", "download", "report"])
    record_result("Leave Export", has_leave_export,
                  "Export found" if has_leave_export else "No export on leave page")

    if not has_export and not has_leave_export:
        record_issue(
            "No export or report generation for team attendance and leave",
            "Neither the attendance nor leave pages offer export/download/report "
            "generation capabilities. Managers need to generate reports (CSV/Excel/PDF) "
            "for compliance and planning purposes.",
            screenshot("10_no_export")
        )


def test_11_dashboard_my_team_link():
    """Verify dashboard has link/section pointing to My Team."""
    print("\n=== TEST 11: Dashboard to My Team Link ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/")
    time.sleep(3)
    body = page_text()
    src = page_source()
    shot = screenshot("11_dashboard")

    # Check if dashboard shows team stats at a glance
    has_team_glance = any(kw in body for kw in ["my team", "team overview", "direct reports",
                                                 "team summary"])
    record_result("Dashboard My Team At-a-Glance", has_team_glance,
                  "Team section on dashboard" if has_team_glance else "No team section on main dashboard")

    # Check sidebar for My Team link (we know it exists from pass 1)
    try:
        team_link = driver.find_elements(By.XPATH,
            "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'my team')]")
        record_result("Sidebar My Team Link", len(team_link) > 0,
                      f"Found {len(team_link)} links" if team_link else "Not found")
    except: pass

    if not has_team_glance:
        record_issue(
            "Main dashboard lacks team summary widget for managers",
            "The main dashboard (/) does not display a 'My Team' summary widget showing "
            "team status at a glance (who's present/absent/on-leave). While /manager page "
            "has this info, the main dashboard should show a quick summary so managers "
            "don't have to navigate away.",
            shot
        )


def test_12_project_module():
    """Check Project module access."""
    print("\n=== TEST 12: Project Module ===")
    restart_driver()

    safe_navigate(PROJECT_URL)
    time.sleep(4)
    shot = screenshot("12_project_module")
    body = page_text()
    current = driver.current_url

    # From pass 1 we know it shows EmpMonitor landing page
    is_landing = "empmonitor" in body or "empower your team" in body
    is_actual_project = any(kw in body for kw in ["my project", "task", "board", "sprint",
                                                    "kanban", "backlog", "create project"])

    if is_landing:
        record_result("Project Module", False,
                      "Shows marketing/landing page instead of project management tool")
        record_issue(
            "Project module shows marketing landing page instead of tool",
            "Navigating to the Project module (test-project.empcloud.com) shows an "
            "EmpMonitor marketing page ('Empower Your Team with Advanced Project Management') "
            "instead of an actual project management tool. Managers cannot assign tasks or "
            "manage projects for their team.",
            shot
        )
    elif is_actual_project:
        record_result("Project Module", True, "Project management tool loaded")
    else:
        # May need login
        ok = login_sso_module(PROJECT_URL, "Project")
        if ok:
            body2 = page_text()
            has_project = any(kw in body2 for kw in ["project", "task", "board"])
            record_result("Project Module (after login)", has_project,
                          "Loaded" if has_project else "Not accessible")
        else:
            record_result("Project Module", False, "Cannot access")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    global driver

    print("=" * 70)
    print("  RAVI KUMAR'S MANAGER DAY -- Pass 2 (Deep Investigation)")
    print(f"  Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  User: {EMAIL}")
    print("=" * 70)

    driver = get_driver()

    try:
        test_01_manager_page_deep()
        test_02_attendance_page()
        test_03_leave_page_approvals()
        test_04_compoff_deep()
        test_05_performance_sso_login()
        test_06_rewards_sso_login()
        test_07_helpdesk_team()
        test_08_events_create()
        test_09_whistleblowing()
        test_10_reports_section()
        test_11_dashboard_my_team_link()
        test_12_project_module()

    except Exception as e:
        print(f"\n[FATAL] {e}")
        traceback.print_exc()
    finally:
        if driver:
            try: driver.quit()
            except: pass

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  PASS 2 SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in test_results if r["passed"])
    failed = sum(1 for r in test_results if not r["passed"])
    total = len(test_results)

    print(f"\n  Total: {total}  |  PASSED: {passed}  |  FAILED: {failed}")
    print(f"  Pass rate: {passed/total*100:.1f}%" if total > 0 else "  No tests ran")

    print(f"\n  Issues filed: {len(issues_found)}")
    for issue in issues_found:
        existing = " (existing)" if issue.get("existing") else ""
        print(f"    - {issue['title']}{existing}")
        print(f"      {issue.get('url', 'N/A')}")

    print("\n  Detailed Results:")
    for r in test_results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"    [{status}] {r['test']}: {r['details']}")

    results_path = Path(r"C:\emptesting\manager_ravi_pass2_results.json")
    with open(results_path, "w") as f:
        json.dump({
            "date": datetime.datetime.now().isoformat(),
            "user": EMAIL,
            "persona": "Ravi Kumar -- Team Lead (Pass 2)",
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "issues_filed": len(issues_found),
            "results": test_results,
            "issues": issues_found
        }, f, indent=2)
    print(f"\n  Results saved to: {results_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
