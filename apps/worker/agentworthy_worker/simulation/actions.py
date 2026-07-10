"""Execute simulation tool actions against Playwright page."""

from __future__ import annotations

import time
from typing import Any

from agentworthy_worker.simulation.a11y_tree import build_tree_from_page
from agentworthy_worker.simulation.safety import (
    FAKE_IDENTITY,
    form_submission_allowed,
    is_destructive_action,
    is_payment_field,
    navigation_allowed,
)


class ActionError(Exception):
    pass


def _resolve_ref(page: Any, tree: list[dict[str, Any]], ref: str) -> Any:
    for node in tree:
        if node["ref"] == ref:
            role = node["role"]
            name = node["name"]
            locator = page.get_by_role(role, name=name) if name else page.get_by_role(role)
            if locator.count() == 0:
                raise ActionError(f"Ref {ref} not found on page")
            return locator.first
    raise ActionError(f"Unknown ref: {ref}")


def execute_action(
    page: Any,
    tree: list[dict[str, Any]],
    action: dict[str, Any],
    task: str,
    root_domain: str,
    page_origin: str,
) -> tuple[str, str | None]:
    """Returns (action_name, error_note or None)."""
    name = action.get("action")
    if name == "click":
        ref = action.get("ref", "")
        node = next((n for n in tree if n["ref"] == ref), None)
        if node and is_destructive_action(node.get("name", ""), task):
            return "click", "blocked_destructive"
        el = _resolve_ref(page, tree, ref)
        el.click(timeout=10_000)
        page.wait_for_load_state("networkidle", timeout=3000)
        return "click", None
    if name == "type":
        ref = action.get("ref", "")
        text = action.get("text", "")
        el = _resolve_ref(page, tree, ref)
        el.fill(text, timeout=10_000)
        return "type", None
    if name == "select":
        ref = action.get("ref", "")
        value = action.get("value", "")
        el = _resolve_ref(page, tree, ref)
        el.select_option(value, timeout=10_000)
        return "select", None
    if name == "navigate":
        url = action.get("url", "")
        allowed, reason = navigation_allowed(url, root_domain)
        if not allowed:
            return "navigate", "blocked_off_domain"
        page.goto(url, timeout=10_000, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=3000)
        return "navigate", reason
    if name == "scroll":
        direction = action.get("direction", "down")
        delta = 600 if direction == "down" else -600
        page.mouse.wheel(0, delta)
        time.sleep(0.3)
        return "scroll", None
    if name in ("extract", "give_up"):
        return name, None
    raise ActionError(f"Unknown action: {name}")


def check_payment_gate(page: Any) -> bool:
    """Return True if a payment field is focused or imminent."""
    focused = page.evaluate("""() => {
        const el = document.activeElement;
        if (!el) return null;
        return {
            autocomplete: el.getAttribute('autocomplete') || '',
            name: el.getAttribute('name') || '',
            id: el.getAttribute('id') || '',
            placeholder: el.getAttribute('placeholder') || '',
            ariaLabel: el.getAttribute('aria-label') || '',
        };
    }""")
    if focused and is_payment_field(focused):
        return True
    return False
