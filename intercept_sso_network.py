"""
Intercept ALL network requests when clicking a module card on EmpCloud dashboard.
Uses Chrome DevTools Protocol via Selenium performance logging.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--window-size=1920,1080')
opts.add_argument('--disable-gpu')
opts.add_argument('--disable-dev-shm-usage')
opts.binary_location = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'

# Enable performance logging to capture ALL network via CDP
opts.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(options=opts)
wait = WebDriverWait(driver, 20)

try:
    # === LOGIN ===
    print("=" * 80)
    print("STEP 1: Logging in...")
    print("=" * 80)
    driver.get('https://test-empcloud.empcloud.com/login')
    time.sleep(3)

    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"], input[name="email"], input[placeholder*="mail"]')))
    email_field.clear()
    email_field.send_keys('ananya@technova.in')

    pass_field = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
    pass_field.clear()
    pass_field.send_keys('Welcome@123')

    # Click login button
    login_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    login_btn.click()
    time.sleep(5)

    print(f"After login URL: {driver.current_url}")
    print(f"Title: {driver.title}")

    # === DASHBOARD ===
    print("\n" + "=" * 80)
    print("STEP 2: On dashboard, looking for module cards...")
    print("=" * 80)

    # Wait for dashboard to load
    time.sleep(3)

    # Find all clickable module cards / links
    # Try multiple selectors for module cards
    selectors_to_try = [
        'a[href*="module"]',
        'a[href*="recruit"]',
        'a[href*="payroll"]',
        'a[href*="performance"]',
        'a[href*="launch"]',
        'a[href*="sso"]',
        '[class*="module"]',
        '[class*="card"]',
        '[class*="Module"]',
        '[class*="Card"]',
        'div[role="button"]',
        '.dashboard-card',
        '.module-card',
    ]

    print("\nSearching for module elements...")
    for sel in selectors_to_try:
        elems = driver.find_elements(By.CSS_SELECTOR, sel)
        if elems:
            print(f"  {sel}: {len(elems)} elements found")
            for i, e in enumerate(elems[:5]):
                txt = e.text.strip()[:100] if e.text else "(no text)"
                href = e.get_attribute('href') or "(no href)"
                print(f"    [{i}] text='{txt}' href={href}")

    # Also look for any links on the page
    all_links = driver.find_elements(By.TAG_NAME, 'a')
    print(f"\nAll <a> links on page: {len(all_links)}")
    for link in all_links:
        href = link.get_attribute('href') or ''
        txt = link.text.strip()[:80] if link.text else ''
        if any(kw in href.lower() + txt.lower() for kw in ['module', 'recruit', 'payroll', 'perform', 'leave', 'attend', 'launch', 'sso', 'insight']):
            print(f"  MATCH: text='{txt}' href={href}")

    # Look for module cards by text content
    print("\nSearching by text content for module names...")
    module_keywords = ['Recruitment', 'Payroll', 'Performance', 'Leave', 'Attendance', 'Core HR', 'LMS']
    target_element = None
    target_name = None

    for kw in module_keywords:
        try:
            elems = driver.find_elements(By.XPATH, f"//*[contains(text(), '{kw}')]")
            for e in elems:
                if e.is_displayed() and e.size['height'] > 0:
                    tag = e.tag_name
                    parent_href = ''
                    try:
                        parent = e.find_element(By.XPATH, './ancestor::a')
                        parent_href = parent.get_attribute('href') or ''
                    except:
                        pass
                    print(f"  Found '{kw}': tag={tag}, displayed={e.is_displayed()}, size={e.size}, parent_href={parent_href}")
                    if target_element is None:
                        target_element = e
                        target_name = kw
        except:
            pass

    # === CLEAR LOGS AND CLICK ===
    print("\n" + "=" * 80)
    print("STEP 3: Clearing performance logs, then clicking a module...")
    print("=" * 80)

    # Drain existing logs
    driver.get_log('performance')
    time.sleep(1)

    # Try clicking a module - try multiple approaches
    clicked = False

    # Approach 1: Try clicking by text
    for kw in ['Recruitment', 'Payroll', 'Performance', 'Leave', 'Attendance']:
        try:
            # Try finding a clickable ancestor
            elems = driver.find_elements(By.XPATH, f"//*[contains(text(), '{kw}')]")
            for e in elems:
                if e.is_displayed() and e.size['height'] > 10:
                    print(f"\nClicking element with text '{kw}' (tag={e.tag_name})...")
                    # Try clicking the element or its parent
                    try:
                        # First try to find a parent <a> or clickable container
                        parent_a = e.find_element(By.XPATH, './ancestor::a')
                        print(f"  Found parent <a> with href={parent_a.get_attribute('href')}")
                        driver.execute_script("arguments[0].click();", parent_a)
                        clicked = True
                        target_name = kw
                        break
                    except:
                        # Click the element itself
                        driver.execute_script("arguments[0].click();", e)
                        clicked = True
                        target_name = kw
                        break
            if clicked:
                break
        except Exception as ex:
            print(f"  Error with '{kw}': {ex}")

    # Approach 2: If no text match, try any card-like element
    if not clicked:
        print("\nTrying card-like elements...")
        for sel in ['[class*="card"]', '[class*="Card"]', '[class*="module"]', '[class*="Module"]']:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in elems:
                if e.is_displayed() and e.size['height'] > 50 and e.size['width'] > 50:
                    txt = e.text.strip()[:60]
                    print(f"  Clicking card: '{txt}' (tag={e.tag_name})")
                    driver.execute_script("arguments[0].click();", e)
                    clicked = True
                    target_name = txt
                    break
            if clicked:
                break

    if not clicked:
        print("\nWARNING: Could not find a module card to click. Dumping page source snippet...")
        src = driver.page_source
        # Look for interesting patterns
        for pattern in ['module', 'card', 'recruit', 'payroll', 'sso', 'launch', 'insight']:
            idx = src.lower().find(pattern)
            if idx >= 0:
                snippet = src[max(0, idx-100):idx+200]
                print(f"\n  Pattern '{pattern}' found at index {idx}:")
                print(f"  ...{snippet}...")

    # Wait for network activity after click
    print(f"\nWaiting for network activity after clicking '{target_name}'...")
    time.sleep(8)

    print(f"Current URL after click: {driver.current_url}")

    # === CAPTURE NETWORK LOGS ===
    print("\n" + "=" * 80)
    print("STEP 4: Capturing ALL network requests...")
    print("=" * 80)

    logs = driver.get_log('performance')
    print(f"Total performance log entries: {len(logs)}")

    # Parse all network requests
    all_requests = []
    all_responses = []

    for log_entry in logs:
        try:
            msg = json.loads(log_entry['message'])['message']
            method = msg.get('method', '')

            if method == 'Network.requestWillBeSent':
                params = msg['params']
                req = params['request']
                url = req['url']
                http_method = req['method']
                headers = req.get('headers', {})
                post_data = req.get('postData', '')
                req_type = params.get('type', '')

                all_requests.append({
                    'url': url,
                    'method': http_method,
                    'type': req_type,
                    'headers': headers,
                    'postData': post_data,
                    'requestId': params.get('requestId', ''),
                })

            elif method == 'Network.responseReceived':
                params = msg['params']
                resp = params.get('response', {})
                all_responses.append({
                    'url': resp.get('url', ''),
                    'status': resp.get('status', ''),
                    'requestId': params.get('requestId', ''),
                    'headers': resp.get('headers', {}),
                })

        except Exception:
            pass

    # Print ALL requests (not just filtered)
    print(f"\n--- ALL {len(all_requests)} Network Requests ---")
    for i, req in enumerate(all_requests):
        url = req['url']
        # Skip chrome-internal and data URLs
        if url.startswith('data:') or url.startswith('chrome'):
            continue
        print(f"\n[{i}] {req['method']} {url}")
        print(f"     Type: {req['type']}")
        if req['postData']:
            print(f"     Body: {req['postData'][:500]}")
        # Print auth headers if present
        for hdr_key in ['Authorization', 'authorization', 'X-Auth-Token', 'x-auth-token', 'Cookie', 'cookie']:
            if hdr_key in req['headers']:
                val = req['headers'][hdr_key]
                # Truncate long values
                if len(val) > 150:
                    val = val[:150] + '...'
                print(f"     {hdr_key}: {val}")

    # Highlight SSO/module-related requests
    keywords = ['sso', 'token', 'launch', 'module', 'recruit', 'payroll', 'performance',
                'leave', 'attend', 'auth', 'session', 'redirect', 'saml', 'oauth',
                'callback', 'login', 'jwt', 'insight']

    print("\n" + "=" * 80)
    print("STEP 5: SSO/Module-related requests (filtered)")
    print("=" * 80)

    matched = 0
    for req in all_requests:
        url = req['url']
        if url.startswith('data:') or url.startswith('chrome'):
            continue
        if any(kw in url.lower() for kw in keywords):
            matched += 1
            print(f"\n*** {req['method']} {url}")
            print(f"    Type: {req['type']}")
            if req['postData']:
                print(f"    Body: {req['postData'][:1000]}")
            # Check response
            for resp in all_responses:
                if resp['requestId'] == req['requestId']:
                    print(f"    Response Status: {resp['status']}")
                    # Check for Location header (redirect)
                    loc = resp['headers'].get('location', resp['headers'].get('Location', ''))
                    if loc:
                        print(f"    Redirect Location: {loc}")
                    break
            # Print all headers for SSO requests
            print(f"    Request Headers:")
            for k, v in req['headers'].items():
                if len(v) > 200:
                    v = v[:200] + '...'
                print(f"      {k}: {v}")

    if matched == 0:
        print("\nNo SSO/module-related requests found in filtered set.")

    # Also check for any redirects / navigations
    print("\n" + "=" * 80)
    print("STEP 6: All response redirects (3xx)")
    print("=" * 80)
    for resp in all_responses:
        if 300 <= (resp.get('status') or 0) < 400:
            print(f"  {resp['status']} {resp['url']}")
            loc = resp['headers'].get('location', resp['headers'].get('Location', ''))
            if loc:
                print(f"    -> {loc}")

    # Check if URL changed (indicating navigation)
    print(f"\nFinal URL: {driver.current_url}")

    # Check for new windows/tabs
    handles = driver.window_handles
    print(f"Window handles: {len(handles)}")
    if len(handles) > 1:
        print("Multiple tabs detected! Switching to each...")
        for idx, handle in enumerate(handles):
            driver.switch_to.window(handle)
            print(f"  Tab {idx}: {driver.current_url}")
            # Capture logs from this tab too
            try:
                extra_logs = driver.get_log('performance')
                for log_entry in extra_logs:
                    try:
                        msg = json.loads(log_entry['message'])['message']
                        if msg['method'] == 'Network.requestWillBeSent':
                            url = msg['params']['request']['url']
                            if not url.startswith('data:') and not url.startswith('chrome'):
                                http_m = msg['params']['request']['method']
                                print(f"    {http_m} {url}")
                    except:
                        pass
            except:
                pass

    # Save full request log to file for analysis
    output_file = r'C:\emptesting\sso_network_capture.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'all_requests': all_requests,
            'all_responses': all_responses,
            'final_url': driver.current_url,
            'window_count': len(handles),
        }, f, indent=2, default=str)
    print(f"\nFull capture saved to {output_file}")

finally:
    driver.quit()
    print("\nDone.")
