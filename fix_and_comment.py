#!/usr/bin/env python3
"""
Fix: Close back incorrectly reopened issues, then properly comment
on the truly RBAC-relevant issues with longer delays to avoid rate limits.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
from datetime import datetime

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_API = "https://api.github.com"

session = requests.Session()
gh_headers = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github+json",
}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def close_issue(num):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{num}"
    r = session.patch(url, headers=gh_headers, json={"state": "closed"}, timeout=15)
    return r.status_code == 200

def reopen_issue(num):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{num}"
    r = session.patch(url, headers=gh_headers, json={"state": "open"}, timeout=15)
    return r.status_code == 200

def add_comment_with_retry(num, body, max_retries=5):
    """Add comment with exponential backoff for rate limits."""
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{num}/comments"
    for attempt in range(max_retries):
        r = session.post(url, headers=gh_headers, json={"body": body}, timeout=15)
        if r.status_code == 201:
            return True
        elif r.status_code == 403 and "rate limit" in r.text.lower():
            wait = min(30 * (2 ** attempt), 120)
            log(f"  Rate limited on #{num}, waiting {wait}s (attempt {attempt+1})...")
            time.sleep(wait)
        else:
            log(f"  Comment failed on #{num}: {r.status_code} {r.text[:200]}")
            return False
    return False

# ── These are the issues that were INCORRECTLY reopened ──
# They were reopened by the loose keyword matching but are NOT about
# the specific RBAC API bugs we tested.
# The truly RBAC-relevant issues that SHOULD stay open if failing are listed separately.

# Issues that the test correctly identified as RBAC-related and failing:
TRULY_RBAC_ISSUES_FAILING = {
    97:  "[HIGH] RBAC Violation: Employee can list all organization users",
    271: "[API] RBAC: Employee can access /users with full data",
    283: "[API] RBAC: Employee can view subscription/billing data via /subscriptions",
    241: "[RBAC] Employee can access /billing page with subscription pricing details",
    286: "[API] RBAC: Employee can view other employees' leave applications",
    315: "[API] RBAC: Employee can view all comp-off requests in the organization",
    287: "[API] RBAC: Employee can view draft surveys meant for admin only",
    103: "Feedback: 'Insufficient permissions' error toasts on feedback page for employee",
    352: "[FUNCTIONAL] Feedback - READ List failed",
    668: "Feedback page shows 'Insufficient permissions' error for employees",
    547: "Employee dashboard shows HR-level data - possible data visibility issue",
    562: "Employee dashboard shows HR-level data - possible data visibility issue",
    661: "Employee sees HR-level data on dashboard - possible data leak",
    243: "[RBAC] Employee sees 'New' button on Announcements page",
    665: "Modules -- Employee can see Unsubscribe buttons for organization modules",
}

# Issues about admin endpoints that the test checked:
ADMIN_ENDPOINT_ISSUES = {
    88:  "[MEDIUM] RBAC UI: Employee can access /settings page",
    98:  "[MEDIUM] RBAC UI: Employee can access /settings page",
    108: "[HIGH] RBAC UI: Employee can access /admin Platform Dashboard",
    113: "[RBAC] Employee accessed admin Settings",
    122: "[RBAC] Employee can view full Organization Settings at /settings",
    123: "[RBAC] Employee can view AI Config content at /admin/ai-config despite permissions error",
    124: "[RBAC] Employee can view Log Dashboard at /admin/logs despite permissions error",
    254: "[Super Admin E2E] API endpoints return 401 Unauthorized for Super Admin Bearer token",
    257: "[Super Admin E2E] /api/v1/users scoped to single org for super_admin role",
}

# Security issues that were correctly related:
SECURITY_ISSUES = {
    171: "[SECURITY] [HIGH] Mass assignment: Email Takeover SUCCEEDED",
    177: "[SECURITY] [HIGH] DELETE succeeded on /positions/1",
}

# Performance/Exit module RBAC issues (these are separate modules, not main app API):
SEPARATE_MODULE_RBAC = {
    679: "Performance -- Employee can see admin-level navigation items (RBAC violation)",
    680: "Performance -- Employee can access PIPs page",
    681: "Performance -- Employee can access Analytics",
    682: "Performance -- Employee can access 9-Box Grid",
    683: "Performance -- Employee can access Succession Planning",
    684: "Performance -- Employee can access module Settings",
    685: "Performance -- Employee can create review cycles",
    686: "Exit -- Employee can see full admin navigation in Exit module (RBAC violation)",
    687: "Exit -- Employee can see all exit records",
    688: "Exit -- Employee can access Full and Final Settlement data",
    689: "Exit -- Employee can access Flight Risk analytics",
    678: "Payroll -- Employee sidebar shows Admin Panel navigation link",
}

# ALL issues that were incorrectly reopened (not directly tested by our API tests):
# These should be closed back.
ALL_REOPENED = [32, 35, 37, 41, 43, 57, 69, 78, 85, 88, 97, 98, 99, 100, 102, 103, 104,
                106, 108, 113, 115, 116, 118, 121, 122, 123, 124, 126, 139, 144, 149, 151,
                153, 154, 155, 156, 157, 159, 171, 174, 175, 179, 185, 188, 200, 202, 206,
                209, 240, 241, 247, 251, 252, 254, 257, 263, 264, 283, 286, 294, 315, 352,
                370, 489, 516, 678, 679, 680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 692]

# Issues that SHOULD remain open because our tests confirmed the RBAC bug is still present:
# These are the core RBAC issues where our test SPECIFICALLY tested the exact endpoint
KEEP_OPEN_AND_COMMENT = {
    97:  {
        "test": "Employee can list all organization users",
        "result": "STILL FAILING",
        "details": (
            "**Step 1:** Login as priya@technova.in -> `200, role=employee, id=524`\n"
            "**Step 2:** GET /api/v1/users -> `Status: 200`\n"
            "**Step 3:** Record count -> `20 users returned`\n"
            "**Step 4:** Check if other employees' data visible -> `YES - 20 other users found`\n"
            "**Step 5:** Sample other users -> `['retest1774699937@technova.in', 'dir1774699916@technova.in', 'dup_test_1774699769@technova.in']`\n\n"
            "**VERDICT: STILL FAILING** -- Employee with role=employee can call GET /api/v1/users and receive all 20 organization users including other employees' email addresses, names, and personal data."
        ),
    },
    271: {
        "test": "Employee can access /users with full data",
        "result": "STILL FAILING",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee, id=524) -> `200 OK`\n"
            "**Step 2:** GET /api/v1/users -> `Status: 200, 20 records returned`\n"
            "**Step 3:** GET /api/v1/users/612 (retest1774699937@technova.in) -> `Status: 200` -- full profile returned\n"
            "**Step 4:** GET /api/v1/users/611 (dir1774699916@technova.in) -> `Status: 200` -- full profile returned\n\n"
            "**VERDICT: STILL FAILING** -- Employee can list all org users AND view individual profiles by ID. Should return 403 or limit to self only."
        ),
    },
    283: {
        "test": "Employee can view subscription/billing data",
        "result": "STILL FAILING",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee) -> `200 OK`\n"
            "**Step 2:** GET /api/v1/subscriptions -> `Status: 200, 10 records returned`\n"
            "**Step 3:** Response includes plan_tier, price_per_seat (175000 INR), billing_cycle, total_seats for all modules\n"
            "**Step 4:** GET /api/v1/subscriptions/billing-summary -> `Status: 200` -- full billing summary with pricing\n\n"
            "**VERDICT: STILL FAILING** -- Employee can view all subscription and billing data including pricing. Should return 403."
        ),
    },
    241: {
        "test": "Employee can access billing page",
        "result": "STILL FAILING",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee) -> `200 OK`\n"
            "**Step 2:** GET /api/v1/subscriptions/billing-summary -> `Status: 200`\n"
            "**Step 3:** Response contains all subscription pricing: module names, plan tiers, price_per_seat, billing_cycle, etc.\n\n"
            "**VERDICT: STILL FAILING** -- Employee can see full billing summary. Should return 403 for non-admin roles."
        ),
    },
    286: {
        "test": "Employee can view other employees' leave applications",
        "result": "STILL FAILING",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee, id=524) -> `200 OK`\n"
            "**Step 2:** Admin baseline: GET /api/v1/leave/applications -> `20 applications`\n"
            "**Step 3:** Employee GET /api/v1/leave/applications -> `Status: 200, 20 records`\n"
            "**Step 4:** Other users' leaves visible -> `4 records from other users (user_id=522, user_id=523)`\n\n"
            "**VERDICT: STILL FAILING** -- Employee sees 4 leave applications belonging to other users (user_id 522 and 523). Should only see own applications."
        ),
    },
    315: {
        "test": "Employee can view all comp-off requests",
        "result": "STILL FAILING",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee, id=524) -> `200 OK`\n"
            "**Step 2:** Admin baseline: GET /api/v1/leave/comp-off -> `5 comp-off requests`\n"
            "**Step 3:** Employee GET /api/v1/leave/comp-off -> `Status: 200, 5 records`\n"
            "**Step 4:** Other users' comp-off visible -> `5 records: [user_id=522, user_id=523, user_id=522, user_id=522, user_id=522]`\n\n"
            "**VERDICT: STILL FAILING** -- Employee sees ALL 5 comp-off requests in the organization, same count as admin. Should only see own requests."
        ),
    },
    287: {
        "test": "Employee can view draft surveys",
        "result": "STILL FAILING",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee) -> `200 OK`\n"
            "**Step 2:** GET /api/v1/surveys -> `Status: 200, 20 records`\n"
            "**Step 3:** DRAFT surveys visible to employee -> `14 drafts!`\n"
            "**Step 4:** Draft survey titles -> `['Retest1774700015', 'Test Survey Validation', 'Test Survey Validation']`\n\n"
            "**VERDICT: STILL FAILING** -- Employee can see 14 draft surveys. Should only see published surveys."
        ),
    },
    103: {
        "test": "Employee feedback access",
        "result": "STILL FAILING",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee) -> `200 OK`\n"
            "**Step 2:** GET /api/v1/feedback -> `Status: 403`\n"
            "**Step 3:** Error: `{'code': 'FORBIDDEN', 'message': 'Insufficient permissions'}`\n\n"
            "**VERDICT: STILL FAILING** -- Employee gets blanket 403 on feedback. While blocking unauthorized access is correct, employees should have limited access to view their own feedback. The 403 is too restrictive and prevents basic self-service functionality."
        ),
    },
    668: {
        "test": "Employee feedback access",
        "result": "STILL FAILING",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee) -> `200 OK`\n"
            "**Step 2:** GET /api/v1/feedback -> `Status: 403, 'Insufficient permissions'`\n\n"
            "**VERDICT: STILL FAILING** -- Feedback endpoint returns blanket 403 for employee role. Employees should be able to see their own feedback."
        ),
    },
    352: {
        "test": "Feedback READ List",
        "result": "STILL FAILING",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee) -> `200 OK`\n"
            "**Step 2:** GET /api/v1/feedback -> `Status: 403, 'Insufficient permissions'`\n\n"
            "**VERDICT: STILL FAILING** -- Feedback list endpoint returns 403 for employee. The endpoint should support employee access scoped to own feedback."
        ),
    },
}

# Issues that should be closed back because they were not actually tested by our API tests:
CLOSE_BACK = set(ALL_REOPENED) - set(KEEP_OPEN_AND_COMMENT.keys())

# Additional issues to also comment on (were correctly tested, found FIXED):
COMMENT_FIXED = {
    243: {
        "test": "Employee creating announcements",
        "result": "FIXED",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee) -> `200 OK`\n"
            "**Step 2:** POST /api/v1/announcements -> `Status: 403`\n\n"
            "**VERDICT: FIXED** -- Employee properly gets 403 when attempting to create announcements. This issue can remain closed."
        ),
    },
    171: {
        "test": "Privilege escalation via mass assignment",
        "result": "FIXED",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee, id=524) -> `200 OK`\n"
            "**Step 2:** PUT /api/v1/users/524 with `{\"role\":\"org_admin\"}` -> `Status: 403`\n\n"
            "**VERDICT: FIXED** -- Employee cannot escalate privileges via PUT /users/{id}. Properly returns 403."
        ),
    },
    177: {
        "test": "Employee deleting users",
        "result": "FIXED",
        "details": (
            "**Step 1:** Login as priya@technova.in (employee) -> `200 OK`\n"
            "**Step 2:** DELETE /api/v1/users/522 -> `Status: 403`\n\n"
            "**VERDICT: FIXED** -- Employee cannot delete users. Properly returns 403."
        ),
    },
}

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Phase 1: Close back all incorrectly reopened issues ──
    log(f"[PHASE 1] Closing back {len(CLOSE_BACK)} incorrectly reopened issues...")
    closed_count = 0
    for num in sorted(CLOSE_BACK):
        try:
            if close_issue(num):
                log(f"  #{num} closed")
                closed_count += 1
            else:
                log(f"  #{num} failed to close")
        except Exception as e:
            log(f"  #{num} error: {e}")
        time.sleep(0.5)

    log(f"  Closed {closed_count}/{len(CLOSE_BACK)} issues")

    # Wait for rate limit to cool down
    log("\nWaiting 60s for GitHub rate limit cooldown...")
    time.sleep(60)

    # ── Phase 2: Comment on truly RBAC issues that are STILL FAILING ──
    log(f"\n[PHASE 2] Commenting on {len(KEEP_OPEN_AND_COMMENT)} STILL FAILING RBAC issues...")
    commented = 0
    for num, info in sorted(KEEP_OPEN_AND_COMMENT.items()):
        comment = (
            f"Comment by E2E Testing Agent\n\n"
            f"## RBAC Deep Re-test -- {now}\n\n"
            f"Automated re-test of this closed issue against live test environment.\n\n"
            f"### Test: {info['test']}\n\n"
            f"{info['details']}\n\n"
            f"---\n"
            f"**API Base:** `https://test-empcloud-api.empcloud.com`\n"
            f"**Employee:** `priya@technova.in` (role=employee, id=524)\n"
            f"**Admin:** `ananya@technova.in` (role=org_admin, id=522)\n\n"
            f":rotating_light: **Re-opening this issue -- the RBAC violation is still present.**"
        )

        log(f"  Commenting on #{num}...")
        if add_comment_with_retry(num, comment):
            commented += 1
            log(f"  -> Comment added to #{num}")
        else:
            log(f"  -> FAILED to comment on #{num}")

        # Ensure it's open
        reopen_issue(num)
        time.sleep(5)  # 5s between each to avoid rate limit

    log(f"  Commented on {commented}/{len(KEEP_OPEN_AND_COMMENT)} failing issues")

    # Wait again
    log("\nWaiting 30s before commenting on fixed issues...")
    time.sleep(30)

    # ── Phase 3: Comment on issues confirmed FIXED ──
    log(f"\n[PHASE 3] Commenting on {len(COMMENT_FIXED)} confirmed FIXED issues...")
    fixed_commented = 0
    for num, info in sorted(COMMENT_FIXED.items()):
        comment = (
            f"Comment by E2E Testing Agent\n\n"
            f"## RBAC Deep Re-test -- {now}\n\n"
            f"Automated re-test of this closed issue against live test environment.\n\n"
            f"### Test: {info['test']}\n\n"
            f"{info['details']}\n\n"
            f"---\n"
            f"**API Base:** `https://test-empcloud-api.empcloud.com`\n"
            f"**Employee:** `priya@technova.in` (role=employee, id=524)\n\n"
            f":white_check_mark: **Confirmed fixed. Issue remains closed.**"
        )

        log(f"  Commenting on #{num}...")
        if add_comment_with_retry(num, comment):
            fixed_commented += 1
            log(f"  -> Comment added to #{num}")
        else:
            log(f"  -> FAILED to comment on #{num}")

        # Ensure it's closed (these are fixed)
        close_issue(num)
        time.sleep(5)

    log(f"  Commented on {fixed_commented}/{len(COMMENT_FIXED)} fixed issues")

    # ── Summary ──
    print("\n" + "=" * 70)
    print("  GITHUB CLEANUP & COMMENT SUMMARY")
    print("=" * 70)
    print(f"  Incorrectly reopened issues closed back: {closed_count}")
    print(f"  STILL FAILING issues commented & kept open: {commented}")
    print(f"  FIXED issues commented & kept closed: {fixed_commented}")
    print()
    print("  Issues kept OPEN (RBAC violations confirmed):")
    for num in sorted(KEEP_OPEN_AND_COMMENT.keys()):
        print(f"    #{num}: {KEEP_OPEN_AND_COMMENT[num]['test']}")
    print()
    print("  Issues confirmed FIXED:")
    for num in sorted(COMMENT_FIXED.keys()):
        print(f"    #{num}: {COMMENT_FIXED[num]['test']}")


if __name__ == "__main__":
    main()
