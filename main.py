#! /usr/bin/python3
# -*- coding: utf-8 -*-
import asyncio

import uvloop

uvloop.install()
from bot import api, bot
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


async def main():
    await bot.start()
    await BotCommands.set_commands(bot)
    await idle()
    await bot.stop()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
