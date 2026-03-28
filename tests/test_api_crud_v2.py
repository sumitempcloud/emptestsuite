#!/usr/bin/env python3
"""EMP Cloud HRMS - CRUD Tester v2: Investigate validation failures and fix them"""

import sys
import json
import urllib.request
import urllib.error
import ssl
import time
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://test-empcloud.empcloud.com/api/v1"
ctx = ssl.create_default_context()

def make_request(url, method="GET", data=None, token=None):
    headers = {
        "User-Agent": "EmpCloud-CRUD-Tester/2.0",
        "Origin": "https://test-empcloud.empcloud.com",
        "Accept": "application/json",
        "Content-Type": "application/json",
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
            except:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(raw)
        except:
            return e.code, raw
    except Exception as e:
        return 0, str(e)

def api(path, method="GET", data=None, token=None):
    url = f"{BASE}{path}"
    return make_request(url, method, data, token)

def login(email, password):
    s, r = api("/auth/login", "POST", {"email": email, "password": password})
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
        return find_token(r)
    return None

def extract_items(resp):
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for key in ["data", "items", "results", "records"]:
            if key in resp and isinstance(resp[key], list):
                return resp[key]
            if key in resp and isinstance(resp.get(key), dict):
                for k2 in ["items", "rows", "records"]:
                    if k2 in resp[key] and isinstance(resp[key][k2], list):
                        return resp[key][k2]
    return []

print("=" * 70)
print("  INVESTIGATING VALIDATION FAILURES")
print("=" * 70)

admin_token = login("ananya@technova.in", "Welcome@123")
emp_token = login("priya@technova.in", "Welcome@123")
print(f"Admin token: {'OK' if admin_token else 'FAIL'}")
print(f"Employee token: {'OK' if emp_token else 'FAIL'}")
ts = int(time.time())

# ── 1. Investigate Users CREATE ──
print("\n--- USERS CREATE ---")
# Try various payloads to understand required fields
for payload in [
    {"email": f"test{ts}@technova.in", "password": "Welcome@123", "name": "Test User", "role": "employee"},
    {"email": f"test{ts}@technova.in", "password": "Welcome@123", "first_name": "Test", "last_name": "User"},
    {"email": f"test{ts}@technova.in", "password": "Welcome@123", "first_name": "Test", "last_name": "User", "department_id": 1, "designation": "Tester"},
]:
    s, r = api("/users", "POST", payload, admin_token)
    print(f"  POST /users {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        cid = r.get("data", {}).get("id") if isinstance(r.get("data"), dict) else None
        print(f"  Created ID: {cid}")
        if cid:
            api(f"/users/{cid}", "DELETE", token=admin_token)
        break

# ── 2. Investigate Surveys CREATE ──
print("\n--- SURVEYS CREATE ---")
# Get existing survey to see structure
s, r = api("/surveys", token=admin_token)
items = extract_items(r)
if items:
    print(f"  Existing survey structure: {json.dumps(items[0])[:500]}")
    sid = items[0].get("id")
    if sid:
        s2, r2 = api(f"/surveys/{sid}", token=admin_token)
        print(f"  Detail: {json.dumps(r2)[:500]}")

for payload in [
    {"title": f"Test Survey {ts}", "description": "Test", "status": "draft"},
    {"title": f"Test Survey {ts}", "description": "Test", "type": "general", "is_anonymous": False},
    {"title": f"Test Survey {ts}", "description": "Test", "start_date": "2026-04-01", "end_date": "2026-04-30"},
    {"title": f"Test Survey {ts}", "description": "Test", "questions": [{"text": "Q1?", "type": "text"}]},
    {"title": f"Test Survey {ts}", "description": "Test", "questions": [{"question_text": "Q1?", "question_type": "text", "is_required": True}]},
]:
    s, r = api("/surveys", "POST", payload, admin_token)
    print(f"  POST /surveys {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        cid = r.get("data", {}).get("id") if isinstance(r.get("data"), dict) else None
        if cid:
            api(f"/surveys/{cid}", "DELETE", token=admin_token)
        break

# ── 3. Investigate Feedback CREATE ──
print("\n--- FEEDBACK CREATE ---")
s, r = api("/feedback", token=admin_token)
items = extract_items(r)
if items:
    print(f"  Existing feedback structure: {json.dumps(items[0])[:500]}")

for payload in [
    {"subject": f"Test Feedback {ts}", "message": "Test feedback message", "type": "general"},
    {"title": f"Test Feedback {ts}", "description": "Test feedback", "type": "suggestion"},
    {"feedback": "Test feedback text", "type": "general", "category": "general"},
    {"subject": f"Test {ts}", "message": "Test", "category": "general", "anonymous": False},
    {"subject": f"Test {ts}", "message": "Test", "type": "suggestion", "target_type": "organization"},
    {"feedback_type": "suggestion", "subject": f"Test {ts}", "message": "Test message"},
]:
    s, r = api("/feedback", "POST", payload, admin_token)
    print(f"  POST /feedback {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        break

# ── 4. Investigate Leave CREATE ──
print("\n--- LEAVE CREATE ---")
s, r = api("/leave/types", token=admin_token)
types = extract_items(r)
if types:
    print(f"  Leave types: {json.dumps(types[:3])[:500]}")

s, r = api("/leave/applications", token=admin_token)
apps = extract_items(r)
if apps:
    print(f"  Existing application structure: {json.dumps(apps[0])[:500]}")

leave_type_id = types[0]["id"] if types else 1
from_d = "2026-04-27"
to_d = "2026-04-27"

for payload in [
    {"leave_type_id": leave_type_id, "from_date": from_d, "to_date": to_d, "reason": "Test"},
    {"leave_type_id": leave_type_id, "start_date": from_d, "end_date": to_d, "reason": "Test"},
    {"type_id": leave_type_id, "from_date": from_d, "to_date": to_d, "reason": "Test"},
    {"leave_type_id": leave_type_id, "from_date": from_d, "to_date": to_d, "reason": "Test", "day_type": "full_day"},
    {"leave_type_id": leave_type_id, "start_date": from_d, "end_date": to_d, "reason": "Test", "duration_type": "full_day"},
]:
    s, r = api("/leave/applications", "POST", payload, emp_token)
    print(f"  POST /leave/applications {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        break

# ── 5. Investigate Forum POST ──
print("\n--- FORUM POST ---")
s, r = api("/forum/posts", token=admin_token)
items = extract_items(r)
if items:
    print(f"  Existing post structure: {json.dumps(items[0])[:500]}")

# Try /forum/categories
s, r = api("/forum/categories", token=admin_token)
print(f"  GET /forum/categories: {s} -> {json.dumps(r)[:300]}")
cats = extract_items(r)
cat_id = cats[0].get("id") if cats else None

for payload in [
    {"title": f"Test Post {ts}", "content": "Test content", "category_id": cat_id},
    {"title": f"Test Post {ts}", "body": "Test content", "category_id": cat_id},
    {"title": f"Test Post {ts}", "content": "Test content"},
    {"title": f"Test Post {ts}", "content": "Test content", "category_id": cat_id, "type": "discussion"},
]:
    s, r = api("/forum/posts", "POST", payload, admin_token)
    print(f"  POST /forum/posts {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        cid = r.get("data", {}).get("id") if isinstance(r.get("data"), dict) else None
        if cid:
            api(f"/forum/posts/{cid}", "DELETE", token=admin_token)
        break

# ── 6. Investigate Wellness POST ──
print("\n--- WELLNESS CHECK-IN ---")
s, r = api("/wellness/check-ins", token=emp_token)
items = extract_items(r)
if items:
    print(f"  Existing check-in structure: {json.dumps(items[0])[:500]}")

for payload in [
    {"mood": 4, "energy_level": 4, "notes": "Test"},
    {"mood_score": 4, "energy_level": 4, "stress_level": 3},
    {"mood": "good", "energy": "high", "date": "2026-03-28"},
    {"mood_score": 4, "energy_level": 4, "stress_level": 3, "notes": "Test", "date": "2026-03-28"},
]:
    s, r = api("/wellness/check-ins", "POST", payload, emp_token)
    print(f"  POST /wellness/check-ins {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        break
    # Also try the singular
    s2, r2 = api("/wellness/check-in", "POST", payload, emp_token)
    print(f"  POST /wellness/check-in {list(payload.keys())} -> {s2}: {json.dumps(r2)[:300]}")
    if s2 in (200, 201):
        break

# ── 7. Investigate Assets DELETE ──
print("\n--- ASSETS DELETE ---")
# Create, then try delete
s, r = api("/assets", "POST", {
    "name": f"Delete Test {ts}",
    "serial_number": f"DEL-{ts}",
    "status": "available",
}, admin_token)
print(f"  POST /assets -> {s}")
if s in (200, 201):
    aid = r.get("data", {}).get("id") if isinstance(r.get("data"), dict) else None
    if aid:
        print(f"  Created asset ID: {aid}")
        s2, r2 = api(f"/assets/{aid}", "DELETE", token=admin_token)
        print(f"  DELETE /assets/{aid} -> {s2}: {json.dumps(r2)[:200]}")
        # Check if it's a soft delete
        s3, r3 = api(f"/assets/{aid}", token=admin_token)
        print(f"  GET /assets/{aid} after delete -> {s3}: {json.dumps(r3)[:200]}")

# ── 8. Check user update verify ──
print("\n--- USER UPDATE VERIFY ---")
s, r = api("/users", token=admin_token)
items = extract_items(r)
if items:
    uid = items[0].get("id")
    # Get current state
    s1, r1 = api(f"/users/{uid}", token=admin_token)
    print(f"  User {uid} current: {json.dumps(r1)[:400]}")

    # Try update with different phone fields
    for payload in [
        {"contact_number": "9999888877"},
        {"phone": "9999888877"},
        {"mobile_number": "9999888877"},
        {"personal_phone": "9999888877"},
    ]:
        su, ru = api(f"/users/{uid}", "PUT", payload, admin_token)
        print(f"  PUT /users/{uid} {payload} -> {su}: {json.dumps(ru)[:200]}")

print("\n" + "=" * 70)
print("  INVESTIGATION COMPLETE")
print("=" * 70)
