"""Fix generation via Sonnet — Stage 4."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from agentworthy_worker.checks.base import CheckResult, CheckStatus
from agentworthy_worker.llm.client import LLMClient
from agentworthy_worker.llm.config import SONNET_MODEL

logger = logging.getLogger(__name__)


def _parse_json_ld(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "@context" in data:
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data = json.loads(match.group())
            if "@context" in data:
                return data
        except json.JSONDecodeError:
            return None
    return None


def generate_fixes_for_category(
    category: str,
    checks: list[CheckResult],
    site_type: str,
    site_name: str,
    site_url: str,
    llm: LLMClient,
) -> dict[str, dict[str, str | None]]:
    """Batch generate fixes for fail/warn checks in a category."""
    needs_fix = [c for c in checks if c.status in (CheckStatus.FAIL, CheckStatus.WARN)]
    if not needs_fix:
        return {}

    prompt_checks = [
        {
            "check_key": c.check_key,
            "status": c.status.value,
            "evidence": c.evidence,
            "plain_explanation": c.plain_explanation,
        }
        for c in needs_fix
    ]
    system = (
        "Generate fixes for website audit checks. Return JSON object keyed by check_key. "
        "Each value: {plain_explanation, fix_code, fix_language, deploy_hint, fix_before, fix_after}. "
        "For schema/JSON-LD use fix_language=json-ld with valid JSON-LD using real site name/url; "
        "mark unknowns as TODO. deploy_hint is one plain sentence."
    )
    user = json.dumps({
        "category": category,
        "site_type": site_type,
        "site_name": site_name,
        "site_url": site_url,
        "checks": prompt_checks,
    })
    raw = llm.complete(SONNET_MODEL, system, user, max_tokens=4096)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        parsed = json.loads(match.group()) if match else {}

    results: dict[str, dict[str, str | None]] = {}
    for check in needs_fix:
        fix = parsed.get(check.check_key, {})
        if not isinstance(fix, dict):
            continue
        fix_code = fix.get("fix_code")
        fix_lang = fix.get("fix_language")
        if fix_lang == "json-ld" and fix_code:
            block = _parse_json_ld(fix_code)
            if not block:
                # one regeneration
                regen = llm.complete(
                    SONNET_MODEL,
                    "Return only valid JSON-LD.",
                    f"Fix this invalid JSON-LD for {site_name} at {site_url}:\n{fix_code}",
                    max_tokens=1024,
                )
                block = _parse_json_ld(regen)
                if not block:
                    results[check.check_key] = {
                        "plain_explanation": check.plain_explanation,
                        "fix_code": None,
                        "fix_language": None,
                        "deploy_hint": None,
                        "fix_before": None,
                        "fix_after": None,
                        "fix_unavailable": regen[:500],
                    }
                    continue
                fix_code = json.dumps(block, indent=2)
        results[check.check_key] = {
            "plain_explanation": fix.get("plain_explanation") or check.plain_explanation,
            "fix_code": fix_code,
            "fix_language": fix_lang,
            "deploy_hint": fix.get("deploy_hint"),
            "fix_before": fix.get("fix_before"),
            "fix_after": fix.get("fix_after"),
        }
    return results


def build_llms_txt(site_name: str, description: str, pages: list[dict[str, str]]) -> str:
    lines = [f"# {site_name}", "", description, ""]
    for p in pages[:20]:
        title = p.get("title", "Page")
        summary = p.get("summary", "")
        url = p.get("url", "")
        lines.append(f"- [{title}]({url}): {summary}")
    return "\n".join(lines) + "\n"
