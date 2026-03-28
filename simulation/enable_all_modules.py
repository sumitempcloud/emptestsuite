"""
Enable/Subscribe ALL modules for ALL 3 organizations in EmpCloud test environment.
Uses API to subscribe, then Selenium to verify dashboard shows all modules.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import time
import os

API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
DASHBOARD_URL = "https://test-empcloud.empcloud.com"

ORGS = [
    {"name": "TechNova", "email": "ananya@technova.in", "password": "Welcome@123"},
    {"name": "GlobalTech", "email": "john@globaltech.com", "password": "Welcome@123"},
    {"name": "Innovate", "email": "hr@innovate.io", "password": "Welcome@123"},
]

SCREENSHOT_DIR = r"C:\emptesting\simulation\screenshots"


def login(email, password):
    """Login via /auth/login and return Bearer headers."""
    r = requests.post(f"{API_BASE}/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        print(f"  [FAIL] Login failed for {email}: {r.status_code} {r.text[:200]}")
        return None
    data = r.json()
    if not data.get("success"):
        print(f"  [FAIL] Login unsuccessful for {email}: {r.text[:200]}")
        return None
    token = data["data"]["tokens"]["access_token"]
    print(f"  [OK] Logged in as {email}")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def process_org(org):
    """Subscribe all modules for one org via API."""
    print(f"\n{'='*60}")
    print(f"  ORGANIZATION: {org['name']}")
    print(f"{'='*60}")

    headers = login(org["email"], org["password"])
    if not headers:
        return {"org": org["name"], "status": "LOGIN_FAILED", "subscribed": [], "total": 0, "newly": []}

    # Get all available modules
    r = requests.get(f"{API_BASE}/modules", headers=headers, timeout=30)
    modules = r.json()["data"]
    print(f"  Available modules: {len(modules)}")

    # Get current subscriptions
    r = requests.get(f"{API_BASE}/subscriptions", headers=headers, timeout=30)
    subs = r.json()["data"]
    sub_mod_ids = {s["module_id"] for s in subs}
    print(f"  Already subscribed: {len(subs)}")

    # Subscribe any missing modules
    newly_subscribed = []
    for m in modules:
        if m["id"] in sub_mod_ids:
            print(f"    [SKIP] {m['name']} (id={m['id']}) -- already subscribed")
            continue
        payload = {
            "module_id": m["id"],
            "plan_tier": "basic",
            "total_seats": 50,
            "billing_cycle": "monthly",
        }
        r2 = requests.post(f"{API_BASE}/subscriptions", json=payload, headers=headers, timeout=30)
        if r2.status_code in [200, 201]:
            print(f"    [SUBSCRIBED] {m['name']} (id={m['id']})")
            newly_subscribed.append(m["name"])
        elif r2.status_code == 409 or "already" in r2.text.lower():
            print(f"    [ALREADY] {m['name']} (id={m['id']})")
        else:
            print(f"    [FAIL] {m['name']} (id={m['id']}): {r2.status_code} {r2.text[:200]}")

    # Final verification
    r = requests.get(f"{API_BASE}/subscriptions", headers=headers, timeout=30)
    final_subs = r.json()["data"]
    final_mod_ids = {s["module_id"] for s in final_subs}

    print(f"\n  --- Verification for {org['name']} ---")
    all_subscribed = []
    for m in modules:
        status = "SUBSCRIBED" if m["id"] in final_mod_ids else "MISSING"
        marker = "[OK]" if status == "SUBSCRIBED" else "[!!]"
        print(f"    {marker} {m['name']} (id={m['id']})")
        if status == "SUBSCRIBED":
            all_subscribed.append(m["name"])

    print(f"  Total: {len(all_subscribed)}/{len(modules)} modules subscribed")

    return {
        "org": org["name"],
        "status": "OK",
        "total": len(modules),
        "subscribed": all_subscribed,
        "newly": newly_subscribed,
    }


def selenium_verify():
    """Verify modules via headless Chrome for each org."""
    print(f"\n{'='*60}")
    print("  SELENIUM VERIFICATION")
    print(f"{'='*60}")

    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        print("  [SKIP] Selenium not installed")
        return

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts = Options()
    opts.binary_location = chrome_path
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")

    for org in ORGS:
        print(f"\n  --- Selenium: {org['name']} ({org['email']}) ---")
        driver = None
        try:
            driver = webdriver.Chrome(options=opts)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)

            # Login
            driver.get(f"{DASHBOARD_URL}/login")
            time.sleep(3)

            # Fill email
            try:
                email_field = driver.find_element(By.CSS_SELECTOR,
                    "input[type='email'], input[name='email'], input[placeholder*='email' i]")
            except Exception:
                inputs = driver.find_elements(By.TAG_NAME, "input")
                email_field = inputs[0] if inputs else None
            if email_field:
                email_field.clear()
                email_field.send_keys(org["email"])

            # Fill password
            try:
                pwd_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            except Exception:
                inputs = driver.find_elements(By.TAG_NAME, "input")
                pwd_field = inputs[1] if len(inputs) > 1 else None
            if pwd_field:
                pwd_field.clear()
                pwd_field.send_keys(org["password"])

            # Click submit
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                btn.click()
            except Exception:
                for b in driver.find_elements(By.TAG_NAME, "button"):
                    if any(kw in b.text.lower() for kw in ["login", "sign in", "submit"]):
                        b.click()
                        break

            time.sleep(5)

            # Check /modules page
            driver.get(f"{DASHBOARD_URL}/modules")
            time.sleep(5)
            driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"enable_{org['name']}_modules.png"))

            body_text = driver.find_element(By.TAG_NAME, "body").text
            subscribed_count = body_text.lower().count("subscribed")
            active_count = body_text.lower().count("active")
            print(f"    /modules page - 'subscribed' mentions: {subscribed_count}, 'active' mentions: {active_count}")

            # Check dashboard for Launch buttons
            driver.get(f"{DASHBOARD_URL}/dashboard")
            time.sleep(5)
            driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"enable_{org['name']}_dashboard.png"))

            launch_btns = driver.find_elements(By.XPATH,
                "//button[contains(text(),'Launch')] | //a[contains(text(),'Launch')]")
            print(f"    Dashboard Launch buttons: {len(launch_btns)}")

            your_modules = driver.find_elements(By.XPATH,
                "//*[contains(text(),'Your Modules') or contains(text(),'your modules')]")
            if your_modules:
                print(f"    'Your Modules' section: FOUND")

            # Print names of launch buttons or nearby text
            for i, btn in enumerate(launch_btns):
                try:
                    parent = btn.find_element(By.XPATH, "./..")
                    card_text = parent.text.split("\n")[0] if parent.text else f"Module {i+1}"
                    print(f"      Launch: {card_text}")
                except Exception:
                    pass

        except Exception as e:
            print(f"    [ERROR] {e}")
            if driver:
                try:
                    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"enable_{org['name']}_error.png"))
                except Exception:
                    pass
        finally:
            if driver:
                driver.quit()


def main():
    print("=" * 60)
    print("  ENABLE ALL MODULES FOR ALL ORGANIZATIONS")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Phase 1: API - subscribe all modules
    results = []
    for org in ORGS:
        result = process_org(org)
        results.append(result)

    # Summary
    print(f"\n\n{'='*60}")
    print("  API SUMMARY")
    print(f"{'='*60}")
    all_ok = True
    for r in results:
        ok = len(r["subscribed"]) == r["total"] and r["total"] > 0
        marker = "OK" if ok else "INCOMPLETE"
        if not ok:
            all_ok = False
        print(f"\n  {r['org']}: [{marker}]")
        print(f"    Subscribed: {len(r['subscribed'])}/{r['total']}")
        if r["newly"]:
            print(f"    Newly subscribed this run: {r['newly']}")
        for name in r["subscribed"]:
            print(f"      - {name}")

    if all_ok:
        print(f"\n  ALL 3 ORGANIZATIONS HAVE ALL MODULES SUBSCRIBED!")
    else:
        print(f"\n  WARNING: Some organizations are missing modules.")

    # Phase 2: Selenium verification
    selenium_verify()

    print(f"\n{'='*60}")
    print("  DONE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
