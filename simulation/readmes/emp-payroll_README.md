# EMP Payroll

> Multi-country payroll engine with India TDS/PF/ESI, US Federal/State/FICA, UK PAYE/NIC -- plus loans, reimbursements, benefits, GL accounting, insurance, global payroll/EOR, earned wage access, pay equity, and compensation benchmarking.

[![Part of EmpCloud](https://img.shields.io/badge/EmpCloud-Module-blue)]()
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-purple.svg)](LICENSE)
[![Tests: 67 passing](https://img.shields.io/badge/tests-67%20passing-brightgreen.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

EMP Payroll is the payroll management module of the [EmpCloud](https://empcloud.com) HRMS ecosystem. India-first payroll engine with PF, ESI, TDS, and Professional Tax built in. Multi-country tax support covers India (FY 2025-26), United States (federal + 50 states), and United Kingdom (PAYE + NIC). Includes salary structure builder, payroll processing lifecycle, payslip generation, bank transfer files, statutory reports, employee benefits, group insurance, GL accounting integration, global payroll for 30 countries with EOR/contractor support, earned wage access, pay equity analysis, and compensation benchmarking.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Frontend Pages](#frontend-pages)
- [Testing](#testing)
- [Test Deployment](#test-deployment)
- [Environment Variables](#environment-variables)
- [License](#license)

---

## Features

### Payroll Engine

| Feature | Description |
|---------|-------------|
| **Salary Structure Builder** | CTC breakdown with configurable components (Basic, HRA, SA, LTA, custom). Assign structures to employees with auto-calculated component splits. |
| **Payroll Processing** | Full lifecycle: Draft > Compute > Approve > Pay with complete audit trail. Payroll variance alerts detect zero net pay or high deduction ratios. |
| **Payslip Generation** | Printable HTML payslips with company header, earnings/deductions breakdown, and YTD totals. Batch email all payslips for a run. |
| **Bank Transfer File** | NEFT/RTGS CSV generation for direct salary credit to employee bank accounts. |
| **Payroll Analytics** | Cost trends, month-over-month comparison, headcount charts, department breakdown, cost pie charts. |

### Multi-Country Tax Engines

| Country | Coverage |
|---------|----------|
| **India (FY 2025-26)** | Old & New regime TDS with Sec 87A rebate, marginal relief, surcharge, 4% cess. EPF (12%) with EPS, admin/EDLI charges, PF ECR generation. ESI (0.75% + 3.25%). Professional Tax for 7 states (Karnataka, Maharashtra, Tamil Nadu, Telangana, West Bengal, Gujarat, Delhi). Form 16 Part A + Part B. |
| **United States** | W-4 based federal withholding with bracket computation. FICA: Social Security (6.2% up to $176,100 wage base) + Medicare (1.45% + 0.9% additional). 50-state tax support (flat/progressive/no-income-tax). FUTA employer unemployment tax. |
| **United Kingdom** | PAYE income tax (cumulative/non-cumulative, all tax codes). National Insurance (Category A/C employee + employer). Student Loan (Plan 1, 2, 4, 5). Auto-enrollment pension (qualifying earnings). Scottish/Welsh regional tax bands. |

### Employee Management

| Feature | Description |
|---------|-------------|
| **Employee CRUD** | Full profile with personal, bank, tax, PF details. CSV import/export. Department filters and instant search. |
| **Salary Assignment** | Assign structures, revise CTC with auto-calculated breakdown. Salary revision history with effective dates. |
| **Employee Notes** | Categorized notes (general, performance, HR, finance) with author tracking. |
| **Employee Timeline** | Visual history showing join date, salary revisions, payslips. YTD summary per employee. |
| **Org Chart** | Visual organizational hierarchy. |

### Loans & Reimbursements

| Feature | Description |
|---------|-------------|
| **Employee Loans** | Salary advance, emergency loan, personal loan with EMI tracking. Record payments, auto-calculate outstanding balance. |
| **Reimbursement Claims** | Submit, approve, reject, pay expense claims. Category-based (medical, travel, food, equipment, internet, books). Visual progress bar. |

### Benefits & Insurance

| Feature | Description |
|---------|-------------|
| **Benefits Plans** | Create benefit plans (health, dental, vision, retirement, wellness, education, transport, meal). Employee enrollment and contribution tracking. Admin dashboard with plan statistics. |
| **Group Insurance** | Insurance policy management (health, life, accident, disability, dental, vision, critical illness). Employee enrollment, dependent coverage, and claims processing with review workflow. |

### GL Accounting

| Feature | Description |
|---------|-------------|
| **GL Mappings** | Map payroll components to general ledger account codes. |
| **Journal Entries** | Auto-generate journal entries from payroll runs. Export journal entry reports. |
| **Period Summaries** | GL period summary with account-wise totals. |

### Global Payroll & EOR

| Feature | Description |
|---------|-------------|
| **30-Country Support** | Country profiles with tax rules, currency, statutory requirements across 6 regions (Asia-Pacific, Europe, Middle East, Americas, Africa). |
| **Global Employees** | Manage employees across countries with country-specific employment type (full-time, part-time, contractor, EOR). |
| **Global Payroll Runs** | Country-specific payroll processing with local currency. Multi-country cost analysis dashboard. |
| **Contractor Invoices** | Submit and manage contractor invoices with approval workflow. |
| **Country Compliance** | Track compliance items per country with status and deadlines. |

### Earned Wage Access

| Feature | Description |
|---------|-------------|
| **EWA Settings** | Configure max advance percentage, fee structure, minimum days worked, and auto-repay rules per org. |
| **Employee Requests** | Employees request early wage access against earned but unpaid salary. Eligibility calculation based on days worked. |
| **Approval & Disbursement** | Admin approval workflow. Auto-repay from next payroll run. |

### Pay Equity & Compensation

| Feature | Description |
|---------|-------------|
| **Pay Equity Analysis** | Analyze pay gaps across dimensions (gender, department, role, location). Compliance report generation. |
| **Compensation Benchmarking** | Import and manage market salary benchmarks by job title and department. Compare actual compensation against market data. Percentile analysis and import support. |
| **Total Rewards Statement** | Comprehensive view of employee compensation: salary, benefits, insurance, bonuses. |

### Tax Declarations

| Feature | Description |
|---------|-------------|
| **Self-Service Declarations** | Employees submit 80C/80D/NPS/HRA investment proofs. Quick declare wizard for all sections. |
| **Approval Workflow** | HR reviews and approves declarations. |
| **Form 16 Generation** | Downloadable Form 16 (Part A + Part B). |

### Attendance & Leave

| Feature | Description |
|---------|-------------|
| **Attendance Summary** | Per-employee monthly summary (present, absent, LOP, overtime). Bulk "Mark All Present". CSV/API import for biometric integration. |
| **Leave Balances** | Earned/casual/sick/privilege leave tracking per financial year. Holiday calendar. |
| **Cloud HRMS Proxy** | When `USE_CLOUD_HRMS=true`, fetches attendance and leave data from EMP Cloud instead of local tables. |

### UI & UX

| Feature | Description |
|---------|-------------|
| **Dark Mode** | Light / Dark / System with persistent toggle. |
| **Command Palette** | Ctrl+K to search pages, employees, actions. |
| **Keyboard Navigation** | G+D (Dashboard), G+E (Employees), G+P (Payroll), G+S (Settings), G+R (Reports), G+A (Attendance). Press ? for shortcut reference. |
| **Mobile Responsive** | Hamburger menu, adaptive layouts, lazy loading for all 40+ pages. |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 6, TypeScript, Tailwind CSS 4, React Query |
| Backend | Node.js 20, Express 5, TypeScript |
| Database | MySQL 8 (default) / PostgreSQL / MongoDB |
| Cache | Redis 7 |
| Auth | JWT (access + refresh tokens) + bcrypt. SSO via EMP Cloud OAuth2. |
| Validation | Zod (server-side request validation) |
| Charts | Recharts (bar, line, area, pie) |
| Email | Nodemailer (SMTP) |
| Testing | Vitest (67 tests: 40 unit + 27 integration) |
| Monorepo | pnpm workspaces (3 packages) |

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/EmpCloud/emp-payroll.git
cd emp-payroll
docker compose up -d --build
```

Wait ~30 seconds for MySQL to initialize, then seed demo data:

```bash
docker exec emp-payroll-server pnpm --filter @emp-payroll/server exec tsx src/db/seed.ts
```

Access:
- **Frontend**: http://localhost:5175
- **API**: http://localhost:4000
- **API Docs**: http://localhost:4000/api/v1/docs/openapi.json
- **Login**: `ananya@technova.in` / `Welcome@123`

### Option 2: Local Development

**Prerequisites:** Node.js >= 20, pnpm >= 9, MySQL 8+

```bash
git clone https://github.com/EmpCloud/emp-payroll.git
cd emp-payroll
pnpm install

# Configure environment
cp packages/server/.env.example packages/server/.env
# Edit .env with your MySQL credentials

# Run migrations + seed
pnpm --filter @emp-payroll/server exec tsx src/db/migrate.ts
pnpm --filter @emp-payroll/server exec tsx src/db/seed.ts

# Start dev servers (in separate terminals)
pnpm --filter @emp-payroll/server dev    # API on :4000
pnpm --filter @emp-payroll/client dev    # UI on :5173
```

### Option 3: Production Deploy

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Serves on port 80 with nginx reverse proxy, gzip compression, and static asset caching.

---

## Project Structure

```
emp-payroll/
  packages/
    shared/                 # Shared types, tax constants (India/US/UK)
      src/
        types/              # TypeScript interfaces & enums
        constants/          # Tax brackets, PF/ESI rates, state taxes
    server/                 # Express API (90+ endpoints)
      src/
        api/
          routes/           # 26 route modules
          middleware/        # Auth, rate-limit, error handling
          validators/       # Zod request schemas
          docs.ts           # OpenAPI specification
        services/           # 50+ business logic services
          tax/              # India, US, UK tax engines
          compliance/       # PF, ESI, PT statutory calculations
        db/
          adapters/         # Knex (MySQL/PG) + MongoDB adapters
          migrations/sql/   # 19 migration files
          seed.ts           # Demo data seeder
        config/             # Env validation, app config
      tests/
        unit/               # 40 unit tests (tax engines)
        integration/        # 27 API integration tests
    client/                 # React SPA (40+ pages)
      src/
        api/                # Axios client, React Query hooks, auth
        components/
          layout/           # DashboardLayout, Sidebar, AuthLayout
          ui/               # 20+ reusable components
        pages/              # 27 page modules (lazy-loaded)
        lib/                # Utils, theme provider
        styles/             # Tailwind + dark mode CSS
  docker/                   # Dockerfiles (dev + prod), nginx.conf
  docker-compose.yml        # Development setup
  docker-compose.prod.yml   # Production setup
  .github/workflows/ci.yml  # CI pipeline
```

---

## API Endpoints

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Login with email/password |
| POST | `/register` | Register new user |
| POST | `/refresh-token` | Refresh access token |
| POST | `/change-password` | Change own password |
| POST | `/reset-employee-password` | Admin reset password |

### Employees (`/api/v1/employees`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List employees (paginated, filterable) |
| POST | `/` | Create employee |
| GET | `/export` | Export CSV |
| GET | `/:id` | Get employee detail |
| PUT | `/:id` | Update employee |
| DELETE | `/:id` | Deactivate employee |
| GET | `/:id/bank-details` | Get bank details |
| PUT | `/:id/bank-details` | Update bank details |
| GET | `/:id/tax-info` | Get tax info |
| PUT | `/:id/tax-info` | Update tax info |
| GET | `/:id/pf-details` | Get PF details |
| PUT | `/:id/pf-details` | Update PF details |
| GET | `/:id/notes` | List employee notes |
| POST | `/:id/notes` | Add note |
| DELETE | `/:id/notes/:noteId` | Delete note |

### Payroll (`/api/v1/payroll`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List payroll runs |
| POST | `/` | Create payroll run |
| GET | `/:id` | Get run details |
| POST | `/:id/compute` | Compute payroll |
| POST | `/:id/approve` | Approve payroll |
| POST | `/:id/pay` | Mark as paid |
| POST | `/:id/cancel` | Cancel run |
| GET | `/:id/payslips` | Get run payslips |
| POST | `/:id/send-payslips` | Email payslips to all employees |
| GET | `/:id/reports/pf` | Download PF ECR file |
| GET | `/:id/reports/esi` | Download ESI return |
| GET | `/:id/reports/pt` | Download PT return |
| GET | `/:id/reports/tds` | Get TDS summary |
| GET | `/:id/reports/bank-file` | Download bank transfer file |

### Salary Structures (`/api/v1/salary-structures`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List structures |
| POST | `/` | Create structure |
| GET | `/:id/components` | Get components |
| POST | `/assign` | Assign to employee |
| GET | `/employee/:empId` | Get employee salary |
| GET | `/employee/:empId/history` | Get salary revision history |

### Benefits (`/api/v1/benefits`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Benefits admin dashboard stats |
| GET | `/plans` | List benefit plans |
| POST | `/plans` | Create benefit plan |
| GET | `/plans/:id` | Get plan detail |
| PUT | `/plans/:id` | Update plan |
| GET | `/enrollments` | List enrollments |
| POST | `/enrollments` | Enroll employee |
| GET | `/my` | My enrolled benefits |

### Insurance (`/api/v1/insurance`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Insurance dashboard stats |
| GET | `/policies` | List insurance policies |
| POST | `/policies` | Create insurance policy |
| GET | `/policies/:id` | Get policy detail |
| PUT | `/policies/:id` | Update policy |
| GET | `/enrollments` | List enrollments |
| POST | `/enrollments` | Enroll employee |
| GET | `/claims` | List insurance claims |
| POST | `/claims` | Submit claim |
| PUT | `/claims/:id/review` | Review claim |

### GL Accounting (`/api/v1/gl-accounting`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mappings` | List GL mappings |
| POST | `/mappings` | Create GL mapping |
| PUT | `/mappings/:id` | Update mapping |
| DELETE | `/mappings/:id` | Delete mapping |
| POST | `/journal-entries/generate` | Generate journal entries from payroll run |
| GET | `/journal-entries` | List journal entries |
| GET | `/period-summary` | GL period summary |

### Global Payroll (`/api/v1/global-payroll`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Global payroll dashboard |
| GET | `/cost-analysis` | Multi-country cost analysis |
| GET | `/countries` | List supported countries |
| GET | `/countries/:id` | Country detail |
| GET | `/employees` | List global employees |
| POST | `/employees` | Add global employee |
| GET | `/employees/:id` | Global employee detail |
| PUT | `/employees/:id` | Update global employee |
| GET | `/runs` | List global payroll runs |
| POST | `/runs` | Create global payroll run |
| GET | `/contractor-invoices` | List contractor invoices |
| POST | `/contractor-invoices` | Submit contractor invoice |
| GET | `/compliance` | Country compliance items |
| PUT | `/compliance/:id` | Update compliance status |

### Earned Wage Access (`/api/v1/earned-wage`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/settings` | Get EWA settings |
| PUT | `/settings` | Update EWA settings (admin) |
| GET | `/requests` | List all EWA requests |
| POST | `/requests` | Create EWA request |
| GET | `/requests/:id` | Get request detail |
| PUT | `/requests/:id/approve` | Approve request |
| PUT | `/requests/:id/reject` | Reject request |
| GET | `/my/eligibility` | Check my EWA eligibility |
| GET | `/my/requests` | My EWA requests |

### Pay Equity (`/api/v1/pay-equity`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analysis` | Pay equity analysis (by dimension: gender, department, role) |
| GET | `/compliance-report` | Generate pay equity compliance report |

### Compensation Benchmarking (`/api/v1/compensation-benchmarks`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List benchmarks |
| POST | `/` | Create benchmark |
| GET | `/:id` | Get benchmark detail |
| PUT | `/:id` | Update benchmark |
| DELETE | `/:id` | Delete benchmark |
| POST | `/import` | Bulk import benchmarks |
| GET | `/comparison` | Compare actual vs. market compensation |

### Self-Service (`/api/v1/self-service`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Employee dashboard data |
| GET | `/payslips` | My payslips |
| GET | `/payslips/:id/pdf` | Download payslip PDF |
| GET | `/salary` | My salary details |
| GET | `/tax/computation` | My tax computation |
| GET | `/tax/declarations` | My declarations |
| POST | `/tax/declarations` | Submit declarations |
| GET | `/tax/form16` | Download Form 16 |
| GET | `/reimbursements` | My reimbursements |
| POST | `/reimbursements` | Submit reimbursement claim |
| GET | `/profile` | My profile |

### Other Modules

| Module | Base Path | Key Endpoints |
|--------|-----------|---------------|
| Attendance | `/api/v1/attendance` | Summary, import, LOP override |
| Leaves | `/api/v1/leaves` | Balances, record, adjust |
| Loans | `/api/v1/loans` | CRUD, payments, EMI tracking |
| Reimbursements | `/api/v1/reimbursements` | Approve, reject, pay |
| Tax | `/api/v1/tax` | Compute, declarations, Form 16 |
| Total Rewards | `/api/v1/total-rewards` | Employee total rewards statement |
| Adjustments | `/api/v1/adjustments` | Salary adjustments, bonus, arrears |
| Announcements | `/api/v1/announcements` | Company announcements |
| Organizations | `/api/v1/organizations` | Settings, activity log |
| Webhooks | `/api/v1/webhooks` | Inbound/outbound event hooks |
| Health | `/health` | Basic + detailed health checks |
| Docs | `/api/v1/docs/openapi.json` | OpenAPI 3.0.3 spec |

---

## Frontend Pages

### Admin Dashboard (27 page modules)

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/` | Stats, charts, quick actions, recent activity |
| Employee List | `/employees` | Searchable list with department filters |
| Employee Detail | `/employees/:id` | Full profile, salary, notes, timeline, YTD |
| New Employee | `/employees/new` | Employee creation form |
| Org Chart | `/employees/org-chart` | Organizational hierarchy |
| Payroll Runs | `/payroll/runs` | List runs, create new |
| Run Detail | `/payroll/runs/:id` | Compute/approve/pay, charts, alerts |
| Salary Structures | `/payroll/salary-structures` | Create/view structures with components |
| Analytics | `/payroll/analytics` | Trend charts, MoM comparison |
| Payslips | `/payslips` | Browse all payslips, export CSV |
| Attendance | `/attendance` | Monthly summary, bulk marking |
| Reports | `/reports` | PF ECR, ESI, PT, TDS downloads |
| Benefits | `/benefits` | Benefit plan management and enrollment |
| Insurance | `/insurance` | Insurance policies, enrollments, claims |
| GL Accounting | `/gl-accounting` | GL mappings, journal entries, period summary |
| Global Payroll | `/global-payroll` | Dashboard, countries, global employees, runs |
| Global Employees | `/global-payroll/employees` | Global employee management |
| Contractor Invoices | `/global-payroll/invoices` | Contractor invoice management |
| Country Compliance | `/global-payroll/compliance` | Country-level compliance tracking |
| Earned Wage Access | `/earned-wage` | EWA settings, requests, approvals |
| Pay Equity | `/pay-equity` | Pay gap analysis and compliance reports |
| Benchmarks | `/benchmarks` | Compensation benchmarking data |
| Total Rewards | `/total-rewards` | Total rewards statements |
| Leaves | `/leaves` | Leave management |
| Loans | `/loans` | Loan management and EMI tracking |
| Exits | `/exits` | Exit management integration |
| Settings | `/settings` | Org info, statutory, payment config |
| Audit Log | `/audit-log` | System activity history |
| System Health | `/system/health` | Uptime, DB, memory monitoring |

### Self-Service Portal (8 pages)

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/my` | Personal stats, quick links |
| Payslips | `/my/payslips` | View/download payslips, dispute |
| Salary | `/my/salary` | CTC breakdown |
| Tax | `/my/tax` | Tax computation, Form 16 |
| Declarations | `/my/declarations` | Submit/track investment proofs |
| Reimbursements | `/my/reimbursements` | Submit/track expense claims |
| Leaves | `/my/leaves` | Leave balances and requests |
| Profile | `/my/profile` | Personal details, change password |

---

## Testing

### Running Tests

```bash
# All tests (unit + integration)
pnpm --filter @emp-payroll/server exec vitest run

# Unit tests only
pnpm --filter @emp-payroll/server exec vitest run tests/unit/

# Integration tests only (requires running server)
pnpm --filter @emp-payroll/server exec vitest run tests/integration/

# Type checking
pnpm --filter @emp-payroll/server exec tsc --noEmit
pnpm --filter @emp-payroll/client exec tsc --noEmit
```

### Test Coverage (67 tests)

| File | Tests | Coverage |
|------|-------|----------|
| `unit/india-tax.test.ts` | 9 | Income tax old/new regime, 80C, HRA, rebate, cess |
| `unit/india-statutory.test.ts` | 9 | PF (ceiling, VPF, DA), ESI, Professional Tax per state |
| `unit/us-tax.test.ts` | 10 | Federal withholding, FICA, Medicare, state tax, FUTA |
| `unit/uk-tax.test.ts` | 12 | PAYE, NIC, student loan, pension, employer cost |
| `integration/api.test.ts` | 27 | Auth, employees, payroll, payslips, salary, notes, attendance, self-service, API docs |

---

## Test Deployment

| Environment | URL |
|-------------|-----|
| Frontend | https://testpayroll.empcloud.com |
| API | https://testpayroll-api.empcloud.com |

SSO integrated with EMP Cloud. HRMS proxy enabled (`USE_CLOUD_HRMS=true`) -- attendance and leave data fetched from EMP Cloud.

---

## Demo Data

The seed creates a complete demo environment:

| Entity | Details |
|--------|---------|
| Organization | TechNova Solutions Pvt. Ltd. (Bengaluru, Karnataka) |
| Employees | 10 (Ananya Gupta as HR Admin + 9 team members) |
| Departments | Engineering, Design, Product, Finance, HR |
| Salary Structure | Standard CTC (Basic 40%, HRA 50% of Basic, SA) |
| Payroll Run | February 2026 (fully paid with 10 payslips) |
| Login | `ananya@technova.in` / `Welcome@123` |

---

## Environment Variables

See `packages/server/.env.example` for all options.

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PROVIDER` | `mysql` | Database: mysql, postgres, mongodb |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `3306` | Database port |
| `DB_NAME` | `emp_payroll` | Database name |
| `DB_USER` | `root` | Database user |
| `DB_PASSWORD` | -- | Database password |
| `JWT_SECRET` | `change-this` | JWT signing secret |
| `JWT_ACCESS_EXPIRY` | `15m` | Access token lifetime |
| `JWT_REFRESH_EXPIRY` | `7d` | Refresh token lifetime |
| `CORS_ORIGIN` | `http://localhost:5173` | Allowed frontend origin |
| `PAYROLL_COUNTRY` | `IN` | Default country for tax rules (IN, US, UK) |
| `USE_CLOUD_HRMS` | `false` | Fetch attendance/leave from EMP Cloud |
| `EMP_CLOUD_URL` | -- | EMP Cloud API URL (for HRMS proxy) |
| `SMTP_HOST` | -- | Email server host |
| `SMTP_PORT` | `587` | Email server port |
| `SMTP_USER` | -- | Email username |
| `SMTP_PASS` | -- | Email password |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |

---

## License

This project is licensed under the [AGPL-3.0 License](LICENSE).
