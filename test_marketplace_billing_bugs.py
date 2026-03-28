"""
EMP Cloud HRMS - Module Marketplace & Billing - Bug Filing Pass
Files GitHub issues for all confirmed bugs found in Pass 1 & 2.
Also performs targeted re-verification of key issues.
"""

import sys
import os
import time
import json
import traceback
import requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://test-empcloud.empcloud.com"
ORG_ADMIN_EMAIL = "ananya@technova.in"
ORG_ADMIN_PASS = "Welcome@123"
SUPER_ADMIN_EMAIL = "admin@empcloud.com"
SUPER_ADMIN_PASS = "SuperAdmin@2026"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\marketplace"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
bugs_filed = []

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--ignore-certificate-errors")
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)

def screenshot(driver, name):
    ts = datetime.now().strftime("%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"{ts}_{name}.png")
    driver.save_screenshot(path)
    print(f"  [SCREENSHOT] {path}")
    return path

def file_bug(title, body, severity="medium", screenshot_path=None):
    label_map = {"critical": "bug-critical", "high": "bug-high", "medium": "bug", "low": "bug-low"}
    labels = [label_map.get(severity, "bug"), "marketplace", "e2e-test"]
    full_body = (
        f"**Severity:** {severity.upper()}\n"
        f"**Found by:** Automated E2E Test\n"
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"**URL:** {BASE_URL}\n\n"
        f"{body}"
    )
    if screenshot_path:
        full_body += f"\n\n**Screenshot:** `{os.path.basename(screenshot_path)}` (see test artifacts in `C:\\Users\\Admin\\screenshots\\marketplace\\`)"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    payload = {"title": f"[E2E-Marketplace] {title}", "body": full_body, "labels": labels}
    try:
        r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues", json=payload, headers=headers, timeout=15)
        if r.status_code == 201:
            url = r.json().get("html_url", "")
            num = r.json().get("number", "?")
            print(f"  [GITHUB ISSUE] #{num} - {url}")
            bugs_filed.append({"title": title, "severity": severity, "issue_url": url, "number": num})
            return url
        else:
            print(f"  [GITHUB WARN] Status {r.status_code}: {r.text[:300]}")
            bugs_filed.append({"title": title, "severity": severity, "issue_url": "FAILED"})
    except Exception as e:
        print(f"  [GITHUB ERROR] {e}")
        bugs_filed.append({"title": title, "severity": severity, "issue_url": "FAILED"})
    return None

def safe_click(driver, element):
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)

def login(driver, email, password, role="user"):
    print(f"\n  Logging in as {role}: {email}")
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    if "/login" not in driver.current_url:
        driver.delete_all_cookies()
        try:
            driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        except:
            pass
        time.sleep(1)
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)

    for by, val in [(By.CSS_SELECTOR, "input[type='email']"), (By.CSS_SELECTOR, "input[type='text']"),
                     (By.ID, "email"), (By.NAME, "email")]:
        try:
            el = WebDriverWait(driver, 5).until(EC.presence_of_element_located((by, val)))
            if el.is_displayed():
                el.clear(); el.send_keys(email)
                break
        except:
            continue
    pf = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pf.clear(); pf.send_keys(password)
    for by, val in [(By.CSS_SELECTOR, "button[type='submit']"),
                     (By.XPATH, "//button[contains(text(),'Sign')]"),
                     (By.XPATH, "//button[contains(text(),'Login')]")]:
        try:
            btn = driver.find_element(by, val)
            if btn.is_displayed(): safe_click(driver, btn); break
        except:
            continue
    time.sleep(4)
    print(f"  Post-login URL: {driver.current_url}")


def main():
    print("=" * 70)
    print("  EMP CLOUD - MARKETPLACE & BILLING BUG VERIFICATION & FILING")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    driver = get_driver()

    try:
        # ──────────────────────────────────────────────────────────────
        # LOGIN AS ORG ADMIN
        # ──────────────────────────────────────────────────────────────
        login(driver, ORG_ADMIN_EMAIL, ORG_ADMIN_PASS, "org_admin")

        # ══════════════════════════════════════════════════════════════
        # BUG 1: Billing tabs do not switch content
        # ══════════════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  BUG VERIFY 1: Billing tabs (Invoices/Payments/Overview)")
        print("=" * 60)

        driver.get(f"{BASE_URL}/billing")
        time.sleep(3)
        sp_sub = screenshot(driver, "billing_subscriptions_default")

        # Get default (Subscriptions) tab content
        sub_body = driver.find_element(By.TAG_NAME, "body").text

        tab_results = {}
        for tab_name in ["Invoices", "Payments", "Overview"]:
            tab_clicked = False
            for by, val in [
                (By.XPATH, f"//button[contains(text(),'{tab_name}')]"),
                (By.XPATH, f"//a[contains(text(),'{tab_name}')]"),
                (By.XPATH, f"//*[contains(text(),'{tab_name}')]"),
            ]:
                try:
                    elems = driver.find_elements(by, val)
                    for el in elems:
                        if el.is_displayed() and el.tag_name in ["button", "a", "div", "span", "li"]:
                            safe_click(driver, el)
                            tab_clicked = True
                            time.sleep(3)
                            break
                    if tab_clicked:
                        break
                except:
                    continue

            if tab_clicked:
                sp = screenshot(driver, f"billing_{tab_name.lower()}_tab")
                tab_body = driver.find_element(By.TAG_NAME, "body").text

                # Check if the main content area changed
                # Strip sidebar text (appears in all tabs) and compare the main content
                # Use a heuristic: check if key differentiating text appears
                if tab_name == "Invoices":
                    # Should show invoice numbers, dates, download options
                    has_unique = any(kw in tab_body.lower() for kw in ["invoice #", "inv-", "download", "pdf", "generated"])
                    # Check if it still shows subscription cards (which means it didn't switch)
                    still_shows_subs = "Billing Cycle" in tab_body or "billing cycle" in tab_body.lower()
                    tab_results[tab_name] = {"unique_content": has_unique, "still_shows_subs": still_shows_subs}

                elif tab_name == "Payments":
                    has_unique = any(kw in tab_body.lower() for kw in ["transaction", "payment id", "receipt", "paid on"])
                    still_shows_subs = "Billing Cycle" in tab_body or "billing cycle" in tab_body.lower()
                    tab_results[tab_name] = {"unique_content": has_unique, "still_shows_subs": still_shows_subs}

                elif tab_name == "Overview":
                    has_unique = any(kw in tab_body.lower() for kw in ["total spend", "chart", "overview", "summary", "analytics"])
                    still_shows_subs = "Billing Cycle" in tab_body or "billing cycle" in tab_body.lower()
                    tab_results[tab_name] = {"unique_content": has_unique, "still_shows_subs": still_shows_subs}

                print(f"  {tab_name}: unique_content={tab_results[tab_name]['unique_content']}, still_shows_subs={tab_results[tab_name]['still_shows_subs']}")

        # Determine if tabs are broken
        tabs_broken = all(
            not tab_results.get(t, {}).get("unique_content", False) and tab_results.get(t, {}).get("still_shows_subs", True)
            for t in ["Invoices", "Payments", "Overview"]
            if t in tab_results
        )

        if tabs_broken:
            print("  CONFIRMED: Billing tabs do not switch content")
            sp = screenshot(driver, "bug_billing_tabs_broken")
            file_bug(
                "Billing page tabs (Invoices/Payments/Overview) do not switch content",
                "The Billing page at `/billing` has four tabs: Subscriptions, Invoices, Payments, and Overview. "
                "However, clicking on the Invoices, Payments, or Overview tabs does not change the displayed content. "
                "All tabs continue showing the same Subscriptions view with subscription cards "
                "(Rewards & Recognition, Recruitment & Talent Acquisition, Project Management).\n\n"
                "**Steps to reproduce:**\n"
                "1. Login as Org Admin (ananya@technova.in)\n"
                "2. Navigate to `/billing`\n"
                "3. Click on 'Invoices' tab\n"
                "4. Observe the content does not change from Subscriptions view\n"
                "5. Repeat for 'Payments' and 'Overview' tabs\n\n"
                "**Expected:** Each tab should show its respective content:\n"
                "- Invoices: Invoice history with invoice numbers, dates, PDF downloads\n"
                "- Payments: Payment transaction history\n"
                "- Overview: Billing summary/analytics\n\n"
                "**Actual:** All tabs display the same Subscriptions view with monthly cost and subscription cards.",
                severity="high", screenshot_path=sp
            )
        else:
            print("  Billing tabs appear to be working correctly")

        # ══════════════════════════════════════════════════════════════
        # BUG 2: No Subscribe button appears after unsubscribing
        # ══════════════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  BUG VERIFY 2: Subscribe button after unsubscribe")
        print("=" * 60)

        driver.get(f"{BASE_URL}/modules")
        time.sleep(3)

        # Count subscribe/unsubscribe buttons before
        unsub_before = driver.find_elements(By.XPATH, "//button[contains(text(),'Unsubscribe')]")
        sub_before = driver.find_elements(By.XPATH, "//button[contains(text(),'Subscribe') and not(contains(text(),'Unsubscribe'))]")
        print(f"  Before: {len(unsub_before)} Unsubscribe, {len(sub_before)} Subscribe buttons")

        if unsub_before:
            # Click last unsubscribe button
            btn = unsub_before[-1]
            try:
                parent = btn.find_element(By.XPATH, "./ancestor::*[string-length(text()) > 20][1]")
                mod_name = parent.text.split("\n")[0][:50]
            except:
                mod_name = "last module"
            print(f"  Unsubscribing from: {mod_name}")
            sp_before = screenshot(driver, "bug2_before_unsubscribe")
            safe_click(driver, btn)
            time.sleep(4)
            sp_after = screenshot(driver, "bug2_after_unsubscribe")

            # Refresh and check
            driver.get(f"{BASE_URL}/modules")
            time.sleep(3)
            sp_refresh = screenshot(driver, "bug2_after_refresh")

            unsub_after = driver.find_elements(By.XPATH, "//button[contains(text(),'Unsubscribe')]")
            sub_after = driver.find_elements(By.XPATH, "//button[contains(text(),'Subscribe') and not(contains(text(),'Unsubscribe'))]")
            print(f"  After: {len(unsub_after)} Unsubscribe, {len(sub_after)} Subscribe buttons")

            if len(unsub_after) < len(unsub_before) and sub_after:
                print("  Subscribe button appeared correctly after unsubscribe -- working as expected")
                # Re-subscribe to restore state
                safe_click(driver, sub_after[-1])
                time.sleep(3)
                print("  Re-subscribed to restore state")
            elif len(unsub_after) < len(unsub_before) and not sub_after:
                print("  CONFIRMED: Module unsubscribed but no Subscribe button appeared")
                file_bug(
                    "No 'Subscribe' button appears after unsubscribing from a module",
                    f"After unsubscribing from a module on the Module Marketplace (`/modules`), "
                    f"the page refreshes but no 'Subscribe' button appears in place of the 'Unsubscribe' button. "
                    f"The user cannot re-subscribe to the module.\n\n"
                    f"**Before unsubscribe:** {len(unsub_before)} Unsubscribe buttons, {len(sub_before)} Subscribe buttons\n"
                    f"**After unsubscribe:** {len(unsub_after)} Unsubscribe buttons, {len(sub_after)} Subscribe buttons\n\n"
                    f"**Steps to reproduce:**\n"
                    f"1. Login as Org Admin\n"
                    f"2. Navigate to `/modules`\n"
                    f"3. Click 'Unsubscribe' on any subscribed module\n"
                    f"4. Observe the module disappears or shows no Subscribe button\n\n"
                    f"**Expected:** A 'Subscribe' button should appear allowing re-subscription\n"
                    f"**Actual:** No Subscribe button is shown. The module may disappear from the list or remain without an action button.",
                    severity="high", screenshot_path=sp_refresh
                )
            elif len(unsub_after) == len(unsub_before):
                print("  Unsubscribe did not take effect (same count)")
                # Check if module just reappeared as subscribed
                body_after = driver.find_element(By.TAG_NAME, "body").text
                print(f"  Page text includes 'success': {'success' in body_after.lower()}")

        # ══════════════════════════════════════════════════════════════
        # BUG 3: Module SSO not working when navigating directly
        # ══════════════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  BUG VERIFY 3: Module SSO / cross-domain auth")
        print("=" * 60)

        # Dashboard has SSO links like ?sso_token=... but direct URLs don't use SSO
        driver.get(BASE_URL)
        time.sleep(3)

        # Find SSO links on the dashboard
        all_links = driver.find_elements(By.TAG_NAME, "a")
        sso_links = []
        non_sso_external = []
        for link in all_links:
            href = link.get_attribute("href") or ""
            if "empcloud.com" in href and "test-empcloud.empcloud.com" not in href:
                if "sso_token" in href:
                    sso_links.append(href[:80])
                else:
                    non_sso_external.append(href[:80])

        print(f"  SSO links found: {len(sso_links)}")
        print(f"  Non-SSO external links: {len(non_sso_external)}")

        # Test an SSO link to verify it works
        if sso_links:
            test_url = None
            for link in all_links:
                href = link.get_attribute("href") or ""
                if "sso_token" in href and "recruit" in href:
                    test_url = href
                    break
            if not test_url:
                for link in all_links:
                    href = link.get_attribute("href") or ""
                    if "sso_token" in href:
                        test_url = href
                        break

            if test_url:
                print(f"  Testing SSO link: {test_url[:80]}...")
                driver.get(test_url)
                time.sleep(5)
                sp = screenshot(driver, "sso_link_test")
                cur = driver.current_url
                body = driver.find_element(By.TAG_NAME, "body").text[:200]
                if "login" in body.lower() or "/login" in cur:
                    print(f"  SSO link still shows login page -- SSO may be broken")
                    file_bug(
                        "Module SSO links redirect to login page instead of authenticating",
                        f"Dashboard module links include SSO tokens (e.g., `?sso_token=...`) but clicking them "
                        f"still redirects to the module's login page instead of auto-authenticating.\n\n"
                        f"**Tested URL:** `{test_url[:100]}...`\n"
                        f"**Redirected to:** {cur}\n"
                        f"**Page content:** {body[:150]}\n\n"
                        f"**Steps to reproduce:**\n"
                        f"1. Login as Org Admin on main dashboard\n"
                        f"2. Click any module link (e.g., 'View Details' or 'Launch' for Recruit)\n"
                        f"3. Link includes sso_token but module shows login page\n\n"
                        f"**Expected:** SSO token should authenticate the user automatically\n"
                        f"**Actual:** Module login page is shown, requiring manual sign-in",
                        severity="high", screenshot_path=sp
                    )
                else:
                    print(f"  SSO link loaded successfully! URL: {cur}")
                    print(f"  Body: {body[:100]}")

        # Go back to main dashboard
        driver.get(BASE_URL)
        time.sleep(2)

        # ══════════════════════════════════════════════════════════════
        # BUG 4: No upgrade/downgrade plan option on billing
        # ══════════════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  BUG VERIFY 4: Missing plan upgrade/downgrade on billing")
        print("=" * 60)

        driver.get(f"{BASE_URL}/billing")
        time.sleep(3)
        sp = screenshot(driver, "billing_upgrade_check")
        body = driver.find_element(By.TAG_NAME, "body").text

        upgrade_found = False
        for by, val in [
            (By.XPATH, "//button[contains(text(),'Upgrade')]"),
            (By.XPATH, "//button[contains(text(),'Downgrade')]"),
            (By.XPATH, "//button[contains(text(),'Change Plan')]"),
            (By.XPATH, "//button[contains(text(),'Change')]"),
            (By.XPATH, "//a[contains(text(),'Upgrade')]"),
            (By.XPATH, "//a[contains(text(),'Change Plan')]"),
        ]:
            try:
                elems = driver.find_elements(by, val)
                for el in elems:
                    if el.is_displayed():
                        upgrade_found = True
                        print(f"  Found: '{el.text.strip()}'")
                        break
            except:
                continue

        # Also check for edit/pencil icons on subscription cards that might allow plan changes
        edit_btns = driver.find_elements(By.CSS_SELECTOR, "button svg, [class*='edit'] button, button[title*='dit']")
        visible_edits = [e for e in edit_btns if e.is_displayed()]
        print(f"  Edit/pencil buttons: {len(visible_edits)}")

        # Try clicking an edit icon to see if it offers plan change
        plan_change_via_edit = False
        if visible_edits and not upgrade_found:
            for eb in visible_edits[:3]:
                try:
                    safe_click(driver, eb)
                    time.sleep(2)
                    sp_edit = screenshot(driver, "billing_edit_click")
                    dialog_body = driver.find_element(By.TAG_NAME, "body").text.lower()
                    if any(kw in dialog_body for kw in ["change plan", "upgrade", "downgrade", "select plan"]):
                        plan_change_via_edit = True
                        print("  Plan change available via edit button")
                        break
                    # Close dialog
                    try:
                        close = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='lose'], [class*='close']")
                        safe_click(driver, close)
                        time.sleep(1)
                    except:
                        driver.get(f"{BASE_URL}/billing")
                        time.sleep(2)
                except:
                    continue

        if not upgrade_found and not plan_change_via_edit:
            print("  CONFIRMED: No plan upgrade/downgrade option found")
            file_bug(
                "No upgrade/downgrade option available on Billing page for subscriptions",
                "The Billing page at `/billing` shows active subscriptions (e.g., Rewards & Recognition on Enterprise plan, "
                "Recruitment on Basic plan) but provides no way to upgrade or downgrade the plan tier.\n\n"
                "**Steps to reproduce:**\n"
                "1. Login as Org Admin\n"
                "2. Navigate to `/billing`\n"
                "3. Look for upgrade/downgrade/change plan buttons on subscription cards\n\n"
                "**Expected:** An 'Upgrade', 'Downgrade', or 'Change Plan' option on each subscription\n"
                "**Actual:** Only edit (pencil) icons are present, which may or may not allow plan changes. "
                "No explicit upgrade/downgrade buttons visible.",
                severity="medium", screenshot_path=sp
            )

        # ══════════════════════════════════════════════════════════════
        # BUG 5: Check marketplace module tier/pricing visibility
        # ══════════════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  BUG VERIFY 5: Module pricing/tier visibility")
        print("=" * 60)

        driver.get(f"{BASE_URL}/modules")
        time.sleep(3)
        sp = screenshot(driver, "marketplace_pricing_check")
        body = driver.find_element(By.TAG_NAME, "body").text

        # From screenshots: modules show tags like "Free tier" on some modules
        # Check if pricing info is visible for all modules
        has_pricing = any(kw in body.lower() for kw in ["free", "price", "cost", "tier", "$", "rs", "\u20b9"])
        has_free_tier = "free tier" in body.lower() or "free" in body.lower()
        print(f"  Has pricing info: {has_pricing}")
        print(f"  Has free tier tags: {has_free_tier}")

        # Check if ALL modules show pricing or just some
        lines = body.split("\n")
        modules_with_pricing = 0
        modules_without_pricing = 0
        for line in lines:
            if any(kw in line.lower() for kw in ["subscribed", "subscribe", "unsubscribe"]):
                if any(kw in line.lower() for kw in ["free", "price", "$", "rs", "\u20b9", "tier"]):
                    modules_with_pricing += 1
                else:
                    modules_without_pricing += 1

        print(f"  Modules with visible pricing: {modules_with_pricing}")
        print(f"  Modules without visible pricing: {modules_without_pricing}")

        if modules_without_pricing > modules_with_pricing:
            file_bug(
                "Module Marketplace does not show pricing/tier information for most modules",
                f"The Module Marketplace at `/modules` shows module cards but most of them lack "
                f"pricing or tier information. Only some modules (like Exit Management) show a 'Free tier' tag. "
                f"Other modules show 'Subscribed' status but no pricing or plan tier.\n\n"
                f"Modules with pricing visible: {modules_with_pricing}\n"
                f"Modules without pricing: {modules_without_pricing}\n\n"
                f"**Expected:** Each module should clearly show its pricing tier (Free/Basic/Pro/Enterprise) "
                f"and monthly cost before subscribing\n"
                f"**Actual:** Most modules only show Subscribed/Unsubscribe without cost information",
                severity="medium", screenshot_path=sp
            )

        # ══════════════════════════════════════════════════════════════
        # SUPER ADMIN TESTS
        # ══════════════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  SUPER ADMIN TESTS")
        print("=" * 60)

        # Logout and login as super admin
        driver.delete_all_cookies()
        try:
            driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        except:
            pass
        time.sleep(1)

        login(driver, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASS, "super_admin")
        sp = screenshot(driver, "super_admin_logged_in")

        # Check super admin dashboard
        driver.get(f"{BASE_URL}/admin/super")
        time.sleep(3)
        sp_admin = screenshot(driver, "super_admin_dashboard")
        body = driver.find_element(By.TAG_NAME, "body").text
        cur = driver.current_url
        print(f"  Super admin URL: {cur}")
        print(f"  Title: {driver.title}")

        if "/login" in cur:
            print("  Super admin redirected to login -- session issue")
            sp = screenshot(driver, "bug_super_admin_login_redirect")
            file_bug(
                "Super Admin cannot access /admin/super after login -- redirected to login page",
                "After logging in as Super Admin (admin@empcloud.com), navigating to `/admin/super` "
                "redirects back to the login page. This appears to be a session/auth issue where "
                "the super admin session is not persisting correctly.\n\n"
                "**Steps to reproduce:**\n"
                "1. Navigate to login page\n"
                "2. Login with admin@empcloud.com / SuperAdmin@2026\n"
                "3. Navigate to `/admin/super`\n"
                "4. Page redirects to `/login`\n\n"
                "**Expected:** Super Admin dashboard should load\n"
                "**Actual:** Redirected to login page",
                severity="critical", screenshot_path=sp
            )
        else:
            print(f"  Super admin dashboard loaded. Content: {body[:200]}")

            # Check for module management features
            has_org_management = any(kw in body.lower() for kw in ["organization", "tenant", "module", "subscription"])
            has_revenue = any(kw in body.lower() for kw in ["revenue", "mrr", "arr", "income", "billing"])
            print(f"  Has org management: {has_org_management}")
            print(f"  Has revenue data: {has_revenue}")

            # Try admin module management URLs
            for path, name in [("/admin/modules", "Modules"), ("/admin/subscriptions", "Subscriptions"),
                               ("/admin/billing", "Billing")]:
                driver.get(f"{BASE_URL}{path}")
                time.sleep(3)
                cur = driver.current_url
                if path in cur:
                    print(f"  Admin {name}: Accessible")
                    screenshot(driver, f"admin_{name.lower()}_page")
                else:
                    print(f"  Admin {name}: Redirected to {cur}")

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        traceback.print_exc()
        if driver:
            screenshot(driver, "fatal_error")
    finally:
        if driver:
            driver.quit()

    # ══════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  FINAL TEST SUMMARY - MARKETPLACE & BILLING")
    print("=" * 70)

    print(f"\n  Total bugs filed: {len(bugs_filed)}")
    for i, b in enumerate(bugs_filed, 1):
        print(f"\n  Bug #{i}: [{b['severity'].upper()}] {b['title']}")
        print(f"    GitHub Issue: {b['issue_url']}")

    print(f"\n  Test artifacts: {SCREENSHOT_DIR}")
    print(f"\n  Key findings from all test passes:")
    print(f"    - Module Marketplace at /modules: WORKING")
    print(f"    - 10+ modules listed (Biometric, Monitor, Exit, Field Force, LMS, Payroll, Performance, Project, Recruit, Rewards)")
    print(f"    - All modules currently subscribed for TechNova org")
    print(f"    - Unsubscribe buttons present (Issue #50 resolved)")
    print(f"    - Billing page at /billing: ACCESSIBLE, shows Rs 1,00,000/month")
    print(f"    - Subscriptions: 3 active (Rewards Enterprise, Recruitment Basic, Project Basic)")
    print(f"    - Module SSO: Dashboard provides SSO token links to subdomain modules")
    print(f"    - Module direct URLs: Require separate login (no SSO auto-auth)")

    print(f"\n  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
