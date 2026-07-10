"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentworthy.config import get_settings
from agentworthy.routes.auth import router as auth_router
from agentworthy.routes.public import router as public_router
from agentworthy.routes.scans import router as scans_router
from agentworthy.routes.sites import router as sites_router

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
)

settings = get_settings()
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app = FastAPI(
    title="Agentworthy API",
    description="AI agent readiness auditing platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_router)
app.include_router(auth_router)
app.include_router(sites_router)
app.include_router(scans_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
