"""Tests for remaining static checks."""

import os
from unittest.mock import patch

import httpx

from agentworthy.models import CheckStatus
from agentworthy_worker.checks.actionability import (
    check_accessible_names,
    check_cta_reachable,
    check_forms_semantic,
    check_no_blocking_interstitials,
)
from agentworthy_worker.checks.discoverability import check_canonicals_clean, check_sitemap_present
from agentworthy_worker.checks.machine_readability import (
    check_contact_machine_readable,
    check_prices_machine_readable,
    check_schema_correct_type,
    check_schema_present,
)
from agentworthy_worker.checks.performance import check_page_weight, check_pagination_exists, check_ttfb
from agentworthy_worker.checks.trust_freshness import check_content_freshness, check_https_valid, check_nap_consistent
from helpers import make_ctx

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_sitemap_present_pass() -> None:
    robots = "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n"
    sitemap = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url></urlset>'
    ctx = make_ctx(
        responses={
            "/robots.txt": (200, robots),
            "sitemap.xml": (200, sitemap),
        },
        robots_content=robots,
    )
    result = check_sitemap_present(ctx)
    assert result.status == CheckStatus.PASS


def test_sitemap_missing_fail() -> None:
    ctx = make_ctx(responses={"/sitemap.xml": (404, "")})
    result = check_sitemap_present(ctx)
    assert result.status == CheckStatus.FAIL


def test_canonicals_clean_pass() -> None:
    html = '<html><head><link rel="canonical" href="https://example.com/"></head><body>Hi</body></html>'
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_canonicals_clean(ctx)
    assert result.status in (CheckStatus.PASS, CheckStatus.WARN)


def test_canonicals_duplicate_fail() -> None:
    html = '<html><head><link rel="canonical" href="https://example.com/a"><link rel="canonical" href="https://example.com/b"></head></html>'
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_canonicals_clean(ctx)
    assert result.status == CheckStatus.FAIL


def test_schema_present_pass() -> None:
    html = '<html><head><script type="application/ld+json">{"@type":"Organization","name":"Test"}</script></head></html>'
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_schema_present(ctx)
    assert result.status == CheckStatus.PASS


def test_schema_present_fail() -> None:
    html = "<html><body>No schema</body></html>"
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_schema_present(ctx)
    assert result.status == CheckStatus.FAIL


@patch("agentworthy_worker.checks.machine_readability.classify_site_type", return_value="ecommerce")
def test_schema_correct_type_ecommerce_pass(_mock) -> None:
    html = '<html><head><script type="application/ld+json">{"@type":"Product","offers":{"price":"29"}}</script></head></html>'
    ctx = make_ctx(pages={"https://example.com": html}, site_type="ecommerce")
    result = check_schema_correct_type(ctx)
    assert result.status == CheckStatus.PASS


def test_prices_machine_readable_pass() -> None:
    html = '<html><body><span>$29.99</span></body></html>'
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_prices_machine_readable(ctx)
    assert result.status == CheckStatus.PASS


def test_contact_machine_readable_pass() -> None:
    html = '<html><body><a href="mailto:hi@example.com">Email</a><a href="tel:+15550100">Call</a></body></html>'
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_contact_machine_readable(ctx)
    assert result.status == CheckStatus.PASS


def test_forms_semantic_pass() -> None:
    html = """<html><body><form><label for="n">Name</label><input id="n" name="name" type="text"></form></body></html>"""
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_forms_semantic(ctx)
    assert result.status == CheckStatus.PASS


def test_cta_reachable_pass() -> None:
    home = '<html><body><a href="https://example.com/shop">Shop Now</a></body></html>'
    shop = "<html><body><button>Buy</button></body></html>"
    ctx = make_ctx(pages={"https://example.com": home, "https://example.com/shop": shop})
    result = check_cta_reachable(ctx)
    assert result.status == CheckStatus.PASS


def test_no_blocking_interstitials_pass() -> None:
    html = "<html><body><main>Content</main></body></html>"
    ctx = make_ctx(pages={"https://example.com": html}, rendered_homepage_html=html)
    result = check_no_blocking_interstitials(ctx)
    assert result.status == CheckStatus.PASS


def test_no_blocking_interstitials_fail() -> None:
    html = '<html><body><div class="modal-overlay" style="position:fixed">Subscribe</div></body></html>'
    ctx = make_ctx(rendered_homepage_html=html, pages={"https://example.com": html})
    result = check_no_blocking_interstitials(ctx)
    assert result.status == CheckStatus.FAIL


def test_accessible_names_pass() -> None:
    html = '<html><body><button>Click me</button><a href="/">Home</a></body></html>'
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_accessible_names(ctx)
    assert result.status == CheckStatus.PASS


def test_accessible_names_fail() -> None:
    html = "<html><body><button></button></body></html>"
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_accessible_names(ctx)
    assert result.status == CheckStatus.FAIL


def test_https_valid_pass() -> None:
    ctx = make_ctx(root_url="https://example.com", responses={"example.com": (200, "<html></html>")})
    result = check_https_valid(ctx)
    assert result.status == CheckStatus.PASS


def test_https_valid_fail_http() -> None:
    ctx = make_ctx(root_url="http://example.com")
    result = check_https_valid(ctx)
    assert result.status == CheckStatus.FAIL


def test_content_freshness_recent_year() -> None:
    html = "<html><body><p>Copyright 2026 Example Co</p></body></html>"
    ctx = make_ctx(pages={"https://example.com": html}, responses={"example.com": (200, html)})
    result = check_content_freshness(ctx)
    assert result.status == CheckStatus.PASS


def test_nap_consistent_pass() -> None:
    html = '<html><body><a href="tel:+15550100">Call</a><a href="mailto:hi@example.com">Email</a></body></html>'
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_nap_consistent(ctx)
    assert result.status == CheckStatus.PASS


def test_ttfb_pass() -> None:
    ctx = make_ctx(homepage_ttfb_ms=500.0)
    result = check_ttfb(ctx)
    assert result.status == CheckStatus.PASS


def test_ttfb_fail() -> None:
    ctx = make_ctx(homepage_ttfb_ms=3500.0)
    result = check_ttfb(ctx)
    assert result.status == CheckStatus.FAIL


def test_page_weight_pass() -> None:
    ctx = make_ctx(homepage_weight_bytes=500_000)
    result = check_page_weight(ctx)
    assert result.status == CheckStatus.PASS


def test_page_weight_fail() -> None:
    ctx = make_ctx(homepage_weight_bytes=4_000_000)
    result = check_page_weight(ctx)
    assert result.status == CheckStatus.FAIL


def test_pagination_exists_pass() -> None:
    html = '<html><body><a href="/page/2">Next</a></body></html>'
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_pagination_exists(ctx)
    assert result.status == CheckStatus.PASS


def test_pagination_infinite_scroll_fail() -> None:
    html = '<html><body><div class="infinite-scroll"></div></body></html>'
    ctx = make_ctx(pages={"https://example.com": html})
    result = check_pagination_exists(ctx)
    assert result.status == CheckStatus.FAIL
