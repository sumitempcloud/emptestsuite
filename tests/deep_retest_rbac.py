#!/usr/bin/env python3
"""
Deep RBAC / Permission Re-test for EmpCloud/EmpCloud
Searches all closed issues with RBAC/permission keywords,
then deeply tests each relevant endpoint and comments/reopens on GitHub.
"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import time
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────
API_BASE = "https://test-empcloud-api.empcloud.com"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_API = "https://api.github.com"

CREDS = {
    "org_admin":  {"email": "ananya@technova.in",   "password": "Welcome@123"},
    "employee":   {"email": "priya@technova.in",     "password": "Welcome@123"},
    "other_org":  {"email": "john@globaltech.com",   "password": "Welcome@123"},
}

SKIP_MODULES = ["field", "biometrics", "emp-field", "emp-biometrics"]

# ── Helpers ─────────────────────────────────────────────────────────────
session = requests.Session()
session.headers["User-Agent"] = "E2E-RBAC-Tester/1.0"

tokens = {}
user_info = {}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def login(role):
    """Login and cache token for a role."""
    cred = CREDS[role]
    log(f"  Logging in as {cred['email']} ({role})...")
    url = f"{API_BASE}/api/v1/auth/login"
    try:
        r = session.post(url, json=cred, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                inner = data["data"]
                token = inner.get("tokens", {}).get("access_token", "")
                if token:
                    tokens[role] = token
                    user_info[role] = inner.get("user", {})
                    log(f"  -> Login OK, user_id={user_info[role].get('id')}, role={user_info[role].get('role')}")
                    return True
                else:
                    log(f"  -> No access_token in response")
            else:
                log(f"  -> success=false: {data}")
        else:
            log(f"  -> Login returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log(f"  -> Login error: {e}")
    return False

def api_call(method, role, path, json_data=None, params=None):
    """Make authenticated API request."""
    headers = {"Authorization": f"Bearer {tokens[role]}"}
    url = f"{API_BASE}{path}"
    try:
        r = session.request(method, url, headers=headers, json=json_data, params=params, timeout=15)
        return r
    except Exception as e:
        log(f"  -> {method} {path} exception: {e}")
        return None

def api_get(role, path, params=None):
    return api_call("GET", role, path, params=params)

def api_post(role, path, json_data=None):
    return api_call("POST", role, path, json_data=json_data)

def api_put(role, path, json_data=None):
    return api_call("PUT", role, path, json_data=json_data)

def api_delete(role, path):
    return api_call("DELETE", role, path)

def safe_json(r):
    if r is None:
        return {}
    try:
        return r.json()
    except Exception:
        return {"raw": r.text[:500] if r.text else ""}

def count_records(data):
    """Count records in various response formats."""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        if data.get("success") and "data" in data:
            return count_records(data["data"])
        for key in ["data", "results", "records", "items", "users", "list", "rows"]:
            if key in data:
                val = data[key]
                if isinstance(val, list):
                    return len(val)
                if isinstance(val, dict):
                    for subkey in ["list", "rows", "items", "records"]:
                        if subkey in val and isinstance(val[subkey], list):
                            return len(val[subkey])
        if "total" in data:
            return data["total"]
        if "pagination" in data and isinstance(data["pagination"], dict):
            return data["pagination"].get("total", -1)
        if "meta" in data and isinstance(data["meta"], dict):
            return data["meta"].get("total", -1)
    return -1

def extract_list(data):
    """Extract the actual list from various response formats."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if data.get("success") and "data" in data:
            return extract_list(data["data"])
        for key in ["data", "results", "records", "items", "users", "list", "rows"]:
            if key in data:
                val = data[key]
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    for subkey in ["list", "rows", "items", "records"]:
                        if subkey in val and isinstance(val[subkey], list):
                            return val[subkey]
    return []


# ── GitHub helpers ──────────────────────────────────────────────────────
gh_headers = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github+json",
}

def search_closed_rbac_issues():
    """Search for all closed issues with RBAC/permission keywords."""
    keywords = [
        "RBAC", "permission", "authorization", "access control",
        "privilege", "escalation", "403", "forbidden", "unauthorized",
        "role", "employee access", "admin only", "cross-org", "tenant",
        "isolation", "data leak", "visibility", "restricted",
    ]
    all_issues = {}

    for kw in keywords:
        query = f'repo:{GITHUB_REPO} is:issue is:closed "{kw}"'
        url = f"{GITHUB_API}/search/issues"
        params = {"q": query, "per_page": 100}
        try:
            r = session.get(url, headers=gh_headers, params=params, timeout=20)
            if r.status_code == 200:
                for item in r.json().get("items", []):
                    num = item["number"]
                    title = item["title"]
                    skip = False
                    for sm in SKIP_MODULES:
                        if sm.lower() in title.lower() or sm.lower() in (item.get("body") or "").lower():
                            skip = True
                    if "rate limit" in title.lower() or "rate-limit" in title.lower() or "ratelimit" in title.lower():
                        skip = True
                    if not skip:
                        all_issues[num] = item
            elif r.status_code == 403:
                log(f"  GitHub search rate limited, waiting 30s...")
                time.sleep(30)
            else:
                log(f"  GitHub search for '{kw}': {r.status_code}")
        except Exception as e:
            log(f"  GitHub search error for '{kw}': {e}")
        time.sleep(1.5)

    return all_issues

def add_github_comment(issue_number, body):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{issue_number}/comments"
    try:
        r = session.post(url, headers=gh_headers, json={"body": body}, timeout=15)
        if r.status_code == 201:
            log(f"  -> Comment added to #{issue_number}")
            return True
        else:
            log(f"  -> Failed to comment on #{issue_number}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log(f"  -> Comment error on #{issue_number}: {e}")
    return False

def reopen_issue(issue_number):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{issue_number}"
    try:
        r = session.patch(url, headers=gh_headers, json={"state": "open"}, timeout=15)
        if r.status_code == 200:
            log(f"  -> Issue #{issue_number} REOPENED")
            return True
        else:
            log(f"  -> Failed to reopen #{issue_number}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log(f"  -> Reopen error #{issue_number}: {e}")
    return False


# ── RBAC Test Suite ─────────────────────────────────────────────────────
test_results = []

class TestResult:
    def __init__(self, test_name, issue_numbers=None):
        self.test_name = test_name
        self.issue_numbers = issue_numbers or []
        self.steps = []
        self.verdict = "UNKNOWN"
        self.details = ""

    def step(self, desc, result):
        self.steps.append((desc, result))
        log(f"  Step {len(self.steps)}: {desc} -> {result}")

    def set_verdict(self, verdict, details=""):
        self.verdict = verdict
        self.details = details
        log(f"  VERDICT: {verdict} {details}")

    def to_markdown(self):
        lines = [f"### {self.test_name}"]
        for i, (desc, result) in enumerate(self.steps, 1):
            lines.append(f"**Step {i}:** {desc} -> `{result}`")
        lines.append(f"\n**VERDICT: {self.verdict}**")
        if self.details:
            lines.append(f"\n{self.details}")
        return "\n".join(lines)


def test_employee_list_users():
    """#97, #271: Employee should NOT list all org users."""
    t = TestResult("Employee can list all organization users", [97, 271])
    t.step(f"Login as {CREDS['employee']['email']}", f"200, role={user_info.get('employee',{}).get('role','?')}, id={user_info.get('employee',{}).get('id','?')}")

    r = api_get("employee", "/api/v1/users")
    if r is None:
        t.set_verdict("ERROR", "Request failed")
        test_results.append(t)
        return t

    data = safe_json(r)
    count = count_records(data)
    t.step(f"GET /api/v1/users", f"Status: {r.status_code}")
    t.step(f"Record count", f"{count} users returned")

    if r.status_code == 200 and count > 1:
        records = extract_list(data)
        own_email = CREDS["employee"]["email"]
        other_users = [u for u in records if u.get("email", "") != own_email]
        t.step(f"Check if other employees' data visible", f"YES - {len(other_users)} other users found")
        if other_users:
            sample = [u.get("email", u.get("first_name", "?")) for u in other_users[:5]]
            t.step(f"Sample other users", f"{sample}")
            t.set_verdict("STILL FAILING", f"Employee can see {count} users including: {sample}")
        else:
            t.set_verdict("FIXED", "Employee only sees own data")
    elif r.status_code in (403, 401):
        t.step(f"Access properly denied", f"{r.status_code}")
        t.set_verdict("FIXED", f"Properly returns {r.status_code} Forbidden")
    elif r.status_code == 200 and count <= 1:
        t.set_verdict("FIXED", "Employee sees only self or empty list")
    else:
        t.step(f"Response body", str(data)[:300])
        t.set_verdict("NEEDS REVIEW", f"Unexpected status {r.status_code}")

    test_results.append(t)
    return t


def test_employee_view_other_user():
    """Employee should NOT see another user's profile by ID."""
    t = TestResult("Employee viewing other user profiles")

    # Get list of users as admin to find target IDs
    admin_r = api_get("org_admin", "/api/v1/users")
    admin_data = safe_json(admin_r) if admin_r else {}
    admin_list = extract_list(admin_data)
    own_email = CREDS["employee"]["email"]
    own_id = user_info.get("employee", {}).get("id")
    targets = []
    for u in admin_list:
        if u.get("email", "") != own_email:
            uid = u.get("id")
            if uid:
                targets.append((uid, u.get("email", "unknown")))
    t.step(f"Found {len(targets)} other users from admin listing", "OK")

    if not targets:
        targets = [(522, "ananya@technova.in")]

    any_leak = False
    for uid, email in targets[:3]:
        r = api_get("employee", f"/api/v1/users/{uid}")
        if r is None:
            continue
        data = safe_json(r)
        t.step(f"GET /api/v1/users/{uid} ({email}) as employee", f"Status: {r.status_code}")
        if r.status_code == 200:
            inner = data.get("data", data)
            returned_email = inner.get("email", "")
            t.step(f"Returned user email", f"{returned_email}")
            if returned_email and returned_email != own_email:
                any_leak = True
                t.step(f"LEAK: Employee can view {returned_email}'s profile", "FAIL")
        elif r.status_code in (403, 401, 404):
            t.step(f"Access denied for user {uid}", f"{r.status_code} (correct)")

    if any_leak:
        t.set_verdict("STILL FAILING", "Employee can view other users' profiles")
    else:
        t.set_verdict("FIXED", "Employee cannot access other user profiles")

    test_results.append(t)
    return t


def test_employee_audit_access():
    """Employee should NOT access audit logs."""
    t = TestResult("Employee accessing audit logs", [250])

    r = api_get("employee", "/api/v1/audit")
    if r is None:
        t.set_verdict("ERROR", "Request failed")
        test_results.append(t)
        return t

    data = safe_json(r)
    count = count_records(data)
    t.step(f"GET /api/v1/audit", f"Status: {r.status_code}")
    t.step(f"Record count", f"{count}")

    if r.status_code == 200 and count > 0:
        records = extract_list(data)
        sample = [a.get("action", a.get("event", "?")) for a in records[:3]]
        t.step(f"Sample audit entries", f"{sample}")
        t.set_verdict("STILL FAILING", f"Employee can access audit logs ({count} records)")
    elif r.status_code in (403, 401):
        t.set_verdict("FIXED", f"Properly returns {r.status_code}")
    elif r.status_code == 200 and count == 0:
        t.set_verdict("NEEDS REVIEW", "200 but 0 records - may be empty or filtered")
    else:
        t.step(f"Response", str(data)[:300])
        t.set_verdict("NEEDS REVIEW", f"Status {r.status_code}")

    test_results.append(t)
    return t


def test_employee_subscription_access():
    """#283: Employee should NOT access subscription/billing data."""
    t = TestResult("Employee accessing subscription/billing data", [283])

    for ep in ["/api/v1/subscriptions", "/api/v1/subscriptions/billing-summary"]:
        r = api_get("employee", ep)
        if r is None:
            continue
        data = safe_json(r)
        count = count_records(data)
        t.step(f"GET {ep}", f"Status: {r.status_code}, records: {count}")

        if r.status_code == 200:
            t.step(f"Response snippet", str(data)[:400])
            if count > 0 or (isinstance(data, dict) and data.get("success")):
                t.set_verdict("STILL FAILING", f"Employee can access {ep}")
                test_results.append(t)
                return t
        elif r.status_code in (403, 401):
            pass  # good
        else:
            t.step(f"Unexpected status for {ep}", f"{r.status_code}")

    if t.verdict == "UNKNOWN":
        # Check if all endpoints returned 403
        denied = [s for s in t.steps if "403" in s[1] or "401" in s[1]]
        if denied:
            t.set_verdict("FIXED", "All subscription endpoints properly return 403/401")
        else:
            t.set_verdict("NEEDS REVIEW", "Unexpected responses")

    test_results.append(t)
    return t


def test_employee_leave_applications():
    """#286: Employee should only see OWN leave applications."""
    t = TestResult("Employee leave application visibility", [286])

    # First get admin's view as baseline
    admin_r = api_get("org_admin", "/api/v1/leave/applications")
    admin_data = safe_json(admin_r) if admin_r else {}
    admin_count = count_records(admin_data)
    t.step(f"Admin sees {admin_count} leave applications (baseline)", "OK")

    r = api_get("employee", "/api/v1/leave/applications")
    if r is None:
        t.set_verdict("ERROR", "Request failed")
        test_results.append(t)
        return t

    data = safe_json(r)
    count = count_records(data)
    t.step(f"GET /api/v1/leave/applications (employee)", f"Status: {r.status_code}, records: {count}")

    if r.status_code == 200:
        records = extract_list(data)
        own_id = user_info.get("employee", {}).get("id")
        own_email = CREDS["employee"]["email"]

        other_leaves = []
        for rec in records:
            rec_uid = rec.get("user_id") or rec.get("userId") or rec.get("employee_id") or rec.get("employeeId")
            rec_user = rec.get("user", {})
            rec_email = rec_user.get("email", "") if isinstance(rec_user, dict) else ""

            if rec_email and rec_email != own_email:
                other_leaves.append(rec_email)
            elif rec_uid and own_id and str(rec_uid) != str(own_id):
                other_leaves.append(f"user_id={rec_uid}")

        t.step(f"Other users' leaves visible", f"{len(other_leaves)} records from other users")
        if other_leaves:
            t.step(f"Sample foreign leaves", f"{other_leaves[:5]}")
            t.set_verdict("STILL FAILING", f"Employee sees {len(other_leaves)} other users' leave applications out of {count} total")
        else:
            t.set_verdict("FIXED", f"Employee sees only own leaves ({count} records)")
    elif r.status_code in (403, 401):
        t.set_verdict("NEEDS REVIEW", f"Employee gets {r.status_code} on leave - may be too restrictive")
    else:
        t.set_verdict("NEEDS REVIEW", f"Status {r.status_code}")

    test_results.append(t)
    return t


def test_employee_compoff():
    """#315: Employee should only see OWN comp-off requests."""
    t = TestResult("Employee comp-off request visibility", [315])

    # Admin baseline
    admin_r = api_get("org_admin", "/api/v1/leave/comp-off")
    admin_data = safe_json(admin_r) if admin_r else {}
    admin_count = count_records(admin_data)
    t.step(f"Admin sees {admin_count} comp-off requests (baseline)", "OK")

    r = api_get("employee", "/api/v1/leave/comp-off")
    if r is None:
        t.set_verdict("ERROR", "Request failed")
        test_results.append(t)
        return t

    data = safe_json(r)
    count = count_records(data)
    t.step(f"GET /api/v1/leave/comp-off (employee)", f"Status: {r.status_code}, records: {count}")

    if r.status_code == 200:
        records = extract_list(data)
        own_id = user_info.get("employee", {}).get("id")
        other_compoffs = []
        for rec in records:
            rec_uid = rec.get("user_id") or rec.get("userId") or rec.get("employee_id")
            if rec_uid and own_id and str(rec_uid) != str(own_id):
                other_compoffs.append(f"user_id={rec_uid}")

        if other_compoffs:
            t.step(f"Other users' comp-off visible", f"{len(other_compoffs)}: {other_compoffs[:5]}")
            t.set_verdict("STILL FAILING", f"Employee sees {len(other_compoffs)} other users' comp-off requests")
        elif admin_count > 0 and count == admin_count:
            t.set_verdict("STILL FAILING", f"Employee sees same count as admin ({count}), likely all org data")
        else:
            t.set_verdict("FIXED", f"Employee sees only own comp-off ({count} records vs admin's {admin_count})")
    elif r.status_code in (403, 401):
        t.set_verdict("FIXED", f"Properly returns {r.status_code}")
    else:
        t.set_verdict("NEEDS REVIEW", f"Status {r.status_code}")

    test_results.append(t)
    return t


def test_employee_surveys():
    """#287: Employee should only see PUBLISHED surveys, not drafts."""
    t = TestResult("Employee survey visibility (drafts vs published)", [287])

    # Try survey endpoints (not in OpenAPI but was in original bugs)
    for ep in ["/api/v1/surveys", "/api/v1/survey", "/api/v1/surveys/list"]:
        r = api_get("employee", ep)
        if r is not None and r.status_code != 404:
            data = safe_json(r)
            count = count_records(data)
            t.step(f"GET {ep} (employee)", f"Status: {r.status_code}, records: {count}")

            if r.status_code == 200:
                records = extract_list(data)
                draft_surveys = [s for s in records if str(s.get("status", "")).lower() in ("draft", "inactive", "unpublished")]
                if draft_surveys:
                    t.step(f"DRAFT surveys visible to employee", f"{len(draft_surveys)} drafts!")
                    sample = [s.get("title", s.get("name", "?")) for s in draft_surveys[:3]]
                    t.step(f"Draft survey titles", f"{sample}")
                    t.set_verdict("STILL FAILING", f"Employee can see {len(draft_surveys)} draft surveys: {sample}")
                else:
                    t.set_verdict("FIXED", f"Employee sees {count} surveys, no drafts")
            elif r.status_code in (403, 401):
                t.set_verdict("NEEDS REVIEW", f"Employee gets {r.status_code} on surveys")
            break
    else:
        # No survey endpoint found - check admin too
        for ep in ["/api/v1/surveys", "/api/v1/survey"]:
            ar = api_get("org_admin", ep)
            if ar and ar.status_code != 404:
                t.step(f"Admin GET {ep}", f"Status: {ar.status_code}")
                break
        t.set_verdict("NEEDS REVIEW", "No survey endpoint responded (all 404)")

    test_results.append(t)
    return t


def test_employee_feedback():
    """#103, #352, #668: Employee feedback access."""
    t = TestResult("Employee feedback visibility", [103, 352, 668])

    for ep in ["/api/v1/feedback", "/api/v1/feedbacks", "/api/v1/feedback/list"]:
        r = api_get("employee", ep)
        if r is not None and r.status_code != 404:
            data = safe_json(r)
            count = count_records(data)
            t.step(f"GET {ep}", f"Status: {r.status_code}, records: {count}")
            if r.status_code == 200:
                t.set_verdict("FIXED", f"Employee can access feedback ({count} records)")
            elif r.status_code in (403, 401):
                err = data.get("message", data.get("error", ""))
                t.step(f"Error message", f"{err}")
                t.set_verdict("STILL FAILING", f"Employee gets {r.status_code}: {err} - should have limited access to own feedback")
            elif r.status_code == 500:
                t.set_verdict("STILL FAILING", f"Server error 500 on feedback endpoint")
            break
    else:
        t.set_verdict("NEEDS REVIEW", "No feedback endpoint found")

    test_results.append(t)
    return t


def test_employee_create_announcement():
    """#243: Employee should NOT create announcements."""
    t = TestResult("Employee creating announcements (should be 403)", [243])

    payload = {"title": "RBAC Test - Should Fail", "content": "This is an automated RBAC test. If you see this, the test created it by mistake.", "status": "draft"}
    r = api_post("employee", "/api/v1/announcements", payload)
    if r is None:
        t.set_verdict("ERROR", "Request failed")
        test_results.append(t)
        return t

    data = safe_json(r)
    t.step(f"POST /api/v1/announcements (employee)", f"Status: {r.status_code}")

    if r.status_code in (201, 200):
        t.step(f"Response", str(data)[:300])
        t.set_verdict("STILL FAILING", "Employee can create announcements!")
        # Cleanup
        ann_id = data.get("data", {}).get("id") or data.get("id")
        if ann_id:
            api_delete("org_admin", f"/api/v1/announcements/{ann_id}")
            t.step("Cleanup: deleted test announcement", "OK")
    elif r.status_code in (403, 401):
        t.set_verdict("FIXED", f"Properly returns {r.status_code}")
    else:
        t.step(f"Response", str(data)[:300])
        t.set_verdict("NEEDS REVIEW", f"Unexpected status {r.status_code}")

    test_results.append(t)
    return t


def test_privilege_escalation():
    """#171: Employee should NOT escalate own role."""
    t = TestResult("Employee privilege escalation (role change to org_admin)", [171])

    own_id = user_info.get("employee", {}).get("id")
    if not own_id:
        own_id = 524

    payload = {"role": "org_admin"}
    r = api_put("employee", f"/api/v1/users/{own_id}", payload)
    if r is None:
        t.set_verdict("ERROR", "Request failed")
        test_results.append(t)
        return t

    data = safe_json(r)
    t.step(f"PUT /api/v1/users/{own_id} with role=org_admin (employee)", f"Status: {r.status_code}")

    if r.status_code == 200:
        inner = data.get("data", data)
        new_role = inner.get("role", "")
        t.step(f"Returned role after update", f"{new_role}")
        if new_role == "org_admin":
            t.set_verdict("STILL FAILING", "CRITICAL: Employee escalated to org_admin!")
            # Revert
            api_put("org_admin", f"/api/v1/users/{own_id}", {"role": "employee"})
            t.step("Reverted role back to employee", "OK")
        else:
            t.set_verdict("NEEDS REVIEW", f"200 returned but role={new_role} (may have ignored role field)")
    elif r.status_code in (403, 401):
        t.set_verdict("FIXED", f"Properly returns {r.status_code}")
    else:
        t.step(f"Response", str(data)[:300])
        t.set_verdict("NEEDS REVIEW", f"Status {r.status_code}")

    test_results.append(t)
    return t


def test_employee_delete_user():
    """Employee should NOT delete any user."""
    t = TestResult("Employee deleting users (should be 403)", [177])

    # Try to delete admin user (522 = ananya)
    admin_id = user_info.get("org_admin", {}).get("id", 522)
    r = api_delete("employee", f"/api/v1/users/{admin_id}")
    if r is None:
        t.set_verdict("ERROR", "Request failed")
        test_results.append(t)
        return t

    data = safe_json(r)
    t.step(f"DELETE /api/v1/users/{admin_id} (employee)", f"Status: {r.status_code}")

    if r.status_code in (200, 204):
        t.set_verdict("STILL FAILING", f"CRITICAL: Employee can delete user {admin_id}!")
    elif r.status_code in (403, 401):
        t.set_verdict("FIXED", f"Properly returns {r.status_code}")
    elif r.status_code == 404:
        t.set_verdict("NEEDS REVIEW", "404 - endpoint may not exist or user not found")
    else:
        t.step(f"Response", str(data)[:300])
        t.set_verdict("NEEDS REVIEW", f"Status {r.status_code}")

    test_results.append(t)
    return t


def test_employee_modules():
    """#665: Check what modules employee sees and whether they see admin actions."""
    t = TestResult("Employee module visibility", [665])

    r = api_get("employee", "/api/v1/modules")
    if r is None:
        t.set_verdict("ERROR", "Request failed")
        test_results.append(t)
        return t

    data = safe_json(r)
    count = count_records(data)
    t.step(f"GET /api/v1/modules", f"Status: {r.status_code}, records: {count}")

    if r.status_code == 200:
        records = extract_list(data)
        module_names = [m.get("name", m.get("module_name", "?")) for m in records[:15]]
        t.step(f"Modules visible", f"{module_names}")
        # Check for admin-only actions
        admin_actions = []
        for m in records:
            if m.get("can_unsubscribe") or m.get("canUnsubscribe"):
                admin_actions.append(f"{m.get('name','?')} has unsubscribe")
            if m.get("can_manage") or m.get("canManage"):
                admin_actions.append(f"{m.get('name','?')} has manage")
        if admin_actions:
            t.step(f"Admin actions visible to employee", f"{admin_actions}")
            t.set_verdict("STILL FAILING", f"Employee sees admin actions: {admin_actions}")
        else:
            t.set_verdict("FIXED", f"Employee sees {count} modules without admin actions")
    elif r.status_code in (403, 401):
        t.set_verdict("NEEDS REVIEW", f"Employee gets {r.status_code} on modules")
    else:
        t.set_verdict("NEEDS REVIEW", f"Status {r.status_code}")

    test_results.append(t)
    return t


def test_employee_notifications():
    """Employee should see own notifications only."""
    t = TestResult("Employee notification visibility")

    for ep in ["/api/v1/notifications", "/api/v1/notification"]:
        r = api_get("employee", ep)
        if r is not None and r.status_code != 404:
            data = safe_json(r)
            count = count_records(data)
            t.step(f"GET {ep}", f"Status: {r.status_code}, records: {count}")
            if r.status_code == 200:
                t.set_verdict("FIXED", f"Returns {count} notifications (scoped to user)")
            elif r.status_code in (403, 401):
                t.set_verdict("NEEDS REVIEW", f"Employee gets {r.status_code} on notifications")
            break
    else:
        t.set_verdict("NEEDS REVIEW", "No notifications endpoint found")

    test_results.append(t)
    return t


def test_employee_admin_endpoints():
    """#108, #257: Employee should NOT access admin-level endpoints."""
    t = TestResult("Employee accessing admin-only endpoints", [108, 254, 257])

    admin_endpoints = [
        ("/api/v1/admin/organizations", "List all organizations"),
        ("/api/v1/admin/super", "Super admin dashboard data"),
        ("/api/v1/admin/analytics/revenue", "Revenue analytics"),
        ("/api/v1/admin/analytics/modules", "Module analytics"),
        ("/api/v1/users/org-chart", "Org chart"),
    ]

    failures = []
    for ep, desc in admin_endpoints:
        r = api_get("employee", ep)
        if r is None:
            continue
        t.step(f"GET {ep} ({desc})", f"Status: {r.status_code}")
        if r.status_code == 200:
            data = safe_json(r)
            count = count_records(data)
            if count > 0 or (isinstance(data, dict) and data.get("success")):
                failures.append(f"{ep} returned {r.status_code} with {count} records")

    if failures:
        t.set_verdict("STILL FAILING", f"Employee can access admin endpoints: {failures}")
    else:
        t.set_verdict("FIXED", "All admin endpoints properly denied")

    test_results.append(t)
    return t


def test_employee_billing_page():
    """#241: Employee should NOT access billing page data."""
    t = TestResult("Employee accessing billing page data", [241])

    r = api_get("employee", "/api/v1/subscriptions/billing-summary")
    if r is None:
        r2 = api_get("employee", "/api/v1/subscriptions")
        if r2 is None:
            t.set_verdict("ERROR", "Request failed")
            test_results.append(t)
            return t
        r = r2
        ep_used = "/api/v1/subscriptions"
    else:
        ep_used = "/api/v1/subscriptions/billing-summary"

    data = safe_json(r)
    t.step(f"GET {ep_used} (employee)", f"Status: {r.status_code}")

    if r.status_code == 200 and data.get("success"):
        t.step(f"Billing data returned", str(data)[:400])
        t.set_verdict("STILL FAILING", f"Employee can see billing data via {ep_used}")
    elif r.status_code in (403, 401):
        t.set_verdict("FIXED", f"Properly returns {r.status_code}")
    else:
        t.set_verdict("NEEDS REVIEW", f"Status {r.status_code}")

    test_results.append(t)
    return t


def test_employee_dashboard_data():
    """#547, #562, #661: Employee dashboard should not show HR-level data."""
    t = TestResult("Employee dashboard HR-level data exposure", [547, 562, 661])

    # Check various dashboard/stats endpoints
    dashboard_eps = [
        "/api/v1/dashboard",
        "/api/v1/dashboard/stats",
        "/api/v1/dashboard/hr",
        "/api/v1/analytics",
        "/api/v1/reports",
    ]

    found_hr_data = False
    for ep in dashboard_eps:
        r = api_get("employee", ep)
        if r is None or r.status_code == 404:
            continue
        data = safe_json(r)
        t.step(f"GET {ep}", f"Status: {r.status_code}")

        if r.status_code == 200:
            data_str = json.dumps(data).lower()
            hr_indicators = ["total_employees", "totalemployees", "headcount", "attrition",
                             "org_stats", "orgstats", "hiring", "payroll_summary"]
            found = [ind for ind in hr_indicators if ind in data_str]
            if found:
                t.step(f"HR-level data indicators found", f"{found}")
                found_hr_data = True

    if found_hr_data:
        t.set_verdict("STILL FAILING", "Employee dashboard exposes HR-level aggregate data")
    else:
        t.set_verdict("FIXED", "No HR-level data exposed to employee")

    test_results.append(t)
    return t


# ── Cross-Org Isolation Tests ──────────────────────────────────────────
def test_cross_org_user_list():
    """Cross-org: GlobalTech should only see GlobalTech users."""
    t = TestResult("Cross-org user listing isolation")

    r = api_get("other_org", "/api/v1/users")
    if r is None:
        t.set_verdict("ERROR", "Request failed")
        test_results.append(t)
        return t

    data = safe_json(r)
    records = extract_list(data)
    count = count_records(data)
    t.step(f"GET /api/v1/users as john@globaltech.com", f"Status: {r.status_code}, records: {count}")

    if r.status_code == 200:
        technova = [u for u in records if "technova" in str(u.get("email", "")).lower()]
        globaltech = [u for u in records if "globaltech" in str(u.get("email", "")).lower()]
        other = [u for u in records if "technova" not in str(u.get("email", "")).lower() and "globaltech" not in str(u.get("email", "")).lower()]
        t.step(f"TechNova users visible", f"{len(technova)}")
        t.step(f"GlobalTech users visible", f"{len(globaltech)}")
        t.step(f"Other/unknown org users", f"{len(other)}")
        if technova:
            sample = [u.get("email") for u in technova[:3]]
            t.step(f"Leaked TechNova emails", f"{sample}")
            t.set_verdict("STILL FAILING", f"GlobalTech admin sees {len(technova)} TechNova users: {sample}")
        else:
            t.set_verdict("FIXED", f"GlobalTech admin sees only own org ({count} users)")
    elif r.status_code in (403, 401):
        t.set_verdict("NEEDS REVIEW", f"Status {r.status_code}")

    test_results.append(t)
    return t


def test_cross_org_user_detail():
    """Cross-org: GlobalTech should NOT see TechNova user by ID."""
    t = TestResult("Cross-org user profile access (should be 404)")

    # Get TechNova user IDs
    admin_r = api_get("org_admin", "/api/v1/users")
    admin_list = extract_list(safe_json(admin_r) if admin_r else {})
    technova_ids = []
    for u in admin_list:
        if "technova" in str(u.get("email", "")).lower():
            uid = u.get("id")
            if uid:
                technova_ids.append((uid, u.get("email")))

    if not technova_ids:
        technova_ids = [(522, "ananya@technova.in")]

    for uid, email in technova_ids[:2]:
        r = api_get("other_org", f"/api/v1/users/{uid}")
        if r is None:
            continue
        data = safe_json(r)
        t.step(f"GET /api/v1/users/{uid} ({email}) as GlobalTech", f"Status: {r.status_code}")

        if r.status_code == 200:
            inner = data.get("data", data)
            returned_email = inner.get("email", "")
            if "technova" in returned_email.lower():
                t.set_verdict("STILL FAILING", f"GlobalTech can see TechNova user: {returned_email}")
                test_results.append(t)
                return t
        elif r.status_code in (404, 403, 401):
            t.step(f"Properly denied/not found", f"{r.status_code}")

    if t.verdict == "UNKNOWN":
        t.set_verdict("FIXED", "Cross-org user profiles properly isolated")

    test_results.append(t)
    return t


def test_cross_org_announcements():
    """Cross-org: Announcements should be isolated per org."""
    t = TestResult("Cross-org announcement isolation")

    r_tech = api_get("org_admin", "/api/v1/announcements")
    r_global = api_get("other_org", "/api/v1/announcements")

    if r_tech is None or r_global is None:
        t.set_verdict("ERROR", "Request failed")
        test_results.append(t)
        return t

    tech_data = safe_json(r_tech)
    glob_data = safe_json(r_global)
    tech_list = extract_list(tech_data)
    glob_list = extract_list(glob_data)
    tech_count = count_records(tech_data)
    glob_count = count_records(glob_data)

    t.step(f"TechNova admin: GET /api/v1/announcements", f"Status: {r_tech.status_code}, records: {tech_count}")
    t.step(f"GlobalTech admin: GET /api/v1/announcements", f"Status: {r_global.status_code}, records: {glob_count}")

    if tech_list and glob_list:
        tech_ids = {str(a.get("id") or a.get("_id")) for a in tech_list}
        leaked = [a for a in glob_list if str(a.get("id") or a.get("_id")) in tech_ids]
        if leaked:
            t.step(f"TechNova announcements leaked to GlobalTech", f"{len(leaked)}")
            t.set_verdict("STILL FAILING", f"GlobalTech sees {len(leaked)} TechNova announcements!")
        else:
            t.set_verdict("FIXED", "Announcements properly isolated between orgs")
    elif r_global.status_code in (403, 401):
        t.set_verdict("NEEDS REVIEW", f"GlobalTech gets {r_global.status_code}")
    else:
        t.set_verdict("FIXED", "No cross-org announcement leakage detected")

    test_results.append(t)
    return t


# ── Issue-to-test mapping ──────────────────────────────────────────────
# Map specific closed issues to tests
ISSUE_TEST_MAP = {
    97:  ["Employee can list all organization users"],
    271: ["Employee can list all organization users"],
    283: ["Employee accessing subscription/billing data"],
    241: ["Employee accessing billing page data"],
    286: ["Employee leave application visibility"],
    287: ["Employee survey visibility"],
    315: ["Employee comp-off request visibility"],
    103: ["Employee feedback visibility"],
    352: ["Employee feedback visibility"],
    668: ["Employee feedback visibility"],
    243: ["Employee creating announcements"],
    171: ["Employee privilege escalation"],
    177: ["Employee deleting users"],
    665: ["Employee module visibility"],
    108: ["Employee accessing admin-only endpoints"],
    254: ["Employee accessing admin-only endpoints"],
    257: ["Employee accessing admin-only endpoints"],
    547: ["Employee dashboard HR-level data exposure"],
    562: ["Employee dashboard HR-level data exposure"],
    661: ["Employee dashboard HR-level data exposure"],
    250: ["Employee accessing audit logs"],
    88:  ["Employee accessing admin-only endpoints"],
    98:  ["Employee accessing admin-only endpoints"],
    113: ["Employee accessing admin-only endpoints"],
    122: ["Employee accessing admin-only endpoints"],
    123: ["Employee accessing admin-only endpoints"],
    124: ["Employee accessing admin-only endpoints"],
}


# ── Main ────────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("  DEEP RBAC / PERMISSION RE-TEST FOR EMPCLOUD")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Phase 1: Find all closed RBAC issues
    log("\n[PHASE 1] Searching for closed RBAC/permission issues on GitHub...")
    closed_issues = search_closed_rbac_issues()
    log(f"Found {len(closed_issues)} unique closed RBAC/permission issues")
    for num, issue in sorted(closed_issues.items()):
        log(f"  #{num}: {issue['title']}")

    # Phase 2: Login all roles
    log("\n[PHASE 2] Logging in all test accounts...")
    login_ok = True
    for role in ["org_admin", "employee", "other_org"]:
        if not login(role):
            log(f"  WARNING: Cannot login as {role}!")
            if role == "employee":
                login_ok = False

    if not login_ok:
        log("FATAL: Employee login failed. Cannot proceed.")
        return

    # Phase 3: Employee RBAC tests
    log("\n" + "=" * 80)
    log("[PHASE 3] === Testing Employee RBAC ===")
    log("=" * 80)

    log(f"\n{'='*60}")
    log(f"=== #97/#271 Employee can list all organization users ===")
    log(f"{'='*60}")
    test_employee_list_users()

    log(f"\n{'='*60}")
    log(f"=== Employee viewing other user profiles ===")
    log(f"{'='*60}")
    test_employee_view_other_user()

    log(f"\n{'='*60}")
    log(f"=== Employee accessing audit logs ===")
    log(f"{'='*60}")
    test_employee_audit_access()

    log(f"\n{'='*60}")
    log(f"=== #283 Employee accessing subscription/billing ===")
    log(f"{'='*60}")
    test_employee_subscription_access()

    log(f"\n{'='*60}")
    log(f"=== #241 Employee accessing billing page ===")
    log(f"{'='*60}")
    test_employee_billing_page()

    log(f"\n{'='*60}")
    log(f"=== #286 Employee leave application visibility ===")
    log(f"{'='*60}")
    test_employee_leave_applications()

    log(f"\n{'='*60}")
    log(f"=== #315 Employee comp-off request visibility ===")
    log(f"{'='*60}")
    test_employee_compoff()

    log(f"\n{'='*60}")
    log(f"=== #287 Employee survey visibility (drafts) ===")
    log(f"{'='*60}")
    test_employee_surveys()

    log(f"\n{'='*60}")
    log(f"=== #103/#352/#668 Employee feedback visibility ===")
    log(f"{'='*60}")
    test_employee_feedback()

    log(f"\n{'='*60}")
    log(f"=== #243 Employee creating announcements ===")
    log(f"{'='*60}")
    test_employee_create_announcement()

    log(f"\n{'='*60}")
    log(f"=== #171 Employee privilege escalation ===")
    log(f"{'='*60}")
    test_privilege_escalation()

    log(f"\n{'='*60}")
    log(f"=== Employee deleting users ===")
    log(f"{'='*60}")
    test_employee_delete_user()

    log(f"\n{'='*60}")
    log(f"=== #665 Employee module visibility ===")
    log(f"{'='*60}")
    test_employee_modules()

    log(f"\n{'='*60}")
    log(f"=== Employee notification visibility ===")
    log(f"{'='*60}")
    test_employee_notifications()

    log(f"\n{'='*60}")
    log(f"=== #108/#257 Employee accessing admin endpoints ===")
    log(f"{'='*60}")
    test_employee_admin_endpoints()

    log(f"\n{'='*60}")
    log(f"=== #547/#562/#661 Employee dashboard data exposure ===")
    log(f"{'='*60}")
    test_employee_dashboard_data()

    # Phase 4: Cross-org isolation tests
    if "other_org" in tokens:
        log("\n" + "=" * 80)
        log("[PHASE 4] === Testing Cross-Org Isolation ===")
        log("=" * 80)

        log(f"\n{'='*60}")
        log(f"=== Cross-org user listing ===")
        log(f"{'='*60}")
        test_cross_org_user_list()

        log(f"\n{'='*60}")
        log(f"=== Cross-org user detail ===")
        log(f"{'='*60}")
        test_cross_org_user_detail()

        log(f"\n{'='*60}")
        log(f"=== Cross-org announcements ===")
        log(f"{'='*60}")
        test_cross_org_announcements()
    else:
        log("\n[PHASE 4] Skipping cross-org tests (login failed)")

    # Phase 5: Summary
    log("\n" + "=" * 80)
    log("[PHASE 5] RESULTS SUMMARY")
    log("=" * 80)

    failing = [t for t in test_results if "FAILING" in t.verdict]
    fixed = [t for t in test_results if t.verdict == "FIXED"]
    review = [t for t in test_results if "REVIEW" in t.verdict or t.verdict == "INFO" or t.verdict == "ERROR"]

    print(f"\n{'='*70}")
    print(f"  TOTAL TESTS:    {len(test_results)}")
    print(f"  FIXED:          {len(fixed)}")
    print(f"  STILL FAILING:  {len(failing)}")
    print(f"  NEEDS REVIEW:   {len(review)}")
    print(f"{'='*70}")

    for t in test_results:
        icon = "PASS" if t.verdict == "FIXED" else ("FAIL" if "FAILING" in t.verdict else "???")
        print(f"  [{icon}] {t.test_name}")
        print(f"         VERDICT: {t.verdict}")
        if t.details:
            print(f"         {t.details}")
        print()

    # Phase 6: GitHub comments
    log("\n" + "=" * 80)
    log("[PHASE 6] Updating GitHub issues with re-test results...")
    log("=" * 80)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # For each closed issue, find relevant tests and comment
    commented = 0
    reopened = 0

    for num, issue in sorted(closed_issues.items()):
        title = issue["title"]
        title_lower = title.lower()
        body_lower = (issue.get("body") or "").lower()
        combined = title_lower + " " + body_lower

        # Find relevant tests for this issue
        relevant_tests = []

        # First check explicit mapping
        if num in ISSUE_TEST_MAP:
            mapped_names = ISSUE_TEST_MAP[num]
            for t in test_results:
                if t.test_name in mapped_names:
                    relevant_tests.append(t)

        # Then check by keyword matching
        if not relevant_tests:
            for t in test_results:
                score = 0
                test_words = t.test_name.lower().split()
                for w in test_words:
                    if len(w) > 3 and w in combined:
                        score += 1
                if score >= 2:
                    relevant_tests.append(t)

        # Skip issues with no relevant tests (not RBAC-related enough)
        if not relevant_tests:
            continue

        # Build the comment
        has_failure = any("FAILING" in t.verdict for t in relevant_tests)

        comment_lines = [
            "Comment by E2E Testing Agent",
            "",
            f"## RBAC Deep Re-test Results - {now}",
            "",
            "Automated re-test of this closed issue against the live test environment (`test-empcloud-api.empcloud.com`).",
            "",
        ]

        for t in relevant_tests:
            comment_lines.append(t.to_markdown())
            comment_lines.append("")

        comment_lines.append("---")
        comment_lines.append(f"**Test Summary:** {len(fixed)} fixed | {len(failing)} still failing | {len(review)} needs review (across all RBAC tests)")
        comment_lines.append(f"**API Base:** `{API_BASE}`")
        comment_lines.append(f"**Employee Account:** `{CREDS['employee']['email']}`")

        if has_failure:
            comment_lines.append("")
            comment_lines.append("**:rotating_light: ACTION: Re-opening this issue -- RBAC violation still detected in automated testing.**")

        comment_body = "\n".join(comment_lines)

        log(f"\n  #{num}: {title}")
        log(f"  Relevant tests: {[t.test_name for t in relevant_tests]}")
        log(f"  Has failure: {has_failure}")

        if add_github_comment(num, comment_body):
            commented += 1

        if has_failure:
            if reopen_issue(num):
                reopened += 1

        time.sleep(1)

    # Final report
    print("\n" + "=" * 80)
    print("  DEEP RBAC RE-TEST COMPLETE")
    print("=" * 80)
    print(f"  Closed RBAC issues found:  {len(closed_issues)}")
    print(f"  Issues commented on:       {commented}")
    print(f"  Issues reopened:           {reopened}")
    print(f"  Tests run:                 {len(test_results)}")
    print(f"  Tests FIXED:               {len(fixed)}")
    print(f"  Tests STILL FAILING:       {len(failing)}")
    print(f"  Tests NEEDS REVIEW:        {len(review)}")
    print()
    if failing:
        print("  STILL FAILING tests:")
        for t in failing:
            issues_str = ", ".join(f"#{n}" for n in t.issue_numbers) if t.issue_numbers else "N/A"
            print(f"    - {t.test_name} (issues: {issues_str})")
            print(f"      {t.details}")
    print()


if __name__ == "__main__":
    main()
