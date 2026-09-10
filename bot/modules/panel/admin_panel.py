"""
 admin 面板
 功能包括注册上限、生成注册码和查看注册码情况
"""
from pyrogram import filters

from bot import bot, _open, save_config, LOGGER, bot_name
from bot.func_helper.emby import emby
from bot.func_helper.filters import admins_on_filter
from bot.sql_helper.sql_code import (
    sql_ban_used_code,
    sql_delete_unused_code,
    sql_delete_used_code,
    sql_get_activity_code_usage,
    sql_get_code,
)
from bot.sql_helper.sql_emby import sql_count_emby
from bot.func_helper.fix_bottons import gm_ikb_content, \
    re_cr_link_ikb, re_cr_activity_ikb, re_cr_line_ikb, close_it_ikb, activity_usage_ikb, code_query_ikb, \
    cr_renew_ikb, alias_setting_ikb
from bot.func_helper.msg_utils import callAnswer, editMessage, callListen, sendMessage
from bot.func_helper.utils import cr_link_one, cr_link_activity, cr_link_line


@bot.on_callback_query(filters.regex('manage') & admins_on_filter)
async def gm_ikb(_, call):
    await callAnswer(call, '✔️ manage面板')
    tg, emby, white, line_pro = sql_count_emby()
    gm_text = f'⚙️ 欢迎您，亲爱的管理员 {call.from_user.first_name}\n\n' \
               f'· 🔖 注册码续期 | **{"True" if _open.allow_code else "False"}**\n' \
               f'· 🎫 总注册限制 | **{_open.all_user}**\n· 🎟️ 已注册人数 | **{emby}** • WL **{white}**\n' \
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


@bot.on_callback_query(filters.regex('all_user_limit') & admins_on_filter)
async def open_all_user_l(_, call):
    await callAnswer(call, '⭕ 限制人数')
    send = await call.message.edit(
        "🦄 请在 120s 内发送注册总人数上限。\n**注**：注册码用户达到上限后将无法创建账户；取消请发送 /cancel")
    if send is False:
        return

    txt = await callListen(call, 120, buttons=gm_ikb_content)
    if txt is False:
        return
    elif txt.text == "/cancel":
        await txt.delete()
        return await gm_ikb(_, call)

    try:
        await txt.delete()
        a = int(txt.text)
    except ValueError:
        await editMessage(call, f"❌ 请输入一个正整数。", buttons=gm_ikb_content)
    else:
        if a <= 0:
            return await editMessage(call, "❌ 请输入一个正整数。", buttons=gm_ikb_content)
        _open.all_user = a
        save_config()
        await editMessage(call, f"✔️ 成功，您已设置 **注册总人数 {a}**", buttons=gm_ikb_content)
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
        buttons=code_query_ikb(
            record.code,
            can_delete=record.used is None,
            can_ban=record.used is not None,
        ),
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


async def _notify_illegal_code_user(tg, text):
    try:
        await bot.send_message(tg, text)
        return True
    except Exception as error:
        LOGGER.warning(f'【封禁注册码】无法通知用户 {tg}：{error}')
        return False


@bot.on_callback_query(filters.regex(r'^rcode_ban:') & admins_on_filter)
async def ban_used_code(_, call):
    code = call.data.split(':', 1)[1]
    await callAnswer(call, '⏳ 正在封禁并扣除时长')
    result = sql_ban_used_code(code)
    status = result['status']

    if status == 'deducted':
        days = result['days']
        tg = result['tg']
        notified = await _notify_illegal_code_user(
            tg,
            f'您因使用非法注册码，现已扣除 {days} 天时长。',
        )
        LOGGER.info(f'【封禁注册码】管理员 {call.from_user.id} 封禁并删除 {code}，用户 {tg} 被扣除 {days} 天')
        expiry_text = ''
        if result['expires_at'] is not None:
            expiry_text = f'\n· 扣除后到期 | **{result["expires_at"].strftime("%Y-%m-%d %H:%M:%S")}**'
        elif result['expiry_kind'] == 'preregister':
            expiry_text = f'\n· 剩余预注册时长 | **{result["remaining_days"]} 天**'
        notify_text = '' if notified else '\n\n⚠️ 处罚已生效，但机器人私聊通知发送失败。'
        return await editMessage(
            call,
            f'🚫 注册码 `{code}` 已封禁并删除\n'
            f'· 使用者 | [{tg}](tg://user?id={tg})\n'
            f'· 已扣除 | **{days} 天**{expiry_text}{notify_text}',
            buttons=code_query_ikb(),
        )

    if status == 'delete_required':
        tg = result['tg']
        if await emby.emby_del(result['embyid']):
            delete_code_status = sql_delete_used_code(code, tg)
            notified = await _notify_illegal_code_user(
                tg,
                '您因使用非法注册码，现已被删除账号。',
            )
            LOGGER.info(
                f'【封禁注册码】管理员 {call.from_user.id} 处理 {code}，'
                f'用户 {tg} 时长不足，账号 {result["name"]} 已删除，'
                f'注册码删除结果：{delete_code_status}'
            )
            notify_text = '' if notified else '\n\n⚠️ 账号已删除，但机器人私聊通知发送失败。'
            code_text = ''
            if delete_code_status not in ('deleted', 'not_found'):
                code_text = f'\n\n⚠️ 账号已删除，但注册码删除失败（{delete_code_status}），请检查数据库。'
            return await editMessage(
                call,
                f'🚫 注册码 `{code}` 封禁操作完成\n'
                f'· 使用者 | [{tg}](tg://user?id={tg})\n'
                f'· 处理结果 | **扣除后时长不足，账号已删除**{notify_text}{code_text}',
                buttons=code_query_ikb(),
            )

        LOGGER.error(
            f'【封禁注册码】删除用户 {tg} 的 Emby 账号 {result["embyid"]} 失败，注册码保留以便重试'
        )
        return await editMessage(
            call,
            f'❌ 注册码 `{code}` 对应账号删除失败，注册码已保留，可稍后重试',
            buttons=code_query_ikb(code, can_ban=True),
        )

    messages = {
        'not_found': '❌ 该注册码已不存在',
        'unused': '❌ 该注册码尚未使用，不能封禁',
        'user_not_found': '❌ 未找到使用该码的用户资料',
        'no_account': '❌ 使用者当前没有账号或可扣除时长',
        'invalid_duration': '❌ 注册码时长无效，无法执行扣除',
        'error': '❌ 数据库操作失败，请稍后重试',
    }
    error_text = messages.get(status, '❌ 封禁失败，请稍后重试')
    record = sql_get_code(code)
    if record is not None:
        return await editMessage(
            call,
            f'{error_text}\n\n{_code_info_text(record)}',
            buttons=code_query_ikb(
                record.code,
                can_delete=record.used is None,
                can_ban=record.used is not None,
            ),
        )
    return await editMessage(call, error_text, buttons=code_query_ikb())


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
