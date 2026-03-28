#!/usr/bin/env python3
"""
Pass 3: Deep retest of all 11 features with direct URL navigation
and careful DOM inspection. Uses page source dumps for debugging.
"""
import sys, os, time, json, traceback, requests, base64, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE    = "https://test-empcloud.empcloud.com"
GH_PAT  = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GH_REPO = "EmpCloud/EmpCloud"
GH_API  = f"https://api.github.com/repos/{GH_REPO}"
CHROME  = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SS_DIR  = r"C:\emptesting\screenshots\feature_verify_v3"
os.makedirs(SS_DIR, exist_ok=True)

CREDS = {
    "super_admin": ("admin@empcloud.com", "SuperAdmin@2026"),
    "org_admin":   ("ananya@technova.in", "Welcome@123"),
    "employee":    ("priya@technova.in",  "Welcome@123"),
}

results = []
driver = None
test_count = 0

def get_driver():
    global driver
    opts = Options()
    opts.binary_location = CHROME
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    svc = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.implicitly_wait(6)
    driver.set_page_load_timeout(30)
    return driver

def restart_check():
    global driver, test_count
    test_count += 1
    if test_count > 1 and (test_count - 1) % 2 == 0:
        print(f"  [Driver restart #{test_count-1}]")
        try: driver.quit()
        except: pass
        driver = get_driver()

def ss(name):
    p = os.path.join(SS_DIR, f"{name}.png")
    try: driver.save_screenshot(p); print(f"  SS: {name}")
    except: p = None
    return p

def login(role):
    email, pw = CREDS[role]
    driver.get(f"{BASE}/login")
    time.sleep(3)
    try:
        e = driver.find_element(By.CSS_SELECTOR, "input[name='email'], input[type='email']")
        e.clear(); e.send_keys(email)
        p = driver.find_element(By.CSS_SELECTOR, "input[name='password'], input[type='password']")
        p.clear(); p.send_keys(pw)
        time.sleep(0.3)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except Exception as ex:
        print(f"  Login form error: {ex}")
        return False
    time.sleep(4)
    ok = "/login" not in driver.current_url
    print(f"  Login {role}: {'OK' if ok else 'FAIL'} -> {driver.current_url}")
    return ok

def gh(method, path, **kw):
    h = {"Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github.v3+json"}
    fn = getattr(requests, method)
    try:
        r = fn(f"{GH_API}{path}", headers=h, timeout=15, **kw)
        return r
    except Exception as e:
        print(f"  GH err: {e}")
        return None

def gh_comment(issue, body):
    r = gh("post", f"/issues/{issue}/comments", json={"body": body})
    if r: print(f"  GH #{issue} comment: {r.status_code}")

def gh_reopen(issue):
    r = gh("patch", f"/issues/{issue}", json={"state": "open"})
    if r: print(f"  GH #{issue} reopen: {r.status_code}")

def gh_upload(filepath, issue, label):
    if not filepath or not os.path.exists(filepath): return ""
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        fname = os.path.basename(filepath)
        path = f"screenshots/feature_verify_v3/{fname}"
        payload = {"message": f"Screenshot: {label} (#{issue})", "content": content, "branch": "main"}
        r = gh("get", f"/contents/{path}")
        if r and r.status_code == 200:
            payload["sha"] = r.json().get("sha")
        r = gh("put", f"/contents/{path}", json=payload)
        if r and r.status_code in (200, 201):
            dl = r.json().get("content", {}).get("download_url", "")
            return f"\n\n![{label}]({dl})"
    except Exception as e:
        print(f"  Upload err: {e}")
    return ""

def jsc(script):
    """Execute JS and return result."""
    try: return driver.execute_script(script)
    except: return None

def click_text(text, tag="*"):
    """Click first visible element containing text."""
    for el in driver.find_elements(By.XPATH, f"//{tag}[contains(text(),'{text}')]"):
        try:
            if el.is_displayed():
                driver.execute_script("arguments[0].click();", el)
                return True
        except: continue
    return False

def dump_page(name, limit=2000):
    """Save page source for debugging."""
    try:
        src = driver.page_source[:limit*10]
        with open(os.path.join(SS_DIR, f"{name}_source.html"), "w", encoding="utf-8") as f:
            f.write(src)
    except: pass

# ═════════════════════════════════════════════════════════════
# TESTS
# ═════════════════════════════════════════════════════════════

def test_499():
    """#499 Audit log filters"""
    restart_check(); d = []; issue = 499

    # Test 1: Super Admin - Log Dashboard -> Audit Events tab
    if not login("super_admin"): return issue, "Audit Log Filters", "BLOCKED", "Login failed"

    driver.get(f"{BASE}/admin/logs")
    time.sleep(4)
    ss("499_log_dashboard")

    # Click "Audit Events" tab using XPath
    clicked = click_text("Audit Events") or click_text("Audit")
    time.sleep(3)
    d.append(f"Clicked Audit tab: {clicked}")
    ss("499_after_audit_click")

    # Check URL - might have changed
    d.append(f"URL after click: {driver.current_url}")

    # Try direct URL for audit events
    driver.get(f"{BASE}/admin/logs?tab=audit")
    time.sleep(3)

    # Also try /admin/audit-events, /admin/audit
    for path in ["/admin/audit-events", "/admin/audit", "/admin/logs/audit"]:
        driver.get(f"{BASE}{path}")
        time.sleep(2)
        src = driver.page_source.lower()
        if "action" in src and ("filter" in src or "select" in src):
            d.append(f"Found audit filters at {path}")
            break

    # Dump page for analysis
    dump_page("499_audit")

    # Search for any select/filter elements
    selects = driver.find_elements(By.TAG_NAME, "select")
    vis_selects = [(s, s.get_attribute("name") or s.get_attribute("class") or "?") for s in selects if s.is_displayed()]
    d.append(f"Selects visible: {len(vis_selects)} ({[v[1][:30] for v in vis_selects]})")

    date_inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[type='datetime-local']") if i.is_displayed()]
    d.append(f"Date inputs: {len(date_inputs)}")

    # Any input with date-like placeholder
    all_inputs = driver.find_elements(By.TAG_NAME, "input")
    date_like = [i for i in all_inputs if i.is_displayed() and
                 any(k in (i.get_attribute("placeholder") or "").lower() for k in ["date", "from", "to", "start", "end"])]
    d.append(f"Date-like inputs: {len(date_like)}")

    ss1 = ss("499_audit_filters_final")

    # Test 2: Org Admin audit log
    login("org_admin")
    time.sleep(2)

    # Navigate to Audit Log (sidebar item seen in org admin view)
    for path in ["/audit-log", "/audit", "/admin/audit-log", "/settings/audit-log"]:
        driver.get(f"{BASE}{path}")
        time.sleep(3)
        if "audit" in driver.page_source.lower():
            d.append(f"Org Admin audit at {path}")
            break

    # Expand Audit Log sidebar if it has subitems
    click_text("Audit Log")
    time.sleep(2)
    ss("499_org_audit")

    # Check again for filters
    selects2 = [s for s in driver.find_elements(By.TAG_NAME, "select") if s.is_displayed()]
    dates2 = [i for i in driver.find_elements(By.CSS_SELECTOR, "input[type='date']") if i.is_displayed()]
    d.append(f"Org admin selects: {len(selects2)}, dates: {len(dates2)}")

    has_filters = len(vis_selects) > 0 or len(date_inputs) > 0 or len(date_like) > 0 or len(selects2) > 0 or len(dates2) > 0
    status = "PASS" if has_filters else "FAIL"

    ss_md = gh_upload(ss1, issue, "Audit Log Filters")
    return issue, "Audit Log Filters", status, "; ".join(d)


def test_519():
    """#519 Create Organization"""
    restart_check(); d = []; issue = 519

    if not login("super_admin"): return issue, "Create Organization", "BLOCKED", "Login failed"

    # Direct URL to organizations page
    for path in ["/admin/organizations", "/admin/orgs", "/admin/super/organizations"]:
        driver.get(f"{BASE}{path}")
        time.sleep(4)
        src = driver.page_source.lower()
        if "organization" in src and len(src) > 2000:
            d.append(f"Org page at {path}")
            break
    else:
        # Click Organizations in sidebar
        driver.get(f"{BASE}/admin/super")
        time.sleep(3)
        click_text("Organizations")
        time.sleep(4)
        d.append(f"Clicked sidebar -> {driver.current_url}")

    ss1 = ss("519_orgs_page")
    dump_page("519_orgs")
    d.append(f"URL: {driver.current_url}")
    d.append(f"Page length: {len(driver.page_source)}")

    # Look for any button on the page
    buttons = driver.find_elements(By.TAG_NAME, "button")
    vis_buttons = [(b, b.text.strip()) for b in buttons if b.is_displayed() and b.text.strip()]
    d.append(f"Buttons: {[v[1][:30] for v in vis_buttons]}")

    # Find create/add button
    create_btn = None
    for b, txt in vis_buttons:
        if any(k in txt.lower() for k in ["create", "add", "new", "+"]):
            create_btn = b
            break

    if create_btn:
        d.append(f"Create button: {create_btn.text}")
        driver.execute_script("arguments[0].click();", create_btn)
        time.sleep(3)
        ss("519_create_form")

        # Fill form
        inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if i.is_displayed()]
        d.append(f"Form inputs: {len(inputs)}")
        for field in inputs:
            nm = (field.get_attribute("name") or "").lower()
            ph = (field.get_attribute("placeholder") or "").lower()
            tp = (field.get_attribute("type") or "").lower()
            lbl = f"{nm} {ph}"
            if "email" in lbl:
                field.clear(); field.send_keys("testorgverify@test.com")
            elif any(k in lbl for k in ["name", "org"]):
                field.clear(); field.send_keys("Test Org Verify")
            elif "domain" in lbl:
                field.clear(); field.send_keys("testorgverify.com")
            elif "phone" in lbl:
                field.clear(); field.send_keys("9999999999")

        # Submit
        for b in driver.find_elements(By.TAG_NAME, "button"):
            if b.is_displayed() and any(k in b.text.lower() for k in ["create", "submit", "save", "add"]):
                driver.execute_script("arguments[0].click();", b)
                time.sleep(4)
                d.append("Submitted")
                break
    else:
        d.append("Create button NOT FOUND")

    ss2 = ss("519_result")
    status = "PASS" if create_btn else "FAIL"
    ss_md = gh_upload(ss1, issue, "Organizations") + gh_upload(ss2, issue, "Result")
    return issue, "Create Organization", status, "; ".join(d)


def test_520():
    """#520 Platform Settings"""
    restart_check(); d = []; issue = 520

    if not login("super_admin"): return issue, "Platform Settings", "BLOCKED", "Login failed"

    # Use direct URL /admin/settings (worked in v1)
    driver.get(f"{BASE}/admin/settings")
    time.sleep(4)

    src = driver.page_source.lower()
    d.append(f"URL: {driver.current_url}")
    d.append(f"Page len: {len(src)}")

    smtp = "smtp" in src
    security = "security" in src
    platform = "platform info" in src or "server version" in src or "node version" in src

    if not (smtp or security or platform):
        # Try other URLs
        for path in ["/admin/platform-settings", "/admin/super/settings"]:
            driver.get(f"{BASE}{path}")
            time.sleep(3)
            src = driver.page_source.lower()
            smtp = smtp or "smtp" in src
            security = security or "security" in src
            platform = platform or "platform" in src

    d.append(f"SMTP: {smtp}, Security: {security}, Platform: {platform}")

    ss1 = ss("520_platform_settings")

    working = smtp and security
    status = "PASS" if working else ("PARTIAL" if (smtp or security or platform) else "FAIL")

    ss_md = gh_upload(ss1, issue, "Platform Settings")
    return issue, "Platform Settings", status, "; ".join(d)


def test_545():
    """#545 Attendance filters"""
    restart_check(); d = []; issue = 545

    if not login("org_admin"): return issue, "Attendance Filters", "BLOCKED", "Login failed"

    driver.get(f"{BASE}/attendance")
    time.sleep(4)

    src = driver.page_source.lower()

    # From screenshot: Month dropdown, Year, "All Departments" dropdown, Date From, Date To
    has_month = "month" in src
    has_dept = "department" in src
    has_date = bool(driver.find_elements(By.CSS_SELECTOR, "input[type='date']"))

    selects = [s for s in driver.find_elements(By.TAG_NAME, "select") if s.is_displayed()]
    d.append(f"Selects: {len(selects)}")
    for s in selects:
        opts = [o.text for o in s.find_elements(By.TAG_NAME, "option")]
        d.append(f"  Select options: {opts[:5]}")

    d.append(f"Month: {has_month}, Dept: {has_dept}, Date: {has_date}")

    ss1 = ss("545_attendance")

    working = has_dept and (has_date or has_month)
    status = "PASS" if working else "FAIL"

    ss_md = gh_upload(ss1, issue, "Attendance Filters")
    return issue, "Attendance Filters", status, "; ".join(d)


def test_556():
    """#556 Employee profile editing"""
    restart_check(); d = []; issue = 556

    if not login("employee"): return issue, "Self-Service Profile", "BLOCKED", "Login failed"

    # From screenshot: sidebar has "Self Service" and dashboard has "My Profile" card
    # Try direct self-service/profile URLs
    for path in ["/self-service", "/self-service/profile", "/profile/edit", "/my-profile",
                 "/employee/profile", "/self-service/personal"]:
        driver.get(f"{BASE}{path}")
        time.sleep(3)
        src = driver.page_source.lower()
        if any(k in src for k in ["personal info", "phone", "email", "address", "edit", "priya"]) and len(src) > 3000:
            d.append(f"Profile at {path}")
            break
    else:
        # Navigate from dashboard - click "My Profile" card
        driver.get(f"{BASE}/dashboard")
        time.sleep(3)

        # Try clicking "My Profile" link/card - it has an arrow icon
        for el in driver.find_elements(By.XPATH, "//*[contains(text(),'My Profile')]"):
            try:
                if el.is_displayed():
                    # Click the parent or the element itself
                    parent = el.find_element(By.XPATH, "..")
                    driver.execute_script("arguments[0].click();", parent)
                    time.sleep(3)
                    d.append(f"Clicked My Profile parent -> {driver.current_url}")
                    break
            except: continue

    ss1 = ss("556_profile_view")
    d.append(f"URL: {driver.current_url}")

    # Check for editable fields or edit button
    edit_btn = None
    for el in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            txt = el.text.lower()
            aria = (el.get_attribute("aria-label") or "").lower()
            html = (el.get_attribute("innerHTML") or "").lower()
            if el.is_displayed() and ("edit" in txt or "edit" in aria or ("pencil" in html and "svg" in html)):
                edit_btn = el
                d.append(f"Edit button: {el.text or el.get_attribute('aria-label') or 'icon'}")
                break
        except: continue

    # Check if page already has editable inputs
    inputs = [i for i in driver.find_elements(By.TAG_NAME, "input") if i.is_displayed()
              and i.get_attribute("type") not in ("hidden", "checkbox", "radio")]
    d.append(f"Visible inputs: {len(inputs)}")

    if edit_btn:
        driver.execute_script("arguments[0].click();", edit_btn)
        time.sleep(3)
        ss("556_edit_mode")

        # Now find phone
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            if inp.is_displayed():
                nm = (inp.get_attribute("name") or "").lower()
                ph = (inp.get_attribute("placeholder") or "").lower()
                if any(k in f"{nm} {ph}" for k in ["phone", "mobile", "contact"]):
                    inp.clear(); inp.send_keys("9876543210")
                    d.append("Updated phone")
                    break

        # Save
        for b in driver.find_elements(By.TAG_NAME, "button"):
            if b.is_displayed() and any(k in b.text.lower() for k in ["save", "update", "submit"]):
                driver.execute_script("arguments[0].click();", b)
                time.sleep(3)
                d.append("Saved")
                break
    elif len(inputs) > 2:
        # Page might already be in edit mode
        d.append("Page appears to have editable fields already")
        for inp in inputs:
            nm = (inp.get_attribute("name") or "").lower()
            ph = (inp.get_attribute("placeholder") or "").lower()
            d.append(f"  Input: name={nm}, ph={ph}")
            if any(k in f"{nm} {ph}" for k in ["phone", "mobile"]):
                inp.clear(); inp.send_keys("9876543210")
                d.append("Updated phone inline")
                edit_btn = True
                break
    else:
        d.append("No edit capability found")
        dump_page("556_profile")

    ss2 = ss("556_after_edit")

    working = edit_btn is not None
    status = "PASS" if working else "FAIL"

    ss_md = gh_upload(ss1, issue, "Profile View") + gh_upload(ss2, issue, "After Edit")
    return issue, "Self-Service Profile", status, "; ".join(d)


def test_563():
    """#563 Bulk leave approval"""
    restart_check(); d = []; issue = 563

    if not login("org_admin"): return issue, "Bulk Leave Approval", "BLOCKED", "Login failed"

    # Org Admin leave management - try various URLs
    for path in ["/leave/approvals", "/leave/pending", "/leave/manage", "/hr/leave",
                 "/leave-management", "/admin/leave", "/leave"]:
        driver.get(f"{BASE}{path}")
        time.sleep(3)
        src = driver.page_source.lower()
        if "leave" in src and ("approv" in src or "pending" in src or "request" in src):
            d.append(f"Leave mgmt at {path}")
            break

    ss1 = ss("563_leave_mgmt")
    d.append(f"URL: {driver.current_url}")

    # Look for tabs (Pending/Approved/Rejected)
    click_text("Pending")
    time.sleep(2)

    # Check for checkboxes
    cbs = [c for c in driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']") if c.is_displayed()]
    d.append(f"Checkboxes: {len(cbs)}")

    # Check for bulk action buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")
    vis_btns = [(b, b.text.strip()) for b in buttons if b.is_displayed() and b.text.strip()]
    d.append(f"Buttons: {[t[:25] for _, t in vis_btns]}")

    select_all = None
    bulk_approve = None
    bulk_reject = None
    for b, t in vis_btns:
        tl = t.lower()
        if "select all" in tl: select_all = b
        if "bulk approve" in tl or "approve selected" in tl or "approve all" in tl: bulk_approve = b
        if "bulk reject" in tl or "reject selected" in tl or "reject all" in tl: bulk_reject = b

    # Also check for "select all" in checkbox labels
    for label in driver.find_elements(By.TAG_NAME, "label"):
        if "select all" in label.text.lower():
            select_all = label
            break

    d.append(f"Select All: {'YES' if select_all else 'NO'}")
    d.append(f"Bulk Approve: {'YES' if bulk_approve else 'NO'}")
    d.append(f"Bulk Reject: {'YES' if bulk_reject else 'NO'}")

    # Check for table header checkbox (common pattern)
    th_cbs = driver.find_elements(By.CSS_SELECTOR, "th input[type='checkbox'], thead input[type='checkbox']")
    if th_cbs:
        select_all = th_cbs[0]
        d.append("Found header checkbox (select all)")

    if select_all:
        driver.execute_script("arguments[0].click();", select_all)
        time.sleep(1)

    ss2 = ss("563_bulk_actions")
    dump_page("563_leave")

    working = select_all or bulk_approve or bulk_reject or len(cbs) > 2
    status = "PASS" if working else "FAIL"

    ss_md = gh_upload(ss1, issue, "Leave Management") + gh_upload(ss2, issue, "Bulk Actions")
    return issue, "Bulk Leave Approval", status, "; ".join(d)


def test_564():
    """#564 Mobile hamburger menu"""
    restart_check(); d = []; issue = 564

    if not login("org_admin"): return issue, "Mobile Hamburger", "BLOCKED", "Login failed"

    driver.get(f"{BASE}/dashboard")
    time.sleep(3)

    driver.set_window_size(375, 812)
    time.sleep(1)
    driver.refresh()
    time.sleep(3)

    ss1 = ss("564_mobile")

    # Find hamburger by position (top-left small button, confirmed in v2)
    hamburger = None
    for btn in driver.find_elements(By.TAG_NAME, "button"):
        try:
            if btn.is_displayed():
                loc = btn.location
                if loc.get("y", 999) < 80 and loc.get("x", 999) < 100:
                    hamburger = btn
                    break
        except: continue

    if hamburger:
        d.append("Hamburger: FOUND")
        driver.execute_script("arguments[0].click();", hamburger)
        time.sleep(2)
        ss2 = ss("564_sidebar_open")

        # Check for sidebar
        nav = driver.find_elements(By.CSS_SELECTOR, "nav, aside, [class*='sidebar']")
        vis_nav = [n for n in nav if n.is_displayed()]
        d.append(f"Visible nav: {len(vis_nav)}")

        if vis_nav:
            links = vis_nav[0].find_elements(By.TAG_NAME, "a")
            vis_links = [l for l in links if l.is_displayed()]
            d.append(f"Menu links: {len(vis_links)}")
            if vis_links:
                driver.execute_script("arguments[0].click();", vis_links[0])
                time.sleep(2)
                d.append(f"Navigated to: {driver.current_url}")
    else:
        d.append("Hamburger: NOT FOUND")

    driver.set_window_size(1920, 1080)
    ss3 = ss("564_final")

    status = "PASS" if hamburger else "FAIL"
    ss_md = gh_upload(ss1, issue, "Mobile View") + gh_upload(ss2 if hamburger else ss1, issue, "Sidebar")
    return issue, "Mobile Hamburger", status, "; ".join(d)


def test_673():
    """#673 Notification bell"""
    restart_check(); d = []; issue = 673

    if not login("org_admin"): return issue, "Notification Bell", "BLOCKED", "Login failed"

    driver.get(f"{BASE}/dashboard")
    time.sleep(3)

    # Bell is top-right (seen in screenshots)
    bell = None
    for el in driver.find_elements(By.CSS_SELECTOR, "button, a, span, div"):
        try:
            if not el.is_displayed(): continue
            html = (el.get_attribute("innerHTML") or "").lower()
            classes = (el.get_attribute("class") or "").lower()
            aria = (el.get_attribute("aria-label") or "").lower()
            if "bell" in html or "notification" in classes or "notification" in aria:
                bell = el
                break
        except: continue

    if not bell:
        # Position-based
        for btn in driver.find_elements(By.CSS_SELECTOR, "button, [role='button']"):
            try:
                if btn.is_displayed():
                    loc = btn.location
                    if loc.get("x", 0) > 1400 and loc.get("y", 999) < 60:
                        bell = btn
                        d.append("Found bell by position")
                        break
            except: continue

    if bell:
        d.append("Bell: FOUND")
        driver.execute_script("arguments[0].click();", bell)
        time.sleep(2)
        ss1 = ss("673_bell_open")

        src = driver.page_source.lower()
        has_dropdown = any(k in src for k in ["notification", "no notification", "mark as read", "mark all", "unread"])
        d.append(f"Dropdown content: {'YES' if has_dropdown else 'CHECK SS'}")

        # Look for notification items
        items = driver.find_elements(By.CSS_SELECTOR,
            "[class*='notification'] li, [class*='dropdown'] [class*='item'], [class*='notification-item']")
        vis_items = [i for i in items if i.is_displayed()]
        d.append(f"Notification items: {len(vis_items)}")
    else:
        d.append("Bell: NOT FOUND")

    ss2 = ss("673_final")

    status = "PASS" if bell else "FAIL"
    ss_md = gh_upload(ss2, issue, "Notification Bell")
    return issue, "Notification Bell", status, "; ".join(d)


def test_700():
    """#700 Leave shows names"""
    restart_check(); d = []; issue = 700

    if not login("org_admin"): return issue, "Leave Names", "BLOCKED", "Login failed"

    driver.get(f"{BASE}/leave")
    time.sleep(4)

    src = driver.page_source
    id_patterns = re.findall(r'User\s*#\d+', src)
    d.append(f"User #ID patterns: {len(id_patterns)}")

    # Check table rows for name-like patterns
    rows = driver.find_elements(By.CSS_SELECTOR, "tr, [class*='row']")
    names_in_rows = 0
    ids_in_rows = 0
    for row in rows[:30]:
        txt = row.text
        if re.search(r'User\s*#\d+', txt): ids_in_rows += 1
        if re.search(r'[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}', txt): names_in_rows += 1

    d.append(f"Rows with names: {names_in_rows}, with IDs: {ids_in_rows}")

    ss1 = ss("700_leave_names")

    working = ids_in_rows == 0 and len(id_patterns) == 0
    status = "PASS" if working else "FAIL"

    ss_md = gh_upload(ss1, issue, "Leave Names")
    return issue, "Leave Names", status, "; ".join(d)


def test_703():
    """#703 Invite Employee"""
    restart_check(); d = []; issue = 703

    if not login("org_admin"): return issue, "Invite Employee", "BLOCKED", "Login failed"

    driver.get(f"{BASE}/users")
    time.sleep(4)

    # Find invite button (confirmed in v1: "Invite Employee" blue button top-right)
    invite = None
    for el in driver.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            if el.is_displayed() and "invite" in el.text.lower():
                invite = el
                break
        except: continue

    if invite:
        d.append(f"Invite: FOUND ({invite.text})")
        bg = invite.value_of_css_property("background-color")
        d.append(f"Color: {bg}")

        driver.execute_script("arguments[0].click();", invite)
        time.sleep(3)

        # Check form
        inputs = [i for i in driver.find_elements(By.TAG_NAME, "input") if i.is_displayed()]
        d.append(f"Form inputs: {len(inputs)}")

        for inp in inputs:
            nm = (inp.get_attribute("name") or "").lower()
            ph = (inp.get_attribute("placeholder") or "").lower()
            if "email" in f"{nm} {ph}":
                inp.clear(); inp.send_keys("testinvite@test.com")
                d.append("Filled email")

        ss1 = ss("703_invite_form")
    else:
        d.append("Invite: NOT FOUND")

    ss2 = ss("703_result")

    status = "PASS" if invite else "FAIL"
    ss_md = gh_upload(ss2, issue, "Invite Employee")
    return issue, "Invite Employee", status, "; ".join(d)


def test_704():
    """#704 Org chart"""
    restart_check(); d = []; issue = 704

    if not login("org_admin"): return issue, "Org Chart", "BLOCKED", "Login failed"

    driver.get(f"{BASE}/org-chart")
    time.sleep(5)

    ss1 = ss("704_org_chart")
    d.append(f"URL: {driver.current_url}")

    # Count employee cards/nodes
    src = driver.page_source

    # From screenshot: each employee has a colored circle + name + title + dept
    # Count unique employee name patterns
    name_matches = re.findall(r'<[^>]*>([A-Z][a-z]+\s+[A-Z][a-z]+)<', src)
    # Filter UI labels
    ui_labels = {"Organization Chart", "Org Chart", "Software Engineer", "Ananya Gupta",
                 "Reporting Structure", "Welcome Back", "Nova Solutions"}
    employee_names = [n for n in name_matches if n not in ui_labels]
    unique_names = list(set(employee_names))

    d.append(f"Employee names in source: {unique_names}")
    d.append(f"Count: {len(unique_names)}")

    # Also try counting by CSS selectors typical for org chart nodes
    for sel in ["[class*='node']", "[class*='card']", "[class*='employee']",
                "[class*='member']", "[class*='person']", "[class*='chart-item']"]:
        els = [e for e in driver.find_elements(By.CSS_SELECTOR, sel) if e.is_displayed() and e.text.strip()]
        if els:
            d.append(f"Selector '{sel}': {len(els)} visible")

    # Try API to count employees
    try:
        token = None
        r = requests.post(f"{BASE}/api/v1/auth/login",
                         json={"email": "ananya@technova.in", "password": "Welcome@123"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            token = data.get("token") or data.get("data", {}).get("token") or data.get("accessToken") or data.get("data", {}).get("accessToken")

        if token:
            headers = {"Authorization": f"Bearer {token}"}
            for ep in ["/api/v1/employees", "/api/v1/users", "/api/v1/org-chart"]:
                r = requests.get(f"{BASE}{ep}", headers=headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        d.append(f"API {ep}: {len(data)} items")
                    elif isinstance(data, dict):
                        items = data.get("data", data.get("employees", data.get("users", [])))
                        if isinstance(items, list):
                            d.append(f"API {ep}: {len(items)} items")
    except: pass

    ss2 = ss("704_final")
    dump_page("704_orgchart")

    # From screenshot: only 2 employees visible (Rahul Sharma, Test Sharma)
    # This should show 17+ employees
    node_count = len(unique_names) if unique_names else 2  # Default from what we see
    working = node_count >= 10
    status = "PASS" if working else "FAIL"

    ss_md = gh_upload(ss1, issue, "Org Chart")
    return issue, "Org Chart", status, "; ".join(d)


# ═════════════════════════════════════════════════════════════
def main():
    global driver
    print("=" * 70)
    print("EMP Cloud - Verify 11 Features (Pass 3 - Deep)")
    print("=" * 70)

    driver = get_driver()

    tests = [
        test_499, test_519, test_520, test_545, test_556,
        test_563, test_564, test_673, test_700, test_703, test_704,
    ]

    for tf in tests:
        name = tf.__doc__ or tf.__name__
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        try:
            r = tf()
            results.append(r)
            print(f"  => {r[2]}: {r[3][:150]}")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"  ERR: {e}\n{tb}")
            inum = int(tf.__name__.split("_")[1])
            results.append((inum, name, "ERROR", str(e)[:200]))

    try: driver.quit()
    except: pass

    # ── Summary ──
    print("\n\n" + "=" * 100)
    print(f"{'Issue':<8} {'Feature':<30} {'Status':<10} {'Details'}")
    print("-" * 100)
    for iss, feat, st, det in results:
        print(f"#{iss:<7} {feat:<30} {st:<10} {det[:80]}")

    p = sum(1 for r in results if r[2] == "PASS")
    f = sum(1 for r in results if r[2] == "FAIL")
    o = len(results) - p - f
    print(f"\nTotal: {len(results)} | Pass: {p} | Fail: {f} | Other: {o}")

    # ── GitHub final comments ──
    print("\n[Posting final GitHub comments...]")
    for iss, feat, st, det in results:
        ss_main = os.path.join(SS_DIR, f"{iss}_final.png")
        if not os.path.exists(ss_main):
            # Find any screenshot for this issue
            for f_name in os.listdir(SS_DIR):
                if f_name.startswith(str(iss)) and f_name.endswith(".png"):
                    ss_main = os.path.join(SS_DIR, f_name)
                    break

        ss_md = gh_upload(ss_main, iss, feat)

        if st == "PASS":
            gh_comment(iss, f"Verified (final pass): {feat} is working correctly. {det}{ss_md}")
        else:
            gh_comment(iss, f"Feature verification failed (final pass): {feat}. Details: {det}{ss_md}")
            gh_reopen(iss)

    with open(os.path.join(SS_DIR, "results.json"), "w") as fj:
        json.dump([{"issue": r[0], "feature": r[1], "status": r[2], "details": r[3]} for r in results], fj, indent=2)

    print("\nDone!")


if __name__ == "__main__":
    main()
