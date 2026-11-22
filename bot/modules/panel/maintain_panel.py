"""
管理菜单的三个页面：
- 🛣️ 线路管理：直连线路的增删改、Pro 标定、默认线路（数据保存在 sidecar；线路 id 要与 OpenResty 的 line_rules 对应）
- 🧾 额外账号：手动添加不绑定 Telegram 的账号（写入 sidecar 与 embyboss 数据库，等级 a 不过期）
- 🧰 维护：原先的维护命令（到期检测、日榜 / 周榜、群成员同步、账号一致性检查、备份数据库、重启）
"""
import asyncio

from pyrogram import filters
from pykeyboard import InlineButton, InlineKeyboard

from bot import bot, LOGGER, owner
from bot.func_helper.emby import emby
from bot.func_helper.filters import admins_on_filter
from bot.func_helper.msg_utils import callAnswer, callListen, editMessage, sendMessage
from bot.func_helper.sidecar_lines import invalidate_lines
from bot.modules.commands.syncs import delete_unbound_accounts, find_unbound_accounts, sync_group_members
from bot.modules.panel.sched_panel import restart_bot, run_backup_db, run_check_ex, run_day_ranks, run_week_ranks
from bot.sql_helper.sql_emby import sql_get_emby
from bot.sql_helper.sql_extra import is_extra_tg, sql_list_extra_accounts

BACK = InlineButton('🔙 返回', 'manage')


def _kb(*buttons):
    kb = InlineKeyboard()
    kb.row(*buttons)
    return kb


def _int_arg(call):
    try:
        return int(call.data.split(':', 1)[1])
    except (IndexError, ValueError):
        return None


# ═════════════ 线路管理 ═════════════

def _lines_text(data):
    lines = data.get('lines') or []
    default = data.get('defaultLineId')
    rows = []
    for l in lines:
        tags = []
        if l['id'] == default:
            tags.append('默认')
        if l.get('pro'):
            tags.append('💎 Pro')
        rows.append(f"· `{l['id']}` {l['name']}{'（' + '，'.join(tags) + '）' if tags else ''}")
    return '🛣️ **线路管理**\n\n' + ('\n'.join(rows) or '（暂无线路）') + \
        '\n\n线路 id 需与 OpenResty `token_line_redirect.lua` 的 line_rules 对应，新增线路前先配好域名。'


def _lines_ikb(data):
    kb = InlineKeyboard(row_width=3)
    kb.add(*[InlineButton(f"{'💎 ' if l.get('pro') else ''}{l['name']}", f"lnadm_v:{l['id']}") for l in data.get('lines') or []])
    kb.row(InlineButton('➕ 新增线路', 'lnadm_add'), BACK)
    return kb


def _line_ikb(line, is_default):
    kb = InlineKeyboard(row_width=2)
    kb.add(InlineButton('✏️ 改名', f"lnadm_ren:{line['id']}"),
           InlineButton('💎 取消 Pro' if line.get('pro') else '💎 设为 Pro', f"lnadm_pro:{line['id']}"))
    if not is_default and not line.get('pro'):
        kb.add(InlineButton('⭐ 设为默认', f"lnadm_def:{line['id']}"))
    if not is_default:
        kb.add(InlineButton('🗑 删除', f"lnadm_del:{line['id']}"))
    kb.row(InlineButton('🔙 线路列表', 'lnadm'))
    return kb


async def _show_lines(call, notice=''):
    ok, data = emby.get_lines()
    if not ok:
        return await editMessage(call, f'⚠️ 读取线路失败：{data}', buttons=_kb(BACK))
    await editMessage(call, (notice + '\n\n' if notice else '') + _lines_text(data), buttons=_lines_ikb(data))


async def _find_line(call, line_id):
    ok, data = emby.get_lines()
    if not ok:
        await editMessage(call, f'⚠️ 读取线路失败：{data}', buttons=_kb(BACK))
        return None, None
    line = next((l for l in data.get('lines') or [] if l['id'] == line_id), None)
    if line is None:
        await _show_lines(call, '⚠️ 线路不存在')
    return line, data


def _after_change(ok, data):
    invalidate_lines()
    if not ok:
        return f'⚠️ {data}'
    moved = data.get('movedUsers') if isinstance(data, dict) else None
    return '✅ 已保存' + (f'，{moved} 位用户已移回默认线路' if moved else '')


@bot.on_callback_query(filters.regex(r'^lnadm$') & admins_on_filter)
async def line_admin(_, call):
    await callAnswer(call, '🛣️ 线路管理')
    await _show_lines(call)


@bot.on_callback_query(filters.regex(r'^lnadm_v:\d+$') & admins_on_filter)
async def line_admin_view(_, call):
    await callAnswer(call, '🛣️ 线路')
    line, data = await _find_line(call, _int_arg(call))
    if line is None:
        return
    is_default = line['id'] == data.get('defaultLineId')
    text = f"🛣️ **线路 `{line['id']}`**\n\n· 名称 | {line['name']}\n· 类型 | {'💎 Pro' if line.get('pro') else '普通'}\n" \
           f"· 默认 | {'是' if is_default else '否'}"
    await editMessage(call, text, buttons=_line_ikb(line, is_default))


@bot.on_callback_query(filters.regex(r'^lnadm_pro:\d+$') & admins_on_filter)
async def line_admin_toggle_pro(_, call):
    line, _data = await _find_line(call, _int_arg(call))
    if line is None:
        return
    ok, data = emby.upsert_line(line['id'], line['name'], not line.get('pro'))
    await callAnswer(call, _after_change(ok, data), True)
    LOGGER.info(f"【线路管理】{call.from_user.id} 将线路 {line['id']} 设为 {'普通' if line.get('pro') else 'Pro'}：{ok}")
    await _show_lines(call)


@bot.on_callback_query(filters.regex(r'^lnadm_def:\d+$') & admins_on_filter)
async def line_admin_default(_, call):
    line_id = _int_arg(call)
    ok, data = emby.set_default_line(line_id)
    await callAnswer(call, _after_change(ok, data), True)
    await _show_lines(call)


@bot.on_callback_query(filters.regex(r'^lnadm_del:\d+$') & admins_on_filter)
async def line_admin_delete(_, call):
    line, _data = await _find_line(call, _int_arg(call))
    if line is None:
        return
    kb = InlineKeyboard(row_width=2)
    kb.add(InlineButton('⚠️ 确认删除', f"lnadm_delok:{line['id']}"), InlineButton('取消', f"lnadm_v:{line['id']}"))
    await editMessage(call, f"确认删除线路 `{line['id']}` {line['name']}？\n该线路上的用户会被移回默认线路。", buttons=kb)


@bot.on_callback_query(filters.regex(r'^lnadm_delok:\d+$') & admins_on_filter)
async def line_admin_delete_ok(_, call):
    line_id = _int_arg(call)
    ok, data = emby.delete_line(line_id)
    await callAnswer(call, _after_change(ok, data), True)
    LOGGER.info(f"【线路管理】{call.from_user.id} 删除线路 {line_id}：{ok}")
    await _show_lines(call)


@bot.on_callback_query(filters.regex(r'^lnadm_ren:\d+$') & admins_on_filter)
async def line_admin_rename(_, call):
    line, _data = await _find_line(call, _int_arg(call))
    if line is None:
        return
    await callAnswer(call, '✏️ 改名')
    await editMessage(call, f"✏️ 请在 120s 内发送线路 `{line['id']}` 的新名称（1~32 字），/cancel 取消")
    content = await callListen(call, 120, buttons=_kb(InlineButton('🔙 线路列表', 'lnadm')))
    if content is False:
        return
    text = (content.text or '').strip()
    await content.delete()
    if text == '/cancel':
        return await _show_lines(call)
    ok, data = emby.upsert_line(line['id'], text, line.get('pro'))
    await _show_lines(call, _after_change(ok, data))


@bot.on_callback_query(filters.regex(r'^lnadm_add$') & admins_on_filter)
async def line_admin_add(_, call):
    await callAnswer(call, '➕ 新增线路')
    await editMessage(call, '➕ **新增线路**\n\n请在 120s 内发送：`线路id 名称 [pro]`\n例如 `4 直连四线` 或 `13 直连Pro三线 pro`\n/cancel 取消')
    content = await callListen(call, 120, buttons=_kb(InlineButton('🔙 线路列表', 'lnadm')))
    if content is False:
        return
    text = (content.text or '').strip()
    await content.delete()
    if text == '/cancel':
        return await _show_lines(call)
    parts = text.split()
    try:
        line_id = int(parts[0])
        pro = len(parts) > 2 and parts[-1].lower() == 'pro'
        name = ' '.join(parts[1:-1] if pro else parts[1:]).strip()
        if line_id <= 0 or not name:
            raise ValueError
    except (ValueError, IndexError):
        return await _show_lines(call, '⚠️ 格式不对：`线路id 名称 [pro]`')
    ok, data = emby.get_lines()
    if ok and any(l['id'] == line_id for l in data.get('lines') or []):
        return await _show_lines(call, f'⚠️ 线路 {line_id} 已存在，请在列表里修改')
    ok, data = emby.upsert_line(line_id, name, pro)
    LOGGER.info(f"【线路管理】{call.from_user.id} 新增线路 {line_id} {name} pro={pro}：{ok}")
    await _show_lines(call, _after_change(ok, data))


# ═════════════ 额外账号 ═════════════

def _extra_ikb(rows):
    kb = InlineKeyboard(row_width=2)
    kb.add(*[InlineButton(f"{r.name}", f"xacct_v:{r.tg}") for r in rows])
    kb.row(InlineButton('➕ 添加额外账号', 'xacct_add'), BACK)
    return kb


async def _show_extra(call, notice=''):
    rows = sql_list_extra_accounts()
    text = '🧾 **额外账号**\n\n不绑定 Telegram 的账号（如管理员手动开的家庭账号），记录在 embyboss 数据库中，等级 a 不过期。\n\n' + \
           ('\n'.join(f"· `{r.tg}` {r.name}" for r in rows) or '（暂无）')
    await editMessage(call, (notice + '\n\n' if notice else '') + text, buttons=_extra_ikb(rows))


@bot.on_callback_query(filters.regex(r'^xacct$') & admins_on_filter)
async def extra_accounts(_, call):
    await callAnswer(call, '🧾 额外账号')
    await _show_extra(call)


@bot.on_callback_query(filters.regex(r'^xacct_v:\d+$') & admins_on_filter)
async def extra_account_view(_, call):
    tg = _int_arg(call)
    e = sql_get_emby(tg) if is_extra_tg(tg) else None
    if e is None or e.tg != tg:
        return await _show_extra(call, '⚠️ 账号不存在')
    await callAnswer(call, e.name)
    kb = InlineKeyboard(row_width=2)
    kb.add(InlineButton('🔑 重置为随机密码', f'xacct_pw:{tg}'), InlineButton('🗑 删除', f'xacct_rm:{tg}'))
    kb.row(InlineButton('🔙 额外账号', 'xacct'))
    await editMessage(call, f"🧾 **{e.name}**\n\n· 编号 | `{e.tg}`\n· 账号 Id | `{e.embyid}`\n· 等级 | {e.lv}\n"
                            f"· 创建 | {e.cr or '未知'}\n· 密码 | `{e.pwd or '空'}`", buttons=kb)


@bot.on_callback_query(filters.regex(r'^xacct_pw:\d+$') & admins_on_filter)
async def extra_account_password(_, call):
    from bot.func_helper.utils import pwd_create
    tg = _int_arg(call)
    e = sql_get_emby(tg) if is_extra_tg(tg) else None
    if e is None or e.tg != tg:
        return await _show_extra(call, '⚠️ 账号不存在')
    new = await pwd_create(8)
    ok = await emby.emby_reset(e.embyid, new)
    await callAnswer(call, '✅ 已重置' if ok else '⚠️ 重置失败', True)
    call.data = f'xacct_v:{tg}'
    await extra_account_view(_, call)


@bot.on_callback_query(filters.regex(r'^xacct_rm:\d+$') & admins_on_filter)
async def extra_account_remove(_, call):
    tg = _int_arg(call)
    kb = InlineKeyboard(row_width=2)
    kb.add(InlineButton('⚠️ 确认删除', f'xacct_rmok:{tg}'), InlineButton('取消', f'xacct_v:{tg}'))
    await editMessage(call, '确认删除该额外账号？播放记录、收藏会一并删除，且不可恢复。', buttons=kb)


@bot.on_callback_query(filters.regex(r'^xacct_rmok:\d+$') & admins_on_filter)
async def extra_account_remove_ok(_, call):
    from bot.sql_helper.sql_emby import sql_delete_emby
    tg = _int_arg(call)
    e = sql_get_emby(tg) if is_extra_tg(tg) else None
    if e is None or e.tg != tg:
        return await _show_extra(call, '⚠️ 账号不存在')
    ok = await emby.emby_del(e.embyid)
    # 额外账号没有 TG 用户可保留，记录一并删除
    sql_delete_emby(tg=tg)
    LOGGER.info(f"【额外账号】{call.from_user.id} 删除 {e.name}：{ok}")
    await _show_extra(call, '✅ 已删除' if ok else '⚠️ sidecar 删除失败，已移除数据库记录')


@bot.on_callback_query(filters.regex(r'^xacct_add$') & admins_on_filter)
async def extra_account_add(_, call):
    await callAnswer(call, '➕ 添加额外账号')
    await editMessage(call, '➕ **添加额外账号**\n\n请在 120s 内发送账号名称（登录用户名），/cancel 取消')
    content = await callListen(call, 120, buttons=_kb(InlineButton('🔙 额外账号', 'xacct')))
    if content is False:
        return
    name = (content.text or '').strip()
    await content.delete()
    if name == '/cancel':
        return await _show_extra(call)
    if not name or len(name) > 64 or any(c in name for c in '\r\n\t'):
        return await _show_extra(call, '⚠️ 名称不合法')
    ok, result = await emby.create_extra_account(name)
    if not ok:
        return await _show_extra(call, f'⚠️ 创建失败：{result}')
    tg, pwd, pwd2 = result
    LOGGER.info(f"【额外账号】{call.from_user.id} 创建 {name}（编号 {tg}）")
    await _show_extra(call, f'✅ 已创建 **{name}**\n· 编号 | `{tg}`\n· 密码 | `{pwd}`\n· 安全码 | `{pwd2}`')


# ═════════════ 维护 ═════════════

def _maintain_ikb(is_owner):
    kb = InlineKeyboard(row_width=2)
    kb.add(InlineButton('⏰ 立即到期检测', 'mtask_exp'), InlineButton('📊 召唤日榜', 'mtask_day'),
           InlineButton('📈 召唤周榜', 'mtask_week'), InlineButton('👥 群成员同步', 'mtask_grp'),
           InlineButton('🔗 账号一致性检查', 'mtask_unb'))
    if is_owner:
        kb.add(InlineButton('💾 备份数据库', 'mtask_bak'), InlineButton('🔁 重启 bot', 'mtask_rst'))
    kb.row(BACK)
    return kb


async def _show_maintain(call, notice=''):
    await editMessage(call, (notice + '\n\n' if notice else '') + '🧰 **维护**\n\n手动执行定时任务与账号维护。', buttons=_maintain_ikb(call.from_user.id == owner))


def _reporter(call):
    async def report(text):
        await sendMessage(call, text)
    return report


@bot.on_callback_query(filters.regex(r'^mtask$') & admins_on_filter)
async def maintain(_, call):
    await callAnswer(call, '🧰 维护')
    await _show_maintain(call)


@bot.on_callback_query(filters.regex(r'^mtask_exp$') & admins_on_filter)
async def maintain_check_ex(_, call):
    await callAnswer(call, '⏰ 正在运行到期检测…')
    await _show_maintain(call, await run_check_ex())


@bot.on_callback_query(filters.regex(r'^mtask_day$') & admins_on_filter)
async def maintain_day_ranks(_, call):
    await callAnswer(call, '📊 正在生成日榜…')
    await run_day_ranks()


@bot.on_callback_query(filters.regex(r'^mtask_week$') & admins_on_filter)
async def maintain_week_ranks(_, call):
    await callAnswer(call, '📈 正在生成周榜…')
    await run_week_ranks()


@bot.on_callback_query(filters.regex(r'^mtask_grp$') & admins_on_filter)
async def maintain_group_sync(_, call):
    kb = InlineKeyboard(row_width=2)
    kb.add(InlineButton('⚠️ 确认执行', 'mtask_grpok'), InlineButton('取消', 'mtask'))
    await editMessage(call, '👥 **群成员同步**\n\n检查所有 b 级账号是否仍在群内，不在群的会被删除账号（保留用户记录）并收到通知。确认执行？', buttons=kb)


@bot.on_callback_query(filters.regex(r'^mtask_grpok$') & admins_on_filter)
async def maintain_group_sync_ok(_, call):
    await callAnswer(call, '👥 群成员同步开始')
    LOGGER.info(f"【群组成员同步任务开启】 - {call.from_user.first_name} - {call.from_user.id}")
    await _show_maintain(call, '👥 群成员同步执行中，结果会单独发送')
    await sync_group_members(_reporter(call))


@bot.on_callback_query(filters.regex(r'^mtask_unb$') & admins_on_filter)
async def maintain_unbound(_, call):
    await callAnswer(call, '🔗 正在检查…')
    ok, unbound = await find_unbound_accounts()
    if not ok:
        return await _show_maintain(call, f'⚠️ 读取账号失败：{unbound}')
    if not unbound:
        return await _show_maintain(call, '✅ 所有账号都在 embyboss 数据库中有记录')
    names = '\n'.join(f'· {name}' for _id, name in unbound[:50])
    more = f'\n…… 共 {len(unbound)} 个' if len(unbound) > 50 else ''
    kb = InlineKeyboard(row_width=2)
    kb.add(InlineButton(f'⚠️ 删除这 {len(unbound)} 个账号', 'mtask_unbok'), InlineButton('取消', 'mtask'))
    await editMessage(call, f'🔗 **账号一致性检查**\n\n以下账号在 sidecar 中存在，但 embyboss 数据库没有记录：\n{names}{more}\n\n'
                            f'若是手动开的账号，请改用「🧾 额外账号」登记，不要删除。', buttons=kb)


@bot.on_callback_query(filters.regex(r'^mtask_unbok$') & admins_on_filter)
async def maintain_unbound_ok(_, call):
    await callAnswer(call, '🔗 开始清理')
    LOGGER.info(f"【账号一致性清理】由 {call.from_user.id} 执行")
    await _show_maintain(call, '🔗 清理执行中，结果会单独发送')
    await delete_unbound_accounts(_reporter(call))


@bot.on_callback_query(filters.regex(r'^mtask_bak$') & admins_on_filter)
async def maintain_backup(_, call):
    if call.from_user.id != owner:
        return await callAnswer(call, '仅 owner 可用', True)
    await callAnswer(call, '💾 正在备份…')
    await run_backup_db()


@bot.on_callback_query(filters.regex(r'^mtask_rst$') & admins_on_filter)
async def maintain_restart(_, call):
    if call.from_user.id != owner:
        return await callAnswer(call, '仅 owner 可用', True)
    await callAnswer(call, '🔁 重启中…')
    send = await call.message.reply("Restarting，等待几秒钟。")
    await asyncio.sleep(0.5)
    restart_bot(send.chat.id, send.id)
