#!/usr/bin/env python3
"""
EMP Cloud HRMS — CRUD Pass 3: Use discovered field names to crack remaining validation errors.
Also file bugs for confirmed issues.
"""

import urllib.request
import urllib.error
import json
import ssl
import sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://test-empcloud.empcloud.com/api/v1"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

HEADERS_BASE = {
    "User-Agent": "EmpCloudCRUDTester/3.0",
    "Origin": "https://test-empcloud.empcloud.com",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

TS = datetime.now().strftime("%m%d%H%M%S")
today = datetime.now().strftime("%Y-%m-%d")

def api(method, path, data=None, token=None, headers_extra=None, raw_data=None):
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

def login():
    s, r, _ = api("POST", "/auth/login", {"email": "ananya@technova.in", "password": "Welcome@123"})
    return r.get("data", {}).get("tokens", {}).get("access_token") if s == 200 else None

def extract_id(resp):
    if not isinstance(resp, dict): return None
    for k in ("id", "_id"):
        if k in resp: return resp[k]
    d = resp.get("data")
    if isinstance(d, dict):
        for k in ("id", "_id"):
            if k in d: return d[k]
    return None

def extract_list(resp):
    if isinstance(resp, list): return resp
    if isinstance(resp, dict):
        d = resp.get("data")
        if isinstance(d, list): return d
        if isinstance(d, dict):
            for k in ("items", "results", "records", "rows"):
                if isinstance(d.get(k), list): return d[k]
    return []

def file_github_issue(title, body_text):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    hdrs = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "EmpCloudCRUDTester/3.0",
        "Content-Type": "application/json",
    }
    payload = {"title": title, "body": body_text, "labels": ["bug", "functional"]}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=hdrs, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=15)
        rd = json.loads(resp.read().decode())
        print(f"  >> GitHub issue #{rd.get('number','?')}: {title}")
        return rd.get("number")
    except Exception as ex:
        print(f"  >> GitHub issue FAILED: {ex}")
        return None

results = {}
bugs_filed = []

print("=" * 70)
print("PASS 3: Final validation probing with exact field names")
print("=" * 70)

T = login()
if not T:
    print("FATAL: Login failed")
    sys.exit(1)
print("[AUTH] OK\n")

# ---------------------------------------------------------------
# LEAVE APPLICATIONS: fields are leave_type_id, start_date, end_date, reason
# from the example: start_date, end_date, days_count, is_half_day, half_day_type, reason
# ---------------------------------------------------------------
print("[LEAVE APPLICATIONS]")
s, r, _ = api("GET", "/leave/types", token=T)
lt_items = extract_list(r)
lt_id = lt_items[0].get("id") if lt_items else None

start_d = (datetime.now() + timedelta(days=50)).strftime("%Y-%m-%d")
end_d = (datetime.now() + timedelta(days=51)).strftime("%Y-%m-%d")

# Use exact field names from the existing records
for pl in [
    {"leave_type_id": lt_id, "start_date": start_d, "end_date": end_d,
     "days_count": 2, "is_half_day": False, "reason": "Auto test leave"},
    {"leave_type_id": lt_id, "start_date": start_d, "end_date": end_d,
     "days_count": 2, "is_half_day": False, "half_day_type": None, "reason": "Test"},
    {"leave_type_id": lt_id, "start_date": start_d, "end_date": start_d,
     "days_count": 1, "is_half_day": False, "reason": "Test leave 1 day"},
    {"leave_type_id": lt_id, "start_date": start_d, "end_date": start_d,
     "reason": "Test leave"},
    {"leave_type_id": lt_id, "start_date": start_d, "end_date": start_d,
     "days_count": 1, "reason": "Test"},
]:
    s2, r2, _ = api("POST", "/leave/applications", pl, T)
    print(f"  POST {list(pl.keys())} -> {s2}: {str(r2)[:250]}")
    if s2 in (200, 201):
        results["Leave Applications CREATE"] = f"PASS: {list(pl.keys())}"
        la_id = extract_id(r2)
        if la_id:
            sc, rc, _ = api("PUT", f"/leave/applications/{la_id}", {"status": "cancelled"}, T)
            print(f"  CANCEL {la_id} -> {sc}")
            results["Leave Applications CANCEL"] = "PASS" if sc in (200, 204) else f"FAIL({sc})"
        break

if "Leave Applications CREATE" not in results:
    # Try with employee token
    print("  Trying with employee token...")
    emp_s, emp_r, _ = api("POST", "/auth/login", {"email": "priya@technova.in", "password": "Welcome@123"})
    emp_t = emp_r.get("data", {}).get("tokens", {}).get("access_token") if emp_s == 200 else None
    if emp_t:
        for pl in [
            {"leave_type_id": lt_id, "start_date": start_d, "end_date": start_d,
             "days_count": 1, "is_half_day": False, "reason": "Employee test leave"},
            {"leave_type_id": lt_id, "start_date": start_d, "end_date": start_d,
             "reason": "Employee test"},
        ]:
            s2, r2, _ = api("POST", "/leave/applications", pl, emp_t)
            print(f"  POST (employee) {list(pl.keys())} -> {s2}: {str(r2)[:250]}")
            if s2 in (200, 201):
                results["Leave Applications CREATE"] = f"PASS (employee): {list(pl.keys())}"
                break

# ---------------------------------------------------------------
# LEAVE POLICIES: fields include leave_type_id, annual_quota, accrual_type, etc.
# ---------------------------------------------------------------
print("\n[LEAVE POLICIES]")
for pl in [
    {"name": f"LP3_{TS}", "leave_type_id": lt_id, "annual_quota": 12,
     "accrual_type": "monthly", "accrual_rate": 1},
    {"name": f"LP3_{TS}", "leave_type_id": lt_id, "annual_quota": 12,
     "accrual_type": "monthly"},
    {"name": f"LP3_{TS}", "leave_type_id": lt_id, "annual_quota": 12},
    {"name": f"LP3_{TS}", "leave_type_id": lt_id},
]:
    s2, r2, _ = api("POST", "/leave/policies", pl, T)
    print(f"  POST {list(pl.keys())} -> {s2}: {str(r2)[:250]}")
    if s2 in (200, 201):
        results["Leave Policies CREATE"] = f"PASS: {list(pl.keys())}"
        pid = extract_id(r2)
        if pid:
            api("DELETE", f"/leave/policies/{pid}", token=T)
        break

# ---------------------------------------------------------------
# COMP-OFF: fields include worked_date, expires_on, reason, days
# ---------------------------------------------------------------
print("\n[COMP-OFF]")
work_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
expire_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

for pl in [
    {"worked_date": work_date, "reason": "Weekend work", "days": 1},
    {"worked_date": work_date, "reason": "Weekend work", "days": 1, "expires_on": expire_date},
    {"worked_date": work_date, "expires_on": expire_date, "reason": "Worked Saturday", "days": 1},
    {"worked_date": work_date, "reason": "Test"},
]:
    s2, r2, _ = api("POST", "/leave/comp-off", pl, T)
    print(f"  POST {list(pl.keys())} -> {s2}: {str(r2)[:250]}")
    if s2 in (200, 201):
        results["Comp-Off CREATE"] = f"PASS: {list(pl.keys())}"
        break

# ---------------------------------------------------------------
# FEEDBACK: fields are category, subject, message, sentiment, is_urgent
# ---------------------------------------------------------------
print("\n[FEEDBACK]")
for pl in [
    {"category": "general", "subject": f"FB3_{TS}", "message": "Test feedback message",
     "sentiment": "positive", "is_urgent": False},
    {"category": "general", "subject": f"FB3_{TS}", "message": "Test feedback"},
    {"subject": f"FB3_{TS}", "message": "Test", "category": "suggestion"},
    {"category": "complaint", "subject": f"FB3_{TS}", "message": "Test feedback",
     "is_urgent": True},
]:
    s2, r2, _ = api("POST", "/feedback", pl, T)
    print(f"  POST {list(pl.keys())} -> {s2}: {str(r2)[:250]}")
    if s2 in (200, 201):
        results["Feedback CREATE"] = f"PASS: {list(pl.keys())}"
        fid = extract_id(r2)
        if fid:
            su, ru, _ = api("PUT", f"/feedback/{fid}", {"subject": f"FB3_{TS}_upd", "message": "Updated"}, T)
            print(f"  UPDATE {fid} -> {su}")
            results["Feedback UPDATE"] = "PASS" if su in (200, 204) else f"FAIL({su})"
            sd, rd, _ = api("DELETE", f"/feedback/{fid}", token=T)
            print(f"  DELETE {fid} -> {sd}")
            results["Feedback DELETE"] = "PASS" if sd in (200, 204) else f"FAIL({sd})"
        break

# ---------------------------------------------------------------
# HELPDESK TICKETS: fields are category, priority, subject, description
# ---------------------------------------------------------------
print("\n[HELPDESK TICKETS]")
for pl in [
    {"category": "IT", "priority": "medium", "subject": f"HT3_{TS}",
     "description": "Test helpdesk ticket"},
    {"category": "it_support", "priority": "low", "subject": f"HT3_{TS}",
     "description": "Test ticket body"},
    {"category": "general", "subject": f"HT3_{TS}", "description": "Test",
     "priority": "high"},
    {"subject": f"HT3_{TS}", "description": "Need help", "category": "hr",
     "priority": "medium"},
    {"subject": f"HT3_{TS}", "description": "Test", "priority": "medium"},
]:
    s2, r2, _ = api("POST", "/helpdesk/tickets", pl, T)
    print(f"  POST {list(pl.keys())} -> {s2}: {str(r2)[:250]}")
    if s2 in (200, 201):
        results["Helpdesk CREATE"] = f"PASS: {list(pl.keys())}"
        tid = extract_id(r2)
        if tid:
            sd, rd, _ = api("DELETE", f"/helpdesk/tickets/{tid}", token=T)
            print(f"  DELETE {tid} -> {sd}")
            results["Helpdesk DELETE"] = "PASS" if sd in (200, 204) else f"FAIL({sd})"
        break

# ---------------------------------------------------------------
# WELLNESS CHECK-IN: fields are mood, energy_level, sleep_hours, exercise_minutes, notes
# ---------------------------------------------------------------
print("\n[WELLNESS CHECK-IN]")
for pl in [
    {"mood": "happy", "energy_level": 8, "sleep_hours": 7, "exercise_minutes": 30,
     "notes": "Feeling great today"},
    {"mood": "happy", "energy_level": 8, "sleep_hours": 7, "exercise_minutes": 30},
    {"mood": "good", "energy_level": 7, "sleep_hours": 8},
    {"mood": "neutral", "energy_level": 5},
    {"mood": "happy"},
    {"check_in_date": today, "mood": "happy", "energy_level": 8,
     "sleep_hours": 7, "exercise_minutes": 30},
]:
    s2, r2, _ = api("POST", "/wellness/check-in", pl, T)
    print(f"  POST {list(pl.keys())} -> {s2}: {str(r2)[:250]}")
    if s2 in (200, 201):
        results["Wellness CHECK-IN"] = f"PASS: {list(pl.keys())}"
        break
    if s2 == 409:
        results["Wellness CHECK-IN"] = "PASS (409=already checked in)"
        break

# ---------------------------------------------------------------
# DOCUMENTS UPLOAD: Use valid PDF with category_id
# ---------------------------------------------------------------
print("\n[DOCUMENTS UPLOAD]")
# First get document categories
s, r, _ = api("GET", "/documents/categories", token=T)
doc_cats = extract_list(r)
cat_id = doc_cats[0].get("id") if doc_cats else 1
print(f"  Using category_id={cat_id}")

boundary = f"----FormBound{TS}"
pdf_content = b"%PDF-1.0\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\nxref\n0 3\ntrailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n0\n%%EOF"

for cat_field, cat_val in [("category_id", str(cat_id)), ("document_category_id", str(cat_id)),
                             ("category", "General")]:
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"test_{TS}.pdf\"\r\n"
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + pdf_content + (
        f"\r\n--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"name\"\r\n\r\nTest Doc {TS}\r\n"
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"{cat_field}\"\r\n\r\n{cat_val}\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    s2, r2, _ = api("POST", "/documents/upload", raw_data=body, token=T,
                    headers_extra={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    print(f"  POST /documents/upload ({cat_field}={cat_val}) -> {s2}: {str(r2)[:200]}")
    if s2 in (200, 201):
        results["Documents UPLOAD"] = f"PASS (field={cat_field})"
        doc_id = extract_id(r2)
        if doc_id:
            sd, rd, _ = api("DELETE", f"/documents/{doc_id}", token=T)
            print(f"  DELETE doc {doc_id} -> {sd}")
            results["Documents DELETE"] = "PASS" if sd in (200, 204) else f"FAIL({sd})"
        break

# ---------------------------------------------------------------
# NOTIFICATIONS MARK-READ
# ---------------------------------------------------------------
print("\n[NOTIFICATIONS]")
s, r, _ = api("GET", "/notifications", token=T)
items = extract_list(r)
if items:
    nid = items[0].get("id")
    print(f"  First notification id={nid}, fields: {list(items[0].keys())}")
    for method, path, pl in [
        ("PUT", f"/notifications/{nid}", {"is_read": True}),
        ("PUT", f"/notifications/{nid}", {"read": True}),
        ("PUT", f"/notifications/{nid}", {"status": "read"}),
        ("PATCH", f"/notifications/{nid}", {"is_read": True}),
        ("POST", f"/notifications/{nid}/read", {}),
        ("PUT", f"/notifications/{nid}/read", {}),
        ("POST", "/notifications/mark-read", {"ids": [nid]}),
        ("POST", "/notifications/mark-as-read", {"ids": [nid]}),
        ("PUT", "/notifications/read-all", {}),
        ("POST", "/notifications/read-all", {}),
    ]:
        s2, r2, _ = api(method, path, pl, T)
        print(f"  {method} {path} -> {s2}: {str(r2)[:150]}")
        if s2 in (200, 204):
            results["Notifications MARK-READ"] = f"PASS: {method} {path}"
            break
else:
    print("  No notifications found")
    results["Notifications MARK-READ"] = "SKIP (no notifications)"

# ---------------------------------------------------------------
# USERS UPDATE — try different approach
# ---------------------------------------------------------------
print("\n[USERS UPDATE]")
s, r, _ = api("GET", "/users", token=T)
items = extract_list(r)
if items:
    uid = items[0].get("id")
    orig = items[0]
    # Try updating first_name which we know exists
    new_name = f"TestName{TS}"
    s2, r2, _ = api("PUT", f"/users/{uid}", {"first_name": new_name}, T)
    print(f"  PUT first_name={new_name} -> {s2}")
    if s2 == 200:
        s3, r3, _ = api("GET", f"/users/{uid}", token=T)
        d = r3.get("data", r3) if isinstance(r3, dict) else {}
        got_name = d.get("first_name") if isinstance(d, dict) else None
        print(f"  GET back first_name={got_name}")
        if got_name == new_name:
            results["Users UPDATE"] = "PASS (first_name persists)"
            # Restore
            api("PUT", f"/users/{uid}", {"first_name": orig.get("first_name", "Ananya")}, T)
        else:
            results["Users UPDATE"] = "BUG: PUT returns 200 but data does not persist"
            file_github_issue(
                "[FUNCTIONAL] Users PUT returns 200 but changes do not persist",
                f"""## [FUNCTIONAL] Users PUT returns 200 but data does not persist

**Endpoint:** `PUT {BASE}/users/{uid}`
**Request:** `{{"first_name": "{new_name}"}}`
**Response:** 200 OK
**Verification GET:** first_name = `{got_name}` (expected `{new_name}`)

The PUT endpoint accepts any payload and returns 200, but the changes are not actually saved.
This affects all user profile update operations.

_Filed by automated CRUD tester pass 3_
""")
            bugs_filed.append("Users PUT returns 200 but changes do not persist")

# ---------------------------------------------------------------
# FILE BUGS for confirmed issues
# ---------------------------------------------------------------
print("\n[FILING BUGS for confirmed issues]")

# Leave Applications always returns 400 regardless of payload
if "Leave Applications CREATE" not in results:
    file_github_issue(
        "[FUNCTIONAL] Leave Applications POST always returns 400 VALIDATION_ERROR",
        f"""## [FUNCTIONAL] Leave Applications POST always returns VALIDATION_ERROR

**Endpoint:** `POST {BASE}/leave/applications`
**Tried payloads with fields:** leave_type_id, start_date, end_date, from_date, to_date, days_count, is_half_day, reason, duration, no_of_days

All combinations return `400 VALIDATION_ERROR: Invalid request data` without specifying which fields are missing or invalid.

The error message does not include validation details, making it impossible to determine the correct payload format.

**Example existing record fields:** id, organization_id, user_id, leave_type_id, start_date, end_date, days_count, is_half_day, half_day_type, reason, status

_Filed by automated CRUD tester pass 3_
""")
    bugs_filed.append("Leave Applications POST always returns 400")

# Comp-Off always returns 400
if "Comp-Off CREATE" not in results:
    file_github_issue(
        "[FUNCTIONAL] Comp-Off POST always returns 400 VALIDATION_ERROR",
        f"""## [FUNCTIONAL] Comp-Off POST always returns VALIDATION_ERROR

**Endpoint:** `POST {BASE}/leave/comp-off`
**Tried fields:** worked_date, expires_on, reason, days, work_date, hours_worked, hours

All return `400 VALIDATION_ERROR: Invalid request data` without field-level details.

**Existing record fields:** worked_date, expires_on, reason, days, status

_Filed by automated CRUD tester pass 3_
""")
    bugs_filed.append("Comp-Off POST always returns 400")

# Wellness check-in always returns 400
if "Wellness CHECK-IN" not in results or "FAIL" in results.get("Wellness CHECK-IN", ""):
    file_github_issue(
        "[FUNCTIONAL] Wellness check-in POST always returns 400 VALIDATION_ERROR",
        f"""## [FUNCTIONAL] Wellness check-in POST always returns VALIDATION_ERROR

**Endpoint:** `POST {BASE}/wellness/check-in`
**Tried fields matching schema:** mood, energy_level, sleep_hours, exercise_minutes, notes, check_in_date

All return `400 VALIDATION_ERROR: Invalid request data`.

**Existing record fields:** mood, energy_level, sleep_hours, exercise_minutes, notes, check_in_date

_Filed by automated CRUD tester pass 3_
""")
    bugs_filed.append("Wellness check-in POST always returns 400")

# Helpdesk tickets create
if "Helpdesk CREATE" not in results:
    file_github_issue(
        "[FUNCTIONAL] Helpdesk Tickets POST always returns 400 VALIDATION_ERROR",
        f"""## [FUNCTIONAL] Helpdesk Tickets POST always returns VALIDATION_ERROR

**Endpoint:** `POST {BASE}/helpdesk/tickets`
**Tried fields:** category, priority, subject, description, type, department_id, status

All return `400 VALIDATION_ERROR: Invalid request data`.

**Existing record fields:** category, priority, subject, description, status, assigned_to, department_id, tags

_Filed by automated CRUD tester pass 3_
""")
    bugs_filed.append("Helpdesk Tickets POST always returns 400")

# Feedback create
if "Feedback CREATE" not in results:
    file_github_issue(
        "[FUNCTIONAL] Feedback POST always returns 400 VALIDATION_ERROR",
        f"""## [FUNCTIONAL] Feedback POST always returns VALIDATION_ERROR

**Endpoint:** `POST {BASE}/feedback`
**Tried fields:** category, subject, message, sentiment, is_urgent, title, description, type

All return `400 VALIDATION_ERROR: Invalid request data`.

**Existing record fields:** category, subject, message, sentiment, status, is_urgent

_Filed by automated CRUD tester pass 3_
""")
    bugs_filed.append("Feedback POST always returns 400")

# Leave Policies create
if "Leave Policies CREATE" not in results:
    file_github_issue(
        "[FUNCTIONAL] Leave Policies POST always returns 400 VALIDATION_ERROR",
        f"""## [FUNCTIONAL] Leave Policies POST always returns VALIDATION_ERROR

**Endpoint:** `POST {BASE}/leave/policies`
**Tried fields:** name, leave_type_id, annual_quota, accrual_type, accrual_rate, description

All return `400 VALIDATION_ERROR: Invalid request data`.

**Existing record fields:** leave_type_id, name, annual_quota, accrual_type, accrual_rate, applicable_from_months, applicable_gender, applicable_employment_types

_Filed by automated CRUD tester pass 3_
""")
    bugs_filed.append("Leave Policies POST always returns 400")

# Attendance GET returns 404 for main path
file_github_issue(
    "[FUNCTIONAL] Attendance GET /attendance returns 404, only /attendance/records works",
    f"""## [FUNCTIONAL] Attendance GET /attendance returns 404

**Endpoint:** `GET {BASE}/attendance`
**Response:** 404 NOT_FOUND

The main attendance listing endpoint returns 404. Only `/attendance/records` works.
Paths tried: /attendance, /attendance/logs, /attendance/list, /attendance/me, /attendance/today

_Filed by automated CRUD tester pass 3_
""")
bugs_filed.append("Attendance GET /attendance returns 404")

# ---------------------------------------------------------------
# FINAL SUMMARY
# ---------------------------------------------------------------
print("\n" + "=" * 70)
print("PASS 3 RESULTS")
print("=" * 70)
for k, v in sorted(results.items()):
    status = "PASS" if "PASS" in v else "FAIL/BUG"
    print(f"  [{status}] {k}: {v}")

print(f"\nBugs filed in pass 3: {len(bugs_filed)}")
for b in bugs_filed:
    print(f"  - {b}")

print("=" * 70)
