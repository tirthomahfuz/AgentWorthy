"""Actionability checks."""

import re
from collections import deque

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import CheckResult
from agentworthy_worker.checks.context import CrawlContext
from agentworthy_worker.checks.utils import make_soup
from agentworthy_worker.crawler import extract_links, normalize_url

CTA_KEYWORDS = re.compile(
    r"\b(buy|shop|order|book|reserve|sign up|signup|get started|contact|subscribe|add to cart|checkout|try free|demo)\b",
    re.I,
)


def check_forms_semantic(ctx: CrawlContext) -> CheckResult:
    weight = 6
    issues: list[dict[str, str]] = []
    good_forms = 0

    for url, html in ctx.pages.items():
        soup = make_soup(html)
        for form in soup.find_all("form"):
            inputs = form.find_all(["input", "textarea", "select"])
            if not inputs:
                continue
            bad = False
            for inp in inputs:
                if inp.name == "input" and inp.get("type") in ("hidden", "submit", "button"):
                    continue
                if inp.name in ("canvas",) or inp.get("role") == "textbox" and inp.name == "div":
                    issues.append({"page": url, "issue": "non-native input"})
                    bad = True
                label = inp.get("aria-label") or inp.get("aria-labelledby")
                if not label:
                    lid = inp.get("id")
                    if lid and form.find("label", attrs={"for": lid}):
                        label = "ok"
                if not label and not inp.get("name"):
                    issues.append({"page": url, "issue": "unlabeled input without name"})
                    bad = True
            if not bad:
                good_forms += 1

    if issues and good_forms == 0:
        return CheckResult(
            check_key="forms_semantic",
            category=CheckCategory.ACTIONABILITY,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"issues": issues[:10]},
            plain_explanation=(
                "Forms use non-semantic or unlabeled inputs that AI agents cannot reliably fill."
            ),
        )
    if issues:
        return CheckResult(
            check_key="forms_semantic",
            category=CheckCategory.ACTIONABILITY,
            weight=weight,
            status=CheckStatus.WARN,
            evidence={"issues": issues[:10], "good_forms": good_forms},
            plain_explanation="Some forms have accessibility issues for AI agents.",
        )
    if good_forms > 0:
        return CheckResult(
            check_key="forms_semantic",
            category=CheckCategory.ACTIONABILITY,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={"good_forms": good_forms},
            plain_explanation="Forms use semantic inputs with labels and name attributes.",
        )
    return CheckResult(
        check_key="forms_semantic",
        category=CheckCategory.ACTIONABILITY,
        weight=weight,
        status=CheckStatus.NOT_APPLICABLE,
        evidence={},
        plain_explanation="No forms found on crawled pages.",
    )


def check_cta_reachable(ctx: CrawlContext) -> CheckResult:
    weight = 5
    root = normalize_url(ctx.root_url)
    visited: set[str] = {root}
    queue: deque[tuple[str, int]] = deque([(root, 0)])
    cta_found: list[dict[str, str]] = []

    pages = {normalize_url(k): v for k, v in ctx.pages.items()}
    while queue:
        url, depth = queue.popleft()
        html = pages.get(url)
        if not html:
            continue
        soup = make_soup(html)
        for el in soup.find_all(["a", "button"]):
            text = el.get_text(strip=True)
            aria = el.get("aria-label", "")
            if CTA_KEYWORDS.search(text) or CTA_KEYWORDS.search(aria):
                if el.name in ("a", "button"):
                    cta_found.append({"page": url, "depth": str(depth), "text": text or aria})
        if depth < 2:
            for link in extract_links(html, url):
                if link not in visited and link in pages:
                    visited.add(link)
                    queue.append((link, depth + 1))

    within_two = [c for c in cta_found if int(c["depth"]) <= 2]
    if within_two:
        return CheckResult(
            check_key="cta_reachable",
            category=CheckCategory.ACTIONABILITY,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={"ctas": within_two[:5]},
            plain_explanation="Primary call-to-action is reachable within 2 clicks of the homepage.",
        )
    if cta_found:
        return CheckResult(
            check_key="cta_reachable",
            category=CheckCategory.ACTIONABILITY,
            weight=weight,
            status=CheckStatus.WARN,
            evidence={"ctas": cta_found[:5]},
            plain_explanation="CTAs exist but may require more than 2 clicks from the homepage.",
        )
    return CheckResult(
        check_key="cta_reachable",
        category=CheckCategory.ACTIONABILITY,
        weight=weight,
        status=CheckStatus.FAIL,
        evidence={},
        plain_explanation="No clear call-to-action button or link found within 2 clicks of the homepage.",
    )


def check_no_blocking_interstitials(ctx: CrawlContext) -> CheckResult:
    weight = 5
    html = ctx.rendered_homepage_html or ctx.homepage_html
    if not html:
        return _fail("no_blocking_interstitials", weight, "No homepage content to analyze.")

    soup = make_soup(html)
    blockers: list[str] = []

    for el in soup.find_all(True):
        style = el.get("style", "")
        classes = " ".join(el.get("class", []))
        el_id = el.get("id", "")
        combined = f"{style} {classes} {el_id}".lower()
        if any(k in combined for k in ("modal", "overlay", "interstitial", "popup", "newsletter")):
            if el.name in ("div", "section") and (
                "fixed" in style.lower() or "modal" in combined
            ):
                blockers.append(f"{el.name}#{el_id or classes[:30]}")

    for el in soup.find_all(attrs={"role": "dialog"}):
        blockers.append("role=dialog")

    if blockers:
        return CheckResult(
            check_key="no_blocking_interstitials",
            category=CheckCategory.ACTIONABILITY,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"blockers": blockers[:5]},
            plain_explanation=(
                "Blocking interstitials (modals, popups) detected that may prevent AI agents "
                "from reaching your content."
            ),
        )
    return CheckResult(
        check_key="no_blocking_interstitials",
        category=CheckCategory.ACTIONABILITY,
        weight=weight,
        status=CheckStatus.PASS,
        evidence={},
        plain_explanation="No blocking interstitials detected on the homepage.",
    )


def check_critical_widgets_accessible(ctx: CrawlContext) -> CheckResult:
    weight = 6
    issues: list[str] = []

    for url, html in ctx.pages.items():
        soup = make_soup(html)
        canvases = soup.find_all("canvas")
        date_widgets = soup.find_all(attrs={"class": re.compile(r"datepicker|date-picker", re.I)})
        native_date = soup.find_all("input", attrs={"type": "date"})
        native_qty = soup.find_all("input", attrs={"type": re.compile(r"number|range")})

        if canvases and not native_date:
            issues.append(f"canvas widget without date fallback on {url}")
        if date_widgets and not native_date:
            issues.append(f"custom date picker without native input on {url}")
        for canvas in canvases:
            if canvas.get("role") not in ("img", "presentation", None):
                issues.append(f"interactive canvas on {url}")

    if issues:
        return CheckResult(
            check_key="critical_widgets_accessible",
            category=CheckCategory.ACTIONABILITY,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"issues": issues[:10]},
            plain_explanation=(
                "Critical widgets (date pickers, quantity selectors) lack accessible fallbacks."
            ),
        )
    return CheckResult(
        check_key="critical_widgets_accessible",
        category=CheckCategory.ACTIONABILITY,
        weight=weight,
        status=CheckStatus.PASS,
        evidence={},
        plain_explanation="No inaccessible custom widgets detected for critical interactions.",
    )


def check_accessible_names(ctx: CrawlContext) -> CheckResult:
    weight = 8
    unnamed: list[dict[str, str]] = []
    named = 0

    for url, html in ctx.pages.items():
        soup = make_soup(html)
        for el in soup.find_all(["a", "button"]):
            text = el.get_text(strip=True)
            aria = el.get("aria-label") or el.get("title") or ""
            if not text and not aria:
                unnamed.append({"page": url, "tag": el.name})
            else:
                named += 1

    if unnamed and named == 0:
        return CheckResult(
            check_key="accessible_names",
            category=CheckCategory.ACTIONABILITY,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"unnamed": unnamed[:10]},
            plain_explanation="Buttons and links lack accessible names. AI agents navigate by accessibility tree.",
        )
    if unnamed:
        ratio = len(unnamed) / (len(unnamed) + named)
        status = CheckStatus.WARN if ratio < 0.3 else CheckStatus.FAIL
        return CheckResult(
            check_key="accessible_names",
            category=CheckCategory.ACTIONABILITY,
            weight=weight,
            status=status,
            evidence={"unnamed_count": len(unnamed), "named_count": named},
            plain_explanation=f"{len(unnamed)} buttons/links lack accessible names.",
        )
    return CheckResult(
        check_key="accessible_names",
        category=CheckCategory.ACTIONABILITY,
        weight=weight,
        status=CheckStatus.PASS,
        evidence={"named_count": named},
        plain_explanation="Buttons and links have accessible names for AI agent navigation.",
    )


def _fail(key: str, weight: int, msg: str) -> CheckResult:
    return CheckResult(
        check_key=key,
        category=CheckCategory.ACTIONABILITY,
        weight=weight,
        status=CheckStatus.FAIL,
        evidence={},
        plain_explanation=msg,
    )