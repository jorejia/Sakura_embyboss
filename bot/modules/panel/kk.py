"""
kk - 纯装x
赠与账户，禁用，删除
"""
import pyrogram
from pyrogram import filters
from pyrogram.errors import BadRequest
from bot import bot, prefixes, owner, bot_photo, admins, LOGGER, default_line_id, line_options
from bot.func_helper.emby import emby
from bot.func_helper.filters import admins_on_filter
from bot.func_helper.fix_bottons import cr_kk_ikb, gog_rester_ikb
from bot.func_helper.line_access import first_pro_line, revoke_line_pro_access
from bot.func_helper.msg_utils import deleteMessage, sendMessage, sendPhoto, editMessage
from bot.func_helper.utils import judge_admins, cr_link_two
from bot.sql_helper.sql_emby import sql_get_emby, sql_grant_line_pro, sql_update_emby, Emby


async def _telegram_identity(tgid):
    """Telegram 无法识别时返回可用于 /kk 面板的占位名称。"""
    try:
        user = await bot.get_chat(tgid)
        name = getattr(user, 'first_name', None) or getattr(user, 'title', None) or '未识别'
        return True, name
    except Exception as error:
        LOGGER.warning(f'【/kk】Telegram 无法识别 {tgid}：{error}')
        return False, '未识别'


async def _refresh_kk_panel(call, tgid):
    _, first_name = await _telegram_identity(tgid)
    panel_text, keyboard = await cr_kk_ikb(tgid, first_name)
    return await editMessage(call, panel_text, buttons=keyboard)


# 管理用户
@bot.on_message(filters.command('kk', prefixes) & admins_on_filter)
async def user_info(_, msg):
    await deleteMessage(msg)
    if msg.reply_to_message is None:
        try:
            uid = int(msg.command[1])
        except (IndexError, KeyError, ValueError):
            return await sendMessage(msg, '🔔 **管理用户:**\n\n用法：`/kk` [tg_id]\n或者对某人回复', timer=20)

        if not msg.sender_chat and msg.from_user.id != owner and uid == owner:
            return await sendMessage(msg,
                                     f"⭕ [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})！不可以偷窥主人",
                                     timer=60)

        recognized, first_name = await _telegram_identity(uid)
        if not recognized and sql_get_emby(tg=uid) is None:
            return await sendMessage(msg, f'{uid} - 🎂Telegram 未识别，数据库也没有此ID', timer=20)

        text, keyboard = await cr_kk_ikb(uid, first_name)
        await sendPhoto(msg, photo=bot_photo, caption=text, buttons=keyboard)  # protect_content=True 移除禁止复制

    else:
        uid = msg.reply_to_message.from_user.id
        try:
            if msg.from_user.id != owner and uid == owner:
                return await msg.reply(
                    f"⭕ [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})！不可以偷窥主人")
        except AttributeError:
            pass

        # first = await bot.get_chat(uid)
        text, keyboard = await cr_kk_ikb(uid, msg.reply_to_message.from_user.first_name)
        await sendMessage(msg, text=text, buttons=keyboard)


@bot.on_message(filters.command('dd', prefixes) & admins_on_filter)
async def douban_info(_, msg):
    await deleteMessage(msg)
    if msg.reply_to_message is None:
        try:
            uid = int(msg.command[1])
            first = await bot.get_chat(uid)
        except (IndexError, KeyError, ValueError):
            return await sendMessage(msg, '🔔 **查询豆瓣ID:**\n\n用法：`/dd` [tg_id]\n或者对某人回复', timer=15)
        except BadRequest:
            return await sendMessage(msg, f'{msg.command[1]} - 🎂抱歉，此id未登记bot，或者id错误', timer=15)
        except AttributeError:
            return
    else:
        try:
            uid = msg.reply_to_message.from_user.id
            first = msg.reply_to_message.from_user
        except AttributeError:
            return await sendMessage(msg, '⛔ 这条消息没有可用的用户信息，请直接输入 tg_id', timer=15)

    e = sql_get_emby(tg=uid)
    if e is None:
        return await sendMessage(msg, f'⛔ [{first.first_name}](tg://user?id={uid}) 未登记 bot 数据', timer=15)
    if not e.douban:
        return await sendMessage(msg, f'⛔ [{first.first_name}](tg://user?id={uid}) 当前未绑定豆瓣ID', timer=15)
    await sendMessage(msg, f'`{e.douban}`', timer=15)


# 解除直连 Pro：与到期任务一致，先切回默认线路，再清除 Pro 到期时间。
@bot.on_callback_query(filters.regex(r'^line_pro_revoke-\d+$'))
async def revoke_line_pro(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    tgid = int(call.data.split("-")[1])
    if ((tgid == owner and call.from_user.id != owner)
            or (tgid in admins and tgid != call.from_user.id)):
        return await call.answer("机器人不可以解除其他 Bot 管理员的直连Pro", show_alert=True)

    user = sql_get_emby(tg=tgid)
    if user is None:
        return await call.answer("该用户没有 Bot 数据", show_alert=True)
    if user.line_pro_ex is None:
        return await call.answer("该用户当前未激活直连Pro", show_alert=True)

    revoked, failed_stage, result = await revoke_line_pro_access(
        user.embyid,
        default_line_id,
        emby.set_use_line,
        lambda: sql_update_emby(Emby.tg == tgid, line_pro_ex=None),
    )
    if not revoked and failed_stage == 'line':
        LOGGER.error(
            f"【直连Pro手动撤权】管理员 {call.from_user.id} 撤销 {tgid} 失败："
            f"切回默认线路 {default_line_id} 失败：{result}"
        )
        return await call.answer(
            f"切回默认线路 {default_line_id} 失败，Pro权限未清除：{result}",
            show_alert=True,
        )
    if not revoked:
        LOGGER.error(
            f"【直连Pro手动撤权】管理员 {call.from_user.id} 已将 {tgid} 切回默认线路，"
            "但清除 line_pro_ex 失败"
        )
        return await call.answer("已切回默认线路，但清除Pro权限失败，请重试", show_alert=True)

    await call.answer("✅ 已解除直连Pro")
    text = (
        f"管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) "
        f"已解除你的直连Pro权限，并切回默认线路 {default_line_id}。"
    )
    LOGGER.info(f"【直连Pro手动撤权】{call.from_user.id} 已解除 {tgid} 的直连Pro权限")
    try:
        await bot.send_message(tgid, text)
    except Exception as error:
        LOGGER.warning(f"【直连Pro手动撤权】通知用户 {tgid} 失败：{error}")

    try:
        await _refresh_kk_panel(call, tgid)
    except Exception as error:
        LOGGER.warning(f"【直连Pro手动撤权】刷新 /kk 面板失败：{error}")
        await editMessage(call, f"✅ 已解除用户 `{tgid}` 的直连Pro权限，并切回默认线路 {default_line_id}")


@bot.on_callback_query(filters.regex(r'^line_pro_grant-\d+$'))
async def grant_line_pro(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    tgid = int(call.data.split("-")[1])
    if ((tgid == owner and call.from_user.id != owner)
            or (tgid in admins and tgid != call.from_user.id)):
        return await call.answer("机器人不可以修改其他 Bot 管理员的直连Pro", show_alert=True)

    target_line = first_pro_line(line_options)
    if target_line is None:
        return await call.answer("配置中没有 Pro 线路，无法赋予权限", show_alert=True)

    result, expires_at, emby_id = sql_grant_line_pro(tgid, days=1)
    if result == 'not_found':
        return await call.answer("该用户没有 Bot 数据", show_alert=True)
    if result == 'no_account':
        return await call.answer("该用户尚未绑定 Emby 账号", show_alert=True)
    if result == 'already_active':
        await call.answer("该用户已经拥有有效直连Pro，面板已刷新", show_alert=True)
        await _refresh_kk_panel(call, tgid)
        return
    if result != 'success':
        return await call.answer("赋予直连Pro失败，请稍后重试", show_alert=True)

    switched, switch_result = await emby.set_use_line(emby_id, target_line.id)
    expires_text = expires_at.strftime('%Y-%m-%d %H:%M:%S')
    if switched:
        alert_text = f"✅ 已赋予直连Pro 1天，到期：{expires_text}\n已切换到 {target_line.name}"
    else:
        alert_text = (f"✅ 已赋予直连Pro 1天，到期：{expires_text}\n"
                      f"但自动切换到 {target_line.name} 失败，请手动处理")

    LOGGER.info(
        f"【直连Pro手动赋予】管理员 {call.from_user.id} 已赋予 {tgid} 1天权限，"
        f"到期时间：{expires_at}，自动切线结果：{switched}，详情：{switch_result}"
    )
    try:
        await bot.send_message(
            tgid,
            f"管理员已为你赋予直连Pro 1天，到期时间：{expires_text}。"
            f"{'已自动切换到 ' + target_line.name if switched else '自动切线失败，请在直连切线中手动选择。'}"
        )
    except Exception as error:
        LOGGER.warning(f"【直连Pro手动赋予】通知用户 {tgid} 失败：{error}")

    await call.answer(alert_text, show_alert=True)
    return await _refresh_kk_panel(call, tgid)


# 封禁或者解除
@bot.on_callback_query(filters.regex('user_ban'))
async def kk_user_ban(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    await call.answer("✅ ok")
    b = int(call.data.split("-")[1])
    if b in admins and b != call.from_user.id:
        return await editMessage(call,
                                 f"⚠️ 打咩，no，机器人不可以对bot管理员出手喔，请[自己](tg://user?id={call.from_user.id})解决",
                                 timer=60)

    _, first_name = await _telegram_identity(b)
    e = sql_get_emby(tg=b)
    if e is None or e.embyid is None:
        await editMessage(call, f'💢 ta 没有注册账户。', timer=60)
    else:
        text = f'🎯 管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) 对 [{first_name}](tg://user?id={b}) - {e.name} 的'
        if e.lv != "c":
            if await emby.emby_change_policy(id=e.embyid, method=True) is True:
                if sql_update_emby(Emby.tg == b, lv='c') is True:
                    text += f'封禁完成，此状态可在下次续期时刷新'
                    LOGGER.info(text)
                else:
                    text += '封禁失败，已执行，但数据库写入错误'
                    LOGGER.error(text)
            else:
                text += f'封禁失败，请检查emby服务器。响应错误'
                LOGGER.error(text)
        elif e.lv == "c":
            if await emby.emby_change_policy(id=e.embyid):
                if sql_update_emby(Emby.tg == b, lv='b'):
                    text += '解禁完成'
                    LOGGER.info(text)
                else:
                    text += '解禁失败，服务器已执行，数据库写入错误'
                    LOGGER.error(text)
            else:
                text += '解封失败，请检查emby服务器。响应错误'
                LOGGER.error(text)
        await editMessage(call, text)
        try:
            await bot.send_message(b, text)
        except Exception as error:
            LOGGER.warning(f'【/kk 封禁操作】通知未识别用户 {b} 失败：{error}')


# 赠送资格
@bot.on_callback_query(filters.regex('gift'))
async def gift(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    await call.answer("✅ ok")
    b = int(call.data.split("-")[1])
    if b in admins and b != call.from_user.id:
        return await editMessage(call,
                                 f"⚠️ 打咩，no，机器人不可以对bot管理员出手喔，请[自己](tg://user?id={call.from_user.id})解决")

    _, first_name = await _telegram_identity(b)
    e = sql_get_emby(tg=b)
    if e is None or e.embyid is None:
        link = await cr_link_two(tg=call.from_user.id, for_tg=b, days=30)
        await editMessage(call, f"🌟 好的，管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n"
                                f'已为 [{first_name}](tg://user?id={b}) 赠予资格。前往bot进行下一步操作：',
                          buttons=gog_rester_ikb(link))
        LOGGER.info(f"【admin】：{call.from_user.id} 已发送 注册资格 {first_name} - {b} ")
    else:
        await editMessage(call, f'💢 [ta](tg://user?id={b}) 已注册账户。')


# 删除账户
@bot.on_callback_query(filters.regex('closeemby'))
async def close_emby(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    await call.answer("✅ ok")
    b = int(call.data.split("-")[1])
    if b in admins and b != call.from_user.id:
        return await editMessage(call,
                                 f"⚠️ 打咩，no，机器人不可以对bot管理员出手喔，请[自己](tg://user?id={call.from_user.id})解决",
                                 timer=60)

    _, first_name = await _telegram_identity(b)
    e = sql_get_emby(tg=b)
    if e is None or e.embyid is None:
        return await editMessage(call, f'💢 ta 还没有注册账户。', timer=60)

    if await emby.emby_del(e.embyid):
        await editMessage(call,
                          f'🎯 done，管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id})\n等级：{e.lv} - [{first_name}](tg://user?id={b}) '
                          f'账户 {e.name} 已完成删除。')
        try:
            await bot.send_message(b,
                                   f"🎯 管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) 已删除 您 的账户 {e.name}")
        except Exception as error:
            LOGGER.warning(f'【/kk 删除账户】通知未识别用户 {b} 失败：{error}')
        LOGGER.info(f"【admin】：{call.from_user.id} 完成删除 {b} 的账户 {e.name}")
    else:
        await editMessage(call, f'🎯 done，等级：{e.lv} - {first_name}的账户 {e.name} 删除失败。')
        LOGGER.info(f"【admin】：{call.from_user.id} 对 {b} 的账户 {e.name} 删除失败 ")


@bot.on_callback_query(filters.regex('fuckoff'))
async def fuck_off_m(_, call):
    if not judge_admins(call.from_user.id):
        return await call.answer("请不要以下犯上 ok？", show_alert=True)

    await call.answer("✅ ok")
    b = int(call.data.split("-")[1])
    if b in admins and b != call.from_user.id:
        return await editMessage(call,
                                 f"⚠️ 打咩，no，机器人不可以对bot管理员出手喔，请[自己](tg://user?id={call.from_user.id})解决",
                                 timer=60)
    try:
        await bot.ban_chat_member(call.message.chat.id, b)
    except pyrogram.errors.ChatAdminRequired:
        await editMessage(call,
                          f"⚠️ 请赋予我踢出成员的权限 [{call.from_user.first_name}](tg://user?id={call.from_user.id})")
    except pyrogram.errors.UserAdminInvalid:
        await editMessage(call,
                          f"⚠️ 打咩，no，机器人不可以对群组管理员出手喔，请[自己](tg://user?id={call.from_user.id})解决")
    else:
        _, first_name = await _telegram_identity(b)
        await call.chat.ban_member(b)  # 默认退群了就删号
        await editMessage(call,
                          f'🎯 done，管理员 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) 已移除 {first_name}')
        LOGGER.info(
            f"【admin】：{call.from_user.id} 已从群组 {call.message.chat.id} 封禁 {first_name} - {b}")
