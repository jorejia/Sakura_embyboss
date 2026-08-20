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


@bot.on_message(filters.command('check_ex', prefixes) & admins_on_filter)
async def check_ex_admin(_, msg):
    send = await msg.reply("🍥 正在运行 【到期检测】。。。")
    result = await check_expired()
    if result == 'paused':
        return await asyncio.gather(
            msg.delete(),
            send.edit("⏸️ 【到期检测已暂停】本次未执行"),
        )
    await asyncio.gather(msg.delete(), send.edit("✅ 【到期检测结束】"))


# bot数据库手动备份
@bot.on_message(filters.command('backup_db', prefixes) & filters.user(owner))
async def manual_backup_db(_, msg):
    await asyncio.gather(deleteMessage(msg), auto_backup_db())


@bot.on_message(filters.command('days_ranks', prefixes) & admins_on_filter)
async def day_r_ranks(_, msg):
    await asyncio.gather(msg.delete(), day_ranks(pin_mode=False))


@bot.on_message(filters.command('week_ranks', prefixes) & admins_on_filter)
async def week_r_ranks(_, msg):
    await asyncio.gather(msg.delete(), week_ranks(pin_mode=False))


@bot.on_message(filters.command('restart', prefixes) & admins_on_filter)
async def restart_bot(_, msg):
    await deleteMessage(msg)
    send = await msg.reply("Restarting，等待几秒钟。")
    schedall.restart_chat_id = send.chat.id
    schedall.restart_msg_id = send.id
    save_config()
    try:
        # some code here
        LOGGER.info("重启")
        os.execl('/bin/systemctl', 'systemctl', 'restart', 'embyboss')  # 用当前进程执行systemctl命令，重启embyboss服务
    except FileNotFoundError:
        exit(1)
