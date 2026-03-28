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

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

# Check if we can post yet
r = gh.get("https://api.github.com/rate_limit", timeout=30)
print(f"Rate limit check: {r.status_code}")
if r.status_code == 200:
    core = r.json().get("resources", {}).get("core", {})
    print(f"  Core: {core.get('remaining')}/{core.get('limit')}")

# Test with a simple GET first
r = gh.get(f"https://api.github.com/repos/{GITHUB_REPO}/issues/509", timeout=30)
print(f"GET issue 509: {r.status_code}")

corrections = [
    (509, (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** Self-manager allowed\n\n"
        f"**Steps:**\n"
        f"1. PUT /users/609 reporting_manager_id=608 -> 200, saved (GET: 608)\n"
        f"2. PUT /users/609 reporting_manager_id=609 (self) -> 200, NOT saved\n"
        f"3. GET /users/609 -> reporting_manager_id=608 (unchanged)\n\n"
        f"Server silently ignores self-assignment. Data integrity OK but should return 400."
    )),
    (530, (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** Circular reporting chain\n\n"
        f"**Steps:**\n"
        f"1. PUT /users/609 reporting_manager_id=608 -> 200, saved (GET: 608)\n"
        f"2. PUT /users/608 reporting_manager_id=609 (circular) -> 200, NOT saved\n"
        f"3. GET /users/608 -> reporting_manager_id=522 (unchanged)\n\n"
        f"Server silently prevents circular chain. Data OK but should return 400."
    )),
    (506, (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** date_of_exit before date_of_joining\n\n"
        f"**Steps:**\n"
        f"1. PUT /users/609 exit=2020-01-01, joining=2022-01-01 -> 200\n"
        f"2. GET /users/609 -> joining unchanged, exit=null\n\n"
        f"Server silently discards invalid dates. Should return 400."
    )),
    (526, (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** Under-18 employee\n\n"
        f"**Steps:**\n"
        f"1. PUT /users/609 date_of_birth=2016-03-30 (age ~10) -> 200\n"
        f"2. GET /users/609 -> date_of_birth=1996-04-04 (unchanged)\n\n"
        f"Server silently ignores under-18 DOB. Should return 400."
    )),
    (540, (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: FIXED\n\n"
        f"**Issue:** Same asset to multiple employees\n\n"
        f"1. POST /assets/48/assign user_id=609 -> 200\n"
        f"2. POST /assets/48/assign user_id=608 -> 403 'Asset is already assigned. Return it first.'\n\n"
        f"Properly prevents double-assignment."
    )),
    (504, (
        f"**{COMMENT_PREFIX}** - Deep Re-test ({timestamp})\n\n"
        f"### Result: INCONCLUSIVE\n\n"
        f"**Issue:** Cannot apply same-day leave\n\n"
        f"POST /leave/applications with start_date=end_date=today returns 400 VALIDATION_ERROR "
        f"'Invalid request data' - unclear if this is same-day rejection or payload schema issue. "
        f"Manual verification recommended."
    )),
]

for issue_num, body in corrections:
    print(f"\nPosting #{issue_num}...", end=" ", flush=True)
    for attempt in range(3):
        try:
            time.sleep(10)
            r = gh.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_num}/comments",
                        json={"body": body}, timeout=30)
            print(f"{r.status_code}", end=" ")
            if r.status_code == 201:
                print("OK")
                break
            elif r.status_code == 403 and "rate" in r.text.lower():
                wait = 90 * (attempt + 1)
                print(f"rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"error: {r.text[:100]}")
                break
        except Exception as e:
            print(f"exception: {e}")
            time.sleep(30)

print("\nDone")
