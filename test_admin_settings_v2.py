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

BASE_URL = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots"
GITHUB_TOKEN = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
PFX = "admfin_"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

bugs_found = []
sc_num = [0]


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
    sc_num[0] += 1
    fname = f"{PFX}{sc_num[0]:02d}_{name}.png"
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


def login_fresh(driver, email, password, role_label):
    print(f"\n  Logging in as {role_label} ({email})")
    driver.delete_all_cookies()
    try:
        driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    except Exception:
        pass

    driver.get(f"{BASE_URL}/login")
    wait_ready(driver)
    time.sleep(3)

    if "/login" not in driver.current_url:
        driver.delete_all_cookies()
        try:
            driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
        except Exception:
            pass
        driver.get(f"{BASE_URL}/login")
        wait_ready(driver)
        time.sleep(3)

    email_field = None
    for attempt in range(5):
        for sel in [
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[name='email']"),
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
        time.sleep(2)

    if not email_field:
        ss(driver, f"nologin_{role_label}")
        return False

    email_field.clear()
    email_field.send_keys(email)

    pw = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pw.clear()
    pw.send_keys(password)

    btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    btn.click()

    wait_ready(driver, 20)
    time.sleep(4)
    ss(driver, f"loggedin_{role_label}")

    if "/login" in driver.current_url:
        print(f"  [FAIL] Still on login page")
        return False

    print(f"  [OK] Logged in, URL: {driver.current_url}")
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
            uname = f"admf_{datetime.now().strftime('%H%M%S')}_{os.path.basename(screenshot_path)}"
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
        print(f"  [ERROR] {resp.status_code}: {resp.text[:200]}")


def body(driver):
    return driver.find_element(By.TAG_NAME, "body").text


def has_errors(driver):
    t = body(driver).lower()
    s = driver.page_source.lower()
    errs = []
    for p in ["500 internal server error", "404 not found", "something went wrong", "server error"]:
        if p in t or p in s:
            errs.append(p)
    if len(body(driver).strip()) < 20:
        errs.append("blank page")
    return errs


def navigate_and_check(driver, path, name, expected_url_contains=None):
    """Navigate to path, wait, screenshot, return (url, body_text, errors)."""
    driver.get(f"{BASE_URL}{path}")
    wait_ready(driver)
    time.sleep(3)
    # Wait for SPA content
    try:
        WebDriverWait(driver, 8).until(
            lambda d: len(d.find_element(By.TAG_NAME, "body").text.strip()) > 30
        )
    except TimeoutException:
        pass
    sc = ss(driver, name)
    url = driver.current_url
    text = body(driver)
    errs = has_errors(driver)

    # Check if redirected away
    check_path = expected_url_contains or path
    redirected = check_path not in url

    print(f"  URL: {url}")
    print(f"  Body ({len(text)} chars): {text[:300]}")
    if redirected:
        print(f"  [REDIRECTED] Expected {check_path} in URL but got {url}")
    if errs:
        print(f"  [ERRORS] {errs}")

    return url, text, errs, sc, redirected


def main():
    print("="*60)
    print(f"  EMP Cloud E2E - Admin/Settings/RBAC")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # ════════════════════════════════════════════════════════
    # PHASE 1: SUPER ADMIN
    # ════════════════════════════════════════════════════════
    print("\n>>> PHASE 1: SUPER ADMIN")
    d = get_driver()
    try:
        if not login_fresh(d, "admin@empcloud.com", "SuperAdmin@2026", "SuperAdmin"):
            report_bug("[Login] Super Admin login failed", "Cannot login as admin@empcloud.com")
            d.quit()
            return

        # /admin/super
        print("\n--- /admin/super ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/admin/super", "sa_dashboard")
        if errs or len(text.strip()) < 30:
            report_bug(
                "[Super Admin] Dashboard /admin/super renders blank",
                f"The super admin dashboard at /admin/super renders with no visible content.\n\n"
                f"Body text length: {len(text.strip())} characters.\n"
                f"The sidebar navigation is present but the main content area is empty.\n"
                f"Expected: organization list, revenue stats, overview dashboard.",
                sc
            )

        # Try clicking Overview Dashboard in sidebar
        print("\n  Clicking 'Overview Dashboard' sidebar link...")
        try:
            ov_link = d.find_element(By.XPATH, "//a[contains(text(),'Overview Dashboard') or contains(text(),'Overview')]")
            ov_link.click()
            wait_ready(d)
            time.sleep(3)
            try:
                WebDriverWait(d, 8).until(
                    lambda dr: len(dr.find_element(By.TAG_NAME, "body").text.strip()) > 30
                )
            except TimeoutException:
                pass
            sc_ov = ss(d, "sa_overview_clicked")
            ov_text = body(d)
            print(f"  Overview URL: {d.current_url}")
            print(f"  Overview body ({len(ov_text)} chars): {ov_text[:400]}")
        except Exception as e:
            print(f"  Could not click Overview: {e}")

        # /admin/ai-config
        print("\n--- /admin/ai-config ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/admin/ai-config", "sa_ai_config")
        if errs:
            report_bug("[Super Admin] AI Config has errors", f"Errors: {errs}\nURL: {url}", sc)
        elif "ai configuration" not in text.lower() and "ai" not in text.lower():
            report_bug("[Super Admin] AI Config missing content", f"URL: {url}\nPreview: {text[:300]}", sc)
        else:
            print("  [PASS] AI Config loaded")

        # /admin/logs
        print("\n--- /admin/logs ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/admin/logs", "sa_logs")
        if errs:
            report_bug("[Super Admin] Log Dashboard errors", f"Errors: {errs}\nURL: {url}", sc)
        elif "log dashboard" not in text.lower() and "log" not in text.lower():
            report_bug("[Super Admin] Log Dashboard missing content", f"URL: {url}\nPreview: {text[:300]}", sc)
        else:
            print("  [PASS] Log Dashboard loaded")

    except Exception as e:
        print(f"  [ERROR] Phase 1: {e}")
        traceback.print_exc()
    finally:
        d.quit()

    # ════════════════════════════════════════════════════════
    # PHASE 2: ORG ADMIN
    # ════════════════════════════════════════════════════════
    print("\n>>> PHASE 2: ORG ADMIN")
    d = get_driver()
    try:
        if not login_fresh(d, "ananya@technova.in", "Welcome@123", "OrgAdmin"):
            report_bug("[Login] Org Admin login failed", "Cannot login as ananya@technova.in")
            d.quit()
            return

        # /settings
        print("\n--- /settings ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/settings", "oa_settings")
        if errs:
            report_bug("[Org Admin] Settings page errors", f"Errors: {errs}", sc)
        elif redir:
            report_bug("[Org Admin] /settings redirects away",
                       f"Navigating to /settings redirects to {url}", sc)
        else:
            print("  [PASS] Settings page loaded")

        # Check what the settings page actually contains
        # Look for settings-specific content vs just sidebar nav
        settings_content_kw = ["organization name", "company", "timezone", "currency", "logo",
                               "work week", "fiscal year", "date format"]
        settings_found = [k for k in settings_content_kw if k in text.lower()]
        print(f"  Settings-specific content found: {settings_found}")

        # /settings/organization
        print("\n--- /settings/organization ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/settings/organization", "oa_org_settings")
        if redir:
            report_bug(
                "[Org Admin] /settings/organization redirects to dashboard",
                f"Navigating to /settings/organization redirects to {url} instead of showing organization settings.\n\n"
                f"Expected: Organization settings page with company name, timezone, logo etc.",
                sc
            )
        elif errs:
            report_bug("[Org Admin] Organization settings errors", f"Errors: {errs}", sc)
        else:
            print("  [PASS] Organization settings loaded")

        # /settings/modules
        print("\n--- /settings/modules ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/settings/modules", "oa_modules")
        if redir:
            report_bug(
                "[Org Admin] /settings/modules redirects to dashboard",
                f"Navigating to /settings/modules redirects to {url} instead of showing module configuration.\n\n"
                f"Expected: Module enable/disable configuration page.",
                sc
            )
        elif errs:
            report_bug("[Org Admin] Modules config errors", f"Errors: {errs}", sc)
        else:
            print("  [PASS] Modules config loaded")

        # /settings/custom-fields
        print("\n--- /settings/custom-fields ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/settings/custom-fields", "oa_custom_fields")
        if redir:
            report_bug(
                "[Org Admin] /settings/custom-fields redirects to dashboard",
                f"Navigating to /settings/custom-fields redirects to {url}.\n\n"
                f"Expected: Custom fields management page.",
                sc
            )
        elif errs:
            report_bug("[Org Admin] Custom fields errors", f"Errors: {errs}", sc)
        else:
            print("  [PASS] Custom fields loaded")

        # Now try navigating via sidebar links from /settings
        print("\n--- Discovering settings sub-pages via sidebar ---")
        d.get(f"{BASE_URL}/settings")
        wait_ready(d)
        time.sleep(3)
        links = d.find_elements(By.CSS_SELECTOR, "a[href]")
        settings_links = []
        for l in links:
            href = l.get_attribute("href") or ""
            txt = l.text.strip()
            if "/settings" in href or txt.lower() in ["settings", "custom fields", "modules", "billing", "organization"]:
                settings_links.append((href, txt))
        print(f"  Settings nav links: {settings_links[:20]}")

        # Navigate using sidebar: Settings link
        print("\n--- Click Settings sidebar link ---")
        try:
            settings_link = d.find_element(By.XPATH, "//a[text()='Settings']")
            settings_link.click()
            wait_ready(d)
            time.sleep(3)
            sc_s = ss(d, "oa_settings_clicked")
            s_url = d.current_url
            s_text = body(d)
            print(f"  URL after clicking Settings: {s_url}")
            print(f"  Content: {s_text[:400]}")
        except Exception as e:
            print(f"  [INFO] {e}")

        # Navigate using sidebar: Custom Fields link
        print("\n--- Click Custom Fields sidebar link ---")
        try:
            cf_link = d.find_element(By.XPATH, "//a[text()='Custom Fields']")
            cf_link.click()
            wait_ready(d)
            time.sleep(3)
            sc_cf = ss(d, "oa_cf_clicked")
            cf_url = d.current_url
            cf_text = body(d)
            print(f"  URL: {cf_url}")
            print(f"  Content: {cf_text[:400]}")
        except Exception as e:
            print(f"  [INFO] {e}")

        # /org-chart
        print("\n--- /org-chart ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/org-chart", "oa_org_chart")
        svgs = len(d.find_elements(By.TAG_NAME, "svg"))
        print(f"  SVG elements: {svgs}")
        if errs:
            report_bug("[Org Chart] Page errors", f"Errors: {errs}", sc)
        elif redir and svgs == 0:
            report_bug("[Org Chart] Not rendering", f"Redirected to {url}, no SVG elements", sc)
        else:
            print("  [PASS] Org chart loaded")

        # /reports
        print("\n--- /reports ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/reports", "oa_reports")
        if redir:
            report_bug(
                "[Reports] /reports route redirects to dashboard",
                f"Navigating to /reports redirects to {url} instead of showing the reports page.\n\n"
                f"Expected: Reports list page with options to generate employee, attendance, leave reports etc.",
                sc
            )
        elif errs:
            report_bug("[Reports] Reports page errors", f"Errors: {errs}", sc)
        else:
            # Check for report-specific content
            report_kw = ["generate", "export", "download", "report type", "date range"]
            rfound = [k for k in report_kw if k in text.lower()]
            print(f"  Report-specific keywords: {rfound}")
            if not rfound:
                print("  [WARN] Reports page loaded but may lack report generation UI")
            else:
                print("  [PASS] Reports page loaded")

    except Exception as e:
        print(f"  [ERROR] Phase 2: {e}")
        traceback.print_exc()
    finally:
        d.quit()

    # ════════════════════════════════════════════════════════
    # PHASE 3: EMPLOYEE RBAC
    # ════════════════════════════════════════════════════════
    print("\n>>> PHASE 3: EMPLOYEE RBAC")
    d = get_driver()
    try:
        if not login_fresh(d, "priya@technova.in", "Welcome@123", "Employee"):
            report_bug("[Login] Employee login failed", "Cannot login as priya@technova.in")
            d.quit()
            return

        denied_kw = ["denied", "unauthorized", "forbidden", "403", "not authorized",
                     "permission", "not allowed", "insufficient"]

        # /admin/super
        print("\n--- Employee -> /admin/super ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/admin/super", "rbac_admin_super")
        denied = any(k in text.lower() for k in denied_kw)
        redirected = any(p in url for p in ["/login", "/dashboard", "/home"]) or "/admin/super" not in url
        admin_content = any(k in text.lower() for k in ["platform admin", "revenue", "organizations", "tenant"])

        if admin_content and not denied:
            report_bug(
                "[RBAC Critical] Employee can access /admin/super",
                f"Employee priya@technova.in can see Super Admin content.\n\nURL: {url}\nContent: {text[:400]}",
                sc
            )
        else:
            reason = "denied" if denied else ("redirected" if redirected else "no admin content visible")
            print(f"  [PASS] /admin/super blocked ({reason})")

        # /admin/ai-config
        print("\n--- Employee -> /admin/ai-config ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/admin/ai-config", "rbac_ai_config")
        denied = any(k in text.lower() for k in denied_kw)
        has_ai = "ai configuration" in text.lower()

        if has_ai and not denied:
            report_bug("[RBAC] Employee can access /admin/ai-config",
                       f"Employee can see AI config.\nURL: {url}\nContent: {text[:300]}", sc)
        else:
            print(f"  [PASS] /admin/ai-config blocked ({'denied' if denied else 'no ai content'})")

        # /admin/logs
        print("\n--- Employee -> /admin/logs ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/admin/logs", "rbac_logs")
        denied = any(k in text.lower() for k in denied_kw)
        has_logs = "log dashboard" in text.lower() and "real-time monitoring" in text.lower()

        if has_logs and not denied:
            report_bug("[RBAC] Employee can access /admin/logs",
                       f"Employee can see log dashboard.\nURL: {url}\nContent: {text[:300]}", sc)
        else:
            print(f"  [PASS] /admin/logs blocked ({'denied' if denied else 'no log content'})")

        # /settings
        print("\n--- Employee -> /settings ---")
        url, text, errs, sc, redir = navigate_and_check(d, "/settings", "rbac_settings")
        denied = any(k in text.lower() for k in denied_kw)
        redirected_away = "/settings" not in url
        admin_settings_kw = ["module", "billing", "subscription", "organization name", "custom field"]
        has_admin_settings = any(k in text.lower() for k in admin_settings_kw)

        if "/settings" in url and not denied and not redirected_away:
            # Employee reached /settings - check what they can see
            print(f"  [WARN] Employee reached /settings at {url}")
            # Check if nav shows admin items
            nav_text = text[:500].lower()
            admin_nav_items = [item for item in ["billing", "users", "modules", "custom fields", "audit log"]
                              if item in nav_text]
            if admin_nav_items:
                report_bug(
                    "[RBAC] Employee can access /settings page",
                    f"Employee (priya@technova.in) can navigate to /settings and sees admin navigation items: {admin_nav_items}.\n\n"
                    f"Employee should be redirected or denied access to admin settings.\n\n"
                    f"URL: {url}\nContent: {text[:500]}",
                    sc
                )
            else:
                print(f"  [INFO] Employee on /settings but no admin nav items visible")
        else:
            reason = "denied" if denied else ("redirected" if redirected_away else "ok")
            print(f"  [PASS] /settings access result: {reason}")

    except Exception as e:
        print(f"  [ERROR] Phase 3: {e}")
        traceback.print_exc()
    finally:
        d.quit()

    # ════════════════════════════════════════════════════════
    # SUMMARY
    # ════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("  FINAL SUMMARY")
    print("="*60)
    print(f"  Bugs filed: {len(bugs_found)}")
    for i, b in enumerate(bugs_found, 1):
        print(f"    {i}. {b}")
    print("\n  Complete.")


if __name__ == "__main__":
    main()
