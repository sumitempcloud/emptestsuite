#!/usr/bin/env python3
import sys, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API = "https://test-empcloud.empcloud.com/api/v1"

# Login and get token
r = requests.post(f"{API}/auth/login", json={
    "email": "ananya@technova.in", "password": "Welcome@123"
}, timeout=15)
token = r.json()["data"]["tokens"]["access_token"]
print(f"Token: {token[:60]}...")

h = {"Authorization": f"Bearer {token}"}

# Comprehensive endpoint scan
endpoints = [
    # Auth/User
    "/me", "/auth/me", "/user/me", "/profile", "/auth/profile", "/users/me",
    # Employees
    "/employees", "/employee", "/employees/list", "/employee/list",
    "/employees/all", "/employee/all", "/employees/directory",
    "/organization/employees", "/org/employees", "/people",
    # Departments
    "/departments", "/department", "/departments/list", "/organization/departments",
    # Leave
    "/leaves", "/leave", "/leave/list", "/leaves/list",
    "/leave/balance", "/leaves/balance", "/leave/types", "/leaves/types",
    "/leave/my", "/leave/applications",
    # Attendance
    "/attendance", "/attendance/list", "/attendance/today",
    "/attendance/clock-in", "/attendance/check-in", "/attendance/checkin",
    "/attendance/my", "/attendance/records",
    # Documents
    "/documents", "/document", "/documents/list", "/documents/my",
    "/documents/categories",
    # Announcements
    "/announcements", "/announcement", "/announcements/list",
    # Events
    "/events", "/event", "/events/list", "/calendar",
    # Surveys
    "/surveys", "/survey", "/surveys/list",
    # Tickets / Helpdesk
    "/tickets", "/ticket", "/helpdesk", "/helpdesk/tickets",
    "/support", "/support/tickets",
    # Assets
    "/assets", "/asset", "/assets/list",
    # Positions / Jobs
    "/positions", "/position", "/jobs", "/vacancies",
    "/recruitment", "/recruitment/positions",
    # Forum
    "/forum", "/forum/posts", "/forum/topics", "/posts",
    # Wellness
    "/wellness", "/wellness/checkin", "/wellness/programs",
    # Feedback
    "/feedback", "/feedbacks", "/feedback/list",
    # Whistleblowing
    "/whistleblowing", "/whistleblow", "/reports",
    # Settings
    "/settings", "/organization/settings", "/settings/general",
    "/settings/departments", "/settings/leave-types",
    # Misc
    "/notifications", "/policies", "/org-chart",
    "/modules", "/billing", "/chatbot",
    "/comp-off", "/leave/comp-off",
    # Manager
    "/manager", "/manager/team", "/my-team",
]

results_by_status = {}
for ep in endpoints:
    try:
        r = requests.get(f"{API}{ep}", headers=h, timeout=8)
        code = r.status_code
        if code not in results_by_status:
            results_by_status[code] = []
        try:
            body = json.dumps(r.json())[:200]
        except:
            body = r.text[:200]
        results_by_status[code].append((ep, body))
    except Exception as e:
        print(f"  ERROR {ep}: {e}")

for code in sorted(results_by_status.keys()):
    eps = results_by_status[code]
    print(f"\n=== HTTP {code} ({len(eps)} endpoints) ===")
    for ep, body in eps:
        print(f"  {ep}: {body}")

# Now test POST endpoints for creating things
print("\n\n=== Testing POST endpoints ===")
post_tests = [
    ("/attendance/clock-in", {}),
    ("/attendance/check-in", {}),
    ("/attendance/checkin", {}),
    ("/leave/apply", {"leave_type": "casual", "from_date": "2026-04-10", "to_date": "2026-04-10", "reason": "test"}),
    ("/leaves/apply", {"leave_type": "casual", "from_date": "2026-04-10", "to_date": "2026-04-10", "reason": "test"}),
    ("/leaves", {"leave_type": "casual", "from_date": "2026-04-10", "to_date": "2026-04-10", "reason": "test"}),
    ("/documents", {"title": "test"}),
    ("/announcements", {"title": "test", "content": "test"}),
    ("/events", {"title": "test", "date": "2026-04-10"}),
    ("/surveys", {"title": "test"}),
    ("/tickets", {"subject": "test", "description": "test"}),
    ("/helpdesk", {"subject": "test", "description": "test"}),
    ("/assets", {"name": "test"}),
    ("/positions", {"title": "test"}),
    ("/forum", {"title": "test", "content": "test"}),
    ("/forum/posts", {"title": "test", "content": "test"}),
    ("/wellness/checkin", {"mood": "good"}),
    ("/feedback", {"title": "test", "message": "test"}),
    ("/whistleblowing", {"description": "test"}),
    ("/departments", {"name": "test"}),
]

for ep, payload in post_tests:
    try:
        r = requests.post(f"{API}{ep}", headers={**h, "Content-Type": "application/json"},
                          json=payload, timeout=8)
        if r.status_code not in (404, 405):
            try:
                body = json.dumps(r.json())[:200]
            except:
                body = r.text[:200]
            print(f"  POST {ep} -> {r.status_code}: {body}")
    except Exception as e:
        print(f"  POST {ep} -> ERROR: {e}")
