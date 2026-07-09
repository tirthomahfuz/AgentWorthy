"""Machine readability checks."""

import json
import re
from typing import Any

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import CheckResult
from agentworthy_worker.checks.context import CrawlContext
from agentworthy_worker.checks.utils import (
    EMAIL_RE,
    extract_json_ld,
    extract_text,
    make_soup,
    schema_types,
)
from agentworthy_worker.llm.client import classify_site_type


def check_schema_present(ctx: CrawlContext) -> CheckResult:
    weight = 5
    html = ctx.homepage_html
    if not html:
        return _fail("schema_present", weight, "No homepage HTML to analyze.")

    blocks = extract_json_ld(html)
    if blocks:
        return CheckResult(
            check_key="schema_present",
            category=CheckCategory.MACHINE_READABILITY,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={"types": list(schema_types(blocks)), "block_count": len(blocks)},
            plain_explanation="Valid JSON-LD structured data was found on your homepage.",
        )
    return CheckResult(
        check_key="schema_present",
        category=CheckCategory.MACHINE_READABILITY,
        weight=weight,
        status=CheckStatus.FAIL,
        evidence={"types": []},
        plain_explanation=(
            "No JSON-LD structured data found. AI agents rely on schema.org markup "
            "to understand your business, products, and services."
        ),
    )


def check_schema_correct_type(ctx: CrawlContext) -> CheckResult:
    weight = 5
    html = ctx.homepage_html
    if not html:
        return _fail("schema_correct_type", weight, "No homepage HTML to analyze.")

    site_type = ctx.site_type or classify_site_type(
        _page_title(html), extract_text(html)[:3000], scan_id=ctx.scan_id
    )
    blocks = extract_json_ld(html)
    types = schema_types(blocks)

    expected = _expected_types(site_type)
    matched = types & expected

    if matched:
        return CheckResult(
            check_key="schema_correct_type",
            category=CheckCategory.MACHINE_READABILITY,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={"site_type": site_type, "found_types": list(types), "matched": list(matched)},
            plain_explanation=f"Schema type matches detected business type ({site_type}).",
        )

    if types:
        return CheckResult(
            check_key="schema_correct_type",
            category=CheckCategory.MACHINE_READABILITY,
            weight=weight,
            status=CheckStatus.WARN,
            evidence={"site_type": site_type, "found_types": list(types), "expected": list(expected)},
            plain_explanation=(
                f"Structured data found but may not match your business type ({site_type}). "
                f"Expected types like {', '.join(expected)}."
            ),
        )

    return CheckResult(
        check_key="schema_correct_type",
        category=CheckCategory.MACHINE_READABILITY,
        weight=weight,
        status=CheckStatus.FAIL,
        evidence={"site_type": site_type, "expected": list(expected)},
        plain_explanation=f"No schema markup matching your {site_type} business type was found.",
    )


def check_prices_machine_readable(ctx: CrawlContext) -> CheckResult:
    weight = 4
    price_patterns: list[str] = []
    image_only = True

    for url, html in ctx.pages.items():
        blocks = extract_json_ld(html)
        for block in blocks:
            if _has_schema_price(block):
                price_patterns.append(f"json-ld on {url}")
                image_only = False

        soup = make_soup(html)
        for el in soup.find_all(string=re.compile(r"\$\d+|\d+\.\d{2}\s*(USD|EUR|GBP)?")):
            if el.parent and el.parent.name != "img":
                price_patterns.append(f"text on {url}")
                image_only = False

        for img in soup.find_all("img", alt=re.compile(r"\$\d+")):
            price_patterns.append(f"image alt on {url}")

    if image_only and price_patterns:
        return CheckResult(
            check_key="prices_machine_readable",
            category=CheckCategory.MACHINE_READABILITY,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"sources": price_patterns},
            plain_explanation="Prices appear only in images, not in machine-readable text or schema.",
        )

    if not image_only:
        return CheckResult(
            check_key="prices_machine_readable",
            category=CheckCategory.MACHINE_READABILITY,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={"sources": price_patterns[:5]},
            plain_explanation="Prices are available in machine-readable form.",
        )

    return CheckResult(
        check_key="prices_machine_readable",
        category=CheckCategory.MACHINE_READABILITY,
        weight=weight,
        status=CheckStatus.WARN,
        evidence={},
        plain_explanation="No prices detected. If you display pricing, ensure it is in text or schema markup.",
    )


def check_contact_machine_readable(ctx: CrawlContext) -> CheckResult:
    weight = 5
    structured_contacts: list[str] = []
    semantic_contacts: list[str] = []
    image_only: list[str] = []

    for url, html in ctx.pages.items():
        blocks = extract_json_ld(html)
        for block in blocks:
            if any(k in json.dumps(block).lower() for k in ("telephone", "email", "address")):
                structured_contacts.append(url)

        soup = make_soup(html)
        if soup.find("a", href=re.compile(r"^mailto:")):
            semantic_contacts.append(f"mailto on {url}")
        if soup.find("a", href=re.compile(r"^tel:")):
            semantic_contacts.append(f"tel on {url}")
        if soup.find("address"):
            semantic_contacts.append(f"address tag on {url}")

        text = extract_text(html)
        if EMAIL_RE.search(text) and not soup.find("a", href=re.compile(r"^mailto:")):
            semantic_contacts.append(f"email text on {url}")

        for img in soup.find_all("img", alt=re.compile(r"@|phone|call|\d{3}")):
            if not structured_contacts and not semantic_contacts:
                image_only.append(url)

    if structured_contacts or semantic_contacts:
        return CheckResult(
            check_key="contact_machine_readable",
            category=CheckCategory.MACHINE_READABILITY,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={
                "structured": structured_contacts[:3],
                "semantic": semantic_contacts[:5],
            },
            plain_explanation="Contact information is available in structured data or semantic HTML.",
        )

    if image_only:
        return CheckResult(
            check_key="contact_machine_readable",
            category=CheckCategory.MACHINE_READABILITY,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"image_only_pages": image_only},
            plain_explanation="Contact info appears to be in images only, not machine-readable.",
        )

    return CheckResult(
        check_key="contact_machine_readable",
        category=CheckCategory.MACHINE_READABILITY,
        weight=weight,
        status=CheckStatus.WARN,
        evidence={},
        plain_explanation="No contact information detected in structured or semantic form.",
    )


def _page_title(html: str) -> str:
    soup = make_soup(html)
    title = soup.find("title")
    return title.get_text(strip=True) if title else ""


def _expected_types(site_type: str) -> set[str]:
    mapping = {
        "ecommerce": {"Product", "Offer", "ItemList"},
        "restaurant": {"Restaurant", "FoodEstablishment", "Menu"},
        "local": {"LocalBusiness", "Store"},
        "saas": {"SoftwareApplication", "Service", "Product"},
        "lead-gen": {"Service", "LocalBusiness", "Organization"},
    }
    return mapping.get(site_type, {"Organization", "LocalBusiness", "WebSite"})


def _has_schema_price(block: dict[str, Any]) -> bool:
    blob = json.dumps(block).lower()
    return "price" in blob or "offers" in blob


def _fail(key: str, weight: int, msg: str) -> CheckResult:
    return CheckResult(
        check_key=key,
        category=CheckCategory.MACHINE_READABILITY,
        weight=weight,
        status=CheckStatus.FAIL,
        evidence={},
        plain_explanation=msg,
    )
