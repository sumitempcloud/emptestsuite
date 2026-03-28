import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import traceback
import requests
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
PREFIX = "adms_"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_found = []
step_counter = [0]

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)


def ss(driver, name):
    step_counter[0] += 1
    fname = f"{PREFIX}{step_counter[0]:02d}_{name}.png"
    path = os.path.join(SCREENSHOT_DIR, fname)
    driver.save_screenshot(path)
    print(f"  [SS] {fname}")
    return path


def wait_ready(driver, timeout=15):
    time.sleep(2)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        pass
    time.sleep(1)


def wait_for_body_content(driver, min_chars=30, timeout=10):
    """Wait for page body to have meaningful content."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_element(By.TAG_NAME, "body").text.strip()) >= min_chars
        )
    except TimeoutException:
        pass


def login_fresh(driver, email, password, role_label):
    """Create a fresh driver session for clean login."""
    print(f"\n{'='*60}")
    print(f"  Logging in as {role_label} ({email})")
    print(f"{'='*60}")

    # Delete all cookies and local/session storage
    driver.delete_all_cookies()
    try:
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
    except Exception:
        pass

    driver.get(f"{BASE_URL}/login")
    wait_ready(driver)
    time.sleep(3)

    # If SPA redirected us away from login, force it
    if "/login" not in driver.current_url:
        driver.delete_all_cookies()
        try:
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
        except Exception:
            pass
        driver.get(f"{BASE_URL}/login")
        wait_ready(driver)
        time.sleep(3)

    # Wait for login form
    email_field = None
    for attempt in range(5):
        for sel in [
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='mail']"),
            (By.CSS_SELECTOR, "input[placeholder*='Email']"),
            (By.ID, "email"),
        ]:
            try:
                email_field = WebDriverWait(driver, 3).until(EC.element_to_be_clickable(sel))
                if email_field:
                    break
            except TimeoutException:
                continue
        if email_field:
            break
        print(f"  Waiting for login form... attempt {attempt+1}")
        time.sleep(2)

    if not email_field:
        # Debug
        print(f"  [DEBUG] URL: {driver.current_url}")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"  [DEBUG] inputs: {len(inputs)}")
        for i in inputs:
            print(f"    type={i.get_attribute('type')} name={i.get_attribute('name')}")
        ss(driver, f"login_fail_{role_label}")
        return False

    ss(driver, f"login_page_{role_label}")

    email_field.clear()
    email_field.send_keys(email)

    pw_field = None
    for sel in [(By.CSS_SELECTOR, "input[type='password']"), (By.NAME, "password"), (By.ID, "password")]:
        try:
            pw_field = driver.find_element(*sel)
            if pw_field:
                break
        except NoSuchElementException:
            continue

    if not pw_field:
        print("  [ERROR] No password field")
        return False

    pw_field.clear()
    pw_field.send_keys(password)

    btn = None
    for sel in [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button[contains(text(),'Sign') or contains(text(),'Login') or contains(text(),'Log in')]"),
    ]:
        try:
            btn = driver.find_element(*sel)
            if btn:
                break
        except NoSuchElementException:
            continue

    if btn:
        btn.click()
    else:
        from selenium.webdriver.common.keys import Keys
        pw_field.send_keys(Keys.RETURN)

    wait_ready(driver, timeout=20)
    time.sleep(4)
    sc = ss(driver, f"login_result_{role_label}")

    url = driver.current_url
    print(f"  URL after login: {url}")

    if "/login" in url:
        errs = driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger, .text-danger, [role='alert']")
        for e in errs:
            t = e.text.strip()
            if t:
                print(f"  [ERROR] {t}")
        return False

    print(f"  [OK] Login done for {role_label}")
    return True


def report_bug(title, description, screenshot_path=None):
    print(f"\n  [BUG] {title}")
    bugs_found.append(title)

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    image_md = ""
    if screenshot_path and os.path.exists(screenshot_path):
        try:
            with open(screenshot_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            uname = f"adms_{datetime.now().strftime('%H%M%S')}_{os.path.basename(screenshot_path)}"
            resp = requests.put(
                f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/{uname}",
                headers=headers,
                json={"message": f"Upload {uname}", "content": img_data},
            )
            if resp.status_code in (200, 201):
                dl = resp.json().get("content", {}).get("download_url", "")
                if dl:
                    image_md = f"\n\n### Screenshot\n![screenshot]({dl})"
                print(f"  [OK] Screenshot uploaded")
            else:
                print(f"  [WARN] Upload: {resp.status_code}")
        except Exception as e:
            print(f"  [WARN] Upload: {e}")

    body = f"""{description}

**Environment:** test-empcloud.empcloud.com
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Browser:** Chrome Headless
**Test:** Automated E2E - Admin/Settings/RBAC{image_md}"""

    resp = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        headers=headers,
        json={"title": title, "body": body, "labels": ["bug", "automated-test"]},
    )
    if resp.status_code == 201:
        print(f"  [OK] Issue: {resp.json().get('html_url', '')}")
    else:
        print(f"  [ERROR] Issue creation: {resp.status_code}: {resp.text[:200]}")


def page_text(driver):
    return driver.find_element(By.TAG_NAME, "body").text


def has_keywords(driver, keywords):
    text = page_text(driver).lower()
    src = driver.page_source.lower()
    combined = text + " " + src
    found = [k for k in keywords if k.lower() in combined]
    missing = [k for k in keywords if k.lower() not in combined]
    return found, missing


def check_errors(driver):
    text = page_text(driver).lower()
    src = driver.page_source.lower()
    issues = []
    for p in ["500 internal server error", "404 not found", "403 forbidden",
              "something went wrong", "page not found", "server error"]:
        if p in text or p in src:
            issues.append(p)
    if len(page_text(driver).strip()) < 20:
        issues.append("blank page")
    return issues


# ── Tests ───────────────────────────────────────────────────────────────

def test_super_admin(driver):
    print("\n" + "="*60)
    print("  PHASE 1: SUPER ADMIN PAGES")
    print("="*60)

    # /admin/super
    print("\n--- /admin/super ---")
    driver.get(f"{BASE_URL}/admin/super")
    wait_ready(driver)
    time.sleep(3)
    wait_for_body_content(driver)
    sc = ss(driver, "sa_dashboard")

    errs = check_errors(driver)
    body = page_text(driver)
    print(f"  URL: {driver.current_url}")
    print(f"  Body ({len(body)} chars): {body[:400]}")

    if errs:
        report_bug(
            "[Super Admin] Dashboard /admin/super is blank or has errors",
            f"The super admin dashboard shows no content.\n\nBody length: {len(body)}\nErrors: {errs}",
            sc
        )

    # Try Overview Dashboard via sidebar
    print("\n  Trying sidebar Overview Dashboard link...")
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href], nav a, aside a")
        for link in links:
            href = link.get_attribute("href") or ""
            txt = link.text.strip()
            if "overview" in txt.lower() or "overview" in href.lower():
                print(f"  Clicking: '{txt}' -> {href}")
                link.click()
                wait_ready(driver)
                time.sleep(3)
                wait_for_body_content(driver)
                sc2 = ss(driver, "sa_overview")
                body2 = page_text(driver)
                print(f"  Overview URL: {driver.current_url}")
                print(f"  Overview body ({len(body2)} chars): {body2[:400]}")
                break
    except Exception as e:
        print(f"  [INFO] {e}")

    # /admin/ai-config
    print("\n--- /admin/ai-config ---")
    driver.get(f"{BASE_URL}/admin/ai-config")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "sa_ai_config")
    errs = check_errors(driver)
    found, missing = has_keywords(driver, ["ai", "config", "model", "provider"])
    body = page_text(driver)
    print(f"  URL: {driver.current_url}")
    print(f"  Found: {found}, Missing: {missing}")
    print(f"  Preview: {body[:300]}")

    if errs:
        report_bug("[Super Admin] AI Config errors", f"Errors: {errs}", sc)
    elif not found:
        report_bug("[Super Admin] AI Config missing content", f"Missing: {missing}\nPreview: {body[:300]}", sc)
    else:
        print("  [PASS] AI Config loaded correctly")

    # /admin/logs
    print("\n--- /admin/logs ---")
    driver.get(f"{BASE_URL}/admin/logs")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "sa_logs")
    errs = check_errors(driver)
    found, missing = has_keywords(driver, ["log", "audit", "monitoring", "error"])
    body = page_text(driver)
    print(f"  URL: {driver.current_url}")
    print(f"  Found: {found}, Missing: {missing}")
    print(f"  Preview: {body[:300]}")

    if errs:
        report_bug("[Super Admin] Logs page errors", f"Errors: {errs}", sc)
    elif not found:
        report_bug("[Super Admin] Logs page missing content", f"Missing: {missing}", sc)
    else:
        print("  [PASS] Log Dashboard loaded correctly")


def test_org_admin(driver):
    print("\n" + "="*60)
    print("  PHASE 2: ORG ADMIN - SETTINGS")
    print("="*60)

    # /settings
    print("\n--- /settings ---")
    driver.get(f"{BASE_URL}/settings")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "oa_settings")
    errs = check_errors(driver)
    body = page_text(driver)
    print(f"  URL: {driver.current_url}")
    print(f"  Preview: {body[:500]}")

    if errs:
        report_bug("[Org Admin] Settings page errors", f"Errors: {errs}", sc)
    else:
        print("  [PASS] Settings page loaded")

    # /settings/organization
    print("\n--- /settings/organization ---")
    driver.get(f"{BASE_URL}/settings/organization")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "oa_org_settings")
    errs = check_errors(driver)
    body = page_text(driver)
    print(f"  URL: {driver.current_url}")
    print(f"  Body ({len(body)} chars): {body[:400]}")

    if errs:
        report_bug("[Org Admin] Organization settings errors", f"Errors: {errs}\nURL: {driver.current_url}", sc)
    elif len(body.strip()) < 50:
        report_bug("[Org Admin] Organization settings page is blank", f"Body: {len(body)} chars\nURL: {driver.current_url}", sc)
    else:
        print("  [PASS] Organization settings loaded")

    # /settings/modules
    print("\n--- /settings/modules ---")
    driver.get(f"{BASE_URL}/settings/modules")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "oa_modules")
    errs = check_errors(driver)
    body = page_text(driver)
    print(f"  URL: {driver.current_url}")
    print(f"  Body ({len(body)} chars): {body[:400]}")

    if errs:
        report_bug("[Org Admin] Modules config errors", f"Errors: {errs}", sc)
    elif len(body.strip()) < 50:
        report_bug("[Org Admin] Modules config blank", f"Body: {len(body)} chars", sc)
    else:
        print("  [PASS] Modules config loaded")

    # /settings/custom-fields
    print("\n--- /settings/custom-fields ---")
    driver.get(f"{BASE_URL}/settings/custom-fields")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "oa_custom_fields")
    errs = check_errors(driver)
    body = page_text(driver)
    print(f"  URL: {driver.current_url}")
    print(f"  Body ({len(body)} chars): {body[:400]}")

    if errs:
        report_bug("[Org Admin] Custom fields errors", f"Errors: {errs}", sc)
    elif len(body.strip()) < 50:
        report_bug("[Org Admin] Custom fields blank", f"Body: {len(body)} chars", sc)
    else:
        print("  [PASS] Custom fields loaded")


def test_org_chart(driver):
    print("\n" + "="*60)
    print("  PHASE 2b: ORG CHART")
    print("="*60)

    print("\n--- /org-chart ---")
    driver.get(f"{BASE_URL}/org-chart")
    wait_ready(driver)
    time.sleep(4)
    sc = ss(driver, "oa_org_chart")
    errs = check_errors(driver)
    found, missing = has_keywords(driver, ["chart", "org", "employee"])
    body = page_text(driver)
    svgs = len(driver.find_elements(By.TAG_NAME, "svg"))
    print(f"  URL: {driver.current_url}")
    print(f"  Found: {found}, SVGs: {svgs}")
    print(f"  Preview: {body[:300]}")

    if errs:
        report_bug("[Org Chart] Page errors", f"Errors: {errs}", sc)
    elif not found and svgs == 0:
        report_bug("[Org Chart] No chart content", f"Missing: {missing}, SVGs: 0", sc)
    else:
        print("  [PASS] Org chart loaded")


def test_reports(driver):
    print("\n" + "="*60)
    print("  PHASE 2c: REPORTS")
    print("="*60)

    print("\n--- /reports ---")
    driver.get(f"{BASE_URL}/reports")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "oa_reports")

    url = driver.current_url
    errs = check_errors(driver)
    body = page_text(driver)
    print(f"  URL: {url}")
    print(f"  Preview: {body[:400]}")

    # Check if /reports redirected away (not a valid route)
    if url != f"{BASE_URL}/reports" and "/reports" not in url:
        print(f"  [INFO] /reports redirected to {url}")
        # Try alternate URLs
        for alt in ["/reports/dashboard", "/report", "/analytics"]:
            driver.get(f"{BASE_URL}{alt}")
            wait_ready(driver)
            time.sleep(2)
            alt_url = driver.current_url
            alt_body = page_text(driver)
            if alt in alt_url and len(alt_body.strip()) > 50:
                print(f"  Found reports at {alt}")
                sc = ss(driver, f"oa_reports_alt")
                break

    found, missing = has_keywords(driver, ["report", "employee", "attendance"])
    if errs:
        report_bug("[Reports] Reports page errors", f"Errors: {errs}\nURL: {url}", sc)
    elif not found:
        report_bug("[Reports] Reports page missing content or not found",
                   f"URL navigated to: {url}\nMissing: {missing}\nPreview: {body[:300]}", sc)
    else:
        print(f"  [PASS] Reports content found (keywords: {found})")

    # Try to generate
    print("\n--- Generate report ---")
    try:
        btns = driver.find_elements(By.XPATH,
            "//button[contains(text(),'Generate') or contains(text(),'Export') or contains(text(),'Download')] | "
            "//a[contains(text(),'Generate') or contains(text(),'Export')]"
        )
        if btns:
            print(f"  Clicking: '{btns[0].text.strip()}'")
            btns[0].click()
            wait_ready(driver)
            time.sleep(3)
            sc = ss(driver, "oa_report_gen")
            gen_errs = check_errors(driver)
            if gen_errs:
                report_bug("[Reports] Report generation error", f"Errors: {gen_errs}", sc)
            else:
                print("  [PASS] Report generation initiated")
        else:
            print("  [INFO] No generate/export buttons found")
    except Exception as e:
        print(f"  [INFO] {e}")


def test_rbac(driver):
    print("\n" + "="*60)
    print("  PHASE 3: RBAC (Employee)")
    print("="*60)

    denied_kw = ["denied", "unauthorized", "forbidden", "403", "not authorized", "permission", "not allowed"]
    admin_kw = ["platform admin", "revenue", "tenant", "super admin dashboard"]

    # /admin/super
    print("\n--- Employee -> /admin/super ---")
    driver.get(f"{BASE_URL}/admin/super")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "rbac_admin_super")
    url = driver.current_url
    body = page_text(driver)
    print(f"  URL: {url}")
    print(f"  Preview: {body[:400]}")

    denied = any(k in body.lower() for k in denied_kw)
    redirected = any(p in url for p in ["/login", "/dashboard", "/home", "/employee"])
    has_admin = any(k in body.lower() for k in admin_kw)

    if has_admin and not denied and not redirected:
        report_bug(
            "[RBAC Critical] Employee accessed Super Admin dashboard",
            f"Employee (priya@technova.in) can see Super Admin content at /admin/super.\n\n"
            f"URL: {url}\nContent: {body[:400]}",
            sc
        )
    else:
        print(f"  [PASS] Access {'denied' if denied else 'redirected' if redirected else 'no admin content'}")

    # /settings
    print("\n--- Employee -> /settings ---")
    driver.get(f"{BASE_URL}/settings")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "rbac_settings")
    url = driver.current_url
    body = page_text(driver)
    print(f"  URL: {url}")
    print(f"  Preview: {body[:400]}")

    denied = any(k in body.lower() for k in denied_kw)
    redirected = any(p in url for p in ["/login", "/dashboard", "/home", "/employee"])
    full_admin = any(k in body.lower() for k in ["module config", "billing", "subscription", "organization setting", "custom field"])

    if full_admin and not denied and not redirected:
        report_bug(
            "[RBAC] Employee accessed admin Settings",
            f"Employee can see admin settings content at /settings.\n\n"
            f"URL: {url}\nContent: {body[:400]}",
            sc
        )
    else:
        print(f"  [PASS] Settings access {'denied' if denied else 'redirected' if redirected else 'limited'}")

    # /admin/ai-config
    print("\n--- Employee -> /admin/ai-config ---")
    driver.get(f"{BASE_URL}/admin/ai-config")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "rbac_ai_config")
    url = driver.current_url
    body = page_text(driver)
    print(f"  URL: {url}")
    print(f"  Preview: {body[:300]}")

    denied = any(k in body.lower() for k in denied_kw)
    redirected = any(p in url for p in ["/login", "/dashboard", "/home", "/employee"])
    has_ai = "ai configuration" in body.lower() or "configure ai" in body.lower()

    if has_ai and not denied and not redirected:
        report_bug(
            "[RBAC] Employee accessed AI Config /admin/ai-config",
            f"Employee can see AI configuration.\n\nURL: {url}\nContent: {body[:300]}",
            sc
        )
    else:
        print(f"  [PASS] AI Config access {'denied' if denied else 'redirected' if redirected else 'blocked'}")

    # /admin/logs
    print("\n--- Employee -> /admin/logs ---")
    driver.get(f"{BASE_URL}/admin/logs")
    wait_ready(driver)
    time.sleep(3)
    sc = ss(driver, "rbac_logs")
    url = driver.current_url
    body = page_text(driver)
    print(f"  URL: {url}")
    print(f"  Preview: {body[:300]}")

    denied = any(k in body.lower() for k in denied_kw)
    redirected = any(p in url for p in ["/login", "/dashboard", "/home", "/employee"])
    has_logs = "log dashboard" in body.lower() or "real-time monitoring" in body.lower()

    if has_logs and not denied and not redirected:
        report_bug(
            "[RBAC] Employee accessed Log Dashboard /admin/logs",
            f"Employee can see log dashboard.\n\nURL: {url}\nContent: {body[:300]}",
            sc
        )
    else:
        print(f"  [PASS] Logs access {'denied' if denied else 'redirected' if redirected else 'blocked'}")


# ── Main ────────────────────────────────────────────────────────────────

def main():
    print("="*60)
    print("  EMP Cloud HRMS - Admin/Settings/RBAC E2E Test")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Use separate driver instances to avoid session bleed
    # PHASE 1: Super Admin
    print("\n>>> Starting Phase 1: Super Admin")
    driver1 = get_driver()
    try:
        if login_fresh(driver1, "admin@empcloud.com", "SuperAdmin@2026", "SuperAdmin"):
            test_super_admin(driver1)
        else:
            sc = ss(driver1, "sa_login_fail")
            report_bug("[Login] Super Admin login failed", "Could not login as admin@empcloud.com", sc)
    except Exception as e:
        print(f"  [ERROR] Phase 1: {e}")
        traceback.print_exc()
    finally:
        driver1.quit()

    # PHASE 2: Org Admin
    print("\n>>> Starting Phase 2: Org Admin")
    driver2 = get_driver()
    try:
        if login_fresh(driver2, "ananya@technova.in", "Welcome@123", "OrgAdmin"):
            test_org_admin(driver2)
            test_org_chart(driver2)
            test_reports(driver2)
        else:
            sc = ss(driver2, "oa_login_fail")
            report_bug("[Login] Org Admin login failed", "Could not login as ananya@technova.in", sc)
    except Exception as e:
        print(f"  [ERROR] Phase 2: {e}")
        traceback.print_exc()
    finally:
        driver2.quit()

    # PHASE 3: Employee RBAC
    print("\n>>> Starting Phase 3: Employee RBAC")
    driver3 = get_driver()
    try:
        if login_fresh(driver3, "priya@technova.in", "Welcome@123", "Employee"):
            test_rbac(driver3)
        else:
            sc = ss(driver3, "emp_login_fail")
            report_bug("[Login] Employee login failed (priya@technova.in)",
                       "Could not login as employee for RBAC test.", sc)
    except Exception as e:
        print(f"  [ERROR] Phase 3: {e}")
        traceback.print_exc()
    finally:
        driver3.quit()

    # Summary
    print("\n" + "="*60)
    print("  FINAL SUMMARY")
    print("="*60)
    print(f"  Bugs filed: {len(bugs_found)}")
    for i, b in enumerate(bugs_found, 1):
        print(f"    {i}. {b}")
    print("\n  Test complete.")


if __name__ == "__main__":
    main()
