"""Update remaining GitHub issues that weren't processed yet."""
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

# Only issues that HAVEN'T been updated yet (121+)
REMAINING = {
    121: ("STILL_FAILING", "/reports redirects to root URL for org admin instead of showing reports."),
    122: ("FIXED", "Employee redirected from /settings. Cannot see full org settings."),
    123: ("FIXED", "Employee redirected from /admin/ai-config. Cannot see AI configuration."),
    124: ("FIXED", "Employee redirected from /admin/logs. Cannot see log dashboard."),
    125: ("FIXED", "Duplicate of #107. Search input found on /employees."),
    126: ("FIXED", "Duplicate of #109. Employee row clicking works."),
    127: ("FIXED", "Duplicate of #110. Add Employee button found."),
    128: ("STILL_FAILING", "Duplicate of #99. Regularization/events error persists."),
    129: ("FIXED", "Duplicate of #107. Search input found on /employees."),
    130: ("FIXED", "Duplicate of #109. Employee row clicking works."),
    131: ("FIXED", "Duplicate of #110. Add Employee button found."),
}


def gh_api(method, endpoint, data=None):
    url = f"https://api.github.com/repos/{GITHUB_REPO}{endpoint}"
    body = json.dumps(data).encode() if data else None
    for attempt in range(4):
        req = urllib.request.Request(url, data=body, method=method, headers={
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Content-Type": "application/json",
        })
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=20)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            err = e.read().decode(errors='replace')
            if e.code == 403 and "rate limit" in err.lower():
                wait = 60 * (attempt + 1)
                print(f"    [Rate limited] Waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"    [GH Error] {e.code}: {err[:200]}")
            return None
        except Exception as e:
            print(f"    [Error] {e}")
            return None
    return None


for issue_num in sorted(REMAINING.keys()):
    status, detail = REMAINING[issue_num]
    print(f"\n  Issue #{issue_num}: {status}")

    if status == "STILL_FAILING":
        comment = (
            f"**Retest (2026-03-27): STILL FAILING**\n\n"
            f"Re-tested from inside the dashboard using Selenium.\n\n"
            f"**Finding:** {detail}\n\n"
            f"Re-opening this issue."
        )
        res = gh_api("PATCH", f"/issues/{issue_num}", {"state": "open"})
        print(f"    Re-opened: {'OK' if res else 'FAILED'}")
        time.sleep(5)
        res = gh_api("POST", f"/issues/{issue_num}/comments", {"body": comment})
        print(f"    Comment: {'OK' if res else 'FAILED'}")
        time.sleep(5)
    elif status == "FIXED":
        comment = (
            f"**Retest (2026-03-27): VERIFIED FIXED**\n\n"
            f"Re-tested from inside the dashboard using Selenium.\n\n"
            f"**Finding:** {detail}\n\n"
            f"Screenshot saved to `screenshots/retest_final/`"
        )
        res = gh_api("POST", f"/issues/{issue_num}/comments", {"body": comment})
        print(f"    Comment: {'OK' if res else 'FAILED'}")
        time.sleep(5)

print("\nDone!")
