#!/usr/bin/env python3
"""
EmpCloud Closed Bug Re-tester (Batch 2: pages 2-4)
Tests closed GitHub issues via API calls and re-opens those still failing.
"""

import sys
import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import time
import re

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# --- Config ---
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
REPO = "EmpCloud/EmpCloud"
GH_API = f"https://api.github.com/repos/{REPO}"

BASE_URL = "https://test-empcloud.empcloud.com"
API_URL = "https://test-empcloud-api.empcloud.com"

MODULE_APIS = {
    "recruit": "https://test-recruit-api.empcloud.com",
    "performance": "https://test-performance-api.empcloud.com",
    "rewards": "https://test-rewards-api.empcloud.com",
    "exit": "https://test-exit-api.empcloud.com",
    "lms": "https://testlms-api.empcloud.com",
    "payroll": "https://testpayroll-api.empcloud.com",
    "project": "https://test-project-api.empcloud.com",
    "monitor": "https://test-empmonitor-api.empcloud.com",
}

MODULE_FRONTENDS = {
    "recruit": "https://test-recruit.empcloud.com",
    "performance": "https://test-performance.empcloud.com",
    "rewards": "https://test-rewards.empcloud.com",
    "exit": "https://test-exit.empcloud.com",
    "lms": "https://testlms.empcloud.com",
    "payroll": "https://testpayroll.empcloud.com",
    "project": "https://test-project.empcloud.com",
    "monitor": "https://test-empmonitor.empcloud.com",
}

CREDS = {
    "org_admin": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "employee": {"email": "priya@technova.in", "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"},
}

# Skip keywords
SKIP_KEYWORDS = ["rate limit", "rate-limit", "ratelimit", "throttl",
                 "field force", "emp-field", "biometric", "emp-biometric"]

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# --- Helpers ---
def http_request(url, method="GET", data=None, headers=None, timeout=20):
    """Generic HTTP request helper."""
    hdrs = headers or {}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(raw), resp.headers
        except json.JSONDecodeError:
            return resp.status, raw, resp.headers
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(raw), {}
        except json.JSONDecodeError:
            return e.code, raw, {}
    except Exception as e:
        return 0, str(e), {}


def gh_get(path, page=1, per_page=100):
    url = f"{GH_API}{path}"
    sep = "&" if "?" in path else "?"
    url += f"{sep}per_page={per_page}&page={page}"
    return http_request(url, headers={
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
    })


def gh_patch(path, data):
    url = f"{GH_API}{path}"
    return http_request(url, method="PATCH", data=data, headers={
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
    })


def gh_post(path, data):
    url = f"{GH_API}{path}"
    return http_request(url, method="POST", data=data, headers={
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
    })


# --- Auth tokens cache ---
_tokens = {}

def get_token(role="org_admin"):
    if role in _tokens:
        return _tokens[role]
    cred = CREDS[role]
    # Try multiple login endpoints
    login_endpoints = [
        f"{API_URL}/api/v1/auth/login",
        f"{API_URL}/auth/login",
        f"{API_URL}/api/auth/login",
        f"{API_URL}/login",
    ]
    for ep in login_endpoints:
        status, body, hdrs = http_request(ep, method="POST", data={
            "email": cred["email"],
            "password": cred["password"],
        })
        if status in (200, 201) and isinstance(body, dict):
            token = (body.get("token") or body.get("access_token") or
                     body.get("data", {}).get("token") if isinstance(body.get("data"), dict) else None)
            if not token and isinstance(body.get("data"), dict):
                token = body["data"].get("access_token") or body["data"].get("accessToken")
            if token:
                _tokens[role] = token
                return token
    # If no token from those, check cookie-based auth
    return None


def auth_headers(role="org_admin"):
    token = get_token(role)
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def should_skip(issue):
    """Check if issue should be skipped."""
    if issue.get("locked"):
        return True, "locked"
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "").lower()
    labels = [l["name"].lower() for l in issue.get("labels", [])]
    combined = title + " " + body + " " + " ".join(labels)
    for kw in SKIP_KEYWORDS:
        if kw in combined:
            return True, f"skip:{kw}"
    return False, ""


def classify_issue(issue):
    """Classify issue into test category based on title/body keywords."""
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "").lower()
    combined = title + " " + body

    # UI-only issues that need browser
    ui_keywords = ["css", "layout", "alignment", "responsive", "animation",
                   "modal", "popup", "tooltip", "hover", "scroll", "font",
                   "color", "style", "pixel", "display", "visual", "ui ",
                   "sidebar", "navbar", "menu", "button text", "icon",
                   "screenshot", "rendering", "z-index", "overflow",
                   "truncat", "overlap"]
    ui_count = sum(1 for kw in ui_keywords if kw in combined)

    # Categories
    if any(kw in combined for kw in ["login", "auth", "sign in", "signin", "sign-in", "logout", "sign out", "session", "jwt", "token expir"]):
        return "auth"
    if any(kw in combined for kw in ["rbac", "role", "permission", "access control", "unauthorized", "forbidden", "privilege"]):
        return "rbac"
    if any(kw in combined for kw in ["xss", "injection", "sanitiz", "script>", "malicious", "sql inject", "html inject"]):
        return "xss"
    if any(kw in combined for kw in ["404", "not found", "routing", "route", "redirect", "navigation", "broken link", "dead link"]):
        return "routing"
    if any(kw in combined for kw in ["crud", "create", "update", "delete", "add ", "edit ", "remove ", "save",
                                       "employee", "leave", "attendance", "department", "document",
                                       "holiday", "shift", "roster", "payroll", "salary",
                                       "recruit", "candidate", "job", "offer", "performance",
                                       "review", "goal", "reward", "exit", "separation",
                                       "project", "task", "timesheet", "lms", "course", "training"]):
        if ui_count >= 2:
            return "needs-browser-test"
        return "crud"
    if any(kw in combined for kw in ["api", "endpoint", "response", "request", "500", "error", "server error", "status code"]):
        return "api"
    if ui_count >= 1:
        return "needs-browser-test"
    return "api"  # default: try API test


def detect_module(issue):
    """Detect which module the issue relates to."""
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "").lower()
    combined = title + " " + body
    labels = [l["name"].lower() for l in issue.get("labels", [])]
    all_text = combined + " " + " ".join(labels)

    for mod in MODULE_APIS:
        if mod in all_text:
            return mod
    # Check for specific module keywords
    module_kw = {
        "recruit": ["recruit", "candidate", "job posting", "applicant", "hiring", "offer letter"],
        "performance": ["performance", "appraisal", "review cycle", "goal", "kpi", "kra"],
        "rewards": ["reward", "recognition", "badge", "appreciation"],
        "exit": ["exit", "separation", "offboard", "full and final", "fnf"],
        "lms": ["lms", "course", "training", "learning"],
        "payroll": ["payroll", "salary", "payslip", "ctc", "compensation"],
        "project": ["project", "task", "timesheet", "sprint"],
        "monitor": ["monitor", "screenshot", "productivity", "tracking"],
    }
    for mod, kws in module_kw.items():
        for kw in kws:
            if kw in all_text:
                return mod
    return "empcloud"  # main module


def extract_endpoint_from_body(body):
    """Try to extract API endpoint or URL from issue body."""
    if not body:
        return None
    # Look for URLs
    urls = re.findall(r'https?://[^\s\)\"\'`]+', body)
    # Look for API paths
    paths = re.findall(r'(?:GET|POST|PUT|PATCH|DELETE)\s+(/[^\s\)\"\'`]+)', body)
    if not paths:
        paths = re.findall(r'`(/api/[^\s`]+)`', body)
    if not paths:
        paths = re.findall(r'(/api/v\d+/[^\s\)\"\'`]+)', body)
    return {"urls": urls, "paths": paths}


# --- Test functions ---
def test_auth(issue):
    """Test authentication-related issues."""
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "").lower()
    results = []

    # Test basic login
    login_endpoints = [
        f"{API_URL}/api/v1/auth/login",
        f"{API_URL}/auth/login",
        f"{API_URL}/api/auth/login",
    ]

    for ep in login_endpoints:
        # Valid creds
        status, resp, _ = http_request(ep, method="POST", data=CREDS["org_admin"])
        if status in (200, 201):
            results.append(("PASS", ep, f"Login works (HTTP {status})"))

            # If issue about logout/session
            if any(kw in title for kw in ["logout", "session", "sign out"]):
                token = None
                if isinstance(resp, dict):
                    token = (resp.get("token") or resp.get("access_token") or
                             (resp.get("data", {}).get("token") if isinstance(resp.get("data"), dict) else None))
                if token:
                    for logout_ep in [f"{API_URL}/api/v1/auth/logout", f"{API_URL}/auth/logout"]:
                        ls, lr, _ = http_request(logout_ep, method="POST",
                                                  headers={"Authorization": f"Bearer {token}"})
                        results.append(("PASS" if ls in (200, 201, 204) else "FAIL",
                                        logout_ep, f"Logout returned HTTP {ls}"))
            break

        # Invalid creds test
        status2, resp2, _ = http_request(ep, method="POST", data={
            "email": "invalid@test.com", "password": "wrong"
        })
        if status2 in (400, 401, 403, 422):
            results.append(("PASS", ep, f"Invalid login properly rejected (HTTP {status2})"))
        elif status2 in (200, 201):
            results.append(("FAIL", ep, "Invalid credentials accepted - security issue"))
        break

    if not results:
        # None of the login endpoints responded successfully
        status, resp, _ = http_request(f"{API_URL}/api/v1/auth/login", method="POST", data=CREDS["org_admin"])
        results.append(("INFO", f"{API_URL}/api/v1/auth/login", f"Login endpoint returned HTTP {status}"))

    return results


def test_rbac(issue):
    """Test RBAC/permission issues."""
    results = []
    title = (issue.get("title") or "").lower()
    module = detect_module(issue)
    api_base = MODULE_APIS.get(module, API_URL)

    # Get employee token
    emp_hdrs = auth_headers("employee")
    admin_hdrs = auth_headers("org_admin")

    # Admin-only endpoints to test with employee creds
    admin_endpoints = [
        "/api/v1/admin/settings",
        "/api/v1/admin/employees",
        "/api/v1/employees",
        "/api/v1/departments",
        "/api/v1/admin/roles",
        "/api/v1/settings",
        "/api/v1/admin/dashboard",
        "/api/v1/organization",
        "/api/v1/admin/users",
    ]

    # Super admin endpoints
    if "super" in title or "admin panel" in title:
        sa_hdrs = auth_headers("super_admin")
        for ep in ["/api/v1/admin/super", "/api/v1/admin/organizations", "/api/v1/admin/super/dashboard"]:
            url = f"{api_base}{ep}"
            # Employee should NOT have access
            s1, r1, _ = http_request(url, headers=emp_hdrs)
            if s1 in (401, 403):
                results.append(("PASS", url, f"Employee properly blocked (HTTP {s1})"))
            elif s1 in (200, 201):
                results.append(("FAIL", url, "Employee can access super admin endpoint"))
            else:
                results.append(("INFO", url, f"Endpoint returned HTTP {s1}"))
        return results

    tested = 0
    for ep in admin_endpoints:
        url = f"{api_base}{ep}"
        s1, r1, _ = http_request(url, headers=emp_hdrs)
        if s1 in (401, 403):
            results.append(("PASS", url, f"Employee correctly denied (HTTP {s1})"))
            tested += 1
        elif s1 in (200, 201):
            # Check if admin gets different data
            s2, r2, _ = http_request(url, headers=admin_hdrs)
            if s2 in (200, 201):
                results.append(("FAIL", url, "Employee has same access as admin - RBAC broken"))
                tested += 1
            else:
                results.append(("INFO", url, f"Employee: {s1}, Admin: {s2}"))
                tested += 1
        if tested >= 3:
            break

    if not results:
        results.append(("INFO", f"{api_base}/api/v1/*", "Could not find testable RBAC endpoints"))

    return results


def test_xss(issue):
    """Test XSS/injection issues."""
    results = []
    module = detect_module(issue)
    api_base = MODULE_APIS.get(module, API_URL)
    hdrs = auth_headers("org_admin")

    xss_payloads = [
        '<script>alert("xss")</script>',
        '"><img src=x onerror=alert(1)>',
        "'; DROP TABLE users; --",
        '<svg onload=alert(1)>',
    ]

    # Try posting to common endpoints with XSS payloads
    test_endpoints = [
        ("/api/v1/employees", {"name": xss_payloads[0], "email": "test@xss.com"}),
        ("/api/v1/departments", {"name": xss_payloads[0]}),
        ("/api/v1/leaves/apply", {"reason": xss_payloads[0]}),
        ("/api/v1/announcements", {"title": xss_payloads[0], "content": xss_payloads[1]}),
    ]

    for ep, payload in test_endpoints:
        url = f"{api_base}{ep}"
        full_hdrs = {**hdrs, "Content-Type": "application/json"}
        s, r, _ = http_request(url, method="POST", data=payload, headers=full_hdrs)
        if s in (400, 422):
            # Check if the response contains the raw payload (not sanitized)
            resp_str = json.dumps(r) if isinstance(r, dict) else str(r)
            if '<script>' in resp_str or 'onerror=' in resp_str:
                results.append(("FAIL", url, "XSS payload reflected in error response"))
            else:
                results.append(("PASS", url, f"Input rejected/sanitized (HTTP {s})"))
            break
        elif s in (200, 201):
            resp_str = json.dumps(r) if isinstance(r, dict) else str(r)
            if '<script>' in resp_str or 'onerror=' in resp_str:
                results.append(("FAIL", url, "XSS payload stored and reflected back"))
            else:
                results.append(("PASS", url, "Input accepted but sanitized in response"))
            break
        elif s in (401, 403):
            continue
        else:
            results.append(("INFO", url, f"Endpoint returned HTTP {s}"))
            break

    if not results:
        results.append(("INFO", f"{api_base}", "Could not reach testable endpoints for XSS"))

    return results


def test_routing(issue):
    """Test 404/routing issues."""
    results = []
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "")
    module = detect_module(issue)

    # Extract URLs from issue
    extracted = extract_endpoint_from_body(body)
    urls_to_test = []

    if extracted and extracted["urls"]:
        urls_to_test.extend(extracted["urls"][:3])
    if extracted and extracted["paths"]:
        base = MODULE_FRONTENDS.get(module, BASE_URL)
        for p in extracted["paths"][:3]:
            urls_to_test.append(f"{base}{p}")

    # Default routes to check based on module
    if not urls_to_test:
        base = MODULE_FRONTENDS.get(module, BASE_URL)
        api_base = MODULE_APIS.get(module, API_URL)
        urls_to_test = [
            f"{base}/",
            f"{base}/dashboard",
            f"{api_base}/api/v1/health",
            f"{api_base}/health",
        ]

    for url in urls_to_test[:4]:
        s, r, _ = http_request(url)
        if s == 404:
            results.append(("FAIL", url, f"Still returning 404"))
        elif s in (200, 301, 302):
            results.append(("PASS", url, f"Route accessible (HTTP {s})"))
        elif s == 0:
            results.append(("FAIL", url, f"Connection error: {r}"))
        else:
            results.append(("INFO", url, f"HTTP {s}"))

    return results


def test_crud(issue):
    """Test CRUD-related issues."""
    results = []
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "")
    module = detect_module(issue)
    api_base = MODULE_APIS.get(module, API_URL)
    hdrs = auth_headers("org_admin")

    # Extract specific endpoints from issue body
    extracted = extract_endpoint_from_body(body)
    endpoints_to_test = []

    if extracted and extracted["paths"]:
        for p in extracted["paths"][:3]:
            endpoints_to_test.append(p)

    # Map keywords to likely API endpoints
    crud_map = {
        "employee": ["/api/v1/employees", "/api/v1/employee"],
        "department": ["/api/v1/departments", "/api/v1/department"],
        "leave": ["/api/v1/leaves", "/api/v1/leave"],
        "attendance": ["/api/v1/attendance"],
        "holiday": ["/api/v1/holidays", "/api/v1/holiday"],
        "shift": ["/api/v1/shifts", "/api/v1/shift"],
        "document": ["/api/v1/documents", "/api/v1/document"],
        "announcement": ["/api/v1/announcements"],
        "candidate": ["/api/v1/candidates"],
        "job": ["/api/v1/jobs"],
        "course": ["/api/v1/courses"],
        "task": ["/api/v1/tasks"],
        "project": ["/api/v1/projects"],
        "salary": ["/api/v1/salary", "/api/v1/payroll"],
        "goal": ["/api/v1/goals"],
        "review": ["/api/v1/reviews"],
        "reward": ["/api/v1/rewards"],
        "roster": ["/api/v1/rosters", "/api/v1/roster"],
        "separation": ["/api/v1/separations"],
        "offer": ["/api/v1/offers"],
        "designation": ["/api/v1/designations"],
        "organization": ["/api/v1/organization"],
        "dashboard": ["/api/v1/dashboard"],
        "notification": ["/api/v1/notifications"],
        "profile": ["/api/v1/profile", "/api/v1/me"],
        "setting": ["/api/v1/settings"],
    }

    if not endpoints_to_test:
        for keyword, eps in crud_map.items():
            if keyword in title:
                endpoints_to_test.extend(eps)
        if not endpoints_to_test:
            # Default: test a few common endpoints
            endpoints_to_test = ["/api/v1/employees", "/api/v1/dashboard", "/api/v1/profile"]

    tested = 0
    for ep in endpoints_to_test[:4]:
        url = f"{api_base}{ep}"
        s, r, _ = http_request(url, headers=hdrs)
        if s in (200, 201):
            results.append(("PASS", url, f"Endpoint working (HTTP {s})"))
            tested += 1
        elif s == 500:
            results.append(("FAIL", url, f"Server error 500: {str(r)[:200]}"))
            tested += 1
        elif s in (401, 403):
            results.append(("INFO", url, f"Auth issue (HTTP {s}) - may need different creds"))
            tested += 1
        elif s == 404:
            results.append(("FAIL", url, f"Endpoint not found (404)"))
            tested += 1
        else:
            results.append(("INFO", url, f"HTTP {s}: {str(r)[:150]}"))
            tested += 1
        if tested >= 3:
            break

    if not results:
        results.append(("INFO", api_base, "Could not determine specific endpoint to test"))

    return results


def test_api_generic(issue):
    """Generic API test for unclassified issues."""
    results = []
    body = (issue.get("body") or "")
    module = detect_module(issue)
    api_base = MODULE_APIS.get(module, API_URL)
    hdrs = auth_headers("org_admin")

    extracted = extract_endpoint_from_body(body)
    if extracted and extracted["paths"]:
        for p in extracted["paths"][:3]:
            url = f"{api_base}{p}"
            s, r, _ = http_request(url, headers=hdrs)
            if s in (200, 201):
                results.append(("PASS", url, f"Working (HTTP {s})"))
            elif s == 500:
                results.append(("FAIL", url, f"Server error: {str(r)[:200]}"))
            else:
                results.append(("INFO", url, f"HTTP {s}"))
        return results

    if extracted and extracted["urls"]:
        for u in extracted["urls"][:3]:
            s, r, _ = http_request(u, headers=hdrs)
            if s in (200, 201, 301, 302):
                results.append(("PASS", u, f"Accessible (HTTP {s})"))
            elif s == 500:
                results.append(("FAIL", u, f"Server error: {str(r)[:200]}"))
            else:
                results.append(("INFO", u, f"HTTP {s}"))
        return results

    # Default health checks
    for ep in ["/api/v1/health", "/health", "/api/v1/dashboard"]:
        url = f"{api_base}{ep}"
        s, r, _ = http_request(url, headers=hdrs)
        if s in (200, 201):
            results.append(("PASS", url, f"OK (HTTP {s})"))
        elif s == 500:
            results.append(("FAIL", url, f"Server error"))
        else:
            results.append(("INFO", url, f"HTTP {s}"))

    return results


# --- Main test dispatcher ---
def test_issue(issue, category):
    """Run appropriate test based on category."""
    if category == "auth":
        return test_auth(issue)
    elif category == "rbac":
        return test_rbac(issue)
    elif category == "xss":
        return test_xss(issue)
    elif category == "routing":
        return test_routing(issue)
    elif category == "crud":
        return test_crud(issue)
    elif category == "api":
        return test_api_generic(issue)
    return []


def build_comment(issue, category, results):
    """Build a detailed comment for re-opened issues."""
    failing = [r for r in results if r[0] == "FAIL"]
    if not failing:
        return None

    lines = ["## Re-test Results (Automated)\n"]
    lines.append(f"**Issue:** #{issue['number']} - {issue['title']}")
    lines.append(f"**Category:** {category}")
    lines.append(f"**Date:** 2026-03-28\n")

    for status, url, detail in failing:
        lines.append("## URL Tested")
        lines.append(f"`{url}`\n")
        lines.append("## Steps to Reproduce")
        if category == "auth":
            lines.append("1. Send POST request to login endpoint with valid credentials")
            lines.append("2. Verify response status and token")
        elif category == "rbac":
            lines.append("1. Authenticate as employee (priya@technova.in)")
            lines.append("2. Send GET request to admin-restricted endpoint")
            lines.append("3. Check if access is properly denied")
        elif category == "xss":
            lines.append("1. Send POST request with XSS payload in input fields")
            lines.append("2. Check if payload is reflected/stored without sanitization")
        elif category == "routing":
            lines.append("1. Send GET request to the URL")
            lines.append("2. Check response status code")
        elif category == "crud":
            lines.append("1. Authenticate as org admin (ananya@technova.in)")
            lines.append("2. Send request to the API endpoint")
            lines.append("3. Check response status and data")
        else:
            lines.append("1. Send request to the API endpoint")
            lines.append("2. Check response")

        lines.append(f"\n## Actual Result")
        lines.append(f"{detail}\n")
        lines.append(f"## Expected Result")
        if category == "auth":
            lines.append("Login should succeed with valid credentials and return a token")
        elif category == "rbac":
            lines.append("Employee should receive 401/403 when accessing admin endpoints")
        elif category == "xss":
            lines.append("Input should be sanitized; XSS payloads should not be reflected")
        elif category == "routing":
            lines.append("Route should return 200 or proper redirect, not 404")
        elif category == "crud":
            lines.append("Endpoint should return 200 with valid data, not an error")
        else:
            lines.append("Endpoint should respond successfully without errors")
        lines.append("")

    return "\n".join(lines)


# --- Main ---
def main():
    print("=" * 70)
    print("EmpCloud Closed Bug Re-tester (Batch 2: Pages 2-4)")
    print("=" * 70)

    # Step 1: Fetch closed issues from pages 2-4
    all_issues = []
    for page in [2, 3, 4]:
        print(f"\nFetching closed issues page {page}...")
        status, data, _ = gh_get("/issues?state=closed", page=page, per_page=100)
        if status == 200 and isinstance(data, list):
            # Filter out pull requests
            issues = [i for i in data if "pull_request" not in i]
            all_issues.extend(issues)
            print(f"  Page {page}: {len(data)} items, {len(issues)} issues (excl PRs)")
        else:
            print(f"  Page {page}: HTTP {status} - {str(data)[:100]}")

    print(f"\nTotal closed issues fetched: {len(all_issues)}")

    # Step 2: Filter
    testable = []
    skipped = []
    for issue in all_issues:
        skip, reason = should_skip(issue)
        if skip:
            skipped.append((issue, reason))
        else:
            testable.append(issue)

    print(f"Testable: {len(testable)}, Skipped: {len(skipped)}")
    if skipped:
        for iss, reason in skipped[:5]:
            print(f"  SKIP #{iss['number']}: {reason} - {iss['title'][:50]}")
        if len(skipped) > 5:
            print(f"  ... and {len(skipped)-5} more skipped")

    # Step 3: Pre-auth
    print("\nAuthenticating...")
    for role in ["org_admin", "employee", "super_admin"]:
        token = get_token(role)
        if token:
            print(f"  {role}: token obtained ({token[:20]}...)")
        else:
            print(f"  {role}: NO TOKEN - auth failed")

    # Step 4: Test each issue
    summary = []  # (issue_number, title, category, verdict, detail)
    reopened = 0
    fixed = 0
    browser_needed = 0
    errors = 0

    for i, issue in enumerate(testable):
        num = issue["number"]
        title = issue["title"]
        category = classify_issue(issue)

        short_title = title[:55] + "..." if len(title) > 55 else title
        print(f"\n[{i+1}/{len(testable)}] #{num}: {short_title}")
        print(f"  Category: {category}")

        if category == "needs-browser-test":
            print(f"  -> SKIP (needs browser/Selenium)")
            summary.append((num, title, category, "SKIP", "Needs browser test"))
            browser_needed += 1
            continue

        try:
            results = test_issue(issue, category)
        except Exception as e:
            print(f"  -> ERROR: {e}")
            summary.append((num, title, category, "ERROR", str(e)[:80]))
            errors += 1
            continue

        if not results:
            print(f"  -> No test results")
            summary.append((num, title, category, "NO-TEST", "No testable endpoints"))
            continue

        # Determine verdict
        has_fail = any(r[0] == "FAIL" for r in results)
        has_pass = any(r[0] == "PASS" for r in results)

        for status, url, detail in results:
            print(f"  [{status}] {url}: {detail[:80]}")

        if has_fail:
            verdict = "STILL-FAILING"
            # Re-open the issue
            print(f"  -> RE-OPENING #{num}")
            s1, r1, _ = gh_patch(f"/issues/{num}", {"state": "open"})
            if s1 in (200, 201):
                print(f"    Issue re-opened successfully")
            else:
                print(f"    Failed to re-open: HTTP {s1}")

            # Post comment
            comment = build_comment(issue, category, results)
            if comment:
                s2, r2, _ = gh_post(f"/issues/{num}/comments", {"body": comment})
                if s2 in (200, 201):
                    print(f"    Comment posted")
                else:
                    print(f"    Failed to post comment: HTTP {s2}")

            fail_detail = "; ".join(f"{r[1]}: {r[2]}" for r in results if r[0] == "FAIL")
            summary.append((num, title, category, "STILL-FAILING", fail_detail[:100]))
            reopened += 1

        elif has_pass:
            verdict = "FIXED"
            print(f"  -> FIXED (leaving closed)")
            summary.append((num, title, category, "FIXED", "All tests passed"))
            fixed += 1

        else:
            verdict = "INCONCLUSIVE"
            info_detail = "; ".join(f"{r[2]}" for r in results)
            print(f"  -> INCONCLUSIVE")
            summary.append((num, title, category, "INCONCLUSIVE", info_detail[:100]))

        # Small delay to avoid GitHub rate limits
        time.sleep(0.5)

    # Step 5: Print summary
    print("\n" + "=" * 70)
    print("SUMMARY TABLE")
    print("=" * 70)
    print(f"{'#':<7} {'Category':<18} {'Verdict':<16} {'Title':<50}")
    print("-" * 91)

    for num, title, cat, verdict, detail in summary:
        short = title[:48] + ".." if len(title) > 48 else title
        print(f"#{num:<6} {cat:<18} {verdict:<16} {short}")

    print("-" * 91)
    print(f"\nTotals:")
    print(f"  Issues tested:      {len(testable)}")
    print(f"  STILL FAILING:      {reopened} (re-opened)")
    print(f"  FIXED:              {fixed} (left closed)")
    print(f"  Needs browser test: {browser_needed}")
    print(f"  Inconclusive:       {len(summary) - reopened - fixed - browser_needed - errors}")
    print(f"  Errors:             {errors}")
    print(f"  Skipped (filtered): {len(skipped)}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
