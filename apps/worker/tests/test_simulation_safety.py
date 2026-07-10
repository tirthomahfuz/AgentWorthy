"""Tests for simulation safety rails."""

import pytest

from agentworthy_worker.simulation.safety import (
    form_submission_allowed,
    is_destructive_action,
    is_payment_field,
    navigation_allowed,
)


def test_payment_field_detection() -> None:
    assert is_payment_field({"autocomplete": "cc-number", "name": "", "id": "", "placeholder": "", "aria-label": ""})
    assert is_payment_field({"name": "card_number", "id": "", "autocomplete": "", "placeholder": "", "aria-label": ""})


def test_destructive_block() -> None:
    assert is_destructive_action("Delete account", "Find pricing")
    assert not is_destructive_action("Delete item", "Delete the old listing from cart")


def test_off_domain_block() -> None:
    allowed, _ = navigation_allowed("https://evil.com/phish", "fixture-store.local")
    assert not allowed
    allowed, reason = navigation_allowed("https://checkout.stripe.com/pay", "fixture-store.local")
    assert allowed and reason == "checkout_allowlist"


def test_same_origin_form() -> None:
    assert form_submission_allowed("/contact", "http://localhost:8780")
    assert not form_submission_allowed("https://thirdparty.com/submit", "http://localhost:8780")
