import asyncio
import json
import os
import traceback

import httpx

from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, PrivateMessageEvent
from nonebot.exception import FinishedException
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="DeviceStatus",
    description="查询 UPA 设备状态",
    usage="/upa status",
)

DEVICE_STATUS_API_URL = os.getenv(
    "DEVICE_STATUS_API_URL", "http://localhost:5000/DeviceStatus"
)

logger.info(f"[DeviceStatus] API URL: {DEVICE_STATUS_API_URL}")

status_matcher = on_message(priority=10)


def format_status(data: dict) -> str:
    mem = data["memory"]
    storage = data["storage"]
    lines = [
        f'CPU 温度: {data["cpuTemperatureCelsius"]}°C',
        f'运行时间: {data["uptime"]}',
        f'设备型号: {data["model"]}',
        f'系统版本: {data["osVersion"]}',
        f'IP 地址: {data["ip"]}',
        "",
        f'内存: {mem["usedMB"]}MB / {mem["totalMB"]}MB ({mem["usagePercentage"]:.1f}%)',
        f'存储: {storage["usedGB"]}GB / {storage["totalGB"]}GB ({storage["usagePercentage"]:.1f}%)',
    ]
    return "\n".join(lines)


@status_matcher.handle()
async def handle_upa_status(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent):
    try:
        text = event.get_plaintext().strip()
        parts = text.split()
        if len(parts) < 2 or parts[0] != "/upa" or parts[1] != "status":
            return

        resp = await asyncio.to_thread(
            httpx.get, DEVICE_STATUS_API_URL, timeout=10.0
        )
        resp.raise_for_status()
        data = resp.json()

        await status_matcher.finish(f"UPA 设备状态:\n{format_status(data)}")
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"[DeviceStatus] Error: {e}\n{traceback.format_exc()}")
        await status_matcher.finish(f"查询设备状态失败: {e}")
