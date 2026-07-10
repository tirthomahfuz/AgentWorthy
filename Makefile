.PHONY: setup up down reset-db test test-e2e lint scan migrate seed

# Fill these in .env after: cp .env.example .env
# Required: ANTHROPIC_API_KEY, NEXTAUTH_SECRET
# For billing: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_*
# Optional: RESEND_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

setup:
	npm install
	cd apps/api && pip install -e ".[dev]" 2>/dev/null || pip install -e .
	cd apps/worker && pip install -e ".[dev]" 2>/dev/null || pip install -e .
	cd apps/worker && playwright install chromium 2>/dev/null || true
	cp -n .env.example .env || true
	$(MAKE) migrate

migrate:
	cd apps/api && alembic upgrade head

up:
	docker compose up -d --build

down:
	docker compose down

reset-db:
	docker compose down -v 2>/dev/null || true
	$(MAKE) up
	sleep 8
	$(MAKE) migrate
	$(MAKE) seed

test:
	cd apps/api && PYTHONPATH=../worker pytest -q
	cd apps/worker && PYTHONPATH=../api pytest -q

test-e2e:
	cd apps/web && npx playwright test

lint:
	cd apps/api && ruff check . 2>/dev/null || true
	cd apps/worker && ruff check . 2>/dev/null || true
	cd apps/web && npm run lint 2>/dev/null || true

seed:
	python3 scripts/seed_dev.py

scan:
	@test -n "$(URL)" || (echo "Usage: make scan URL=https://example.com" && exit 1)
	python3 scripts/run_scan.py "$(URL)"
