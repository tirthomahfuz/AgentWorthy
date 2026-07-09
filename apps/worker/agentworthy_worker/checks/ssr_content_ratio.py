"""ssr_content_ratio: meaningful content in initial HTML without JS execution."""

import re
from html import unescape
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import CheckResult

SSR_RATIO_THRESHOLD = 0.30


def _extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def check_ssr_content_ratio(
    root_url: str,
    client: httpx.Client,
    rendered_html: str | None = None,
) -> CheckResult:
    """Compare raw HTTP response text vs rendered DOM text length."""
    try:
        response = client.get(root_url, follow_redirects=True, timeout=15.0)
        raw_html = response.text
    except httpx.HTTPError as e:
        return CheckResult(
            check_key="ssr_content_ratio",
            category=CheckCategory.MACHINE_READABILITY,
            weight=6,
            status=CheckStatus.FAIL,
            evidence={"url": root_url, "error": str(e)},
            plain_explanation=(
                "We could not fetch your homepage to check if content is visible without JavaScript."
            ),
        )

    raw_text = _extract_text_from_html(raw_html)
    raw_length = len(raw_text)

    if rendered_html is None:
        # Without Playwright render, use raw HTML as baseline and warn
        rendered_length = raw_length
        ratio = 1.0 if raw_length > 0 else 0.0
        used_playwright = False
    else:
        rendered_text = _extract_text_from_html(rendered_html)
        rendered_length = len(rendered_text)
        ratio = raw_length / rendered_length if rendered_length > 0 else 0.0
        used_playwright = True

    evidence = {
        "url": root_url,
        "raw_text_length": raw_length,
        "rendered_text_length": rendered_length,
        "ratio": round(ratio, 3),
        "threshold": SSR_RATIO_THRESHOLD,
        "raw_text_preview": raw_text[:300],
        "used_playwright": used_playwright,
    }

    if not used_playwright:
        if raw_length < 100:
            return CheckResult(
                check_key="ssr_content_ratio",
                category=CheckCategory.MACHINE_READABILITY,
                weight=6,
                status=CheckStatus.WARN,
                evidence=evidence,
                plain_explanation=(
                    "Very little text content was found in the initial HTML response. "
                    "If your site relies heavily on JavaScript to render content, "
                    "AI agents may struggle to read it."
                ),
            )
        return CheckResult(
            check_key="ssr_content_ratio",
            category=CheckCategory.MACHINE_READABILITY,
            weight=6,
            status=CheckStatus.PASS,
            evidence=evidence,
            plain_explanation=(
                f"Your homepage has {raw_length} characters of readable text in the initial HTML. "
                "Content appears to be available without JavaScript execution."
            ),
        )

    if ratio < SSR_RATIO_THRESHOLD:
        return CheckResult(
            check_key="ssr_content_ratio",
            category=CheckCategory.MACHINE_READABILITY,
            weight=6,
            status=CheckStatus.FAIL,
            evidence=evidence,
            plain_explanation=(
                f"Only {ratio:.0%} of your visible content is present in the initial HTML "
                f"(threshold is {SSR_RATIO_THRESHOLD:.0%}). AI agents that don't execute "
                "JavaScript will miss most of what visitors see."
            ),
        )

    if ratio < 0.5:
        return CheckResult(
            check_key="ssr_content_ratio",
            category=CheckCategory.MACHINE_READABILITY,
            weight=6,
            status=CheckStatus.WARN,
            evidence=evidence,
            plain_explanation=(
                f"About {ratio:.0%} of your content is in the initial HTML. "
                "Consider server-side rendering more content for better AI agent compatibility."
            ),
        )

    return CheckResult(
        check_key="ssr_content_ratio",
        category=CheckCategory.MACHINE_READABILITY,
        weight=6,
        status=CheckStatus.PASS,
        evidence=evidence,
        plain_explanation=(
            f"Your site has strong server-side content: {ratio:.0%} of visible text "
            "is available in the initial HTML without JavaScript."
        ),
    )
