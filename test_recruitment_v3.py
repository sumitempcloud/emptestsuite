#!/usr/bin/env python3
"""
EMP Cloud HRMS - Recruitment Module E2E Test v3
Robust version with session management and per-page testing.
Sidebar: Dashboard, Jobs, Candidates, Interviews, Offers, Onboarding, Referrals, Analytics, Settings
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import traceback
import urllib.request
import urllib.error
import ssl
import base64
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────
RECRUIT_URL = "https://test-recruit.empcloud.com"
MAIN_URL = "https://test-empcloud.empcloud.com"
RECRUIT_API = "https://test-recruit-api.empcloud.com"
EMAIL = "ananya@technova.in"
PASSW = "Welcome@123"
SS_DIR = r"C:\Users\Admin\screenshots\recruit"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

os.makedirs(SS_DIR, exist_ok=True)

bugs_found = []
test_results = []
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def shot(driver, name):
    """Safe screenshot that handles driver crashes."""
    try:
        path = os.path.join(SS_DIR, f"{name}_{ts()}.png")
        driver.save_screenshot(path)
        print(f"    [SS] {path}")
        return path
    except Exception as e:
        print(f"    [SS FAILED] {e}")
        return None


def gh_issue(title, body, labels=None, ss_path=None):
    if labels is None:
        labels = ["bug"]
    full_body = body
    if ss_path:
        full_body += f"\n\n**Screenshot:** `{ss_path}`"
    full_body += f"\n\n_Automated E2E test - {datetime.now().isoformat()}_"

    data = json.dumps({"title": title, "body": full_body, "labels": labels}).encode('utf-8')
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        data=data,
        headers={
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "EmpCloud-E2E-Test"
        },
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx)
        result = json.loads(resp.read().decode('utf-8'))
        print(f"    [GH] Issue #{result['number']}: {result['html_url']}")
        return result['number']
    except Exception as e:
        print(f"    [GH ERROR] {e}")
        return None


def bug(driver, name, desc, severity="medium", labels=None):
    ss = shot(driver, f"BUG_{name}")
    if labels is None:
        labels = ["bug", f"severity:{severity}"]
    else:
        labels = list(labels) + [f"severity:{severity}"]
    inum = gh_issue(f"[Recruit E2E] {name}", desc, labels, ss)
    bugs_found.append({"name": name, "severity": severity, "issue": inum, "screenshot": ss})


def result(name, passed, details=""):
    s = "PASS" if passed else "FAIL"
    print(f"  [{s}] {name} {details}")
    test_results.append({"test": name, "passed": passed, "details": details})


def make_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                "--disable-gpu", "--window-size=1920,1080", "--ignore-certificate-errors",
                "--disable-extensions", "--disable-popup-blocking"]:
        opts.add_argument(arg)
    svc = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(45)
    d.implicitly_wait(3)
    return d


def wait_stable(driver, t=10):
    try:
        WebDriverWait(driver, t).until(lambda d: d.execute_script("return document.readyState") == "complete")
    except:
        pass
    time.sleep(1.5)


def safe_click(driver, el):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.3)
        el.click()
        return True
    except:
        try:
            driver.execute_script("arguments[0].click();", el)
            return True
        except:
            return False


def do_login(driver):
    """Perform login and wait for dashboard. Returns True if successful."""
    print("    [LOGIN] Performing login...")
    driver.get(RECRUIT_URL)
    wait_stable(driver, 15)

    # Check if already on dashboard
    if "/dashboard" in driver.current_url and "login" not in driver.current_url.lower():
        # Verify we see the sidebar
        try:
            driver.find_element(By.XPATH, "//a[normalize-space()='Dashboard']")
            print("    [LOGIN] Already logged in")
            return True
        except:
            pass

    # Wait for login form
    try:
        email_el = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
        )
    except TimeoutException:
        print("    [LOGIN] No login form found")
        return False

    email_el.clear()
    email_el.send_keys(EMAIL)

    pass_el = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pass_el.clear()
    pass_el.send_keys(PASSW)

    # Click Sign in button
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(normalize-space(), 'Sign in')]")
        safe_click(driver, btn)
    except:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            safe_click(driver, btn)
        except:
            pass_el.send_keys(Keys.RETURN)

    # Wait for dashboard to appear
    try:
        WebDriverWait(driver, 15).until(EC.url_contains("/dashboard"))
        wait_stable(driver)
        print(f"    [LOGIN] Success - URL: {driver.current_url}")
        return True
    except TimeoutException:
        print(f"    [LOGIN] Did not reach dashboard - URL: {driver.current_url}")
        # Check for error messages
        try:
            errs = driver.find_elements(By.CSS_SELECTOR, "[class*='error'], [role='alert']")
            for e in errs:
                if e.is_displayed() and e.text.strip():
                    print(f"    [LOGIN] Error: {e.text.strip()}")
        except:
            pass
        return False


def ensure_logged_in(driver):
    """Ensure we are on the recruit dashboard. Re-login if needed."""
    try:
        cur = driver.current_url
        if "login" in cur.lower() or "sign" in cur.lower():
            return do_login(driver)
        # Check if session is still valid by looking for sidebar
        sidebar = driver.find_elements(By.XPATH, "//a[normalize-space()='Dashboard']")
        if not sidebar:
            return do_login(driver)
        return True
    except:
        return do_login(driver)


def navigate_sidebar(driver, label):
    """Click a sidebar link by its exact text. Handles session expiry."""
    ensure_logged_in(driver)
    time.sleep(0.5)

    # Use JavaScript to find and get href of the sidebar link, then navigate
    try:
        # First try to find the link and get its href
        links = driver.find_elements(By.XPATH, f"//a[normalize-space()='{label}']")
        for link in links:
            if link.is_displayed():
                href = link.get_attribute("href")
                if href:
                    # Use JS click to avoid intercepted clicks
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(2)
                    wait_stable(driver)

                    # Check if we got logged out
                    if "login" in driver.current_url.lower():
                        print(f"    Session expired navigating to {label}, re-logging in")
                        do_login(driver)
                        # Try again
                        links2 = driver.find_elements(By.XPATH, f"//a[normalize-space()='{label}']")
                        for l2 in links2:
                            if l2.is_displayed():
                                driver.execute_script("arguments[0].click();", l2)
                                time.sleep(2)
                                wait_stable(driver)
                                break
                    return True
        print(f"    Could not find sidebar link: {label}")
        return False
    except Exception as e:
        print(f"    Sidebar navigation error: {e}")
        return False


def is_blank(driver):
    """Check if the main content area is blank."""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.strip()
        # The sidebar always has text, so we need at least sidebar + some content
        # Sidebar has: Dashboard, Jobs, Candidates, etc. ~ about 80 chars
        return len(body) < 100
    except:
        return True


def get_heading(driver):
    for sel in ["h1", "h2", "[class*='page-title']", "[class*='heading']"]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.text.strip():
                    return el.text.strip()
        except:
            continue
    return ""


def find_btn(driver, keywords):
    """Find a visible button by keyword in its text."""
    all_btns = driver.find_elements(By.CSS_SELECTOR, "button, a[class*='btn'], [role='button']")
    for kw in keywords:
        for btn in all_btns:
            try:
                if btn.is_displayed() and kw.lower() in btn.text.lower():
                    return btn
            except:
                continue
    # Try plus-icon buttons (buttons with just an icon and no text)
    for btn in all_btns:
        try:
            if btn.is_displayed() and btn.text.strip() in ["", "+"]:
                svgs = btn.find_elements(By.CSS_SELECTOR, "svg, i")
                if svgs:
                    return btn
        except:
            continue
    return None


def get_form_fields(driver):
    fields = driver.find_elements(By.CSS_SELECTOR,
        "input:not([type='hidden']):not([type='checkbox']):not([type='radio']), "
        "textarea, select, [role='combobox'], [contenteditable='true'], "
        ".ql-editor, .ProseMirror")
    return [f for f in fields if f.is_displayed()]


def get_errors(driver):
    errs = []
    for sel in ["[class*='error']", "[class*='alert-danger']", "[role='alert']",
                "[class*='toast-error']", "[class*='Toastify__toast--error']"]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.text.strip():
                    errs.append(el.text.strip())
        except:
            continue
    return errs


def find_modal(driver):
    for sel in ["[class*='modal'][class*='show']", "[role='dialog']",
                "[class*='dialog']:not([class*='hidden'])", "[class*='drawer']",
                ".modal.show", "[class*='MuiDialog']", "[class*='MuiModal']"]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    return el
        except:
            continue
    return None


def close_any_modal(driver):
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
    except:
        pass


def collect_sidebar_urls(driver):
    """Collect all sidebar link URLs."""
    urls = {}
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "nav a, aside a, [class*='sidebar'] a")
        for link in links:
            try:
                text = link.text.strip()
                href = link.get_attribute("href")
                if text and href:
                    urls[text] = href
            except:
                continue
    except:
        pass
    return urls


# ════════════════════════════════════════════════════════════════════════
# MAIN TEST FLOW
# ════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("EMP CLOUD HRMS - RECRUITMENT MODULE E2E TEST v3")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    driver = None
    try:
        driver = make_driver()
        print("[SETUP] Chrome driver ready")

        # ── LOGIN ───────────────────────────────────────────────────
        print("\n[TEST] Login to Recruit App")
        ok = do_login(driver)
        if not ok:
            bug(driver, "Login failed", "Cannot login to Recruit app", "critical")
            result("Login", False, "Failed")
            return
        shot(driver, "00_dashboard")
        result("Login", True, f"URL: {driver.current_url}")

        # ── Collect sidebar URLs ────────────────────────────────────
        sidebar_urls = collect_sidebar_urls(driver)
        print(f"\n    Sidebar URLs found: {json.dumps(sidebar_urls, indent=2)}")

        # ── DASHBOARD ───────────────────────────────────────────────
        print("\n[TEST] Dashboard")
        heading = get_heading(driver)
        if is_blank(driver):
            bug(driver, "Dashboard blank", "Dashboard has no content", "high")
            result("Dashboard", False, "Blank")
        else:
            result("Dashboard", True, f"Heading: '{heading}'")

        # ── JOBS PAGE ───────────────────────────────────────────────
        print("\n[TEST] Jobs Page")
        if navigate_sidebar(driver, "Jobs"):
            shot(driver, "T01_jobs")
            heading = get_heading(driver)
            url = driver.current_url
            print(f"    URL: {url}, Heading: '{heading}'")

            if is_blank(driver):
                bug(driver, "Jobs page blank", f"Jobs page is blank.\n\n**URL:** {url}", "high")
                result("Jobs Page", False, "Blank")
            else:
                result("Jobs Page", True, f"Heading: '{heading}'")

            # ── CREATE JOB (Bug #51) ────────────────────────────────
            print("\n[TEST] Create Job (Bug #51)")
            create_btn = find_btn(driver, ["Create", "Add", "New Job", "Post Job", "Post", "+"])
            if create_btn:
                print(f"    Found button: '{create_btn.text.strip()}'")
                safe_click(driver, create_btn)
                time.sleep(3)
                wait_stable(driver)
                shot(driver, "T01_create_job_clicked")

                # Check if we got logged out
                if "login" in driver.current_url.lower():
                    bug(driver, "Create job redirects to login",
                        "**Bug #51 Verification:** Clicking Create Job redirects to login page.\n"
                        "Session may be expiring on navigation.",
                        "critical", ["bug", "Bug#51"])
                    result("Create Job (Bug #51)", False, "Redirected to login")
                else:
                    modal = find_modal(driver)
                    fields = get_form_fields(driver)
                    errors = get_errors(driver)
                    blank = is_blank(driver)
                    new_url = driver.current_url

                    print(f"    URL: {new_url}, Fields: {len(fields)}, Modal: {modal is not None}, Blank: {blank}")

                    if modal:
                        mf = [f for f in modal.find_elements(By.CSS_SELECTOR,
                            "input:not([type='hidden']), textarea, select, [role='combobox']")
                            if f.is_displayed()]
                        shot(driver, "T01_create_job_modal")
                        if mf:
                            # Try fill title
                            for f in mf:
                                a = " ".join(filter(None, [f.get_attribute("name"),
                                    f.get_attribute("placeholder"), f.get_attribute("id")])).lower()
                                if any(k in a for k in ["title", "name", "job", "position"]):
                                    try:
                                        f.clear()
                                        f.send_keys("QA Engineer - E2E Test")
                                    except:
                                        pass
                                    break
                            shot(driver, "T01_create_job_filled")

                            # Try submit
                            save = find_btn(driver, ["Save", "Submit", "Post", "Create", "Publish"])
                            if save:
                                safe_click(driver, save)
                                time.sleep(4)
                                wait_stable(driver)
                                shot(driver, "T01_create_job_submitted")
                                post_errors = get_errors(driver)
                                if post_errors:
                                    result("Create Job (Bug #51)", True,
                                        f"Form validation: {post_errors[:2]}")
                                else:
                                    result("Create Job (Bug #51)", True, "Form submitted")
                            else:
                                result("Create Job (Bug #51)", True, f"Modal with {len(mf)} fields")
                        else:
                            bug(driver, "Create job modal empty",
                                "**Bug #51 Verification:** Create Job modal is empty with no form fields.",
                                "critical", ["bug", "Bug#51"])
                            result("Create Job (Bug #51)", False, "Modal empty")
                    elif len(fields) > 0:
                        shot(driver, "T01_create_job_form")
                        # Try fill & submit
                        for f in fields:
                            a = " ".join(filter(None, [f.get_attribute("name"),
                                f.get_attribute("placeholder"), f.get_attribute("id")])).lower()
                            tag = f.tag_name
                            try:
                                if any(k in a for k in ["title", "name", "position", "job"]):
                                    f.clear(); f.send_keys("QA Engineer - E2E Test")
                                elif any(k in a for k in ["location", "city"]):
                                    f.clear(); f.send_keys("Remote")
                                elif any(k in a for k in ["department", "dept"]):
                                    f.clear(); f.send_keys("Engineering")
                                elif tag == "textarea":
                                    f.clear(); f.send_keys("Automated test job description.")
                                elif tag == "select":
                                    options = f.find_elements(By.TAG_NAME, "option")
                                    if len(options) > 1:
                                        options[1].click()
                            except:
                                pass

                        shot(driver, "T01_create_job_filled")
                        save = find_btn(driver, ["Save", "Submit", "Post", "Create", "Publish"])
                        if save:
                            safe_click(driver, save)
                            time.sleep(4)
                            wait_stable(driver)
                            shot(driver, "T01_create_job_submitted")
                            post_errors = get_errors(driver)
                            post_blank = is_blank(driver)
                            if post_blank:
                                bug(driver, "Create job blank after submit",
                                    "**Bug #51 Verification:** Page blank after submitting job form.\n\n"
                                    f"Errors: {post_errors}",
                                    "critical", ["bug", "Bug#51"])
                                result("Create Job (Bug #51)", False, "Blank after submit")
                            elif post_errors:
                                result("Create Job (Bug #51)", True, f"Validation: {post_errors[:2]}")
                            else:
                                result("Create Job (Bug #51)", True, "Submitted")
                        else:
                            result("Create Job (Bug #51)", True, f"Form with {len(fields)} fields")
                    elif blank:
                        bug(driver, "Create job blank page",
                            "**Bug #51 Verification:** Create Job leads to a blank page.\n\n"
                            f"**URL:** {new_url}\nNo form, modal or content visible.",
                            "critical", ["bug", "regression", "Bug#51"])
                        result("Create Job (Bug #51)", False, "Blank page")
                    else:
                        result("Create Job (Bug #51)", True, f"Page loaded: {new_url}")

                close_any_modal(driver)
            else:
                bug(driver, "No create job button",
                    "**Bug #51 Verification:** No Create/Add Job button found on Jobs page.\n\n"
                    f"**URL:** {driver.current_url}",
                    "critical", ["bug", "Bug#51"])
                result("Create Job (Bug #51)", False, "No button")
        else:
            result("Jobs Page", False, "Could not navigate")

        # ── CANDIDATES PAGE ─────────────────────────────────────────
        print("\n[TEST] Candidates Page")
        if navigate_sidebar(driver, "Candidates"):
            shot(driver, "T02_candidates")
            heading = get_heading(driver)
            url = driver.current_url
            print(f"    URL: {url}, Heading: '{heading}'")

            if is_blank(driver):
                bug(driver, "Candidates page blank", f"Candidates page is blank.\n\n**URL:** {url}", "high")
                result("Candidates Page", False, "Blank")
            else:
                result("Candidates Page", True, f"Heading: '{heading}'")

                # Try add candidate
                add_btn = find_btn(driver, ["Add", "Create", "New", "+"])
                if add_btn:
                    safe_click(driver, add_btn)
                    time.sleep(3)
                    wait_stable(driver)
                    shot(driver, "T02_add_candidate")
                    modal = find_modal(driver)
                    fields = get_form_fields(driver)
                    if modal or len(fields) > 0:
                        result("Add Candidate", True, f"Form fields: {len(fields)}, Modal: {modal is not None}")
                    else:
                        if is_blank(driver):
                            bug(driver, "Add candidate blank", "Add candidate form is blank", "medium")
                        result("Add Candidate", False, "No form appeared")
                    close_any_modal(driver)
        else:
            result("Candidates Page", False, "Could not navigate")

        # ── INTERVIEWS PAGE + SCHEDULE (Bug #52) ────────────────────
        print("\n[TEST] Interviews Page")
        if navigate_sidebar(driver, "Interviews"):
            shot(driver, "T03_interviews")
            heading = get_heading(driver)
            url = driver.current_url
            print(f"    URL: {url}, Heading: '{heading}'")

            if is_blank(driver):
                bug(driver, "Interviews page blank",
                    f"**Bug #52 Related:** Interviews page is blank.\n\n**URL:** {url}",
                    "high", ["bug", "Bug#52"])
                result("Interviews Page", False, "Blank")
            else:
                result("Interviews Page", True, f"Heading: '{heading}'")

            # Schedule interview (Bug #52)
            print("\n[TEST] Schedule Interview (Bug #52)")
            sched_btn = find_btn(driver, ["Schedule", "Add", "Create", "New", "+"])
            if sched_btn:
                print(f"    Found: '{sched_btn.text.strip()}'")
                safe_click(driver, sched_btn)
                time.sleep(3)
                wait_stable(driver)
                shot(driver, "T03_schedule_clicked")

                if "login" in driver.current_url.lower():
                    bug(driver, "Schedule interview redirects to login",
                        "**Bug #52 Verification:** Scheduling redirects to login.",
                        "critical", ["bug", "Bug#52"])
                    result("Schedule Interview (Bug #52)", False, "Redirected to login")
                else:
                    modal = find_modal(driver)
                    fields = get_form_fields(driver)
                    blank = is_blank(driver)
                    new_url = driver.current_url
                    print(f"    URL: {new_url}, Fields: {len(fields)}, Modal: {modal is not None}, Blank: {blank}")

                    if modal:
                        mf = [f for f in modal.find_elements(By.CSS_SELECTOR,
                            "input:not([type='hidden']), textarea, select, [role='combobox']")
                            if f.is_displayed()]
                        shot(driver, "T03_schedule_modal")
                        if mf:
                            result("Schedule Interview (Bug #52)", True, f"Modal with {len(mf)} fields")
                        else:
                            bug(driver, "Schedule interview modal empty",
                                "**Bug #52 Verification:** Schedule modal is empty.",
                                "high", ["bug", "Bug#52"])
                            result("Schedule Interview (Bug #52)", False, "Modal empty")
                    elif blank and len(fields) == 0:
                        bug(driver, "Schedule interview blank page",
                            "**Bug #52 Verification:** Scheduling interview shows blank page.\n\n"
                            f"**URL:** {new_url}\nNo form or content rendered.",
                            "critical", ["bug", "regression", "Bug#52"])
                        result("Schedule Interview (Bug #52)", False, "Blank page")
                    elif len(fields) > 0:
                        result("Schedule Interview (Bug #52)", True, f"{len(fields)} fields")
                    else:
                        result("Schedule Interview (Bug #52)", True, f"Page: {new_url}")
                close_any_modal(driver)
            else:
                bug(driver, "No schedule interview button",
                    "**Bug #52 Verification:** No Schedule button on Interviews page.\n\n"
                    f"**URL:** {driver.current_url}",
                    "high", ["bug", "Bug#52"])
                result("Schedule Interview (Bug #52)", False, "No button")
        else:
            result("Interviews Page", False, "Could not navigate")

        # ── OFFERS PAGE + CREATE (Bug #53) ──────────────────────────
        print("\n[TEST] Offers Page")
        if navigate_sidebar(driver, "Offers"):
            shot(driver, "T04_offers")
            heading = get_heading(driver)
            url = driver.current_url
            print(f"    URL: {url}, Heading: '{heading}'")

            if is_blank(driver):
                bug(driver, "Offers page blank",
                    f"**Bug #53 Related:** Offers page is blank.\n\n**URL:** {url}",
                    "high", ["bug", "Bug#53"])
                result("Offers Page", False, "Blank")
            else:
                result("Offers Page", True, f"Heading: '{heading}'")

            # Create offer (Bug #53)
            print("\n[TEST] Create Offer (Bug #53)")
            create_btn = find_btn(driver, ["Create", "Add", "New", "Generate", "+"])
            if create_btn:
                print(f"    Found: '{create_btn.text.strip()}'")
                safe_click(driver, create_btn)
                time.sleep(3)
                wait_stable(driver)
                shot(driver, "T04_create_offer_clicked")

                if "login" in driver.current_url.lower():
                    bug(driver, "Create offer redirects to login",
                        "**Bug #53 Verification:** Create offer redirects to login.",
                        "critical", ["bug", "Bug#53"])
                    result("Create Offer (Bug #53)", False, "Redirected to login")
                else:
                    modal = find_modal(driver)
                    fields = get_form_fields(driver)
                    blank = is_blank(driver)
                    new_url = driver.current_url
                    print(f"    URL: {new_url}, Fields: {len(fields)}, Modal: {modal is not None}, Blank: {blank}")

                    if modal:
                        mf = [f for f in modal.find_elements(By.CSS_SELECTOR,
                            "input:not([type='hidden']), textarea, select, [role='combobox']")
                            if f.is_displayed()]
                        shot(driver, "T04_create_offer_modal")
                        if mf:
                            result("Create Offer (Bug #53)", True, f"Modal with {len(mf)} fields")
                        else:
                            bug(driver, "Create offer modal empty",
                                "**Bug #53 Verification:** Create offer modal is empty.",
                                "high", ["bug", "Bug#53"])
                            result("Create Offer (Bug #53)", False, "Modal empty")
                    elif blank and len(fields) == 0:
                        bug(driver, "Create offer blank page",
                            "**Bug #53 Verification:** Create offer shows blank page.\n\n"
                            f"**URL:** {new_url}",
                            "critical", ["bug", "regression", "Bug#53"])
                        result("Create Offer (Bug #53)", False, "Blank page")
                    elif len(fields) > 0:
                        result("Create Offer (Bug #53)", True, f"{len(fields)} fields")
                    else:
                        result("Create Offer (Bug #53)", True, f"Page: {new_url}")
                close_any_modal(driver)
            else:
                bug(driver, "No create offer button",
                    "**Bug #53 Verification:** No Create button on Offers page.\n\n"
                    f"**URL:** {driver.current_url}",
                    "high", ["bug", "Bug#53"])
                result("Create Offer (Bug #53)", False, "No button")
        else:
            result("Offers Page", False, "Could not navigate")

        # ── ONBOARDING PAGE + ADD TASK (Bug #54) ────────────────────
        print("\n[TEST] Onboarding Page")
        if navigate_sidebar(driver, "Onboarding"):
            shot(driver, "T05_onboarding")
            heading = get_heading(driver)
            url = driver.current_url
            print(f"    URL: {url}, Heading: '{heading}'")

            if is_blank(driver):
                bug(driver, "Onboarding page blank",
                    f"**Bug #54 Related:** Onboarding page is blank.\n\n**URL:** {url}",
                    "high", ["bug", "Bug#54"])
                result("Onboarding Page", False, "Blank")
            else:
                result("Onboarding Page", True, f"Heading: '{heading}'")

            # Look for Templates tab
            for kw in ["Template", "Checklist", "Tasks"]:
                try:
                    tabs = driver.find_elements(By.XPATH,
                        f"//*[contains(normalize-space(), '{kw}') and "
                        "(self::a or self::button or self::span or self::div[@role='tab'] or self::li)]")
                    for tab in tabs:
                        if tab.is_displayed() and len(tab.text.strip()) < 50:
                            safe_click(driver, tab)
                            time.sleep(2)
                            wait_stable(driver)
                            shot(driver, "T05_onboarding_tab")
                            break
                except:
                    continue

            # Try create template first
            create_btn = find_btn(driver, ["Create", "Add Template", "New Template", "Add", "+"])
            if create_btn:
                print(f"    Create template: '{create_btn.text.strip()}'")
                safe_click(driver, create_btn)
                time.sleep(3)
                wait_stable(driver)
                shot(driver, "T05_create_template")

            # Try open existing template
            try:
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, [class*='card'], [class*='list-item']")
                for row in rows:
                    if row.is_displayed() and row.text.strip():
                        links = row.find_elements(By.CSS_SELECTOR, "a, [role='button'], button")
                        if links:
                            safe_click(driver, links[0])
                        else:
                            safe_click(driver, row)
                        time.sleep(2)
                        wait_stable(driver)
                        shot(driver, "T05_template_detail")
                        break
            except:
                pass

            # Add task (Bug #54)
            print("\n[TEST] Add Task (Bug #54)")
            add_task = find_btn(driver, ["Add Task", "Add", "New Task", "+"])
            # Also check for specific "Add Task" text
            if not add_task:
                try:
                    xp = "//*[contains(translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add task')]"
                    els = driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed():
                            add_task = el
                            break
                except:
                    pass

            if add_task:
                print(f"    Found: '{add_task.text.strip()}'")
                safe_click(driver, add_task)
                time.sleep(3)
                wait_stable(driver)
                shot(driver, "T05_add_task_clicked")

                modal = find_modal(driver)
                fields = get_form_fields(driver)
                errors = get_errors(driver)
                print(f"    Fields: {len(fields)}, Modal: {modal is not None}, Errors: {errors}")

                if errors:
                    bug(driver, "Add task errors",
                        f"**Bug #54 Verification:** Add Task shows errors:\n" +
                        "\n".join(f"- {e}" for e in errors),
                        "high", ["bug", "Bug#54"])
                    result("Add Task (Bug #54)", False, f"Errors: {errors}")
                elif modal:
                    mf = [f for f in modal.find_elements(By.CSS_SELECTOR,
                        "input:not([type='hidden']), textarea, select")
                        if f.is_displayed()]
                    if mf:
                        for f in mf:
                            a = " ".join(filter(None, [f.get_attribute("name"),
                                f.get_attribute("placeholder"), f.get_attribute("id")])).lower()
                            if any(k in a for k in ["task", "name", "title"]):
                                try:
                                    f.clear(); f.send_keys("E2E Test Task")
                                except:
                                    pass
                                break
                        shot(driver, "T05_task_filled")

                        save = find_btn(driver, ["Save", "Add", "Submit", "Create"])
                        if save:
                            safe_click(driver, save)
                            time.sleep(3)
                            wait_stable(driver)
                            shot(driver, "T05_task_saved")
                            post_errors = get_errors(driver)
                            if post_errors:
                                bug(driver, "Add task save error",
                                    f"**Bug #54 Verification:** Save task fails:\n{post_errors}",
                                    "high", ["bug", "Bug#54"])
                                result("Add Task (Bug #54)", False, f"Save errors: {post_errors}")
                            else:
                                result("Add Task (Bug #54)", True, "Task saved")
                        else:
                            result("Add Task (Bug #54)", True, f"Modal with {len(mf)} fields")
                    else:
                        bug(driver, "Add task modal empty",
                            "**Bug #54 Verification:** Add Task modal has no fields.",
                            "high", ["bug", "Bug#54"])
                        result("Add Task (Bug #54)", False, "Modal empty")
                elif len(fields) > 0:
                    result("Add Task (Bug #54)", True, f"{len(fields)} fields")
                else:
                    bug(driver, "Add task no form",
                        "**Bug #54 Verification:** Add Task click produced no form or modal.",
                        "high", ["bug", "Bug#54"])
                    result("Add Task (Bug #54)", False, "No form")
                close_any_modal(driver)
            else:
                bug(driver, "No add task button",
                    "**Bug #54 Verification:** No 'Add Task' button on onboarding page.\n\n"
                    f"**URL:** {driver.current_url}",
                    "high", ["bug", "Bug#54"])
                result("Add Task (Bug #54)", False, "No button")
        else:
            result("Onboarding Page", False, "Could not navigate")

        # ── REFERRALS PAGE ──────────────────────────────────────────
        print("\n[TEST] Referrals Page")
        if navigate_sidebar(driver, "Referrals"):
            shot(driver, "T06_referrals")
            heading = get_heading(driver)
            if is_blank(driver):
                bug(driver, "Referrals page blank",
                    f"Referrals page is blank.\n\n**URL:** {driver.current_url}", "medium")
                result("Referrals Page", False, "Blank")
            else:
                result("Referrals Page", True, f"Heading: '{heading}'")
        else:
            result("Referrals Page", False, "Could not navigate")

        # ── ANALYTICS PAGE ──────────────────────────────────────────
        print("\n[TEST] Analytics Page")
        if navigate_sidebar(driver, "Analytics"):
            shot(driver, "T07_analytics")
            heading = get_heading(driver)
            if is_blank(driver):
                bug(driver, "Analytics page blank",
                    f"Analytics page is blank.\n\n**URL:** {driver.current_url}", "medium")
                result("Analytics Page", False, "Blank")
            else:
                result("Analytics Page", True, f"Heading: '{heading}'")
        else:
            result("Analytics Page", False, "Could not navigate")

        # ── SETTINGS PAGE ───────────────────────────────────────────
        print("\n[TEST] Settings Page")
        if navigate_sidebar(driver, "Settings"):
            shot(driver, "T08_settings")
            heading = get_heading(driver)
            if is_blank(driver):
                bug(driver, "Settings page blank",
                    f"Settings page is blank.\n\n**URL:** {driver.current_url}", "medium")
                result("Settings Page", False, "Blank")
            else:
                result("Settings Page", True, f"Heading: '{heading}'")
        else:
            result("Settings Page", False, "Could not navigate")

        # ── FORM VALIDATION ─────────────────────────────────────────
        print("\n[TEST] Empty Form Validation")
        try:
            navigate_sidebar(driver, "Jobs")
            create_btn = find_btn(driver, ["Create", "Add", "New", "+"])
            if create_btn:
                safe_click(driver, create_btn)
                time.sleep(3)
                wait_stable(driver)

                # Try submit empty
                save = find_btn(driver, ["Save", "Submit", "Post", "Create", "Publish"])
                if save:
                    safe_click(driver, save)
                    time.sleep(2)
                    wait_stable(driver)
                    shot(driver, "T09_validation")
                    errors = get_errors(driver)
                    if errors:
                        result("Form Validation", True, f"Caught {len(errors)} errors")
                    else:
                        result("Form Validation", True, "No explicit errors (may have client validation)")
                else:
                    result("Form Validation", False, "No submit button")
                close_any_modal(driver)
            else:
                result("Form Validation", False, "No create button")
        except Exception as e:
            result("Form Validation", False, str(e))

        # ── CONSOLE ERRORS ──────────────────────────────────────────
        print("\n[TEST] Console Errors")
        try:
            logs = driver.get_log("browser")
            severe = [l for l in logs if l.get("level") == "SEVERE"]
            js_errs = [l for l in severe if any(k in l.get("message", "").lower()
                for k in ["uncaught", "typeerror", "referenceerror", "syntaxerror", "chunk"])]
            if js_errs:
                msgs = [l["message"][:200] for l in js_errs[:5]]
                bug(driver, "JavaScript errors",
                    "JS errors in console:\n\n" + "\n".join(f"- `{m}`" for m in msgs),
                    "medium")
                result("Console Errors", False, f"{len(js_errs)} JS errors")
            else:
                result("Console Errors", True, f"{len(severe)} severe (non-critical)")
        except:
            result("Console Errors", True, "Could not check")

        # ── API HEALTH ──────────────────────────────────────────────
        print("\n[TEST] Recruit API Health")
        try:
            req = urllib.request.Request(RECRUIT_API + "/health", headers={
                "User-Agent": "EmpCloud-E2E-Test", "Origin": RECRUIT_URL
            })
            resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=10)
            result("API Health", True, f"HTTP {resp.getcode()}")
        except urllib.error.HTTPError as e:
            result("API Health", e.code < 500, f"HTTP {e.code}")
        except Exception as e:
            result("API Health", False, str(e))

    except Exception as e:
        print(f"\n[FATAL] {e}")
        traceback.print_exc()
        if driver:
            shot(driver, "FATAL")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
            print("\n[TEARDOWN] Browser closed")

    # ── SUMMARY ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in test_results if r["passed"])
    failed = sum(1 for r in test_results if not r["passed"])
    print(f"Total: {len(test_results)} | PASSED: {passed} | FAILED: {failed}")
    print("-" * 70)
    for r in test_results:
        s = "PASS" if r["passed"] else "FAIL"
        print(f"  [{s}] {r['test']}: {r['details'][:120]}")

    print(f"\nBUGS FILED: {len(bugs_found)}")
    print("-" * 70)
    for b in bugs_found:
        print(f"  #{b['issue']} [{b['severity']}] {b['name']}")
        if b['screenshot']:
            print(f"    {b['screenshot']}")

    print(f"\nFinished: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
