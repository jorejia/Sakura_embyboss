import asyncio
import random
from datetime import datetime, timezone, timedelta

from cacheout import Cache
from pyrogram import filters

from bot import bot, _open, sakura_b
from bot.func_helper.filters import user_in_group_on_filter
from bot.func_helper.fix_bottons import checkin_menu_ikb, back_start_ikb
from bot.func_helper.msg_utils import callAnswer, editMessage
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby

checkin_cache = Cache(ttl=300)


def _is_checked_in_today(user, now):
    return bool(user.ch and user.ch.strftime("%Y-%m-%d") >= now.strftime("%Y-%m-%d"))


def _build_checkin_text(question=None, notice=None):
    text = "**🎯 每日签到**"
    if notice:
        text += f"\n\n{notice}"
    if question:
        text += f"\n\n请完成下面这道题后签到：\n`{question} = ?`\n\n答错会重新生成一题。"
    return text


def _create_checkin_question():
    operator = random.choice(["+", "-"])
    left = random.randint(2, 20)
    right = random.randint(1, 20)
    if operator == "-" and right > left:
        left, right = right, left
    answer = left + right if operator == "+" else left - right

    options = {answer}
    while len(options) < 4:
        offset = random.choice([-9, -8, -7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        candidate = answer + offset
        if candidate >= 0:
            options.add(candidate)
    option_list = list(options)
    random.shuffle(option_list)
    return f"{left} {operator} {right}", answer, option_list


async def _show_checkin_menu(call, notice=None):
    question, answer, options = _create_checkin_question()
    checkin_cache.set(call.from_user.id, answer)
    await editMessage(call, _build_checkin_text(question, notice), buttons=checkin_menu_ikb(options))


async def _show_already_checked_in(call):
    await editMessage(call,
                      _build_checkin_text(notice='⭕ 您今天已经签到过了，明天再来吧。'),
                      buttons=back_start_ikb)


async def _reward_checkin(call, user, now):
    member_active = bool(user.ex and user.ex.strftime("%Y-%m-%d") > now.strftime("%Y-%m-%d"))
    reward = random.randint(1, 5) * (2 if member_active else 1)
    balance = user.iv + reward
    sql_update_emby(Emby.tg == call.from_user.id, iv=balance, ch=now)
    suffix = ' （会员双倍）' if member_active else ''
    text = f'🎉 **签到成功** | + {reward} {sakura_b}{suffix}\n' \
           f'💴 **当前余额** | {balance} {sakura_b}\n' \
           f'⏳ **签到日期** | {now.strftime("%Y-%m-%d")}'
    checkin_cache.delete(call.from_user.id)
    try:
        await call.message.delete()
    except Exception:
        pass
    await bot.send_message(
        chat_id=call.message.chat.id,
        text=text,
        disable_web_page_preview=True
    )


def _get_checkin_user(call):
    if not _open.checkin:
        return None, '❌ 未开启签到系统，等待！'
    user = sql_get_emby(call.from_user.id)
    if not user:
        return None, '🧮 未查询到数据库'
    return user, None


@bot.on_callback_query(filters.regex(r'^checkin$') & user_in_group_on_filter)
async def user_in_checkin(_, call):
    user, error = _get_checkin_user(call)
    if error:
        return await callAnswer(call, error, True)

    now = datetime.now(timezone(timedelta(hours=8)))
    if _is_checked_in_today(user, now):
        await _show_already_checked_in(call)
        return

    await callAnswer(call, '🧮 请先完成计算验证')
    await _show_checkin_menu(call)


@bot.on_callback_query(filters.regex(r'^checkin_answer:') & user_in_group_on_filter)
async def answer_checkin_question(_, call):
    user, error = _get_checkin_user(call)
    if error:
        return await callAnswer(call, error, True)

    now = datetime.now(timezone(timedelta(hours=8)))
    if _is_checked_in_today(user, now):
        await _show_already_checked_in(call)
        return

    cached_answer = checkin_cache.get(call.from_user.id)
    if cached_answer is None:
        await callAnswer(call, '⌛ 题目已过期，已为您重新生成', True)
        await _show_checkin_menu(call)
        return

    try:
        selected_answer = int(call.data.split(':', 1)[1])
    except (IndexError, ValueError):
        await callAnswer(call, '⚠️ 题目参数异常，已为您重新生成', True)
        await _show_checkin_menu(call)
        return

    if selected_answer != cached_answer:
        await callAnswer(call, '❌ 签到失败，已重新生成一题', True)
        await _show_checkin_menu(call, notice='❌ 本题答错了，再试一次吧。')
        return

    await callAnswer(call, '🎉 恭喜你签到成功', True)
    await _reward_checkin(call, user, now)
