import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

opts = Options()
opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")
opts.add_argument("--disable-gpu")
opts.add_argument("--disable-software-rasterizer")
opts.add_argument("--disable-features=VizDisplayCompositor")
opts.add_argument("--single-process")
opts.add_argument("--no-zygote")

print("Creating driver...")
svc = Service(ChromeDriverManager().install())
d = webdriver.Chrome(service=svc, options=opts)
d.set_page_load_timeout(60)
print("Driver OK")

try:
    print("Loading login page...")
    d.get("https://test-empcloud.empcloud.com/login")
    time.sleep(5)
    print(f"URL: {d.current_url}")
    d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt3_login.png")

    # Fill email
    d.find_element(By.CSS_SELECTOR, "input[name='email']").send_keys("priya@technova.in")
    d.find_element(By.CSS_SELECTOR, "input[name='password']").send_keys("Welcome@123")
    time.sleep(1)
    d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt3_filled.png")

    # Click Sign in button specifically
    btn = d.find_element(By.XPATH, "//button[contains(text(),'Sign in')]")
    print(f"Found Sign in button: {btn.text}")
    btn.click()
    print("Clicked Sign in, waiting...")

    # Wait carefully
    for i in range(15):
        time.sleep(1)
        try:
            url = d.current_url
            print(f"  {i+1}s: {url}")
            if "dashboard" in url or "home" in url:
                break
        except Exception as e:
            print(f"  {i+1}s: ERROR - {e}")
            break

    d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt3_after.png")
    body = d.find_element(By.TAG_NAME, "body").text[:300]
    print(f"Body: {body}")

except Exception as e:
    print(f"ERROR: {e}")

try:
    d.quit()
except:
    pass
print("DONE")
