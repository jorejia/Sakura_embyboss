"""
额外账号：管理员手动添加、不绑定 Telegram 的账号。

沿用历史约定：tg 使用 1~99999 的占位编号（真实 Telegram 用户 id 远大于此），等级 a（白名单，不参与到期检测）。
"""
from datetime import datetime

from sqlalchemy import func

from bot import LOGGER
from bot.sql_helper import Session
from bot.sql_helper.sql_emby import Emby

EXTRA_TG_MIN = 1
EXTRA_TG_MAX = 99999


def is_extra_tg(tg) -> bool:
    try:
        return EXTRA_TG_MIN <= int(tg) <= EXTRA_TG_MAX
    except (TypeError, ValueError):
        return False


def sql_list_extra_accounts():
    with Session() as session:
        try:
            return session.query(Emby).filter(
                Emby.tg >= EXTRA_TG_MIN, Emby.tg <= EXTRA_TG_MAX, Emby.embyid.isnot(None)
            ).order_by(Emby.tg).all()
        except Exception as e:
            LOGGER.error(f"查询额外账号失败: {e}")
            return []


def sql_add_extra_account(embyid: str, name: str, pwd: str, pwd2: str):
    """分配下一个占位 tg 并写入记录，返回 tg；失败返回 None。"""
    with Session() as session:
        try:
            current = session.query(func.max(Emby.tg)).filter(
                Emby.tg >= EXTRA_TG_MIN, Emby.tg <= EXTRA_TG_MAX
            ).with_for_update().scalar()
            tg = (current or 0) + 1
            if tg > EXTRA_TG_MAX:
                LOGGER.error("额外账号占位编号已用尽")
                return None
            session.add(Emby(tg=tg, embyid=embyid, name=name, pwd=pwd, pwd2=pwd2, lv='a',
                             cr=datetime.now(), ex=None, us=0, iv=0, notify_enabled=0))
            session.commit()
            return tg
        except Exception as e:
            session.rollback()
            LOGGER.error(f"写入额外账号失败: {e}")
            return None
