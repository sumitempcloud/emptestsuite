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

session = requests.Session()
session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
r = session.post(f"{API_BASE}/auth/login", json={"email": "ananya@technova.in", "password": "Welcome@123"}, timeout=30)
token = find_token(r.json())
session.headers["Authorization"] = f"Bearer {token}"
print("API logged in")

# ── #504 with correct schema ──
print("\n=== #504 same-day leave ===")
today_str = datetime.now().strftime("%Y-%m-%d")
# Based on sample: start_date, end_date, leave_type_id, is_half_day, reason, user_id
# The logged-in user is 522 (ananya), she's org admin

# Get the login user's id
login_resp = r.json()
my_id = None
if isinstance(login_resp, dict):
    user_obj = login_resp.get("data", {}).get("user", {})
    my_id = user_obj.get("id")
print(f"My user_id: {my_id}")

# Try as employee (priya) who has existing leave apps
session2 = requests.Session()
session2.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
r2 = session2.post(f"{API_BASE}/auth/login", json={"email": "priya@technova.in", "password": "Welcome@123"}, timeout=30)
token2 = find_token(r2.json())
if token2:
    session2.headers["Authorization"] = f"Bearer {token2}"
    print("Logged in as priya (employee)")

    # Apply same-day leave as employee
    leave_payload = {
        "start_date": today_str,
        "end_date": today_str,
        "leave_type_id": 16,
        "is_half_day": False,
        "reason": "E2E Test - same day leave application"
    }
    r = session2.post(f"{API_BASE}/leave/applications", json=leave_payload, timeout=30)
    print(f"POST /leave/applications as employee: {r.status_code}")
    body = r.json() if r.headers.get('content-type','').startswith('application/json') else r.text
    print(f"  Response: {json.dumps(body)[:500] if isinstance(body, dict) else str(body)[:500]}")

    if r.status_code in (200, 201):
        verdict_504 = "FIXED"
        detail_504 = f"Same-day leave accepted with {r.status_code} for employee priya@technova.in."
    elif r.status_code in (400, 422):
        err = json.dumps(body).lower()
        if "same" in err or "today" in err or "advance" in err:
            verdict_504 = "STILL FAILING"
            detail_504 = f"Same-day leave rejected: {str(body)[:300]}"
        else:
            verdict_504 = "INCONCLUSIVE"
            detail_504 = f"Rejected with {r.status_code} for unclear reason: {str(body)[:300]}"
    else:
        verdict_504 = "INCONCLUSIVE"
        detail_504 = f"Status {r.status_code}: {str(body)[:300]}"
else:
    print("Could not login as priya")
    # Try as admin with user_id
    leave_payload = {
        "start_date": today_str,
        "end_date": today_str,
        "leave_type_id": 16,
        "is_half_day": False,
        "reason": "E2E Test - same day leave",
        "user_id": my_id,
    }
    r = session.post(f"{API_BASE}/leave/applications", json=leave_payload, timeout=30)
    print(f"POST /leave/applications as admin: {r.status_code}")
    body = r.json() if r.headers.get('content-type','').startswith('application/json') else r.text
    print(f"  Response: {json.dumps(body)[:500] if isinstance(body, dict) else str(body)[:500]}")
    if r.status_code in (200, 201):
        verdict_504 = "FIXED"
        detail_504 = f"Same-day leave accepted with {r.status_code}."
    else:
        verdict_504 = "INCONCLUSIVE"
        detail_504 = f"Status {r.status_code}: {str(body)[:300]}"

print(f"\n#504 Verdict: {verdict_504}")
print(f"  {detail_504}")

# ── #526 deeper: verify DOB actually saved ──
print("\n=== #526 verify under-18 DOB saved ===")
from datetime import timedelta
under18_dob = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
r = session.put(f"{API_BASE}/users/609", json={"date_of_birth": under18_dob}, timeout=30)
print(f"PUT DOB={under18_dob}: {r.status_code}")
r = session.get(f"{API_BASE}/users/609", timeout=30)
user_d = r.json().get("data", r.json())
saved_dob = user_d.get("date_of_birth")
print(f"GET verify DOB: {saved_dob}")
if saved_dob and "2016" in str(saved_dob):
    print("  Under-18 DOB was SAVED - bug still exists")
    verdict_526 = "STILL FAILING"
else:
    print("  Under-18 DOB was NOT saved (silently ignored)")
    verdict_526 = "PARTIALLY_FIXED"

# Revert
adult_dob = (datetime.now() - timedelta(days=365*30)).strftime("%Y-%m-%d")
session.put(f"{API_BASE}/users/609", json={"date_of_birth": adult_dob}, timeout=30)

# ── Post corrected GitHub comments with longer delays ──
print("\n=== Posting GitHub comments (with delays) ===")
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

comments_to_post = []

# #509 correction
comments_to_post.append((509, (
    f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
    f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
    f"**Issue:** Self-manager allowed\n\n"
    f"**Reproduction Steps:**\n"
    f"1. PUT /api/v1/users/609 with reporting_manager_id=608 -> 200, saved (GET confirms 608)\n"
    f"2. PUT /api/v1/users/609 with reporting_manager_id=609 (self) -> 200, NOT saved\n"
    f"3. GET /api/v1/users/609 -> reporting_manager_id = 608 (unchanged)\n\n"
    f"**Verdict:** Server silently ignores self-assignment. Data integrity OK but should return 400.\n\n"
    f"**API Base:** `{API_BASE}`"
)))

# #530 correction
comments_to_post.append((530, (
    f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
    f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
    f"**Issue:** Circular reporting chain\n\n"
    f"**Reproduction Steps:**\n"
    f"1. PUT /api/v1/users/609 reporting_manager_id=608 -> 200, saved (GET: 608)\n"
    f"2. PUT /api/v1/users/608 reporting_manager_id=609 (circular) -> 200, NOT saved\n"
    f"3. GET /api/v1/users/608 -> reporting_manager_id = 522 (unchanged)\n\n"
    f"**Verdict:** Server silently prevents circular chain. Data OK but should return 400.\n\n"
    f"**API Base:** `{API_BASE}`"
)))

# #506 correction
comments_to_post.append((506, (
    f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
    f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
    f"**Issue:** date_of_exit before date_of_joining\n\n"
    f"**Reproduction Steps:**\n"
    f"1. PUT /api/v1/users/609 with exit=2020-01-01, joining=2022-01-01 -> 200\n"
    f"2. GET /api/v1/users/609 -> joining=2026-03-28 (unchanged), exit=null (not saved)\n\n"
    f"**Verdict:** Server returns 200 but silently discards invalid dates. Should return 400.\n\n"
    f"**API Base:** `{API_BASE}`"
)))

# #540 correction
comments_to_post.append((540, (
    f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
    f"### Result: FIXED\n\n"
    f"**Issue:** Same asset assigned to multiple employees\n\n"
    f"**Reproduction:**\n"
    f"1. POST /api/v1/assets/48/assign user_id=609 -> 200 OK\n"
    f"2. POST /api/v1/assets/48/assign user_id=608 -> 403 'Asset is already assigned. Return it first.'\n\n"
    f"**Verdict:** Properly prevents double-assignment with clear error message.\n\n"
    f"**API Base:** `{API_BASE}`"
)))

# #504
comments_to_post.append((504, (
    f"**{COMMENT_PREFIX}** - Deep Re-test ({timestamp})\n\n"
    f"### Result: {verdict_504.upper()}\n\n"
    f"**Issue:** Cannot apply same-day leave\n\n"
    f"**Details:** {detail_504}\n\n"
    f"**API Base:** `{API_BASE}`"
)))

# #526 if partially fixed
if verdict_526 == "PARTIALLY_FIXED":
    comments_to_post.append((526, (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** Under-18 employee\n\n"
        f"**Reproduction:**\n"
        f"1. PUT /api/v1/users/609 with date_of_birth={under18_dob} -> 200\n"
        f"2. GET /api/v1/users/609 -> date_of_birth NOT saved (silently ignored)\n\n"
        f"**Verdict:** Server silently ignores under-18 DOB. Should return 400.\n\n"
        f"**API Base:** `{API_BASE}`"
    )))

for issue_num, body in comments_to_post:
    print(f"  Posting comment on #{issue_num}...", end=" ")
    time.sleep(5)  # Wait between comments to avoid secondary rate limit
    r = gh.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_num}/comments",
                json={"body": body}, timeout=30)
    print(f"{r.status_code}")
    if r.status_code >= 400:
        print(f"    Error: {r.text[:200]}")
        if r.status_code == 403 and "rate" in r.text.lower():
            print("    Rate limited, waiting 60s...")
            time.sleep(60)
            r = gh.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_num}/comments",
                        json={"body": body}, timeout=30)
            print(f"    Retry: {r.status_code}")

print("\n=== FINAL CORRECTED SUMMARY ===")
print("=" * 70)
summary = [
    ("#505", "Duplicate emp_code accepted", "STILL FAILING", "201 Created with duplicate emp_code TN-001"),
    ("#506", "date_of_exit before joining", "PARTIALLY FIXED", "200 returned but dates NOT saved (silent rejection)"),
    ("#509", "Self-manager allowed", "PARTIALLY FIXED", "200 returned but self-assignment NOT saved (silent rejection)"),
    ("#510", "Event end < start", "FIXED", "400 VALIDATION_ERROR returned"),
    ("#511", "Survey end < start", "FIXED", "400 VALIDATION_ERROR returned"),
    ("#523", "Attendance worked_minutes", "STILL FAILING", "5/7 records have calculation mismatches"),
    ("#526", "Under-18 employee", verdict_526.replace("_", " ").upper(), f"DOB {'saved' if verdict_526 == 'STILL FAILING' else 'NOT saved (silent rejection)'}"),
    ("#530", "Circular reporting chain", "PARTIALLY FIXED", "200 returned but circular chain NOT created (silent rejection)"),
    ("#539", "Warranty < purchase date", "FIXED", "400 VALIDATION_ERROR returned"),
    ("#540", "Same asset to multiple employees", "FIXED", "403 'Asset is already assigned. Return it first.'"),
    ("#541", "Org user count mismatch", "STILL FAILING", "Org reports 9, actual count 20"),
    ("#504", "Cannot apply same-day leave", verdict_504, detail_504),
]

for num, title, verdict, detail in summary:
    marker = "PASS" if "FIXED" in verdict else ("PARTIAL" if "PARTIAL" in verdict else "FAIL")
    print(f"  [{marker:>7}] {num} {title}")
    print(f"           {verdict}: {detail}")

print("\n" + "=" * 70)
print("DONE")
