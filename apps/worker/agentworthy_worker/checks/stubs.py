"""Stub checks for Phase 1 skeleton — return not_applicable until implemented."""

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import CHECK_DEFINITIONS, CheckResult


def stub_check(check_key: str) -> CheckResult:
    definition = CHECK_DEFINITIONS[check_key]
    return CheckResult(
        check_key=check_key,
        category=definition["category"],
        weight=definition["weight"],
        status=CheckStatus.NOT_APPLICABLE,
        evidence={"note": "Check not yet implemented in Phase 1"},
        plain_explanation="This check will be evaluated in a future release.",
    )


STUB_CHECKS = [key for key in CHECK_DEFINITIONS if key not in {
    "robots_agent_access",
    "llms_txt_present",
    "ssr_content_ratio",
}]
