# EMP Cloud — Definitive Test Plan for Automated Agents

**Target System:** `https://test-empcloud.empcloud.com`  
**API Prefix:** `/api/v1/`  
**Goal:** Empower E2E Testing Agents to autonomously test EMP Cloud across 15+ subdomains while simulating human workflows and adhering to strict E2E testing protocols.

---

## 1. CRITICAL AGENT INSTRUCTIONS (READ BEFORE TESTING)

> [!CAUTION]
> Testing agents must adhere strictly to these rules. Any bug report failing to follow these guidelines will be rejected by the Lead Tester.

1. **SSO is Mandatory for Modules**:
   - The EMP Cloud infrastructure utilizes a core API (`test-empcloud-api.empcloud.com`) and separate module APIs (e.g., `testpayroll-api`, `test-recruit-api`).
   - For any external module, you MUST authenticate via SSO. Generate a core JWT `access_token` and append it: `https://testpayroll.empcloud.com?sso_token=<token>`.
   - **DO NOT** test or report bugs on direct module logins (e.g. `POST /api/v1/auth/login` on the Payroll API). They will intentionally fail.
2. **Mandatory Evidence (Screenshots/Logs)**:
   - Every bug report must include a base64 or URL-hosted screenshot uploaded to `/screenshots/issue_{number}.png` or explicitly written API request/response logs.
3. **Handle "By Design" Features**:
   - `DELETE` actions usually trigger a "Soft Delete" (HTTP 200). Items remain accessible via `GET` for audit purposes. **Do not log this as a bug.**
   - Stored XSS explicitly visible in the DB is handled by React UI escaping. Target execution, not storage.
4. **Use Exact API Paths**:
   - Note key differences: `/api/v1/organizations/me/departments` (not `/departments`), `/v1/projects` (for Project module API), and `/api/v1/attendance/check-in`.

---

## 2. Testing Personas (Workflow Simulations)

Test the system exactly according to their daily tasks and assigned Role-Based Access Controls (RBAC).

### Persona A: Ananya Gupta (HR Manager / Org Admin)
*Login: ananya@technova.in / Welcome@123*
- **Morning Checks:** Check dashboard widgets, verify attendance (Present/Absent). Handle all pending leave applications from employees.
- **Onboarding Workflow:** Add employee (required fields + validation), assign a laptop (Assets module), upload an offer letter (Documents module).
- **Engagement:** Publish announcements, create a quarterly survey, post in the company Forum.

### Persona B: Priya (Employee / Software Engineer)
*Login: priya@technova.in / Welcome@123*
- **Self Service:** `POST /api/v1/attendance/check-in`, apply for sick leave. Read and acknowledge company policies.
- **Restrictions:** Verify Priya **cannot** access `/api/v1/admin/*` endpoints or see `/settings`.
- **SSO Access:** Open Payroll via SSO (`testpayroll`) and access self-service payslip PDFs. Launch Exit module to test voluntary resignation pipeline.

### Persona C: Vikram (Super Admin)
*Login: admin@empcloud.com / SuperAdmin@2026*
- **Platform Analytics:** Assess `/admin/health` and `/admin/organizations`.
- **Tenant Isolation:** Ensure Super Admin context switching accurately isolates data between multiple tenants. 

---

## 3. Core Business Logic & Cross-Module Data Flows (E2E Validation)

Agents must systematically verify that data propagates seamlessly via Webhooks/APIs across various systems. Test the following rules:

### A. Leave & Payroll Integrations
- [ ] **L001-L003:** An employee cannot apply for leave exceeding their accrued balance. The system must prevent negative balances.
- [ ] **L006 & P002:** An unapproved/rejected leave request results in Loss of Pay (LOP) within the Payroll module computation (`testpayroll-api`).
- [ ] **A008 & P005:** Overtime calculated natively in the Attendance table must cleanly pass into standard Salary Structures as Bonus Pay.

### B. Access Control & Cross-Tenant Data Isolation (CRITICAL)
- [ ] **MT001-MT005:** A user bearing an `{organization_id: A}` SSO JWT token explicitly must return a `403 Forbidden` or `404 Not Found` if they try to fetch `/employees/:id` from Organization B. 
- [ ] **E003-E004:** Test circular reporting logic. Prevent an employee from assigning themselves as their own manager.

### C. Assets Lifecycle
- [ ] **AS001-AS002:** Attempt to assign an already-assigned laptop to a new employee. Action must immediately fail.
- [ ] **EX003:** In the Exit Module (`test-exit` subdomain), an employee's final Full & Final (F&F) settlement must be locked until all items in the Assets Module are marked 'Returned'.

---

## 4. Subdomain & Module E2E Test Scope

Agents should systematically run testing against the working subsets of these defined APIs. Run validations on 400 Bad Requests and verify 200 OK payloads match schemas.

1. **Core (`test-empcloud-api`)**
   - Auth JWT `POST /api/v1/auth/login`
   - Employee directory and org-chart endpoint
   - Helpdesk tickets `GET/POST` & Announcement statuses
2. **Payroll (`testpayroll-api`)**
   - Rely heavily on `GET /api/v1/salary-structures/{id}/components`. 
   - Note: Substantial endpoints are missing (404/429 limits). Do not report standard 429 Rate Limits as code bugs. Run tests at slow intervals.
3. **Recruit (`test-recruit-api`)**
   - Manage ATS Pipeline: Move candidate POST `/api/v1/applications/{id}/stage` through stages. Score Resumes automatically.
4. **Performance (`test-performance-api`)**
   - Generate `GET /api/v1/goals` and bind `POST /api/v1/one-on-ones` to a review cycle. Validate 9-box grids.
5. **Rewards (`test-rewards-api`)**
   - `POST /api/v1/kudos` and ensure points integrate into `GET /api/v1/leaderboard`. Test push notifications payload.

---

> [!TIP]
> **Actionable Delivery for the Agent**
> Step 1. Pick a Persona. Step 2. Generate a valid Session JWT. Step 3. Launch an SSO Module. Step 4. Replicate a true working day simulation. Step 5. Compare API interactions against the Business Rules provided above.
> Make sure to report back to the Lead Tester with full POST request bodies when bugs are detected.
