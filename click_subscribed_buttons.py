import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_click_subscribed"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

LOGIN_URL = "https://test-empcloud.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  [Screenshot] {path}")

def setup_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    return driver

def login(driver):
    print("=== LOGGING IN ===")
    driver.get(LOGIN_URL + "/login")
    time.sleep(4)

    try:
        # Click somewhere neutral first to dismiss any dropdowns
        driver.find_element(By.TAG_NAME, "body").click()
        time.sleep(1)

        email_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail']"))
        )
        email_field.clear()
        email_field.send_keys(EMAIL)
        time.sleep(0.5)

        pw_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        pw_field.clear()
        pw_field.send_keys(PASSWORD)
        time.sleep(0.5)

        # Find sign in button specifically
        sign_in_btn = None
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            txt = b.text.strip().lower()
            if txt in ["sign in", "login", "log in", "signin"]:
                sign_in_btn = b
                break
        if not sign_in_btn:
            sign_in_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

        print(f"  Clicking: '{sign_in_btn.text.strip()}'")
        sign_in_btn.click()
        time.sleep(8)

        screenshot(driver, "01_after_login")
        print(f"  Current URL after login: {driver.current_url}")

        # Check if still on login page
        if "/login" in driver.current_url:
            print("  WARNING: Still on login page, trying JS click...")
            driver.execute_script("arguments[0].click();", sign_in_btn)
            time.sleep(8)
            screenshot(driver, "01_after_login_retry")
            print(f"  Current URL after retry: {driver.current_url}")

    except Exception as e:
        print(f"  Login error: {e}")
        screenshot(driver, "01_login_error")

def go_to_modules(driver):
    print("\n=== NAVIGATING TO /modules ===")
    driver.get(LOGIN_URL + "/modules")
    time.sleep(5)
    screenshot(driver, "02_modules_page")
    print(f"  Current URL: {driver.current_url}")

def find_all_interactive_elements(driver):
    """Find all buttons/links with relevant text on the modules page."""
    print("\n=== FINDING ALL INTERACTIVE ELEMENTS ===")

    # Find all elements that might be module rows/cards
    # Look for buttons, links, and any clickable elements
    keywords = ["Subscribed", "Launch", "Open", "View Details", "Manage", "Subscribe", "Active", "Explore"]

    results = []

    # Strategy 1: Find buttons and links by text
    all_buttons = driver.find_elements(By.CSS_SELECTOR, "button, a, [role='button'], .btn, [class*='btn']")
    print(f"  Found {len(all_buttons)} total button/link elements")

    for elem in all_buttons:
        try:
            text = elem.text.strip()
            if not text:
                continue
            for kw in keywords:
                if kw.lower() in text.lower():
                    tag = elem.tag_name
                    classes = elem.get_attribute("class") or ""
                    href = elem.get_attribute("href") or ""
                    onclick = elem.get_attribute("onclick") or ""
                    data_href = elem.get_attribute("data-href") or ""
                    aria = elem.get_attribute("aria-label") or ""

                    # Try to find parent module name
                    module_name = "Unknown"
                    try:
                        parent = elem.find_element(By.XPATH, "./ancestor::div[contains(@class,'card') or contains(@class,'module') or contains(@class,'row') or contains(@class,'col')]")
                        headings = parent.find_elements(By.CSS_SELECTOR, "h1,h2,h3,h4,h5,h6,.title,.module-name,[class*='title'],[class*='name']")
                        for h in headings:
                            ht = h.text.strip()
                            if ht and ht != text:
                                module_name = ht
                                break
                        if module_name == "Unknown":
                            ptxt = parent.text.strip().split('\n')[0][:60]
                            if ptxt and ptxt != text:
                                module_name = ptxt
                    except:
                        pass

                    results.append({
                        'element': elem,
                        'text': text,
                        'tag': tag,
                        'class': classes,
                        'href': href,
                        'onclick': onclick,
                        'data_href': data_href,
                        'aria': aria,
                        'module_name': module_name
                    })
                    break
        except:
            continue

    # Strategy 2: Also look for card-level clickable elements
    cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='module'], [class*='subscription']")
    print(f"  Found {len(cards)} card-like elements")

    print(f"\n  === FOUND {len(results)} INTERACTIVE ELEMENTS ===")
    for i, r in enumerate(results):
        print(f"\n  [{i+1}] Module: {r['module_name']}")
        print(f"      Button text: '{r['text']}'")
        print(f"      Tag: {r['tag']}")
        print(f"      Class: {r['class'][:100]}")
        print(f"      Href: {r['href']}")
        print(f"      Onclick: {r['onclick']}")
        print(f"      Data-href: {r['data_href']}")
        print(f"      Aria: {r['aria']}")

    return results

def dump_page_source_snippet(driver):
    """Dump relevant parts of the page source for analysis."""
    print("\n=== PAGE SOURCE ANALYSIS ===")
    try:
        # Get all text content to understand layout
        body = driver.find_element(By.TAG_NAME, "body")
        body_text = body.text
        print(f"  Full page text (first 3000 chars):")
        print(f"  {body_text[:3000]}")

        # Also check for hidden links/forms
        all_links = driver.find_elements(By.TAG_NAME, "a")
        print(f"\n  All links on page ({len(all_links)}):")
        for link in all_links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()[:60]
            if href and ("empcloud" in href or "sso" in href.lower() or "token" in href.lower() or "module" in href.lower()):
                print(f"    [{text}] -> {href}")
    except Exception as e:
        print(f"  Error: {e}")

def click_each_module(driver, elements):
    """Click each module button one by one."""
    print("\n=== CLICKING EACH MODULE BUTTON ===")

    for i, elem_info in enumerate(elements):
        idx = i + 1
        print(f"\n--- Module {idx}: {elem_info['module_name']} (button: '{elem_info['text']}') ---")

        # Go back to modules page first
        driver.get(LOGIN_URL + "/modules")
        time.sleep(3)

        url_before = driver.current_url
        handles_before = driver.window_handles
        print(f"  URL before: {url_before}")
        print(f"  Window handles before: {len(handles_before)}")

        screenshot(driver, f"03_module_{idx:02d}_before_{elem_info['module_name'].replace(' ','_')[:20]}")

        try:
            # Re-find the element (page was reloaded)
            time.sleep(2)

            # Try to find the same button again
            btn_text = elem_info['text']
            found = False

            # Try multiple strategies to re-find
            buttons = driver.find_elements(By.CSS_SELECTOR, "button, a, [role='button']")
            target = None
            for b in buttons:
                try:
                    if b.text.strip() == btn_text:
                        # Check if it's the right module
                        target = b
                        # If we have multiple with same text, try to match by index
                except:
                    continue

            if not target:
                # Try by xpath text match
                try:
                    target = driver.find_element(By.XPATH, f"//*[normalize-space(text())='{btn_text}']")
                except:
                    pass

            if not target:
                print(f"  Could not re-find button with text '{btn_text}', skipping")
                continue

            # If there are multiple buttons with same text, get the i-th one
            matching_buttons = []
            for b in buttons:
                try:
                    if b.text.strip() == btn_text:
                        matching_buttons.append(b)
                except:
                    continue

            if i < len(matching_buttons):
                target = matching_buttons[i]
            elif matching_buttons:
                target = matching_buttons[0]

            print(f"  Clicking button...")

            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
            time.sleep(1)

            # Click
            try:
                target.click()
            except:
                driver.execute_script("arguments[0].click();", target)

            time.sleep(5)

            url_after = driver.current_url
            handles_after = driver.window_handles

            print(f"  URL after: {url_after}")
            print(f"  Window handles after: {len(handles_after)}")
            print(f"  URL changed? {'YES' if url_before != url_after else 'NO'}")
            print(f"  SSO token in URL? {'YES' if 'sso_token' in url_after or 'token' in url_after else 'NO'}")

            # Check new windows/tabs
            if len(handles_after) > len(handles_before):
                print(f"  NEW WINDOW/TAB OPENED!")
                for h in handles_after:
                    if h not in handles_before:
                        driver.switch_to.window(h)
                        time.sleep(3)
                        new_url = driver.current_url
                        print(f"  New tab URL: {new_url}")
                        print(f"  SSO token in new tab? {'YES' if 'sso_token' in new_url or 'token' in new_url else 'NO'}")
                        screenshot(driver, f"03_module_{idx:02d}_newtab_{elem_info['module_name'].replace(' ','_')[:20]}")
                        driver.close()
                # Switch back to original
                driver.switch_to.window(handles_before[0])

            screenshot(driver, f"03_module_{idx:02d}_after_{elem_info['module_name'].replace(' ','_')[:20]}")

            # Check for modals/popups
            try:
                modals = driver.find_elements(By.CSS_SELECTOR, ".modal, [role='dialog'], .popup, .overlay, [class*='modal'], [class*='dialog']")
                visible_modals = [m for m in modals if m.is_displayed()]
                if visible_modals:
                    print(f"  MODAL/DIALOG appeared! Count: {len(visible_modals)}")
                    for m in visible_modals:
                        print(f"    Modal text: {m.text[:200]}")
                    screenshot(driver, f"03_module_{idx:02d}_modal_{elem_info['module_name'].replace(' ','_')[:20]}")
            except:
                pass

        except Exception as e:
            print(f"  Error clicking: {e}")
            screenshot(driver, f"03_module_{idx:02d}_error_{elem_info['module_name'].replace(' ','_')[:20]}")

def click_module_names(driver):
    """Try clicking on module names/titles instead of buttons."""
    print("\n\n=== CLICKING MODULE NAMES (NOT BUTTONS) ===")

    driver.get(LOGIN_URL + "/modules")
    time.sleep(4)

    # Find module name elements - headings inside cards
    name_selectors = [
        "[class*='card'] h1, [class*='card'] h2, [class*='card'] h3, [class*='card'] h4, [class*='card'] h5",
        "[class*='module'] h1, [class*='module'] h2, [class*='module'] h3, [class*='module'] h4, [class*='module'] h5",
        "[class*='card'] [class*='title'], [class*='card'] [class*='name']",
        "[class*='module'] [class*='title'], [class*='module'] [class*='name']",
    ]

    module_names = []
    for sel in name_selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in elems:
                t = e.text.strip()
                if t and len(t) < 50 and t not in [m['text'] for m in module_names]:
                    module_names.append({'element': e, 'text': t})
        except:
            continue

    if not module_names:
        # Fallback: look for any text that matches known module names
        known_modules = ["EmpCloud", "Recruit", "Performance", "Rewards", "Exit", "LMS", "Payroll", "Project", "Monitor",
                         "HRMS", "Leave", "Attendance", "Onboarding", "emp-core", "Field Force", "Biometrics"]
        all_elems = driver.find_elements(By.CSS_SELECTOR, "*")
        for e in all_elems:
            try:
                t = e.text.strip()
                for km in known_modules:
                    if t == km:
                        module_names.append({'element': e, 'text': t})
                        break
            except:
                continue

    print(f"  Found {len(module_names)} module name elements")
    for mn in module_names:
        print(f"    - '{mn['text']}'")

    for i, mn in enumerate(module_names[:10]):  # Limit to 10
        print(f"\n  Clicking module name: '{mn['text']}'")

        driver.get(LOGIN_URL + "/modules")
        time.sleep(3)

        url_before = driver.current_url
        handles_before = driver.window_handles

        try:
            # Re-find
            # Try direct text match
            target = None
            try:
                targets = driver.find_elements(By.XPATH, f"//*[normalize-space(text())='{mn['text']}']")
                if targets:
                    target = targets[0]
            except:
                pass

            if not target:
                print(f"    Could not re-find '{mn['text']}', skipping")
                continue

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
            time.sleep(1)

            try:
                target.click()
            except:
                driver.execute_script("arguments[0].click();", target)

            time.sleep(5)

            url_after = driver.current_url
            handles_after = driver.window_handles

            print(f"    URL before: {url_before}")
            print(f"    URL after: {url_after}")
            print(f"    Changed? {'YES' if url_before != url_after else 'NO'}")
            print(f"    SSO token? {'YES' if 'sso_token' in url_after or 'token' in url_after else 'NO'}")

            if len(handles_after) > len(handles_before):
                print(f"    NEW TAB opened!")
                for h in handles_after:
                    if h not in handles_before:
                        driver.switch_to.window(h)
                        time.sleep(3)
                        print(f"    New tab URL: {driver.current_url}")
                        screenshot(driver, f"04_modname_{i:02d}_{mn['text'].replace(' ','_')[:15]}")
                        driver.close()
                driver.switch_to.window(handles_before[0])

            screenshot(driver, f"04_modname_{i:02d}_after_{mn['text'].replace(' ','_')[:15]}")

        except Exception as e:
            print(f"    Error: {e}")

def check_right_click_links(driver):
    """Check href attributes that might reveal SSO URLs."""
    print("\n\n=== CHECKING FOR SSO URLS IN HREF/DATA ATTRIBUTES ===")

    driver.get(LOGIN_URL + "/modules")
    time.sleep(4)

    # Get full page source and look for SSO patterns
    source = driver.page_source

    import re

    # Look for SSO-related URLs
    sso_patterns = [
        r'sso[_-]?token[=:]["\']?([^"\'&\s]+)',
        r'token[=:]["\']?([^"\'&\s]+)',
        r'https?://[^"\'>\s]*sso[^"\'>\s]*',
        r'https?://[^"\'>\s]*token[^"\'>\s]*',
        r'redirect[_-]?url[=:]["\']?([^"\'&\s]+)',
    ]

    print("  Searching page source for SSO patterns...")
    for pattern in sso_patterns:
        matches = re.findall(pattern, source, re.IGNORECASE)
        if matches:
            print(f"  Pattern '{pattern}':")
            for m in matches[:5]:
                print(f"    -> {m[:200]}")

    # Check all elements for data attributes
    all_with_data = driver.find_elements(By.CSS_SELECTOR, "[data-url], [data-href], [data-link], [data-redirect], [data-sso]")
    print(f"\n  Elements with data-url/href/link/redirect/sso: {len(all_with_data)}")
    for e in all_with_data:
        attrs = {}
        for attr in ['data-url', 'data-href', 'data-link', 'data-redirect', 'data-sso']:
            val = e.get_attribute(attr)
            if val:
                attrs[attr] = val
        if attrs:
            print(f"    {e.tag_name} [{e.text[:30]}]: {attrs}")

    # Check all anchor tags
    all_anchors = driver.find_elements(By.TAG_NAME, "a")
    print(f"\n  All anchor hrefs ({len(all_anchors)}):")
    for a in all_anchors:
        href = a.get_attribute("href") or ""
        text = a.text.strip()[:40]
        if href and href != "javascript:void(0)" and href != "#":
            print(f"    [{text}] -> {href}")

def inspect_network_on_click(driver):
    """Use CDP to capture network requests when clicking subscribed buttons."""
    print("\n\n=== MONITORING NETWORK REQUESTS ON CLICK ===")

    driver.get(LOGIN_URL + "/modules")
    time.sleep(4)

    # Enable network tracking via CDP
    driver.execute_cdp_cmd("Network.enable", {})

    # Find subscribed buttons
    buttons = driver.find_elements(By.CSS_SELECTOR, "button, a, [role='button']")
    subscribed_buttons = []
    for b in buttons:
        try:
            if "subscribed" in b.text.strip().lower() or "launch" in b.text.strip().lower():
                subscribed_buttons.append(b)
        except:
            continue

    if not subscribed_buttons:
        print("  No subscribed/launch buttons found for network monitoring")
        return

    print(f"  Found {len(subscribed_buttons)} subscribed/launch buttons")

    # Click the first one and capture via JS
    # Intercept window.open
    driver.execute_script("""
        window.__captured_urls = [];
        window.__orig_open = window.open;
        window.open = function(url) {
            window.__captured_urls.push(url);
            console.log('INTERCEPTED window.open: ' + url);
            return window.__orig_open.apply(this, arguments);
        };

        // Also intercept location changes
        window.__orig_assign = window.location.assign;
        // Can't easily override location.href, but let's try
    """)

    for i, btn in enumerate(subscribed_buttons[:5]):
        print(f"\n  Clicking button {i+1}: '{btn.text.strip()}'")

        handles_before = driver.window_handles
        url_before = driver.current_url

        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(1)

            try:
                btn.click()
            except:
                driver.execute_script("arguments[0].click();", btn)

            time.sleep(5)

            # Check captured URLs
            captured = driver.execute_script("return window.__captured_urls || [];")
            if captured:
                print(f"  CAPTURED window.open URLs:")
                for u in captured:
                    print(f"    -> {u}")

            url_after = driver.current_url
            handles_after = driver.window_handles

            print(f"  URL: {url_before} -> {url_after}")

            if len(handles_after) > len(handles_before):
                for h in handles_after:
                    if h not in handles_before:
                        driver.switch_to.window(h)
                        time.sleep(3)
                        print(f"  NEW TAB URL: {driver.current_url}")
                        screenshot(driver, f"05_network_{i:02d}_newtab")
                        driver.close()
                driver.switch_to.window(handles_before[0])

            # Go back to modules
            driver.get(LOGIN_URL + "/modules")
            time.sleep(3)

            # Re-inject interceptor
            driver.execute_script("""
                window.__captured_urls = [];
                window.__orig_open = window.__orig_open || window.open;
                window.open = function(url) {
                    window.__captured_urls.push(url);
                    return window.__orig_open.apply(this, arguments);
                };
            """)

            # Re-find buttons
            buttons = driver.find_elements(By.CSS_SELECTOR, "button, a, [role='button']")
            subscribed_buttons = []
            for b in buttons:
                try:
                    if "subscribed" in b.text.strip().lower() or "launch" in b.text.strip().lower():
                        subscribed_buttons.append(b)
                except:
                    continue

        except Exception as e:
            print(f"  Error: {e}")

def dump_full_html_of_module_cards(driver):
    """Get the raw HTML of module cards for detailed analysis."""
    print("\n\n=== RAW HTML OF MODULE CARDS ===")

    driver.get(LOGIN_URL + "/modules")
    time.sleep(4)

    # Try to get the main content area HTML
    selectors = [
        "[class*='module']", "[class*='subscription']", "[class*='card']",
        "main", "[class*='content']", "[class*='grid']"
    ]

    for sel in selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                print(f"\n  Selector '{sel}' found {len(elems)} elements")
                for i, e in enumerate(elems[:5]):
                    html = e.get_attribute("outerHTML")
                    if html and len(html) > 50:
                        print(f"  Element {i+1} HTML ({len(html)} chars):")
                        print(f"  {html[:500]}")
                        print(f"  ...")
        except:
            continue


def main():
    driver = setup_driver()

    try:
        login(driver)
        go_to_modules(driver)

        # Dump page text for understanding
        dump_page_source_snippet(driver)

        # Find all interactive elements
        elements = find_all_interactive_elements(driver)

        # Dump raw HTML for analysis
        dump_full_html_of_module_cards(driver)

        # Check for SSO URLs in page source
        check_right_click_links(driver)

        # Click each module button
        if elements:
            click_each_module(driver, elements)

        # Try clicking module names
        click_module_names(driver)

        # Monitor network on click
        inspect_network_on_click(driver)

        print("\n\n=== DONE ===")

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        screenshot(driver, "fatal_error")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
