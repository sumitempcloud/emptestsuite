# Comprehensive Payroll Test Suite

> **Testing Agent Note:** This is an exhaustive list derived directly from project parameters. Every item must be tested. Record actual HTTP response codes, payloads, and screenshot evidence.

## 1. Business Logic Rules

- [ ] **P001** (CRITICAL): Cannot run payroll twice for same month
- [ ] **P002** (CRITICAL): Payroll includes LOP deductions for unapproved absences
- [ ] **P003** (CRITICAL): Tax calculation follows correct slab (old vs new regime)
- [ ] **P004** (HIGH): PF deduction = 12% of basic (or as per policy)
- [ ] **P005** (HIGH): ESI applicable only if gross < threshold
- [ ] **P006** (HIGH): Professional Tax per state rules
- [ ] **P007** (HIGH): TDS deducted monthly based on projected annual tax
- [ ] **P008** (HIGH): New joiner — pro-rated salary for partial month
- [ ] **P009** (HIGH): Exit mid-month — pro-rated salary + F&F
- [ ] **P010** (HIGH): Cannot modify payslip after payroll is locked
- [ ] **P011** (MEDIUM): Overtime pay added to gross
- [ ] **P012** (MEDIUM): Reimbursement claims included in payroll
- [ ] **P013** (MEDIUM): Bonus/incentive correctly added
- [ ] **P014** (MEDIUM): Loan EMI deducted from salary
- [ ] **P015** (CRITICAL): Net pay = Gross - Deductions (PF + ESI + PT + TDS + loans)
- [ ] **P016** (HIGH): Bank file generated with correct account details
- [ ] **P017** (HIGH): Form 16 generated at year end
- [ ] **P018** (HIGH): Payroll lock prevents any changes
- [ ] **P019** (MEDIUM): Salary revision — effective from a specific date
- [ ] **P020** (MEDIUM): Arrears calculation on back-dated revision

## 2. API Endpoints to Verify

- [ ] `POST` `/api/v1/auth/login` -> Expected Status: `400`
- [ ] `POST` `/api/v1/auth/refresh-token` -> Expected Status: `400`
- [ ] `POST` `/api/v1/auth/register` -> Expected Status: `400`
- [ ] `GET` `/api/v1/benefits/my` -> Expected Status: `200`
- [ ] `GET` `/api/v1/benefits/plans` -> Expected Status: `200`
- [ ] `GET` `/api/v1/employees/{id}/notes` -> Expected Status: `200`
- [ ] `POST` `/api/v1/insurance/claims` -> Expected Status: `400`
- [ ] `GET` `/api/v1/insurance/policies` -> Expected Status: `200`
- [ ] `GET` `/api/v1/salary-structures/employee/{empId}/history` -> Expected Status: `200`
- [ ] `GET` `/api/v1/salary-structures/{id}/components` -> Expected Status: `200`
- [ ] `GET` `/api/v1/adjustments` -> Expected Status: `429`
- [ ] `GET` `/api/v1/announcements` -> Expected Status: `429`
- [ ] `GET` `/api/v1/attendance` -> Expected Status: `429`
- [ ] `GET` `/api/v1/auth` -> Expected Status: `429`
- [ ] `POST` `/api/v1/auth/change-password` -> Expected Status: `500`
- [ ] `POST` `/api/v1/auth/reset-employee-password` -> Expected Status: `403`
- [ ] `GET` `/api/v1/benefits` -> Expected Status: `429`
- [ ] `GET` `/api/v1/benefits/dashboard` -> Expected Status: `403`
- [ ] `GET` `/api/v1/benefits/enrollments` -> Expected Status: `403`
- [ ] `POST` `/api/v1/benefits/enrollments` -> Expected Status: `404`
- [ ] `POST` `/api/v1/benefits/plans` -> Expected Status: `403`
- [ ] `GET` `/api/v1/benefits/plans/{id}` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/benefits/plans/{id}` -> Expected Status: `403`
- [ ] `GET` `/api/v1/compensation-benchmarks` -> Expected Status: `404`
- [ ] `GET` `/api/v1/compensation-benchmarks/comparison` -> Expected Status: `429`
- [ ] `POST` `/api/v1/compensation-benchmarks/import` -> Expected Status: `404`
- [ ] `GET` `/api/v1/compensation-benchmarks/{id}` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/compensation-benchmarks/{id}` -> Expected Status: `404`
- [ ] `DELETE` `/api/v1/compensation-benchmarks/{id}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/earned-wage` -> Expected Status: `404`

