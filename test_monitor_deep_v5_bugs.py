"""
EMP Monitor - v5: File remaining bugs found through visual inspection
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
from datetime import datetime

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

bugs_filed = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def file_bug(title, body):
    bugs_filed.append(title)
    log(f"  Filing: {title}")
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github+json"
            },
            json={
                "title": title,
                "body": body,
                "labels": ["bug", "verified-bug", "monitor"]
            }
        )
        if resp.status_code == 201:
            log(f"  Filed issue #{resp.json()['number']}")
        else:
            log(f"  Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log(f"  Error: {e}")

def main():
    log("="*70)
    log("EMP MONITOR - Filing remaining bugs from visual inspection")
    log("="*70)

    # Bug 1: "Failed to fetch" errors on multiple Settings pages (caused by dev API)
    file_bug(
        "[Monitor] Settings pages show 'Failed to fetch' errors due to wrong API endpoint",
        "**Affected Pages:**\n"
        "- `/admin/settings/location` - Shows 'Failed to fetch locations' red error banner\n"
        "- `/admin/settings/roles` - Shows 'Failed to fetch roles' red error banner\n"
        "- `/admin/settings/localization` - Shows 'Failed to fetch localization settings' red error banner\n\n"
        "**Steps to Reproduce:**\n"
        "1. Login as admin (ananya@technova.in)\n"
        "2. Navigate to any of the Settings sub-pages above\n\n"
        "**Expected:** Settings data loads correctly from test environment API\n\n"
        "**Actual:** Red error banner shows 'Failed to fetch [X]' at top of page. "
        "No data is loaded in the tables (locations, roles, etc. all show empty).\n\n"
        "**Root Cause:** Related to issue where frontend makes API calls to `service.dev.empmonitor.com` "
        "(dev environment) instead of the test environment API. These dev API calls fail, resulting in "
        "the fetch errors.\n\n"
        "**Console errors confirm:** `Department API Error: AxiosError`, "
        "`Failed to load resource: service.dev.empmonitor.com/api/v3/location/get-locations`\n\n"
        "**Impact:** HIGH - Admin cannot manage locations, departments, roles, permissions, or localization settings. "
        "All Settings configuration is effectively broken."
    )
    time.sleep(1)

    # Bug 2: DLP Screenshot Logs and Email Activity Logs redirect to login
    file_bug(
        "[Monitor] DLP Screenshot Logs and Email Activity Logs pages redirect to login when authenticated",
        "**Affected Pages:**\n"
        "- `/admin/dlp/screenshotlog` - DLP > Screenshot Logs\n"
        "- `/admin/dlp/emailactivity` - DLP > Email Activity Logs\n\n"
        "**Steps to Reproduce:**\n"
        "1. Login as admin via SSO (ananya@technova.in)\n"
        "2. Navigate to `/admin/dlp/screenshotlog` or `/admin/dlp/emailactivity`\n\n"
        "**Expected:** DLP log pages load with content\n\n"
        "**Actual:** Both pages redirect to the login page even though the user is authenticated. "
        "Other DLP sub-pages (USB Detection, System Logs) work correctly.\n\n"
        "**Working DLP pages for comparison:**\n"
        "- `/admin/dlp/usb` - Works correctly\n"
        "- `/admin/dlp/systemlogs` - Works correctly\n\n"
        "**Impact:** MEDIUM - Admin cannot view screenshot audit logs or email activity logs, "
        "reducing DLP monitoring capability."
    )
    time.sleep(1)

    # Bug 3: Dashboard shows invalid time value 259:56:78
    # Already filed but as duplicates. This is a data validation bug.
    file_bug(
        "[Monitor] Dashboard displays impossible time value '259:56:78 hr' (78 seconds exceeds 59)",
        "**Page:** Admin Dashboard > Today Activity Snapshot\n\n"
        "**Steps to Reproduce:**\n"
        "1. Login as admin (ananya@technova.in)\n"
        "2. View the 'Today Activity Snapshot' section on the dashboard\n\n"
        "**Expected:** Time values should be in valid HH:MM:SS format where:\n"
        "- Seconds (SS) <= 59\n"
        "- Minutes (MM) <= 59\n\n"
        "**Actual:** The dashboard shows `259:56:78 hr` where 78 seconds exceeds "
        "the maximum valid value of 59. This value appears to be the sum of other time values "
        "but is not properly normalized.\n\n"
        "**All time values observed:**\n"
        "- Idle Time: 45:37:40 hr (valid)\n"
        "- Active Time: 71:59:57 hr (valid)\n"
        "- Total: 259:56:78 hr (INVALID - 78 seconds)\n\n"
        "**Impact:** LOW-MEDIUM - Displays incorrect/impossible time calculations. "
        "Suggests the time aggregation logic adds raw seconds without normalizing to MM:SS format."
    )
    time.sleep(1)

    # Bug 4: Employee Comparison shows no functionality besides date pickers
    file_bug(
        "[Monitor] Employee Comparison page shows 'No Activity Data' with no way to select employees",
        "**Page:** Employees > Employee Comparison (`/admin/comparison`)\n\n"
        "**Steps to Reproduce:**\n"
        "1. Login as admin\n"
        "2. Navigate to Employees > Employee Comparison\n\n"
        "**Expected:** Ability to select two employees and compare their productivity metrics side-by-side\n\n"
        "**Actual:** Page shows two side-by-side panels both displaying 'No Activity Data' with "
        "employee dropdowns (both showing 'See All Employees') and date pickers, but no comparison data loads. "
        "Selecting employees from dropdown does not populate comparison data due to API failures "
        "(calls to dev.empmonitor.com instead of test environment).\n\n"
        "**Impact:** MEDIUM - Employee comparison feature is non-functional. "
        "Admins cannot compare employee productivity metrics."
    )
    time.sleep(1)

    # Bug 5: Real Time Track has broken layout / limited content
    file_bug(
        "[Monitor] Real Time Track page shows 'no employees found' with broken productivity meter UI",
        "**Page:** Employees > Real Time Track (`/admin/realtime`)\n\n"
        "**Steps to Reproduce:**\n"
        "1. Login as admin\n"
        "2. Navigate to Employees > Real Time Track\n\n"
        "**Expected:** Real-time view of employee activity with productivity indicators\n\n"
        "**Actual:** Page shows:\n"
        "- 'Employee's Real Time Insights' heading\n"
        "- Search bar\n"
        "- A 'Productivity meter' gauge that appears as just a horizontal line (broken rendering)\n"
        "- 'No employees found' message\n"
        "- Copyright footer overlaps with content area\n\n"
        "**Impact:** MEDIUM - Real-time employee tracking feature is non-functional. "
        "The productivity meter gauge has rendering issues."
    )
    time.sleep(1)

    # Bug 6: Live Monitoring shows no search input
    file_bug(
        "[Monitor] Live Monitoring page lacks search/filter functionality for employees",
        "**Page:** Live Monitoring (`/admin/livemonitoring`)\n\n"
        "**Steps to Reproduce:**\n"
        "1. Login as admin\n"
        "2. Navigate to Live Monitoring\n\n"
        "**Expected:** Search bar and filters to find specific employees for live monitoring. "
        "README describes 'Filtering and Searching Capabilities' with 'Advanced Filtering' "
        "and 'Quick Search' as key features.\n\n"
        "**Actual:** The page title says 'Live Recording' (not 'Live Monitoring' matching the sidebar), "
        "shows a search field and department/employee dropdowns but 'No Agents Found' message. "
        "The search field exists but does not function without connected agents.\n\n"
        "**Note:** Page title inconsistency: sidebar says 'Live Monitoring' but page heading says 'Live Recording'\n\n"
        "**Impact:** LOW - Title inconsistency between sidebar and page heading."
    )
    time.sleep(1)

    # Bug 7: License shows "0 out of 0 Licenses"
    file_bug(
        "[Monitor] License information shows 'Used 0 out of 0 Licenses' - no license allocated",
        "**Page:** Admin sidebar (visible on all pages)\n\n"
        "**Steps to Reproduce:**\n"
        "1. Login as admin\n"
        "2. Observe the license information panel at the bottom of the sidebar\n\n"
        "**Expected:** License count should reflect the organization's subscription "
        "(e.g., 'Used 5 out of 50 Licenses')\n\n"
        "**Actual:** Shows 'Used 0 out of 0 Licenses, 0 - Licenses left & Expired on ...'\n\n"
        "**Impact:** MEDIUM - No licenses are allocated to the test organization, "
        "which may explain why features like Live Monitoring show no agents and why "
        "monitoring data is limited. The test environment may need license provisioning."
    )
    time.sleep(1)

    # Summary
    log("\n" + "="*70)
    log("BUGS FILED SUMMARY")
    log("="*70)
    log(f"Total bugs filed: {len(bugs_filed)}")
    for b in bugs_filed:
        log(f"  - {b}")

if __name__ == "__main__":
    main()
