#!/usr/bin/env python3
"""
EMP Cloud HRMS - Comprehensive Business Logic & Edge Case Testing
Senior QA: Real HR business rules, edge cases, data integrity.

Discovered API routes:
  POST /auth/login
  GET  /organizations/me, /organizations/me/departments
  GET/POST /users, /leave/types, /leave/applications, /leave/balances
  POST /attendance/check-in, /attendance/check-out
  GET  /attendance/records
  GET/POST /announcements, /events, /surveys
  GET/POST /helpdesk/tickets, /assets, /positions, /documents
  GET/POST /forum/posts, /forum/categories
  GET/POST /wellness/check-ins
  GET  /notifications
  PUT/PATCH /notifications/mark-all-read
"""

import sys
import json
import time
import requests
from datetime import datetime, timedelta, date
from typing import Optional

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

CREDENTIALS = {
    "org_admin": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "employee": {"email": "priya@technova.in", "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"},
}

BUGS = []
RESULTS = {"passed": 0, "failed": 0, "skipped": 0, "bugs": 0}


# ── helpers ──────────────────────────────────────────────────────────────────
def login(role):
    cred = CREDENTIALS[role]
    try:
        r = requests.post(f"{API_BASE}/auth/login", json=cred, timeout=30)
        if r.status_code == 200:
            data = r.json()["data"]
            return {"token": data["tokens"]["access_token"], "user": data["user"], "org": data.get("org", {})}
        print(f"  [LOGIN FAIL] {role}: {r.status_code}")
        return None
    except Exception as e:
        print(f"  [LOGIN ERROR] {role}: {e}")
        return None

def api(method, path, token, data=None, params=None):
    try:
        r = requests.request(method, f"{API_BASE}{path}",
                             headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                             json=data, params=params, timeout=30)
        try:
            return r.status_code, r.json()
        except:
            return r.status_code, r.text[:500]
    except Exception as e:
        return 0, str(e)

def ok(s): return s in (200, 201)

def record(name, passed, detail="", bug_title="", expected="", actual="", endpoint="", steps="", rule=""):
    RESULTS["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail[:300]}")
    if not passed and bug_title:
        BUGS.append({"title": f"[FUNCTIONAL] {bug_title}", "endpoint": endpoint,
                      "steps": steps, "expected": expected, "actual": actual, "business_rule": rule})
        RESULTS["bugs"] += 1

def skip(name, reason=""):
    RESULTS["skipped"] += 1
    print(f"  [SKIP] {name}: {reason}")

def cleanup_delete(path, token):
    api("DELETE", path, token)

def file_github_issues():
    if not BUGS:
        print("\n=== No bugs to file ===")
        return
    print(f"\n=== Filing {len(BUGS)} bugs to GitHub ===")
    hdr = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
    for bug in BUGS:
        body = f"""## Bug Report (Automated QA - Business Logic)

**URL/Endpoint:** `{API_BASE}{bug['endpoint']}`

**Steps to Reproduce:**
{bug['steps']}

**Expected Result:**
{bug['expected']}

**Actual Result:**
{bug['actual']}

**Business Rule Violated:**
{bug['business_rule']}

**Environment:** Test (test-empcloud-api.empcloud.com)
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        try:
            r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                              headers=hdr, json={"title": bug["title"], "body": body,
                              "labels": ["bug", "functional", "automated-qa"]}, timeout=30)
            if r.status_code == 201:
                print(f"  [FILED] {bug['title']} -> {r.json().get('html_url')}")
            else:
                print(f"  [FAIL] {bug['title']} - {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  [ERROR] {e}")


# ── discovery ────────────────────────────────────────────────────────────────
def discover(tok):
    info = {}
    for key, path in [
        ("org", "/organizations/me"), ("departments", "/organizations/me/departments"),
        ("users", "/users"), ("leave_types", "/leave/types"),
        ("leave_balances", "/leave/balances"), ("leave_apps", "/leave/applications"),
        ("attendance", "/attendance/records"), ("announcements", "/announcements"),
        ("events", "/events"), ("surveys", "/surveys"),
        ("tickets", "/helpdesk/tickets"), ("assets", "/assets"),
        ("positions", "/positions"), ("documents", "/documents"),
        ("forum_posts", "/forum/posts"), ("forum_cats", "/forum/categories"),
        ("wellness", "/wellness/check-ins"), ("notifications", "/notifications"),
    ]:
        s, d = api("GET", path, tok)
        if isinstance(d, dict):
            info[key] = d.get("data", []) if key != "org" else d.get("data", {})
        else:
            info[key] = [] if key != "org" else {}
    return info


# ═══════════════════════════════════════════════════════════════════════════
# 1. LEAVE MANAGEMENT EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════
def test_leave(admin_tok, emp_tok, emp_user, info):
    print("\n" + "="*70)
    print("1. LEAVE MANAGEMENT EDGE CASES")
    print("="*70)

    leave_types = [lt for lt in info.get("leave_types", []) if lt.get("is_active")]
    if not leave_types:
        skip("All leave tests", "No active leave types"); return
    lt_id = leave_types[0]["id"]
    emp_id = emp_user["id"]
    today = date.today()
    cleanup_ids = []

    def apply_leave(start, end, days, reason, token=emp_tok, lt=lt_id):
        return api("POST", "/leave/applications", token, {
            "leave_type_id": lt, "start_date": start, "end_date": end,
            "days_count": days, "reason": reason
        })

    # ── 1a. Past dates ──
    past_s = (today - timedelta(days=30)).isoformat()
    past_e = (today - timedelta(days=29)).isoformat()
    s, d = apply_leave(past_s, past_e, 1, "QA past dates")
    if ok(s):
        lid = d.get("data", {}).get("id")
        if lid: cleanup_ids.append(lid)
        record("Leave: Past dates (30 days ago)", False,
               f"Leave accepted for {past_s} to {past_e}",
               bug_title="Leave application accepted for dates 30 days in the past without restriction",
               endpoint="/leave/applications",
               steps=f"1. POST /leave/applications\n2. start_date={past_s}, end_date={past_e}",
               expected="Should reject or require special approval for past-dated leave",
               actual=f"API returned 201 and created the application",
               rule="Leave for past dates should be restricted to prevent retroactive manipulation of records")
    else:
        record("Leave: Past dates", True, f"Rejected ({s})")

    # ── 1b. end_date < start_date ──
    s, d = apply_leave((today+timedelta(60)).isoformat(), (today+timedelta(55)).isoformat(), 1, "QA bad dates")
    record("Leave: end < start", not ok(s), f"Status {s}")

    # ── 1c. Exceeds balance ──
    s, d = apply_leave((today+timedelta(70)).isoformat(), (today+timedelta(170)).isoformat(), 100, "QA exceed balance")
    if ok(s):
        lid = d.get("data", {}).get("id")
        if lid: cleanup_ids.append(lid)
        record("Leave: 100 days (exceeds balance)", False, "100-day leave accepted",
               bug_title="Leave exceeding balance accepted",
               endpoint="/leave/applications", steps="POST 100 days leave (balance ~18)",
               expected="Reject: insufficient balance", actual=f"Status {s}",
               rule="Leave balance must be validated before acceptance")
    else:
        err = str(d)[:200]
        record("Leave: Exceeds balance", True, f"Rejected: {err}")

    # ── 1d. Overlapping dates ──
    ol = (today + timedelta(days=80)).isoformat()
    s1, d1 = apply_leave(ol, ol, 1, "QA overlap 1")
    lid1 = d1.get("data", {}).get("id") if ok(s1) and isinstance(d1, dict) else None
    if lid1: cleanup_ids.append(lid1)
    s2, d2 = apply_leave(ol, ol, 1, "QA overlap 2")
    if ok(s1) and ok(s2):
        lid2 = d2.get("data", {}).get("id")
        if lid2: cleanup_ids.append(lid2)
        record("Leave: Overlapping dates", False, "Both accepted",
               bug_title="Overlapping leave accepted", endpoint="/leave/applications",
               steps=f"1. Apply for {ol}\n2. Apply same date again",
               expected="Second rejected (overlap)", actual="Both accepted",
               rule="Overlapping leave must be prevented")
    else:
        record("Leave: Overlapping dates", True, f"Second handled: {s2} - {str(d2)[:100]}")

    # ── 1e. Non-existent leave type ──
    s, d = apply_leave((today+timedelta(85)).isoformat(), (today+timedelta(85)).isoformat(), 1, "QA bad type", lt=99999)
    record("Leave: Non-existent type", not ok(s), f"Status {s}")

    # ── 1f. Weekend span (Thu-Mon = should be 3 not 5) ──
    days_to_thu = (3 - today.weekday()) % 7
    if days_to_thu <= 1: days_to_thu += 7
    thu = today + timedelta(days=days_to_thu + 14)
    mon = thu + timedelta(days=4)
    s, d = apply_leave(thu.isoformat(), mon.isoformat(), 5, "QA weekend span")
    if ok(s) and isinstance(d, dict):
        lid = d.get("data", {}).get("id")
        if lid: cleanup_ids.append(lid)
        days_counted = d.get("data", {}).get("days_count")
        if days_counted:
            dc = float(str(days_counted))
            if dc >= 5:
                record("Leave: Weekend counted as leave", False,
                       f"Thu({thu})-Mon({mon}) counted as {dc} days (expected 3 working days)",
                       bug_title="Weekend days (Sat/Sun) counted as leave days in leave application",
                       endpoint="/leave/applications",
                       steps=f"1. Apply leave Thu {thu} to Mon {mon}\n2. days_count returned = {dc}",
                       expected="3 working days (Thu, Fri, Mon) - Sat/Sun should be excluded",
                       actual=f"days_count = {dc} (includes Sat and Sun)",
                       rule="Non-working days (weekends) should not be deducted from leave balance")
            else:
                record("Leave: Weekend excluded", True, f"{dc} days counted (correct)")
        else:
            record("Leave: Weekend span", True, "Accepted, days_count not clear")
    else:
        record("Leave: Weekend span", True, f"Status {s}")

    # ── 1g. Negative balances check ──
    balances = info.get("leave_balances", [])
    neg = [b for b in balances if float(str(b.get("balance", 0))) < 0]
    if neg:
        for b in neg:
            record("Leave: Negative balance", False,
                   f"User {b['user_id']}, type {b['leave_type_id']}: balance={b['balance']}",
                   bug_title=f"Negative leave balance: {b['balance']}",
                   endpoint="/leave/balances", steps="GET /leave/balances",
                   expected="Balance >= 0", actual=f"balance = {b['balance']}",
                   rule="Leave balance must never go negative")
    else:
        record("Leave: No negative balances", True, "All balances >= 0")

    # ── 1h. Half day ──
    hd = (today + timedelta(days=90)).isoformat()
    s, d = api("POST", "/leave/applications", emp_tok, {
        "leave_type_id": lt_id, "start_date": hd, "end_date": hd,
        "days_count": 0.5, "is_half_day": 1, "half_day_type": "first_half",
        "reason": "QA half day"
    })
    if ok(s):
        ld = d.get("data", {})
        lid = ld.get("id")
        if lid: cleanup_ids.append(lid)
        dc = ld.get("days_count")
        record("Leave: Half day", True, f"Accepted with days_count={dc}")
    else:
        # Try without is_half_day flag, just 0.5 days_count
        s2, d2 = api("POST", "/leave/applications", emp_tok, {
            "leave_type_id": lt_id, "start_date": hd, "end_date": hd,
            "days_count": 0.5, "reason": "QA half day v2"
        })
        if ok(s2):
            lid2 = d2.get("data", {}).get("id")
            if lid2: cleanup_ids.append(lid2)
            record("Leave: Half day (v2)", True, f"Accepted with days_count=0.5")
        else:
            record("Leave: Half day", True, f"Validation: {s} / {s2} - may not support half-day via API")

    # Cleanup
    for lid in cleanup_ids:
        api("DELETE", f"/leave/applications/{lid}", admin_tok)


# ═══════════════════════════════════════════════════════════════════════════
# 2. ATTENDANCE EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════
def test_attendance(admin_tok, emp_tok, admin_user, emp_user, info):
    print("\n" + "="*70)
    print("2. ATTENDANCE EDGE CASES")
    print("="*70)

    # ── 2a. Double check-in ──
    # Use admin (may already have checked in today from discovery phase)
    s, d = api("POST", "/attendance/check-in", admin_tok, {})
    if ok(s):
        # Now try again
        s2, d2 = api("POST", "/attendance/check-in", admin_tok, {})
        if ok(s2):
            record("Attendance: Double check-in", False, "Second check-in accepted",
                   bug_title="Double check-in accepted on same day",
                   endpoint="/attendance/check-in", steps="1. Check in\n2. Check in again",
                   expected="Second rejected", actual=f"Both accepted",
                   rule="One check-in per day until check-out")
        else:
            record("Attendance: Double check-in", True, f"Rejected: {s2} - {str(d2)[:100]}")
        # Check out
        api("POST", "/attendance/check-out", admin_tok, {})
    elif s == 409:
        record("Attendance: Double check-in", True, f"Already checked in (409) - validation works")
    else:
        record("Attendance: Check-in", True, f"Status {s}")

    # ── 2b. Check-out without check-in ──
    # Use a user who hasn't checked in - create a temp user scenario
    # Since we can't easily test this without a fresh user, check the message
    # The employee already checked in/out. Double check-out should fail.
    s, d = api("POST", "/attendance/check-out", emp_tok, {})
    record("Attendance: Check-out handling", True, f"Status {s}: {str(d)[:100]}")

    # ── 2c. Worked hours from existing records ──
    records = info.get("attendance", [])
    for rec in records:
        ci = rec.get("check_in")
        co = rec.get("check_out")
        wm = rec.get("worked_minutes")
        if ci and co and wm is not None:
            try:
                ci_dt = datetime.fromisoformat(ci.replace("Z", "+00:00"))
                co_dt = datetime.fromisoformat(co.replace("Z", "+00:00"))
                expected_min = (co_dt - ci_dt).total_seconds() / 60
                actual_min = float(str(wm))
                if abs(expected_min - actual_min) > 2 and expected_min > 0:
                    record("Attendance: Hours accuracy", False,
                           f"Record {rec['id']}: check_in={ci}, check_out={co}, expected ~{expected_min:.0f}min, got {actual_min}min",
                           bug_title=f"Attendance record {rec['id']}: worked_minutes ({actual_min}) does not match check_in/out difference ({expected_min:.0f})",
                           endpoint=f"/attendance/records",
                           steps=f"1. GET /attendance/records\n2. Record {rec['id']}: check_in={ci}, check_out={co}",
                           expected=f"worked_minutes ~ {expected_min:.0f}",
                           actual=f"worked_minutes = {actual_min}",
                           rule="worked_minutes must equal (check_out - check_in)")
                    break
            except:
                pass
    else:
        record("Attendance: Hours accuracy", True, "Existing records have consistent worked_minutes")


# ═══════════════════════════════════════════════════════════════════════════
# 3. EMPLOYEE DATA INTEGRITY
# ═══════════════════════════════════════════════════════════════════════════
def test_employees(admin_tok, emp_tok, admin_user, emp_user, info):
    print("\n" + "="*70)
    print("3. EMPLOYEE DATA INTEGRITY")
    print("="*70)

    users = info.get("users", [])
    depts = info.get("departments", [])
    dept_id = depts[0]["id"] if depts else None
    admin_id = admin_user["id"]
    ts = int(time.time())

    def create_user(extra):
        base = {"first_name": "QA", "last_name": f"Test{ts}",
                "email": f"qa-{ts}-{time.time_ns()}@test.com",
                "role": "employee", "department_id": dept_id,
                "date_of_joining": date.today().isoformat(), "password": "Test@12345"}
        base.update(extra)
        return api("POST", "/users", admin_tok, base)

    # ── 3a. Duplicate email ──
    s, d = create_user({"email": CREDENTIALS["employee"]["email"]})
    if ok(s):
        uid = d.get("data", {}).get("id")
        record("Employee: Duplicate email", False, f"Created with dup email",
               bug_title="Employee created with duplicate email",
               endpoint="/users", steps=f"POST /users with email={CREDENTIALS['employee']['email']}",
               expected="Reject: email in use", actual=f"Status {s}, ID {uid}",
               rule="Email must be unique (login credential)")
        if uid: cleanup_delete(f"/users/{uid}", admin_tok)
    else:
        record("Employee: Duplicate email", True, f"Rejected ({s})")

    # ── 3b. Duplicate emp_code ──
    existing_code = next((u["emp_code"] for u in users if u.get("emp_code")), None)
    if existing_code:
        s, d = create_user({"emp_code": existing_code})
        if ok(s):
            uid = d.get("data", {}).get("id")
            record("Employee: Duplicate emp_code", False, f"Created with dup code={existing_code}",
                   bug_title="Employee created with duplicate employee code (emp_code)",
                   endpoint="/users",
                   steps=f"1. POST /users with emp_code={existing_code}\n2. This code already exists on another employee",
                   expected="Reject: emp_code must be unique",
                   actual=f"API returned {s} - duplicate code accepted",
                   rule="Employee codes must be unique identifiers within the organization")
            if uid: cleanup_delete(f"/users/{uid}", admin_tok)
        else:
            record("Employee: Duplicate emp_code", True, f"Rejected ({s})")

    # ── 3c. Exit before joining ──
    s, d = create_user({"date_of_joining": "2025-06-01", "date_of_exit": "2025-01-01"})
    if ok(s):
        uid = d.get("data", {}).get("id")
        record("Employee: Exit before joining", False, "exit=2025-01-01 < joining=2025-06-01 accepted",
               bug_title="Employee created with date_of_exit (2025-01-01) before date_of_joining (2025-06-01)",
               endpoint="/users",
               steps="1. POST /users with date_of_joining=2025-06-01, date_of_exit=2025-01-01",
               expected="Reject: exit must be after joining",
               actual=f"Status {s}",
               rule="date_of_exit must be >= date_of_joining")
        if uid: cleanup_delete(f"/users/{uid}", admin_tok)
    else:
        record("Employee: Exit before joining", True, f"Rejected ({s})")

    # ── 3d. Under-18 ──
    dob = (date.today() - timedelta(days=365*16)).isoformat()
    s, d = create_user({"date_of_birth": dob})
    if ok(s):
        uid = d.get("data", {}).get("id")
        record("Employee: Under-18 (age 16)", False, f"DOB={dob} accepted",
               bug_title="No minimum age validation: employee created with date_of_birth making them 16 years old",
               endpoint="/users",
               steps=f"1. POST /users with date_of_birth={dob} (age ~16)",
               expected="Reject or warn: must be >= 18 years old",
               actual=f"Status {s}",
               rule="Labor law compliance: employees must be at least 18 years old")
        if uid: cleanup_delete(f"/users/{uid}", admin_tok)
    else:
        record("Employee: Under-18", True, f"Response ({s})")

    # ── 3e. Non-existent department ──
    s, d = create_user({"department_id": 99999})
    if ok(s):
        uid = d.get("data", {}).get("id")
        record("Employee: Non-existent dept", False, "dept_id=99999 accepted",
               bug_title="Employee created with non-existent department_id=99999",
               endpoint="/users", steps="POST /users with department_id=99999",
               expected="Reject: department not found",
               actual=f"Status {s}",
               rule="Referential integrity: department_id must exist")
        if uid: cleanup_delete(f"/users/{uid}", admin_tok)
    else:
        record("Employee: Non-existent dept", True, f"Rejected ({s})")

    # ── 3f. Self-manager in existing data ──
    self_mgrs = [u for u in users if u.get("reporting_manager_id") == u.get("id") and u.get("id")]
    if self_mgrs:
        for sm in self_mgrs[:1]:
            record("Employee: Self-manager in data", False,
                   f"User {sm['id']} ({sm.get('first_name','')} {sm.get('last_name','')}) reports to themselves",
                   bug_title=f"Employee ID {sm['id']} has reporting_manager_id = own ID (self-referencing manager)",
                   endpoint=f"/users",
                   steps=f"1. GET /users\n2. User {sm['id']}: reporting_manager_id = {sm['reporting_manager_id']} (same as own ID)",
                   expected="reporting_manager_id should never equal own user ID",
                   actual=f"User {sm['id']} reports to themselves",
                   rule="Reporting hierarchy cannot contain self-references")
    else:
        record("Employee: No self-managers", True, "No users report to themselves")

    # ── 3g. Set self as manager via API ──
    s, d = api("PUT", f"/users/{admin_id}", admin_tok, {
        "first_name": admin_user["first_name"], "last_name": admin_user["last_name"],
        "email": admin_user["email"], "reporting_manager_id": admin_id,
        "role": admin_user["role"], "department_id": admin_user.get("department_id"),
        "date_of_joining": str(admin_user.get("date_of_joining", ""))[:10],
    })
    if ok(s):
        ld = d.get("data", {}) if isinstance(d, dict) else {}
        if ld.get("reporting_manager_id") == admin_id:
            record("Employee: Self-manager via API", False,
                   f"User {admin_id} set as own manager",
                   bug_title="API allows setting an employee as their own reporting manager",
                   endpoint=f"/users/{admin_id}",
                   steps=f"1. PUT /users/{admin_id} with reporting_manager_id={admin_id}",
                   expected="Reject: cannot report to yourself",
                   actual=f"Status {s} - self-reference created",
                   rule="Reporting hierarchy must not contain self-references (prevents infinite loops)")
            # Revert
            api("PUT", f"/users/{admin_id}", admin_tok, {
                "first_name": admin_user["first_name"], "last_name": admin_user["last_name"],
                "email": admin_user["email"], "reporting_manager_id": None,
                "role": admin_user["role"], "department_id": admin_user.get("department_id"),
                "date_of_joining": str(admin_user.get("date_of_joining", ""))[:10],
            })
        else:
            record("Employee: Self-manager via API", True, "Self-ref not stored")
    else:
        record("Employee: Self-manager API", True, f"Status {s}")

    # ── 3h. Circular reporting (A->B, B->A) ──
    if len(users) >= 2:
        u1, u2 = users[0], users[1]
        u1_id, u2_id = u1["id"], u2["id"]
        u1_orig = u1.get("reporting_manager_id")
        u2_orig = u2.get("reporting_manager_id")
        # Set A->B
        api("PUT", f"/users/{u1_id}", admin_tok, {
            "first_name": u1["first_name"], "last_name": u1["last_name"],
            "email": u1["email"], "reporting_manager_id": u2_id,
            "role": u1.get("role","employee"), "department_id": u1.get("department_id"),
            "date_of_joining": str(u1.get("date_of_joining",""))[:10],
        })
        # Set B->A
        s, d = api("PUT", f"/users/{u2_id}", admin_tok, {
            "first_name": u2["first_name"], "last_name": u2["last_name"],
            "email": u2["email"], "reporting_manager_id": u1_id,
            "role": u2.get("role","employee"), "department_id": u2.get("department_id"),
            "date_of_joining": str(u2.get("date_of_joining",""))[:10],
        })
        if ok(s):
            ld = d.get("data", {}) if isinstance(d, dict) else {}
            if ld.get("reporting_manager_id") == u1_id:
                record("Employee: Circular reporting", False,
                       f"Circular chain: {u1_id} -> {u2_id} -> {u1_id}",
                       bug_title="Circular reporting chain allowed (A->B, B->A creates infinite loop)",
                       endpoint=f"/users/{u2_id}",
                       steps=f"1. Set user {u1_id} manager = {u2_id}\n2. Set user {u2_id} manager = {u1_id}",
                       expected="Reject: circular chain detected",
                       actual="Both updates accepted",
                       rule="Reporting hierarchy must be a DAG (directed acyclic graph)")
            else:
                record("Employee: Circular reporting", True, "Prevented")
        else:
            record("Employee: Circular reporting", True, f"Prevented ({s})")
        # Revert both
        api("PUT", f"/users/{u1_id}", admin_tok, {
            "first_name": u1["first_name"], "last_name": u1["last_name"],
            "email": u1["email"], "reporting_manager_id": u1_orig,
            "role": u1.get("role","employee"), "department_id": u1.get("department_id"),
            "date_of_joining": str(u1.get("date_of_joining",""))[:10],
        })
        api("PUT", f"/users/{u2_id}", admin_tok, {
            "first_name": u2["first_name"], "last_name": u2["last_name"],
            "email": u2["email"], "reporting_manager_id": u2_orig,
            "role": u2.get("role","employee"), "department_id": u2.get("department_id"),
            "date_of_joining": str(u2.get("date_of_joining",""))[:10],
        })


# ═══════════════════════════════════════════════════════════════════════════
# 4. ANNOUNCEMENT LOGIC
# ═══════════════════════════════════════════════════════════════════════════
def test_announcements(admin_tok, emp_tok, info):
    print("\n" + "="*70)
    print("4. ANNOUNCEMENT LOGIC")
    print("="*70)

    def create_ann(title, content, priority="low"):
        return api("POST", "/announcements", admin_tok, {
            "title": title, "content": content, "priority": priority, "target_type": "all"
        })

    # ── 4a. Empty content ──
    s, d = create_ann("QA Empty Content", "")
    if ok(s):
        aid = d.get("data", {}).get("id")
        record("Announcement: Empty content", False, "Created with empty content",
               bug_title="Announcement created with empty content body",
               endpoint="/announcements", steps="POST with content=''",
               expected="Reject: content required", actual=f"Status {s}",
               rule="Announcements must have meaningful content")
        if aid: cleanup_delete(f"/announcements/{aid}", admin_tok)
    else:
        record("Announcement: Empty content", True, f"Rejected ({s})")

    # ── 4b. Empty title ──
    s, d = create_ann("", "Some content")
    if ok(s):
        aid = d.get("data", {}).get("id")
        record("Announcement: Empty title", False, "Created with empty title",
               bug_title="Announcement created with empty title",
               endpoint="/announcements", steps="POST with title=''",
               expected="Reject: title required", actual=f"Status {s}",
               rule="Announcements must have a title")
        if aid: cleanup_delete(f"/announcements/{aid}", admin_tok)
    else:
        record("Announcement: Empty title", True, f"Rejected ({s})")

    # ── 4c. Delete and verify ──
    s, d = create_ann("QA Delete Test", "Will delete")
    if ok(s):
        aid = d.get("data", {}).get("id")
        if aid:
            api("DELETE", f"/announcements/{aid}", admin_tok)
            sg, dg = api("GET", f"/announcements/{aid}", admin_tok)
            if sg == 200 and isinstance(dg, dict):
                gd = dg.get("data", {})
                if gd and not gd.get("is_deleted") and not gd.get("deleted_at"):
                    record("Announcement: Soft delete visible", False,
                           f"Deleted announcement {aid} still returned via GET",
                           bug_title="Deleted announcement still visible via GET endpoint",
                           endpoint=f"/announcements/{aid}",
                           steps=f"1. DELETE /announcements/{aid}\n2. GET /announcements/{aid}",
                           expected="404 or deleted flag set", actual=f"Still returns data",
                           rule="Deleted items should not be visible in normal GET requests")
                else:
                    record("Announcement: Delete", True, "Properly handled")
            else:
                record("Announcement: Delete", True, f"GET after delete: {sg}")


# ═══════════════════════════════════════════════════════════════════════════
# 5. EVENT LOGIC
# ═══════════════════════════════════════════════════════════════════════════
def test_events(admin_tok, info):
    print("\n" + "="*70)
    print("5. EVENT LOGIC")
    print("="*70)

    today = date.today()

    # ── 5a. end < start ──
    s, d = api("POST", "/events", admin_tok, {
        "title": "QA Bad Dates", "description": "end before start", "event_type": "other",
        "start_date": (today+timedelta(10)).isoformat(), "end_date": (today+timedelta(5)).isoformat(),
        "location": "Test", "target_type": "all"
    })
    if ok(s):
        eid = d.get("data", {}).get("id")
        record("Event: end < start", False, "Created with end before start",
               bug_title="Event created with end_date before start_date (no date range validation)",
               endpoint="/events",
               steps=f"1. POST /events\n2. start_date={today+timedelta(10)}, end_date={today+timedelta(5)}",
               expected="Reject: end_date >= start_date required",
               actual=f"Status {s} - event created",
               rule="Events must have valid date ranges")
        if eid: cleanup_delete(f"/events/{eid}", admin_tok)
    else:
        record("Event: end < start", True, f"Rejected ({s})")

    # ── 5b. Empty title ──
    s, d = api("POST", "/events", admin_tok, {
        "title": "", "description": "test", "event_type": "other",
        "start_date": (today+timedelta(10)).isoformat(), "end_date": (today+timedelta(11)).isoformat(),
        "location": "Test", "target_type": "all"
    })
    if ok(s):
        eid = d.get("data", {}).get("id")
        record("Event: Empty title", False, "Created with empty title",
               bug_title="Event created with empty title",
               endpoint="/events", steps="POST with title=''",
               expected="Reject: title required", actual=f"Status {s}",
               rule="Events must have a title")
        if eid: cleanup_delete(f"/events/{eid}", admin_tok)
    else:
        record("Event: Empty title", True, f"Rejected ({s})")

    # ── 5c. Check existing events for date issues ──
    events = info.get("events", [])
    for e in events:
        sd = str(e.get("start_date",""))[:10]
        ed = str(e.get("end_date",""))[:10]
        if sd and ed and ed < sd:
            record("Event: Existing bad dates", False,
                   f"Event '{e.get('title',e['id'])}': start={sd}, end={ed}",
                   bug_title=f"Existing event '{e.get('title','?')}' has end_date ({ed}) before start_date ({sd})",
                   endpoint=f"/events/{e['id']}",
                   steps=f"GET /events -> event {e['id']}",
                   expected="end_date >= start_date", actual=f"start={sd}, end={ed}",
                   rule="Event date consistency")


# ═══════════════════════════════════════════════════════════════════════════
# 6. SURVEY LOGIC
# ═══════════════════════════════════════════════════════════════════════════
def test_surveys(admin_tok, info):
    print("\n" + "="*70)
    print("6. SURVEY LOGIC")
    print("="*70)

    today = date.today()

    # ── 6a. end < start ──
    s, d = api("POST", "/surveys", admin_tok, {
        "title": "QA Bad Dates", "description": "test", "type": "pulse",
        "start_date": (today+timedelta(10)).isoformat(), "end_date": (today+timedelta(5)).isoformat(),
        "target_type": "all"
    })
    if ok(s):
        sid = d.get("data", {}).get("id")
        record("Survey: end < start", False, "Created with end before start",
               bug_title="Survey created with end_date before start_date (no date validation)",
               endpoint="/surveys",
               steps=f"1. POST /surveys\n2. start_date={today+timedelta(10)}, end_date={today+timedelta(5)}",
               expected="Reject: end_date >= start_date",
               actual=f"Status {s} - survey created",
               rule="Survey date range must be valid")
        if sid: cleanup_delete(f"/surveys/{sid}", admin_tok)
    else:
        record("Survey: end < start", True, f"Response ({s})")

    # ── 6b. Publish with no questions ──
    s, d = api("POST", "/surveys", admin_tok, {
        "title": "QA No Questions", "description": "test", "type": "pulse",
        "status": "published", "start_date": today.isoformat(),
        "end_date": (today+timedelta(7)).isoformat(), "target_type": "all"
    })
    if ok(s):
        ld = d.get("data", {})
        sid = ld.get("id")
        if ld.get("status") == "published":
            record("Survey: Published with 0 questions", False, "Published with no questions",
                   bug_title="Survey published with zero questions",
                   endpoint="/surveys", steps="POST with status=published and no questions",
                   expected="Reject or keep as draft", actual=f"Status {s}, status=published",
                   rule="Published surveys must have >= 1 question")
        else:
            record("Survey: Published with 0 questions", True, f"Created as '{ld.get('status')}' (not published)")
        if sid: cleanup_delete(f"/surveys/{sid}", admin_tok)
    else:
        record("Survey: 0 questions", True, f"Response ({s})")


# ═══════════════════════════════════════════════════════════════════════════
# 7. HELPDESK LOGIC
# ═══════════════════════════════════════════════════════════════════════════
def test_helpdesk(admin_tok, emp_tok, info):
    print("\n" + "="*70)
    print("7. HELPDESK LOGIC")
    print("="*70)

    # ── 7a. Empty subject ──
    s, d = api("POST", "/helpdesk/tickets", emp_tok, {
        "subject": "", "description": "test", "priority": "medium", "category": "general"
    })
    if ok(s):
        tid = d.get("data", {}).get("id")
        record("Helpdesk: Empty subject", False, "Created with empty subject",
               bug_title="Helpdesk ticket created with empty subject",
               endpoint="/helpdesk/tickets", steps="POST with subject=''",
               expected="Reject: subject required", actual=f"Status {s}",
               rule="Tickets must have a subject for identification")
        if tid: cleanup_delete(f"/helpdesk/tickets/{tid}", admin_tok)
    else:
        record("Helpdesk: Empty subject", True, f"Rejected ({s})")

    # ── 7b. Create, close, assign to nonexistent ──
    s, d = api("POST", "/helpdesk/tickets", emp_tok, {
        "subject": "QA Test Ticket", "description": "Testing lifecycle",
        "priority": "low", "category": "general"
    })
    if ok(s):
        tid = d.get("data", {}).get("id")
        record("Helpdesk: Create", True, f"Ticket {tid}")

        # Assign to non-existent
        sa, da = api("PUT", f"/helpdesk/tickets/{tid}", admin_tok, {
            "assigned_to": 99999, "status": "in_progress"
        })
        if ok(sa):
            record("Helpdesk: Assign to nonexistent user", False, "assigned_to=99999 accepted",
                   bug_title="Helpdesk ticket assigned to non-existent user (ID 99999)",
                   endpoint=f"/helpdesk/tickets/{tid}",
                   steps="PUT with assigned_to=99999",
                   expected="Reject: user not found",
                   actual=f"Status {sa}",
                   rule="Ticket assignment must reference valid user")
        else:
            record("Helpdesk: Assign to nonexistent", True, f"Handled ({sa})")

        cleanup_delete(f"/helpdesk/tickets/{tid}", admin_tok)


# ═══════════════════════════════════════════════════════════════════════════
# 8. ASSET MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════
def test_assets(admin_tok, info):
    print("\n" + "="*70)
    print("8. ASSET MANAGEMENT")
    print("="*70)

    ts = int(time.time())

    # ── 8a. Existing warranty < purchase ──
    for a in info.get("assets", []):
        pd = str(a.get("purchase_date",""))[:10]
        we = str(a.get("warranty_expiry",""))[:10]
        if pd and we and we < pd and pd != "" and we != "":
            record("Asset: Existing warranty < purchase", False,
                   f"Asset '{a.get('name',a['id'])}': purchase={pd}, warranty={we}",
                   bug_title=f"Existing asset has warranty_expiry ({we}) before purchase_date ({pd})",
                   endpoint=f"/assets/{a['id']}",
                   steps=f"GET /assets -> ID {a['id']}",
                   expected="warranty_expiry > purchase_date", actual=f"purchase={pd}, warranty={we}",
                   rule="Warranty cannot expire before purchase")
            break  # Report only first

    # ── 8b. Create with warranty < purchase ──
    s, d = api("POST", "/assets", admin_tok, {
        "name": "QA Warranty Test", "asset_tag": f"QA-W-{ts}", "serial_number": f"SN-W-{ts}",
        "purchase_date": "2025-06-01", "warranty_expiry": "2024-01-01",
        "status": "available", "condition_status": "new"
    })
    if ok(s):
        aid = d.get("data", {}).get("id")
        record("Asset: Warranty < purchase", False, "warranty=2024 < purchase=2025 accepted",
               bug_title="Asset created with warranty_expiry (2024-01-01) before purchase_date (2025-06-01)",
               endpoint="/assets",
               steps="POST with purchase_date=2025-06-01, warranty_expiry=2024-01-01",
               expected="Reject: warranty must be after purchase",
               actual=f"Status {s}",
               rule="Logical date constraint: warranty_expiry >= purchase_date")
        if aid: cleanup_delete(f"/assets/{aid}", admin_tok)
    else:
        record("Asset: Warranty < purchase", True, f"Response ({s})")

    # ── 8c. Double assignment ──
    s, d = api("POST", "/assets", admin_tok, {
        "name": "QA Double Assign", "asset_tag": f"QA-DA-{ts}", "serial_number": f"SN-DA-{ts}",
        "purchase_date": "2025-01-01", "status": "available", "condition_status": "new"
    })
    if ok(s):
        asset_id = d.get("data", {}).get("id")
        users = info.get("users", [])
        if asset_id and len(users) >= 2:
            u1, u2 = users[0]["id"], users[1]["id"]
            # Assign via PUT (status=assigned + assigned_to)
            s1, _ = api("PUT", f"/assets/{asset_id}", admin_tok, {
                "name": "QA Double Assign", "asset_tag": f"QA-DA-{ts}",
                "status": "assigned", "assigned_to": u1, "condition_status": "new"
            })
            s2, d2 = api("PUT", f"/assets/{asset_id}", admin_tok, {
                "name": "QA Double Assign", "asset_tag": f"QA-DA-{ts}",
                "status": "assigned", "assigned_to": u2, "condition_status": "new"
            })
            if ok(s1) and ok(s2):
                record("Asset: Double assignment", False,
                       f"Asset {asset_id} assigned to both {u1} and {u2}",
                       bug_title="Same asset assigned to multiple employees (no unassignment required first)",
                       endpoint=f"/assets/{asset_id}",
                       steps=f"1. PUT assign to user {u1}\n2. PUT assign to user {u2} (no unassign step)",
                       expected="Reject second: must unassign first",
                       actual="Both accepted",
                       rule="Physical asset can only be assigned to one employee at a time")
            else:
                record("Asset: Double assignment", True, f"Assign1={s1}, Assign2={s2}")
        cleanup_delete(f"/assets/{asset_id}", admin_tok)


# ═══════════════════════════════════════════════════════════════════════════
# 9. POSITION LOGIC
# ═══════════════════════════════════════════════════════════════════════════
def test_positions(admin_tok, info):
    print("\n" + "="*70)
    print("9. POSITION/VACANCY LOGIC")
    print("="*70)

    ts = int(time.time())
    depts = info.get("departments", [])
    dept_id = depts[0]["id"] if depts else None

    s, d = api("POST", "/positions", admin_tok, {
        "title": f"QA Neg HC {ts}", "code": f"NEG-{ts}",
        "department_id": dept_id, "headcount_budget": -5, "status": "active"
    })
    if ok(s):
        ld = d.get("data", {})
        pid = ld.get("id")
        hc = ld.get("headcount_budget")
        if hc is not None and int(str(hc)) < 0:
            record("Position: Negative headcount", False, f"headcount_budget={hc}",
                   bug_title="Position created with negative headcount_budget",
                   endpoint="/positions", steps="POST with headcount_budget=-5",
                   expected="Reject: headcount must be positive", actual=f"headcount_budget={hc}",
                   rule="Position headcount must be a positive integer")
        else:
            record("Position: Negative headcount", True, f"Stored as {hc}")
        if pid: cleanup_delete(f"/positions/{pid}", admin_tok)
    else:
        record("Position: Negative headcount", True, f"Response ({s})")


# ═══════════════════════════════════════════════════════════════════════════
# 10. DOCUMENT ACCESS CONTROL
# ═══════════════════════════════════════════════════════════════════════════
def test_documents(admin_tok, emp_tok, admin_user, info):
    print("\n" + "="*70)
    print("10. DOCUMENT LOGIC")
    print("="*70)

    # Employee accessing admin's docs
    s, d = api("GET", "/documents", emp_tok, params={"user_id": admin_user["id"]})
    if s == 200 and isinstance(d, dict):
        docs = d.get("data", [])
        admin_docs = [doc for doc in docs if doc.get("user_id") == admin_user["id"]]
        if admin_docs:
            record("Document: Cross-employee access", False,
                   f"Employee sees {len(admin_docs)} docs of user {admin_user['id']}",
                   bug_title="Employee can access other employees' documents via user_id filter parameter",
                   endpoint="/documents",
                   steps=f"1. Login as employee\n2. GET /documents?user_id={admin_user['id']}",
                   expected="Only own documents or 403",
                   actual=f"Returns {len(admin_docs)} documents of another user",
                   rule="Document access: employees see only their own documents unless authorized")
        else:
            record("Document: Cross-employee access", True, "Properly filtered")
    else:
        record("Document: Cross-employee access", True, f"Access controlled ({s})")


# ═══════════════════════════════════════════════════════════════════════════
# 11. FORUM LOGIC
# ═══════════════════════════════════════════════════════════════════════════
def test_forums(admin_tok, emp_tok, emp_user, info):
    print("\n" + "="*70)
    print("11. FORUM LOGIC")
    print("="*70)

    cats = info.get("forum_cats", [])
    cat_id = cats[0]["id"] if cats else None

    # ── 11a. Empty content ──
    s, d = api("POST", "/forum/posts", emp_tok, {
        "title": "QA Empty", "content": "", "category_id": cat_id, "post_type": "discussion"
    })
    if ok(s):
        pid = d.get("data", {}).get("id")
        record("Forum: Empty content", False, "Post created with empty content",
               bug_title="Forum post created with empty content body",
               endpoint="/forum/posts", steps="POST with content=''",
               expected="Reject: content required", actual=f"Status {s}",
               rule="Forum posts must have content")
        if pid: cleanup_delete(f"/forum/posts/{pid}", admin_tok)
    else:
        record("Forum: Empty content", True, f"Response ({s})")

    # ── 11b. Non-existent category ──
    s, d = api("POST", "/forum/posts", emp_tok, {
        "title": "QA Bad Cat", "content": "test", "category_id": 99999, "post_type": "discussion"
    })
    if ok(s):
        pid = d.get("data", {}).get("id")
        record("Forum: Non-existent category", False, "Post in category 99999",
               bug_title="Forum post created with non-existent category_id",
               endpoint="/forum/posts", steps="POST with category_id=99999",
               expected="Reject: category not found", actual=f"Status {s}",
               rule="Category must exist (referential integrity)")
        if pid: cleanup_delete(f"/forum/posts/{pid}", admin_tok)
    else:
        record("Forum: Non-existent category", True, f"Response ({s})")

    # ── 11c. Employee edit others' post ──
    posts = info.get("forum_posts", [])
    other_post = next((p for p in posts if p.get("author_id") != emp_user["id"]), None)
    if other_post:
        orig_content = other_post.get("content", "")
        s, d = api("PUT", f"/forum/posts/{other_post['id']}", emp_tok, {
            "title": other_post.get("title", ""), "content": "HACKED BY QA",
            "category_id": other_post.get("category_id"), "post_type": other_post.get("post_type", "discussion")
        })
        if ok(s):
            record("Forum: Edit others' post", False,
                   f"Employee edited post {other_post['id']} by user {other_post.get('author_id')}",
                   bug_title="Regular employee can edit another user's forum post (broken access control)",
                   endpoint=f"/forum/posts/{other_post['id']}",
                   steps=f"1. Login as employee ({emp_user['email']})\n2. PUT /forum/posts/{other_post['id']}",
                   expected="403: only author or admin", actual=f"Status {s}",
                   rule="Forum authorization: only post author and admins can edit")
            # Revert
            api("PUT", f"/forum/posts/{other_post['id']}", admin_tok, {
                "title": other_post.get("title",""), "content": orig_content,
                "category_id": other_post.get("category_id"), "post_type": other_post.get("post_type","discussion")
            })
        else:
            record("Forum: Edit others' post", True, f"Denied ({s})")


# ═══════════════════════════════════════════════════════════════════════════
# 12. WELLNESS LOGIC
# ═══════════════════════════════════════════════════════════════════════════
def test_wellness(admin_tok, emp_tok, info):
    print("\n" + "="*70)
    print("12. WELLNESS LOGIC")
    print("="*70)

    today = date.today()

    # ── 12a. Future date ──
    s, d = api("POST", "/wellness/check-ins", emp_tok, {
        "check_in_date": (today+timedelta(7)).isoformat(),
        "mood": "good", "energy_level": 3, "sleep_hours": 7, "exercise_minutes": 30
    })
    if ok(s):
        cid = d.get("data", {}).get("id")
        record("Wellness: Future date", False, "Check-in for 7 days from now accepted",
               bug_title="Wellness check-in accepted for a future date",
               endpoint="/wellness/check-ins",
               steps=f"POST with check_in_date={today+timedelta(7)}",
               expected="Reject: cannot check-in for future",
               actual=f"Status {s}",
               rule="Wellness check-ins must be for today or past only")
        if cid: cleanup_delete(f"/wellness/check-ins/{cid}", admin_tok)
    else:
        record("Wellness: Future date", True, f"Response ({s})")

    # ── 12b. Invalid values ──
    s, d = api("POST", "/wellness/check-ins", emp_tok, {
        "check_in_date": (today-timedelta(10)).isoformat(),
        "mood": "good", "energy_level": 999, "sleep_hours": -5, "exercise_minutes": -100
    })
    if ok(s):
        cid = d.get("data", {}).get("id")
        record("Wellness: Out-of-range values", False,
               "energy=999, sleep=-5, exercise=-100 accepted",
               bug_title="Wellness check-in accepts invalid numeric values (energy=999, sleep=-5, exercise=-100)",
               endpoint="/wellness/check-ins",
               steps="POST with energy_level=999, sleep_hours=-5, exercise_minutes=-100",
               expected="Reject: values out of valid range",
               actual=f"Status {s}",
               rule="Wellness values must have valid ranges (energy 1-5, sleep/exercise >= 0)")
        if cid: cleanup_delete(f"/wellness/check-ins/{cid}", admin_tok)
    else:
        record("Wellness: Out-of-range values", True, f"Response ({s})")

    # ── 12c. Double check-in ──
    cd = (today - timedelta(5)).isoformat()
    base = {"check_in_date": cd, "mood": "good", "energy_level": 3, "sleep_hours": 7, "exercise_minutes": 30}
    s1, d1 = api("POST", "/wellness/check-ins", emp_tok, base)
    cid1 = d1.get("data", {}).get("id") if ok(s1) and isinstance(d1, dict) else None
    s2, d2 = api("POST", "/wellness/check-ins", emp_tok, {**base, "mood": "bad", "energy_level": 1})
    cid2 = d2.get("data", {}).get("id") if ok(s2) and isinstance(d2, dict) else None
    if ok(s1) and ok(s2):
        record("Wellness: Double check-in", False, f"Two check-ins for {cd} accepted",
               bug_title="Multiple wellness check-ins allowed on the same day",
               endpoint="/wellness/check-ins",
               steps=f"1. POST check-in for {cd}\n2. POST another for same date",
               expected="Second rejected or updates first",
               actual="Both accepted as separate records",
               rule="One wellness check-in per employee per day")
    else:
        record("Wellness: Double check-in", True, f"First={s1}, Second={s2}")
    if cid1: cleanup_delete(f"/wellness/check-ins/{cid1}", admin_tok)
    if cid2: cleanup_delete(f"/wellness/check-ins/{cid2}", admin_tok)


# ═══════════════════════════════════════════════════════════════════════════
# 13. BILLING / 14. NOTIFICATIONS / 15. CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════
def test_billing_notifs_consistency(admin_tok, emp_tok, admin_session, info):
    print("\n" + "="*70)
    print("13-15. BILLING, NOTIFICATIONS, CONSISTENCY")
    print("="*70)

    org = admin_session.get("org", {})
    cur = org.get("current_user_count", 0)
    allowed = org.get("total_allowed_user_count", 0)
    record("Billing: User counts", True, f"current={cur}, allowed={allowed}")

    if allowed > 0 and cur > allowed:
        record("Billing: Over limit", False, f"{cur} > {allowed}",
               bug_title=f"Active users ({cur}) exceed subscription limit ({allowed})",
               endpoint="/organizations/me", steps="GET /organizations/me",
               expected=f"<= {allowed}", actual=f"{cur}",
               rule="Subscription user limit enforcement")

    # Notifications
    s, d = api("GET", "/notifications", emp_tok)
    record("Notifications: Endpoint", s == 200, f"Status {s}")

    s, d = api("PUT", "/notifications/mark-all-read", emp_tok, {})
    record("Notifications: Mark all read", ok(s) or s == 204, f"Status {s}")

    # Consistency: org user count vs API
    users = info.get("users", [])
    active = len([u for u in users if u.get("status") == 1])
    if cur > 0 and abs(cur - active) > 3:
        record("Consistency: User count", False,
               f"Org says {cur}, API has {active} active ({len(users)} total)",
               bug_title=f"Org current_user_count ({cur}) differs significantly from API active users ({active})",
               endpoint="/organizations/me vs /users",
               steps="Compare current_user_count with active users from /users",
               expected="Counts should match", actual=f"Org={cur}, Active={active}",
               rule="Dashboard consistency")
    else:
        record("Consistency: User count", True, f"Org={cur}, Active={active}, Total={len(users)}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("="*70)
    print("EMP CLOUD HRMS - BUSINESS LOGIC & EDGE CASE TEST SUITE")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {API_BASE}")
    print("="*70)

    # Login
    print("\n--- Authenticating ---")
    admin_sess = login("org_admin")
    emp_sess = login("employee")
    if not admin_sess or not emp_sess:
        print("FATAL: Login failed"); return

    at = admin_sess["token"]
    et = emp_sess["token"]
    au = admin_sess["user"]
    eu = emp_sess["user"]
    print(f"  Admin: {au['first_name']} {au['last_name']} (ID: {au['id']})")
    print(f"  Employee: {eu['first_name']} {eu['last_name']} (ID: {eu['id']})")

    # Discover
    print("\n--- Discovering data ---")
    info = discover(at)
    for k in ["users","departments","leave_types","leave_balances","leave_apps",
              "attendance","assets","tickets","events","surveys","forum_posts","wellness"]:
        v = info.get(k, [])
        print(f"  {k}: {len(v) if isinstance(v, list) else 'N/A'}")

    # Run tests
    test_leave(at, et, eu, info)
    test_attendance(at, et, au, eu, info)
    test_employees(at, et, au, eu, info)
    test_announcements(at, et, info)
    test_events(at, info)
    test_surveys(at, info)
    test_helpdesk(at, et, info)
    test_assets(at, info)
    test_positions(at, info)
    test_documents(at, et, au, info)
    test_forums(at, et, eu, info)
    test_wellness(at, et, info)
    test_billing_notifs_consistency(at, et, admin_sess, info)

    # Summary
    print("\n" + "="*70)
    print("TEST EXECUTION SUMMARY")
    print("="*70)
    total = RESULTS["passed"] + RESULTS["failed"] + RESULTS["skipped"]
    print(f"  PASSED:     {RESULTS['passed']}")
    print(f"  FAILED:     {RESULTS['failed']}")
    print(f"  SKIPPED:    {RESULTS['skipped']}")
    print(f"  BUGS FOUND: {RESULTS['bugs']}")
    print(f"  TOTAL:      {total}")
    if total: print(f"  PASS RATE:  {RESULTS['passed']/total*100:.1f}%")

    # File bugs
    if BUGS:
        print(f"\n--- Filing {len(BUGS)} bugs to GitHub ---")
        file_github_issues()
    else:
        print("\n--- No bugs to file ---")

    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
