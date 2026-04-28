import math
import cn2an
from datetime import datetime, timezone, timedelta

from bot import bot, bot_photo, group, sakura_b, LOGGER, ranks, _open
from bot.func_helper.emby import emby
from bot.func_helper.utils import convert_to_beijing_time, convert_s, cache, get_users
from bot.sql_helper import Session
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_embys, Emby, sql_update_emby
from bot.func_helper.fix_bottons import plays_list_button


class Uplaysinfo:
    client = emby

    @classmethod
    @cache.memoize(ttl=120)
    async def users_playback_list(cls, days):
        play_list = await emby.emby_cust_commit(user_id=None, days=days, method='sp')
        if play_list is None:
            return None, 1, 1
        with Session() as session:
            # 查询 Emby 表的所有name不为空数据
            result = session.query(Emby).filter(Emby.name.isnot(None)).all()
            if not result:
                return None, 1
            page = math.ceil(len(play_list) / 10)
            members = await get_users()
            members_dict = {}
            for r in result:
                members_dict[r.name] = {"name": members.get(r.tg, '未绑定bot或已删除'), "tg": r.tg, "lv": r.lv,
                                        "iv": r.iv}
            n = 1
            ls = []
            a = []
            m = ["🥇", "🥈", "🥉", "🏅"]
            num = [1000, 900, 800, 700, 600, 500, 400, 300, 200, 100]
            while n <= page:
                d = (n - 1) * 10
                e = 1 if d == 0 else d + 1
                txt = f'**▎🏆{ranks.logo} {days} 天看片榜**\n\n'
                for p in play_list[d:d + 10]:
                    medal = m[e - 1] if e < 4 else m[3]
                    em = members_dict.get(p[0], None)
                    if not em:
                        emby_name = '未绑定bot或已删除'
                        tg = 'None'
                    else:
                        # emby_name = f'{em["name"][:1]}░{em["name"][-1:]}' if em["lv"] == 'a' else f'{em["name"]}' tg隐藏没意义
                        emby_name = em["name"]
                        tg = em["tg"]

                        iv = num[e - 1] + (int(p[1]) // 60) if e <= 10 else (int(p[1]) // 60)
                        new_iv = em["iv"] + iv if e <= 10 else em["iv"] + iv
                        ls.append([em["tg"], new_iv, medal + emby_name, iv])
                    ad_time = await convert_s(int(p[1]))
                    txt += f'{medal}**第{cn2an.an2cn(e)}名** | [{emby_name}](google.com?q={tg})\n' \
                           f'  播放时长 | {ad_time}\n'
                    e += 1
                txt += f'\n#UPlaysRank {datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")}'
                a.append(txt)
                n += 1
            return a, page, ls

    @staticmethod
    async def user_plays_rank(days=7, uplays=True):
        a, n, ls = await Uplaysinfo.users_playback_list(days)
        if not a:
            return await bot.send_photo(chat_id=group[0], photo=bot_photo,
                                        caption=f'🍥 获取过去{days}天UserPlays失败了嘤嘤嘤 ~ 手动重试 ')
        play_button = await plays_list_button(n, 1, days)
        send = await bot.send_photo(chat_id=group[0], photo=bot_photo, caption=a[0], reply_markup=play_button)
        if uplays and _open.uplays:
            if sql_update_embys(some_list=ls, method='iv'):
                text = f'**自动将观看时长转换为{sakura_b}**\n\n'
                for i in ls:
                    text += f'[{i[2]}](tg://user?id={i[0]}) 获得了 {i[3]} {sakura_b}奖励\n'
                n = 4096
                chunks = [text[i:i + n] for i in range(0, len(text), n)]
                for c in chunks:
                    await bot.send_message(chat_id=group[0],
                                           text=c + f'\n⏱️ 当前时间 - {datetime.now().strftime("%Y-%m-%d")}')
                LOGGER.info(f'【userplayrank】： ->成功 数据库执行批量操作{ls}')
            else:
                await send.reply(f'**🎂！！！为用户增加{sakura_b}出错啦** @工程师看看吧~ ')
                LOGGER.error(f'【userplayrank】：-？失败 数据库执行批量操作{ls}')

    @staticmethod
    async def check_low_activity():
        now = datetime.now(timezone(timedelta(hours=8)))
        success, users = await emby.users()
        if not success:
            return await bot.send_message(chat_id=group[0], text='⭕ 调用emby api失败')
        msg = ''

        async def load_last_activity(embyid):
            success_activity, activity = await emby.get_sidecar_user_last_activity(embyid)
            if not success_activity:
                return "None"
            last_activity = activity.get("LastActivityDate")
            if not last_activity:
                return "None"
            return convert_to_beijing_time(last_activity)

        # print(users)
        for user in users:
            # 数据库先找
            e = sql_get_emby(tg=user["Name"])
            if e is None:
                continue

            elif e.lv == 'c':
                # print(e.tg)
                ac_date = await load_last_activity(user["Id"])
                if ac_date == "None" or ac_date + timedelta(days=15) < now:
                    if await emby.emby_del(id=e.embyid):
                        msg += f'**🔋活跃检测** - [{e.name}](tg://user?id={e.tg})\n#id{e.tg} 禁用后未解禁，已执行删除。\n\n'
                        LOGGER.info(f"【活跃检测】- 删除账户 {user['Name']} #id{e.tg}")
                    else:
                        msg += f'**🔋活跃检测** - [{e.name}](tg://user?id={e.tg})\n#id{e.tg} 禁用后未解禁，执行删除失败。\n\n'
                        LOGGER.info(f"【活跃检测】- 删除账户失败 {user['Name']} #id{e.tg}")
            elif e.lv == 'b':
                ac_date = await load_last_activity(user["Id"])
                if ac_date != "None":
                    if ac_date + timedelta(days=21) < now:
                        if await emby.emby_change_policy(id=user["Id"], method=True):
                            sql_update_emby(Emby.embyid == user["Id"], lv='c')
                            msg += f"**🔋活跃检测** - [{user['Name']}](tg://user?id={e.tg})\n#id{e.tg} 21天未活跃，禁用\n\n"
                            LOGGER.info(f"【活跃检测】- 禁用账户 {user['Name']} #id{e.tg}：21天未活跃")
                        else:
                            msg += f"**🎂活跃检测** - [{user['Name']}](tg://user?id={e.tg})\n21天未活跃，禁用失败啦！检查emby连通性\n\n"
                            LOGGER.info(f"【活跃检测】- 禁用账户 {user['Name']} #id{e.tg}：禁用失败啦！检查emby连通性")
                else:
                    if await emby.emby_change_policy(id=user["Id"], method=True):
                        sql_update_emby(Emby.embyid == user["Id"], lv='c')
                        msg += f"**🔋活跃检测** - [{user['Name']}](tg://user?id={e.tg})\n#id{e.tg} 注册后未活跃，禁用\n\n"
                        LOGGER.info(f"【活跃检测】- 禁用账户 {user['Name']} #id{e.tg}：注册后未活跃禁用")
                    else:
                        msg += f"**🎂活跃检测** - [{user['Name']}](tg://user?id={e.tg})\n#id{e.tg} 注册后未活跃，禁用失败啦！检查emby连通性\n\n"
                        LOGGER.info(f"【活跃检测】- 禁用账户 {user['Name']} #id{e.tg}：禁用失败啦！检查emby连通性")
        n = 1000
        chunks = [msg[i:i + n] for i in range(0, len(msg), n)]
        for c in chunks:
            await bot.send_message(chat_id=group[0], text=c + f'**{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}**')
