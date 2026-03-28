"""File additional issues discovered from screenshot review."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import requests
import base64
import os

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\hr_journey"
headers = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

def upload_screenshot(filepath):
    if not filepath or not os.path.exists(filepath):
        return None
    with open(filepath, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    fname = os.path.basename(filepath)
    path = f"test-screenshots/hr-journey/{fname}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    resp = requests.put(url, headers=headers, json={
        "message": f"Screenshot: {fname}",
        "content": content
    }, timeout=30)
    if resp.status_code in [200, 201]:
        return resp.json().get("content", {}).get("download_url", "")
    return None

def file_issue(title, body, labels):
    resp = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        headers=headers,
        json={"title": title, "body": body, "labels": labels},
        timeout=30
    )
    url = resp.json().get("html_url", "")
    print(f"  [{resp.status_code}] {title[:70]}")
    print(f"    {url}")
    return url

# Issue 1: Org chart page returns 500 Internal Server Error
ss_url = upload_screenshot(os.path.join(SCREENSHOT_DIR, "09_org_chart_070433.png"))
print(f"  Uploaded org chart screenshot: {ss_url}")

file_issue(
    "Org Chart page returns 500 Internal Server Error - nginx crashes when loading /org-chart",
    f"""## What I was trying to do
Viewing the organization chart to check company hierarchy and verify new employee Rahul Sharma is under his manager.

## What happened
Navigating to /org-chart shows a **500 Internal Server Error** from nginx/1.18.0 (Ubuntu).

The page completely fails to load - no org chart, no error message in the application, just a raw nginx 500 page.

## What I expected
An interactive org chart showing the company hierarchy with:
- All employees in a tree structure
- Reporting relationships
- Clickable names to view profiles
- Department groupings

## Screenshot
![500 error on org chart]({ss_url})

## Additional context
- The API endpoint GET /api/v1/users/org-chart does return data (2 entries), but the frontend page crashes
- Employee directory (GET /api/v1/employees/directory) works fine and shows 20 employees
- This is a critical page for HR managers to visualize team structure

## Environment
- URL: https://test-empcloud.empcloud.com/org-chart
- Error: 500 Internal Server Error (nginx/1.18.0)
- User: ananya@technova.in (HR Manager)
- Date: 2026-03-28
""",
    ["bug", "critical", "hr-journey-test"]
)

# Issue 2: Leave requests show "User #524" instead of employee names
ss_url2 = upload_screenshot(os.path.join(SCREENSHOT_DIR, "03_leave_page_070243.png"))
print(f"  Uploaded leave page screenshot: {ss_url2}")

file_issue(
    "Pending leave requests show 'User #524' instead of employee names - HR cannot identify who requested",
    f"""## What I was trying to do
Reviewing 17 pending leave requests as HR Manager to approve or reject them.

## What happened
The Leave Dashboard shows pending leave requests, but employee names display as "User #524", "User #522", etc. instead of actual names like "Priya Patel" or "Ananya Gupta".

This makes it impossible for HR to quickly identify who is requesting leave without cross-referencing user IDs manually.

## What I expected
Leave requests should show:
- **Employee full name** (e.g., "Priya Patel")
- Department
- Leave type
- Date range
- Number of days
- Reason
- Approve/Reject buttons

## Screenshot
![Leave requests showing user IDs]({ss_url2})

## Impact
With 17 pending requests, an HR manager cannot efficiently process approvals when they can't identify the employees. This is a daily workflow blocker.

## Environment
- URL: https://test-empcloud.empcloud.com/leave
- User: ananya@technova.in (HR Manager)
- Date: 2026-03-28
""",
    ["bug", "ux", "hr-journey-test"]
)

# Issue 3: Employee assets page (/my-assets or /assets for employee) not working
file_issue(
    "Employee cannot view their assigned assets - assets page not accessible for employee role",
    """## What I was trying to do
As employee Priya, checking what assets (laptop, monitor, etc.) are assigned to me.

## What happened
Navigating to /assets or /my-assets as an employee shows no asset information. The page either redirects or shows empty content.

## What I expected
Employees should be able to see:
- List of assets assigned to them (laptop serial number, monitor, phone, etc.)
- Asset condition/status
- Date of assignment
- Option to report issues with assigned assets

## Context
The HR manager view (/assets) does show an assets section, but there's no way for employees to see what's specifically assigned to them from their self-service portal.

## Environment
- URL: https://test-empcloud.empcloud.com/assets
- User: priya@technova.in (Employee)
- Date: 2026-03-28
""",
    ["bug", "hr-journey-test"]
)

# Issue 4: Audit log has no UI but API works
file_issue(
    "Audit log has no dedicated UI page - API returns data but no way to browse it visually",
    """## What I was trying to do
Checking recent audit log entries to see what actions have been performed (new employee added, leave approved, etc.).

## What happened
- Navigating to /audit-log or /audit shows no dedicated audit log page
- However, GET /api/v1/audit API works and returns 20 audit entries (mostly login actions)

## What I expected
A dedicated Audit Log page where HR/admins can:
- Browse all actions chronologically
- Filter by action type (login, create, update, delete)
- Filter by user
- Filter by date range
- See details of each action (what changed, old vs new values)
- Export audit data

## Context
The sidebar menu shows "Audit Log" link, but clicking it doesn't navigate to a working page. The API endpoint exists and returns data, so this appears to be a frontend routing/rendering issue.

## Environment
- URL: https://test-empcloud.empcloud.com/audit-log
- API: GET /api/v1/audit returns 200 with data
- Date: 2026-03-28
""",
    ["bug", "hr-journey-test"]
)

# Issue 5: Invite button not visible in UI
file_issue(
    "No 'Invite Employee' button visible in UI despite API working - HR must use API to invite",
    """## What I was trying to do
Inviting a new hire (newhire@technova.in) to join the organization.

## What happened
- The employee directory page has no visible "Invite" button
- The POST /api/v1/users/invite API works correctly and sends invitations
- Successfully invited via API (status: pending, expires in 7 days)

## What I expected
A visible "Invite" or "Add & Invite" button on the Employees page that:
- Opens a form to enter email, name, role
- Sends invitation email
- Shows pending invitations list

## Context
The API invitation worked perfectly - it generated a token, set status to "pending", and configured a 7-day expiry. But there's no UI to access this functionality without using the API directly.

## Environment
- URL: https://test-empcloud.empcloud.com/employees
- API: POST /api/v1/users/invite works (201)
- Date: 2026-03-28
""",
    ["bug", "ux", "hr-journey-test"]
)

print("\nDone filing additional issues!")
