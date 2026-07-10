"""Tests for site ownership verification."""

from unittest.mock import MagicMock, patch

import httpx

from agentworthy.services.verification import (
    check_dns_txt,
    check_meta_tag,
    generate_verification_token,
    verify_ownership,
)


class MockTransport(httpx.BaseTransport):
    def __init__(self, html: str, status: int = 200) -> None:
        self.html = html
        self.status = status

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(self.status, text=self.html, headers={"content-type": "text/html"})


def test_generate_token_unique() -> None:
    a = generate_verification_token()
    b = generate_verification_token()
    assert a != b
    assert len(a) > 20


def test_meta_tag_found() -> None:
    token = "test-token-123"
    html = f'<html><head><meta name="agentworthy-verification" content="{token}"></head></html>'
    client = httpx.Client(transport=MockTransport(html))
    assert check_meta_tag("https://example.com", token, client) is True
    client.close()


def test_meta_tag_not_found() -> None:
    html = "<html><head></head><body>hi</body></html>"
    client = httpx.Client(transport=MockTransport(html))
    assert check_meta_tag("https://example.com", "missing", client) is False
    client.close()


@patch("agentworthy.services.verification.check_dns_txt", return_value=False)
def test_verify_neither_found(_mock_dns: MagicMock) -> None:
    html = "<html><body>no token</body></html>"
    with patch("httpx.Client") as mock_client_cls:
        instance = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = instance
        instance.get.return_value = MagicMock(status_code=200, text=html)
        ok, message, methods = verify_ownership("https://example.com", "tok")
    assert ok is False
    assert methods["meta_tag"] is False


@patch("agentworthy.services.verification.dns.resolver.resolve")
def test_dns_txt_found(mock_resolve: MagicMock) -> None:
    mock_resolve.return_value = [MagicMock(to_text=lambda: '"agentworthy-verification=mytoken"')]
    assert check_dns_txt("https://example.com", "mytoken") is True


@patch("agentworthy.services.verification.dns.resolver.resolve")
def test_dns_txt_not_found(mock_resolve: MagicMock) -> None:
    import dns.resolver
    mock_resolve.side_effect = dns.resolver.NXDOMAIN
    assert check_dns_txt("https://example.com", "mytoken") is False
