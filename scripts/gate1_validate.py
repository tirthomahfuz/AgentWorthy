#!/usr/bin/env python3
"""Gate 1 validation script — full scan JSON, 429 proof, pytest, llm_usage."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from io import StringIO

# Paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "apps", "api"))
sys.path.insert(0, os.path.join(ROOT, "apps", "worker"))

SITES = [
    ("Shopify", "https://www.gymshark.com"),
    ("Restaurant", "https://www.olivegarden.com"),
    ("SaaS", "https://vercel.com"),
    ("Local services", "https://www.angieslist.com"),
    ("fahimison.vercel.app", "https://fahimison.vercel.app"),
]


def run_full_scans() -> list[dict]:
    import httpx
    from agentworthy_worker.checks.runner import calculate_score, category_breakdown, run_all_checks
    from agentworthy_worker.crawler import CRAWLER_USER_AGENT
    from agentworthy_worker.scan_context import build_crawl_context

    results = []
    headers = {"User-Agent": CRAWLER_USER_AGENT}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client:
        for label, url in SITES:
            print(f"\n{'='*60}\nScanning [{label}]: {url}\n{'='*60}", file=sys.stderr)
            try:
                ctx = build_crawl_context(client, url, max_pages=10, scan_id=str(uuid.uuid4()))
                checks = run_all_checks(ctx)
                score, grade = calculate_score(checks)
                output = {
                    "label": label,
                    "url": url,
                    "overall_score": score,
                    "letter_grade": grade,
                    "site_type": ctx.site_type,
                    "category_breakdown": category_breakdown(checks),
                    "checks": [
                        {
                            "check_key": r.check_key,
                            "category": r.category.value,
                            "status": r.status.value,
                            "weight": r.weight,
                        }
                        for r in checks
                    ],
                    "error": None,
                }
            except Exception as e:
                output = {
                    "label": label,
                    "url": url,
                    "overall_score": None,
                    "letter_grade": None,
                    "site_type": None,
                    "category_breakdown": {},
                    "checks": [],
                    "error": str(e),
                }
            results.append(output)
            print(json.dumps(output, indent=2))
    return results


def analyze_scores(results: list[dict]) -> list[str]:
    warnings = []
    scores = [r["overall_score"] for r in results if r["overall_score"] is not None]
    for r in results:
        if r.get("error"):
            warnings.append(f"ERROR: {r['label']} ({r['url']}) failed: {r['error']}")
        s = r.get("overall_score")
        if s == 0:
            warnings.append(f"SUSPICIOUS: {r['label']} scored 0")
        if s == 100:
            warnings.append(f"SUSPICIOUS: {r['label']} scored 100")
    if len(scores) >= 5:
        spread = max(scores) - min(scores)
        if spread < 5:
            warnings.append(f"SUSPICIOUS: all scores within {spread} points: {scores}")
    return warnings


def run_pytest_summary() -> str:
    cmds = [
        ["python3", "-m", "pytest", "--tb=no", "-q", "-rs"],
        ["python3", "-m", "pytest", "--tb=no", "-q", "-rs"],
    ]
    cwd_worker = os.path.join(ROOT, "apps", "worker")
    cwd_api = os.path.join(ROOT, "apps", "api")
    env = {**os.environ, "PYTHONPATH": os.path.join(ROOT, "apps", "api")}
    w = subprocess.run(cmds[0], cwd=cwd_worker, capture_output=True, text=True, env=env)
    a = subprocess.run(cmds[1], cwd=cwd_api, capture_output=True, text=True, env=env)
    combined = f"worker: {w.stdout.strip()}\napi: {a.stdout.strip()}"
    return combined


def run_429_proof() -> str:
    """Use fakeredis + TestClient for raw 429 HTTP response."""
    try:
        import fakeredis
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fakeredis", "-q"])
        import fakeredis

    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from agentworthy.main import app

    fake = fakeredis.FakeRedis(decode_responses=True)
    ip_hash = "gate1_test_ip_hash"
    from datetime import UTC, datetime
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"rate_limit:public_scan:{ip_hash}:{today}"
    fake.set(key, "3")

    with patch("agentworthy.redis_client.get_redis", return_value=fake):
        with patch("agentworthy.routes.public.hash_ip", return_value=ip_hash):
            with patch("agentworthy.routes.public.increment_rate_limit"):
                client = TestClient(app)
                resp = client.post("/public/scan", json={"url": "https://example.com"})
                lines = [
                    f"HTTP/1.1 {resp.status_code}",
                    *[f"{k}: {v}" for k, v in resp.headers.items()],
                    "",
                    resp.text,
                ]
                return "\n".join(lines)
    return ""


def run_llm_usage_proof() -> list[dict]:
    """Run 3 haiku classifications and return llm_usage rows."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return [{"error": "ANTHROPIC_API_KEY not set — cannot produce real llm_usage rows"}]

    db_url = os.environ.get("DATABASE_URL", "postgresql://agentworthy:agentworthy@localhost:5432/agentworthy")
    os.environ["DATABASE_URL"] = db_url

    try:
        from sqlalchemy import text
        from agentworthy.database import SessionLocal, engine
        from agentworthy.models import LLMUsage
        from agentworthy_worker.llm.client import classify_site_type

        # Ensure table exists
        from agentworthy.database import Base
        import agentworthy.models  # noqa: F401
        Base.metadata.create_all(bind=engine)

        scan_ids = [str(uuid.uuid4()) for _ in range(3)]
        samples = [
            ("Gymshark - Workout Clothes", "Shop fitness apparel and gym wear online."),
            ("Olive Garden Italian Restaurant", "Find a restaurant near you for pasta and dining."),
            ("Vercel - Develop. Preview. Ship.", "Deploy web applications with zero configuration."),
        ]
        for scan_id, (title, text_content) in zip(scan_ids, samples):
            classify_site_type(title, text_content, scan_id=scan_id)

        db = SessionLocal()
        rows = db.query(LLMUsage).order_by(LLMUsage.created_at.desc()).limit(3).all()
        return [
            {
                "id": str(r.id),
                "scan_id": str(r.scan_id) if r.scan_id else None,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
            }
            for r in rows
        ]
    except Exception as e:
        return [{"error": str(e)}]


def main() -> None:
    print("GATE 1 VALIDATION\n", file=sys.stderr)

    print("\n## 1. FULL SCAN JSON OUTPUT\n")
    scan_results = run_full_scans()
    warnings = analyze_scores(scan_results)
    if warnings:
        print("\n### DIAGNOSIS\n", file=sys.stderr)
        for w in warnings:
            print(w, file=sys.stderr)

    print("\n## 2. RAW HTTP 429 RESPONSE\n")
    print(run_429_proof())

    print("\n## 3. PYTEST SUMMARY\n")
    print(run_pytest_summary())

    print("\n## 4. LLM_USAGE ROWS\n")
    print(json.dumps(run_llm_usage_proof(), indent=2))


if __name__ == "__main__":
    main()
