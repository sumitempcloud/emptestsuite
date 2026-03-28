# Comprehensive LMS Test Suite

> **Testing Agent Note:** This is an exhaustive list derived directly from project parameters. Every item must be tested. Record actual HTTP response codes, payloads, and screenshot evidence.

## 1. Business Logic Rules

- [ ] **LM001** (HIGH): Mandatory training — employee cannot skip compliance courses
- [ ] **LM002** (MEDIUM): Course completion certificate auto-generated
- [ ] **LM003** (HIGH): Quiz pass mark enforced — cannot "complete" without passing
- [ ] **LM004** (MEDIUM): Training expiry — recertification required after X months
- [ ] **LM005** (MEDIUM): Course enrollment capacity limit
- [ ] **LM006** (MEDIUM): Manager can assign courses to team

## 2. API Endpoints to Verify

- [ ] `POST` `/api/v1/auth/login` -> Expected Status: `400`
- [ ] `POST` `/api/v1/auth/sso` -> Expected Status: `400`
- [ ] `POST` `/api/v1/certificates/issue` -> Expected Status: `400`
- [ ] `GET` `/api/v1/certificates/my` -> Expected Status: `200`
- [ ] `GET` `/api/v1/courses` -> Expected Status: `200`
- [ ] `POST` `/api/v1/courses` -> Expected Status: `422`
- [ ] `GET` `/api/v1/discussions` -> Expected Status: `400`
- [ ] `POST` `/api/v1/discussions` -> Expected Status: `422`
- [ ] `POST` `/api/v1/enrollments` -> Expected Status: `422`
- [ ] `POST` `/api/v1/enrollments/bulk` -> Expected Status: `422`
- [ ] `GET` `/api/v1/enrollments/my` -> Expected Status: `200`
- [ ] `GET` `/api/v1/gamification/leaderboard` -> Expected Status: `200`
- [ ] `GET` `/api/v1/learning-paths` -> Expected Status: `200`
- [ ] `POST` `/api/v1/learning-paths` -> Expected Status: `400`
- [ ] `GET` `/api/v1/ratings` -> Expected Status: `400`
- [ ] `POST` `/api/v1/ratings` -> Expected Status: `422`
- [ ] `POST` `/api/v1/scorm/upload` -> Expected Status: `400`
- [ ] `GET` `/api/v1/certificates/{id}/download` -> Expected Status: `404`
- [ ] `GET` `/api/v1/certificates/{id}/verify` -> Expected Status: `404`
- [ ] `POST` `/api/v1/compliance/assign` -> Expected Status: `404`
- [ ] `GET` `/api/v1/compliance/dashboard` -> Expected Status: `500`
- [ ] `GET` `/api/v1/compliance/my` -> Expected Status: `404`
- [ ] `GET` `/api/v1/compliance/overdue` -> Expected Status: `404`
- [ ] `GET` `/api/v1/courses/{id}` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/courses/{id}` -> Expected Status: `404`
- [ ] `DELETE` `/api/v1/courses/{id}` -> Expected Status: `404`
- [ ] `POST` `/api/v1/discussions/{id}/replies` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/enrollments/{id}/progress` -> Expected Status: `404`
- [ ] `GET` `/api/v1/gamification/badges` -> Expected Status: `404`
- [ ] `GET` `/api/v1/gamification/my` -> Expected Status: `404`
- [ ] `GET` `/api/v1/ilt` -> Expected Status: `404`
- [ ] `POST` `/api/v1/ilt` -> Expected Status: `404`
- [ ] `POST` `/api/v1/ilt/{id}/attendance` -> Expected Status: `404`
- [ ] `POST` `/api/v1/ilt/{id}/register` -> Expected Status: `404`
- [ ] `GET` `/api/v1/learning-paths/{id}` -> Expected Status: `404`
- [ ] `POST` `/api/v1/learning-paths/{id}/enroll` -> Expected Status: `404`
- [ ] `POST` `/api/v1/quizzes/attempt` -> Expected Status: `404`

