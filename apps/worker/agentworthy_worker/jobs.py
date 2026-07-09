"""RQ job handlers for scan processing."""

import logging
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from agentworthy.database import SessionLocal
from agentworthy.models import Check, CheckStatus, PublicScan, Scan, ScanStatus
from agentworthy_worker.checks.runner import calculate_score, run_implemented_checks
from agentworthy_worker.crawler import CRAWLER_USER_AGENT, crawl_site

logger = logging.getLogger(__name__)


def _save_check(db: Session, scan_id: uuid.UUID, result: object) -> None:
    from agentworthy_worker.checks.base import CheckResult

    assert isinstance(result, CheckResult)
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


def run_static_scan(scan_id: str) -> None:
    """Main RQ job: run static check suite for a scan."""
    correlation_id = scan_id
    log = logging.LoggerAdapter(logger, {"correlation_id": correlation_id})
    log.info("Starting static scan")

    db = SessionLocal()
    try:
        scan_uuid = uuid.UUID(scan_id)
        scan = db.get(Scan, scan_uuid)
        if not scan:
            log.error("Scan not found")
            return

        public_scan = db.query(PublicScan).filter(PublicScan.scan_id == scan_uuid).first()
        if not public_scan:
            log.error("Public scan record not found")
            scan.status = ScanStatus.FAILED
            scan.error_message = "No URL associated with scan"
            db.commit()
            return

        root_url = public_scan.url
        scan.status = ScanStatus.CRAWLING
        db.commit()

        log.info("Crawling site", extra={"url": root_url})
        pages = crawl_site(root_url, max_pages=25)
        homepage_html = pages.get(root_url) or (list(pages.values())[0] if pages else None)

        scan.status = ScanStatus.SCORING
        db.commit()

        rendered_html: str | None = None
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=CRAWLER_USER_AGENT)
                page.goto(root_url, wait_until="networkidle", timeout=30000)
                rendered_html = page.content()
                browser.close()
        except Exception as e:
            log.warning("Playwright render failed, using raw HTML only", extra={"error": str(e)})

        headers = {"User-Agent": CRAWLER_USER_AGENT}
        with httpx.Client(headers=headers, follow_redirects=True, timeout=15.0) as client:
            results = run_implemented_checks(root_url, client, rendered_html)

        for result in results:
            _save_check(db, scan_uuid, result)
            db.commit()

        score, grade = calculate_score(results)
        scan.overall_score = score
        scan.letter_grade = grade
        scan.status = ScanStatus.COMPLETE
        scan.finished_at = datetime.now(UTC)
        scan.site_type = "unknown"

        public_scan.score = score
        db.commit()

        log.info("Scan complete", extra={"score": score, "grade": grade})

    except Exception as e:
        log.exception("Scan failed")
        if db:
            scan = db.get(Scan, uuid.UUID(scan_id))
            if scan:
                scan.status = ScanStatus.FAILED
                scan.error_message = str(e)
                scan.finished_at = datetime.now(UTC)
                db.commit()
    finally:
        db.close()
