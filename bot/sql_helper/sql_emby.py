"""
基本的sql操作
"""
from datetime import datetime

from bot.sql_helper import Base, Session, engine
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, case, inspect, text
from sqlalchemy import func
from sqlalchemy import or_
from bot.func_helper.line_access import line_pro_trial_expiry


class Emby(Base):
    """
    emby表，tg主键，默认值lv，us，iv
    """
    __tablename__ = 'emby'
    tg = Column(BigInteger, primary_key=True, autoincrement=False)
    embyid = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    pwd = Column(String(255), nullable=True)
    pwd2 = Column(String(255), nullable=True)
    douban = Column(String(255), nullable=True)
    lv = Column(String(1), default='d')
    invite = Column(String(1), default='n')
    cr = Column(DateTime, nullable=True)
    ex = Column(DateTime, nullable=True)
    us = Column(Integer, default=0)
    iv = Column(Integer, default=0)
    ch = Column(DateTime, nullable=True)
    notify_enabled = Column(Integer, default=0)
    line_pro_ex = Column(DateTime, nullable=True)
    line_pro_trial_used = Column(Integer, nullable=False, default=0)


Emby.__table__.create(bind=engine, checkfirst=True)


def _ensure_emby_columns():
    """为历史库补齐新增字段，避免老部署升级后缺列。"""
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("emby")}
    statements = []

    if "notify_enabled" not in columns:
        statements.append(
            "ALTER TABLE emby ADD COLUMN notify_enabled INT NOT NULL DEFAULT 0"
        )

    if "line_pro_ex" not in columns:
        statements.append(
            "ALTER TABLE emby ADD COLUMN line_pro_ex DATETIME NULL"
        )

    if "line_pro_trial_used" not in columns:
        statements.append(
            "ALTER TABLE emby ADD COLUMN line_pro_trial_used INT NOT NULL DEFAULT 0"
        )

    # 兼容已经部署过试用字段的数据库：当前有 Pro 权限的用户不再获得试用入口。
    statements.append(
        "UPDATE emby SET line_pro_trial_used = 1 "
        "WHERE line_pro_ex IS NOT NULL AND line_pro_trial_used = 0"
    )

    if statements:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))


_ensure_emby_columns()


def sql_add_emby(tg: int):
    """
    添加一条emby记录，如果tg已存在则忽略
    """
    with Session() as session:
        try:
            emby = Emby(tg=tg)
            session.add(emby)
            session.commit()
        except:
            pass


def sql_delete_emby(tg=None, embyid=None, name=None):
    """
    根据tg, embyid或name删除一条emby记录
    """
    with Session() as session:
        try:
            # 仅使用显式传入的参数构造查询条件，避免 None 变成 IS NULL 误删占位记录
            conditions = []
            if tg is not None:
                conditions.append(Emby.tg == tg)
            if embyid is not None:
                conditions.append(Emby.embyid == embyid)
            if name is not None:
                conditions.append(Emby.name == name)
            if not conditions:
                return None
            condition = or_(*conditions)
            # 用filter来过滤，注意要加括号
            emby = session.query(Emby).filter(condition).with_for_update().first()
            if emby:
                session.delete(emby)
                session.commit()
                return True
            else:
                return None
        except:
            return False


def sql_update_embys(some_list: list, method=None):
    """ 根据list中的tg值批量更新一些值 ，此方法不可更新主键"""
    with Session() as session:
        if method == 'iv':
            try:
                mappings = [{"tg": c[0], "iv": c[1]} for c in some_list]
                session.bulk_update_mappings(Emby, mappings)
                session.commit()
                return True
            except:
                session.rollback()
                return False
        if method == 'ex':
            try:
                mappings = [{"tg": c[0], "ex": c[1]} for c in some_list]
                session.bulk_update_mappings(Emby, mappings)
                session.commit()
                return True
            except:
                session.rollback()
                return False
        if method == 'bind':
            try:
                # mappings = [{"name": c[0], "embyid": c[1]} for c in some_list] 没有主键不能插入的这是emby表
                mappings = [{"tg": c[0], "name": c[1], "embyid": c[2]} for c in some_list]
                session.bulk_update_mappings(Emby, mappings)
                session.commit()
                return True
            except Exception as e:
                print(e)
                session.rollback()
                return False


def sql_get_emby(tg):
    """
    查询一条emby记录，可以根据tg, embyid或者name来查询
    """
    with Session() as session:
        try:
            # 使用or_方法来表示或者的逻辑，如果有tg就用tg，如果有embyid就用embyid，如果有name就用name，如果都没有就返回None
            emby = session.query(Emby).filter(or_(Emby.tg == tg, Emby.name == tg, Emby.embyid == tg, Emby.douban == tg)).first()
            return emby
        except:
            return None


# def sql_get_emby_by_embyid(embyid):
#     """
#     Retrieve an Emby object from the database based on the provided Emby ID.
#
#     Parameters:
#         embyid : The Emby ID used to identify the Emby object.
#
#     Returns:
#         tuple: A tuple containing a boolean value indicating whether the retrieval was successful
#                and the retrieved Emby object. If the retrieval was unsuccessful, the boolean value
#                will be False and the Emby object will be None.
#     """
#     with Session() as session:
#         try:
#             emby = session.query(Emby).filter((Emby.embyid == embyid)).first()
#             return True, emby
#         except Exception as e:
#             return False, None


def get_all_emby(condition):
    """
    查询所有emby记录
    """
    with Session() as session:
        try:
            embies = session.query(Emby).filter(condition).all()
            return embies
        except:
            return None


def sql_update_emby(condition, **kwargs):
    """
    更新一条emby记录，根据condition来匹配，然后更新其他的字段
    """
    with Session() as session:
        try:
            # 用filter来过滤，注意要加括号
            emby = session.query(Emby).filter(condition).first()
            if emby is None:
                return False
            # 然后用setattr方法来更新其他的字段，如果有就更新，如果没有就保持原样
            for k, v in kwargs.items():
                setattr(emby, k, v)
            session.commit()
            return True
        except:
            return False


def sql_rebind_emby(source_tg: int, target_tg: int, require_archived: bool = False):
    """将原账号的全部资料原子迁移到新 TG，仅替换 TG 主键。

    :return: success / source_not_found / target_not_found / target_has_account / same_tg / error
    """
    if source_tg == target_tg:
        return 'same_tg'

    with Session() as session:
        try:
            records = session.query(Emby).filter(
                Emby.tg.in_((source_tg, target_tg))
            ).order_by(Emby.tg).with_for_update().all()
            records = {record.tg: record for record in records}
            source = records.get(source_tg)
            target = records.get(target_tg)

            if source is None:
                return 'source_not_found'
            if target is None:
                return 'target_not_found'
            if target.embyid is not None:
                return 'target_has_account'
            if require_archived and source.lv != 'c':
                return 'source_not_archived'

            # 动态复制全部非主键列，避免豆瓣、余额、通知、Pro 等字段遗漏，
            # 以后 Emby 表新增的账号字段也会自动随改绑继承。
            for column in Emby.__table__.columns:
                if column.name != 'tg':
                    setattr(target, column.name, getattr(source, column.name))

            session.delete(source)
            session.commit()
            return 'success'
        except Exception:
            session.rollback()
            return 'error'


def sql_claim_line_pro_trial(tg: int, now=None):
    """原子领取一次 1 天直连 Pro 试用；成功返回新到期时间。"""
    now = now or datetime.now()
    with Session() as session:
        try:
            user = session.query(Emby).filter(
                Emby.tg == tg,
                Emby.line_pro_trial_used == 0,
            ).with_for_update().first()
            if user is None:
                return None

            user.line_pro_ex = line_pro_trial_expiry(user.line_pro_ex, now=now)
            user.line_pro_trial_used = 1
            expires_at = user.line_pro_ex
            session.commit()
            return expires_at
        except Exception:
            session.rollback()
            return False


#
# def sql_change_emby(name, new_tg):
#     with Session() as session:
#         try:
#             emby = session.query(Emby).filter_by(name=name).first()
#             if emby is None:
#                 return False
#             emby.tg = new_tg
#             session.commit()
#             return True
#         except Exception as e:
#             print(e)
#             return False


def sql_count_emby():
    """
    # 检索 TG、Emby 账号、白名单和当前有效直连 Pro 的真实数据库数量
    # count = sql_count_emby()
    :return: int, int, int, int
    """
    with Session() as session:
        try:
            now = datetime.now()
            # 使用func.count来计算数量，使用filter来过滤条件
            count = session.query(
                func.count(Emby.tg).label("tg_count"),
                func.count(Emby.embyid).label("embyid_count"),
                func.count(case((Emby.lv == "a", 1))).label("lv_a_count"),
                func.count(case((Emby.line_pro_ex > now, 1))).label("line_pro_count"),
            ).first()
        except Exception as e:
            # print(e)
            return None, None, None, None
        else:
            return count.tg_count, count.embyid_count, count.lv_a_count, count.line_pro_count


def sql_count_registered_slots():
    """配置文件的已注册人数只计算正常账号 b 和到期封存账号 c。"""
    with Session() as session:
        try:
            return session.query(func.count(Emby.tg)).filter(
                Emby.lv.in_(("b", "c"))
            ).scalar()
        except Exception:
            return None
