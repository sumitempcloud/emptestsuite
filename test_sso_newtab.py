#!/usr/bin/env python3
"""
EMP Cloud — SSO Module Testing (handles new tab links)
Tests each external module via SSO from the dashboard.
"""

import sys, os, time, base64, requests, traceback
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager

BASE = "https://test-empcloud.empcloud.com"
SSDIR = r"C:\Users\Admin\screenshots\dashboard_sso"
GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"
os.makedirs(SSDIR, exist_ok=True)

results = []
bugs = []

SSO_MODULES = [
    ("Rewards & Recognition", "test-rewards.empcloud.com"),
    ("Recruitment", "test-recruit.empcloud.com"),
    ("Projects", "test-project.empcloud.com"),
    ("Performance", "test-performance.empcloud.com"),
    ("Payroll", "testpayroll.empcloud.com"),
    ("LMS", "testlms.empcloud.com"),
    ("Exit Management", "test-exit.empcloud.com"),
    ("Employee Monitoring", "test-empmonitor.empcloud.com"),
]

def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def log(m):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)

def ss(driver, name):
    safe = name.replace(" ","_").replace("/","_").replace("\\","_").replace("&","and")[:70]
    p = os.path.join(SSDIR, f"sso2_{safe}_{ts()}.png")
    try:
        driver.save_screenshot(p)
        return p
    except:
        return None

def add_result(page, status, detail="", ssp=None):
    results.append({"page":page,"status":status,"detail":detail,"ss":ssp})

def add_bug(title, desc, ssp=None):
    bugs.append({"title":title,"desc":desc,"ss":ssp})

def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage",
              "--window-size=1920,1080","--disable-gpu","--disable-extensions",
              "--ignore-certificate-errors"]:
        opts.add_argument(a)
    path = ChromeDriverManager().install()
    svc = Service(path)
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(2)
    return d

def login(driver, email="ananya@technova.in", password="Welcome@123"):
    driver.get(f"{BASE}/login")
    wait = WebDriverWait(driver, 15)
    em = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='email']")))
    em.clear(); em.send_keys(email)
    pw = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
    pw.clear(); pw.send_keys(password)
    time.sleep(0.3)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    WebDriverWait(driver, 15).until(lambda d: "/login" not in d.current_url)
    time.sleep(3)
    log(f"  Logged in -> {driver.current_url}")
    return True

def gh_upload(filepath):
    if not filepath or not os.path.exists(filepath): return None
    fn = os.path.basename(filepath)
    with open(filepath,"rb") as f: content = base64.b64encode(f.read()).decode()
    url = f"https://api.github.com/repos/{GH_REPO}/contents/test-screenshots/dashboard-sso/{fn}"
    h = {"Authorization":f"token {GH_TOKEN}","Accept":"application/vnd.github.v3+json"}
    r = requests.put(url, json={"message":f"Add screenshot: {fn}","content":content,"branch":"main"}, headers=h)
    if r.status_code in (200,201):
        return r.json().get("content",{}).get("download_url","")
    return None

def gh_issue(title, body, ss_url=None):
    if ss_url: body += f"\n\n**Screenshot:**\n![screenshot]({ss_url})"
    url = f"https://api.github.com/repos/{GH_REPO}/issues"
    h = {"Authorization":f"token {GH_TOKEN}","Accept":"application/vnd.github.v3+json"}
    r = requests.post(url, json={"title":title,"body":body,"labels":["bug","functional-test","dashboard-sso"]}, headers=h)
    if r.status_code == 201:
        return r.json().get("html_url","")
    return None


if __name__ == "__main__":
    log("SSO Module Testing - New Tab Handling")

    for mod_name, domain in SSO_MODULES:
        log(f"\n{'='*50}")
        log(f"Testing SSO: {mod_name} ({domain})")
        log(f"{'='*50}")

        driver = create_driver()
        try:
            login(driver)

            # Navigate to dashboard, scroll to modules
            driver.get(BASE)
            time.sleep(4)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            # Find the Launch link for this module's domain
            launch_href = None
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                if domain in href and text == "Launch":
                    launch_href = href
                    log(f"  Found Launch link")
                    break

            if not launch_href:
                # Try module name link
                for link in links:
                    href = link.get_attribute("href") or ""
                    if domain in href:
                        launch_href = href
                        log(f"  Found module link: {link.text.strip()[:40]}")
                        break

            if not launch_href:
                log(f"  No SSO link found for {domain}")
                add_result(f"SSO: {mod_name}", "SKIP", "No link found")
                continue

            # Navigate directly to the SSO URL (since Launch opens new tab)
            log(f"  Navigating to SSO URL...")
            driver.get(launch_href)
            time.sleep(6)  # Allow SSO redirect + SPA render

            cur = driver.current_url
            log(f"  Final URL: {cur}")

            body = ""
            try: body = driver.find_element(By.TAG_NAME, "body").text[:2000]
            except: pass

            ssp = ss(driver, f"{mod_name}_loaded")
            log(f"  Body preview ({len(body)} chars): {body[:200]}")

            # Check for errors
            errors = []
            for pat in ["403 Forbidden","404 Not Found","500 Internal Server Error",
                        "Something went wrong","Application error","Server Error",
                        "Page not found","Cannot read properties"]:
                if pat.lower() in body.lower():
                    errors.append(pat)

            if len(body.strip()) < 30:
                errors.append("Page nearly blank")

            if "login" in cur.lower() and domain not in cur:
                errors.append("Redirected back to login (SSO failed)")

            if errors:
                add_result(f"SSO: {mod_name}", "FAIL", f"{cur} | {'; '.join(errors)}", ssp)
                add_bug(
                    f"[FUNCTIONAL] SSO to {mod_name} ({domain}): {errors[0]}",
                    f"**Module:** {mod_name}\n**Domain:** {domain}\n**Final URL:** {cur}\n**Errors:** {'; '.join(errors)}\n**Body preview:** {body[:400]}",
                    ssp
                )
            else:
                add_result(f"SSO: {mod_name}", "PASS", f"{cur} | Content loaded", ssp)

                # Test internal navigation
                try:
                    nav_links = driver.find_elements(By.TAG_NAME, "a")
                    internal = [(l.text.strip(), l.get_attribute("href")) for l in nav_links
                               if domain in (l.get_attribute("href") or "") and l.text.strip()]
                    if internal:
                        log(f"  Internal links found: {len(internal)}")
                        for text, href in internal[:3]:
                            log(f"    - {text[:40]}: {href[:80]}")
                        # Click first internal link
                        first_text, first_href = internal[0]
                        driver.get(first_href)
                        time.sleep(4)
                        ss(driver, f"{mod_name}_nav_{first_text[:20]}")
                        log(f"  Navigated to: {driver.current_url}")
                        nbody = driver.find_element(By.TAG_NAME, "body").text[:300]
                        if len(nbody.strip()) < 20:
                            add_result(f"SSO Nav: {mod_name} > {first_text}", "FAIL", "Blank after nav")
                        else:
                            add_result(f"SSO Nav: {mod_name} > {first_text}", "PASS", driver.current_url)
                except Exception as e:
                    log(f"  Nav test error: {e}")

        except Exception as e:
            log(f"  ERROR: {e}")
            traceback.print_exc()
            ssp = ss(driver, f"{mod_name}_error")
            add_result(f"SSO: {mod_name}", "ERROR", str(e), ssp)
        finally:
            try: driver.quit()
            except: pass

    # ── Also test as employee ──
    log(f"\n{'='*50}")
    log("Testing SSO as Employee (priya@technova.in)")
    log(f"{'='*50}")

    emp_modules = ["Rewards & Recognition", "Recruitment", "Performance", "Payroll"]
    for mod_name, domain in SSO_MODULES:
        if mod_name not in emp_modules:
            continue
        log(f"\n--- Emp SSO: {mod_name} ---")
        driver = create_driver()
        try:
            login(driver, "priya@technova.in", "Welcome@123")
            driver.get(BASE)
            time.sleep(4)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            launch_href = None
            for link in driver.find_elements(By.TAG_NAME, "a"):
                href = link.get_attribute("href") or ""
                if domain in href:
                    launch_href = href
                    break

            if not launch_href:
                add_result(f"Emp SSO: {mod_name}", "SKIP", "No link for employee")
                continue

            driver.get(launch_href)
            time.sleep(6)
            cur = driver.current_url
            body = driver.find_element(By.TAG_NAME, "body").text[:1000]
            ssp = ss(driver, f"emp_{mod_name}")
            log(f"  URL: {cur}")
            log(f"  Body: {body[:150]}")

            if len(body.strip()) < 30 or "login" in cur.lower():
                add_result(f"Emp SSO: {mod_name}", "FAIL", f"{cur} | Blank or login redirect", ssp)
                add_bug(f"[FUNCTIONAL] Employee SSO to {mod_name} fails",
                        f"**Module:** {mod_name}\n**User:** priya@technova.in (employee)\n**URL:** {cur}\n**Body:** {body[:300]}", ssp)
            else:
                add_result(f"Emp SSO: {mod_name}", "PASS", f"{cur}", ssp)
        except Exception as e:
            log(f"  ERROR: {e}")
            add_result(f"Emp SSO: {mod_name}", "ERROR", str(e))
        finally:
            try: driver.quit()
            except: pass

    # ── Report ──
    log(f"\n{'='*70}")
    log("SSO TEST REPORT")
    log(f"{'='*70}")
    p = sum(1 for r in results if r["status"]=="PASS")
    f = sum(1 for r in results if r["status"]=="FAIL")
    e = sum(1 for r in results if r["status"]=="ERROR")
    s = sum(1 for r in results if r["status"]=="SKIP")
    log(f"Summary: {p} PASS | {f} FAIL | {e} ERROR | {s} SKIP")
    log(f"Bugs: {len(bugs)}")
    log(f"\n{'Page':<45} {'Status':<8} Details")
    log("-"*110)
    for r in results:
        log(f"{r['page'][:44]:<45} {r['status']:<8} {r['detail'][:60]}")

    # File bugs
    if bugs:
        log(f"\n--- Filing {len(bugs)} bugs ---")
        for b in bugs:
            ss_url = gh_upload(b["ss"])
            iu = gh_issue(b["title"], b["desc"], ss_url)
            if iu: log(f"  Filed: {iu}")
            time.sleep(1)

    log("\nDONE")
