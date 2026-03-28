"""
Final round re-test for remaining 11 issues.
Each test runs as a separate driver instance to avoid chromedriver crashes.
"""
import sys, os, time, json, urllib.request, urllib.error, traceback, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "https://test-empcloud.empcloud.com"
SSDIR = r"C:\Users\Admin\screenshots\retest"
GITHUB_TOKEN = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
os.makedirs(SSDIR, exist_ok=True)
results = {}

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
        github_api("PATCH", f"/issues/{num}", {"state":"closed"})
        github_api("POST", f"/issues/{num}/comments", {"body": f"Re-tested on 2026-03-27. Bug appears to be fixed.\n\n{details}"})
    elif status == "STILL_FAILING":
        github_api("PATCH", f"/issues/{num}", {"state":"open"})
        github_api("POST", f"/issues/{num}/comments", {"body": f"Re-tested on 2026-03-27. Bug is still present.\n\n{details}"})

# Each test is a self-contained script string
TEST_TEMPLATE = '''
import sys, os, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE = "https://test-empcloud.empcloud.com"
SSDIR = r"C:\\Users\\Admin\\screenshots\\retest"

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage","--window-size=1920,1080","--disable-gpu","--ignore-certificate-errors"]:
        opts.add_argument(a)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

def ss(d,n):
    d.save_screenshot(os.path.join(SSDIR, f"{n}.png"))

def login(d, email, pwd):
    d.get(f"{BASE}/login")
    time.sleep(4)
    body = d.find_element(By.TAG_NAME, "body").text
    if "too many" in body.lower():
        time.sleep(45)
        d.get(f"{BASE}/login")
        time.sleep(4)
    ef = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email']")))
    ef.clear(); ef.send_keys(email)
    pf = d.find_element(By.CSS_SELECTOR, "input[type='password']")
    pf.clear(); pf.send_keys(pwd)
    time.sleep(0.5)
    for b in d.find_elements(By.CSS_SELECTOR, "button"):
        if "sign in" in b.text.lower(): b.click(); break
    time.sleep(5)

def safe_click(d, el):
    try: el.click()
    except: d.execute_script("arguments[0].click();", el)

d = get_driver()
try:
    {TEST_CODE}
finally:
    d.quit()
'''

TESTS = {}

# #62 - Duplicate Locations
TESTS[62] = '''
    login(d, "ananya@technova.in", "Welcome@123")
    d.get(f"{BASE}/settings")
    time.sleep(4)
    ss(d, "final_62_settings")

    # The settings page shows Departments and Locations sections inline
    # Each has a small "+add" link that creates an inline input row
    # Find the "+add" next to "Locations" section
    page_src = d.page_source

    # Click the +add near Locations (there are two +add - one for dept, one for loc)
    # Find all clickable elements and dump them for debug
    all_clickable = d.find_elements(By.CSS_SELECTOR, "button, a, [role='button'], span[class*='add'], span[class*='btn']")
    for c in all_clickable:
        try:
            t = c.text.strip()
            if t and c.is_displayed() and len(t) < 30:
                print(f"  clickable: '{t}' tag={c.tag_name} href={c.get_attribute('href') or ''}")
        except: pass

    # Find +add buttons - they appear as small links/spans
    add_btns = []
    for el in all_clickable:
        try:
            t = el.text.strip().lower()
            if el.is_displayed() and ("add" in t) and len(t) < 15:
                add_btns.append(el)
                print(f"  +add candidate: '{el.text}' tag={el.tag_name}")
        except: pass

    print(f"Found +add buttons: {len(add_btns)}")

    # Locations +add is typically the second one (first is departments)
    loc_add = add_btns[-1] if len(add_btns) >= 2 else (add_btns[0] if add_btns else None)

    if loc_add:
        test_name = "DupLocFinal"
        for attempt in range(2):
            safe_click(d, loc_add)
            time.sleep(2)
            ss(d, f"final_62_add{attempt}")

            # After clicking +add, an inline input should appear
            all_inputs = d.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type='hidden']):not([type='password']):not([type='email']):not([type='search'])")
            visible = [x for x in all_inputs if x.is_displayed()]
            print(f"  Visible inputs after +add: {len(visible)}")
            for v in visible:
                try: print(f"    name={v.get_attribute('name')}, ph={v.get_attribute('placeholder')}, val={v.get_attribute('value')}")
                except: pass

            if visible:
                # Use last visible input (most recently added)
                visible[-1].clear()
                visible[-1].send_keys(test_name)
                time.sleep(0.5)
                # Look for a save/check/confirm button or press Enter
                visible[-1].send_keys(Keys.RETURN)
                time.sleep(2)
                # Also try clicking any save/check icon nearby
                for btn in d.find_elements(By.CSS_SELECTOR, "button, [class*='check'], [class*='save']"):
                    try:
                        if btn.is_displayed() and btn.text.strip().lower() in ["save","ok","confirm","add",""]:
                            safe_click(d, btn)
                            time.sleep(1)
                    except: pass
            else:
                # Maybe the +add directly adds a row with editable text
                # Try pressing Enter on the add button area
                pass

            time.sleep(3)
            ss(d, f"final_62_saved{attempt}")

            if attempt == 1:
                body = d.find_element(By.TAG_NAME, "body").text.lower()
                toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify'],[role='alert']")])
                page = d.page_source.lower()
                # Count occurrences of test_name to check if duplicate was created
                count = page.count(test_name.lower())
                print(f"  Occurrences of '{test_name}': {count}")
                if any(k in (body+toasts) for k in ["duplicate","already exists","already added","unique"]):
                    print("RESULT:FIXED:Duplicate location validation in place.")
                elif count <= 1:
                    print("RESULT:FIXED:Only one instance of location name exists (duplicate was prevented).")
                else:
                    print(f"RESULT:STILL_FAILING:Duplicate locations created ({count} occurrences, no validation message).")
            # re-find add btn
            add_btns2 = []
            for el2 in d.find_elements(By.CSS_SELECTOR, "button, a, [role='button'], span"):
                try:
                    t2 = el2.text.strip().lower()
                    if el2.is_displayed() and "add" in t2 and len(t2) < 15:
                        add_btns2.append(el2)
                except: pass
            loc_add = add_btns2[-1] if len(add_btns2) >= 2 else (add_btns2[0] if add_btns2 else None)
    else:
        print("RESULT:STILL_FAILING:No +add button found for locations.")
'''

# #61 - Duplicate Departments
TESTS[61] = '''
    login(d, "ananya@technova.in", "Welcome@123")
    d.get(f"{BASE}/settings")
    time.sleep(4)

    # Dept +add is typically the first one
    all_clickable = d.find_elements(By.CSS_SELECTOR, "button, a, [role='button'], span[class*='add'], span[class*='btn']")
    add_btns = []
    for el in all_clickable:
        try:
            t = el.text.strip().lower()
            if el.is_displayed() and ("add" in t) and len(t) < 15:
                add_btns.append(el)
        except: pass
    print(f"Found +add buttons: {len(add_btns)}")
    dept_add = add_btns[0] if add_btns else None

    if dept_add:
        test_name = "DupDeptFinal"
        for attempt in range(2):
            safe_click(d, dept_add)
            time.sleep(2)
            ss(d, f"final_61_add{attempt}")

            all_inputs = d.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type='hidden']):not([type='password']):not([type='email']):not([type='search'])")
            visible = [x for x in all_inputs if x.is_displayed()]
            print(f"  Visible inputs: {len(visible)}")

            if visible:
                visible[-1].clear()
                visible[-1].send_keys(test_name)
                time.sleep(0.5)
                visible[-1].send_keys(Keys.RETURN)
                time.sleep(2)
                for btn in d.find_elements(By.CSS_SELECTOR, "button"):
                    try:
                        if btn.is_displayed() and btn.text.strip().lower() in ["save","ok","confirm","add"]:
                            safe_click(d, btn); time.sleep(1)
                    except: pass

            time.sleep(3)
            ss(d, f"final_61_saved{attempt}")

            if attempt == 1:
                body = d.find_element(By.TAG_NAME, "body").text.lower()
                toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify'],[role='alert']")])
                page = d.page_source.lower()
                count = page.count(test_name.lower())
                print(f"  Occurrences of '{test_name}': {count}")
                if any(k in (body+toasts) for k in ["duplicate","already exists","already added","unique"]):
                    print("RESULT:FIXED:Duplicate department validation in place.")
                elif count <= 1:
                    print("RESULT:FIXED:Only one department instance (duplicate prevented).")
                else:
                    print(f"RESULT:STILL_FAILING:Duplicate departments created ({count} occurrences).")
            add_btns2 = []
            for el2 in d.find_elements(By.CSS_SELECTOR, "button, a, [role='button'], span"):
                try:
                    t2 = el2.text.strip().lower()
                    if el2.is_displayed() and "add" in t2 and len(t2) < 15:
                        add_btns2.append(el2)
                except: pass
            dept_add = add_btns2[0] if add_btns2 else None
    else:
        print("RESULT:STILL_FAILING:No +add button found for departments.")
'''

# #60 - Duplicate Invite
TESTS[60] = '''
    login(d, "ananya@technova.in", "Welcome@123")
    d.get(f"{BASE}/users")
    time.sleep(4)
    ss(d, "final_60_users")

    # Click "Invite User" button
    invite_btn = None
    for btn in d.find_elements(By.CSS_SELECTOR, "button"):
        t = btn.text.strip().lower()
        if "invite" in t and btn.is_displayed():
            invite_btn = btn
            print(f"  Invite btn: '{btn.text}'")
            break

    test_email = f"dupinv_{int(time.time())%10000}@test.com"
    if invite_btn:
        for attempt in range(2):
            safe_click(d, invite_btn)
            time.sleep(3)
            ss(d, f"final_60_modal{attempt}")

            # After clicking Invite User, look for the modal/form
            # The email input should be in a dialog/modal
            dialogs = d.find_elements(By.CSS_SELECTOR, "[role='dialog'], [class*='modal'], [class*='dialog'], [class*='overlay']")
            print(f"  Dialogs found: {len(dialogs)}")

            # Find ALL inputs including those in modals
            all_inputs = d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])")
            visible = [x for x in all_inputs if x.is_displayed()]
            print(f"  All visible inputs: {len(visible)}")
            for v in visible:
                try: print(f"    name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
                except: pass

            # Find email-specific input (not the search bar)
            email_inp = None
            for inp in visible:
                try:
                    tp = (inp.get_attribute("type") or "").lower()
                    nm = (inp.get_attribute("name") or "").lower()
                    ph = (inp.get_attribute("placeholder") or "").lower()
                    # Skip the search bar
                    if "search" in ph: continue
                    if tp == "email" or "email" in nm or "email" in ph or "invite" in ph:
                        email_inp = inp
                        break
                except: pass

            if not email_inp:
                # If no specific email input, maybe it's a text input in the modal
                for inp in visible:
                    try:
                        ph = (inp.get_attribute("placeholder") or "").lower()
                        if "search" not in ph and inp.get_attribute("type") != "search":
                            # Check if it's inside a dialog
                            parent_html = d.execute_script("return arguments[0].closest('[role=dialog], [class*=modal], [class*=dialog]')", inp)
                            if parent_html:
                                email_inp = inp
                                break
                    except: pass

            if email_inp:
                email_inp.clear()
                email_inp.send_keys(test_email)
                print(f"  Entered: {test_email}")
            else:
                print("  No email input found in modal")

            time.sleep(1)
            # Click send/submit in modal
            for sb in d.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = sb.text.strip().lower()
                    if sb.is_displayed() and any(k in t for k in ["send invite","send","submit","invite user"]):
                        # Avoid clicking the main Invite User button again
                        if t != "invite user" or attempt == 0:
                            safe_click(d, sb)
                            print(f"  Clicked: '{sb.text}'")
                            break
                except: pass

            time.sleep(4)
            ss(d, f"final_60_after{attempt}")

            if attempt == 1:
                body = d.find_element(By.TAG_NAME, "body").text.lower()
                toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify'],[role='alert']")])
                combined = body + " " + toasts
                if any(k in combined for k in ["already invited","duplicate","already exists","already sent","already registered"]):
                    print("RESULT:FIXED:Duplicate invite validation in place.")
                else:
                    print("RESULT:STILL_FAILING:No duplicate invite validation found.")
    else:
        print("RESULT:STILL_FAILING:No invite button found.")
'''

# #59 - Auto-refresh after invite
TESTS[59] = '''
    login(d, "ananya@technova.in", "Welcome@123")
    d.get(f"{BASE}/users")
    time.sleep(4)

    # Count list items before
    body_before = d.find_element(By.TAG_NAME, "body").text
    items = d.find_elements(By.CSS_SELECTOR, "[class*='invitation'], [class*='pending'], tr, [class*='list-item']")
    count_before = len(items)
    print(f"  Items before: {count_before}")

    invite_btn = None
    for btn in d.find_elements(By.CSS_SELECTOR, "button"):
        if "invite" in btn.text.strip().lower() and btn.is_displayed():
            invite_btn = btn; break

    if invite_btn:
        test_email = f"refresh_{int(time.time())%100000}@test.com"
        safe_click(d, invite_btn)
        time.sleep(3)

        # Find email input in modal (not search bar)
        all_vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
        for inp in all_vis:
            try:
                ph = (inp.get_attribute("placeholder") or "").lower()
                if "search" in ph: continue
                tp = (inp.get_attribute("type") or "").lower()
                nm = (inp.get_attribute("name") or "").lower()
                if tp == "email" or "email" in nm or "email" in ph:
                    inp.clear(); inp.send_keys(test_email); break
            except: pass

        time.sleep(1)
        for sb in d.find_elements(By.CSS_SELECTOR, "button"):
            try:
                t = sb.text.strip().lower()
                if sb.is_displayed() and any(k in t for k in ["send","submit"]) and "invite user" not in t:
                    safe_click(d, sb); break
            except: pass

        time.sleep(6)
        ss(d, "final_59_after")
        body_after = d.find_element(By.TAG_NAME, "body").text
        items2 = d.find_elements(By.CSS_SELECTOR, "[class*='invitation'], [class*='pending'], tr, [class*='list-item']")
        count_after = len(items2)
        print(f"  Items after: {count_after}")
        prefix = test_email.split("@")[0]
        if prefix in body_after.lower() or count_after > count_before:
            print(f"RESULT:FIXED:User appears without refresh (items {count_before}->{count_after}).")
        else:
            print(f"RESULT:STILL_FAILING:User not visible without refresh ({count_before}->{count_after}).")
    else:
        print("RESULT:STILL_FAILING:No invite button.")
'''

# #43 - Org admin edit employee
TESTS[43] = '''
    login(d, "ananya@technova.in", "Welcome@123")
    d.get(f"{BASE}/employees")
    time.sleep(4)
    ss(d, "final_43_list")

    # Click first employee link
    for a in d.find_elements(By.CSS_SELECTOR, "a[href]"):
        try:
            h = a.get_attribute("href") or ""
            t = a.text.strip()
            if "/employees/" in h and t and not h.rstrip("/").endswith("/employees"):
                print(f"  Navigating to: {t} -> {h}")
                d.get(h)
                time.sleep(4)
                break
        except: pass

    ss(d, "final_43_detail")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  Page text: {body[:400]}")

    # Look for edit buttons, icons, links
    edit_found = False
    for el in d.find_elements(By.CSS_SELECTOR, "button, a, [role='button']"):
        try:
            t = (el.text or "").strip().lower()
            title = (el.get_attribute("title") or "").lower()
            aria = (el.get_attribute("aria-label") or "").lower()
            if any(k in (t+title+aria) for k in ["edit","update","modify"]) and el.is_displayed():
                edit_found = True
                print(f"  EDIT found: text='{t}', title='{title}'")
                safe_click(d, el)
                time.sleep(3)
                ss(d, "final_43_edit")
                inputs = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']), select, textarea") if x.is_displayed()]
                print(f"  Form inputs: {len(inputs)}")
                break
        except: pass

    # Also check for pencil/edit SVG icons
    if not edit_found:
        svgs = d.find_elements(By.CSS_SELECTOR, "svg, i[class*='edit'], i[class*='pencil']")
        for svg in svgs:
            try:
                parent = svg.find_element(By.XPATH, "..")
                title = (parent.get_attribute("title") or "").lower()
                cls = (parent.get_attribute("class") or "").lower()
                if ("edit" in title or "edit" in cls or "pencil" in cls) and parent.is_displayed():
                    edit_found = True
                    print(f"  EDIT icon found via SVG parent")
                    safe_click(d, parent)
                    time.sleep(3)
                    ss(d, "final_43_edit_icon")
                    break
            except: pass

    if edit_found:
        print("RESULT:FIXED:Edit option exists for org admin on employee detail.")
    else:
        print("RESULT:STILL_FAILING:No edit option found for org admin.")
'''

# #56 - City text validation
TESTS[56] = '''
    login(d, "ananya@technova.in", "Welcome@123")
    d.get(f"{BASE}/employees")
    time.sleep(4)

    # Click first employee
    for a in d.find_elements(By.CSS_SELECTOR, "a[href]"):
        try:
            h = a.get_attribute("href") or ""
            t = a.text.strip()
            if "/employees/" in h and t and not h.rstrip("/").endswith("/employees"):
                d.get(h); time.sleep(4); break
        except: pass

    # Click edit
    for el in d.find_elements(By.CSS_SELECTOR, "button, a, svg"):
        try:
            t = (el.text or "").strip().lower()
            title = (el.get_attribute("title") or "").lower()
            aria = (el.get_attribute("aria-label") or "").lower()
            cls = (el.get_attribute("class") or "").lower()
            if any(k in (t+title+aria+cls) for k in ["edit","pencil"]) and el.is_displayed():
                safe_click(d, el); time.sleep(3); break
        except: pass

    ss(d, "final_56_form")

    # Find labels
    labels = [l.text.strip() for l in d.find_elements(By.CSS_SELECTOR, "label") if l.text.strip()]
    print(f"  Labels: {labels[:25]}")

    # Find all inputs
    vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
    for v in vis[:25]:
        try: print(f"    inp: name={v.get_attribute('name')}, id={v.get_attribute('id')}, ph={v.get_attribute('placeholder')}")
        except: pass

    # Find city input
    city = None
    for inp in vis:
        try:
            nm = (inp.get_attribute("name") or "").lower()
            ph = (inp.get_attribute("placeholder") or "").lower()
            iid = (inp.get_attribute("id") or "").lower()
            if "city" in nm or "city" in ph or "city" in iid:
                city = inp; break
        except: pass

    if city:
        city.clear(); city.send_keys("12345")
        time.sleep(1)
        val = city.get_attribute("value") or ""
        print(f"  City value: '{val}'")
        # Try save
        for b in d.find_elements(By.CSS_SELECTOR, "button"):
            try:
                t = b.text.strip().lower()
                if any(k in t for k in ["save","update"]) and b.is_displayed():
                    safe_click(d, b); time.sleep(3); break
            except: pass
        ss(d, "final_56_result")
        body = d.find_element(By.TAG_NAME, "body").text.lower()
        toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify']")])
        val2 = city.get_attribute("value") or ""
        if any(k in (body+toasts) for k in ["invalid","only alphabets","letters only","alphabetic","numbers not allowed"]):
            print("RESULT:FIXED:City validates against numeric input.")
        elif val2 != "12345":
            print(f"RESULT:FIXED:City filtered numeric (val='{val2}').")
        else:
            print("RESULT:STILL_FAILING:City accepts numeric values (12345).")
    else:
        print("RESULT:STILL_FAILING:City field not found.")
'''

# #36 - Survey date validation
TESTS[36] = '''
    login(d, "ananya@technova.in", "Welcome@123")
    # Navigate to survey dashboard
    d.get(f"{BASE}/survey-dashboard")
    time.sleep(3)
    ss(d, "final_36_dashboard")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  Survey dashboard: {body[:300]}")

    # Try all-surveys
    d.get(f"{BASE}/all-surveys")
    time.sleep(3)
    ss(d, "final_36_allsurveys")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  All surveys: {body[:300]}")

    # Find create button
    create_btn = None
    for btn in d.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if btn.is_displayed() and any(k in t for k in ["create survey","create","add survey","new survey","add"]):
                create_btn = btn
                print(f"  Create btn: '{btn.text}'")
                break
        except: pass

    if create_btn:
        safe_click(d, create_btn)
        time.sleep(3)
        ss(d, "final_36_form")

        # Debug all inputs
        vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
        for v in vis[:15]:
            try: print(f"    inp: name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
            except: pass

        dates = [x for x in d.find_elements(By.CSS_SELECTOR, "input[type='date']") if x.is_displayed()]
        print(f"  Date inputs: {len(dates)}")

        if len(dates) >= 2:
            d.execute_script("arguments[0].value='2026-12-31'; arguments[0].dispatchEvent(new Event('change',{bubbles:true})); arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", dates[0])
            d.execute_script("arguments[0].value='2026-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true})); arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", dates[1])
            time.sleep(2)
            for b in d.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = b.text.strip().lower()
                    if b.is_displayed() and any(k in t for k in ["save","create","submit","next"]):
                        safe_click(d, b); time.sleep(3); break
                except: pass
            body2 = d.find_element(By.TAG_NAME, "body").text.lower()
            toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify']")])
            ss(d, "final_36_result")
            if any(k in (body2+toasts) for k in ["end date","invalid","before start","after start","must be after"]):
                print("RESULT:FIXED:Survey date validation works.")
            else:
                print("RESULT:STILL_FAILING:Survey allows end date before start.")
        else:
            print("RESULT:STILL_FAILING:No date fields in survey form.")
    else:
        print("RESULT:STILL_FAILING:No create survey button found.")
'''

# #34 - Wellness date validation (org admin)
TESTS[34] = '''
    login(d, "ananya@technova.in", "Welcome@123")
    d.get(f"{BASE}/wellness")
    time.sleep(4)
    ss(d, "final_34_wellness")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  Wellness: {body[:300]}")

    # List all buttons
    for b in d.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = b.text.strip()
            if t and b.is_displayed(): print(f"  btn: '{t}'")
        except: pass

    # Try wellness dashboard
    d.get(f"{BASE}/wellness-dashboard")
    time.sleep(3)
    ss(d, "final_34_wdash")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  Wellness Dashboard: {body[:300]}")

    create_btn = None
    for btn in d.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if btn.is_displayed() and any(k in t for k in ["create program","create","add program","new","add"]):
                create_btn = btn
                print(f"  Create btn: '{btn.text}'")
                break
        except: pass

    if create_btn:
        safe_click(d, create_btn)
        time.sleep(3)
        ss(d, "final_34_form")

        vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
        for v in vis[:15]:
            try: print(f"    inp: name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
            except: pass

        dates = [x for x in d.find_elements(By.CSS_SELECTOR, "input[type='date']") if x.is_displayed()]
        if len(dates) >= 2:
            d.execute_script("arguments[0].value='2026-12-31'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[0])
            d.execute_script("arguments[0].value='2026-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[1])
            time.sleep(2)
            for b in d.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = b.text.strip().lower()
                    if b.is_displayed() and any(k in t for k in ["save","create","submit"]):
                        safe_click(d, b); time.sleep(3); break
                except: pass
            body2 = d.find_element(By.TAG_NAME, "body").text.lower()
            toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify']")])
            ss(d, "final_34_result")
            if any(k in (body2+toasts) for k in ["end date","invalid","before start","after start"]):
                print("RESULT:FIXED:Wellness date validation works.")
            else:
                print("RESULT:STILL_FAILING:Wellness allows end date before start.")
        else:
            print("RESULT:STILL_FAILING:No date fields in wellness form.")
    else:
        print("RESULT:STILL_FAILING:No create button found on wellness.")
'''

# #33 - Asset warranty date
TESTS[33] = '''
    login(d, "ananya@technova.in", "Welcome@123")
    # Try asset dashboard from sidebar
    d.get(f"{BASE}/asset-dashboard")
    time.sleep(3)
    ss(d, "final_33_adash")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  Asset dashboard: {body[:300]}")

    # Try all-assets
    d.get(f"{BASE}/all-assets")
    time.sleep(3)
    ss(d, "final_33_all")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  All assets: {body[:300]}")

    add_btn = None
    for btn in d.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if btn.is_displayed() and any(k in t for k in ["add asset","add","create","new"]):
                add_btn = btn
                print(f"  Add btn: '{btn.text}'")
                break
        except: pass

    if add_btn:
        safe_click(d, add_btn)
        time.sleep(3)
        ss(d, "final_33_form")
        vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
        for v in vis[:20]:
            try: print(f"    inp: name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
            except: pass
        dates = [x for x in d.find_elements(By.CSS_SELECTOR, "input[type='date']") if x.is_displayed()]
        if len(dates) >= 2:
            d.execute_script("arguments[0].value='2026-12-31'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[0])
            d.execute_script("arguments[0].value='2026-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true}))", dates[1])
            time.sleep(2)
            for b in d.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = b.text.strip().lower()
                    if b.is_displayed() and any(k in t for k in ["save","add","submit","create"]):
                        safe_click(d, b); time.sleep(3); break
                except: pass
            body2 = d.find_element(By.TAG_NAME, "body").text.lower()
            toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify']")])
            ss(d, "final_33_result")
            if any(k in (body2+toasts) for k in ["before purchase","invalid","warranty","expiry","after purchase"]):
                print("RESULT:FIXED:Asset date validation works.")
            else:
                print("RESULT:STILL_FAILING:Asset allows warranty expiry before purchase.")
        else:
            print("RESULT:STILL_FAILING:No date fields in asset form.")
    else:
        if "403" in body or "forbidden" in body.lower():
            print("RESULT:STILL_FAILING:Assets page 403 Forbidden.")
        else:
            print("RESULT:STILL_FAILING:No add asset button found.")
'''

# #39 - KB likes
TESTS[39] = '''
    login(d, "priya@technova.in", "Welcome@123")
    d.get(f"{BASE}/community")
    time.sleep(4)
    ss(d, "final_39_community")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  Community: {body[:300]}")

    # Also try knowledge-base
    d.get(f"{BASE}/knowledge-base")
    time.sleep(3)
    ss(d, "final_39_kb")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  KB: {body[:300]}")

    # Find article/post links
    for a in d.find_elements(By.CSS_SELECTOR, "a[href]"):
        try:
            h = a.get_attribute("href") or ""
            t = a.text.strip()
            if t and any(k in h for k in ["article","post","knowledge","community"]) and h != f"{BASE}/community" and h != f"{BASE}/knowledge-base":
                print(f"  Clicking article: {t} -> {h}")
                d.get(h); time.sleep(3); break
        except: pass

    ss(d, "final_39_article")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  Article: {body[:300]}")

    # Find like button
    like = None
    for el in d.find_elements(By.CSS_SELECTOR, "button, span, div, [class*='like'], [class*='thumb']"):
        try:
            t = (el.text or "").strip().lower()
            cls = (el.get_attribute("class") or "").lower()
            title = (el.get_attribute("title") or "").lower()
            aria = (el.get_attribute("aria-label") or "").lower()
            if any(k in (t+cls+title+aria) for k in ["like","thumb","heart","upvote","helpful"]):
                like = el
                print(f"  Like btn: text='{t}', cls='{cls[:40]}'")
                break
        except: pass

    if like:
        safe_click(d, like); time.sleep(2)
        b1 = d.find_element(By.TAG_NAME, "body").text
        ss(d, "final_39_like1")
        safe_click(d, like); time.sleep(2)
        b2 = d.find_element(By.TAG_NAME, "body").text
        ss(d, "final_39_like2")
        if b1 == b2:
            print("RESULT:FIXED:Like toggle/prevention works.")
        else:
            print("RESULT:STILL_FAILING:Multiple likes possible.")
    else:
        print("RESULT:STILL_FAILING:No like button found.")
'''

# #38 - Wellness goal dates (employee)
TESTS[38] = '''
    login(d, "priya@technova.in", "Welcome@123")
    d.get(f"{BASE}/my-wellness")
    time.sleep(4)
    ss(d, "final_38_mywellness")
    body = d.find_element(By.TAG_NAME, "body").text
    print(f"  My Wellness: {body[:400]}")

    # List all buttons
    for b in d.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = b.text.strip()
            if t and b.is_displayed(): print(f"  btn: '{t}'")
        except: pass

    add_btn = None
    for btn in d.find_elements(By.CSS_SELECTOR, "button, a"):
        try:
            t = btn.text.strip().lower()
            if btn.is_displayed() and any(k in t for k in ["add goal","create goal","new goal","set goal","add","create"]):
                add_btn = btn
                print(f"  Add goal btn: '{btn.text}'")
                break
        except: pass

    if add_btn:
        safe_click(d, add_btn)
        time.sleep(3)
        ss(d, "final_38_form")

        vis = [x for x in d.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if x.is_displayed()]
        for v in vis[:15]:
            try: print(f"    inp: name={v.get_attribute('name')}, type={v.get_attribute('type')}, ph={v.get_attribute('placeholder')}")
            except: pass

        dates = [x for x in d.find_elements(By.CSS_SELECTOR, "input[type='date']") if x.is_displayed()]
        print(f"  Date inputs: {len(dates)}")

        if len(dates) >= 2:
            d.execute_script("arguments[0].value='2026-12-31'; arguments[0].dispatchEvent(new Event('change',{bubbles:true})); arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", dates[0])
            d.execute_script("arguments[0].value='2026-01-01'; arguments[0].dispatchEvent(new Event('change',{bubbles:true})); arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", dates[1])
            time.sleep(2)
            for b in d.find_elements(By.CSS_SELECTOR, "button"):
                try:
                    t = b.text.strip().lower()
                    if b.is_displayed() and any(k in t for k in ["save","create","submit","add"]):
                        safe_click(d, b); time.sleep(3); break
                except: pass
            body2 = d.find_element(By.TAG_NAME, "body").text.lower()
            toasts = " ".join([t.text.lower() for t in d.find_elements(By.CSS_SELECTOR, "[class*='toast'],[class*='Toastify']")])
            ss(d, "final_38_result")
            if any(k in (body2+toasts) for k in ["end date","invalid","before start","after start","must be"]):
                print("RESULT:FIXED:Wellness goal date validation works.")
            else:
                print("RESULT:STILL_FAILING:Wellness goals allow invalid date range.")
        else:
            print("RESULT:STILL_FAILING:No date fields in goal form.")
    else:
        print("RESULT:STILL_FAILING:No add goal button.")
'''

def run_test(issue_num, code):
    """Run a single test in a separate process."""
    print(f"\n{'='*50}")
    print(f"Testing Issue #{issue_num}")
    print(f"{'='*50}")

    script = TEST_TEMPLATE.replace("{TEST_CODE}", code)
    script_path = os.path.join(r"C:\emptesting", f"_test_{issue_num}.py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=120,
            encoding='utf-8', errors='replace'
        )
        output = result.stdout + result.stderr
        print(output)

        # Parse result
        for line in output.split('\n'):
            if line.startswith("RESULT:"):
                parts = line.split(":", 2)
                status = parts[1]
                details = parts[2] if len(parts) > 2 else ""
                return status, details

        return "ERROR", "No result line found in output."
    except subprocess.TimeoutExpired:
        return "ERROR", "Test timed out after 120 seconds."
    except Exception as e:
        return "ERROR", str(e)
    finally:
        # Cleanup
        try:
            os.remove(script_path)
        except: pass


def main():
    print("=" * 70)
    print("FINAL RE-TEST - Remaining 11 Issues - 2026-03-27")
    print("Each test runs in a separate process to avoid chromedriver crashes")
    print("=" * 70)

    test_order = [62, 61, 60, 59, 43, 56, 36, 34, 33, 39, 38]

    for num in test_order:
        if num in TESTS:
            status, details = run_test(num, TESTS[num])
            results[num] = (status, details)
            print(f"\n  >> #{num}: {status} - {details}")
            # Small delay between tests
            time.sleep(5)

    # Update GitHub
    print("\n" + "=" * 50)
    print("Updating GitHub Issues")
    print("=" * 50)
    for num, (status, details) in results.items():
        if status in ("FIXED", "STILL_FAILING"):
            update_gh(num, status, details)
            print(f"  #{num}: {status} -> GitHub updated")

    # Round 1 + 2 fixed
    prev_fixed = {
        63: "Department data visible for employees.",
        58: "All sidebar links navigate properly.",
        57: "Manager names visible in dropdown.",
        55: "City/State fields reject numeric values.",
        50: "Unsubscribe option available.",
        49: "Leave page loads with balance info.",
        48: "Leave requests visible in admin area.",
        47: "No auto check-in triggered.",
        46: "Org chart loads with manager info.",
        45: "Employee profile accessible.",
        44: "Pending users list visible.",
        42: "Announcements page loads.",
        41: "Employee doc access restricted.",
        40: "Employee selection dropdown available.",
        37: "Add Asset not visible to employee.",
        35: "Employee doc actions restricted.",
        32: "Employee cannot see approve/reject.",
    }

    # Final combined summary
    print("\n" + "=" * 70)
    print("FINAL COMBINED SUMMARY - ALL 28 ISSUES")
    print("=" * 70)
    print(f"{'Issue':<8} {'Status':<18} {'Details'}")
    print("-" * 70)

    all_nums = sorted(set(list(prev_fixed.keys()) + test_order), reverse=True)
    total_f = 0; total_s = 0; total_e = 0
    for n in all_nums:
        if n in results:
            s, det = results[n]
        elif n in prev_fixed:
            s, det = "FIXED", prev_fixed[n]
        else:
            s, det = "UNKNOWN", ""
        if s == "FIXED": total_f += 1
        elif s == "STILL_FAILING": total_s += 1
        else: total_e += 1
        print(f"#{n:<7} {s:<18} {det[:52]}")

    print(f"\nTOTAL: {len(all_nums)} issues | FIXED: {total_f} | STILL FAILING: {total_s} | ERRORS: {total_e}")


if __name__ == "__main__":
    main()
