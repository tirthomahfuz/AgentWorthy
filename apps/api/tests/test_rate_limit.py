"""Tests for Redis rate limiting."""

from unittest.mock import MagicMock, patch

import pytest

from agentworthy.redis_client import check_rate_limit, hash_ip, increment_rate_limit


@patch("agentworthy.redis_client.get_redis")
def test_rate_limit_blocks_fourth_scan(mock_get_redis: MagicMock) -> None:
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.get.return_value = "3"
    ip_hash = hash_ip("192.168.1.1")
    allowed, remaining = check_rate_limit(ip_hash)
    assert allowed is False
    assert remaining == 0


@patch("agentworthy.redis_client.get_redis")
def test_rate_limit_allows_under_limit(mock_get_redis: MagicMock) -> None:
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.get.return_value = "2"
    ip_hash = hash_ip("192.168.1.1")
    allowed, remaining = check_rate_limit(ip_hash)
    assert allowed is True
    assert remaining == 1


@patch("agentworthy.redis_client.get_redis")
def test_increment_rate_limit(mock_get_redis: MagicMock) -> None:
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    mock_get_redis.return_value = mock_redis
    increment_rate_limit(hash_ip("10.0.0.1"))
    mock_pipe.incr.assert_called_once()
    mock_pipe.expire.assert_called_once()
    mock_pipe.execute.assert_called_once()
