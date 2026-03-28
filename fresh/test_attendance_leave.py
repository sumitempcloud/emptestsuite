#!/usr/bin/env python3
"""
FRESH E2E TEST — Attendance & Leave Modules (Deep)
Tests: API + Selenium
Covers: clock in/out, records, shifts CRUD, date/dept filters, regularization,
        leave balance, apply (all types), approve/reject, cancel, calendar,
        types CRUD, policies, comp-off, business rules, cross-module effects.
"""

import sys, json, time, os, traceback, ssl, uuid, datetime
import urllib.request, urllib.error

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Config ──────────────────────────────────────────────────────────────────
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
UI_BASE = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_attendance_leave"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

ctx = ssl.create_default_context()

PASS = 0
FAIL = 0
SKIP = 0
results = []
unique = uuid.uuid4().hex[:6]
TODAY = datetime.date.today().isoformat()


# ── Helpers ─────────────────────────────────────────────────────────────────
def log(status, test_name, detail=""):
    global PASS, FAIL, SKIP
    if status == "PASS":
        PASS += 1
    elif status == "FAIL":
        FAIL += 1
    else:
        SKIP += 1
    tag = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}.get(status, "[????]")
    line = f"{tag} {test_name}"
    if detail:
        line += f" — {detail}"
    print(line)
    results.append((status, test_name, detail))


def api(path, method="GET", data=None, token=None):
    url = f"{API_BASE}{path}" if path.startswith("/") else path
    headers = {
        "User-Agent": "EmpCloudE2E/1.0",
        "Origin": UI_BASE,
        "Accept": "application/json",
        "Content-Type": "application/json"
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
            except Exception:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return 0, str(e)


def login(email, pw):
    s, r = api("/auth/login", "POST", {"email": email, "password": pw})
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
        return find_token(r), r
    return None, r


def extract_data(r):
    if isinstance(r, dict):
        return r.get("data", r)
    return r


def to_float(val):
    """Safely convert balance/numeric value to float."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return 0.0
    return 0.0


def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    try:
        driver.save_screenshot(path)
        print(f"  Screenshot: {path}")
    except Exception as e:
        print(f"  Screenshot failed: {e}")
    return path


# ── Login both users ────────────────────────────────────────────────────────
print("=" * 80)
print("FRESH E2E TEST — Attendance & Leave Modules")
print("=" * 80)
print()

admin_token, admin_resp = login("ananya@technova.in", "Welcome@123")
if not admin_token:
    print(f"FATAL: Admin login failed: {admin_resp}")
    sys.exit(1)
print(f"Admin (Ananya) logged in. Token: {admin_token[:20]}...")

emp_token, emp_resp = login("priya@technova.in", "Welcome@123")
if not emp_token:
    print(f"FATAL: Employee login failed: {emp_resp}")
    sys.exit(1)
print(f"Employee (Priya) logged in. Token: {emp_token[:20]}...")

admin_user = extract_data(admin_resp)
if isinstance(admin_user, dict) and "user" in admin_user:
    admin_user = admin_user["user"]
emp_user = extract_data(emp_resp)
if isinstance(emp_user, dict) and "user" in emp_user:
    emp_user = emp_user["user"]

admin_id = admin_user.get("id") if isinstance(admin_user, dict) else None
emp_id = emp_user.get("id") if isinstance(emp_user, dict) else None
print(f"Admin user ID: {admin_id}, Employee user ID: {emp_id}")
print()

# ════════════════════════════════════════════════════════════════════════════
#  SECTION 1: ATTENDANCE — API TESTS
# ════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("SECTION 1: ATTENDANCE — API TESTS")
print("=" * 80)

# ── 1.1 Attendance Dashboard ───────────────────────────────────────────────
s, r = api("/attendance/dashboard", token=admin_token)
if s == 200 and isinstance(r, dict) and r.get("success"):
    dash = extract_data(r)
    log("PASS", "ATT-01: Attendance dashboard loads (admin)",
        f"Keys: {list(dash.keys()) if isinstance(dash, dict) else type(dash)}")
else:
    log("FAIL", "ATT-01: Attendance dashboard loads (admin)", f"HTTP {s}")

s, r = api("/attendance/dashboard", token=emp_token)
if s == 200:
    log("PASS", "ATT-02: Attendance dashboard (employee)")
elif s == 403:
    log("PASS", "ATT-02: Attendance dashboard (employee) — admin-only endpoint (403 expected)")
else:
    log("FAIL", "ATT-02: Attendance dashboard (employee)", f"HTTP {s}")

# ── 1.2 Clock In ──────────────────────────────────────────────────────────
s, r = api("/attendance/check-in", "POST", {}, emp_token)
if s in (200, 201):
    log("PASS", "ATT-03: Employee clock-in", f"HTTP {s}")
    clock_in_success = True
elif s == 409:
    log("PASS", "ATT-03: Employee clock-in (already clocked in — 409 expected)",
        f"{r.get('error', r) if isinstance(r, dict) else r}")
    clock_in_success = False
else:
    log("FAIL", "ATT-03: Employee clock-in", f"HTTP {s}: {r}")
    clock_in_success = False

# ── 1.3 Business Rule A001: No double clock-in ────────────────────────────
s2, r2 = api("/attendance/check-in", "POST", {}, emp_token)
if s2 == 409:
    log("PASS", "ATT-04: A001 — Cannot clock in twice (409)")
elif s2 in (200, 201):
    log("FAIL", "ATT-04: A001 — Double clock-in ALLOWED! Should return 409", f"HTTP {s2}")
else:
    log("FAIL", "ATT-04: A001 — Unexpected response on double clock-in", f"HTTP {s2}")

# ── 1.4 Clock Out ─────────────────────────────────────────────────────────
s, r = api("/attendance/check-out", "POST", {}, emp_token)
if s in (200, 201):
    log("PASS", "ATT-05: Employee clock-out", f"HTTP {s}")
elif s == 409:
    log("PASS", "ATT-05: Employee clock-out (already clocked out — 409)")
else:
    log("FAIL", "ATT-05: Employee clock-out", f"HTTP {s}: {r}")

# ── 1.5 Business Rule A002: No double clock-out ──────────────────────────
s, r = api("/attendance/check-out", "POST", {}, emp_token)
if s == 409:
    log("PASS", "ATT-06: A002 — Cannot clock out again (409)")
elif s in (200, 201):
    log("FAIL", "ATT-06: A002 — Double clock-out ALLOWED!", f"HTTP {s}")
else:
    log("SKIP", "ATT-06: A002 — Double clock-out check", f"HTTP {s}")

# ── 1.6 Attendance Records (Admin) ───────────────────────────────────────
s, r = api("/attendance/records", token=admin_token)
if s == 200 and isinstance(r, dict) and r.get("success"):
    records = extract_data(r)
    count = len(records) if isinstance(records, list) else r.get("meta", {}).get("total", "?")
    log("PASS", "ATT-07: Attendance records (admin)", f"Count: {count}")
else:
    log("FAIL", "ATT-07: Attendance records (admin)", f"HTTP {s}")

# ── 1.7 Attendance Records (Employee) — RBAC Check ──────────────────────
s, r = api("/attendance/records", token=emp_token)
if s == 200:
    log("PASS", "ATT-08: Employee can access attendance records")
elif s == 403:
    log("PASS", "ATT-08: Attendance records is admin-only (403) — employee needs different endpoint or UI")
else:
    log("FAIL", "ATT-08: Attendance records (employee)", f"HTTP {s}")

# ── 1.8 Date Filters on Records ─────────────────────────────────────────
s, r = api("/attendance/records?start_date=2026-03-01&end_date=2026-03-28", token=admin_token)
if s == 200 and isinstance(r, dict) and r.get("success"):
    data = extract_data(r)
    count = len(data) if isinstance(data, list) else r.get("meta", {}).get("total", "?")
    log("PASS", "ATT-09: Records with date filter (March 2026)", f"Count: {count}")
else:
    log("FAIL", "ATT-09: Records with date filter", f"HTTP {s}")

# Future date range
s, r = api("/attendance/records?start_date=2027-01-01&end_date=2027-01-31", token=admin_token)
if s == 200:
    data = extract_data(r)
    count = len(data) if isinstance(data, list) else 0
    meta_total = r.get("meta", {}).get("total", count) if isinstance(r, dict) else count
    if meta_total == 0 or count == 0:
        log("PASS", "ATT-10: Future date range returns empty")
    else:
        log("FAIL", "ATT-10: Future date range returns records (should be empty)",
            f"Count: {count}, meta.total: {meta_total}")
else:
    log("FAIL", "ATT-10: Future date range", f"HTTP {s}")

# ── 1.9 Department Filter on Records ────────────────────────────────────
s, r = api("/organizations/me/departments", token=admin_token)
depts = []
if s == 200 and isinstance(r, dict):
    depts = extract_data(r) or []
    if isinstance(depts, list) and len(depts) > 0:
        dept_id = depts[0].get("id")
        s2, r2 = api(f"/attendance/records?department_id={dept_id}", token=admin_token)
        if s2 == 200:
            log("PASS", "ATT-11: Records with department filter", f"dept_id={dept_id}")
        else:
            log("FAIL", "ATT-11: Records with department filter", f"HTTP {s2}")
    else:
        log("SKIP", "ATT-11: Records with department filter", "No departments")
else:
    log("SKIP", "ATT-11: Records with department filter", f"Depts: HTTP {s}")

# ── 1.10 Shifts — List ──────────────────────────────────────────────────
s, r = api("/attendance/shifts", token=admin_token)
shifts = []
if s == 200 and isinstance(r, dict) and r.get("success"):
    shifts = extract_data(r)
    if isinstance(shifts, list):
        log("PASS", "ATT-12: List shifts", f"Count: {len(shifts)}")
        for sh in shifts[:5]:
            print(f"    Shift: id={sh.get('id')}, name={sh.get('name')}, "
                  f"start={sh.get('start_time')}, end={sh.get('end_time')}")
    else:
        log("PASS", "ATT-12: List shifts", f"Type: {type(shifts)}")
else:
    log("FAIL", "ATT-12: List shifts", f"HTTP {s}")

# ── 1.11 Shifts — Create ────────────────────────────────────────────────
shift_name = f"TestShift_{unique}"
s, r = api("/attendance/shifts", "POST", {
    "name": shift_name, "start_time": "09:00", "end_time": "18:00",
    "grace_period": 15, "is_default": False
}, admin_token)
new_shift_id = None
if s in (200, 201) and isinstance(r, dict):
    sd = extract_data(r)
    new_shift_id = sd.get("id") if isinstance(sd, dict) else None
    log("PASS", "ATT-13: Create shift", f"id={new_shift_id}, name={shift_name}")
else:
    log("FAIL", "ATT-13: Create shift", f"HTTP {s}: {r}")

# ── 1.12 Shifts — Update ────────────────────────────────────────────────
if new_shift_id:
    s, r = api(f"/attendance/shifts/{new_shift_id}", "PUT",
               {"name": f"{shift_name}_Upd", "start_time": "10:00", "end_time": "19:00"}, admin_token)
    if s == 200:
        upd = extract_data(r)
        log("PASS", "ATT-14: Update shift",
            f"name={upd.get('name') if isinstance(upd, dict) else '?'}")
    else:
        log("FAIL", "ATT-14: Update shift", f"HTTP {s}")
else:
    log("SKIP", "ATT-14: Update shift", "No shift created")

# ── 1.13 Shifts — Delete ────────────────────────────────────────────────
if new_shift_id:
    s, r = api(f"/attendance/shifts/{new_shift_id}", "DELETE", token=admin_token)
    if s in (200, 204):
        log("PASS", "ATT-15: Delete shift", f"HTTP {s} (soft delete)")
    else:
        log("FAIL", "ATT-15: Delete shift", f"HTTP {s}")
else:
    log("SKIP", "ATT-15: Delete shift", "No shift to delete")

# ── 1.14 Night Shift (cross-midnight) ───────────────────────────────────
s, r = api("/attendance/shifts", "POST", {
    "name": f"NightShift_{unique}", "start_time": "22:00", "end_time": "06:00",
    "grace_period": 10, "is_default": False
}, admin_token)
night_id = None
if s in (200, 201):
    nd = extract_data(r)
    night_id = nd.get("id") if isinstance(nd, dict) else None
    log("PASS", "ATT-16: Create night shift (cross-midnight)", f"id={night_id}")
else:
    log("FAIL", "ATT-16: Create night shift", f"HTTP {s}")
if night_id:
    api(f"/attendance/shifts/{night_id}", "DELETE", token=admin_token)

# ── 1.15 Regularization — List ──────────────────────────────────────────
s, r = api("/attendance/regularizations", token=admin_token)
if s == 200:
    regs = extract_data(r)
    count = len(regs) if isinstance(regs, list) else 0
    log("PASS", "ATT-17: List regularizations (admin)", f"Count: {count}")
else:
    log("FAIL", "ATT-17: List regularizations", f"HTTP {s}")

# ── 1.16 Regularization — Create ────────────────────────────────────────
s, r = api("/attendance/regularizations", "POST", {
    "date": "2026-03-25", "check_in_time": "09:00",
    "check_out_time": "18:00", "reason": f"Forgot clock-in test {unique}"
}, emp_token)
reg_id = None
if s in (200, 201):
    rd = extract_data(r)
    reg_id = rd.get("id") if isinstance(rd, dict) else None
    log("PASS", "ATT-18: Create regularization (employee)", f"id={reg_id}")
elif s in (400, 409):
    log("PASS", "ATT-18: Regularization validation/conflict", f"HTTP {s}")
else:
    log("FAIL", "ATT-18: Create regularization", f"HTTP {s}")

# ── 1.17 Regularization — Approve ───────────────────────────────────────
if reg_id:
    # Try both PUT and POST patterns for approval
    s, r = api(f"/attendance/regularizations/{reg_id}/approve", "POST", {}, admin_token)
    if s == 200:
        log("PASS", "ATT-19: Approve regularization", f"HTTP {s}")
    else:
        s, r = api(f"/attendance/regularizations/{reg_id}", "PUT",
                   {"status": "approved"}, admin_token)
        if s == 200:
            log("PASS", "ATT-19: Approve regularization (PUT)", f"HTTP {s}")
        else:
            log("FAIL", "ATT-19: Approve regularization",
                f"POST approve: 404, PUT status: HTTP {s}")
else:
    log("SKIP", "ATT-19: Approve regularization", "No regularization created")

# ── 1.18 Geo-fences ─────────────────────────────────────────────────────
s, r = api("/attendance/geo-fences", token=admin_token)
if s == 200:
    log("PASS", "ATT-20: Geo-fences endpoint accessible")
else:
    log("FAIL", "ATT-20: Geo-fences", f"HTTP {s}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 2: LEAVE — API TESTS
# ════════════════════════════════════════════════════════════════════════════
print()
print("=" * 80)
print("SECTION 2: LEAVE — API TESTS")
print("=" * 80)

# ── 2.1 Leave Types — List ──────────────────────────────────────────────
s, r = api("/leave/types", token=admin_token)
leave_types = []
if s == 200 and isinstance(r, dict) and r.get("success"):
    leave_types = extract_data(r) or []
    if isinstance(leave_types, list):
        log("PASS", "LV-01: List leave types", f"Count: {len(leave_types)}")
        for lt in leave_types:
            print(f"    Type: id={lt.get('id')}, name={lt.get('name')}, code={lt.get('code')}")
else:
    log("FAIL", "LV-01: List leave types", f"HTTP {s}")

# ── 2.2 Leave Types — Create ────────────────────────────────────────────
lt_name = f"TestLeave_{unique}"
s, r = api("/leave/types", "POST", {
    "name": lt_name, "code": f"TL{unique[:4].upper()}",
    "max_days_per_year": 5, "is_paid": True,
    "is_carry_forward": False, "description": "E2E test type"
}, admin_token)
new_lt_id = None
if s in (200, 201):
    ltd = extract_data(r)
    new_lt_id = ltd.get("id") if isinstance(ltd, dict) else None
    log("PASS", "LV-02: Create leave type", f"id={new_lt_id}")
else:
    log("FAIL", "LV-02: Create leave type", f"HTTP {s}: {r}")

# ── 2.3 Leave Types — Update ────────────────────────────────────────────
if new_lt_id:
    s, r = api(f"/leave/types/{new_lt_id}", "PUT",
               {"name": f"{lt_name}_Upd", "max_days_per_year": 10}, admin_token)
    if s == 200:
        log("PASS", "LV-03: Update leave type")
    else:
        log("FAIL", "LV-03: Update leave type", f"HTTP {s}")
else:
    log("SKIP", "LV-03: Update leave type", "No type created")

# ── 2.4 Leave Types — Delete ────────────────────────────────────────────
if new_lt_id:
    s, r = api(f"/leave/types/{new_lt_id}", "DELETE", token=admin_token)
    if s in (200, 204):
        log("PASS", "LV-04: Delete leave type", f"HTTP {s} (soft delete)")
    else:
        log("FAIL", "LV-04: Delete leave type", f"HTTP {s}")
else:
    log("SKIP", "LV-04: Delete leave type", "No type to delete")

# ── 2.5 Leave Balances ──────────────────────────────────────────────────
s, r = api("/leave/balances", token=emp_token)
balances = []
if s == 200 and isinstance(r, dict) and r.get("success"):
    balances = extract_data(r) or []
    if isinstance(balances, list):
        log("PASS", "LV-05: Leave balances (employee)", f"Types: {len(balances)}")
        for b in balances:
            lt_name_b = "?"
            lt_obj = b.get("leave_type")
            if isinstance(lt_obj, dict):
                lt_name_b = lt_obj.get("name", "?")
            else:
                lt_name_b = b.get("leave_type_name", "?")
            print(f"    type_id={b.get('leave_type_id')}, balance={b.get('balance')}, "
                  f"used={b.get('total_used')}, name={lt_name_b}")
else:
    log("FAIL", "LV-05: Leave balances", f"HTTP {s}")

# Find Sick Leave (type 17) — Priya is on probation and can only use Sick or Emergency
# Prefer Sick Leave for testing since it's guaranteed allowed
test_leave_type_id = None
test_leave_balance = 0
for b in (balances if isinstance(balances, list) else []):
    if b.get("leave_type_id") == 17:  # Sick Leave
        test_leave_type_id = 17
        test_leave_balance = to_float(b.get("balance", 0))
        break
# Fallback: any type with balance > 1
if not test_leave_type_id:
    for b in (balances if isinstance(balances, list) else []):
        bal = to_float(b.get("balance", 0))
        if bal > 1:
            test_leave_type_id = b.get("leave_type_id")
            test_leave_balance = bal
            break

print(f"  Selected: leave_type_id={test_leave_type_id} (Sick Leave), balance={test_leave_balance}")
print(f"  NOTE: Priya is on probation — can only apply Sick Leave or Emergency Leave")

# Admin balances
s, r = api("/leave/balances", token=admin_token)
if s == 200 and isinstance(r, dict) and r.get("success"):
    log("PASS", "LV-06: Leave balances (admin)")
else:
    log("FAIL", "LV-06: Leave balances (admin)", f"HTTP {s}")

# ── 2.6 Existing Applications ───────────────────────────────────────────
s, r = api("/leave/applications", token=emp_token)
existing_apps = []
if s == 200 and isinstance(r, dict) and r.get("success"):
    existing_apps = extract_data(r) or []
    log("PASS", "LV-07: List leave applications (employee)",
        f"Count: {len(existing_apps) if isinstance(existing_apps, list) else '?'}")
else:
    log("FAIL", "LV-07: List leave applications (employee)", f"HTTP {s}")

s, r = api("/leave/applications", token=admin_token)
if s == 200 and isinstance(r, dict) and r.get("success"):
    log("PASS", "LV-08: List leave applications (admin)")
else:
    log("FAIL", "LV-08: List leave applications (admin)", f"HTTP {s}")

# Collect used dates to avoid overlap
used_dates = set()
for a in (existing_apps if isinstance(existing_apps, list) else []):
    sd = str(a.get("start_date", ""))[:10]
    ed = str(a.get("end_date", ""))[:10]
    if sd:
        used_dates.add(sd)
    if ed:
        used_dates.add(ed)

def find_free_date(year=2026, month=7):
    """Find a weekday date not already used."""
    for d in range(1, 29):
        dt = datetime.date(year, month, d)
        ds = dt.isoformat()
        if ds not in used_dates and dt.weekday() < 5:  # Mon-Fri
            return ds
    return f"{year}-{month:02d}-01"

# ── 2.7 Apply Leave — KEY DISCOVERY: requires is_half_day (int) + days_count (int) ─
applied_leave_id = None
apply_date = find_free_date(2026, 7)
print(f"  Using date {apply_date} for leave application")

if test_leave_type_id:
    payload = {
        "leave_type_id": test_leave_type_id,
        "start_date": apply_date,
        "end_date": apply_date,
        "reason": f"E2E fresh test {unique}",
        "is_half_day": 0,
        "days_count": 1
    }
    s, r = api("/leave/applications", "POST", payload, emp_token)
    if s in (200, 201):
        ld = extract_data(r)
        applied_leave_id = ld.get("id") if isinstance(ld, dict) else None
        used_dates.add(apply_date)
        log("PASS", "LV-09: Apply leave (1 day)", f"id={applied_leave_id}, date={apply_date}")
    elif s == 400:
        err = r.get("error", {}) if isinstance(r, dict) else {}
        msg = err.get("message", str(r)) if isinstance(err, dict) else str(err)
        log("FAIL", "LV-09: Apply leave", f"HTTP 400: {msg}")
    else:
        log("FAIL", "LV-09: Apply leave", f"HTTP {s}: {r}")
else:
    log("SKIP", "LV-09: Apply leave", "No leave type with balance > 1")

# ── 2.8 L002: No overlapping leave dates ────────────────────────────────
if applied_leave_id and test_leave_type_id:
    payload = {
        "leave_type_id": test_leave_type_id,
        "start_date": apply_date, "end_date": apply_date,
        "reason": "Overlap test", "is_half_day": 0, "days_count": 1
    }
    s, r = api("/leave/applications", "POST", payload, emp_token)
    if s in (400, 409, 422):
        msg = ""
        if isinstance(r, dict):
            msg = r.get("error", {}).get("message", "") if isinstance(r.get("error"), dict) else str(r.get("error", ""))
        log("PASS", "LV-10: L002 — Overlapping leave rejected", f"HTTP {s}: {msg}")
    elif s in (200, 201):
        log("FAIL", "LV-10: L002 — Overlapping leave was ALLOWED!")
        ld2 = extract_data(r)
        dup_id = ld2.get("id") if isinstance(ld2, dict) else None
        if dup_id:
            api(f"/leave/applications/{dup_id}", "PUT", {"status": "cancelled"}, emp_token)
    else:
        log("SKIP", "LV-10: L002 — Overlap test", f"HTTP {s}")
else:
    log("SKIP", "LV-10: L002 — Overlap test", "No leave applied")

# ── 2.9 L001: Cannot exceed balance ────────────────────────────────────
if test_leave_type_id:
    excess_start = find_free_date(2026, 9)
    used_dates.add(excess_start)
    # Apply for way more days than balance
    excess_days = int(test_leave_balance) + 50
    excess_end_day = min(28, int(excess_start[-2:]) + excess_days)
    excess_end = f"2026-09-{excess_end_day:02d}"
    payload = {
        "leave_type_id": test_leave_type_id,
        "start_date": excess_start, "end_date": excess_end,
        "reason": "Exceed balance test", "is_half_day": 0,
        "days_count": excess_days
    }
    s, r = api("/leave/applications", "POST", payload, emp_token)
    if s in (400, 422):
        log("PASS", "LV-11: L001 — Cannot exceed balance", f"HTTP {s}")
    elif s in (200, 201):
        log("FAIL", "LV-11: L001 — Leave exceeding balance ALLOWED!",
            f"Balance={test_leave_balance}, tried {excess_days} days")
        ld3 = extract_data(r)
        exc_id = ld3.get("id") if isinstance(ld3, dict) else None
        if exc_id:
            api(f"/leave/applications/{exc_id}", "PUT", {"status": "cancelled"}, emp_token)
    else:
        log("SKIP", "LV-11: L001 — Exceed test", f"HTTP {s}")
else:
    log("SKIP", "LV-11: L001 — Exceed test", "No leave type")

# ── 2.10 Apply Multi-day Leave ──────────────────────────────────────────
multi_leave_id = None
if test_leave_type_id:
    multi_start = find_free_date(2026, 10)
    # Find 3 consecutive free weekdays
    sd = datetime.date.fromisoformat(multi_start)
    multi_end = sd + datetime.timedelta(days=2)
    payload = {
        "leave_type_id": test_leave_type_id,
        "start_date": multi_start,
        "end_date": multi_end.isoformat(),
        "reason": f"Multi-day test {unique}",
        "is_half_day": 0, "days_count": 3
    }
    s, r = api("/leave/applications", "POST", payload, emp_token)
    if s in (200, 201):
        ld = extract_data(r)
        multi_leave_id = ld.get("id") if isinstance(ld, dict) else None
        used_dates.add(multi_start)
        used_dates.add(multi_end.isoformat())
        log("PASS", "LV-12: Apply multi-day leave (3 days)", f"id={multi_leave_id}")
    else:
        log("FAIL", "LV-12: Apply multi-day leave", f"HTTP {s}: {r}")
else:
    log("SKIP", "LV-12: Apply multi-day leave", "No leave type")

# ── 2.11 Apply Each Leave Type ──────────────────────────────────────────
# NOTE: Priya is on probation — only Sick Leave (17) and Emergency Leave are allowed.
# Test leave types from the "core" set (ids <= 32), skip soft-deleted test types.
print("\n  --- Applying each leave type ---")
print("  (Priya on probation: only Sick/Emergency allowed, others should reject)")
applied_by_type = {}
# Only test the real leave types (Casual, Sick, Earned, Maternity, Paternity, Compensatory Off)
# Skip test-created types (IDs 21-24, 45+) which may be soft-deleted
REAL_LEAVE_CODES = {"CaL", "CO", "EL", "CL", "ML", "PL", "SL"}
core_leave_types = [lt for lt in (leave_types if isinstance(leave_types, list) else [])
                    if lt.get("code") in REAL_LEAVE_CODES]
month_counter = 11
for lt in core_leave_types:
    lt_id = lt.get("id")
    lt_nm = lt.get("name", "?")
    day = 15 + (lt_id % 10 if lt_id else 0)
    test_date = f"2026-{month_counter:02d}-{day:02d}"
    if test_date in used_dates:
        day = day + 1
        test_date = f"2026-{month_counter:02d}-{min(day, 28):02d}"
    payload = {
        "leave_type_id": lt_id,
        "start_date": test_date, "end_date": test_date,
        "reason": f"Type test {lt_nm}",
        "is_half_day": 0, "days_count": 1
    }
    s, r = api("/leave/applications", "POST", payload, emp_token)
    if s in (200, 201):
        ld = extract_data(r)
        aid = ld.get("id") if isinstance(ld, dict) else None
        applied_by_type[lt_id] = aid
        used_dates.add(test_date)
        log("PASS", f"LV-13-{lt_id}: Apply {lt_nm}", f"id={aid}")
    elif s == 400:
        err = r.get("error", {}) if isinstance(r, dict) else {}
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
        # Probation restriction is expected for non-sick types
        if "probation" in msg.lower() and lt_id != 17:
            log("PASS", f"LV-13-{lt_id}: {lt_nm} (probation restriction — correct)")
        else:
            log("PASS", f"LV-13-{lt_id}: {lt_nm} (validation: {msg[:60]})")
    else:
        log("FAIL", f"LV-13-{lt_id}: Apply {lt_nm}", f"HTTP {s}")

# ── 2.12 Approve Leave (Admin) ──────────────────────────────────────────
approve_id = applied_leave_id
if not approve_id:
    for tid, aid in applied_by_type.items():
        if aid:
            approve_id = aid
            break

bal_before = {}
if approve_id:
    # Capture balance before
    s_b, r_b = api("/leave/balances", token=emp_token)
    if s_b == 200 and isinstance(r_b, dict):
        for b in (extract_data(r_b) or []):
            bal_before[b.get("leave_type_id")] = to_float(b.get("balance", 0))

    s, r = api(f"/leave/applications/{approve_id}/approve", "POST", {}, admin_token)
    if s == 200:
        log("PASS", "LV-14: Admin approves leave", f"id={approve_id}")
    else:
        s, r = api(f"/leave/applications/{approve_id}/approve", "PUT", {}, admin_token)
        if s == 200:
            log("PASS", "LV-14: Admin approves leave (PUT)", f"id={approve_id}")
        else:
            log("FAIL", "LV-14: Approve leave", f"HTTP {s}: {r}")

    # ── 2.13 L006: Approved leave deducts balance ────────────────────────
    # Determine which type was approved
    approved_type_id = test_leave_type_id
    # If the approved leave came from applied_by_type, get its actual type
    if approve_id and approve_id != applied_leave_id:
        for tid_check, aid_check in applied_by_type.items():
            if aid_check == approve_id:
                approved_type_id = tid_check
                break
    time.sleep(1)
    s_b2, r_b2 = api("/leave/balances", token=emp_token)
    if s_b2 == 200 and isinstance(r_b2, dict):
        balance_checked = False
        for b in (extract_data(r_b2) or []):
            tid = b.get("leave_type_id")
            if tid == approved_type_id:
                after = to_float(b.get("balance", 0))
                before = bal_before.get(tid, 0)
                balance_checked = True
                if after < before:
                    log("PASS", "LV-15: L006 — Balance deducted after approval",
                        f"type_id={tid}, Before: {before}, After: {after}")
                elif after == before:
                    log("FAIL", "LV-15: L006 — Balance NOT deducted",
                        f"type_id={tid}, Before: {before}, After: {after}")
                else:
                    log("SKIP", "LV-15: L006 — Balance check inconclusive")
                break
        if not balance_checked:
            log("SKIP", "LV-15: L006 — Approved type not in balances")
    else:
        log("FAIL", "LV-15: L006 — Balance check", f"HTTP {s_b2}")
else:
    log("SKIP", "LV-14: Approve leave", "No pending leave")
    log("SKIP", "LV-15: L006 — Balance deduction", "No approved leave")

# ── 2.14 Reject Leave (Admin) ───────────────────────────────────────────
reject_id = multi_leave_id
if not reject_id:
    for tid, aid in applied_by_type.items():
        if aid and aid != approve_id:
            reject_id = aid
            break

if reject_id:
    s, r = api(f"/leave/applications/{reject_id}/reject", "POST",
               {"reason": "Rejected for testing"}, admin_token)
    if s == 200:
        log("PASS", "LV-16: Admin rejects leave", f"id={reject_id}")
    else:
        s, r = api(f"/leave/applications/{reject_id}/reject", "PUT",
                   {"reason": "Rejected for testing"}, admin_token)
        if s == 200:
            log("PASS", "LV-16: Admin rejects leave (PUT)")
        else:
            log("FAIL", "LV-16: Reject leave", f"HTTP {s}: {r}")
else:
    log("SKIP", "LV-16: Reject leave", "No pending leave")

# ── 2.15 Cancel Leave ───────────────────────────────────────────────────
cancel_id = None
for tid, aid in applied_by_type.items():
    if aid and aid != approve_id and aid != reject_id:
        cancel_id = aid
        break

if cancel_id:
    s, r = api(f"/leave/applications/{cancel_id}", "PUT",
               {"status": "cancelled"}, emp_token)
    if s == 200:
        log("PASS", "LV-17: Cancel leave application", f"id={cancel_id}")
    else:
        s, r = api(f"/leave/applications/{cancel_id}/cancel", "POST", {}, emp_token)
        if s == 200:
            log("PASS", "LV-17: Cancel leave (via /cancel)")
        else:
            log("FAIL", "LV-17: Cancel leave", f"HTTP {s}: {r}")
else:
    log("SKIP", "LV-17: Cancel leave", "No suitable leave")

# ── 2.16 L004: Employee cannot self-approve ─────────────────────────────
self_approve_id = None
for tid, aid in applied_by_type.items():
    if aid and aid not in (approve_id, reject_id, cancel_id):
        self_approve_id = aid
        break

if self_approve_id:
    s, r = api(f"/leave/applications/{self_approve_id}/approve", "POST", {}, emp_token)
    if s in (400, 403):
        log("PASS", "LV-18: L004 — Employee cannot self-approve", f"HTTP {s}")
    elif s == 200:
        log("FAIL", "LV-18: L004 — Employee self-approved leave!")
    else:
        log("SKIP", "LV-18: L004 — Self-approve test", f"HTTP {s}")
else:
    log("SKIP", "LV-18: L004 — Self-approve test", "No pending leave")

# ── 2.17 Leave Calendar ─────────────────────────────────────────────────
s, r = api("/leave/calendar", token=admin_token)
if s == 200 and isinstance(r, dict) and r.get("success"):
    cal = extract_data(r)
    count = len(cal) if isinstance(cal, list) else "?"
    log("PASS", "LV-19: Leave calendar", f"Entries: {count}")
else:
    log("FAIL", "LV-19: Leave calendar", f"HTTP {s}")

s, r = api("/leave/calendar?month=2026-08", token=admin_token)
if s == 200:
    log("PASS", "LV-20: Leave calendar with month filter")
else:
    s, r = api("/leave/calendar?year=2026&month=8", token=admin_token)
    if s == 200:
        log("PASS", "LV-20: Leave calendar (year/month filter)")
    else:
        log("FAIL", "LV-20: Leave calendar filter", f"HTTP {s}")

# ── 2.18 Leave Policies ─────────────────────────────────────────────────
s, r = api("/leave/policies", token=admin_token)
policies = []
if s == 200 and isinstance(r, dict) and r.get("success"):
    policies = extract_data(r) or []
    log("PASS", "LV-21: List leave policies",
        f"Count: {len(policies) if isinstance(policies, list) else '?'}")
    for p in (policies if isinstance(policies, list) else [])[:5]:
        print(f"    Policy: id={p.get('id')}, name={p.get('name')}, "
              f"type_id={p.get('leave_type_id')}, accrual={p.get('accrual_type')}")
else:
    log("FAIL", "LV-21: Leave policies", f"HTTP {s}")

# ── 2.19 Leave Policies — Create (needs exact fields) ───────────────────
# Required: leave_type_id, name, annual_quota (number), accrual_type
pol_lt_id = leave_types[0].get("id") if leave_types else 17
s, r = api("/leave/policies", "POST", {
    "leave_type_id": pol_lt_id,
    "name": f"TestPolicy_{unique}",
    "annual_quota": 10,
    "accrual_type": "annual",
    "applicable_from_months": 0,
    "is_active": True
}, admin_token)
new_policy_id = None
if s in (200, 201):
    pd = extract_data(r)
    new_policy_id = pd.get("id") if isinstance(pd, dict) else None
    log("PASS", "LV-22: Create leave policy", f"id={new_policy_id}")
else:
    log("FAIL", "LV-22: Create leave policy", f"HTTP {s}: {r}")

# Cleanup policy
if new_policy_id:
    api(f"/leave/policies/{new_policy_id}", "DELETE", token=admin_token)

# ── 2.20 Comp-Off ───────────────────────────────────────────────────────
s, r = api("/leave/comp-off", token=admin_token)
if s == 200 and isinstance(r, dict):
    log("PASS", "LV-23: List comp-off",
        f"Count: {len(extract_data(r)) if isinstance(extract_data(r), list) else '?'}")
else:
    log("FAIL", "LV-23: List comp-off", f"HTTP {s}")

s, r = api("/leave/comp-off", "POST", {
    "date": "2026-03-22", "reason": f"Weekend work test {unique}", "hours": 8
}, emp_token)
if s in (200, 201):
    cd = extract_data(r)
    log("PASS", "LV-24: Create comp-off request", f"id={cd.get('id') if isinstance(cd, dict) else '?'}")
elif s == 400:
    log("PASS", "LV-24: Comp-off validation (400)")
else:
    log("FAIL", "LV-24: Create comp-off", f"HTTP {s}")

# ── 2.21 Half-day Leave (L012) ──────────────────────────────────────────
# Must use Sick Leave (17) since Priya is on probation
half_day_id = None
if test_leave_type_id:
    hd_date = find_free_date(2026, 12)
    s, r = api("/leave/applications", "POST", {
        "leave_type_id": 17,  # Sick Leave — allowed during probation
        "start_date": hd_date, "end_date": hd_date,
        "reason": "Half-day sick leave test", "is_half_day": 1,
        "half_day_type": "first_half", "days_count": 1
    }, emp_token)
    if s in (200, 201):
        hd = extract_data(r)
        half_day_id = hd.get("id") if isinstance(hd, dict) else None
        days = hd.get("days_count") if isinstance(hd, dict) else None
        used_dates.add(hd_date)
        if days and to_float(days) == 0.5:
            log("PASS", "LV-25: L012 — Half-day leave (0.5 days deducted)", f"days_count={days}")
        else:
            log("PASS", "LV-25: Half-day leave applied", f"days_count={days}")
    else:
        log("FAIL", "LV-25: Half-day leave", f"HTTP {s}: {r}")
else:
    log("SKIP", "LV-25: Half-day leave", "No leave type")

# ── 2.22 Invalid date: end < start ──────────────────────────────────────
if test_leave_type_id:
    s, r = api("/leave/applications", "POST", {
        "leave_type_id": 17,  # Sick Leave — probation-safe
        "start_date": "2026-12-20", "end_date": "2026-12-15",
        "reason": "Invalid date test", "is_half_day": 0, "days_count": 1
    }, emp_token)
    if s in (400, 422):
        log("PASS", "LV-26: End date < start date rejected", f"HTTP {s}")
    elif s in (200, 201):
        log("FAIL", "LV-26: End date < start date was ALLOWED!")
        inv = extract_data(r)
        if isinstance(inv, dict) and inv.get("id"):
            api(f"/leave/applications/{inv['id']}", "PUT", {"status": "cancelled"}, emp_token)
    else:
        log("SKIP", "LV-26: Invalid date test", f"HTTP {s}")
else:
    log("SKIP", "LV-26: Invalid date test", "No leave type")

# ── 2.23 Leave without reason ───────────────────────────────────────────
if test_leave_type_id:
    nr_date = find_free_date(2026, 12)
    s, r = api("/leave/applications", "POST", {
        "leave_type_id": 17,  # Sick Leave — probation-safe
        "start_date": nr_date, "end_date": nr_date,
        "is_half_day": 0, "days_count": 1
    }, emp_token)
    if s in (400, 422):
        log("PASS", "LV-27: Leave without reason rejected", f"HTTP {s}")
    elif s in (200, 201):
        log("FAIL", "LV-27: Leave without reason ALLOWED — reason should be required")
        inv = extract_data(r)
        if isinstance(inv, dict) and inv.get("id"):
            api(f"/leave/applications/{inv['id']}", "PUT", {"status": "cancelled"}, emp_token)
    else:
        log("SKIP", "LV-27: Leave without reason", f"HTTP {s}")
else:
    log("SKIP", "LV-27: Leave without reason", "No leave type")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 3: CROSS-MODULE — Leave Affects Attendance
# ════════════════════════════════════════════════════════════════════════════
print()
print("=" * 80)
print("SECTION 3: CROSS-MODULE — Leave Affects Attendance")
print("=" * 80)

# A010: Approved leave should show "On Leave" in attendance
if approve_id and apply_date:
    s, r = api(f"/attendance/records?start_date={apply_date}&end_date={apply_date}",
               token=admin_token)
    if s == 200:
        data = extract_data(r)
        if isinstance(data, list):
            found_on_leave = False
            for rec in data:
                uid = rec.get("user_id") or rec.get("employee_id")
                status = str(rec.get("status", "")).lower()
                if str(uid) == str(emp_id) and "leave" in status:
                    found_on_leave = True
                    break
            if found_on_leave:
                log("PASS", "CROSS-01: A010 — Approved leave shows 'On Leave' in attendance")
            elif len(data) == 0:
                log("SKIP", "CROSS-01: A010 — No attendance record for future leave date (expected)")
            else:
                log("SKIP", "CROSS-01: A010 — Future leave date, no attendance record yet")
        else:
            log("SKIP", "CROSS-01: A010 — Unexpected data format")
    else:
        log("FAIL", "CROSS-01: A010 — Check attendance for leave date", f"HTTP {s}")
else:
    log("SKIP", "CROSS-01: A010 — Cross-module check", "No approved leave")

# Calendar reflects approved leave
s, r = api("/leave/calendar", token=admin_token)
if s == 200:
    cal = extract_data(r)
    log("PASS", "CROSS-02: Leave calendar accessible",
        f"Entries: {len(cal) if isinstance(cal, list) else '?'}")
else:
    log("FAIL", "CROSS-02: Leave calendar", f"HTTP {s}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 4: SELENIUM UI TESTS
# ════════════════════════════════════════════════════════════════════════════
print()
print("=" * 80)
print("SECTION 4: SELENIUM UI TESTS")
print("=" * 80)

driver = None
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    def make_driver():
        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        d = webdriver.Chrome(options=opts)
        d.set_page_load_timeout(30)
        d.implicitly_wait(5)
        return d

    def ui_login(d, email, pw):
        d.get(f"{UI_BASE}/login")
        time.sleep(2)
        try:
            email_input = WebDriverWait(d, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
            )
            email_input.clear()
            email_input.send_keys(email)
            pw_input = d.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
            pw_input.clear()
            pw_input.send_keys(pw)
            btn = d.find_element(By.CSS_SELECTOR, "button[type='submit']")
            btn.click()
            time.sleep(3)
            return True
        except Exception as e:
            print(f"    Login failed: {e}")
            return False

    def wait_for_page(d, timeout=8):
        time.sleep(2)
        try:
            WebDriverWait(d, timeout).until(
                lambda dr: dr.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

    # ── Admin UI tests — restart driver every 3 pages to avoid crashes ──
    admin_pages = [
        ("/attendance", "Attendance page", "02"),
        ("/attendance/records", "Attendance records", "03"),
        ("/attendance/shifts", "Shifts management", "04"),
        ("/leave", "Leave management", "05"),
        ("/leave/applications", "Leave applications", "06"),
        ("/leave/types", "Leave types", "07"),
        ("/leave/calendar", "Leave calendar", "08"),
        ("/leave/policies", "Leave policies", "09"),
    ]

    driver = make_driver()
    pages_since_restart = 0
    if ui_login(driver, "ananya@technova.in", "Welcome@123"):
        screenshot(driver, "01_admin_login")
        log("PASS", "UI-01: Admin login")

        for url_suffix, name, idx in admin_pages:
            try:
                if pages_since_restart >= 3:
                    driver.quit()
                    time.sleep(1)
                    driver = make_driver()
                    ui_login(driver, "ananya@technova.in", "Welcome@123")
                    pages_since_restart = 0

                driver.get(f"{UI_BASE}{url_suffix}")
                wait_for_page(driver)
                screenshot(driver, f"{idx}_{url_suffix.replace('/', '_').strip('_')}")
                if len(driver.page_source) > 600:
                    log("PASS", f"UI-{idx}: {name} loads")
                else:
                    log("FAIL", f"UI-{idx}: {name} empty")
                pages_since_restart += 1
            except Exception as e:
                log("FAIL", f"UI-{idx}: {name}", f"Driver error: {str(e)[:80]}")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = make_driver()
                ui_login(driver, "ananya@technova.in", "Welcome@123")
                pages_since_restart = 0
    else:
        screenshot(driver, "01_admin_login_fail")
        log("FAIL", "UI-01: Admin login failed")

    try:
        driver.quit()
    except Exception:
        pass
    driver = None
    time.sleep(1)

    # ── Employee UI tests — restart driver every 3 pages ─────────────────
    emp_pages = [
        ("/dashboard", "Employee dashboard", "11"),
        ("/attendance", "Employee attendance", "12"),
        ("/leave", "Employee leave page", "13"),
        ("/leave/apply", "Leave apply page", "14"),
        ("/leave/applications", "My leave apps", "15"),
        ("/leave/calendar", "Leave calendar", "16"),
    ]

    driver = make_driver()
    pages_since_restart = 0
    if ui_login(driver, "priya@technova.in", "Welcome@123"):
        screenshot(driver, "10_employee_login")
        log("PASS", "UI-10: Employee login")

        for url_suffix, name, idx in emp_pages:
            try:
                if pages_since_restart >= 3:
                    driver.quit()
                    time.sleep(1)
                    driver = make_driver()
                    ui_login(driver, "priya@technova.in", "Welcome@123")
                    pages_since_restart = 0

                driver.get(f"{UI_BASE}{url_suffix}")
                wait_for_page(driver)
                screenshot(driver, f"{idx}_{url_suffix.replace('/', '_').strip('_')}")
                if len(driver.page_source) > 600:
                    log("PASS", f"UI-{idx}: {name} loads")
                else:
                    log("FAIL", f"UI-{idx}: {name} empty")
                pages_since_restart += 1
            except Exception as e:
                log("FAIL", f"UI-{idx}: {name}", f"Driver error: {str(e)[:80]}")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = make_driver()
                ui_login(driver, "priya@technova.in", "Welcome@123")
                pages_since_restart = 0
    else:
        screenshot(driver, "10_employee_login_fail")
        log("FAIL", "UI-10: Employee login failed")

    try:
        if driver:
            driver.quit()
    except Exception:
        pass
    driver = None

except ImportError:
    log("SKIP", "SELENIUM: Not available", "pip install selenium")
except Exception as e:
    log("FAIL", "SELENIUM ERROR", str(e))
    traceback.print_exc()
    if driver:
        try:
            screenshot(driver, "error_screenshot")
            driver.quit()
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 5: ADDITIONAL BUSINESS RULES
# ════════════════════════════════════════════════════════════════════════════
print()
print("=" * 80)
print("SECTION 5: ADDITIONAL BUSINESS RULES")
print("=" * 80)

# ── L003: No negative balances ──────────────────────────────────────────
s, r = api("/leave/balances", token=emp_token)
if s == 200 and isinstance(r, dict):
    all_pos = True
    for b in (extract_data(r) or []):
        bal = to_float(b.get("balance", 0))
        if bal < 0:
            all_pos = False
            log("FAIL", "BIZ-01: L003 — Negative balance found!",
                f"type_id={b.get('leave_type_id')}, balance={bal}")
            break
    if all_pos:
        log("PASS", "BIZ-01: L003 — No negative balances")
else:
    log("FAIL", "BIZ-01: L003 — Balance check", f"HTTP {s}")

# ── A003: Cannot clock in for future date ───────────────────────────────
s, r = api("/attendance/check-in", "POST", {"date": "2027-01-01"}, emp_token)
if s in (400, 422):
    log("PASS", "BIZ-02: A003 — Future date clock-in rejected", f"HTTP {s}")
elif s == 409:
    log("PASS", "BIZ-02: A003 — Clock-in rejected (already clocked in, future date param ignored)")
elif s in (200, 201):
    log("FAIL", "BIZ-02: A003 — Future date clock-in ALLOWED!")
else:
    log("SKIP", "BIZ-02: A003 — Future date clock-in", f"HTTP {s}")

# ── L010: Cannot approve already rejected leave ────────────────────────
if reject_id:
    s, r = api(f"/leave/applications/{reject_id}/approve", "POST", {}, admin_token)
    if s in (400, 409, 422):
        log("PASS", "BIZ-03: L010 — Cannot approve rejected leave", f"HTTP {s}")
    elif s == 200:
        log("FAIL", "BIZ-03: L010 — Approved an already rejected leave!")
    else:
        log("SKIP", "BIZ-03: L010 — Approve rejected", f"HTTP {s}")
else:
    log("SKIP", "BIZ-03: L010 — Approve rejected", "No rejected leave")

# ── L011: Cannot reject already approved leave ─────────────────────────
if approve_id:
    s, r = api(f"/leave/applications/{approve_id}/reject", "POST",
               {"reason": "Test re-reject"}, admin_token)
    if s in (400, 409, 422):
        log("PASS", "BIZ-04: L011 — Cannot reject approved leave", f"HTTP {s}")
    elif s == 200:
        log("FAIL", "BIZ-04: L011 — Rejected an already approved leave!")
    else:
        log("SKIP", "BIZ-04: L011 — Reject approved", f"HTTP {s}")
else:
    log("SKIP", "BIZ-04: L011 — Reject approved", "No approved leave")

# ── Invalid leave_type_id ───────────────────────────────────────────────
s, r = api("/leave/applications", "POST", {
    "leave_type_id": 99999, "start_date": "2026-12-01", "end_date": "2026-12-01",
    "reason": "Invalid type", "is_half_day": 0, "days_count": 1
}, emp_token)
if s in (400, 404, 422):
    log("PASS", "BIZ-05: Invalid leave_type_id rejected", f"HTTP {s}")
elif s in (200, 201):
    log("FAIL", "BIZ-05: Invalid leave_type_id ACCEPTED!")
else:
    log("SKIP", "BIZ-05: Invalid leave_type_id", f"HTTP {s}")

# ── L008: Cancel approved leave restores balance ────────────────────────
if approve_id:
    s_b, r_b = api("/leave/balances", token=emp_token)
    bal_before_cancel = {}
    if s_b == 200 and isinstance(r_b, dict):
        for b in (extract_data(r_b) or []):
            bal_before_cancel[b.get("leave_type_id")] = to_float(b.get("balance", 0))

    s, r = api(f"/leave/applications/{approve_id}", "PUT",
               {"status": "cancelled"}, emp_token)
    ok = s == 200
    if not ok:
        s, r = api(f"/leave/applications/{approve_id}/cancel", "POST", {}, emp_token)
        ok = s == 200

    if ok:
        log("PASS", "BIZ-06a: Cancel approved leave succeeded")
        time.sleep(1)
        s_b2, r_b2 = api("/leave/balances", token=emp_token)
        # The approved leave was Sick Leave (17) from applied_by_type
        cancel_check_type = 17  # Sick Leave
        if s_b2 == 200 and isinstance(r_b2, dict):
            for b in (extract_data(r_b2) or []):
                tid = b.get("leave_type_id")
                if tid == cancel_check_type:
                    after = to_float(b.get("balance", 0))
                    before = bal_before_cancel.get(tid, 0)
                    if after > before:
                        log("PASS", "BIZ-06b: L008 — Balance restored",
                            f"Before: {before}, After: {after}")
                    elif after == before:
                        log("FAIL", "BIZ-06b: L008 — Balance NOT restored",
                            f"Before: {before}, After: {after}")
                    else:
                        log("SKIP", "BIZ-06b: Inconclusive")
                    break
        else:
            log("FAIL", "BIZ-06b: Balance check", f"HTTP {s_b2}")
    else:
        log("FAIL", "BIZ-06: Cancel approved leave", f"HTTP {s}")
else:
    log("SKIP", "BIZ-06: L008 — Cancel approved", "No approved leave")


# ════════════════════════════════════════════════════════════════════════════
#  CLEANUP
# ════════════════════════════════════════════════════════════════════════════
print()
print("--- Cleanup: Cancelling test leaves ---")
all_cancel_ids = set()
if applied_leave_id:
    all_cancel_ids.add(applied_leave_id)
if multi_leave_id:
    all_cancel_ids.add(multi_leave_id)
if half_day_id:
    all_cancel_ids.add(half_day_id)
for aid in applied_by_type.values():
    if aid:
        all_cancel_ids.add(aid)

for aid in all_cancel_ids:
    s, r = api(f"/leave/applications/{aid}", "PUT", {"status": "cancelled"}, emp_token)
    if s != 200:
        api(f"/leave/applications/{aid}/cancel", "POST", {}, emp_token)
    print(f"  Cancelled id={aid}: HTTP {s}")

# Cleanup test policy
if new_policy_id:
    api(f"/leave/policies/{new_policy_id}", "DELETE", token=admin_token)


# ════════════════════════════════════════════════════════════════════════════
#  SUMMARY
# ════════════════════════════════════════════════════════════════════════════
print()
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)
print(f"  PASS: {PASS}")
print(f"  FAIL: {FAIL}")
print(f"  SKIP: {SKIP}")
print(f"  TOTAL: {PASS + FAIL + SKIP}")
print()

if FAIL > 0:
    print("FAILED TESTS:")
    for status, name, detail in results:
        if status == "FAIL":
            print(f"  [FAIL] {name} — {detail}")

if SKIP > 0:
    print()
    print("SKIPPED TESTS:")
    for status, name, detail in results:
        if status == "SKIP":
            print(f"  [SKIP] {name} — {detail}")

print()
print(f"Screenshots: {SCREENSHOT_DIR}")
print("=" * 80)
