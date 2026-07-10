#!/usr/bin/env python3
"""Seed dev user, verified fixture site, and one completed scan."""

import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "apps", "api"))
sys.path.insert(0, os.path.join(ROOT, "apps", "worker"))

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

from agentworthy.database import SessionLocal
from agentworthy.models import Check, CheckCategory, CheckStatus, Plan, Scan, ScanStatus, ScanTrigger, Site, User
from agentworthy.services.verification import generate_verification_token


def main() -> None:
    db = SessionLocal()
    email = "dev@agentworthy.local"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name="Dev User", plan=Plan.FREE)
        db.add(user)
        db.commit()
        db.refresh(user)

    site = db.query(Site).filter(Site.user_id == user.id).first()
    if not site:
        site = Site(
            user_id=user.id,
            root_url="http://localhost:8780",
            display_name="Fixture Store",
            verified=True,
            verification_token=generate_verification_token(),
        )
        db.add(site)
        db.commit()
        db.refresh(site)

    existing = db.query(Scan).filter(Scan.site_id == site.id, Scan.status == ScanStatus.COMPLETE).first()
    if not existing:
        scan = Scan(
            site_id=site.id,
            status=ScanStatus.COMPLETE,
            trigger=ScanTrigger.MANUAL,
            overall_score=72,
            letter_grade="C",
            site_type="ecommerce",
        )
        db.add(scan)
        db.flush()
        db.add(Check(
            scan_id=scan.id,
            category=CheckCategory.DISCOVERABILITY,
            check_key="robots_agent_access",
            status=CheckStatus.PASS,
            weight=5,
            plain_explanation="Robots allows agents",
        ))
        db.commit()
        print(f"Created scan {scan.id}")
    else:
        print(f"Scan already exists {existing.id}")
    print(f"Dev user: {email}, site: {site.root_url}")
    db.close()


if __name__ == "__main__":
    main()
