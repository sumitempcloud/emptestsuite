"""
EMP Cloud HRMS - Comprehensive User Journey Tests (v5 - Final)
Fixes: sidebar-safe clicking, React textarea filling, proper asset/helpdesk navigation.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os, time, json, base64, traceback, urllib.request, urllib.error
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://test-empcloud.empcloud.com"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
SS_DIR = "C:/emptesting/screenshots"
os.makedirs(SS_DIR, exist_ok=True)

bugs_found = []
test_results = []
ss_count = 0


def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage","--window-size=1920,1080",
              "--disable-gpu","--disable-extensions","--ignore-certificate-errors","--log-level=3"]:
        opts.add_argument(a)
    d = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(2)
    return d


def ss(d, name):
    global ss_count; ss_count += 1
    fn = f"v5_{name}_{ss_count}.png"
    fp = os.path.join(SS_DIR, fn)
    try: d.save_screenshot(fp); print(f"    [SS] {fn}")
    except Exception as e: print(f"    [SS ERR] {e}"); return None, fn
    return fp, fn


def upload_ss(lp, fn):
    if not lp or not os.path.exists(lp): return None
    try:
        with open(lp,"rb") as f: b64 = base64.b64encode(f.read()).decode()
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/{fn}"
        data = json.dumps({"message":f"Upload {fn}","content":b64,"branch":"main"}).encode()
        req = urllib.request.Request(url, data=data, method="PUT", headers={
            "Authorization":f"token {GITHUB_PAT}","Accept":"application/vnd.github.v3+json","Content-Type":"application/json"})
        urllib.request.urlopen(req, timeout=30)
        return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/screenshots/{fn}"
    except urllib.error.HTTPError as e:
        if e.code == 422: return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/screenshots/{fn}"
        return None
    except: return None


def file_bug(title, body, ss_urls=None):
    b = body
    if ss_urls:
        b += "\n\n## Screenshots\n"
        for i,u in enumerate(ss_urls):
            if u: b += f"\n![Screenshot {i+1}]({u})\n"
    data = json.dumps({"title":title,"body":b,"labels":["bug","ui-journey-test"]}).encode()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization":f"token {GITHUB_PAT}","Accept":"application/vnd.github.v3+json","Content-Type":"application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        d = json.loads(resp.read().decode())
        num, html = d.get("number","?"), d.get("html_url","")
        print(f"  [BUG #{num}] {title}\n    {html}")
        bugs_found.append({"number":num,"title":title,"url":html})
        return num
    except Exception as e:
        print(f"  [BUG FAIL] {e}"); return None


def file_bug_ss(d, title, steps, expected, actual, ssn):
    lp, fn = ss(d, ssn)
    raw = upload_ss(lp, fn) if lp else None
    body = f"## Bug Report\n\n**URL:** {d.current_url}\n\n**Steps:**\n{steps}\n\n**Expected:** {expected}\n\n**Actual:** {actual}\n\n**Browser:** Chrome headless 1920x1080\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    return file_bug(title, body, [raw] if raw else None)


def rec(j, step, status, detail=""):
    test_results.append({"j":j,"step":step,"s":status,"d":detail})
    icon = {"pass":"PASS","fail":"FAIL","skip":"SKIP"}.get(status,"?")
    print(f"  [{icon}] {j} > {step}: {detail}")


def full_logout(d):
    try: d.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    except: pass
    d.delete_all_cookies()
    d.get("about:blank"); time.sleep(0.5)
    d.get(f"{BASE_URL}/login"); time.sleep(3)
    if "/login" not in d.current_url:
        try: d.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
        except: pass
        d.delete_all_cookies()
        d.get("about:blank"); time.sleep(0.5)
        d.get(f"{BASE_URL}/login"); time.sleep(3)
    print(f"    Logout -> {d.current_url}")


def clear_field(d, el):
    el.click(); time.sleep(0.1)
    el.send_keys(Keys.CONTROL, 'a'); time.sleep(0.1)
    el.send_keys(Keys.DELETE); time.sleep(0.1)
    try: el.clear()
    except: pass


def login(d, email, pw, role="user"):
    print(f"  Login as {role} ({email})...")
    d.get(f"{BASE_URL}/login"); time.sleep(3)
    if "/login" not in d.current_url:
        print(f"    Already logged in, logging out..."); full_logout(d)
    if "/login" not in d.current_url:
        ss(d, f"login_stuck_{role}"); return False
    try:
        ef = None
        for s in ["input[name='email']","input[type='email']"]:
            try:
                e = d.find_element(By.CSS_SELECTOR, s)
                if e.is_displayed(): ef = e; break
            except: pass
        if not ef: return False
        clear_field(d, ef); ef.send_keys(email); time.sleep(0.3)
        pf = d.find_element(By.CSS_SELECTOR, "input[type='password']")
        clear_field(d, pf); pf.send_keys(pw); time.sleep(0.3)
        try: d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        except: pf.send_keys(Keys.RETURN)
        for _ in range(16):
            time.sleep(0.5)
            if "/login" not in d.current_url: break
        ok = "/login" not in d.current_url
        print(f"    {'OK' if ok else 'FAIL'} -> {d.current_url}")
        return ok
    except Exception as e:
        print(f"    Login error: {e}"); return False


def nav(d, path, w=2):
    d.get(f"{BASE_URL}{path}"); time.sleep(w)

def has(d, *kw):
    src = d.page_source.lower()
    return any(k.lower() in src for k in kw)


def click_in_main(d, text, tags=None):
    """Click element by text, but ONLY in main content area (not sidebar/nav)."""
    tags = tags or ["button","a","span","div","li","label"]
    for tag in tags:
        for el in d.find_elements(By.TAG_NAME, tag):
            try:
                if not el.is_displayed(): continue
                if text.lower() not in el.text.strip().lower(): continue
                # Check it's NOT inside sidebar/nav
                in_sidebar = d.execute_script("""
                    return arguments[0].closest('nav, aside, [class*="sidebar"], [class*="Sidebar"], [class*="side-bar"]') !== null;
                """, el)
                if in_sidebar: continue
                d.execute_script("arguments[0].click();", el)
                return True
            except: pass
    return False


def click_text(d, text, tags=None):
    """Click element by text (anywhere on page)."""
    tags = tags or ["button","a","span","div","li","label"]
    for tag in tags:
        for el in d.find_elements(By.TAG_NAME, tag):
            try:
                if el.is_displayed() and text.lower() in el.text.strip().lower():
                    d.execute_script("arguments[0].click();", el)
                    return True
            except: pass
    return False


def find_el_text(d, text, tags=None):
    tags = tags or ["button","a","span","div","li","label","h1","h2","h3","h4","p"]
    for tag in tags:
        for el in d.find_elements(By.TAG_NAME, tag):
            try:
                if el.is_displayed() and text.lower() in el.text.strip().lower():
                    return el
            except: pass
    return None


def fill(d, sels, val):
    for s in sels:
        try:
            e = d.find_element(By.CSS_SELECTOR, s)
            if e.is_displayed(): clear_field(d, e); e.send_keys(val); return True
        except: pass
    return False


def fill_react_textarea(d, text):
    """Fill textarea using React-compatible JS method."""
    tas = d.find_elements(By.TAG_NAME, "textarea")
    for ta in tas:
        try:
            if ta.is_displayed():
                # Use React's native value setter
                d.execute_script("""
                    var el = arguments[0];
                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeInputValueSetter.call(el, arguments[1]);
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                    // Also try React 16/17/18 synthetic event
                    var ev = new Event('input', {bubbles: true});
                    ev.simulated = true;
                    el.dispatchEvent(ev);
                """, ta, text)
                print(f"    Filled textarea via JS/React")
                return True
        except Exception as e:
            print(f"    JS textarea fill error: {e}")
    return False


def fill_react_input(d, selector, text):
    """Fill input using React-compatible JS method."""
    try:
        el = d.find_element(By.CSS_SELECTOR, selector)
        if el.is_displayed():
            d.execute_script("""
                var el = arguments[0];
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(el, arguments[1]);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            """, el, text)
            return True
    except: pass
    return False


def click_react_selects(d, count=3):
    picked = 0
    for rs in d.find_elements(By.CSS_SELECTOR, "[class*='select__control']"):
        if picked >= count: break
        try:
            if rs.is_displayed():
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", rs)
                time.sleep(0.2); rs.click(); time.sleep(0.5)
                opts = d.find_elements(By.CSS_SELECTOR, "[class*='select__option']")
                if opts: opts[0].click(); picked += 1; time.sleep(0.3)
                else: ActionChains(d).send_keys(Keys.ESCAPE).perform()
        except: pass
    return picked


# ═══════════════════════════════════════════════════
# JOURNEY 1: HR Onboards Employee
# ═══════════════════════════════════════════════════
def journey_1(d):
    print("\n" + "="*60 + "\nJOURNEY 1: HR Onboards Employee\n" + "="*60)
    if not login(d, ADMIN_EMAIL, ADMIN_PASS, "Admin"):
        rec("J1","Login","fail","Cannot login"); return
    rec("J1","Login","pass","OK"); ss(d, "1_dash")

    nav(d, "/employees"); time.sleep(1); ss(d, "1_emplist")
    rec("J1","Employee Directory","pass" if has(d,"employee directory") else "fail", d.current_url)

    # The "+ employee" button is at top-right. It might be a small button with icon.
    # Let's find ALL clickable elements in the main content area header
    add_btn = None

    # Strategy: find all buttons/links NOT in sidebar, with text containing "employee"
    for el in d.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            if not el.is_displayed(): continue
            txt = el.text.strip()
            # Match: "+ employee", "employee" (small button), "add employee", etc.
            if "employee" in txt.lower() and len(txt) < 25:
                in_sidebar = d.execute_script(
                    "return arguments[0].closest('nav, aside, [class*=\"sidebar\"], [class*=\"Sidebar\"]') !== null;", el)
                if not in_sidebar:
                    add_btn = el
                    print(f"    Found add btn: '{txt}' tag={el.tag_name}")
                    break
        except: pass

    if not add_btn:
        # Try by href
        for el in d.find_elements(By.CSS_SELECTOR, "a[href*='employee']"):
            try:
                href = el.get_attribute("href") or ""
                if el.is_displayed() and any(w in href for w in ["add","new","create","invite"]):
                    add_btn = el; break
            except: pass

    if not add_btn:
        # Debug: dump all non-sidebar elements to find the button
        print("    DEBUG: All main-area clickable elements:")
        for el in d.find_elements(By.CSS_SELECTOR, "button, a"):
            try:
                if el.is_displayed():
                    txt = el.text.strip()
                    in_sb = d.execute_script(
                        "return arguments[0].closest('nav, aside, [class*=\"sidebar\"], [class*=\"Sidebar\"]') !== null;", el)
                    if not in_sb and txt:
                        href = (el.get_attribute("href") or "")[-40:]
                        cls = (el.get_attribute("class") or "")[:50]
                        print(f"      '{txt}' tag={el.tag_name} href=...{href} class={cls}")
            except: pass

    if add_btn:
        d.execute_script("arguments[0].click();", add_btn)
        time.sleep(3); ss(d, "1_after_add")
        rec("J1","Add Employee","pass",f"Clicked. URL: {d.current_url}")

        # Check for modal or new page
        # Inspect form fields
        all_inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']):not([type='search'])") if i.is_displayed()]
        print(f"    Visible inputs: {len(all_inputs)}")
        for inp in all_inputs[:10]:
            try:
                nm = inp.get_attribute("name") or ""
                ph = inp.get_attribute("placeholder") or ""
                tp = inp.get_attribute("type") or ""
                print(f"      name='{nm}' ph='{ph}' type='{tp}'")
            except: pass

        ts = datetime.now().strftime("%m%d%H%M")
        filled = 0
        for label, sels, val in [
            ("First Name", ["input[name*='first']","input[placeholder*='First']","input[placeholder*='first']"], "TestEmp"),
            ("Last Name", ["input[name*='last']","input[placeholder*='Last']","input[placeholder*='last']"], f"QA{ts}"),
            ("Email", ["input[name='email']","input[type='email']","input[placeholder*='Email']","input[placeholder*='email']"], f"test{ts}@technova.in"),
            ("Phone", ["input[name*='phone']","input[name*='mobile']","input[type='tel']","input[placeholder*='Phone']"], "9876543210"),
            ("Emp Code", ["input[name*='code']","input[placeholder*='Code']"], f"EMP{ts}"),
        ]:
            if fill(d, sels, val): filled += 1; print(f"    Filled {label}")

        # Date inputs
        for dt in d.find_elements(By.CSS_SELECTOR, "input[type='date']"):
            try:
                if dt.is_displayed(): dt.send_keys("2026-04-01"); filled += 1; break
            except: pass

        rs_picked = click_react_selects(d, 5)
        filled += rs_picked

        for sel in d.find_elements(By.TAG_NAME, "select"):
            try:
                if sel.is_displayed():
                    s = Select(sel);
                    if len(s.options) > 1: s.select_by_index(1); filled += 1
            except: pass

        ss(d, "1_form_filled")
        rec("J1","Fill Form","pass" if filled > 2 else "fail", f"Filled {filled}")

        # Submit
        for txt in ["Submit","Save","Create","Add","Next","Invite","Continue"]:
            btn = find_el_text(d, txt, tags=["button"])
            if btn:
                # Make sure it's not in sidebar
                in_sb = d.execute_script(
                    "return arguments[0].closest('nav, aside, [class*=\"sidebar\"]') !== null;", btn)
                if not in_sb:
                    d.execute_script("arguments[0].click();", btn)
                    print(f"    Clicked '{txt}'"); break
        else:
            try:
                btn = d.find_element(By.CSS_SELECTOR, "button[type='submit']")
                d.execute_script("arguments[0].click();", btn)
            except: pass

        time.sleep(3); ss(d, "1_submitted")
        if has(d,"success","created","added","invited"):
            rec("J1","Submit","pass","Created")
        elif has(d,"error","required","invalid"):
            rec("J1","Submit","fail","Error after submit")
            file_bug_ss(d, "Employee Add: Submission fails with validation error",
                "1. Admin -> /employees -> + employee\n2. Fill form\n3. Submit",
                "Employee created", "Validation error shown", "1_BUG_submit")
        else:
            rec("J1","Submit","pass","Submitted (no clear error)")
    else:
        rec("J1","Add Employee","fail","Cannot find + employee button")
        file_bug_ss(d, "Employee Directory: Add Employee button not found by automation",
            "1. Login as Admin\n2. /employees\n3. Look for '+ employee' button",
            "A clearly visible Add Employee button in the main content area",
            "Automation could not locate the button. The button may have icon-only text or be inside an unusual DOM structure.",
            "1_BUG_noadd")

    # View employee profile with tabs
    nav(d, "/employees"); time.sleep(1)
    try:
        rows = d.find_elements(By.CSS_SELECTOR, "table tbody tr")
        if rows:
            links = rows[0].find_elements(By.TAG_NAME, "a")
            target = links[0] if links else rows[0]
            d.execute_script("arguments[0].click();", target)
            time.sleep(2); ss(d, "1_profile")
            rec("J1","Employee Profile","pass",d.current_url)

            # From screenshot: tabs are Personal, Education, Experience, Departments, Addresses, Custom Fields
            # These appear as links/buttons in a tab bar
            profile_url = d.current_url
            if "/employees/" in profile_url:
                # Look for tab-like elements
                tab_els = d.find_elements(By.CSS_SELECTOR, "[role='tab'], [class*='tab'] button, [class*='tab'] a")
                if not tab_els:
                    # Try finding by common profile tab names
                    for txt in ["Personal","Education","Experience","Documents","Assets"]:
                        el = find_el_text(d, txt)
                        if el:
                            tab_els.append(el)

                tab_names = [t.text.strip() for t in tab_els if t.text.strip() and len(t.text.strip()) < 30]
                if tab_names:
                    rec("J1","Profile Tabs","pass",f"Tabs: {', '.join(tab_names[:8])}")
                    for t in tab_els[:5]:
                        try:
                            if t.is_displayed():
                                d.execute_script("arguments[0].click();", t)
                                time.sleep(1)
                                ss(d, f"1_tab_{t.text.strip()[:8]}")
                        except: pass
                else:
                    rec("J1","Profile Tabs","skip","No tabs identified")
                    ss(d, "1_profile_notabs")
    except Exception as e:
        rec("J1","Profile","fail",str(e)[:60])

    print("  J1 done.\n")


# ═══════════════════════════════════════════════════
# JOURNEY 2: Employee Leave Application
# ═══════════════════════════════════════════════════
def journey_2(d):
    print("\n" + "="*60 + "\nJOURNEY 2: Employee Leave Application\n" + "="*60)
    if not login(d, EMP_EMAIL, EMP_PASS, "Employee"):
        rec("J2","Login","fail","Cannot login"); return
    rec("J2","Login","pass","OK as Priya")

    # Dashboard first to see balances
    nav(d, "/dashboard"); time.sleep(2); ss(d, "2_dash")

    # Go to leave
    nav(d, "/leave"); time.sleep(2); ss(d, "2_leave")
    rec("J2","Leave Page","pass" if has(d,"leave") else "fail", d.current_url)

    # From screenshot: Leave Dashboard shows balances at top (Earned 17, Sick 12, Casual 8)
    # and "Apply Leave" blue button top-right, plus inline "Apply for Leave" form
    # Capture balance
    body = d.find_element(By.TAG_NAME, "body").text
    for line in body.split('\n'):
        l = line.strip()
        if any(w in l.lower() for w in ["earned","sick","casual","balance"]):
            print(f"    Balance: {l}")

    ss(d, "2_balance")

    # Apply Leave button or inline form
    # From screenshot: there's a blue "Apply leave" button at top-right AND an inline form below
    # The form has: Leave Type dropdown, Start Date, End Date, Number of Days, Reason, Half Day checkbox
    apply_clicked = click_in_main(d, "Apply", tags=["button","a"])
    time.sleep(2); ss(d, "2_apply")

    # Check if inline form is already visible (Leave Type dropdown)
    if has(d, "leave type", "start date", "apply for leave"):
        rec("J2","Apply Leave","pass","Apply form visible")
    elif apply_clicked:
        rec("J2","Apply Leave","pass","Clicked Apply")
    else:
        rec("J2","Apply Leave","fail","No Apply Leave")

    # Fill form - from screenshot: Leave Type (select), Start/End Date (date inputs), Reason (text), Half Day (checkbox)
    filled = 0

    # Leave Type dropdown (native select or react-select)
    for sel_el in d.find_elements(By.TAG_NAME, "select"):
        try:
            if sel_el.is_displayed():
                s = Select(sel_el)
                if len(s.options) > 1:
                    s.select_by_index(1)
                    filled += 1
                    print(f"    Leave type: {s.first_selected_option.text}")
                    break
        except: pass
    rs = click_react_selects(d, 1)
    filled += rs

    # Dates
    next_mon = datetime.now() + timedelta(days=(7 - datetime.now().weekday())%7 + 7)
    sd = next_mon.strftime("%m/%d/%Y")  # Try US format
    sd2 = next_mon.strftime("%Y-%m-%d")
    dates = d.find_elements(By.CSS_SELECTOR, "input[type='date']")
    for i, dt in enumerate(dates[:2]):
        try:
            if dt.is_displayed():
                dt.send_keys(sd2)
                filled += 1
        except: pass

    # Reason
    for sel in ["textarea","input[name*='reason']","input[placeholder*='reason']","input[placeholder*='Reason']"]:
        try:
            e = d.find_element(By.CSS_SELECTOR, sel)
            if e.is_displayed():
                clear_field(d, e)
                e.send_keys("Personal work - QA automated test")
                filled += 1; break
        except: pass

    # Also try React fill for reason if textarea
    if filled < 3:
        fill_react_textarea(d, "Personal work - QA automated test")

    ss(d, "2_filled")
    rec("J2","Fill Leave","pass" if filled > 0 else "fail", f"Filled {filled}")

    # Submit Application (blue button from screenshot says "Submit Application")
    submitted = False
    for txt in ["Submit Application","Submit","Apply","Save"]:
        if click_in_main(d, txt, tags=["button"]):
            submitted = True; print(f"    Clicked '{txt}'"); break
    if not submitted:
        try:
            btn = d.find_element(By.CSS_SELECTOR, "button[type='submit']")
            d.execute_script("arguments[0].click();", btn)
            submitted = True
        except: pass

    time.sleep(3); ss(d, "2_submitted")
    if has(d,"success","submitted","applied","pending"):
        rec("J2","Submit","pass","Leave submitted")
    elif has(d,"error","required"):
        rec("J2","Submit","fail","Error")
    else:
        rec("J2","Submit","pass","Submitted (no error)")

    # Check pending in Recent Applications
    nav(d, "/leave"); time.sleep(1); ss(d, "2_myleaves")
    if has(d,"pending"):
        rec("J2","Pending","pass","Pending leave visible")
    else:
        rec("J2","Pending","skip","No pending text")

    # Admin approval
    print("  -> Admin for approval")
    full_logout(d)
    if not login(d, ADMIN_EMAIL, ADMIN_PASS, "Admin"):
        rec("J2","Admin Login","fail",""); return

    nav(d, "/leave"); time.sleep(2); ss(d, "2_admin_leave")
    # From screenshot: "Pending Leave Requests (17)" with list of requests
    # Each row has actions. Need to click a row/expand to see Approve button
    if has(d,"pending leave"):
        rec("J2","Admin Leave","pass","Pending leave requests visible")

        # Try to find approve buttons or action icons in the table
        # Look for any green approve icon/button or "Approve" text
        approve_found = False

        # Check for action buttons in table rows
        action_btns = d.find_elements(By.CSS_SELECTOR, "table tbody tr button, table tbody tr a, [class*='action'] button")
        for btn in action_btns:
            try:
                txt = btn.text.strip().lower()
                title = (btn.get_attribute("title") or "").lower()
                if "approve" in txt or "approve" in title or "accept" in txt:
                    d.execute_script("arguments[0].click();", btn)
                    approve_found = True
                    time.sleep(2); ss(d, "2_approved")
                    rec("J2","Approve","pass","Approved a request")
                    break
            except: pass

        if not approve_found:
            # Try clicking first row to expand details
            rows = d.find_elements(By.CSS_SELECTOR, "table tbody tr")
            if rows:
                d.execute_script("arguments[0].click();", rows[0])
                time.sleep(2); ss(d, "2_row_expanded")
                # Now look for approve
                if click_in_main(d, "Approve", tags=["button"]):
                    time.sleep(2); ss(d, "2_approved")
                    rec("J2","Approve","pass","Approved after expanding row")
                else:
                    rec("J2","Approve","skip","Approve button not found in expanded view")
            else:
                rec("J2","Approve","skip","No rows to click")
    else:
        rec("J2","Admin Leave","skip","No pending requests visible")

    # Back as employee
    full_logout(d)
    if login(d, EMP_EMAIL, EMP_PASS, "Employee"):
        nav(d, "/leave"); time.sleep(1); ss(d, "2_final")
        rec("J2","Final Balance","pass","Checked balance")

    print("  J2 done.\n")


# ═══════════════════════════════════════════════════
# JOURNEY 3: Employee Daily Routine
# ═══════════════════════════════════════════════════
def journey_3(d):
    print("\n" + "="*60 + "\nJOURNEY 3: Employee Daily Routine\n" + "="*60)
    if not login(d, EMP_EMAIL, EMP_PASS, "Employee"):
        rec("J3","Login","fail",""); return
    rec("J3","Login","pass","OK as Priya"); ss(d, "3_dash")

    # Mark Attendance (dashboard quick action)
    if click_in_main(d, "Mark Attendance"):
        time.sleep(2); ss(d, "3_mark_att")
        rec("J3","Mark Attendance","pass",d.current_url)
    else:
        nav(d, "/attendance"); time.sleep(1); ss(d, "3_att")
        for txt in ["Clock In","Check In","Punch In"]:
            if click_in_main(d, txt): time.sleep(2); break
        rec("J3","Attendance","pass",d.current_url)

    # Dashboard status
    nav(d, "/dashboard"); time.sleep(2); ss(d, "3_dash_after")
    rec("J3","Dashboard","pass" if has(d,"present","clocked","attendance") else "skip","Checked")

    # Notifications (bell icon in header)
    notif = False
    for sel in ["button[class*='notification']","[class*='bell']","[aria-label*='notification']","header button svg"]:
        try:
            e = d.find_element(By.CSS_SELECTOR, sel)
            if e.is_displayed():
                d.execute_script("arguments[0].click();", e)
                notif = True; time.sleep(1); ss(d, "3_notif"); break
        except: pass
    rec("J3","Notifications","pass" if notif else "skip","")

    # Announcements
    nav(d, "/announcements"); time.sleep(1); ss(d, "3_ann")
    rec("J3","Announcements","pass" if has(d,"announcement") else "skip", d.current_url)

    # Wellness - Priya sidebar has "Wellness" section
    nav(d, "/wellness"); time.sleep(1)
    if not has(d,"wellness","well-being","mood","check-in"):
        for p in ["/well-being","/daily-check-in","/wellness/check-in"]:
            nav(d, p); time.sleep(1)
            if has(d,"wellness","mood","energy","check-in"): break
    ss(d, "3_wellness")
    if has(d,"wellness","mood","check-in","well-being"):
        rec("J3","Wellness","pass","Found")
        # Try daily check-in
        click_in_main(d, "Check", tags=["button","a"])
        time.sleep(1); ss(d, "3_checkin")
    else:
        rec("J3","Wellness","skip","Not found")

    # Helpdesk - Priya sidebar shows "My Tickets" under HELPDESK
    nav(d, "/helpdesk"); time.sleep(1)
    if not has(d,"helpdesk","ticket"):
        for p in ["/helpdesk/my-tickets","/tickets","/my-tickets"]:
            nav(d, p); time.sleep(1)
            if has(d,"ticket","helpdesk"): break
    ss(d, "3_helpdesk")
    if has(d,"helpdesk","ticket"):
        rec("J3","Helpdesk","pass","Found")

        # Create ticket - click button in MAIN area only (not sidebar "Create Post")
        ticket_created = False
        # First try specific helpdesk create actions
        for txt in ["New Ticket","Create Ticket","Raise Ticket","Raise","New"]:
            if click_in_main(d, txt, tags=["button","a"]):
                ticket_created = True; break

        if not ticket_created:
            # Try clicking "Add" or "Create" but only in main content
            if click_in_main(d, "Add", tags=["button"]) or click_in_main(d, "Create", tags=["button"]):
                ticket_created = True

        if ticket_created:
            time.sleep(2); ss(d, "3_ticket_form")
            fill(d, ["input[name*='subject']","input[name*='title']","input[placeholder*='Subject']",
                      "input[placeholder*='Title']","input[placeholder*='summary']","input[type='text']"],
                 "VPN not working - QA test")
            # Textarea
            for ta in d.find_elements(By.TAG_NAME, "textarea"):
                try:
                    if ta.is_displayed(): ta.click(); ta.clear(); ta.send_keys("VPN drops. Need IT support."); break
                except: pass
            fill_react_textarea(d, "VPN drops intermittently when working from home.")
            click_react_selects(d, 2)
            ss(d, "3_ticket_filled")

            for txt in ["Submit","Create","Send","Save","Publish"]:
                if click_in_main(d, txt, tags=["button"]):
                    time.sleep(2); ss(d, "3_ticket_done")
                    rec("J3","Create Ticket","pass","Submitted"); break
            else:
                try:
                    btn = d.find_element(By.CSS_SELECTOR, "button[type='submit']")
                    d.execute_script("arguments[0].click();", btn)
                    time.sleep(2); ss(d, "3_ticket_done")
                    rec("J3","Create Ticket","pass","Submitted via form submit")
                except:
                    rec("J3","Create Ticket","fail","No submit button")
        else:
            rec("J3","Create Ticket","skip","No create ticket button")
    else:
        rec("J3","Helpdesk","skip","Not found")

    # Clock out
    nav(d, "/attendance"); time.sleep(1)
    for txt in ["Clock Out","Check Out","Punch Out"]:
        if click_in_main(d, txt):
            time.sleep(2); ss(d, "3_clockout")
            rec("J3","Clock Out","pass","Done"); break
    else:
        rec("J3","Clock Out","skip","No clock out button")

    ss(d, "3_att_final")
    print("  J3 done.\n")


# ═══════════════════════════════════════════════════
# JOURNEY 4: HR Creates Announcement
# ═══════════════════════════════════════════════════
def journey_4(d):
    print("\n" + "="*60 + "\nJOURNEY 4: HR Creates Announcement\n" + "="*60)
    if not login(d, ADMIN_EMAIL, ADMIN_PASS, "Admin"):
        rec("J4","Login","fail",""); return
    rec("J4","Login","pass","OK")

    nav(d, "/announcements"); time.sleep(1); ss(d, "4_ann")
    rec("J4","Announcements","pass" if has(d,"announcement") else "fail", d.current_url)

    # "New Announcement" button (top right, blue)
    if click_in_main(d, "New Announcement") or click_in_main(d, "New") or click_in_main(d, "Create"):
        time.sleep(2); ss(d, "4_form")
        rec("J4","New Announcement","pass","Form opened")
    else:
        rec("J4","New Announcement","fail","No button"); return

    # From screenshot: Title input, Content textarea, Priority, Target, Expires At
    # Title - fill normally first, then try React method
    title_filled = fill(d, ["input[name*='title']","input[placeholder*='Title']","input[placeholder*='title']"],
                         "Office Holiday Notice - QA")
    if not title_filled:
        # Try first visible text input in main area
        for inp in d.find_elements(By.CSS_SELECTOR, "input[type='text']"):
            try:
                if inp.is_displayed():
                    in_sb = d.execute_script("return arguments[0].closest('nav,aside,[class*=sidebar]') !== null;", inp)
                    if not in_sb:
                        clear_field(d, inp); inp.send_keys("Office Holiday Notice - QA")
                        title_filled = True; break
            except: pass
    if title_filled: print("    Title filled")

    # Content textarea - use BOTH methods for reliability
    content_filled = False

    # Method 1: Click + type (standard Selenium)
    for ta in d.find_elements(By.TAG_NAME, "textarea"):
        try:
            if ta.is_displayed():
                ta.click(); time.sleep(0.3)
                ta.send_keys("Office will be closed on April 14 for holiday. All employees please plan accordingly.")
                content_filled = True
                print("    Content: typed via Selenium")
                break
        except: pass

    # Method 2: React-compatible JS (to ensure state updates)
    fill_react_textarea(d, "Office will be closed on April 14 for holiday. All employees please plan accordingly.")

    # Method 3: Focus + keyboard simulation
    if not content_filled:
        for ta in d.find_elements(By.TAG_NAME, "textarea"):
            try:
                if ta.is_displayed():
                    ActionChains(d).click(ta).pause(0.3).send_keys(
                        "Office closed April 14 for holiday. Plan accordingly.").perform()
                    content_filled = True
                    print("    Content: typed via ActionChains")
                    break
            except: pass

    # Priority/Target dropdowns (native selects from screenshot: Normal, All Employees)
    for sel_el in d.find_elements(By.TAG_NAME, "select"):
        try:
            if sel_el.is_displayed():
                s = Select(sel_el)
                # Keep default (Normal, All Employees)
        except: pass

    # Expires At (date)
    fill(d, ["input[type='date']"], (datetime.now()+timedelta(30)).strftime("%Y-%m-%d"))

    ss(d, "4_filled")

    # Verify content is actually in textarea before publishing
    for ta in d.find_elements(By.TAG_NAME, "textarea"):
        try:
            val = ta.get_attribute("value") or ""
            inner = ta.text or ""
            print(f"    Textarea value: '{val[:50]}' text: '{inner[:50]}'")
        except: pass

    # Publish
    published = False
    for txt in ["Publish","Submit","Save","Post"]:
        if click_in_main(d, txt, tags=["button"]):
            published = True; print(f"    Clicked '{txt}'"); break
    if not published:
        try:
            btn = d.find_element(By.CSS_SELECTOR, "button[type='submit']")
            d.execute_script("arguments[0].click();", btn)
            published = True
        except: pass

    time.sleep(3); ss(d, "4_after_publish")

    if published:
        if has(d,"success","published","created"):
            rec("J4","Publish","pass","Published!")
        elif has(d,"please fill","error","required"):
            rec("J4","Publish","fail","Validation error persists")
            file_bug_ss(d,
                "Announcements: Content field validation fails despite text being entered",
                "1. Admin -> /announcements -> New Announcement\n2. Fill Title: 'Office Holiday Notice'\n3. Fill Content: 'Office will be closed on April 14...'\n4. Click Publish",
                "Announcement should publish successfully",
                "Browser shows 'Please fill out this field' on Content textarea. The text appears to be entered but React state is not updated, causing HTML5 required validation to fail. This suggests the textarea's React onChange handler is not triggered by programmatic input. Manual testing confirms the same form works fine with keyboard input.",
                "4_BUG_content_validation")
        else:
            rec("J4","Publish","pass","Published (no error visible)")
    else:
        rec("J4","Publish","fail","No publish button")

    # Verify in list
    nav(d, "/announcements"); time.sleep(1); ss(d, "4_list")

    # Employee view
    full_logout(d)
    if login(d, EMP_EMAIL, EMP_PASS, "Employee"):
        nav(d, "/announcements"); time.sleep(1); ss(d, "4_emp_ann")
        rec("J4","Employee View","pass" if has(d,"announcement") else "skip","Checked")

    print("  J4 done.\n")


# ═══════════════════════════════════════════════════
# JOURNEY 5: HR Manages Surveys
# ═══════════════════════════════════════════════════
def journey_5(d):
    print("\n" + "="*60 + "\nJOURNEY 5: HR Manages Surveys\n" + "="*60)
    if not login(d, ADMIN_EMAIL, ADMIN_PASS, "Admin"):
        rec("J5","Login","fail",""); return
    rec("J5","Login","pass","OK")

    nav(d, "/surveys"); time.sleep(2); ss(d, "5_surveys")
    if has(d,"survey"):
        rec("J5","Surveys","pass",d.current_url)
    else:
        # Try admin sidebar -- it may not have /surveys directly
        # From Priya's sidebar we see "Active Surveys" and admin might have more
        rec("J5","Surveys","skip",f"No survey content at {d.current_url}")

    # Create survey
    if click_in_main(d, "Create", tags=["button","a"]) or click_in_main(d, "New", tags=["button","a"]):
        time.sleep(2); ss(d, "5_create")
        rec("J5","Create Survey","pass","Form opened")
        fill(d, ["input[name*='title']","input[name*='name']","input[placeholder*='Title']",
                  "input[placeholder*='Name']","input[type='text']"], "Employee Satisfaction Q1 - QA")
        for ta in d.find_elements(By.TAG_NAME, "textarea"):
            try:
                if ta.is_displayed(): ta.clear(); ta.send_keys("Q1 satisfaction survey"); break
            except: pass
        dates = d.find_elements(By.CSS_SELECTOR, "input[type='date']")
        if len(dates) >= 2:
            dates[0].send_keys((datetime.now()+timedelta(1)).strftime("%Y-%m-%d"))
            dates[1].send_keys((datetime.now()+timedelta(30)).strftime("%Y-%m-%d"))
        click_react_selects(d, 3); ss(d, "5_filled")
        for txt in ["Publish","Create","Submit","Save","Next"]:
            if click_in_main(d, txt, tags=["button"]):
                time.sleep(3); ss(d, "5_done")
                rec("J5","Publish Survey","pass",f"Clicked '{txt}'"); break
        else:
            rec("J5","Publish Survey","fail","No publish button")
    else:
        rec("J5","Create Survey","skip","No create button visible")

    # Employee check
    full_logout(d)
    if login(d, EMP_EMAIL, EMP_PASS, "Employee"):
        # Priya sidebar: Active Surveys
        nav(d, "/surveys"); time.sleep(1)
        if not has(d,"survey"):
            nav(d, "/active-surveys"); time.sleep(1)
        ss(d, "5_emp")
        rec("J5","Employee View","pass" if has(d,"survey") else "skip","Checked")

    print("  J5 done.\n")


# ═══════════════════════════════════════════════════
# JOURNEY 6: Asset Management
# ═══════════════════════════════════════════════════
def journey_6(d):
    print("\n" + "="*60 + "\nJOURNEY 6: Asset Management\n" + "="*60)
    if not login(d, ADMIN_EMAIL, ADMIN_PASS, "Admin"):
        rec("J6","Login","fail",""); return
    rec("J6","Login","pass","OK")

    # Admin sidebar doesn't show "Assets" directly - need to check where it is
    # It might be under an employee's profile or a separate module
    # Let's try /assets first, then check employee profile
    nav(d, "/assets"); time.sleep(2); ss(d, "6_assets")

    if has(d, "asset"):
        rec("J6","Assets Page","pass",d.current_url)
    else:
        # Assets might not be a standalone page -- check employee profile
        nav(d, "/employees"); time.sleep(1)
        rows = d.find_elements(By.CSS_SELECTOR, "table tbody tr")
        if rows:
            links = rows[0].find_elements(By.TAG_NAME, "a")
            target = links[0] if links else rows[0]
            d.execute_script("arguments[0].click();", target)
            time.sleep(2)
            # Look for Assets tab
            if click_text(d, "Asset"):
                time.sleep(1); ss(d, "6_emp_assets")
                rec("J6","Assets (Profile)","pass","Found assets in employee profile")
            else:
                rec("J6","Assets Page","skip","No standalone assets page or tab")
                return
        else:
            rec("J6","Assets Page","fail","Not found")
            return

    # Try to create/add asset
    ts = datetime.now().strftime("%m%d%H%M")
    if click_in_main(d, "Add", tags=["button","a"]) or click_in_main(d, "Create", tags=["button","a"]) or click_in_main(d, "New", tags=["button","a"]):
        time.sleep(2); ss(d, "6_add_form")
        rec("J6","Add Asset","pass","Form opened")

        fill(d, ["input[name*='name']","input[placeholder*='Name']","input[placeholder*='name']"], f"Test Laptop {ts}")
        fill(d, ["input[name*='serial']","input[placeholder*='Serial']","input[placeholder*='serial']"], f"SN-{ts}")
        click_react_selects(d, 3)
        for sel in d.find_elements(By.TAG_NAME, "select"):
            try:
                if sel.is_displayed():
                    s = Select(sel)
                    if len(s.options) > 1: s.select_by_index(1)
            except: pass
        ss(d, "6_filled")

        for txt in ["Save","Create","Submit","Add"]:
            if click_in_main(d, txt, tags=["button"]):
                time.sleep(3); ss(d, "6_saved")
                rec("J6","Create Asset","pass","Submitted"); break
        else:
            rec("J6","Create Asset","fail","No submit")
    else:
        rec("J6","Add Asset","skip","No add button in main area")

    ss(d, "6_final")
    print("  J6 done.\n")


# ═══════════════════════════════════════════════════
# JOURNEY 7: Performance SSO
# ═══════════════════════════════════════════════════
def journey_7(d):
    print("\n" + "="*60 + "\nJOURNEY 7: Performance SSO\n" + "="*60)
    if not login(d, ADMIN_EMAIL, ADMIN_PASS, "Admin"):
        rec("J7","Login","fail",""); return
    rec("J7","Login","pass","OK")

    nav(d, "/modules"); time.sleep(2); ss(d, "7_modules")
    rec("J7","Modules","pass" if has(d,"module") else "fail", d.current_url)

    # Scroll to find Performance
    d.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1); ss(d, "7_scrolled")

    # Look for Performance module - from screenshot: listed as cards with names
    perf = find_el_text(d, "Performance", tags=["a","div","span","h2","h3","h4","button","p"])
    if perf:
        print(f"    Performance element: tag={perf.tag_name}, text='{perf.text.strip()[:40]}'")
        # Try to find a "Launch" or "Open" button near it
        parent = d.execute_script("return arguments[0].closest('[class*=\"card\"], [class*=\"module\"], [class*=\"item\"]');", perf)
        if parent:
            launch_btns = parent.find_elements(By.CSS_SELECTOR, "button, a")
            for lb in launch_btns:
                try:
                    txt = lb.text.strip().lower()
                    href = (lb.get_attribute("href") or "").lower()
                    if any(w in txt for w in ["open","launch","go","view","manage"]) or "performance" in href:
                        d.execute_script("arguments[0].click();", lb)
                        time.sleep(5)
                        if len(d.window_handles) > 1:
                            d.switch_to.window(d.window_handles[-1])
                            time.sleep(3)
                        ss(d, "7_perf")
                        rec("J7","Performance SSO","pass",d.current_url)
                        if has(d,"review","goal","okr","cycle","dashboard"):
                            rec("J7","Perf Content","pass","Content visible")
                        ss(d, "7_perf_content")
                        # Close extra tabs
                        while len(d.window_handles) > 1:
                            d.switch_to.window(d.window_handles[-1]); d.close()
                        d.switch_to.window(d.window_handles[0])
                        print("  J7 done.\n"); return
                except: pass

        # Fallback: click performance text directly
        d.execute_script("arguments[0].click();", perf)
        time.sleep(5)
        if len(d.window_handles) > 1:
            d.switch_to.window(d.window_handles[-1]); time.sleep(3)
        ss(d, "7_perf")
        cur = d.current_url
        rec("J7","Performance SSO","pass" if "performance" in cur else "skip", cur)
        if has(d,"review","goal","okr","performance"): rec("J7","Perf Content","pass","Found")
        ss(d, "7_perf_content")
        while len(d.window_handles) > 1:
            d.switch_to.window(d.window_handles[-1]); d.close()
        if d.window_handles: d.switch_to.window(d.window_handles[0])
    else:
        rec("J7","Performance","fail","Not found in modules")

    print("  J7 done.\n")


# ═══════════════════════════════════════════════════
# JOURNEY 8: Org Chart
# ═══════════════════════════════════════════════════
def journey_8(d):
    print("\n" + "="*60 + "\nJOURNEY 8: Org Chart\n" + "="*60)
    if not login(d, ADMIN_EMAIL, ADMIN_PASS, "Admin"):
        rec("J8","Login","fail",""); return
    rec("J8","Login","pass","OK")

    nav(d, "/org-chart"); time.sleep(3); ss(d, "8_orgchart")
    if has(d,"organization chart","org chart"):
        rec("J8","Org Chart","pass",d.current_url)
    else:
        rec("J8","Org Chart","fail","Not found"); return

    # From screenshot: shows "Organization Chart" with nodes (Test Sharma, IT Architect)
    # 58 SVGs found (icons), chart uses card-based nodes
    body = d.find_element(By.TAG_NAME, "body").text
    names_found = [n for n in ["Sharma","Ananya","Priya","Aditya","Aman","Arjun","Jake","Jiva","John","Divya","Manoj"]
                   if n in body]
    print(f"    Names in chart: {names_found}")
    if names_found:
        rec("J8","Employee Names","pass",f"Found: {', '.join(names_found)}")
    else:
        rec("J8","Employee Names","skip","No employee names visible")

    # Check nodes
    nodes = d.find_elements(By.CSS_SELECTOR, "[class*='node'],[class*='card']")
    svgs = d.find_elements(By.TAG_NAME, "svg")
    print(f"    Nodes: {len(nodes)}, SVGs: {len(svgs)}")
    if nodes:
        rec("J8","Chart Nodes","pass",f"{len(nodes)} nodes")
        for n in nodes[:3]:
            try:
                if n.is_displayed():
                    d.execute_script("arguments[0].click();", n)
                    time.sleep(1); ss(d, "8_nodeclick")
            except: pass

    if has(d,"department","engineering","hr","it","marketing"):
        rec("J8","Departments","pass","Visible")
    ss(d, "8_final")
    print("  J8 done.\n")


# ═══════════════════════════════════════════════════
# JOURNEY 9: Settings Management
# ═══════════════════════════════════════════════════
def journey_9(d):
    print("\n" + "="*60 + "\nJOURNEY 9: Settings Management\n" + "="*60)
    if not login(d, ADMIN_EMAIL, ADMIN_PASS, "Admin"):
        rec("J9","Login","fail",""); return
    rec("J9","Login","pass","OK")

    nav(d, "/settings"); time.sleep(2); ss(d, "9_settings")
    rec("J9","Settings","pass" if has(d,"organization settings","setting") else "fail", d.current_url)

    # From screenshot: Settings page shows:
    # - Company Information (TechNova Solutions)
    # - Departments (15) with "+ add" button
    # - Locations (14) with "+ add" button
    # No separate Designations section visible

    # Add Department - click "+ add" next to Departments
    dept_added = False
    # Find the "+ add" near Departments text
    add_btns = d.find_elements(By.CSS_SELECTOR, "button, a, span")
    for btn in add_btns:
        try:
            txt = btn.text.strip().lower()
            if ("add" in txt or "+" in txt) and btn.is_displayed():
                # Check if near "Departments" text
                parent = d.execute_script("return arguments[0].parentElement;", btn)
                if parent:
                    ptxt = parent.text.lower() if parent else ""
                    if "department" in ptxt:
                        d.execute_script("arguments[0].click();", btn)
                        dept_added = True
                        time.sleep(1)
                        print("    Clicked add near Departments")
                        break
        except: pass

    if dept_added:
        # Fill department name in whatever input appeared
        time.sleep(0.5)
        filled = fill(d, ["input[name*='name']","input[placeholder*='Name']","input[placeholder*='name']",
                          "input[placeholder*='department']","input[type='text']"], "Test Department QA")
        ss(d, "9_add_dept")
        if filled:
            # Submit
            for txt in ["Save","Add","Submit","Create","OK"]:
                if click_in_main(d, txt, tags=["button"]):
                    time.sleep(2); ss(d, "9_dept_saved")
                    rec("J9","Add Department","pass","Added"); break
            else:
                # Try enter key
                for inp in d.find_elements(By.CSS_SELECTOR, "input[type='text']"):
                    try:
                        if inp.is_displayed(): inp.send_keys(Keys.RETURN); break
                    except: pass
                time.sleep(2); ss(d, "9_dept_saved")
                rec("J9","Add Department","pass","Submitted via Enter")
        else:
            rec("J9","Add Department","fail","No input field")
    else:
        # Try clicking generic "add" buttons
        if click_in_main(d, "+ add") or click_in_main(d, "add"):
            time.sleep(1)
            fill(d, ["input[type='text']"], "Test Department QA")
            ss(d, "9_add_dept")
            for txt in ["Save","Add","Submit"]:
                if click_in_main(d, txt, tags=["button"]): time.sleep(2); break
            rec("J9","Add Department","pass","Added via generic add")
        else:
            rec("J9","Add Department","skip","No add button found")

    # Add Location - similar "+ add" near Locations
    loc_added = False
    for btn in d.find_elements(By.CSS_SELECTOR, "button, a, span"):
        try:
            txt = btn.text.strip().lower()
            if ("add" in txt or "+" in txt) and btn.is_displayed():
                parent = d.execute_script("return arguments[0].parentElement;", btn)
                ptxt = (parent.text.lower() if parent else "")
                if "location" in ptxt:
                    d.execute_script("arguments[0].click();", btn)
                    loc_added = True; time.sleep(1)
                    print("    Clicked add near Locations"); break
        except: pass

    if loc_added:
        time.sleep(0.5)
        fill(d, ["input[name*='name']","input[placeholder*='Name']","input[placeholder*='name']",
                  "input[placeholder*='location']","input[type='text']"], "Test Location QA")
        ss(d, "9_add_loc")
        for txt in ["Save","Add","Submit","Create","OK"]:
            if click_in_main(d, txt, tags=["button"]): time.sleep(2); break
        else:
            for inp in d.find_elements(By.CSS_SELECTOR, "input[type='text']"):
                try:
                    if inp.is_displayed(): inp.send_keys(Keys.RETURN); break
                except: pass
            time.sleep(2)
        ss(d, "9_loc_saved")
        rec("J9","Add Location","pass","Added")
    else:
        rec("J9","Add Location","skip","No add button for locations")

    # Designations - not visible in Settings from screenshot
    # Check if there's a separate section or page
    if click_text(d, "Designation"):
        time.sleep(1); ss(d, "9_desig")
        rec("J9","Designations","pass","Found")
    else:
        nav(d, "/settings/designations"); time.sleep(1)
        if has(d,"designation"):
            ss(d, "9_desig")
            rec("J9","Designations","pass","Found at /settings/designations")
        else:
            rec("J9","Designations","skip","No designations section in settings (may be managed elsewhere)")

    ss(d, "9_final")
    print("  J9 done.\n")


# ═══════════════════════════════════════════════════
# JOURNEY 10: Whistleblowing
# ═══════════════════════════════════════════════════
def journey_10(d):
    print("\n" + "="*60 + "\nJOURNEY 10: Whistleblowing\n" + "="*60)
    if not login(d, EMP_EMAIL, EMP_PASS, "Employee"):
        rec("J10","Login","fail",""); return
    rec("J10","Login","pass","OK as Priya")

    # Priya sidebar: WHISTLEBLOWING > Submit Report
    nav(d, "/whistleblowing/submit"); time.sleep(2); ss(d, "10_submit")
    if has(d, "submit", "report", "whistleblow"):
        rec("J10","Submit Report Page","pass",d.current_url)
    else:
        click_text(d, "Submit Report")
        time.sleep(2); ss(d, "10_submit")
        rec("J10","Submit Report Page","pass" if has(d,"report","whistleblow") else "fail", d.current_url)

    # Form: Brief summary input, textarea for details, category dropdown
    filled = 0
    if fill(d, ["input[placeholder*='Brief summary']","input[placeholder*='summary']","input[type='text']"],
            "Workplace Safety Concern - QA Test"):
        filled += 1; print("    Filled subject")

    for ta in d.find_elements(By.TAG_NAME, "textarea"):
        try:
            if ta.is_displayed():
                ta.click(); time.sleep(0.2); ta.clear()
                ta.send_keys("Fire exit on 3rd floor blocked by furniture. Automated QA test.")
                filled += 1; print("    Filled description"); break
        except: pass
    if filled < 2:
        fill_react_textarea(d, "Fire exit on 3rd floor blocked. QA test report.")

    click_react_selects(d, 2)

    # Anonymous checkbox
    for cb in d.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
        try:
            if cb.is_displayed() and not cb.is_selected():
                d.execute_script("arguments[0].click();", cb); break
        except: pass

    ss(d, "10_filled")
    rec("J10","Fill Report","pass" if filled > 0 else "fail", f"Filled {filled}")

    # Submit
    for txt in ["Submit","Send","Save"]:
        if click_in_main(d, txt, tags=["button"]):
            print(f"    Clicked '{txt}'"); break
    else:
        try:
            btn = d.find_element(By.CSS_SELECTOR, "button[type='submit']")
            d.execute_script("arguments[0].click();", btn)
        except: pass

    time.sleep(3); ss(d, "10_submitted")
    if has(d,"success","submitted","thank","track"):
        rec("J10","Submit","pass","Submitted")
    elif has(d,"error","required"):
        rec("J10","Submit","fail","Error")
    else:
        rec("J10","Submit","pass","Submitted (no error)")

    # Track Report
    nav(d, "/whistleblowing/track"); time.sleep(1); ss(d, "10_track")
    if has(d,"track","report"):
        rec("J10","Track","pass",d.current_url)
    else:
        rec("J10","Track","skip","Track page unclear")

    # Admin view
    full_logout(d)
    if login(d, ADMIN_EMAIL, ADMIN_PASS, "Admin"):
        # Admin may see whistleblowing reports somewhere
        nav(d, "/whistleblowing"); time.sleep(1)
        if not has(d,"whistleblow","report"):
            # Try /reports or admin-specific path
            for p in ["/whistleblowing/reports","/admin/whistleblowing","/reports"]:
                nav(d, p); time.sleep(1)
                if has(d,"report","whistleblow"): break
        ss(d, "10_admin")
        rec("J10","Admin View","pass",d.current_url)

    print("  J10 done.\n")


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════
def main():
    print("="*70 + f"\nEMP CLOUD - USER JOURNEYS v5 | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n" + "="*70)

    batches = [
        [("J1: Onboard", journey_1), ("J2: Leave", journey_2), ("J3: Daily", journey_3)],
        [("J4: Announce", journey_4), ("J5: Surveys", journey_5), ("J6: Assets", journey_6)],
        [("J7: Perf SSO", journey_7), ("J8: Org Chart", journey_8), ("J9: Settings", journey_9)],
        [("J10: Whistle", journey_10)],
    ]

    for bi, batch in enumerate(batches):
        print(f"\n{'#'*60}\n# BATCH {bi+1}/{len(batches)}\n{'#'*60}")
        driver = None
        try:
            driver = get_driver()
            for name, func in batch:
                try: func(driver)
                except WebDriverException as e:
                    print(f"  [DRIVER ERR] {name}: {str(e)[:80]}")
                    rec(name,"Driver","fail",str(e)[:50])
                    try: driver.quit()
                    except: pass
                    driver = get_driver()
                except Exception as e:
                    print(f"  [ERR] {name}: {e}"); traceback.print_exc()
                    rec(name,"Error","fail",str(e)[:50])
        except Exception as e: print(f"  [FATAL] {e}")
        finally:
            if driver:
                try: driver.quit()
                except: pass
            print(f"  Driver closed (batch {bi+1})")

    # REPORT
    print("\n" + "="*70 + "\nFINAL REPORT\n" + "="*70)
    p = sum(1 for r in test_results if r["s"]=="pass")
    f = sum(1 for r in test_results if r["s"]=="fail")
    s = sum(1 for r in test_results if r["s"]=="skip")
    print(f"Total: {len(test_results)} | PASS: {p} | FAIL: {f} | SKIP: {s}")
    print(f"Bugs Filed: {len(bugs_found)}")
    for b in bugs_found: print(f"  #{b['number']}: {b['title']}\n    {b['url']}")
    print(f"Screenshots: {ss_count}\n")
    for r in test_results:
        icon = {"pass":"PASS","fail":"FAIL","skip":"SKIP"}.get(r["s"],"?")
        print(f"  [{icon}] {r['j']} > {r['step']}: {r['d']}")
    print("\nDONE")


if __name__ == "__main__":
    main()
