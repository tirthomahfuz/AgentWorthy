"""Pydantic schemas for API request/response."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class PublicScanRequest(BaseModel):
    url: str = Field(..., min_length=4, max_length=2048)
    email: str | None = None


class PublicScanResponse(BaseModel):
    scan_id: uuid.UUID
    public_scan_id: uuid.UUID
    status: str


class CheckResult(BaseModel):
    id: uuid.UUID
    category: str
    check_key: str
    status: str
    weight: int
    evidence: dict[str, Any] | None
    plain_explanation: str | None
    fix_code: str | None
    fix_language: str | None

    model_config = {"from_attributes": True}


class ScanReport(BaseModel):
    id: uuid.UUID
    status: str
    overall_score: int | None
    letter_grade: str | None
    site_type: str | None
    url: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    checks: list[CheckResult] = []

    model_config = {"from_attributes": True}


class RateLimitError(BaseModel):
    detail: str
    retry_after_seconds: int | None = None
