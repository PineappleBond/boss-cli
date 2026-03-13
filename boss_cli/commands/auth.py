"""Authentication commands: login, logout, status, me."""

from __future__ import annotations

import json
import logging

import click
from rich.panel import Panel

from ._common import (
    console,
    handle_command,
    require_auth,
    structured_output_options,
)

logger = logging.getLogger(__name__)


@click.command()
def login() -> None:
    """扫码登录 Boss 直聘 APP"""
    from ..auth import qr_login
    import asyncio

    try:
        asyncio.run(qr_login())
    except RuntimeError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise SystemExit(1) from None


@click.command()
def logout() -> None:
    """清除已保存的登录凭证"""
    from ..auth import clear_credential
    clear_credential()
    console.print("[green]✅ 已退出登录[/green]")


@click.command()
@structured_output_options
def status(as_json: bool, as_yaml: bool) -> None:
    """查看当前登录状态"""
    from ..auth import get_credential
    cred = get_credential()
    if cred:
        data = {"authenticated": True, "cookie_count": len(cred.cookies)}
        if as_json:
            click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        elif as_yaml:
            try:
                import yaml
                click.echo(yaml.dump(data, allow_unicode=True))
            except ImportError:
                click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            n = len(cred.cookies)
            console.print(f"[green]✅ 已登录[/green] ({n} cookies)")
    else:
        if as_json:
            click.echo(json.dumps({"authenticated": False}))
        else:
            console.print("[yellow]⚠️  未登录[/yellow]，使用 [bold]boss login[/bold] 扫码登录")


@click.command()
@structured_output_options
def me(as_json: bool, as_yaml: bool) -> None:
    """查看个人资料和求职期望"""
    cred = require_auth()

    def _render(info: dict) -> None:
        name = info.get("name", info.get("nickName", "-"))
        age = info.get("age", "-")
        degree = info.get("degreeCategory", "-")
        account = info.get("account", "-")
        gender = "男" if info.get("gender") == 1 else "女" if info.get("gender") == 2 else "-"

        panel = Panel(
            f"[bold]{name}[/bold]  {gender}  {age}\n"
            f"学历: {degree}\n"
            f"账号: {account}",
            title="👤 个人资料",
            border_style="cyan",
        )
        console.print(panel)

    handle_command(
        cred,
        action=lambda c: c.get_resume_baseinfo(),
        render=_render,
        as_json=as_json,
        as_yaml=as_yaml,
    )
