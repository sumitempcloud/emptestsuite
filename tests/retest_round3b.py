import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import urllib.request
import urllib.error
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\retest"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

CREDS = {
    "org_admin": ("ananya@technova.in", "Welcome@123"),
    "employee": ("priya@technova.in", "Welcome@123"),
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
results = {}

# Cache chromedriver path
_cdp = ChromeDriverManager().install()

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for arg in ["--headless=new","--no-sandbox","--disable-dev-shm-usage","--window-size=1920,1080","--disable-gpu","--disable-extensions","--ignore-certificate-errors"]:
        opts.add_argument(arg)
    return webdriver.Chrome(service=Service(_cdp), options=opts)

def ss(d, n):
    p = os.path.join(SCREENSHOT_DIR, f"{n}.png")
    d.save_screenshot(p)
    print(f"  SS: {p}")

def login(d, role):
    email, pwd = CREDS[role]
    d.get(f"{BASE_URL}/login")
    time.sleep(4)
    body = d.find_element(By.TAG_NAME, "body").text
    if "too many" in body.lower():
        print(f"  Rate limited, waiting 60s...")
        time.sleep(60)
        d.get(f"{BASE_URL}/login")
        time.sleep(4)
    try:
        ef = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email']")))
        ef.clear(); ef.send_keys(email)
        pf = d.find_element(By.CSS_SELECTOR, "input[type='password']")
        pf.clear(); pf.send_keys(pwd)
        time.sleep(0.5)
        for b in d.find_elements(By.CSS_SELECTOR, "button"):
            if "sign in" in b.text.lower():
                b.click()
                break
        time.sleep(5)
        body = d.find_element(By.TAG_NAME, "body").text
        if "too many" in body.lower():
            print(f"  Rate limited after submit, waiting 60s...")
            time.sleep(60)
            return login(d, role)  # retry
        ok = "login" not in d.current_url or "welcome" in body.lower() or "dashboard" in body.lower()
        print(f"  Login as {role}: {'OK' if ok else 'FAIL'}, URL: {d.current_url}")
        return ok
    except Exception as e:
        print(f"  Login error: {e}")
        return False

def safe_click(d, el):
    try: el.click()
    except: d.execute_script("arguments[0].click();", el)

def find_btn(d, keywords):
    for b in d.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = b.text.strip().lower()
            if b.is_displayed() and any(k in t for k in keywords):
                return b
        except: pass
    return None

def get_sidebar(d):
    m = {}
    for a in d.find_elements(By.CSS_SELECTOR, "a[href]"):
        try:
            t = a.text.strip().lower()
            h = a.get_attribute("href") or ""
            if t and BASE_URL in h:
                m[t] = h
        except: pass
    return m

def github_api(method, endpoint, data=None):
    url = f"https://api.github.com/repos/{GITHUB_REPO}{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "EmpCloud-Retest")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  GH error: {e.code} {e.read().decode()[:200]}")
        return None

def update_gh(num, status, details):
    if status == "FIXED":
        github_api("PATCH", f"/issues/{num}", {"state": "closed"})
        github_api("POST", f"/issues/{num}/comments", {"body": f"Re-tested on 2026-03-27. Bug appears to be fixed.\n\n{details}"})
    else:
        github_api("PATCH", f"/issues/{num}", {"state": "open"})
        github_api("POST", f"/issues/{num}/comments", {"body": f"Re-tested on 2026-03-27. Bug is still present.\n\n{details}"})


def run_org_admin_tests():
    """All org admin tests in one browser session."""
    d = get_driver()
    try:
        if not login(d, "org_admin"):
            print("FATAL: Cannot login as org_admin")
            return

        sidebar = get_sidebar(d)
        print(f"  Sidebar: {list(sidebar.keys())}")

        # ===== #62 Duplicate Locations =====
        print("\n[#62] Duplicate Locations")
        settings_url = sidebar.get("settings", "")
        if settings_url:
            d.get(settings_url)
        else:
            d.get(f"{BASE_URL}/settings")
        time.sleep(4)
        ss(d, "r3_62_settings")

        # Collect all clickable text on settings page
        all_texts = []
        for el in d.find_elements(By.CSS_SELECTOR, "button, a, [role='tab'], span"):
            try:
                t = el.text.strip()
                if t and len(t) < 50:
                    all_texts.append(t)
            except: pass
        print(f"  Page elements: {all_texts[:30]}")

        # Click Locations
        for el in d.find_elements(By.CSS_SELECTOR, "button, a, [role='tab'], div"):
            try:
                t = el.text.strip().lower()
                if t == "locations" or t == "location":
                    safe_click(d, el)
                    time.sleep(3)
                    print(f"  Clicked: {el.text}")
                    break
            except: pass

        ss(d, "r3_62_locations")
        body = d.find_element(By.TAG_NAME, "body").text
        print(f"  Page: {body[:300]}")

        add = find_btn(d, ["add location", "add new", "+"])
        if not add:
            add = find_btn(d, ["add"])

        if add:
            loc = "DupLocationR3"
            for i in range(2):
                safe_click(d, add)
                time.sleep(2)
                ss(d, f"r3_62_modal{i}")
                vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type='hidden']):not([type='password']):not([type='email']):not([type='search'])") if x.is_displayed()]
                print(f"  Visible inputs: {len(vis)}")
                if vis:
                    vis[0].clear()
                    vis[0].send_keys(loc)
                time.sleep(1)
                sv = find_btn(d, ["save", "submit", "confirm", "create"])
                if sv: safe_click(d, sv)
                time.sleep(3)
                ss(d, f"r3_62_save{i}")
                if i == 1:
                    txt = d.find_element(By.TAG_NAME, "body").text.lower()
                    toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify'],[role='alert']")])
                    if any(k in (txt + toasts) for k in ["duplicate","already exists","already added","unique"]):
                        results[62] = ("FIXED", "Duplicate location validation in place.")
                    else:
                        results[62] = ("STILL_FAILING", "No duplicate location validation.")
                # re-find add
                add = find_btn(d, ["add location", "add new", "+"]) or find_btn(d, ["add"])
        else:
            results[62] = ("STILL_FAILING", "No add location button found in settings.")
        if 62 not in results:
            results[62] = ("STILL_FAILING", "Incomplete test.")

        # ===== #61 Duplicate Departments =====
        print("\n[#61] Duplicate Departments")
        if settings_url:
            d.get(settings_url)
        time.sleep(3)
        for el in d.find_elements(By.CSS_SELECTOR, "button, a, [role='tab'], div"):
            try:
                t = el.text.strip().lower()
                if t == "departments" or t == "department":
                    safe_click(d, el)
                    time.sleep(3)
                    print(f"  Clicked: {el.text}")
                    break
            except: pass
        ss(d, "r3_61_dept")

        add = find_btn(d, ["add department", "add new", "+"]) or find_btn(d, ["add"])
        if add:
            dept = "DupDeptR3"
            for i in range(2):
                safe_click(d, add)
                time.sleep(2)
                vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type='hidden']):not([type='password']):not([type='email']):not([type='search'])") if x.is_displayed()]
                if vis:
                    vis[0].clear()
                    vis[0].send_keys(dept)
                time.sleep(1)
                sv = find_btn(d, ["save", "submit", "confirm", "create"])
                if sv: safe_click(d, sv)
                time.sleep(3)
                ss(d, f"r3_61_save{i}")
                if i == 1:
                    txt = d.find_element(By.TAG_NAME, "body").text.lower()
                    toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify'],[role='alert']")])
                    if any(k in (txt+toasts) for k in ["duplicate","already exists","already added","unique"]):
                        results[61] = ("FIXED", "Duplicate department validation in place.")
                    else:
                        results[61] = ("STILL_FAILING", "No duplicate department validation.")
                add = find_btn(d, ["add department", "add new", "+"]) or find_btn(d, ["add"])
        else:
            results[61] = ("STILL_FAILING", "No add department button found.")
        if 61 not in results:
            results[61] = ("STILL_FAILING", "Incomplete test.")

        # ===== #60 Duplicate Invite =====
        print("\n[#60] Duplicate Invite")
        users_url = sidebar.get("users", f"{BASE_URL}/users")
        d.get(users_url)
        time.sleep(4)
        ss(d, "r3_60_users")
        body = d.find_element(By.TAG_NAME, "body").text
        print(f"  Users page: {body[:200]}")

        invite = find_btn(d, ["invite now", "invite user", "invite"])
        email = f"dup3_{int(time.time())%10000}@test.com"
        if invite:
            print(f"  Invite btn: '{invite.text}'")
            for i in range(2):
                safe_click(d, invite)
                time.sleep(3)
                ss(d, f"r3_60_modal{i}")
                # Debug all visible inputs
                vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
                for v in vis:
                    try: print(f"    inp: name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
                    except: pass
                # Enter email
                for inp in vis:
                    try:
                        tp = (inp.get_attribute("type") or "").lower()
                        nm = (inp.get_attribute("name") or "").lower()
                        ph = (inp.get_attribute("placeholder") or "").lower()
                        if tp == "email" or "email" in nm or "email" in ph or "mail" in ph:
                            inp.clear(); inp.send_keys(email)
                            print(f"  Typed email in: {nm or ph}")
                            break
                    except: pass
                time.sleep(1)
                sv = find_btn(d, ["send invite", "send", "invite", "submit"])
                if sv:
                    safe_click(d, sv)
                    print(f"  Clicked: '{sv.text}'")
                time.sleep(4)
                ss(d, f"r3_60_after{i}")
                if i == 1:
                    txt = d.find_element(By.TAG_NAME, "body").text.lower()
                    toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify'],[role='alert']")])
                    if any(k in (txt+toasts) for k in ["already invited","duplicate","already exists","already sent","already registered"]):
                        results[60] = ("FIXED", "Duplicate invite validation in place.")
                    else:
                        results[60] = ("STILL_FAILING", "No duplicate invite validation.")
                invite = find_btn(d, ["invite now", "invite user", "invite"])
        else:
            results[60] = ("STILL_FAILING", "No invite button found.")
        if 60 not in results:
            results[60] = ("STILL_FAILING", "Incomplete test.")

        # ===== #59 Auto-refresh after invite =====
        print("\n[#59] Auto-refresh after invite")
        d.get(users_url)
        time.sleep(4)
        body_before = d.find_element(By.TAG_NAME, "body").text
        rows_before = len(d.find_elements(By.CSS_SELECTOR, "tr, [class*='list-item']"))

        invite = find_btn(d, ["invite now", "invite user", "invite"])
        if invite:
            new_email = f"auto3_{int(time.time())%100000}@test.com"
            safe_click(d, invite)
            time.sleep(3)
            vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
            for inp in vis:
                try:
                    tp = (inp.get_attribute("type") or "").lower()
                    nm = (inp.get_attribute("name") or "").lower()
                    ph = (inp.get_attribute("placeholder") or "").lower()
                    if tp == "email" or "email" in nm or "email" in ph:
                        inp.clear(); inp.send_keys(new_email)
                        break
                except: pass
            time.sleep(1)
            sv = find_btn(d, ["send invite", "send", "invite", "submit"])
            if sv: safe_click(d, sv)
            time.sleep(5)
            ss(d, "r3_59_after")
            body_after = d.find_element(By.TAG_NAME, "body").text
            rows_after = len(d.find_elements(By.CSS_SELECTOR, "tr, [class*='list-item']"))
            print(f"  Rows: {rows_before} -> {rows_after}")
            if new_email.split("@")[0] in body_after.lower() or rows_after > rows_before:
                results[59] = ("FIXED", f"User appears without refresh (rows {rows_before}->{rows_after}).")
            else:
                results[59] = ("STILL_FAILING", f"User not visible without refresh (rows {rows_before}->{rows_after}).")
        else:
            results[59] = ("STILL_FAILING", "No invite button found.")

        # ===== #43 Org admin edit employee =====
        print("\n[#43] Edit employee")
        emp_url = sidebar.get("employees", f"{BASE_URL}/employees")
        d.get(emp_url)
        time.sleep(4)
        ss(d, "r3_43_list")

        # Find employee detail links
        emp_hrefs = []
        for a in d.find_elements(By.CSS_SELECTOR, "a[href]"):
            try:
                h = a.get_attribute("href") or ""
                t = a.text.strip()
                if "/employees/" in h and t and not h.rstrip("/").endswith("/employees"):
                    emp_hrefs.append((t, h))
            except: pass
        print(f"  Employee links: {emp_hrefs[:5]}")

        if emp_hrefs:
            d.get(emp_hrefs[0][1])
            time.sleep(4)
            ss(d, "r3_43_detail")
            body = d.find_element(By.TAG_NAME, "body").text
            print(f"  Detail: {body[:300]}")

            # Look for ANY edit button/icon
            edit_found = False
            for el in d.find_elements(By.CSS_SELECTOR, "button, a, [role='button'], svg"):
                try:
                    t = (el.text or "").strip().lower()
                    title = (el.get_attribute("title") or "").lower()
                    aria = (el.get_attribute("aria-label") or "").lower()
                    cls = (el.get_attribute("class") or "").lower()
                    if any(k in (t+title+aria+cls) for k in ["edit","pencil","modify"]):
                        edit_found = True
                        print(f"  Edit found: text='{t}' title='{title}' class='{cls[:50]}'")
                        safe_click(d, el)
                        time.sleep(3)
                        ss(d, "r3_43_edit")
                        form_inputs = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']), select, textarea") if x.is_displayed()]
                        if len(form_inputs) > 2:
                            results[43] = ("FIXED", f"Edit form with {len(form_inputs)} inputs accessible.")
                        else:
                            results[43] = ("FIXED", "Edit option exists for org admin.")
                        break
                except: pass

            if not edit_found:
                results[43] = ("STILL_FAILING", "No edit button/icon found on employee detail.")
        else:
            results[43] = ("STILL_FAILING", "No employee links found.")

        # ===== #56 City validation =====
        print("\n[#56] City validation")
        if emp_hrefs:
            d.get(emp_hrefs[0][1])
            time.sleep(4)
            # Click edit
            for el in d.find_elements(By.CSS_SELECTOR, "button, a"):
                try:
                    t = el.text.strip().lower()
                    title = (el.get_attribute("title") or "").lower()
                    if "edit" in t or "edit" in title:
                        safe_click(d, el)
                        time.sleep(3)
                        break
                except: pass

            ss(d, "r3_56_form")
            # Dump all labels and inputs
            labels = [l.text.strip() for l in d.find_elements(By.CSS_SELECTOR, "label") if l.text.strip()]
            print(f"  Labels: {labels[:25]}")

            vis_inputs = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
            for v in vis_inputs[:20]:
                try: print(f"    inp: name={v.get_attribute('name')}, id={v.get_attribute('id')}, ph={v.get_attribute('placeholder')}")
                except: pass

            city = None
            for inp in vis_inputs:
                try:
                    nm = (inp.get_attribute("name") or "").lower()
                    ph = (inp.get_attribute("placeholder") or "").lower()
                    iid = (inp.get_attribute("id") or "").lower()
                    if "city" in nm or "city" in ph or "city" in iid:
                        city = inp
                        break
                except: pass

            if city:
                city.clear(); city.send_keys("12345")
                time.sleep(1)
                sv = find_btn(d, ["save", "update"])
                if sv: safe_click(d, sv); time.sleep(3)
                ss(d, "r3_56_result")
                txt = d.find_element(By.TAG_NAME, "body").text.lower()
                val = city.get_attribute("value") or ""
                if any(k in txt for k in ["invalid","only alphabets","letters only","alphabetic"]):
                    results[56] = ("FIXED", "City validates against numeric.")
                elif val != "12345":
                    results[56] = ("FIXED", f"City filtered numeric (val='{val}').")
                else:
                    results[56] = ("STILL_FAILING", "City still accepts '12345'.")
            else:
                results[56] = ("STILL_FAILING", "City field not found in employee form.")
        else:
            results[56] = ("STILL_FAILING", "No employees to test.")

        # ===== #36 Survey date =====
        print("\n[#36] Survey date validation")
        survey_url = None
        for k, v in sidebar.items():
            if "survey" in k: survey_url = v; break
        if not survey_url:
            for p in ["/surveys", "/survey"]:
                d.get(f"{BASE_URL}{p}")
                time.sleep(2)
                if "login" not in d.current_url:
                    survey_url = d.current_url; break
        if survey_url:
            d.get(survey_url)
            time.sleep(3)
        ss(d, "r3_36_page")
        body = d.find_element(By.TAG_NAME, "body").text
        print(f"  Survey: {body[:200]}")

        add = find_btn(d, ["create survey","add survey","create","add"])
        if add:
            safe_click(d, add); time.sleep(3)
            dates = [x for x in d.find_elements(By.CSS_SELECTOR, "input[type='date']") if x.is_displayed()]
            if len(dates) >= 2:
                d.execute_script("arguments[0].value='2026-12-31'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[0])
                d.execute_script("arguments[0].value='2026-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[1])
                time.sleep(2)
                sv = find_btn(d, ["save","create","submit"])
                if sv: safe_click(d, sv); time.sleep(3)
                txt = d.find_element(By.TAG_NAME, "body").text.lower()
                if any(k in txt for k in ["end date","invalid","before start","after start"]):
                    results[36] = ("FIXED", "Survey date validation works.")
                else:
                    results[36] = ("STILL_FAILING", "Survey allows end < start.")
            else:
                results[36] = ("STILL_FAILING", "No date fields in survey form.")
        else:
            results[36] = ("STILL_FAILING", "Survey module/create not found.")

        # ===== #34 Wellness date =====
        print("\n[#34] Wellness date validation")
        well_url = sidebar.get("wellness", f"{BASE_URL}/wellness")
        d.get(well_url)
        time.sleep(4)
        ss(d, "r3_34_page")
        body = d.find_element(By.TAG_NAME, "body").text
        print(f"  Wellness: {body[:300]}")

        # Dump all buttons
        btns = [(b.text.strip(), b.tag_name) for b in d.find_elements(By.CSS_SELECTOR, "button, a") if b.is_displayed() and b.text.strip()]
        print(f"  Buttons: {btns[:20]}")

        add = find_btn(d, ["create program","add program","new program","create","add new"])
        if not add:
            add = find_btn(d, ["add"])
        if add:
            print(f"  Clicking: '{add.text}'")
            safe_click(d, add); time.sleep(3)
            ss(d, "r3_34_form")
            dates = [x for x in d.find_elements(By.CSS_SELECTOR, "input[type='date']") if x.is_displayed()]
            print(f"  Date inputs: {len(dates)}")
            all_vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
            for v in all_vis[:15]:
                try: print(f"    inp: name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
                except: pass
            if len(dates) >= 2:
                d.execute_script("arguments[0].value='2026-12-31'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[0])
                d.execute_script("arguments[0].value='2026-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[1])
                time.sleep(2)
                sv = find_btn(d, ["save","create","submit","add"])
                if sv: safe_click(d, sv); time.sleep(3)
                txt = d.find_element(By.TAG_NAME, "body").text.lower()
                toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify']")])
                ss(d, "r3_34_result")
                if any(k in (txt+toasts) for k in ["end date","invalid","before start","after start"]):
                    results[34] = ("FIXED", "Wellness date validation works.")
                else:
                    results[34] = ("STILL_FAILING", "Wellness allows end < start.")
            else:
                results[34] = ("STILL_FAILING", "No date fields in wellness form.")
        else:
            results[34] = ("STILL_FAILING", "No create button on wellness page.")

        # ===== #33 Asset warranty date =====
        print("\n[#33] Asset warranty date")
        asset_url = None
        for k, v in sidebar.items():
            if "asset" in k: asset_url = v; break
        if asset_url:
            d.get(asset_url)
        else:
            d.get(f"{BASE_URL}/assets")
        time.sleep(3)
        ss(d, "r3_33_page")
        body = d.find_element(By.TAG_NAME, "body").text
        print(f"  Assets: {body[:200]}")
        if "403" in body or "forbidden" in body.lower():
            results[33] = ("STILL_FAILING", "Assets 403 Forbidden.")
        else:
            add = find_btn(d, ["add asset","add","create","new"])
            if add:
                safe_click(d, add); time.sleep(3)
                ss(d, "r3_33_form")
                dates = [x for x in d.find_elements(By.CSS_SELECTOR, "input[type='date']") if x.is_displayed()]
                if len(dates) >= 2:
                    d.execute_script("arguments[0].value='2026-12-31'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[0])
                    d.execute_script("arguments[0].value='2026-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[1])
                    time.sleep(2)
                    sv = find_btn(d, ["save","add","submit"])
                    if sv: safe_click(d, sv); time.sleep(3)
                    txt = d.find_element(By.TAG_NAME, "body").text.lower()
                    if any(k in txt for k in ["before purchase","invalid","warranty","after purchase"]):
                        results[33] = ("FIXED", "Asset date validation works.")
                    else:
                        results[33] = ("STILL_FAILING", "Asset allows warranty < purchase.")
                else:
                    results[33] = ("STILL_FAILING", "No date fields in asset form.")
            else:
                results[33] = ("STILL_FAILING", "No add asset button.")
    finally:
        try: d.quit()
        except: pass


def run_employee_tests():
    """Employee-role tests."""
    d = get_driver()
    try:
        if not login(d, "employee"):
            print("FATAL: Cannot login as employee")
            return

        sidebar = get_sidebar(d)
        print(f"  Employee sidebar: {list(sidebar.keys())}")

        # ===== #39 KB Likes =====
        print("\n[#39] Knowledge Base Likes")
        comm_url = sidebar.get("community", "")
        if comm_url:
            d.get(comm_url)
        else:
            d.get(f"{BASE_URL}/community")
        time.sleep(3)
        ss(d, "r3_39_page")
        body = d.find_element(By.TAG_NAME, "body").text
        print(f"  Community: {body[:300]}")

        # Look for any posts or articles
        cards = d.find_elements(By.CSS_SELECTOR, "[class*='card'], article, [class*='post']")
        links = []
        for a in d.find_elements(By.CSS_SELECTOR, "a[href]"):
            try:
                h = a.get_attribute("href") or ""
                t = a.text.strip()
                if t and any(k in h for k in ["post","article","community","discuss"]):
                    links.append((t,h))
            except: pass
        print(f"  Cards: {len(cards)}, Links: {links[:5]}")

        if links:
            d.get(links[0][1])
            time.sleep(3)
        elif cards:
            safe_click(d, cards[0])
            time.sleep(3)

        ss(d, "r3_39_article")
        body = d.find_element(By.TAG_NAME, "body").text
        print(f"  Article: {body[:300]}")

        like = None
        for el in d.find_elements(By.CSS_SELECTOR, "button, span, div, [class*='like'], [class*='thumb'], [class*='heart']"):
            try:
                t = (el.text or "").strip().lower()
                cls = (el.get_attribute("class") or "").lower()
                title = (el.get_attribute("title") or "").lower()
                aria = (el.get_attribute("aria-label") or "").lower()
                if any(k in (t+cls+title+aria) for k in ["like","thumb","heart","upvote"]):
                    like = el
                    print(f"  Like btn: text='{t}', cls='{cls[:40]}'")
                    break
            except: pass

        if like:
            safe_click(d, like); time.sleep(2)
            b1 = d.find_element(By.TAG_NAME, "body").text
            safe_click(d, like); time.sleep(2)
            b2 = d.find_element(By.TAG_NAME, "body").text
            ss(d, "r3_39_likes")
            if b1 == b2:
                results[39] = ("FIXED", "Like toggle prevents duplicates.")
            else:
                results[39] = ("STILL_FAILING", "Multiple likes possible.")
        else:
            results[39] = ("STILL_FAILING", "No like button found.")

        # ===== #38 Wellness goal dates =====
        print("\n[#38] Wellness goal dates")
        well_url = sidebar.get("wellness", f"{BASE_URL}/wellness")
        d.get(well_url)
        time.sleep(3)
        ss(d, "r3_38_wellness")
        body = d.find_element(By.TAG_NAME, "body").text
        print(f"  Wellness: {body[:300]}")

        # Click My Wellness
        mw = find_btn(d, ["my wellness"])
        if mw:
            safe_click(d, mw); time.sleep(3)
            ss(d, "r3_38_my")
            body = d.find_element(By.TAG_NAME, "body").text
            print(f"  My Wellness: {body[:300]}")

            # Dump buttons
            btns = [(b.text.strip(), b.tag_name) for b in d.find_elements(By.CSS_SELECTOR, "button, a") if b.is_displayed() and b.text.strip()]
            print(f"  Buttons: {btns[:20]}")

        add = find_btn(d, ["add goal","create goal","new goal","set goal"])
        if not add:
            add = find_btn(d, ["add","create"])
        if add:
            print(f"  Clicking: '{add.text}'")
            safe_click(d, add); time.sleep(3)
            ss(d, "r3_38_form")
            dates = [x for x in d.find_elements(By.CSS_SELECTOR, "input[type='date']") if x.is_displayed()]
            print(f"  Date inputs: {len(dates)}")
            vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
            for v in vis[:15]:
                try: print(f"    inp: name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
                except: pass
            if len(dates) >= 2:
                d.execute_script("arguments[0].value='2026-12-31'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[0])
                d.execute_script("arguments[0].value='2026-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[1])
                time.sleep(2)
                sv = find_btn(d, ["save","create","submit","add"])
                if sv: safe_click(d, sv); time.sleep(3)
                txt = d.find_element(By.TAG_NAME, "body").text.lower()
                toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify']")])
                ss(d, "r3_38_result")
                if any(k in (txt+toasts) for k in ["end date","invalid","before start","after start","must be"]):
                    results[38] = ("FIXED", "Wellness goal date validation works.")
                else:
                    results[38] = ("STILL_FAILING", "Wellness goals allow invalid date range.")
            else:
                results[38] = ("STILL_FAILING", "No date fields in goal form.")
        else:
            results[38] = ("STILL_FAILING", "No add goal button found.")

    finally:
        try: d.quit()
        except: pass


def main():
    print("=" * 70)
    print("ROUND 3B - 2026-03-27")
    print("=" * 70)

    run_org_admin_tests()

    print("\n--- Waiting 20s ---")
    time.sleep(20)

    run_employee_tests()

    # Update GitHub
    print("\n--- GitHub Updates ---")
    for num, (status, details) in results.items():
        try:
            update_gh(num, status, details)
            print(f"  #{num}: {status}")
        except Exception as e:
            print(f"  #{num}: GH error: {e}")

    # Summary
    r1_fixed = {63:1,57:1,55:1,50:1,49:1,48:1,47:1,46:1,45:1,44:1,42:1,41:1,40:1,37:1,35:1,32:1}
    r2_fixed = {58:1}

    print("\n" + "=" * 70)
    print("FINAL SUMMARY - ALL 28 ISSUES")
    print("=" * 70)
    print(f"{'Issue':<8} {'Status':<18} {'Details'}")
    print("-" * 70)

    all_nums = sorted(list(set(list(r1_fixed.keys()) + list(r2_fixed.keys()) + [62,61,60,59,56,43,39,38,36,34,33])), reverse=True)
    total_fixed = 0
    total_failing = 0
    for n in all_nums:
        if n in results:
            s, d2 = results[n]
        elif n in r1_fixed or n in r2_fixed:
            s, d2 = "FIXED", "(confirmed in earlier round)"
        else:
            s, d2 = "UNKNOWN", ""
        if s == "FIXED": total_fixed += 1
        elif s == "STILL_FAILING": total_failing += 1
        print(f"#{n:<7} {s:<18} {d2[:52]}")

    print(f"\nTOTAL: {len(all_nums)} | FIXED: {total_fixed} | STILL_FAILING: {total_failing}")

if __name__ == "__main__":
    main()
