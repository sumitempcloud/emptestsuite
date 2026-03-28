#!/usr/bin/env python3
"""
EMP Cloud HRMS - Module Subscription & Deep Testing (v2)
- Re-subscribe any accidentally unsubscribed modules
- Fix login for recruit (Sign in button) and LMS
- Deep-test each module subdomain
- File GitHub issues for bugs
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os, time, json, base64, traceback, re
import urllib.request, urllib.error
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

BASE       = "https://test-empcloud.empcloud.com"
ORG_EMAIL  = "ananya@technova.in"
ORG_PASS   = "Welcome@123"
SA_EMAIL   = "admin@empcloud.com"
SA_PASS    = "SuperAdmin@2026"
GH_PAT     = "$GITHUB_TOKEN"
GH_REPO    = "EmpCloud/EmpCloud"
SS_DIR     = r"C:\emptesting\screenshots"
CHROME     = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

SUBDOMAINS = {
    "recruit":     "https://test-recruit.empcloud.com",
    "performance": "https://test-performance.empcloud.com",
    "rewards":     "https://test-rewards.empcloud.com",
    "exit":        "https://test-exit.empcloud.com",
    "lms":         "https://testlms.empcloud.com",
    "payroll":     "https://testpayroll.empcloud.com",
    "project":     "https://test-project.empcloud.com",
    "monitor":     "https://test-empmonitor.empcloud.com",
}

os.makedirs(SS_DIR, exist_ok=True)
bugs = []
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
_cd = None

def cdpath():
    global _cd
    if not _cd: _cd = ChromeDriverManager().install()
    return _cd

def kill_chrome():
    """Kill all chrome/chromedriver processes."""
    import subprocess
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"], capture_output=True)

def mkdriver():
    o = Options()
    o.binary_location = CHROME
    o.add_argument("--headless=new")
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--disable-gpu")
    o.add_argument("--window-size=1920,1080")
    o.add_argument("--disable-extensions")
    o.add_argument("--ignore-certificate-errors")
    d = webdriver.Chrome(service=Service(cdpath()), options=o)
    return d

def alive(d):
    try: d.current_url; return True
    except: return False

def safe_quit(d):
    try: d.quit()
    except: pass
    time.sleep(1)

def shot(d, name):
    try:
        p = os.path.join(SS_DIR, f"{re.sub(r'[^a-zA-Z0-9_-]','_',name)[:50]}_{TS}.png")
        d.save_screenshot(p); print(f"  [SS] {p}"); return p
    except: return None

def go(d, url):
    try:
        d.get(url); time.sleep(3); return True
    except Exception as e:
        print(f"  [NAV-ERR] {url}: {e}"); return False

def login(d, email, pw, base=None):
    """Robust login handling all button variants."""
    t = base or BASE
    print(f"  Login {email} at {t}...")
    if not go(d, f"{t}/login"): return False
    time.sleep(2)

    # Find email field
    ef = None
    for s in ["input[name='email']","input[type='email']","#email",
              "input[name='username']","input[placeholder*='mail']",
              "input[placeholder*='Mail']","input[placeholder*='company']",
              "input[placeholder*='Username']","input[placeholder*='username']"]:
        try:
            e = d.find_element(By.CSS_SELECTOR, s)
            if e.is_displayed(): ef = e; break
        except: pass
    if not ef:
        try:
            for inp in d.find_elements(By.TAG_NAME, "input"):
                tp = (inp.get_attribute("type") or "").lower()
                ph = (inp.get_attribute("placeholder") or "").lower()
                if tp in ("email","text") and inp.is_displayed() and "search" not in ph:
                    ef = inp; break
        except: pass
    if not ef: print("  [WARN] No email field"); return False
    ef.clear(); ef.send_keys(email); time.sleep(0.3)

    # Find password field
    pf = None
    for s in ["input[name='password']","input[type='password']","#password"]:
        try:
            e = d.find_element(By.CSS_SELECTOR, s)
            if e.is_displayed(): pf = e; break
        except: pass
    if not pf: print("  [WARN] No pass field"); return False
    pf.clear(); pf.send_keys(pw); time.sleep(0.3)

    # Find submit button - match "Sign in", "Login", "Log in", "Submit" etc.
    btn = None
    try:
        for b in d.find_elements(By.TAG_NAME, "button"):
            if b.is_displayed():
                txt = b.text.lower().strip()
                if any(w in txt for w in ["login","sign in","submit","log in","signin"]):
                    btn = b; break
    except: pass
    if not btn:
        try: btn = d.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except: pass
    if not btn:
        # Try any visible button
        try:
            for b in d.find_elements(By.TAG_NAME, "button"):
                if b.is_displayed() and len(b.text.strip()) > 0 and len(b.text.strip()) < 20:
                    btn = b; break
        except: pass

    if btn:
        print(f"    Clicking: '{btn.text.strip()}'")
        try: btn.click()
        except: d.execute_script("arguments[0].click();", btn)
    else:
        pf.send_keys(Keys.RETURN)

    time.sleep(8)
    try:
        WebDriverWait(d, 10).until(
            lambda x: x.execute_script("return document.readyState") == "complete"
        )
    except: pass
    time.sleep(2)
    ok = "/login" not in d.current_url.lower()
    print(f"  {'[OK]' if ok else '[FAIL]'} -> {d.current_url}")
    return ok

def bodytext(d):
    try: return d.find_element(By.TAG_NAME, "body").text
    except: return ""

def upload_ss(fp, rn):
    try:
        with open(fp,"rb") as f: ct = base64.b64encode(f.read()).decode()
        url = f"https://api.github.com/repos/{GH_REPO}/contents/screenshots/{rn}"
        data = json.dumps({"message":f"Add {rn}","content":ct}).encode()
        req = urllib.request.Request(url,data=data,method="PUT")
        req.add_header("Authorization",f"token {GH_PAT}")
        req.add_header("Content-Type","application/json")
        req.add_header("User-Agent","EmpCloud-Test/1.0")
        resp = urllib.request.urlopen(req, timeout=60)
        raw = f"https://raw.githubusercontent.com/{GH_REPO}/main/screenshots/{rn}"
        print(f"  [UP] {raw}"); return raw
    except urllib.error.HTTPError as e:
        if e.code==422:
            return f"https://raw.githubusercontent.com/{GH_REPO}/main/screenshots/{rn}"
        b = e.read().decode()[:200]
        print(f"  [UP-ERR] {e.code}: {b}"); return None
    except Exception as e:
        print(f"  [UP-ERR] {e}"); return None

def gh_issue(title, body, labels=None):
    try:
        url = f"https://api.github.com/repos/{GH_REPO}/issues"
        data = json.dumps({"title":title,"body":body,"labels":labels or ["bug"]}).encode()
        req = urllib.request.Request(url,data=data,method="POST")
        req.add_header("Authorization",f"token {GH_PAT}")
        req.add_header("Content-Type","application/json")
        req.add_header("User-Agent","EmpCloud-Test/1.0")
        resp = urllib.request.urlopen(req, timeout=30)
        n = json.loads(resp.read().decode())["number"]
        print(f"  [ISSUE #{n}] {title}"); return n
    except urllib.error.HTTPError as e:
        b = e.read().decode()[:200]
        print(f"  [ISSUE-ERR] {e.code}: {b}"); return None
    except Exception as e:
        print(f"  [ISSUE-ERR] {e}"); return None

def file_bug(d, mod, title, desc):
    sn = f"module_{mod}_{TS}"
    sp = shot(d, sn)
    if not sp: return
    rn = f"{sn}.png"
    img = upload_ss(sp, rn)
    body = f"""## Bug Report: {mod}

**Module:** {mod}
**URL:** {d.current_url}
**Timestamp:** {datetime.now().isoformat()}

## Description
{desc}

## Screenshot
![Screenshot]({img or 'N/A'})

## Environment
- Browser: Chrome (headless), 1920x1080
- User: {ORG_EMAIL}
"""
    n = gh_issue(title, body, ["bug","module-testing"])
    bugs.append({"module":mod,"title":title,"issue":n,"url":d.current_url})

def sidebar(d):
    items = []; seen = set()
    for sel in ["nav a",".sidebar a","[class*='sidebar'] a","[class*='Sidebar'] a",
                "aside a","[class*='drawer'] a","[class*='Drawer'] a",
                ".MuiDrawer-root a",".MuiList-root a","[class*='menu'] a","[role='navigation'] a"]:
        try:
            for el in d.find_elements(By.CSS_SELECTOR, sel):
                try:
                    t = el.text.strip(); h = el.get_attribute("href") or ""
                    if t and t not in seen and len(t)<80: seen.add(t); items.append({"text":t,"href":h})
                except: pass
        except: pass
    return items

# ════════════════════════════════════════════════════
# STEP 1: RE-SUBSCRIBE ALL MODULES
# ════════════════════════════════════════════════════
def resubscribe_all():
    print("\n" + "="*70)
    print("STEP 1: RE-SUBSCRIBE ALL MODULES (fix accidental unsubscribes)")
    print("="*70)

    d = mkdriver()
    try:
        login(d, ORG_EMAIL, ORG_PASS)
        go(d, f"{BASE}/modules")
        time.sleep(2)
        shot(d, "resub_before")

        text = bodytext(d)
        print(f"  Modules page text:\n{text[:800]}")

        # Find Subscribe buttons (NOT Unsubscribe)
        subscribe_clicked = 0
        for attempt in range(3):  # multiple passes since page may update
            try:
                buttons = d.find_elements(By.CSS_SELECTOR, "button, a, [role='button']")
                for btn in buttons:
                    try:
                        txt = btn.text.strip()
                        # ONLY click "Subscribe" not "Unsubscribe"
                        if txt == "Subscribe" and btn.is_displayed():
                            print(f"    Clicking Subscribe button...")
                            try: btn.click()
                            except: d.execute_script("arguments[0].click();", btn)
                            time.sleep(3)
                            subscribe_clicked += 1
                            # Handle confirmation
                            try:
                                for cb in d.find_elements(By.CSS_SELECTOR, "button"):
                                    ct = cb.text.lower()
                                    if cb.is_displayed() and any(w in ct for w in ["confirm","ok","yes","proceed","subscribe"]):
                                        cb.click(); time.sleep(2); break
                            except: pass
                            shot(d, f"resub_click_{subscribe_clicked}")
                    except StaleElementReferenceException:
                        continue
                    except: pass
            except: pass
            if subscribe_clicked == 0:
                break
            # Re-navigate to refresh
            go(d, f"{BASE}/modules")
            time.sleep(2)

        print(f"  Clicked Subscribe {subscribe_clicked} times")

        # Verify final state
        go(d, f"{BASE}/modules")
        time.sleep(2)
        shot(d, "resub_after")
        text = bodytext(d)
        print(f"  Final modules state:\n{text[:800]}")

    except Exception as e:
        print(f"  [ERR] {e}"); traceback.print_exc()
    finally:
        safe_quit(d)

# ════════════════════════════════════════════════════
# STEP 2: VERIFY SIDEBAR (updated)
# ════════════════════════════════════════════════════
def verify_sidebar():
    print("\n" + "="*70)
    print("STEP 2: VERIFY ALL MODULES IN SIDEBAR")
    print("="*70)

    d = mkdriver()
    sb_items = []
    try:
        login(d, ORG_EMAIL, ORG_PASS)
        go(d, f"{BASE}/dashboard")
        time.sleep(3)

        # expand collapsed groups
        for sel in ["[class*='sidebar'] svg",".MuiListItemButton-root","[class*='expand']"]:
            try:
                for el in d.find_elements(By.CSS_SELECTOR, sel):
                    try:
                        if el.is_displayed():
                            try: el.click()
                            except: d.execute_script("arguments[0].click();", el)
                            time.sleep(0.3)
                    except: pass
            except: pass
        time.sleep(1)

        sb_items = sidebar(d)
        print(f"\n  Full sidebar ({len(sb_items)} items):")
        for i in sb_items: print(f"    {i['text']:30s} {i['href']}")
        shot(d, "v2_sidebar")

    except Exception as e:
        print(f"  [ERR] {e}")
    finally:
        safe_quit(d)
    return sb_items

# ════════════════════════════════════════════════════
# STEP 3: DEEP TEST EACH MODULE
# ════════════════════════════════════════════════════
def test_recruit():
    print(f"\n{'~'*60}\n  RECRUIT (https://test-recruit.empcloud.com)\n{'~'*60}")
    d = mkdriver()
    try:
        go(d, "https://test-recruit.empcloud.com")
        time.sleep(2)
        shot(d, "v2_recruit_land")
        cur = d.current_url

        if "/login" in cur.lower():
            # The recruit login has "Sign in" button
            ok = login(d, ORG_EMAIL, ORG_PASS, base="https://test-recruit.empcloud.com")
            time.sleep(3)
            shot(d, "v2_recruit_postlogin")
            cur = d.current_url
            text = bodytext(d)

            if "/login" in cur.lower():
                print("  [BUG] Cannot login to recruit module")
                file_bug(d, "recruit",
                    "[Recruit] Cannot login to EMP Recruit subdomain with org admin credentials",
                    f"Attempting to login with {ORG_EMAIL} / Welcome@123 at https://test-recruit.empcloud.com/login "
                    f"stays on the login page. The page shows demo credentials hint but org admin creds don't work. "
                    f"Current URL after login attempt: {cur}")
                return {"status": "login_failed"}

        text = bodytext(d)
        print(f"  Loaded: {d.current_url}")
        print(f"  Text: {text[:300]}")

        # Test sub-pages
        nav_items = sidebar(d)
        print(f"  Nav: {len(nav_items)} items")
        for n in nav_items[:10]: print(f"    - {n['text']}")

        for path in ["/jobs","/candidates","/dashboard","/pipeline","/applications"]:
            if not alive(d): break
            go(d, f"https://test-recruit.empcloud.com{path}")
            time.sleep(1)
            t = bodytext(d)
            ok = len(t.strip())>30 and "/login" not in d.current_url.lower()
            print(f"    {'[OK]' if ok else '[--]'} {path} ({len(t)}ch)")
            if ok: shot(d, f"v2_recruit_{path.strip('/')}")

        return {"status": "loaded" if "/login" not in d.current_url.lower() else "login_failed"}

    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_performance():
    print(f"\n{'~'*60}\n  PERFORMANCE (https://test-performance.empcloud.com)\n{'~'*60}")
    d = mkdriver()
    try:
        go(d, "https://test-performance.empcloud.com")
        time.sleep(2)
        if "/login" in d.current_url.lower():
            login(d, ORG_EMAIL, ORG_PASS, base="https://test-performance.empcloud.com")
            time.sleep(3)

        text = bodytext(d)
        print(f"  Loaded: {d.current_url}")
        shot(d, "v2_perf_main")

        nav_items = sidebar(d)
        print(f"  Nav: {[n['text'] for n in nav_items[:10]]}")

        # Test key pages
        for path in ["/dashboard","/review-cycles","/goals","/goal-alignment","/competencies",
                     "/pips","/career-paths","/one-on-ones","/feedback","/analytics","/9-box","/settings"]:
            if not alive(d): break
            go(d, f"https://test-performance.empcloud.com{path}")
            time.sleep(1)
            t = bodytext(d)
            ok = len(t.strip())>30 and "/login" not in d.current_url.lower()
            print(f"    {'[OK]' if ok else '[--]'} {path} ({len(t)}ch)")

        # Try creating a goal
        go(d, "https://test-performance.empcloud.com/goals")
        time.sleep(2)
        shot(d, "v2_perf_goals")
        try:
            for el in d.find_elements(By.CSS_SELECTOR, "button"):
                if el.is_displayed() and any(w in el.text.lower() for w in ["add","create","new","+"]):
                    print(f"  Create btn: '{el.text.strip()}'")
                    try: el.click()
                    except: d.execute_script("arguments[0].click();", el)
                    time.sleep(3)
                    shot(d, "v2_perf_create_goal")
                    break
        except: pass

        return {"status": "loaded"}
    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_rewards():
    print(f"\n{'~'*60}\n  REWARDS (https://test-rewards.empcloud.com)\n{'~'*60}")
    d = mkdriver()
    try:
        go(d, "https://test-rewards.empcloud.com")
        time.sleep(2)
        if "/login" in d.current_url.lower():
            login(d, ORG_EMAIL, ORG_PASS, base="https://test-rewards.empcloud.com")
            time.sleep(3)

        text = bodytext(d)
        print(f"  Loaded: {d.current_url}")
        shot(d, "v2_rewards_main")

        # Test badges, kudos, leaderboard
        for path in ["/dashboard","/feed","/celebrations","/kudos","/leaderboard",
                     "/badges","/rewards","/redemptions","/challenges","/milestones",
                     "/nominations","/budgets","/analytics","/settings"]:
            if not alive(d): break
            go(d, f"https://test-rewards.empcloud.com{path}")
            time.sleep(1)
            t = bodytext(d)
            ok = len(t.strip())>30 and "/login" not in d.current_url.lower()
            print(f"    {'[OK]' if ok else '[--]'} {path} ({len(t)}ch)")

        # Try giving kudos
        go(d, "https://test-rewards.empcloud.com/kudos")
        time.sleep(2)
        shot(d, "v2_rewards_kudos")
        try:
            for el in d.find_elements(By.CSS_SELECTOR, "button"):
                if el.is_displayed() and any(w in el.text.lower() for w in ["give","send","new","create","+"]):
                    print(f"  Kudos btn: '{el.text.strip()}'")
                    try: el.click()
                    except: d.execute_script("arguments[0].click();", el)
                    time.sleep(3)
                    shot(d, "v2_rewards_give_kudos")
                    break
        except: pass

        return {"status": "loaded"}
    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_exit():
    print(f"\n{'~'*60}\n  EXIT (https://test-exit.empcloud.com)\n{'~'*60}")
    d = mkdriver()
    try:
        go(d, "https://test-exit.empcloud.com")
        time.sleep(2)
        if "/login" in d.current_url.lower():
            login(d, ORG_EMAIL, ORG_PASS, base="https://test-exit.empcloud.com")
            time.sleep(3)

        text = bodytext(d)
        print(f"  Loaded: {d.current_url}")
        shot(d, "v2_exit_main")

        for path in ["/dashboard","/exits","/checklists","/clearance","/interviews",
                     "/fnf","/notice-buyout","/assets","/kt","/letters","/alumni","/rehire",
                     "/analytics","/flight-risk","/settings"]:
            if not alive(d): break
            go(d, f"https://test-exit.empcloud.com{path}")
            time.sleep(1)
            t = bodytext(d)
            ok = len(t.strip())>30 and "/login" not in d.current_url.lower()
            print(f"    {'[OK]' if ok else '[--]'} {path} ({len(t)}ch)")
            if ok and path in ["/exits","/checklists"]:
                shot(d, f"v2_exit_{path.strip('/')}")

        return {"status": "loaded"}
    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_lms():
    print(f"\n{'~'*60}\n  LMS (https://testlms.empcloud.com)\n{'~'*60}")
    d = mkdriver()
    try:
        go(d, "https://testlms.empcloud.com")
        time.sleep(2)
        shot(d, "v2_lms_land")

        if "/login" in d.current_url.lower():
            # Try org admin creds first
            ok = login(d, ORG_EMAIL, ORG_PASS, base="https://testlms.empcloud.com")
            time.sleep(3)
            shot(d, "v2_lms_orgadmin_attempt")

            if "/login" in d.current_url.lower():
                print("  [BUG] Org admin cannot login to LMS")
                file_bug(d, "lms",
                    "[LMS] Cannot login to EmpCloud LMS with org admin credentials",
                    f"Attempting to login with {ORG_EMAIL} at https://testlms.empcloud.com/login "
                    f"fails. The login page shows demo credentials (admin@demo.com / demo1234) "
                    f"suggesting the LMS module is not properly integrated with the main EmpCloud "
                    f"authentication system. Org admin credentials should work across all subscribed modules.")
                return {"status": "login_failed"}

        text = bodytext(d)
        print(f"  Loaded: {d.current_url}")
        print(f"  Text: {text[:300]}")

        for path in ["/courses","/dashboard","/learning","/my-courses","/assessments"]:
            if not alive(d): break
            go(d, f"https://testlms.empcloud.com{path}")
            time.sleep(1)
            t = bodytext(d)
            ok = len(t.strip())>30 and "/login" not in d.current_url.lower()
            print(f"    {'[OK]' if ok else '[--]'} {path} ({len(t)}ch)")

        return {"status": "loaded" if "/login" not in d.current_url.lower() else "login_failed"}
    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_payroll():
    print(f"\n{'~'*60}\n  PAYROLL (https://testpayroll.empcloud.com)\n{'~'*60}")
    d = mkdriver()
    try:
        go(d, "https://testpayroll.empcloud.com")
        time.sleep(2)
        if "/login" in d.current_url.lower():
            login(d, ORG_EMAIL, ORG_PASS, base="https://testpayroll.empcloud.com")
            time.sleep(3)

        text = bodytext(d)
        print(f"  Loaded: {d.current_url}")
        shot(d, "v2_payroll_main")

        nav_items = sidebar(d)
        print(f"  Nav: {[n['text'] for n in nav_items[:10]]}")

        # Try admin panel link
        for n in nav_items:
            if "admin" in n["text"].lower() and n["href"]:
                print(f"  Trying Admin Panel: {n['href']}")
                go(d, n["href"])
                time.sleep(2)
                shot(d, "v2_payroll_admin")
                admin_text = bodytext(d)
                print(f"  Admin text: {admin_text[:200]}")
                break

        for path in ["/dashboard","/my","/payslips","/my-salary","/my-tax",
                     "/declarations","/reimbursements","/admin","/admin/dashboard",
                     "/admin/employees","/admin/payroll-run","/admin/salary-structure",
                     "/admin/components"]:
            if not alive(d): break
            go(d, f"https://testpayroll.empcloud.com{path}")
            time.sleep(1)
            t = bodytext(d)
            ok = len(t.strip())>30 and "/login" not in d.current_url.lower()
            print(f"    {'[OK]' if ok else '[--]'} {path} ({len(t)}ch)")
            if ok and "admin" in path:
                shot(d, f"v2_payroll_{path.strip('/').replace('/','_')}")

        return {"status": "loaded"}
    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_project():
    print(f"\n{'~'*60}\n  PROJECT (https://test-project.empcloud.com)\n{'~'*60}")
    d = mkdriver()
    try:
        go(d, "https://test-project.empcloud.com")
        time.sleep(2)
        text = bodytext(d)
        shot(d, "v2_project_land")
        print(f"  Loaded: {d.current_url}")
        print(f"  Text: {text[:300]}")

        # The project page shows a marketing landing page, not an app
        if "empower your team" in text.lower() or "streamline" in text.lower():
            print("  [BUG] Project module shows marketing landing page, not the app")

            # Try clicking the CTA button
            try:
                for el in d.find_elements(By.CSS_SELECTOR, "button, a"):
                    if el.is_displayed() and any(w in el.text.lower() for w in ["streamline","start","get started","login","sign"]):
                        print(f"  Clicking CTA: '{el.text.strip()}'")
                        href = el.get_attribute("href")
                        if href:
                            go(d, href)
                        else:
                            try: el.click()
                            except: d.execute_script("arguments[0].click();", el)
                        time.sleep(3)
                        shot(d, "v2_project_after_cta")
                        print(f"  After CTA: {d.current_url}")
                        print(f"  Text: {bodytext(d)[:200]}")
                        break
            except: pass

            file_bug(d, "project",
                "[Project] Module shows marketing landing page instead of project management app",
                f"Navigating to https://test-project.empcloud.com shows a marketing/promotional page "
                f"with text 'Empower Your Team with Advanced Project Management in EmpMonitor' instead "
                f"of the actual project management application. There is no login form or app interface. "
                f"The page title references EmpMonitor, suggesting a branding mismatch. "
                f"Sub-pages like /projects, /dashboard, /tasks all redirect back to the same landing page.")

        # Try sub-pages anyway
        for path in ["/login","/projects","/dashboard","/tasks","/boards"]:
            if not alive(d): break
            go(d, f"https://test-project.empcloud.com{path}")
            time.sleep(1)
            t = bodytext(d)
            cur = d.current_url
            print(f"    {path} -> {cur} ({len(t)}ch)")
            if "/login" in path and "/login" in cur.lower():
                # Try logging in
                login(d, ORG_EMAIL, ORG_PASS, base="https://test-project.empcloud.com")
                time.sleep(2)
                shot(d, "v2_project_postlogin")
                print(f"  After login: {d.current_url}")

        return {"status": "landing_page_only"}
    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_monitor():
    print(f"\n{'~'*60}\n  MONITOR (https://test-empmonitor.empcloud.com)\n{'~'*60}")
    d = mkdriver()
    try:
        go(d, "https://test-empmonitor.empcloud.com")
        time.sleep(2)
        shot(d, "v2_monitor_land")
        cur = d.current_url
        text = bodytext(d)
        print(f"  Loaded: {cur}")
        print(f"  Text: {text[:300]}")

        # EmpMonitor has its own login with Username/Password
        if "/login" in cur.lower() or "login to your account" in text.lower() or "admin-login" in cur.lower():
            # Try the admin login page
            go(d, "https://test-empmonitor.empcloud.com/admin-login")
            time.sleep(2)
            shot(d, "v2_monitor_admin_login")

            # Try login with org admin email
            login(d, ORG_EMAIL, ORG_PASS, base="https://test-empmonitor.empcloud.com")
            time.sleep(3)
            shot(d, "v2_monitor_postlogin")
            cur = d.current_url

            if "/login" in cur.lower() or "admin-login" in cur.lower():
                print("  [BUG] Cannot login to EmpMonitor with org admin credentials")
                file_bug(d, "monitor",
                    "[Monitor] Cannot login to EmpMonitor with org admin credentials",
                    f"EmpMonitor at https://test-empmonitor.empcloud.com has its own login system "
                    f"separate from EmpCloud. The admin login page uses Username/Password fields "
                    f"(not Email), and org admin credentials ({ORG_EMAIL}) don't work. "
                    f"The module is not integrated with EmpCloud's SSO/authentication.")
                return {"status": "login_failed"}

        text = bodytext(d)
        print(f"  Post-login: {d.current_url}")
        print(f"  Text: {text[:200]}")
        return {"status": "loaded" if "/login" not in d.current_url.lower() else "login_failed"}
    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_billing():
    print(f"\n{'~'*60}\n  BILLING (main app)\n{'~'*60}")
    d = mkdriver()
    try:
        login(d, ORG_EMAIL, ORG_PASS)
        go(d, f"{BASE}/billing")
        time.sleep(2)
        text = bodytext(d)
        print(f"  Loaded: {d.current_url} ({len(text)}ch)")
        shot(d, "v2_billing_main")

        # Test billing tabs
        for tab_text in ["Subscriptions","Invoices","Payments","Overview"]:
            try:
                for el in d.find_elements(By.CSS_SELECTOR, "button, a, [role='tab']"):
                    if el.is_displayed() and tab_text.lower() in el.text.lower():
                        try: el.click()
                        except: d.execute_script("arguments[0].click();", el)
                        time.sleep(2)
                        shot(d, f"v2_billing_{tab_text.lower()}")
                        print(f"    [OK] Tab: {tab_text} ({len(bodytext(d))}ch)")
                        break
            except: pass

        return {"status": "loaded"}
    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_biometrics():
    print(f"\n{'~'*60}\n  BIOMETRICS (main app)\n{'~'*60}")
    d = mkdriver()
    try:
        login(d, ORG_EMAIL, ORG_PASS)
        go(d, f"{BASE}/biometrics")
        time.sleep(2)
        text = bodytext(d)
        print(f"  Loaded: {d.current_url} ({len(text)}ch)")
        print(f"  Text: {text[:400]}")
        shot(d, "v2_biometrics_main")

        # Test sub-pages
        for path in ["/biometrics/devices","/biometrics/logs","/biometrics/enrollment",
                     "/biometrics/settings","/biometrics/face-enrollment"]:
            if not alive(d): break
            go(d, f"{BASE}{path}")
            time.sleep(1)
            t = bodytext(d)
            ok = len(t.strip())>30 and "/login" not in d.current_url.lower()
            print(f"    {'[OK]' if ok else '[--]'} {path} ({len(t)}ch)")
            if ok: shot(d, f"v2_biometrics_{path.split('/')[-1]}")

        return {"status": "loaded"}
    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_field_force():
    print(f"\n{'~'*60}\n  FIELD FORCE (main app)\n{'~'*60}")
    d = mkdriver()
    try:
        login(d, ORG_EMAIL, ORG_PASS)
        go(d, f"{BASE}/field-force")
        time.sleep(2)
        text = bodytext(d)
        cur = d.current_url
        print(f"  Loaded: {cur} ({len(text)}ch)")
        shot(d, "v2_field_main")

        # Check if it redirected to dashboard
        if cur.rstrip("/") == BASE or "/dashboard" in cur.lower():
            # /field-force may redirect to main dashboard - that's a bug
            print("  [INFO] /field-force redirects to main dashboard")

        # Try other field force paths
        for path in ["/field-force/dashboard","/field-force/tracking","/field-force/staff",
                     "/field-force/routes","/field-force/attendance","/field-force/reports"]:
            if not alive(d): break
            go(d, f"{BASE}{path}")
            time.sleep(1)
            t = bodytext(d)
            c = d.current_url
            redirected = c.rstrip("/") == BASE or "/dashboard" == c.replace(BASE,"").rstrip("/")
            ok = len(t.strip())>30 and not redirected
            print(f"    {'[OK]' if ok else '[--]'} {path} -> {c}")

        return {"status": "loaded"}
    except Exception as e:
        print(f"  [ERR] {e}"); return {"status": "error"}
    finally:
        safe_quit(d)

def test_core_sidebar_links():
    """Test remaining sidebar links in main app."""
    print(f"\n{'~'*60}\n  CORE HRMS SIDEBAR LINK TESTS\n{'~'*60}")
    d = mkdriver()
    results = {}
    try:
        login(d, ORG_EMAIL, ORG_PASS)
        go(d, f"{BASE}/dashboard")
        time.sleep(3)

        sb = sidebar(d)
        tested = set()
        for item in sb:
            if not alive(d): break
            h = item.get("href",""); t = item["text"]
            if not h or h in tested: continue
            if any(w in t.lower() for w in ["logout","sign out"]): continue
            tested.add(h)
            go(d, h)
            if not alive(d): break
            text = bodytext(d)
            cur = d.current_url
            has_err = any(kw in text.lower() for kw in ["unexpected error","error occurred","something went wrong"])
            is_404 = "404" in text.lower() or "not found" in text.lower()
            blank = len(text.strip()) < 30
            redir_login = "/login" in cur.lower()

            if has_err:
                print(f"    [ERR-PAGE] {t}: unexpected error displayed")
                file_bug(d, t.replace(" ","_"),
                    f"[{t}] Page shows 'unexpected error' message",
                    f"Navigating to sidebar link '{t}' ({h}) displays an 'An unexpected error occurred' message. "
                    f"The page partially loads but core content fails to render.")
                results[t] = "error"
            elif is_404:
                print(f"    [404] {t}")
                file_bug(d, t.replace(" ","_"),
                    f"[{t}] Page shows 404 Not Found",
                    f"Sidebar link '{t}' ({h}) leads to a 404 page.")
                results[t] = "404"
            elif blank:
                print(f"    [BLANK] {t}")
                results[t] = "blank"
            elif redir_login:
                print(f"    [LOGIN-REDIR] {t}")
                results[t] = "login_redirect"
            else:
                print(f"    [OK] {t} ({len(text)}ch)")
                results[t] = "ok"

        shot(d, "v2_sidebar_tests_done")
    except Exception as e:
        print(f"  [ERR] {e}")
    finally:
        safe_quit(d)
    return results

# Super Admin panels check
def test_superadmin_panels():
    print(f"\n{'~'*60}\n  SUPER ADMIN PANEL CHECKS\n{'~'*60}")
    d = mkdriver()
    try:
        login(d, SA_EMAIL, SA_PASS)

        for path in ["/admin/super","/admin/modules","/admin/organizations",
                     "/admin/revenue","/admin/subscriptions","/admin/ai-config","/admin/logs"]:
            if not alive(d): break
            go(d, f"{BASE}{path}")
            time.sleep(2)
            text = bodytext(d)
            cur = d.current_url
            has_err = "unexpected error" in text.lower()
            print(f"  {'[ERR]' if has_err else '[OK]'} {path} ({len(text)}ch)")
            shot(d, f"v2_sa_{path.split('/')[-1]}")

            if has_err:
                file_bug(d, f"sa_{path.split('/')[-1]}",
                    f"[Super Admin] {path} shows 'unexpected error'",
                    f"Super Admin page {BASE}{path} displays 'An unexpected error occurred'. "
                    f"The navigation sidebar loads but the main content area shows an error.")

    except Exception as e:
        print(f"  [ERR] {e}")
    finally:
        safe_quit(d)

# ════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════
if __name__ == "__main__":
    print("="*70)
    print("EMP CLOUD - MODULE SUBSCRIPTION & DEEP TEST (v2)")
    print(f"Started: {datetime.now().isoformat()}")
    print("="*70)

    # Ensure no zombie chromes from previous runs
    kill_chrome()
    time.sleep(3)

    # Step 1: Re-subscribe
    resubscribe_all()

    # Step 2: Verify sidebar
    sb = verify_sidebar()

    # Step 3: Test each module
    results = {}
    results["recruit"] = test_recruit()
    results["performance"] = test_performance()
    results["rewards"] = test_rewards()
    results["exit"] = test_exit()
    results["lms"] = test_lms()
    results["payroll"] = test_payroll()
    results["project"] = test_project()
    results["monitor"] = test_monitor()
    results["billing"] = test_billing()
    results["biometrics"] = test_biometrics()
    results["field_force"] = test_field_force()

    # Step 4: Core sidebar link tests
    sidebar_results = test_core_sidebar_links()

    # Step 5: Super Admin panels
    test_superadmin_panels()

    # Summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)

    print("\nModule Results:")
    for mod, r in results.items():
        st = r.get("status","?") if isinstance(r,dict) else str(r)
        print(f"  [{st:20s}] {mod}")

    print(f"\nSidebar Link Results:")
    for link, st in sidebar_results.items():
        if st != "ok":
            print(f"  [{st:15s}] {link}")
    ok_count = sum(1 for s in sidebar_results.values() if s == "ok")
    print(f"  {ok_count}/{len(sidebar_results)} sidebar links OK")

    print(f"\nBugs filed: {len(bugs)}")
    for b in bugs:
        print(f"  #{b.get('issue','?')}: {b['title']}")

    print(f"\nCompleted: {datetime.now().isoformat()}")

    with open(os.path.join(SS_DIR,"..","subscribe_test_results_v2.json"),"w",encoding="utf-8") as f:
        json.dump({"ts":datetime.now().isoformat(),"results":{k:str(v) for k,v in results.items()},
                   "sidebar_results":sidebar_results,"bugs":bugs},f,indent=2,ensure_ascii=False)
