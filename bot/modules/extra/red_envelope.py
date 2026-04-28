"""
red_envelope - 

Author:susu
Date:2023/01/02
"""
import cn2an
import asyncio
import random
import math
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from bot import bot, prefixes, sakura_b, bot_photo, LOGGER
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.fix_bottons import users_iv_button
from bot.func_helper.msg_utils import sendPhoto, sendMessage, callAnswer, editMessage
from bot.func_helper.utils import pwd_create, judge_admins, cache
from bot.sql_helper import Session
from bot.sql_helper.sql_emby import Emby, sql_get_emby, sql_update_emby
from bot.ranks_helper.ranks_draw import RanksDraw
from bot.schemas import Yulv

# 小项目，说实话不想写数据库里面。放内存里了，从字典里面每次拿分

red_bags = {}


async def create_reds(money, members, first_name, flag=None, private=None):
    red_id = await pwd_create(5)
    if flag:
        red_bags.update(
            {red_id: dict(money=money, members=members, flag=1, sender=first_name, num=money // members, rest=members,
                          m=money, used={})})
    elif private:
        red_bags.update(
            {red_id: dict(money=money, members=private, flag=2, sender=first_name, m=money, rest=True)})
    else:
        red_bags.update(
            {red_id: dict(money=money, members=members, flag={}, sender=first_name, rest=members, m=money, n=0)})
    return InlineKeyboardMarkup([[InlineKeyboardButton(text='👆🏻 好運連連', callback_data=f'red_bag-{red_id}')]])


@bot.on_message(filters.command('red', prefixes) & user_in_group_on_filter & filters.group)
async def send_red_envelop(_, msg):
    # if msg.reply_to_message:
    #     try:
    #         money = int(msg.command[1])
    #     except (IndexError, KeyError, ValueError):
    #         return await asyncio.gather(msg.delete(),
    #                                     sendMessage(msg, f'**🧧 专享红包：\n\n使用请回复一位群友 + {sakura_b}', timer=60))
    #     if not msg.sender_chat:
    #         e = sql_get_emby(tg=msg.from_user.id)
    #         if not e or e.iv < 5 or money < 5 or msg.reply_to_message.from_user.id == msg.from_user.id:
    #             await asyncio.gather(msg.delete(),
    #                                  msg.chat.restrict_member(msg.from_user.id, ChatPermissions(),
    #                                                           datetime.now() + timedelta(minutes=1)),
    #                                  sendMessage(msg, f'[{msg.from_user.first_name}](tg://user?id={msg.from_user.id}) '
    #                                                   f'违反规则，禁言一分钟。\nⅰ 所持有{sakura_b}不小于5\nⅱ 发出{sakura_b}不小于5\nⅲ 不许发自己',
    #                                              timer=60))
    #             return
    #         else:
    #             new_iv = e.iv - money
    #             sql_update_emby(Emby.tg == msg.from_user.id, iv=new_iv)
    #             if not msg.reply_to_message.from_user.photo:
    #                 user_pic = None
    #             else:
    #                 user_pic = await bot.download_media(msg.reply_to_message.from_user.photo.big_file_id,
    #                                                     in_memory=True)
    #             first_name = msg.from_user.first_name

    #     elif msg.sender_chat.id == msg.chat.id:
    #         if not msg.reply_to_message.from_user.photo:
    #             user_pic = None
    #         else:
    #             user_pic = await bot.download_media(message=msg.reply_to_message.from_user.photo.big_file_id,
    #                                                 in_memory=True)
    #         first_name = msg.chat.title
    #     else:
    #         return
    #     reply, delete = await asyncio.gather(msg.reply('正在准备专享红包，稍等'), msg.delete())
    #     ikb = create_reds(money=money, first_name=first_name, members=1, private=msg.reply_to_message.from_user.id)
    #     cover = RanksDraw.hb_test_draw(money, 1, user_pic, f'{msg.reply_to_message.from_user.first_name} 专享')
    #     ikb, cover = await asyncio.gather(ikb, cover)
    #     await asyncio.gather(sendPhoto(msg, photo=cover, buttons=ikb), reply.delete(),
    #                          sendMessage(msg, f'🔥 [{msg.reply_to_message.from_user.first_name}]'
    #                                           f'(tg://user?id={msg.reply_to_message.from_user.id})\n'
    #                                           f' 您收到一个来自 [{first_name}](tg://user?id={msg.from_user.id}) 的专属红包'))

      if not msg.reply_to_message:
        try:
            money = int(msg.command[1])
            members = int(msg.command[2])
            if members == 1:
                members = 2
        except (IndexError, KeyError, ValueError):
            return await asyncio.gather(msg.delete(),
                                        sendMessage(msg,
                                                    f'**🧧 发红包：**\n\n'
                                                    f'`/red` [总{sakura_b}数] [份数(至少2)] [mode]\n'
                                                    f'[mode] 留空 - 拼手气 | 任意值 - 均分',
                                                    timer=20))
        if not msg.sender_chat:
            e = sql_get_emby(tg=msg.from_user.id)
            if not all([e, e.iv >= money, money >= members, members > 0]):
                await asyncio.gather(msg.delete(),
                                     msg.chat.restrict_member(msg.from_user.id, ChatPermissions(),
                                                              datetime.now() + timedelta(minutes=1)),
                                     sendMessage(msg, f'[{msg.from_user.first_name}](tg://user?id={msg.from_user.id}) '
                                                      f'未私聊过bot或{sakura_b}不足，禁言一分钟。', timer=20))
                return
            else:
                new_iv = e.iv - money
                sql_update_emby(Emby.tg == msg.from_user.id, iv=new_iv)
                if not msg.from_user.photo:
                    user_pic = None
                else:
                    user_pic = await bot.download_media(msg.from_user.photo.big_file_id, in_memory=True)
                first_name = msg.from_user.first_name

        elif msg.sender_chat.id == msg.chat.id:
            if not msg.chat.photo:
                user_pic = None
            else:
                user_pic = await bot.download_media(message=msg.chat.photo.big_file_id, in_memory=True)
            first_name = msg.chat.title
        else:
            return

        try:
            flag = msg.command[3]
        except:
            flag = None
        reply, delete = await asyncio.gather(msg.reply('正在准备红包，稍等'), msg.delete())
        ikb = create_reds(money=money, members=members, flag=flag, first_name=first_name)
        cover = RanksDraw.hb_test_draw(money, members, user_pic, first_name)
        ikb, cover = await asyncio.gather(ikb, cover)
        await asyncio.gather(sendPhoto(msg, photo=cover, buttons=ikb), reply.delete())


@bot.on_callback_query(filters.regex("red_bag") & user_in_group_on_filter)
async def pick_red_bag(_, call):
    red_id = call.data.split('-')[1]
    try:
        bag = red_bags[red_id]
    except (IndexError, KeyError):
        return await callAnswer(call, '/(ㄒoㄒ)/~~ \n\n来晚了，红包已经被抢光啦。', True)

    e = sql_get_emby(tg=call.from_user.id)
    if not e:
        return await callAnswer(call, '你还未私聊bot! 数据库没有你.', True)

    # 均分模式 只需要计算 rest 剩余数，每次取出的 num 就行了
    if bag["flag"] == 1:
        if call.from_user.id in bag["used"]: return await callAnswer(call, 'ʕ•̫͡•ʔ 你已经领取过红包了。不许贪吃',
                                                                     True)
        if bag["rest"] >= 1:
            new = e.iv + bag["num"]
        else:
            return await callAnswer(call, '/(ㄒoㄒ)/~~ \n\n来晚了，红包已经被抢光啦。', True)

        sql_update_emby(Emby.tg == call.from_user.id, iv=new)
        bag["used"][call.from_user.id] = bag["num"]
        bag["rest"] = bag["rest"] - 1
        if bag["rest"] == 0:
            red_bags.pop(red_id, '不存在的红包')
            text = f'🧧 {sakura_b}红包\n\n**{random.choice(Yulv.load_yulv().red_bag)}\n\n' \
                   f'🕶️{bag["sender"]} **的红包已经被抢光啦~\n\n'
            top_five_scores = sorted(bag["flag"].items(), key=lambda x: x[1], reverse=True)[:5]
            members = await get_users()
            for i, score in enumerate(top_five_scores):
                text += f'**🎖️ [{members.get(score[0], "None")}](tg://user?id={score[0]}) 获得了 {score[1]} {sakura_b}**'
            await editMessage(call, text)

        await callAnswer(call, f'🧧 {random.choice(Yulv.load_yulv().red_bag)}\n\n'
                               f'恭喜，你领取到了 {bag["sender"]} の {bag["num"]}{sakura_b}', True)

    elif bag["flag"] == 2:
        if bag["rest"] and call.from_user.id == bag["members"]:
            bag["rest"] = False
            red_bags.pop(red_id, '不存在的红包')
            new_iv = e.iv + bag["money"]
            sql_update_emby(Emby.tg == call.from_user.id, iv=new_iv)
            await callAnswer(call, f'🧧 {random.choice(Yulv.load_yulv().red_bag)}\n\n'
                                   f'恭喜，你领取到了 {bag["sender"]} の {bag["m"]}{sakura_b}', True)
            members = await get_users()
            text = f'🧧 {sakura_b}红包\n\n**{random.choice(Yulv.load_yulv().red_bag)}\n\n' \
                   f'🕶️{bag["sender"]} **的专属红包已被 [{members.get(call.from_user.id, "None")}](tg://user?id={bag["members"]}) 领取'
            await editMessage(call, text)
            return
        else:
            return await callAnswer(call, 'ʕ•̫͡•ʔ 这是你的专属红包吗？', True)
    else:
        if call.from_user.id in bag["flag"]: return await callAnswer(call, 'ʕ•̫͡•ʔ 你已经领取过红包了。不许贪吃', True)

        if bag["rest"] > 1:
            k = bag["m"] - 1 * (bag["members"] - bag["n"] - 1)
            t = math.ceil(random.uniform(1, k / 2))  # 对每个红包的上限进行动态限制

        elif bag["rest"] == 1:
            t = bag["m"]
        else:
            return await callAnswer(call, '/(ㄒoㄒ)/~~ \n\n来晚了，红包已经被抢光啦。', True)

        bag["flag"][call.from_user.id] = t
        bag.update({"m": bag["m"] - t, "rest": bag["rest"] - 1, "n": bag["n"] + 1})
        # print(bag)

        await callAnswer(call, f'🧧 {random.choice(Yulv.load_yulv().red_bag)}\n\n'
                               f'恭喜，你领取到了 {bag["sender"]} の {t}{sakura_b}', True)
        new = e.iv + t
        sql_update_emby(Emby.tg == call.from_user.id, iv=new)

        if bag["rest"] == 0:
            red_bags.pop(red_id, '不存在的红包')
            # 找出运气王
            # 对用户按照积分从高到低进行排序，并取出前六名
            top_five_scores = sorted(bag["flag"].items(), key=lambda x: x[1], reverse=True)[:6]
            text = f'🧧 {sakura_b}红包\n\n**{random.choice(Yulv.load_yulv().red_bag)}\n\n' \
                   f'🕶️{bag["sender"]} **的红包已经被抢光啦~ \n\n'
            members = await get_users()
            for i, score in enumerate(top_five_scores):
                if i == 0:
                    text += f'**🏆 手气最佳 [{members.get(score[0], "None")}](tg://user?id={score[0]}) **获得了 {score[1]} {sakura_b}'
                else:
                    text += f'\n**🏅 [{members.get(score[0], "None")}](tg://user?id={score[0]})** 获得了 {score[1]} {sakura_b}'
            await editMessage(call, text)


@bot.on_message(filters.command("srank", prefixes) & user_in_group_on_filter & filters.group)
async def s_rank(_, msg):
    await msg.delete()
    if not msg.sender_chat:
        e = sql_get_emby(tg=msg.from_user.id)
        if not e or e.iv < 2:
            await asyncio.gather(msg.delete(),
                                 msg.chat.restrict_member(msg.from_user.id, ChatPermissions(),
                                                          datetime.now() + timedelta(minutes=1)),
                                 sendMessage(msg, f'[{msg.from_user.first_name}]({msg.from_user.id}) '
                                                  f'未私聊过bot或不足支付手续费2{sakura_b}，禁言一分钟。', timer=60))
            return
        else:
            sql_update_emby(Emby.tg == msg.from_user.id, iv=e.iv - 2)
            sender = msg.from_user.id
    elif msg.sender_chat.id == msg.chat.id:
        sender = msg.chat.id
    else:
        return
    reply = await msg.reply(f"已扣除手续2{sakura_b}, 请稍等......加载中")
    text, i = await users_iv_rank()
    t = '❌ 数据库操作失败' if not text else text[0]
    button = await users_iv_button(i, 1, sender)
    await asyncio.gather(reply.delete(),
                         sendPhoto(msg, photo=bot_photo, caption=f'**▎🏆 {sakura_b}风云录**\n\n{t}', buttons=button,
                                   timer=300))


async def resolve_rank_user_names(user_ids):
    unique_ids = []
    seen = set()
    for user_id in user_ids:
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        unique_ids.append(user_id)

    if not unique_ids:
        return {}

    try:
        users = await bot.get_users(unique_ids)
        if not isinstance(users, list):
            users = [users]
        return {user.id: user.first_name for user in users if getattr(user, "id", None)}
    except Exception as e:
        LOGGER.warning(f'【srank】批量获取 Telegram 用户名失败: {e}')
        return {}


@cache.memoize(ttl=120)
async def users_iv_rank():
    with Session() as session:
        top_rows = session.query(Emby.tg, Emby.iv).filter(Emby.iv > 0).order_by(Emby.iv.desc()).limit(100).all()
        if not top_rows:
            return None, 1

        members_dict = await resolve_rank_user_names([row.tg for row in top_rows])
        total_pages = min(math.ceil(len(top_rows) / 10), 10)

        results_list = []
        medals = ["🥇", "🥈", "🥉", "🏅"]

        for page in range(1, total_pages + 1):
            offset = (page - 1) * 10
            result = top_rows[offset:offset + 10]
            rank_index = offset + 1
            text = ''
            for q in result:
                name = str(members_dict.get(q.tg, q.tg))[:12]
                medal = medals[rank_index - 1] if rank_index < 4 else medals[3]
                text += f'{medal}**第{cn2an.an2cn(rank_index)}名** | [{name}](google.com?q={q.tg}) の **{q.iv} {sakura_b}**\n'
                rank_index += 1

            results_list.append(text)

        return results_list, total_pages
    

# 检索翻页
@bot.on_callback_query(filters.regex('users_iv') & user_in_group_on_filter)
async def users_iv_pikb(_, call):
    # print(call.data)
    j, tg = map(int, call.data.split(":")[1].split('_'))
    if call.from_user.id != tg:
        if not judge_admins(call.from_user.id):
            return await callAnswer(call, '❌ 这不是你召唤出的榜单，请使用自己的 /srank', True)

    await callAnswer(call, f'将为您翻到第 {j} 页')
    a, b = await users_iv_rank()
    button = await users_iv_button(b, j, tg)
    text = a[j - 1]
    await editMessage(call, f'**▎🏆 {sakura_b}风云录**\n\n{text}', buttons=button)
