"""
EMP Cloud HRMS - Module Marketplace & Billing E2E Test - Pass 2
Deeper testing: billing tabs, module subscribe/unsubscribe cycle,
super admin module view, module integration via known URLs
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
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──
BASE_URL = "https://test-empcloud.empcloud.com"
ORG_ADMIN_EMAIL = "ananya@technova.in"
ORG_ADMIN_PASS = "Welcome@123"
SUPER_ADMIN_EMAIL = "admin@empcloud.com"
SUPER_ADMIN_PASS = "SuperAdmin@2026"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\marketplace"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
bugs = []

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
    full_body = (f"**Severity:** {severity.upper()}\n**Found by:** Automated E2E Test (Pass 2)\n"
                 f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n**URL:** {BASE_URL}\n\n{body}")
    if screenshot_path:
        full_body += f"\n\n**Screenshot:** `{os.path.basename(screenshot_path)}` (attached to test artifacts)"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    payload = {"title": f"[E2E-Marketplace] {title}", "body": full_body, "labels": labels}
    try:
        r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues", json=payload, headers=headers, timeout=15)
        if r.status_code == 201:
            url = r.json().get("html_url", "")
            print(f"  [GITHUB ISSUE] #{r.json().get('number')} - {url}")
            bugs.append({"title": title, "severity": severity, "issue_url": url})
            return url
        else:
            print(f"  [GITHUB WARN] Status {r.status_code}: {r.text[:200]}")
            bugs.append({"title": title, "severity": severity, "issue_url": "FAILED TO CREATE"})
    except Exception as e:
        print(f"  [GITHUB ERROR] {e}")
        bugs.append({"title": title, "severity": severity, "issue_url": "FAILED TO CREATE"})
    return None

def safe_click(driver, element):
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)

def login(driver, email, password, role="user"):
    print(f"\n{'='*60}")
    print(f"  Logging in as {role}: {email}")
    print(f"{'='*60}")
    # Go to login page explicitly
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)

    # If redirected to dashboard, we need to logout first
    if "/login" not in driver.current_url:
        print("  Not on login page, trying to logout...")
        # Try logout link
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        if "/login" not in driver.current_url:
            # Force clear and try again
            driver.delete_all_cookies()
            driver.execute_script("localStorage.clear(); sessionStorage.clear();")
            time.sleep(1)
            driver.get(f"{BASE_URL}/login")
            time.sleep(3)

    screenshot(driver, f"login_page_{role}")

    # Find email field
    email_field = None
    for by, val in [(By.CSS_SELECTOR, "input[type='email']"), (By.CSS_SELECTOR, "input[type='text']"),
                     (By.ID, "email"), (By.NAME, "email"), (By.CSS_SELECTOR, "input[placeholder*='mail']")]:
        try:
            el = WebDriverWait(driver, 5).until(EC.presence_of_element_located((by, val)))
            if el.is_displayed():
                email_field = el
                break
        except:
            continue

    if not email_field:
        # List all inputs for debugging
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"  Inputs on page ({len(inputs)}):")
        for i, inp in enumerate(inputs):
            print(f"    [{i}] type={inp.get_attribute('type')} name={inp.get_attribute('name')} placeholder={inp.get_attribute('placeholder')}")
        raise Exception(f"Cannot find email field. URL: {driver.current_url}")

    email_field.clear()
    email_field.send_keys(email)

    # Password
    pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pass_field.clear()
    pass_field.send_keys(password)

    # Submit
    for by, val in [(By.CSS_SELECTOR, "button[type='submit']"),
                     (By.XPATH, "//button[contains(text(),'Login')]"),
                     (By.XPATH, "//button[contains(text(),'Sign')]")]:
        try:
            btn = driver.find_element(by, val)
            if btn.is_displayed():
                safe_click(driver, btn)
                break
        except:
            continue

    time.sleep(4)
    screenshot(driver, f"after_login_{role}")
    print(f"  Post-login URL: {driver.current_url}")

def logout(driver):
    """Force logout by clearing all auth state."""
    print("  Logging out...")
    # Try clicking sign-out link
    try:
        links = driver.find_elements(By.XPATH, "//a[contains(text(),'Sign out') or contains(text(),'Logout') or contains(text(),'Log out')]")
        for link in links:
            if link.is_displayed():
                safe_click(driver, link)
                time.sleep(2)
                return
    except:
        pass
    # Fallback: clear cookies and storage
    driver.delete_all_cookies()
    try:
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
    except:
        pass
    time.sleep(1)


# ══════════════════════════════════════════════════════════════════════
# TEST 1: Deep Marketplace Testing
# ══════════════════════════════════════════════════════════════════════
def test_marketplace_deep(driver):
    print("\n" + "="*70)
    print("  TEST 1: DEEP MARKETPLACE TESTING")
    print("="*70)

    driver.get(f"{BASE_URL}/modules")
    time.sleep(3)
    screenshot(driver, "marketplace_deep_start")

    # ── Get all module cards ──
    print("\n[1a] Enumerate all module cards")
    body = driver.find_element(By.TAG_NAME, "body").text
    page_src = driver.page_source

    # Find all elements that might be module rows/cards
    # From screenshot: each module has name, description, tags (free/paid), Subscribe/Unsubscribe button
    module_rows = []
    # Try finding by common card/row patterns
    for sel in ["[class*='module']", "[class*='Module']", ".card", "[class*='card']",
                "[class*='Card']", "li", "[class*='item']", "[class*='Item']",
                "[class*='row']", "[class*='list-item']"]:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            # Filter to ones that contain Subscribe/Unsubscribe text
            for el in elems:
                txt = el.text
                if ("Subscribe" in txt or "Unsubscribe" in txt) and len(txt) > 20:
                    module_rows.append(el)
        except:
            continue

    # Deduplicate by taking unique text content
    seen_texts = set()
    unique_rows = []
    for r in module_rows:
        t = r.text[:80]
        if t not in seen_texts:
            seen_texts.add(t)
            unique_rows.append(r)

    print(f"  Found {len(unique_rows)} module rows")
    modules_info = []
    for i, row in enumerate(unique_rows):
        txt = row.text.replace("\n", " | ")
        # Determine status
        if "Unsubscribe" in row.text:
            status = "subscribed"
        elif "Subscribe" in row.text:
            status = "not_subscribed"
        else:
            status = "unknown"
        # Check for free/paid tags
        tier = "unknown"
        txt_lower = row.text.lower()
        if "free" in txt_lower:
            tier = "free"
        elif "paid" in txt_lower or "price" in txt_lower or "premium" in txt_lower:
            tier = "paid"
        modules_info.append({"index": i, "text_preview": txt[:120], "status": status, "tier": tier})
        print(f"    [{i}] {status:15s} | {tier:7s} | {txt[:100]}")

    # ── Subscribe/Unsubscribe cycle ──
    print("\n[1b] Test Subscribe/Unsubscribe cycle")
    # Find a module that is currently subscribed and try to unsubscribe then re-subscribe
    unsub_buttons = driver.find_elements(By.XPATH, "//button[contains(text(),'Unsubscribe')]")
    sub_buttons = driver.find_elements(By.XPATH, "//button[contains(text(),'Subscribe') and not(contains(text(),'Unsubscribe'))]")

    print(f"  Unsubscribe buttons: {len(unsub_buttons)}")
    print(f"  Subscribe buttons: {len(sub_buttons)}")

    cycle_result = "not_tested"
    if unsub_buttons:
        # Pick the last unsubscribe button (safer, likely a less critical module)
        btn = unsub_buttons[-1]
        # Get the parent/row text to know which module
        try:
            parent = btn.find_element(By.XPATH, "./ancestor::*[contains(@class,'card') or contains(@class,'module') or contains(@class,'item') or contains(@class,'row')][1]")
            mod_name = parent.text.split("\n")[0][:60]
        except:
            mod_name = "unknown module"

        print(f"  Unsubscribing from: {mod_name}")
        screenshot(driver, "before_unsubscribe_cycle")
        safe_click(driver, btn)
        time.sleep(3)
        screenshot(driver, "after_unsubscribe_click")

        # Check for confirmation dialog
        try:
            dialogs = driver.find_elements(By.CSS_SELECTOR, "[role='dialog'], [class*='modal'], [class*='Modal'], [class*='dialog']")
            if dialogs:
                print(f"  Confirmation dialog appeared")
                screenshot(driver, "unsubscribe_confirmation_dialog")
                # Try to confirm
                for by, val in [(By.XPATH, "//button[contains(text(),'Confirm')]"),
                                (By.XPATH, "//button[contains(text(),'Yes')]"),
                                (By.XPATH, "//button[contains(text(),'OK')]"),
                                (By.XPATH, "//button[contains(text(),'Unsubscribe')]")]:
                    try:
                        confirm_btn = driver.find_element(by, val)
                        if confirm_btn.is_displayed():
                            safe_click(driver, confirm_btn)
                            time.sleep(3)
                            break
                    except:
                        continue
        except:
            pass

        screenshot(driver, "after_unsubscribe_confirmed")
        # Check page for success/failure
        body_after = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "success" in body_after or "unsubscribed" in body_after:
            print("  Unsubscribe SUCCESS")
        else:
            print("  Unsubscribe result unclear, checking button state...")

        # Now look for Subscribe button where Unsubscribe was
        time.sleep(2)
        driver.get(f"{BASE_URL}/modules")
        time.sleep(3)
        screenshot(driver, "marketplace_after_unsubscribe")

        # Try to re-subscribe
        new_sub_buttons = driver.find_elements(By.XPATH, "//button[contains(text(),'Subscribe') and not(contains(text(),'Unsubscribe'))]")
        print(f"  Subscribe buttons after unsubscribe: {len(new_sub_buttons)}")

        if new_sub_buttons:
            print(f"  Re-subscribing...")
            safe_click(driver, new_sub_buttons[-1])
            time.sleep(3)
            screenshot(driver, "after_resubscribe")

            # Check for confirmation/payment dialog
            try:
                dialogs = driver.find_elements(By.CSS_SELECTOR, "[role='dialog'], [class*='modal'], [class*='Modal']")
                if dialogs:
                    print("  Subscribe confirmation dialog appeared")
                    screenshot(driver, "subscribe_confirmation_dialog")
                    for by, val in [(By.XPATH, "//button[contains(text(),'Confirm')]"),
                                    (By.XPATH, "//button[contains(text(),'Yes')]"),
                                    (By.XPATH, "//button[contains(text(),'Subscribe')]"),
                                    (By.XPATH, "//button[contains(text(),'OK')]")]:
                        try:
                            cb = driver.find_element(by, val)
                            if cb.is_displayed():
                                safe_click(driver, cb)
                                time.sleep(3)
                                break
                        except:
                            continue
            except:
                pass

            screenshot(driver, "after_resubscribe_confirmed")
            cycle_result = "completed"
            print("  Subscribe/Unsubscribe cycle completed")
        else:
            cycle_result = "unsubscribe_worked_but_no_resubscribe_button"
            print("  [WARN] No subscribe button found after unsubscribing")
    else:
        print("  No unsubscribe buttons available to test cycle")
        cycle_result = "no_unsubscribe_buttons"

    # ── Check for Free vs Paid module behavior ──
    print("\n[1c] Check free vs paid module subscribe behavior")
    driver.get(f"{BASE_URL}/modules")
    time.sleep(3)

    # Look for pricing/plan indicators in page source
    page_src = driver.page_source.lower()
    has_free_tag = "free" in page_src
    has_paid_tag = any(kw in page_src for kw in ["paid", "premium", "enterprise", "price", "razorpay", "stripe"])
    print(f"  Free tag in source: {has_free_tag}")
    print(f"  Paid/premium tag in source: {has_paid_tag}")

    # Check if any Subscribe button triggers a payment flow
    sub_buttons = driver.find_elements(By.XPATH, "//button[contains(text(),'Subscribe') and not(contains(text(),'Unsubscribe'))]")
    if sub_buttons:
        print(f"  Testing subscribe on first available button...")
        safe_click(driver, sub_buttons[0])
        time.sleep(4)
        screenshot(driver, "subscribe_flow_test")

        # Check for payment/pricing modal
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        src = driver.page_source.lower()
        if any(kw in body_text or kw in src for kw in ["payment", "checkout", "razorpay", "stripe", "card number", "pricing"]):
            print("  Payment flow detected!")
        elif any(kw in body_text for kw in ["select", "plan", "choose", "tier"]):
            print("  Plan selection dialog detected")
            screenshot(driver, "plan_selection_dialog")
        else:
            print("  Direct subscribe (no payment flow) - likely free module")

        # Dismiss any dialogs
        try:
            close_btns = driver.find_elements(By.CSS_SELECTOR, "[class*='close'], button[aria-label='close'], button[aria-label='Close']")
            for cb in close_btns:
                if cb.is_displayed():
                    safe_click(driver, cb)
                    time.sleep(1)
                    break
        except:
            pass
    else:
        print("  All modules already subscribed, no Subscribe buttons to test")

    return {"modules_info": modules_info, "cycle_result": cycle_result}


# ══════════════════════════════════════════════════════════════════════
# TEST 2: Deep Billing Testing
# ══════════════════════════════════════════════════════════════════════
def test_billing_deep(driver):
    print("\n" + "="*70)
    print("  TEST 2: DEEP BILLING TESTING")
    print("="*70)

    results = {}
    driver.get(f"{BASE_URL}/billing")
    time.sleep(3)
    screenshot(driver, "billing_main")

    # ── Check billing tabs: Subscriptions, Invoices, Payments, Overview ──
    tabs = ["Subscriptions", "Invoices", "Payments", "Overview"]
    for tab_name in tabs:
        print(f"\n[2a] Testing Billing Tab: {tab_name}")
        # Find and click tab
        tab_clicked = False
        for by, val in [
            (By.XPATH, f"//button[contains(text(),'{tab_name}')]"),
            (By.XPATH, f"//a[contains(text(),'{tab_name}')]"),
            (By.XPATH, f"//div[contains(text(),'{tab_name}')]"),
            (By.XPATH, f"//*[@role='tab'][contains(text(),'{tab_name}')]"),
            (By.CSS_SELECTOR, f"[data-tab='{tab_name.lower()}']"),
        ]:
            try:
                elems = driver.find_elements(by, val)
                for el in elems:
                    if el.is_displayed():
                        safe_click(driver, el)
                        tab_clicked = True
                        time.sleep(3)
                        break
                if tab_clicked:
                    break
            except:
                continue

        if tab_clicked:
            screenshot(driver, f"billing_tab_{tab_name.lower()}")
            body = driver.find_element(By.TAG_NAME, "body").text
            print(f"  Tab '{tab_name}' content preview: {body[200:500]}")

            # Analyze tab content
            body_lower = body.lower()

            if tab_name == "Subscriptions":
                # Check for subscription details
                has_plan = any(kw in body_lower for kw in ["plan", "basic", "pro", "enterprise", "starter", "free"])
                has_price = any(c in body for c in ["$", "Rs", "INR", "\u20b9"])  # currency symbols
                has_dates = any(kw in body_lower for kw in ["start", "end", "expir", "renew", "due"])
                print(f"    Has plan info: {has_plan}, Has pricing: {has_price}, Has dates: {has_dates}")
                results["subscriptions_tab"] = {"plan": has_plan, "price": has_price, "dates": has_dates}

                # Check for edit/manage subscription buttons
                edit_btns = driver.find_elements(By.CSS_SELECTOR, "[class*='edit'], [class*='Edit'], button svg")
                print(f"    Edit/action buttons found: {len(edit_btns)}")

                # Try clicking an edit button on a subscription
                if edit_btns:
                    for eb in edit_btns[:2]:
                        try:
                            if eb.is_displayed():
                                safe_click(driver, eb)
                                time.sleep(2)
                                screenshot(driver, "subscription_edit_click")
                                # Check what opened
                                dialogs = driver.find_elements(By.CSS_SELECTOR, "[role='dialog'], [class*='modal'], [class*='Modal'], [class*='drawer'], [class*='Drawer']")
                                if dialogs:
                                    print("    Edit dialog/drawer opened")
                                    screenshot(driver, "subscription_edit_dialog")
                                    # Close it
                                    try:
                                        close = driver.find_element(By.CSS_SELECTOR, "[class*='close'], button[aria-label*='lose']")
                                        safe_click(driver, close)
                                        time.sleep(1)
                                    except:
                                        driver.find_element(By.TAG_NAME, "body").click()
                                        time.sleep(1)
                                break
                        except:
                            continue

            elif tab_name == "Invoices":
                has_invoices = any(kw in body_lower for kw in ["invoice", "inv-", "#inv", "download", "pdf"])
                has_table = len(driver.find_elements(By.TAG_NAME, "table")) > 0
                # Check for "no invoices" message
                no_invoices = any(kw in body_lower for kw in ["no invoice", "no data", "empty", "no records"])
                print(f"    Has invoice data: {has_invoices}, Has table: {has_table}, Empty: {no_invoices}")
                results["invoices_tab"] = {"has_data": has_invoices, "has_table": has_table, "empty": no_invoices}

                if no_invoices and not has_invoices:
                    sp = screenshot(driver, "bug_no_invoices")
                    file_bug(
                        "Billing Invoices tab shows no invoice data",
                        "The Invoices tab on the billing page shows no invoice records. "
                        "For an organization with active subscriptions (Rewards & Recognition on Enterprise, "
                        "Recruitment on Basic, Project Management on Basic), there should be invoice records. "
                        "This could indicate invoices are not being generated or the tab is not loading data.\n\n"
                        "**Steps:** Login as Org Admin > Billing > Invoices tab\n"
                        "**Expected:** Invoice records for active subscriptions\n"
                        "**Actual:** No invoices shown",
                        severity="medium", screenshot_path=sp
                    )

            elif tab_name == "Payments":
                has_payments = any(kw in body_lower for kw in ["payment", "transaction", "paid", "amount", "date"])
                no_payments = any(kw in body_lower for kw in ["no payment", "no data", "empty", "no records", "no transaction"])
                print(f"    Has payment data: {has_payments}, Empty: {no_payments}")
                results["payments_tab"] = {"has_data": has_payments, "empty": no_payments}

                if no_payments and not has_payments:
                    sp = screenshot(driver, "bug_no_payments")
                    file_bug(
                        "Billing Payments tab shows no payment history",
                        "The Payments tab on the billing page is empty. "
                        "Organizations with paid subscriptions should have payment records.\n\n"
                        "**Steps:** Login as Org Admin > Billing > Payments tab\n"
                        "**Expected:** Payment history records\n"
                        "**Actual:** No payments shown",
                        severity="medium", screenshot_path=sp
                    )

            elif tab_name == "Overview":
                has_summary = any(kw in body_lower for kw in ["total", "summary", "overview", "cost", "monthly", "annual"])
                print(f"    Has overview/summary: {has_summary}")
                results["overview_tab"] = {"has_summary": has_summary}

        else:
            print(f"  [WARN] Could not find/click tab: {tab_name}")
            results[f"{tab_name.lower()}_tab"] = "not_found"

    # ── Check monthly cost display ──
    print("\n[2b] Verify monthly cost and subscription details")
    driver.get(f"{BASE_URL}/billing")
    time.sleep(3)
    body = driver.find_element(By.TAG_NAME, "body").text
    # From screenshot we saw "Rs 1,00,000.00 /month"
    if any(c in body for c in ["\u20b9", "Rs", "INR", "$"]):
        print(f"  Currency/price info found in billing page")
        # Extract price-like patterns
        import re
        prices = re.findall(r'[\u20b9$][\d,]+\.?\d*|Rs\.?\s*[\d,]+\.?\d*|INR\s*[\d,]+\.?\d*', body)
        for p in prices:
            print(f"    Price found: {p}")
        results["prices"] = prices
    else:
        print("  No currency info found")
        results["prices"] = []

    # ── Check for upgrade/downgrade options ──
    print("\n[2c] Check for plan upgrade/downgrade options")
    upgrade_found = False
    for by, val in [
        (By.XPATH, "//button[contains(text(),'Upgrade')]"),
        (By.XPATH, "//button[contains(text(),'Downgrade')]"),
        (By.XPATH, "//button[contains(text(),'Change Plan')]"),
        (By.XPATH, "//a[contains(text(),'Upgrade')]"),
        (By.CSS_SELECTOR, "[class*='upgrade']"),
    ]:
        try:
            elems = driver.find_elements(by, val)
            for el in elems:
                if el.is_displayed():
                    print(f"  Upgrade/change option: '{el.text.strip()}'")
                    upgrade_found = True
        except:
            continue

    if not upgrade_found:
        print("  No upgrade/downgrade buttons found")
        # This may or may not be a bug -- depends on design
        # Check if there are edit icons (pencil) on subscription cards
        edit_icons = driver.find_elements(By.CSS_SELECTOR, "svg, [class*='edit'], [class*='pencil']")
        clickable_icons = [e for e in edit_icons if e.is_displayed()]
        print(f"  Edit icons on page: {len(clickable_icons)}")

    results["upgrade_available"] = upgrade_found
    return results


# ══════════════════════════════════════════════════════════════════════
# TEST 3: Module Integration - Access modules via known URLs
# ══════════════════════════════════════════════════════════════════════
def test_module_integration(driver):
    print("\n" + "="*70)
    print("  TEST 3: MODULE INTEGRATION VIA KNOWN URLs")
    print("="*70)

    results = {}

    # These are the known module frontend URLs
    module_urls = {
        "Recruit": "https://test-recruit.empcloud.com",
        "Performance": "https://test-performance.empcloud.com",
        "Rewards": "https://test-rewards.empcloud.com",
        "Exit": "https://test-exit.empcloud.com",
        "LMS": "https://testlms.empcloud.com",
        "Payroll": "https://testpayroll.empcloud.com",
        "Project": "https://test-project.empcloud.com",
        "Monitor": "https://test-empmonitor.empcloud.com",
    }

    # First check the dashboard for module insight cards and links
    print("\n[3a] Check dashboard for module links/cards")
    driver.get(BASE_URL)
    time.sleep(3)
    screenshot(driver, "dashboard_for_modules")

    # From the screenshot, the dashboard has "Module Insights" with Recruitment, Performance, Recognition, Exit & Attrition
    body = driver.find_element(By.TAG_NAME, "body").text
    for mod in module_urls:
        if mod.lower() in body.lower():
            print(f"  Module '{mod}' mentioned on dashboard")

    # Check for clickable module cards/links that navigate to subdomain modules
    all_links = driver.find_elements(By.TAG_NAME, "a")
    external_module_links = []
    for link in all_links:
        href = link.get_attribute("href") or ""
        if "empcloud.com" in href and "test-empcloud" not in href and href.startswith("http"):
            txt = link.text.strip()
            if txt:
                external_module_links.append({"text": txt, "href": href})
                print(f"  External module link: {txt} -> {href}")

    if not external_module_links:
        print("  No external module links on dashboard (modules may be accessed via direct URLs)")

    # ── Test each module URL ──
    print("\n[3b] Test module URLs for accessibility")
    for mod_name, mod_url in module_urls.items():
        print(f"\n  Testing: {mod_name} ({mod_url})")
        try:
            driver.get(mod_url)
            time.sleep(5)
            cur_url = driver.current_url
            title = driver.title
            body_text = driver.find_element(By.TAG_NAME, "body").text[:400]
            screenshot(driver, f"module_{mod_name.lower()}")

            print(f"    URL: {cur_url}")
            print(f"    Title: {title}")
            print(f"    Body: {body_text[:120]}")

            # Determine load status
            body_lower = body_text.lower()
            if "login" in body_lower or "sign in" in body_lower or "/login" in cur_url:
                status = "requires_login"
                print(f"    Status: Requires separate login (not SSO)")
            elif "404" in title or "not found" in body_lower:
                status = "not_found"
                print(f"    Status: 404 Not Found")
            elif "error" in body_lower or "500" in title:
                status = "error"
                print(f"    Status: Error page")
            elif len(body_text.strip()) < 10:
                status = "blank"
                print(f"    Status: Blank page")
            else:
                status = "loaded"
                print(f"    Status: Loaded successfully")

            results[mod_name] = {"url": cur_url, "title": title, "status": status}

            if status in ["not_found", "error", "blank"]:
                sp = screenshot(driver, f"bug_module_{mod_name.lower()}_error")
                file_bug(
                    f"Module '{mod_name}' returns {status} at {mod_url}",
                    f"The {mod_name} module at {mod_url} is not loading properly.\n\n"
                    f"**Current URL:** {cur_url}\n**Title:** {title}\n"
                    f"**Body:** {body_text[:200]}\n\n"
                    f"**Expected:** Module should load or redirect to login\n"
                    f"**Actual:** {status}",
                    severity="high", screenshot_path=sp
                )

        except Exception as e:
            print(f"    Error: {e}")
            results[mod_name] = {"status": f"exception: {str(e)[:100]}"}

    # Go back to main app
    driver.get(BASE_URL)
    time.sleep(2)

    # ── Check module settings page ──
    print("\n[3c] Check module-specific settings")
    driver.get(f"{BASE_URL}/settings")
    time.sleep(3)
    screenshot(driver, "settings_main")
    body = driver.find_element(By.TAG_NAME, "body").text

    # Look for module-related settings sections
    settings_items = []
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        txt = link.text.strip()
        href = link.get_attribute("href") or ""
        if "setting" in href.lower() and txt:
            settings_items.append({"text": txt, "href": href})

    if settings_items:
        print(f"  Settings links ({len(settings_items)}):")
        for s in settings_items[:15]:
            print(f"    - {s['text']} -> {s['href']}")
    else:
        print("  No sub-settings links found")

    # Check for module-related settings
    for mod_kw in ["attendance", "leave", "payroll", "recruit", "performance"]:
        if mod_kw in body.lower():
            print(f"  Settings mention: {mod_kw}")

    return results


# ══════════════════════════════════════════════════════════════════════
# TEST 4: Super Admin Module Management
# ══════════════════════════════════════════════════════════════════════
def test_super_admin(driver):
    print("\n" + "="*70)
    print("  TEST 4: SUPER ADMIN - MODULE & BILLING MANAGEMENT")
    print("="*70)

    results = {}

    # ── Super Admin Dashboard ──
    print("\n[4a] Check super admin dashboard")
    driver.get(f"{BASE_URL}/admin/super")
    time.sleep(3)
    screenshot(driver, "super_admin_dashboard")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Title: {driver.title}")
    print(f"  URL: {driver.current_url}")
    print(f"  Body preview: {body[:300]}")

    has_admin = any(kw in body.lower() for kw in ["admin", "organization", "revenue", "platform", "super"])
    results["admin_dashboard"] = has_admin
    print(f"  Admin dashboard loaded: {has_admin}")

    # ── Check admin module/subscription management ──
    print("\n[4b] Check admin-level module/subscription management")
    admin_pages = [
        ("/admin/super", "Super Admin Dashboard"),
        ("/admin/modules", "Admin Modules"),
        ("/admin/subscriptions", "Admin Subscriptions"),
        ("/admin/billing", "Admin Billing"),
        ("/admin/plans", "Admin Plans"),
        ("/admin/organizations", "Admin Organizations"),
    ]
    for url_path, name in admin_pages:
        driver.get(f"{BASE_URL}{url_path}")
        time.sleep(3)
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        cur = driver.current_url
        if url_path in cur or any(kw in body for kw in ["admin", "module", "subscription", "organization", "plan", "revenue"]):
            print(f"  {name}: ACCESSIBLE at {cur}")
            screenshot(driver, f"admin_{url_path.replace('/', '_')}")
            results[url_path] = "accessible"
        else:
            print(f"  {name}: NOT FOUND (redirected to {cur})")
            results[url_path] = "not_found"

    # ── Check revenue/billing from admin perspective ──
    print("\n[4c] Check admin revenue overview")
    driver.get(f"{BASE_URL}/admin/super")
    time.sleep(3)
    body = driver.find_element(By.TAG_NAME, "body").text
    revenue_keywords = ["revenue", "mrr", "arr", "total", "income", "earning", "billing"]
    found_revenue = [kw for kw in revenue_keywords if kw in body.lower()]
    print(f"  Revenue keywords on admin page: {found_revenue}")
    results["revenue_keywords"] = found_revenue

    return results


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════
def main():
    print("="*70)
    print("  EMP CLOUD - MARKETPLACE & BILLING E2E TEST (PASS 2)")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    all_results = {}
    driver = None

    try:
        driver = get_driver()
        print("  Chrome driver initialized")

        # ── Org Admin Tests ──
        login(driver, ORG_ADMIN_EMAIL, ORG_ADMIN_PASS, "org_admin")
        all_results["marketplace_deep"] = test_marketplace_deep(driver)
        all_results["billing_deep"] = test_billing_deep(driver)
        all_results["module_integration"] = test_module_integration(driver)

        # ── Super Admin Tests ──
        logout(driver)
        time.sleep(2)
        login(driver, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASS, "super_admin")
        all_results["super_admin"] = test_super_admin(driver)

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        traceback.print_exc()
        if driver:
            screenshot(driver, "fatal_error")
    finally:
        if driver:
            driver.quit()

    # ── Summary ──
    print("\n" + "="*70)
    print("  PASS 2 - TEST SUMMARY")
    print("="*70)

    print(f"\n  Bugs filed: {len(bugs)}")
    for b in bugs:
        print(f"    [{b['severity'].upper()}] {b['title']}")
        print(f"           Issue: {b['issue_url']}")

    # Marketplace
    mp = all_results.get("marketplace_deep", {})
    mods = mp.get("modules_info", [])
    print(f"\n  Marketplace Modules ({len(mods)}):")
    for m in mods:
        print(f"    {m['status']:15s} | {m['tier']:7s} | {m['text_preview'][:80]}")
    print(f"  Subscribe/Unsubscribe cycle: {mp.get('cycle_result', 'N/A')}")

    # Billing
    bl = all_results.get("billing_deep", {})
    for tab in ["subscriptions_tab", "invoices_tab", "payments_tab", "overview_tab"]:
        val = bl.get(tab, "N/A")
        print(f"  Billing {tab}: {val}")
    print(f"  Prices found: {bl.get('prices', [])}")
    print(f"  Upgrade available: {bl.get('upgrade_available', 'N/A')}")

    # Module Integration
    mi = all_results.get("module_integration", {})
    print(f"\n  Module Integration:")
    for mod, info in mi.items():
        if isinstance(info, dict):
            print(f"    {mod}: {info.get('status', 'N/A')}")

    # Super Admin
    sa = all_results.get("super_admin", {})
    print(f"\n  Super Admin:")
    for k, v in sa.items():
        print(f"    {k}: {v}")

    print(f"\n  Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


if __name__ == "__main__":
    main()
