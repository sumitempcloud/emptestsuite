import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
print("Driver OK")

print("Loading login page...")
d.get("https://test-empcloud.empcloud.com/login")
time.sleep(5)
print(f"URL: {d.current_url}")

d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt2_login.png")

# List all buttons
btns = d.find_elements(By.CSS_SELECTOR, "button")
print(f"Found {len(btns)} buttons:")
for i, b in enumerate(btns):
    print(f"  [{i}] text='{b.text}' type={b.get_attribute('type')} class={b.get_attribute('class')}")

# List all inputs
inputs = d.find_elements(By.CSS_SELECTOR, "input")
print(f"\nFound {len(inputs)} inputs:")
for i, inp in enumerate(inputs):
    print(f"  [{i}] type={inp.get_attribute('type')} name={inp.get_attribute('name')} placeholder={inp.get_attribute('placeholder')}")

# Fill in email and password
email_f = d.find_elements(By.CSS_SELECTOR, "input[type='email'], input[name='email']")
if email_f:
    email_f[0].clear()
    email_f[0].send_keys("priya@technova.in")
    print("Email filled")

pw_f = d.find_elements(By.CSS_SELECTOR, "input[type='password']")
if pw_f:
    pw_f[0].clear()
    pw_f[0].send_keys("Welcome@123")
    print("Password filled")
    # Submit via ENTER key instead of button click
    pw_f[0].send_keys(Keys.RETURN)
    print("Submitted via ENTER")

time.sleep(6)
print(f"After login URL: {d.current_url}")

d.save_screenshot(r"C:\Users\Admin\screenshots\retest_final\qt2_after_login.png")

body = d.find_element(By.TAG_NAME, "body").text[:300]
print(f"Body: {body}")

d.quit()
print("DONE")
