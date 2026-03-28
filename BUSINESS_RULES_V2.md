# EMP Cloud — Business Rules V2 (Advanced & Edge Cases)

Additional business rules beyond the 200 in BUSINESS_RULES.md. These focus on real-world edge cases, compliance, cross-module interactions, and scenarios a QA team often misses.

---

## 16. SALARY & COMPENSATION

| # | Rule | Priority |
|---|------|----------|
| SC001 | Salary cannot be zero or negative | CRITICAL |
| SC002 | Basic pay must be >= minimum wage (as per state law) | HIGH |
| SC003 | HRA cannot exceed 50% of basic (tax rule) | HIGH |
| SC004 | Salary revision effective date cannot be in the past without admin override | MEDIUM |
| SC005 | Arrears auto-calculated on back-dated salary revision | HIGH |
| SC006 | CTC = Gross + Employer PF + Employer ESI + Gratuity | HIGH |
| SC007 | Salary structure template — all components must sum to CTC | CRITICAL |
| SC008 | Cannot assign salary structure to terminated employee | HIGH |
| SC009 | Salary slip shows correct month/year — no future payslips | HIGH |
| SC010 | Increment % cannot exceed company max (e.g., 100%) | MEDIUM |

## 17. TAX & STATUTORY COMPLIANCE

| # | Rule | Priority |
|---|------|----------|
| TX001 | PF applies only if basic <= Rs 15,000/month (or opt-in above) | CRITICAL |
| TX002 | ESI applies only if gross <= Rs 21,000/month | CRITICAL |
| TX003 | Professional Tax per state slab (varies by state) | HIGH |
| TX004 | TDS computed on projected annual income, not monthly | HIGH |
| TX005 | New regime vs old regime — employee choice respected | HIGH |
| TX006 | 80C deductions capped at Rs 1.5L per year | HIGH |
| TX007 | HRA exemption calculation correct (rent - 10% basic) | HIGH |
| TX008 | Standard deduction of Rs 50,000 applied (new regime) | MEDIUM |
| TX009 | Form 16 generated correctly at year end | HIGH |
| TX010 | Investment declarations locked after verification deadline | MEDIUM |
| TX011 | Cannot declare more than actual investment proof | MEDIUM |
| TX012 | Tax computed correctly on bonus/arrears (separate slab) | HIGH |

## 18. SHIFT & SCHEDULING

| # | Rule | Priority |
|---|------|----------|
| SH001 | Employee cannot be assigned to two overlapping shifts | CRITICAL |
| SH002 | Minimum rest period between shifts (11 hours per labor law) | HIGH |
| SH003 | Night shift — different pay rate if applicable | MEDIUM |
| SH004 | Shift swap — requires manager approval | MEDIUM |
| SH005 | Weekly off — at least 1 day off per 7 days | HIGH |
| SH006 | Cannot schedule shift on public holiday (unless essential) | MEDIUM |
| SH007 | Shift start/end time — cannot be same | LOW |
| SH008 | Rotating shift — auto-assignment per schedule | MEDIUM |
| SH009 | On-call duty — tracked separately from regular shift | MEDIUM |
| SH010 | Maximum working hours per week (48 hours per Shops Act) | HIGH |

## 19. OVERTIME & COMPENSATION

| # | Rule | Priority |
|---|------|----------|
| OT001 | OT only after completing regular shift hours | HIGH |
| OT002 | OT rate = 2x regular rate (as per Factories Act) | HIGH |
| OT003 | OT requires pre-approval from manager | MEDIUM |
| OT004 | Maximum OT hours per month capped | MEDIUM |
| OT005 | OT on holidays = 3x rate (or per policy) | MEDIUM |
| OT006 | Comp-off alternative to OT pay — employee choice | MEDIUM |
| OT007 | OT auto-calculated from attendance (beyond shift hours) | HIGH |

## 20. EMPLOYEE DOCUMENTS & COMPLIANCE

| # | Rule | Priority |
|---|------|----------|
| DC001 | Mandatory documents list — joining checklist (ID proof, PAN, Aadhaar, bank) | HIGH |
| DC002 | Cannot mark onboarding complete without mandatory docs | HIGH |
| DC003 | Document expiry tracking (visa, passport, license) | HIGH |
| DC004 | Expired document → auto-notification to HR | MEDIUM |
| DC005 | Document access — employee sees only own documents | CRITICAL |
| DC006 | HR can see all employee documents | HIGH |
| DC007 | Document categories — cannot delete category with documents in it | MEDIUM |
| DC008 | File size limit on uploads (e.g., max 10MB) | MEDIUM |
| DC009 | Allowed file types only (PDF, JPG, PNG — no .exe) | HIGH |
| DC010 | Document version history — upload new version doesn't delete old | MEDIUM |

## 21. REPORTING HIERARCHY & ORG STRUCTURE

| # | Rule | Priority |
|---|------|----------|
| OH001 | Every employee must have a reporting manager (except CEO) | HIGH |
| OH002 | Reporting chain depth limit (no infinite nesting) | MEDIUM |
| OH003 | Department must have at least one head/manager | MEDIUM |
| OH004 | Cannot delete department with active employees | CRITICAL |
| OH005 | Cannot delete designation if employees have that designation | HIGH |
| OH006 | Org chart reflects real-time reporting structure | HIGH |
| OH007 | Manager transfer — all reportees should be re-assigned or moved | HIGH |
| OH008 | Matrix reporting — employee can have dotted-line manager | MEDIUM |
| OH009 | Head count per department — tracked and reportable | MEDIUM |
| OH010 | Cost center assignment per employee/department | MEDIUM |

## 22. REWARDS & RECOGNITION

| # | Rule | Priority |
|---|------|----------|
| RW001 | Cannot give kudos to yourself | HIGH |
| RW002 | Maximum kudos per day limit enforced | MEDIUM |
| RW003 | Points expiry — unused points expire after X months | MEDIUM |
| RW004 | Reward redemption — cannot redeem more than balance | CRITICAL |
| RW005 | Manager budget — cannot award more than allocated | HIGH |
| RW006 | Nomination requires at least one nominator besides self | MEDIUM |
| RW007 | Challenge completion — auto-award points on meeting criteria | MEDIUM |
| RW008 | Celebration auto-detection — birthday/anniversary from profile data | MEDIUM |
| RW009 | Leaderboard — only active employees, terminated excluded | HIGH |
| RW010 | Anonymous kudos — sender identity not revealed if enabled | HIGH |

## 23. SURVEY & FEEDBACK INTEGRITY

| # | Rule | Priority |
|---|------|----------|
| SF001 | Anonymous survey — response CANNOT be linked to employee | CRITICAL |
| SF002 | Survey results visible only after end date (no early peeking) | HIGH |
| SF003 | Cannot edit response after submission | HIGH |
| SF004 | Manager cannot see individual anonymous responses | CRITICAL |
| SF005 | Minimum response threshold before results visible (e.g., 5 responses) | MEDIUM |
| SF006 | Feedback marked anonymous — audit log does NOT record user | CRITICAL |
| SF007 | Whistleblowing report — absolutely no user tracking | CRITICAL |
| SF008 | Survey question order randomization (if enabled) | LOW |
| SF009 | Mandatory questions — cannot submit without answering all | HIGH |
| SF010 | NPS calculation — (Promoters - Detractors) / Total × 100 | MEDIUM |

## 24. EMAIL & NOTIFICATION RULES

| # | Rule | Priority |
|---|------|----------|
| EM001 | Welcome email sent on employee creation | HIGH |
| EM002 | Password reset email — token expires in 30 min | HIGH |
| EM003 | Leave approval/rejection email within 1 minute | MEDIUM |
| EM004 | Payslip available email on payroll completion | HIGH |
| EM005 | Document expiry reminder — 30/15/7 days before | MEDIUM |
| EM006 | Birthday/anniversary auto-email | LOW |
| EM007 | Exit interview reminder to manager | MEDIUM |
| EM008 | Overdue invoice warning emails (7 days, 14 days, 15 days) | HIGH |
| EM009 | Unsubscribe from non-critical emails (but not system alerts) | MEDIUM |
| EM010 | Email template — correct merge tags (employee name, dates, etc.) | HIGH |

## 25. INTEGRATION & DATA SYNC RULES

| # | Rule | Priority |
|---|------|----------|
| IN001 | Attendance data syncs to Payroll for LOP calculation | CRITICAL |
| IN002 | Leave data syncs to Payroll for deductions | CRITICAL |
| IN003 | Employee creation in Core → auto-visible in Payroll | HIGH |
| IN004 | Employee termination in Core → blocked in all modules | CRITICAL |
| IN005 | Salary revision in Payroll → reflected in next payslip | HIGH |
| IN006 | Performance rating → used for increment recommendation | MEDIUM |
| IN007 | Recruitment hire → auto-creates employee in Core | HIGH |
| IN008 | Exit completion → deactivates in all modules | CRITICAL |
| IN009 | SSO session — logging out of Core logs out of all modules | HIGH |
| IN010 | Module subscription change → immediate access update | HIGH |

## 26. CONCURRENT ACCESS & RACE CONDITIONS

| # | Rule | Priority |
|---|------|----------|
| RC001 | Two managers approving same leave simultaneously — no double deduction | CRITICAL |
| RC002 | Two employees booking last available leave day — one should fail | HIGH |
| RC003 | Payroll running while salary is being revised — lock mechanism | CRITICAL |
| RC004 | Asset assigned while being assigned to another — second should fail | HIGH |
| RC005 | Duplicate form submission — prevented by idempotency | HIGH |
| RC006 | Concurrent attendance check-in from two devices — only one succeeds | MEDIUM |
| RC007 | Same candidate hired by two recruiters — conflict resolution | MEDIUM |
| RC008 | Bulk leave approval — atomic (all succeed or all fail) | HIGH |

## 27. DATA MIGRATION & IMPORT RULES

| # | Rule | Priority |
|---|------|----------|
| DM001 | CSV import — duplicate email detection | CRITICAL |
| DM002 | CSV import — mandatory fields validated before import | HIGH |
| DM003 | CSV import — partial failure should not corrupt existing data | CRITICAL |
| DM004 | CSV import — report which rows failed and why | HIGH |
| DM005 | Bulk operations — rollback on failure | HIGH |
| DM006 | Data export — respects RBAC (employee exports only own data) | HIGH |
| DM007 | Historical data import — dates validated (not future) | MEDIUM |

## 28. CALENDAR & HOLIDAY RULES

| # | Rule | Priority |
|---|------|----------|
| CH001 | Holiday list per location (different states have different holidays) | HIGH |
| CH002 | Optional holidays — limited number per employee | MEDIUM |
| CH003 | Holiday on weekend — substitute holiday on next working day (per policy) | MEDIUM |
| CH004 | Restricted holidays — need to apply, not automatic | MEDIUM |
| CH005 | Financial year calendar (Apr-Mar for India) vs calendar year | HIGH |
| CH006 | Working days calculation excludes holidays and weekends | CRITICAL |
| CH007 | Leave calendar shows holidays, leaves, and events together | MEDIUM |

## 29. GRATUITY & BENEFITS

| # | Rule | Priority |
|---|------|----------|
| GB001 | Gratuity eligible after 5 years of service | HIGH |
| GB002 | Gratuity = 15/26 × last drawn salary × years of service | HIGH |
| GB003 | Gratuity max cap Rs 20L (as per Payment of Gratuity Act) | HIGH |
| GB004 | Insurance enrollment — within 30 days of joining | MEDIUM |
| GB005 | Insurance — dependents management (add/remove family) | MEDIUM |
| GB006 | Flexible benefits plan — allocation within total limit | MEDIUM |
| GB007 | Meal vouchers/fuel card — taxable beyond threshold | MEDIUM |

## 30. AUDIT & COMPLIANCE REPORTING

| # | Rule | Priority |
|---|------|----------|
| AC001 | Every user action logged with timestamp, user ID, IP | CRITICAL |
| AC002 | Audit log is append-only — cannot be modified or deleted | CRITICAL |
| AC003 | Login attempts (success + failure) logged | HIGH |
| AC004 | Salary/payroll changes logged with before/after values | CRITICAL |
| AC005 | Leave approval chain logged | HIGH |
| AC006 | Document access logged | MEDIUM |
| AC007 | Export of audit logs for external compliance tools | MEDIUM |
| AC008 | Retention period — audit logs kept for minimum 7 years | HIGH |
| AC009 | SOC 2 compliance — access controls documented | HIGH |
| AC010 | POSH compliance — harassment reporting tracked | HIGH |

---

**Total additional rules: ~150 (across 15 new categories)**
**Grand total with V1: ~350 business rules**

Each should be tested and categorized as: ENFORCED / NOT ENFORCED / NOT IMPLEMENTED / PARTIAL
