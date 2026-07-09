"""Integration test for 429 rate limit response."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from agentworthy.main import app


@patch("agentworthy.routes.public.increment_rate_limit")
@patch("agentworthy.routes.public.check_rate_limit", return_value=(False, 0))
def test_public_scan_returns_429_when_rate_limited(_mock_check, _mock_incr) -> None:
    client = TestClient(app)
    response = client.post("/public/scan", json={"url": "https://example.com"})
    assert response.status_code == 429
    assert "Rate limit" in response.json()["detail"]
