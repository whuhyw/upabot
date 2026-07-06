import os

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter


def main() -> None:
    nonebot.init()
    nonebot.load_plugin("nonebot_plugin_orm")
    nonebot.load_plugin("duckbot.plugins.music_converter")
    nonebot.load_plugin("duckbot.plugins.device_commands")
    nonebot.load_plugin("duckbot.plugins.taboo")
    driver = nonebot.get_driver()
    driver.register_adapter(OneBotV11Adapter)
    nonebot.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8080")))


if __name__ == "__main__":
    main()
