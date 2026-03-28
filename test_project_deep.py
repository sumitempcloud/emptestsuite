"""
Deep test of EmpCloud PROJECT MANAGEMENT module (emp-project) via SSO.
Tests: SSO login, Dashboard, Projects CRUD, Tasks CRUD, Kanban, Gantt,
       Time Tracking, Timesheets, Reports, Settings, and direct API endpoints.
"""
import sys, os, time, json, traceback, datetime, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ---------- Config ----------
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SSO_LOGIN_URL = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
PROJECT_FRONTEND = "https://test-project.empcloud.com"
PROJECT_API = "https://test-project-api.empcloud.com"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = r"C:\emptesting\screenshots\project"
RESULTS_FILE = r"C:\emptesting\test_project_deep_results.json"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

results = {
    "module": "emp-project",
    "timestamp": datetime.datetime.now().isoformat(),
    "sso_login": None,
    "frontend_status": None,
    "api_tests": {},
    "ui_tests": {},
    "bugs": [],
    "screenshots": []
}
bug_list = []
screenshot_idx = 0

def screenshot(driver, name):
    global screenshot_idx
    screenshot_idx += 1
    fname = f"{screenshot_idx:02d}_{name}.png"
    path = os.path.join(SCREENSHOT_DIR, fname)
    driver.save_screenshot(path)
    results["screenshots"].append(fname)
    print(f"  [Screenshot] {fname}")
    return path

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def file_bug(title, body, labels=None):
    """File a GitHub issue with [Projects] prefix."""
    if labels is None:
        labels = ["bug", "emp-project"]
    full_title = f"[Projects] {title}"
    bug_list.append({"title": full_title, "body": body})
    log(f"  BUG: {full_title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={"title": full_title, "body": body, "labels": labels},
            timeout=15
        )
        if resp.status_code == 201:
            url = resp.json().get("html_url", "")
            log(f"  Filed: {url}")
            return url
        else:
            log(f"  GitHub issue creation failed: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log(f"  GitHub issue creation error: {e}")
    return None

# ==================== PHASE 1: SSO Login ====================
def do_sso_login():
    log("=== PHASE 1: SSO Login ===")
    try:
        resp = requests.post(SSO_LOGIN_URL, json={
            "email": EMAIL, "password": PASSWORD
        }, timeout=15)
        log(f"  Login response: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            token = (data.get("data", {}).get("tokens", {}).get("access_token")
                     or data.get("data", {}).get("token")
                     or data.get("token"))
            if not token:
                # try nested
                for key in data:
                    if isinstance(data[key], dict):
                        if "token" in data[key]:
                            token = data[key]["token"]
                            break
                        if "access_token" in data[key]:
                            token = data[key]["access_token"]
                            break
            if token:
                log(f"  Token obtained: {token[:30]}...")
                results["sso_login"] = "SUCCESS"
                return token
            else:
                log(f"  No token in response: {json.dumps(data)[:300]}")
                results["sso_login"] = "FAIL - no token"
        else:
            log(f"  Login failed: {resp.text[:300]}")
            results["sso_login"] = f"FAIL - HTTP {resp.status_code}"
    except Exception as e:
        log(f"  Login error: {e}")
        results["sso_login"] = f"ERROR - {e}"
    return None

# ==================== PHASE 2: API Tests ====================
def test_api(token):
    log("=== PHASE 2: Direct API Tests ===")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    endpoints = {
        "health": {"method": "GET", "url": f"{PROJECT_API}/health", "auth": False},
        "health_v1": {"method": "GET", "url": f"{PROJECT_API}/v1/health", "auth": False},
        "projects_list": {"method": "GET", "url": f"{PROJECT_API}/v1/projects", "auth": True},
        "tasks_list": {"method": "GET", "url": f"{PROJECT_API}/v1/tasks", "auth": True},
        "time_entries": {"method": "GET", "url": f"{PROJECT_API}/v1/time-entries", "auth": True},
        "users": {"method": "GET", "url": f"{PROJECT_API}/v1/users", "auth": True},
        "reports": {"method": "GET", "url": f"{PROJECT_API}/v1/reports", "auth": True},
    }

    for name, cfg in endpoints.items():
        try:
            h = headers if cfg["auth"] else {"Content-Type": "application/json"}
            resp = requests.request(cfg["method"], cfg["url"], headers=h, timeout=15)
            status = resp.status_code
            body_preview = resp.text[:300]
            results["api_tests"][name] = {
                "status": status,
                "preview": body_preview
            }
            log(f"  {name}: HTTP {status} - {body_preview[:100]}")
            if status == 502:
                file_bug(
                    f"API endpoint {cfg['url']} returns 502 Bad Gateway",
                    f"**Endpoint:** `{cfg['method']} {cfg['url']}`\n**Status:** 502 Bad Gateway\n\n"
                    f"The project API is returning 502, indicating the backend service may be down.\n\n"
                    f"**Response:**\n```\n{body_preview}\n```"
                )
            elif status >= 500:
                file_bug(
                    f"API endpoint {cfg['url']} returns {status} server error",
                    f"**Endpoint:** `{cfg['method']} {cfg['url']}`\n**Status:** {status}\n\n"
                    f"**Response:**\n```\n{body_preview}\n```"
                )
        except requests.exceptions.ConnectionError as e:
            results["api_tests"][name] = {"status": "CONNECTION_ERROR", "error": str(e)[:200]}
            log(f"  {name}: CONNECTION ERROR - {str(e)[:100]}")
        except Exception as e:
            results["api_tests"][name] = {"status": "ERROR", "error": str(e)[:200]}
            log(f"  {name}: ERROR - {e}")

    # Try to create a project via API
    log("  --- Create project via API ---")
    try:
        create_payload = {
            "name": f"AutoTest Project {datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "description": "Created by automated deep test",
            "status": "active",
            "startDate": datetime.datetime.now().isoformat(),
            "endDate": (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
        }
        resp = requests.post(f"{PROJECT_API}/v1/projects", headers=headers,
                             json=create_payload, timeout=15)
        results["api_tests"]["create_project"] = {
            "status": resp.status_code,
            "preview": resp.text[:300]
        }
        log(f"  create_project: HTTP {resp.status_code} - {resp.text[:150]}")
        if resp.status_code in (200, 201):
            project_data = resp.json()
            project_id = project_data.get("data", {}).get("_id") or project_data.get("data", {}).get("id") or project_data.get("_id")
            if project_id:
                log(f"  Created project ID: {project_id}")
                # Try to create a task in this project
                task_payload = {
                    "title": f"AutoTest Task {datetime.datetime.now().strftime('%H%M%S')}",
                    "description": "Automated test task",
                    "projectId": project_id,
                    "status": "todo",
                    "priority": "medium"
                }
                tresp = requests.post(f"{PROJECT_API}/v1/tasks", headers=headers,
                                      json=task_payload, timeout=15)
                results["api_tests"]["create_task"] = {
                    "status": tresp.status_code,
                    "preview": tresp.text[:300]
                }
                log(f"  create_task: HTTP {tresp.status_code} - {tresp.text[:150]}")

                # Try to log time
                time_payload = {
                    "projectId": project_id,
                    "hours": 2,
                    "description": "Automated test time entry",
                    "date": datetime.datetime.now().strftime("%Y-%m-%d")
                }
                tresp2 = requests.post(f"{PROJECT_API}/v1/time-entries", headers=headers,
                                       json=time_payload, timeout=15)
                results["api_tests"]["create_time_entry"] = {
                    "status": tresp2.status_code,
                    "preview": tresp2.text[:300]
                }
                log(f"  create_time_entry: HTTP {tresp2.status_code} - {tresp2.text[:150]}")
    except Exception as e:
        results["api_tests"]["create_project"] = {"status": "ERROR", "error": str(e)[:200]}
        log(f"  create_project ERROR: {e}")

    return results["api_tests"]

# ==================== PHASE 3: UI Tests ====================
def test_ui(token):
    log("=== PHASE 3: UI Tests via Selenium ===")
    opts = Options()
    opts.binary_location = CHROME
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 15)

    try:
        # --- 3a: SSO Load ---
        log("  [3a] Loading project frontend via SSO...")
        sso_url = f"{PROJECT_FRONTEND}?sso_token={token}"
        try:
            driver.get(sso_url)
        except Exception as e:
            log(f"  Page load exception (may be timeout): {e}")
        time.sleep(5)
        screenshot(driver, "sso_landing")

        page_title = driver.title
        page_source_len = len(driver.page_source)
        current_url = driver.current_url
        log(f"  Title: {page_title} | URL: {current_url} | Source len: {page_source_len}")

        # Check for 502 / error pages
        body_text = ""
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text[:2000]
        except:
            pass

        is_502 = "502" in body_text or "Bad Gateway" in body_text
        is_error = "error" in body_text.lower()[:200] or "not found" in body_text.lower()[:200]

        if is_502:
            results["frontend_status"] = "502 - DOWN"
            log("  RESULT: Frontend returns 502 Bad Gateway - STILL DOWN")
            file_bug(
                "Project module frontend returns 502 Bad Gateway",
                f"**URL:** `{PROJECT_FRONTEND}`\n**SSO URL:** `{sso_url[:80]}...`\n\n"
                f"The project management module frontend is returning a 502 Bad Gateway error.\n"
                f"This indicates the backend/upstream service is not running or not reachable.\n\n"
                f"**Page title:** {page_title}\n"
                f"**Body text (first 500 chars):**\n```\n{body_text[:500]}\n```\n\n"
                f"**Impact:** Users cannot access project management features at all.\n"
                f"**Severity:** Critical - entire module is inaccessible."
            )
            screenshot(driver, "502_error")
        elif page_source_len < 500 and not body_text.strip():
            results["frontend_status"] = "BLANK PAGE"
            log("  RESULT: Frontend loads but page is blank/empty")
            file_bug(
                "Project module frontend loads blank page",
                f"**URL:** `{PROJECT_FRONTEND}`\n\n"
                f"The project module loads but shows a blank page with minimal content.\n"
                f"Page source length: {page_source_len} chars.\n"
                f"**Page title:** {page_title}"
            )
        else:
            results["frontend_status"] = "LOADED"
            log(f"  RESULT: Frontend loaded. Body preview: {body_text[:200]}")

        # --- 3b: Dashboard ---
        log("  [3b] Testing Dashboard...")
        try:
            driver.get(f"{PROJECT_FRONTEND}/dashboard?sso_token={token}")
            time.sleep(4)
            screenshot(driver, "dashboard")
            dash_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
            results["ui_tests"]["dashboard"] = {
                "status": "LOADED" if len(dash_text) > 50 else "MINIMAL",
                "preview": dash_text[:300]
            }
            log(f"  Dashboard: {dash_text[:150]}")
        except Exception as e:
            results["ui_tests"]["dashboard"] = {"status": "ERROR", "error": str(e)[:200]}
            log(f"  Dashboard error: {e}")
            screenshot(driver, "dashboard_error")

        # --- 3c: Projects List ---
        log("  [3c] Testing Projects List...")
        for projects_path in ["/projects", "/project", "/project/list"]:
            try:
                driver.get(f"{PROJECT_FRONTEND}{projects_path}?sso_token={token}")
                time.sleep(4)
                proj_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
                if len(proj_text) > 50:
                    screenshot(driver, f"projects_list_{projects_path.replace('/', '_')}")
                    results["ui_tests"]["projects_list"] = {
                        "status": "LOADED",
                        "path": projects_path,
                        "preview": proj_text[:300]
                    }
                    log(f"  Projects list at {projects_path}: {proj_text[:150]}")
                    break
            except Exception as e:
                log(f"  Projects {projects_path}: {e}")
        else:
            results["ui_tests"]["projects_list"] = {"status": "NOT_FOUND"}
            screenshot(driver, "projects_list_notfound")

        # --- 3d: Tasks ---
        log("  [3d] Testing Tasks...")
        for tasks_path in ["/tasks", "/task", "/task/list"]:
            try:
                driver.get(f"{PROJECT_FRONTEND}{tasks_path}?sso_token={token}")
                time.sleep(4)
                task_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
                if len(task_text) > 50:
                    screenshot(driver, f"tasks_{tasks_path.replace('/', '_')}")
                    results["ui_tests"]["tasks"] = {
                        "status": "LOADED",
                        "path": tasks_path,
                        "preview": task_text[:300]
                    }
                    log(f"  Tasks at {tasks_path}: {task_text[:150]}")
                    break
            except Exception as e:
                log(f"  Tasks {tasks_path}: {e}")
        else:
            results["ui_tests"]["tasks"] = {"status": "NOT_FOUND"}
            screenshot(driver, "tasks_notfound")

        # --- 3e: Kanban Board ---
        log("  [3e] Testing Kanban Board...")
        for kanban_path in ["/kanban", "/board", "/tasks/kanban", "/task/board"]:
            try:
                driver.get(f"{PROJECT_FRONTEND}{kanban_path}?sso_token={token}")
                time.sleep(4)
                kb_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
                if len(kb_text) > 50:
                    screenshot(driver, f"kanban_{kanban_path.replace('/', '_')}")
                    results["ui_tests"]["kanban"] = {
                        "status": "LOADED",
                        "path": kanban_path,
                        "preview": kb_text[:300]
                    }
                    log(f"  Kanban at {kanban_path}: {kb_text[:150]}")
                    break
            except Exception as e:
                log(f"  Kanban {kanban_path}: {e}")
        else:
            results["ui_tests"]["kanban"] = {"status": "NOT_FOUND"}
            screenshot(driver, "kanban_notfound")

        # --- 3f: Gantt Chart ---
        log("  [3f] Testing Gantt Chart...")
        for gantt_path in ["/gantt", "/gantt-chart", "/tasks/gantt", "/project/gantt"]:
            try:
                driver.get(f"{PROJECT_FRONTEND}{gantt_path}?sso_token={token}")
                time.sleep(4)
                g_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
                if len(g_text) > 50:
                    screenshot(driver, f"gantt_{gantt_path.replace('/', '_')}")
                    results["ui_tests"]["gantt"] = {
                        "status": "LOADED",
                        "path": gantt_path,
                        "preview": g_text[:300]
                    }
                    log(f"  Gantt at {gantt_path}: {g_text[:150]}")
                    break
            except Exception as e:
                log(f"  Gantt {gantt_path}: {e}")
        else:
            results["ui_tests"]["gantt"] = {"status": "NOT_FOUND"}
            screenshot(driver, "gantt_notfound")

        # --- 3g: Time Tracking ---
        log("  [3g] Testing Time Tracking...")
        for tt_path in ["/time-tracking", "/timetracking", "/time-entries", "/timelog"]:
            try:
                driver.get(f"{PROJECT_FRONTEND}{tt_path}?sso_token={token}")
                time.sleep(4)
                tt_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
                if len(tt_text) > 50:
                    screenshot(driver, f"timetracking_{tt_path.replace('/', '_')}")
                    results["ui_tests"]["time_tracking"] = {
                        "status": "LOADED",
                        "path": tt_path,
                        "preview": tt_text[:300]
                    }
                    log(f"  Time tracking at {tt_path}: {tt_text[:150]}")
                    break
            except Exception as e:
                log(f"  Time tracking {tt_path}: {e}")
        else:
            results["ui_tests"]["time_tracking"] = {"status": "NOT_FOUND"}
            screenshot(driver, "timetracking_notfound")

        # --- 3h: Timesheets ---
        log("  [3h] Testing Timesheets...")
        for ts_path in ["/timesheets", "/timesheet", "/time-sheet"]:
            try:
                driver.get(f"{PROJECT_FRONTEND}{ts_path}?sso_token={token}")
                time.sleep(4)
                ts_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
                if len(ts_text) > 50:
                    screenshot(driver, f"timesheets_{ts_path.replace('/', '_')}")
                    results["ui_tests"]["timesheets"] = {
                        "status": "LOADED",
                        "path": ts_path,
                        "preview": ts_text[:300]
                    }
                    log(f"  Timesheets at {ts_path}: {ts_text[:150]}")
                    break
            except Exception as e:
                log(f"  Timesheets {ts_path}: {e}")
        else:
            results["ui_tests"]["timesheets"] = {"status": "NOT_FOUND"}
            screenshot(driver, "timesheets_notfound")

        # --- 3i: Reports ---
        log("  [3i] Testing Reports...")
        for rp_path in ["/reports", "/report", "/analytics"]:
            try:
                driver.get(f"{PROJECT_FRONTEND}{rp_path}?sso_token={token}")
                time.sleep(4)
                rp_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
                if len(rp_text) > 50:
                    screenshot(driver, f"reports_{rp_path.replace('/', '_')}")
                    results["ui_tests"]["reports"] = {
                        "status": "LOADED",
                        "path": rp_path,
                        "preview": rp_text[:300]
                    }
                    log(f"  Reports at {rp_path}: {rp_text[:150]}")
                    break
            except Exception as e:
                log(f"  Reports {rp_path}: {e}")
        else:
            results["ui_tests"]["reports"] = {"status": "NOT_FOUND"}
            screenshot(driver, "reports_notfound")

        # --- 3j: Settings ---
        log("  [3j] Testing Settings...")
        for st_path in ["/settings", "/setting", "/admin/settings"]:
            try:
                driver.get(f"{PROJECT_FRONTEND}{st_path}?sso_token={token}")
                time.sleep(4)
                st_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
                if len(st_text) > 50:
                    screenshot(driver, f"settings_{st_path.replace('/', '_')}")
                    results["ui_tests"]["settings"] = {
                        "status": "LOADED",
                        "path": st_path,
                        "preview": st_text[:300]
                    }
                    log(f"  Settings at {st_path}: {st_text[:150]}")
                    break
            except Exception as e:
                log(f"  Settings {st_path}: {e}")
        else:
            results["ui_tests"]["settings"] = {"status": "NOT_FOUND"}
            screenshot(driver, "settings_notfound")

        # --- 3k: Check navigation / sidebar links ---
        log("  [3k] Checking for navigation/sidebar links...")
        try:
            driver.get(f"{PROJECT_FRONTEND}?sso_token={token}")
            time.sleep(4)
            links = driver.find_elements(By.TAG_NAME, "a")
            nav_links = []
            for link in links[:50]:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                if href and text:
                    nav_links.append({"text": text, "href": href})
            results["ui_tests"]["navigation_links"] = nav_links[:30]
            log(f"  Found {len(nav_links)} nav links")
            for nl in nav_links[:15]:
                log(f"    - {nl['text']}: {nl['href']}")
        except Exception as e:
            log(f"  Navigation check error: {e}")

        # --- 3l: Final full-page screenshot ---
        screenshot(driver, "final_state")

    except Exception as e:
        log(f"  UI test fatal error: {e}")
        traceback.print_exc()
        try:
            screenshot(driver, "fatal_error")
        except:
            pass
    finally:
        driver.quit()
        log("  Browser closed.")

# ==================== MAIN ====================
def main():
    log("========== EmpCloud Project Module Deep Test ==========")

    # Phase 1: SSO
    token = do_sso_login()
    if not token:
        log("FATAL: Could not get SSO token. Aborting.")
        results["bugs"] = bug_list
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        return

    # Phase 2: API
    test_api(token)

    # Check if API is entirely down (all 502)
    api_statuses = [v.get("status") for v in results["api_tests"].values()]
    all_502 = all(s == 502 for s in api_statuses if isinstance(s, int))
    all_conn_error = all(s == "CONNECTION_ERROR" for s in api_statuses)

    if all_502:
        results["frontend_status"] = "LIKELY DOWN (all APIs return 502)"
        log("All API endpoints return 502 - backend is down")
    elif all_conn_error:
        results["frontend_status"] = "LIKELY DOWN (all APIs connection refused)"
        log("All API endpoints connection error - backend unreachable")

    # Phase 3: UI
    test_ui(token)

    # Summary
    results["bugs"] = bug_list
    results["summary"] = {
        "sso": results["sso_login"],
        "frontend": results["frontend_status"],
        "api_endpoints_tested": len(results["api_tests"]),
        "api_working": sum(1 for v in results["api_tests"].values()
                          if isinstance(v.get("status"), int) and v["status"] < 400),
        "api_errors": sum(1 for v in results["api_tests"].values()
                         if isinstance(v.get("status"), int) and v["status"] >= 400),
        "ui_pages_tested": len(results["ui_tests"]),
        "ui_pages_loaded": sum(1 for v in results["ui_tests"].values()
                               if isinstance(v, dict) and v.get("status") == "LOADED"),
        "bugs_filed": len(bug_list),
        "screenshots_taken": len(results["screenshots"])
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    log("========== SUMMARY ==========")
    for k, v in results["summary"].items():
        log(f"  {k}: {v}")
    log(f"Results saved to {RESULTS_FILE}")
    log("========== DONE ==========")

if __name__ == "__main__":
    main()
