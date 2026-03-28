import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import time
from datetime import datetime, timedelta, date

# ── Config ──────────────────────────────────────────────────────────────
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
LOGIN_EMAIL = "ananya@technova.in"
LOGIN_PASS = "Welcome@123"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
COMMENT_PREFIX = "Comment by E2E Testing Agent"

results = []  # (issue_number, title, verdict, details)

# ── Helpers ─────────────────────────────────────────────────────────────
session = requests.Session()
session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

def find_token(obj, depth=0):
    """Recursively search for a token-like string in a nested dict."""
    if depth > 5:
        return None
    if isinstance(obj, str) and len(obj) > 20:
        return obj
    if isinstance(obj, dict):
        # Check token keys first
        for k in ["token", "access_token", "accessToken", "jwt", "auth_token"]:
            if k in obj and isinstance(obj[k], str) and len(obj[k]) > 20:
                return obj[k]
        # Then recurse into nested dicts
        for k in obj:
            if isinstance(obj[k], dict):
                t = find_token(obj[k], depth + 1)
                if t:
                    return t
    return None

def login():
    print("=" * 70)
    print("LOGGING IN...")
    urls_to_try = [
        f"{API_BASE}/auth/login",
        f"{API_BASE}/auth/sign-in",
        f"{API_BASE}/login",
        API_BASE.rsplit("/api/v1", 1)[0] + "/auth/login",
        API_BASE.rsplit("/api/v1", 1)[0] + "/login",
    ]
    for url in urls_to_try:
        r = session.post(url, json={"email": LOGIN_EMAIL, "password": LOGIN_PASS}, timeout=30)
        print(f"  POST {url} -> {r.status_code}")
        if r.status_code in (200, 201):
            data = r.json()
            token = find_token(data)
            if token:
                session.headers["Authorization"] = f"Bearer {token}"
                print(f"  Logged in OK. Token: {token[:30]}...")
                return data
            else:
                print(f"  200 but no token. Keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                print(f"  Full: {json.dumps(data)[:800]}")
            # Also check response headers for token
            for hdr in ["authorization", "x-auth-token", "x-access-token"]:
                if hdr in r.headers:
                    token = r.headers[hdr].replace("Bearer ", "")
                    session.headers["Authorization"] = f"Bearer {token}"
                    print(f"  Token from header {hdr}: {token[:30]}...")
                    return data
            # Check cookies
            if "token" in session.cookies:
                token = session.cookies["token"]
                session.headers["Authorization"] = f"Bearer {token}"
                print(f"  Token from cookie: {token[:30]}...")
                return data

    print("  FATAL: Could not log in. Exiting.")
    sys.exit(1)


def api(method, path, payload=None, params=None):
    url = f"{API_BASE}{path}" if path.startswith("/") else path
    r = session.request(method, url, json=payload, params=params, timeout=30)
    try:
        body = r.json()
    except:
        body = r.text[:500]
    return r.status_code, body


def record(issue, title, verdict, details):
    results.append((issue, title, verdict, details))
    tag = "STILL OPEN" if verdict == "STILL FAILING" else "FIXED"
    print(f"\n  >>> VERDICT #{issue}: {tag} <<<\n")


def gh_comment(issue_number, body):
    """Post comment on GitHub issue."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/comments"
    r = requests.post(url, json={"body": body},
                      headers={"Authorization": f"token {GITHUB_PAT}",
                               "Accept": "application/vnd.github.v3+json"}, timeout=30)
    print(f"  GitHub comment #{issue_number}: {r.status_code}")
    return r.status_code


def gh_reopen(issue_number):
    """Reopen a GitHub issue."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}"
    r = requests.patch(url, json={"state": "open"},
                       headers={"Authorization": f"token {GITHUB_PAT}",
                                "Accept": "application/vnd.github.v3+json"}, timeout=30)
    print(f"  GitHub reopen #{issue_number}: {r.status_code}")
    return r.status_code


# ── Login ───────────────────────────────────────────────────────────────
login_data = login()


# ═══════════════════════════════════════════════════════════════════════
# HELPER: find users, assets, etc.
# ═══════════════════════════════════════════════════════════════════════
def get_users(params=None):
    """Fetch users list, trying multiple endpoints."""
    for path in ["/users", "/employees", "/user"]:
        code, body = api("GET", path, params=params)
        if code == 200:
            # extract list
            if isinstance(body, list):
                return body
            if isinstance(body, dict):
                for k in ["data", "users", "employees", "results", "items"]:
                    if k in body and isinstance(body[k], list):
                        return body[k]
                # Maybe paginated
                if "rows" in body:
                    return body["rows"]
            return body
    return []

def get_user_detail(uid):
    for path in [f"/users/{uid}", f"/employees/{uid}"]:
        code, body = api("GET", path)
        if code == 200:
            if isinstance(body, dict) and "data" in body:
                return body["data"]
            return body
    return None

def update_user(uid, payload):
    """Try PUT then PATCH on user."""
    for method in ["PUT", "PATCH"]:
        for path in [f"/users/{uid}", f"/employees/{uid}"]:
            code, body = api(method, path, payload)
            if code != 404:
                return code, body
    return 404, {}

print("\n" + "=" * 70)
print("FETCHING USERS LIST...")
users = get_users({"page": 1, "limit": 50})
if isinstance(users, dict):
    print(f"  Users response type dict, keys: {list(users.keys()) if isinstance(users, dict) else 'N/A'}")
    # try to unwrap
    for k in ["data", "users", "rows"]:
        if k in users and isinstance(users[k], list):
            users = users[k]
            break
if isinstance(users, list):
    print(f"  Found {len(users)} users")
    for u in users[:5]:
        if isinstance(u, dict):
            print(f"    id={u.get('id')}, emp_code={u.get('emp_code','?')}, name={u.get('name', u.get('first_name','?'))}, email={u.get('email','?')}")
else:
    print(f"  Unexpected users format: {str(users)[:300]}")
    users = []


# ═══════════════════════════════════════════════════════════════════════
# #505 - Duplicate emp_code accepted
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #505 Duplicate emp_code accepted ===")
print("Step 1: Find existing emp_code from users list")

existing_emp_code = None
existing_user = None
if isinstance(users, list) and len(users) > 0:
    for u in users:
        if isinstance(u, dict) and u.get("emp_code"):
            existing_emp_code = u["emp_code"]
            existing_user = u
            break

if existing_emp_code:
    print(f"  Found emp_code: '{existing_emp_code}' (user id={existing_user.get('id')})")
    print(f"Step 2: POST new user with same emp_code '{existing_emp_code}'")
    new_user_payload = {
        "first_name": "Duplicate",
        "last_name": "Test",
        "name": "Duplicate Test",
        "email": f"dup_test_{int(time.time())}@technova.in",
        "emp_code": existing_emp_code,
        "department_id": existing_user.get("department_id"),
        "designation_id": existing_user.get("designation_id"),
        "date_of_joining": "2024-01-01",
        "role": "employee",
        "password": "Test@12345",
    }
    code, body = api("POST", "/users", new_user_payload)
    print(f"  POST /users -> {code}")
    print(f"  Response: {json.dumps(body) if isinstance(body, dict) else str(body)[:500]}")
    print(f"Step 3: Evaluate")
    if code in (409, 400, 422):
        print(f"  Duplicate emp_code REJECTED with {code}")
        record(505, "Duplicate emp_code accepted", "FIXED", f"Server returned {code}, rejecting duplicate emp_code.")
    elif code in (200, 201):
        print(f"  Duplicate emp_code ACCEPTED with {code} - BUG STILL EXISTS")
        record(505, "Duplicate emp_code accepted", "STILL FAILING", f"Server returned {code}, accepted duplicate emp_code '{existing_emp_code}'.")
    else:
        print(f"  Unexpected status {code}")
        record(505, "Duplicate emp_code accepted", "INCONCLUSIVE", f"Unexpected status {code}: {str(body)[:300]}")
else:
    print("  No emp_code found in users list. Trying manual emp_code.")
    # Create two users with same code
    ts = int(time.time())
    payload1 = {"first_name": "DupA", "last_name": "Test", "email": f"dupa_{ts}@technova.in",
                "emp_code": f"DUPTEST-{ts}", "date_of_joining": "2024-01-01", "password": "Test@12345"}
    code1, body1 = api("POST", "/users", payload1)
    print(f"  POST user A -> {code1}")
    payload2 = {"first_name": "DupB", "last_name": "Test", "email": f"dupb_{ts}@technova.in",
                "emp_code": f"DUPTEST-{ts}", "date_of_joining": "2024-01-01", "password": "Test@12345"}
    code2, body2 = api("POST", "/users", payload2)
    print(f"  POST user B (same emp_code) -> {code2}")
    if code2 in (409, 400, 422):
        record(505, "Duplicate emp_code accepted", "FIXED", f"Second user rejected with {code2}.")
    elif code2 in (200, 201):
        record(505, "Duplicate emp_code accepted", "STILL FAILING", f"Both users created with same emp_code.")
    else:
        record(505, "Duplicate emp_code accepted", "INCONCLUSIVE", f"Status: {code1}, {code2}")


# ═══════════════════════════════════════════════════════════════════════
# #506 - date_of_exit before date_of_joining
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #506 date_of_exit before date_of_joining ===")

# Find a test user
test_uid = None
if isinstance(users, list):
    for u in users:
        if isinstance(u, dict) and u.get("id"):
            test_uid = u["id"]
            break

if not test_uid:
    test_uid = 599

print(f"Step 1: PUT user {test_uid} with date_of_exit=2020-01-01, date_of_joining=2022-01-01")
payload = {"date_of_exit": "2020-01-01", "date_of_joining": "2022-01-01"}
code, body = update_user(test_uid, payload)
print(f"  Response: {code}")
print(f"  Body: {json.dumps(body) if isinstance(body, dict) else str(body)[:500]}")

if code in (400, 422):
    print("  Invalid dates REJECTED")
    record(506, "date_of_exit before date_of_joining", "FIXED", f"Server rejected with {code}.")
elif code == 200:
    print("  Invalid dates ACCEPTED - BUG STILL EXISTS")
    record(506, "date_of_exit before date_of_joining", "STILL FAILING", f"Server accepted exit date before joining date.")
    # Revert
    update_user(test_uid, {"date_of_exit": None})
else:
    print(f"  Unexpected status {code}")
    record(506, "date_of_exit before date_of_joining", "INCONCLUSIVE", f"Status {code}: {str(body)[:300]}")


# ═══════════════════════════════════════════════════════════════════════
# #509 - Self-manager allowed
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #509 Self-manager allowed ===")

if test_uid:
    print(f"Step 1: PUT user {test_uid} with reporting_manager_id={test_uid}")
    code, body = update_user(test_uid, {"reporting_manager_id": test_uid})
    print(f"  Response: {code}")
    print(f"  Body: {json.dumps(body) if isinstance(body, dict) else str(body)[:500]}")

    if code in (400, 422):
        print("  Self-manager REJECTED")
        record(509, "Self-manager allowed", "FIXED", f"Server rejected with {code}.")
    elif code == 200:
        # Verify it actually saved
        user_data = get_user_detail(test_uid)
        actual_mgr = user_data.get("reporting_manager_id") if user_data else "?"
        print(f"  Verification: reporting_manager_id = {actual_mgr}")
        if str(actual_mgr) == str(test_uid):
            print("  Self-manager ACCEPTED and SAVED - BUG STILL EXISTS")
            record(509, "Self-manager allowed", "STILL FAILING", f"User {test_uid} set as own manager.")
        else:
            print("  200 returned but value not saved - ambiguous")
            record(509, "Self-manager allowed", "INCONCLUSIVE", f"200 returned but reporting_manager_id={actual_mgr}")
    else:
        record(509, "Self-manager allowed", "INCONCLUSIVE", f"Status {code}: {str(body)[:300]}")
else:
    record(509, "Self-manager allowed", "INCONCLUSIVE", "No test user found")


# ═══════════════════════════════════════════════════════════════════════
# #530 - Circular reporting chain
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #530 Circular reporting chain ===")

user_a = None
user_b = None
if isinstance(users, list) and len(users) >= 2:
    valid = [u for u in users if isinstance(u, dict) and u.get("id")]
    if len(valid) >= 2:
        user_a = valid[0]["id"]
        user_b = valid[1]["id"]

if user_a and user_b:
    print(f"Step 1: Set user {user_a} reporting_manager = {user_b}")
    code1, body1 = update_user(user_a, {"reporting_manager_id": user_b})
    print(f"  -> {code1}: {json.dumps(body1) if isinstance(body1, dict) else str(body1)[:300]}")

    print(f"Step 2: Set user {user_b} reporting_manager = {user_a} (creates circle)")
    code2, body2 = update_user(user_b, {"reporting_manager_id": user_a})
    print(f"  -> {code2}: {json.dumps(body2) if isinstance(body2, dict) else str(body2)[:300]}")

    if code2 in (400, 422):
        print("  Circular chain REJECTED")
        record(530, "Circular reporting chain", "FIXED", f"Step 2 rejected with {code2}.")
    elif code2 == 200:
        print("  Circular chain ACCEPTED - BUG STILL EXISTS")
        record(530, "Circular reporting chain", "STILL FAILING",
               f"A({user_a})->B({user_b}) and B->A both accepted, creating circular chain.")
    else:
        record(530, "Circular reporting chain", "INCONCLUSIVE", f"Status {code1}, {code2}")
else:
    record(530, "Circular reporting chain", "INCONCLUSIVE", "Need at least 2 users")


# ═══════════════════════════════════════════════════════════════════════
# #510 - Event end_date before start_date
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #510 Event end_date before start_date ===")

event_payload = {
    "title": "E2E Test Event - Invalid Dates",
    "name": "E2E Test Event - Invalid Dates",
    "description": "Testing date validation",
    "start_date": "2025-06-15",
    "end_date": "2025-06-10",  # BEFORE start
    "event_type": "holiday",
    "type": "holiday",
    "is_active": True,
}

# Try multiple event endpoints
event_created = False
for path in ["/events", "/holidays", "/company-events", "/calendar/events"]:
    code, body = api("POST", path, event_payload)
    print(f"  POST {path} -> {code}")
    if code != 404:
        print(f"  Body: {json.dumps(body) if isinstance(body, dict) else str(body)[:500]}")
        if code in (400, 422):
            record(510, "Event end_date before start_date", "FIXED", f"Rejected with {code} at {path}.")
            event_created = True
            break
        elif code in (200, 201):
            record(510, "Event end_date before start_date", "STILL FAILING",
                   f"Event created with end_date < start_date at {path}.")
            event_created = True
            break

if not event_created:
    record(510, "Event end_date before start_date", "INCONCLUSIVE", "No event endpoint responded.")


# ═══════════════════════════════════════════════════════════════════════
# #511 - Survey end_date before start_date
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #511 Survey end_date before start_date ===")

survey_payload = {
    "title": "E2E Test Survey - Invalid Dates",
    "name": "E2E Test Survey - Invalid Dates",
    "description": "Testing date validation",
    "start_date": "2025-06-15",
    "end_date": "2025-06-10",  # BEFORE start
    "is_active": True,
    "status": "active",
}

survey_tested = False
for path in ["/surveys", "/survey", "/engagement/surveys"]:
    code, body = api("POST", path, survey_payload)
    print(f"  POST {path} -> {code}")
    if code != 404:
        print(f"  Body: {json.dumps(body) if isinstance(body, dict) else str(body)[:500]}")
        if code in (400, 422):
            record(511, "Survey end_date before start_date", "FIXED", f"Rejected with {code} at {path}.")
            survey_tested = True
            break
        elif code in (200, 201):
            record(511, "Survey end_date before start_date", "STILL FAILING",
                   f"Survey created with end_date < start_date at {path}.")
            survey_tested = True
            break

if not survey_tested:
    record(511, "Survey end_date before start_date", "INCONCLUSIVE", "No survey endpoint responded.")


# ═══════════════════════════════════════════════════════════════════════
# #526 - Under-18 employee
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #526 Under-18 employee ===")

# Make DOB = 10 years ago (clearly under 18)
under18_dob = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
print(f"Step 1: Update user with date_of_birth={under18_dob} (age ~10)")

if test_uid:
    code, body = update_user(test_uid, {"date_of_birth": under18_dob, "dob": under18_dob})
    print(f"  Response: {code}")
    print(f"  Body: {json.dumps(body) if isinstance(body, dict) else str(body)[:500]}")

    if code in (400, 422):
        print("  Under-18 DOB REJECTED")
        record(526, "Under-18 employee", "FIXED", f"Rejected with {code}.")
    elif code == 200:
        print("  Under-18 DOB ACCEPTED - BUG STILL EXISTS")
        record(526, "Under-18 employee", "STILL FAILING", f"User updated with DOB {under18_dob} (age ~10).")
        # Revert
        adult_dob = (datetime.now() - timedelta(days=365*30)).strftime("%Y-%m-%d")
        update_user(test_uid, {"date_of_birth": adult_dob, "dob": adult_dob})
    else:
        record(526, "Under-18 employee", "INCONCLUSIVE", f"Status {code}")
else:
    record(526, "Under-18 employee", "INCONCLUSIVE", "No test user")


# ═══════════════════════════════════════════════════════════════════════
# #539 - Warranty before purchase date (Assets)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #539 Warranty before purchase date ===")

asset_payload = {
    "name": "E2E Test Laptop",
    "asset_name": "E2E Test Laptop",
    "asset_type": "laptop",
    "type": "laptop",
    "category": "laptop",
    "serial_number": f"SN-TEST-{int(time.time())}",
    "purchase_date": "2025-06-15",
    "warranty_expiry": "2024-01-01",  # BEFORE purchase
    "warranty_expiry_date": "2024-01-01",
    "status": "available",
}

asset_tested = False
for path in ["/assets", "/asset", "/inventory/assets"]:
    code, body = api("POST", path, asset_payload)
    print(f"  POST {path} -> {code}")
    if code != 404:
        print(f"  Body: {json.dumps(body) if isinstance(body, dict) else str(body)[:500]}")
        if code in (400, 422):
            record(539, "Warranty before purchase date", "FIXED", f"Rejected with {code}.")
            asset_tested = True
            break
        elif code in (200, 201):
            record(539, "Warranty before purchase date", "STILL FAILING",
                   f"Asset created with warranty_expiry before purchase_date.")
            asset_tested = True
            break

if not asset_tested:
    record(539, "Warranty before purchase date", "INCONCLUSIVE", "No asset endpoint responded.")


# ═══════════════════════════════════════════════════════════════════════
# #540 - Same asset assigned to multiple employees
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #540 Same asset to multiple employees ===")

# First, get existing assets
assets_list = []
for path in ["/assets", "/asset"]:
    code, body = api("GET", path, params={"page": 1, "limit": 10})
    if code == 200:
        if isinstance(body, list):
            assets_list = body
        elif isinstance(body, dict):
            for k in ["data", "assets", "rows", "items", "results"]:
                if k in body and isinstance(body[k], list):
                    assets_list = body[k]
                    break
        if assets_list:
            print(f"  Found {len(assets_list)} assets via {path}")
            break

assign_tested = False
if assets_list and isinstance(users, list) and len(users) >= 2:
    asset_id = assets_list[0].get("id") if isinstance(assets_list[0], dict) else None
    emp_a = users[0].get("id") if isinstance(users[0], dict) else None
    emp_b = users[1].get("id") if isinstance(users[1], dict) else None

    if asset_id and emp_a and emp_b:
        print(f"  Asset ID: {asset_id}, Employee A: {emp_a}, Employee B: {emp_b}")

        # Try assigning
        for assign_path_tpl in ["/assets/{}/assign", "/assets/{}/allocate", "/asset-assignments"]:
            assign_path = assign_path_tpl.format(asset_id)
            assign_payload = {"user_id": emp_a, "employee_id": emp_a, "assigned_to": emp_a, "asset_id": asset_id}

            print(f"  Step 1: Assign asset {asset_id} to employee {emp_a}")
            code1, body1 = api("POST", assign_path, assign_payload)
            print(f"    POST {assign_path} -> {code1}")
            if code1 == 404:
                continue

            print(f"    Body: {json.dumps(body1) if isinstance(body1, dict) else str(body1)[:300]}")

            print(f"  Step 2: Assign same asset {asset_id} to employee {emp_b}")
            assign_payload2 = {"user_id": emp_b, "employee_id": emp_b, "assigned_to": emp_b, "asset_id": asset_id}
            code2, body2 = api("POST", assign_path, assign_payload2)
            print(f"    POST {assign_path} -> {code2}")
            print(f"    Body: {json.dumps(body2) if isinstance(body2, dict) else str(body2)[:300]}")

            if code2 in (400, 409, 422):
                record(540, "Same asset to multiple employees", "FIXED", f"Second assign rejected with {code2}.")
            elif code2 in (200, 201):
                record(540, "Same asset to multiple employees", "STILL FAILING",
                       f"Asset {asset_id} assigned to both {emp_a} and {emp_b}.")
            else:
                record(540, "Same asset to multiple employees", "INCONCLUSIVE", f"Status {code1}, {code2}")
            assign_tested = True
            break

        # Also try PUT on asset with assigned_to
        if not assign_tested:
            print("  Trying PUT /assets/{id} with assigned_to field...")
            code1, body1 = api("PUT", f"/assets/{asset_id}", {"assigned_to": emp_a, "user_id": emp_a})
            print(f"    PUT assign to A: {code1}")
            code2, body2 = api("PUT", f"/assets/{asset_id}", {"assigned_to": emp_b, "user_id": emp_b})
            print(f"    PUT assign to B: {code2}")
            # This approach just overwrites, so check if there's validation
            if code2 in (400, 409, 422):
                record(540, "Same asset to multiple employees", "FIXED", f"Rejected with {code2}.")
            elif code2 == 200:
                record(540, "Same asset to multiple employees", "STILL FAILING",
                       f"Asset reassigned without unassigning first.")
            assign_tested = True

if not assign_tested:
    record(540, "Same asset to multiple employees", "INCONCLUSIVE", "Could not find assets or assignment endpoint.")


# ═══════════════════════════════════════════════════════════════════════
# #541 - Org user count mismatch
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #541 Org user count mismatch ===")

# Get org info from login
org_count = None
if isinstance(login_data, dict):
    # Dig for org user count
    for path_keys in [
        ["data", "organization", "current_user_count"],
        ["organization", "current_user_count"],
        ["data", "org", "current_user_count"],
        ["org", "current_user_count"],
        ["data", "organization", "user_count"],
        ["data", "user_count"],
        ["user_count"],
    ]:
        obj = login_data
        for k in path_keys:
            if isinstance(obj, dict) and k in obj:
                obj = obj[k]
            else:
                obj = None
                break
        if obj is not None and isinstance(obj, (int, float)):
            org_count = int(obj)
            print(f"  Org user count from login: {org_count} (path: {'.'.join(path_keys)})")
            break

# Also try /organization or /org endpoint
if org_count is None:
    for path in ["/organization", "/org", "/organisations/current", "/organizations/me"]:
        code, body = api("GET", path)
        if code == 200 and isinstance(body, dict):
            for k in ["current_user_count", "user_count", "total_users"]:
                if k in body:
                    org_count = body[k]
                    print(f"  Org user count from {path}: {org_count}")
                    break
                if "data" in body and isinstance(body["data"], dict) and k in body["data"]:
                    org_count = body["data"][k]
                    print(f"  Org user count from {path}.data: {org_count}")
                    break
            if org_count is not None:
                break

# Count actual active users
print("  Counting actual active users...")
actual_count = 0
page = 1
while True:
    page_users = get_users({"page": page, "limit": 100, "status": "active"})
    if not isinstance(page_users, list) or len(page_users) == 0:
        break
    actual_count += len(page_users)
    if len(page_users) < 100:
        break
    page += 1

# Also try without status filter and count manually
if actual_count == 0:
    page = 1
    while True:
        page_users = get_users({"page": page, "limit": 100})
        if not isinstance(page_users, list) or len(page_users) == 0:
            break
        for u in page_users:
            if isinstance(u, dict):
                st = u.get("status", "active")
                if st in ("active", "Active", None, ""):
                    actual_count += 1
            else:
                actual_count += 1
        if len(page_users) < 100:
            break
        page += 1

print(f"  Actual active users counted: {actual_count}")

if org_count is not None and actual_count > 0:
    if org_count == actual_count:
        print(f"  MATCH: org says {org_count}, actual count {actual_count}")
        record(541, "Org user count mismatch", "FIXED", f"Org count ({org_count}) matches actual ({actual_count}).")
    else:
        print(f"  MISMATCH: org says {org_count}, actual count {actual_count}")
        record(541, "Org user count mismatch", "STILL FAILING",
               f"Org reports {org_count} users but counted {actual_count} active users.")
else:
    record(541, "Org user count mismatch", "INCONCLUSIVE",
           f"org_count={org_count}, actual_count={actual_count}")


# ═══════════════════════════════════════════════════════════════════════
# #523 - Attendance worked_minutes mismatch
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #523 Attendance worked_minutes mismatch ===")

attendance_tested = False
for path in ["/attendance", "/attendances", "/attendance/logs", "/attendance/records"]:
    code, body = api("GET", path, params={"page": 1, "limit": 10})
    print(f"  GET {path} -> {code}")
    if code == 200:
        records_list = []
        if isinstance(body, list):
            records_list = body
        elif isinstance(body, dict):
            for k in ["data", "records", "rows", "items", "attendances"]:
                if k in body and isinstance(body[k], list):
                    records_list = body[k]
                    break

        if records_list:
            print(f"  Found {len(records_list)} attendance records")
            mismatches = 0
            checked = 0
            for rec in records_list[:10]:
                if not isinstance(rec, dict):
                    continue
                check_in = rec.get("check_in") or rec.get("checkin") or rec.get("clock_in") or rec.get("punch_in")
                check_out = rec.get("check_out") or rec.get("checkout") or rec.get("clock_out") or rec.get("punch_out")
                worked = rec.get("worked_minutes") or rec.get("total_minutes") or rec.get("working_minutes") or rec.get("duration_minutes")

                if check_in and check_out and worked is not None:
                    checked += 1
                    try:
                        # Parse times
                        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%H:%M:%S", "%H:%M"]:
                            try:
                                ci = datetime.strptime(str(check_in), fmt)
                                co = datetime.strptime(str(check_out), fmt)
                                diff_min = (co - ci).total_seconds() / 60
                                tolerance = 2  # 2 minute tolerance
                                if abs(diff_min - float(worked)) > tolerance:
                                    mismatches += 1
                                    print(f"    MISMATCH: in={check_in}, out={check_out}, "
                                          f"calc={diff_min:.0f}min, stored={worked}min")
                                else:
                                    print(f"    OK: in={check_in}, out={check_out}, "
                                          f"calc={diff_min:.0f}min, stored={worked}min")
                                break
                            except:
                                continue
                    except Exception as e:
                        print(f"    Parse error: {e}")

            if checked > 0:
                if mismatches > 0:
                    record(523, "Attendance worked_minutes mismatch", "STILL FAILING",
                           f"{mismatches}/{checked} records have worked_minutes mismatch.")
                else:
                    record(523, "Attendance worked_minutes mismatch", "FIXED",
                           f"All {checked} checked records have correct worked_minutes.")
                attendance_tested = True
                break
            else:
                print("  No records with both check_in, check_out, and worked_minutes")
                if records_list:
                    print(f"  Sample record keys: {list(records_list[0].keys()) if isinstance(records_list[0], dict) else '?'}")

if not attendance_tested:
    record(523, "Attendance worked_minutes mismatch", "INCONCLUSIVE", "No attendance records with required fields found.")


# ═══════════════════════════════════════════════════════════════════════
# #504 - Cannot apply same-day leave
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== #504 Cannot apply same-day leave ===")

today_str = datetime.now().strftime("%Y-%m-%d")
# First find leave types
leave_type_id = None
for path in ["/leave-types", "/leave/types", "/leaves/types"]:
    code, body = api("GET", path)
    print(f"  GET {path} -> {code}")
    if code == 200:
        lt_list = body if isinstance(body, list) else body.get("data", body.get("leave_types", []))
        if isinstance(lt_list, list) and len(lt_list) > 0:
            leave_type_id = lt_list[0].get("id")
            print(f"  Found leave type: id={leave_type_id}, name={lt_list[0].get('name', '?')}")
            break

leave_payload = {
    "start_date": today_str,
    "end_date": today_str,
    "from_date": today_str,
    "to_date": today_str,
    "reason": "E2E Test - same day leave",
    "leave_type_id": leave_type_id,
    "type_id": leave_type_id,
    "status": "pending",
}

leave_tested = False
for path in ["/leaves", "/leave", "/leave-applications", "/leave/apply"]:
    code, body = api("POST", path, leave_payload)
    print(f"  POST {path} -> {code}")
    if code != 404:
        print(f"  Body: {json.dumps(body) if isinstance(body, dict) else str(body)[:500]}")
        if code in (200, 201):
            print("  Same-day leave ACCEPTED - This is correct behavior (bug was that it was rejected)")
            record(504, "Cannot apply same-day leave", "FIXED",
                   f"Same-day leave accepted with {code}.")
            leave_tested = True
            break
        elif code in (400, 422):
            # Check if it's specifically rejecting same-day
            err_text = json.dumps(body).lower() if isinstance(body, dict) else str(body).lower()
            if "same" in err_text or "today" in err_text or "advance" in err_text:
                print("  Same-day leave REJECTED - BUG STILL EXISTS")
                record(504, "Cannot apply same-day leave", "STILL FAILING",
                       f"Same-day leave rejected: {str(body)[:300]}")
            else:
                print(f"  Rejected but maybe for other reasons: {err_text[:200]}")
                record(504, "Cannot apply same-day leave", "INCONCLUSIVE",
                       f"Rejected with {code}: {str(body)[:300]}")
            leave_tested = True
            break

if not leave_tested:
    record(504, "Cannot apply same-day leave", "INCONCLUSIVE", "No leave endpoint responded.")


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY & GITHUB COMMENTS
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=" * 70)
print("FINAL RESULTS SUMMARY")
print("=" * 70)

for issue_num, title, verdict, details in results:
    status = "STILL OPEN" if verdict == "STILL FAILING" else verdict
    print(f"  #{issue_num} {title}: {status}")
    print(f"    {details}")
print()

# Post GitHub comments and reopen failures
print("=" * 70)
print("POSTING GITHUB COMMENTS...")
print("=" * 70)

for issue_num, title, verdict, details in results:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    if verdict == "STILL FAILING":
        comment_body = (
            f"**{COMMENT_PREFIX}** - Deep Re-test ({timestamp})\n\n"
            f"### Result: BUG STILL REPRODUCES\n\n"
            f"**Issue:** {title}\n\n"
            f"**Details:** {details}\n\n"
            f"**API Base:** `{API_BASE}`\n"
            f"**Credentials:** Org Admin (ananya@technova.in)\n\n"
            f"Re-opening this issue as the bug is still reproducible."
        )
        gh_comment(issue_num, comment_body)
        gh_reopen(issue_num)

    elif verdict == "FIXED":
        comment_body = (
            f"**{COMMENT_PREFIX}** - Deep Re-test ({timestamp})\n\n"
            f"### Result: APPEARS FIXED\n\n"
            f"**Issue:** {title}\n\n"
            f"**Details:** {details}\n\n"
            f"**API Base:** `{API_BASE}`\n"
            f"**Credentials:** Org Admin (ananya@technova.in)\n\n"
            f"This issue appears to be resolved based on automated re-testing."
        )
        gh_comment(issue_num, comment_body)

    elif verdict == "INCONCLUSIVE":
        comment_body = (
            f"**{COMMENT_PREFIX}** - Deep Re-test ({timestamp})\n\n"
            f"### Result: INCONCLUSIVE\n\n"
            f"**Issue:** {title}\n\n"
            f"**Details:** {details}\n\n"
            f"**API Base:** `{API_BASE}`\n"
            f"**Credentials:** Org Admin (ananya@technova.in)\n\n"
            f"Could not conclusively reproduce or confirm fix. Manual verification recommended."
        )
        gh_comment(issue_num, comment_body)

    time.sleep(1)  # Avoid GitHub rate limits

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
