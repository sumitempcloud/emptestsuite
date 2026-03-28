# EmpCloud Workforce Management

EmpCloud is a workforce management platform with a Next.js frontend and Node.js backend APIs for project and task operations.

Repository: [https://github.com/EmpCloud/emp-project](https://github.com/EmpCloud/emp-project)

## Repository Structure

```text
emp-project/
├─ packages/
│  ├─ client/           # Next.js frontend app (port 3000)
│  └─ server/
│     ├─ project/       # Project management API (port 9000)
│     └─ task/          # Task management API (port 9001)
├─ LICENSE
└─ .gitignore
```

## Services At a Glance

| Service | Path | Purpose | Default Port |
|---|---|---|---|
| Client | `packages/client` | Web dashboard, auth, reports, chat, admin/member UI | `3000` |
| Project API | `packages/server/project` | Admin, users, roles/permissions, projects, reports, uploads | `9000` |
| Task API | `packages/server/task` | Task/subtask workflows and task-related APIs | `9001` |
| Redis | external dependency | Caching and shared runtime support | `6379` |

## Prerequisites

- Node.js 18+ and npm 9+
- Redis running locally on `6379`
- MongoDB access (local or remote, based on service config)

## Quick Start (Local Development)

Start services in this order: backend APIs first, then client.

### 1) Start Project API

```bash
cd packages/server/project
npm install
npm run dev
```

This runs swagger generation and starts `project.server.js` with nodemon.

### 2) Start Task API

```bash
cd packages/server/task
npm install
npm run dev
```

This runs swagger generation and starts `task.server.js` with nodemon.

### 3) Start Client

```bash
cd packages/client
npm install
cp .env.example .env
npm run dev
```

Frontend runs at `http://localhost:3000`.

## Environment Configuration

- Client environment template: `packages/client/.env.example`
- Backend configuration files:
  - `packages/server/project/config/localDev.json`
  - `packages/server/task/config/localDev.json`

Client typically points to:

- `PROJECT_API=http://localhost:9000/v1`
- `TASK_API=http://localhost:9001/v1`

If you run all services locally, ensure these values in client `.env` match your active backend ports.

## Useful Commands

### Run everything from repo root

```bash
# one-time setup: install all package dependencies
npm install
npm run install:all

# run project API + task API + client together
npm run dev:all
```

Single command (installs + starts all services):

```bash
npm run start:all
```

### Client

```bash
cd packages/client
npm run dev
npm run build
npm run lint
```

### Project API

```bash
cd packages/server/project
npm run dev
```

### Task API

```bash
cd packages/server/task
npm run dev
```

## API Docs

- Project API Swagger: `http://localhost:9000/explorer`
- Task API Swagger: check service output for explorer URL (depends on local config)

## Existing Package Documentation

- Frontend docs: `packages/client/README.md`
- Project API docs: `packages/server/project/Readme.md`


