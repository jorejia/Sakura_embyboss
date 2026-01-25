"""
服务器讯息打印

"""
from datetime import datetime, timezone, timedelta
from pyrogram import filters
from bot import bot, emby_line, _open
from bot.func_helper.emby import emby
from bot.func_helper.filters import user_in_group_on_filter
from bot.sql_helper.sql_emby import sql_get_emby
from bot.func_helper.fix_bottons import cr_page_server
from bot.func_helper.msg_utils import callAnswer, editMessage


@bot.on_callback_query(filters.regex('server') & user_in_group_on_filter)
async def server(_, call):
    data = sql_get_emby(tg=call.from_user.id)
    if not data:
        return await editMessage(call, '⚠️ 数据库没有你，请重新 /start录入')
    await callAnswer(call, '🌐查询中...')
    try:
        j = int(call.data.split(':')[1])
    except IndexError:
        # 第一次查看
        send = await editMessage(call, "**▎🌐查询中...\n\nο(=•ω＜=)ρ⌒☆ 发送bibo电波~bibo~ \n⚡ 点击按钮查看相应服务器状态**")
        if send is False:
            return

        keyboard, sever = await cr_page_server()
        server_info = sever[0]['server'] if sever == '' else ''
    else:
        keyboard, sever = await cr_page_server()
        server_info = ''.join([item['server'] for item in sever if item['id'] == j])

    pwd = '空' if not data.pwd else data.pwd
    all_user = _open.all_user
    emby_user = _open.tem
    try:
        online = emby.get_current_playing_count()
    except:
        online = 'Emby服务器断连 ·0'
    text = f'**▎服务器地址见用户手册\n\n' \
           f'{server_info}' \
           f'· 🎫 总上限 | **{all_user}**\n· 🎟️ 已注册 | **{emby_user}**\n' \
           f'· 🎬 正在播放 | **{online}** 人\n\n' \
           f'**· 🌏 [{(datetime.now(timezone(timedelta(hours=8)))).strftime("%Y-%m-%d %H:%M:%S")}]**'
    await editMessage(call, text, buttons=keyboard)
