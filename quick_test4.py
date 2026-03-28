import sys, time, subprocess
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
opts.add_argument("--js-flags=--max-old-space-size=512")
opts.add_argument("--disable-features=TranslateUI")
opts.add_argument("--disable-background-networking")
opts.add_argument("--disable-default-apps")
opts.add_argument("--disable-sync")
opts.add_argument("--disable-background-timer-throttling")

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
    d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt4_login.png")

    d.find_element(By.CSS_SELECTOR, "input[name='email']").send_keys("priya@technova.in")
    d.find_element(By.CSS_SELECTOR, "input[name='password']").send_keys("Welcome@123")
    time.sleep(1)

    btn = d.find_element(By.XPATH, "//button[contains(text(),'Sign in')]")
    print(f"Clicking Sign in...")
    btn.click()

    # Wait carefully with try/except on each check
    for i in range(20):
        time.sleep(1)
        try:
            url = d.current_url
            if i % 3 == 0:
                print(f"  {i+1}s: {url}")
            if "dashboard" in url or "home" in url:
                print(f"  Logged in! URL: {url}")
                break
        except Exception as e:
            print(f"  {i+1}s: Driver error - {type(e).__name__}: {str(e)[:100]}")
            # Check if chrome is still running
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"], capture_output=True, text=True)
            if "chrome.exe" not in result.stdout:
                print("  Chrome process is DEAD")
                break
            continue

    try:
        d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt4_after.png")
        print(f"Final URL: {d.current_url}")
        body = d.find_element(By.TAG_NAME, "body").text[:500]
        print(f"Body: {body}")
    except Exception as e:
        print(f"Post-login error: {e}")

except Exception as e:
    print(f"ERROR: {e}")

try: d.quit()
except: pass
print("DONE")
