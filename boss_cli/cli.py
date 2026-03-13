"""CLI entry point for Boss CLI."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from boss_cli.auth import clear_credential, get_credential, qr_login
from boss_cli.client import BossClient, list_cities, resolve_city
from boss_cli.constants import DEGREE_CODES, EXP_CODES, SALARY_CODES

console = Console()


def _require_auth():
    """Get credential or exit with error."""
    cred = get_credential()
    if not cred:
        console.print("[yellow]⚠️  未登录[/yellow]，使用 [bold]boss login[/bold] 扫码登录")
        sys.exit(1)
    return cred


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
@click.version_option(package_name="boss-cli")
def cli(verbose: bool) -> None:
    """Boss CLI — 在终端使用 BOSS 直聘 🤝"""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(name)s: %(message)s")


# ── Auth commands ───────────────────────────────────────────────────

@cli.command()
def login() -> None:
    """扫码登录 Boss 直聘 APP"""
    try:
        asyncio.run(qr_login())
    except RuntimeError as e:
        console.print(f"[red]❌ {e}[/red]")
        sys.exit(1)


@cli.command()
def logout() -> None:
    """清除已保存的登录凭证"""
    clear_credential()
    console.print("[green]✅ 已退出登录[/green]")


@cli.command()
def status() -> None:
    """查看当前登录状态"""
    cred = get_credential()
    if cred:
        n = len(cred.cookies)
        console.print(f"[green]✅ 已登录[/green] ({n} cookies)")
    else:
        console.print("[yellow]⚠️  未登录[/yellow]，使用 [bold]boss login[/bold] 扫码登录")


# ── Personal Profile ────────────────────────────────────────────────

@cli.command()
@click.option("--json-output", "as_json", is_flag=True, help="输出原始 JSON")
def me(as_json: bool) -> None:
    """查看个人资料和求职期望"""
    cred = _require_auth()
    asyncio.run(_me(as_json, cred))


async def _me(as_json: bool, cred: object) -> None:
    async with BossClient(cred) as client:
        try:
            info = await client.get_resume_baseinfo()
        except Exception as e:
            console.print(f"[red]❌ 获取个人资料失败: {e}[/red]")
            return

    if as_json:
        click.echo(json.dumps(info, indent=2, ensure_ascii=False))
        return

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


# ── Applied Jobs ────────────────────────────────────────────────────

@cli.command()
@click.option("-p", "--page", default=1, type=int, help="页码 (默认: 1)")
@click.option("--json-output", "as_json", is_flag=True, help="输出原始 JSON")
def applied(page: int, as_json: bool) -> None:
    """查看已投递的职位"""
    cred = _require_auth()
    asyncio.run(_applied(page, as_json, cred))


async def _applied(page: int, as_json: bool, cred: object) -> None:
    async with BossClient(cred) as client:
        try:
            data = await client.get_deliver_list(page=page)
        except Exception as e:
            console.print(f"[red]❌ 获取投递记录失败: {e}[/red]")
            return

    if as_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    card_list = data.get("cardList", [])
    total = data.get("totalCount", 0)

    if not card_list:
        console.print("[yellow]暂无投递记录[/yellow]")
        return

    table = Table(title=f"📮 已投递 ({total} 个)", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("职位", style="bold cyan", max_width=25)
    table.add_column("公司", style="green", max_width=20)
    table.add_column("薪资", style="yellow", max_width=12)
    table.add_column("状态", max_width=10)
    table.add_column("时间", style="dim", max_width=15)

    for i, card in enumerate(card_list, 1):
        job_info = card.get("jobInfo", card)
        brand_info = card.get("brandInfo", card)
        status_info = card.get("deliverStatusDesc", card.get("statusDesc", "-"))

        table.add_row(
            str(i),
            job_info.get("jobName", card.get("jobName", "-")),
            brand_info.get("brandName", card.get("brandName", "-")),
            job_info.get("salaryDesc", card.get("salaryDesc", "-")),
            str(status_info),
            card.get("updateTimeDesc", card.get("createTimeDesc", "-")),
        )

    console.print(table)

    if page * 15 < total:
        console.print(f"\n  [dim]▸ 更多: boss applied -p {page + 1}[/dim]")


# ── Interview ───────────────────────────────────────────────────────

@cli.command()
@click.option("--json-output", "as_json", is_flag=True, help="输出原始 JSON")
def interviews(as_json: bool) -> None:
    """查看面试邀请"""
    cred = _require_auth()
    asyncio.run(_interviews(as_json, cred))


async def _interviews(as_json: bool, cred: object) -> None:
    async with BossClient(cred) as client:
        try:
            data = await client.get_interview_data()
        except Exception as e:
            console.print(f"[red]❌ 获取面试数据失败: {e}[/red]")
            return

    if as_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    interview_list = data.get("interviewList", [])

    if not interview_list:
        console.print("[yellow]暂无面试邀请[/yellow]")
        return

    table = Table(title=f"📋 面试邀请 ({len(interview_list)} 个)", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("职位", style="bold cyan", max_width=25)
    table.add_column("公司", style="green", max_width=20)
    table.add_column("时间", style="yellow", max_width=20)
    table.add_column("地点", style="blue", max_width=25)
    table.add_column("状态", max_width=10)

    for i, interview in enumerate(interview_list, 1):
        table.add_row(
            str(i),
            interview.get("jobName", "-"),
            interview.get("brandName", "-"),
            interview.get("interviewTime", "-"),
            interview.get("address", "-"),
            interview.get("statusDesc", "-"),
        )

    console.print(table)


# ── Chat / Friend list ──────────────────────────────────────────────

@cli.command("chat")
@click.option("--json-output", "as_json", is_flag=True, help="输出原始 JSON")
def chat_list(as_json: bool) -> None:
    """查看沟通过的 Boss 列表"""
    cred = _require_auth()
    asyncio.run(_chat_list(as_json, cred))


async def _chat_list(as_json: bool, cred: object) -> None:
    async with BossClient(cred) as client:
        try:
            data = await client.get_friend_list()
        except Exception as e:
            console.print(f"[red]❌ 获取好友列表失败: {e}[/red]")
            return

    if as_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    friend_list = data.get("result", data.get("friendList", []))

    if not friend_list:
        console.print("[yellow]暂无沟通记录[/yellow]")
        return

    table = Table(title=f"💬 沟通列表 ({len(friend_list)} 个)", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Boss", style="bold cyan", max_width=15)
    table.add_column("公司", style="green", max_width=20)
    table.add_column("职位", max_width=25)
    table.add_column("最近消息", style="dim", max_width=30)

    for i, friend in enumerate(friend_list, 1):
        table.add_row(
            str(i),
            friend.get("name", friend.get("bossName", "-")),
            friend.get("brandName", "-"),
            friend.get("jobName", "-"),
            friend.get("lastMsg", friend.get("lastText", "-")),
        )

    console.print(table)


# ── Greet / Apply ───────────────────────────────────────────────────

@cli.command()
@click.argument("security_id")
@click.option("--lid", default="", help="Lid parameter from search results")
def greet(security_id: str, lid: str) -> None:
    """向 Boss 打招呼 / 投递简历 (需要 securityId)"""
    cred = _require_auth()
    asyncio.run(_greet(security_id, lid, cred))


async def _greet(security_id: str, lid: str, cred: object) -> None:
    async with BossClient(cred) as client:
        try:
            data = await client.add_friend(security_id=security_id, lid=lid)
            console.print("[green]✅ 打招呼成功！[/green]")
            if data:
                click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            console.print(f"[red]❌ 打招呼失败: {e}[/red]")


# ── Batch Greet ─────────────────────────────────────────────────────

@cli.command("batch-greet")
@click.argument("keyword")
@click.option("-c", "--city", default="全国", help="城市名称或代码")
@click.option("-n", "--count", default=5, type=int, help="打招呼数量 (默认: 5)")
@click.option("--salary", type=click.Choice(list(SALARY_CODES.keys())), help="薪资筛选")
@click.option("--exp", type=click.Choice(list(EXP_CODES.keys())), help="工作经验筛选")
@click.option("--degree", type=click.Choice(list(DEGREE_CODES.keys())), help="学历筛选")
@click.option("--dry-run", is_flag=True, help="仅预览，不实际发送")
@click.option("-y", "--yes", is_flag=True, help="跳过确认提示")
def batch_greet(keyword: str, city: str, count: int, salary: str | None, exp: str | None, degree: str | None, dry_run: bool, yes: bool) -> None:
    """批量向搜索结果中的 Boss 打招呼

    例: boss batch-greet "golang" --city 杭州 -n 10 --salary 20-30K
    """
    cred = _require_auth()
    asyncio.run(_batch_greet(keyword, city, count, salary, exp, degree, dry_run, yes, cred))


async def _batch_greet(
    keyword: str,
    city: str,
    count: int,
    salary: str | None,
    exp: str | None,
    degree: str | None,
    dry_run: bool,
    yes: bool,
    cred: object,
) -> None:
    city_code = resolve_city(city)
    salary_code = SALARY_CODES.get(salary) if salary else None
    exp_code = EXP_CODES.get(exp) if exp else None
    degree_code = DEGREE_CODES.get(degree) if degree else None

    async with BossClient(cred) as client:
        # Search for jobs
        try:
            data = await client.search_jobs(
                query=keyword,
                city=city_code,
                experience=exp_code,
                degree=degree_code,
                salary=salary_code,
            )
        except Exception as e:
            console.print(f"[red]❌ 搜索失败: {e}[/red]")
            return

        job_list = data.get("jobList", [])
        if not job_list:
            console.print("[yellow]没有找到匹配的职位[/yellow]")
            return

        targets = job_list[:count]

        # Preview
        table = Table(title=f"🎯 将向以下 {len(targets)} 个职位打招呼", show_lines=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("职位", style="bold cyan", max_width=25)
        table.add_column("公司", style="green", max_width=20)
        table.add_column("薪资", style="yellow", max_width=12)

        for i, job in enumerate(targets, 1):
            table.add_row(
                str(i),
                job.get("jobName", "-"),
                job.get("brandName", "-"),
                job.get("salaryDesc", "-"),
            )

        console.print(table)

        if dry_run:
            console.print("\n  [dim]📋 预览模式，未实际发送[/dim]")
            return

        if not yes:
            confirm = click.confirm(f"\n确定向 {len(targets)} 个职位打招呼吗?")
            if not confirm:
                console.print("[dim]已取消[/dim]")
                return

        # Send greetings
        success = 0
        for i, job in enumerate(targets, 1):
            security_id = job.get("securityId", "")
            lid = job.get("lid", "")
            job_name = job.get("jobName", "?")
            brand = job.get("brandName", "?")

            if not security_id:
                console.print(f"  [{i}] [yellow]跳过 {job_name} (无 securityId)[/yellow]")
                continue

            try:
                await client.add_friend(security_id=security_id, lid=lid)
                console.print(f"  [{i}] [green]✅ {job_name} @ {brand}[/green]")
                success += 1
                # Rate limit: wait 1-2 seconds between greetings
                if i < len(targets):
                    time.sleep(1.5)
            except Exception as e:
                console.print(f"  [{i}] [red]❌ {job_name}: {e}[/red]")

        console.print(f"\n[bold]完成: {success}/{len(targets)} 个打招呼成功[/bold]")


# ── Job Search ──────────────────────────────────────────────────────

@cli.command()
@click.argument("keyword")
@click.option("-c", "--city", default="全国", help="城市名称或代码 (默认: 全国)")
@click.option("-p", "--page", default=1, type=int, help="页码 (默认: 1)")
@click.option("--salary", type=click.Choice(list(SALARY_CODES.keys())), help="薪资筛选")
@click.option("--exp", type=click.Choice(list(EXP_CODES.keys())), help="工作经验筛选")
@click.option("--degree", type=click.Choice(list(DEGREE_CODES.keys())), help="学历筛选")
@click.option("--json-output", "as_json", is_flag=True, help="输出原始 JSON")
def search(keyword: str, city: str, page: int, salary: str | None, exp: str | None, degree: str | None, as_json: bool) -> None:
    """搜索职位 (例: boss search Python --city 北京)"""
    cred = get_credential()
    asyncio.run(_search(keyword, city, page, salary, exp, degree, as_json, cred))


async def _search(
    keyword: str, city: str, page: int,
    salary: str | None, exp: str | None, degree: str | None,
    as_json: bool, cred: object | None,
) -> None:
    city_code = resolve_city(city)
    salary_code = SALARY_CODES.get(salary) if salary else None
    exp_code = EXP_CODES.get(exp) if exp else None
    degree_code = DEGREE_CODES.get(degree) if degree else None

    async with BossClient(cred) as client:
        try:
            data = await client.search_jobs(
                query=keyword,
                city=city_code,
                page=page,
                experience=exp_code,
                degree=degree_code,
                salary=salary_code,
            )
        except Exception as e:
            console.print(f"[red]❌ 搜索失败: {e}[/red]")
            return

    job_list = data.get("jobList", [])

    if as_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if not job_list:
        console.print("[yellow]没有找到匹配的职位[/yellow]")
        return

    filters = [city]
    if salary:
        filters.append(salary)
    if exp:
        filters.append(exp)
    if degree:
        filters.append(degree)
    filter_str = " · ".join(filters)

    table = Table(
        title=f"🔍 搜索: {keyword} ({filter_str}) — {len(job_list)} 个结果",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("职位", style="bold cyan", max_width=30)
    table.add_column("公司", style="green", max_width=20)
    table.add_column("薪资", style="yellow", max_width=12)
    table.add_column("经验", max_width=10)
    table.add_column("学历", max_width=8)
    table.add_column("地区", style="blue", max_width=15)
    table.add_column("技能", style="dim", max_width=20)

    for i, job in enumerate(job_list, 1):
        skills = job.get("skills", [])
        skill_str = ", ".join(skills[:3]) if skills else "-"
        area = job.get("areaDistrict", "")
        biz = job.get("businessDistrict", "")
        location = f"{area} {biz}".strip() if area else job.get("cityName", "-")

        table.add_row(
            str(i),
            job.get("jobName", "-"),
            job.get("brandName", "-"),
            job.get("salaryDesc", "-"),
            job.get("jobExperience", "-"),
            job.get("jobDegree", "-"),
            location,
            skill_str,
        )

    console.print(table)

    has_more = data.get("hasMore", False)
    if has_more:
        console.print(f"\n  [dim]▸ 更多结果: boss search \"{keyword}\" --city {city} -p {page + 1}[/dim]")


# ── Recommend ───────────────────────────────────────────────────────

@cli.command()
@click.option("-p", "--page", default=1, type=int, help="页码 (默认: 1)")
@click.option("--json-output", "as_json", is_flag=True, help="输出原始 JSON")
def recommend(page: int, as_json: bool) -> None:
    """查看推荐职位 (基于求职期望)"""
    cred = _require_auth()
    asyncio.run(_recommend(page, as_json, cred))


async def _recommend(page: int, as_json: bool, cred: object) -> None:
    async with BossClient(cred) as client:
        try:
            data = await client.get_recommend_jobs(page=page)
        except Exception as e:
            console.print(f"[red]❌ 获取推荐失败: {e}[/red]")
            return

    job_list = data.get("jobList", [])

    if as_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if not job_list:
        console.print("[yellow]暂无推荐职位，请先设置求职期望[/yellow]")
        return

    table = Table(
        title=f"⭐ 推荐职位 (第 {page} 页 · {len(job_list)} 个)",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("职位", style="bold cyan", max_width=30)
    table.add_column("公司", style="green", max_width=20)
    table.add_column("薪资", style="yellow", max_width=12)
    table.add_column("经验", max_width=10)
    table.add_column("学历", max_width=8)
    table.add_column("地区", style="blue", max_width=15)

    for i, job in enumerate(job_list, 1):
        area = job.get("areaDistrict", "")
        biz = job.get("businessDistrict", "")
        location = f"{area} {biz}".strip() if area else job.get("cityName", "-")

        table.add_row(
            str(i),
            job.get("jobName", "-"),
            job.get("brandName", "-"),
            job.get("salaryDesc", "-"),
            job.get("jobExperience", "-"),
            job.get("jobDegree", "-"),
            location,
        )

    console.print(table)

    has_more = data.get("hasMore", False)
    if has_more:
        console.print(f"\n  [dim]▸ 更多推荐: boss recommend -p {page + 1}[/dim]")


# ── Cities ──────────────────────────────────────────────────────────

@cli.command()
def cities() -> None:
    """列出支持的城市代码"""
    codes = list_cities()
    table = Table(title="🏙️ 支持的城市", show_lines=False)
    table.add_column("城市", style="cyan", width=10)
    table.add_column("代码", style="dim", width=12)

    for name, code in codes.items():
        table.add_row(name, code)

    console.print(table)
    console.print(f"\n  [dim]共 {len(codes)} 个城市。使用: boss search \"Python\" --city 杭州[/dim]")


# ── Entry ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
