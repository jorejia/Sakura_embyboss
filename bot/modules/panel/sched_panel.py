import asyncio
import os

from pyrogram import filters
from bot import bot, schedall, save_config, prefixes, owner, LOGGER
from bot.func_helper.filters import admins_on_filter
from bot.func_helper.fix_bottons import sched_buttons
from bot.func_helper.msg_utils import callAnswer, editMessage, deleteMessage
from bot.func_helper.scheduler import Scheduler
from bot.scheduler import *

# 实例化
scheduler = Scheduler()

# 初始化命令 开机检查重启
loop = asyncio.get_event_loop()
# loop.call_later(5, lambda: loop.create_task(BotCommands.set_commands(client=bot)))
loop.call_later(5, lambda: loop.create_task(check_restart()))

# 启动定时任务
auto_backup_db = DbBackupUtils.auto_backup_db

# 写优雅点
# 字典，method相应的操作函数
action_dict = {
    "dayrank": day_ranks,
    "weekrank": week_ranks,
    "backup_db": auto_backup_db
}

# 字典，对应的操作函数的参数和id
args_dict = {
    "dayrank": {'hour': 18, 'minute': 30, 'id': 'day_ranks'},
    "weekrank": {'day_of_week': "sun", 'hour': 23, 'minute': 50, 'id': 'week_ranks'},
    "backup_db": {'hour': 2, 'minute': 30, 'id': 'backup_db'}
}


def set_all_sche():
    # 到期检测始终注册；暂停状态由 check_expired 内部统一判断，
    # 从而让自动任务与手动 /check_ex 具有完全一致的行为。
    scheduler.add_job(check_expired, 'cron', hour=0, minute=0, id='check_expired')
    for key, value in action_dict.items():
        if getattr(schedall, key):
            action = action_dict[key]
            args = args_dict[key]
            scheduler.add_job(action, 'cron', **args)


set_all_sche()


async def sched_panel(_, msg):
    await editMessage(msg,
                      text='🎮 **管理定时任务面板**',
                      buttons=sched_buttons())


@bot.on_callback_query(filters.regex(r'^expiry_pause_toggle$') & admins_on_filter)
async def toggle_expiry_pause(_, call):
    schedall.check_ex_paused = not schedall.check_ex_paused
    save_config()
    status = '已暂停' if schedall.check_ex_paused else '已恢复'
    LOGGER.info(f'【admin】到期检测{status}，操作管理员：{call.from_user.id}')
    await asyncio.gather(
        callAnswer(call, f'✅ 到期检测{status}', True),
        sched_panel(_, call.message),
    )





@bot.on_callback_query(filters.regex('sched') & admins_on_filter)
async def sched_change_policy(_, call):
    try:
        method = call.data.split('-')[1]
        # 根据method的值来添加或移除相应的任务
        action = action_dict[method]
        args = args_dict[method]
        if getattr(schedall, method):
            scheduler.remove_job(job_id=args['id'], jobstore='default')
        else:
            scheduler.add_job(action, 'cron', **args)
        setattr(schedall, method, not getattr(schedall, method))
        save_config()
        await asyncio.gather(callAnswer(call, f'⭕️ {method} 更改成功'), sched_panel(_, call.message))
    except IndexError:
        await sched_panel(_, call.message)


# ───────── 维护任务（由管理菜单「🧰 维护」调用，不再提供命令） ─────────

async def run_check_ex() -> str:
    result = await check_expired()
    if result == 'paused':
        return "⏸️ 【到期检测已暂停】本次未执行"
    return "✅ 【到期检测结束】"


async def run_backup_db():
    await auto_backup_db()


async def run_day_ranks():
    await day_ranks(pin_mode=False)


async def run_week_ranks():
    await week_ranks(pin_mode=False)


def restart_bot(chat_id: int, msg_id: int):
    """记录重启提示消息后重启 embyboss 服务（不会返回）"""
    schedall.restart_chat_id = chat_id
    schedall.restart_msg_id = msg_id
    save_config()
    try:
        LOGGER.info("重启")
        os.execl('/bin/systemctl', 'systemctl', 'restart', 'embyboss')  # 用当前进程执行systemctl命令，重启embyboss服务
    except FileNotFoundError:
        exit(1)
