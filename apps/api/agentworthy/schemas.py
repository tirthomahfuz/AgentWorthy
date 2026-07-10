"""Pydantic schemas for API request/response."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PublicScanRequest(BaseModel):
    url: str = Field(..., min_length=4, max_length=2048)
    email: str | None = None


class PublicScanResponse(BaseModel):
    scan_id: uuid.UUID
    public_scan_id: uuid.UUID
    status: str


class AuthSyncRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    name: str | None = Field(None, max_length=255)


class AuthSyncResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str | None
    access_token: str


class SiteCreate(BaseModel):
    root_url: str = Field(..., min_length=4, max_length=2048)
    display_name: str = Field(..., min_length=1, max_length=255)


class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    root_url: str
    display_name: str | None
    verified: bool
    verification_token: str | None
    created_at: datetime
    latest_score: int | None = None
    latest_grade: str | None = None
    last_scan_at: datetime | None = None


class SiteVerifyResponse(BaseModel):
    verified: bool
    message: str
    methods: dict[str, bool]


class ScanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    overall_score: int | None
    letter_grade: str | None
    started_at: datetime | None
    finished_at: datetime | None
    trigger: str


class ScanTriggerResponse(BaseModel):
    scan_id: uuid.UUID
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

    model_config = ConfigDict(from_attributes=True)


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
    authenticated: bool = False

    model_config = ConfigDict(from_attributes=True)


class RateLimitError(BaseModel):
    detail: str
    retry_after_seconds: int | None = None

