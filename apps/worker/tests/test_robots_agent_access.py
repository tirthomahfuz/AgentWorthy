"""Tests for robots_agent_access check."""

import pytest
from urllib import robotparser

from agentworthy.models import CheckStatus
from agentworthy_worker.checks.robots_agent_access import check_robots_agent_access
from helpers import make_ctx


@pytest.fixture
def fixtures_dir():
    import os
    return os.path.join(os.path.dirname(__file__), "fixtures")


def test_robots_allows_all_agents(fixtures_dir: str) -> None:
    with open(f"{fixtures_dir}/robots_allow_all.txt") as f:
        robots_content = f.read()
    ctx = make_ctx(responses={"/robots.txt": (200, robots_content)})
    result = check_robots_agent_access(ctx)
    assert result.status == CheckStatus.PASS
    assert result.evidence["blocked_bots"] == []


def test_robots_blocks_agents(fixtures_dir: str) -> None:
    with open(f"{fixtures_dir}/robots_block_agents.txt") as f:
        robots_content = f.read()
    ctx = make_ctx(responses={"/robots.txt": (200, robots_content)})
    result = check_robots_agent_access(ctx)
    assert result.status == CheckStatus.FAIL
    assert len(result.evidence["blocked_bots"]) == 4


def test_robots_missing_returns_warn() -> None:
    ctx = make_ctx(responses={})
    result = check_robots_agent_access(ctx)
    assert result.status == CheckStatus.WARN


def test_robotparser_parsing(fixtures_dir: str) -> None:
    with open(f"{fixtures_dir}/robots_block_agents.txt") as f:
        content = f.read()
    rp = robotparser.RobotFileParser()
    rp.parse(content.splitlines())
    assert not rp.can_fetch("GPTBot", "https://example.com/")
    assert rp.can_fetch("Googlebot", "https://example.com/")
