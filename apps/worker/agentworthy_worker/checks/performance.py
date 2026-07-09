"""Performance checks for agents."""

import re
import time

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import CheckResult
from agentworthy_worker.checks.context import CrawlContext
from agentworthy_worker.checks.utils import make_soup

TTFB_THRESHOLD_MS = 1500
PAGE_WEIGHT_THRESHOLD_BYTES = 3 * 1024 * 1024


def check_ttfb(ctx: CrawlContext) -> CheckResult:
    weight = 5
    ttfb_ms = ctx.homepage_ttfb_ms

    if ttfb_ms is None:
        start = time.perf_counter()
        try:
            ctx.client.get(ctx.root_url, timeout=15.0)
            ttfb_ms = (time.perf_counter() - start) * 1000
        except Exception as e:
            return CheckResult(
                check_key="ttfb",
                category=CheckCategory.PERFORMANCE,
                weight=weight,
                status=CheckStatus.FAIL,
                evidence={"error": str(e)},
                plain_explanation="Could not measure time to first byte.",
            )

    if ttfb_ms <= TTFB_THRESHOLD_MS:
        return CheckResult(
            check_key="ttfb",
            category=CheckCategory.PERFORMANCE,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={"ttfb_ms": round(ttfb_ms, 1), "threshold_ms": TTFB_THRESHOLD_MS},
            plain_explanation=f"Time to first byte is {ttfb_ms:.0f}ms (under {TTFB_THRESHOLD_MS}ms).",
        )
    if ttfb_ms <= TTFB_THRESHOLD_MS * 2:
        return CheckResult(
            check_key="ttfb",
            category=CheckCategory.PERFORMANCE,
            weight=weight,
            status=CheckStatus.WARN,
            evidence={"ttfb_ms": round(ttfb_ms, 1), "threshold_ms": TTFB_THRESHOLD_MS},
            plain_explanation=f"TTFB is {ttfb_ms:.0f}ms, slower than the {TTFB_THRESHOLD_MS}ms target.",
        )
    return CheckResult(
        check_key="ttfb",
        category=CheckCategory.PERFORMANCE,
        weight=weight,
        status=CheckStatus.FAIL,
        evidence={"ttfb_ms": round(ttfb_ms, 1), "threshold_ms": TTFB_THRESHOLD_MS},
        plain_explanation=f"TTFB is {ttfb_ms:.0f}ms. Slow responses delay AI agent interactions.",
    )


def check_page_weight(ctx: CrawlContext) -> CheckResult:
    weight = 5
    size = ctx.homepage_weight_bytes

    if size is None:
        try:
            resp = ctx.client.get(ctx.root_url, timeout=15.0)
            size = len(resp.content)
        except Exception as e:
            return CheckResult(
                check_key="page_weight",
                category=CheckCategory.PERFORMANCE,
                weight=weight,
                status=CheckStatus.FAIL,
                evidence={"error": str(e)},
                plain_explanation="Could not measure homepage weight.",
            )

    size_mb = size / (1024 * 1024)
    if size <= PAGE_WEIGHT_THRESHOLD_BYTES:
        return CheckResult(
            check_key="page_weight",
            category=CheckCategory.PERFORMANCE,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={"bytes": size, "mb": round(size_mb, 2)},
            plain_explanation=f"Homepage weight is {size_mb:.1f}MB (under 3MB).",
        )
    return CheckResult(
        check_key="page_weight",
        category=CheckCategory.PERFORMANCE,
        weight=weight,
        status=CheckStatus.FAIL,
        evidence={"bytes": size, "mb": round(size_mb, 2)},
        plain_explanation=f"Homepage is {size_mb:.1f}MB. Heavy pages slow AI agent crawlers.",
    )


def check_pagination_exists(ctx: CrawlContext) -> CheckResult:
    weight = 5
    has_pagination = False
    has_infinite_scroll = False

    for url, html in ctx.pages.items():
        soup = make_soup(html)
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            text = a.get_text(strip=True).lower()
            if re.search(r"page=\d+|/page/\d+|p=\d+", href) or text in ("next", "2", "3", "older", "more"):
                has_pagination = True

        for el in soup.find_all(True):
            classes = " ".join(el.get("class", [])).lower()
            if any(k in classes for k in ("infinite-scroll", "infinite_scroll", "load-more", "loadmore")):
                has_infinite_scroll = True
            if el.get("data-infinite") or el.get("data-scroll-load"):
                has_infinite_scroll = True

    if has_pagination:
        return CheckResult(
            check_key="pagination_exists",
            category=CheckCategory.PERFORMANCE,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={"has_pagination": True},
            plain_explanation="Traditional pagination links found for navigating content.",
        )
    if has_infinite_scroll:
        return CheckResult(
            check_key="pagination_exists",
            category=CheckCategory.PERFORMANCE,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"infinite_scroll": True},
            plain_explanation=(
                "Infinite scroll detected without pagination links. "
                "AI agents may not reach content beyond the first viewport."
            ),
        )
    return CheckResult(
        check_key="pagination_exists",
        category=CheckCategory.PERFORMANCE,
        weight=weight,
        status=CheckStatus.PASS,
        evidence={},
        plain_explanation="No infinite-scroll-only pattern detected on crawled pages.",
    )
