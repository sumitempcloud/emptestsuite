"""Quick debug: test login after logout to figure out the exact problem."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

BASE = "https://test-empcloud.empcloud.com"

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage","--window-size=1920,1080",
              "--disable-gpu","--ignore-certificate-errors","--log-level=3"]:
        opts.add_argument(a)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

d = get_driver()
try:
    # 1. Login as admin first
    print("=== First login as admin ===")
    d.get(f"{BASE}/login")
    time.sleep(2)
    print(f"URL: {d.current_url}")

    ef = d.find_element(By.CSS_SELECTOR, "input[name='email'],input[type='email']")
    ef.send_keys("ananya@technova.in")
    pf = d.find_element(By.CSS_SELECTOR, "input[type='password']")
    pf.send_keys("Welcome@123")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(3)
    print(f"After login: {d.current_url}")
    d.save_screenshot("C:/emptesting/screenshots/debug_1_loggedin.png")

    # 2. Now try full logout
    print("\n=== Logout approach 1: clear all + navigate ===")
    d.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    d.delete_all_cookies()
    d.get("about:blank")
    time.sleep(1)
    d.get(f"{BASE}/login")
    time.sleep(3)
    print(f"After clear+blank+login: {d.current_url}")
    d.save_screenshot("C:/emptesting/screenshots/debug_2_after_logout.png")

    # Check if on login page
    if "/login" in d.current_url:
        print("On login page! Trying to login as priya...")
        # Dump page inputs
        inputs = d.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            try:
                print(f"  input: type={inp.get_attribute('type')} name={inp.get_attribute('name')} displayed={inp.is_displayed()} value={inp.get_attribute('value')}")
            except: pass

        ef = None
        for s in ["input[name='email']","input[type='email']"]:
            try:
                e = d.find_element(By.CSS_SELECTOR, s)
                if e.is_displayed(): ef = e; break
            except: pass
        if ef:
            ef.clear()
            ef.send_keys("priya@technova.in")
            pf = d.find_element(By.CSS_SELECTOR, "input[type='password']")
            pf.clear()
            pf.send_keys("Welcome@123")
            d.save_screenshot("C:/emptesting/screenshots/debug_3_creds_entered.png")
            d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(5)
            print(f"After priya login attempt: {d.current_url}")
            d.save_screenshot("C:/emptesting/screenshots/debug_4_after_priya.png")

            # Check for error messages
            body = d.find_element(By.TAG_NAME, "body").text
            print(f"Body text (first 300): {body[:300]}")

            # Check for error toast/message
            for sel in [".error",".toast","[class*='error']","[class*='alert']","[role='alert']"]:
                try:
                    e = d.find_element(By.CSS_SELECTOR, sel)
                    if e.is_displayed():
                        print(f"  Error element ({sel}): {e.text}")
                except: pass
        else:
            print("No email field found!")
    else:
        print(f"NOT on login page: {d.current_url}")

    # 3. Try approach 2: navigate directly without clearing
    print("\n=== Approach 2: Just navigate to /login (no clear) ===")
    d.get(f"{BASE}/login")
    time.sleep(3)
    print(f"URL: {d.current_url}")

finally:
    d.quit()
    print("\nDone")
