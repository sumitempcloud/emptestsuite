#!/usr/bin/env python3
"""
Close Exit Management issues where the alt path actually works.
From results: /fnf works (FnF found), /kt works (KT found), /interviews works (interviews found)
So the consolidated issue for Exit overstates things. Update it.
Also close some other false positive 404s where the feature exists at a different route.
"""
import requests, time

GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"
HEADERS = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
BASE = f"https://api.github.com/repos/{GH_REPO}"

def update_issue(num, title=None, body=None):
    data = {}
    if title: data["title"] = title
    if body: data["body"] = body
    r = requests.patch(f"{BASE}/issues/{num}", headers=HEADERS, json=data, timeout=30)
    time.sleep(0.5)
    print(f"  Updated #{num}: {r.status_code}")

def close_with_comment(num, comment):
    requests.post(f"{BASE}/issues/{num}/comments", headers=HEADERS,
                 json={"body": comment}, timeout=30)
    time.sleep(0.3)
    requests.patch(f"{BASE}/issues/{num}", headers=HEADERS,
                  json={"state": "closed"}, timeout=30)
    time.sleep(0.3)
    print(f"  Closed #{num}")

def add_comment(num, comment):
    requests.post(f"{BASE}/issues/{num}/comments", headers=HEADERS,
                 json={"body": comment}, timeout=30)
    time.sleep(0.3)
    print(f"  Commented #{num}")

def main():
    # Exit Management consolidated issue #619 - update to reflect actual state
    # Working: Dashboard (/), Clearance (/clearance), Interviews (/interviews), FnF (/fnf), KT (/kt), Analytics (/analytics)
    # NOT working: /initiate, /settlement, /reports, /exit-interview, /knowledge-transfer, /full-final
    # But /interviews, /fnf, /kt work - so Exit is mostly functional, just some alt paths broken

    update_issue(619,
        title="Exit Management — Initiate Exit and Reports pages return 404",
        body=(
            "Some pages in the **Exit Management** module return 404 errors.\n\n"
            "**Working pages:**\n"
            "- Dashboard (/) - PASS\n"
            "- Clearance (/clearance) - PASS\n"
            "- Exit Interviews (/interviews) - PASS\n"
            "- Full & Final Settlement (/fnf) - PASS\n"
            "- Knowledge Transfer (/kt) - PASS\n"
            "- Analytics (/analytics) - PASS\n\n"
            "**Broken pages (404):**\n"
            "- Initiate Exit (/initiate) - no route found to start offboarding\n"
            "- Reports (/reports) - reports page not found\n\n"
            "**Steps to reproduce:**\n"
            "1. Login as HR Admin (ananya@technova.in)\n"
            "2. Navigate to Exit Management module via SSO from dashboard\n"
            "3. Try /initiate or /reports\n\n"
            "**Expected:** Pages load with content\n"
            "**Actual:** 404 Not Found\n\n"
            "---\n*Filed by automated SSO module testing*"
        )
    )

    # Recruitment issue #602 - /reports 404 is a real issue, keep it open but retitle
    update_issue(602,
        title="Recruitment — Reports page returns 404",
        body=(
            "The Recruitment module's Reports page (/reports) returns 404.\n\n"
            "**Working pages:** Dashboard, Jobs (/jobs), Candidates (/candidates), Interviews (/interviews), "
            "Offers (/offers), Onboarding (/onboarding), Settings (/settings)\n\n"
            "**Broken:** Reports (/reports) — 404\n\n"
            "**Steps:** Login as HR Admin > SSO to Recruitment > Navigate to /reports\n"
            "**Expected:** Reports/analytics page loads\n"
            "**Actual:** 404 Not Found\n\n"
            "---\n*Filed by automated SSO module testing*"
        )
    )

    # Payroll consolidated #587 - update with accurate info
    # Working: Dashboard (/), Payslips (/payslips), Tax (/tax), Reports (/reports), Employees (/employees), Reimbursements (/reimbursements)
    # NOT working: /salary, /declarations, /run-payroll, /admin/payroll
    update_issue(587,
        title="Payroll — Salary, Declarations, and Run Payroll pages return 404",
        body=(
            "Several pages in the **Payroll** module return 404 errors.\n\n"
            "**Working pages:**\n"
            "- Dashboard (/) - shows payroll and tax info\n"
            "- My Payslips (/payslips) - loads but no download button\n"
            "- My Tax (/tax) - tax and TDS info visible\n"
            "- Payroll Reports (/reports) - loads\n"
            "- Employees (/employees) - loads\n\n"
            "**Broken pages (404):**\n"
            "- My Salary (/salary, /my-salary, /salary-structure) - no route found\n"
            "- Declarations (/declarations, /tax-declarations) - no route found\n"
            "- Run Payroll (/run-payroll, /payroll-run, /admin/payroll) - no route found\n\n"
            "**Steps to reproduce:**\n"
            "1. Login as HR Admin (ananya@technova.in)\n"
            "2. Navigate to Payroll module via SSO from dashboard\n"
            "3. Try /salary, /declarations, or /run-payroll\n\n"
            "**Expected:** Pages load with salary structure, tax declarations, or payroll processing\n"
            "**Actual:** 404 Not Found\n\n"
            "---\n*Filed by automated SSO module testing*"
        )
    )

    # Performance consolidated #603 - update with accurate info
    # Working: Dashboard (/), Review Cycles (/review-cycles), Goals (/goals), Analytics (/analytics)
    # NOT working: /reviews, /okrs, /self-assessment, /manager-review, /360-feedback, /calibration, /reports
    update_issue(603,
        title="Performance — Reviews, Self Assessment, Manager Review, 360 Feedback, and Calibration pages return 404",
        body=(
            "Multiple sub-pages in the **Performance** module return 404.\n\n"
            "**Working pages:**\n"
            "- Dashboard (/) - shows performance and review info\n"
            "- Review Cycles (/review-cycles) - loads\n"
            "- Goals (/goals) - loads (though no goal/OKR keywords detected)\n"
            "- Analytics (/analytics) - loads\n\n"
            "**Broken pages (404):**\n"
            "- Reviews (/reviews)\n"
            "- OKRs (/okrs)\n"
            "- Self Assessment (/self-assessment, /self-review)\n"
            "- Manager Review (/manager-review, /team-reviews)\n"
            "- 360 Feedback (/360-feedback, /peer-review)\n"
            "- Calibration (/calibration)\n"
            "- Reports (/reports)\n\n"
            "**Steps:** Login as HR Admin > SSO to Performance > Navigate to above paths\n"
            "**Expected:** Each page loads with its content\n"
            "**Actual:** 404 Not Found\n\n"
            "---\n*Filed by automated SSO module testing*"
        )
    )

    # Rewards consolidated #614 - update
    # Working: Dashboard (/), Kudos (/kudos), Challenges (/challenges), Badges (/badges), Leaderboard (/leaderboard), Celebrations (/celebrations)
    # NOT working: /recognition, /catalog, /store
    update_issue(614,
        title="Rewards — Recognition and Rewards Catalog pages return 404",
        body=(
            "Some pages in the **Rewards** module return 404.\n\n"
            "**Working pages:**\n"
            "- Dashboard (/) - shows reward info\n"
            "- Kudos (/kudos) - recognition features found\n"
            "- Team Challenges (/challenges) - loads\n"
            "- Badges (/badges) - loads\n"
            "- Leaderboard (/leaderboard) - loads\n"
            "- Celebrations (/celebrations) - loads\n\n"
            "**Broken pages (404):**\n"
            "- Recognition (/recognition) - 404\n"
            "- Rewards Catalog (/catalog, /rewards-catalog, /store) - no route found\n\n"
            "**Steps:** Login as HR Admin > SSO to Rewards > Navigate to /recognition or /catalog\n"
            "**Expected:** Pages load\n"
            "**Actual:** 404 Not Found\n\n"
            "---\n*Filed by automated SSO module testing*"
        )
    )

    # LMS consolidated #636 - update
    # Working: Dashboard (/), Courses (/courses), Certifications (/certifications), Compliance (/compliance), Analytics (/analytics), My Learning (/my-learning)
    # NOT working: /assign, /assignments, /quiz, /assessments, /quizzes, /certificates, /compliance-training, /reports
    update_issue(636,
        title="LMS — Course Assignments, Quizzes, and Reports pages return 404",
        body=(
            "Several pages in the **LMS** module return 404.\n\n"
            "**Working pages:**\n"
            "- Dashboard (/) - learning overview\n"
            "- Courses (/courses) - loads\n"
            "- Certifications (/certifications) - loads\n"
            "- Compliance Training (/compliance) - loads\n"
            "- Analytics (/analytics) - learner progress\n"
            "- My Learning (/my-learning) - loads\n\n"
            "**Broken pages (404):**\n"
            "- Assign Course (/assign, /assignments) - no route\n"
            "- Quiz/Assessment (/quiz, /assessments, /quizzes) - no route\n"
            "- Certificates (/certificates) - 404 (but /certifications works)\n"
            "- Reports (/reports) - 404\n\n"
            "**Steps:** Login as HR Admin > SSO to LMS > Navigate to /assign or /quiz\n"
            "**Expected:** Pages load\n"
            "**Actual:** 404 Not Found\n\n"
            "---\n*Filed by automated SSO module testing*"
        )
    )

    # Projects consolidated #644 - update
    # Working: Dashboard (/)
    # NOT working: almost everything else
    update_issue(644,
        title="Projects — All sub-pages return 404 (only dashboard works)",
        body=(
            "Nearly all sub-pages in the **Projects** module return 404.\n\n"
            "**Working pages:**\n"
            "- Dashboard (/) - shows project and team overview\n\n"
            "**Broken pages (404):**\n"
            "- Projects List (/projects)\n"
            "- Tasks (/tasks)\n"
            "- Kanban Board (/kanban, /board)\n"
            "- Time Tracking (/time-tracking, /timesheet, /timesheets)\n"
            "- Gantt Chart (/gantt, /timeline)\n"
            "- Reports (/reports)\n"
            "- Settings (/settings)\n"
            "- My Tasks (/my-tasks)\n\n"
            "The module appears to only have the dashboard implemented. "
            "All other routes return 404.\n\n"
            "**Steps:** Login as HR Admin > SSO to Projects > Navigate to any sub-page\n"
            "**Expected:** Sub-pages load with content\n"
            "**Actual:** 404 Not Found for all sub-pages\n\n"
            "---\n*Filed by automated SSO module testing*"
        )
    )

    print("\nDone updating issues!")

if __name__ == "__main__":
    main()
