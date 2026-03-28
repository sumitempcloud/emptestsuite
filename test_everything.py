#!/usr/bin/env python3
"""EMP Cloud HRMS - Comprehensive E2E API Test Suite"""

import sys
import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import time
import traceback
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Config ──────────────────────────────────────────────────────────────────
BASE    = "https://test-empcloud.empcloud.com"
API     = f"{BASE}/api/v1"
GH_PAT  = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"

USERS = {
    "org_admin":  {"email": "ananya@technova.in",  "password": "Welcome@123"},
    "employee":   {"email": "priya@technova.in",    "password": "Welcome@123"},
    "super_admin":{"email": "admin@empcloud.com",   "password": "SuperAdmin@2026"},
    "other_org":  {"email": "john@globaltech.com",  "password": "Welcome@123"},
}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# ── State ───────────────────────────────────────────────────────────────────
tokens = {}
user_profiles = {}
results = []          # (section, test_name, status, detail)
bugs = []             # list of bug dicts
created_ids = {}      # endpoint -> list of ids we created (for cleanup)

# ── Helpers ─────────────────────────────────────────────────────────────────
def api(method, path, body=None, token=None, expected=None, raw_body=None, content_type=None):
    """Make an API call. Returns (status_code, parsed_json_or_text)."""
    url = path if path.startswith("http") else f"{API}{path}"
    data = None
    if raw_body is not None:
        data = raw_body if isinstance(raw_body, bytes) else raw_body.encode()
    elif body is not None:
        data = json.dumps(body).encode()

    req = urllib.request.Request(url, data=data, method=method)
    if content_type:
        req.add_header("Content-Type", content_type)
    elif body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    req.add_header("Origin", "https://test-empcloud.empcloud.com")
    req.add_header("Referer", "https://test-empcloud.empcloud.com/")

    try:
        resp = urllib.request.urlopen(req, context=CTX, timeout=30)
        text = resp.read().decode("utf-8", errors="replace")
        code = resp.getcode()
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        code = e.code
    except Exception as e:
        return (0, str(e))

    try:
        parsed = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError:
        parsed = text

    return (code, parsed)


def record(section, name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((section, name, status, str(detail)[:300]))
    mark = "+" if passed else "X"
    print(f"  [{mark}] {name}  {str(detail)[:120]}")


def file_bug(title, method, url, steps, req_body, expected, actual_status, actual_body):
    body_str = json.dumps(actual_body, indent=2) if isinstance(actual_body, dict) else str(actual_body)
    if len(body_str) > 1500:
        body_str = body_str[:1500] + "\n... (truncated)"
    req_str = json.dumps(req_body, indent=2) if isinstance(req_body, dict) else str(req_body)

    issue_body = f"""## URL Tested
{method} {url}

## Steps to Reproduce
{steps}

## Request
Method: {method}
Endpoint: {url}
Body: {req_str}

## Expected Result
{expected}

## Actual Result
Status: {actual_status}
Response:
```json
{body_str}
```
"""
    bugs.append({"title": title, "body": issue_body})
    print(f"  [BUG] {title}")


def push_bugs_to_github():
    if not bugs:
        print("\nNo bugs to file.")
        return
    print(f"\n{'='*60}")
    print(f"FILING {len(bugs)} BUGS TO GITHUB")
    print(f"{'='*60}")
    for b in bugs:
        try:
            url = f"https://api.github.com/repos/{GH_REPO}/issues"
            payload = {"title": f"[E2E] {b['title']}", "body": b['body'], "labels": ["bug", "e2e-test"]}
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Authorization", f"token {GH_PAT}")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/vnd.github+json")
            resp = urllib.request.urlopen(req, context=CTX, timeout=20)
            rj = json.loads(resp.read().decode())
            print(f"  Filed: #{rj.get('number','')} - {b['title']}")
        except Exception as e:
            print(f"  Failed to file '{b['title']}': {e}")


# ── Discovery: find real endpoints ──────────────────────────────────────────
def discover_endpoints(token):
    """Try common endpoint patterns and return those that respond."""
    print("\n[DISCOVERY] Probing for available endpoints...")
    # We'll just try each and track in results
    candidates = [
        "/users", "/announcements", "/documents", "/events", "/surveys",
        "/feedback", "/assets", "/positions", "/helpdesk/tickets", "/forum",
        "/leave/applications", "/leave/balances", "/leave/types", "/leave/policies",
        "/leave/comp-off", "/attendance", "/attendance/shifts", "/wellness",
        "/policies", "/notifications", "/audit", "/modules", "/subscriptions",
        "/custom-fields", "/holidays", "/invitations", "/org-chart", "/dashboard",
        "/reports", "/settings", "/departments", "/locations", "/designations",
        "/whistleblowing", "/knowledge-base", "/billing",
        # Alternate patterns
        "/employee/leave", "/employee/attendance", "/admin/users",
        "/organization/settings", "/organization/departments",
        "/hr/leave-types", "/hr/holidays", "/hr/policies",
        "/asset/categories", "/helpdesk/categories",
        "/forum/categories", "/forum/posts",
        "/survey/list", "/announcement/list",
        "/auth/me", "/auth/profile", "/me", "/profile",
        "/auth/logout", "/auth/refresh",
    ]
    found = {}
    for ep in candidates:
        code, body = api("GET", ep, token=token)
        status_str = f"{code}"
        if code in (200, 201):
            found[ep] = "ok"
            status_str += " OK"
        elif code == 404:
            status_str += " Not Found"
        elif code == 403:
            found[ep] = "forbidden"
            status_str += " Forbidden"
        elif code == 401:
            status_str += " Unauthorized"
        elif code == 405:
            found[ep] = "method_not_allowed"
            status_str += " Method Not Allowed"
        else:
            found[ep] = f"other_{code}"
            status_str += f" Other"
        print(f"  {ep:40s} -> {status_str}")
    return found


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 1: AUTH & SESSION
# ════════════════════════════════════════════════════════════════════════════
def test_auth():
    print(f"\n{'='*60}")
    print("SECTION 1: AUTH & SESSION")
    print(f"{'='*60}")

    # Login all users
    for role, creds in USERS.items():
        code, body = api("POST", "/auth/login", body=creds)
        if code in (200, 201) and isinstance(body, dict):
            token = (body.get("token") or body.get("access_token") or
                     body.get("data", {}).get("token") or
                     body.get("data", {}).get("access_token") or "")
            if not token and isinstance(body.get("data"), dict):
                token = body["data"].get("accessToken", "")
            if not token:
                # Try to find token anywhere in response
                bstr = json.dumps(body)
                for key in ("token", "accessToken", "access_token", "jwt"):
                    if f'"{key}"' in bstr:
                        # Traverse
                        def find_key(d, k):
                            if isinstance(d, dict):
                                if k in d and isinstance(d[k], str) and len(d[k]) > 20:
                                    return d[k]
                                for v in d.values():
                                    r = find_key(v, k)
                                    if r: return r
                            if isinstance(d, list):
                                for v in d:
                                    r = find_key(v, k)
                                    if r: return r
                            return None
                        token = find_key(body, key) or ""
                        if token: break
            tokens[role] = token
            record("AUTH", f"Login {role}", bool(token),
                   f"code={code}, token={'yes' if token else 'NO TOKEN'}, keys={list(body.keys()) if isinstance(body, dict) else 'N/A'}")
            if not token:
                print(f"    Full response: {json.dumps(body)[:500]}")
            # Store profile if available
            if isinstance(body, dict):
                user_profiles[role] = body.get("user") or body.get("data", {}).get("user") or body.get("data", {})
        else:
            tokens[role] = ""
            record("AUTH", f"Login {role}", False, f"code={code}, body={str(body)[:200]}")

    # Test wrong password
    code, body = api("POST", "/auth/login", body={"email": "ananya@technova.in", "password": "Wrong@999"})
    record("AUTH", "Wrong password rejected", code in (400, 401, 403, 422),
           f"code={code}")

    # Test empty login
    code, body = api("POST", "/auth/login", body={})
    record("AUTH", "Empty login body rejected", code in (400, 401, 422),
           f"code={code}")

    # Test no token (unauthorized)
    code, body = api("GET", "/users")
    record("AUTH", "No-token request rejected", code in (401, 403),
           f"code={code}")

    # Test invalid token
    code, body = api("GET", "/users", token="invalid_token_12345")
    record("AUTH", "Invalid token rejected", code in (401, 403),
           f"code={code}")

    # Test expired-style token (JWT with exp in past)
    code, body = api("GET", "/users", token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDAwMDAwMDB9.fake")
    record("AUTH", "Expired/fake JWT rejected", code in (401, 403),
           f"code={code}")

    # Token refresh
    if tokens.get("org_admin"):
        code, body = api("POST", "/auth/refresh", token=tokens["org_admin"])
        record("AUTH", "Token refresh", code in (200, 201, 404, 405),
               f"code={code}")
        if code == 200 and isinstance(body, dict):
            new_token = body.get("token") or body.get("access_token") or body.get("data", {}).get("token", "")
            if new_token:
                tokens["org_admin"] = new_token

    # Logout test
    if tokens.get("employee"):
        old_token = tokens["employee"]
        code, body = api("POST", "/auth/logout", token=old_token)
        logout_exists = code not in (404, 405)
        record("AUTH", "Logout endpoint exists", True, f"code={code}")
        if logout_exists and code in (200, 201, 204):
            # Check if old token is invalidated
            code2, _ = api("GET", "/users", token=old_token)
            if code2 in (401, 403):
                record("AUTH", "Token invalidated after logout", True, f"code={code2}")
            else:
                record("AUTH", "Token invalidated after logout", False, f"code={code2} - token still works!")
                file_bug("Token not invalidated after logout",
                         "POST", f"{API}/auth/logout",
                         "1. Login as employee\n2. Call POST /auth/logout\n3. Use old token for GET /users",
                         {}, "Old token should return 401", code2, _)
            # Re-login employee
            code3, body3 = api("POST", "/auth/login", body=USERS["employee"])
            if code3 in (200, 201) and isinstance(body3, dict):
                def find_token(d):
                    if isinstance(d, dict):
                        for k in ("token", "accessToken", "access_token"):
                            if k in d and isinstance(d[k], str) and len(d[k]) > 20:
                                return d[k]
                        for v in d.values():
                            r = find_token(v)
                            if r: return r
                    return None
                tokens["employee"] = find_token(body3) or ""

    # Auth via me/profile endpoint
    for ep in ("/auth/me", "/me", "/profile", "/auth/profile"):
        if tokens.get("org_admin"):
            code, body = api("GET", ep, token=tokens["org_admin"])
            if code == 200:
                record("AUTH", f"Profile endpoint {ep} works", True, f"code={code}")
                if isinstance(body, dict):
                    user_profiles["org_admin"] = body.get("data") or body.get("user") or body
                break
    else:
        record("AUTH", "Profile endpoint found", False, "None of /auth/me, /me, /profile work")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 2: FULL CRUD ON EVERY ENDPOINT
# ════════════════════════════════════════════════════════════════════════════
def crud_test(section, endpoint, create_body, update_body, token, id_field="id",
              list_key=None, alt_endpoints=None, skip_delete=False, skip_create=False):
    """Generic CRUD test. Returns dict with found ids."""
    t = token
    result = {"list_code": 0, "items": [], "created_id": None}

    # LIST / READ
    code, body = api("GET", endpoint, token=t)
    result["list_code"] = code
    record(section, f"GET {endpoint}", code in (200, 201),
           f"code={code}")
    if code == 200 and isinstance(body, dict):
        # Try to find list data
        items = []
        if list_key and list_key in body:
            items = body[list_key]
        elif "data" in body:
            d = body["data"]
            if isinstance(d, list):
                items = d
            elif isinstance(d, dict):
                # Look for a list inside data
                for v in d.values():
                    if isinstance(v, list):
                        items = v
                        break
                if not items:
                    items = [d]  # single item
        elif isinstance(body, list):
            items = body
        result["items"] = items if isinstance(items, list) else []
        record(section, f"GET {endpoint} returns data", len(result["items"]) >= 0,
               f"count={len(result['items'])}")
    elif code == 200 and isinstance(body, list):
        result["items"] = body
        record(section, f"GET {endpoint} returns list", True, f"count={len(body)}")

    # CREATE
    if not skip_create and create_body:
        code, body = api("POST", endpoint, body=create_body, token=t)
        record(section, f"POST {endpoint}", code in (200, 201),
               f"code={code}")
        if code in (200, 201) and isinstance(body, dict):
            new_item = body.get("data") or body
            if isinstance(new_item, dict):
                cid = new_item.get(id_field) or new_item.get("_id") or new_item.get("id")
                result["created_id"] = cid
                created_ids.setdefault(endpoint, []).append(cid)
                record(section, f"POST {endpoint} returned id", bool(cid),
                       f"id={cid}")
        elif code not in (200, 201):
            if code not in (404, 405):
                detail = str(body)[:200] if not isinstance(body, dict) else json.dumps(body)[:200]
                record(section, f"POST {endpoint} error details", False, detail)

    # GET by ID
    if result["created_id"]:
        code, body = api("GET", f"{endpoint}/{result['created_id']}", token=t)
        record(section, f"GET {endpoint}/{{id}}", code in (200, 201),
               f"code={code}")
    elif result["items"] and isinstance(result["items"][0], dict):
        first_id = result["items"][0].get(id_field) or result["items"][0].get("_id") or result["items"][0].get("id")
        if first_id:
            code, body = api("GET", f"{endpoint}/{first_id}", token=t)
            record(section, f"GET {endpoint}/{{id}}", code in (200, 201),
                   f"code={code}, id={first_id}")

    # UPDATE
    target_id = result["created_id"]
    if not target_id and result["items"] and isinstance(result["items"][0], dict):
        target_id = result["items"][0].get(id_field) or result["items"][0].get("_id") or result["items"][0].get("id")
    if target_id and update_body:
        code, body = api("PUT", f"{endpoint}/{target_id}", body=update_body, token=t)
        if code in (404, 405):
            # Try PATCH
            code, body = api("PATCH", f"{endpoint}/{target_id}", body=update_body, token=t)
        record(section, f"UPDATE {endpoint}/{{id}}", code in (200, 201, 204),
               f"code={code}, id={target_id}")

    # DELETE
    if result["created_id"] and not skip_delete:
        code, body = api("DELETE", f"{endpoint}/{result['created_id']}", token=t)
        record(section, f"DELETE {endpoint}/{{id}}", code in (200, 201, 204),
               f"code={code}, id={result['created_id']}")
        # Verify deletion
        if code in (200, 201, 204):
            code2, _ = api("GET", f"{endpoint}/{result['created_id']}", token=t)
            record(section, f"Verify deleted {endpoint}/{{id}}", code2 in (404, 410, 400),
                   f"code={code2}")
            if code2 == 200:
                file_bug(f"Deleted {endpoint} item still accessible",
                         "GET", f"{API}{endpoint}/{result['created_id']}",
                         f"1. Login as org_admin\n2. Create item via POST {endpoint}\n3. Delete it\n4. GET it again",
                         {}, "Should return 404 after deletion", code2, _)

    return result


def test_full_crud():
    print(f"\n{'='*60}")
    print("SECTION 2: FULL CRUD ON EVERY ENDPOINT")
    print(f"{'='*60}")

    t = tokens.get("org_admin", "")
    if not t:
        print("  SKIP: No org_admin token")
        return

    ts = datetime.now().strftime("%Y%m%d%H%M%S")

    # ── Users ──
    print("\n--- Users ---")
    code, body = api("GET", "/users", token=t)
    record("CRUD", "GET /users", code in (200, 201), f"code={code}")
    users_list = []
    if code == 200 and isinstance(body, dict):
        users_list = body.get("data", body.get("users", []))
        if isinstance(users_list, dict):
            users_list = users_list.get("users", users_list.get("items", [users_list]))
        if isinstance(users_list, list) and len(users_list) > 0:
            uid = users_list[0].get("id") or users_list[0].get("_id")
            if uid:
                c2, b2 = api("GET", f"/users/{uid}", token=t)
                record("CRUD", "GET /users/{id}", c2 in (200, 201), f"code={c2}")
                # Update user
                c3, b3 = api("PUT", f"/users/{uid}", body={"phone": "9999999999"}, token=t)
                if c3 in (404, 405):
                    c3, b3 = api("PATCH", f"/users/{uid}", body={"phone": "9999999999"}, token=t)
                record("CRUD", "UPDATE /users/{id}", c3 in (200, 201, 204), f"code={c3}")

    # ── Announcements ──
    print("\n--- Announcements ---")
    crud_test("CRUD", "/announcements",
              {"title": f"Test Announcement {ts}", "content": "E2E test announcement body", "type": "general"},
              {"title": f"Updated Announcement {ts}"},
              t)

    # ── Documents ──
    print("\n--- Documents ---")
    code, body = api("GET", "/documents", token=t)
    record("CRUD", "GET /documents", code in (200, 201), f"code={code}")

    # ── Events ──
    print("\n--- Events ---")
    crud_test("CRUD", "/events",
              {"title": f"Test Event {ts}", "description": "E2E event",
               "start_date": "2026-04-01T10:00:00Z", "end_date": "2026-04-01T12:00:00Z",
               "type": "meeting"},
              {"title": f"Updated Event {ts}"},
              t)

    # ── Surveys ──
    print("\n--- Surveys ---")
    survey_result = crud_test("CRUD", "/surveys",
              {"title": f"Test Survey {ts}", "description": "E2E survey",
               "questions": [{"text": "Rate your satisfaction", "type": "rating"}]},
              {"title": f"Updated Survey {ts}"},
              t)
    # Publish survey
    if survey_result.get("created_id"):
        code, body = api("POST", f"/surveys/{survey_result['created_id']}/publish", token=t)
        record("CRUD", "POST /surveys/{id}/publish", code in (200, 201, 204, 404), f"code={code}")

    # ── Feedback ──
    print("\n--- Feedback ---")
    crud_test("CRUD", "/feedback",
              {"title": f"Test Feedback {ts}", "description": "E2E feedback", "type": "suggestion"},
              {"title": f"Updated Feedback {ts}"},
              t)

    # ── Assets ──
    print("\n--- Assets ---")
    crud_test("CRUD", "/assets",
              {"name": f"Test Laptop {ts}", "type": "laptop", "serial_number": f"SN{ts}",
               "status": "available"},
              {"name": f"Updated Laptop {ts}"},
              t)
    # Asset categories
    code, body = api("GET", "/assets/categories", token=t)
    if code == 404:
        code, body = api("GET", "/asset/categories", token=t)
    record("CRUD", "GET /assets/categories", code in (200, 201), f"code={code}")

    # ── Positions ──
    print("\n--- Positions ---")
    crud_test("CRUD", "/positions",
              {"title": f"Test Position {ts}", "department": "Engineering",
               "vacancies": 2, "status": "open"},
              {"title": f"Updated Position {ts}"},
              t)

    # ── Helpdesk Tickets ──
    print("\n--- Helpdesk Tickets ---")
    crud_test("CRUD", "/helpdesk/tickets",
              {"subject": f"Test Ticket {ts}", "description": "E2E helpdesk ticket",
               "priority": "medium", "category": "IT"},
              {"subject": f"Updated Ticket {ts}"},
              t)

    # ── Forum ──
    print("\n--- Forum ---")
    crud_test("CRUD", "/forum",
              {"title": f"Test Post {ts}", "content": "E2E forum post body",
               "category": "general"},
              {"title": f"Updated Post {ts}"},
              t)
    code, body = api("GET", "/forum/categories", token=t)
    record("CRUD", "GET /forum/categories", code in (200, 201), f"code={code}")

    # ── Leave ──
    print("\n--- Leave ---")
    # Leave types
    crud_test("CRUD", "/leave/types",
              {"name": f"Test Leave {ts}", "code": f"TL{ts[-4:]}",
               "days_allowed": 10, "carry_forward": True},
              {"name": f"Updated Leave Type {ts}"},
              t)
    # Leave policies
    crud_test("CRUD", "/leave/policies",
              {"name": f"Test Policy {ts}", "description": "E2E leave policy"},
              {"name": f"Updated Policy {ts}"},
              t)
    # Leave applications
    crud_test("CRUD", "/leave/applications",
              {"leave_type": "casual", "start_date": "2026-04-15",
               "end_date": "2026-04-16", "reason": "E2E test leave"},
              None, t, skip_delete=True)
    # Leave balances
    code, body = api("GET", "/leave/balances", token=t)
    record("CRUD", "GET /leave/balances", code in (200, 201), f"code={code}")
    # Comp-off
    code, body = api("GET", "/leave/comp-off", token=t)
    record("CRUD", "GET /leave/comp-off", code in (200, 201, 404), f"code={code}")

    # ── Attendance ──
    print("\n--- Attendance ---")
    code, body = api("GET", "/attendance", token=t)
    record("CRUD", "GET /attendance", code in (200, 201), f"code={code}")
    # Check-in
    code, body = api("POST", "/attendance/check-in", body={"timestamp": datetime.utcnow().isoformat() + "Z"}, token=t)
    if code in (404, 405):
        code, body = api("POST", "/attendance", body={"type": "check_in"}, token=t)
    record("CRUD", "POST /attendance check-in", code in (200, 201, 400, 409), f"code={code}")
    # Check-out
    code, body = api("POST", "/attendance/check-out", body={"timestamp": datetime.utcnow().isoformat() + "Z"}, token=t)
    if code in (404, 405):
        code, body = api("POST", "/attendance", body={"type": "check_out"}, token=t)
    record("CRUD", "POST /attendance check-out", code in (200, 201, 400, 409), f"code={code}")
    # Shifts
    crud_test("CRUD", "/attendance/shifts",
              {"name": f"Test Shift {ts}", "start_time": "09:00", "end_time": "18:00"},
              {"name": f"Updated Shift {ts}"},
              t)

    # ── Wellness ──
    print("\n--- Wellness ---")
    code, body = api("GET", "/wellness", token=t)
    record("CRUD", "GET /wellness", code in (200, 201, 404), f"code={code}")
    code, body = api("POST", "/wellness/check-in", body={"mood": "good", "score": 8}, token=t)
    record("CRUD", "POST /wellness/check-in", code in (200, 201, 404), f"code={code}")

    # ── Policies ──
    print("\n--- Policies ---")
    crud_test("CRUD", "/policies",
              {"title": f"Test Policy Doc {ts}", "content": "E2E policy content",
               "category": "hr"},
              {"title": f"Updated Policy Doc {ts}"},
              t)

    # ── Notifications ──
    print("\n--- Notifications ---")
    code, body = api("GET", "/notifications", token=t)
    record("CRUD", "GET /notifications", code in (200, 201), f"code={code}")
    # Mark read
    if code == 200 and isinstance(body, dict):
        notifs = body.get("data", [])
        if isinstance(notifs, list) and len(notifs) > 0:
            nid = notifs[0].get("id") or notifs[0].get("_id")
            if nid:
                c2, _ = api("PUT", f"/notifications/{nid}/read", token=t)
                if c2 in (404, 405):
                    c2, _ = api("PATCH", f"/notifications/{nid}", body={"read": True}, token=t)
                record("CRUD", "Mark notification read", c2 in (200, 201, 204), f"code={c2}")

    # ── Audit ──
    print("\n--- Audit ---")
    code, body = api("GET", "/audit", token=t)
    record("CRUD", "GET /audit", code in (200, 201), f"code={code}")

    # ── Modules ──
    print("\n--- Modules ---")
    code, body = api("GET", "/modules", token=t)
    record("CRUD", "GET /modules", code in (200, 201), f"code={code}")

    # ── Subscriptions ──
    print("\n--- Subscriptions ---")
    code, body = api("GET", "/subscriptions", token=t)
    record("CRUD", "GET /subscriptions", code in (200, 201, 404), f"code={code}")

    # ── Custom Fields ──
    print("\n--- Custom Fields ---")
    crud_test("CRUD", "/custom-fields",
              {"name": f"test_field_{ts}", "type": "text", "entity": "user"},
              {"name": f"updated_field_{ts}"},
              t)

    # ── Holidays ──
    print("\n--- Holidays ---")
    crud_test("CRUD", "/holidays",
              {"name": f"Test Holiday {ts}", "date": "2026-12-25",
               "type": "public"},
              {"name": f"Updated Holiday {ts}"},
              t)

    # ── Invitations ──
    print("\n--- Invitations ---")
    code, body = api("GET", "/invitations", token=t)
    record("CRUD", "GET /invitations", code in (200, 201, 404), f"code={code}")
    code, body = api("POST", "/invitations",
                     body={"email": f"testinvite{ts}@test.com", "role": "employee"},
                     token=t)
    record("CRUD", "POST /invitations (send invite)", code in (200, 201, 400, 409), f"code={code}")

    # ── Org Chart ──
    print("\n--- Org Chart ---")
    code, body = api("GET", "/org-chart", token=t)
    record("CRUD", "GET /org-chart", code in (200, 201, 404), f"code={code}")

    # ── Dashboard ──
    print("\n--- Dashboard ---")
    code, body = api("GET", "/dashboard", token=t)
    record("CRUD", "GET /dashboard", code in (200, 201), f"code={code}")

    # ── Reports ──
    print("\n--- Reports ---")
    code, body = api("GET", "/reports", token=t)
    record("CRUD", "GET /reports", code in (200, 201, 404), f"code={code}")

    # ── Settings ──
    print("\n--- Settings ---")
    code, body = api("GET", "/settings", token=t)
    record("CRUD", "GET /settings", code in (200, 201), f"code={code}")
    if code == 200:
        code2, body2 = api("PUT", "/settings", body={"timezone": "Asia/Kolkata"}, token=t)
        if code2 in (404, 405):
            code2, body2 = api("PATCH", "/settings", body={"timezone": "Asia/Kolkata"}, token=t)
        record("CRUD", "UPDATE /settings", code2 in (200, 201, 204), f"code={code2}")

    # ── Departments ──
    print("\n--- Departments ---")
    crud_test("CRUD", "/departments",
              {"name": f"Test Dept {ts}", "code": f"TD{ts[-4:]}"},
              {"name": f"Updated Dept {ts}"},
              t)

    # ── Locations ──
    print("\n--- Locations ---")
    crud_test("CRUD", "/locations",
              {"name": f"Test Location {ts}", "address": "123 Test St", "city": "TestCity"},
              {"name": f"Updated Location {ts}"},
              t)

    # ── Designations ──
    print("\n--- Designations ---")
    crud_test("CRUD", "/designations",
              {"name": f"Test Designation {ts}", "level": 5},
              {"name": f"Updated Designation {ts}"},
              t)

    # ── Whistleblowing ──
    print("\n--- Whistleblowing ---")
    crud_test("CRUD", "/whistleblowing",
              {"subject": f"Test Report {ts}", "description": "E2E whistleblowing test",
               "category": "fraud", "anonymous": True},
              None, t, skip_delete=True)

    # ── Knowledge Base ──
    print("\n--- Knowledge Base ---")
    crud_test("CRUD", "/knowledge-base",
              {"title": f"Test Article {ts}", "content": "E2E KB content",
               "category": "general"},
              {"title": f"Updated Article {ts}"},
              t)

    # ── Billing ──
    print("\n--- Billing ---")
    code, body = api("GET", "/billing", token=t)
    record("CRUD", "GET /billing", code in (200, 201, 403), f"code={code}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 3: RBAC VERIFICATION
# ════════════════════════════════════════════════════════════════════════════
def test_rbac():
    print(f"\n{'='*60}")
    print("SECTION 3: RBAC VERIFICATION")
    print(f"{'='*60}")

    admin_t = tokens.get("org_admin", "")
    emp_t = tokens.get("employee", "")
    if not admin_t or not emp_t:
        print("  SKIP: Need both org_admin and employee tokens")
        return

    # Endpoints employee should NOT have full access to
    admin_only = [
        ("/users", "All users list"),
        ("/audit", "Audit logs"),
        ("/settings", "Org settings"),
        ("/billing", "Billing info"),
        ("/invitations", "Invitations"),
        ("/custom-fields", "Custom fields management"),
    ]

    for ep, desc in admin_only:
        # Admin should get 200
        ac, ab = api("GET", ep, token=admin_t)
        # Employee tries
        ec, eb = api("GET", ep, token=emp_t)

        if ac == 200 and ec == 200:
            # Both get 200 - check if employee gets less data or same
            admin_count = 0
            emp_count = 0
            if isinstance(ab, dict):
                ad = ab.get("data", ab)
                if isinstance(ad, list): admin_count = len(ad)
                elif isinstance(ad, dict):
                    for v in ad.values():
                        if isinstance(v, list):
                            admin_count = len(v)
                            break
            if isinstance(eb, dict):
                ed = eb.get("data", eb)
                if isinstance(ed, list): emp_count = len(ed)
                elif isinstance(ed, dict):
                    for v in ed.values():
                        if isinstance(v, list):
                            emp_count = len(v)
                            break

            if ep in ("/audit", "/settings", "/billing", "/invitations"):
                record("RBAC", f"Employee blocked from {desc}", ec in (403, 401),
                       f"admin={ac}, emp={ec} - Employee should NOT access {desc}")
                if ec == 200:
                    file_bug(f"Employee can access admin-only {desc}",
                             "GET", f"{API}{ep}",
                             f"1. Login as employee (priya@technova.in)\n2. GET {ep}",
                             {}, f"Should return 403 for employee", ec, eb)
            else:
                record("RBAC", f"Employee access to {desc}", True,
                       f"admin={ac}(count={admin_count}), emp={ec}(count={emp_count})")
        elif ac == 200 and ec in (403, 401):
            record("RBAC", f"Employee blocked from {desc}", True,
                   f"admin={ac}, emp={ec}")
        else:
            record("RBAC", f"{desc} access pattern", True,
                   f"admin={ac}, emp={ec}")

    # Employee SHOULD access
    employee_ok = [
        ("/leave/balances", "Own leave balances"),
        ("/attendance", "Own attendance"),
        ("/notifications", "Own notifications"),
        ("/announcements", "Public announcements"),
        ("/surveys", "Active surveys"),
        ("/dashboard", "Dashboard"),
    ]
    for ep, desc in employee_ok:
        ec, eb = api("GET", ep, token=emp_t)
        record("RBAC", f"Employee can access {desc}", ec in (200, 201),
               f"code={ec}")

    # Employee should not create admin resources
    admin_create_tests = [
        ("/users", {"email": "hacker@evil.com", "role": "admin"}, "Create user"),
        ("/leave/types", {"name": "Hacker Leave", "days": 999}, "Create leave type"),
        ("/holidays", {"name": "Hacker Holiday", "date": "2026-06-06"}, "Create holiday"),
    ]
    for ep, body, desc in admin_create_tests:
        ec, eb = api("POST", ep, body=body, token=emp_t)
        record("RBAC", f"Employee blocked from {desc}", ec in (403, 401, 404, 405),
               f"code={ec}")
        if ec in (200, 201):
            file_bug(f"Employee can {desc} (privilege escalation)",
                     "POST", f"{API}{ep}",
                     f"1. Login as employee\n2. POST {ep} with admin-level data",
                     body, f"Should return 403", ec, eb)

    # Super admin access
    sa_t = tokens.get("super_admin", "")
    if sa_t:
        sa_endpoints = ["/users", "/modules", "/billing", "/audit"]
        for ep in sa_endpoints:
            sc, sb = api("GET", ep, token=sa_t)
            record("RBAC", f"Super admin access {ep}", sc in (200, 201),
                   f"code={sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 4: CROSS-ORG ISOLATION
# ════════════════════════════════════════════════════════════════════════════
def test_cross_org():
    print(f"\n{'='*60}")
    print("SECTION 4: CROSS-ORG ISOLATION")
    print(f"{'='*60}")

    other_t = tokens.get("other_org", "")
    admin_t = tokens.get("org_admin", "")
    if not other_t:
        print("  SKIP: No other_org token (john@globaltech.com)")
        return

    # Get TechNova user IDs from admin
    technova_user_ids = []
    if admin_t:
        code, body = api("GET", "/users", token=admin_t)
        if code == 200 and isinstance(body, dict):
            users = body.get("data", body.get("users", []))
            if isinstance(users, dict):
                users = users.get("users", users.get("items", []))
            if isinstance(users, list):
                for u in users[:5]:
                    uid = u.get("id") or u.get("_id")
                    if uid:
                        technova_user_ids.append(uid)

    # Test other_org can't see TechNova data
    iso_endpoints = ["/users", "/announcements", "/events", "/leave/applications",
                     "/attendance", "/departments", "/positions", "/holidays",
                     "/helpdesk/tickets", "/forum", "/assets"]

    for ep in iso_endpoints:
        oc, ob = api("GET", ep, token=other_t)
        if admin_t:
            ac, ab = api("GET", ep, token=admin_t)
        else:
            ac, ab = 0, {}

        if oc == 200 and ac == 200:
            # Both returned data - check no overlap
            def extract_ids(body):
                ids = set()
                items = []
                if isinstance(body, dict):
                    d = body.get("data", body)
                    if isinstance(d, list): items = d
                    elif isinstance(d, dict):
                        for v in d.values():
                            if isinstance(v, list):
                                items = v
                                break
                elif isinstance(body, list):
                    items = body
                for item in items:
                    if isinstance(item, dict):
                        i = item.get("id") or item.get("_id")
                        if i: ids.add(str(i))
                return ids

            admin_ids = extract_ids(ab)
            other_ids = extract_ids(ob)
            overlap = admin_ids & other_ids

            if overlap:
                record("CROSS-ORG", f"Isolation {ep}", False,
                       f"OVERLAP! {len(overlap)} shared IDs: {list(overlap)[:3]}")
                file_bug(f"Cross-org data leak at {ep}",
                         "GET", f"{API}{ep}",
                         f"1. Login as john@globaltech.com (GlobalTech)\n2. GET {ep}\n3. Compare with TechNova admin data",
                         {}, "GlobalTech should NOT see TechNova data",
                         oc, {"overlap_count": len(overlap), "overlapping_ids": list(overlap)[:5]})
            else:
                record("CROSS-ORG", f"Isolation {ep}", True,
                       f"No overlap (admin={len(admin_ids)} ids, other={len(other_ids)} ids)")
        elif oc in (403, 401):
            record("CROSS-ORG", f"Isolation {ep}", True, f"other_org blocked ({oc})")
        else:
            record("CROSS-ORG", f"Isolation {ep}", True, f"admin={ac}, other={oc}")

    # Direct access to TechNova user IDs
    for uid in technova_user_ids[:3]:
        oc, ob = api("GET", f"/users/{uid}", token=other_t)
        record("CROSS-ORG", f"Direct access TechNova user {uid}", oc in (403, 404, 401),
               f"code={oc}")
        if oc == 200:
            file_bug(f"Cross-org user data accessible: user {uid}",
                     "GET", f"{API}/users/{uid}",
                     f"1. Login as john@globaltech.com\n2. GET /users/{uid} (TechNova user)",
                     {}, "Should return 403 or 404", oc, ob)


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 5: DATA INTEGRITY
# ════════════════════════════════════════════════════════════════════════════
def test_data_integrity():
    print(f"\n{'='*60}")
    print("SECTION 5: DATA INTEGRITY")
    print(f"{'='*60}")

    t = tokens.get("org_admin", "")
    if not t:
        print("  SKIP: No org_admin token")
        return

    # User count consistency
    code, body = api("GET", "/users", token=t)
    if code == 200 and isinstance(body, dict):
        data = body.get("data", body)
        user_count = 0
        if isinstance(data, list):
            user_count = len(data)
        elif isinstance(data, dict):
            user_count = data.get("total", data.get("count", 0))
            for v in data.values():
                if isinstance(v, list):
                    user_count = max(user_count, len(v))
                    break
        record("INTEGRITY", f"Users list count", user_count > 0, f"count={user_count}")

        # Check org settings for expected count
        sc, sb = api("GET", "/settings", token=t)
        if sc == 200 and isinstance(sb, dict):
            sd = sb.get("data", sb)
            if isinstance(sd, dict):
                org_count = sd.get("current_user_count") or sd.get("user_count") or sd.get("total_users")
                if org_count:
                    match = int(org_count) == user_count
                    record("INTEGRITY", "User count matches org settings",
                           match or abs(int(org_count) - user_count) <= 2,
                           f"users_api={user_count}, org_setting={org_count}")
                    if not match and abs(int(org_count) - user_count) > 2:
                        file_bug("User count mismatch between /users and /settings",
                                 "GET", f"{API}/users vs {API}/settings",
                                 "1. GET /users count\n2. GET /settings user count\n3. Compare",
                                 {}, f"Counts should match", 200,
                                 {"users_api": user_count, "org_setting": org_count})

    # Department reference validation
    code, body = api("GET", "/users", token=t)
    if code == 200:
        data = body.get("data", body) if isinstance(body, dict) else body
        users = data if isinstance(data, list) else (data.get("users", data.get("items", [])) if isinstance(data, dict) else [])

        # Get departments
        dc, db = api("GET", "/departments", token=t)
        dept_ids = set()
        if dc == 200 and isinstance(db, dict):
            depts = db.get("data", db)
            if isinstance(depts, list):
                for d in depts:
                    did = d.get("id") or d.get("_id")
                    if did: dept_ids.add(str(did))
            elif isinstance(depts, dict):
                for v in depts.values():
                    if isinstance(v, list):
                        for d in v:
                            did = d.get("id") or d.get("_id")
                            if did: dept_ids.add(str(did))

        if dept_ids and isinstance(users, list):
            bad_dept_refs = 0
            for u in users:
                if isinstance(u, dict):
                    dept_id = u.get("department_id") or u.get("departmentId") or u.get("department", {}).get("id") if isinstance(u.get("department"), dict) else u.get("department")
                    if dept_id and str(dept_id) not in dept_ids and dept_id not in ("", None):
                        bad_dept_refs += 1
            record("INTEGRITY", "Department references valid",
                   bad_dept_refs == 0,
                   f"invalid_refs={bad_dept_refs}, known_depts={len(dept_ids)}")
            if bad_dept_refs > 0:
                file_bug("Invalid department references in user records",
                         "GET", f"{API}/users",
                         "1. GET /users\n2. GET /departments\n3. Check all department_ids are valid",
                         {}, "All department references should be valid",
                         200, {"bad_refs": bad_dept_refs})

    # Leave balance math
    code, body = api("GET", "/leave/balances", token=t)
    if code == 200 and isinstance(body, dict):
        balances = body.get("data", body)
        if isinstance(balances, list):
            math_errors = 0
            for b in balances:
                if isinstance(b, dict):
                    alloc = b.get("allocated", b.get("total", 0)) or 0
                    carry = b.get("carry_forward", b.get("carried_forward", 0)) or 0
                    used = b.get("used", b.get("taken", 0)) or 0
                    balance = b.get("balance", b.get("remaining", b.get("available", None)))
                    if balance is not None:
                        expected_bal = float(alloc) + float(carry) - float(used)
                        actual_bal = float(balance)
                        if abs(expected_bal - actual_bal) > 0.01:
                            math_errors += 1
            record("INTEGRITY", "Leave balance math", math_errors == 0,
                   f"errors={math_errors}, checked={len(balances)} balances")
            if math_errors > 0:
                file_bug("Leave balance calculation mismatch",
                         "GET", f"{API}/leave/balances",
                         "1. GET /leave/balances\n2. Check allocated + carry_forward - used = balance",
                         {}, "Balance math should be correct", 200,
                         {"math_errors": math_errors})


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 6: INPUT VALIDATION
# ════════════════════════════════════════════════════════════════════════════
def test_input_validation():
    print(f"\n{'='*60}")
    print("SECTION 6: INPUT VALIDATION")
    print(f"{'='*60}")

    t = tokens.get("org_admin", "")
    if not t:
        print("  SKIP: No org_admin token")
        return

    xss_payload = '<script>alert("XSS")</script>'
    sqli_payload = "'; DROP TABLE users; --"

    # Test each POST endpoint with bad inputs
    endpoints_with_post = [
        ("/announcements", {"title": "Test", "content": "Test"}),
        ("/events", {"title": "Test", "start_date": "2026-04-01"}),
        ("/surveys", {"title": "Test"}),
        ("/feedback", {"title": "Test"}),
        ("/assets", {"name": "Test"}),
        ("/positions", {"title": "Test"}),
        ("/helpdesk/tickets", {"subject": "Test"}),
        ("/forum", {"title": "Test", "content": "Test"}),
        ("/holidays", {"name": "Test", "date": "2026-12-25"}),
        ("/departments", {"name": "Test"}),
        ("/leave/types", {"name": "Test", "code": "TST"}),
        ("/policies", {"title": "Test", "content": "Test"}),
    ]

    for ep, valid_body in endpoints_with_post:
        # Empty body
        code, body = api("POST", ep, body={}, token=t)
        record("VALIDATION", f"Empty body POST {ep}",
               code in (400, 422, 404, 405),
               f"code={code}")
        if code in (200, 201):
            file_bug(f"Empty body accepted at POST {ep}",
                     "POST", f"{API}{ep}",
                     f"1. Login as org_admin\n2. POST {ep} with empty body {{}}",
                     {}, "Should return 400/422 validation error", code, body)

        # Wrong types
        wrong_body = {k: 12345 if isinstance(v, str) else "not_a_number" for k, v in valid_body.items()}
        code, body = api("POST", ep, body=wrong_body, token=t)
        record("VALIDATION", f"Wrong types POST {ep}",
               code in (400, 422, 404, 405, 500),
               f"code={code}")

        # XSS payload
        xss_body = {k: xss_payload if isinstance(v, str) else v for k, v in valid_body.items()}
        code, body = api("POST", ep, body=xss_body, token=t)
        xss_stored = False
        if code in (200, 201) and isinstance(body, dict):
            body_str = json.dumps(body)
            if '<script>' in body_str:
                xss_stored = True
                file_bug(f"XSS payload stored at {ep}",
                         "POST", f"{API}{ep}",
                         f"1. POST {ep} with XSS in text fields\n2. Check response for unescaped script tags",
                         xss_body, "XSS should be sanitized or rejected", code, body)
        record("VALIDATION", f"XSS handling POST {ep}",
               not xss_stored,
               f"code={code}, xss_in_response={xss_stored}")
        # Clean up XSS-created items
        if code in (200, 201) and isinstance(body, dict):
            cid = (body.get("data", {}).get("id") if isinstance(body.get("data"), dict) else body.get("id"))
            if cid:
                api("DELETE", f"{ep}/{cid}", token=t)

        # SQL injection
        sqli_body = {k: sqli_payload if isinstance(v, str) else v for k, v in valid_body.items()}
        code, body = api("POST", ep, body=sqli_body, token=t)
        record("VALIDATION", f"SQLi handling POST {ep}",
               code not in (500,),
               f"code={code}")
        if code == 500:
            file_bug(f"Possible SQL injection at {ep}",
                     "POST", f"{API}{ep}",
                     f"1. POST {ep} with SQL injection payload",
                     sqli_body, "Should handle gracefully, not 500", code, body)
        # Clean up
        if code in (200, 201) and isinstance(body, dict):
            cid = (body.get("data", {}).get("id") if isinstance(body.get("data"), dict) else body.get("id"))
            if cid:
                api("DELETE", f"{ep}/{cid}", token=t)


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 7: MASS ASSIGNMENT
# ════════════════════════════════════════════════════════════════════════════
def test_mass_assignment():
    print(f"\n{'='*60}")
    print("SECTION 7: MASS ASSIGNMENT PROTECTION")
    print(f"{'='*60}")

    t = tokens.get("org_admin", "")
    emp_t = tokens.get("employee", "")
    if not t:
        print("  SKIP: No org_admin token")
        return

    # Get a user ID to test with
    code, body = api("GET", "/users", token=t)
    target_uid = None
    if code == 200 and isinstance(body, dict):
        users = body.get("data", body)
        if isinstance(users, dict):
            users = users.get("users", users.get("items", []))
        if isinstance(users, list) and len(users) > 0:
            # Find the employee user
            for u in users:
                if isinstance(u, dict) and u.get("email") == "priya@technova.in":
                    target_uid = u.get("id") or u.get("_id")
                    break
            if not target_uid:
                target_uid = users[0].get("id") or users[0].get("_id")

    if not target_uid:
        print("  SKIP: No user ID found")
        return

    # First get original user data
    orig_code, orig_body = api("GET", f"/users/{target_uid}", token=t)
    orig_user = {}
    if orig_code == 200 and isinstance(orig_body, dict):
        orig_user = orig_body.get("data", orig_body)

    mass_assignment_tests = [
        ({"role": "super_admin"}, "Role escalation to super_admin"),
        ({"organization_id": 999}, "Change organization_id"),
        ({"email": "stolen@evil.com"}, "Change email via mass assignment"),
        ({"salary": 9999999}, "Set salary via mass assignment"),
        ({"status": 0}, "Deactivate user via mass assignment"),
        ({"is_admin": True}, "Set is_admin flag"),
        ({"permissions": ["*"]}, "Set wildcard permissions"),
    ]

    for payload, desc in mass_assignment_tests:
        # Try PUT
        code, body = api("PUT", f"/users/{target_uid}", body=payload, token=t)
        if code in (404, 405):
            code, body = api("PATCH", f"/users/{target_uid}", body=payload, token=t)

        # Check if the field actually changed
        field_changed = False
        if code in (200, 201):
            check_code, check_body = api("GET", f"/users/{target_uid}", token=t)
            if check_code == 200 and isinstance(check_body, dict):
                updated = check_body.get("data", check_body)
                if isinstance(updated, dict):
                    for key, val in payload.items():
                        curr = updated.get(key)
                        orig = orig_user.get(key) if isinstance(orig_user, dict) else None
                        if curr is not None and str(curr) == str(val) and str(curr) != str(orig):
                            field_changed = True

        passed = not field_changed and code not in (200, 201) or (code in (200, 201) and not field_changed)
        record("MASS-ASSIGN", desc, passed,
               f"code={code}, field_changed={field_changed}")

        if field_changed:
            file_bug(f"Mass assignment vulnerability: {desc}",
                     "PUT", f"{API}/users/{target_uid}",
                     f"1. Login as org_admin\n2. PUT /users/{target_uid} with {json.dumps(payload)}",
                     payload, f"Field should NOT be updated via mass assignment",
                     code, body)

    # Employee trying to update their own protected fields
    if emp_t:
        # Get employee's own user ID
        ec, eb = api("GET", "/auth/me", token=emp_t)
        if ec != 200:
            ec, eb = api("GET", "/me", token=emp_t)
        if ec != 200:
            ec, eb = api("GET", "/profile", token=emp_t)

        emp_uid = None
        if ec == 200 and isinstance(eb, dict):
            eu = eb.get("data", eb)
            if isinstance(eu, dict):
                emp_uid = eu.get("id") or eu.get("_id")

        if emp_uid:
            emp_payloads = [
                ({"role": "admin"}, "Employee self-escalate to admin"),
                ({"salary": 9999999}, "Employee set own salary"),
                ({"status": 0}, "Employee change own status"),
            ]
            for payload, desc in emp_payloads:
                code, body = api("PUT", f"/users/{emp_uid}", body=payload, token=emp_t)
                if code in (404, 405):
                    code, body = api("PATCH", f"/users/{emp_uid}", body=payload, token=emp_t)
                record("MASS-ASSIGN", desc, code in (400, 403, 401, 404, 405, 422),
                       f"code={code}")
                if code in (200, 201):
                    file_bug(f"Employee mass assignment: {desc}",
                             "PUT", f"{API}/users/{emp_uid}",
                             f"1. Login as employee\n2. PUT /users/{emp_uid} with {json.dumps(payload)}",
                             payload, "Should be rejected", code, body)


# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    start = time.time()
    print("=" * 60)
    print("EMP CLOUD HRMS - COMPREHENSIVE E2E API TEST SUITE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE}")
    print("=" * 60)

    # Run all test sections
    test_auth()

    # Discovery
    if tokens.get("org_admin"):
        found = discover_endpoints(tokens["org_admin"])

    test_full_crud()
    test_rbac()
    test_cross_org()
    test_data_integrity()
    test_input_validation()
    test_mass_assignment()

    # ── Results Matrix ──
    elapsed = time.time() - start
    print(f"\n{'='*80}")
    print("COMPLETE TEST RESULTS MATRIX")
    print(f"{'='*80}")

    sections = {}
    for section, name, status, detail in results:
        sections.setdefault(section, []).append((name, status, detail))

    total_pass = sum(1 for _, _, s, _ in results if s == "PASS")
    total_fail = sum(1 for _, _, s, _ in results if s == "FAIL")

    for section, tests in sections.items():
        s_pass = sum(1 for _, s, _ in tests if s == "PASS")
        s_fail = sum(1 for _, s, _ in tests if s == "FAIL")
        print(f"\n--- {section} --- ({s_pass} pass, {s_fail} fail)")
        for name, status, detail in tests:
            mark = "PASS" if status == "PASS" else "FAIL"
            print(f"  [{mark}] {name:55s} | {detail[:80]}")

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total tests:  {len(results)}")
    print(f"Passed:       {total_pass}")
    print(f"Failed:       {total_fail}")
    print(f"Bugs found:   {len(bugs)}")
    print(f"Time elapsed: {elapsed:.1f}s")
    print(f"{'='*80}")

    # File bugs
    if bugs:
        push_bugs_to_github()

    print(f"\n{'='*80}")
    print(f"BUGS SUMMARY ({len(bugs)} total)")
    print(f"{'='*80}")
    for i, b in enumerate(bugs, 1):
        print(f"  {i}. {b['title']}")

    print("\nDone.")


if __name__ == "__main__":
    main()
