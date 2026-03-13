"""Tests for Boss CLI commands using Click's test runner."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from boss_cli.cli import cli

runner = CliRunner()


class TestCliBasic:
    """Test CLI basics without requiring cookies."""

    def test_version(self):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0." in result.output

    def test_help(self):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "BOSS 直聘" in result.output

    def test_all_commands_registered(self):
        result = runner.invoke(cli, ["--help"])
        commands_expected = [
            # Auth
            "login", "status", "logout",
            # Personal
            "me", "applied", "interviews",
            # Search & Browse
            "search", "recommend", "cities",
            # Social
            "chat", "greet", "batch-greet",
        ]
        for cmd in commands_expected:
            assert cmd in result.output, f"Command '{cmd}' not found in CLI help"

    def test_search_help(self):
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "--city" in result.output
        assert "--salary" in result.output
        assert "--exp" in result.output
        assert "--degree" in result.output

    def test_recommend_help(self):
        result = runner.invoke(cli, ["recommend", "--help"])
        assert result.exit_code == 0

    def test_me_help(self):
        result = runner.invoke(cli, ["me", "--help"])
        assert result.exit_code == 0

    def test_applied_help(self):
        result = runner.invoke(cli, ["applied", "--help"])
        assert result.exit_code == 0

    def test_interviews_help(self):
        result = runner.invoke(cli, ["interviews", "--help"])
        assert result.exit_code == 0

    def test_chat_help(self):
        result = runner.invoke(cli, ["chat", "--help"])
        assert result.exit_code == 0

    def test_greet_help(self):
        result = runner.invoke(cli, ["greet", "--help"])
        assert result.exit_code == 0

    def test_batch_greet_help(self):
        result = runner.invoke(cli, ["batch-greet", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--count" in result.output or "-n" in result.output

    def test_cities_output(self):
        result = runner.invoke(cli, ["cities"])
        assert result.exit_code == 0
        assert "北京" in result.output
        assert "上海" in result.output
        assert "杭州" in result.output
        assert "101010100" in result.output

    def test_status_without_auth(self):
        with patch("boss_cli.cli.get_credential", return_value=None):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "未登录" in result.output

    def test_me_without_auth(self):
        with patch("boss_cli.cli.get_credential", return_value=None):
            result = runner.invoke(cli, ["me"])
            assert result.exit_code == 1
            assert "未登录" in result.output

    def test_applied_without_auth(self):
        with patch("boss_cli.cli.get_credential", return_value=None):
            result = runner.invoke(cli, ["applied"])
            assert result.exit_code == 1

    def test_logout(self):
        with patch("boss_cli.cli.clear_credential"):
            result = runner.invoke(cli, ["logout"])
            assert result.exit_code == 0
            assert "已退出" in result.output


class TestCityResolution:
    """Test city name to code resolution."""

    def test_resolve_known_city(self):
        from boss_cli.client import resolve_city
        assert resolve_city("北京") == "101010100"
        assert resolve_city("上海") == "101020100"
        assert resolve_city("杭州") == "101210100"

    def test_resolve_unknown_city_returns_nationwide(self):
        from boss_cli.client import resolve_city
        assert resolve_city("不存在的城市") == "100010000"

    def test_resolve_code_passthrough(self):
        from boss_cli.client import resolve_city
        assert resolve_city("101010100") == "101010100"

    def test_list_cities(self):
        from boss_cli.client import list_cities
        cities = list_cities()
        assert len(cities) > 30
        assert "北京" in cities
        assert "杭州" in cities


class TestConstants:
    """Test constants are properly defined."""

    def test_salary_codes(self):
        from boss_cli.constants import SALARY_CODES
        assert len(SALARY_CODES) >= 8
        assert "20-30K" in SALARY_CODES

    def test_exp_codes(self):
        from boss_cli.constants import EXP_CODES
        assert len(EXP_CODES) >= 7
        assert "3-5年" in EXP_CODES

    def test_degree_codes(self):
        from boss_cli.constants import DEGREE_CODES
        assert len(DEGREE_CODES) >= 7
        assert "本科" in DEGREE_CODES

    def test_api_urls_defined(self):
        from boss_cli import constants
        assert constants.JOB_SEARCH_URL
        assert constants.JOB_RECOMMEND_URL
        assert constants.JOB_DETAIL_URL
        assert constants.DELIVER_LIST_URL
        assert constants.INTERVIEW_DATA_URL
        assert constants.FRIEND_LIST_URL
        assert constants.USER_INFO_URL
        assert constants.RESUME_BASEINFO_URL


class TestCredential:
    """Test credential management."""

    def test_credential_creation(self):
        from boss_cli.auth import Credential
        cred = Credential(cookies={"foo": "bar", "baz": "qux"})
        assert cred.is_valid
        assert cred.cookies == {"foo": "bar", "baz": "qux"}

    def test_credential_empty(self):
        from boss_cli.auth import Credential
        cred = Credential(cookies={})
        assert not cred.is_valid

    def test_credential_serialization(self):
        from boss_cli.auth import Credential
        cred = Credential(cookies={"a": "1"})
        data = cred.to_dict()
        assert "cookies" in data
        assert "saved_at" in data

        cred2 = Credential.from_dict(data)
        assert cred2.cookies == cred.cookies

    def test_cookie_header(self):
        from boss_cli.auth import Credential
        cred = Credential(cookies={"a": "1", "b": "2"})
        header = cred.as_cookie_header()
        assert "a=1" in header
        assert "b=2" in header
