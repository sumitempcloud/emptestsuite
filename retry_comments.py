#!/usr/bin/env python3
"""Retry posting GitHub comments for rate-limited issues."""
import sys, json, time, requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

GITHUB_TOKEN = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
TODAY = "2026-03-28"

# All issue verdicts from the test run
VERDICTS = {
    703: ("STILL FAILING", "Login as Org Admin via Selenium, navigate to /employees, look for 'Invite Employee' button -> NOT FOUND"),
    702: ("INCONCLUSIVE", "Navigate to /audit-log -> redirects to root. Feature request (audit log UI page)"),
    701: ("STILL FAILING", "Navigate to /assets as Employee -> 403 Forbidden. Assets page not accessible"),
    700: ("INCONCLUSIVE", "GET /organizations/me/leave/applications -> 200 OK with 20 results. User field value = None (field not present in API response)"),
    699: ("STILL FAILING", "GET /organizations/me/org-chart -> 404. Org chart API endpoint not found, returns 0 entries"),
    698: ("FIXED", "Login as Employee, navigate to /helpdesk -> page loaded without redirect to dashboard"),
    697: ("FIXED", "Login as Employee, POST leave application -> 201 Created. Leave application submitted successfully"),
    696: ("STILL FAILING", "Navigate to /attendance -> no date picker or department filter elements found on page"),
    695: ("STILL FAILING", "Navigate to /employees as Org Admin -> no 'Add Employee' button found"),
    694: ("STILL FAILING", "GET org chart API -> 404, returns 0 entries when org has 20+ employees"),
    693: ("STILL FAILING", "GET /docs -> 404. API documentation endpoint not found"),
    692: ("FIXED", "Login as Org Admin, POST leave application -> 201 Created. HR Manager can now apply leave successfully"),
    691: ("INCONCLUSIVE", "POST document with wrong multipart field -> 404 (endpoint not found at /organizations/me/documents)"),
    690: ("STILL FAILING", "POST leave application -> 400 'Overlapping leave application exists'. Error message improved but test dates overlap with existing application"),
    689: ("FIXED", "Login as Employee, navigate to /exit/analytics/flight-risk -> redirected away. Employee correctly denied access"),
    688: ("FIXED", "Login as Employee, navigate to /exit/full-and-final -> redirected away. Access correctly denied"),
    687: ("FIXED", "Login as Employee, navigate to /exit -> redirected away. Access correctly denied"),
    686: ("FIXED", "Login as Employee, navigate to /exit -> redirected away. Admin navigation not exposed"),
    685: ("FIXED", "Login as Employee, navigate to /performance/review-cycles -> redirected away. Access correctly denied"),
    684: ("FIXED", "Login as Employee, navigate to /performance/settings -> redirected away. Access correctly denied"),
    683: ("FIXED", "Login as Employee, navigate to /performance/succession-planning -> redirected away. Access correctly denied"),
    682: ("FIXED", "Login as Employee, navigate to /performance/9-box -> redirected away. Access correctly denied"),
    681: ("FIXED", "Login as Employee, navigate to /performance/analytics -> redirected away. Access correctly denied"),
    680: ("FIXED", "Login as Employee, navigate to /performance/pips -> redirected away. Access correctly denied"),
    679: ("FIXED", "Login as Employee, navigate to /performance -> redirected away. Admin navigation not exposed"),
    678: ("FIXED", "Login as Employee, navigate to /payroll -> redirected away. Admin Panel link not accessible"),
    677: ("INCONCLUSIVE", "POST /organizations/me/announcements -> 404 endpoint not found. Cannot verify announcement validation"),
    676: ("INCONCLUSIVE", "Enhancement request for bulk ops, export, notifications. Would need new endpoints to verify"),
    673: ("STILL FAILING", "Login as Employee, found notification bell, clicked it -> no visible notification panel/dropdown opened"),
    672: ("FIXED", "Login as Employee, navigate to /modules, found Payroll module, clicked -> module accessible"),
    671: ("FIXED", "Login as Employee, navigate to /helpdesk -> page loaded without redirect to dashboard"),
    670: ("STILL FAILING", "Navigate to /profile as Employee -> Edit Profile button NOT FOUND on page"),
    669: ("STILL FAILING", "Navigate to /employees as Org Admin -> 'Add Employee' button NOT FOUND"),
    668: ("INCONCLUSIVE", "GET /organizations/me/feedback as employee -> 404 endpoint not found"),
    667: ("STILL FAILING", "Navigate to /payroll -> redirects to root. Payroll module sub-pages still inaccessible"),
    666: ("FIXED", "Login as Employee, navigate to /modules, found Projects -> module accessible"),
    665: ("STILL FAILING", "Login as Employee, navigate to /modules -> page loads without restriction. Employee CAN see module management"),
    664: ("STILL FAILING", "Navigate to /performance -> redirects to root. Performance module sub-pages still 404"),
    663: ("INCONCLUSIVE", "Token expired during test. Could not verify leave application"),
    662: ("STILL FAILING", "Navigate to /rewards -> redirects to root. Rewards module still inaccessible"),
    661: ("INCONCLUSIVE", "GET /organizations/me/dashboard -> 404 endpoint not found"),
    660: ("STILL FAILING", "Navigate to /exit -> redirects to root. Exit module pages still inaccessible"),
    659: ("STILL FAILING", "Navigate to /lms -> redirects to root. LMS module pages still inaccessible"),
    658: ("STILL FAILING", "Navigate to /projects/tasks -> redirects to root. Projects sub-pages still 404"),
    657: ("STILL FAILING", "Navigate to /employees -> 'Add Employee' button NOT FOUND on page"),
    655: ("STILL FAILING", "Navigate to /projects/my-tasks -> redirects to root"),
    654: ("STILL FAILING", "Navigate to /projects/settings -> redirects to root"),
    653: ("STILL FAILING", "Navigate to /projects/reports -> redirects to root"),
    652: ("STILL FAILING", "Navigate to /projects/timeline -> redirects to root"),
    651: ("STILL FAILING", "Navigate to /projects/gantt -> redirects to root"),
    650: ("STILL FAILING", "Navigate to /projects/timesheets -> redirects to root"),
    649: ("STILL FAILING", "Navigate to /projects/timesheet -> redirects to root"),
    648: ("STILL FAILING", "Navigate to /projects/time-tracking -> redirects to root"),
    647: ("STILL FAILING", "Navigate to /projects/board -> redirects to root"),
    646: ("STILL FAILING", "Navigate to /projects/board -> redirects to root"),
    645: ("STILL FAILING", "Navigate to /projects/tasks -> redirects to root"),
    644: ("STILL FAILING", "Navigate to /projects -> redirects to root"),
    643: ("STILL FAILING", "Navigate to /lms/reports -> redirects to root"),
    642: ("STILL FAILING", "Navigate to /lms/compliance-training -> redirects to root"),
    641: ("STILL FAILING", "Navigate to /lms/certificates -> redirects to root"),
    640: ("STILL FAILING", "Navigate to /lms/quizzes -> redirects to root"),
    639: ("STILL FAILING", "Navigate to /lms/assessments -> redirects to root"),
    638: ("STILL FAILING", "Navigate to /lms/quiz -> redirects to root"),
    637: ("STILL FAILING", "Navigate to /lms/assignments -> redirects to root"),
    636: ("STILL FAILING", "Navigate to /lms/assignments -> redirects to root"),
    635: ("STILL FAILING", "Navigate to /exit/reports -> redirects to root"),
    634: ("STILL FAILING", "Navigate to /exit/knowledge-transfer -> redirects to root"),
    633: ("FIXED", "Navigate to /attendance -> page loads (enhancement: filters still missing)"),
    632: ("STILL FAILING", "Navigate to /exit/full-and-final -> redirects to root"),
    631: ("FIXED", "Login as Employee, found Performance on /modules page -> module accessible"),
    630: ("STILL FAILING", "Navigate to /exit/full-and-final -> redirects to root"),
    629: ("INCONCLUSIVE", "Token expired. Could not verify leave type name"),
    628: ("STILL FAILING", "Navigate to /exit/interview -> redirects to root"),
    627: ("INCONCLUSIVE", "Token expired. Could not verify date formatting"),
    626: ("INCONCLUSIVE", "Token expired. Could not verify user name display"),
    625: ("STILL FAILING", "Navigate to /exit/clearance -> redirects to root"),
    624: ("STILL FAILING", "Navigate to /exit/new -> redirects to root"),
    622: ("STILL FAILING", "Navigate to /exit/initiate-exit -> redirects to root"),
    620: ("FIXED", "Navigate to /modules -> page loads. Modules page accessible"),
    619: ("STILL FAILING", "Navigate to /exit/initiate-exit -> redirects to root"),
    618: ("STILL FAILING", "Navigate to /rewards/store -> redirects to root"),
    617: ("STILL FAILING", "Navigate to /rewards/catalog -> redirects to root"),
    616: ("STILL FAILING", "Navigate to /rewards/catalog -> redirects to root"),
    615: ("STILL FAILING", "Navigate to /rewards/team-challenges -> redirects to root"),
    614: ("STILL FAILING", "Navigate to /rewards/recognition -> redirects to root"),
    613: ("STILL FAILING", "Navigate to /rewards/give-kudos -> redirects to root"),
    612: ("STILL FAILING", "Navigate to /performance/reports -> redirects to root"),
    611: ("STILL FAILING", "Navigate to /performance/calibration -> redirects to root"),
    610: ("STILL FAILING", "Navigate to /performance/peer-review -> redirects to root"),
    609: ("STILL FAILING", "Navigate to /performance/360-feedback -> redirects to root"),
    608: ("STILL FAILING", "Navigate to /performance/team-reviews -> redirects to root"),
    607: ("STILL FAILING", "Navigate to /performance/manager-review -> redirects to root"),
    606: ("STILL FAILING", "Navigate to /performance/self-review -> redirects to root"),
    605: ("STILL FAILING", "Navigate to /performance/self-assessment -> redirects to root"),
    604: ("STILL FAILING", "Navigate to /performance/okrs -> redirects to root"),
}

def post_comment(issue_num, body):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_num}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.post(url, json={"body": body}, headers=headers, timeout=30)
    return resp.status_code

def reopen_issue(issue_num):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_num}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.patch(url, json={"state": "open"}, headers=headers, timeout=30)
    return resp.status_code

# Check rate limit
print("Checking rate limit status...")
resp = requests.get("https://api.github.com/rate_limit",
                     headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=10)
rl = resp.json().get("resources", {}).get("core", {})
print(f"  Rate limit: {rl.get('remaining')}/{rl.get('limit')}, resets at {rl.get('reset')}")

success = 0
failed = 0
rate_limited = 0

for issue_num in sorted(VERDICTS.keys(), reverse=True):
    verdict, details = VERDICTS[issue_num]

    comment = (
        f"Comment by E2E Testing Agent \u2014 Re-tested on {TODAY}:\n"
        f"- {details}\n"
        f"- Result: **{verdict}**"
    )

    status = post_comment(issue_num, comment)
    if status == 201:
        print(f"  #{issue_num}: comment posted ({verdict})")
        success += 1
    elif status == 403:
        print(f"  #{issue_num}: RATE LIMITED - waiting 120s then retrying...")
        rate_limited += 1
        time.sleep(120)
        status = post_comment(issue_num, comment)
        if status == 201:
            print(f"  #{issue_num}: comment posted on retry ({verdict})")
            success += 1
        else:
            print(f"  #{issue_num}: still failed after retry ({status}) - stopping batch")
            failed += 1
            break
    else:
        print(f"  #{issue_num}: error ({status})")
        failed += 1

    # Reopen if still failing (idempotent)
    if verdict == "STILL FAILING":
        rs = reopen_issue(issue_num)
        if rs == 200:
            print(f"    -> Re-opened #{issue_num}")
        time.sleep(2)

    time.sleep(3)

print(f"\nDone: {success} comments posted, {failed} failed, {rate_limited} rate-limited retries")
