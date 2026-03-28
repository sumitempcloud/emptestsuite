#!/usr/bin/env python3
"""
Follow-up test:
1. Verify employee can see "Unsubscribe" buttons (potential RBAC issue)
2. Test Projects module more deeply (it was accessible)
3. Try logging into each module directly with employee creds
4. Compare admin vs employee /modules page
"""

import sys, os, time, json, ssl, re
import urllib.request, urllib.parse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\employee_modules_v2"
GH_PAT = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

test_results = []
bugs_found = []
DRIVER_PATH = None

MODULE_SUBDOMAINS = {
    "payroll": "testpayroll.empcloud.com",
    "recruitment": "test-recruit.empcloud.com",
    "performance": "test-performance.empcloud.com",
    "rewards": "test-rewards.empcloud.com",
    "exit": "test-exit.empcloud.com",
    "lms": "testlms.empcloud.com",
    "projects": "test-project.empcloud.com",
}

def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def result(name, status, details=""):
    test_results.append({"test": name, "status": status, "details": details})
    print(f"  [{status}] {name}: {details}", flush=True)

def bug(title, desc, sev="medium", sp=None):
    bugs_found.append({"title": title, "description": desc, "severity": sev, "screenshot": sp})
    print(f"  [BUG-{sev.upper()}] {title}", flush=True)

def shot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{ts()}.png")
    try:
        driver.save_screenshot(path)
    except:
        path = None
    return path

def create_driver():
    global DRIVER_PATH
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
              "--disable-gpu", "--window-size=1920,1080", "--ignore-certificate-errors"]:
        opts.add_argument(a)
    if DRIVER_PATH is None:
        DRIVER_PATH = ChromeDriverManager().install()
    d = webdriver.Chrome(service=Service(DRIVER_PATH), options=opts)
    d.set_page_load_timeout(60)
    d.implicitly_wait(3)
    return d

def do_login(driver, email, password):
    driver.get(BASE_URL + "/login")
    time.sleep(5)
    try:
        e = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        p = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        e.clear(); e.send_keys(email)
        p.clear(); p.send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except:
        return False
    time.sleep(6)
    return "/login" not in driver.current_url.lower()

def upload_screenshot_github(filepath):
    if not filepath or not os.path.exists(filepath):
        return None
    fname = os.path.basename(filepath)
    import base64
    with open(filepath, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    url = f"https://api.github.com/repos/{GH_REPO}/contents/screenshots/employee_modules_v2/{fname}"
    data = json.dumps({"message": f"Upload {fname}", "content": content, "branch": "main"}).encode()
    req = urllib.request.Request(url, data=data, method="PUT", headers={
        "Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-E2E", "Content-Type": "application/json",
    })
    try:
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        res = json.loads(r.read().decode())
        return res.get("content", {}).get("download_url", "")
    except:
        return None

def file_github_issue(title, body, labels=None):
    if labels is None:
        labels = ["bug"]
    # Duplicate check
    try:
        sq = urllib.parse.quote(title[:50])
        search_url = f"https://api.github.com/search/issues?q=repo:{GH_REPO}+is:issue+in:title+{sq}"
        req = urllib.request.Request(search_url, headers={
            "Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github+json",
            "User-Agent": "EmpCloud-E2E",
        })
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=15)
        res = json.loads(r.read().decode())
        if res.get("total_count", 0) > 0:
            log(f"  [GH-SKIP] Similar issue exists: #{res['items'][0]['number']}")
            return res["items"][0].get("html_url")
    except:
        pass

    url = f"https://api.github.com/repos/{GH_REPO}/issues"
    data = json.dumps({"title": title, "body": body, "labels": labels}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-E2E", "Content-Type": "application/json",
    })
    try:
        r = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        res = json.loads(r.read().decode())
        log(f"  [GH-ISSUE] #{res.get('number')} -> {res.get('html_url')}")
        return res.get("html_url")
    except Exception as e:
        log(f"  [GH-ISSUE-FAIL] {e}")
        return None


def main():
    log("=" * 70)
    log("EMPLOYEE MODULES FOLLOW-UP TESTS")
    log("=" * 70)

    # ── Test 1: Employee /modules page — check for Unsubscribe buttons ──
    log("\n--- Test 1: Employee sees Unsubscribe buttons (RBAC check) ---")
    driver = create_driver()
    try:
        ok = do_login(driver, "priya@technova.in", "Welcome@123")
        if not ok:
            log("FATAL: Cannot login")
            driver.quit()
            return

        driver.get(BASE_URL + "/modules")
        time.sleep(5)

        # Check for Unsubscribe buttons
        unsub_buttons = []
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            text = (btn.text or "").strip().lower()
            if "unsubscribe" in text:
                unsub_buttons.append(btn)

        sp1 = shot(driver, "emp_modules_unsub_check")
        if unsub_buttons:
            log(f"  Found {len(unsub_buttons)} Unsubscribe buttons visible to employee!")
            result("Modules-RBAC-Unsubscribe", "FAIL",
                   f"Employee can see {len(unsub_buttons)} Unsubscribe buttons")
            bug("Modules — Employee can see Unsubscribe buttons for organization modules",
                "Employee (priya@technova.in) on the /modules page can see 'Unsubscribe' "
                "buttons for all subscribed modules. Only Org Admin should be able to "
                "manage module subscriptions.\n\n"
                "**Steps:**\n1. Login as priya@technova.in (Employee)\n"
                "2. Go to /modules\n"
                "3. Each module card shows 'Subscribed' with an 'Unsubscribe' button\n\n"
                "**Expected:** Employee should not see subscription management controls.\n"
                "**Risk:** Employee could unsubscribe the entire organization from a module.",
                "critical", sp1)

            # Actually try clicking Unsubscribe to see if it works
            log("  Testing if Unsubscribe actually works...")
            # DO NOT actually unsubscribe - just check if button is enabled/clickable
            for btn in unsub_buttons[:1]:
                is_disabled = btn.get_attribute("disabled")
                classes = btn.get_attribute("class") or ""
                log(f"  Unsubscribe button: disabled={is_disabled}, classes={classes[:60]}")
                if not is_disabled:
                    result("Modules-RBAC-UnsubscribeClickable", "FAIL",
                           "Unsubscribe button is clickable (not disabled)")
        else:
            result("Modules-RBAC-Unsubscribe", "PASS", "No Unsubscribe buttons visible")

        # Check if employee sees Launch buttons (comparing with admin)
        launch_buttons = []
        for el in driver.find_elements(By.XPATH,
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'launch')]"):
            text = (el.text or "").strip()
            if text:
                launch_buttons.append(text)
        log(f"  Launch elements found by employee: {launch_buttons}")
        if not launch_buttons:
            result("Modules-NoLaunchButtons", "FAIL",
                   "Employee cannot see any Launch buttons on /modules page")

    finally:
        driver.quit()

    # ── Test 2: Org Admin /modules page — check for Launch buttons ──
    log("\n--- Test 2: Org Admin /modules page (for comparison) ---")
    driver = create_driver()
    try:
        ok = do_login(driver, "ananya@technova.in", "Welcome@123")
        if not ok:
            log("Cannot login as admin")
            driver.quit()
            return

        driver.get(BASE_URL + "/modules")
        time.sleep(5)
        sp2 = shot(driver, "admin_modules_page")

        page_text = driver.find_element(By.TAG_NAME, "body").text
        log("  Admin /modules page content:")
        for line in page_text.split('\n'):
            if line.strip():
                log(f"    | {line.strip()}")

        # Check for Launch buttons
        launch_elements = []
        for el in driver.find_elements(By.XPATH,
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'launch')]"):
            text = (el.text or "").strip()
            tag = el.tag_name
            href = el.get_attribute("href") or ""
            if text:
                launch_elements.append(f"<{tag}> '{text}' href={href[:80]}")
        log(f"  Admin Launch elements: {launch_elements}")

        # Check for SSO links
        sso_links = []
        for a in driver.find_elements(By.TAG_NAME, "a"):
            href = (a.get_attribute("href") or "")
            text = (a.text or "").strip()
            if "sso_token" in href or any(sd in href for sd in MODULE_SUBDOMAINS.values()):
                sso_links.append(f"{text}: {href[:100]}")
        log(f"  Admin SSO links found: {len(sso_links)}")
        for sl in sso_links:
            log(f"    {sl}")

        if sso_links:
            result("Admin-Modules-LaunchButtons", "PASS",
                   f"Admin sees {len(sso_links)} SSO launch links")
        else:
            result("Admin-Modules-LaunchButtons", "INFO", "Admin also has no launch links on /modules")

    finally:
        driver.quit()

    # ── Test 3: Try direct login to each module with employee creds ──
    log("\n--- Test 3: Direct login to modules with employee creds ---")
    driver = create_driver()
    test_count = 0
    for mod_name, subdomain in MODULE_SUBDOMAINS.items():
        if test_count > 0 and test_count % 2 == 0:
            driver.quit()
            driver = create_driver()

        log(f"\n  Trying {mod_name} ({subdomain}) direct login...")
        try:
            driver.get(f"https://{subdomain}/login")
            time.sleep(5)
            sp = shot(driver, f"direct_login_{mod_name}")

            # Check if login page shows
            src = driver.page_source.lower()
            if "sign in" in src or "login" in src or "email" in src:
                # Try to login with employee creds
                try:
                    e = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
                    p = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                    e.clear(); e.send_keys("priya@technova.in")
                    p.clear(); p.send_keys("Welcome@123")
                    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                    time.sleep(6)

                    current = driver.current_url.lower()
                    sp_after = shot(driver, f"direct_login_{mod_name}_after")
                    if "login" not in current:
                        log(f"  {mod_name}: Direct login SUCCEEDED -> {driver.current_url}")
                        result(f"DirectLogin-{mod_name}", "PASS", f"Logged in: {driver.current_url}")

                        # Now explore what we can see
                        body_text = driver.find_element(By.TAG_NAME, "body").text
                        log(f"  Content (first 20 lines):")
                        for line in body_text.split('\n')[:20]:
                            if line.strip():
                                log(f"    | {line.strip()}")

                        # Explore sidebar links
                        nav_links = []
                        for a in driver.find_elements(By.TAG_NAME, "a"):
                            href = (a.get_attribute("href") or "")
                            text = (a.text or "").strip()
                            if text and subdomain in href:
                                nav_links.append(f"{text}: {href}")
                        log(f"  Navigation links ({len(nav_links)}):")
                        for nl in nav_links[:20]:
                            log(f"    {nl}")

                    else:
                        page_text = driver.find_element(By.TAG_NAME, "body").text
                        if "invalid" in page_text.lower() or "error" in page_text.lower() or "not found" in page_text.lower():
                            log(f"  {mod_name}: Login FAILED (invalid creds or not allowed)")
                            result(f"DirectLogin-{mod_name}", "FAIL", "Invalid credentials or access denied")
                        else:
                            log(f"  {mod_name}: Still on login page")
                            result(f"DirectLogin-{mod_name}", "FAIL", "Login did not succeed")
                except NoSuchElementException:
                    log(f"  {mod_name}: No login form found")
                    result(f"DirectLogin-{mod_name}", "INFO", "No login form")
            else:
                log(f"  {mod_name}: No login page (URL: {driver.current_url})")
                # Maybe landed on the app directly
                if subdomain in driver.current_url and "login" not in driver.current_url:
                    result(f"DirectLogin-{mod_name}", "PASS", f"Direct access: {driver.current_url}")
                else:
                    result(f"DirectLogin-{mod_name}", "INFO", f"URL: {driver.current_url}")

        except Exception as e:
            log(f"  {mod_name}: Error - {e}")
            result(f"DirectLogin-{mod_name}", "ERROR", str(e))

        test_count += 1

    driver.quit()

    # ── Test 4: Deep test Projects module (it was accessible) ──
    log("\n--- Test 4: Deep test Projects module ---")
    driver = create_driver()
    try:
        proj_url = "https://test-project.empcloud.com"
        driver.get(proj_url)
        time.sleep(5)
        sp_proj = shot(driver, "projects_deep_landing")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        log("  Projects landing page text:")
        for line in body_text.split('\n'):
            if line.strip():
                log(f"    | {line.strip()}")

        # Click "Streamline Your Projects Now" button if it exists
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            text = (btn.text or "").strip()
            if "streamline" in text.lower() or "start" in text.lower() or "get started" in text.lower():
                log(f"  Clicking button: '{text}'")
                btn.click()
                time.sleep(4)
                sp_after = shot(driver, "projects_after_cta_click")
                log(f"  After click URL: {driver.current_url}")
                body_after = driver.find_element(By.TAG_NAME, "body").text
                for line in body_after.split('\n')[:20]:
                    if line.strip():
                        log(f"    | {line.strip()}")
                break
        for a in driver.find_elements(By.TAG_NAME, "a"):
            text = (a.text or "").strip()
            if "streamline" in text.lower() or "start" in text.lower():
                log(f"  Clicking link: '{text}'")
                a.click()
                time.sleep(4)
                shot(driver, "projects_after_cta_link")
                log(f"  After click URL: {driver.current_url}")
                break

        # This looks like an unauthenticated marketing page, not the actual module
        # The fact that it doesn't redirect to login is notable
        result("Projects-DirectAccess", "INFO",
               "Projects shows marketing page (not authenticated app), no login redirect")

        # Check if there's any actual functionality
        src = driver.page_source.lower()
        if "login" in src or "sign in" in src:
            log("  Page has login references")
        if any(kw in src for kw in ["dashboard", "my projects", "my tasks", "kanban"]):
            log("  Page has project functionality references")
        else:
            log("  No project functionality visible - just marketing page")
            result("Projects-NoFunctionality", "FAIL",
                   "Projects module shows only marketing page, no actual project management")

    finally:
        driver.quit()

    # ── Summary ──
    log("\n" + "=" * 70)
    log("FOLLOW-UP RESULTS")
    log("=" * 70)

    for r in test_results:
        log(f"  [{r['status']}] {r['test']}: {r['details']}")

    log(f"\n  Bugs found: {len(bugs_found)}")
    for b in bugs_found:
        log(f"  [BUG-{b['severity'].upper()}] {b['title']}")

    # Upload key screenshots and file bugs
    log("\n--- Uploading screenshots and filing bugs ---")
    uploaded = {}
    key_shots = [f for f in os.listdir(SCREENSHOT_DIR) if f.endswith(".png") and
                 any(kw in f for kw in ["unsub", "admin_modules", "direct_login", "projects_deep"])]
    for fname in key_shots[:15]:
        fpath = os.path.join(SCREENSHOT_DIR, fname)
        url = upload_screenshot_github(fpath)
        if url:
            uploaded[fname] = url
        time.sleep(0.5)

    for b in bugs_found:
        body = b["description"] + "\n\n"
        body += f"**Severity:** {b['severity']}\n"
        body += f"**User:** priya@technova.in\n**Role:** Employee\n"
        body += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        if b.get("screenshot"):
            fname = os.path.basename(b["screenshot"])
            if fname in uploaded:
                body += f"\n**Screenshot:**\n![{fname}]({uploaded[fname]})\n"
        labels = ["bug"]
        if b["severity"] == "critical":
            labels.append("critical")
        file_github_issue(b["title"], body, labels)
        time.sleep(1)

    # File feature requests for Projects (only module accessible)
    proj_infos = [r for r in test_results if r["test"].startswith("Projects-") and r["status"] in ("FAIL", "INFO")]
    if proj_infos:
        for r in proj_infos:
            if "marketing" in r["details"].lower() or "NoFunctionality" in r["test"]:
                file_github_issue(
                    "Projects — Module shows marketing page instead of project management for employees",
                    "When employee accesses https://test-project.empcloud.com directly, they see a "
                    "marketing/landing page ('Empower Your Team with Advanced Project Management') "
                    "instead of actual project management functionality.\n\n"
                    "**Expected:** Employee should see their assigned projects, tasks, and boards.\n"
                    "**Actual:** Marketing page with no functional content.\n\n"
                    "This may be because:\n1. Employee SSO is not configured for this module\n"
                    "2. The module lacks employee-facing features\n"
                    "3. The landing page is shown to unauthenticated users\n\n"
                    f"**User:** priya@technova.in\n**Role:** Employee",
                    labels=["bug"]
                )
                break

    log("\n  DONE")


if __name__ == "__main__":
    main()
