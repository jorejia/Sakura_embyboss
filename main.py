#! /usr/bin/python3
# -*- coding: utf-8 -*-
import asyncio

import uvloop

uvloop.install()
from bot import api, bot, config, LOGGER
from bot.scheduler import BotCommands
from pyrogram import idle

# 面板
from bot.modules.panel import *
# 命令
from bot.modules.commands import *
# 其他
from bot.modules.extra import *
from bot.modules.callback import *

if api.status:
    from bot.web import *


def _proxy_log_text():
    proxy = config.proxy
    if not proxy or not proxy.scheme:
        return "未配置代理，当前为直连 Telegram"
    auth = "已配置账号密码" if proxy.username or proxy.password else "未配置账号密码"
    return f"scheme={proxy.scheme}, host={proxy.hostname}, port={proxy.port}, {auth}"


async def main():
    started = False
    try:
        await bot.start()
        started = True

        try:
            await BotCommands.set_commands(bot)
        except Exception as e:
            LOGGER.exception(f"【Telegram连接】设置 Bot 命令菜单失败，可能是 Telegram 网络/API 问题：{type(e).__name__}: {e}")
            raise

        await idle()
    except TimeoutError as e:
        LOGGER.exception(f"【Telegram连接阶段】bot.start() 建立 Telegram MTProto 会话时超时。连接对象是 Telegram 数据中心，不是 Emby/Sidecar/WebHook。{_proxy_log_text()}。错误：{e}")
        raise
    except OSError as e:
        LOGGER.exception(f"【Telegram连接阶段】bot.start() 建立 Telegram MTProto 会话时发生系统网络错误。连接对象是 Telegram 数据中心，不是 Emby/Sidecar/WebHook。{_proxy_log_text()}。错误：{type(e).__name__}: {e}")
        raise
    except Exception as e:
        LOGGER.exception(f"【Telegram连接阶段】bot.start()/idle() 期间失败。若前面出现 Unable to connect due to network issues，这是 Pyrogram 连接 Telegram MTProto 数据中心失败，不是 Emby/Sidecar/WebHook。{_proxy_log_text()}。错误：{type(e).__name__}: {e}")
        raise
    finally:
        if started:
            await bot.stop()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
