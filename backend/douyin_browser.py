"""Read public Douyin video metadata in a fresh, anonymous browser context."""
import asyncio
import logging
import sys
import threading
from urllib.parse import urlsplit

from douyin import parse_video_data

logger = logging.getLogger(__name__)
_browser_slot = threading.BoundedSemaphore(1)


def extract_browser_video(video_id, user_agent):
    # Keep browser memory bounded on a small Railway instance.
    if not _browser_slot.acquire(timeout=3):
        raise ValueError("Browser Douyin sedang memproses video lain. Coba lagi sebentar.")
    try:
        return asyncio.run(_extract(video_id, user_agent))
    finally:
        _browser_slot.release()


async def _extract(video_id, user_agent):
    from playwright.async_api import async_playwright

    if not video_id.isdigit():
        raise ValueError("ID video Douyin tidak valid.")
    url = f"https://www.douyin.com/video/{video_id}"
    headers = {"User-Agent": user_agent, "Referer": "https://www.douyin.com/"}
    result = asyncio.get_running_loop().create_future()
    async with async_playwright() as playwright:
        launch_options = {"headless": True, "timeout": 15000, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        try:
            browser = await playwright.chromium.launch(channel="chromium", **launch_options)
        except Exception:
            if sys.platform != "win32":
                raise
            browser = await playwright.chromium.launch(channel="msedge", **launch_options)
        try:
            # No login cookie file, persistent profile, or imported storage state.
            context = await browser.new_context(user_agent=user_agent, locale="zh-CN", viewport={"width": 1280, "height": 800})
            page = await context.new_page()

            async def read_response(response):
                parts = urlsplit(response.url)
                if result.done() or parts.hostname != "www.douyin.com" or parts.path != "/aweme/v1/web/aweme/detail/":
                    return
                logger.info("Douyin browser detail HTTP %s for %s", response.status, video_id)
                if response.status != 200:
                    return
                try:
                    data = await response.json()
                    info = parse_video_data(data, video_id, url, headers)
                    if info and not result.done():
                        result.set_result(info)
                    elif isinstance(data, dict):
                        logger.info("Douyin browser returned no matching video; status_code=%s", data.get("status_code"))
                except Exception:
                    logger.debug("Douyin browser response did not contain usable video metadata")

            page.on("response", read_response)
            try:
                navigation = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                logger.info("Douyin browser page HTTP %s for %s", navigation.status if navigation else None, video_id)
                return await asyncio.wait_for(asyncio.shield(result), timeout=30)
            except Exception as exc:
                if result.done() and not result.cancelled():
                    return result.result()
                logger.warning("Douyin browser ended without video: %s", type(exc).__name__)
                raise ValueError(
                    "Douyin belum memberikan video ke browser server tanpa login. "
                    "Coba lagi nanti atau gunakan postingan lain yang bisa diputar di browser tanpa login."
                ) from exc
            finally:
                if not result.done():
                    result.cancel()
        finally:
            await browser.close()
