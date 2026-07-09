"""Tests for robots_agent_access check."""

import httpx
import pytest
from urllib import robotparser

from agentworthy.models import CheckStatus
from agentworthy_worker.checks.robots_agent_access import check_robots_agent_access


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


def test_robots_allows_all_agents(fixtures_dir: str) -> None:
    with open(f"{fixtures_dir}/robots_allow_all.txt") as f:
        robots_content = f.read()

    transport = MockTransport({"/robots.txt": (200, robots_content)})
    client = httpx.Client(transport=transport, base_url="https://example.com")

    result = check_robots_agent_access("https://example.com", client)
    assert result.status == CheckStatus.PASS
    assert result.check_key == "robots_agent_access"
    assert result.evidence["blocked_bots"] == []


def test_robots_blocks_agents(fixtures_dir: str) -> None:
    with open(f"{fixtures_dir}/robots_block_agents.txt") as f:
        robots_content = f.read()

    transport = MockTransport({"/robots.txt": (200, robots_content)})
    client = httpx.Client(transport=transport, base_url="https://example.com")

    result = check_robots_agent_access("https://example.com", client)
    assert result.status == CheckStatus.FAIL
    assert len(result.evidence["blocked_bots"]) == 4


def test_robots_missing_returns_warn() -> None:
    transport = MockTransport({})
    client = httpx.Client(transport=transport, base_url="https://example.com")

    result = check_robots_agent_access("https://example.com", client)
    assert result.status == CheckStatus.WARN


def test_robotparser_parsing(fixtures_dir: str) -> None:
    with open(f"{fixtures_dir}/robots_block_agents.txt") as f:
        content = f.read()
    rp = robotparser.RobotFileParser()
    rp.parse(content.splitlines())
    assert not rp.can_fetch("GPTBot", "https://example.com/")
    assert rp.can_fetch("Googlebot", "https://example.com/")
