#!/usr/bin/env python3
"""
EMP Cloud HRMS - Full Dashboard E2E Test (Org Admin)
Complete walkthrough of all modules.
"""

import sys, os, time, json, traceback, urllib.request, urllib.parse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCREENSHOTS_DIR = r"C:\Users\Admin\screenshots\full_dashboard"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

BASE_URL = "https://test-empcloud.empcloud.com"
LOGIN_EMAIL = "ananya@technova.in"
LOGIN_PASS = "Welcome@123"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

test_results = []
bugs_found = []
pages_tested = []
sidebar_links = []

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def add_result(mod, name, status, details=""):
    test_results.append({"module":mod,"test":name,"status":status,"details":details})
    log(f"  [{status}] {mod} > {name}: {details}")

def add_bug(title, severity, steps, module):
    bugs_found.append({"title":title,"severity":severity,"steps":steps,"module":module})

def ss(driver, name):
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:100]
    p = os.path.join(SCREENSHOTS_DIR, f"{safe}.png")
    try: driver.save_screenshot(p); return p
    except: return ""

def file_github_issue(title, body, labels=None):
    try:
        import ssl
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        payload = {"title": title, "body": body}
        if labels: payload["labels"] = labels
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Authorization', f'token {GITHUB_PAT}')
        req.add_header('Accept', 'application/vnd.github.v3+json')
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'EmpCloud-E2E-Test')
        ctx = ssl._create_unverified_context()
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        result = json.loads(resp.read().decode('utf-8'))
        log(f"  [GITHUB] Issue #{result['number']}: {title}")
        return result.get('number')
    except Exception as e:
        log(f"  [GITHUB] Failed: {e}")
        return None

def setup_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    opts = webdriver.ChromeOptions()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    opts.page_load_strategy = 'eager'  # Don't wait for all resources
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    svc = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.set_page_load_timeout(120)  # Very generous to avoid killing connection
    driver.implicitly_wait(5)
    return driver

def get_js_errors(driver):
    try:
        return [l for l in driver.get_log("browser") if l.get("level") == "SEVERE"]
    except:
        return []

def wait_ready(driver, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        try:
            state = driver.execute_script("return document.readyState")
            if state in ("complete", "interactive"):
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def get_text(driver, maxlen=2000):
    try:
        return driver.execute_script("return document.body ? document.body.innerText.substring(0, arguments[0]) : ''", maxlen)
    except:
        return ""

def has_content(driver, minlen=30):
    return len(get_text(driver, 200).strip()) >= minlen

def go(driver, path, wait=4):
    """Navigate to a path. With page_load_strategy='none', driver.get returns immediately."""
    url = f"{BASE_URL}{path}" if path.startswith("/") else path
    try:
        driver.get(url)
    except Exception as e:
        log(f"    Navigation error for {path}: {str(e)[:50]}")
    time.sleep(wait)
    wait_ready(driver, timeout=8)
    return True

def click_el(driver, selectors, text_match=""):
    """Click element by CSS selectors or text."""
    from selenium.webdriver.common.by import By
    for sel in selectors:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});arguments[0].click();", el)
                    time.sleep(0.5)
                    return True
        except: continue
    if text_match:
        for tag in ["button","a","span","div","li"]:
            try:
                els = driver.find_elements(By.XPATH, f"//{tag}[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{text_match.lower()}')]")
                for el in els:
                    if el.is_displayed():
                        driver.execute_script("arguments[0].click();", el)
                        time.sleep(0.5)
                        return True
            except: continue
    return False

def check_els(driver, selectors):
    from selenium.webdriver.common.by import By
    found = []
    for sel in selectors:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed():
                    found.append(sel)
                    break
        except: continue
    return found

def find_sidebar_link(keywords):
    for sl in sidebar_links:
        h = sl.get("href","").lower()
        t = sl.get("text","").lower()
        for kw in keywords:
            if kw in h or kw in t:
                return sl
    return None

# ═══════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════
def do_login(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    log("Opening login page...")
    driver.get(f"{BASE_URL}/login")
    # With page_load_strategy='none', driver.get returns immediately
    # Wait for the page to actually render
    time.sleep(8)
    wait_ready(driver, timeout=15)
    ss(driver, "01_login_page")
    log(f"  URL: {driver.current_url}, Title: {driver.title}")

    # Wait for email input
    email_el = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email']"))
    )
    email_el.clear()
    email_el.send_keys(LOGIN_EMAIL)
    time.sleep(0.3)

    pwd_el = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
    pwd_el.clear()
    pwd_el.send_keys(LOGIN_PASS)
    time.sleep(0.3)

    ss(driver, "02_login_filled")

    # Click Sign in
    btn = driver.find_element(By.XPATH, "//button[contains(text(),'Sign in')]")
    driver.execute_script("arguments[0].click();", btn)
    log("  Clicked Sign in, waiting...")

    # Wait for redirect (max 20s)
    for i in range(20):
        time.sleep(1)
        if "/login" not in driver.current_url:
            break

    time.sleep(2)
    ss(driver, "03_after_login")
    log(f"  URL: {driver.current_url}")

    if "too many" in get_text(driver, 300).lower():
        log("  Rate limited, waiting 90s...")
        time.sleep(90)
        driver.get(f"{BASE_URL}/login")
        time.sleep(8)
        wait_ready(driver, timeout=15)
        el = driver.find_element(By.CSS_SELECTOR, "input[name='email']")
        el.clear(); el.send_keys(LOGIN_EMAIL)
        el2 = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        el2.clear(); el2.send_keys(LOGIN_PASS)
        driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//button[contains(text(),'Sign in')]"))
        for i in range(20):
            time.sleep(1)
            if "/login" not in driver.current_url: break
        time.sleep(2)
        ss(driver, "03b_retry")
        log(f"  URL after retry: {driver.current_url}")

    ok = "/login" not in driver.current_url
    log(f"  Login {'SUCCESS' if ok else 'FAILED'}")
    return ok

# ═══════════════════════════════════════════════════
# PHASE 1: SIDEBAR MAPPING
# ═══════════════════════════════════════════════════
def phase1_sidebar(driver):
    from selenium.webdriver.common.by import By

    log("=" * 60)
    log("PHASE 1: SIDEBAR MAPPING")
    log("=" * 60)

    # We should already be on dashboard after login
    time.sleep(3)
    wait_ready(driver)
    ss(driver, "04_dashboard")
    log(f"  On: {driver.current_url}")

    # Use JS to find all links and clickable nav items
    log("  Collecting all navigation elements via JS...")
    links_data = driver.execute_script("""
        var results = [];
        var seen = new Set();

        // Get all <a> tags
        document.querySelectorAll('a').forEach(function(a) {
            var href = a.getAttribute('href') || a.href || '';
            var text = (a.innerText || a.textContent || '').trim();
            if (!text || text.length > 60) return;
            if (seen.has(text + href)) return;
            seen.add(text + href);

            // Check if it's a nav/sidebar link
            var el = a;
            var isSidebar = false;
            for (var i = 0; i < 10; i++) {
                el = el.parentElement;
                if (!el) break;
                var cls = (el.className || '').toLowerCase();
                var tag = el.tagName.toLowerCase();
                if (cls.includes('sidebar') || cls.includes('side-nav') || cls.includes('nav') ||
                    cls.includes('menu') || tag === 'aside' || tag === 'nav') {
                    isSidebar = true;
                    break;
                }
            }

            if (href && !href.includes('logout') && !href.includes('javascript:') &&
                !href.startsWith('#') && !href.includes('mailto:') && !href.includes('register')) {
                results.push({
                    text: text.substring(0, 50),
                    href: href,
                    fullHref: a.href,
                    isSidebar: isSidebar,
                    visible: a.offsetParent !== null
                });
            }
        });

        return results;
    """)

    log(f"  JS found {len(links_data or [])} links")

    for ld in (links_data or []):
        href = ld.get("fullHref") or ld.get("href", "")
        text = ld.get("text", "")
        if not text or not href:
            continue
        sidebar_links.append({
            "text": text,
            "href": href,
            "isSidebar": ld.get("isSidebar", False),
            "visible": ld.get("visible", False)
        })
        marker = "S" if ld.get("isSidebar") else " "
        vis = "V" if ld.get("visible") else "H"
        log(f"    [{marker}{vis}] {text:<35} -> {href}")

    # Also try to expand collapsed sidebar sections
    log("  Attempting to expand sidebar sections...")
    try:
        expanded = driver.execute_script("""
            var count = 0;
            document.querySelectorAll('[aria-expanded="false"]').forEach(function(el) {
                try { el.click(); count++; } catch(e) {}
            });
            // Also try elements with chevron/arrow classes
            document.querySelectorAll('[class*="chevron"], [class*="arrow"], [class*="expand"], [class*="collapse"]').forEach(function(el) {
                try { el.click(); count++; } catch(e) {}
            });
            return count;
        """)
        log(f"  Clicked {expanded} expandable elements")
    except:
        pass

    time.sleep(2)

    # Re-collect after expansion
    links_data2 = driver.execute_script("""
        var results = [];
        var seen = new Set();
        document.querySelectorAll('a').forEach(function(a) {
            var href = a.href || '';
            var text = (a.innerText || '').trim();
            if (!text || text.length > 60 || seen.has(href)) return;
            seen.add(href);
            if (href && !href.includes('logout') && !href.includes('javascript:') &&
                !href.startsWith('#') && !href.includes('register')) {
                results.push({text: text.substring(0, 50), href: href});
            }
        });
        return results;
    """)

    existing_hrefs = set(sl.get("href","") for sl in sidebar_links)
    new_count = 0
    for ld in (links_data2 or []):
        if ld["href"] not in existing_hrefs:
            sidebar_links.append({"text": ld["text"], "href": ld["href"], "isSidebar": False, "visible": True})
            new_count += 1
            log(f"    [NEW] {ld['text']:<35} -> {ld['href']}")

    log(f"  Found {new_count} new links after expansion. Total: {len(sidebar_links)}")

    # Take expanded screenshot
    try:
        h = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, min(h + 100, 6000))
        time.sleep(0.5)
        ss(driver, "05_sidebar_full")
        driver.set_window_size(1920, 1080)
    except:
        pass

    ss(driver, "06_sidebar_final")
    add_result("Phase 1", "Sidebar Mapping", "PASS" if sidebar_links else "FAIL", f"Found {len(sidebar_links)} links")
    return sidebar_links

# ═══════════════════════════════════════════════════
# PHASE 2: TEST EVERY PAGE
# ═══════════════════════════════════════════════════
def phase2_pages(driver):
    from selenium.webdriver.common.by import By

    log("=" * 60)
    log("PHASE 2: TEST EVERY PAGE")
    log("=" * 60)

    seen = set()
    unique = []
    for sl in sidebar_links:
        href = sl.get("href","")
        if href and href not in seen and BASE_URL in href:
            seen.add(href)
            unique.append({"text": sl.get("text",""), "href": href})

    log(f"  Testing {len(unique)} unique internal pages...")

    for i, lnk in enumerate(unique):
        href = lnk["href"]
        text = lnk["text"]
        log(f"  [{i+1}/{len(unique)}] {text} -> {href}")

        res = {"url":href,"text":text,"status":"UNKNOWN","title":"","heading":"","errors":[]}
        try:
            go(driver, href, wait=4)
            cur = driver.current_url
            body = get_text(driver, 500)
            res["title"] = driver.execute_script("return document.title") or ""

            # Get heading
            heading = driver.execute_script("""
                var h = document.querySelector('h1, h2, .page-title, [class*="heading"]');
                return h ? h.innerText.trim().substring(0, 80) : '';
            """) or ""
            res["heading"] = heading

            is_404 = "404" in body[:300] or "not found" in body.lower()[:300]
            is_blank = len(body.strip()) < 20
            is_login = "/login" in cur

            toasts = driver.execute_script("""
                var t = [];
                document.querySelectorAll('.toast-error, [class*="Toastify__toast--error"], [class*="alert-danger"]').forEach(function(el){
                    if(el.offsetParent !== null) t.push(el.innerText.substring(0,80));
                });
                return t;
            """) or []

            js_errs = get_js_errors(driver)

            if is_login:
                res["status"] = "REDIRECT_LOGIN"
                add_result("Phase 2", text, "FAIL", f"Redirected to login")
                add_bug(f"[Auth] {text} redirects to login", "critical",
                    f"1. Login as Org Admin\n2. Navigate to {href}\n3. Redirected to login", "Auth")
            elif is_404:
                res["status"] = "404"
                add_result("Phase 2", text, "FAIL", f"404")
                add_bug(f"[404] {text} not found", "high",
                    f"1. Login as Org Admin\n2. Navigate to {href}\n3. 404", "Navigation")
            elif is_blank:
                res["status"] = "BLANK"
                add_result("Phase 2", text, "FAIL", f"Blank page")
                add_bug(f"[Blank] {text} empty", "high",
                    f"1. Login as Org Admin\n2. Navigate to {href}\n3. Blank", "Navigation")
            elif toasts:
                res["status"] = "TOAST_ERROR"
                add_result("Phase 2", text, "WARN", f"Toasts: {toasts}")
            else:
                res["status"] = "OK"
                add_result("Phase 2", text, "PASS", f"Heading: {heading}")

            if js_errs:
                res["errors"] = [e.get("message","")[:80] for e in js_errs[:3]]

            ss(driver, f"p2_{i+1:02d}_{text[:20]}")

        except Exception as e:
            res["status"] = "EXCEPTION"
            add_result("Phase 2", text, "FAIL", str(e)[:100])
            ss(driver, f"p2_{i+1:02d}_error")

        pages_tested.append(res)

    ok = sum(1 for p in pages_tested if p["status"]=="OK")
    fail = sum(1 for p in pages_tested if p["status"] in ("404","BLANK","REDIRECT_LOGIN","EXCEPTION"))
    log(f"  Phase 2: {ok} OK, {fail} Failed / {len(pages_tested)} total")

# ═══════════════════════════════════════════════════
# PHASE 3: DEEP MODULE TESTS
# ═══════════════════════════════════════════════════

def navigate_to(driver, keywords, fallback_paths):
    """Try sidebar link, then fallback paths."""
    sl = find_sidebar_link(keywords)
    if sl:
        go(driver, sl["href"])
        if has_content(driver): return True
    for p in fallback_paths:
        go(driver, p)
        if has_content(driver): return True
    return False

def test_A_dashboard(driver):
    log("\n--- A) Dashboard ---")
    go(driver, "/dashboard")
    # If /dashboard redirects, try /
    if not has_content(driver):
        go(driver, "/")
    ss(driver, "p3A_dashboard")
    text = get_text(driver)

    if len(text.strip()) > 50:
        add_result("Dashboard", "Page loads", "PASS", f"{len(text)} chars")
    else:
        add_result("Dashboard", "Page loads", "FAIL", "Empty")
        add_bug("[Dashboard] Empty", "high", "1. Login\n2. Dashboard is empty", "Dashboard")
        return

    # Widgets
    w = check_els(driver, ["[class*='card']","[class*='widget']","[class*='stat']",".card","[class*='tile']","[class*='metric']"])
    add_result("Dashboard", "Widgets", "PASS" if w else "WARN", str(w[:3]))

    # Stats keywords
    for kw in ["employee","attendance","leave","present","absent"]:
        if kw in text.lower():
            add_result("Dashboard", f"Stats: {kw}", "PASS", "Found on dashboard")

    # Check welcome message
    if "welcome" in text.lower():
        add_result("Dashboard", "Welcome message", "PASS", "Present")

    # Module insights section
    if "module" in text.lower() or "insight" in text.lower():
        add_result("Dashboard", "Module Insights", "PASS", "Present")

def test_B_employees(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    log("\n--- B) Employee Directory ---")

    loaded = navigate_to(driver, ["employee","people","directory"],
                        ["/employees","/employee","/employee-directory"])
    ss(driver, "p3B_employees")
    if not loaded:
        add_result("Employees", "Page load", "FAIL", "Not accessible")
        add_bug("[Employees] Not accessible", "critical", "1. Login\n2. Go to employees\n3. Not found", "Employees")
        return

    add_result("Employees", "Page load", "PASS", "Loaded")
    text = get_text(driver)

    # Table/list
    tbl = check_els(driver, ["table","[class*='table']","[class*='list']","[class*='grid']","[class*='card']"])
    add_result("Employees", "List visible", "PASS" if tbl else "WARN", str(tbl[:2]))

    # Check for employee names in text
    if "ananya" in text.lower() or "technova" in text.lower():
        add_result("Employees", "Employee data visible", "PASS", "Names found in list")

    # Search
    search_done = False
    try:
        inp = driver.execute_script("""
            var inputs = document.querySelectorAll("input[type='search'], input[placeholder*='earch'], input[class*='search'], [class*='search'] input");
            for(var i=0; i<inputs.length; i++){
                if(inputs[i].offsetParent !== null) return inputs[i];
            }
            return null;
        """)
        if inp:
            inp.clear()
            inp.send_keys("ananya")
            time.sleep(2)
            ss(driver, "p3B_search")
            add_result("Employees", "Search", "PASS", "Typed search term")
            inp.clear()
            time.sleep(1)
            search_done = True
    except:
        pass
    if not search_done:
        add_result("Employees", "Search", "WARN", "No search input found")

    # Department filter
    filters = check_els(driver, ["select","[class*='filter']","[class*='dropdown']"])
    add_result("Employees", "Filters", "PASS" if filters else "WARN", str(filters[:2]))

    # Click first employee
    try:
        clicked = driver.execute_script("""
            var rows = document.querySelectorAll("table tbody tr, [class*='employee-card'], [class*='list-item'], [class*='emp-row'], [class*='emp-card']");
            for(var i=0; i<rows.length; i++){
                if(rows[i].offsetParent !== null && rows[i].innerText.trim().length > 5){
                    rows[i].click();
                    return true;
                }
            }
            return false;
        """)
        if clicked:
            time.sleep(3)
            ss(driver, "p3B_profile")
            add_result("Employees", "Click employee -> profile", "PASS", "Profile opened")

            # Profile tabs
            tabs_clicked = 0
            for tab in ["Personal","Education","Experience","Documents","Address","Attendance","Leave","Assets","Custom"]:
                try:
                    t = driver.execute_script(f"""
                        var els = document.querySelectorAll('button, a, [role="tab"], li');
                        for(var i=0; i<els.length; i++){{
                            if(els[i].innerText.trim().includes('{tab}') && els[i].offsetParent !== null){{
                                els[i].click(); return true;
                            }}
                        }}
                        return false;
                    """)
                    if t:
                        time.sleep(1.5)
                        ss(driver, f"p3B_tab_{tab}")
                        tabs_clicked += 1
                except:
                    pass
            add_result("Employees", "Profile tabs", "PASS" if tabs_clicked > 0 else "WARN", f"{tabs_clicked} tabs")

            go(driver, "/employees")  # Navigate back to list
        else:
            add_result("Employees", "Click employee", "WARN", "No clickable row found")
    except Exception as e:
        add_result("Employees", "Click employee", "WARN", str(e)[:80])

    # Add Employee
    go(driver, "/employees")
    time.sleep(1)
    add_ok = click_el(driver, ["button[class*='add']","a[class*='add']","[class*='create']","button.btn-primary"], "add employee")
    time.sleep(2)
    ss(driver, "p3B_add_emp")
    add_result("Employees", "Add Employee", "PASS" if add_ok else "WARN", "Form opened" if add_ok else "Button not found")

def test_C_attendance(driver):
    log("\n--- C) Attendance ---")
    loaded = navigate_to(driver, ["attendance"], ["/attendance"])
    ss(driver, "p3C_attendance")
    if not loaded:
        add_result("Attendance", "Page load", "FAIL", "Not accessible")
        return
    text = get_text(driver)
    add_result("Attendance", "Page load", "PASS", f"{len(text)} chars")

    for kw in ["present","absent","late","check-in","check-out","on time","total"]:
        if kw in text.lower():
            add_result("Attendance", f"Stats: {kw}", "PASS", "Found")
            break

    dates = check_els(driver, ["input[type='date']","[class*='date']","[class*='calendar']","[class*='picker']"])
    add_result("Attendance", "Date filter", "PASS" if dates else "WARN", str(dates[:2]))

    # Shifts
    sl = find_sidebar_link(["shift"])
    if sl:
        go(driver, sl["href"])
        ss(driver, "p3C_shifts")
        add_result("Attendance", "Shifts page", "PASS" if has_content(driver) else "FAIL", "")

    # Regularization
    sl = find_sidebar_link(["regular"])
    if sl:
        go(driver, sl["href"])
        ss(driver, "p3C_regularization")
        add_result("Attendance", "Regularization", "PASS" if has_content(driver) else "FAIL", "")

def test_D_leave(driver):
    log("\n--- D) Leave Management ---")
    loaded = navigate_to(driver, ["leave"], ["/leave","/leaves"])
    ss(driver, "p3D_leave")
    if not loaded:
        add_result("Leave", "Page load", "FAIL", "Not accessible")
        return
    text = get_text(driver)
    add_result("Leave", "Page load", "PASS", f"{len(text)} chars")

    for kw in ["balance","available","taken","pending","approved","casual","sick","earned"]:
        if kw in text.lower():
            add_result("Leave", f"Info: {kw}", "PASS", "Found")

    apply = click_el(driver, ["button[class*='apply']","a[class*='apply']"], "apply leave")
    if not apply: apply = click_el(driver, [], "apply")
    time.sleep(2)
    ss(driver, "p3D_apply")
    add_result("Leave", "Apply Leave", "PASS" if apply else "WARN", "Form" if apply else "Not found")

    # Calendar
    sl = find_sidebar_link(["calendar"])
    if sl:
        go(driver, sl["href"])
        ss(driver, "p3D_calendar")
        add_result("Leave", "Calendar", "PASS" if has_content(driver) else "WARN", "")

    # Leave types
    sl = find_sidebar_link(["leave-type","leave type"])
    if sl:
        go(driver, sl["href"])
        ss(driver, "p3D_types")
        add_result("Leave", "Leave types", "PASS" if has_content(driver) else "WARN", "")

    # Comp-off
    sl = find_sidebar_link(["comp-off","compoff"])
    if sl:
        go(driver, sl["href"])
        ss(driver, "p3D_compoff")
        add_result("Leave", "Comp-off", "PASS" if has_content(driver) else "WARN", "")

def test_E_documents(driver):
    log("\n--- E) Documents ---")
    loaded = navigate_to(driver, ["document"], ["/documents"])
    ss(driver, "p3E_documents")
    if not loaded:
        add_result("Documents", "Page load", "FAIL", "Not accessible")
        add_bug("[Documents] Not accessible", "medium", "1. Login\n2. Go to documents", "Documents")
        return
    add_result("Documents", "Page load", "PASS", "Loaded")

    upload = click_el(driver, ["button[class*='upload']"], "upload")
    time.sleep(2)
    ss(driver, "p3E_upload")
    add_result("Documents", "Upload", "PASS" if upload else "WARN", "")

    # Categories filter
    cats = check_els(driver, ["select","[class*='category']","[class*='filter']"])
    add_result("Documents", "Categories filter", "PASS" if cats else "WARN", str(cats[:2]))

def test_F_announcements(driver):
    log("\n--- F) Announcements ---")
    loaded = navigate_to(driver, ["announce"], ["/announcements"])
    ss(driver, "p3F_announcements")
    if not loaded:
        add_result("Announcements", "Page load", "FAIL", "Not accessible")
        return
    add_result("Announcements", "Page load", "PASS", "Loaded")

    create = click_el(driver, ["button[class*='create']","button[class*='add']","button.btn-primary"], "create")
    time.sleep(2)
    ss(driver, "p3F_create")
    add_result("Announcements", "Create form", "PASS" if create else "WARN", "")

def test_G_helpdesk(driver):
    log("\n--- G) Helpdesk ---")
    loaded = navigate_to(driver, ["helpdesk","ticket"], ["/helpdesk","/tickets"])
    ss(driver, "p3G_helpdesk")
    if not loaded:
        add_result("Helpdesk", "Page load", "WARN", "Not found (may be disabled)")
        return
    add_result("Helpdesk", "Page load", "PASS", "Loaded")

    create = click_el(driver, ["button.btn-primary"], "create ticket")
    time.sleep(2)
    ss(driver, "p3G_ticket")
    add_result("Helpdesk", "Create ticket", "PASS" if create else "WARN", "")

    # Knowledge base
    sl = find_sidebar_link(["knowledge"])
    if sl:
        go(driver, sl["href"])
        ss(driver, "p3G_kb")
        add_result("Helpdesk", "Knowledge base", "PASS" if has_content(driver) else "WARN", "")

def test_H_surveys(driver):
    log("\n--- H) Surveys ---")
    loaded = navigate_to(driver, ["survey"], ["/surveys"])
    ss(driver, "p3H_surveys")
    if not loaded:
        add_result("Surveys", "Page load", "WARN", "Not found")
        return
    add_result("Surveys", "Page load", "PASS", "Loaded")

    create = click_el(driver, ["button.btn-primary"], "create survey")
    time.sleep(2)
    ss(driver, "p3H_create")
    add_result("Surveys", "Create survey", "PASS" if create else "WARN", "")

def test_I_events(driver):
    log("\n--- I) Events ---")
    loaded = navigate_to(driver, ["event"], ["/events"])
    ss(driver, "p3I_events")
    if not loaded:
        add_result("Events", "Page load", "WARN", "Not found")
        return
    add_result("Events", "Page load", "PASS", "Loaded")

    create = click_el(driver, ["button.btn-primary"], "create event")
    time.sleep(2)
    ss(driver, "p3I_create")
    add_result("Events", "Create event", "PASS" if create else "WARN", "")

def test_J_wellness(driver):
    log("\n--- J) Wellness ---")
    loaded = navigate_to(driver, ["wellness","well-being"], ["/wellness"])
    ss(driver, "p3J_wellness")
    if not loaded:
        add_result("Wellness", "Page load", "WARN", "Not found")
        return
    add_result("Wellness", "Page load", "PASS", "Loaded")
    text = get_text(driver)
    kw = [k for k in ["mood","energy","check-in","wellness","well-being"] if k in text.lower()]
    add_result("Wellness", "Features", "PASS" if kw else "WARN", str(kw))

def test_K_forum(driver):
    log("\n--- K) Forum ---")
    loaded = navigate_to(driver, ["forum","community"], ["/forum","/community"])
    ss(driver, "p3K_forum")
    if not loaded:
        add_result("Forum", "Page load", "WARN", "Not found")
        return
    add_result("Forum", "Page load", "PASS", "Loaded")

    create = click_el(driver, ["button.btn-primary"], "create post")
    time.sleep(2)
    ss(driver, "p3K_post")
    add_result("Forum", "Create post", "PASS" if create else "WARN", "")

def test_L_feedback(driver):
    log("\n--- L) Feedback ---")
    loaded = navigate_to(driver, ["feedback"], ["/feedback"])
    ss(driver, "p3L_feedback")
    if not loaded:
        add_result("Feedback", "Page load", "WARN", "Not found")
        return
    add_result("Feedback", "Page load", "PASS", "Loaded")

    submit = click_el(driver, ["button.btn-primary","button[type='submit']"], "submit")
    time.sleep(2)
    ss(driver, "p3L_submit")
    add_result("Feedback", "Submit form", "PASS" if submit else "WARN", "")

def test_M_assets(driver):
    log("\n--- M) Assets ---")
    loaded = navigate_to(driver, ["asset"], ["/assets"])
    ss(driver, "p3M_assets")
    if not loaded:
        add_result("Assets", "Page load", "WARN", "Not found")
        return
    add_result("Assets", "Page load", "PASS", "Loaded")

    add_ok = click_el(driver, ["button.btn-primary","button[class*='add']"], "add asset")
    time.sleep(2)
    ss(driver, "p3M_add")
    add_result("Assets", "Add asset", "PASS" if add_ok else "WARN", "")

    # Categories
    cats = check_els(driver, ["[class*='category']","[class*='filter']","select","[class*='tab']"])
    add_result("Assets", "Categories", "PASS" if cats else "WARN", str(cats[:2]))

def test_N_positions(driver):
    log("\n--- N) Positions ---")
    loaded = navigate_to(driver, ["position","vacanc","recruit"], ["/positions","/vacancies","/recruitment"])
    ss(driver, "p3N_positions")
    if not loaded:
        add_result("Positions", "Page load", "WARN", "Not found")
        return
    add_result("Positions", "Page load", "PASS", "Loaded")
    text = get_text(driver)
    for kw in ["position","vacancy","open","filled"]:
        if kw in text.lower():
            add_result("Positions", f"Data: {kw}", "PASS", "Found")
            break

def test_O_orgchart(driver):
    log("\n--- O) Org Chart ---")
    loaded = navigate_to(driver, ["org-chart","orgchart","org chart"], ["/org-chart","/orgchart"])
    ss(driver, "p3O_orgchart")
    if not loaded:
        add_result("Org Chart", "Page load", "WARN", "Not found")
        return
    add_result("Org Chart", "Page load", "PASS", "Loaded")

    nodes = check_els(driver, ["[class*='node']","[class*='chart']","svg","canvas","[class*='org']","[class*='tree']"])
    add_result("Org Chart", "Chart elements", "PASS" if nodes else "WARN", str(nodes[:2]))

    # Click a node
    clicked = driver.execute_script("""
        var nodes = document.querySelectorAll('[class*="node"], [class*="chart"] [class*="card"], svg g');
        for(var i=0; i<nodes.length; i++){
            if(nodes[i].offsetParent !== null){
                nodes[i].click();
                return true;
            }
        }
        return false;
    """)
    if clicked:
        time.sleep(2)
        ss(driver, "p3O_node_click")
        add_result("Org Chart", "Node clickable", "PASS", "Clicked a node")

def test_P_settings(driver):
    log("\n--- P) Settings ---")
    loaded = navigate_to(driver, ["setting"], ["/settings"])
    ss(driver, "p3P_settings")
    if loaded:
        add_result("Settings", "Page load", "PASS", "Loaded")
    else:
        add_result("Settings", "Page load", "WARN", "Not found directly")

    subs = {
        "Departments": ["department"],
        "Locations": ["location","office"],
        "Designations": ["designation"],
        "Custom Fields": ["custom-field","custom_field","customfield"],
        "Modules": ["module"]
    }
    for name, kws in subs.items():
        sl = find_sidebar_link(kws)
        if sl:
            go(driver, sl["href"])
            time.sleep(2)
            ss(driver, f"p3P_{name.replace(' ','_')}")
            if has_content(driver):
                add_result("Settings", name, "PASS", "Page loaded")
                # Try add/edit buttons
                add_btn = click_el(driver, ["button[class*='add']","button.btn-primary"], "add")
                time.sleep(1)
                if add_btn:
                    ss(driver, f"p3P_{name.replace(' ','_')}_add")
                    add_result("Settings", f"{name} add form", "PASS", "Form opened")
                    # Close/dismiss
                    click_el(driver, ["button[class*='close']","[class*='modal'] button","button[class*='cancel']"], "cancel")
                    time.sleep(1)
            else:
                add_result("Settings", name, "FAIL", "Page blank")
        else:
            add_result("Settings", name, "WARN", "Link not found")

def test_Q_reports(driver):
    log("\n--- Q) Reports ---")
    loaded = navigate_to(driver, ["report"], ["/reports"])
    ss(driver, "p3Q_reports")
    if not loaded:
        add_result("Reports", "Page load", "WARN", "Not found")
        return
    add_result("Reports", "Page load", "PASS", "Loaded")

    # Try generating
    gen = click_el(driver, ["button.btn-primary","button[class*='generate']"], "generate")
    time.sleep(3)
    ss(driver, "p3Q_generate")
    add_result("Reports", "Generate report", "PASS" if gen else "WARN", "")

def test_R_billing(driver):
    log("\n--- R) Billing ---")
    loaded = navigate_to(driver, ["billing","subscription","plan"], ["/billing","/subscription"])
    ss(driver, "p3R_billing")
    if not loaded:
        add_result("Billing", "Page load", "WARN", "Not found")
        return
    add_result("Billing", "Page load", "PASS", "Loaded")
    text = get_text(driver)
    for kw in ["plan","billing","subscription","invoice","payment"]:
        if kw in text.lower():
            add_result("Billing", f"Info: {kw}", "PASS", "Found")

def test_S_users(driver):
    log("\n--- S) Users/Invitations ---")
    loaded = navigate_to(driver, ["user","invitation","invite"], ["/users","/invitations"])
    ss(driver, "p3S_users")
    if not loaded:
        add_result("Users", "Page load", "WARN", "Not found")
        return
    add_result("Users", "Page load", "PASS", "Loaded")

    invite = click_el(driver, ["button.btn-primary"], "invite")
    time.sleep(2)
    ss(driver, "p3S_invite")
    add_result("Users", "Invite user", "PASS" if invite else "WARN", "")

def test_T_chatbot(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    log("\n--- T) AI Chatbot ---")

    go(driver, "/", wait=3)

    # Look for chatbot bubble via JS
    bubble = driver.execute_script("""
        // Try class-based selectors
        var sels = ['[class*="chatbot"]','[class*="chat-bubble"]','[class*="chat-icon"]',
                    '[class*="ai-chat"]','[class*="assistant"]','button[class*="chat"]',
                    '[class*="floating"]','[class*="fab"]','[class*="purple"]',
                    '[class*="bot-trigger"]'];
        for(var i=0; i<sels.length; i++){
            var els = document.querySelectorAll(sels[i]);
            for(var j=0; j<els.length; j++){
                if(els[j].offsetParent !== null){
                    els[j].click();
                    return 'class:' + sels[i];
                }
            }
        }
        // Try fixed positioned elements at bottom-right
        var all = document.querySelectorAll('button, div[role="button"]');
        for(var i=0; i<all.length; i++){
            var rect = all[i].getBoundingClientRect();
            var style = getComputedStyle(all[i]);
            if(style.position === 'fixed' && rect.bottom > window.innerHeight - 120 && rect.right > window.innerWidth - 120){
                all[i].click();
                return 'fixed-position';
            }
        }
        return null;
    """)

    if bubble:
        time.sleep(2)
        ss(driver, "p3T_chatbot")
        add_result("Chatbot", "Open bubble", "PASS", f"Found via {bubble}")

        # Type message
        typed = driver.execute_script("""
            var inputs = document.querySelectorAll("input[class*='chat'], textarea[class*='chat'], input[placeholder*='essage'], textarea[placeholder*='essage'], [class*='chat'] input, [class*='chat'] textarea, [class*='chatbot'] input, [class*='chatbot'] textarea");
            for(var i=0; i<inputs.length; i++){
                if(inputs[i].offsetParent !== null){
                    inputs[i].value = 'How many employees are there?';
                    inputs[i].dispatchEvent(new Event('input', {bubbles:true}));
                    return true;
                }
            }
            return false;
        """)
        if typed:
            time.sleep(1)
            # Try enter key
            click_el(driver, ["button[class*='send']","button[type='submit']","[class*='chat'] button"], "send")
            time.sleep(5)
            ss(driver, "p3T_response")
            add_result("Chatbot", "Send message", "PASS", "Message sent")
        else:
            add_result("Chatbot", "Send message", "WARN", "Input not found")
    else:
        ss(driver, "p3T_no_chatbot")
        add_result("Chatbot", "Open bubble", "WARN", "Bubble not found")

# ═══════════════════════════════════════════════════
# PHASE 4: FORM VALIDATION
# ═══════════════════════════════════════════════════
def phase4_forms(driver):
    from selenium.webdriver.common.by import By

    log("=" * 60)
    log("PHASE 4: FORM VALIDATION")
    log("=" * 60)

    tested = 0
    form_links = [sl for sl in sidebar_links if any(kw in sl.get("text","").lower() for kw in ["add","create","new","apply","invite"])]

    # Also test known form paths
    form_paths = ["/employees", "/leave", "/attendance"]

    for ft in form_links[:6]:
        try:
            go(driver, ft["href"])
            time.sleep(2)

            visible_inputs = driver.execute_script("""
                var inputs = document.querySelectorAll("input:not([type='hidden']), select, textarea");
                var count = 0;
                for(var i=0; i<inputs.length; i++) {
                    if(inputs[i].offsetParent !== null) count++;
                }
                return count;
            """)

            if not visible_inputs or visible_inputs < 1:
                continue

            tested += 1

            # Try empty submit
            submitted = click_el(driver, ["button[type='submit']","button.btn-primary","button[class*='save']","button[class*='submit']"], "submit")
            time.sleep(2)

            if submitted:
                errs = check_els(driver, ["[class*='error']","[class*='invalid']",".has-error",".is-invalid","[role='alert']"])
                html5_inv = driver.execute_script("return document.querySelectorAll(':invalid').length")
                ss(driver, f"p4_form_{tested}")

                if errs or (html5_inv and html5_inv > 0):
                    add_result("Validation", f"Empty submit: {ft.get('text','')}", "PASS",
                             f"{len(errs)} CSS, {html5_inv} HTML5")
                else:
                    add_result("Validation", f"Empty submit: {ft.get('text','')}", "WARN",
                             "No validation errors")

            # Required field indicators
            req = driver.execute_script("return document.querySelectorAll('[required], [aria-required=\"true\"], .required').length")
            add_result("Validation", f"Required fields: {ft.get('text','')}", "PASS" if req else "WARN", f"{req} fields")

        except Exception as e:
            log(f"  Form error: {e}")

    add_result("Phase 4", "Form validation", "PASS" if tested > 0 else "WARN", f"Tested {tested} forms")

# ═══════════════════════════════════════════════════
# FILE BUGS
# ═══════════════════════════════════════════════════
def file_all_bugs():
    log("=" * 60)
    log("FILING GITHUB ISSUES")
    log("=" * 60)

    if not bugs_found:
        log("  No bugs to file!")
        return

    filed = 0
    for bug in bugs_found:
        body = f"""## Bug Report (Automated E2E Test)

**Module:** {bug['module']}
**Severity:** {bug['severity']}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Environment:** {BASE_URL}
**User:** Org Admin ({LOGIN_EMAIL})

## Steps to Reproduce
{bug['steps']}

## Expected Behavior
The page/feature should load and function correctly.

## Actual Behavior
{bug['title']}

---
*Filed by automated E2E dashboard test*"""

        num = file_github_issue(bug['title'], body, ["bug","e2e-test"])
        if num: filed += 1
        time.sleep(1)

    log(f"  Filed {filed}/{len(bugs_found)} issues")

# ═══════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════
def print_summary():
    log("\n" + "=" * 70)
    log("COMPLETE TEST SUMMARY")
    log("=" * 70)

    p = sum(1 for r in test_results if r["status"]=="PASS")
    f = sum(1 for r in test_results if r["status"]=="FAIL")
    w = sum(1 for r in test_results if r["status"]=="WARN")

    log(f"\nTotal tests: {len(test_results)}")
    log(f"  PASSED: {p}")
    log(f"  FAILED: {f}")
    log(f"  WARNINGS: {w}")
    log(f"\nBugs filed: {len(bugs_found)}")
    log(f"Pages tested in Phase 2: {len(pages_tested)}")
    log(f"Sidebar links: {len(sidebar_links)}")

    mods = {}
    for r in test_results:
        m = r["module"]
        if m not in mods: mods[m] = {}
        mods[m][r["status"]] = mods[m].get(r["status"], 0) + 1

    log(f"\n{'Module':<25} {'PASS':>6} {'FAIL':>6} {'WARN':>6}")
    log("-" * 50)
    for m in sorted(mods):
        c = mods[m]
        log(f"{m:<25} {c.get('PASS',0):>6} {c.get('FAIL',0):>6} {c.get('WARN',0):>6}")

    log(f"\n{'='*70}")
    log("ALL PAGES TESTED (Phase 2):")
    log(f"{'='*70}")
    for p in pages_tested:
        st = p["status"]
        icon = "OK" if st=="OK" else "FAIL" if st in ("404","BLANK","REDIRECT_LOGIN","EXCEPTION") else "WARN"
        log(f"  [{icon:>4}] {p.get('text',''):<40} {st:<15} {p.get('url','')}")

    if bugs_found:
        log(f"\n{'='*70}")
        log("BUGS FOUND:")
        log(f"{'='*70}")
        for bug in bugs_found:
            log(f"  [{bug['severity'].upper():>8}] {bug['title']}")

    failures = [r for r in test_results if r["status"]=="FAIL"]
    if failures:
        log(f"\n{'='*70}")
        log("ALL FAILURES:")
        log(f"{'='*70}")
        for fl in failures:
            log(f"  [{fl['module']}] {fl['test']}: {fl['details']}")

    log(f"\n{'='*70}")
    log("TEST RUN COMPLETE")
    log(f"{'='*70}")

# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════
def main():
    log("Starting EMP Cloud HRMS Full Dashboard E2E Test")
    driver = None
    try:
        driver = setup_driver()
        log("  Driver ready")

        if not do_login(driver):
            log("CRITICAL: Cannot login!")
            return

        phase1_sidebar(driver)
        phase2_pages(driver)

        log("=" * 60)
        log("PHASE 3: DEEP MODULE TESTING")
        log("=" * 60)

        test_A_dashboard(driver)
        test_B_employees(driver)
        test_C_attendance(driver)
        test_D_leave(driver)
        test_E_documents(driver)
        test_F_announcements(driver)
        test_G_helpdesk(driver)
        test_H_surveys(driver)
        test_I_events(driver)
        test_J_wellness(driver)
        test_K_forum(driver)
        test_L_feedback(driver)
        test_M_assets(driver)
        test_N_positions(driver)
        test_O_orgchart(driver)
        test_P_settings(driver)
        test_Q_reports(driver)
        test_R_billing(driver)
        test_S_users(driver)
        test_T_chatbot(driver)

        phase4_forms(driver)
        file_all_bugs()

    except Exception as e:
        log(f"FATAL: {e}")
        traceback.print_exc()
        if driver: ss(driver, "FATAL")
    finally:
        if driver:
            try: driver.quit()
            except: pass

    print_summary()

if __name__ == "__main__":
    main()
