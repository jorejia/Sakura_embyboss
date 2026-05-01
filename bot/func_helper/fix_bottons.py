from pykeyboard import InlineKeyboard, InlineButton
from pyrogram.types import InlineKeyboardMarkup
from pyromod.helpers import ikb, array_chunk
from bot import chanel, main_group, bot_name, extra_emby_libs, _open, user_buy, sakura_b, schedall
from bot.func_helper.emby import emby
from bot.func_helper.utils import judge_admins, members_info, convert_to_beijing_time

"""start面板 ↓"""


def judge_start_ikb(uid: int) -> InlineKeyboardMarkup:
    """
    start面板按钮
    :param uid:
    :return:
    """
    d = [['️👥 用户功能', 'members'], ['🌐 服务器', 'server'], ['🎟️ 使用注册码', 'exchange']]
    if _open.checkin:
        d.append([f'🎯 签到', 'checkin'])
    if user_buy.stat:
        d.append(user_buy.button)
    lines = array_chunk(d, 2)
    if judge_admins(uid):
        lines.append([['👮🏻‍♂️ admin', 'manage']])
    keyword = ikb(lines)
    return keyword


# un_group_answer
group_f = ikb([[('点击我(●ˇ∀ˇ●)', f't.me/{bot_name}', 'url')]])
# un in group
judge_group_ikb = ikb([[('🌟 上新通知频道', f't.me/{chanel}', 'url'),
                        ('💫 MICU Media 股东会', f't.me/{main_group}', 'url')]])

"""members ↓"""


def members_ikb(emby=False) -> InlineKeyboardMarkup:
    """
    判断用户面板
    :param emby:
    :return:
    """
    if emby:
        return ikb([[('🏪 兑换商店', 'storeall'), ('📺 追剧推送', 'notify_menu')],
                    [('🛡️ 家长控制', 'parental_menu'), ('🛣️ 线路选择', 'line_menu')],
                    [('🎬 豆瓣点播', 'dianbo'), ('⭕ 重置密码', 'reset')],
                    [('♻️ 主界面', 'back_start')]])
    else:
        return ikb(
            [[('👑 注册Emby账号', 'create')], [('⭕ 从被封禁TG换绑', 'changetg')],
             [('♻️ 主界面', 'back_start')]])


back_start_ikb = ikb([[('💫 回到首页', 'back_start')]])
back_members_ikb = ikb([[('💨 返回', 'members')]])
server_info_ikb = ikb([[('🔙 - 用户', 'members'), ('❌ - 上一级', 'back_start')]])
re_create_ikb = ikb([[('🍥 重新输入', 'create'), ('💫 用户主页', 'members')]])
re_changetg_ikb = ikb([[('✨ 换绑TG', 'changetg'), ('💫 用户主页', 'members')]])
re_bindtg_ikb = ikb([[('✨ 绑定TG', 'bindtg'), ('💫 用户主页', 'members')]])
re_delme_ikb = ikb([[('♻️ 重试', 'delme')], [('🔙 返回', 'members')]])
re_reset_ikb = ikb([[('♻️ 重试', 'reset')], [('🔙 返回', 'members')]])
re_exchange_b_ikb = ikb([[('♻️ 重试', 'exchange'), ('❌ 关闭', 'closeit')]])
re_douban_ikb = ikb([[('♻️ 重试', 'dianadd'), ('❌ 关闭', 'closeit')]])

def dianbo_ikb():
    return ikb([[('🫛 绑定豆瓣ID', 'dianadd'), ('✖️ 清除绑定', 'diandel')], [('🔙 返回', 'members')]])

def dianbo_no_ikb():
    return ikb([[], [('❌ 取消', 'members')]])


def notify_menu_ikb(enabled: bool):
    action_text = '关闭追剧推送' if enabled else '开启追剧推送'
    return ikb([
        [(f'📺 {action_text}', 'notify_toggle')],
        [('🔙 返回', 'members')]
    ])


def parental_menu_ikb(current_value: int):
    def label(value: int, text: str) -> str:
        prefix = '✅ ' if current_value == value else ''
        return f'{prefix}{text}'

    return ikb([
        [[label(1, '0+ 全龄'), 'parental_set:1'], [label(4, '7+ 少儿'), 'parental_set:4']],
        [[label(7, '12+ 指导'), 'parental_set:7'], [label(8, '16+ 青少'), 'parental_set:8']],
        [[label(10, '18+ 全部'), 'parental_set:10']],
        [('🔙 返回', 'members')]
    ])


def parental_rating_label(value: int) -> str:
    mapping = {
        1: '0+ 全龄',
        4: '7+ 少儿',
        7: '12+ 指导',
        8: '16+ 青少',
        9: '17+ 限制',
        10: '18+ 成人'
    }
    return mapping.get(value, f'未知({value})')


def line_menu_ikb(current_value: int):
    def label(value: int, text: str) -> str:
        prefix = '✅ ' if current_value == value else ''
        return f'{prefix}{text}'

    return ikb([
        [[label(1, '直连一线'), 'line_set:1'], [label(2, '直连二线'), 'line_set:2']],
        [('🔙 返回', 'members')]
    ])


def line_label(value: int) -> str:
    mapping = {
        1: '直连一线',
        2: '直连二线'
    }
    return mapping.get(value, f'未知({value})')



def store_ikb():
    return ikb([[(f'🕐 兑换时长', 'store-renew')], [(f'🔍 我的邀请码', 'store-query'), (f'🔙 返回', 'members')]])

def store_vip_ikb():
    return ikb([[(f'🕐 兑换时长', 'store-renew'), (f'🎟️ 兑换邀请码', 'store-invite')], [(f'🔍 我的邀请码', 'store-query'), (f'🔙 返回', 'members')]])

def store_c_ikb():
    return ikb([[(f'🔍 我的邀请码', 'store-query'), (f'🔙 返回', 'members')]])


re_store_renew = ikb([[('✨ 重新输入', 'changetg'), ('💫 取消输入', 'storeall')]])


def del_me_ikb(embyid) -> InlineKeyboardMarkup:
    return ikb([[('🎯 确定', f'delemby-{embyid}')], [('🔙 取消', 'members')]])


def emby_block_ikb(embyid) -> InlineKeyboardMarkup:
    return ikb(
        [[("✔️️ - 显示", f"emby_unblock-{embyid}"), ("✖️ - 隐藏", f"emby_block-{embyid}")], [("🔙 返回", "members")]])


user_emby_block_ikb = ikb([[('✅ 已隐藏', 'members')]])
user_emby_unblock_ikb = ikb([[('❎ 已显示', 'members')]])


def checkin_menu_ikb(options=None) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard(row_width=4)
    options = options or []
    if options:
        keyboard.row(*[InlineButton(str(option), f'checkin_answer:{option}') for option in options])
    keyboard.row(InlineButton('♻️ 主界面', 'back_start'))
    return keyboard

"""admins ↓"""

gm_ikb_content = ikb([[('⭕ 注册状态', 'open-menu'), ('🎁 生成活动码', 'cr_activity'), ('🎟️ 生成注册', 'cr_link')],
                      [('💊 查询注册', 'ch_link'), ('🏷️ 别名设置', 'alias_setting'), ('🏬 兑换设置', 'set_renew')],
                      [('🌏 定时', 'schedall'), ('🕹️ 主界面', 'back_start'), ('其他 🪟', 'back_config')]])


def open_menu_ikb(openstats, timingstats) -> InlineKeyboardMarkup:
    return ikb([[(f'{openstats} 自由注册', 'open_stat'), (f'{timingstats} 定时注册', 'open_timing')],
                [('⭕ 注册限制', 'all_user_limit')], [('🌟 返回上一级', 'manage')]])


back_free_ikb = ikb([[('🔙 返回上一级', 'open-menu')]])
back_open_menu_ikb = ikb([[('🪪 重新定时', 'open_timing'), ('🔙 注册状态', 'open-menu')]])
re_cr_link_ikb = ikb([[('♻️ 继续创建', 'cr_link'), ('🎗️ 返回主页', 'manage')]])
close_it_ikb = ikb([[('❌ - Close', 'closeit')]])


def ch_link_ikb(ls: list) -> InlineKeyboardMarkup:
    lines = array_chunk(ls, 2)
    lines.append([["💫 回到首页", "manage"]])
    return ikb(lines)


def alias_setting_ikb(item_id) -> InlineKeyboardMarkup:
    return ikb([[('🧹 清空别名', f'alias_clear-{item_id}'), ('✏️ 修改别名', f'alias_modify-{item_id}')],
                [('🔙 返回', 'manage')]])


def date_ikb(i) -> InlineKeyboardMarkup:
    return ikb([[('🌘 - 月', f'register_mon_{i}'), ('🌗 - 季', f'register_sea_{i}'),
                 ('🌖 - 半年', f'register_half_{i}')],
                [('🌕 - 年', f'register_year_{i}'), ('🎟️ - 已用', f'register_used_{i}')], [('🔙 - 返回', 'ch_link')]])


# 翻页按钮
async def cr_paginate(i, j, n) -> InlineKeyboardMarkup:
    """
    :param i: 总数
    :param j: 目前
    :param n: mode 可变项
    :return:
    """
    keyboard = InlineKeyboard()
    keyboard.paginate(i, j, 'pagination_keyboard:{number}' + f'-{n}')
    keyboard.row(
        InlineButton('❌ - Close', 'closeit')
    )
    return keyboard


async def users_iv_button(i, j, tg) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard()
    keyboard.paginate(i, j, 'users_iv:{number}' + f'_{tg}')
    keyboard.row(
        InlineButton('❌ - Close', f'closeit_{tg}')
    )
    return keyboard


async def plays_list_button(i, j, days) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard()
    keyboard.paginate(i, j, 'uranks:{number}' + f'_{days}')
    keyboard.row(
        InlineButton('❌ - Close', f'closeit')
    )
    return keyboard


async def user_query_page(i, j) -> InlineKeyboardMarkup:
    """
    member的注册码查询分页
    :param i: 总
    :param j: 当前
    :param tg: tg
    :return:
    """
    keyboard = InlineKeyboard()
    keyboard.paginate(i, j, 'store-query:{number}')
    keyboard.row(
        InlineButton('❌ Close', f'closeit'), InlineButton('🔙 Back', 'storeall')
    )
    return keyboard


def cr_renew_ikb():
    checkin = '✔️' if _open.checkin else '❌'
    exchange = '✔️' if _open.exchange else '❌'
    whitelist = '✔️' if _open.whitelist else '❌'
    invite = '✔️' if _open.invite else '❌'
    keyboard = InlineKeyboard(row_width=2)
    keyboard.add(InlineButton(f'{checkin} 每日签到', f'set_renew-checkin'),
                 InlineButton(f'{exchange} 自动{sakura_b}续期', f'set_renew-exchange'),
                 InlineButton(f'{whitelist} 兑换白名单', f'set_renew-whitelist'),
                 InlineButton(f'{invite} 兑换邀请码', f'set_renew-invite'))
    keyboard.row(InlineButton(f'◀ 返回', 'manage'))
    return keyboard


""" config_panel ↓"""


def config_preparation() -> InlineKeyboardMarkup:
    code = '✅' if _open.allow_code else '❎'
    buy_stat = '✅' if user_buy.stat else '❎'
    leave_ban = '✅' if _open.leave_ban else '❎'
    uplays = '✅' if _open.uplays else '❎'
    site = '✅' if _open.site else '❎'
    keyboard = ikb(
        [[('📄 导出日志', 'log_out'), ('💠 emby线路', 'set_line')],
         [(f'{site} 正常/隐身模式', 'change_site_open')],
         [(f'{code} 注册码续期', 'open_allow_code'), (f'{buy_stat} 开关购买', 'set_buy')],
         [(f'{leave_ban} 退群封禁', 'leave_ban'), (f'{uplays} 自动看片结算', 'set_uplays')],
         [('🔙 返回', 'manage')]])
    return keyboard


back_config_p_ikb = ikb([[("🎮  ️返回主控", "back_config")]])


def back_set_ikb(method) -> InlineKeyboardMarkup:
    return ikb([[("♻️ 重新设置", f"{method}"), ("🔙 返回主页", "back_config")]])


def try_set_buy(ls: list) -> InlineKeyboardMarkup:
    d = [[ls], [["✅ 体验结束返回", "back_config"]]]
    return ikb(d)


""" other """
register_code_ikb = ikb([[('🎟️ 注册', 'create'), ('⭕ 取消', 'closeit')]])
dp_g_ikb = ikb([[("🈺 ╰(￣ω￣ｏ)", "t.me/Aaaaa_su", "url")]])


async def cr_kk_ikb(uid, first):
    text = ''
    text1 = ''
    keyboard = []
    data = await members_info(uid)
    if data is None:
        text += f'**· 🆔 TG** ：[{first}](tg://user?id={uid}) [`{uid}`]\n请点击 /start 唤起菜单'
    else:
        name, lv, ex, us, embyid, pwd2, douban = data
        if douban is None:
            douban = '未绑定'
        if name != '无账户信息':
            ban = "🌟 解除禁用" if lv == "**到期封存**" else '💢 禁用账户'
            keyboard = [[ban, f'user_ban-{uid}'], ['⚠️ 删除账户', f'closeemby-{uid}']]
            if len(extra_emby_libs) > 0:
                success, rep = emby.user(embyid=embyid)
                if success:
                    try:
                        currentblock = rep["Policy"]["BlockedMediaFolders"]
                    except KeyError:
                        currentblock = []
                    # 此处符号用于展示是否开启的状态
                    libs, embyextralib = ['✖️', f'embyextralib_unblock-{uid}'] if set(extra_emby_libs).issubset(
                        set(currentblock)) else ['✔️', f'embyextralib_block-{uid}']
                    keyboard.append([f'{libs} 额外媒体库', embyextralib])
            last_activity_text = "未知"
            try:
                success, activity = await emby.get_sidecar_user_last_activity(embyid)
                if success:
                    last_activity = activity.get("LastActivityDate")
                    if last_activity:
                        last_activity_text = convert_to_beijing_time(last_activity).strftime("%Y-%m-%d %H:%M:%S")
                text1 = f"**· 🔋 上次活动** | {last_activity_text}\n"
            except (TypeError, IndexError, ValueError):
                text1 = f"**· 🔋 上次活动** | {last_activity_text}\n"
        else:
            keyboard.append(['✨ 赠送资格', f'gift-{uid}'])
        text += f"**· 🍉 TG&名称** | [{first}](tg://user?id={uid})\n" \
                f"**· 🍒 用户のID** | `{uid}`\n" \
                f"**· 🍓 当前状态** | {lv}\n" \
                f"**· 🫛 豆瓣のID** | `{douban}`\n" \
                f"**· 🍥 当前{sakura_b}** | {us[1]}\n" \
                f"**· ⏰ 未用天数** | {us[0]}\n" \
                f"**· 💠 账号名称** | {name}\n" \
                f"**· 🚨 到期时间** | **{ex}**\n"
        text += text1
        keyboard.extend([['🚫 踢出并封禁', f'fuckoff-{uid}'], ['❌ 删除消息', f'closeit']])
        lines = array_chunk(keyboard, 2)
        keyboard = ikb(lines)
    return text, keyboard


def cv_user_ip(user_id):
    return ikb([[('🌏 播放查询', f'userip-{user_id}'), ('❌ 关闭', 'closeit')]])


def gog_rester_ikb(link=None) -> InlineKeyboardMarkup:
    link_ikb = ikb([[('🎁 点击领取', link, 'url')]]) if link else ikb([[('👆🏻 点击注册', f't.me/{bot_name}', 'url')]])
    return link_ikb


""" sched_panel ↓"""


def sched_buttons():
    dayrank = '✅' if schedall.dayrank else '❎'
    weekrank = '✅' if schedall.weekrank else '❎'
    dayplayrank = '✅' if schedall.dayplayrank else '❎'
    weekplayrank = '✅' if schedall.weekplayrank else '❎'
    check_ex = '✅' if schedall.check_ex else '❎'
    low_activity = '✅' if schedall.low_activity else '❎'
    backup_db = '✅' if schedall.backup_db else '❎'
    keyboard = InlineKeyboard(row_width=2)
    keyboard.add(InlineButton(f'{dayrank} 播放日榜', f'sched-dayrank'),
                 InlineButton(f'{weekrank} 播放周榜', f'sched-weekrank'),
                 InlineButton(f'{dayplayrank} 看片日榜', f'sched-dayplayrank'),
                 InlineButton(f'{weekplayrank} 看片周榜', f'sched-weekplayrank'),
                 InlineButton(f'{check_ex} 到期保号', f'sched-check_ex'),
                 InlineButton(f'{low_activity} 活跃保号', f'sched-low_activity'),
                 InlineButton(f'{backup_db} 自动备份数据库', f'sched-backup_db'),
                 )
    keyboard.row(InlineButton(f'🫧 返回', 'manage'))
    return keyboard


""" checkin 按钮↓"""

# def shici_button(ls: list):
#     shici = []
#     for l in ls:
#         l = [l, f'checkin-{l}']
#         shici.append(l)
#     # print(shici)
#     lines = array_chunk(shici, 4)
#     return ikb(lines)


# checkin_button = ikb([[('🔋 重新签到', 'checkin'), ('🎮 返回主页', 'back_start')]])
