"""RQ job handlers for scan processing."""

import logging
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from agentworthy.database import SessionLocal
from agentworthy.models import Check, PublicScan, Scan, ScanStatus
from agentworthy_worker.checks.base import CheckResult
from agentworthy_worker.checks.runner import calculate_score, category_breakdown, run_all_checks
from agentworthy_worker.crawler import CRAWLER_USER_AGENT
from agentworthy_worker.scan_context import build_crawl_context

logger = logging.getLogger(__name__)


def _save_check(db: Session, scan_id: uuid.UUID, result: CheckResult) -> None:
    check = Check(
        id=uuid.uuid4(),
        scan_id=scan_id,
        category=result.category,
        check_key=result.check_key,
        status=result.status,
        weight=result.weight,
        evidence=result.evidence,
        plain_explanation=result.plain_explanation,
        fix_code=result.fix_code,
        fix_language=result.fix_language,
    )
    db.add(check)


def _execute_scan(scan_id: str, root_url: str, max_pages: int) -> None:
    log = logging.LoggerAdapter(logger, {"correlation_id": scan_id})
    db = SessionLocal()
    try:
        scan_uuid = uuid.UUID(scan_id)
        scan = db.get(Scan, scan_uuid)
        if not scan:
            log.error("Scan not found")
            return

        scan.status = ScanStatus.CRAWLING
        db.commit()

        headers = {"User-Agent": CRAWLER_USER_AGENT}
        with httpx.Client(headers=headers, follow_redirects=True, timeout=15.0) as client:
            log.info("Building crawl context", extra={"url": root_url, "max_pages": max_pages})
            ctx = build_crawl_context(client, root_url, max_pages=max_pages, scan_id=scan_id)

            scan.status = ScanStatus.SCORING
            db.commit()

            results = run_all_checks(ctx)

        for result in results:
            _save_check(db, scan_uuid, result)
            db.commit()

        score, grade = calculate_score(results)
        breakdown = category_breakdown(results)

        scan.overall_score = score
        scan.letter_grade = grade
        scan.status = ScanStatus.COMPLETE
        scan.finished_at = datetime.now(UTC)
        scan.site_type = ctx.site_type or "other"

        public_scan = db.query(PublicScan).filter(PublicScan.scan_id == scan_uuid).first()
        if public_scan:
            public_scan.score = score

        db.commit()
        log.info("Scan complete", extra={"score": score, "grade": grade, "breakdown": breakdown})

    except Exception as e:
        log.exception("Scan failed")
        scan = db.get(Scan, uuid.UUID(scan_id))
        if scan:
            scan.status = ScanStatus.FAILED
            scan.error_message = str(e)
            scan.finished_at = datetime.now(UTC)
            db.commit()
    finally:
        db.close()


def run_static_scan(scan_id: str) -> None:
    """Public free scan job."""
    log = logging.LoggerAdapter(logger, {"correlation_id": scan_id})
    log.info("Starting public static scan")
    db = SessionLocal()
    try:
        scan_uuid = uuid.UUID(scan_id)
        public_scan = db.query(PublicScan).filter(PublicScan.scan_id == scan_uuid).first()
        if not public_scan:
            scan = db.get(Scan, scan_uuid)
            if scan:
                scan.status = ScanStatus.FAILED
                scan.error_message = "No URL associated with scan"
                db.commit()
            return
        root_url = public_scan.url
    finally:
        db.close()
    _execute_scan(scan_id, root_url, max_pages=25)


def run_site_scan(scan_id: str, root_url: str, max_pages: int = 25) -> None:
    """Authenticated site scan job."""
    log = logging.LoggerAdapter(logger, {"correlation_id": scan_id})
    log.info("Starting site scan", extra={"url": root_url, "max_pages": max_pages})
    _execute_scan(scan_id, root_url, max_pages=max_pages)
