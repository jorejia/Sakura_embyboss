"""
定时检测账户有无过期
"""
from datetime import timedelta, datetime

from pyrogram.errors import FloodWait
from sqlalchemy import and_
from asyncio import sleep
from bot import bot, default_line_id, group, LOGGER, _open, schedall
from bot.func_helper.emby import emby
from bot.func_helper.line_access import revoke_line_pro_access
from bot.sql_helper.sql_emby import Emby, get_all_emby, sql_update_emby
from bot.sql_helper.sql_emby2 import get_all_emby2, Emby2, sql_update_emby2


async def check_line_pro_expired():
    now = datetime.now()
    expired_users = get_all_emby(and_(Emby.line_pro_ex.isnot(None), Emby.line_pro_ex <= now))
    if not expired_users:
        LOGGER.info('【直连Pro到期检测】- 无到期用户，跳过')
        return

    for user in expired_users:
        revoked, failed_stage, result = await revoke_line_pro_access(
            user.embyid,
            default_line_id,
            emby.set_use_line,
            lambda: sql_update_emby(
                and_(Emby.tg == user.tg, Emby.line_pro_ex <= now),
                line_pro_ex=None,
            ),
        )
        if not revoked and failed_stage == 'line':
            text = (f'【直连Pro到期检测】\n#id{user.tg} [{user.name}](tg://user?id={user.tg}) '
                    f'权限已到期，但切回默认线路失败：{result}，下次任务将重试')
            LOGGER.error(text)
            try:
                await bot.send_message(user.tg, text)
            except Exception as error:
                LOGGER.error(error)
            continue

        if revoked:
            text = (f'【直连Pro到期检测】\n#id{user.tg} [{user.name}](tg://user?id={user.tg}) '
                    f'直连Pro已到期，权限已取消并切回默认线路 {default_line_id}')
            LOGGER.info(text)
        else:
            text = (f'【直连Pro到期检测】\n#id{user.tg} [{user.name}](tg://user?id={user.tg}) '
                    f'已切回默认线路 {default_line_id}，但数据库撤权失败，下次任务将重试')
            LOGGER.error(text)
        try:
            await bot.send_message(user.tg, text)
        except FloodWait as flood_wait:
            LOGGER.warning(str(flood_wait))
            await sleep(flood_wait.value * 1.2)
            await bot.send_message(user.tg, text)
        except Exception as error:
            LOGGER.error(error)


async def check_expired():
    if schedall.check_ex_paused:
        LOGGER.info('【到期检测】- 当前为暂停状态，本次任务不执行')
        return 'paused'

    await check_line_pro_expired()
    # 到期用户仅允许使用余额自动续期；否则禁用并进入封存期。
    rst = get_all_emby(and_(Emby.ex < datetime.now(), Emby.lv == 'b'))
    if rst is None:
        return LOGGER.info('【到期检测】- 等级 b 无到期用户，跳过')
    dead_day = datetime.now() + timedelta(days=5)
    ext = (datetime.now() + timedelta(days=30))
    for r in rst:
        if _open.exchange and r.iv >= _open.exchange_cost * 30:
            b = r.iv - _open.exchange_cost * 30
            if sql_update_emby(Emby.tg == r.tg, ex=ext, iv=b):
                text = f'【到期检测】\n#id{r.tg} 续期账户 [{r.name}](tg://user?id={r.tg})\n' \
                       f'在当前时间自动续期30天\n' \
                       f'📅实时到期: {ext.strftime("%Y-%m-%d %H:%M:%S")}'
                LOGGER.info(text)
            else:
                text = f'【到期检测】\n#id{r.tg} 续期账户 [{r.name}](tg://user?id={r.tg})\n续期失败，请联系闺蜜（管理）'
                LOGGER.error(text)
            try:
                await bot.send_message(r.tg, text)
            except FloodWait as f:
                LOGGER.warning(str(f))
                await sleep(f.value * 1.2)
                await bot.send_message(r.tg, text)
            except Exception as e:
                LOGGER.error(e)

        else:
            if await emby.emby_change_policy(r.embyid, method=True):
                if sql_update_emby(Emby.tg == r.tg, lv='c'):
                    text = f'【到期检测】\n#id{r.tg} 账号已到期 [{r.name}](tg://user?id={r.tg})\n数据将为您封存保留至 {dead_day.strftime("%Y-%m-%d")}，请及时续期'
                    LOGGER.info(text)
                else:
                    text = f'【到期检测】\n#id{r.tg} 到期禁用 [{r.name}](tg://user?id={r.tg}) 已禁用，数据库写入失败'
                    LOGGER.warning(text)
            else:
                text = f'【到期检测】\n#id{r.tg} 到期禁用 [{r.name}](tg://user?id={r.tg}) embyapi操作失败'
                LOGGER.error(text)
            try:
                await bot.send_message(r.tg, text)
            except FloodWait as f:
                LOGGER.warning(str(f))
                await sleep(f.value * 1.2)
                await bot.send_message(r.tg, text)
            except Exception as e:
                LOGGER.error(e)

    rsc = get_all_emby(and_(Emby.ex < datetime.now(), Emby.lv == 'c'))
    if rsc is None:
        return LOGGER.info('【到期检测】- 等级 c 无到期用户，跳过')
    for c in rsc:
        delta = c.ex + timedelta(days=5)
        if datetime.now() < delta:
            continue
        if await emby.emby_del(c.embyid):
            text = f'【到期检测】\n#id{c.tg} 删除账户 [{c.name}](tg://user?id={c.tg})\n已到期 5 天，执行清除任务。期待下次与你相遇'
            LOGGER.info(text)
        else:
            text = f'【到期检测】\n#id{c.tg} #删除账户 [{c.name}](tg://user?id={c.tg})\n到期删除失败，请检查以免无法进行后续使用'
            LOGGER.warning(text)
        try:
            send = await bot.send_message(c.tg, text)
            await send.forward(group[0])
        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value * 1.2)
            send = await bot.send_message(c.tg.text)
            await send.forward(group[0])
        except Exception as e:
            LOGGER.error(e)

    rseired = get_all_emby2(and_(Emby2.expired == 0, Emby2.ex < datetime.now()))
    if rseired is None:
        return LOGGER.info(f'【封禁检测】- emby2 无数据，跳过')
    for e in rseired:
        if await emby.emby_change_policy(id=e.embyid, method=True):
            if sql_update_emby2(Emby2.embyid == e.embyid, expired=1):
                text = f"【封禁检测】- 到期封印非TG账户 [{e.name}](google.com?q={e.embyid}) Done！"
                LOGGER.info(text)
            else:
                text = f'【封禁检测】- 到期封印非TG账户：`{e.name}` 数据库更改失败'
        else:
            text = '【封禁检测】- 到期封印非TG账户：`{e.name}` embyapi操作失败，请手动'
        try:
            await bot.send_message(group[0], text)
        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value * 1.2)
            await bot.send_message(group[0].text)
        except Exception as e:
            LOGGER.error(e)
