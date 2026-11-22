from datetime import timedelta, datetime

from pyrogram import filters
from pyrogram.errors import BadRequest

from bot import bot, prefixes, LOGGER
from bot.func_helper.emby import emby
from bot.func_helper.filters import admins_on_filter
from bot.func_helper.msg_utils import deleteMessage, sendMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby


async def get_user_input(msg):
    await deleteMessage(msg)
    gm_name = msg.sender_chat.title if msg.sender_chat else f'管理员 [{msg.from_user.first_name}]({msg.from_user.id})'
    if msg.reply_to_message is None:
        try:
            b = msg.command[1]  # name
            c = float(msg.command[2])  # 天数
        except (IndexError, KeyError, BadRequest, ValueError, AttributeError):
            return None, None, None
    else:
        try:
            b = msg.reply_to_message.from_user.id
            c = float(msg.command[1])
        except (IndexError, KeyError, BadRequest, ValueError, AttributeError):
            return None, None, None

    e = sql_get_emby(tg=b)
    if not e:
        await sendMessage(msg, f"♻️ 未检索到Emby {b}，请确认重试或手动检查。")
        return None, None, None

    return c, e, gm_name


@bot.on_message(filters.command('renew', prefixes) & admins_on_filter)
async def renew_user(_, msg):
    days, e, gm_name = await get_user_input(msg)
    if not e:
        return await sendMessage(msg,
                                 f"🔔 **使用格式：**\n\n/renew [Emby账户名] [+/-天数]\n或回复某人 /renew [+/-天数]",
                                 timer=60)
    reply = await msg.reply(f"🍓 正在处理ing···/·")
    try:
        name = f'[{e.name}]({e.tg})' if e.tg else e.name
    except:
        name = e.name
    # 时间是 utc 来算的
    Now = datetime.now()
    ex_new = Now + timedelta(days=days) if Now > e.ex else e.ex + timedelta(days=days)
    lv = e.lv
    if ex_new > Now:
        lv = 'a' if e.lv == 'a' else 'b'
    elif e.lv != 'a':
        lv = 'c'
    # 先改 sidecar 状态，确认成功后才写数据库；数据库写失败则把 sidecar 恢复到原状态
    disable = lv == 'c'
    was_disabled = e.lv == 'c'
    action = '禁用' if disable else '解封'
    if not await emby.emby_change_policy(e.embyid, method=disable):
        LOGGER.error(f"【admin】[renew]：{gm_name} 调整 {name} 失败：sidecar {action}未成功")
        return await reply.edit(f'❌ 调整失败：sidecar {action}未成功，到期时间未改动，请稍后重试。')
    if sql_update_emby(Emby.tg == e.tg, ex=ex_new, lv=lv) is not True:
        restored = disable == was_disabled or await emby.emby_change_policy(e.embyid, method=was_disabled)
        LOGGER.error(f"【admin】[renew]：{gm_name} 调整 {name} 数据库写入失败，sidecar 状态"
                     f"{'已恢复' if restored else '恢复失败，需人工核对'}")
        return await reply.edit('❌ 调整失败：数据库写入失败，到期时间未改动'
                                + ('' if restored else '；sidecar 状态恢复失败，请人工核对'))

    i = await reply.edit(
        f'🍒 __ {gm_name} 已调整 emby 用户 {name} 到期时间 {days} 天 (以当前时间计)__'
        f'\n📅 实时到期：{ex_new.strftime("%Y-%m-%d %H:%M:%S")}')
    try:
        await i.forward(e.tg)
    except:
        pass

    LOGGER.info(
        f"【admin】[renew]：{gm_name} 对 emby账户 {name} 调节 {days} 天，"
        f"实时到期：{ex_new.strftime('%Y-%m-%d %H:%M:%S')}")
