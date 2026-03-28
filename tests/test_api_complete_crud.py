#!/usr/bin/env python3
"""
EMP Cloud HRMS — Complete API CRUD Coverage Test
Pure API testing using urllib.request. No Selenium.
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import time
import sys
import os
from datetime import datetime, timedelta

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── Config ──────────────────────────────────────────────────────────────
BASE = "https://test-empcloud.empcloud.com/api/v1"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
CREDS_ADMIN = {"email": "ananya@technova.in", "password": "Welcome@123"}
CREDS_EMP = {"email": "priya@technova.in", "password": "Welcome@123"}

HEADERS_BASE = {
    "User-Agent": "EmpCloudCRUDTester/1.0",
    "Origin": "https://test-empcloud.empcloud.com",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ── CRUD Matrix storage ─────────────────────────────────────────────────
crud_matrix = []  # list of dicts
bugs = []  # collected bugs to file

# ── Helpers ──────────────────────────────────────────────────────────────
def api(method, path, data=None, token=None, headers_extra=None, raw_data=None):
    """Fire an HTTP request; return (status, body_dict_or_text, headers)."""
    url = path if path.startswith("http") else f"{BASE}{path}"
    hdrs = dict(HEADERS_BASE)
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    if headers_extra:
        hdrs.update(headers_extra)
    body = None
    if raw_data is not None:
        body = raw_data
    elif data is not None:
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
        raw = resp.read().decode()
        try:
            jdata = json.loads(raw)
        except Exception:
            jdata = raw
        return resp.status, jdata, dict(resp.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else ""
        try:
            jdata = json.loads(raw)
        except Exception:
            jdata = raw
        return e.code, jdata, {}
    except Exception as e:
        return 0, {"error": str(e)}, {}


def login(creds):
    """Login and return token."""
    for login_path in ["/auth/login", "/login", "/auth/sign-in", "/sessions"]:
        s, r, _ = api("POST", login_path, creds)
        if s in (200, 201):
            token = None
            if isinstance(r, dict):
                token = (r.get("token") or r.get("access_token")
                         or r.get("data", {}).get("token")
                         or r.get("data", {}).get("access_token")
                         or (r.get("data", {}).get("session", {}) or {}).get("access_token"))
            if token:
                print(f"  [LOGIN] OK via {login_path} -> token ...{token[-12:]}")
                return token
            # Handle nested structures like data.tokens.access_token
            if isinstance(r, dict):
                data = r.get("data", {})
                if isinstance(data, dict):
                    tokens = data.get("tokens", {})
                    if isinstance(tokens, dict):
                        t = tokens.get("access_token") or tokens.get("token") or tokens.get("accessToken")
                        if t:
                            print(f"  [LOGIN] OK via {login_path} data.tokens -> ...{t[-12:]}")
                            return t
                    # Also try data.accessToken
                    t = data.get("accessToken")
                    if t:
                        print(f"  [LOGIN] OK via {login_path} data.accessToken -> ...{t[-12:]}")
                        return t
            print(f"  [LOGIN] 200 at {login_path} but token not found. Response keys: {list(r.keys()) if isinstance(r, dict) else 'non-dict'}")
            if isinstance(r, dict) and "data" in r and isinstance(r["data"], dict):
                print(f"    data keys: {list(r['data'].keys())}")
                for k2, v2 in r["data"].items():
                    if isinstance(v2, dict):
                        print(f"    data.{k2} keys: {list(v2.keys())}")
            # Last resort: return any string that looks like a JWT
            if isinstance(r, dict):
                for k, v in r.items():
                    if isinstance(v, dict):
                        for k2, v2 in v.items():
                            if isinstance(v2, str) and len(v2) > 20 and "." in v2:
                                print(f"    Using {k}.{k2} as token")
                                return v2
                            if isinstance(v2, dict):
                                for k3, v3 in v2.items():
                                    if isinstance(v3, str) and len(v3) > 20 and "." in v3:
                                        print(f"    Using {k}.{k2}.{k3} as token")
                                        return v3
        else:
            print(f"  [LOGIN] {login_path} -> {s}")
    print("  [LOGIN] FAILED all paths")
    return None


def file_github_issue(title, body_text):
    """File a GitHub issue."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    hdrs = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "EmpCloudCRUDTester/1.0",
        "Content-Type": "application/json",
    }
    payload = {"title": title, "body": body_text, "labels": ["bug", "functional"]}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=hdrs, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=15)
        rd = json.loads(resp.read().decode())
        num = rd.get("number", "?")
        print(f"    >> GitHub issue #{num} filed: {title}")
        return num
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else ""
        print(f"    >> GitHub issue FAILED ({e.code}): {raw[:200]}")
        return None
    except Exception as ex:
        print(f"    >> GitHub issue FAILED: {ex}")
        return None


def record_bug(endpoint, method, url, request_body, response, description):
    """Record and file a functional bug."""
    bug = {
        "endpoint": endpoint,
        "method": method,
        "url": url,
        "request_body": str(request_body)[:500],
        "response": str(response)[:500],
        "description": description,
    }
    bugs.append(bug)
    body_md = f"""## [FUNCTIONAL] {description}

**Endpoint:** `{method} {url}`

**Request Body:**
```json
{str(request_body)[:800]}
```

**Response:**
```json
{str(response)[:800]}
```

**Steps to Reproduce:**
1. Authenticate as Org Admin (ananya@technova.in)
2. Send `{method}` to `{url}`
3. Observe the failure described above

**Expected:** CRUD operation should succeed.
**Actual:** {description}

_Filed by automated CRUD tester on {datetime.now().isoformat()}_
"""
    file_github_issue(f"[FUNCTIONAL] {description}", body_md)


def add_matrix(endpoint, create="—", read="—", update="—", delete="—", fields="", notes=""):
    crud_matrix.append({
        "endpoint": endpoint, "create": create, "read": read,
        "update": update, "delete": delete, "fields": fields, "notes": notes,
    })


def extract_id(resp, keys=("id", "_id", "data")):
    """Try to extract an ID from response."""
    if not isinstance(resp, dict):
        return None
    # Direct id
    for k in ("id", "_id"):
        if k in resp:
            return resp[k]
    # In data
    d = resp.get("data")
    if isinstance(d, dict):
        for k in ("id", "_id"):
            if k in d:
                return d[k]
    if isinstance(d, list) and len(d) > 0:
        return d[0].get("id") or d[0].get("_id")
    return None


def extract_list(resp):
    """Extract list of items."""
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        d = resp.get("data")
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            items = d.get("items") or d.get("results") or d.get("records") or d.get("rows")
            if isinstance(items, list):
                return items
            # Maybe data itself is a single item
            return [d] if d.get("id") else []
        # Try top-level
        for k in ("items", "results", "records", "rows"):
            if isinstance(resp.get(k), list):
                return resp[k]
    return []


def get_first_id(resp):
    """Get the first item's ID from a list response."""
    items = extract_list(resp)
    if items:
        return items[0].get("id") or items[0].get("_id")
    return None


def try_post(path, payloads, token, label=""):
    """Try POST with multiple payload variants. Return (status, resp, winning_payload)."""
    for i, pl in enumerate(payloads):
        s, r, _ = api("POST", path, pl, token)
        if s in (200, 201):
            print(f"    [CREATE] {label} OK (attempt {i+1}) -> {s}")
            return s, r, pl
        elif s in (400, 422):
            errs = ""
            if isinstance(r, dict):
                errs = r.get("errors") or r.get("message") or r.get("error") or r
            print(f"    [CREATE] {label} attempt {i+1} -> {s}: {str(errs)[:200]}")
        else:
            print(f"    [CREATE] {label} attempt {i+1} -> {s}: {str(r)[:200]}")
    return s, r, None


# ── UNIQUE SUFFIX for test data ──────────────────────────────────────────
TS = datetime.now().strftime("%m%d%H%M%S")
UNIQ = f"test{TS}"

# =========================================================================
# MAIN
# =========================================================================
print("=" * 70)
print("EMP Cloud HRMS — Complete API CRUD Coverage Test")
print(f"Timestamp: {datetime.now().isoformat()}")
print("=" * 70)

# ── Authenticate ─────────────────────────────────────────────────────────
print("\n[1] AUTHENTICATION")
admin_token = login(CREDS_ADMIN)
emp_token = login(CREDS_EMP)

if not admin_token:
    print("FATAL: Cannot authenticate admin. Aborting.")
    sys.exit(1)

T = admin_token  # shorthand

# Helper: test a full CRUD cycle for a generic endpoint
def test_crud_cycle(name, base_path, create_payloads, update_data,
                    id_in_path=True, delete=True, alt_paths=None):
    """
    Generic CRUD cycle tester.
    Returns dict with results for the matrix.
    """
    print(f"\n{'-'*60}")
    print(f"  [{name.upper()}]")
    result = {"endpoint": name, "create": "—", "read": "—",
              "update": "—", "delete": "—", "fields": "", "notes": ""}

    # READ (list)
    paths_to_try = [base_path]
    if alt_paths:
        paths_to_try.extend(alt_paths)
    read_ok = False
    read_resp = None
    working_path = base_path
    for p in paths_to_try:
        s, r, _ = api("GET", p, token=T)
        print(f"    [READ] GET {p} -> {s}")
        if s == 200:
            read_ok = True
            read_resp = r
            working_path = p
            result["read"] = "PASS"
            items = extract_list(r)
            print(f"    [READ] Got {len(items)} items")
            break
        elif s == 404:
            result["read"] = "404"
        else:
            result["read"] = f"FAIL({s})"

    if not read_ok:
        result["notes"] = f"GET returned {s}"
        if s not in (200,):
            record_bug(name, "GET", working_path, None, str(read_resp)[:300],
                       f"{name} GET {working_path} returns {s} instead of 200")

    # CREATE
    created_id = None
    if create_payloads:
        s, r, winning = try_post(working_path, create_payloads, T, name)
        if s in (200, 201):
            result["create"] = "PASS"
            created_id = extract_id(r)
            if winning:
                result["fields"] = ", ".join(winning.keys())
            print(f"    [CREATE] id={created_id}")
        elif s in (400, 422):
            result["create"] = f"VALIDATION({s})"
            if isinstance(r, dict):
                errs = r.get("errors") or r.get("message") or ""
                result["fields"] = f"Required: {str(errs)[:100]}"
        elif s == 404:
            result["create"] = "404"
            record_bug(name, "POST", working_path, create_payloads[0], str(r)[:300],
                       f"{name} POST returns 404 — endpoint may not exist")
        elif s == 405:
            result["create"] = "N/A(405)"
        else:
            result["create"] = f"FAIL({s})"
            record_bug(name, "POST", working_path, create_payloads[0] if create_payloads else {},
                       str(r)[:300], f"{name} POST returns unexpected {s}")

    # UPDATE
    target_id = created_id
    if not target_id and read_resp:
        target_id = get_first_id(read_resp)

    if target_id and update_data:
        if id_in_path:
            up_path = f"{working_path}/{target_id}"
        else:
            up_path = working_path
            update_data["id"] = target_id
        s, r, _ = api("PUT", up_path, update_data, T)
        print(f"    [UPDATE] PUT {up_path} -> {s}")
        if s in (200, 201, 204):
            result["update"] = "PASS"
            # Verify persistence
            if id_in_path:
                sv, rv, _ = api("GET", up_path, token=T)
                if sv == 200:
                    print(f"    [UPDATE] Verified by GET -> {sv}")
        elif s == 404:
            result["update"] = "404"
        elif s == 405:
            result["update"] = "N/A(405)"
        else:
            result["update"] = f"FAIL({s})"
    elif update_data:
        result["update"] = "SKIP(no id)"

    # DELETE
    if delete and created_id:
        del_path = f"{working_path}/{created_id}"
        s, r, _ = api("DELETE", del_path, token=T)
        print(f"    [DELETE] DELETE {del_path} -> {s}")
        if s in (200, 204):
            result["delete"] = "PASS"
            # Verify deletion
            sv, rv, _ = api("GET", del_path, token=T)
            if sv == 404:
                print(f"    [DELETE] Verified gone (404)")
            elif sv == 200:
                print(f"    [DELETE] WARNING: still returns 200 after delete")
                result["notes"] += " DELETE not effective"
        elif s == 404:
            result["delete"] = "404"
        elif s == 405:
            result["delete"] = "N/A(405)"
        else:
            result["delete"] = f"FAIL({s})"
    elif delete and not created_id:
        result["delete"] = "SKIP(no id)"

    add_matrix(**result)
    return result


# =========================================================================
# 1. USERS
# =========================================================================
print(f"\n{'='*60}")
print("  [USERS]")
user_result = {"endpoint": "Users", "create": "N/A", "read": "—",
               "update": "—", "delete": "N/A", "fields": "", "notes": ""}

# GET list
for p in ["/users", "/employees", "/members", "/people", "/user"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        user_result["read"] = "PASS"
        items = extract_list(r)
        print(f"  [READ] Got {len(items)} users")
        if items:
            uid = items[0].get("id") or items[0].get("_id")
            print(f"  [READ] First user id={uid}")
            # GET by id
            s2, r2, _ = api("GET", f"{p}/{uid}", token=T)
            print(f"  [READ by ID] GET {p}/{uid} -> {s2}")
            # PUT update
            s3, r3, _ = api("PUT", f"{p}/{uid}", {"contact_number": "9999900000"}, T)
            print(f"  [UPDATE] PUT {p}/{uid} contact_number -> {s3}")
            if s3 in (200, 201):
                user_result["update"] = "PASS"
                # Verify
                s4, r4, _ = api("GET", f"{p}/{uid}", token=T)
                if s4 == 200:
                    data = r4.get("data", r4) if isinstance(r4, dict) else r4
                    cn = data.get("contact_number", "?") if isinstance(data, dict) else "?"
                    print(f"  [VERIFY] contact_number={cn}")
                    if str(cn) == "9999900000":
                        print(f"  [VERIFY] Persisted OK")
                    else:
                        print(f"  [VERIFY] May not have persisted")
                        user_result["notes"] = "Update may not persist"
            elif s3 == 404:
                user_result["update"] = "404"
            else:
                user_result["update"] = f"FAIL({s3})"
                user_result["fields"] = str(r3)[:100] if isinstance(r3, dict) else ""
        break

add_matrix(**user_result)

# =========================================================================
# 2. DEPARTMENTS
# =========================================================================
test_crud_cycle(
    "Departments", "/departments",
    create_payloads=[
        {"name": f"TestDept_{UNIQ}", "description": "Auto-test department"},
        {"name": f"TestDept_{UNIQ}", "department_name": f"TestDept_{UNIQ}"},
        {"department_name": f"TestDept_{UNIQ}", "description": "Auto-test"},
    ],
    update_data={"name": f"TestDept_{UNIQ}_upd", "description": "Updated"},
)

# =========================================================================
# 3. LOCATIONS
# =========================================================================
test_crud_cycle(
    "Locations", "/locations",
    create_payloads=[
        {"name": f"TestLoc_{UNIQ}", "address": "123 Test St", "city": "Mumbai",
         "state": "Maharashtra", "country": "India", "zip_code": "400001"},
        {"location_name": f"TestLoc_{UNIQ}", "address": "123 Test St"},
        {"name": f"TestLoc_{UNIQ}"},
    ],
    update_data={"name": f"TestLoc_{UNIQ}_upd", "address": "456 Update Rd"},
)

# =========================================================================
# 4. DESIGNATIONS
# =========================================================================
test_crud_cycle(
    "Designations", "/designations",
    create_payloads=[
        {"name": f"TestDesig_{UNIQ}", "description": "Auto-test designation"},
        {"designation_name": f"TestDesig_{UNIQ}"},
        {"title": f"TestDesig_{UNIQ}"},
    ],
    update_data={"name": f"TestDesig_{UNIQ}_upd"},
    delete=False,
)

# =========================================================================
# 5. ATTENDANCE
# =========================================================================
print(f"\n{'-'*60}")
print("  [ATTENDANCE]")
att_result = {"endpoint": "Attendance", "create": "—", "read": "—",
              "update": "N/A", "delete": "N/A", "fields": "", "notes": ""}

for p in ["/attendance", "/attendance/logs", "/attendance/list"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        att_result["read"] = "PASS"
        break
else:
    att_result["read"] = f"FAIL({s})"

# Check-in
today = datetime.now().strftime("%Y-%m-%d")
for cin_path in ["/attendance/check-in", "/attendance/checkin", "/attendance/punch"]:
    for payload in [
        {"date": today, "time": datetime.now().strftime("%H:%M:%S")},
        {"check_in_time": datetime.now().isoformat()},
        {"timestamp": datetime.now().isoformat(), "type": "check_in"},
        {},
    ]:
        s, r, _ = api("POST", cin_path, payload, T)
        print(f"  [CHECK-IN] POST {cin_path} -> {s}: {str(r)[:150]}")
        if s in (200, 201):
            att_result["create"] = "PASS"
            att_result["fields"] = ", ".join(payload.keys()) if payload else "none"
            break
    if att_result["create"] == "PASS":
        break

# Check-out
for cout_path in ["/attendance/check-out", "/attendance/checkout"]:
    for payload in [
        {"date": today, "time": datetime.now().strftime("%H:%M:%S")},
        {"check_out_time": datetime.now().isoformat()},
        {},
    ]:
        s, r, _ = api("POST", cout_path, payload, T)
        print(f"  [CHECK-OUT] POST {cout_path} -> {s}: {str(r)[:150]}")
        if s in (200, 201):
            att_result["notes"] = "check-in/out OK"
            break

add_matrix(**att_result)

# =========================================================================
# 6. SHIFTS
# =========================================================================
test_crud_cycle(
    "Shifts", "/attendance/shifts",
    create_payloads=[
        {"name": f"Shift_{UNIQ}", "start_time": "09:00", "end_time": "18:00"},
        {"shift_name": f"Shift_{UNIQ}", "start_time": "09:00:00", "end_time": "18:00:00"},
        {"name": f"Shift_{UNIQ}", "from_time": "09:00", "to_time": "18:00"},
    ],
    update_data={"name": f"Shift_{UNIQ}_upd", "start_time": "10:00", "end_time": "19:00"},
    alt_paths=["/shifts"],
)

# =========================================================================
# 7. LEAVE BALANCES
# =========================================================================
print(f"\n{'-'*60}")
print("  [LEAVE BALANCES]")
lb_res = {"endpoint": "Leave Balances", "create": "N/A", "read": "—",
           "update": "N/A", "delete": "N/A", "fields": "", "notes": "Read-only"}
for p in ["/leave/balances", "/leave/balance", "/leaves/balances", "/leaves/balance"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        lb_res["read"] = "PASS"
        break
add_matrix(**lb_res)

# =========================================================================
# 8. LEAVE TYPES
# =========================================================================
test_crud_cycle(
    "Leave Types", "/leave/types",
    create_payloads=[
        {"name": f"LType_{UNIQ}", "description": "Test leave type", "days": 10,
         "is_paid": True, "is_carry_forward": False},
        {"leave_type_name": f"LType_{UNIQ}", "max_days": 10, "paid": True},
        {"name": f"LType_{UNIQ}", "allowed_days": 10},
        {"name": f"LType_{UNIQ}"},
    ],
    update_data={"name": f"LType_{UNIQ}_upd", "days": 15},
    alt_paths=["/leaves/types", "/leave-types"],
)

# =========================================================================
# 9. LEAVE APPLICATIONS
# =========================================================================
print(f"\n{'-'*60}")
print("  [LEAVE APPLICATIONS]")
la_res = {"endpoint": "Leave Applications", "create": "—", "read": "—",
           "update": "—", "delete": "N/A", "fields": "", "notes": ""}

# GET list
la_path = None
for p in ["/leave/applications", "/leave/requests", "/leaves", "/leave",
          "/leave/apply", "/leaves/applications"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        la_res["read"] = "PASS"
        la_path = p
        break

# Get leave types for application
leave_type_id = None
for ltp in ["/leave/types", "/leaves/types", "/leave-types"]:
    s, r, _ = api("GET", ltp, token=T)
    if s == 200:
        items = extract_list(r)
        if items:
            leave_type_id = items[0].get("id") or items[0].get("_id")
            print(f"  [INFO] leave_type_id={leave_type_id}")
        break

# POST apply
start_d = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
end_d = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d")
apply_paths = ["/leave/applications", "/leave/apply", "/leave/requests", "/leaves/apply"]
payloads = [
    {"leave_type_id": leave_type_id, "from_date": start_d, "to_date": end_d,
     "reason": "Auto-test leave", "half_day": False},
    {"leave_type_id": leave_type_id, "start_date": start_d, "end_date": end_d,
     "reason": "Auto-test leave"},
    {"leave_type": leave_type_id, "from": start_d, "to": end_d, "reason": "Test"},
    {"type_id": leave_type_id, "from_date": start_d, "to_date": end_d,
     "reason": "Test", "days": 2},
]
leave_app_id = None
for ap in apply_paths:
    for pl in payloads:
        s, r, _ = api("POST", ap, pl, T)
        print(f"  [CREATE] POST {ap} -> {s}: {str(r)[:200]}")
        if s in (200, 201):
            la_res["create"] = "PASS"
            la_res["fields"] = ", ".join(pl.keys())
            leave_app_id = extract_id(r)
            break
        elif s in (400, 422):
            errs = r.get("errors", r.get("message", "")) if isinstance(r, dict) else ""
            print(f"    Required fields hint: {str(errs)[:200]}")
    if la_res["create"] == "PASS":
        break

# Cancel
if leave_app_id:
    for cancel_pl in [{"status": "cancelled"}, {"action": "cancel"}, {"cancelled": True}]:
        cp = f"{la_path or '/leave/applications'}/{leave_app_id}"
        s, r, _ = api("PUT", cp, cancel_pl, T)
        print(f"  [CANCEL] PUT {cp} -> {s}")
        if s in (200, 204):
            la_res["update"] = "PASS"
            break
        else:
            la_res["update"] = f"FAIL({s})"

add_matrix(**la_res)

# =========================================================================
# 10. LEAVE POLICIES
# =========================================================================
test_crud_cycle(
    "Leave Policies", "/leave/policies",
    create_payloads=[
        {"name": f"LPol_{UNIQ}", "description": "Test policy", "leave_types": []},
        {"policy_name": f"LPol_{UNIQ}", "rules": []},
        {"name": f"LPol_{UNIQ}"},
    ],
    update_data={"name": f"LPol_{UNIQ}_upd"},
    delete=False,
    alt_paths=["/leaves/policies", "/leave-policies"],
)

# =========================================================================
# 11. COMP-OFF
# =========================================================================
print(f"\n{'-'*60}")
print("  [COMP-OFF]")
co_res = {"endpoint": "Comp-Off", "create": "—", "read": "—",
           "update": "N/A", "delete": "N/A", "fields": "", "notes": ""}
for p in ["/leave/comp-off", "/leave/compoff", "/comp-off", "/leaves/comp-off"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        co_res["read"] = "PASS"
        break

for p in ["/leave/comp-off", "/leave/compoff", "/comp-off"]:
    for pl in [
        {"date": today, "reason": "Worked on holiday", "hours": 8},
        {"worked_date": today, "reason": "Test comp-off"},
        {"date": today, "reason": "Test"},
    ]:
        s, r, _ = api("POST", p, pl, T)
        print(f"  [CREATE] POST {p} -> {s}: {str(r)[:150]}")
        if s in (200, 201):
            co_res["create"] = "PASS"
            co_res["fields"] = ", ".join(pl.keys())
            break
    if co_res["create"] == "PASS":
        break

add_matrix(**co_res)

# =========================================================================
# 12. DOCUMENTS
# =========================================================================
print(f"\n{'-'*60}")
print("  [DOCUMENTS]")
doc_res = {"endpoint": "Documents", "create": "—", "read": "—",
           "update": "N/A", "delete": "—", "fields": "", "notes": ""}
doc_path = None
for p in ["/documents", "/docs", "/files"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        doc_res["read"] = "PASS"
        doc_path = p
        break

# Try upload (multipart)
import io
boundary = f"----FormBoundary{UNIQ}"
file_content = "This is a test document for CRUD testing."
body_parts = []
body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"test_{UNIQ}.txt\"\r\nContent-Type: text/plain\r\n\r\n{file_content}\r\n")
body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"name\"\r\n\r\nTest Document {UNIQ}\r\n")
body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"category\"\r\n\r\nGeneral\r\n")
body_parts.append(f"--{boundary}--\r\n")
multipart_body = "".join(body_parts).encode()
doc_upload_paths = [doc_path or "/documents", "/documents/upload"]
for up in doc_upload_paths:
    s, r, _ = api("POST", up, raw_data=multipart_body, token=T,
                   headers_extra={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    print(f"  [UPLOAD] POST {up} -> {s}: {str(r)[:150]}")
    if s in (200, 201):
        doc_res["create"] = "PASS"
        doc_id = extract_id(r)
        if doc_id:
            sd, rd, _ = api("DELETE", f"{doc_path or '/documents'}/{doc_id}", token=T)
            print(f"  [DELETE] -> {sd}")
            doc_res["delete"] = "PASS" if sd in (200, 204) else f"FAIL({sd})"
        break

add_matrix(**doc_res)

# =========================================================================
# 13. DOCUMENT CATEGORIES
# =========================================================================
test_crud_cycle(
    "Document Categories", "/documents/categories",
    create_payloads=[
        {"name": f"DocCat_{UNIQ}", "description": "Test category"},
        {"category_name": f"DocCat_{UNIQ}"},
    ],
    update_data=None,
    delete=False,
    alt_paths=["/document-categories"],
)

# =========================================================================
# 14. ANNOUNCEMENTS
# =========================================================================
test_crud_cycle(
    "Announcements", "/announcements",
    create_payloads=[
        {"title": f"Ann_{UNIQ}", "description": "Test announcement body",
         "publish_date": today, "is_published": True},
        {"title": f"Ann_{UNIQ}", "content": "Test announcement", "date": today},
        {"title": f"Ann_{UNIQ}", "body": "Test announcement"},
        {"title": f"Ann_{UNIQ}", "message": "Test"},
    ],
    update_data={"title": f"Ann_{UNIQ}_upd", "description": "Updated announcement"},
)

# =========================================================================
# 15. EVENTS
# =========================================================================
evt_start = (datetime.now() + timedelta(days=10)).isoformat()
evt_end = (datetime.now() + timedelta(days=10, hours=2)).isoformat()
test_crud_cycle(
    "Events", "/events",
    create_payloads=[
        {"title": f"Evt_{UNIQ}", "description": "Test event",
         "start_date": evt_start, "end_date": evt_end, "location": "Online"},
        {"name": f"Evt_{UNIQ}", "start": evt_start, "end": evt_end},
        {"title": f"Evt_{UNIQ}", "date": evt_start},
    ],
    update_data={"title": f"Evt_{UNIQ}_upd", "description": "Updated event"},
)

# =========================================================================
# 16. SURVEYS
# =========================================================================
test_crud_cycle(
    "Surveys", "/surveys",
    create_payloads=[
        {"title": f"Surv_{UNIQ}", "description": "Test survey",
         "questions": [{"text": "How satisfied are you?", "type": "rating"}]},
        {"title": f"Surv_{UNIQ}", "description": "Test survey"},
        {"name": f"Surv_{UNIQ}", "description": "Test"},
    ],
    update_data={"title": f"Surv_{UNIQ}_upd", "status": "published"},
)

# =========================================================================
# 17. FEEDBACK
# =========================================================================
test_crud_cycle(
    "Feedback", "/feedback",
    create_payloads=[
        {"title": f"Fb_{UNIQ}", "description": "Test feedback", "type": "general",
         "rating": 4},
        {"subject": f"Fb_{UNIQ}", "message": "Test feedback"},
        {"title": f"Fb_{UNIQ}", "content": "Test"},
    ],
    update_data={"title": f"Fb_{UNIQ}_upd"},
    alt_paths=["/feedbacks"],
)

# =========================================================================
# 18. ASSETS
# =========================================================================
test_crud_cycle(
    "Assets", "/assets",
    create_payloads=[
        {"name": f"Asset_{UNIQ}", "asset_type": "Laptop", "serial_number": f"SN{UNIQ}",
         "status": "available", "description": "Test asset"},
        {"asset_name": f"Asset_{UNIQ}", "type": "Laptop", "serial": f"SN{UNIQ}"},
        {"name": f"Asset_{UNIQ}", "category": "Hardware"},
        {"name": f"Asset_{UNIQ}"},
    ],
    update_data={"name": f"Asset_{UNIQ}_upd", "status": "in_use"},
)

# =========================================================================
# 19. ASSET CATEGORIES
# =========================================================================
test_crud_cycle(
    "Asset Categories", "/assets/categories",
    create_payloads=[
        {"name": f"AstCat_{UNIQ}", "description": "Test asset category"},
        {"category_name": f"AstCat_{UNIQ}"},
    ],
    update_data=None,
    delete=False,
    alt_paths=["/asset-categories"],
)

# =========================================================================
# 20. POSITIONS
# =========================================================================
test_crud_cycle(
    "Positions", "/positions",
    create_payloads=[
        {"title": f"Pos_{UNIQ}", "department": "Engineering", "location": "Mumbai",
         "description": "Test position", "status": "open"},
        {"position_title": f"Pos_{UNIQ}", "department_id": 1},
        {"title": f"Pos_{UNIQ}"},
    ],
    update_data={"title": f"Pos_{UNIQ}_upd", "status": "closed"},
    alt_paths=["/jobs", "/recruitment/positions"],
)

# =========================================================================
# 21. VACANCIES
# =========================================================================
test_crud_cycle(
    "Vacancies", "/positions/vacancies",
    create_payloads=[
        {"title": f"Vac_{UNIQ}", "positions": 3, "department": "Engineering"},
        {"vacancy_title": f"Vac_{UNIQ}", "count": 3},
        {"title": f"Vac_{UNIQ}"},
    ],
    update_data=None,
    delete=False,
    alt_paths=["/vacancies", "/recruitment/vacancies"],
)

# =========================================================================
# 22. HELPDESK TICKETS
# =========================================================================
test_crud_cycle(
    "Helpdesk Tickets", "/helpdesk",
    create_payloads=[
        {"subject": f"Ticket_{UNIQ}", "description": "Test ticket", "priority": "medium",
         "category": "IT"},
        {"title": f"Ticket_{UNIQ}", "description": "Test", "priority": "medium"},
        {"subject": f"Ticket_{UNIQ}", "message": "Test ticket"},
        {"subject": f"Ticket_{UNIQ}"},
    ],
    update_data={"status": "in_progress"},
    alt_paths=["/helpdesk/tickets", "/tickets", "/support/tickets"],
)

# =========================================================================
# 23. KNOWLEDGE BASE
# =========================================================================
test_crud_cycle(
    "Knowledge Base", "/knowledge-base",
    create_payloads=[
        {"title": f"KB_{UNIQ}", "content": "Test knowledge base article",
         "category": "General"},
        {"title": f"KB_{UNIQ}", "body": "Test article"},
        {"title": f"KB_{UNIQ}"},
    ],
    update_data=None,
    delete=False,
    alt_paths=["/kb", "/knowledge"],
)

# =========================================================================
# 24-25. FORUM CATEGORIES + POSTS
# =========================================================================
# Forum categories first
print(f"\n{'-'*60}")
print("  [FORUM CATEGORIES]")
fc_res = {"endpoint": "Forum Categories", "create": "—", "read": "—",
           "update": "N/A", "delete": "N/A", "fields": "", "notes": ""}
forum_cat_id = None
for p in ["/forum/categories", "/forums/categories", "/forum-categories"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        fc_res["read"] = "PASS"
        items = extract_list(r)
        if items:
            forum_cat_id = items[0].get("id") or items[0].get("_id")
        for pl in [
            {"name": f"ForumCat_{UNIQ}", "description": "Test forum category"},
            {"category_name": f"ForumCat_{UNIQ}"},
        ]:
            sc, rc, _ = api("POST", p, pl, T)
            print(f"  [CREATE] POST {p} -> {sc}")
            if sc in (200, 201):
                fc_res["create"] = "PASS"
                fc_res["fields"] = ", ".join(pl.keys())
                cid = extract_id(rc)
                if cid:
                    forum_cat_id = cid
                break
        break
add_matrix(**fc_res)

# Forum posts
test_crud_cycle(
    "Forum Posts", "/forum/posts",
    create_payloads=[
        {"title": f"Post_{UNIQ}", "content": "Test forum post",
         "category_id": forum_cat_id},
        {"title": f"Post_{UNIQ}", "body": "Test post",
         "category_id": forum_cat_id},
        {"subject": f"Post_{UNIQ}", "content": "Test",
         "forum_category_id": forum_cat_id},
    ],
    update_data={"title": f"Post_{UNIQ}_upd", "content": "Updated post"},
    alt_paths=["/forum", "/forums", "/forum/threads"],
)

# =========================================================================
# 26. POLICIES
# =========================================================================
test_crud_cycle(
    "Policies", "/policies",
    create_payloads=[
        {"title": f"Pol_{UNIQ}", "description": "Test policy document",
         "content": "Policy content here", "category": "HR"},
        {"name": f"Pol_{UNIQ}", "description": "Test policy", "type": "company"},
        {"title": f"Pol_{UNIQ}", "body": "Policy text"},
        {"title": f"Pol_{UNIQ}"},
    ],
    update_data={"title": f"Pol_{UNIQ}_upd", "content": "Updated policy"},
    alt_paths=["/company-policies", "/hr-policies"],
)

# =========================================================================
# 27. WELLNESS
# =========================================================================
print(f"\n{'-'*60}")
print("  [WELLNESS]")
well_res = {"endpoint": "Wellness", "create": "—", "read": "—",
             "update": "N/A", "delete": "N/A", "fields": "", "notes": ""}
for p in ["/wellness", "/wellness/check-ins", "/wellness/logs"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        well_res["read"] = "PASS"
        break

for p in ["/wellness/check-in", "/wellness/checkin", "/wellness"]:
    for pl in [
        {"mood": "good", "notes": "Feeling great", "date": today, "score": 8},
        {"mood": 4, "date": today},
        {"wellness_score": 8, "date": today},
    ]:
        s, r, _ = api("POST", p, pl, T)
        print(f"  [CHECK-IN] POST {p} -> {s}: {str(r)[:150]}")
        if s in (200, 201):
            well_res["create"] = "PASS"
            well_res["fields"] = ", ".join(pl.keys())
            break
    if well_res["create"] == "PASS":
        break
add_matrix(**well_res)

# =========================================================================
# 28. WELLNESS PROGRAMS
# =========================================================================
test_crud_cycle(
    "Wellness Programs", "/wellness/programs",
    create_payloads=[
        {"name": f"WProg_{UNIQ}", "description": "Test wellness program",
         "start_date": today, "end_date": end_d},
        {"title": f"WProg_{UNIQ}", "description": "Test"},
    ],
    update_data=None,
    delete=False,
    alt_paths=["/wellness-programs"],
)

# =========================================================================
# 29. WHISTLEBLOWING
# =========================================================================
print(f"\n{'-'*60}")
print("  [WHISTLEBLOWING]")
wb_res = {"endpoint": "Whistleblowing", "create": "—", "read": "—",
           "update": "N/A", "delete": "N/A", "fields": "", "notes": ""}

wb_id = None
for p in ["/whistleblowing", "/whistleblower", "/reports/whistleblowing"]:
    for pl in [
        {"subject": f"WB_{UNIQ}", "description": "Test report", "anonymous": True,
         "category": "misconduct"},
        {"title": f"WB_{UNIQ}", "message": "Test report", "is_anonymous": True},
        {"subject": f"WB_{UNIQ}", "details": "Test"},
    ]:
        s, r, _ = api("POST", p, pl, T)
        print(f"  [CREATE] POST {p} -> {s}: {str(r)[:150]}")
        if s in (200, 201):
            wb_res["create"] = "PASS"
            wb_res["fields"] = ", ".join(pl.keys())
            wb_id = extract_id(r)
            break
    if wb_res["create"] == "PASS":
        break

for p in ["/whistleblowing", "/whistleblower", "/reports/whistleblowing"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        wb_res["read"] = "PASS"
        break
add_matrix(**wb_res)

# =========================================================================
# 30. NOTIFICATIONS
# =========================================================================
print(f"\n{'-'*60}")
print("  [NOTIFICATIONS]")
notif_res = {"endpoint": "Notifications", "create": "N/A", "read": "—",
              "update": "—", "delete": "N/A", "fields": "", "notes": ""}
notif_id = None
for p in ["/notifications", "/notification"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        notif_res["read"] = "PASS"
        items = extract_list(r)
        if items:
            notif_id = items[0].get("id") or items[0].get("_id")
        break

if notif_id:
    for p in [f"/notifications/{notif_id}", f"/notifications/{notif_id}/read",
              "/notifications/mark-read", "/notifications/read"]:
        for pl in [{"read": True}, {"is_read": True}, {"ids": [notif_id]}]:
            m = "PUT" if "/read" not in p or p.endswith(f"/{notif_id}") else "POST"
            s, r, _ = api(m, p, pl, T)
            print(f"  [MARK READ] {m} {p} -> {s}")
            if s in (200, 204):
                notif_res["update"] = "PASS"
                break
        if notif_res["update"] == "PASS":
            break
add_matrix(**notif_res)

# =========================================================================
# 31. AUDIT
# =========================================================================
print(f"\n{'-'*60}")
print("  [AUDIT]")
audit_res = {"endpoint": "Audit", "create": "N/A", "read": "—",
              "update": "N/A", "delete": "N/A", "fields": "", "notes": "Read-only"}
for p in ["/audit", "/audit-logs", "/audit/logs", "/audits"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        audit_res["read"] = "PASS"
        break
add_matrix(**audit_res)

# =========================================================================
# 32. MODULES
# =========================================================================
print(f"\n{'-'*60}")
print("  [MODULES]")
mod_res = {"endpoint": "Modules", "create": "N/A", "read": "—",
            "update": "N/A", "delete": "N/A", "fields": "", "notes": "Read-only"}
for p in ["/modules", "/module", "/features"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        mod_res["read"] = "PASS"
        break
add_matrix(**mod_res)

# =========================================================================
# 33. SUBSCRIPTIONS
# =========================================================================
test_crud_cycle(
    "Subscriptions", "/subscriptions",
    create_payloads=[
        {"plan": "basic", "module": "attendance"},
        {"subscription_type": "premium"},
        {"plan_id": 1},
    ],
    update_data=None,
    delete=True,
    alt_paths=["/subscription", "/plans"],
)

# =========================================================================
# 34. CUSTOM FIELDS
# =========================================================================
test_crud_cycle(
    "Custom Fields", "/custom-fields",
    create_payloads=[
        {"name": f"CF_{UNIQ}", "field_type": "text", "entity": "employee",
         "label": f"Custom Field {UNIQ}", "required": False},
        {"field_name": f"CF_{UNIQ}", "type": "string", "module": "users"},
        {"name": f"CF_{UNIQ}", "type": "text"},
    ],
    update_data={"name": f"CF_{UNIQ}_upd", "label": "Updated field"},
    alt_paths=["/custom_fields", "/customfields"],
)

# =========================================================================
# 35. HOLIDAYS
# =========================================================================
hol_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
test_crud_cycle(
    "Holidays", "/holidays",
    create_payloads=[
        {"name": f"Hol_{UNIQ}", "date": hol_date, "description": "Test holiday",
         "type": "public"},
        {"holiday_name": f"Hol_{UNIQ}", "date": hol_date, "is_optional": False},
        {"name": f"Hol_{UNIQ}", "date": hol_date},
    ],
    update_data={"name": f"Hol_{UNIQ}_upd", "description": "Updated holiday"},
)

# =========================================================================
# 36. INVITATIONS
# =========================================================================
print(f"\n{'-'*60}")
print("  [INVITATIONS]")
inv_res = {"endpoint": "Invitations", "create": "—", "read": "—",
            "update": "N/A", "delete": "N/A", "fields": "", "notes": ""}
for p in ["/invitations", "/invites", "/invitation"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        inv_res["read"] = "PASS"
        break

for p in ["/invitations", "/invites", "/invitation", "/invitations/invite"]:
    for pl in [
        {"email": f"testinvite_{UNIQ}@example.com", "role": "employee",
         "name": f"TestUser {UNIQ}"},
        {"email": f"testinvite_{UNIQ}@example.com", "role_id": 2},
        {"email": f"testinvite_{UNIQ}@example.com"},
    ]:
        s, r, _ = api("POST", p, pl, T)
        print(f"  [CREATE] POST {p} -> {s}: {str(r)[:150]}")
        if s in (200, 201):
            inv_res["create"] = "PASS"
            inv_res["fields"] = ", ".join(pl.keys())
            break
    if inv_res["create"] == "PASS":
        break
add_matrix(**inv_res)

# =========================================================================
# 37. ORG CHART
# =========================================================================
print(f"\n{'-'*60}")
print("  [ORG CHART]")
oc_res = {"endpoint": "Org Chart", "create": "N/A", "read": "—",
           "update": "N/A", "delete": "N/A", "fields": "", "notes": "Read-only"}
for p in ["/org-chart", "/orgchart", "/organization-chart", "/org/chart"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        oc_res["read"] = "PASS"
        break
add_matrix(**oc_res)

# =========================================================================
# 38. DASHBOARD
# =========================================================================
print(f"\n{'-'*60}")
print("  [DASHBOARD]")
dash_res = {"endpoint": "Dashboard", "create": "N/A", "read": "—",
             "update": "N/A", "delete": "N/A", "fields": "", "notes": "Read-only"}
for p in ["/dashboard", "/dashboard/stats", "/dashboard/summary", "/home"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        dash_res["read"] = "PASS"
        break
add_matrix(**dash_res)

# =========================================================================
# 39. REPORTS
# =========================================================================
print(f"\n{'-'*60}")
print("  [REPORTS]")
rep_res = {"endpoint": "Reports", "create": "—", "read": "—",
            "update": "N/A", "delete": "N/A", "fields": "", "notes": ""}
for p in ["/reports", "/report", "/analytics"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        rep_res["read"] = "PASS"
        break

for p in ["/reports", "/reports/generate", "/report/generate"]:
    for pl in [
        {"type": "attendance", "from_date": today, "to_date": today,
         "format": "json"},
        {"report_type": "attendance", "date_range": {"start": today, "end": today}},
        {"name": "attendance_report"},
    ]:
        s, r, _ = api("POST", p, pl, T)
        print(f"  [GENERATE] POST {p} -> {s}: {str(r)[:150]}")
        if s in (200, 201):
            rep_res["create"] = "PASS"
            rep_res["fields"] = ", ".join(pl.keys())
            break
    if rep_res["create"] == "PASS":
        break
add_matrix(**rep_res)

# =========================================================================
# 40. SETTINGS
# =========================================================================
print(f"\n{'-'*60}")
print("  [SETTINGS]")
set_res = {"endpoint": "Settings", "create": "N/A", "read": "—",
            "update": "—", "delete": "N/A", "fields": "", "notes": ""}
settings_path = None
for p in ["/settings", "/config", "/preferences", "/organization/settings"]:
    s, r, _ = api("GET", p, token=T)
    print(f"  [READ] GET {p} -> {s}")
    if s == 200:
        set_res["read"] = "PASS"
        settings_path = p
        break

if settings_path:
    for pl in [
        {"timezone": "Asia/Kolkata"},
        {"company_name": "TechNova"},
        {"notification_email": True},
    ]:
        s, r, _ = api("PUT", settings_path, pl, T)
        print(f"  [UPDATE] PUT {settings_path} -> {s}")
        if s in (200, 204):
            set_res["update"] = "PASS"
            break
add_matrix(**set_res)


# =========================================================================
# SUMMARY — CRUD MATRIX
# =========================================================================
print("\n\n" + "=" * 100)
print("COMPLETE CRUD MATRIX")
print("=" * 100)

header = f"| {'Endpoint':<25} | {'CREATE':<16} | {'READ':<12} | {'UPDATE':<12} | {'DELETE':<12} | {'Required Fields':<30} | {'Notes':<30} |"
sep = f"|{'-'*27}|{'-'*18}|{'-'*14}|{'-'*14}|{'-'*14}|{'-'*32}|{'-'*32}|"
print(header)
print(sep)

pass_c = fail_c = skip_c = 0
for row in crud_matrix:
    line = f"| {row['endpoint']:<25} | {row['create']:<16} | {row['read']:<12} | {row['update']:<12} | {row['delete']:<12} | {row['fields'][:30]:<30} | {row['notes'][:30]:<30} |"
    print(line)
    for op in ['create', 'read', 'update', 'delete']:
        v = row[op]
        if v.startswith("PASS"):
            pass_c += 1
        elif v in ("N/A", "—", "") or v.startswith("SKIP") or v.startswith("N/A"):
            skip_c += 1
        else:
            fail_c += 1

print(sep)
total = pass_c + fail_c
print(f"\n  PASS: {pass_c}   FAIL/ISSUE: {fail_c}   SKIPPED/N/A: {skip_c}   TOTAL TESTED: {total}")
print(f"  Coverage rate: {pass_c}/{total} = {pass_c*100//max(total,1)}%")

print(f"\n  Bugs filed to GitHub: {len(bugs)}")
for b in bugs:
    print(f"    - {b['description']}")

print(f"\n{'='*100}")
print("Test run complete.")
print(f"{'='*100}")
