import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_click_subscribed"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
LOGIN_URL = "https://test-empcloud.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  [Screenshot] {path}")

def setup_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    return driver

def login(driver):
    print("=== LOGGING IN ===")
    driver.get(LOGIN_URL + "/login")
    time.sleep(4)
    driver.find_element(By.TAG_NAME, "body").click()
    time.sleep(1)
    email_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
    )
    email_field.clear()
    email_field.send_keys(EMAIL)
    pw_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pw_field.clear()
    pw_field.send_keys(PASSWORD)
    for b in driver.find_elements(By.TAG_NAME, "button"):
        if b.text.strip().lower() in ["sign in", "login"]:
            b.click()
            break
    time.sleep(8)
    print(f"  Logged in. URL: {driver.current_url}")

def go_to_modules(driver):
    driver.get(LOGIN_URL + "/modules")
    time.sleep(5)

def main():
    driver = setup_driver()
    try:
        login(driver)
        go_to_modules(driver)
        screenshot(driver, "10_modules_full")

        # === STEP 1: Get raw HTML of the module cards area ===
        print("\n=== STEP 1: RAW HTML ANALYSIS ===")
        # Get the main content area
        html_snippet = driver.execute_script("""
            // Find the main content (not sidebar)
            var main = document.querySelector('main') || document.querySelector('[class*="content"]') || document.querySelector('[class*="marketplace"]');
            if (!main) {
                // Fallback: get everything after sidebar
                var all = document.querySelectorAll('div');
                for (var i = 0; i < all.length; i++) {
                    if (all[i].textContent.includes('Module Marketplace') && all[i].offsetWidth > 500) {
                        main = all[i];
                        break;
                    }
                }
            }
            return main ? main.innerHTML.substring(0, 8000) : document.body.innerHTML.substring(0, 8000);
        """)
        print(f"  Main content HTML (first 8000 chars):")
        print(html_snippet[:8000])

        # === STEP 2: Find ALL elements with text "Subscribed" ===
        print("\n\n=== STEP 2: ALL ELEMENTS WITH 'Subscribed' TEXT ===")
        subscribed_elems = driver.execute_script("""
            var results = [];
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
                var el = all[i];
                // Direct text only (not child text)
                var directText = '';
                for (var j = 0; j < el.childNodes.length; j++) {
                    if (el.childNodes[j].nodeType === 3) {
                        directText += el.childNodes[j].textContent.trim();
                    }
                }
                if (directText === 'Subscribed' || el.textContent.trim() === 'Subscribed') {
                    results.push({
                        tag: el.tagName,
                        classes: el.className,
                        id: el.id,
                        outerHTML: el.outerHTML.substring(0, 300),
                        isButton: el.tagName === 'BUTTON',
                        isLink: el.tagName === 'A',
                        href: el.href || '',
                        onclick: el.getAttribute('onclick') || '',
                        role: el.getAttribute('role') || '',
                        cursor: window.getComputedStyle(el).cursor,
                        clickable: window.getComputedStyle(el).pointerEvents !== 'none',
                        parentTag: el.parentElement ? el.parentElement.tagName : '',
                        parentClass: el.parentElement ? el.parentElement.className.substring(0, 100) : '',
                        directText: directText
                    });
                }
            }
            return results;
        """)
        print(f"  Found {len(subscribed_elems)} elements with 'Subscribed' text:")
        for i, e in enumerate(subscribed_elems):
            print(f"\n  [{i+1}]")
            for k, v in e.items():
                print(f"    {k}: {v}")

        # === STEP 3: Identify module cards and their structure ===
        print("\n\n=== STEP 3: MODULE CARD STRUCTURE ===")
        module_info = driver.execute_script("""
            var results = [];
            // Find all "Subscribed" badges
            var badges = [];
            var spans = document.querySelectorAll('span, div, p, button, a, badge');
            for (var i = 0; i < spans.length; i++) {
                var directText = '';
                for (var j = 0; j < spans[i].childNodes.length; j++) {
                    if (spans[i].childNodes[j].nodeType === 3) directText += spans[i].childNodes[j].textContent.trim();
                }
                if (directText === 'Subscribed') badges.push(spans[i]);
            }

            for (var i = 0; i < badges.length; i++) {
                var badge = badges[i];
                // Walk up to find the card container
                var card = badge;
                for (var j = 0; j < 10; j++) {
                    card = card.parentElement;
                    if (!card) break;
                    if (card.className && (card.className.includes('card') || card.className.includes('border') || card.className.includes('rounded'))) break;
                }
                if (!card) continue;

                // Get all interactive elements in this card
                var links = card.querySelectorAll('a');
                var buttons = card.querySelectorAll('button');
                var clickables = card.querySelectorAll('[onclick], [role="button"]');

                var info = {
                    cardTag: card.tagName,
                    cardClass: card.className.substring(0, 150),
                    cardText: card.textContent.trim().substring(0, 200),
                    cardOnClick: card.getAttribute('onclick') || '',
                    cardCursor: window.getComputedStyle(card).cursor,
                    links: [],
                    buttons: [],
                    clickables: []
                };

                for (var l = 0; l < links.length; l++) {
                    info.links.push({
                        text: links[l].textContent.trim().substring(0, 50),
                        href: links[l].href,
                        class: links[l].className.substring(0, 100)
                    });
                }
                for (var b = 0; b < buttons.length; b++) {
                    info.buttons.push({
                        text: buttons[b].textContent.trim().substring(0, 50),
                        class: buttons[b].className.substring(0, 100),
                        onclick: buttons[b].getAttribute('onclick') || ''
                    });
                }
                results.push(info);
            }
            return results;
        """)

        print(f"  Found {len(module_info)} module cards:")
        for i, m in enumerate(module_info):
            print(f"\n  --- Card {i+1} ---")
            print(f"  Text: {m['cardText']}")
            print(f"  Tag: {m['cardTag']}, Class: {m['cardClass']}")
            print(f"  onClick: {m['cardOnClick']}")
            print(f"  Cursor: {m['cardCursor']}")
            print(f"  Links: {m['links']}")
            print(f"  Buttons: {m['buttons']}")

        # === STEP 4: Click each "Subscribed" badge ===
        print("\n\n=== STEP 4: CLICKING 'Subscribed' BADGES ===")

        # Get count of Subscribed badges
        num_badges = driver.execute_script("""
            var count = 0;
            var all = document.querySelectorAll('span, div, p, badge');
            for (var i = 0; i < all.length; i++) {
                var directText = '';
                for (var j = 0; j < all[i].childNodes.length; j++) {
                    if (all[i].childNodes[j].nodeType === 3) directText += all[i].childNodes[j].textContent.trim();
                }
                if (directText === 'Subscribed') count++;
            }
            return count;
        """)
        print(f"  Total 'Subscribed' badges: {num_badges}")

        for idx in range(num_badges):
            go_to_modules(driver)

            # Intercept window.open and location changes
            driver.execute_script("""
                window.__captured = [];
                var orig = window.open;
                window.open = function(url) {
                    window.__captured.push('window.open:' + url);
                    return orig.apply(this, arguments);
                };
            """)

            url_before = driver.current_url
            handles_before = set(driver.window_handles)

            # Click the idx-th Subscribed badge
            click_result = driver.execute_script("""
                var badges = [];
                var all = document.querySelectorAll('span, div, p, badge');
                for (var i = 0; i < all.length; i++) {
                    var directText = '';
                    for (var j = 0; j < all[i].childNodes.length; j++) {
                        if (all[i].childNodes[j].nodeType === 3) directText += all[i].childNodes[j].textContent.trim();
                    }
                    if (directText === 'Subscribed') badges.push(all[i]);
                }
                if (arguments[0] < badges.length) {
                    var el = badges[arguments[0]];
                    // Get module name from parent card
                    var card = el;
                    for (var j = 0; j < 10; j++) {
                        card = card.parentElement;
                        if (!card) break;
                        var h = card.querySelector('h1,h2,h3,h4,h5,h6');
                        if (h) {
                            el.click();
                            return {moduleName: h.textContent.trim(), clicked: true};
                        }
                    }
                    el.click();
                    return {moduleName: 'Unknown', clicked: true};
                }
                return {moduleName: '', clicked: false};
            """, idx)

            print(f"\n  Badge {idx+1}: Module='{click_result.get('moduleName','?')}', Clicked={click_result.get('clicked')}")

            time.sleep(5)

            url_after = driver.current_url
            handles_after = set(driver.window_handles)
            captured = driver.execute_script("return window.__captured || [];")

            print(f"    URL before: {url_before}")
            print(f"    URL after:  {url_after}")
            print(f"    Changed? {'YES' if url_before != url_after else 'NO'}")
            print(f"    SSO token? {'YES' if 'token' in url_after.lower() else 'NO'}")
            print(f"    Captured window.open: {captured}")

            new_handles = handles_after - handles_before
            if new_handles:
                print(f"    NEW TAB(S) OPENED: {len(new_handles)}")
                for h in new_handles:
                    driver.switch_to.window(h)
                    time.sleep(3)
                    print(f"    New tab URL: {driver.current_url}")
                    screenshot(driver, f"20_badge_{idx+1}_newtab")
                    driver.close()
                driver.switch_to.window(list(handles_before)[0])

            screenshot(driver, f"20_badge_{idx+1}_after")

            # Check for modals/dialogs
            modals = driver.find_elements(By.CSS_SELECTOR, "[role='dialog'], .modal, [class*='modal'], [class*='dialog'], [class*='popup']")
            visible = [m for m in modals if m.is_displayed()]
            if visible:
                print(f"    MODAL appeared! Text: {visible[0].text[:200]}")
                screenshot(driver, f"20_badge_{idx+1}_modal")

        # === STEP 5: Click module names/titles ===
        print("\n\n=== STEP 5: CLICKING MODULE NAMES ===")

        go_to_modules(driver)
        module_names = driver.execute_script("""
            var results = [];
            var badges = [];
            var all = document.querySelectorAll('span, div, p, badge');
            for (var i = 0; i < all.length; i++) {
                var directText = '';
                for (var j = 0; j < all[i].childNodes.length; j++) {
                    if (all[i].childNodes[j].nodeType === 3) directText += all[i].childNodes[j].textContent.trim();
                }
                if (directText === 'Subscribed') badges.push(all[i]);
            }

            for (var i = 0; i < badges.length; i++) {
                var card = badges[i];
                for (var j = 0; j < 10; j++) {
                    card = card.parentElement;
                    if (!card) break;
                    var h = card.querySelector('h1,h2,h3,h4,h5,h6,[class*="title"],[class*="name"]');
                    if (h) {
                        var link = h.querySelector('a') || (h.tagName === 'A' ? h : null);
                        results.push({
                            name: h.textContent.trim(),
                            tag: h.tagName,
                            isLink: !!link,
                            href: link ? link.href : '',
                            cursor: window.getComputedStyle(h).cursor
                        });
                        break;
                    }
                }
            }
            return results;
        """)

        print(f"  Module names found: {len(module_names)}")
        for mn in module_names:
            print(f"    {mn}")

        for idx in range(len(module_names)):
            go_to_modules(driver)

            driver.execute_script("""
                window.__captured = [];
                var orig = window.open;
                window.open = function(url) {
                    window.__captured.push('window.open:' + url);
                    return orig.apply(this, arguments);
                };
            """)

            url_before = driver.current_url
            handles_before = set(driver.window_handles)

            click_result = driver.execute_script("""
                var badges = [];
                var all = document.querySelectorAll('span, div, p, badge');
                for (var i = 0; i < all.length; i++) {
                    var directText = '';
                    for (var j = 0; j < all[i].childNodes.length; j++) {
                        if (all[i].childNodes[j].nodeType === 3) directText += all[i].childNodes[j].textContent.trim();
                    }
                    if (directText === 'Subscribed') badges.push(all[i]);
                }

                var card = badges[arguments[0]];
                if (!card) return {clicked: false};
                for (var j = 0; j < 10; j++) {
                    card = card.parentElement;
                    if (!card) break;
                    var h = card.querySelector('h1,h2,h3,h4,h5,h6');
                    if (h) {
                        var link = h.querySelector('a');
                        if (link) {
                            link.click();
                            return {clicked: true, name: h.textContent.trim(), wasLink: true, href: link.href};
                        } else {
                            h.click();
                            return {clicked: true, name: h.textContent.trim(), wasLink: false};
                        }
                    }
                }
                return {clicked: false};
            """, idx)

            print(f"\n  Name {idx+1}: {click_result}")
            time.sleep(5)

            url_after = driver.current_url
            handles_after = set(driver.window_handles)
            captured = driver.execute_script("return window.__captured || [];")

            print(f"    URL before: {url_before}")
            print(f"    URL after:  {url_after}")
            print(f"    Changed? {'YES' if url_before != url_after else 'NO'}")
            print(f"    SSO token? {'YES' if 'token' in url_after.lower() else 'NO'}")
            print(f"    Captured: {captured}")

            new_handles = handles_after - handles_before
            if new_handles:
                print(f"    NEW TAB(S): {len(new_handles)}")
                for h in new_handles:
                    driver.switch_to.window(h)
                    time.sleep(3)
                    print(f"    New tab URL: {driver.current_url}")
                    screenshot(driver, f"30_name_{idx+1}_newtab")
                    driver.close()
                driver.switch_to.window(list(handles_before)[0])

            screenshot(driver, f"30_name_{idx+1}_after")

        # === STEP 6: Click entire card container ===
        print("\n\n=== STEP 6: CLICKING ENTIRE CARD CONTAINERS ===")

        go_to_modules(driver)
        num_cards = driver.execute_script("""
            var badges = [];
            var all = document.querySelectorAll('span, div, p, badge');
            for (var i = 0; i < all.length; i++) {
                var directText = '';
                for (var j = 0; j < all[i].childNodes.length; j++) {
                    if (all[i].childNodes[j].nodeType === 3) directText += all[i].childNodes[j].textContent.trim();
                }
                if (directText === 'Subscribed') badges.push(all[i]);
            }
            return badges.length;
        """)

        for idx in range(num_cards):
            go_to_modules(driver)

            driver.execute_script("""
                window.__captured = [];
                var orig = window.open;
                window.open = function(url) {
                    window.__captured.push('window.open:' + url);
                    return orig.apply(this, arguments);
                };
            """)

            url_before = driver.current_url
            handles_before = set(driver.window_handles)

            click_result = driver.execute_script("""
                var badges = [];
                var all = document.querySelectorAll('span, div, p, badge');
                for (var i = 0; i < all.length; i++) {
                    var directText = '';
                    for (var j = 0; j < all[i].childNodes.length; j++) {
                        if (all[i].childNodes[j].nodeType === 3) directText += all[i].childNodes[j].textContent.trim();
                    }
                    if (directText === 'Subscribed') badges.push(all[i]);
                }

                var badge = badges[arguments[0]];
                if (!badge) return {clicked: false};
                // Walk up to nearest card-like container
                var card = badge;
                for (var j = 0; j < 10; j++) {
                    card = card.parentElement;
                    if (!card) break;
                    var cls = card.className || '';
                    if (cls.includes('border') || cls.includes('card') || cls.includes('rounded-lg') || cls.includes('shadow')) {
                        card.click();
                        var h = card.querySelector('h1,h2,h3,h4,h5');
                        return {clicked: true, name: h ? h.textContent.trim() : 'Unknown', cardClass: cls.substring(0, 100)};
                    }
                }
                return {clicked: false};
            """, idx)

            print(f"\n  Card {idx+1}: {click_result}")
            time.sleep(5)

            url_after = driver.current_url
            handles_after = set(driver.window_handles)
            captured = driver.execute_script("return window.__captured || [];")

            print(f"    URL before: {url_before}")
            print(f"    URL after:  {url_after}")
            print(f"    Changed? {'YES' if url_before != url_after else 'NO'}")
            print(f"    SSO token? {'YES' if 'token' in url_after.lower() else 'NO'}")
            print(f"    Captured: {captured}")

            new_handles = handles_after - handles_before
            if new_handles:
                print(f"    NEW TAB(S): {len(new_handles)}")
                for h in new_handles:
                    driver.switch_to.window(h)
                    time.sleep(3)
                    new_url = driver.current_url
                    print(f"    New tab URL: {new_url}")
                    print(f"    SSO token in new tab? {'YES' if 'token' in new_url.lower() else 'NO'}")
                    screenshot(driver, f"40_card_{idx+1}_newtab")
                    driver.close()
                driver.switch_to.window(list(handles_before)[0])

            screenshot(driver, f"40_card_{idx+1}_after")

        # === STEP 7: Check for event listeners via JS ===
        print("\n\n=== STEP 7: CHECKING EVENT LISTENERS ===")
        go_to_modules(driver)

        listeners_info = driver.execute_script("""
            // Check if any React/Next.js event handlers are on the cards
            var results = [];
            var badges = [];
            var all = document.querySelectorAll('span, div, p, badge');
            for (var i = 0; i < all.length; i++) {
                var directText = '';
                for (var j = 0; j < all[i].childNodes.length; j++) {
                    if (all[i].childNodes[j].nodeType === 3) directText += all[i].childNodes[j].textContent.trim();
                }
                if (directText === 'Subscribed') badges.push(all[i]);
            }

            for (var i = 0; i < badges.length; i++) {
                var el = badges[i];
                var info = {
                    tag: el.tagName,
                    hasReactProps: false,
                    reactEvents: []
                };
                // Check React internal props
                var keys = Object.keys(el);
                for (var k = 0; k < keys.length; k++) {
                    if (keys[k].startsWith('__react')) {
                        info.hasReactProps = true;
                        info.reactEvents.push(keys[k]);
                    }
                }
                // Check parent chain for click handlers
                var node = el;
                for (var j = 0; j < 5; j++) {
                    var nodeKeys = Object.keys(node);
                    var reactKey = '';
                    for (var k = 0; k < nodeKeys.length; k++) {
                        if (nodeKeys[k].startsWith('__reactFiber') || nodeKeys[k].startsWith('__reactProps')) {
                            reactKey = nodeKeys[k];
                            break;
                        }
                    }
                    if (reactKey && node[reactKey]) {
                        var props = node[reactKey];
                        if (props.onClick || props.memoizedProps && props.memoizedProps.onClick) {
                            info.parentWithClick = j;
                            info.parentTag = node.tagName;
                            info.parentClass = (node.className || '').substring(0, 80);
                            break;
                        }
                    }
                    node = node.parentElement;
                    if (!node) break;
                }
                results.push(info);
            }
            return results;
        """)
        print(f"  Event listener analysis:")
        for i, l in enumerate(listeners_info):
            print(f"    Badge {i+1}: {l}")

        # === FINAL: Full page scroll screenshot ===
        print("\n\n=== FINAL SCREENSHOTS ===")
        go_to_modules(driver)

        # Scroll down to capture all modules
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        screenshot(driver, "50_modules_top")

        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        screenshot(driver, "50_modules_mid")

        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(1)
        screenshot(driver, "50_modules_bottom")

        driver.execute_script("window.scrollTo(0, 2000);")
        time.sleep(1)
        screenshot(driver, "50_modules_bottom2")

        print("\n\n=== COMPLETE ===")

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        screenshot(driver, "fatal_error")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
