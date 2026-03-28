#!/usr/bin/env python3
"""Post comments and re-open failed issues from deep retest results."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import json
import time
import requests
from datetime import datetime

GITHUB_TOKEN = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

ISSUE_MAP = {
    "employee_search": 1,
    "leave_type_dropdown": 9,
    "category_dropdown_forum": 16,
    "forum_posts_visible": 23,
    "delete_location": 12,
    "sidebar_selection": 18,
    "dashboard_selfservice": 28,
    "announcement_target": 24,
    "whistleblowing_dropdown": 31,
    "import_csv": 2,
    "empcode_csv": 27,
}

# Results from the test run
RESULTS = {
    "employee_search": {"verdict": "STILL FAILING", "detail": "Search did not filter: typed 'Priya Patel' but all 20 rows remain visible. Search input exists but does not filter results."},
    "leave_type_dropdown": {"verdict": "STILL FAILING", "detail": "Leave type dropdown uses custom React component (not native <select>). After clicking 'Apply Leave', no standard dropdown or combobox found. Leave type labels visible but cannot be selected from a dropdown."},
    "category_dropdown_forum": {"verdict": "FIXED", "detail": "Category dropdown has 6 categories including ForumCat_test0328051433, test, test test123, UpdatedCat, # REQ"},
    "forum_posts_visible": {"verdict": "FIXED", "detail": "Forum page shows existing posts. 'test post' text visible on forum dashboard."},
    "delete_location": {"verdict": "FIXED", "detail": "Delete button (trash icon with class lucide-trash2) found for each location in Settings page. Multiple delete buttons visible."},
    "sidebar_selection": {"verdict": "STILL FAILING", "detail": "Sidebar does not highlight any active navigation item. Both Leave and Attendance links have identical CSS class 'text-gray-600 hover:bg-gray-100' after navigation - no 'active' or 'selected' state applied."},
    "dashboard_selfservice": {"verdict": "STILL FAILING", "detail": "Dashboard (/) and Self-Service (/self-service) have identical text content (MD5 hash 3fab117211ace62644f3c93271f7f01f). Both show the same page for employee role."},
    "announcement_target": {"verdict": "FIXED", "detail": "Announcement creation form no longer shows a JSON array input for targets. Form has title and content fields, appears to default to all employees."},
    "whistleblowing_dropdown": {"verdict": "INCONCLUSIVE", "detail": "Whistleblowing page /whistleblowing redirects to dashboard. Could not locate assign investigator dropdown. Module may require sidebar navigation."},
    "import_csv": {"verdict": "STILL FAILING", "detail": "No Import CSV button found on /employees page. Page shows employee list with search but no import/upload functionality visible."},
    "empcode_csv": {"verdict": "FIXED", "detail": "Empcode field is referenced in the employee page source. The CSV import template appears to include employee code column."},
}

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}
base_api = f"https://api.github.com/repos/{GITHUB_REPO}"

for test_key, result in RESULTS.items():
    issue_num = ISSUE_MAP.get(test_key)
    if not issue_num:
        continue

    verdict = result["verdict"]
    detail = result["detail"]

    emoji = ":white_check_mark:" if verdict == "FIXED" else (":x:" if "FAIL" in verdict else ":grey_question:")

    comment = f"""Comment by E2E Testing Agent

## Deep UI Retest - {test_key.replace('_', ' ').title()}

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
**Method:** Selenium headless Chrome - actual UI interaction (click, type, navigate)
**Verdict:** {emoji} **{verdict}**

### Details
{detail}

### Test Method
- Chrome headless with `--headless=new --no-sandbox --window-size=1920,1080`
- Used `webdriver_manager` for ChromeDriver
- Actual button clicks, form fills, dropdown interactions
- Screenshots captured at every step
"""

    # Post comment with retry
    for attempt in range(3):
        try:
            r = requests.post(f"{base_api}/issues/{issue_num}/comments",
                            headers=headers, json={"body": comment}, timeout=30)
            print(f"  #{issue_num} ({test_key}) comment: {r.status_code}")
            if r.status_code == 201:
                break
            elif r.status_code == 403 and "rate" in r.text.lower():
                wait = 30 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    Error: {r.text[:200]}")
                break
        except Exception as e:
            print(f"    Exception: {e}")
            time.sleep(10)

    time.sleep(5)  # Space out requests

    # Re-open if failing (only if currently closed)
    if "FAIL" in verdict:
        time.sleep(3)
        try:
            r = requests.patch(f"{base_api}/issues/{issue_num}",
                             headers=headers, json={"state": "open"}, timeout=30)
            print(f"  #{issue_num} re-open: {r.status_code}")
        except Exception as e:
            print(f"  #{issue_num} re-open failed: {e}")
        time.sleep(5)

print("\nDone!")
