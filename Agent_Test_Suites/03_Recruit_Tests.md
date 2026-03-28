# Comprehensive Recruit Test Suite

> **Testing Agent Note:** This is an exhaustive list derived directly from project parameters. Every item must be tested. Record actual HTTP response codes, payloads, and screenshot evidence.

## 1. Business Logic Rules

- [ ] **R001** (HIGH): Cannot hire more than position headcount allows
- [ ] **R002** (HIGH): Offer letter requires approval before sending
- [ ] **R003** (HIGH): Candidate cannot be in two active pipelines
- [ ] **R004** (MEDIUM): Cannot skip pipeline stages (Applied→Offer not allowed)
- [ ] **R005** (MEDIUM): Cannot send offer without interview completion
- [ ] **R006** (HIGH): Hired candidate auto-creates employee record
- [ ] **R007** (MEDIUM): Rejected candidate — reason mandatory
- [ ] **R008** (MEDIUM): Job posting auto-closes when positions filled
- [ ] **R009** (MEDIUM): Referral bonus tracked when referred candidate is hired
- [ ] **R010** (MEDIUM): Background check must complete before offer
- [ ] **R011** (HIGH): Duplicate candidate detection (same email/phone)

## 2. API Endpoints to Verify

- [ ] `GET` `/api/v1/applications` -> Expected Status: `200`
- [ ] `POST` `/api/v1/applications` -> Expected Status: `400`
- [ ] `PATCH` `/api/v1/applications/{id}/stage` -> Expected Status: `400`
- [ ] `POST` `/api/v1/auth/sso` -> Expected Status: `400`
- [ ] `GET` `/api/v1/background-checks/candidate/{candidateId}` -> Expected Status: `200`
- [ ] `PUT` `/api/v1/background-checks/{id}` -> Expected Status: `400`
- [ ] `GET` `/api/v1/candidates` -> Expected Status: `200`
- [ ] `POST` `/api/v1/candidates` -> Expected Status: `400`
- [ ] `PUT` `/api/v1/candidates/{id}` -> Expected Status: `400`
- [ ] `GET` `/api/v1/interviews` -> Expected Status: `200`
- [ ] `POST` `/api/v1/interviews` -> Expected Status: `400`
- [ ] `POST` `/api/v1/interviews/{id}/feedback` -> Expected Status: `400`
- [ ] `POST` `/api/v1/interviews/{id}/recordings` -> Expected Status: `400`
- [ ] `GET` `/api/v1/interviews/{id}/recordings` -> Expected Status: `200`
- [ ] `GET` `/api/v1/interviews/{id}/transcript` -> Expected Status: `200`
- [ ] `GET` `/api/v1/jobs` -> Expected Status: `200`
- [ ] `POST` `/api/v1/jobs` -> Expected Status: `400`
- [ ] `PUT` `/api/v1/jobs/{id}` -> Expected Status: `400`
- [ ] `PATCH` `/api/v1/jobs/{id}/status` -> Expected Status: `400`
- [ ] `GET` `/api/v1/onboarding/templates` -> Expected Status: `200`
- [ ] `POST` `/api/v1/public/careers/{slug}/apply` -> Expected Status: `400`
- [ ] `POST` `/api/v1/ai/batch-score` -> Expected Status: `404`
- [ ] `GET` `/api/v1/ai/rankings/{jobId}` -> Expected Status: `404`
- [ ] `POST` `/api/v1/ai/score-resume` -> Expected Status: `404`
- [ ] `GET` `/api/v1/ai/skills/{candidateId}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/applications/{id}` -> Expected Status: `500`
- [ ] `GET` `/api/v1/applications/{id}/timeline` -> Expected Status: `500`
- [ ] `POST` `/api/v1/assessments` -> Expected Status: `404`
- [ ] `GET` `/api/v1/assessments/{id}` -> Expected Status: `404`
- [ ] `POST` `/api/v1/assessments/{id}/submit` -> Expected Status: `404`
- [ ] `POST` `/api/v1/background-checks` -> Expected Status: `404`
- [ ] `GET` `/api/v1/background-checks/{id}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/candidates/compare` -> Expected Status: `500`
- [ ] `GET` `/api/v1/candidates/{id}` -> Expected Status: `500`
- [ ] `POST` `/api/v1/candidates/{id}/resume` -> Expected Status: `500`
- [ ] `GET` `/api/v1/interviews/{id}` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/interviews/{id}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/interviews/{id}/calendar-links` -> Expected Status: `404`
- [ ] `POST` `/api/v1/interviews/{id}/generate-meet` -> Expected Status: `404`
- [ ] `DELETE` `/api/v1/interviews/{id}/recordings` -> Expected Status: `404`
- [ ] `POST` `/api/v1/interviews/{id}/recordings/{recId}/transcribe` -> Expected Status: `404`

