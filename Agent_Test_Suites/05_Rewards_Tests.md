# Comprehensive Rewards Test Suite

> **Testing Agent Note:** This is an exhaustive list derived directly from project parameters. Every item must be tested. Record actual HTTP response codes, payloads, and screenshot evidence.

## 1. Business Logic Rules

- [ ] **H001** (HIGH): Ticket SLA — response time tracked
- [ ] **H002** (HIGH): Ticket auto-escalation after SLA breach
- [ ] **H003** (MEDIUM): Cannot close ticket without resolution
- [ ] **H004** (HIGH): Ticket status flow: Open → In Progress → Resolved → Closed
- [ ] **H005** (MEDIUM): Cannot reopen a closed ticket after X days
- [ ] **H006** (HIGH): Priority-based SLA (Critical < High < Medium < Low)
- [ ] **H007** (MEDIUM): Ticket assignment — only to agents, not regular employees
- [ ] **W001** (HIGH): Survey response is anonymous (if configured)
- [ ] **W002** (HIGH): Cannot submit survey after end date
- [ ] **W003** (HIGH): Cannot submit survey twice
- [ ] **W004** (MEDIUM): Wellness check-in — only one per day
- [ ] **W005** (MEDIUM): Forum post — author can edit/delete own, not others
- [ ] **W006** (CRITICAL): Whistleblowing — truly anonymous (no user tracking)
- [ ] **W007** (HIGH): Feedback marked anonymous — identity not exposed
- [ ] **N001** (HIGH): Leave application → manager notification
- [ ] **N002** (HIGH): Leave approval/rejection → employee notification
- [ ] **N003** (HIGH): New announcement → all target employees notified
- [ ] **N004** (HIGH): Ticket update → requester notified
- [ ] **N005** (MEDIUM): Payslip generated → employee notified
- [ ] **N006** (MEDIUM): Document uploaded for employee → employee notified
- [ ] **N007** (MEDIUM): Event created → invited employees notified
- [ ] **N008** (HIGH): Performance review assigned → employee notified
- [ ] **N009** (MEDIUM): Asset assigned → employee notified
- [ ] **N010** (HIGH): Password expiry warning → user notified

## 2. API Endpoints to Verify

- [ ] `GET` `/api/v1/badges` -> Expected Status: `200`
- [ ] `POST` `/api/v1/badges` -> Expected Status: `400`
- [ ] `POST` `/api/v1/badges/award` -> Expected Status: `400`
- [ ] `GET` `/api/v1/badges/my` -> Expected Status: `200`
- [ ] `GET` `/api/v1/celebrations/feed` -> Expected Status: `200`
- [ ] `POST` `/api/v1/celebrations/{id}/wish` -> Expected Status: `400`
- [ ] `GET` `/api/v1/challenges` -> Expected Status: `200`
- [ ] `POST` `/api/v1/challenges` -> Expected Status: `400`
- [ ] `POST` `/api/v1/kudos` -> Expected Status: `400`
- [ ] `GET` `/api/v1/kudos` -> Expected Status: `200`
- [ ] `GET` `/api/v1/kudos/received` -> Expected Status: `200`
- [ ] `GET` `/api/v1/kudos/sent` -> Expected Status: `200`
- [ ] `POST` `/api/v1/kudos/{id}/comments` -> Expected Status: `400`
- [ ] `POST` `/api/v1/kudos/{id}/reactions` -> Expected Status: `400`
- [ ] `GET` `/api/v1/leaderboard` -> Expected Status: `200`
- [ ] `GET` `/api/v1/leaderboard/department/{deptId}` -> Expected Status: `200`
- [ ] `GET` `/api/v1/leaderboard/my-rank` -> Expected Status: `200`
- [ ] `GET` `/api/v1/milestones/rules` -> Expected Status: `200`
- [ ] `POST` `/api/v1/milestones/rules` -> Expected Status: `400`
- [ ] `POST` `/api/v1/nominations` -> Expected Status: `400`
- [ ] `GET` `/api/v1/nominations/programs` -> Expected Status: `200`
- [ ] `POST` `/api/v1/nominations/programs` -> Expected Status: `400`
- [ ] `PUT` `/api/v1/nominations/{id}/review` -> Expected Status: `400`
- [ ] `POST` `/api/v1/points/adjust` -> Expected Status: `400`
- [ ] `GET` `/api/v1/points/balance` -> Expected Status: `200`
- [ ] `GET` `/api/v1/points/transactions` -> Expected Status: `200`
- [ ] `POST` `/api/v1/push/subscribe` -> Expected Status: `400`
- [ ] `POST` `/api/v1/push/test` -> Expected Status: `400`
- [ ] `POST` `/api/v1/push/unsubscribe` -> Expected Status: `400`
- [ ] `GET` `/api/v1/redemptions` -> Expected Status: `200`
- [ ] `GET` `/api/v1/redemptions/my` -> Expected Status: `200`
- [ ] `PUT` `/api/v1/redemptions/{id}/approve` -> Expected Status: `400`
- [ ] `PUT` `/api/v1/redemptions/{id}/fulfill` -> Expected Status: `400`
- [ ] `GET` `/api/v1/rewards` -> Expected Status: `200`
- [ ] `POST` `/api/v1/rewards` -> Expected Status: `400`
- [ ] `POST` `/api/v1/rewards/{id}/redeem` -> Expected Status: `400`
- [ ] `GET` `/api/v1/slack/config` -> Expected Status: `200`
- [ ] `PUT` `/api/v1/slack/config` -> Expected Status: `200`
- [ ] `POST` `/api/v1/slack/test` -> Expected Status: `400`
- [ ] `GET` `/api/v1/celebrations` -> Expected Status: `404`
- [ ] `GET` `/api/v1/challenges/{id}` -> Expected Status: `404`
- [ ] `POST` `/api/v1/challenges/{id}/complete` -> Expected Status: `404`
- [ ] `POST` `/api/v1/challenges/{id}/join` -> Expected Status: `404`
- [ ] `GET` `/api/v1/challenges/{id}/progress` -> Expected Status: `404`
- [ ] `GET` `/api/v1/kudos/{id}` -> Expected Status: `404`
- [ ] `DELETE` `/api/v1/kudos/{id}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/manager/dashboard` -> Expected Status: `404`
- [ ] `GET` `/api/v1/manager/recommendations` -> Expected Status: `404`
- [ ] `GET` `/api/v1/manager/team-comparison` -> Expected Status: `404`
- [ ] `GET` `/api/v1/milestones/history` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/milestones/rules/{id}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/push/vapid-key` -> Expected Status: `503`
- [ ] `POST` `/api/v1/slack/slash-command` -> Expected Status: `404`
- [ ] `GET` `/api/v1/teams` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/teams` -> Expected Status: `404`
- [ ] `POST` `/api/v1/teams/test` -> Expected Status: `404`

