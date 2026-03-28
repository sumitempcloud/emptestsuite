import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_scroll"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
LOGIN_URL = "https://test-empcloud.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

def make_driver(width=1920, height=2000):
    opts = webdriver.ChromeOptions()
    opts.binary_location = CHROME_PATH
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument(f"--window-size={width},{height}")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--force-device-scale-factor=1")
    return webdriver.Chrome(options=opts)

def login(driver):
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 15)

    # Email
    email_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[id='email'], input[placeholder*='mail']")))
    email_field.clear()
    email_field.send_keys(EMAIL)

    # Try to find and click Next/Continue or go straight to password
    try:
        next_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Next') or contains(text(),'Continue') or contains(text(),'Proceed')]")
        next_btn.click()
        time.sleep(2)
    except:
        pass

    # Password
    pw_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='password']")))
    pw_field.clear()
    pw_field.send_keys(PASSWORD)

    # Submit
    try:
        login_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Sign') or contains(text(),'Log') or contains(text(),'Submit') or @type='submit']")
        login_btn.click()
    except:
        pw_field.send_keys("\n")

    print("Waiting 5s for dashboard to fully load...")
    time.sleep(5)
    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "01_after_login.png"))
    print(f"Current URL: {driver.current_url}")
    print(f"Page title: {driver.title}")

def scroll_and_capture(driver):
    page_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    print(f"\nPage height: {page_height}px, Viewport height: {viewport_height}px")

    scroll_pos = 0
    step = 800
    idx = 2

    while scroll_pos < page_height:
        driver.execute_script(f"window.scrollTo(0, {scroll_pos})")
        time.sleep(1)

        fname = f"{idx:02d}_scroll_{scroll_pos}px.png"
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, fname))
        print(f"\nScreenshot: {fname} (scroll={scroll_pos}px)")

        # Find visible links and buttons
        elements = driver.find_elements(By.CSS_SELECTOR, "a, button, [role='button']")
        interesting = []
        for el in elements:
            try:
                txt = el.text.strip()
                href = el.get_attribute("href") or ""
                if txt and any(kw in txt.lower() for kw in ["launch", "open module", "go to", "your modules", "view details", "module", "insight", "explore", "visit", "access"]):
                    tag = el.tag_name
                    interesting.append(f"  [{tag}] '{txt}' href={href}")
            except:
                pass

        if interesting:
            print(f"  Interesting elements found:")
            for item in interesting:
                print(item)
        else:
            print("  No matching keywords in visible elements at this scroll position.")

        scroll_pos += step
        idx += 1

        # Re-check page height (dynamic content may have loaded)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height > page_height:
            print(f"  Page grew from {page_height} to {new_height}px")
            page_height = new_height

def print_full_page_text(driver):
    driver.execute_script("window.scrollTo(0, 0)")
    time.sleep(0.5)
    body_text = driver.find_element(By.TAG_NAME, "body").text
    print("\n" + "="*80)
    print("FULL PAGE TEXT CONTENT")
    print("="*80)
    print(body_text)
    print("="*80)

def capture_tall_viewport():
    """Re-login with a very tall viewport to capture the entire page in one shot."""
    print("\n\n>>> PHASE 2: Very tall viewport (1920x5000) <<<")
    driver2 = make_driver(1920, 5000)
    try:
        login(driver2)
        time.sleep(3)

        page_height = driver2.execute_script("return document.body.scrollHeight")
        print(f"Page height with tall viewport: {page_height}px")

        driver2.save_screenshot(os.path.join(SCREENSHOT_DIR, "full_page_tall_viewport.png"))
        print("Saved: full_page_tall_viewport.png")

        # Also try setting viewport to exact page height
        if page_height > 5000:
            driver2.set_window_size(1920, page_height + 100)
            time.sleep(1)
            driver2.save_screenshot(os.path.join(SCREENSHOT_DIR, "full_page_exact_height.png"))
            print(f"Saved: full_page_exact_height.png (height={page_height+100})")

        # Collect ALL links/buttons on the page
        print("\n--- ALL links and buttons on page ---")
        elements = driver2.find_elements(By.CSS_SELECTOR, "a, button, [role='button']")
        for el in elements:
            try:
                txt = el.text.strip()
                href = el.get_attribute("href") or ""
                if txt:
                    print(f"  [{el.tag_name}] '{txt}' href={href}")
            except:
                pass

    finally:
        driver2.quit()

def main():
    print(">>> PHASE 1: Scrolling capture (1920x2000) <<<")
    driver = make_driver(1920, 2000)
    try:
        login(driver)
        scroll_and_capture(driver)
        print_full_page_text(driver)
    finally:
        driver.quit()

    capture_tall_viewport()
    print("\n\nDone! All screenshots saved to:", SCREENSHOT_DIR)

if __name__ == "__main__":
    main()
