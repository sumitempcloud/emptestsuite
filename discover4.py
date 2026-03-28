#!/usr/bin/env python3
import sys, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API = "https://test-empcloud.empcloud.com/api/v1"

r = requests.post(f"{API}/auth/login", json={
    "email": "ananya@technova.in", "password": "Welcome@123"
}, timeout=15)
token = r.json()["data"]["tokens"]["access_token"]
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Check employee login too
r2 = requests.post(f"{API}/auth/login", json={
    "email": "priya@technova.in", "password": "Welcome@123"
}, timeout=15)
emp_token = r2.json()["data"]["tokens"]["access_token"]
eh = {"Authorization": f"Bearer {emp_token}", "Content-Type": "application/json"}

# 1. Employee CRUD discovery
print("=== Employee endpoints ===")
# Get employee directory
r = requests.get(f"{API}/employees/directory", headers=h, timeout=10)
emps = r.json()["data"]
print(f"Directory has {len(emps)} employees")
if emps:
    print(f"First emp keys: {list(emps[0].keys())}")
    emp_id = emps[0]["id"]
    # Try GET single employee
    for ep in [f"/employees/{emp_id}", f"/employees/directory/{emp_id}", f"/users/{emp_id}"]:
        r = requests.get(f"{API}{ep}", headers=h, timeout=8)
        if r.status_code != 404:
            print(f"  GET {ep} -> {r.status_code}: {r.text[:200]}")

# Try POST employee
for ep in ["/employees", "/employees/create", "/employees/invite", "/users", "/users/invite"]:
    r = requests.post(f"{API}{ep}", headers=h, json={
        "first_name": "Test", "last_name": "User", "email": "testx@technova.in",
        "designation": "Tester", "department_id": 20, "role": "employee"
    }, timeout=8)
    if r.status_code != 404:
        print(f"  POST {ep} -> {r.status_code}: {r.text[:200]}")

# Try PUT/PATCH employee
for ep in [f"/employees/{emp_id}", f"/users/{emp_id}"]:
    r = requests.put(f"{API}{ep}", headers=h, json={"designation": "Test Update"}, timeout=8)
    if r.status_code != 404:
        print(f"  PUT {ep} -> {r.status_code}: {r.text[:200]}")
    r = requests.patch(f"{API}{ep}", headers=h, json={"designation": "Test Update"}, timeout=8)
    if r.status_code != 404:
        print(f"  PATCH {ep} -> {r.status_code}: {r.text[:200]}")

# 2. Department discovery
print("\n=== Department endpoints ===")
for ep in ["/departments", "/organization/departments", "/settings/departments"]:
    r = requests.get(f"{API}{ep}", headers=h, timeout=8)
    if r.status_code != 404:
        print(f"  GET {ep} -> {r.status_code}: {r.text[:200]}")

# 3. Leave - get existing structure
print("\n=== Leave details ===")
r = requests.get(f"{API}/leave/applications", headers=h, timeout=10)
apps = r.json()["data"]
print(f"Leave applications: {len(apps)}")
if apps:
    print(f"App keys: {list(apps[0].keys())}")
    print(f"First app: {json.dumps(apps[0])[:300]}")

# Try leave apply
for ep in ["/leave/apply", "/leave/applications"]:
    r = requests.post(f"{API}{ep}", headers=eh, json={
        "leave_type_id": 18, "start_date": "2026-04-15", "end_date": "2026-04-15",
        "reason": "Test leave", "days_count": 1
    }, timeout=8)
    if r.status_code != 404:
        print(f"  POST {ep} -> {r.status_code}: {r.text[:200]}")

# Leave balance
for ep in ["/leave/balance", "/leave/balances", "/leave/my-balance"]:
    r = requests.get(f"{API}{ep}", headers=eh, timeout=8)
    if r.status_code != 404:
        print(f"  GET {ep} (emp) -> {r.status_code}: {r.text[:200]}")

# 4. Attendance
print("\n=== Attendance ===")
r = requests.get(f"{API}/attendance/records", headers=h, timeout=10)
recs = r.json()["data"]
print(f"Attendance records: {len(recs)}")
if recs:
    print(f"Record keys: {list(recs[0].keys())}")

# Check out
for ep in ["/attendance/check-out", "/attendance/clock-out", "/attendance/checkout"]:
    r = requests.post(f"{API}{ep}", headers=h, json={}, timeout=8)
    if r.status_code != 404:
        print(f"  POST {ep} -> {r.status_code}: {r.text[:200]}")

# 5. Events - need correct format
print("\n=== Events detail ===")
r = requests.get(f"{API}/events", headers=h, timeout=10)
evts = r.json()["data"]
if evts:
    print(f"Event keys: {list(evts[0].keys())}")
    print(f"First event: {json.dumps(evts[0])[:300]}")

# Try with more fields
r = requests.post(f"{API}/events", headers=h, json={
    "title": "Test Event",
    "description": "Test",
    "event_type": "training",
    "start_date": "2026-04-15T09:00:00.000Z",
    "end_date": "2026-04-15T17:00:00.000Z",
    "location": "Office"
}, timeout=8)
print(f"  POST /events -> {r.status_code}: {r.text[:200]}")

# 6. Helpdesk tickets detail
print("\n=== Helpdesk ===")
r = requests.get(f"{API}/helpdesk/tickets", headers=h, timeout=10)
tix = r.json()["data"]
if tix:
    print(f"Ticket keys: {list(tix[0].keys())}")
    print(f"First ticket: {json.dumps(tix[0])[:300]}")

# Create ticket
r = requests.post(f"{API}/helpdesk/tickets", headers=h, json={
    "subject": "Test Ticket", "description": "Test desc", "category": "general", "priority": "medium"
}, timeout=8)
print(f"  POST /helpdesk/tickets -> {r.status_code}: {r.text[:200]}")

# 7. Forum posts detail
print("\n=== Forum ===")
r = requests.get(f"{API}/forum/posts", headers=h, timeout=10)
posts = r.json()["data"]
if posts:
    print(f"Post keys: {list(posts[0].keys())}")
    print(f"First post: {json.dumps(posts[0])[:300]}")

# Try with category_id
r = requests.post(f"{API}/forum/posts", headers=h, json={
    "title": "Test Post", "content": "Test content", "category_id": 1, "post_type": "discussion"
}, timeout=8)
print(f"  POST /forum/posts -> {r.status_code}: {r.text[:200]}")

# 8. Feedback detail
print("\n=== Feedback ===")
r = requests.get(f"{API}/feedback", headers=h, timeout=10)
fb = r.json()["data"]
if fb:
    print(f"Feedback keys: {list(fb[0].keys())}")
    print(f"First feedback: {json.dumps(fb[0])[:300]}")

r = requests.post(f"{API}/feedback", headers=eh, json={
    "category": "general", "subject": "Test FB", "message": "Test msg"
}, timeout=8)
print(f"  POST /feedback -> {r.status_code}: {r.text[:200]}")

# 9. Wellness checkin
print("\n=== Wellness ===")
for ep in ["/wellness/check-in", "/wellness/checkin", "/wellness/checkins", "/wellness/daily-checkin"]:
    r = requests.post(f"{API}{ep}", headers=eh, json={
        "mood": "good", "energy_level": 4, "sleep_hours": 7, "stress_level": 3
    }, timeout=8)
    if r.status_code != 404:
        print(f"  POST {ep} -> {r.status_code}: {r.text[:200]}")

for ep in ["/wellness/check-ins", "/wellness/checkins", "/wellness/my-checkins", "/wellness/history"]:
    r = requests.get(f"{API}{ep}", headers=eh, timeout=8)
    if r.status_code != 404:
        print(f"  GET {ep} -> {r.status_code}: {r.text[:200]}")

# 10. Whistleblowing
print("\n=== Whistleblowing ===")
for ep in ["/whistleblowing", "/whistleblower", "/anonymous-reports", "/reports/anonymous",
           "/whistleblowing/reports", "/reports"]:
    r = requests.post(f"{API}{ep}", headers=eh, json={
        "subject": "Test", "description": "Test report", "category": "misconduct"
    }, timeout=8)
    if r.status_code != 404:
        print(f"  POST {ep} -> {r.status_code}: {r.text[:200]}")
    r2 = requests.get(f"{API}{ep}", headers=h, timeout=8)
    if r2.status_code != 404:
        print(f"  GET {ep} -> {r2.status_code}: {r2.text[:200]}")

# 11. Documents upload
print("\n=== Documents ===")
r = requests.get(f"{API}/documents", headers=h, timeout=10)
docs = r.json()["data"]
if docs:
    print(f"Doc keys: {list(docs[0].keys())}")
    doc_id = docs[0]["id"]
    r = requests.get(f"{API}/documents/{doc_id}", headers=h, timeout=8)
    print(f"  GET /documents/{doc_id} -> {r.status_code}: {r.text[:200]}")

# Upload
import tempfile, os
tf = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
tf.write(b"test file content")
tf.close()
hh = {"Authorization": f"Bearer {token}"}
r = requests.post(f"{API}/documents", headers=hh,
    files={"file": ("test.txt", open(tf.name, "rb"), "text/plain")},
    data={"category_id": 15, "name": "TestDoc"}, timeout=10)
print(f"  POST /documents (upload) -> {r.status_code}: {r.text[:200]}")
os.unlink(tf.name)

# Users endpoint for employee management
print("\n=== Users endpoints ===")
for ep in ["/users", "/users/list", "/users/all", "/users/directory"]:
    r = requests.get(f"{API}{ep}", headers=h, timeout=8)
    if r.status_code != 404:
        print(f"  GET {ep} -> {r.status_code}: {r.text[:200]}")

# Leave balance for employee
print("\n=== Leave balance (employee) ===")
for ep in ["/leave/balance", "/leave/balances", "/leave/my-balance", "/leave/entitlements"]:
    r = requests.get(f"{API}{ep}", headers=eh, timeout=8)
    if r.status_code != 404:
        print(f"  GET {ep} (emp) -> {r.status_code}: {r.text[:200]}")
