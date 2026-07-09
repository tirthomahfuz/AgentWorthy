"""Check suite runner with per-check timeouts."""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from agentworthy.models import CheckCategory, CheckStatus

from agentworthy_worker.checks.actionability import (
    check_accessible_names,
    check_critical_widgets_accessible,
    check_cta_reachable,
    check_forms_semantic,
    check_no_blocking_interstitials,
)
from agentworthy_worker.checks.base import CHECK_DEFINITIONS, CheckResult
from agentworthy_worker.checks.context import CrawlContext
from agentworthy_worker.checks.discoverability import check_canonicals_clean, check_sitemap_present
from agentworthy_worker.checks.llms_txt_present import check_llms_txt_present
from agentworthy_worker.checks.machine_readability import (
    check_contact_machine_readable,
    check_prices_machine_readable,
    check_schema_correct_type,
    check_schema_present,
)
from agentworthy_worker.checks.performance import check_page_weight, check_pagination_exists, check_ttfb
from agentworthy_worker.checks.robots_agent_access import check_robots_agent_access
from agentworthy_worker.checks.ssr_content_ratio import check_ssr_content_ratio
from agentworthy_worker.checks.trust_freshness import (
    check_content_freshness,
    check_https_valid,
    check_nap_consistent,
)

logger = logging.getLogger(__name__)

CHECK_TIMEOUT_SECONDS = 10

CheckFn = Callable[[CrawlContext], CheckResult]

ALL_CHECKS: list[tuple[str, CheckFn]] = [
    ("robots_agent_access", check_robots_agent_access),
    ("llms_txt_present", check_llms_txt_present),
    ("sitemap_present", check_sitemap_present),
    ("canonicals_clean", check_canonicals_clean),
    ("ssr_content_ratio", check_ssr_content_ratio),
    ("schema_present", check_schema_present),
    ("schema_correct_type", check_schema_correct_type),
    ("prices_machine_readable", check_prices_machine_readable),
    ("contact_machine_readable", check_contact_machine_readable),
    ("forms_semantic", check_forms_semantic),
    ("cta_reachable", check_cta_reachable),
    ("no_blocking_interstitials", check_no_blocking_interstitials),
    ("critical_widgets_accessible", check_critical_widgets_accessible),
    ("accessible_names", check_accessible_names),
    ("https_valid", check_https_valid),
    ("content_freshness", check_content_freshness),
    ("nap_consistent", check_nap_consistent),
    ("ttfb", check_ttfb),
    ("page_weight", check_page_weight),
    ("pagination_exists", check_pagination_exists),
]


def _run_with_timeout(fn: CheckFn, ctx: CrawlContext, check_key: str) -> CheckResult:
    definition = CHECK_DEFINITIONS[check_key]
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn, ctx)
        try:
            return future.result(timeout=CHECK_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            return CheckResult(
                check_key=check_key,
                category=definition["category"],
                weight=definition["weight"],
                status=CheckStatus.WARN,
                evidence={"check timed out": True, "timeout_seconds": CHECK_TIMEOUT_SECONDS},
                plain_explanation=f"The {check_key} check timed out after {CHECK_TIMEOUT_SECONDS}s.",
            )
        except Exception as e:
            logger.exception("Check failed", extra={"check_key": check_key})
            return CheckResult(
                check_key=check_key,
                category=definition["category"],
                weight=definition["weight"],
                status=CheckStatus.WARN,
                evidence={"error": str(e)},
                plain_explanation=f"The {check_key} check encountered an error.",
            )


def run_all_checks(ctx: CrawlContext) -> list[CheckResult]:
    results: list[CheckResult] = []
    for check_key, fn in ALL_CHECKS:
        logger.info("Running check", extra={"check_key": check_key})
        results.append(_run_with_timeout(fn, ctx, check_key))
    return results


def calculate_score(results: list[CheckResult]) -> tuple[int, str]:
    """Score = 100 * (pass weights + 0.5 * warn weights) / applicable weights."""
    applicable = [r for r in results if r.status != CheckStatus.NOT_APPLICABLE]
    if not applicable:
        return 0, "F"

    pass_weight = sum(r.weight for r in applicable if r.status == CheckStatus.PASS)
    warn_weight = sum(r.weight for r in applicable if r.status == CheckStatus.WARN)
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


def category_breakdown(results: list[CheckResult]) -> dict[str, dict[str, int | float]]:
    breakdown: dict[str, dict[str, int | float]] = {}
    for cat in CheckCategory:
        cat_checks = [r for r in results if r.category == cat and r.status != CheckStatus.NOT_APPLICABLE]
        if not cat_checks:
            continue
        pass_w = sum(r.weight for r in cat_checks if r.status == CheckStatus.PASS)
        warn_w = sum(r.weight for r in cat_checks if r.status == CheckStatus.WARN)
        total_w = sum(r.weight for r in cat_checks)
        score = int(100 * (pass_w + 0.5 * warn_w) / total_w) if total_w else 0
        breakdown[cat.value] = {
            "score": score,
            "checks": len(cat_checks),
            "pass": sum(1 for r in cat_checks if r.status == CheckStatus.PASS),
            "warn": sum(1 for r in cat_checks if r.status == CheckStatus.WARN),
            "fail": sum(1 for r in cat_checks if r.status == CheckStatus.FAIL),
        }
    return breakdown
