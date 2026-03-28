import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

opts = Options()
opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")
opts.add_argument("--disable-gpu")

svc = Service(ChromeDriverManager().install())
d = webdriver.Chrome(service=svc, options=opts)
d.set_page_load_timeout(60)
d.implicitly_wait(5)

try:
    d.get("https://test-empcloud.empcloud.com/login")
    time.sleep(4)

    # Use React-friendly input method
    email_el = d.find_element(By.CSS_SELECTOR, "input[name='email']")
    pw_el = d.find_element(By.CSS_SELECTOR, "input[name='password']")

    # Method 1: Use JS to set value and trigger React onChange
    d.execute_script("""
        var emailEl = arguments[0];
        var pwEl = arguments[1];
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(emailEl, 'priya@technova.in');
        emailEl.dispatchEvent(new Event('input', { bubbles: true }));
        emailEl.dispatchEvent(new Event('change', { bubbles: true }));
        nativeInputValueSetter.call(pwEl, 'Welcome@123');
        pwEl.dispatchEvent(new Event('input', { bubbles: true }));
        pwEl.dispatchEvent(new Event('change', { bubbles: true }));
    """, email_el, pw_el)

    time.sleep(1)
    d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt5_filled.png")

    # Click Sign in
    btn = d.find_element(By.XPATH, "//button[contains(text(),'Sign in')]")
    btn.click()
    print("Clicked Sign in")

    time.sleep(8)
    print(f"URL: {d.current_url}")
    d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt5_after.png")

    body = d.find_element(By.TAG_NAME, "body").text[:500]
    print(f"Body: {body}")

    # If still on login, try method 2: clear and type character by character
    if "login" in d.current_url:
        print("\nMethod 1 failed. Trying Method 2: character-by-character...")
        email_el = d.find_element(By.CSS_SELECTOR, "input[name='email']")
        pw_el = d.find_element(By.CSS_SELECTOR, "input[name='password']")

        # Triple-click to select all, then type
        email_el.click()
        email_el.send_keys(Keys.CONTROL + "a")
        email_el.send_keys(Keys.DELETE)
        time.sleep(0.5)
        for ch in "priya@technova.in":
            email_el.send_keys(ch)
            time.sleep(0.05)

        pw_el.click()
        pw_el.send_keys(Keys.CONTROL + "a")
        pw_el.send_keys(Keys.DELETE)
        time.sleep(0.5)
        for ch in "Welcome@123":
            pw_el.send_keys(ch)
            time.sleep(0.05)

        time.sleep(1)
        d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt5_method2_filled.png")

        # Check what's in the fields
        print(f"Email value: {email_el.get_attribute('value')}")
        print(f"PW value: {pw_el.get_attribute('value')}")

        btn = d.find_element(By.XPATH, "//button[contains(text(),'Sign in')]")
        btn.click()
        print("Clicked Sign in again")

        time.sleep(8)
        print(f"URL after method 2: {d.current_url}")
        d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt5_method2_after.png")
        body = d.find_element(By.TAG_NAME, "body").text[:500]
        print(f"Body: {body}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

try: d.quit()
except: pass
print("DONE")
