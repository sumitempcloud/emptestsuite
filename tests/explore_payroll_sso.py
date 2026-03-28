import sys, os, time, json, traceback
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_explore_payroll"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

BASE = "https://test-empcloud.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

step = [0]

def ss(driver, name):
    step[0] += 1
    fname = f"{step[0]:02d}_{name}.png"
    path = os.path.join(SCREENSHOT_DIR, fname)
    driver.save_screenshot(path)
    print(f"  [Screenshot] {fname} | URL: {driver.current_url}")
    return path

def make_driver(enable_perf_log=False):
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--ignore-certificate-errors")
    if enable_perf_log:
        opts.set_capability("goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"})
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    return driver

def login(driver):
    print(f"\n--- Logging in as {EMAIL} ---")
    driver.get(BASE + "/login")
    time.sleep(3)
    ss(driver, "login_page")

    try:
        email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail'], input[id*='email']")
        email_field.clear()
        email_field.send_keys(EMAIL)
    except:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"  Found {len(inputs)} input fields")
        for i, inp in enumerate(inputs):
            print(f"    input[{i}]: type={inp.get_attribute('type')} name={inp.get_attribute('name')} placeholder={inp.get_attribute('placeholder')}")
        if inputs:
            inputs[0].clear()
            inputs[0].send_keys(EMAIL)

    try:
        pw_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pw_field.clear()
        pw_field.send_keys(PASSWORD)
    except:
        pass

    time.sleep(1)
    ss(driver, "login_filled")

    try:
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        btn.click()
    except:
        btns = driver.find_elements(By.TAG_NAME, "button")
        for b in btns:
            txt = b.text.lower()
            if 'login' in txt or 'sign in' in txt or 'submit' in txt:
                b.click()
                break

    time.sleep(5)
    ss(driver, "after_login")
    print(f"  Post-login URL: {driver.current_url}")
    return driver

def find_all_payroll_links(driver, context=""):
    print(f"\n--- Scanning all links for payroll references ({context}) ---")
    links = driver.find_elements(By.TAG_NAME, "a")
    found = []
    for link in links:
        try:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            onclick = link.get_attribute("onclick") or ""
            if any(kw in (href + text + onclick).lower() for kw in ['payroll', 'pay', 'salary', 'sso', 'testpayroll']):
                print(f"  FOUND: '{text}' -> {href} (onclick={onclick})")
                found.append((text, href, link))
        except StaleElementReferenceException:
            pass

    # Also check buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        try:
            text = btn.text.strip()
            onclick = btn.get_attribute("onclick") or ""
            if any(kw in (text + onclick).lower() for kw in ['payroll', 'pay', 'salary']):
                print(f"  FOUND BUTTON: '{text}' (onclick={onclick})")
                found.append((text, "", btn))
        except StaleElementReferenceException:
            pass

    if not found:
        print("  No payroll links/buttons found on this page.")
    return found

def scan_all_subdomain_links(driver, context=""):
    """Find ALL links pointing to any empcloud.com subdomain"""
    print(f"\n--- Scanning all empcloud subdomain links ({context}) ---")
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        try:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            if 'empcloud.com' in href and href != BASE + "/":
                print(f"  LINK: '{text}' -> {href}")
        except StaleElementReferenceException:
            pass

def check_page_source_for_payroll(driver, context=""):
    """Check page source for payroll-related strings"""
    print(f"\n--- Checking page source for payroll references ({context}) ---")
    src = driver.page_source.lower()
    keywords = ['payroll', 'testpayroll', 'sso_token', 'ssotoken', 'emp-payroll', 'salary', 'pay-run']
    for kw in keywords:
        idx = src.find(kw)
        if idx >= 0:
            snippet = driver.page_source[max(0, idx-100):idx+200]
            print(f"  MATCH '{kw}' at pos {idx}: ...{snippet}...")

def check_for_sso_token(url, context=""):
    if 'sso_token' in url.lower() or 'ssotoken' in url.lower() or 'token' in url.lower():
        print(f"  *** SSO TOKEN DETECTED in URL ({context}): {url}")
        return True
    return False

# ============================================================
# ATTEMPT 1: Dashboard -> look for Payroll card/link
# ============================================================
def attempt_1():
    print("\n" + "="*70)
    print("ATTEMPT 1: Dashboard -> Payroll card/link")
    print("="*70)
    driver = make_driver()
    try:
        login(driver)
        driver.get(BASE + "/dashboard")
        time.sleep(4)
        ss(driver, "dashboard_page")
        print(f"  Dashboard URL: {driver.current_url}")

        find_all_payroll_links(driver, "dashboard")
        scan_all_subdomain_links(driver, "dashboard")
        check_page_source_for_payroll(driver, "dashboard")

        # Try clicking any payroll-like card/div
        cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='module'], [class*='tile'], [class*='widget']")
        for card in cards:
            try:
                text = card.text.strip().lower()
                if 'payroll' in text or 'pay' in text:
                    print(f"  Clicking card with text: {card.text.strip()[:80]}")
                    ss(driver, "dashboard_payroll_card_before")
                    card.click()
                    time.sleep(4)
                    ss(driver, "dashboard_payroll_card_after")
                    print(f"  After click URL: {driver.current_url}")
                    check_for_sso_token(driver.current_url, "dashboard card click")
                    # Check all tabs/windows
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[-1])
                        time.sleep(3)
                        ss(driver, "dashboard_payroll_new_tab")
                        print(f"  New tab URL: {driver.current_url}")
                        check_for_sso_token(driver.current_url, "dashboard card new tab")
                    break
            except Exception as e:
                print(f"  Card click error: {e}")
    except Exception as e:
        print(f"  ATTEMPT 1 ERROR: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

# ============================================================
# ATTEMPT 2: /modules page
# ============================================================
def attempt_2():
    print("\n" + "="*70)
    print("ATTEMPT 2: /modules page -> Payroll")
    print("="*70)
    driver = make_driver()
    try:
        login(driver)

        for path in ["/modules", "/module", "/apps"]:
            driver.get(BASE + path)
            time.sleep(4)
            ss(driver, f"modules_page_{path.replace('/','')}")
            print(f"  {path} URL: {driver.current_url}")
            found = find_all_payroll_links(driver, path)
            check_page_source_for_payroll(driver, path)

            # Click payroll if found
            for text, href, elem in found:
                try:
                    print(f"  Clicking: '{text}' -> {href}")
                    ss(driver, f"modules_payroll_before_click")
                    elem.click()
                    time.sleep(5)
                    ss(driver, f"modules_payroll_after_click")
                    print(f"  After click URL: {driver.current_url}")
                    check_for_sso_token(driver.current_url, "modules page click")
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[-1])
                        time.sleep(3)
                        ss(driver, "modules_payroll_new_tab")
                        print(f"  New tab URL: {driver.current_url}")
                        check_for_sso_token(driver.current_url, "modules new tab")
                    break
                except Exception as e:
                    print(f"  Click error: {e}")

            # Also look for clickable divs/cards with payroll text
            all_elems = driver.find_elements(By.XPATH, "//*[contains(translate(text(),'PAYROLL','payroll'),'payroll')]")
            for elem in all_elems:
                try:
                    tag = elem.tag_name
                    text = elem.text.strip()[:80]
                    print(f"  Element with 'payroll' text: <{tag}> '{text}'")
                except:
                    pass
    except Exception as e:
        print(f"  ATTEMPT 2 ERROR: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

# ============================================================
# ATTEMPT 3: /billing page
# ============================================================
def attempt_3():
    print("\n" + "="*70)
    print("ATTEMPT 3: /billing page -> Payroll")
    print("="*70)
    driver = make_driver()
    try:
        login(driver)
        driver.get(BASE + "/billing")
        time.sleep(4)
        ss(driver, "billing_page")
        print(f"  Billing URL: {driver.current_url}")
        find_all_payroll_links(driver, "billing")
        check_page_source_for_payroll(driver, "billing")
        scan_all_subdomain_links(driver, "billing")
    except Exception as e:
        print(f"  ATTEMPT 3 ERROR: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

# ============================================================
# ATTEMPT 4: Sidebar navigation
# ============================================================
def attempt_4():
    print("\n" + "="*70)
    print("ATTEMPT 4: Sidebar navigation -> Payroll")
    print("="*70)
    driver = make_driver()
    try:
        login(driver)
        time.sleep(2)
        ss(driver, "sidebar_check")

        # Check sidebar / nav elements
        nav_selectors = [
            "nav", "[class*='sidebar']", "[class*='Sidebar']", "[class*='nav']",
            "[class*='menu']", "[class*='Menu']", "[role='navigation']",
            ".side-bar", "#sidebar", ".left-panel", ".nav-panel"
        ]
        for sel in nav_selectors:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for elem in elems:
                    text = elem.text.strip()
                    if text and len(text) < 2000:
                        if 'payroll' in text.lower() or 'pay' in text.lower():
                            print(f"  SIDEBAR MATCH ({sel}): {text[:200]}")
            except:
                pass

        # Try hamburger menu if exists
        for sel in ["[class*='hamburger']", "[class*='toggle']", "[aria-label*='menu']", "button.menu", ".menu-toggle"]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, sel)
                btn.click()
                time.sleep(2)
                ss(driver, "sidebar_expanded")
                find_all_payroll_links(driver, "sidebar expanded")
                break
            except:
                pass

        find_all_payroll_links(driver, "sidebar page")
    except Exception as e:
        print(f"  ATTEMPT 4 ERROR: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

# ============================================================
# ATTEMPT 5: Direct URL attempts
# ============================================================
def attempt_5():
    print("\n" + "="*70)
    print("ATTEMPT 5: Direct URL attempts")
    print("="*70)
    driver = make_driver()
    try:
        login(driver)

        direct_paths = [
            "/payroll",
            "/modules/payroll",
            "/module/payroll",
            "/module/emp-payroll",
            "/modules/emp-payroll",
            "/app/payroll",
            "/sso/payroll",
            "/redirect/payroll",
        ]
        for path in direct_paths:
            driver.get(BASE + path)
            time.sleep(4)
            ss(driver, f"direct_{path.replace('/','_').strip('_')}")
            print(f"  {path} -> {driver.current_url}")
            check_for_sso_token(driver.current_url, f"direct {path}")
            if 'testpayroll' in driver.current_url:
                print(f"  *** LANDED ON PAYROLL DOMAIN! URL: {driver.current_url}")
                ss(driver, f"direct_{path.replace('/','_').strip('_')}_payroll_landed")
    except Exception as e:
        print(f"  ATTEMPT 5 ERROR: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

# ============================================================
# ATTEMPT 6: Deep HTML/JS analysis for SSO
# ============================================================
def attempt_6():
    print("\n" + "="*70)
    print("ATTEMPT 6: HTML/JS analysis for SSO URLs and payroll references")
    print("="*70)
    driver = make_driver()
    try:
        login(driver)

        # Check dashboard source thoroughly
        for page in ["/dashboard", "/modules", "/"]:
            driver.get(BASE + page)
            time.sleep(4)
            src = driver.page_source

            # Search for all occurrences of payroll, sso, token in source
            lower_src = src.lower()
            for keyword in ['payroll', 'sso', 'sso_token', 'testpayroll', 'emp-payroll', 'redirect']:
                start = 0
                count = 0
                while True:
                    idx = lower_src.find(keyword, start)
                    if idx < 0:
                        break
                    count += 1
                    if count <= 5:  # Print first 5 occurrences
                        snippet = src[max(0,idx-80):idx+150]
                        snippet = snippet.replace('\n', ' ').replace('\r', '')
                        print(f"  [{page}] '{keyword}' at {idx}: ...{snippet}...")
                    start = idx + len(keyword)
                if count > 0:
                    print(f"  [{page}] Total '{keyword}' occurrences: {count}")

            # Check iframes
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i, iframe in enumerate(iframes):
                src_attr = iframe.get_attribute("src") or ""
                print(f"  [{page}] iframe[{i}]: src={src_attr}")

            # Check scripts for SSO-related functions
            scripts = driver.find_elements(By.TAG_NAME, "script")
            for s in scripts:
                script_src = s.get_attribute("src") or ""
                inner = s.get_attribute("innerHTML") or ""
                if any(kw in (script_src + inner).lower() for kw in ['payroll', 'sso', 'sso_token']):
                    print(f"  [{page}] Script with payroll/sso ref: src={script_src[:100]}")
                    if inner and len(inner) < 5000:
                        for line in inner.split('\n'):
                            if any(kw in line.lower() for kw in ['payroll', 'sso']):
                                print(f"    JS line: {line.strip()[:200]}")

        # Execute JS to find React/Vue state or window variables with SSO info
        try:
            result = driver.execute_script("""
                var info = {};
                // Check window-level variables
                for (var key in window) {
                    try {
                        var val = JSON.stringify(window[key]);
                        if (val && (val.toLowerCase().includes('payroll') || val.toLowerCase().includes('sso'))) {
                            info[key] = val.substring(0, 500);
                        }
                    } catch(e) {}
                }
                return JSON.stringify(info);
            """)
            if result and result != '{}':
                print(f"  Window variables with payroll/sso: {result[:2000]}")
        except Exception as e:
            print(f"  JS execution error: {e}")

        # Check localStorage and sessionStorage
        try:
            ls = driver.execute_script("return JSON.stringify(localStorage);")
            ss_storage = driver.execute_script("return JSON.stringify(sessionStorage);")
            for name, val in [("localStorage", ls), ("sessionStorage", ss_storage)]:
                if val and ('payroll' in val.lower() or 'sso' in val.lower() or 'token' in val.lower()):
                    print(f"  {name} (relevant): {val[:2000]}")
                elif val:
                    print(f"  {name} keys: {val[:500]}")
        except:
            pass

    except Exception as e:
        print(f"  ATTEMPT 6 ERROR: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

# ============================================================
# ATTEMPT 7: Network/performance logs for SSO token generation
# ============================================================
def attempt_7():
    print("\n" + "="*70)
    print("ATTEMPT 7: Network logs for SSO token generation")
    print("="*70)
    driver = make_driver(enable_perf_log=True)
    try:
        login(driver)

        # Navigate to pages that might trigger SSO
        for page in ["/dashboard", "/modules"]:
            driver.get(BASE + page)
            time.sleep(4)

            # Click any payroll-related element
            found = find_all_payroll_links(driver, f"attempt7 {page}")
            for text, href, elem in found:
                try:
                    elem.click()
                    time.sleep(5)
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[-1])
                        time.sleep(3)
                        print(f"  New tab after click: {driver.current_url}")
                        ss(driver, "attempt7_new_tab")
                        check_for_sso_token(driver.current_url, "attempt7 new tab")
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                except Exception as e:
                    print(f"  Click error: {e}")

        # Analyze performance logs
        try:
            logs = driver.get_log("performance")
            print(f"\n  Performance log entries: {len(logs)}")
            for entry in logs:
                try:
                    msg = json.loads(entry["message"])
                    method = msg.get("message", {}).get("method", "")
                    params = msg.get("message", {}).get("params", {})

                    # Check network requests
                    if "Network.requestWillBeSent" in method:
                        url = params.get("request", {}).get("url", "")
                        if any(kw in url.lower() for kw in ['payroll', 'sso', 'token', 'redirect']):
                            print(f"  NET REQUEST: {url}")

                    if "Network.responseReceived" in method:
                        url = params.get("response", {}).get("url", "")
                        if any(kw in url.lower() for kw in ['payroll', 'sso', 'token', 'redirect']):
                            status = params.get("response", {}).get("status", "")
                            print(f"  NET RESPONSE: {url} (status={status})")
                except:
                    pass
        except Exception as e:
            print(f"  Performance log error: {e}")

        # Check browser console logs
        try:
            browser_logs = driver.get_log("browser")
            for entry in browser_logs:
                msg = entry.get("message", "")
                if any(kw in msg.lower() for kw in ['payroll', 'sso', 'token']):
                    print(f"  CONSOLE: {msg[:300]}")
        except:
            pass

    except Exception as e:
        print(f"  ATTEMPT 7 ERROR: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

# ============================================================
# ATTEMPT 8: Full link dump + click every module card
# ============================================================
def attempt_8():
    print("\n" + "="*70)
    print("ATTEMPT 8: Full link/card exploration on dashboard and modules page")
    print("="*70)
    driver = make_driver(enable_perf_log=True)
    try:
        login(driver)

        for page in ["/dashboard", "/modules", "/"]:
            driver.get(BASE + page)
            time.sleep(4)
            print(f"\n  --- Page: {page} (URL: {driver.current_url}) ---")

            # Print ALL links
            links = driver.find_elements(By.TAG_NAME, "a")
            print(f"  Total links on page: {len(links)}")
            for i, link in enumerate(links):
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()
                    if href and text:
                        print(f"    [{i}] '{text[:60]}' -> {href}")
                    elif href:
                        aria = link.get_attribute("aria-label") or ""
                        title = link.get_attribute("title") or ""
                        print(f"    [{i}] (no text, aria='{aria}', title='{title}') -> {href}")
                except:
                    pass

            # Find and click all module-like cards
            card_selectors = [
                "[class*='module']", "[class*='Module']", "[class*='card']", "[class*='Card']",
                "[class*='app-']", "[class*='service']", "[class*='product']",
                "[data-module]", "[data-app]"
            ]
            for sel in card_selectors:
                try:
                    cards = driver.find_elements(By.CSS_SELECTOR, sel)
                    for card in cards:
                        text = card.text.strip()
                        if text and len(text) < 200:
                            cls = card.get_attribute("class") or ""
                            print(f"    Card ({sel}): '{text[:80]}' class={cls[:80]}")
                except:
                    pass

            # Try XPath to find any element with payroll in any attribute
            try:
                payroll_elems = driver.find_elements(By.XPATH, "//*[contains(@*,'payroll') or contains(@*,'Payroll')]")
                for elem in payroll_elems:
                    tag = elem.tag_name
                    attrs = driver.execute_script("""
                        var items = arguments[0].attributes;
                        var result = {};
                        for (var i = 0; i < items.length; i++) {
                            result[items[i].name] = items[i].value;
                        }
                        return JSON.stringify(result);
                    """, elem)
                    print(f"    PAYROLL ATTR ELEMENT: <{tag}> attrs={attrs}")
            except:
                pass

        # Now check performance logs for any SSO/payroll network calls
        try:
            logs = driver.get_log("performance")
            for entry in logs:
                try:
                    msg = json.loads(entry["message"])
                    method = msg.get("message", {}).get("method", "")
                    params = msg.get("message", {}).get("params", {})
                    if "Network.requestWillBeSent" in method:
                        url = params.get("request", {}).get("url", "")
                        if any(kw in url.lower() for kw in ['payroll', 'sso', 'module']):
                            print(f"  NET: {url}")
                except:
                    pass
        except:
            pass

    except Exception as e:
        print(f"  ATTEMPT 8 ERROR: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

# ============================================================
# ATTEMPT 9: API-based SSO token generation
# ============================================================
def attempt_9():
    print("\n" + "="*70)
    print("ATTEMPT 9: Try API endpoints for SSO token")
    print("="*70)
    driver = make_driver()
    try:
        login(driver)

        # Get cookies/token from current session
        cookies = driver.get_cookies()
        print(f"  Cookies: {json.dumps([{c['name']: c['value'][:30]+'...'} for c in cookies], indent=2)}")

        # Try to get auth token from localStorage
        token = driver.execute_script("return localStorage.getItem('token') || localStorage.getItem('auth_token') || localStorage.getItem('accessToken') || localStorage.getItem('jwt') || '';")
        if token:
            print(f"  Auth token from localStorage: {token[:50]}...")

        # Dump all localStorage keys
        all_keys = driver.execute_script("return Object.keys(localStorage);")
        print(f"  localStorage keys: {all_keys}")
        for key in all_keys:
            val = driver.execute_script(f"return localStorage.getItem('{key}');")
            if val and len(val) < 500:
                print(f"    {key} = {val[:200]}")
            elif val:
                print(f"    {key} = ({len(val)} chars) {val[:100]}...")

        # Try known API patterns for SSO
        api_base = "https://test-empcloud-api.empcloud.com"
        sso_endpoints = [
            f"{api_base}/api/sso/payroll",
            f"{api_base}/api/sso/generate",
            f"{api_base}/api/modules/payroll/sso",
            f"{api_base}/api/auth/sso",
            f"{api_base}/api/v1/sso/payroll",
            f"{api_base}/api/redirect/payroll",
            f"{BASE}/api/sso/payroll",
            f"{BASE}/api/modules/sso",
        ]
        for endpoint in sso_endpoints:
            driver.get(endpoint)
            time.sleep(2)
            body = driver.find_element(By.TAG_NAME, "body").text[:500]
            print(f"  {endpoint} -> URL: {driver.current_url}")
            print(f"    Body: {body[:200]}")
            check_for_sso_token(driver.current_url, f"API {endpoint}")

    except Exception as e:
        print(f"  ATTEMPT 9 ERROR: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

# ============================================================
# RUN ALL ATTEMPTS
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("PAYROLL SSO EXPLORATION")
    print("=" * 70)

    attempt_1()
    attempt_2()
    attempt_3()
    attempt_4()
    attempt_5()
    attempt_6()
    attempt_7()
    attempt_8()
    attempt_9()

    print("\n" + "=" * 70)
    print("EXPLORATION COMPLETE")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}")
    print("=" * 70)
