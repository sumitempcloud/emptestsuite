# Comprehensive Performance Test Suite

> **Testing Agent Note:** This is an exhaustive list derived directly from project parameters. Every item must be tested. Record actual HTTP response codes, payloads, and screenshot evidence.

## 1. Business Logic Rules

- [ ] **PF001** (HIGH): Self-assessment deadline enforcement
- [ ] **PF002** (HIGH): Manager review only after self-assessment submitted
- [ ] **PF003** (HIGH): Cannot modify ratings after calibration locked
- [ ] **PF004** (MEDIUM): Goal progress cannot exceed 100%
- [ ] **PF005** (HIGH): Review cycle cannot be closed with pending reviews
- [ ] **PF006** (MEDIUM): PIP duration enforcement — auto-close after period
- [ ] **PF007** (MEDIUM): 360 feedback — cannot review yourself
- [ ] **PF008** (MEDIUM): Performance rating affects salary revision (integration)
- [ ] **PF009** (MEDIUM): Goal alignment — child goals contribute to parent
- [ ] **PF010** (HIGH): Cannot create review cycle with end date before start date

## 2. API Endpoints to Verify

- [ ] `GET` `/api/v1/analytics/goal-completion` -> Expected Status: `200`
- [ ] `GET` `/api/v1/analytics/overview` -> Expected Status: `200`
- [ ] `GET` `/api/v1/analytics/ratings-distribution` -> Expected Status: `400`
- [ ] `GET` `/api/v1/analytics/team-comparison` -> Expected Status: `200`
- [ ] `GET` `/api/v1/analytics/top-performers` -> Expected Status: `400`
- [ ] `GET` `/api/v1/analytics/trends` -> Expected Status: `200`
- [ ] `POST` `/api/v1/auth/sso` -> Expected Status: `400`
- [ ] `GET` `/api/v1/career-paths` -> Expected Status: `200`
- [ ] `POST` `/api/v1/career-paths` -> Expected Status: `400`
- [ ] `POST` `/api/v1/career-paths/{id}/levels` -> Expected Status: `400`
- [ ] `GET` `/api/v1/competency-frameworks` -> Expected Status: `200`
- [ ] `POST` `/api/v1/competency-frameworks` -> Expected Status: `400`
- [ ] `GET` `/api/v1/competency-frameworks/{id}` -> Expected Status: `400`
- [ ] `POST` `/api/v1/competency-frameworks/{id}/competencies` -> Expected Status: `400`
- [ ] `GET` `/api/v1/feedback` -> Expected Status: `200`
- [ ] `POST` `/api/v1/feedback` -> Expected Status: `400`
- [ ] `GET` `/api/v1/goals` -> Expected Status: `200`
- [ ] `POST` `/api/v1/goals` -> Expected Status: `400`
- [ ] `GET` `/api/v1/goals/{id}` -> Expected Status: `400`
- [ ] `PUT` `/api/v1/goals/{id}` -> Expected Status: `400`
- [ ] `POST` `/api/v1/goals/{id}/check-in` -> Expected Status: `400`
- [ ] `POST` `/api/v1/goals/{id}/key-results` -> Expected Status: `400`
- [ ] `POST` `/api/v1/letters/generate` -> Expected Status: `400`
- [ ] `POST` `/api/v1/letters/{id}/send` -> Expected Status: `400`
- [ ] `GET` `/api/v1/manager-effectiveness` -> Expected Status: `400`
- [ ] `GET` `/api/v1/manager-effectiveness/{managerId}` -> Expected Status: `400`
- [ ] `GET` `/api/v1/notifications/settings` -> Expected Status: `200`
- [ ] `PUT` `/api/v1/notifications/settings` -> Expected Status: `200`
- [ ] `GET` `/api/v1/one-on-ones` -> Expected Status: `200`
- [ ] `POST` `/api/v1/one-on-ones` -> Expected Status: `400`
- [ ] `POST` `/api/v1/one-on-ones/{id}/agenda-items` -> Expected Status: `400`
- [ ] `POST` `/api/v1/peer-reviews/nominate` -> Expected Status: `400`
- [ ] `GET` `/api/v1/peer-reviews/nominations` -> Expected Status: `400`
- [ ] `GET` `/api/v1/pips` -> Expected Status: `200`
- [ ] `POST` `/api/v1/pips` -> Expected Status: `400`
- [ ] `GET` `/api/v1/pips/{id}` -> Expected Status: `400`
- [ ] `POST` `/api/v1/pips/{id}/close` -> Expected Status: `400`
- [ ] `POST` `/api/v1/pips/{id}/objectives` -> Expected Status: `400`
- [ ] `POST` `/api/v1/pips/{id}/updates` -> Expected Status: `400`
- [ ] `GET` `/api/v1/review-cycles` -> Expected Status: `200`
- [ ] `POST` `/api/v1/review-cycles` -> Expected Status: `400`
- [ ] `GET` `/api/v1/review-cycles/{id}` -> Expected Status: `400`
- [ ] `PUT` `/api/v1/review-cycles/{id}` -> Expected Status: `400`
- [ ] `POST` `/api/v1/review-cycles/{id}/close` -> Expected Status: `400`
- [ ] `POST` `/api/v1/review-cycles/{id}/launch` -> Expected Status: `400`
- [ ] `POST` `/api/v1/review-cycles/{id}/participants` -> Expected Status: `400`
- [ ] `GET` `/api/v1/review-cycles/{id}/ratings-distribution` -> Expected Status: `400`
- [ ] `GET` `/api/v1/reviews` -> Expected Status: `200`
- [ ] `GET` `/api/v1/reviews/{id}` -> Expected Status: `400`
- [ ] `PUT` `/api/v1/reviews/{id}` -> Expected Status: `400`
- [ ] `POST` `/api/v1/reviews/{id}/submit` -> Expected Status: `400`
- [ ] `GET` `/api/v1/succession-plans` -> Expected Status: `200`
- [ ] `POST` `/api/v1/succession-plans` -> Expected Status: `400`
- [ ] `POST` `/api/v1/succession-plans/{id}/candidates` -> Expected Status: `400`
- [ ] `POST` `/api/v1/ai-summary/cycle/{cycleId}` -> Expected Status: `404`
- [ ] `POST` `/api/v1/ai-summary/review/{reviewId}` -> Expected Status: `404`
- [ ] `POST` `/api/v1/ai-summary/team/{managerId}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/ai-summary/{id}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/career-paths/{id}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/employees/{id}/career-track` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/employees/{id}/career-track` -> Expected Status: `404`
- [ ] `GET` `/api/v1/feedback/{id}` -> Expected Status: `404`
- [ ] `POST` `/api/v1/goal-alignment/link` -> Expected Status: `404`
- [ ] `DELETE` `/api/v1/goal-alignment/link/{id}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/goal-alignment/rollup/{goalId}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/goal-alignment/tree` -> Expected Status: `404`
- [ ] `GET` `/api/v1/letter-templates` -> Expected Status: `404`
- [ ] `POST` `/api/v1/letter-templates` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/letter-templates/{id}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/letters/{id}/download` -> Expected Status: `404`
- [ ] `POST` `/api/v1/manager-effectiveness/calculate` -> Expected Status: `404`
- [ ] `GET` `/api/v1/manager-effectiveness/{managerId}/trends` -> Expected Status: `404`
- [ ] `GET` `/api/v1/nine-box` -> Expected Status: `404`
- [ ] `GET` `/api/v1/nine-box/history/{employeeId}` -> Expected Status: `404`

