#!/usr/bin/env python3
"""
Comprehensive API Security & Functionality Tester for EMP Cloud HRMS
Tests: endpoint discovery, CRUD, RBAC, cross-org isolation, input validation, data consistency
Files bugs via GitHub API.
"""
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import time
import traceback

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Disable SSL verification for test environment
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = "https://test-empcloud-api.empcloud.com"
API = f"{BASE}/api/v1"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

CREDS = {
    "org_admin": ("ananya@technova.in", "Welcome@123"),
    "employee": ("priya@technova.in", "Welcome@123"),
    "super_admin": ("admin@empcloud.com", "SuperAdmin@2026"),
    "other_org": ("john@globaltech.com", "Welcome@123"),
}

HEADERS_BASE = {
    "User-Agent": "EmpCloud-API-Tester/1.0",
    "Origin": "https://test-empcloud.empcloud.com",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

tokens = {}
bugs_found = []
existing_issues = []

# ── Helpers ──────────────────────────────────────────────────────────────

def api_call(method, url, data=None, token=None, timeout=20):
    """Make an API call and return (status, headers, body_dict_or_text)"""
    headers = dict(HEADERS_BASE)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, dict(resp.headers), json.loads(raw)
        except json.JSONDecodeError:
            return resp.status, dict(resp.headers), raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, {}, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {}, raw
    except Exception as e:
        return 0, {}, str(e)


def login(email, password):
    """Login and return token"""
    for path in ["/api/v1/auth/login", "/auth/login", "/api/v1/login", "/login"]:
        url = BASE + path
        status, _, body = api_call("POST", url, {"email": email, "password": password})
        if status == 200 and isinstance(body, dict):
            # Check data.tokens.access_token (EmpCloud pattern)
            data = body.get("data", {})
            if isinstance(data, dict):
                tkns = data.get("tokens", {})
                if isinstance(tkns, dict) and tkns.get("access_token"):
                    print(f"  [LOGIN OK] {email} via {path} (data.tokens.access_token)")
                    return tkns["access_token"]
                # Fallback: data.token or data.access_token
                for key in ["access_token", "token", "jwt", "authToken"]:
                    if data.get(key):
                        print(f"  [LOGIN OK] {email} via {path} (data.{key})")
                        return data[key]
            # Top-level token
            for key in ["token", "access_token", "jwt", "authToken"]:
                if body.get(key):
                    print(f"  [LOGIN OK] {email} via {path} ({key})")
                    return body[key]
            print(f"  [LOGIN 200 but no token] {email} via {path}")
    print(f"  [LOGIN FAIL] {email}")
    return None


def fetch_existing_issues():
    """Get existing GitHub issues to avoid duplicates"""
    global existing_issues
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues?state=all&per_page=100"
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "EmpCloud-API-Tester/1.0",
    }
    try:
        for page in range(1, 5):
            req = urllib.request.Request(f"{url}&page={page}", headers=headers)
            resp = urllib.request.urlopen(req, timeout=15, context=ctx)
            issues = json.loads(resp.read().decode())
            if not issues:
                break
            existing_issues.extend(issues)
        print(f"  Fetched {len(existing_issues)} existing issues")
    except Exception as e:
        print(f"  Warning: Could not fetch existing issues: {e}")


def is_duplicate(title):
    """Check if similar issue already exists"""
    title_lower = title.lower()
    for issue in existing_issues:
        existing = issue.get("title", "").lower()
        # Check for high similarity
        words_new = set(title_lower.split())
        words_existing = set(existing.split())
        if len(words_new) > 2 and len(words_new & words_existing) / len(words_new) > 0.6:
            return issue["number"]
    return None


def file_bug(title, body, labels=None):
    """File a GitHub issue"""
    if labels is None:
        labels = ["bug"]

    dup = is_duplicate(title)
    if dup:
        print(f"  [SKIP DUPLICATE] #{dup}: {title}")
        return None

    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "EmpCloud-API-Tester/1.0",
        "Content-Type": "application/json",
    }
    payload = {"title": title, "body": body, "labels": labels}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        result = json.loads(resp.read().decode())
        num = result.get("number")
        print(f"  [BUG FILED] #{num}: {title}")
        existing_issues.append({"number": num, "title": title})
        bugs_found.append({"number": num, "title": title})
        return num
    except Exception as e:
        print(f"  [BUG FILE FAIL] {title}: {e}")
        return None


# ── Phase 1: Endpoint Discovery ─────────────────────────────────────────

def discover_endpoints():
    """Try all endpoints with org admin token and record results"""
    print("\n" + "="*80)
    print("PHASE 1: ENDPOINT DISCOVERY")
    print("="*80)

    token = tokens["org_admin"]

    endpoints = [
        # Core
        ("GET", "/users"),
        ("GET", "/employees"),
        ("GET", "/departments"),
        ("GET", "/locations"),
        ("GET", "/designations"),
        ("GET", "/organizations"),
        ("GET", "/org-chart"),
        # Attendance
        ("GET", "/attendance"),
        ("GET", "/attendance/shifts"),
        ("GET", "/attendance/summary"),
        ("GET", "/attendance/logs"),
        ("GET", "/attendance/settings"),
        # Leave
        ("GET", "/leave/balances"),
        ("GET", "/leave/applications"),
        ("GET", "/leave/types"),
        ("GET", "/leave/policies"),
        ("GET", "/leave/holidays"),
        ("GET", "/leave/comp-off"),
        ("GET", "/leave/settings"),
        # Documents
        ("GET", "/documents"),
        ("GET", "/documents/categories"),
        ("GET", "/documents/templates"),
        # Announcements & Events
        ("GET", "/announcements"),
        ("GET", "/events"),
        ("GET", "/surveys"),
        ("GET", "/feedback"),
        # Assets
        ("GET", "/assets"),
        ("GET", "/assets/categories"),
        ("GET", "/assets/requests"),
        # Recruitment
        ("GET", "/positions"),
        ("GET", "/positions/vacancies"),
        ("GET", "/jobs"),
        ("GET", "/candidates"),
        # Helpdesk
        ("GET", "/tickets"),
        ("GET", "/helpdesk/tickets"),
        ("GET", "/helpdesk/categories"),
        # Knowledge & Wellness
        ("GET", "/knowledge-base"),
        ("GET", "/wellness"),
        ("GET", "/wellness/check-in"),
        # Forum
        ("GET", "/forum"),
        ("GET", "/forum/posts"),
        ("GET", "/forum/categories"),
        # Policy & Compliance
        ("GET", "/whistleblowing"),
        ("GET", "/policies"),
        # Admin
        ("GET", "/notifications"),
        ("GET", "/audit"),
        ("GET", "/audit/logs"),
        ("GET", "/modules"),
        ("GET", "/subscriptions"),
        ("GET", "/billing"),
        ("GET", "/settings"),
        ("GET", "/custom-fields"),
        # Onboarding
        ("GET", "/invitations"),
        ("GET", "/onboarding"),
        ("GET", "/onboarding/tasks"),
        # Dashboard & Reports
        ("GET", "/dashboard"),
        ("GET", "/dashboard/stats"),
        ("GET", "/reports"),
        ("GET", "/holidays"),
        # Profile
        ("GET", "/profile"),
        ("GET", "/me"),
        ("GET", "/auth/me"),
        # Payroll
        ("GET", "/payroll"),
        ("GET", "/payroll/salary-structures"),
        ("GET", "/payroll/payslips"),
        # Performance
        ("GET", "/performance"),
        ("GET", "/performance/goals"),
        ("GET", "/performance/reviews"),
        # Additional
        ("GET", "/teams"),
        ("GET", "/roles"),
        ("GET", "/permissions"),
        ("GET", "/integrations"),
        ("GET", "/webhooks"),
        ("GET", "/shifts"),
        ("GET", "/grades"),
        ("GET", "/branches"),
        ("GET", "/cost-centers"),
        ("GET", "/employee-types"),
        ("GET", "/approval-workflows"),
        ("GET", "/workflow"),
        ("GET", "/workflow/approvals"),
        ("GET", "/tasks"),
        ("GET", "/company"),
        ("GET", "/organization"),
        ("GET", "/org/settings"),
    ]

    live_endpoints = {}

    for method, path in endpoints:
        url = API + path
        status, hdrs, body = api_call(method, url, token=token)

        count = "?"
        if isinstance(body, dict):
            if isinstance(body.get("data"), list):
                count = len(body["data"])
            elif isinstance(body.get("data"), dict) and isinstance(body["data"].get("items"), list):
                count = len(body["data"]["items"])
            elif isinstance(body.get("data"), dict) and isinstance(body["data"].get("rows"), list):
                count = len(body["data"]["rows"])
            elif isinstance(body.get("data"), dict) and isinstance(body["data"].get("records"), list):
                count = len(body["data"]["records"])
            elif isinstance(body.get("items"), list):
                count = len(body["items"])
            elif isinstance(body.get("results"), list):
                count = len(body["results"])
        elif isinstance(body, list):
            count = len(body)

        status_mark = "OK" if status == 200 else f"{status}"
        print(f"  [{status_mark:>4}] {method} {path} -> count={count}")

        if status in (200, 201):
            live_endpoints[path] = {"method": method, "status": status, "body": body, "count": count}

    print(f"\n  Live endpoints: {len(live_endpoints)}")
    return live_endpoints


# ── Phase 2: CRUD Testing ────────────────────────────────────────────────

def test_crud(live_endpoints):
    """Test CRUD on live endpoints"""
    print("\n" + "="*80)
    print("PHASE 2: CRUD TESTING")
    print("="*80)

    token = tokens["org_admin"]
    results = {}

    # Try POST on various endpoints
    crud_tests = {
        "/departments": {"name": "API Test Dept " + str(int(time.time())), "description": "Test department"},
        "/designations": {"name": "API Test Designation " + str(int(time.time())), "description": "Test"},
        "/locations": {"name": "API Test Location " + str(int(time.time())), "address": "Test Address"},
        "/announcements": {"title": "API Test Announcement " + str(int(time.time())), "content": "Test content", "description": "test"},
        "/events": {"title": "API Test Event " + str(int(time.time())), "description": "Test", "start_date": "2026-04-01", "end_date": "2026-04-02"},
        "/tickets": {"subject": "API Test Ticket " + str(int(time.time())), "description": "Test ticket", "priority": "low"},
        "/helpdesk/tickets": {"subject": "API Test Ticket " + str(int(time.time())), "description": "Test ticket", "priority": "low"},
        "/holidays": {"name": "API Test Holiday " + str(int(time.time())), "date": "2026-12-25", "type": "public"},
        "/leave/apply": {"leave_type_id": 1, "start_date": "2026-06-01", "end_date": "2026-06-01", "reason": "API Test"},
        "/leave/types": {"name": "API Test Leave " + str(int(time.time())), "days": 5},
        "/assets": {"name": "API Test Asset " + str(int(time.time())), "category": "laptop", "serial_number": "TEST123"},
        "/policies": {"title": "API Test Policy " + str(int(time.time())), "content": "Test policy content"},
        "/forum/posts": {"title": "API Test Post " + str(int(time.time())), "content": "Test post content"},
        "/invitations": {"email": "testinvite_api@example.com", "role": "employee"},
        "/teams": {"name": "API Test Team " + str(int(time.time()))},
        "/roles": {"name": "API Test Role " + str(int(time.time()))},
        "/shifts": {"name": "API Test Shift " + str(int(time.time())), "start_time": "09:00", "end_time": "18:00"},
        "/custom-fields": {"name": "api_test_field", "type": "text", "module": "employee"},
        "/surveys": {"title": "API Test Survey " + str(int(time.time())), "description": "Test"},
        "/wellness/check-in": {"mood": "good", "notes": "API test check-in"},
        "/notifications": {"title": "API Test Notification", "message": "Test"},
    }

    for path, payload in crud_tests.items():
        url = API + path
        status, _, body = api_call("POST", url, payload, token=token)
        print(f"  [POST {status:>3}] {path}")
        results[f"POST {path}"] = {"status": status, "body": body}

        # If created, try to get the ID for update/delete testing
        created_id = None
        if status in (200, 201) and isinstance(body, dict):
            data = body.get("data", body)
            if isinstance(data, dict):
                created_id = data.get("id") or data.get("_id")

        if created_id:
            # Try PUT
            update_payload = dict(payload)
            if "name" in update_payload:
                update_payload["name"] = update_payload["name"] + " UPDATED"
            if "title" in update_payload:
                update_payload["title"] = update_payload["title"] + " UPDATED"

            put_url = f"{url}/{created_id}"
            status_put, _, body_put = api_call("PUT", put_url, update_payload, token=token)
            print(f"  [PUT  {status_put:>3}] {path}/{created_id}")
            results[f"PUT {path}/{created_id}"] = {"status": status_put}

            # Try DELETE
            status_del, _, body_del = api_call("DELETE", put_url, token=token)
            print(f"  [DEL  {status_del:>3}] {path}/{created_id}")
            results[f"DELETE {path}/{created_id}"] = {"status": status_del}

    # Test DELETE on endpoints that shouldn't allow it without specific ID
    for path in live_endpoints:
        url = API + path
        status, _, body = api_call("DELETE", url, token=token)
        if status in (200, 204):
            bug_title = f"[API] DELETE {path} without ID returns success ({status})"
            bug_body = f"""## Bug Report

**Endpoint:** `DELETE {API}{path}`
**Status:** {status}
**Expected:** DELETE without specific resource ID should return 400 or 405
**Actual:** Returns {status} success

**Impact:** Potential mass deletion of data if DELETE on collection endpoint is allowed.

**Response:**
```json
{json.dumps(body, indent=2)[:500] if isinstance(body, dict) else str(body)[:500]}
```
"""
            file_bug(bug_title, bug_body, ["bug", "API", "security"])

    return results


# ── Phase 3: Employee vs Admin RBAC ─────────────────────────────────────

def test_rbac(live_endpoints):
    """Compare employee vs admin access on each endpoint"""
    print("\n" + "="*80)
    print("PHASE 3: EMPLOYEE vs ADMIN RBAC COMPARISON")
    print("="*80)

    admin_token = tokens["org_admin"]
    emp_token = tokens.get("employee")

    if not emp_token:
        print("  [SKIP] No employee token available")
        return {}

    # Endpoints that employees should NOT see
    admin_only_paths = [
        "/audit", "/audit/logs", "/billing", "/subscriptions",
        "/settings", "/invitations", "/roles", "/permissions",
        "/custom-fields", "/integrations", "/webhooks",
        "/approval-workflows", "/workflow", "/workflow/approvals",
        "/org/settings", "/reports",
    ]

    results = {}

    for path in live_endpoints:
        url = API + path

        # Admin call
        status_admin, _, body_admin = api_call("GET", url, token=admin_token)
        # Employee call
        status_emp, _, body_emp = api_call("GET", url, token=emp_token)

        admin_count = "?"
        emp_count = "?"

        for label, body, count_ref in [("admin", body_admin, "admin_count"), ("emp", body_emp, "emp_count")]:
            c = "?"
            if isinstance(body, dict):
                data = body.get("data", body)
                if isinstance(data, list):
                    c = len(data)
                elif isinstance(data, dict):
                    for k in ["items", "rows", "records", "employees", "users"]:
                        if isinstance(data.get(k), list):
                            c = len(data[k])
                            break
            elif isinstance(body, list):
                c = len(body)
            if label == "admin":
                admin_count = c
            else:
                emp_count = c

        flag = ""
        is_bug = False

        # Check if employee can access admin-only endpoints
        if path in admin_only_paths and status_emp == 200:
            flag = " ** BUG: Employee can access admin-only endpoint!"
            is_bug = True

        # Check if employee sees more data than expected
        if (isinstance(admin_count, int) and isinstance(emp_count, int) and
            emp_count > 0 and admin_count > 0):
            # Employee seeing ALL users/employees is suspicious
            if path in ["/users", "/employees"] and emp_count == admin_count and admin_count > 5:
                flag = f" ** BUG: Employee sees all {emp_count} records (same as admin)!"
                is_bug = True

        print(f"  {path}: admin={status_admin}(n={admin_count}), emp={status_emp}(n={emp_count}){flag}")

        if is_bug:
            bug_title = f"[API] RBAC: Employee can access {path} with full data"
            bug_body = f"""## Bug Report

**Endpoint:** `GET {API}{path}`
**Category:** RBAC / Authorization
**Tested with:**
- Org Admin (ananya@technova.in): Status {status_admin}, Count: {admin_count}
- Employee (priya@technova.in): Status {status_emp}, Count: {emp_count}

**Expected:** Employee should have restricted access to `{path}` (admin-only endpoint or limited data).
**Actual:** Employee gets full access with the same data as admin.

**Impact:** Information disclosure - employees can see sensitive organizational data they shouldn't access.

**Admin Response (sample):**
```json
{json.dumps(body_admin, indent=2)[:300] if isinstance(body_admin, dict) else str(body_admin)[:300]}
```

**Employee Response (sample):**
```json
{json.dumps(body_emp, indent=2)[:300] if isinstance(body_emp, dict) else str(body_emp)[:300]}
```
"""
            file_bug(bug_title, bug_body, ["bug", "API", "security", "RBAC"])

        results[path] = {
            "admin_status": status_admin, "admin_count": admin_count,
            "emp_status": status_emp, "emp_count": emp_count,
            "is_bug": is_bug
        }

    # Also test write operations employee shouldn't be able to do
    write_tests = [
        ("POST", "/departments", {"name": "EmpTest Dept RBAC"}),
        ("POST", "/designations", {"name": "EmpTest Desig RBAC"}),
        ("POST", "/locations", {"name": "EmpTest Location RBAC"}),
        ("POST", "/announcements", {"title": "EmpTest Announcement RBAC", "content": "test"}),
        ("POST", "/holidays", {"name": "EmpTest Holiday RBAC", "date": "2026-12-31"}),
        ("POST", "/leave/types", {"name": "EmpTest Leave Type RBAC", "days": 99}),
        ("POST", "/invitations", {"email": "rbactest@example.com", "role": "admin"}),
        ("POST", "/roles", {"name": "EmpTest Role RBAC"}),
        ("POST", "/policies", {"title": "EmpTest Policy RBAC", "content": "test"}),
        ("POST", "/shifts", {"name": "EmpTest Shift RBAC", "start_time": "09:00", "end_time": "18:00"}),
        ("DELETE", "/departments/1", None),
        ("DELETE", "/users/1", None),
    ]

    print("\n  --- Employee Write Operation Tests ---")
    for method, path, payload in write_tests:
        url = API + path
        status, _, body = api_call(method, url, payload, token=emp_token)
        flag = ""
        if status in (200, 201, 204):
            flag = " ** BUG: Employee can perform admin write!"
            bug_title = f"[API] RBAC: Employee can {method} {path}"
            bug_body = f"""## Bug Report

**Endpoint:** `{method} {API}{path}`
**Category:** RBAC / Authorization
**Tested with:** Employee (priya@technova.in)

**Expected:** Employee should get 403 Forbidden for admin-only write operations.
**Actual:** Returns {status} - operation appears to succeed.

**Payload:** `{json.dumps(payload)}`

**Response:**
```json
{json.dumps(body, indent=2)[:500] if isinstance(body, dict) else str(body)[:500]}
```

**Impact:** Privilege escalation - regular employees can modify organizational data.
"""
            file_bug(bug_title, bug_body, ["bug", "API", "security", "RBAC"])

        print(f"  [{status:>3}] {method} {path}{flag}")

    return results


# ── Phase 4: Cross-Org Isolation ─────────────────────────────────────────

def test_cross_org(live_endpoints):
    """Test data isolation between organizations"""
    print("\n" + "="*80)
    print("PHASE 4: CROSS-ORG ISOLATION")
    print("="*80)

    technova_token = tokens["org_admin"]
    globaltech_token = tokens.get("other_org")

    if not globaltech_token:
        print("  [SKIP] No GlobalTech token available")
        return {}

    results = {}

    # Endpoints where we can extract IDs
    id_endpoints = ["/users", "/employees", "/departments", "/locations",
                    "/designations", "/announcements", "/holidays", "/leave/types",
                    "/assets", "/tickets", "/helpdesk/tickets", "/policies",
                    "/teams", "/shifts", "/roles"]

    for path in id_endpoints:
        if path not in live_endpoints:
            continue

        url = API + path

        # TechNova
        status_tn, _, body_tn = api_call("GET", url, token=technova_token)
        # GlobalTech
        status_gt, _, body_gt = api_call("GET", url, token=globaltech_token)

        def extract_ids(body):
            ids = set()
            data = body
            if isinstance(body, dict):
                data = body.get("data", body)
                if isinstance(data, dict):
                    for k in ["items", "rows", "records", "employees", "users"]:
                        if isinstance(data.get(k), list):
                            data = data[k]
                            break
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for k in ["id", "_id", "user_id", "employee_id"]:
                            if item.get(k):
                                ids.add(str(item[k]))
            return ids

        ids_tn = extract_ids(body_tn) if status_tn == 200 else set()
        ids_gt = extract_ids(body_gt) if status_gt == 200 else set()

        overlap = ids_tn & ids_gt
        flag = ""

        if overlap and len(overlap) > 0:
            # Some IDs (like system defaults) might legitimately overlap
            # Only flag if significant overlap
            if len(overlap) > 2 or (len(ids_tn) > 0 and len(overlap) / max(len(ids_tn), 1) > 0.3):
                flag = f" ** BUG: {len(overlap)} overlapping IDs!"
                bug_title = f"[API] Cross-Org: Data leakage on {path} - overlapping IDs between tenants"
                bug_body = f"""## Bug Report

**Endpoint:** `GET {API}{path}`
**Category:** Multi-tenancy / Data Isolation

**TechNova (ananya@technova.in):** {len(ids_tn)} records, Status {status_tn}
**GlobalTech (john@globaltech.com):** {len(ids_gt)} records, Status {status_gt}
**Overlapping IDs:** {len(overlap)} -> {list(overlap)[:10]}

**Expected:** Each organization should see only their own data with no overlapping record IDs.
**Actual:** {len(overlap)} records appear in both organizations' responses.

**Impact:** Critical data isolation failure - organizations can potentially access each other's data.
"""
                file_bug(bug_title, bug_body, ["bug", "API", "security", "multi-tenancy"])

        print(f"  {path}: TN={len(ids_tn)} ids, GT={len(ids_gt)} ids, overlap={len(overlap)}{flag}")
        results[path] = {"tn_ids": len(ids_tn), "gt_ids": len(ids_gt), "overlap": len(overlap)}

    # Cross-org access attempt: try to access TechNova resources with GlobalTech token
    print("\n  --- Cross-Org Direct Access Tests ---")

    # Get some TechNova user IDs
    status, _, body = api_call("GET", API + "/users", token=technova_token)
    tn_user_ids = []
    if status == 200 and isinstance(body, dict):
        data = body.get("data", body)
        if isinstance(data, list):
            tn_user_ids = [str(u.get("id") or u.get("_id")) for u in data[:3] if isinstance(u, dict)]
        elif isinstance(data, dict):
            for k in ["items", "rows", "records", "users", "employees"]:
                if isinstance(data.get(k), list):
                    tn_user_ids = [str(u.get("id") or u.get("_id")) for u in data[k][:3] if isinstance(u, dict)]
                    break

    for uid in tn_user_ids:
        if not uid or uid == "None":
            continue
        for path_tmpl in ["/users/{}", "/employees/{}"]:
            url = API + path_tmpl.format(uid)
            status, _, body = api_call("GET", url, token=globaltech_token)
            flag = ""
            if status == 200 and isinstance(body, dict):
                flag = " ** BUG: Cross-org user data accessible!"
                bug_title = f"[API] Cross-Org: GlobalTech can access TechNova user {uid} via {path_tmpl.format(uid)}"
                bug_body = f"""## Bug Report

**Endpoint:** `GET {url}`
**Category:** Multi-tenancy / Data Isolation
**Tested with:** GlobalTech token (john@globaltech.com) accessing TechNova user ID {uid}

**Expected:** 403 or 404 - cross-organization access should be blocked
**Actual:** Returns 200 with user data

**Response:**
```json
{json.dumps(body, indent=2)[:500] if isinstance(body, dict) else str(body)[:500]}
```

**Impact:** Critical - users from one organization can access another organization's employee data.
"""
                file_bug(bug_title, bug_body, ["bug", "API", "security", "critical", "multi-tenancy"])

            print(f"  [{status:>3}] GET {path_tmpl.format(uid)} (GT token){flag}")

    return results


# ── Phase 5: Input Validation ────────────────────────────────────────────

def test_input_validation(live_endpoints):
    """Test input validation on POST/PUT endpoints"""
    print("\n" + "="*80)
    print("PHASE 5: INPUT VALIDATION")
    print("="*80)

    token = tokens["org_admin"]
    results = {}

    post_endpoints = [
        "/departments", "/designations", "/locations", "/announcements",
        "/holidays", "/leave/types", "/leave/apply", "/events",
        "/tickets", "/helpdesk/tickets", "/assets", "/policies",
        "/forum/posts", "/invitations", "/teams", "/roles",
        "/shifts", "/surveys", "/custom-fields",
    ]

    xss_payload = '<script>alert("XSS")</script><img src=x onerror=alert(1)>'
    sql_payload = "'; DROP TABLE users; --"
    long_string = "A" * 5000

    for path in post_endpoints:
        url = API + path

        # Test 1: Empty body
        status_empty, _, body_empty = api_call("POST", url, {}, token=token)
        flag_empty = ""
        if status_empty in (200, 201):
            flag_empty = " ** BUG: Accepts empty body!"
            bug_title = f"[API] Validation: {path} accepts empty POST body"
            bug_body = f"""## Bug Report

**Endpoint:** `POST {API}{path}`
**Category:** Input Validation

**Test:** Sent empty JSON body `{{}}`
**Expected:** 400/422 validation error
**Actual:** Returns {status_empty} success

**Response:**
```json
{json.dumps(body_empty, indent=2)[:500] if isinstance(body_empty, dict) else str(body_empty)[:500]}
```

**Impact:** Can create records with no required fields, leading to data integrity issues.
"""
            file_bug(bug_title, bug_body, ["bug", "API", "validation"])

        # Test 2: Wrong types
        wrong_types = {"name": 12345, "title": True, "email": [], "date": {"not": "a date"}, "days": "not a number", "id": "string_id"}
        status_wrong, _, body_wrong = api_call("POST", url, wrong_types, token=token)
        flag_wrong = ""
        if status_wrong in (200, 201):
            flag_wrong = " ** BUG: Accepts wrong types!"
            bug_title = f"[API] Validation: {path} accepts wrong field types"
            bug_body = f"""## Bug Report

**Endpoint:** `POST {API}{path}`
**Category:** Input Validation

**Test:** Sent fields with wrong types (number for string, boolean for title, array for email, etc.)
**Payload:** `{json.dumps(wrong_types)}`
**Expected:** 400/422 validation error
**Actual:** Returns {status_wrong}

**Response:**
```json
{json.dumps(body_wrong, indent=2)[:500] if isinstance(body_wrong, dict) else str(body_wrong)[:500]}
```

**Impact:** Type coercion issues can lead to unexpected behavior and data corruption.
"""
            file_bug(bug_title, bug_body, ["bug", "API", "validation"])

        # Test 3: XSS payload
        xss_data = {"name": xss_payload, "title": xss_payload, "description": xss_payload, "content": xss_payload}
        status_xss, _, body_xss = api_call("POST", url, xss_data, token=token)
        flag_xss = ""
        if status_xss in (200, 201):
            # Check if script tag is stored as-is
            resp_str = json.dumps(body_xss) if isinstance(body_xss, dict) else str(body_xss)
            if "<script>" in resp_str or "onerror=" in resp_str:
                flag_xss = " ** BUG: XSS stored!"
                bug_title = f"[API] XSS: {path} stores script tags without sanitization"
                bug_body = f"""## Bug Report

**Endpoint:** `POST {API}{path}`
**Category:** Security / XSS

**Test:** Sent HTML/JavaScript in text fields
**Payload:** `{json.dumps(xss_data)[:200]}`
**Expected:** Input should be sanitized, HTML tags stripped or encoded
**Actual:** Script tags stored as-is in response

**Response containing unsanitized HTML:**
```json
{json.dumps(body_xss, indent=2)[:500] if isinstance(body_xss, dict) else str(body_xss)[:500]}
```

**Impact:** Stored XSS vulnerability - malicious scripts could execute when data is rendered in the frontend.
"""
                file_bug(bug_title, bug_body, ["bug", "API", "security", "XSS"])

        # Test 4: Extremely long string
        long_data = {"name": long_string, "title": long_string, "description": long_string}
        status_long, _, body_long = api_call("POST", url, long_data, token=token)
        flag_long = ""
        if status_long in (200, 201):
            flag_long = " ** BUG: Accepts 5000-char strings!"
            bug_title = f"[API] Validation: {path} accepts extremely long strings (5000 chars)"
            bug_body = f"""## Bug Report

**Endpoint:** `POST {API}{path}`
**Category:** Input Validation

**Test:** Sent 5000-character strings in text fields
**Expected:** 400/422 with max length validation error
**Actual:** Returns {status_long} - accepts the data

**Impact:** Can cause database bloat, UI rendering issues, and potential buffer overflow.
"""
            file_bug(bug_title, bug_body, ["bug", "API", "validation"])

        # Test 5: SQL injection attempt
        sql_data = {"name": sql_payload, "title": sql_payload, "email": sql_payload}
        status_sql, _, body_sql = api_call("POST", url, sql_data, token=token)
        flag_sql = ""
        if status_sql == 500:
            flag_sql = " ** BUG: SQL injection causes 500!"
            bug_title = f"[API] SQLi: {path} returns 500 on SQL injection payload"
            bug_body = f"""## Bug Report

**Endpoint:** `POST {API}{path}`
**Category:** Security / SQL Injection

**Test:** Sent SQL injection payload in text fields
**Payload:** `{json.dumps(sql_data)}`
**Expected:** 400 validation error (input should be parameterized/sanitized)
**Actual:** Returns 500 Internal Server Error

**Impact:** The 500 error suggests the SQL payload may be reaching the database query unsanitized.
"""
            file_bug(bug_title, bug_body, ["bug", "API", "security"])

        print(f"  {path}: empty={status_empty}{flag_empty}, wrongtype={status_wrong}{flag_wrong}, xss={status_xss}{flag_xss}, long={status_long}{flag_long}, sql={status_sql}{flag_sql}")

    return results


# ── Phase 6: Data Consistency ────────────────────────────────────────────

def test_data_consistency(live_endpoints):
    """Test data consistency across related endpoints"""
    print("\n" + "="*80)
    print("PHASE 6: DATA CONSISTENCY")
    print("="*80)

    token = tokens["org_admin"]

    # Test 1: User count consistency
    print("\n  --- User Count Consistency ---")
    status_users, _, body_users = api_call("GET", API + "/users", token=token)
    status_org, _, body_org = api_call("GET", API + "/organizations", token=token)
    status_org2, _, body_org2 = api_call("GET", API + "/organization", token=token)
    status_company, _, body_company = api_call("GET", API + "/company", token=token)

    user_count = None
    if status_users == 200 and isinstance(body_users, dict):
        data = body_users.get("data", body_users)
        if isinstance(data, list):
            user_count = len(data)
        elif isinstance(data, dict):
            for k in ["items", "rows", "records", "users", "employees", "total"]:
                v = data.get(k)
                if isinstance(v, list):
                    user_count = len(v)
                    break
                elif isinstance(v, int):
                    user_count = v
                    break

    # Check org for user count
    org_user_count = None
    for body in [body_org, body_org2, body_company]:
        if isinstance(body, dict):
            data = body.get("data", body)
            if isinstance(data, dict):
                org_user_count = data.get("current_user_count") or data.get("user_count") or data.get("total_users") or data.get("employee_count")
            elif isinstance(data, list) and data:
                org_user_count = data[0].get("current_user_count") or data[0].get("user_count") if isinstance(data[0], dict) else None
        if org_user_count:
            break

    print(f"  User count from /users: {user_count}")
    print(f"  User count from org: {org_user_count}")
    if user_count and org_user_count and user_count != org_user_count:
        print(f"  ** BUG: User count mismatch! /users={user_count} vs org={org_user_count}")
        file_bug(
            f"[API] Data Consistency: User count mismatch - /users ({user_count}) vs org ({org_user_count})",
            f"""## Bug Report

**Category:** Data Consistency

**Observation:**
- `GET /api/v1/users` returns {user_count} users
- Organization data shows {org_user_count} users

**Expected:** Both should return the same count.
**Impact:** Inconsistent user counts may indicate stale data or counting logic errors.
""",
            ["bug", "API", "data-consistency"]
        )

    # Test 2: Department references in users
    print("\n  --- Department Reference Integrity ---")
    status_depts, _, body_depts = api_call("GET", API + "/departments", token=token)

    dept_ids = set()
    if status_depts == 200 and isinstance(body_depts, dict):
        data = body_depts.get("data", body_depts)
        if isinstance(data, list):
            for d in data:
                if isinstance(d, dict):
                    did = d.get("id") or d.get("_id")
                    if did:
                        dept_ids.add(str(did))
        elif isinstance(data, dict):
            for k in ["items", "rows", "records"]:
                if isinstance(data.get(k), list):
                    for d in data[k]:
                        if isinstance(d, dict):
                            did = d.get("id") or d.get("_id")
                            if did:
                                dept_ids.add(str(did))
                    break

    user_dept_ids = set()
    if status_users == 200 and isinstance(body_users, dict):
        data = body_users.get("data", body_users)
        items = data
        if isinstance(data, dict):
            for k in ["items", "rows", "records", "users", "employees"]:
                if isinstance(data.get(k), list):
                    items = data[k]
                    break
        if isinstance(items, list):
            for u in items:
                if isinstance(u, dict):
                    did = u.get("department_id") or u.get("departmentId") or u.get("department")
                    if did and isinstance(did, (str, int)):
                        user_dept_ids.add(str(did))

    orphan_depts = user_dept_ids - dept_ids if dept_ids else set()
    print(f"  Known departments: {len(dept_ids)}")
    print(f"  Department IDs referenced by users: {len(user_dept_ids)}")
    if orphan_depts:
        print(f"  ** BUG: {len(orphan_depts)} orphan department references: {list(orphan_depts)[:10]}")
        file_bug(
            f"[API] Data Consistency: {len(orphan_depts)} orphan department references in user records",
            f"""## Bug Report

**Category:** Data Consistency / Referential Integrity

**Observation:**
- `/api/v1/departments` lists {len(dept_ids)} departments
- `/api/v1/users` references {len(user_dept_ids)} unique department IDs
- **{len(orphan_depts)}** department IDs in user records don't exist in departments list
- Orphan IDs: {list(orphan_depts)[:10]}

**Expected:** All department_id values in user records should reference valid department records.
**Impact:** Data integrity issue - users assigned to non-existent departments.
""",
            ["bug", "API", "data-consistency"]
        )

    # Test 3: Leave balance math
    print("\n  --- Leave Balance Math ---")
    status_lb, _, body_lb = api_call("GET", API + "/leave/balances", token=token)

    if status_lb == 200 and isinstance(body_lb, dict):
        data = body_lb.get("data", body_lb)
        items = data
        if isinstance(data, dict):
            for k in ["items", "rows", "records", "balances"]:
                if isinstance(data.get(k), list):
                    items = data[k]
                    break

        if isinstance(items, list):
            balance_bugs = []
            for bal in items[:50]:
                if not isinstance(bal, dict):
                    continue
                allocated = bal.get("allocated") or bal.get("total") or bal.get("total_days") or 0
                carry = bal.get("carry_forward") or bal.get("carried_forward") or 0
                used = bal.get("used") or bal.get("used_days") or bal.get("taken") or 0
                remaining = bal.get("balance") or bal.get("remaining") or bal.get("available") or bal.get("remaining_days")

                if remaining is not None and all(isinstance(v, (int, float)) for v in [allocated, carry, used, remaining]):
                    expected = allocated + carry - used
                    if abs(expected - remaining) > 0.01:
                        leave_type = bal.get("leave_type") or bal.get("type") or bal.get("name") or bal.get("leave_type_name") or "unknown"
                        balance_bugs.append(f"{leave_type}: {allocated}+{carry}-{used}={expected} but shows {remaining}")

            if balance_bugs:
                print(f"  ** BUG: {len(balance_bugs)} leave balance math errors!")
                for b in balance_bugs[:5]:
                    print(f"    - {b}")
                file_bug(
                    f"[API] Data Consistency: Leave balance math errors ({len(balance_bugs)} records)",
                    f"""## Bug Report

**Category:** Data Consistency / Business Logic
**Endpoint:** `GET /api/v1/leave/balances`

**Observation:** Leave balance calculation errors found:
{chr(10).join(f'- {b}' for b in balance_bugs[:10])}

**Expected:** `remaining = allocated + carry_forward - used`
**Impact:** Employees may see incorrect leave balances.
""",
                    ["bug", "API", "data-consistency"]
                )
            else:
                print("  Leave balance math: OK (or no numeric balances found)")
        else:
            print(f"  Leave balances: Could not parse items from response")
    else:
        print(f"  Leave balances: Status {status_lb}")

    # Test 4: Pagination consistency
    print("\n  --- Pagination Consistency ---")
    for path in ["/users", "/employees", "/departments", "/leave/applications", "/attendance"]:
        if path not in live_endpoints:
            continue
        url = API + path

        # Get with default pagination
        s1, _, b1 = api_call("GET", url, token=token)
        # Get with explicit pagination
        s2, _, b2 = api_call("GET", url + "?page=1&limit=10", token=token)
        s3, _, b3 = api_call("GET", url + "?page=1&per_page=10", token=token)
        # Get page 0 (should be invalid)
        s4, _, b4 = api_call("GET", url + "?page=0", token=token)
        # Get negative page
        s5, _, b5 = api_call("GET", url + "?page=-1", token=token)
        # Get extremely large page
        s6, _, b6 = api_call("GET", url + "?page=999999&limit=10", token=token)

        flags = []
        if s4 == 200:
            # Check if page=0 returns data (it shouldn't)
            pass  # Some APIs treat page=0 as page=1, which is acceptable
        if s5 == 200:
            flags.append("accepts negative page")
        if s6 == 200 and isinstance(b6, dict):
            data = b6.get("data", b6)
            if isinstance(data, list) and len(data) > 0:
                flags.append(f"page=999999 returns {len(data)} records")
            elif isinstance(data, dict):
                for k in ["items", "rows", "records"]:
                    if isinstance(data.get(k), list) and len(data[k]) > 0:
                        flags.append(f"page=999999 returns {len(data[k])} records")
                        break

        if flags:
            print(f"  {path}: {', '.join(flags)}")
        else:
            print(f"  {path}: pagination OK")

    # Test 5: Auth token after different operations
    print("\n  --- Stale/Invalid Token Tests ---")
    # Try with garbage token
    status_garbage, _, body_garbage = api_call("GET", API + "/users", token="garbage_invalid_token_12345")
    print(f"  Garbage token -> /users: status={status_garbage}")
    if status_garbage == 200:
        file_bug(
            "[API] Auth: Garbage token accepted by /users endpoint",
            f"""## Bug Report

**Category:** Authentication
**Endpoint:** `GET {API}/users`
**Test:** Sent request with token `garbage_invalid_token_12345`
**Expected:** 401 Unauthorized
**Actual:** Returns {status_garbage} with data

**Impact:** Critical authentication bypass.
""",
            ["bug", "API", "security", "critical"]
        )

    # Try with no token
    status_none, _, body_none = api_call("GET", API + "/users")
    print(f"  No token -> /users: status={status_none}")
    if status_none == 200:
        file_bug(
            "[API] Auth: /users accessible without authentication token",
            f"""## Bug Report

**Category:** Authentication
**Endpoint:** `GET {API}/users`
**Test:** Sent request with no Authorization header
**Expected:** 401 Unauthorized
**Actual:** Returns {status_none}

**Impact:** Critical - unauthenticated access to user data.
""",
            ["bug", "API", "security", "critical"]
        )

    # Test 6: HTTP Method Override
    print("\n  --- HTTP Method Override Tests ---")
    for path in ["/users", "/departments"]:
        if path not in live_endpoints:
            continue
        url = API + path
        # Try method override headers
        for override_header in ["X-HTTP-Method-Override", "X-Method-Override"]:
            headers_extra = dict(HEADERS_BASE)
            headers_extra["Authorization"] = f"Bearer {token}"
            headers_extra[override_header] = "DELETE"
            req = urllib.request.Request(url, headers=headers_extra, method="GET")
            try:
                resp = urllib.request.urlopen(req, timeout=15, context=ctx)
                status_override = resp.status
            except urllib.error.HTTPError as e:
                status_override = e.code
            except:
                status_override = 0

            # If the response is different from normal GET, it might be honoring the override
            if status_override in (204, 200):
                print(f"  {path} with {override_header}=DELETE: status={status_override}")


# ── Phase 7: Additional Security Tests ───────────────────────────────────

def test_additional_security(live_endpoints):
    """Test additional security concerns"""
    print("\n" + "="*80)
    print("PHASE 7: ADDITIONAL SECURITY TESTS")
    print("="*80)

    token = tokens["org_admin"]

    # Test 1: IDOR - Try to access sequential IDs
    print("\n  --- IDOR Sequential ID Test ---")
    for path in ["/users", "/employees", "/departments"]:
        for test_id in [1, 2, 3, 100, 999]:
            url = f"{API}{path}/{test_id}"
            status, _, body = api_call("GET", url, token=token)
            if status == 200:
                print(f"  [{status}] GET {path}/{test_id} -> accessible")

    # Test 2: Mass assignment
    print("\n  --- Mass Assignment Test ---")
    # Try to set admin/role fields during profile update
    mass_payloads = [
        {"role": "super_admin", "is_admin": True, "is_superadmin": True},
        {"organization_id": "different_org_id", "org_id": 999},
        {"salary": 999999, "ctc": 999999},
        {"permissions": ["admin", "super_admin", "delete_all"]},
    ]

    for ep in ["/profile", "/me", "/auth/me", "/users/me"]:
        for payload in mass_payloads:
            url = API + ep
            status, _, body = api_call("PUT", url, payload, token=tokens.get("employee", token))
            if status == 200 and isinstance(body, dict):
                # Check if sensitive fields were actually set
                data = body.get("data", body)
                if isinstance(data, dict):
                    if data.get("role") in ["super_admin", "admin"] or data.get("is_admin") == True:
                        print(f"  ** BUG: Mass assignment on {ep} - role/admin escalation!")
                        file_bug(
                            f"[API] Mass Assignment: {ep} allows role/permission escalation",
                            f"""## Bug Report

**Category:** Security / Mass Assignment
**Endpoint:** `PUT {API}{ep}`
**Payload:** `{json.dumps(payload)}`
**Expected:** Sensitive fields (role, is_admin, permissions) should be ignored
**Actual:** Returns 200 with potentially modified admin fields

**Response:**
```json
{json.dumps(body, indent=2)[:500]}
```

**Impact:** Privilege escalation via mass assignment.
""",
                            ["bug", "API", "security", "critical"]
                        )
            if status != 404:
                print(f"  [{status}] PUT {ep} with {list(payload.keys())}")

    # Test 3: Path traversal in file/document endpoints
    print("\n  --- Path Traversal Test ---")
    traversal_payloads = ["../../../etc/passwd", "..\\..\\..\\windows\\system32\\config\\sam", "%2e%2e%2f%2e%2e%2f"]
    for payload in traversal_payloads:
        for path in ["/documents", "/documents/download"]:
            url = f"{API}{path}/{urllib.parse.quote(payload, safe='')}"
            status, _, body = api_call("GET", url, token=token)
            if status == 200:
                print(f"  ** POSSIBLE BUG: Path traversal on {path} returned 200")

    # Test 4: Sensitive data in responses
    print("\n  --- Sensitive Data Exposure Check ---")
    sensitive_fields = ["password", "password_hash", "secret", "api_key", "private_key",
                        "credit_card", "ssn", "social_security", "bank_account", "aadhaar"]

    for path in live_endpoints:
        url = API + path
        status, _, body = api_call("GET", url, token=token)
        if status == 200 and isinstance(body, (dict, list)):
            body_str = json.dumps(body).lower()
            exposed = [f for f in sensitive_fields if f in body_str]
            if exposed:
                # Check if password_hash or actual password values are present
                if "password" in exposed or "password_hash" in exposed:
                    # Double check it's not just a field name reference
                    if '"password":' in body_str or '"password_hash":' in body_str:
                        print(f"  ** BUG: {path} exposes sensitive fields: {exposed}")
                        file_bug(
                            f"[API] Data Exposure: {path} returns sensitive fields ({', '.join(exposed)})",
                            f"""## Bug Report

**Category:** Security / Data Exposure
**Endpoint:** `GET {API}{path}`

**Sensitive fields found in response:** {', '.join(exposed)}

**Expected:** Sensitive fields like passwords and hashes should never be returned in API responses.
**Impact:** Information disclosure - sensitive data exposed through API.
""",
                            ["bug", "API", "security"]
                        )

    # Test 5: Super admin endpoints accessible by org admin
    print("\n  --- Super Admin Endpoint Access ---")
    super_admin_paths = [
        "/admin/organizations", "/admin/users", "/admin/settings",
        "/admin/revenue", "/admin/logs", "/admin/ai-config",
        "/super-admin/organizations", "/super-admin/dashboard",
        "/admin/super", "/platform/settings", "/platform/organizations",
    ]

    for path in super_admin_paths:
        url = API + path
        status, _, body = api_call("GET", url, token=token)
        if status == 200:
            print(f"  ** BUG: Org admin can access super-admin endpoint {path}")
            file_bug(
                f"[API] RBAC: Org Admin can access super-admin endpoint {path}",
                f"""## Bug Report

**Category:** RBAC / Authorization
**Endpoint:** `GET {API}{path}`
**Tested with:** Org Admin (ananya@technova.in)

**Expected:** 403 Forbidden - only super admins should access platform-level endpoints
**Actual:** Returns 200

**Impact:** Privilege escalation - org admins accessing platform-wide data.
""",
                ["bug", "API", "security", "RBAC"]
            )
        else:
            print(f"  [{status}] {path}")

    # Test 6: Verb tampering
    print("\n  --- HTTP Verb Tampering ---")
    for path in list(live_endpoints.keys())[:10]:
        url = API + path
        for method in ["PATCH", "OPTIONS", "TRACE", "CONNECT"]:
            status, hdrs, body = api_call(method, url, token=token)
            if method == "TRACE" and status == 200:
                print(f"  ** BUG: TRACE method enabled on {path}")
                file_bug(
                    f"[API] Security: TRACE method enabled on {path}",
                    f"""## Bug Report

**Category:** Security
**Endpoint:** `TRACE {API}{path}`

**Expected:** TRACE method should be disabled (returns 405)
**Actual:** Returns {status}

**Impact:** TRACE method can be used for cross-site tracing (XST) attacks.
""",
                    ["bug", "API", "security"]
                )
            if method == "OPTIONS" and status == 200:
                allow = hdrs.get("Allow", hdrs.get("allow", ""))
                if allow:
                    print(f"  OPTIONS {path}: Allow={allow}")

    # Test 7: ID enumeration - try to export/list all with large limit
    print("\n  --- Data Export / Large Limit Test ---")
    for path in ["/users", "/employees", "/leave/applications", "/attendance"]:
        url = API + path + "?limit=10000&per_page=10000&page_size=10000"
        status, _, body = api_call("GET", url, token=token)
        if status == 200 and isinstance(body, dict):
            data = body.get("data", body)
            count = None
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict):
                for k in ["items", "rows", "records"]:
                    if isinstance(data.get(k), list):
                        count = len(data[k])
                        break
            if count and count > 100:
                print(f"  {path}?limit=10000 returned {count} records - may need pagination cap")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    print("="*80)
    print("EMP CLOUD HRMS - COMPREHENSIVE API TESTER")
    print("="*80)

    # Fetch existing issues
    print("\n[1/8] Fetching existing GitHub issues...")
    fetch_existing_issues()

    # Login all users
    print("\n[2/8] Logging in all test users...")
    for role, (email, pwd) in CREDS.items():
        tokens[role] = login(email, pwd)

    if not tokens.get("org_admin"):
        print("\nFATAL: Could not login as org admin. Cannot proceed.")
        # Try alternative API base
        print("Trying alternative base URL patterns...")
        global BASE, API
        for alt_base in [
            "https://test-empcloud-api.empcloud.com",
            "https://test-empcloud.empcloud.com",
        ]:
            for alt_prefix in ["/api/v1", "/api", ""]:
                url = alt_base + alt_prefix + "/auth/login"
                status, _, body = api_call("POST", url, {"email": "ananya@technova.in", "password": "Welcome@123"})
                print(f"  Trying {url}: status={status}")
                if status == 200:
                    print(f"  Response keys: {list(body.keys()) if isinstance(body, dict) else 'not dict'}")
                    print(f"  Body: {json.dumps(body, indent=2)[:500] if isinstance(body, dict) else str(body)[:300]}")
        return

    # Phase 1: Discovery
    print("\n[3/8] Discovering endpoints...")
    live_endpoints = discover_endpoints()

    if not live_endpoints:
        print("\nNo live endpoints found! Checking API base...")
        # Try a raw request to see what the API returns
        for path in ["/", "/api", "/api/v1", "/health", "/api/health"]:
            url = BASE + path
            status, _, body = api_call("GET", url, token=tokens["org_admin"])
            print(f"  {url}: {status}")
        return

    # Phase 2: CRUD
    print("\n[4/8] Testing CRUD operations...")
    try:
        test_crud(live_endpoints)
    except Exception as e:
        print(f"  CRUD testing error: {e}")
        traceback.print_exc()

    # Phase 3: RBAC
    print("\n[5/8] Testing RBAC (Employee vs Admin)...")
    try:
        test_rbac(live_endpoints)
    except Exception as e:
        print(f"  RBAC testing error: {e}")
        traceback.print_exc()

    # Phase 4: Cross-Org
    print("\n[6/8] Testing Cross-Org Isolation...")
    try:
        test_cross_org(live_endpoints)
    except Exception as e:
        print(f"  Cross-org testing error: {e}")
        traceback.print_exc()

    # Phase 5: Input Validation
    print("\n[7/8] Testing Input Validation...")
    try:
        test_input_validation(live_endpoints)
    except Exception as e:
        print(f"  Input validation testing error: {e}")
        traceback.print_exc()

    # Phase 6: Data Consistency
    print("\n[8/8] Testing Data Consistency & Additional Security...")
    try:
        test_data_consistency(live_endpoints)
    except Exception as e:
        print(f"  Data consistency testing error: {e}")
        traceback.print_exc()

    try:
        test_additional_security(live_endpoints)
    except Exception as e:
        print(f"  Additional security testing error: {e}")
        traceback.print_exc()

    # Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"Live endpoints discovered: {len(live_endpoints)}")
    print(f"Bugs filed: {len(bugs_found)}")
    for bug in bugs_found:
        print(f"  #{bug['number']}: {bug['title']}")
    print("\nDone!")


if __name__ == "__main__":
    main()
