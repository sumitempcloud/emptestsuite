"""
Ravi Kumar Manager Day — Final Bug Filing
File confirmed bugs from Pass 1-3 screenshot analysis.
Also close/comment on false positives.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import datetime
import json
import base64
from pathlib import Path

GITHUB_PAT  = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
HEADERS = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

issues_filed = []


def upload_screenshot(filepath, folder="manager_ravi_final"):
    if not filepath or not Path(filepath).exists():
        return None
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        fname = Path(filepath).name
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/{folder}/{fname}"
        resp = requests.put(url, headers=HEADERS, json={
            "message": f"Upload screenshot: {fname}", "content": content, "branch": "main"
        }, timeout=30)
        if resp.status_code in (200, 201):
            return resp.json().get("content", {}).get("download_url", "")
    except:
        pass
    return None


def check_duplicate(title_fragment):
    """Check if an issue with similar title already exists."""
    try:
        resp = requests.get("https://api.github.com/search/issues", headers=HEADERS,
            params={"q": f'repo:{GITHUB_REPO} is:issue state:open "{title_fragment}"'}, timeout=15)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            if items:
                return items[0]
    except:
        pass
    return None


def file_issue(title, body, labels=None):
    if labels is None:
        labels = ["bug", "manager-experience"]

    # Check duplicate
    existing = check_duplicate(title[:50])
    if existing:
        print(f"  [EXISTS] {title}")
        print(f"           {existing['html_url']}")
        issues_filed.append({"title": title, "url": existing["html_url"], "existing": True})
        return existing["html_url"]

    payload = {"title": title, "body": body, "labels": labels}
    try:
        resp = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                             headers=HEADERS, json=payload, timeout=30)
        if resp.status_code == 201:
            url = resp.json()["html_url"]
            print(f"  [FILED] {title}")
            print(f"          {url}")
            issues_filed.append({"title": title, "url": url})
            return url
        else:
            print(f"  [FAIL] {title}: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"  [ERROR] {title}: {e}")
    return None


def add_comment(issue_number, comment):
    """Add a comment to an existing issue."""
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/comments",
            headers=HEADERS, json={"body": comment}, timeout=15)
        if resp.status_code == 201:
            print(f"  [COMMENT] Added to #{issue_number}")
            return True
    except:
        pass
    return False


def main():
    print("=" * 70)
    print("  RAVI KUMAR — Filing Confirmed Manager Experience Bugs")
    print(f"  Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ── BUG 1: Leave Dashboard shows User IDs instead of names ─────────
    print("\n--- Bug 1: Leave Dashboard User IDs ---")
    img1 = upload_screenshot(r"C:\Users\Admin\screenshots\manager_ravi_p3\065629_01_leave_dashboard.png")
    file_issue(
        "Leave dashboard shows 'User #524' instead of employee names",
        f"""## Description
The Leave Dashboard (/leave) shows user IDs like "User #524" and "User #522" instead of actual employee names (e.g., "Priya Patel") in the Pending Leave Requests table.

Interestingly, the My Team page (/manager) correctly shows full employee names like "Priya Patel" for the same pending leave requests. This is inconsistent.

**User:** Ananya (ananya@technova.in) acting as Manager
**Persona:** Ravi Kumar -- Team Lead at TechNova Solutions
**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
**URL:** https://test-empcloud.empcloud.com/leave

## Screenshot
{f'![Leave Dashboard]({img1})' if img1 else 'See local screenshots'}

## Steps to Reproduce
1. Login as ananya@technova.in
2. Navigate to /leave (Leave Dashboard)
3. Look at the "Pending Leave Requests" table
4. Notice employee column shows "User #524" instead of real names

## Expected
Employee names should display as full names (e.g., "Priya Patel") matching how they appear on the /manager page.

## Actual
Employee names show as "User #524", "User #522" etc. — making it impossible for a manager to identify who is requesting leave without cross-referencing IDs.

## Impact
**Medium-High** — Managers cannot identify leave requestors at a glance, breaking the approval workflow.
""",
        ["bug", "manager-experience", "leave"]
    )

    # ── BUG 2: Raw ISO dates in leave requests ────────────────────────
    print("\n--- Bug 2: Raw ISO dates in leave requests ---")
    file_issue(
        "Leave requests show raw ISO timestamps instead of formatted dates",
        f"""## Description
Pending leave requests on both the /leave and /manager pages display dates in raw ISO 8601 format (e.g., "2026-06-26T00:00:00.000Z") instead of human-readable format (e.g., "Jun 26, 2026" or "26 Jun 2026").

**User:** Ananya (ananya@technova.in) acting as Manager
**Persona:** Ravi Kumar -- Team Lead at TechNova Solutions
**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
**URL:** https://test-empcloud.empcloud.com/leave, https://test-empcloud.empcloud.com/manager

## Screenshot
{f'![Leave Dashboard]({img1})' if img1 else 'See local screenshots'}

## Steps to Reproduce
1. Login as ananya@technova.in
2. Navigate to /leave or /manager
3. Look at the dates in "Pending Leave Requests"
4. Dates show as "2026-06-26T00:00:00.000Z — 2026-06-26T00:00:00.000Z"

## Expected
Dates should be formatted in a readable format like "Jun 26, 2026" or "26/06/2026".

## Actual
Raw ISO 8601 timestamps are displayed: "2026-06-26T00:00:00.000Z — 2026-06-26T00:00:00.000Z"

## Impact
**Medium** — Difficult for managers to quickly read and compare leave dates.
""",
        ["bug", "manager-experience", "leave", "ui"]
    )

    # ── BUG 3: Leave type shows trailing zero ─────────────────────────
    print("\n--- Bug 3: Leave type trailing zero ---")
    file_issue(
        "Leave type displays 'Earned Leave0' with trailing zero",
        f"""## Description
On both the /leave and /manager pages, leave types display with a trailing "0" appended — e.g., "Earned Leave0" instead of "Earned Leave".

**User:** Ananya (ananya@technova.in) acting as Manager
**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
**URL:** https://test-empcloud.empcloud.com/leave

## Screenshot
{f'![Leave Dashboard]({img1})' if img1 else 'See local screenshots'}

## Steps to Reproduce
1. Login as ananya@technova.in
2. Navigate to /leave
3. Look at the "TYPE" column in Pending Leave Requests
4. Every leave type shows "Earned Leave0" instead of "Earned Leave"

## Expected
Leave type should display as "Earned Leave" (without trailing zero).

## Actual
Shows "Earned Leave0" — likely a concatenation bug (leave type name + some numeric value).

## Impact
**Low** — Cosmetic issue but looks unprofessional and confusing.
""",
        ["bug", "manager-experience", "leave", "ui"]
    )

    # ── BUG 4: Performance SSO redirect fails ─────────────────────────
    print("\n--- Bug 4: Performance SSO redirect fails ---")
    img4 = upload_screenshot(r"C:\Users\Admin\screenshots\manager_ravi_p3\065741_04_performance_from_link.png")
    file_issue(
        "Performance module SSO redirect fails — returns to EmpCloud dashboard",
        f"""## Description
When clicking the "Performance Management & Career Development" link from the EmpCloud dashboard, the URL correctly includes an SSO token (`?sso_token=eyJ...`), but the user is redirected back to the EmpCloud main dashboard instead of landing on the Performance module.

The Performance module at test-performance.empcloud.com has its own separate login page and does not process the SSO token correctly.

**User:** Ananya (ananya@technova.in)
**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
**URL:** https://test-empcloud.empcloud.com/ -> https://test-performance.empcloud.com

## Screenshot
{f'![Dashboard showing module links]({img4})' if img4 else 'See local screenshots'}

## Steps to Reproduce
1. Login as ananya@technova.in on EmpCloud
2. Scroll to "Your Modules" section on dashboard
3. Click "Performance Management & Career Development" link
4. Observe: URL has SSO token but user lands back on EmpCloud dashboard
5. Going directly to test-performance.empcloud.com shows a separate login page

## Expected
Clicking the Performance link should SSO the user seamlessly into the Performance module.

## Actual
SSO token is generated but the redirect fails. The Performance module shows its own login page instead of honoring the SSO token.

## Impact
**High** — Managers cannot seamlessly review team performance without manually logging into a separate system.
""",
        ["bug", "manager-experience", "sso", "performance"]
    )

    # ── BUG 5: No date filter/picker on attendance page ────────────────
    print("\n--- Bug 5: Attendance page no date filter ---")
    img5 = upload_screenshot(r"C:\Users\Admin\screenshots\manager_ravi_p3\065653_03_attendance.png")
    file_issue(
        "Attendance dashboard lacks date picker or date range filter",
        f"""## Description
The Attendance Dashboard (/attendance) shows "Today's Attendance" but provides no date picker, date range filter, or calendar control to view attendance for other dates. Managers can only see today's data.

The page has calendar SVG icons (decorative) but no interactive date selection controls.

**User:** Ananya (ananya@technova.in) acting as Manager
**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
**URL:** https://test-empcloud.empcloud.com/attendance

## Screenshot
{f'![Attendance Dashboard]({img5})' if img5 else 'See local screenshots'}

## Steps to Reproduce
1. Login as ananya@technova.in
2. Navigate to /attendance
3. Try to filter or change the date to view past attendance
4. No date picker or filter control available

## Expected
A date picker or date range filter should allow managers to view attendance for any date or date range, not just today.

## Actual
Only "Today's Attendance" is shown with no way to view historical attendance data.

## Impact
**High** — Managers cannot review past attendance, spot patterns of lateness/absenteeism, or verify payroll data.
""",
        ["bug", "manager-experience", "attendance", "feature-gap"]
    )

    # ── Update Issue #558: Manager page DOES have "Review" buttons ─────
    print("\n--- Updating Issue #558 (approve/reject on manager page) ---")
    add_comment(558,
        """**Update from deeper investigation (Pass 3):**

After scrolling down and inspecting the Pending Leave Requests table on /manager, each leave request row actually has a **"Review"** button (not direct "Approve"/"Reject" buttons).

Clicking "Review" on /leave opens a detail view where approve/reject actions may be available.

However, the workflow could be improved:
- The /manager page should ideally have **one-click approve/reject** directly on each pending request row, rather than requiring a "Review" click first
- The current "Review" button is subtle and may be missed by managers scanning the dashboard quickly

Adjusting severity to **enhancement/usability** rather than a missing feature. The approval workflow exists but requires an extra click."""
    )

    # ── Summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  FINAL BUG FILING SUMMARY")
    print("=" * 70)
    print(f"\n  Bugs filed/found: {len(issues_filed)}")
    for issue in issues_filed:
        existing = " (existing)" if issue.get("existing") else " (NEW)"
        print(f"    {existing} {issue['title']}")
        print(f"            {issue.get('url', 'N/A')}")

    # Save consolidated results
    all_results_path = Path(r"C:\emptesting\manager_ravi_all_results.json")

    # Load results from all passes
    all_data = {"date": datetime.datetime.now().isoformat(), "persona": "Ravi Kumar -- Team Lead"}

    for pass_file in ["manager_ravi_results.json", "manager_ravi_pass2_results.json",
                       "manager_ravi_pass3_results.json"]:
        fpath = Path(f"C:/emptesting/{pass_file}")
        if fpath.exists():
            with open(fpath) as f:
                data = json.load(f)
                all_data[pass_file] = data

    all_data["final_issues"] = issues_filed

    # Consolidate all unique test results
    all_tests = []
    for key in ["manager_ravi_results.json", "manager_ravi_pass2_results.json",
                 "manager_ravi_pass3_results.json"]:
        if key in all_data and "results" in all_data[key]:
            all_tests.extend(all_data[key]["results"])

    total = len(all_tests)
    passed = sum(1 for t in all_tests if t["passed"])
    failed = total - passed

    all_data["consolidated"] = {
        "total_tests_across_passes": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "N/A"
    }

    with open(all_results_path, "w") as f:
        json.dump(all_data, f, indent=2)

    print(f"\n  Consolidated results: {all_results_path}")
    print(f"  Total tests across all passes: {total}")
    print(f"  Passed: {passed}  |  Failed: {failed}  |  Rate: {passed/total*100:.1f}%")

    # Final manager workflow assessment
    print("\n" + "=" * 70)
    print("  MANAGER EXPERIENCE ASSESSMENT")
    print("=" * 70)
    print("""
  WORKING WELL:
    [OK] /manager page (My Team) — Excellent dashboard with attendance stats,
         team member list, leave calendar, and pending leave requests
    [OK] Employee directory (/employees) — Can browse and click into profiles
    [OK] Leave dashboard (/leave) — Shows balances, pending requests with Review action
    [OK] Comp-Off (/leave/comp-off) — Request and approval tabs, working
    [OK] Events (/events) — List events, Manage Events button
    [OK] Helpdesk (/helpdesk) — Dashboard with SLA, tickets, categories
    [OK] Whistleblowing — Full dashboard, submit, track, and all reports
    [OK] Dashboard Module Insights — Shows Recruitment, Performance, Rewards stats
    [OK] Sidebar navigation — 11 manager-relevant links

  BUGS FOUND:
    [BUG] Leave dashboard shows "User #524" instead of employee names
    [BUG] Leave dates shown as raw ISO timestamps (2026-06-26T00:00:00.000Z)
    [BUG] Leave type shows "Earned Leave0" (trailing zero)
    [BUG] Performance module SSO redirect fails — returns to dashboard
    [BUG] Rewards module SSO requires separate login (no auto-SSO)
    [BUG] Attendance page has no date picker/filter for historical data
    [BUG] Attendance page has no export/download feature
    [BUG] Project module shows marketing landing page instead of tool

  ENHANCEMENT OPPORTUNITIES:
    [ENH] Manager page could have one-click approve/reject (currently "Review")
    [ENH] Main dashboard could show a "My Team" summary widget
    [ENH] Attendance page could show team vs self toggle tabs
""")
    print("=" * 70)


if __name__ == "__main__":
    main()
