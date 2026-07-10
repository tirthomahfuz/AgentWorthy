"""RQ job handlers for scan processing."""

import logging
import os
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from agentworthy.database import SessionLocal
from agentworthy.models import (
    Alert,
    AlertType,
    Check,
    Journey,
    Plan,
    PublicScan,
    Scan,
    ScanStatus,
    Simulation,
    SimulationOutcome,
    Site,
    User,
)
from agentworthy.plan_limits import get_plan_limits
from agentworthy.services.diff import diff_scans
from agentworthy_worker.checks.base import CheckResult
from agentworthy_worker.checks.runner import calculate_score, category_breakdown, run_all_checks
from agentworthy_worker.crawler import CRAWLER_USER_AGENT
from agentworthy_worker.fixes.generator import generate_fixes_for_category
from agentworthy_worker.llm.client import LLMClient
from agentworthy_worker.scan_context import build_crawl_context
from agentworthy_worker.security.ssrf import validate_scan_url
from agentworthy_worker.simulation.journeys import journeys_for_site_type
from agentworthy_worker.simulation.loop import run_simulation

logger = logging.getLogger(__name__)
SCAN_LLM_BUDGET = int(os.environ.get("SCAN_LLM_BUDGET", "300000"))


def _save_check(db: Session, scan_id: uuid.UUID, result: CheckResult, fix_meta: dict | None = None) -> None:
    meta = fix_meta or {}
    check = Check(
        id=uuid.uuid4(),
        scan_id=scan_id,
        category=result.category,
        check_key=result.check_key,
        status=result.status,
        weight=result.weight,
        evidence=result.evidence,
        plain_explanation=meta.get("plain_explanation") or result.plain_explanation,
        fix_code=meta.get("fix_code") or result.fix_code,
        fix_language=meta.get("fix_language") or result.fix_language,
        deploy_hint=meta.get("deploy_hint"),
        fix_before=meta.get("fix_before"),
        fix_after=meta.get("fix_after"),
    )
    db.add(check)


def _run_simulations(
    db: Session,
    scan_uuid: uuid.UUID,
    scan_id: str,
    root_url: str,
    site_type: str,
    site_id: uuid.UUID | None,
    max_sims: int,
    log: logging.LoggerAdapter,
) -> int:
    if max_sims <= 0:
        return 0
    tokens_used = [0]
    journeys = []
    if site_id:
        db_journeys = db.query(Journey).filter(Journey.site_id == site_id, Journey.enabled.is_(True)).all()
        journeys = [(j.task_key, j.task_template) for j in db_journeys]
    if not journeys:
        journeys = [(j["task_key"], j["task_template"]) for j in journeys_for_site_type(site_type)[:max_sims]]

    for task_key, task in journeys[:max_sims]:
        if tokens_used[0] >= SCAN_LLM_BUDGET:
            break
        sim_id = str(uuid.uuid4())
        try:
            result = run_simulation(scan_id, sim_id, root_url, task, token_budget=SCAN_LLM_BUDGET, tokens_used=tokens_used)
            outcome = SimulationOutcome.SUCCESS if result["outcome"] == "success" else SimulationOutcome.FAIL
            db.add(Simulation(
                id=uuid.UUID(sim_id),
                scan_id=scan_uuid,
                task_key=task_key,
                task_description=task,
                outcome=outcome,
                steps=result["steps"],
                failure_point=result.get("failure_point"),
                failure_reason=result.get("failure_reason"),
            ))
            db.commit()
        except Exception as e:
            log.exception("Simulation failed", extra={"task_key": task_key})
            db.add(Simulation(
                id=uuid.uuid4(),
                scan_id=scan_uuid,
                task_key=task_key,
                task_description=task,
                outcome=SimulationOutcome.FAIL,
                failure_point="error",
                failure_reason=str(e),
            ))
            db.commit()
    return tokens_used[0]


def _generate_fixes(
    results: list[CheckResult],
    site_type: str,
    site_name: str,
    site_url: str,
    scan_id: str,
) -> dict[str, dict]:
    llm = LLMClient(scan_id=scan_id)
    by_cat: dict[str, list[CheckResult]] = {}
    for r in results:
        by_cat.setdefault(r.category.value, []).append(r)
    all_fixes: dict[str, dict] = {}
    for cat, checks in by_cat.items():
        try:
            fixes = generate_fixes_for_category(cat, checks, site_type, site_name, site_url, llm)
            all_fixes.update(fixes)
        except Exception:
            logger.exception("Fix generation failed for %s", cat)
    return all_fixes


def _execute_scan(scan_id: str, root_url: str, max_pages: int, run_sims: bool = False, site_id: uuid.UUID | None = None) -> None:
    log = logging.LoggerAdapter(logger, {"correlation_id": scan_id})
    db = SessionLocal()
    try:
        root_url = validate_scan_url(root_url)
        scan_uuid = uuid.UUID(scan_id)
        scan = db.get(Scan, scan_uuid)
        if not scan:
            log.error("Scan not found")
            return

        scan.correlation_id = scan_id
        scan.status = ScanStatus.CRAWLING
        db.commit()

        headers = {"User-Agent": CRAWLER_USER_AGENT}
        with httpx.Client(headers=headers, follow_redirects=True, timeout=15.0) as client:
            log.info("Building crawl context", extra={"url": root_url, "max_pages": max_pages})
            ctx = build_crawl_context(client, root_url, max_pages=max_pages, scan_id=scan_id)

        max_sims = 0
        if run_sims and site_id:
            site = db.get(Site, site_id)
            user = db.get(User, site.user_id) if site else None
            if user and site and site.verified:
                max_sims = get_plan_limits(user.plan.value).simulations_per_scan

        if max_sims > 0:
            scan.status = ScanStatus.SIMULATING
            db.commit()
            tokens = _run_simulations(db, scan_uuid, scan_id, root_url, ctx.site_type or "other", site_id, max_sims, log)
            scan.llm_tokens_used = tokens

        scan.status = ScanStatus.SCORING
        db.commit()
        results = run_all_checks(ctx)
        fixes = _generate_fixes(results, ctx.site_type or "other", root_url, root_url, scan_id)

        for result in results:
            _save_check(db, scan_uuid, result, fixes.get(result.check_key))
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

        if site_id:
            prev = (
                db.query(Scan)
                .filter(Scan.site_id == site_id, Scan.id != scan_uuid, Scan.status == ScanStatus.COMPLETE)
                .order_by(Scan.finished_at.desc())
                .first()
            )
            if prev:
                prev_checks = db.query(Check).filter(Check.scan_id == prev.id).all()
                curr_checks = db.query(Check).filter(Check.scan_id == scan_uuid).all()
                prev_sims = db.query(Simulation).filter(Simulation.scan_id == prev.id).all()
                curr_sims = db.query(Simulation).filter(Simulation.scan_id == scan_uuid).all()
                for alert in diff_scans(prev_checks, curr_checks, prev_sims, curr_sims, prev.overall_score, score):
                    db.add(Alert(
                        site_id=site_id,
                        scan_id=scan_uuid,
                        type=AlertType(alert["type"]),
                        payload=alert,
                    ))

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
    _execute_scan(scan_id, root_url, max_pages=25, run_sims=False)


def run_site_scan(scan_id: str, root_url: str, max_pages: int = 25) -> None:
    log = logging.LoggerAdapter(logger, {"correlation_id": scan_id})
    log.info("Starting site scan", extra={"url": root_url, "max_pages": max_pages})
    db = SessionLocal()
    site_id = None
    try:
        scan = db.get(Scan, uuid.UUID(scan_id))
        site_id = scan.site_id if scan else None
    finally:
        db.close()
    _execute_scan(scan_id, root_url, max_pages=max_pages, run_sims=True, site_id=site_id)
