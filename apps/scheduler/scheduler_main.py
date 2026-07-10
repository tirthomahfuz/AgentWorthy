#!/usr/bin/env python3
"""Enqueue scheduled scans for paid plans."""

import hashlib
import logging
import os
import time

from sqlalchemy import and_

from agentworthy.database import SessionLocal
from agentworthy.models import Plan, Scan, ScanStatus, ScanTrigger, Site, User
from agentworthy.plan_limits import get_plan_limits
from agentworthy.redis_client import enqueue_site_scan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")

FREQUENCY_SEC = {"weekly": 7 * 86400, "daily": 86400}


def should_run(site_id: str, frequency: str) -> bool:
    h = int(hashlib.sha256(site_id.encode()).hexdigest()[:8], 16)
    window = FREQUENCY_SEC.get(frequency, 0)
    if not window:
        return False
    return (int(time.time()) + h) % window < 3600


def main() -> None:
    db = SessionLocal()
    try:
        sites = (
            db.query(Site)
            .join(User)
            .filter(Site.verified.is_(True), Site.read_only.is_(False))
            .all()
        )
        for site in sites:
            user = db.get(User, site.user_id)
            if not user:
                continue
            limits = get_plan_limits(user.plan.value)
            if limits.scan_frequency == "manual":
                continue
            if not should_run(str(site.id), limits.scan_frequency):
                continue
            active = db.query(Scan).filter(
                Scan.site_id == site.id,
                Scan.status.in_([ScanStatus.QUEUED, ScanStatus.CRAWLING, ScanStatus.SIMULATING, ScanStatus.SCORING]),
            ).first()
            if active:
                continue
            import uuid
            scan = Scan(site_id=site.id, status=ScanStatus.QUEUED, trigger=ScanTrigger.SCHEDULED)
            db.add(scan)
            db.commit()
            enqueue_site_scan(str(scan.id), site.root_url, limits.pages_per_scan)
            logger.info("Scheduled scan %s for %s", scan.id, site.root_url)
    finally:
        db.close()
    time.sleep(300)


if __name__ == "__main__":
    while True:
        main()
