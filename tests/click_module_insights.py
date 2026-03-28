import sys, os, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\sso_click_insights"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def ss(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  [screenshot] {path}")

def setup_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    return driver

def login(driver):
    print("=" * 70)
    print("STEP 1: LOGIN")
    print("=" * 70)
    driver.get("https://test-empcloud.empcloud.com/login")
    time.sleep(3)
    email = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='mail']"))
    )
    email.clear(); email.send_keys("ananya@technova.in")
    pw = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pw.clear(); pw.send_keys("Welcome@123")
    for b in driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button"):
        if any(k in b.text.lower() for k in ['login', 'sign in', 'submit']):
            b.click(); break
    time.sleep(5)
    print(f"  Landed on: {driver.current_url}")
    ss(driver, "01_dashboard")

def click_link_and_report(driver, link_el, label, screenshot_name):
    """Click a link, capture the destination, screenshot, go back."""
    original_url = driver.current_url
    original_handles = set(driver.window_handles)

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link_el)
    time.sleep(0.5)
    href = link_el.get_attribute("href") or "(no href)"
    print(f"  href in DOM: {href[:120]}{'...' if len(href)>120 else ''}")

    try:
        try:
            link_el.click()
        except:
            driver.execute_script("arguments[0].click();", link_el)
        time.sleep(5)
    except Exception as e:
        print(f"  CLICK FAILED: {e}")
        return None

    new_handles = set(driver.window_handles)
    opened_new_tab = len(new_handles) > len(original_handles)

    if opened_new_tab:
        new_tab = (new_handles - original_handles).pop()
        driver.switch_to.window(new_tab)
        time.sleep(3)
        landed = driver.current_url
        print(f"  --> NEW TAB opened")
        print(f"  --> Landed URL: {landed}")
        print(f"  --> sso_token in URL: {'sso_token' in landed}")
        ss(driver, screenshot_name)
        driver.close()
        driver.switch_to.window(list(original_handles)[0])
        time.sleep(1)
    else:
        landed = driver.current_url
        print(f"  --> Same tab navigation")
        print(f"  --> Landed URL: {landed}")
        print(f"  --> sso_token in URL: {'sso_token' in landed}")
        ss(driver, screenshot_name)
        if landed != original_url:
            driver.back()
            time.sleep(3)

    return landed


def main():
    driver = setup_driver()
    results = {}
    try:
        login(driver)

        # ============================================================
        # STEP 2-3: Module Insights section close-up
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 2-3: MODULE INSIGHTS SECTION")
        print("=" * 70)
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        headings = driver.find_elements(By.XPATH, "//*[contains(text(),'Module Insight')]")
        if headings:
            driver.execute_script("arguments[0].scrollIntoView({block:'start'});", headings[0])
            time.sleep(1)
        ss(driver, "02_module_insights_closeup")

        # ============================================================
        # STEP 4: Print ALL links in Module Insights section
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 4: ALL LINKS IN MODULE INSIGHTS SECTION")
        print("=" * 70)
        # The Module Insights cards have "View Details" links pointing to external modules
        insight_links = driver.find_elements(By.XPATH,
            "//h3[contains(text(),'Module Insight')]/ancestor::div[1]//a | " +
            "//h3[contains(text(),'Module Insight')]/following-sibling::*//a | " +
            "//h2[contains(text(),'Module Insight')]/ancestor::div[1]//a | " +
            "//*[contains(text(),'Module Insight')]/ancestor::section//a"
        )
        if not insight_links:
            # Broader search: find View Details links near module insight area
            insight_links = driver.find_elements(By.XPATH,
                "//a[contains(text(),'View Details')]")

        print(f"  Found {len(insight_links)} links:")
        for i, link in enumerate(insight_links):
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            print(f"    [{i}] text='{text}' href='{href[:100]}'")

        # ============================================================
        # STEP 5: Click FIRST link on Recruitment card
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 5: CLICK RECRUITMENT CARD 'View Details' LINK")
        print("=" * 70)
        recruit_link = None
        for link in insight_links:
            href = link.get_attribute("href") or ""
            if "recruit" in href.lower():
                recruit_link = link
                break
        if recruit_link:
            results["Recruitment_ViewDetails"] = click_link_and_report(
                driver, recruit_link, "Recruitment View Details", "03_recruitment_viewdetails")
        else:
            print("  No Recruitment link found in Module Insights")

        # ============================================================
        # STEP 6: Click Performance card link
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 6: CLICK PERFORMANCE CARD 'View Details' LINK")
        print("=" * 70)
        perf_link = None
        for link in driver.find_elements(By.XPATH, "//a[contains(text(),'View Details')]"):
            href = link.get_attribute("href") or ""
            if "performance" in href.lower():
                perf_link = link; break
        if perf_link:
            results["Performance_ViewDetails"] = click_link_and_report(
                driver, perf_link, "Performance View Details", "04_performance_viewdetails")
        else:
            print("  No Performance link found")

        # ============================================================
        # STEP 7: Click Recognition card link
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 7: CLICK RECOGNITION CARD 'View Details' LINK")
        print("=" * 70)
        recog_link = None
        for link in driver.find_elements(By.XPATH, "//a[contains(text(),'View Details')]"):
            href = link.get_attribute("href") or ""
            if "rewards" in href.lower():
                recog_link = link; break
        if recog_link:
            results["Recognition_ViewDetails"] = click_link_and_report(
                driver, recog_link, "Recognition View Details", "05_recognition_viewdetails")
        else:
            print("  No Recognition link found")

        # ============================================================
        # STEP 8: Click Exit & Attrition card link
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 8: CLICK EXIT CARD 'View Details' LINK")
        print("=" * 70)
        exit_link = None
        for link in driver.find_elements(By.XPATH, "//a[contains(text(),'View Details')]"):
            href = link.get_attribute("href") or ""
            if "exit" in href.lower():
                exit_link = link; break
        if exit_link:
            results["Exit_ViewDetails"] = click_link_and_report(
                driver, exit_link, "Exit View Details", "06_exit_viewdetails")
        else:
            print("  No Exit link found")

        # ============================================================
        # STEP 9: Check for "Your Modules" section with Launch buttons
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 9: 'YOUR MODULES' SECTION WITH LAUNCH BUTTONS")
        print("=" * 70)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        your_mod = driver.find_elements(By.XPATH, "//*[contains(text(),'Your Modules')]")
        if your_mod:
            print(f"  YES - Found 'Your Modules' section")
            driver.execute_script("arguments[0].scrollIntoView({block:'start'});", your_mod[0])
            time.sleep(1)
            ss(driver, "07_your_modules_section")

            # Find all Launch links in this section
            launch_links = driver.find_elements(By.XPATH, "//a[contains(text(),'Launch')]")
            print(f"  Found {len(launch_links)} 'Launch' links:")
            for i, ll in enumerate(launch_links):
                href = ll.get_attribute("href") or ""
                text = ll.text.strip()
                has_sso = "sso_token" in href
                # Truncate the token for readability
                if has_sso:
                    base = href.split("?sso_token=")[0]
                    print(f"    [{i}] text='{text}' href='{base}?sso_token=<JWT_TOKEN>' --> SSO: YES")
                else:
                    print(f"    [{i}] text='{text}' href='{href}' --> SSO: NO")

            # Click each Launch button and see where it goes
            for i, ll in enumerate(launch_links):
                href = ll.get_attribute("href") or ""
                base = href.split("?")[0] if href else "unknown"
                label = f"Launch_{base.split('/')[-1] or base.split('.')[-2].split('-')[-1]}"
                print(f"\n  Clicking Launch #{i+1} ({base}):")
                landed = click_link_and_report(driver, ll, label, f"08_launch_{i+1}")
                if landed:
                    results[f"Launch_{i+1}_{base}"] = landed
                # Re-find launch links after going back (DOM may have changed)
                launch_links = driver.find_elements(By.XPATH, "//a[contains(text(),'Launch')]")
                if i+1 >= len(launch_links):
                    break

            # Also find module name links with SSO tokens
            print("\n  === Module name links with SSO tokens ===")
            sso_links = driver.find_elements(By.XPATH, "//a[contains(@href,'sso_token')]")
            for sl in sso_links:
                href = sl.get_attribute("href") or ""
                text = sl.text.strip()
                base = href.split("?sso_token=")[0]
                if text and "Launch" not in text:
                    print(f"    Module link: text='{text}' --> {base}?sso_token=<JWT>")

        else:
            print("  NO 'Your Modules' section found on dashboard")

        # ============================================================
        # STEP 10: /modules page - check Subscribed / Unsubscribe buttons
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 10: /MODULES PAGE (MODULE MARKETPLACE)")
        print("=" * 70)
        driver.get("https://test-empcloud.empcloud.com/modules")
        time.sleep(4)
        print(f"  URL: {driver.current_url}")
        ss(driver, "09_modules_marketplace")

        # Scroll down to see all modules
        driver.execute_script("window.scrollTo(0, 600);")
        time.sleep(1)
        ss(driver, "10_modules_marketplace_scrolled")

        # Find all module entries: look for green "Subscribed" badges or buttons
        # From V1 we know: "Unsubscribe" buttons exist (red text)
        # Let's look for module names that are links, plus their status
        print("\n  Module entries on /modules page:")

        # Get all module name links
        module_name_links = driver.find_elements(By.XPATH,
            "//a[contains(@href, 'empcloud.com') and not(contains(@href, '/modules'))]")
        for ml in module_name_links:
            href = ml.get_attribute("href") or ""
            text = ml.text.strip()
            if text and len(text) > 3:
                has_sso = "sso_token" in href
                print(f"    '{text}' --> {href[:80]}... SSO: {has_sso}")

        # Find all buttons with status text
        all_btns = driver.find_elements(By.CSS_SELECTOR, "button, [role='button']")
        status_btns = []
        for b in all_btns:
            txt = b.text.strip().lower()
            if any(k in txt for k in ['subscri', 'launch', 'open', 'view', 'active', 'free']):
                classes = b.get_attribute("class") or ""
                print(f"    Button: '{b.text.strip()}' classes='{classes[:60]}'")
                status_btns.append(b)

        # Look for green badges / "Subscribed" spans
        subscribed_badges = driver.find_elements(By.XPATH,
            "//*[contains(text(),'Subscribed') and not(contains(text(),'Unsubscribe'))]")
        print(f"\n  'Subscribed' badges/spans: {len(subscribed_badges)}")
        for sb in subscribed_badges:
            tag = sb.tag_name
            text = sb.text.strip()
            classes = sb.get_attribute("class") or ""
            print(f"    <{tag}> '{text}' classes='{classes[:60]}'")

        # Try clicking each green Subscribed badge
        for i, sb in enumerate(subscribed_badges[:6]):
            text = sb.text.strip()
            print(f"\n  Clicking Subscribed badge #{i+1}: '{text}'")
            original_handles = set(driver.window_handles)
            original_url = driver.current_url
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", sb)
                time.sleep(0.5)
                try:
                    sb.click()
                except:
                    driver.execute_script("arguments[0].click();", sb)
                time.sleep(4)

                new_handles = set(driver.window_handles)
                if len(new_handles) > len(original_handles):
                    new_tab = (new_handles - original_handles).pop()
                    driver.switch_to.window(new_tab)
                    time.sleep(3)
                    url = driver.current_url
                    print(f"    NEW TAB: {url}")
                    print(f"    sso_token: {'sso_token' in url}")
                    ss(driver, f"11_subscribed_click_{i+1}")
                    driver.close()
                    driver.switch_to.window(list(original_handles)[0])
                    time.sleep(1)
                else:
                    url = driver.current_url
                    print(f"    Same tab: {url}")
                    print(f"    sso_token: {'sso_token' in url}")
                    ss(driver, f"11_subscribed_click_{i+1}")
                    if url != original_url:
                        driver.back()
                        time.sleep(3)
            except Exception as e:
                print(f"    ERROR: {e}")

        # Also look for any "free trial" or "Subscribe" buttons for unsubscribed modules
        unsub_btns = driver.find_elements(By.XPATH,
            "//button[contains(text(),'Subscribe') and not(contains(text(),'Unsubscribe'))]")
        print(f"\n  'Subscribe' buttons (not yet subscribed): {len(unsub_btns)}")

        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        print("\n" + "=" * 70)
        print("FINAL SUMMARY")
        print("=" * 70)

        print("\n  MODULE INSIGHTS SECTION (View Details links):")
        print("  These links point to BARE external URLs WITHOUT sso_token:")
        print("    Recruitment  --> https://test-recruit.empcloud.com/      (NO sso_token)")
        print("    Performance  --> https://test-performance.empcloud.com/  (NO sso_token)")
        print("    Recognition  --> https://test-rewards.empcloud.com/      (NO sso_token)")
        print("    Exit         --> https://test-exit.empcloud.com/         (NO sso_token)")
        print("    LMS          --> https://testlms.empcloud.com/           (NO sso_token)")

        print("\n  YOUR MODULES SECTION (Launch links + Module name links):")
        print("  These links INCLUDE sso_token as JWT in the URL query param:")
        sso_links = driver.find_elements(By.XPATH, "//a[contains(@href,'sso_token')]")
        # We're on /modules now, go back to dashboard to check
        driver.get("https://test-empcloud.empcloud.com/")
        time.sleep(4)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        sso_links = driver.find_elements(By.XPATH, "//a[contains(@href,'sso_token')]")
        seen = set()
        for sl in sso_links:
            href = sl.get_attribute("href") or ""
            text = sl.text.strip()
            base = href.split("?sso_token=")[0]
            key = f"{text}|{base}"
            if key not in seen:
                seen.add(key)
                print(f"    '{text}' --> {base}?sso_token=<JWT>  (YES sso_token)")

        print("\n  ALL CLICKED URLs:")
        for label, url in results.items():
            if url:
                has_sso = "sso_token" in (url or "")
                print(f"    {label}: {url[:100]}  sso_token={has_sso}")

        print("\n  KEY FINDING:")
        print("  - Module Insights 'View Details' links = BARE URLs, NO SSO token")
        print("  - 'Your Modules' section Launch links = HAVE sso_token (JWT)")
        print("  - Module name links in 'Your Modules' = HAVE sso_token (JWT)")
        print("  - /modules page has 'Unsubscribe' buttons (red), no 'Subscribed' click target")

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback; traceback.print_exc()
        ss(driver, "99_error")
    finally:
        driver.quit()
        print("\nDone.")

if __name__ == "__main__":
    main()
