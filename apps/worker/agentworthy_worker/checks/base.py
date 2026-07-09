"""Check result dataclass used by the static scan engine."""

from dataclasses import dataclass, field
from typing import Any

from agentworthy.models import CheckCategory, CheckStatus


@dataclass
class CheckResult:
    check_key: str
    category: CheckCategory
    weight: int
    status: CheckStatus
    evidence: dict[str, Any] = field(default_factory=dict)
    plain_explanation: str = ""
    fix_code: str | None = None
    fix_language: str | None = None


# Agent user agents that must not be blocked
AGENT_BOTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended"]

# Check registry with weights from spec
CHECK_DEFINITIONS: dict[str, dict[str, Any]] = {
    # A. Discoverability (15 total)
    "robots_agent_access": {"category": CheckCategory.DISCOVERABILITY, "weight": 4},
    "llms_txt_present": {"category": CheckCategory.DISCOVERABILITY, "weight": 4},
    "sitemap_present": {"category": CheckCategory.DISCOVERABILITY, "weight": 3},
    "canonicals_clean": {"category": CheckCategory.DISCOVERABILITY, "weight": 4},
    # B. Machine readability (25 total)
    "ssr_content_ratio": {"category": CheckCategory.MACHINE_READABILITY, "weight": 6},
    "schema_present": {"category": CheckCategory.MACHINE_READABILITY, "weight": 5},
    "schema_correct_type": {"category": CheckCategory.MACHINE_READABILITY, "weight": 5},
    "prices_machine_readable": {"category": CheckCategory.MACHINE_READABILITY, "weight": 4},
    "contact_machine_readable": {"category": CheckCategory.MACHINE_READABILITY, "weight": 5},
    # C. Actionability (30 total)
    "forms_semantic": {"category": CheckCategory.ACTIONABILITY, "weight": 6},
    "cta_reachable": {"category": CheckCategory.ACTIONABILITY, "weight": 5},
    "no_blocking_interstitials": {"category": CheckCategory.ACTIONABILITY, "weight": 5},
    "critical_widgets_accessible": {"category": CheckCategory.ACTIONABILITY, "weight": 6},
    "accessible_names": {"category": CheckCategory.ACTIONABILITY, "weight": 8},
    # D. Trust and freshness (15 total)
    "https_valid": {"category": CheckCategory.TRUST_FRESHNESS, "weight": 5},
    "content_freshness": {"category": CheckCategory.TRUST_FRESHNESS, "weight": 5},
    "nap_consistent": {"category": CheckCategory.TRUST_FRESHNESS, "weight": 5},
    # E. Performance (15 total)
    "ttfb": {"category": CheckCategory.PERFORMANCE, "weight": 5},
    "page_weight": {"category": CheckCategory.PERFORMANCE, "weight": 5},
    "pagination_exists": {"category": CheckCategory.PERFORMANCE, "weight": 5},
}
