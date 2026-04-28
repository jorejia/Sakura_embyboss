"""
用户区面板代码
先检测有无账户
无 -> 创建账户、换绑tg

有 -> 账户续期，重置密码，删除账户，显隐媒体库
"""
import asyncio
import datetime
import math
import random
from datetime import timedelta, datetime

from pyrogram.errors import BadRequest
from bot.schemas import ExDate, Yulv
from bot import bot, LOGGER, _open, emby_line, sakura_b, ranks, group, extra_emby_libs, config, user_buy, \
    bot_name
from pyrogram import filters
from bot.func_helper.emby import emby
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.utils import members_info, tem_alluser, cr_link_one, cr_link_invite
from bot.func_helper.fix_bottons import members_ikb, back_members_ikb, re_create_ikb, del_me_ikb, re_delme_ikb, \
    re_reset_ikb, re_changetg_ikb, emby_block_ikb, user_emby_block_ikb, user_emby_unblock_ikb, re_exchange_b_ikb, \
    dianbo_ikb, re_douban_ikb, store_ikb, store_vip_ikb, store_c_ikb, re_store_renew, re_bindtg_ikb, close_it_ikb, \
    user_query_page, notify_menu_ikb, parental_menu_ikb, parental_rating_label, line_menu_ikb, line_label
from bot.func_helper.msg_utils import callAnswer, editMessage, callListen, sendMessage, ask_return, deleteMessage
from bot.modules.commands import p_start
from bot.modules.commands.exchange import rgs_code
from bot.sql_helper.sql_code import sql_count_c_code
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby, sql_delete_emby
from bot.sql_helper.sql_emby2 import sql_get_emby2, sql_delete_emby2
from bot.sql_helper import Session

# 创号函数
async def create_user(_, call, us, stats):
    same = await editMessage(call,
                             text='🤖**注意：您已进入注册状态:\n\n• 请在2min内输入 `[用户名][空格][安全码]`\n• 举个例子🌰：`username 1234`**\n\n• 用户名尽量使用英文，用于emby登陆'
                                  '\n• 安全码用于重置密码等操作，请填入最熟悉的数字4~6位；退出请点 /cancel')
    if same is False:
        return

    txt = await callListen(call, 120, buttons=back_members_ikb)
    if txt is False:
        return

    elif txt.text == '/cancel':
        return await asyncio.gather(txt.delete(),
                                    editMessage(call, '__您已经取消输入__ **会话已结束！**', back_members_ikb))
    else:
        try:
            await txt.delete()
            emby_name, emby_pwd2 = txt.text.split()
        except (IndexError, ValueError):
            await editMessage(call, f'⚠️ 输入格式错误\n【`{txt.text}`】\n **会话已结束！**', re_create_ikb)
        else:
            await editMessage(call,
                              f'🆗 会话结束，收到设置\n\n用户名：**{emby_name}**  安全码：**{emby_pwd2}** \n\n__正在为您初始化账户，更新用户策略__......')
            try:
                x = int(emby_name)
            except ValueError:
                pass
            else:
                try:
                    await bot.get_chat(x)
                except BadRequest:
                    pass
                else:
                    return await editMessage(call, "🚫 根据银河正义法，您创建的用户名不得与任何 tg_id 相同",
                                             re_create_ikb)
            # await asyncio.sleep(1)
            # emby api操作
            pwd1 = await emby.emby_create(call.from_user.id, emby_name, emby_pwd2, us, stats)
            if pwd1 == 403:
                await editMessage(call, '**🚫 很抱歉，注册总数已达限制。**', back_members_ikb)
            elif pwd1 == 100:
                await editMessage(call,
                                  '**- ❎ 已有此账户名，请重新输入注册\n- ❎ 或检查有无特殊字符\n- ❎ 或emby服务器连接不通，会话已结束！**',
                                  re_create_ikb)
                LOGGER.error("【创建账户】：重复账户 or 未知错误！")
            else:
                await editMessage(call,
                                  f'**▎创建用户成功🎉**\n\n'
                                  f'· 用户名称 | `{emby_name}`\n'
                                  f'· 登陆密码 | `{pwd1[0]}`\n'
                                  f'· 安全码 | {emby_pwd2}（仅用于重置密码）\n'
                                  f'· 到期时间 | {pwd1[1]}\n'
                                  f'· 服务器地址 | 见下方用户手册，请认真看使用限制，否则连不上\n\n'
                                  f'**·[【必看用户手册】](https://micu.hk/archives/emby-users) - 手册口令 a1234**')
                if stats == 'y':
                    LOGGER.info(f"【创建账户】[开注状态]：{call.from_user.id} - 建立了 {emby_name} ")
                elif stats == 'n':
                    LOGGER.info(f"【创建账户】：{call.from_user.id} - 建立了 {emby_name} ")
                await tem_alluser()


# 键盘中转
@bot.on_callback_query(filters.regex('members') & user_in_group_on_filter)
async def members(_, call):
    data = await members_info(tg=call.from_user.id)
    if not data:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start录入', True)

    await callAnswer(call, f"✅ 用户界面")
    name, lv, ex, us, embyid, pwd2, douban = data
    if douban is None:
        douban = '未绑定'
    text = f"▎__欢迎进入用户面板！{call.from_user.first_name}__\n\n" \
           f"**· 🍒 用户のID** | `{call.from_user.id}`\n" \
           f"**· 🍓 当前状态** | {lv}\n" \
           f"**· 🫛 豆瓣のID** | `{douban}`\n" \
           f"**· 🍥 当前{sakura_b}** | {us[1]}\n" \
           f"**· ⏰ 未用天数** | {us[0]}\n" \
           f"**· 💠 账号名称** | {name}\n" \
           f"**· 🚨 到期时间** | **{ex}**\n"
    if not embyid:
        await editMessage(call, text, members_ikb(False))
    else:
        await editMessage(call, text, members_ikb(True))


# 创建账户
@bot.on_callback_query(filters.regex('create') & user_in_group_on_filter)
async def create(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    if not e:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start录入', True)

    if e.embyid:
        await callAnswer(call, '💦 你已经有账户啦！请勿重复注册。', True)
    elif not _open.stat and int(e.us) <= 0:
        await callAnswer(call, f'🤖 当前没有可注册时长，请先使用注册码', True)
    elif not _open.stat and int(e.us) > 0:
        if _open.tem < _open.all_user:
            send = await callAnswer(call, f'🪙 欢迎注册 MICU Cloud Media，请稍后。', True)
            if send is False:
                return
            else:
                await create_user(_, call, us=e.us, stats='n')
        else:
            if e.invite == 'y':
                send = await callAnswer(call, f'🪙 欢迎注册 MICU Cloud Media，请稍后。', True)
                if send is False:
                    return
                else:
                    sql_update_emby(Emby.tg == call.from_user.id, invite='n')
                    await create_user(_, call, us=e.us, stats='n')
            else:
                send = await callAnswer(call, f'🤖 当前服务器人数已达上限，无法注册，请耐心等待。', True)


    elif _open.stat:
        send = await callAnswer(call, f"🪙 开放注册，免除积分要求。", True)
        if send is False:
            return
        else:
            await create_user(_, call, us=30, stats='y')


# 换绑tg
@bot.on_callback_query(filters.regex('changetg') & user_in_group_on_filter)
async def change_tg(_, call):
    d = sql_get_emby(tg=call.from_user.id)
    if not d:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start录入', True)
    if d.embyid:
        return await callAnswer(call, '⚖️ 您已经拥有账户，请不要钻空子', True)

    await callAnswer(call, '⚖️ 更换绑定的TG')
    send = await editMessage(call,
                             '🔰 **【更换绑定emby的tg】**\n'
                             '须知：\n'
                             '- **请确保您之前用其他tg账户注册过**\n'
                             '- **请确保您注册的其他tg账户呈已注销状态**\n'
                             '- **请确保输入正确的emby用户名，安全码/密码**\n\n'
                             '您有120s回复 `[emby用户名] [安全码(或密码)]`\n例如 `苏苏 5210` ，安全码和密码只需要任意其一，退出点 /cancel')
    if send is False:
        return

    m = await callListen(call, 120, buttons=back_members_ikb)
    if m is False:
        return

    elif m.text == '/cancel':
        await m.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**', back_members_ikb)
    else:
        try:
            await m.delete()
            emby_name, emby_pwd = m.text.split()
        except (IndexError, ValueError):
            return await editMessage(call, f'⚠️ 输入格式错误\n【`{m.text}`】\n **会话已结束！**', re_changetg_ikb)

        await editMessage(call,
                          f'✔️ 会话结束，收到设置\n\n用户名：**{emby_name}** 正在检查码 **{emby_pwd}**......')

        pwd = '空（直接回车）', 5210 if emby_pwd == 'None' else emby_pwd, emby_pwd
        e = sql_get_emby(tg=emby_name)
        replace_tg=e.tg

        if emby_pwd != e.pwd2:
            LOGGER.info(f'emby_pwd: {emby_pwd}, e.pwd2: {e.pwd2}')
            success, embyid = await emby.authority_account(call.from_user.id, emby_name, emby_pwd)
            if not success:
                return await editMessage(call,
                                            f'💢 安全码or密码验证错误，请检查输入\n{emby_name} {emby_pwd} 是否正确。',
                                            buttons=re_changetg_ikb)
            text = f'⭕ 账户 {emby_name} 的密码验证成功！\n\n' \
                    f'· 用户名称 | `{emby_name}`\n' \
                    f'· 用户密码 | `{pwd[0]}`\n' \
                    f'· 安全密码 | `{e.pwd2}`（仅发送一次）\n' \
                    f'· 到期时间 | `{e.ex}`'
        elif emby_pwd == e.pwd2:
            text = f'⭕ 账户 {emby_name} 的安全码验证成功！\n\n' \
                    f'· 用户名称 | `{emby_name}`\n' \
                    f'· 用户密码 | `{e.pwd}`\n' \
                    f'· 安全密码 | `{pwd[1]}`（仅发送一次）\n' \
                    f'· 到期时间 | `{e.ex}`'
        f = None
        try:
            f = await bot.get_users(user_ids=e.tg)
        except Exception as ex:
            LOGGER.error(f'【TG改绑】 emby账户{emby_name} 通过tg api获取{e.tg}用户失败，原因：{ex}')
        if f is not None and not f.is_deleted:
            await sendMessage(call,
                                f'⭕#TG改绑 **用户 [{call.from_user.id}](tg://user?id={call.from_user.id}) 正在试图改绑一个状态正常的[tg用户](tg://user?id={e.tg}) - {e.name}\n\n请管理员检查。**',
                                send=True)
            return await editMessage(call,
                                        f'⚠️ **你所要换绑的[tg](tg://user?id={e.tg}) - {e.tg}\n\n用户状态正常！无须换绑。**',
                                        buttons=back_members_ikb)
        if sql_update_emby(Emby.tg == call.from_user.id, embyid=e.embyid, name=e.name, pwd=e.pwd, pwd2=e.pwd2,
                            lv=e.lv, cr=e.cr, ex=e.ex, iv=e.iv):
            await sendMessage(call,
                                f'⭕#TG改绑 原emby账户 #{emby_name} \n\n已绑定至 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) - {call.from_user.id}',
                                send=True)
            LOGGER.info(
                f'【TG改绑】 emby账户 {emby_name} 绑定至 {call.from_user.first_name}-{call.from_user.id}')
            await editMessage(call, text)
        else:
            await editMessage(call, '🍰 **【TG改绑】数据库处理出错，请联系闺蜜（管理）！**', back_members_ikb)
            LOGGER.error(f"【TG改绑】 emby账户{emby_name} 绑定未知错误。")
        if sql_delete_emby(tg=replace_tg):
            LOGGER.info(f'【TG改绑】删除原账户 id{e.tg}, Emby:{e.name} 成功...')
        else:
            await editMessage(call, "🍰 **⭕#TG改绑 原账户删除错误，请联系闺蜜（管理）！**", back_members_ikb)
            LOGGER.error(f"【TG改绑】删除原账户 id{e.tg}, Emby:{e.name} 失败...")


@bot.on_callback_query(filters.regex('bindtg') & user_in_group_on_filter)
async def bind_tg(_, call):
    d = sql_get_emby(tg=call.from_user.id)
    if d.embyid is not None:
        return await callAnswer(call, '⚖️ 您已经拥有账户，请不要钻空子', True)
    await callAnswer(call, '⚖️ 将账户绑定TG')
    send = await editMessage(call,
                             '🔰 **【已有emby绑定至tg】**\n'
                             '须知：\n'
                             '- **请确保您需绑定的账户不在bot中**\n'
                             '- **请确保您不是恶意绑定他人的账户**\n'
                             '- **请确保输入正确的emby用户名，密码**\n\n'
                             '您有120s回复 `[emby用户名] [密码]`\n例如 `苏苏 5210` ，若密码为空则填写“None”，退出点 /cancel')
    if send is False:
        return

    m = await callListen(call, 120, buttons=back_members_ikb)
    if m is False:
        return

    elif m.text == '/cancel':
        await m.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**', back_members_ikb)
    else:
        try:
            await m.delete()
            emby_name, emby_pwd = m.text.split()
        except (IndexError, ValueError):
            return await editMessage(call, f'⚠️ 输入格式错误\n【`{m.text}`】\n **会话已结束！**', re_bindtg_ikb)
        await editMessage(call,
                          f'✔️ 会话结束，收到设置\n\n用户名：**{emby_name}** 正在检查密码 **{emby_pwd}**......')
        e = sql_get_emby(tg=emby_name)
        if e is None:
            e2 = sql_get_emby2(name=emby_name)
            if e2 is None:
                success, embyid = await emby.authority_account(call.from_user.id, emby_name, emby_pwd)
                if not success:
                    return await editMessage(call,
                                             f'🍥 很遗憾绑定失败，您输入的账户密码不符（{emby_name} - {emby_pwd}），请仔细确认后再次尝试',
                                             buttons=re_bindtg_ikb)
                else:
                    pwd = ['空（直接回车）', 5210] if emby_pwd == 'None' else [emby_pwd, emby_pwd]
                    ex = (datetime.now() + timedelta(days=30))
                    text = f'✅ 账户 {emby_name} 成功绑定\n\n' \
                           f'· 用户名称 | `{emby_name}`\n' \
                           f'· 登陆密码 | `{pwd[0]}`\n' \
                           f'· 安全码 | {pwd[1]}（仅用于重置密码）\n' \
                           f'· 到期时间 | {ex}\n' \
                           f'· 服务器地址 | 见下方用户手册，请认真看使用限制，否则连不上\n\n' \
                           f'**·[【必看用户手册】](https://micu.hk/archives/emby-users) - 手册口令 a1234**'
                    sql_update_emby(Emby.tg == call.from_user.id, embyid=embyid, name=emby_name, pwd=emby_pwd,
                                    pwd2=emby_pwd, lv='b', cr=datetime.now(), ex=ex)
                    await editMessage(call, text)
                    await sendMessage(call,
                                      f'⭕#新TG绑定 原emby账户 #{emby_name} \n\n已绑定至 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) - {call.from_user.id}',
                                      send=True)
                    LOGGER.info(
                        f'【新TG绑定】 emby账户 {emby_name} 绑定至 {call.from_user.first_name}-{call.from_user.id}')
            else:
                await editMessage(call, '🔍 数据库已有此账户，不可绑定，请使用 **换绑TG**', buttons=re_changetg_ikb)
        else:
            await editMessage(call, '🔍 数据库已有此账户，不可绑定，请使用 **换绑TG**', buttons=re_changetg_ikb)


# kill yourself
@bot.on_callback_query(filters.regex('delme') & user_in_group_on_filter)
async def del_me(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    if e is None:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start录入', True)
    else:
        if e.embyid is None:
            return await callAnswer(call, '未查询到账户，不许乱点！💢', True)
        await callAnswer(call, "🔴 请先进行 安全码 验证")
        edt = await editMessage(call, '**🔰账户安全验证**：\n\n👮🏻验证是否本人进行敏感操作，请对我发送您设置的安全码。倒计时 120s\n'
                                      '🛑 **停止请点 /cancel**')
        if edt is False:
            return

        m = await callListen(call, 120)
        if m is False:
            return

        elif m.text == '/cancel':
            await m.delete()
            await editMessage(call, '__您已经取消输入__ **会话已结束！**', buttons=back_members_ikb)
        else:
            if m.text == e.pwd2:
                await m.delete()
                await editMessage(call, '**⚠️ 如果您的账户到期，我们将封存您的账户，但仍保留数据'
                                        '而如果您选择删除，这意味着服务器会将您此前的活动数据全部删除。\n**',
                                  buttons=del_me_ikb(e.embyid))
            else:
                await m.delete()
                await editMessage(call, '**💢 验证不通过，安全码错误。**', re_delme_ikb)


@bot.on_callback_query(filters.regex('delemby') & user_in_group_on_filter)
async def del_emby(_, call):
    send = await callAnswer(call, "🎯 get，正在删除ing。。。")
    if send is False:
        return

    embyid = call.data.split('-')[1]
    if await emby.emby_del(embyid):
        send1 = await editMessage(call, '🗑️ 好了，已经为您删除...\n愿来日各自安好，山高水长，我们有缘再见！',
                                  buttons=back_members_ikb)
        if send1 is False:
            return

        LOGGER.info(f"【删除账号】：{call.from_user.id} 已删除！")
    else:
        await editMessage(call, '🥧 蛋糕辣~ 好像哪里出问题了，请向管理反应', buttons=back_members_ikb)
        LOGGER.error(f"【删除账号】：{call.from_user.id} 失败！")


# 重置密码为空密码
@bot.on_callback_query(filters.regex('reset') & user_in_group_on_filter)
async def reset(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    if e is None:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start录入', True)
    if e.embyid is None:
        return await bot.answer_callback_query(call.id, '未查询到账户，不许乱点！💢', show_alert=True)
    else:
        await callAnswer(call, "🔴 请先进行 安全码 验证")
        send = await editMessage(call, '**🔰账户安全验证**：\n\n 👮🏻验证是否本人进行敏感操作，请对我发送您设置的安全码。倒计时 120 s\n'
                                       '🛑 **停止请点 /cancel**')
        if send is False:
            return

        m = await callListen(call, 120, buttons=back_members_ikb)
        if m is False:
            return

        elif m.text == '/cancel':
            await m.delete()
            await editMessage(call, '__您已经取消输入__ **会话已结束！**', buttons=back_members_ikb)
        else:
            if m.text != e.pwd2:
                await m.delete()
                await editMessage(call, f'**💢 验证不通过，{m.text} 安全码错误。**', buttons=re_reset_ikb)
            else:
                await m.delete()
                await editMessage(call, '🎯 请在 120s内 输入你要更新的密码,不限制中英文，emoji。特殊字符部分支持，其他概不负责。\n\n'
                                        '点击 /cancel 将重置为空密码并退出。 无更改退出状态请等待120s')
                mima = await callListen(call, 120, buttons=back_members_ikb)
                if mima is False:
                    return

                elif mima.text == '/cancel':
                    await mima.delete()
                    await editMessage(call, '**🎯 收到，正在重置ing。。。**')
                    if await emby.emby_reset(id=e.embyid) is True:
                        await editMessage(call, '🕶️ 操作完成！已为您重置密码为 空。', buttons=back_members_ikb)
                        LOGGER.info(f"【重置密码】：{call.from_user.id} 成功重置了空密码！")
                    else:
                        await editMessage(call, '🫥 重置密码操作失败！请联系管理员。')
                        LOGGER.error(f"【重置密码】：{call.from_user.id} 重置密码失败 ！")

                else:
                    await mima.delete()
                    await editMessage(call, '**🎯 收到，正在重置ing。。。**')
                    if await emby.emby_reset(id=e.embyid, new=mima.text) is True:
                        await editMessage(call, f'🕶️ 操作完成！已为您重置密码为 `{mima.text}`',
                                          buttons=back_members_ikb)
                        LOGGER.info(f"【重置密码】：{call.from_user.id} 成功重置了密码为 {mima.text} ！")
                    else:
                        await editMessage(call, '🫥 操作失败！请联系管理员。', buttons=back_members_ikb)
                        LOGGER.error(f"【重置密码】：{call.from_user.id} 重置密码失败 ！")


# 显示/隐藏某些库
@bot.on_callback_query(filters.regex('embyblock') & user_in_group_on_filter)
async def embyblocks(_, call):
    data = sql_get_emby(tg=call.from_user.id)
    if not data:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start录入', True)
    if data.embyid is None:
        return await callAnswer(call, '❓ 未查询到账户，不许乱点!', True)
    elif data.lv == "c":
        return await callAnswer(call, '💢 账户到期，封禁中无法使用！', True)
    elif len(config.emby_block) == 0:
        send = await editMessage(call, '⭕ 管理员未设置。。。 快催催\no(*////▽////*)q', buttons=back_members_ikb)
        if send is False:
            return
    else:
        success, rep = emby.user(embyid=data.embyid)
        try:
            if success is False:
                stat = '💨 未知'
            else:
                blocks = rep["Policy"]["BlockedMediaFolders"]
                if set(config.emby_block).issubset(set(blocks)):
                    stat = '🔴 隐藏'
                else:
                    stat = '🟢 显示'
        except KeyError:
            stat = '💨 未知'
        block = ", ".join(config.emby_block)
        await asyncio.gather(callAnswer(call, "✅ 到位"),
                             editMessage(call,
                                         f'🤺 用户状态：{stat}\n🎬 目前设定的库为: \n\n**{block}**\n\n请选择你的操作。',
                                         buttons=emby_block_ikb(data.embyid)))


# 隐藏
@bot.on_callback_query(filters.regex('emby_block') & user_in_group_on_filter)
async def user_emby_block(_, call):
    embyid = call.data.split('-')[1]
    send = await callAnswer(call, f'🎬 正在为您关闭显示ing')
    if send is False:
        return
    success, rep = emby.user(embyid=embyid)
    currentblock = []
    if success:
        try:
            currentblock = list(set(rep["Policy"]["BlockedMediaFolders"] + config.emby_block + ['播放列表']))
        except KeyError:
            currentblock = ['播放列表'] + extra_emby_libs + config.emby_block
        re = await emby.emby_block(embyid, 0, block=currentblock)
        if re is True:
            send1 = await editMessage(call, f'🕶️ ο(=•ω＜=)ρ⌒☆\n 小尾巴隐藏好了！ ', buttons=user_emby_block_ikb)
            if send1 is False:
                return
        else:
            await editMessage(call, f'🕶️ Error!\n 隐藏失败，请上报管理检查)', buttons=back_members_ikb)


# 显示
@bot.on_callback_query(filters.regex('emby_unblock') & user_in_group_on_filter)
async def user_emby_unblock(_, call):
    embyid = call.data.split('-')[1]
    send = await callAnswer(call, f'🎬 正在为您开启显示ing')
    if send is False:
        return
    success, rep = emby.user(embyid=embyid)
    currentblock = []
    if success:
        try:
            currentblock = list(set(rep["Policy"]["BlockedMediaFolders"] + ['播放列表']))
            # 保留不同的元素
            currentblock = [x for x in currentblock if x not in config.emby_block] + [x for x in config.emby_block if
                                                                                      x not in currentblock]
        except KeyError:
            currentblock = ['播放列表'] + extra_emby_libs
        re = await emby.emby_block(embyid, 0, block=currentblock)
        if re is True:
            # await embyblock(_, call)
            send1 = await editMessage(call, f'🕶️ ┭┮﹏┭┮\n 小尾巴被抓住辽！ ', buttons=user_emby_unblock_ikb)
            if send1 is False:
                return
        else:
            await editMessage(call, f'🎬 Error!\n 显示失败，请上报管理检查设置', buttons=back_members_ikb)


@bot.on_callback_query(filters.regex('exchange') & user_in_group_on_filter)
async def call_exchange(_, call):
    await asyncio.gather(callAnswer(call, '🔋 使用注册码'), deleteMessage(call))
    msg = await ask_return(call, text='🔋 **【使用注册码】**：\n\n'
                                      f'- 请在120s内对我发送你的注册码，形如\n`{ranks.logo}-xx-xxxx`\n\n退出点 /cancel',
                           button=re_exchange_b_ikb)
    if msg is False:
        return
    elif msg.text == '/cancel':
        await asyncio.gather(msg.delete(), p_start(_, msg))
    else:
        await rgs_code(_, msg, register_code=msg.text)


@bot.on_callback_query(filters.regex('storeall') & user_in_group_on_filter)
async def do_store(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    ch_day=e.ex - datetime.now()
    if ch_day.days > 90 or e.lv == 'a':
        await asyncio.gather(callAnswer(call, '✔️ 欢迎进入兑换商店'),
                         editMessage(call, f'**🏪 兑换商店**\n\n**自动续期** | 需米币数量>450，自动续费一个月\n**兑换时长** | 会员可见，可按天手动续期\n**兑换邀请码** | 剩余时长大于90天可见',
                                     buttons=store_vip_ikb()))
    elif e.lv == 'c':
        await asyncio.gather(callAnswer(call, '✔️ 欢迎进入兑换商店'),
                         editMessage(call, f'**🏪 兑换商店**\n\n**自动续期** | 需米币数量>450，自动续费一个月\n**兑换时长** | 会员可见，可按天手动续期\n**兑换邀请码** | 剩余时长大于90天可见',
                                     buttons=store_c_ikb()))
    else:
        await asyncio.gather(callAnswer(call, '✔️ 欢迎进入兑换商店'),
                         editMessage(call, f'**🏪 兑换商店**\n\n**自动续期** | 需米币数量>450，自动续费一个月\n**兑换时长** | 会员可见，可按天手动续期\n**兑换邀请码** | 剩余时长大于90天可见',
                                     buttons=store_ikb()))


def build_notify_menu_text(enabled: bool) -> str:
    status = '已开启' if enabled else '已关闭'
    return (
        f'**📺 追剧推送**\n\n'
        f'**当前状态**：{status}\n\n'
        f'说明：\n'
        f'- 开启后，新加入的收藏/取消收藏会收到私聊消息\n'
        f'- 已收藏的剧集更新时会收到推送提醒\n'
    )


def build_parental_menu_text(current_value: int) -> str:
    return (
        f'**🛡️ 家长控制**\n\n'
        f'根据内容分级限制电影和剧集的可见范围，'
        f'分级适用于未成年人家长管理，本服没有成人内容\n\n'
        f'**当前状态**：{parental_rating_label(current_value)}\n\n'
        f'说明：\n'
        f'- `0+ 全龄` 范围最小仅保留儿童、全年龄内容\n'
        f'- `7+ / 12+ / 16+ / 18+` 逐步放宽可见范围\n'
        f'- `18+ 全部` 默认此项显示库内所有内容'
    )


def build_line_menu_text(current_value: int) -> str:
    return (
        f'**🛣️  **\n\n'
        f'本功能只作为直连线路视频流的实时切换，不适用于海外线，'
        f'线路地址见用户手册\n\n'
        f'**当前线路**：{line_label(current_value)}\n\n'
        f'说明：\n'
        f'- 切换不会中断当前播放的视频\n'
        f'- 切换后会立即作用于下一次播放的视频\n'
        f'- 不通的地区、运营商、时间段两条线的体验均不一样，建议随时切换使用更适合的线路'
    )


@bot.on_callback_query(filters.regex('notify_menu') & user_in_group_on_filter)
async def notify_menu(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    if e is None:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start 录入', True)
    if not e.embyid:
        return await callAnswer(call, '❌ 需要先拥有 Emby 账号后才能设置追剧推送', True)

    enabled = bool(e.notify_enabled)
    await asyncio.gather(
        callAnswer(call, '📺 追剧推送'),
        editMessage(call, build_notify_menu_text(enabled), buttons=notify_menu_ikb(enabled))
    )


@bot.on_callback_query(filters.regex('notify_toggle') & user_in_group_on_filter)
async def notify_toggle(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    if e is None:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start 录入', True)
    if not e.embyid:
        return await callAnswer(call, '❌ 需要先拥有 Emby 账号后才能设置追剧推送', True)

    enabled = not bool(e.notify_enabled)
    if not sql_update_emby(Emby.tg == call.from_user.id, notify_enabled=int(enabled)):
        return await callAnswer(call, '❌ 状态更新失败，请稍后重试', True)

    await asyncio.gather(
        callAnswer(call, f'已{"开启" if enabled else "关闭"}追剧推送', True),
        editMessage(call, build_notify_menu_text(enabled), buttons=notify_menu_ikb(enabled))
    )
    LOGGER.info(f'【追剧推送】用户 {call.from_user.id} 已调整为 {"开启" if enabled else "关闭"}')


@bot.on_callback_query(filters.regex('parental_menu') & user_in_group_on_filter)
async def parental_menu(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    if e is None:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start 录入', True)
    if not e.embyid:
        return await callAnswer(call, '❌ 需要先拥有 Emby 账号后才能设置家长控制', True)

    ok, value = await emby.get_parental_rating(e.embyid)
    if not ok:
        return await callAnswer(call, f'❌ 获取当前家长控制状态失败：{value}', True)

    await asyncio.gather(
        callAnswer(call, '🛡️ 家长控制'),
        editMessage(call, build_parental_menu_text(value), buttons=parental_menu_ikb(value))
    )


@bot.on_callback_query(filters.regex(r'parental_set:\d+') & user_in_group_on_filter)
async def parental_set(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    if e is None:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start 录入', True)
    if not e.embyid:
        return await callAnswer(call, '❌ 需要先拥有 Emby 账号后才能设置家长控制', True)

    try:
        value = int(call.data.split(':', 1)[1])
    except (IndexError, ValueError):
        return await callAnswer(call, '❌ 档位参数错误', True)

    ok, result = await emby.set_parental_rating(e.embyid, value)
    if not ok:
        return await callAnswer(call, f'❌ 设置失败：{result}', True)

    await asyncio.gather(
        callAnswer(call, f'已切换到 {parental_rating_label(result)}', True),
        editMessage(call, build_parental_menu_text(result), buttons=parental_menu_ikb(result))
    )


@bot.on_callback_query(filters.regex('line_menu') & user_in_group_on_filter)
async def line_menu(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    if e is None:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start 录入', True)
    if not e.embyid:
        return await callAnswer(call, '❌ 需要先拥有 Emby 账号后才能设置线路', True)

    ok, value = await emby.get_use_line(e.embyid)
    if not ok:
        return await callAnswer(call, f'❌ 获取当前线路失败：{value}', True)

    await asyncio.gather(
        callAnswer(call, '🛣️ 线路选择'),
        editMessage(call, build_line_menu_text(value), buttons=line_menu_ikb(value))
    )


@bot.on_callback_query(filters.regex(r'line_set:\d+') & user_in_group_on_filter)
async def line_set(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    if e is None:
        return await callAnswer(call, '⚠️ 数据库没有你，请重新 /start 录入', True)
    if not e.embyid:
        return await callAnswer(call, '❌ 需要先拥有 Emby 账号后才能设置线路', True)

    try:
        value = int(call.data.split(':', 1)[1])
    except (IndexError, ValueError):
        return await callAnswer(call, '❌ 线路参数错误', True)

    ok, result = await emby.set_use_line(e.embyid, value)
    if not ok:
        return await callAnswer(call, f'❌ 设置失败：{result}', True)

    await asyncio.gather(
        callAnswer(call, f'已切换到 {line_label(result)}', True),
        editMessage(call, build_line_menu_text(result), buttons=line_menu_ikb(result))
    )


# 豆瓣点播
@bot.on_callback_query(filters.regex('dianbo') & user_in_group_on_filter)
async def dianbo(_, call):
    e = sql_get_emby(tg=call.from_user.id)    
    if e.douban:
        douban = e.douban
    else:
        douban = '未绑定'
    if e.lv and (e.lv == 'b' or e.lv == 'a'):
        await asyncio.gather(callAnswer(call, '🎬 豆瓣点播'),
                        editMessage(call, f'**🎬 绑定豆瓣 - 开启点播之旅~\n\n- 🫛 豆瓣のID | `{douban}`\n\n- 📅 我的想看 | [点击查看](https://movie.douban.com/people/{douban}/wish)**',
                                    buttons=dianbo_ikb()))
    else:
        return callAnswer(call, '❌ 仅持有账户可进行豆瓣点播', True)


@bot.on_callback_query(filters.regex('dianadd') & user_in_group_on_filter)
async def dianbo_add(_, call):
    e = sql_get_emby(tg=call.from_user.id)
    if e.douban:
        await callAnswer(call, '你已经绑定了豆瓣ID，不可以贪心哦，修改请先清除绑定', True)
        return
    await asyncio.gather(callAnswer(call, '🫛 绑定豆瓣ID'), deleteMessage(call))
    msg = await ask_return(call, text='🫛 **【绑定豆瓣ID】**：\n\n'
                                      f'- 请在120s内对我发送你的豆瓣ID，数字ID或者个性化ID，不可以是用户名，如果绑定无效的ID后续将无法同步\n\n退出点 /cancel',
                           button=re_douban_ikb)
    if msg is False:
        return
    elif msg.text == '/cancel':
        await asyncio.gather(msg.delete(), p_start(_, msg))
    else:
        sql_update_emby(Emby.tg == call.from_user.id, douban=msg.text)
        await sendMessage(call, f'🎊 恭喜你，豆瓣账号 `{msg.text}` 已绑定成功，去添加你喜欢的影视到想看吧~')


@bot.on_callback_query(filters.regex('diandel') & user_in_group_on_filter)
async def dianbo_del(_, call):
        e = sql_get_emby(tg=call.from_user.id)
        douban = e.douban
        if douban:
            sql_update_emby(Emby.tg == call.from_user.id, douban='')
            await callAnswer(call, '成功清除豆瓣绑定', True)
        else:
            await callAnswer(call, '当前未绑定豆瓣ID', True)


@bot.on_callback_query(filters.regex('store-renew') & user_in_group_on_filter)
async def do_store_renew(_, call):
    if _open.exchange:
        await callAnswer(call, '✔️ 进入兑换时长')
        e = sql_get_emby(tg=call.from_user.id)
        if e is None:
            return
        if e.iv < _open.exchange_cost:
            return await editMessage(call,
                                     f'**🏪 兑换规则：**\n当前兑换为 {_open.exchange_cost} {sakura_b} / 1 天，**持有积分不得低于{_open.exchange_cost}**，当前仅：{e.iv}，请好好努力。',
                                     buttons=back_members_ikb)

        await editMessage(call,
                          f'🏪 请输入您需要兑换的天数，当前兑换为 {_open.exchange_cost} {sakura_b} / 1 天，退出请 /cancel')
        m = await callListen(call, 120, buttons=re_store_renew)
        if m is False:
            return

        elif m.text == '/cancel':
            await asyncio.gather(m.delete(), do_store(_, call))
        else:
            try:
                await m.delete()
                days = int(m.text)
                iv = days * _open.exchange_cost
            except KeyError:
                await editMessage(call, f'❌ 请不要调戏bot，输入一个整数！！！', buttons=re_store_renew)
            else:
                new_us = e.iv - iv
                if new_us < 0:
                    sql_update_emby(Emby.tg == call.from_user.id, iv=e.iv - 2)
                    return await editMessage(call, f'🫡，不要太贪心哦！兑换时间超出你持有的{e.iv}{sakura_b}，罚2米币。')
                if days < 1:
                    sql_update_emby(Emby.tg == call.from_user.id, iv=e.iv - 2)
                    return await editMessage(call, f'🫡，没带这么小气的，哼！至少兑换1天，罚2米币。')
                new_ex = e.ex + timedelta(days)
                sql_update_emby(Emby.tg == call.from_user.id, ex=new_ex, iv=new_us)
                await asyncio.gather(emby.emby_change_policy(id=e.embyid),
                                     editMessage(call, f'🎉 您已花费 {iv}{sakura_b}\n🌏 到期时间 **{new_ex}**'))
                LOGGER.info(f'【兑换续期】- {call.from_user.id} 已花费 {iv}{sakura_b}，到期时间：{new_ex}')
    else:
        await callAnswer(call, '❌ 管理员未开启此兑换', True)


@bot.on_callback_query(filters.regex('store-whitelist') & user_in_group_on_filter)
async def do_store_whitelist(_, call):
    if _open.whitelist:
        e = sql_get_emby(tg=call.from_user.id)
        if e is None:
            return
        if e.iv < _open.whitelist_cost or e.lv == 'a':
            return await callAnswer(call,
                                    f'🏪 兑换规则：\n当前兑换白名单需要 {_open.whitelist_cost} {sakura_b}，已有白名单无法再次消费。勉励',
                                    True)
        await callAnswer(call, f'🏪 您已满足 {_open.whitelist_cost} {sakura_b}要求', True)
        sql_update_emby(Emby.tg == call.from_user.id, lv='a', iv=e.iv - _open.whitelist_cost)
        send = await call.message.edit(f'**{random.choice(Yulv.load_yulv().wh_msg)}**\n\n'
                                       f'🎉 恭喜[{call.from_user.first_name}](tg://user?id={call.from_user.id}) 今日晋升，{ranks["logo"]}白名单')
        await send.forward(group[0])
        LOGGER.info(f'【兑换白名单】- {call.from_user.id} 已花费 9999{sakura_b}，晋升白名单')
    else:
        await callAnswer(call, '❌ 管理员未开启此兑换', True)


@bot.on_callback_query(filters.regex('store-invite') & user_in_group_on_filter)
async def do_store_invite(_, call):
    if _open.invite:
        e = sql_get_emby(tg=call.from_user.id)
        if not e or not e.embyid:
            return callAnswer(call, '❌ 仅持有账户可兑换此选项', True)
        if e.iv < _open.invite_cost:
            return await callAnswer(call,
                                    f'🏪 兑换规则：\n当前兑换邀请码至少需要 {_open.invite_cost} {sakura_b}。勉励',
                                    True)
        days = 30
        count = 1
        method = 'code'
        sql_update_emby(Emby.tg == call.from_user.id, iv=e.iv - _open.invite_cost)
        links = await cr_link_invite(call.from_user.id, days, count, days, method)
        if links is None:
            return await editMessage(call, '⚠️ 数据库插入失败，请检查数据库')
        links = f"🎯 {bot_name}已为您生成了 **{days}天** 邀请码\n\n" + links
        chunks = [links[i:i + 4096] for i in range(0, len(links), 4096)]
        for chunk in chunks:
            await sendMessage(call, chunk)
        LOGGER.info(f"【注册码兑换】：{bot_name}已为 {content.from_user.id} 生成了 {count} 个 {days} 天邀请码")

    else:
        await callAnswer(call, '❌ 管理员未开启此兑换', True)


@bot.on_callback_query(filters.regex('store-query') & user_in_group_on_filter)
async def do_store_query(_, call):
    a, b = sql_count_c_code(tg_id=call.from_user.id)
    if not a:
        return await callAnswer(call, '❌ 空', True)
    try:
        number = int(call.data.split(':')[1])
    except (IndexError, KeyError, ValueError):
        number = 1
    await callAnswer(call, '📜 正在翻页')
    await editMessage(call, text=a[number - 1], buttons=await user_query_page(b, number))
