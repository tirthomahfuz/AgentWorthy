#!/usr/bin/env bash
# Start full stack for Gate 2 e2e and classification scan.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/workspace/local/pgsql/bin:/workspace/local/redis/bin:$PATH"
export DATABASE_URL="${DATABASE_URL:-postgresql://agentworthy@localhost:5432/agentworthy}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export NEXTAUTH_SECRET="${NEXTAUTH_SECRET:-dev-nextauth-secret-change-in-production}"
export NEXTAUTH_URL="${NEXTAUTH_URL:-http://localhost:3000}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
export PYTHONPATH="$ROOT/apps/api:$ROOT/apps/worker"

# Load .env if present (includes ANTHROPIC_API_KEY when configured)
if [ -f "$ROOT/.env" ]; then set -a; source "$ROOT/.env"; set +a; fi

echo "ANTHROPIC_API_KEY set: $([ -n "${ANTHROPIC_API_KEY:-}" ] && echo yes || echo no)"

cd "$ROOT/apps/api"
alembic upgrade head

echo "Stack env ready. Start services in separate terminals:"
echo "  uvicorn agentworthy.main:app --host 0.0.0.0 --port 8000"
echo "  python -m agentworthy_worker.main"
echo "  python3 apps/web/e2e/fixture_server.py"
echo "  npm run dev:web --workspace=apps/web"
