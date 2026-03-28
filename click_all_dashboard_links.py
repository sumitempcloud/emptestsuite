import sys
import os
import time
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_click_all"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

LOGIN_URL = "https://test-empcloud.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

MODULE_SUBDOMAINS = [
    "testpayroll", "test-recruit", "test-performance",
    "test-rewards", "test-exit", "testlms",
    "test-project", "test-empmonitor"
]

SSO_KEYWORDS = ["sso", "launch", "open", "view", "redirect", "token", "auth"]


def make_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    return driver


def screenshot(driver, name):
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name)[:80]
    path = os.path.join(SCREENSHOT_DIR, f"{safe}.png")
    driver.save_screenshot(path)
    print(f"  [SCREENSHOT] {path}")
    return path


def login(driver):
    print(f"\n{'='*80}")
    print("STEP 1: LOGIN")
    print(f"{'='*80}")
    driver.get(LOGIN_URL)
    time.sleep(3)
    screenshot(driver, "01_login_page")

    try:
        email_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail'], input[id*='email']"))
        )
        email_field.clear()
        email_field.send_keys(EMAIL)

        pwd_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pwd_field.clear()
        pwd_field.send_keys(PASSWORD)

        screenshot(driver, "02_credentials_entered")

        # Try multiple selectors for login button
        login_btn = None
        for sel in [
            "button[type='submit']",
            "button.login-btn",
            "//button[contains(text(),'Login')]",
            "//button[contains(text(),'Sign')]",
            "//button[contains(text(),'login')]",
        ]:
            try:
                if sel.startswith("//"):
                    login_btn = driver.find_element(By.XPATH, sel)
                else:
                    login_btn = driver.find_element(By.CSS_SELECTOR, sel)
                if login_btn:
                    break
            except:
                continue

        if login_btn:
            login_btn.click()
            print("  Clicked login button")
        else:
            from selenium.webdriver.common.keys import Keys
            pwd_field.send_keys(Keys.RETURN)
            print("  Pressed Enter to login")

        time.sleep(6)
        screenshot(driver, "03_after_login")
        print(f"  Current URL after login: {driver.current_url}")
        return True
    except Exception as e:
        print(f"  LOGIN ERROR: {e}")
        screenshot(driver, "03_login_error")
        return False


def collect_all_links(driver):
    """Collect all <a> tags on the page."""
    print(f"\n{'='*80}")
    print("STEP 2: COLLECT ALL LINKS (<a> tags)")
    print(f"{'='*80}")

    links = driver.find_elements(By.TAG_NAME, 'a')
    link_data = []
    for i, link in enumerate(links):
        try:
            text = (link.text or "").strip()[:80]
            href = link.get_attribute('href') or ''
            classes = link.get_attribute('class') or ''
            link_id = link.get_attribute('id') or ''
            onclick = link.get_attribute('onclick') or ''
            target = link.get_attribute('target') or ''
            displayed = link.is_displayed()
            parent_text = ""
            try:
                parent = link.find_element(By.XPATH, '..')
                parent_text = (parent.get_attribute('class') or '')[:40]
            except:
                pass

            entry = {
                'index': i,
                'text': text,
                'href': href,
                'class': classes[:60],
                'id': link_id,
                'onclick': onclick[:80],
                'target': target,
                'displayed': displayed,
                'parent_class': parent_text,
            }
            link_data.append(entry)
            vis = "VISIBLE" if displayed else "hidden"
            print(f"  [{i:3d}] [{vis:7s}] {text:50s} -> {href[:120]}")
            if onclick:
                print(f"         onclick: {onclick[:100]}")
        except Exception as e:
            print(f"  [{i:3d}] ERROR reading link: {e}")
    print(f"\n  Total links found: {len(link_data)}")
    return link_data


def collect_all_buttons(driver):
    """Collect all <button> tags on the page."""
    print(f"\n{'='*80}")
    print("STEP 3: COLLECT ALL BUTTONS")
    print(f"{'='*80}")

    buttons = driver.find_elements(By.TAG_NAME, 'button')
    btn_data = []
    for i, btn in enumerate(buttons):
        try:
            text = (btn.text or "").strip()[:80]
            onclick = btn.get_attribute('onclick') or ''
            classes = btn.get_attribute('class') or ''
            btn_id = btn.get_attribute('id') or ''
            btn_type = btn.get_attribute('type') or ''
            displayed = btn.is_displayed()

            entry = {
                'index': i,
                'text': text,
                'onclick': onclick[:100],
                'class': classes[:60],
                'id': btn_id,
                'type': btn_type,
                'displayed': displayed,
            }
            btn_data.append(entry)
            vis = "VISIBLE" if displayed else "hidden"
            print(f"  BUTTON [{i:3d}] [{vis:7s}] {text:50s} | class: {classes[:40]}")
            if onclick:
                print(f"           onclick: {onclick[:100]}")
        except Exception as e:
            print(f"  BUTTON [{i:3d}] ERROR: {e}")
    print(f"\n  Total buttons found: {len(btn_data)}")
    return btn_data


def collect_clickable_elements(driver):
    """Find additional clickable elements: divs, spans with click handlers, cards, tiles."""
    print(f"\n{'='*80}")
    print("STEP 4: COLLECT CLICKABLE DIVS/CARDS/TILES")
    print(f"{'='*80}")

    clickable = []
    # Look for common dashboard card/tile patterns
    selectors = [
        "[onclick]",
        "[role='button']",
        "[role='link']",
        ".card[style*='cursor']",
        ".module-card",
        ".dashboard-card",
        ".tile",
        ".menu-item",
        ".nav-item",
        ".sidebar-item",
        "[data-href]",
        "[data-url]",
        "[data-link]",
        "[data-module]",
    ]
    for sel in selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                tag = elem.tag_name
                text = (elem.text or "").strip()[:60]
                onclick = elem.get_attribute('onclick') or ''
                data_href = elem.get_attribute('data-href') or elem.get_attribute('data-url') or ''
                if text or onclick or data_href:
                    entry = {
                        'selector': sel,
                        'tag': tag,
                        'text': text,
                        'onclick': onclick[:100],
                        'data_href': data_href,
                    }
                    clickable.append(entry)
                    print(f"  [{sel:30s}] <{tag}> {text:40s} | onclick: {onclick[:60]} | data: {data_href[:60]}")
        except:
            pass
    print(f"\n  Total clickable elements found: {len(clickable)}")
    return clickable


def check_module_links(link_data):
    """Find links that point to module subdomains."""
    print(f"\n{'='*80}")
    print("STEP 5: MODULE SUBDOMAIN LINKS")
    print(f"{'='*80}")

    module_links = []
    for entry in link_data:
        href = entry['href'].lower()
        text = entry['text'].lower()
        for sub in MODULE_SUBDOMAINS:
            if sub in href or sub in text:
                module_links.append(entry)
                print(f"  MODULE [{sub}]: {entry['text']} -> {entry['href']}")
                break
    if not module_links:
        print("  No direct module subdomain links found in <a> tags!")
    return module_links


def check_sso_links(link_data, btn_data):
    """Find links/buttons with SSO-related keywords."""
    print(f"\n{'='*80}")
    print("STEP 6: SSO / LAUNCH / REDIRECT KEYWORDS")
    print(f"{'='*80}")

    sso_items = []
    for entry in link_data:
        combined = f"{entry['href']} {entry['text']} {entry['onclick']} {entry['class']} {entry['id']}".lower()
        for kw in SSO_KEYWORDS:
            if kw in combined:
                sso_items.append(('link', entry, kw))
                print(f"  SSO-LINK [{kw}]: {entry['text']} -> {entry['href']}")
                break
    for entry in btn_data:
        combined = f"{entry['text']} {entry['onclick']} {entry['class']} {entry['id']}".lower()
        for kw in SSO_KEYWORDS:
            if kw in combined:
                sso_items.append(('button', entry, kw))
                print(f"  SSO-BUTTON [{kw}]: {entry['text']} | onclick: {entry['onclick']}")
                break
    if not sso_items:
        print("  No SSO/launch/redirect keywords found!")
    return sso_items


def scroll_and_capture(driver):
    """Scroll the full page and capture sections."""
    print(f"\n{'='*80}")
    print("STEP 7: FULL PAGE SCROLL & CAPTURE")
    print(f"{'='*80}")

    total_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    print(f"  Total page height: {total_height}px, Viewport: {viewport_height}px")

    scroll_pos = 0
    section = 0
    while scroll_pos < total_height:
        driver.execute_script(f"window.scrollTo(0, {scroll_pos})")
        time.sleep(0.5)
        screenshot(driver, f"04_scroll_section_{section:02d}_at_{scroll_pos}px")
        scroll_pos += viewport_height
        section += 1

    # Scroll back to top
    driver.execute_script("window.scrollTo(0, 0)")
    time.sleep(0.5)
    print(f"  Captured {section} scroll sections")


def check_sidebar_and_nav(driver):
    """Explore sidebar/navigation menus."""
    print(f"\n{'='*80}")
    print("STEP 8: SIDEBAR / NAVIGATION MENUS")
    print(f"{'='*80}")

    nav_selectors = [
        "nav a", ".sidebar a", ".nav a", ".menu a",
        "[class*='sidebar'] a", "[class*='nav'] a", "[class*='menu'] a",
        ".drawer a", "[class*='drawer'] a",
        "aside a", "header a",
    ]
    nav_links = {}
    for sel in nav_selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                text = (elem.text or "").strip()[:60]
                href = elem.get_attribute('href') or ''
                if text and href:
                    key = f"{text}|{href}"
                    if key not in nav_links:
                        nav_links[key] = {'text': text, 'href': href, 'selector': sel}
        except:
            pass

    for key, info in nav_links.items():
        print(f"  NAV: {info['text']:40s} -> {info['href'][:100]} (via {info['selector']})")
    print(f"\n  Total nav links: {len(nav_links)}")
    return nav_links


def click_module_links_and_track(driver, link_data):
    """Click each external module link, screenshot the result, print final URL."""
    print(f"\n{'='*80}")
    print("STEP 9: CLICK EACH EXTERNAL MODULE LINK -> TRACK NAVIGATION")
    print(f"{'='*80}")

    results = []
    dashboard_url = driver.current_url

    # Identify links worth clicking: module subdomains, or interesting internal routes
    interesting_links = []
    for entry in link_data:
        href = entry['href']
        text = entry['text']
        if not href or href == '#' or href.startswith('javascript:void'):
            continue
        # Module subdomain links
        is_module = any(sub in href.lower() for sub in MODULE_SUBDOMAINS)
        # SSO or launch keywords
        is_sso = any(kw in href.lower() or kw in text.lower() for kw in SSO_KEYWORDS)
        # Internal navigation links (not just anchors)
        is_internal_route = href.startswith(LOGIN_URL) and href != dashboard_url
        # External links
        is_external = not href.startswith(LOGIN_URL) and href.startswith('http')

        if is_module or is_sso or is_internal_route or is_external:
            interesting_links.append((entry, is_module, is_sso))

    if not interesting_links:
        # If no interesting links, just click all visible links
        print("  No external module links found. Will click ALL visible links...")
        for entry in link_data:
            if entry['displayed'] and entry['href'] and entry['href'] != '#':
                interesting_links.append((entry, False, False))

    print(f"\n  Will click {len(interesting_links)} interesting links\n")

    for i, (entry, is_module, is_sso) in enumerate(interesting_links[:40]):  # Limit to 40
        href = entry['href']
        text = entry['text'] or f"(no text, index {entry['index']})"
        tags = []
        if is_module:
            tags.append("MODULE")
        if is_sso:
            tags.append("SSO")
        tag_str = f" [{', '.join(tags)}]" if tags else ""

        print(f"\n  --- Click [{i+1}]{tag_str}: '{text}' -> {href[:120]} ---")

        try:
            # Open in new tab to preserve dashboard
            driver.execute_script(f"window.open('{href}', '_blank');")
            time.sleep(3)

            # Switch to new tab
            handles = driver.window_handles
            if len(handles) > 1:
                driver.switch_to.window(handles[-1])
                time.sleep(2)

                final_url = driver.current_url
                page_title = driver.title
                print(f"    FINAL URL: {final_url}")
                print(f"    PAGE TITLE: {page_title}")

                # Check for SSO tokens in URL
                if 'token' in final_url.lower() or 'sso' in final_url.lower() or 'auth' in final_url.lower():
                    print(f"    *** SSO/TOKEN DETECTED IN URL ***")

                safe_name = f"05_click_{i:02d}_{text[:30].replace(' ','_')}"
                screenshot(driver, safe_name)

                result = {
                    'link_text': text,
                    'original_href': href,
                    'final_url': final_url,
                    'page_title': page_title,
                    'is_module': is_module,
                    'is_sso': is_sso,
                    'has_token_in_url': 'token' in final_url.lower(),
                }
                results.append(result)

                # Close tab and go back to dashboard
                driver.close()
                driver.switch_to.window(handles[0])
                time.sleep(0.5)
            else:
                print("    (no new tab opened)")
        except Exception as e:
            print(f"    ERROR clicking: {e}")
            # Try to recover
            try:
                handles = driver.window_handles
                if len(handles) > 1:
                    driver.switch_to.window(handles[-1])
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except:
                pass

    return results


def inspect_network_for_sso(driver):
    """Check for SSO patterns in page source and network."""
    print(f"\n{'='*80}")
    print("STEP 10: INSPECT PAGE SOURCE FOR SSO MECHANISMS")
    print(f"{'='*80}")

    source = driver.page_source

    # Look for SSO-related patterns
    patterns = ['sso', 'single-sign-on', 'oauth', 'token', 'jwt', 'redirect',
                'launch', 'cross-domain', 'postMessage', 'iframe']
    for pat in patterns:
        if pat.lower() in source.lower():
            # Find context around the match
            idx = source.lower().find(pat.lower())
            snippet = source[max(0, idx-80):idx+120]
            snippet = snippet.replace('\n', ' ').strip()
            print(f"  FOUND '{pat}' in page source: ...{snippet}...")

    # Check localStorage and sessionStorage for tokens
    try:
        local_storage = driver.execute_script("""
            var items = {};
            for (var i = 0; i < localStorage.length; i++) {
                var key = localStorage.key(i);
                var val = localStorage.getItem(key);
                if (val && val.length < 500) items[key] = val.substring(0, 200);
                else if (val) items[key] = val.substring(0, 200) + '...(truncated)';
            }
            return items;
        """)
        print(f"\n  LOCAL STORAGE ({len(local_storage)} items):")
        for k, v in local_storage.items():
            print(f"    {k}: {v[:150]}")
    except Exception as e:
        print(f"  localStorage error: {e}")

    try:
        session_storage = driver.execute_script("""
            var items = {};
            for (var i = 0; i < sessionStorage.length; i++) {
                var key = sessionStorage.key(i);
                var val = sessionStorage.getItem(key);
                if (val && val.length < 500) items[key] = val.substring(0, 200);
                else if (val) items[key] = val.substring(0, 200) + '...(truncated)';
            }
            return items;
        """)
        print(f"\n  SESSION STORAGE ({len(session_storage)} items):")
        for k, v in session_storage.items():
            print(f"    {k}: {v[:150]}")
    except Exception as e:
        print(f"  sessionStorage error: {e}")

    # Check cookies
    try:
        cookies = driver.get_cookies()
        print(f"\n  COOKIES ({len(cookies)}):")
        for c in cookies:
            val = str(c.get('value', ''))[:100]
            print(f"    {c['name']}: {val} | domain: {c.get('domain', '')} | path: {c.get('path', '')}")
    except Exception as e:
        print(f"  cookies error: {e}")


def check_js_functions(driver):
    """Look for JS functions related to SSO/navigation."""
    print(f"\n{'='*80}")
    print("STEP 11: CHECK JS FUNCTIONS FOR SSO/NAVIGATION")
    print(f"{'='*80}")

    scripts = driver.find_elements(By.TAG_NAME, 'script')
    print(f"  Found {len(scripts)} <script> tags")

    for i, script in enumerate(scripts):
        src = script.get_attribute('src') or ''
        content = script.get_attribute('innerHTML') or ''
        if src:
            print(f"  SCRIPT [{i}] src: {src[:120]}")
        if content and len(content) > 10:
            # Check for SSO patterns in inline scripts
            for pat in ['sso', 'token', 'redirect', 'launch', 'navigate', 'module', 'subdomain']:
                if pat in content.lower():
                    idx = content.lower().find(pat)
                    snippet = content[max(0,idx-50):idx+100].replace('\n',' ').strip()
                    print(f"  SCRIPT [{i}] contains '{pat}': ...{snippet[:150]}...")
                    break


def try_direct_module_navigation(driver):
    """Try navigating directly to module URLs to understand SSO flow."""
    print(f"\n{'='*80}")
    print("STEP 12: DIRECT MODULE URL NAVIGATION (SSO FLOW TEST)")
    print(f"{'='*80}")

    module_urls = [
        ("Payroll", "https://testpayroll.empcloud.com"),
        ("Recruit", "https://test-recruit.empcloud.com"),
        ("Performance", "https://test-performance.empcloud.com"),
        ("Rewards", "https://test-rewards.empcloud.com"),
        ("Exit", "https://test-exit.empcloud.com"),
        ("LMS", "https://testlms.empcloud.com"),
        ("Project", "https://test-project.empcloud.com"),
    ]

    dashboard_handle = driver.current_window_handle
    results = []

    for name, url in module_urls:
        print(f"\n  --- Trying direct navigation to {name}: {url} ---")
        try:
            driver.execute_script(f"window.open('{url}', '_blank');")
            time.sleep(4)
            handles = driver.window_handles
            if len(handles) > 1:
                driver.switch_to.window(handles[-1])
                time.sleep(2)
                final_url = driver.current_url
                title = driver.title
                print(f"    FINAL URL: {final_url}")
                print(f"    TITLE: {title}")

                if final_url != url and final_url != url + '/':
                    print(f"    *** REDIRECTED! Original: {url} -> Final: {final_url} ***")

                screenshot(driver, f"06_direct_{name}")

                results.append({
                    'module': name,
                    'attempted_url': url,
                    'final_url': final_url,
                    'title': title,
                    'was_redirected': final_url.rstrip('/') != url.rstrip('/'),
                })

                driver.close()
                driver.switch_to.window(dashboard_handle)
                time.sleep(0.5)
        except Exception as e:
            print(f"    ERROR: {e}")
            try:
                handles = driver.window_handles
                if len(handles) > 1:
                    driver.switch_to.window(handles[-1])
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except:
                pass

    return results


def print_final_summary(link_data, btn_data, click_results, direct_results):
    """Print a complete summary map."""
    print(f"\n{'='*80}")
    print("FINAL SUMMARY: COMPLETE DASHBOARD MAP")
    print(f"{'='*80}")

    print(f"\n--- ALL LINKS ({len(link_data)}) ---")
    print(f"{'Text':<50} {'URL':<80} {'Visible':<8}")
    print("-" * 140)
    for entry in link_data:
        vis = "Y" if entry['displayed'] else "N"
        print(f"{entry['text']:<50} {entry['href'][:80]:<80} {vis:<8}")

    print(f"\n--- ALL BUTTONS ({len(btn_data)}) ---")
    print(f"{'Text':<50} {'Class':<50} {'Visible':<8}")
    print("-" * 110)
    for entry in btn_data:
        vis = "Y" if entry['displayed'] else "N"
        print(f"{entry['text'][:50]:<50} {entry['class'][:50]:<50} {vis:<8}")

    if click_results:
        print(f"\n--- CLICK NAVIGATION RESULTS ({len(click_results)}) ---")
        print(f"{'Link Text':<40} {'Original URL':<60} {'Final URL':<60} {'Token?':<6}")
        print("-" * 170)
        for r in click_results:
            print(f"{r['link_text'][:40]:<40} {r['original_href'][:60]:<60} {r['final_url'][:60]:<60} {str(r['has_token_in_url']):<6}")

    if direct_results:
        print(f"\n--- DIRECT MODULE NAVIGATION ({len(direct_results)}) ---")
        print(f"{'Module':<20} {'Attempted URL':<50} {'Final URL':<60} {'Redirected?':<12}")
        print("-" * 145)
        for r in direct_results:
            print(f"{r['module']:<20} {r['attempted_url']:<50} {r['final_url'][:60]:<60} {str(r['was_redirected']):<12}")

    print(f"\n{'='*80}")
    print("SSO MECHANISM ANALYSIS")
    print(f"{'='*80}")

    # Analyze SSO
    token_links = [r for r in click_results if r.get('has_token_in_url')]
    redirected_modules = [r for r in direct_results if r.get('was_redirected')]

    if token_links:
        print("\n  SSO TOKEN PASSING detected in these links:")
        for r in token_links:
            print(f"    {r['link_text']} -> {r['final_url'][:120]}")
    if redirected_modules:
        print("\n  REDIRECT-BASED SSO detected for these modules:")
        for r in redirected_modules:
            print(f"    {r['module']}: {r['attempted_url']} -> {r['final_url'][:120]}")

    print("\n  DONE.\n")


def main():
    driver = make_driver()
    try:
        if not login(driver):
            print("Login failed. Aborting.")
            return

        # Collect everything on the dashboard
        link_data = collect_all_links(driver)
        btn_data = collect_all_buttons(driver)
        clickable_data = collect_clickable_elements(driver)
        scroll_and_capture(driver)
        nav_links = check_sidebar_and_nav(driver)
        module_links = check_module_links(link_data)
        sso_items = check_sso_links(link_data, btn_data)

        # Inspect for SSO mechanisms
        inspect_network_for_sso(driver)
        check_js_functions(driver)

        # Click each interesting link
        click_results = click_module_links_and_track(driver, link_data)

        # Try direct module URLs
        direct_results = try_direct_module_navigation(driver)

        # Print final summary
        print_final_summary(link_data, btn_data, click_results, direct_results)

    finally:
        driver.quit()
        print("\nBrowser closed.")


if __name__ == "__main__":
    main()
