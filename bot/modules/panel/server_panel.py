"""
服务器信息面板

仅展示基础容量和当前播放信息，不再依赖探针。
"""
from datetime import datetime, timezone, timedelta

from pyrogram import filters

from bot import bot, _open
from bot.func_helper.emby import emby
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.fix_bottons import server_info_ikb
from bot.func_helper.msg_utils import callAnswer, editMessage
from bot.sql_helper.sql_emby import sql_get_emby


@bot.on_callback_query(filters.regex(r'^server$') & user_in_group_on_filter)
async def server(_, call):
    data = sql_get_emby(tg=call.from_user.id)
    if not data:
        return await editMessage(call, '⚠️ 数据库没有你，请重新 /start录入')

    await callAnswer(call, '🌐查询中...')

    all_user = _open.all_user
    emby_user = _open.tem
    remain_user = max(all_user - emby_user, 0)
    try:
        online = emby.get_current_playing_count()
    except Exception:
        online = 'Emby服务器断连 ·0'

    current_time = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    if data.embyid:
        text = f'**▎服务器地址见用户手册\n\n' \
               f'· 🎫 总上限 | **{all_user}**\n' \
               f'· 🎟️ 已注册 | **{emby_user}**\n' \
               f'· 🎬 正在播放 | **{online}** 人\n\n' \
               f'**· 🌏 [{current_time}]**'
    else:
        text = f'**▎服务器地址见用户手册\n\n' \
               f'· 💫 剩余可注册位置 | **{remain_user}**\n\n' \
               f'**· 🌏 [{current_time}]**'
    await editMessage(call, text, buttons=server_info_ikb)
