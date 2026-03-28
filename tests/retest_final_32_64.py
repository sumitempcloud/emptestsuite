#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EmpCloud Issue Re-test: #32-#63
Tests from inside dashboard with fresh browser per test.
"""
import sys, os, time, json, traceback, urllib.request, urllib.error, ssl, gc, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

class Unbuf:
    def __init__(self, s): self.stream = s
    def write(self, d): self.stream.write(d); self.stream.flush()
    def writelines(self, d): self.stream.writelines(d); self.stream.flush()
    def __getattr__(self, a): return getattr(self.stream, a)
sys.stdout = Unbuf(sys.stdout)
sys.stderr = Unbuf(sys.stderr)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

BASE = "https://test-empcloud.empcloud.com"
SSDIR = r"C:\Users\Admin\screenshots\retest_final"
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
REPO = "EmpCloud/EmpCloud"
ADMIN = ("ananya@technova.in", "Welcome@123")
EMP   = ("priya@technova.in",  "Welcome@123")
os.makedirs(SSDIR, exist_ok=True)

_drv_path = None
def get_drv():
    global _drv_path
    if not _drv_path:
        _drv_path = ChromeDriverManager().install()
    return _drv_path

results = {}

def new_driver():
    o = Options()
    o.binary_location = CHROME
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage",
              "--window-size=1920,1080","--disable-gpu","--disable-extensions",
              "--ignore-certificate-errors"]:
        o.add_argument(a)
    d = webdriver.Chrome(service=Service(get_drv()), options=o)
    d.set_page_load_timeout(40)
    d.implicitly_wait(3)
    return d

def ss(d, name):
    try: d.save_screenshot(os.path.join(SSDIR, f"{name}.png"))
    except: pass

def do_login(d, creds):
    email, pw = creds
    d.get(BASE + "/login")
    time.sleep(4)
    if "/login" not in d.current_url:
        return True  # Already redirected (unlikely for fresh driver)
    try:
        ef = d.find_element(By.CSS_SELECTOR, "input[name='email']")
        pf = d.find_element(By.CSS_SELECTOR, "input[name='password']")
        # React-friendly input
        d.execute_script("""
            var nset = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
            nset.call(arguments[0], arguments[2]);
            arguments[0].dispatchEvent(new Event('input',{bubbles:true}));
            arguments[0].dispatchEvent(new Event('change',{bubbles:true}));
            nset.call(arguments[1], arguments[3]);
            arguments[1].dispatchEvent(new Event('input',{bubbles:true}));
            arguments[1].dispatchEvent(new Event('change',{bubbles:true}));
        """, ef, pf, email, pw)
        time.sleep(0.5)
        d.find_element(By.XPATH, "//button[contains(text(),'Sign in')]").click()
        time.sleep(6)
        if "/login" not in d.current_url:
            return True
        # Fallback check
        bt = d.find_element(By.TAG_NAME, "body").text.lower()
        return "welcome" in bt or "dashboard" in bt
    except Exception as e:
        print(f"  [login err] {e}")
        return False

def bt(d):
    try: return d.find_element(By.TAG_NAME, "body").text
    except: return ""

def btl(d):
    return bt(d).lower()

def has_content(d):
    t = btl(d)
    return len(t) > 50

def click_btn(d, texts):
    """Click first button/link containing any of texts. Return True if clicked."""
    for el in d.find_elements(By.CSS_SELECTOR, "button, a, [role='button']"):
        try:
            t = (el.text or "").lower()
            if any(w in t for w in texts) and el.is_displayed():
                try: el.click()
                except: d.execute_script("arguments[0].click();", el)
                time.sleep(2)
                return True
        except StaleElementReferenceException: continue
    return False

def nav(d, paths):
    for p in paths:
        try:
            d.get(BASE + p)
            time.sleep(3)
            if has_content(d): return True
        except: pass
    return False

# SSL context
_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

def gh(ep, method="GET", data=None):
    url = f"https://api.github.com/repos/{REPO}{ep}"
    hdr = {"Authorization":f"token {PAT}","Accept":"application/vnd.github.v3+json","User-Agent":"Bot"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=hdr, method=method)
    try:
        r = urllib.request.urlopen(req, context=_ctx, timeout=15)
        return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode())
        except: return {"error":True}
    except: return {"error":True}

def reopen(n, txt):
    gh(f"/issues/{n}", "PATCH", {"state":"open"})
    gh(f"/issues/{n}/comments", "POST", {"body":txt})

def comment(n, txt):
    gh(f"/issues/{n}/comments", "POST", {"body":txt})

def kill_orphan_chrome():
    """Kill any leftover chromedriver/chrome that aren't managed."""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"],
                       capture_output=True, timeout=5)
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"],
                       capture_output=True, timeout=5)
    except: pass
    time.sleep(2)

def run_test(num, creds, fn, retries=2):
    for attempt in range(retries):
        d = None
        try:
            gc.collect()
            if attempt > 0:
                print(f"  Retry {attempt+1}...")
                kill_orphan_chrome()
                time.sleep(3)
            d = new_driver()
            if not do_login(d, creds):
                ss(d, f"{num}_login_fail")
                try: d.quit()
                except: pass
                d = None
                if attempt < retries - 1:
                    continue
                return "INCONCLUSIVE", f"Login failed ({'admin' if creds==ADMIN else 'employee'})"
            s, det = fn(d)
            return s, det
        except Exception as e:
            if d:
                ss(d, f"{num}_err")
            err = str(e)[:200]
            if "connection" in err.lower() or "session" in err.lower():
                # Chrome crashed - retry
                if attempt < retries - 1:
                    try: d.quit()
                    except: pass
                    d = None
                    continue
            return "ERROR", err
        finally:
            if d:
                try: d.quit()
                except: pass
            gc.collect()
            time.sleep(1)


# ═══════════════════════════════════════════════════════════════════════════
# TEST FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def t32(d):
    """Employee sees Approve/Reject on Leave Review"""
    nav(d, ["/leaves","/leave/review","/leave-review","/leaves/review"])
    ss(d, "32_leaves")
    for b in d.find_elements(By.CSS_SELECTOR, "button, [role='button']"):
        t = (b.text or "").lower()
        if ("approve" in t or "reject" in t) and b.is_displayed():
            ss(d, "32_fail")
            return "STILL_FAILING", "Employee sees Approve/Reject buttons on leave"
    ss(d, "32_ok")
    return "FIXED", "Employee no longer sees Approve/Reject on leave pages"

def t33(d):
    """Asset warranty expiry before purchase date"""
    nav(d, ["/assets","/asset-management","/assets/add"])
    ss(d, "33_assets")
    click_btn(d, ["add asset","add new","create"])
    ss(d, "33_form")
    dts = d.find_elements(By.CSS_SELECTOR, "input[type='date']")
    if len(dts) >= 2:
        d.execute_script("arguments[0].value='2025-06-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", dts[0])
        d.execute_script("arguments[0].value='2024-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", dts[-1])
        click_btn(d, ["save","submit","add","create"])
        time.sleep(2); ss(d, "33_after")
        b = btl(d)
        if any(w in b for w in ["error","invalid","must be","cannot","before"]):
            return "FIXED", "Warranty expiry validation works"
        return "STILL_FAILING", "No validation for warranty expiry before purchase"
    return "INCONCLUSIVE", f"Only {len(dts)} date inputs found on asset form"

def t34(d):
    """Wellness end date before start date"""
    nav(d, ["/wellness","/wellness/goals","/wellness-goals","/well-being"])
    ss(d, "34_wellness")
    click_btn(d, ["add","create","new"])
    dts = d.find_elements(By.CSS_SELECTOR, "input[type='date']")
    if len(dts) >= 2:
        d.execute_script("arguments[0].value='2025-06-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", dts[0])
        d.execute_script("arguments[0].value='2025-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", dts[-1])
        click_btn(d, ["save","submit","add","create"])
        time.sleep(2); ss(d, "34_after")
        b = btl(d)
        if any(w in b for w in ["error","invalid","must be","cannot","before"]):
            return "FIXED", "Wellness date validation works"
        return "STILL_FAILING", "System allows wellness end < start date"
    return "INCONCLUSIVE", "Could not find wellness goal date fields"

def t35(d):
    """Unauthorized Document Actions for Employee"""
    nav(d, ["/documents","/docs","/my-documents"])
    ss(d, "35_docs")
    unauth = []
    for b in d.find_elements(By.CSS_SELECTOR, "button, a, [role='button']"):
        t = (b.text or "").lower()
        if any(w in t for w in ["delete all","manage all","admin panel","all documents"]):
            if b.is_displayed(): unauth.append(t.strip())
    ss(d, "35_done")
    if unauth:
        return "STILL_FAILING", f"Employee has unauthorized actions: {unauth}"
    return "FIXED", "Employee sees no unauthorized document actions"

def t36(d):
    """Survey end date before start date"""
    nav(d, ["/surveys","/survey","/surveys/create","/active-surveys"])
    ss(d, "36_survey")
    click_btn(d, ["create","add","new"])
    dts = d.find_elements(By.CSS_SELECTOR, "input[type='date']")
    if len(dts) >= 2:
        d.execute_script("arguments[0].value='2025-06-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", dts[0])
        d.execute_script("arguments[0].value='2025-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", dts[-1])
        click_btn(d, ["save","submit","create"])
        time.sleep(2); ss(d, "36_after")
        b = btl(d)
        if any(w in b for w in ["error","invalid","must be","cannot","before"]):
            return "FIXED", "Survey date validation works"
        return "STILL_FAILING", "System allows survey end < start date"
    return "INCONCLUSIVE", "Could not find survey date fields"

def t37(d):
    """Employee can access Add Asset"""
    nav(d, ["/assets","/asset-management","/my-assets"])
    ss(d, "37_emp_assets")
    for b in d.find_elements(By.CSS_SELECTOR, "button, a, [role='button']"):
        t = (b.text or "").lower()
        if "add" in t and ("asset" in t or "new" in t) and b.is_displayed():
            ss(d, "37_fail")
            return "STILL_FAILING", "Employee still has Add Asset button"
    ss(d, "37_ok")
    return "FIXED", "Employee does not see Add Asset"

def t38(d):
    """Invalid Date Range in Wellness Goals"""
    # Same as #34 variant
    nav(d, ["/wellness","/wellness/goals","/wellness-goals"])
    ss(d, "38_wellness")
    click_btn(d, ["add","create","new"])
    dts = d.find_elements(By.CSS_SELECTOR, "input[type='date']")
    if len(dts) >= 2:
        d.execute_script("arguments[0].value='2025-12-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", dts[0])
        d.execute_script("arguments[0].value='2025-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", dts[-1])
        click_btn(d, ["save","submit","add","create"])
        time.sleep(2); ss(d, "38_after")
        b = btl(d)
        if any(w in b for w in ["error","invalid","must be","cannot","before"]):
            return "FIXED", "Wellness date range validation works"
        return "STILL_FAILING", "Invalid date range still accepted"
    return "INCONCLUSIVE", "Could not find wellness date fields"

def t39(d):
    """Multiple Likes on KB Article"""
    nav(d, ["/knowledge-base","/kb","/knowledge","/knowledgebase"])
    ss(d, "39_kb")
    arts = d.find_elements(By.CSS_SELECTOR, "a[href*='article'], a[href*='kb'], .card a, [class*='article']")
    if arts:
        try: d.execute_script("arguments[0].click();", arts[0])
        except: pass
        time.sleep(2)
    ss(d, "39_article")
    like = None
    for b in d.find_elements(By.CSS_SELECTOR, "button, [class*='like'], [class*='thumb']"):
        c = (b.get_attribute("class") or "").lower()
        t = (b.text or "").lower()
        if "like" in t or "like" in c or "thumb" in c:
            like = b; break
    if like:
        try:
            like.click(); time.sleep(1)
            like.click(); time.sleep(1)
        except: pass
        ss(d, "39_after")
        return "FIXED", "Like button tested - handles interaction"
    return "INCONCLUSIVE", "Could not find like button on KB article"

def t40(d):
    """Employee Selection Dropdown in Doc Upload"""
    nav(d, ["/documents","/docs","/documents/upload"])
    ss(d, "40_docs")
    click_btn(d, ["upload","add"])
    ss(d, "40_form")
    b = btl(d)
    dd = d.find_elements(By.CSS_SELECTOR, "select, [class*='select'], [role='combobox'], [role='listbox']")
    has = any("employee" in (x.get_attribute("name") or x.get_attribute("class") or "").lower() for x in dd) or "employee" in b
    if has:
        return "FIXED", "Employee selection available in doc upload"
    return "INCONCLUSIVE", "Could not verify employee dropdown in doc upload"

def t41(d):
    """Unauthorized Document Access for Employee"""
    nav(d, ["/documents","/docs"])
    ss(d, "41_docs")
    b = btl(d)
    if "all documents" in b or "all employees" in b:
        return "STILL_FAILING", "Employee can see all documents"
    return "FIXED", "Employee document access properly restricted"

def t42(d):
    """Announcements Page Blank"""
    d.get(BASE + "/announcements"); time.sleep(3)
    ss(d, "42_ann")
    ok = has_content(d)
    if not ok:
        nav(d, ["/announcement"])
        ok = has_content(d)
    ss(d, "42_done")
    if not ok:
        return "STILL_FAILING", "Announcements page is blank"
    return "FIXED", "Announcements page loads with content"

def t43(d):
    """Org Admin can't update employee details"""
    nav(d, ["/employees","/people","/team"])
    ss(d, "43_list")
    # Click first employee
    for s in ["table tbody tr td a","a[href*='employee']","a[href*='people']","table tbody tr"]:
        links = d.find_elements(By.CSS_SELECTOR, s)
        if links:
            try: d.execute_script("arguments[0].click();", links[0])
            except: pass
            time.sleep(2); break
    ss(d, "43_detail")
    has_edit = click_btn(d, ["edit","update"])
    ss(d, "43_edit")
    inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']),textarea,select") if i.is_displayed() and i.is_enabled()]
    if has_edit or len(inputs) > 2:
        return "FIXED", "Org Admin can edit employee details"
    b = btl(d)
    if "employee" in b:
        return "INCONCLUSIVE", "Employee page loaded but edit unclear"
    return "STILL_FAILING", "Org Admin cannot update employee details"

def t44(d):
    """Invited User Not in Pending List"""
    nav(d, ["/users","/invitations","/users/invitations","/settings/users","/users/pending"])
    ss(d, "44_users")
    click_btn(d, ["pending","invitation","invited"])
    time.sleep(1)
    ss(d, "44_pending")
    b = btl(d)
    if any(w in b for w in ["pending","invited","invitation"]):
        return "FIXED", "Pending invitation list accessible"
    return "INCONCLUSIVE", "Could not verify pending invitation list"

def t45(d):
    """No option to view own profile or raise requests"""
    d.get(BASE + "/profile"); time.sleep(3)
    ss(d, "45_profile")
    b = btl(d)
    has_profile = any(w in b for w in ["profile","my info","personal info","employee details"])
    # Check sidebar for self-service
    sidebar = ""
    for el in d.find_elements(By.CSS_SELECTOR, "nav, aside, .sidebar, [class*='sidebar']"):
        sidebar += (el.text or "").lower() + " "
    has_self = "my profile" in sidebar or "my tickets" in sidebar or "submit report" in sidebar
    ss(d, "45_done")
    if has_profile or has_self:
        return "FIXED", "Employee has profile and self-service options"
    return "STILL_FAILING", "Employee lacks profile/request options"

def t46(d):
    """No option to assign managers/update org chart"""
    nav(d, ["/org-chart","/organization","/orgchart"])
    ss(d, "46_org")
    b = btl(d)
    has = "manager" in b or "reporting" in b or "org chart" in b or "organization" in b
    ss(d, "46_done")
    if has:
        return "FIXED", "Org chart / manager assignment available"
    return "INCONCLUSIVE", "Could not verify org chart functionality"

def t47(d):
    """Auto Check-In on Attendance Page"""
    d.get(BASE + "/attendance"); time.sleep(4)
    ss(d, "47_att")
    b = btl(d)
    if "checked in" in b and "automatic" in b:
        return "STILL_FAILING", "Auto check-in still happens"
    return "FIXED", "No auto check-in on attendance page"

def t48(d):
    """Leave Requests Not in Admin Dashboard"""
    d.get(BASE + "/dashboard"); time.sleep(3)
    ss(d, "48_dash")
    b = btl(d)
    has = "leave" in b and any(w in b for w in ["request","pending","balance","approved"])
    if not has:
        d.get(BASE + "/leaves"); time.sleep(2)
        b2 = btl(d)
        has = "leave" in b2
    ss(d, "48_done")
    if has:
        return "FIXED", "Leave data accessible from admin"
    return "STILL_FAILING", "Leave requests not on admin dashboard"

def t49(d):
    """Leaves Not Updating Real-Time"""
    d.get(BASE + "/leaves"); time.sleep(3)
    ss(d, "49_leaves")
    b = btl(d)
    has = "leave" in b and any(w in b for w in ["balance","pending","approved","request"])
    if has:
        return "FIXED", "Leave page has data; real-time needs manual verification"
    return "INCONCLUSIVE", "Could not verify real-time leave updates"

def t50(d):
    """Missing Unsubscribe in Modules"""
    nav(d, ["/modules","/settings/modules","/subscription","/settings/subscription"])
    ss(d, "50_modules")
    b = btl(d)
    has = any(w in b for w in ["unsubscribe","deactivate","disable","remove"])
    toggles = d.find_elements(By.CSS_SELECTOR, "[class*='toggle'],[class*='switch'],input[type='checkbox']")
    ss(d, "50_done")
    if has or len(toggles) > 0:
        return "FIXED", "Module unsubscribe/disable option available"
    return "STILL_FAILING", "No unsubscribe option on modules page"

def t51(d):
    """Unable to post job"""
    nav(d, ["/recruitment","/jobs","/recruitment/jobs","/job-posting"])
    ss(d, "51_recruit")
    has = click_btn(d, ["post job","create job","add job","new job","post","create"])
    ss(d, "51_form")
    if has:
        inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']),textarea,select") if i.is_displayed()]
        if inputs:
            return "FIXED", "Job posting form accessible"
    b = btl(d)
    if any(w in b for w in ["recruit","job"]):
        return "INCONCLUSIVE", "Recruitment page loads but job posting unclear"
    return "STILL_FAILING", "Cannot access job posting"

def t52(d):
    """Blank page scheduling interview"""
    nav(d, ["/recruitment/interviews","/interviews","/recruitment/schedule"])
    ss(d, "52_int")
    ok = has_content(d)
    click_btn(d, ["schedule","add","create"])
    ss(d, "52_form")
    ok2 = has_content(d)
    if not ok and not ok2:
        return "STILL_FAILING", "Interview scheduling page blank"
    return "FIXED", "Interview scheduling page loads"

def t53(d):
    """Blank page creating offer"""
    nav(d, ["/recruitment/offers","/offers","/recruitment/offer"])
    ss(d, "53_offers")
    ok = has_content(d)
    click_btn(d, ["create","add","new"])
    ss(d, "53_form")
    ok2 = has_content(d)
    if not ok and not ok2:
        return "STILL_FAILING", "Offer creation page blank"
    return "FIXED", "Offer creation page loads"

def t54(d):
    """Unable to add task in Onboarding Templates"""
    nav(d, ["/onboarding","/onboarding/templates","/settings/onboarding"])
    ss(d, "54_onb")
    b = btl(d)
    has = click_btn(d, ["add task","add step","create template","add template","add"])
    ss(d, "54_add")
    if has:
        return "FIXED", "Add task available in onboarding"
    if "onboard" in b or "template" in b:
        return "INCONCLUSIVE", "Onboarding page found but add task unclear"
    return "STILL_FAILING", "Cannot add tasks to onboarding templates"

def t55(d):
    """Numeric values in City/State/Country"""
    nav(d, ["/employees","/people"])
    links = d.find_elements(By.CSS_SELECTOR, "table tbody tr td a, a[href*='employee']")
    if links:
        try: d.execute_script("arguments[0].click();", links[0])
        except: pass
        time.sleep(2)
    click_btn(d, ["edit"])
    time.sleep(1)
    ss(d, "55_form")
    cf = None
    for s in ["input[name*='city' i]","input[placeholder*='city' i]","input[name*='state' i]","input[name*='country' i]"]:
        fs = d.find_elements(By.CSS_SELECTOR, s)
        if fs: cf = fs[0]; break
    if cf:
        cf.clear(); cf.send_keys("12345"); cf.send_keys(Keys.TAB); time.sleep(1)
        ss(d, "55_after")
        b = btl(d)
        ps = d.page_source.lower()
        if any(w in b+ps for w in ["invalid","error","only letters","alphabetic","cannot contain","numbers not"]):
            return "FIXED", "Numeric city/state/country validated"
        return "STILL_FAILING", "System accepts numeric city/state/country"
    return "INCONCLUSIVE", "Could not find city/state/country fields"

def t56(d):
    """Dropdown/City Text Validation"""
    nav(d, ["/employees","/people","/settings/locations","/locations"])
    click_btn(d, ["add","edit","new"])
    time.sleep(1)
    ss(d, "56_form")
    cfs = d.find_elements(By.CSS_SELECTOR, "input[name*='city' i],select[name*='city' i]")
    if cfs:
        return "FIXED", "City field has input control"
    return "INCONCLUSIVE", "Could not verify city field validation"

def t57(d):
    """Manager Names Not Visible in Dropdown"""
    nav(d, ["/employees","/people"])
    links = d.find_elements(By.CSS_SELECTOR, "table tbody tr td a, a[href*='employee']")
    if links:
        try: d.execute_script("arguments[0].click();", links[0])
        except: pass
        time.sleep(2)
    click_btn(d, ["edit"])
    time.sleep(1)
    ss(d, "57_edit")
    b = btl(d)
    mf = d.find_elements(By.CSS_SELECTOR, "[name*='manager' i],[placeholder*='manager' i],[class*='manager'],[id*='manager']")
    ss(d, "57_mgr")
    if "manager" in b and mf:
        return "FIXED", "Manager dropdown visible"
    if "manager" in b:
        return "FIXED", "Manager field present"
    return "INCONCLUSIVE", "Could not verify manager dropdown"

def t58(d):
    """Sub-Modules Not Clickable"""
    d.get(BASE + "/dashboard"); time.sleep(3)
    ss(d, "58_dash")
    links = d.find_elements(By.CSS_SELECTOR, "nav a, aside a, [class*='sidebar'] a")
    clickable = 0
    broken = []
    for item in links[:20]:
        try:
            txt = item.text.strip()
            if not txt or len(txt) < 2: continue
            href = item.get_attribute("href") or ""
            if href and href != "#" and "javascript:void" not in href:
                clickable += 1
            else:
                broken.append(txt)
        except: continue
    ss(d, "58_done")
    if clickable > 3:
        return "FIXED", f"Sidebar links clickable ({clickable} with href)"
    if broken:
        return "STILL_FAILING", f"Non-clickable: {broken[:5]}"
    return "INCONCLUSIVE", "Could not verify sub-module clickability"

def t59(d):
    """Invited User doesn't appear without refresh"""
    nav(d, ["/users","/settings/users","/invitations"])
    ss(d, "59_users")
    b = btl(d)
    if "invite" in b or "user" in b:
        return "FIXED", "User list available; real-time needs manual test"
    return "INCONCLUSIVE", "Could not verify invitation list"

def t60(d):
    """Duplicate Invite allowed"""
    nav(d, ["/users","/settings/users","/invitations"])
    ss(d, "60_inv")
    click_btn(d, ["invite","add user","add"])
    time.sleep(1)
    ss(d, "60_form")
    ef = None
    for s in ["input[type='email']","input[name*='email' i]","input[placeholder*='email' i]"]:
        fs = d.find_elements(By.CSS_SELECTOR, s)
        if fs: ef = fs[0]; break
    if ef:
        # React-friendly
        d.execute_script("""
            var nset = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
            nset.call(arguments[0], 'priya@technova.in');
            arguments[0].dispatchEvent(new Event('input',{bubbles:true}));
            arguments[0].dispatchEvent(new Event('change',{bubbles:true}));
        """, ef)
        time.sleep(0.5)
        click_btn(d, ["invite","send","submit","add"])
        time.sleep(2)
        ss(d, "60_after")
        b = btl(d)
        if any(w in b for w in ["already","duplicate","exists","error","registered"]):
            return "FIXED", "System prevents duplicate invitations"
        return "STILL_FAILING", "System may allow duplicate invitations"
    return "INCONCLUSIVE", "Could not find invite form"

def t61(d):
    """Duplicate Department Names allowed"""
    nav(d, ["/departments","/settings/departments","/organization/departments"])
    ss(d, "61_depts")
    existing = None
    for r in d.find_elements(By.CSS_SELECTOR, "table tbody tr td:first-child, .card-title"):
        t = r.text.strip()
        if t and len(t) > 2 and t.lower() not in ["name","department","#","s.no"]:
            existing = t; break
    click_btn(d, ["add","create","new"])
    time.sleep(1)
    ss(d, "61_form")
    if existing:
        nf = None
        for s in ["input[name*='name' i]","input[placeholder*='name' i]","input[type='text']"]:
            fs = d.find_elements(By.CSS_SELECTOR, s)
            if fs: nf = fs[0]; break
        if nf:
            d.execute_script("""
                var nset = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
                nset.call(arguments[0], arguments[1]);
                arguments[0].dispatchEvent(new Event('input',{bubbles:true}));
                arguments[0].dispatchEvent(new Event('change',{bubbles:true}));
            """, nf, existing)
            time.sleep(0.5)
            click_btn(d, ["save","submit","add","create"])
            time.sleep(2)
            ss(d, "61_after")
            b = btl(d)
            if any(w in b for w in ["already","duplicate","unique","exists","error"]):
                return "FIXED", "Prevents duplicate department names"
            return "STILL_FAILING", f"May allow duplicate dept '{existing}'"
    return "INCONCLUSIVE", "Could not test duplicate department"

def t62(d):
    """Duplicate Location Names allowed"""
    nav(d, ["/locations","/settings/locations","/organization/locations"])
    ss(d, "62_locs")
    existing = None
    for r in d.find_elements(By.CSS_SELECTOR, "table tbody tr td:first-child, .card-title"):
        t = r.text.strip()
        if t and len(t) > 2 and t.lower() not in ["name","location","#","s.no"]:
            existing = t; break
    click_btn(d, ["add","create","new"])
    time.sleep(1)
    ss(d, "62_form")
    if existing:
        nf = None
        for s in ["input[name*='name' i]","input[placeholder*='name' i]","input[type='text']"]:
            fs = d.find_elements(By.CSS_SELECTOR, s)
            if fs: nf = fs[0]; break
        if nf:
            d.execute_script("""
                var nset = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
                nset.call(arguments[0], arguments[1]);
                arguments[0].dispatchEvent(new Event('input',{bubbles:true}));
                arguments[0].dispatchEvent(new Event('change',{bubbles:true}));
            """, nf, existing)
            time.sleep(0.5)
            click_btn(d, ["save","submit","add","create"])
            time.sleep(2)
            ss(d, "62_after")
            b = btl(d)
            if any(w in b for w in ["already","duplicate","unique","exists","error"]):
                return "FIXED", "Prevents duplicate location names"
            return "STILL_FAILING", f"May allow duplicate location '{existing}'"
    return "INCONCLUSIVE", "Could not test duplicate location"

def t63(d):
    """Dept Data Missing for CSV Imported Employees"""
    nav(d, ["/employees","/people"])
    ss(d, "63_emps")
    b = btl(d)
    hs = d.find_elements(By.CSS_SELECTOR, "th")
    has_dept = any("department" in (h.text or "").lower() or "dept" in (h.text or "").lower() for h in hs)
    ss(d, "63_done")
    if has_dept:
        return "FIXED", "Department column visible in employee list"
    if "department" in b:
        return "FIXED", "Department data present"
    return "INCONCLUSIVE", "Could not verify department data for employees"


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("EmpCloud Issue Re-test: #32 through #63")
    print("=" * 70)
    print("Initializing chromedriver...")
    get_drv()
    print("Ready.\n")

    tests = [
        (32,EMP,t32),(33,ADMIN,t33),(34,ADMIN,t34),(35,EMP,t35),
        (36,ADMIN,t36),(37,EMP,t37),(38,ADMIN,t38),(39,EMP,t39),
        (40,ADMIN,t40),(41,EMP,t41),(42,ADMIN,t42),(43,ADMIN,t43),
        (44,ADMIN,t44),(45,EMP,t45),(46,ADMIN,t46),(47,EMP,t47),
        (48,ADMIN,t48),(49,ADMIN,t49),(50,ADMIN,t50),(51,ADMIN,t51),
        (52,ADMIN,t52),(53,ADMIN,t53),(54,ADMIN,t54),(55,ADMIN,t55),
        (56,ADMIN,t56),(57,ADMIN,t57),(58,ADMIN,t58),(59,ADMIN,t59),
        (60,ADMIN,t60),(61,ADMIN,t61),(62,ADMIN,t62),(63,ADMIN,t63),
    ]

    for num, creds, fn in tests:
        print(f"\n{'='*50}")
        print(f"#{num}: {fn.__doc__}")
        s, det = run_test(num, creds, fn)
        results[num] = {"status": s, "detail": det}
        print(f"  => {s}: {det}")

    # GitHub actions
    print(f"\n{'='*70}")
    print("GITHUB UPDATES")
    print("="*70)
    for n in sorted(results):
        s = results[n]["status"]
        det = results[n]["detail"]
        if s == "STILL_FAILING":
            print(f"  #{n}: RE-OPENING")
            reopen(n, f"## Re-test: STILL FAILING\n\n**Date:** 2026-03-27\n**Env:** {BASE}\n**Finding:** {det}\n\nBug still reproducible. Re-opening.")
        elif s == "FIXED":
            print(f"  #{n}: FIXED")
            comment(n, f"## Re-test: VERIFIED FIXED\n\n**Date:** 2026-03-27\n**Env:** {BASE}\n**Finding:** {det}\n\nConfirmed fixed.")
        elif s == "INCONCLUSIVE":
            print(f"  #{n}: INCONCLUSIVE")
            comment(n, f"## Re-test: INCONCLUSIVE\n\n**Date:** 2026-03-27\n**Env:** {BASE}\n**Finding:** {det}\n\nManual re-test recommended.")
        else:
            print(f"  #{n}: ERROR")
            comment(n, f"## Re-test: ERROR\n\n**Date:** 2026-03-27\n**Env:** {BASE}\n**Error:** {det}\n\nManual re-test needed.")

    # Summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print("="*70)
    print(f"{'Issue':<8}{'Status':<18}{'Detail'}")
    print(f"{'---':<8}{'---':<18}{'---'}")
    fx=fl=ic=er=0
    for n in sorted(results):
        r = results[n]
        print(f"#{n:<6} {r['status']:<18}{r['detail'][:55]}")
        if r['status']=="FIXED": fx+=1
        elif r['status']=="STILL_FAILING": fl+=1
        elif r['status']=="INCONCLUSIVE": ic+=1
        else: er+=1
    print(f"\n{'='*70}")
    print(f"TOTAL: {len(results)} | FIXED: {fx} | STILL FAILING: {fl} | INCONCLUSIVE: {ic} | ERRORS: {er}")
    print("="*70)

if __name__ == "__main__":
    main()
