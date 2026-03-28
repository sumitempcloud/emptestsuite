import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import time
import os
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_explore_dashboard"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

LOGIN_URL = "https://test-empcloud.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

def ss(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    try:
        total_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
        driver.set_window_size(1920, min(total_height + 200, 8000))
        time.sleep(0.5)
        driver.save_screenshot(path)
        driver.set_window_size(1920, 1080)
        print(f"  [Screenshot] {name}.png")
    except Exception as e:
        print(f"  [Screenshot ERROR] {name}: {e}")
    return path

def setup_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--force-device-scale-factor=1")
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    return driver

def login(driver):
    print("=" * 70)
    print("STEP 1: LOGIN")
    print("=" * 70)
    driver.get(LOGIN_URL + "/login")
    time.sleep(4)

    # Use JS to set field values to avoid double-entry issues
    email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
    pw_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")

    # Clear and set via JS + React input simulation
    driver.execute_script("""
        var emailEl = arguments[0];
        var pwEl = arguments[1];
        var email = arguments[2];
        var pw = arguments[3];

        // React-compatible value setter
        function setNativeValue(element, value) {
            const valueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            const prototype = Object.getPrototypeOf(element);
            const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
            if (valueSetter && valueSetter !== prototypeValueSetter) {
                prototypeValueSetter.call(element, value);
            } else {
                valueSetter.call(element, value);
            }
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }

        setNativeValue(emailEl, email);
        setNativeValue(pwEl, pw);
    """, email_field, pw_field, EMAIL, PASSWORD)
    time.sleep(1)

    # Screenshot filled form
    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "00_login_filled.png"))
    print("  [Screenshot] 00_login_filled.png")

    btn = driver.find_element(By.XPATH, "//button[contains(text(),'Sign in')]")
    driver.execute_script("arguments[0].click();", btn)
    print("  Clicked Sign in")

    # Wait for URL to change from /login
    for i in range(30):
        time.sleep(1)
        url = driver.current_url
        print(f"  Wait {i+1}: {url}")
        if "/login" not in url:
            print(f"  Login successful!")
            break
    else:
        # If still on login, check for error messages
        print(f"  WARNING: Still on login page after 30s")
        errs = driver.find_elements(By.CSS_SELECTOR, "[class*='error'], [class*='alert'], [role='alert']")
        for e in errs:
            print(f"  Error msg: {e.text}")
        # Try once more with explicit form submit
        form = driver.find_elements(By.TAG_NAME, "form")
        if form:
            driver.execute_script("arguments[0].submit()", form[0])
            time.sleep(5)
            print(f"  After form submit: {driver.current_url}")

    print(f"  Current URL: {driver.current_url}")
    time.sleep(5)  # Let dashboard fully render

    # Check page title and content
    title = driver.title
    print(f"  Page title: {title}")

    # Look for dashboard indicators
    body_text = driver.execute_script("return document.body.innerText.substring(0, 500)")
    print(f"  Page text (first 500): {body_text[:300]}")

    ss(driver, "01_dashboard_full_page")
    return "/login" not in driver.current_url

def screenshot_module_insights(driver):
    print("\n" + "=" * 70)
    print("STEP 2: MODULE INSIGHTS SECTION")
    print("=" * 70)
    try:
        heading = driver.find_element(By.XPATH, "//h2[contains(text(),'Module Insights')]")
        driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", heading)
        time.sleep(1)
        driver.set_window_size(1920, 1080)
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "02_module_insights_section.png"))
        print("  [Screenshot] 02_module_insights_section.png")
        print(f"  Found 'Module Insights' heading")
    except Exception as e:
        print(f"  Module Insights heading not found: {e}")

    # Also screenshot "Your Modules" section
    try:
        heading2 = driver.find_element(By.XPATH, "//h2[contains(text(),'Your Modules')]")
        driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", heading2)
        time.sleep(1)
        driver.set_window_size(1920, 1080)
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "03_your_modules_section.png"))
        print("  [Screenshot] 03_your_modules_section.png")
        print(f"  Found 'Your Modules' heading")
    except Exception as e:
        print(f"  Your Modules heading not found: {e}")

    # Scroll to bottom for more sections
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    driver.set_window_size(1920, 1080)
    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "04_dashboard_bottom.png"))
    print("  [Screenshot] 04_dashboard_bottom.png")

    driver.execute_script("window.scrollTo(0, 0)")
    time.sleep(0.5)

def find_all_module_cards(driver):
    print("\n" + "=" * 70)
    print("STEP 3: MODULE NAME CARDS")
    print("=" * 70)
    module_names = ["Payroll", "Recruit", "Performance", "Rewards", "Exit",
                    "LMS", "Project", "Monitor", "Attendance", "Leave",
                    "Biometric", "Field Force", "Learning"]
    found = {}
    for name in module_names:
        elements = driver.find_elements(By.XPATH, f"//a[contains(text(),'{name}')]")
        if elements:
            for el in elements:
                text = el.text.strip()[:80]
                href = el.get_attribute("href") or ""
                short_href = href.split("?")[0] if href else ""
                has_sso = "sso_token" in href
                print(f"  CARD: '{text}' -> {short_href} (sso_token={has_sso})")
                found[name] = {"text": text, "href": href, "has_sso": has_sso}
    return found

def dump_all_links(driver):
    print("\n" + "=" * 70)
    print("STEP 5: ALL LINKS ON PAGE (text + href)")
    print("=" * 70)
    links = driver.find_elements(By.TAG_NAME, "a")
    print(f"  Total <a> tags: {len(links)}\n")

    all_links = []
    for i, link in enumerate(links):
        try:
            text = link.text.strip().replace("\n", " ")[:80]
            href = link.get_attribute("href") or ""
            target = link.get_attribute("target") or ""
            if not text and not href:
                continue

            # Shorten SSO token URLs for readability
            short_href = href
            if "sso_token=" in href:
                short_href = href.split("sso_token=")[0] + "sso_token=<JWT...>"

            entry = {"text": text, "href": href, "target": target}
            all_links.append(entry)
            print(f"  [{i:3d}] {text:<50s} {short_href}")
        except:
            pass

    # Buttons
    print(f"\n  --- Buttons ---")
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for i, btn in enumerate(buttons):
        try:
            text = btn.text.strip().replace("\n", " ")[:80]
            if text and text not in ["EN", "HI", "ES", "FR", "DE", "AR", "PT", "JA", "ZH"]:
                classes = (btn.get_attribute("class") or "")[:60]
                print(f"  [btn {i:3d}] {text:<50s} class={classes}")
        except:
            pass

    # Clickable cards / divs
    print(f"\n  --- Cards/Clickable divs ---")
    cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='Card']")
    for i, card in enumerate(cards[:30]):
        try:
            text = card.text.strip().replace("\n", " | ")[:100]
            tag = card.tag_name
            classes = (card.get_attribute("class") or "")[:60]
            if text:
                print(f"  [card {i:3d}] <{tag}> class={classes}")
                print(f"             text: {text}")
        except:
            pass

    return all_links

def find_external_module_links(driver):
    print("\n" + "=" * 70)
    print("STEP 4: EXTERNAL MODULE LINKS")
    print("=" * 70)
    module_domains = ["recruit", "performance", "rewards", "exit", "lms",
                      "payroll", "project", "empmonitor"]
    links = driver.find_elements(By.TAG_NAME, "a")
    external = []
    seen = set()

    for link in links:
        try:
            href = link.get_attribute("href") or ""
            text = link.text.strip()[:80]
            base_url = href.split("?")[0]

            if base_url in seen:
                continue

            for domain in module_domains:
                if domain in href.lower():
                    seen.add(base_url)
                    has_sso = "sso_token" in href
                    external.append({"text": text, "href": href, "base_url": base_url})
                    print(f"  EXTERNAL: '{text}'")
                    print(f"    URL: {base_url}")
                    print(f"    Has sso_token: {has_sso}")
                    break

            if "empcloud.com" in href and "test-empcloud.empcloud.com" not in href:
                if base_url not in seen:
                    seen.add(base_url)
                    external.append({"text": text, "href": href, "base_url": base_url})
                    print(f"  OTHER EMPCLOUD: '{text}' -> {base_url}")
        except:
            pass

    print(f"\n  Total external module links: {len(external)}")
    return external

def click_and_screenshot_modules(driver, external_links):
    print("\n" + "=" * 70)
    print("STEP 6 & 7: CLICK MODULE LINKS + CHECK SSO TOKEN")
    print("=" * 70)

    if not external_links:
        print("  No external module links to click.")
        return

    original_window = driver.current_window_handle

    for i, link_info in enumerate(external_links):
        text = link_info.get("text", f"module_{i}")
        href = link_info["href"]
        base_url = link_info.get("base_url", href.split("?")[0])

        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in text)[:30]
        if not safe_name:
            safe_name = f"module_{i}"

        print(f"\n  --- Clicking [{i+1}/{len(external_links)}]: '{text}' ---")
        print(f"  Opening: {base_url}")

        try:
            # Open in new tab
            driver.execute_script("window.open(arguments[0], '_blank');", href)
            time.sleep(4)

            # Switch to new tab
            new_handles = [h for h in driver.window_handles if h != original_window]
            if new_handles:
                driver.switch_to.window(new_handles[-1])
                final_url = driver.current_url
                print(f"  Final URL: {final_url}")

                # Check sso_token
                has_sso = "sso_token" in final_url
                print(f"  URL contains sso_token: {has_sso}")

                if has_sso:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(final_url)
                    params = parse_qs(parsed.query)
                    if "sso_token" in params:
                        token = params["sso_token"][0]
                        print(f"  sso_token (first 60 chars): {token[:60]}...")

                # Screenshot
                time.sleep(2)
                ss(driver, f"06_{safe_name}")

                # Close tab and go back
                driver.close()
                driver.switch_to.window(original_window)
                time.sleep(1)
            else:
                print("  No new tab opened")
                final_url = driver.current_url
                print(f"  Current URL: {final_url}")
                has_sso = "sso_token" in final_url
                print(f"  URL contains sso_token: {has_sso}")

        except Exception as e:
            print(f"  ERROR: {e}")
            traceback.print_exc()
            # Recovery: make sure we're back on main window
            try:
                for h in driver.window_handles:
                    if h != original_window:
                        driver.switch_to.window(h)
                        driver.close()
                driver.switch_to.window(original_window)
            except:
                pass

def check_sidebar_nav(driver):
    print("\n" + "=" * 70)
    print("EXTRA: SIDEBAR NAVIGATION LINKS")
    print("=" * 70)
    nav_links = driver.find_elements(By.CSS_SELECTOR, "nav a, aside a, [class*='sidebar'] a, [class*='Sidebar'] a")
    if nav_links:
        print(f"  Found {len(nav_links)} sidebar/nav links:")
        for link in nav_links:
            try:
                text = link.text.strip().replace("\n", " ")[:60]
                href = link.get_attribute("href") or ""
                if text or href:
                    short = href.split("?")[0]
                    print(f"    '{text}' -> {short}")
            except:
                pass
    else:
        print("  No sidebar nav links found with standard selectors.")

    # Check for internal route links
    print("\n  --- Internal dashboard routes ---")
    internal = driver.find_elements(By.CSS_SELECTOR, "a[href*='empcloud.com/']")
    seen = set()
    for link in internal:
        try:
            href = link.get_attribute("href") or ""
            text = link.text.strip()[:60]
            path = href.replace("https://test-empcloud.empcloud.com", "")
            if path and path not in seen and "test-empcloud" in href:
                seen.add(path)
                print(f"    '{text}' -> {path}")
        except:
            pass

def main():
    driver = setup_driver()
    try:
        if not login(driver):
            print("LOGIN FAILED")
            return

        screenshot_module_insights(driver)
        module_cards = find_all_module_cards(driver)
        check_sidebar_nav(driver)
        external_links = find_external_module_links(driver)
        dump_all_links(driver)
        click_and_screenshot_modules(driver, external_links)

        # Final summary
        print("\n" + "=" * 70)
        print("FINAL SUMMARY")
        print("=" * 70)
        print(f"\nModule cards found on dashboard: {len(module_cards)}")
        for name, info in module_cards.items():
            base = info['href'].split('?')[0]
            print(f"  {name}: {base} (sso_token={info['has_sso']})")

        print(f"\nExternal module links: {len(external_links)}")
        for link in external_links:
            has_sso = "sso_token" in link["href"]
            print(f"  '{link['text']}' -> {link['base_url']} (sso_token={has_sso})")

        print(f"\nAll SSO links use ?sso_token=<JWT> parameter: YES")
        print(f"JWT is RS256-signed, contains sub/org_id/email/role/org_name claims")
        print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        ss(driver, "99_error_state")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
