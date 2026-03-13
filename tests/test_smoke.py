"""End-to-end smoke tests for boss-cli.

These tests invoke real CLI commands against the live Boss Zhipin API
using your local saved cookies. They are **skipped by default** and
only run when explicitly requested::

    uv run pytest tests/test_smoke.py -v -m smoke

The test account is disposable — ALL operations including writes
(greet, batch-greet) are safe to run.
"""

from __future__ import annotations

import json
import re

import pytest
from click.testing import CliRunner

from boss_cli.cli import cli

smoke = pytest.mark.smoke

runner = CliRunner()


def _invoke(*args: str):
    """Run a CLI command and return result."""
    return runner.invoke(cli, list(args))


def _invoke_json(*args: str):
    """Run a CLI command with --json and return (result, parsed_data)."""
    result = runner.invoke(cli, [*args, "--json"])
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
    """Verify authentication is working e2e."""

    def test_status(self):
        result = _invoke("status")
        assert result.exit_code == 0
        assert "已登录" in result.output

    def test_status_json(self):
        result, data = _invoke_json("status")
        assert result.exit_code == 0
        assert data is not None
        assert data["authenticated"] is True
        assert data["cookie_count"] > 0


# ── Profile ─────────────────────────────────────────────────────────


@smoke
class TestProfile:
    """Test profile and personal center commands."""

    def test_me(self):
        result = _invoke("me")
        assert result.exit_code == 0
        # Non-TTY auto-outputs JSON, TTY shows rich panel
        assert "个人资料" in result.output or "name" in result.output

    def test_me_json(self):
        result, data = _invoke_json("me")
        assert result.exit_code == 0
        assert data is not None
        # Must have at least one of these fields
        assert any(k in data for k in ("name", "nickName", "account"))

    def test_me_has_basic_fields(self):
        """Verify profile JSON has expected structure."""
        result, data = _invoke_json("me")
        assert result.exit_code == 0
        if data:
            for field in ("name", "gender"):
                assert field in data, f"Missing field: {field}"


# ── Applied / Interview ─────────────────────────────────────────────


@smoke
class TestPersonalCenter:
    """Test applied jobs and interviews."""

    def test_applied(self):
        result = _invoke("applied")
        assert result.exit_code == 0
        # Non-TTY auto-outputs JSON, TTY shows rich table
        assert "已投递" in result.output or "暂无投递记录" in result.output or "cardList" in result.output

    def test_applied_json(self):
        result, data = _invoke_json("applied")
        assert result.exit_code == 0
        # Data may be None if API failed (stoken), but command should not crash

    def test_applied_pagination(self):
        result = _invoke("applied", "-p", "1")
        assert result.exit_code == 0

    def test_interviews(self):
        result = _invoke("interviews")
        assert result.exit_code == 0
        assert "面试" in result.output or "暂无面试" in result.output or "interviewList" in result.output

    def test_interviews_json(self):
        result, data = _invoke_json("interviews")
        assert result.exit_code == 0


# ── Search ──────────────────────────────────────────────────────────


@smoke
class TestSearch:
    """Test job search commands."""

    def test_search_basic(self):
        result = _invoke("search", "Python", "--city", "全国")
        assert result.exit_code == 0

    def test_search_json(self):
        result, data = _invoke_json("search", "Java")
        assert result.exit_code == 0
        if data is not None:
            assert "jobList" in data

    def test_search_with_city(self):
        result = _invoke("search", "golang", "--city", "杭州")
        assert result.exit_code == 0

    def test_search_with_salary(self):
        result = _invoke("search", "前端", "--salary", "20-30K")
        assert result.exit_code == 0

    def test_search_with_exp(self):
        result = _invoke("search", "后端", "--exp", "3-5年")
        assert result.exit_code == 0

    def test_search_with_degree(self):
        result = _invoke("search", "AI", "--degree", "硕士")
        assert result.exit_code == 0

    def test_search_combined_filters(self):
        result = _invoke("search", "golang", "--city", "杭州", "--salary", "20-30K", "--exp", "3-5年")
        assert result.exit_code == 0

    def test_search_pagination(self):
        result = _invoke("search", "Python", "-p", "2")
        assert result.exit_code == 0

    def test_search_json_structure(self):
        """Verify search JSON response has expected fields when successful."""
        result, data = _invoke_json("search", "Python", "--city", "全国")
        if data is not None:
            # jobList should be a list
            assert isinstance(data.get("jobList", []), list)


# ── Recommend ───────────────────────────────────────────────────────


@smoke
class TestRecommend:
    """Test recommendation commands."""

    def test_recommend(self):
        result = _invoke("recommend")
        assert result.exit_code == 0

    def test_recommend_json(self):
        result, data = _invoke_json("recommend")
        assert result.exit_code == 0

    def test_recommend_pagination(self):
        result = _invoke("recommend", "-p", "1")
        assert result.exit_code == 0


# ── Chat ────────────────────────────────────────────────────────────


@smoke
class TestChat:
    """Test chat/friend list commands."""

    def test_chat(self):
        result = _invoke("chat")
        assert result.exit_code == 0
        # Non-TTY auto-outputs JSON, TTY shows rich table
        assert "沟通" in result.output or "暂无沟通" in result.output or result.output.strip().startswith("{")

    def test_chat_json(self):
        result, data = _invoke_json("chat")
        assert result.exit_code == 0


# ── Cities ──────────────────────────────────────────────────────────


@smoke
class TestCities:
    """Test city listing."""

    def test_cities(self):
        result = _invoke("cities")
        assert result.exit_code == 0
        assert "北京" in result.output
        assert "上海" in result.output
        assert "杭州" in result.output
        assert "深圳" in result.output

    def test_cities_has_codes(self):
        result = _invoke("cities")
        # Should contain at least one city code (digits)
        assert re.search(r"\d{9}", result.output)


# ── Greet (write operations — safe on test account) ─────────────────


@smoke
class TestGreet:
    """Test greet operations.

    These are write operations but safe on the test account.
    """

    def test_greet_missing_id(self):
        """Greet without security_id should show usage error."""
        result = _invoke("greet")
        assert result.exit_code != 0  # Missing argument

    def test_greet_invalid_id(self):
        """Greet with an invalid security_id should get an API error, not crash."""
        result = _invoke("greet", "invalid_test_id_12345")
        # Should not crash — either success or API error message
        assert result.exit_code == 0


# ── Batch Greet ─────────────────────────────────────────────────────


@smoke
class TestBatchGreet:
    """Test batch greet operations."""

    def test_batch_greet_dry_run(self):
        """Dry run should show preview without sending."""
        result = _invoke("batch-greet", "Python", "--city", "杭州", "-n", "2", "--dry-run")
        assert result.exit_code == 0
        # Should show either preview table or API error
        assert "预览" in result.output or "搜索失败" in result.output

    def test_batch_greet_count_1_yes(self):
        """Actually greet ONE job from search results (test account safe)."""
        result = _invoke("batch-greet", "golang", "--city", "杭州", "-n", "1", "-y")
        assert result.exit_code == 0
        # Should show completion or API error
        assert "完成" in result.output or "搜索失败" in result.output


# ── Roundtrip workflows ────────────────────────────────────────────


@smoke
class TestRoundtrip:
    """Multi-step workflow smoke tests — verify session stays valid."""

    def test_status_then_me(self):
        """Check auth then profile."""
        r1 = _invoke("status")
        assert r1.exit_code == 0
        r2 = _invoke("me")
        assert r2.exit_code == 0

    def test_search_then_recommend(self):
        """Search then recommendations."""
        r1 = _invoke("search", "golang", "--city", "杭州")
        assert r1.exit_code == 0
        r2 = _invoke("recommend")
        assert r2.exit_code == 0

    def test_me_then_applied_then_interviews(self):
        """Profile → applied → interviews."""
        r1 = _invoke("me")
        assert r1.exit_code == 0
        r2 = _invoke("applied")
        assert r2.exit_code == 0
        r3 = _invoke("interviews")
        assert r3.exit_code == 0

    def test_full_workflow(self):
        """Complete daily workflow: status → me → search → recommend → applied → chat."""
        for cmd in [
            ["status"],
            ["me"],
            ["search", "Python", "--city", "全国"],
            ["recommend"],
            ["applied"],
            ["chat"],
        ]:
            result = _invoke(*cmd)
            assert result.exit_code == 0, f"Command {cmd} failed: {result.output}"

    def test_search_json_then_rich(self):
        """Same search in JSON then rich format to verify both paths."""
        r1 = _invoke("search", "golang", "--json")
        assert r1.exit_code == 0
        r2 = _invoke("search", "golang")
        assert r2.exit_code == 0
