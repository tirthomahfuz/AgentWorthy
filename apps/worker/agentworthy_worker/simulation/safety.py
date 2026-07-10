"""Simulation safety rails."""

from __future__ import annotations

import re
from urllib.parse import urlparse

PAYMENT_PATTERNS = re.compile(
    r"card|cvv|cvc|expir|cc-number|credit", re.I
)
DESTRUCTIVE_PATTERNS = re.compile(
    r"\b(delete|unsubscribe|cancel account|remove)\b", re.I
)
CHECKOUT_ALLOWLIST = {
    "checkout.stripe.com",
    "checkout.shopify.com",
    "pay.google.com",
}
FAKE_IDENTITY = {
    "name": "Test Agent",
    "email": "test@agentworthy.example",
    "phone": "000-000-0000",
    "address": "123 Test St",
}


def is_payment_field(attrs: dict[str, str]) -> bool:
    ac = attrs.get("autocomplete", "")
    if ac.startswith("cc-"):
        return True
    combined = " ".join(attrs.get(k, "") for k in ("name", "id", "placeholder", "aria-label"))
    return bool(PAYMENT_PATTERNS.search(combined))


def is_destructive_action(name: str, task: str) -> bool:
    if DESTRUCTIVE_PATTERNS.search(name):
        if not DESTRUCTIVE_PATTERNS.search(task):
            return True
    return False


def navigation_allowed(target_url: str, root_domain: str) -> tuple[bool, str | None]:
    host = (urlparse(target_url).hostname or "").lower()
    if host == root_domain or host.endswith(f".{root_domain}"):
        return True, None
    if host in CHECKOUT_ALLOWLIST:
        return True, "checkout_allowlist"
    return False, None


def form_submission_allowed(action: str | None, page_origin: str) -> bool:
    if not action or action.startswith("/") or action.startswith(page_origin):
        return True
    return False
