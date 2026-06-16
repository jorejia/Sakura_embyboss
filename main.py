#! /usr/bin/python3
# -*- coding: utf-8 -*-
import asyncio
import socket

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


def _tcp_check(host, port, timeout=5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, None
    except OSError as e:
        return False, f"{type(e).__name__}: {e}"


def _check_telegram_network():
    proxy = config.proxy
    if proxy and proxy.scheme:
        if not proxy.hostname or not proxy.port:
            LOGGER.error(f"【Telegram网络诊断】已配置代理但 hostname/port 不完整。{_proxy_log_text()}")
            return

        ok, error = _tcp_check(proxy.hostname, proxy.port, timeout=5)
        if not ok:
            LOGGER.error(
                f"【Telegram网络诊断】代理端口不可达，Pyrogram 无法通过代理连接 Telegram。"
                f"{_proxy_log_text()}，错误：{error}"
            )
        return

    checks = [
        ("Telegram Bot API", "api.telegram.org", 443),
        ("Telegram MTProto DC1", "149.154.175.53", 443),
        ("Telegram MTProto DC2", "149.154.167.51", 443),
        ("Telegram MTProto DC4", "149.154.167.91", 443),
        ("Telegram MTProto DC5", "91.108.56.151", 443),
    ]
    failed = []
    for name, host, port in checks:
        ok, error = _tcp_check(host, port, timeout=5)
        if not ok:
            failed.append(f"{name} {host}:{port} -> {error}")

    if len(failed) == len(checks):
        LOGGER.error(
            "【Telegram网络诊断】当前未配置代理，且服务器直连 Telegram 全部失败。"
            "这通常表示服务器网络无法访问 Telegram，需要在 config.json 配置可用代理。"
            f"失败明细：{' | '.join(failed)}"
        )
    elif failed:
        LOGGER.warning(
            "【Telegram网络诊断】当前未配置代理，部分 Telegram 地址直连失败。"
            "如果随后出现 Connection timed out，优先检查服务器到 Telegram MTProto 的路由/防火墙。"
            f"失败明细：{' | '.join(failed)}"
        )


async def main():
    started = False
    try:
        _check_telegram_network()
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
