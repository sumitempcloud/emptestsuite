#!/usr/bin/env python
"""
EMP Cloud HRMS - Dashboard Module Access E2E Test
Tests all sidebar navigation, module links, marketplace, and employee vs admin access.
"""

import sys
import os
import time
import json
import traceback
import requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Force unbuffered output
import functools
import subprocess
print = functools.partial(print, flush=True)

# Note: Chrome processes cleaned before script start

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud.empcloud.com"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_access"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── Globals ─────────────────────────────────────────────────────────────
bugs = []
admin_sidebar = []
employee_sidebar = []
module_matrix = []  # final matrix rows


DRIVER_PATH = None

import tempfile

def get_chrome_options():
    tmpdir = tempfile.mkdtemp()
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument(f"--user-data-dir={tmpdir}")
    opts.page_load_strategy = 'normal'
    return opts

def get_driver():
    global DRIVER_PATH
    if DRIVER_PATH is None:
        DRIVER_PATH = ChromeDriverManager().install()
    opts = get_chrome_options()
    for attempt in range(3):
        try:
            svc = Service(DRIVER_PATH)
            d = webdriver.Chrome(service=svc, options=opts)
            d.set_page_load_timeout(30)
            d.implicitly_wait(3)
            return d
        except Exception as e:
            print(f"  Driver creation attempt {attempt+1} failed: {e}")
            time.sleep(5)
    raise RuntimeError("Failed to create Chrome driver after 3 attempts")

def is_driver_alive(driver):
    """Check if driver session is still valid."""
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


def ss(driver, name):
    """Take screenshot with sanitized filename."""
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:120]
    path = os.path.join(SCREENSHOT_DIR, f"{safe}.png")
    try:
        driver.save_screenshot(path)
    except Exception:
        pass
    return path


def file_bug(title, body, severity="medium", screenshot_path=None):
    """File a GitHub issue."""
    labels = ["bug", f"severity:{severity}", "e2e-test", "module-access"]
    full_body = f"**Severity:** {severity}\n**Date:** {datetime.now().isoformat()}\n\n{body}"
    if screenshot_path:
        full_body += f"\n\n**Screenshot:** `{screenshot_path}`"
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github+json"},
            json={"title": f"[Module Access] {title}", "body": full_body, "labels": labels},
            timeout=15,
        )
        if resp.status_code in (201, 200):
            url = resp.json().get("html_url", "")
            print(f"    [BUG FILED] #{resp.json().get('number','')} {url}")
            bugs.append({"title": title, "severity": severity, "issue_url": url})
        else:
            print(f"    [BUG FILING FAILED] {resp.status_code}: {resp.text[:200]}")
            bugs.append({"title": title, "severity": severity, "issue_url": "FAILED_TO_FILE"})
    except Exception as e:
        print(f"    [BUG FILING ERROR] {e}")
        bugs.append({"title": title, "severity": severity, "issue_url": "ERROR"})


def login(driver, email, password, role="user"):
    """Login to EMP Cloud."""
    print(f"\n{'='*60}")
    print(f"  Logging in as {role}: {email}")
    print(f"{'='*60}")
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    ss(driver, f"login_page_{role}")

    # Check current URL – might already be on dashboard
    if "/dashboard" in driver.current_url or "/home" in driver.current_url:
        print("  Already logged in, logging out first...")
        logout(driver)
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)

    try:
        # Try multiple selectors for email field
        email_field = None
        for sel in [
            "input[name='email']", "input[type='email']", "input[name='username']",
            "input[id='email']", "input[placeholder*='email' i]", "input[placeholder*='Email']",
            "#email", "input[name='login']",
        ]:
            try:
                email_field = driver.find_element(By.CSS_SELECTOR, sel)
                if email_field.is_displayed():
                    break
                email_field = None
            except NoSuchElementException:
                continue

        if not email_field:
            # Try all visible inputs
            inputs = driver.find_elements(By.TAG_NAME, "input")
            visible = [i for i in inputs if i.is_displayed()]
            print(f"  Found {len(visible)} visible inputs")
            if len(visible) >= 2:
                email_field = visible[0]
            else:
                ss(driver, f"login_fail_no_email_{role}")
                print("  ERROR: Cannot find email field")
                return False

        email_field.clear()
        email_field.send_keys(email)
        time.sleep(0.5)

        # Password field
        pw_field = None
        for sel in [
            "input[name='password']", "input[type='password']", "input[id='password']",
        ]:
            try:
                pw_field = driver.find_element(By.CSS_SELECTOR, sel)
                if pw_field.is_displayed():
                    break
                pw_field = None
            except NoSuchElementException:
                continue

        if not pw_field:
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            if inputs:
                pw_field = inputs[0]
            else:
                print("  ERROR: Cannot find password field")
                return False

        pw_field.clear()
        pw_field.send_keys(password)
        time.sleep(0.5)

        # Click login button
        btn = None
        for sel in [
            "button[type='submit']", "button.login-btn", "button:not([type='button'])",
            "input[type='submit']",
        ]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, sel)
                if btn.is_displayed():
                    break
                btn = None
            except NoSuchElementException:
                continue

        if not btn:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for b in buttons:
                txt = b.text.strip().lower()
                if "login" in txt or "sign in" in txt or "log in" in txt or "submit" in txt:
                    btn = b
                    break
            if not btn and buttons:
                btn = buttons[-1]

        if btn:
            btn.click()
        else:
            # Fallback: submit the form
            pw_field.submit()

        time.sleep(5)
        ss(driver, f"after_login_{role}")
        current = driver.current_url
        print(f"  After login URL: {current}")

        if "/login" in current:
            # Check for error messages
            try:
                errs = driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger, .toast-error, [role='alert']")
                for e in errs:
                    if e.is_displayed():
                        err_text = e.text
                        print(f"  Login error: {err_text}")
            except Exception:
                pass
            print("  WARNING: Still on login page")
            return False

        print(f"  Login successful! URL: {current}")
        return True

    except Exception as e:
        print(f"  Login exception: {e}")
        ss(driver, f"login_exception_{role}")
        return False


def logout(driver):
    """Logout from EMP Cloud. Always navigate back to base domain first."""
    try:
        # Always navigate back to base domain first
        driver.get(f"{BASE_URL}/")
        time.sleep(2)

        # Try clicking user profile / avatar / dropdown
        for sel in [
            ".user-menu", ".avatar", ".profile-dropdown", "[data-toggle='dropdown']",
            ".nav-user", ".user-avatar", "img.avatar", ".user-profile",
            "button[aria-label*='profile' i]", "button[aria-label*='user' i]",
        ]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    el.click()
                    time.sleep(1)
                    break
            except NoSuchElementException:
                continue

        # Try xpath for logout text
        for text in ["Sign out", "Logout", "Log Out", "Sign Out", "Log out"]:
            try:
                els = driver.find_elements(By.XPATH, f"//*[contains(text(),'{text}')]")
                for el in els:
                    if el.is_displayed():
                        el.click()
                        time.sleep(3)
                        print(f"  Logged out via '{text}' button")
                        return
            except Exception:
                continue

        # Look for logout link by href
        for sel in [
            "a[href*='logout']", "button[onclick*='logout']",
        ]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    el.click()
                    time.sleep(3)
                    return
            except (NoSuchElementException, Exception):
                continue

        # Fallback: navigate to logout URL
        driver.get(f"{BASE_URL}/logout")
        time.sleep(3)

        # Clear cookies to ensure clean state
        driver.delete_all_cookies()
        time.sleep(1)
    except Exception as e:
        print(f"  Logout exception: {e}")
        driver.get(f"{BASE_URL}/logout")
        time.sleep(3)
        driver.delete_all_cookies()
        time.sleep(1)


def expand_sidebar(driver):
    """Expand all sidebar items using JavaScript (no clicking to avoid Chrome crashes)."""
    print("\n  Expanding sidebar via JS...")
    try:
        # Use JS to expand all collapsible elements without clicking
        driver.execute_script("""
            // Show all collapsed/hidden sub-menus
            document.querySelectorAll('.collapse, [class*="submenu"], [class*="sub-menu"]').forEach(function(el) {
                el.classList.add('show');
                el.style.display = 'block';
                el.style.height = 'auto';
            });
            // Set aria-expanded to true
            document.querySelectorAll('[aria-expanded="false"]').forEach(function(el) {
                el.setAttribute('aria-expanded', 'true');
            });
        """)
        time.sleep(1)
        print("  Sidebar expanded via JS")
    except Exception as e:
        print(f"  JS expansion failed: {e}")


def map_sidebar(driver, role="admin"):
    """Map all sidebar navigation items using a single JS call to avoid Chrome crashes."""
    print(f"\n{'='*60}")
    print(f"  Mapping sidebar for {role}")
    print(f"{'='*60}")

    expand_sidebar(driver)
    time.sleep(1)

    # Take screenshot
    ss(driver, f"sidebar_full_{role}")

    # Extract ALL sidebar data in a single JS call to minimize Selenium round-trips
    sidebar_items = driver.execute_script("""
        var results = [];
        var seen = {};
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
            var a = links[i];
            var href = a.href || '';
            var text = (a.textContent || '').trim().replace(/\\s+/g, ' ');

            if (!text || text.length > 100) continue;
            if (!href || href === '#' || href.startsWith('javascript:')) continue;
            if (seen[href]) continue;
            seen[href] = true;

            // Get icon class
            var iconEl = a.querySelector('i, [class*="icon"]');
            var icon = '';
            if (iconEl && typeof iconEl.className === 'string') {
                icon = iconEl.className;
            }

            // Check parent for sub-menu indicators
            var parent = a.parentElement;
            var parentCls = parent ? (parent.className || '') : '';
            var hasSub = /has-sub|has-children|submenu|dropdown/.test(parentCls);

            // Determine level
            var level = 0;
            var grandparent = parent ? parent.parentElement : null;
            if (grandparent) {
                var gpCls = grandparent.className || '';
                if (/sub-menu|submenu|collapse|second-level|child/.test(gpCls)) level = 1;
            }

            results.push({
                text: text,
                href: href,
                icon: icon.substring(0, 60),
                has_sub: hasSub,
                level: level,
                displayed: a.offsetParent !== null
            });
        }
        return results;
    """)

    print(f"  Found {len(sidebar_items)} sidebar items via JS")

    # Print sidebar structure
    print(f"\n  {'='*50}")
    print(f"  SIDEBAR STRUCTURE ({role}) - {len(sidebar_items)} items")
    print(f"  {'='*50}")
    for item in sidebar_items:
        indent = "    " + ("  " * item.get("level", 0))
        sub_marker = " [+]" if item.get("has_sub") else ""
        vis = "" if item.get("displayed", True) else " (hidden)"
        print(f"{indent}{item['text']}{sub_marker}{vis}")
        if item.get("href"):
            href_display = item['href']
            if len(href_display) > 100:
                href_display = href_display[:100] + "..."
            print(f"{indent}  -> {href_display}")

    return sidebar_items


def test_sidebar_links(driver, sidebar_items, role="admin", email=None, password=None):
    """Click every sidebar link and record results. Returns (driver, results) - driver may be new if recovered."""
    print(f"\n{'='*60}")
    print(f"  Testing {len(sidebar_items)} sidebar links ({role})")
    print(f"{'='*60}")

    results = []
    base_domain = "test-empcloud.empcloud.com"
    driver_recovered = False

    for idx, item in enumerate(sidebar_items):
        href = item["href"]
        text = item["text"]

        # Skip items without real hrefs
        if not href or href.endswith("#") or href.startswith("javascript:"):
            results.append({
                **item,
                "final_url": "",
                "page_heading": "",
                "status": "SKIP_NO_LINK",
                "has_content": False,
                "error_msg": "",
                "redirected_subdomain": False,
            })
            continue

        # Check if driver is still alive; recover if not
        if not is_driver_alive(driver):
            print(f"\n  ** DRIVER CRASHED! Recovering... **")
            try:
                driver.quit()
            except Exception:
                pass
            time.sleep(3)
            driver = get_driver()
            if email and password:
                login(driver, email, password, role)
            else:
                # Navigate to base URL to have some session
                driver.get(BASE_URL)
                time.sleep(3)
            driver_recovered = True

        print(f"\n  [{idx+1}/{len(sidebar_items)}] Clicking: {text}")
        print(f"    href: {href}")

        try:
            # For subdomain links, skip the actual navigation to avoid destabilizing the driver
            is_subdomain = base_domain not in href and "empcloud.com" in href

            driver.get(href)
            time.sleep(4)

            final_url = driver.current_url
            print(f"    Final URL: {final_url}")

            # Check if redirected to subdomain
            redirected_subdomain = False
            if base_domain not in final_url and "empcloud.com" in final_url:
                redirected_subdomain = True
                print(f"    ** REDIRECTED TO SUBDOMAIN **")

            # Check for login redirect
            if "/login" in final_url:
                print(f"    ** REDIRECTED TO LOGIN **")

            # Get page heading
            heading = ""
            for sel in ["h1", "h2", ".page-title", ".content-header h1", ".breadcrumb-item.active"]:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    if el.is_displayed() and el.text.strip():
                        heading = el.text.strip()[:80]
                        break
                except NoSuchElementException:
                    continue

            # Check page title
            page_title = driver.title or ""
            if not heading:
                heading = page_title[:80]

            print(f"    Heading: {heading}")

            # Check for errors
            error_msg = ""
            error_selectors = [
                ".toast-error", ".alert-danger", ".error-page", ".error-message",
                "[class*='not-found']", "[class*='404']", ".swal2-title",
            ]
            for sel in error_selectors:
                try:
                    errs = driver.find_elements(By.CSS_SELECTOR, sel)
                    for e in errs:
                        if e.is_displayed() and e.text.strip():
                            error_msg = e.text.strip()[:100]
                            break
                except Exception:
                    continue
                if error_msg:
                    break

            # Also check page body for common error text
            if not error_msg:
                try:
                    body_text = driver.find_element(By.TAG_NAME, "body").text[:2000]
                    for phrase in ["Page Not Found", "404", "Not Found", "Access Denied",
                                   "Forbidden", "500 Internal Server Error", "Something went wrong"]:
                        if phrase.lower() in body_text.lower():
                            try:
                                main_content = driver.find_element(By.CSS_SELECTOR, ".main-content, .content-page, .page-content, main, #content, .content-wrapper")
                                if phrase.lower() in main_content.text.lower():
                                    error_msg = phrase
                                    break
                            except NoSuchElementException:
                                pass
                except Exception:
                    pass

            # Check if content loaded (not blank)
            has_content = True
            try:
                content_area = None
                for csel in [".main-content", ".content-page", ".page-content", "main", "#content", ".content-wrapper", ".container-fluid"]:
                    try:
                        content_area = driver.find_element(By.CSS_SELECTOR, csel)
                        if content_area.is_displayed():
                            break
                        content_area = None
                    except NoSuchElementException:
                        continue

                if content_area:
                    content_text = content_area.text.strip()
                    if len(content_text) < 10:
                        has_content = False
                        print(f"    ** CONTENT APPEARS BLANK **")
            except Exception:
                pass

            if error_msg:
                print(f"    ERROR: {error_msg}")

            # Screenshot
            ss_path = ss(driver, f"{role}_{idx}_{text}")

            # Determine status
            status = "OK"
            if "/login" in final_url:
                status = "REDIRECT_LOGIN"
            elif error_msg:
                status = f"ERROR: {error_msg}"
            elif not has_content:
                status = "BLANK_CONTENT"
            elif redirected_subdomain:
                status = "OK_SUBDOMAIN"

            # File bug if there's an issue
            if status not in ("OK", "OK_SUBDOMAIN"):
                severity = "high" if "REDIRECT_LOGIN" in status else "medium"
                file_bug(
                    f"{text} link issue for {role}: {status}",
                    f"**Module:** {text}\n**Link:** {href}\n**Final URL:** {final_url}\n**Status:** {status}\n**Error:** {error_msg}\n**Role:** {role}",
                    severity=severity,
                    screenshot_path=ss_path,
                )

            results.append({
                **item,
                "final_url": final_url,
                "page_heading": heading,
                "status": status,
                "has_content": has_content,
                "error_msg": error_msg,
                "redirected_subdomain": redirected_subdomain,
            })

            # If we visited a subdomain, navigate back to base domain
            if redirected_subdomain:
                try:
                    driver.get(BASE_URL)
                    time.sleep(2)
                except Exception:
                    pass

        except Exception as e:
            err_str = str(e)[:120]
            print(f"    EXCEPTION: {err_str}")

            # If it's a connection error, the driver is dead
            if "NewConnectionError" in err_str or "ConnectionRefused" in err_str or "Max retries" in err_str:
                print(f"    ** DRIVER DEAD - will recover on next iteration **")

            results.append({
                **item,
                "final_url": "",
                "page_heading": "",
                "status": f"EXCEPTION: {err_str[:80]}",
                "has_content": False,
                "error_msg": err_str[:100],
                "redirected_subdomain": False,
            })

    return driver, results


def test_module_marketplace(driver):
    """Navigate to /modules and list all modules."""
    print(f"\n{'='*60}")
    print(f"  Step 3: Module Marketplace")
    print(f"{'='*60}")

    # Navigate back to base domain first
    driver.get(f"{BASE_URL}/modules")
    time.sleep(5)
    ss(driver, "marketplace_modules")

    final_url = driver.current_url
    print(f"  Final URL: {final_url}")

    modules_found = []

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"  Page contains 'Module Marketplace': {'Module Marketplace' in body_text}")

        # The marketplace page shows module cards. Parse from text using known patterns.
        # From our first run we know the text format contains module names followed by
        # their status (Subscribed/Subscribe). Parse using regex approach on body text.
        import re

        # Extract the marketplace section (after "Module Marketplace")
        mp_start = body_text.find("Module Marketplace")
        if mp_start >= 0:
            mp_text = body_text[mp_start:]
            print(f"  Marketplace text found ({len(mp_text)} chars)")

            # Known module patterns from first run:
            # "Module Name\nemp-slug\nDescription\nSubscribed\nUnsubscribe"
            # OR "Module Name\nemp-slug\nDescription\nSubscribe"
            lines = mp_text.split('\n')
            i = 1  # skip "Module Marketplace" header line
            while i < len(lines):
                line = lines[i].strip()
                # Skip empty lines and known non-module lines
                if not line or line in ("Module Marketplace", "Browse and subscribe to EMP modules for your organization."):
                    i += 1
                    continue

                # Check if this looks like a module name (not a slug, not status)
                if line.startswith("emp-") or line.lower() in ("subscribed", "subscribe", "unsubscribe"):
                    i += 1
                    continue

                # Check if next line is an emp- slug
                if i + 1 < len(lines) and lines[i + 1].strip().startswith("emp-"):
                    mod_name = line
                    slug = lines[i + 1].strip() if i + 1 < len(lines) else ""
                    # Look ahead for status
                    status = "UNKNOWN"
                    desc = ""
                    for j in range(i + 2, min(i + 6, len(lines))):
                        lj = lines[j].strip().lower()
                        if lj == "subscribed":
                            status = "SUBSCRIBED"
                            break
                        elif lj == "subscribe":
                            status = "NOT_SUBSCRIBED"
                            break
                        elif lj and lj != "unsubscribe":
                            desc = lines[j].strip()

                    modules_found.append({
                        "name": mod_name,
                        "slug": slug,
                        "description": desc,
                        "status": status,
                    })
                    i += 4  # skip ahead past this module block
                else:
                    i += 1

        if not modules_found:
            # Fallback: try to find modules using JS to query the React/Vue state
            try:
                # Try getting text of specific card elements
                cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='module'], [class*='grid'] > div")
                for card in cards:
                    card_text = card.text.strip()
                    if "emp-" in card_text and len(card_text) > 20:
                        lines = card_text.split('\n')
                        if len(lines) >= 2:
                            name = lines[0].strip()
                            status = "SUBSCRIBED" if "subscribed" in card_text.lower() else "NOT_SUBSCRIBED"
                            if name and not name.startswith("emp-"):
                                modules_found.append({"name": name, "slug": "", "description": "", "status": status})
            except Exception:
                pass

    except Exception as e:
        print(f"  Error parsing marketplace: {e}")

    # Print modules
    print(f"\n  {'='*50}")
    print(f"  MODULES FOUND: {len(modules_found)}")
    print(f"  {'='*50}")
    for m in modules_found:
        status_icon = "ACTIVE" if m["status"] == "SUBSCRIBED" else "INACTIVE"
        desc = m.get("description", "")
        print(f"    [{status_icon}] {m['name']} ({m.get('slug', '')}) - {desc}")

    if not modules_found:
        print("  WARNING: Could not parse module marketplace")
        print(f"  Page text preview:")
        try:
            print(f"  {driver.find_element(By.TAG_NAME, 'body').text[:2000]}")
        except Exception:
            pass

    return modules_found


def test_employee_self_service(driver):
    """Test employee self-service data flows."""
    print(f"\n{'='*60}")
    print(f"  Step 5: Employee Self-Service Data Flow")
    print(f"{'='*60}")

    self_service_items = {
        "My Profile": ["/profile", "/my-profile", "/self-service/profile", "/me", "/employee/profile"],
        "My Attendance": ["/attendance", "/my-attendance", "/self-service/attendance", "/attendance/my"],
        "My Leaves": ["/leaves", "/my-leaves", "/self-service/leaves", "/leave/my", "/leave/balance"],
        "My Documents": ["/documents", "/my-documents", "/self-service/documents", "/document/my"],
    }

    results = {}

    for section, url_suffixes in self_service_items.items():
        print(f"\n  Checking: {section}")
        found = False

        for suffix in url_suffixes:
            url = f"{BASE_URL}{suffix}"
            driver.get(url)
            time.sleep(3)

            final_url = driver.current_url
            if "/login" in final_url:
                continue

            body_text = ""
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text[:2000]
            except Exception:
                pass

            # Check if the page has relevant content
            if len(body_text) > 50 and "404" not in body_text and "not found" not in body_text.lower():
                print(f"    Found at: {final_url}")
                ss(driver, f"employee_self_service_{section.replace(' ', '_')}")

                results[section] = {
                    "url": final_url,
                    "has_content": True,
                    "preview": body_text[:200],
                }
                found = True
                break

        if not found:
            # Also try clicking sidebar link
            try:
                for text_match in [section, section.replace("My ", "")]:
                    links = driver.find_elements(By.XPATH, f"//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{text_match.lower()}')]")
                    for link in links:
                        if link.is_displayed():
                            link.click()
                            time.sleep(3)
                            final_url = driver.current_url
                            body_text = driver.find_element(By.TAG_NAME, "body").text[:2000]
                            if "/login" not in final_url and len(body_text) > 50:
                                print(f"    Found via sidebar click: {final_url}")
                                ss(driver, f"employee_self_service_{section.replace(' ', '_')}")
                                results[section] = {
                                    "url": final_url,
                                    "has_content": True,
                                    "preview": body_text[:200],
                                }
                                found = True
                                break
                    if found:
                        break
            except Exception:
                pass

        if not found:
            print(f"    NOT FOUND for: {section}")
            results[section] = {
                "url": "",
                "has_content": False,
                "preview": "",
            }
            file_bug(
                f"Employee self-service '{section}' not accessible",
                f"Could not find a working page for employee self-service section '{section}'.\nTried URLs: {url_suffixes}",
                severity="medium",
                screenshot_path=ss(driver, f"employee_missing_{section.replace(' ', '_')}"),
            )

    # Check dashboard widgets
    print(f"\n  Checking dashboard widgets...")
    driver.get(f"{BASE_URL}/dashboard")
    time.sleep(4)
    ss(driver, "employee_dashboard_widgets")

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text[:3000]
        # Look for personalized data
        personal_indicators = ["priya", "welcome", "attendance", "leave", "birthday", "announcement"]
        found_personal = []
        for indicator in personal_indicators:
            if indicator.lower() in body_text.lower():
                found_personal.append(indicator)

        if found_personal:
            print(f"    Dashboard shows personalized data: {found_personal}")
        else:
            print(f"    Dashboard may not show personalized data")
    except Exception as e:
        print(f"    Error checking dashboard: {e}")

    return results


def check_employee_admin_restriction(admin_items, emp_items):
    """Check that employee cannot see admin-only sections."""
    print(f"\n{'='*60}")
    print(f"  Checking admin vs employee access restrictions")
    print(f"{'='*60}")

    admin_only_keywords = [
        "admin", "settings", "config", "users", "roles", "permissions",
        "organization", "company", "module", "subscription", "billing",
        "audit", "import", "export",
    ]

    admin_texts = set(i["text"].lower() for i in admin_items)
    emp_texts = set(i["text"].lower() for i in emp_items)

    admin_only = admin_texts - emp_texts
    emp_only = emp_texts - admin_texts
    shared = admin_texts & emp_texts

    print(f"\n  Admin-only items ({len(admin_only)}):")
    for item in sorted(admin_only):
        print(f"    - {item}")

    print(f"\n  Employee-only items ({len(emp_only)}):")
    for item in sorted(emp_only):
        print(f"    - {item}")

    print(f"\n  Shared items ({len(shared)}):")
    for item in sorted(shared):
        print(f"    - {item}")

    # Check if employee can see admin-specific items
    leaks = []
    for emp_text in emp_texts:
        for kw in admin_only_keywords:
            if kw in emp_text and emp_text in admin_texts:
                leaks.append(emp_text)
                break

    if leaks:
        print(f"\n  WARNING: Employee may have access to admin sections: {leaks}")
        file_bug(
            "Employee may have access to admin-only sections",
            f"Employee sidebar contains items that appear admin-only:\n" + "\n".join(f"- {l}" for l in leaks),
            severity="high",
        )
    else:
        print(f"\n  OK: No obvious admin section leaks to employee")


def build_final_matrix(admin_results, emp_results, modules_found):
    """Build and print the final module access matrix."""
    print(f"\n{'='*70}")
    print(f"  FINAL MODULE ACCESS MATRIX")
    print(f"{'='*70}")

    # Combine all unique module/link entries
    all_entries = {}

    for r in admin_results:
        key = r["text"]
        all_entries[key] = {
            "text": r["text"],
            "href": r["href"],
            "final_url": r.get("final_url", ""),
            "admin_status": r.get("status", "N/A"),
            "emp_status": "N/A",
        }

    for r in emp_results:
        key = r["text"]
        if key in all_entries:
            all_entries[key]["emp_status"] = r.get("status", "N/A")
        else:
            all_entries[key] = {
                "text": r["text"],
                "href": r["href"],
                "final_url": r.get("final_url", ""),
                "admin_status": "NOT_IN_SIDEBAR",
                "emp_status": r.get("status", "N/A"),
            }

    # Print as table
    header = f"| {'Module':<30} | {'Sidebar Link':<40} | {'URL':<50} | {'Org Admin':<20} | {'Employee':<20} | {'Status':<15} |"
    sep = f"|{'-'*32}|{'-'*42}|{'-'*52}|{'-'*22}|{'-'*22}|{'-'*17}|"

    print(header)
    print(sep)

    for key, entry in sorted(all_entries.items()):
        # Overall status
        admin_ok = entry["admin_status"] in ("OK", "OK_SUBDOMAIN", "SKIP_NO_LINK")
        emp_ok = entry["emp_status"] in ("OK", "OK_SUBDOMAIN", "SKIP_NO_LINK", "N/A", "NOT_IN_SIDEBAR")
        overall = "OK" if admin_ok and emp_ok else "ISSUE"
        if entry["admin_status"] == "NOT_IN_SIDEBAR":
            overall = "EMP_ONLY"

        href_short = entry["href"][-40:] if entry["href"] else ""
        url_short = entry["final_url"][-50:] if entry["final_url"] else ""

        print(f"| {entry['text']:<30} | {href_short:<40} | {url_short:<50} | {entry['admin_status']:<20} | {entry['emp_status']:<20} | {overall:<15} |")

    print(sep)
    print(f"\nTotal entries: {len(all_entries)}")

    # Summary
    ok_count = sum(1 for e in all_entries.values() if e["admin_status"] in ("OK", "OK_SUBDOMAIN"))
    issue_count = sum(1 for e in all_entries.values() if e["admin_status"] not in ("OK", "OK_SUBDOMAIN", "SKIP_NO_LINK", "N/A", "NOT_IN_SIDEBAR"))
    skip_count = sum(1 for e in all_entries.values() if e["admin_status"] == "SKIP_NO_LINK")

    print(f"\nAdmin Links: OK={ok_count}, Issues={issue_count}, Skipped={skip_count}")

    return all_entries


# ── Main ────────────────────────────────────────────────────────────────
def main():
    print(f"{'#'*70}")
    print(f"  EMP Cloud HRMS - Dashboard Module Access E2E Test")
    print(f"  Date: {datetime.now().isoformat()}")
    print(f"  Base URL: {BASE_URL}")
    print(f"{'#'*70}")

    driver = get_driver()
    admin_results = []
    emp_results = []
    modules_found = []

    def run_session(email, password, role, callback):
        """Run a callback with a fresh driver+login. Handles crashes with retry."""
        for attempt in range(2):
            d = get_driver()
            try:
                if not login(d, email, password, role):
                    print(f"  Login failed for {role} attempt {attempt+1}")
                    d.quit()
                    time.sleep(5)
                    continue
                result = callback(d)
                d.quit()
                return result
            except Exception as e:
                print(f"  Session {role} crashed attempt {attempt+1}: {str(e)[:100]}")
                try:
                    d.quit()
                except Exception:
                    pass
                time.sleep(3)
        return None

    try:
        # ── STEP 1: Admin Sidebar Mapping ────────────────────────────
        admin_sidebar_items = []
        print("\n  === STEP 1: Map Admin Sidebar ===")
        result = run_session(ADMIN_EMAIL, ADMIN_PASS, "admin", lambda d: map_sidebar(d, "admin"))
        if result:
            admin_sidebar_items = result

        # ── STEP 2: Test Every Admin Link (using session-based batching) ──
        print(f"\n  === STEP 2: Test {len(admin_sidebar_items)} Admin Links ===")
        def test_admin_links(d):
            results = []
            base_domain = "test-empcloud.empcloud.com"
            for idx, item in enumerate(admin_sidebar_items):
                href = item["href"]
                text = item["text"]
                if not href or href.endswith("#") or href.startswith("javascript:"):
                    results.append({**item, "final_url": "", "page_heading": "", "status": "SKIP_NO_LINK",
                                    "has_content": False, "error_msg": "", "redirected_subdomain": False})
                    continue

                print(f"\n  [{idx+1}/{len(admin_sidebar_items)}] {text}")
                print(f"    href: {href[:100]}")

                try:
                    d.get(href)
                    time.sleep(4)
                    final_url = d.current_url
                    print(f"    URL: {final_url[:100]}")

                    redirected_subdomain = base_domain not in final_url and "empcloud.com" in final_url
                    if redirected_subdomain:
                        print(f"    ** SUBDOMAIN **")

                    heading = ""
                    for sel in ["h1", "h2", ".page-title"]:
                        try:
                            el = d.find_element(By.CSS_SELECTOR, sel)
                            if el.is_displayed() and el.text.strip():
                                heading = el.text.strip()[:80]
                                break
                        except NoSuchElementException:
                            continue
                    if not heading:
                        heading = d.title[:80] if d.title else ""

                    error_msg = ""
                    has_content = True
                    ss(d, f"admin_{idx}_{text}")

                    status = "OK"
                    if "/login" in final_url:
                        status = "REDIRECT_LOGIN"
                    elif redirected_subdomain:
                        status = "OK_SUBDOMAIN"

                    print(f"    Status: {status} | {heading}")

                    if status not in ("OK", "OK_SUBDOMAIN"):
                        file_bug(f"{text} link issue for admin: {status}",
                                 f"**Module:** {text}\n**Link:** {href}\n**Final URL:** {final_url}\n**Status:** {status}\n**Role:** admin",
                                 severity="high" if "LOGIN" in status else "medium")

                    results.append({**item, "final_url": final_url, "page_heading": heading,
                                    "status": status, "has_content": has_content,
                                    "error_msg": error_msg, "redirected_subdomain": redirected_subdomain})

                    # Return to base after subdomain
                    if redirected_subdomain:
                        d.get(BASE_URL)
                        time.sleep(2)

                except Exception as e:
                    print(f"    EXCEPTION: {str(e)[:100]}")
                    results.append({**item, "final_url": "", "page_heading": "",
                                    "status": f"EXCEPTION: {str(e)[:80]}", "has_content": False,
                                    "error_msg": str(e)[:100], "redirected_subdomain": False})
            return results

        result = run_session(ADMIN_EMAIL, ADMIN_PASS, "admin", test_admin_links)
        if result:
            admin_results = result

        # ── STEP 3: Module Marketplace ────────────────────────────────
        print("\n  === STEP 3: Module Marketplace ===")
        result = run_session(ADMIN_EMAIL, ADMIN_PASS, "admin", lambda d: test_module_marketplace(d))
        if result:
            modules_found = result

        # ── STEP 4: Employee Tests ──────────────────────────────────
        print("\n  === STEP 4: Employee Sidebar ===")
        emp_sidebar_items = []
        result = run_session(EMP_EMAIL, EMP_PASS, "employee", lambda d: map_sidebar(d, "employee"))
        if result:
            emp_sidebar_items = result

        print(f"\n  === STEP 4b: Test {len(emp_sidebar_items)} Employee Links ===")
        def test_emp_links(d):
            results = []
            base_domain = "test-empcloud.empcloud.com"
            for idx, item in enumerate(emp_sidebar_items):
                href = item["href"]
                text = item["text"]
                if not href or href.endswith("#") or href.startswith("javascript:"):
                    results.append({**item, "final_url": "", "page_heading": "", "status": "SKIP_NO_LINK",
                                    "has_content": False, "error_msg": "", "redirected_subdomain": False})
                    continue

                print(f"\n  [{idx+1}/{len(emp_sidebar_items)}] {text}")
                try:
                    d.get(href)
                    time.sleep(4)
                    final_url = d.current_url
                    redirected_subdomain = base_domain not in final_url and "empcloud.com" in final_url

                    heading = ""
                    for sel in ["h1", "h2", ".page-title"]:
                        try:
                            el = d.find_element(By.CSS_SELECTOR, sel)
                            if el.is_displayed() and el.text.strip():
                                heading = el.text.strip()[:80]
                                break
                        except NoSuchElementException:
                            continue

                    ss(d, f"emp_{idx}_{text}")

                    status = "OK"
                    if "/login" in final_url:
                        status = "REDIRECT_LOGIN"
                    elif redirected_subdomain:
                        status = "OK_SUBDOMAIN"

                    print(f"    {status} | {final_url[:80]}")

                    if status not in ("OK", "OK_SUBDOMAIN"):
                        file_bug(f"{text} link issue for employee: {status}",
                                 f"**Module:** {text}\n**Link:** {href}\n**Final URL:** {final_url}\n**Status:** {status}\n**Role:** employee",
                                 severity="high" if "LOGIN" in status else "medium")

                    results.append({**item, "final_url": final_url, "page_heading": heading,
                                    "status": status, "has_content": True,
                                    "error_msg": "", "redirected_subdomain": redirected_subdomain})

                    if redirected_subdomain:
                        d.get(BASE_URL)
                        time.sleep(2)

                except Exception as e:
                    print(f"    EXCEPTION: {str(e)[:100]}")
                    results.append({**item, "final_url": "", "page_heading": "",
                                    "status": f"EXCEPTION: {str(e)[:80]}", "has_content": False,
                                    "error_msg": str(e)[:100], "redirected_subdomain": False})
            return results

        result = run_session(EMP_EMAIL, EMP_PASS, "employee", test_emp_links)
        if result:
            emp_results = result

        if admin_sidebar_items and emp_sidebar_items:
            check_employee_admin_restriction(admin_sidebar_items, emp_sidebar_items)

        # ── STEP 5: Employee Self-Service ────────────────────────────
        print("\n  === STEP 5: Employee Self-Service ===")
        run_session(EMP_EMAIL, EMP_PASS, "employee", lambda d: test_employee_self_service(d))

        # ── FINAL MATRIX ────────────────────────────────────────────
        final_matrix = build_final_matrix(admin_results, emp_results, modules_found)

        # ── BUG SUMMARY ─────────────────────────────────────────────
        print(f"\n{'='*70}")
        print(f"  BUG SUMMARY: {len(bugs)} bugs filed")
        print(f"{'='*70}")
        for b in bugs:
            print(f"  [{b['severity'].upper()}] {b['title']}")
            print(f"    Issue: {b['issue_url']}")

        print(f"\n{'='*70}")
        print(f"  TEST COMPLETE")
        print(f"  Screenshots: {SCREENSHOT_DIR}")
        print(f"  Total admin sidebar items: {len(admin_results)}")
        print(f"  Total employee sidebar items: {len(emp_results)}")
        print(f"  Total marketplace modules: {len(modules_found)}")
        print(f"  Total bugs filed: {len(bugs)}")
        print(f"{'='*70}")

    except Exception as e:
        print(f"\nFATAL EXCEPTION: {e}")
        traceback.print_exc()
        ss(driver, "fatal_exception")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
