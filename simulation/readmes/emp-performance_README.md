# EMP Performance

> Monitor performance and guide career development for employee growth

[![Part of EmpCloud](https://img.shields.io/badge/EmpCloud-Module-blue)]()
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Status: Built](https://img.shields.io/badge/Status-Built-green)]()

EMP Performance is the performance management module of the EmpCloud ecosystem. It provides review cycles, goals and OKRs, self/manager/peer assessments, competency frameworks, career paths, 1-on-1 meetings, continuous feedback, PIPs, performance analytics with bell curve calibration, 9-box grid, succession planning, goal alignment trees, performance letter generation, skills gap analysis, manager effectiveness scoring, AI-powered review summaries, and automated email reminders.

**GitHub:** https://github.com/EmpCloud/emp-performance

---

## Project Status

**Built** -- all phases implemented and tested.

| Test Suite | Count | Details |
|------------|-------|---------|
| API endpoint tests | 128 | Full endpoint coverage across all route files |
| E2E workflow tests | 34 | Complete review cycle and goal workflows |
| E2E advanced workflows | 62 | Multi-step flows: 360 reviews, PIPs, succession, letters |
| Unit tests (feedback) | 11 | Feedback service logic |
| Unit tests (goals) | 14 | Goal service logic, key results, check-ins |
| Unit tests (review cycles) | 14 | Review cycle service logic, launch, close |
| **Total** | **263** | All passing |

### Metrics

| Metric | Count |
|--------|-------|
| Database tables | 29+ |
| Database migrations | 6 |
| API route files | 17 |
| Service modules | 21 |
| Frontend pages | 44 |

---

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| Review Cycles | Built | Create quarterly/annual/360-degree review cycles, add participants, launch, close |
| Goals & OKRs | Built | Set goals with key results, weight, due dates, progress tracking, check-ins |
| Self-Assessment | Built | Employee self-review forms with competency ratings |
| Manager Assessment | Built | Manager reviews with ratings per competency |
| Peer Reviews | Built | 360-degree peer feedback with nomination and approval workflow |
| Ratings & Bell Curve | Built | Org-wide ratings distribution, bell curve analysis, calibration |
| PIPs | Built | Performance Improvement Plans with objectives, timeline, progress updates, close with outcome |
| Competency Frameworks | Built | Define competencies per role/level with weights |
| Career Paths | Built | Define career ladders and progression paths with levels |
| 1-on-1 Meetings | Built | Schedule, agenda, notes, action items, recurrence, mark complete |
| Continuous Feedback | Built | Quick kudos/constructive feedback between review cycles, public kudos wall |
| Performance Analytics | Built | Trends, team comparisons, top/bottom performers, goal completion rates |
| 9-Box Grid | Built | Performance vs Potential matrix with color-coded cells, drag-to-reposition, history tracking |
| Succession Planning | Built | Succession plans per critical role, candidate readiness tracking, development actions |
| Goal Alignment Tree | Built | Company -> department -> team -> individual goal cascade with progress rollup |
| Performance Letter Generation | Built | Appraisal, increment, promotion, confirmation, warning letter templates (Handlebars + PDF) |
| Skills Gap Analysis | Built | Radar chart visualization, gap table, learning recommendations per employee |
| Manager Effectiveness | Built | Manager scoring based on team metrics, review completion, feedback quality, 1:1 frequency |
| AI Review Summaries | Built | AI-powered summary generation for review cycles, individual reviews, and team performance |
| Automated Email Reminders | Built | BullMQ daily jobs for review deadlines, PIP check-ins, meeting reminders, goal due dates |
| Notification Settings | Built | Configurable reminder schedules per org, opt-in/out per notification type |
| SSO Authentication | Built | Single sign-on from EMP Cloud dashboard via JWT token exchange |
| API Documentation | Built | Swagger UI at /api/docs with OpenAPI 3.0 spec |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Runtime | Node.js 20 |
| Backend | Express 5, TypeScript |
| Frontend | React 19, Vite 6, TypeScript |
| Styling | Tailwind CSS, Radix UI |
| Database | MySQL 8 via Knex.js (`emp_performance` database) |
| Cache / Queue | Redis 7, BullMQ |
| Auth | OAuth2/OIDC via EMP Cloud (RS256 JWT verification), SSO token exchange |
| Charts | Recharts (bell curve, radar, trends, 9-box grid) |
| PDF Generation | Puppeteer / Handlebars |
| AI | OpenAI/Claude for review summary generation |
| Testing | Vitest (API + unit tests) |
| API Docs | Swagger UI + OpenAPI 3.0 |
| Monorepo | pnpm workspaces |

---

## Project Structure

```
emp-performance/
  package.json
  pnpm-workspace.yaml
  tsconfig.json
  docker-compose.yml
  .env.example
  packages/
    shared/                     # @emp-performance/shared
      src/
        types/                  # TypeScript interfaces & enums
        validators/             # Zod request validation schemas
        constants/              # Rating scales, statuses, defaults
    server/                     # @emp-performance/server (port 4300)
      src/
        config/                 # Environment configuration
        db/
          connection.ts         # Knex connection to emp_performance
          empcloud.ts           # Read-only connection to empcloud DB
          migrations/
            sql/                # 6 migration files
              001_initial_schema.ts
              002_nine_box.ts
              003_notification_settings.ts
              004_performance_letters.ts
              005_participant_final_rating.ts
              006_manager_effectiveness.ts
        api/
          middleware/            # auth, RBAC, error handling
          routes/               # 17 route files
            auth.routes.ts
            review-cycle.routes.ts
            review.routes.ts
            goal.routes.ts
            competency.routes.ts
            pip.routes.ts
            career-path.routes.ts
            one-on-one.routes.ts
            feedback.routes.ts
            peer-review.routes.ts
            analytics.routes.ts
            letter.routes.ts
            succession.routes.ts
            manager-effectiveness.routes.ts
            ai-summary.routes.ts
            notification.routes.ts
            health.routes.ts
          docs.ts               # OpenAPI spec & Swagger UI setup
        services/               # 21 service files
          auth/                 # SSO authentication
          review/               # Review cycle management, individual reviews
          goal/                 # Goals, key results, check-ins, alignment
          competency/           # Competency frameworks and ratings
          pip/                  # Performance improvement plans
          career/               # Career paths and employee tracks
          one-on-one/           # 1-on-1 meeting management
          feedback/             # Continuous feedback and kudos
          peer-review/          # Peer review nominations and approval
          analytics/            # Performance analytics, 9-box grid, succession planning
          letter/               # Performance letter templates and PDF generation
          manager-effectiveness/ # Manager scoring and team metrics
          ai-summary/           # AI-powered review and performance summaries
          notification/         # Notification settings management
          email/                # Email rendering and sending
        jobs/                   # BullMQ workers
          queue.ts              # Queue definitions
          reminder.jobs.ts      # Review deadlines, PIP alerts, meeting reminders, goal due dates
        utils/                  # Logger, errors, response helpers
        swagger/                # OpenAPI spec
        __tests__/              # Test files
          api.test.ts           # 128 API endpoint tests
          e2e.test.ts           # 34 E2E workflow tests
          e2e-workflows.test.ts # 62 advanced workflow tests
      src/services/
        feedback/feedback.service.test.ts  # 11 unit tests
        goal/goal.service.test.ts          # 14 unit tests
        review/review-cycle.service.test.ts # 14 unit tests
    client/                     # @emp-performance/client (port 5177)
      src/
        api/                    # API client & hooks
        components/
          layout/               # DashboardLayout, SelfServiceLayout
          ui/                   # Radix-based UI primitives
          performance/          # NineBoxGrid, GoalAlignmentTree, SkillsRadar, BellCurve, etc.
        pages/                  # 44 route-based page components
        lib/                    # Auth store, utilities
```

---

## Database Tables (29+)

| Table | Purpose |
|-------|---------|
| `competency_frameworks` | Competency sets per org, role, and level |
| `competencies` | Individual competencies within a framework (with weights) |
| `review_cycles` | Quarterly/annual/360 review cycle configuration |
| `review_cycle_participants` | Employees participating in a cycle with status and final rating |
| `reviews` | Individual review submissions (self, manager, peer) |
| `review_competency_ratings` | Per-competency ratings within a review |
| `goals` | Employee/team goals with cascading hierarchy |
| `key_results` | OKR key results under a goal |
| `goal_check_ins` | Progress updates on goals/KRs |
| `goal_alignments` | Parent-child goal alignment links (company -> dept -> team -> individual) |
| `performance_improvement_plans` | PIP records with status lifecycle |
| `pip_objectives` | Specific objectives within a PIP |
| `pip_updates` | Progress check-ins for a PIP |
| `continuous_feedback` | Quick kudos/constructive feedback |
| `career_paths` | Career ladder definitions |
| `career_path_levels` | Steps/levels in a career path |
| `employee_career_tracks` | Employee assignment to career path/level |
| `one_on_one_meetings` | 1:1 meeting records with recurrence |
| `meeting_agenda_items` | Agenda, action items, and notes for 1:1s |
| `peer_review_nominations` | Peer nominations for 360 reviews |
| `rating_distributions` | Cached bell curve / distribution snapshots |
| `nine_box_placements` | Employee 9-box grid positions (performance vs potential) |
| `succession_plans` | Succession plans per critical role |
| `succession_candidates` | Candidates in succession plans with readiness level |
| `skills_assessments` | Employee skill ratings for gap analysis |
| `letter_templates` | Performance letter templates (appraisal, increment, promotion, etc.) |
| `generated_letters` | Generated performance letter PDFs |
| `email_reminder_configs` | Configurable reminder schedules per org |
| `manager_effectiveness_scores` | Manager effectiveness ratings and metrics |
| `audit_logs` | Module-specific audit trail |

**6 migrations** across the database schema.

---

## API Endpoints

All endpoints under `/api/v1/`. Server runs on port **4300**.

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/sso` | SSO token exchange (EMP Cloud JWT -> Performance session token) |

### Review Cycles
| Method | Path | Description |
|--------|------|-------------|
| GET | `/review-cycles` | List cycles (paginated, filterable by status, type, year) |
| POST | `/review-cycles` | Create new cycle |
| GET | `/review-cycles/:id` | Get cycle detail with participant stats |
| PUT | `/review-cycles/:id` | Update cycle settings/dates |
| POST | `/review-cycles/:id/launch` | Launch cycle, notify participants |
| POST | `/review-cycles/:id/close` | Close cycle, finalize ratings |
| POST | `/review-cycles/:id/participants` | Add participants (bulk) |
| GET | `/review-cycles/:id/ratings-distribution` | Bell curve data |

### Reviews
| Method | Path | Description |
|--------|------|-------------|
| GET | `/reviews` | List reviews for current user |
| GET | `/reviews/:id` | Get review detail with competency ratings |
| PUT | `/reviews/:id` | Save draft or submit review |
| POST | `/reviews/:id/submit` | Submit finalized review |

### Goals & OKRs
| Method | Path | Description |
|--------|------|-------------|
| GET | `/goals` | List goals (filter by employee, cycle, status) |
| POST | `/goals` | Create goal |
| GET | `/goals/:id` | Get goal with key results and check-ins |
| PUT | `/goals/:id` | Update goal |
| POST | `/goals/:id/key-results` | Add key result |
| POST | `/goals/:id/check-in` | Log progress check-in |

### Goal Alignment Tree
| Method | Path | Description |
|--------|------|-------------|
| GET | `/goal-alignment/tree` | Get full alignment tree (company -> dept -> team -> individual) |
| POST | `/goal-alignment/link` | Link child goal to parent goal |
| DELETE | `/goal-alignment/link/:id` | Remove alignment link |
| GET | `/goal-alignment/rollup/:goalId` | Get progress rollup for a goal and its children |

### 9-Box Grid
| Method | Path | Description |
|--------|------|-------------|
| GET | `/nine-box` | Get 9-box grid data for org/department |
| PUT | `/nine-box/:employeeId` | Update employee placement (performance vs potential) |
| GET | `/nine-box/history/:employeeId` | Get placement history over time |

### Succession Planning
| Method | Path | Description |
|--------|------|-------------|
| GET | `/succession-plans` | List succession plans |
| POST | `/succession-plans` | Create succession plan for a role |
| GET | `/succession-plans/:id` | Get plan with candidates and readiness |
| POST | `/succession-plans/:id/candidates` | Add candidate to plan |
| PUT | `/succession-plans/:id/candidates/:candidateId` | Update readiness level |
| DELETE | `/succession-plans/:id/candidates/:candidateId` | Remove candidate |

### Skills Gap Analysis
| Method | Path | Description |
|--------|------|-------------|
| GET | `/skills-gap/:employeeId` | Get skills gap analysis for an employee |
| GET | `/skills-gap/team/:teamId` | Get team-level skills gap summary |
| POST | `/skills-gap/assess` | Submit skill assessment |
| GET | `/skills-gap/recommendations/:employeeId` | Get learning recommendations |

### Manager Effectiveness
| Method | Path | Description |
|--------|------|-------------|
| GET | `/manager-effectiveness` | Get effectiveness scores for all managers |
| GET | `/manager-effectiveness/:managerId` | Get detailed effectiveness breakdown for a manager |
| GET | `/manager-effectiveness/:managerId/trends` | Get effectiveness trends over time |
| POST | `/manager-effectiveness/calculate` | Trigger effectiveness score recalculation |

### AI Review Summaries
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ai-summary/review/:reviewId` | Generate AI summary for an individual review |
| POST | `/ai-summary/cycle/:cycleId` | Generate AI summary for a review cycle |
| POST | `/ai-summary/team/:managerId` | Generate AI team performance summary |
| GET | `/ai-summary/:id` | Retrieve a previously generated summary |

### Performance Letters
| Method | Path | Description |
|--------|------|-------------|
| GET | `/letter-templates` | List letter templates (appraisal, increment, promotion, confirmation, warning) |
| POST | `/letter-templates` | Create letter template |
| PUT | `/letter-templates/:id` | Update template |
| POST | `/letters/generate` | Generate performance letter PDF |
| GET | `/letters/:id/download` | Download generated letter |
| POST | `/letters/:id/send` | Email letter to employee |

### Competency Frameworks
| Method | Path | Description |
|--------|------|-------------|
| GET | `/competency-frameworks` | List frameworks |
| POST | `/competency-frameworks` | Create framework |
| GET | `/competency-frameworks/:id` | Get with competencies |
| POST | `/competency-frameworks/:id/competencies` | Add competency |

### PIPs
| Method | Path | Description |
|--------|------|-------------|
| GET | `/pips` | List PIPs (filterable by status, employee, manager) |
| POST | `/pips` | Create PIP |
| GET | `/pips/:id` | Get PIP detail with objectives and updates |
| POST | `/pips/:id/objectives` | Add objective |
| POST | `/pips/:id/updates` | Add check-in/update |
| POST | `/pips/:id/close` | Close PIP with outcome (met/not_met/extended) |

### Career Paths
| Method | Path | Description |
|--------|------|-------------|
| GET | `/career-paths` | List career paths |
| POST | `/career-paths` | Create career path |
| GET | `/career-paths/:id` | Get career path with levels |
| POST | `/career-paths/:id/levels` | Add level |
| GET | `/employees/:id/career-track` | Get employee career track |
| PUT | `/employees/:id/career-track` | Assign/update career track |

### 1-on-1 Meetings
| Method | Path | Description |
|--------|------|-------------|
| GET | `/one-on-ones` | List meetings |
| POST | `/one-on-ones` | Create meeting |
| GET | `/one-on-ones/:id` | Get meeting detail with agenda items |
| POST | `/one-on-ones/:id/agenda-items` | Add agenda/action item |
| POST | `/one-on-ones/:id/complete` | Mark meeting completed |

### Continuous Feedback
| Method | Path | Description |
|--------|------|-------------|
| GET | `/feedback` | List feedback (given/received, public kudos wall) |
| POST | `/feedback` | Give feedback (kudos or constructive) |
| GET | `/feedback/:id` | Get feedback detail |

### Peer Reviews
| Method | Path | Description |
|--------|------|-------------|
| POST | `/peer-reviews/nominate` | Nominate peers for 360 review |
| GET | `/peer-reviews/nominations` | List nominations pending approval |
| POST | `/peer-reviews/nominations/:id/approve` | Approve nomination |
| POST | `/peer-reviews/nominations/:id/reject` | Reject nomination |

### Notification Settings
| Method | Path | Description |
|--------|------|-------------|
| GET | `/notifications/settings` | Get notification preferences |
| PUT | `/notifications/settings` | Update notification preferences |
| GET | `/notifications/pending` | View pending reminder queue |

### Analytics
| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/overview` | Dashboard summary stats |
| GET | `/analytics/ratings-distribution` | Bell curve data across cycles |
| GET | `/analytics/team-comparison` | Team-by-team performance comparison |
| GET | `/analytics/trends` | Performance trends over time |
| GET | `/analytics/goal-completion` | Goal completion rates by team/department |
| GET | `/analytics/top-performers` | Top and bottom performer rankings |

### Other Endpoints
- **Self-Service**: My reviews, goals, PIPs, 1:1s, feedback, career track, skills gap, letters
- **API Docs**: Swagger UI at `/api/docs`
- **Health**: GET `/health` for service health check

---

## Frontend Pages (44)

### Admin Pages
| Route | Page | Description |
|-------|------|-------------|
| `/dashboard` | Dashboard | Active cycles, pending reviews, goal completion rate, quick actions |
| `/review-cycles` | Review Cycles | Table with status badges, create button, filter by year/type |
| `/review-cycles/:id` | Review Cycle Detail | Tabs: Overview, Participants, Ratings Distribution, Settings |
| `/review-cycles/new` | Create Cycle | Multi-step wizard: type, dates, participants, competencies |
| `/goals` | Goals Overview | Tree view of org goals, filter by team/employee/status |
| `/goals/new` | Create Goal | Goal form with key results, alignment, weight |
| `/goals/:id` | Goal Detail | Key results, check-in history, progress chart |
| `/goals/alignment` | Goal Alignment Tree | Company -> dept -> team -> individual cascade with progress rollup |
| `/analytics` | Analytics | Bell curve, trends, team comparison, top performers |
| `/analytics/nine-box` | 9-Box Grid | Performance vs Potential matrix with color-coded cells, click to drill down |
| `/analytics/skills-gap` | Skills Gap Analysis | Radar chart, gap table, learning recommendations |
| `/succession-plans` | Succession Plans | List of plans with readiness indicators |
| `/succession-plans/:id` | Succession Plan Detail | Candidates, readiness tracking, development actions |
| `/competency-frameworks` | Competency Frameworks | CRUD list and editor |
| `/competency-frameworks/new` | Create Framework | Framework builder with competency weights |
| `/competency-frameworks/:id` | Framework Detail | Competency list, edit weights |
| `/pips` | PIP List | Filterable table by status/employee |
| `/pips/new` | Create PIP | PIP form with objectives and timeline |
| `/pips/:id` | PIP Detail | Timeline, objectives, updates, close action |
| `/career-paths` | Career Paths | Visual ladder editor, list view |
| `/career-paths/new` | Create Career Path | Path builder with levels |
| `/career-paths/:id` | Career Path Detail | Level progression, assigned employees |
| `/feedback` | Feedback Wall | Public kudos feed, give feedback button |
| `/feedback/give` | Give Feedback | Feedback form with type selection |
| `/one-on-ones` | 1:1 Overview | Manager view of all 1:1s |
| `/one-on-ones/new` | Create Meeting | Meeting form with recurrence settings |
| `/one-on-ones/:id` | Meeting Detail | Agenda items, action items, notes, complete button |
| `/letters` | Performance Letters | Generated letter list, generate new |
| `/letters/templates` | Letter Templates | CRUD with Handlebars preview for 5 letter types |
| `/settings` | Settings | Rating scales, defaults, notifications, reminder configuration |

### Self-Service Pages (Employee View)
| Route | Page | Description |
|-------|------|-------------|
| `/my` | My Performance | Cards: pending reviews, goals, upcoming 1:1, recent feedback |
| `/my/reviews` | My Reviews | List of reviews to complete (self, peer) |
| `/my/reviews/:id` | My Review Form | Self-assessment with competency ratings and comments |
| `/my/goals` | My Goals | Personal goals/OKRs with progress bars |
| `/my/goals/:id` | Goal Detail | Key results, check-in history, add check-in |
| `/my/pip` | My PIP | Current PIP, objectives, updates, timeline |
| `/my/one-on-ones` | My 1:1s | Upcoming/past meetings list |
| `/my/one-on-ones/:id` | 1:1 Detail | Meeting agenda, action items, notes |
| `/my/feedback` | My Feedback | Received and given feedback history |
| `/my/career` | My Career Path | Current level, next steps, competency gaps |
| `/my/skills` | My Skills Gap | Personal radar chart, gap analysis, recommended learning |
| `/my/reviews (cycle)` | My Cycle Reviews | Reviews within a specific cycle |
| `/my/letters` | My Letters | View and download performance letters |
| `/auth/login` | Login | SSO redirect or manual login |

---

## Background Jobs (BullMQ)

Automated reminder and notification system using Redis-backed job queues:

| Job | Schedule | Description |
|-----|----------|-------------|
| Review deadline reminders | Daily | Notify participants of upcoming review submission deadlines |
| PIP check-in alerts | Daily | Remind managers/employees of upcoming PIP check-in dates |
| Meeting reminders | Daily | Send reminders for upcoming 1-on-1 meetings |
| Goal due date alerts | Daily | Notify employees of goals approaching their due date |
| Cycle launch notifications | On launch | Email all participants when a review cycle is launched |
| Cycle close notifications | On close | Email all participants when a review cycle is closed |

---

## Test Deployment

| Environment | URL |
|-------------|-----|
| Frontend | https://test-performance.empcloud.com |
| API | https://test-performance-api.empcloud.com |

SSO integrated with EMP Cloud.

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
git clone https://github.com/EmpCloud/emp-performance.git
cd emp-performance
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
PORT=4300
NODE_ENV=development

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=secret
DB_NAME=emp_performance

# EMP Cloud (required for auth)
EMPCLOUD_DB_NAME=empcloud
EMPCLOUD_API_URL=http://localhost:3000
EMPCLOUD_PUBLIC_KEY_PATH=./keys/public.pem

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# AI (for review summaries)
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...

# Email (for reminders)
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
pnpm --filter @emp-performance/server dev    # Server on :4300
pnpm --filter @emp-performance/client dev    # Client on :5177

# Run migrations
pnpm --filter @emp-performance/server migrate
```

Once running, visit:
- **Client**: http://localhost:5177
- **API**: http://localhost:4300
- **API Documentation**: http://localhost:4300/api/docs

### Running Tests
```bash
# Run all tests (API + unit)
pnpm --filter @emp-performance/server test

# Run only unit tests
pnpm --filter @emp-performance/server test -- --grep "service"

# Run only API tests
pnpm --filter @emp-performance/server test -- --grep "API"

# Run E2E workflow tests
pnpm --filter @emp-performance/server test -- --grep "workflow"
```

---

## Cross-Module Integration

### Webhook to EMP Cloud
EMP Performance sends event webhooks to EMP Cloud for unified activity tracking:
- `review.completed` -- When a review cycle is closed and ratings finalized
- `pip.created` -- When a new PIP is created for an employee
- `pip.closed` -- When a PIP is closed with an outcome

### EMP Cloud AI Agent Tools
EMP Cloud's AI agent includes 3 cross-module tools that call EMP Performance's API:
- `get_review_cycle_status` -- Fetch active review cycle status and progress
- `get_goals_summary` -- Get goal completion summary by team
- `get_team_performance` -- Get team performance ratings and trends

### Skills Gap -> LMS Integration
Skills gap analysis recommendations can link to EMP LMS courses when both modules are active, providing a direct path from identified skill gaps to learning resources.

---

## License

This project is licensed under the [AGPL-3.0 License](LICENSE).
