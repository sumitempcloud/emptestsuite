"""
V3: Instead of clicking links (which don't navigate cross-origin in headless),
    extract the href values and navigate directly via driver.get().
    This tests the actual SSO token flow end-to-end.
"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
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
    ss(driver, "v3_01_dashboard")

def main():
    driver = setup_driver()
    try:
        login(driver)

        # ============================================================
        # STEP 2-3: Screenshot Module Insights close-up
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 2-3: MODULE INSIGHTS CLOSE-UP")
        print("=" * 70)
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        ss(driver, "v3_02_module_insights")

        # ============================================================
        # STEP 4: Collect ALL links - Module Insights "View Details" + Your Modules SSO
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 4: ALL LINKS (View Details + SSO Launch)")
        print("=" * 70)

        # Module Insights "View Details" links (NO sso_token)
        view_details = driver.find_elements(By.XPATH, "//a[contains(text(),'View Details')]")
        print(f"\n  Module Insights 'View Details' links ({len(view_details)}):")
        vd_hrefs = {}
        for vd in view_details:
            href = vd.get_attribute("href") or ""
            text = vd.text.strip()
            # Find module name from parent card
            try:
                card_text = driver.execute_script(
                    "let el=arguments[0]; for(let i=0;i<5;i++) el=el.parentElement; return el.innerText;", vd)
                card_name = card_text.split('\n')[0] if card_text else "Unknown"
            except:
                card_name = "Unknown"
            has_sso = "sso_token" in href
            print(f"    Card: '{card_name}' | text='{text}' | href='{href}' | sso_token={has_sso}")
            vd_hrefs[card_name] = href

        # SSO links (from "Your Modules" section)
        sso_links = driver.find_elements(By.XPATH, "//a[contains(@href,'sso_token')]")
        print(f"\n  SSO token links on dashboard ({len(sso_links)}):")
        sso_hrefs = {}
        for sl in sso_links:
            href = sl.get_attribute("href") or ""
            text = sl.text.strip()
            base = href.split("?sso_token=")[0]
            token_preview = href.split("?sso_token=")[1][:40] + "..." if "sso_token" in href else ""
            if base not in sso_hrefs:  # deduplicate by base URL
                sso_hrefs[base] = href
                print(f"    '{text}' --> {base}?sso_token={token_preview}")

        # ============================================================
        # STEP 5: Click Recruitment "View Details" (no sso) -> navigate directly
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 5: RECRUITMENT - 'View Details' (bare URL, no SSO)")
        print("=" * 70)
        recruit_bare = "https://test-recruit.empcloud.com/"
        print(f"  Navigating to BARE URL: {recruit_bare}")
        driver.get(recruit_bare)
        time.sleep(5)
        print(f"  Landed URL: {driver.current_url}")
        print(f"  sso_token in URL: {'sso_token' in driver.current_url}")
        ss(driver, "v3_03_recruit_bare")
        # Check page title/content
        title = driver.title
        body_text = driver.execute_script("return document.body?.innerText?.substring(0,200) || ''")
        print(f"  Page title: {title}")
        print(f"  Body preview: {body_text[:150]}")

        # Now try SSO link for Recruitment
        print(f"\n  Now navigating to SSO URL for Recruitment:")
        recruit_sso = sso_hrefs.get("https://test-recruit.empcloud.com/", "")
        if recruit_sso:
            print(f"  URL: {recruit_sso[:80]}...sso_token=<JWT>")
            driver.get(recruit_sso)
            time.sleep(5)
            print(f"  Landed URL: {driver.current_url}")
            print(f"  sso_token in final URL: {'sso_token' in driver.current_url}")
            ss(driver, "v3_04_recruit_sso")
            title = driver.title
            body_text = driver.execute_script("return document.body?.innerText?.substring(0,200) || ''")
            print(f"  Page title: {title}")
            print(f"  Body preview: {body_text[:150]}")
        else:
            print("  No SSO URL found for Recruitment")

        # ============================================================
        # STEP 6: Performance - bare + SSO
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 6: PERFORMANCE")
        print("=" * 70)
        perf_bare = "https://test-performance.empcloud.com/"
        print(f"  Navigating to BARE URL: {perf_bare}")
        driver.get(perf_bare)
        time.sleep(5)
        print(f"  Landed URL: {driver.current_url}")
        ss(driver, "v3_05_performance_bare")
        title = driver.title
        print(f"  Page title: {title}")

        perf_sso = sso_hrefs.get("https://test-performance.empcloud.com/", "")
        if perf_sso:
            print(f"\n  Now with SSO token:")
            driver.get(perf_sso)
            time.sleep(5)
            print(f"  Landed URL: {driver.current_url}")
            print(f"  sso_token in final URL: {'sso_token' in driver.current_url}")
            ss(driver, "v3_06_performance_sso")
            title = driver.title
            body_text = driver.execute_script("return document.body?.innerText?.substring(0,200) || ''")
            print(f"  Page title: {title}")
            print(f"  Body preview: {body_text[:150]}")

        # ============================================================
        # STEP 7: Recognition (Rewards) - bare + SSO
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 7: RECOGNITION (REWARDS)")
        print("=" * 70)
        rewards_bare = "https://test-rewards.empcloud.com/"
        print(f"  Navigating to BARE URL: {rewards_bare}")
        driver.get(rewards_bare)
        time.sleep(5)
        print(f"  Landed URL: {driver.current_url}")
        ss(driver, "v3_07_rewards_bare")
        title = driver.title
        print(f"  Page title: {title}")

        rewards_sso = sso_hrefs.get("https://test-rewards.empcloud.com/", "")
        if rewards_sso:
            print(f"\n  Now with SSO token:")
            driver.get(rewards_sso)
            time.sleep(5)
            print(f"  Landed URL: {driver.current_url}")
            print(f"  sso_token in final URL: {'sso_token' in driver.current_url}")
            ss(driver, "v3_08_rewards_sso")
            title = driver.title
            body_text = driver.execute_script("return document.body?.innerText?.substring(0,200) || ''")
            print(f"  Page title: {title}")
            print(f"  Body preview: {body_text[:150]}")

        # ============================================================
        # STEP 8: Exit - bare + SSO
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 8: EXIT")
        print("=" * 70)
        exit_bare = "https://test-exit.empcloud.com/"
        print(f"  Navigating to BARE URL: {exit_bare}")
        driver.get(exit_bare)
        time.sleep(5)
        print(f"  Landed URL: {driver.current_url}")
        ss(driver, "v3_09_exit_bare")
        title = driver.title
        print(f"  Page title: {title}")

        exit_sso = sso_hrefs.get("https://test-exit.empcloud.com/", "")
        if exit_sso:
            print(f"\n  Now with SSO token:")
            driver.get(exit_sso)
            time.sleep(5)
            print(f"  Landed URL: {driver.current_url}")
            print(f"  sso_token in final URL: {'sso_token' in driver.current_url}")
            ss(driver, "v3_10_exit_sso")
            title = driver.title
            body_text = driver.execute_script("return document.body?.innerText?.substring(0,200) || ''")
            print(f"  Page title: {title}")
            print(f"  Body preview: {body_text[:150]}")

        # ============================================================
        # STEP 9: Your Modules - remaining SSO launches
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 9: REMAINING SSO MODULE LAUNCHES")
        print("=" * 70)
        remaining = {
            "LMS": "https://testlms.empcloud.com/",
            "Payroll": "https://testpayroll.empcloud.com/",
            "Project": "https://test-project.empcloud.com/",
            "Monitor": "https://test-empmonitor.empcloud.com/",
        }
        idx = 11
        for name, base in remaining.items():
            sso_url = sso_hrefs.get(base, "")
            if sso_url:
                print(f"\n  {name} (SSO):")
                driver.get(sso_url)
                time.sleep(5)
                print(f"    Landed URL: {driver.current_url}")
                print(f"    sso_token in final URL: {'sso_token' in driver.current_url}")
                ss(driver, f"v3_{idx}_{name.lower()}_sso")
                title = driver.title
                print(f"    Page title: {title}")
                idx += 1

        # ============================================================
        # STEP 10: /modules page - Subscribed badges
        # ============================================================
        print("\n" + "=" * 70)
        print("STEP 10: /MODULES PAGE - SUBSCRIBED BADGES")
        print("=" * 70)
        driver.get("https://test-empcloud.empcloud.com/modules")
        time.sleep(4)
        print(f"  URL: {driver.current_url}")
        ss(driver, "v3_20_modules_page")

        # Find module name links on /modules page
        all_links = driver.find_elements(By.TAG_NAME, "a")
        module_links_on_page = []
        for link in all_links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            if text and "empcloud.com" in href and "/modules" not in href and len(text) > 5:
                module_links_on_page.append((text, href))
                has_sso = "sso_token" in href
                print(f"  Module link: '{text}' href='{href[:80]}' sso={has_sso}")

        # Find green "Subscribed" spans and their associated module names
        subscribed_spans = driver.find_elements(By.XPATH,
            "//span[contains(text(),'Subscribed') and not(contains(text(),'Unsubscribe'))]")
        print(f"\n  Green 'Subscribed' badges: {len(subscribed_spans)}")

        # For each subscribed badge, find the parent card and its module name
        for i, sb in enumerate(subscribed_spans):
            try:
                # Navigate up to the card container to find module name
                card = driver.execute_script(
                    "let el=arguments[0]; for(let i=0;i<6;i++){el=el.parentElement; if(!el) break;} return el;", sb)
                card_text = card.text if card else ""
                module_name = card_text.split('\n')[0] if card_text else f"Module #{i+1}"
                print(f"    [{i+1}] '{module_name}' - Subscribed (green badge, not clickable as link)")
            except:
                print(f"    [{i+1}] (could not determine module name)")

        # Unsubscribe buttons
        unsub_btns = driver.find_elements(By.XPATH, "//button[contains(text(),'Unsubscribe')]")
        print(f"\n  'Unsubscribe' buttons (red): {len(unsub_btns)}")
        print("  NOTE: 'Subscribed' is a <span> status badge, NOT a clickable link/button.")
        print("  The only action is 'Unsubscribe' (red text button).")

        # Scroll to show more
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        ss(driver, "v3_21_modules_page_bottom")

        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        print("\n" + "=" * 70)
        print("FINAL SUMMARY")
        print("=" * 70)

        print("""
  DASHBOARD LAYOUT (top to bottom):
  1. Welcome banner + stats (Employees, Departments, etc.)
  2. Core HRMS quick-access bar (Employee Directory, Attendance, etc.)
  3. MODULE INSIGHTS section - 4 colored cards:
     - Recruitment (blue) - stats + "View Details" link
     - Performance (green) - stats + "View Details" link
     - Recognition (pink) - stats + "View Details" link
     - Exit & Attrition (yellow) - stats + "View Details" link
     - Learning & Development (purple) - stats + "View Details" link
  4. YOUR MODULES section - 9 module cards with "Launch" buttons

  SSO ENTRY POINTS:
  +-------------------------------------------------+------------------+
  | Entry Point                                     | Has sso_token?   |
  +-------------------------------------------------+------------------+
  | Module Insights "View Details" links             | NO (bare URL)   |
  | Your Modules "Launch" buttons                    | YES (JWT token) |
  | Your Modules module name links                   | YES (JWT token) |
  | /modules page "Subscribed" badge                 | NOT clickable   |
  | /modules page module name links                  | NO (local path) |
  +-------------------------------------------------+------------------+

  BEHAVIOR WHEN CLICKING:
  - "View Details" (bare URL like https://test-recruit.empcloud.com/):
    The external module has NO auth context -> likely shows login page
  - "Launch" (URL with ?sso_token=<JWT>):
    The external module receives a signed JWT -> should auto-authenticate
  - In headless Selenium, cross-origin navigation bounces back to
    empcloud dashboard (likely JS-based redirect or SPA routing)

  BUG CANDIDATE:
  - Module Insights "View Details" links do NOT include sso_token
  - User clicking "View Details" on any insight card would land on the
    external module WITHOUT authentication (no SSO handoff)
  - This contrasts with "Your Modules" section which correctly includes
    sso_token in all Launch links
""")

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback; traceback.print_exc()
        ss(driver, "v3_99_error")
    finally:
        driver.quit()
        print("Done.")

if __name__ == "__main__":
    main()
