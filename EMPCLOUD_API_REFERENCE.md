# EmpCloud Comprehensive API Reference

> Compiled from all 12 EmpCloud GitHub repository READMEs on 2026-03-28.
> NOTE: emp-biometrics has no README (404). Biometric APIs are documented in EMP Cloud core.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Authentication & SSO](#authentication--sso)
3. [Module Connection Map](#module-connection-map)
4. [Test Deployment URLs](#test-deployment-urls)
5. [Tech Stack Summary](#tech-stack-summary)
6. [EMP Cloud (Core HRMS + Identity)](#emp-cloud-core-hrms--identity)
7. [EMP Payroll](#emp-payroll)
8. [EMP Recruit](#emp-recruit)
9. [EMP Performance](#emp-performance)
10. [EMP Rewards](#emp-rewards)
11. [EMP Exit](#emp-exit)
12. [EMP LMS](#emp-lms)
13. [EMP Billing (Internal)](#emp-billing-internal)
14. [EMP Monitor](#emp-monitor)
15. [EMP Project](#emp-project)
16. [EMP Field](#emp-field)
17. [EMP Biometrics](#emp-biometrics)
18. [Role-Based Access Control](#role-based-access-control)
19. [API Response Format](#api-response-format)
20. [Database Schema Summary](#database-schema-summary)
21. [Environment Variables Reference](#environment-variables-reference)

---

## Architecture Overview

```
empcloud.com                    <- EMP Cloud (core HRMS + identity + gateway)
|   Built-in: Employee Profiles, Attendance, Leave, Documents,
|             Announcements, Policies, Org Chart, Notifications,
|             Bulk Import, Self-Service Dashboard, Unified Widgets,
|             Super Admin Dashboard, Onboarding Wizard, AI Agent,
|             Service Health, Data Sanity, Log Pipeline, API Docs,
|             Helpdesk, Surveys, Assets, Positions, Forum, Events,
|             Wellness, Whistleblowing, Anonymous Feedback, Custom Fields
|
|- payroll.empcloud.com         <- EMP Payroll (sellable module)
|- monitor.empcloud.com         <- EMP Monitor (sellable module)
|- recruit.empcloud.com         <- EMP Recruit (sellable module)
|- field.empcloud.com           <- EMP Field (sellable module)
|- biometrics.empcloud.com      <- EMP Biometrics (sellable module)
|- projects.empcloud.com        <- EMP Projects (sellable module)
|- rewards.empcloud.com         <- EMP Rewards (sellable module)
|- performance.empcloud.com     <- EMP Performance (sellable module)
|- exit.empcloud.com            <- EMP Exit (sellable module)
|- lms.empcloud.com             <- EMP LMS (sellable module)
```

### Design Principles

- **EMP Cloud IS the core HRMS** -- Attendance, Leave, Employee Profiles, Documents, Announcements, Policies are built directly into EMP Cloud
- **EMP Billing is internal** -- Powers subscription invoicing behind the scenes; NOT a sellable module
- **10 sellable modules** in the marketplace
- **OAuth2/OIDC Authorization Server** -- SOC 2 compliant, RS256 asymmetric signing, PKCE for SPAs
- **SSO via sso_token URL parameter** -- Cross-module SSO uses short-lived sso_token
- **Single MySQL instance, separate databases** -- `empcloud`, `emp_payroll`, `emp_monitor`, `emp_lms`, etc.
- **Subdomain-based module routing** -- Each module is an independent app at its own URL
- **Seat-based subscriptions** -- Orgs subscribe to modules with allocated seats
- **Payroll fetches from Cloud** -- EMP Payroll retrieves attendance/leave from EMP Cloud via service APIs
- **Auto-migrations on startup** -- Server runs pending DB migrations automatically on boot

---

## Authentication & SSO

### Method: OAuth2/OIDC + JWT (RS256)

**EMP Cloud is the identity provider. All modules authenticate through it.**

#### SSO Flow (sso_token -- primary for cross-module navigation)

1. User is authenticated on EMP Cloud
2. User clicks a module link (e.g., "Open Recruit")
3. EMP Cloud generates a short-lived sso_token (stored in DB, expires in 60s)
4. Redirect to: `recruit.empcloud.com/sso/callback?sso_token=<token>`
5. Module backend calls `POST /api/v1/auth/sso/validate` with `{ sso_token }`
6. EMP Cloud validates (exists, not expired, not used) -> returns user details + org info
7. Module creates a local session for the user

#### OAuth2 Full Flow (for initial auth)

1. User visits module subdomain
2. No session -> redirect to `empcloud.com/oauth/authorize?client_id=...&redirect_uri=...&response_type=code&scope=openid profile module:access&code_challenge=<PKCE>`
3. User authenticates on empcloud.com
4. EMP Cloud checks subscription + available seat
5. Redirect back with auth code
6. Module exchanges code for tokens: `POST empcloud.com/oauth/token` -> `{ access_token, refresh_token, id_token }`
7. Module verifies access_token using EMP Cloud's public key (RS256)

#### OIDC Discovery Endpoints

| Endpoint | Description |
|----------|-------------|
| `/.well-known/openid-configuration` | OIDC discovery |
| `/oauth/jwks` | JSON Web Key Set |
| `/oauth/authorize` | Authorization endpoint |
| `/oauth/token` | Token endpoint |

#### Module OAuth Client IDs

| Module | Client ID |
|--------|-----------|
| EMP Payroll | `emp-payroll` |
| EMP Monitor | `emp-monitor` |
| EMP Recruit | `emp-recruit` |
| EMP Field | `emp-field` |
| EMP Biometrics | `emp-biometrics` |
| EMP Projects | `emp-projects` |
| EMP Rewards | `emp-rewards` |
| EMP Performance | `emp-performance` |
| EMP Exit | `emp-exit` |
| EMP LMS | `emp-lms` |

---

## Module Connection Map

### How modules connect to EMP Cloud

| Module | Auth Method | Database | Reads from EmpCloud DB? | Webhooks to Cloud? |
|--------|-------------|----------|------------------------|-------------------|
| EMP Cloud | Native (identity server) | `empcloud` | N/A | N/A |
| EMP Payroll | JWT + SSO | `emp_payroll` | Yes (attendance, leave when `USE_CLOUD_HRMS=true`) | No |
| EMP Recruit | RS256 JWT + SSO | `emp_recruit` | Yes (users, orgs) | Yes (candidate.hired, offer.accepted, onboarding.completed) |
| EMP Performance | RS256 JWT + SSO | `emp_performance` | Yes (users, orgs) | Yes (review.completed, pip.created, pip.closed) |
| EMP Rewards | RS256 JWT + SSO | `emp_rewards` | Yes (users, orgs, celebrations) | No |
| EMP Exit | RS256 JWT + SSO | `emp_exit` | Yes (users, orgs) | No (completes exit -> deactivates user in Cloud) |
| EMP LMS | JWT + SSO | `emp_lms` | Yes (users, orgs) | No (awards via Rewards API, fetches skills from Performance API) |
| EMP Billing | JWT (internal) | `emp_billing` | Internal engine | Internal |
| EMP Monitor | Separate (Laravel + Node.js) | Separate | No (independent system) | No |
| EMP Project | Separate | MongoDB | No (independent system) | No |
| EMP Field | JWT | MongoDB | No (independent system) | No |

### Cross-Module AI Agent Tools (in EMP Cloud)

EMP Cloud's AI agent calls these module APIs:

| Tool | Module Called | Description |
|------|-------------|-------------|
| `get_open_jobs` | Recruit | Fetch open job postings |
| `get_hiring_pipeline` | Recruit | Pipeline summary with stage counts |
| `get_recruitment_stats` | Recruit | Time-to-hire and source analytics |
| `get_review_cycle_status` | Performance | Active review cycle status |
| `get_goals_summary` | Performance | Goal completion summary by team |
| `get_team_performance` | Performance | Team performance ratings and trends |
| `get_kudos_summary` | Rewards | Recognition summary |
| `get_recognition_leaderboard` | Rewards | Top recognized employees |
| `get_active_exits` | Exit | Active exit count and details |
| `get_attrition_analytics` | Exit | Attrition rate and trends |
| `get_course_catalog` | LMS | Available courses |
| `get_training_compliance` | LMS | Compliance training status |
| `get_payroll_summary` | Payroll | Payroll run summary |
| `get_salary_lookup` | Payroll | Employee salary details |
| `get_payroll_analytics` | Payroll | Payroll cost analytics |

---

## Test Deployment URLs

| Module | Frontend URL | API URL |
|--------|-------------|---------|
| EMP Cloud | https://test-empcloud.empcloud.com | https://test-empcloud-api.empcloud.com |
| EMP Recruit | https://test-recruit.empcloud.com | https://test-recruit-api.empcloud.com |
| EMP Performance | https://test-performance.empcloud.com | https://test-performance-api.empcloud.com |
| EMP Rewards | https://test-rewards.empcloud.com | https://test-rewards-api.empcloud.com |
| EMP Exit | https://test-exit.empcloud.com | https://test-exit-api.empcloud.com |
| EMP LMS | https://testlms.empcloud.com | https://testlms-api.empcloud.com |
| EMP Payroll | https://testpayroll.empcloud.com | https://testpayroll-api.empcloud.com |
| EMP Project | https://test-project.empcloud.com | https://test-project-api.empcloud.com |
| EMP Monitor | https://test-empmonitor.empcloud.com | https://test-empmonitor-api.empcloud.com |
| EMP Billing | (internal, port 4001) | (internal, port 4001) |

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 6, TypeScript, Tailwind CSS, Radix UI, React Query v5 |
| Backend | Node.js 20 LTS, Express 5, TypeScript |
| Database | MySQL 8 (Knex.js) -- most modules; MongoDB (emp-project, emp-field, emp-monitor) |
| Cache | Redis 7 |
| Auth | OAuth2/OIDC, RS256 JWT, PKCE, bcryptjs |
| Queue | BullMQ (async jobs) |
| Payments | Stripe, Razorpay, PayPal |
| API Docs | Swagger UI + OpenAPI 3.0 JSON (per module) |
| Validation | Zod schemas |
| Monorepo | pnpm workspaces |
| Infra | Docker, Docker Compose |

### Per-Module Ports

| Module | API Port | Client Port |
|--------|----------|-------------|
| EMP Cloud | 3000 | 5173 |
| EMP Billing | 4001 | 5174 |
| EMP Payroll | 4000 | 5175 |
| EMP Performance | 4300 | 5177 |
| EMP Exit | 4400 | 5178 |
| EMP Recruit | 4500 | 5179 |
| EMP Rewards | 4600 | 5180 |
| EMP LMS | 4700 | 5183 |
| EMP Project (Project API) | 9000 | 3000 |
| EMP Project (Task API) | 9001 | -- |

---

## EMP Cloud (Core HRMS + Identity)

**API Base**: `/api/v1/` on port 3000
**Database**: `empcloud`
**Repo**: https://github.com/EmpCloud/EmpCloud

### All API Endpoints

#### Auth (`/api/v1/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login with email/password |
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/password-reset` | Request password reset |
| POST | `/api/v1/auth/sso/validate` | Validate SSO token from module |

#### OAuth (`/oauth`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/oauth/authorize` | Authorization endpoint |
| POST | `/oauth/token` | Token exchange |
| POST | `/oauth/revoke` | Token revocation |
| POST | `/oauth/introspect` | Token introspection |
| GET | `/oauth/jwks` | JSON Web Key Set |
| GET | `/.well-known/openid-configuration` | OIDC discovery |

#### Organizations (`/api/v1/organizations`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/organizations` | Create organization |
| GET | `/api/v1/organizations/me` | Get current org |
| PUT | `/api/v1/organizations/me` | Update current org |
| GET | `/api/v1/organizations/me/departments` | List departments |
| POST | `/api/v1/organizations/me/departments` | Create department |
| GET | `/api/v1/organizations/me/locations` | List locations |
| POST | `/api/v1/organizations/me/locations` | Create location |

#### Users (`/api/v1/users`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/users` | List users |
| POST | `/api/v1/users/invite` | Invite user via email |
| GET | `/api/v1/users/:id` | Get user detail |
| PUT | `/api/v1/users/:id` | Update user |
| PUT | `/api/v1/users/:id/roles` | Assign roles |

#### Modules (`/api/v1/modules`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/modules` | List available modules |
| GET | `/api/v1/modules/:id` | Get module detail |

#### Subscriptions (`/api/v1/subscriptions`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/subscriptions` | List org subscriptions |
| POST | `/api/v1/subscriptions` | Subscribe to module |
| PUT | `/api/v1/subscriptions/:id` | Update subscription (seats) |
| DELETE | `/api/v1/subscriptions/:id` | Unsubscribe |

#### Employees (`/api/v1/employees`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/employees` | Employee directory (search, filters) |
| GET | `/api/v1/employees/:id` | Employee profile |
| PUT | `/api/v1/employees/:id` | Update employee |
| GET | `/api/v1/employees/:id/profile` | Extended profile |
| PUT | `/api/v1/employees/:id/profile` | Update extended profile |
| POST | `/api/v1/employees/:id/photo` | Upload profile photo |
| GET | `/api/v1/employees/:id/photo` | Get profile photo |
| GET | `/api/v1/employees/:id/addresses` | List addresses |
| POST | `/api/v1/employees/:id/addresses` | Add address |
| GET | `/api/v1/employees/:id/education` | Education history |
| POST | `/api/v1/employees/:id/education` | Add education |
| GET | `/api/v1/employees/:id/experience` | Work experience |
| POST | `/api/v1/employees/:id/experience` | Add experience |
| GET | `/api/v1/employees/:id/dependents` | Dependents |
| POST | `/api/v1/employees/:id/dependents` | Add dependent |
| GET | `/api/v1/employees/org-chart` | Organization chart |

#### Attendance (`/api/v1/attendance`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/attendance/check-in` | Daily check-in |
| POST | `/api/v1/attendance/check-out` | Daily check-out |
| GET | `/api/v1/attendance/records` | Attendance records |
| GET | `/api/v1/attendance/dashboard` | Attendance dashboard |
| GET | `/api/v1/attendance/reports` | Monthly reports |
| GET | `/api/v1/attendance/export` | CSV export |
| GET | `/api/v1/attendance/shifts` | List shifts |
| POST | `/api/v1/attendance/shifts` | Create shift |
| PUT | `/api/v1/attendance/shifts/:id` | Update shift |
| GET | `/api/v1/attendance/shift-assignments` | List assignments |
| POST | `/api/v1/attendance/shift-assignments` | Assign shift |
| GET | `/api/v1/attendance/geo-fences` | List geo-fences |
| POST | `/api/v1/attendance/geo-fences` | Create geo-fence |
| GET | `/api/v1/attendance/regularizations` | List regularization requests |
| POST | `/api/v1/attendance/regularizations` | Submit regularization |
| PUT | `/api/v1/attendance/regularizations/:id` | Approve/reject |
| GET | `/api/v1/attendance/schedule` | Shift schedule calendar |

#### Leave (`/api/v1/leave`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/leave/types` | Leave types |
| POST | `/api/v1/leave/types` | Create leave type |
| GET | `/api/v1/leave/policies` | Leave policies |
| POST | `/api/v1/leave/policies` | Create leave policy |
| GET | `/api/v1/leave/balances` | Leave balances |
| GET | `/api/v1/leave/applications` | List leave applications |
| POST | `/api/v1/leave/applications` | Apply for leave |
| PUT | `/api/v1/leave/applications/:id` | Update application |
| POST | `/api/v1/leave/applications/:id/approve` | Approve |
| POST | `/api/v1/leave/applications/:id/reject` | Reject |
| POST | `/api/v1/leave/bulk-approve` | Bulk approve |
| POST | `/api/v1/leave/bulk-reject` | Bulk reject |
| GET | `/api/v1/leave/calendar` | Team leave calendar |
| GET | `/api/v1/leave/comp-off` | Comp-off requests |
| POST | `/api/v1/leave/comp-off` | Create comp-off |
| GET | `/api/v1/leave/dashboard` | Leave dashboard |

#### Documents (`/api/v1/documents`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/documents/categories` | Document categories |
| POST | `/api/v1/documents/categories` | Create category |
| GET | `/api/v1/documents` | List documents |
| POST | `/api/v1/documents` | Upload document |
| GET | `/api/v1/documents/:id` | Get document |
| GET | `/api/v1/documents/:id/download` | Download |
| PUT | `/api/v1/documents/:id/verify` | Verify document |
| GET | `/api/v1/documents/my` | My documents |
| GET | `/api/v1/documents/mandatory` | Mandatory docs tracking |
| GET | `/api/v1/documents/expiry-alerts` | Expiry alerts |

#### Announcements (`/api/v1/announcements`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/announcements` | List announcements |
| POST | `/api/v1/announcements` | Create announcement |
| GET | `/api/v1/announcements/:id` | Get announcement |
| PUT | `/api/v1/announcements/:id` | Update |
| DELETE | `/api/v1/announcements/:id` | Delete |
| POST | `/api/v1/announcements/:id/read` | Mark read |
| GET | `/api/v1/announcements/unread-count` | Unread count |

#### Policies (`/api/v1/policies`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/policies` | List policies |
| POST | `/api/v1/policies` | Create policy |
| GET | `/api/v1/policies/:id` | Get policy |
| PUT | `/api/v1/policies/:id` | Update |
| POST | `/api/v1/policies/:id/acknowledge` | Acknowledge policy |
| GET | `/api/v1/policies/pending` | Pending acknowledgments |

#### Notifications (`/api/v1/notifications`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/notifications` | List notifications |
| POST | `/api/v1/notifications/:id/read` | Mark read |
| POST | `/api/v1/notifications/read-all` | Mark all read |
| GET | `/api/v1/notifications/unread-count` | Unread count |
| GET | `/api/v1/notifications/preferences` | Notification preferences |

#### Dashboard (`/api/v1/dashboard`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dashboard/widgets` | Unified widget data |
| GET | `/api/v1/dashboard/module-summaries` | Module summaries |
| GET | `/api/v1/dashboard/module-insights` | Module insight cards |

#### Billing (`/api/v1/billing`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/billing/invoices` | List invoices |
| GET | `/api/v1/billing/invoices/:id` | Invoice detail |
| POST | `/api/v1/billing/invoices/:id/pay` | Initiate payment |
| POST | `/api/v1/billing/webhooks/stripe` | Stripe webhook |
| POST | `/api/v1/billing/webhooks/razorpay` | Razorpay webhook |
| POST | `/api/v1/billing/webhooks/paypal` | PayPal webhook |

#### AI Agent (`/api/v1/chatbot`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chatbot/message` | Send message to AI agent |
| GET | `/api/v1/chatbot/conversations` | List conversations |
| GET | `/api/v1/chatbot/conversations/:id` | Get conversation history |

#### AI Config (`/api/v1/ai-config`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/ai-config` | Get AI provider config |
| PUT | `/api/v1/ai-config` | Update AI provider settings |

#### Admin (`/api/v1/admin`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/organizations` | List all orgs (super admin) |
| GET | `/api/v1/admin/organizations/:id` | Org detail |
| GET | `/api/v1/admin/health` | Service health dashboard |
| GET | `/api/v1/admin/data-sanity` | Data sanity checker |
| GET | `/api/v1/admin/stats` | Platform-wide stats |

#### Logs (`/api/v1/logs`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/logs` | Query logs |
| GET | `/api/v1/logs/analysis` | Log analysis |

#### Helpdesk (`/api/v1/helpdesk`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/helpdesk/tickets` | List tickets |
| POST | `/api/v1/helpdesk/tickets` | Create ticket |
| GET | `/api/v1/helpdesk/tickets/:id` | Ticket detail |
| PUT | `/api/v1/helpdesk/tickets/:id` | Update ticket |
| GET | `/api/v1/helpdesk/categories` | Helpdesk categories |
| GET | `/api/v1/helpdesk/knowledge-base` | Knowledge base articles |
| POST | `/api/v1/helpdesk/knowledge-base` | Create article |
| POST | `/api/v1/helpdesk/knowledge-base/:id/rate` | Rate article |

#### Surveys (`/api/v1/surveys`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/surveys` | List surveys |
| POST | `/api/v1/surveys` | Create survey |
| GET | `/api/v1/surveys/:id` | Get survey with responses |
| POST | `/api/v1/surveys/:id/respond` | Submit response |
| GET | `/api/v1/surveys/:id/results` | Survey results |

#### Assets (`/api/v1/assets`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/assets` | List assets |
| POST | `/api/v1/assets` | Create asset |
| GET | `/api/v1/assets/:id` | Get asset |
| PUT | `/api/v1/assets/:id` | Update asset |
| GET | `/api/v1/assets/categories` | Asset categories |
| POST | `/api/v1/assets/:id/assign` | Assign asset |
| GET | `/api/v1/assets/my` | My assigned assets |

#### Positions (`/api/v1/positions`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/positions` | List positions |
| POST | `/api/v1/positions` | Create position |
| GET | `/api/v1/positions/:id` | Get position |
| PUT | `/api/v1/positions/:id` | Update position |
| GET | `/api/v1/positions/headcount` | Headcount planning |

#### Forum (`/api/v1/forum`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/forum/categories` | Forum categories |
| POST | `/api/v1/forum/categories` | Create category |
| GET | `/api/v1/forum/posts` | List posts |
| POST | `/api/v1/forum/posts` | Create post |
| GET | `/api/v1/forum/posts/:id` | Get post with replies |
| POST | `/api/v1/forum/posts/:id/replies` | Reply to post |
| POST | `/api/v1/forum/posts/:id/react` | React to post |

#### Events (`/api/v1/events`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/events` | List events |
| POST | `/api/v1/events` | Create event |
| GET | `/api/v1/events/:id` | Get event |
| POST | `/api/v1/events/:id/register` | Register for event |
| GET | `/api/v1/events/calendar` | Events calendar |

#### Wellness (`/api/v1/wellness`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/wellness/dashboard` | Wellness dashboard |
| POST | `/api/v1/wellness/check-in` | Daily check-in |
| GET | `/api/v1/wellness/goals` | Wellness goals |

#### Feedback (`/api/v1/feedback`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/feedback` | Submit anonymous feedback |
| GET | `/api/v1/feedback` | List feedback (admin) |

#### Whistleblowing (`/api/v1/whistleblowing`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/whistleblowing` | Submit anonymous report |
| GET | `/api/v1/whistleblowing` | List reports (admin) |
| GET | `/api/v1/whistleblowing/:id` | Report detail |
| GET | `/api/v1/whistleblowing/track/:trackingId` | Track report status |

#### Custom Fields (`/api/v1/custom-fields`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/custom-fields/definitions` | Field definitions |
| POST | `/api/v1/custom-fields/definitions` | Create field definition |
| GET | `/api/v1/custom-fields/values/:entityType/:entityId` | Get values |
| PUT | `/api/v1/custom-fields/values/:entityType/:entityId` | Set values |

#### Biometrics (`/api/v1/biometrics`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/biometrics/enroll` | Face enrollment |
| POST | `/api/v1/biometrics/verify` | Face verification |
| GET | `/api/v1/biometrics/devices` | List devices |
| POST | `/api/v1/biometrics/qr/generate` | Generate QR code |
| POST | `/api/v1/biometrics/qr/scan` | QR attendance scan |

#### Manager (`/api/v1/manager`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/manager/dashboard` | Manager dashboard |
| GET | `/api/v1/manager/team` | Team members |

#### Import (`/api/v1/import`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/import/upload` | Upload CSV |
| POST | `/api/v1/import/preview` | Preview import data |
| POST | `/api/v1/import/execute` | Execute import |
| GET | `/api/v1/import/history` | Import history |

#### Audit (`/api/v1/audit`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/audit` | Audit log |

#### Other
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/docs` | Swagger UI |
| GET | `/api/docs/openapi.json` | OpenAPI spec |

---

## EMP Payroll

**API Base**: `/api/v1/` on port 4000
**Database**: `emp_payroll` (MySQL, also supports PostgreSQL/MongoDB)
**Repo**: https://github.com/EmpCloud/emp-payroll

### Auth (`/api/v1/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/register` | Register |
| POST | `/api/v1/auth/refresh-token` | Refresh token |
| POST | `/api/v1/auth/change-password` | Change password |
| POST | `/api/v1/auth/reset-employee-password` | Admin reset |

### Employees (`/api/v1/employees`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/employees` | List employees |
| POST | `/api/v1/employees` | Create employee |
| GET | `/api/v1/employees/export` | Export CSV |
| GET | `/api/v1/employees/:id` | Get detail |
| PUT | `/api/v1/employees/:id` | Update |
| DELETE | `/api/v1/employees/:id` | Deactivate |
| GET | `/api/v1/employees/:id/bank-details` | Bank details |
| PUT | `/api/v1/employees/:id/bank-details` | Update bank |
| GET | `/api/v1/employees/:id/tax-info` | Tax info |
| PUT | `/api/v1/employees/:id/tax-info` | Update tax |
| GET | `/api/v1/employees/:id/pf-details` | PF details |
| PUT | `/api/v1/employees/:id/pf-details` | Update PF |
| GET | `/api/v1/employees/:id/notes` | Notes |
| POST | `/api/v1/employees/:id/notes` | Add note |
| DELETE | `/api/v1/employees/:id/notes/:noteId` | Delete note |

### Payroll (`/api/v1/payroll`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/payroll` | List payroll runs |
| POST | `/api/v1/payroll` | Create run |
| GET | `/api/v1/payroll/:id` | Run details |
| POST | `/api/v1/payroll/:id/compute` | Compute |
| POST | `/api/v1/payroll/:id/approve` | Approve |
| POST | `/api/v1/payroll/:id/pay` | Mark paid |
| POST | `/api/v1/payroll/:id/cancel` | Cancel |
| GET | `/api/v1/payroll/:id/payslips` | Payslips |
| POST | `/api/v1/payroll/:id/send-payslips` | Email payslips |
| GET | `/api/v1/payroll/:id/reports/pf` | PF ECR file |
| GET | `/api/v1/payroll/:id/reports/esi` | ESI return |
| GET | `/api/v1/payroll/:id/reports/pt` | PT return |
| GET | `/api/v1/payroll/:id/reports/tds` | TDS summary |
| GET | `/api/v1/payroll/:id/reports/bank-file` | Bank transfer file |

### Salary Structures (`/api/v1/salary-structures`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/salary-structures` | List structures |
| POST | `/api/v1/salary-structures` | Create |
| GET | `/api/v1/salary-structures/:id/components` | Components |
| POST | `/api/v1/salary-structures/assign` | Assign to employee |
| GET | `/api/v1/salary-structures/employee/:empId` | Employee salary |
| GET | `/api/v1/salary-structures/employee/:empId/history` | Revision history |

### Benefits (`/api/v1/benefits`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/benefits/dashboard` | Dashboard |
| GET | `/api/v1/benefits/plans` | List plans |
| POST | `/api/v1/benefits/plans` | Create plan |
| GET | `/api/v1/benefits/plans/:id` | Plan detail |
| PUT | `/api/v1/benefits/plans/:id` | Update |
| GET | `/api/v1/benefits/enrollments` | Enrollments |
| POST | `/api/v1/benefits/enrollments` | Enroll |
| GET | `/api/v1/benefits/my` | My benefits |

### Insurance (`/api/v1/insurance`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/insurance/dashboard` | Dashboard |
| GET | `/api/v1/insurance/policies` | Policies |
| POST | `/api/v1/insurance/policies` | Create |
| GET | `/api/v1/insurance/policies/:id` | Detail |
| PUT | `/api/v1/insurance/policies/:id` | Update |
| GET | `/api/v1/insurance/enrollments` | Enrollments |
| POST | `/api/v1/insurance/enrollments` | Enroll |
| GET | `/api/v1/insurance/claims` | Claims |
| POST | `/api/v1/insurance/claims` | Submit claim |
| PUT | `/api/v1/insurance/claims/:id/review` | Review |

### GL Accounting (`/api/v1/gl-accounting`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/gl-accounting/mappings` | GL mappings |
| POST | `/api/v1/gl-accounting/mappings` | Create |
| PUT | `/api/v1/gl-accounting/mappings/:id` | Update |
| DELETE | `/api/v1/gl-accounting/mappings/:id` | Delete |
| POST | `/api/v1/gl-accounting/journal-entries/generate` | Generate from payroll |
| GET | `/api/v1/gl-accounting/journal-entries` | List entries |
| GET | `/api/v1/gl-accounting/period-summary` | Period summary |

### Global Payroll (`/api/v1/global-payroll`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/global-payroll/dashboard` | Dashboard |
| GET | `/api/v1/global-payroll/cost-analysis` | Cost analysis |
| GET | `/api/v1/global-payroll/countries` | Countries |
| GET | `/api/v1/global-payroll/countries/:id` | Country detail |
| GET | `/api/v1/global-payroll/employees` | Global employees |
| POST | `/api/v1/global-payroll/employees` | Add |
| GET | `/api/v1/global-payroll/employees/:id` | Detail |
| PUT | `/api/v1/global-payroll/employees/:id` | Update |
| GET | `/api/v1/global-payroll/runs` | Runs |
| POST | `/api/v1/global-payroll/runs` | Create |
| GET | `/api/v1/global-payroll/contractor-invoices` | Invoices |
| POST | `/api/v1/global-payroll/contractor-invoices` | Submit |
| GET | `/api/v1/global-payroll/compliance` | Compliance |
| PUT | `/api/v1/global-payroll/compliance/:id` | Update |

### Earned Wage Access (`/api/v1/earned-wage`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/earned-wage/settings` | Settings |
| PUT | `/api/v1/earned-wage/settings` | Update |
| GET | `/api/v1/earned-wage/requests` | All requests |
| POST | `/api/v1/earned-wage/requests` | Create |
| GET | `/api/v1/earned-wage/requests/:id` | Detail |
| PUT | `/api/v1/earned-wage/requests/:id/approve` | Approve |
| PUT | `/api/v1/earned-wage/requests/:id/reject` | Reject |
| GET | `/api/v1/earned-wage/my/eligibility` | My eligibility |
| GET | `/api/v1/earned-wage/my/requests` | My requests |

### Pay Equity (`/api/v1/pay-equity`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/pay-equity/analysis` | Analysis |
| GET | `/api/v1/pay-equity/compliance-report` | Report |

### Compensation Benchmarks (`/api/v1/compensation-benchmarks`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/compensation-benchmarks` | List |
| POST | `/api/v1/compensation-benchmarks` | Create |
| GET | `/api/v1/compensation-benchmarks/:id` | Detail |
| PUT | `/api/v1/compensation-benchmarks/:id` | Update |
| DELETE | `/api/v1/compensation-benchmarks/:id` | Delete |
| POST | `/api/v1/compensation-benchmarks/import` | Bulk import |
| GET | `/api/v1/compensation-benchmarks/comparison` | Compare vs market |

### Self-Service (`/api/v1/self-service`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/self-service/dashboard` | Employee dashboard |
| GET | `/api/v1/self-service/payslips` | My payslips |
| GET | `/api/v1/self-service/payslips/:id/pdf` | Download payslip |
| GET | `/api/v1/self-service/salary` | My salary |
| GET | `/api/v1/self-service/tax/computation` | Tax computation |
| GET | `/api/v1/self-service/tax/declarations` | My declarations |
| POST | `/api/v1/self-service/tax/declarations` | Submit declarations |
| GET | `/api/v1/self-service/tax/form16` | Form 16 |
| GET | `/api/v1/self-service/reimbursements` | My reimbursements |
| POST | `/api/v1/self-service/reimbursements` | Submit claim |
| GET | `/api/v1/self-service/profile` | My profile |

### Other Payroll Endpoints
| Module | Base | Description |
|--------|------|-------------|
| Attendance | `/api/v1/attendance` | Summary, import, LOP override |
| Leaves | `/api/v1/leaves` | Balances, record, adjust |
| Loans | `/api/v1/loans` | CRUD, payments, EMI tracking |
| Reimbursements | `/api/v1/reimbursements` | Approve, reject, pay |
| Tax | `/api/v1/tax` | Compute, declarations, Form 16 |
| Total Rewards | `/api/v1/total-rewards` | Total rewards statement |
| Adjustments | `/api/v1/adjustments` | Salary adjustments, bonus, arrears |
| Announcements | `/api/v1/announcements` | Company announcements |
| Organizations | `/api/v1/organizations` | Settings, activity log |
| Webhooks | `/api/v1/webhooks` | Inbound/outbound hooks |
| Health | `/health` | Health check |
| Docs | `/api/v1/docs/openapi.json` | OpenAPI spec |

### Tax Engine Coverage
| Country | Coverage |
|---------|----------|
| India (FY 2025-26) | Old & New regime TDS, 87A rebate, surcharge, cess, EPF 12%, EPS, ESI 0.75%+3.25%, PT for 7 states, Form 16 |
| United States | W-4 federal withholding, FICA (SS 6.2% + Medicare 1.45% + 0.9%), 50-state tax, FUTA |
| United Kingdom | PAYE, NIC Cat A/C, Student Loan Plan 1/2/4/5, auto-enrollment pension, Scottish/Welsh bands |

---

## EMP Recruit

**API Base**: `/api/v1/` on port 4500
**Database**: `emp_recruit`
**Repo**: https://github.com/EmpCloud/emp-recruit

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/sso` | SSO token exchange |

### Job Postings
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/jobs` | List jobs |
| POST | `/api/v1/jobs` | Create job |
| GET | `/api/v1/jobs/:id` | Job detail |
| PUT | `/api/v1/jobs/:id` | Update |
| PATCH | `/api/v1/jobs/:id/status` | Change status |
| GET | `/api/v1/jobs/:id/applications` | Applications for job |
| GET | `/api/v1/jobs/:id/analytics` | Job analytics |

### AI JD Generator
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/job-descriptions/generate` | Generate AI JD |
| GET | `/api/v1/job-descriptions/templates` | JD templates |

### Candidates
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/candidates` | List/search |
| POST | `/api/v1/candidates` | Create |
| GET | `/api/v1/candidates/:id` | Profile |
| PUT | `/api/v1/candidates/:id` | Update |
| POST | `/api/v1/candidates/:id/resume` | Upload resume |
| GET | `/api/v1/candidates/compare` | Side-by-side comparison |

### Applications (ATS)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/applications` | List |
| POST | `/api/v1/applications` | Create |
| GET | `/api/v1/applications/:id` | Detail |
| PATCH | `/api/v1/applications/:id/stage` | Move stage |
| GET | `/api/v1/applications/:id/timeline` | Stage history |

### Interviews
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/interviews` | List |
| POST | `/api/v1/interviews` | Schedule |
| GET | `/api/v1/interviews/:id` | Detail |
| PUT | `/api/v1/interviews/:id` | Reschedule |
| POST | `/api/v1/interviews/:id/feedback` | Submit scorecard |
| POST | `/api/v1/interviews/:id/generate-meet` | Generate Meet link |
| POST | `/api/v1/interviews/:id/send-invitation` | Send invite |
| POST | `/api/v1/interviews/:id/recordings` | Upload recording |
| GET | `/api/v1/interviews/:id/recordings` | List recordings |
| DELETE | `/api/v1/interviews/:id/recordings` | Delete recording |
| POST | `/api/v1/interviews/:id/recordings/:recId/transcribe` | Transcribe |
| GET | `/api/v1/interviews/:id/transcript` | Get transcript |
| PUT | `/api/v1/interviews/:id/transcript` | Edit transcript |
| GET | `/api/v1/interviews/:id/calendar-links` | Calendar links |
| GET | `/api/v1/interviews/:id/calendar.ics` | Download .ics |

### Offers
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/offers` | Create |
| GET | `/api/v1/offers/:id` | Detail |
| POST | `/api/v1/offers/:id/submit-approval` | Submit for approval |
| POST | `/api/v1/offers/:id/approve` | Approve |
| POST | `/api/v1/offers/:id/send` | Send to candidate |
| POST | `/api/v1/offers/:id/generate-pdf` | Generate PDF |
| POST | `/api/v1/offers/:id/email-letter` | Email letter |

### AI Resume Scoring
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ai/score-resume` | Score single resume |
| POST | `/api/v1/ai/batch-score` | Batch score |
| GET | `/api/v1/ai/rankings/:jobId` | Rankings |
| GET | `/api/v1/ai/skills/:candidateId` | Extracted skills |

### Background Checks
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/background-checks` | Initiate |
| GET | `/api/v1/background-checks/:id` | Status |
| GET | `/api/v1/background-checks/candidate/:candidateId` | By candidate |
| PUT | `/api/v1/background-checks/:id` | Update |

### Custom Pipeline Stages
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/pipeline-stages` | Get config |
| PUT | `/api/v1/pipeline-stages` | Update order/names/colors |
| POST | `/api/v1/pipeline-stages` | Add stage |
| DELETE | `/api/v1/pipeline-stages/:id` | Remove |

### Candidate Portal (Magic Link)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/portal/send-magic-link` | Send magic link |
| POST | `/api/v1/portal/verify` | Verify token |
| GET | `/api/v1/portal/my-applications` | My applications |
| GET | `/api/v1/portal/my-interviews` | My interviews |
| GET | `/api/v1/portal/my-offers` | My offers |

### Onboarding
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/onboarding/templates` | Templates |
| POST | `/api/v1/onboarding/templates` | Create |
| POST | `/api/v1/onboarding/checklists` | Generate checklist |
| PATCH | `/api/v1/onboarding/tasks/:id` | Update task |

### Public Career Page (No Auth)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/public/careers/:slug` | Career page |
| GET | `/api/v1/public/careers/:slug/jobs` | Open jobs |
| POST | `/api/v1/public/careers/:slug/apply` | Apply |

### Candidate Surveys
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/surveys` | Create survey |
| GET | `/api/v1/surveys/:id` | With responses |
| POST | `/api/v1/surveys/:id/respond` | Respond |

### Psychometric Assessments
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/assessments` | Assign |
| GET | `/api/v1/assessments/:id` | Results |
| POST | `/api/v1/assessments/:id/submit` | Submit answers |

---

## EMP Performance

**API Base**: `/api/v1/` on port 4300
**Database**: `emp_performance`
**Repo**: https://github.com/EmpCloud/emp-performance

### Auth
| POST | `/api/v1/auth/sso` | SSO token exchange |

### Review Cycles
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/review-cycles` | List |
| POST | `/api/v1/review-cycles` | Create |
| GET | `/api/v1/review-cycles/:id` | Detail |
| PUT | `/api/v1/review-cycles/:id` | Update |
| POST | `/api/v1/review-cycles/:id/launch` | Launch |
| POST | `/api/v1/review-cycles/:id/close` | Close |
| POST | `/api/v1/review-cycles/:id/participants` | Add participants |
| GET | `/api/v1/review-cycles/:id/ratings-distribution` | Bell curve |

### Reviews
| GET | `/api/v1/reviews` | List | PUT | `/api/v1/reviews/:id` | Save/submit |
| GET | `/api/v1/reviews/:id` | Detail | POST | `/api/v1/reviews/:id/submit` | Submit |

### Goals & OKRs
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/goals` | List |
| POST | `/api/v1/goals` | Create |
| GET | `/api/v1/goals/:id` | Detail |
| PUT | `/api/v1/goals/:id` | Update |
| POST | `/api/v1/goals/:id/key-results` | Add key result |
| POST | `/api/v1/goals/:id/check-in` | Log check-in |

### Goal Alignment
| GET | `/api/v1/goal-alignment/tree` | Full tree |
| POST | `/api/v1/goal-alignment/link` | Link goals |
| DELETE | `/api/v1/goal-alignment/link/:id` | Unlink |
| GET | `/api/v1/goal-alignment/rollup/:goalId` | Progress rollup |

### 9-Box Grid
| GET | `/api/v1/nine-box` | Grid data |
| PUT | `/api/v1/nine-box/:employeeId` | Update placement |
| GET | `/api/v1/nine-box/history/:employeeId` | History |

### Succession Planning
| GET | `/api/v1/succession-plans` | List |
| POST | `/api/v1/succession-plans` | Create |
| GET | `/api/v1/succession-plans/:id` | Detail |
| POST | `/api/v1/succession-plans/:id/candidates` | Add candidate |
| PUT | `/api/v1/succession-plans/:id/candidates/:candidateId` | Update readiness |
| DELETE | `/api/v1/succession-plans/:id/candidates/:candidateId` | Remove |

### Skills Gap Analysis
| GET | `/api/v1/skills-gap/:employeeId` | Employee gap |
| GET | `/api/v1/skills-gap/team/:teamId` | Team gap |
| POST | `/api/v1/skills-gap/assess` | Submit assessment |
| GET | `/api/v1/skills-gap/recommendations/:employeeId` | Learning recs |

### Manager Effectiveness
| GET | `/api/v1/manager-effectiveness` | All managers |
| GET | `/api/v1/manager-effectiveness/:managerId` | Detail |
| GET | `/api/v1/manager-effectiveness/:managerId/trends` | Trends |
| POST | `/api/v1/manager-effectiveness/calculate` | Recalculate |

### AI Review Summaries
| POST | `/api/v1/ai-summary/review/:reviewId` | Individual summary |
| POST | `/api/v1/ai-summary/cycle/:cycleId` | Cycle summary |
| POST | `/api/v1/ai-summary/team/:managerId` | Team summary |
| GET | `/api/v1/ai-summary/:id` | Retrieve |

### Performance Letters
| GET | `/api/v1/letter-templates` | Templates |
| POST | `/api/v1/letter-templates` | Create |
| PUT | `/api/v1/letter-templates/:id` | Update |
| POST | `/api/v1/letters/generate` | Generate PDF |
| GET | `/api/v1/letters/:id/download` | Download |
| POST | `/api/v1/letters/:id/send` | Email |

### Competency Frameworks
| GET | `/api/v1/competency-frameworks` | List |
| POST | `/api/v1/competency-frameworks` | Create |
| GET | `/api/v1/competency-frameworks/:id` | Detail |
| POST | `/api/v1/competency-frameworks/:id/competencies` | Add competency |

### PIPs
| GET | `/api/v1/pips` | List |
| POST | `/api/v1/pips` | Create |
| GET | `/api/v1/pips/:id` | Detail |
| POST | `/api/v1/pips/:id/objectives` | Add objective |
| POST | `/api/v1/pips/:id/updates` | Add update |
| POST | `/api/v1/pips/:id/close` | Close |

### Career Paths
| GET | `/api/v1/career-paths` | List |
| POST | `/api/v1/career-paths` | Create |
| GET | `/api/v1/career-paths/:id` | Detail |
| POST | `/api/v1/career-paths/:id/levels` | Add level |
| GET | `/api/v1/employees/:id/career-track` | Employee track |
| PUT | `/api/v1/employees/:id/career-track` | Assign track |

### 1-on-1 Meetings
| GET | `/api/v1/one-on-ones` | List |
| POST | `/api/v1/one-on-ones` | Create |
| GET | `/api/v1/one-on-ones/:id` | Detail |
| POST | `/api/v1/one-on-ones/:id/agenda-items` | Add item |
| POST | `/api/v1/one-on-ones/:id/complete` | Complete |

### Continuous Feedback
| GET | `/api/v1/feedback` | List |
| POST | `/api/v1/feedback` | Give |
| GET | `/api/v1/feedback/:id` | Detail |

### Peer Reviews
| POST | `/api/v1/peer-reviews/nominate` | Nominate |
| GET | `/api/v1/peer-reviews/nominations` | List pending |
| POST | `/api/v1/peer-reviews/nominations/:id/approve` | Approve |
| POST | `/api/v1/peer-reviews/nominations/:id/reject` | Reject |

### Analytics
| GET | `/api/v1/analytics/overview` | Dashboard |
| GET | `/api/v1/analytics/ratings-distribution` | Bell curve |
| GET | `/api/v1/analytics/team-comparison` | Team comparison |
| GET | `/api/v1/analytics/trends` | Trends |
| GET | `/api/v1/analytics/goal-completion` | Goal rates |
| GET | `/api/v1/analytics/top-performers` | Top/bottom |

---

## EMP Rewards

**API Base**: `/api/v1/` on port 4600
**Database**: `emp_rewards`
**Repo**: https://github.com/EmpCloud/emp-rewards

### Kudos
| POST | `/api/v1/kudos` | Send kudos |
| GET | `/api/v1/kudos` | Public feed |
| GET | `/api/v1/kudos/:id` | Detail |
| DELETE | `/api/v1/kudos/:id` | Retract |
| GET | `/api/v1/kudos/received` | My received |
| GET | `/api/v1/kudos/sent` | My sent |
| POST | `/api/v1/kudos/:id/reactions` | React |
| POST | `/api/v1/kudos/:id/comments` | Comment |

### Points
| GET | `/api/v1/points/balance` | Balance |
| GET | `/api/v1/points/transactions` | History |
| POST | `/api/v1/points/adjust` | Manual adjust (admin) |

### Badges
| GET | `/api/v1/badges` | List |
| POST | `/api/v1/badges` | Create (admin) |
| GET | `/api/v1/badges/my` | My badges |
| POST | `/api/v1/badges/award` | Award (admin) |

### Rewards Catalog
| GET | `/api/v1/rewards` | Browse |
| POST | `/api/v1/rewards` | Create (admin) |
| POST | `/api/v1/rewards/:id/redeem` | Redeem |

### Redemptions
| GET | `/api/v1/redemptions` | List (admin) |
| GET | `/api/v1/redemptions/my` | My redemptions |
| PUT | `/api/v1/redemptions/:id/approve` | Approve |
| PUT | `/api/v1/redemptions/:id/fulfill` | Fulfill |

### Nominations
| GET | `/api/v1/nominations/programs` | List programs |
| POST | `/api/v1/nominations/programs` | Create (admin) |
| POST | `/api/v1/nominations` | Submit |
| PUT | `/api/v1/nominations/:id/review` | Review (admin) |

### Leaderboard
| GET | `/api/v1/leaderboard` | Org leaderboard |
| GET | `/api/v1/leaderboard/department/:deptId` | Department |
| GET | `/api/v1/leaderboard/my-rank` | My rank |

### Celebrations
| GET | `/api/v1/celebrations` | Upcoming |
| GET | `/api/v1/celebrations/feed` | Social feed |
| POST | `/api/v1/celebrations/:id/wish` | Send wish |

### Team Challenges
| GET | `/api/v1/challenges` | List |
| POST | `/api/v1/challenges` | Create (admin) |
| GET | `/api/v1/challenges/:id` | Detail |
| POST | `/api/v1/challenges/:id/join` | Join |
| GET | `/api/v1/challenges/:id/progress` | Progress |
| POST | `/api/v1/challenges/:id/complete` | End & award |

### Milestones
| GET | `/api/v1/milestones/rules` | Rules |
| POST | `/api/v1/milestones/rules` | Create (admin) |
| PUT | `/api/v1/milestones/rules/:id` | Update |
| GET | `/api/v1/milestones/history` | History |

### Manager Dashboard
| GET | `/api/v1/manager/dashboard` | Team engagement |
| GET | `/api/v1/manager/team-comparison` | Dept comparison |
| GET | `/api/v1/manager/recommendations` | AI recs |

### Slack Integration
| GET | `/api/v1/slack/config` | Config |
| PUT | `/api/v1/slack/config` | Update |
| POST | `/api/v1/slack/test` | Test |
| POST | `/api/v1/slack/slash-command` | /kudos command |

### Teams Integration
| GET | `/api/v1/teams` | Config |
| PUT | `/api/v1/teams` | Update (admin) |
| POST | `/api/v1/teams/test` | Test (admin) |

### Push Notifications
| GET | `/api/v1/push/vapid-key` | VAPID key |
| POST | `/api/v1/push/subscribe` | Subscribe |
| POST | `/api/v1/push/unsubscribe` | Unsubscribe |
| POST | `/api/v1/push/test` | Test |

### Integration
| GET | `/api/v1/integration/user/:userId/summary` | For EMP Performance |

---

## EMP Exit

**API Base**: `/api/v1/` on port 4400
**Database**: `emp_exit`
**Repo**: https://github.com/EmpCloud/emp-exit

### Exit Requests
| POST | `/api/v1/exits` | Initiate |
| GET | `/api/v1/exits` | List |
| GET | `/api/v1/exits/:id` | Detail |
| PUT | `/api/v1/exits/:id` | Update |
| POST | `/api/v1/exits/:id/cancel` | Cancel |
| POST | `/api/v1/exits/:id/complete` | Complete |

### Self-Service
| POST | `/api/v1/self-service/resign` | Submit resignation |
| GET | `/api/v1/self-service/my-exit` | My exit status |
| GET | `/api/v1/self-service/my-checklist` | My checklist |
| POST | `/api/v1/self-service/exit-interview` | Submit interview |
| POST | `/api/v1/self-service/nps-survey` | Submit NPS |

### Checklist Templates
| GET | `/api/v1/checklist-templates` | List |
| POST | `/api/v1/checklist-templates` | Create |
| PUT | `/api/v1/checklist-templates/:id` | Update |
| POST | `/api/v1/checklist-templates/:id/items` | Add item |

### Clearance
| GET | `/api/v1/clearance-departments` | List |
| GET | `/api/v1/exits/:id/clearance` | Status |
| PUT | `/api/v1/exits/:id/clearance/:clearanceId` | Approve/reject |
| GET | `/api/v1/my-clearances` | My pending |

### Exit Interviews
| GET | `/api/v1/interview-templates` | Templates |
| POST | `/api/v1/interview-templates` | Create |
| GET | `/api/v1/exits/:id/interview` | Get |
| POST | `/api/v1/exits/:id/interview` | Schedule |

### Full & Final Settlement
| POST | `/api/v1/exits/:id/fnf/calculate` | Calculate |
| GET | `/api/v1/exits/:id/fnf` | Details |
| PUT | `/api/v1/exits/:id/fnf` | Update |
| POST | `/api/v1/exits/:id/fnf/approve` | Approve |
| POST | `/api/v1/exits/:id/fnf/mark-paid` | Mark paid |

### Asset Returns
| GET | `/api/v1/exits/:id/assets` | List |
| POST | `/api/v1/exits/:id/assets` | Add |
| PUT | `/api/v1/exits/:id/assets/:assetId` | Update |

### Knowledge Transfer
| POST | `/api/v1/exits/:id/kt` | Create KT plan |
| PUT | `/api/v1/exits/:id/kt` | Update |
| POST | `/api/v1/exits/:id/kt/items` | Add item |

### Letters
| GET | `/api/v1/letter-templates` | Templates |
| POST | `/api/v1/letter-templates` | Create |
| POST | `/api/v1/exits/:id/letters/generate` | Generate PDF |
| GET | `/api/v1/exits/:id/letters/:letterId/download` | Download |
| POST | `/api/v1/exits/:id/letters/:letterId/send` | Email |

### Flight Risk / Attrition
| GET | `/api/v1/predictions/dashboard` | Dashboard |
| GET | `/api/v1/predictions/high-risk` | High-risk |
| GET | `/api/v1/predictions/employee/:employeeId` | Individual |
| GET | `/api/v1/predictions/trends` | Trends |
| POST | `/api/v1/predictions/calculate` | Recalculate |

### Notice Buyout
| POST | `/api/v1/exits/:id/buyout/calculate` | Calculate |
| POST | `/api/v1/exits/:id/buyout/request` | Request |
| PUT | `/api/v1/exits/:id/buyout/approve` | Approve/reject |
| GET | `/api/v1/exits/:id/buyout` | Details |

### Email Templates
| GET | `/api/v1/email-templates` | List |
| PUT | `/api/v1/email-templates/:stage` | Update |
| POST | `/api/v1/email-templates/:stage/preview` | Preview |
| GET | `/api/v1/exits/:id/email-log` | Email log |

### Rehire
| GET | `/api/v1/rehire` | List |
| POST | `/api/v1/rehire` | Create |
| PUT | `/api/v1/rehire/:id/screen` | Screen |
| PUT | `/api/v1/rehire/:id/approve` | Approve |
| POST | `/api/v1/rehire/:id/hire` | Hire |
| GET | `/api/v1/rehire/eligible` | Eligible alumni |

### NPS
| GET | `/api/v1/nps/scores` | NPS |
| GET | `/api/v1/nps/trends` | Trends |
| GET | `/api/v1/nps/responses` | Responses |
| GET | `/api/v1/nps/department/:deptId` | By department |

---

## EMP LMS

**API Base**: `/api/v1/` on port 4700
**Database**: `emp_lms`
**Repo**: https://github.com/EmpCloud/emp-lms

### Auth
| POST | `/api/v1/auth/login` | JWT login |
| POST | `/api/v1/auth/sso` | SSO exchange |

### Courses
| GET | `/api/v1/courses` | List |
| POST | `/api/v1/courses` | Create (admin) |
| GET | `/api/v1/courses/:id` | Detail |
| PUT | `/api/v1/courses/:id` | Update |
| DELETE | `/api/v1/courses/:id` | Delete |

### Enrollments
| POST | `/api/v1/enrollments` | Enroll |
| POST | `/api/v1/enrollments/bulk` | Bulk enroll |
| GET | `/api/v1/enrollments/my` | My enrollments |
| PUT | `/api/v1/enrollments/:id/progress` | Update progress |

### Quizzes
| GET | `/api/v1/quizzes/:id` | Get quiz |
| POST | `/api/v1/quizzes/attempt` | Submit attempt |
| GET | `/api/v1/quizzes/:id/attempts` | List attempts |

### Learning Paths
| GET | `/api/v1/learning-paths` | List |
| POST | `/api/v1/learning-paths` | Create |
| GET | `/api/v1/learning-paths/:id` | Detail |
| POST | `/api/v1/learning-paths/:id/enroll` | Enroll |

### Certifications
| GET | `/api/v1/certificates/my` | My certs |
| POST | `/api/v1/certificates/issue` | Issue (admin) |
| GET | `/api/v1/certificates/:id/download` | Download PDF |
| GET | `/api/v1/certificates/:id/verify` | Verify |

### Compliance
| GET | `/api/v1/compliance/my` | My assignments |
| POST | `/api/v1/compliance/assign` | Assign (admin) |
| GET | `/api/v1/compliance/dashboard` | Dashboard |
| GET | `/api/v1/compliance/overdue` | Overdue |

### ILT Sessions
| GET | `/api/v1/ilt` | List |
| POST | `/api/v1/ilt` | Create (admin) |
| POST | `/api/v1/ilt/:id/register` | Register |
| POST | `/api/v1/ilt/:id/attendance` | Mark attendance |

### SCORM
| GET | `/api/v1/scorm/:id/launch` | Launch player |
| POST | `/api/v1/scorm/upload` | Upload package |
| POST | `/api/v1/scorm/:id/tracking` | Save tracking |

### Gamification
| GET | `/api/v1/gamification/leaderboard` | Leaderboard |
| GET | `/api/v1/gamification/my` | My points/badges |
| GET | `/api/v1/gamification/badges` | Badges |

### Discussions
| GET | `/api/v1/discussions` | List (?course_id=) |
| POST | `/api/v1/discussions` | Create |
| POST | `/api/v1/discussions/:id/replies` | Reply |

### Ratings
| GET | `/api/v1/ratings` | List (?course_id=) |
| POST | `/api/v1/ratings` | Submit |
| PUT | `/api/v1/ratings/:id` | Update |

### Other
| GET | `/api/v1/analytics/overview` | Overview |
| GET | `/api/v1/analytics/courses` | Course analytics |
| GET | `/api/v1/analytics/users` | User analytics |
| GET | `/api/v1/recommendations` | AI recommendations |
| GET | `/api/v1/marketplace` | Content marketplace |
| POST | `/api/v1/video/upload` | Video upload |
| GET | `/api/v1/video/:id/stream` | Video stream |
| GET | `/api/v1/notifications` | Notifications |
| GET | `/health` | Health check |

---

## EMP Billing (Internal)

**API Base**: `/api/v1/` on port 4001
**Database**: `emp_billing` (MySQL/PostgreSQL/MongoDB)
**Repo**: https://github.com/EmpCloud/emp-billing
**Note**: Internal engine, NOT a sellable module.

### All Route Modules
| Module | Base Path | Description |
|--------|-----------|-------------|
| Auth | `/api/v1/auth` | Login, register, refresh, logout, forgot/reset |
| Organizations | `/api/v1/organizations` | CRUD, settings, branding, tax config |
| Clients | `/api/v1/clients` | CRUD, contacts, portal, statements, import/export |
| Products | `/api/v1/products` | CRUD, price lists, import/export |
| Invoices | `/api/v1/invoices` | CRUD, send, duplicate, void, write-off, bulk, PDF |
| Quotes | `/api/v1/quotes` | CRUD, send, convert to invoice |
| Payments | `/api/v1/payments` | Record, refund, receipts, gateway callbacks |
| Credit Notes | `/api/v1/credit-notes` | CRUD, apply to invoice, refund |
| Expenses | `/api/v1/expenses` | CRUD, receipt upload, OCR scanning |
| Vendors | `/api/v1/vendors` | CRUD |
| Recurring | `/api/v1/recurring` | Profile CRUD, pause/resume, history |
| Subscriptions | `/api/v1/subscriptions` | Plans, subscriptions, usage records |
| Coupons | `/api/v1/coupons` | CRUD, per-client limits |
| Usage | `/api/v1/usage` | Usage events, aggregation |
| Dunning | `/api/v1/dunning` | Retry schedules, attempts |
| Disputes | `/api/v1/disputes` | CRUD, resolution |
| Reports | `/api/v1/reports` | Revenue, receivables, tax, expenses, P&L |
| Scheduled Reports | `/api/v1/scheduled-reports` | Recurring report emails |
| Metrics | `/api/v1/metrics` | MRR, ARR, churn, LTV, cohort |
| Webhooks | `/api/v1/webhooks` | Subscribe to events, logs |
| API Keys | `/api/v1/api-keys` | Create/revoke (admin) |
| Custom Domains | `/api/v1/domains` | Domain mapping, DNS verification |
| Portal | `/api/v1/portal` | Client-facing: invoices, quotes, payments, disputes |
| Notifications | `/api/v1/notifications` | Management |
| Settings | `/api/v1/settings` | Tax rates, gateways, templates, numbering |
| Search | `/api/v1/search` | Full-text search |
| Currency | `/api/v1/currencies` | Currency list, exchange rates |
| Gateways | `/api/v1/gateways` | Payment gateway config |
| Upload | `/api/v1/upload` | File upload |

### Tax Engine Coverage
| Region | Features |
|--------|----------|
| India (GST) | CGST+SGST/IGST, 5 slabs, HSN/SAC, TDS, reverse charge, e-Invoice, e-Way Bill |
| UAE | 5% VAT, excise 50-100%, corporate tax 0/9/15%, TRN validation |
| EU (27 countries) + UK | Standard/reduced/super-reduced/zero/parking rates, reverse charge B2B |
| US (50 states + DC) | State base rates, county/city stacking, nexus, no-tax states |

---

## EMP Monitor

**Tech Stack**: QT (desktop), Laravel (frontend), Node.js (backend)
**Database**: Separate (not MySQL shared instance)
**Repo**: https://github.com/EmpCloud/emp-monitor

EMP Monitor is an employee monitoring and productivity platform. Unlike other EMP modules, it uses a different tech stack (QT for cross-platform desktop client, Laravel for web frontend, Node.js for backend). The README does not list specific API endpoints.

### Features
- Employee monitoring and productivity tracking
- Time tracking (work hours, active/idle time)
- User activity monitoring (app/website usage)
- Insider threat detection and DLP
- Attendance monitoring
- Workforce productivity analytics
- Project management integration
- Screenshots and activity logging

---

## EMP Project

**API Base**: `/v1/` on ports 9000 (Project API) and 9001 (Task API)
**Database**: MongoDB
**Repo**: https://github.com/EmpCloud/emp-project

### Services
| Service | Port | Purpose |
|---------|------|---------|
| Client | 3000 | Next.js web dashboard |
| Project API | 9000 | Admin, users, roles, projects, reports, uploads |
| Task API | 9001 | Task/subtask workflows |

### API Documentation
- Project API Swagger: `http://localhost:9000/explorer`
- Task API: check service output for explorer URL

### Environment
- `PROJECT_API=http://localhost:9000/v1`
- `TASK_API=http://localhost:9001/v1`

---

## EMP Field

**Tech Stack**: React 18, Node.js/Express, MongoDB, Mongoose
**Database**: MongoDB
**Repo**: https://github.com/EmpCloud/emp-field

### Features
- Real-time GPS location tracking
- Geofence-aware activity
- Attendance and leave management
- Task assignment and stage progression
- Client management
- Exportable reports and analytics

### API
- Backend base path: `/v1/*` routes
- Swagger docs at `/api-doc`

---

## EMP Biometrics

**Repo**: https://github.com/EmpCloud/emp-biometrics
**Status**: No README found (404). Biometric APIs are built into EMP Cloud core under `/api/v1/biometrics`.

---

## Role-Based Access Control

### EMP Cloud Roles
| Role | Access Level |
|------|-------------|
| **Super Admin** | Platform-wide: all orgs, all modules, health dashboard, data sanity, log dashboard, AI config |
| **Org Admin** | Full org access: employees, attendance, leave, documents, subscriptions, billing, settings |
| **HR Admin** | HR functions: employees, attendance, leave, documents, announcements, policies, helpdesk, surveys |
| **Employee** | Self-service: own profile, attendance, leave, documents, notifications, self-service dashboard |

### EMP Billing Roles
| Role | Access |
|------|--------|
| Owner | Full access |
| Admin | Full access |
| Accountant | Financial operations |
| Sales | Client and quote management |
| Viewer | Read-only access |

### Module-Level RBAC
Each module implements RBAC via middleware. Typical pattern:
- **Admin/Manager** -- Full CRUD, settings, analytics
- **Employee** -- Self-service views only (my reviews, my goals, my kudos, etc.)
- Auth middleware extracts user role from JWT and enforces route-level access

---

## API Response Format

All modules use a consistent response structure:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

### Paginated Response
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "totalPages": 8
  }
}
```

---

## Database Schema Summary

### EMP Cloud (`empcloud` -- 29 migrations)
**Identity**: organizations, users, roles, user_roles, organization_departments, organization_locations, modules, org_subscriptions, org_module_seats, module_features, oauth_clients, oauth_authorization_codes, oauth_access_tokens, oauth_refresh_tokens, oauth_scopes, signing_keys, audit_logs, invitations

**Employee**: employee_profiles, employee_addresses, employee_education, employee_work_experience, employee_dependents

**Attendance**: shifts, shift_assignments, geo_fence_locations, attendance_records, attendance_regularizations

**Leave**: leave_types, leave_policies, leave_balances, leave_applications, leave_approvals, comp_off_requests

**Documents**: document_categories, employee_documents

**Announcements**: announcements, announcement_reads

**Policies**: company_policies, policy_acknowledgments

**Notifications**: notifications

**Extended**: helpdesk_tickets, helpdesk_categories, knowledge_base_articles, surveys, survey_questions, survey_responses, assets, asset_categories, asset_assignments, positions, headcount_plans, anonymous_feedback, company_events, event_registrations, whistleblowing_reports, chatbot_conversations, chatbot_messages, forum_categories, forum_posts, forum_replies, wellness_check_ins, wellness_goals, shift_swap_requests, custom_field_definitions, custom_field_values, ai_provider_configs, kb_article_ratings

### EMP Payroll (`emp_payroll` -- 19 migrations)
employees, salary_structures, salary_components, payroll_runs, payslips, bank_details, tax_info, pf_details, employee_notes, attendance records, leave_balances, loans, reimbursements, benefits, insurance, GL mappings, journal entries, global employees, contractor invoices, EWA, benchmarks, etc.

### EMP Recruit (`emp_recruit` -- 8 migrations)
job_postings, candidates, applications, application_stage_history, interviews, interview_panelists, interview_feedback, interview_recordings, interview_transcripts, offers, offer_approvers, offer_letters, onboarding_templates, onboarding_template_tasks, onboarding_checklists, onboarding_tasks, referrals, email_templates, career_pages, job_board_postings, recruitment_events, candidate_portal_tokens, resume_scores, pipeline_stage_configs, background_checks, candidate_surveys, psychometric_assessments

### EMP Performance (`emp_performance` -- 6 migrations)
competency_frameworks, competencies, review_cycles, review_cycle_participants, reviews, review_competency_ratings, goals, key_results, goal_check_ins, goal_alignments, performance_improvement_plans, pip_objectives, pip_updates, continuous_feedback, career_paths, career_path_levels, employee_career_tracks, one_on_one_meetings, meeting_agenda_items, peer_review_nominations, rating_distributions, nine_box_placements, succession_plans, succession_candidates, skills_assessments, letter_templates, generated_letters, email_reminder_configs, manager_effectiveness_scores, audit_logs

### EMP Rewards (`emp_rewards` -- 7 migrations)
recognition_settings, recognition_categories, kudos, kudos_reactions, kudos_comments, point_balances, point_transactions, badge_definitions, user_badges, reward_catalog, reward_redemptions, nomination_programs, nominations, leaderboard_cache, recognition_budgets, celebration_events, notifications, team_challenges, challenge_participants, milestone_rules, slack_integrations

### EMP Exit (`emp_exit` -- 4 migrations)
exit_requests, exit_checklist_templates, exit_checklist_template_items, exit_checklist_instances, clearance_departments, clearance_records, exit_interview_templates, exit_interview_questions, exit_interviews, exit_interview_responses, fnf_settlements, asset_returns, knowledge_transfers, kt_items, letter_templates, generated_letters, bgv_records, reference_checks, alumni_profiles, exit_settings, attrition_scores, buyout_requests, rehire_applications, exit_survey_responses, exit_email_logs, audit_logs

### EMP LMS (`emp_lms` -- 1 migration)
courses, course_modules, lessons, course_categories, enrollments, lesson_progress, quizzes, questions, quiz_attempts, quiz_attempt_answers, learning_paths, learning_path_courses, learning_path_enrollments, certificates, certificate_templates, compliance_assignments, compliance_records, ilt_sessions, ilt_attendance, scorm_packages, scorm_tracking, content_library, course_ratings, discussions, user_learning_profiles, notifications, audit_logs

### EMP Billing (`emp_billing` -- 17 migrations)
organizations, users, clients, client_contacts, products, price_lists, tax_rates, invoices, invoice_items, quotes, quote_items, credit_notes, credit_note_items, payments, payment_allocations, expenses, expense_categories, vendors, recurring_profiles, recurring_executions, templates, client_portal_access, webhooks, webhook_deliveries, audit_logs, settings, notifications, disputes, scheduled_reports, subscriptions, plans, usage_records, coupons, dunning_attempts, saved_payment_methods, custom_domains, api_keys

---

## Environment Variables Reference

### EMP Cloud
```
PORT=3000
NODE_ENV=development
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=secret
DB_NAME=empcloud
REDIS_HOST=localhost
REDIS_PORT=6379
RSA_PRIVATE_KEY_PATH=./keys/private.pem
RSA_PUBLIC_KEY_PATH=./keys/public.pem
ACCESS_TOKEN_EXPIRY=15m
REFRESH_TOKEN_EXPIRY=7d
AUTH_CODE_EXPIRY=10m
ALLOWED_ORIGINS=http://localhost:5173,...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
SMTP_HOST=localhost
SMTP_PORT=1025
```

### EMP Payroll
```
PORT=4000
DB_PROVIDER=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=emp_payroll
DB_USER=root
DB_PASSWORD=...
JWT_SECRET=change-this
JWT_ACCESS_EXPIRY=15m
JWT_REFRESH_EXPIRY=7d
CORS_ORIGIN=http://localhost:5173
PAYROLL_COUNTRY=IN
USE_CLOUD_HRMS=false
EMP_CLOUD_URL=...
REDIS_URL=redis://localhost:6379
SMTP_HOST=...
SMTP_PORT=587
```

### EMP Recruit
```
PORT=4500
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=secret
DB_NAME=emp_recruit
EMPCLOUD_DB_NAME=empcloud
EMPCLOUD_API_URL=http://localhost:3000
EMPCLOUD_PUBLIC_KEY_PATH=./keys/public.pem
REDIS_HOST=localhost
REDIS_PORT=6379
SMTP_HOST=localhost
SMTP_PORT=1025
```

### EMP Performance
```
PORT=4300
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=secret
DB_NAME=emp_performance
EMPCLOUD_DB_NAME=empcloud
EMPCLOUD_API_URL=http://localhost:3000
EMPCLOUD_PUBLIC_KEY_PATH=./keys/public.pem
REDIS_HOST=localhost
REDIS_PORT=6379
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
SMTP_HOST=localhost
SMTP_PORT=1025
```

### EMP LMS
```
PORT=4700
DB_HOST=localhost
DB_NAME=emp_lms
EMPCLOUD_DB_NAME=empcloud
REDIS_HOST=localhost
JWT_SECRET=...
SMTP_HOST=localhost
AI_API_KEY=...
REWARDS_API_URL=...
```

### EMP Billing
```
PORT=4001
DB_PROVIDER=mysql
DB_HOST=localhost
DB_NAME=emp_billing
JWT_SECRET=...
STRIPE_SECRET_KEY=...
RAZORPAY_KEY_ID=...
PAYPAL_CLIENT_ID=...
```

### EMP Rewards
```
PORT=4600
DB_NAME=emp_rewards
(similar pattern to other modules)
```

### EMP Exit
```
PORT=4400
DB_NAME=emp_exit
(similar pattern to other modules)
```

### EMP Project
```
PROJECT_API=http://localhost:9000/v1
TASK_API=http://localhost:9001/v1
(MongoDB-based, see localDev.json configs)
```

### EMP Field
```
(MongoDB-based, see packages/server/.env)
```

---

## Testing Instructions Per Module

| Module | Command | Tests |
|--------|---------|-------|
| EMP Cloud | `pnpm --filter server test` / `npx playwright test` | 700+ (277 E2E + 161 API + 285 unit + 109 security) |
| EMP Payroll | `pnpm --filter @emp-payroll/server exec vitest run` | 67 (40 unit + 27 integration) |
| EMP Recruit | `pnpm --filter @emp-recruit/server test` | 206+ (109 API + 58 E2E + 33 interview + 6 SSO + 21 Playwright) |
| EMP Performance | `pnpm --filter @emp-performance/server test` | 263 (128 API + 34 E2E + 62 advanced + 39 unit) |
| EMP Rewards | Manual + automated | Covers 18 route + 17 service modules |
| EMP Exit | Manual + automated | Covers 17 route + 15 service modules |
| EMP LMS | `pnpm exec vitest run` (in packages/server) | 657 tests, 28 suites |
| EMP Billing | `pnpm run test` | 778+ unit + 130 E2E Playwright |
| EMP Project | Via npm scripts per package | See package docs |
| EMP Field | Via npm scripts per package | See package docs |

### Swagger UI URLs (per module)
Every module serves Swagger UI at `/api/docs` (or `/explorer` for EMP Project).
