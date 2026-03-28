#!/usr/bin/env python3
"""EMP Cloud HRMS - Module Subscription & Testing"""
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
API1       = "https://test-empcloud.empcloud.com/api/v1"
API2       = "https://test-empcloud-api.empcloud.com/api/v1"
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
    return webdriver.Chrome(service=Service(cdpath()), options=o)

def alive(d):
    try: d.current_url; return True
    except: return False

def shot(d, name):
    try:
        p = os.path.join(SS_DIR, f"{re.sub(r'[^a-zA-Z0-9_-]','_',name)[:50]}_{TS}.png")
        d.save_screenshot(p); print(f"  [SS] {p}"); return p
    except: return None

def go(d, url):
    try:
        d.get(url)
        time.sleep(3)
        return True
    except Exception as e:
        print(f"  [NAV-ERR] {url}: {e}")
        return False

def login(d, email, pw, base=None):
    t = base or BASE
    print(f"  Login {email} at {t}...")
    if not go(d, f"{t}/login"): return False
    time.sleep(2)

    ef = None
    for s in ["input[name='email']","input[type='email']","#email","input[name='username']"]:
        try:
            e = d.find_element(By.CSS_SELECTOR, s)
            if e.is_displayed(): ef = e; break
        except: pass
    if not ef:
        try:
            for inp in d.find_elements(By.TAG_NAME, "input"):
                tp = (inp.get_attribute("type") or "").lower()
                if tp in ("email","text") and inp.is_displayed(): ef = inp; break
        except: pass
    if not ef: print("  [WARN] No email field"); return False
    ef.clear(); ef.send_keys(email); time.sleep(0.3)

    pf = None
    for s in ["input[name='password']","input[type='password']","#password"]:
        try:
            e = d.find_element(By.CSS_SELECTOR, s)
            if e.is_displayed(): pf = e; break
        except: pass
    if not pf: print("  [WARN] No pass field"); return False
    pf.clear(); pf.send_keys(pw); time.sleep(0.3)

    btn = None
    try:
        for b in d.find_elements(By.TAG_NAME, "button"):
            if b.is_displayed() and any(w in b.text.lower() for w in ["login","sign in","submit"]):
                btn = b; break
    except: pass
    if not btn:
        try: btn = d.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except: pass
    if btn:
        try: btn.click()
        except: d.execute_script("arguments[0].click();", btn)
    else:
        pf.send_keys(Keys.RETURN)

    time.sleep(5)
    ok = "/login" not in d.current_url.lower()
    print(f"  {'[OK]' if ok else '[??]'} -> {d.current_url}")
    return ok

def apicall(method, url, token=None, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type","application/json")
    req.add_header("User-Agent","EmpCloud-Test/1.0")
    req.add_header("Origin", BASE)
    if token: req.add_header("Authorization", f"Bearer {token}")
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        b = e.read().decode()[:200]
        print(f"  [API {e.code}] {method} ...{url[-40:]}: {b[:100]}")
        return {"_err": e.code}
    except Exception as e:
        print(f"  [API-ERR] {e}")
        return {"_err": str(e)}

def get_token(email, pw):
    for base in [API1, API2]:
        for ep in ["/auth/login","/auth/signin","/login"]:
            r = apicall("POST", f"{base}{ep}", data={"email":email,"password":pw})
            if "_err" not in r:
                for fn in [lambda: r.get("token"), lambda: r.get("access_token"),
                           lambda: (r.get("data") or {}).get("token"),
                           lambda: (r.get("data") or {}).get("access_token"),
                           lambda: (r.get("data") or {}).get("accessToken")]:
                    t = fn()
                    if t and isinstance(t,str) and len(t)>10:
                        print(f"  [TOKEN] from {base}{ep}")
                        return t
    return None

def upload_ss(fp, rn):
    try:
        with open(fp,"rb") as f: ct = base64.b64encode(f.read()).decode()
        url = f"https://api.github.com/repos/{GH_REPO}/contents/screenshots/{rn}"
        data = json.dumps({"message":f"Add {rn}","content":ct}).encode()
        req = urllib.request.Request(url,data=data,method="PUT")
        req.add_header("Authorization",f"token {GH_PAT}")
        req.add_header("Content-Type","application/json")
        req.add_header("User-Agent","EmpCloud-Test/1.0")
        urllib.request.urlopen(req, timeout=60)
        raw = f"https://raw.githubusercontent.com/{GH_REPO}/main/screenshots/{rn}"
        print(f"  [UP] {raw}")
        return raw
    except urllib.error.HTTPError as e:
        if e.code==422: return f"https://raw.githubusercontent.com/{GH_REPO}/main/screenshots/{rn}"
        print(f"  [UP-ERR] {e.code}"); return None
    except: return None

def gh_issue(title, body, labels=None):
    try:
        url = f"https://api.github.com/repos/{GH_REPO}/issues"
        data = json.dumps({"title":title,"body":body,"labels":labels or ["bug"]}).encode()
        req = urllib.request.Request(url,data=data,method="POST")
        req.add_header("Authorization",f"token {GH_PAT}")
        req.add_header("Content-Type","application/json")
        req.add_header("User-Agent","EmpCloud-Test/1.0")
        r = urllib.request.urlopen(req, timeout=30)
        n = json.loads(r.read().decode())["number"]
        print(f"  [ISSUE #{n}] {title}")
        return n
    except Exception as e:
        print(f"  [ISSUE-ERR] {e}"); return None

def bug(d, mod, title, desc):
    sn = f"module_{mod}_{TS}"
    sp = shot(d, sn)
    if not sp: return
    img = upload_ss(sp, f"{sn}.png")
    body = f"""## Bug: {mod}
**URL:** {d.current_url}
**Time:** {datetime.now().isoformat()}

## Description
{desc}

## Screenshot
![Screenshot]({img or 'N/A'})

## Env
Chrome headless 1920x1080, User: {ORG_EMAIL}
"""
    n = gh_issue(title, body, ["bug","module-testing"])
    bugs.append({"module":mod,"title":title,"issue":n})

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

def bodytext(d):
    try: return d.find_element(By.TAG_NAME, "body").text
    except: return ""

# ════════════════════════════════════════════════════
# PHASE 1
# ════════════════════════════════════════════════════
def phase1():
    print("\n"+"="*70+"\nPHASE 1: SUBSCRIBE TO ALL MODULES\n"+"="*70)
    subscribed = []; api_mods = []

    # A) Org Admin UI
    print("\n[1A] Org Admin UI...")
    d = mkdriver()
    try:
        login(d, ORG_EMAIL, ORG_PASS)
        shot(d, "p1_login")

        for path in ["/modules","/marketplace","/subscription","/subscriptions",
                     "/admin/modules","/settings/modules","/billing","/billing/modules",
                     "/marketplace/modules"]:
            if not alive(d): break
            url = f"{BASE}{path}"
            print(f"  Try {url}")
            go(d, url)
            if not alive(d): break
            cur = d.current_url.lower()
            if "/login" in cur:
                login(d, ORG_EMAIL, ORG_PASS)
                go(d, url)
            if not alive(d): break
            text = bodytext(d).lower()
            if any(kw in text for kw in ["module","subscribe","marketplace","subscription","plan","pricing"]):
                print(f"  [OK] Modules page: {url}")
                shot(d, "p1_modules_page")
                try:
                    for el in d.find_elements(By.CSS_SELECTOR, "button, a, [role='button']"):
                        try:
                            t = el.text.lower().strip()
                            if el.is_displayed() and any(w in t for w in ["subscribe","enable","activate","buy","try","start"]):
                                print(f"    Click: '{el.text.strip()}'")
                                try: el.click()
                                except: d.execute_script("arguments[0].click();", el)
                                time.sleep(3)
                                for cb in d.find_elements(By.CSS_SELECTOR, "button"):
                                    try:
                                        if cb.is_displayed() and any(w in cb.text.lower() for w in ["confirm","ok","yes","proceed"]):
                                            cb.click(); time.sleep(2); break
                                    except: pass
                                subscribed.append(el.text.strip())
                                shot(d, f"p1_sub_{len(subscribed)}")
                        except: pass
                except: pass
                break

        if alive(d):
            go(d, f"{BASE}/dashboard")
            time.sleep(2)
            sb = sidebar(d)
            for item in sb:
                if any(kw in item["text"].lower() for kw in ["module","marketplace","subscription","billing"]):
                    print(f"  Sidebar: {item['text']} -> {item['href']}")
                    if item["href"]: go(d, item["href"]); shot(d, "p1_sidebar_mod"); break

            text = bodytext(d)
            print(f"  Page text (500): {text[:500]}")
            shot(d, "p1_current")
    except Exception as e:
        print(f"  [ERR] {e}"); traceback.print_exc()
    finally:
        try: d.quit()
        except: pass

    # B) API
    print("\n[1B] API...")
    org_tok = get_token(ORG_EMAIL, ORG_PASS)
    sa_tok = get_token(SA_EMAIL, SA_PASS)

    for tok, lbl in [(org_tok,"Org"),(sa_tok,"SA")]:
        if not tok: continue
        for base in [API1, API2]:
            for ep in ["/modules","/modules/all","/modules/available","/marketplace",
                       "/marketplace/modules","/subscriptions","/organization/modules",
                       "/admin/modules","/tenant/modules"]:
                r = apicall("GET", f"{base}{ep}", tok)
                if "_err" not in r:
                    mods = r if isinstance(r,list) else None
                    if not mods and isinstance(r,dict):
                        for k in ["data","modules","items","results"]:
                            if isinstance(r.get(k), list): mods = r[k]; break
                    if mods:
                        print(f"  [{lbl}] {len(mods)} modules from {ep}")
                        api_mods = mods
                        for m in mods[:10]:
                            if isinstance(m,dict):
                                n = m.get("name") or m.get("title") or m.get("module_name") or str(m)[:60]
                                mid = m.get("id") or m.get("_id")
                                act = m.get("subscribed") or m.get("is_subscribed") or m.get("active") or m.get("enabled")
                                print(f"    {n} (id={mid} active={act})")
                            else: print(f"    {m}")
                        break
            if api_mods: break
        if api_mods: break

    # Subscribe via API
    if api_mods:
        for tok, lbl in [(org_tok,"Org"),(sa_tok,"SA")]:
            if not tok: continue
            for m in api_mods:
                if not isinstance(m,dict): continue
                mid = m.get("id") or m.get("_id") or m.get("module_id")
                mn = m.get("name") or m.get("title") or str(mid)
                act = m.get("subscribed") or m.get("is_subscribed") or m.get("active")
                if act: continue
                if not mid: continue
                print(f"  Sub {mn} as {lbl}...")
                for base in [API1, API2]:
                    ok = False
                    for ep, pay in [(f"/modules/{mid}/subscribe",{}),(f"/modules/{mid}/activate",{}),
                                    (f"/modules/{mid}/enable",{}),(f"/subscriptions",{"module_id":mid}),
                                    (f"/marketplace/{mid}/subscribe",{})]:
                        r = apicall("POST", f"{base}{ep}", tok, pay)
                        if "_err" not in r:
                            print(f"    [OK] {ep}"); subscribed.append(mn); ok=True; break
                    if ok: break

    # C) Super Admin UI
    print("\n[1C] Super Admin UI...")
    d = mkdriver()
    try:
        login(d, SA_EMAIL, SA_PASS)
        for path in ["/admin/super","/admin/modules","/admin/marketplace","/admin/subscriptions","/admin/organizations"]:
            if not alive(d): break
            go(d, f"{BASE}{path}")
            if not alive(d): break
            text = bodytext(d)
            cur = d.current_url
            if "/login" not in cur.lower() and len(text)>50:
                print(f"  [OK] {path} ({len(text)} chars)")
                shot(d, f"p1_sa_{path.split('/')[-1]}")
                if any(kw in text.lower() for kw in ["module","subscription","tenant"]):
                    print(f"    Content: {text[:300]}")
    except Exception as e:
        print(f"  [ERR] {e}")
    finally:
        try: d.quit()
        except: pass

    print(f"\n[P1 DONE] subscribed={subscribed} api={len(api_mods)}")
    return subscribed, api_mods

# ════════════════════════════════════════════════════
# PHASE 2
# ════════════════════════════════════════════════════
def phase2():
    print("\n"+"="*70+"\nPHASE 2: VERIFY SIDEBAR\n"+"="*70)
    d = mkdriver()
    sb_items = []; missing = []
    try:
        login(d, ORG_EMAIL, ORG_PASS)
        go(d, f"{BASE}/dashboard")
        time.sleep(3)

        # expand
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
        print(f"\n  Sidebar ({len(sb_items)}):")
        for i in sb_items: print(f"    {i['text']} -> {i['href']}")
        shot(d, "p2_sidebar")

        combined = " ".join(i["text"].lower() for i in sb_items) + " " + bodytext(d).lower()
        kws = {
            "Core HRMS":["hrms","dashboard","employee","attendance","leave"],
            "Monitoring":["monitor","monitoring","empmonitor"],
            "Rewards":["reward","recognition","kudos"],
            "Recruitment":["recruit","hiring","candidate","job"],
            "Billing":["billing","invoice","payment","subscription"],
            "Exit":["exit","offboard","separation"],
            "LMS":["lms","learning","course","training"],
            "Payroll":["payroll","salary","payslip"],
            "Performance":["performance","review","goal","appraisal"],
            "Project":["project","task","timesheet"],
            "Field Force":["field force","field tracking"],
            "Biometrics":["biometric","fingerprint","face"],
        }
        found = []
        print("\n  Module check:")
        for mod, ws in kws.items():
            p = any(w in combined for w in ws)
            print(f"    [{'OK' if p else 'MISS'}] {mod}")
            (found if p else missing).append(mod)

        if len(missing)>=2:
            sp = shot(d, "p2_missing")
            if sp:
                img = upload_ss(sp, f"p2_missing_{TS}.png")
                gh_issue(f"[Sidebar] {len(missing)} modules missing from sidebar",
                    f"""## Missing Modules
{chr(10).join(f'- [ ] {m}' for m in missing)}

## Found
{chr(10).join(f'- [x] {m}' for m in found)}

## Sidebar Items
{chr(10).join(f'- {i["text"]} ({i["href"]})' for i in sb_items)}

## Screenshot
![Screenshot]({img or 'N/A'})
""", ["bug","module-testing","sidebar"])
    except Exception as e:
        print(f"  [ERR] {e}"); traceback.print_exc()
    finally:
        try: d.quit()
        except: pass
    return sb_items, missing

# ════════════════════════════════════════════════════
# PHASE 3
# ════════════════════════════════════════════════════
def test_subdomain(mkey, murl):
    print(f"\n{'~'*50}\n  MODULE: {mkey} ({murl})\n{'~'*50}")
    res = {"module":mkey,"url":murl,"status":"unknown","issues":[],"features":[]}
    d = mkdriver()
    try:
        ok = go(d, murl)
        if not ok or not alive(d):
            res["status"]="unreachable"; res["issues"].append("unreachable")
            return res
        time.sleep(2)
        cur = d.current_url; text = bodytext(d)
        shot(d, f"p3_{mkey}_land")

        if any(kw in text.lower() for kw in ["404","not found","server error","500","503"]):
            res["status"]="error"; res["issues"].append("error page")
            bug(d, mkey, f"[{mkey}] Error on load", f"{murl} shows error.\nText: {text[:300]}")
            return res

        if len(text.strip())<20:
            res["status"]="blank"; res["issues"].append("blank")
            bug(d, mkey, f"[{mkey}] Blank page", f"{murl} blank.")
            return res

        if "/login" in cur.lower() or "sign in" in text.lower()[:300]:
            print(f"  -> login redirect, logging in...")
            login(d, ORG_EMAIL, ORG_PASS, base=murl)
            time.sleep(3)
            if not alive(d):
                res["status"]="driver_crash"; return res
            cur = d.current_url; text = bodytext(d)
            shot(d, f"p3_{mkey}_postlogin")
            if "/login" in cur.lower():
                res["status"]="login_failed"; res["issues"].append("login failed")
                bug(d, mkey, f"[{mkey}] Cannot login", f"Login with {ORG_EMAIL} fails at {murl}")
                return res

        res["status"]="loaded"
        print(f"  [OK] {cur}")
        print(f"  Text: {text[:200]}")

        mnav = sidebar(d)
        print(f"  Nav: {len(mnav)} items")
        for n in mnav[:8]: print(f"    - {n['text']}")

        # sub-pages
        fmap = {
            "rewards":     ["/badges","/kudos","/leaderboard","/dashboard"],
            "recruit":     ["/jobs","/candidates","/pipeline","/dashboard"],
            "exit":        ["/dashboard","/exits","/offboarding"],
            "lms":         ["/courses","/dashboard","/learning"],
            "payroll":     ["/dashboard","/payslips","/salary"],
            "performance": ["/dashboard","/reviews","/goals","/okrs"],
            "project":     ["/projects","/dashboard","/tasks","/boards"],
            "monitor":     ["/dashboard","/monitoring","/activity"],
        }
        for p in fmap.get(mkey, ["/dashboard"]):
            if not alive(d): break
            try:
                go(d, f"{murl}{p}")
                if not alive(d): break
                time.sleep(1)
                c = d.current_url; t = bodytext(d)
                ok = len(t.strip())>30 and "/login" not in c.lower() and not any(kw in t.lower() for kw in ["404","not found"])
                res["features"].append({"path":p,"ok":ok,"len":len(t)})
                print(f"    {'[OK]' if ok else '[--]'} {p} ({len(t)}ch)")
            except Exception as e:
                res["features"].append({"path":p,"ok":False})
                print(f"    [ERR] {p}: {e}")

        # nav click
        if alive(d):
            for n in mnav[:3]:
                if n["href"] and (murl in n["href"] or n["href"].startswith("/")):
                    href = n["href"] if n["href"].startswith("http") else f"{murl}{n['href']}"
                    go(d, href); time.sleep(1)
                    shot(d, f"p3_{mkey}_{n['text'][:10].replace(' ','_')}")
                    print(f"    Nav -> {n['text']}"); break

        # create btn
        if alive(d):
            try:
                for el in d.find_elements(By.CSS_SELECTOR, "button, a, [role='button']"):
                    try:
                        t = el.text.lower().strip()
                        if el.is_displayed() and any(w in t for w in ["add","create","new"]) and len(t)<30:
                            print(f"  Create: '{el.text.strip()}'")
                            try: el.click()
                            except: d.execute_script("arguments[0].click();", el)
                            time.sleep(3)
                            shot(d, f"p3_{mkey}_create")
                            res["features"].append({"action":"create","ok":True})
                            break
                    except: pass
            except: pass

    except Exception as e:
        res["status"]="exception"; res["issues"].append(str(e))
        print(f"  [ERR] {e}"); traceback.print_exc()
    finally:
        try: d.quit()
        except: pass
    return res

def test_main_modules():
    print(f"\n{'~'*50}\n  Main-app modules\n{'~'*50}")
    results = {}
    d = mkdriver()
    try:
        login(d, ORG_EMAIL, ORG_PASS)
        mods = {
            "billing":    ["/billing","/billing/dashboard","/settings/billing","/settings/subscription"],
            "biometrics": ["/biometrics","/biometric","/biometrics/devices","/settings/biometrics"],
            "field_force":["/field-force","/field","/fieldforce","/emp-field"],
            "core_hrms":  ["/dashboard","/employees","/attendance","/leave","/documents"],
        }
        for mod, paths in mods.items():
            if not alive(d): break
            print(f"\n  {mod}:")
            found = False
            for p in paths:
                if not alive(d): break
                url = f"{BASE}{p}"
                go(d, url)
                if not alive(d): break
                cur = d.current_url
                if "/login" in cur.lower():
                    login(d, ORG_EMAIL, ORG_PASS)
                    go(d, url)
                if not alive(d): break
                text = bodytext(d)
                ok = len(text.strip())>50 and "/login" not in d.current_url.lower() and not any(kw in text.lower() for kw in ["404","not found"])
                if ok:
                    print(f"    [OK] {p} ({len(text)}ch)")
                    shot(d, f"p3_{mod}_{p.strip('/').replace('/','_')}")
                    results[mod] = {"module":mod,"url":url,"status":"loaded","features":[],"issues":[]}
                    found = True; break
                else:
                    print(f"    [--] {p}")
            if not found:
                results[mod] = {"module":mod,"url":"N/A","status":"not_found","features":[],"issues":[]}

        # Test sidebar links
        if alive(d):
            print("\n  Sidebar link tests...")
            go(d, f"{BASE}/dashboard")
            time.sleep(2)
            if alive(d):
                sb = sidebar(d)
                tested = set()
                for item in sb:
                    if not alive(d): break
                    h = item.get("href",""); t = item["text"]
                    if not h or h in tested: continue
                    if any(w in t.lower() for w in ["logout","profile","notification","setting","help"]): continue
                    tested.add(h)
                    try:
                        go(d, h)
                        if not alive(d): break
                        text = bodytext(d)
                        has_err = any(kw in text.lower() for kw in ["404","not found","error occurred","something went wrong"])
                        blank = len(text.strip())<30
                        if has_err:
                            print(f"    [BUG] {t}: error")
                            bug(d, t.replace(" ","_"), f"[Sidebar] '{t}' shows error", f"'{t}' -> {d.current_url}\nText: {text[:300]}")
                        elif blank:
                            print(f"    [BUG] {t}: blank")
                            bug(d, t.replace(" ","_"), f"[Sidebar] '{t}' blank", f"'{t}' -> {d.current_url}")
                        else:
                            print(f"    [OK] {t} ({len(text)}ch)")
                    except Exception as e:
                        print(f"    [ERR] {t}: {e}")

        shot(d, "p3_final")
    except Exception as e:
        print(f"  [ERR] {e}"); traceback.print_exc()
    finally:
        try: d.quit()
        except: pass
    return results

def phase3():
    print("\n"+"="*70+"\nPHASE 3: TEST EACH MODULE\n"+"="*70)
    results = {}
    for mkey, murl in SUBDOMAINS.items():
        results[mkey] = test_subdomain(mkey, murl)
    results.update(test_main_modules())
    return results

# ════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════
if __name__ == "__main__":
    print("="*70+f"\nEMP CLOUD - MODULE TEST\n{datetime.now().isoformat()}\n"+"="*70)

    sub, api_m = phase1()
    print(f"\n[P1] sub={sub} api={len(api_m)}")

    sb, miss = phase2()
    print(f"\n[P2] sidebar={len(sb)} miss={miss}")

    res = phase3()

    print("\n"+"="*70+"\nSUMMARY\n"+"="*70)
    for n, r in res.items():
        st = r.get("status","?")
        feat = r.get("features",[])
        ok_f = sum(1 for f in feat if f.get("ok"))
        iss = r.get("issues",[])
        print(f"  [{st:15s}] {n:20s} feat:{ok_f}/{len(feat)} issues:{len(iss)}  {r.get('url','')[:50]}")

    print(f"\nBugs: {len(bugs)}")
    for b in bugs: print(f"  #{b.get('issue','?')}: {b['title']}")
    print(f"\nDone: {datetime.now().isoformat()}")

    with open(os.path.join(SS_DIR,"..","subscribe_test_results.json"),"w",encoding="utf-8") as f:
        json.dump({"ts":datetime.now().isoformat(),"sub":sub,"api":len(api_m),"sidebar":sb,
                   "miss":miss,"res":{k:str(v)[:500] for k,v in res.items()},"bugs":bugs},f,indent=2)
