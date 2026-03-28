# EmpCloud Correct API Paths

> Compiled from all 12 EmpCloud GitHub repository READMEs on 2026-03-28.
> Use this to fix wrong API paths used by test agents.

---

## Common Wrong Path Patterns -> Correct Paths

### EMP Cloud (API: https://test-empcloud-api.empcloud.com)

| Wrong Path (commonly used) | Correct Path | Notes |
|----------------------------|-------------|-------|
| `/departments` | `/api/v1/organizations/me/departments` | Departments are under org |
| `/locations` | `/api/v1/organizations/me/locations` | Locations are under org |
| `/api/v1/departments` | `/api/v1/organizations/me/departments` | Must go through org |
| `/api/v1/locations` | `/api/v1/organizations/me/locations` | Must go through org |
| `/api/v1/org` | `/api/v1/organizations/me` | Use /organizations/me |
| `/api/v1/organization` | `/api/v1/organizations/me` | Plural + /me |
| `/api/v1/employees/:id/extended` | `/api/v1/employees/:id/profile` | It's "profile" not "extended" |
| `/api/v1/attendance/checkin` | `/api/v1/attendance/check-in` | Hyphenated |
| `/api/v1/attendance/checkout` | `/api/v1/attendance/check-out` | Hyphenated |
| `/api/v1/leave/apply` | `/api/v1/leave/applications` | POST to /applications |
| `/api/v1/leave/approve/:id` | `/api/v1/leave/applications/:id/approve` | Nested under application |
| `/api/v1/leave/reject/:id` | `/api/v1/leave/applications/:id/reject` | Nested under application |
| `/api/v1/auth/sso` | `/api/v1/auth/sso/validate` | Cloud validates tokens at /validate |
| `/api/v1/documents/upload` | `/api/v1/documents` | POST to base path |
| `/api/v1/policies/acknowledge/:id` | `/api/v1/policies/:id/acknowledge` | ID before action |
| `/api/v1/notifications/mark-read` | `/api/v1/notifications/:id/read` | Per-notification |
| `/api/v1/notifications/mark-all-read` | `/api/v1/notifications/read-all` | read-all |
| `/api/v1/admin/health` | `/api/v1/admin/health` | Correct |
| `/api/v1/admin/data-sanity` | `/api/v1/admin/data-sanity` | Correct |
| `/api/docs` | `/api/docs` | Correct (Swagger UI) |
| `/health` | `/health` | Correct (health check) |

### EMP Payroll (API: https://testpayroll-api.empcloud.com)

| Wrong Path | Correct Path | Notes |
|------------|-------------|-------|
| `/api/v1/payroll/runs` | `/api/v1/payroll` | Runs are the base /payroll resource |
| `/api/v1/payroll/runs/:id` | `/api/v1/payroll/:id` | No /runs/ segment |
| `/api/v1/employees/:id/salary` | `/api/v1/salary-structures/employee/:empId` | Salary under salary-structures |
| `/api/v1/employees/:id/salary-history` | `/api/v1/salary-structures/employee/:empId/history` | Under salary-structures |
| `/api/v1/payslips` | `/api/v1/payroll/:id/payslips` | Payslips are under a payroll run |
| `/api/v1/self-service/payslips/:id` | `/api/v1/self-service/payslips/:id/pdf` | Add /pdf for download |
| `/api/v1/tax/form16` | `/api/v1/self-service/tax/form16` | Under self-service |
| `/api/v1/declarations` | `/api/v1/self-service/tax/declarations` | Under self-service/tax |
| `/api/v1/payroll/:id/reports` | `/api/v1/payroll/:id/reports/pf` (or /esi, /pt, /tds, /bank-file) | Specify report type |
| `/api/v1/salary-structures/assign/:empId` | `/api/v1/salary-structures/assign` | POST body contains empId |
| `/api/v1/docs` | `/api/v1/docs/openapi.json` | Payroll uses this path |

### EMP Recruit (API: https://test-recruit-api.empcloud.com)

| Wrong Path | Correct Path | Notes |
|------------|-------------|-------|
| `/api/v1/auth/login` | `/api/v1/auth/sso` | Recruit uses SSO only |
| `/api/v1/jobs/:id/candidates` | `/api/v1/jobs/:id/applications` | Applications, not candidates |
| `/api/v1/applications/:id/move` | `/api/v1/applications/:id/stage` | PATCH to /stage |
| `/api/v1/interviews/:id/record` | `/api/v1/interviews/:id/recordings` | Plural "recordings" |
| `/api/v1/offers/:id/pdf` | `/api/v1/offers/:id/generate-pdf` | Full verb path |
| `/api/v1/offers/:id/accept` | `/api/v1/offers/:id/send` | Cloud sends, candidate responds |
| `/api/v1/scoring/resume` | `/api/v1/ai/score-resume` | Under /ai/ prefix |
| `/api/v1/scoring/batch` | `/api/v1/ai/batch-score` | Under /ai/ |
| `/api/v1/candidates/:id/score` | `/api/v1/ai/skills/:candidateId` | Under /ai/ |
| `/api/v1/portal/login` | `/api/v1/portal/send-magic-link` | Magic link, not login |
| `/api/v1/careers/:slug` | `/api/v1/public/careers/:slug` | Under /public/ prefix |
| `/api/v1/pipeline` | `/api/v1/pipeline-stages` | Hyphenated full name |
| `/api/v1/background-check` | `/api/v1/background-checks` | Plural |

### EMP Performance (API: https://test-performance-api.empcloud.com)

| Wrong Path | Correct Path | Notes |
|------------|-------------|-------|
| `/api/v1/auth/login` | `/api/v1/auth/sso` | SSO only |
| `/api/v1/cycles` | `/api/v1/review-cycles` | Full name |
| `/api/v1/review-cycles/:id/start` | `/api/v1/review-cycles/:id/launch` | "launch" not "start" |
| `/api/v1/review-cycles/:id/end` | `/api/v1/review-cycles/:id/close` | "close" not "end" |
| `/api/v1/reviews/:id/save` | `/api/v1/reviews/:id` | PUT to base path |
| `/api/v1/goals/:id/okr` | `/api/v1/goals/:id/key-results` | "key-results" |
| `/api/v1/goals/:id/progress` | `/api/v1/goals/:id/check-in` | "check-in" |
| `/api/v1/goal-alignment` | `/api/v1/goal-alignment/tree` | Need /tree |
| `/api/v1/nine-box-grid` | `/api/v1/nine-box` | Shorter name |
| `/api/v1/succession` | `/api/v1/succession-plans` | Full name |
| `/api/v1/skills/:employeeId` | `/api/v1/skills-gap/:employeeId` | "skills-gap" |
| `/api/v1/1on1` | `/api/v1/one-on-ones` | Spelled out |
| `/api/v1/meetings` | `/api/v1/one-on-ones` | Use one-on-ones |
| `/api/v1/pips/:id/complete` | `/api/v1/pips/:id/close` | "close" not "complete" |
| `/api/v1/letters` | `/api/v1/letters/generate` | POST to generate |
| `/api/v1/analytics` | `/api/v1/analytics/overview` | Specify sub-path |
| `/api/v1/competencies` | `/api/v1/competency-frameworks` | Full name |

### EMP Rewards (API: https://test-rewards-api.empcloud.com)

| Wrong Path | Correct Path | Notes |
|------------|-------------|-------|
| `/api/v1/recognition` | `/api/v1/kudos` | "kudos" is the entity |
| `/api/v1/kudos/my` | `/api/v1/kudos/received` or `/api/v1/kudos/sent` | Separate sent/received |
| `/api/v1/points` | `/api/v1/points/balance` | Specify sub-path |
| `/api/v1/rewards/redeem/:id` | `/api/v1/rewards/:id/redeem` | ID before action |
| `/api/v1/leaderboard/:deptId` | `/api/v1/leaderboard/department/:deptId` | Need /department/ prefix |
| `/api/v1/celebrations/upcoming` | `/api/v1/celebrations` | Base path returns upcoming |
| `/api/v1/challenges/:id/end` | `/api/v1/challenges/:id/complete` | "complete" not "end" |
| `/api/v1/milestones` | `/api/v1/milestones/rules` | Need /rules |
| `/api/v1/teams/config` | `/api/v1/teams` | Base path |

### EMP Exit (API: https://test-exit-api.empcloud.com)

| Wrong Path | Correct Path | Notes |
|------------|-------------|-------|
| `/api/v1/exit-requests` | `/api/v1/exits` | Short name |
| `/api/v1/exits/:id/checklist` | `/api/v1/self-service/my-checklist` | Self-service path for employee |
| `/api/v1/exits/:id/clearance/:id/approve` | `/api/v1/exits/:id/clearance/:clearanceId` | PUT with status |
| `/api/v1/clearances/my` | `/api/v1/my-clearances` | Top-level path |
| `/api/v1/fnf/:id` | `/api/v1/exits/:id/fnf` | Nested under exit |
| `/api/v1/fnf/:id/calculate` | `/api/v1/exits/:id/fnf/calculate` | Nested under exit |
| `/api/v1/exits/:id/knowledge-transfer` | `/api/v1/exits/:id/kt` | Abbreviated "kt" |
| `/api/v1/exits/:id/letters` | `/api/v1/exits/:id/letters/generate` | POST to generate |
| `/api/v1/predictions` | `/api/v1/predictions/dashboard` | Specify sub-path |
| `/api/v1/attrition` | `/api/v1/predictions/dashboard` | Under predictions |
| `/api/v1/buyout/:id` | `/api/v1/exits/:id/buyout` | Nested under exit |
| `/api/v1/nps` | `/api/v1/nps/scores` | Specify sub-path |
| `/api/v1/rehire/eligible` | `/api/v1/rehire/eligible` | Correct |
| `/api/v1/resign` | `/api/v1/self-service/resign` | Under self-service |

### EMP LMS (API: https://testlms-api.empcloud.com)

| Wrong Path | Correct Path | Notes |
|------------|-------------|-------|
| `/api/v1/auth/login` | `/api/v1/auth/sso` | SSO preferred (also has /login) |
| `/api/v1/courses/:id/enroll` | `/api/v1/enrollments` | POST to /enrollments |
| `/api/v1/enrollments/my/:id/progress` | `/api/v1/enrollments/:id/progress` | No /my/ in update path |
| `/api/v1/quizzes/:id/submit` | `/api/v1/quizzes/attempt` | POST to /attempt |
| `/api/v1/learning-paths/:id/enrol` | `/api/v1/learning-paths/:id/enroll` | Double "l" |
| `/api/v1/certificates` | `/api/v1/certificates/my` | Need /my for list |
| `/api/v1/certificates/:id/pdf` | `/api/v1/certificates/:id/download` | "download" |
| `/api/v1/compliance` | `/api/v1/compliance/my` or `/api/v1/compliance/dashboard` | Specify sub-path |
| `/api/v1/ilt/:id/attend` | `/api/v1/ilt/:id/attendance` | "attendance" |
| `/api/v1/scorm/:id/play` | `/api/v1/scorm/:id/launch` | "launch" |
| `/api/v1/leaderboard` | `/api/v1/gamification/leaderboard` | Under /gamification/ |
| `/api/v1/badges` | `/api/v1/gamification/badges` | Under /gamification/ |
| `/api/v1/discussions/:id/reply` | `/api/v1/discussions/:id/replies` | Plural |

### EMP Billing (API: internal port 4001)

| Wrong Path | Correct Path | Notes |
|------------|-------------|-------|
| `/api/v1/invoices/:id/payment` | `/api/v1/payments` | Payments are separate resource |
| `/api/v1/invoices/:id/pdf` | `/api/v1/invoices/:id` | PDF generation is part of invoice actions |
| `/api/v1/recurring-invoices` | `/api/v1/recurring` | Short name |
| `/api/v1/saas-metrics` | `/api/v1/metrics` | Short name |
| `/api/v1/webhook` | `/api/v1/webhooks` | Plural |
| `/api/v1/api-key` | `/api/v1/api-keys` | Plural |
| `/api/v1/domain` | `/api/v1/domains` | Plural |

---

## Complete Endpoint Pattern Reference

### EMP Cloud API Patterns (Base: /api/v1/)

```
# Auth
POST   /auth/login
POST   /auth/register
POST   /auth/password-reset
POST   /auth/sso/validate

# OAuth
GET    /oauth/authorize
POST   /oauth/token
POST   /oauth/revoke
POST   /oauth/introspect
GET    /oauth/jwks
GET    /.well-known/openid-configuration

# Organizations
POST   /organizations
GET    /organizations/me
PUT    /organizations/me
GET    /organizations/me/departments
POST   /organizations/me/departments
PUT    /organizations/me/departments/:id
DELETE /organizations/me/departments/:id
GET    /organizations/me/locations
POST   /organizations/me/locations

# Users
GET    /users
POST   /users/invite
GET    /users/:id
PUT    /users/:id
PUT    /users/:id/roles

# Modules & Subscriptions
GET    /modules
GET    /modules/:id
GET    /subscriptions
POST   /subscriptions
PUT    /subscriptions/:id
DELETE /subscriptions/:id

# Employees
GET    /employees
GET    /employees/:id
PUT    /employees/:id
GET    /employees/:id/profile
PUT    /employees/:id/profile
POST   /employees/:id/photo
GET    /employees/:id/photo
GET    /employees/:id/addresses
POST   /employees/:id/addresses
GET    /employees/:id/education
POST   /employees/:id/education
GET    /employees/:id/experience
POST   /employees/:id/experience
GET    /employees/:id/dependents
POST   /employees/:id/dependents
GET    /employees/org-chart

# Attendance
POST   /attendance/check-in
POST   /attendance/check-out
GET    /attendance/records
GET    /attendance/dashboard
GET    /attendance/reports
GET    /attendance/export
GET    /attendance/shifts
POST   /attendance/shifts
PUT    /attendance/shifts/:id
GET    /attendance/shift-assignments
POST   /attendance/shift-assignments
GET    /attendance/geo-fences
POST   /attendance/geo-fences
GET    /attendance/regularizations
POST   /attendance/regularizations
PUT    /attendance/regularizations/:id
GET    /attendance/schedule

# Leave
GET    /leave/types
POST   /leave/types
GET    /leave/policies
POST   /leave/policies
GET    /leave/balances
GET    /leave/applications
POST   /leave/applications
PUT    /leave/applications/:id
POST   /leave/applications/:id/approve
POST   /leave/applications/:id/reject
POST   /leave/bulk-approve
POST   /leave/bulk-reject
GET    /leave/calendar
GET    /leave/comp-off
POST   /leave/comp-off
GET    /leave/dashboard

# Documents
GET    /documents/categories
POST   /documents/categories
GET    /documents
POST   /documents
GET    /documents/:id
GET    /documents/:id/download
PUT    /documents/:id/verify
GET    /documents/my
GET    /documents/mandatory
GET    /documents/expiry-alerts

# Announcements
GET    /announcements
POST   /announcements
GET    /announcements/:id
PUT    /announcements/:id
DELETE /announcements/:id
POST   /announcements/:id/read
GET    /announcements/unread-count

# Policies
GET    /policies
POST   /policies
GET    /policies/:id
PUT    /policies/:id
POST   /policies/:id/acknowledge
GET    /policies/pending

# Notifications
GET    /notifications
POST   /notifications/:id/read
POST   /notifications/read-all
GET    /notifications/unread-count
GET    /notifications/preferences

# Dashboard
GET    /dashboard/widgets
GET    /dashboard/module-summaries
GET    /dashboard/module-insights

# Billing
GET    /billing/invoices
GET    /billing/invoices/:id
POST   /billing/invoices/:id/pay
POST   /billing/webhooks/stripe
POST   /billing/webhooks/razorpay
POST   /billing/webhooks/paypal

# AI
POST   /chatbot/message
GET    /chatbot/conversations
GET    /chatbot/conversations/:id
GET    /ai-config
PUT    /ai-config

# Admin
GET    /admin/organizations
GET    /admin/organizations/:id
GET    /admin/health
GET    /admin/data-sanity
GET    /admin/stats

# Logs
GET    /logs
GET    /logs/analysis

# Helpdesk
GET    /helpdesk/tickets
POST   /helpdesk/tickets
GET    /helpdesk/tickets/:id
PUT    /helpdesk/tickets/:id
GET    /helpdesk/categories
GET    /helpdesk/knowledge-base
POST   /helpdesk/knowledge-base
POST   /helpdesk/knowledge-base/:id/rate

# Surveys
GET    /surveys
POST   /surveys
GET    /surveys/:id
POST   /surveys/:id/respond
GET    /surveys/:id/results

# Assets
GET    /assets
POST   /assets
GET    /assets/:id
PUT    /assets/:id
GET    /assets/categories
POST   /assets/:id/assign
GET    /assets/my

# Positions
GET    /positions
POST   /positions
GET    /positions/:id
PUT    /positions/:id
GET    /positions/headcount

# Forum
GET    /forum/categories
POST   /forum/categories
GET    /forum/posts
POST   /forum/posts
GET    /forum/posts/:id
POST   /forum/posts/:id/replies
POST   /forum/posts/:id/react

# Events
GET    /events
POST   /events
GET    /events/:id
POST   /events/:id/register
GET    /events/calendar

# Wellness
GET    /wellness/dashboard
POST   /wellness/check-in
GET    /wellness/goals

# Feedback
POST   /feedback
GET    /feedback

# Whistleblowing
POST   /whistleblowing
GET    /whistleblowing
GET    /whistleblowing/:id
GET    /whistleblowing/track/:trackingId

# Custom Fields
GET    /custom-fields/definitions
POST   /custom-fields/definitions
GET    /custom-fields/values/:entityType/:entityId
PUT    /custom-fields/values/:entityType/:entityId

# Biometrics
POST   /biometrics/enroll
POST   /biometrics/verify
GET    /biometrics/devices
POST   /biometrics/qr/generate
POST   /biometrics/qr/scan

# Manager
GET    /manager/dashboard
GET    /manager/team

# Import
POST   /import/upload
POST   /import/preview
POST   /import/execute
GET    /import/history

# Audit
GET    /audit

# System
GET    /health              (no /api/v1 prefix)
GET    /api/docs            (Swagger UI)
GET    /api/docs/openapi.json
```

### EMP Payroll API Patterns (Base: /api/v1/)

```
# Auth
POST   /auth/login
POST   /auth/register
POST   /auth/refresh-token
POST   /auth/change-password
POST   /auth/reset-employee-password

# Employees
GET    /employees
POST   /employees
GET    /employees/export
GET    /employees/:id
PUT    /employees/:id
DELETE /employees/:id
GET    /employees/:id/bank-details
PUT    /employees/:id/bank-details
GET    /employees/:id/tax-info
PUT    /employees/:id/tax-info
GET    /employees/:id/pf-details
PUT    /employees/:id/pf-details
GET    /employees/:id/notes
POST   /employees/:id/notes
DELETE /employees/:id/notes/:noteId

# Payroll
GET    /payroll
POST   /payroll
GET    /payroll/:id
POST   /payroll/:id/compute
POST   /payroll/:id/approve
POST   /payroll/:id/pay
POST   /payroll/:id/cancel
GET    /payroll/:id/payslips
POST   /payroll/:id/send-payslips
GET    /payroll/:id/reports/pf
GET    /payroll/:id/reports/esi
GET    /payroll/:id/reports/pt
GET    /payroll/:id/reports/tds
GET    /payroll/:id/reports/bank-file

# Salary
GET    /salary-structures
POST   /salary-structures
GET    /salary-structures/:id/components
POST   /salary-structures/assign
GET    /salary-structures/employee/:empId
GET    /salary-structures/employee/:empId/history

# Benefits
GET    /benefits/dashboard
GET    /benefits/plans
POST   /benefits/plans
GET    /benefits/plans/:id
PUT    /benefits/plans/:id
GET    /benefits/enrollments
POST   /benefits/enrollments
GET    /benefits/my

# Insurance
GET    /insurance/dashboard
GET    /insurance/policies
POST   /insurance/policies
GET    /insurance/policies/:id
PUT    /insurance/policies/:id
GET    /insurance/enrollments
POST   /insurance/enrollments
GET    /insurance/claims
POST   /insurance/claims
PUT    /insurance/claims/:id/review

# GL
GET    /gl-accounting/mappings
POST   /gl-accounting/mappings
PUT    /gl-accounting/mappings/:id
DELETE /gl-accounting/mappings/:id
POST   /gl-accounting/journal-entries/generate
GET    /gl-accounting/journal-entries
GET    /gl-accounting/period-summary

# Global Payroll
GET    /global-payroll/dashboard
GET    /global-payroll/cost-analysis
GET    /global-payroll/countries
GET    /global-payroll/countries/:id
GET    /global-payroll/employees
POST   /global-payroll/employees
GET    /global-payroll/employees/:id
PUT    /global-payroll/employees/:id
GET    /global-payroll/runs
POST   /global-payroll/runs
GET    /global-payroll/contractor-invoices
POST   /global-payroll/contractor-invoices
GET    /global-payroll/compliance
PUT    /global-payroll/compliance/:id

# EWA
GET    /earned-wage/settings
PUT    /earned-wage/settings
GET    /earned-wage/requests
POST   /earned-wage/requests
GET    /earned-wage/requests/:id
PUT    /earned-wage/requests/:id/approve
PUT    /earned-wage/requests/:id/reject
GET    /earned-wage/my/eligibility
GET    /earned-wage/my/requests

# Pay Equity
GET    /pay-equity/analysis
GET    /pay-equity/compliance-report

# Benchmarks
GET    /compensation-benchmarks
POST   /compensation-benchmarks
GET    /compensation-benchmarks/:id
PUT    /compensation-benchmarks/:id
DELETE /compensation-benchmarks/:id
POST   /compensation-benchmarks/import
GET    /compensation-benchmarks/comparison

# Self-Service
GET    /self-service/dashboard
GET    /self-service/payslips
GET    /self-service/payslips/:id/pdf
GET    /self-service/salary
GET    /self-service/tax/computation
GET    /self-service/tax/declarations
POST   /self-service/tax/declarations
GET    /self-service/tax/form16
GET    /self-service/reimbursements
POST   /self-service/reimbursements
GET    /self-service/profile

# Other
GET    /attendance (summary)
GET    /leaves (balances)
GET    /loans
POST   /loans
GET    /reimbursements
GET    /total-rewards/:employeeId
GET    /adjustments
GET    /announcements
GET    /organizations (settings)
GET    /health
GET    /api/v1/docs/openapi.json
```

### EMP Recruit API Patterns (Base: /api/v1/)

```
POST   /auth/sso
GET    /jobs
POST   /jobs
GET    /jobs/:id
PUT    /jobs/:id
PATCH  /jobs/:id/status
GET    /jobs/:id/applications
GET    /jobs/:id/analytics
POST   /job-descriptions/generate
GET    /job-descriptions/templates
GET    /candidates
POST   /candidates
GET    /candidates/:id
PUT    /candidates/:id
POST   /candidates/:id/resume
GET    /candidates/compare
GET    /applications
POST   /applications
GET    /applications/:id
PATCH  /applications/:id/stage
GET    /applications/:id/timeline
GET    /interviews
POST   /interviews
GET    /interviews/:id
PUT    /interviews/:id
POST   /interviews/:id/feedback
POST   /interviews/:id/generate-meet
POST   /interviews/:id/send-invitation
POST   /interviews/:id/recordings
GET    /interviews/:id/recordings
DELETE /interviews/:id/recordings
POST   /interviews/:id/recordings/:recId/transcribe
GET    /interviews/:id/transcript
PUT    /interviews/:id/transcript
GET    /interviews/:id/calendar-links
GET    /interviews/:id/calendar.ics
POST   /offers
GET    /offers/:id
POST   /offers/:id/submit-approval
POST   /offers/:id/approve
POST   /offers/:id/send
POST   /offers/:id/generate-pdf
POST   /offers/:id/email-letter
POST   /ai/score-resume
POST   /ai/batch-score
GET    /ai/rankings/:jobId
GET    /ai/skills/:candidateId
POST   /background-checks
GET    /background-checks/:id
GET    /background-checks/candidate/:candidateId
PUT    /background-checks/:id
GET    /pipeline-stages
PUT    /pipeline-stages
POST   /pipeline-stages
DELETE /pipeline-stages/:id
POST   /portal/send-magic-link
POST   /portal/verify
GET    /portal/my-applications
GET    /portal/my-interviews
GET    /portal/my-offers
GET    /onboarding/templates
POST   /onboarding/templates
POST   /onboarding/checklists
PATCH  /onboarding/tasks/:id
GET    /public/careers/:slug
GET    /public/careers/:slug/jobs
POST   /public/careers/:slug/apply
POST   /surveys
GET    /surveys/:id
POST   /surveys/:id/respond
POST   /assessments
GET    /assessments/:id
POST   /assessments/:id/submit
GET    /health
GET    /api/docs
```

### EMP Performance API Patterns (Base: /api/v1/)

```
POST   /auth/sso
GET    /review-cycles
POST   /review-cycles
GET    /review-cycles/:id
PUT    /review-cycles/:id
POST   /review-cycles/:id/launch
POST   /review-cycles/:id/close
POST   /review-cycles/:id/participants
GET    /review-cycles/:id/ratings-distribution
GET    /reviews
GET    /reviews/:id
PUT    /reviews/:id
POST   /reviews/:id/submit
GET    /goals
POST   /goals
GET    /goals/:id
PUT    /goals/:id
POST   /goals/:id/key-results
POST   /goals/:id/check-in
GET    /goal-alignment/tree
POST   /goal-alignment/link
DELETE /goal-alignment/link/:id
GET    /goal-alignment/rollup/:goalId
GET    /nine-box
PUT    /nine-box/:employeeId
GET    /nine-box/history/:employeeId
GET    /succession-plans
POST   /succession-plans
GET    /succession-plans/:id
POST   /succession-plans/:id/candidates
PUT    /succession-plans/:id/candidates/:candidateId
DELETE /succession-plans/:id/candidates/:candidateId
GET    /skills-gap/:employeeId
GET    /skills-gap/team/:teamId
POST   /skills-gap/assess
GET    /skills-gap/recommendations/:employeeId
GET    /manager-effectiveness
GET    /manager-effectiveness/:managerId
GET    /manager-effectiveness/:managerId/trends
POST   /manager-effectiveness/calculate
POST   /ai-summary/review/:reviewId
POST   /ai-summary/cycle/:cycleId
POST   /ai-summary/team/:managerId
GET    /ai-summary/:id
GET    /letter-templates
POST   /letter-templates
PUT    /letter-templates/:id
POST   /letters/generate
GET    /letters/:id/download
POST   /letters/:id/send
GET    /competency-frameworks
POST   /competency-frameworks
GET    /competency-frameworks/:id
POST   /competency-frameworks/:id/competencies
GET    /pips
POST   /pips
GET    /pips/:id
POST   /pips/:id/objectives
POST   /pips/:id/updates
POST   /pips/:id/close
GET    /career-paths
POST   /career-paths
GET    /career-paths/:id
POST   /career-paths/:id/levels
GET    /employees/:id/career-track
PUT    /employees/:id/career-track
GET    /one-on-ones
POST   /one-on-ones
GET    /one-on-ones/:id
POST   /one-on-ones/:id/agenda-items
POST   /one-on-ones/:id/complete
GET    /feedback
POST   /feedback
GET    /feedback/:id
POST   /peer-reviews/nominate
GET    /peer-reviews/nominations
POST   /peer-reviews/nominations/:id/approve
POST   /peer-reviews/nominations/:id/reject
GET    /notifications/settings
PUT    /notifications/settings
GET    /notifications/pending
GET    /analytics/overview
GET    /analytics/ratings-distribution
GET    /analytics/team-comparison
GET    /analytics/trends
GET    /analytics/goal-completion
GET    /analytics/top-performers
GET    /health
GET    /api/docs
```

### EMP Rewards API Patterns (Base: /api/v1/)

```
POST   /kudos
GET    /kudos
GET    /kudos/:id
DELETE /kudos/:id
GET    /kudos/received
GET    /kudos/sent
POST   /kudos/:id/reactions
POST   /kudos/:id/comments
GET    /points/balance
GET    /points/transactions
POST   /points/adjust
GET    /badges
POST   /badges
GET    /badges/my
POST   /badges/award
GET    /rewards
POST   /rewards
POST   /rewards/:id/redeem
GET    /redemptions
GET    /redemptions/my
PUT    /redemptions/:id/approve
PUT    /redemptions/:id/fulfill
GET    /nominations/programs
POST   /nominations/programs
POST   /nominations
PUT    /nominations/:id/review
GET    /leaderboard
GET    /leaderboard/department/:deptId
GET    /leaderboard/my-rank
GET    /celebrations
GET    /celebrations/feed
POST   /celebrations/:id/wish
GET    /challenges
POST   /challenges
GET    /challenges/:id
POST   /challenges/:id/join
GET    /challenges/:id/progress
POST   /challenges/:id/complete
GET    /milestones/rules
POST   /milestones/rules
PUT    /milestones/rules/:id
GET    /milestones/history
GET    /manager/dashboard
GET    /manager/team-comparison
GET    /manager/recommendations
GET    /slack/config
PUT    /slack/config
POST   /slack/test
POST   /slack/slash-command
GET    /teams
PUT    /teams
POST   /teams/test
GET    /push/vapid-key
POST   /push/subscribe
POST   /push/unsubscribe
POST   /push/test
GET    /integration/user/:userId/summary
GET    /health
GET    /api/docs
```

### EMP Exit API Patterns (Base: /api/v1/)

```
POST   /exits
GET    /exits
GET    /exits/:id
PUT    /exits/:id
POST   /exits/:id/cancel
POST   /exits/:id/complete
POST   /self-service/resign
GET    /self-service/my-exit
GET    /self-service/my-checklist
POST   /self-service/exit-interview
POST   /self-service/nps-survey
GET    /checklist-templates
POST   /checklist-templates
PUT    /checklist-templates/:id
POST   /checklist-templates/:id/items
GET    /clearance-departments
GET    /exits/:id/clearance
PUT    /exits/:id/clearance/:clearanceId
GET    /my-clearances
GET    /interview-templates
POST   /interview-templates
GET    /exits/:id/interview
POST   /exits/:id/interview
POST   /exits/:id/fnf/calculate
GET    /exits/:id/fnf
PUT    /exits/:id/fnf
POST   /exits/:id/fnf/approve
POST   /exits/:id/fnf/mark-paid
GET    /exits/:id/assets
POST   /exits/:id/assets
PUT    /exits/:id/assets/:assetId
POST   /exits/:id/kt
PUT    /exits/:id/kt
POST   /exits/:id/kt/items
GET    /letter-templates
POST   /letter-templates
POST   /exits/:id/letters/generate
GET    /exits/:id/letters/:letterId/download
POST   /exits/:id/letters/:letterId/send
GET    /predictions/dashboard
GET    /predictions/high-risk
GET    /predictions/employee/:employeeId
GET    /predictions/trends
POST   /predictions/calculate
POST   /exits/:id/buyout/calculate
POST   /exits/:id/buyout/request
PUT    /exits/:id/buyout/approve
GET    /exits/:id/buyout
GET    /email-templates
PUT    /email-templates/:stage
POST   /email-templates/:stage/preview
GET    /exits/:id/email-log
GET    /rehire
POST   /rehire
PUT    /rehire/:id/screen
PUT    /rehire/:id/approve
POST   /rehire/:id/hire
GET    /rehire/eligible
GET    /nps/scores
GET    /nps/trends
GET    /nps/responses
GET    /nps/department/:deptId
GET    /health
GET    /api/docs
```

### EMP LMS API Patterns (Base: /api/v1/)

```
POST   /auth/login
POST   /auth/sso
GET    /courses
POST   /courses
GET    /courses/:id
PUT    /courses/:id
DELETE /courses/:id
POST   /enrollments
POST   /enrollments/bulk
GET    /enrollments/my
PUT    /enrollments/:id/progress
GET    /quizzes/:id
POST   /quizzes/attempt
GET    /quizzes/:id/attempts
GET    /learning-paths
POST   /learning-paths
GET    /learning-paths/:id
POST   /learning-paths/:id/enroll
GET    /certificates/my
POST   /certificates/issue
GET    /certificates/:id/download
GET    /certificates/:id/verify
GET    /compliance/my
POST   /compliance/assign
GET    /compliance/dashboard
GET    /compliance/overdue
GET    /ilt
POST   /ilt
POST   /ilt/:id/register
POST   /ilt/:id/attendance
GET    /scorm/:id/launch
POST   /scorm/upload
POST   /scorm/:id/tracking
GET    /gamification/leaderboard
GET    /gamification/my
GET    /gamification/badges
GET    /discussions
POST   /discussions
POST   /discussions/:id/replies
GET    /ratings
POST   /ratings
PUT    /ratings/:id
GET    /analytics/overview
GET    /analytics/courses
GET    /analytics/users
GET    /recommendations
GET    /marketplace
POST   /video/upload
GET    /video/:id/stream
GET    /notifications
GET    /health
```

---

## Key Takeaways for Test Agents

1. **All module APIs use `/api/v1/` prefix** (except EMP Project which uses `/v1/`)
2. **Departments and locations are UNDER organizations**: `/api/v1/organizations/me/departments`
3. **SSO validation is at**: `POST /api/v1/auth/sso/validate` (Cloud) or `POST /api/v1/auth/sso` (modules)
4. **Check-in/check-out are hyphenated**: `/api/v1/attendance/check-in`
5. **Leave applications use REST pattern**: POST to `/applications`, actions nested under ID
6. **Payroll runs are at `/api/v1/payroll`** (not `/api/v1/payroll/runs`)
7. **Employee salary is under salary-structures**: `/api/v1/salary-structures/employee/:empId`
8. **Each module has its own API domain** in the test environment
9. **Swagger UI is at `/api/docs`** for every module (except EMP Project which uses `/explorer`)
10. **Health check is at `/health`** (no /api/v1 prefix) for all modules
