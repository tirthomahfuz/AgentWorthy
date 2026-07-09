"""Trust and freshness checks."""

import re
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import CheckResult
from agentworthy_worker.checks.context import CrawlContext
from agentworthy_worker.checks.utils import EMAIL_RE, extract_json_ld, extract_text, make_soup


def check_https_valid(ctx: CrawlContext) -> CheckResult:
    weight = 5
    parsed = urlparse(ctx.root_url)
    if parsed.scheme != "https":
        return CheckResult(
            check_key="https_valid",
            category=CheckCategory.TRUST_FRESHNESS,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"scheme": parsed.scheme},
            plain_explanation="Site is not served over HTTPS. AI agents and users expect secure connections.",
        )
    try:
        resp = ctx.client.get(ctx.root_url, timeout=10.0)
        return CheckResult(
            check_key="https_valid",
            category=CheckCategory.TRUST_FRESHNESS,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={"status_code": resp.status_code},
            plain_explanation="HTTPS is enabled with a valid certificate.",
        )
    except Exception as e:
        return CheckResult(
            check_key="https_valid",
            category=CheckCategory.TRUST_FRESHNESS,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"error": str(e)},
            plain_explanation="HTTPS certificate validation failed.",
        )


def check_content_freshness(ctx: CrawlContext) -> CheckResult:
    weight = 5
    cutoff = datetime.now(UTC) - timedelta(days=90)
    fresh_signals: list[str] = []
    stale_signals: list[str] = []

    try:
        resp = ctx.client.head(ctx.root_url, timeout=10.0, follow_redirects=True)
        lm = resp.headers.get("last-modified")
        if lm:
            try:
                dt = parsedate_to_datetime(lm)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                if dt >= cutoff:
                    fresh_signals.append(f"Last-Modified: {lm}")
                else:
                    stale_signals.append(f"Last-Modified: {lm}")
            except (TypeError, ValueError):
                pass
    except Exception:
        pass

    for url, html in ctx.pages.items():
        soup = make_soup(html)
        for meta in soup.find_all("meta"):
            prop = (meta.get("property") or meta.get("name") or "").lower()
            if prop in ("article:modified_time", "og:updated_time", "date", "last-modified"):
                content = meta.get("content", "")
                if _is_recent_date(content, cutoff):
                    fresh_signals.append(f"{prop} on {url}")
                else:
                    stale_signals.append(f"{prop} on {url}")

        text = extract_text(html)
        years = re.findall(r"\b(20\d{2})\b", text)
        current_year = datetime.now(UTC).year
        if any(int(y) >= current_year - 1 for y in years):
            fresh_signals.append(f"recent year mention on {url}")

    if fresh_signals:
        return CheckResult(
            check_key="content_freshness",
            category=CheckCategory.TRUST_FRESHNESS,
            weight=weight,
            status=CheckStatus.PASS,
            evidence={"signals": fresh_signals[:5]},
            plain_explanation="Fresh content signals detected within the last 90 days.",
        )
    if stale_signals:
        return CheckResult(
            check_key="content_freshness",
            category=CheckCategory.TRUST_FRESHNESS,
            weight=weight,
            status=CheckStatus.WARN,
            evidence={"stale": stale_signals[:5]},
            plain_explanation="Content may be stale. No recent update signals found.",
        )
    return CheckResult(
        check_key="content_freshness",
        category=CheckCategory.TRUST_FRESHNESS,
        weight=weight,
        status=CheckStatus.WARN,
        evidence={},
        plain_explanation="No freshness signals detected. Consider adding visible last-updated dates.",
    )


def check_nap_consistent(ctx: CrawlContext) -> CheckResult:
    weight = 5
    phones: set[str] = set()
    emails: set[str] = set()
    names: set[str] = set()

    for url, html in ctx.pages.items():
        blocks = extract_json_ld(html)
        for block in blocks:
            blob = str(block)
            if "telephone" in blob.lower():
                for m in re.findall(r'"telephone"\s*:\s*"([^"]+)"', blob, re.I):
                    phones.add(_normalize_phone(m))
            if "email" in blob.lower():
                for m in re.findall(r'"email"\s*:\s*"([^"]+)"', blob, re.I):
                    emails.add(m.lower())
            if block.get("name"):
                names.add(str(block["name"]).strip().lower())

        soup = make_soup(html)
        for a in soup.find_all("a", href=re.compile(r"^tel:")):
            phones.add(_normalize_phone(a["href"].replace("tel:", "")))
        for m in EMAIL_RE.findall(extract_text(html)):
            emails.add(m.lower())

    inconsistencies: list[str] = []
    if len(phones) > 1:
        inconsistencies.append(f"multiple phones: {phones}")
    if len(emails) > 2:
        inconsistencies.append(f"multiple emails: {emails}")
    if len(names) > 2:
        inconsistencies.append(f"multiple business names: {names}")

    if not phones and not emails and not names:
        return CheckResult(
            check_key="nap_consistent",
            category=CheckCategory.TRUST_FRESHNESS,
            weight=weight,
            status=CheckStatus.NOT_APPLICABLE,
            evidence={},
            plain_explanation="No NAP (name, address, phone) data found to compare.",
        )

    if inconsistencies:
        return CheckResult(
            check_key="nap_consistent",
            category=CheckCategory.TRUST_FRESHNESS,
            weight=weight,
            status=CheckStatus.FAIL,
            evidence={"issues": inconsistencies},
            plain_explanation="Inconsistent name, address, or phone across pages may confuse AI agents.",
        )

    return CheckResult(
        check_key="nap_consistent",
        category=CheckCategory.TRUST_FRESHNESS,
        weight=weight,
        status=CheckStatus.PASS,
        evidence={"phones": list(phones), "emails": list(emails)},
        plain_explanation="Name, address, and phone information is consistent across pages.",
    )


def _normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)[-10:]


def _is_recent_date(value: str, cutoff: datetime) -> bool:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(value[:19], fmt.replace("Z", ""))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt >= cutoff
        except ValueError:
            continue
    return False
