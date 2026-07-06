import os
import traceback

import httpx
from nonebot import logger, on_command
from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent
from nonebot.exception import FinishedException
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="Device Commands",
    description="和 Uparupa 本身有关的命令",
    usage="/upa args",
)

DEVICE_STATUS_API_URL = os.getenv(
    "DEVICE_STATUS_API_URL", "http://host.docker.internal:5000/DeviceStatus"
)

logger.info(f"[DeviceCommands] Status API URL: {DEVICE_STATUS_API_URL}")

status_matcher = on_command("upa")


def format_status(data: dict) -> str:
    mem = data["memory"]
    storage = data["storage"]
    lines = [
        f"CPU 温度: {data['cpuTemperatureCelsius']}°C",
        f"运行时间: {data['uptime']}",
        f"设备型号: {data['model']}",
        f"系统版本: {data['osVersion']}",
        f"IP 地址: {data['ip']}",
        "",
        f"内存: {mem['usedMB']}MB / {mem['totalMB']}MB ({mem['usagePercentage']:.1f}%)",
        f"存储: {storage['usedGB']}GB / {storage['totalGB']}GB ({storage['usagePercentage']:.1f}%)",
    ]
    return "\n".join(lines)


async def handle_status():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(DEVICE_STATUS_API_URL)
        resp.raise_for_status()
        data = resp.json()

        await status_matcher.finish(f"Upa 设备状态:\n{format_status(data)}")
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"[DeviceCommands] Error: {e}\n{traceback.format_exc()}")
        await status_matcher.finish(f"查询设备状态失败 ({DEVICE_STATUS_API_URL}): {e}")


@status_matcher.handle()
async def upa_commands_handler(bot: Bot, event: PrivateMessageEvent):
    text = event.get_plaintext().strip()
    parts = text.split()[1:]

    if len(parts) == 0:
        return

    if parts[0] == "status":
        await handle_status()
