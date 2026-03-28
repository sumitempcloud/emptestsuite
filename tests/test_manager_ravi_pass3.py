"""
Ravi Kumar's Manager Day — Pass 3 (Final Verification & Bug Filing)
Targeted checks based on Pass 1+2 screenshot analysis:
1. Leave Dashboard shows "User P824" instead of real employee names
2. Manager page pending leaves - scroll down to check approve/reject
3. Attendance page - confirm no date filter, check for team vs self toggle
4. Performance/Rewards SSO failure verification
5. Leave page approve/reject workflow
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://test-empcloud.empcloud.com"
EMAIL    = "ananya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT  = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = Path(r"C:\Users\Admin\screenshots\manager_ravi_p3")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

PERFORMANCE_URL = "https://test-performance.empcloud.com"
REWARDS_URL     = "https://test-rewards.empcloud.com"

issues_found = []
test_results = []
test_count = 0
driver = None


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
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/manager_ravi_p3/{fname}"
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
    try: return driver.find_element(By.TAG_NAME, "body").text
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
        print("  [login] Still on login page")
        return False
    except Exception as e:
        print(f"  [login error] {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════

def test_01_leave_dashboard_names():
    """Check Leave Dashboard for 'User P824' bug — employee names not showing."""
    print("\n=== TEST 01: Leave Dashboard Employee Names ===")
    global driver
    driver = get_driver()
    login_ui(driver)

    safe_navigate(f"{BASE_URL}/leave")
    time.sleep(3)
    shot = screenshot("01_leave_dashboard")
    body = page_text()

    # Check pending leave requests section
    print(f"    Page text length: {len(body)}")

    # Look for "User P" pattern (indicates masked/broken names)
    has_user_ids = "User P" in body or "User #" in body or "user p" in body.lower()
    has_real_names = any(name in body for name in ["Priya", "Rahul", "Vikram", "Ananya",
                                                    "Sneha", "Amit", "Deepak", "Neha",
                                                    "Arjun", "Ravi"])

    print(f"    Has 'User P...' IDs: {has_user_ids}")
    print(f"    Has real names: {has_real_names}")

    # Extract the names shown in pending requests
    lines = body.split('\n')
    pending_section = False
    employee_lines = []
    for line in lines:
        if "pending" in line.lower() and "leave" in line.lower():
            pending_section = True
            continue
        if pending_section and line.strip():
            employee_lines.append(line.strip())
            if len(employee_lines) > 15:
                break

    print(f"    Pending request entries:")
    for line in employee_lines[:10]:
        print(f"      | {line}")

    if has_user_ids and not has_real_names:
        record_result("Leave Dashboard Employee Names", False,
                      "Shows 'User P824' style IDs instead of real employee names")
        record_issue(
            "Leave dashboard shows user IDs instead of employee names in pending requests",
            "The Leave Dashboard (/leave) shows entries like 'User P824' instead of actual "
            "employee names (e.g., 'Priya Patel') in the Pending Leave Requests list. "
            "As a manager, I need to see who is requesting leave by name to make informed "
            "approval decisions.\n\n"
            "This may be a data display issue or a broken name resolution in the leave request list.",
            shot
        )
    elif has_real_names:
        record_result("Leave Dashboard Employee Names", True, "Real employee names displayed")
    else:
        record_result("Leave Dashboard Employee Names", False,
                      "Cannot determine — names may be abbreviated or missing")

    # Scroll down to see more
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        shot2 = screenshot("01_leave_scrolled")
    except: pass

    # Check for approve/reject on leave page
    body_lower = body.lower()
    has_approve = "approve" in body_lower
    has_reject = "reject" in body_lower or "decline" in body_lower

    # Look for action buttons or links
    try:
        action_elements = driver.find_elements(By.CSS_SELECTOR,
            "button, a, [role='button']")
        action_texts = [el.text.strip().lower() for el in action_elements if el.text.strip()]
        approve_actions = [t for t in action_texts if "approve" in t or "accept" in t]
        reject_actions = [t for t in action_texts if "reject" in t or "decline" in t]
        print(f"    Approve actions: {approve_actions}")
        print(f"    Reject actions: {reject_actions}")

        # Also check for status column showing approve/reject per row
        status_cells = driver.find_elements(By.XPATH,
            "//*[contains(text(), 'Pending') or contains(text(), 'pending')]")
        print(f"    Pending status cells: {len(status_cells)}")
    except Exception as e:
        print(f"    Error: {e}")

    record_result("Leave Page Approve/Reject", has_approve or has_reject,
                  f"Approve: {has_approve}, Reject: {has_reject}")


def test_02_manager_page_scroll_and_actions():
    """Scroll the manager page to check approve/reject on pending leaves."""
    print("\n=== TEST 02: Manager Page - Scroll & Action Check ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/manager")
    time.sleep(3)
    shot1 = screenshot("02_manager_top")
    body_top = page_text()

    # Scroll to pending leave section
    try:
        driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(1)
        shot2 = screenshot("02_manager_mid")

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        shot3 = screenshot("02_manager_bottom")
    except: pass

    body_full = page_text()

    # Check pending leave request details
    has_pending = "pending leave" in body_full.lower()
    record_result("Manager Page Pending Leaves Section", has_pending,
                  "Section found" if has_pending else "Not found")

    # Extract pending leave request table content
    lines = body_full.split('\n')
    in_pending = False
    pending_data = []
    for line in lines:
        if "pending leave" in line.lower():
            in_pending = True
            continue
        if in_pending and line.strip():
            pending_data.append(line.strip())
            if len(pending_data) > 20:
                break

    print(f"    Pending leave section content:")
    for line in pending_data[:15]:
        print(f"      | {line}")

    # Check if column headers include status/action
    headers_text = " ".join(pending_data[:3]).lower() if pending_data else ""
    has_action_col = any(kw in headers_text for kw in ["action", "status", "approve", "reject"])
    record_result("Pending Leaves Action Column", has_action_col,
                  f"Action/status column found: {has_action_col}")

    # Check for status indicators (pending, approved, rejected)
    statuses_found = []
    for line in pending_data:
        line_lower = line.lower()
        for s in ["pending", "approved", "rejected"]:
            if s in line_lower:
                statuses_found.append(s)
    record_result("Leave Request Status Shown", len(statuses_found) > 0,
                  f"Statuses: {list(set(statuses_found))}")

    # Look for clickable elements in pending section
    try:
        # Try to find the pending leave rows and check for action buttons
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, [class*='request'], [class*='leave-row']")
        print(f"    Table rows found: {len(rows)}")

        if rows:
            for i, row in enumerate(rows[:3]):
                row_text = row.text.strip()
                # Check for buttons/links inside the row
                btns = row.find_elements(By.CSS_SELECTOR, "button, a, svg, [role='button']")
                btn_texts = [b.text.strip() or b.get_attribute("title") or b.get_attribute("aria-label") or "" for b in btns]
                print(f"    Row {i}: '{row_text[:80]}' | Buttons: {[t for t in btn_texts if t]}")
    except Exception as e:
        print(f"    Row analysis error: {e}")

    # Check if there's a "View All" or similar to go to full approval page
    try:
        view_all = driver.find_elements(By.XPATH,
            "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'view all')] | "
            "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'see all')]")
        if view_all:
            print(f"    'View All' links: {[v.text for v in view_all]}")
            record_result("View All Pending Leaves Link", True, f"{len(view_all)} links")
        else:
            record_result("View All Pending Leaves Link", False, "No 'View All' link")
    except: pass


def test_03_attendance_features():
    """Detailed attendance page check: date filter, team toggle, export."""
    print("\n=== TEST 03: Attendance Page Features ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/attendance")
    time.sleep(3)
    shot = screenshot("03_attendance")
    body = page_text()

    # Check what's on the page
    print(f"    Attendance page content preview:")
    for line in body.split('\n')[:20]:
        if line.strip():
            print(f"      | {line.strip()}")

    # Check for Today's label
    has_today = "today" in body.lower()
    record_result("Attendance Shows Today", has_today,
                  "Today's attendance shown" if has_today else "No today label")

    # Check for date picker / calendar / filter
    try:
        date_elements = driver.find_elements(By.CSS_SELECTOR,
            "input[type='date'], [class*='date'], [class*='Date'], "
            "[class*='calendar'], [class*='Calendar'], "
            "[class*='picker'], [class*='Picker'], "
            "input[placeholder*='date'], input[placeholder*='Date']")
        print(f"    Date-related elements: {len(date_elements)}")
        for el in date_elements[:5]:
            print(f"      tag={el.tag_name}, class={el.get_attribute('class')[:50]}, "
                  f"type={el.get_attribute('type')}, placeholder={el.get_attribute('placeholder')}")
    except: pass

    # Check for filter/select controls
    try:
        selects = driver.find_elements(By.CSS_SELECTOR, "select, [role='listbox'], [class*='select']")
        print(f"    Select elements: {len(selects)}")
        for sel in selects[:3]:
            print(f"      text: {sel.text[:50]}")
    except: pass

    # Check for tabs (e.g., My Attendance / Team Attendance)
    try:
        tabs = driver.find_elements(By.CSS_SELECTOR,
            "[role='tab'], [class*='tab'], button[class*='Tab']")
        tab_texts = [t.text.strip() for t in tabs if t.text.strip()]
        print(f"    Tabs: {tab_texts}")

        # Look for team tab
        for tab in tabs:
            txt = tab.text.strip().lower()
            if "team" in txt or "all" in txt:
                print(f"    Found team tab: '{tab.text.strip()}'")
                try:
                    tab.click()
                    time.sleep(2)
                    screenshot("03_attendance_team_tab")
                except: pass
                break
    except: pass

    # Check for late indicators (from pass 2 screenshot, we can see 'Late' column exists)
    has_late_col = "late" in body.lower()
    record_result("Attendance Late Column", has_late_col,
                  "Late column found" if has_late_col else "No late column")

    # Check for export/download
    try:
        export_btns = driver.find_elements(By.XPATH,
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'export')] | "
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'download')] | "
            "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'export')]")
        has_export = len(export_btns) > 0
        record_result("Attendance Export Button", has_export,
                      f"Found {len(export_btns)} export buttons" if has_export else "No export button")
        if not has_export:
            record_issue(
                "Attendance page has no export or download feature",
                "The Attendance Dashboard does not have an export or download button. "
                "Managers need to be able to export attendance data (CSV/Excel/PDF) for "
                "record-keeping, compliance, and sharing with HR.",
                screenshot("03_no_export")
            )
    except: pass


def test_04_performance_sso_verification():
    """Verify Performance module SSO — try clicking from main app's module links."""
    print("\n=== TEST 04: Performance SSO from Main App ===")
    restart_driver()

    # First navigate to dashboard and try the Performance link in Module Insights
    safe_navigate(f"{BASE_URL}/")
    time.sleep(3)
    body = page_text()

    # Try clicking "Performance" link if visible
    try:
        perf_links = driver.find_elements(By.XPATH,
            "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'performance')]")
        if perf_links:
            print(f"    Performance links: {[l.text.strip() for l in perf_links]}")
            # Click the first one
            link = perf_links[0]
            href = link.get_attribute("href") or ""
            print(f"    Link href: {href}")
            try:
                link.click()
                time.sleep(4)
            except:
                driver.execute_script("arguments[0].click();", link)
                time.sleep(4)

            current = driver.current_url
            shot = screenshot("04_performance_from_link")
            body2 = page_text()

            # Check if we landed on performance login or performance dashboard
            on_perf_login = "/login" in current and "performance" in current
            on_perf_dash = "/login" not in current and "performance" in current.lower()

            if on_perf_login:
                record_result("Performance SSO from Dashboard Link", False,
                              f"Redirected to login: {current}")
            elif on_perf_dash:
                record_result("Performance SSO from Dashboard Link", True,
                              f"SSO worked! At: {current}")
            else:
                record_result("Performance SSO from Dashboard Link", False,
                              f"Ended up at: {current}")
        else:
            record_result("Performance Link on Dashboard", False, "No Performance link found")
    except Exception as e:
        record_result("Performance SSO from Dashboard", False, f"Error: {e}")

    # Also try the Module Insights card links
    try:
        safe_navigate(f"{BASE_URL}/")
        time.sleep(2)
        # Look for module cards
        cards = driver.find_elements(By.CSS_SELECTOR,
            "[class*='module'], [class*='card'], [class*='insight']")
        for card in cards:
            if "performance" in card.text.lower():
                print(f"    Performance card found: {card.text[:50]}")
                try:
                    inner_links = card.find_elements(By.TAG_NAME, "a")
                    if inner_links:
                        href = inner_links[0].get_attribute("href")
                        print(f"    Card link: {href}")
                except: pass
                break
    except: pass


def test_05_leave_approve_reject_workflow():
    """Try the actual approve/reject workflow on leave requests."""
    print("\n=== TEST 05: Leave Approve/Reject Workflow ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/leave")
    time.sleep(3)
    body = page_text()
    shot = screenshot("05_leave_for_actions")

    # Check for pending count
    pending_match = None
    for line in body.split('\n'):
        if 'pending' in line.lower() and ('request' in line.lower() or '(' in line):
            pending_match = line.strip()
            break
    print(f"    Pending info: {pending_match}")

    # Look for clickable pending leave entries
    try:
        # Find rows in the pending leave requests table
        table_rows = driver.find_elements(By.CSS_SELECTOR,
            "table tbody tr")
        print(f"    Table rows: {len(table_rows)}")

        if table_rows:
            # Try clicking on the first pending entry
            first_row = table_rows[0]
            row_text = first_row.text.strip()
            print(f"    First row: {row_text[:100]}")

            # Check for action buttons in the row
            btns_in_row = first_row.find_elements(By.CSS_SELECTOR, "button, a, [role='button']")
            for btn in btns_in_row:
                btn_text = btn.text.strip()
                btn_title = btn.get_attribute("title") or ""
                btn_aria = btn.get_attribute("aria-label") or ""
                if btn_text or btn_title or btn_aria:
                    print(f"    Button: text='{btn_text}', title='{btn_title}', aria='{btn_aria}'")

            # Try clicking the row itself to open details
            try:
                first_row.click()
                time.sleep(2)
                new_body = page_text()
                shot2 = screenshot("05_leave_row_click")

                # Check if a detail/modal opened
                has_detail = any(kw in new_body.lower() for kw in [
                    "approve", "reject", "detail", "reason", "status"])
                record_result("Leave Row Click Opens Details", has_detail,
                              "Detail view opened" if has_detail else "No detail view")
            except:
                print("    Cannot click row")

    except Exception as e:
        print(f"    Error: {e}")

    # Check if there's a separate approval page linked from sidebar
    # From sidebar we know /leave links exist but check for approval-specific route
    safe_navigate(f"{BASE_URL}/leave")
    time.sleep(2)

    # Look for any approval-related navigation within the leave section
    try:
        all_links = driver.find_elements(By.CSS_SELECTOR, "a")
        approval_links = [l for l in all_links
                         if any(kw in (l.text or "").lower() for kw in ["approval", "pending", "approve"])]
        for link in approval_links:
            print(f"    Approval link: text='{link.text.strip()}', href='{link.get_attribute('href')}'")
    except: pass


def test_06_team_member_profile_from_manager():
    """Click a team member on /manager page to view their profile."""
    print("\n=== TEST 06: Team Member Profile from Manager Page ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/manager")
    time.sleep(3)
    body = page_text()
    shot = screenshot("06_manager_for_profiles")

    # Get list of team members shown
    lines = body.split('\n')
    in_attendance = False
    members = []
    for line in lines:
        if "team attendance" in line.lower():
            in_attendance = True
            continue
        if in_attendance and line.strip():
            # Check if it looks like a name (not a section header)
            stripped = line.strip()
            if len(stripped) > 2 and not any(kw in stripped.lower() for kw in
                ["team", "calendar", "pending", "leave", "section", "present", "absent",
                 "late", "half day", "on time", "total"]):
                members.append(stripped)
            if "pending" in stripped.lower() or "calendar" in stripped.lower():
                break

    print(f"    Team members found: {members[:10]}")

    # Try to click on a member name
    try:
        # Look for links with employee names
        all_links = driver.find_elements(By.CSS_SELECTOR, "a")
        member_links = []
        for link in all_links:
            text = link.text.strip()
            href = link.get_attribute("href") or ""
            if text and any(m.split()[0] in text for m in members if m.strip()):
                member_links.append(link)
            elif "employee" in href or "profile" in href:
                member_links.append(link)

        if member_links:
            print(f"    Clickable member links: {len(member_links)}")
            link = member_links[0]
            print(f"    Clicking: '{link.text.strip()}' -> {link.get_attribute('href')}")
            try:
                link.click()
                time.sleep(3)
                shot2 = screenshot("06_member_profile")
                profile_body = page_text()
                has_profile = any(kw in profile_body.lower() for kw in [
                    "profile", "details", "phone", "email", "department",
                    "designation", "joining", "employee"])
                record_result("Member Profile from Manager Page", has_profile,
                              f"Profile at {driver.current_url}")
            except Exception as e:
                record_result("Member Profile Click", False, f"Error: {e}")
        else:
            record_result("Clickable Member Links", False, "No clickable member names on manager page")
    except Exception as e:
        record_result("Member Profile Navigation", False, f"Error: {e}")


def test_07_dashboard_module_insights():
    """Check Module Insights section on dashboard for manager-relevant info."""
    print("\n=== TEST 07: Dashboard Module Insights ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/")
    time.sleep(3)
    shot = screenshot("07_dashboard_modules")
    body = page_text()

    # Extract Module Insights section
    lines = body.split('\n')
    in_insights = False
    insights = []
    for line in lines:
        if "module insight" in line.lower():
            in_insights = True
            continue
        if in_insights and line.strip():
            insights.append(line.strip())
            if len(insights) > 20:
                break

    print(f"    Module Insights:")
    for line in insights[:15]:
        print(f"      | {line}")

    # Check for key manager modules
    insights_text = " ".join(insights).lower()
    modules_present = {
        "Recruitment": "recruit" in insights_text,
        "Performance": "performance" in insights_text,
        "Recognition/Rewards": "recognition" in insights_text or "reward" in insights_text,
    }
    for mod, found in modules_present.items():
        record_result(f"Dashboard {mod} Insight", found,
                      "Present" if found else "Missing")


def test_08_events_team_meeting():
    """Try creating a team meeting event."""
    print("\n=== TEST 08: Create Team Meeting Event ===")
    restart_driver()

    safe_navigate(f"{BASE_URL}/events")
    time.sleep(3)
    body = page_text()

    # Click "Manage Events"
    try:
        manage_btn = driver.find_elements(By.XPATH,
            "//button[contains(text(),'Manage')] | //a[contains(text(),'Manage')]")
        if manage_btn:
            try:
                manage_btn[0].click()
                time.sleep(2)
                shot = screenshot("08_manage_events")
                body2 = page_text()

                # Look for create/add button in manage view
                create_btns = driver.find_elements(By.XPATH,
                    "//button[contains(text(),'Create')] | //button[contains(text(),'Add')] | "
                    "//button[contains(text(),'New')]")
                if create_btns:
                    print(f"    Create button: {create_btns[0].text}")
                    create_btns[0].click()
                    time.sleep(2)
                    shot2 = screenshot("08_create_event_form")
                    form_body = page_text()

                    # Check form fields
                    form_fields = {
                        "title": any(kw in form_body.lower() for kw in ["title", "name", "event name"]),
                        "date": any(kw in form_body.lower() for kw in ["date", "when"]),
                        "description": any(kw in form_body.lower() for kw in ["description", "details", "about"]),
                    }
                    record_result("Event Creation Form", all(form_fields.values()),
                                  f"Fields: {form_fields}")

                    # Check if can invite/select attendees
                    has_attendees = any(kw in form_body.lower() for kw in [
                        "attendee", "invite", "participant", "guest", "team member",
                        "employee", "select"])
                    record_result("Event Invite/Attendee Selection", has_attendees,
                                  "Can select attendees" if has_attendees else "No attendee selection")
                else:
                    record_result("Create Event Button in Manage", False, "No create button")
            except Exception as e:
                record_result("Manage Events Click", False, f"Error: {e}")
        else:
            record_result("Manage Events Button", False, "Not found")
    except Exception as e:
        print(f"    Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════

def main():
    global driver

    print("=" * 70)
    print("  RAVI KUMAR'S MANAGER DAY -- Pass 3 (Final Verification)")
    print(f"  Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        test_01_leave_dashboard_names()
        test_02_manager_page_scroll_and_actions()
        test_03_attendance_features()
        test_04_performance_sso_verification()
        test_05_leave_approve_reject_workflow()
        test_06_team_member_profile_from_manager()
        test_07_dashboard_module_insights()
        test_08_events_team_meeting()
    except Exception as e:
        print(f"\n[FATAL] {e}")
        traceback.print_exc()
    finally:
        if driver:
            try: driver.quit()
            except: pass

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  PASS 3 SUMMARY")
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

    results_path = Path(r"C:\emptesting\manager_ravi_pass3_results.json")
    with open(results_path, "w") as f:
        json.dump({
            "date": datetime.datetime.now().isoformat(),
            "user": EMAIL,
            "persona": "Ravi Kumar -- Pass 3",
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
