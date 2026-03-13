"""API client for Boss Zhipin."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from boss_cli.auth import Credential
from boss_cli.constants import (
    BASE_URL,
    CITY_CODES,
    DELIVER_LIST_URL,
    FRIEND_ADD_URL,
    FRIEND_LIST_URL,
    GEEK_GET_JOB_URL,
    HEADERS,
    INTERVIEW_DATA_URL,
    JOB_CARD_URL,
    JOB_DETAIL_URL,
    JOB_HISTORY_URL,
    JOB_RECOMMEND_URL,
    JOB_SEARCH_URL,
    RESUME_BASEINFO_URL,
    RESUME_EXPECT_URL,
    RESUME_STATUS_URL,
    USER_INFO_URL,
)

logger = logging.getLogger(__name__)


class BossClient:
    """Async HTTP client wrapper for Boss Zhipin APIs."""

    def __init__(self, credential: Credential | None = None):
        self.credential = credential
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> BossClient:
        headers = dict(HEADERS)
        cookies = {}
        if self.credential:
            cookies = self.credential.cookies
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=headers,
            cookies=cookies,
            follow_redirects=True,
            timeout=httpx.Timeout(30),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with BossClient() as client:'")
        return self._client

    def _check_response(self, data: dict[str, Any], action: str) -> dict[str, Any]:
        """Validate API response and return zpData."""
        code = data.get("code", -1)
        if code == 37:
            raise RuntimeError(
                f"{action}: 环境异常 (__zp_stoken__ 已过期)。"
                "请清除 cookie 后重新登录: boss logout && boss login"
            )
        if code != 0:
            raise RuntimeError(f"{action}: {data.get('message', 'Unknown error')} (code={code})")
        return data.get("zpData", {})

    # ── Job Search & Browse ─────────────────────────────────────────

    async def search_jobs(
        self,
        query: str,
        city: str = "101010100",
        page: int = 1,
        page_size: int = 15,
        experience: str | None = None,
        degree: str | None = None,
        salary: str | None = None,
        industry: str | None = None,
        scale: str | None = None,
        stage: str | None = None,
    ) -> dict[str, Any]:
        """Search jobs."""
        params: dict[str, Any] = {
            "query": query,
            "city": city,
            "page": page,
            "pageSize": page_size,
        }
        if experience:
            params["experience"] = experience
        if degree:
            params["degree"] = degree
        if salary:
            params["salary"] = salary
        if industry:
            params["industry"] = industry
        if scale:
            params["scale"] = scale
        if stage:
            params["stage"] = stage

        resp = await self.client.get(JOB_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "搜索职位")

    async def get_recommend_jobs(self, page: int = 1) -> dict[str, Any]:
        """Get personalized job recommendations."""
        resp = await self.client.get(JOB_RECOMMEND_URL, params={"page": page})
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "推荐职位")

    async def get_job_card(self, security_id: str, lid: str) -> dict[str, Any]:
        """Get job card info (hover preview)."""
        resp = await self.client.get(
            JOB_CARD_URL,
            params={"securityId": security_id, "lid": lid},
        )
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "职位卡片")

    async def get_job_detail(self, security_id: str, lid: str = "") -> dict[str, Any]:
        """Get detailed information for a specific job."""
        params: dict[str, str] = {"securityId": security_id}
        if lid:
            params["lid"] = lid
        resp = await self.client.get(JOB_DETAIL_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "职位详情")

    # ── Personal Center ─────────────────────────────────────────────

    async def get_user_info(self) -> dict[str, Any]:
        """Get current user info (userId, name, avatar, etc.)."""
        resp = await self.client.get(USER_INFO_URL)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "用户信息")

    async def get_resume_baseinfo(self) -> dict[str, Any]:
        """Get resume basic info (full profile: name, age, degree, etc.)."""
        resp = await self.client.get(RESUME_BASEINFO_URL)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "简历基本信息")

    async def get_resume_expect(self) -> dict[str, Any]:
        """Get job expectations (desired position, salary, city)."""
        resp = await self.client.get(RESUME_EXPECT_URL)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "求职期望")

    async def get_resume_status(self) -> dict[str, Any]:
        """Get resume status."""
        resp = await self.client.get(RESUME_STATUS_URL)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "简历状态")

    async def get_deliver_list(self, page: int = 1) -> dict[str, Any]:
        """Get list of jobs applied to (已投递)."""
        resp = await self.client.get(DELIVER_LIST_URL, params={"page": page})
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "已投递列表")

    async def get_interview_data(self) -> dict[str, Any]:
        """Get interview data (面试)."""
        resp = await self.client.get(INTERVIEW_DATA_URL)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "面试数据")

    async def get_job_history(self, page: int = 1) -> dict[str, Any]:
        """Get job browsing history."""
        resp = await self.client.get(JOB_HISTORY_URL, params={"page": page})
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "浏览历史")

    # ── Social / Chat ───────────────────────────────────────────────

    async def get_friend_list(self) -> dict[str, Any]:
        """Get geek friend list (沟通过的 Boss)."""
        resp = await self.client.get(FRIEND_LIST_URL)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "好友列表")

    async def add_friend(self, security_id: str, lid: str = "") -> dict[str, Any]:
        """Send greeting to a Boss (打招呼 / 投递简历).

        Args:
            security_id: Job security ID from search results
            lid: Lid parameter from search results
        """
        params: dict[str, str] = {"securityId": security_id}
        if lid:
            params["lid"] = lid
        resp = await self.client.get(FRIEND_ADD_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "打招呼")

    async def get_geek_job(self, security_id: str) -> dict[str, Any]:
        """Get interacted job info."""
        resp = await self.client.get(
            GEEK_GET_JOB_URL,
            params={"securityId": security_id},
        )
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "互动职位")


# ── City resolution ─────────────────────────────────────────────────

def resolve_city(name: str) -> str:
    """Resolve city name to code, passthrough if already a code."""
    if name.isdigit() and len(name) >= 6:
        return name
    return CITY_CODES.get(name, CITY_CODES["全国"])


def list_cities() -> dict[str, str]:
    """Return all supported city name -> code mappings."""
    return dict(CITY_CODES)
