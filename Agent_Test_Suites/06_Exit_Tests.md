# Comprehensive Exit Test Suite

> **Testing Agent Note:** This is an exhaustive list derived directly from project parameters. Every item must be tested. Record actual HTTP response codes, payloads, and screenshot evidence.

## 1. Business Logic Rules

- [ ] **EX001** (CRITICAL): Clearance must complete before F&F
- [ ] **EX002** (CRITICAL): F&F calculation: pending salary + leave encashment - recoveries
- [ ] **EX003** (HIGH): All assets must be returned (clearance checklist)
- [ ] **EX004** (MEDIUM): Exit interview should happen before last working day
- [ ] **EX005** (CRITICAL): Employee access revoked on last working day
- [ ] **EX006** (HIGH): Cannot re-initiate exit for already exited employee
- [ ] **EX007** (HIGH): Notice buyout calculation (salary * remaining notice days)
- [ ] **EX008** (MEDIUM): Knowledge transfer tasks must be completed
- [ ] **EX009** (MEDIUM): Resignation withdrawal allowed before acceptance
- [ ] **EX010** (MEDIUM): Attrition rate calculation — only voluntary exits

## 2. API Endpoints to Verify

- [ ] `POST` `/api/v1/exits` -> Expected Status: `400`
- [ ] `GET` `/api/v1/exits` -> Expected Status: `200`
- [ ] `POST` `/api/v1/predictions/calculate` -> Expected Status: `200`
- [ ] `GET` `/api/v1/predictions/dashboard` -> Expected Status: `200`
- [ ] `GET` `/api/v1/predictions/employee/{employeeId}` -> Expected Status: `200`
- [ ] `GET` `/api/v1/predictions/high-risk` -> Expected Status: `200`
- [ ] `GET` `/api/v1/predictions/trends` -> Expected Status: `200`
- [ ] `GET` `/api/v1/rehire` -> Expected Status: `200`
- [ ] `POST` `/api/v1/rehire` -> Expected Status: `400`
- [ ] `GET` `/api/v1/self-service/my-checklist` -> Expected Status: `200`
- [ ] `GET` `/api/v1/self-service/my-exit` -> Expected Status: `200`
- [ ] `POST` `/api/v1/self-service/resign` -> Expected Status: `400`
- [ ] `GET` `/api/v1/checklist-templates` -> Expected Status: `404`
- [ ] `POST` `/api/v1/checklist-templates` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/checklist-templates/{id}` -> Expected Status: `404`
- [ ] `POST` `/api/v1/checklist-templates/{id}/items` -> Expected Status: `404`
- [ ] `GET` `/api/v1/clearance-departments` -> Expected Status: `404`
- [ ] `GET` `/api/v1/email-templates` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/email-templates/{stage}` -> Expected Status: `404`
- [ ] `POST` `/api/v1/email-templates/{stage}/preview` -> Expected Status: `404`
- [ ] `GET` `/api/v1/exits/{id}` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/exits/{id}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/exits/{id}/assets` -> Expected Status: `404`
- [ ] `POST` `/api/v1/exits/{id}/assets` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/exits/{id}/assets/{assetId}` -> Expected Status: `404`
- [ ] `GET` `/api/v1/exits/{id}/buyout` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/exits/{id}/buyout/approve` -> Expected Status: `404`
- [ ] `POST` `/api/v1/exits/{id}/buyout/calculate` -> Expected Status: `404`
- [ ] `POST` `/api/v1/exits/{id}/buyout/request` -> Expected Status: `404`
- [ ] `POST` `/api/v1/exits/{id}/cancel` -> Expected Status: `404`
- [ ] `GET` `/api/v1/exits/{id}/clearance` -> Expected Status: `404`
- [ ] `PUT` `/api/v1/exits/{id}/clearance/{clearanceId}` -> Expected Status: `404`

