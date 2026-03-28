"""
File verified bugs from Priya's employee journey testing.
Only files issues that were confirmed by screenshot review.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import base64
import time
from pathlib import Path

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
SCREENSHOT_DIR = Path(r"C:\Users\Admin\screenshots\employee_journey")

headers = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json"
}


def upload_screenshot(filepath):
    """Upload screenshot to GitHub and return markdown image link."""
    if not filepath or not Path(filepath).exists():
        return ""
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        fname = Path(filepath).name
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/employee_journey/{fname}"
        resp = requests.put(url, headers=headers, json={
            "message": f"Upload: {fname}", "content": content, "branch": "main"
        }, timeout=30)
        if resp.status_code in (200, 201):
            dl = resp.json().get("content", {}).get("download_url", "")
            if dl:
                return f"![screenshot]({dl})"
        # Maybe already exists
        elif resp.status_code == 422:
            # Get the existing file URL
            get_resp = requests.get(url, headers=headers, timeout=15)
            if get_resp.status_code == 200:
                dl = get_resp.json().get("download_url", "")
                if dl:
                    return f"![screenshot]({dl})"
    except Exception as e:
        print(f"  Upload error for {filepath}: {e}")
    return f"Local: `{filepath}`"


def file_issue(title, body, labels):
    """File a GitHub issue."""
    resp = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        headers=headers,
        json={"title": title, "body": body, "labels": labels},
        timeout=30
    )
    if resp.status_code == 201:
        url = resp.json()["html_url"]
        print(f"  FILED: {title}")
        print(f"    {url}")
        return url
    else:
        print(f"  FAILED ({resp.status_code}): {title}")
        print(f"    {resp.text[:200]}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# VERIFIED BUGS TO FILE
# ═══════════════════════════════════════════════════════════════════════════

bugs = []

# Bug 1: Feedback page shows "Insufficient permissions" for employee
bugs.append({
    "title": "Feedback page shows 'Insufficient permissions' error for employees",
    "screenshots": [SCREENSHOT_DIR / "070056_p2_feedback_page_deep.png"],
    "body": """## Description
When I navigate to the Feedback page (All Feedback) as an employee, two red "Insufficient permissions" error toasts appear at the bottom of the page. The feedback list shows "No feedback matches the current filters" — I can't see any feedback, not even my own previously submitted ones.

**User:** Priya Patel (priya@technova.in) — Employee role
**URL:** https://test-empcloud.empcloud.com/feedback

## Steps to Reproduce
1. Login as priya@technova.in (Employee)
2. Click "Submit Feedback" or navigate to /feedback
3. Observe the "Insufficient permissions" error toasts

## Expected
Employees should be able to view their own submitted feedback and submit new anonymous feedback without permission errors.

## Actual
Two "Insufficient permissions" error toasts appear. The feedback list is empty.
""",
    "labels": ["bug", "employee-journey", "feedback", "permissions"]
})

# Bug 2: Profile Edit shows no editable fields
bugs.append({
    "title": "Edit Profile button doesn't make any fields editable",
    "screenshots": [
        SCREENSHOT_DIR / "065817_p2_profile_view.png",
        SCREENSHOT_DIR / "065821_p2_profile_edit_mode.png"
    ],
    "body": """## Description
On the My Profile page, clicking "Edit Profile" doesn't change anything visible. All personal information fields (Personal Email, Contact Number, Gender, Date of Birth, Blood Group, Marital Status, Nationality, etc.) remain as read-only text with dashes for empty values. There are no editable input fields, no save button appears.

I need to update my phone number and emergency contact but there's no way to do it.

**User:** Priya Patel (priya@technova.in) — Employee role
**URL:** https://test-empcloud.empcloud.com/employees/524

## Steps to Reproduce
1. Login as priya@technova.in
2. Go to My Profile (sidebar or dashboard quick action)
3. Click "Edit Profile" button (top right)
4. Observe — no fields become editable

## Expected
Clicking "Edit Profile" should make at least basic fields (phone number, emergency contact, address) editable, with a Save button.

## Actual
The page looks identical before and after clicking Edit Profile. No input fields appear, no way to modify any information. Employees have no self-service way to update their profile.
""",
    "labels": ["bug", "employee-journey", "profile"]
})

# Bug 3: Helpdesk ticket creation form not filling — need to check this more
bugs.append({
    "title": "Helpdesk My Tickets page navigates to dashboard instead of tickets",
    "screenshots": [
        SCREENSHOT_DIR / "065933_p2_helpdesk_deep.png",
        SCREENSHOT_DIR / "065936_p2_helpdesk_create_deep.png"
    ],
    "body": """## Description
When navigating to the Helpdesk section, the page redirects to the main dashboard instead of showing the ticket list. Both direct URL navigation (/helpdesk) and sidebar link clicks land on the dashboard. The sidebar shows "My Tickets" and "Knowledge Base" links, but clicking "My Tickets" still shows the dashboard.

My laptop keyboard is broken and I can't raise an IT support ticket.

**User:** Priya Patel (priya@technova.in) — Employee role
**URL:** https://test-empcloud.empcloud.com/helpdesk/my-tickets

## Steps to Reproduce
1. Login as priya@technova.in
2. Click "My Tickets" in the sidebar under Helpdesk
3. Observe — lands on dashboard, not the ticket list

Note: The sidebar navigation audit showed the link goes to /helpdesk/my-tickets but the page content shown is the dashboard (Welcome back, Priya! with quick actions).

## Expected
Should show a list of my helpdesk tickets with the ability to create a new ticket.

## Actual
Redirects to or shows the main dashboard. No ticket list or ticket creation form accessible.
""",
    "labels": ["bug", "employee-journey", "helpdesk"]
})

# Bug 4: Payroll SSO doesn't work for employees
bugs.append({
    "title": "Payroll module doesn't open from Module Marketplace — SSO not working",
    "screenshots": [
        SCREENSHOT_DIR / "070047_p2_modules_payroll.png",
        SCREENSHOT_DIR / "064125_payroll_direct.png"
    ],
    "body": """## Description
From the Module Marketplace page, clicking on Payroll Management (which shows as "Subscribed") does not navigate to the payroll system. The page stays on the modules page.

When directly visiting the payroll URL (testpayroll.empcloud.com), it shows a login page pre-filled with ananya@technova.in (the admin) instead of automatically logging in Priya via SSO. Employees shouldn't need to know separate login credentials for payroll.

I need to check my payslip and tax deductions but can't access the payroll system.

**User:** Priya Patel (priya@technova.in) — Employee role
**URL:** https://test-empcloud.empcloud.com/modules

## Steps to Reproduce
1. Login as priya@technova.in on EMP Cloud
2. Navigate to Module Marketplace (/modules)
3. Click on "Payroll Management" (shows "Subscribed" status)
4. Nothing happens — stays on modules page
5. Direct visit to testpayroll.empcloud.com shows login with wrong email

## Expected
Clicking Payroll should SSO into the payroll system as Priya, showing her salary and payslip.

## Actual
- Clicking Payroll from modules page: nothing happens
- Direct URL: shows login page with admin email pre-filled instead of SSO
""",
    "labels": ["bug", "employee-journey", "payroll", "sso"]
})

# Bug 5: Notification bell doesn't open panel
bugs.append({
    "title": "Notification bell click doesn't open notification panel",
    "screenshots": [SCREENSHOT_DIR / "070139_p2_notif_after_click.png"],
    "body": """## Description
Clicking the notification bell icon in the header does not open a notification dropdown or panel. The page just stays on the dashboard with no visible change. There's no way for me to see my notifications.

**User:** Priya Patel (priya@technova.in) — Employee role
**URL:** https://test-empcloud.empcloud.com/dashboard

## Steps to Reproduce
1. Login as priya@technova.in
2. Click the bell icon in the top header bar
3. Observe — no notification panel or dropdown appears

## Expected
A dropdown or panel should appear showing recent notifications (leave approvals, announcements, etc.) with the ability to mark them as read.

## Actual
Nothing visibly happens when clicking the bell icon. No notification list appears.
""",
    "labels": ["bug", "employee-journey", "notifications"]
})

# Bug 6: Profile missing photo upload area
bugs.append({
    "title": "No way to upload or change profile photo",
    "screenshots": [SCREENSHOT_DIR / "065817_p2_profile_view.png"],
    "body": """## Description
The employee profile page shows a circular avatar placeholder with initials "PP" (Priya Patel), but there's no option to upload or change a profile photo. No camera icon overlay, no upload button, nothing clickable on the avatar area.

**User:** Priya Patel (priya@technova.in) — Employee role
**URL:** https://test-empcloud.empcloud.com/employees/524

## Steps to Reproduce
1. Login as priya@technova.in
2. Go to My Profile
3. Look for any way to upload or change profile photo
4. Also try clicking "Edit Profile" — still no photo upload option

## Expected
Should be able to click on the avatar/photo area to upload a profile picture, or have an "Upload Photo" button.

## Actual
Only shows initials "PP" in a circle. No upload functionality available, even in edit mode.
""",
    "labels": ["enhancement", "employee-journey", "profile"]
})

# Bug 7: Leave balance cards on dashboard don't show leave type names
bugs.append({
    "title": "Dashboard leave balance section doesn't label leave types clearly",
    "screenshots": [SCREENSHOT_DIR / "065507_p2_dashboard_deep.png"],
    "body": """## Description
The Leave Balance section on the employee dashboard shows numbers (17.0, 11.0, 8.0) but the leave type labels are not clearly visible or are cut off. While the dedicated Leave Dashboard page shows them properly (Earned Leave, Sick Leave, Privilege Leave), the dashboard widget could be more informative at a glance.

**User:** Priya Patel (priya@technova.in) — Employee role
**URL:** https://test-empcloud.empcloud.com/dashboard

## Steps to Reproduce
1. Login as priya@technova.in
2. Look at the "Leave Balance" section on the dashboard
3. The leave type names are not fully visible

## Expected
Leave balance cards should clearly show "Earned Leave: 17", "Sick Leave: 11", "Privilege Leave: 8" with readable labels.

## Actual
Numbers are shown but leave type labels may be truncated or unclear in the dashboard widget.
""",
    "labels": ["enhancement", "employee-journey", "dashboard"]
})

# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("Filing verified employee journey bugs...")
    print("=" * 60)

    filed = []
    for i, bug in enumerate(bugs, 1):
        print(f"\n[{i}/{len(bugs)}] {bug['title']}")

        # Upload screenshots
        ss_links = []
        for sp in bug.get("screenshots", []):
            link = upload_screenshot(sp)
            if link:
                ss_links.append(link)

        body = bug["body"]
        if ss_links:
            body += "\n## Screenshots\n" + "\n\n".join(ss_links) + "\n"

        url = file_issue(bug["title"], body, bug["labels"])
        if url:
            filed.append({"title": bug["title"], "url": url})

        time.sleep(1)  # Rate limit courtesy

    print(f"\n{'=' * 60}")
    print(f"Filed {len(filed)}/{len(bugs)} issues")
    for f in filed:
        print(f"  - {f['title']}")
        print(f"    {f['url']}")


if __name__ == "__main__":
    main()
