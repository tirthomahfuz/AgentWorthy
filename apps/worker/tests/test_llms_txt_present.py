"""Tests for llms_txt_present check."""

import httpx
import pytest

from agentworthy.models import CheckStatus
from agentworthy_worker.checks.llms_txt_present import check_llms_txt_present


class MockTransport(httpx.BaseTransport):
    def __init__(self, responses: dict[str, tuple[int, str]]) -> None:
        self.responses = responses

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for pattern, (status, body) in self.responses.items():
            if pattern in url:
                return httpx.Response(status, text=body)
        return httpx.Response(404, text="Not Found")


@pytest.fixture
def fixtures_dir():
    import os
    return os.path.join(os.path.dirname(__file__), "fixtures")


def test_llms_txt_present_pass(fixtures_dir: str) -> None:
    with open(f"{fixtures_dir}/llms_txt_valid.txt") as f:
        content = f.read()

    transport = MockTransport({"/llms.txt": (200, content)})
    client = httpx.Client(transport=transport, base_url="https://example.com")

    result = check_llms_txt_present("https://example.com", client)
    assert result.status == CheckStatus.PASS
    assert result.evidence["content_length"] > 20


def test_llms_txt_missing_fail() -> None:
    transport = MockTransport({})
    client = httpx.Client(transport=transport, base_url="https://example.com")

    result = check_llms_txt_present("https://example.com", client)
    assert result.status == CheckStatus.FAIL


def test_llms_txt_too_short_warn() -> None:
    transport = MockTransport({"/llms.txt": (200, "short")})
    client = httpx.Client(transport=transport, base_url="https://example.com")

    result = check_llms_txt_present("https://example.com", client)
    assert result.status == CheckStatus.WARN
