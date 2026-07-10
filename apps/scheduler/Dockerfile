FROM python:3.12-slim
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/
COPY apps/api/agentworthy apps/api/agentworthy
COPY apps/api/alembic apps/api/alembic
COPY apps/api/alembic.ini apps/api/
COPY apps/worker/pyproject.toml apps/worker/
COPY apps/worker/agentworthy_worker apps/worker/agentworthy_worker
RUN pip install --no-cache-dir -e apps/api -e apps/worker
ENV PYTHONPATH=/app/apps/api:/app/apps/worker
COPY apps/scheduler/scheduler_main.py apps/scheduler/
CMD ["python", "apps/scheduler/scheduler_main.py"]
