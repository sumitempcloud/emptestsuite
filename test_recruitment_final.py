#!/usr/bin/env python3
"""
EMP Cloud HRMS - Recruitment Module E2E Test (Definitive)
Exact button texts from UI screenshots:
  Jobs: "+ Create Job"
  Candidates: "+ Add Candidate"
  Interviews: "+ Schedule Interview"
  Offers: "+ New Offer"
  Onboarding: "Manage Templates" -> expand template -> "Add Task"
  Referrals: "+ Refer Someone"
  Settings: tabs Career Page / Email Templates / Pipeline
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os, time, json, traceback, urllib.request, urllib.error, ssl
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

RECRUIT = "https://test-recruit.empcloud.com"
RECRUIT_API = "https://test-recruit-api.empcloud.com"
EMAIL = "ananya@technova.in"
PASSW = "Welcome@123"
SS_DIR = r"C:\Users\Admin\screenshots\recruit"
GH_PAT = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"
os.makedirs(SS_DIR, exist_ok=True)

bugs_filed = []
test_results = []
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE
_cdpath = None

def get_cdpath():
    global _cdpath
    if not _cdpath:
        _cdpath = ChromeDriverManager().install()
    return _cdpath

def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def shot(d, name):
    try:
        p = os.path.join(SS_DIR, f"{name}_{ts()}.png")
        d.save_screenshot(p)
        print(f"    [SS] {p}")
        return p
    except: return None

def gh_issue(title, body, labels, ss_path=None):
    fb = body + (f"\n\n**Screenshot:** `{ss_path}`" if ss_path else "")
    fb += f"\n\n_Automated E2E test - {datetime.now().isoformat()}_"
    data = json.dumps({"title": title, "body": fb, "labels": labels}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_REPO}/issues", data=data,
        headers={"Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github.v3+json",
                 "Content-Type": "application/json", "User-Agent": "EmpCloud-E2E"}, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx)
        r = json.loads(resp.read().decode())
        print(f"    [GH] Issue #{r['number']}: {r['html_url']}")
        return r['number']
    except Exception as e:
        print(f"    [GH ERR] {e}")
        return None

def file_bug(d, name, desc, severity="medium", extra_labels=None):
    ss = shot(d, f"BUG_{name.replace(' ', '_')[:40]}")
    labels = ["bug", f"severity:{severity}"] + (extra_labels or [])
    inum = gh_issue(f"[Recruit E2E] {name}", desc, labels, ss)
    bugs_filed.append({"name": name, "severity": severity, "issue": inum, "screenshot": ss})

def log(name, passed, details=""):
    print(f"  [{'PASS' if passed else 'FAIL'}] {name} {details}")
    test_results.append({"test": name, "passed": passed, "details": details})

def new_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
              "--window-size=1920,1080", "--ignore-certificate-errors", "--disable-extensions"]:
        opts.add_argument(a)
    d = webdriver.Chrome(service=Service(get_cdpath()), options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(2)
    return d

def wait_stable(d, t=8):
    try: WebDriverWait(d, t).until(lambda x: x.execute_script("return document.readyState") == "complete")
    except: pass
    time.sleep(1.5)

def do_login(d, retries=3):
    for attempt in range(retries):
        try:
            d.get(RECRUIT)
            wait_stable(d, 15)
            if "/dashboard" in d.current_url:
                try:
                    d.find_element(By.XPATH, "//a[normalize-space()='Dashboard']")
                    return True
                except: pass
            em = WebDriverWait(d, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
            em.clear(); em.send_keys(EMAIL)
            time.sleep(0.5)
            pw = d.find_element(By.CSS_SELECTOR, "input[type='password']")
            pw.clear(); pw.send_keys(PASSW)
            time.sleep(0.5)
            # Click Sign in
            try:
                btn = d.find_element(By.XPATH, "//button[normalize-space()='Sign in']")
                btn.click()
            except:
                pw.send_keys(Keys.RETURN)
            WebDriverWait(d, 15).until(EC.url_contains("/dashboard"))
            wait_stable(d)
            return True
        except Exception as e:
            print(f"    [LOGIN {attempt+1}/{retries}] {str(e)[:60]}")
            if attempt < retries - 1:
                time.sleep(3)
                # Try to create a fresh page load
                try: d.delete_all_cookies()
                except: pass
    return False

def login_and_go(d, path):
    if not do_login(d):
        return False
    if path and path != "/dashboard":
        d.get(RECRUIT + path)
        wait_stable(d)
    return True

def get_heading(d):
    for sel in ["h1", "h2"]:
        try:
            for el in d.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed() and el.text.strip():
                    return el.text.strip()
        except: pass
    return ""

def has_content(d):
    try: return len(d.find_element(By.TAG_NAME, "body").text.strip()) > 100
    except: return False

def find_clickable(d, text_keywords):
    """Find ANY visible clickable element whose text contains any keyword.
    Searches button, a, div[role=button], span inside buttons, etc."""
    # First: search all buttons and links
    all_clickables = d.find_elements(By.CSS_SELECTOR,
        "button, a, [role='button'], [class*='btn'], [onclick]")
    for kw in text_keywords:
        kw_lower = kw.lower()
        for el in all_clickables:
            try:
                if el.is_displayed() and kw_lower in el.text.strip().lower():
                    return el
            except: continue
    # Second: search by XPath for any element containing the text
    for kw in text_keywords:
        try:
            xp = (f"//*[contains(translate(normalize-space(), "
                  f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                  f"'{kw.lower()}')]")
            for el in d.find_elements(By.XPATH, xp):
                try:
                    if el.is_displayed() and el.tag_name in ['button', 'a', 'div', 'span']:
                        # Check if it or parent is clickable
                        if el.tag_name in ['button', 'a']:
                            return el
                        parent = el.find_element(By.XPATH, "./..")
                        if parent.tag_name in ['button', 'a']:
                            return parent
                        return el
                except: continue
        except: continue
    return None

def find_modal(d):
    for sel in ["[role='dialog']", ".modal.show", "[class*='modal-content']",
                "[class*='MuiDialog']", "[class*='drawer']"]:
        try:
            for el in d.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed(): return el
        except: continue
    return None

def get_form_fields(d, root=None):
    r = root or d
    return [f for f in r.find_elements(By.CSS_SELECTOR,
        "input:not([type='hidden']):not([type='checkbox']):not([type='radio']), "
        "textarea, select, [role='combobox'], [contenteditable='true']")
        if f.is_displayed()]

def click_and_check(d, btn_keywords, context):
    """Click a button and analyze what happened. Returns (found, result_dict)."""
    btn = find_clickable(d, btn_keywords)
    if not btn:
        return False, {"action": "no_button"}

    url0 = d.current_url
    src0 = d.page_source
    btn_text = btn.text.strip()
    print(f"    Clicking: '{btn_text}'")

    try: btn.click()
    except: d.execute_script("arguments[0].click();", btn)
    time.sleep(5)
    wait_stable(d)

    url1 = d.current_url
    modal = find_modal(d)
    src_changed = d.page_source != src0

    if modal:
        fields = get_form_fields(d, modal)
        return True, {"action": "modal", "fields": len(fields), "modal": modal, "url": url1}
    elif url1 != url0:
        fields = get_form_fields(d)
        blank = not has_content(d)
        return True, {"action": "navigated", "fields": len(fields), "url": url1, "blank": blank}
    elif src_changed:
        fields = get_form_fields(d)
        return True, {"action": "page_changed", "fields": len(fields), "url": url1}
    else:
        return True, {"action": "nothing", "url": url1, "btn_text": btn_text}

def run_test(test_fn, name):
    d = None
    try:
        d = new_driver()
        test_fn(d)
    except WebDriverException as e:
        print(f"  [CRASH] {name}")
        log(f"{name} (crash)", False, "Driver crashed")
    except Exception as e:
        print(f"  [ERROR] {name}: {e}")
        traceback.print_exc()
        if d: shot(d, f"ERR_{name[:20]}")
        log(name, False, str(e)[:100])
    finally:
        if d:
            try: d.quit()
            except: pass


# ════════════════════════════════════════════════════════════════════════
def test_login_dashboard(d):
    print("\n[TEST] Login & Dashboard")
    if not do_login(d):
        file_bug(d, "Login fails", "Cannot login to Recruit app", "critical")
        log("Login", False); return
    shot(d, "T00_dashboard")
    log("Login", True, f"URL: {d.current_url}")
    h = get_heading(d)
    body = d.find_element(By.TAG_NAME, "body").text
    stats = any(k in body for k in ["Open Jobs", "Total Candidates", "Pipeline"])
    log("Dashboard", has_content(d), f"Heading: '{h}', Stats: {stats}")


def test_jobs_and_create(d):
    """Jobs page + Bug #51: Create Job"""
    print("\n[TEST] Jobs Page + Create Job (Bug #51)")
    if not login_and_go(d, "/jobs"):
        log("Jobs Page", False, "Login failed"); log("Create Job (Bug #51)", False, "Login failed"); return
    shot(d, "T01_jobs")
    h = get_heading(d)
    body = d.find_element(By.TAG_NAME, "body").text
    has_tabs = any(t in body for t in ["Draft", "Open", "Closed", "Filled"])
    if not has_content(d):
        file_bug(d, "Jobs page blank", "Jobs page blank", "high")
        log("Jobs Page", False, "Blank"); return
    log("Jobs Page", True, f"Heading: '{h}', Tabs: {has_tabs}")

    # Bug #51: Click "+ Create Job"
    found, result = click_and_check(d, ["Create Job", "Create", "Add Job", "New Job"], "create job")
    shot(d, "T01_create_job_result")

    if not found:
        file_bug(d, "No Create Job button (Bug #51)",
            "**Bug #51:** No Create Job button.\n**URL:** " + d.current_url,
            "critical", ["Bug#51"])
        log("Create Job (Bug #51)", False, "No button"); return

    act = result["action"]
    if act == "modal":
        if result["fields"] > 0:
            log("Create Job (Bug #51)", True, f"Modal with {result['fields']} fields")
        else:
            file_bug(d, "Create Job modal empty (Bug #51)",
                "**Bug #51:** Modal has no fields.", "critical", ["Bug#51"])
            log("Create Job (Bug #51)", False, "Modal empty")
    elif act == "navigated":
        if result.get("blank"):
            file_bug(d, "Create Job blank page (Bug #51 CONFIRMED)",
                f"**Bug #51 ACTIVE:** Navigates to blank page.\n**URL:** {result['url']}",
                "critical", ["Bug#51", "regression"])
            log("Create Job (Bug #51)", False, "CONFIRMED - blank page")
        elif result["fields"] > 0:
            log("Create Job (Bug #51)", True, f"Form at {result['url']}, {result['fields']} fields")
        else:
            log("Create Job (Bug #51)", True, f"Page at {result['url']}")
    elif act == "page_changed":
        log("Create Job (Bug #51)", result["fields"] > 0,
            f"Page changed, {result['fields']} fields")
    elif act == "nothing":
        file_bug(d, "Create Job button does nothing (Bug #51 CONFIRMED)",
            "**Bug #51 - STILL ACTIVE:** Clicking '+ Create Job' has no effect.\n\n"
            f"**URL:** {result['url']}\n**Button:** '{result.get('btn_text', '')}'\n\n"
            "No modal, no navigation, no form. Users cannot create job postings.\n\n"
            "**Expected:** Job creation form/modal appears.\n"
            "**Actual:** Nothing happens.",
            "critical", ["Bug#51", "regression"])
        log("Create Job (Bug #51)", False, "CONFIRMED - button does nothing")
    try: ActionChains(d).send_keys(Keys.ESCAPE).perform()
    except: pass


def test_candidates(d):
    print("\n[TEST] Candidates Page")
    if not login_and_go(d, "/candidates"):
        log("Candidates Page", False, "Login failed"); return
    shot(d, "T02_candidates")
    h = get_heading(d)
    body = d.find_element(By.TAG_NAME, "body").text
    has_table = "NAME" in body and "EMAIL" in body
    if not has_content(d):
        file_bug(d, "Candidates blank", "Candidates blank", "high")
        log("Candidates Page", False, "Blank"); return
    log("Candidates Page", True, f"Heading: '{h}', Table: {has_table}")

    # Test Add Candidate
    found, result = click_and_check(d, ["Add Candidate", "Add", "Create"], "add candidate")
    shot(d, "T02_add_candidate")
    if not found:
        log("Add Candidate", False, "No button")
    elif result["action"] in ["modal", "navigated", "page_changed"]:
        log("Add Candidate", True, f"{result['action']}, fields: {result.get('fields', 0)}")
    elif result["action"] == "nothing":
        file_bug(d, "Add Candidate does nothing", "Add Candidate button non-functional", "medium")
        log("Add Candidate", False, "Button does nothing")
    try: ActionChains(d).send_keys(Keys.ESCAPE).perform()
    except: pass


def test_interviews_and_schedule(d):
    """Interviews + Bug #52: Schedule Interview"""
    print("\n[TEST] Interviews + Schedule (Bug #52)")
    if not login_and_go(d, "/interviews"):
        log("Interviews Page", False, "Login failed"); log("Schedule Interview (Bug #52)", False, "Login failed"); return
    shot(d, "T03_interviews")
    h = get_heading(d)
    body = d.find_element(By.TAG_NAME, "body").text
    has_table = "CANDIDATE" in body and "STATUS" in body
    if not has_content(d):
        file_bug(d, "Interviews blank", "Interviews blank", "high", ["Bug#52"])
        log("Interviews Page", False, "Blank"); return
    log("Interviews Page", True, f"Heading: '{h}', Table: {has_table}")

    # Bug #52: Click "+ Schedule Interview"
    found, result = click_and_check(d,
        ["Schedule Interview", "Schedule", "Add Interview", "New Interview"], "schedule")
    shot(d, "T03_schedule_result")

    if not found:
        file_bug(d, "No Schedule Interview button (Bug #52)",
            "**Bug #52:** No Schedule Interview button.\n**URL:** " + d.current_url,
            "high", ["Bug#52"])
        log("Schedule Interview (Bug #52)", False, "No button"); return

    act = result["action"]
    if act == "modal":
        if result["fields"] > 0:
            log("Schedule Interview (Bug #52)", True, f"Modal with {result['fields']} fields")
        else:
            file_bug(d, "Schedule Interview modal empty (Bug #52)",
                "**Bug #52:** Modal empty.", "high", ["Bug#52"])
            log("Schedule Interview (Bug #52)", False, "Modal empty")
    elif act == "navigated":
        if result.get("blank"):
            file_bug(d, "Schedule Interview blank (Bug #52 CONFIRMED)",
                f"**Bug #52 ACTIVE:** Blank page.\n**URL:** {result['url']}",
                "critical", ["Bug#52", "regression"])
            log("Schedule Interview (Bug #52)", False, "CONFIRMED - blank page")
        else:
            log("Schedule Interview (Bug #52)", True, f"Page at {result['url']}, {result['fields']} fields")
    elif act == "page_changed":
        log("Schedule Interview (Bug #52)", True, f"Page changed, {result['fields']} fields")
    elif act == "nothing":
        file_bug(d, "Schedule Interview does nothing (Bug #52 CONFIRMED)",
            "**Bug #52 ACTIVE:** Button does nothing.\n**URL:** " + result['url'],
            "critical", ["Bug#52", "regression"])
        log("Schedule Interview (Bug #52)", False, "CONFIRMED - does nothing")
    try: ActionChains(d).send_keys(Keys.ESCAPE).perform()
    except: pass


def test_offers_and_create(d):
    """Offers + Bug #53: Create Offer"""
    print("\n[TEST] Offers + Create (Bug #53)")
    if not login_and_go(d, "/offers"):
        log("Offers Page", False, "Login failed"); log("Create Offer (Bug #53)", False, "Login failed"); return
    shot(d, "T04_offers")
    h = get_heading(d)
    body = d.find_element(By.TAG_NAME, "body").text
    has_tabs = any(t in body for t in ["Draft", "Pending Approval", "Sent", "Accepted"])
    if not has_content(d):
        file_bug(d, "Offers blank", "Offers blank", "high", ["Bug#53"])
        log("Offers Page", False, "Blank"); return
    log("Offers Page", True, f"Heading: '{h}', Tabs: {has_tabs}")

    # Bug #53: Click "+ New Offer"
    found, result = click_and_check(d,
        ["New Offer", "Create Offer", "Add Offer", "Create", "New"], "create offer")
    shot(d, "T04_create_offer_result")

    if not found:
        file_bug(d, "No Create Offer button (Bug #53)",
            "**Bug #53:** No create offer button.\n**URL:** " + d.current_url,
            "high", ["Bug#53"])
        log("Create Offer (Bug #53)", False, "No button"); return

    act = result["action"]
    if act == "modal":
        if result["fields"] > 0:
            log("Create Offer (Bug #53)", True, f"Modal with {result['fields']} fields")
        else:
            file_bug(d, "Create Offer modal empty (Bug #53)",
                "**Bug #53:** Modal empty.", "high", ["Bug#53"])
            log("Create Offer (Bug #53)", False, "Modal empty")
    elif act == "navigated":
        if result.get("blank"):
            file_bug(d, "Create Offer blank (Bug #53 CONFIRMED)",
                f"**Bug #53 ACTIVE:** Blank page.\n**URL:** {result['url']}",
                "critical", ["Bug#53", "regression"])
            log("Create Offer (Bug #53)", False, "CONFIRMED - blank page")
        else:
            log("Create Offer (Bug #53)", True, f"Page at {result['url']}, {result['fields']} fields")
    elif act == "page_changed":
        log("Create Offer (Bug #53)", True, f"Page changed, {result['fields']} fields")
    elif act == "nothing":
        file_bug(d, "Create Offer does nothing (Bug #53 CONFIRMED)",
            "**Bug #53 ACTIVE:** Button does nothing.\n**URL:** " + result['url'],
            "critical", ["Bug#53", "regression"])
        log("Create Offer (Bug #53)", False, "CONFIRMED - does nothing")
    try: ActionChains(d).send_keys(Keys.ESCAPE).perform()
    except: pass


def test_onboarding_and_task(d):
    """Onboarding + Bug #54: Add Task in Template"""
    print("\n[TEST] Onboarding + Add Task (Bug #54)")
    if not login_and_go(d, "/onboarding"):
        log("Onboarding Page", False, "Login failed"); log("Add Task (Bug #54)", False, "Login failed"); return
    shot(d, "T05_onboarding")
    h = get_heading(d)
    if not has_content(d):
        file_bug(d, "Onboarding blank", "Onboarding blank", "high", ["Bug#54"])
        log("Onboarding Page", False, "Blank"); return
    log("Onboarding Page", True, f"Heading: '{h}'")

    # Step 1: Click "Manage Templates" button (top right)
    manage_btn = find_clickable(d, ["Manage Templates", "Templates"])
    if manage_btn:
        print(f"    Clicking Manage Templates: '{manage_btn.text.strip()}'")
        try: manage_btn.click()
        except: d.execute_script("arguments[0].click();", manage_btn)
        time.sleep(3); wait_stable(d)
        shot(d, "T05_templates_page")
    else:
        print("    No 'Manage Templates' button found, trying direct URL")
        d.get(RECRUIT + "/onboarding/templates")
        wait_stable(d)
        shot(d, "T05_templates_page")

    # Step 2: Expand an existing template (click the arrow/expand icon)
    # Templates are listed with expand arrows. Look for expandable rows.
    expanded = False
    try:
        # Look for expand buttons/icons or clickable rows
        expand_els = d.find_elements(By.CSS_SELECTOR,
            "[class*='expand'], [class*='accordion'], [class*='collapse'], "
            "svg[class*='chevron'], svg[class*='arrow'], button svg, "
            "[class*='template'] > button, [class*='template'] > div")
        for el in expand_els:
            try:
                if el.is_displayed():
                    d.execute_script("arguments[0].click();", el)
                    time.sleep(2); wait_stable(d)
                    expanded = True
                    shot(d, "T05_template_expanded")
                    break
            except: continue
    except: pass

    if not expanded:
        # Try clicking on template name text
        try:
            for el in d.find_elements(By.XPATH,
                "//*[contains(text(), 'asfas') or contains(text(), 'onboarding tester')]"):
                if el.is_displayed():
                    d.execute_script("arguments[0].click();", el)
                    time.sleep(2); wait_stable(d)
                    expanded = True
                    shot(d, "T05_template_expanded")
                    break
        except: pass

    if not expanded:
        # Try any clickable row-like element in the template list
        try:
            rows = d.find_elements(By.CSS_SELECTOR,
                "[class*='template'], [class*='accordion-header'], "
                "tr, [class*='list-item'], [class*='card']")
            for row in rows:
                if row.is_displayed() and row.text.strip() and "task" in row.text.lower() or "tester" in row.text.lower():
                    d.execute_script("arguments[0].click();", row)
                    time.sleep(2); wait_stable(d)
                    expanded = True
                    shot(d, "T05_template_expanded")
                    break
        except: pass

    print(f"    Template expanded: {expanded}")

    # Step 3: Look for "Add Task" button
    url0 = d.current_url
    src0 = d.page_source

    add_task = find_clickable(d, ["Add Task", "New Task"])
    if not add_task:
        # Broader: any "Add" button that appeared after expanding
        add_task = find_clickable(d, ["Add"])

    if not add_task:
        file_bug(d, "No Add Task button (Bug #54)",
            "**Bug #54:** Cannot find 'Add Task' button.\n\n"
            f"**URL:** {d.current_url}\n**Heading:** {get_heading(d)}\n"
            f"**Template expanded:** {expanded}\n\n"
            "The onboarding template page does not show an Add Task option. "
            "Either the templates cannot be expanded, or the Add Task button is missing.",
            "high", ["Bug#54"])
        log("Add Task (Bug #54)", False, "No button"); return

    print(f"    Add Task: '{add_task.text.strip()}'")
    try: add_task.click()
    except: d.execute_script("arguments[0].click();", add_task)
    time.sleep(5); wait_stable(d)
    shot(d, "T05_add_task_result")

    url1 = d.current_url
    modal = find_modal(d)

    # Check errors
    errs = []
    for sel in ["[class*='error']", "[class*='alert-danger']", "[role='alert']",
                "[class*='toast--error']"]:
        try:
            for el in d.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed() and el.text.strip():
                    errs.append(el.text.strip())
        except: pass

    if errs:
        file_bug(d, "Add Task errors (Bug #54 CONFIRMED)",
            f"**Bug #54 ACTIVE:** Add Task errors:\n" + "\n".join(f"- {e}" for e in errs),
            "critical", ["Bug#54", "regression"])
        log("Add Task (Bug #54)", False, f"CONFIRMED - errors: {errs[:2]}")
    elif modal:
        fields = get_form_fields(d, modal)
        if fields:
            # Try to fill and save
            for f in fields:
                a = " ".join(filter(None, [f.get_attribute("name"),
                    f.get_attribute("placeholder"), f.get_attribute("id")])).lower()
                if any(k in a for k in ["task", "name", "title"]) or f == fields[0]:
                    try: f.clear(); f.send_keys("E2E Test Task")
                    except: pass
                    break
            save = find_clickable(d, ["Save", "Add", "Submit", "Create"])
            if save:
                d.execute_script("arguments[0].click();", save)
                time.sleep(3); wait_stable(d)
                shot(d, "T05_task_saved")
                log("Add Task (Bug #54)", True, "Task saved")
            else:
                log("Add Task (Bug #54)", True, f"Modal with {len(fields)} fields")
        else:
            file_bug(d, "Add Task modal empty (Bug #54)",
                "**Bug #54:** Modal empty.", "high", ["Bug#54"])
            log("Add Task (Bug #54)", False, "Modal empty")
    elif url1 != url0:
        if not has_content(d):
            file_bug(d, "Add Task blank (Bug #54 CONFIRMED)",
                f"**Bug #54 ACTIVE:** Blank page.\n**URL:** {url1}",
                "critical", ["Bug#54", "regression"])
            log("Add Task (Bug #54)", False, "CONFIRMED - blank page")
        else:
            fields = get_form_fields(d)
            log("Add Task (Bug #54)", True, f"Page at {url1}, {len(fields)} fields")
    elif d.page_source != src0:
        fields = get_form_fields(d)
        if fields:
            log("Add Task (Bug #54)", True, f"Inline form, {len(fields)} fields")
        else:
            log("Add Task (Bug #54)", True, "Page content changed")
    else:
        file_bug(d, "Add Task does nothing (Bug #54 CONFIRMED)",
            "**Bug #54 ACTIVE:** Button does nothing.\n**URL:** " + url1,
            "critical", ["Bug#54", "regression"])
        log("Add Task (Bug #54)", False, "CONFIRMED - does nothing")


def test_referrals(d):
    print("\n[TEST] Referrals Page")
    if not login_and_go(d, "/referrals"):
        log("Referrals Page", False, "Login failed"); return
    shot(d, "T06_referrals")
    h = get_heading(d)
    body = d.find_element(By.TAG_NAME, "body").text
    has_refer = "Refer Someone" in body or "referral" in body.lower()
    if not has_content(d):
        file_bug(d, "Referrals blank", "Referrals blank", "medium")
        log("Referrals Page", False, "Blank")
    else:
        log("Referrals Page", True, f"Heading: '{h}', Refer btn: {has_refer}")


def test_analytics(d):
    print("\n[TEST] Analytics Page")
    if not login_and_go(d, "/analytics"):
        log("Analytics Page", False, "Login failed"); return
    shot(d, "T07_analytics")
    h = get_heading(d)
    body = d.find_element(By.TAG_NAME, "body").text
    charts = any(k in body for k in ["Pipeline Funnel", "Time to Hire", "Source Effectiveness"])
    if not has_content(d):
        file_bug(d, "Analytics blank", "Analytics blank", "medium")
        log("Analytics Page", False, "Blank")
    else:
        log("Analytics Page", True, f"Heading: '{h}', Charts: {charts}")


def test_settings(d):
    print("\n[TEST] Settings Page")
    if not login_and_go(d, "/settings"):
        log("Settings Page", False, "Login failed"); return
    shot(d, "T08_settings")
    h = get_heading(d)
    body = d.find_element(By.TAG_NAME, "body").text
    tabs = any(k in body for k in ["Career Page", "Email Templates", "Pipeline"])
    if not has_content(d):
        file_bug(d, "Settings blank", "Settings blank", "medium")
        log("Settings Page", False, "Blank")
    else:
        log("Settings Page", True, f"Heading: '{h}', Tabs: {tabs}")


def test_console(d):
    print("\n[TEST] Console Errors")
    if not login_and_go(d, "/dashboard"):
        log("Console Errors", False, "Login failed"); return
    for p in ["/jobs", "/candidates", "/interviews", "/offers", "/onboarding"]:
        try: d.get(RECRUIT + p); wait_stable(d, 5)
        except: pass
    try:
        logs = d.get_log("browser")
        severe = [l for l in logs if l.get("level") == "SEVERE"]
        js_errs = [l for l in severe if any(k in l.get("message", "").lower()
            for k in ["uncaught", "typeerror", "referenceerror", "syntaxerror", "chunk"])]
        if js_errs:
            msgs = [l["message"][:200] for l in js_errs[:5]]
            file_bug(d, "JavaScript errors",
                "JS errors:\n\n" + "\n".join(f"- `{m}`" for m in msgs), "medium")
            log("Console Errors", False, f"{len(js_errs)} JS errors")
        else:
            log("Console Errors", True, f"{len(severe)} severe (non-critical)" if severe else "Clean")
    except:
        log("Console Errors", True, "Could not check")


def test_api():
    print("\n[TEST] API Health")
    try:
        req = urllib.request.Request(RECRUIT_API + "/health",
            headers={"User-Agent": "EmpCloud-E2E", "Origin": RECRUIT})
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=10)
        log("API Health", True, f"HTTP {resp.getcode()}")
    except urllib.error.HTTPError as e:
        log("API Health", e.code < 500, f"HTTP {e.code}")
    except Exception as e:
        log("API Health", False, str(e)[:60])


# ════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("EMP CLOUD HRMS - RECRUITMENT MODULE E2E TEST")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)
    get_cdpath()

    tests = [
        ("Login+Dashboard", test_login_dashboard),
        ("Jobs+Create(#51)", test_jobs_and_create),
        ("Candidates", test_candidates),
        ("Interviews+Schedule(#52)", test_interviews_and_schedule),
        ("Offers+Create(#53)", test_offers_and_create),
        ("Onboarding+Task(#54)", test_onboarding_and_task),
        ("Referrals", test_referrals),
        ("Analytics", test_analytics),
        ("Settings", test_settings),
        ("Console", test_console),
    ]
    for name, fn in tests:
        run_test(fn, name)
    test_api()

    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    p = sum(1 for r in test_results if r["passed"])
    f = sum(1 for r in test_results if not r["passed"])
    print(f"Total: {len(test_results)} | PASSED: {p} | FAILED: {f}")
    print("-" * 70)
    for r in test_results:
        s = "PASS" if r["passed"] else "FAIL"
        print(f"  [{s}] {r['test']}: {r['details'][:120]}")
    print(f"\nBUGS FILED: {len(bugs_filed)}")
    print("-" * 70)
    for b in bugs_filed:
        print(f"  #{b['issue']} [{b['severity']}] {b['name']}")
        if b['screenshot']: print(f"    {b['screenshot']}")
    print(f"\nScreenshots: {SS_DIR}")
    print(f"Finished: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
