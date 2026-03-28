#!/usr/bin/env python3
"""Investigate remaining failures: feedback, leave, wellness"""

import sys, json, urllib.request, urllib.error, ssl, time
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://test-empcloud.empcloud.com/api/v1"
ctx = ssl.create_default_context()

def api(path, method="GET", data=None, token=None):
    url = f"{BASE}{path}"
    headers = {"User-Agent": "EmpCloud-CRUD-Tester/3.0", "Origin": "https://test-empcloud.empcloud.com",
               "Accept": "application/json", "Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try: return resp.status, json.loads(raw)
            except: return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try: return e.code, json.loads(raw)
        except: return e.code, raw
    except Exception as e:
        return 0, str(e)

def login(email, password):
    s, r = api("/auth/login", "POST", {"email": email, "password": password})
    if s == 200 and isinstance(r, dict):
        def ft(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if "token" in k.lower() and isinstance(v, str) and len(v) > 20: return v
                    f = ft(v)
                    if f: return f
            return None
        return ft(r)
    return None

admin_token = login("ananya@technova.in", "Welcome@123")
emp_token = login("priya@technova.in", "Welcome@123")
ts = int(time.time())

# ── Feedback: try with exact structure matching existing data ──
print("--- FEEDBACK (matching existing structure) ---")
# existing has: category, subject, message, sentiment, is_urgent
for payload in [
    {"category": "management", "subject": f"Test {ts}", "message": "Test message"},
    {"category": "management", "subject": f"Test {ts}", "message": "Test message", "is_urgent": False},
    {"category": "management", "subject": f"Test {ts}", "message": "Test message", "sentiment": "neutral", "is_urgent": False},
    {"category": "management", "subject": f"Test {ts}", "message": "Test", "is_anonymous": False},
]:
    s, r = api("/feedback", "POST", payload, emp_token)
    print(f"  emp POST /feedback {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        print("  SUCCESS!")
        break

# Try as admin
for payload in [
    {"category": "management", "subject": f"Test {ts}", "message": "Test"},
    {"category": "general", "subject": f"Test {ts}", "message": "Test"},
]:
    s, r = api("/feedback", "POST", payload, admin_token)
    print(f"  admin POST /feedback {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        print("  SUCCESS!")
        break

# ── Leave: try with exact structure matching existing ──
print("\n--- LEAVE (matching existing structure) ---")
# existing has: leave_type_id, start_date, end_date, days_count, is_half_day, half_day_type, reason
for payload in [
    {"leave_type_id": 18, "start_date": "2026-04-28", "end_date": "2026-04-28", "reason": "Test", "is_half_day": False},
    {"leave_type_id": 18, "start_date": "2026-04-28", "end_date": "2026-04-28", "reason": "Test", "is_half_day": 0, "days_count": 1},
    {"leave_type_id": 18, "start_date": "2026-04-28T00:00:00.000Z", "end_date": "2026-04-28T00:00:00.000Z", "reason": "Test", "is_half_day": 0},
]:
    s, r = api("/leave/applications", "POST", payload, emp_token)
    print(f"  emp POST {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        print("  SUCCESS!")
        break

# Try as admin
for payload in [
    {"leave_type_id": 18, "start_date": "2026-04-28", "end_date": "2026-04-28", "reason": "Test", "is_half_day": False},
    {"leave_type_id": 18, "start_date": "2026-04-28", "end_date": "2026-04-28", "reason": "Test", "user_id": 524},
]:
    s, r = api("/leave/applications", "POST", payload, admin_token)
    print(f"  admin POST {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        print("  SUCCESS!")
        break

# ── Wellness: try with exact structure ──
print("\n--- WELLNESS (matching existing structure) ---")
# existing has: check_in_date, mood, energy_level, sleep_hours, exercise_minutes, notes
for payload in [
    {"check_in_date": "2026-03-28", "mood": "great", "energy_level": 3, "sleep_hours": 7, "exercise_minutes": 30},
    {"check_in_date": "2026-03-28", "mood": "great", "energy_level": 3},
    {"mood": "great", "energy_level": 3, "sleep_hours": 7, "exercise_minutes": 30},
    {"mood": "good", "energy_level": 4},
    {"check_in_date": "2026-03-28", "mood": "good", "energy_level": 4, "sleep_hours": 7.0, "exercise_minutes": 30, "notes": "test"},
]:
    s, r = api("/wellness/check-in", "POST", payload, emp_token)
    print(f"  emp POST /wellness/check-in {list(payload.keys())} -> {s}: {json.dumps(r)[:300]}")
    if s in (200, 201):
        print("  SUCCESS!")
        break

# Try check-ins plural (POST)
for payload in [
    {"check_in_date": "2026-03-28", "mood": "good", "energy_level": 4},
]:
    s, r = api("/wellness/check-ins", "POST", payload, emp_token)
    print(f"  emp POST /wellness/check-ins -> {s}: {json.dumps(r)[:300]}")

# Try /wellness directly
s, r = api("/wellness", "POST", {"mood": "good", "energy_level": 4, "check_in_date": "2026-03-28"}, emp_token)
print(f"  emp POST /wellness -> {s}: {json.dumps(r)[:300]}")

# ── Assets DELETE: investigate routing ──
print("\n--- ASSETS DELETE investigation ---")
# List existing assets
s, r = api("/assets", token=admin_token)
if s == 200:
    items = r.get("data", []) if isinstance(r, dict) else []
    if items:
        aid = items[-1].get("id")
        print(f"  Trying to delete asset {aid}...")
        for method in ["DELETE"]:
            for path in [f"/assets/{aid}", f"/asset/{aid}"]:
                sd, rd = api(path, method, token=admin_token)
                print(f"  {method} {path} -> {sd}: {json.dumps(rd)[:200]}")
        # Try with body
        sd, rd = api(f"/assets/{aid}", "DELETE", {"id": aid}, admin_token)
        print(f"  DELETE /assets/{aid} with body -> {sd}: {json.dumps(rd)[:200]}")
        # Try PUT to archive
        sd, rd = api(f"/assets/{aid}", "PUT", {"status": "retired"}, admin_token)
        print(f"  PUT /assets/{aid} status=retired -> {sd}: {json.dumps(rd)[:200]}")

print("\nDone.")
