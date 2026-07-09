"""Discoverability checks: sitemap_present, canonicals_clean."""

import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import CheckResult
from agentworthy_worker.checks.context import CrawlContext
from agentworthy_worker.checks.utils import find_canonicals, same_origin


def check_sitemap_present(ctx: CrawlContext) -> CheckResult:
    weight = 3
    parsed = urlparse(ctx.root_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    sitemap_urls: list[str] = []

    if ctx.robots_content:
        for line in ctx.robots_content.splitlines():
            if line.lower().startswith("sitemap:"):
                sitemap_urls.append(line.split(":", 1)[1].strip())

    if not sitemap_urls:
        sitemap_urls.append(f"{base}/sitemap.xml")

    found_url: str | None = None
    valid = False
    errors: list[str] = []

    for url in sitemap_urls:
        try:
            resp = ctx.client.get(url, timeout=10.0)
            if resp.status_code != 200:
                errors.append(f"{url}: HTTP {resp.status_code}")
                continue
            content = resp.text.strip()
            if "<urlset" in content or "<sitemapindex" in content:
                try:
                    ET.fromstring(content)
                    found_url = url
                    valid = True
                    break
                except ET.ParseError:
                    errors.append(f"{url}: invalid XML")
            else:
                errors.append(f"{url}: not a sitemap")
        except httpx.HTTPError as e:
            errors.append(f"{url}: {e}")

    if valid and found_url:
        referenced_in_robots = bool(
            ctx.robots_content
            and any(line.lower().startswith("sitemap:") for line in ctx.robots_content.splitlines())
        )
        status = CheckStatus.PASS if referenced_in_robots else CheckStatus.WARN
        explanation = (
            "Your XML sitemap is present and valid."
            if referenced_in_robots
            else "A valid sitemap exists but is not referenced in robots.txt. Add a Sitemap: line."
        )
        return CheckResult(
            check_key="sitemap_present",
            category=CheckCategory.DISCOVERABILITY,
            weight=weight,
            status=status,
            evidence={"sitemap_url": found_url, "referenced_in_robots": referenced_in_robots},
            plain_explanation=explanation,
        )

    return CheckResult(
        check_key="sitemap_present",
        category=CheckCategory.DISCOVERABILITY,
        weight=weight,
        status=CheckStatus.FAIL,
        evidence={"attempted_urls": sitemap_urls, "errors": errors},
        plain_explanation=(
            "No valid XML sitemap was found. AI agents use sitemaps to discover all your pages."
        ),
    )


def check_canonicals_clean(ctx: CrawlContext) -> CheckResult:
    weight = 4
    issues: list[dict[str, str]] = []
    canonical_map: dict[str, list[str]] = {}

    for page_url, html in ctx.pages.items():
        canonicals = find_canonicals(html, page_url)
        if len(canonicals) > 1:
            issues.append({"page": page_url, "issue": "multiple canonical tags", "canonicals": str(canonicals)})
        elif len(canonicals) == 1:
            canonical = canonicals[0]
            canonical_map.setdefault(canonical, []).append(page_url)
            parsed_page = urlparse(page_url)
            if parsed_page.query and canonical.rstrip("/") != page_url.rstrip("/").split("?")[0]:
                issues.append({"page": page_url, "issue": "query param page without self-referencing canonical"})

    for canonical, sources in canonical_map.items():
        if len(sources) > 1:
            issues.append({
                "canonical": canonical,
                "issue": "duplicate content trap",
                "pages": ", ".join(sources),
            })

    if issues:
        return CheckResult(
            check_key="canonicals_clean",
            category=CheckCategory.DISCOVERABILITY,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"issues": issues, "pages_checked": len(ctx.pages)},
            plain_explanation=(
                "Canonical tag issues may confuse AI agents about which URL is the authoritative page."
            ),
        )

    has_canonical = any(find_canonicals(html, url) for url, html in ctx.pages.items())
    if not has_canonical and len(ctx.pages) > 1:
        return CheckResult(
            check_key="canonicals_clean",
            category=CheckCategory.DISCOVERABILITY,
            weight=weight,
            status=CheckStatus.WARN,
            evidence={"pages_checked": len(ctx.pages)},
            plain_explanation="No canonical tags found across multiple pages. Consider adding them.",
        )

    return CheckResult(
        check_key="canonicals_clean",
        category=CheckCategory.DISCOVERABILITY,
        weight=weight,
        status=CheckStatus.PASS,
        evidence={"pages_checked": len(ctx.pages)},
        plain_explanation="Canonical tags are clean with no duplicate-content traps detected.",
    )
