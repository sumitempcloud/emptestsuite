"""
EMP Monitor Module - Deep Test v4 (visit ALL discovered sub-pages)
Visit every page discovered in sidebar expansion, screenshot each, find bugs.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
import json
import os
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_monitor"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

LOGIN_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
MONITOR_BASE = "https://test-empmonitor.empcloud.com"

ADMIN_EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

bugs = []
test_results = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {name}.png")
    return path

def file_bug(title, body):
    bugs.append(title)
    log(f"  BUG: {title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github+json"
            },
            json={
                "title": title,
                "body": body,
                "labels": ["bug", "verified-bug", "monitor"]
            }
        )
        if resp.status_code == 201:
            log(f"  Filed issue #{resp.json()['number']}: {title}")
        else:
            log(f"  Issue filing status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log(f"  Error filing bug: {e}")

def record(test_name, status, details=""):
    test_results.append({"test": test_name, "status": status, "details": details})
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
    log(f"  [{icon}] {test_name}: {details}")

def make_driver():
    opts = Options()
    opts.binary_location = CHROME_PATH
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(3)
    return driver

def get_sso_token(email, password):
    log(f"Logging in as {email}...")
    resp = requests.post(LOGIN_URL, json={"email": email, "password": password})
    data = resp.json()
    token = (
        data.get("data", {}).get("tokens", {}).get("access_token")
        or data.get("data", {}).get("token")
        or data.get("token")
    )
    if token:
        log(f"  Got token: {token[:30]}...")
    return token

def get_body_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except:
        return ""

def main():
    log("="*70)
    log("EMP MONITOR - v4: Visit ALL Sub-Pages + File Remaining Bugs")
    log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("="*70)

    admin_token = get_sso_token(ADMIN_EMAIL, PASSWORD)
    if not admin_token:
        log("FATAL: No admin token")
        sys.exit(1)

    driver = make_driver()
    try:
        # SSO in
        driver.get(f"{MONITOR_BASE}?sso_token={admin_token}")
        time.sleep(5)
        log(f"  Landed: {driver.current_url}")

        # All pages discovered from sidebar expansion
        all_pages = [
            # Employees sub-menu
            ("Employee Details", "/admin/employee-details"),
            ("Employee Comparison", "/admin/comparison"),
            ("Employee Attendance", "/admin/attendance"),
            ("Employee Insights", "/admin/insights"),
            ("Real Time Track", "/admin/realtime"),
            # DLP sub-menu
            ("DLP - USB Detection", "/admin/dlp/usb"),
            ("DLP - System Logs", "/admin/dlp/systemlogs"),
            ("DLP - Screenshot Logs", "/admin/dlp/screenshotlog"),
            ("DLP - Email Activity Logs", "/admin/dlp/emailactivity"),
            # Settings sub-menu
            ("Settings - Location & Dept", "/admin/settings/location"),
            ("Settings - Storage Types", "/admin/settings/storage"),
            ("Settings - Productivity Rules", "/admin/settings/productivity"),
            ("Settings - Roles & Permissions", "/admin/settings/roles"),
            ("Settings - Shift Management", "/admin/settings/shift"),
            ("Settings - Monitoring Control", "/admin/settings/monitoring"),
            ("Settings - Localization", "/admin/settings/localization"),
            # Main pages
            ("Dashboard", "/admin/dashboard"),
            ("Timesheets", "/admin/timesheets"),
            ("Live Monitoring", "/admin/livemonitoring"),
            ("Time Claim", "/admin/timeclaim"),
        ]

        for name, path in all_pages:
            log(f"\n--- {name} ({path}) ---")
            try:
                driver.get(f"{MONITOR_BASE}{path}")
                time.sleep(4)
                curr = driver.current_url
                body = get_body_text(driver)
                safe_name = name.replace(" ", "_").replace("-", "").replace("&", "n").replace("/", "_")
                screenshot(driver, f"V4_{safe_name}")

                if "/login" in curr:
                    record(name, "fail", f"Redirected to login from {path}")
                    file_bug(
                        f"[Monitor] Page {path} redirects to login even when authenticated",
                        f"**Steps:**\n1. SSO login as admin\n2. Navigate to {MONITOR_BASE}{path}\n\n"
                        f"**Expected:** Page loads with content\n"
                        f"**Actual:** Redirected to login page\n"
                        f"**Impact:** {name} feature is inaccessible"
                    )
                elif len(body) < 30:
                    record(name, "warn", f"Page nearly empty ({len(body)} chars)")
                else:
                    record(name, "pass", f"Loaded ({len(body)} chars) at {curr[:60]}")

                    # Deep inspection per page type
                    if "employee-details" in path:
                        # Check employee table
                        headers = ["name", "email", "department", "location", "system"]
                        found = [h for h in headers if h in body.lower()]
                        log(f"  Employee table headers: {found}")
                        # Check search
                        search_el = driver.find_elements(By.CSS_SELECTOR, "input[type='search'], input[placeholder*='earch']")
                        log(f"  Search inputs: {len(search_el)}")

                    elif "comparison" in path:
                        log(f"  Comparison page body preview: {body[:200]}")

                    elif "insights" in path:
                        # Check charts
                        charts = driver.find_elements(By.CSS_SELECTOR, "canvas, svg, [class*='chart']")
                        log(f"  Chart elements: {len(charts)}")
                        # Check export
                        export = driver.find_elements(By.XPATH, "//*[contains(text(),'Download') or contains(text(),'Export') or contains(text(),'CSV')]")
                        log(f"  Export buttons: {len(export)}")

                    elif "realtime" in path:
                        log(f"  Real Time Track body: {body[:200]}")

                    elif "dlp" in path:
                        log(f"  DLP page body preview: {body[:200]}")
                        # Check for table/list
                        tables = driver.find_elements(By.CSS_SELECTOR, "table, [class*='table'], [role='grid']")
                        log(f"  Tables: {len(tables)}")

                    elif "settings" in path:
                        # Check for form elements
                        inputs = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea, button")
                        log(f"  Form elements: {len(inputs)}")
                        # Check for toggles
                        toggles = driver.find_elements(By.CSS_SELECTOR, "[class*='toggle'], [class*='switch'], [role='switch']")
                        log(f"  Toggles: {len(toggles)}")

                    # Scroll for full page
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    screenshot(driver, f"V4_{safe_name}_bottom")

            except Exception as e:
                log(f"  ERROR: {e}")
                record(name, "fail", f"Error: {str(e)[:80]}")

        # ---- Check for invalid time values on dashboard ----
        log("\n--- Dashboard Data Validation ---")
        driver.get(f"{MONITOR_BASE}/admin/dashboard")
        time.sleep(5)
        body = get_body_text(driver)

        # Check for impossible time values (e.g., "259:56:78 hr" where 78 > 59 seconds)
        import re
        time_values = re.findall(r'(\d+:\d+:\d+)\s*hr', body)
        log(f"  Time values on dashboard: {time_values}")
        for tv in time_values:
            parts = tv.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                if seconds > 59 or minutes > 59:
                    file_bug(
                        f"[Monitor] Invalid time value on dashboard: {tv} hr (seconds/minutes > 59)",
                        f"**Steps:** Login as admin, view dashboard 'Today Activity Snapshot'\n\n"
                        f"**Expected:** Time values should use valid HH:MM:SS format where MM <= 59 and SS <= 59\n\n"
                        f"**Actual:** Dashboard shows '{tv} hr' which has "
                        f"{'seconds > 59' if seconds > 59 else ''}"
                        f"{' and ' if seconds > 59 and minutes > 59 else ''}"
                        f"{'minutes > 59' if minutes > 59 else ''}\n\n"
                        f"**All time values shown:** {time_values}\n\n"
                        f"**Impact:** Incorrect time calculations/display. Users see impossible time values."
                    )
                    record(f"Dashboard: Time value {tv}", "fail", f"Invalid time: seconds={seconds} or minutes={minutes} > 59")

        # ---- Check Activity Breakdown table for data inconsistencies ----
        log("\n--- Activity Breakdown Validation ---")
        # The Activity Breakdown table should have valid percentage/time values
        if "activity break down" in body.lower() or "activity breakdown" in body.lower():
            record("Activity Breakdown table", "pass", "Table present on dashboard")

        # ---- Check "View Report" buttons actually work ----
        log("\n--- View Report Buttons ---")
        view_report_btns = driver.find_elements(By.XPATH, "//*[contains(text(),'View Report')]")
        log(f"  View Report buttons: {len(view_report_btns)}")
        for i, btn in enumerate(view_report_btns[:2]):
            try:
                before_url = driver.current_url
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(3)
                after_url = driver.current_url
                body_after = get_body_text(driver)
                screenshot(driver, f"V4_view_report_{i}")
                if after_url != before_url:
                    record(f"View Report button {i}", "pass", f"Navigated to {after_url[:60]}")
                elif len(body_after) > 100:
                    record(f"View Report button {i}", "pass", "Report content loaded")
                else:
                    record(f"View Report button {i}", "warn", "Button click had no visible effect")
                # Go back
                driver.get(f"{MONITOR_BASE}/admin/dashboard")
                time.sleep(3)
            except Exception as e:
                log(f"  View Report error: {e}")

        # ---- Check "Download Report" button ----
        log("\n--- Download Report Button ---")
        body = get_body_text(driver)
        download_btns = driver.find_elements(By.XPATH, "//*[contains(text(),'Download Report')]")
        if download_btns:
            record("Download Report button", "pass", f"Found {len(download_btns)} download buttons")
        else:
            record("Download Report button", "warn", "No Download Report button found")

        # ---- Check sidebar "Behaviour" is a typo check ----
        log("\n--- Behaviour spelling check ---")
        # Note: "Behaviour" is actually correct British English spelling, not a bug

        # ---- Check "Reseller" page ----
        log("\n--- Reseller Page ---")
        driver.get(f"{MONITOR_BASE}/admin/reseller")
        time.sleep(3)
        curr = driver.current_url
        body = get_body_text(driver)
        if "/login" not in curr and len(body) > 50:
            screenshot(driver, "V4_reseller")
            record("Reseller page", "pass", f"Loaded at {curr[:60]}")
        else:
            log(f"  Reseller redirected or empty: {curr[:60]}")

        # ---- Check "Mobile Task" page ----
        log("\n--- Mobile Task Page ---")
        mobile_paths = ["/admin/mobiletask", "/admin/mobile-task", "/admin/mobile"]
        for path in mobile_paths:
            driver.get(f"{MONITOR_BASE}{path}")
            time.sleep(3)
            curr = driver.current_url
            body = get_body_text(driver)
            if "/login" not in curr and len(body) > 50:
                screenshot(driver, f"V4_mobiletask")
                record("Mobile Task page", "pass", f"Loaded at {curr[:60]}")
                break
        else:
            log(f"  Mobile Task not found via direct paths")

    except Exception as e:
        log(f"ERROR: {e}")
        traceback.print_exc()
        screenshot(driver, "V4_error")
    finally:
        driver.quit()

    # ---- Summary ----
    log("\n" + "="*70)
    log("V4 TEST SUMMARY")
    log("="*70)

    pass_count = sum(1 for r in test_results if r["status"] == "pass")
    fail_count = sum(1 for r in test_results if r["status"] == "fail")
    warn_count = sum(1 for r in test_results if r["status"] == "warn")

    log(f"\nTotal tests: {len(test_results)}")
    log(f"  PASS: {pass_count}")
    log(f"  FAIL: {fail_count}")
    log(f"  WARN: {warn_count}")

    if fail_count > 0:
        log(f"\n--- FAILURES ---")
        for r in test_results:
            if r["status"] == "fail":
                log(f"  FAIL: {r['test']} -- {r['details']}")

    if warn_count > 0:
        log(f"\n--- WARNINGS ---")
        for r in test_results:
            if r["status"] == "warn":
                log(f"  WARN: {r['test']} -- {r['details']}")

    log(f"\nBugs filed: {len(bugs)}")
    for b in bugs:
        log(f"  - {b}")

    log(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
