"""Browser-assisted QR login via Camoufox.

Hybrid approach:
1. Complete the QR login flow via HTTP (httpx) to obtain session cookies
   (wt2, wbg, zp_at).
2. Inject those cookies into a Camoufox browser and navigate to the site
   so that client-side JavaScript generates ``__zp_stoken__``.
3. Export all cookies from the browser context.

This gives us the complete cookie set that pure HTTP cannot achieve.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from typing import Any

from .auth import Credential, qr_login, save_credential
from .constants import BASE_URL

logger = logging.getLogger(__name__)

# Cookie domains to export from browser
BROWSER_EXPORT_DOMAINS = (".zhipin.com", "zhipin.com", "www.zhipin.com")


class BrowserLoginUnavailable(RuntimeError):
    """Raised when the camoufox browser backend cannot be started."""


def _ensure_camoufox_ready() -> None:
    """Validate that the Camoufox package and browser binary are available."""
    try:
        import camoufox  # noqa: F401
    except ImportError as exc:
        raise BrowserLoginUnavailable(
            "Browser-assisted QR login requires the `camoufox` package.\n"
            "Install it with: pip install 'kabi-boss-cli[browser]'"
        ) from exc

    try:
        result = subprocess.run(
            [sys.executable, "-m", "camoufox", "path"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BrowserLoginUnavailable(
            "Unable to validate the Camoufox browser installation."
        ) from exc

    if result.returncode != 0 or not result.stdout.strip():
        raise BrowserLoginUnavailable(
            "Camoufox browser runtime is missing. Run `python -m camoufox fetch` first."
        )


def _normalize_browser_cookies(raw_cookies: list[dict[str, Any]]) -> dict[str, str]:
    """Convert Playwright cookie entries into a flat dict, filtering to zhipin.com."""
    cookies: dict[str, str] = {}
    for entry in raw_cookies:
        name = entry.get("name")
        value = entry.get("value")
        domain = entry.get("domain", "")
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        if not any(domain.endswith(d) for d in BROWSER_EXPORT_DOMAINS):
            continue
        cookies[name] = value
    return cookies


def _hydrate_stoken_via_browser(cookies: dict[str, str]) -> dict[str, str]:
    """Inject session cookies into a Camoufox browser and harvest __zp_stoken__.

    Boss Zhipin's client-side JS generates __zp_stoken__ on page load.
    We open a headless browser with the session cookies already set, visit
    the site, and let JS run naturally.
    """
    from camoufox.sync_api import Camoufox

    playwright_cookies = []
    for name, value in cookies.items():
        playwright_cookies.append({
            "name": name,
            "value": value,
            "domain": ".zhipin.com",
            "path": "/",
        })

    with Camoufox(headless=True) as browser:
        context = browser.new_context()
        context.add_cookies(playwright_cookies)
        page = context.new_page()

        try:
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=20_000)
        except Exception:
            # networkidle may timeout, but cookies may still be set
            logger.debug("Camoufox page load did not reach networkidle")

        # Give JS a moment to set cookies
        try:
            page.wait_for_timeout(3000)
        except Exception:
            pass

        # Export all cookies
        result = _normalize_browser_cookies(context.cookies())

    return result


def browser_qr_login(
    *,
    on_status: callable | None = None,
) -> Credential:
    """Hybrid QR login: HTTP for session + Camoufox for __zp_stoken__.

    1. Run the standard HTTP QR login flow (user scans in terminal)
    2. If __zp_stoken__ is missing, use a headless Camoufox browser
       with the session cookies to let JS generate it
    3. Return the complete credential
    """
    _ensure_camoufox_ready()

    def _emit(msg: str) -> None:
        if on_status:
            on_status(msg)
        else:
            print(msg)

    # Step 1: Complete QR login via HTTP (reuse existing flow)
    cred = asyncio.run(qr_login())

    # Step 2: If __zp_stoken__ is missing, hydrate via browser
    if "__zp_stoken__" not in cred.cookies:
        _emit("\n🔧 正在通过浏览器补全 __zp_stoken__...")

        try:
            enriched = _hydrate_stoken_via_browser(cred.cookies)
        except Exception as exc:
            logger.warning("Browser __zp_stoken__ hydration failed: %s", exc)
            _emit("[yellow]⚠️  浏览器补全 __zp_stoken__ 失败，部分接口可能不可用[/yellow]")
            return cred

        if "__zp_stoken__" in enriched:
            # Merge: keep all original cookies, add browser-enriched ones
            merged = {**cred.cookies, **enriched}
            cred = Credential(cookies=merged)
            save_credential(cred)
            _emit("✅ __zp_stoken__ 补全成功！")
        else:
            _emit("⚠️  浏览器未能生成 __zp_stoken__，部分接口可能返回「环境异常」")
    else:
        _emit("✅ 已获取完整 cookies（含 __zp_stoken__）")

    return cred
