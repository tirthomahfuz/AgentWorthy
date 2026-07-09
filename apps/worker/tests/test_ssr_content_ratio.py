"""Tests for ssr_content_ratio check."""

import httpx
import pytest

from agentworthy.models import CheckStatus
from agentworthy_worker.checks.ssr_content_ratio import check_ssr_content_ratio


class MockTransport(httpx.BaseTransport):
    def __init__(self, responses: dict[str, tuple[int, str]]) -> None:
        self.responses = responses

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for pattern, (status, body) in self.responses.items():
            if pattern in url:
                return httpx.Response(status, text=body, headers={"content-type": "text/html"})
        return httpx.Response(404, text="Not Found")


@pytest.fixture
def fixtures_dir():
    import os
    return os.path.join(os.path.dirname(__file__), "fixtures")


def test_ssr_good_content_without_playwright(fixtures_dir: str) -> None:
    with open(f"{fixtures_dir}/ssr_good.html") as f:
        html = f.read()

    transport = MockTransport({"example.com": (200, html)})
    client = httpx.Client(transport=transport)

    result = check_ssr_content_ratio("https://example.com", client)
    assert result.status == CheckStatus.PASS
    assert result.evidence["raw_text_length"] > 100


def test_ssr_poor_ratio_with_rendered(fixtures_dir: str) -> None:
    with open(f"{fixtures_dir}/ssr_poor.html") as f:
        raw_html = f.read()

    rendered_html = """<html><body>
    <h1>Welcome</h1>
    <p>This content only appears after JavaScript runs. We offer many services
    including consulting, implementation, training, and support for businesses
    of all sizes across multiple industries worldwide.</p>
    </body></html>"""

    transport = MockTransport({"example.com": (200, raw_html)})
    client = httpx.Client(transport=transport)

    result = check_ssr_content_ratio("https://example.com", client, rendered_html)
    assert result.status == CheckStatus.FAIL
    assert result.evidence["ratio"] < 0.30


def test_ssr_good_ratio_with_rendered(fixtures_dir: str) -> None:
    with open(f"{fixtures_dir}/ssr_good.html") as f:
        html = f.read()

    transport = MockTransport({"example.com": (200, html)})
    client = httpx.Client(transport=transport)

    result = check_ssr_content_ratio("https://example.com", client, html)
    assert result.status == CheckStatus.PASS
    assert result.evidence["ratio"] >= 0.30
