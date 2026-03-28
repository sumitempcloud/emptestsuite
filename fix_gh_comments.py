import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import time
from datetime import datetime, timezone

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
COMMENT_PREFIX = "Comment by E2E Testing Agent"
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"

gh = requests.Session()
gh.headers.update({
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json",
})

# Test auth
r = gh.get("https://api.github.com/user", timeout=30)
print(f"GitHub auth check: {r.status_code}")
if r.status_code == 200:
    print(f"  Authenticated as: {r.json().get('login')}")
else:
    print(f"  Auth failed: {r.text[:200]}")
    # Try with Bearer instead
    gh.headers["Authorization"] = f"Bearer {GITHUB_PAT}"
    r = gh.get("https://api.github.com/user", timeout=30)
    print(f"  Bearer auth: {r.status_code}")

# Test repo access
r = gh.get(f"https://api.github.com/repos/{GITHUB_REPO}", timeout=30)
print(f"Repo access: {r.status_code}")
if r.status_code == 200:
    perms = r.json().get("permissions", {})
    print(f"  Permissions: {perms}")

# Test comment on issue 540
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

# Also need to do the leave test properly
session = requests.Session()
session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

# Login
def find_token(obj, depth=0):
    if depth > 5: return None
    if isinstance(obj, str) and len(obj) > 20: return obj
    if isinstance(obj, dict):
        for k in ["token", "access_token", "accessToken"]:
            if k in obj and isinstance(obj[k], str) and len(obj[k]) > 20: return obj[k]
        for k in obj:
            if isinstance(obj[k], dict):
                t = find_token(obj[k], depth+1)
                if t: return t
    return None

r = session.post(f"{API_BASE}/auth/login", json={"email": "ananya@technova.in", "password": "Welcome@123"}, timeout=30)
token = find_token(r.json())
session.headers["Authorization"] = f"Bearer {token}"
print(f"\nAPI login OK")

# ── #504: Try leave with proper payload ──
print("\n=== #504 same-day leave - thorough test ===")
today_str = datetime.now().strftime("%Y-%m-%d")

# Get leave types
r = session.get(f"{API_BASE}/leave/types", timeout=30)
print(f"Leave types: {r.status_code}")
lt_data = r.json()
lt_list = lt_data.get("data", [])
if isinstance(lt_list, list):
    for lt in lt_list[:5]:
        print(f"  id={lt.get('id')}, name={lt.get('name')}, type={lt.get('type')}")

# Try different payload structures
payloads = [
    {"from_date": today_str, "to_date": today_str, "leave_type_id": 16, "reason": "E2E same-day leave test"},
    {"start_date": today_str, "end_date": today_str, "leave_type_id": 16, "reason": "E2E same-day leave test"},
    {"from_date": today_str, "to_date": today_str, "type_id": 16, "reason": "E2E same-day leave test"},
    {"from_date": today_str, "to_date": today_str, "leave_type_id": 16, "reason": "E2E same-day leave test", "duration": "full_day"},
]

for i, payload in enumerate(payloads):
    r = session.post(f"{API_BASE}/leave/applications", json=payload, timeout=30)
    print(f"  Attempt {i+1} POST /leave/applications -> {r.status_code}")
    body = r.json() if r.headers.get('content-type','').startswith('application/json') else r.text
    print(f"    Payload: {json.dumps(payload)}")
    print(f"    Response: {json.dumps(body)[:500] if isinstance(body, dict) else str(body)[:500]}")
    if r.status_code in (200, 201):
        print(f"    Same-day leave ACCEPTED - bug #504 is FIXED")
        break
    elif r.status_code in (400, 422):
        err_msg = json.dumps(body).lower()
        if "same" in err_msg or "today" in err_msg or "advance" in err_msg or "past" in err_msg:
            print(f"    Same-day leave specifically rejected - bug #504 STILL FAILING")
        else:
            print(f"    Rejected for other validation reason, trying next payload...")

# Check what fields the leave/applications endpoint expects
r = session.get(f"{API_BASE}/leave/applications", params={"page": 1, "limit": 1}, timeout=30)
if r.status_code == 200:
    apps = r.json().get("data", [])
    if apps and isinstance(apps, list) and len(apps) > 0:
        print(f"  Sample leave application keys: {list(apps[0].keys())}")
        print(f"  Sample: {json.dumps(apps[0])[:500]}")

# ── Post all corrected GitHub comments ──
print("\n=== Posting GitHub comments ===")

corrections = {
    509: (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** Self-manager allowed\n\n"
        f"**Reproduction Steps:**\n"
        f"1. PUT /api/v1/users/609 with reporting_manager_id=608 -> 200 (saved correctly, verified via GET)\n"
        f"2. PUT /api/v1/users/609 with reporting_manager_id=609 (self) -> 200 (but NOT saved)\n"
        f"3. GET /api/v1/users/609 -> reporting_manager_id still = 608\n\n"
        f"**Verdict:** The server silently ignores self-assignment and keeps the previous manager value. "
        f"Data integrity is preserved, but the API should ideally return 400 with a clear error message "
        f"instead of returning 200 and silently discarding the update.\n\n"
        f"**API Base:** `{API_BASE}`"
    ),
    530: (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** Circular reporting chain\n\n"
        f"**Reproduction Steps:**\n"
        f"1. PUT /api/v1/users/609 with reporting_manager_id=608 -> 200, saved (verified via GET: 608)\n"
        f"2. PUT /api/v1/users/608 with reporting_manager_id=609 (would create circle) -> 200, NOT saved\n"
        f"3. GET /api/v1/users/608 -> reporting_manager_id = 522 (unchanged)\n\n"
        f"**Verdict:** The server silently prevents circular chains - the data integrity is maintained. "
        f"However, the API returns 200 instead of 400 with a clear error. Previous verdict of STILL FAILING "
        f"was incorrect - the circular chain is NOT actually created.\n\n"
        f"**API Base:** `{API_BASE}`"
    ),
    506: (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** date_of_exit before date_of_joining\n\n"
        f"**Reproduction Steps:**\n"
        f"1. PUT /api/v1/users/609 with date_of_exit=2020-01-01, date_of_joining=2022-01-01 -> 200\n"
        f"2. GET /api/v1/users/609 -> date_of_joining=2026-03-28 (unchanged), date_of_exit=null (not saved)\n\n"
        f"**Verdict:** The server returns 200 but silently ignores the invalid date combination. "
        f"Data integrity is preserved but the API should return 400 with validation error. "
        f"Previous verdict of STILL FAILING was incorrect - invalid dates are NOT actually saved.\n\n"
        f"**API Base:** `{API_BASE}`"
    ),
    540: (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: FIXED\n\n"
        f"**Issue:** Same asset assigned to multiple employees\n\n"
        f"**Reproduction Steps:**\n"
        f"1. POST /api/v1/assets/48/assign with user_id=609 -> 200 (assigned successfully)\n"
        f"2. POST /api/v1/assets/48/assign with user_id=608 -> 403 Forbidden\n"
        f"3. Error message: 'Asset is already assigned. Return it first.'\n\n"
        f"**Verdict:** FIXED. The server properly prevents double-assignment with a clear error message.\n\n"
        f"**API Base:** `{API_BASE}`"
    ),
}

for issue_num, body in corrections.items():
    r = gh.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_num}/comments",
                json={"body": body}, timeout=30)
    print(f"  Comment #{issue_num}: {r.status_code}")
    if r.status_code >= 400:
        print(f"    Error: {r.text[:300]}")
    time.sleep(1)

# Close issues that were incorrectly reopened (530 is actually partially fixed)
# Revert 530 and 506 state if they were reopened incorrectly
for issue_num in [530, 506]:
    # Check current state
    r = gh.get(f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_num}", timeout=30)
    if r.status_code == 200:
        state = r.json().get("state")
        print(f"  Issue #{issue_num} state: {state}")

print("\nDone.")
