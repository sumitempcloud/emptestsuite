"""
Run this script AFTER the GitHub secondary rate limit resets (~30 min after the main test).
Posts correction comments for bugs whose verdicts were refined by deeper investigation.
"""
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

corrections = [
    (509, "open", (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Correction: PARTIALLY FIXED (silent rejection, not fully broken)\n\n"
        f"**Issue:** Self-manager allowed\n\n"
        f"**Deeper investigation:**\n"
        f"1. PUT /users/609 reporting_manager_id=608 -> 200, saved (GET confirms: 608)\n"
        f"2. PUT /users/609 reporting_manager_id=609 (self) -> 200, but NOT saved\n"
        f"3. GET /users/609 -> reporting_manager_id=608 (unchanged)\n\n"
        f"**Corrected verdict:** Server silently ignores self-assignment and keeps the previous value. "
        f"Data integrity is preserved but the API should return 400 with an explicit error instead of "
        f"returning 200 and silently discarding the update.\n\n"
        f"**API Base:** `{API_BASE}`"
    )),
    (530, "open", (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Correction: PARTIALLY FIXED (silent rejection, not fully broken)\n\n"
        f"**Issue:** Circular reporting chain\n\n"
        f"**Deeper investigation:**\n"
        f"1. PUT /users/609 reporting_manager_id=608 -> 200, saved (GET confirms: 608)\n"
        f"2. PUT /users/608 reporting_manager_id=609 (would create circle) -> 200, but NOT saved\n"
        f"3. GET /users/608 -> reporting_manager_id=522 (unchanged, no circle created)\n\n"
        f"**Corrected verdict:** Server silently prevents circular chains. Data integrity is maintained "
        f"but the API should return 400 instead of 200.\n\n"
        f"**API Base:** `{API_BASE}`"
    )),
    (506, "open", (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Correction: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** date_of_exit before date_of_joining\n\n"
        f"**Deeper investigation:**\n"
        f"1. PUT /users/609 with exit=2020-01-01, joining=2022-01-01 -> 200\n"
        f"2. GET /users/609 -> date_of_joining unchanged, date_of_exit=null (not saved)\n\n"
        f"**Corrected verdict:** Server returns 200 but silently discards the invalid dates. "
        f"Data integrity is preserved but should return 400 with validation error.\n\n"
        f"**API Base:** `{API_BASE}`"
    )),
    (526, "open", (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Correction: PARTIALLY FIXED (silent rejection)\n\n"
        f"**Issue:** Under-18 employee\n\n"
        f"**Deeper investigation:**\n"
        f"1. PUT /users/609 date_of_birth=2016-03-30 (age ~10) -> 200\n"
        f"2. GET /users/609 -> date_of_birth=1996-04-04 (unchanged, under-18 DOB not saved)\n\n"
        f"**Corrected verdict:** Server silently ignores under-18 DOB. Data integrity preserved "
        f"but should return 400.\n\n"
        f"**API Base:** `{API_BASE}`"
    )),
    (540, None, (
        f"**{COMMENT_PREFIX}** - Deep Re-test Correction ({timestamp})\n\n"
        f"### Result: FIXED\n\n"
        f"**Issue:** Same asset assigned to multiple employees\n\n"
        f"1. POST /assets/48/assign user_id=609 -> 200 OK\n"
        f"2. POST /assets/48/assign user_id=608 -> 403 'Asset is already assigned. Return it first.'\n\n"
        f"Properly prevents double-assignment with clear error."
    )),
    (504, None, (
        f"**{COMMENT_PREFIX}** - Deep Re-test ({timestamp})\n\n"
        f"### Result: INCONCLUSIVE\n\n"
        f"**Issue:** Cannot apply same-day leave\n\n"
        f"POST /leave/applications with start_date=end_date=today returns 400 VALIDATION_ERROR "
        f"'Invalid request data'. Tested as both org admin and employee. The error message is generic "
        f"and does not indicate whether same-day is specifically rejected or if the payload schema "
        f"differs from expected. Manual verification recommended."
    )),
]

for issue_num, desired_state, body in corrections:
    print(f"\nPosting correction on #{issue_num}...", end=" ", flush=True)
    for attempt in range(5):
        try:
            r = gh.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_num}/comments",
                        json={"body": body}, timeout=30)
            print(f"{r.status_code}", end=" ")
            if r.status_code == 201:
                print("OK")
                break
            elif r.status_code == 403:
                retry_after = int(r.headers.get("Retry-After", 120))
                print(f"rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
            else:
                print(f"error: {r.text[:150]}")
                break
        except Exception as e:
            print(f"exception: {e}, retrying in 60s...")
            time.sleep(60)
    time.sleep(5)

print("\nDone posting corrections.")
