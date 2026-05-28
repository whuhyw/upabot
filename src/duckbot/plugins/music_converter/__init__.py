import re
import traceback
from typing import Optional

import httpx
from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, PrivateMessageEvent
from nonebot.exception import FinishedException
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="MusicConverter",
    description="将 Apple Music 链接转换为网易云音乐链接",
    usage="发送 Apple Music 链接即可自动转换",
)

APPLE_MUSIC_PATTERN = re.compile(
    r"https?://music\.apple\.com/\w{2}/(?:album|song)/[^\s?/]+(?:/[^\s?/]+(?:\?[^\s]*)?)?"
)

CONVERT_API = "https://duckran.top/api/music/convert"

music_matcher = on_message(priority=10)


async def convert_url(url: str) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(CONVERT_API, params={"url": url})
        resp.raise_for_status()
        return resp.json()


@music_matcher.handle()
async def handle_apple_music_link(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent):
    try:
        text = event.get_plaintext()
        logger.info(f"[MusicConverter] Received message: {text}")
        match = APPLE_MUSIC_PATTERN.search(text)
        if not match:
            logger.info("[MusicConverter] No Apple Music pattern match")
            return

        url = match.group(0)
        logger.info(f"[MusicConverter] Matched URL: {url}")

        data = await convert_url(url)
        if not data or not data.get("neteaseUrl"):
            logger.warning(f"[MusicConverter] API returned no result: {data}")
            await music_matcher.finish("无法转换该 Apple Music 链接。")

        title = data.get("name", "未知歌曲")
        artist = data.get("artist", "")
        netease_url = data["neteaseUrl"]

        reply = (
            f"Apple Music -> 网易云音乐\n"
            f"原曲: {title} - {artist}\n"
            f"{netease_url}"
        )
        logger.info(f"[MusicConverter] Sending reply: {reply}")
        await music_matcher.finish(reply)
    except FinishedException:
        raise
    except httpx.HTTPError as e:
        logger.error(f"[MusicConverter] API request failed: {e}\n{traceback.format_exc()}")
        await music_matcher.finish("转换服务暂时不可用，请稍后再试。")
    except Exception as e:
        logger.error(f"[MusicConverter] Error: {e}\n{traceback.format_exc()}")
        await music_matcher.finish(f"处理出错: {e}")
