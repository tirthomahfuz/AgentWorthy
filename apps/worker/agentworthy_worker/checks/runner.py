"""Check suite runner."""

import logging
from typing import Any

import httpx

from agentworthy_worker.checks.base import CHECK_DEFINITIONS, CheckResult
from agentworthy_worker.checks.llms_txt_present import check_llms_txt_present
from agentworthy_worker.checks.robots_agent_access import check_robots_agent_access
from agentworthy_worker.checks.ssr_content_ratio import check_ssr_content_ratio
from agentworthy_worker.checks.stubs import STUB_CHECKS, stub_check

logger = logging.getLogger(__name__)


def run_implemented_checks(
    root_url: str,
    client: httpx.Client,
    rendered_html: str | None = None,
) -> list[CheckResult]:
    results: list[CheckResult] = []

    logger.info("Running robots_agent_access check", extra={"url": root_url})
    results.append(check_robots_agent_access(root_url, client))

    logger.info("Running llms_txt_present check", extra={"url": root_url})
    results.append(check_llms_txt_present(root_url, client))

    logger.info("Running ssr_content_ratio check", extra={"url": root_url})
    results.append(check_ssr_content_ratio(root_url, client, rendered_html))

    for check_key in STUB_CHECKS:
        results.append(stub_check(check_key))

    return results


def calculate_score(results: list[CheckResult]) -> tuple[int, str]:
    """Score = 100 * (pass weights + 0.5 * warn weights) / applicable weights."""
    applicable = [r for r in results if r.status.value != "not_applicable"]
    if not applicable:
        return 0, "F"

    pass_weight = sum(r.weight for r in applicable if r.status.value == "pass")
    warn_weight = sum(r.weight for r in applicable if r.status.value == "warn")
    total_weight = sum(r.weight for r in applicable)

    score = int(100 * (pass_weight + 0.5 * warn_weight) / total_weight)

    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    return score, grade
