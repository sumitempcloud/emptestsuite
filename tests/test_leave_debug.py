#!/usr/bin/env python3
import sys, json, urllib.request, urllib.error, ssl
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = "https://test-empcloud.empcloud.com/api/v1"
ctx = ssl.create_default_context()

def api(path, method="GET", data=None, token=None):
    url = f"{BASE}{path}"
    headers = {"User-Agent": "X", "Origin": "https://test-empcloud.empcloud.com",
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
    except Exception as e: return 0, str(e)

def login(email, pw):
    s, r = api("/auth/login", "POST", {"email": email, "password": pw})
    if s == 200:
        def ft(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if "token" in k.lower() and isinstance(v, str) and len(v) > 20: return v
                    f = ft(v)
                    if f: return f
            return None
        return ft(r)
    return None

emp_token = login("priya@technova.in", "Welcome@123")
admin_token = login("ananya@technova.in", "Welcome@123")

# Try every possible combo for leave
payloads = [
    {"leave_type_id": 18, "start_date": "2026-05-01", "end_date": "2026-05-01", "reason": "test", "is_half_day": False, "half_day_type": None},
    {"leave_type_id": 18, "start_date": "2026-05-02", "end_date": "2026-05-02", "reason": "test"},
    {"leave_type_id": "18", "start_date": "2026-05-03", "end_date": "2026-05-03", "reason": "test"},
    {"leaveTypeId": 18, "startDate": "2026-05-04", "endDate": "2026-05-04", "reason": "test"},
    {"leave_type_id": 18, "from_date": "2026-05-05", "to_date": "2026-05-05", "reason": "test"},
    {"type": 18, "start_date": "2026-05-06", "end_date": "2026-05-06", "reason": "test"},
    {"leave_type": 18, "start_date": "2026-05-07", "end_date": "2026-05-07", "reason": "test"},
    {"leave_type_id": 18, "start_date": "2026-05-08", "end_date": "2026-05-08", "reason": "test", "days": 1},
    {"leave_type_id": 18, "date_from": "2026-05-09", "date_to": "2026-05-09", "reason": "test"},
]

for p in payloads:
    s, r = api("/leave/applications", "POST", p, emp_token)
    print(f"  {list(p.keys())} -> {s}: {json.dumps(r)[:200]}")
    if s in (200, 201):
        print("  FOUND IT!")
        break

# Try alternate leave endpoints
print("\n--- Alternate leave endpoints ---")
for path in ["/leave/apply", "/leaves/apply", "/leave/request", "/leaves", "/leave-applications"]:
    s, r = api(path, "POST", {"leave_type_id": 18, "start_date": "2026-05-10", "end_date": "2026-05-10", "reason": "test"}, emp_token)
    print(f"  POST {path} -> {s}: {json.dumps(r)[:200]}")
    if s in (200, 201):
        print("  FOUND IT!")
        break

# Check if there's validation detail we can extract
print("\n--- Try with verbose error ---")
s, r = api("/leave/applications", "POST",
    {"leave_type_id": 18, "start_date": "2026-05-10", "end_date": "2026-05-10", "reason": "Test leave"},
    emp_token)
print(f"Full response: {json.dumps(r, indent=2)}")

# Try as OPTIONS to see allowed methods
print("\n--- OPTIONS ---")
s, r = api("/leave/applications", "OPTIONS", token=emp_token)
print(f"OPTIONS: {s}")
