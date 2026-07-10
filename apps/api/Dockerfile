FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml apps/api/
COPY apps/api/agentworthy apps/api/agentworthy
COPY apps/api/alembic apps/api/alembic
COPY apps/api/alembic.ini apps/api/

WORKDIR /app/apps/api

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn agentworthy.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
