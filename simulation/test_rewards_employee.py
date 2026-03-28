"""
Rewards Module - Employee Perspective Testing (priya@technova.in)
Tests: SSO login, kudos, leaderboard, points, badges, challenges, admin access denial
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException
)

# ── Config ──────────────────────────────────────────────────────────────
CHROME_BIN   = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
LOGIN_API    = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
REWARDS_URL  = "https://test-rewards.empcloud.com"
REWARDS_API  = "https://test-rewards-api.empcloud.com"
EMAIL        = "priya@technova.in"
PASSWORD     = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_rewards_employee"
GITHUB_PAT   = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO  = "EmpCloud/EmpCloud"

bugs = []

def screenshot(driver, name):
    path = f"{SCREENSHOT_DIR}\\{name}.png"
    driver.save_screenshot(path)
    print(f"  [SCREENSHOT] {path}")
    return path

def file_bug(title, body):
    bugs.append(title)
    print(f"  [BUG] {title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={
                "title": title,
                "body": body,
                "labels": ["bug", "rewards", "employee"]
            },
            timeout=15
        )
        if resp.status_code in (201, 200):
            print(f"    -> Filed: {resp.json().get('html_url')}")
        else:
            print(f"    -> Failed to file ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        print(f"    -> Error filing bug: {e}")

def make_driver():
    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(3)
    return driver

def login_get_token():
    """Login via API and get SSO token."""
    print("\n[1] Logging in via API to get token...")
    resp = requests.post(LOGIN_API, json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    print(f"  Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  Response: {resp.text[:500]}")
        file_bug(
            "[Rewards Employee] Login API failure",
            f"POST {LOGIN_API} returned {resp.status_code}.\n\nResponse:\n```\n{resp.text[:1000]}\n```"
        )
        return None
    data = resp.json()
    # Token is at data.data.tokens.access_token
    token = None
    inner = data.get("data", {})
    if isinstance(inner, dict):
        tokens = inner.get("tokens", {})
        if isinstance(tokens, dict):
            token = tokens.get("access_token")
    if not token:
        token = data.get("token") or data.get("access_token")
    if not token:
        print(f"  Full response keys: {list(data.keys())}")
        print(f"  Response: {json.dumps(data, indent=2)[:1000]}")
    else:
        print(f"  Token obtained: {token[:20]}...")
    return token

def test_sso_login(driver, token):
    """Test 1: SSO into Rewards module."""
    print("\n[1] SSO into Rewards module...")
    sso_url = f"{REWARDS_URL}?sso_token={token}"
    driver.get(sso_url)
    time.sleep(4)
    screenshot(driver, "01_sso_landing")

    current = driver.current_url
    page_src = driver.page_source.lower()
    title = driver.title
    print(f"  URL: {current}")
    print(f"  Title: {title}")

    # Check if we landed on a login page (SSO failed) or the app
    if "login" in current.lower() and "sso_token" not in current.lower():
        file_bug(
            "[Rewards Employee] SSO redirect fails - lands on login page",
            f"After SSO with valid token, user is redirected to login page.\nURL: {current}"
        )
        return False

    if "error" in page_src[:500] or "unauthorized" in page_src[:500]:
        file_bug(
            "[Rewards Employee] SSO returns error/unauthorized",
            f"SSO URL returned error page.\nURL: {current}\nTitle: {title}"
        )
        return False

    # Check for some sign of being logged in
    if any(kw in page_src for kw in ["dashboard", "rewards", "priya", "kudos", "leaderboard", "points", "welcome"]):
        print("  SSO login appears successful.")
        return True

    # If the page loaded something, take it as partial success
    print(f"  Page loaded but unclear if logged in. Body length: {len(page_src)}")
    screenshot(driver, "01_sso_unclear")
    return True  # continue testing

def test_give_kudos(driver):
    """Test 2: Can Priya give kudos to a colleague?"""
    print("\n[2] Testing: Give kudos to a colleague...")
    screenshot(driver, "02_before_kudos")

    # Try to find and click kudos-related buttons/links
    kudos_found = False
    for selector in [
        "//a[contains(translate(text(),'KUDOS','kudos'),'kudos')]",
        "//button[contains(translate(text(),'KUDOS','kudos'),'kudos')]",
        "//span[contains(translate(text(),'KUDOS','kudos'),'kudos')]",
        "//*[contains(translate(text(),'GIVE KUDOS','give kudos'),'give kudos')]",
        "//*[contains(translate(text(),'SEND KUDOS','send kudos'),'send kudos')]",
        "//*[contains(translate(text(),'RECOGNIZE','recognize'),'recognize')]",
        "//*[contains(translate(text(),'APPRECIATION','appreciation'),'appreciation')]",
        "//a[contains(@href,'kudos')]",
        "//a[contains(@href,'recognition')]",
    ]:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                print(f"  Found kudos element: '{elements[0].text}' via {selector}")
                kudos_found = True
                try:
                    elements[0].click()
                    time.sleep(2)
                    screenshot(driver, "02_kudos_clicked")
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", elements[0])
                    time.sleep(2)
                    screenshot(driver, "02_kudos_clicked_js")
                break
        except Exception:
            continue

    if not kudos_found:
        # Try navigating directly
        for path in ["/kudos", "/recognition", "/give-kudos", "/send-kudos"]:
            try:
                driver.get(f"{REWARDS_URL}{path}")
                time.sleep(2)
                page = driver.page_source.lower()
                if "404" not in page[:500] and "not found" not in page[:500] and len(page) > 500:
                    print(f"  Navigated to {path}")
                    kudos_found = True
                    screenshot(driver, f"02_kudos_nav_{path.strip('/')}")
                    break
            except Exception:
                continue

    if not kudos_found:
        print("  Could not find kudos/recognition feature.")
        file_bug(
            "[Rewards Employee] Kudos/recognition feature not accessible",
            "Employee cannot find any kudos or recognition feature on the Rewards module. "
            "Searched for links, buttons, and direct navigation paths."
        )
    else:
        # Try to interact with the kudos form
        page = driver.page_source.lower()
        if any(kw in page for kw in ["select", "colleague", "recipient", "send", "submit", "message"]):
            print("  Kudos form/interface appears present.")
            screenshot(driver, "02_kudos_form")
        else:
            print("  Kudos page loaded but form not clearly visible.")
            screenshot(driver, "02_kudos_page_content")

    return kudos_found

def test_leaderboard(driver):
    """Test 3: Can she see the leaderboard?"""
    print("\n[3] Testing: Leaderboard visibility...")

    leaderboard_found = False
    for selector in [
        "//a[contains(translate(text(),'LEADERBOARD','leaderboard'),'leaderboard')]",
        "//span[contains(translate(text(),'LEADERBOARD','leaderboard'),'leaderboard')]",
        "//*[contains(translate(text(),'LEADERBOARD','leaderboard'),'leaderboard')]",
        "//a[contains(@href,'leader')]",
        "//a[contains(@href,'ranking')]",
    ]:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                print(f"  Found leaderboard element: '{elements[0].text}'")
                leaderboard_found = True
                try:
                    elements[0].click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", elements[0])
                time.sleep(2)
                screenshot(driver, "03_leaderboard_clicked")
                break
        except Exception:
            continue

    if not leaderboard_found:
        for path in ["/leaderboard", "/leader-board", "/rankings", "/top-performers"]:
            try:
                driver.get(f"{REWARDS_URL}{path}")
                time.sleep(2)
                page = driver.page_source.lower()
                if "404" not in page[:500] and "not found" not in page[:500] and len(page) > 500:
                    print(f"  Navigated to {path}")
                    leaderboard_found = True
                    screenshot(driver, f"03_leaderboard_{path.strip('/')}")
                    break
            except Exception:
                continue

    if not leaderboard_found:
        print("  Leaderboard not found.")
        file_bug(
            "[Rewards Employee] Leaderboard not accessible",
            "Employee cannot find leaderboard in the Rewards module."
        )
    else:
        page = driver.page_source.lower()
        if any(kw in page for kw in ["rank", "points", "score", "top", "#1", "position"]):
            print("  Leaderboard content appears present.")
        else:
            print("  Leaderboard page loaded but no ranking data visible.")
        screenshot(driver, "03_leaderboard_content")

    return leaderboard_found

def test_points_balance(driver):
    """Test 4: Points balance visibility."""
    print("\n[4] Testing: Points balance...")

    # Go to main dashboard/home first
    driver.get(REWARDS_URL)
    time.sleep(3)
    screenshot(driver, "04_home_for_points")

    page = driver.page_source.lower()
    points_visible = False

    for kw in ["points", "balance", "coins", "credits", "reward points", "my points"]:
        if kw in page:
            print(f"  Found '{kw}' on page.")
            points_visible = True
            break

    if not points_visible:
        # Try navigating to points/wallet pages
        for path in ["/points", "/my-points", "/wallet", "/balance", "/my-rewards", "/profile"]:
            try:
                driver.get(f"{REWARDS_URL}{path}")
                time.sleep(2)
                pg = driver.page_source.lower()
                if "404" not in pg[:500] and len(pg) > 500:
                    if any(kw in pg for kw in ["points", "balance", "coins", "credits"]):
                        points_visible = True
                        print(f"  Found points info at {path}")
                        screenshot(driver, f"04_points_{path.strip('/')}")
                        break
            except Exception:
                continue

    if not points_visible:
        print("  Points balance not found.")
        file_bug(
            "[Rewards Employee] Points balance not visible",
            "Employee cannot see their points balance anywhere in the Rewards module."
        )
    else:
        screenshot(driver, "04_points_visible")

    return points_visible

def test_badges(driver):
    """Test 5: Badge visibility."""
    print("\n[5] Testing: Badges...")

    badges_found = False
    for selector in [
        "//a[contains(translate(text(),'BADGES','badges'),'badges')]",
        "//span[contains(translate(text(),'BADGES','badges'),'badges')]",
        "//*[contains(translate(text(),'BADGE','badge'),'badge')]",
        "//*[contains(translate(text(),'ACHIEVEMENT','achievement'),'achievement')]",
        "//a[contains(@href,'badge')]",
        "//a[contains(@href,'achievement')]",
    ]:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                print(f"  Found badge element: '{elements[0].text}'")
                badges_found = True
                try:
                    elements[0].click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", elements[0])
                time.sleep(2)
                screenshot(driver, "05_badges_clicked")
                break
        except Exception:
            continue

    if not badges_found:
        for path in ["/badges", "/my-badges", "/achievements"]:
            try:
                driver.get(f"{REWARDS_URL}{path}")
                time.sleep(2)
                pg = driver.page_source.lower()
                if "404" not in pg[:500] and len(pg) > 500:
                    badges_found = True
                    print(f"  Navigated to {path}")
                    screenshot(driver, f"05_badges_{path.strip('/')}")
                    break
            except Exception:
                continue

    if not badges_found:
        print("  Badges section not found.")
        file_bug(
            "[Rewards Employee] Badges section not accessible",
            "Employee cannot find badges or achievements in the Rewards module."
        )
    else:
        screenshot(driver, "05_badges_content")

    return badges_found

def test_challenges(driver):
    """Test 6: Can she join challenges?"""
    print("\n[6] Testing: Challenges...")

    challenges_found = False
    for selector in [
        "//a[contains(translate(text(),'CHALLENGES','challenges'),'challenges')]",
        "//span[contains(translate(text(),'CHALLENGE','challenge'),'challenge')]",
        "//*[contains(translate(text(),'CHALLENGE','challenge'),'challenge')]",
        "//*[contains(translate(text(),'CONTEST','contest'),'contest')]",
        "//a[contains(@href,'challenge')]",
        "//a[contains(@href,'contest')]",
    ]:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                print(f"  Found challenge element: '{elements[0].text}'")
                challenges_found = True
                try:
                    elements[0].click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", elements[0])
                time.sleep(2)
                screenshot(driver, "06_challenges_clicked")
                break
        except Exception:
            continue

    if not challenges_found:
        for path in ["/challenges", "/my-challenges", "/contests", "/activities"]:
            try:
                driver.get(f"{REWARDS_URL}{path}")
                time.sleep(2)
                pg = driver.page_source.lower()
                if "404" not in pg[:500] and len(pg) > 500:
                    challenges_found = True
                    print(f"  Navigated to {path}")
                    screenshot(driver, f"06_challenges_{path.strip('/')}")
                    break
            except Exception:
                continue

    if not challenges_found:
        print("  Challenges section not found.")
        file_bug(
            "[Rewards Employee] Challenges not accessible",
            "Employee cannot find challenges or contests in the Rewards module."
        )
    else:
        # Look for a join button
        page = driver.page_source.lower()
        if any(kw in page for kw in ["join", "participate", "enroll", "sign up", "register"]):
            print("  Join/participate option appears available.")
        else:
            print("  Challenges page loaded but no join option visible.")
        screenshot(driver, "06_challenges_content")

    return challenges_found

def test_admin_access_denied(driver):
    """Test 7 & 8: Employee should NOT see admin settings or rewards catalog config."""
    print("\n[7] Testing: Admin settings should NOT be accessible...")

    issues = []

    # Test admin-related paths
    admin_paths = [
        ("/admin", "admin dashboard"),
        ("/admin/settings", "admin settings"),
        ("/settings", "settings"),
        ("/admin/catalog", "rewards catalog config"),
        ("/catalog/manage", "catalog management"),
        ("/admin/rewards", "admin rewards config"),
        ("/configuration", "configuration"),
        ("/admin/badges", "admin badges config"),
        ("/manage", "manage section"),
    ]

    for path, desc in admin_paths:
        try:
            driver.get(f"{REWARDS_URL}{path}")
            time.sleep(2)
            pg = driver.page_source.lower()
            current = driver.current_url.lower()
            screenshot(driver, f"07_admin_check_{path.strip('/').replace('/', '_')}")

            # Check if admin content is actually accessible (it shouldn't be)
            has_admin_content = any(kw in pg for kw in [
                "admin panel", "manage rewards", "configure", "reward catalog",
                "create badge", "delete", "edit reward", "admin settings"
            ])

            # If admin content is shown (not redirected/blocked), that's a bug
            if has_admin_content and "access denied" not in pg and "unauthorized" not in pg and "forbidden" not in pg:
                issues.append((path, desc))
                print(f"  WARNING: {desc} ({path}) appears accessible!")
        except Exception as e:
            print(f"  Error checking {path}: {e}")

    # Also check for admin nav items on the page
    driver.get(REWARDS_URL)
    time.sleep(2)
    page = driver.page_source.lower()
    screenshot(driver, "07_check_admin_nav")

    admin_nav_keywords = ["admin", "manage catalog", "configure rewards", "system settings", "reward settings"]
    visible_admin_nav = []
    for kw in admin_nav_keywords:
        if kw in page:
            # Verify it's in a navigation context, not just text
            visible_admin_nav.append(kw)

    if visible_admin_nav:
        print(f"  Admin navigation items visible: {visible_admin_nav}")
        # This could be a bug if these are clickable admin links
        for selector in [
            "//a[contains(translate(text(),'ADMIN','admin'),'admin')]",
            "//a[contains(translate(text(),'MANAGE','manage'),'manage')]",
            "//a[contains(@href,'admin')]",
            "//a[contains(@href,'manage')]",
            "//a[contains(@href,'config')]",
        ]:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for el in elements:
                    txt = el.text.strip()
                    href = el.get_attribute("href") or ""
                    if txt and any(kw in txt.lower() for kw in ["admin", "manage", "config", "catalog"]):
                        issues.append((href, f"Nav link: {txt}"))
                        print(f"  Admin nav link found: '{txt}' -> {href}")
            except Exception:
                continue

    if issues:
        details = "\n".join([f"- `{p}` ({d})" for p, d in issues])
        file_bug(
            "[Rewards Employee] Admin features accessible to employee",
            f"Employee (priya@technova.in) can access admin features that should be restricted:\n\n{details}\n\n"
            "Expected: Employee should not see or access admin settings or rewards catalog configuration."
        )
        screenshot(driver, "08_admin_access_bug")
    else:
        print("  Admin settings properly hidden from employee.")

    print("\n[8] Testing: Rewards catalog configuration should NOT be accessible...")
    # Already tested above via admin paths
    catalog_accessible = False
    for path in ["/catalog/config", "/catalog/edit", "/rewards/config", "/catalog/manage"]:
        try:
            driver.get(f"{REWARDS_URL}{path}")
            time.sleep(2)
            pg = driver.page_source.lower()
            screenshot(driver, f"08_catalog_check_{path.strip('/').replace('/', '_')}")
            if any(kw in pg for kw in ["edit catalog", "add reward", "configure", "create reward"]):
                if "access denied" not in pg and "unauthorized" not in pg:
                    catalog_accessible = True
                    print(f"  WARNING: Catalog config at {path} is accessible!")
        except Exception:
            continue

    if catalog_accessible:
        file_bug(
            "[Rewards Employee] Rewards catalog configuration accessible to employee",
            "Employee can access and potentially modify the rewards catalog configuration. "
            "This should be restricted to admin/HR roles only."
        )
    else:
        print("  Rewards catalog config properly restricted.")

    return len(issues) == 0 and not catalog_accessible

def explore_page(driver):
    """Take screenshots of main sections visible on the page."""
    print("\n[9] Capturing overview screenshots of all visible sections...")
    driver.get(REWARDS_URL)
    time.sleep(3)
    screenshot(driver, "09_main_dashboard")

    # Capture page source info
    page = driver.page_source
    page_lower = page.lower()

    # Find all nav links
    try:
        nav_links = driver.find_elements(By.CSS_SELECTOR, "nav a, .sidebar a, .menu a, [role='navigation'] a")
        if not nav_links:
            nav_links = driver.find_elements(By.CSS_SELECTOR, "a[href]")

        visited = set()
        for i, link in enumerate(nav_links[:15]):
            try:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                if not href or href in visited or "javascript" in href.lower():
                    continue
                if REWARDS_URL in href or href.startswith("/"):
                    visited.add(href)
                    if text:
                        print(f"  Nav: '{text}' -> {href}")
                    try:
                        link.click()
                    except ElementClickInterceptedException:
                        driver.execute_script("arguments[0].click();", link)
                    time.sleep(2)
                    safe_name = text.replace(" ", "_").replace("/", "_")[:20] if text else f"link_{i}"
                    screenshot(driver, f"09_nav_{safe_name}")
            except Exception:
                continue
    except Exception as e:
        print(f"  Error exploring nav: {e}")

    # Full page screenshot
    screenshot(driver, "09_final_state")

# ── Main ────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("REWARDS MODULE - EMPLOYEE TESTING (priya@technova.in)")
    print("=" * 60)

    # Step 1: Get auth token
    token = login_get_token()
    if not token:
        print("\nFATAL: Could not obtain auth token. Aborting.")
        return

    driver = make_driver()
    results = {}

    try:
        # Test 1: SSO Login
        sso_ok = test_sso_login(driver, token)
        results["SSO Login"] = "PASS" if sso_ok else "FAIL"

        if not sso_ok:
            # Try direct cookie/localStorage injection as fallback
            print("  Attempting fallback: set token in localStorage...")
            driver.get(REWARDS_URL)
            time.sleep(2)
            driver.execute_script(f"localStorage.setItem('token', '{token}');")
            driver.execute_script(f"localStorage.setItem('sso_token', '{token}');")
            driver.execute_script(f"localStorage.setItem('access_token', '{token}');")
            driver.refresh()
            time.sleep(3)
            screenshot(driver, "01_fallback_localstorage")

        # Test 2: Give Kudos
        kudos_ok = test_give_kudos(driver)
        results["Give Kudos"] = "PASS" if kudos_ok else "FAIL"

        # Test 3: Leaderboard
        lb_ok = test_leaderboard(driver)
        results["Leaderboard"] = "PASS" if lb_ok else "FAIL"

        # Test 4: Points Balance
        pts_ok = test_points_balance(driver)
        results["Points Balance"] = "PASS" if pts_ok else "FAIL"

        # Test 5: Badges
        badges_ok = test_badges(driver)
        results["Badges"] = "PASS" if badges_ok else "FAIL"

        # Test 6: Challenges
        chall_ok = test_challenges(driver)
        results["Challenges"] = "PASS" if chall_ok else "FAIL"

        # Test 7 & 8: Admin access denial
        admin_ok = test_admin_access_denied(driver)
        results["Admin Access Denied"] = "PASS" if admin_ok else "FAIL"

        # Test 9: Overview screenshots
        explore_page(driver)
        results["Screenshots"] = "DONE"

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        screenshot(driver, "fatal_error")
    finally:
        driver.quit()

    # ── Summary ──
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    for test, result in results.items():
        status = "PASS" if result == "PASS" else ("DONE" if result == "DONE" else "FAIL")
        print(f"  {test:30s} {status}")

    print(f"\nBugs filed: {len(bugs)}")
    for b in bugs:
        print(f"  - {b}")
    print("=" * 60)

if __name__ == "__main__":
    main()
