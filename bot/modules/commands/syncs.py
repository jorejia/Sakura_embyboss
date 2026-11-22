"""
账号同步类维护任务（由管理菜单「🧰 维护」调用，不再提供命令）

1. 群组成员同步：遍历数据库中等级 b 账户，检测是否仍在群组，否 -> 删除账号（保留用户记录）
2. 账号一致性检查：列出 sidecar 中存在、但 embyboss 数据库没有记录的账号，确认后删除

已移除：
- /deleted（清理死号）：退群即删号的逻辑已覆盖，单独的注销号清理不再需要
- /embyadmin：账号不在 Emby 原后端，没有 Emby 控制台权限可开
- /bindall_id：账号由 embyboss 创建，embyid 天然一致，不再需要按名称回填
"""
import time
from asyncio import sleep
from datetime import datetime

from pyrogram.errors import FloodWait

from bot import bot, LOGGER, group
from bot.func_helper.emby import emby
from bot.sql_helper.sql_emby import get_all_emby, Emby, sql_get_emby


def _chunks(text, n=1000):
    return [text[i:i + n] for i in range(0, len(text), n)] or ['']


async def sync_group_members(report):
    """群组成员同步。report(text) 用于把进度 / 结果发回管理员。"""
    members = [member.user.id async for member in bot.get_chat_members(group[0])]
    r = get_all_emby(Emby.lv == 'b')
    if not r:
        return await report("⚡群组同步任务\n\n结束！没有需要检查的账户。")
    a = b = 0
    text = ''
    start = time.perf_counter()
    for i in r:
        b += 1
        if i.tg not in members:
            if await emby.emby_del(i.embyid):
                a += 1
                reply_text = f'{b}. #id{i.tg} - [{i.name}](tg://user?id={i.tg}) 账号删除，用户记录保留\n'
                LOGGER.info(reply_text)
            else:
                reply_text = f'{b}. #id{i.tg} - [{i.name}](tg://user?id={i.tg}) 删除错误\n'
                LOGGER.error(reply_text)
            text += reply_text
            try:
                await bot.send_message(i.tg, reply_text)
            except FloodWait as f:
                LOGGER.warning(str(f))
                await sleep(f.value * 1.2)
                await bot.send_message(i.tg, reply_text)
            except Exception as e:
                LOGGER.error(e)
    for c in _chunks(text):
        if c:
            await report(c + f'\n🔈 当前时间：{datetime.now().strftime("%Y-%m-%d")}')
    times = time.perf_counter() - start
    if a:
        await report(f"**⚡群组成员同步任务 结束！**\n  共检索出 {b} 个账户，删除 {a} 个账户，耗时：{times:.3f}s")
    else:
        await report("**群组成员同步任务 结束！没人偷跑~**")
    LOGGER.info(f"【群组同步任务结束】共检索出 {b} 个账户，删除 {a} 个账户，耗时：{times:.3f}s")


async def find_unbound_accounts():
    """返回 (True, [(id, name)]) / (False, 错误)：sidecar 中存在、embyboss 数据库没有记录的非管理员账号。"""
    success, alluser = await emby.users()
    if not success or alluser is None:
        return False, alluser
    unbound = []
    for v in alluser:
        try:
            if v.get('Policy') and bool(v['Policy'].get('IsAdministrator')):
                continue
            if sql_get_emby(v['Id']) is None:
                unbound.append((v['Id'], v['Name']))
        except Exception as e:
            LOGGER.warning(e)
    return True, unbound


async def delete_unbound_accounts(report):
    """删除未绑定账号（调用前应已向管理员展示过清单并确认）。"""
    ok, unbound = await find_unbound_accounts()
    if not ok:
        return await report(f"⚠️ 读取账号列表失败：{unbound}")
    a = 0
    text = ''
    for embyid, name in unbound:
        if await emby.emby_del(embyid):
            a += 1
            text += f"🎯 #{name} 未绑定bot，删除\n"
        else:
            text += f"🌧️ #{name} 未绑定bot，删除失败\n"
    for c in _chunks(text):
        if c:
            await report(c)
    await report(f"⚡账号一致性清理完成：共 {len(unbound)} 个未绑定账号，删除 {a} 个")
    LOGGER.info(f"【账号一致性清理】未绑定 {len(unbound)} 个，删除 {a} 个")
