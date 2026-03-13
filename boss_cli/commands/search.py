"""Search and browse commands: search, recommend, cities."""

from __future__ import annotations

import json
import logging

import click
from rich.table import Table

from ..client import list_cities, resolve_city
from ..constants import DEGREE_CODES, EXP_CODES, SALARY_CODES
from ._common import (
    console,
    handle_command,
    require_auth,
    structured_output_options,
)

logger = logging.getLogger(__name__)


@click.command()
@click.argument("keyword")
@click.option("-c", "--city", default="全国", help="城市名称或代码 (默认: 全国)")
@click.option("-p", "--page", default=1, type=int, help="页码 (默认: 1)")
@click.option("--salary", type=click.Choice(list(SALARY_CODES.keys())), help="薪资筛选")
@click.option("--exp", type=click.Choice(list(EXP_CODES.keys())), help="工作经验筛选")
@click.option("--degree", type=click.Choice(list(DEGREE_CODES.keys())), help="学历筛选")
@structured_output_options
def search(keyword: str, city: str, page: int, salary: str | None, exp: str | None, degree: str | None, as_json: bool, as_yaml: bool) -> None:
    """搜索职位 (例: boss search Python --city 北京)"""
    from ..auth import get_credential
    cred = get_credential()  # search works without full auth sometimes

    city_code = resolve_city(city)
    salary_code = SALARY_CODES.get(salary) if salary else None
    exp_code = EXP_CODES.get(exp) if exp else None
    degree_code = DEGREE_CODES.get(degree) if degree else None

    def _action(client):
        return client.search_jobs(
            query=keyword, city=city_code, page=page,
            experience=exp_code, degree=degree_code, salary=salary_code,
        )

    def _render(data: dict) -> None:
        job_list = data.get("jobList", [])
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

        table = Table(title=f"🔍 搜索: {keyword} ({filter_str}) — {len(job_list)} 个结果", show_lines=True)
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

    from ._common import handle_errors, get_client
    from ..exceptions import BossApiError

    try:
        from ..client import BossClient
        with BossClient(cred) as client:
            data = _action(client)
        if as_json:
            click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        elif as_yaml:
            try:
                import yaml
                click.echo(yaml.dump(data, allow_unicode=True, default_flow_style=False))
            except ImportError:
                click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            _render(data)
    except BossApiError as exc:
        console.print(f"[red]❌ 搜索失败: {exc}[/red]")


@click.command()
@click.option("-p", "--page", default=1, type=int, help="页码 (默认: 1)")
@structured_output_options
def recommend(page: int, as_json: bool, as_yaml: bool) -> None:
    """查看推荐职位 (基于求职期望)"""
    cred = require_auth()

    def _render(data: dict) -> None:
        job_list = data.get("jobList", [])
        if not job_list:
            console.print("[yellow]暂无推荐职位，请先设置求职期望[/yellow]")
            return

        table = Table(title=f"⭐ 推荐职位 (第 {page} 页 · {len(job_list)} 个)", show_lines=True)
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

    handle_command(cred, action=lambda c: c.get_recommend_jobs(page=page), render=_render, as_json=as_json, as_yaml=as_yaml)


@click.command()
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
