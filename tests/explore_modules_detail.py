"""
Detailed exploration of the /modules page - extract all module info, buttons, and SSO elements.
"""
import sys, os, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_exploration"
BASE_URL = "https://test-empcloud.empcloud.com"

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

def save_screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"[SCREENSHOT] {name}.png", flush=True)

def login(driver):
    driver.get(f"{BASE_URL}/login")
    time.sleep(3)
    email_field = driver.find_element(By.CSS_SELECTOR, 'input[type="email"], input[name="email"], input[placeholder*="mail"]')
    email_field.clear()
    email_field.send_keys("ananya@technova.in")
    pw_field = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
    pw_field.clear()
    pw_field.send_keys("Welcome@123")
    btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    btn.click()
    time.sleep(5)
    print(f"Logged in. URL: {driver.current_url}", flush=True)

def main():
    driver = setup_driver()
    try:
        login(driver)

        # Go to /modules
        driver.get(f"{BASE_URL}/modules")
        time.sleep(4)
        print(f"\nOn /modules page. URL: {driver.current_url}", flush=True)

        # Use JS to extract all module-related info
        result = driver.execute_script("""
            let data = {};

            // Get all text content from the page
            data.pageTitle = document.title;
            data.h1 = Array.from(document.querySelectorAll('h1,h2,h3')).map(e => e.textContent.trim());

            // Find all module items - look for repeated patterns
            // From the screenshot: each module is a row with name, description, status badge, and a button
            let rows = [];

            // Strategy: find all elements that contain module names
            let allText = document.body.innerText;

            // Look for badges/status indicators
            let badges = document.querySelectorAll('[class*=badge], [class*=Badge], span[class*=bg-], span[class*=text-]');
            let badgeTexts = [];
            badges.forEach(b => {
                let t = b.textContent.trim();
                if (t && t.length < 30) badgeTexts.push(t + ' | class: ' + b.className.substring(0, 80));
            });
            data.badges = badgeTexts.slice(0, 30);

            // Look for subscribe/unsubscribe buttons
            let buttons = document.querySelectorAll('button');
            let buttonData = [];
            buttons.forEach(b => {
                let text = b.textContent.trim();
                let classes = b.className || '';
                let disabled = b.disabled;
                let ariaLabel = b.getAttribute('aria-label') || '';
                if (text.length > 0 || ariaLabel) {
                    buttonData.push({
                        text: text.substring(0, 80),
                        class: classes.substring(0, 100),
                        disabled: disabled,
                        ariaLabel: ariaLabel
                    });
                }
            });
            data.buttons = buttonData;

            // Look for all links
            let links = document.querySelectorAll('a');
            let linkData = [];
            links.forEach(a => {
                let text = a.textContent.trim();
                let href = a.getAttribute('href') || '';
                if (text.length > 0 || href) {
                    linkData.push({
                        text: text.substring(0, 80),
                        href: href,
                        class: (a.className || '').substring(0, 80)
                    });
                }
            });
            data.links = linkData;

            // Find elements with "subscribed" text
            let subscribed = [];
            document.querySelectorAll('*').forEach(el => {
                if (el.children.length === 0 && el.textContent.trim().toLowerCase().includes('subscrib')) {
                    subscribed.push({tag: el.tagName, text: el.textContent.trim(), class: (el.className||'').substring(0,80)});
                }
            });
            data.subscribed = subscribed;

            // Find the main content area structure
            let mainContent = document.querySelector('main') || document.querySelector('[class*=content]');
            if (mainContent) {
                // Get direct children structure
                let children = [];
                mainContent.querySelectorAll(':scope > *').forEach(c => {
                    children.push({tag: c.tagName, class: (c.className||'').substring(0,60), text: c.textContent.trim().substring(0,100)});
                });
                data.mainChildren = children.slice(0, 20);
            }

            // Find module list items - look for list-like container
            let moduleItems = [];
            // Look for elements that seem like module cards/rows
            let potentialCards = document.querySelectorAll('[class*=border], [class*=rounded]');
            potentialCards.forEach(card => {
                let text = card.textContent.trim();
                // Only include if it looks like a module entry (has known module names)
                let moduleNames = ['Biometric', 'Monitor', 'Exit', 'Field Force', 'Learning', 'Payroll', 'Performance', 'Recruit', 'Reward', 'Project'];
                for (let name of moduleNames) {
                    if (text.includes(name) && text.length < 500) {
                        // Check if this element has a button child
                        let btn = card.querySelector('button');
                        let btnText = btn ? btn.textContent.trim() : 'NO BUTTON';
                        let btnClass = btn ? btn.className : '';
                        moduleItems.push({
                            text: text.substring(0, 200),
                            tag: card.tagName,
                            class: (card.className||'').substring(0, 100),
                            buttonText: btnText,
                            buttonClass: btnClass.substring(0, 100),
                            innerHTML: card.innerHTML.substring(0, 500)
                        });
                        break;
                    }
                }
            });
            data.moduleItems = moduleItems.slice(0, 20);

            return JSON.stringify(data, null, 2);
        """)

        parsed = json.loads(result)
        print("\n===== PAGE STRUCTURE =====", flush=True)
        print(f"Title: {parsed.get('pageTitle')}", flush=True)
        print(f"Headings: {parsed.get('h1')}", flush=True)

        print("\n===== BADGES/STATUS =====", flush=True)
        for b in parsed.get('badges', []):
            print(f"  {b}", flush=True)

        print("\n===== BUTTONS =====", flush=True)
        for b in parsed.get('buttons', []):
            print(f"  text: '{b['text']}' | class: {b['class']} | disabled: {b['disabled']}", flush=True)

        print("\n===== LINKS =====", flush=True)
        for l in parsed.get('links', []):
            print(f"  text: '{l['text'][:60]}' | href: {l['href']} | class: {l['class'][:50]}", flush=True)

        print("\n===== SUBSCRIBED ELEMENTS =====", flush=True)
        for s in parsed.get('subscribed', []):
            print(f"  {s}", flush=True)

        print("\n===== MODULE ITEMS (cards/rows) =====", flush=True)
        for i, m in enumerate(parsed.get('moduleItems', [])):
            print(f"\n  Module Item #{i}:", flush=True)
            print(f"    Text: {m['text'][:150]}", flush=True)
            print(f"    Tag/Class: {m['tag']} | {m['class'][:80]}", flush=True)
            print(f"    Button: '{m['buttonText']}' | class: {m['buttonClass'][:80]}", flush=True)
            print(f"    innerHTML: {m['innerHTML'][:300]}", flush=True)

        # Save full data
        with open(os.path.join(SCREENSHOT_DIR, "modules_data.json"), "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        print(f"\nFull data saved to modules_data.json", flush=True)

        # Now try scrolling to see if there are more modules below
        total_modules = driver.execute_script("""
            let names = ['Biometric', 'Monitor', 'Exit', 'Field Force', 'Learning', 'Payroll',
                         'Performance', 'Recruit', 'Reward', 'Project'];
            let found = [];
            let body = document.body.innerText;
            names.forEach(n => { if (body.includes(n)) found.push(n); });
            return found;
        """)
        print(f"\nModule names found on page: {total_modules}", flush=True)

        # Try to scroll down to see more
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        save_screenshot(driver, "15_modules_bottom_v2")

        # Now try to expand the window to capture FULL page
        page_h = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, min(page_h + 200, 6000))
        time.sleep(1)
        save_screenshot(driver, "16_modules_fullpage")
        driver.set_window_size(1920, 1080)

        # Check dashboard for Module Insights
        print("\n\n===== DASHBOARD MODULE INSIGHTS =====", flush=True)
        driver.get(BASE_URL)
        time.sleep(4)

        insights = driver.execute_script("""
            let result = [];
            // Look for "Module Insights" heading
            let allEls = document.querySelectorAll('*');
            let insightsSection = null;
            for (let el of allEls) {
                if (el.textContent.trim().startsWith('Module Insights') && el.tagName.match(/^H[1-6]$/)) {
                    insightsSection = el.parentElement || el.closest('section') || el.closest('div');
                    break;
                }
            }
            if (insightsSection) {
                result.push('Found Module Insights section');
                result.push('HTML: ' + insightsSection.innerHTML.substring(0, 2000));
                // Find all links within
                let links = insightsSection.querySelectorAll('a');
                links.forEach(a => {
                    result.push('Link: ' + a.textContent.trim().substring(0, 60) + ' -> ' + (a.getAttribute('href') || ''));
                });
            } else {
                result.push('Module Insights section NOT found by heading');
                // Try text search
                let bodyText = document.body.innerText;
                let idx = bodyText.indexOf('Module Insights');
                if (idx >= 0) {
                    result.push('Found text "Module Insights" at position ' + idx);
                    result.push('Context: ' + bodyText.substring(Math.max(0, idx-50), idx+200));
                } else {
                    result.push('Text "Module Insights" not found on dashboard');
                }
            }
            return result;
        """)
        for line in insights:
            print(f"  {str(line)[:300]}", flush=True)

        # Screenshot the dashboard module insights area
        driver.execute_script("window.scrollTo(0, 600)")
        time.sleep(1)
        save_screenshot(driver, "17_dashboard_module_insights")

        # Make dashboard full height
        page_h = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, min(page_h + 200, 6000))
        time.sleep(1)
        save_screenshot(driver, "18_dashboard_fullpage")
        driver.set_window_size(1920, 1080)

        # Now check what the "Subscribed" buttons do and look for SSO launch patterns
        print("\n\n===== SSO LAUNCH INVESTIGATION =====", flush=True)
        driver.get(f"{BASE_URL}/modules")
        time.sleep(4)

        # Try clicking a "Subscribed" button/badge on a module
        sso_info = driver.execute_script("""
            let results = [];
            // Find all clickable elements near module names
            let allBtns = document.querySelectorAll('button, a[role="button"]');
            allBtns.forEach(b => {
                let text = b.textContent.trim();
                if (text.includes('Subscribed') || text.includes('Subscribe') || text.includes('Launch')
                    || text.includes('Open') || text.includes('View') || text.includes('Unsubscribe')) {
                    results.push({
                        tag: b.tagName,
                        text: text.substring(0, 80),
                        class: b.className.substring(0, 100),
                        href: b.getAttribute('href') || '',
                        onclick: b.getAttribute('onclick') || '',
                        dataAttrs: Array.from(b.attributes).filter(a => a.name.startsWith('data-')).map(a => a.name + '=' + a.value).join(', '),
                        parent: b.parentElement ? b.parentElement.textContent.trim().substring(0, 100) : ''
                    });
                }
            });
            return results;
        """)
        print(f"Found {len(sso_info)} relevant buttons:", flush=True)
        for s in sso_info:
            print(f"  {json.dumps(s, indent=4)}", flush=True)

        # Check sidebar for module links
        print("\n\n===== SIDEBAR MODULE LINKS =====", flush=True)
        sidebar_links = driver.execute_script("""
            let nav = document.querySelector('nav');
            if (!nav) return [];
            let links = nav.querySelectorAll('a');
            return Array.from(links).map(a => ({
                text: a.textContent.trim().substring(0, 60),
                href: a.getAttribute('href') || '',
                class: (a.className||'').substring(0, 80),
                active: a.getAttribute('data-active')
            }));
        """)
        for l in sidebar_links:
            print(f"  {l['text']:<30} -> {l['href']:<30} active={l.get('active','')}", flush=True)

        # Try clicking on the module row itself (not just button)
        print("\n\n===== CLICKING MODULE ROW =====", flush=True)
        try:
            # Click "Exit Management & OffBoarding" row
            exit_row = driver.find_element(By.XPATH, "//*[contains(text(), 'Exit Management')]")
            parent = exit_row.find_element(By.XPATH, "./..")
            print(f"Found Exit row. Parent tag: {parent.tag_name}, class: {parent.get_attribute('class')[:60]}", flush=True)
            save_screenshot(driver, "19_before_exit_click")
            parent.click()
            time.sleep(3)
            save_screenshot(driver, "20_after_exit_click")
            print(f"After clicking Exit row, URL: {driver.current_url}", flush=True)
        except Exception as e:
            print(f"  Error clicking Exit row: {e}", flush=True)

        # Check if clicking revealed a modal or navigated
        new_url = driver.current_url
        if new_url != f"{BASE_URL}/modules":
            print(f"  NAVIGATED TO: {new_url}", flush=True)
            save_screenshot(driver, "21_navigated_page")
        else:
            # Check for modal
            modal = driver.execute_script("""
                let modals = document.querySelectorAll('[class*=modal], [class*=Modal], [role="dialog"], [class*=popup], [class*=Popup]');
                if (modals.length > 0) {
                    return Array.from(modals).map(m => ({
                        class: m.className.substring(0, 100),
                        text: m.textContent.trim().substring(0, 300),
                        visible: m.offsetParent !== null
                    }));
                }
                return [];
            """)
            print(f"  Modals found: {len(modal)}", flush=True)
            for m in modal:
                print(f"    class: {m['class']}, visible: {m['visible']}, text: {m['text'][:200]}", flush=True)

        print("\n\nDONE!", flush=True)

    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        save_screenshot(driver, "ERROR")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
