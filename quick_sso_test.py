import sys, os, time, json, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Login via API to get token
data = json.dumps({'email':'ananya@technova.in','password':'Welcome@123'}).encode()
req = urllib.request.Request('https://test-empcloud-api.empcloud.com/api/v1/auth/login',
    data=data, headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0',
    'Origin':'https://test-empcloud.empcloud.com','Accept':'application/json'})
resp = json.loads(urllib.request.urlopen(req).read())
token = resp['data']['tokens']['access_token']
print(f'Got token: {token[:50]}...')

# Module URLs
modules = {
    'Payroll': 'https://testpayroll.empcloud.com',
    'Recruit': 'https://test-recruit.empcloud.com',
    'Performance': 'https://test-performance.empcloud.com',
    'Rewards': 'https://test-rewards.empcloud.com',
    'Exit': 'https://test-exit.empcloud.com',
    'LMS': 'https://testlms.empcloud.com',
}

os.makedirs('C:/Users/Admin/screenshots/sso_quick_test', exist_ok=True)

for name, url in modules.items():
    print(f'\n=== {name} ===')
    try:
        opts = Options()
        opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--window-size=1920,1080')
        opts.binary_location = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

        sso_url = f'{url}?sso_token={token}'
        print(f'  Navigating to: {sso_url[:80]}...')
        driver.get(sso_url)
        time.sleep(5)

        final_url = driver.current_url
        title = driver.title
        body_text = driver.find_element('tag name', 'body').text[:200]

        print(f'  Final URL: {final_url}')
        print(f'  Title: {title}')
        print(f'  Body: {body_text[:100]}')

        # Check if authenticated
        if '/login' in final_url:
            print(f'  STATUS: FAIL - Redirected to login (SSO failed)')
        elif 'error' in body_text.lower() or 'unauthorized' in body_text.lower():
            print(f'  STATUS: FAIL - Error on page')
        else:
            print(f'  STATUS: PASS - Page loaded, authenticated')

        driver.save_screenshot(f'C:/Users/Admin/screenshots/sso_quick_test/{name}_dashboard.png')

        # Try a sub-page
        if name == 'Payroll':
            driver.get(f'{url}/my')
            time.sleep(3)
            print(f'  /my: {driver.title} | URL: {driver.current_url}')
            driver.save_screenshot(f'C:/Users/Admin/screenshots/sso_quick_test/{name}_my.png')
        elif name == 'Recruit':
            driver.get(f'{url}/jobs')
            time.sleep(3)
            print(f'  /jobs: {driver.title} | URL: {driver.current_url}')
            driver.save_screenshot(f'C:/Users/Admin/screenshots/sso_quick_test/{name}_jobs.png')
        elif name == 'Performance':
            driver.get(f'{url}/dashboard')
            time.sleep(3)
            print(f'  /dashboard: {driver.title} | URL: {driver.current_url}')
            driver.save_screenshot(f'C:/Users/Admin/screenshots/sso_quick_test/{name}_dashboard2.png')

        driver.quit()
    except Exception as e:
        print(f'  ERROR: {e}')
        try: driver.quit()
        except: pass

print('\n=== DONE ===')
