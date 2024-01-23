"""
定时推送日榜和周榜
"""
from pyrogram import enums
from datetime import date

from bot.func_helper.emby import emby
from bot.ranks_helper import ranks_draw
from bot import bot, group, ranks, LOGGER, schedall, save_config


async def day_ranks(pin_mode=True):
    draw = ranks_draw.RanksDraw(ranks.logo, backdrop=ranks.backdrop)
    LOGGER.info("【ranks_task】定时任务 正在推送日榜")
    success, movies = await emby.get_emby_report(types='Movie', days=1)
    if not success:
        LOGGER.error('【ranks_task】推送日榜失败，获取Movies数据失败!')
        return
    success, tvs = await emby.get_emby_report(types='Episode', days=1)
    if not success:
        LOGGER.error('【ranks_task】推送日榜失败，获取Episode数据失败!')
        return
    # 绘制海报
    await draw.draw(movies, tvs)
    path = draw.save()

    try:
        if pin_mode:
            await bot.unpin_chat_message(chat_id=group[0], message_id=schedall.day_ranks_message_id)
    except Exception as e:
        LOGGER.warning(f'【ranks_task】unpin day_ranks_message exception {e}')
        pass
    payload = ""
    if movies:
        tmp = "**▎电影:**\n\n"
        for i, movie in enumerate(movies[:10]):
            user_id, item_id, item_type, name, count, duarion = tuple(movie)
            tmp += str(i + 1) + "." + name + " - " + str(count) + "\n"
        payload = tmp
    if tvs:
        tmp = "\n**▎电视剧:**\n\n"
        for i, tv in enumerate(tvs[:10]):
            user_id, item_id, item_type, name, count, duarion = tuple(tv)
            tmp += str(i + 1) + "." + name + " - " + str(count) + "\n"
        payload += tmp
    payload = f"**【MICU Cloud Media 播放日榜】**\n\n**▎📢公告:**\n\n{ranks.announce}\n\n" + payload + "\n#DayRanks" + "  " + date.today().strftime('%Y-%m-%d')
    message_info = await bot.send_photo(chat_id=group[0], photo=open(path, "rb"), caption=payload,
                                        parse_mode=enums.ParseMode.MARKDOWN)
    if pin_mode:
        await bot.pin_chat_message(chat_id=message_info.chat.id, message_id=message_info.id, disable_notification=True)
    schedall.day_ranks_message_id = message_info.id
    save_config()
    LOGGER.info("【ranks_task】定时任务 推送日榜完成")


async def week_ranks(pin_mode=True):
    draw = ranks_draw.RanksDraw(ranks.logo, weekly=True, backdrop=ranks.backdrop)
    LOGGER.info("【ranks_task】定时任务 正在推送周榜")
    success, movies = await emby.get_emby_report(types='Movie', days=7)
    if not success:
        LOGGER.warning('【ranks_task】推送周榜失败，没有获取到Movies数据!')
        return
    success, tvs = await emby.get_emby_report(types='Episode', days=7)
    if not success:
        LOGGER.error('【ranks_task】推送周榜失败，没有获取到Episode数据!')
        return
    # 绘制海报
    await draw.draw(movies, tvs)
    path = draw.save()

    try:
        if pin_mode:
            await bot.unpin_chat_message(chat_id=group[0], message_id=schedall.week_ranks_message_id)
    except Exception as e:
        LOGGER.warning(f'【ranks_task】unpin day_ranks_message exception {e}')
        pass
    payload = ""
    if movies:
        tmp = "**▎电影:**\n\n"
        for i, movie in enumerate(movies[:10]):
            user_id, item_id, item_type, name, count, duarion = tuple(movie)
            tmp += str(i + 1) + "." + name + " - " + str(count) + "\n"
        payload = tmp
    if tvs:
        tmp = "\n**▎电视剧:**\n\n"
        for i, tv in enumerate(tvs[:10]):
            user_id, item_id, item_type, name, count, duarion = tuple(tv)
            tmp += str(i + 1) + "." + name + " - " + str(count) + "\n"
        payload += tmp
    payload = f"**【{ranks.logo} 播放周榜】**\n\n" + payload + "\n#WeekRanks" + "  " + date.today().strftime(
        '%Y-%m-%d')
    message_info = await bot.send_photo(chat_id=group[0], photo=open(path, "rb"), caption=payload,
                                        parse_mode=enums.ParseMode.MARKDOWN)
    if pin_mode:
        await bot.pin_chat_message(chat_id=message_info.chat.id, message_id=message_info.id, disable_notification=True)
    schedall.week_ranks_message_id = message_info.id
    save_config()
    LOGGER.info("【ranks_task】定时任务 推送周榜完成")
