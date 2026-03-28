"""
Fix GitHub issues #1062-#1078: Rewrite bad titles with internal rule numbers
and replace boilerplate bodies with clear, plain English descriptions.
"""

import json
import time
import urllib.request

GITHUB_TOKEN = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
API = f"https://api.github.com/repos/{REPO}/issues"

# --- Rewritten issues ---
ISSUES = {
    1062: {
        "title": "Payroll module needs a salary creation and update endpoint",
        "body": """## What is needed
The payroll system should expose an API endpoint (and corresponding UI form) that lets HR create or update an employee's salary record.

## Current behavior
There is no salary creation or update API endpoint available. HR cannot programmatically set up salary records, and the system cannot validate salary values at the point of entry.

## How it should work
1. HR navigates to the Payroll module and selects an employee
2. A form or API allows entering the salary amount and components
3. The system validates that the salary is a positive number (not zero, not negative)
4. The record is saved and reflected in the employee's payroll profile

## Who needs it
HR Administrators and Payroll teams who set up compensation for new and existing employees.

## Why it matters
Without a salary creation endpoint, there is no way to onboard employees into payroll or enforce basic validation like preventing zero or negative salary values."""
    },
    1063: {
        "title": "Salary structure template should validate that all components add up to total CTC",
        "body": """## What is needed
When an HR admin defines a salary structure template (Basic, HRA, Special Allowance, etc.), the system must verify that all individual components add up exactly to the employee's total Cost to Company (CTC).

## Current behavior
There is no salary structure template with editable components available for testing. The system does not appear to enforce that component totals match the declared CTC.

## How it should work
1. HR creates or edits a salary structure template
2. They enter amounts or percentages for each component (Basic, HRA, Conveyance, etc.)
3. The system sums all components and compares to the CTC
4. If they do not match, a clear error message is shown before saving
5. The template is only saved when the sum matches the CTC exactly

## Who needs it
HR Administrators and Payroll managers who design compensation structures.

## Why it matters
If salary components do not add up to CTC, employees may be underpaid or overpaid, and statutory deductions will be calculated on wrong base amounts. This causes compliance problems and payroll disputes."""
    },
    1064: {
        "title": "Provident Fund deduction should only apply when basic salary is within the statutory threshold",
        "body": """## What is needed
The payroll system must enforce the Provident Fund (PF) eligibility rule: PF is mandatory only when an employee's basic salary is at or below Rs 15,000 per month. Employees earning above this threshold should have PF applied only if they explicitly opt in.

## Current behavior
No salary or payroll records with a PF breakdown were found. It is unclear whether the system checks the basic salary threshold before applying PF deductions.

## How it should work
1. When payroll is processed, the system checks each employee's basic salary
2. If basic salary is Rs 15,000/month or less, PF is deducted automatically (12% employee + 12% employer)
3. If basic salary exceeds Rs 15,000/month, PF is only deducted if the employee has opted in
4. The PF breakdown should be visible in the salary slip

## Who needs it
Payroll teams, Finance, and Compliance officers.

## Why it matters
Incorrect PF application violates the Employees' Provident Fund Act. Deducting PF from ineligible employees without consent leads to legal issues, and failing to deduct for eligible employees results in compliance penalties."""
    },
    1065: {
        "title": "ESI deduction should only apply when gross salary is within the statutory threshold",
        "body": """## What is needed
The payroll system must enforce the Employee State Insurance (ESI) eligibility rule: ESI applies only when an employee's gross salary is at or below Rs 21,000 per month.

## Current behavior
No salary data with ESI breakdown is available. The system does not appear to check the gross salary threshold before applying ESI deductions.

## How it should work
1. During payroll processing, the system checks each employee's gross salary
2. If gross salary is Rs 21,000/month or less, ESI is deducted automatically (employee 0.75% + employer 3.25%)
3. If gross salary exceeds Rs 21,000/month, ESI must not be deducted
4. The ESI status and amounts should be visible in the salary slip

## Who needs it
Payroll teams, Finance, and Compliance officers.

## Why it matters
Applying ESI to employees who earn above the threshold is incorrect and causes unnecessary deductions from their salary. Failing to apply it to eligible employees creates compliance risk under the ESI Act."""
    },
    1066: {
        "title": "Shift management module needed to prevent overlapping shift assignments",
        "body": """## What is needed
The system needs a shift management module where HR can define shifts and assign employees to them. The system must prevent assigning an employee to two shifts that overlap in time.

## Current behavior
No shift assignment functionality (API or UI) was found in the system. There is no way to create shifts or assign employees to them.

## How it should work
1. HR defines shifts with start time, end time, and name (e.g., Morning 6AM-2PM, General 9AM-6PM)
2. HR assigns employees to shifts
3. When assigning, the system checks if the employee already has a shift during that time window
4. If the new shift overlaps with an existing one, the system blocks the assignment and shows an error
5. Shift schedules are visible on a calendar or roster view

## Who needs it
HR Administrators, Shift Supervisors, and Operations Managers.

## Why it matters
Without shift management, attendance tracking has no reference for expected work hours. Overlapping shifts cause confusion in attendance records, incorrect overtime calculations, and payroll errors."""
    },
    1067: {
        "title": "Overtime should only be counted after an employee completes their full regular shift",
        "body": """## What is needed
The system should only count overtime hours after an employee has completed their full regular shift hours for the day. Working extra time on a day where the regular shift was not completed should not count as overtime.

## Current behavior
No overtime data was found in the API. The system does not appear to track or calculate overtime at all.

## How it should work
1. An employee's regular shift is defined (e.g., 8 hours)
2. The system tracks total hours worked from attendance check-in/check-out
3. Only hours worked beyond the regular shift count as overtime
4. If an employee works 7 hours on an 8-hour shift, no overtime is recorded even if they came early
5. Overtime hours and regular hours are shown separately in attendance and payroll

## Who needs it
HR Managers, Payroll teams, and Employees.

## Why it matters
Counting overtime before a full shift is completed inflates payroll costs and is non-compliant with the Factories Act, which defines overtime as work beyond normal working hours."""
    },
    1068: {
        "title": "Overtime hours should be auto-calculated from attendance when employees work beyond their shift",
        "body": """## What is needed
When an employee clocks out after their shift end time, the system should automatically calculate the overtime hours by comparing actual work hours against the assigned shift hours.

## Current behavior
Attendance records capture check-in and check-out times, but overtime is not automatically calculated from the difference between actual hours worked and shift hours.

## How it should work
1. Employee clocks in and clocks out through the attendance system
2. The system compares actual hours worked against the assigned shift hours
3. Any hours beyond the shift duration are automatically recorded as overtime
4. Overtime appears in the attendance summary, employee dashboard, and payroll reports
5. Overtime pay is calculated at 2x the regular hourly rate (per Factories Act)

## Who needs it
HR Managers, Payroll teams, and Employees who work extra hours.

## Why it matters
Without automatic overtime calculation, HR must manually compute overtime for every employee each pay period. This is error-prone, delays payroll processing, and can lead to underpayment of employees who worked extra hours."""
    },
    1069: {
        "title": "Salary creation API endpoint is missing from the Payroll module",
        "body": """## What is needed
The Payroll module must provide an API endpoint for creating new salary records for employees. This is a foundational requirement for all payroll operations.

## Current behavior
No salary creation API endpoint exists. Salary records cannot be created programmatically, which blocks testing and automation of payroll workflows.

## How it should work
1. HR or an automated onboarding process calls the salary creation endpoint with employee ID and salary details
2. The system validates the input (positive amounts, required fields present)
3. A salary record is created and linked to the employee
4. The record becomes available for payroll processing, tax calculations, and reporting

## Who needs it
HR Administrators, Payroll teams, and system integrators who build onboarding automations.

## Why it matters
Without a salary creation endpoint, new employees cannot be set up in payroll. This blocks the entire compensation workflow from hiring through monthly salary processing."""
    },
    1070: {
        "title": "CTC breakdown calculation is not available in payroll records",
        "body": """## What is needed
The payroll system should calculate and display a full CTC (Cost to Company) breakdown showing how CTC is composed of Gross Salary plus employer contributions (Employer PF, Employer ESI, and Gratuity).

## Current behavior
No CTC breakdown data was found in the payroll records. The system does not show how CTC splits into its constituent parts.

## How it should work
1. When a salary record exists, the system calculates: CTC = Gross Salary + Employer PF + Employer ESI + Gratuity
2. Each component amount is stored and displayed in the employee's compensation details
3. Changes to any component automatically recalculate the CTC
4. The breakdown is visible in salary slips, offer letters, and HR reports

## Who needs it
HR Administrators, Finance teams, and Employees reviewing their compensation.

## Why it matters
Without a proper CTC breakdown, employees do not understand their full compensation, HR cannot generate accurate offer letters, and finance teams cannot forecast labor costs correctly."""
    },
    1071: {
        "title": "Complete salary structure with all components is not available for employees",
        "body": """## What is needed
Each employee should have a complete salary structure showing all individual components (Basic, HRA, Conveyance, Special Allowance, etc.) that together make up their CTC.

## Current behavior
No complete salary structure with individual components was found. Employee salary records do not break down into the standard component-level detail.

## How it should work
1. HR defines a salary structure template with components and their percentages or fixed amounts
2. When an employee is assigned a CTC, the system auto-calculates each component based on the template
3. The full structure is viewable by HR and the employee
4. All components must sum exactly to the CTC
5. Changes to the template or CTC recalculate all components

## Who needs it
HR Administrators, Payroll teams, and Employees.

## Why it matters
Without a component-level salary structure, statutory deductions (PF, ESI, Professional Tax) cannot be calculated correctly because they depend on specific components like Basic and Gross salary. This leads to compliance violations and inaccurate payslips."""
    },
    1072: {
        "title": "Salary records lack basic and PF breakdown needed for statutory compliance",
        "body": """## What is needed
Salary records must include a breakdown showing the Basic salary amount and the corresponding Provident Fund (PF) deduction, so the system can verify PF is being applied correctly based on the statutory threshold.

## Current behavior
No salary data with Basic salary and PF amounts was found. The system does not expose these values for verification or reporting.

## How it should work
1. Each salary record includes the Basic salary as a separate line item
2. PF contribution is calculated based on the Basic amount (12% employee, 12% employer)
3. PF is mandatory when Basic is at or below Rs 15,000/month; optional above that threshold
4. The Basic and PF amounts are visible in salary slips and payroll reports

## Who needs it
Payroll teams, Compliance officers, and Auditors.

## Why it matters
PF compliance is a legal requirement. Without visible Basic and PF breakdowns, there is no way to verify that PF rules are being followed, which creates audit risk and potential penalties from the Employees' Provident Fund Organisation."""
    },
    1073: {
        "title": "Gross salary data not available for verifying ESI eligibility threshold",
        "body": """## What is needed
The payroll system must expose gross salary data so the system (and auditors) can verify whether ESI deductions are being applied correctly based on the Rs 21,000/month threshold.

## Current behavior
No gross salary data is available for checking against the ESI threshold. It is not possible to verify whether ESI is correctly applied or skipped.

## How it should work
1. Each employee's payroll record shows their gross salary
2. The system automatically checks if gross salary is at or below Rs 21,000/month
3. ESI is applied only to eligible employees; ineligible employees are excluded
4. The ESI eligibility status and deduction amounts are visible in salary slips

## Who needs it
Payroll teams, Compliance officers, and Auditors.

## Why it matters
Without gross salary visibility, there is no way to verify ESI compliance. Incorrect ESI application leads to penalties under the ESI Act and causes incorrect take-home pay for employees."""
    },
    1074: {
        "title": "Shift management module is missing from the system",
        "body": """## What is needed
The system needs a dedicated shift management module where HR can create, edit, and assign work shifts to employees.

## Current behavior
No shift management functionality was found anywhere in the system — neither in the API nor in the UI. There is no way to define shifts or assign employees to them.

## How it should work
1. HR creates shifts with a name, start time, and end time (e.g., "Morning Shift" 6:00 AM - 2:00 PM)
2. Shifts can be assigned to individual employees or groups
3. The system prevents overlapping shift assignments for the same employee
4. Shift data feeds into attendance tracking and overtime calculations
5. A shift roster or calendar view shows the schedule

## Who needs it
HR Administrators, Operations Managers, and Shift Supervisors.

## Why it matters
Without shift management, attendance has no baseline for expected hours. Overtime cannot be calculated because there is no way to know when an employee's regular shift ends. This also prevents proper compliance with labor regulations around maximum work hours."""
    },
    1075: {
        "title": "Overtime tracking is completely missing from the payroll system",
        "body": """## What is needed
The payroll system must track overtime hours worked by employees and include overtime pay in salary calculations.

## Current behavior
No overtime data was found in any API endpoint. The system does not record, calculate, or report on overtime hours.

## How it should work
1. Overtime hours are either entered manually by a supervisor or auto-calculated from attendance
2. Overtime is only counted after an employee has completed their regular shift hours
3. Overtime pay is calculated at the statutory rate (2x regular hourly rate per the Factories Act)
4. Overtime totals appear in attendance reports and are automatically included in payroll
5. Monthly and annual overtime summaries are available for compliance reporting

## Who needs it
HR Managers, Payroll teams, Operations Managers, and Employees.

## Why it matters
Many employees regularly work beyond their shift hours. Without overtime tracking, they are not compensated fairly, the company risks labor law violations, and payroll figures are inaccurate."""
    },
    1076: {
        "title": "Overtime hours should be auto-calculated from attendance when employee works beyond shift",
        "body": """## What is needed
When an employee works beyond their assigned shift hours (for example, their shift is 9 AM to 6 PM but they clock out at 8 PM), the system should automatically calculate 2 hours of overtime.

## Current behavior
Attendance records capture check-in and check-out times, but overtime is not automatically calculated by comparing actual hours against shift hours.

## How it should work
1. Employee clocks in and clocks out
2. System compares actual worked hours against the assigned shift duration
3. Extra time beyond the shift is recorded as overtime
4. Overtime shows in attendance reports, the employee dashboard, and payroll
5. Overtime pay rate is 2x the regular hourly rate (per Factories Act)

## Who needs it
HR Managers, Payroll teams, and Employees.

## Why it matters
Without automatic overtime calculation, HR staff must manually track and compute overtime for every employee each pay period. This is slow, error-prone, and often results in employees not being paid correctly for extra hours worked."""
    },
    1077: {
        "title": "Salary creation endpoint missing — cannot set up new employee compensation",
        "body": """## What is needed
The Payroll module needs a working API endpoint (and UI form) for creating salary records when onboarding new employees or updating compensation.

## Current behavior
No salary creation API endpoint was found. New employees cannot have their salary set up through the system.

## How it should work
1. During onboarding or compensation revision, HR enters salary details for an employee
2. The system validates the salary (must be a positive number, required fields filled in)
3. A salary record is created and linked to the employee's profile
4. The salary is immediately available for payroll processing and reporting

## Who needs it
HR Administrators and Payroll teams responsible for onboarding and compensation management.

## Why it matters
Salary creation is the starting point for all payroll operations. Without it, new hires cannot be paid, tax deductions cannot be calculated, and the entire payroll workflow is blocked."""
    },
    1078: {
        "title": "Payroll module does not validate against zero or negative salary values",
        "body": """## What is needed
When salary data is entered or updated, the system must reject zero and negative values. The existing salary data (for example, CTC of Rs 200,000 and Basic of Rs 80,000) is stored but there is no validation endpoint to test whether invalid values are properly blocked.

## Current behavior
Salary records exist with valid positive values, but there is no write API to test whether the system would accept a zero or negative salary. The validation rule cannot be verified.

## How it should work
1. When HR creates or updates a salary record, they enter the salary amount
2. If the value is zero or negative, the system immediately shows a validation error and blocks the save
3. Only positive salary values are accepted
4. This validation applies to all salary components (Basic, HRA, CTC, etc.), not just the total

## Who needs it
HR Administrators and Payroll teams entering compensation data.

## Why it matters
A zero or negative salary would corrupt payroll calculations, produce incorrect tax deductions, and generate invalid salary slips. Preventing bad data at the point of entry avoids cascading errors throughout the payroll system."""
    },
}

def update_issue(issue_num, title, body):
    """Update a GitHub issue's title and body."""
    url = f"{API}/{issue_num}"
    data = json.dumps({"title": title, "body": body}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PATCH")
    req.add_header("Authorization", f"token {GITHUB_TOKEN}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            return resp.status, result.get("title", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def main():
    total = len(ISSUES)
    success = 0
    failed = 0

    for i, (issue_num, content) in enumerate(sorted(ISSUES.items())):
        print(f"\n[{i+1}/{total}] Updating issue #{issue_num}...")
        print(f"  New title: {content['title']}")

        status, info = update_issue(issue_num, content["title"], content["body"])

        if status in (200, 201):
            print(f"  OK (HTTP {status})")
            success += 1
        else:
            print(f"  FAILED (HTTP {status}): {info}")
            failed += 1

        # 5 second delay between API calls as requested
        if i < total - 1:
            print("  Waiting 5 seconds...")
            time.sleep(5)

    print(f"\n{'='*60}")
    print(f"Done. {success} updated, {failed} failed out of {total} issues.")


if __name__ == "__main__":
    main()
