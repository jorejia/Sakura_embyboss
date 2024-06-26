"""
对用户分数调整
score +-

对用户sakura_b币调整
coins +-
"""
import asyncio

from pyrogram import filters
from pyrogram.errors import BadRequest
from bot import bot, prefixes, LOGGER, sakura_b
from bot.func_helper.filters import admins_on_filter
from bot.func_helper.msg_utils import sendMessage, deleteMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.func_helper.fix_bottons import group_f


async def get_user_input(msg):
    gm_name = msg.sender_chat.title if msg.sender_chat else f'管理员 [{msg.from_user.first_name}]({msg.from_user.id})'
    if msg.reply_to_message is None:
        try:
            uid = int(msg.command[1])
            b = int(msg.command[2])
            first = await bot.get_chat(uid)
        except (IndexError, KeyError, BadRequest, ValueError, AttributeError):
            await deleteMessage(msg)
            return None, None, None, gm_name
    else:
        try:
            first = msg.reply_to_message.from_user
            uid = first.id
            b = int(msg.command[1])
        except (IndexError, ValueError, AttributeError):
            await deleteMessage(msg)
            return None, None, None, gm_name
    return uid, b, first, gm_name


@bot.on_message(filters.command('score', prefixes=prefixes) & admins_on_filter)
async def score_user(_, msg):
    uid, b, first, gm_name = await get_user_input(msg)
    if not first:
        return await sendMessage(msg,
                                 "🔔 **调整积分：**\n\n`/score` [tg_id] [+/-积分]\n或回复某人，请确认对象正确",
                                 timer=20)
    e = sql_get_emby(tg=uid)
    if not e:
        return await sendMessage(msg, f"数据库中没有[ta](tg://user?id={uid}) 。请先私聊我", buttons=group_f)

    us = e.us + b
    if sql_update_emby(Emby.tg == uid, us=us):
        await asyncio.gather(sendMessage(msg,
                                         f"· 🎯 {gm_name} 调节了 [{first.first_name}](tg://user?id={uid}) 积分： {b}"
                                         f"\n· 🎟️ 实时积分: **{us}**"),
                             msg.delete())
        LOGGER.info(f"【admin】[积分]：{gm_name} 对 {first.first_name}-{uid}  {b}分  ")
    else:
        await sendMessage(msg, '⚠️ 数据库操作失败，请检查')
        LOGGER.info(f"【admin】[积分]：{gm_name} 对 {first.first_name}-{uid} 数据操作失败")


@bot.on_message(filters.command('coins', prefixes=prefixes) & admins_on_filter)
async def coins_user(_, msg):
    uid, b, first, gm_name = await get_user_input(msg)
    if not first:
        return await sendMessage(msg,
                                 "🔔 **调整米币：**\n\n`/coins` [tg_id] [+/-米币]\n或回复某人，请确认对象正确",
                                 timer=20)

    e = sql_get_emby(tg=uid)
    if not e:
        return await sendMessage(msg, f"数据库中没有[ta](tg://user?id={uid}) 。请先私聊我", buttons=group_f)

    # 加上判定send_chat
    us = e.iv + b
    if sql_update_emby(Emby.tg == uid, iv=us):
        await asyncio.gather(sendMessage(msg,
                                         f"· 🎯 恭喜 [{first.first_name}](tg://user?id={uid}) 获得了{b}{sakura_b}奖励\n"
                                         f"· 😍😍 羡慕死了~"),
                             msg.delete())
        LOGGER.info(
            f"【admin】[{sakura_b}]- {gm_name} 对 {first.first_name}-{uid}  {b}{sakura_b}")
    else:
        await sendMessage(msg, '⚠️ 数据库操作失败，请检查')
        LOGGER.info(f"【admin】[{sakura_b}]：{gm_name} 对 {first.first_name}-{uid} 数据操作失败")
