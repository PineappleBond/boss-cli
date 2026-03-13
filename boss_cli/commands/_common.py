"""Common helpers for Boss CLI commands."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any, TypeVar

import click
from rich.console import Console

from ..auth import Credential, get_credential
from ..client import BossClient
from ..exceptions import BossApiError, SessionExpiredError, error_code_for_exception

T = TypeVar("T")

console = Console()
error_console = Console(stderr=True)


def require_auth() -> Credential:
    """Get credential or exit with error."""
    cred = get_credential()
    if not cred:
        console.print("[yellow]⚠️  未登录[/yellow]，使用 [bold]boss login[/bold] 扫码登录")
        sys.exit(1)
    return cred


def get_client(credential: Credential | None = None) -> BossClient:
    """Create a BossClient with optional credential."""
    return BossClient(credential)


def run_client_action(credential: Credential, action: Callable[[BossClient], T]) -> T:
    """Run an authenticated client action with auto-retry on session expiry.

    If SessionExpiredError is raised, tries once more with a fresh browser
    credential before giving up.
    """
    try:
        with get_client(credential) as client:
            return action(client)
    except SessionExpiredError:
        # Try refreshing from browser
        from ..auth import extract_browser_credential
        fresh = extract_browser_credential()
        if fresh:
            with get_client(fresh) as client:
                return action(client)
        raise


def handle_command(
    credential: Credential,
    *,
    action: Callable[[BossClient], T],
    render: Callable[[T], None] | None = None,
    as_json: bool = False,
    as_yaml: bool = False,
) -> T | None:
    """Run a client action with structured output support.

    - If --json is set, print JSON to stdout
    - If --yaml is set, print YAML to stdout
    - If non-TTY and neither flag, auto YAML
    - Otherwise, call render() for rich output
    """
    try:
        data = run_client_action(credential, action)

        if as_json:
            click.echo(json.dumps(data, indent=2, ensure_ascii=False))
            return data

        if as_yaml or not sys.stdout.isatty():
            try:
                import yaml
                click.echo(yaml.dump(data, allow_unicode=True, default_flow_style=False))
            except ImportError:
                click.echo(json.dumps(data, indent=2, ensure_ascii=False))
            return data

        if render:
            render(data)
        return data

    except BossApiError as exc:
        _print_error(exc)
        return None


def handle_errors(fn: Callable[[], T]) -> T | None:
    """Run arbitrary command logic and catch BossApiError."""
    try:
        return fn()
    except BossApiError as exc:
        _print_error(exc)
        return None


def _print_error(exc: BossApiError) -> None:
    """Print formatted error message."""
    code = error_code_for_exception(exc)
    console.print(f"[red]❌ [{code}] {exc}[/red]")


def structured_output_options(command: Callable) -> Callable:
    """Add --json/--yaml options to a Click command."""
    command = click.option("--yaml", "as_yaml", is_flag=True, help="以 YAML 格式输出")(command)
    command = click.option("--json", "as_json", is_flag=True, help="以 JSON 格式输出")(command)
    return command
