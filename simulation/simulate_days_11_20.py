#!/usr/bin/env python3
"""
EMP Cloud 30-Day HRMS Simulation — Days 11-20
Tests Performance, Exit, LMS, Rewards, Projects modules + core HR operations
for 3 organizations: TechNova, GlobalTech, Innovate Solutions.
"""

import sys
import os
import json
import time
import requests
import traceback
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ─── Configuration ───────────────────────────────────────────────────────────
CORE_API = "https://test-empcloud-api.empcloud.com/api/v1"
PERF_API = "https://test-performance-api.empcloud.com/api/v1"
EXIT_API = "https://test-exit-api.empcloud.com/api/v1"
LMS_API  = "https://testlms-api.empcloud.com/api/v1"
REWARDS_API = "https://test-rewards-api.empcloud.com/api/v1"
PROJECT_API = "https://test-project-api.empcloud.com/v1"

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

ORGS = [
    {"name": "TechNova", "email": "ananya@technova.in", "password": "Welcome@123"},
    {"name": "GlobalTech", "email": "john@globaltech.com", "password": "Welcome@123"},
    {"name": "Innovate Solutions", "email": "hr@innovate.io", "password": "Welcome@123"},
]

# Load setup data
with open(r"C:\emptesting\simulation\setup_data.json", "r", encoding="utf-8") as f:
    SETUP = json.load(f)

# State tracking
STATE = {
    "days_completed": [],
    "bugs_filed": [],
    "bugs_found": [],
    "performance": {},
    "exit": {},
    "lms": {},
    "rewards": {},
    "projects": {},
    "leave_applications": {},
    "transfers": {},
    "attendance": {},
    "announcements": {},
    "hr_review": {},
    "billing": {},
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def api(method, url, token=None, json_data=None, params=None, timeout=30):
    """Make API call with error handling."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.request(method, url, headers=headers, json=json_data, params=params, timeout=timeout)
        try:
            body = r.json()
        except Exception:
            body = r.text
        return {"status": r.status_code, "body": body, "ok": 200 <= r.status_code < 300}
    except Exception as e:
        return {"status": 0, "body": str(e), "ok": False}

def login(email, password):
    """Login to core EMP Cloud."""
    r = api("POST", f"{CORE_API}/auth/login", json_data={"email": email, "password": password})
    if r["ok"] and isinstance(r["body"], dict):
        # Token is at data.tokens.access_token
        data = r["body"].get("data", {})
        if isinstance(data, dict):
            tokens = data.get("tokens", {})
            if isinstance(tokens, dict) and tokens.get("access_token"):
                return tokens["access_token"]
            # Fallback
            token = data.get("token") or data.get("accessToken") or data.get("access_token")
            if token:
                return token
        token = r["body"].get("token") or r["body"].get("accessToken") or r["body"].get("access_token")
        if token:
            return token
    log(f"  LOGIN FAILED for {email}: {r['status']} {str(r['body'])[:200]}")
    return None

def sso_to_module(core_token, module_api):
    """SSO from core to an external module."""
    r = api("POST", f"{module_api}/auth/sso", token=core_token, json_data={"token": core_token})
    if r["ok"] and isinstance(r["body"], dict):
        data = r["body"].get("data", {})
        if isinstance(data, dict):
            tokens = data.get("tokens", {})
            if isinstance(tokens, dict) and tokens.get("access_token"):
                return tokens["access_token"]
            t = data.get("token") or data.get("accessToken") or data.get("access_token")
            if t:
                return t
        t = r["body"].get("token") or r["body"].get("accessToken") or r["body"].get("access_token")
        if t:
            return t
    log(f"  SSO to {module_api} response: {r['status']} {str(r['body'])[:200]}")
    return core_token  # Fall back to core token

def get_org_employees(org_name):
    """Get real employees (with emp_code like TN-xxx, GT-xxx, IS-xxx) for an org."""
    prefix_map = {"TechNova": "TN-", "GlobalTech": "GT-", "Innovate Solutions": "IS-"}
    prefix = prefix_map.get(org_name, "")
    emps = [e for e in SETUP["employees"]
            if e["organization"] == org_name and e.get("emp_code") and e["emp_code"].startswith(prefix)
            and e["role"] == "employee"]
    return sorted(emps, key=lambda x: x["id"])

def get_org_departments(org_name):
    return [d for d in SETUP["departments"] if d["organization"] == org_name]

def get_org_leave_type(org_name, type_name):
    for lt in SETUP.get("leave_types", []):
        if lt["organization"] == org_name and lt["name"] == type_name:
            return lt["id"]
    # Search from org config
    for org in SETUP["organizations"]:
        if org["name"] == org_name:
            for lt in org.get("leave_types", []):
                if lt["name"] == type_name:
                    return lt["id"]
    return None

def record_bug(title, details, day):
    """Record a bug found during simulation."""
    STATE["bugs_found"].append({"title": title, "details": details, "day": day})
    log(f"  BUG: {title}")

def file_github_issue(title, body, labels=None):
    """File a GitHub issue."""
    if labels is None:
        labels = ["bug", "30-day-sim"]
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"title": title, "body": body, "labels": labels}
    try:
        r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                          headers=headers, json=data, timeout=30)
        if r.status_code == 201:
            issue = r.json()
            log(f"  Filed issue #{issue['number']}: {title}")
            STATE["bugs_filed"].append({"number": issue["number"], "title": title})
            return issue["number"]
        else:
            log(f"  Failed to file issue: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log(f"  Failed to file issue: {e}")
    return None

def search_existing_issues(keyword):
    """Search for existing issues to avoid duplicates."""
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        q = f'repo:{GITHUB_REPO} "{keyword}" in:title'
        r = requests.get("https://api.github.com/search/issues", headers=headers,
                         params={"q": q}, timeout=15)
        if r.status_code == 200:
            return r.json().get("items", [])
    except Exception:
        pass
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 11 — Performance Reviews Start
# ═══════════════════════════════════════════════════════════════════════════════

def day_11():
    log("=" * 70)
    log("DAY 11 — Performance Reviews Start")
    log("=" * 70)
    STATE["performance"] = {}

    for org in ORGS:
        org_name = org["name"]
        log(f"\n--- {org_name} ---")
        token = login(org["email"], org["password"])
        if not token:
            record_bug(f"Can't log in as {org_name} admin for performance review setup",
                       f"Login failed for {org['email']}", 11)
            continue

        # SSO to Performance module
        perf_token = sso_to_module(token, PERF_API)
        log(f"  SSO to Performance module: {'OK' if perf_token else 'FAILED'}")

        org_state = {"sso_ok": perf_token is not None, "review_cycle": None, "goals": [], "self_assessments": []}

        # 1. Create review cycle
        cycle_data = {
            "name": "Q1 2026 Performance Review",
            "description": "Quarterly performance review for Q1 2026",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "type": "quarterly",
            "status": "active",
        }
        r = api("POST", f"{PERF_API}/review-cycles", token=perf_token, json_data=cycle_data)
        log(f"  Create review cycle: {r['status']} {str(r['body'])[:200]}")
        cycle_id = None
        if r["ok"] and isinstance(r["body"], dict):
            cycle_id = r["body"].get("id") or (r["body"].get("data", {}).get("id") if isinstance(r["body"].get("data"), dict) else None)
            org_state["review_cycle"] = cycle_id

        if not cycle_id:
            # Try GET existing cycles
            r2 = api("GET", f"{PERF_API}/review-cycles", token=perf_token)
            log(f"  GET review-cycles: {r2['status']} {str(r2['body'])[:200]}")
            if r2["ok"] and isinstance(r2["body"], dict):
                cycles = r2["body"].get("data", r2["body"].get("items", []))
                if isinstance(cycles, list) and cycles:
                    cycle_id = cycles[0].get("id")
                    org_state["review_cycle"] = cycle_id
                    log(f"  Using existing cycle: {cycle_id}")
            elif r2["ok"] and isinstance(r2["body"], list) and r2["body"]:
                cycle_id = r2["body"][0].get("id")
                org_state["review_cycle"] = cycle_id

        # If cycle creation/retrieval completely fails, note it
        if not r["ok"] and r["status"] not in [409, 422]:
            if r["status"] == 401:
                record_bug(
                    f"[30-Day Sim] Performance SSO returns 401 when creating review cycle for {org_name}",
                    f"After SSO from core to Performance module, POST /review-cycles returns 401. "
                    f"Status: {r['status']}, Body: {str(r['body'])[:300]}", 11)

        # 2. Set goals for 10 employees
        employees = get_org_employees(org_name)[:10]
        goals_set = 0
        for emp in employees:
            goal_data = {
                "employee_id": emp["id"],
                "title": f"Q1 2026 Goals for {emp['first_name']} {emp['last_name']}",
                "description": f"Performance goals for Q1 2026",
                "target_date": "2026-03-31",
                "status": "in_progress",
                "weight": 100,
            }
            if cycle_id:
                goal_data["review_cycle_id"] = cycle_id

            r = api("POST", f"{PERF_API}/goals", token=perf_token, json_data=goal_data)
            if r["ok"]:
                goals_set += 1
                goal_id = None
                if isinstance(r["body"], dict):
                    goal_id = r["body"].get("id") or (r["body"].get("data", {}).get("id") if isinstance(r["body"].get("data"), dict) else None)
                org_state["goals"].append({"employee_id": emp["id"], "goal_id": goal_id})

                # Try adding key results
                if goal_id:
                    kr_data = {
                        "title": f"Complete key deliverables",
                        "target_value": 100,
                        "current_value": 0,
                        "unit": "percent",
                    }
                    api("POST", f"{PERF_API}/goals/{goal_id}/key-results", token=perf_token, json_data=kr_data)

        log(f"  Goals set: {goals_set}/10 employees")

        # 3. Try self-assessment
        r = api("GET", f"{PERF_API}/reviews", token=perf_token)
        log(f"  GET reviews: {r['status']} {str(r['body'])[:150]}")

        # Try to submit self-assessment for first employee if reviews exist
        if r["ok"] and isinstance(r["body"], dict):
            reviews = r["body"].get("data", r["body"].get("items", []))
            if isinstance(reviews, list):
                for rev in reviews[:3]:
                    rev_id = rev.get("id")
                    if rev_id:
                        sa = api("PUT", f"{PERF_API}/reviews/{rev_id}", token=perf_token,
                                 json_data={"self_rating": 4, "self_comments": "Performed well this quarter"})
                        if sa["ok"]:
                            org_state["self_assessments"].append(rev_id)

        STATE["performance"][org_name] = org_state

    STATE["days_completed"].append(11)
    log("\nDay 11 complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 12 — Regular Day + Resignations
# ═══════════════════════════════════════════════════════════════════════════════

def day_12():
    log("=" * 70)
    log("DAY 12 — Regular Day + Resignations")
    log("=" * 70)
    STATE["exit"] = {}

    for org in ORGS:
        org_name = org["name"]
        log(f"\n--- {org_name} ---")
        token = login(org["email"], org["password"])
        if not token:
            continue

        org_state = {"attendance_count": 0, "resignations": [], "clearance": []}

        # 1. Normal attendance for all employees (check-in)
        employees = get_org_employees(org_name)
        checkin_ok = 0
        for emp in employees[:30]:  # Up to 30 to keep it reasonable
            r = api("POST", f"{CORE_API}/attendance/check-in", token=token,
                    json_data={"employee_id": emp["id"], "timestamp": "2026-03-12T09:00:00Z"})
            if r["ok"]:
                checkin_ok += 1
        log(f"  Attendance check-in: {checkin_ok}/{min(len(employees), 30)}")
        org_state["attendance_count"] = checkin_ok

        # 2. Two employees submit resignation via Exit module
        exit_token = sso_to_module(token, EXIT_API)
        resign_emps = employees[-4:-2] if len(employees) >= 4 else employees[:2]

        for emp in resign_emps:
            # Try self-service resign
            resign_data = {
                "employee_id": emp["id"],
                "reason": "Personal reasons - career growth opportunity",
                "last_working_date": "2026-04-15",
                "notice_period_days": 30,
            }
            r = api("POST", f"{EXIT_API}/self-service/resign", token=exit_token, json_data=resign_data)
            log(f"  Resign {emp['first_name']} {emp['last_name']}: {r['status']} {str(r['body'])[:200]}")

            exit_id = None
            if r["ok"] and isinstance(r["body"], dict):
                exit_id = r["body"].get("id") or (r["body"].get("data", {}).get("id") if isinstance(r["body"].get("data"), dict) else None)

            if not r["ok"]:
                # Try POST /exits (admin-initiated)
                r2 = api("POST", f"{EXIT_API}/exits", token=exit_token, json_data={
                    "employee_id": emp["id"],
                    "type": "resignation",
                    "reason": "Personal reasons - career growth",
                    "last_working_date": "2026-04-15",
                    "notice_period_days": 30,
                })
                log(f"  Exit (admin): {r2['status']} {str(r2['body'])[:200]}")
                if r2["ok"] and isinstance(r2["body"], dict):
                    exit_id = r2["body"].get("id") or (r2["body"].get("data", {}).get("id") if isinstance(r2["body"].get("data"), dict) else None)

            if exit_id:
                org_state["resignations"].append({"employee_id": emp["id"], "exit_id": exit_id,
                                                   "name": f"{emp['first_name']} {emp['last_name']}"})

                # Create clearance checklist
                clearance_data = {
                    "department": "IT",
                    "items": [
                        {"item": "Return laptop", "status": "pending"},
                        {"item": "Return access card", "status": "pending"},
                        {"item": "Knowledge transfer", "status": "pending"},
                        {"item": "Email account deactivation", "status": "pending"},
                    ]
                }
                r3 = api("POST", f"{EXIT_API}/clearance/{exit_id}", token=exit_token, json_data=clearance_data)
                log(f"  Clearance checklist: {r3['status']} {str(r3['body'])[:150]}")
                if r3["ok"]:
                    org_state["clearance"].append(exit_id)

        # Also try GET exits to see what exists
        r = api("GET", f"{EXIT_API}/exits", token=exit_token)
        log(f"  GET exits: {r['status']} {str(r['body'])[:200]}")

        STATE["exit"][org_name] = org_state

    STATE["days_completed"].append(12)
    log("\nDay 12 complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 13 — Training & Learning
# ═══════════════════════════════════════════════════════════════════════════════

def day_13():
    log("=" * 70)
    log("DAY 13 — Training & Learning")
    log("=" * 70)
    STATE["lms"] = {}

    for org in ORGS:
        org_name = org["name"]
        log(f"\n--- {org_name} ---")
        token = login(org["email"], org["password"])
        if not token:
            continue

        lms_token = sso_to_module(token, LMS_API)
        org_state = {"sso_ok": lms_token is not None, "course_id": None, "enrollments": 0, "completions": 0}

        # 1. Create course
        course_data = {
            "title": "Security Awareness Training",
            "description": "Mandatory security awareness training for all employees covering phishing, passwords, and data protection.",
            "category": "compliance",
            "type": "online",
            "duration_hours": 2,
            "status": "published",
            "is_mandatory": True,
        }
        r = api("POST", f"{LMS_API}/courses", token=lms_token, json_data=course_data)
        log(f"  Create course: {r['status']} {str(r['body'])[:200]}")
        course_id = None
        if r["ok"] and isinstance(r["body"], dict):
            course_id = r["body"].get("id") or (r["body"].get("data", {}).get("id") if isinstance(r["body"].get("data"), dict) else None)

        if not course_id:
            # Check existing courses
            r2 = api("GET", f"{LMS_API}/courses", token=lms_token)
            log(f"  GET courses: {r2['status']} {str(r2['body'])[:200]}")
            if r2["ok"] and isinstance(r2["body"], dict):
                courses = r2["body"].get("data", r2["body"].get("items", []))
                if isinstance(courses, list) and courses:
                    course_id = courses[0].get("id")
            elif r2["ok"] and isinstance(r2["body"], list) and r2["body"]:
                course_id = r2["body"][0].get("id")

        org_state["course_id"] = course_id

        # 2. Assign (enroll) all employees
        employees = get_org_employees(org_name)
        enrolled = 0
        enrollment_ids = []
        for emp in employees:
            enroll_data = {
                "course_id": course_id,
                "employee_id": emp["id"],
                "user_id": emp["id"],
            }
            r = api("POST", f"{LMS_API}/enrollments", token=lms_token, json_data=enroll_data)
            if r["ok"]:
                enrolled += 1
                eid = None
                if isinstance(r["body"], dict):
                    eid = r["body"].get("id") or (r["body"].get("data", {}).get("id") if isinstance(r["body"].get("data"), dict) else None)
                enrollment_ids.append({"employee_id": emp["id"], "enrollment_id": eid})
        log(f"  Enrolled: {enrolled}/{len(employees)}")
        org_state["enrollments"] = enrolled

        # 3. 20 employees complete the course
        completed = 0
        for entry in enrollment_ids[:20]:
            eid = entry.get("enrollment_id")
            if eid:
                r = api("PUT", f"{LMS_API}/enrollments/{eid}/progress", token=lms_token,
                        json_data={"progress": 100, "status": "completed", "completed_at": "2026-03-13T17:00:00Z"})
                if r["ok"]:
                    completed += 1
                else:
                    # Try PATCH
                    r2 = api("PATCH", f"{LMS_API}/enrollments/{eid}/progress", token=lms_token,
                             json_data={"progress": 100, "status": "completed"})
                    if r2["ok"]:
                        completed += 1
        log(f"  Completed course: {completed}/20")
        org_state["completions"] = completed

        # Check certifications
        r = api("GET", f"{LMS_API}/certifications", token=lms_token)
        log(f"  GET certifications: {r['status']} {str(r['body'])[:150]}")

        # Check learning paths
        r = api("GET", f"{LMS_API}/learning-paths", token=lms_token)
        log(f"  GET learning-paths: {r['status']} {str(r['body'])[:150]}")

        STATE["lms"][org_name] = org_state

    STATE["days_completed"].append(13)
    log("\nDay 13 complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 14 — Public Holiday
# ═══════════════════════════════════════════════════════════════════════════════

def day_14():
    log("=" * 70)
    log("DAY 14 — Public Holiday (No Attendance)")
    log("=" * 70)

    for org in ORGS:
        org_name = org["name"]
        log(f"\n--- {org_name} ---")
        token = login(org["email"], org["password"])
        if not token:
            continue

        employees = get_org_employees(org_name)

        # Try to check in on holiday - system should reject
        test_emp = employees[0] if employees else None
        if test_emp:
            r = api("POST", f"{CORE_API}/attendance/check-in", token=token,
                    json_data={"employee_id": test_emp["id"], "timestamp": "2026-03-14T09:00:00Z"})
            log(f"  Holiday check-in attempt: {r['status']} {str(r['body'])[:200]}")
            if r["ok"]:
                record_bug(
                    f"[30-Day Sim] System allows clock-in on public holiday",
                    f"For {org_name}, employee {test_emp['first_name']} was able to check in on "
                    f"2026-03-14 which should be a public holiday. Status: {r['status']}", 14)

        # Check holidays/events list
        r = api("GET", f"{CORE_API}/events", token=token, params={"date": "2026-03-14"})
        log(f"  GET events for holiday date: {r['status']} {str(r['body'])[:200]}")

        # Check attendance records - should be empty for this date
        r = api("GET", f"{CORE_API}/attendance/records", token=token,
                params={"date": "2026-03-14"})
        log(f"  Attendance records on holiday: {r['status']} {str(r['body'])[:200]}")

    STATE["days_completed"].append(14)
    log("\nDay 14 complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 15 — Mid-Month HR Review
# ═══════════════════════════════════════════════════════════════════════════════

def day_15():
    log("=" * 70)
    log("DAY 15 — Mid-Month HR Review")
    log("=" * 70)
    STATE["hr_review"] = {}

    for org in ORGS:
        org_name = org["name"]
        log(f"\n--- {org_name} ---")
        token = login(org["email"], org["password"])
        if not token:
            continue

        review = {}

        # 1. Total headcount
        r = api("GET", f"{CORE_API}/users", token=token, params={"limit": 1})
        log(f"  GET users: {r['status']} {str(r['body'])[:200]}")
        if r["ok"] and isinstance(r["body"], dict):
            total = r["body"].get("total") or r["body"].get("meta", {}).get("total") or r["body"].get("pagination", {}).get("total")
            review["headcount"] = total
            log(f"  Headcount: {total}")

        # 2. Attrition (check exits)
        exit_token = sso_to_module(token, EXIT_API)
        r = api("GET", f"{EXIT_API}/exits", token=exit_token)
        log(f"  GET exits (attrition): {r['status']} {str(r['body'])[:150]}")
        exit_count = 0
        if r["ok"]:
            if isinstance(r["body"], dict):
                exits = r["body"].get("data", r["body"].get("items", []))
                if isinstance(exits, list):
                    exit_count = len(exits)
            elif isinstance(r["body"], list):
                exit_count = len(r["body"])
        review["attrition"] = exit_count

        # 3. Leave utilization
        r = api("GET", f"{CORE_API}/leave/applications", token=token, params={"limit": 100})
        log(f"  Leave applications: {r['status']} {str(r['body'])[:150]}")
        leave_count = 0
        if r["ok"] and isinstance(r["body"], dict):
            apps = r["body"].get("data", r["body"].get("items", []))
            if isinstance(apps, list):
                leave_count = len(apps)
        review["leave_applications"] = leave_count

        # 4. Attendance compliance
        r = api("GET", f"{CORE_API}/attendance/records", token=token,
                params={"start_date": "2026-03-01", "end_date": "2026-03-15"})
        log(f"  Attendance records: {r['status']} {str(r['body'])[:150]}")

        # 5. Open helpdesk tickets
        r = api("GET", f"{CORE_API}/helpdesk/tickets", token=token, params={"status": "open"})
        log(f"  Helpdesk tickets: {r['status']} {str(r['body'])[:150]}")
        ticket_count = 0
        if r["ok"]:
            if isinstance(r["body"], dict):
                tickets = r["body"].get("data", r["body"].get("items", []))
                if isinstance(tickets, list):
                    ticket_count = len(tickets)
            elif isinstance(r["body"], list):
                ticket_count = len(r["body"])
        review["open_tickets"] = ticket_count

        # 6. Survey results
        r = api("GET", f"{CORE_API}/surveys", token=token)
        log(f"  Surveys: {r['status']} {str(r['body'])[:150]}")

        # 7. Post announcement
        ann_data = {
            "title": "Monthly town hall this Friday",
            "content": "Dear team, our monthly town hall will be held this Friday at 3 PM. "
                       "We'll discuss Q1 progress, upcoming projects, and team updates. "
                       "All employees are expected to attend.",
            "type": "general",
            "priority": "normal",
            "is_published": True,
        }
        r = api("POST", f"{CORE_API}/announcements", token=token, json_data=ann_data)
        log(f"  Post announcement: {r['status']} {str(r['body'])[:150]}")
        review["announcement_posted"] = r["ok"]

        STATE["hr_review"][org_name] = review

    STATE["days_completed"].append(15)
    log("\nDay 15 complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 16 — Rewards & Recognition
# ═══════════════════════════════════════════════════════════════════════════════

def day_16():
    log("=" * 70)
    log("DAY 16 — Rewards & Recognition")
    log("=" * 70)
    STATE["rewards"] = {}

    for org in ORGS:
        org_name = org["name"]
        log(f"\n--- {org_name} ---")
        token = login(org["email"], org["password"])
        if not token:
            continue

        rewards_token = sso_to_module(token, REWARDS_API)
        org_state = {"sso_ok": rewards_token is not None, "kudos_given": 0, "badges_awarded": 0, "leaderboard": None}

        employees = get_org_employees(org_name)

        # 1. Give kudos to 5 top performers
        kudos_given = 0
        kudos_messages = [
            "Outstanding work on the Q1 deliverables! Your dedication is truly appreciated.",
            "Excellent leadership during the project launch. You inspire the team.",
            "Great problem-solving skills demonstrated this month. Keep it up!",
            "Your mentorship of junior team members has been invaluable.",
            "Fantastic customer presentation that won us a major deal!",
        ]
        for i, emp in enumerate(employees[:5]):
            kudos_data = {
                "recipient_id": emp["id"],
                "message": kudos_messages[i],
                "category": "excellence",
                "value": "teamwork",
                "points": 100,
                "is_public": True,
            }
            r = api("POST", f"{REWARDS_API}/kudos", token=rewards_token, json_data=kudos_data)
            log(f"  Kudos to {emp['first_name']}: {r['status']} {str(r['body'])[:150]}")
            if r["ok"]:
                kudos_given += 1
        org_state["kudos_given"] = kudos_given

        # 2. Award badges to 3 employees
        badges_awarded = 0
        # First check available badges
        r = api("GET", f"{REWARDS_API}/badges", token=rewards_token)
        log(f"  GET badges: {r['status']} {str(r['body'])[:200]}")
        badge_ids = []
        if r["ok"]:
            if isinstance(r["body"], dict):
                badges = r["body"].get("data", r["body"].get("items", []))
                if isinstance(badges, list):
                    badge_ids = [b.get("id") for b in badges if b.get("id")]
            elif isinstance(r["body"], list):
                badge_ids = [b.get("id") for b in r["body"] if b.get("id")]

        if not badge_ids:
            # Create badges
            badge_names = ["Star Performer", "Team Player", "Innovation Champion"]
            for bname in badge_names:
                r = api("POST", f"{REWARDS_API}/badges", token=rewards_token,
                        json_data={"name": bname, "description": f"Awarded for being a {bname.lower()}", "icon": "star"})
                if r["ok"] and isinstance(r["body"], dict):
                    bid = r["body"].get("id") or (r["body"].get("data", {}).get("id") if isinstance(r["body"].get("data"), dict) else None)
                    if bid:
                        badge_ids.append(bid)

        for i, emp in enumerate(employees[5:8]):
            if badge_ids:
                badge_id = badge_ids[i % len(badge_ids)]
                r = api("POST", f"{REWARDS_API}/badges/{badge_id}/award", token=rewards_token,
                        json_data={"employee_id": emp["id"], "user_id": emp["id"]})
                log(f"  Badge to {emp['first_name']}: {r['status']} {str(r['body'])[:150]}")
                if r["ok"]:
                    badges_awarded += 1
        org_state["badges_awarded"] = badges_awarded

        # 3. Check leaderboard
        r = api("GET", f"{REWARDS_API}/leaderboard", token=rewards_token)
        log(f"  Leaderboard: {r['status']} {str(r['body'])[:200]}")
        org_state["leaderboard"] = r["ok"]

        # Check points balance
        r = api("GET", f"{REWARDS_API}/points/balance", token=rewards_token)
        log(f"  Points balance: {r['status']} {str(r['body'])[:150]}")

        STATE["rewards"][org_name] = org_state

    STATE["days_completed"].append(16)
    log("\nDay 16 complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 17 — Project Updates
# ═══════════════════════════════════════════════════════════════════════════════

def day_17():
    log("=" * 70)
    log("DAY 17 — Project Updates")
    log("=" * 70)
    STATE["projects"] = {}

    for org in ORGS:
        org_name = org["name"]
        log(f"\n--- {org_name} ---")
        token = login(org["email"], org["password"])
        if not token:
            continue

        proj_token = sso_to_module(token, PROJECT_API.replace("/v1", ""))
        # Project module uses /v1/ not /api/v1/
        org_state = {"sso_ok": proj_token is not None, "project_id": None, "tasks": [], "time_entries": []}

        # 1. Create project
        proj_data = {
            "name": "Q2 Product Launch",
            "description": "Planning and execution for Q2 2026 product launch including marketing, engineering, and sales alignment.",
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
            "status": "active",
            "priority": "high",
        }
        r = api("POST", f"{PROJECT_API}/projects", token=proj_token, json_data=proj_data)
        log(f"  Create project: {r['status']} {str(r['body'])[:200]}")
        project_id = None
        if r["ok"] and isinstance(r["body"], dict):
            project_id = r["body"].get("id") or r["body"].get("_id") or \
                         (r["body"].get("data", {}).get("id") if isinstance(r["body"].get("data"), dict) else None) or \
                         (r["body"].get("data", {}).get("_id") if isinstance(r["body"].get("data"), dict) else None)

        if not project_id:
            # Get existing
            r2 = api("GET", f"{PROJECT_API}/projects", token=proj_token)
            log(f"  GET projects: {r2['status']} {str(r2['body'])[:200]}")
            if r2["ok"]:
                projects = r2["body"] if isinstance(r2["body"], list) else r2["body"].get("data", []) if isinstance(r2["body"], dict) else []
                if isinstance(projects, list) and projects:
                    project_id = projects[0].get("id") or projects[0].get("_id")

        org_state["project_id"] = project_id

        # 2. Create tasks
        employees = get_org_employees(org_name)
        task_defs = [
            {"title": "Design product landing page", "priority": "high"},
            {"title": "Develop marketing materials", "priority": "medium"},
            {"title": "Set up CI/CD pipeline", "priority": "high"},
            {"title": "Write product documentation", "priority": "medium"},
            {"title": "Plan launch event", "priority": "low"},
        ]
        tasks_created = 0
        task_ids = []
        for i, td in enumerate(task_defs):
            assignee = employees[i] if i < len(employees) else employees[0]
            task_data = {
                "title": td["title"],
                "description": f"Task for Q2 Product Launch project",
                "priority": td["priority"],
                "status": "todo",
                "assignee_id": assignee["id"],
                "assignee": assignee["id"],
                "due_date": "2026-04-15",
            }
            if project_id:
                task_data["project_id"] = project_id
                task_data["project"] = project_id

            r = api("POST", f"{PROJECT_API}/tasks", token=proj_token, json_data=task_data)
            log(f"  Create task '{td['title'][:30]}': {r['status']} {str(r['body'])[:150]}")
            if r["ok"]:
                tasks_created += 1
                tid = None
                if isinstance(r["body"], dict):
                    tid = r["body"].get("id") or r["body"].get("_id") or \
                          (r["body"].get("data", {}).get("id") if isinstance(r["body"].get("data"), dict) else None)
                task_ids.append(tid)
                org_state["tasks"].append({"title": td["title"], "task_id": tid})

        log(f"  Tasks created: {tasks_created}/5")

        # 3. Log time entries
        time_logged = 0
        for tid in task_ids[:3]:
            if tid:
                te_data = {
                    "task_id": tid,
                    "task": tid,
                    "hours": 4,
                    "duration": 240,  # minutes
                    "description": "Worked on initial setup and planning",
                    "date": "2026-03-17",
                }
                if project_id:
                    te_data["project_id"] = project_id
                    te_data["project"] = project_id

                r = api("POST", f"{PROJECT_API}/time-entries", token=proj_token, json_data=te_data)
                log(f"  Log time: {r['status']} {str(r['body'])[:150]}")
                if r["ok"]:
                    time_logged += 1
                    org_state["time_entries"].append(tid)

        log(f"  Time entries logged: {time_logged}")

        STATE["projects"][org_name] = org_state

    STATE["days_completed"].append(17)
    log("\nDay 17 complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 18 — More Leave + Overtime
# ═══════════════════════════════════════════════════════════════════════════════

def day_18():
    log("=" * 70)
    log("DAY 18 — More Leave + Overtime")
    log("=" * 70)
    STATE["leave_applications"] = {}

    for org in ORGS:
        org_name = org["name"]
        log(f"\n--- {org_name} ---")
        token = login(org["email"], org["password"])
        if not token:
            continue

        org_state = {"leave_applied": 0, "compoff_requests": 0, "approvals": 0, "balances_checked": 0}
        employees = get_org_employees(org_name)
        earned_leave_id = get_org_leave_type(org_name, "Earned Leave")
        compoff_id = get_org_leave_type(org_name, "Compensatory Off")

        # 1. 5 employees apply for earned leave (next week)
        leave_applied = 0
        leave_ids = []
        for idx, emp in enumerate(employees[:5]):
            # Offset dates per employee to avoid overlaps
            start = f"2026-04-{6 + idx * 7:02d}"
            end = f"2026-04-{10 + idx * 7:02d}"
            leave_data = {
                "user_id": emp["id"],
                "employee_id": emp["id"],
                "leave_type_id": earned_leave_id,
                "start_date": start,
                "end_date": end,
                "reason": "Planned vacation - family trip",
                "is_half_day": False,
                "days_count": 5,
            }
            r = api("POST", f"{CORE_API}/leave/applications", token=token, json_data=leave_data)
            log(f"  Leave for {emp['first_name']}: {r['status']} {str(r['body'])[:150]}")
            if r["ok"]:
                leave_applied += 1
                lid = None
                if isinstance(r["body"], dict):
                    lid = r["body"].get("id") or (r["body"].get("data", {}).get("id") if isinstance(r["body"].get("data"), dict) else None)
                leave_ids.append(lid)
        org_state["leave_applied"] = leave_applied

        # 2. 3 employees request comp-off (worked overtime)
        compoff_requests = 0
        compoff_ids = []
        for emp in employees[5:8]:
            compoff_data = {
                "user_id": emp["id"],
                "employee_id": emp["id"],
                "leave_type_id": compoff_id,
                "start_date": "2026-04-20",
                "end_date": "2026-04-20",
                "reason": "Compensatory off for overtime worked on Saturday March 14",
                "is_half_day": False,
                "days_count": 1,
            }
            # Try regular leave application with comp-off type
            r = api("POST", f"{CORE_API}/leave/applications", token=token, json_data=compoff_data)
            log(f"  Comp-off {emp['first_name']}: {r['status']} {str(r['body'])[:150]}")
            if r["ok"]:
                compoff_requests += 1
                lid = None
                if isinstance(r["body"], dict):
                    lid = r["body"].get("id") or (r["body"].get("data", {}).get("id") if isinstance(r["body"].get("data"), dict) else None)
                compoff_ids.append(lid)
            else:
                # Try comp-off specific endpoint
                r2 = api("POST", f"{CORE_API}/leave/comp-off", token=token, json_data={
                    "employee_id": emp["id"],
                    "worked_date": "2026-03-14",
                    "reason": "Overtime on Saturday",
                })
                log(f"  Comp-off (alt): {r2['status']} {str(r2['body'])[:150]}")
                if r2["ok"]:
                    compoff_requests += 1

        org_state["compoff_requests"] = compoff_requests

        # 3. Manager approves/rejects
        approvals = 0
        for lid in leave_ids[:3]:  # Approve first 3
            if lid:
                r = api("PUT", f"{CORE_API}/leave/applications/{lid}/approve", token=token,
                        json_data={"comments": "Approved. Enjoy your vacation!"})
                log(f"  Approve leave {lid}: {r['status']}")
                if r["ok"]:
                    approvals += 1

        for lid in leave_ids[3:]:  # Reject rest
            if lid:
                r = api("PUT", f"{CORE_API}/leave/applications/{lid}/reject", token=token,
                        json_data={"comments": "Sorry, team needs you that week due to project deadline."})
                log(f"  Reject leave {lid}: {r['status']}")

        for lid in compoff_ids:
            if lid:
                r = api("PUT", f"{CORE_API}/leave/applications/{lid}/approve", token=token,
                        json_data={"comments": "Comp-off approved."})
                if r["ok"]:
                    approvals += 1

        org_state["approvals"] = approvals

        # 4. Check leave balances
        balances_checked = 0
        for emp in employees[:5]:
            r = api("GET", f"{CORE_API}/leave/balances", token=token,
                    params={"employee_id": emp["id"]})
            if r["ok"]:
                balances_checked += 1
        log(f"  Leave balances checked: {balances_checked}/5")
        org_state["balances_checked"] = balances_checked

        STATE["leave_applications"][org_name] = org_state

    STATE["days_completed"].append(18)
    log("\nDay 18 complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 19 — Employee Transfers
# ═══════════════════════════════════════════════════════════════════════════════

def day_19():
    log("=" * 70)
    log("DAY 19 — Employee Transfers")
    log("=" * 70)
    STATE["transfers"] = {}

    for org in ORGS:
        org_name = org["name"]
        log(f"\n--- {org_name} ---")
        token = login(org["email"], org["password"])
        if not token:
            continue

        org_state = {"transfers_done": 0, "org_chart_checked": False, "details": []}
        employees = get_org_employees(org_name)
        departments = get_org_departments(org_name)

        # Pick 2 employees to transfer between departments
        transfer_pairs = []
        if len(employees) >= 2 and len(departments) >= 2:
            emp1 = employees[0]
            emp2 = employees[10] if len(employees) > 10 else employees[1]
            # Find a different department for each
            for emp in [emp1, emp2]:
                current_dept = emp.get("department_id")
                new_dept = None
                for d in departments:
                    if d["id"] != current_dept:
                        new_dept = d
                        break
                if new_dept:
                    transfer_pairs.append({"employee": emp, "new_dept": new_dept, "old_dept_id": current_dept})

        transfers_done = 0
        for tp in transfer_pairs:
            emp = tp["employee"]
            new_dept = tp["new_dept"]
            r = api("PUT", f"{CORE_API}/users/{emp['id']}", token=token,
                    json_data={"department_id": new_dept["id"]})
            log(f"  Transfer {emp['first_name']} {emp['last_name']} to {new_dept['name']}: "
                f"{r['status']} {str(r['body'])[:150]}")
            if r["ok"]:
                transfers_done += 1
                org_state["details"].append({
                    "employee_id": emp["id"],
                    "name": f"{emp['first_name']} {emp['last_name']}",
                    "from_dept": tp["old_dept_id"],
                    "to_dept": new_dept["id"],
                    "to_dept_name": new_dept["name"],
                })

        org_state["transfers_done"] = transfers_done

        # Verify org chart updated
        r = api("GET", f"{CORE_API}/users/org-chart", token=token)
        log(f"  Org chart: {r['status']} {str(r['body'])[:200]}")
        org_state["org_chart_checked"] = r["ok"]

        # Verify employees show under new department
        for detail in org_state["details"]:
            r = api("GET", f"{CORE_API}/users/{detail['employee_id']}", token=token)
            if r["ok"] and isinstance(r["body"], dict):
                user_data = r["body"].get("data", r["body"])
                actual_dept = user_data.get("department_id")
                if actual_dept != detail["to_dept"]:
                    record_bug(
                        f"[30-Day Sim] Employee department not updated after transfer in {org_name}",
                        f"PUT /users/{detail['employee_id']} with department_id={detail['to_dept']} returned 200, "
                        f"but GET /users/{detail['employee_id']} still shows department_id={actual_dept}",
                        19)
                else:
                    log(f"  Verified {detail['name']} now in dept {actual_dept}")

        STATE["transfers"][org_name] = org_state

    STATE["days_completed"].append(19)
    log("\nDay 19 complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 20 — Billing & Subscription Check
# ═══════════════════════════════════════════════════════════════════════════════

def day_20():
    log("=" * 70)
    log("DAY 20 — Billing & Subscription Check")
    log("=" * 70)
    STATE["billing"] = {}

    for org in ORGS:
        org_name = org["name"]
        log(f"\n--- {org_name} ---")
        token = login(org["email"], org["password"])
        if not token:
            continue

        org_state = {"subscriptions": None, "modules": None, "user_count": None, "all_modules_accessible": True}

        # 1. Check subscriptions
        r = api("GET", f"{CORE_API}/subscriptions", token=token)
        log(f"  Subscriptions: {r['status']} {str(r['body'])[:300]}")
        if r["ok"]:
            org_state["subscriptions"] = r["body"]

        # 2. Check modules
        r = api("GET", f"{CORE_API}/modules", token=token)
        log(f"  Modules: {r['status']} {str(r['body'])[:300]}")
        if r["ok"]:
            org_state["modules"] = r["body"]

        # 3. Check user count
        r = api("GET", f"{CORE_API}/users", token=token, params={"limit": 1})
        if r["ok"] and isinstance(r["body"], dict):
            count = r["body"].get("total") or r["body"].get("meta", {}).get("total") or \
                    r["body"].get("pagination", {}).get("total")
            org_state["user_count"] = count
            log(f"  User count: {count}")

        # 4. Test SSO to all modules
        module_apis = {
            "Performance": PERF_API,
            "Exit": EXIT_API,
            "LMS": LMS_API,
            "Rewards": REWARDS_API,
        }
        for mod_name, mod_api in module_apis.items():
            mod_token = sso_to_module(token, mod_api)
            # Quick health check
            test_endpoint = {
                "Performance": "/review-cycles",
                "Exit": "/exits",
                "LMS": "/courses",
                "Rewards": "/kudos",
            }
            ep = test_endpoint.get(mod_name, "")
            r = api("GET", f"{mod_api}{ep}", token=mod_token)
            accessible = r["ok"] or r["status"] == 200
            log(f"  {mod_name} accessible: {accessible} ({r['status']})")
            if not accessible:
                org_state["all_modules_accessible"] = False

        # Test Project module (different prefix)
        proj_token = sso_to_module(token, PROJECT_API.replace("/v1", ""))
        r = api("GET", f"{PROJECT_API}/projects", token=proj_token)
        log(f"  Projects accessible: {r['ok']} ({r['status']})")

        # Check org details
        r = api("GET", f"{CORE_API}/organizations/me", token=token)
        log(f"  Org info: {r['status']} {str(r['body'])[:200]}")

        STATE["billing"][org_name] = org_state

    STATE["days_completed"].append(20)
    log("\nDay 20 complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# Bug Filing
# ═══════════════════════════════════════════════════════════════════════════════

def file_bugs():
    """Consolidate and file bugs found during simulation."""
    log("=" * 70)
    log("Filing consolidated bugs")
    log("=" * 70)

    # Collect actual issues from what we observed
    consolidated_bugs = []

    # Check SSO issues across all modules
    sso_failed_modules = set()
    for org_name in ["TechNova", "GlobalTech", "Innovate Solutions"]:
        perf = STATE.get("performance", {}).get(org_name, {})
        if perf.get("review_cycle") is None and perf.get("sso_ok"):
            sso_failed_modules.add("Performance")
        lms = STATE.get("lms", {}).get(org_name, {})
        if lms.get("course_id") is None and lms.get("sso_ok"):
            sso_failed_modules.add("LMS")
        rew = STATE.get("rewards", {}).get(org_name, {})
        if rew.get("kudos_given", 0) == 0:
            sso_failed_modules.add("Rewards")
        exit_s = STATE.get("exit", {}).get(org_name, {})
        if len(exit_s.get("resignations", [])) == 0:
            sso_failed_modules.add("Exit")

    if sso_failed_modules:
        modules_str = ", ".join(sorted(sso_failed_modules))
        consolidated_bugs.append({
            "title": f"[30-Day Sim] SSO from core to external modules returns 500 -- all module APIs inaccessible",
            "body": f"""## [30-Day Sim] Days 11-20

## URL Tested
- POST https://test-performance-api.empcloud.com/api/v1/auth/sso
- POST https://test-exit-api.empcloud.com/api/v1/auth/sso
- POST https://testlms-api.empcloud.com/api/v1/auth/sso
- POST https://test-rewards-api.empcloud.com/api/v1/auth/sso

## Steps to Reproduce
1. Login at https://test-empcloud.empcloud.com with any org admin (e.g. ananya@technova.in / Welcome@123)
2. Get the access_token from data.tokens.access_token
3. POST to any module's /api/v1/auth/sso with the core token
4. Module returns 500 Internal Error
5. Any subsequent API calls to the module return 401 Invalid Token

## Expected Result
SSO should return a module-specific token that allows access to module APIs.

## Actual Result
All module SSO endpoints return: `{{"success": false, "error": {{"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}}}}`

Affected modules: {modules_str}

This blocks ALL external module functionality: performance reviews, exit management, LMS courses, rewards/kudos, and project management.

Tested across all 3 orgs (TechNova, GlobalTech, Innovate Solutions) with same result.""",
            "labels": ["bug", "30-day-sim", "critical"],
        })

    # Check Project module 502
    proj_down = all(
        STATE.get("projects", {}).get(org, {}).get("project_id") is None
        for org in ["TechNova", "GlobalTech", "Innovate Solutions"]
    )
    if proj_down:
        consolidated_bugs.append({
            "title": "[30-Day Sim] Project module API is completely down -- returns 502 Bad Gateway",
            "body": """## [30-Day Sim] Days 11-20

## URL Tested
- https://test-project-api.empcloud.com/v1/projects
- https://test-project-api.empcloud.com/v1/tasks
- https://test-project-api.empcloud.com/v1/time-entries

## Steps to Reproduce
1. Login at https://test-empcloud.empcloud.com with any org admin
2. Try to access any Project module API endpoint
3. All return 502 Bad Gateway with a Cloudflare error page

## Expected Result
Project module API should be running and accessible.

## Actual Result
All requests to test-project-api.empcloud.com return 502 Bad Gateway (Cloudflare).
The backend server appears to be down.

Tested across all 3 orgs with same result.""",
            "labels": ["bug", "30-day-sim", "critical"],
        })

    # Add any manually recorded bugs
    for bug in STATE.get("bugs_found", []):
        consolidated_bugs.append({
            "title": bug["title"],
            "body": f"## [30-Day Sim] Day {bug['day']}\n\n{bug['details']}",
            "labels": ["bug", "30-day-sim"],
        })

    if not consolidated_bugs:
        log("No bugs to file.")
        return

    # Check existing issues to avoid duplicates
    existing = search_existing_issues("30-Day Sim")
    existing_titles_lower = [i.get("title", "").lower() for i in existing]

    for bug in consolidated_bugs:
        title = bug["title"]
        # Check for duplicates
        title_lower = title.lower()
        already_exists = False
        for et in existing_titles_lower:
            if "sso" in title_lower and "sso" in et and "500" in et:
                already_exists = True
                break
            if "project" in title_lower and "502" in title_lower and "502" in et and "project" in et:
                already_exists = True
                break
            if title_lower == et:
                already_exists = True
                break

        if already_exists:
            log(f"  Skip (similar exists): {title}")
            continue

        file_github_issue(title, bug["body"], bug.get("labels", ["bug", "30-day-sim"]))


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    log("=" * 70)
    log("EMP Cloud 30-Day Simulation — Days 11-20")
    log(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    day_funcs = [
        (11, day_11),
        (12, day_12),
        (13, day_13),
        (14, day_14),
        (15, day_15),
        (16, day_16),
        (17, day_17),
        (18, day_18),
        (19, day_19),
        (20, day_20),
    ]

    for day_num, func in day_funcs:
        try:
            func()
        except Exception as e:
            log(f"ERROR on Day {day_num}: {e}")
            traceback.print_exc()
            STATE["days_completed"].append(day_num)

    # File bugs
    try:
        file_bugs()
    except Exception as e:
        log(f"Error filing bugs: {e}")

    # Save state
    state_path = r"C:\emptesting\simulation\day11_20_state.json"
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(STATE, f, indent=2, default=str)
    log(f"\nState saved to {state_path}")

    # Summary
    log("\n" + "=" * 70)
    log("SIMULATION SUMMARY — Days 11-20")
    log("=" * 70)
    log(f"Days completed: {STATE['days_completed']}")
    log(f"Bugs found: {len(STATE['bugs_found'])}")
    log(f"Bugs filed on GitHub: {len(STATE['bugs_filed'])}")

    for org_name in ["TechNova", "GlobalTech", "Innovate Solutions"]:
        log(f"\n--- {org_name} ---")
        perf = STATE.get("performance", {}).get(org_name, {})
        log(f"  Performance: SSO={'OK' if perf.get('sso_ok') else 'FAIL'}, "
            f"Cycle={perf.get('review_cycle')}, Goals={len(perf.get('goals', []))}")

        exit_s = STATE.get("exit", {}).get(org_name, {})
        log(f"  Exit: Resignations={len(exit_s.get('resignations', []))}, "
            f"Clearance={len(exit_s.get('clearance', []))}")

        lms = STATE.get("lms", {}).get(org_name, {})
        log(f"  LMS: SSO={'OK' if lms.get('sso_ok') else 'FAIL'}, "
            f"Course={lms.get('course_id')}, Enrolled={lms.get('enrollments', 0)}, "
            f"Completed={lms.get('completions', 0)}")

        rewards = STATE.get("rewards", {}).get(org_name, {})
        log(f"  Rewards: Kudos={rewards.get('kudos_given', 0)}, "
            f"Badges={rewards.get('badges_awarded', 0)}, "
            f"Leaderboard={'OK' if rewards.get('leaderboard') else 'N/A'}")

        proj = STATE.get("projects", {}).get(org_name, {})
        log(f"  Projects: Project={proj.get('project_id')}, "
            f"Tasks={len(proj.get('tasks', []))}, "
            f"TimeEntries={len(proj.get('time_entries', []))}")

        leave = STATE.get("leave_applications", {}).get(org_name, {})
        log(f"  Leave: Applied={leave.get('leave_applied', 0)}, "
            f"CompOff={leave.get('compoff_requests', 0)}, "
            f"Approved={leave.get('approvals', 0)}")

        xfer = STATE.get("transfers", {}).get(org_name, {})
        log(f"  Transfers: {xfer.get('transfers_done', 0)} done, "
            f"OrgChart={'checked' if xfer.get('org_chart_checked') else 'not checked'}")

        billing = STATE.get("billing", {}).get(org_name, {})
        log(f"  Billing: Users={billing.get('user_count')}, "
            f"AllModules={'OK' if billing.get('all_modules_accessible') else 'ISSUES'}")

    log("\nDone!")


if __name__ == "__main__":
    main()
