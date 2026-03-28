"""
Comprehensive SSO Module Testing for EmpCloud
Tests: Payroll, Recruit, Performance, Rewards, Exit, LMS
Method: Login via API -> use access_token as ?sso_token= parameter
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ──
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
CREDENTIALS = {"email": "ananya@technova.in", "password": "Welcome@123"}
SCREENSHOT_DIR = "C:/emptesting/simulation/screenshots/sso_modules"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"

MODULES = {
    "payroll": {
        "base_url": "https://testpayroll.empcloud.com",
        "pages": {
            "dashboard": "/",
            "payslips": "/my",
            "salary": "/salary",
            "tax": "/tax",
            "run_payroll": "/admin/payroll",
            "admin_employees": "/admin/employees",
        }
    },
    "recruit": {
        "base_url": "https://test-recruit.empcloud.com",
        "pages": {
            "dashboard": "/",
            "jobs": "/jobs",
            "candidates": "/candidates",
            "interviews": "/interviews",
            "offers": "/offers",
            "analytics": "/analytics",
        }
    },
    "performance": {
        "base_url": "https://test-performance.empcloud.com",
        "pages": {
            "dashboard": "/",
            "review_cycles": "/review-cycles",
            "goals": "/goals",
            "analytics": "/analytics",
            "nine_box": "/nine-box",
        }
    },
    "rewards": {
        "base_url": "https://test-rewards.empcloud.com",
        "pages": {
            "dashboard": "/",
            "kudos": "/kudos",
            "badges": "/badges",
            "leaderboard": "/leaderboard",
            "challenges": "/challenges",
        }
    },
    "exit": {
        "base_url": "https://test-exit.empcloud.com",
        "pages": {
            "dashboard": "/",
            "exits": "/exits",
            "clearance": "/clearance",
            "fnf": "/fnf",
            "analytics": "/analytics",
        }
    },
    "lms": {
        "base_url": "https://testlms.empcloud.com",
        "pages": {
            "dashboard": "/",
            "courses": "/courses",
            "my_learning": "/my-learning",
            "certifications": "/certifications",
        }
    },
}

# Batch modules: restart driver every 2 modules
MODULE_BATCHES = [
    ["payroll", "recruit"],
    ["performance", "rewards"],
    ["exit", "lms"],
]

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── Results tracking ──
results = []
bugs = []


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def get_access_token():
    """Login via API and return access_token."""
    log("Authenticating via API...")
    try:
        resp = requests.post(
            f"{API_BASE}/auth/login",
            json=CREDENTIALS,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        log(f"  Auth response status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            # Try multiple paths to find the token
            token = (
                data.get("access_token")
                or data.get("token")
                or data.get("data", {}).get("access_token")
                or data.get("data", {}).get("token")
            )
            # Check nested tokens object: data.tokens.access_token
            if not token and "data" in data and isinstance(data["data"], dict):
                tokens_obj = data["data"].get("tokens", {})
                if isinstance(tokens_obj, dict):
                    token = tokens_obj.get("access_token") or tokens_obj.get("token") or tokens_obj.get("accessToken")
                    if not token:
                        # Try any key with 'token' in name
                        for k, v in tokens_obj.items():
                            if "token" in k.lower() and isinstance(v, str) and len(v) > 20:
                                token = v
                                break
            if token:
                log(f"  Got access_token ({len(token)} chars)")
                return token
            log(f"  Could not find token in response: {json.dumps(data)[:500]}")
            return None
        else:
            log(f"  Auth failed: {resp.text[:300]}")
            return None
    except Exception as e:
        log(f"  Auth error: {e}")
        return None


def create_driver():
    """Create a new Chrome WebDriver instance."""
    opts = Options()
    opts.binary_location = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(45)
    driver.implicitly_wait(5)
    return driver


def check_page_state(driver):
    """Analyze the current page state - check for errors, auth issues, content."""
    state = {
        "url": driver.current_url,
        "title": driver.title,
        "authenticated": False,
        "has_content": False,
        "error": None,
        "body_text_preview": "",
    }

    try:
        body = driver.find_element(By.TAG_NAME, "body").text[:1500]
        state["body_text_preview"] = body[:300]
    except:
        body = ""

    body_lower = body.lower() if body else ""

    # Check for login/auth pages (means SSO failed)
    login_indicators = ["sign in", "log in", "login", "enter your email", "enter your password", "forgot password"]
    if any(ind in body_lower for ind in login_indicators) and "welcome" not in body_lower[:100]:
        # Could be a login page redirect
        if "login" in driver.current_url.lower() or "auth" in driver.current_url.lower():
            state["error"] = "Redirected to login page - SSO authentication failed"
        elif any(ind in body_lower[:200] for ind in login_indicators):
            state["error"] = "Appears to be login page - SSO may not have worked"

    # Check for explicit errors
    error_indicators = ["404", "not found", "500", "internal server error", "502 bad gateway",
                        "503 service unavailable", "something went wrong", "error occurred",
                        "page not found", "access denied", "forbidden", "unauthorized"]
    for err in error_indicators:
        if err in body_lower:
            state["error"] = f"Page contains error indicator: '{err}'"
            break

    # Check for blank/empty page
    if len(body.strip()) < 10:
        state["error"] = "Page appears blank/empty"

    # Check if authenticated (look for user indicators)
    auth_indicators = ["ananya", "technova", "dashboard", "admin", "logout", "profile",
                       "settings", "employee", "menu", "navigation", "sidebar"]
    state["authenticated"] = any(ind in body_lower for ind in auth_indicators)

    # Check for meaningful content
    state["has_content"] = len(body.strip()) > 50 and not state.get("error")

    return state


def take_screenshot(driver, module_name, page_name):
    """Take a screenshot and return the file path."""
    filename = f"{module_name}_{page_name}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    try:
        driver.save_screenshot(filepath)
        log(f"    Screenshot saved: {filename}")
        return filepath
    except Exception as e:
        log(f"    Screenshot failed: {e}")
        return None


def navigate_sso(driver, base_url, token):
    """Navigate to module with SSO token and wait for auth."""
    sso_url = f"{base_url}?sso_token={token}"
    log(f"  SSO navigate: {base_url}")
    try:
        driver.get(sso_url)
        time.sleep(4)  # Wait for SSO redirect/auth to complete

        # Wait for page to stabilize
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass
        time.sleep(2)
        return True
    except Exception as e:
        log(f"  Navigation error: {e}")
        return False


def navigate_page(driver, base_url, path, token):
    """Navigate to a specific page within a module."""
    if path == "/":
        url = f"{base_url}?sso_token={token}"
    else:
        url = f"{base_url}{path}"

    log(f"  Navigating to: {base_url}{path}")
    try:
        driver.get(url)
        time.sleep(3)
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass
        time.sleep(2)
        return True
    except Exception as e:
        log(f"  Page load error: {e}")
        return False


def file_bug(module, page, issue, screenshot_path=None):
    """File a GitHub issue for a discovered bug."""
    title = f"[{module.capitalize()} SSO] {issue[:80]}"
    body = f"""## Bug Report

**Module:** {module.capitalize()}
**Page:** {page}
**Issue:** {issue}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Test:** SSO Token Authentication Test

### Steps to Reproduce
1. Login via API to get access_token
2. Navigate to module URL with ?sso_token= parameter
3. Navigate to the specific page

### Expected
Page loads with authenticated content.

### Actual
{issue}
"""
    if screenshot_path:
        body += f"\n### Screenshot\nScreenshot saved: {os.path.basename(screenshot_path)}\n"

    bugs.append({
        "title": title,
        "body": body,
        "module": module,
        "page": page,
        "screenshot": screenshot_path,
    })
    return title


def create_github_issues():
    """Create GitHub issues for all discovered bugs."""
    if not bugs:
        log("No bugs to file.")
        return

    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Get existing issues to avoid duplicates
    existing_titles = set()
    try:
        page_num = 1
        while True:
            resp = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                headers=headers,
                params={"state": "all", "per_page": 100, "page": page_num},
                timeout=15,
            )
            if resp.status_code == 200:
                issues = resp.json()
                if not issues:
                    break
                for iss in issues:
                    existing_titles.add(iss["title"].strip().lower())
                page_num += 1
                if page_num > 5:
                    break
            else:
                break
    except Exception as e:
        log(f"Warning: could not fetch existing issues: {e}")

    created = 0
    skipped = 0
    for bug in bugs:
        if bug["title"].strip().lower() in existing_titles:
            log(f"  Skipping duplicate: {bug['title']}")
            skipped += 1
            continue

        try:
            resp = requests.post(
                f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                headers=headers,
                json={"title": bug["title"], "body": bug["body"], "labels": ["bug", "sso-testing"]},
                timeout=15,
            )
            if resp.status_code == 201:
                issue_url = resp.json().get("html_url", "")
                log(f"  Filed: {bug['title']} -> {issue_url}")
                created += 1
            else:
                log(f"  Failed to file: {bug['title']} ({resp.status_code}: {resp.text[:200]})")
        except Exception as e:
            log(f"  Error filing bug: {e}")

    log(f"GitHub Issues: {created} created, {skipped} skipped (duplicate)")


def upload_screenshots_to_github():
    """Upload all screenshots to the GitHub repo."""
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }

    import base64
    screenshots = [f for f in os.listdir(SCREENSHOT_DIR) if f.endswith(".png")]
    uploaded = 0

    for fname in screenshots:
        fpath = os.path.join(SCREENSHOT_DIR, fname)
        try:
            with open(fpath, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")

            gh_path = f"testing/screenshots/sso_modules/{fname}"

            # Check if file exists
            sha = None
            resp = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/contents/{gh_path}",
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                sha = resp.json().get("sha")

            payload = {
                "message": f"Upload SSO test screenshot: {fname}",
                "content": content,
                "branch": "main",
            }
            if sha:
                payload["sha"] = sha

            resp = requests.put(
                f"https://api.github.com/repos/{GITHUB_REPO}/contents/{gh_path}",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if resp.status_code in (200, 201):
                uploaded += 1
            else:
                log(f"  Upload failed for {fname}: {resp.status_code}")
        except Exception as e:
            log(f"  Upload error for {fname}: {e}")

    log(f"Uploaded {uploaded}/{len(screenshots)} screenshots to GitHub")


def test_module(driver, module_name, module_config, token):
    """Test all pages within a module."""
    base_url = module_config["base_url"]
    pages = module_config["pages"]
    module_results = []

    log(f"\n{'='*60}")
    log(f"TESTING MODULE: {module_name.upper()}")
    log(f"Base URL: {base_url}")
    log(f"{'='*60}")

    # First, do SSO auth on the dashboard
    first_page = True
    for page_name, path in pages.items():
        log(f"\n  --- Page: {page_name} ({path}) ---")

        if first_page:
            success = navigate_sso(driver, base_url, token)
            first_page = False
        else:
            success = navigate_page(driver, base_url, path, token)

        if not success:
            result = {
                "module": module_name,
                "page": page_name,
                "path": path,
                "status": "NAVIGATION_FAILED",
                "error": "Could not load page",
                "screenshot": None,
            }
            module_results.append(result)
            file_bug(module_name, page_name, f"Page failed to load: {base_url}{path}")
            continue

        # Check page state
        state = check_page_state(driver)
        log(f"    URL: {state['url']}")
        log(f"    Title: {state['title']}")
        log(f"    Authenticated: {state['authenticated']}")
        log(f"    Has Content: {state['has_content']}")
        if state["error"]:
            log(f"    ERROR: {state['error']}")
        if state["body_text_preview"]:
            preview = state["body_text_preview"][:150].replace("\n", " ")
            log(f"    Preview: {preview}")

        # Take screenshot
        ss_path = take_screenshot(driver, module_name, page_name)

        # Determine status
        if state["error"]:
            status = "ERROR"
            file_bug(module_name, page_name, state["error"], ss_path)
        elif not state["authenticated"]:
            status = "AUTH_ISSUE"
            file_bug(module_name, page_name, f"SSO authentication not confirmed on {path}", ss_path)
        elif state["has_content"]:
            status = "OK"
        else:
            status = "PARTIAL"

        result = {
            "module": module_name,
            "page": page_name,
            "path": path,
            "status": status,
            "url": state["url"],
            "title": state["title"],
            "authenticated": state["authenticated"],
            "has_content": state["has_content"],
            "error": state["error"],
            "screenshot": ss_path,
        }
        module_results.append(result)

    return module_results


def main():
    log("=" * 60)
    log("EmpCloud SSO Module Testing")
    log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    # Step 1: Get access token
    token = get_access_token()
    if not token:
        log("FATAL: Could not get access token. Aborting.")
        return

    all_results = []

    # Step 2: Test modules in batches (restart driver every 2 modules)
    for batch_idx, batch in enumerate(MODULE_BATCHES):
        log(f"\n{'#'*60}")
        log(f"BATCH {batch_idx + 1}: {', '.join(b.upper() for b in batch)}")
        log(f"{'#'*60}")

        driver = create_driver()
        try:
            for module_name in batch:
                if module_name not in MODULES:
                    log(f"  Unknown module: {module_name}, skipping")
                    continue

                module_results = test_module(driver, module_name, MODULES[module_name], token)
                all_results.extend(module_results)

                # Re-authenticate token between modules in same batch
                # (token is still valid, just need fresh SSO for next module)
        except Exception as e:
            log(f"  Batch error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                driver.quit()
                log(f"  Driver closed for batch {batch_idx + 1}")
            except:
                pass

        # Small pause between batches
        time.sleep(2)

    # Step 3: Summary
    log(f"\n{'='*60}")
    log("TEST SUMMARY")
    log(f"{'='*60}")

    ok_count = sum(1 for r in all_results if r["status"] == "OK")
    error_count = sum(1 for r in all_results if r["status"] == "ERROR")
    auth_count = sum(1 for r in all_results if r["status"] == "AUTH_ISSUE")
    partial_count = sum(1 for r in all_results if r["status"] == "PARTIAL")
    nav_fail_count = sum(1 for r in all_results if r["status"] == "NAVIGATION_FAILED")

    log(f"Total pages tested: {len(all_results)}")
    log(f"  OK:                {ok_count}")
    log(f"  PARTIAL:           {partial_count}")
    log(f"  ERROR:             {error_count}")
    log(f"  AUTH_ISSUE:        {auth_count}")
    log(f"  NAVIGATION_FAILED: {nav_fail_count}")
    log(f"  Bugs to file:      {len(bugs)}")

    # Per-module breakdown
    for mod_name in MODULES:
        mod_results = [r for r in all_results if r["module"] == mod_name]
        if mod_results:
            statuses = [r["status"] for r in mod_results]
            log(f"\n  {mod_name.upper()}:")
            for r in mod_results:
                icon = "OK" if r["status"] == "OK" else "!!" if r["status"] == "ERROR" else "??"
                log(f"    [{icon}] {r['page']:20s} -> {r['status']} {r.get('error', '') or ''}")

    # Step 4: Save results JSON
    results_path = "C:/emptesting/simulation/sso_test_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_pages": len(all_results),
            "ok": ok_count,
            "errors": error_count,
            "auth_issues": auth_count,
            "results": all_results,
            "bugs": [{"title": b["title"], "module": b["module"], "page": b["page"]} for b in bugs],
        }, f, indent=2, default=str)
    log(f"\nResults saved to: {results_path}")

    # Step 5: File bugs on GitHub
    log(f"\n{'='*60}")
    log("FILING GITHUB ISSUES")
    log(f"{'='*60}")
    create_github_issues()

    # Step 6: Upload screenshots
    log(f"\n{'='*60}")
    log("UPLOADING SCREENSHOTS TO GITHUB")
    log(f"{'='*60}")
    upload_screenshots_to_github()

    log(f"\nDone at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
