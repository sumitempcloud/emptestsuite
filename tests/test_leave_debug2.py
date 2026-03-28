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

# Check all leave types to get valid IDs
s, r = api("/leave/types", token=emp_token)
print("Leave types:")
items = r.get("data", []) if isinstance(r, dict) else []
for item in items:
    print(f"  ID: {item.get('id')}, Name: {item.get('name')}, Code: {item.get('code')}")

# Check balances
s, r = api("/leave/balances", token=emp_token)
print("\nBalances:")
items = r.get("data", []) if isinstance(r, dict) else []
for item in items:
    print(f"  Type ID: {item.get('leave_type_id')}, Balance: {item.get('balance')}, Used: {item.get('total_used')}")

# Check existing applications to avoid date conflicts
s, r = api("/leave/applications", token=emp_token)
print("\nExisting applications:")
apps = r.get("data", []) if isinstance(r, dict) else []
for a in apps:
    print(f"  ID: {a.get('id')}, Type: {a.get('leave_type_id')}, {a.get('start_date')[:10]} to {a.get('end_date')[:10]}, Status: {a.get('status')}")

# Try with different leave type IDs and far-future dates
print("\n--- Trying each leave type with far-future dates ---")
for lt_id in [16, 17, 18, 19, 20]:
    payload = {
        "leave_type_id": lt_id,
        "start_date": "2026-06-15",
        "end_date": "2026-06-15",
        "reason": "CRUD testing"
    }
    s, r = api("/leave/applications", "POST", payload, emp_token)
    print(f"  type_id={lt_id} -> {s}: {json.dumps(r)[:200]}")
    if s in (200, 201):
        print("  SUCCESS!")
        break

# Maybe the issue is the employee doesn't have balances for those types
# Try with Casual Leave (type 18) which has balance 17
print("\n--- Different date formats ---")
for date_str in ["2026-07-01", "07/01/2026", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00.000Z"]:
    payload = {"leave_type_id": 18, "start_date": date_str, "end_date": date_str, "reason": "test"}
    s, r = api("/leave/applications", "POST", payload, emp_token)
    print(f"  date='{date_str}' -> {s}")

# Maybe it needs a specific field we're missing?
# Send empty POST to see what fields are required
print("\n--- Empty POST ---")
s, r = api("/leave/applications", "POST", {}, emp_token)
print(f"  Empty: {s}: {json.dumps(r)[:300]}")

# Try with all possible fields
print("\n--- All fields ---")
payload = {
    "leave_type_id": 18,
    "start_date": "2026-07-01",
    "end_date": "2026-07-01",
    "reason": "CRUD testing leave",
    "is_half_day": 0,
    "half_day_type": None,
    "days_count": 1,
    "status": "pending",
    "user_id": 524,
    "contact_number": "9876543210",
    "address": "test"
}
s, r = api("/leave/applications", "POST", payload, emp_token)
print(f"  All fields: {s}: {json.dumps(r)[:300]}")

# One more: maybe the token user is the admin employee (522) and we need priya (524)
print("\n--- Who am I? ---")
s, r = api("/auth/me", token=emp_token)
print(f"  /auth/me: {s}: {json.dumps(r)[:300]}")
s, r = api("/users/me", token=emp_token)
print(f"  /users/me: {s}: {json.dumps(r)[:300]}")
s, r = api("/profile", token=emp_token)
print(f"  /profile: {s}: {json.dumps(r)[:300]}")
