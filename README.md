# Agentworthy

AI agent readiness auditing platform. Answers one question for business owners: **Can AI agents (ChatGPT Operator, Claude computer use, Perplexity shopping agents) actually find, understand, and transact with your website?**

## Monorepo Structure

```
apps/
  web/      — Next.js 14 frontend (landing page, report viewer)
  api/      — FastAPI backend (REST API, auth, billing)
  worker/   — Scan engine (static checks, agent simulation)
packages/
  shared/   — Shared TypeScript types
```

## Quick Start (Local Development)

```bash
# 1. Clone and enter the repo
cd agentworthy

# 2. Copy environment variables
cp .env.example .env

# 3. Start infrastructure and services
docker compose up -d postgres redis

# 4. Install Python dependencies
cd apps/api && pip install -e ".[dev]" && cd ../..
cd apps/worker && pip install -e ".[dev]" && playwright install chromium && cd ../..

# 5. Run database migrations
cd apps/api && alembic upgrade head && cd ../..

# 6. Install Node dependencies
npm install

# 7. Start API, worker, and web (three terminals)
cd apps/api && uvicorn agentworthy.main:app --reload --port 8000
cd apps/worker && PYTHONPATH=../api python -m agentworthy_worker.main
npm run dev:web
```

Or run everything with Docker:

```bash
docker compose up --build
```

- **Web**: http://localhost:3000
- **API**: http://localhost:8000
- **API docs**: http://localhost:8000/docs

## Phase 1 Status (Current)

- [x] Monorepo scaffold with docker-compose
- [x] PostgreSQL schema via Alembic migration
- [x] Static check suite skeleton (20 checks defined)
- [x] First 3 checks fully implemented and tested:
  - `robots_agent_access` — AI bot access in robots.txt
  - `llms_txt_present` — llms.txt at site root
  - `ssr_content_ratio` — server-side content vs rendered DOM
- [x] POST `/public/scan` with Redis rate limiting (3/day per IP)
- [x] Landing page with URL scanner
- [x] Report page at `/report/[scan_id]` with live polling

## Running Tests

```bash
# Worker check suite tests
cd apps/worker && PYTHONPATH=../api pytest -v

# API tests
cd apps/api && pytest -v
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind, shadcn/ui |
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| Workers | Python, Playwright, RQ |
| Queue | Redis + RQ |
| Database | PostgreSQL 16, SQLAlchemy 2.0, Alembic |
| Auth | NextAuth.js (Phase 2) |
| Payments | Stripe (Phase 5) |

## License

Proprietary. All rights reserved.
