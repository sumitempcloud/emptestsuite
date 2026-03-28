# Comprehensive Cross-Module & Security Integrity Tests

> **Testing Agent Note:** This is an exhaustive list derived directly from project parameters. Every item must be tested. Record actual HTTP response codes, payloads, and screenshot evidence.

## 1. Business Logic Rules

- [ ] **MT001** (CRITICAL): Org A cannot see Org B's employees
- [ ] **MT002** (CRITICAL): Org A cannot modify Org B's data
- [ ] **MT003** (CRITICAL): Org A cannot access Org B's modules
- [ ] **MT004** (CRITICAL): Cross-org search returns nothing
- [ ] **MT005** (CRITICAL): API with org A token cannot access org B IDs
- [ ] **MT006** (HIGH): SSO token scoped to single org
- [ ] **MT007** (HIGH): Super Admin sees all orgs but with explicit context
- [ ] **MT008** (CRITICAL): Module data isolated per org (payroll, performance, etc.)
- [ ] **MT009** (HIGH): Audit log only shows current org's actions
- [ ] **MT010** (HIGH): Notifications scoped to org
- [ ] **S001** (HIGH): Password minimum strength (8+ chars, uppercase, lowercase, special)
- [ ] **S002** (MEDIUM): Password history — cannot reuse last X passwords
- [ ] **S003** (HIGH): Session timeout after X minutes of inactivity
- [ ] **S004** (HIGH): Account lockout after X failed login attempts
- [ ] **S005** (CRITICAL): All critical actions logged in audit trail
- [ ] **S006** (CRITICAL): Sensitive data encrypted at rest (salary, bank details, PAN)
- [ ] **S007** (HIGH): API rate limiting per user/org
- [ ] **S008** (HIGH): CORS — only allowed origins
- [ ] **S009** (HIGH): JWT token expiry enforced
- [ ] **S010** (HIGH): Refresh token rotation — old refresh token invalidated
- [ ] **S011** (HIGH): Password reset token — single use, expires in X minutes
- [ ] **S012** (MEDIUM): GDPR — employee can request data export
- [ ] **S013** (MEDIUM): GDPR — employee can request data deletion
- [ ] **S014** (HIGH): Data backup and recovery
- [ ] **S015** (CRITICAL): Role-based access — employee cannot access admin APIs

## 2. API Endpoints to Verify

*No endpoints found or API not deployed.*

