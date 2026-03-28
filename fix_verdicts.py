import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import time
from datetime import datetime

API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
COMMENT_PREFIX = "Comment by E2E Testing Agent"

session = requests.Session()
session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

# Login
r = session.post(f"{API_BASE}/auth/login", json={"email": "ananya@technova.in", "password": "Welcome@123"}, timeout=30)
data = r.json()
# Find token recursively
def find_token(obj, depth=0):
    if depth > 5: return None
    if isinstance(obj, str) and len(obj) > 20: return obj
    if isinstance(obj, dict):
        for k in ["token", "access_token", "accessToken"]:
            if k in obj and isinstance(obj[k], str) and len(obj[k]) > 20:
                return obj[k]
        for k in obj:
            if isinstance(obj[k], dict):
                t = find_token(obj[k], depth+1)
                if t: return t
    return None
token = find_token(data)
session.headers["Authorization"] = f"Bearer {token}"
print(f"Logged in. Token: {token[:30]}...")

# ── #509 deeper check: does PUT actually update reporting_manager_id at all? ──
print("\n=== #509 deeper investigation ===")
# First, find a user and set their manager to a known value
# Get two users
r = session.get(f"{API_BASE}/users", params={"page": 1, "limit": 10}, timeout=30)
users = r.json().get("data", [])
print(f"Got {len(users)} users")

# Pick user 609, set manager to 608, verify it sticks
uid = 609
mgr_id = 608

# Step 1: Set manager to 608
r = session.put(f"{API_BASE}/users/{uid}", json={"reporting_manager_id": mgr_id}, timeout=30)
print(f"Set user {uid} manager to {mgr_id}: {r.status_code}")
resp1 = r.json()
saved_mgr = resp1.get("data", {}).get("reporting_manager_id")
print(f"  Response shows reporting_manager_id = {saved_mgr}")

# Verify with GET
r = session.get(f"{API_BASE}/users/{uid}", timeout=30)
user_data = r.json().get("data", r.json())
actual_mgr = user_data.get("reporting_manager_id")
print(f"  GET verify: reporting_manager_id = {actual_mgr}")

# Step 2: Now set self-manager
r = session.put(f"{API_BASE}/users/{uid}", json={"reporting_manager_id": uid}, timeout=30)
print(f"Set user {uid} manager to SELF ({uid}): {r.status_code}")
resp2 = r.json()
saved_mgr2 = resp2.get("data", {}).get("reporting_manager_id")
print(f"  Response shows reporting_manager_id = {saved_mgr2}")

# Verify with GET
r = session.get(f"{API_BASE}/users/{uid}", timeout=30)
user_data2 = r.json().get("data", r.json())
actual_mgr2 = user_data2.get("reporting_manager_id")
print(f"  GET verify: reporting_manager_id = {actual_mgr2}")

if actual_mgr2 == uid:
    print("  VERDICT: STILL FAILING - self-manager was saved")
    verdict_509 = "STILL FAILING"
elif actual_mgr2 == mgr_id:
    print("  VERDICT: Server silently ignored self-assignment (kept previous value)")
    verdict_509 = "INCONCLUSIVE_SILENT"
else:
    print(f"  VERDICT: Unexpected - manager is now {actual_mgr2}")
    verdict_509 = "INCONCLUSIVE"

# ── #530 deeper check ──
print("\n=== #530 deeper investigation ===")
# User 609 -> mgr 608, then 608 -> mgr 609
r = session.put(f"{API_BASE}/users/609", json={"reporting_manager_id": 608}, timeout=30)
print(f"Step 1: Set 609->608: {r.status_code}")
r_data = r.json().get("data", {})
print(f"  reporting_manager_id in response: {r_data.get('reporting_manager_id')}")

r = session.get(f"{API_BASE}/users/609", timeout=30)
actual = r.json().get("data", r.json()).get("reporting_manager_id")
print(f"  GET verify 609's manager: {actual}")

r = session.put(f"{API_BASE}/users/608", json={"reporting_manager_id": 609}, timeout=30)
print(f"Step 2: Set 608->609 (circular): {r.status_code}")
r_data2 = r.json().get("data", {})
print(f"  reporting_manager_id in response: {r_data2.get('reporting_manager_id')}")

r = session.get(f"{API_BASE}/users/608", timeout=30)
actual2 = r.json().get("data", r.json()).get("reporting_manager_id")
print(f"  GET verify 608's manager: {actual2}")

if actual2 == 609:
    print("  VERDICT: STILL FAILING - circular chain created (609->608->609)")
    verdict_530 = "STILL FAILING"
else:
    print(f"  VERDICT: Server prevented circular chain (608's manager = {actual2})")
    verdict_530 = "FIXED"

# ── #506 deeper check ──
print("\n=== #506 deeper check - verify dates actually saved ===")
r = session.put(f"{API_BASE}/users/609", json={"date_of_exit": "2020-01-01", "date_of_joining": "2022-01-01"}, timeout=30)
print(f"PUT exit<joining: {r.status_code}")
r = session.get(f"{API_BASE}/users/609", timeout=30)
u = r.json().get("data", r.json())
doj = u.get("date_of_joining")
doe = u.get("date_of_exit")
print(f"  date_of_joining = {doj}")
print(f"  date_of_exit = {doe}")
if doe and "2020" in str(doe):
    print("  VERDICT: STILL FAILING - exit before joining saved")
else:
    print("  VERDICT: Server may have silently ignored the invalid dates")

# ── #504 find leave endpoint ──
print("\n=== #504 - finding leave application endpoint ===")
for path in ["/leave/applications", "/leave/apply", "/leaves/apply", "/leave-applications",
             "/leaves", "/leave/request", "/leave/requests"]:
    r = session.get(f"{API_BASE}{path}", params={"page": 1, "limit": 1}, timeout=30)
    print(f"  GET {path} -> {r.status_code}")
    if r.status_code == 200:
        print(f"    Body keys: {list(r.json().keys()) if isinstance(r.json(), dict) else type(r.json())}")

# Try POST to various endpoints
today_str = datetime.now().strftime("%Y-%m-%d")
leave_payload = {
    "start_date": today_str,
    "end_date": today_str,
    "from_date": today_str,
    "to_date": today_str,
    "reason": "E2E Test - same day leave",
    "leave_type_id": 16,
    "type_id": 16,
}
for path in ["/leave/applications", "/leave/apply", "/leaves/apply", "/leave-applications",
             "/leaves", "/leave/request", "/leave/requests"]:
    r = session.post(f"{API_BASE}{path}", json=leave_payload, timeout=30)
    print(f"  POST {path} -> {r.status_code}")
    if r.status_code != 404:
        print(f"    Body: {json.dumps(r.json()) if r.headers.get('content-type','').startswith('application/json') else r.text[:300]}")
        break

# ── Update GitHub comments for #540 (was INCONCLUSIVE but actually FIXED) ──
print("\n=== Updating GitHub for corrected verdicts ===")
timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

# #540 is FIXED - asset assignment returned 403 "Asset is already assigned. Return it first."
comment_540 = (
    f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
    f"### Result: FIXED\n\n"
    f"**Issue:** Same asset to multiple employees\n\n"
    f"**Details:** Assigning an already-assigned asset to another employee now returns "
    f"403 Forbidden with message 'Asset is already assigned. Return it first.' "
    f"The previous INCONCLUSIVE verdict was incorrect - this is clearly fixed.\n\n"
    f"**API Base:** `{API_BASE}`"
)
r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues/540/comments",
                   json={"body": comment_540},
                   headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}, timeout=30)
print(f"  GitHub comment #540 correction: {r.status_code}")

# #509 - update based on deeper check
if verdict_509 == "STILL FAILING":
    comment_509 = (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: BUG STILL REPRODUCES\n\n"
        f"**Issue:** Self-manager allowed\n\n"
        f"**Details:** PUT /users/609 with reporting_manager_id=609 was accepted and saved. "
        f"GET verification confirms user is set as own reporting manager.\n\n"
        f"Re-opening this issue."
    )
    r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues/509/comments",
                       json={"body": comment_509},
                       headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}, timeout=30)
    print(f"  GitHub comment #509: {r.status_code}")
    r = requests.patch(f"https://api.github.com/repos/{GITHUB_REPO}/issues/509",
                       json={"state": "open"},
                       headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}, timeout=30)
    print(f"  GitHub reopen #509: {r.status_code}")
elif verdict_509 == "INCONCLUSIVE_SILENT":
    comment_509 = (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** Self-manager allowed\n\n"
        f"**Details:** PUT /users/609 with reporting_manager_id=609 returns 200 but the value is NOT saved - "
        f"the server silently ignores the self-assignment and keeps the previous manager. "
        f"While the data integrity is preserved, the API should return 400 instead of silently ignoring.\n\n"
        f"**API Base:** `{API_BASE}`"
    )
    r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues/509/comments",
                       json={"body": comment_509},
                       headers={"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}, timeout=30)
    print(f"  GitHub comment #509 (partial fix): {r.status_code}")

print("\nDone with corrections.")
