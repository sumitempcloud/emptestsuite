import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

headers = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json",
}

# Update issue #135 with corrected details
update_body = (
    "## Bug Report -- UPDATED\n\n"
    "**Module:** Field Force Management (https://test-field.empcloud.com)\n\n"
    "**Issue:** The entire Field Force module is DOWN. The server at test-field.empcloud.com "
    "returns ERR_INVALID_RESPONSE on every request -- root URL and all sub-paths "
    "(/tracking, /gps, /check-in, /routes, /dashboard, etc.).\n\n"
    "**Evidence from screenshots:**\n"
    "- Root URL: \"This site can't be reached -- ERR_INVALID_RESPONSE\"\n"
    "- /tracking: \"This site can't be reached -- ERR_INVALID_RESPONSE\"\n"
    "- /check-in: \"This site can't be reached -- ERR_INVALID_RESPONSE\"\n"
    "- All 16 tested sub-paths return the same error\n\n"
    "**Note:** The automated test initially reported several sub-pages and features "
    "(GPS tracking, route optimization, check-in/check-out) as PASS. This was a "
    "**false positive** -- the Chrome error page HTML was long enough (>500 chars) "
    "and contained URL text matching keywords like \"tracking\", \"check-in\", \"routes\". "
    "Manual screenshot review confirmed ALL pages are unreachable.\n\n"
    "**Corrected Results:**\n"
    "- Field Force Site Load: FAIL (ERR_INVALID_RESPONSE)\n"
    "- GPS Tracking: FAIL (site down)\n"
    "- Route Optimization: FAIL (site down)\n"
    "- Check-in/Check-out: FAIL (site down)\n"
    "- Field Dashboard: FAIL (site down)\n"
    "- All 16 sub-pages: FAIL (site down)\n\n"
    "**Impact:** The entire Field Force Management module is non-functional. "
    "No testing of GPS tracking, route optimization, or check-in/check-out is possible.\n\n"
    "**Severity:** critical\n"
    "**Date:** 2026-03-27\n"
    "**Screenshots:** Multiple screenshots confirming \"This site can't be reached\" on all paths"
)

resp = requests.patch(
    f"https://api.github.com/repos/{GITHUB_REPO}/issues/135",
    headers=headers,
    json={"body": update_body},
    timeout=15
)
print(f"Updated #135: {resp.status_code}")

# File correction issue
test_bug = {
    "title": "[Field Force] All features reported as PASS are false positives - entire site is DOWN",
    "body": (
        "## Correction Report\n\n"
        "**Module:** Field Force Management (https://test-field.empcloud.com)\n\n"
        "**Summary:** The automated E2E test initially reported 16 accessible pages and PASS results "
        "for GPS tracking, route optimization, and check-in/check-out on the Field Force module. "
        "**All of these are false positives.**\n\n"
        "**Root Cause of False Positives:** The test checked whether the page HTML was longer than "
        "500 characters and contained keywords. The Chrome \"This site can't be reached\" error page "
        "met both criteria:\n"
        "- The error page HTML is well over 500 characters\n"
        "- The error page displays the URL being visited (e.g., "
        "\"https://test-field.empcloud.com/tracking\"), which contains the keywords being searched for\n\n"
        "**Actual State:** Every URL on test-field.empcloud.com returns ERR_INVALID_RESPONSE. "
        "The server is completely unreachable. Confirmed via manual screenshot review.\n\n"
        "**Corrected Results (all FAIL):**\n\n"
        "| Test | Automated Result | Actual Result |\n"
        "|------|-----------------|---------------|\n"
        "| Site Load | FAIL | FAIL |\n"
        "| GPS Tracking | ~~PASS~~ | FAIL |\n"
        "| Route Optimization | ~~PASS~~ | FAIL |\n"
        "| Check-in/Check-out | ~~PASS~~ | FAIL |\n"
        "| Dashboard Sections | ~~PASS~~ | FAIL |\n"
        "| 16 Sub-pages | ~~16 accessible~~ | 0 accessible |\n\n"
        "**Severity:** critical\n"
        "**Date:** 2026-03-27"
    ),
    "labels": ["bug", "severity:critical", "module:field-force"]
}

resp2 = requests.post(
    f"https://api.github.com/repos/{GITHUB_REPO}/issues",
    headers=headers, json=test_bug, timeout=15
)
if resp2.status_code == 201:
    print(f"Created correction issue: {resp2.json()['html_url']}")
else:
    print(f"Failed: {resp2.status_code} {resp2.text[:200]}")

# Also file issue about monitor login "User does not exist" being distinct from the generic login issue
monitor_login_bug = {
    "title": "[Monitor] Employee login also fails with 'User does not exist'",
    "body": (
        "## Bug Report\n\n"
        "**Module:** Employee Monitoring (https://test-empmonitor.empcloud.com)\n\n"
        "**Steps to Reproduce:**\n"
        "1. Navigate to https://test-empmonitor.empcloud.com/login\n"
        "2. Enter Employee credentials (priya@technova.in / Welcome@123)\n"
        "3. Click Login\n\n"
        "**Expected:** Employee should be able to log in and see their own monitoring data\n"
        "**Actual:** Error message \"User does not exist\" displayed, same as Org Admin.\n\n"
        "**Screenshot confirms:** The login page at test-empmonitor.empcloud.com shows a red error "
        "banner with \"User does not exist\" after entering valid employee credentials.\n\n"
        "**Analysis:** The monitoring module (empmonitor-4.0-front-end) has its own user database "
        "that is completely independent of the main EMP Cloud HRMS. No users from the main system "
        "are provisioned in the monitoring module. This blocks ALL monitoring functionality for "
        "ALL user roles.\n\n"
        "**Related:** GitHub issue #144 (same issue for Org Admin)\n\n"
        "**Severity:** critical\n"
        "**Date:** 2026-03-27"
    ),
    "labels": ["bug", "severity:critical", "module:monitoring"]
}

resp3 = requests.post(
    f"https://api.github.com/repos/{GITHUB_REPO}/issues",
    headers=headers, json=monitor_login_bug, timeout=15
)
if resp3.status_code == 201:
    print(f"Created monitor employee issue: {resp3.json()['html_url']}")
else:
    print(f"Failed: {resp3.status_code} {resp3.text[:200]}")
