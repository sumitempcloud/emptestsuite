"""
V8 - Final click test with proper module name resolution + screenshots.
"""
import sys, os, time, json, traceback
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys

SCREENSHOTS = r"C:\Users\Admin\screenshots\sso_explore_modules"
BASE = "https://test-empcloud.empcloud.com"
EMAIL = "ananya@technova.in"
PASSW = "Welcome@123"

# Known module URL map (from previous runs)
MODULE_URL_MAP = {
    'https://test-rewards.empcloud.com': ('emp-rewards', 'Rewards & Recognition'),
    'https://test-recruit.empcloud.com': ('emp-recruit', 'Recruitment & Talent Acquisition'),
    'https://test-project.empcloud.com': ('emp-projects', 'Project Management & Time Tracking'),
    'https://test-performance.empcloud.com': ('emp-performance', 'Performance Management & Career Development'),
    'https://testpayroll.empcloud.com': ('emp-payroll', 'Payroll Management'),
    'https://testlms.empcloud.com': ('emp-lms', 'Learning Management & Training'),
    'https://test-field.empcloud.com': ('emp-field', 'Field Force Management & GPS Tracking'),
    'https://test-exit.empcloud.com': ('emp-exit', 'Exit Management & Offboarding'),
    'https://test-empmonitor.empcloud.com': ('emp-monitor', 'Employee Monitoring & Activity Tracking'),
}

def setup():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-dev-shm-usage")
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(5)
    return d

def ss(d, name):
    path = os.path.join(SCREENSHOTS, f"{name}.png")
    d.save_screenshot(path)
    print(f"  [SS] {name}.png")

def login(d):
    print("=== LOGIN ===")
    d.get(f"{BASE}/login")
    time.sleep(4)
    email_el = d.find_element(By.CSS_SELECTOR, "input[type='email']")
    email_el.click()
    time.sleep(0.2)
    email_el.send_keys(Keys.CONTROL + "a")
    time.sleep(0.1)
    email_el.send_keys(EMAIL)
    pw_el = d.find_element(By.CSS_SELECTOR, "input[type='password']")
    pw_el.click()
    time.sleep(0.2)
    pw_el.send_keys(Keys.CONTROL + "a")
    time.sleep(0.1)
    pw_el.send_keys(PASSW)
    time.sleep(0.5)
    for b in d.find_elements(By.CSS_SELECTOR, "button"):
        if 'sign in' in b.text.strip().lower():
            b.click()
            break
    try:
        WebDriverWait(d, 15).until(lambda dr: '/login' not in dr.current_url)
    except:
        pass
    time.sleep(2)
    print(f"  URL: {d.current_url}")
    return '/login' not in d.current_url

def main():
    d = setup()
    try:
        if not login(d):
            print("Login failed")
            d.quit()
            return

        # ========================================
        # 1. Dashboard full scroll
        # ========================================
        print("\n=== DASHBOARD FULL SCROLL ===")
        d.get(f"{BASE}/")
        time.sleep(5)

        # Force scroll to load lazy content
        for scroll_y in range(0, 5000, 300):
            d.execute_script(f"window.scrollTo(0, {scroll_y})")
            time.sleep(0.2)
        time.sleep(1)

        total_h = d.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
        print(f"  Total height after scrolling: {total_h}")

        # Capture from top
        d.execute_script("window.scrollTo(0, 0)")
        time.sleep(0.3)
        pos = 0
        part = 0
        while pos < total_h:
            d.execute_script(f"window.scrollTo(0, {pos})")
            time.sleep(0.3)
            ss(d, f"40_dash_{part:02d}")
            pos += 900
            part += 1

        # ========================================
        # 2. Click-test each module Launch link
        # ========================================
        print("\n=== MODULE LAUNCH CLICK TESTS ===")

        results = []

        for base_url, (slug, name) in MODULE_URL_MAP.items():
            safe = slug.replace('-', '_')
            print(f"\n  --- {name} ({slug}) ---")
            print(f"      Target: {base_url}")

            try:
                d.get(f"{BASE}/")
                time.sleep(4)

                # Scroll down to load "Your Modules" section
                for sy in range(0, 3000, 300):
                    d.execute_script(f"window.scrollTo(0, {sy})")
                    time.sleep(0.15)
                time.sleep(1)

                handles_before = set(d.window_handles)

                # Find the Launch link for this module
                found = d.execute_script("""
                    var baseUrl = arguments[0];
                    var links = document.querySelectorAll('a');
                    for (var i = 0; i < links.length; i++) {
                        var href = links[i].getAttribute('href') || '';
                        if (href.includes(baseUrl) && href.includes('sso_token') &&
                            links[i].innerText.trim() === 'Launch') {
                            links[i].scrollIntoView({block: 'center'});
                            return true;
                        }
                    }
                    return false;
                """, base_url)

                if not found:
                    print(f"      Launch link not found")
                    results.append({
                        'module': name, 'slug': slug, 'target': base_url,
                        'status': 'NOT_FOUND', 'actual': '', 'title': '', 'new_tab': False
                    })
                    continue

                time.sleep(0.3)
                ss(d, f"50_before_{safe}")

                # Click the Launch link
                d.execute_script("""
                    var baseUrl = arguments[0];
                    var links = document.querySelectorAll('a');
                    for (var i = 0; i < links.length; i++) {
                        var href = links[i].getAttribute('href') || '';
                        if (href.includes(baseUrl) && href.includes('sso_token') &&
                            links[i].innerText.trim() === 'Launch') {
                            links[i].click();
                            return;
                        }
                    }
                """, base_url)

                time.sleep(5)

                handles_after = set(d.window_handles)
                new_tabs = handles_after - handles_before

                if new_tabs:
                    new_h = list(new_tabs)[0]
                    d.switch_to.window(new_h)
                    time.sleep(3)
                    url_after = d.current_url
                    title_after = d.title
                    ss(d, f"50_after_{safe}")
                    d.close()
                    d.switch_to.window(list(handles_before)[0])
                else:
                    url_after = d.current_url
                    title_after = d.title
                    ss(d, f"50_after_{safe}")

                url_base = url_after.split('?')[0]
                has_sso = 'sso_token' in url_after
                print(f"      Result: {url_base}")
                print(f"      Title: {title_after}")
                print(f"      New tab: {bool(new_tabs)}, SSO still in URL: {has_sso}")

                results.append({
                    'module': name, 'slug': slug, 'target': base_url,
                    'status': 'OK', 'actual': url_base, 'title': title_after,
                    'new_tab': bool(new_tabs), 'sso_consumed': not has_sso,
                })

            except Exception as e:
                print(f"      Error: {e}")
                results.append({
                    'module': name, 'slug': slug, 'target': base_url,
                    'status': f'ERROR: {e}', 'actual': '', 'title': '', 'new_tab': False
                })

        # ========================================
        # 3. Billing page tabs
        # ========================================
        print("\n=== BILLING PAGE TABS ===")
        d.get(f"{BASE}/billing")
        time.sleep(4)
        ss(d, "60_billing_subscriptions")

        # The tabs are visible in the screenshot: Subscriptions, Invoices, Payments, Overview
        # They might be <a> tags or styled buttons
        tab_html = d.execute_script("""
            // Get all elements in the tab row area
            var all = document.querySelectorAll('*');
            var tabRow = null;
            for (var i = 0; i < all.length; i++) {
                var el = all[i];
                var rect = el.getBoundingClientRect();
                // Tab row is typically between y=60 and y=120 on billing page
                if (rect.y > 55 && rect.y < 130 && rect.height > 20 && rect.height < 60
                    && rect.width > 500 && !el.closest('nav')) {
                    return el.outerHTML.substring(0, 3000);
                }
            }
            return 'NOT FOUND';
        """)
        print(f"  Tab row HTML: {tab_html[:500]}")

        # Try clicking tabs by text content with broader matching
        for tab_text in ['Invoices', 'Payments', 'Overview']:
            print(f"\n  --- Tab: {tab_text} ---")
            d.get(f"{BASE}/billing")
            time.sleep(3)

            # Click using XPath
            try:
                elements = d.find_elements(By.XPATH, f"//*[text()='{tab_text}']")
                for el in elements:
                    if el.is_displayed() and not d.execute_script("return arguments[0].closest('nav') !== null", el):
                        print(f"    Found: <{el.tag_name}> '{el.text}'")
                        el.click()
                        time.sleep(2)
                        ss(d, f"60_billing_{tab_text.lower()}")
                        print(f"    URL: {d.current_url}")
                        break
                else:
                    # Try partial match
                    elements = d.find_elements(By.XPATH, f"//*[contains(text(), '{tab_text}')]")
                    for el in elements:
                        if el.is_displayed() and not d.execute_script("return arguments[0].closest('nav') !== null", el):
                            print(f"    Partial match: <{el.tag_name}> '{el.text.strip()[:40]}'")
                            el.click()
                            time.sleep(2)
                            ss(d, f"60_billing_{tab_text.lower()}")
                            break
                    else:
                        print(f"    Tab not found")
            except Exception as e:
                print(f"    Error: {e}")

        # ========================================
        # DEFINITIVE SUMMARY
        # ========================================
        print("\n" + "="*80)
        print("  COMPLETE LIST OF ALL DISCOVERED MODULE LAUNCH MECHANISMS")
        print("="*80)

        print("""
========================================================================
A. /modules PAGE (Module Marketplace) - SUBSCRIPTION MANAGEMENT ONLY
========================================================================
  URL: /modules
  Purpose: Subscribe/unsubscribe to modules
  Interactive elements per module row:
    - Module title (h3) - NOT clickable (cursor:auto, no onClick handler)
    - Module slug (span, e.g. "emp-payroll")
    - "Subscribed" badge (green checkmark + text)
    - "Unsubscribe" button (red text, class: text-xs text-red-500)
    - Some modules show "Free tier" badge
  NO launch, open, view, go, or access links exist on this page.
  NO clickable cards - the rows have cursor:auto and no React onClick.

  10 Modules listed:
""")
        modules_info = [
            ('Biometric Verification & Access Control', 'emp-biometrics'),
            ('Employee Monitoring & Activity Tracking', 'emp-monitor'),
            ('Exit Management & Offboarding', 'emp-exit'),
            ('Field Force Management & GPS Tracking', 'emp-field'),
            ('Learning Management & Training', 'emp-lms'),
            ('Payroll Management', 'emp-payroll'),
            ('Performance Management & Career Development', 'emp-performance'),
            ('Project Management & Time Tracking', 'emp-projects'),
            ('Recruitment & Talent Acquisition', 'emp-recruit'),
            ('Rewards & Recognition', 'emp-rewards'),
        ]
        for name, slug in modules_info:
            print(f"    {name} (slug: {slug}) - Subscribed")

        print("""
========================================================================
B. DASHBOARD (/) - PRIMARY MODULE LAUNCH LOCATION
========================================================================
  The dashboard has these module-related sections:

  1. "Module Insights" section:
     - Cards for Recruitment, Performance, Recognition, Exit & Attrition, Learning
     - "View Details" links (NO sso_token, direct URL)

  2. "Your Modules" section (scrolled down):
     - Each module has TWO launch mechanisms:
       a) Module name as clickable link (with ?sso_token=<JWT>)
       b) "Launch" text link (with ?sso_token=<JWT>)
     - All open in NEW TAB
     - SSO token is consumed on redirect (not visible in final URL)
""")
        print("  MODULE LAUNCH URL MAP:")
        for base_url, (slug, name) in sorted(MODULE_URL_MAP.items(), key=lambda x: x[1][1]):
            # Find click result
            cr = next((r for r in results if r['slug'] == slug), None)
            status = cr['status'] if cr else 'unknown'
            actual = cr.get('actual', '') if cr else ''
            title = cr.get('title', '') if cr else ''

            print(f"\n    {name}")
            print(f"      Slug: {slug}")
            print(f"      Launch URL: {base_url}?sso_token=<JWT>")
            print(f"      Click result: {actual} (title: {title})")

        print(f"""
    Biometric Verification & Access Control
      Slug: emp-biometrics
      Launch URL: NONE (features accessible within Attendance module)
      Note: No separate external app - biometric features are integrated

========================================================================
C. /billing PAGE - SUBSCRIPTION COSTS
========================================================================
  URL: /billing
  Shows: Monthly cost (Rs 1,00,000.00), per-module pricing
  Tabs: Subscriptions, Invoices, Payments, Overview
  NO module launch links on this page.

========================================================================
D. SIDEBAR - 51 INTERNAL NAVIGATION LINKS
========================================================================
  All links are internal to the main EmpCloud app.
  NO external module launch links in sidebar.
  Key sections: Dashboard, Self Service, Modules, Billing, Users, Employees,
  Probation, Org Chart, AI Assistant, My Team, Attendance, Leave, Comp-Off,
  Documents, Announcements, Policies, Settings, Custom Fields, Audit Log,
  Positions (Dashboard/List/Vacancies/Headcount Plans),
  Community (Forum/Create Post/Dashboard),
  Events (Events/My Events/Dashboard),
  Whistleblowing (Submit/Track/Dashboard/All Reports),
  Helpdesk (My Tickets/All Tickets/Dashboard/Knowledge Base),
  Surveys (Dashboard/All/Active),
  Wellness (Main/My/Check-in/Dashboard),
  Assets (Dashboard/All/Categories),
  Feedback (Submit/My/All/Dashboard)

========================================================================
E. SSO AUTHENTICATION MECHANISM
========================================================================
  - Auth storage: localStorage['empcloud-auth'] contains accessToken (JWT)
  - Module launch: ?sso_token=<JWT> appended to module base URL
  - JWT payload includes: sub (userId), org_id, email, role (org_admin),
    first_name, last_name, org_name, scope, client_id, jti, iat, exp, iss
  - Token issuer: https://test-empcloud-api.empcloud.com
  - APIs called by /modules page: /api/v1/modules, /api/v1/subscriptions
  - APIs called by dashboard: /api/v1/modules, /api/v1/subscriptions,
    /api/v1/dashboard/widgets, /api/v1/billing/summary,
    /api/v1/organizations/me/stats, /api/v1/onboarding/status

========================================================================
F. CLICK TEST RESULTS SUMMARY
========================================================================
""")
        for r in results:
            status_icon = "OK" if r['status'] == 'OK' else r['status']
            sso_note = " (SSO consumed)" if r.get('sso_consumed') else " (SSO still in URL)" if r['status'] == 'OK' else ""
            print(f"  [{status_icon}] {r['module']} ({r['slug']})")
            print(f"       Target:  {r['target']}")
            if r['actual']:
                print(f"       Landed:  {r['actual']}")
                print(f"       Title:   {r['title']}")
                print(f"       New tab: {r['new_tab']}{sso_note}")

        # Save
        save_path = os.path.join(SCREENSHOTS, "discovery_results.json")
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump({
                'modules': modules_info,
                'module_url_map': {slug: {'name': name, 'url': url} for url, (slug, name) in MODULE_URL_MAP.items()},
                'click_results': results,
            }, f, indent=2, default=str)
        print(f"\n  Results saved to {save_path}")

    except Exception as e:
        print(f"\nFATAL: {e}")
        traceback.print_exc()
        ss(d, "99_error")
    finally:
        d.quit()
        print("\nDone.")

if __name__ == '__main__':
    main()
