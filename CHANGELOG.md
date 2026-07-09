# Changelog

All notable changes to Agentworthy are documented in this file.

## [Unreleased]

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
