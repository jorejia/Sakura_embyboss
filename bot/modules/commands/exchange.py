"""
兑换注册码exchange
"""
import requests
import time
from datetime import timedelta, datetime

from bot import bot, _open, LOGGER, bot_photo, user_buy
from bot.func_helper.emby import emby
from bot.func_helper.line_access import line_pro_status_text
from bot.func_helper.fix_bottons import register_code_ikb
from bot.func_helper.msg_utils import sendMessage, sendPhoto
from bot.sql_helper.sql_code import Code
from bot.sql_helper.sql_emby import sql_get_emby, Emby
from bot.sql_helper import Session


async def _redeem_line_code(msg, register_code, data):
    if not data.embyid:
        return await sendMessage(msg, "🔔 **尚未拥有 Emby 账号**\n线路码只能用于已绑定的 Emby 账号。", timer=60)

    now = datetime.now()
    with Session() as session:
        code = session.query(Code).filter(Code.code == register_code).with_for_update().first()
        if not code or code.invite != 'l':
            return await sendMessage(msg, "⛔ **线路码无效，请确认后重试。**", timer=60)
        if code.used is not None:
            return await sendMessage(
                msg,
                f'此 `{register_code}` 线路码已被 [{code.used}](tg://user?id={code.used}) 使用。'
            )

        user = session.query(Emby).filter(Emby.tg == msg.from_user.id).with_for_update().first()
        if user is None or not user.embyid:
            return await sendMessage(msg, "🔔 **尚未拥有 Emby 账号**\n线路码只能用于已绑定的 Emby 账号。", timer=60)

        days = code.us
        base_ex = user.line_pro_ex if user.line_pro_ex and user.line_pro_ex > now else now
        line_pro_ex = base_ex + timedelta(days=days)
        updated = session.query(Code).filter(
            Code.code == register_code,
            Code.invite == 'l',
            Code.used.is_(None)
        ).update({Code.used: msg.from_user.id, Code.usedtime: now})
        if updated == 0:
            session.rollback()
            return await sendMessage(msg, '⛔ 线路码已被使用，请勿重复兑换。', timer=60)
        user.line_pro_ex = line_pro_ex
        user.line_pro_trial_used = 1
        session.commit()

    masked_code = register_code[:-7] + "░" * 7
    await sendMessage(
        msg,
        f'🎊 直连Pro已激活 {days} 天\n'
        f'📅 到期时间：**{line_pro_status_text(line_pro_ex)}**\n\n'
        f'现在可在「直连切线」中查看并切换 Pro 线路。'
    )
    LOGGER.info(
        f"【线路码】：{msg.from_user.first_name}[{msg.chat.id}] 使用了 {masked_code}，"
        f"直连Pro到期时间：{line_pro_ex}"
    )


async def rgs_code(_, msg, register_code):
    data = sql_get_emby(tg=msg.from_user.id)
    if not data: return await sendMessage(msg, "请先点击 /start ，否则无法使用注册码")
    embyid = data.embyid
    ex = data.ex
    lv = data.lv
    us = data.us
    with Session() as session:
        code_info = session.query(Code.invite).filter(Code.code == register_code).first()
    if not code_info:
        return await sendMessage(msg, "⛔ **你输入了一个错误de注册码，请确认好重试。**", timer=60)
    code_type = code_info[0]
    if code_type == 'l':
        return await _redeem_line_code(msg, register_code, data)
    if _open.stat:
        return await sendMessage(msg, "🤧 自由注册开启下无法使用注册码。")
    if code_type == 'a':
        if embyid:
            return await sendMessage(msg, "🔔 **已有账号**\n活动码只能无账号的情况下使用哦~", timer=60)
        if us != 0:
            return await sendMessage(msg, "🔔 **已有注册码**\n无法重复使用，快去创建账号吧，不可以贪心的哦~", timer=60)
    if embyid is None and us > 0 and not _open.allow_code:
        return await sendMessage(msg, "🔔 **已有注册码**\n无法重复使用，快去创建账号吧，不可以贪心的哦~", timer=60)
    elif embyid:
        if not _open.allow_code:
            return await sendMessage(msg, "🔔 **已有账号**\n当前群活动中，临时关闭续费，等待活动结束（一般1-2小时）即可恢复~", timer=60)
        with Session() as session:
            # with_for_update 是一个排他锁，其实就不需要悲观锁或者是乐观锁，先锁定先到的数据使其他session无法读取，修改(单独似乎不起作用，也许是不能完全防止并发冲突，于是加入原子操作)
            r = session.query(Code).filter(Code.code == register_code).with_for_update().first()
            if not r: return await sendMessage(msg, "⛔ **你输入了一个错误de注册码，请确认好重试。**", timer=60)
            re = session.query(Code).filter(Code.code == register_code, Code.used.is_(None)).with_for_update().update(
                {Code.used: msg.from_user.id, Code.usedtime: datetime.now()})
            session.commit()  # 必要的提交。否则失效
            tg1 = r.tg
            us1 = r.us
            used = r.used
            if re == 0: return await sendMessage(msg,
                                                 f'此 `{register_code}` \n注册码已被使用,是[{used}](tg://user?id={used})的形状了喔')
            session.query(Code).filter(Code.code == register_code).with_for_update().update(
                {Code.used: msg.from_user.id, Code.usedtime: datetime.now()})
            first = await bot.get_chat(tg1)
            # 此处需要写一个判断 now和ex的大小比较。进行日期加减。
            ex_new = datetime.now()
            if lv == 'c':
                ex_new = ex_new + timedelta(days=us1)               
                session.query(Emby).filter(Emby.tg == msg.from_user.id).update({Emby.ex: ex_new, Emby.lv: 'b'})
                session.commit()
                time.sleep(1)
                datac = sql_get_emby(tg=msg.from_user.id)
                lvc = datac.lv
                if lvc == 'c':
                    await sendMessage(msg,
                                    f'续费失败，请看用户手册第18条申诉')
                else:
                    await emby.emby_change_policy(id=embyid, method=False)
                    await sendMessage(msg, f'🎊 少年郎，恭喜你，已续费 {us1} 天🎁\n'
                                        f'请点击 /myinfo 确认续费时长已到账，如有疑问，可以看用户手册第18条申诉')                   
            elif lv == 'b' or lv == 'a':
                base_ex = data.ex if data.ex and data.ex > datetime.now() else datetime.now()
                ex_new = base_ex + timedelta(days=us1)
                session.query(Emby).filter(Emby.tg == msg.from_user.id).update({Emby.ex: ex_new})
                session.commit()
                await sendMessage(msg,
                                  f'🎊 少年郎，恭喜你，已续费 {us1} 天🎁\n请点击 /myinfo 确认续费时长已到账，如有疑问，可以看用户手册第18条申诉')
            else:
                await sendMessage(msg,
                                  f'⚠️ 当前账户状态 `{lv}` 暂不支持使用注册码续期，请联系管理员检查。')
            session.commit()
            new_code = register_code[:-7] + "░" * 7
            LOGGER.info(f"【续费】：{msg.from_user.first_name}[{msg.chat.id}] 使用了 {register_code}，到期时间：{ex_new}")

    else:
        with Session() as session:
            # 我勒个豆，终于用 原子操作 + 排他锁 成功防止了并发更新
            # 在 UPDATE 语句中添加一个条件，只有当注册码未被使用时，才更新数据。这样，如果有两个用户同时尝试使用同一条注册码，只有一个用户的 UPDATE 语句会成功，因为另一个用户的 UPDATE 语句会发现注册码已经被使用。
            r = session.query(Code).filter(Code.code == register_code).with_for_update().first()
            if not r: return await sendMessage(msg, "⛔ **你输入了一个错误de注册码，请确认好重试。**", timer=60)
            re = session.query(Code).filter(Code.code == register_code, Code.used.is_(None)).with_for_update().update(
                {Code.used: msg.from_user.id, Code.usedtime: datetime.now()})
            session.commit()  # 必要的提交。否则失效
            tg1 = r.tg
            us1 = r.us
            in1 = r.invite
            used = r.used
            if re == 0: return await sendMessage(msg,
                                                 f'此 `{register_code}` \n注册码已被使用,是 [{used}](tg://user?id={used}) 的形状了喔')
            first = await bot.get_chat(tg1)
            x = data.us + us1
            session.query(Emby).filter(Emby.tg == msg.from_user.id).update({Emby.us: x, Emby.invite: in1})
            session.commit()
            new_code = register_code[:-7] + "░" * 7
            if in1 == 'y':
                await sendPhoto(msg, photo=bot_photo,
                                  caption=f'🎊 少年郎，恭喜你，已经收到了 [{first.first_name}](tg://user?id={tg1}) 发送的邀请注册资格\n\n请选择你的选项~',
                                  buttons=register_code_ikb)
                await sendMessage(msg,
                                  f'· 🎟️ 邀请码使用 - [{msg.from_user.first_name}](tg://user?id={msg.chat.id}) [{msg.from_user.id}] 使用了 {new_code} 尊贵的邀请码闪瞎了眼，可以直接创建 {us1} 天账户',
                                  send=True)
            else:
                await sendPhoto(msg, photo=bot_photo,
                                  caption=f'🎊 少年郎，恭喜你，已经成功使用注册码，未注册期间不计时\n\n请选择你的选项~',
                                  buttons=register_code_ikb)
                await sendMessage(msg,
                                  f'· 🎟️ 注册码使用 - [{msg.from_user.first_name}](tg://user?id={msg.chat.id}) [{msg.from_user.id}] 使用了 {new_code} 获得 {us1} 天预注册时长，请在服务器未满时创建账户',
                                  send=True)
                if us1 == 3:
                    url = "http://127.0.0.1:5000/webhook"
                    try:
                        response = requests.get(url, timeout=5)
                        if response.status_code >= 400:
                            LOGGER.warning(f"【本机Webhook网络】GET {url} 返回 HTTP {response.status_code}，body={response.text[:200]}")
                    except requests.exceptions.Timeout as e:
                        LOGGER.error(f"【本机Webhook网络】GET {url} 超时，请检查 127.0.0.1:5000 服务是否启动。error={type(e).__name__}: {e}")
                    except requests.exceptions.ConnectionError as e:
                        LOGGER.error(f"【本机Webhook网络】GET {url} 连接失败，请检查端口、防火墙或 webhook 服务。error={type(e).__name__}: {e}")
                    except requests.exceptions.RequestException as e:
                        LOGGER.error(f"【本机Webhook网络】GET {url} 请求异常。error={type(e).__name__}: {e}")


            LOGGER.info(
                f"【注册码】：{msg.from_user.first_name}[{msg.chat.id}] 使用了 {register_code} - 可创建 {us1}天账户")


# @bot.on_message(filters.regex('exchange') & filters.private & user_in_group_on_filter)
# async def exchange_buttons(_, call):
#
#     await rgs_code(_, msg)
