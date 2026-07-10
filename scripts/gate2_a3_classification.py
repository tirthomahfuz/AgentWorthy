#!/usr/bin/env python3
"""A3: Real pipeline scan via POST /public/scan + llm_usage + schema_correct_type proof."""

import json
import os
import sys
import time

import httpx
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "apps", "api"))

load_dotenv(os.path.join(ROOT, ".env"))

from agentworthy.database import SessionLocal
from agentworthy.models import Check, LLMUsage, Scan, ScanStatus

API = os.environ.get("API_URL", "http://localhost:8000")
URL = "https://fahimison.vercel.app"


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    with httpx.Client(base_url=API, timeout=120) as client:
        resp = client.post("/public/scan", json={"url": URL})
        resp.raise_for_status()
        scan_id = resp.json()["scan_id"]
        print(f"Queued scan_id={scan_id} url={URL}")

        for _ in range(120):
            report = client.get(f"/public/scan/{scan_id}").json()
            if report["status"] in ("complete", "failed"):
                break
            time.sleep(2)
        else:
            print("ERROR: scan timed out", file=sys.stderr)
            sys.exit(1)

    db = SessionLocal()
    scan = db.get(Scan, scan_id)
    schema = (
        db.query(Check)
        .filter(Check.scan_id == scan_id, Check.check_key == "schema_correct_type")
        .first()
    )
    usage = db.query(LLMUsage).filter(LLMUsage.scan_id == scan_id).all()

    output = {
        "scan_id": str(scan_id),
        "url": URL,
        "status": scan.status.value if scan else None,
        "overall_score": scan.overall_score if scan else None,
        "letter_grade": scan.letter_grade if scan else None,
        "site_type": scan.site_type if scan else None,
        "schema_correct_type": {
            "status": schema.status.value if schema else None,
            "evidence": schema.evidence if schema else None,
            "plain_explanation": schema.plain_explanation if schema else None,
        },
        "llm_usage": [
            {
                "id": str(r.id),
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
            }
            for r in usage
        ],
    }
    print(json.dumps(output, indent=2))
    db.close()


if __name__ == "__main__":
    main()
