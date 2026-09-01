import traceback

from nonebot import logger, on_command, on_message
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.exception import FinishedException
from nonebot.params import CommandArg, Depends
from nonebot.plugin import PluginMetadata
from nonebot_plugin_orm import Model, get_session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from .image_gen import render_chat_image
from .message_cache import ChatMessage, MessageCache

__plugin_meta__ = PluginMetadata(
    name="Taboo",
    description="哈利·波特式禁忌词监控 - 群聊提及关键词时私信通知",
    usage=(
        "命令前缀: /taboo 或 /tb\n"
        "  reg <关键词>     注册关键词\n"
        "  unreg <关键词>   取消关键词\n"
        "  list / ls        查看已注册的关键词\n"
        "  on               开启监控 (默认)\n"
        "  off              关闭监控 (临时)\n"
        "当群聊中有人提及你的关键词且监控开启时，机器人会转发聊天记录到你的私信"
    ),
)


class TabooKeyword(Model):
    __tablename__ = "taboo_keywords"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_qq: Mapped[int] = mapped_column()
    keyword: Mapped[str] = mapped_column(unique=True)


class TabooSetting(Model):
    __tablename__ = "taboo_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_qq: Mapped[int] = mapped_column(unique=True)
    enabled: Mapped[bool] = mapped_column(default=True)


HELP_TEXT = (
    "Taboo 使用说明:\n"
    "/taboo reg <关键词>   - 注册关键词\n"
    "/taboo unreg <关键词> - 取消关键词\n"
    "/taboo list          - 列出关键词 (/tb ls)\n"
    "/taboo on            - 开启监控\n"
    "/taboo off           - 关闭监控"
)

msg_cache = MessageCache()


async def get_or_create_setting(session: AsyncSession, user_qq: int) -> TabooSetting:
    result = await session.execute(
        select(TabooSetting).where(TabooSetting.user_qq == user_qq)
    )
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = TabooSetting(user_qq=user_qq, enabled=True)
        session.add(setting)
    return setting


# ---- Subcommand handlers ----

async def handle_reg(session: AsyncSession, user_qq: int, keyword: str) -> None:
    if not keyword:
        await taboo_matcher.finish("请指定关键词，格式: /taboo reg <关键词>")

    existing = await session.execute(
        select(TabooKeyword).where(TabooKeyword.keyword == keyword)
    )
    if existing.scalar_one_or_none():
        await taboo_matcher.finish(f"关键词「{keyword}」已被其他人注册")

    await get_or_create_setting(session, user_qq)
    session.add(TabooKeyword(user_qq=user_qq, keyword=keyword))
    await session.commit()
    await taboo_matcher.finish(
        f"关键词「{keyword}」注册成功！\n"
        "当群聊中有人提及此关键词且监控开启时，将转发聊天记录到您的私信。"
    )


async def handle_unreg(session: AsyncSession, user_qq: int, keyword: str) -> None:
    if not keyword:
        await taboo_matcher.finish("请指定关键词，格式: /taboo unreg <关键词>")

    result = await session.execute(
        select(TabooKeyword).where(
            TabooKeyword.user_qq == user_qq,
            TabooKeyword.keyword == keyword,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        await taboo_matcher.finish(f"您未注册关键词「{keyword}」")

    await session.delete(record)
    await session.commit()
    await taboo_matcher.finish(f"关键词「{keyword}」已取消注册")


async def handle_list(session: AsyncSession, user_qq: int, _: str = "") -> None:
    result = await session.execute(
        select(TabooKeyword).where(TabooKeyword.user_qq == user_qq)
    )
    keywords = result.scalars().all()
    if not keywords:
        await taboo_matcher.finish("您尚未注册任何关键词")

    kw_list = "\n".join(
        f"  {i + 1}. {kw.keyword}" for i, kw in enumerate(keywords)
    )
    await taboo_matcher.finish(f"您已注册的关键词:\n{kw_list}")


async def handle_on(session: AsyncSession, user_qq: int, _: str = "") -> None:
    setting = await get_or_create_setting(session, user_qq)
    if setting.enabled:
        await taboo_matcher.finish("监控已开启，无需重复操作")
    setting.enabled = True
    await session.commit()
    await taboo_matcher.finish("Taboo 监控已开启")


async def handle_off(session: AsyncSession, user_qq: int, _: str = "") -> None:
    setting = await get_or_create_setting(session, user_qq)
    if not setting.enabled:
        await taboo_matcher.finish("监控已关闭，无需重复操作")
    setting.enabled = False
    await session.commit()
    await taboo_matcher.finish("Taboo 监控已关闭")


async def show_help(_session: AsyncSession = None, _user_qq: int = 0, prefix: str = "") -> None:
    msg = HELP_TEXT
    if prefix:
        msg = f"{prefix}\n\n{HELP_TEXT}"
    await taboo_matcher.finish(msg)


# ---- Command dispatcher ----

CMD_MAP = {
    "reg": handle_reg, "register": handle_reg, "add": handle_reg,
    "unreg": handle_unreg, "unregister": handle_unreg,
    "remove": handle_unreg, "del": handle_unreg, "delete": handle_unreg,
    "list": handle_list, "ls": handle_list,
    "on": handle_on, "enable": handle_on,
    "off": handle_off, "disable": handle_off,
    "help": show_help, "h": show_help,
}

taboo_matcher = on_command("taboo", aliases={"tb"}, priority=5, block=True)


@taboo_matcher.handle()
async def handle_taboo_command(
    bot: Bot,
    event: PrivateMessageEvent,
    arg: Message = CommandArg(),
    session: AsyncSession = Depends(get_session),
):
    try:
        if not isinstance(event, PrivateMessageEvent):
            await taboo_matcher.finish("请在私聊中使用 Taboo 命令")

        text = arg.extract_plain_text().strip()
        if not text:
            await show_help()

        parts = text.split(maxsplit=1)
        subcmd = parts[0].lower()
        subarg = parts[1].strip() if len(parts) > 1 else ""
        user_qq = int(event.get_user_id())

        handler = CMD_MAP.get(subcmd)
        if handler:
            # pass a dummy arg for handlers that accept keyword arg
            await handler(session, user_qq, subarg)
        else:
            await show_help(prefix=f"未知命令: {subcmd}")

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"[Taboo] Command error: {e}\n{traceback.format_exc()}")
        await taboo_matcher.finish(f"处理出错: {e}")


# ---- Group message monitoring ----

group_handler = on_message(priority=10)


@group_handler.handle()
async def handle_group_message(
    bot: Bot,
    event: GroupMessageEvent,
    session: AsyncSession = Depends(get_session),
):
    try:
        text = event.get_plaintext()

        # Cache this message for context
        msg_cache.add(
            event.group_id,
            ChatMessage(
                user_id=event.sender.user_id,
                nickname=event.sender.card or event.sender.nickname
                or str(event.sender.user_id),
                text=text,
                time=event.time,
            ),
        )

        # Check if any registered keywords match
        result = await session.execute(select(TabooKeyword))
        keywords = result.scalars().all()

        matched = [kw for kw in keywords if kw.keyword in text]
        if not matched:
            return

        msg_cache.mark_last_as_trigger(event.group_id)
        context = msg_cache.get_context(event.group_id, count=10)

        try:
            group_info = await bot.call_api("get_group_info", group_id=event.group_id)
            group_name = group_info.get("group_name", str(event.group_id))
        except Exception:
            group_name = str(event.group_id)

        try:
            img_b64 = await render_chat_image(
                keyword=matched[0].keyword,
                messages=context,
                group_name=group_name,
            )
        except Exception as e:
            logger.error(f"[Taboo] Image render failed: {e}")
            await bot.send_private_msg(
                user_id=event.get_user_id(),
                message=f"有人在群 {group_name} 中提到了「{matched[0].keyword}」",
            )
            return

        notified = set()
        for kw in matched:
            if kw.user_qq in notified:
                continue
            notified.add(kw.user_qq)

            if int(event.get_user_id()) == kw.user_qq:
                continue

            setting_result = await session.execute(
                select(TabooSetting).where(TabooSetting.user_qq == kw.user_qq)
            )
            setting = setting_result.scalar_one_or_none()
            if setting is not None and not setting.enabled:
                continue

            try:
                await bot.send_private_msg(
                    user_id=kw.user_qq,
                    message=MessageSegment.image(file=img_b64),
                )
            except Exception as e:
                logger.warning(f"[Taboo] Failed to notify {kw.user_qq}: {e}")

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"[Taboo] Group handler error: {e}\n{traceback.format_exc()}")
