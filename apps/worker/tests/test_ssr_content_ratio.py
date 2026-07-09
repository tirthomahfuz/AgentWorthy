"""Tests for ssr_content_ratio check."""

import os

from agentworthy.models import CheckStatus
from agentworthy_worker.checks.ssr_content_ratio import check_ssr_content_ratio
from helpers import make_ctx

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_ssr_good_content_without_playwright() -> None:
    with open(f"{FIXTURES}/ssr_good.html") as f:
        html = f.read()
    ctx = make_ctx(
        responses={"example.com": (200, html)},
        pages={"https://example.com": html},
    )
    result = check_ssr_content_ratio(ctx)
    assert result.status == CheckStatus.PASS


def test_ssr_poor_ratio_with_rendered() -> None:
    with open(f"{FIXTURES}/ssr_poor.html") as f:
        raw_html = f.read()
    rendered_html = """<html><body><h1>Welcome</h1><p>This content only appears after
    JavaScript runs. We offer many services including consulting, implementation,
    training, and support for businesses of all sizes across multiple industries.</p></body></html>"""
    ctx = make_ctx(
        responses={"example.com": (200, raw_html)},
        pages={"https://example.com": raw_html},
        rendered_homepage_html=rendered_html,
    )
    result = check_ssr_content_ratio(ctx)
    assert result.status == CheckStatus.FAIL
    assert result.evidence["ratio"] < 0.30


def test_ssr_render_blocked_warn() -> None:
    with open(f"{FIXTURES}/ssr_good.html") as f:
        html = f.read()
    ctx = make_ctx(
        pages={"https://example.com": html},
        responses={"example.com": (200, html)},
        render_blocked=True,
    )
    result = check_ssr_content_ratio(ctx)
    assert result.status == CheckStatus.WARN
    assert result.evidence.get("rendered_fetch_blocked")


def test_ssr_good_ratio_with_rendered() -> None:
    with open(f"{FIXTURES}/ssr_good.html") as f:
        html = f.read()
    ctx = make_ctx(
        pages={"https://example.com": html},
        responses={"example.com": (200, html)},
        rendered_homepage_html=html,
    )
    result = check_ssr_content_ratio(ctx)
    assert result.status == CheckStatus.PASS
