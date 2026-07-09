FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml apps/api/
COPY apps/api/agentworthy apps/api/agentworthy
COPY apps/api/alembic apps/api/alembic
COPY apps/api/alembic.ini apps/api/

COPY apps/worker/pyproject.toml apps/worker/
COPY apps/worker/agentworthy_worker apps/worker/agentworthy_worker

WORKDIR /app/apps/api
RUN pip install --no-cache-dir -e .

WORKDIR /app/apps/worker
RUN pip install --no-cache-dir -e . && playwright install chromium --with-deps

ENV PYTHONPATH=/app/apps/api:/app/apps/worker

CMD ["python", "-m", "agentworthy_worker.main"]
