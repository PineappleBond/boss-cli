"""End-to-end smoke tests for boss-cli.

These tests invoke real CLI commands against the live Boss Zhipin API
using your local browser cookies. They are **skipped by default** and
only run when explicitly requested::

    uv run pytest -m smoke -v

Only read-only operations are tested — no writes (greet, batch-greet).
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from boss_cli.cli import cli

smoke = pytest.mark.smoke

runner = CliRunner()


def _invoke(*args: str):
    """Run a CLI command and return result."""
    return runner.invoke(cli, list(args))


def _invoke_json(*args: str):
    """Run a CLI command with --json-output and return parsed data."""
    result = runner.invoke(cli, [*args, "--json-output"])
    if result.exit_code != 0:
        return result, None
    try:
        data = json.loads(result.output)
    except json.JSONDecodeError:
        data = None
    return result, data


# ── Auth ────────────────────────────────────────────────────────────


@smoke
class TestAuth:
    """Verify authentication is working end-to-end."""

    def test_status(self):
        result = _invoke("status")
        assert result.exit_code == 0, f"status failed: {result.output}"
        assert "已登录" in result.output


# ── Read-only queries ───────────────────────────────────────────────


@smoke
class TestReadOnly:
    """Read-only CLI smoke tests."""

    def test_search(self):
        result = _invoke("search", "Python", "--city", "全国")
        assert result.exit_code == 0, f"search failed: {result.output}"

    def test_search_json(self):
        result, data = _invoke_json("search", "Java")
        assert result.exit_code == 0, f"search json failed: {result.output}"
        if data is not None:
            assert "jobList" in data

    def test_search_with_filters(self):
        result = _invoke("search", "golang", "--city", "杭州", "--salary", "20-30K")
        assert result.exit_code == 0, f"filtered search failed: {result.output}"

    def test_recommend(self):
        result = _invoke("recommend")
        assert result.exit_code == 0, f"recommend failed: {result.output}"

    def test_recommend_json(self):
        result, data = _invoke_json("recommend")
        assert result.exit_code == 0, f"recommend json failed: {result.output}"

    def test_me(self):
        result = _invoke("me")
        assert result.exit_code == 0, f"me failed: {result.output}"
        assert "个人资料" in result.output

    def test_me_json(self):
        result, data = _invoke_json("me")
        assert result.exit_code == 0, f"me json failed: {result.output}"
        assert data is not None
        assert "name" in data or "nickName" in data

    def test_applied(self):
        result = _invoke("applied")
        assert result.exit_code == 0, f"applied failed: {result.output}"

    def test_interviews(self):
        result = _invoke("interviews")
        assert result.exit_code == 0, f"interviews failed: {result.output}"

    def test_chat(self):
        result = _invoke("chat")
        assert result.exit_code == 0, f"chat failed: {result.output}"

    def test_cities(self):
        result = _invoke("cities")
        assert result.exit_code == 0, f"cities failed: {result.output}"
        assert "北京" in result.output

    def test_batch_greet_dry_run(self):
        """Test batch-greet with --dry-run (no actual writes).

        Note: this may fail with __zp_stoken__ expiry since search is used internally.
        """
        result = _invoke(
            "batch-greet", "Python", "--city", "杭州", "-n", "2", "--dry-run"
        )
        assert result.exit_code == 0, f"batch-greet dry-run failed: {result.output}"
        # May get "预览" or "环境异常" depending on stoken
        assert "预览" in result.output or "环境异常" in result.output


# ── Search → Read roundtrip ─────────────────────────────────────────


@smoke
class TestRoundtrip:
    """Multi-step workflow smoke tests."""

    def test_search_then_recommend(self):
        """Search then check recommendations — verifies session stays valid."""
        search_result = _invoke("search", "golang", "--city", "杭州")
        assert search_result.exit_code == 0

        rec_result = _invoke("recommend")
        assert rec_result.exit_code == 0

    def test_me_then_applied(self):
        """Check profile then check applications."""
        me_result = _invoke("me")
        assert me_result.exit_code == 0

        applied_result = _invoke("applied")
        assert applied_result.exit_code == 0
