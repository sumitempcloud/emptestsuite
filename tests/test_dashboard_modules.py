#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EMP Cloud HRMS - Full Dashboard Sidebar Mapping & Module Testing
Tests all sidebar links, sub-menus, module accessibility, and reports bugs.
"""

import sys
import os
import time
import json
import re
import traceback
import urllib.request
import urllib.error
import base64
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, ElementClickInterceptedException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
ORG_ADMIN_EMAIL = "ananya@technova.in"
ORG_ADMIN_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\dashboard_modules"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

EXPECTED_MODULES = [
    "Core HRMS", "Employee Monitoring", "Rewards & Recognition",
    "Recruitment / ATS", "Billing", "Exit Management",
    "LMS / Learning", "Payroll", "Performance Management",
    "Project Management", "Field Force", "Biometrics"
]

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ─── Data Classes ─────────────────────────────────────────────────────────────
@dataclass
class SidebarLink:
    text: str
    href: str
    level: int = 0  # 0=top, 1=sub-menu
    parent: str = ""
    navigated_url: str = ""
    status: str = "untested"  # ok, broken, blank, error, redirect, subdomain
    error_detail: str = ""
    screenshot_path: str = ""
    js_errors: list = field(default_factory=list)
    has_error_toast: bool = False

@dataclass
class BugReport:
    title: str
    description: str
    severity: str  # critical, high, medium, low
    screenshot_path: str = ""
    url: str = ""
    github_issue_url: str = ""

# ─── Globals ──────────────────────────────────────────────────────────────────
sidebar_links: list[SidebarLink] = []
bugs: list[BugReport] = []
driver = None

# ─── Helper Functions ─────────────────────────────────────────────────────────
def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)


def screenshot(name):
    safe = re.sub(r'[^\w\-.]', '_', name)[:80]
    ts = datetime.now().strftime("%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"{safe}_{ts}.png")
    try:
        driver.save_screenshot(path)
        print(f"  [screenshot] {path}")
        return path
    except Exception as e:
        print(f"  [screenshot-fail] {e}")
        return ""


def get_js_errors():
    errors = []
    try:
        logs = driver.get_log("browser")
        for entry in logs:
            if entry.get("level") in ("SEVERE",):
                msg = entry.get("message", "")
                if "favicon" not in msg.lower():
                    errors.append(msg)
    except Exception:
        pass
    return errors


def check_error_toasts():
    """Check for visible error toasts/banners on the page."""
    selectors = [
        ".Toastify__toast--error",
        ".toast-error",
        "[class*='error-toast']",
        "[class*='error-banner']",
        ".ant-message-error",
        ".alert-danger",
        "[role='alert']",
        ".MuiAlert-standardError",
        ".notification-error",
    ]
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    return True, el.text[:200]
        except Exception:
            pass
    return False, ""


def is_page_blank():
    """Check if page is essentially blank."""
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        text = body.text.strip()
        if len(text) < 10:
            # Also check if there's meaningful DOM
            children = driver.find_elements(By.CSS_SELECTOR, "body > *")
            visible = [c for c in children if c.is_displayed()]
            if len(visible) < 2:
                return True
        return False
    except Exception:
        return True


def is_404_page():
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        indicators = ["404", "not found", "page not found", "page doesn't exist"]
        return any(ind in body_text for ind in indicators)
    except Exception:
        return False


def file_github_issue(bug: BugReport):
    """File a GitHub issue via API."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    severity_label = f"severity:{bug.severity}"
    labels = ["bug", "e2e-test", "dashboard-modules", severity_label]

    body = f"## Bug Report (Automated E2E Test)\n\n"
    body += f"**Severity:** {bug.severity}\n"
    body += f"**URL:** {bug.url}\n"
    body += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    body += f"### Description\n{bug.description}\n\n"
    if bug.screenshot_path:
        body += f"### Screenshot\nScreenshot saved locally at: `{bug.screenshot_path}`\n\n"
    body += "---\n*Filed automatically by E2E dashboard module test suite.*\n"

    payload = json.dumps({
        "title": bug.title,
        "body": body,
        "labels": labels,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"token {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "EmpCloud-E2E-Tester")

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode("utf-8"))
        bug.github_issue_url = data.get("html_url", "")
        print(f"  [github] Issue filed: {bug.github_issue_url}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"  [github-error] {e.code}: {err_body[:300]}")
    except Exception as e:
        print(f"  [github-error] {e}")


def add_bug(title, description, severity, url="", screenshot_path=""):
    bug = BugReport(
        title=title,
        description=description,
        severity=severity,
        url=url,
        screenshot_path=screenshot_path,
    )
    bugs.append(bug)
    print(f"\n  *** BUG [{severity.upper()}]: {title}")
    file_github_issue(bug)
    return bug


def wait_for_page_load(timeout=15):
    """Wait for page to finish loading."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        pass
    time.sleep(2)  # Extra settle time for SPAs


# ─── Login ────────────────────────────────────────────────────────────────────
def login():
    print("\n=== LOGGING IN AS ORG ADMIN ===")
    driver.get(BASE_URL)
    wait_for_page_load()
    time.sleep(3)

    current = driver.current_url
    print(f"  Initial URL: {current}")
    screenshot("00_initial_page")

    # Try to find login form
    try:
        # Look for email field
        email_field = None
        for sel in ["input[name='email']", "input[type='email']", "input[name='username']",
                     "input[placeholder*='mail']", "input[placeholder*='Email']",
                     "#email", "#username", "input[name='login']"]:
            try:
                email_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                if email_field:
                    break
            except TimeoutException:
                continue

        if not email_field:
            # Maybe we need to navigate to login page
            for login_path in ["/login", "/auth/login", "/signin"]:
                driver.get(BASE_URL + login_path)
                wait_for_page_load()
                time.sleep(2)
                for sel in ["input[name='email']", "input[type='email']", "input[name='username']",
                             "input[placeholder*='mail']", "#email"]:
                    try:
                        email_field = driver.find_element(By.CSS_SELECTOR, sel)
                        if email_field:
                            break
                    except NoSuchElementException:
                        continue
                if email_field:
                    break

        if not email_field:
            screenshot("00_no_login_form")
            # Try finding any input
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"  Found {len(inputs)} input elements")
            for i, inp in enumerate(inputs):
                print(f"    input[{i}]: type={inp.get_attribute('type')}, name={inp.get_attribute('name')}, placeholder={inp.get_attribute('placeholder')}")
            if len(inputs) >= 2:
                email_field = inputs[0]
            else:
                print("  ERROR: Cannot find login form!")
                return False

        email_field.clear()
        email_field.send_keys(ORG_ADMIN_EMAIL)

        # Find password field
        pass_field = None
        for sel in ["input[name='password']", "input[type='password']", "#password"]:
            try:
                pass_field = driver.find_element(By.CSS_SELECTOR, sel)
                if pass_field:
                    break
            except NoSuchElementException:
                continue

        if not pass_field:
            print("  ERROR: Cannot find password field!")
            return False

        pass_field.clear()
        pass_field.send_keys(ORG_ADMIN_PASS)
        screenshot("00_credentials_entered")

        # Find and click login button
        btn = None
        for sel in ["button[type='submit']", "input[type='submit']",
                     "button:has-text('Login')", "button:has-text('Sign')",
                     "button.login-btn", "#login-btn"]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, sel)
                if btn:
                    break
            except (NoSuchElementException, Exception):
                continue

        if not btn:
            # Try finding button by text
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for b in buttons:
                txt = b.text.lower()
                if any(kw in txt for kw in ["login", "sign in", "submit", "log in"]):
                    btn = b
                    break

        if not btn:
            # Last resort: try all buttons
            buttons = driver.find_elements(By.TAG_NAME, "button")
            if buttons:
                btn = buttons[-1]

        if btn:
            btn.click()
            print("  Clicked login button")
            wait_for_page_load()
            time.sleep(5)
        else:
            print("  ERROR: Cannot find login button!")
            return False

        screenshot("00_after_login")
        current = driver.current_url
        print(f"  Post-login URL: {current}")

        # Check if login succeeded
        if "login" in current.lower() and "dashboard" not in current.lower():
            # Maybe there's an error
            body_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"  Page text (first 300 chars): {body_text[:300]}")
            # Try again with a wait
            time.sleep(5)
            current = driver.current_url
            if "login" in current.lower():
                print("  WARNING: Still on login page after 5s extra wait")
                screenshot("00_login_stuck")

        return True

    except Exception as e:
        print(f"  Login error: {e}")
        traceback.print_exc()
        screenshot("00_login_error")
        return False


# ─── Sidebar Mapping ─────────────────────────────────────────────────────────
def expand_sidebar():
    """Try to expand the sidebar if it's collapsed."""
    try:
        # Common sidebar toggle selectors
        toggles = [
            "[class*='sidebar-toggle']",
            "[class*='hamburger']",
            "[class*='menu-toggle']",
            "button[class*='sidebar']",
            ".nav-toggle",
            "[data-toggle='sidebar']",
            "button.toggle-btn",
            "[class*='collapse-btn']",
        ]
        for sel in toggles:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed():
                        el.click()
                        time.sleep(1)
                        print(f"  Clicked sidebar toggle: {sel}")
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def map_sidebar():
    """Map all sidebar navigation items."""
    print("\n=== MAPPING SIDEBAR NAVIGATION ===")
    wait_for_page_load()
    time.sleep(3)

    # Take sidebar screenshot
    screenshot("01_sidebar_full")

    # Try to expand sidebar first
    expand_sidebar()
    time.sleep(2)
    screenshot("01_sidebar_expanded")

    # Strategy: find all nav links in sidebar area
    sidebar_selectors = [
        "nav a", "aside a",
        "[class*='sidebar'] a",
        "[class*='Sidebar'] a",
        "[class*='side-bar'] a",
        "[class*='sidenav'] a",
        "[class*='nav-menu'] a",
        "[class*='left-menu'] a",
        "[class*='main-menu'] a",
        "[role='navigation'] a",
        ".menu a",
        ".nav a",
        "#sidebar a",
        "#side-menu a",
    ]

    all_links = []
    seen_hrefs = set()

    for sel in sidebar_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                try:
                    href = el.get_attribute("href") or ""
                    text = el.text.strip() or el.get_attribute("title") or el.get_attribute("aria-label") or ""
                    if not text:
                        # Try getting text from child span
                        spans = el.find_elements(By.TAG_NAME, "span")
                        for s in spans:
                            t = s.text.strip()
                            if t:
                                text = t
                                break
                    if not text:
                        text = el.get_attribute("innerText") or ""
                        text = text.strip()

                    if href and href not in seen_hrefs and text:
                        if href.startswith("javascript:") or href == "#":
                            continue
                        seen_hrefs.add(href)
                        all_links.append({"text": text, "href": href, "element_sel": sel})
                except StaleElementReferenceException:
                    continue
        except Exception:
            continue

    # Also try to find menu items that might be buttons (not <a> tags)
    menu_item_selectors = [
        "[class*='sidebar'] [class*='menu-item']",
        "[class*='sidebar'] li",
        "[class*='Sidebar'] [class*='MenuItem']",
        "[class*='sidebar'] [role='menuitem']",
        "nav [role='menuitem']",
    ]

    for sel in menu_item_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                try:
                    # Check if this element contains an <a> we already captured
                    inner_a = el.find_elements(By.TAG_NAME, "a")
                    if inner_a:
                        continue
                    text = el.text.strip()
                    onclick = el.get_attribute("onclick") or ""
                    data_href = el.get_attribute("data-href") or el.get_attribute("data-url") or ""
                    if text and (onclick or data_href or el.is_displayed()):
                        key = f"menuitem:{text}"
                        if key not in seen_hrefs:
                            seen_hrefs.add(key)
                            all_links.append({"text": text, "href": data_href or f"[click:{text}]", "element_sel": sel})
                except StaleElementReferenceException:
                    continue
        except Exception:
            continue

    print(f"\n  Found {len(all_links)} sidebar links:")
    for i, link in enumerate(all_links):
        print(f"    [{i+1}] {link['text']} -> {link['href']}")
        sidebar_links.append(SidebarLink(
            text=link['text'],
            href=link['href'],
            level=0,
        ))

    return all_links


def expand_and_find_submenus():
    """Click on items that have sub-menus to reveal nested items."""
    print("\n=== EXPANDING SUB-MENUS ===")

    expandable_selectors = [
        "[class*='sidebar'] [class*='has-sub']",
        "[class*='sidebar'] [class*='has-children']",
        "[class*='sidebar'] [class*='submenu-toggle']",
        "[class*='sidebar'] [class*='expandable']",
        "[class*='sidebar'] [class*='dropdown']",
        "[class*='sidebar'] li:has(ul)",
        "[class*='sidebar'] [aria-expanded]",
        "nav [aria-expanded]",
        "[class*='sidebar'] [class*='arrow']",
        "[class*='sidebar'] [class*='caret']",
        "[class*='sidebar'] details summary",
    ]

    expanded_count = 0
    for sel in expandable_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                try:
                    if el.is_displayed():
                        expanded = el.get_attribute("aria-expanded")
                        if expanded == "false" or expanded is None:
                            try:
                                el.click()
                                time.sleep(1)
                                expanded_count += 1
                            except ElementClickInterceptedException:
                                driver.execute_script("arguments[0].click();", el)
                                time.sleep(1)
                                expanded_count += 1
                except (StaleElementReferenceException, Exception):
                    continue
        except Exception:
            continue

    print(f"  Expanded {expanded_count} sub-menu items")

    # Now re-scan for any new links
    new_links = []
    existing_hrefs = {sl.href for sl in sidebar_links}

    for sel in ["[class*='sidebar'] a", "nav a", "aside a", "[class*='Sidebar'] a"]:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                try:
                    href = el.get_attribute("href") or ""
                    text = el.text.strip() or el.get_attribute("title") or ""
                    if not text:
                        spans = el.find_elements(By.TAG_NAME, "span")
                        for s in spans:
                            t = s.text.strip()
                            if t:
                                text = t
                                break
                    if href and href not in existing_hrefs and text:
                        if href.startswith("javascript:") or href == "#":
                            continue
                        existing_hrefs.add(href)
                        new_links.append(SidebarLink(text=text, href=href, level=1))
                except StaleElementReferenceException:
                    continue
        except Exception:
            continue

    if new_links:
        print(f"  Found {len(new_links)} additional sub-menu links:")
        for link in new_links:
            print(f"    [sub] {link.text} -> {link.href}")
            sidebar_links.append(link)

    screenshot("01_sidebar_all_expanded")


# ─── Test Each Link ───────────────────────────────────────────────────────────
def test_sidebar_link(link: SidebarLink, index: int):
    """Navigate to a sidebar link and check its status."""
    print(f"\n--- Testing [{index+1}/{len(sidebar_links)}]: {link.text} ---")
    print(f"  href: {link.href}")

    if link.href.startswith("[click:"):
        print("  Skipping click-only item (no href)")
        link.status = "click-only"
        return

    try:
        driver.get(link.href)
        wait_for_page_load()
        time.sleep(3)

        current_url = driver.current_url
        link.navigated_url = current_url
        print(f"  Navigated to: {current_url}")

        # Check for subdomain redirect
        base_domain = "test-empcloud.empcloud.com"
        from urllib.parse import urlparse
        parsed = urlparse(current_url)
        if parsed.hostname and parsed.hostname != base_domain:
            link.status = "subdomain"
            link.error_detail = f"Redirected to subdomain: {parsed.hostname}"
            print(f"  NOTE: Redirected to subdomain: {parsed.hostname}")

        # Check for JS errors
        js_errors = get_js_errors()
        link.js_errors = js_errors
        if js_errors:
            print(f"  JS Errors: {len(js_errors)}")
            for err in js_errors[:3]:
                print(f"    - {err[:150]}")

        # Check for error toasts
        has_toast, toast_text = check_error_toasts()
        link.has_error_toast = has_toast
        if has_toast:
            print(f"  Error toast: {toast_text}")

        # Check for 404
        if is_404_page():
            link.status = "404"
            link.error_detail = "Page shows 404 / Not Found"
            ss = screenshot(f"bug_404_{link.text}")
            link.screenshot_path = ss
            add_bug(
                title=f"[Dashboard] 404 error on sidebar link: {link.text}",
                description=f"Sidebar link '{link.text}' (href: {link.href}) leads to a 404 page.\nNavigated URL: {current_url}",
                severity="high",
                url=current_url,
                screenshot_path=ss,
            )
            return

        # Check for blank page
        if is_page_blank():
            link.status = "blank"
            link.error_detail = "Page is blank/empty"
            ss = screenshot(f"bug_blank_{link.text}")
            link.screenshot_path = ss
            add_bug(
                title=f"[Dashboard] Blank page on sidebar link: {link.text}",
                description=f"Sidebar link '{link.text}' (href: {link.href}) leads to a blank page.\nNavigated URL: {current_url}",
                severity="high",
                url=current_url,
                screenshot_path=ss,
            )
            return

        # Check for redirect back to dashboard/login
        if "login" in current_url.lower() and "login" not in link.href.lower():
            link.status = "redirect-login"
            link.error_detail = "Redirected to login page"
            ss = screenshot(f"bug_redirect_login_{link.text}")
            link.screenshot_path = ss
            add_bug(
                title=f"[Dashboard] Sidebar link redirects to login: {link.text}",
                description=f"Sidebar link '{link.text}' (href: {link.href}) redirects to login page.\nThis may indicate an auth issue or broken route.\nNavigated URL: {current_url}",
                severity="high",
                url=current_url,
                screenshot_path=ss,
            )
            return

        # Check if redirected back to dashboard root when it shouldn't
        if (current_url.rstrip("/") == BASE_URL.rstrip("/") or
            current_url.rstrip("/") == BASE_URL.rstrip("/") + "/dashboard"):
            if link.href.rstrip("/") != BASE_URL.rstrip("/") and \
               link.href.rstrip("/") != BASE_URL.rstrip("/") + "/dashboard" and \
               "dashboard" not in link.text.lower() and "home" not in link.text.lower():
                link.status = "redirect-dashboard"
                link.error_detail = "Redirected back to dashboard"
                ss = screenshot(f"bug_redirect_dash_{link.text}")
                link.screenshot_path = ss
                add_bug(
                    title=f"[Dashboard] Sidebar link redirects to dashboard: {link.text}",
                    description=f"Sidebar link '{link.text}' (href: {link.href}) redirects back to the main dashboard instead of its intended page.\nExpected: specific module page\nActual: {current_url}",
                    severity="medium",
                    url=current_url,
                    screenshot_path=ss,
                )
                return

        # If we got here with JS errors or toasts, still note issues
        if link.status != "subdomain":
            link.status = "ok"

        if js_errors:
            ss = screenshot(f"jserror_{link.text}")
            link.screenshot_path = ss
            # Only file bug for severe JS errors (not network/font errors)
            critical_errors = [e for e in js_errors if "uncaught" in e.lower() or "typeerror" in e.lower() or "referenceerror" in e.lower()]
            if critical_errors:
                add_bug(
                    title=f"[Dashboard] JS errors on page: {link.text}",
                    description=f"Page '{link.text}' ({current_url}) has JavaScript errors:\n" +
                                "\n".join(f"- {e[:200]}" for e in critical_errors[:5]),
                    severity="medium",
                    url=current_url,
                    screenshot_path=ss,
                )

        if has_toast:
            ss = screenshot(f"toast_error_{link.text}")
            link.screenshot_path = ss
            add_bug(
                title=f"[Dashboard] Error toast on page: {link.text}",
                description=f"Page '{link.text}' ({current_url}) shows an error toast: {toast_text}",
                severity="medium",
                url=current_url,
                screenshot_path=ss,
            )

        # Take regular screenshot
        if not link.screenshot_path:
            link.screenshot_path = screenshot(f"page_{link.text}")

    except WebDriverException as e:
        link.status = "error"
        link.error_detail = str(e)[:200]
        print(f"  WebDriver error: {e}")
        ss = screenshot(f"error_{link.text}")
        link.screenshot_path = ss
        add_bug(
            title=f"[Dashboard] Navigation error on: {link.text}",
            description=f"Failed to navigate to '{link.text}' ({link.href}).\nError: {str(e)[:300]}",
            severity="high",
            url=link.href,
            screenshot_path=ss,
        )
    except Exception as e:
        link.status = "error"
        link.error_detail = str(e)[:200]
        print(f"  Error: {e}")
        traceback.print_exc()


# ─── Check Modules Page ──────────────────────────────────────────────────────
def check_modules_page():
    """Check /modules or /settings/modules for enabled modules."""
    print("\n=== CHECKING MODULES/SETTINGS PAGE ===")

    module_paths = [
        "/modules", "/settings/modules", "/admin/modules",
        "/settings", "/admin/settings", "/subscription",
        "/settings/subscription"
    ]

    for path in module_paths:
        url = BASE_URL + path
        print(f"  Trying: {url}")
        try:
            driver.get(url)
            wait_for_page_load()
            time.sleep(3)
            current = driver.current_url
            print(f"  Landed on: {current}")

            if "login" in current.lower():
                print("  -> Redirected to login, skipping")
                continue

            body = driver.find_element(By.TAG_NAME, "body").text
            if is_404_page() or len(body.strip()) < 20:
                print("  -> 404 or blank, skipping")
                continue

            print(f"  Page content (first 500 chars):\n{body[:500]}")
            ss = screenshot(f"modules_page_{path.replace('/', '_')}")

            # Look for module toggle/status indicators
            toggles = driver.find_elements(By.CSS_SELECTOR,
                "[class*='toggle'], [class*='switch'], input[type='checkbox'], [class*='module']")
            if toggles:
                print(f"  Found {len(toggles)} toggle/module elements")

            return True

        except Exception as e:
            print(f"  Error: {e}")
            continue

    print("  Could not find modules page")
    return False


def check_billing_page():
    """Check billing/subscription status."""
    print("\n=== CHECKING BILLING PAGE ===")

    billing_paths = ["/billing", "/settings/billing", "/admin/billing",
                     "/subscription", "/settings/subscription"]

    for path in billing_paths:
        url = BASE_URL + path
        print(f"  Trying: {url}")
        try:
            driver.get(url)
            wait_for_page_load()
            time.sleep(3)
            current = driver.current_url
            print(f"  Landed on: {current}")

            if "login" in current.lower():
                print("  -> Redirected to login, skipping")
                continue

            body = driver.find_element(By.TAG_NAME, "body").text
            if is_404_page() or len(body.strip()) < 20:
                print("  -> 404 or blank, skipping")
                continue

            print(f"  Billing page content (first 500 chars):\n{body[:500]}")
            ss = screenshot(f"billing_page_{path.replace('/', '_')}")
            return True

        except Exception as e:
            print(f"  Error: {e}")
            continue

    # Try finding billing via sidebar
    print("  Checking for billing link in sidebar...")
    for link in sidebar_links:
        if "billing" in link.text.lower() or "billing" in link.href.lower():
            print(f"  Found billing link: {link.text} -> {link.href}")
            try:
                driver.get(link.href)
                wait_for_page_load()
                time.sleep(3)
                body = driver.find_element(By.TAG_NAME, "body").text
                print(f"  Billing content (first 500 chars):\n{body[:500]}")
                screenshot("billing_via_sidebar")
                return True
            except Exception:
                pass

    print("  Could not find billing page")
    return False


# ─── Alternate approach: dump all links from page ────────────────────────────
def dump_all_page_links():
    """Fallback: get ALL links on the page for analysis."""
    print("\n=== DUMPING ALL PAGE LINKS (fallback) ===")
    try:
        links = driver.find_elements(By.TAG_NAME, "a")
        print(f"  Total <a> elements on page: {len(links)}")
        for i, el in enumerate(links):
            try:
                href = el.get_attribute("href") or ""
                text = el.text.strip() or el.get_attribute("title") or el.get_attribute("aria-label") or ""
                if href and text:
                    print(f"    [{i}] {text} -> {href}")
            except StaleElementReferenceException:
                continue
    except Exception as e:
        print(f"  Error dumping links: {e}")


def analyze_page_structure():
    """Analyze the page DOM structure to find navigation elements."""
    print("\n=== ANALYZING PAGE STRUCTURE ===")
    try:
        # Check for common SPA framework clues
        frameworks = {
            "React": "div#root, div#__next, [data-reactroot]",
            "Angular": "[ng-app], [ng-controller], app-root",
            "Vue": "div#app, [data-v-]",
        }
        for name, sel in frameworks.items():
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    print(f"  Detected framework: {name} (selector: {sel})")
            except Exception:
                pass

        # Get main structural elements
        structural = ["nav", "aside", "header", "main", "footer",
                      "[role='navigation']", "[role='main']", "[role='banner']"]
        for sel in structural:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    for el in els:
                        classes = el.get_attribute("class") or ""
                        tag = el.tag_name
                        print(f"  Found <{tag}> class='{classes[:100]}' id='{el.get_attribute('id') or ''}' visible={el.is_displayed()}")
            except Exception:
                pass

        # Get page title
        title = driver.title
        print(f"  Page title: {title}")

        # Check iframes
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            print(f"  Found {len(iframes)} iframes")
            for i, iframe in enumerate(iframes):
                src = iframe.get_attribute("src") or ""
                print(f"    iframe[{i}]: src={src}")

        # Get all divs with sidebar-like classes
        all_divs = driver.find_elements(By.CSS_SELECTOR, "div[class]")
        sidebar_divs = []
        for d in all_divs:
            cls = (d.get_attribute("class") or "").lower()
            if any(kw in cls for kw in ["sidebar", "sidenav", "side-bar", "nav", "menu", "drawer"]):
                sidebar_divs.append(d)

        if sidebar_divs:
            print(f"\n  Found {len(sidebar_divs)} sidebar/nav divs:")
            for d in sidebar_divs[:10]:
                cls = d.get_attribute("class") or ""
                tag = d.tag_name
                children_a = d.find_elements(By.TAG_NAME, "a")
                children_text = d.text[:200] if d.text else "(empty)"
                print(f"    <{tag} class='{cls[:80]}'> links={len(children_a)}")
                if children_a:
                    for a in children_a[:5]:
                        print(f"      -> {a.text.strip()} | href={a.get_attribute('href')}")

    except Exception as e:
        print(f"  Error analyzing structure: {e}")
        traceback.print_exc()


# ─── Comprehensive sidebar scan ──────────────────────────────────────────────
def comprehensive_sidebar_scan():
    """Deep scan for sidebar elements using multiple strategies."""
    print("\n=== COMPREHENSIVE SIDEBAR SCAN ===")

    # Strategy 1: JavaScript DOM traversal
    try:
        result = driver.execute_script("""
            let links = [];
            // Get all links on page
            document.querySelectorAll('a').forEach(a => {
                let rect = a.getBoundingClientRect();
                let text = a.innerText ? a.innerText.trim() : (a.title || a.getAttribute('aria-label') || '');
                let href = a.href || '';
                if (text && href && rect.x < 300) {  // Sidebar is typically on left side
                    links.push({
                        text: text.substring(0, 100),
                        href: href,
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        visible: rect.width > 0 && rect.height > 0
                    });
                }
            });
            return links;
        """)
        if result:
            print(f"  JS scan found {len(result)} left-side links:")
            seen_hrefs = {sl.href for sl in sidebar_links}
            for item in result:
                marker = " [NEW]" if item['href'] not in seen_hrefs else ""
                print(f"    {item['text']} -> {item['href']} (x={item['x']}, visible={item['visible']}){marker}")
                if item['href'] not in seen_hrefs and item['visible']:
                    seen_hrefs.add(item['href'])
                    sidebar_links.append(SidebarLink(
                        text=item['text'],
                        href=item['href'],
                        level=0 if item['x'] < 50 else 1,
                    ))
    except Exception as e:
        print(f"  JS scan error: {e}")

    # Strategy 2: Look for clickable elements that might expand menus
    try:
        result = driver.execute_script("""
            let items = [];
            document.querySelectorAll('[class*="sidebar"] *, [class*="Sidebar"] *, nav *, aside *').forEach(el => {
                if (el.tagName === 'A' || el.tagName === 'BUTTON' || el.onclick ||
                    el.getAttribute('role') === 'button' || el.getAttribute('role') === 'menuitem') {
                    let rect = el.getBoundingClientRect();
                    let text = el.innerText ? el.innerText.trim() : '';
                    if (text && rect.width > 0 && rect.height > 0 && rect.x < 350) {
                        items.push({
                            tag: el.tagName,
                            text: text.substring(0, 100),
                            href: el.href || '',
                            class: (el.className || '').substring(0, 100),
                            ariaExpanded: el.getAttribute('aria-expanded')
                        });
                    }
                }
            });
            return items;
        """)
        if result:
            print(f"\n  Found {len(result)} interactive sidebar elements:")
            for item in result[:50]:
                exp = f" [aria-expanded={item['ariaExpanded']}]" if item['ariaExpanded'] else ""
                print(f"    <{item['tag']}> {item['text']} href={item['href']}{exp}")
    except Exception as e:
        print(f"  Interactive scan error: {e}")


# ─── Final Report ─────────────────────────────────────────────────────────────
def print_report():
    print("\n" + "=" * 80)
    print("  FULL DASHBOARD MODULE TEST REPORT")
    print("=" * 80)

    print(f"\n  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  User: {ORG_ADMIN_EMAIL}")

    # Sidebar Map
    print(f"\n{'─' * 60}")
    print("  COMPLETE SIDEBAR MAP")
    print(f"{'─' * 60}")
    for i, link in enumerate(sidebar_links):
        indent = "    " if link.level == 0 else "      "
        status_icon = {
            "ok": "[OK]",
            "broken": "[BROKEN]",
            "blank": "[BLANK]",
            "404": "[404]",
            "error": "[ERROR]",
            "redirect-login": "[REDIR->LOGIN]",
            "redirect-dashboard": "[REDIR->DASH]",
            "subdomain": "[SUBDOMAIN]",
            "untested": "[UNTESTED]",
            "click-only": "[CLICK-ONLY]",
        }.get(link.status, f"[{link.status}]")

        print(f"{indent}{status_icon} {link.text}")
        print(f"{indent}  href: {link.href}")
        if link.navigated_url and link.navigated_url != link.href:
            print(f"{indent}  actual: {link.navigated_url}")
        if link.error_detail:
            print(f"{indent}  detail: {link.error_detail}")
        if link.js_errors:
            print(f"{indent}  js_errors: {len(link.js_errors)}")

    # Module Accessibility
    print(f"\n{'─' * 60}")
    print("  MODULE ACCESSIBILITY")
    print(f"{'─' * 60}")

    module_keywords = {
        "Core HRMS": ["employee", "department", "org", "hrms", "people", "team"],
        "Employee Monitoring": ["monitor", "tracking", "emp-monitor", "attendance"],
        "Rewards & Recognition": ["reward", "recognition", "emp-reward"],
        "Recruitment / ATS": ["recruit", "ats", "hiring", "job", "applicant", "candidate"],
        "Billing": ["billing", "subscription", "plan", "payment"],
        "Exit Management": ["exit", "offboard", "separation", "resign"],
        "LMS / Learning": ["lms", "learning", "training", "course"],
        "Payroll": ["payroll", "salary", "compensation", "pay"],
        "Performance Management": ["performance", "appraisal", "review", "goal", "okr"],
        "Project Management": ["project", "task", "sprint", "kanban"],
        "Field Force": ["field", "field-force", "fieldforce"],
        "Biometrics": ["biometric", "fingerprint", "face-recognition"],
    }

    accessible = []
    broken = []
    missing = []

    for module_name, keywords in module_keywords.items():
        found = False
        module_status = "missing"
        for link in sidebar_links:
            combined = (link.text + " " + link.href).lower()
            if any(kw in combined for kw in keywords):
                found = True
                if link.status == "ok" or link.status == "subdomain":
                    module_status = "accessible"
                else:
                    module_status = f"broken ({link.status})"
                break

        if module_status == "accessible":
            accessible.append(module_name)
            print(f"  [ACCESSIBLE] {module_name}")
        elif module_status == "missing":
            missing.append(module_name)
            print(f"  [MISSING]    {module_name}")
        else:
            broken.append(module_name)
            print(f"  [BROKEN]     {module_name} - {module_status}")

    # Bug Summary
    print(f"\n{'─' * 60}")
    print("  BUG SUMMARY")
    print(f"{'─' * 60}")
    print(f"  Total bugs found: {len(bugs)}")

    severity_counts = {}
    for bug in bugs:
        severity_counts[bug.severity] = severity_counts.get(bug.severity, 0) + 1

    for sev in ["critical", "high", "medium", "low"]:
        if sev in severity_counts:
            print(f"    {sev.upper()}: {severity_counts[sev]}")

    for i, bug in enumerate(bugs):
        print(f"\n  Bug #{i+1}: [{bug.severity.upper()}] {bug.title}")
        print(f"    URL: {bug.url}")
        print(f"    Screenshot: {bug.screenshot_path}")
        if bug.github_issue_url:
            print(f"    GitHub: {bug.github_issue_url}")

    # Summary Stats
    print(f"\n{'─' * 60}")
    print("  SUMMARY STATISTICS")
    print(f"{'─' * 60}")
    print(f"  Total sidebar links found: {len(sidebar_links)}")
    status_counts = {}
    for link in sidebar_links:
        status_counts[link.status] = status_counts.get(link.status, 0) + 1
    for status, count in sorted(status_counts.items()):
        print(f"    {status}: {count}")

    print(f"\n  Modules accessible: {len(accessible)}/{len(EXPECTED_MODULES)}")
    print(f"  Modules broken: {len(broken)}/{len(EXPECTED_MODULES)}")
    print(f"  Modules missing from sidebar: {len(missing)}/{len(EXPECTED_MODULES)}")
    print(f"  Total bugs filed: {len(bugs)}")
    print(f"\n  Screenshots saved to: {SCREENSHOT_DIR}")
    print("=" * 80)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    global driver
    print("=" * 80)
    print("  EMP Cloud HRMS - Dashboard Module & Sidebar Test Suite")
    print("=" * 80)

    driver = create_driver()

    try:
        # Step 1: Login
        if not login():
            print("\nFATAL: Login failed, aborting test.")
            return

        # Navigate to dashboard
        driver.get(BASE_URL)
        wait_for_page_load()
        time.sleep(5)
        print(f"\n  Dashboard URL: {driver.current_url}")
        screenshot("02_dashboard")

        # Step 2: Analyze page structure
        analyze_page_structure()

        # Step 3: Map sidebar
        map_sidebar()

        # Step 4: Expand sub-menus and find more links
        # Re-navigate to dashboard first
        driver.get(BASE_URL)
        wait_for_page_load()
        time.sleep(3)
        expand_and_find_submenus()

        # Step 5: If we found few links, do comprehensive scan
        if len(sidebar_links) < 5:
            driver.get(BASE_URL)
            wait_for_page_load()
            time.sleep(3)
            comprehensive_sidebar_scan()
            dump_all_page_links()

        # Step 6: Test each sidebar link
        print(f"\n=== TESTING {len(sidebar_links)} SIDEBAR LINKS ===")
        for i, link in enumerate(sidebar_links):
            test_sidebar_link(link, i)
            # After testing, check if we're still logged in
            if "login" in driver.current_url.lower():
                print("  Session expired, re-logging in...")
                login()

        # Step 7: Check modules page
        check_modules_page()

        # Step 8: Check billing page
        check_billing_page()

        # Step 9: File bugs for missing modules
        module_keywords = {
            "Core HRMS": ["employee", "department", "org", "hrms", "people", "team"],
            "Employee Monitoring": ["monitor", "tracking", "emp-monitor", "attendance"],
            "Rewards & Recognition": ["reward", "recognition", "emp-reward"],
            "Recruitment / ATS": ["recruit", "ats", "hiring", "job", "applicant", "candidate"],
            "Billing": ["billing", "subscription", "plan", "payment"],
            "Exit Management": ["exit", "offboard", "separation", "resign"],
            "LMS / Learning": ["lms", "learning", "training", "course"],
            "Payroll": ["payroll", "salary", "compensation", "pay"],
            "Performance Management": ["performance", "appraisal", "review", "goal", "okr"],
            "Project Management": ["project", "task", "sprint", "kanban"],
            "Field Force": ["field", "field-force", "fieldforce"],
            "Biometrics": ["biometric", "fingerprint", "face-recognition"],
        }

        for module_name, keywords in module_keywords.items():
            found = False
            for link in sidebar_links:
                combined = (link.text + " " + link.href).lower()
                if any(kw in combined for kw in keywords):
                    found = True
                    break
            if not found:
                add_bug(
                    title=f"[Dashboard] Module missing from sidebar: {module_name}",
                    description=f"Expected module '{module_name}' is not accessible from the dashboard sidebar.\n"
                                f"Keywords searched: {', '.join(keywords)}\n"
                                f"Total sidebar links found: {len(sidebar_links)}",
                    severity="medium",
                    url=BASE_URL,
                )

        # Final Report
        print_report()

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        screenshot("fatal_error")
    finally:
        driver.quit()
        print("\nDriver closed. Test complete.")


if __name__ == "__main__":
    main()
