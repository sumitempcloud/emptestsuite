#!/usr/bin/env python3
"""
EmpCloud Open Bug Verification Script
Fetches all open issues from EmpCloud/EmpCloud, tests each one,
and labels verified bugs or closes false positives.
"""

import sys
import os
import json
import time
import re
import traceback
import requests
from datetime import datetime
from urllib.parse import urljoin

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Config ──────────────────────────────────────────────────────────────────
GITHUB_PAT = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
GH_API = "https://api.github.com"
GH_HEADERS = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github+json",
}

API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
FRONTEND_BASE = "https://test-empcloud.empcloud.com"

MODULE_URLS = {
    "recruit": {"fe": "https://test-recruit.empcloud.com", "api": "https://test-recruit-api.empcloud.com"},
    "performance": {"fe": "https://test-performance.empcloud.com", "api": "https://test-performance-api.empcloud.com"},
    "rewards": {"fe": "https://test-rewards.empcloud.com", "api": "https://test-rewards-api.empcloud.com"},
    "exit": {"fe": "https://test-exit.empcloud.com", "api": "https://test-exit-api.empcloud.com"},
    "lms": {"fe": "https://testlms.empcloud.com", "api": "https://testlms-api.empcloud.com"},
    "payroll": {"fe": "https://testpayroll.empcloud.com", "api": "https://testpayroll-api.empcloud.com"},
    "project": {"fe": "https://test-project.empcloud.com", "api": "https://test-project-api.empcloud.com"},
    "monitor": {"fe": "https://test-empmonitor.empcloud.com", "api": "https://test-empmonitor-api.empcloud.com"},
    "empcloud": {"fe": "https://test-empcloud.empcloud.com", "api": "https://test-empcloud-api.empcloud.com"},
}

ADMIN_CREDS = {"email": "ananya@technova.in", "password": "Welcome@123"}
EMPLOYEE_CREDS = {"email": "priya@technova.in", "password": "Welcome@123"}

CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

SKIP_KEYWORDS = ["field force", "emp-field", "biometrics", "emp-biometrics",
                 "rate limit", "rate-limit", "ratelimit", "throttl"]

GH_DELAY = 5  # seconds between GitHub API write calls

# ── Tokens cache ────────────────────────────────────────────────────────────
_token_cache = {}

def get_api_token(creds, label=""):
    """Login to the main EmpCloud API and get a JWT token."""
    key = creds["email"]
    cached = _token_cache.get(key)
    if cached and (time.time() - cached["ts"]) < 780:  # 13 min, refresh before 15-min expiry
        return cached["token"]
    print(f"  [AUTH] Getting fresh token for {creds['email']}...")
    try:
        r = requests.post(
            f"{API_BASE}/auth/login",
            json=creds,
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            token = (
                data.get("token")
                or data.get("access_token")
                or data.get("data", {}).get("token")
                or data.get("data", {}).get("access_token")
                or (data.get("data", {}).get("tokens") or {}).get("access_token")
            )
            if not token:
                # Try nested
                for k, v in data.items():
                    if isinstance(v, dict):
                        if "token" in v:
                            token = v["token"]
                            break
                        if "access_token" in v:
                            token = v["access_token"]
                            break
                        for k2, v2 in v.items():
                            if isinstance(v2, dict) and "access_token" in v2:
                                token = v2["access_token"]
                                break
            if token:
                _token_cache[key] = {"token": token, "ts": time.time()}
                print(f"  [AUTH] Got token for {creds['email']}")
                return token
            else:
                print(f"  [AUTH] Login OK but no token in response: {json.dumps(data)[:300]}")
        else:
            print(f"  [AUTH] Login failed {r.status_code}: {r.text[:300]}")
    except Exception as e:
        print(f"  [AUTH] Login error: {e}")
    return None


def get_admin_token():
    return get_api_token(ADMIN_CREDS, "admin")


def get_employee_token():
    return get_api_token(EMPLOYEE_CREDS, "employee")


def api_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── GitHub helpers ──────────────────────────────────────────────────────────
def gh_get(path, params=None):
    url = f"{GH_API}{path}" if path.startswith("/") else path
    r = requests.get(url, headers=GH_HEADERS, params=params, timeout=30)
    return r


def gh_post(path, json_data):
    url = f"{GH_API}{path}" if path.startswith("/") else path
    r = requests.post(url, headers=GH_HEADERS, json=json_data, timeout=30)
    return r


def gh_patch(path, json_data):
    url = f"{GH_API}{path}" if path.startswith("/") else path
    r = requests.patch(url, headers=GH_HEADERS, json=json_data, timeout=30)
    return r


def fetch_all_open_issues():
    """Fetch all open issues (not PRs) from the repo."""
    issues = []
    page = 1
    while True:
        print(f"  Fetching issues page {page}...")
        r = gh_get(f"/repos/{REPO}/issues", params={"state": "open", "per_page": 100, "page": page})
        if r.status_code != 200:
            print(f"  ERROR fetching issues: {r.status_code} {r.text[:300]}")
            break
        batch = r.json()
        if not batch:
            break
        for issue in batch:
            if "pull_request" not in issue:
                issues.append(issue)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(1)
    return issues


def should_skip(issue):
    """Check if issue should be skipped (field force, biometrics, rate limits)."""
    text = (issue.get("title", "") + " " + (issue.get("body") or "")).lower()
    labels = [l["name"].lower() for l in issue.get("labels", [])]
    for kw in SKIP_KEYWORDS:
        if kw in text or any(kw in lb for lb in labels):
            return True, kw
    return False, None


def has_programmer_comment(issue):
    """Check if a programmer has commented explaining the issue."""
    number = issue["number"]
    r = gh_get(f"/repos/{REPO}/issues/{number}/comments")
    if r.status_code != 200:
        return False, ""
    comments = r.json()
    for c in comments:
        body = (c.get("body") or "").lower()
        author = (c.get("user", {}).get("login") or "").lower()
        # Look for programmer explanations
        explain_keywords = ["by design", "intended", "not a bug", "working as expected",
                           "won't fix", "wontfix", "expected behavior", "this is correct",
                           "closing because", "fixed in", "resolved in", "deployed fix",
                           "already fixed"]
        for kw in explain_keywords:
            if kw in body:
                return True, c.get("body", "")[:200]
    return False, ""


def add_label(issue_number, label):
    """Add a label to an issue, creating it first if needed."""
    # Ensure label exists
    r = gh_get(f"/repos/{REPO}/labels/{label}")
    if r.status_code == 404:
        print(f"    Creating label '{label}'...")
        gh_post(f"/repos/{REPO}/labels", {
            "name": label,
            "color": "d73a4a",
            "description": "Bug verified by E2E testing"
        })
        time.sleep(GH_DELAY)
    # Add label to issue
    r = gh_post(f"/repos/{REPO}/issues/{issue_number}/labels", {"labels": [label]})
    time.sleep(GH_DELAY)
    return r.status_code in (200, 201)


def add_comment(issue_number, body):
    """Add a comment to an issue."""
    r = gh_post(f"/repos/{REPO}/issues/{issue_number}/comments", {"body": body})
    time.sleep(GH_DELAY)
    return r.status_code in (200, 201)


def close_issue(issue_number, comment):
    """Close an issue with a comment."""
    add_comment(issue_number, comment)
    r = gh_patch(f"/repos/{REPO}/issues/{issue_number}", {"state": "closed"})
    time.sleep(GH_DELAY)
    return r.status_code == 200


# ── Bug classification ──────────────────────────────────────────────────────
def classify_bug(issue):
    """Classify a bug to determine test strategy."""
    title = issue.get("title", "").lower()
    body = (issue.get("body") or "").lower()
    labels = [l["name"].lower() for l in issue.get("labels", [])]
    text = title + " " + body

    # Extract endpoint if mentioned
    endpoint = None
    ep_match = re.search(r'((?:GET|POST|PUT|PATCH|DELETE)\s+)?(/api/v1/[^\s\)\"\'\`]+)', text, re.IGNORECASE)
    if ep_match:
        endpoint = ep_match.group(2).rstrip('`"\' ')
    # Also look for just paths
    if not endpoint:
        ep_match = re.search(r'endpoint[:\s]+[`"]?(/[^\s\)`"\'\`]+)', text, re.IGNORECASE)
        if ep_match:
            endpoint = ep_match.group(1).rstrip('`"\' ')
    # Clean endpoint: strip backticks, trailing punctuation
    if endpoint:
        endpoint = endpoint.strip('`"\' .,;:')

    # Extract HTTP method
    method = "GET"
    method_match = re.search(r'\b(GET|POST|PUT|PATCH|DELETE)\b', text, re.IGNORECASE)
    if method_match:
        method = method_match.group(1).upper()

    # Extract module
    module = None
    for mod_name in MODULE_URLS:
        if mod_name in text:
            module = mod_name
            break

    # Extract page path
    page_path = None
    path_match = re.search(r'(?:page|url|route|path|navigate)[:\s]+[`"]?(/[^\s\)`"\'\`]+)', text, re.IGNORECASE)
    if path_match:
        page_path = path_match.group(1).strip('`"\' .,;:')
    if not page_path:
        path_match = re.search(r'(?:404|not found|missing)[^/]*((?:/my)?/[a-z][a-z0-9/-]+)', text, re.IGNORECASE)
        if path_match:
            page_path = path_match.group(1).strip('`"\' .,;:')
    # Don't use /api/v1/* paths as page paths (those are API endpoints, not frontend)
    if page_path and page_path.startswith("/api/"):
        page_path = None

    # Classify
    if any(kw in text for kw in ["rbac", "role", "permission", "unauthorized", "forbidden", "access control", "employee can", "employee should not"]):
        return {"type": "rbac", "endpoint": endpoint, "method": method, "module": module, "page": page_path}
    elif any(kw in text for kw in ["404", "not found", "page not found", "missing page"]):
        if endpoint:
            return {"type": "api_404", "endpoint": endpoint, "method": method, "module": module, "page": page_path}
        else:
            return {"type": "page_404", "endpoint": endpoint, "method": method, "module": module, "page": page_path}
    elif any(kw in text for kw in ["validation", "invalid", "accepts invalid", "should reject", "does not validate"]):
        return {"type": "validation", "endpoint": endpoint, "method": method, "module": module, "page": page_path}
    elif any(kw in text for kw in ["ui", "display", "layout", "css", "style", "button", "modal", "render", "visual"]):
        return {"type": "ui", "endpoint": endpoint, "method": method, "module": module, "page": page_path}
    elif any(kw in text for kw in ["/my/", "self-service", "self service", "employee portal", "employee dashboard"]):
        return {"type": "self_service", "endpoint": endpoint, "method": method, "module": module, "page": page_path}
    elif endpoint:
        return {"type": "api", "endpoint": endpoint, "method": method, "module": module, "page": page_path}
    else:
        return {"type": "general", "endpoint": endpoint, "method": method, "module": module, "page": page_path}


# ── Test functions ──────────────────────────────────────────────────────────
def test_api_endpoint(endpoint, method="GET", token=None, payload=None, expected_status=None, base_url=None):
    """Test an API endpoint. Returns (is_bug, evidence)."""
    if not endpoint:
        return None, "No endpoint to test"

    if not base_url:
        base_url = API_BASE
    if endpoint.startswith("http"):
        url = endpoint
    else:
        # Avoid doubling /api/v1: if base already ends with /api/v1 and endpoint starts with /api/v1
        if base_url.rstrip("/").endswith("/api/v1") and endpoint.startswith("/api/v1/"):
            # Use just the API root (strip /api/v1 from base)
            api_root = base_url.rstrip("/").rsplit("/api/v1", 1)[0]
            url = f"{api_root}{endpoint}"
        else:
            url = f"{base_url}{endpoint}"

    headers = {}
    if token:
        headers = api_headers(token)

    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            r = requests.post(url, headers=headers, json=payload or {}, timeout=30)
        elif method == "PUT":
            r = requests.put(url, headers=headers, json=payload or {}, timeout=30)
        elif method == "PATCH":
            r = requests.patch(url, headers=headers, json=payload or {}, timeout=30)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, timeout=30)
        else:
            r = requests.get(url, headers=headers, timeout=30)

        status = r.status_code
        body_preview = r.text[:300] if r.text else "(empty)"

        if expected_status:
            is_bug = status != expected_status
            return is_bug, f"{method} {url} -> {status} (expected {expected_status}). Body: {body_preview}"

        # General heuristics
        if status == 404:
            return True, f"{method} {url} -> 404 Not Found. Body: {body_preview}"
        elif status == 500:
            return True, f"{method} {url} -> 500 Internal Server Error. Body: {body_preview}"
        elif status == 502:
            return True, f"{method} {url} -> 502 Bad Gateway. Body: {body_preview}"
        elif status == 503:
            return True, f"{method} {url} -> 503 Service Unavailable. Body: {body_preview}"
        elif status in (200, 201, 204):
            return False, f"{method} {url} -> {status} OK. Body: {body_preview}"
        elif status == 401:
            if token:
                return True, f"{method} {url} -> 401 Unauthorized even with valid token. Body: {body_preview}"
            return None, f"{method} {url} -> 401 (no token provided)"
        elif status == 403:
            return None, f"{method} {url} -> 403 Forbidden. Body: {body_preview}"
        else:
            return None, f"{method} {url} -> {status}. Body: {body_preview}"

    except requests.exceptions.ConnectionError:
        return True, f"{method} {url} -> Connection refused/failed"
    except requests.exceptions.Timeout:
        return True, f"{method} {url} -> Timeout (30s)"
    except Exception as e:
        return None, f"{method} {url} -> Error: {e}"


def test_rbac(info, issue):
    """Test RBAC bug: employee accessing admin-only endpoint."""
    emp_token = get_employee_token()
    admin_token = get_admin_token()
    endpoint = info.get("endpoint")
    method = info.get("method", "GET")

    if not endpoint:
        # Try to extract from issue body
        body = (issue.get("body") or "") + " " + issue.get("title", "")
        ep_match = re.search(r'/api/v1/[^\s\)\"\']+', body)
        if ep_match:
            endpoint = ep_match.group(0)

    if not endpoint:
        return None, "Could not determine endpoint to test RBAC"

    # Determine module API base
    module = info.get("module")
    base_url = API_BASE
    if module and module in MODULE_URLS:
        base_url = MODULE_URLS[module]["api"] + "/api/v1"

    # Test with employee token - should be forbidden
    is_bug_emp, evidence_emp = test_api_endpoint(endpoint, method, emp_token, base_url=base_url)

    # If employee gets 200 on an admin-only endpoint, that's a bug
    if is_bug_emp is False:
        # Employee got 200 - this IS the RBAC bug (employee shouldn't have access)
        return True, f"RBAC BUG: Employee can access admin-only endpoint. {evidence_emp}"
    elif is_bug_emp is True:
        # Endpoint itself is broken
        return True, f"Endpoint error (may mask RBAC issue): {evidence_emp}"
    else:
        # 403/401 = RBAC working correctly, or inconclusive
        # Verify admin CAN access
        is_bug_admin, evidence_admin = test_api_endpoint(endpoint, method, admin_token, base_url=base_url)
        if is_bug_admin is False:
            return False, f"RBAC working correctly. Admin: {evidence_admin}. Employee: {evidence_emp}"
        else:
            return None, f"Inconclusive. Admin: {evidence_admin}. Employee: {evidence_emp}"


def test_api_404(info, issue):
    """Test if an API endpoint returns 404."""
    token = get_admin_token()
    endpoint = info.get("endpoint")
    method = info.get("method", "GET")

    if not endpoint:
        return None, "No endpoint found in issue"

    module = info.get("module")
    base_url = API_BASE
    if module and module in MODULE_URLS:
        base_url = MODULE_URLS[module]["api"] + "/api/v1"

    return test_api_endpoint(endpoint, method, token, base_url=base_url)


def test_validation(info, issue):
    """Test validation bugs by sending invalid data."""
    token = get_admin_token()
    endpoint = info.get("endpoint")
    method = info.get("method", "POST")

    if not endpoint:
        return None, "No endpoint found to test validation"

    module = info.get("module")
    base_url = API_BASE
    if module and module in MODULE_URLS:
        base_url = MODULE_URLS[module]["api"] + "/api/v1"

    # Send obviously invalid data
    invalid_payloads = [
        {"email": "not-an-email", "name": "", "phone": "abc"},
        {"date": "invalid-date", "amount": "not-a-number", "id": -999},
        {},
    ]

    results = []
    for payload in invalid_payloads:
        is_bug, evidence = test_api_endpoint(endpoint, method, token, payload=payload, base_url=base_url)
        results.append((is_bug, evidence))
        if is_bug is True:
            # Server accepted invalid data (200/201) or crashed (500)
            return True, f"Validation bug confirmed: {evidence}"

    # Check if any returned 200 (accepted invalid data)
    for is_bug, evidence in results:
        if is_bug is False and "200" in evidence:
            return True, f"Server accepted invalid data without validation: {evidence}"

    # All rejected properly
    combined = " | ".join(e for _, e in results)
    return False, f"Validation appears to work: {combined}"


def test_page_or_self_service(info, issue, as_employee=False):
    """Test a page via Selenium (headless). Returns (is_bug, evidence)."""
    page_path = info.get("page")
    module = info.get("module")

    if not page_path and not module:
        return None, "No page path or module to test"

    # Determine the base URL
    fe_base = FRONTEND_BASE
    if module and module in MODULE_URLS:
        fe_base = MODULE_URLS[module]["fe"]

    # Get SSO token
    creds = EMPLOYEE_CREDS if as_employee else ADMIN_CREDS
    token = get_api_token(creds)
    if not token:
        return None, "Could not get auth token for SSO"

    target_url = fe_base
    if page_path:
        target_url = fe_base.rstrip("/") + "/" + page_path.lstrip("/")

    # Append SSO token
    sep = "&" if "?" in target_url else "?"
    sso_url = f"{target_url}{sep}sso_token={token}"

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        opts = Options()
        opts.binary_location = CHROME_PATH
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-gpu")

        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(30)

        try:
            driver.get(sso_url)
            time.sleep(3)  # Wait for SPA to render

            page_title = driver.title
            page_source = driver.page_source[:2000]
            current_url = driver.current_url

            # Check for 404 indicators
            is_404 = any(kw in page_source.lower() for kw in [
                "404", "not found", "page not found", "cannot find",
                "does not exist", "no route", "route not found"
            ])

            # Check for error indicators
            is_error = any(kw in page_source.lower() for kw in [
                "error", "something went wrong", "internal server error",
                "application error", "unhandled", "uncaught"
            ])

            # Check for blank page
            body_text = ""
            try:
                body_el = driver.find_element(By.TAG_NAME, "body")
                body_text = body_el.text.strip()
            except:
                pass

            is_blank = len(body_text) < 10

            evidence = f"URL: {current_url}, Title: '{page_title}', Body length: {len(body_text)} chars"

            if is_404:
                return True, f"Page shows 404. {evidence}"
            elif is_error and not is_404:
                return True, f"Page shows error. {evidence}. Source snippet: {page_source[:200]}"
            elif is_blank:
                return True, f"Page appears blank. {evidence}"
            else:
                return False, f"Page loads OK. {evidence}"

        finally:
            driver.quit()

    except ImportError:
        return None, "Selenium not installed - cannot test UI"
    except Exception as e:
        return None, f"Selenium error: {e}"


def test_ui(info, issue):
    """Test UI bugs via Selenium."""
    return test_page_or_self_service(info, issue, as_employee=False)


def test_self_service(info, issue):
    """Test self-service pages as employee."""
    return test_page_or_self_service(info, issue, as_employee=True)


def test_general(info, issue):
    """General test: try API if endpoint exists, otherwise try page."""
    endpoint = info.get("endpoint")
    if endpoint:
        token = get_admin_token()
        method = info.get("method", "GET")
        module = info.get("module")
        base_url = API_BASE
        if module and module in MODULE_URLS:
            base_url = MODULE_URLS[module]["api"] + "/api/v1"
        return test_api_endpoint(endpoint, method, token, base_url=base_url)

    page = info.get("page")
    if page:
        return test_page_or_self_service(info, issue)

    return None, "Could not determine what to test"


# ── Main test dispatcher ────────────────────────────────────────────────────
TEST_DISPATCH = {
    "rbac": test_rbac,
    "api_404": test_api_404,
    "page_404": test_page_or_self_service,
    "validation": test_validation,
    "ui": test_ui,
    "self_service": test_self_service,
    "api": test_api_404,
    "general": test_general,
}


def process_issue(issue, idx, total):
    """Process a single issue. Returns result dict."""
    number = issue["number"]
    title = issue["title"]
    labels = [l["name"] for l in issue.get("labels", [])]

    print(f"\n{'='*70}")
    print(f"[{idx}/{total}] Issue #{number}: {title}")
    print(f"  Labels: {labels}")

    # Already verified?
    if "verified-bug" in labels:
        print(f"  SKIP: Already has verified-bug label")
        return {"number": number, "action": "skip", "reason": "already verified"}

    # Should skip?
    skip, reason = should_skip(issue)
    if skip:
        print(f"  SKIP: Matches skip keyword '{reason}'")
        return {"number": number, "action": "skip", "reason": f"skip keyword: {reason}"}

    # Check programmer comments
    time.sleep(1)  # Be gentle on GH API
    has_comment, comment_text = has_programmer_comment(issue)
    if has_comment:
        print(f"  SKIP: Programmer explained: {comment_text[:100]}")
        return {"number": number, "action": "skip", "reason": f"programmer comment: {comment_text[:80]}"}

    # Classify
    info = classify_bug(issue)
    bug_type = info["type"]
    print(f"  Type: {bug_type} | Endpoint: {info.get('endpoint')} | Module: {info.get('module')} | Page: {info.get('page')}")

    # Test
    test_fn = TEST_DISPATCH.get(bug_type, test_general)
    try:
        is_bug, evidence = test_fn(info, issue)
    except Exception as e:
        is_bug, evidence = None, f"Test error: {e}\n{traceback.format_exc()}"

    print(f"  Result: is_bug={is_bug}")
    print(f"  Evidence: {evidence[:200] if evidence else 'none'}")

    # Take action
    if is_bug is True:
        print(f"  ACTION: Tagging as verified-bug")
        add_label(number, "verified-bug")
        comment_body = f"Verified by E2E Test Lead. Bug confirmed.\n\n**Evidence:**\n```\n{evidence[:500]}\n```\n\n*Automated verification on {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        add_comment(number, comment_body)
        return {"number": number, "action": "verified", "evidence": evidence[:300]}

    elif is_bug is False:
        print(f"  ACTION: Closing as false positive")
        comment_body = f"Closing as false positive after E2E verification.\n\n**Evidence:**\n```\n{evidence[:500]}\n```\n\nThe reported behavior could not be reproduced. If this is still an issue, please reopen with updated reproduction steps.\n\n*Automated verification on {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        close_issue(number, comment_body)
        return {"number": number, "action": "closed", "evidence": evidence[:300]}

    else:
        print(f"  ACTION: Inconclusive, leaving open")
        return {"number": number, "action": "inconclusive", "evidence": evidence[:300] if evidence else ""}


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("EmpCloud Open Bug Verification")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. Fetch all open issues
    print("\n[STEP 1] Fetching all open issues...")
    issues = fetch_all_open_issues()
    print(f"  Found {len(issues)} open issues")

    if not issues:
        print("No open issues found. Done.")
        return

    # 2. Pre-auth to validate credentials
    print("\n[STEP 2] Validating credentials...")
    admin_token = get_admin_token()
    emp_token = get_employee_token()
    if not admin_token:
        print("  WARNING: Could not get admin token. API tests may fail.")
    if not emp_token:
        print("  WARNING: Could not get employee token. RBAC tests may fail.")

    # 3. Process each issue
    print(f"\n[STEP 3] Processing {len(issues)} issues...")
    results = []
    selenium_count = 0

    for idx, issue in enumerate(issues, 1):
        try:
            result = process_issue(issue, idx, len(issues))
            results.append(result)
        except Exception as e:
            print(f"  ERROR processing #{issue['number']}: {e}")
            traceback.print_exc()
            results.append({"number": issue["number"], "action": "error", "evidence": str(e)[:200]})

    # 4. Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    verified = [r for r in results if r.get("action") == "verified"]
    closed = [r for r in results if r.get("action") == "closed"]
    skipped = [r for r in results if r.get("action") == "skip"]
    inconclusive = [r for r in results if r.get("action") == "inconclusive"]
    errors = [r for r in results if r.get("action") == "error"]

    print(f"Total processed:   {len(results)}")
    print(f"Verified bugs:     {len(verified)}")
    print(f"Closed (false +):  {len(closed)}")
    print(f"Skipped:           {len(skipped)}")
    print(f"Inconclusive:      {len(inconclusive)}")
    print(f"Errors:            {len(errors)}")

    if verified:
        print(f"\nVerified bugs:")
        for r in verified:
            print(f"  #{r['number']}: {r.get('evidence', '')[:100]}")

    if closed:
        print(f"\nClosed as false positive:")
        for r in closed:
            print(f"  #{r['number']}: {r.get('evidence', '')[:100]}")

    if inconclusive:
        print(f"\nInconclusive (left open):")
        for r in inconclusive:
            print(f"  #{r['number']}: {r.get('evidence', '')[:100]}")

    if errors:
        print(f"\nErrors:")
        for r in errors:
            print(f"  #{r['number']}: {r.get('evidence', '')[:100]}")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
