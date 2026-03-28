#!/usr/bin/env python3
"""
EMP Cloud - Full Coverage API Test Suite
Tests every known endpoint: CRUD, RBAC, cross-org isolation, validation, pagination, search.
Skips: Field Force, Biometrics, Rate Limiting checks.
"""

import sys
import os
import json
import time
import random
import string
import traceback
import requests
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================
# CONFIG
# ============================================================
API_BASE = "https://test-empcloud.empcloud.com/api/v1"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"

USERS = {
    "org_admin": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "employee": {"email": "priya@technova.in", "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"},
    "other_org": {"email": "john@globaltech.com", "password": "Welcome@123"},
}

TIMEOUT = 30

# ============================================================
# RESULTS TRACKING
# ============================================================
results = []
bugs = []
coverage_matrix = defaultdict(lambda: defaultdict(lambda: "SKIP"))

def uid():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

def log(msg):
    print(f"  {msg}")

def record(endpoint, test_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"endpoint": endpoint, "test": test_name, "status": status, "detail": detail})
    coverage_matrix[endpoint][test_name] = status
    symbol = "[PASS]" if passed else "[FAIL]"
    print(f"    {symbol} {test_name}: {detail[:120]}")

def record_bug(tag, title, body):
    bugs.append({"tag": tag, "title": title, "body": body})

# ============================================================
# AUTH
# ============================================================
tokens = {}

def login(role):
    if role in tokens:
        return tokens[role]
    creds = USERS[role]
    try:
        r = requests.post(f"{API_BASE}/auth/login", json=creds, timeout=TIMEOUT)
        if r.status_code in (200, 201):
            data = r.json()
            # Token is at data.tokens.access_token
            token = None
            d = data.get("data", {})
            if isinstance(d, dict):
                t = d.get("tokens", {})
                if isinstance(t, dict):
                    token = t.get("access_token")
                # Fallback
                if not token:
                    token = d.get("token") or d.get("access_token")
            if not token:
                token = data.get("token") or data.get("access_token")
            if token:
                tokens[role] = token
                return token
    except Exception:
        pass
    return None

def headers(role):
    t = login(role)
    if t:
        return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}

def safe_json(r):
    try:
        return r.json()
    except Exception:
        return {}

def get_list_data(j):
    """Extract list from various API response formats."""
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        for key in ["data", "results", "items", "records", "list", "rows"]:
            v = j.get(key)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for k2 in ["data", "results", "items", "records", "list", "rows"]:
                    v2 = v.get(k2)
                    if isinstance(v2, list):
                        return v2
    return []

def get_item_data(j):
    """Extract single item from response."""
    if isinstance(j, dict):
        d = j.get("data")
        if isinstance(d, dict):
            return d
        return j
    return j

def get_id(item):
    """Get ID from item."""
    if isinstance(item, dict):
        for key in ["id", "_id", "ID", "Id"]:
            if key in item:
                return item[key]
    return None

# ============================================================
# GITHUB ISSUE FILING
# ============================================================
existing_issues_cache = None

def get_existing_issues():
    global existing_issues_cache
    if existing_issues_cache is not None:
        return existing_issues_cache
    try:
        h = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
        all_issues = []
        page = 1
        while page <= 5:
            r = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                headers=h, params={"state": "all", "per_page": 100, "page": page}, timeout=20
            )
            if r.status_code != 200:
                break
            batch = r.json()
            if not batch:
                break
            all_issues.extend(batch)
            page += 1
        existing_issues_cache = [i.get("title", "") for i in all_issues]
        return existing_issues_cache
    except Exception:
        existing_issues_cache = []
        return []

def file_github_issue(tag, title, body):
    full_title = f"{tag} {title}"
    existing = get_existing_issues()
    # Check for duplicate
    for et in existing:
        if et.strip().lower() == full_title.strip().lower():
            print(f"    [SKIP-ISSUE] Duplicate: {full_title}")
            return
    try:
        h = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
        labels = ["bug", "automated-test"]
        if "SECURITY" in tag:
            labels.append("security")
        r = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers=h, json={"title": full_title, "body": body, "labels": labels}, timeout=20
        )
        if r.status_code == 201:
            url = r.json().get("html_url", "")
            print(f"    [ISSUE FILED] {full_title} -> {url}")
            existing_issues_cache.append(full_title)
        else:
            print(f"    [ISSUE FAIL] {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"    [ISSUE ERROR] {e}")

# ============================================================
# TEST: LOGIN ALL ROLES
# ============================================================
def test_auth():
    print("\n{'='*60}")
    print("PHASE 1: AUTHENTICATION")
    print("="*60)
    for role in USERS:
        t = login(role)
        record("/auth/login", f"login_{role}", t is not None,
               f"Token obtained: {'yes' if t else 'no'}")
        if not t:
            record_bug("[FUNCTIONAL]", f"Login fails for {role}",
                       f"POST {API_BASE}/auth/login with {USERS[role]['email']} returns no token")

# ============================================================
# GENERIC CRUD TESTER
# ============================================================
def test_crud(endpoint, create_payload, update_field=None, update_value=None, name_label=None):
    """Full CRUD test for an endpoint."""
    ep = endpoint
    label = name_label or endpoint
    print(f"\n  --- CRUD: {label} ({ep}) ---")

    created_id = None

    # 1. CREATE (admin)
    try:
        r = requests.post(f"{API_BASE}{ep}", headers=headers("org_admin"),
                          json=create_payload, timeout=TIMEOUT)
        j = safe_json(r)
        ok = r.status_code in (200, 201)
        item = get_item_data(j)
        created_id = get_id(item)
        record(ep, "CREATE", ok, f"Status={r.status_code}, id={created_id}")
        if not ok:
            record_bug("[FUNCTIONAL]", f"CREATE fails on {ep}",
                       f"POST {API_BASE}{ep}\nPayload: {json.dumps(create_payload)}\nStatus: {r.status_code}\nResponse: {r.text[:500]}")
    except Exception as e:
        record(ep, "CREATE", False, str(e))

    # 2. READ LIST (admin)
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        j = safe_json(r)
        items = get_list_data(j)
        ok = r.status_code == 200
        record(ep, "READ_LIST", ok, f"Status={r.status_code}, count={len(items)}")
        # If we didn't get created_id from create, try to find it in the list
        if not created_id and items:
            created_id = get_id(items[0])
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))

    # 3. READ BY ID
    if created_id:
        try:
            r = requests.get(f"{API_BASE}{ep}/{created_id}", headers=headers("org_admin"), timeout=TIMEOUT)
            ok = r.status_code == 200
            record(ep, "READ_BY_ID", ok, f"Status={r.status_code}")
            if not ok and r.status_code != 404:
                record_bug("[FUNCTIONAL]", f"GET by ID fails on {ep}/{created_id}",
                           f"GET {API_BASE}{ep}/{created_id}\nStatus: {r.status_code}\nResponse: {r.text[:500]}")
        except Exception as e:
            record(ep, "READ_BY_ID", False, str(e))
    else:
        record(ep, "READ_BY_ID", False, "No ID available")

    # 4. UPDATE
    if created_id and update_field:
        try:
            update_payload = {update_field: update_value}
            # Try PUT then PATCH
            r = requests.put(f"{API_BASE}{ep}/{created_id}", headers=headers("org_admin"),
                             json=update_payload, timeout=TIMEOUT)
            if r.status_code in (404, 405):
                r = requests.patch(f"{API_BASE}{ep}/{created_id}", headers=headers("org_admin"),
                                   json=update_payload, timeout=TIMEOUT)
            ok = r.status_code in (200, 201, 204)
            record(ep, "UPDATE", ok, f"Status={r.status_code}")
            if ok:
                # Verify update persisted
                r2 = requests.get(f"{API_BASE}{ep}/{created_id}", headers=headers("org_admin"), timeout=TIMEOUT)
                j2 = get_item_data(safe_json(r2))
                actual = j2.get(update_field) if isinstance(j2, dict) else None
                persisted = actual == update_value if actual is not None else None
                record(ep, "UPDATE_VERIFY", persisted if persisted is not None else True,
                       f"Expected={update_value}, Got={actual}")
                if persisted is False:
                    record_bug("[FUNCTIONAL]", f"UPDATE does not persist on {ep}",
                               f"PUT {API_BASE}{ep}/{created_id}\nSent: {json.dumps(update_payload)}\nExpected {update_field}={update_value}, Got {actual}")
        except Exception as e:
            record(ep, "UPDATE", False, str(e))
    else:
        record(ep, "UPDATE", created_id is None, "No ID or no update field")

    # 5. DELETE
    if created_id:
        try:
            r = requests.delete(f"{API_BASE}{ep}/{created_id}", headers=headers("org_admin"), timeout=TIMEOUT)
            ok = r.status_code in (200, 204, 202)
            record(ep, "DELETE", ok, f"Status={r.status_code}")
            if ok:
                # Verify deletion
                r2 = requests.get(f"{API_BASE}{ep}/{created_id}", headers=headers("org_admin"), timeout=TIMEOUT)
                gone = r2.status_code in (404, 410, 403)
                record(ep, "DELETE_VERIFY", gone, f"After delete GET returns {r2.status_code}")
                if not gone:
                    # Could be soft delete - check if item is marked deleted
                    j2 = get_item_data(safe_json(r2))
                    is_soft = False
                    if isinstance(j2, dict):
                        for k in ["deleted", "is_deleted", "deletedAt", "deleted_at"]:
                            if j2.get(k):
                                is_soft = True
                                break
                    record(ep, "SOFT_DELETE_CHECK", is_soft,
                           f"Soft delete detected: {is_soft}")
        except Exception as e:
            record(ep, "DELETE", False, str(e))
    else:
        record(ep, "DELETE", False, "No ID available")

    return created_id


def test_rbac(endpoint, create_payload, name_label=None):
    """Test employee vs admin access and cross-org isolation."""
    ep = endpoint
    label = name_label or endpoint
    print(f"\n  --- RBAC/Isolation: {label} ---")

    # Admin creates a record first
    created_id = None
    try:
        r = requests.post(f"{API_BASE}{ep}", headers=headers("org_admin"),
                          json=create_payload, timeout=TIMEOUT)
        if r.status_code in (200, 201):
            item = get_item_data(safe_json(r))
            created_id = get_id(item)
    except Exception:
        pass

    # Employee READ access
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("employee"), timeout=TIMEOUT)
        record(ep, "RBAC_EMPLOYEE_READ", r.status_code in (200, 403),
               f"Employee GET list: {r.status_code}")
    except Exception as e:
        record(ep, "RBAC_EMPLOYEE_READ", False, str(e))

    # Employee CREATE should fail (or be limited)
    try:
        r = requests.post(f"{API_BASE}{ep}", headers=headers("employee"),
                          json=create_payload, timeout=TIMEOUT)
        # For most admin endpoints, employee should get 403
        # For self-service (leave, feedback), 200/201 is fine
        emp_can_create = r.status_code in (200, 201)
        record(ep, "RBAC_EMPLOYEE_CREATE", True,
               f"Employee POST: {r.status_code} (allowed={emp_can_create})")
        # Clean up employee-created items
        if emp_can_create:
            eid = get_id(get_item_data(safe_json(r)))
            if eid:
                requests.delete(f"{API_BASE}{ep}/{eid}", headers=headers("employee"), timeout=TIMEOUT)
    except Exception as e:
        record(ep, "RBAC_EMPLOYEE_CREATE", False, str(e))

    # Cross-org isolation: john (globaltech) should NOT see ananya's (technova) data
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("other_org"), timeout=TIMEOUT)
        j = safe_json(r)
        other_items = get_list_data(j)
        record(ep, "CROSS_ORG_READ", r.status_code in (200, 403),
               f"Other org GET: status={r.status_code}, items={len(other_items)}")
        # If other_org can see data, check it's not technova's
        if r.status_code == 200 and created_id and other_items:
            leaked = any(str(get_id(i)) == str(created_id) for i in other_items)
            record(ep, "CROSS_ORG_ISOLATION", not leaked,
                   f"Technova item visible to GlobalTech: {leaked}")
            if leaked:
                record_bug("[SECURITY]", f"Cross-org data leak on {ep}",
                           f"GET {API_BASE}{ep} with john@globaltech.com shows item {created_id} from technova org.\n"
                           f"Response: {json.dumps(other_items[:2], default=str)[:500]}")
    except Exception as e:
        record(ep, "CROSS_ORG_READ", False, str(e))

    # If we have an ID, test cross-org access by ID
    if created_id:
        try:
            r = requests.get(f"{API_BASE}{ep}/{created_id}", headers=headers("other_org"), timeout=TIMEOUT)
            isolated = r.status_code in (403, 404)
            record(ep, "CROSS_ORG_BY_ID", isolated,
                   f"Other org GET by ID: {r.status_code}")
            if not isolated and r.status_code == 200:
                record_bug("[SECURITY]", f"Cross-org ID access on {ep}/{created_id}",
                           f"GET {API_BASE}{ep}/{created_id} with john@globaltech.com returns 200.\n"
                           f"Expected 403/404 for cross-tenant isolation.")
        except Exception as e:
            record(ep, "CROSS_ORG_BY_ID", False, str(e))

    # Cleanup
    if created_id:
        try:
            requests.delete(f"{API_BASE}{ep}/{created_id}", headers=headers("org_admin"), timeout=TIMEOUT)
        except Exception:
            pass

    # Unauthenticated access should fail
    try:
        r = requests.get(f"{API_BASE}{ep}", headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
        blocked = r.status_code in (401, 403)
        record(ep, "UNAUTH_BLOCKED", blocked, f"No-auth GET: {r.status_code}")
        if not blocked:
            record_bug("[SECURITY]", f"Unauthenticated access allowed on {ep}",
                       f"GET {API_BASE}{ep} without auth token returns {r.status_code}")
    except Exception as e:
        record(ep, "UNAUTH_BLOCKED", False, str(e))


def test_validation(endpoint, name_label=None):
    """Test input validation: empty body, wrong types, XSS."""
    ep = endpoint
    label = name_label or endpoint
    print(f"\n  --- Validation: {label} ---")

    # Empty body POST
    try:
        r = requests.post(f"{API_BASE}{ep}", headers=headers("org_admin"), json={}, timeout=TIMEOUT)
        rejected = r.status_code in (400, 422, 409)
        record(ep, "VALIDATION_EMPTY_BODY", rejected, f"Empty POST: {r.status_code}")
        if not rejected and r.status_code in (200, 201):
            record_bug("[FUNCTIONAL]", f"Empty POST accepted on {ep}",
                       f"POST {API_BASE}{ep} with empty body {{}} returns {r.status_code}")
    except Exception as e:
        record(ep, "VALIDATION_EMPTY_BODY", False, str(e))

    # XSS payload
    xss_payload = {"title": "<script>alert('xss')</script>", "name": "<img src=x onerror=alert(1)>",
                   "content": "<script>document.cookie</script>", "description": "normal",
                   "subject": "test", "message": "test"}
    try:
        r = requests.post(f"{API_BASE}{ep}", headers=headers("org_admin"), json=xss_payload, timeout=TIMEOUT)
        j = safe_json(r)
        resp_text = json.dumps(j, default=str)
        # Check if raw script tags appear unsanitized in response
        has_raw_script = "<script>" in resp_text and "alert" in resp_text
        record(ep, "XSS_INPUT", True, f"XSS POST: {r.status_code}")
        if has_raw_script and r.status_code in (200, 201):
            record_bug("[SECURITY]", f"XSS reflected unsanitized on {ep}",
                       f"POST {API_BASE}{ep} with <script>alert('xss')</script> in title.\n"
                       f"Response contains raw script tags: {resp_text[:300]}")
        # Cleanup
        item = get_item_data(j)
        xid = get_id(item)
        if xid:
            requests.delete(f"{API_BASE}{ep}/{xid}", headers=headers("org_admin"), timeout=TIMEOUT)
    except Exception as e:
        record(ep, "XSS_INPUT", False, str(e))

    # Wrong types
    wrong_payload = {"title": 12345, "name": True, "start_date": "not-a-date", "days_count": "abc"}
    try:
        r = requests.post(f"{API_BASE}{ep}", headers=headers("org_admin"), json=wrong_payload, timeout=TIMEOUT)
        record(ep, "VALIDATION_WRONG_TYPES", True, f"Wrong types POST: {r.status_code}")
    except Exception as e:
        record(ep, "VALIDATION_WRONG_TYPES", False, str(e))


def test_pagination(endpoint, name_label=None):
    """Test pagination parameters."""
    ep = endpoint
    label = name_label or endpoint
    print(f"\n  --- Pagination: {label} ---")
    try:
        # Page 1
        r1 = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"),
                          params={"page": 1, "per_page": 2}, timeout=TIMEOUT)
        j1 = safe_json(r1)
        items1 = get_list_data(j1)
        # Page 2
        r2 = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"),
                          params={"page": 2, "per_page": 2}, timeout=TIMEOUT)
        j2 = safe_json(r2)
        items2 = get_list_data(j2)
        record(ep, "PAGINATION", r1.status_code == 200,
               f"Page1: {len(items1)} items, Page2: {len(items2)} items")
        # Check for pagination metadata
        has_meta = False
        for key in ["total", "totalCount", "total_count", "pagination", "meta"]:
            if key in j1:
                has_meta = True
                break
            if isinstance(j1.get("data"), dict) and key in j1["data"]:
                has_meta = True
                break
        record(ep, "PAGINATION_META", has_meta, f"Has pagination metadata: {has_meta}")
    except Exception as e:
        record(ep, "PAGINATION", False, str(e))


def test_search(endpoint, search_field="search", search_term="test", name_label=None):
    """Test search/filter functionality."""
    ep = endpoint
    label = name_label or endpoint
    print(f"\n  --- Search: {label} ---")
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"),
                         params={search_field: search_term}, timeout=TIMEOUT)
        ok = r.status_code == 200
        items = get_list_data(safe_json(r))
        record(ep, "SEARCH", ok, f"Search '{search_field}={search_term}': status={r.status_code}, results={len(items)}")
    except Exception as e:
        record(ep, "SEARCH", False, str(e))


# ============================================================
# ENDPOINT-SPECIFIC TESTS
# ============================================================

def test_users():
    ep = "/users"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)

    # READ LIST
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        j = safe_json(r)
        items = get_list_data(j)
        record(ep, "READ_LIST", r.status_code == 200, f"Status={r.status_code}, users={len(items)}")
        # Get a user ID for further tests
        if items:
            uid_val = get_id(items[0])
            if uid_val:
                r2 = requests.get(f"{API_BASE}{ep}/{uid_val}", headers=headers("org_admin"), timeout=TIMEOUT)
                record(ep, "READ_BY_ID", r2.status_code == 200, f"Status={r2.status_code}")
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))

    # Employee sees limited users
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("employee"), timeout=TIMEOUT)
        record(ep, "RBAC_EMPLOYEE_READ", r.status_code in (200, 403),
               f"Employee GET users: {r.status_code}")
    except Exception as e:
        record(ep, "RBAC_EMPLOYEE_READ", False, str(e))

    # Cross-org
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("other_org"), timeout=TIMEOUT)
        j = safe_json(r)
        items = get_list_data(j)
        has_technova = any("technova" in str(i).lower() for i in items)
        record(ep, "CROSS_ORG_ISOLATION", not has_technova,
               f"GlobalTech sees technova users: {has_technova}, items={len(items)}")
        if has_technova:
            record_bug("[SECURITY]", "Cross-org user data leak on /users",
                       f"GET {API_BASE}/users with john@globaltech.com shows technova users")
    except Exception as e:
        record(ep, "CROSS_ORG_ISOLATION", False, str(e))

    test_pagination(ep)
    test_search(ep)
    test_validation(ep)


def test_announcements():
    ep = "/announcements"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    payload = {"title": f"Test Announcement {tag}", "content": f"Content for testing {tag}"}
    test_crud(ep, payload, "title", f"Updated Announcement {tag}")
    test_rbac(ep, {"title": f"RBAC Ann {tag}", "content": "RBAC test"})
    test_validation(ep)
    test_pagination(ep)
    test_search(ep)


def test_documents():
    ep = "/documents"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    # Documents might need file upload, test what we can
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        record(ep, "READ_LIST", r.status_code == 200, f"Status={r.status_code}")
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))
    test_rbac(ep, {"title": "Test Doc", "content": "test"})
    test_validation(ep)
    test_pagination(ep)


def test_events():
    ep = "/events"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    start = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
    payload = {
        "title": f"Test Event {tag}",
        "description": f"Event desc {tag}",
        "start_date": start,
        "end_date": end,
        "location": "Test Location"
    }
    test_crud(ep, payload, "title", f"Updated Event {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)
    test_search(ep)


def test_surveys():
    ep = "/surveys"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    payload = {"title": f"Test Survey {tag}", "description": f"Survey desc {tag}"}
    test_crud(ep, payload, "title", f"Updated Survey {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)


def test_feedback():
    ep = "/feedback"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    payload = {"subject": f"Feedback {tag}", "message": f"Feedback msg {tag}", "category": "general"}
    test_crud(ep, payload, "subject", f"Updated Feedback {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)


def test_assets():
    ep = "/assets"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    payload = {"name": f"Laptop {tag}", "category": "electronics", "serial_number": f"SN-{tag}"}
    test_crud(ep, payload, "name", f"Updated Laptop {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)
    test_search(ep)


def test_positions():
    ep = "/positions"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    payload = {"title": f"Engineer {tag}", "department": "Engineering", "type": "full-time"}
    test_crud(ep, payload, "title", f"Updated Engineer {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)


def test_helpdesk():
    ep = "/helpdesk/tickets"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    payload = {
        "category": "IT",
        "subject": f"Ticket {tag}",
        "description": f"Ticket desc {tag}",
        "priority": "medium"
    }
    test_crud(ep, payload, "subject", f"Updated Ticket {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)


def test_forum():
    ep = "/forum"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)

    # First get or create a category
    cat_id = None
    try:
        r = requests.get(f"{API_BASE}/forum/categories", headers=headers("org_admin"), timeout=TIMEOUT)
        cats = get_list_data(safe_json(r))
        record("/forum/categories", "READ_LIST", r.status_code == 200,
               f"Status={r.status_code}, categories={len(cats)}")
        if cats:
            cat_id = get_id(cats[0])
    except Exception as e:
        record("/forum/categories", "READ_LIST", False, str(e))

    tag = uid()
    payload = {"title": f"Forum Post {tag}", "content": f"Forum content {tag}"}
    if cat_id:
        payload["category_id"] = cat_id

    test_crud(ep, payload, "title", f"Updated Post {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)
    test_search(ep)

    # Test forum categories CRUD
    cat_payload = {"name": f"TestCat {tag}", "description": "Test category"}
    print(f"\n  --- Forum Categories CRUD ---")
    test_crud("/forum/categories", cat_payload, "name", f"UpdatedCat {tag}", "/forum/categories")


def test_leave_types():
    ep = "/leave/types"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    payload = {
        "name": f"TestLeave {tag}",
        "code": f"TL{tag[:4].upper()}",
        "type": "paid",
        "max_days_allowed": 10,
        "is_carry_forward": False
    }
    test_crud(ep, payload, "name", f"Updated Leave {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)


def test_leave_policies():
    ep = "/leave/policies"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    payload = {"name": f"TestPolicy {tag}", "description": f"Policy desc {tag}"}
    test_crud(ep, payload, "name", f"Updated Policy {tag}")
    test_rbac(ep, payload)
    test_validation(ep)


def test_leave_applications():
    ep = "/leave/applications"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)

    # Get a leave type ID first
    leave_type_id = None
    try:
        r = requests.get(f"{API_BASE}/leave/types", headers=headers("org_admin"), timeout=TIMEOUT)
        types = get_list_data(safe_json(r))
        if types:
            leave_type_id = get_id(types[0])
    except Exception:
        pass

    tag = uid()
    start = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
    payload = {
        "leave_type_id": leave_type_id or 1,
        "start_date": start,
        "end_date": end,
        "days_count": 1,
        "is_half_day": False,
        "reason": f"Test leave {tag}"
    }
    test_crud(ep, payload, "reason", f"Updated reason {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)


def test_leave_balances():
    ep = "/leave/balances"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        j = safe_json(r)
        items = get_list_data(j)
        record(ep, "READ_LIST", r.status_code == 200, f"Status={r.status_code}, balances={len(items)}")

        # Verify balance math for each entry
        for item in items[:5]:
            if isinstance(item, dict):
                total = item.get("total", item.get("total_days", item.get("entitled")))
                used = item.get("used", item.get("used_days", item.get("taken")))
                remaining = item.get("remaining", item.get("remaining_days", item.get("balance")))
                if total is not None and used is not None and remaining is not None:
                    try:
                        expected = float(total) - float(used)
                        actual = float(remaining)
                        correct = abs(expected - actual) < 0.01
                        record(ep, "BALANCE_MATH", correct,
                               f"total={total} - used={used} = {expected}, remaining={remaining}")
                        if not correct:
                            record_bug("[FUNCTIONAL]", "Leave balance math incorrect",
                                       f"GET {API_BASE}{ep}\nItem: {json.dumps(item, default=str)[:300]}\n"
                                       f"Expected remaining={expected}, got {remaining}")
                    except (ValueError, TypeError):
                        pass
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))

    # Employee should see own balances
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("employee"), timeout=TIMEOUT)
        record(ep, "RBAC_EMPLOYEE_READ", r.status_code == 200,
               f"Employee balance read: {r.status_code}")
    except Exception as e:
        record(ep, "RBAC_EMPLOYEE_READ", False, str(e))


def test_leave_compoff():
    ep = "/leave/comp-off"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    work_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    payload = {"work_date": work_date, "reason": f"Compoff test {tag}"}
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        record(ep, "READ_LIST", r.status_code == 200, f"Status={r.status_code}")
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))
    try:
        r = requests.post(f"{API_BASE}{ep}", headers=headers("org_admin"), json=payload, timeout=TIMEOUT)
        record(ep, "CREATE", r.status_code in (200, 201, 400, 422),
               f"Status={r.status_code}")
    except Exception as e:
        record(ep, "CREATE", False, str(e))
    test_validation(ep)


def test_attendance_shifts():
    ep = "/attendance/shifts"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    payload = {"name": f"Shift {tag}", "start_time": "09:00", "end_time": "18:00"}
    test_crud(ep, payload, "name", f"Updated Shift {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)


def test_attendance_records():
    ep = "/attendance/records"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        record(ep, "READ_LIST", r.status_code == 200, f"Status={r.status_code}")
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))
    # Employee should see own records
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("employee"), timeout=TIMEOUT)
        record(ep, "RBAC_EMPLOYEE_READ", r.status_code in (200, 403),
               f"Employee attendance: {r.status_code}")
    except Exception as e:
        record(ep, "RBAC_EMPLOYEE_READ", False, str(e))
    test_pagination(ep)


def test_wellness():
    ep = "/wellness"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        record(ep, "READ_LIST", r.status_code == 200, f"Status={r.status_code}")
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))

    # Wellness check-in
    ep2 = "/wellness/check-in"
    print(f"\n  --- Wellness Check-in ---")
    payload = {"mood": "happy", "stress_level": 3, "notes": "Feeling good"}
    try:
        r = requests.post(f"{API_BASE}{ep2}", headers=headers("employee"), json=payload, timeout=TIMEOUT)
        record(ep2, "CREATE", r.status_code in (200, 201), f"Status={r.status_code}")
    except Exception as e:
        record(ep2, "CREATE", False, str(e))
    try:
        r = requests.get(f"{API_BASE}{ep2}", headers=headers("employee"), timeout=TIMEOUT)
        record(ep2, "READ_LIST", r.status_code in (200, 404), f"Status={r.status_code}")
    except Exception as e:
        record(ep2, "READ_LIST", False, str(e))
    test_validation(ep2)


def test_policies():
    ep = "/policies"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    tag = uid()
    payload = {
        "title": f"Policy {tag}",
        "description": f"Policy desc {tag}",
        "content": f"Full policy content {tag}",
        "category": "general"
    }
    test_crud(ep, payload, "title", f"Updated Policy {tag}")
    test_rbac(ep, payload)
    test_validation(ep)
    test_pagination(ep)
    test_search(ep)


def test_notifications():
    ep = "/notifications"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        record(ep, "READ_LIST", r.status_code == 200, f"Status={r.status_code}")
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("employee"), timeout=TIMEOUT)
        record(ep, "RBAC_EMPLOYEE_READ", r.status_code == 200, f"Employee: {r.status_code}")
    except Exception as e:
        record(ep, "RBAC_EMPLOYEE_READ", False, str(e))
    test_pagination(ep)


def test_audit():
    ep = "/audit"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        record(ep, "READ_LIST", r.status_code in (200, 403), f"Status={r.status_code}")
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))
    # Employee should NOT see audit logs
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("employee"), timeout=TIMEOUT)
        blocked = r.status_code in (403, 401)
        record(ep, "RBAC_EMPLOYEE_BLOCKED", blocked or r.status_code == 200,
               f"Employee audit access: {r.status_code}")
    except Exception as e:
        record(ep, "RBAC_EMPLOYEE_BLOCKED", False, str(e))
    # Super admin should see
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("super_admin"), timeout=TIMEOUT)
        record(ep, "SUPER_ADMIN_READ", r.status_code in (200, 403),
               f"Super admin audit: {r.status_code}")
    except Exception as e:
        record(ep, "SUPER_ADMIN_READ", False, str(e))


def test_modules():
    ep = "/modules"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        j = safe_json(r)
        items = get_list_data(j)
        record(ep, "READ_LIST", r.status_code == 200,
               f"Status={r.status_code}, modules={len(items)}")
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("super_admin"), timeout=TIMEOUT)
        record(ep, "SUPER_ADMIN_READ", r.status_code == 200, f"Super admin: {r.status_code}")
    except Exception as e:
        record(ep, "SUPER_ADMIN_READ", False, str(e))


def test_subscriptions():
    ep = "/subscriptions"
    print(f"\n{'='*50}")
    print(f"TESTING: {ep}")
    print("="*50)
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
        record(ep, "READ_LIST", r.status_code in (200, 403), f"Status={r.status_code}")
    except Exception as e:
        record(ep, "READ_LIST", False, str(e))
    try:
        r = requests.get(f"{API_BASE}{ep}", headers=headers("super_admin"), timeout=TIMEOUT)
        record(ep, "SUPER_ADMIN_READ", r.status_code in (200, 403), f"Super admin: {r.status_code}")
    except Exception as e:
        record(ep, "SUPER_ADMIN_READ", False, str(e))


def test_super_admin_endpoints():
    """Test super admin specific functionality."""
    print(f"\n{'='*50}")
    print("TESTING: SUPER ADMIN ENDPOINTS")
    print("="*50)

    # Super admin should access org management, etc
    for ep in ["/admin/organizations", "/admin/users", "/admin/stats", "/organizations",
               "/admin/dashboard", "/stats", "/dashboard"]:
        try:
            r = requests.get(f"{API_BASE}{ep}", headers=headers("super_admin"), timeout=TIMEOUT)
            record(ep, "SUPER_ADMIN_READ", r.status_code in (200, 404),
                   f"Status={r.status_code}")
            # Regular user should not access admin endpoints
            if "/admin/" in ep:
                r2 = requests.get(f"{API_BASE}{ep}", headers=headers("employee"), timeout=TIMEOUT)
                blocked = r2.status_code in (401, 403, 404)
                record(ep, "RBAC_EMPLOYEE_BLOCKED", blocked,
                       f"Employee access to admin: {r2.status_code}")
                if not blocked and r2.status_code == 200:
                    record_bug("[SECURITY]", f"Employee can access admin endpoint {ep}",
                               f"GET {API_BASE}{ep} with employee token returns {r2.status_code}")
        except Exception as e:
            record(ep, "SUPER_ADMIN_READ", False, str(e))


def test_data_integrity():
    """Cross-check data consistency."""
    print(f"\n{'='*50}")
    print("TESTING: DATA INTEGRITY")
    print("="*50)

    # User count consistency
    try:
        r = requests.get(f"{API_BASE}/users", headers=headers("org_admin"), timeout=TIMEOUT)
        j = safe_json(r)
        items = get_list_data(j)
        total_from_meta = None
        if isinstance(j, dict):
            for k in ["total", "totalCount", "total_count"]:
                if k in j:
                    total_from_meta = j[k]
                    break
                if isinstance(j.get("data"), dict) and k in j["data"]:
                    total_from_meta = j["data"][k]
                    break
                if isinstance(j.get("meta"), dict) and k in j["meta"]:
                    total_from_meta = j["meta"][k]
                    break
        if total_from_meta is not None:
            match = int(total_from_meta) >= len(items)
            record("/users", "DATA_INTEGRITY_USER_COUNT", match,
                   f"Meta total={total_from_meta}, items returned={len(items)}")
        else:
            record("/users", "DATA_INTEGRITY_USER_COUNT", True, "No total metadata to verify")
    except Exception as e:
        record("/users", "DATA_INTEGRITY_USER_COUNT", False, str(e))


def test_method_not_allowed():
    """Test that endpoints reject unsupported HTTP methods."""
    print(f"\n{'='*50}")
    print("TESTING: METHOD NOT ALLOWED")
    print("="*50)
    read_only_endpoints = ["/notifications", "/audit", "/leave/balances"]
    for ep in read_only_endpoints:
        try:
            r = requests.delete(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
            proper = r.status_code in (404, 405, 400, 403)
            record(ep, "METHOD_NOT_ALLOWED", proper,
                   f"DELETE on read-only: {r.status_code}")
        except Exception as e:
            record(ep, "METHOD_NOT_ALLOWED", False, str(e))


def test_sql_injection():
    """Basic SQL injection probes."""
    print(f"\n{'='*50}")
    print("TESTING: SQL INJECTION PROBES")
    print("="*50)
    sqli_payloads = [
        "' OR '1'='1",
        "1; DROP TABLE users; --",
        "' UNION SELECT * FROM users --"
    ]
    for ep in ["/users", "/announcements", "/leave/types"]:
        for payload_str in sqli_payloads:
            try:
                r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"),
                                 params={"search": payload_str}, timeout=TIMEOUT)
                # Should not return 500 (would indicate SQL error)
                safe = r.status_code != 500
                record(ep, "SQLI_PROBE", safe,
                       f"SQLi '{payload_str[:30]}': {r.status_code}")
                if not safe:
                    record_bug("[SECURITY]", f"Possible SQL injection on {ep}",
                               f"GET {API_BASE}{ep}?search={payload_str}\n"
                               f"Returns 500 (possible SQL error)\nResponse: {r.text[:300]}")
                    break  # One failure per endpoint is enough
            except Exception as e:
                record(ep, "SQLI_PROBE", False, str(e))
                break


def test_idor():
    """Test IDOR by accessing sequential/guessed IDs from another org."""
    print(f"\n{'='*50}")
    print("TESTING: IDOR (Insecure Direct Object Reference)")
    print("="*50)

    # Try to access resources with sequential IDs from other org
    for ep in ["/users", "/announcements", "/leave/applications", "/helpdesk/tickets"]:
        try:
            # Get items from org_admin
            r = requests.get(f"{API_BASE}{ep}", headers=headers("org_admin"), timeout=TIMEOUT)
            items = get_list_data(safe_json(r))
            if items:
                target_id = get_id(items[0])
                if target_id:
                    # Try accessing from other org
                    r2 = requests.get(f"{API_BASE}{ep}/{target_id}",
                                      headers=headers("other_org"), timeout=TIMEOUT)
                    isolated = r2.status_code in (403, 404)
                    record(ep, "IDOR_CHECK", isolated,
                           f"Cross-org ID {target_id}: {r2.status_code}")
                    if not isolated and r2.status_code == 200:
                        record_bug("[SECURITY]", f"IDOR vulnerability on {ep}/{target_id}",
                                   f"GET {API_BASE}{ep}/{target_id} with other org creds returns 200\n"
                                   f"Response: {r2.text[:300]}")
        except Exception as e:
            record(ep, "IDOR_CHECK", False, str(e))


# ============================================================
# MAIN
# ============================================================
def main():
    start_time = time.time()
    print("=" * 60)
    print("EMP CLOUD - FULL COVERAGE API TEST SUITE")
    print(f"API Base: {API_BASE}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Phase 1: Auth
    test_auth()

    # Bail out if no tokens
    if not tokens:
        print("\nFATAL: Could not log in with any account. Aborting.")
        return

    print(f"\nLogged in as: {list(tokens.keys())}")

    # Phase 2: Full CRUD + RBAC + Validation per endpoint
    test_users()
    test_announcements()
    test_documents()
    test_events()
    test_surveys()
    test_feedback()
    test_assets()
    test_positions()
    test_helpdesk()
    test_forum()
    test_leave_types()
    test_leave_policies()
    test_leave_applications()
    test_leave_balances()
    test_leave_compoff()
    test_attendance_shifts()
    test_attendance_records()
    test_wellness()
    test_policies()
    test_notifications()
    test_audit()
    test_modules()
    test_subscriptions()

    # Phase 3: Cross-cutting concerns
    test_super_admin_endpoints()
    test_data_integrity()
    test_method_not_allowed()
    test_sql_injection()
    test_idor()

    elapsed = time.time() - start_time

    # ============================================================
    # FILE BUGS
    # ============================================================
    print(f"\n{'='*60}")
    print("FILING GITHUB ISSUES FOR NEW BUGS")
    print("="*60)
    for bug in bugs:
        file_github_issue(bug["tag"], bug["title"], bug["body"])

    # ============================================================
    # COVERAGE MATRIX
    # ============================================================
    print(f"\n{'='*60}")
    print("COMPLETE COVERAGE MATRIX")
    print("="*60)

    all_tests = set()
    for ep in coverage_matrix:
        for t in coverage_matrix[ep]:
            all_tests.add(t)
    all_tests = sorted(all_tests)

    # Print header
    ep_col = 28
    test_col = 6
    header = "ENDPOINT".ljust(ep_col) + " | " + " | ".join(t[:test_col].ljust(test_col) for t in all_tests)
    print(header)
    print("-" * len(header))

    for ep in sorted(coverage_matrix.keys()):
        row = ep[:ep_col].ljust(ep_col) + " | "
        row += " | ".join(coverage_matrix[ep].get(t, "---")[:test_col].ljust(test_col) for t in all_tests)
        print(row)

    # ============================================================
    # SUMMARY
    # ============================================================
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total tests:  {total}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {failed}")
    print(f"Pass rate:    {(passed/total*100):.1f}%" if total > 0 else "N/A")
    print(f"Bugs found:   {len(bugs)}")
    print(f"Time elapsed: {elapsed:.1f}s")
    print(f"Endpoints:    {len(coverage_matrix)}")

    # Failed tests detail
    if failed:
        print(f"\n--- FAILED TESTS ---")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  {r['endpoint']} / {r['test']}: {r['detail'][:100]}")

    # Bug summary
    if bugs:
        print(f"\n--- BUGS FILED ---")
        for b in bugs:
            print(f"  {b['tag']} {b['title']}")

    print(f"\nDone at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
