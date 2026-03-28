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

print("Creating driver...")
svc = Service(ChromeDriverManager().install())
d = webdriver.Chrome(service=svc, options=opts)
d.set_page_load_timeout(30)
print(f"Driver OK. Session: {d.session_id}")

print("Loading login page...")
d.get("https://test-empcloud.empcloud.com/login")
time.sleep(5)
print(f"URL: {d.current_url}")
print(f"Title: {d.title}")

# Try login
email_f = d.find_elements(By.CSS_SELECTOR, "input[type='email'], input[name='email']")
print(f"Email fields: {len(email_f)}")
if email_f:
    email_f[0].send_keys("priya@technova.in")
    pw_f = d.find_elements(By.CSS_SELECTOR, "input[type='password']")
    print(f"PW fields: {len(pw_f)}")
    if pw_f:
        pw_f[0].send_keys("Welcome@123")
        btns = d.find_elements(By.CSS_SELECTOR, "button[type='submit'], button")
        for b in btns:
            if b.text.strip():
                print(f"Clicking button: {b.text}")
                b.click()
                break
        time.sleep(5)
        print(f"After login URL: {d.current_url}")
        body = d.find_element(By.TAG_NAME, "body").text[:200]
        print(f"Body: {body}")

d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\quicktest.png")
d.quit()
print("DONE")
