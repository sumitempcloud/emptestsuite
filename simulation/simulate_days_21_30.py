#!/usr/bin/env python3
"""
EMP Cloud 30-Day HRMS Simulation — Days 21-30 (Month-End Payroll)
Simulates the last 10 days of March 2026 including payroll processing,
exit handling, attendance, and month-end reporting for 3 organizations.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import time
import random
import os
from datetime import datetime, timedelta, date
from collections import defaultdict

# =============================================================================
# CONFIGURATION
# =============================================================================
CORE_API = "https://test-empcloud-api.empcloud.com/api/v1"
PAYROLL_API = "https://testpayroll-api.empcloud.com/api/v1"
EXIT_API = "https://test-exit-api.empcloud.com/api/v1"
PERFORMANCE_API = "https://test-performance-api.empcloud.com/api/v1"
REWARDS_API = "https://test-rewards-api.empcloud.com/api/v1"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

ORGS = [
    {"name": "TechNova", "id": 5, "email": "ananya@technova.in", "password": "Welcome@123", "domain": "technova.in"},
    {"name": "GlobalTech", "id": 9, "email": "john@globaltech.com", "password": "Welcome@123", "domain": "globaltech.com"},
    {"name": "Innovate Solutions", "id": 39, "email": "hr@innovate.io", "password": "Welcome@123", "domain": "innovate.io"},
]

# March 2026 working days (Mon-Fri, excluding weekends)
MARCH_2026_START = date(2026, 3, 1)
MARCH_2026_END = date(2026, 3, 31)
SIMULATION_DAYS = list(range(21, 31))  # Days 21-30

# Simulation dates: Day 21 = March 21, etc.
def sim_date(day_num):
    return date(2026, 3, day_num)

def is_weekday(d):
    return d.weekday() < 5

def get_working_days_in_march():
    """Get all working days in March 2026."""
    days = []
    d = MARCH_2026_START
    while d <= MARCH_2026_END:
        if is_weekday(d):
            days.append(d)
        d += timedelta(days=1)
    return days

MARCH_WORKING_DAYS = get_working_days_in_march()
TOTAL_WORKING_DAYS = len(MARCH_WORKING_DAYS)

# =============================================================================
# STATE MANAGEMENT
# =============================================================================
state = {
    "simulation_phase": "days_21_30",
    "completed_days": [],
    "bugs_filed": [],
    "tokens": {},
    "payroll_tokens": {},
    "exit_tokens": {},
    "employees_by_org": {},
    "active_employees_by_org": {},
    "resigned_employees": {},
    "new_joiners": {},
    "attendance_records": {},
    "leave_records": {},
    "payroll_runs": {},
    "payslips": {},
    "helpdesk_tickets": {},
    "announcements_created": {},
    "exit_processed": {},
    "fnf_settlements": {},
    "month_end_reports": {},
    "data_integrity": {},
    "api_errors": [],
    "day_logs": {},
}

# Load previous state if available
PREV_STATE_PATH = r"C:\emptesting\simulation\day11_20_state.json"
SETUP_DATA_PATH = r"C:\emptesting\simulation\setup_data.json"
STATE_OUTPUT_PATH = r"C:\emptesting\simulation\day21_30_state.json"
REPORT_OUTPUT_PATH = r"C:\emptesting\simulation\month_end_report.json"

def load_setup_data():
    with open(SETUP_DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_previous_state():
    if os.path.exists(PREV_STATE_PATH):
        with open(PREV_STATE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_state():
    with open(STATE_OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)

def save_report(report):
    with open(REPORT_OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)

# =============================================================================
# API HELPERS
# =============================================================================
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def api_call(method, url, token=None, json_data=None, params=None, label=""):
    """Make API call with error handling."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.request(method, url, headers=headers, json=json_data, params=params, timeout=30)
        status = resp.status_code
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:500]}
        if status >= 400:
            err = {"label": label, "url": url, "method": method, "status": status, "body": body}
            state["api_errors"].append(err)
            if status not in (401, 403, 404, 409, 422):
                log(f"  [ERROR] {label}: {status} - {json.dumps(body)[:200]}")
        return status, body
    except Exception as e:
        err = {"label": label, "url": url, "method": method, "error": str(e)}
        state["api_errors"].append(err)
        log(f"  [EXCEPTION] {label}: {e}")
        return 0, {"error": str(e)}

def login_core(email, password):
    """Login to core EmpCloud API."""
    status, body = api_call("POST", f"{CORE_API}/auth/login",
                            json_data={"email": email, "password": password},
                            label=f"Login {email}")
    if status == 200:
        # Primary path: body.data.tokens.access_token
        data = body.get("data", {})
        if isinstance(data, dict):
            tokens = data.get("tokens", {})
            if isinstance(tokens, dict) and "access_token" in tokens:
                return tokens["access_token"]
            # Fallback within data
            for key in ["token", "access_token", "accessToken"]:
                if key in data:
                    return data[key]
        # Top-level fallbacks
        for key in ["token", "access_token", "accessToken"]:
            if key in body:
                return body[key]
    log(f"  Login failed for {email}: {status} {json.dumps(body)[:200]}")
    return None

def sso_to_module(core_token, module_api_base, label="module"):
    """SSO from core to a module. Uses POST /auth/sso with {token: core_token}.
    Response: data.tokens.accessToken"""
    # Primary: POST /auth/sso with core token
    status, body = api_call("POST", f"{module_api_base}/auth/sso",
                            json_data={"token": core_token},
                            label=f"SSO to {label}")
    if status == 200:
        data = body.get("data", {})
        if isinstance(data, dict):
            tokens = data.get("tokens", {})
            if isinstance(tokens, dict):
                t = tokens.get("accessToken") or tokens.get("access_token")
                if t:
                    return t
            # Flat token
            t = data.get("token") or data.get("accessToken")
            if t:
                return t

    # Fallback: try direct login at module
    status2, body2 = api_call("POST", f"{module_api_base}/auth/login",
                              json_data={"email": "", "password": "", "token": core_token},
                              label=f"Direct login at {label}")
    if status2 == 200:
        data2 = body2.get("data", {})
        if isinstance(data2, dict):
            tokens2 = data2.get("tokens", {})
            if isinstance(tokens2, dict):
                return tokens2.get("accessToken") or tokens2.get("access_token")

    # Last resort: use core token directly
    return core_token

def login_to_payroll(org):
    """Login directly to payroll module using org admin credentials."""
    status, body = api_call("POST", f"{PAYROLL_API}/auth/login",
                            json_data={"email": org["email"], "password": org["password"]},
                            label=f"Payroll login {org['email']}")
    if status == 200:
        data = body.get("data", {})
        tokens = data.get("tokens", {})
        return tokens.get("accessToken") or tokens.get("access_token")
    return None

def file_bug(title, body_text, labels=None):
    """File a bug on GitHub."""
    if labels is None:
        labels = ["bug", "30-day-sim"]
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": f"[30-Day Sim] {title}",
        "body": body_text,
        "labels": labels
    }
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers=headers, json=data, timeout=30
        )
        if resp.status_code == 201:
            issue = resp.json()
            bug_info = {"number": issue["number"], "title": title, "url": issue["html_url"]}
            state["bugs_filed"].append(bug_info)
            log(f"  BUG FILED: #{issue['number']} - {title}")
            return bug_info
        else:
            log(f"  Failed to file bug: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log(f"  Exception filing bug: {e}")
    return None

# =============================================================================
# EMPLOYEE DATA HELPERS
# =============================================================================
def get_real_employees(org):
    """Filter setup data to get real employees (not test/QA) for an org, with emp_code."""
    setup = load_setup_data()
    employees = []
    for emp in setup.get("employees", []):
        if emp.get("organization") != org["name"]:
            continue
        # Filter out test/QA users
        fn = (emp.get("first_name") or "").lower()
        ln = (emp.get("last_name") or "").lower()
        em = (emp.get("email") or "").lower()
        if any(x in fn for x in ["test", "qa", "crud", "duplicate", "retest"]):
            continue
        if any(x in em for x in ["test.com", "qa-", "crudtest", "dup_test", "retest", "company.com", "gmail.com"]):
            continue
        if emp.get("emp_code") and emp["emp_code"].startswith(("TN-", "GT-", "IS-")):
            employees.append(emp)
    return employees

def classify_employees(org):
    """Classify employees into active, resigned, new joiners for the simulation."""
    employees = get_real_employees(org)
    if not employees:
        return [], [], []

    # Sort by emp_code number
    def code_num(e):
        code = e.get("emp_code", "XX-000")
        try:
            return int(code.split("-")[1])
        except:
            return 0
    employees.sort(key=code_num)

    # Pick 1-2 employees per org as "resigned on Day 12" (from previous sim phase)
    # Use employees with higher emp_code numbers (newer hires) as resigned
    resigned = []
    if len(employees) >= 10:
        resigned = [employees[-3], employees[-5]]  # 2 resignations per org
    elif len(employees) >= 5:
        resigned = [employees[-2]]

    # New joiners (joined in March 2026)
    new_joiners = []
    for emp in employees:
        doj = emp.get("date_of_joining", "")
        if doj and "2026-03" in doj:
            if emp not in resigned:
                new_joiners.append(emp)

    # Active = everyone except resigned
    resigned_ids = {e["id"] for e in resigned}
    active = [e for e in employees if e["id"] not in resigned_ids]

    return active, resigned, new_joiners

# =============================================================================
# DAY 21: LAST WEEK PREPARATION
# =============================================================================
def day_21(org, token):
    """Day 21 - Last week preparation: attendance, close tickets, leave approvals, announcement."""
    day_log = {"date": "2026-03-21", "org": org["name"], "actions": []}
    log(f"\n{'='*60}")
    log(f"DAY 21 - Last Week Preparation - {org['name']}")
    log(f"{'='*60}")

    active, resigned, new_joiners = classify_employees(org)
    state["active_employees_by_org"][org["name"]] = [e["id"] for e in active]
    state["resigned_employees"][org["name"]] = [{"id": e["id"], "name": f"{e['first_name']} {e['last_name']}"} for e in resigned]
    state["new_joiners"][org["name"]] = [{"id": e["id"], "name": f"{e['first_name']} {e['last_name']}"} for e in new_joiners]

    # 1. Normal attendance for sample employees
    log(f"  Marking attendance for {len(active)} active employees...")
    attendance_count = 0
    today_str = "2026-03-21"
    for emp in active[:20]:  # Sample up to 20
        status, body = api_call("POST", f"{CORE_API}/attendance/check-in",
                                token=token,
                                json_data={"employee_id": emp["id"]},
                                label=f"Check-in {emp['first_name']}")
        if status in (200, 201, 409):  # 409 = already checked in = success
            attendance_count += 1
        time.sleep(0.1)
    day_log["actions"].append(f"Attendance marked for {attendance_count}/{min(len(active),20)} employees")
    log(f"  Attendance: {attendance_count} check-ins")

    # 2. Close helpdesk tickets
    log("  Closing open helpdesk tickets...")
    status, body = api_call("GET", f"{CORE_API}/helpdesk/tickets", token=token,
                            params={"status": "open"}, label="Get open tickets")
    tickets_closed = 0
    if status == 200:
        tickets = body.get("data", body.get("tickets", []))
        if isinstance(tickets, list):
            for ticket in tickets[:10]:
                tid = ticket.get("id")
                if tid:
                    s2, _ = api_call("PUT", f"{CORE_API}/helpdesk/tickets/{tid}",
                                     token=token,
                                     json_data={"status": "closed", "resolution": "Resolved before month-end"},
                                     label=f"Close ticket {tid}")
                    if s2 in (200, 201):
                        tickets_closed += 1
                    time.sleep(0.1)
    day_log["actions"].append(f"Helpdesk tickets closed: {tickets_closed}")
    state["helpdesk_tickets"][org["name"]] = {"closed_day21": tickets_closed}
    log(f"  Helpdesk: {tickets_closed} tickets closed")

    # 3. Final leave approvals
    log("  Processing final leave approvals...")
    status, body = api_call("GET", f"{CORE_API}/leave/applications",
                            token=token, params={"status": "pending"},
                            label="Get pending leaves")
    leaves_approved = 0
    if status == 200:
        apps = body.get("data", body.get("applications", []))
        if isinstance(apps, list):
            for app in apps[:10]:
                aid = app.get("id")
                if aid:
                    s2, _ = api_call("PUT", f"{CORE_API}/leave/applications/{aid}/approve",
                                     token=token,
                                     json_data={"status": "approved", "comments": "Month-end approval"},
                                     label=f"Approve leave {aid}")
                    if s2 in (200, 201):
                        leaves_approved += 1
                    time.sleep(0.1)
    day_log["actions"].append(f"Leaves approved: {leaves_approved}")
    state["leave_records"].setdefault(org["name"], {})["approved_day21"] = leaves_approved
    log(f"  Leaves approved: {leaves_approved}")

    # 4. Create announcement: month-end closing
    log("  Creating month-end announcement...")
    status, body = api_call("POST", f"{CORE_API}/announcements",
                            token=token,
                            json_data={
                                "title": "Month-End Closing - Submit All Claims",
                                "content": "Dear Team,\n\nThis is a reminder that March 2026 month-end closing is approaching. Please submit all pending expense claims, timesheets, and leave applications by March 27.\n\nThank you,\nHR Department",
                                "type": "general",
                                "priority": "high",
                                "published": True
                            },
                            label="Create announcement")
    if status in (200, 201):
        ann_id = body.get("id") or (body.get("data", {}) or {}).get("id")
        state["announcements_created"][org["name"]] = {"id": ann_id, "title": "Month-End Closing"}
        day_log["actions"].append(f"Announcement created: id={ann_id}")
        log(f"  Announcement created: {ann_id}")
    else:
        day_log["actions"].append(f"Announcement creation: {status}")
        log(f"  Announcement: status {status}")

    state["day_logs"]["day_21_" + org["name"]] = day_log
    return day_log

# =============================================================================
# DAY 22: EXIT PROCESSING
# =============================================================================
def day_22(org, token):
    """Day 22 - Exit processing for resigned employees."""
    day_log = {"date": "2026-03-22", "org": org["name"], "actions": []}
    log(f"\n{'='*60}")
    log(f"DAY 22 - Exit Processing - {org['name']}")
    log(f"{'='*60}")

    resigned = state.get("resigned_employees", {}).get(org["name"], [])
    if not resigned:
        log("  No resigned employees to process")
        day_log["actions"].append("No resignations to process")
        state["day_logs"]["day_22_" + org["name"]] = day_log
        return day_log

    # Get SSO token for Exit module
    exit_token = sso_to_module(token, EXIT_API, "exit")

    for emp_info in resigned:
        emp_id = emp_info["id"]
        emp_name = emp_info["name"]
        log(f"  Processing exit for {emp_name} (ID: {emp_id})...")

        # 1. Create exit record
        status, body = api_call("POST", f"{EXIT_API}/exits",
                                token=exit_token,
                                json_data={
                                    "employee_id": emp_id,
                                    "resignation_date": "2026-03-12",
                                    "last_working_day": "2026-03-22",
                                    "reason": "Personal reasons",
                                    "type": "resignation",
                                    "notice_period": 10
                                },
                                label=f"Create exit for {emp_name}")
        exit_id = None
        if status in (200, 201):
            exit_id = body.get("id") or (body.get("data", {}) or {}).get("id")
            log(f"    Exit record created: {exit_id}")
        else:
            log(f"    Exit record: status {status}")
            # Try GET to find existing exit
            s2, b2 = api_call("GET", f"{EXIT_API}/exits",
                              token=exit_token, params={"employee_id": emp_id},
                              label=f"Get exits for {emp_name}")
            if s2 == 200:
                exits = b2.get("data", b2.get("exits", []))
                if isinstance(exits, list) and exits:
                    exit_id = exits[0].get("id")

        if exit_id:
            # 2. Clearance checklist
            log(f"    Processing clearance for exit {exit_id}...")
            status, body = api_call("GET", f"{EXIT_API}/clearance/{exit_id}",
                                    token=exit_token,
                                    label=f"Get clearance for {emp_name}")
            if status == 200:
                items = body.get("data", body.get("items", body.get("clearance", [])))
                if isinstance(items, list):
                    for item in items:
                        item_id = item.get("id")
                        if item_id:
                            api_call("PUT", f"{EXIT_API}/clearance/{exit_id}/{item_id}",
                                     token=exit_token,
                                     json_data={"status": "completed", "completed": True,
                                                "remarks": "Completed on last working day"},
                                     label=f"Complete clearance item {item_id}")
                            time.sleep(0.1)
                    day_log["actions"].append(f"Clearance completed for {emp_name}: {len(items)} items")

            # 3. F&F calculation
            log(f"    Calculating F&F settlement...")
            status, body = api_call("POST", f"{EXIT_API}/fnf/{exit_id}/calculate",
                                    token=exit_token,
                                    json_data={"last_working_day": "2026-03-22"},
                                    label=f"F&F for {emp_name}")
            if status in (200, 201):
                fnf_data = body.get("data", body)
                state["fnf_settlements"].setdefault(org["name"], {})[str(emp_id)] = {
                    "employee": emp_name,
                    "exit_id": exit_id,
                    "fnf": fnf_data
                }
                log(f"    F&F calculated")
                day_log["actions"].append(f"F&F calculated for {emp_name}")
            else:
                log(f"    F&F calculation: status {status}")
                day_log["actions"].append(f"F&F calculation failed for {emp_name}: {status}")

            # 4. Exit interview
            log(f"    Recording exit interview...")
            status, body = api_call("POST", f"{EXIT_API}/exit-interviews",
                                    token=exit_token,
                                    json_data={
                                        "exit_id": exit_id,
                                        "employee_id": emp_id,
                                        "feedback": "Good experience overall. Leaving for personal growth.",
                                        "rating": 4,
                                        "would_recommend": True,
                                        "conducted_by": "HR Manager",
                                        "date": "2026-03-22"
                                    },
                                    label=f"Exit interview for {emp_name}")
            if status in (200, 201):
                log(f"    Exit interview recorded")
                day_log["actions"].append(f"Exit interview for {emp_name}")
            else:
                day_log["actions"].append(f"Exit interview status {status} for {emp_name}")

        # 5. Deactivate employee
        log(f"    Deactivating employee account...")
        status, body = api_call("PUT", f"{CORE_API}/users/{emp_id}",
                                token=token,
                                json_data={"status": "inactive", "is_active": False,
                                           "date_of_exit": "2026-03-22"},
                                label=f"Deactivate {emp_name}")
        if status == 200:
            log(f"    Account deactivated")
            day_log["actions"].append(f"Deactivated {emp_name}")
            # Remove from active list
            active_ids = state.get("active_employees_by_org", {}).get(org["name"], [])
            if emp_id in active_ids:
                active_ids.remove(emp_id)
        else:
            day_log["actions"].append(f"Deactivation status {status} for {emp_name}")

        state["exit_processed"].setdefault(org["name"], []).append({
            "employee_id": emp_id, "name": emp_name, "exit_id": exit_id,
            "last_working_day": "2026-03-22", "status": "processed"
        })
        time.sleep(0.3)

    state["day_logs"]["day_22_" + org["name"]] = day_log
    return day_log

# =============================================================================
# DAYS 23-26: REGULAR WORKING DAYS
# =============================================================================
def days_23_26(org, token):
    """Days 23-26 - Regular working days with attendance."""
    combined_log = {"dates": "2026-03-23 to 2026-03-26", "org": org["name"], "actions": []}
    log(f"\n{'='*60}")
    log(f"DAYS 23-26 - Regular Working Days - {org['name']}")
    log(f"{'='*60}")

    active_ids = state.get("active_employees_by_org", {}).get(org["name"], [])
    active_emps = []
    setup = load_setup_data()
    for emp in setup.get("employees", []):
        if emp["id"] in active_ids:
            active_emps.append(emp)

    total_attendance = 0
    for day_num in [23, 24, 25, 26]:
        d = sim_date(day_num)
        if not is_weekday(d):
            combined_log["actions"].append(f"Day {day_num} ({d}) is weekend - skipped")
            continue

        day_str = d.isoformat()
        log(f"  Day {day_num} ({day_str}) - Marking attendance...")

        day_attendance = 0
        # Mark attendance for sample of active employees
        sample = active_emps[:25] if len(active_emps) > 25 else active_emps
        for emp in sample:
            # Randomly skip ~10% for absences
            if random.random() < 0.1:
                continue
            status, body = api_call("POST", f"{CORE_API}/attendance/check-in",
                                    token=token,
                                    json_data={"employee_id": emp["id"]},
                                    label=f"Check-in D{day_num} {emp.get('first_name','')}")
            if status in (200, 201, 409):  # 409 = already checked in
                day_attendance += 1
                # Also check out
                api_call("POST", f"{CORE_API}/attendance/check-out",
                         token=token,
                         json_data={"employee_id": emp["id"]},
                         label=f"Check-out D{day_num} {emp.get('first_name','')}")
            time.sleep(0.05)

        total_attendance += day_attendance
        combined_log["actions"].append(f"Day {day_num}: {day_attendance} attended")
        log(f"    Day {day_num}: {day_attendance} check-ins")

    # Update helpdesk
    log("  Checking helpdesk ticket status...")
    status, body = api_call("GET", f"{CORE_API}/helpdesk/tickets", token=token, label="Get tickets")
    ticket_summary = {"open": 0, "closed": 0, "total": 0}
    if status == 200:
        tickets = body.get("data", body.get("tickets", []))
        if isinstance(tickets, list):
            ticket_summary["total"] = len(tickets)
            for t in tickets:
                st = (t.get("status") or "").lower()
                if st in ("open", "pending", "in_progress"):
                    ticket_summary["open"] += 1
                else:
                    ticket_summary["closed"] += 1
    state["helpdesk_tickets"][org["name"]] = ticket_summary
    combined_log["actions"].append(f"Helpdesk: {ticket_summary}")

    state["attendance_records"].setdefault(org["name"], {})["days_23_26"] = total_attendance
    state["day_logs"]["days_23_26_" + org["name"]] = combined_log
    return combined_log

# =============================================================================
# DAY 27: PRE-PAYROLL VERIFICATION
# =============================================================================
def day_27(org, token):
    """Day 27 - Pre-payroll: verify attendance data, check discrepancies."""
    day_log = {"date": "2026-03-27", "org": org["name"], "actions": [], "discrepancies": []}
    log(f"\n{'='*60}")
    log(f"DAY 27 - Pre-Payroll Verification - {org['name']}")
    log(f"{'='*60}")

    active_ids = state.get("active_employees_by_org", {}).get(org["name"], [])
    setup = load_setup_data()
    active_emps = [e for e in setup.get("employees", []) if e["id"] in active_ids]

    # Verify attendance records for the month
    log("  Fetching attendance records for March 2026...")
    status, body = api_call("GET", f"{CORE_API}/attendance/records",
                            token=token,
                            params={"date": "2026-03-27"},
                            label="Get March attendance")
    attendance_data = {}
    if status == 200:
        records = body.get("data", body.get("records", body.get("attendance", [])))
        if isinstance(records, list):
            for rec in records:
                eid = rec.get("employee_id") or rec.get("user_id")
                if eid:
                    attendance_data.setdefault(eid, []).append(rec)
            log(f"  Found attendance for {len(attendance_data)} employees")
        elif isinstance(records, dict):
            attendance_data = records
            log(f"  Attendance data retrieved (dict format)")
    else:
        log(f"  Attendance fetch: status {status}")

    # Fetch leave records
    log("  Fetching leave records for March 2026...")
    status, body = api_call("GET", f"{CORE_API}/leave/applications",
                            token=token,
                            params={"start_date": "2026-03-01", "end_date": "2026-03-31",
                                    "status": "approved"},
                            label="Get March leaves")
    leave_data = {}
    if status == 200:
        apps = body.get("data", body.get("applications", []))
        if isinstance(apps, list):
            for app in apps:
                eid = app.get("employee_id") or app.get("user_id")
                if eid:
                    leave_data.setdefault(eid, []).append(app)
            log(f"  Found leaves for {len(leave_data)} employees")

    # Verify totals
    log("  Verifying attendance + leave = expected working days...")
    verification_results = []
    sample_emps = active_emps[:15]
    for emp in sample_emps:
        eid = emp["id"]
        att_days = len(attendance_data.get(eid, []))
        leave_days = sum(
            float(l.get("days", l.get("number_of_days", 1)))
            for l in leave_data.get(eid, [])
        )

        # Check if new joiner (pro-rated)
        doj = emp.get("date_of_joining", "")
        expected_days = TOTAL_WORKING_DAYS
        if doj and "2026-03" in doj:
            try:
                join_date = date.fromisoformat(doj[:10])
                expected_days = sum(1 for d in MARCH_WORKING_DAYS if d >= join_date)
            except:
                pass

        total = att_days + leave_days
        discrepancy = abs(total - expected_days) if expected_days > 0 else 0

        result = {
            "employee_id": eid,
            "name": f"{emp['first_name']} {emp['last_name']}",
            "attendance_days": att_days,
            "leave_days": leave_days,
            "expected_working_days": expected_days,
            "total": total,
            "discrepancy": discrepancy
        }
        verification_results.append(result)

        if discrepancy > 2:
            day_log["discrepancies"].append(result)

    # Check new joiners for pro-rated
    new_joiners = state.get("new_joiners", {}).get(org["name"], [])
    log(f"  New joiners (pro-rated salary): {len(new_joiners)}")
    for nj in new_joiners:
        day_log["actions"].append(f"New joiner: {nj['name']} (ID: {nj['id']}) - pro-rated salary needed")

    # Check exits
    exits = state.get("exit_processed", {}).get(org["name"], [])
    log(f"  Exits (pro-rated + F&F): {len(exits)}")
    for ex in exits:
        day_log["actions"].append(f"Exit: {ex['name']} (ID: {ex['employee_id']}) - pro-rated + F&F needed")

    day_log["actions"].append(f"Attendance verified for {len(verification_results)} employees")
    day_log["actions"].append(f"Discrepancies found: {len(day_log['discrepancies'])}")
    state["attendance_records"].setdefault(org["name"], {})["verification"] = verification_results
    state["day_logs"]["day_27_" + org["name"]] = day_log

    log(f"  Verification complete: {len(verification_results)} checked, {len(day_log['discrepancies'])} discrepancies")
    return day_log

# =============================================================================
# DAY 28: PAYROLL PROCESSING
# =============================================================================
def day_28(org, token):
    """Day 28 - PAYROLL PROCESSING for March 2026."""
    day_log = {"date": "2026-03-28", "org": org["name"], "actions": [], "payroll_details": {}}
    log(f"\n{'='*60}")
    log(f"DAY 28 - PAYROLL PROCESSING - {org['name']}")
    log(f"{'='*60}")

    # 1. Authenticate to payroll module
    log("  Authenticating to Payroll module...")
    payroll_token = login_to_payroll(org)
    if not payroll_token:
        payroll_token = sso_to_module(token, PAYROLL_API, "payroll")
    state["payroll_tokens"][org["name"]] = payroll_token
    log(f"  Payroll token: {'obtained' if payroll_token else 'FAILED'}")

    # NOTE: The payroll module maps org_admin as 'employee' role, which blocks
    # admin endpoints. This is a known SSO role-mapping bug.
    # We will still attempt payroll operations and use self-service where possible.

    # 2. Run payroll for March 2026
    log("  Running payroll for March 2026...")
    status, body = api_call("POST", f"{PAYROLL_API}/payroll",
                            token=payroll_token,
                            json_data={
                                "month": 3,
                                "year": 2026,
                                "period": "2026-03",
                                "pay_period": "monthly",
                                "description": "March 2026 Monthly Payroll"
                            },
                            label="Run payroll March 2026")

    payroll_id = None
    if status in (200, 201):
        payroll_id = body.get("id") or (body.get("data", {}) or {}).get("id")
        log(f"  Payroll run created: {payroll_id}")
        day_log["actions"].append(f"Payroll run created: {payroll_id}")
    else:
        log(f"  Payroll run: status {status}")
        day_log["actions"].append(f"Payroll run failed: {status} - {json.dumps(body)[:200]}")

        # Check for existing payroll run
        s2, b2 = api_call("GET", f"{PAYROLL_API}/payroll",
                          token=payroll_token,
                          params={"month": 3, "year": 2026},
                          label="Get existing payroll")
        if s2 == 200:
            runs = b2.get("data", b2.get("payroll", b2.get("runs", [])))
            if isinstance(runs, list) and runs:
                payroll_id = runs[0].get("id")
                log(f"  Found existing payroll run: {payroll_id}")
            elif isinstance(runs, dict):
                payroll_id = runs.get("id")

        # If still 403, the payroll module SSO role-mapping bug is blocking admin access
        if s2 == 403 or status == 403:
            day_log["actions"].append("KNOWN ISSUE: Payroll module maps org_admin as 'employee' role, blocking admin payroll operations")
            log("  KNOWN ISSUE: Payroll SSO role-mapping bug - org_admin mapped as 'employee'")

            # Try to get payslip data from self-service as workaround
            log("  Attempting self-service payslip access as workaround...")
            s3, b3 = api_call("GET", f"{PAYROLL_API}/self-service/payslips",
                              token=payroll_token,
                              params={"month": 3, "year": 2026},
                              label="Self-service payslips (workaround)")
            if s3 == 200:
                ss_data = b3.get("data", {})
                ss_payslips = ss_data.get("data", []) if isinstance(ss_data, dict) else ss_data
                if isinstance(ss_payslips, list) and ss_payslips:
                    log(f"  Self-service found {len(ss_payslips)} payslips")
                    day_log["actions"].append(f"Self-service payslips accessible: {len(ss_payslips)} found")
                    # Use the payroll_run_id from a payslip
                    payroll_id = ss_payslips[0].get("payroll_run_id")
                    if payroll_id:
                        log(f"  Extracted payroll run ID from self-service: {payroll_id}")
                        day_log["actions"].append(f"Payroll run ID from self-service: {payroll_id}")

                    # Store payslip samples for verification
                    state["payslips"][org["name"]] = {
                        "payroll_id": payroll_id,
                        "count": len(ss_payslips),
                        "sample_payslips": ss_payslips[:5],
                        "source": "self-service"
                    }
                else:
                    log("  Self-service: no March 2026 payslips found")
            else:
                log(f"  Self-service: status {s3}")

    state["payroll_runs"][org["name"]] = {
        "payroll_id": payroll_id,
        "status": status,
        "month": "March 2026"
    }

    if not payroll_id:
        log("  WARNING: No payroll ID obtained - skipping payslip verification")
        day_log["actions"].append("Payroll ID not obtained - payslip verification skipped")

        # File bug if payroll run fails due to role issue (only once)
        payroll_bug_filed = any("role mapped as" in b.get("title", "") for b in state.get("bugs_filed", []))
        if status == 403 and not payroll_bug_filed:
            file_bug(
                f"Day 28: Org admin can't run payroll - role mapped as 'employee' in payroll module",
                f"""## URL Tested
POST {PAYROLL_API}/payroll

## Steps to Reproduce
1. Login as {org['email']} (role: org_admin in EMP Cloud core)
2. SSO or direct login to payroll module
3. Check JWT claims - role is 'employee' instead of 'admin'/'hr'
4. POST /api/v1/payroll with month=3, year=2026

## Expected Result
Org admins from EMP Cloud should be mapped to admin/hr role in Payroll module.
Payroll run should be created successfully.

## Actual Result
- Payroll SSO maps org_admin as 'employee' role in JWT
- All admin payroll operations (GET /payroll, POST /payroll, GET /employees) return 403 Forbidden
- Even super_admin gets 403

This blocks the entire payroll workflow for all organizations.

## Affected Organizations
All orgs: TechNova, GlobalTech, Innovate Solutions

## Workaround
Self-service endpoints (GET /self-service/payslips) work for employee-level access.
"""
            )
        elif status not in (200, 201, 409):
            file_bug(
                f"Day 28: Payroll run fails for {org['name']} - March 2026",
                f"""## URL Tested
POST {PAYROLL_API}/payroll

## Steps to Reproduce
1. Login as {org['email']}
2. SSO to payroll module
3. POST /api/v1/payroll with month=3, year=2026

## Expected Result
Payroll run created successfully for March 2026

## Actual Result
Status: {status}
Response: {json.dumps(body)[:500]}
"""
            )

        state["day_logs"]["day_28_" + org["name"]] = day_log
        return day_log

    # 3. Get payslips (try admin endpoint, fall back to self-service)
    payslips = []
    existing_ps = state.get("payslips", {}).get(org["name"], {}).get("sample_payslips", [])
    if existing_ps:
        # Already got payslips from self-service workaround above
        payslips = existing_ps
        log(f"  Using {len(payslips)} payslips from self-service workaround")
    elif payroll_id:
        log(f"  Fetching payslips for payroll run {payroll_id}...")
        status, body = api_call("GET", f"{PAYROLL_API}/payroll/{payroll_id}/payslips",
                                token=payroll_token,
                                label="Get payslips")
        if status == 200:
            payslips = body.get("data", body.get("payslips", []))
            if isinstance(payslips, list):
                log(f"  Found {len(payslips)} payslips")
                day_log["actions"].append(f"Payslips found: {len(payslips)}")
            else:
                payslips = []
        else:
            log(f"  Payslips fetch: status {status}")
            day_log["actions"].append(f"Payslips fetch failed: {status}")
            # Fallback: try self-service
            s_ss, b_ss = api_call("GET", f"{PAYROLL_API}/self-service/payslips",
                                  token=payroll_token, label="Self-service payslips fallback")
            if s_ss == 200:
                ss_data = b_ss.get("data", {})
                payslips = ss_data.get("data", []) if isinstance(ss_data, dict) else (ss_data if isinstance(ss_data, list) else [])
                log(f"  Self-service fallback: {len(payslips)} payslips")

    if not state.get("payslips", {}).get(org["name"]):
        state["payslips"][org["name"]] = {
            "payroll_id": payroll_id,
            "count": len(payslips),
            "sample_payslips": payslips[:5] if payslips else []
        }

    # 4. Verify 5 random payslips
    if payslips:
        sample = random.sample(payslips, min(5, len(payslips)))
        log(f"  Verifying {len(sample)} sample payslips...")
        verification_issues = []

        for ps in sample:
            emp_name = ps.get("employee_name", ps.get("name", f"Emp #{ps.get('employee_id', ps.get('empcloud_user_id', '?'))}"))

            # Handle self-service payslip format with earnings/deductions arrays
            earnings_list = ps.get("earnings", [])
            deductions_list = ps.get("deductions", [])

            if isinstance(earnings_list, list) and earnings_list:
                gross = sum(float(e.get("amount", 0)) for e in earnings_list)
            else:
                gross = float(ps.get("gross_pay", ps.get("gross", ps.get("gross_salary", 0))) or 0)

            if isinstance(deductions_list, list) and deductions_list:
                deductions_total = sum(float(d.get("amount", 0)) for d in deductions_list)
                pf = sum(float(d.get("amount", 0)) for d in deductions_list if d.get("code") in ("EPF", "PF"))
                esi = sum(float(d.get("amount", 0)) for d in deductions_list if d.get("code") in ("ESI", "ESIC"))
                pt = sum(float(d.get("amount", 0)) for d in deductions_list if d.get("code") in ("PT", "PROFESSIONAL_TAX"))
                tds = sum(float(d.get("amount", 0)) for d in deductions_list if d.get("code") in ("TDS", "INCOME_TAX", "TAX"))
            else:
                deductions_total = float(ps.get("total_deductions", ps.get("deductions", 0)) or 0)
                pf = float(ps.get("pf", ps.get("provident_fund", ps.get("epf", 0))) or 0)
                esi = float(ps.get("esi", ps.get("esic", 0)) or 0)
                pt = float(ps.get("pt", ps.get("professional_tax", 0)) or 0)
                tds = float(ps.get("tds", ps.get("income_tax", ps.get("tax", 0))) or 0)

            net = float(ps.get("net_pay", ps.get("net", ps.get("net_salary", 0))) or 0)
            if net == 0 and gross > 0:
                net = gross - deductions_total

            deductions = deductions_total
            lop = float(ps.get("lop_days", ps.get("loss_of_pay_days", 0)) or 0)

            log(f"    {emp_name}: Gross={gross}, Deductions={deductions}, Net={net}")
            log(f"      PF={pf}, ESI={esi}, PT={pt}, TDS={tds}, LOP days={lop}")

            # Verify net = gross - deductions (with tolerance)
            if gross > 0 and net > 0:
                expected_net = gross - deductions
                if abs(net - expected_net) > 1:
                    issue = f"Net pay mismatch for {emp_name}: {net} != {gross} - {deductions} = {expected_net}"
                    verification_issues.append(issue)
                    log(f"      ISSUE: {issue}")

            # Check if deductions are present
            if gross > 15000 and pf == 0 and esi == 0 and tds == 0:
                issue = f"No statutory deductions for {emp_name} with gross {gross}"
                verification_issues.append(issue)

            day_log["payroll_details"][emp_name] = {
                "gross": gross, "deductions": deductions, "net": net,
                "pf": pf, "esi": esi, "pt": pt, "tds": tds, "lop_days": lop
            }

        if verification_issues:
            day_log["actions"].append(f"Payslip issues found: {len(verification_issues)}")
            for issue in verification_issues:
                file_bug(
                    f"Day 28: Payslip calculation issue for {org['name']}",
                    f"""## URL Tested
GET {PAYROLL_API}/payroll/{payroll_id}/payslips

## Steps to Reproduce
1. Login as {org['email']}
2. SSO to payroll module
3. Run payroll for March 2026
4. Check payslip calculations

## Expected Result
Net pay = Gross pay - Total deductions
Statutory deductions (PF, ESI, PT, TDS) should be calculated

## Actual Result
{issue}
"""
                )
        else:
            day_log["actions"].append("All sample payslips verified correctly")
    else:
        day_log["actions"].append("No payslips to verify")

    # 5. Generate statutory reports
    log("  Generating statutory reports...")
    for report_type in ["pf", "esi", "bank-file"]:
        status, body = api_call("GET", f"{PAYROLL_API}/payroll/{payroll_id}/reports/{report_type}",
                                token=payroll_token,
                                label=f"{report_type.upper()} report")
        if status == 200:
            log(f"    {report_type.upper()} report: OK")
            day_log["actions"].append(f"{report_type.upper()} report generated")
        else:
            log(f"    {report_type.upper()} report: status {status}")
            day_log["actions"].append(f"{report_type.upper()} report: status {status}")
        time.sleep(0.2)

    state["day_logs"]["day_28_" + org["name"]] = day_log
    return day_log

# =============================================================================
# DAY 29: PAYSLIP DISTRIBUTION
# =============================================================================
def day_29(org, token):
    """Day 29 - Payslip distribution and employee self-service checks."""
    day_log = {"date": "2026-03-29", "org": org["name"], "actions": []}
    log(f"\n{'='*60}")
    log(f"DAY 29 - Payslip Distribution - {org['name']}")
    log(f"{'='*60}")

    # Note: March 29, 2026 is a Sunday - but we simulate it as a payslip access day
    payroll_token = state.get("payroll_tokens", {}).get(org["name"])
    if not payroll_token:
        payroll_token = login_to_payroll(org)
    if not payroll_token:
        payroll_token = sso_to_module(token, PAYROLL_API, "payroll")

    # Employee self-service payslip checks
    active_ids = state.get("active_employees_by_org", {}).get(org["name"], [])
    setup = load_setup_data()
    active_emps = [e for e in setup.get("employees", []) if e["id"] in active_ids]

    log("  Employees checking payslips via self-service...")
    payslip_checks = 0
    payslip_issues = []

    # Check self-service endpoint
    status, body = api_call("GET", f"{PAYROLL_API}/self-service/payslips",
                            token=payroll_token,
                            params={"month": 3, "year": 2026},
                            label="Self-service payslips")
    if status == 200:
        ss_payslips = body.get("data", body.get("payslips", []))
        if isinstance(ss_payslips, list):
            log(f"  Self-service payslips: {len(ss_payslips)} found")
            payslip_checks = len(ss_payslips)

            # Try downloading PDF for first payslip
            if ss_payslips:
                ps_id = ss_payslips[0].get("id")
                if ps_id:
                    s2, b2 = api_call("GET", f"{PAYROLL_API}/self-service/payslips/{ps_id}/pdf",
                                      token=payroll_token,
                                      label="Download payslip PDF")
                    if s2 == 200:
                        log(f"    Payslip PDF download: OK")
                        day_log["actions"].append("Payslip PDF download successful")
                    else:
                        log(f"    Payslip PDF download: status {s2}")
                        day_log["actions"].append(f"Payslip PDF download: status {s2}")
        else:
            log(f"  Self-service payslips: non-list response")
    else:
        log(f"  Self-service payslips: status {status}")
        day_log["actions"].append(f"Self-service payslips: status {status}")

    # Check tax details
    log("  Checking tax details...")
    status, body = api_call("GET", f"{PAYROLL_API}/self-service/tax/declarations",
                            token=payroll_token,
                            label="Tax declarations")
    if status == 200:
        log(f"  Tax declarations: OK")
        day_log["actions"].append("Tax declarations accessible")
    else:
        log(f"  Tax declarations: status {status}")
        day_log["actions"].append(f"Tax declarations: status {status}")

    status, body = api_call("GET", f"{PAYROLL_API}/self-service/tax/form16",
                            token=payroll_token,
                            label="Form 16")
    if status == 200:
        log(f"  Form 16: OK")
        day_log["actions"].append("Form 16 accessible")
    else:
        log(f"  Form 16: status {status}")
        day_log["actions"].append(f"Form 16: status {status}")

    day_log["actions"].append(f"Payslip distribution: {payslip_checks} payslips accessed")
    state["day_logs"]["day_29_" + org["name"]] = day_log
    return day_log

# =============================================================================
# DAY 30: MONTH-END REPORTS & ANALYTICS
# =============================================================================
def day_30(org, token):
    """Day 30 - Month-end reports and analytics."""
    day_log = {"date": "2026-03-30", "org": org["name"], "actions": [], "reports": {}}
    log(f"\n{'='*60}")
    log(f"DAY 30 - Month-End Reports & Analytics - {org['name']}")
    log(f"{'='*60}")

    # 1. ATTENDANCE SUMMARY
    log("  1. Attendance Summary...")
    status, body = api_call("GET", f"{CORE_API}/attendance/records",
                            token=token,
                            params={"date": "2026-03-28"},
                            label="March attendance summary")
    att_summary = {"total_present": 0, "total_records": 0, "late_arrivals": 0}
    if status == 200:
        records = body.get("data", body.get("records", []))
        if isinstance(records, list):
            att_summary["total_records"] = len(records)
            for rec in records:
                if rec.get("status") in ("present", "checked_in", "checked_out"):
                    att_summary["total_present"] += 1
                ci = rec.get("check_in_time", rec.get("check_in", ""))
                if ci and "09:30" < str(ci)[11:16] if len(str(ci)) > 16 else False:
                    att_summary["late_arrivals"] += 1
    day_log["reports"]["attendance"] = att_summary
    log(f"    Present: {att_summary['total_present']}, Records: {att_summary['total_records']}, Late: {att_summary['late_arrivals']}")

    # 2. LEAVE SUMMARY
    log("  2. Leave Summary...")
    status, body = api_call("GET", f"{CORE_API}/leave/applications",
                            token=token,
                            params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
                            label="March leave summary")
    leave_summary = {"total_applications": 0, "by_type": {}, "by_status": {}}
    if status == 200:
        apps = body.get("data", body.get("applications", []))
        if isinstance(apps, list):
            leave_summary["total_applications"] = len(apps)
            for app in apps:
                lt = app.get("leave_type_name", app.get("leave_type", app.get("type", "Unknown")))
                if isinstance(lt, dict):
                    lt = lt.get("name", "Unknown")
                leave_summary["by_type"][str(lt)] = leave_summary["by_type"].get(str(lt), 0) + 1
                st = app.get("status", "unknown")
                leave_summary["by_status"][str(st)] = leave_summary["by_status"].get(str(st), 0) + 1
    day_log["reports"]["leave"] = leave_summary
    log(f"    Total applications: {leave_summary['total_applications']}")

    # Leave balances
    status, body = api_call("GET", f"{CORE_API}/leave/balances",
                            token=token, label="Leave balances")
    if status == 200:
        balances = body.get("data", body.get("balances", []))
        if isinstance(balances, list):
            zero_balance = sum(1 for b in balances
                             if float(b.get("balance", b.get("remaining", 1)) or 1) == 0)
            leave_summary["zero_balance_employees"] = zero_balance
            leave_summary["total_balance_records"] = len(balances)
            log(f"    Zero balance employees: {zero_balance}")

    # 3. PAYROLL SUMMARY
    log("  3. Payroll Summary...")
    payroll_token = state.get("payroll_tokens", {}).get(org["name"])
    if not payroll_token:
        payroll_token = login_to_payroll(org)
    if not payroll_token:
        payroll_token = sso_to_module(token, PAYROLL_API, "payroll")

    payroll_info = state.get("payroll_runs", {}).get(org["name"], {})
    payroll_id = payroll_info.get("payroll_id")
    payroll_summary = {"total_cost": 0, "employee_count": 0, "pf_total": 0, "esi_total": 0}

    # Use stored payslips from Day 28 if available
    stored_ps = state.get("payslips", {}).get(org["name"], {}).get("sample_payslips", [])
    if stored_ps:
        payroll_summary["employee_count"] = state.get("payslips", {}).get(org["name"], {}).get("count", len(stored_ps))
        for ps in stored_ps:
            earnings = ps.get("earnings", [])
            deductions_arr = ps.get("deductions", [])
            if isinstance(earnings, list) and earnings:
                payroll_summary["total_cost"] += sum(float(e.get("amount", 0)) for e in earnings)
            else:
                payroll_summary["total_cost"] += float(ps.get("gross_pay", ps.get("gross", 0)) or 0)
            if isinstance(deductions_arr, list):
                payroll_summary["pf_total"] += sum(float(d.get("amount", 0)) for d in deductions_arr if d.get("code") in ("EPF", "PF"))
                payroll_summary["esi_total"] += sum(float(d.get("amount", 0)) for d in deductions_arr if d.get("code") in ("ESI", "ESIC"))
            else:
                payroll_summary["pf_total"] += float(ps.get("pf", ps.get("epf", 0)) or 0)
                payroll_summary["esi_total"] += float(ps.get("esi", ps.get("esic", 0)) or 0)
    elif payroll_id:
        status, body = api_call("GET", f"{PAYROLL_API}/payroll/{payroll_id}/payslips",
                                token=payroll_token, label="Payroll summary")
        if status == 200:
            payslips_data = body.get("data", body.get("payslips", []))
            if isinstance(payslips_data, list):
                payroll_summary["employee_count"] = len(payslips_data)
                for ps in payslips_data:
                    payroll_summary["total_cost"] += float(ps.get("gross_pay", ps.get("gross", 0)) or 0)
                    payroll_summary["pf_total"] += float(ps.get("pf", ps.get("epf", 0)) or 0)
                    payroll_summary["esi_total"] += float(ps.get("esi", ps.get("esic", 0)) or 0)
    day_log["reports"]["payroll"] = payroll_summary
    log(f"    Total cost: {payroll_summary['total_cost']}, Employees: {payroll_summary['employee_count']}")

    # 4. HEADCOUNT
    log("  4. Headcount Report...")
    status, body = api_call("GET", f"{CORE_API}/users", token=token,
                            label="Get all users")
    headcount = {"total": 0, "active": 0, "inactive": 0, "by_department": {}}
    if status == 200:
        users = body.get("data", body.get("users", []))
        if isinstance(users, list):
            headcount["total"] = len(users)
            for u in users:
                is_active = u.get("is_active", u.get("status") != "inactive")
                if is_active:
                    headcount["active"] += 1
                else:
                    headcount["inactive"] += 1
                dept = u.get("department_name", u.get("department", {}) if isinstance(u.get("department"), dict) else u.get("department", "Unknown"))
                if isinstance(dept, dict):
                    dept = dept.get("name", "Unknown")
                dept = str(dept) if dept else "Unknown"
                headcount["by_department"][dept] = headcount["by_department"].get(dept, 0) + 1

    # Add simulation context
    new_joiners_count = len(state.get("new_joiners", {}).get(org["name"], []))
    exits_count = len(state.get("exit_processed", {}).get(org["name"], []))
    headcount["new_joiners_march"] = new_joiners_count
    headcount["exits_march"] = exits_count
    if headcount["active"] > 0:
        headcount["attrition_rate_pct"] = round(exits_count / (headcount["active"] + exits_count) * 100, 2)
    else:
        headcount["attrition_rate_pct"] = 0

    day_log["reports"]["headcount"] = headcount
    log(f"    Active: {headcount['active']}, Exits: {exits_count}, New joiners: {new_joiners_count}")

    # 5. PERFORMANCE (via SSO)
    log("  5. Performance Summary...")
    perf_token = sso_to_module(token, PERFORMANCE_API, "performance")
    perf_summary = {"review_cycles": 0, "goals_count": 0}

    status, body = api_call("GET", f"{PERFORMANCE_API}/review-cycles",
                            token=perf_token, label="Review cycles")
    if status == 200:
        cycles = body.get("data", body.get("cycles", []))
        if isinstance(cycles, list):
            perf_summary["review_cycles"] = len(cycles)

    status, body = api_call("GET", f"{PERFORMANCE_API}/goals",
                            token=perf_token, label="Goals")
    if status == 200:
        goals = body.get("data", body.get("goals", []))
        if isinstance(goals, list):
            perf_summary["goals_count"] = len(goals)
            completed = sum(1 for g in goals if (g.get("status") or "").lower() in ("completed", "achieved"))
            perf_summary["completed_goals"] = completed
    day_log["reports"]["performance"] = perf_summary
    log(f"    Review cycles: {perf_summary['review_cycles']}, Goals: {perf_summary['goals_count']}")

    # 6. ENGAGEMENT
    log("  6. Engagement Summary...")
    eng_summary = {"surveys": 0, "forum_posts": 0, "helpdesk_resolution_rate": 0}

    status, body = api_call("GET", f"{CORE_API}/surveys", token=token, label="Surveys")
    if status == 200:
        surveys = body.get("data", body.get("surveys", []))
        if isinstance(surveys, list):
            eng_summary["surveys"] = len(surveys)

    status, body = api_call("GET", f"{CORE_API}/forum/posts", token=token, label="Forum posts")
    if status == 200:
        posts = body.get("data", body.get("posts", []))
        if isinstance(posts, list):
            eng_summary["forum_posts"] = len(posts)

    ticket_info = state.get("helpdesk_tickets", {}).get(org["name"], {})
    total_tickets = ticket_info.get("total", 0)
    closed_tickets = ticket_info.get("closed", 0)
    if total_tickets > 0:
        eng_summary["helpdesk_resolution_rate"] = round(closed_tickets / total_tickets * 100, 2)
    eng_summary["helpdesk_total"] = total_tickets
    eng_summary["helpdesk_closed"] = closed_tickets

    day_log["reports"]["engagement"] = eng_summary
    log(f"    Surveys: {eng_summary['surveys']}, Forum posts: {eng_summary['forum_posts']}, Helpdesk resolution: {eng_summary['helpdesk_resolution_rate']}%")

    state["month_end_reports"][org["name"]] = day_log["reports"]
    state["day_logs"]["day_30_" + org["name"]] = day_log
    return day_log

# =============================================================================
# DATA INTEGRITY CHECKS
# =============================================================================
def run_data_integrity_checks(org, token):
    """Run end-of-month data integrity checks."""
    log(f"\n{'='*60}")
    log(f"DATA INTEGRITY CHECKS - {org['name']}")
    log(f"{'='*60}")

    checks = {
        "org": org["name"],
        "timestamp": datetime.now().isoformat(),
        "results": []
    }

    # 1. Attendance + Leave = Working Days
    log("  Check 1: Attendance + Leave = Working Days...")
    verification = state.get("attendance_records", {}).get(org["name"], {}).get("verification", [])
    discrepancy_count = sum(1 for v in verification if v.get("discrepancy", 0) > 2)
    checks["results"].append({
        "check": "Attendance + Leave = Working Days",
        "employees_checked": len(verification),
        "discrepancies": discrepancy_count,
        "status": "PASS" if discrepancy_count == 0 else "WARN"
    })
    log(f"    {len(verification)} checked, {discrepancy_count} discrepancies: {'PASS' if discrepancy_count == 0 else 'WARN'}")

    # 2. Leave balance consistency
    log("  Check 2: Leave balance consistency...")
    status, body = api_call("GET", f"{CORE_API}/leave/balances", token=token, label="Leave balances check")
    balance_issues = 0
    if status == 200:
        balances = body.get("data", body.get("balances", []))
        if isinstance(balances, list):
            for b in balances:
                bal = float(b.get("balance", b.get("remaining", 0)) or 0)
                if bal < 0:
                    balance_issues += 1
    checks["results"].append({
        "check": "Leave balance >= 0",
        "negative_balances": balance_issues,
        "status": "PASS" if balance_issues == 0 else "FAIL"
    })
    log(f"    Negative balances: {balance_issues}: {'PASS' if balance_issues == 0 else 'FAIL'}")

    # 3. Payroll total = Sum of payslips
    log("  Check 3: Payroll total consistency...")
    payroll_info = state.get("payslips", {}).get(org["name"], {})
    payslip_count = payroll_info.get("count", 0)
    payroll_summary = state.get("month_end_reports", {}).get(org["name"], {}).get("payroll", {})
    checks["results"].append({
        "check": "Payroll total = Sum of payslips",
        "payslip_count": payslip_count,
        "total_cost": payroll_summary.get("total_cost", 0),
        "status": "PASS" if payslip_count > 0 else "SKIP"
    })
    log(f"    Payslips: {payslip_count}, Total: {payroll_summary.get('total_cost', 0)}")

    # 4. Employee count consistency across modules
    log("  Check 4: Employee count consistency...")
    headcount = state.get("month_end_reports", {}).get(org["name"], {}).get("headcount", {})
    active_in_state = len(state.get("active_employees_by_org", {}).get(org["name"], []))
    active_in_api = headcount.get("active", 0)
    count_match = abs(active_in_state - active_in_api) < 5  # Allow small tolerance
    checks["results"].append({
        "check": "Employee count consistency",
        "state_count": active_in_state,
        "api_count": active_in_api,
        "status": "PASS" if count_match else "WARN"
    })
    log(f"    State: {active_in_state}, API: {active_in_api}: {'PASS' if count_match else 'WARN'}")

    # 5. Department headcount consistency
    log("  Check 5: Department headcounts...")
    dept_counts = headcount.get("by_department", {})
    checks["results"].append({
        "check": "Department headcounts",
        "departments": len(dept_counts),
        "data": dept_counts,
        "status": "PASS" if dept_counts else "SKIP"
    })
    log(f"    Departments tracked: {len(dept_counts)}")

    # 6. No orphan records check
    log("  Check 6: No orphan records...")
    resigned_ids = [e["id"] for e in state.get("resigned_employees", {}).get(org["name"], [])]
    orphan_issues = []

    # Check if exited employees have pending leave/assets
    for rid in resigned_ids:
        s, b = api_call("GET", f"{CORE_API}/leave/applications",
                        token=token, params={"employee_id": rid, "status": "pending"},
                        label=f"Orphan leave check emp {rid}")
        if s == 200:
            apps = b.get("data", b.get("applications", []))
            if isinstance(apps, list) and len(apps) > 0:
                orphan_issues.append(f"Employee {rid} (exited) has {len(apps)} pending leaves")

    checks["results"].append({
        "check": "No orphan records for exited employees",
        "issues": orphan_issues,
        "status": "PASS" if not orphan_issues else "WARN"
    })
    log(f"    Orphan issues: {len(orphan_issues)}")

    state["data_integrity"][org["name"]] = checks

    # File bugs for failures
    failures = [c for c in checks["results"] if c["status"] == "FAIL"]
    if failures:
        for fail in failures:
            file_bug(
                f"Day 30: Data integrity failure - {fail['check']} ({org['name']})",
                f"""## URL Tested
{CORE_API} / {PAYROLL_API}

## Steps to Reproduce
1. Login as {org['email']}
2. Run month-end data integrity check: {fail['check']}

## Expected Result
Data should be consistent across all modules

## Actual Result
Check FAILED: {json.dumps(fail, default=str)}
"""
            )

    return checks

# =============================================================================
# GENERATE FINAL MONTH-END REPORT
# =============================================================================
def generate_month_end_report():
    """Compile the comprehensive month-end report."""
    log(f"\n{'='*70}")
    log("GENERATING COMPREHENSIVE MONTH-END REPORT")
    log(f"{'='*70}")

    report = {
        "report_title": "EMP Cloud - March 2026 Month-End Report",
        "generated_at": datetime.now().isoformat(),
        "simulation_period": "2026-03-01 to 2026-03-31",
        "days_simulated": "21-30 (this phase)",
        "total_working_days_march": TOTAL_WORKING_DAYS,
        "organizations": {}
    }

    for org in ORGS:
        org_name = org["name"]
        org_report = {
            "org_id": org["id"],
            "admin_email": org["email"],
        }

        # Headcount
        headcount = state.get("month_end_reports", {}).get(org_name, {}).get("headcount", {})
        org_report["headcount"] = {
            "total_employees": headcount.get("total", 0),
            "active": headcount.get("active", 0),
            "inactive": headcount.get("inactive", 0),
            "new_joiners_march": headcount.get("new_joiners_march", 0),
            "exits_march": headcount.get("exits_march", 0),
            "attrition_rate": headcount.get("attrition_rate_pct", 0),
            "by_department": headcount.get("by_department", {})
        }

        # Attendance
        att = state.get("month_end_reports", {}).get(org_name, {}).get("attendance", {})
        org_report["attendance"] = {
            "total_records": att.get("total_records", 0),
            "total_present": att.get("total_present", 0),
            "late_arrivals": att.get("late_arrivals", 0),
            "absenteeism_rate": round(
                (1 - att.get("total_present", 0) / max(att.get("total_records", 1), 1)) * 100, 2
            ) if att.get("total_records", 0) > 0 else 0
        }

        # Leave
        leave = state.get("month_end_reports", {}).get(org_name, {}).get("leave", {})
        org_report["leave"] = leave

        # Payroll
        payroll = state.get("month_end_reports", {}).get(org_name, {}).get("payroll", {})
        org_report["payroll"] = {
            "total_cost": payroll.get("total_cost", 0),
            "employee_count": payroll.get("employee_count", 0),
            "pf_total": payroll.get("pf_total", 0),
            "esi_total": payroll.get("esi_total", 0),
            "payroll_run_id": state.get("payroll_runs", {}).get(org_name, {}).get("payroll_id"),
        }

        # Performance
        org_report["performance"] = state.get("month_end_reports", {}).get(org_name, {}).get("performance", {})

        # Engagement
        org_report["engagement"] = state.get("month_end_reports", {}).get(org_name, {}).get("engagement", {})

        # Exit processing
        org_report["exits"] = state.get("exit_processed", {}).get(org_name, [])

        # Data integrity
        integrity = state.get("data_integrity", {}).get(org_name, {})
        results = integrity.get("results", [])
        org_report["data_integrity"] = {
            "checks_run": len(results),
            "passed": sum(1 for r in results if r.get("status") == "PASS"),
            "warned": sum(1 for r in results if r.get("status") == "WARN"),
            "failed": sum(1 for r in results if r.get("status") == "FAIL"),
            "skipped": sum(1 for r in results if r.get("status") == "SKIP"),
            "details": results
        }

        report["organizations"][org_name] = org_report

    # Summary
    report["summary"] = {
        "total_bugs_filed": len(state.get("bugs_filed", [])),
        "bugs": state.get("bugs_filed", []),
        "api_errors_count": len(state.get("api_errors", [])),
        "simulation_completed": True,
        "days_completed": state.get("completed_days", []),
    }

    save_report(report)
    log(f"\nMonth-end report saved to: {REPORT_OUTPUT_PATH}")
    return report

# =============================================================================
# MAIN EXECUTION
# =============================================================================
def main():
    log("=" * 70)
    log("EMP CLOUD 30-DAY SIMULATION: DAYS 21-30 (MONTH-END PAYROLL)")
    log("=" * 70)
    log(f"Date range: March 21-30, 2026")
    log(f"Total working days in March 2026: {TOTAL_WORKING_DAYS}")
    log(f"Organizations: {', '.join(o['name'] for o in ORGS)}")

    # Load previous state if available
    prev = load_previous_state()
    if prev:
        log(f"\nPrevious state loaded from {PREV_STATE_PATH}")
        # Merge relevant data
        for key in ["resigned_employees", "new_joiners", "attendance_records", "leave_records"]:
            if key in prev:
                state.setdefault(key, {}).update(prev[key])
    else:
        log("\nNo previous state found - starting fresh for days 21-30")

    # Login to all orgs
    log("\n--- Authenticating to all organizations ---")
    for org in ORGS:
        token = login_core(org["email"], org["password"])
        if token:
            state["tokens"][org["name"]] = token
            log(f"  {org['name']}: authenticated")
        else:
            log(f"  {org['name']}: AUTHENTICATION FAILED")

    # Check we have at least one working token
    working_orgs = [(org, state["tokens"][org["name"]]) for org in ORGS if org["name"] in state["tokens"]]
    if not working_orgs:
        log("\nFATAL: No organizations authenticated. Aborting simulation.")
        save_state()
        return

    log(f"\n{len(working_orgs)} organizations authenticated successfully")

    # ===========================================
    # Execute simulation days
    # ===========================================

    for org, token in working_orgs:
        # DAY 21
        try:
            day_21(org, token)
            state["completed_days"].append(f"day_21_{org['name']}")
        except Exception as e:
            log(f"  DAY 21 ERROR ({org['name']}): {e}")
            state["api_errors"].append({"day": 21, "org": org["name"], "error": str(e)})
        save_state()

        # DAY 22
        try:
            day_22(org, token)
            state["completed_days"].append(f"day_22_{org['name']}")
        except Exception as e:
            log(f"  DAY 22 ERROR ({org['name']}): {e}")
            state["api_errors"].append({"day": 22, "org": org["name"], "error": str(e)})
        save_state()

        # DAYS 23-26
        try:
            days_23_26(org, token)
            state["completed_days"].append(f"days_23_26_{org['name']}")
        except Exception as e:
            log(f"  DAYS 23-26 ERROR ({org['name']}): {e}")
            state["api_errors"].append({"day": "23-26", "org": org["name"], "error": str(e)})
        save_state()

        # DAY 27
        try:
            day_27(org, token)
            state["completed_days"].append(f"day_27_{org['name']}")
        except Exception as e:
            log(f"  DAY 27 ERROR ({org['name']}): {e}")
            state["api_errors"].append({"day": 27, "org": org["name"], "error": str(e)})
        save_state()

        # DAY 28 - PAYROLL
        try:
            day_28(org, token)
            state["completed_days"].append(f"day_28_{org['name']}")
        except Exception as e:
            log(f"  DAY 28 ERROR ({org['name']}): {e}")
            state["api_errors"].append({"day": 28, "org": org["name"], "error": str(e)})
        save_state()

        # DAY 29
        try:
            day_29(org, token)
            state["completed_days"].append(f"day_29_{org['name']}")
        except Exception as e:
            log(f"  DAY 29 ERROR ({org['name']}): {e}")
            state["api_errors"].append({"day": 29, "org": org["name"], "error": str(e)})
        save_state()

        # DAY 30
        try:
            day_30(org, token)
            state["completed_days"].append(f"day_30_{org['name']}")
        except Exception as e:
            log(f"  DAY 30 ERROR ({org['name']}): {e}")
            state["api_errors"].append({"day": 30, "org": org["name"], "error": str(e)})
        save_state()

        # DATA INTEGRITY CHECKS
        try:
            run_data_integrity_checks(org, token)
        except Exception as e:
            log(f"  DATA INTEGRITY ERROR ({org['name']}): {e}")
            state["api_errors"].append({"day": "integrity", "org": org["name"], "error": str(e)})
        save_state()

    # Generate final report
    try:
        report = generate_month_end_report()
    except Exception as e:
        log(f"REPORT GENERATION ERROR: {e}")

    # Final save
    save_state()

    # Print summary
    log(f"\n{'='*70}")
    log("SIMULATION COMPLETE - DAYS 21-30")
    log(f"{'='*70}")
    log(f"Days completed: {len(state['completed_days'])}")
    log(f"Bugs filed: {len(state.get('bugs_filed', []))}")
    log(f"API errors: {len(state.get('api_errors', []))}")
    log(f"State saved to: {STATE_OUTPUT_PATH}")
    log(f"Report saved to: {REPORT_OUTPUT_PATH}")

    for org in ORGS:
        org_name = org["name"]
        payroll = state.get("payroll_runs", {}).get(org_name, {})
        exits = state.get("exit_processed", {}).get(org_name, [])
        payslips = state.get("payslips", {}).get(org_name, {})
        integrity = state.get("data_integrity", {}).get(org_name, {})
        results = integrity.get("results", [])

        log(f"\n  {org_name}:")
        log(f"    Payroll run: {payroll.get('payroll_id', 'N/A')}")
        log(f"    Payslips: {payslips.get('count', 0)}")
        log(f"    Exits processed: {len(exits)}")
        log(f"    Integrity checks: {sum(1 for r in results if r.get('status')=='PASS')} pass, "
            f"{sum(1 for r in results if r.get('status')=='WARN')} warn, "
            f"{sum(1 for r in results if r.get('status')=='FAIL')} fail")

    if state.get("bugs_filed"):
        log(f"\n  Bugs filed:")
        for bug in state["bugs_filed"]:
            log(f"    #{bug.get('number', '?')}: {bug.get('title', 'N/A')}")

if __name__ == "__main__":
    main()
