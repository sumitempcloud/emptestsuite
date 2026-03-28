# EMP Billing

> Open-source billing and invoicing platform -- quotes, invoices, payments, subscriptions, multi-country tax, and three payment gateways.

[![Part of EmpCloud](https://img.shields.io/badge/EmpCloud-Module-blue)]()
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-purple.svg)](LICENSE)
[![Tests: 778+ unit / 130 E2E](https://img.shields.io/badge/tests-778%2B%20unit%20%7C%20130%20E2E-brightgreen.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

EMP Billing is the internal billing engine of the [EmpCloud](https://empcloud.com) ecosystem. It handles the complete billing lifecycle: **Quotes > Invoices > Payments > Receipts > Reports**. Includes client management, product catalog, three payment gateways (Stripe, Razorpay, PayPal), recurring invoices, subscriptions with usage-based billing, coupons, credit notes, dunning, client portal, webhooks, API keys, custom domain mapping, multi-country tax engines (India GST, UAE VAT, EU/UK VAT, US Sales Tax), SaaS metrics (MRR/ARR/churn/LTV), and a full report builder.

**Note:** EMP Billing is an internal engine -- it is NOT a sellable module in the marketplace. It powers subscription invoicing for the EmpCloud platform.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Frontend Pages](#frontend-pages)
- [Testing](#testing)
- [Tax Engine Coverage](#tax-engine-coverage)
- [Payment Gateways](#payment-gateways)
- [Database Schema](#database-schema)
- [Test Deployment](#test-deployment)
- [License](#license)

---

## Features

### Core Billing

| Feature | Description |
|---------|-------------|
| **Invoicing** | Create, edit, duplicate, void, write-off invoices with multi-tax line items, auto-numbering, partial payments, credit notes, bulk actions, PDF generation. |
| **Quotes / Estimates** | Full quote lifecycle with versioning, client approval via portal, one-click convert to invoice. |
| **Payments** | Record full/partial payments, multiple methods (cash, bank, UPI, card, gateway), refunds, overpayment credits, auto-charge recurring. |
| **Credit Notes** | Issue credits, apply to invoices, process refunds. |
| **Recurring Invoices** | Auto-generate on schedule (daily/weekly/monthly/yearly), auto-send, auto-charge, pause/resume. |

### Clients & Products

| Feature | Description |
|---------|-------------|
| **Client Management** | Contact database, multiple addresses, portal access, statements, outstanding tracking, CSV import/export, tags/groups. |
| **Product Catalog** | Items/services with SKU, units, tax association, price lists, optional inventory tracking. |

### Tax Engines

| Region | Coverage |
|--------|----------|
| **India (GST)** | CGST + SGST / IGST, 5 rate slabs (0/5/12/18/28%), HSN/SAC codes, reverse charge, TDS, GSTR-1/3B data export, e-Invoice IRN and e-Way Bill hooks. |
| **UAE** | 5% VAT (standard/zero-rated/exempt), excise tax (50-100%), corporate tax (0/9/15%), TRN validation, reverse charge for imported services. |
| **EU (27 countries) + UK** | Standard/reduced/super-reduced/zero/parking rates per country, reverse charge mechanism for cross-border B2B. UK: 20% standard, 5% reduced, 0% zero-rated. |
| **US (50 states + DC)** | State base rates, county/city tax stacking, nexus tracking, no-tax states (OR, MT, NH, DE, AK). |

### Payments & Subscriptions

| Feature | Description |
|---------|-------------|
| **Stripe** | Cards, ACH -- test mode configured. |
| **Razorpay** | India: UPI, netbanking, cards, wallets -- test mode configured. |
| **PayPal** | REST API v2 -- sandbox mode configured, webhook route active. |
| **Subscriptions** | Plan management, trial periods, usage-based billing, quantity seats. |
| **Usage Billing** | Record usage events, aggregate by billing period, auto-invoice on cycle. |
| **Coupons** | Percentage/fixed discounts, max redemptions, per-client limits, date validity, minimum amount rules. |
| **Dunning** | Automated failed payment retry with configurable retry schedules. |

### Platform

| Feature | Description |
|---------|-------------|
| **Client Portal** | Branded login, view invoices/quotes/payments, pay online, approve quotes, raise disputes, download statements. |
| **Multi-Tenancy** | Every query scoped by `org_id`. Role-based access: Owner, Admin, Accountant, Sales, Viewer. |
| **Notifications** | Email (Nodemailer + Handlebars), SMS (Twilio), WhatsApp (Twilio + Meta Cloud API). |
| **Templates** | Handlebars-based PDF/email templates (invoice, quote, receipt, credit note, statement, payment reminder, welcome, dispute, subscription). 9 templates total. |
| **Reports** | Revenue, receivables aging, tax summaries, expenses, P&L, client reports, scheduled email reports. Custom report builder UI with filters, grouping, column selection. |
| **SaaS Metrics** | MRR, ARR, churn, LTV, cohort analysis, revenue breakdown. |
| **Webhooks** | Subscribe to 20+ event types, delivery logs, retry mechanism. |
| **API Keys** | Create/revoke API keys for programmatic access. Admin-only management. |
| **Custom Domain Mapping** | SaaS customers point subdomains via CNAME. DNS verification with TXT records. In-memory caching. Settings UI. |
| **Search** | Full-text search across invoices, clients, quotes, payments, expenses. |
| **Import/Export** | CSV import/export for clients and products. |
| **OCR** | Receipt scanning via Tesseract.js (local) or cloud providers (Google Vision, AWS Textract, Azure Form Recognizer). |
| **Disputes** | Client-raised disputes via portal with resolution workflow. |
| **Expenses & Vendors** | Expense tracking with receipt upload, OCR scanning, bill-to-client. Vendor management. |
| **Audit Log** | Full activity trail for all operations. |
| **API Documentation** | Full OpenAPI 3.0 spec with Swagger UI at `/api/docs`. |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, TypeScript |
| Styling | Tailwind CSS, Radix UI |
| State | Zustand (client), TanStack Query (server) |
| Backend | Express 5, TypeScript |
| Validation | Zod (shared between client & server) |
| Database | MySQL (default) / PostgreSQL / MongoDB -- switchable via `DB_PROVIDER` |
| Queue | BullMQ + Redis |
| PDF | Puppeteer + Handlebars |
| Email | Nodemailer + Handlebars |
| SMS | Twilio REST API |
| WhatsApp | Twilio / Meta Cloud API |
| Payments | Stripe, Razorpay, PayPal (plugin-based) |
| Auth | JWT (access + refresh tokens) |
| Monorepo | pnpm workspaces (3 packages) |

---

## Quick Start

### Prerequisites

- Node.js 20+
- pnpm 9+
- Docker & Docker Compose (for infrastructure)

### Install & Run

```bash
# 1. Clone
git clone https://github.com/EmpCloud/emp-billing.git
cd emp-billing

# 2. Install dependencies
pnpm install

# 3. Set up environment
cp .env.example .env
# Edit .env with your DB credentials, JWT secrets, gateway keys

# 4. Start infrastructure
docker compose up -d  # MySQL + Redis + Mailpit

# 5. Run migrations & seed
pnpm run db:migrate
pnpm run db:seed

# 6. Start development
pnpm run dev
# Server: http://localhost:4001
# Client: http://localhost:5174
# API Docs: http://localhost:4001/api/docs
# Mailpit: http://localhost:8025
```

### Docker Deployment

```bash
# Start everything (builds automatically)
docker compose up -d

# Or rebuild after code changes
docker compose up -d --build app

# View logs
docker logs -f emp-billing-app

# Stop
docker compose down
```

In production mode (`NODE_ENV=production`), the server serves the client SPA on port 4001 -- no separate frontend server needed.

---

## Project Structure

```
emp-billing/
  packages/
    shared/              # @emp-billing/shared -- types, validators, constants
      src/
        types/           # TypeScript interfaces & enums
        constants/       # Tax engines (GST, UAE, VAT, Sales Tax), currencies
        validators/      # Zod schemas (shared client + server)
        utils/           # Formatters, calculators
    server/              # @emp-billing/server -- Express API
      src/
        api/
          routes/        # 29 route modules
          controllers/   # Thin controllers
          middleware/     # Auth, RBAC, rate limiting, error handling
          validators/    # Request validation
          docs/          # OpenAPI spec + Swagger UI
        services/        # 28 business logic service domains
        db/
          adapters/      # MySQL/PG (Knex) + MongoDB adapters
          migrations/    # 17 migration files
        config/          # Environment config
        utils/           # Logger, PDF, number generator, CSV
        jobs/            # BullMQ workers (8 queues)
        events/          # Typed event emitter
        templates/       # 9 Handlebars templates (invoice, quote, receipt, etc.)
    client/              # @emp-billing/client -- React SPA
      src/
        api/             # Axios client + typed hooks
        components/      # Reusable UI components
        pages/           # 24 page modules
        store/           # Zustand stores
  scripts/
    e2e/                 # 130 Playwright E2E tests (7 test files)
  docker/                # Dockerfile + entrypoint
  docker-compose.yml     # MySQL + PostgreSQL + Redis + Mailpit + App
  .env.example           # All environment variables
```

---

## API Endpoints

All API routes are under `/api/v1/`. Server runs on port **4001**.

| Module | Base Path | Description |
|--------|-----------|-------------|
| Auth | `/auth` | Login, register, refresh, logout, forgot/reset password |
| Organizations | `/organizations` | CRUD, settings, branding, tax config |
| Clients | `/clients` | CRUD, contacts, portal access, statements, import/export |
| Products | `/products` | CRUD, price lists, import/export |
| Invoices | `/invoices` | CRUD, send, duplicate, void, write-off, bulk actions, PDF |
| Quotes | `/quotes` | CRUD, send, convert to invoice, client approval |
| Payments | `/payments` | Record, refund, receipts, gateway callbacks |
| Credit Notes | `/credit-notes` | CRUD, apply to invoice, refund |
| Expenses | `/expenses` | CRUD, receipt upload, bill to client, OCR scanning |
| Vendors | `/vendors` | Vendor CRUD, expense association |
| Recurring | `/recurring` | Profile CRUD, pause/resume, execution history |
| Subscriptions | `/subscriptions` | Plans, subscriptions, usage records |
| Coupons | `/coupons` | CRUD, per-client limits, validation |
| Usage | `/usage` | Usage event recording, aggregation |
| Dunning | `/dunning` | Retry schedules, attempt history |
| Disputes | `/disputes` | Dispute CRUD, resolution workflow |
| Reports | `/reports` | Revenue, receivables, tax, expenses, aging, P&L |
| Scheduled Reports | `/scheduled-reports` | Schedule recurring report emails |
| Metrics | `/metrics` | MRR, ARR, churn, LTV, cohort analysis |
| Webhooks | `/webhooks` | Subscribe to events, delivery logs |
| API Keys | `/api-keys` | Create/revoke API keys (admin only) |
| Custom Domains | `/domains` | Domain mapping, DNS verification |
| Portal | `/portal` | Client-facing: invoices, quotes, payments, disputes |
| Notifications | `/notifications` | Notification management |
| Settings | `/settings` | Tax rates, payment gateways, templates, numbering |
| Search | `/search` | Full-text search across all entities |
| Currency | `/currencies` | Currency list and exchange rates |
| Gateways | `/gateways` | Payment gateway configuration |
| Upload | `/upload` | File upload (receipts, attachments) |

Full interactive API documentation available at `/api/docs` when running the server.

---

## Frontend Pages

24 page modules across admin and portal views:

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/dashboard` | Revenue stats, outstanding, recent invoices, charts |
| Invoices | `/invoices` | Invoice list, create/edit, send, PDF, bulk actions |
| Invoice Detail | `/invoices/:id` | Full invoice with line items, payments, timeline |
| Quotes | `/quotes` | Quote list, create/edit, send, convert to invoice |
| Clients | `/clients` | Client list, create/edit, import/export |
| Client Detail | `/clients/:id` | Contact info, invoices, payments, statements |
| Products | `/products` | Product catalog, create/edit, import/export |
| Payments | `/payments` | Payment list, record payment, refund |
| Credit Notes | `/credit-notes` | Credit note list, create, apply to invoice |
| Expenses | `/expenses` | Expense list, create, receipt upload, OCR |
| Vendors | `/vendors` | Vendor list, create/edit |
| Recurring | `/recurring` | Recurring invoice profiles, execution history |
| Subscriptions | `/subscriptions` | Subscription management, plan assignment |
| Coupons | `/coupons` | Coupon management, validation rules |
| Dunning | `/dunning` | Dunning schedules, retry history |
| Disputes | `/disputes` | Dispute management, resolution |
| Usage | `/usage` | Usage record management |
| Reports | `/reports` | Revenue, aging, tax, expense, P&L reports. Custom report builder. |
| Metrics | `/metrics` | SaaS metrics: MRR, ARR, churn, LTV, cohort |
| Webhooks | `/webhooks` | Webhook subscriptions, delivery logs |
| Settings | `/settings` | Org settings, tax rates, gateways, templates, domains |
| Team | `/team` | Team member management (RBAC roles) |
| Audit Log | `/audit` | Full activity trail |
| Client Portal | `/portal/*` | Client-facing: login, invoices, quotes, payments, disputes |

---

## Testing

### Unit Tests (778+ passing)

```bash
# Run all unit tests
pnpm run test

# Individual packages
pnpm --filter @emp-billing/server test     # 457+ tests (39 files)
pnpm --filter @emp-billing/client test     # 11 tests (3 files)
pnpm --filter @emp-billing/shared test     # 150 tests (4 files) -- validators, tax engines
```

Coverage includes services, middleware, utils, events, Zustand stores, Zod validators, and all four tax engines (GST, UAE, VAT, Sales Tax).

### E2E Tests (130 Playwright tests)

```bash
# Run full E2E suite (requires server + client running on localhost:4001)
bash scripts/e2e/run-all.sh
```

| Test File | Modules Covered | Tests |
|-----------|----------------|-------|
| `auth-dashboard.test.ts` | Login, Register, Forgot Password, Dashboard | 12 |
| `invoices-quotes.test.ts` | Invoice CRUD, PDF, Quotes, Convert to Invoice | 19 |
| `clients-products.test.ts` | Client CRUD, Statements, Product CRUD, Inventory | 16 |
| `payments-expenses-vendors.test.ts` | Payments, Expenses, Vendors | 20 |
| `creditnotes-recurring-subscriptions.test.ts` | Credit Notes, Recurring Profiles, Subscriptions | 21 |
| `coupons-dunning-disputes-usage-metrics.test.ts` | Coupons, Dunning, Disputes, Usage, Metrics | 21 |
| `reports-webhooks-settings-team-audit.test.ts` | Reports, Webhooks, Settings, Tax Rates, Team, Audit Log | 28 |

Tests fill real forms with realistic data, interact with dropdowns and modals, verify toast notifications, check navigation, and validate data persistence across page reloads.

---

## Tax Engine Coverage

| Region | Features |
|--------|----------|
| **India (GST)** | CGST+SGST/IGST, 5 rate slabs, HSN/SAC, TDS, reverse charge, e-Invoice IRN, e-Way Bill |
| **UAE** | 5% VAT (standard/zero/exempt), excise tax (50-100%), corporate tax (0/9/15%), TRN validation |
| **EU (27 countries)** | Standard/reduced/super-reduced/zero/parking rates, reverse charge B2B |
| **UK** | 20% standard, 5% reduced, 0% zero-rated, reverse charge |
| **US (50 states + DC)** | State base rates, county/city stacking, no-tax states |

---

## Payment Gateways

Each gateway implements the `IPaymentGateway` interface:

```typescript
interface IPaymentGateway {
  createOrder(input: CreateOrderInput): Promise<CreateOrderResult>;
  verifyPayment(input: VerifyPaymentInput): Promise<VerifyPaymentResult>;
  chargeCustomer(input: ChargeCustomerInput): Promise<ChargeCustomerResult>;
  refund(input: RefundInput): Promise<RefundResult>;
  handleWebhook(payload: WebhookPayload): Promise<WebhookResult>;
}
```

Configure gateway credentials in `.env` and they auto-initialize on server start. Extensible -- implement the interface to add any gateway.

---

## Database Schema

30+ tables across 17 migrations:

`organizations`, `users`, `clients`, `client_contacts`, `products`, `price_lists`, `tax_rates`, `invoices`, `invoice_items`, `quotes`, `quote_items`, `credit_notes`, `credit_note_items`, `payments`, `payment_allocations`, `expenses`, `expense_categories`, `vendors`, `recurring_profiles`, `recurring_executions`, `templates`, `client_portal_access`, `webhooks`, `webhook_deliveries`, `audit_logs`, `settings`, `notifications`, `disputes`, `scheduled_reports`, `subscriptions`, `plans`, `usage_records`, `coupons`, `dunning_attempts`, `saved_payment_methods`, `custom_domains`, `api_keys`

Supports three database backends:

| Provider | Config Value | Adapter |
|----------|-------------|---------|
| MySQL 8.0 | `DB_PROVIDER=mysql` | KnexAdapter |
| PostgreSQL 16 | `DB_PROVIDER=pg` | KnexAdapter |
| MongoDB 7+ | `DB_PROVIDER=mongodb` | MongoAdapter |

---

## Security

A comprehensive security audit identified and fixed 30 vulnerabilities:

- Redis-based rate limiting on all authentication and sensitive endpoints
- RBAC enforcement on all sensitive routes (admin, settings, team management, audit logs)
- SSRF protection on webhook URLs -- blocks private/internal IPs, localhost, and link-local addresses
- Puppeteer sandboxing -- PDF generation runs in a sandboxed Chromium instance
- Input validation on all API endpoints via Zod schemas
- XSS prevention -- template outputs sanitized, Content-Security-Policy headers
- SQL injection protection -- parameterized queries via Knex, no raw string interpolation

---

## Test Deployment

| Environment | URL |
|-------------|-----|
| Frontend | https://testbilling.empcloud.com |
| API | https://testbilling-api.empcloud.com |

---

## Architecture Decisions

1. **Money as integers** -- All amounts in smallest currency unit (paise/cents/fils). No floating-point rounding errors.
2. **DB abstraction** -- `IDBAdapter` interface with Knex (MySQL/PG) and MongoDB adapters. Switch via env var.
3. **Event-driven** -- Major actions emit typed events. Listeners handle side effects (email, PDF, webhooks) keeping services decoupled.
4. **Plugin-based gateways** -- Add payment gateways without touching core code.
5. **Multi-tenant** -- Every query scoped by `org_id`. Middleware extracts org context from JWT.
6. **Thin controllers** -- Validate (Zod) > Service > ApiResponse. Business logic lives in services.

---

## License

This project is licensed under the [AGPL-3.0 License](LICENSE).
