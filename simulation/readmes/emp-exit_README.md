# EMP Exit

> Complete employee offboarding platform -- exit workflows, clearance, interviews, full & final settlement, knowledge transfer, alumni network, and predictive attrition.

[![Part of EmpCloud](https://img.shields.io/badge/EmpCloud-Module-blue)]()
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-purple.svg)](LICENSE)
[![Status: Built](https://img.shields.io/badge/Status-Built-green)]()

EMP Exit is the offboarding and exit management module of the [EmpCloud](https://empcloud.com) HRMS ecosystem. It provides configurable exit workflows with multi-department sign-off, exit interviews with structured feedback, full & final settlement calculation, asset return tracking, knowledge transfer documentation, letter generation (experience, relieving, service certificate), background verification, alumni network, predictive attrition dashboard with flight risk scoring, notice period buyout calculator, exit stage email notifications, rehire workflow pipeline, and exit survey NPS tracking.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Frontend Pages](#frontend-pages)
- [Test Suite](#test-suite)
- [Test Deployment](#test-deployment)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Exit Requests** | Initiate employee exits (resignation, termination, retirement, contract end). Configurable notice periods. Cancel or complete exits with user deactivation in EMP Cloud. |
| **Exit Interviews** | Structured interview templates with question sets. Record reason for leaving, ratings, and suggestions. Self-service submission by exiting employee. |
| **Offboarding Checklists** | Configurable checklist templates per org/department/role. Instantiated per exit with item-level completion tracking. |
| **Clearance Workflow** | Multi-department clearance sign-off (IT, Finance, HR, Admin, Manager). Per-department approval chain. View pending clearances assigned to you. |
| **Knowledge Transfer** | KT documentation with successor assignment. Individual KT checklist items with completion tracking. Handover verification. |
| **Full & Final Settlement** | Calculate pending salary, leave encashment, gratuity, deductions, notice recovery. Manual adjustments. Approval workflow. Mark as paid. Integrates with notice buyout. |
| **Asset Return Tracking** | Track assets to be returned by exiting employee. Update asset status, verify condition, record damage assessment. |
| **Letter Generation** | Org-specific Handlebars letter templates. Generate experience letter, relieving letter, service certificate as PDF. Email letters to employee. Download generated PDFs. |
| **Background Verification** | Store verification results and reference checks. Link to employment history. |
| **Alumni Network** | Optional alumni directory for ex-employees. Opt-in profiles. Rehire eligibility indicators. |
| **Flight Risk / Attrition Prediction** | Predictive flight risk scoring (0-100) for all employees. Risk factor analysis. Department-level attrition heatmap. Trend tracking over time. On-demand recalculation. |
| **Notice Period Buyout** | Calculate buyout amount based on remaining notice days and daily rate. Request/approve workflow. Integrates with F&F settlement. |
| **Rehire Workflow** | Pipeline: alumni -> screening -> approved -> hired. Reactivate user in EMP Cloud on hire. List rehire-eligible alumni. |
| **Exit Stage Email Notifications** | 6 branded Handlebars email templates for each exit milestone: initiation, clearance, interview, FnF, letter, completion. Preview and customize templates. Email delivery logging. |
| **Exit Survey NPS** | Net Promoter Score survey for exiting employees. NPS gauge visualization. Monthly/quarterly trend tracking. Department-level breakdown. |
| **Exit Analytics** | Attrition rate, reason breakdown (pie chart), department-wise trends, tenure at exit distribution, rehire pool statistics. |
| **API Documentation** | Swagger UI at `/api/docs` with full OpenAPI 3.0 spec. |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Runtime | Node.js 20 |
| Backend | Express 5, TypeScript |
| Frontend | React 19, Vite 6, TypeScript |
| Styling | Tailwind CSS, Radix UI |
| Database | MySQL 8 via Knex.js (`emp_exit` database) |
| Cache / Queue | Redis 7, BullMQ |
| Auth | OAuth2/OIDC via EMP Cloud (RS256 JWT verification) |
| PDF Generation | Puppeteer |
| Charts | Recharts |
| Email | Handlebars templates + Nodemailer |
| Monorepo | pnpm workspaces (3 packages) |

---

## Quick Start

### Prerequisites

- Node.js 20+
- pnpm 9+
- MySQL 8+
- Redis 7+
- EMP Cloud running (for authentication)
- EMP Payroll (optional, for salary data in F&F calculation)

### Install

```bash
git clone https://github.com/EmpCloud/emp-exit.git
cd emp-exit
pnpm install
```

### Environment Setup

```bash
cp .env.example .env
# Edit .env with your database credentials, Redis URL, and EMP Cloud URL
```

### Docker

```bash
docker-compose up -d
```

### Development

```bash
# Run all packages concurrently
pnpm dev

# Run individually
pnpm --filter @emp-exit/server dev    # Server on :4400
pnpm --filter @emp-exit/client dev    # Client on :5178

# Run migrations
pnpm --filter @emp-exit/server migrate
```

Once running, visit:
- **Client**: http://localhost:5178
- **API**: http://localhost:4400
- **API Documentation**: http://localhost:4400/api/docs

---

## Project Structure

```
emp-exit/
  package.json
  pnpm-workspace.yaml
  tsconfig.json
  docker-compose.yml
  .env.example
  packages/
    shared/                     # @emp-exit/shared
      src/
        types/                  # TypeScript interfaces & enums
        validators/             # Zod request validation schemas
        constants/              # Exit types, statuses, defaults
    server/                     # @emp-exit/server (port 4400)
      src/
        config/                 # Environment configuration
        db/
          connection.ts         # Knex connection to emp_exit
          empcloud.ts           # Read-only connection to empcloud DB
          migrations/sql/       # 4 migration files
        api/
          middleware/            # Auth, RBAC, error handling
          routes/               # 17 route modules
        services/               # 15 business logic service modules
        jobs/                   # BullMQ workers (notifications, letter gen, attrition scoring, email)
        utils/                  # Logger, errors, response helpers
        swagger/                # OpenAPI spec & Swagger UI setup
        templates/              # Handlebars email templates (6 exit stage templates)
    client/                     # @emp-exit/client (port 5178)
      src/
        api/                    # API client & hooks
        components/
          layout/               # DashboardLayout, SelfServiceLayout
          ui/                   # Radix-based UI primitives
          exit/                 # ExitStatusBadge, ClearanceProgress, FnFBreakdown, NPSGauge, RiskHeatmap
        pages/                  # 15 route-based page modules
        lib/                    # Auth store, utilities
```

---

## Database Schema

24+ tables across 4 migrations:

| Table | Purpose |
|-------|---------|
| `exit_requests` | Central exit record (type, dates, notice period, status, rehire eligibility) |
| `exit_checklist_templates` | Configurable checklists per org/department/role |
| `exit_checklist_template_items` | Items within a checklist template |
| `exit_checklist_instances` | Instantiated checklist items for a specific exit |
| `clearance_departments` | Departments that must sign off (IT, Finance, HR, Admin, Manager) |
| `clearance_records` | Per-exit, per-department clearance approval status |
| `exit_interview_templates` | Configurable exit interview question sets |
| `exit_interview_questions` | Questions within an interview template |
| `exit_interviews` | Completed interview records |
| `exit_interview_responses` | Individual answers to interview questions |
| `fnf_settlements` | Full & final settlement (earnings, deductions, net payable) |
| `asset_returns` | Assets to be returned by exiting employee |
| `knowledge_transfers` | KT record per exit with successor assignment |
| `kt_items` | Individual KT checklist items |
| `letter_templates` | Org-specific Handlebars letter templates |
| `generated_letters` | Generated letter PDFs for specific exits |
| `bgv_records` | Background verification records |
| `reference_checks` | Reference check records linked to BGV |
| `alumni_profiles` | Optional alumni directory entries |
| `exit_settings` | Per-org exit configuration |
| `attrition_scores` | Predictive flight risk scores (0-100) with risk factors |
| `buyout_requests` | Notice period buyout requests with calculated amounts and approval status |
| `rehire_applications` | Rehire pipeline records (alumni -> screening -> approved -> hired) |
| `exit_survey_responses` | NPS survey responses with score and comments |
| `exit_email_logs` | Log of sent exit stage notification emails |
| `audit_logs` | Module-specific audit trail |

---

## API Endpoints

All endpoints under `/api/v1/`. Server runs on port **4400**.

### Exit Requests

| Method | Path | Description |
|--------|------|-------------|
| POST | `/exits` | Initiate exit |
| GET | `/exits` | List exits (query: status, employee, date range) |
| GET | `/exits/:id` | Get exit detail |
| PUT | `/exits/:id` | Update exit |
| POST | `/exits/:id/cancel` | Cancel exit |
| POST | `/exits/:id/complete` | Complete exit (deactivates user in EMP Cloud) |

### Self-Service (Employee)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/self-service/resign` | Submit resignation |
| GET | `/self-service/my-exit` | View own exit status |
| GET | `/self-service/my-checklist` | View own checklist items |
| POST | `/self-service/exit-interview` | Submit exit interview responses |
| POST | `/self-service/nps-survey` | Submit NPS survey response |

### Checklist Templates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/checklist-templates` | List templates |
| POST | `/checklist-templates` | Create template |
| PUT | `/checklist-templates/:id` | Update template |
| POST | `/checklist-templates/:id/items` | Add item to template |

### Clearance

| Method | Path | Description |
|--------|------|-------------|
| GET | `/clearance-departments` | List configured departments |
| GET | `/exits/:id/clearance` | Get clearance status for exit |
| PUT | `/exits/:id/clearance/:clearanceId` | Approve/reject clearance |
| GET | `/my-clearances` | Pending clearances assigned to me |

### Exit Interviews

| Method | Path | Description |
|--------|------|-------------|
| GET | `/interview-templates` | List interview templates |
| POST | `/interview-templates` | Create interview template |
| GET | `/exits/:id/interview` | Get interview for exit |
| POST | `/exits/:id/interview` | Schedule interview |

### Full & Final Settlement

| Method | Path | Description |
|--------|------|-------------|
| POST | `/exits/:id/fnf/calculate` | Calculate F&F |
| GET | `/exits/:id/fnf` | Get F&F details |
| PUT | `/exits/:id/fnf` | Update F&F (manual adjustments) |
| POST | `/exits/:id/fnf/approve` | Approve F&F |
| POST | `/exits/:id/fnf/mark-paid` | Mark F&F as paid |

### Asset Returns

| Method | Path | Description |
|--------|------|-------------|
| GET | `/exits/:id/assets` | List assets for exit |
| POST | `/exits/:id/assets` | Add asset to return list |
| PUT | `/exits/:id/assets/:assetId` | Update asset status |

### Knowledge Transfer

| Method | Path | Description |
|--------|------|-------------|
| POST | `/exits/:id/kt` | Create KT plan |
| PUT | `/exits/:id/kt` | Update KT (assign successor) |
| POST | `/exits/:id/kt/items` | Add KT item |

### Letters

| Method | Path | Description |
|--------|------|-------------|
| GET | `/letter-templates` | List letter templates |
| POST | `/letter-templates` | Create letter template |
| POST | `/exits/:id/letters/generate` | Generate letter PDF |
| GET | `/exits/:id/letters/:letterId/download` | Download PDF |
| POST | `/exits/:id/letters/:letterId/send` | Email letter to employee |

### Flight Risk / Attrition Prediction

| Method | Path | Description |
|--------|------|-------------|
| GET | `/predictions/dashboard` | Flight risk dashboard summary |
| GET | `/predictions/high-risk` | List high-risk employees |
| GET | `/predictions/employee/:employeeId` | Individual risk score with factors |
| GET | `/predictions/trends` | Attrition trend over time |
| POST | `/predictions/calculate` | Trigger risk score recalculation |

### Notice Period Buyout

| Method | Path | Description |
|--------|------|-------------|
| POST | `/exits/:id/buyout/calculate` | Calculate buyout amount |
| POST | `/exits/:id/buyout/request` | Submit buyout request |
| PUT | `/exits/:id/buyout/approve` | Approve/reject buyout request |
| GET | `/exits/:id/buyout` | Get buyout details and status |

### Exit Stage Email Notifications

| Method | Path | Description |
|--------|------|-------------|
| GET | `/email-templates` | List exit stage email templates |
| PUT | `/email-templates/:stage` | Update email template for a stage |
| POST | `/email-templates/:stage/preview` | Preview rendered email template |
| GET | `/exits/:id/email-log` | View sent emails for an exit |

### Rehire Workflow

| Method | Path | Description |
|--------|------|-------------|
| GET | `/rehire` | List rehire applications |
| POST | `/rehire` | Create rehire application from alumni |
| PUT | `/rehire/:id/screen` | Move to screening stage |
| PUT | `/rehire/:id/approve` | Approve for rehire |
| POST | `/rehire/:id/hire` | Complete rehire (reactivate user in EMP Cloud) |
| GET | `/rehire/eligible` | List alumni eligible for rehire |

### Exit Survey NPS

| Method | Path | Description |
|--------|------|-------------|
| GET | `/nps/scores` | Get NPS calculation (promoters, passives, detractors) |
| GET | `/nps/trends` | NPS trend over time (monthly/quarterly) |
| GET | `/nps/responses` | List all survey responses |
| GET | `/nps/department/:deptId` | Department-level NPS breakdown |

### Other Endpoints

| Area | Description |
|------|-------------|
| BGV | CRUD for background verification records and reference checks |
| Alumni | Directory listing, profile updates, opt-in |
| Settings | Get/update org exit settings |
| Analytics | Attrition rate, reason breakdown, department trends, tenure distribution, rehire pool |
| Health | `/health` basic health check |
| API Docs | Swagger UI at `/api/docs` |

---

## Frontend Pages

### Admin Pages

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard` | Dashboard | Active exits, clearance pending, F&F pending, attrition chart |
| `/exits` | Exit List | Table with filters (status, date, department, type) |
| `/exits/new` | Initiate Exit | Form: select employee, exit type, dates, reason |
| `/exits/:id` | Exit Detail | Tabs: Overview, Checklist, Clearance, Interview, F&F, Assets, KT, Letters, Buyout |
| `/checklists` | Checklist Templates | CRUD for exit checklist templates |
| `/interviews` | Interview Templates | CRUD for interview question templates |
| `/letters` | Letter Templates | CRUD with Handlebars preview |
| `/clearance` | Clearance Config | Manage clearance departments |
| `/fnf` | F&F Management | Full & final settlement management |
| `/analytics` | Exit Analytics | Attrition rate, reason pie chart, department trends, tenure histogram |
| `/alumni` | Alumni Directory | Alumni listing with rehire eligibility indicators |
| `/rehire` | Rehire Management | Pipeline view: alumni -> screening -> approved -> hired |
| `/buyout` | Notice Buyout | Buyout requests and approvals |
| `/settings` | Settings | Module settings, buyout rules, email config |
| `/assets` | Asset Returns | Asset return tracking |

### Self-Service Pages

| Route | Page | Description |
|-------|------|-------------|
| `/my` | Self-Service Dashboard | Employee self-service overview |
| `/my/exit` | My Exit | Submit resignation, view status, checklist, clearance |
| `/my/exit/interview` | Exit Interview | Complete exit interview form |
| `/my/exit/kt` | Knowledge Transfer | Add KT documentation items |
| `/my/exit/buyout` | Notice Buyout | Request notice period buyout, view calculation |
| `/my/exit/nps` | NPS Survey | Submit exit NPS survey |
| `/my/exit/letters` | My Letters | View and download exit letters |
| `/my/alumni` | My Alumni Profile | Opt in/update alumni profile |

---

## Test Suite

BullMQ background workers handle exit stage email notifications, letter PDF generation, attrition risk score calculation, and scheduled reminders. All 17 route modules and 15 service modules are covered by manual and integration testing.

---

## Test Deployment

| Environment | URL |
|-------------|-----|
| Frontend | https://test-exit.empcloud.com |
| API | https://test-exit-api.empcloud.com |

SSO integrated with EMP Cloud.

---

## License

This project is licensed under the [AGPL-3.0 License](LICENSE).
