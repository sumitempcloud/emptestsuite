"""
EMP Cloud HRMS - Super Admin Full Dashboard E2E Test
Resilient version - recreates driver on crash
"""

import os, sys, time, json, traceback, requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *

BASE_URL = "https://test-empcloud.empcloud.com"
EMAIL = "admin@empcloud.com"
PASSW = "SuperAdmin@2026"
SS_DIR = r"C:\Users\Admin\screenshots\full_dashboard_superadmin"
GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"

os.makedirs(SS_DIR, exist_ok=True)
bugs = []
results = []
gh_issues = []
auth_token = None


def mk_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-extensions")
    opts.page_load_strategy = "normal"
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(3)
    return d


def ss(d, name):
    p = os.path.join(SS_DIR, f"{name}.png")
    try:
        d.save_screenshot(p)
        print(f"  [SS] {name}.png")
    except:
        print(f"  [SS] FAILED {name}.png")
        p = None
    return p


def log_r(phase, test, status, details=""):
    results.append({"phase": phase, "test": test, "status": status, "details": details})
    print(f"  [{status}] {phase} > {test}: {details}")


def log_bug(title, desc, sev, sp=None):
    bugs.append({"title": title, "desc": desc, "sev": sev, "ss": sp})
    print(f"  [BUG-{sev.upper()}] {title}")


def gh_issue(title, desc, sev, sp=None):
    if "rate limit" in title.lower() or "429" in title.lower():
        return None
    labels = ["bug", "super-admin", "e2e-test"]
    if sev == "critical": labels.append("critical")
    elif sev == "high": labels.append("high-priority")
    body = f"## Bug Report\n**Severity:** {sev}\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n### Description\n{desc}\n\n### Environment\n- URL: {BASE_URL}\n- Role: Super Admin\n- Browser: Chrome headless\n"
    if sp: body += f"\n### Screenshot\n`{sp}`\n"
    try:
        r = requests.post(f"https://api.github.com/repos/{GH_REPO}/issues",
            headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"},
            json={"title": f"[Super Admin E2E] {title}", "body": body, "labels": labels}, timeout=15)
        if r.status_code == 201:
            url = r.json().get("html_url", "")
            print(f"  [GH] {url}")
            gh_issues.append(url)
            return url
        else:
            print(f"  [GH] Failed: {r.status_code}")
    except Exception as e:
        print(f"  [GH] Error: {e}")
    return None


def safe_click(d, el):
    try:
        el.click()
    except:
        d.execute_script("arguments[0].click();", el)


def driver_ok(d):
    """Check if driver session is alive."""
    try:
        _ = d.current_url
        return True
    except:
        return False


def login(d):
    """Login and return (driver, success). May recreate driver if rate-limited."""
    d.get(f"{BASE_URL}/login")
    time.sleep(3)
    body = d.find_element(By.TAG_NAME, "body").text.lower()
    if "too many" in body or "try again later" in body:
        print("  Rate limited. Waiting 60s...")
        d.quit()
        time.sleep(60)
        d = mk_driver()
        d.get(f"{BASE_URL}/login")
        time.sleep(3)
        body = d.find_element(By.TAG_NAME, "body").text.lower()
        if "too many" in body:
            print("  Still rate limited. Waiting 90s more...")
            d.quit()
            time.sleep(90)
            d = mk_driver()
            d.get(f"{BASE_URL}/login")
            time.sleep(3)

    ef = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
    ef.clear(); ef.send_keys(EMAIL)
    pf = d.find_element(By.CSS_SELECTOR, "input[type='password']")
    pf.clear(); pf.send_keys(PASSW)
    time.sleep(0.5)

    for sel in ["button[type='submit']", "button"]:
        for b in d.find_elements(By.CSS_SELECTOR, sel):
            if b.is_displayed() and ("sign" in b.text.lower() or "log" in b.text.lower() or b.get_attribute("type") == "submit"):
                safe_click(d, b)
                break
        else:
            continue
        break
    time.sleep(5)

    if "/login" in d.current_url:
        return d, False
    return d, True


def get_or_fix_driver(d):
    """Return a working, logged-in driver. Recreate if session died."""
    if driver_ok(d):
        return d
    print("  [WARN] Driver session dead, recreating...")
    try:
        d.quit()
    except:
        pass
    d = mk_driver()
    d, ok = login(d)
    if not ok:
        print("  [WARN] Re-login failed")
    return d


def nav(d, path):
    """Navigate, return page info or None if login redirect."""
    d = get_or_fix_driver(d)
    try:
        d.get(f"{BASE_URL}{path}")
    except WebDriverException:
        d = get_or_fix_driver(d)
        try:
            d.get(f"{BASE_URL}{path}")
        except:
            return d, None
    time.sleep(3)
    try:
        cur = d.current_url
    except:
        d = get_or_fix_driver(d)
        return d, None
    if "/login" in cur:
        return d, None
    body = d.find_element(By.TAG_NAME, "body").text.strip()
    src = d.page_source
    return d, {"text": body, "source": src, "url": cur, "blank": len(body) < 20,
               "tl": body.lower(), "sl": src.lower()}


def main():
    print("=" * 70)
    print("EMP CLOUD HRMS - SUPER ADMIN FULL DASHBOARD E2E TEST")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    global auth_token
    d = mk_driver()

    try:
        # ============================================================
        # PHASE 1: LOGIN & SIDEBAR
        # ============================================================
        print("\n" + "=" * 70)
        print("PHASE 1: LOGIN & SIDEBAR")
        print("=" * 70)

        d, ok = login(d)
        ss(d, "01_login_page")
        if not ok:
            log_r("P1", "Login", "FAIL", "Could not login")
            return
        ss(d, "02_after_login")
        log_r("P1", "Login", "PASS", f"-> {d.current_url}")

        # Extract token
        try:
            ls = d.execute_script("var r={};for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);r[k]=localStorage.getItem(k);}return r;")
            for k, v in ls.items():
                if "token" in k.lower() or "auth" in k.lower():
                    auth_token = v
                    try:
                        p = json.loads(v)
                        if isinstance(p, dict):
                            auth_token = p.get("token") or p.get("access_token") or p.get("accessToken") or v
                    except: pass
                    break
            if not auth_token:
                for c in d.get_cookies():
                    if "token" in c["name"].lower():
                        auth_token = c["value"]; break
            print(f"  Token: {'yes' if auth_token else 'no'} (len={len(str(auth_token)) if auth_token else 0})")
        except Exception as e:
            print(f"  Token extraction error: {e}")

        # Sidebar
        print("\n  Mapping sidebar...")
        time.sleep(2)
        for sel in ["[class*='sidebar-toggle']", "button[aria-label*='menu']"]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            if els:
                try: safe_click(d, els[0]); time.sleep(1)
                except: pass
                break

        items = []
        seen = set()
        for sel in ["nav a", "aside a", "[class*='sidebar'] a", "[class*='Sidebar'] a",
                     "[class*='sidenav'] a", "[class*='drawer'] a", "[role='navigation'] a", "[class*='menu'] a"]:
            try:
                for el in d.find_elements(By.CSS_SELECTOR, sel):
                    try:
                        href = el.get_attribute("href") or ""
                        text = el.text.strip()
                        if not text:
                            for sp in el.find_elements(By.TAG_NAME, "span"):
                                if sp.text.strip(): text = sp.text.strip(); break
                        if text and href and href not in seen:
                            seen.add(href)
                            items.append({"text": text, "href": href})
                    except StaleElementReferenceException: continue
            except: continue

        if not items:
            # Fallback: all links
            for a in d.find_elements(By.TAG_NAME, "a")[:80]:
                try:
                    href = a.get_attribute("href") or ""
                    text = a.text.strip()
                    if text and BASE_URL in href and href not in seen:
                        seen.add(href); items.append({"text": text, "href": href})
                except: continue

        ss(d, "03_sidebar")
        admin_kw = ["/admin", "/super", "/system", "/config", "/logs", "/audit", "/module", "/org", "/revenue", "/billing", "/ai"]
        admin_items = []
        print(f"\n  Sidebar ({len(items)} items):")
        for it in items:
            path = it["href"].replace(BASE_URL, "")
            is_admin = any(kw in path.lower() for kw in admin_kw)
            print(f"    {'**' if is_admin else '  '} {it['text']}: {path}")
            if is_admin: admin_items.append(it)

        log_r("P1", "Sidebar", "PASS" if items else "WARN", f"{len(items)} total, {len(admin_items)} admin")
        if admin_items:
            print(f"\n  Admin-only sections ({len(admin_items)}):")
            for a in admin_items:
                print(f"    * {a['text']}: {a['href'].replace(BASE_URL,'')}")

        # ============================================================
        # PHASE 2A: SUPER ADMIN DASHBOARD
        # ============================================================
        print("\n" + "-" * 70)
        print("PHASE 2A: SUPER ADMIN DASHBOARD")
        print("-" * 70)

        dash_found = None
        for route in ["/admin/super", "/admin", "/admin/dashboard", "/super-admin"]:
            d, pg = nav(d, route)
            if not pg: continue
            ss(d, f"04_dash{route.replace('/','_')}")

            if pg["blank"]:
                log_r("P2A", f"Dash {route}", "FAIL", "BLANK")
                sp = ss(d, f"04_blank{route.replace('/','_')}")
                log_bug(f"Super Admin Dashboard blank at {route}", f"Page at {route} is blank. URL={pg['url']}", "critical", sp)
                gh_issue(f"Super Admin Dashboard blank at {route}", f"Page at {route} is blank. URL={pg['url']}", "critical", sp)
                continue

            checks = {
                "org_list": any(kw in pg["tl"] for kw in ["organization", "org", "companies", "technova", "globaltech"]),
                "user_counts": any(kw in pg["tl"] for kw in ["user", "users", "employees", "members"]),
                "revenue_stats": any(kw in pg["tl"] for kw in ["revenue", "billing", "subscription", "mrr"]),
                "system_health": any(kw in pg["tl"] for kw in ["health", "status", "uptime", "system", "server"]),
            }
            for n, ok in checks.items():
                log_r("P2A", f"{route} {n}", "PASS" if ok else "WARN", "Found" if ok else "Missing")
            if any(checks.values()):
                dash_found = route
                log_r("P2A", "Dashboard", "PASS", f"at {route}")
                break
        if not dash_found:
            log_r("P2A", "Dashboard", "FAIL", "No working dashboard")

        # ============================================================
        # PHASE 2B: AI CONFIGURATION
        # ============================================================
        print("\n" + "-" * 70)
        print("PHASE 2B: AI CONFIGURATION")
        print("-" * 70)

        ai_found = None
        for route in ["/admin/ai-config", "/admin/ai", "/settings/ai", "/admin/ai-providers", "/ai-config"]:
            d, pg = nav(d, route)
            if not pg: continue
            ss(d, f"05_ai{route.replace('/','_')}")
            if pg["blank"]: continue

            providers = {
                "claude": any(kw in pg["tl"] for kw in ["claude", "anthropic"]),
                "openai": any(kw in pg["tl"] for kw in ["openai", "gpt"]),
                "gemini": any(kw in pg["tl"] for kw in ["gemini", "google"]),
            }
            has_keys = any(kw in pg["sl"] for kw in ["api_key", "apikey", "api-key", "api key"])
            has_tog = any(kw in pg["sl"] for kw in ["toggle", "switch", "checkbox", "enable", "disable"])
            print(f"  Providers: {[k for k,v in providers.items() if v]}, Keys: {has_keys}, Toggle: {has_tog}")

            for p, ok in providers.items():
                log_r("P2B", f"Provider {p}", "PASS" if ok else "WARN", "")
            log_r("P2B", "API Keys", "PASS" if has_keys else "WARN", "")
            log_r("P2B", "Toggles", "PASS" if has_tog else "WARN", "")

            # Test toggles
            togs = d.find_elements(By.CSS_SELECTOR, "[role='switch'], input[type='checkbox'], [class*='toggle'], [class*='Switch']")
            if togs:
                print(f"  {len(togs)} toggle elements found")
                for i, t in enumerate(togs[:2]):
                    try:
                        b = t.get_attribute("aria-checked") or t.get_attribute("checked") or "?"
                        safe_click(d, t); time.sleep(1)
                        a = t.get_attribute("aria-checked") or t.get_attribute("checked") or "?"
                        print(f"    Toggle {i}: {b} -> {a}")
                        safe_click(d, t); time.sleep(0.5)
                    except: pass

            if any(providers.values()):
                ai_found = route
                log_r("P2B", "AI Config", "PASS", f"at {route}")
                break
        if not ai_found:
            log_r("P2B", "AI Config", "FAIL", "Not found")
            sp = ss(d, "05_ai_notfound")
            log_bug("AI Config page not found", "No AI config route loads properly.", "high", sp)
            gh_issue("AI Config page not found", "None of the expected routes load an AI config page.", "high", sp)

        # ============================================================
        # PHASE 2C: LOG DASHBOARD
        # ============================================================
        print("\n" + "-" * 70)
        print("PHASE 2C: LOG DASHBOARD")
        print("-" * 70)

        log_found = None
        for route in ["/admin/logs", "/logs", "/admin/log-dashboard", "/admin/system-logs"]:
            d, pg = nav(d, route)
            if not pg: continue
            ss(d, f"06_log{route.replace('/','_')}")
            if pg["blank"]: continue

            tabs = {
                "overview": any(kw in pg["tl"] for kw in ["overview", "summary", "dashboard"]),
                "errors": any(kw in pg["tl"] for kw in ["error", "errors", "exception"]),
                "slow_queries": any(kw in pg["tl"] for kw in ["slow", "query", "queries"]),
                "auth_events": any(kw in pg["tl"] for kw in ["auth", "login", "authentication"]),
            }
            has_entries = any(kw in pg["tl"] for kw in ["log", "entry", "timestamp", "level", "info", "warn"])
            print(f"  Tabs: {[k for k,v in tabs.items() if v]}, Entries: {has_entries}")

            for t, ok in tabs.items():
                log_r("P2C", f"Tab {t}", "PASS" if ok else "WARN", "")
            log_r("P2C", "Entries", "PASS" if has_entries else "WARN", "")

            # Click tabs
            tab_els = d.find_elements(By.CSS_SELECTOR, "[role='tab'], button[class*='tab'], [class*='Tab']")
            for te in tab_els[:5]:
                try:
                    txt = te.text.strip()
                    if txt:
                        safe_click(d, te); time.sleep(1)
                        ss(d, f"06_tab_{txt.lower().replace(' ','_')[:15]}")
                        print(f"    Clicked: {txt}")
                except: pass

            if has_entries or any(tabs.values()):
                log_found = route
                log_r("P2C", "Log Dashboard", "PASS", f"at {route}")
                break
        if not log_found:
            log_r("P2C", "Log Dashboard", "FAIL", "Not found")
            log_bug("Log Dashboard not found", "No log dashboard route works.", "medium")
            gh_issue("Log Dashboard not found", "Tried multiple routes.", "medium")

        # ============================================================
        # PHASE 2D: MODULE MANAGEMENT
        # ============================================================
        print("\n" + "-" * 70)
        print("PHASE 2D: MODULE MANAGEMENT")
        print("-" * 70)

        mod_found = None
        for route in ["/admin/modules", "/modules", "/admin/marketplace", "/admin/subscriptions", "/settings/modules"]:
            d, pg = nav(d, route)
            if not pg: continue
            ss(d, f"07_mod{route.replace('/','_')}")
            if pg["blank"]: continue

            has_mod = any(kw in pg["tl"] for kw in ["module", "marketplace", "plugin"])
            has_sub = any(kw in pg["tl"] for kw in ["subscribe", "subscription", "plan"])
            has_tog = any(kw in pg["tl"] for kw in ["enable", "disable", "activate"])
            print(f"  Modules: {has_mod}, Sub: {has_sub}, Toggle: {has_tog}")
            log_r("P2D", "Module List", "PASS" if has_mod else "WARN", "")
            log_r("P2D", "Subscription", "PASS" if has_sub else "WARN", "")

            if has_mod:
                mod_found = route
                log_r("P2D", "Module Mgmt", "PASS", f"at {route}")
                break
        if not mod_found:
            log_r("P2D", "Module Mgmt", "FAIL", "Not found")
            log_bug("Module Management not found", "No module mgmt route works.", "medium")
            gh_issue("Module Management not found", "Tried multiple routes.", "medium")

        # ============================================================
        # PHASE 2E: ORGANIZATION MANAGEMENT
        # ============================================================
        print("\n" + "-" * 70)
        print("PHASE 2E: ORG MANAGEMENT")
        print("-" * 70)

        org_found = None
        for route in ["/admin/organizations", "/admin/orgs", "/organizations", "/admin/tenants"]:
            d, pg = nav(d, route)
            if not pg: continue
            ss(d, f"08_org{route.replace('/','_')}")
            if pg["blank"]: continue

            known = {"technova": "technova" in pg["tl"], "globaltech": "globaltech" in pg["tl"]}
            has_list = any(kw in pg["tl"] for kw in ["organization", "company", "tenant"])
            has_users = any(kw in pg["tl"] for kw in ["users", "members", "employees"])
            print(f"  Orgs: {[k for k,v in known.items() if v]}, List: {has_list}, Users: {has_users}")
            for o, ok in known.items():
                log_r("P2E", f"Org {o}", "PASS" if ok else "WARN", "")
            log_r("P2E", "Org List", "PASS" if has_list else "WARN", "")
            log_r("P2E", "User Counts", "PASS" if has_users else "WARN", "")

            if has_list or any(known.values()):
                org_found = route
                log_r("P2E", "Org Mgmt", "PASS", f"at {route}")
                break
        if not org_found:
            log_r("P2E", "Org Mgmt", "FAIL", "Not found")

        # ============================================================
        # PHASE 2F: REVENUE/BILLING
        # ============================================================
        print("\n" + "-" * 70)
        print("PHASE 2F: REVENUE/BILLING")
        print("-" * 70)

        rev_found = None
        for route in ["/admin/revenue", "/admin/billing", "/admin/analytics", "/admin/subscriptions", "/billing"]:
            d, pg = nav(d, route)
            if not pg: continue
            ss(d, f"09_rev{route.replace('/','_')}")
            if pg["blank"]: continue

            has_rev = any(kw in pg["tl"] for kw in ["revenue", "income", "mrr", "arr"])
            has_bill = any(kw in pg["tl"] for kw in ["billing", "invoice", "payment", "subscription"])
            print(f"  Revenue: {has_rev}, Billing: {has_bill}")
            log_r("P2F", "Revenue", "PASS" if has_rev else "WARN", "")
            log_r("P2F", "Billing", "PASS" if has_bill else "WARN", "")
            if has_rev or has_bill:
                rev_found = route
                log_r("P2F", "Revenue Dash", "PASS", f"at {route}")
                break
        if not rev_found:
            log_r("P2F", "Revenue Dash", "WARN", "Not found")

        # ============================================================
        # PHASE 2G: AUDIT LOGS
        # ============================================================
        print("\n" + "-" * 70)
        print("PHASE 2G: AUDIT LOGS")
        print("-" * 70)

        aud_found = None
        for route in ["/admin/audit", "/audit", "/admin/audit-logs", "/audit-logs", "/admin/activity"]:
            d, pg = nav(d, route)
            if not pg: continue
            ss(d, f"10_aud{route.replace('/','_')}")
            if pg["blank"]: continue

            has_aud = any(kw in pg["tl"] for kw in ["audit", "activity", "action", "event"])
            has_ent = any(kw in pg["tl"] for kw in ["log", "entry", "timestamp", "user"])
            print(f"  Audit: {has_aud}, Entries: {has_ent}")
            log_r("P2G", "Audit Content", "PASS" if has_aud else "WARN", "")
            log_r("P2G", "Entries", "PASS" if has_ent else "WARN", "")
            if has_aud or has_ent:
                aud_found = route
                log_r("P2G", "Audit Logs", "PASS", f"at {route}")
                break
        if not aud_found:
            log_r("P2G", "Audit Logs", "FAIL", "Not found")

        # ============================================================
        # EXTRA ADMIN PAGES
        # ============================================================
        print("\n" + "-" * 70)
        print("EXTRA ADMIN PAGES")
        print("-" * 70)

        for route, name in [("/admin/settings", "Settings"), ("/admin/roles", "Roles"),
                             ("/admin/permissions", "Perms"), ("/settings", "Settings"),
                             ("/admin/notifications", "Notifs"), ("/admin/integrations", "Integ"),
                             ("/admin/security", "Security"), ("/admin/email-config", "EmailCfg"),
                             ("/admin/api-keys", "APIKeys")]:
            d, pg = nav(d, route)
            if pg and not pg["blank"]:
                print(f"  OK: {name} at {route} ({len(pg['text'])} chars)")
                ss(d, f"14{route.replace('/','_')}")
            elif pg and pg["blank"]:
                print(f"  BLANK: {name} at {route}")
                sp = ss(d, f"14{route.replace('/','_')}_blank")
                log_bug(f"{name} blank at {route}", f"{name} page is blank", "low", sp)
            else:
                print(f"  LOGIN: {route}")

        # ============================================================
        # PHASE 3: API TESTING
        # ============================================================
        print("\n" + "=" * 70)
        print("PHASE 3: API TESTING")
        print("=" * 70)

        if not auth_token:
            for ep in ["/api/v1/auth/login", "/api/auth/login"]:
                try:
                    r = requests.post(f"{BASE_URL}{ep}",
                        json={"email": EMAIL, "password": PASSW}, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        auth_token = data.get("token") or data.get("access_token")
                        if not auth_token and isinstance(data.get("data"), dict):
                            auth_token = data["data"].get("token") or data["data"].get("access_token")
                        if auth_token:
                            print(f"  Token via API {ep}"); break
                except: continue

        hdrs = {"Accept": "application/json", "Content-Type": "application/json"}
        if auth_token: hdrs["Authorization"] = f"Bearer {auth_token}"
        else: print("  [WARN] No auth token")

        for name, eps in [
            ("GET Users", ["/api/v1/users", "/api/users", "/api/v1/admin/users"]),
            ("GET Modules", ["/api/v1/modules", "/api/modules", "/api/v1/admin/modules"]),
            ("GET Audit", ["/api/v1/audit", "/api/audit", "/api/v1/audit-logs"]),
            ("GET Orgs", ["/api/v1/organizations", "/api/organizations", "/api/v1/orgs", "/api/v1/admin/organizations"]),
        ]:
            print(f"\n  {name}:")
            ok = False
            for ep in eps:
                try:
                    r = requests.get(f"{BASE_URL}{ep}", headers=hdrs, timeout=10)
                    if r.status_code == 429: print(f"    {ep}: 429 skip"); continue
                    print(f"    {ep}: {r.status_code}")
                    if r.status_code == 200:
                        data = r.json()
                        items = data if isinstance(data, list) else []
                        if isinstance(data, dict):
                            for k in ["data","users","modules","entries","organizations","results","logs","orgs"]:
                                if k in data and isinstance(data[k], list): items = data[k]; break
                        print(f"      {len(items)} items")
                        if items and isinstance(items[0], dict):
                            print(f"      Keys: {list(items[0].keys())[:8]}")
                        if "user" in name.lower() and items:
                            orgs_seen = set()
                            for it in items:
                                if isinstance(it, dict):
                                    org = it.get("organization") or it.get("orgId") or it.get("organizationId") or it.get("org")
                                    if org: orgs_seen.add(str(org)[:50])
                            if orgs_seen:
                                print(f"      Orgs: {orgs_seen}")
                                log_r("P3", "Cross-Org Users", "PASS" if len(orgs_seen)>1 else "WARN", f"{len(orgs_seen)} orgs")
                        log_r("P3", name, "PASS", f"{ep} -> {len(items)} items")
                        ok = True; break
                except Exception as e:
                    print(f"    {ep}: Error {e}")
            if not ok:
                log_r("P3", name, "FAIL", "No endpoint worked")

        # User info
        print("\n  Current User:")
        for ep in ["/api/v1/auth/me", "/api/v1/me", "/api/auth/me"]:
            try:
                r = requests.get(f"{BASE_URL}{ep}", headers=hdrs, timeout=10)
                if r.status_code == 429: continue
                if r.status_code == 200:
                    ud = r.json()
                    if isinstance(ud, dict) and "data" in ud: ud = ud["data"]
                    if isinstance(ud, dict):
                        role = ud.get("role") or ud.get("userRole") or ud.get("type") or "?"
                        email = ud.get("email") or "?"
                        print(f"    {ep}: email={email}, role={role}")
                        log_r("P3", "User Info", "PASS", f"email={email}, role={role}")
                    break
            except: continue

        # ============================================================
        # PHASE 4: CROSS-ORG VISIBILITY
        # ============================================================
        print("\n" + "=" * 70)
        print("PHASE 4: CROSS-ORG VISIBILITY")
        print("=" * 70)

        # Org switcher
        d = get_or_fix_driver(d)
        print("\n  Org switcher:")
        found_sw = False
        for sel in ["[class*='org-switch']", "[class*='OrgSwitch']", "[class*='tenant']",
                     "[class*='workspace']", "select[name*='org']"]:
            els = d.find_elements(By.CSS_SELECTOR, sel)
            if els:
                safe_click(d, els[0]); time.sleep(2)
                ss(d, "11_org_switch")
                log_r("P4", "Org Switcher", "PASS", f"via {sel}")
                found_sw = True; break
        if not found_sw:
            for btn in d.find_elements(By.TAG_NAME, "button"):
                t = btn.text.strip().lower()
                if any(kw in t for kw in ["switch", "organization", "workspace"]):
                    safe_click(d, btn); time.sleep(2)
                    ss(d, "11_switch_btn")
                    log_r("P4", "Org Switcher", "PASS", f"btn: {btn.text.strip()}")
                    found_sw = True; break
        if not found_sw:
            log_r("P4", "Org Switcher", "WARN", "Not found")

        # Multi-org check
        print("\n  Multi-org data:")
        for route in ["/admin/organizations", "/admin/super", "/admin"]:
            d, pg = nav(d, route)
            if not pg: continue
            orgs = [n for n in ["technova", "globaltech", "acme", "demo"] if n in pg["tl"]]
            if orgs:
                print(f"    {route}: {orgs}")
                log_r("P4", "Multi-Org", "PASS", f"{len(orgs)} orgs: {orgs}")
                ss(d, "12_multi_org"); break

        # Cross-org users
        for route in ["/admin/users", "/employees", "/admin/employees"]:
            d, pg = nav(d, route)
            if pg and not pg["blank"]:
                doms = set(n for n in ["technova", "globaltech", "empcloud", "acme"] if n in pg["tl"])
                if doms:
                    log_r("P4", "Cross-Org Users", "PASS" if len(doms)>1 else "WARN", f"{doms}")
                    ss(d, "13_cross_org"); break

    except Exception as e:
        print(f"\n[FATAL] {e}")
        traceback.print_exc()
        try: ss(d, "99_fatal")
        except: pass
    finally:
        try: d.quit()
        except: pass

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    pc = sum(1 for r in results if r["status"] == "PASS")
    fc = sum(1 for r in results if r["status"] == "FAIL")
    wc = sum(1 for r in results if r["status"] == "WARN")

    print(f"\nTotal: {len(results)}  |  PASS: {pc}  |  FAIL: {fc}  |  WARN: {wc}")
    print(f"Bugs: {len(bugs)}")
    for i, b in enumerate(bugs, 1):
        print(f"  {i}. [{b['sev'].upper()}] {b['title']}")

    print(f"\nGH Issues: {len(gh_issues)}")
    for u in gh_issues:
        print(f"  {u}")

    print("\n--- DETAILED ---")
    ph = None
    for r in results:
        if r["phase"] != ph:
            ph = r["phase"]
            print(f"\n  {ph}:")
        print(f"    [{r['status']}] {r['test']}: {r['details']}")

    print(f"\nScreenshots: {SS_DIR}")
    print(f"Done: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
