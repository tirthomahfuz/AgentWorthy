"""Authenticated scan routes."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from agentworthy.auth import get_current_user, get_site_for_user
from agentworthy.database import get_db
from agentworthy.models import Check, PublicScan, Scan, ScanStatus, ScanTrigger, Site, User
from agentworthy.redis_client import enqueue_site_scan
from agentworthy.schemas import CheckResult, ScanReport, ScanSummary, ScanTriggerResponse

router = APIRouter(prefix="/sites", tags=["scans"])


def _active_scan(db: Session, site_id: uuid.UUID) -> Scan | None:
    return (
        db.query(Scan)
        .filter(
            Scan.site_id == site_id,
            Scan.status.in_([
                ScanStatus.QUEUED,
                ScanStatus.CRAWLING,
                ScanStatus.SIMULATING,
                ScanStatus.SCORING,
            ]),
        )
        .first()
    )


@router.post("/{site_id}/scans", response_model=ScanTriggerResponse, status_code=201)
def trigger_scan(
    site_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanTriggerResponse:
    site = get_site_for_user(db, site_id, user)
    if _active_scan(db, site.id):
        raise HTTPException(status_code=409, detail="A scan is already running for this site")

    scan = Scan(
        site_id=site.id,
        status=ScanStatus.QUEUED,
        trigger=ScanTrigger.MANUAL,
        started_at=datetime.now(UTC),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    max_pages = 200 if site.verified else 25
    enqueue_site_scan(str(scan.id), site.root_url, max_pages)
    return ScanTriggerResponse(scan_id=scan.id, status=scan.status.value)


@router.get("/{site_id}/scans", response_model=list[ScanSummary])
def list_scans(
    site_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ScanSummary]:
    site = get_site_for_user(db, site_id, user)
    scans = db.query(Scan).filter(Scan.site_id == site.id).order_by(desc(Scan.started_at)).limit(50).all()
    return [
        ScanSummary(
            id=s.id,
            status=s.status.value,
            overall_score=s.overall_score,
            letter_grade=s.letter_grade,
            started_at=s.started_at,
            finished_at=s.finished_at,
            trigger=s.trigger.value,
        )
        for s in scans
    ]


@router.get("/{site_id}/scans/{scan_id}", response_model=ScanReport)
def get_scan_report(
    site_id: uuid.UUID,
    scan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanReport:
    site = get_site_for_user(db, site_id, user)
    scan = db.get(Scan, scan_id)
    if not scan or scan.site_id != site.id:
        raise HTTPException(status_code=404, detail="Scan not found")

    checks = db.query(Check).filter(Check.scan_id == scan_id).order_by(Check.category, Check.check_key).all()
    return ScanReport(
        id=scan.id,
        status=scan.status.value,
        overall_score=scan.overall_score,
        letter_grade=scan.letter_grade,
        site_type=scan.site_type,
        url=site.root_url,
        started_at=scan.started_at,
        finished_at=scan.finished_at,
        error_message=scan.error_message,
        checks=[CheckResult.model_validate(c) for c in checks],
        authenticated=True,
    )


@router.get("/{site_id}/sparkline")
def site_sparkline(
    site_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    site = get_site_for_user(db, site_id, user)
    since = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    since = since - timedelta(days=30)
    scans = (
        db.query(Scan)
        .filter(
            Scan.site_id == site.id,
            Scan.status == ScanStatus.COMPLETE,
            Scan.finished_at >= since,
        )
        .order_by(Scan.finished_at)
        .all()
    )
    return [
        {"date": s.finished_at.isoformat() if s.finished_at else None, "score": s.overall_score}
        for s in scans
        if s.overall_score is not None
    ]
