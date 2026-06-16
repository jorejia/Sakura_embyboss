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
        LOGGER.exception(f"【Telegram连接】连接 Telegram 超时。请检查服务器到 Telegram 的网络、config.json 的 proxy 配置、代理服务是否可用。{_proxy_log_text()}。错误：{e}")
        raise
    except OSError as e:
        LOGGER.exception(f"【Telegram连接】连接 Telegram 发生系统网络错误。请检查 DNS、路由、防火墙、代理端口。{_proxy_log_text()}。错误：{type(e).__name__}: {e}")
        raise
    except Exception as e:
        LOGGER.exception(f"【Telegram连接】Bot 启动/运行失败。{_proxy_log_text()}。错误：{type(e).__name__}: {e}")
        raise
    finally:
        if started:
            await bot.stop()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
