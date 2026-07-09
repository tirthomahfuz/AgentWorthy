#!/usr/bin/env python3
"""Run a full static scan against a URL without database (for completion gate proof)."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

import httpx
from agentworthy_worker.checks.runner import calculate_score, category_breakdown, run_all_checks
from agentworthy_worker.crawler import CRAWLER_USER_AGENT
from agentworthy_worker.scan_context import build_crawl_context


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: run_scan.py <url>")
        sys.exit(1)
    url = sys.argv[1]
    headers = {"User-Agent": CRAWLER_USER_AGENT}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
        ctx = build_crawl_context(client, url, max_pages=10)
        results = run_all_checks(ctx)
    score, grade = calculate_score(results)
    breakdown = category_breakdown(results)
    output = {
        "url": url,
        "overall_score": score,
        "letter_grade": grade,
        "site_type": ctx.site_type,
        "category_breakdown": breakdown,
        "checks": [
            {"key": r.check_key, "status": r.status.value, "category": r.category.value}
            for r in results
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
