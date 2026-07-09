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
    assert score == 50
    assert grade == "F"


def test_calculate_score_boundary_59_is_f() -> None:
    # 10 pass (weight 5 each) + 10 warn = (50+5)/100 = 55... need exact 59
    # Use weights: 18 pass + 2 warn of weight 10 each = (180+10)/200 = 95 - too high
    # 11 checks weight 10: 10 pass + 1 warn = (100+5)/110 = 95.45
    # Target 59: pass_w + 0.5*warn_w = 0.59 * total
    # 59 pass only of weight 1 = 59/100
    results = [CheckResult(f"c{i}", CheckCategory.PERFORMANCE, 1, CheckStatus.PASS) for i in range(59)]
    results += [CheckResult("f", CheckCategory.PERFORMANCE, 41, CheckStatus.FAIL)]
    score, grade = calculate_score(results)
    assert score == 59
    assert grade == "F"


def test_calculate_score_boundary_60_is_d() -> None:
    results = [CheckResult(f"c{i}", CheckCategory.PERFORMANCE, 1, CheckStatus.PASS) for i in range(60)]
    results += [CheckResult("f", CheckCategory.PERFORMANCE, 40, CheckStatus.FAIL)]
    score, grade = calculate_score(results)
    assert score == 60
    assert grade == "D"


def test_calculate_score_boundary_89_is_b() -> None:
    results = [CheckResult(f"c{i}", CheckCategory.PERFORMANCE, 1, CheckStatus.PASS) for i in range(89)]
    results += [CheckResult("f", CheckCategory.PERFORMANCE, 11, CheckStatus.FAIL)]
    score, grade = calculate_score(results)
    assert score == 89
    assert grade == "B"


def test_calculate_score_boundary_90_is_a() -> None:
    results = [CheckResult(f"c{i}", CheckCategory.PERFORMANCE, 1, CheckStatus.PASS) for i in range(90)]
    results += [CheckResult("f", CheckCategory.PERFORMANCE, 10, CheckStatus.FAIL)]
    score, grade = calculate_score(results)
    assert score == 90
    assert grade == "A"


def test_calculate_score_ignores_not_applicable() -> None:
    results = [
        CheckResult("a", CheckCategory.DISCOVERABILITY, 4, CheckStatus.PASS),
        CheckResult("b", CheckCategory.DISCOVERABILITY, 4, CheckStatus.NOT_APPLICABLE),
    ]
    score, grade = calculate_score(results)
    assert score == 100
    assert grade == "A"
