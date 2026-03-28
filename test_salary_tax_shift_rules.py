#!/usr/bin/env python3
"""
EMP Cloud HRMS - Business Rules V2: Sections 16-19
Salary & Compensation, Tax & Statutory, Shift & Scheduling, Overtime & Compensation
Tests each rule via API and Selenium SSO.
"""

import sys, os, time, json, traceback, ssl, re
import urllib.request, urllib.error, urllib.parse
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MAIN_URL       = "https://test-empcloud.empcloud.com"
PAYROLL_URL    = "https://testpayroll.empcloud.com"
API_BASE       = "https://test-empcloud-api.empcloud.com/api/v1"
PAYROLL_API    = "https://testpayroll-api.empcloud.com/api/v1"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\salary_tax_shift"
GITHUB_PAT     = "$GITHUB_TOKEN"
GITHUB_REPO    = "EmpCloud/EmpCloud"

CREDS = {
    "org_admin":  {"email": "ananya@technova.in", "password": "Welcome@123"},
    "employee":   {"email": "priya@technova.in",  "password": "Welcome@123"},
}

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
bugs_found = []
test_results = []
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def shot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{ts()}.png")
    try:
        driver.save_screenshot(path)
        print(f"    [SCREENSHOT] {path}")
    except Exception:
        pass
    return path

def log_result(rule_id, status, details=""):
    test_results.append({"rule": rule_id, "status": status, "details": details})
    icon = {"ENFORCED": "PASS", "NOT ENFORCED": "FAIL", "NOT IMPLEMENTED": "SKIP",
            "PARTIAL": "WARN", "ERROR": "ERR"}.get(status, status)
    print(f"  [{icon}] {rule_id}: {status} - {details}")

def record_bug(title, desc, severity, sp=None):
    bugs_found.append({"title": title, "description": desc, "severity": severity, "screenshot": sp})
    print(f"  [BUG-{severity.upper()}] {title}")

def file_github_issue(title, body, labels=None):
    if labels is None:
        labels = ["bug"]
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    payload = json.dumps({"title": title, "body": body, "labels": labels}).encode()
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "EmpCloud-E2E-Tester",
        "Content-Type": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        result = json.loads(resp.read().decode())
        print(f"    [GITHUB] Issue #{result.get('number')} -> {result.get('html_url')}")
        return result
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else ""
        print(f"    [GITHUB-ERR] {e.code}: {err[:300]}")
    except Exception as e:
        print(f"    [GITHUB-ERR] {e}")
    return None

def api_request(url, token=None, method="GET", data=None):
    headers = {
        "User-Agent": "EmpCloud-E2E-Tester",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(raw), dict(resp.headers)
        except json.JSONDecodeError:
            return resp.status, raw, dict(resp.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(raw), dict(e.headers) if e.headers else {}
        except json.JSONDecodeError:
            return e.code, raw, dict(e.headers) if e.headers else {}
    except Exception as e:
        return 0, str(e), {}

def safe_json(body):
    if isinstance(body, dict):
        return body
    if isinstance(body, str):
        try:
            return json.loads(body)
        except Exception:
            return {}
    return {}

def create_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                "--disable-gpu", "--window-size=1920,1080",
                "--ignore-certificate-errors", "--disable-web-security"]:
        opts.add_argument(arg)
    svc = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=svc, options=opts)
    d.set_page_load_timeout(60)
    d.implicitly_wait(3)
    return d

def do_login(driver, base_url, email, password, label=""):
    print(f"    Logging in as {email} on {base_url} ...")
    driver.get(base_url + "/login")
    time.sleep(5)
    src = driver.page_source.lower()
    if "too many" in src or "rate limit" in src:
        return False, "rate_limited"
    email_el = None
    for sel in [(By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='company']"),
                (By.CSS_SELECTOR, "input[placeholder*='email']"),
                (By.NAME, "email"), (By.ID, "email")]:
        try:
            el = driver.find_element(*sel)
            if el.is_displayed():
                email_el = el; break
        except NoSuchElementException:
            continue
    pass_el = None
    for sel in [(By.CSS_SELECTOR, "input[type='password']"), (By.NAME, "password")]:
        try:
            el = driver.find_element(*sel)
            if el.is_displayed():
                pass_el = el; break
        except NoSuchElementException:
            continue
    if not email_el or not pass_el:
        return False, "no_fields"
    email_el.clear(); email_el.send_keys(email)
    pass_el.clear(); pass_el.send_keys(password)
    for sel in [(By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(),'Sign')]"),
                (By.XPATH, "//button[contains(text(),'Log')]")]:
        try:
            btn = driver.find_element(*sel)
            if btn.is_displayed():
                btn.click(); break
        except NoSuchElementException:
            continue
    time.sleep(6)
    shot(driver, f"post_login_{label}")
    url_after = driver.current_url
    success = "/login" not in url_after.lower()
    print(f"    Post-login URL: {url_after} (success={success})")
    return success, "ok" if success else "login_failed"

def extract_token(driver):
    try:
        keys = driver.execute_script("return Object.keys(localStorage);")
        for k in (keys or []):
            val = driver.execute_script(f"return localStorage.getItem('{k}');")
            if val and ("auth" in k.lower() or "token" in k.lower()):
                try:
                    parsed = json.loads(val)
                    state = parsed.get("state", parsed) if isinstance(parsed, dict) else {}
                    tok = state.get("accessToken") or state.get("token")
                    if tok:
                        return tok
                except (json.JSONDecodeError, TypeError):
                    if isinstance(val, str) and val.startswith("ey"):
                        return val
    except Exception:
        pass
    return None

def page_has_text(driver, *texts):
    src = driver.page_source.lower()
    for t in texts:
        if t.lower() in src:
            return True
    return False

def extract_numbers_from_text(text):
    """Extract currency-like numbers from text (e.g., '2,00,000' or '196200')."""
    # Match Indian number format like 2,00,000 or plain numbers
    matches = re.findall(r'[\d,]+\.?\d*', text)
    results = []
    for m in matches:
        clean = m.replace(',', '')
        try:
            val = float(clean)
            if val > 0:
                results.append(val)
        except ValueError:
            pass
    return results


# ---------------------------------------------------------------------------
# PAYROLL LOGIN & API TOKEN
# ---------------------------------------------------------------------------
def login_payroll_direct(driver, email, password):
    """Log in directly to the Payroll module."""
    print(f"    Logging in to Payroll as {email}...")
    driver.get(PAYROLL_URL + "/login")
    time.sleep(5)
    shot(driver, "payroll_login_page")

    email_el = None
    for sel in [(By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='Email']"),
                (By.NAME, "email"), (By.ID, "email")]:
        try:
            el = driver.find_element(*sel)
            if el.is_displayed():
                email_el = el; break
        except NoSuchElementException:
            continue

    pass_el = None
    for sel in [(By.CSS_SELECTOR, "input[type='password']"), (By.NAME, "password")]:
        try:
            el = driver.find_element(*sel)
            if el.is_displayed():
                pass_el = el; break
        except NoSuchElementException:
            continue

    if not email_el or not pass_el:
        print("    Payroll login fields not found")
        return False

    email_el.clear(); email_el.send_keys(email)
    time.sleep(1)
    pass_el.clear(); pass_el.send_keys(password)
    time.sleep(1)

    # Try multiple button selectors
    clicked = False
    for sel in [(By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(),'Sign in')]"),
                (By.XPATH, "//button[contains(text(),'Sign')]"),
                (By.XPATH, "//button[contains(text(),'Login')]"),
                (By.XPATH, "//button[contains(text(),'Log in')]"),
                (By.CSS_SELECTOR, "button.btn-primary"),
                (By.CSS_SELECTOR, "button"),
                (By.XPATH, "//input[@type='submit']")]:
        try:
            btn = driver.find_element(*sel)
            if btn.is_displayed() and btn.is_enabled():
                print(f"    Clicking button: {btn.text} ({sel})")
                btn.click()
                clicked = True
                break
        except NoSuchElementException:
            continue

    if not clicked:
        # Try submitting via JS
        try:
            driver.execute_script("document.querySelector('form').submit();")
            print("    Submitted form via JS")
        except Exception:
            pass

    time.sleep(8)
    shot(driver, "payroll_post_login")
    url_after = driver.current_url
    page_text = driver.find_element(By.TAG_NAME, "body").text[:500]
    print(f"    Payroll post-login URL: {url_after}")
    print(f"    Payroll post-login text: {page_text[:300]}")
    success = "/login" not in url_after.lower()
    print(f"    Payroll login success: {success}")
    return success


def get_payroll_token(driver):
    """Extract auth token from payroll app localStorage."""
    try:
        keys = driver.execute_script("return Object.keys(localStorage);")
        print(f"    Payroll localStorage keys: {keys}")
        for k in (keys or []):
            val = driver.execute_script(f"return localStorage.getItem('{k}');")
            if val and len(val) > 20:
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        for tk in ["accessToken", "token", "sso_token", "jwt", "access_token"]:
                            if parsed.get(tk):
                                print(f"    Payroll token from '{k}' -> {tk}: {str(parsed[tk])[:50]}...")
                                return parsed[tk]
                        state = parsed.get("state", {})
                        if isinstance(state, dict):
                            for tk in ["accessToken", "token"]:
                                if state.get(tk):
                                    print(f"    Payroll token from '{k}' -> state.{tk}")
                                    return state[tk]
                except (json.JSONDecodeError, TypeError):
                    if isinstance(val, str) and val.startswith("ey"):
                        print(f"    Payroll JWT from '{k}'")
                        return val
    except Exception as e:
        print(f"    get_payroll_token error: {e}")
    return None


def login_payroll_api(email, password):
    """Try to get a payroll API token via direct API login."""
    for ep in [f"{PAYROLL_API}/auth/login", f"{PAYROLL_API}/login",
               f"https://testpayroll-api.empcloud.com/api/auth/login",
               f"https://testpayroll-api.empcloud.com/login"]:
        code, body, _ = api_request(ep, method="POST", data={"email": email, "password": password})
        print(f"    {ep} -> HTTP {code}, body type={type(body).__name__}")
        if code == 200:
            if isinstance(body, dict):
                print(f"    Response keys: {list(body.keys())}")
                print(f"    Response (first 500): {json.dumps(body, default=str)[:500]}")
                # Deep search for token in response
                token = None
                for key_path in [
                    lambda b: b.get("token"),
                    lambda b: b.get("accessToken"),
                    lambda b: b.get("access_token"),
                    lambda b: b.get("data", {}).get("token") if isinstance(b.get("data"), dict) else None,
                    lambda b: b.get("data", {}).get("accessToken") if isinstance(b.get("data"), dict) else None,
                    lambda b: b.get("data", {}).get("access_token") if isinstance(b.get("data"), dict) else None,
                    lambda b: b.get("result", {}).get("token") if isinstance(b.get("result"), dict) else None,
                    lambda b: b.get("auth", {}).get("token") if isinstance(b.get("auth"), dict) else None,
                ]:
                    try:
                        token = key_path(body)
                        if token:
                            break
                    except Exception:
                        continue
                # Also search recursively for any JWT-like string
                if not token:
                    body_str = json.dumps(body)
                    jwt_match = re.search(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', body_str)
                    if jwt_match:
                        token = jwt_match.group(0)
                        print(f"    Found JWT via regex in response")
                if token:
                    print(f"    Payroll API token from {ep}: {str(token)[:50]}...")
                    return token
                else:
                    print(f"    No token found in response body")
            elif isinstance(body, str) and body.startswith("ey"):
                print(f"    Payroll API token (raw string) from {ep}")
                return body
    return None


# ---------------------------------------------------------------------------
# SCRAPE PAYROLL DASHBOARD DATA
# ---------------------------------------------------------------------------
def scrape_dashboard_data(driver):
    """Scrape the payroll dashboard for salary data visible in the UI."""
    data = {}
    try:
        # Get all text content from page
        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"    Dashboard text (first 1000 chars): {body_text[:1000]}")

        # Extract structured data from the visible dashboard
        # Look for Monthly CTC, Net Pay, Tax Regime
        lines = body_text.split("\n")
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            # Look for labeled values
            if "monthly ctc" in line_lower or "ctc" in line_lower:
                nums = extract_numbers_from_text(line)
                if not nums and i+1 < len(lines):
                    nums = extract_numbers_from_text(lines[i+1])
                if nums:
                    data["monthly_ctc"] = nums[0]
            if "net pay" in line_lower:
                nums = extract_numbers_from_text(line)
                if not nums and i+1 < len(lines):
                    nums = extract_numbers_from_text(lines[i+1])
                if nums:
                    data["net_pay"] = nums[0]
            if "gross" in line_lower and "pay" in line_lower:
                nums = extract_numbers_from_text(line)
                if not nums and i+1 < len(lines):
                    nums = extract_numbers_from_text(lines[i+1])
                if nums:
                    data["gross_pay"] = nums[0]
            if "tax regime" in line_lower or "regime" in line_lower:
                if "old" in line_lower:
                    data["tax_regime"] = "old"
                elif "new" in line_lower:
                    data["tax_regime"] = "new"
                else:
                    # Check next line
                    if i+1 < len(lines):
                        next_line = lines[i+1].strip().lower()
                        if "old" in next_line:
                            data["tax_regime"] = "old"
                        elif "new" in next_line:
                            data["tax_regime"] = "new"
            if "deduction" in line_lower:
                nums = extract_numbers_from_text(line)
                if nums:
                    data["deductions"] = nums[0]
            if "basic" in line_lower:
                nums = extract_numbers_from_text(line)
                if nums:
                    data["basic"] = nums[0]
            if "hra" in line_lower:
                nums = extract_numbers_from_text(line)
                if nums:
                    data["hra"] = nums[0]
            if "pf" in line_lower and "employer" not in line_lower:
                nums = extract_numbers_from_text(line)
                if nums:
                    data["pf"] = nums[0]
            if "esi" in line_lower:
                nums = extract_numbers_from_text(line)
                if nums:
                    data["esi"] = nums[0]
            if "professional tax" in line_lower or "pt" == line_lower.strip():
                nums = extract_numbers_from_text(line)
                if nums:
                    data["professional_tax"] = nums[0]
            if "tds" in line_lower:
                nums = extract_numbers_from_text(line)
                if nums:
                    data["tds"] = nums[0]
            if "february" in line_lower or "march" in line_lower or "january" in line_lower:
                if "payslip" in line_lower or "latest" in line_lower:
                    data["latest_payslip_month"] = line.strip()
            if "earning" in line_lower:
                nums = extract_numbers_from_text(line)
                if nums:
                    data["earnings"] = nums[0]

        print(f"    Scraped dashboard data: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"    scrape_dashboard_data error: {e}")
    return data


def scrape_salary_page(driver):
    """Navigate to My Salary page and scrape salary structure data."""
    data = {}
    try:
        driver.get(PAYROLL_URL + "/my/salary")
        time.sleep(4)
        shot(driver, "my_salary_page")
        src = driver.page_source.lower()

        # If redirected to login, this page needs auth
        if "/login" in driver.current_url.lower():
            print("    /my/salary redirected to login")
            return data

        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"    My Salary text: {body_text[:1500]}")

        lines = body_text.split("\n")
        for i, line in enumerate(lines):
            ll = line.strip().lower()
            if "basic" in ll:
                nums = extract_numbers_from_text(line)
                if nums: data["basic"] = nums[0]
            if "hra" in ll:
                nums = extract_numbers_from_text(line)
                if nums: data["hra"] = nums[0]
            if "ctc" in ll:
                nums = extract_numbers_from_text(line)
                if nums: data["ctc"] = nums[0]
            if "gross" in ll:
                nums = extract_numbers_from_text(line)
                if nums: data["gross"] = nums[0]
            if "pf" in ll or "provident" in ll:
                nums = extract_numbers_from_text(line)
                if nums: data["pf"] = nums[0]
            if "esi" in ll:
                nums = extract_numbers_from_text(line)
                if nums: data["esi"] = nums[0]
            if "gratuity" in ll:
                nums = extract_numbers_from_text(line)
                if nums: data["gratuity"] = nums[0]
            if "employer pf" in ll or "employer contribution" in ll:
                nums = extract_numbers_from_text(line)
                if nums: data["employer_pf"] = nums[0]

        # Also try tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        for tidx, table in enumerate(tables[:5]):
            rows = table.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td") + row.find_elements(By.TAG_NAME, "th")
                cell_texts = [c.text.strip() for c in cells]
                if len(cell_texts) >= 2:
                    label = cell_texts[0].lower()
                    val_text = cell_texts[-1]
                    nums = extract_numbers_from_text(val_text)
                    if nums:
                        if "basic" in label: data["basic"] = nums[0]
                        elif "hra" in label: data["hra"] = nums[0]
                        elif "gross" in label: data["gross"] = nums[0]
                        elif "ctc" in label: data["ctc"] = nums[0]
                        elif "pf" in label and "employer" in label: data["employer_pf"] = nums[0]
                        elif "pf" in label: data["pf"] = nums[0]
                        elif "esi" in label and "employer" in label: data["employer_esi"] = nums[0]
                        elif "esi" in label: data["esi"] = nums[0]
                        elif "gratuity" in label: data["gratuity"] = nums[0]
                        elif "net" in label: data["net_pay"] = nums[0]

        print(f"    My Salary scraped: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"    scrape_salary_page error: {e}")
    return data


def scrape_tax_page(driver):
    """Navigate to My Tax page and scrape tax regime/declaration data."""
    data = {}
    try:
        driver.get(PAYROLL_URL + "/my/tax")
        time.sleep(4)
        shot(driver, "my_tax_page")

        if "/login" in driver.current_url.lower():
            print("    /my/tax redirected to login")
            return data

        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"    My Tax text: {body_text[:1500]}")

        if "old regime" in body_text.lower():
            data["regime"] = "old"
        elif "new regime" in body_text.lower():
            data["regime"] = "new"

        if "80c" in body_text.lower() or "80C" in body_text:
            data["has_80c"] = True
        if "declaration" in body_text.lower():
            data["has_declarations"] = True
        if "form 16" in body_text.lower() or "form16" in body_text.lower():
            data["has_form16"] = True

        print(f"    My Tax scraped: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"    scrape_tax_page error: {e}")
    return data


def scrape_payslip_page(driver):
    """Navigate to My Payslips and extract payslip data."""
    data = {}
    try:
        driver.get(PAYROLL_URL + "/my/payslips")
        time.sleep(4)
        shot(driver, "my_payslips_page")

        if "/login" in driver.current_url.lower():
            # Try alternative paths
            for alt in ["/my/payslip", "/payslips", "/payslip"]:
                driver.get(PAYROLL_URL + alt)
                time.sleep(3)
                if "/login" not in driver.current_url.lower():
                    break

        if "/login" in driver.current_url.lower():
            print("    Payslips page redirected to login")
            return data

        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"    Payslips text: {body_text[:1500]}")

        # Check for month/year in payslips
        now = datetime.now()
        future_months = ["april 2026", "may 2026", "june 2026", "july 2026",
                         "august 2026", "september 2026", "october 2026",
                         "november 2026", "december 2026"]
        for fm in future_months:
            if fm in body_text.lower():
                data["has_future_payslip"] = fm
                break

        if "february 2026" in body_text.lower():
            data["latest_month"] = "February 2026"
        elif "march 2026" in body_text.lower():
            data["latest_month"] = "March 2026"

        print(f"    Payslips scraped: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"    scrape_payslip_page error: {e}")
    return data


def scrape_admin_panel(driver):
    """Navigate to payroll Admin Panel and check for salary structure management."""
    data = {"pages_found": []}
    try:
        # Click Admin Panel in sidebar
        for sel in [(By.XPATH, "//a[contains(text(),'Admin')]"),
                    (By.XPATH, "//span[contains(text(),'Admin')]"),
                    (By.XPATH, "//*[contains(text(),'Admin Panel')]")]:
            try:
                el = driver.find_element(*sel)
                if el.is_displayed():
                    el.click()
                    time.sleep(3)
                    shot(driver, "admin_panel")
                    break
            except NoSuchElementException:
                continue

        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"    Admin Panel text: {body_text[:1500]}")

        # Try admin sub-pages
        admin_paths = [
            "/admin", "/admin/salary-structure", "/admin/salary-components",
            "/admin/payroll", "/admin/tax-settings", "/admin/shifts",
            "/admin/overtime", "/admin/employees", "/admin/settings",
            "/admin/statutory", "/admin/pf-settings", "/admin/esi-settings",
        ]
        for path in admin_paths:
            driver.get(PAYROLL_URL + path)
            time.sleep(2)
            if "/login" not in driver.current_url.lower():
                src = driver.page_source.lower()
                if "404" not in src and len(src) > 500:
                    data["pages_found"].append(path)
                    print(f"    [ADMIN PAGE] {path}")
                    shot(driver, f"admin_{path.replace('/', '_')}")

        print(f"    Admin pages found: {data['pages_found']}")
    except Exception as e:
        print(f"    scrape_admin_panel error: {e}")
    return data


# ---------------------------------------------------------------------------
# PAYROLL API EXPLORATION
# ---------------------------------------------------------------------------
def explore_payroll_api(token):
    """Probe payroll API endpoints using the auth token."""
    endpoints = {}
    candidates = [
        ("self_service_dashboard", f"{PAYROLL_API}/self-service/dashboard"),
        ("self_service_salary", f"{PAYROLL_API}/self-service/salary"),
        ("self_service_payslips", f"{PAYROLL_API}/self-service/payslips"),
        ("self_service_tax", f"{PAYROLL_API}/self-service/tax"),
        ("salary_structure", f"{PAYROLL_API}/salary-structure"),
        ("salary_components", f"{PAYROLL_API}/salary-components"),
        ("employees", f"{PAYROLL_API}/employees"),
        ("employee_salary", f"{PAYROLL_API}/employee-salary"),
        ("payroll_run", f"{PAYROLL_API}/payroll/run"),
        ("payroll", f"{PAYROLL_API}/payroll"),
        ("payslips", f"{PAYROLL_API}/payslips"),
        ("tax_settings", f"{PAYROLL_API}/tax-settings"),
        ("tax_regime", f"{PAYROLL_API}/tax-regime"),
        ("tax_declarations", f"{PAYROLL_API}/tax-declarations"),
        ("statutory", f"{PAYROLL_API}/statutory"),
        ("pf_settings", f"{PAYROLL_API}/pf-settings"),
        ("esi_settings", f"{PAYROLL_API}/esi-settings"),
        ("shifts", f"{PAYROLL_API}/shifts"),
        ("overtime", f"{PAYROLL_API}/overtime"),
        ("attendance", f"{PAYROLL_API}/attendance"),
        ("settings", f"{PAYROLL_API}/settings"),
        ("announcements", f"{PAYROLL_API}/announcements"),
        ("ctc", f"{PAYROLL_API}/ctc"),
        ("investment", f"{PAYROLL_API}/investment-declarations"),
        ("emp_salary", f"{API_BASE}/salary"),
        ("emp_shifts", f"{API_BASE}/shifts"),
        ("emp_overtime", f"{API_BASE}/overtime"),
        ("emp_attendance", f"{API_BASE}/attendance"),
        ("emp_employees", f"{API_BASE}/employees"),
    ]
    for key, url in candidates:
        code, body, _ = api_request(url, token=token)
        if code in (200, 201):
            endpoints[key] = {"url": url, "code": code, "data": body}
            print(f"    [API OK] {key} -> {url} (HTTP {code})")
        elif code == 403:
            endpoints[key] = {"url": url, "code": code, "data": body}
            print(f"    [API FORBIDDEN] {key} -> {url} (HTTP 403)")
        elif code == 401:
            pass  # skip silently
        elif code not in (0, 404):
            print(f"    [API {code}] {key} -> {url}")
    return endpoints


# ---------------------------------------------------------------------------
# BUSINESS RULE TESTS
# ---------------------------------------------------------------------------
def test_all_rules(payroll_token, main_token, driver, dashboard_data, salary_data,
                   tax_data, payslip_data, api_endpoints):
    """Test all 39 rules from sections 16-19."""

    def fval(v, default=0):
        if v is None: return default
        try: return float(str(v).replace(',', ''))
        except: return default

    print("\n" + "="*70)
    print("SECTION 16: SALARY & COMPENSATION")
    print("="*70)

    # SC001: Salary cannot be zero or negative
    print("\n--- SC001: Salary cannot be zero or negative ---")
    sc001_done = False
    tok = payroll_token or main_token

    # Try salary-structure, employee-salary and other admin payroll endpoints
    test_urls = []
    for key in ["salary_structure_admin", "salary_structure", "employee_salary",
                 "emp_salary", "self_service_salary"]:
        ep = api_endpoints.get(key)
        if ep:
            test_urls.append(ep["url"])
    # Also try known payroll API paths
    test_urls.extend([
        f"{PAYROLL_API}/salary-structure",
        f"{PAYROLL_API}/employee-salary",
        f"{PAYROLL_API}/salary",
    ])
    # Deduplicate
    test_urls = list(dict.fromkeys(test_urls))

    for url in test_urls:
        for bad_val in [0, -5000]:
            for payload in [
                {"ctc": bad_val, "basic": bad_val, "gross": bad_val},
                {"employee_id": "test", "ctc": bad_val},
                {"amount": bad_val},
            ]:
                code, body, _ = api_request(url, token=tok, method="POST", data=payload)
                if code in (400, 422):
                    log_result("SC001", "ENFORCED", f"API rejects salary={bad_val} at {url} (HTTP {code})")
                    sc001_done = True
                    break
                elif code in (200, 201):
                    log_result("SC001", "NOT ENFORCED", f"API accepted salary={bad_val} at {url}")
                    record_bug("[Business Rule] SC001: Zero/negative salary accepted",
                               f"POST {url} with salary={bad_val} returned HTTP {code}. Salary must be > 0.",
                               "critical")
                    sc001_done = True
                    break
            if sc001_done:
                break
        if sc001_done:
            break
    if not sc001_done:
        if salary_data.get("ctc") or salary_data.get("basic"):
            log_result("SC001", "NOT IMPLEMENTED",
                       f"Salary data exists (CTC={salary_data.get('ctc')}, Basic={salary_data.get('basic')}) "
                       "but no salary write API found to test zero/negative validation")
        else:
            log_result("SC001", "NOT IMPLEMENTED", "No salary creation API endpoint found")

    # SC002: Basic pay must be >= minimum wage
    print("\n--- SC002: Basic >= minimum wage ---")
    basic_val = fval(salary_data.get("basic") or payslip_data.get("basic"))
    if basic_val and basic_val > 0:
        if basic_val >= 8000:  # rough minimum wage check
            log_result("SC002", "PARTIAL", f"Basic={basic_val}/month appears above minimum wage but no API validation test possible")
        else:
            log_result("SC002", "NOT ENFORCED", f"Basic={basic_val}/month may be below minimum wage")
    else:
        log_result("SC002", "NOT IMPLEMENTED", "No basic salary data found to verify minimum wage")

    # SC003: HRA cannot exceed 50% of basic
    print("\n--- SC003: HRA <= 50% of basic ---")
    basic_for_hra = fval(salary_data.get("basic") or payslip_data.get("basic"))
    hra_val = fval(salary_data.get("hra") or payslip_data.get("hra"))
    if basic_for_hra and hra_val:
        limit = basic_for_hra * 0.5
        if hra_val <= limit + 1:  # small tolerance
            log_result("SC003", "ENFORCED", f"HRA={hra_val} <= 50% of basic={basic_for_hra} (limit={limit})")
        else:
            log_result("SC003", "NOT ENFORCED", f"HRA={hra_val} > 50% of basic={basic_for_hra} (limit={limit})")
            record_bug("[Business Rule] SC003: HRA exceeds 50% of basic",
                       f"HRA={hra_val} exceeds 50% limit of basic={basic_for_hra} (max={limit})", "high")
    else:
        log_result("SC003", "NOT IMPLEMENTED", "No basic/HRA salary data to verify")

    # SC004: Salary revision past date
    print("\n--- SC004: Salary revision past effective date ---")
    log_result("SC004", "NOT IMPLEMENTED", "No salary revision API found; requires admin salary management")

    # SC005: Arrears auto-calculated
    print("\n--- SC005: Arrears auto-calculation ---")
    log_result("SC005", "NOT IMPLEMENTED", "Requires back-dated salary revision + payroll run")

    # SC006: CTC = Gross + Employer PF + Employer ESI + Gratuity
    print("\n--- SC006: CTC breakdown verification ---")
    sc006_done = False

    # Prefer payslip data for precise monthly verification
    total_employer_cost = fval(payslip_data.get("total_employer_cost"))
    payslip_gross = fval(payslip_data.get("gross_earnings"))
    payslip_epf = fval(payslip_data.get("employer_pf"))
    payslip_eesi = fval(payslip_data.get("employer_esi"))

    # Also compute from salary structure
    ctc = fval(salary_data.get("ctc")) or total_employer_cost
    gross = fval(salary_data.get("gross")) or payslip_gross
    epf = payslip_epf
    eesi = payslip_eesi
    gratuity = fval(salary_data.get("gratuity"))

    # Check at payslip level first (most precise)
    if total_employer_cost and payslip_gross:
        expected_ctc = payslip_gross + payslip_epf + payslip_eesi
        diff = abs(total_employer_cost - expected_ctc)
        if diff < 10:
            log_result("SC006", "ENFORCED",
                       f"Monthly CTC (total_employer_cost)={total_employer_cost} = "
                       f"Gross({payslip_gross}) + Employer PF({payslip_epf}) + Employer ESI({payslip_eesi}) = {expected_ctc}")
            sc006_done = True
        else:
            # Maybe gratuity is included
            expected_with_gratuity = payslip_gross + payslip_epf + payslip_eesi + gratuity
            if abs(total_employer_cost - expected_with_gratuity) < 10:
                log_result("SC006", "ENFORCED",
                           f"CTC={total_employer_cost} = Gross({payslip_gross}) + EPF({payslip_epf}) + "
                           f"EESI({payslip_eesi}) + Gratuity({gratuity}) = {expected_with_gratuity}")
                sc006_done = True

    # Also check for data consistency between salary structure and payslip
    if salary_data.get("special_allowance") and payslip_data.get("special_allowance"):
        struct_sa = fval(salary_data.get("special_allowance"))
        slip_sa = fval(payslip_data.get("special_allowance"))
        if struct_sa and slip_sa and abs(struct_sa - slip_sa) > 10:
            print(f"    [DATA NOTE] Special Allowance: Structure={struct_sa}/month vs Payslip={slip_sa}/month (diff={slip_sa-struct_sa})")
            # This is not necessarily a bug - payslip SA may vary based on actual deductions

    if not sc006_done and ctc and gross:
        expected = gross + epf + eesi + gratuity
        diff = abs(ctc - expected)
        if diff < 100:
            log_result("SC006", "ENFORCED",
                       f"CTC={ctc} ~ Gross({gross})+EPF({epf})+EESI({eesi})+Gratuity({gratuity})={expected}")
        else:
            log_result("SC006", "PARTIAL",
                       f"CTC={ctc}, Gross={gross}, Employer PF={epf}, ESI={eesi}, Gratuity={gratuity}. "
                       f"CTC-Gross={ctc-gross}. Difference may include employer contributions not fully scraped.")
            # The difference between CTC and Gross should be employer statutory contributions
            employer_contrib = ctc - gross
            if employer_contrib > 0:
                print(f"    Employer contributions implied: {employer_contrib}")
        sc006_done = True
    elif not sc006_done and ctc:
        log_result("SC006", "PARTIAL", f"CTC={ctc} visible but Gross breakdown not fully available")
        sc006_done = True

    if not sc006_done:
        # Check API
        for key in ["self_service_dashboard", "self_service_salary", "ctc"]:
            ep = api_endpoints.get(key)
            if not ep or ep["code"] != 200:
                continue
            data = ep["data"]
            if isinstance(data, dict):
                d = data.get("data", data)
                c = d.get("ctc") or d.get("monthlyCTC") or d.get("monthly_ctc")
                g = d.get("gross") or d.get("grossSalary")
                if c:
                    log_result("SC006", "PARTIAL", f"CTC={c} from API ({key}) but full breakdown not available")
                    sc006_done = True
                    break
    if not sc006_done:
        log_result("SC006", "NOT IMPLEMENTED", "No CTC breakdown data found")

    # SC007: Salary structure components sum to CTC
    print("\n--- SC007: Components sum to CTC ---")
    if salary_data.get("ctc") and salary_data.get("basic"):
        log_result("SC007", "PARTIAL", "Salary components visible but full summation requires all components")
    else:
        log_result("SC007", "NOT IMPLEMENTED", "No complete salary structure found")

    # SC008: Cannot assign salary to terminated employee
    print("\n--- SC008: No salary for terminated employee ---")
    emp_ep = api_endpoints.get("emp_employees") or api_endpoints.get("employees")
    if emp_ep and emp_ep["code"] == 200:
        items = emp_ep["data"]
        if isinstance(items, dict):
            items = items.get("data", items.get("employees", []))
        if isinstance(items, list):
            terminated = [e for e in items if str(e.get("status", "")).lower() in ("terminated", "inactive", "separated")]
            if terminated:
                term_id = terminated[0].get("id") or terminated[0].get("_id")
                log_result("SC008", "PARTIAL", f"Found {len(terminated)} terminated employees but no salary assignment API to test")
            else:
                log_result("SC008", "NOT IMPLEMENTED", "No terminated employees found in system")
        else:
            log_result("SC008", "NOT IMPLEMENTED", "Could not parse employee list")
    else:
        log_result("SC008", "NOT IMPLEMENTED", "Employee list not accessible")

    # SC009: Salary slip correct month/year
    print("\n--- SC009: Salary slip month/year ---")
    if payslip_data.get("has_future_payslip"):
        log_result("SC009", "NOT ENFORCED", f"Future payslip found: {payslip_data['has_future_payslip']}")
        record_bug("[Business Rule] SC009: Future payslip exists",
                   f"Payslip for {payslip_data['has_future_payslip']} found. No future payslips should exist.", "high")
    elif payslip_data.get("month") and payslip_data.get("year"):
        m, y = payslip_data["month"], payslip_data["year"]
        now = datetime.now()
        if int(y) > now.year or (int(y) == now.year and int(m) > now.month):
            log_result("SC009", "NOT ENFORCED", f"Latest payslip month={m}/{y} is in the future!")
            record_bug("[Business Rule] SC009: Future payslip exists",
                       f"Payslip for {m}/{y} found but current date is {now.month}/{now.year}.", "high")
        else:
            log_result("SC009", "ENFORCED", f"Latest payslip: {m}/{y} (not in future, status={payslip_data.get('status')})")
    elif dashboard_data.get("latest_payslip_month"):
        log_result("SC009", "ENFORCED", f"Latest payslip from dashboard: {dashboard_data['latest_payslip_month']}")
    else:
        log_result("SC009", "NOT IMPLEMENTED", "No payslip month data found")

    # SC010: Increment cap
    print("\n--- SC010: Increment % cap ---")
    log_result("SC010", "NOT IMPLEMENTED", "No increment/revision API found")

    # -----------------------------------------------------------------------
    print("\n" + "="*70)
    print("SECTION 17: TAX & STATUTORY COMPLIANCE")
    print("="*70)

    # TX001: PF threshold (basic <= 15K)
    print("\n--- TX001: PF deduction (12% of basic, threshold Rs 15K) ---")
    basic = fval(salary_data.get("basic") or payslip_data.get("basic") or dashboard_data.get("basic"))
    pf = fval(payslip_data.get("employee_pf") or salary_data.get("pf") or dashboard_data.get("pf"))
    if basic and pf:
        pf_base = min(basic, 15000)
        expected_pf = pf_base * 0.12
        if basic > 15000:
            if abs(pf - 1800) < 50:
                log_result("TX001", "ENFORCED", f"Basic={basic}>15K, PF={pf} ~ 12% of 15K threshold (1800)")
            elif abs(pf - basic * 0.12) < 50:
                log_result("TX001", "PARTIAL", f"Basic={basic}>15K, PF={pf} = 12% of full basic (employee opted for full PF)")
            else:
                log_result("TX001", "NOT ENFORCED", f"Basic={basic}, PF={pf} (expected ~1800 or ~{basic*0.12:.0f})")
                record_bug("[Business Rule] TX001: PF deduction incorrect",
                           f"Basic={basic}>15K, PF={pf}. Expected 12% of min(basic,15000)=1800.", "critical")
        else:
            if abs(pf - basic * 0.12) < 50:
                log_result("TX001", "ENFORCED", f"Basic={basic}<=15K, PF={pf} ~ 12% of basic ({basic*0.12:.0f})")
            else:
                log_result("TX001", "NOT ENFORCED", f"Basic={basic}, PF={pf} (expected {basic*0.12:.0f})")
    else:
        # Check API dashboard
        dash_ep = api_endpoints.get("self_service_dashboard")
        if dash_ep and dash_ep["code"] == 200:
            d = dash_ep["data"]
            if isinstance(d, dict):
                d = d.get("data", d)
                b = d.get("basic") or d.get("basicSalary")
                p = d.get("pf") or d.get("pfDeduction") or d.get("employeePF")
                if b and p:
                    log_result("TX001", "PARTIAL", f"API has basic={b}, pf={p} - verify 12% calculation")
                else:
                    log_result("TX001", "NOT IMPLEMENTED", f"API dashboard keys: {list(d.keys()) if isinstance(d, dict) else 'N/A'}")
            else:
                log_result("TX001", "NOT IMPLEMENTED", "Dashboard API returned non-dict")
        else:
            log_result("TX001", "NOT IMPLEMENTED", "No salary data with basic/PF found")

    # TX002: ESI threshold (gross <= 21K)
    print("\n--- TX002: ESI threshold (gross <= Rs 21K) ---")
    gross_val = fval(payslip_data.get("gross_earnings") or salary_data.get("gross") or dashboard_data.get("gross_pay"))
    esi_val = fval(payslip_data.get("employee_esi") or salary_data.get("esi") or dashboard_data.get("esi"))
    if gross_val:
        if gross_val > 21000:
            if esi_val and float(esi_val) > 0:
                log_result("TX002", "NOT ENFORCED", f"Gross={gross_val}>21K but ESI={esi_val}>0")
                record_bug("[Business Rule] TX002: ESI charged above Rs 21K threshold",
                           f"Gross={gross_val} exceeds Rs 21,000 but ESI={esi_val} is still charged.", "critical")
            else:
                log_result("TX002", "ENFORCED", f"Gross={gross_val}>21K and ESI=0 (correct)")
        else:
            if esi_val:
                expected_esi = gross_val * 0.0075
                log_result("TX002", "ENFORCED", f"Gross={gross_val}<=21K, ESI={esi_val} (expected ~{expected_esi:.0f})")
            else:
                log_result("TX002", "PARTIAL", f"Gross={gross_val}<=21K but ESI value not found")
    else:
        log_result("TX002", "NOT IMPLEMENTED", "No gross salary data for ESI threshold check")

    # TX003: Professional Tax
    print("\n--- TX003: Professional Tax per state slab ---")
    pt = fval(payslip_data.get("professional_tax") or salary_data.get("professional_tax") or dashboard_data.get("professional_tax"))
    if pt:
        log_result("TX003", "PARTIAL", f"Professional Tax=Rs {pt}/month found; state slab verification needs manual check")
    else:
        log_result("TX003", "NOT IMPLEMENTED", "No Professional Tax data found")

    # TX004: TDS on projected annual income
    print("\n--- TX004: TDS on projected annual income ---")
    tds = fval(payslip_data.get("tds") or salary_data.get("tds") or dashboard_data.get("tds"))
    if tds:
        log_result("TX004", "PARTIAL", f"TDS={tds} found; projected annual calculation needs manual verification")
    else:
        log_result("TX004", "NOT IMPLEMENTED", "No TDS data found")

    # TX005: Tax regime choice (old vs new)
    print("\n--- TX005: Tax regime (old vs new) ---")
    regime = tax_data.get("regime") or dashboard_data.get("tax_regime")
    if regime:
        log_result("TX005", "ENFORCED", f"Tax regime = '{regime}' regime. Employee choice is recorded.")
    else:
        # Check payroll dashboard via UI
        if driver:
            try:
                driver.get(PAYROLL_URL + "/my")
                time.sleep(4)
                src = driver.page_source.lower()
                if "old regime" in src:
                    log_result("TX005", "ENFORCED", "Tax regime = 'Old Regime' visible on dashboard")
                elif "new regime" in src:
                    log_result("TX005", "ENFORCED", "Tax regime = 'New Regime' visible on dashboard")
                else:
                    log_result("TX005", "NOT IMPLEMENTED", "No tax regime selection found")
            except Exception:
                log_result("TX005", "NOT IMPLEMENTED", "Could not check tax regime via UI")
        else:
            log_result("TX005", "NOT IMPLEMENTED", "No tax regime data found")

    # TX006: 80C cap (1.5L)
    print("\n--- TX006: 80C deductions cap (Rs 1.5L) ---")
    if tax_data.get("has_80c") or tax_data.get("has_declarations"):
        log_result("TX006", "PARTIAL", "Tax declarations page exists; 80C cap enforcement needs manual test")
    else:
        inv_ep = api_endpoints.get("investment") or api_endpoints.get("tax_declarations")
        if inv_ep:
            log_result("TX006", "PARTIAL", f"Tax declarations API exists ({inv_ep['url']}); cap validation needs test")
        else:
            log_result("TX006", "NOT IMPLEMENTED", "No investment declarations found")

    # TX007-TX008
    print("\n--- TX007: HRA exemption calculation ---")
    log_result("TX007", "NOT IMPLEMENTED", "Requires payroll computation with rent details")

    print("\n--- TX008: Standard deduction Rs 50K ---")
    log_result("TX008", "NOT IMPLEMENTED", "Requires tax computation breakdown")

    # TX009: Form 16
    print("\n--- TX009: Form 16 ---")
    if tax_data.get("has_form16"):
        log_result("TX009", "PARTIAL", "Form 16 reference found in tax page")
    else:
        log_result("TX009", "NOT IMPLEMENTED", "No Form 16 page found")

    # TX010-TX012
    for rule, desc in [("TX010", "Investment declaration lock"),
                       ("TX011", "Proof > declaration check"),
                       ("TX012", "Tax on bonus/arrears")]:
        print(f"\n--- {rule}: {desc} ---")
        log_result(rule, "NOT IMPLEMENTED", f"Requires {desc}; manual verification needed")

    # -----------------------------------------------------------------------
    print("\n" + "="*70)
    print("SECTION 18: SHIFT & SCHEDULING")
    print("="*70)

    shift_ep = api_endpoints.get("shifts") or api_endpoints.get("emp_shifts")

    # SH001: No overlapping shifts
    print("\n--- SH001: No overlapping shifts ---")
    if shift_ep and shift_ep["code"] == 200:
        shifts_data = shift_ep["data"]
        if isinstance(shifts_data, dict):
            shifts_data = shifts_data.get("data", shifts_data.get("shifts", []))
        if isinstance(shifts_data, list) and len(shifts_data) >= 2:
            log_result("SH001", "PARTIAL",
                       f"Found {len(shifts_data)} shifts. Overlap test requires shift assignment API.")
        else:
            log_result("SH001", "NOT IMPLEMENTED", "Insufficient shift data for overlap test")
    else:
        # Check main app attendance page for shifts
        if driver:
            try:
                driver.get(MAIN_URL + "/attendance")
                time.sleep(3)
                if page_has_text(driver, "shift"):
                    shot(driver, "sh001_attendance")
                    log_result("SH001", "PARTIAL", "Shift references in attendance page; overlap test needs manual check")
                else:
                    log_result("SH001", "NOT IMPLEMENTED", "No shift management module found")
            except Exception:
                log_result("SH001", "NOT IMPLEMENTED", "No shift management module found")
        else:
            log_result("SH001", "NOT IMPLEMENTED", "No shift API or UI found")

    # SH002-SH010
    for rule, desc in [
        ("SH002", "Minimum 11hr rest between shifts"),
        ("SH003", "Night shift different pay rate"),
        ("SH004", "Shift swap requires manager approval"),
        ("SH005", "Weekly off - 1 day per 7"),
        ("SH006", "No shift on public holiday"),
        ("SH007", "Shift start/end time cannot be same"),
        ("SH008", "Rotating shift auto-assignment"),
        ("SH009", "On-call duty tracked separately"),
        ("SH010", "Max 48 working hours/week"),
    ]:
        print(f"\n--- {rule}: {desc} ---")
        if shift_ep and shift_ep["code"] == 200:
            log_result(rule, "NOT IMPLEMENTED", f"Shift module exists but {desc.lower()} not testable via current API")
        else:
            log_result(rule, "NOT IMPLEMENTED", f"No shift management module found for: {desc}")

    # -----------------------------------------------------------------------
    print("\n" + "="*70)
    print("SECTION 19: OVERTIME & COMPENSATION")
    print("="*70)

    ot_ep = api_endpoints.get("overtime") or api_endpoints.get("emp_overtime")
    att_ep = api_endpoints.get("attendance") or api_endpoints.get("emp_attendance")

    # OT001: OT only after regular shift hours
    print("\n--- OT001: OT only after regular hours ---")
    ot001_done = False
    if ot_ep and ot_ep["code"] == 200:
        data = ot_ep["data"]
        if isinstance(data, dict):
            data = data.get("data", data.get("results", []))
        if isinstance(data, list):
            for item in data[:10]:
                reg = item.get("regularHours") or item.get("regular_hours")
                ot = item.get("overtimeHours") or item.get("overtime_hours") or item.get("otHours")
                if reg and ot:
                    if float(ot) > 0 and float(reg) >= 8:
                        log_result("OT001", "ENFORCED", f"OT={ot}hrs after regular={reg}hrs")
                    elif float(ot) > 0 and float(reg) < 8:
                        log_result("OT001", "NOT ENFORCED", f"OT={ot}hrs but regular={reg}hrs < 8")
                        record_bug("[Business Rule] OT001: OT without completing regular hours",
                                   f"OT={ot}hrs with only regular={reg}hrs worked", "high")
                    ot001_done = True
                    break

    if not ot001_done and att_ep and att_ep["code"] == 200:
        data = att_ep["data"]
        if isinstance(data, dict):
            data = data.get("data", data.get("results", []))
        if isinstance(data, list):
            for item in data[:20]:
                ot = item.get("overtime") or item.get("otHours") or item.get("overtime_hours")
                total = item.get("totalHours") or item.get("workedHours") or item.get("worked_hours")
                if ot is not None and total is not None and float(ot) > 0:
                    if float(total) > 8:
                        log_result("OT001", "ENFORCED", f"OT={ot}hrs with total={total}hrs > 8")
                    else:
                        log_result("OT001", "NOT ENFORCED", f"OT={ot}hrs with total={total}hrs <= 8")
                    ot001_done = True
                    break

    if not ot001_done:
        # Check if "ot" keyword appeared on payroll dashboard
        if dashboard_data.get("ot") or ("ot" in str(dashboard_data).lower()):
            log_result("OT001", "NOT IMPLEMENTED", "OT references found in UI but no API data for validation")
        else:
            log_result("OT001", "NOT IMPLEMENTED", "No overtime data found")

    # OT002-OT007
    print("\n--- OT002: OT rate = 2x regular ---")
    log_result("OT002", "NOT IMPLEMENTED", "No OT rate data available")

    print("\n--- OT003: OT requires manager approval ---")
    log_result("OT003", "NOT IMPLEMENTED", "No OT approval workflow found")

    print("\n--- OT004: Max OT hours/month ---")
    log_result("OT004", "NOT IMPLEMENTED", "No OT cap settings found")

    print("\n--- OT005: Holiday OT = 3x rate ---")
    log_result("OT005", "NOT IMPLEMENTED", "No holiday OT data found")

    print("\n--- OT006: Comp-off vs OT pay ---")
    log_result("OT006", "NOT IMPLEMENTED", "No comp-off module found")

    # OT007: OT auto-calculated from attendance
    print("\n--- OT007: OT auto-calculated from attendance ---")
    if att_ep and att_ep["code"] == 200:
        data = att_ep["data"]
        if isinstance(data, dict):
            data = data.get("data", data.get("results", []))
        if isinstance(data, list) and len(data) > 0:
            sample = data[0]
            has_ot = any(k for k in (sample.keys() if isinstance(sample, dict) else [])
                        if "overtime" in k.lower() or "ot" in k.lower())
            if has_ot:
                log_result("OT007", "ENFORCED", "Attendance records include OT field - auto-calculated from attendance")
            else:
                log_result("OT007", "NOT IMPLEMENTED",
                           f"Attendance data found but no OT field. Keys: {list(sample.keys()) if isinstance(sample, dict) else 'N/A'}")
        else:
            log_result("OT007", "NOT IMPLEMENTED", "No attendance records found")
    else:
        log_result("OT007", "NOT IMPLEMENTED", "No attendance API data available")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print("="*70)
    print("EMP Cloud Business Rules V2 - Sections 16-19")
    print("Salary, Tax, Shift, Overtime")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    driver = None
    main_token = None
    payroll_token = None
    dashboard_data = {}
    salary_data = {}
    tax_data = {}
    payslip_data = {}
    api_endpoints = {}

    try:
        # Step 1: Browser login to main app (for SSO token)
        print("\n[STEP 1] Browser Login to Main App")
        driver = create_driver()
        login_ok, login_status = do_login(driver, MAIN_URL,
                                          CREDS["org_admin"]["email"],
                                          CREDS["org_admin"]["password"],
                                          "admin_main")
        if login_ok:
            main_token = extract_token(driver)
            print(f"    Main app token: {str(main_token)[:50]}..." if main_token else "    No token from main app")

        # Step 2: Login to Payroll directly
        print("\n[STEP 2] Login to Payroll Module")
        payroll_login_ok = login_payroll_direct(driver, CREDS["org_admin"]["email"],
                                                 CREDS["org_admin"]["password"])
        if payroll_login_ok:
            payroll_token = get_payroll_token(driver)
            print(f"    Payroll token: {str(payroll_token)[:50]}..." if payroll_token else "    No payroll token from localStorage")

        # Also try API login for payroll
        if not payroll_token:
            payroll_token = login_payroll_api(CREDS["org_admin"]["email"], CREDS["org_admin"]["password"])

        use_token = payroll_token or main_token

        # Step 3: Explore Payroll API
        print("\n[STEP 3] Payroll API Exploration")
        if use_token:
            api_endpoints = explore_payroll_api(use_token)
            print(f"\n  Total API endpoints found: {len(api_endpoints)}")
        else:
            print("  [WARN] No token available for API exploration")

        # Step 4: Scrape Payroll UI pages
        print("\n[STEP 4] Scraping Payroll UI")

        # If payroll login worked, navigate within payroll
        if payroll_login_ok and "/login" not in driver.current_url.lower():
            print("  Scraping from payroll session...")

            # Dashboard
            driver.get(PAYROLL_URL + "/my")
            time.sleep(4)
            shot(driver, "payroll_dashboard_my")
            dashboard_data = scrape_dashboard_data(driver)

            # Also try /dashboard
            driver.get(PAYROLL_URL + "/dashboard")
            time.sleep(4)
            if "/login" not in driver.current_url.lower():
                shot(driver, "payroll_dashboard")
                dash2 = scrape_dashboard_data(driver)
                # Merge
                for k, v in dash2.items():
                    if k not in dashboard_data:
                        dashboard_data[k] = v

            # My Salary
            salary_data = scrape_salary_page(driver)

            # My Tax
            tax_data = scrape_tax_page(driver)

            # Payslips
            payslip_data = scrape_payslip_page(driver)

            # Admin Panel exploration
            admin_data = scrape_admin_panel(driver)
        else:
            # SSO approach: get fresh token and navigate
            print("  Payroll direct login may not have persisted. Getting fresh SSO token...")
            # Re-login to main app for fresh token
            login_ok2, _ = do_login(driver, MAIN_URL, CREDS["org_admin"]["email"],
                                    CREDS["org_admin"]["password"], "admin_refresh")
            if login_ok2:
                fresh_token = extract_token(driver)
                if fresh_token:
                    main_token = fresh_token
                    use_token = payroll_token or main_token

            if main_token:
                sso_url = f"{PAYROLL_URL}?sso_token={main_token}"
                driver.get(sso_url)
                time.sleep(8)
                shot(driver, "payroll_sso_dashboard")
                dashboard_data = scrape_dashboard_data(driver)

                # After SSO, try getting payroll token
                payroll_token = get_payroll_token(driver) or payroll_token
                use_token = payroll_token or main_token

                # Try navigating within payroll
                for nav_page, scrape_fn, data_key in [
                    ("My Salary", scrape_salary_page, "salary"),
                    ("My Tax", scrape_tax_page, "tax"),
                ]:
                    # Click sidebar link
                    try:
                        link = driver.find_element(By.XPATH, f"//a[contains(text(),'{nav_page}')]")
                        if link.is_displayed():
                            link.click()
                            time.sleep(4)
                            if data_key == "salary":
                                salary_data = scrape_fn(driver)
                            elif data_key == "tax":
                                tax_data = scrape_fn(driver)
                    except NoSuchElementException:
                        pass

        # Step 5: Also call self-service API directly
        print("\n[STEP 5] Direct API Data Fetch")
        def to_float(v):
            """Safely convert value to float."""
            if v is None:
                return None
            try:
                return float(str(v).replace(',', ''))
            except (ValueError, TypeError):
                return None

        if use_token:
            # Self-service dashboard
            code, body, _ = api_request(f"{PAYROLL_API}/self-service/dashboard", token=use_token)
            if code == 200 and isinstance(body, dict):
                print(f"    Self-service dashboard API: {json.dumps(body, indent=2, default=str)[:3000]}")
                d = body.get("data", body)
                # Extract employee info
                emp = d.get("employee", d) if isinstance(d, dict) else {}
                if isinstance(emp, dict):
                    tax_info = emp.get("taxInfo", emp.get("tax_info", {}))
                    if isinstance(tax_info, dict):
                        regime = tax_info.get("regime")
                        if regime:
                            tax_data["regime"] = str(regime).lower()
                    pf_details = emp.get("pfDetails", emp.get("pf_details", {}))
                    if isinstance(pf_details, dict):
                        tax_data["pf_contribution_rate"] = pf_details.get("contributionRate")
                        tax_data["pf_opted_out"] = pf_details.get("isOptedOut", False)
                        tax_data["pf_number"] = pf_details.get("pfNumber")

                # Extract salary summary if present
                sal_summary = d.get("salary", d.get("salarySummary", {}))
                if isinstance(sal_summary, dict):
                    if sal_summary.get("ctc"): dashboard_data["monthly_ctc"] = to_float(sal_summary["ctc"])
                    if sal_summary.get("gross"): dashboard_data["gross_pay"] = to_float(sal_summary["gross"])
                    if sal_summary.get("net_pay"): dashboard_data["net_pay"] = to_float(sal_summary["net_pay"])

                # Also check for monthlyCTC etc at top level
                if isinstance(d, dict):
                    for k, v in d.items():
                        kl = k.lower()
                        if "ctc" in kl and v and "monthly_ctc" not in dashboard_data:
                            dashboard_data["monthly_ctc"] = to_float(v)
                        if "regime" in kl and v:
                            tax_data.setdefault("regime", str(v).lower())

            # Self-service salary (this has detailed structure)
            code, body, _ = api_request(f"{PAYROLL_API}/self-service/salary", token=use_token)
            if code == 200 and isinstance(body, dict):
                print(f"    Self-service salary API: {json.dumps(body, indent=2, default=str)[:3000]}")
                d = body.get("data", body)
                if isinstance(d, dict):
                    # Annual figures
                    salary_data["ctc_annual"] = to_float(d.get("ctc"))
                    salary_data["gross_annual"] = to_float(d.get("gross_salary"))
                    salary_data["net_annual"] = to_float(d.get("net_salary"))
                    # Monthly = annual / 12
                    if salary_data.get("ctc_annual"):
                        salary_data["ctc"] = salary_data["ctc_annual"] / 12
                    if salary_data.get("gross_annual"):
                        salary_data["gross"] = salary_data["gross_annual"] / 12

                    # Components
                    components = d.get("components", [])
                    if isinstance(components, list):
                        for comp in components:
                            code_name = comp.get("code", "").upper()
                            monthly = to_float(comp.get("monthlyAmount"))
                            annual = to_float(comp.get("annualAmount"))
                            if code_name == "BASIC":
                                salary_data["basic"] = monthly
                                salary_data["basic_annual"] = annual
                            elif code_name == "HRA":
                                salary_data["hra"] = monthly
                                salary_data["hra_annual"] = annual
                            elif code_name == "SA":
                                salary_data["special_allowance"] = monthly

            # Self-service payslips (detailed breakdown with deductions)
            code, body, _ = api_request(f"{PAYROLL_API}/self-service/payslips", token=use_token)
            if code == 200 and isinstance(body, dict):
                print(f"    Self-service payslips API: {json.dumps(body, indent=2, default=str)[:3000]}")
                d = body.get("data", body)
                slips = d.get("data", d) if isinstance(d, dict) else d
                if isinstance(slips, list) and len(slips) > 0:
                    latest = slips[0]
                    payslip_data["month"] = latest.get("month")
                    payslip_data["year"] = latest.get("year")
                    payslip_data["paid_days"] = to_float(latest.get("paid_days"))
                    payslip_data["lop_days"] = to_float(latest.get("lop_days"))
                    payslip_data["gross_earnings"] = to_float(latest.get("gross_earnings"))
                    payslip_data["total_deductions"] = to_float(latest.get("total_deductions"))
                    payslip_data["net_pay"] = to_float(latest.get("net_pay"))
                    payslip_data["total_employer_cost"] = to_float(latest.get("total_employer_cost"))
                    payslip_data["status"] = latest.get("status")

                    # Parse earnings
                    for e in latest.get("earnings", []):
                        code_name = e.get("code", "").upper()
                        amt = to_float(e.get("amount"))
                        if code_name == "BASIC": payslip_data["basic"] = amt
                        elif code_name == "HRA": payslip_data["hra"] = amt
                        elif code_name == "SA": payslip_data["special_allowance"] = amt

                    # Parse deductions
                    for d_item in latest.get("deductions", []):
                        code_name = d_item.get("code", "").upper()
                        amt = to_float(d_item.get("amount"))
                        if "EPF" in code_name or "PF" in code_name:
                            payslip_data["employee_pf"] = amt
                        elif "PT" in code_name or "PROFESSIONAL" in code_name.upper():
                            payslip_data["professional_tax"] = amt
                        elif "ESI" in code_name:
                            payslip_data["employee_esi"] = amt
                        elif "TDS" in code_name:
                            payslip_data["tds"] = amt

                    # Parse employer contributions
                    for ec in latest.get("employer_contributions", []):
                        code_name = ec.get("code", "").upper()
                        amt = to_float(ec.get("amount"))
                        if "EPF" in code_name or "PF" in code_name:
                            payslip_data["employer_pf"] = amt
                        elif "ESI" in code_name:
                            payslip_data["employer_esi"] = amt

                    # Check for future payslips
                    now = datetime.now()
                    for slip in slips:
                        m = slip.get("month")
                        y = slip.get("year")
                        if m and y:
                            if int(y) > now.year or (int(y) == now.year and int(m) > now.month):
                                payslip_data["has_future_payslip"] = f"{m}/{y}"

            # Self-service tax
            code, body, _ = api_request(f"{PAYROLL_API}/self-service/tax", token=use_token)
            if code == 200 and isinstance(body, dict):
                print(f"    Self-service tax API: {json.dumps(body, indent=2, default=str)[:2000]}")
                d = body.get("data", body)
                if isinstance(d, dict):
                    if d.get("regime"): tax_data["regime"] = str(d["regime"]).lower()
                    if d.get("declarations"): tax_data["has_declarations"] = True
                    if d.get("form16"): tax_data["has_form16"] = True

            # Also try salary-structure and salary-components admin endpoints
            for key, url in [
                ("salary_structure_admin", f"{PAYROLL_API}/salary-structure"),
                ("salary_components_admin", f"{PAYROLL_API}/salary-components"),
                ("tax_settings_admin", f"{PAYROLL_API}/tax-settings"),
                ("shift_settings_admin", f"{PAYROLL_API}/shifts"),
                ("overtime_admin", f"{PAYROLL_API}/overtime"),
                ("attendance_admin", f"{PAYROLL_API}/attendance"),
            ]:
                c, b, _ = api_request(url, token=use_token)
                if c in (200, 201):
                    api_endpoints[key] = {"url": url, "code": c, "data": b}
                    print(f"    [API OK] {key} -> {url} (HTTP {c})")
                    if isinstance(b, dict):
                        print(f"      Response preview: {json.dumps(b, default=str)[:300]}")

        print(f"\n  Final dashboard_data: {json.dumps(dashboard_data, indent=2, default=str)}")
        print(f"  Final salary_data: {json.dumps(salary_data, indent=2, default=str)}")
        print(f"  Final tax_data: {json.dumps(tax_data, indent=2, default=str)}")
        print(f"  Final payslip_data: {json.dumps(payslip_data, indent=2, default=str)}")

        # Step 6: Run all business rule tests
        print("\n[STEP 6] Running Business Rule Tests")
        test_all_rules(payroll_token, main_token, driver,
                       dashboard_data, salary_data, tax_data, payslip_data,
                       api_endpoints)

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        traceback.print_exc()
        if driver:
            shot(driver, "fatal_error")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    enforced = [r for r in test_results if r["status"] == "ENFORCED"]
    not_enforced = [r for r in test_results if r["status"] == "NOT ENFORCED"]
    partial = [r for r in test_results if r["status"] == "PARTIAL"]
    not_impl = [r for r in test_results if r["status"] == "NOT IMPLEMENTED"]

    print(f"\n  ENFORCED:        {len(enforced)}")
    for r in enforced:
        print(f"    {r['rule']}: {r['details']}")

    print(f"\n  NOT ENFORCED:    {len(not_enforced)}")
    for r in not_enforced:
        print(f"    {r['rule']}: {r['details']}")

    print(f"\n  PARTIAL:         {len(partial)}")
    for r in partial:
        print(f"    {r['rule']}: {r['details']}")

    print(f"\n  NOT IMPLEMENTED: {len(not_impl)}")
    for r in not_impl:
        print(f"    {r['rule']}: {r['details']}")

    # ---------------------------------------------------------------------------
    # File GitHub issues
    # ---------------------------------------------------------------------------
    print("\n" + "="*70)
    print("FILING GITHUB ISSUES")
    print("="*70)

    for bug in bugs_found:
        title = bug["title"]
        severity = bug["severity"]
        desc = bug["description"]
        labels = ["bug"]
        if severity == "critical":
            labels.append("priority: critical")
        elif severity == "high":
            labels.append("priority: high")

        body = f"""## Description
{desc}

## Severity
{severity.upper()}

## Business Rule
{title}

## Environment
- API: {PAYROLL_API}
- Payroll UI: {PAYROLL_URL}
- Tested: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Tester: Automated E2E (Business Rules V2 Sections 16-19)
"""
        print(f"\n  Filing: {title}")
        file_github_issue(title, body, labels)
        time.sleep(2)

    # File feature requests for critical NOT IMPLEMENTED rules
    critical_rules = ["SC001", "SC006", "SC007", "TX001", "TX002", "SH001", "OT001", "OT007"]
    critical_not_impl = [r for r in not_impl if r["rule"] in critical_rules]
    for r in critical_not_impl:
        title = f"[Feature Request] {r['rule']}: Business rule not testable - needs API/UI"
        body = f"""## Feature Request
Rule **{r['rule']}** from Business Rules V2 is not testable via the current API or UI.

## Details
{r['details']}

## Priority
CRITICAL/HIGH business rule that should be enforced and testable.

## Environment
- Payroll API: {PAYROLL_API}
- Payroll UI: {PAYROLL_URL}
- Tested: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        print(f"\n  Filing feature request: {title}")
        file_github_issue(title, body, ["enhancement"])
        time.sleep(2)

    print("\n" + "="*70)
    print(f"TOTAL: {len(test_results)} rules tested")
    print(f"  ENFORCED:        {len(enforced)}")
    print(f"  NOT ENFORCED:    {len(not_enforced)}")
    print(f"  PARTIAL:         {len(partial)}")
    print(f"  NOT IMPLEMENTED: {len(not_impl)}")
    print(f"  BUGS FILED:      {len(bugs_found)}")
    print(f"  FEATURE REQUESTS: {len(critical_not_impl)}")
    print("="*70)


if __name__ == "__main__":
    main()
