"""Public scan API routes."""

import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from agentworthy.database import get_db
from agentworthy.models import Check, PublicScan, Scan, ScanStatus, ScanTrigger
from agentworthy.redis_client import (
    check_rate_limit,
    enqueue_scan,
    hash_ip,
    increment_rate_limit,
)
from agentworthy.schemas import CheckResult, PublicScanRequest, PublicScanResponse, ScanReport
from agentworthy_worker.security.ssrf import validate_scan_url

router = APIRouter(prefix="/public", tags=["public"])


def normalize_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if not parsed.netloc:
        raise ValueError("Invalid URL")
    scheme = parsed.scheme or "https"
    return f"{scheme}://{parsed.netloc}{parsed.path.rstrip('/') or ''}"


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/plans")
def public_plans() -> list[dict]:
    from agentworthy.plan_limits import PLAN_LIMITS
    return [
        {
            "id": k,
            "name": v.name,
            "price_usd": v.price_usd,
            "max_sites": v.max_sites,
            "pages_per_scan": v.pages_per_scan,
            "simulations_per_scan": v.simulations_per_scan,
            "scan_frequency": v.scan_frequency,
            "api_access": v.api_access,
            "max_seats": v.max_seats,
        }
        for k, v in PLAN_LIMITS.items()
    ]


@router.post("/scan", response_model=PublicScanResponse)
def create_public_scan(
    body: PublicScanRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PublicScanResponse:
    ip = get_client_ip(request)
    ip_hash = hash_ip(ip)
    allowed, remaining = check_rate_limit(ip_hash)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Free tier allows 3 scans per day. Try again tomorrow.",
        )

    try:
        normalized = validate_scan_url(normalize_url(body.url))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    scan = Scan(
        status=ScanStatus.QUEUED,
        trigger=ScanTrigger.FREE_PUBLIC,
        started_at=datetime.now(UTC),
    )
    db.add(scan)
    db.flush()

    public_scan = PublicScan(
        url=normalized,
        email=body.email,
        ip_hash=ip_hash,
        scan_id=scan.id,
    )
    db.add(public_scan)
    db.commit()
    db.refresh(scan)

    increment_rate_limit(ip_hash)
    enqueue_scan(str(scan.id))

    return PublicScanResponse(
        scan_id=scan.id,
        public_scan_id=public_scan.id,
        status=scan.status.value,
    )


@router.get("/scan/{scan_id}", response_model=ScanReport)
def get_public_scan(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> ScanReport:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    public_scan = db.query(PublicScan).filter(PublicScan.scan_id == scan_id).first()
    checks = db.query(Check).filter(Check.scan_id == scan_id).order_by(Check.category, Check.check_key).all()

    return ScanReport(
        id=scan.id,
        status=scan.status.value,
        overall_score=scan.overall_score,
        letter_grade=scan.letter_grade,
        site_type=scan.site_type,
        url=public_scan.url if public_scan else None,
        started_at=scan.started_at,
        finished_at=scan.finished_at,
        error_message=scan.error_message,
        checks=[CheckResult.model_validate(c) for c in checks],
    )
