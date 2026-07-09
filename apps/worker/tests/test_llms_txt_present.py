"""Tests for llms_txt_present check."""

from agentworthy.models import CheckStatus
from agentworthy_worker.checks.llms_txt_present import check_llms_txt_present
from helpers import make_ctx


def test_llms_txt_present_pass() -> None:
    import os
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    with open(f"{fixtures_dir}/llms_txt_valid.txt") as f:
        content = f.read()
    ctx = make_ctx(responses={"/llms.txt": (200, content)})
    result = check_llms_txt_present(ctx)
    assert result.status == CheckStatus.PASS


def test_llms_txt_missing_fail() -> None:
    ctx = make_ctx(responses={})
    result = check_llms_txt_present(ctx)
    assert result.status == CheckStatus.FAIL


def test_llms_txt_too_short_warn() -> None:
    ctx = make_ctx(responses={"/llms.txt": (200, "short")})
    result = check_llms_txt_present(ctx)
    assert result.status == CheckStatus.WARN
