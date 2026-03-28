"""
EMP Cloud HRMS - Critical Data Flow E2E Tests
Tests data consistency across ALL modules from inside the dashboard.
Saves screenshots locally, uploads to GitHub at the end.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import functools
print = functools.partial(print, flush=True)

import time, json, base64, urllib.request, traceback, os, re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = f"{BASE_URL}/api/v1"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
SS_DIR = "C:\\emptesting\\screenshots"
os.makedirs(SS_DIR, exist_ok=True)

REPORT = {"flows_tested": 0, "flows_passed": 0, "flows_failed": 0,
          "bugs": [], "screenshots": {}, "details": {}}

CHROMEDRIVER_PATH = None
def get_driver():
    global CHROMEDRIVER_PATH
    opts = webdriver.ChromeOptions()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage","--window-size=1920,1080",
              "--disable-gpu","--ignore-certificate-errors","--disable-extensions"]:
        opts.add_argument(a)
    if not CHROMEDRIVER_PATH:
        CHROMEDRIVER_PATH = ChromeDriverManager().install()
    d = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=opts)
    d.set_page_load_timeout(60)
    d.implicitly_wait(3)
    return d

def save_ss(driver, name):
    """Save screenshot locally only. Returns local path."""
    p = os.path.join(SS_DIR, f"df_{name}_{int(time.time())}.png")
    try:
        driver.save_screenshot(p)
        REPORT["screenshots"][name] = p
        return p
    except:
        return None

def upload_screenshots_to_github():
    """Batch upload all screenshots at end."""
    print("\n--- Uploading screenshots to GitHub ---")
    urls = {}
    for name, path in REPORT["screenshots"].items():
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'rb') as f:
                content = base64.b64encode(f.read()).decode()
            fname = os.path.basename(path)
            data = json.dumps({"message": f"Screenshot: {name}", "content": content}).encode()
            req = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/{fname}",
                data=data, method='PUT',
                headers={"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"})
            resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
            url = resp["content"]["download_url"]
            urls[name] = url
            print(f"  Uploaded: {name}")
        except Exception as e:
            print(f"  Upload failed {name}: {str(e)[:60]}")
            urls[name] = None
    return urls

def file_bug(title, body, severity="medium"):
    labels = ["bug", "data-flow"]
    if severity in ("high","critical"):
        labels.append(f"priority-{severity}")
    try:
        data = json.dumps({"title": f"[DATA FLOW] {title}", "body": body, "labels": labels}).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            data=data, method='POST',
            headers={"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        url = resp.get("html_url", "?")
        print(f"  [BUG] {title} -> {url}")
        REPORT["bugs"].append({"title": title, "severity": severity, "url": url})
        return url
    except Exception as e:
        print(f"  [BUG FAIL] {e}")
        REPORT["bugs"].append({"title": title, "severity": severity, "url": "FAILED"})
        return None

def api_req(endpoint, token=None, method='GET', data=None):
    url = f"{API_URL}/{endpoint}" if not endpoint.startswith("http") else endpoint
    headers = {"Accept":"application/json","Content-Type":"application/json",
               "User-Agent":"EmpCloudTest/1.0","Origin":BASE_URL}
    if token: headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code}
    except Exception as e:
        return {"error": str(e)}

def api_login(email, password):
    r = api_req("auth/login", data={"email": email, "password": password}, method='POST')
    if "error" not in r:
        try: return r["data"]["tokens"]["access_token"]
        except: pass
    return None

def login(driver, email, password):
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    try:
        try:
            driver.find_element(By.XPATH, "//*[contains(text(),'Sign in')]").click()
            time.sleep(0.5)
        except: pass
        ef = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
        ef.clear(); ef.send_keys(email)
        pf = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pf.clear(); pf.send_keys(password)
        time.sleep(0.3)
        btns = driver.find_elements(By.CSS_SELECTOR, "button")
        btn = next((b for b in btns if "sign in" in b.text.lower()), None)
        if not btn: btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(5)
        WebDriverWait(driver, 20).until(lambda d: "/login" not in d.current_url)
        print(f"  [LOGIN] {email} OK")
        return True
    except Exception as e:
        print(f"  [LOGIN FAIL] {email}: {e}")
        return False

def go(d, path, w=4):
    try: d.get(f"{BASE_URL}{path}" if path.startswith("/") else path)
    except: pass
    time.sleep(w)

def body(d):
    try: return d.find_element(By.TAG_NAME, "body").text
    except: return ""

def wait_body(d, n=6):
    for _ in range(n):
        time.sleep(1)
        t = body(d)
        if len(t) > 100: return t
    return body(d)

def rows(d, css="table tbody tr", t=5):
    try:
        WebDriverWait(d, t).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        return d.find_elements(By.CSS_SELECTOR, css)
    except:
        return []


# ═══════════════════════════════════════════════════════════════════════
# FLOWS
# ═══════════════════════════════════════════════════════════════════════

def flow1(d):
    """Employee cross-module consistency."""
    print("\n=== FLOW 1: Employee Cross-Module ===")
    R = {"status": "STARTED", "checks": {}}
    go(d, "/employees", 5)
    text = wait_body(d)
    save_ss(d, "f1_employees")

    # Extract employee name from table
    emp = None
    trs = rows(d)
    for tr in trs[:10]:
        tds = tr.find_elements(By.TAG_NAME, "td")
        if tds:
            ct = tds[0].text.strip()
            # Get lines that look like names (>3 chars, contain space)
            for line in ct.split("\n"):
                line = line.strip()
                if len(line) > 4 and " " in line and "@" not in line:
                    emp = line
                    break
            if emp: break

    # Fallback: look for known names in page text
    if not emp:
        for n in ["Aditya Joshi", "Aman Gupta", "Arjun Patel", "Divya Menon",
                   "Jay Sharma", "Jane Smith", "John Doe", "Priya Sharma",
                   "Animesh Devangari", "Sarthak"]:
            if n.lower() in text.lower():
                emp = n
                break

    # Last fallback: first name from text with typical name pattern
    if not emp:
        m = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z]+)', text)
        if m:
            emp = m.group(1)

    print(f"  Tracking: '{emp}'")
    R["employee"] = emp

    modules = {
        "attendance": "/attendance",
        "leave": "/leave",
        "org_chart": "/org-chart",
    }
    for mod, path in modules.items():
        go(d, path, 5)
        mt = wait_body(d)
        save_ss(d, f"f1_{mod}")
        found = emp and emp.lower() in mt.lower() if emp else None
        # Also try first name only
        if not found and emp and " " in emp:
            first = emp.split()[0]
            found = first.lower() in mt.lower()
        R["checks"][mod] = found
        print(f"  {mod}: {found}")

    # Documents & Assets
    for mod in ["documents", "assets"]:
        go(d, f"/{mod}", 4)
        mt = wait_body(d)
        save_ss(d, f"f1_{mod}")
        R["checks"][f"{mod}_loaded"] = len(mt) > 50
        print(f"  {mod}: loaded={len(mt) > 50}")

    if emp:
        missing = [m for m, v in R["checks"].items() if v is False]
        if missing:
            R["status"] = "FAIL"
        else:
            R["status"] = "PASS"
    else:
        R["status"] = "WARN"
    return R


def flow2(d):
    """Leave balance consistency."""
    print("\n=== FLOW 2: Leave Balance ===")
    R = {"status": "STARTED", "balances": {}}
    go(d, "/leave", 5)
    text = wait_body(d)
    save_ss(d, "f2_leave")

    for lt in ["earned","casual","sick","privilege","annual","comp"]:
        for i, line in enumerate(text.split("\n")):
            if lt in line.lower():
                nums = re.findall(r'(\d+\.?\d*)', line)
                if nums:
                    R["balances"][lt] = nums
                    break

    print(f"  Balances: {R['balances']}")

    go(d, "/attendance", 5)
    att = wait_body(d)
    save_ss(d, "f2_attendance")
    R["att_leave_refs"] = att.lower().count("leave")
    print(f"  Attendance leave refs: {R['att_leave_refs']}")

    go(d, "/dashboard", 4)
    dash = wait_body(d)
    save_ss(d, "f2_dashboard")
    R["dash_has_leave"] = "leave" in dash.lower()

    R["status"] = "PASS" if R["balances"] else "FAIL"
    R["leave_text_sample"] = text[:300]
    return R


def flow3(d):
    """Attendance vs Dashboard stats."""
    print("\n=== FLOW 3: Attendance vs Dashboard ===")
    R = {"status": "STARTED", "att": {}, "dash": {}}

    go(d, "/attendance", 5)
    att = wait_body(d)
    save_ss(d, "f3_attendance")
    kws = ["total","present","absent","late","on leave"]
    for kw in kws:
        m = re.findall(rf'{kw}\s*[:=]?\s*(\d+)', att.lower())
        if m: R["att"][kw] = m[0]
    R["att"]["rows"] = len(rows(d))
    print(f"  Att stats: {R['att']}")

    go(d, "/dashboard", 5)
    dash = wait_body(d)
    save_ss(d, "f3_dashboard")
    for kw in kws:
        m = re.findall(rf'{kw}\s*[:=]?\s*(\d+)', dash.lower())
        if m: R["dash"][kw] = m[0]
    print(f"  Dash stats: {R['dash']}")

    mm = []
    for kw in kws:
        a, dd = R["att"].get(kw), R["dash"].get(kw)
        if a and dd and a != dd:
            mm.append(f"{kw}: att={a} dash={dd}")
    R["mismatches"] = mm
    R["status"] = "FAIL" if mm else ("PASS" if (R["att"] or R["dash"]) else "WARN")
    return R


def flow4(d):
    """Employee profile tabs."""
    print("\n=== FLOW 4: Profile Tabs ===")
    R = {"status": "STARTED", "tabs": {}}
    go(d, "/employees", 5)
    wait_body(d)

    # Try to click first employee
    emp_url = None
    trs = rows(d)
    if trs:
        try:
            d.execute_script("arguments[0].click();", trs[0])
            time.sleep(4)
            if re.search(r'/employees?/', d.current_url) and d.current_url != f"{BASE_URL}/employees":
                emp_url = d.current_url
        except: pass

    if not emp_url:
        links = d.find_elements(By.CSS_SELECTOR, "a[href*='employee']")
        for l in links:
            h = l.get_attribute("href") or ""
            if re.search(r'/employees?/\d+', h):
                emp_url = h; break

    if not emp_url:
        emp_url = f"{BASE_URL}/employees/522"  # Ananya's ID from API

    print(f"  Profile: {emp_url}")
    d.get(emp_url)
    time.sleep(5)
    pt = wait_body(d)
    save_ss(d, "f4_profile")
    R["profile_chars"] = len(pt)
    R["has_email"] = "@" in pt

    tab_names = ["personal","education","experience","documents","address","attendance","leave","assets"]
    all_tabs = d.find_elements(By.CSS_SELECTOR, "[role='tab'], [class*='tab'] button, [class*='tab'] a, .tabs button, .tabs a")
    for tn in tab_names:
        for tel in all_tabs:
            if tn in tel.text.strip().lower():
                try:
                    d.execute_script("arguments[0].click();", tel)
                    time.sleep(2)
                    tc = body(d)
                    no_data = "no data" in tc.lower()[:300] or "no record" in tc.lower()[:300]
                    R["tabs"][tn] = not no_data
                    print(f"    {tn}: data={not no_data}")
                except: pass
                break

    R["status"] = "PASS" if R["tabs"] else "WARN"
    return R


def flow5(d):
    """Department consistency."""
    print("\n=== FLOW 5: Department Consistency ===")
    R = {"status": "STARTED"}
    dkws = ["engineering","hr","human resources","finance","marketing","sales",
            "design","product","operations","it","technology","support"]

    go(d, "/employees", 5)
    et = wait_body(d)
    save_ss(d, "f5_employees")
    ed = {k.title() for k in dkws if k in et.lower()}

    go(d, "/org-chart", 7)
    ot = wait_body(d)
    save_ss(d, "f5_orgchart")
    od = {k.title() for k in dkws if k in ot.lower()}

    R["emp_depts"] = sorted(ed)
    R["org_depts"] = sorted(od)
    print(f"  Emp: {ed}  Org: {od}")

    eo, oo = ed - od, od - ed
    R["emp_only"] = sorted(eo)
    R["org_only"] = sorted(oo)

    if eo or oo:
        R["status"] = "FAIL"
    else:
        R["status"] = "PASS" if ed else "WARN"
    return R


def flow6_admin(d):
    """Announcements - admin part."""
    go(d, "/announcements", 5)
    t = wait_body(d)
    save_ss(d, "f6_admin_ann")
    go(d, "/dashboard", 4)
    dt = wait_body(d)
    save_ss(d, "f6_admin_dash")
    return {
        "has": len(t) > 200 and "no announcement" not in t.lower()[:300],
        "chars": len(t),
        "on_dash": "announcement" in dt.lower(),
        "text_sample": t[:300]
    }

def flow6_emp(d):
    """Announcements - employee part."""
    go(d, "/announcements", 5)
    t = wait_body(d)
    save_ss(d, "f6_emp_ann")
    go(d, "/dashboard", 4)
    dt = wait_body(d)
    save_ss(d, "f6_emp_dash")
    return {
        "has": len(t) > 200 and "no announcement" not in t.lower()[:300],
        "chars": len(t),
        "text_sample": t[:300]
    }


def flow8_check(d, role_name):
    """Events check for a role."""
    go(d, "/events", 5)
    t = wait_body(d)
    save_ss(d, f"f8_{role_name}_events")
    return {
        "has": len(t) > 200 and "no event" not in t.lower()[:300],
        "chars": len(t)
    }


def flow10_check(d, role_name):
    """Survey check for a role."""
    go(d, "/surveys", 5)
    t = wait_body(d)
    save_ss(d, f"f10_{role_name}_surveys")
    return {
        "has": len(t) > 200 and "no survey" not in t.lower()[:300],
        "chars": len(t)
    }


def flow13_api(token):
    """API data counts."""
    counts = {}
    for name, ep in {"employees":"employees","announcements":"announcements",
                     "documents":"documents","events":"events","surveys":"surveys",
                     "departments":"departments"}.items():
        r = api_req(ep, token=token)
        if "error" not in r:
            if isinstance(r, list):
                counts[name] = len(r)
            elif isinstance(r, dict):
                data = r.get("data") or r.get("results") or r.get(name)
                if isinstance(data, list):
                    counts[name] = len(data)
                elif isinstance(r.get("data"), dict) and "total" in r["data"]:
                    counts[name] = r["data"]["total"]
                elif "total" in r:
                    counts[name] = r["total"]
                else:
                    counts[name] = "unk"
        else:
            counts[name] = f"err:{r.get('error')}"
    return counts

def flow13_ui(d):
    """UI data counts."""
    counts = {}
    for name, path in {"employees":"/employees","announcements":"/announcements",
                       "documents":"/documents","events":"/events","surveys":"/surveys"}.items():
        go(d, path, 4)
        text = wait_body(d)
        save_ss(d, f"f13_{name}")
        c = None
        for pat in [r'(?:total|showing)\s*:?\s*(\d+)', r'(\d+)\s*(?:total|results|records)', r'of\s+(\d+)']:
            m = re.search(pat, text.lower())
            if m: c = int(m.group(1)); break
        if c is None:
            r = rows(d)
            if r: c = len(r)
        counts[name] = c
    return counts


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("EMP CLOUD HRMS - CRITICAL DATA FLOW TEST")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # API
    print("\n--- API Auth ---")
    time.sleep(3)
    token = api_login(ADMIN_EMAIL, ADMIN_PASS)
    if not token:
        time.sleep(10)
        token = api_login(ADMIN_EMAIL, ADMIN_PASS)
    print(f"  Token: {'OK' if token else 'NONE'}")

    # ── BATCH 1: Admin flows 1-5 + flow7 + flow12 (single driver) ──
    print("\n--- BATCH 1: Admin Flows ---")
    d = get_driver()
    try:
        if not login(d, ADMIN_EMAIL, ADMIN_PASS):
            print("FATAL: Admin login failed")
            save_ss(d, "fatal_login")
            d.quit()
            return

        for name, func in [
            ("Flow 1: Employee Cross-Module", lambda: flow1(d)),
            ("Flow 2: Leave Balance", lambda: flow2(d)),
            ("Flow 3: Attendance vs Dashboard", lambda: flow3(d)),
            ("Flow 4: Profile Tabs", lambda: flow4(d)),
            ("Flow 5: Department Consistency", lambda: flow5(d)),
        ]:
            REPORT["flows_tested"] += 1
            try:
                r = func()
                REPORT["details"][name] = r
                st = r.get("status", "UNK")
                if st == "PASS": REPORT["flows_passed"] += 1
                elif st in ("FAIL","ERROR"): REPORT["flows_failed"] += 1
                print(f"  >> {name}: {st}")
            except Exception as e:
                print(f"  >> {name}: ERROR - {e}")
                traceback.print_exc()
                REPORT["details"][name] = {"status": "ERROR", "error": str(e)}
                REPORT["flows_failed"] += 1

        # Flow 6 admin part
        f6_admin = flow6_admin(d)

        # Flow 7: Documents
        REPORT["flows_tested"] += 1
        go(d, "/documents", 5)
        dt = wait_body(d)
        save_ss(d, "f7_documents")
        has_docs = len(dt) > 200 and "no document" not in dt.lower()[:300]
        REPORT["details"]["Flow 7: Documents"] = {"status": "PASS" if has_docs else "WARN", "has_docs": has_docs}
        if has_docs: REPORT["flows_passed"] += 1
        print(f"  >> Flow 7: Documents: {'PASS' if has_docs else 'WARN'}")

        # Flow 8 admin part
        f8_admin = flow8_check(d, "admin")

        # Flow 9: Helpdesk
        REPORT["flows_tested"] += 1
        hd_found = False
        for hp in ["/helpdesk", "/tickets"]:
            go(d, hp, 4)
            ht = wait_body(d)
            if len(ht) > 100 and any(k in ht.lower() for k in ["ticket","helpdesk"]):
                save_ss(d, "f9_admin_helpdesk")
                hd_found = True
                print(f"  >> Flow 9: Helpdesk found at {hp}")
                break
        REPORT["details"]["Flow 9: Helpdesk"] = {"status": "PASS" if hd_found else "WARN"}
        if hd_found: REPORT["flows_passed"] += 1
        print(f"  >> Flow 9: {'PASS' if hd_found else 'WARN'}")

        # Flow 10 admin part
        f10_admin = flow10_check(d, "admin")

        # Flow 11: Wellness (check as admin)
        REPORT["flows_tested"] += 1
        w_found = False
        for wp in ["/wellness", "/daily-checkin"]:
            go(d, wp, 4)
            wt = wait_body(d)
            if len(wt) > 100 and any(k in wt.lower() for k in ["wellness","check","mood"]):
                save_ss(d, "f11_wellness")
                w_found = True
                break
        REPORT["details"]["Flow 11: Wellness"] = {"status": "PASS" if w_found else "WARN"}
        if w_found: REPORT["flows_passed"] += 1
        print(f"  >> Flow 11: Wellness: {'PASS' if w_found else 'WARN'}")

        # Flow 12: Users
        REPORT["flows_tested"] += 1
        u_found = False
        for up in ["/users", "/settings/users"]:
            go(d, up, 4)
            ut = wait_body(d)
            if len(ut) > 100 and any(k in ut.lower() for k in ["user","invite","role"]):
                save_ss(d, "f12_users")
                u_found = True
                break
        REPORT["details"]["Flow 12: User Management"] = {"status": "PASS" if u_found else "WARN"}
        if u_found: REPORT["flows_passed"] += 1
        print(f"  >> Flow 12: Users: {'PASS' if u_found else 'WARN'}")

        # Flow 13 UI part
        f13_ui = flow13_ui(d)

    finally:
        d.quit()

    # ── BATCH 2: Employee session (flows 6,8,10 employee parts) ──
    print("\n--- BATCH 2: Employee Flows ---")
    d2 = get_driver()
    f6_emp = None
    f8_emp = None
    f10_emp = None
    try:
        if login(d2, EMP_EMAIL, EMP_PASS):
            f6_emp = flow6_emp(d2)
            f8_emp = flow8_check(d2, "emp")
            f10_emp = flow10_check(d2, "emp")

            # Flow 11 employee part
            for wp in ["/wellness", "/daily-checkin"]:
                go(d2, wp, 4)
                wt = wait_body(d2)
                if "wellness" in wt.lower() or "mood" in wt.lower():
                    save_ss(d2, "f11_emp_wellness")
                    break
        else:
            print("  Employee login failed")
    finally:
        d2.quit()

    # ── Process cross-role flows ──
    # Flow 6: Announcements
    REPORT["flows_tested"] += 1
    f6_result = {"status": "STARTED", "admin": f6_admin}
    if f6_emp:
        f6_result["employee"] = f6_emp
        print(f"  Flow 6: Admin has={f6_admin['has']}, Emp has={f6_emp['has']}")
        if f6_admin["has"] and not f6_emp["has"]:
            f6_result["status"] = "FAIL"
        else:
            f6_result["status"] = "PASS"
    else:
        f6_result["status"] = "WARN"
    REPORT["details"]["Flow 6: Announcements"] = f6_result
    if f6_result["status"] == "PASS": REPORT["flows_passed"] += 1
    elif f6_result["status"] == "FAIL": REPORT["flows_failed"] += 1
    print(f"  >> Flow 6: Announcements: {f6_result['status']}")

    # Flow 8: Events
    REPORT["flows_tested"] += 1
    f8_result = {"status": "STARTED", "admin": f8_admin}
    if f8_emp:
        f8_result["employee"] = f8_emp
        print(f"  Flow 8: Admin has={f8_admin['has']}, Emp has={f8_emp['has']}")
        if f8_admin["has"] and not f8_emp["has"]:
            f8_result["status"] = "FAIL"
        else:
            f8_result["status"] = "PASS"
    else:
        f8_result["status"] = "WARN"
    REPORT["details"]["Flow 8: Events"] = f8_result
    if f8_result["status"] == "PASS": REPORT["flows_passed"] += 1
    elif f8_result["status"] == "FAIL": REPORT["flows_failed"] += 1
    print(f"  >> Flow 8: Events: {f8_result['status']}")

    # Flow 10: Surveys
    REPORT["flows_tested"] += 1
    f10_result = {"status": "STARTED", "admin": f10_admin}
    if f10_emp:
        f10_result["employee"] = f10_emp
        print(f"  Flow 10: Admin has={f10_admin['has']}, Emp has={f10_emp['has']}")
        if f10_admin["has"] and not f10_emp["has"]:
            f10_result["status"] = "FAIL"
        else:
            f10_result["status"] = "PASS"
    else:
        f10_result["status"] = "WARN"
    REPORT["details"]["Flow 10: Surveys"] = f10_result
    if f10_result["status"] == "PASS": REPORT["flows_passed"] += 1
    elif f10_result["status"] == "FAIL": REPORT["flows_failed"] += 1
    print(f"  >> Flow 10: Surveys: {f10_result['status']}")

    # Flow 13: API consistency
    REPORT["flows_tested"] += 1
    f13_api_counts = flow13_api(token) if token else {}
    f13_result = {"status": "STARTED", "api": f13_api_counts, "ui": f13_ui, "mismatches": []}
    print(f"  Flow 13 API: {json.dumps(f13_api_counts, default=str)}")
    print(f"  Flow 13 UI:  {json.dumps(f13_ui, default=str)}")
    for name in f13_ui:
        av, uv = f13_api_counts.get(name), f13_ui.get(name)
        if isinstance(av, int) and isinstance(uv, int) and av != uv:
            f13_result["mismatches"].append({"module": name, "api": av, "ui": uv})
    f13_result["status"] = "FAIL" if f13_result["mismatches"] else "PASS"
    REPORT["details"]["Flow 13: API Consistency"] = f13_result
    if f13_result["status"] == "PASS": REPORT["flows_passed"] += 1
    elif f13_result["status"] == "FAIL": REPORT["flows_failed"] += 1
    print(f"  >> Flow 13: API Consistency: {f13_result['status']}")

    # ── Upload screenshots ──
    ss_urls = upload_screenshots_to_github()

    # ── File bugs with screenshot URLs ──
    print("\n--- Filing Bugs ---")

    # Flow 1 bugs
    f1 = REPORT["details"].get("Flow 1: Employee Cross-Module", {})
    if f1.get("status") == "FAIL":
        emp = f1.get("employee", "unknown")
        missing = [m for m, v in f1.get("checks", {}).items() if v is False]
        body_text = f"""## Employee Not Found Across Modules

**Employee:** {emp}
**Missing from:** {', '.join(missing)}
**Present in:** {', '.join(m for m, v in f1.get('checks', {}).items() if v is True)}

**Steps:**
1. Found "{emp}" in /employees directory
2. Checked each module
3. Employee not found in some modules

**Expected:** Employee visible in all HR modules.
**Actual:** Missing from {len(missing)} module(s).

![Employees]({ss_urls.get('f1_employees', 'N/A')})
![Attendance]({ss_urls.get('f1_attendance', 'N/A')})
![Leave]({ss_urls.get('f1_leave', 'N/A')})
![Org Chart]({ss_urls.get('f1_org_chart', 'N/A')})
"""
        file_bug(f"Employee '{emp}' not found in {', '.join(missing)}", body_text, "high")

    # Flow 2 bugs
    f2 = REPORT["details"].get("Flow 2: Leave Balance", {})
    if f2.get("status") == "FAIL" and not f2.get("balances"):
        body_text = f"""## Leave Balance Data Not Visible

**Steps:** Navigate to /leave as Org Admin
**Expected:** Leave balances (Earned, Sick, Casual) with numeric values
**Actual:** No balance data found

**Page text:** {f2.get('leave_text_sample', 'N/A')[:400]}

![Leave]({ss_urls.get('f2_leave', 'N/A')})
"""
        file_bug("Leave balance not visible on leave page", body_text, "medium")

    # Flow 3 bugs
    f3 = REPORT["details"].get("Flow 3: Attendance vs Dashboard", {})
    if f3.get("mismatches"):
        body_text = f"""## Attendance Stats Mismatch

**Mismatches:** {chr(10).join('- ' + m for m in f3['mismatches'])}
**Attendance:** {json.dumps(f3.get('att', {}))}
**Dashboard:** {json.dumps(f3.get('dash', {}))}

![Attendance]({ss_urls.get('f3_attendance', 'N/A')})
![Dashboard]({ss_urls.get('f3_dashboard', 'N/A')})
"""
        file_bug(f"Attendance stats mismatch: {'; '.join(f3['mismatches'])}", body_text, "high")

    # Flow 5 bugs
    f5 = REPORT["details"].get("Flow 5: Department Consistency", {})
    if f5.get("status") == "FAIL":
        body_text = f"""## Department Inconsistency

**Only in Employee List:** {f5.get('emp_only', [])}
**Only in Org Chart:** {f5.get('org_only', [])}

![Employees]({ss_urls.get('f5_employees', 'N/A')})
![Org Chart]({ss_urls.get('f5_orgchart', 'N/A')})
"""
        file_bug("Department mismatch between Employee List and Org Chart", body_text, "medium")

    # Flow 6 bugs
    f6 = REPORT["details"].get("Flow 6: Announcements", {})
    if f6.get("status") == "FAIL":
        body_text = f"""## Announcements Not Visible to Employee

**Admin:** {f6.get('admin', {}).get('chars', '?')} chars
**Employee:** {f6.get('employee', {}).get('chars', '?')} chars

![Admin]({ss_urls.get('f6_admin_ann', 'N/A')})
![Employee]({ss_urls.get('f6_emp_ann', 'N/A')})
"""
        file_bug("Announcements not visible to employee", body_text, "high")

    # Flow 8 bugs
    f8 = REPORT["details"].get("Flow 8: Events", {})
    if f8.get("status") == "FAIL":
        body_text = f"""## Events Not Visible to Employee

![Admin]({ss_urls.get('f8_admin_events', 'N/A')})
![Employee]({ss_urls.get('f8_emp_events', 'N/A')})
"""
        file_bug("Events not visible to employee", body_text, "medium")

    # Flow 10 bugs
    f10 = REPORT["details"].get("Flow 10: Surveys", {})
    if f10.get("status") == "FAIL":
        body_text = f"""## Surveys Not Visible to Employee

![Admin]({ss_urls.get('f10_admin_surveys', 'N/A')})
![Employee]({ss_urls.get('f10_emp_surveys', 'N/A')})
"""
        file_bug("Active surveys not visible to employees", body_text, "medium")

    # Flow 13 bugs
    f13 = REPORT["details"].get("Flow 13: API Consistency", {})
    if f13.get("mismatches"):
        mm = "\n".join([f"- **{m['module']}**: API={m['api']}, UI={m['ui']}" for m in f13["mismatches"]])
        body_text = f"""## API vs UI Count Mismatch

{mm}

**API:** {json.dumps(f13.get('api', {}), default=str)}
**UI:** {json.dumps(f13.get('ui', {}), default=str)}
"""
        file_bug(f"API vs UI count mismatch in {len(f13['mismatches'])} modules", body_text, "high")

    # ── Final Report ──
    print("\n")
    print("=" * 70)
    print("CRITICAL DATA FLOW TEST - FINAL REPORT")
    print("=" * 70)
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Flows Tested: {REPORT['flows_tested']}")
    print(f"Passed: {REPORT['flows_passed']}")
    print(f"Failed: {REPORT['flows_failed']}")
    warn = REPORT['flows_tested'] - REPORT['flows_passed'] - REPORT['flows_failed']
    print(f"Warnings/Unknown: {warn}")
    print(f"Bugs Filed: {len(REPORT['bugs'])}")
    print(f"Screenshots: {len(REPORT['screenshots'])}")

    print("\n--- Results ---")
    for name, d in REPORT["details"].items():
        st = d.get("status", "UNK")
        m = {"PASS":"PASS","FAIL":"FAIL","WARN":"WARN","ERROR":"ERR"}.get(st, "UNK")
        print(f"  [{m}] {name}")

    if REPORT["bugs"]:
        print("\n--- Bugs Filed ---")
        for b in REPORT["bugs"]:
            print(f"  [{b['severity'].upper()}] {b['title']}")
            print(f"    {b['url']}")

    print(f"\n--- Screenshots ({len(REPORT['screenshots'])}) ---")
    for name, path in REPORT["screenshots"].items():
        url = ss_urls.get(name, "not uploaded")
        print(f"  {name}: {url}")

    print("\n--- Key Findings ---")
    for name, d in REPORT["details"].items():
        if not isinstance(d, dict): continue
        for k, v in d.items():
            if k in ("status","error") or "text" in k.lower(): continue
            if v is not None and v != "STARTED" and v != {} and v != []:
                vstr = json.dumps(v, default=str) if not isinstance(v, str) else v
                if len(vstr) > 2:
                    print(f"  {name} | {k}: {vstr[:120]}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
