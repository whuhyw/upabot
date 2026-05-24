import re
import traceback

from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, PrivateMessageEvent
from nonebot.exception import FinishedException
from nonebot.plugin import PluginMetadata

from .apple import extract_apple_music_metadata
from .netease import search_netease

__plugin_meta__ = PluginMetadata(
    name="MusicConverter",
    description="将 Apple Music 链接转换为网易云音乐链接",
    usage="发送 Apple Music 链接即可自动转换",
)

APPLE_MUSIC_PATTERN = re.compile(
    r"https?://music\.apple\.com/\w{2}/(?:album|song)/[^\s?/]+(?:/[^\s?/]+(?:\?[^\s]*)?)?"
)

music_matcher = on_message(priority=10)


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
        metadata = await extract_apple_music_metadata(url)
        if not metadata:
            logger.warning("[MusicConverter] Failed to extract metadata")
            await music_matcher.finish("无法解析该 Apple Music 链接。")

        title, artist = metadata
        logger.info(f"[MusicConverter] Metadata: title={title!r}, artist={artist!r}")
        query = f"{title} {artist}" if artist else title
        result = await search_netease(query)
        if not result:
            msg = f"未在网易云音乐找到匹配歌曲: {title}"
            if artist:
                msg += f" - {artist}"
            logger.warning(f"[MusicConverter] NetEase search no results: {msg}")
            await music_matcher.finish(msg)

        name, song_id = result
        reply = (
            f"Apple Music → 网易云音乐\n"
            f"原曲: {title} - {artist}\n"
            f"匹配: {name}\n"
            f"https://music.163.com/#/song?id={song_id}"
        )
        logger.info(f"[MusicConverter] Sending reply: {reply}")
        await music_matcher.finish(reply)
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"[MusicConverter] Error: {e}\n{traceback.format_exc()}")
        await music_matcher.finish(f"处理出错: {e}")
