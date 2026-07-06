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


async def get_or_create_setting(session: AsyncSession, user_qq: int):
    result = await session.execute(
        select(TabooSetting).where(TabooSetting.user_qq == user_qq)
    )
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = TabooSetting(user_qq=user_qq, enabled=True)
        session.add(setting)
    return setting


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
            await taboo_matcher.finish(HELP_TEXT)

        parts = text.split(maxsplit=1)
        subcmd = parts[0].lower()
        subarg = parts[1].strip() if len(parts) > 1 else ""

        user_qq = int(event.get_user_id())

        if subcmd in ("reg", "register", "add"):
            if not subarg:
                await taboo_matcher.finish("请指定关键词，格式: /taboo reg <关键词>")

            existing = await session.execute(
                select(TabooKeyword).where(TabooKeyword.keyword == subarg)
            )
            if existing.scalar_one_or_none():
                await taboo_matcher.finish(f"关键词「{subarg}」已被其他人注册")

            await get_or_create_setting(session, user_qq)
            session.add(TabooKeyword(user_qq=user_qq, keyword=subarg))
            await session.commit()
            await taboo_matcher.finish(
                f"关键词「{subarg}」注册成功！\n"
                "当群聊中有人提及此关键词且监控开启时，将转发聊天记录到您的私信。"
            )

        elif subcmd in ("unreg", "unregister", "remove", "del", "delete"):
            if not subarg:
                await taboo_matcher.finish("请指定关键词，格式: /taboo unreg <关键词>")

            result = await session.execute(
                select(TabooKeyword).where(
                    TabooKeyword.user_qq == user_qq,
                    TabooKeyword.keyword == subarg,
                )
            )
            record = result.scalar_one_or_none()
            if not record:
                await taboo_matcher.finish(f"您未注册关键词「{subarg}」")

            await session.delete(record)
            await session.commit()
            await taboo_matcher.finish(f"关键词「{subarg}」已取消注册")

        elif subcmd in ("list", "ls"):
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

        elif subcmd in ("on", "enable"):
            setting = await get_or_create_setting(session, user_qq)
            if setting.enabled:
                await taboo_matcher.finish("监控已开启，无需重复操作")
            setting.enabled = True
            await session.commit()
            await taboo_matcher.finish("Taboo 监控已开启")

        elif subcmd in ("off", "disable"):
            setting = await get_or_create_setting(session, user_qq)
            if not setting.enabled:
                await taboo_matcher.finish("监控已关闭，无需重复操作")
            setting.enabled = False
            await session.commit()
            await taboo_matcher.finish("Taboo 监控已关闭")

        elif subcmd in ("help", "h", "-h", "--help"):
            await taboo_matcher.finish(HELP_TEXT)

        else:
            await taboo_matcher.finish(f"未知命令: {subcmd}\n{HELP_TEXT}")

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"[Taboo] Command error: {e}\n{traceback.format_exc()}")
        await taboo_matcher.finish(f"处理出错: {e}")


group_handler = on_message(priority=10)


@group_handler.handle()
async def handle_group_message(
    bot: Bot,
    event: GroupMessageEvent,
    session: AsyncSession = Depends(get_session),
):
    try:
        text = event.get_plaintext()

        result = await session.execute(select(TabooKeyword))
        keywords = result.scalars().all()

        matched = [kw for kw in keywords if kw.keyword in text]
        if not matched:
            return

        try:
            history = await bot.call_api(
                "get_group_msg_history",
                group_id=event.group_id,
                count=10,
            )
        except Exception:
            history = {"messages": []}

        nodes = []
        for msg in history.get("messages", []):
            sender_id = msg.get("sender", {}).get("user_id", 0)
            if sender_id == int(bot.self_id):
                continue

            nickname = (
                msg.get("sender", {}).get("card")
                or msg.get("sender", {}).get("nickname")
                or str(sender_id)
            )
            content = msg.get("message", [])
            if content:
                nodes.append(
                    MessageSegment.node_custom(
                        user_id=sender_id,
                        nickname=nickname,
                        content=Message(content),
                    )
                )

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
                if nodes:
                    await bot.send_private_forward_msg(
                        user_id=kw.user_qq,
                        messages=nodes,
                    )
                else:
                    await bot.send_private_msg(
                        user_id=kw.user_qq,
                        message=f"有人在群 {event.group_id} 中提到了「{kw.keyword}」",
                    )
            except Exception as e:
                logger.warning(f"[Taboo] Failed to notify {kw.user_qq}: {e}")

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"[Taboo] Group handler error: {e}\n{traceback.format_exc()}")
