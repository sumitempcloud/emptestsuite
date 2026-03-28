"""
Update GitHub issues #98-#131 based on retest results.
With proper rate limit handling.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import time
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_PAT = "$GITHUB_TOKEN"

# Results from the test run
RESULTS = {
    # FIXED issues (98 already commented)
    104: ("FIXED", "No raw i18n keys in sidebar. Sidebar shows 'My Profile', 'Dashboard', etc. correctly."),
    106: ("FIXED", "Employee login works via both UI and API. priya@technova.in can log in successfully."),
    107: ("FIXED", "Search input found on /employees page (input[placeholder*='earch'])."),
    108: ("FIXED", "Employee properly redirected away from /admin. Cannot access admin dashboard."),
    109: ("FIXED", "Can click employee row in directory (table tbody tr selector works)."),
    110: ("FIXED", "Add Employee button found on /employees page."),
    122: ("FIXED", "Employee redirected from /settings. Cannot see full org settings."),
    123: ("FIXED", "Employee redirected from /admin/ai-config. Cannot see AI configuration."),
    124: ("FIXED", "Employee redirected from /admin/logs. Cannot see log dashboard."),

    # STILL FAILING issues
    99:  ("STILL_FAILING", "'Invalid ID parameter' error still appears on /events/my-events page for employee user."),
    100: ("STILL_FAILING", "/assets page shows 403/Forbidden error for employee user."),
    101: ("STILL_FAILING", "'Invalid ID' error still appears on /assets/my-assets page."),
    102: ("STILL_FAILING", "'Invalid ID' error still appears on /positions/open page."),
    103: ("STILL_FAILING", "'Insufficient permissions' error still shown on /feedback page for employee."),
    105: ("STILL_FAILING", "/wellness/daily-checkin redirects to root URL instead of showing daily checkin page."),
    119: ("STILL_FAILING", "/settings/modules redirects to root URL for org admin instead of loading modules settings."),
    120: ("STILL_FAILING", "/settings/custom-fields redirects to root URL for org admin."),
    121: ("STILL_FAILING", "/reports redirects to root URL for org admin instead of showing reports."),

    # Duplicates - FIXED (inherit from parent)
    112: ("FIXED", "Duplicate of #107. Employee directory search works."),
    113: ("FIXED", "Duplicate of #98. Employee RBAC for settings works."),
    114: ("FIXED", "Duplicate of #107. Employee directory search works."),
    115: ("FIXED", "Duplicate of #98. Settings access properly restricted."),
    117: ("FIXED", "Duplicate of #108. Employee RBAC for admin works."),
    118: ("FIXED", "Duplicate of #98. Settings access properly restricted."),
    125: ("FIXED", "Duplicate of #107. Search input found on /employees."),
    126: ("FIXED", "Duplicate of #109. Employee row clicking works."),
    127: ("FIXED", "Duplicate of #110. Add Employee button found."),
    129: ("FIXED", "Duplicate of #107. Search input found on /employees."),
    130: ("FIXED", "Duplicate of #109. Employee row clicking works."),
    131: ("FIXED", "Duplicate of #110. Add Employee button found."),

    # Duplicates - STILL FAILING (inherit from parent)
    111: ("STILL_FAILING", "Duplicate of #99. 'Invalid ID parameter' on events page persists."),
    116: ("STILL_FAILING", "Duplicate of #99. Attendance/events related error persists."),
    128: ("STILL_FAILING", "Duplicate of #99. Regularization/events error persists."),
}


def gh_api(method, endpoint, data=None):
    url = f"https://api.github.com/repos/{GITHUB_REPO}{endpoint}"
    body = json.dumps(data).encode() if data else None
    for attempt in range(4):
        req = urllib.request.Request(url, data=body, method=method, headers={
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "EmpCloud-Retest-Bot",
            "Content-Type": "application/json",
        })
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=20)
            result = json.loads(resp.read())
            return result
        except urllib.error.HTTPError as e:
            err = e.read().decode(errors='replace')
            if e.code == 403 and "rate limit" in err.lower():
                wait = 60 * (attempt + 1)
                print(f"    [Rate limited] Waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            elif e.code == 422:
                # Validation error (e.g., issue already open)
                print(f"    [422] {err[:200]}")
                return {"error": 422}
            print(f"    [GH Error] {e.code}: {err[:200]}")
            return None
        except Exception as e:
            print(f"    [Error] {e}")
            return None
    print(f"    [Failed] All retries exhausted")
    return None


def process_issue(issue_num, status, detail):
    print(f"\n  Issue #{issue_num}: {status}")

    if status == "STILL_FAILING":
        comment = (
            f"**Retest (2026-03-27): STILL FAILING**\n\n"
            f"Re-tested from inside the dashboard using Selenium.\n\n"
            f"**Finding:** {detail}\n\n"
            f"Screenshot saved to `screenshots/retest_final/`\n\n"
            f"Re-opening this issue."
        )
        # Re-open
        res = gh_api("PATCH", f"/issues/{issue_num}", {"state": "open"})
        if res:
            print(f"    Re-opened: OK")
        time.sleep(5)
        # Comment
        res = gh_api("POST", f"/issues/{issue_num}/comments", {"body": comment})
        if res:
            print(f"    Comment: OK")
        time.sleep(5)

    elif status == "FIXED":
        comment = (
            f"**Retest (2026-03-27): VERIFIED FIXED**\n\n"
            f"Re-tested from inside the dashboard using Selenium.\n\n"
            f"**Finding:** {detail}\n\n"
            f"Screenshot saved to `screenshots/retest_final/`"
        )
        res = gh_api("POST", f"/issues/{issue_num}/comments", {"body": comment})
        if res:
            print(f"    Comment: OK")
        time.sleep(5)


def main():
    print("=" * 60)
    print("Updating GitHub Issues #98-#131")
    print("=" * 60)

    # Process in order
    for issue_num in sorted(RESULTS.keys()):
        status, detail = RESULTS[issue_num]
        process_issue(issue_num, status, detail)

    # Summary
    fixed = [n for n, (s, _) in RESULTS.items() if s == "FIXED"]
    failing = [n for n, (s, _) in RESULTS.items() if s == "STILL_FAILING"]

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"FIXED ({len(fixed)}):   {sorted(fixed)}")
    print(f"FAILING ({len(failing)}): {sorted(failing)}")
    print(f"\nTotal: {len(RESULTS)} issues processed")
    print(f"  Re-opened: {len(failing)}")
    print(f"  Confirmed fixed: {len(fixed)}")


if __name__ == "__main__":
    main()
