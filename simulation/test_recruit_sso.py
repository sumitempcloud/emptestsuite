"""
EMP Recruit Module - Comprehensive SSO Test
Tests: Dashboard, Jobs, Create Job, Candidates, Add Candidate,
       Interviews, Offers, Analytics, Settings, Pipeline Stages,
       Onboarding, Referrals, AI Scoring, Job Detail
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
import json
import os
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\module_recruit"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

BASE_URL = "https://test-recruit.empcloud.com"
AUTH_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
API_BASE = "https://test-recruit-api.empcloud.com"

bugs = []

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  [Screenshot] {path}")
    return path

def file_bug(title, body):
    """File a bug on GitHub."""
    bugs.append(title)
    print(f"  [BUG] {title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={
                "title": title,
                "body": body,
                "labels": ["bug", "recruit"]
            },
            timeout=15
        )
        if resp.status_code == 201:
            url = resp.json().get("html_url", "")
            print(f"    Filed: {url}")
        else:
            print(f"    GitHub returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"    Failed to file bug: {e}")

def get_sso_token():
    """Get SSO token from EMP Cloud auth."""
    print("[1] Getting SSO token...")
    resp = requests.post(AUTH_URL, json={
        "email": "ananya@technova.in",
        "password": "Welcome@123"
    }, timeout=15)
    if resp.status_code != 200:
        print(f"  Auth failed: {resp.status_code} {resp.text[:300]}")
        return None
    data = resp.json()
    token = (
        data.get("data", {}).get("tokens", {}).get("access_token")
        or data.get("data", {}).get("token")
        or data.get("token")
    )
    if not token:
        print(f"  No token in response: {json.dumps(data)[:300]}")
        return None
    print(f"  Token obtained (length={len(token)})")
    return token

def setup_driver():
    """Set up Chrome headless."""
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(20)
    driver.implicitly_wait(3)
    return driver

def wait_for_page(driver, timeout=10):
    """Wait for page to finish loading."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except:
        pass
    time.sleep(1.5)

def check_page_for_errors(driver, page_name):
    """Check for visible error messages on page."""
    for xpath in [
        "//*[contains(text(),'Something went wrong')]",
        "//*[contains(text(),'Internal Server Error')]",
        "//*[contains(text(),'Page Not Found')]",
    ]:
        try:
            elems = driver.find_elements(By.XPATH, xpath)
            for el in elems:
                if el.is_displayed() and el.text.strip():
                    return el.text.strip()
        except:
            pass
    return None

def get_page_title_text(driver):
    """Get visible heading text."""
    for sel in ["h1", "h2", "[class*='title']", "[class*='heading']"]:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed() and el.text.strip():
                return el.text.strip()
        except:
            pass
    return driver.title

def test_sso_login(driver, token):
    """Test SSO login to Recruit module."""
    print("\n[2] SSO Login to Recruit...")
    sso_url = f"{BASE_URL}?sso_token={token}"
    driver.get(sso_url)
    wait_for_page(driver, 15)
    time.sleep(2)

    screenshot(driver, "01_dashboard_sso")

    current = driver.current_url
    print(f"  Current URL: {current}")

    if "login" in current.lower() and "sso" not in current.lower():
        file_bug(
            "[Recruit] SSO login redirect fails - lands on login page",
            f"After SSO token login, user is redirected to login page instead of dashboard.\nURL: {current}"
        )
        return False

    heading = get_page_title_text(driver)
    print(f"  Page heading: {heading}")

    err = check_page_for_errors(driver, "Dashboard")
    if err:
        file_bug("[Recruit] Dashboard shows error after SSO login",
                 f"Error visible on dashboard after SSO: {err}")

    print("  SSO login completed.")
    return True

def test_jobs_page(driver):
    """Test /jobs page."""
    print("\n[3] Testing /jobs page...")
    driver.get(f"{BASE_URL}/jobs")
    wait_for_page(driver)
    screenshot(driver, "02_jobs_list")

    heading = get_page_title_text(driver)
    print(f"  Page heading: {heading}")

    err = check_page_for_errors(driver, "Jobs")
    if err:
        file_bug("[Recruit] Jobs list page shows error", f"Error on /jobs: {err}")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    print(f"  Body text length: {len(body_text)}")

def test_create_job(driver):
    """Test /jobs/new - create a job posting."""
    print("\n[4] Testing /jobs/new (Create Job)...")
    driver.get(f"{BASE_URL}/jobs/new")
    wait_for_page(driver)
    screenshot(driver, "03_jobs_new_form")

    heading = get_page_title_text(driver)
    print(f"  Page heading: {heading}")

    err = check_page_for_errors(driver, "New Job")
    if err:
        file_bug("[Recruit] Create Job page shows error", f"Error on /jobs/new: {err}")

    form_filled = False
    try:
        # Title field
        title_field = None
        for sel in ["input[name='title']", "input[placeholder*='itle']", "input[type='text']"]:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elems:
                    if el.is_displayed() and el.is_enabled():
                        title_field = el
                        break
                if title_field:
                    break
            except:
                pass

        if title_field:
            title_field.clear()
            title_field.send_keys("QA Test Engineer - Automated Test")
            print("  Filled title field")
            form_filled = True

        # Description
        for sel in ["textarea[name='description']", "textarea"]:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elems:
                    if el.is_displayed() and el.is_enabled():
                        el.clear()
                        el.send_keys("Automated test job posting for QA validation. Skills: Python, Selenium, API Testing.")
                        print("  Filled description field")
                        break
            except:
                pass

        # Dropdowns
        selects = driver.find_elements(By.TAG_NAME, "select")
        for s in selects:
            try:
                if s.is_displayed():
                    sel = Select(s)
                    if len(sel.options) > 1:
                        sel.select_by_index(1)
                        print(f"  Selected dropdown: {sel.options[1].text}")
            except:
                pass

        screenshot(driver, "04_jobs_new_filled")

        # Submit
        submit_btn = None
        for sel in ["button[type='submit']", "//button[contains(text(),'Create')]",
                     "//button[contains(text(),'Save')]", "//button[contains(text(),'Post')]"]:
            try:
                if sel.startswith("//"):
                    elems = driver.find_elements(By.XPATH, sel)
                else:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elems:
                    if el.is_displayed() and el.is_enabled():
                        submit_btn = el
                        break
                if submit_btn:
                    break
            except:
                pass

        if submit_btn:
            print(f"  Clicking submit: '{submit_btn.text}'")
            submit_btn.click()
            time.sleep(3)
            wait_for_page(driver)
            screenshot(driver, "05_jobs_new_submitted")
            current_url = driver.current_url
            print(f"  After submit URL: {current_url}")
            if "/jobs/new" not in current_url:
                print("  Job creation successful (redirected to job detail)")
            else:
                print("  Still on form - may need required fields")
        else:
            print("  No submit button found")

    except Exception as e:
        print(f"  Error: {e}")
        screenshot(driver, "05_jobs_new_error")

def test_candidates_page(driver):
    """Test /candidates page."""
    print("\n[5] Testing /candidates page...")
    driver.get(f"{BASE_URL}/candidates")
    wait_for_page(driver)
    screenshot(driver, "06_candidates_list")

    heading = get_page_title_text(driver)
    print(f"  Page heading: {heading}")

    err = check_page_for_errors(driver, "Candidates")
    if err:
        file_bug("[Recruit] Candidates page shows error", f"Error on /candidates: {err}")

def test_add_candidate(driver):
    """Try to add a candidate with thorough form filling."""
    print("\n[6] Testing Add Candidate...")
    driver.get(f"{BASE_URL}/candidates")
    wait_for_page(driver)

    # Click Add button or navigate directly
    add_btn = None
    for sel in ["//button[contains(text(),'Add')]", "//a[contains(text(),'Add')]"]:
        try:
            elems = driver.find_elements(By.XPATH, sel)
            for el in elems:
                if el.is_displayed():
                    add_btn = el
                    break
            if add_btn:
                break
        except:
            pass

    if add_btn:
        print(f"  Found add button: '{add_btn.text}'")
        add_btn.click()
        time.sleep(2)
        wait_for_page(driver)
    else:
        driver.get(f"{BASE_URL}/candidates/new")
        wait_for_page(driver)

    screenshot(driver, "07_add_candidate_form")

    try:
        # Fill all visible text inputs
        inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")
        print(f"  Found {len(inputs)} form fields")

        test_values = {
            "first": "Priya", "john": "Priya",
            "last": "Sharma", "doe": "Sharma",
            "email": "priya.sharma.autotest@example.com",
            "phone": "9876543210", "mobile": "9876543210",
            "company": "TestCorp", "acme": "TestCorp",
            "engineer": "QA Engineer", "position": "QA Engineer",
            "experience": "5", "years": "5",
            "linkedin": "https://linkedin.com/in/priyasharma",
            "portfolio": "https://priyasharma.dev",
            "react": "Python, Selenium, API Testing",
            "senior": "automation, testing, qa",
        }

        for inp in inputs:
            try:
                if not inp.is_displayed() or not inp.is_enabled():
                    continue
                tag = inp.tag_name
                if tag == "select":
                    s = Select(inp)
                    if len(s.options) > 1:
                        s.select_by_index(1)
                        print(f"  Selected dropdown: {s.options[1].text}")
                    continue
                itype = inp.get_attribute("type") or ""
                if itype in ("hidden", "file", "checkbox", "radio"):
                    continue
                placeholder = (inp.get_attribute("placeholder") or "").lower()
                name = (inp.get_attribute("name") or "").lower()

                val = None
                if itype == "email" or "email" in name:
                    val = "priya.sharma.autotest@example.com"
                elif itype == "tel" or "phone" in name or "phone" in placeholder:
                    val = "9876543210"
                elif itype == "number" or "experience" in name or "years" in placeholder:
                    val = "5"
                elif itype == "url" or "linkedin" in placeholder:
                    val = "https://linkedin.com/in/priya"
                elif tag == "textarea":
                    val = "Experienced QA engineer with automation skills in Python and Selenium."
                else:
                    # Match by placeholder keywords
                    for key, v in test_values.items():
                        if key in placeholder or key in name:
                            val = v
                            break
                    if not val:
                        val = "Test Value"

                inp.clear()
                inp.send_keys(val)
            except:
                pass

        screenshot(driver, "08_add_candidate_filled")

        # Submit
        submit_btn = None
        for sel in ["button[type='submit']", "//button[contains(text(),'Add')]",
                     "//button[contains(text(),'Save')]", "//button[contains(text(),'Create')]"]:
            try:
                if sel.startswith("//"):
                    elems = driver.find_elements(By.XPATH, sel)
                else:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elems:
                    if el.is_displayed() and el.is_enabled():
                        submit_btn = el
                        break
                if submit_btn:
                    break
            except:
                pass

        if submit_btn:
            print(f"  Clicking submit: '{submit_btn.text}'")
            submit_btn.click()
            time.sleep(3)
            wait_for_page(driver)
            screenshot(driver, "09_add_candidate_result")
            url = driver.current_url
            print(f"  After submit URL: {url}")

            # Check if redirected to candidate detail (success) or stayed (error)
            if "/candidates/new" not in url and "/candidates/" in url:
                print("  Candidate created successfully")
                body = driver.find_element(By.TAG_NAME, "body").text
                if len(body.strip()) < 30:
                    file_bug(
                        "[Recruit] Candidate detail page renders blank after successful creation",
                        f"After adding a candidate, redirected to {url} but page is blank.\n"
                        "Expected: Candidate profile should display."
                    )
            elif "/candidates/new" in url:
                # Check validation errors
                errors = driver.find_elements(By.CSS_SELECTOR, "[class*='error'], [role='alert']")
                visible = [e.text for e in errors if e.is_displayed() and e.text.strip()]
                if visible:
                    print(f"  Validation errors: {visible}")
                else:
                    file_bug(
                        "[Recruit] Add Candidate form stays on page without feedback",
                        f"Form submitted but stayed on /candidates/new with no visible error."
                    )

    except Exception as e:
        print(f"  Error: {e}")
        traceback.print_exc()

def test_interviews_page(driver):
    """Test /interviews page."""
    print("\n[7] Testing /interviews page...")
    driver.get(f"{BASE_URL}/interviews")
    wait_for_page(driver)
    screenshot(driver, "10_interviews")
    heading = get_page_title_text(driver)
    print(f"  Page heading: {heading}")
    err = check_page_for_errors(driver, "Interviews")
    if err:
        file_bug("[Recruit] Interviews page shows error", f"Error on /interviews: {err}")

def test_offers_page(driver):
    """Test /offers page."""
    print("\n[8] Testing /offers page...")
    driver.get(f"{BASE_URL}/offers")
    wait_for_page(driver)
    screenshot(driver, "11_offers")
    heading = get_page_title_text(driver)
    print(f"  Page heading: {heading}")
    err = check_page_for_errors(driver, "Offers")
    if err:
        file_bug("[Recruit] Offers page shows error", f"Error on /offers: {err}")

def test_analytics_page(driver):
    """Test /analytics page."""
    print("\n[9] Testing /analytics page...")
    driver.get(f"{BASE_URL}/analytics")
    wait_for_page(driver)
    screenshot(driver, "12_analytics")
    heading = get_page_title_text(driver)
    print(f"  Page heading: {heading}")
    err = check_page_for_errors(driver, "Analytics")
    if err:
        file_bug("[Recruit] Analytics page shows error", f"Error on /analytics: {err}")

def test_settings_page(driver):
    """Test /settings page."""
    print("\n[10] Testing /settings page...")
    driver.get(f"{BASE_URL}/settings")
    wait_for_page(driver)
    screenshot(driver, "13_settings")
    heading = get_page_title_text(driver)
    print(f"  Page heading: {heading}")
    err = check_page_for_errors(driver, "Settings")
    if err:
        file_bug("[Recruit] Settings page shows error", f"Error on /settings: {err}")

def test_remaining_pages(driver):
    """Test pipeline-config, onboarding, referrals, ai-scoring."""
    pages = [
        ("/pipeline-config", "14_pipeline_config", "Pipeline Config"),
        ("/onboarding", "15_onboarding", "Onboarding"),
        ("/referrals", "16_referrals", "Referrals"),
        ("/ai-scoring", "17_ai_scoring", "AI Scoring"),
    ]
    for route, ss_name, label in pages:
        print(f"\n[Extra] Testing {route}...")
        try:
            driver.get(f"{BASE_URL}{route}")
            wait_for_page(driver)
            screenshot(driver, ss_name)
            heading = get_page_title_text(driver)
            print(f"  Heading: {heading}")
            body = driver.find_element(By.TAG_NAME, "body").text
            print(f"  Content length: {len(body)}")
            if "Page Not Found" in heading or len(body.strip()) < 30:
                file_bug(f"[Recruit] {label} page returns Page Not Found",
                         f"Navigating to {route} shows 'Page Not Found'. "
                         f"README documents this route as a valid page.")
        except Exception as e:
            print(f"  Error: {e}")

def test_job_detail(driver):
    """Test clicking into a job detail to see pipeline/kanban board."""
    print("\n[Extra] Testing job detail page...")
    driver.get(f"{BASE_URL}/jobs")
    wait_for_page(driver)
    try:
        job_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/jobs/']")
        for jl in job_links:
            href = jl.get_attribute("href") or ""
            if "/jobs/" in href and "/new" not in href and jl.is_displayed():
                print(f"  Clicking job: {jl.text[:50]}")
                jl.click()
                time.sleep(2)
                wait_for_page(driver)
                screenshot(driver, "20_job_detail")
                print(f"  URL: {driver.current_url}")
                heading = get_page_title_text(driver)
                print(f"  Heading: {heading}")
                body = driver.find_element(By.TAG_NAME, "body").text
                has_pipeline = any(kw in body.lower() for kw in
                                   ["applied", "screened", "interview", "offer", "hired", "pipeline"])
                print(f"  Pipeline stages visible: {has_pipeline}")
                err = check_page_for_errors(driver, "Job Detail")
                if err:
                    file_bug("[Recruit] Job detail page shows error", f"Error: {err}")
                break
    except Exception as e:
        print(f"  Error: {e}")

def test_api_endpoints(token):
    """Test key API endpoints directly."""
    print("\n[API] Testing Recruit API endpoints...")

    # SSO exchange to get module-specific token
    try:
        sso_resp = requests.post(f"{API_BASE}/api/v1/auth/sso", json={"token": token}, timeout=10)
        print(f"  POST /api/v1/auth/sso -> {sso_resp.status_code}")
        recruit_token = None
        if sso_resp.status_code == 200:
            sso_data = sso_resp.json()
            recruit_token = sso_data.get("data", {}).get("token") or sso_data.get("token")
            if recruit_token:
                print(f"  Recruit session token obtained (length={len(recruit_token)})")
    except Exception as e:
        print(f"  SSO exchange error: {e}")
        recruit_token = None

    # Test with both tokens
    for label, tok in [("EmpCloud Token", token), ("Recruit Token", recruit_token)]:
        if not tok:
            continue
        print(f"\n  --- {label} ---")
        headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
        for path in ["/api/v1/jobs", "/api/v1/candidates", "/api/v1/interviews",
                     "/api/v1/offers", "/api/v1/analytics/overview", "/api/v1/pipeline-stages"]:
            try:
                resp = requests.get(f"{API_BASE}{path}", headers=headers, timeout=10)
                print(f"  GET {path} -> {resp.status_code}")
                if resp.status_code >= 500:
                    file_bug(f"[Recruit] API {path} returns {resp.status_code} server error",
                             f"GET {API_BASE}{path} returned {resp.status_code}.\n{resp.text[:300]}")
            except Exception as e:
                print(f"  GET {path} -> Error: {e}")


def main():
    print("=" * 70)
    print("EMP RECRUIT MODULE - COMPREHENSIVE SSO TEST")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Step 1: Get SSO token
    token = get_sso_token()
    if not token:
        print("FATAL: Could not get SSO token. Aborting.")
        return

    # Step 2: Test API endpoints
    test_api_endpoints(token)

    # Step 3: Browser tests
    driver = None
    try:
        driver = setup_driver()
        print("\n  Chrome driver initialized.")

        # SSO Login
        ok = test_sso_login(driver, token)
        if not ok:
            print("  SSO login failed but continuing...")

        # Test all pages
        test_jobs_page(driver)
        test_create_job(driver)
        test_candidates_page(driver)
        test_add_candidate(driver)
        test_interviews_page(driver)
        test_offers_page(driver)
        test_analytics_page(driver)
        test_settings_page(driver)
        test_remaining_pages(driver)
        test_job_detail(driver)

    except Exception as e:
        print(f"\nFATAL browser error: {e}")
        traceback.print_exc()
        if driver:
            screenshot(driver, "fatal_error")
    finally:
        if driver:
            driver.quit()
            print("\n  Browser closed.")

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Bugs filed: {len(bugs)}")
    for i, b in enumerate(bugs, 1):
        print(f"  {i}. {b}")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}")
    print("Done.")


if __name__ == "__main__":
    main()
