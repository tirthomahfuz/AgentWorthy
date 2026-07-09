"""ssr_content_ratio: meaningful content in initial HTML without JS execution."""

import re
from html import unescape

import httpx

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import CheckResult
from agentworthy_worker.checks.context import CrawlContext
from agentworthy_worker.checks.utils import extract_text

SSR_RATIO_THRESHOLD = 0.30
MAX_REDIRECTS = 5


def check_ssr_content_ratio(ctx: CrawlContext) -> CheckResult:
    root_url = ctx.root_url
    client = ctx.client
    rendered_html = ctx.rendered_homepage_html

    try:
        response = _fetch_with_redirect_limit(client, root_url)
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            return CheckResult(
                check_key="ssr_content_ratio",
                category=CheckCategory.MACHINE_READABILITY,
                weight=6,
                status=CheckStatus.WARN,
                evidence={"content_type": content_type},
                plain_explanation="Homepage response is not HTML.",
            )
        raw_html = response.text
    except httpx.HTTPError as e:
        return CheckResult(
            check_key="ssr_content_ratio",
            category=CheckCategory.MACHINE_READABILITY,
            weight=6,
            status=CheckStatus.FAIL,
            evidence={"url": root_url, "error": str(e)},
            plain_explanation="Could not fetch homepage to check SSR content.",
        )

    raw_text = extract_text(raw_html)
    raw_length = len(raw_text)

    if ctx.render_blocked:
        return CheckResult(
            check_key="ssr_content_ratio",
            category=CheckCategory.MACHINE_READABILITY,
            weight=6,
            status=CheckStatus.WARN,
            evidence={
                "raw_text_length": raw_length,
                "rendered_fetch_blocked": True,
            },
            plain_explanation=(
                "Headless browser rendering was blocked. Falling back to raw HTML analysis only."
            ),
        )

    if rendered_html is None:
        if raw_length < 100:
            return CheckResult(
                check_key="ssr_content_ratio",
                category=CheckCategory.MACHINE_READABILITY,
                weight=6,
                status=CheckStatus.WARN,
                evidence={"raw_text_length": raw_length},
                plain_explanation="Very little text in initial HTML. Site may rely on JavaScript.",
            )
        return CheckResult(
            check_key="ssr_content_ratio",
            category=CheckCategory.MACHINE_READABILITY,
            weight=6,
            status=CheckStatus.PASS,
            evidence={"raw_text_length": raw_length},
            plain_explanation=f"Homepage has {raw_length} characters of readable text in initial HTML.",
        )

    rendered_text = extract_text(rendered_html)
    rendered_length = len(rendered_text)
    ratio = raw_length / rendered_length if rendered_length > 0 else 0.0

    evidence = {
        "url": root_url,
        "raw_text_length": raw_length,
        "rendered_text_length": rendered_length,
        "ratio": round(ratio, 3),
        "threshold": SSR_RATIO_THRESHOLD,
    }

    if ratio < SSR_RATIO_THRESHOLD:
        return CheckResult(
            check_key="ssr_content_ratio",
            category=CheckCategory.MACHINE_READABILITY,
            weight=6,
            status=CheckStatus.FAIL,
            evidence=evidence,
            plain_explanation=(
                f"Only {ratio:.0%} of visible content is in initial HTML "
                f"(threshold {SSR_RATIO_THRESHOLD:.0%})."
            ),
        )
    if ratio < 0.5:
        return CheckResult(
            check_key="ssr_content_ratio",
            category=CheckCategory.MACHINE_READABILITY,
            weight=6,
            status=CheckStatus.WARN,
            evidence=evidence,
            plain_explanation=f"About {ratio:.0%} of content is in initial HTML.",
        )
    return CheckResult(
        check_key="ssr_content_ratio",
        category=CheckCategory.MACHINE_READABILITY,
        weight=6,
        status=CheckStatus.PASS,
        evidence=evidence,
        plain_explanation=f"Strong SSR content: {ratio:.0%} available without JavaScript.",
    )


def _fetch_with_redirect_limit(client: httpx.Client, url: str) -> httpx.Response:
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        response = client.get(current, follow_redirects=False, timeout=15.0)
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if not location:
                return response
            current = location
            continue
        return response
    raise httpx.TooManyRedirects("Exceeded 5 redirects", request=None)  # type: ignore[arg-type]
