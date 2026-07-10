"""SSRF guard tests."""

import pytest

from agentworthy_worker.security.ssrf import validate_scan_url


def test_blocks_localhost() -> None:
    with pytest.raises(ValueError, match="Blocked|Private"):
        validate_scan_url("http://localhost/admin")


def test_blocks_metadata_ip() -> None:
    with pytest.raises(ValueError, match="Blocked|Private"):
        validate_scan_url("http://169.254.169.254/latest/meta-data")


def test_allows_public_https() -> None:
    url = validate_scan_url("https://example.com")
    assert url.startswith("https://example.com")
