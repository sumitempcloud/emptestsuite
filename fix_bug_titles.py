"""
Fix GitHub issue titles and bodies to plain English.
Goes slow: 5 seconds between API calls.
"""

import json
import time
import urllib.request

TOKEN = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
BASE = f"https://api.github.com/repos/{REPO}/issues"
DELAY = 5

# Each entry: (issue_number, new_title, new_body, close: bool)
ISSUES = [
    (1060,
     "Some employees have no reporting manager assigned — org chart breaks",
     "## Bug\n\nSome employees in the system have no reporting manager assigned to them. "
     "This causes the org chart to break because it cannot build the hierarchy when manager links are missing.\n\n"
     "## Why it matters\n\nWithout a reporting manager, approval workflows (leave, expenses, etc.) have no one to route to, "
     "and the org chart renders incorrectly or shows orphaned nodes. Every employee should have a reporting manager assigned.",
     False),

    (1059,
     "Employee can view other employees' documents by guessing document ID",
     "## Bug\n\nAn employee can access documents belonging to other employees by directly requesting a document by its ID. "
     "The API does not verify that the requesting user owns the document.\n\n"
     "## Why it matters\n\nThis is a data privacy issue. Employees should only be able to see their own documents. "
     "The backend must check document ownership before returning the file.",
     False),

    (1058,
     "Overtime hours should be auto-calculated from attendance records",
     "## Feature Gap\n\nThe system does not automatically calculate overtime hours based on attendance punch-in/punch-out records. "
     "HR has to manually compute overtime, which is error-prone and time-consuming.\n\n"
     "## Why it matters\n\nAutomatic overtime calculation ensures payroll accuracy and saves HR significant manual effort each pay cycle.",
     False),

    (1057,
     "Overtime should only count after completing regular shift hours",
     "## Feature Gap\n\nThe system currently does not enforce that overtime only begins after an employee has completed their full "
     "regular shift hours. This means partial shifts could incorrectly generate overtime.\n\n"
     "## Why it matters\n\nOvertime pay should only kick in after the standard shift is complete. "
     "Without this check, payroll costs could be inflated by incorrectly classified overtime.",
     False),

    (1056,
     "System should prevent assigning overlapping shifts to same employee",
     "## Feature Gap\n\nThe system allows an employee to be assigned to two shifts that overlap in time. "
     "There is no validation preventing this conflict.\n\n"
     "## Why it matters\n\nOverlapping shifts cause confusion in attendance tracking, incorrect working-hour calculations, "
     "and payroll errors. The system should block or warn when a shift assignment conflicts with an existing one.",
     False),

    (1055,
     "ESI deduction should auto-disable when salary exceeds Rs 21,000 threshold",
     "## Feature Gap\n\nWhen an employee's gross salary exceeds Rs 21,000 per month, ESI (Employee State Insurance) contributions "
     "should automatically stop. Currently the system does not enforce this threshold.\n\n"
     "## Why it matters\n\nESI is only applicable to employees earning below the statutory limit. "
     "Continuing to deduct ESI above the threshold results in incorrect payroll and compliance issues.",
     False),

    (1054,
     "PF deduction should follow Rs 15,000 basic pay threshold rule",
     "## Feature Gap\n\nProvident Fund (PF) deductions should be calculated on basic pay capped at Rs 15,000 (or the actual basic "
     "if lower). The system does not currently enforce this statutory threshold.\n\n"
     "## Why it matters\n\nIncorrect PF calculation leads to compliance violations and wrong deductions on employee payslips. "
     "The system must respect the statutory ceiling for PF computation.",
     False),

    (1053,
     "Salary structure components should sum up to match total CTC",
     "## Feature Gap\n\nWhen defining a salary structure, the individual components (basic, HRA, allowances, employer contributions, etc.) "
     "should add up to the total CTC. The system does not validate this.\n\n"
     "## Why it matters\n\nIf components don't match CTC, payslips will be inaccurate and employees will see discrepancies. "
     "A validation check ensures the salary breakdown is mathematically consistent.",
     False),

    (1052,
     "Survey results can be viewed before survey ends — early peeking allowed",
     "## Bug\n\nSurvey results and analytics are accessible even while the survey is still active and collecting responses. "
     "Anyone with access to results can see partial data before the survey end date.\n\n"
     "## Why it matters\n\nEarly access to survey results can bias decision-making and discourage honest responses if participants "
     "learn that results are being monitored in real time. Results should be locked until the survey closes.",
     False),

    (1051,
     "CTC calculation formula (Gross + Employer PF + ESI + Gratuity) should be validated",
     "## Feature Gap\n\nThe system does not validate that CTC equals Gross Salary plus employer-side statutory contributions "
     "(PF, ESI, Gratuity). There is no formula enforcement.\n\n"
     "## Why it matters\n\nWithout this validation, CTC figures can be inconsistent with actual salary components, "
     "causing confusion during offer letters, appraisals, and payroll processing.",
     False),

    (1050,
     "Salary field should not accept zero or negative values",
     "## Bug\n\nThe salary input field accepts zero and negative numbers without any validation error. "
     "It is possible to save an employee record with a salary of 0 or -5000.\n\n"
     "## Why it matters\n\nZero or negative salaries are invalid and cause downstream errors in payroll processing, "
     "tax calculations, and reports. The field should reject these values with a clear error message.",
     False),

    (1049,
     "Failed login attempts are not recorded in the audit log",
     "## Bug\n\nWhen a user enters incorrect credentials, the failed login attempt is not captured in the system's audit log. "
     "Only successful logins are recorded.\n\n"
     "## Why it matters\n\nFailed login tracking is essential for security monitoring. Without it, brute-force attempts "
     "and unauthorized access attempts go undetected. The audit log should record every failed login with timestamp and IP.",
     False),

    (1048,
     "No API to calculate working days excluding holidays and weekends",
     "## Bug\n\nThere is no API endpoint or utility to calculate the number of working days between two dates, "
     "excluding weekends and configured holidays.\n\n"
     "## Why it matters\n\nWorking day calculations are needed for leave balances, project timelines, payroll pro-rating, "
     "and SLA tracking. Without this, each module has to implement its own (possibly inconsistent) logic.",
     False),

    (1040,
     "Nomination program allows self-nomination without other nominators",
     "## Bug\n\nIn the rewards/recognition module, an employee can nominate themselves for a program. "
     "The system does not block self-nominations or require at least one external nominator.\n\n"
     "## Why it matters\n\nSelf-nomination defeats the purpose of peer recognition programs. "
     "The system should either block self-nominations entirely or require additional nominators to validate the nomination.",
     False),

    (1039,
     "System allows deleting department that still has active employees",
     "## Bug\n\nA department can be deleted even when it still has active employees assigned to it. "
     "There is no check to prevent this.\n\n"
     "## Why it matters\n\nDeleting a department with active employees orphans those employees — they lose their department assignment, "
     "which breaks org charts, reports, and approval workflows. The system should block deletion until all employees are reassigned.",
     False),

    (1038,
     "Department can exist without any manager assigned",
     "## Bug\n\nA department can be created or left in a state where no manager is assigned to it. "
     "The system does not enforce that every department must have a manager.\n\n"
     "## Why it matters\n\nA department without a manager has no one to approve leave, expenses, or other requests for its members. "
     "This creates workflow dead-ends. Every department should have at least one designated manager.",
     False),

    (1037,
     "Document category can be deleted even when documents exist in it",
     "## Bug\n\nA document category can be deleted even though there are still documents filed under it. "
     "No validation prevents this.\n\n"
     "## Why it matters\n\nDeleting a category with existing documents orphans those documents — they become uncategorized "
     "and may disappear from search and listing views. The system should block deletion or require moving documents first.",
     False),

    (1021,
     "Deactivated employees still appear in the default employee list",
     "## Bug\n\nEmployees who have been deactivated (terminated, resigned, etc.) still show up in the default employee listing. "
     "The list does not filter them out by default.\n\n"
     "## Why it matters\n\nManagers and HR see a cluttered list mixing active and inactive employees. "
     "This causes confusion when assigning work, sending communications, or running headcount reports. "
     "Inactive employees should be hidden by default and only visible with an explicit filter.",
     False),

    (1017,
     "Past leave that already happened can still be cancelled",
     "## Bug\n\nThe system allows cancelling a leave request for dates that have already passed. "
     "For example, if an employee took leave last week, they can still cancel that leave today.\n\n"
     "## Why it matters\n\nCancelling past leave retroactively messes up attendance records, leave balances, and payroll calculations. "
     "Once a leave date has passed, it should be locked and only modifiable by HR/admin with proper justification.",
     False),

    (1013,
     "No seat limit check — org can invite unlimited users beyond subscription seats",
     "## Bug\n\nThe system does not check the organization's subscription seat limit when inviting new users. "
     "An org subscribed for 50 seats can invite 500 users without any warning or block.\n\n"
     "## Why it matters\n\nThis is a billing loophole. Organizations can use more seats than they pay for. "
     "The system should enforce the seat limit and prompt an upgrade when the limit is reached.",
     False),
]


def api_call(method, url, data=None):
    """Make a GitHub API call."""
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main():
    total = len(ISSUES)
    for idx, (number, title, body, close) in enumerate(ISSUES, 1):
        print(f"\n[{idx}/{total}] Issue #{number}")
        print(f"  New title: {title}")

        payload = {"title": title, "body": body}
        if close:
            payload["state"] = "closed"
            print("  Action: CLOSE")

        status, resp = api_call("PATCH", f"{BASE}/{number}", payload)

        if status in (200, 201):
            print(f"  OK (HTTP {status})")
        else:
            print(f"  FAILED (HTTP {status}): {resp}")

        if idx < total:
            print(f"  Waiting {DELAY}s...")
            time.sleep(DELAY)

    print("\nDone! All issues updated.")


if __name__ == "__main__":
    main()
