"""
Visual exploration of EmpCloud /modules page to find SSO launch buttons.
Takes multiple screenshots at various stages and dumps element info.
"""
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

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_exploration"
BASE_URL = "https://test-empcloud.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def save_screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"[SCREENSHOT] {name}.png saved ({os.path.getsize(path)} bytes)")
    return path

def setup_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    return driver

def login(driver):
    print("\n=== STEP 1: LOGIN ===")
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    save_screenshot(driver, "01_login_page")

    # Find and fill email
    try:
        email_field = driver.find_element(By.CSS_SELECTOR, 'input[type="email"], input[name="email"], input[placeholder*="mail"]')
        email_field.clear()
        email_field.send_keys(EMAIL)
    except Exception as e:
        print(f"Email field attempt 1 failed: {e}")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            print(f"  input: type={inp.get_attribute('type')} name={inp.get_attribute('name')} placeholder={inp.get_attribute('placeholder')}")
        if inputs:
            inputs[0].clear()
            inputs[0].send_keys(EMAIL)

    # Find and fill password
    try:
        pw_field = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
        pw_field.clear()
        pw_field.send_keys(PASSWORD)
    except Exception as e:
        print(f"Password field: {e}")

    save_screenshot(driver, "02_login_filled")

    # Click login button
    try:
        btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        btn.click()
    except:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "login" in b.text.lower() or "sign" in b.text.lower():
                b.click()
                break

    time.sleep(5)
    save_screenshot(driver, "03_after_login")
    print(f"Current URL after login: {driver.current_url}")

def explore_dashboard(driver):
    print("\n=== STEP 2: DASHBOARD EXPLORATION ===")
    save_screenshot(driver, "04_dashboard_full")

    # Look for module-related elements on dashboard
    print("\n--- Dashboard links and buttons ---")
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        href = link.get_attribute("href") or ""
        text = link.text.strip()[:80]
        if text or "module" in href.lower():
            print(f"  a | text: '{text}' | href: {href}")

    # Look for Module Insights section
    print("\n--- Looking for 'Module Insights' section ---")
    try:
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Module') or contains(text(), 'module')]")
        for el in elements:
            print(f"  {el.tag_name} | text: '{el.text[:80]}' | class: {el.get_attribute('class')[:60] if el.get_attribute('class') else 'none'}")
    except Exception as e:
        print(f"  Error: {e}")

    # Scroll down on dashboard
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2)")
    time.sleep(1)
    save_screenshot(driver, "05_dashboard_scrolled_mid")

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    save_screenshot(driver, "06_dashboard_scrolled_bottom")

def explore_modules_page(driver):
    print("\n=== STEP 3: /modules PAGE ===")
    driver.get(f"{BASE_URL}/modules")
    time.sleep(4)
    save_screenshot(driver, "07_modules_page_top")
    print(f"Current URL: {driver.current_url}")
    print(f"Page title: {driver.title}")

    # Get page height
    page_height = driver.execute_script("return document.body.scrollHeight")
    print(f"Page height: {page_height}px")

    # Scroll and screenshot in sections
    driver.execute_script("window.scrollTo(0, 400)")
    time.sleep(1)
    save_screenshot(driver, "08_modules_scroll_400")

    driver.execute_script("window.scrollTo(0, 800)")
    time.sleep(1)
    save_screenshot(driver, "09_modules_scroll_800")

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    save_screenshot(driver, "10_modules_scroll_bottom")

    # Back to top for element analysis
    driver.execute_script("window.scrollTo(0, 0)")
    time.sleep(1)

    print("\n--- ALL links on /modules page ---")
    links = driver.find_elements(By.TAG_NAME, "a")
    for i, link in enumerate(links):
        href = link.get_attribute("href") or ""
        text = link.text.strip()[:80]
        cls = (link.get_attribute("class") or "")[:60]
        if text or href:
            print(f"  [{i}] a | text: '{text}' | href: {href} | class: {cls}")

    print("\n--- ALL buttons on /modules page ---")
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for i, btn in enumerate(buttons):
        text = btn.text.strip()[:80]
        cls = (btn.get_attribute("class") or "")[:60]
        onclick = btn.get_attribute("onclick") or ""
        print(f"  [{i}] button | text: '{text}' | class: {cls} | onclick: {onclick[:60]}")

    print("\n--- Module-related elements (class*=module, data-module, etc.) ---")
    selectors = [
        '[class*=module]', '[class*=Module]', '[data-module]',
        'a[href*=empcloud]', '[class*=card]', '[class*=Card]',
        '[class*=launch]', '[class*=Launch]', '[class*=sso]', '[class*=SSO]',
        '[class*=grid]', '[class*=Grid]',
        '[role="button"]', '[class*=tile]', '[class*=Tile]',
    ]
    seen_elements = set()
    for sel in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                el_id = id(el)
                if el_id not in seen_elements:
                    seen_elements.add(el_id)
                    text = el.text.strip()[:60].replace('\n', ' | ')
                    href = el.get_attribute("href") or ""
                    cls = (el.get_attribute("class") or "")[:80]
                    tag = el.tag_name
                    print(f"  [{sel}] {tag} | text: '{text}' | href: {href} | class: {cls}")
        except:
            pass

    # Look for specific keywords in buttons/links
    print("\n--- Elements with launch/open/view/go keywords ---")
    keywords = ['launch', 'open', 'view', 'go to', 'start', 'access', 'enter', 'visit']
    all_clickable = driver.find_elements(By.CSS_SELECTOR, "a, button, [role='button'], [onclick]")
    for el in all_clickable:
        text = el.text.strip().lower()
        for kw in keywords:
            if kw in text:
                print(f"  FOUND: {el.tag_name} | text: '{el.text.strip()[:80]}' | href: {el.get_attribute('href')} | class: {(el.get_attribute('class') or '')[:60]}")
                break

def dump_module_html(driver):
    print("\n=== STEP 4: HTML DUMP OF MODULE AREAS ===")

    # Get outer HTML of main content area
    try:
        main = driver.find_element(By.CSS_SELECTOR, "main, [role='main'], #root > div > div, .content, .main-content")
        html = main.get_attribute("outerHTML")
        html_path = os.path.join(SCREENSHOT_DIR, "modules_main_content.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Main content HTML saved to {html_path} ({len(html)} chars)")
        # Print first 3000 chars
        print(f"\n--- First 3000 chars of main content ---")
        print(html[:3000])
    except Exception as e:
        print(f"Could not find main content: {e}")
        # Fallback: get full page HTML
        html = driver.page_source
        html_path = os.path.join(SCREENSHOT_DIR, "modules_full_page.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Full page HTML saved to {html_path} ({len(html)} chars)")
        print(f"\n--- First 3000 chars ---")
        print(html[:3000])

    # Look for module cards specifically
    print("\n--- Module card elements ---")
    card_selectors = [
        ".module-card", ".moduleCard", "[class*=ModuleCard]",
        ".card", "[class*=card]",
        ".module-item", ".module-tile",
        "div[class*=module]", "div[class*=Module]",
    ]
    for sel in card_selectors:
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                print(f"\n  Selector '{sel}' found {len(cards)} elements:")
                for i, card in enumerate(cards[:10]):
                    inner = card.get_attribute("innerHTML")[:300]
                    print(f"    Card {i}: {inner}")
        except:
            pass

def try_clicking_module(driver):
    print("\n=== STEP 5: TRY CLICKING A MODULE CARD ===")

    # Try various strategies to find clickable module elements
    clickable_candidates = []

    # Strategy 1: Cards with text
    cards = driver.find_elements(By.CSS_SELECTOR, "[class*=card], [class*=Card], [class*=module], [class*=Module]")
    for card in cards:
        text = card.text.strip()
        if text and len(text) > 3:
            clickable_candidates.append(("card/module class", card, text[:50]))

    # Strategy 2: Links with empcloud in href
    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='empcloud'], a[href*='module']")
    for link in links:
        clickable_candidates.append(("empcloud link", link, link.text.strip()[:50]))

    # Strategy 3: Any element with "Launch" or "Open" text
    try:
        launch_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'Launch') or contains(text(), 'Open') or contains(text(), 'View')]")
        for el in launch_els:
            clickable_candidates.append(("launch/open text", el, el.text.strip()[:50]))
    except:
        pass

    print(f"Found {len(clickable_candidates)} clickable candidates:")
    for label, el, text in clickable_candidates[:15]:
        print(f"  [{label}] text: '{text}' | tag: {el.tag_name}")

    # Click the first promising one
    if clickable_candidates:
        label, el, text = clickable_candidates[0]
        print(f"\nClicking: [{label}] '{text}'")
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            time.sleep(0.5)
            save_screenshot(driver, "11_before_click")
            el.click()
            time.sleep(3)
            save_screenshot(driver, "12_after_click")
            print(f"After click URL: {driver.current_url}")
        except Exception as e:
            print(f"Click failed: {e}")
            # Try JS click
            try:
                driver.execute_script("arguments[0].click();", el)
                time.sleep(3)
                save_screenshot(driver, "12_after_jsclick")
                print(f"After JS click URL: {driver.current_url}")
            except Exception as e2:
                print(f"JS click also failed: {e2}")
    else:
        print("No clickable candidates found!")

def check_alternative_urls(driver):
    print("\n=== STEP 6: CHECK ALTERNATIVE MODULE URLS ===")
    alt_urls = [
        "/dashboard",
        "/modules",
        "/admin/modules",
        "/settings/modules",
        "/app/modules",
    ]
    for url_path in alt_urls:
        full_url = f"{BASE_URL}{url_path}"
        print(f"\nTrying: {full_url}")
        try:
            driver.get(full_url)
            time.sleep(3)
            print(f"  Landed at: {driver.current_url}")
            print(f"  Title: {driver.title}")
            page_text = driver.find_element(By.TAG_NAME, "body").text[:200]
            print(f"  Body text: {page_text}")
        except Exception as e:
            print(f"  Error: {e}")

def explore_sidebar_nav(driver):
    print("\n=== STEP 7: SIDEBAR / NAVIGATION EXPLORATION ===")
    driver.get(f"{BASE_URL}/modules")
    time.sleep(3)

    # Look for sidebar nav elements
    nav_selectors = [
        "nav", "aside", "[class*=sidebar]", "[class*=Sidebar]",
        "[class*=nav]", "[class*=Nav]", "[class*=menu]", "[class*=Menu]",
        "[class*=drawer]", "[class*=Drawer]",
    ]
    for sel in nav_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            if elements:
                print(f"\n  Selector '{sel}' found {len(elements)} elements:")
                for i, el in enumerate(elements[:3]):
                    text = el.text.strip()[:200].replace('\n', ' | ')
                    print(f"    [{i}] text: '{text}'")
        except:
            pass

    # Take a full-page screenshot using JS to capture everything
    try:
        total_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, min(total_height + 200, 5000))
        time.sleep(1)
        save_screenshot(driver, "13_modules_fullpage_tall")
        driver.set_window_size(1920, 1080)
    except Exception as e:
        print(f"Full-page screenshot failed: {e}")

def main():
    driver = setup_driver()
    try:
        login(driver)
        explore_dashboard(driver)
        explore_modules_page(driver)
        dump_module_html(driver)
        try_clicking_module(driver)

        # Go back to modules after clicking
        driver.get(f"{BASE_URL}/modules")
        time.sleep(3)

        explore_sidebar_nav(driver)
        check_alternative_urls(driver)

        # Final summary screenshot
        driver.get(f"{BASE_URL}/modules")
        time.sleep(3)
        save_screenshot(driver, "14_final_modules")

        print("\n\n========== SUMMARY ==========")
        print(f"Screenshots saved to: {SCREENSHOT_DIR}")
        screenshots = [f for f in os.listdir(SCREENSHOT_DIR) if f.endswith('.png')]
        print(f"Total screenshots: {len(screenshots)}")
        for s in sorted(screenshots):
            print(f"  - {s}")

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        save_screenshot(driver, "ERROR_screenshot")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
