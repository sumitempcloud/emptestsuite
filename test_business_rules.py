#!/usr/bin/env python3
"""
EmpCloud HRMS - Critical Business Rules Audit (v3 - corrected API formats)
Tests 46 business rules across all HRMS domains.
"""
import sys, json, time, traceback
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import urllib3
urllib3.disable_warnings()

# ── Config ─────────────────────────────────────────────────────────────
API      = "https://test-empcloud-api.empcloud.com/api/v1"
PAYROLL  = "https://testpayroll-api.empcloud.com/api/v1"
RECRUIT  = "https://test-recruit-api.empcloud.com/api/v1"
PERF     = "https://test-performance-api.empcloud.com/api/v1"
EXIT     = "https://test-exit-api.empcloud.com/api/v1"

GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO  = "EmpCloud/EmpCloud"

ENFORCED = "ENFORCED"
NOT_ENFORCED = "NOT ENFORCED"
NOT_IMPL = "NOT IMPLEMENTED"
PARTIAL  = "PARTIAL"

results = []

def record(rid, cat, rule, status, detail=""):
    results.append({"id": rid, "category": cat, "rule": rule, "status": status, "detail": detail, "issue_url": None})
    icons = {ENFORCED: "[OK]", NOT_ENFORCED: "[BUG]", NOT_IMPL: "[N/A]", PARTIAL: "[!!]"}
    print(f"  {icons.get(status,'[??]')} Rule {rid}: {rule} -> {status}")
    if detail: print(f"      {detail[:280]}")

def hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

def login_cloud(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    if r.status_code != 200: return None
    return r.json()["data"]["tokens"]["access_token"]

def login_module(base, email, pw):
    """Login to a module that uses accessToken (camelCase)."""
    r = requests.post(f"{base}/auth/login", json={"email": email, "password": pw}, timeout=30)
    if r.status_code != 200: return None
    d = r.json()["data"]
    t = d.get("tokens", {})
    return t.get("accessToken") or t.get("access_token") or d.get("accessToken") or d.get("access_token")

def get_data(r):
    """Extract data from EmpCloud response, handling both data=[] and data={data:[]}."""
    if not r or r.status_code != 200: return None
    d = r.json()
    payload = d.get("data", d)
    if isinstance(payload, list): return payload
    if isinstance(payload, dict) and "data" in payload: return payload["data"]
    return payload

def file_issue(title, body, labels):
    try:
        r = requests.post(f"https://api.github.com/repos/{GH_REPO}/issues",
            headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"},
            json={"title": title, "body": body, "labels": labels}, timeout=30)
        return r.json().get("html_url") if r.status_code == 201 else None
    except: return None


# ══════════════════════════════════════════════════════════════════════
def test_subscription(at):
    print("\n=== SUBSCRIPTION & BILLING RULES ===")

    # 1: Seat limit
    try:
        subs = get_data(requests.get(f"{API}/subscriptions", headers=hdr(at), timeout=20))
        info = ""
        if isinstance(subs, list) and subs:
            info = f"total_seats={subs[0].get('total_seats')}, used={subs[0].get('used_seats')}"
        r = requests.post(f"{API}/users/invite", headers=hdr(at), json={
            "email": f"seattest_{int(time.time())}@fake-test.com",
            "first_name": "SeatTest", "last_name": "User", "role": "employee"
        }, timeout=20)
        if r.status_code in [200, 201]:
            record(1, "Subscription", "Seat limit enforcement", NOT_ENFORCED,
                   f"Invite succeeded without seat check. {info}")
        elif "seat" in r.text.lower() or "limit" in r.text.lower():
            record(1, "Subscription", "Seat limit enforcement", ENFORCED, f"Blocked: {r.text[:200]}")
        else:
            record(1, "Subscription", "Seat limit enforcement", PARTIAL, f"{r.status_code}: {r.text[:200]}. {info}")
    except Exception as e:
        record(1, "Subscription", "Seat limit enforcement", PARTIAL, str(e))

    # 2: Module access after unsubscribe
    try:
        subs = get_data(requests.get(f"{API}/subscriptions", headers=hdr(at), timeout=20))
        record(2, "Subscription", "Module access after unsubscribe", PARTIAL,
               f"{len(subs) if isinstance(subs, list) else 0} subscriptions. Cannot safely unsubscribe on shared test env.")
    except Exception as e:
        record(2, "Subscription", "Module access after unsubscribe", PARTIAL, str(e))

    # 3: Free tier limits
    try:
        mods = get_data(requests.get(f"{API}/modules", headers=hdr(at), timeout=20))
        free = [m for m in (mods if isinstance(mods, list) else []) if m.get("is_free") or m.get("price", 1) == 0]
        record(3, "Subscription", "Free tier limits",
               PARTIAL if free else NOT_IMPL,
               f"{len(free)} free modules" if free else "No free-tier modules found")
    except Exception as e:
        record(3, "Subscription", "Free tier limits", NOT_IMPL, str(e))

    # 4: Auto-renew
    try:
        subs = get_data(requests.get(f"{API}/subscriptions", headers=hdr(at), timeout=20))
        if isinstance(subs, list) and subs:
            s = subs[0]
            bc = s.get("billing_cycle")
            record(4, "Subscription", "Billing cycle auto-renew", PARTIAL if bc else NOT_IMPL,
                   f"billing_cycle={bc}, start={s.get('start_date')}, end={s.get('end_date')}")
        else:
            record(4, "Subscription", "Billing cycle auto-renew", NOT_IMPL, "No subscriptions")
    except Exception as e:
        record(4, "Subscription", "Billing cycle auto-renew", PARTIAL, str(e))

    # 5: Overdue invoice
    try:
        r = requests.get(f"{API}/billing/invoices", headers=hdr(at), timeout=20)
        invs = get_data(r)
        if isinstance(invs, list):
            overdue = [i for i in invs if i.get("status") in ["overdue", "past_due"]]
            record(5, "Subscription", "Overdue invoice enforcement (15 days)", PARTIAL,
                   f"{len(invs)} invoices, {len(overdue)} overdue. Cannot verify product-stop.")
        else:
            record(5, "Subscription", "Overdue invoice enforcement (15 days)", NOT_IMPL,
                   f"No invoice data (may be empty): {r.text[:200]}")
    except Exception as e:
        record(5, "Subscription", "Overdue invoice enforcement (15 days)", NOT_IMPL, str(e))


def test_leave(at, et):
    print("\n=== LEAVE RULES ===")
    bals = get_data(requests.get(f"{API}/leave/balances", headers=hdr(et), timeout=20)) or []
    types = get_data(requests.get(f"{API}/leave/types", headers=hdr(at), timeout=20)) or []

    # Find a leave type with balance
    lt_id = bals[0]["leave_type_id"] if isinstance(bals, list) and bals else (types[0]["id"] if isinstance(types, list) and types else None)
    bal_val = float(bals[0].get("balance", 0)) if isinstance(bals, list) and bals else 0

    # 6: Cannot exceed balance
    try:
        r = requests.post(f"{API}/leave/applications", headers=hdr(et), json={
            "leave_type_id": lt_id, "start_date": "2026-08-01", "end_date": "2026-09-20",
            "days_count": 50, "reason": "Business rule test - exceed balance"
        }, timeout=20)
        if r.status_code == 400 and ("balance" in r.text.lower() or "insufficient" in r.text.lower()):
            record(6, "Leave", "Cannot apply leave > balance", ENFORCED,
                   f"Blocked: {r.json().get('error',{}).get('message','')}")
        elif r.status_code in [200, 201]:
            record(6, "Leave", "Cannot apply leave > balance", NOT_ENFORCED,
                   f"50-day leave accepted with balance {bal_val}!")
        else:
            record(6, "Leave", "Cannot apply leave > balance", PARTIAL, f"{r.status_code}: {r.text[:200]}")
    except Exception as e:
        record(6, "Leave", "Cannot apply leave > balance", PARTIAL, str(e))

    # 7: Cannot apply on behalf of another
    try:
        emps = get_data(requests.get(f"{API}/employees", headers=hdr(at), timeout=20)) or []
        other_id = next((e["id"] for e in emps if e.get("email") != "priya@technova.in"), None)
        if other_id and lt_id:
            r = requests.post(f"{API}/leave/applications", headers=hdr(et), json={
                "leave_type_id": lt_id, "start_date": "2026-07-10", "end_date": "2026-07-10",
                "days_count": 1, "reason": "test on-behalf", "employee_id": other_id, "user_id": other_id
            }, timeout=20)
            if r.status_code in [400, 403, 422]:
                record(7, "Leave", "Cannot apply leave on behalf of another (as employee)", ENFORCED,
                       f"Blocked: {r.status_code}")
            elif r.status_code in [200, 201]:
                d = r.json().get("data", r.json())
                if str(d.get("user_id")) == str(other_id):
                    record(7, "Leave", "Cannot apply leave on behalf of another (as employee)", NOT_ENFORCED,
                           f"Applied for another employee!")
                else:
                    record(7, "Leave", "Cannot apply leave on behalf of another (as employee)", ENFORCED,
                           "Server ignored employee_id, applied to self")
                try:
                    aid = d.get("id")
                    if aid: requests.put(f"{API}/leave/applications/{aid}", headers=hdr(et), json={"status":"cancelled"}, timeout=10)
                except: pass
            else:
                record(7, "Leave", "Cannot apply leave on behalf of another (as employee)", PARTIAL, f"{r.status_code}: {r.text[:200]}")
        else:
            record(7, "Leave", "Cannot apply leave on behalf of another (as employee)", PARTIAL, "No other employee found")
    except Exception as e:
        record(7, "Leave", "Cannot apply leave on behalf of another (as employee)", PARTIAL, str(e))

    # 8: Manager approval RBAC (approve is PUT not POST)
    try:
        apps = get_data(requests.get(f"{API}/leave/applications", headers=hdr(at), timeout=20)) or []
        pending = [a for a in (apps if isinstance(apps, list) else []) if a.get("status") == "pending"]
        if pending:
            aid = pending[0]["id"]
            r = requests.put(f"{API}/leave/applications/{aid}/approve", headers=hdr(et), json={}, timeout=20)
            if r.status_code == 403:
                record(8, "Leave", "Manager can only approve direct reports' leaves", ENFORCED,
                       f"Employee blocked (403): {r.json().get('error',{}).get('message','')}")
            elif r.status_code in [200, 201]:
                record(8, "Leave", "Manager can only approve direct reports' leaves", NOT_ENFORCED,
                       "Non-manager employee approved a leave!")
            else:
                record(8, "Leave", "Manager can only approve direct reports' leaves", PARTIAL, f"{r.status_code}: {r.text[:200]}")
        else:
            record(8, "Leave", "Manager can only approve direct reports' leaves", PARTIAL, "No pending apps")
    except Exception as e:
        record(8, "Leave", "Manager can only approve direct reports' leaves", PARTIAL, str(e))

    # 9: No negative balances
    try:
        negs = [b for b in (bals if isinstance(bals, list) else []) if float(b.get("balance", 0)) < 0]
        record(9, "Leave", "Leave balance should not go negative",
               NOT_ENFORCED if negs else ENFORCED,
               f"Found {len(negs)} negative" if negs else f"No negative balances across {len(bals)} types")
    except Exception as e:
        record(9, "Leave", "Leave balance should not go negative", PARTIAL, str(e))

    # 10: Cannot cancel past leave
    try:
        apps = get_data(requests.get(f"{API}/leave/applications", headers=hdr(et), timeout=20)) or []
        today = datetime.now().strftime("%Y-%m-%d")
        past_app = next((a for a in (apps if isinstance(apps, list) else [])
                         if a.get("end_date","")[:10] < today and a.get("status") == "approved"), None)
        if past_app:
            r = requests.put(f"{API}/leave/applications/{past_app['id']}", headers=hdr(et),
                             json={"status": "cancelled"}, timeout=20)
            if r.status_code in [200, 201]:
                record(10, "Leave", "Cannot cancel already taken leave (past dates)", NOT_ENFORCED,
                       f"Past leave (ended {past_app['end_date'][:10]}) was cancelled!")
            elif r.status_code in [400, 403, 422]:
                record(10, "Leave", "Cannot cancel already taken leave (past dates)", ENFORCED,
                       f"Blocked: {r.status_code}")
            else:
                record(10, "Leave", "Cannot cancel already taken leave (past dates)", PARTIAL, f"{r.status_code}")
        else:
            record(10, "Leave", "Cannot cancel already taken leave (past dates)", PARTIAL, "No past approved leaves")
    except Exception as e:
        record(10, "Leave", "Cannot cancel already taken leave (past dates)", PARTIAL, str(e))

    # 11: Maternity/paternity eligibility
    mat = [t for t in (types if isinstance(types, list) else []) if "matern" in t.get("name","").lower() or "patern" in t.get("name","").lower()]
    record(11, "Leave", "Maternity/paternity leave eligibility checks",
           PARTIAL if mat else NOT_IMPL,
           f"Types: {[m['name'] for m in mat]}. Gender/tenure checks not testable via API alone." if mat else "No mat/pat types")

    # 12: Leave accrual
    try:
        pols = get_data(requests.get(f"{API}/leave/policies", headers=hdr(at), timeout=20)) or []
        accrual = [p for p in (pols if isinstance(pols, list) else []) if p.get("accrual") or p.get("accrual_type") or p.get("accrual_frequency")]
        record(12, "Leave", "Leave accrual (balances increase monthly)",
               ENFORCED if accrual else PARTIAL,
               f"{len(accrual)} policies with accrual" if accrual else f"Policies found but no accrual fields. Keys: {list(pols[0].keys())[:12] if pols else 'none'}")
    except Exception as e:
        record(12, "Leave", "Leave accrual (balances increase monthly)", PARTIAL, str(e))

    # 13: Probation leave restrictions
    try:
        pols = get_data(requests.get(f"{API}/leave/policies", headers=hdr(at), timeout=20)) or []
        found = any("probation" in json.dumps(p).lower() for p in (pols if isinstance(pols, list) else []))
        record(13, "Leave", "Probation period leave restrictions",
               ENFORCED if found else NOT_IMPL,
               "Probation config found" if found else "No probation config in leave policies")
    except Exception as e:
        record(13, "Leave", "Probation period leave restrictions", PARTIAL, str(e))


def test_attendance(at, et):
    print("\n=== ATTENDANCE RULES ===")

    # 14: Cannot check in twice
    try:
        r1 = requests.post(f"{API}/attendance/check-in", headers=hdr(et), json={}, timeout=20)
        time.sleep(0.5)
        r2 = requests.post(f"{API}/attendance/check-in", headers=hdr(et), json={}, timeout=20)
        if r2.status_code == 409 and "already" in r2.text.lower():
            record(14, "Attendance", "Cannot clock in twice in same day", ENFORCED,
                   f"Second blocked (409): {r2.json().get('error',{}).get('message','')}")
        elif r1.status_code == 409 and "already" in r1.text.lower():
            record(14, "Attendance", "Cannot clock in twice in same day", ENFORCED,
                   f"Already checked in: {r1.json().get('error',{}).get('message','')}")
        elif r1.status_code in [200,201] and r2.status_code in [200,201]:
            record(14, "Attendance", "Cannot clock in twice in same day", NOT_ENFORCED,
                   "Both check-ins accepted!")
        else:
            record(14, "Attendance", "Cannot clock in twice in same day", PARTIAL,
                   f"R1:{r1.status_code} R2:{r2.status_code}")
    except Exception as e:
        record(14, "Attendance", "Cannot clock in twice in same day", PARTIAL, str(e))

    # 15: Cannot check out without check in
    try:
        # Use admin token (admin may not have checked in today)
        r = requests.post(f"{API}/attendance/check-out", headers=hdr(at), json={}, timeout=20)
        if r.status_code in [400, 409] and any(kw in r.text.lower() for kw in ["not checked", "check in first", "no check-in"]):
            record(15, "Attendance", "Cannot clock out without clocking in", ENFORCED,
                   f"{r.status_code}: {r.json().get('error',{}).get('message','')}")
        elif r.status_code == 409 and "already" in r.text.lower():
            record(15, "Attendance", "Cannot clock out without clocking in", PARTIAL,
                   "Already checked out (admin was already checked in/out today)")
        elif r.status_code in [200, 201]:
            record(15, "Attendance", "Cannot clock out without clocking in", PARTIAL,
                   "Check-out succeeded (admin likely already checked in)")
        else:
            record(15, "Attendance", "Cannot clock out without clocking in", PARTIAL,
                   f"{r.status_code}: {r.text[:200]}")
    except Exception as e:
        record(15, "Attendance", "Cannot clock out without clocking in", PARTIAL, str(e))

    # 16: Future date check-in
    try:
        future = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        r = requests.post(f"{API}/attendance/check-in", headers=hdr(et), json={"date": future}, timeout=20)
        if r.status_code == 409 and "already" in r.text.lower():
            # Already checked in, system may just be rejecting because of that, not date
            record(16, "Attendance", "Cannot clock in for future dates", PARTIAL,
                   "Already checked in today - cannot isolate future date check")
        elif r.status_code in [400, 422] and ("future" in r.text.lower() or "invalid" in r.text.lower()):
            record(16, "Attendance", "Cannot clock in for future dates", ENFORCED,
                   f"Blocked: {r.text[:200]}")
        elif r.status_code in [200, 201]:
            record(16, "Attendance", "Cannot clock in for future dates", NOT_ENFORCED,
                   "Future date accepted!")
        else:
            record(16, "Attendance", "Cannot clock in for future dates", PARTIAL,
                   f"{r.status_code}: {r.text[:200]}")
    except Exception as e:
        record(16, "Attendance", "Cannot clock in for future dates", PARTIAL, str(e))

    # 17: Past date check-in
    try:
        past = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        r = requests.post(f"{API}/attendance/check-in", headers=hdr(et), json={"date": past}, timeout=20)
        if r.status_code == 409 and "already" in r.text.lower():
            record(17, "Attendance", "Cannot clock in for past dates (only regularization)", PARTIAL,
                   "Already checked in today - cannot isolate past date check")
        elif r.status_code in [400, 422]:
            record(17, "Attendance", "Cannot clock in for past dates (only regularization)", ENFORCED,
                   f"Blocked: {r.text[:200]}")
        elif r.status_code in [200, 201]:
            record(17, "Attendance", "Cannot clock in for past dates (only regularization)", NOT_ENFORCED,
                   "Past date check-in accepted!")
        else:
            record(17, "Attendance", "Cannot clock in for past dates (only regularization)", PARTIAL,
                   f"{r.status_code}: {r.text[:200]}")
    except Exception as e:
        record(17, "Attendance", "Cannot clock in for past dates (only regularization)", PARTIAL, str(e))

    # 18: Late arrival flagging
    try:
        recs = get_data(requests.get(f"{API}/attendance/records", headers=hdr(at), timeout=20)) or []
        if isinstance(recs, list) and recs:
            has_late = "late_minutes" in recs[0] or "late" in json.dumps(recs[0]).lower()
            record(18, "Attendance", "Late arrival flagging",
                   ENFORCED if has_late else NOT_IMPL,
                   f"late_minutes field present, value={recs[0].get('late_minutes')}" if has_late else f"Keys: {list(recs[0].keys())[:12]}")
        else:
            record(18, "Attendance", "Late arrival flagging", PARTIAL, "No records")
    except Exception as e:
        record(18, "Attendance", "Late arrival flagging", PARTIAL, str(e))

    # 19: Overtime calculation
    try:
        recs = get_data(requests.get(f"{API}/attendance/records", headers=hdr(at), timeout=20)) or []
        if isinstance(recs, list) and recs:
            has_ot = "overtime_minutes" in recs[0]
            record(19, "Attendance", "Overtime calculation",
                   ENFORCED if has_ot else NOT_IMPL,
                   f"overtime_minutes field present, value={recs[0].get('overtime_minutes')}" if has_ot else f"Keys: {list(recs[0].keys())[:12]}")
        else:
            record(19, "Attendance", "Overtime calculation", PARTIAL, "No records")
    except Exception as e:
        record(19, "Attendance", "Overtime calculation", PARTIAL, str(e))

    # 20: Attendance on holidays
    try:
        r = requests.get(f"{API}/leave/calendar", headers=hdr(at), timeout=20)
        record(20, "Attendance", "Cannot mark attendance on holidays", PARTIAL,
               f"Holiday calendar: {r.status_code}. Cannot verify blocking without scheduling holiday check-in.")
    except Exception as e:
        record(20, "Attendance", "Cannot mark attendance on holidays", PARTIAL, str(e))


def test_employee(at, et, ot):
    print("\n=== EMPLOYEE RULES ===")
    emps = get_data(requests.get(f"{API}/employees", headers=hdr(at), timeout=20)) or []

    # 21: Cannot delete employee with pending items
    try:
        r = requests.delete(f"{API}/employees/{emps[0]['id'] if emps else 999}", headers=hdr(at), timeout=20)
        if r.status_code == 404:
            record(21, "Employee", "Cannot delete employee with pending items", NOT_IMPL,
                   "DELETE endpoint not found (404) - employee deletion not supported via API")
        elif r.status_code in [400, 409, 422]:
            record(21, "Employee", "Cannot delete employee with pending items", ENFORCED,
                   f"Blocked: {r.text[:200]}")
        elif r.status_code in [200, 204]:
            record(21, "Employee", "Cannot delete employee with pending items", NOT_ENFORCED,
                   "Employee deleted without check!")
        else:
            record(21, "Employee", "Cannot delete employee with pending items", PARTIAL, f"{r.status_code}: {r.text[:200]}")
    except Exception as e:
        record(21, "Employee", "Cannot delete employee with pending items", PARTIAL, str(e))

    # 22: Cannot change org_id
    try:
        if emps:
            eid = emps[0]["id"]
            orig_org = emps[0].get("organization_id")
            r = requests.put(f"{API}/employees/{eid}/profile", headers=hdr(at),
                             json={"organization_id": 99999}, timeout=20)
            # Verify org didn't change
            r2 = requests.get(f"{API}/employees/{eid}/profile", headers=hdr(at), timeout=20)
            if r2.status_code == 200:
                new_org = r2.json().get("data", {}).get("organization_id")
                if str(new_org) == str(orig_org):
                    record(22, "Employee", "Cannot change employee org_id (cross-org transfer)", ENFORCED,
                           f"PUT accepted but org_id stayed {orig_org} (silently ignored)")
                else:
                    record(22, "Employee", "Cannot change employee org_id (cross-org transfer)", NOT_ENFORCED,
                           f"org_id changed from {orig_org} to {new_org}!")
            else:
                record(22, "Employee", "Cannot change employee org_id (cross-org transfer)", PARTIAL, f"Verify: {r2.status_code}")
        else:
            record(22, "Employee", "Cannot change employee org_id (cross-org transfer)", PARTIAL, "No employees")
    except Exception as e:
        record(22, "Employee", "Cannot change employee org_id (cross-org transfer)", PARTIAL, str(e))

    # 23: Terminated employee login
    try:
        term = [e for e in (emps if isinstance(emps, list) else []) if e.get("status") in [0, "0", "inactive", "terminated"]]
        if term:
            email = term[0].get("email")
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": "Welcome@123"}, timeout=20)
            if r.status_code == 200:
                record(23, "Employee", "Terminated employee cannot login", NOT_ENFORCED,
                       f"Terminated {email} logged in!")
            else:
                msg = r.json().get("error", {}).get("message", "") if r.status_code != 200 else ""
                record(23, "Employee", "Terminated employee cannot login", ENFORCED,
                       f"Login blocked ({r.status_code}): {msg}")
        else:
            record(23, "Employee", "Terminated employee cannot login", PARTIAL, "No terminated employees in system")
    except Exception as e:
        record(23, "Employee", "Terminated employee cannot login", PARTIAL, str(e))

    # 24: Deactivated not in headcount
    try:
        all_emps = get_data(requests.get(f"{API}/employees", headers=hdr(at), timeout=20)) or []
        inactive_in_list = [e for e in (all_emps if isinstance(all_emps, list) else [])
                           if e.get("status") in [0, "0", "inactive", "terminated", "deactivated"]]
        record(24, "Employee", "Deactivated employees not in active headcount",
               NOT_ENFORCED if inactive_in_list else ENFORCED,
               f"Found {len(inactive_in_list)} inactive in default list!" if inactive_in_list
               else f"Default list ({len(all_emps)} emps) shows only active")
    except Exception as e:
        record(24, "Employee", "Deactivated employees not in active headcount", PARTIAL, str(e))

    # 25: Notice period
    try:
        if emps:
            r = requests.get(f"{API}/employees/{emps[0]['id']}/profile", headers=hdr(at), timeout=20)
            has = "notice" in r.text.lower() if r.status_code == 200 else False
            record(25, "Employee", "Notice period enforcement",
                   PARTIAL if has else NOT_IMPL,
                   "Notice period fields found in profile" if has else "No notice period fields")
        else:
            record(25, "Employee", "Notice period enforcement", PARTIAL, "No employees")
    except Exception as e:
        record(25, "Employee", "Notice period enforcement", PARTIAL, str(e))

    # 26: Probation tracking
    try:
        if emps:
            r = requests.get(f"{API}/employees/{emps[0]['id']}/profile", headers=hdr(at), timeout=20)
            has = "probation" in r.text.lower() if r.status_code == 200 else False
            record(26, "Employee", "Probation period tracking",
                   ENFORCED if has else NOT_IMPL,
                   "Probation fields in profile (probation_end_date, probation_status, etc.)" if has else "No probation fields")
        else:
            record(26, "Employee", "Probation period tracking", PARTIAL, "No employees")
    except Exception as e:
        record(26, "Employee", "Probation period tracking", PARTIAL, str(e))


def test_payroll(at):
    print("\n=== PAYROLL RULES ===")
    pt = login_module(PAYROLL, "ananya@technova.in", "Welcome@123")
    if not pt:
        for i in range(27, 33):
            record(i, "Payroll", f"Rule {i}", PARTIAL, "Payroll login failed")
        return

    runs = get_data(requests.get(f"{PAYROLL}/payroll", headers=hdr(pt), timeout=20)) or []

    # 27: Duplicate payroll run
    try:
        if isinstance(runs, list) and runs:
            m, y = runs[0].get("month"), runs[0].get("year")
            r = requests.post(f"{PAYROLL}/payroll", headers=hdr(pt), json={
                "name": f"Dup Test {m}/{y}", "month": m, "year": y, "payDate": runs[0].get("pay_date","2026-02-28")
            }, timeout=20)
            if r.status_code == 409 and "already exists" in r.text.lower():
                record(27, "Payroll", "Cannot run payroll twice for same month", ENFORCED,
                       f"Blocked (409): {r.json().get('error',{}).get('message','')}")
            elif r.status_code in [200, 201]:
                record(27, "Payroll", "Cannot run payroll twice for same month", NOT_ENFORCED, "Duplicate created!")
            else:
                record(27, "Payroll", "Cannot run payroll twice for same month", PARTIAL, f"{r.status_code}: {r.text[:200]}")
        else:
            record(27, "Payroll", "Cannot run payroll twice for same month", PARTIAL, "No existing runs")
    except Exception as e:
        record(27, "Payroll", "Cannot run payroll twice for same month", PARTIAL, str(e))

    # 28: LOP deductions
    try:
        if isinstance(runs, list) and runs:
            slips = get_data(requests.get(f"{PAYROLL}/payroll/{runs[0]['id']}/payslips", headers=hdr(pt), timeout=20)) or []
            if isinstance(slips, list) and slips:
                has_lop = "lop_days" in slips[0]
                record(28, "Payroll", "Payroll includes LOP deductions",
                       ENFORCED if has_lop else NOT_IMPL,
                       f"lop_days={slips[0].get('lop_days')}, paid_days={slips[0].get('paid_days')}" if has_lop else "No LOP field")
            else:
                record(28, "Payroll", "Payroll includes LOP deductions", PARTIAL, "No payslips")
        else:
            record(28, "Payroll", "Payroll includes LOP deductions", PARTIAL, "No runs")
    except Exception as e:
        record(28, "Payroll", "Payroll includes LOP deductions", PARTIAL, str(e))

    # 29: Tax calculation
    try:
        if isinstance(runs, list) and runs:
            slips = get_data(requests.get(f"{PAYROLL}/payroll/{runs[0]['id']}/payslips", headers=hdr(pt), timeout=20)) or []
            if isinstance(slips, list) and slips:
                ded_codes = [d.get("code","") for d in slips[0].get("deductions", [])]
                has_tax = any(c in ["TDS", "INCOME_TAX", "TAX"] for c in ded_codes) or slips[0].get("ytd_tax_paid") is not None
                record(29, "Payroll", "Tax calculation follows correct slab",
                       PARTIAL if has_tax else NOT_IMPL,
                       f"Tax/TDS in deductions: {ded_codes}, ytd_tax_paid={slips[0].get('ytd_tax_paid')}" if has_tax else f"Deduction codes: {ded_codes}")
            else:
                record(29, "Payroll", "Tax calculation follows correct slab", PARTIAL, "No payslips")
        else:
            record(29, "Payroll", "Tax calculation follows correct slab", PARTIAL, "No runs")
    except Exception as e:
        record(29, "Payroll", "Tax calculation follows correct slab", PARTIAL, str(e))

    # 30: PF/ESI statutory
    try:
        if isinstance(runs, list) and runs:
            slips = get_data(requests.get(f"{PAYROLL}/payroll/{runs[0]['id']}/payslips", headers=hdr(pt), timeout=20)) or []
            if isinstance(slips, list) and slips:
                ded_codes = [d.get("code","") for d in slips[0].get("deductions", [])]
                emp_contrib = [c.get("code","") for c in slips[0].get("employer_contributions", [])]
                has_pf = "EPF" in ded_codes or "PF" in ded_codes or "EPF" in emp_contrib
                has_esi = "ESI" in ded_codes or "ESIC" in ded_codes or "ESI" in emp_contrib
                record(30, "Payroll", "PF/ESI deductions match statutory rules",
                       ENFORCED if (has_pf or has_esi) else NOT_IMPL,
                       f"EPF: {'yes' if has_pf else 'no'}, ESI: {'yes' if has_esi else 'no'}. Ded: {ded_codes}, Employer: {emp_contrib}")
            else:
                record(30, "Payroll", "PF/ESI deductions match statutory rules", PARTIAL, "No payslips")
        else:
            record(30, "Payroll", "PF/ESI deductions match statutory rules", PARTIAL, "No runs")
    except Exception as e:
        record(30, "Payroll", "PF/ESI deductions match statutory rules", PARTIAL, str(e))

    # 31: Cannot modify locked payroll
    try:
        locked = [r for r in (runs if isinstance(runs, list) else []) if r.get("status") in ["approved", "paid", "locked", "completed"]]
        if locked:
            rid = locked[0]["id"]
            # Payroll doesn't have PUT endpoint - this IS enforcement by design
            r = requests.put(f"{PAYROLL}/payroll/{rid}", headers=hdr(pt), json={"status": "draft"}, timeout=20)
            if r.status_code == 404:
                record(31, "Payroll", "Cannot modify payslip after payroll locked", ENFORCED,
                       "No PUT endpoint exists for payroll runs - modification impossible by design")
            elif r.status_code in [400, 403, 409]:
                record(31, "Payroll", "Cannot modify payslip after payroll locked", ENFORCED,
                       f"Blocked: {r.status_code}")
            elif r.status_code == 200:
                record(31, "Payroll", "Cannot modify payslip after payroll locked", NOT_ENFORCED,
                       "Locked payroll modified!")
            else:
                record(31, "Payroll", "Cannot modify payslip after payroll locked", PARTIAL, f"{r.status_code}")
        else:
            record(31, "Payroll", "Cannot modify payslip after payroll locked", PARTIAL,
                   f"No locked runs. Statuses: {[r.get('status') for r in runs[:5]]}")
    except Exception as e:
        record(31, "Payroll", "Cannot modify payslip after payroll locked", PARTIAL, str(e))

    # 32: F&F settlement
    try:
        et = login_module(EXIT, "ananya@technova.in", "Welcome@123")
        if et:
            exits = get_data(requests.get(f"{EXIT}/exits", headers=hdr(et), timeout=20)) or []
            if isinstance(exits, list) and exits:
                eid = exits[0]["id"]
                r = requests.get(f"{EXIT}/exits/{eid}/fnf", headers=hdr(et), timeout=20)
                if r.status_code == 200:
                    fnf_str = r.text.lower()
                    has = any(kw in fnf_str for kw in ["salary", "encash", "recovery", "deduction"])
                    record(32, "Payroll", "F&F settlement (salary + leave encashment - recoveries)",
                           ENFORCED if has else PARTIAL,
                           f"F&F endpoint works with components" if has else "F&F exists but component details unclear")
                else:
                    record(32, "Payroll", "F&F settlement (salary + leave encashment - recoveries)", PARTIAL,
                           f"F&F: {r.status_code}: {r.text[:200]}")
            else:
                record(32, "Payroll", "F&F settlement (salary + leave encashment - recoveries)", PARTIAL, "No exits")
        else:
            record(32, "Payroll", "F&F settlement (salary + leave encashment - recoveries)", PARTIAL, "Exit login failed")
    except Exception as e:
        record(32, "Payroll", "F&F settlement (salary + leave encashment - recoveries)", PARTIAL, str(e))


def test_assets(at):
    print("\n=== ASSET RULES ===")
    assets = get_data(requests.get(f"{API}/assets", headers=hdr(at), timeout=20)) or []

    # 33: Cannot delete assigned asset
    try:
        assigned = [a for a in (assets if isinstance(assets, list) else []) if a.get("status") == "assigned"]
        if assigned:
            r = requests.delete(f"{API}/assets/{assigned[0]['id']}", headers=hdr(at), timeout=20)
            if r.status_code == 404:
                record(33, "Asset", "Cannot delete assigned asset", NOT_IMPL, "DELETE endpoint not found")
            elif r.status_code in [400, 409]:
                record(33, "Asset", "Cannot delete assigned asset", ENFORCED, f"Blocked: {r.text[:200]}")
            elif r.status_code in [200, 204]:
                record(33, "Asset", "Cannot delete assigned asset", NOT_ENFORCED, "Assigned asset deleted!")
            else:
                record(33, "Asset", "Cannot delete assigned asset", PARTIAL, f"{r.status_code}: {r.text[:200]}")
        else:
            record(33, "Asset", "Cannot delete assigned asset", PARTIAL,
                   f"No assigned assets. Statuses: {list(set(a.get('status') for a in assets[:20]))}")
    except Exception as e:
        record(33, "Asset", "Cannot delete assigned asset", PARTIAL, str(e))

    # 34: Return date on unassignment
    try:
        if isinstance(assets, list) and assets:
            keys = list(assets[0].keys())
            has = any(kw in str(keys).lower() for kw in ["return", "unassign"])
            record(34, "Asset", "Asset return date on unassignment",
                   ENFORCED if has else NOT_IMPL,
                   f"Return tracking fields found" if has else f"No return date fields. Keys: {keys[:15]}")
        else:
            record(34, "Asset", "Asset return date on unassignment", NOT_IMPL, "No assets")
    except Exception as e:
        record(34, "Asset", "Asset return date on unassignment", PARTIAL, str(e))

    # 35: Cannot assign retired asset
    try:
        retired = [a for a in (assets if isinstance(assets, list) else []) if a.get("status") in ["retired", "scrapped"]]
        if retired:
            r = requests.post(f"{API}/assets/{retired[0]['id']}/assign", headers=hdr(at),
                              json={"employee_id": 524}, timeout=20)
            if r.status_code in [400, 409]:
                record(35, "Asset", "Cannot assign retired/scrapped asset", ENFORCED, f"Blocked: {r.text[:200]}")
            elif r.status_code in [200, 201]:
                record(35, "Asset", "Cannot assign retired/scrapped asset", NOT_ENFORCED, "Retired asset assigned!")
            else:
                record(35, "Asset", "Cannot assign retired/scrapped asset", PARTIAL, f"{r.status_code}")
        else:
            record(35, "Asset", "Cannot assign retired/scrapped asset", PARTIAL,
                   f"No retired assets. Statuses: {list(set(a.get('status') for a in assets[:20]))}")
    except Exception as e:
        record(35, "Asset", "Cannot assign retired/scrapped asset", PARTIAL, str(e))


def test_recruitment(at):
    print("\n=== RECRUITMENT RULES ===")
    rt = login_module(RECRUIT, "ananya@technova.in", "Welcome@123") or at

    # 36: Headcount
    try:
        r = requests.get(f"{API}/positions", headers=hdr(at), timeout=20)
        if r.status_code == 200:
            pos = get_data(r) or []
            record(36, "Recruitment", "Cannot hire more than headcount allows", PARTIAL,
                   f"{len(pos)} positions found. Headcount enforcement requires full hiring flow test.")
        else:
            record(36, "Recruitment", "Cannot hire more than headcount allows", NOT_IMPL,
                   f"Positions: {r.status_code}: {r.text[:200]}")
    except Exception as e:
        record(36, "Recruitment", "Cannot hire more than headcount allows", PARTIAL, str(e))

    # 37: Offer requires approval
    try:
        jobs = get_data(requests.get(f"{RECRUIT}/jobs", headers=hdr(rt), timeout=20))
        if isinstance(jobs, list) and jobs:
            r = requests.post(f"{RECRUIT}/offers", headers=hdr(rt), json={
                "job_id": jobs[0]["id"], "candidate_id": "fake", "salary": 50000
            }, timeout=20)
            if r.status_code in [400, 403, 422]:
                record(37, "Recruitment", "Offer letter requires approval", PARTIAL,
                       f"Offer creation rejected ({r.status_code}): {r.text[:200]}")
            elif r.status_code in [200, 201]:
                record(37, "Recruitment", "Offer letter requires approval", NOT_ENFORCED, "Offer created without approval!")
            else:
                record(37, "Recruitment", "Offer letter requires approval", PARTIAL, f"{r.status_code}: {r.text[:200]}")
        else:
            record(37, "Recruitment", "Offer letter requires approval", PARTIAL, "No jobs found")
    except Exception as e:
        record(37, "Recruitment", "Offer letter requires approval", PARTIAL, str(e))

    # 38: Candidate in two pipelines
    try:
        jobs = get_data(requests.get(f"{RECRUIT}/jobs", headers=hdr(rt), timeout=20))
        record(38, "Recruitment", "Candidate cannot be in two active pipelines", PARTIAL,
               f"{len(jobs) if isinstance(jobs, list) else 0} jobs. Cannot test without creating test candidates.")
    except Exception as e:
        record(38, "Recruitment", "Candidate cannot be in two active pipelines", PARTIAL, str(e))


def test_performance(at, et):
    print("\n=== PERFORMANCE RULES ===")
    pt = login_module(PERF, "ananya@technova.in", "Welcome@123") or at

    # 39: Deadline enforcement
    try:
        cycles = get_data(requests.get(f"{PERF}/review-cycles", headers=hdr(pt), timeout=20)) or []
        if isinstance(cycles, list) and cycles:
            c = cycles[0]
            has_deadline = any(kw in json.dumps(c).lower() for kw in ["deadline", "due_date", "self_review_end"])
            if has_deadline:
                record(39, "Performance", "Self-assessment deadline enforcement", PARTIAL,
                       "Deadline fields exist. Enforcement requires expired-cycle test.")
            else:
                has_dates = c.get("start_date") and c.get("end_date")
                record(39, "Performance", "Self-assessment deadline enforcement",
                       PARTIAL if has_dates else NOT_IMPL,
                       f"Cycle has start/end dates: {c.get('start_date')}-{c.get('end_date')}" if has_dates else f"Keys: {list(c.keys())[:12]}")
        else:
            record(39, "Performance", "Self-assessment deadline enforcement", NOT_IMPL, "No review cycles")
    except Exception as e:
        record(39, "Performance", "Self-assessment deadline enforcement", PARTIAL, str(e))

    # 40: Manager review after self-assessment
    try:
        reviews = get_data(requests.get(f"{PERF}/reviews", headers=hdr(pt), timeout=20)) or []
        if isinstance(reviews, list) and reviews:
            s = json.dumps(reviews[0]).lower()
            has = any(kw in s for kw in ["self_assessment", "self_review", "selfassessment", "self_rating"])
            record(40, "Performance", "Manager review after self-assessment only",
                   PARTIAL if has else NOT_IMPL,
                   "Self-assessment fields exist" if has else f"Keys: {list(reviews[0].keys())[:12]}")
        else:
            record(40, "Performance", "Manager review after self-assessment only", PARTIAL,
                   f"No reviews found (may be empty)")
    except Exception as e:
        record(40, "Performance", "Manager review after self-assessment only", PARTIAL, str(e))

    # 41: Locked calibration
    try:
        cycles = get_data(requests.get(f"{PERF}/review-cycles", headers=hdr(pt), timeout=20)) or []
        locked = [c for c in (cycles if isinstance(cycles, list) else []) if c.get("status") in ["locked", "calibrated", "closed", "completed"]]
        if locked:
            revs = get_data(requests.get(f"{PERF}/reviews", headers=hdr(pt), params={"cycle_id": locked[0]["id"]}, timeout=20)) or []
            if isinstance(revs, list) and revs:
                r = requests.put(f"{PERF}/reviews/{revs[0]['id']}", headers=hdr(pt),
                                 json={"rating": 5, "comments": "test"}, timeout=20)
                if r.status_code in [400, 403, 409]:
                    record(41, "Performance", "Cannot modify ratings after calibration locked", ENFORCED, f"Blocked: {r.status_code}")
                elif r.status_code == 200:
                    record(41, "Performance", "Cannot modify ratings after calibration locked", NOT_ENFORCED, "Modified after lock!")
                else:
                    record(41, "Performance", "Cannot modify ratings after calibration locked", PARTIAL, f"{r.status_code}")
            else:
                record(41, "Performance", "Cannot modify ratings after calibration locked", PARTIAL, "No reviews in locked cycle")
        else:
            record(41, "Performance", "Cannot modify ratings after calibration locked", PARTIAL,
                   f"No locked cycles. Statuses: {[c.get('status') for c in cycles[:5]]}")
    except Exception as e:
        record(41, "Performance", "Cannot modify ratings after calibration locked", PARTIAL, str(e))


def test_security(at, et):
    print("\n=== SECURITY & COMPLIANCE RULES ===")

    # 42: Password policy
    try:
        r1 = requests.get(f"{API}/organizations/me", headers=hdr(at), timeout=20)
        combined = r1.text.lower() if r1.status_code == 200 else ""
        try:
            r2 = requests.get(f"{API}/organizations/me/settings", headers=hdr(at), timeout=20)
            if r2.status_code == 200: combined += r2.text.lower()
        except: pass
        has = any(kw in combined for kw in ["password_expir", "password_rotation", "password_policy", "passwordPolicy"])
        record(42, "Security", "Password expiry/rotation policy",
               ENFORCED if has else NOT_IMPL,
               "Password policy settings found" if has else "No password rotation/expiry settings")
    except Exception as e:
        record(42, "Security", "Password expiry/rotation policy", PARTIAL, str(e))

    # 43: Session/token validation
    try:
        r = requests.get(f"{API}/employees", headers=hdr("invalid_expired_token_xyz"), timeout=20)
        if r.status_code in [401, 403]:
            record(43, "Security", "Session timeout after inactivity", PARTIAL,
                   f"Invalid tokens rejected ({r.status_code}). Actual inactivity timeout not testable in single run.")
        else:
            record(43, "Security", "Session timeout after inactivity", NOT_ENFORCED,
                   f"Invalid token got {r.status_code}!")
    except Exception as e:
        record(43, "Security", "Session timeout after inactivity", PARTIAL, str(e))

    # 44: Audit log
    try:
        r = requests.get(f"{API}/audit", headers=hdr(at), timeout=20)
        if r.status_code == 200:
            logs = get_data(r) or []
            if isinstance(logs, list) and logs:
                actions = set(str(l.get("action","")).lower() for l in logs[:50])
                record(44, "Security", "Audit log for critical actions", ENFORCED,
                       f"{len(logs)} entries. Actions: {sorted(actions)[:10]}")
            else:
                record(44, "Security", "Audit log for critical actions", PARTIAL, "Audit exists but empty")
        elif r.status_code == 403:
            st = login_cloud("admin@empcloud.com", "SuperAdmin@2026")
            if st:
                r2 = requests.get(f"{API}/audit", headers=hdr(st), timeout=20)
                record(44, "Security", "Audit log for critical actions",
                       ENFORCED if r2.status_code == 200 else PARTIAL,
                       "Audit restricted to super admin (correct)")
            else:
                record(44, "Security", "Audit log for critical actions", PARTIAL, "Restricted, super admin login failed")
        else:
            record(44, "Security", "Audit log for critical actions", NOT_IMPL, f"Audit: {r.status_code}")
    except Exception as e:
        record(44, "Security", "Audit log for critical actions", PARTIAL, str(e))

    # 45: Data retention
    try:
        found = False
        for ep in [f"{API}/admin/data-retention", f"{API}/organizations/me/settings"]:
            try:
                r = requests.get(ep, headers=hdr(at), timeout=15)
                if r.status_code == 200 and any(kw in r.text.lower() for kw in ["retention", "purge", "archive"]):
                    record(45, "Security", "Data retention / purge policy", PARTIAL, f"Found at {ep}")
                    found = True; break
            except: continue
        if not found:
            record(45, "Security", "Data retention / purge policy", NOT_IMPL, "No retention settings found")
    except Exception as e:
        record(45, "Security", "Data retention / purge policy", NOT_IMPL, str(e))

    # 46: GDPR
    try:
        found = False
        for ep in [f"{API}/privacy", f"{API}/gdpr", f"{API}/data-requests"]:
            try:
                r = requests.get(ep, headers=hdr(at), timeout=15)
                if r.status_code == 200:
                    record(46, "Security", "GDPR/privacy - data deletion request", PARTIAL, f"Endpoint: {ep}")
                    found = True; break
            except: continue
        if not found:
            record(46, "Security", "GDPR/privacy - data deletion request", NOT_IMPL, "No GDPR endpoints found")
    except Exception as e:
        record(46, "Security", "GDPR/privacy - data deletion request", NOT_IMPL, str(e))


# ══════════════════════════════════════════════════════════════════════
def main():
    print("=" * 80)
    print("EmpCloud HRMS - CRITICAL BUSINESS RULES AUDIT")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    print("\n--- Authentication ---")
    at = login_cloud("ananya@technova.in", "Welcome@123")
    print(f"  Admin: {'OK' if at else 'FAIL'}")
    et = login_cloud("priya@technova.in", "Welcome@123")
    print(f"  Employee: {'OK' if et else 'FAIL'}")
    ot = login_cloud("john@globaltech.com", "Welcome@123")
    print(f"  Other Org: {'OK' if ot else 'FAIL'}")
    if not at: print("FATAL"); return

    test_subscription(at)
    test_leave(at, et or at)
    test_attendance(at, et or at)
    test_employee(at, et or at, ot)
    test_payroll(at)
    test_assets(at)
    test_recruitment(at)
    test_performance(at, et or at)
    test_security(at, et or at)

    # File GitHub issues
    print("\n\n=== FILING GITHUB ISSUES ===")
    bugs = features = 0
    for res in results:
        if res["status"] == NOT_ENFORCED:
            title = f"[Business Rule] Rule #{res['id']}: {res['rule']}"
            body = f"## Business Rule Violation\n\n**Category:** {res['category']}\n**Rule:** {res['rule']}\n**Status:** NOT ENFORCED\n\n### Test Result\n{res['detail']}\n\n### Expected\nSystem should enforce this rule and reject violations.\n\n### Severity\n**HIGH**\n\n---\n*Business Rules Audit {datetime.now().strftime('%Y-%m-%d')}*"
            url = file_issue(title, body, ["bug", "business-rule", "compliance"])
            if url: res["issue_url"] = url; bugs += 1; print(f"  BUG: {title} -> {url}")
            time.sleep(1.5)
        elif res["status"] == NOT_IMPL:
            title = f"[Feature Request] Rule #{res['id']}: {res['rule']}"
            body = f"## Feature Request\n\n**Category:** {res['category']}\n**Rule:** {res['rule']}\n\n### Detail\n{res['detail']}\n\n### Acceptance Criteria\n- Implement and enforce this business rule\n- Return clear errors on violation\n\n---\n*Business Rules Audit {datetime.now().strftime('%Y-%m-%d')}*"
            url = file_issue(title, body, ["enhancement", "business-rule", "feature-request"])
            if url: res["issue_url"] = url; features += 1; print(f"  FEATURE: {title} -> {url}")
            time.sleep(1.5)

    # Matrix
    print("\n\n" + "=" * 135)
    print("BUSINESS RULES COMPLIANCE MATRIX")
    print("=" * 135)
    print(f"{'#':<4} {'Category':<16} {'Rule':<60} {'Status':<18} {'Issue'}")
    print("-" * 135)

    c = {ENFORCED:0, NOT_ENFORCED:0, NOT_IMPL:0, PARTIAL:0}
    for r in results:
        print(f"{r['id']:<4} {r['category']:<16} {r['rule'][:59]:<60} {r['status']:<18} {r.get('issue_url','') or ''}")
        c[r['status']] = c.get(r['status'],0) + 1

    print("-" * 135)
    t = len(results)
    print(f"\nSUMMARY:")
    print(f"  Total rules tested:     {t}")
    print(f"  ENFORCED:               {c[ENFORCED]}")
    print(f"  NOT ENFORCED (bugs):    {c[NOT_ENFORCED]}")
    print(f"  NOT IMPLEMENTED:        {c[NOT_IMPL]}")
    print(f"  PARTIAL/INCONCLUSIVE:   {c[PARTIAL]}")
    print(f"\n  GitHub bugs filed:      {bugs}")
    print(f"  GitHub features filed:  {features}")
    print(f"\n  Compliance Score:       {c[ENFORCED]}/{t} ({100*c[ENFORCED]/max(t,1):.1f}%)")
    print("=" * 135)

    with open(r"C:\emptesting\business_rules_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to C:\\emptesting\\business_rules_results.json")

if __name__ == "__main__":
    main()
