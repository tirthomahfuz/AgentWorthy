"""Tests for scoring calculation."""

from agentworthy.models import CheckCategory, CheckStatus
from agentworthy_worker.checks.base import CheckResult
from agentworthy_worker.checks.runner import calculate_score


def test_calculate_score_all_pass() -> None:
    results = [
        CheckResult("a", CheckCategory.DISCOVERABILITY, 4, CheckStatus.PASS),
        CheckResult("b", CheckCategory.DISCOVERABILITY, 4, CheckStatus.PASS),
    ]
    score, grade = calculate_score(results)
    assert score == 100
    assert grade == "A"


def test_calculate_score_mixed() -> None:
    results = [
        CheckResult("a", CheckCategory.DISCOVERABILITY, 4, CheckStatus.PASS),
        CheckResult("b", CheckCategory.DISCOVERABILITY, 4, CheckStatus.WARN),
        CheckResult("c", CheckCategory.DISCOVERABILITY, 4, CheckStatus.FAIL),
    ]
    score, grade = calculate_score(results)
    # pass=4, warn=2, total=12 -> (4+2)/12 * 100 = 50
    assert score == 50
    assert grade == "F"


def test_calculate_score_ignores_not_applicable() -> None:
    results = [
        CheckResult("a", CheckCategory.DISCOVERABILITY, 4, CheckStatus.PASS),
        CheckResult("b", CheckCategory.DISCOVERABILITY, 4, CheckStatus.NOT_APPLICABLE),
    ]
    score, grade = calculate_score(results)
    assert score == 100
    assert grade == "A"
