#!/usr/bin/env python3
"""Run real pipeline scan for fahimison.vercel.app and dump llm_usage + schema_correct_type."""

import json
import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "apps", "api"))
sys.path.insert(0, os.path.join(ROOT, "apps", "worker"))

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

import httpx
from sqlalchemy import text

from agentworthy.database import SessionLocal, engine
from agentworthy.models import Check, LLMUsage, Scan, ScanStatus, ScanTrigger
from agentworthy_worker.checks.runner import run_all_checks, calculate_score
from agentworthy_worker.crawler import CRAWLER_USER_AGENT
from agentworthy_worker.jobs import _save_check, _execute_scan
from agentworthy_worker.scan_context import build_crawl_context

URL = "https://fahimison.vercel.app"


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    scan_id = str(uuid.uuid4())
    db = SessionLocal()
    scan = Scan(
        id=uuid.UUID(scan_id),
        status=ScanStatus.QUEUED,
        trigger=ScanTrigger.FREE_PUBLIC,
    )
    db.add(scan)
    db.commit()
    db.close()

    print(f"Running pipeline scan_id={scan_id} url={URL}")
    _execute_scan(scan_id, URL, max_pages=25)

    db = SessionLocal()
    scan = db.get(Scan, uuid.UUID(scan_id))
    schema_check = (
        db.query(Check)
        .filter(Check.scan_id == scan.id, Check.check_key == "schema_correct_type")
        .first()
    )
    usage_rows = db.query(LLMUsage).filter(LLMUsage.scan_id == scan.id).all()

    output = {
        "scan_id": scan_id,
        "url": URL,
        "overall_score": scan.overall_score if scan else None,
        "letter_grade": scan.letter_grade if scan else None,
        "site_type": scan.site_type if scan else None,
        "schema_correct_type": {
            "status": schema_check.status.value if schema_check else None,
            "evidence": schema_check.evidence if schema_check else None,
            "plain_explanation": schema_check.plain_explanation if schema_check else None,
        },
        "llm_usage": [
            {
                "id": str(r.id),
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
            }
            for r in usage_rows
        ],
    }
    print(json.dumps(output, indent=2))
    db.close()


if __name__ == "__main__":
    main()
