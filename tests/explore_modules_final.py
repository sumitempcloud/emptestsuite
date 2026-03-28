"""
Final targeted exploration: Module Insights SSO links on dashboard + full modules page.
"""
import sys, os, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
    driver.find_element(By.CSS_SELECTOR, 'input[type="email"]').send_keys("ananya@technova.in")
    driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys("Welcome@123")
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    time.sleep(5)
    print(f"Logged in. URL: {driver.current_url}", flush=True)

def main():
    driver = setup_driver()
    try:
        login(driver)

        # ===== DASHBOARD: Module Insights zoom =====
        print("\n===== DASHBOARD MODULE INSIGHTS - ZOOMED =====", flush=True)

        # Scroll to Module Insights section and screenshot just that area
        driver.execute_script("""
            let h2s = document.querySelectorAll('h2');
            for (let h of h2s) {
                if (h.textContent.includes('Module Insights')) {
                    h.scrollIntoView({block: 'start'});
                    break;
                }
            }
        """)
        time.sleep(1)
        save_screenshot(driver, "30_module_insights_zoomed")

        # Extract ALL Module Insights cards with their links
        insights_data = driver.execute_script("""
            let results = [];
            // Find the Module Insights container
            let h2s = document.querySelectorAll('h2');
            let container = null;
            for (let h of h2s) {
                if (h.textContent.includes('Module Insights')) {
                    container = h.parentElement;
                    break;
                }
            }
            if (!container) return {error: 'Module Insights not found'};

            // Get the full HTML
            let html = container.innerHTML;

            // Find all cards within
            let cards = container.querySelectorAll('[class*=rounded]');
            cards.forEach(card => {
                let title = '';
                let stats = [];
                let links = [];

                // Get card heading
                let heading = card.querySelector('h3, h4, [class*=font-semibold], [class*=font-bold]');
                if (heading) title = heading.textContent.trim();

                // Get stats/numbers
                card.querySelectorAll('[class*=text-2xl], [class*=text-3xl], [class*=font-bold]').forEach(s => {
                    stats.push(s.textContent.trim());
                });

                // Get all links
                card.querySelectorAll('a').forEach(a => {
                    links.push({
                        text: a.textContent.trim(),
                        href: a.getAttribute('href') || '',
                        class: (a.className || '').substring(0, 100)
                    });
                });

                if (title || links.length > 0) {
                    results.push({title, stats, links, text: card.textContent.trim().substring(0, 200)});
                }
            });

            return {cards: results, html: html.substring(0, 5000)};
        """)

        print(f"\nModule Insights data:", flush=True)
        if isinstance(insights_data, dict):
            if 'cards' in insights_data:
                for i, card in enumerate(insights_data['cards']):
                    print(f"\n  Card #{i}: {card.get('title', 'NO TITLE')}", flush=True)
                    print(f"    Stats: {card.get('stats', [])}", flush=True)
                    print(f"    Text: {card.get('text', '')[:150]}", flush=True)
                    for link in card.get('links', []):
                        print(f"    LINK: '{link['text']}' -> {link['href']}", flush=True)
            if 'html' in insights_data:
                # Save HTML
                with open(os.path.join(SCREENSHOT_DIR, "module_insights_html.txt"), "w", encoding="utf-8") as f:
                    f.write(insights_data['html'])
                print(f"\n  HTML saved to module_insights_html.txt", flush=True)

        # ===== MODULES PAGE: Scroll through ALL modules with tall window =====
        print("\n\n===== /MODULES FULL PAGE (tall window) =====", flush=True)
        driver.get(f"{BASE_URL}/modules")
        time.sleep(4)

        # Get full page height and resize
        page_h = driver.execute_script("return document.body.scrollHeight")
        print(f"Page height: {page_h}px", flush=True)
        driver.set_window_size(1920, max(page_h + 200, 3000))
        time.sleep(2)
        save_screenshot(driver, "31_modules_full_tall")

        # Reset window
        driver.set_window_size(1920, 1080)
        time.sleep(1)

        # ===== Check each module card for ANY hidden links/actions =====
        print("\n\n===== MODULE CARD DETAILED ANALYSIS =====", flush=True)
        module_details = driver.execute_script("""
            let modules = [];
            let cards = document.querySelectorAll('[class*="rounded-xl"][class*="border"]');
            cards.forEach(card => {
                let text = card.textContent.trim();
                let moduleNames = ['Biometric', 'Monitor', 'Exit', 'Field Force', 'Learning',
                                   'Payroll', 'Performance', 'Project', 'Recruit', 'Reward'];
                let isModule = false;
                for (let name of moduleNames) {
                    if (text.includes(name)) { isModule = true; break; }
                }
                if (!isModule) return;

                let info = {
                    fullText: text.substring(0, 200),
                    allLinks: [],
                    allButtons: [],
                    allInputs: [],
                    dataAttributes: {},
                    cursor: window.getComputedStyle(card).cursor,
                    hasClickHandler: card.onclick !== null,
                    role: card.getAttribute('role') || '',
                    tabindex: card.getAttribute('tabindex') || '',
                    ariaLabel: card.getAttribute('aria-label') || '',
                };

                // Check all anchor tags
                card.querySelectorAll('a').forEach(a => {
                    info.allLinks.push({
                        text: a.textContent.trim(),
                        href: a.getAttribute('href') || '',
                        target: a.getAttribute('target') || '',
                    });
                });

                // Check all buttons
                card.querySelectorAll('button').forEach(b => {
                    info.allButtons.push({
                        text: b.textContent.trim(),
                        type: b.getAttribute('type') || '',
                        disabled: b.disabled,
                    });
                });

                // Check data attributes on the card
                Array.from(card.attributes).forEach(attr => {
                    if (attr.name.startsWith('data-')) {
                        info.dataAttributes[attr.name] = attr.value;
                    }
                });

                // Check parent for links
                let parent = card.parentElement;
                if (parent && parent.tagName === 'A') {
                    info.parentLink = parent.getAttribute('href');
                }

                modules.push(info);
            });
            return modules;
        """)

        for i, m in enumerate(module_details):
            print(f"\n  Module #{i}: {m['fullText'][:80]}", flush=True)
            print(f"    Cursor: {m['cursor']} | Clickable: {m['hasClickHandler']} | Role: {m['role']} | TabIndex: {m['tabindex']}", flush=True)
            print(f"    Data attrs: {m['dataAttributes']}", flush=True)
            if m.get('parentLink'):
                print(f"    PARENT LINK: {m['parentLink']}", flush=True)
            if m['allLinks']:
                for link in m['allLinks']:
                    print(f"    LINK: '{link['text']}' -> {link['href']} (target={link['target']})", flush=True)
            else:
                print(f"    No links inside card", flush=True)
            if m['allButtons']:
                for btn in m['allButtons']:
                    print(f"    BUTTON: '{btn['text']}' type={btn['type']} disabled={btn['disabled']}", flush=True)

        # ===== Check the blue "EMP Cloud - Core HRMS" banner area on dashboard =====
        print("\n\n===== DASHBOARD CORE HRMS BANNER =====", flush=True)
        driver.get(BASE_URL)
        time.sleep(4)

        banner = driver.execute_script("""
            // Look for the blue banner area with module quick links
            let results = [];
            // Find elements with gradient/brand background
            let els = document.querySelectorAll('[class*=gradient], [class*=brand], [class*=blue]');
            els.forEach(el => {
                let text = el.textContent.trim();
                if (text.includes('EMP Cloud') || text.includes('Core HRMS')) {
                    // Find all clickable items inside
                    let links = el.querySelectorAll('a, button, [role="button"]');
                    let linkData = [];
                    links.forEach(l => {
                        linkData.push({
                            tag: l.tagName,
                            text: l.textContent.trim().substring(0, 60),
                            href: l.getAttribute('href') || '',
                            class: (l.className || '').substring(0, 80)
                        });
                    });
                    results.push({
                        text: text.substring(0, 300),
                        links: linkData,
                        html: el.innerHTML.substring(0, 1000)
                    });
                }
            });
            return results;
        """)

        for i, b in enumerate(banner):
            print(f"\n  Banner #{i}: {b['text'][:100]}", flush=True)
            for link in b.get('links', []):
                print(f"    {link['tag']}: '{link['text']}' -> {link['href']}", flush=True)

        # Scroll to and screenshot the banner area
        driver.execute_script("""
            let els = document.querySelectorAll('[class*=gradient]');
            for (let el of els) {
                if (el.textContent.includes('Core HRMS')) {
                    el.scrollIntoView({block: 'center'});
                    break;
                }
            }
        """)
        time.sleep(1)
        save_screenshot(driver, "32_core_hrms_banner")

        # ===== Check the icon row under the blue banner =====
        print("\n\n===== CORE HRMS ICON BAR =====", flush=True)
        icon_bar = driver.execute_script("""
            // The blue banner has small icons: Employee Directory, Attendance, Case Management, etc.
            let results = [];
            // Look for icon grid under the banner
            let flexDivs = document.querySelectorAll('[class*="flex"][class*="gap"]');
            flexDivs.forEach(div => {
                let text = div.textContent.trim();
                if (text.includes('Employee Directory') && text.includes('Attendance')) {
                    let items = div.querySelectorAll('a, button, div[class*="cursor"], [onclick]');
                    items.forEach(item => {
                        results.push({
                            tag: item.tagName,
                            text: item.textContent.trim().substring(0, 60),
                            href: item.getAttribute('href') || '',
                            cursor: window.getComputedStyle(item).cursor,
                            class: (item.className || '').substring(0, 80)
                        });
                    });
                    // Also get the direct children
                    let children = div.children;
                    for (let c of children) {
                        results.push({
                            tag: c.tagName + ' (child)',
                            text: c.textContent.trim().substring(0, 60),
                            href: c.getAttribute('href') || '',
                            cursor: window.getComputedStyle(c).cursor,
                            class: (c.className || '').substring(0, 80)
                        });
                    }
                }
            });
            return results;
        """)

        for item in icon_bar:
            print(f"  {item['tag']}: '{item['text']}' -> href={item['href']} cursor={item['cursor']}", flush=True)

        # ===== Summary of ALL external links found =====
        print("\n\n========================================", flush=True)
        print("===== SUMMARY: ALL SSO/EXTERNAL LINKS =====", flush=True)
        print("========================================", flush=True)

        all_external = driver.execute_script("""
            let links = [];
            // Check dashboard
            document.querySelectorAll('a').forEach(a => {
                let href = a.getAttribute('href') || '';
                if (href.includes('empcloud.com') && !href.includes('test-empcloud.empcloud.com')) {
                    links.push({
                        text: a.textContent.trim().substring(0, 80),
                        href: href,
                        context: (a.closest('[class*=card], [class*=rounded]') || {}).textContent?.trim().substring(0, 100) || 'no context'
                    });
                }
            });
            return links;
        """)

        # Also check /modules for external links
        driver.get(f"{BASE_URL}/modules")
        time.sleep(3)
        modules_external = driver.execute_script("""
            let links = [];
            document.querySelectorAll('a').forEach(a => {
                let href = a.getAttribute('href') || '';
                if (href.includes('empcloud.com') && !href.includes('test-empcloud.empcloud.com')) {
                    links.push({
                        text: a.textContent.trim().substring(0, 80),
                        href: href,
                        context: 'modules page'
                    });
                }
            });
            return links;
        """)

        all_links = all_external + modules_external
        print(f"\nTotal external empcloud links found: {len(all_links)}", flush=True)
        for link in all_links:
            print(f"  '{link['text']}' -> {link['href']}", flush=True)
            print(f"    Context: {link['context'][:80]}", flush=True)

        # Final screenshots list
        print("\n\n===== ALL SCREENSHOTS =====", flush=True)
        for f in sorted(os.listdir(SCREENSHOT_DIR)):
            if f.endswith('.png'):
                size = os.path.getsize(os.path.join(SCREENSHOT_DIR, f))
                print(f"  {f} ({size:,} bytes)", flush=True)

        print("\nDONE!", flush=True)

    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        save_screenshot(driver, "ERROR_final")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
