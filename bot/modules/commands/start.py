"""
启动面板start命令 返回面ban

+ myinfo 个人数据
+ count  服务器媒体数
"""
import asyncio
from pyrogram import filters

from bot.func_helper.emby import Embyservice
from bot.modules.commands.exchange import rgs_code
from bot.sql_helper.sql_emby import sql_add_emby
from bot.func_helper.filters import user_in_group_filter, user_in_group_on_filter
from bot.func_helper.msg_utils import deleteMessage, sendMessage, sendPhoto, callAnswer, editMessage
from bot.func_helper.fix_bottons import group_f, judge_start_ikb, judge_group_ikb, cr_kk_ikb
from bot import bot, prefixes, group, bot_photo, ranks, _open


# 非隐身模式下，未入群用户除 /start 外不能使用任何私聊功能
@bot.on_message(filters.private & ~filters.command('start', prefixes), group=-1)
async def reject_unauthorized_private(_, msg):
    if not _open.site or await user_in_group_filter(_, msg):
        return

    await sendMessage(msg, '当前未加入MICU社区群，无法使用机器人功能，请先点击 /start 加入社区~')
    msg.stop_propagation()


# 反命令提示
@bot.on_message((filters.command('start', prefixes) | filters.command('count', prefixes) | filters.command('myinfo', prefixes)) & filters.chat(group))
async def ui_g_command(_, msg):
    await asyncio.gather(deleteMessage(msg),
                         sendMessage(msg,
                                     f"🤖 亲爱的 [{msg.from_user.first_name}](tg://user?id={msg.from_user.id}) 这是一条私聊命令",
                                     buttons=group_f, timer=60))


# 查看自己的信息
@bot.on_message(filters.command('myinfo', prefixes) & filters.private)
async def my_info(_, msg):
    await msg.delete()
    if msg.sender_chat:
        return
    text, keyboard = await cr_kk_ikb(uid=msg.from_user.id, first=msg.from_user.first_name)
    await sendMessage(msg, text)


@bot.on_message(filters.command('count', prefixes) & user_in_group_on_filter & filters.private)
async def count_info(_, msg):
    await deleteMessage(msg)
    text = Embyservice.get_medias_count()
    await sendMessage(msg, text, timer=60)


# 私聊开启面板
@bot.on_message(filters.command('start', prefixes) & filters.private)
async def p_start(_, msg):
    # 首次私聊 /start 即建立 TG 占位记录；主键重复时 sql_add_emby 会忽略。
    sql_add_emby(msg.from_user.id)

    if not await user_in_group_filter(_, msg):
        if not _open.site:
            return await asyncio.gather(deleteMessage(msg),
                                        sendMessage(msg,
                                                    '🌻 **只在此山中，云深不知处**\n\n站点已开启隐身模式，暂不接收新人入群\n期待我们在未来相遇~',
                                                    timer=30))
        else:   
            return await asyncio.gather(deleteMessage(msg),
                                        sendMessage(msg,
                                                    '🌸 **桃花流水窅然去，别有天地非人间**\n\n恭喜你发现了MICU Cloud Media，欢迎加入我们的群组\n加群后可以点击 /start 使用更多机器人功能哦~',
                                                    buttons=judge_group_ikb,
                                                    timer=180))
    try:
        u = msg.command[1].split('-')[0]
        if u in f'{ranks.logo}' or u == str(msg.from_user.id):
            await asyncio.gather(msg.delete(), rgs_code(_, msg, register_code=msg.command[1]))
        else:
            await asyncio.gather(sendMessage(msg, '🤺 你也想和bot击剑吗 ?'), msg.delete())
    except (IndexError, TypeError):
        if await user_in_group_filter(_, msg):
            await asyncio.gather(deleteMessage(msg),
                                 sendPhoto(msg, bot_photo,
                                           f"**✨ 只有你想见我的时候我们的相遇才有意义**\n\n🍉__你好鸭 [{msg.from_user.first_name}](tg://user?id={msg.from_user.id}) 请选择功能__👇",
                                           buttons=judge_start_ikb(msg.from_user.id)))


# 返回面板
@bot.on_callback_query(filters.regex('back_start'))
async def b_start(_, call):
    if await user_in_group_filter(_, call):
        await asyncio.gather(callAnswer(call, "⭐ 返回start"),
                             editMessage(call,
                                         text=f"**✨ 只有你想见我的时候我们的相遇才有意义**\n\n🍉__你好鸭 [{call.from_user.first_name}](tg://user?id={call.from_user.id}) 请选择功能__👇",
                                         buttons=judge_start_ikb(
                                             call.from_user.id)))
    elif not await user_in_group_filter(_, call):
        await asyncio.gather(callAnswer(call, "⭐ 返回start"),
                             editMessage(call, text='💢 必须加入我们的群组，然后再 /start 滴~',
                                         buttons=judge_group_ikb))


@bot.on_callback_query(filters.regex('store_all'))
async def store_alls(_, call):
    if not await user_in_group_filter(_, call):
        await asyncio.gather(callAnswer(call, "⭐ 返回start"),
                             deleteMessage(call), sendPhoto(call, bot_photo,
                                                            '💢 拜托啦！请先点击下面加入我们的群组，然后再 /start 一下好吗？',
                                                            judge_group_ikb))
    elif await user_in_group_filter(_, call):
        await callAnswer(call, '⭕ 正在编辑', True)
