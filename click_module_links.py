import sys, os, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_click_all"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def make_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(20)
    driver.implicitly_wait(3)
    return driver

def screenshot(driver, name):
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name)[:80]
    path = os.path.join(SCREENSHOT_DIR, f"{safe}.png")
    driver.save_screenshot(path)
    return path

def login(driver):
    driver.get("https://test-empcloud.empcloud.com")
    time.sleep(3)
    email = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail']"))
    )
    email.clear(); email.send_keys("ananya@technova.in")
    pwd = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pwd.clear(); pwd.send_keys("Welcome@123")
    btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    btn.click()
    time.sleep(6)
    print(f"Logged in. URL: {driver.current_url}")

driver = make_driver()
try:
    login(driver)

    # Collect all links
    links = driver.find_elements(By.TAG_NAME, 'a')
    all_links = []
    for link in links:
        try:
            text = (link.text or "").strip().replace('\n', ' ')[:60]
            href = link.get_attribute('href') or ''
            all_links.append({'text': text, 'href': href})
        except:
            pass

    # Categorize links
    internal = []  # same domain routes
    module_no_sso = []  # module subdomains without sso_token
    module_with_sso = []  # module subdomains with sso_token
    base = "https://test-empcloud.empcloud.com"

    for entry in all_links:
        href = entry['href']
        if not href or href == '#':
            continue
        if 'sso_token' in href:
            module_with_sso.append(entry)
        elif href.startswith(base):
            internal.append(entry)
        elif 'empcloud.com' in href:
            module_no_sso.append(entry)

    print(f"\n{'='*80}")
    print(f"LINK SUMMARY: {len(internal)} internal, {len(module_no_sso)} module (no SSO), {len(module_with_sso)} module (with SSO)")
    print(f"{'='*80}")

    print(f"\n--- INTERNAL LINKS ({len(internal)}) ---")
    for e in internal:
        route = e['href'].replace(base, '')
        print(f"  {e['text']:<45} -> {route}")

    print(f"\n--- MODULE LINKS WITHOUT SSO TOKEN ({len(module_no_sso)}) ---")
    for e in module_no_sso:
        print(f"  {e['text']:<45} -> {e['href']}")

    print(f"\n--- MODULE LINKS WITH SSO TOKEN ({len(module_with_sso)}) ---")
    # Deduplicate by module subdomain
    seen_modules = {}
    for e in module_with_sso:
        domain = e['href'].split('?')[0]
        if domain not in seen_modules:
            seen_modules[domain] = e
        print(f"  {e['text']:<45} -> {domain}?sso_token=<JWT>")

    # Now click each unique module SSO link and track where it goes
    print(f"\n{'='*80}")
    print("CLICKING MODULE SSO LINKS (one per module)")
    print(f"{'='*80}")

    dashboard_handle = driver.current_window_handle
    sso_results = []

    for domain, entry in seen_modules.items():
        href = entry['href']
        text = entry['text']
        module_name = domain.replace('https://', '').split('.')[0]
        print(f"\n  >>> {module_name}: '{text}'")
        print(f"      Link: {domain}?sso_token=<JWT>")

        try:
            driver.execute_script(f"window.open(arguments[0], '_blank');", href)
            time.sleep(4)
            handles = driver.window_handles
            driver.switch_to.window(handles[-1])
            time.sleep(2)

            final_url = driver.current_url
            title = driver.title
            # Strip token from final URL for display
            display_url = final_url.split('?sso_token=')[0] if 'sso_token' in final_url else final_url
            has_token_in_final = 'sso_token' in final_url or 'token' in final_url

            print(f"      FINAL URL: {display_url}")
            print(f"      TITLE: {title}")
            print(f"      SSO token in final URL: {has_token_in_final}")
            print(f"      Token was consumed (stripped): {not has_token_in_final}")

            sc = screenshot(driver, f"07_module_{module_name}")
            print(f"      Screenshot: {sc}")

            sso_results.append({
                'module': module_name,
                'text': text,
                'sso_url': f"{domain}?sso_token=<JWT>",
                'final_url': display_url,
                'title': title,
                'token_consumed': not has_token_in_final,
            })

            driver.close()
            driver.switch_to.window(dashboard_handle)
            time.sleep(0.5)
        except Exception as e:
            print(f"      ERROR: {e}")
            try:
                for h in driver.window_handles[1:]:
                    driver.switch_to.window(h)
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except:
                pass

    # Also click the "View Details" links (no SSO token) to see what happens
    print(f"\n{'='*80}")
    print("CLICKING MODULE LINKS WITHOUT SSO TOKEN (View Details)")
    print(f"{'='*80}")

    nosso_results = []
    for entry in module_no_sso:
        href = entry['href']
        text = entry['text']
        module_name = href.replace('https://', '').split('.')[0]
        print(f"\n  >>> {module_name}: '{text}' -> {href}")

        try:
            driver.execute_script(f"window.open(arguments[0], '_blank');", href)
            time.sleep(4)
            handles = driver.window_handles
            driver.switch_to.window(handles[-1])
            time.sleep(2)

            final_url = driver.current_url
            title = driver.title
            print(f"      FINAL URL: {final_url}")
            print(f"      TITLE: {title}")
            print(f"      Redirected to login? {'login' in final_url.lower() or final_url.rstrip('/') == href.rstrip('/')}")

            sc = screenshot(driver, f"08_nosso_{module_name}")
            print(f"      Screenshot: {sc}")

            nosso_results.append({
                'module': module_name,
                'text': text,
                'original_url': href,
                'final_url': final_url,
                'title': title,
            })

            driver.close()
            driver.switch_to.window(dashboard_handle)
            time.sleep(0.5)
        except Exception as e:
            print(f"      ERROR: {e}")
            try:
                for h in driver.window_handles[1:]:
                    driver.switch_to.window(h)
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except:
                pass

    # Also try direct module URL navigation (no token at all)
    print(f"\n{'='*80}")
    print("DIRECT MODULE URL NAVIGATION (no token, fresh tab)")
    print(f"{'='*80}")

    direct_urls = [
        ("testpayroll", "https://testpayroll.empcloud.com"),
        ("test-recruit", "https://test-recruit.empcloud.com"),
        ("test-performance", "https://test-performance.empcloud.com"),
        ("test-rewards", "https://test-rewards.empcloud.com"),
        ("test-exit", "https://test-exit.empcloud.com"),
        ("testlms", "https://testlms.empcloud.com"),
        ("test-project", "https://test-project.empcloud.com"),
        ("test-empmonitor", "https://test-empmonitor.empcloud.com"),
    ]

    direct_results = []
    for name, url in direct_urls:
        print(f"\n  >>> {name}: {url}")
        try:
            driver.execute_script(f"window.open(arguments[0], '_blank');", url)
            time.sleep(4)
            handles = driver.window_handles
            driver.switch_to.window(handles[-1])
            time.sleep(2)

            final_url = driver.current_url
            title = driver.title
            redirected = final_url.rstrip('/') != url.rstrip('/')
            print(f"      FINAL URL: {final_url}")
            print(f"      TITLE: {title}")
            print(f"      Redirected: {redirected}")

            sc = screenshot(driver, f"09_direct_{name}")
            print(f"      Screenshot: {sc}")

            direct_results.append({
                'module': name,
                'attempted': url,
                'final_url': final_url,
                'title': title,
                'redirected': redirected,
            })

            driver.close()
            driver.switch_to.window(dashboard_handle)
            time.sleep(0.5)
        except Exception as e:
            print(f"      ERROR: {e}")
            try:
                for h in driver.window_handles[1:]:
                    driver.switch_to.window(h)
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except:
                pass

    # FINAL COMPLETE MAP
    print(f"\n{'='*80}")
    print("COMPLETE DASHBOARD MAP")
    print(f"{'='*80}")

    print(f"\n{'='*80}")
    print("SSO MECHANISM ANALYSIS")
    print(f"{'='*80}")
    print("""
SSO TYPE: JWT Token via URL Query Parameter
  - Algorithm: RS256 (RSA Signature with SHA-256)
  - Key ID (kid): MjjnAEAPSQoO04cD
  - Issuer: https://test-empcloud-api.empcloud.com
  - Client: empcloud-dashboard
  - Scopes: openid profile email

SSO FLOW:
  1. User logs into EMP Cloud dashboard (test-empcloud.empcloud.com)
  2. Auth token stored in localStorage key: 'empcloud-auth'
  3. Dashboard renders module cards with pre-generated SSO JWT tokens
  4. Each module link contains: https://<module>.empcloud.com/?sso_token=<JWT>
  5. JWT payload includes: sub (user ID), org_id, email, role, name, org_name
  6. Token has 15-minute expiry (iat to exp = 900 seconds)
  7. Module app receives the sso_token, validates the RS256 signature, and creates a session

TOKEN PAYLOAD FIELDS:
  - sub: 522 (user ID)
  - org_id: 5
  - email: ananya@technova.in
  - role: org_admin
  - first_name: Ananya
  - last_name: Gupta
  - org_name: TechNova
  - scope: openid profile email
  - client_id: empcloud-dashboard
  - jti: unique token ID (nonce)
  - iat/exp: issued-at / expiry timestamps

TWO TYPES OF MODULE LINKS ON DASHBOARD:
  A) "View Details" links -> point to bare module URL (no sso_token)
     These are in the "Module Insights" section cards
  B) "Launch" links -> point to module URL with ?sso_token=<JWT>
     These are in the module launcher section lower on the page
""")

    if sso_results:
        print("\nSSO LINK CLICK RESULTS:")
        for r in sso_results:
            print(f"  {r['module']:<25} Title: {r['title']:<40} Token consumed: {r['token_consumed']}")

    if nosso_results:
        print("\nNO-SSO LINK CLICK RESULTS:")
        for r in nosso_results:
            print(f"  {r['module']:<25} Final: {r['final_url'][:70]}")

    if direct_results:
        print("\nDIRECT URL RESULTS (no login context):")
        for r in direct_results:
            print(f"  {r['module']:<25} Final: {r['final_url'][:70]}  Redirected: {r['redirected']}")

    print("\nDONE.")

finally:
    driver.quit()
