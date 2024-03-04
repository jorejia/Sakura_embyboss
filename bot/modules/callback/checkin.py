import asyncio
import random
from datetime import datetime, timezone, timedelta

from pyrogram import filters

from bot import bot, _open, sakura_b
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.msg_utils import callAnswer, sendMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby


@bot.on_callback_query(filters.regex('checkin') & user_in_group_on_filter)
async def user_in_checkin(_, call):
    if _open.checkin:
        e = sql_get_emby(call.from_user.id)
        now = datetime.now(timezone(timedelta(hours=8)))
        if not e:
            return await callAnswer(call, '🧮 未查询到数据库', True)
        elif not e.ch or e.ch.strftime("%Y-%m-%d") < now.strftime("%Y-%m-%d"):
            if e.ex and e.ex.strftime("%Y-%m-%d") > now.strftime("%Y-%m-%d"):
                reward = random.randint(1, 5) * 2
                s = e.iv + reward
                sql_update_emby(Emby.tg == call.from_user.id, iv=s, ch=now)
                text = f'🎉 **签到成功** | + {reward} {sakura_b} （会员双倍）\n💴 **当前余额** | {s} {sakura_b}\n⏳ **签到日期** | {now.strftime("%Y-%m-%d")}'
                await asyncio.gather(call.message.delete(), sendMessage(call, text=text))
            else:
                reward = random.randint(1, 5)
                s = e.iv + reward
                sql_update_emby(Emby.tg == call.from_user.id, iv=s, ch=now)
                text = f'🎉 **签到成功** | + {reward} {sakura_b}\n💴 **当前余额** | {s} {sakura_b}\n⏳ **签到日期** | {now.strftime("%Y-%m-%d")}'
                await asyncio.gather(call.message.delete(), sendMessage(call, text=text))                
        else:
            await callAnswer(call, '⭕ 您今天已经签到过了！签到是无聊的活动哦。', True)
    else:
        await callAnswer(call, '❌ 未开启签到系统，等待！', True)
