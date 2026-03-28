# EMP Rewards

> Employee recognition and rewards platform -- peer-to-peer kudos, points, badges, catalog redemption, team challenges, and celebrations.

[![Part of EmpCloud](https://img.shields.io/badge/EmpCloud-Module-blue)]()
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-purple.svg)](LICENSE)
[![Status: Built](https://img.shields.io/badge/Status-Built-green)]()

EMP Rewards is the employee recognition and rewards module of the [EmpCloud](https://empcloud.com) HRMS ecosystem. It provides peer-to-peer kudos with reactions and comments, a configurable points economy, badge achievements, a redeemable reward catalog, leaderboards, manager nominations, celebration feeds (birthdays, anniversaries), team challenges, automated milestone rewards, budget management, Slack and Microsoft Teams integrations, push notifications, and a manager recognition dashboard with engagement scoring.

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
| **Peer Recognition / Kudos** | Send kudos to colleagues with message, category, points, public/private visibility. Reactions and comments on public kudos. |
| **Points System** | Earn points for giving/receiving kudos, milestones, challenge wins. Configurable point values per org. Full ledger of all point transactions. |
| **Badges & Achievements** | Milestone badges (tenure, kudos count, top performer), custom org-defined badges. Auto-award on threshold triggers. |
| **Reward Catalog** | Redeemable rewards (gift cards, extra PTO, swag, experiences) with point-based pricing and stock management. |
| **Redemption & Fulfillment** | Employees redeem points for catalog rewards. Approval workflow with fulfillment tracking. |
| **Leaderboard** | Top recognized employees by period (weekly/monthly/quarterly). Department leaderboards and personal rank tracking. Cached and refreshed hourly. |
| **Manager Nominations** | Create nomination programs (Employee of the Month, etc.). Managers nominate employees; admins review and award. |
| **Celebrations Feed** | Auto-detect birthdays and work anniversaries from EMP Cloud. Combined social feed with kudos and celebrations. Send wishes. |
| **Team Challenges** | Time-bound competitions with rules, progress tracking, and auto-award for winners. Individual or team participation. |
| **Automated Milestone Rewards** | Define milestone rules (e.g., 1-year anniversary, 100 kudos received). System auto-triggers badges and point awards on threshold. |
| **Budget Management** | Set recognition budgets per manager or department. Track spend vs. allocation. Prevent over-budget recognition. |
| **Slack Integration** | Incoming webhook notifications for kudos and badges. `/kudos` slash command support. Per-org configuration. |
| **Microsoft Teams Integration** | Webhook notifications for kudos, celebrations, and milestones. Configurable per-org with test webhook support. |
| **Push Notifications** | Web push via VAPID keys. Subscribe/unsubscribe endpoints. Real-time alerts for kudos, badges, and celebrations. |
| **Manager Recognition Dashboard** | Team engagement score, department comparison, AI-powered recognition recommendations. |
| **Analytics** | Recognition trends, most recognized values, department participation, budget utilization, top recognizers. |
| **Integration API** | `/integration/user/:userId/summary` endpoint for EMP Performance module to fetch recognition data. |
| **API Documentation** | Swagger UI at `/api/docs` with full OpenAPI 3.0 spec. |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Runtime | Node.js 20 |
| Backend | Express 5, TypeScript |
| Frontend | React 19, Vite 6, TypeScript |
| Styling | Tailwind CSS, Radix UI |
| Database | MySQL 8 via Knex.js (`emp_rewards` database) |
| Cache / Queue | Redis 7, BullMQ |
| Auth | OAuth2/OIDC via EMP Cloud (RS256 JWT verification) |
| Integrations | Slack Webhooks & Slash Commands, Microsoft Teams Webhooks, Web Push (VAPID) |
| Monorepo | pnpm workspaces (3 packages) |

---

## Quick Start

### Prerequisites

- Node.js 20+
- pnpm 9+
- MySQL 8+
- Redis 7+
- EMP Cloud running (for authentication)

### Install

```bash
git clone https://github.com/EmpCloud/emp-rewards.git
cd emp-rewards
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
pnpm --filter @emp-rewards/server dev    # Server on :4600
pnpm --filter @emp-rewards/client dev    # Client on :5180

# Run migrations
pnpm --filter @emp-rewards/server migrate
```

Once running, visit:
- **Client**: http://localhost:5180
- **API**: http://localhost:4600
- **API Documentation**: http://localhost:4600/api/docs

---

## Project Structure

```
emp-rewards/
  package.json
  pnpm-workspace.yaml
  tsconfig.json
  docker-compose.yml
  .env.example
  packages/
    shared/                     # @emp-rewards/shared
      src/
        types/                  # TypeScript interfaces & enums
        validators/             # Zod request validation schemas
        constants/              # Categories, defaults, permissions
    server/                     # @emp-rewards/server (port 4600)
      src/
        config/                 # Environment configuration
        db/
          connection.ts         # Knex connection to emp_rewards
          empcloud.ts           # Read-only connection to empcloud DB
          migrations/sql/       # 7 migration files
        api/
          middleware/            # Auth, RBAC, error handling
          routes/               # 18 route modules
        services/               # 17 business logic service modules
        jobs/                   # BullMQ workers (badge eval, leaderboard, celebrations, milestones, challenges)
        utils/                  # Logger, errors, response helpers
        swagger/                # OpenAPI spec & Swagger UI setup
    client/                     # @emp-rewards/client (port 5180)
      src/
        api/                    # API client & hooks
        components/
          layout/               # DashboardLayout, SelfServiceLayout
          ui/                   # Radix-based UI primitives
          rewards/              # ChallengeCard, MilestoneProgress, EngagementScore, etc.
        pages/                  # 15 route-based page modules
        lib/                    # Auth store, utilities
```

---

## Database Schema

21+ tables across 7 migrations:

| Table | Purpose |
|-------|---------|
| `recognition_settings` | Per-org configuration (point values, kudos limits, moderation) |
| `recognition_categories` | Kudos categories (teamwork, innovation, leadership, etc.) |
| `kudos` | Core recognition records (sender, recipient, message, points) |
| `kudos_reactions` | Likes/emoji reactions on kudos |
| `kudos_comments` | Comments on public kudos |
| `point_balances` | Current redeemable balance per user |
| `point_transactions` | Ledger of all point changes (earn/spend) |
| `badge_definitions` | System and org-custom badge templates with criteria |
| `user_badges` | Badges earned by users |
| `reward_catalog` | Redeemable rewards with point cost and stock |
| `reward_redemptions` | Employee redemption requests with approval status |
| `nomination_programs` | Programs like "Employee of the Month" |
| `nominations` | Individual nominations submitted by managers |
| `leaderboard_cache` | Materialized leaderboard rankings (refreshed hourly) |
| `recognition_budgets` | Per-manager/department spend caps |
| `celebration_events` | Birthdays, work anniversaries, promotions |
| `notifications` | In-app notification queue |
| `team_challenges` | Time-bound team competitions with rules and prizes |
| `challenge_participants` | Team/individual participation and progress in challenges |
| `milestone_rules` | Automated milestone trigger definitions |
| `slack_integrations` | Per-org Slack and MS Teams webhook URLs and config |

---

## API Endpoints

All endpoints under `/api/v1/`. Server runs on port **4600**.

### Kudos / Recognition

| Method | Path | Description |
|--------|------|-------------|
| POST | `/kudos` | Send kudos to a colleague |
| GET | `/kudos` | Public kudos feed (paginated) |
| GET | `/kudos/:id` | Single kudos detail |
| DELETE | `/kudos/:id` | Retract own kudos |
| GET | `/kudos/received` | My received kudos |
| GET | `/kudos/sent` | My sent kudos |
| POST | `/kudos/:id/reactions` | React to kudos |
| POST | `/kudos/:id/comments` | Comment on kudos |

### Points

| Method | Path | Description |
|--------|------|-------------|
| GET | `/points/balance` | My point balance |
| GET | `/points/transactions` | My points history |
| POST | `/points/adjust` | Manual point adjustment (admin) |

### Badges

| Method | Path | Description |
|--------|------|-------------|
| GET | `/badges` | List badge definitions |
| POST | `/badges` | Create custom badge (admin) |
| GET | `/badges/my` | My earned badges |
| POST | `/badges/award` | Manually award badge (admin/manager) |

### Rewards Catalog

| Method | Path | Description |
|--------|------|-------------|
| GET | `/rewards` | Browse catalog |
| POST | `/rewards` | Create reward (admin) |
| POST | `/rewards/:id/redeem` | Redeem points for reward |

### Redemptions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/redemptions` | List all redemptions (admin) |
| GET | `/redemptions/my` | My redemptions |
| PUT | `/redemptions/:id/approve` | Approve redemption |
| PUT | `/redemptions/:id/fulfill` | Mark fulfilled |

### Nominations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/nominations/programs` | List nomination programs |
| POST | `/nominations/programs` | Create program (admin) |
| POST | `/nominations` | Submit nomination |
| PUT | `/nominations/:id/review` | Review nomination (admin) |

### Leaderboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/leaderboard` | Org leaderboard (by period) |
| GET | `/leaderboard/department/:deptId` | Department leaderboard |
| GET | `/leaderboard/my-rank` | My current rank |

### Celebrations Feed

| Method | Path | Description |
|--------|------|-------------|
| GET | `/celebrations` | Upcoming birthdays and work anniversaries |
| GET | `/celebrations/feed` | Combined celebration + kudos social feed |
| POST | `/celebrations/:id/wish` | Send a wish for a celebration |

### Team Challenges

| Method | Path | Description |
|--------|------|-------------|
| GET | `/challenges` | List active and past challenges |
| POST | `/challenges` | Create team challenge (admin) |
| GET | `/challenges/:id` | Challenge detail with leaderboard |
| POST | `/challenges/:id/join` | Join a challenge |
| GET | `/challenges/:id/progress` | Progress for all participants |
| POST | `/challenges/:id/complete` | End challenge and auto-award winners |

### Automated Milestone Rewards

| Method | Path | Description |
|--------|------|-------------|
| GET | `/milestones/rules` | List milestone trigger rules |
| POST | `/milestones/rules` | Create milestone rule (admin) |
| PUT | `/milestones/rules/:id` | Update milestone rule |
| GET | `/milestones/history` | View triggered milestone awards |

### Manager Recognition Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/manager/dashboard` | Team engagement score and recognition summary |
| GET | `/manager/team-comparison` | Department-level recognition comparison |
| GET | `/manager/recommendations` | AI-powered recognition recommendations |

### Slack Integration

| Method | Path | Description |
|--------|------|-------------|
| GET | `/slack/config` | Get Slack integration config |
| PUT | `/slack/config` | Update webhook URL and settings |
| POST | `/slack/test` | Send test notification to Slack |
| POST | `/slack/slash-command` | Handle /kudos slash command from Slack |

### Microsoft Teams Integration

| Method | Path | Description |
|--------|------|-------------|
| GET | `/teams` | Get Teams integration config |
| PUT | `/teams` | Update Teams webhook URL and settings (admin) |
| POST | `/teams/test` | Test webhook delivery (admin) |

### Push Notifications

| Method | Path | Description |
|--------|------|-------------|
| GET | `/push/vapid-key` | Get VAPID public key for client subscription |
| POST | `/push/subscribe` | Register push subscription |
| POST | `/push/unsubscribe` | Remove push subscription |
| POST | `/push/test` | Test push notification to self |

### Other Endpoints

| Area | Description |
|------|-------------|
| Settings | Org recognition settings, category CRUD |
| Budgets | CRUD budgets, usage tracking |
| Notifications | List, mark read, unread count |
| Analytics | Overview, trends, categories, departments, top recognizers, budget utilization |
| Integration | `/integration/user/:userId/summary` for EMP Performance |
| Health | `/health` basic health check |
| API Docs | Swagger UI at `/api/docs` |

---

## Frontend Pages

### Admin / Manager Views

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard` | Dashboard | Overview stats, recent activity, quick send kudos |
| `/feed` | Social Feed | Public celebration wall / social feed |
| `/kudos` | Kudos Management | All kudos with moderation tools |
| `/leaderboard` | Leaderboard | Org-wide leaderboard with period/dept filters |
| `/badges` | Badge Management | Create/manage badge definitions |
| `/rewards` | Reward Catalog | Manage reward catalog |
| `/redemptions` | Redemption Management | Approve/reject/fulfill redemptions |
| `/nominations` | Nomination Management | Manage programs, review nominations |
| `/budgets` | Budget Management | Set and track recognition budgets |
| `/challenges` | Team Challenges | Create and manage time-bound competitions |
| `/challenges/:id` | Challenge Detail | Progress tracking, participant leaderboard |
| `/milestones` | Milestone Rules | Configure automated milestone reward triggers |
| `/celebrations` | Celebrations | Upcoming birthdays, anniversaries, wish functionality |
| `/analytics` | Analytics | Charts: trends, categories, departments, ROI |
| `/settings` | Settings | Org recognition settings, categories, Slack config, Teams config |

### Employee Self-Service

| Route | Page | Description |
|-------|------|-------------|
| `/my` | My Summary | Points balance, recent kudos, badges |
| `/my/kudos` | My Kudos | Send kudos, view sent/received |
| `/my/badges` | My Badges | Earned badges, progress toward next |
| `/my/rewards` | Reward Catalog | Browse and redeem rewards |
| `/my/redemptions` | My Redemptions | Track redemption status |
| `/my/notifications` | Notifications | Notification center |

---

## Test Suite

BullMQ background workers cover badge evaluation, leaderboard refresh, celebration detection, milestone triggers, and challenge completion. Manual and automated testing covers all 18 route modules and 17 service modules.

---

## Test Deployment

| Environment | URL |
|-------------|-----|
| Frontend | https://test-rewards.empcloud.com |
| API | https://test-rewards-api.empcloud.com |

SSO integrated with EMP Cloud.

---

## License

This project is licensed under the [AGPL-3.0 License](LICENSE).
