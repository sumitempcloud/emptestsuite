#!/usr/bin/env python3
import sys, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API = "https://test-empcloud.empcloud.com/api/v1"

r = requests.post(f"{API}/auth/login", json={
    "email": "priya@technova.in", "password": "Welcome@123"
}, timeout=15)
emp_token = r.json()["data"]["tokens"]["access_token"]
eh = {"Authorization": f"Bearer {emp_token}", "Content-Type": "application/json"}

r2 = requests.post(f"{API}/auth/login", json={
    "email": "ananya@technova.in", "password": "Welcome@123"
}, timeout=15)
admin_token = r2.json()["data"]["tokens"]["access_token"]
ah = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

# Feedback - try different field combos
print("=== Feedback POST variations ===")
payloads = [
    {"category": "general", "subject": "Test", "message": "Test msg", "is_anonymous": False},
    {"category": "management", "subject": "Test", "message": "Test msg"},
    {"category": "workplace", "subject": "Test", "message": "Test msg"},
    {"category": "general", "subject": "Test", "message": "Test msg", "sentiment": "positive"},
]
for p in payloads:
    r = requests.post(f"{API}/feedback", headers=eh, json=p, timeout=8)
    print(f"  {json.dumps(p)} -> {r.status_code}: {r.text[:200]}")
    if r.status_code in (200, 201):
        break

# Whistleblowing
print("\n=== Whistleblowing POST variations ===")
payloads = [
    {"category": "misconduct", "subject": "Test Report", "description": "Test desc", "is_anonymous": True},
    {"category": "safety_violation", "subject": "Test Report", "description": "Test desc", "severity": "medium"},
    {"category": "misconduct", "severity": "low", "subject": "Test", "description": "Test report text", "is_anonymous": True},
]
for p in payloads:
    r = requests.post(f"{API}/whistleblowing/reports", headers=eh, json=p, timeout=8)
    print(f"  {json.dumps(p)} -> {r.status_code}: {r.text[:200]}")
    if r.status_code in (200, 201):
        break

# Documents upload - try different patterns
print("\n=== Document upload ===")
import tempfile, os
tf = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
tf.write("test document content for upload testing")
tf.close()
hh = {"Authorization": f"Bearer {admin_token}"}

for ep in ["/documents", "/documents/upload", "/documents/create"]:
    for field in ["file", "document", "attachment"]:
        r = requests.post(f"{API}{ep}", headers=hh,
            files={field: ("test_upload.txt", open(tf.name, "rb"), "text/plain")},
            data={"category_id": 15, "name": "TestUpload", "user_id": 522}, timeout=10)
        if r.status_code not in (404, 405):
            print(f"  POST {ep} field={field} -> {r.status_code}: {r.text[:200]}")

# Also try with JSON
r = requests.post(f"{API}/documents", headers=ah, json={
    "category_id": 15, "name": "TestDoc", "user_id": 522
}, timeout=8)
print(f"  POST /documents (json, no file) -> {r.status_code}: {r.text[:200]}")
os.unlink(tf.name)

# Events - try different formats
print("\n=== Events POST ===")
payloads = [
    {"title": "Test Event", "description": "Test", "event_type": "meeting",
     "start_date": "2026-04-15", "end_date": "2026-04-15", "is_all_day": True,
     "target_type": "all"},
    {"title": "Test Event", "description": "Test", "event_type": "meeting",
     "start_date": "2026-04-15T09:00:00Z", "end_date": "2026-04-15T17:00:00Z",
     "is_all_day": False, "target_type": "all"},
]
for p in payloads:
    r = requests.post(f"{API}/events", headers=ah, json=p, timeout=8)
    print(f"  {json.dumps(p)[:100]} -> {r.status_code}: {r.text[:200]}")
    if r.status_code in (200, 201):
        break

# Update/delete patterns for existing resources
print("\n=== Update/Delete patterns ===")

# Announcements
r = requests.get(f"{API}/announcements", headers=ah, timeout=10)
anns = r.json()["data"]
if anns:
    aid = anns[-1]["id"]
    r = requests.put(f"{API}/announcements/{aid}", headers=ah, json={"title": "Updated"}, timeout=8)
    print(f"  PUT /announcements/{aid} -> {r.status_code}: {r.text[:150]}")
    r = requests.patch(f"{API}/announcements/{aid}", headers=ah, json={"title": "Updated2"}, timeout=8)
    print(f"  PATCH /announcements/{aid} -> {r.status_code}: {r.text[:150]}")

# Tickets
r = requests.get(f"{API}/helpdesk/tickets", headers=ah, timeout=10)
tix = r.json()["data"]
if tix:
    tid = tix[-1]["id"]
    r = requests.put(f"{API}/helpdesk/tickets/{tid}", headers=ah, json={"status": "in_progress"}, timeout=8)
    print(f"  PUT /helpdesk/tickets/{tid} -> {r.status_code}: {r.text[:150]}")
    r = requests.patch(f"{API}/helpdesk/tickets/{tid}", headers=ah, json={"status": "in_progress"}, timeout=8)
    print(f"  PATCH /helpdesk/tickets/{tid} -> {r.status_code}: {r.text[:150]}")

# Forum posts
r = requests.get(f"{API}/forum/posts", headers=ah, timeout=10)
posts = r.json()["data"]
if posts:
    pid = posts[-1]["id"]
    r = requests.put(f"{API}/forum/posts/{pid}", headers=ah, json={"content": "Updated"}, timeout=8)
    print(f"  PUT /forum/posts/{pid} -> {r.status_code}: {r.text[:150]}")
    r = requests.delete(f"{API}/forum/posts/{pid}", headers=ah, timeout=8)
    print(f"  DELETE /forum/posts/{pid} -> {r.status_code}: {r.text[:150]}")

# Surveys
r = requests.get(f"{API}/surveys", headers=ah, timeout=10)
survs = r.json()["data"]
if survs:
    sid = survs[-1]["id"]
    r = requests.put(f"{API}/surveys/{sid}", headers=ah, json={"status": "active"}, timeout=8)
    print(f"  PUT /surveys/{sid} -> {r.status_code}: {r.text[:150]}")
    r = requests.patch(f"{API}/surveys/{sid}", headers=ah, json={"status": "active"}, timeout=8)
    print(f"  PATCH /surveys/{sid} -> {r.status_code}: {r.text[:150]}")
    r = requests.put(f"{API}/surveys/{sid}/publish", headers=ah, json={}, timeout=8)
    print(f"  PUT /surveys/{sid}/publish -> {r.status_code}: {r.text[:150]}")

# Assets
r = requests.get(f"{API}/assets", headers=ah, timeout=10)
assets = r.json()["data"]
if assets:
    asid = assets[-1]["id"]
    r = requests.put(f"{API}/assets/{asid}", headers=ah, json={"name": "Updated Asset"}, timeout=8)
    print(f"  PUT /assets/{asid} -> {r.status_code}: {r.text[:150]}")
    r = requests.delete(f"{API}/assets/{asid}", headers=ah, timeout=8)
    print(f"  DELETE /assets/{asid} -> {r.status_code}: {r.text[:150]}")

# Positions
r = requests.get(f"{API}/positions", headers=ah, timeout=10)
pos = r.json()["data"]
if pos:
    posid = pos[-1]["id"]
    r = requests.put(f"{API}/positions/{posid}", headers=ah, json={"title": "Updated Pos"}, timeout=8)
    print(f"  PUT /positions/{posid} -> {r.status_code}: {r.text[:150]}")
    r = requests.delete(f"{API}/positions/{posid}", headers=ah, timeout=8)
    print(f"  DELETE /positions/{posid} -> {r.status_code}: {r.text[:150]}")

# Events delete
r = requests.get(f"{API}/events", headers=ah, timeout=10)
evts = r.json()["data"]
if evts:
    eid = evts[-1]["id"]
    r = requests.put(f"{API}/events/{eid}", headers=ah, json={"title": "Updated Event"}, timeout=8)
    print(f"  PUT /events/{eid} -> {r.status_code}: {r.text[:150]}")
    r = requests.delete(f"{API}/events/{eid}", headers=ah, timeout=8)
    print(f"  DELETE /events/{eid} -> {r.status_code}: {r.text[:150]}")

# Leave cancel
r = requests.get(f"{API}/leave/applications", headers=ah, timeout=10)
leaves = r.json()["data"]
pending = [l for l in leaves if l["status"] == "pending"]
if pending:
    lid = pending[0]["id"]
    r = requests.patch(f"{API}/leave/applications/{lid}/cancel", headers=eh, json={}, timeout=8)
    print(f"  PATCH /leave/applications/{lid}/cancel -> {r.status_code}: {r.text[:150]}")
    r = requests.put(f"{API}/leave/applications/{lid}/cancel", headers=eh, json={}, timeout=8)
    print(f"  PUT /leave/applications/{lid}/cancel -> {r.status_code}: {r.text[:150]}")
    r = requests.patch(f"{API}/leave/applications/{lid}", headers=eh, json={"status": "cancelled"}, timeout=8)
    print(f"  PATCH /leave/applications/{lid} -> {r.status_code}: {r.text[:150]}")
print(f"  Pending leaves found: {len(pending)}")

# Documents delete
r = requests.get(f"{API}/documents", headers=ah, timeout=10)
docs = r.json()["data"]
if docs:
    did = docs[-1]["id"]
    r = requests.delete(f"{API}/documents/{did}", headers=ah, timeout=8)
    print(f"  DELETE /documents/{did} -> {r.status_code}: {r.text[:150]}")

# User deactivate
print("\n=== User deactivate ===")
r = requests.get(f"{API}/users", headers=ah, timeout=10)
users = r.json()["data"]
# Find the test user we created
test_users = [u for u in users if u.get("email") == "testx@technova.in"]
if test_users:
    uid = test_users[0]["id"]
    r = requests.patch(f"{API}/users/{uid}", headers=ah, json={"status": 0}, timeout=8)
    print(f"  PATCH /users/{uid} status=0 -> {r.status_code}: {r.text[:150]}")
    r = requests.put(f"{API}/users/{uid}/deactivate", headers=ah, json={}, timeout=8)
    print(f"  PUT /users/{uid}/deactivate -> {r.status_code}: {r.text[:150]}")
    r = requests.patch(f"{API}/users/{uid}/status", headers=ah, json={"status": "inactive"}, timeout=8)
    print(f"  PATCH /users/{uid}/status -> {r.status_code}: {r.text[:150]}")
    r = requests.delete(f"{API}/users/{uid}", headers=ah, timeout=8)
    print(f"  DELETE /users/{uid} -> {r.status_code}: {r.text[:150]}")
