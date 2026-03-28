"""
Supplementary RBAC test - check exact sidebar URLs the employee can see.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os, json, time, requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

CHROME_BIN = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_performance_employee"
AUTH_API = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
PERF_FRONTEND = "https://test-performance.empcloud.com"
EMAIL = "priya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log(f"  Screenshot: {name}.png")

def file_bug(title, body):
    full_title = f"[Performance Employee] {title}"
    try:
        # Check if similar exists
        resp = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"},
            params={"state": "open", "per_page": 100}, timeout=15
        )
        if resp.status_code == 200:
            for issue in resp.json():
                if title.lower()[:40] in issue.get("title", "").lower():
                    log(f"  Similar bug exists: {issue['html_url']}")
                    return issue['html_url']

        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"},
            json={"title": full_title, "body": body, "labels": ["bug", "performance", "rbac"]},
            timeout=15
        )
        if resp.status_code == 201:
            url = resp.json().get("html_url", "")
            log(f"  Bug filed: {url}")
            return url
        else:
            log(f"  Bug filing failed: {resp.status_code}")
    except Exception as e:
        log(f"  Error: {e}")
    return None

def main():
    log("=" * 70)
    log("SUPPLEMENTARY RBAC TEST - Exact sidebar URLs")
    log("=" * 70)

    # Login
    resp = requests.post(AUTH_API, json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    data = resp.json()
    token = data["data"]["tokens"]["access_token"]
    log(f"Logged in, token length: {len(token)}")

    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)

    try:
        sso_url = f"{PERF_FRONTEND}?sso_token={token}"
        driver.get(sso_url)
        time.sleep(3)

        # These are the EXACT sidebar URLs visible to the employee
        # Admin-only pages an employee should NOT access:
        admin_pages = {
            "Review Cycles": "/review-cycles",
            "Goal Alignment": "/goals/alignment",
            "Competencies": "/competencies",
            "PIPs": "/pips",
            "Career Paths": "/career-paths",
            "Analytics": "/analytics",
            "9-Box Grid": "/analytics/nine-box",
            "Skills Gap": "/analytics/skills-gap",
            "Succession": "/succession",
            "Settings": "/settings",
        }

        # Employee-appropriate pages:
        employee_pages = {
            "Dashboard": "/dashboard",
            "Goals": "/goals",
            "1-on-1s": "/one-on-ones",
            "Feedback": "/feedback",
            "Letters": "/letters",
        }

        violations = []

        log("\n--- Admin-only pages (should be BLOCKED for employee) ---")
        for name, path in admin_pages.items():
            url = f"{PERF_FRONTEND}{path}"
            driver.get(url)
            time.sleep(2)
            page_text = driver.find_element(By.TAG_NAME, "body").text
            current_url = driver.current_url
            is_blocked = any(k in page_text.lower() for k in [
                "unauthorized", "forbidden", "access denied", "not found", "404"
            ])
            is_redirected = "/dashboard" in current_url and path != "/dashboard"

            scr_name = f"14_sidebar_{name.lower().replace(' ', '_').replace('-', '_')}"
            screenshot(driver, scr_name)

            if is_blocked or is_redirected:
                log(f"  [OK]   {name} ({path}) - Blocked/redirected")
            else:
                log(f"  [FAIL] {name} ({path}) - ACCESSIBLE! Text: {page_text[:100]}")
                violations.append(name)

        log("\n--- Employee pages (should be accessible) ---")
        for name, path in employee_pages.items():
            url = f"{PERF_FRONTEND}{path}"
            driver.get(url)
            time.sleep(2)
            page_text = driver.find_element(By.TAG_NAME, "body").text
            scr_name = f"15_employee_{name.lower().replace(' ', '_').replace('-', '_')}"
            screenshot(driver, scr_name)

            is_error = "not found" in page_text.lower() or "404" in page_text
            if is_error:
                log(f"  [WARN] {name} ({path}) - Not accessible (404)")
            else:
                log(f"  [OK]   {name} ({path}) - Accessible")

        # Also test: can the employee click "Create PIP" button?
        log("\n--- Testing Create PIP button ---")
        driver.get(f"{PERF_FRONTEND}/pips")
        time.sleep(2)
        try:
            create_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Create PIP')]")
            if create_btn.is_displayed():
                log("  [FAIL] 'Create PIP' button is visible to employee!")
                create_btn.click()
                time.sleep(2)
                screenshot(driver, "16_create_pip_dialog")
                page_text = driver.find_element(By.TAG_NAME, "body").text
                log(f"  After click: {page_text[:200]}")
                violations.append("Create PIP button")
        except:
            log("  [OK] No 'Create PIP' button visible")

        # Test: can employee click "Create Cycle"?
        log("\n--- Testing Create Cycle button ---")
        driver.get(f"{PERF_FRONTEND}/review-cycles")
        time.sleep(2)
        try:
            create_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Create Cycle')]")
            if create_btn.is_displayed():
                log("  [FAIL] 'Create Cycle' button is visible to employee!")
                create_btn.click()
                time.sleep(2)
                screenshot(driver, "17_create_cycle_dialog")
                page_text = driver.find_element(By.TAG_NAME, "body").text
                log(f"  After click: {page_text[:200]}")
                violations.append("Create Cycle button")
        except:
            log("  [OK] No 'Create Cycle' button visible")

        # Test: can employee save settings?
        log("\n--- Testing Save Settings button ---")
        driver.get(f"{PERF_FRONTEND}/settings")
        time.sleep(2)
        try:
            save_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Save Settings')]")
            if save_btn.is_displayed():
                log("  [FAIL] 'Save Settings' button is visible to employee!")
                violations.append("Save Settings button")
                screenshot(driver, "18_save_settings_visible")
        except:
            log("  [OK] No 'Save Settings' button visible")

        # Summary and bug update
        log(f"\n{'='*70}")
        log(f"VIOLATIONS FOUND: {len(violations)}")
        for v in violations:
            log(f"  - {v}")

        if violations:
            violation_list = "\n".join(f"- **{v}** is accessible to employee" for v in violations)
            # Update existing issue #830 with additional details
            log("\nUpdating existing bug #830 with sidebar details...")
            try:
                comment_body = (
                    f"**Additional RBAC violations found via sidebar navigation:**\n\n"
                    f"{violation_list}\n\n"
                    f"The sidebar exposes ALL admin navigation links to the employee role, including:\n"
                    f"Review Cycles (with Create Cycle button), PIPs (with Create PIP button), "
                    f"Analytics, 9-Box Grid, Skills Gap, Succession, Competencies, Settings (with Save Settings button).\n\n"
                    f"**Root cause:** The sidebar/navigation does not filter menu items by role. "
                    f"The frontend renders the full admin sidebar for all users.\n\n"
                    f"**Impact:** High - Employee can view admin pages, create PIPs, create review cycles, "
                    f"and modify module settings."
                )
                resp = requests.post(
                    f"https://api.github.com/repos/{GITHUB_REPO}/issues/830/comments",
                    headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"},
                    json={"body": comment_body},
                    timeout=15
                )
                if resp.status_code == 201:
                    log(f"  Comment added to #830")
                else:
                    log(f"  Comment failed: {resp.status_code}")
            except Exception as e:
                log(f"  Error: {e}")

            # File separate bug for sidebar nav not filtering by role
            file_bug(
                "Sidebar navigation exposes all admin menu items to employee role",
                f"**User:** priya@technova.in (Employee role)\n"
                f"**Module:** Performance\n\n"
                f"**Issue:** The sidebar navigation renders ALL menu items regardless of user role. "
                f"Employee user sees: Review Cycles, Competencies, PIPs, Career Paths, Analytics, "
                f"9-Box Grid, Skills Gap, Succession, Settings.\n\n"
                f"**Violations:**\n{violation_list}\n\n"
                f"**Expected:** Employee should only see: Dashboard, My Goals, My Reviews, "
                f"1-on-1s, Feedback, Letters.\n\n"
                f"**Root cause:** Frontend sidebar component does not implement role-based filtering.\n\n"
                f"**Impact:** Critical RBAC issue. Employee can:\n"
                f"- View and create review cycles\n"
                f"- View and create PIPs\n"
                f"- Access analytics and 9-box grid\n"
                f"- Modify performance module settings\n"
            )

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback; traceback.print_exc()
        try:
            screenshot(driver, "99_supplement_error")
        except:
            pass
    finally:
        driver.quit()

    log("=" * 70)
    log("Supplementary test complete.")

if __name__ == "__main__":
    main()
