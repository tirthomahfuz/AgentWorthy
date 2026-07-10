# Changelog

All notable changes to Agentworthy are documented in this file.

## [Unreleased]

### Stages 3–7 (in progress on `cursor/full-product-8be4`)

- Stage 3: Agent simulation engine (Playwright loop, safety rails, fixture store, journey templates)
- Stage 4: Fix generation via Sonnet (batched by category, JSON-LD validation, llms.txt builder)
- Stage 5: Stripe billing (checkout, webhooks, plan limits, customer portal)
- Stage 6: Scan diff engine, scheduler container, alert rows
- Stage 7: SSRF guard, CI workflow, Makefile, DEPLOYMENT.md, seed script
- Migration `002_stage3_7`: fix_applied, api_tokens, stripe_events, deploy_hint columns
- 63 pytest tests passing (13 API + 50 worker)

### Gate 2 completion (Part A)

- Full Playwright e2e: magic-link login, add site, fail/pass verification, scan, dashboard score + sparkline
- Dev NextAuth file adapter for email magic links; production guard when RESEND_API_KEY missing
- SQLAlchemy enum value fix (`_pg_enum`) so Postgres receives lowercase enum values
- Proof artifacts: `docs/proof/gate2-dashboard.png`, gate scripts for A2/A3 validation

### Stage 2 — Auth, dashboard, site management

- NextAuth.js with email magic link (dev console fallback) and Google OAuth
- POST /auth/sync — JWT access tokens, users table sync on first login
- Sites CRUD with meta tag / DNS TXT verification
- Authenticated scans (manual trigger, 25/200 pages by verified status, one active scan per site)
- Dashboard with site cards, Recharts sparklines, empty states
- Settings skeleton (profile, sites, billing placeholder)
- Cross-user 403/404 tests, verification unit tests, Playwright e2e (full flow)

### Stage 1 — Complete static check suite

- Implemented all 20 static checks with CrawlContext pattern
- Per-check 10s timeouts in worker pipeline
- LLM site-type classification via haiku (with fallback to `other`)
- SSR content ratio hardening (render blocked, redirect limits, non-HTML)
- Weighted scoring with boundary tests (59/60, 89/90)
- 43 worker tests + 4 API tests passing
- Real scan validation against 5 live websites

## [0.1.0] — 2026-07-09

### Phase 1 scaffold

- Monorepo: apps/web, apps/api, apps/worker, packages/shared
- docker-compose.yml for local development
- Alembic initial migration with full schema
- First 3 static checks: robots_agent_access, llms_txt_present, ssr_content_ratio
- POST /public/scan with Redis rate limiting (3/IP/day)
- Landing page and /report/[scan_id] with live polling
