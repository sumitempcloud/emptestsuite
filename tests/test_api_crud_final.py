#!/usr/bin/env python3
"""
EMP Cloud HRMS — Final pass: File remaining bugs and print consolidated CRUD matrix.
"""

import urllib.request
import urllib.error
import json
import ssl
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://test-empcloud.empcloud.com/api/v1"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def file_github_issue(title, body_text):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    hdrs = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "EmpCloudCRUDTester/4.0",
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

now = datetime.now().isoformat()

# File remaining bugs discovered in pass 3
print("=" * 70)
print("Filing remaining confirmed bugs")
print("=" * 70)

file_github_issue(
    "[FUNCTIONAL] Feedback UPDATE/DELETE endpoints return 404",
    f"""## [FUNCTIONAL] Feedback PUT/DELETE /feedback/:id returns 404

**Endpoints:**
- `PUT {BASE}/feedback/16` -> 404
- `DELETE {BASE}/feedback/16` -> 404

Feedback can be created (POST) and listed (GET) but individual feedback items cannot be updated or deleted.
The PUT and DELETE methods on `/feedback/:id` return 404 NOT_FOUND.

**Steps to Reproduce:**
1. POST /feedback with {{"subject": "test", "message": "test", "category": "suggestion"}} -> 201 (success)
2. PUT /feedback/<new_id> with update data -> 404
3. DELETE /feedback/<new_id> -> 404

_Filed by automated CRUD tester on {now}_
""")

file_github_issue(
    "[FUNCTIONAL] Helpdesk Tickets DELETE returns 404",
    f"""## [FUNCTIONAL] Helpdesk Tickets DELETE /helpdesk/tickets/:id returns 404

**Endpoint:** `DELETE {BASE}/helpdesk/tickets/20`
**Response:** 404 NOT_FOUND

Helpdesk tickets can be created, read, and updated but cannot be deleted.

**Steps to Reproduce:**
1. POST /helpdesk/tickets -> 201 (creates ticket)
2. DELETE /helpdesk/tickets/<new_id> -> 404

_Filed by automated CRUD tester on {now}_
""")

file_github_issue(
    "[FUNCTIONAL] Leave Applications cancel (PUT status) returns 404",
    f"""## [FUNCTIONAL] Leave Applications PUT /leave/applications/:id returns 404

**Endpoint:** `PUT {BASE}/leave/applications/34`
**Request:** `{{"status": "cancelled"}}`
**Response:** 404 NOT_FOUND

Leave applications can be created and listed but cannot be updated/cancelled via PUT.

**Steps to Reproduce:**
1. POST /leave/applications with valid data -> 201
2. PUT /leave/applications/<id> with {{"status": "cancelled"}} -> 404

_Filed by automated CRUD tester on {now}_
""")

file_github_issue(
    "[FUNCTIONAL] Assets DELETE /assets/:id returns 404",
    f"""## [FUNCTIONAL] Assets DELETE endpoint returns 404

**Endpoint:** `DELETE {BASE}/assets/<id>`
**Response:** 404 NOT_FOUND

Assets can be created (POST), listed (GET), and updated (PUT), but DELETE returns 404.
Tested immediately after creating a new asset - the DELETE endpoint appears to not exist.

_Filed by automated CRUD tester on {now}_
""")

file_github_issue(
    "[FUNCTIONAL] Policies DELETE returns 200 but does not actually delete",
    f"""## [FUNCTIONAL] Policies soft-delete issue - GET still returns data after DELETE

**Endpoint:** `DELETE {BASE}/policies/<id>` -> 200 OK
**Verification:** `GET {BASE}/policies/<id>` -> 200 OK (still returns data)

The DELETE operation returns 200 success but the record is still fully accessible via GET.
There is no indication in the response that the item has been soft-deleted.

_Filed by automated CRUD tester on {now}_
""")

# ---------------------------------------------------------------
# CONSOLIDATED CRUD MATRIX
# ---------------------------------------------------------------
print("\n\n" + "=" * 120)
print("CONSOLIDATED CRUD MATRIX (All 3 passes combined)")
print("=" * 120)

# Compile all results across all passes
matrix = [
    # (Endpoint, CREATE, READ, UPDATE, DELETE, Required Fields, Notes)
    ("Users", "N/A", "PASS", "PASS", "N/A", "first_name, last_name, email, etc.", "PUT 200 but contact_number doesn't persist; first_name does"),
    ("Departments", "404", "404", "---", "---", "---", "Endpoint not found"),
    ("Locations", "404", "404", "---", "---", "---", "Endpoint not found"),
    ("Designations", "404", "404", "---", "---", "---", "Endpoint not found"),
    ("Attendance", "PASS*", "PASS", "N/A", "N/A", "none (empty body)", "Check-in/out OK (409=already done); GET via /attendance/records"),
    ("Shifts", "PASS", "PASS", "PASS", "PASS", "name, start_time, end_time", "Full CRUD lifecycle verified"),
    ("Leave Balances", "N/A", "PASS", "N/A", "N/A", "---", "Read-only endpoint"),
    ("Leave Types", "PASS", "PASS", "PASS", "---", "name, code, type, max_days_allowed, is_carry_forward", "CREATE + UPDATE verified"),
    ("Leave Applications", "PASS", "PASS", "BUG", "N/A", "leave_type_id, start_date, end_date, days_count, is_half_day, reason", "PUT cancel returns 404"),
    ("Leave Policies", "PASS", "PASS", "PASS", "---", "name, leave_type_id, annual_quota, accrual_type, accrual_rate", "Full CRU verified"),
    ("Comp-Off", "PASS", "PASS", "N/A", "N/A", "worked_date, reason, days, expires_on", "CREATE + READ verified"),
    ("Documents", "PASS", "PASS", "N/A", "PASS", "file (multipart), name, category_id", "Upload via /documents/upload; PDF only"),
    ("Document Categories", "PASS", "PASS", "---", "---", "name, description", "CREATE + READ verified"),
    ("Announcements", "PASS", "PASS", "PASS", "PASS", "title, content, date", "Full CRUD lifecycle verified + deletion confirmed"),
    ("Events", "PASS", "PASS", "PASS", "PASS", "title, description, start_date, end_date, location", "Full CRUD lifecycle verified + deletion confirmed"),
    ("Surveys", "PASS", "PASS", "PASS", "PASS", "title, description", "Full CRUD lifecycle verified + deletion confirmed"),
    ("Feedback", "PASS", "PASS", "BUG", "BUG", "subject, message, category", "PUT/DELETE return 404"),
    ("Assets", "PASS", "PASS", "PASS", "BUG", "name, asset_type, serial_number, status", "DELETE returns 404"),
    ("Asset Categories", "PASS", "PASS", "---", "---", "name, description", "CREATE + READ verified"),
    ("Positions", "PASS", "PASS", "PASS", "PASS", "title, department, location, description, status", "DELETE returns 200 'Position closed'"),
    ("Vacancies", "404", "PASS", "---", "---", "---", "POST to /positions/vacancies returns 404"),
    ("Helpdesk Tickets", "PASS", "PASS", "PASS", "BUG", "category, subject, description, priority", "DELETE returns 404"),
    ("Knowledge Base", "404", "404", "---", "---", "---", "Endpoint not found"),
    ("Forum Categories", "PASS", "PASS", "N/A", "N/A", "name, description", "CREATE + READ verified"),
    ("Forum Posts", "PASS", "PASS", "PASS", "PASS", "title, content, category_id", "Full CRUD lifecycle verified + deletion confirmed"),
    ("Policies", "PASS", "PASS", "PASS", "BUG*", "title, description, content, category", "DELETE returns 200 but data still accessible"),
    ("Wellness", "BUG", "PASS", "N/A", "N/A", "---", "GET /wellness/check-ins works; POST check-in always 400"),
    ("Wellness Programs", "PASS", "PASS", "---", "---", "title, description", "CREATE + READ verified"),
    ("Whistleblowing", "404", "404", "---", "---", "---", "Endpoint not found"),
    ("Notifications", "N/A", "PASS", "---", "N/A", "---", "Read OK; mark-read not testable (no notifications)"),
    ("Audit", "N/A", "PASS", "N/A", "N/A", "---", "Read-only endpoint"),
    ("Modules", "N/A", "PASS", "N/A", "N/A", "---", "Read-only endpoint"),
    ("Subscriptions", "400", "PASS", "---", "---", "---", "CREATE returns validation error"),
    ("Custom Fields", "404", "404", "---", "---", "---", "Endpoint not found"),
    ("Holidays", "404", "404", "---", "---", "---", "Endpoint not found"),
    ("Invitations", "404", "404", "---", "---", "---", "Endpoint not found"),
    ("Org Chart", "N/A", "404", "N/A", "N/A", "---", "Endpoint not found"),
    ("Dashboard", "N/A", "404", "N/A", "N/A", "---", "Endpoint not found"),
    ("Reports", "404", "404", "---", "---", "---", "Endpoint not found"),
    ("Settings", "N/A", "404", "---", "N/A", "---", "Endpoint not found"),
]

header = f"| {'Endpoint':<22} | {'CREATE':<12} | {'READ':<8} | {'UPDATE':<8} | {'DELETE':<8} | {'Required Fields':<55} | {'Notes':<50} |"
sep = "|" + "-" * 24 + "|" + "-" * 14 + "|" + "-" * 10 + "|" + "-" * 10 + "|" + "-" * 10 + "|" + "-" * 57 + "|" + "-" * 52 + "|"
print(header)
print(sep)

pass_count = 0
fail_count = 0
bug_count = 0
not_found_count = 0
na_count = 0

for row in matrix:
    ep, c, r, u, d, fields, notes = row
    line = f"| {ep:<22} | {c:<12} | {r:<8} | {u:<8} | {d:<8} | {fields[:55]:<55} | {notes[:50]:<50} |"
    print(line)
    for op in (c, r, u, d):
        if op.startswith("PASS"):
            pass_count += 1
        elif op.startswith("BUG"):
            bug_count += 1
        elif op == "404" or op == "400":
            fail_count += 1
        elif op in ("N/A", "---"):
            na_count += 1
        else:
            fail_count += 1

print(sep)

total_ops = pass_count + fail_count + bug_count
print(f"""
SUMMARY:
  PASS:              {pass_count}
  BUG (filed):       {bug_count}
  FAIL/404/400:      {fail_count}
  N/A or not tested: {na_count}
  --------------------------
  Total testable:    {total_ops}
  Pass rate:         {pass_count}/{total_ops} = {pass_count*100//max(total_ops,1)}%

ENDPOINTS FULLY WORKING (all CRUD):
  - Shifts (CREATE/READ/UPDATE/DELETE)
  - Announcements (CREATE/READ/UPDATE/DELETE + verified deletion)
  - Events (CREATE/READ/UPDATE/DELETE + verified deletion)
  - Surveys (CREATE/READ/UPDATE/DELETE + verified deletion)
  - Forum Posts (CREATE/READ/UPDATE/DELETE + verified deletion)
  - Positions (CREATE/READ/UPDATE/DELETE)

ENDPOINTS PARTIALLY WORKING:
  - Users (READ + UPDATE, but contact_number field update issue)
  - Leave Types (CREATE/READ/UPDATE)
  - Leave Applications (CREATE/READ, but cancel/PUT returns 404)
  - Leave Policies (CREATE/READ/UPDATE)
  - Comp-Off (CREATE/READ)
  - Documents (READ/UPLOAD/DELETE)
  - Assets (CREATE/READ/UPDATE, DELETE returns 404)
  - Feedback (CREATE/READ, UPDATE/DELETE return 404)
  - Helpdesk Tickets (CREATE/READ/UPDATE, DELETE returns 404)
  - Policies (CREATE/READ/UPDATE, DELETE doesn't actually remove)
  - Attendance (check-in/check-out work, GET via /attendance/records)

ENDPOINTS NOT FOUND (404):
  - Departments, Locations, Designations
  - Knowledge Base, Whistleblowing
  - Custom Fields, Holidays, Invitations
  - Org Chart, Dashboard, Reports, Settings

GITHUB ISSUES FILED: 18+ total across all passes
""")

print("=" * 120)
print("Test complete. Script: C:\\emptesting\\test_api_complete_crud.py (main)")
print("Pass 2: C:\\emptesting\\test_api_crud_pass2.py")
print("Pass 3: C:\\emptesting\\test_api_crud_pass3.py")
print("Final:  C:\\emptesting\\test_api_crud_final.py")
print("=" * 120)
