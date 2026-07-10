# Deploy Agentworthy on Vercel

## Why you saw `404: NOT_FOUND`

1. **`main` was empty** — only a README. Vercel had no Next.js app to build. This is fixed: `main` now contains the full app.
2. **Wrong Root Directory** — Vercel must build `apps/web`, not the repo root.

## Step 1 — Vercel project settings

In [Vercel Dashboard](https://vercel.com) → your project → **Settings → General**:

| Setting | Value |
|---------|--------|
| **Root Directory** | `apps/web` |
| **Framework Preset** | Next.js |
| **Node.js Version** | 22.x |

Leave Build Command and Install Command empty (uses `apps/web/vercel.json`).

## Step 2 — Environment variables

In **Settings → Environment Variables**, add:

| Variable | Example | Required |
|----------|---------|----------|
| `NEXTAUTH_SECRET` | `openssl rand -base64 32` | Yes |
| `NEXTAUTH_URL` | `https://your-app.vercel.app` | Yes |
| `RESEND_API_KEY` | from [resend.com](https://resend.com) | Yes (magic-link login) |
| `EMAIL_FROM` | `Agentworthy <onboarding@yourdomain.com>` | Yes with Resend |
| `API_URL` | `https://your-api.onrender.com` | Yes (for scans) |

You do **not** need `NEXT_PUBLIC_API_URL` if you use the built-in proxy (`/api/backend`).

## Step 3 — Deploy the backend (required for scans)

Vercel hosts the **frontend only**. Scans need FastAPI + Postgres + Redis + worker.

**Easiest option — Render (free tier):**

1. Go to [render.com](https://render.com) → New **Blueprint**
2. Connect this repo — uses `render.yaml` in the root
3. Copy the Render API URL (e.g. `https://agentworthy-api.onrender.com`)
4. Set `API_URL` in Vercel to that URL
5. Redeploy Vercel

## Step 4 — Redeploy

Push to `main` or click **Redeploy** in Vercel after changing env vars.

## Verify

- `https://your-app.vercel.app` — landing page
- `https://your-app.vercel.app/api/health` — should show `{"web":"ok","api":"ok",...}`

If `api` is `unreachable`, fix `API_URL` and ensure Render services are running.

## Local vs production

| Feature | Local (`make up`) | Vercel only | Vercel + Render API |
|---------|-------------------|-------------|---------------------|
| Landing page | ✅ | ✅ | ✅ |
| Free scan | ✅ | ❌ | ✅ |
| Login / dashboard | ✅ | ❌ (needs Resend) | ✅ |
