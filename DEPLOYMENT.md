# Agentworthy Deployment Guide

## Table of Contents

1. [Architecture](#architecture)
2. [Environment Variables](#environment-variables)
3. [Local Development](#local-development)
4. [Production Deployment](#production-deployment)
5. [Stripe Webhook Setup](#stripe-webhook-setup)
6. [First-Deploy Checklist](#first-deploy-checklist)

## Architecture

- **Web** — Next.js on Vercel (or container)
- **API** — FastAPI container
- **Worker** — RQ + Playwright container
- **Scheduler** — Periodic scan enqueue container
- **Postgres** — Managed database
- **Redis** — Job queue + rate limiting

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `API_SECRET_KEY` | Yes | JWT signing secret |
| `NEXTAUTH_SECRET` | Yes | NextAuth session secret |
| `NEXTAUTH_URL` | Yes | Public web URL |
| `ANTHROPIC_API_KEY` | Yes | LLM classification, simulation, fixes |
| `STRIPE_SECRET_KEY` | Billing | Stripe test/live secret |
| `STRIPE_WEBHOOK_SECRET` | Billing | Webhook signature verification |
| `STRIPE_PRICE_STARTER` | Billing | Starter plan price ID |
| `STRIPE_PRICE_PRO` | Billing | Pro plan price ID |
| `STRIPE_PRICE_AGENCY` | Billing | Agency plan price ID |
| `RESEND_API_KEY` | Prod email | Magic link delivery |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth |
| `SCAN_LLM_BUDGET` | Optional | Max tokens per scan (default 300000) |
| `SCREENSHOT_PATH` | Optional | Simulation screenshot storage |

## Local Development

```bash
cp .env.example .env   # fill ANTHROPIC_API_KEY, NEXTAUTH_SECRET at minimum
make setup
make up
make seed
```

Open http://localhost:3000

## Production Deployment

1. Deploy Postgres and Redis
2. Build and deploy API, worker, scheduler containers
3. Deploy web to Vercel with `NEXT_PUBLIC_API_URL` pointing to API
4. Run `alembic upgrade head` on production database
5. Configure Stripe webhooks to `https://api.yourdomain.com/billing/webhook`

## Stripe Webhook Setup

Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`

## First-Deploy Checklist

- [ ] All env vars set
- [ ] Migrations applied
- [ ] Stripe products/prices created (`python scripts/stripe_seed.py`)
- [ ] Webhook endpoint verified
- [ ] Health checks: `/health` on API
- [ ] Self-audit scan of marketing site ≥ 95
