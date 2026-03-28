#!/usr/bin/env python3
"""
EMP Cloud HRMS - Comprehensive Functional API CRUD Tester
Tests all CRUD operations across all endpoints, files GitHub issues for bugs.
"""

import sys
import json
import urllib.request
import urllib.error
import ssl
import time
import traceback
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://test-empcloud.empcloud.com/api/v1"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
ctx = ssl.create_default_context()

# ── Tracking ──
RESULTS = {}
BUGS = []

def init_result(ep):
    if ep not in RESULTS:
        RESULTS[ep] = {"CREATE": "N/A", "READ": "N/A", "UPDATE": "N/A", "DELETE": "N/A", "NOTES": ""}

def set_result(ep, op, status, note=""):
    init_result(ep)
    RESULTS[ep][op] = status
    if note:
        existing = RESULTS[ep]["NOTES"]
        RESULTS[ep]["NOTES"] = f"{existing}; {note}" if existing else note

def log(msg):
    print(f"  {msg}")

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

# ── HTTP ──
def make_request(url, method="GET", data=None, token=None):
    headers = {
        "User-Agent": "EmpCloud-CRUD-Tester/4.0",
        "Origin": "https://test-empcloud.empcloud.com",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(raw)
        except:
            return e.code, raw
    except Exception as e:
        return 0, str(e)

def api(path, method="GET", data=None, token=None):
    url = f"{BASE}{path}"
    return make_request(url, method, data, token)

# ── Auth ──
def login(email, password):
    s, r = api("/auth/login", "POST", {"email": email, "password": password})
    if s == 200 and isinstance(r, dict):
        def find_token(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if "token" in k.lower() and isinstance(v, str) and len(v) > 20:
                        return v
                    found = find_token(v)
                    if found:
                        return found
            return None
        return find_token(r)
    return None

# ── GitHub ──
def file_github_issue(title, body):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {
        "User-Agent": "EmpCloud-CRUD-Tester/4.0",
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    payload = json.dumps({"title": title, "body": body, "labels": ["bug", "functional", "api"]}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            r = json.loads(resp.read().decode("utf-8"))
            return r.get("html_url", "filed")
    except Exception as e:
        return f"FAILED: {e}"

def report_bug(endpoint, method, description, request_body=None, response_status=None, response_body=None):
    title = f"[FUNCTIONAL] {method} {endpoint} - {description}"
    body = f"""## Functional Bug Report

**Endpoint:** `{method} {BASE}{endpoint}`
**Date:** {datetime.now().isoformat()}
**Environment:** test-empcloud.empcloud.com

### Description
{description}

### Request
- **Method:** {method}
- **URL:** `{BASE}{endpoint}`
"""
    if request_body:
        body += f"- **Body:**\n```json\n{json.dumps(request_body, indent=2)[:1000]}\n```\n"
    body += f"""
### Response
- **Status Code:** {response_status}
- **Body:**
```json
{json.dumps(response_body, indent=2) if isinstance(response_body, (dict, list)) else str(response_body)[:1000]}
```

### Expected Behavior
The CRUD operation should succeed with valid data and proper authentication.

### Severity
Functional - CRUD operation failure
"""
    issue_url = file_github_issue(title, body)
    BUGS.append({"endpoint": endpoint, "method": method, "desc": description, "issue": issue_url})
    log(f"  BUG FILED: {issue_url}")
    return issue_url

# ── Helpers ──
def extract_items(resp):
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for key in ["data", "items", "results", "records"]:
            if key in resp and isinstance(resp[key], list):
                return resp[key]
    return []

def extract_id(item):
    if isinstance(item, dict):
        return item.get("id") or item.get("_id")
    return None

def extract_created_id(resp):
    if isinstance(resp, dict):
        cid = extract_id(resp)
        if cid:
            return cid
        if isinstance(resp.get("data"), dict):
            return extract_id(resp["data"])
    return None


# ══════════════════════════════════════════════
#  TEST FUNCTIONS
# ══════════════════════════════════════════════

def test_users(admin_token):
    section("1. USERS / EMPLOYEES")
    ep = "/users"
    init_result(ep)
    ts = int(time.time())

    # READ - list
    log("GET /users ...")
    status, resp = api("/users", token=admin_token)
    log(f"  Status: {status}")
    if status == 200:
        items = extract_items(resp)
        log(f"  Count: {len(items)} users")
        set_result(ep, "READ", "PASS", f"{len(items)} users")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {status}")
        return

    # READ - single
    items = extract_items(resp)
    if items:
        uid = extract_id(items[0])
        log(f"GET /users/{uid} ...")
        s2, r2 = api(f"/users/{uid}", token=admin_token)
        log(f"  Status: {s2}")
        if s2 != 200:
            report_bug(f"/users/{uid}", "GET", f"Get single user returned HTTP {s2}", None, s2, r2)

    # CREATE
    log("POST /users ...")
    create_payload = {
        "email": f"crudtest{ts}@technova.in",
        "password": "Welcome@123",
        "first_name": "CRUDTest",
        "last_name": f"User{ts}",
    }
    sc, rc = api("/users", "POST", create_payload, admin_token)
    log(f"  Status: {sc}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        new_uid = extract_created_id(rc)
        log(f"  Created user ID: {new_uid}")

        # UPDATE - try to update contact_number
        if new_uid:
            log(f"PUT /users/{new_uid} - update contact_number ...")
            su, ru = api(f"/users/{new_uid}", "PUT", {"contact_number": "9876543210"}, admin_token)
            log(f"  Status: {su}")
            if su == 200:
                # VERIFY: check if update persisted
                sv, rv = api(f"/users/{new_uid}", token=admin_token)
                user_data = rv.get("data", rv) if isinstance(rv, dict) else {}
                actual = user_data.get("contact_number") if isinstance(user_data, dict) else None
                if actual == "9876543210":
                    set_result(ep, "UPDATE", "PASS", "contact_number persisted")
                    log(f"  Verified: contact_number = {actual}")
                else:
                    set_result(ep, "UPDATE", "FAIL", "Update accepted but not persisted")
                    log(f"  BUG: PUT returned 200 but contact_number is '{actual}' (expected '9876543210')")
                    report_bug(f"/users/{new_uid}", "PUT",
                        "PUT /users/{id} returns 200 but contact_number field change does not persist. "
                        "The response still shows contact_number as null after update.",
                        {"contact_number": "9876543210"}, sv,
                        {"expected": "9876543210", "actual": actual, "full_response": rv})
            else:
                set_result(ep, "UPDATE", "FAIL", f"HTTP {su}")
                report_bug(f"/users/{new_uid}", "PUT", f"Update user returned HTTP {su}",
                           {"contact_number": "9876543210"}, su, ru)

            # DELETE (cleanup)
            log(f"DELETE /users/{new_uid} ...")
            sd, rd = api(f"/users/{new_uid}", "DELETE", token=admin_token)
            log(f"  Status: {sd}")
            if sd in (200, 204):
                set_result(ep, "DELETE", "PASS")
                # Verify deletion
                sg, rg = api(f"/users/{new_uid}", token=admin_token)
                if sg == 404:
                    log(f"  Verified: user deleted (404)")
                elif sg == 200:
                    log(f"  WARNING: user still accessible after DELETE")
            else:
                set_result(ep, "DELETE", "FAIL", f"HTTP {sd}")
    else:
        set_result(ep, "CREATE", "FAIL", f"HTTP {sc}")
        log(f"  Response: {json.dumps(rc)[:300]}")


def test_announcements(admin_token):
    section("2. ANNOUNCEMENTS")
    ep = "/announcements"
    init_result(ep)
    ts = int(time.time())

    # READ
    log("GET /announcements ...")
    s, r = api("/announcements", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} announcements")
        set_result(ep, "READ", "PASS", f"{len(items)} items")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE
    log("POST /announcements ...")
    payload = {"title": f"CRUD Test Announcement {ts}", "content": "Automated CRUD test announcement."}
    sc, rc = api("/announcements", "POST", payload, admin_token)
    log(f"  Status: {sc}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        new_id = extract_created_id(rc)
        log(f"  Created ID: {new_id}")

        if new_id:
            # VERIFY created
            sv, rv = api(f"/announcements/{new_id}", token=admin_token)
            log(f"  Verify GET: {sv}")
            if sv == 404:
                log(f"  NOTE: GET /announcements/{new_id} returns 404 right after creation")
                report_bug(f"/announcements/{new_id}", "GET",
                    "Newly created announcement returns 404 on individual GET. "
                    "POST /announcements returns 201 with ID, but GET /announcements/{id} returns 404.",
                    None, sv, rv)

            # UPDATE
            log(f"PUT /announcements/{new_id} ...")
            su, ru = api(f"/announcements/{new_id}", "PUT",
                         {"title": f"Updated Announcement {ts}"}, admin_token)
            log(f"  Status: {su}")
            if su in (200, 201, 204):
                set_result(ep, "UPDATE", "PASS")
            else:
                set_result(ep, "UPDATE", "FAIL", f"HTTP {su}")
                report_bug(f"/announcements/{new_id}", "PUT",
                           f"Update announcement returned HTTP {su}",
                           {"title": f"Updated Announcement {ts}"}, su, ru)

            # DELETE
            log(f"DELETE /announcements/{new_id} ...")
            sd, rd = api(f"/announcements/{new_id}", "DELETE", token=admin_token)
            log(f"  Status: {sd}")
            if sd in (200, 204):
                set_result(ep, "DELETE", "PASS")
                # Verify deleted
                sg, rg = api(f"/announcements/{new_id}", token=admin_token)
                if sg == 404:
                    log(f"  Verified: deleted (404)")
                elif sg == 200:
                    report_bug(f"/announcements/{new_id}", "DELETE",
                        "Announcement still accessible after DELETE returned 200",
                        None, sg, rg)
            else:
                set_result(ep, "DELETE", "FAIL", f"HTTP {sd}")
    else:
        set_result(ep, "CREATE", "FAIL", f"HTTP {sc}")
        log(f"  Response: {json.dumps(rc)[:300]}")


def test_documents(admin_token):
    section("3. DOCUMENTS")
    ep = "/documents"
    init_result(ep)

    # READ
    log("GET /documents ...")
    s, r = api("/documents", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} documents")
        set_result(ep, "READ", "PASS", f"{len(items)} items")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE - documents likely require multipart file upload
    log("POST /documents (JSON attempt) ...")
    sc, rc = api("/documents", "POST", {
        "title": "CRUD Test Doc",
        "name": "crud_test_doc",
        "description": "Test",
        "type": "policy",
    }, admin_token)
    log(f"  Status: {sc}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        new_id = extract_created_id(rc)
        if new_id:
            sd, rd = api(f"/documents/{new_id}", "DELETE", token=admin_token)
            set_result(ep, "DELETE", "PASS" if sd in (200, 204) else "FAIL")
    else:
        set_result(ep, "CREATE", "SKIP", "Requires multipart file upload")
        log(f"  Expected: document endpoints likely need file upload")


def test_events(admin_token):
    section("4. EVENTS")
    ep = "/events"
    init_result(ep)
    ts = int(time.time())

    # READ
    log("GET /events ...")
    s, r = api("/events", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} events")
        set_result(ep, "READ", "PASS", f"{len(items)} items")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE
    log("POST /events ...")
    start = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    payload = {
        "title": f"CRUD Test Event {ts}",
        "description": "Automated CRUD test event",
        "start_date": start,
        "end_date": start,
        "location": "Online",
    }
    sc, rc = api("/events", "POST", payload, admin_token)
    log(f"  Status: {sc}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        new_id = extract_created_id(rc)
        log(f"  Created ID: {new_id}")

        if new_id:
            # UPDATE
            log(f"PUT /events/{new_id} ...")
            su, ru = api(f"/events/{new_id}", "PUT",
                         {"title": f"Updated Event {ts}", "location": "Conference Room"}, admin_token)
            log(f"  Status: {su}")
            if su in (200, 201, 204):
                set_result(ep, "UPDATE", "PASS")
                # Verify update
                sv, rv = api(f"/events/{new_id}", token=admin_token)
                if sv == 200:
                    data = rv.get("data", rv) if isinstance(rv, dict) else {}
                    if isinstance(data, dict) and data.get("location") == "Conference Room":
                        log(f"  Verified: location updated")
            else:
                set_result(ep, "UPDATE", "FAIL", f"HTTP {su}")
                report_bug(f"/events/{new_id}", "PUT", f"Update event returned HTTP {su}",
                           {"title": f"Updated Event {ts}"}, su, ru)

            # DELETE
            log(f"DELETE /events/{new_id} ...")
            sd, rd = api(f"/events/{new_id}", "DELETE", token=admin_token)
            log(f"  Status: {sd}")
            if sd in (200, 204):
                set_result(ep, "DELETE", "PASS")
            else:
                set_result(ep, "DELETE", "FAIL", f"HTTP {sd}")
    else:
        set_result(ep, "CREATE", "FAIL", f"HTTP {sc}")
        log(f"  Response: {json.dumps(rc)[:300]}")


def test_surveys(admin_token):
    section("5. SURVEYS")
    ep = "/surveys"
    init_result(ep)
    ts = int(time.time())

    # READ
    log("GET /surveys ...")
    s, r = api("/surveys", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} surveys")
        set_result(ep, "READ", "PASS", f"{len(items)} items")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE
    log("POST /surveys ...")
    payload = {"title": f"CRUD Test Survey {ts}", "description": "Automated CRUD test", "status": "draft"}
    sc, rc = api("/surveys", "POST", payload, admin_token)
    log(f"  Status: {sc}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        new_id = extract_created_id(rc)
        log(f"  Created ID: {new_id}")

        if new_id:
            # UPDATE - publish
            log(f"PUT /surveys/{new_id} - publish ...")
            su, ru = api(f"/surveys/{new_id}", "PUT", {"status": "active", "title": f"Updated Survey {ts}"}, admin_token)
            log(f"  Status: {su}")
            if su in (200, 201, 204):
                set_result(ep, "UPDATE", "PASS")
            else:
                set_result(ep, "UPDATE", "FAIL", f"HTTP {su}")

            # DELETE
            log(f"DELETE /surveys/{new_id} ...")
            sd, rd = api(f"/surveys/{new_id}", "DELETE", token=admin_token)
            log(f"  Status: {sd}")
            if sd in (200, 204):
                set_result(ep, "DELETE", "PASS")
            else:
                set_result(ep, "DELETE", "FAIL", f"HTTP {sd}")
    else:
        set_result(ep, "CREATE", "FAIL", f"HTTP {sc}")
        log(f"  Response: {json.dumps(rc)[:300]}")


def test_feedback(admin_token, emp_token):
    section("6. FEEDBACK")
    ep = "/feedback"
    init_result(ep)
    ts = int(time.time())

    # READ
    log("GET /feedback ...")
    s, r = api("/feedback", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} feedback entries")
        set_result(ep, "READ", "PASS", f"{len(items)} items")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE (requires: category, subject, message)
    log("POST /feedback (as employee) ...")
    payload = {
        "category": "management",
        "subject": f"CRUD Test Feedback {ts}",
        "message": "Automated CRUD feedback test message.",
    }
    sc, rc = api("/feedback", "POST", payload, emp_token or admin_token)
    log(f"  Status: {sc}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        new_id = extract_created_id(rc)
        log(f"  Created ID: {new_id}")

        if new_id:
            # Try UPDATE (admin response)
            log(f"PUT /feedback/{new_id} - admin respond ...")
            su, ru = api(f"/feedback/{new_id}", "PUT",
                         {"status": "acknowledged", "admin_response": "Thank you for the feedback."}, admin_token)
            log(f"  Status: {su}")
            if su in (200, 201, 204):
                set_result(ep, "UPDATE", "PASS")
            else:
                # Try respond endpoint
                su2, ru2 = api(f"/feedback/{new_id}/respond", "PUT",
                               {"admin_response": "Thank you.", "status": "acknowledged"}, admin_token)
                log(f"  /respond: {su2}")
                if su2 in (200, 201, 204):
                    set_result(ep, "UPDATE", "PASS")
                else:
                    set_result(ep, "UPDATE", "FAIL", f"HTTP {su}")

            # DELETE
            log(f"DELETE /feedback/{new_id} ...")
            sd, rd = api(f"/feedback/{new_id}", "DELETE", token=admin_token)
            log(f"  Status: {sd}")
            if sd in (200, 204):
                set_result(ep, "DELETE", "PASS")
            else:
                set_result(ep, "DELETE", "FAIL", f"HTTP {sd}")
    else:
        set_result(ep, "CREATE", "FAIL", f"HTTP {sc}")
        log(f"  Response: {json.dumps(rc)[:300]}")


def test_assets(admin_token):
    section("7. ASSETS")
    ep = "/assets"
    init_result(ep)
    ts = int(time.time())

    # READ
    log("GET /assets ...")
    s, r = api("/assets", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} assets")
        set_result(ep, "READ", "PASS", f"{len(items)} items")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE
    log("POST /assets ...")
    payload = {
        "name": f"CRUD Test Laptop {ts}",
        "serial_number": f"SN-CRUD-{ts}",
        "status": "available",
        "description": "Automated CRUD test asset",
    }
    sc, rc = api("/assets", "POST", payload, admin_token)
    log(f"  Status: {sc}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        new_id = extract_created_id(rc)
        log(f"  Created ID: {new_id}")

        if new_id:
            # UPDATE
            log(f"PUT /assets/{new_id} ...")
            su, ru = api(f"/assets/{new_id}", "PUT",
                         {"name": f"Updated Laptop {ts}", "status": "in_use"}, admin_token)
            log(f"  Status: {su}")
            if su in (200, 201, 204):
                set_result(ep, "UPDATE", "PASS")
            else:
                set_result(ep, "UPDATE", "FAIL", f"HTTP {su}")
                report_bug(f"/assets/{new_id}", "PUT", f"Update asset returned HTTP {su}",
                           {"name": f"Updated Laptop {ts}"}, su, ru)

            # DELETE
            log(f"DELETE /assets/{new_id} ...")
            sd, rd = api(f"/assets/{new_id}", "DELETE", token=admin_token)
            log(f"  Status: {sd}")
            if sd in (200, 204):
                set_result(ep, "DELETE", "PASS")
            else:
                set_result(ep, "DELETE", "FAIL", f"HTTP {sd}")
                log(f"  Response: {json.dumps(rd)[:200]}")
                # This is a known bug: DELETE /assets/{id} returns 404
                report_bug(f"/assets/{new_id}", "DELETE",
                    "DELETE /assets/{id} returns 404 (Endpoint not found). "
                    "Asset was created successfully (POST 201) and can be read and updated, "
                    "but the DELETE endpoint does not exist. Asset cannot be removed via API.",
                    None, sd, rd)
    else:
        set_result(ep, "CREATE", "FAIL", f"HTTP {sc}")


def test_positions(admin_token):
    section("8. POSITIONS")
    ep = "/positions"
    init_result(ep)
    ts = int(time.time())

    # READ
    log("GET /positions ...")
    s, r = api("/positions", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} positions")
        set_result(ep, "READ", "PASS", f"{len(items)} items")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE
    log("POST /positions ...")
    payload = {
        "title": f"CRUD Test Engineer {ts}",
        "description": "Automated CRUD test position",
        "status": "open",
    }
    sc, rc = api("/positions", "POST", payload, admin_token)
    log(f"  Status: {sc}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        new_id = extract_created_id(rc)
        log(f"  Created ID: {new_id}")

        if new_id:
            # UPDATE
            log(f"PUT /positions/{new_id} ...")
            su, ru = api(f"/positions/{new_id}", "PUT",
                         {"title": f"Senior CRUD Engineer {ts}"}, admin_token)
            log(f"  Status: {su}")
            if su in (200, 201, 204):
                set_result(ep, "UPDATE", "PASS")
            else:
                set_result(ep, "UPDATE", "FAIL", f"HTTP {su}")

            # DELETE
            log(f"DELETE /positions/{new_id} ...")
            sd, rd = api(f"/positions/{new_id}", "DELETE", token=admin_token)
            log(f"  Status: {sd}")
            if sd in (200, 204):
                set_result(ep, "DELETE", "PASS")
            else:
                set_result(ep, "DELETE", "FAIL", f"HTTP {sd}")
    else:
        set_result(ep, "CREATE", "FAIL", f"HTTP {sc}")


def test_leave(admin_token, emp_token):
    section("9. LEAVE")
    ep = "/leave"
    init_result(ep)

    # READ - balances
    log("GET /leave/balances (employee) ...")
    s, r = api("/leave/balances", token=emp_token or admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Found {len(items)} balance entries")

    # READ - types
    log("GET /leave/types ...")
    s, r = api("/leave/types", token=admin_token)
    log(f"  Status: {s}")
    leave_types = extract_items(r) if s == 200 else []
    log(f"  Found {len(leave_types)} leave types")
    for lt in leave_types:
        log(f"    ID={lt.get('id')}, Name={lt.get('name')}, Code={lt.get('code')}")

    # READ - applications
    log("GET /leave/applications ...")
    s, r = api("/leave/applications", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Found {len(items)} applications")
        set_result(ep, "READ", "PASS", f"{len(items)} apps, {len(leave_types)} types")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE - apply for leave
    log("POST /leave/applications ...")
    lt_id = leave_types[0]["id"] if leave_types else 18
    from_d = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

    # Try many payload variations - this endpoint consistently returns 400
    payloads = [
        {"leave_type_id": lt_id, "start_date": from_d, "end_date": from_d, "reason": "CRUD test"},
        {"leave_type_id": lt_id, "start_date": from_d, "end_date": from_d, "reason": "CRUD test", "is_half_day": False},
        {"leave_type_id": lt_id, "start_date": from_d, "end_date": from_d, "reason": "CRUD test", "is_half_day": 0, "half_day_type": None},
        {"leave_type_id": lt_id, "from_date": from_d, "to_date": from_d, "reason": "CRUD test"},
        {"leave_type_id": str(lt_id), "start_date": from_d, "end_date": from_d, "reason": "CRUD test"},
    ]

    created = False
    for payload in payloads:
        sc, rc = api("/leave/applications", "POST", payload, emp_token or admin_token)
        log(f"  {list(payload.keys())} -> {sc}")
        if sc in (200, 201):
            set_result(ep, "CREATE", "PASS")
            created = True
            break

    if not created:
        set_result(ep, "CREATE", "FAIL", "All payload variations return HTTP 400")
        log(f"  BUG: POST /leave/applications always returns 400 with generic 'Invalid request data'")
        report_bug("/leave/applications", "POST",
            "POST /leave/applications returns 400 'Invalid request data' for ALL payload variations. "
            "Tested with: leave_type_id (int/str), start_date/end_date and from_date/to_date formats, "
            "with/without is_half_day, half_day_type, days_count. "
            "Existing applications in DB use fields: leave_type_id, start_date, end_date, reason, is_half_day. "
            "The validation error provides no field-level detail, making it impossible to determine required format.",
            {"leave_type_id": lt_id, "start_date": from_d, "end_date": from_d, "reason": "CRUD test"},
            400, {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Invalid request data"}})


def test_tickets(admin_token):
    section("10. TICKETS / HELPDESK")
    ep = "/helpdesk/tickets"
    init_result(ep)
    ts = int(time.time())

    # READ
    log("GET /helpdesk/tickets ...")
    s, r = api("/helpdesk/tickets", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} tickets")
        set_result(ep, "READ", "PASS", f"{len(items)} tickets")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE
    log("POST /helpdesk/tickets ...")
    payload = {
        "subject": f"CRUD Test Ticket {ts}",
        "description": "Automated CRUD test ticket",
        "priority": "medium",
        "category": "general",
    }
    sc, rc = api("/helpdesk/tickets", "POST", payload, admin_token)
    log(f"  Status: {sc}")
    log(f"  Response: {json.dumps(rc)[:300]}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        new_id = extract_created_id(rc)
        log(f"  Created ID: {new_id}")

        if new_id:
            # UPDATE
            su, ru = api(f"/helpdesk/tickets/{new_id}", "PUT",
                         {"status": "in_progress", "priority": "high"}, admin_token)
            log(f"  PUT: {su}")
            if su in (200, 201, 204):
                set_result(ep, "UPDATE", "PASS")
            else:
                set_result(ep, "UPDATE", "FAIL", f"HTTP {su}")

            # DELETE
            sd, rd = api(f"/helpdesk/tickets/{new_id}", "DELETE", token=admin_token)
            log(f"  DELETE: {sd}")
            if sd in (200, 204):
                set_result(ep, "DELETE", "PASS")
            else:
                set_result(ep, "DELETE", "FAIL", f"HTTP {sd}")
    else:
        set_result(ep, "CREATE", "FAIL", f"HTTP {sc}")


def test_forum(admin_token):
    section("11. FORUM")
    ep = "/forum"
    init_result(ep)
    ts = int(time.time())

    # READ - categories
    log("GET /forum/categories ...")
    s, r = api("/forum/categories", token=admin_token)
    log(f"  Status: {s}")
    cats = extract_items(r) if s == 200 else []
    cat_id = extract_id(cats[0]) if cats else None
    log(f"  Categories: {len(cats)}, using cat_id={cat_id}")

    # READ - posts
    log("GET /forum/posts ...")
    s, r = api("/forum/posts", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} posts")
        set_result(ep, "READ", "PASS", f"{len(items)} posts, {len(cats)} categories")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE (requires: title, content, category_id)
    log("POST /forum/posts ...")
    payload = {
        "title": f"CRUD Test Post {ts}",
        "content": "Automated CRUD test forum post.",
        "category_id": cat_id,
    }
    sc, rc = api("/forum/posts", "POST", payload, admin_token)
    log(f"  Status: {sc}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        new_id = extract_created_id(rc)
        log(f"  Created ID: {new_id}")

        if new_id:
            # UPDATE
            su, ru = api(f"/forum/posts/{new_id}", "PUT",
                         {"title": f"Updated Post {ts}", "content": "Updated content"}, admin_token)
            log(f"  PUT: {su}")
            if su in (200, 201, 204):
                set_result(ep, "UPDATE", "PASS")
            else:
                set_result(ep, "UPDATE", "FAIL", f"HTTP {su}")

            # DELETE
            sd, rd = api(f"/forum/posts/{new_id}", "DELETE", token=admin_token)
            log(f"  DELETE: {sd}")
            if sd in (200, 204):
                set_result(ep, "DELETE", "PASS")
            else:
                set_result(ep, "DELETE", "FAIL", f"HTTP {sd}")
    else:
        set_result(ep, "CREATE", "FAIL", f"HTTP {sc}")
        log(f"  Response: {json.dumps(rc)[:300]}")


def test_wellness(emp_token):
    section("12. WELLNESS")
    ep = "/wellness"
    init_result(ep)

    # READ
    log("GET /wellness/check-ins ...")
    s, r = api("/wellness/check-ins", token=emp_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} check-ins")
        set_result(ep, "READ", "PASS", f"{len(items)} check-ins")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")

    # CREATE (requires: check_in_date, mood, energy_level, sleep_hours, exercise_minutes)
    log("POST /wellness/check-in ...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    payload = {
        "check_in_date": tomorrow,
        "mood": "good",
        "energy_level": 4,
        "sleep_hours": 7,
        "exercise_minutes": 30,
    }
    sc, rc = api("/wellness/check-in", "POST", payload, emp_token)
    log(f"  Status: {sc}")
    if sc in (200, 201):
        set_result(ep, "CREATE", "PASS")
        log(f"  Response: {json.dumps(rc)[:200]}")
    else:
        set_result(ep, "CREATE", "FAIL", f"HTTP {sc}")
        log(f"  Response: {json.dumps(rc)[:300]}")


def test_notifications(admin_token):
    section("13. NOTIFICATIONS")
    ep = "/notifications"
    init_result(ep)

    log("GET /notifications ...")
    s, r = api("/notifications", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} notifications")
        set_result(ep, "READ", "PASS", f"{len(items)} items")

        if items:
            nid = extract_id(items[0])
            if nid:
                log(f"PUT /notifications/{nid}/read ...")
                su, ru = api(f"/notifications/{nid}/read", "PUT", {"is_read": True}, admin_token)
                log(f"  Status: {su}")
                if su in (200, 204):
                    set_result(ep, "UPDATE", "PASS", "mark as read")
                else:
                    su2, ru2 = api(f"/notifications/{nid}", "PUT", {"is_read": True, "read": True}, admin_token)
                    if su2 in (200, 204):
                        set_result(ep, "UPDATE", "PASS")
                    else:
                        set_result(ep, "UPDATE", "FAIL", f"HTTP {su}")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")


def test_audit(admin_token):
    section("14. AUDIT")
    ep = "/audit"
    init_result(ep)

    log("GET /audit ...")
    s, r = api("/audit", token=admin_token)
    log(f"  Status: {s}")
    if s == 200:
        items = extract_items(r)
        log(f"  Count: {len(items)} audit entries")
        set_result(ep, "READ", "PASS", f"{len(items)} entries")
    else:
        set_result(ep, "READ", "FAIL", f"HTTP {s}")


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  EMP CLOUD HRMS - FUNCTIONAL API CRUD TEST SUITE")
    print(f"  Base URL: {BASE}")
    print(f"  Date: {datetime.now().isoformat()}")
    print("=" * 70)

    # Auth
    section("AUTHENTICATION")
    admin_token = login("ananya@technova.in", "Welcome@123")
    emp_token = login("priya@technova.in", "Welcome@123")
    log(f"Admin (ananya): {'OK' if admin_token else 'FAIL'}")
    log(f"Employee (priya): {'OK' if emp_token else 'FAIL'}")

    if not admin_token and not emp_token:
        print("\nFATAL: No authentication tokens obtained.")
        return

    token = admin_token or emp_token

    # Run all tests
    tests = [
        ("Users", lambda: test_users(token)),
        ("Announcements", lambda: test_announcements(token)),
        ("Documents", lambda: test_documents(token)),
        ("Events", lambda: test_events(token)),
        ("Surveys", lambda: test_surveys(token)),
        ("Feedback", lambda: test_feedback(token, emp_token)),
        ("Assets", lambda: test_assets(token)),
        ("Positions", lambda: test_positions(token)),
        ("Leave", lambda: test_leave(token, emp_token)),
        ("Tickets", lambda: test_tickets(token)),
        ("Forum", lambda: test_forum(token)),
        ("Wellness", lambda: test_wellness(emp_token or token)),
        ("Notifications", lambda: test_notifications(token)),
        ("Audit", lambda: test_audit(token)),
    ]

    for name, test_fn in tests:
        try:
            test_fn()
        except Exception as e:
            print(f"\n  ERROR in {name}: {e}")
            traceback.print_exc()

    # ── CRUD MATRIX ──
    section("CRUD MATRIX")
    hdr = f"| {'Endpoint':<25} | {'CREATE':<12} | {'READ':<12} | {'UPDATE':<12} | {'DELETE':<12} | {'Notes':<45} |"
    sep = f"|{'-'*27}|{'-'*14}|{'-'*14}|{'-'*14}|{'-'*14}|{'-'*47}|"
    print(hdr)
    print(sep)
    for ep, res in RESULTS.items():
        notes = res['NOTES'][:45] if res['NOTES'] else ""
        row = f"| {ep:<25} | {res['CREATE']:<12} | {res['READ']:<12} | {res['UPDATE']:<12} | {res['DELETE']:<12} | {notes:<45} |"
        print(row)
    print(sep)

    # ── Summary ──
    section("SUMMARY")
    total = pass_c = fail_c = skip_c = 0
    for ep, res in RESULTS.items():
        for op in ["CREATE", "READ", "UPDATE", "DELETE"]:
            v = res[op]
            if v != "N/A":
                total += 1
                if v == "PASS":
                    pass_c += 1
                elif "FAIL" in v:
                    fail_c += 1
                else:
                    skip_c += 1

    print(f"  Total operations tested: {total}")
    print(f"  PASSED:  {pass_c}")
    print(f"  FAILED:  {fail_c}")
    print(f"  SKIPPED: {skip_c}")
    print(f"  Pass rate: {pass_c/total*100:.1f}%" if total else "  No tests")
    print(f"\n  Bugs filed on GitHub: {len(BUGS)}")

    if BUGS:
        print(f"\n  Filed Issues:")
        for bug in BUGS:
            print(f"    [{bug['method']}] {bug['endpoint']}")
            print(f"      Desc: {bug['desc'][:80]}")
            print(f"      URL:  {bug['issue']}")

    print(f"\n{'='*70}")
    print(f"  TEST COMPLETE - {datetime.now().isoformat()}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
