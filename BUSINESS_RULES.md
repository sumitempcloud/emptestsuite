# EMP Cloud — Business Rules Test Checklist

Complete list of business rules that MUST be enforced in a production HRMS. Each rule should be tested and marked: ENFORCED / NOT ENFORCED / NOT IMPLEMENTED.

---

## 1. SUBSCRIPTION & BILLING

| # | Rule | Priority |
|---|------|----------|
| B001 | Product stops working if invoice overdue >15 days | CRITICAL |
| B002 | Cannot add employees beyond seat limit | CRITICAL |
| B003 | Module access revoked after unsubscribe | HIGH |
| B004 | Free tier modules have feature restrictions | MEDIUM |
| B005 | Subscription auto-renews at cycle end | HIGH |
| B006 | Grace period before account suspension (warning emails) | HIGH |
| B007 | Downgrade plan — excess seats should be flagged | MEDIUM |
| B008 | Cannot subscribe to same module twice | LOW |
| B009 | Billing history preserved after plan change | MEDIUM |
| B010 | Proration on mid-cycle upgrade/downgrade | MEDIUM |
| B011 | Tax (GST/VAT) correctly applied on invoices | HIGH |
| B012 | Payment failure retry logic (dunning) | HIGH |
| B013 | Refund processing on cancellation within trial | MEDIUM |
| B014 | Super Admin can manually suspend/unsuspend org | HIGH |
| B015 | Suspended org — all users see "Account suspended" message | HIGH |

## 2. LEAVE MANAGEMENT

| # | Rule | Priority |
|---|------|----------|
| L001 | Cannot apply leave exceeding balance | CRITICAL |
| L002 | Cannot apply overlapping leave dates | CRITICAL |
| L003 | Leave balance cannot go negative | CRITICAL |
| L004 | Only manager/admin can approve — not self-approve | CRITICAL |
| L005 | Manager can only approve direct reports' leave | HIGH |
| L006 | Approved leave deducts balance | CRITICAL |
| L007 | Rejected leave does NOT deduct balance | CRITICAL |
| L008 | Cancelled leave restores balance | HIGH |
| L009 | Cannot cancel already taken leave (past dates) | HIGH |
| L010 | Cannot approve already rejected leave | MEDIUM |
| L011 | Cannot reject already approved leave (need cancel flow) | MEDIUM |
| L012 | Half-day leave deducts 0.5 from balance | HIGH |
| L013 | Leave on public holiday — holiday not counted as leave day | HIGH |
| L014 | Leave spanning weekend — weekends excluded (or per policy) | HIGH |
| L015 | Maternity leave — gender eligibility check | MEDIUM |
| L016 | Paternity leave — gender eligibility check | MEDIUM |
| L017 | Probation period — restricted leave during probation | MEDIUM |
| L018 | Leave accrual — monthly balance increment per policy | HIGH |
| L019 | Carry forward — unused leave carries to next year (per policy) | HIGH |
| L020 | Leave encashment — payout for unused leave on exit | MEDIUM |
| L021 | Comp-off earned only by working on holiday/weekend | HIGH |
| L022 | Comp-off expiry — expires if not used within X days | MEDIUM |
| L023 | Annual leave reset at year start | HIGH |
| L024 | Cannot apply leave for terminated/inactive employee | HIGH |
| L025 | Back-dated leave application — restricted or requires approval | MEDIUM |

## 3. ATTENDANCE

| # | Rule | Priority |
|---|------|----------|
| A001 | Cannot clock in twice in same day | CRITICAL |
| A002 | Cannot clock out without clocking in | CRITICAL |
| A003 | Cannot clock in for future dates | HIGH |
| A004 | Cannot clock in for past dates (only regularization) | HIGH |
| A005 | Late arrival flagged if after shift start time | HIGH |
| A006 | Early departure flagged if before shift end time | MEDIUM |
| A007 | Overtime tracked if beyond shift hours | HIGH |
| A008 | Worked hours = clock_out - clock_in (minus breaks) | CRITICAL |
| A009 | Attendance on holiday — should warn or block | MEDIUM |
| A010 | Employee on approved leave — attendance shows "On Leave" | HIGH |
| A011 | Night shift (cross-midnight) — hours calculated correctly | HIGH |
| A012 | Regularization requires manager approval | HIGH |
| A013 | Cannot regularize for more than X days back | MEDIUM |
| A014 | Attendance report matches actual records | HIGH |
| A015 | Geo-fencing — clock in only from office (if configured) | MEDIUM |
| A016 | Multiple shifts — employee can only be in one shift at a time | MEDIUM |
| A017 | Absent without leave (AWOL) — auto-flagged after X days | MEDIUM |

## 4. EMPLOYEE LIFECYCLE

| # | Rule | Priority |
|---|------|----------|
| E001 | Unique email per org (no duplicate emails) | CRITICAL |
| E002 | Unique emp_code per org | CRITICAL |
| E003 | Cannot set self as reporting manager | HIGH |
| E004 | Cannot create circular reporting chain (A→B→A) | HIGH |
| E005 | Minimum age validation (18+) | HIGH |
| E006 | Date of exit cannot be before date of joining | HIGH |
| E007 | Date of birth cannot be in future | HIGH |
| E008 | Terminated employee cannot login | CRITICAL |
| E009 | Deactivated employee excluded from headcount | HIGH |
| E010 | Notice period enforcement on resignation | HIGH |
| E011 | Probation end date auto-calculated from joining date | MEDIUM |
| E012 | Cannot delete employee with pending assets/leaves/tickets | HIGH |
| E013 | Employee transfer — update department, manager, location | MEDIUM |
| E014 | Re-hire — create new record or reactivate old? | MEDIUM |
| E015 | Employee data retention after termination (for compliance) | HIGH |
| E016 | Cannot change employee's org_id (cross-org transfer) | CRITICAL |
| E017 | Invitation expires after X days | MEDIUM |
| E018 | Cannot invite already active employee | HIGH |
| E019 | Org admin cannot modify super admin's data | HIGH |
| E020 | Employee confirmation — probation to confirmed transition | MEDIUM |

## 5. PAYROLL

| # | Rule | Priority |
|---|------|----------|
| P001 | Cannot run payroll twice for same month | CRITICAL |
| P002 | Payroll includes LOP deductions for unapproved absences | CRITICAL |
| P003 | Tax calculation follows correct slab (old vs new regime) | CRITICAL |
| P004 | PF deduction = 12% of basic (or as per policy) | HIGH |
| P005 | ESI applicable only if gross < threshold | HIGH |
| P006 | Professional Tax per state rules | HIGH |
| P007 | TDS deducted monthly based on projected annual tax | HIGH |
| P008 | New joiner — pro-rated salary for partial month | HIGH |
| P009 | Exit mid-month — pro-rated salary + F&F | HIGH |
| P010 | Cannot modify payslip after payroll is locked | HIGH |
| P011 | Overtime pay added to gross | MEDIUM |
| P012 | Reimbursement claims included in payroll | MEDIUM |
| P013 | Bonus/incentive correctly added | MEDIUM |
| P014 | Loan EMI deducted from salary | MEDIUM |
| P015 | Net pay = Gross - Deductions (PF + ESI + PT + TDS + loans) | CRITICAL |
| P016 | Bank file generated with correct account details | HIGH |
| P017 | Form 16 generated at year end | HIGH |
| P018 | Payroll lock prevents any changes | HIGH |
| P019 | Salary revision — effective from a specific date | MEDIUM |
| P020 | Arrears calculation on back-dated revision | MEDIUM |

## 6. ASSETS

| # | Rule | Priority |
|---|------|----------|
| AS001 | Cannot assign same asset to two employees | CRITICAL |
| AS002 | Cannot delete asset that is currently assigned | HIGH |
| AS003 | Asset return date recorded on unassignment | HIGH |
| AS004 | Cannot assign retired/scrapped asset | HIGH |
| AS005 | Warranty expiry cannot be before purchase date | HIGH |
| AS006 | Asset value depreciation tracking | MEDIUM |
| AS007 | Asset audit trail — who had it, when | MEDIUM |
| AS008 | Exit employee — all assets must be returned (clearance check) | HIGH |
| AS009 | Serial number must be unique | HIGH |
| AS010 | Asset category cannot be deleted if assets exist in it | MEDIUM |

## 7. RECRUITMENT

| # | Rule | Priority |
|---|------|----------|
| R001 | Cannot hire more than position headcount allows | HIGH |
| R002 | Offer letter requires approval before sending | HIGH |
| R003 | Candidate cannot be in two active pipelines | HIGH |
| R004 | Cannot skip pipeline stages (Applied→Offer not allowed) | MEDIUM |
| R005 | Cannot send offer without interview completion | MEDIUM |
| R006 | Hired candidate auto-creates employee record | HIGH |
| R007 | Rejected candidate — reason mandatory | MEDIUM |
| R008 | Job posting auto-closes when positions filled | MEDIUM |
| R009 | Referral bonus tracked when referred candidate is hired | MEDIUM |
| R010 | Background check must complete before offer | MEDIUM |
| R011 | Duplicate candidate detection (same email/phone) | HIGH |

## 8. PERFORMANCE

| # | Rule | Priority |
|---|------|----------|
| PF001 | Self-assessment deadline enforcement | HIGH |
| PF002 | Manager review only after self-assessment submitted | HIGH |
| PF003 | Cannot modify ratings after calibration locked | HIGH |
| PF004 | Goal progress cannot exceed 100% | MEDIUM |
| PF005 | Review cycle cannot be closed with pending reviews | HIGH |
| PF006 | PIP duration enforcement — auto-close after period | MEDIUM |
| PF007 | 360 feedback — cannot review yourself | MEDIUM |
| PF008 | Performance rating affects salary revision (integration) | MEDIUM |
| PF009 | Goal alignment — child goals contribute to parent | MEDIUM |
| PF010 | Cannot create review cycle with end date before start date | HIGH |

## 9. EXIT MANAGEMENT

| # | Rule | Priority |
|---|------|----------|
| EX001 | Clearance must complete before F&F | CRITICAL |
| EX002 | F&F calculation: pending salary + leave encashment - recoveries | CRITICAL |
| EX003 | All assets must be returned (clearance checklist) | HIGH |
| EX004 | Exit interview should happen before last working day | MEDIUM |
| EX005 | Employee access revoked on last working day | CRITICAL |
| EX006 | Cannot re-initiate exit for already exited employee | HIGH |
| EX007 | Notice buyout calculation (salary * remaining notice days) | HIGH |
| EX008 | Knowledge transfer tasks must be completed | MEDIUM |
| EX009 | Resignation withdrawal allowed before acceptance | MEDIUM |
| EX010 | Attrition rate calculation — only voluntary exits | MEDIUM |

## 10. MULTI-TENANT ISOLATION

| # | Rule | Priority |
|---|------|----------|
| MT001 | Org A cannot see Org B's employees | CRITICAL |
| MT002 | Org A cannot modify Org B's data | CRITICAL |
| MT003 | Org A cannot access Org B's modules | CRITICAL |
| MT004 | Cross-org search returns nothing | CRITICAL |
| MT005 | API with org A token cannot access org B IDs | CRITICAL |
| MT006 | SSO token scoped to single org | HIGH |
| MT007 | Super Admin sees all orgs but with explicit context | HIGH |
| MT008 | Module data isolated per org (payroll, performance, etc.) | CRITICAL |
| MT009 | Audit log only shows current org's actions | HIGH |
| MT010 | Notifications scoped to org | HIGH |

## 11. SECURITY & COMPLIANCE

| # | Rule | Priority |
|---|------|----------|
| S001 | Password minimum strength (8+ chars, uppercase, lowercase, special) | HIGH |
| S002 | Password history — cannot reuse last X passwords | MEDIUM |
| S003 | Session timeout after X minutes of inactivity | HIGH |
| S004 | Account lockout after X failed login attempts | HIGH |
| S005 | All critical actions logged in audit trail | CRITICAL |
| S006 | Sensitive data encrypted at rest (salary, bank details, PAN) | CRITICAL |
| S007 | API rate limiting per user/org | HIGH |
| S008 | CORS — only allowed origins | HIGH |
| S009 | JWT token expiry enforced | HIGH |
| S010 | Refresh token rotation — old refresh token invalidated | HIGH |
| S011 | Password reset token — single use, expires in X minutes | HIGH |
| S012 | GDPR — employee can request data export | MEDIUM |
| S013 | GDPR — employee can request data deletion | MEDIUM |
| S014 | Data backup and recovery | HIGH |
| S015 | Role-based access — employee cannot access admin APIs | CRITICAL |

## 12. HELPDESK & SLA

| # | Rule | Priority |
|---|------|----------|
| H001 | Ticket SLA — response time tracked | HIGH |
| H002 | Ticket auto-escalation after SLA breach | HIGH |
| H003 | Cannot close ticket without resolution | MEDIUM |
| H004 | Ticket status flow: Open → In Progress → Resolved → Closed | HIGH |
| H005 | Cannot reopen a closed ticket after X days | MEDIUM |
| H006 | Priority-based SLA (Critical < High < Medium < Low) | HIGH |
| H007 | Ticket assignment — only to agents, not regular employees | MEDIUM |

## 13. LMS / TRAINING

| # | Rule | Priority |
|---|------|----------|
| LM001 | Mandatory training — employee cannot skip compliance courses | HIGH |
| LM002 | Course completion certificate auto-generated | MEDIUM |
| LM003 | Quiz pass mark enforced — cannot "complete" without passing | HIGH |
| LM004 | Training expiry — recertification required after X months | MEDIUM |
| LM005 | Course enrollment capacity limit | MEDIUM |
| LM006 | Manager can assign courses to team | MEDIUM |

## 14. WELLNESS & ENGAGEMENT

| # | Rule | Priority |
|---|------|----------|
| W001 | Survey response is anonymous (if configured) | HIGH |
| W002 | Cannot submit survey after end date | HIGH |
| W003 | Cannot submit survey twice | HIGH |
| W004 | Wellness check-in — only one per day | MEDIUM |
| W005 | Forum post — author can edit/delete own, not others | MEDIUM |
| W006 | Whistleblowing — truly anonymous (no user tracking) | CRITICAL |
| W007 | Feedback marked anonymous — identity not exposed | HIGH |

## 15. NOTIFICATIONS & COMMUNICATIONS

| # | Rule | Priority |
|---|------|----------|
| N001 | Leave application → manager notification | HIGH |
| N002 | Leave approval/rejection → employee notification | HIGH |
| N003 | New announcement → all target employees notified | HIGH |
| N004 | Ticket update → requester notified | HIGH |
| N005 | Payslip generated → employee notified | MEDIUM |
| N006 | Document uploaded for employee → employee notified | MEDIUM |
| N007 | Event created → invited employees notified | MEDIUM |
| N008 | Performance review assigned → employee notified | HIGH |
| N009 | Asset assigned → employee notified | MEDIUM |
| N010 | Password expiry warning → user notified | HIGH |

---

**Total: ~200 business rules across 15 categories**

Each should be tested and categorized as:
- **ENFORCED** — rule works correctly
- **NOT ENFORCED** — rule should exist but doesn't (BUG)
- **NOT IMPLEMENTED** — feature doesn't exist yet (FEATURE REQUEST)
- **PARTIALLY ENFORCED** — works in some scenarios but not all
