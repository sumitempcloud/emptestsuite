# EmpCloud Comprehensive Knowledge Base

> Generated: 2026-03-28 22:00
> Source: All test results, API references, READMEs, simulation data
> Total endpoints mapped: 626

## Table of Contents
- [A. Definitive API Map](#a-definitive-api-map)
- [B. Module Feature Matrix](#b-module-feature-matrix)
- [C. Known Working Flows](#c-known-working-flows)
- [D. Known Broken Flows](#d-known-broken-flows)
- [E. Optimal Test Suite](#e-optimal-test-suite)
- [F. Environment Configuration](#f-environment-configuration)

---
## A. Definitive API Map

### EMP Cloud Core
- **API Base**: `https://test-empcloud-api.empcloud.com`
- **Prefix**: `/api/v1/`
- **Auth**: JWT (native)
- **Needs SSO**: No

**Verified Working (84 endpoints):**

| Method | Path | Status | Response Keys |
|--------|------|--------|---------------|
| GET | `/.well-known/openid-configuration` | 200 | issuer, authorization_endpoint, token_endpoint |
| GET | `/api/docs` | 200 |  |
| GET | `/api/v1/admin/data-sanity` | 200 | success, data |
| GET | `/api/v1/admin/health` | 200 | success, data |
| GET | `/api/v1/admin/organizations` | 200 | success, data, meta |
| GET | `/api/v1/admin/organizations/5` | 200 | success, data |
| GET | `/api/v1/announcements` | 200 | success, data, meta |
| POST | `/api/v1/announcements` | 201 | success, data |
| GET | `/api/v1/announcements/unread-count` | 200 | success, data |
| GET | `/api/v1/assets` | 200 | success, data, meta |
| POST | `/api/v1/assets` | 201 | success, data |
| GET | `/api/v1/assets/categories` | 200 | success, data |
| GET | `/api/v1/assets/my` | 200 | success, data |
| POST | `/api/v1/attendance/check-in` | 409 | success, error |
| POST | `/api/v1/attendance/check-out` | 409 | success, error |
| GET | `/api/v1/attendance/dashboard` | 200 | success, data |
| GET | `/api/v1/attendance/records` | 200 | success, data, meta |
| GET | `/api/v1/attendance/records?start_date=2026-03-01&end_date=2026-03-28` | 200 | success, data, meta |
| GET | `/api/v1/attendance/shifts` | 200 | success, data |
| POST | `/api/v1/attendance/shifts` | 201 | success, data |
| PUT | `/api/v1/attendance/shifts/10` | 200 | success, data |
| GET | `/api/v1/audit` | 200 | success, data, meta |
| POST | `/api/v1/auth/login` | 200 | success, data |
| POST | `/api/v1/auth/register` | 400 | success, error |
| GET | `/api/v1/chatbot/conversations` | 200 | success, data |
| GET | `/api/v1/custom-fields/definitions` | 200 | success, data |
| POST | `/api/v1/custom-fields/definitions` | 400 | success, error |
| GET | `/api/v1/dashboard/widgets` | 200 | success, data |
| GET | `/api/v1/docs/openapi.json` | 200 | openapi, info, servers |
| GET | `/api/v1/documents` | 200 | success, data, meta |
| GET | `/api/v1/documents/categories` | 200 | success, data |
| GET | `/api/v1/documents/my` | 200 | success, data, meta |
| GET | `/api/v1/employees/663/profile` | 200 | success, data |
| GET | `/api/v1/events` | 200 | success, data, meta |
| POST | `/api/v1/events` | 201 | success, data |
| GET | `/api/v1/feedback` | 200 | success, data, meta |
| POST | `/api/v1/feedback` | 400 | success, error |
| GET | `/api/v1/forum/categories` | 200 | success, data |
| POST | `/api/v1/forum/categories` | 201 | success, data |
| GET | `/api/v1/forum/posts` | 200 | success, data, meta |
| POST | `/api/v1/forum/posts` | 201 | success, data |
| GET | `/api/v1/helpdesk/tickets` | 200 | success, data, meta |
| POST | `/api/v1/helpdesk/tickets` | 400 | success, error |
| GET | `/api/v1/leave/applications` | 200 | success, data, meta |
| POST | `/api/v1/leave/applications` | 400 | success, error |
| GET | `/api/v1/leave/balances` | 200 | success, data |
| GET | `/api/v1/leave/calendar` | 200 | success, data |
| GET | `/api/v1/leave/comp-off` | 200 | success, data, meta |
| GET | `/api/v1/leave/policies` | 200 | success, data |
| POST | `/api/v1/leave/policies` | 400 | success, error |
| GET | `/api/v1/leave/types` | 200 | success, data |
| POST | `/api/v1/leave/types` | 400 | success, error |
| PUT | `/api/v1/leave/types/31` | 200 | success, data |
| GET | `/api/v1/modules` | 200 | success, data |
| GET | `/api/v1/notifications` | 200 | success, data, meta |
| GET | `/api/v1/notifications/unread-count` | 200 | success, data |
| GET | `/api/v1/organizations/me` | 200 | success, data |
| PUT | `/api/v1/organizations/me` | 200 | success, data |
| GET | `/api/v1/organizations/me/departments` | 200 | success, data |
| POST | `/api/v1/organizations/me/departments` | 201 | success, data |
| GET | `/api/v1/organizations/me/locations` | 200 | success, data |
| POST | `/api/v1/organizations/me/locations` | 201 | success, data |
| GET | `/api/v1/policies` | 200 | success, data, meta |
| POST | `/api/v1/policies` | 201 | success, data |
| GET | `/api/v1/policies/pending` | 200 | success, data |
| GET | `/api/v1/positions` | 200 | success, data, meta |
| POST | `/api/v1/positions` | 201 | success, data |
| GET | `/api/v1/self-service/payslips` | 200 | success, data |
| GET | `/api/v1/subscriptions` | 200 | success, data |
| GET | `/api/v1/surveys` | 200 | success, data, meta |
| POST | `/api/v1/surveys` | 400 | success, error |
| GET | `/api/v1/users` | 200 | success, data, meta |
| GET | `/api/v1/users/663` | 200 | success, data |
| PUT | `/api/v1/users/663` | 200 | success, data |
| POST | `/api/v1/users/invite` | 201 | success, data |
| GET | `/api/v1/users/org-chart` | 200 | success, data |
| GET | `/api/v1/users?page=1&limit=5` | 200 | success, data, meta |
| GET | `/api/v1/users?search=priya` | 200 | success, data, meta |
| POST | `/api/v1/wellness/check-in` | 400 | success, error |
| GET | `/health` | 200 | success, data |
| POST | `/oauth/introspect` | 400 | success, error |
| GET | `/oauth/jwks` | 200 | keys |
| POST | `/oauth/revoke` | 400 | success, error |
| POST | `/oauth/token` | 400 | success, error |

**Not Working / Not Deployed (101 endpoints):**

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/api/v1/admin` | 403 | auth_error |
| GET | `/api/v1/admin/stats` | 404 | working |
| GET | `/api/v1/ai-config` | 404 | working |
| GET | `/api/v1/analytics` | 401 | UNAUTHORIZED (401) |
| GET | `/api/v1/analytics/overview` | 401 | UNAUTHORIZED (401) |
| GET | `/api/v1/applications` | 401 | UNAUTHORIZED (401) |
| GET | `/api/v1/attendance` | 404 | missing_404 |
| GET | `/api/v1/attendance/export` | 404 | working |
| GET | `/api/v1/attendance/geo-fences` | 200 | exists but no data |
| GET | `/api/v1/attendance/regularizations` | 200 | exists but no data |
| GET | `/api/v1/attendance/reports` | 404 | working |
| GET | `/api/v1/attendance/schedule` | 404 | working |
| GET | `/api/v1/attendance/shift-assignments` | 404 | working |
| GET | `/api/v1/auth` | 404 | missing_404 |
| POST | `/api/v1/auth/password-reset` | 404 | NOT FOUND (404) |
| POST | `/api/v1/auth/sso/validate` | 404 | NOT FOUND (404) |
| GET | `/api/v1/badges` | 401 | UNAUTHORIZED (401) |
| GET | `/api/v1/billing` | 404 | missing_404 |
| GET | `/api/v1/billing/invoices` | 200 | exists but no data |
| GET | `/api/v1/biometrics` | 404 | missing_404 |
| ... | *81 more* | | |

### EMP Payroll
- **API Base**: `https://testpayroll-api.empcloud.com`
- **Prefix**: `/api/v1/`
- **Auth**: SSO token
- **Needs SSO**: Yes

**Verified Working (10 endpoints):**

| Method | Path | Status | Response Keys |
|--------|------|--------|---------------|
| POST | `/api/v1/auth/login` | 400 |  |
| POST | `/api/v1/auth/refresh-token` | 400 |  |
| POST | `/api/v1/auth/register` | 400 |  |
| GET | `/api/v1/benefits/my` | 200 |  |
| GET | `/api/v1/benefits/plans` | 200 |  |
| GET | `/api/v1/employees/{id}/notes` | 200 |  |
| POST | `/api/v1/insurance/claims` | 400 |  |
| GET | `/api/v1/insurance/policies` | 200 |  |
| GET | `/api/v1/salary-structures/employee/{empId}/history` | 200 |  |
| GET | `/api/v1/salary-structures/{id}/components` | 200 |  |

**Not Working / Not Deployed (112 endpoints):**

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/api/v1/adjustments` | 429 | rate_limited |
| GET | `/api/v1/announcements` | 429 | rate_limited |
| GET | `/api/v1/attendance` | 429 | rate_limited |
| GET | `/api/v1/auth` | 429 | rate_limited |
| POST | `/api/v1/auth/change-password` | 500 | server_error |
| POST | `/api/v1/auth/reset-employee-password` | 403 | auth_error |
| GET | `/api/v1/benefits` | 429 | rate_limited |
| GET | `/api/v1/benefits/dashboard` | 403 | auth_error |
| GET | `/api/v1/benefits/enrollments` | 403 | auth_error |
| POST | `/api/v1/benefits/enrollments` | 404 | missing_404 |
| POST | `/api/v1/benefits/plans` | 403 | auth_error |
| GET | `/api/v1/benefits/plans/{id}` | 404 | missing_404 |
| PUT | `/api/v1/benefits/plans/{id}` | 403 | auth_error |
| GET | `/api/v1/compensation-benchmarks` | 404 | missing_404 |
| GET | `/api/v1/compensation-benchmarks/comparison` | 429 | rate_limited |
| POST | `/api/v1/compensation-benchmarks/import` | 404 | missing_404 |
| GET | `/api/v1/compensation-benchmarks/{id}` | 404 | missing_404 |
| PUT | `/api/v1/compensation-benchmarks/{id}` | 404 | missing_404 |
| DELETE | `/api/v1/compensation-benchmarks/{id}` | 404 | missing_404 |
| GET | `/api/v1/earned-wage` | 404 | missing_404 |
| ... | *92 more* | | |

### EMP Recruit
- **API Base**: `https://test-recruit-api.empcloud.com`
- **Prefix**: `/api/v1/`
- **Auth**: SSO only
- **Needs SSO**: Yes

**Verified Working (21 endpoints):**

| Method | Path | Status | Response Keys |
|--------|------|--------|---------------|
| GET | `/api/v1/applications` | 200 |  |
| POST | `/api/v1/applications` | 400 |  |
| PATCH | `/api/v1/applications/{id}/stage` | 400 |  |
| POST | `/api/v1/auth/sso` | 400 |  |
| GET | `/api/v1/background-checks/candidate/{candidateId}` | 200 |  |
| PUT | `/api/v1/background-checks/{id}` | 400 |  |
| GET | `/api/v1/candidates` | 200 |  |
| POST | `/api/v1/candidates` | 400 |  |
| PUT | `/api/v1/candidates/{id}` | 400 |  |
| GET | `/api/v1/interviews` | 200 |  |
| POST | `/api/v1/interviews` | 400 |  |
| POST | `/api/v1/interviews/{id}/feedback` | 400 |  |
| POST | `/api/v1/interviews/{id}/recordings` | 400 |  |
| GET | `/api/v1/interviews/{id}/recordings` | 200 |  |
| GET | `/api/v1/interviews/{id}/transcript` | 200 |  |
| GET | `/api/v1/jobs` | 200 |  |
| POST | `/api/v1/jobs` | 400 |  |
| PUT | `/api/v1/jobs/{id}` | 400 |  |
| PATCH | `/api/v1/jobs/{id}/status` | 400 |  |
| GET | `/api/v1/onboarding/templates` | 200 |  |
| POST | `/api/v1/public/careers/{slug}/apply` | 400 |  |

**Not Working / Not Deployed (51 endpoints):**

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | `/api/v1/ai/batch-score` | 404 | missing_404 |
| GET | `/api/v1/ai/rankings/{jobId}` | 404 | missing_404 |
| POST | `/api/v1/ai/score-resume` | 404 | missing_404 |
| GET | `/api/v1/ai/skills/{candidateId}` | 404 | missing_404 |
| GET | `/api/v1/applications/{id}` | 500 | server_error |
| GET | `/api/v1/applications/{id}/timeline` | 500 | server_error |
| POST | `/api/v1/assessments` | 404 | missing_404 |
| GET | `/api/v1/assessments/{id}` | 404 | missing_404 |
| POST | `/api/v1/assessments/{id}/submit` | 404 | missing_404 |
| POST | `/api/v1/background-checks` | 404 | missing_404 |
| GET | `/api/v1/background-checks/{id}` | 404 | missing_404 |
| GET | `/api/v1/candidates/compare` | 500 | server_error |
| GET | `/api/v1/candidates/{id}` | 500 | server_error |
| POST | `/api/v1/candidates/{id}/resume` | 500 | server_error |
| GET | `/api/v1/interviews/{id}` | 404 | missing_404 |
| PUT | `/api/v1/interviews/{id}` | 404 | missing_404 |
| GET | `/api/v1/interviews/{id}/calendar-links` | 404 | missing_404 |
| POST | `/api/v1/interviews/{id}/generate-meet` | 404 | missing_404 |
| DELETE | `/api/v1/interviews/{id}/recordings` | 404 | missing_404 |
| POST | `/api/v1/interviews/{id}/recordings/{recId}/transcribe` | 404 | missing_404 |
| ... | *31 more* | | |

### EMP Performance
- **API Base**: `https://test-performance-api.empcloud.com`
- **Prefix**: `/api/v1/`
- **Auth**: SSO only
- **Needs SSO**: Yes

**Verified Working (54 endpoints):**

| Method | Path | Status | Response Keys |
|--------|------|--------|---------------|
| GET | `/api/v1/analytics/goal-completion` | 200 |  |
| GET | `/api/v1/analytics/overview` | 200 |  |
| GET | `/api/v1/analytics/ratings-distribution` | 400 |  |
| GET | `/api/v1/analytics/team-comparison` | 200 |  |
| GET | `/api/v1/analytics/top-performers` | 400 |  |
| GET | `/api/v1/analytics/trends` | 200 |  |
| POST | `/api/v1/auth/sso` | 400 |  |
| GET | `/api/v1/career-paths` | 200 |  |
| POST | `/api/v1/career-paths` | 400 |  |
| POST | `/api/v1/career-paths/{id}/levels` | 400 |  |
| GET | `/api/v1/competency-frameworks` | 200 |  |
| POST | `/api/v1/competency-frameworks` | 400 |  |
| GET | `/api/v1/competency-frameworks/{id}` | 400 |  |
| POST | `/api/v1/competency-frameworks/{id}/competencies` | 400 |  |
| GET | `/api/v1/feedback` | 200 |  |
| POST | `/api/v1/feedback` | 400 |  |
| GET | `/api/v1/goals` | 200 |  |
| POST | `/api/v1/goals` | 400 |  |
| GET | `/api/v1/goals/{id}` | 400 |  |
| PUT | `/api/v1/goals/{id}` | 400 |  |
| POST | `/api/v1/goals/{id}/check-in` | 400 |  |
| POST | `/api/v1/goals/{id}/key-results` | 400 |  |
| POST | `/api/v1/letters/generate` | 400 |  |
| POST | `/api/v1/letters/{id}/send` | 400 |  |
| GET | `/api/v1/manager-effectiveness` | 400 |  |
| GET | `/api/v1/manager-effectiveness/{managerId}` | 400 |  |
| GET | `/api/v1/notifications/settings` | 200 |  |
| PUT | `/api/v1/notifications/settings` | 200 |  |
| GET | `/api/v1/one-on-ones` | 200 |  |
| POST | `/api/v1/one-on-ones` | 400 |  |
| POST | `/api/v1/one-on-ones/{id}/agenda-items` | 400 |  |
| POST | `/api/v1/peer-reviews/nominate` | 400 |  |
| GET | `/api/v1/peer-reviews/nominations` | 400 |  |
| GET | `/api/v1/pips` | 200 |  |
| POST | `/api/v1/pips` | 400 |  |
| GET | `/api/v1/pips/{id}` | 400 |  |
| POST | `/api/v1/pips/{id}/close` | 400 |  |
| POST | `/api/v1/pips/{id}/objectives` | 400 |  |
| POST | `/api/v1/pips/{id}/updates` | 400 |  |
| GET | `/api/v1/review-cycles` | 200 |  |
| POST | `/api/v1/review-cycles` | 400 |  |
| GET | `/api/v1/review-cycles/{id}` | 400 |  |
| PUT | `/api/v1/review-cycles/{id}` | 400 |  |
| POST | `/api/v1/review-cycles/{id}/close` | 400 |  |
| POST | `/api/v1/review-cycles/{id}/launch` | 400 |  |
| POST | `/api/v1/review-cycles/{id}/participants` | 400 |  |
| GET | `/api/v1/review-cycles/{id}/ratings-distribution` | 400 |  |
| GET | `/api/v1/reviews` | 200 |  |
| GET | `/api/v1/reviews/{id}` | 400 |  |
| PUT | `/api/v1/reviews/{id}` | 400 |  |
| POST | `/api/v1/reviews/{id}/submit` | 400 |  |
| GET | `/api/v1/succession-plans` | 200 |  |
| POST | `/api/v1/succession-plans` | 400 |  |
| POST | `/api/v1/succession-plans/{id}/candidates` | 400 |  |

**Not Working / Not Deployed (33 endpoints):**

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | `/api/v1/ai-summary/cycle/{cycleId}` | 404 | missing_404 |
| POST | `/api/v1/ai-summary/review/{reviewId}` | 404 | missing_404 |
| POST | `/api/v1/ai-summary/team/{managerId}` | 404 | missing_404 |
| GET | `/api/v1/ai-summary/{id}` | 404 | missing_404 |
| GET | `/api/v1/career-paths/{id}` | 404 | missing_404 |
| GET | `/api/v1/employees/{id}/career-track` | 404 | missing_404 |
| PUT | `/api/v1/employees/{id}/career-track` | 404 | missing_404 |
| GET | `/api/v1/feedback/{id}` | 404 | missing_404 |
| POST | `/api/v1/goal-alignment/link` | 404 | missing_404 |
| DELETE | `/api/v1/goal-alignment/link/{id}` | 404 | missing_404 |
| GET | `/api/v1/goal-alignment/rollup/{goalId}` | 404 | missing_404 |
| GET | `/api/v1/goal-alignment/tree` | 404 | missing_404 |
| GET | `/api/v1/letter-templates` | 404 | missing_404 |
| POST | `/api/v1/letter-templates` | 404 | missing_404 |
| PUT | `/api/v1/letter-templates/{id}` | 404 | missing_404 |
| GET | `/api/v1/letters/{id}/download` | 404 | missing_404 |
| POST | `/api/v1/manager-effectiveness/calculate` | 404 | missing_404 |
| GET | `/api/v1/manager-effectiveness/{managerId}/trends` | 404 | missing_404 |
| GET | `/api/v1/nine-box` | 404 | missing_404 |
| GET | `/api/v1/nine-box/history/{employeeId}` | 404 | missing_404 |
| ... | *13 more* | | |

### EMP Rewards
- **API Base**: `https://test-rewards-api.empcloud.com`
- **Prefix**: `/api/v1/`
- **Auth**: SSO only
- **Needs SSO**: Yes

**Verified Working (39 endpoints):**

| Method | Path | Status | Response Keys |
|--------|------|--------|---------------|
| GET | `/api/v1/badges` | 200 |  |
| POST | `/api/v1/badges` | 400 |  |
| POST | `/api/v1/badges/award` | 400 |  |
| GET | `/api/v1/badges/my` | 200 |  |
| GET | `/api/v1/celebrations/feed` | 200 |  |
| POST | `/api/v1/celebrations/{id}/wish` | 400 |  |
| GET | `/api/v1/challenges` | 200 |  |
| POST | `/api/v1/challenges` | 400 |  |
| POST | `/api/v1/kudos` | 400 |  |
| GET | `/api/v1/kudos` | 200 |  |
| GET | `/api/v1/kudos/received` | 200 |  |
| GET | `/api/v1/kudos/sent` | 200 |  |
| POST | `/api/v1/kudos/{id}/comments` | 400 |  |
| POST | `/api/v1/kudos/{id}/reactions` | 400 |  |
| GET | `/api/v1/leaderboard` | 200 |  |
| GET | `/api/v1/leaderboard/department/{deptId}` | 200 |  |
| GET | `/api/v1/leaderboard/my-rank` | 200 |  |
| GET | `/api/v1/milestones/rules` | 200 |  |
| POST | `/api/v1/milestones/rules` | 400 |  |
| POST | `/api/v1/nominations` | 400 |  |
| GET | `/api/v1/nominations/programs` | 200 |  |
| POST | `/api/v1/nominations/programs` | 400 |  |
| PUT | `/api/v1/nominations/{id}/review` | 400 |  |
| POST | `/api/v1/points/adjust` | 400 |  |
| GET | `/api/v1/points/balance` | 200 |  |
| GET | `/api/v1/points/transactions` | 200 |  |
| POST | `/api/v1/push/subscribe` | 400 |  |
| POST | `/api/v1/push/test` | 400 |  |
| POST | `/api/v1/push/unsubscribe` | 400 |  |
| GET | `/api/v1/redemptions` | 200 |  |
| GET | `/api/v1/redemptions/my` | 200 |  |
| PUT | `/api/v1/redemptions/{id}/approve` | 400 |  |
| PUT | `/api/v1/redemptions/{id}/fulfill` | 400 |  |
| GET | `/api/v1/rewards` | 200 |  |
| POST | `/api/v1/rewards` | 400 |  |
| POST | `/api/v1/rewards/{id}/redeem` | 400 |  |
| GET | `/api/v1/slack/config` | 200 |  |
| PUT | `/api/v1/slack/config` | 200 |  |
| POST | `/api/v1/slack/test` | 400 |  |

**Not Working / Not Deployed (17 endpoints):**

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/api/v1/celebrations` | 404 | missing_404 |
| GET | `/api/v1/challenges/{id}` | 404 | missing_404 |
| POST | `/api/v1/challenges/{id}/complete` | 404 | missing_404 |
| POST | `/api/v1/challenges/{id}/join` | 404 | missing_404 |
| GET | `/api/v1/challenges/{id}/progress` | 404 | missing_404 |
| GET | `/api/v1/kudos/{id}` | 404 | missing_404 |
| DELETE | `/api/v1/kudos/{id}` | 404 | missing_404 |
| GET | `/api/v1/manager/dashboard` | 404 | missing_404 |
| GET | `/api/v1/manager/recommendations` | 404 | missing_404 |
| GET | `/api/v1/manager/team-comparison` | 404 | missing_404 |
| GET | `/api/v1/milestones/history` | 404 | missing_404 |
| PUT | `/api/v1/milestones/rules/{id}` | 404 | missing_404 |
| GET | `/api/v1/push/vapid-key` | 503 | server_error |
| POST | `/api/v1/slack/slash-command` | 404 | missing_404 |
| GET | `/api/v1/teams` | 404 | missing_404 |
| PUT | `/api/v1/teams` | 404 | missing_404 |
| POST | `/api/v1/teams/test` | 404 | missing_404 |

### EMP Exit
- **API Base**: `https://test-exit-api.empcloud.com`
- **Prefix**: `/api/v1/`
- **Auth**: SSO only
- **Needs SSO**: Yes

**Verified Working (12 endpoints):**

| Method | Path | Status | Response Keys |
|--------|------|--------|---------------|
| POST | `/api/v1/exits` | 400 |  |
| GET | `/api/v1/exits` | 200 |  |
| POST | `/api/v1/predictions/calculate` | 200 |  |
| GET | `/api/v1/predictions/dashboard` | 200 |  |
| GET | `/api/v1/predictions/employee/{employeeId}` | 200 |  |
| GET | `/api/v1/predictions/high-risk` | 200 |  |
| GET | `/api/v1/predictions/trends` | 200 |  |
| GET | `/api/v1/rehire` | 200 |  |
| POST | `/api/v1/rehire` | 400 |  |
| GET | `/api/v1/self-service/my-checklist` | 200 |  |
| GET | `/api/v1/self-service/my-exit` | 200 |  |
| POST | `/api/v1/self-service/resign` | 400 |  |

**Not Working / Not Deployed (50 endpoints):**

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/api/v1/checklist-templates` | 404 | missing_404 |
| POST | `/api/v1/checklist-templates` | 404 | missing_404 |
| PUT | `/api/v1/checklist-templates/{id}` | 404 | missing_404 |
| POST | `/api/v1/checklist-templates/{id}/items` | 404 | missing_404 |
| GET | `/api/v1/clearance-departments` | 404 | missing_404 |
| GET | `/api/v1/email-templates` | 404 | missing_404 |
| PUT | `/api/v1/email-templates/{stage}` | 404 | missing_404 |
| POST | `/api/v1/email-templates/{stage}/preview` | 404 | missing_404 |
| GET | `/api/v1/exits/{id}` | 404 | missing_404 |
| PUT | `/api/v1/exits/{id}` | 404 | missing_404 |
| GET | `/api/v1/exits/{id}/assets` | 404 | missing_404 |
| POST | `/api/v1/exits/{id}/assets` | 404 | missing_404 |
| PUT | `/api/v1/exits/{id}/assets/{assetId}` | 404 | missing_404 |
| GET | `/api/v1/exits/{id}/buyout` | 404 | missing_404 |
| PUT | `/api/v1/exits/{id}/buyout/approve` | 404 | missing_404 |
| POST | `/api/v1/exits/{id}/buyout/calculate` | 404 | missing_404 |
| POST | `/api/v1/exits/{id}/buyout/request` | 404 | missing_404 |
| POST | `/api/v1/exits/{id}/cancel` | 404 | missing_404 |
| GET | `/api/v1/exits/{id}/clearance` | 404 | missing_404 |
| PUT | `/api/v1/exits/{id}/clearance/{clearanceId}` | 404 | missing_404 |
| ... | *30 more* | | |

### EMP LMS
- **API Base**: `https://testlms-api.empcloud.com`
- **Prefix**: `/api/v1/`
- **Auth**: SSO preferred (also has /login)
- **Needs SSO**: Yes

**Verified Working (17 endpoints):**

| Method | Path | Status | Response Keys |
|--------|------|--------|---------------|
| POST | `/api/v1/auth/login` | 400 |  |
| POST | `/api/v1/auth/sso` | 400 |  |
| POST | `/api/v1/certificates/issue` | 400 |  |
| GET | `/api/v1/certificates/my` | 200 |  |
| GET | `/api/v1/courses` | 200 |  |
| POST | `/api/v1/courses` | 422 |  |
| GET | `/api/v1/discussions` | 400 |  |
| POST | `/api/v1/discussions` | 422 |  |
| POST | `/api/v1/enrollments` | 422 |  |
| POST | `/api/v1/enrollments/bulk` | 422 |  |
| GET | `/api/v1/enrollments/my` | 200 |  |
| GET | `/api/v1/gamification/leaderboard` | 200 |  |
| GET | `/api/v1/learning-paths` | 200 |  |
| POST | `/api/v1/learning-paths` | 400 |  |
| GET | `/api/v1/ratings` | 400 |  |
| POST | `/api/v1/ratings` | 422 |  |
| POST | `/api/v1/scorm/upload` | 400 |  |

**Not Working / Not Deployed (25 endpoints):**

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/api/v1/certificates/{id}/download` | 404 | missing_404 |
| GET | `/api/v1/certificates/{id}/verify` | 404 | missing_404 |
| POST | `/api/v1/compliance/assign` | 404 | missing_404 |
| GET | `/api/v1/compliance/dashboard` | 500 | server_error |
| GET | `/api/v1/compliance/my` | 404 | missing_404 |
| GET | `/api/v1/compliance/overdue` | 404 | missing_404 |
| GET | `/api/v1/courses/{id}` | 404 | missing_404 |
| PUT | `/api/v1/courses/{id}` | 404 | missing_404 |
| DELETE | `/api/v1/courses/{id}` | 404 | missing_404 |
| POST | `/api/v1/discussions/{id}/replies` | 404 | missing_404 |
| PUT | `/api/v1/enrollments/{id}/progress` | 404 | missing_404 |
| GET | `/api/v1/gamification/badges` | 404 | missing_404 |
| GET | `/api/v1/gamification/my` | 404 | missing_404 |
| GET | `/api/v1/ilt` | 404 | missing_404 |
| POST | `/api/v1/ilt` | 404 | missing_404 |
| POST | `/api/v1/ilt/{id}/attendance` | 404 | missing_404 |
| POST | `/api/v1/ilt/{id}/register` | 404 | missing_404 |
| GET | `/api/v1/learning-paths/{id}` | 404 | missing_404 |
| POST | `/api/v1/learning-paths/{id}/enroll` | 404 | missing_404 |
| POST | `/api/v1/quizzes/attempt` | 404 | missing_404 |
| ... | *5 more* | | |

### EMP Project
- **API Base**: `https://test-project-api.empcloud.com`
- **Prefix**: `/v1/`
- **Auth**: Separate
- **Needs SSO**: Yes

*No endpoint test data available for this module.*

### EMP Monitor
- **API Base**: `https://test-empmonitor-api.empcloud.com`
- **Prefix**: `N/A`
- **Auth**: Separate (Laravel + Node.js)
- **Needs SSO**: No

*No endpoint test data available for this module.*

### README vs Reality Summary

| Module | README Endpoints | Working | Missing (404) | Broken (500) | Auth Errors | Coverage |
|--------|-----------------|---------|---------------|--------------|-------------|----------|
| core | 33 | 13 | 19 | 0 | 1 | 39.4% |
| payroll | 122 | 10 | 46 | 2 | 36 | 8.2% |
| recruit | 72 | 21 | 35 | 11 | 5 | 29.2% |
| performance | 87 | 54 | 33 | 0 | 0 | 62.1% |
| rewards | 56 | 39 | 16 | 1 | 0 | 69.6% |
| exit | 62 | 12 | 50 | 0 | 0 | 19.4% |
| lms | 42 | 17 | 24 | 1 | 0 | 40.5% |
| billing | 0 | 0 | 0 | 0 | 0 | 0.0% |
| project | 0 | 0 | 0 | 0 | 0 | 0.0% |
| monitor | 0 | 0 | 0 | 0 | 0 | 0.0% |

---
## B. Module Feature Matrix

### EMP Cloud Core

| Feature | In README | API Exists | UI Works | Admin | Employee |
|---------|-----------|-----------|----------|-------|----------|
| Auth | Yes | Yes | Yes | Yes | Yes |
| OAuth/OIDC | Yes | Yes | Yes | Yes | No |
| Organizations | Yes | Yes | Yes | Yes | No |
| Users/Employees | Yes | Yes | Yes | Yes | Yes |
| Attendance | Yes | Yes | Yes | Yes | Yes |
| Leave Management | Yes | Yes | Yes | Yes | Yes |
| Documents | Yes | Yes | Yes | Yes | Yes |
| Announcements | Yes | Yes | Yes | Yes | Yes |
| Policies | Yes | Yes | Yes | Yes | Yes |
| Notifications | Yes | Yes | Yes | Yes | Yes |
| Dashboard | Yes | Yes | Yes | Yes | Yes |
| Helpdesk | Yes | Yes | Yes | Yes | Yes |
| Surveys | Yes | Yes | Yes | Yes | Yes |
| Assets | Yes | Yes | Yes | Yes | Yes |
| Positions | Yes | Yes | Yes | Yes | No |
| Forum | Yes | Yes | Yes | Yes | Yes |
| Events | Yes | Yes | Yes | Yes | Yes |
| Wellness | Yes | No | No | No | No |
| Feedback | Yes | Yes | Yes | Yes | Yes |
| Whistleblowing | Yes | No | No | No | No |
| Custom Fields | Yes | No | No | No | No |
| Biometrics | Yes | No | No | No | No |
| Manager Dashboard | Yes | No | No | No | No |
| Bulk Import | Yes | No | No | No | No |
| AI Chatbot | Yes | No | Yes | Yes | Yes |
| AI Config | Yes | No | Yes | Yes | No |
| Audit Log | Yes | Yes | Yes | Yes | No |
| Billing | Yes | No | Yes | Yes | No |
| Org Chart | Yes | Yes | Yes | Yes | Yes |
| Admin Health | Yes | Yes | Yes | Yes | No |

### EMP Payroll

| Feature | In README | API Exists | UI Works | Admin | Employee |
|---------|-----------|-----------|----------|-------|----------|
| Auth/Login | Yes | Yes | Yes | Yes | Yes |
| Employee Management | Yes | Yes | Yes | Yes | No |
| Payroll Runs | Yes | Yes | Yes | Yes | No |
| Payslips | Yes | Yes | Yes | Yes | Yes |
| Salary Structures | Yes | Yes | Yes | Yes | No |
| Benefits | Yes | Yes | No | Yes | Yes |
| Insurance | Yes | Yes | No | Yes | No |
| GL Accounting | Yes | No | No | No | No |
| Global Payroll | Yes | No | No | No | No |
| Earned Wage Access | Yes | No | No | No | No |
| Pay Equity | Yes | No | No | No | No |
| Compensation Benchmarks | Yes | No | No | No | No |
| Self-Service | Yes | Yes | Yes | No | Yes |
| Tax Engine | Yes | Yes | Yes | Yes | Yes |
| Loans | Yes | No | No | No | No |
| Reimbursements | Yes | No | No | No | No |

### EMP Recruit

| Feature | In README | API Exists | UI Works | Admin | Employee |
|---------|-----------|-----------|----------|-------|----------|
| SSO Auth | Yes | Yes | Yes | Yes | No |
| Job Postings | Yes | Yes | Yes | Yes | No |
| Candidates | Yes | Yes | Yes | Yes | No |
| Applications/ATS | Yes | Yes | Yes | Yes | No |
| Interviews | Yes | Yes | Yes | Yes | No |
| Offers | Yes | Yes | Yes | Yes | No |
| AI Resume Scoring | Yes | Yes | No | Yes | No |
| Background Checks | Yes | Yes | No | Yes | No |
| Pipeline Stages | Yes | Yes | Yes | Yes | No |
| Candidate Portal | Yes | Yes | No | No | No |
| Onboarding | Yes | Yes | No | Yes | No |
| Public Career Page | Yes | Yes | No | No | No |
| Psychometric Assessments | Yes | Yes | No | Yes | No |

### EMP Performance

| Feature | In README | API Exists | UI Works | Admin | Employee |
|---------|-----------|-----------|----------|-------|----------|
| SSO Auth | Yes | Yes | Yes | Yes | No |
| Review Cycles | Yes | Yes | Yes | Yes | Yes |
| Goals & OKRs | Yes | Yes | Yes | Yes | Yes |
| Goal Alignment | Yes | Yes | No | Yes | No |
| 9-Box Grid | Yes | Yes | Yes | Yes | No |
| Succession Planning | Yes | Yes | No | Yes | No |
| Skills Gap Analysis | Yes | Yes | No | Yes | Yes |
| Manager Effectiveness | Yes | Yes | No | Yes | No |
| AI Review Summaries | Yes | Yes | No | Yes | No |
| Performance Letters | Yes | Yes | No | Yes | No |
| Competency Frameworks | Yes | Yes | No | Yes | No |
| PIPs | Yes | Yes | Yes | Yes | Yes |
| Career Paths | Yes | Yes | No | Yes | Yes |
| 1-on-1 Meetings | Yes | Yes | No | Yes | Yes |
| Continuous Feedback | Yes | Yes | No | Yes | Yes |
| Peer Reviews | Yes | Yes | No | Yes | Yes |
| Analytics | Yes | Yes | No | Yes | No |

### EMP Rewards

| Feature | In README | API Exists | UI Works | Admin | Employee |
|---------|-----------|-----------|----------|-------|----------|
| Kudos | Yes | Yes | Yes | Yes | Yes |
| Points | Yes | Yes | Yes | Yes | Yes |
| Badges | Yes | Yes | Yes | Yes | Yes |
| Rewards Catalog | Yes | Yes | No | Yes | Yes |
| Redemptions | Yes | Yes | No | Yes | Yes |
| Nominations | Yes | Yes | No | Yes | Yes |
| Leaderboard | Yes | Yes | Yes | Yes | Yes |
| Celebrations | Yes | Yes | Yes | Yes | Yes |
| Team Challenges | Yes | Yes | No | Yes | Yes |
| Milestones | Yes | Yes | No | Yes | No |
| Slack Integration | Yes | Yes | No | Yes | No |
| Teams Integration | Yes | Yes | No | Yes | No |
| Push Notifications | Yes | Yes | No | Yes | Yes |

### EMP Exit

| Feature | In README | API Exists | UI Works | Admin | Employee |
|---------|-----------|-----------|----------|-------|----------|
| Exit Requests | Yes | Yes | Yes | Yes | No |
| Self-Service Resignation | Yes | Yes | Yes | No | Yes |
| Checklist Templates | Yes | Yes | No | Yes | No |
| Clearance | Yes | Yes | No | Yes | No |
| Exit Interviews | Yes | Yes | No | Yes | Yes |
| F&F Settlement | Yes | Yes | No | Yes | No |
| Asset Returns | Yes | Yes | No | Yes | No |
| Knowledge Transfer | Yes | Yes | No | Yes | Yes |
| Letters | Yes | Yes | No | Yes | No |
| Flight Risk / Attrition | Yes | Yes | No | Yes | No |
| Notice Buyout | Yes | Yes | No | Yes | Yes |
| Rehire | Yes | Yes | No | Yes | No |
| NPS | Yes | Yes | No | Yes | No |

### EMP LMS

| Feature | In README | API Exists | UI Works | Admin | Employee |
|---------|-----------|-----------|----------|-------|----------|
| Auth (SSO + Login) | Yes | Yes | Yes | Yes | Yes |
| Courses | Yes | Yes | Yes | Yes | Yes |
| Enrollments | Yes | Yes | Yes | Yes | Yes |
| Quizzes | Yes | Yes | No | Yes | Yes |
| Learning Paths | Yes | Yes | No | Yes | Yes |
| Certifications | Yes | Yes | No | Yes | Yes |
| Compliance | Yes | Yes | No | Yes | Yes |
| ILT Sessions | Yes | Yes | No | Yes | Yes |
| SCORM | Yes | Yes | No | Yes | Yes |
| Gamification | Yes | Yes | No | Yes | Yes |
| Discussions | Yes | Yes | No | Yes | Yes |
| Analytics | Yes | Yes | No | Yes | No |
| AI Recommendations | Yes | Yes | No | Yes | Yes |
| Video | Yes | Yes | No | Yes | Yes |

---
## C. Known Working Flows

### 1. Admin Login + Token

1. `POST /api/v1/auth/login with {email: 'ananya@technova.in', password: 'Welcome@123'}`
2. `Response: {success: true, data: {access_token: '...', user: {...}}}`
3. `Use access_token in Authorization: Bearer header for subsequent requests`

**Notes:** Works for all user roles. Token expires in 15 minutes.

### 2. Employee Directory + Profile

1. `GET /api/v1/users (returns paginated user list with meta)`
2. `GET /api/v1/users/:id (individual user details)`
3. `GET /api/v1/employees/:id/profile (extended profile)`
4. `GET /api/v1/employees/:id/addresses (address list)`
5. `GET /api/v1/employees/:id/education (education history)`
6. `GET /api/v1/employees/:id/experience (work experience)`
7. `GET /api/v1/employees/:id/dependents (dependents list)`

**Notes:** Note: /api/v1/employees (list) returns 404 -- use /api/v1/users instead. Org chart at /api/v1/users/org-chart (NOT /employees/org-chart).

### 3. Attendance Check-in/Check-out

1. `POST /api/v1/attendance/check-in (returns 200 or 409 if already checked in)`
2. `GET /api/v1/attendance/records (list with pagination)`
3. `GET /api/v1/attendance/dashboard (dashboard data)`
4. `POST /api/v1/attendance/check-out (returns 200 or 409 if already checked out)`

**Notes:** 409 Conflict is expected when already checked in/out for the day.

### 4. Leave Application + Approval

1. `GET /api/v1/leave/types (list leave types with IDs)`
2. `GET /api/v1/leave/balances (check available balance)`
3. `POST /api/v1/leave/applications {leave_type_id, start_date, end_date, reason}`
4. `GET /api/v1/leave/applications (list all applications)`
5. `POST /api/v1/leave/applications/:id/approve (admin approves)`

**Notes:** Leave types vary by org. TechNova has Casual, Sick, Earned, Compensatory, Maternity, Paternity.

### 5. Helpdesk Ticket Lifecycle

1. `GET /api/v1/helpdesk/categories (list categories)`
2. `POST /api/v1/helpdesk/tickets {subject, description, category_id, priority}`
3. `GET /api/v1/helpdesk/tickets (list all)`
4. `GET /api/v1/helpdesk/tickets/:id (detail)`
5. `PUT /api/v1/helpdesk/tickets/:id {status: 'in_progress'} (update status)`
6. `PUT /api/v1/helpdesk/tickets/:id {status: 'resolved'} (close ticket)`

**Notes:** 80% resolution rate observed in simulation. Knowledge base articles also available.

### 6. SSO Into External Module (Payroll Example)

1. `POST /api/v1/auth/login on test-empcloud-api.empcloud.com -> get access_token`
2. `Navigate browser to: https://testpayroll.empcloud.com?sso_token=<access_token>`
3. `Module reads token from URL and authenticates`
4. `For API: capture module session cookie from redirect response`

**Notes:** Token lifetime is 15 minutes. Same pattern for all modules (recruit, performance, rewards, exit, lms, project).

### 7. Payroll Self-Service (Employee View)

1. `SSO into payroll module`
2. `GET /api/v1/self-service/payslips (my payslips)`
3. `GET /api/v1/self-service/payslips/:id/pdf (download payslip)`
4. `GET /api/v1/self-service/salary (my salary)`
5. `GET /api/v1/self-service/tax/declarations (my declarations)`
6. `GET /api/v1/self-service/tax/form16 (form 16)`

**Notes:** Employee role in payroll module has limited access (most admin endpoints return 403).

### 8. Announcement CRUD

1. `POST /api/v1/announcements {title, content, priority, target_type: 'all'}`
2. `GET /api/v1/announcements (list, paginated)`
3. `GET /api/v1/announcements/:id (detail)`
4. `PUT /api/v1/announcements/:id (update)`
5. `POST /api/v1/announcements/:id/read (mark as read)`
6. `GET /api/v1/announcements/unread-count (count)`

**Notes:** Admin creates, employees read. Soft delete is by design.

### 9. Policy + Acknowledgment

1. `POST /api/v1/policies {title, content, category}`
2. `GET /api/v1/policies (list)`
3. `GET /api/v1/policies/pending (pending acknowledgments)`
4. `POST /api/v1/policies/:id/acknowledge (employee acknowledges)`

**Notes:** 23 pending acknowledgments in TechNova as of simulation.

### 10. Forum Post + Reply

1. `GET /api/v1/forum/categories (list categories)`
2. `POST /api/v1/forum/categories {name, description} (admin creates)`
3. `POST /api/v1/forum/posts {title, content, category_id}`
4. `GET /api/v1/forum/posts (list with pagination)`
5. `GET /api/v1/forum/posts/:id (with replies)`
6. `POST /api/v1/forum/posts/:id/replies {content}`
7. `POST /api/v1/forum/posts/:id/react {type: 'like'}`

**Notes:** 19 posts in TechNova simulation.

### 11. Survey Creation + Response

1. `POST /api/v1/surveys {title, description, type, is_anonymous, questions: [...]}`
2. `GET /api/v1/surveys (list)`
3. `GET /api/v1/surveys/:id (with responses)`
4. `POST /api/v1/surveys/:id/respond {answers: [...]}`

**Notes:** 20 surveys in TechNova. Supports engagement, pulse, and custom types.

### 12. Asset Management

1. `GET /api/v1/assets/categories (list categories)`
2. `POST /api/v1/assets {name, asset_tag, category_id, serial_number}`
3. `GET /api/v1/assets (list)`
4. `POST /api/v1/assets/:id/assign {user_id}`
5. `GET /api/v1/assets/my (employee: my assigned assets)`

**Notes:** Asset tracking with categories, serial numbers, warranty tracking.

### 13. Events CRUD + Registration

1. `POST /api/v1/events {title, description, event_type, start_date, end_date, location}`
2. `GET /api/v1/events (list)`
3. `POST /api/v1/events/:id/register (RSVP)`

**Notes:** 14 events in TechNova. Calendar endpoint requires date params.

---
## D. Known Broken Flows

### 1. Payroll Run by Org Admin
- **Broken Step:** `POST /api/v1/payroll (create payroll run)`
- **Error:** Org admin SSO token maps to 'employee' role in payroll module, returning 403 Forbidden
- **Issue:** #722 - Org admin can't run payroll -- role mapped as 'employee' in payroll module
- **Workaround:** Use payroll's native auth (POST /api/v1/auth/login) with admin credentials if available

### 2. Payroll Run for Innovate Solutions
- **Broken Step:** `POST /api/v1/payroll for org_id 39`
- **Error:** Payroll run fails for Innovate Solutions organization
- **Issue:** #727 - Payroll run fails for Innovate Solutions - March 2026
- **Workaround:** None known -- only TechNova payroll runs have succeeded

### 3. SSO Validate Endpoint
- **Broken Step:** `POST /api/v1/auth/sso/validate`
- **Error:** Returns 404 Not Found
- **Issue:** Endpoint listed in README but not found on API. Modules may use direct sso_token URL param instead.
- **Workaround:** Use sso_token as URL parameter (e.g., ?sso_token=<token>) instead of API validate call

### 4. Password Reset
- **Broken Step:** `POST /api/v1/auth/password-reset`
- **Error:** Returns 404 Not Found
- **Issue:** Endpoint listed in README but not deployed
- **Workaround:** None -- use known passwords for testing

### 5. Wellness Module
- **Broken Step:** `GET /api/v1/wellness/*`
- **Error:** Returns 404 -- wellness endpoints not deployed
- **Issue:** All wellness endpoints (/dashboard, /check-in, /goals) return 404
- **Workaround:** Skip wellness testing -- APIs not implemented yet

### 6. Whistleblowing Module
- **Broken Step:** `GET /api/v1/whistleblowing`
- **Error:** Returns 404 -- endpoints not deployed
- **Issue:** Listed in README but returns 404
- **Workaround:** Skip whistleblowing testing

### 7. Custom Fields
- **Broken Step:** `GET /api/v1/custom-fields/definitions`
- **Error:** Returns 404
- **Issue:** Custom fields endpoints not deployed
- **Workaround:** Skip custom fields testing

### 8. Bulk Leave Approve/Reject
- **Broken Step:** `POST /api/v1/leave/bulk-approve`
- **Error:** Returns 404
- **Issue:** Bulk approve/reject endpoints not deployed
- **Workaround:** Approve/reject individually via POST /api/v1/leave/applications/:id/approve

### 9. Leave Dashboard
- **Broken Step:** `GET /api/v1/leave/dashboard`
- **Error:** Returns 404
- **Issue:** Leave dashboard endpoint not deployed
- **Workaround:** Use /api/v1/leave/balances and /api/v1/leave/applications separately

### 10. Attendance Reports/Export
- **Broken Step:** `GET /api/v1/attendance/reports and /export`
- **Error:** Returns 404
- **Issue:** Report and export endpoints not deployed
- **Workaround:** Use /api/v1/attendance/records with date filters

### 11. Attendance Shift Assignments
- **Broken Step:** `GET /api/v1/attendance/shift-assignments`
- **Error:** Returns 404
- **Issue:** Shift assignment listing endpoint not deployed
- **Workaround:** Shifts themselves work (GET /api/v1/attendance/shifts)

### 12. Document Upload
- **Broken Step:** `POST /api/v1/documents`
- **Error:** Returns 404 for POST
- **Issue:** Document upload endpoint not responding to POST
- **Workaround:** Documents can be read via GET /api/v1/documents

### 13. Payroll GL Accounting
- **Broken Step:** `All /api/v1/gl-accounting/* endpoints`
- **Error:** Returns 404 (Cannot GET/POST)
- **Issue:** GL accounting module not deployed in payroll
- **Workaround:** None -- skip GL accounting tests

### 14. Payroll Global Payroll
- **Broken Step:** `All /api/v1/global-payroll/* endpoints`
- **Error:** Returns 404
- **Issue:** Global payroll module not deployed
- **Workaround:** None -- skip global payroll tests

### 15. Payroll Earned Wage Access
- **Broken Step:** `All /api/v1/earned-wage/* endpoints`
- **Error:** Returns 404
- **Issue:** EWA module not deployed
- **Workaround:** None -- skip EWA tests

---
## E. Optimal Test Suite

### Smoke Tests
*Run FIRST -- verifies basic connectivity and auth*
**Estimated time:** 30 seconds

- **Health Check**: `GET /health` -> expect 200
- **Admin Login**: `POST /api/v1/auth/login (ananya@technova.in)` -> expect 200
- **Employee Login**: `POST /api/v1/auth/login (priya@technova.in)` -> expect 200
- **Super Admin Login**: `POST /api/v1/auth/login (admin@empcloud.com)` -> expect 200
- **List Users**: `GET /api/v1/users` -> expect 200
- **Org Info**: `GET /api/v1/organizations/me` -> expect 200
- **Swagger Docs**: `GET /api/docs` -> expect 200
- **OIDC Discovery**: `GET /.well-known/openid-configuration` -> expect 200

### Core Regression
*Core HRMS module regression tests*
**Estimated time:** 3-5 minutes

- **Departments CRUD** (core): `GET /organizations/me/departments`, `POST /organizations/me/departments`
- **Locations CRUD** (core): `GET /organizations/me/locations`, `POST /organizations/me/locations`
- **User Profile** (core): `GET /users/:id`, `PUT /users/:id`, `GET /employees/:id/profile`
- **Attendance Flow** (core): `POST /attendance/check-in`, `GET /attendance/records`, `POST /attendance/check-out`
- **Leave Flow** (core): `GET /leave/types`, `GET /leave/balances`, `POST /leave/applications`, `POST /leave/applications/:id/approve`
- **Announcements** (core): `GET /announcements`, `POST /announcements`, `GET /announcements/unread-count`
- **Policies** (core): `GET /policies`, `POST /policies`, `GET /policies/pending`, `POST /policies/:id/acknowledge`
- **Documents** (core): `GET /documents`, `GET /documents/categories`, `GET /documents/my`
- **Helpdesk** (core): `GET /helpdesk/tickets`, `POST /helpdesk/tickets`, `PUT /helpdesk/tickets/:id`
- **Surveys** (core): `GET /surveys`, `POST /surveys/:id/respond`
- **Forum** (core): `GET /forum/categories`, `GET /forum/posts`, `POST /forum/posts`
- **Events** (core): `GET /events`, `POST /events`, `POST /events/:id/register`
- **Assets** (core): `GET /assets`, `POST /assets`, `POST /assets/:id/assign`
- **Notifications** (core): `GET /notifications`, `GET /notifications/unread-count`
- **Feedback** (core): `GET /feedback`, `POST /feedback`
- **Audit Log** (core): `GET /audit`

### Module Regression
*External module tests (require SSO)*
**Estimated time:** 5-10 minutes

- **Payroll SSO + Self-Service** (payroll): `SSO to testpayroll.empcloud.com`, `GET /self-service/payslips`, `GET /self-service/salary`, `GET /salary-structures/employee/:empId`
- **Payroll Admin** (payroll): `GET /payroll (list runs)`, `GET /employees (payroll employees)`, `GET /salary-structures`
- **Recruit SSO + Jobs** (recruit): `POST /auth/sso`, `GET /jobs`, `GET /candidates`, `GET /interviews`
- **Performance SSO + Reviews** (performance): `POST /auth/sso`, `GET /review-cycles`, `GET /goals`, `GET /competency-frameworks`
- **Rewards SSO + Kudos** (rewards): `GET /kudos`, `GET /leaderboard`, `GET /badges`, `GET /celebrations`
- **Exit SSO + Exits** (exit): `GET /exits`, `GET /checklist-templates`, `GET /predictions/dashboard`
- **LMS SSO + Courses** (lms): `POST /auth/sso`, `GET /courses`, `GET /enrollments/my`, `GET /learning-paths`

### Rbac Security
*Role-based access control tests*
**Estimated time:** 2-3 minutes

- **Employee cannot access admin endpoints**:
  - Login as priya@technova.in
  - GET /api/v1/admin/organizations -> expect 403
  - POST /api/v1/organizations/me/departments -> expect 403
  - GET /api/v1/audit -> expect 403 or filtered
- **Org admin cannot see other org data**:
  - Login as ananya@technova.in (TechNova)
  - Try to access GlobalTech user IDs -> expect 404 or empty
- **Super admin has full access**:
  - Login as admin@empcloud.com
  - GET /api/v1/admin/organizations -> expect 200 with all orgs
  - GET /api/v1/admin/health -> expect 200
- **Payroll RBAC via SSO**:
  - SSO as employee -> most admin payroll endpoints return 403
  - SSO as org admin -> currently maps as employee (bug #722)

### Data Integrity
*Data consistency and validation tests*
**Estimated time:** 2-3 minutes

- **Leave balance non-negative**: GET /leave/balances -> all balances >= 0
- **Attendance + Leave = Working Days**: Cross-reference attendance records with leave applications
- **Employee count consistency**: GET /users count matches setup_data expectations
- **Duplicate prevention**: POST /users/invite with existing email -> error
- **Soft delete behavior**: DELETE item -> GET item still returns (by design)
- **Pagination works**: GET /users?page=1&limit=5 -> returns correct count

### Skip List
*Tests to SKIP (known false positives or not ready)*

- **Rate limiting**: All rate limits removed for testing
- **Field Force (emp-field)**: Module not ready for testing
- **Biometrics (emp-biometrics)**: Module not ready for testing
- **Direct subdomain login**: Modules use SSO only, not direct login
- **Soft delete items accessible**: By design for audit trail
- **XSS stored in DB**: React auto-escapes, Knex parameterizes -- not exploitable
- **Wellness endpoints**: All return 404 -- not deployed
- **Whistleblowing endpoints**: All return 404 -- not deployed
- **Custom Fields endpoints**: All return 404 -- not deployed
- **GL Accounting (Payroll)**: All return 404 -- not deployed
- **Global Payroll**: All return 404 -- not deployed
- **Earned Wage Access**: All return 404 -- not deployed
- **Pay Equity**: Not deployed
- **Compensation Benchmarks**: Not deployed
- **EMP Monitor API tests**: Different tech stack (QT/Laravel/Node.js), no standard API

---
## F. Environment Configuration

### URLs
- **App**: https://test-empcloud.empcloud.com
- **API**: https://test-empcloud-api.empcloud.com
- **Swagger**: https://test-empcloud-api.empcloud.com/api/docs

### Credentials

| Role | Email | Password | Org ID |
|------|-------|----------|--------|
| super_admin | admin@empcloud.com | SuperAdmin@2026 | N/A |
| org_admin | ananya@technova.in | Welcome@123 | 5 |
| employee | priya@technova.in | Welcome@123 | 5 |
| org_admin | john@globaltech.com | Welcome@123 | 9 |
| org_admin | hr@innovate.io | Welcome@123 | 39 |

### Module URLs

| Module | Frontend | API | SSO URL Pattern |
|--------|----------|-----|-----------------|
| payroll | https://testpayroll.empcloud.com | https://testpayroll-api.empcloud.com | `https://testpayroll.empcloud.com?sso_token=<JWT>` |
| recruit | https://test-recruit.empcloud.com | https://test-recruit-api.empcloud.com | `https://test-recruit.empcloud.com?sso_token=<JWT>` |
| performance | https://test-performance.empcloud.com | https://test-performance-api.empcloud.com | `https://test-performance.empcloud.com?sso_token=<JWT>` |
| rewards | https://test-rewards.empcloud.com | https://test-rewards-api.empcloud.com | `https://test-rewards.empcloud.com?sso_token=<JWT>` |
| exit | https://test-exit.empcloud.com | https://test-exit-api.empcloud.com | `https://test-exit.empcloud.com?sso_token=<JWT>` |
| lms | https://testlms.empcloud.com | https://testlms-api.empcloud.com | `https://testlms.empcloud.com?sso_token=<JWT>` |
| project | https://test-project.empcloud.com | https://test-project-api.empcloud.com | `https://test-project.empcloud.com?sso_token=<JWT>` |
| monitor | https://test-empmonitor.empcloud.com | https://test-empmonitor-api.empcloud.com | `https://test-empmonitor.empcloud.com?sso_token=<JWT>` |

### SSO Mechanism
- sso_token URL parameter -- navigate to module_url?sso_token=<access_token>
- Token expires in 15 minutes (access token)
- Rate limiting: DISABLED for testing
- Pagination defaults: page=1, limit=20

### API Response Format
```json
// Success: {"success": true, "data": {...}}
// Error:   {"success": false, "error": {"code": "...", "message": "..."}}
// Paginated: {"success": true, "data": [...], "meta": {"page": 1, "limit": 20, "total": N, "totalPages": M}}
```

### Organizations

#### TechNova (ID: 5)
- Admin: ananya@technova.in
- Departments: Engineering, Sales, HR, Finance, Operations
- Leave Types: Casual Leave, Compensatory Off, Earned Leave, Maternity Leave, Paternity Leave, Sick Leave
- Shifts: General Shift, Morning Shift, Night Shift

#### GlobalTech (ID: 9)
- Admin: john@globaltech.com
- Departments: Engineering, Sales, HR, Finance, Operations
- Leave Types: Casual Leave, Compensatory Off, Earned Leave, Maternity Leave, Paternity Leave, Sick Leave
- Shifts: General Shift, Morning Shift, Night Shift

#### Innovate Solutions (ID: 39)
- Admin: hr@innovate.io
- Departments: Engineering, Sales, HR, Finance, Operations
- Leave Types: Casual Leave, Compensatory Off, Earned Leave, Maternity Leave, Paternity Leave, Sick Leave
- Shifts: General Shift, Morning Shift, Night Shift

### Critical Rules (from CLAUDE.md)

1. **Module Auth**: External modules use SSO from EMP Cloud. Core JWT does NOT work on module APIs.
2. **Correct API Paths**: See CORRECT_API_PATHS.md. Common mistakes: /departments -> /organizations/me/departments, /leave/apply -> /leave/applications
3. **Soft Delete**: DELETE returns 200 but items remain accessible. This is BY DESIGN for audit trail.
4. **XSS in DB**: Script tags stored in DB are NOT a vulnerability (React auto-escapes, Knex parameterizes).
5. **Do NOT Report**: Rate limiting issues, Field Force, Biometrics, direct subdomain login failures, soft delete, stored XSS.
6. **Bug Reports**: Must include URL, Steps to Reproduce, Expected vs Actual, Screenshot.
7. **Read Programmer Comments**: Before re-opening bugs, read ALL comments from sumitempcloud.
8. **Consolidate Bugs**: Group similar issues into ONE issue.
9. **Human-Style Titles**: Write like a real person, not a robot.
10. **EMP Project uses /v1/ prefix** (not /api/v1/)

### Simulation Statistics (March 2026)

- Total bugs filed during simulation: 2
- API errors encountered: 620
- Organizations tested: 3 (TechNova, GlobalTech, Innovate Solutions)
- Employees per org: 20
- Working days simulated: 22

**TechNova:**
  - Headcount: 20 active, 2 exits
  - Attendance: 20 records, 20 late
  - Leave: 20 applications
  - Engagement: 20 surveys, 19 forum posts, 20 tickets

**GlobalTech:**
  - Headcount: 20 active, 2 exits
  - Attendance: 20 records, 20 late
  - Leave: 3 applications
  - Engagement: 0 surveys, 0 forum posts, 0 tickets

**Innovate Solutions:**
  - Headcount: 20 active, 2 exits
  - Attendance: 20 records, 20 late
  - Leave: 3 applications
  - Engagement: 0 surveys, 0 forum posts, 0 tickets
