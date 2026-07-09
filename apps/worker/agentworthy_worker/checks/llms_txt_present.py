"""llms_txt_present: llms.txt file at site root."""

from urllib.parse import urlparse

import httpx

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import CheckResult


def check_llms_txt_present(root_url: str, client: httpx.Client) -> CheckResult:
    parsed = urlparse(root_url)
    llms_url = f"{parsed.scheme}://{parsed.netloc}/llms.txt"

    try:
        response = client.get(llms_url, follow_redirects=True, timeout=10.0)
    except httpx.HTTPError as e:
        return CheckResult(
            check_key="llms_txt_present",
            category=CheckCategory.DISCOVERABILITY,
            weight=4,
            status=CheckStatus.FAIL,
            evidence={"llms_url": llms_url, "error": str(e)},
            plain_explanation=(
                "We could not check for llms.txt. This file helps AI agents quickly understand "
                "your site's purpose, key pages, and how to interact with it."
            ),
        )

    if response.status_code == 404:
        return CheckResult(
            check_key="llms_txt_present",
            category=CheckCategory.DISCOVERABILITY,
            weight=4,
            status=CheckStatus.FAIL,
            evidence={"llms_url": llms_url, "status_code": 404},
            plain_explanation=(
                "No llms.txt file was found at your site root. AI agents like ChatGPT and Claude "
                "use this file to quickly understand what your business does and which pages matter most."
            ),
        )

    if response.status_code >= 400:
        return CheckResult(
            check_key="llms_txt_present",
            category=CheckCategory.DISCOVERABILITY,
            weight=4,
            status=CheckStatus.FAIL,
            evidence={"llms_url": llms_url, "status_code": response.status_code},
            plain_explanation=f"llms.txt returned HTTP {response.status_code}.",
        )

    content = response.text.strip()
    if len(content) < 20:
        return CheckResult(
            check_key="llms_txt_present",
            category=CheckCategory.DISCOVERABILITY,
            weight=4,
            status=CheckStatus.WARN,
            evidence={"llms_url": llms_url, "content_preview": content},
            plain_explanation=(
                "An llms.txt file exists but appears very short. Consider adding a description "
                "of your business, key page links, and contact information."
            ),
        )

    return CheckResult(
        check_key="llms_txt_present",
        category=CheckCategory.DISCOVERABILITY,
        weight=4,
        status=CheckStatus.PASS,
        evidence={"llms_url": llms_url, "content_preview": content[:500], "content_length": len(content)},
        plain_explanation=(
            "Your site has an llms.txt file that helps AI agents understand your business "
            "and find important pages quickly."
        ),
    )
