# EMP Cloud — End-to-End Test Plan

**Application:** EMP Cloud (Enterprise HRMS Platform)
**Environment:** https://test-empcloud.empcloud.com/
**Date:** 2026-03-27
**Version:** 1.0

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Scope](#2-scope)
3. [Test Environment & Prerequisites](#3-test-environment--prerequisites)
4. [Test Data Requirements](#4-test-data-requirements)
5. [Module-wise Test Scenarios](#5-module-wise-test-scenarios)
   - 5.1 Authentication & Authorization
   - 5.2 Dashboard
   - 5.3 Employee Management
   - 5.4 Attendance & Time Tracking
   - 5.5 Leave Management
   - 5.6 Payroll
   - 5.7 Recruitment / Applicant Tracking
   - 5.8 Performance Management
   - 5.9 Organization / Department Management
   - 5.10 Reports & Analytics
   - 5.11 Notifications & Alerts
   - 5.12 Settings & Configuration
   - 5.13 User Roles & Permissions
6. [Cross-Cutting Concerns](#6-cross-cutting-concerns)
7. [Exit Criteria](#7-exit-criteria)

---

## 1. Introduction

This document outlines a comprehensive end-to-end test plan for the EMP Cloud Enterprise HRMS Platform hosted at the test environment. The goal is to validate all major user workflows, data integrity, access controls, and integration points across every module.

---

## 2. Scope

### In Scope
- All functional modules accessible via the web UI
- Role-based access control (Admin, HR, Manager, Employee)
- CRUD operations across all entities
- Business rule validations
- Cross-module data flow (e.g., leave balance affecting payroll)
- API-driven behavior observed through the UI
- Browser compatibility (Chrome, Firefox, Edge)
- Responsive layout (desktop, tablet, mobile)

### Out of Scope
- Load/performance testing (separate plan)
- Penetration testing (separate plan)
- Third-party integrations not exposed in the test environment

---

## 3. Test Environment & Prerequisites

| Item | Detail |
|------|--------|
| URL | https://test-empcloud.empcloud.com/ |
| Browsers | Chrome (latest), Firefox (latest), Edge (latest) |
| Devices | Desktop (1920×1080), Tablet (768×1024), Mobile (375×812) |
| Test accounts | Admin, HR Manager, Department Manager, Employee (minimum 4) |
| Test data | Seeded employees, departments, leave policies, pay structures |
| Tools | Selenium / Playwright / Cypress, Postman (API validation) |

---

## 4. Test Data Requirements

| Data | Details |
|------|---------|
| Employees | Minimum 20 seeded across 3+ departments |
| Departments | At least 3 (e.g., Engineering, HR, Finance) |
| Leave types | Casual, Sick, Earned/Privilege, Compensatory |
| Pay structures | At least 2 (salaried, hourly) |
| Roles | Super Admin, HR Admin, Manager, Employee |
| Shift schedules | Day shift, Night shift, Flexible |
| Holidays | Public holiday calendar for current year |

---

## 5. Module-wise Test Scenarios

---

### 5.1 Authentication & Authorization

#### 5.1.1 Login

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| AUTH-001 | Valid login | Enter valid username + password → click Login | Redirect to dashboard; session cookie set | P0 |
| AUTH-002 | Invalid password | Enter valid username + wrong password → click Login | Error message displayed; no redirect | P0 |
| AUTH-003 | Invalid username | Enter non-existent username → click Login | Generic error "Invalid credentials" | P0 |
| AUTH-004 | Empty fields | Submit login form with blank fields | Inline validation errors on both fields | P1 |
| AUTH-005 | SQL injection attempt | Enter `' OR 1=1 --` in username field | Rejected; no data leak | P0 |
| AUTH-006 | XSS in login | Enter `<script>alert(1)</script>` in fields | Input sanitized; no script execution | P0 |
| AUTH-007 | Account lockout | Enter wrong password 5 consecutive times | Account locked; lockout message shown | P1 |
| AUTH-008 | Remember me | Check "Remember me" → login → close & reopen browser | Session persists | P2 |
| AUTH-009 | Case sensitivity | Login with uppercase username variant | Behavior per design (case-insensitive or error) | P2 |

#### 5.1.2 Logout

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| AUTH-010 | Normal logout | Click Logout from user menu | Redirect to login; session invalidated | P0 |
| AUTH-011 | Back button after logout | Logout → press browser Back | Login page shown; no access to protected pages | P0 |
| AUTH-012 | Session timeout | Stay idle beyond session timeout period | Auto-logout; redirect to login with message | P1 |

#### 5.1.3 Password Management

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| AUTH-013 | Forgot password | Click "Forgot Password" → enter email → submit | Reset email sent; confirmation message shown | P0 |
| AUTH-014 | Password reset link | Click link from reset email | Redirect to reset form; link is one-time use | P1 |
| AUTH-015 | Change password | Profile → Change Password → enter old + new + confirm | Password updated; forced re-login | P1 |
| AUTH-016 | Password strength | Enter weak password (e.g., "123") | Validation error with strength requirements | P1 |
| AUTH-017 | Password mismatch | New password ≠ confirm password | Inline error "Passwords do not match" | P1 |
| AUTH-018 | Expired reset link | Use reset link after expiry window | Error "Link expired"; prompted to request again | P2 |

#### 5.1.4 Multi-Factor Authentication (if applicable)

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| AUTH-019 | MFA setup | Enable MFA from profile settings | QR code / SMS setup flow completes | P1 |
| AUTH-020 | MFA login | Login → enter MFA code | Access granted after valid code | P1 |
| AUTH-021 | MFA invalid code | Login → enter wrong MFA code | Access denied; retry allowed | P1 |

---

### 5.2 Dashboard

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| DASH-001 | Dashboard loads | Login as Admin → land on dashboard | All widgets/cards render with data | P0 |
| DASH-002 | Role-specific dashboard | Login as Employee vs Admin | Different widgets/data visible per role | P0 |
| DASH-003 | Quick stats accuracy | Compare dashboard headcount with Employee list | Numbers match | P1 |
| DASH-004 | Recent activity | Perform an action → return to dashboard | Action appears in activity feed | P2 |
| DASH-005 | Navigation from dashboard | Click each widget/card link | Navigates to correct detail page | P1 |
| DASH-006 | Date range filter | Change dashboard date range | Data refreshes for selected period | P1 |
| DASH-007 | Dashboard refresh | Click refresh / pull-to-refresh | Data updates without full page reload | P2 |
| DASH-008 | Empty state | New tenant with no data | Appropriate empty states / onboarding prompts | P2 |

---

### 5.3 Employee Management

#### 5.3.1 Employee List

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| EMP-001 | View employee list | Navigate to Employees module | Paginated list of employees displayed | P0 |
| EMP-002 | Search employee | Type name in search bar | Filtered results in real-time | P0 |
| EMP-003 | Filter by department | Select department from filter dropdown | Only employees of that department shown | P1 |
| EMP-004 | Filter by status | Filter Active / Inactive / All | Correct employee subset displayed | P1 |
| EMP-005 | Sort columns | Click column header (Name, ID, Dept) | List sorts ascending/descending | P1 |
| EMP-006 | Pagination | Navigate pages (Next, Prev, page number) | Correct page loads; page indicator updates | P1 |
| EMP-007 | Export employee list | Click Export → choose CSV/Excel | File downloads with correct data | P2 |

#### 5.3.2 Add Employee

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| EMP-008 | Add new employee — happy path | Fill all required fields → Submit | Employee created; appears in list; success toast | P0 |
| EMP-009 | Required field validation | Leave mandatory fields blank → Submit | Inline errors on each required field | P0 |
| EMP-010 | Duplicate employee ID | Enter an existing employee ID → Submit | Error "Employee ID already exists" | P1 |
| EMP-011 | Duplicate email | Enter an existing email address → Submit | Error "Email already registered" | P1 |
| EMP-012 | Invalid email format | Enter "abc@" → Submit | Validation error on email field | P1 |
| EMP-013 | Invalid phone number | Enter letters in phone field → Submit | Validation error | P1 |
| EMP-014 | Date validation | Enter future date as DOB | Validation error | P1 |
| EMP-015 | Profile photo upload | Upload valid image (JPG/PNG <5MB) | Image preview shown; saved on submit | P2 |
| EMP-016 | Profile photo — invalid file | Upload a .exe or oversized file | Error with file type/size requirement | P2 |
| EMP-017 | Cancel add employee | Fill partial data → click Cancel | Confirmation prompt; no employee created | P2 |

#### 5.3.3 Edit Employee

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| EMP-018 | Edit employee details | Open employee → Edit → change fields → Save | Changes persisted; success message | P0 |
| EMP-019 | Edit — no changes | Open edit → Save without changes | No error; handled gracefully | P2 |
| EMP-020 | Edit — validation | Clear a required field → Save | Validation error | P1 |
| EMP-021 | Change department | Edit employee → change department → Save | Employee moves to new department in list | P1 |
| EMP-022 | Change reporting manager | Edit → assign new manager → Save | Org chart updated; manager sees employee | P1 |

#### 5.3.4 Deactivate / Terminate Employee

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| EMP-023 | Deactivate employee | Select employee → Deactivate → Confirm | Status changes; employee cannot login | P0 |
| EMP-024 | Reactivate employee | Select inactive employee → Reactivate | Status changes to Active; login restored | P1 |
| EMP-025 | Terminate with exit date | Set termination date + reason → Confirm | Employee record updated; access revoked on date | P1 |
| EMP-026 | Terminate — pending leaves | Terminate employee who has pending leave requests | Pending leaves cancelled/handled per policy | P2 |

#### 5.3.5 Employee Profile / Detail View

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| EMP-027 | View full profile | Click employee name from list | Profile page with all tabs (Personal, Job, Docs, etc.) | P0 |
| EMP-028 | Tab navigation | Click each tab on employee profile | Correct content loads per tab | P1 |
| EMP-029 | Document upload | Upload a document (PDF, DOCX) to employee profile | Document saved; appears in documents tab | P1 |
| EMP-030 | Document download | Click download on an uploaded document | File downloads correctly | P2 |
| EMP-031 | Document delete | Delete an uploaded document | Document removed after confirmation | P2 |
| EMP-032 | Employment history | View job history / promotions | Chronological list of position changes | P2 |

---

### 5.4 Attendance & Time Tracking

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| ATT-001 | Clock in | Employee clicks "Clock In" | Timestamp recorded; status changes to "Present" | P0 |
| ATT-002 | Clock out | Employee clicks "Clock Out" | Timestamp recorded; total hours calculated | P0 |
| ATT-003 | Duplicate clock in | Click "Clock In" when already clocked in | Error or button disabled | P1 |
| ATT-004 | View daily attendance | Admin → Attendance → select date | List of all employees with check-in/out times | P0 |
| ATT-005 | Attendance calendar view | Employee → My Attendance → Calendar | Monthly view with color-coded days (present, absent, leave, holiday) | P1 |
| ATT-006 | Mark attendance manually | Admin → select employee → mark attendance | Attendance record created with manual flag | P1 |
| ATT-007 | Overtime calculation | Employee works beyond shift hours | OT hours calculated and displayed | P1 |
| ATT-008 | Late arrival flag | Employee clocks in after shift start time | "Late" flag on attendance record | P1 |
| ATT-009 | Early departure flag | Employee clocks out before shift end | "Early departure" flag recorded | P2 |
| ATT-010 | Attendance report | Generate monthly attendance report | Report shows all days with accurate totals | P1 |
| ATT-011 | Attendance regularization | Employee requests correction for missed punch | Request submitted → Manager approves → record updated | P1 |
| ATT-012 | Bulk attendance upload | Admin uploads CSV of attendance records | Records imported; errors reported for invalid rows | P2 |

---

### 5.5 Leave Management

#### 5.5.1 Leave Application

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| LV-001 | Apply for leave — happy path | Select type, dates, reason → Submit | Leave request created; status "Pending" | P0 |
| LV-002 | Apply — insufficient balance | Request more days than available balance | Error "Insufficient leave balance" | P0 |
| LV-003 | Apply — past date | Select a past date as start date | Behavior per policy (allowed or blocked) | P1 |
| LV-004 | Apply — overlapping dates | Request leave for dates with existing request | Error "Overlapping leave request exists" | P1 |
| LV-005 | Apply — half day | Select "Half Day" option | 0.5 days deducted from balance on approval | P1 |
| LV-006 | Apply — with attachment | Attach medical certificate → Submit | File uploaded and linked to request | P2 |
| LV-007 | Cancel pending leave | Employee cancels own pending request | Status changes to "Cancelled"; balance restored | P1 |
| LV-008 | Cancel approved leave | Employee requests cancellation of approved leave | Cancellation request sent to manager | P1 |

#### 5.5.2 Leave Approval

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| LV-009 | Approve leave | Manager opens pending request → Approve | Status changes to "Approved"; balance deducted | P0 |
| LV-010 | Reject leave | Manager opens pending request → Reject with reason | Status "Rejected"; balance unchanged | P0 |
| LV-011 | Bulk approve | Manager selects multiple requests → Approve All | All selected requests approved | P2 |
| LV-012 | Approval notification | Employee submits leave | Manager receives notification (in-app + email) | P1 |
| LV-013 | Approval outcome notification | Manager approves/rejects | Employee receives notification with status | P1 |

#### 5.5.3 Leave Balance & Policy

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| LV-014 | View leave balance | Employee → My Leaves → Balance | Correct balance per leave type | P0 |
| LV-015 | Leave accrual | After monthly accrual cycle runs | Balance incremented per policy | P1 |
| LV-016 | Leave carry-forward | Year-end → verify carry-forward logic | Balances carry/expire per policy settings | P2 |
| LV-017 | Leave policy assignment | Admin assigns policy to department | All employees in department get policy | P1 |
| LV-018 | Holiday on leave dates | Apply leave spanning a public holiday | Holiday not counted as leave day | P1 |
| LV-019 | Weekend on leave dates | Apply leave spanning a weekend | Weekends excluded (or included per policy) | P1 |

---

### 5.6 Payroll

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| PAY-001 | Run payroll | Admin → Payroll → select month → Run | Payroll processed for all active employees | P0 |
| PAY-002 | Salary breakdown | View employee payslip | Gross, deductions, net pay correctly calculated | P0 |
| PAY-003 | Tax calculation | Verify tax deductions on payslip | Tax computed per applicable rules | P0 |
| PAY-004 | Leave deduction | Employee with LOP (Loss of Pay) days | Salary deducted proportionally | P1 |
| PAY-005 | Overtime pay | Employee with approved OT hours | OT amount added to gross pay | P1 |
| PAY-006 | Bonus/Allowance | Add one-time bonus to employee | Reflected in that month's payslip | P1 |
| PAY-007 | Payslip download | Employee → Payslips → Download PDF | PDF generated with correct data | P1 |
| PAY-008 | Payroll report | Admin → generate payroll summary report | Totals match sum of individual payslips | P1 |
| PAY-009 | Re-run payroll | Admin re-runs payroll for a processed month | Previous run replaced; changes reflected | P2 |
| PAY-010 | New joiner mid-month | Employee joined on 15th → run payroll | Pro-rated salary calculated | P1 |
| PAY-011 | Terminated employee | Employee exited mid-month → run payroll | Final settlement calculated (pro-rated + dues) | P1 |
| PAY-012 | Payroll lock | Lock payroll after processing | No further edits allowed for that period | P2 |
| PAY-013 | Statutory compliance | Verify PF/ESI/PT deductions (if applicable) | Amounts match statutory rules | P1 |

---

### 5.7 Recruitment / Applicant Tracking

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| REC-001 | Create job posting | HR → Recruitment → New Job → fill details → Publish | Job appears in open positions | P0 |
| REC-002 | Edit job posting | Edit an existing open position | Changes saved and reflected | P1 |
| REC-003 | Close job posting | Close/archive a position | Position no longer visible to applicants | P1 |
| REC-004 | Add candidate | Add candidate manually to a job | Candidate appears in pipeline | P0 |
| REC-005 | Upload resume | Upload resume (PDF/DOC) for candidate | File attached to candidate profile | P1 |
| REC-006 | Move candidate through stages | Drag/move candidate: Applied → Screening → Interview → Offer | Stage updates; history tracked | P0 |
| REC-007 | Schedule interview | Select candidate → schedule interview with date/time/panel | Interview event created; notifications sent | P1 |
| REC-008 | Interview feedback | Interviewer submits feedback/scorecard | Feedback saved; visible to HR | P1 |
| REC-009 | Reject candidate | Reject candidate with reason | Status changes; rejection email sent (if configured) | P1 |
| REC-010 | Generate offer letter | Select candidate → Generate Offer | Offer letter generated from template | P2 |
| REC-011 | Convert to employee | Accepted candidate → Convert to Employee | Employee record created with candidate data | P1 |

---

### 5.8 Performance Management

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| PERF-001 | Create appraisal cycle | Admin → Performance → New Cycle → set dates | Cycle created; visible to participants | P0 |
| PERF-002 | Self-assessment | Employee fills self-assessment form → Submit | Submission saved; status moves to "Manager Review" | P0 |
| PERF-003 | Manager review | Manager reviews + rates employee → Submit | Rating saved; visible in performance record | P0 |
| PERF-004 | Goal setting | Employee/Manager creates goals for cycle | Goals saved and linked to appraisal | P1 |
| PERF-005 | Goal progress update | Employee updates goal completion percentage | Progress reflected in performance dashboard | P1 |
| PERF-006 | 360° feedback (if applicable) | Peers/subordinates submit feedback | All feedback aggregated in review | P2 |
| PERF-007 | Performance rating history | View employee's historical ratings | All past cycles and ratings displayed | P2 |
| PERF-008 | Appraisal reminder | Cycle deadline approaches | Email/notification sent to incomplete participants | P2 |
| PERF-009 | Final rating calibration | HR adjusts final ratings | Adjusted ratings saved; audit trail maintained | P2 |

---

### 5.9 Organization / Department Management

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| ORG-001 | View org chart | Navigate to Organization Chart | Hierarchical view of departments and reporting lines | P1 |
| ORG-002 | Create department | Admin → Add Department → fill details → Save | Department appears in list and dropdowns | P0 |
| ORG-003 | Edit department | Edit department name/head → Save | Changes reflected across system | P1 |
| ORG-004 | Delete department | Delete department with no employees | Department removed | P1 |
| ORG-005 | Delete department — with employees | Attempt to delete department that has employees | Blocked with error or reassignment prompt | P1 |
| ORG-006 | Create designation/role | Add new designation (e.g., "Senior Engineer") | Available in employee forms | P1 |
| ORG-007 | Branch/location management | Add/edit office locations | Locations available in employee assignment | P2 |

---

### 5.10 Reports & Analytics

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| RPT-001 | Headcount report | Generate headcount by department | Numbers match employee list counts | P1 |
| RPT-002 | Attendance report | Generate monthly attendance summary | Data matches attendance records | P1 |
| RPT-003 | Leave report | Generate leave utilization report | Balances and usage match leave records | P1 |
| RPT-004 | Payroll report | Generate payroll cost report | Totals match processed payroll | P1 |
| RPT-005 | Turnover report | Generate attrition/turnover report | Terminated employees correctly counted | P2 |
| RPT-006 | Custom date range | Apply date range filter on any report | Data filtered to selected range | P1 |
| RPT-007 | Export report | Export any report to CSV/Excel/PDF | File downloads with correct data and formatting | P1 |
| RPT-008 | Report access control | Employee tries to access admin-level report | Access denied / report not visible | P1 |
| RPT-009 | Dashboard charts | Verify chart data matches tabular report data | Visual and tabular data consistent | P2 |

---

### 5.11 Notifications & Alerts

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| NOTIF-001 | In-app notification | Trigger an event (e.g., leave approved) | Bell icon shows notification; count increments | P1 |
| NOTIF-002 | Email notification | Trigger an event with email enabled | Email received with correct content | P1 |
| NOTIF-003 | Mark as read | Click a notification | Marked as read; count decrements | P2 |
| NOTIF-004 | Notification link | Click notification | Navigates to relevant page (e.g., leave detail) | P1 |
| NOTIF-005 | Mark all as read | Click "Mark all as read" | All notifications marked read; count resets to 0 | P2 |
| NOTIF-006 | Notification preferences | Disable a notification type in settings | That notification type no longer sent | P2 |

---

### 5.12 Settings & Configuration

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| SET-001 | Company profile | Admin → Settings → update company info → Save | Changes persisted | P1 |
| SET-002 | Leave policy config | Create/edit leave policy (types, limits, accrual) | Policy saved; applied to assigned groups | P0 |
| SET-003 | Shift configuration | Create/edit shift timings | Shift available for employee assignment | P1 |
| SET-004 | Holiday calendar | Add/edit/delete public holidays | Calendar updated; affects leave calculations | P1 |
| SET-005 | Email template config | Edit notification email templates | Updated template used in future emails | P2 |
| SET-006 | Payroll settings | Configure pay components, tax rules | Settings applied in next payroll run | P1 |
| SET-007 | Workflow config | Configure approval workflows (leave, expense) | Workflow followed when requests are submitted | P1 |

---

### 5.13 User Roles & Permissions

| # | Test Case | Steps | Expected Result | Priority |
|---|-----------|-------|-----------------|----------|
| ROLE-001 | Admin full access | Login as Admin → navigate all modules | All modules and actions accessible | P0 |
| ROLE-002 | HR limited access | Login as HR → check module access | Access to HR modules; no system admin settings | P0 |
| ROLE-003 | Manager access | Login as Manager → check access | Own team data only; approval actions available | P0 |
| ROLE-004 | Employee access | Login as Employee → check access | Self-service only (own profile, leaves, payslips) | P0 |
| ROLE-005 | URL direct access | Employee manually types admin URL | 403 Forbidden or redirect to dashboard | P0 |
| ROLE-006 | Create custom role | Admin → create role with specific permissions | Role available for user assignment | P1 |
| ROLE-007 | Modify role permissions | Edit an existing role's permissions | Changes take effect on next login | P1 |
| ROLE-008 | Assign role to user | Assign a role to an employee | Employee sees modules per role | P1 |
| ROLE-009 | Remove role | Remove a role from a user | Access revoked immediately/on next login | P1 |

---

## 6. Cross-Cutting Concerns

### 6.1 UI / UX

| # | Test Case | Priority |
|---|-----------|----------|
| UI-001 | All pages render without console errors | P1 |
| UI-002 | Responsive layout at 1920px, 1024px, 768px, 375px widths | P1 |
| UI-003 | Consistent branding (logo, colors, fonts) across all pages | P2 |
| UI-004 | Loading indicators shown during async operations | P2 |
| UI-005 | Breadcrumb navigation works correctly | P2 |
| UI-006 | Form field tab order is logical | P2 |
| UI-007 | Toast/success/error messages appear and auto-dismiss | P1 |
| UI-008 | Modals/dialogs can be closed via X, Escape, and outside click | P2 |
| UI-009 | Tables handle 0 rows, 1 row, and large datasets gracefully | P1 |
| UI-010 | Date pickers respect locale and format | P2 |

### 6.2 Data Integrity & Cross-Module Flows

| # | Test Case | Priority |
|---|-----------|----------|
| DATA-001 | Employee added → appears in attendance, leave, payroll modules | P0 |
| DATA-002 | Employee deactivated → excluded from payroll run | P0 |
| DATA-003 | Leave approved → balance updated → reflected in payroll if LOP | P0 |
| DATA-004 | Attendance data → feeds into payroll OT/deduction calculations | P1 |
| DATA-005 | Department deleted → employees reassigned or blocked | P1 |
| DATA-006 | Candidate converted to employee → no duplicate data; all fields carry over | P1 |
| DATA-007 | Payroll processed → payslip available for employee download | P1 |

### 6.3 Security

| # | Test Case | Priority |
|---|-----------|----------|
| SEC-001 | All pages served over HTTPS | P0 |
| SEC-002 | Session tokens are HttpOnly and Secure | P0 |
| SEC-003 | CSRF protection on all state-changing forms | P0 |
| SEC-004 | API returns 401 for unauthenticated requests | P0 |
| SEC-005 | API returns 403 for unauthorized role accessing protected endpoint | P0 |
| SEC-006 | Sensitive data (salary, SSN) masked in UI by default | P1 |
| SEC-007 | Password stored as hash (verify via DB or API behavior) | P1 |
| SEC-008 | File upload rejects executable files (.exe, .sh, .bat) | P1 |
| SEC-009 | No sensitive data in URL parameters | P1 |
| SEC-010 | Rate limiting on login and API endpoints | P2 |

### 6.4 Browser Compatibility

| # | Test Case | Priority |
|---|-----------|----------|
| COMPAT-001 | Full test pass on Chrome (latest) | P0 |
| COMPAT-002 | Full test pass on Firefox (latest) | P1 |
| COMPAT-003 | Full test pass on Edge (latest) | P1 |
| COMPAT-004 | Full test pass on Safari (latest — if Mac available) | P2 |

### 6.5 Accessibility

| # | Test Case | Priority |
|---|-----------|----------|
| A11Y-001 | All images have alt text | P2 |
| A11Y-002 | Form labels associated with inputs | P2 |
| A11Y-003 | Keyboard navigation (Tab, Enter, Escape) works throughout | P2 |
| A11Y-004 | Color contrast meets WCAG AA standard | P2 |
| A11Y-005 | Screen reader reads page content meaningfully | P2 |

---

## 7. Exit Criteria

| Criteria | Threshold |
|----------|-----------|
| All P0 test cases | 100% pass |
| All P1 test cases | ≥ 95% pass |
| All P2 test cases | ≥ 85% pass |
| No open Severity 1 (Blocker) bugs | 0 |
| No open Severity 2 (Critical) bugs | 0 |
| Open Severity 3 (Major) bugs | ≤ 3, with workarounds documented |
| Test coverage of identified modules | 100% of modules exercised |
| Cross-module data flow tests | All pass |
| Security tests (P0) | 100% pass |

---

**Total Test Cases: ~150+**

> **Note:** This test plan is based on standard HRMS platform modules inferred from the EMP Cloud branding. The actual modules and features may differ. This plan should be reviewed and tailored after a walkthrough of the live application to add, remove, or modify scenarios based on the actual feature set.
