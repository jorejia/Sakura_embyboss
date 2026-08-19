"""
 admin 面板
 功能暂定 开关注册，生成注册码，查看注册码情况，邀请注册排名情况
"""
import asyncio

from pyrogram import filters
from pyrogram.errors import BadRequest

from bot import bot, _open, save_config, bot_photo, LOGGER, bot_name
from bot.func_helper.emby import emby
from bot.func_helper.filters import admins_on_filter
from bot.sql_helper.sql_code import sql_delete_unused_code, sql_get_code, sql_get_activity_code_usage
from bot.sql_helper.sql_emby import sql_count_emby, sql_count_registered_slots
from bot.func_helper.fix_bottons import gm_ikb_content, open_menu_ikb, gog_rester_ikb, back_open_menu_ikb, \
    back_free_ikb, \
    re_cr_link_ikb, re_cr_activity_ikb, re_cr_line_ikb, close_it_ikb, activity_usage_ikb, code_query_ikb, \
    cr_renew_ikb, alias_setting_ikb
from bot.func_helper.msg_utils import callAnswer, editMessage, sendPhoto, callListen, deleteMessage, sendMessage
from bot.func_helper.utils import open_check, cr_link_one, cr_link_activity, cr_link_line


@bot.on_callback_query(filters.regex('manage') & admins_on_filter)
async def gm_ikb(_, call):
    await callAnswer(call, '✔️ manage面板')
    stat, all_user, tem, timing, allow_code = await open_check()
    stat = "True" if stat else "False"
    allow_code = 'True' if allow_code else 'False'
    timing = 'Turn off' if timing == 0 else str(timing) + ' min'
    tg, emby, white, line_pro = sql_count_emby()
    gm_text = f'⚙️ 欢迎您，亲爱的管理员 {call.from_user.first_name}\n\n· ®️ 注册状态 | **{stat}**\n· ⏳ 定时注册 | **{timing}**\n' \
               f'· 🔖 注册码续期 | **{allow_code}**\n' \
               f'· 🎫 总注册限制 | **{all_user}**\n· 🎟️ 已注册人数 | **{emby}** • WL **{white}**\n' \
               f'· 💎 有效直连Pro | **{line_pro}**\n· 🤖 bot使用人数 | {tg}'

    await editMessage(call, gm_text, buttons=gm_ikb_content)


def _alias_display(value):
    value = str(value or '').strip()
    if not value:
        return '未设置'
    return value.replace('`', 'ˋ')


def _alias_panel_text(item_id, payload):
    return f'🏷️ **别名设置**\n\n' \
           f'· item_id | `{item_id}`\n' \
           f'· 主名 | `{_alias_display(payload.get("Name"))}`\n' \
           f'· 别名 | `{_alias_display(payload.get("OtherName"))}`'


async def _show_alias_panel(call, item_id):
    ok, payload = await emby.get_item_other_name(item_id)
    if not ok:
        error = payload.get('error', payload) if isinstance(payload, dict) else payload
        return await editMessage(call, f'⚠️ 获取别名失败：{error}', buttons=gm_ikb_content)
    return await editMessage(call, _alias_panel_text(item_id, payload), buttons=alias_setting_ikb(item_id))


# 开关注册
@bot.on_callback_query(filters.regex('open-menu') & admins_on_filter)
async def open_menu(_, call):
    await callAnswer(call, '®️ register面板')
    # [开关，注册总数，定时注册] 此间只对emby表中tg用户进行统计
    stat, all_user, tem, timing, allow_code = await open_check()
    tg, emby, white, line_pro = sql_count_emby()
    openstats = '✅' if stat else '❎'  # 三元运算
    timingstats = '❎' if timing == 0 else '✅'
    text = f'⚙ **注册状态设置**：\n\n- 自由注册即定量方式，定时注册既定时又定量，将自动转发消息至群组，再次点击按钮可提前结束并报告。\n' \
           f'- **注册总人数限制 {all_user}**'
    await editMessage(call, text, buttons=open_menu_ikb(openstats, timingstats))
    registered_slots = sql_count_registered_slots()
    if registered_slots is not None and tem != registered_slots:
        _open.tem = registered_slots
        save_config()


@bot.on_callback_query(filters.regex('open_stat') & admins_on_filter)
async def open_stats(_, call):
    stat, all_user, tem, timing, allow_code = await open_check()
    if timing != 0:
        return await callAnswer(call, "🔴 目前正在运行定时注册。\n无法调用，请再次点击，【定时注册】关闭状态", True)

    tg, emby, white, line_pro = sql_count_emby()
    if stat:
        _open.stat = False
        save_config()
        await callAnswer(call, "🟢【自由注册】\n\n已结束", True)
        sur = all_user - tem
        text = f'🫧 管理员 {call.from_user.first_name} 已关闭 **自由注册**\n\n' \
               f'🎫 总注册限制 | {all_user}\n🎟️ 已注册人数 | {tem}\n' \
               f'🎭 剩余可注册 | **{sur}**\n🤖 bot使用人数 | {tg}'
        await asyncio.gather(sendPhoto(call, photo=bot_photo, caption=text, send=True),
                             editMessage(call, text, buttons=back_free_ikb))
        # await open_menu(_, call)
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 关闭了自由注册")
    elif not stat:
        _open.stat = True
        save_config()
        await callAnswer(call, "🟡【自由注册】\n\n已开启", True)
        sur = all_user - tem  # for i in group可以多个群组用，但是现在不做
        text = f'🫧 管理员 {call.from_user.first_name} 已开启 **自由注册**\n\n' \
               f'🎫 总注册限制 | {all_user}\n🎟️ 已注册人数 | {tem}\n' \
               f'🎭 剩余可注册 | **{sur}**\n🤖 bot使用人数 | {tg}'
        await asyncio.gather(sendPhoto(call, photo=bot_photo, caption=text, buttons=gog_rester_ikb(), send=True),
                             editMessage(call, text=text, buttons=back_free_ikb))
        # await open_menu(_, call)
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 开启了自由注册，总人数限制 {all_user}")


change_for_timing_task = None


@bot.on_callback_query(filters.regex('open_timing') & admins_on_filter)
async def open_timing(_, call):
    global change_for_timing_task
    if _open.timing == 0:
        await callAnswer(call, '⭕ 定时设置')
        await editMessage(call,
                          "🦄【定时注册】 \n\n- 请在 120s 内发送 [定时时长] [总人数]\n"
                          "- 形如：`30 50` 即30min，总人数限制50\n"
                          "- 如需要关闭定时注册，再次点击【定时注册】\n"
                          "- 设置好之后将发送置顶消息注意权限\n- 退出 /cancel")

        txt = await callListen(call, 120, buttons=back_open_menu_ikb)
        if txt is False:
            return

        await txt.delete()
        if txt.text == '/cancel':
            return await open_menu(_, call)

        try:
            new_timing, new_all_user = txt.text.split()
            _open.timing = int(new_timing)
            _open.all_user = int(new_all_user)
            _open.stat = True
            save_config()
        except ValueError:
            await editMessage(call, "🚫 请检查数字填写是否正确。\n`[时长min] [总人数]`", buttons=back_open_menu_ikb)
        else:
            tg, emby, white, line_pro = sql_count_emby()
            sur = _open.all_user - emby
            await asyncio.gather(sendPhoto(call, photo=bot_photo,
                                           caption=f'🫧 管理员 {call.from_user.first_name} 已开启 **定时注册**\n\n'
                                                   f'⏳ 可持续时间 | **{_open.timing}** min\n'
                                                   f'🎫 总注册限制 | {_open.all_user}\n🎟️ 已注册人数 | {emby}\n'
                                                   f'🎭 剩余可注册 | **{sur}**\n🤖 bot使用人数 | {tg}',
                                           buttons=gog_rester_ikb(), send=True),
                                 editMessage(call,
                                             f"®️ 好，已设置**定时注册 {_open.timing} min 总限额 {_open.all_user}**",
                                             buttons=back_free_ikb))
            LOGGER.info(
                f"【admin】-定时注册：管理员 {call.from_user.first_name} 开启了定时注册 {_open.timing} min，人数限制 {sur}")
            # 创建一个异步任务并保存为变量，并给它一个名字
            change_for_timing_task = asyncio.create_task(
                change_for_timing(_open.timing, call.from_user.id, call), name='change_for_timing')

    else:
        try:
            # 遍历所有的异步任务，找到'change_for_timing'，取消
            for task in asyncio.all_tasks():
                if task.get_name() == 'change_for_timing':
                    change_for_timing_task = task
                    break
            change_for_timing_task.cancel()
        except AttributeError:
            pass
        else:
            await callAnswer(call, "Ⓜ️【定时任务运行终止】\n\n**已为您停止**", True)
            await open_menu(_, call)


async def change_for_timing(timing, tgid, call):
    a = _open.tem
    timing = timing * 60
    try:
        await asyncio.sleep(timing)
    except asyncio.CancelledError:
        pass
    finally:
        _open.timing = 0
        _open.stat = False
        save_config()
        b = _open.tem - a
        s = _open.all_user - _open.tem
        text = f'⏳** 注册结束**：\n\n🍉 目前席位：{_open.tem}\n🥝 新增席位：{b}\n🍋 剩余席位：{s}'
        send = await sendPhoto(call, photo=bot_photo, caption=text, timer=300, send=True)
        send1 = await send.forward(tgid)
        LOGGER.info(f'【admin】-定时注册：运行结束，本次注册 目前席位：{_open.tem}  新增席位:{b}  剩余席位：{s}')
        await deleteMessage(send1, 30)


@bot.on_callback_query(filters.regex('all_user_limit') & admins_on_filter)
async def open_all_user_l(_, call):
    await callAnswer(call, '⭕ 限制人数')
    send = await call.message.edit(
        "🦄 请在 120s 内发送开注总人数，本次修改不会对注册状态改动，如需要开注册请点击打开自由注册\n**注**：总人数满自动关闭注册 取消 /cancel")
    if send is False:
        return

    txt = await callListen(call, 120, buttons=back_free_ikb)
    if txt is False:
        return
    elif txt.text == "/cancel":
        await txt.delete()
        return await open_menu(_, call)

    try:
        await txt.delete()
        a = int(txt.text)
    except ValueError:
        await editMessage(call, f"❌ 八嘎，请输入一个数字给我。", buttons=back_free_ikb)
    else:
        _open.all_user = a
        save_config()
        await editMessage(call, f"✔️ 成功，您已设置 **注册总人数 {a}**", buttons=back_free_ikb)
        LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 调整了总人数限制：{a}")


# 生成注册链接
@bot.on_callback_query(filters.regex('cr_link') & admins_on_filter)
async def cr_link(_, call):
    await callAnswer(call, '✔️ 创建注册码')
    send = await editMessage(call,
                             f'🎟️ 请回复创建 [天数] [数量] [模式]\n\n'
                             f'**天数**：月30，季90，半年180，年365\n'
                             f'**模式**： link -深链接 | code -码\n'
                             f'**示例**：`1 20 link` 记作 20条 1天注册码链接\n'
                             f'__取消本次操作，请 /cancel__')
    if send is False:
        return

    content = await callListen(call, 120, buttons=re_cr_link_ikb)
    if content is False:
        return
    elif content.text == '/cancel':
        await content.delete()
        return await editMessage(call, '⭕ 您已经取消操作了。', buttons=re_cr_link_ikb)
    try:
        await content.delete()
        times, count, method = content.text.split()
        count = int(count)
        days = int(times)
        if method != 'code' and method != 'link':
            return editMessage(call, '⭕ 输入的method参数有误', buttons=re_cr_link_ikb)
    except (ValueError, IndexError):
        return await editMessage(call, '⚠️ 检查输入，有误。', buttons=re_cr_link_ikb)
    else:
        links = await cr_link_one(call.from_user.id, times, count, days, method)
        if links is None:
            return await editMessage(call, '⚠️ 数据库插入失败，请检查数据库。', buttons=re_cr_link_ikb)
        links = f"🎯 {bot_name}已为您生成了 **{days}天** 邀请码 {count} 个\n\n" + links
        chunks = [links[i:i + 4096] for i in range(0, len(links), 4096)]
        for chunk in chunks:
            await sendMessage(content, chunk, buttons=close_it_ikb)
        await editMessage(call, f'📂 {bot_name}已为 您 生成了 {count} 个 {days} 天邀请码', buttons=re_cr_link_ikb)
        LOGGER.info(f"【admin】：{bot_name}已为 {content.from_user.id} 生成了 {count} 个 {days} 天邀请码")


@bot.on_callback_query(filters.regex('cr_activity') & admins_on_filter)
async def cr_activity(_, call):
    await callAnswer(call, '✔️ 创建活动码')
    send = await editMessage(call,
                             f'🎁 请回复创建 [天数] [数量] [模式]\n\n'
                             f'**天数**：月30，季90，半年180，年365\n'
                             f'**模式**： link -深链接 | code -码\n'
                             f'**示例**：`1 20 link` 记作 20条 1天活动码链接\n'
                             f'__取消本次操作，请 /cancel__')
    if send is False:
        return

    content = await callListen(call, 120, buttons=re_cr_activity_ikb)
    if content is False:
        return
    elif content.text == '/cancel':
        await content.delete()
        return await editMessage(call, '⭕ 您已经取消操作了。', buttons=re_cr_activity_ikb)
    try:
        await content.delete()
        times, count, method = content.text.split()
        count = int(count)
        days = int(times)
        if method != 'code' and method != 'link':
            return editMessage(call, '⭕ 输入的method参数有误', buttons=re_cr_activity_ikb)
    except (ValueError, IndexError):
        return await editMessage(call, '⚠️ 检查输入，有误。', buttons=re_cr_activity_ikb)
    else:
        links = await cr_link_activity(call.from_user.id, times, count, days, method)
        if links is None:
            return await editMessage(call, '⚠️ 数据库插入失败，请检查数据库。', buttons=re_cr_activity_ikb)
        header = f"🎯 {bot_name}已为您生成了 **{days}天** 活动码 {count} 个\n\n"
        chunks = []
        chunk = header
        # 预留状态文字的长度，避免查询后超过 Telegram 的 4096 字符限制。
        for line in links.splitlines():
            candidate = f'{chunk}{line}\n'
            if len(candidate) > 3200 and chunk != header:
                chunks.append(chunk.rstrip())
                chunk = f'{header}{line}\n'
            else:
                chunk = candidate
        if chunk != header:
            chunks.append(chunk.rstrip())
        for chunk in chunks:
            await sendMessage(content, chunk, buttons=activity_usage_ikb)
        await editMessage(call, f'📂 {bot_name}已为 您 生成了 {count} 个 {days} 天活动码', buttons=re_cr_activity_ikb)
        LOGGER.info(f"【admin】：{bot_name}已为 {content.from_user.id} 生成了 {count} 个 {days} 天活动码")


def _activity_code_line(line):
    """从活动码结果的一行中提取原始码，兼容 code 和深链接模式。"""
    display = line.split('  —  ', 1)[0].strip().strip('`')
    if not display or display.startswith('🎯'):
        return None, None
    if '?start=' in display:
        code = display.split('?start=', 1)[1].split('&', 1)[0].strip()
    else:
        code = display
    return display, code


@bot.on_callback_query(filters.regex(r'^activity_usage$') & admins_on_filter)
async def activity_usage(_, call):
    lines = (call.message.text or '').splitlines()
    entries = [_activity_code_line(line) for line in lines]
    entries = [(display, code) for display, code in entries if code]
    if not entries:
        return await callAnswer(call, '⚠️ 未在当前消息中找到活动码', True)

    usage = sql_get_activity_code_usage([code for _, code in entries])
    if usage is None:
        return await callAnswer(call, '⚠️ 数据库查询失败', True)

    header = next((line for line in lines if line.strip().startswith('🎯')), '🎯 活动码使用情况')
    result_lines = [header, '']
    for display, code in entries:
        if code not in usage:
            status = '⚠️ 已不存在'
        elif usage[code]:
            status = '✅ 已使用'
        else:
            status = '⭕ 未使用'
        result_lines.append(f'{display}  —  {status}')

    await callAnswer(call, '♻️ 已刷新最新使用情况')
    await editMessage(call, '\n'.join(result_lines), buttons=activity_usage_ikb)


@bot.on_callback_query(filters.regex(r'^cr_line$') & admins_on_filter)
async def cr_line(_, call):
    await callAnswer(call, '✔️ 创建线路码')
    send = await editMessage(call,
                             f'💎 请回复创建 [天数] [数量] [模式]\n\n'
                             f'**天数**：月30，季90，半年180，年365\n'
                             f'**模式**： link -深链接 | code -码\n'
                             f'**示例**：`30 20 code` 记作 20 个 30 天线路码\n'
                             f'__取消本次操作，请 /cancel__')
    if send is False:
        return

    content = await callListen(call, 120, buttons=re_cr_line_ikb)
    if content is False:
        return
    if content.text == '/cancel':
        await content.delete()
        return await editMessage(call, '⭕ 您已经取消操作了。', buttons=re_cr_line_ikb)
    try:
        await content.delete()
        times, count, method = content.text.split()
        count = int(count)
        days = int(times)
        if days <= 0 or count <= 0 or method not in ('code', 'link'):
            raise ValueError
    except (ValueError, IndexError):
        return await editMessage(call, '⚠️ 检查输入，有误。', buttons=re_cr_line_ikb)

    links = await cr_link_line(call.from_user.id, times, count, days, method)
    if links is None:
        return await editMessage(call, '⚠️ 数据库插入失败，请检查数据库。', buttons=re_cr_line_ikb)
    links = f"🎯 {bot_name}已为您生成 **{days}天** 线路码 {count} 个\n\n" + links
    chunks = [links[i:i + 4096] for i in range(0, len(links), 4096)]
    for chunk in chunks:
        await sendMessage(content, chunk, buttons=close_it_ikb)
    await editMessage(call, f'📂 已生成 {count} 个 {days} 天线路码', buttons=re_cr_line_ikb)
    LOGGER.info(f"【admin】：{bot_name}已为 {call.from_user.id} 生成了 {count} 个 {days} 天线路码")


@bot.on_callback_query(filters.regex('alias_setting') & admins_on_filter)
async def alias_setting(_, call):
    await callAnswer(call, '🏷️ 别名设置')
    send = await editMessage(call,
                             '🏷️ **别名设置**\n\n'
                             '- 请在 120s 内发送需要设置别名的 `item_id`\n'
                             '- 退出请发送 /cancel')
    if send is False:
        return

    content = await callListen(call, 120, buttons=gm_ikb_content)
    if content is False:
        return
    elif content.text == '/cancel':
        await content.delete()
        return await gm_ikb(_, call)

    try:
        await content.delete()
        item_id = int(content.text.strip())
        if item_id <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        return await editMessage(call, '⚠️ item_id 需要是正整数。', buttons=gm_ikb_content)
    return await _show_alias_panel(call, item_id)


@bot.on_callback_query(filters.regex('alias_clear') & admins_on_filter)
async def alias_clear(_, call):
    await callAnswer(call, '🧹 正在清空别名')
    try:
        item_id = int(call.data.split('-')[1])
    except (IndexError, ValueError):
        return await editMessage(call, '⚠️ item_id 参数错误。', buttons=gm_ikb_content)

    ok, payload = await emby.set_item_other_name(item_id, '')
    if not ok:
        error = payload.get('error', payload) if isinstance(payload, dict) else payload
        return await editMessage(call, f'⚠️ 清空别名失败：{error}', buttons=alias_setting_ikb(item_id))
    return await _show_alias_panel(call, item_id)


@bot.on_callback_query(filters.regex('alias_modify') & admins_on_filter)
async def alias_modify(_, call):
    await callAnswer(call, '✏️ 修改别名')
    try:
        item_id = int(call.data.split('-')[1])
    except (IndexError, ValueError):
        return await editMessage(call, '⚠️ item_id 参数错误。', buttons=gm_ikb_content)

    send = await editMessage(call,
                             f'✏️ **修改别名**\n\n'
                             f'· item_id | `{item_id}`\n\n'
                             f'- 请在 120s 内发送新的别名\n'
                             f'- 退出请发送 /cancel')
    if send is False:
        return

    content = await callListen(call, 120, buttons=alias_setting_ikb(item_id))
    if content is False:
        return
    elif content.text == '/cancel':
        await content.delete()
        return await _show_alias_panel(call, item_id)

    new_alias = content.text.strip()
    await content.delete()
    if not new_alias:
        return await editMessage(call, '⚠️ 别名不能为空。', buttons=alias_setting_ikb(item_id))

    ok, payload = await emby.set_item_other_name(item_id, new_alias)
    if not ok:
        error = payload.get('error', payload) if isinstance(payload, dict) else payload
        return await editMessage(call, f'⚠️ 修改别名失败：{error}', buttons=alias_setting_ikb(item_id))
    return await _show_alias_panel(call, item_id)


def _code_type_text(invite):
    return {
        None: '普通注册码',
        'n': '普通注册码',
        'y': '邀请码',
        'a': '活动码',
        'l': '直连Pro线路码',
    }.get(invite, f'未知类型（{invite}）')


def _code_info_text(record):
    used = record.used is not None
    text = (
        f'🎫 **注册码查询**\n\n'
        f'· 码 | `{record.code}`\n'
        f'· 性质 | **{_code_type_text(record.invite)}**\n'
        f'· 时长 | **{record.us} 天**\n'
        f'· 生成者 | [{record.tg}](tg://user?id={record.tg})\n'
        f'· 使用状态 | **{"已使用" if used else "未使用"}**'
    )
    if used:
        used_time = record.usedtime.strftime('%Y-%m-%d %H:%M:%S') if record.usedtime else '未记录'
        text += (
            f'\n· 使用者 | [{record.used}](tg://user?id={record.used})'
            f'\n· 使用时间 | **{used_time}**'
        )
    return text


# 查询任意一个注册码
@bot.on_callback_query(filters.regex(r'^ch_link$') & admins_on_filter)
async def ch_link(_, call):
    await callAnswer(call, '🔍 查询注册码')
    await editMessage(
        call,
        '🔍 **查询注册码**\n\n请在 120 秒内发送需要查询的完整码\n取消请发送 /cancel',
        buttons=code_query_ikb(),
    )
    content = await callListen(call, 120, buttons=code_query_ikb())
    if content is False:
        return

    code = content.text.strip().strip('`')
    await content.delete()
    if code == '/cancel':
        return await editMessage(call, '✅ 已取消注册码查询', buttons=gm_ikb_content)
    if not code:
        return await editMessage(call, '⚠️ 注册码不能为空', buttons=code_query_ikb())

    record = sql_get_code(code)
    if record is None:
        return await editMessage(call, f'❌ 未找到注册码 `{code}`', buttons=code_query_ikb())

    await editMessage(
        call,
        _code_info_text(record),
        buttons=code_query_ikb(record.code, can_delete=record.used is None),
    )


@bot.on_callback_query(filters.regex(r'^rcode_delete:') & admins_on_filter)
async def delete_unused_code(_, call):
    code = call.data.split(':', 1)[1]
    result = sql_delete_unused_code(code)
    if result == 'deleted':
        LOGGER.info(f'【删除注册码】管理员 {call.from_user.id} 删除了未使用码 {code}')
        await callAnswer(call, '✅ 注册码已删除', True)
        return await editMessage(
            call,
            f'🗑 注册码 `{code}` 已从数据库删除',
            buttons=code_query_ikb(),
        )
    if result == 'used':
        await callAnswer(call, '❌ 该码已被使用，不能删除', True)
        record = sql_get_code(code)
        if record is not None:
            return await editMessage(call, _code_info_text(record), buttons=code_query_ikb())
        return
    if result == 'not_found':
        await callAnswer(call, '❌ 该码已不存在', True)
        return await editMessage(call, f'❌ 注册码 `{code}` 已不存在', buttons=code_query_ikb())
    return await callAnswer(call, '❌ 数据库删除失败，请稍后重试', True)


@bot.on_callback_query(filters.regex('set_renew'))
async def set_renew(_, call):
    await callAnswer(call, '🚀 进入续期设置')
    try:
        method = call.data.split('-')[1]
        setattr(_open, method, not getattr(_open, method))
        save_config()
    except IndexError:
        pass
    finally:
        await editMessage(call, text='⭕ **关于用户组的续期功能**\n\n选择点击下方按钮开关任意兑换功能',
                          buttons=cr_renew_ikb())
