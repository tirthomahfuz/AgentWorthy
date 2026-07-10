"""Prune accessibility tree to interactive and landmark nodes with stable refs."""

from __future__ import annotations

from typing import Any

INTERACTIVE_ROLES = {
    "button", "link", "textbox", "checkbox", "radio", "combobox",
    "listbox", "menuitem", "tab", "searchbox", "switch", "spinbutton",
}
LANDMARK_ROLES = {"main", "navigation", "banner", "contentinfo", "form", "search"}


def prune_a11y_tree(raw_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign ref ids and return pruned flat list."""
    out: list[dict[str, Any]] = []
    counter = 0

    def walk(nodes: list[dict[str, Any]]) -> None:
        nonlocal counter
        for node in nodes:
            role = (node.get("role") or "").lower()
            name = (node.get("name") or "").strip()
            if role in INTERACTIVE_ROLES or role in LANDMARK_ROLES:
                counter += 1
                ref = f"e{counter}"
                out.append({
                    "ref": ref,
                    "role": role,
                    "name": name[:120],
                    "value": node.get("value"),
                })
            children = node.get("children") or []
            if children:
                walk(children)

    walk(raw_nodes)
    return out


def build_tree_from_page(page: Any) -> list[dict[str, Any]]:
    """Extract simplified a11y snapshot from Playwright page."""
    snapshot = page.accessibility.snapshot(interesting_only=True)
    if not snapshot:
        return []
    return prune_a11y_tree([snapshot])
