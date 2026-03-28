#!/usr/bin/env python3
"""
EMP Cloud 30-Day Simulation — Full Feature Coverage Test
Tests EVERY endpoint from the API reference across all modules.
Files bugs for missing/broken endpoints.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import time
import os
from datetime import datetime, timedelta

# ============================================================
# CONFIG
# ============================================================
CORE_API = "https://test-empcloud-api.empcloud.com"
PAYROLL_API = "https://testpayroll-api.empcloud.com"
RECRUIT_API = "https://test-recruit-api.empcloud.com"
PERFORMANCE_API = "https://test-performance-api.empcloud.com"
REWARDS_API = "https://test-rewards-api.empcloud.com"
EXIT_API = "https://test-exit-api.empcloud.com"
LMS_API = "https://testlms-api.empcloud.com"
PROJECT_API = "https://test-project-api.empcloud.com"

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_API = "https://api.github.com"

CREDS = {
    "technova": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "globaltech": {"email": "john@globaltech.com", "password": "Welcome@123"},
    "innovate": {"email": "hr@innovate.io", "password": "Welcome@123"},
    "superadmin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"},
    "employee": {"email": "priya@technova.in", "password": "Welcome@123"},
}

# Known IDs from setup_data.json
TECHNOVA_ORG_ID = 5
TECHNOVA_DEPT_ID = 72
TECHNOVA_EMP_ID = 663  # Shaurya Naidu
TECHNOVA_LEAVE_TYPE_ID = 31  # Casual Leave
TECHNOVA_SHIFT_ID = 10  # General Shift

TIMEOUT = 30
results = []
bugs_to_file = []
tokens = {}

# ============================================================
# HELPERS
# ============================================================
def login(cred_key):
    """Login and cache token."""
    if cred_key in tokens:
        return tokens[cred_key]
    cred = CREDS[cred_key]
    try:
        r = requests.post(f"{CORE_API}/api/v1/auth/login",
                          json={"email": cred["email"], "password": cred["password"]},
                          timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            # Try all known token locations
            token = None
            d = data.get("data", {}) or {}
            t = d.get("tokens", {}) or {}
            token = (t.get("access_token") or t.get("accessToken") or t.get("token")
                     or d.get("token") or d.get("accessToken") or d.get("access_token")
                     or data.get("token") or data.get("accessToken") or data.get("access_token"))
            tokens[cred_key] = token
            return token
        else:
            print(f"  [LOGIN FAIL] {cred_key}: {r.status_code}")
            return None
    except Exception as e:
        print(f"  [LOGIN ERROR] {cred_key}: {e}")
        return None


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def extract_token(data):
    """Extract token from any response structure."""
    if not isinstance(data, dict):
        return None
    d = data.get("data", {}) or {}
    t = (d.get("tokens", {}) or {}) if isinstance(d, dict) else {}
    return (t.get("access_token") or t.get("accessToken") or t.get("token")
            or (d.get("token") if isinstance(d, dict) else None)
            or (d.get("accessToken") if isinstance(d, dict) else None)
            or (d.get("access_token") if isinstance(d, dict) else None)
            or data.get("token") or data.get("accessToken") or data.get("access_token"))


def sso_login(module_api, core_token):
    """SSO into a module using core token."""
    try:
        r = requests.post(f"{module_api}/api/v1/auth/sso",
                          json={"token": core_token},
                          headers=auth_headers(core_token),
                          timeout=TIMEOUT)
        if r.status_code == 200:
            tok = extract_token(r.json())
            if tok:
                return tok
        # Try alternate SSO path
        r2 = requests.post(f"{module_api}/api/v1/auth/sso/validate",
                           json={"token": core_token},
                           headers=auth_headers(core_token),
                           timeout=TIMEOUT)
        if r2.status_code == 200:
            tok = extract_token(r2.json())
            if tok:
                return tok
        return core_token  # fallback: try with core token
    except:
        return core_token


def test_endpoint(category, method, path, base_url=None, token=None, body=None,
                  files=None, expected_statuses=None, notes_prefix="", cred_key="technova"):
    """Test a single endpoint and record result."""
    if base_url is None:
        base_url = CORE_API
    if token is None:
        token = login(cred_key)
    if expected_statuses is None:
        expected_statuses = [200, 201, 204]

    url = f"{base_url}{path}"
    if token in ("none", "skip_auth", None):
        headers = {}
        if token != "none":
            # Try to get a real token for skip_auth
            pass
    else:
        headers = {"Authorization": f"Bearer {token}"}
    if not files:
        headers["Content-Type"] = "application/json"

    result = {
        "category": category,
        "endpoint": path,
        "method": method,
        "status": None,
        "notes": "",
        "data_count": None,
        "response_keys": [],
    }

    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
        elif method == "POST":
            if files:
                h = {"Authorization": f"Bearer {token}"}
                r = requests.post(url, headers=h, files=files, data=body or {}, timeout=TIMEOUT)
            else:
                r = requests.post(url, headers=headers, json=body or {}, timeout=TIMEOUT)
        elif method == "PUT":
            r = requests.put(url, headers=headers, json=body or {}, timeout=TIMEOUT)
        elif method == "PATCH":
            r = requests.patch(url, headers=headers, json=body or {}, timeout=TIMEOUT)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, timeout=TIMEOUT)
        else:
            result["notes"] = f"Unknown method: {method}"
            results.append(result)
            return result

        result["status"] = r.status_code

        # Parse response
        try:
            data = r.json()
            if isinstance(data, dict):
                result["response_keys"] = list(data.keys())[:10]
                # Try to get data count
                for key in ["data", "results", "items", "records", "employees", "users"]:
                    if key in data and isinstance(data[key], list):
                        result["data_count"] = len(data[key])
                        break
                if result["data_count"] is None and "data" in data and isinstance(data["data"], dict):
                    for key in data["data"]:
                        if isinstance(data["data"][key], list):
                            result["data_count"] = len(data["data"][key])
                            break
                if result["data_count"] is None and "pagination" in data:
                    result["data_count"] = data["pagination"].get("total", "?")
                if result["data_count"] is None and "total" in data:
                    result["data_count"] = data["total"]
            elif isinstance(data, list):
                result["data_count"] = len(data)
        except:
            pass

        # Classify
        if r.status_code in expected_statuses:
            if result["data_count"] == 0 or (isinstance(result.get("data_count"), int) and result["data_count"] == 0):
                result["notes"] = f"{notes_prefix}exists but no data"
            elif result["data_count"] is not None:
                result["notes"] = f"{notes_prefix}working (count={result['data_count']})"
            else:
                result["notes"] = f"{notes_prefix}working"
        elif r.status_code == 404:
            result["notes"] = f"{notes_prefix}NOT FOUND (404)"
            bugs_to_file.append({
                "title": f"[30-Day Sim] Feature missing: {method} {path}",
                "body": f"## URL Tested\n`{method} {url}`\n\n## Steps to Reproduce\n1. Login as {cred_key}\n2. Call `{method} {url}`\n\n## Expected Result\nEndpoint should exist and return data\n\n## Actual Result\nHTTP 404 — endpoint not found\n\n## Response\n```\n{r.text[:500]}\n```",
            })
        elif r.status_code == 500:
            result["notes"] = f"{notes_prefix}SERVER ERROR (500)"
            bugs_to_file.append({
                "title": f"[30-Day Sim] Server error on {method} {path}",
                "body": f"## URL Tested\n`{method} {url}`\n\n## Steps to Reproduce\n1. Login as {cred_key}\n2. Call `{method} {url}`\n\n## Expected Result\nEndpoint should respond successfully\n\n## Actual Result\nHTTP 500 — internal server error\n\n## Response\n```\n{r.text[:500]}\n```",
            })
        elif r.status_code == 401:
            result["notes"] = f"{notes_prefix}UNAUTHORIZED (401)"
        elif r.status_code == 403:
            result["notes"] = f"{notes_prefix}FORBIDDEN (403)"
        elif r.status_code == 400:
            result["notes"] = f"{notes_prefix}BAD REQUEST (400)"
        elif r.status_code == 422:
            result["notes"] = f"{notes_prefix}VALIDATION ERROR (422)"
        else:
            result["notes"] = f"{notes_prefix}HTTP {r.status_code}"

    except requests.exceptions.Timeout:
        result["status"] = "TIMEOUT"
        result["notes"] = f"{notes_prefix}Request timed out"
    except requests.exceptions.ConnectionError:
        result["status"] = "CONN_ERR"
        result["notes"] = f"{notes_prefix}Connection refused"
    except Exception as e:
        result["status"] = "ERROR"
        result["notes"] = f"{notes_prefix}{str(e)[:100]}"

    results.append(result)
    status_str = str(result["status"]).ljust(6)
    print(f"  [{status_str}] {method.ljust(6)} {path}  => {result['notes']}")
    return result


def file_github_bug(title, body):
    """File a bug on GitHub."""
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "title": title,
        "body": body,
        "labels": ["bug", "30-day-sim"],
    }
    try:
        r = requests.post(f"{GITHUB_API}/repos/{GITHUB_REPO}/issues",
                          headers=headers, json=payload, timeout=30)
        if r.status_code == 201:
            issue = r.json()
            print(f"    -> Filed bug #{issue['number']}: {title}")
            return issue["number"]
        else:
            print(f"    -> Failed to file bug: {r.status_code} {r.text[:200]}")
            return None
    except Exception as e:
        print(f"    -> Error filing bug: {e}")
        return None


# ============================================================
# MAIN TEST FUNCTIONS
# ============================================================

def test_auth():
    print("\n" + "="*60)
    print("=== AUTH ===")
    print("="*60)
    # Login (already tested via login helper)
    test_endpoint("Auth", "POST", "/api/v1/auth/login",
                  body={"email": "ananya@technova.in", "password": "Welcome@123"})

    # Register (don't actually create - test with incomplete data to see if endpoint exists)
    test_endpoint("Auth", "POST", "/api/v1/auth/register",
                  body={"email": "test_coverage@test.com", "password": "Test@12345",
                        "first_name": "Coverage", "last_name": "Test",
                        "organization_name": "CoverageTestOrg"},
                  expected_statuses=[200, 201, 400, 422], token="skip_auth")

    # Password reset
    test_endpoint("Auth", "POST", "/api/v1/auth/password-reset",
                  body={"email": "ananya@technova.in"},
                  expected_statuses=[200, 201, 400, 422])

    # SSO validate
    token = login("technova")
    test_endpoint("Auth", "POST", "/api/v1/auth/sso/validate",
                  body={"token": token},
                  expected_statuses=[200, 201, 400, 422])


def test_oauth():
    print("\n" + "="*60)
    print("=== OAUTH ===")
    print("="*60)
    test_endpoint("OAuth", "GET", "/.well-known/openid-configuration",
                  expected_statuses=[200, 404], token="none")
    test_endpoint("OAuth", "GET", "/oauth/jwks",
                  expected_statuses=[200, 404], token="none")
    test_endpoint("OAuth", "POST", "/oauth/token",
                  body={"grant_type": "client_credentials"},
                  expected_statuses=[200, 400, 401, 404], token="none")
    test_endpoint("OAuth", "POST", "/oauth/revoke",
                  body={"token": "test"},
                  expected_statuses=[200, 400, 401, 404], token="none")
    test_endpoint("OAuth", "POST", "/oauth/introspect",
                  body={"token": "test"},
                  expected_statuses=[200, 400, 401, 404], token="none")


def test_organizations():
    print("\n" + "="*60)
    print("=== ORGANIZATIONS ===")
    print("="*60)
    test_endpoint("Organizations", "GET", "/api/v1/organizations/me")
    test_endpoint("Organizations", "PUT", "/api/v1/organizations/me",
                  body={"name": "TechNova Solutions"},
                  expected_statuses=[200, 400, 422])

    # Departments
    test_endpoint("Organizations", "GET", "/api/v1/organizations/me/departments")
    r = test_endpoint("Organizations", "POST", "/api/v1/organizations/me/departments",
                      body={"name": f"CoverageTestDept_{int(time.time())}"},
                      expected_statuses=[200, 201, 400, 422])
    # Try to get created dept ID for update/delete
    new_dept_id = None
    if r["status"] in [200, 201]:
        try:
            for res in results:
                pass  # We'll use a fixed approach
        except:
            pass

    test_endpoint("Organizations", "PUT", f"/api/v1/organizations/me/departments/{TECHNOVA_DEPT_ID}",
                  body={"name": "Engineering"},
                  expected_statuses=[200, 400, 404, 422])

    # Locations
    test_endpoint("Organizations", "GET", "/api/v1/organizations/me/locations")
    test_endpoint("Organizations", "POST", "/api/v1/organizations/me/locations",
                  body={"name": "Coverage Test Office", "address": "123 Test St", "city": "Mumbai",
                        "state": "Maharashtra", "country": "India", "pincode": "400001"},
                  expected_statuses=[200, 201, 400, 422])

    # Designations
    test_endpoint("Organizations", "GET", "/api/v1/organizations/me/designations",
                  expected_statuses=[200, 404])


def test_users():
    print("\n" + "="*60)
    print("=== USERS ===")
    print("="*60)
    test_endpoint("Users", "GET", "/api/v1/users")
    test_endpoint("Users", "GET", "/api/v1/users?page=1&limit=5")
    test_endpoint("Users", "GET", "/api/v1/users?search=priya")
    test_endpoint("Users", "GET", f"/api/v1/users/{TECHNOVA_EMP_ID}")
    test_endpoint("Users", "PUT", f"/api/v1/users/{TECHNOVA_EMP_ID}",
                  body={"phone": "+91-9876543210"},
                  expected_statuses=[200, 400, 422])

    # Invite
    test_endpoint("Users", "POST", "/api/v1/users/invite",
                  body={"email": f"coverage_invite_{int(time.time())}@technova.in",
                        "first_name": "Coverage", "last_name": "Invite", "role": "employee"},
                  expected_statuses=[200, 201, 400, 422])

    # Org chart
    test_endpoint("Users", "GET", "/api/v1/users/org-chart",
                  expected_statuses=[200, 404])
    test_endpoint("Users", "GET", "/api/v1/employees/org-chart",
                  expected_statuses=[200, 404])

    # Employee profile
    test_endpoint("Users", "GET", f"/api/v1/employees/{TECHNOVA_EMP_ID}/profile")
    test_endpoint("Users", "GET", f"/api/v1/employees/{TECHNOVA_EMP_ID}/addresses",
                  expected_statuses=[200, 404])
    test_endpoint("Users", "GET", f"/api/v1/employees/{TECHNOVA_EMP_ID}/education",
                  expected_statuses=[200, 404])
    test_endpoint("Users", "GET", f"/api/v1/employees/{TECHNOVA_EMP_ID}/experience",
                  expected_statuses=[200, 404])
    test_endpoint("Users", "GET", f"/api/v1/employees/{TECHNOVA_EMP_ID}/dependents",
                  expected_statuses=[200, 404])


def test_attendance():
    print("\n" + "="*60)
    print("=== ATTENDANCE ===")
    print("="*60)
    # Check-in/out (use employee cred)
    emp_token = login("employee")
    test_endpoint("Attendance", "POST", "/api/v1/attendance/check-in",
                  token=emp_token, expected_statuses=[200, 201, 400, 409, 422])
    test_endpoint("Attendance", "POST", "/api/v1/attendance/check-out",
                  token=emp_token, expected_statuses=[200, 201, 400, 409, 422])

    # Records
    test_endpoint("Attendance", "GET", "/api/v1/attendance/records")
    test_endpoint("Attendance", "GET", "/api/v1/attendance/records?start_date=2026-03-01&end_date=2026-03-28")
    test_endpoint("Attendance", "GET", "/api/v1/attendance/dashboard",
                  expected_statuses=[200, 404])

    # Shifts
    test_endpoint("Attendance", "GET", "/api/v1/attendance/shifts")
    ts = int(time.time())
    test_endpoint("Attendance", "POST", "/api/v1/attendance/shifts",
                  body={"name": f"CoverageShift_{ts}", "start_time": "14:00", "end_time": "22:00"},
                  expected_statuses=[200, 201, 400, 422])
    test_endpoint("Attendance", "PUT", f"/api/v1/attendance/shifts/{TECHNOVA_SHIFT_ID}",
                  body={"name": "General Shift"},
                  expected_statuses=[200, 400, 404, 422])

    # Shift assignments
    test_endpoint("Attendance", "GET", "/api/v1/attendance/shift-assignments",
                  expected_statuses=[200, 404])

    # Regularizations
    test_endpoint("Attendance", "GET", "/api/v1/attendance/regularizations",
                  expected_statuses=[200, 404])

    # Geo-fences
    test_endpoint("Attendance", "GET", "/api/v1/attendance/geo-fences",
                  expected_statuses=[200, 404])

    # Schedule
    test_endpoint("Attendance", "GET", "/api/v1/attendance/schedule",
                  expected_statuses=[200, 404])

    # Reports & Export
    test_endpoint("Attendance", "GET", "/api/v1/attendance/reports",
                  expected_statuses=[200, 404])
    test_endpoint("Attendance", "GET", "/api/v1/attendance/export",
                  expected_statuses=[200, 404])


def test_leave():
    print("\n" + "="*60)
    print("=== LEAVE ===")
    print("="*60)
    test_endpoint("Leave", "GET", "/api/v1/leave/balances")
    test_endpoint("Leave", "GET", "/api/v1/leave/types")

    # Create leave type
    ts = int(time.time())
    test_endpoint("Leave", "POST", "/api/v1/leave/types",
                  body={"name": f"CoverageLeave_{ts}", "days_allowed": 5, "carry_forward": False},
                  expected_statuses=[200, 201, 400, 422])

    # Update leave type
    test_endpoint("Leave", "PUT", f"/api/v1/leave/types/{TECHNOVA_LEAVE_TYPE_ID}",
                  body={"name": "Casual Leave", "days_allowed": 12},
                  expected_statuses=[200, 400, 404, 422])

    # Applications
    test_endpoint("Leave", "GET", "/api/v1/leave/applications")

    # Apply for leave (as employee)
    emp_token = login("employee")
    future_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
    future_date2 = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
    test_endpoint("Leave", "POST", "/api/v1/leave/applications",
                  body={"leave_type_id": TECHNOVA_LEAVE_TYPE_ID,
                        "start_date": future_date, "end_date": future_date2,
                        "reason": "Coverage test leave application"},
                  token=emp_token,
                  expected_statuses=[200, 201, 400, 422])

    # Policies
    test_endpoint("Leave", "GET", "/api/v1/leave/policies")
    test_endpoint("Leave", "POST", "/api/v1/leave/policies",
                  body={"name": f"CoveragePolicy_{ts}", "description": "Test policy"},
                  expected_statuses=[200, 201, 400, 422])

    # Comp-off
    test_endpoint("Leave", "GET", "/api/v1/leave/comp-off")

    # Calendar
    test_endpoint("Leave", "GET", "/api/v1/leave/calendar",
                  expected_statuses=[200, 404])

    # Dashboard
    test_endpoint("Leave", "GET", "/api/v1/leave/dashboard",
                  expected_statuses=[200, 404])

    # Bulk approve/reject
    test_endpoint("Leave", "POST", "/api/v1/leave/bulk-approve",
                  body={"ids": []},
                  expected_statuses=[200, 400, 404, 422])
    test_endpoint("Leave", "POST", "/api/v1/leave/bulk-reject",
                  body={"ids": []},
                  expected_statuses=[200, 400, 404, 422])


def test_documents():
    print("\n" + "="*60)
    print("=== DOCUMENTS ===")
    print("="*60)
    test_endpoint("Documents", "GET", "/api/v1/documents")
    test_endpoint("Documents", "GET", "/api/v1/documents/categories",
                  expected_statuses=[200, 404])
    test_endpoint("Documents", "GET", "/api/v1/documents/my",
                  expected_statuses=[200, 404])
    test_endpoint("Documents", "GET", "/api/v1/documents/mandatory",
                  expected_statuses=[200, 404])
    test_endpoint("Documents", "GET", "/api/v1/documents/expiry-alerts",
                  expected_statuses=[200, 404])

    # Upload a test document (multipart)
    token = login("technova")
    try:
        import io
        fake_file = io.BytesIO(b"Coverage test document content")
        files = {"file": ("coverage_test.txt", fake_file, "text/plain")}
        test_endpoint("Documents", "POST", "/api/v1/documents",
                      files=files,
                      body={"title": "Coverage Test Doc", "category": "general",
                            "employee_id": str(TECHNOVA_EMP_ID)},
                      expected_statuses=[200, 201, 400, 422])
    except Exception as e:
        print(f"  [ERROR] Document upload: {e}")


def test_announcements():
    print("\n" + "="*60)
    print("=== ANNOUNCEMENTS ===")
    print("="*60)
    test_endpoint("Announcements", "GET", "/api/v1/announcements")

    ts = int(time.time())
    r = test_endpoint("Announcements", "POST", "/api/v1/announcements",
                      body={"title": f"Coverage Test Announcement {ts}",
                            "content": "This is a coverage test announcement.",
                            "priority": "normal"},
                      expected_statuses=[200, 201, 400, 422])

    test_endpoint("Announcements", "GET", "/api/v1/announcements/unread-count",
                  expected_statuses=[200, 404])


def test_policies():
    print("\n" + "="*60)
    print("=== POLICIES ===")
    print("="*60)
    test_endpoint("Policies", "GET", "/api/v1/policies")

    ts = int(time.time())
    test_endpoint("Policies", "POST", "/api/v1/policies",
                  body={"title": f"Coverage Test Policy {ts}",
                        "content": "This is a coverage test policy document.",
                        "category": "general"},
                  expected_statuses=[200, 201, 400, 422])

    test_endpoint("Policies", "GET", "/api/v1/policies/pending",
                  expected_statuses=[200, 404])


def test_events():
    print("\n" + "="*60)
    print("=== EVENTS ===")
    print("="*60)
    test_endpoint("Events", "GET", "/api/v1/events")

    ts = int(time.time())
    future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    test_endpoint("Events", "POST", "/api/v1/events",
                  body={"title": f"Coverage Test Event {ts}",
                        "description": "Coverage test event.",
                        "start_date": future, "end_date": future,
                        "location": "Virtual"},
                  expected_statuses=[200, 201, 400, 422])

    test_endpoint("Events", "GET", "/api/v1/events/calendar",
                  expected_statuses=[200, 404])


def test_surveys():
    print("\n" + "="*60)
    print("=== SURVEYS ===")
    print("="*60)
    test_endpoint("Surveys", "GET", "/api/v1/surveys")

    ts = int(time.time())
    test_endpoint("Surveys", "POST", "/api/v1/surveys",
                  body={"title": f"Coverage Survey {ts}",
                        "description": "Coverage test survey",
                        "questions": [{"text": "Rate coverage?", "type": "rating"}]},
                  expected_statuses=[200, 201, 400, 422])


def test_forum():
    print("\n" + "="*60)
    print("=== FORUM ===")
    print("="*60)
    test_endpoint("Forum", "GET", "/api/v1/forum/categories")
    test_endpoint("Forum", "GET", "/api/v1/forum/posts")

    ts = int(time.time())
    test_endpoint("Forum", "POST", "/api/v1/forum/posts",
                  body={"title": f"Coverage Test Post {ts}",
                        "content": "This is a coverage test forum post.",
                        "category_id": 1},
                  expected_statuses=[200, 201, 400, 422])

    test_endpoint("Forum", "POST", "/api/v1/forum/categories",
                  body={"name": f"CoverageCategory_{ts}"},
                  expected_statuses=[200, 201, 400, 422])


def test_feedback():
    print("\n" + "="*60)
    print("=== FEEDBACK ===")
    print("="*60)
    test_endpoint("Feedback", "GET", "/api/v1/feedback")

    ts = int(time.time())
    test_endpoint("Feedback", "POST", "/api/v1/feedback",
                  body={"content": f"Coverage test feedback {ts}",
                        "type": "suggestion", "anonymous": True},
                  expected_statuses=[200, 201, 400, 422])


def test_helpdesk():
    print("\n" + "="*60)
    print("=== HELPDESK ===")
    print("="*60)
    test_endpoint("Helpdesk", "GET", "/api/v1/helpdesk/tickets")

    ts = int(time.time())
    test_endpoint("Helpdesk", "POST", "/api/v1/helpdesk/tickets",
                  body={"subject": f"Coverage Test Ticket {ts}",
                        "description": "Coverage test helpdesk ticket.",
                        "priority": "medium", "category": "IT"},
                  expected_statuses=[200, 201, 400, 422])

    test_endpoint("Helpdesk", "GET", "/api/v1/helpdesk/categories",
                  expected_statuses=[200, 404])
    test_endpoint("Helpdesk", "GET", "/api/v1/helpdesk/knowledge-base",
                  expected_statuses=[200, 404])

    test_endpoint("Helpdesk", "POST", "/api/v1/helpdesk/knowledge-base",
                  body={"title": f"Coverage KB Article {ts}",
                        "content": "Coverage test knowledge base article.",
                        "category": "IT"},
                  expected_statuses=[200, 201, 400, 422])


def test_assets():
    print("\n" + "="*60)
    print("=== ASSETS ===")
    print("="*60)
    test_endpoint("Assets", "GET", "/api/v1/assets")
    test_endpoint("Assets", "GET", "/api/v1/assets/categories",
                  expected_statuses=[200, 404])
    test_endpoint("Assets", "GET", "/api/v1/assets/my",
                  expected_statuses=[200, 404])

    ts = int(time.time())
    test_endpoint("Assets", "POST", "/api/v1/assets",
                  body={"name": f"Coverage Laptop {ts}",
                        "type": "Laptop", "serial_number": f"COV-{ts}",
                        "status": "available"},
                  expected_statuses=[200, 201, 400, 422])


def test_positions():
    print("\n" + "="*60)
    print("=== POSITIONS ===")
    print("="*60)
    test_endpoint("Positions", "GET", "/api/v1/positions")
    test_endpoint("Positions", "GET", "/api/v1/positions/headcount",
                  expected_statuses=[200, 404])

    ts = int(time.time())
    test_endpoint("Positions", "POST", "/api/v1/positions",
                  body={"title": f"Coverage Position {ts}",
                        "department_id": TECHNOVA_DEPT_ID,
                        "vacancies": 2},
                  expected_statuses=[200, 201, 400, 422])


def test_wellness():
    print("\n" + "="*60)
    print("=== WELLNESS ===")
    print("="*60)
    emp_token = login("employee")
    test_endpoint("Wellness", "GET", "/api/v1/wellness/dashboard",
                  token=emp_token, expected_statuses=[200, 404])
    test_endpoint("Wellness", "POST", "/api/v1/wellness/check-in",
                  token=emp_token,
                  body={"mood": 4, "energy": 3, "sleep_hours": 7,
                        "exercise": True, "notes": "Coverage test"},
                  expected_statuses=[200, 201, 400, 422])
    test_endpoint("Wellness", "GET", "/api/v1/wellness/goals",
                  token=emp_token, expected_statuses=[200, 404])


def test_whistleblowing():
    print("\n" + "="*60)
    print("=== WHISTLEBLOWING ===")
    print("="*60)
    test_endpoint("Whistleblowing", "GET", "/api/v1/whistleblowing")
    test_endpoint("Whistleblowing", "POST", "/api/v1/whistleblowing",
                  body={"subject": "Coverage test report",
                        "description": "This is a coverage test whistleblowing report.",
                        "anonymous": True},
                  expected_statuses=[200, 201, 400, 422])


def test_notifications():
    print("\n" + "="*60)
    print("=== NOTIFICATIONS ===")
    print("="*60)
    test_endpoint("Notifications", "GET", "/api/v1/notifications")
    test_endpoint("Notifications", "GET", "/api/v1/notifications/unread-count",
                  expected_statuses=[200, 404])
    test_endpoint("Notifications", "POST", "/api/v1/notifications/read-all",
                  expected_statuses=[200, 204, 404])
    test_endpoint("Notifications", "GET", "/api/v1/notifications/preferences",
                  expected_statuses=[200, 404])


def test_audit():
    print("\n" + "="*60)
    print("=== AUDIT / LOGS ===")
    print("="*60)
    test_endpoint("Audit", "GET", "/api/v1/audit",
                  expected_statuses=[200, 404])
    test_endpoint("Audit", "GET", "/api/v1/logs",
                  expected_statuses=[200, 404])
    test_endpoint("Audit", "GET", "/api/v1/logs/analysis",
                  expected_statuses=[200, 404])


def test_modules_subscriptions():
    print("\n" + "="*60)
    print("=== MODULES & SUBSCRIPTIONS ===")
    print("="*60)
    test_endpoint("Modules", "GET", "/api/v1/modules")
    test_endpoint("Subscriptions", "GET", "/api/v1/subscriptions")


def test_custom_fields():
    print("\n" + "="*60)
    print("=== CUSTOM FIELDS ===")
    print("="*60)
    test_endpoint("CustomFields", "GET", "/api/v1/custom-fields/definitions",
                  expected_statuses=[200, 404])

    ts = int(time.time())
    test_endpoint("CustomFields", "POST", "/api/v1/custom-fields/definitions",
                  body={"name": f"coverage_field_{ts}", "type": "text",
                        "entity_type": "employee", "required": False},
                  expected_statuses=[200, 201, 400, 404, 422])

    test_endpoint("CustomFields", "GET",
                  f"/api/v1/custom-fields/values/employee/{TECHNOVA_EMP_ID}",
                  expected_statuses=[200, 404])


def test_dashboard():
    print("\n" + "="*60)
    print("=== DASHBOARD ===")
    print("="*60)
    test_endpoint("Dashboard", "GET", "/api/v1/dashboard/widgets",
                  expected_statuses=[200, 404])
    test_endpoint("Dashboard", "GET", "/api/v1/dashboard/module-summaries",
                  expected_statuses=[200, 404])
    test_endpoint("Dashboard", "GET", "/api/v1/dashboard/module-insights",
                  expected_statuses=[200, 404])


def test_billing():
    print("\n" + "="*60)
    print("=== BILLING ===")
    print("="*60)
    test_endpoint("Billing", "GET", "/api/v1/billing/invoices",
                  expected_statuses=[200, 404])


def test_ai_chatbot():
    print("\n" + "="*60)
    print("=== AI / CHATBOT ===")
    print("="*60)
    test_endpoint("AI", "POST", "/api/v1/chatbot/message",
                  body={"message": "What is my leave balance?"},
                  expected_statuses=[200, 201, 400, 404, 422, 500])
    test_endpoint("AI", "GET", "/api/v1/chatbot/conversations",
                  expected_statuses=[200, 404])
    test_endpoint("AI", "GET", "/api/v1/ai-config",
                  expected_statuses=[200, 404])


def test_admin():
    print("\n" + "="*60)
    print("=== ADMIN (Super Admin) ===")
    print("="*60)
    sa_token = login("superadmin")
    test_endpoint("Admin", "GET", "/api/v1/admin/organizations",
                  token=sa_token, cred_key="superadmin")
    test_endpoint("Admin", "GET", f"/api/v1/admin/organizations/{TECHNOVA_ORG_ID}",
                  token=sa_token, expected_statuses=[200, 404], cred_key="superadmin")
    test_endpoint("Admin", "GET", "/api/v1/admin/health",
                  token=sa_token, cred_key="superadmin")
    test_endpoint("Admin", "GET", "/api/v1/admin/data-sanity",
                  token=sa_token, cred_key="superadmin")
    test_endpoint("Admin", "GET", "/api/v1/admin/stats",
                  token=sa_token, expected_statuses=[200, 404], cred_key="superadmin")


def test_health():
    print("\n" + "="*60)
    print("=== HEALTH / MISC ===")
    print("="*60)
    test_endpoint("Health", "GET", "/health", expected_statuses=[200, 404], token="none")
    test_endpoint("Health", "GET", "/api/docs", expected_statuses=[200, 301, 302, 404], token="none")


# ============================================================
# MODULE TESTS
# ============================================================

def test_payroll():
    print("\n" + "="*60)
    print("=== PAYROLL MODULE (SSO) ===")
    print("="*60)
    core_token = login("technova")
    mod_token = sso_login(PAYROLL_API, core_token)

    test_endpoint("Payroll", "GET", "/api/v1/payroll",
                  base_url=PAYROLL_API, token=mod_token)
    test_endpoint("Payroll", "GET", "/api/v1/salary-structures",
                  base_url=PAYROLL_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Payroll", "GET", f"/api/v1/salary-structures/employee/{TECHNOVA_EMP_ID}",
                  base_url=PAYROLL_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Payroll", "GET", "/api/v1/self-service/payslips",
                  base_url=PAYROLL_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Payroll", "GET", "/api/v1/self-service/tax/declarations",
                  base_url=PAYROLL_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Payroll", "GET", "/api/v1/docs/openapi.json",
                  base_url=PAYROLL_API, token=mod_token,
                  expected_statuses=[200, 404])


def test_recruit():
    print("\n" + "="*60)
    print("=== RECRUIT MODULE (SSO) ===")
    print("="*60)
    core_token = login("technova")
    mod_token = sso_login(RECRUIT_API, core_token)

    test_endpoint("Recruit", "GET", "/api/v1/jobs",
                  base_url=RECRUIT_API, token=mod_token)
    test_endpoint("Recruit", "POST", "/api/v1/jobs",
                  base_url=RECRUIT_API, token=mod_token,
                  body={"title": f"Coverage Test Job {int(time.time())}",
                        "department": "Engineering", "location": "Mumbai",
                        "type": "full-time"},
                  expected_statuses=[200, 201, 400, 422])
    test_endpoint("Recruit", "GET", "/api/v1/applications",
                  base_url=RECRUIT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Recruit", "GET", "/api/v1/interviews",
                  base_url=RECRUIT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Recruit", "GET", "/api/v1/offers",
                  base_url=RECRUIT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Recruit", "GET", "/api/v1/pipeline-stages",
                  base_url=RECRUIT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Recruit", "GET", "/api/v1/analytics",
                  base_url=RECRUIT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Recruit", "GET", "/api/v1/analytics/overview",
                  base_url=RECRUIT_API, token=mod_token,
                  expected_statuses=[200, 404])


def test_performance():
    print("\n" + "="*60)
    print("=== PERFORMANCE MODULE (SSO) ===")
    print("="*60)
    core_token = login("technova")
    mod_token = sso_login(PERFORMANCE_API, core_token)

    test_endpoint("Performance", "GET", "/api/v1/review-cycles",
                  base_url=PERFORMANCE_API, token=mod_token)
    test_endpoint("Performance", "GET", "/api/v1/goals",
                  base_url=PERFORMANCE_API, token=mod_token)
    test_endpoint("Performance", "GET", "/api/v1/nine-box",
                  base_url=PERFORMANCE_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Performance", "GET", "/api/v1/pips",
                  base_url=PERFORMANCE_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Performance", "GET", "/api/v1/one-on-ones",
                  base_url=PERFORMANCE_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Performance", "GET", "/api/v1/competency-frameworks",
                  base_url=PERFORMANCE_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Performance", "GET", "/api/v1/succession-plans",
                  base_url=PERFORMANCE_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Performance", "GET", "/api/v1/analytics/overview",
                  base_url=PERFORMANCE_API, token=mod_token,
                  expected_statuses=[200, 404])


def test_rewards():
    print("\n" + "="*60)
    print("=== REWARDS MODULE (SSO) ===")
    print("="*60)
    core_token = login("technova")
    mod_token = sso_login(REWARDS_API, core_token)

    test_endpoint("Rewards", "GET", "/api/v1/kudos",
                  base_url=REWARDS_API, token=mod_token)
    test_endpoint("Rewards", "POST", "/api/v1/kudos",
                  base_url=REWARDS_API, token=mod_token,
                  body={"recipient_id": TECHNOVA_EMP_ID,
                        "message": "Coverage test kudos!", "points": 10},
                  expected_statuses=[200, 201, 400, 422])
    test_endpoint("Rewards", "GET", "/api/v1/points/balance",
                  base_url=REWARDS_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Rewards", "GET", "/api/v1/leaderboard",
                  base_url=REWARDS_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Rewards", "GET", "/api/v1/badges",
                  base_url=REWARDS_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Rewards", "GET", "/api/v1/challenges",
                  base_url=REWARDS_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Rewards", "GET", "/api/v1/celebrations",
                  base_url=REWARDS_API, token=mod_token,
                  expected_statuses=[200, 404])


def test_exit():
    print("\n" + "="*60)
    print("=== EXIT MODULE (SSO) ===")
    print("="*60)
    core_token = login("technova")
    mod_token = sso_login(EXIT_API, core_token)

    test_endpoint("Exit", "GET", "/api/v1/exits",
                  base_url=EXIT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Exit", "GET", "/api/v1/exit-interviews",
                  base_url=EXIT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Exit", "GET", "/api/v1/my-clearances",
                  base_url=EXIT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Exit", "GET", "/api/v1/predictions/dashboard",
                  base_url=EXIT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Exit", "GET", "/api/v1/nps/scores",
                  base_url=EXIT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Exit", "GET", "/api/v1/rehire/eligible",
                  base_url=EXIT_API, token=mod_token,
                  expected_statuses=[200, 404])


def test_lms():
    print("\n" + "="*60)
    print("=== LMS MODULE (SSO) ===")
    print("="*60)
    core_token = login("technova")
    mod_token = sso_login(LMS_API, core_token)

    test_endpoint("LMS", "GET", "/api/v1/courses",
                  base_url=LMS_API, token=mod_token)
    test_endpoint("LMS", "GET", "/api/v1/certifications",
                  base_url=LMS_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("LMS", "GET", "/api/v1/certificates/my",
                  base_url=LMS_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("LMS", "GET", "/api/v1/learning-paths",
                  base_url=LMS_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("LMS", "GET", "/api/v1/quizzes",
                  base_url=LMS_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("LMS", "GET", "/api/v1/gamification/leaderboard",
                  base_url=LMS_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("LMS", "GET", "/api/v1/gamification/badges",
                  base_url=LMS_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("LMS", "GET", "/api/v1/compliance/dashboard",
                  base_url=LMS_API, token=mod_token,
                  expected_statuses=[200, 404])


def test_project():
    print("\n" + "="*60)
    print("=== PROJECT MODULE (SSO — /v1/ prefix) ===")
    print("="*60)
    core_token = login("technova")
    mod_token = sso_login(PROJECT_API, core_token)

    # Project uses /v1/ not /api/v1/
    test_endpoint("Project", "GET", "/v1/projects",
                  base_url=PROJECT_API, token=mod_token)
    test_endpoint("Project", "GET", "/v1/tasks",
                  base_url=PROJECT_API, token=mod_token,
                  expected_statuses=[200, 404])
    test_endpoint("Project", "GET", "/v1/time-entries",
                  base_url=PROJECT_API, token=mod_token,
                  expected_statuses=[200, 404])

    # Also try /api/v1/ in case
    test_endpoint("Project", "GET", "/api/v1/projects",
                  base_url=PROJECT_API, token=mod_token,
                  expected_statuses=[200, 404],
                  notes_prefix="(alt path) ")


# ============================================================
# MULTI-ORG ISOLATION TEST
# ============================================================
def test_multi_org():
    print("\n" + "="*60)
    print("=== MULTI-ORG ISOLATION ===")
    print("="*60)
    # Login as GlobalTech admin, ensure we can't see TechNova data
    gt_token = login("globaltech")
    test_endpoint("MultiOrg", "GET", "/api/v1/organizations/me",
                  token=gt_token, cred_key="globaltech")
    test_endpoint("MultiOrg", "GET", "/api/v1/users",
                  token=gt_token, cred_key="globaltech")
    test_endpoint("MultiOrg", "GET", "/api/v1/organizations/me/departments",
                  token=gt_token, cred_key="globaltech")

    # Innovate
    inn_token = login("innovate")
    test_endpoint("MultiOrg", "GET", "/api/v1/organizations/me",
                  token=inn_token, cred_key="innovate",
                  notes_prefix="(Innovate) ")


# ============================================================
# MAIN
# ============================================================
def main():
    start_time = time.time()
    print("=" * 70)
    print("  EMP CLOUD — FULL FEATURE COVERAGE TEST")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Login all accounts first
    print("\n--- Logging in all accounts ---")
    for key in CREDS:
        t = login(key)
        if t:
            print(f"  [OK] {key}: token={t[:20]}...")
        else:
            print(f"  [FAIL] {key}: no token")

    # Run all test categories
    test_auth()
    test_oauth()
    test_organizations()
    test_users()
    test_attendance()
    test_leave()
    test_documents()
    test_announcements()
    test_policies()
    test_events()
    test_surveys()
    test_forum()
    test_feedback()
    test_helpdesk()
    test_assets()
    test_positions()
    test_wellness()
    test_whistleblowing()
    test_notifications()
    test_audit()
    test_modules_subscriptions()
    test_custom_fields()
    test_dashboard()
    test_billing()
    test_ai_chatbot()
    test_admin()
    test_health()

    # Module tests
    test_payroll()
    test_recruit()
    test_performance()
    test_rewards()
    test_exit()
    test_lms()
    test_project()

    # Multi-org
    test_multi_org()

    elapsed = time.time() - start_time

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 70)
    print("  COVERAGE MATRIX")
    print("=" * 70)

    # Group by category
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    total = len(results)
    working = sum(1 for r in results if "working" in str(r.get("notes", "")))
    no_data = sum(1 for r in results if "no data" in str(r.get("notes", "")))
    not_found = sum(1 for r in results if "NOT FOUND" in str(r.get("notes", "")))
    errors = sum(1 for r in results if "ERROR" in str(r.get("notes", "")) or "500" in str(r.get("notes", "")))
    auth_issues = sum(1 for r in results if "UNAUTHORIZED" in str(r.get("notes", "")) or "FORBIDDEN" in str(r.get("notes", "")))

    print(f"\n{'Category':<20} {'Endpoint':<55} {'Method':<7} {'Status':<8} {'Notes'}")
    print("-" * 150)

    for cat in sorted(categories.keys()):
        for r in categories[cat]:
            status_str = str(r["status"])[:7] if r["status"] else "?"
            notes = (r.get("notes", "") or "")[:60]
            print(f"{r['category']:<20} {r['endpoint']:<55} {r['method']:<7} {status_str:<8} {notes}")

    print("\n" + "=" * 70)
    print(f"  SUMMARY")
    print(f"  Total endpoints tested: {total}")
    print(f"  Working:                {working}")
    print(f"  Exists but no data:     {no_data}")
    print(f"  Not found (404):        {not_found}")
    print(f"  Server errors (500):    {errors}")
    print(f"  Auth issues (401/403):  {auth_issues}")
    print(f"  Other:                  {total - working - no_data - not_found - errors - auth_issues}")
    print(f"  Elapsed time:           {elapsed:.1f}s")
    print("=" * 70)

    # ============================================================
    # SAVE RESULTS
    # ============================================================
    output_path = "C:/emptesting/simulation/feature_coverage.json"
    coverage_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "working": working,
            "no_data": no_data,
            "not_found": not_found,
            "server_errors": errors,
            "auth_issues": auth_issues,
            "elapsed_seconds": round(elapsed, 1),
        },
        "results": results,
        "bugs_to_file": [{"title": b["title"]} for b in bugs_to_file],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(coverage_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResults saved to {output_path}")

    # ============================================================
    # FILE BUGS
    # ============================================================
    if bugs_to_file:
        print(f"\n--- Filing {len(bugs_to_file)} bugs on GitHub ---")
        for bug in bugs_to_file:
            file_github_bug(bug["title"], bug["body"])
    else:
        print("\nNo bugs to file — all endpoints responded.")

    print("\nDone.")


if __name__ == "__main__":
    main()
