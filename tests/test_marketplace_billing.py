"""
EMP Cloud HRMS - Module Marketplace & Billing E2E Test
Tests: Module listing, subscribe/unsubscribe, billing dashboard, module integration
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

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
ORG_ADMIN_EMAIL = "ananya@technova.in"
ORG_ADMIN_PASS = "Welcome@123"
SUPER_ADMIN_EMAIL = "admin@empcloud.com"
SUPER_ADMIN_PASS = "SuperAdmin@2026"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\marketplace"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── Helpers ─────────────────────────────────────────────────────────────────
bugs = []

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-web-security")
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
    full_body = f"**Severity:** {severity.upper()}\n**Found by:** Automated E2E Test\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n**URL:** {BASE_URL}\n\n{body}"
    if screenshot_path:
        fname = os.path.basename(screenshot_path)
        full_body += f"\n\n**Screenshot:** `{fname}` (attached to test artifacts)"
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

def wait_and_find(driver, by, value, timeout=12):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))

def wait_clickable(driver, by, value, timeout=12):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))

def safe_click(driver, element):
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)

def login(driver, email, password, role="user"):
    print(f"\n{'='*60}")
    print(f"  Logging in as {role}: {email}")
    print(f"{'='*60}")
    driver.get(BASE_URL)
    time.sleep(3)
    screenshot(driver, f"login_page_{role}")

    # Check if already on dashboard (session might persist)
    if "/dashboard" in driver.current_url or "/home" in driver.current_url:
        print("  Already logged in, logging out first...")
        try:
            driver.get(f"{BASE_URL}/login")
            time.sleep(2)
        except:
            pass

    # Try multiple selectors for email field
    email_sel = [
        (By.ID, "email"), (By.NAME, "email"), (By.ID, "username"),
        (By.NAME, "username"), (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, "input[type='text']"), (By.CSS_SELECTOR, "input[placeholder*='mail']"),
        (By.CSS_SELECTOR, "input[placeholder*='Email']"),
        (By.XPATH, "//input[@type='email' or @type='text'][1]"),
    ]
    email_field = None
    for by, val in email_sel:
        try:
            email_field = WebDriverWait(driver, 5).until(EC.presence_of_element_located((by, val)))
            if email_field.is_displayed():
                break
            email_field = None
        except:
            email_field = None

    if not email_field:
        # Dump page for debug
        screenshot(driver, f"login_no_email_field_{role}")
        print(f"  [ERROR] Could not find email input. URL: {driver.current_url}")
        print(f"  Page title: {driver.title}")
        # Try finding all inputs
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for i, inp in enumerate(inputs):
            print(f"    input[{i}]: type={inp.get_attribute('type')} name={inp.get_attribute('name')} id={inp.get_attribute('id')} placeholder={inp.get_attribute('placeholder')}")
        raise Exception("Cannot find email field on login page")

    email_field.clear()
    email_field.send_keys(email)

    # Find password field
    pass_sel = [
        (By.ID, "password"), (By.NAME, "password"),
        (By.CSS_SELECTOR, "input[type='password']"),
    ]
    pass_field = None
    for by, val in pass_sel:
        try:
            pass_field = driver.find_element(by, val)
            if pass_field.is_displayed():
                break
            pass_field = None
        except:
            pass_field = None

    if not pass_field:
        raise Exception("Cannot find password field on login page")

    pass_field.clear()
    pass_field.send_keys(password)

    # Click login button
    btn_sel = [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button[contains(text(),'Login')]"),
        (By.XPATH, "//button[contains(text(),'Sign')]"),
        (By.XPATH, "//button[contains(text(),'Log')]"),
        (By.CSS_SELECTOR, "button.login-btn"),
        (By.CSS_SELECTOR, "input[type='submit']"),
    ]
    for by, val in btn_sel:
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
    return driver

def collect_sidebar_items(driver):
    """Collect all sidebar/nav menu items."""
    items = []
    selectors = [
        "nav a", ".sidebar a", ".side-menu a", ".nav-menu a",
        "[class*='sidebar'] a", "[class*='nav'] a", ".menu-item a",
        "[role='navigation'] a", ".ant-menu a", ".MuiDrawer-root a",
    ]
    for sel in selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elems:
                txt = el.text.strip()
                href = el.get_attribute("href") or ""
                if txt and len(txt) > 1:
                    items.append({"text": txt, "href": href})
        except:
            continue
    # Deduplicate
    seen = set()
    unique = []
    for it in items:
        key = it["text"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique

# ── TEST: Module Marketplace ────────────────────────────────────────────────
def test_module_marketplace(driver):
    print("\n" + "="*70)
    print("  TEST: MODULE MARKETPLACE")
    print("="*70)

    results = {"modules_found": [], "subscribe_free": None, "subscribe_paid": None,
               "unsubscribe": None, "sidebar_after_sub": None}

    # ── 1. Navigate to module marketplace ──
    print("\n[STEP 1] Navigate to module marketplace")
    marketplace_urls = [
        "/modules", "/marketplace", "/module-marketplace", "/subscription/modules",
        "/settings/modules", "/admin/modules", "/billing/modules",
        "/subscription", "/settings/subscription", "/plans",
    ]
    found_marketplace = False
    for url_path in marketplace_urls:
        full = f"{BASE_URL}{url_path}"
        print(f"  Trying: {full}")
        driver.get(full)
        time.sleep(3)
        # Check if we got a real page (not 404 or redirect to home)
        cur = driver.current_url
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if any(kw in body_text for kw in ["module", "marketplace", "subscribe", "plan", "pricing", "addon"]):
            print(f"  Found marketplace at: {cur}")
            found_marketplace = True
            screenshot(driver, "marketplace_found")
            break
        # Also check page source for module-related content
        src = driver.page_source.lower()
        if any(kw in src for kw in ["module-card", "module_card", "subscription-card", "pricing-card"]):
            print(f"  Found marketplace (via page source) at: {cur}")
            found_marketplace = True
            screenshot(driver, "marketplace_found_src")
            break

    if not found_marketplace:
        # Try finding via sidebar links
        print("  Trying to find marketplace via sidebar navigation...")
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(3)
        sidebar_items = collect_sidebar_items(driver)
        print(f"  Sidebar items found: {len(sidebar_items)}")
        for it in sidebar_items:
            print(f"    - {it['text']} -> {it['href']}")

        marketplace_keywords = ["module", "marketplace", "subscription", "plan", "billing", "addon", "add-on"]
        for it in sidebar_items:
            if any(kw in it["text"].lower() for kw in marketplace_keywords):
                print(f"  Clicking sidebar: {it['text']}")
                try:
                    driver.get(it["href"])
                    time.sleep(3)
                    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                    if any(kw in body_text for kw in ["module", "subscribe", "plan", "pricing"]):
                        found_marketplace = True
                        screenshot(driver, "marketplace_via_sidebar")
                        break
                except:
                    continue

    if not found_marketplace:
        print("  [WARN] Module marketplace page not found via direct URLs or sidebar.")
        screenshot(driver, "marketplace_not_found")
        sp = screenshot(driver, "bug_marketplace_not_found")
        file_bug(
            "Module Marketplace page not discoverable",
            "Attempted multiple URLs (/modules, /marketplace, /module-marketplace, "
            "/subscription/modules, /settings/modules, etc.) and sidebar navigation. "
            "Could not find a dedicated module marketplace page. "
            "The marketplace should be easily accessible for org admins.",
            severity="high", screenshot_path=sp
        )
        # Fall back: try to find modules from the existing page
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(3)

    # ── 2. List available modules ──
    print("\n[STEP 2] List available modules and their status")
    # Try to detect modules from the page
    body_text = driver.find_element(By.TAG_NAME, "body").text
    screenshot(driver, "modules_listing_page")

    # Try card-based module listings
    module_selectors = [
        "[class*='module']", "[class*='Module']", "[class*='card']",
        "[class*='subscription']", "[class*='plan']", "[class*='pricing']",
        ".card", ".ant-card", ".MuiCard-root",
    ]
    module_cards = []
    for sel in module_selectors:
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(cards) >= 2:  # Likely found module cards
                module_cards = cards
                print(f"  Found {len(cards)} potential module cards with selector: {sel}")
                break
        except:
            continue

    known_modules = ["Recruit", "Performance", "Rewards", "Exit", "LMS", "Payroll", "Project", "Monitor",
                     "Attendance", "Leave", "Employee", "Core HR", "Documents", "Helpdesk"]

    found_modules = []
    for mod_name in known_modules:
        if mod_name.lower() in body_text.lower():
            # Determine status
            status = "unknown"
            # Check surrounding context
            text_lower = body_text.lower()
            idx = text_lower.find(mod_name.lower())
            if idx >= 0:
                context = text_lower[max(0, idx-100):idx+200]
                if "subscribed" in context or "active" in context or "enabled" in context:
                    status = "subscribed"
                elif "free" in context:
                    status = "free"
                elif "unsubscribed" in context or "inactive" in context or "disabled" in context:
                    status = "not_subscribed"
                elif "subscribe" in context or "buy" in context or "purchase" in context:
                    status = "available"
            found_modules.append({"name": mod_name, "status": status})
            print(f"    Module: {mod_name} - Status: {status}")

    if not found_modules:
        print("  No known modules detected in page text.")
        # Check sidebar for module names
        sidebar_items = collect_sidebar_items(driver)
        for it in sidebar_items:
            for mod_name in known_modules:
                if mod_name.lower() in it["text"].lower():
                    found_modules.append({"name": mod_name, "status": "in_sidebar"})
                    print(f"    Module (sidebar): {mod_name} -> {it['href']}")

    results["modules_found"] = found_modules
    print(f"  Total modules detected: {len(found_modules)}")

    # ── 3. Try subscribing to a free module ──
    print("\n[STEP 3] Try subscribing to a free module")
    subscribe_btns = []
    btn_selectors = [
        (By.XPATH, "//button[contains(text(),'Subscribe')]"),
        (By.XPATH, "//button[contains(text(),'subscribe')]"),
        (By.XPATH, "//a[contains(text(),'Subscribe')]"),
        (By.XPATH, "//button[contains(text(),'Enable')]"),
        (By.XPATH, "//button[contains(text(),'Activate')]"),
        (By.XPATH, "//button[contains(text(),'Add')]"),
        (By.XPATH, "//button[contains(text(),'Try')]"),
        (By.XPATH, "//button[contains(text(),'Free')]"),
        (By.CSS_SELECTOR, "[class*='subscribe']"),
        (By.CSS_SELECTOR, "button[class*='activate']"),
    ]
    for by, val in btn_selectors:
        try:
            btns = driver.find_elements(by, val)
            for b in btns:
                if b.is_displayed():
                    subscribe_btns.append(b)
        except:
            continue

    print(f"  Found {len(subscribe_btns)} subscribe/activate buttons")
    if subscribe_btns:
        try:
            btn = subscribe_btns[0]
            btn_text = btn.text.strip()
            print(f"  Clicking: '{btn_text}'")
            screenshot(driver, "before_subscribe_click")
            safe_click(driver, btn)
            time.sleep(4)
            screenshot(driver, "after_subscribe_click")
            print(f"  URL after click: {driver.current_url}")
            body_after = driver.find_element(By.TAG_NAME, "body").text.lower()
            if any(kw in body_after for kw in ["success", "subscribed", "activated", "enabled", "payment", "checkout"]):
                results["subscribe_free"] = "button_found_and_clicked"
                print("  Subscribe action triggered successfully")
            else:
                results["subscribe_free"] = "button_clicked_unclear_result"
                print("  Clicked but outcome unclear")
        except Exception as e:
            results["subscribe_free"] = f"error: {e}"
            print(f"  Error clicking subscribe: {e}")
    else:
        results["subscribe_free"] = "no_subscribe_buttons_found"
        print("  No subscribe buttons found on page")

    # ── 4. Try subscribing to a paid module — check payment flow ──
    print("\n[STEP 4] Check payment flow for paid modules")
    # Look for paid module indicators
    paid_keywords = ["price", "pricing", "payment", "checkout", "razorpay", "stripe", "pay now",
                     "buy now", "upgrade", "premium", "pro", "enterprise"]
    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    page_src = driver.page_source.lower()

    has_payment = any(kw in body_text or kw in page_src for kw in paid_keywords)
    print(f"  Payment-related content found: {has_payment}")

    if has_payment:
        # Try to find and click a paid module's subscribe button
        paid_btns = []
        try:
            paid_btns = driver.find_elements(By.XPATH, "//button[contains(text(),'Buy') or contains(text(),'Upgrade') or contains(text(),'Pay')]")
        except:
            pass
        if paid_btns:
            try:
                btn = paid_btns[0]
                print(f"  Clicking paid option: '{btn.text.strip()}'")
                screenshot(driver, "before_paid_subscribe")
                safe_click(driver, btn)
                time.sleep(5)
                screenshot(driver, "after_paid_subscribe")
                cur = driver.current_url
                new_body = driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(kw in cur.lower() or kw in new_body for kw in ["payment", "checkout", "razorpay", "stripe", "card"]):
                    results["subscribe_paid"] = "payment_flow_triggered"
                    print("  Payment flow detected!")
                else:
                    results["subscribe_paid"] = "clicked_but_no_payment_flow"
                    print("  Clicked but no payment gateway detected")
            except Exception as e:
                results["subscribe_paid"] = f"error: {e}"
        else:
            results["subscribe_paid"] = "no_paid_buttons_found"
    else:
        results["subscribe_paid"] = "no_payment_content_on_page"
        print("  No payment-related content found on the page")

    # ── 5. Check sidebar after subscription ──
    print("\n[STEP 5] Check sidebar for subscribed modules")
    driver.get(f"{BASE_URL}/dashboard")
    time.sleep(3)
    sidebar_items = collect_sidebar_items(driver)
    screenshot(driver, "sidebar_after_subscription")
    print(f"  Sidebar items ({len(sidebar_items)}):")
    sidebar_module_names = []
    for it in sidebar_items:
        print(f"    - {it['text']} -> {it['href']}")
        sidebar_module_names.append(it["text"])
    results["sidebar_after_sub"] = sidebar_module_names

    # ── 6. Try unsubscribing (Issue #50 — missing unsubscribe option) ──
    print("\n[STEP 6] Try unsubscribing from a module (Issue #50)")
    # Navigate back to marketplace/modules
    for url_path in ["/modules", "/marketplace", "/subscription", "/settings/modules", "/billing"]:
        driver.get(f"{BASE_URL}{url_path}")
        time.sleep(2)
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        if any(kw in body for kw in ["module", "subscribe", "plan"]):
            break

    unsub_selectors = [
        (By.XPATH, "//button[contains(text(),'Unsubscribe')]"),
        (By.XPATH, "//button[contains(text(),'unsubscribe')]"),
        (By.XPATH, "//button[contains(text(),'Cancel')]"),
        (By.XPATH, "//button[contains(text(),'Deactivate')]"),
        (By.XPATH, "//button[contains(text(),'Disable')]"),
        (By.XPATH, "//button[contains(text(),'Remove')]"),
        (By.XPATH, "//a[contains(text(),'Unsubscribe')]"),
        (By.CSS_SELECTOR, "[class*='unsubscribe']"),
        (By.CSS_SELECTOR, "[class*='cancel-sub']"),
    ]
    unsub_found = False
    for by, val in unsub_selectors:
        try:
            elems = driver.find_elements(by, val)
            for el in elems:
                if el.is_displayed():
                    unsub_found = True
                    print(f"  Unsubscribe option found: '{el.text.strip()}'")
                    screenshot(driver, "unsubscribe_option_found")
                    break
            if unsub_found:
                break
        except:
            continue

    if not unsub_found:
        print("  [BUG] No unsubscribe option found (confirms Issue #50)")
        sp = screenshot(driver, "bug_no_unsubscribe_option")
        results["unsubscribe"] = "not_found"
        file_bug(
            "No unsubscribe option available for subscribed modules (ref #50)",
            "After navigating to module marketplace/subscription pages, no unsubscribe, "
            "cancel, deactivate, or disable button/link is visible for any subscribed module. "
            "This confirms the issue reported in #50. Org admins should be able to unsubscribe "
            "from modules they no longer need.\n\n"
            "**Steps to reproduce:**\n"
            "1. Login as Org Admin\n"
            "2. Navigate to module/subscription management\n"
            "3. Look for unsubscribe/cancel option on subscribed modules\n"
            "4. No such option exists\n\n"
            "**Expected:** An unsubscribe or cancel button for each subscribed module\n"
            "**Actual:** No way to unsubscribe",
            severity="high", screenshot_path=sp
        )
    else:
        results["unsubscribe"] = "found"

    return results

# ── TEST: Billing Dashboard ─────────────────────────────────────────────────
def test_billing(driver):
    print("\n" + "="*70)
    print("  TEST: BILLING DASHBOARD")
    print("="*70)

    results = {"billing_page_found": False, "plan_info": None, "invoices": None, "metrics": None}

    # ── 1. Navigate to billing ──
    print("\n[STEP 1] Navigate to billing page")
    billing_urls = [
        "/billing", "/subscription/billing", "/settings/billing",
        "/account/billing", "/admin/billing", "/payments",
        "/invoices", "/settings/subscription", "/plans",
        "/subscription", "/pricing",
    ]
    found_billing = False
    for url_path in billing_urls:
        full = f"{BASE_URL}{url_path}"
        print(f"  Trying: {full}")
        driver.get(full)
        time.sleep(3)
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if any(kw in body_text for kw in ["billing", "invoice", "plan", "subscription", "payment", "usage"]):
            print(f"  Found billing at: {driver.current_url}")
            found_billing = True
            results["billing_page_found"] = True
            screenshot(driver, "billing_page_found")
            break

    if not found_billing:
        # Try via sidebar
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(3)
        sidebar = collect_sidebar_items(driver)
        billing_kw = ["billing", "invoice", "payment", "subscription", "plan"]
        for it in sidebar:
            if any(kw in it["text"].lower() for kw in billing_kw):
                print(f"  Trying sidebar: {it['text']} -> {it['href']}")
                try:
                    driver.get(it["href"])
                    time.sleep(3)
                    body = driver.find_element(By.TAG_NAME, "body").text.lower()
                    if any(kw in body for kw in billing_kw):
                        found_billing = True
                        results["billing_page_found"] = True
                        screenshot(driver, "billing_via_sidebar")
                        break
                except:
                    continue

    if not found_billing:
        print("  [BUG] Billing page not found")
        sp = screenshot(driver, "bug_billing_not_found")
        file_bug(
            "Billing page not accessible for Org Admin",
            "Tried multiple billing URLs (/billing, /subscription/billing, /settings/billing, "
            "/account/billing, etc.) and sidebar navigation. No billing page could be found. "
            "Org Admins should have access to view their billing information, current plan, "
            "and invoices.",
            severity="high", screenshot_path=sp
        )

    # ── 2. Check billing dashboard content ──
    print("\n[STEP 2] Check billing dashboard — plan, usage, invoices")
    body_text = driver.find_element(By.TAG_NAME, "body").text
    screenshot(driver, "billing_dashboard_content")

    # Check for plan info
    plan_keywords = ["plan", "tier", "subscription", "current plan", "free", "basic", "pro", "enterprise", "starter"]
    plan_found = [kw for kw in plan_keywords if kw in body_text.lower()]
    results["plan_info"] = plan_found if plan_found else None
    print(f"  Plan-related keywords found: {plan_found}")

    # Check for invoices
    invoice_keywords = ["invoice", "receipt", "bill", "transaction", "payment history"]
    invoice_found = [kw for kw in invoice_keywords if kw in body_text.lower()]
    results["invoices"] = invoice_found if invoice_found else None
    print(f"  Invoice-related keywords found: {invoice_found}")

    # Check for usage metrics
    usage_keywords = ["usage", "employee", "user", "seat", "storage", "api call", "limit", "quota"]
    usage_found = [kw for kw in usage_keywords if kw in body_text.lower()]
    results["metrics"] = usage_found if usage_found else None
    print(f"  Usage metric keywords found: {usage_found}")

    if not plan_found and found_billing:
        sp = screenshot(driver, "bug_billing_no_plan_info")
        file_bug(
            "Billing page missing current plan information",
            "The billing page does not display the current subscription plan, "
            "tier, or plan name. Users should be able to see their active plan details.",
            severity="medium", screenshot_path=sp
        )

    if not invoice_found and found_billing:
        sp = screenshot(driver, "bug_billing_no_invoices")
        file_bug(
            "Billing page missing invoice/payment history",
            "The billing page does not show any invoice or payment history section. "
            "Users should be able to view past invoices and payment records.",
            severity="medium", screenshot_path=sp
        )

    # ── 3. Check subscription metrics ──
    print("\n[STEP 3] Check subscription metrics")
    # Look for tables or metric cards
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"  Tables on page: {len(tables)}")
    for i, tbl in enumerate(tables):
        try:
            rows = tbl.find_elements(By.TAG_NAME, "tr")
            print(f"    Table {i}: {len(rows)} rows")
            for j, row in enumerate(rows[:5]):
                print(f"      Row {j}: {row.text[:120]}")
        except:
            pass

    # ── 4. Test billing forms ──
    print("\n[STEP 4] Test billing-related forms")
    forms = driver.find_elements(By.TAG_NAME, "form")
    print(f"  Forms on billing page: {len(forms)}")
    for i, form in enumerate(forms):
        try:
            inputs = form.find_elements(By.TAG_NAME, "input")
            btns = form.find_elements(By.TAG_NAME, "button")
            print(f"    Form {i}: {len(inputs)} inputs, {len(btns)} buttons")
        except:
            pass

    # Look for upgrade/change plan buttons
    upgrade_btns = []
    for by, val in [
        (By.XPATH, "//button[contains(text(),'Upgrade')]"),
        (By.XPATH, "//button[contains(text(),'Change')]"),
        (By.XPATH, "//button[contains(text(),'Manage')]"),
        (By.XPATH, "//a[contains(text(),'Upgrade')]"),
        (By.XPATH, "//a[contains(text(),'Change Plan')]"),
    ]:
        try:
            elems = driver.find_elements(by, val)
            upgrade_btns.extend([e for e in elems if e.is_displayed()])
        except:
            pass

    if upgrade_btns:
        print(f"  Found {len(upgrade_btns)} upgrade/change buttons")
        for b in upgrade_btns[:2]:
            print(f"    Button: '{b.text.strip()}'")
    else:
        print("  No upgrade/change plan buttons found")

    return results

# ── TEST: Module Integration ────────────────────────────────────────────────
def test_module_integration(driver):
    print("\n" + "="*70)
    print("  TEST: MODULE INTEGRATION")
    print("="*70)

    results = {"sidebar_modules": [], "module_loads": {}, "module_settings": {}}

    # ── 1. Verify modules in sidebar ──
    print("\n[STEP 1] Check modules accessible from sidebar")
    driver.get(f"{BASE_URL}/dashboard")
    time.sleep(3)

    sidebar_items = collect_sidebar_items(driver)
    screenshot(driver, "dashboard_sidebar_full")

    known_modules_urls = {
        "recruit": "https://test-recruit.empcloud.com",
        "performance": "https://test-performance.empcloud.com",
        "rewards": "https://test-rewards.empcloud.com",
        "exit": "https://test-exit.empcloud.com",
        "lms": "https://testlms.empcloud.com",
        "payroll": "https://testpayroll.empcloud.com",
        "project": "https://test-project.empcloud.com",
        "monitor": "https://test-empmonitor.empcloud.com",
    }

    module_sidebar_items = []
    for it in sidebar_items:
        for mod_key in known_modules_urls:
            if mod_key in it["text"].lower() or mod_key in it.get("href", "").lower():
                module_sidebar_items.append({"name": mod_key, "text": it["text"], "href": it["href"]})
                print(f"  Module in sidebar: {it['text']} -> {it['href']}")

    results["sidebar_modules"] = module_sidebar_items

    if not module_sidebar_items:
        print("  No known module links found in sidebar. Checking for any external links...")
        for it in sidebar_items:
            href = it.get("href", "")
            if "empcloud.com" in href and BASE_URL not in href:
                module_sidebar_items.append({"name": "unknown", "text": it["text"], "href": href})
                print(f"  External module link: {it['text']} -> {href}")

    # ── 2. Click module in sidebar, verify it loads ──
    print("\n[STEP 2] Test module loading from sidebar clicks")
    test_count = min(3, len(module_sidebar_items))  # Test up to 3 modules
    for i in range(test_count):
        mod = module_sidebar_items[i]
        print(f"\n  Testing module: {mod['text']}")
        try:
            # Navigate to the module URL
            target_url = mod["href"]
            driver.get(target_url)
            time.sleep(5)
            cur_url = driver.current_url
            print(f"    Loaded URL: {cur_url}")
            screenshot(driver, f"module_load_{mod['name']}")

            page_title = driver.title
            body_text = driver.find_element(By.TAG_NAME, "body").text[:300]
            print(f"    Page title: {page_title}")
            print(f"    Body preview: {body_text[:150]}")

            # Check if page loaded properly
            if "error" in body_text.lower() or "not found" in body_text.lower() or "404" in page_title.lower():
                results["module_loads"][mod["name"]] = "error_page"
                sp = screenshot(driver, f"bug_module_error_{mod['name']}")
                file_bug(
                    f"Module '{mod['text']}' shows error page when accessed from sidebar",
                    f"Clicking '{mod['text']}' in the sidebar navigates to {target_url} "
                    f"but the page shows an error. Current URL: {cur_url}\n"
                    f"Page title: {page_title}\nBody: {body_text[:200]}",
                    severity="high", screenshot_path=sp
                )
            elif len(body_text.strip()) < 20:
                results["module_loads"][mod["name"]] = "blank_page"
                sp = screenshot(driver, f"bug_module_blank_{mod['name']}")
                file_bug(
                    f"Module '{mod['text']}' shows blank page",
                    f"Clicking '{mod['text']}' in the sidebar shows an empty/blank page. "
                    f"URL: {cur_url}",
                    severity="high", screenshot_path=sp
                )
            else:
                results["module_loads"][mod["name"]] = "loaded"
                print(f"    Module loaded successfully")

            # Check for iframes (some modules may load via iframe)
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                print(f"    Found {len(iframes)} iframe(s)")
                for idx, iframe in enumerate(iframes):
                    src = iframe.get_attribute("src") or ""
                    print(f"      iframe[{idx}] src: {src[:100]}")

        except Exception as e:
            results["module_loads"][mod["name"]] = f"exception: {str(e)[:100]}"
            print(f"    Error: {e}")

        # Go back to main dashboard for next test
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(2)

    # ── 3. Test module-specific settings ──
    print("\n[STEP 3] Test module-specific settings")
    settings_urls = ["/settings", "/settings/modules", "/admin/settings"]
    for url_path in settings_urls:
        driver.get(f"{BASE_URL}{url_path}")
        time.sleep(3)
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "setting" in body:
            screenshot(driver, f"settings_page_{url_path.replace('/', '_')}")
            print(f"  Settings page found at: {url_path}")

            # Look for module-specific settings sections
            for mod_name in ["recruit", "performance", "payroll", "leave", "attendance"]:
                if mod_name in body:
                    print(f"    Module settings found for: {mod_name}")
                    results["module_settings"][mod_name] = True
            break

    return results

# ── TEST: Super Admin Module Management ──────────────────────────────────────
def test_super_admin_modules(driver):
    print("\n" + "="*70)
    print("  TEST: SUPER ADMIN - MODULE MANAGEMENT")
    print("="*70)

    results = {"admin_module_page": False, "org_modules": None}

    # Navigate to super admin module management
    admin_urls = [
        "/admin/super", "/admin/modules", "/admin/subscriptions",
        "/admin/organizations", "/admin/billing", "/admin/plans",
    ]
    for url_path in admin_urls:
        driver.get(f"{BASE_URL}{url_path}")
        time.sleep(3)
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        cur = driver.current_url
        if any(kw in body for kw in ["admin", "organization", "module", "subscription", "plan", "revenue"]):
            print(f"  Admin page found: {cur}")
            screenshot(driver, f"superadmin_{url_path.replace('/', '_')}")
            results["admin_module_page"] = True

            # Look for org module management
            if "organization" in body or "tenant" in body:
                results["org_modules"] = "found"
                print("  Organization/tenant management visible")

    return results

# ── MAIN RUNNER ─────────────────────────────────────────────────────────────
def main():
    print("="*70)
    print("  EMP CLOUD HRMS - MODULE MARKETPLACE & BILLING E2E TEST")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    all_results = {}
    driver = None

    try:
        driver = get_driver()
        print(f"  Chrome driver initialized")

        # ── Part 1: Org Admin — Marketplace & Billing ──
        login(driver, ORG_ADMIN_EMAIL, ORG_ADMIN_PASS, "org_admin")
        all_results["marketplace"] = test_module_marketplace(driver)
        all_results["billing"] = test_billing(driver)
        all_results["integration"] = test_module_integration(driver)

        # ── Part 2: Super Admin — Module Management ──
        # Clear cookies and login as super admin
        driver.delete_all_cookies()
        time.sleep(1)
        login(driver, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASS, "super_admin")
        all_results["super_admin"] = test_super_admin_modules(driver)

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
    print("  TEST SUMMARY")
    print("="*70)

    print(f"\n  Bugs filed: {len(bugs)}")
    for b in bugs:
        print(f"    [{b['severity'].upper()}] {b['title']}")
        print(f"           Issue: {b['issue_url']}")

    print(f"\n  Marketplace Results:")
    mp = all_results.get("marketplace", {})
    print(f"    Modules found: {len(mp.get('modules_found', []))}")
    for m in mp.get("modules_found", []):
        print(f"      - {m['name']}: {m['status']}")
    print(f"    Free subscribe: {mp.get('subscribe_free', 'N/A')}")
    print(f"    Paid subscribe: {mp.get('subscribe_paid', 'N/A')}")
    print(f"    Unsubscribe: {mp.get('unsubscribe', 'N/A')}")

    print(f"\n  Billing Results:")
    bl = all_results.get("billing", {})
    print(f"    Page found: {bl.get('billing_page_found', False)}")
    print(f"    Plan info: {bl.get('plan_info', 'N/A')}")
    print(f"    Invoices: {bl.get('invoices', 'N/A')}")
    print(f"    Metrics: {bl.get('metrics', 'N/A')}")

    print(f"\n  Integration Results:")
    integ = all_results.get("integration", {})
    print(f"    Sidebar modules: {len(integ.get('sidebar_modules', []))}")
    for name, status in integ.get("module_loads", {}).items():
        print(f"      {name}: {status}")

    print(f"\n  Super Admin Results:")
    sa = all_results.get("super_admin", {})
    print(f"    Admin module page: {sa.get('admin_module_page', False)}")

    print(f"\n  Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

if __name__ == "__main__":
    main()
