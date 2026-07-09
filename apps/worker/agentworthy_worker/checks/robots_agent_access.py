"""robots_agent_access: robots.txt exists and does not block AI agent bots."""

from urllib.parse import urljoin, urlparse

import httpx
from urllib import robotparser

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import AGENT_BOTS, CheckResult


def check_robots_agent_access(root_url: str, client: httpx.Client) -> CheckResult:
    parsed = urlparse(root_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        response = client.get(robots_url, follow_redirects=True, timeout=10.0)
    except httpx.HTTPError as e:
        return CheckResult(
            check_key="robots_agent_access",
            category=CheckCategory.DISCOVERABILITY,
            weight=4,
            status=CheckStatus.FAIL,
            evidence={"robots_url": robots_url, "error": str(e)},
            plain_explanation=(
                "We could not fetch your robots.txt file. AI agents rely on robots.txt "
                "to know which pages they are allowed to visit."
            ),
        )

    if response.status_code == 404:
        return CheckResult(
            check_key="robots_agent_access",
            category=CheckCategory.DISCOVERABILITY,
            weight=4,
            status=CheckStatus.WARN,
            evidence={"robots_url": robots_url, "status_code": 404},
            plain_explanation=(
                "No robots.txt file was found. While not required, having one helps AI agents "
                "understand your crawling preferences. None of the major AI bots are explicitly blocked."
            ),
        )

    if response.status_code >= 400:
        return CheckResult(
            check_key="robots_agent_access",
            category=CheckCategory.DISCOVERABILITY,
            weight=4,
            status=CheckStatus.FAIL,
            evidence={"robots_url": robots_url, "status_code": response.status_code},
            plain_explanation=(
                f"robots.txt returned HTTP {response.status_code}, "
                "which may prevent agents from crawling."
            ),
        )

    robots_content = response.text
    rp = robotparser.RobotFileParser()
    rp.parse(robots_content.splitlines())

    blocked_bots: list[str] = []
    allowed_bots: list[str] = []

    for bot in AGENT_BOTS:
        test_url = urljoin(root_url, "/")
        if rp.can_fetch(bot, test_url):
            allowed_bots.append(bot)
        else:
            blocked_bots.append(bot)

    evidence = {
        "robots_url": robots_url,
        "robots_content_preview": robots_content[:500],
        "blocked_bots": blocked_bots,
        "allowed_bots": allowed_bots,
    }

    if blocked_bots:
        return CheckResult(
            check_key="robots_agent_access",
            category=CheckCategory.DISCOVERABILITY,
            weight=4,
            status=CheckStatus.FAIL,
            evidence=evidence,
            plain_explanation=(
                f"Your robots.txt blocks these AI agent crawlers: {', '.join(blocked_bots)}. "
                "This means ChatGPT, Claude, Perplexity, and Google's AI may not be able to "
                "read or interact with your site."
            ),
        )

    return CheckResult(
        check_key="robots_agent_access",
        category=CheckCategory.DISCOVERABILITY,
        weight=4,
        status=CheckStatus.PASS,
        evidence=evidence,
        plain_explanation=(
            "Your robots.txt allows all major AI agent crawlers "
            f"({', '.join(AGENT_BOTS)}) to access your site."
        ),
    )
