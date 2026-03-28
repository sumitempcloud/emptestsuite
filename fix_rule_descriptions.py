"""
Fix GitHub issue descriptions for EmpCloud/EmpCloud repo.
Rewrites cryptic rule-number issues with clear plain English titles and detailed bodies.
"""

import urllib.request
import json
import time
import ssl

TOKEN = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
BASE = f"https://api.github.com/repos/{REPO}/issues"
DELAY = 5  # seconds between API calls

# SSL context for Windows
ctx = ssl.create_default_context()

def patch_issue(number, title, body):
    """PATCH an issue to update title and body."""
    url = f"{BASE}/{number}"
    data = json.dumps({"title": title, "body": body}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PATCH", headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        result = json.loads(resp.read())
        print(f"  OK - updated #{number}: {result['title']}")
        return True
    except Exception as e:
        print(f"  FAILED #{number}: {e}")
        return False


# ============================================================
# BUSINESS RULES AGENT issues
# ============================================================

business_rules = {
    1018: {
        "title": "Employees on probation should have restricted leave access — no policy exists",
        "body": """## What is needed
Employees who are still in their probation period should have limited or no access to certain leave types (such as earned leave or casual leave). A probation-aware leave policy needs to be created so the system can automatically restrict leave for new joiners until their probation ends.

## Current behavior
The leave module has no concept of probation periods. A brand-new employee on Day 1 of probation has the same leave entitlements as a confirmed employee. There is no configuration to link probation status with leave eligibility.

## How it should work
1. HR Admin should be able to define probation duration (e.g., 3 months, 6 months) in the employee onboarding or policy settings
2. Leave policies should have a toggle or rule that says "available only after probation" for specific leave types
3. When a probationary employee tries to apply for a restricted leave type, the system should show a clear message like "This leave type is not available during your probation period"
4. Once probation is marked as complete, the employee should automatically gain access to all applicable leave types

## Who needs it
HR Manager, Employees (new joiners)

## Why it matters
Without probation-based leave restrictions, new employees can exhaust their leave balance before confirmation. This creates policy inconsistencies and administrative overhead for HR who must manually track and reject leaves during probation."""
    },

    1019: {
        "title": "System should block deletion of employees who have pending items like assets or leave balances",
        "body": """## What is needed
Before an employee record can be deleted (or permanently deactivated), the system should check for any pending items — such as unreturned assets, pending leave requests, outstanding loans, or unresolved helpdesk tickets — and prevent the deletion until those items are cleared.

## Current behavior
The employee deletion endpoint does not exist (returns 404). Even when employee removal is eventually implemented, there is no validation logic to check for pending dependencies before allowing deletion.

## How it should work
1. When an admin attempts to delete or permanently remove an employee, the system should first scan for pending items (unreturned assets, open leave requests, pending reimbursements, active loans, open helpdesk tickets)
2. If any pending items exist, the system should block the deletion and display a clear summary: "Cannot delete employee — 2 assets not returned, 1 pending leave request"
3. The admin should be able to see exactly which items need to be resolved
4. Only after all pending items are cleared or transferred should deletion proceed

## Who needs it
HR Manager, Super Admin

## Why it matters
Deleting an employee with pending items creates orphaned records — assets that no one is accountable for, leave balances that disappear, and audit trail gaps. This is critical for data integrity, compliance, and proper offboarding."""
    },

    1022: {
        "title": "System should prevent deleting an asset that is currently assigned to an employee",
        "body": """## What is needed
When an asset (laptop, phone, ID card, etc.) is currently assigned to an employee, the system should not allow that asset to be deleted. The asset must first be unassigned or returned before it can be removed from the system.

## Current behavior
The asset deletion endpoint does not exist (returns 404). When asset deletion is implemented, there is no planned validation to check whether the asset is currently assigned to someone.

## How it should work
1. When an admin tries to delete an asset, the system should check the asset's assignment status
2. If the asset is currently assigned to an employee, block the deletion with a clear error: "Cannot delete this asset — it is currently assigned to [Employee Name]"
3. The admin should first unassign the asset (mark it as returned) and then delete it
4. Only unassigned or decommissioned assets should be deletable

## Who needs it
HR Manager, IT Admin

## Why it matters
Deleting an assigned asset breaks the chain of custody. The employee would still physically have the asset, but there would be no system record of it. This creates accountability gaps and makes IT asset audits unreliable."""
    },

    1023: {
        "title": "When an asset is unassigned from an employee, the return date should be automatically recorded",
        "body": """## What is needed
When an asset is unassigned from an employee (returned to inventory), the system should automatically capture and store the return date. This ensures a complete audit trail of when assets were issued and when they came back.

## Current behavior
The asset data model does not include any return date or unassignment date fields. The current asset fields track purchase date, warranty, and status, but there is no way to record when an asset was returned by an employee.

## How it should work
1. Add a "return_date" field to the asset assignment record
2. When an admin unassigns an asset from an employee, the system should automatically set the return date to the current date
3. The return date should be visible in the asset history and the employee's asset assignment history
4. Asset reports should be able to filter by return date for audit purposes

## Who needs it
HR Manager, IT Admin, Finance team (for asset depreciation tracking)

## Why it matters
Without return dates, there is no way to verify when an asset was actually returned. This is essential for exit processes, IT asset audits, and resolving disputes about asset custody. It also helps track asset utilization and turnaround time."""
    },

    1056: {
        "title": "System allows assigning overlapping shifts to the same employee — no conflict validation",
        "body": """## What is needed
When assigning a shift to an employee, the system should check whether the new shift overlaps with any existing shift already assigned to that employee. If there is a time conflict, the system should block the assignment or show a warning.

## Current behavior
The system allows assigning two or more shifts that overlap in time to the same employee without any validation or warning. For example, an employee could be assigned both a 9 AM - 6 PM shift and a 2 PM - 10 PM shift on the same day.

## How it should work
1. When a new shift is being assigned to an employee, the system should check all existing shift assignments for that employee on the same date(s)
2. If the new shift overlaps with an existing shift (any time period that intersects), the system should block the assignment with an error: "This shift conflicts with an existing shift assigned to this employee"
3. If the organization wants to allow split shifts, there should be an explicit configuration option for that
4. The conflict check should work for both single-day and recurring shift assignments

## Who needs it
HR Manager, Shift Supervisor, Payroll team

## Why it matters
Overlapping shifts cause chaos in attendance tracking — the system cannot determine which shift the employee is working. This leads to incorrect working-hour calculations, wrong overtime figures, and payroll errors. It also creates confusion for the employee about their actual schedule."""
    },

    995: {
        "title": "System does not enforce hiring limits — positions can be filled beyond approved headcount",
        "body": """## What is needed
The system should enforce headcount limits during the recruitment and hiring process. When a department has an approved headcount of, say, 10 people, the system should not allow an 11th hire to be processed without explicit approval or headcount revision.

## Current behavior
The headcount management feature does not work. The API returns a validation error when attempting to check headcount limits, meaning there is no functional headcount enforcement in the recruitment pipeline. Recruiters can process unlimited hires regardless of approved positions.

## How it should work
1. HR Admin should be able to set approved headcount for each department or position
2. During the hiring process, when a candidate is being moved to "offer" or "hired" stage, the system should check the current filled positions against the approved headcount
3. If the headcount limit would be exceeded, the system should block the action with a message: "Cannot process this hire — department headcount limit reached (10/10 positions filled)"
4. A senior HR leader or admin should have the ability to override or increase the headcount with proper justification

## Who needs it
HR Manager, Recruitment team, Department heads

## Why it matters
Without headcount enforcement, organizations risk over-hiring, which leads to budget overruns and staffing imbalances. Headcount governance is a fundamental HR control required for workforce planning, budgeting, and compliance with organizational policies."""
    },
}


# ============================================================
# PAYROLL RULES AGENT issues
# ============================================================

payroll_rules = {
    1051: {
        "title": "CTC calculation should be validated — Gross plus employer PF, ESI, and Gratuity must equal total CTC",
        "body": """## What is needed
The system should validate that an employee's Cost to Company (CTC) equals the sum of Gross Salary plus all employer-side statutory contributions — specifically Employer PF, Employer ESI, and Gratuity. This formula must be enforced whenever a salary structure is created or modified.

## Current behavior
The system does not validate the CTC formula. An admin can enter a CTC value that does not match the sum of its underlying components. There is no consistency check between CTC and the actual salary breakdown.

## How it should work
1. When creating or editing a salary structure, the system should compute: CTC = Gross Salary + Employer PF + Employer ESI + Gratuity
2. If the entered CTC does not match this computed total, the system should show an error: "CTC does not match the sum of salary components — expected Rs X but got Rs Y"
3. The system should either auto-calculate CTC from components or auto-adjust components to match CTC (configurable by admin)
4. This validation should run on both manual entry and bulk salary uploads

## Who needs it
HR Manager, Payroll team, Finance team

## Why it matters
When CTC does not match its components, offer letters show one number while payslips show another. This creates confusion during appraisals, causes discrepancies in tax projections, and undermines employee trust. Accurate CTC computation is fundamental to payroll integrity."""
    },

    1053: {
        "title": "Salary structure components should add up to total CTC — no validation exists",
        "body": """## What is needed
When defining a salary structure, the individual components (Basic Pay, HRA, Special Allowance, employer contributions, etc.) should mathematically add up to the declared total CTC. The system should enforce this and not allow saving a salary structure where the numbers do not balance.

## Current behavior
The system allows saving a salary structure where the individual components do not add up to the total CTC. For example, you could set CTC as Rs 10,00,000 but the components could total Rs 9,50,000 — the system would accept this without any warning.

## How it should work
1. When an admin creates or modifies a salary structure, the system should sum all components (basic, HRA, allowances, employer statutory contributions)
2. Compare this sum against the declared CTC value
3. If there is a mismatch, show a clear error: "Salary components total Rs 9,50,000 but CTC is set to Rs 10,00,000 — please correct the difference of Rs 50,000"
4. The system should not allow saving the structure until the numbers balance
5. Optionally, provide an "auto-adjust" feature that distributes the remaining amount to a flexible component like Special Allowance

## Who needs it
HR Manager, Payroll team

## Why it matters
If components do not match CTC, payslips will be inaccurate and employees will see unexplained discrepancies. During audits, mismatched salary structures raise red flags. This is a basic data integrity check that every payroll system must have."""
    },

    1054: {
        "title": "PF deduction should apply only on basic pay up to Rs 15,000 — statutory threshold not enforced",
        "body": """## What is needed
Provident Fund (PF) contributions should be calculated on basic pay capped at Rs 15,000 per month, as per the statutory ceiling set by the Employees' Provident Fund Organisation (EPFO). If an employee's basic pay exceeds Rs 15,000, PF should still be computed on Rs 15,000 unless the employer opts for PF on actual basic.

## Current behavior
The system does not enforce the Rs 15,000 statutory ceiling for PF computation. There is no threshold-based logic in the PF calculation, meaning PF could be calculated incorrectly — either over-deducting or under-deducting.

## How it should work
1. By default, PF should be calculated as 12% of basic pay, capped at Rs 15,000 (i.e., maximum employee PF contribution of Rs 1,800 per month)
2. If an employee's basic pay is below Rs 15,000, PF should be calculated on the actual basic
3. There should be a configuration option for "PF on actual basic" for employers who choose to contribute on the full basic salary
4. The employer PF contribution should follow the same ceiling rule
5. This should be clearly reflected on payslips with the correct PF basis amount shown

## Who needs it
Payroll team, HR Manager, Finance team

## Why it matters
PF calculation errors lead to statutory non-compliance, incorrect employee deductions, and mismatches during EPFO filings. Employees may be over-deducted or under-deducted, leading to disputes and penalties from regulatory authorities."""
    },

    1055: {
        "title": "ESI deduction should automatically stop when gross salary exceeds Rs 21,000 per month",
        "body": """## What is needed
Employee State Insurance (ESI) contributions should automatically stop being deducted when an employee's gross salary exceeds Rs 21,000 per month. This is a statutory requirement — ESI only applies to employees earning below this threshold.

## Current behavior
The system does not enforce the Rs 21,000 gross salary threshold for ESI applicability. There is no automatic check that disables ESI deductions when an employee's salary crosses the limit, whether through a salary revision, promotion, or annual increment.

## How it should work
1. During payroll processing, the system should check each employee's gross salary against the Rs 21,000 threshold
2. If gross salary is Rs 21,000 or below, apply ESI deductions (employee: 0.75%, employer: 3.25%)
3. If gross salary exceeds Rs 21,000, automatically skip ESI deductions for that employee
4. When an employee's salary is revised and crosses the threshold, the system should automatically stop ESI from the next payroll cycle
5. Generate a notification to HR when an employee moves out of ESI eligibility

## Who needs it
Payroll team, HR Manager, Finance team

## Why it matters
Deducting ESI from employees who earn above the statutory limit is non-compliant and results in incorrect take-home pay. It also creates complications during ESI filings and can lead to refund requests. This threshold check is a basic statutory compliance requirement for Indian payroll."""
    },

    1057: {
        "title": "Overtime pay should only start after an employee completes their full regular shift hours",
        "body": """## What is needed
The system should ensure that overtime hours are only counted after an employee has completed their full regular shift duration. If an employee works less than their scheduled shift hours, those extra minutes should not be treated as overtime — they are just catching up on regular hours.

## Current behavior
The system does not enforce the rule that overtime begins only after the full regular shift is completed. This means an employee who was scheduled for 8 hours but worked 7 hours on Monday and 10 hours on Tuesday could potentially get overtime credit for Tuesday even though they were short on Monday.

## How it should work
1. The system should know each employee's regular shift duration (e.g., 8 hours, 9 hours)
2. When calculating overtime, first verify that the employee has completed their full scheduled shift hours for that day
3. Only hours worked beyond the regular shift duration should count as overtime
4. If an employee clocks out early and comes back, the gap should be handled according to company policy (configurable)
5. Overtime calculations should feed directly into payroll for accurate overtime pay computation

## Who needs it
Payroll team, HR Manager, Shift Supervisor

## Why it matters
If overtime is counted without verifying full shift completion, the organization pays overtime wages for regular work hours. This inflates payroll costs and creates unfair discrepancies between employees. Accurate overtime tracking is essential for labor law compliance and cost control."""
    },

    1058: {
        "title": "Overtime hours should be automatically calculated from attendance punch-in and punch-out records",
        "body": """## What is needed
The system should automatically calculate overtime hours by comparing an employee's actual attendance records (punch-in/punch-out times) against their assigned shift schedule. HR should not need to manually compute overtime for each employee every pay cycle.

## Current behavior
The system does not automatically compute overtime from attendance data. HR teams must manually review attendance logs, compare against shift schedules, and calculate overtime hours — which is slow, error-prone, and does not scale.

## How it should work
1. The system should pull each employee's punch-in and punch-out times from attendance records
2. Compare actual working hours against the assigned shift schedule for that day
3. Any hours worked beyond the scheduled shift (after completing full regular hours) should be flagged as overtime
4. Overtime hours should be categorized (regular overtime, weekend overtime, holiday overtime) based on when they occurred
5. The calculated overtime should be available in payroll processing for automatic overtime pay computation
6. HR should be able to review and approve overtime before it is sent to payroll

## Who needs it
Payroll team, HR Manager, Employees

## Why it matters
Manual overtime calculation is one of the biggest time sinks in payroll processing. It leads to errors, disputes, and delayed salary disbursement. Automating this saves HR hours of work each pay cycle and ensures every employee is paid accurately for their extra hours."""
    },
}


# ============================================================
# PLATFORM SECURITY AGENT issues
# ============================================================

security_rules = {
    1024: {
        "title": "No password expiry or rotation policy — users can keep the same password forever",
        "body": """## What is needed
The platform should enforce a password expiry and rotation policy. Users should be required to change their passwords periodically (e.g., every 90 days) and should not be able to reuse recent passwords. This is a fundamental security control for any enterprise platform.

## Current behavior
There is no password rotation or expiry mechanism. Once a user sets a password, they can use it indefinitely without ever being prompted to change it. There are no settings for configuring password expiry duration or reuse restrictions.

## How it should work
1. Super Admin should be able to configure password expiry duration (e.g., 30, 60, 90 days) in the platform security settings
2. When a user's password reaches the expiry date, they should be forced to change it at next login
3. The system should maintain a password history (last 5 passwords minimum) and prevent reuse
4. Users should receive a reminder notification a few days before their password expires (e.g., 7 days before)
5. Super Admin should be able to see a report of users with expired or soon-to-expire passwords

## Who needs it
Super Admin, all platform users

## Why it matters
Stale passwords are one of the most common security vulnerabilities. If a password is compromised and never rotated, an attacker has indefinite access. Password rotation is required by most security compliance frameworks (SOC 2, ISO 27001) and is a basic expectation for any enterprise HR platform handling sensitive employee data."""
    },

    1016: {
        "title": "Overdue invoices should trigger account restrictions after 15 days — no enforcement exists",
        "body": """## What is needed
When an organization's subscription invoice remains unpaid for more than 15 days past the due date, the platform should automatically restrict or limit access to certain features. This is a standard billing enforcement mechanism to ensure timely payments.

## Current behavior
There is no overdue invoice enforcement. Even if an invoice is past due, the organization continues to have full, unrestricted access to all platform features. The billing system does not generate invoices in the test environment, and there is no logic to act on overdue payments.

## How it should work
1. The system should track invoice due dates and monitor payment status
2. After 15 days past the due date, automatically send escalation reminders to the organization admin
3. After the grace period, restrict access to non-essential features (e.g., disable new module subscriptions, block adding new employees) while keeping core features accessible
4. Display a clear banner to org admins: "Your invoice is overdue — please make payment to restore full access"
5. Once payment is received, immediately restore full access
6. Super Admin should have the ability to manually override restrictions for specific organizations

## Who needs it
Super Admin, Organization Admin, Finance team

## Why it matters
Without payment enforcement, organizations can use the platform indefinitely without paying. This directly impacts revenue collection and cash flow. A structured escalation process encourages timely payments while being fair to customers by providing warnings and grace periods."""
    },

    1015: {
        "title": "Free tier usage limits are not enforced — free plan users can access unlimited features",
        "body": """## What is needed
Organizations on the free tier should have clear usage limits — such as maximum number of employees, restricted module access, or limited storage. The system should enforce these limits and prompt users to upgrade when they reach the ceiling.

## Current behavior
There are no free tier limits defined or enforced in the system. Free plan organizations have the same access as paid organizations. There are no modules marked as free-tier-only, and no usage caps are in place.

## How it should work
1. Define clear free tier limits (e.g., maximum 25 employees, access to core HR module only, no payroll or recruitment)
2. When a free tier organization tries to exceed a limit (e.g., adding a 26th employee), show a clear message: "You have reached the free plan limit of 25 employees — upgrade to add more"
3. Restrict access to premium modules with a clear upgrade prompt instead of silently blocking
4. Display current usage vs. limits on the organization dashboard (e.g., "15/25 employees used")
5. Super Admin should be able to configure and adjust free tier limits from the admin panel

## Who needs it
Super Admin, Organization Admin (free tier users)

## Why it matters
Without free tier limits, there is no incentive for organizations to upgrade to paid plans. This undermines the entire subscription revenue model. Clear limits with upgrade prompts drive conversions while still giving new organizations a taste of the platform's value."""
    },
}

# ============================================================
# Main execution
# ============================================================

all_issues = {}
all_issues.update(business_rules)
all_issues.update(payroll_rules)
all_issues.update(security_rules)

issue_order = [
    # Business Rules
    1018, 1019, 1022, 1023, 1056, 995,
    # Payroll Rules
    1051, 1053, 1054, 1055, 1057, 1058,
    # Platform Security
    1024, 1016, 1015,
]

print(f"Updating {len(issue_order)} issues in EmpCloud/EmpCloud...")
print(f"Delay between calls: {DELAY} seconds\n")

success = 0
failed = 0

for num in issue_order:
    info = all_issues[num]
    print(f"Updating #{num}: {info['title'][:70]}...")
    ok = patch_issue(num, info["title"], info["body"])
    if ok:
        success += 1
    else:
        failed += 1
    time.sleep(DELAY)

print(f"\nDone! {success} updated, {failed} failed.")
