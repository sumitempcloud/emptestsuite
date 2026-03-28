# EMP Recruit

> Streamline hiring and onboarding for faster, seamless team growth

[![Part of EmpCloud](https://img.shields.io/badge/EmpCloud-Module-blue)]()
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-purple.svg)](LICENSE)
[![Status: Built](https://img.shields.io/badge/Status-Built-green)]()

EMP Recruit is the recruitment and applicant tracking module of the EmpCloud ecosystem. It provides end-to-end hiring workflow management from job posting through candidate tracking, interviews, offers, and onboarding -- plus AI-powered JD generation, resume scoring, candidate comparison, background checks, psychometric assessments, candidate surveys, custom pipeline stages, offer letter PDF generation, and a public candidate portal with magic link authentication.

**GitHub:** https://github.com/EmpCloud/emp-recruit

---

## Project Status

**Built** -- all phases implemented and tested.

| Test Suite | Count | Details |
|------------|-------|---------|
| API endpoint tests | 109 | Full endpoint coverage across all route files |
| E2E workflow tests | 58 | Complete hiring pipeline flows |
| Interview E2E tests | 33 | Scheduling, recordings, transcripts, calendar, invitations |
| SSO unit tests | 6 | Token exchange and validation |
| Playwright browser tests | 21+ | End-to-end UI flows with screenshots |
| **Total** | **206+** | All passing |

---

## Live URLs

| Environment | URL |
|-------------|-----|
| Frontend (test) | https://test-recruit.empcloud.com |
| API (test) | https://test-recruit-api.empcloud.com |
| Client (local) | http://localhost:5179 |
| API (local) | http://localhost:4500 |
| API Documentation | http://localhost:4500/api/docs |

---

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| Job Postings | Built | Create openings with title, description, requirements, department, location, salary range, employment type |
| AI JD Generator | Built | AI-powered job description generation from minimal input (title, role level, key requirements) |
| Career Page | Built | Public-facing careers page, customizable per organization with branding |
| Application Tracking (ATS) | Built | Kanban pipeline: Applied -> Screened -> Interview -> Offer -> Hired/Rejected |
| Custom Pipeline Stages | Built | Drag-and-drop stage reordering, per-org customization, color picker for stages |
| Candidate Management | Built | Candidate profiles, resume upload/parsing, notes, tags, search |
| Candidate Comparison | Built | Side-by-side view of 2-3 candidates with skill/experience/score comparison |
| Interview Scheduling | Built | Schedule interviews, assign interviewers, calendar integration |
| Interview Feedback | Built | Structured scorecards, interviewer ratings, recommendation |
| Video Conferencing | Built | Google Meet and Jitsi Meet integration with real working meeting links |
| Interview Recording Upload | Built | Audio/video recording upload support up to 500MB per file |
| Automatic Transcription | Built | Transcript generation from uploaded interview recordings |
| Add to Calendar | Built | Google Calendar, Outlook, Office 365 links and .ics file download |
| Email Invitations | Built | Send interview invitations with calendar links to candidates and panelists |
| AI Resume Scoring | Built | Skill extraction, auto-scoring 0-100, batch scoring, candidate rankings |
| Offer Management | Built | Generate offer letters, approval workflow, e-signature |
| Offer Letter PDF Generation | Built | Handlebars templates, PDF rendering, email offer letter to candidate |
| Onboarding Checklists | Built | Pre-joining tasks, document collection, IT provisioning, welcome kit |
| Background Checks | Built | Background verification requests, status tracking, provider integration |
| Candidate Surveys | Built | Pre/post interview surveys for candidate experience feedback |
| Psychometric Assessments | Built | Assessment test assignments, scoring, candidate evaluation |
| Referral Program | Built | Employee referral tracking, bonus eligibility, referral analytics |
| Recruitment Analytics | Built | Time-to-hire, source effectiveness, pipeline conversion, offer acceptance rate |
| Job Board Integration | Built | Post to LinkedIn, Indeed, Naukri via API hooks |
| Email Templates | Built | Automated emails for each pipeline stage (Handlebars-based) |
| Candidate Portal | Built | Magic link authentication, application tracking, interview schedule view for candidates |
| SSO Authentication | Built | Single sign-on from EMP Cloud dashboard via JWT token exchange |
| API Documentation | Built | Swagger UI at /api/docs with OpenAPI 3.0 spec |

---

## Screenshots

### Dashboard
![Dashboard](e2e/screenshots/recruit-01-dashboard.png)

### Job Postings
![Jobs](e2e/screenshots/recruit-02-jobs.png)

### Job Detail with ATS Pipeline
![Job Detail](e2e/screenshots/recruit-03-job-detail.png)

### Candidates
![Candidates](e2e/screenshots/recruit-04-candidates.png)

### Interviews
![Interviews](e2e/screenshots/recruit-05-interviews.png)

### Interview Detail (Meet Link + Calendar)
![Interview Detail](e2e/screenshots/recruit-06-interview-detail.png)

### Offers
![Offers](e2e/screenshots/recruit-07-offers.png)

### Recruitment Analytics
![Analytics](e2e/screenshots/recruit-08-analytics.png)

### Settings
![Settings](e2e/screenshots/recruit-09-settings.png)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Runtime | Node.js 20 |
| Backend | Express 5, TypeScript |
| Frontend | React 19, Vite 6, TypeScript |
| Styling | Tailwind CSS, Radix UI |
| Database | MySQL 8 via Knex.js (`emp_recruit` database) |
| Cache / Queue | Redis 7, BullMQ |
| Auth | OAuth2/OIDC via EMP Cloud (RS256 JWT verification), SSO token exchange |
| File Uploads | Multer (local storage, S3-ready) |
| PDF Generation | Puppeteer / Handlebars |
| AI | Natural language processing for JD generation, skill extraction, and resume scoring |
| Testing | Vitest (API + unit tests), Playwright (browser tests) |
| API Docs | Swagger UI + OpenAPI 3.0 |
| Monorepo | pnpm workspaces |

---

## Project Structure

```
emp-recruit/
  package.json
  pnpm-workspace.yaml
  tsconfig.json
  docker-compose.yml
  .env.example
  packages/
    shared/                     # @emp-recruit/shared
      src/
        types/                  # TypeScript interfaces & enums
        validators/             # Zod request validation schemas
        constants/              # Stage definitions, defaults
    server/                     # @emp-recruit/server (port 4500)
      src/
        config/                 # Environment configuration
        db/
          connection.ts         # Knex connection to emp_recruit
          empcloud.ts           # Read-only connection to empcloud DB
          migrations/
            sql/                # 8 migration files
              001_initial_schema.ts
              002_interview_recordings.ts
              003_candidate_scores.ts
              004_offer_letters.ts
              005_custom_pipeline.ts
              006_background_checks.ts
              007_candidate_surveys.ts
              008_psychometric_assessments.ts
        api/
          middleware/            # auth, RBAC, error handling, upload
          routes/               # 22 route files
            auth.routes.ts
            job.routes.ts
            candidate.routes.ts
            application.routes.ts
            interview.routes.ts
            offer.routes.ts
            offer-letter.routes.ts
            onboarding.routes.ts
            referral.routes.ts
            analytics.routes.ts
            scoring.routes.ts
            pipeline.routes.ts
            portal.routes.ts
            public.routes.ts
            career-page.routes.ts
            email-template.routes.ts
            comparison.routes.ts
            job-description.routes.ts
            background-check.routes.ts
            survey.routes.ts
            assessment.routes.ts
            health.routes.ts
          validators/           # Request validators
        services/               # 23 service files
          auth/                 # SSO authentication
          job/                  # Job posting CRUD, status management
          job-description/      # AI-powered JD generation
          candidate/            # Candidate profiles, search, management
          application/          # ATS pipeline, stage transitions
          interview/            # Scheduling, calendar, recording, invitation, transcription
          offer/                # Offer management, approval workflow, letter generation
          onboarding/           # Checklist templates, task management
          referral/             # Referral tracking, bonus eligibility
          analytics/            # Recruitment metrics and reporting
          scoring/              # AI resume scoring, skill extraction
          pipeline/             # Custom pipeline stage management
          portal/               # Candidate portal, magic links
          career-page/          # Public career page configuration
          comparison/           # Candidate side-by-side comparison
          email/                # Email template rendering and sending
          background-check/     # Background verification management
          survey/               # Candidate surveys
          assessment/           # Psychometric assessment management
        jobs/                   # BullMQ workers (email, resume parse, AI scoring, job board sync)
        utils/                  # Logger, errors, response helpers
        swagger/                # OpenAPI spec & Swagger UI setup
        __tests__/              # Test files
          api.test.ts           # 109 API endpoint tests
          e2e.test.ts           # 58 E2E workflow tests
          interview-e2e.test.ts # 33 interview tests
          sso.test.ts           # 6 SSO tests
    client/                     # @emp-recruit/client (port 5179)
      src/
        api/                    # API client & hooks
        components/
          layout/               # DashboardLayout, PublicLayout, CandidatePortalLayout
          ui/                   # Radix-based UI primitives
          recruit/              # KanbanBoard, FeedbackForm, CandidateComparison, etc.
        pages/                  # Route-based page components
        lib/                    # Auth store, utilities
```

---

## Database Tables (25+)

| Table | Purpose |
|-------|---------|
| `job_postings` | Job openings with title, description, requirements, salary, status |
| `candidates` | Candidate profiles with contact info, resume, experience, source |
| `applications` | Links candidates to jobs with pipeline stage tracking |
| `application_stage_history` | Audit trail of all stage transitions |
| `interviews` | Scheduled interviews with type, time, location, meeting link |
| `interview_panelists` | Interviewer assignments per interview |
| `interview_feedback` | Structured scorecard ratings and recommendations |
| `interview_recordings` | Audio/video recording metadata and file paths for interviews |
| `interview_transcripts` | Generated transcripts from interview recordings |
| `offers` | Offer details with salary, designation, approval status |
| `offer_approvers` | Multi-step offer approval chain |
| `offer_letters` | Generated offer letter PDFs with template reference |
| `onboarding_templates` | Reusable onboarding task templates |
| `onboarding_template_tasks` | Individual tasks within a template |
| `onboarding_checklists` | Instantiated checklists for hired candidates |
| `onboarding_tasks` | Individual onboarding task assignments and progress |
| `referrals` | Employee referral tracking with bonus eligibility |
| `email_templates` | Handlebars-based email templates per pipeline stage |
| `career_pages` | Per-org public career page configuration |
| `job_board_postings` | External job board posting status tracking |
| `recruitment_events` | Analytics event log for reporting |
| `candidate_portal_tokens` | Magic link tokens for candidate portal authentication |
| `resume_scores` | AI-generated resume scores with skill extraction data |
| `pipeline_stage_configs` | Per-org custom pipeline stage definitions with ordering and colors |
| `background_checks` | Background verification requests and results |
| `candidate_surveys` | Survey assignments and responses from candidates |
| `psychometric_assessments` | Assessment test results and scoring |

**8 migrations** across the database schema.

---

## API Endpoints

All endpoints under `/api/v1/`. Server runs on port **4500**.

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/sso` | SSO token exchange (EMP Cloud JWT -> Recruit session token) |

### Job Postings
| Method | Path | Description |
|--------|------|-------------|
| GET | `/jobs` | List job postings (paginated, filterable) |
| POST | `/jobs` | Create job posting |
| GET | `/jobs/:id` | Get job posting detail |
| PUT | `/jobs/:id` | Update job posting |
| PATCH | `/jobs/:id/status` | Change status (publish/pause/close) |
| GET | `/jobs/:id/applications` | List applications for a job |
| GET | `/jobs/:id/analytics` | Job-level analytics |

### AI JD Generator
| Method | Path | Description |
|--------|------|-------------|
| POST | `/job-descriptions/generate` | Generate AI-powered job description from minimal input |
| GET | `/job-descriptions/templates` | List available JD templates |

### Candidates
| Method | Path | Description |
|--------|------|-------------|
| GET | `/candidates` | List/search candidates |
| POST | `/candidates` | Create candidate |
| GET | `/candidates/:id` | Get candidate profile |
| PUT | `/candidates/:id` | Update candidate |
| POST | `/candidates/:id/resume` | Upload/replace resume |
| GET | `/candidates/compare` | Side-by-side comparison of 2-3 candidates |

### Applications (ATS)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/applications` | List all applications |
| POST | `/applications` | Create application |
| GET | `/applications/:id` | Get application with full history |
| PATCH | `/applications/:id/stage` | Move to next/prev stage |
| GET | `/applications/:id/timeline` | Stage history timeline |

### Interviews
| Method | Path | Description |
|--------|------|-------------|
| GET | `/interviews` | List interviews |
| POST | `/interviews` | Schedule interview |
| GET | `/interviews/:id` | Get interview detail |
| PUT | `/interviews/:id` | Reschedule/update |
| POST | `/interviews/:id/feedback` | Submit feedback scorecard |
| POST | `/interviews/:id/generate-meet` | Generate Google Meet or Jitsi Meet link |
| POST | `/interviews/:id/send-invitation` | Send email invitation with calendar links |
| POST | `/interviews/:id/recordings` | Upload interview recording (audio/video, up to 500MB) |
| GET | `/interviews/:id/recordings` | List recordings for an interview |
| DELETE | `/interviews/:id/recordings` | Delete a recording |
| POST | `/interviews/:id/recordings/:recId/transcribe` | Generate transcript from a recording |
| GET | `/interviews/:id/transcript` | Get interview transcript |
| PUT | `/interviews/:id/transcript` | Update/edit interview transcript |
| GET | `/interviews/:id/calendar-links` | Get calendar links (Google, Outlook, Office 365) |
| GET | `/interviews/:id/calendar.ics` | Download .ics calendar file |

### Offers
| Method | Path | Description |
|--------|------|-------------|
| POST | `/offers` | Create offer |
| GET | `/offers/:id` | Get offer detail |
| POST | `/offers/:id/submit-approval` | Submit for approval |
| POST | `/offers/:id/approve` | Approve offer |
| POST | `/offers/:id/send` | Send to candidate |
| POST | `/offers/:id/generate-pdf` | Generate offer letter PDF from template |
| POST | `/offers/:id/email-letter` | Email offer letter PDF to candidate |

### AI Resume Scoring
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ai/score-resume` | Score a single resume against job requirements (0-100) |
| POST | `/ai/batch-score` | Batch score multiple resumes for a job posting |
| GET | `/ai/rankings/:jobId` | Get ranked candidate list by AI score |
| GET | `/ai/skills/:candidateId` | Get extracted skills for a candidate |

### Background Checks
| Method | Path | Description |
|--------|------|-------------|
| POST | `/background-checks` | Initiate background check for a candidate |
| GET | `/background-checks/:id` | Get background check status and results |
| GET | `/background-checks/candidate/:candidateId` | List all checks for a candidate |
| PUT | `/background-checks/:id` | Update check status/results |

### Custom Pipeline Stages
| Method | Path | Description |
|--------|------|-------------|
| GET | `/pipeline-stages` | Get org pipeline stage configuration |
| PUT | `/pipeline-stages` | Update stage order, names, and colors |
| POST | `/pipeline-stages` | Add custom stage |
| DELETE | `/pipeline-stages/:id` | Remove custom stage |

### Candidate Portal (Magic Link Auth)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/portal/send-magic-link` | Send magic link email to candidate |
| POST | `/portal/verify` | Verify magic link token |
| GET | `/portal/my-applications` | Candidate views their applications |
| GET | `/portal/my-interviews` | Candidate views scheduled interviews |
| GET | `/portal/my-offers` | Candidate views offers |

### Onboarding
| Method | Path | Description |
|--------|------|-------------|
| GET | `/onboarding/templates` | List templates |
| POST | `/onboarding/templates` | Create template |
| POST | `/onboarding/checklists` | Generate checklist for hire |
| PATCH | `/onboarding/tasks/:id` | Update task status |

### Public Career Page (No Auth)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/public/careers/:slug` | Public career page |
| GET | `/public/careers/:slug/jobs` | List open jobs |
| POST | `/public/careers/:slug/apply` | Submit application with resume |

### Candidate Surveys
| Method | Path | Description |
|--------|------|-------------|
| POST | `/surveys` | Create candidate survey |
| GET | `/surveys/:id` | Get survey with responses |
| POST | `/surveys/:id/respond` | Submit survey response |

### Psychometric Assessments
| Method | Path | Description |
|--------|------|-------------|
| POST | `/assessments` | Assign assessment to candidate |
| GET | `/assessments/:id` | Get assessment results |
| POST | `/assessments/:id/submit` | Submit assessment answers |

### Other Endpoints
- **Referrals**: CRUD for employee referral submissions
- **Email Templates**: CRUD with preview rendering
- **Career Page Admin**: Config and publish controls
- **Analytics**: Overview, pipeline funnel, time-to-hire, source effectiveness, offer acceptance rate
- **Job Board Integration**: Post/remove jobs on external boards
- **API Docs**: Swagger UI at `/api/docs`
- **Health**: GET `/health` for service health check

---

## SSO Authentication

EMP Recruit supports single sign-on from the EMP Cloud dashboard. The flow works as follows:

1. User clicks "Recruit" in the EMP Cloud dashboard
2. EMP Cloud generates a short-lived JWT and redirects to EMP Recruit with a `?sso_token=<jwt>` URL parameter
3. The Recruit client extracts the token and sends it to `POST /api/v1/auth/sso`
4. The server validates the JWT against EMP Cloud's public key, resolves the user and organization, and issues a module-specific Recruit session token
5. The client stores the Recruit token and the user is authenticated without any login form

This allows seamless navigation between EMP Cloud and Recruit without requiring users to log in again.

---

## Frontend Pages (25+)

### Admin Pages (Authenticated)
| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Overview stats, open positions, pipeline summary |
| `/jobs` | Job List | Job postings with status/department filters |
| `/jobs/new` | Job Form | Create/edit job posting |
| `/jobs/:id` | Job Detail | Applications kanban board with custom pipeline stages |
| `/candidates` | Candidate List | Searchable candidate database |
| `/candidates/:id` | Candidate Detail | Full profile, application history, AI score |
| `/candidates/compare` | Candidate Comparison | Side-by-side view of 2-3 candidates |
| `/interviews` | Interview List | Calendar view of interviews |
| `/offers` | Offer List | Offers with status filter |
| `/onboarding` | Onboarding List | Active onboarding checklists |
| `/referrals` | Referral List | Referral tracking |
| `/analytics` | Analytics | Charts: time-to-hire, funnel, sources |
| `/ai-scoring` | AI Resume Scoring | Batch scoring dashboard, candidate rankings |
| `/pipeline-config` | Pipeline Configuration | Drag-and-drop stage editor with color picker |
| `/settings` | Settings | Career page, email templates, integrations |

### Public Pages (No Auth)
| Route | Page | Description |
|-------|------|-------------|
| `/careers/:slug` | Career Page | Public career page with org branding |
| `/careers/:slug/jobs/:jobId` | Job View | Public job detail |
| `/careers/:slug/apply/:jobId` | Application Form | Resume upload and apply |

### Candidate Portal Pages (Magic Link Auth)
| Route | Page | Description |
|-------|------|-------------|
| `/portal/login` | Portal Login | Magic link request form |
| `/portal/verify` | Magic Link Verify | Token verification landing |
| `/portal/dashboard` | Portal Dashboard | Candidate's application overview |
| `/portal/applications` | My Applications | Application status tracking with stage timeline |
| `/portal/interviews` | My Interviews | Upcoming interview schedule and details |
| `/portal/offers` | My Offers | View and respond to offers |

---

## Getting Started

### Prerequisites
- Node.js 20+
- pnpm 9+
- MySQL 8+
- Redis 7+
- EMP Cloud running (for authentication)

### Install
```bash
git clone https://github.com/EmpCloud/emp-recruit.git
cd emp-recruit
pnpm install
```

### Environment Setup
```bash
cp .env.example .env
# Edit .env with your database credentials and EMP Cloud URL
```

Key environment variables:
```env
# Server
PORT=4500
NODE_ENV=development

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=secret
DB_NAME=emp_recruit

# EMP Cloud (required for auth)
EMPCLOUD_DB_NAME=empcloud
EMPCLOUD_API_URL=http://localhost:3000
EMPCLOUD_PUBLIC_KEY_PATH=./keys/public.pem

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Email (for invitations, magic links, offer letters)
SMTP_HOST=localhost
SMTP_PORT=1025
```

### Docker
```bash
docker-compose up -d
```

### Development
```bash
# Run all packages in development mode
pnpm dev

# Run individually
pnpm --filter @emp-recruit/server dev    # Server on :4500
pnpm --filter @emp-recruit/client dev    # Client on :5179

# Run migrations
pnpm --filter @emp-recruit/server migrate
```

Once running, visit:
- **Client**: http://localhost:5179
- **API**: http://localhost:4500
- **API Documentation**: http://localhost:4500/api/docs

### Running Tests
```bash
# Run all API and unit tests
pnpm --filter @emp-recruit/server test

# Run specific test suite
pnpm --filter @emp-recruit/server test -- --grep "interview"

# Run Playwright browser tests
npx playwright test
```

---

## Cross-Module Integration

### Webhook to EMP Cloud
EMP Recruit sends event webhooks to EMP Cloud for unified activity tracking:
- `candidate.hired` -- When a candidate is moved to Hired stage
- `offer.accepted` -- When a candidate accepts an offer
- `onboarding.completed` -- When all onboarding tasks are done

### EMP Cloud AI Agent Tools
EMP Cloud's AI agent includes 3 cross-module tools that call EMP Recruit's API:
- `get_open_jobs` -- Fetch open job postings
- `get_hiring_pipeline` -- Get pipeline summary with stage counts
- `get_recruitment_stats` -- Get time-to-hire and source analytics

---

## License

This project is licensed under the [AGPL-3.0 License](LICENSE).
