"""
可调节设置
此处为控制面板2，主要是为了在bot中能够设置一些变量
部分目前有 导出日志，更改emby线路，设置购买按钮

"""
from bot import bot, prefixes, bot_photo, Now, LOGGER, config, save_config, _open, user_buy
from pyrogram import filters

from bot.func_helper.filters import admins_on_filter
from bot.func_helper.fix_bottons import config_preparation, close_it_ikb, back_config_p_ikb, back_set_ikb, try_set_buy
from bot.func_helper.msg_utils import deleteMessage, editMessage, callAnswer, callListen, sendPhoto, sendFile


@bot.on_message(filters.command('config', prefixes=prefixes) & admins_on_filter)
async def config_p_set(_, msg):
    await deleteMessage(msg)
    await sendPhoto(msg, photo=bot_photo, caption="🌸 欢迎回来！\n\n👇点击你要修改的内容。",
                    buttons=config_preparation())


@bot.on_callback_query(filters.regex('back_config') & admins_on_filter)
async def config_p_re(_, call):
    await callAnswer(call, "✅ config")
    await editMessage(call, "🌸 欢迎回来！\n\n👇点击你要修改的内容。", buttons=config_preparation())


@bot.on_callback_query(filters.regex("log_out") & admins_on_filter)
async def log_out(_, call):
    await callAnswer(call, '🌐查询中...')
    # file位置以main.py为准
    send = await sendFile(call, file=f"log/log_{Now:%Y%m%d}.txt", file_name=f'log_{Now:%Y-%m-%d}.txt',
                          caption="📂 **导出日志成功！**", buttons=close_it_ikb)
    if send is not True:
        return LOGGER.info(f"【admin】：{call.from_user.id} - 导出日志失败！")

    LOGGER.info(f"【admin】：{call.from_user.id} - 导出日志成功！")


# 设置 emby 线路
@bot.on_callback_query(filters.regex('set_line') & admins_on_filter)
async def set_emby_line(_, call):
    await callAnswer(call, '📌 设置emby线路')
    send = await editMessage(call,
                             "💘【设置线路】\n\n对我发送向emby用户展示的emby地址吧\n取消点击 /cancel")
    if send is False:
        return

    txt = await callListen(call, 120, buttons=back_set_ikb('set_line'))
    if txt is False:
        return

    elif txt.text == '/cancel':
        await txt.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**', buttons=back_set_ikb('set_line'))
    else:
        await txt.delete()
        config.emby_line = txt.text
        save_config()
        await editMessage(call, f"**【网址样式】:** \n\n{config.emby_line}\n\n设置完成！done！",
                          buttons=back_config_p_ikb)
        LOGGER.info(f"【admin】：{call.from_user.id} - 更新emby线路为{config.emby_line}设置完成")


# 设置需要显示/隐藏的库
@bot.on_callback_query(filters.regex('set_block') & admins_on_filter)
async def set_block(_, call):
    await callAnswer(call, '📺 设置显隐媒体库')
    send = await editMessage(call,
                             "🎬**【设置需要显示/隐藏的库】**\n\n对我发送库的名字，多个**中文逗号**隔开\n例: `SGNB 特效电影，纪录片`\n超时自动退出 or 点 /cancel 退出")
    if send is False:
        return

    txt = await callListen(call, 120)
    if txt is False:
        return await config_p_re(_, call)

    elif txt.text == '/cancel':
        # config.emby_block = []
        # save_config()
        await txt.delete()
        return await config_p_re(_, call)
        # await editMessage(call, '__已清空并退出，__ **会话已结束！**', buttons=back_set_ikb('set_block'))
        # LOGGER.info(f"【admin】：{call.from_user.id} - 清空 指定显示/隐藏内容库 设置完成")
    else:
        c = txt.text.split("，")
        config.emby_block = c
        save_config()
        await txt.delete()
        await editMessage(call, f"🎬 指定显示/隐藏内容如下: \n\n{'.'.join(config.emby_block)}\n设置完成！done！",
                          buttons=back_config_p_ikb)
        LOGGER.info(f"【admin】：{call.from_user.id} - 更新指定显示/隐藏内容库为 {config.emby_block} 设置完成")


@bot.on_callback_query(filters.regex("set_buy") & admins_on_filter)
async def set_buy(_, call):
    if user_buy.stat:
        user_buy.stat = False
        save_config()
        await callAnswer(call, '**👮🏻‍♂️ 已经为您关闭购买按钮啦！**')
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} - 关闭了购买按钮")
        return await config_p_re(_, call)

    user_buy.stat = True
    await editMessage(call, '**👮🏻‍♂️ 已经为您开启购买按钮啦！目前默认只使用一个按钮，如果需求请github联系**\n'
                            '- 更换按钮请输入格式形如： \n\n`[按钮文字描述] - http://xxx`\n'
                            '- 退出状态请按 /cancel，需要markdown效果的话请在配置文件更改')
    save_config()
    LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} - 开启了购买按钮")

    txt = await callListen(call, 120, buttons=back_set_ikb('set_buy'))
    if txt is False:
        return

    elif txt.text == '/cancel':
        await txt.delete()
        await editMessage(call, '__您已经取消输入__ 退出状态。', buttons=back_config_p_ikb)
    else:
        await txt.delete()
        try:
            buy_text, buy_button = txt.text.replace(' ', '').split('-')
        except (IndexError, TypeError):
            await editMessage(call, f"**格式有误，您的输入：**\n\n{txt.text}", buttons=back_set_ikb('set_buy'))
        else:
            d = [buy_text, buy_button, 'url']
            keyboard = try_set_buy(d)
            edt = await editMessage(call, "**🫡 按钮效果如下：**\n可点击尝试，确认后返回",
                                    buttons=keyboard)
            if edt is False:
                LOGGER.info(f'【admin】：{txt.from_user.id} - 更新了购买按钮设置 失败')
                return await editMessage(call, "可能输入的link格式错误，请重试。http/https+link",
                                         buttons=back_config_p_ikb)
            user_buy.button = d
            save_config()
            LOGGER.info(f'【admin】：{txt.from_user.id} - 更新了购买按钮设置 {user_buy.button}')


@bot.on_callback_query(filters.regex('open_allow_code') & admins_on_filter)
async def open_allow_code(_, call):
    if _open.allow_code:
        _open.allow_code = False
        await callAnswer(call, '**👮🏻‍♂️ 您已调整 注册码续期 Falese（关闭）**', True)
        await config_p_re(_, call)
        save_config()
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 已调整 注册码续期 Falese")
    elif not _open.allow_code:
        _open.allow_code = True
        await callAnswer(call, '**👮🏻‍♂️ 您已调整 注册码续期 True（开启）**', True)
        await config_p_re(_, call)
        save_config()
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 已调整 注册码续期 True")


@bot.on_callback_query(filters.regex('change_site_open') & admins_on_filter)
async def change_site_open(_, call):
    if _open.site:
        _open.site = False
        await callAnswer(call, '**👮🏻‍♂️ 站点已进入隐身模式**', True)
        await config_p_re(_, call)
        save_config()
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 调整站点进入隐身模式")
    elif not _open.site:
        _open.site = True
        await callAnswer(call, '**👮🏻‍♂️ 站点已进入正常模式**', True)
        await config_p_re(_, call)
        save_config()
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 调整站点进入正常模式")


@bot.on_callback_query(filters.regex('leave_ban') & admins_on_filter)
async def open_leave_ban(_, call):
    if _open.leave_ban:
        _open.leave_ban = False
        await callAnswer(call, '**👮🏻‍♂️ 您已关闭 退群封禁，用户退群bot将不会被封印了**', True)
        await config_p_re(_, call)
        save_config()
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 已调整 退群封禁设置 Falese")
    elif not _open.leave_ban:
        _open.leave_ban = True
        await callAnswer(call, '**👮🏻‍♂️ 您已开启 退群封禁，用户退群bot将会被封印，禁止入群**', True)
        await config_p_re(_, call)
        save_config()
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 已调整 退群封禁设置 True")


@bot.on_callback_query(filters.regex('set_uplays') & admins_on_filter)
async def open_leave_ban(_, call):
    if _open.uplays:
        _open.uplays = False
        await callAnswer(call, '**👮🏻‍♂️ 您已关闭 看片榜结算，自动召唤看片榜将不被计算积分**', True)
        await config_p_re(_, call)
        save_config()
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 已调整 看片榜结算 Falese")
    elif not _open.uplays:
        _open.uplays = True
        await callAnswer(call, '**👮🏻‍♂️ 您已开启 看片榜结算，自动召唤看片榜将会被计算积分**', True)
        await config_p_re(_, call)
        save_config()
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 已调整 看片榜结算 True")
