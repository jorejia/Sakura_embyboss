import math
from datetime import datetime, timedelta

from bot.sql_helper import Base, Session, engine
from bot.sql_helper.sql_emby import Emby
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, or_, and_, case, func
from cacheout import Cache

cache = Cache()


class Code(Base):
    """
    register_code表，code主键，tg,us,used,used_time
    """
    __tablename__ = 'Rcode'
    code = Column(String(50), primary_key=True, autoincrement=False)
    tg = Column(BigInteger)
    us = Column(Integer)
    invite = Column(String(1), default='n')
    used = Column(BigInteger, nullable=True)
    usedtime = Column(DateTime, nullable=True)


Code.__table__.create(bind=engine, checkfirst=True)


def _non_line_code_condition():
    return or_(Code.invite != 'l', Code.invite.is_(None))


def sql_add_code(code_list: list, tg: int, us: int, invite: str):
    """ 批量添加记录，如果code已存在则忽略 """
    with Session() as session:
        try:
            code_list = [Code(code=c, tg=tg, us=us, invite=invite) for c in code_list]
            session.add_all(code_list)
            session.commit()
            return True
        except:
            session.rollback()
            return False


def sql_update_code(code, used: int, usedtime):
    with Session() as session:
        try:
            data = {"used": used, "usedtime": usedtime}
            c = session.query(Code).filter(Code.code == code).update(data)
            if c == 0:
                return False
            session.commit()
            return True
        except Exception as e:
            print(e)
            return False


def sql_get_code(code):
    with Session() as session:
        try:
            code = session.query(Code).filter(Code.code == code).first()
            return code
        except:
            return None


def sql_get_activity_code_usage(codes):
    """批量查询活动码的最新使用状态。"""
    if not codes:
        return {}
    with Session() as session:
        try:
            records = session.query(Code).filter(
                Code.code.in_(codes),
                Code.invite == 'a'
            ).all()
            return {record.code: record.used is not None for record in records}
        except Exception:
            return None


def sql_delete_unused_code(code):
    """删除一条仍未使用的注册码。

    :return: deleted / used / not_found / error
    """
    with Session() as session:
        try:
            record = session.query(Code).filter(Code.code == code).with_for_update().first()
            if record is None:
                return 'not_found'
            if record.used is not None:
                return 'used'
            session.delete(record)
            session.commit()
            return 'deleted'
        except Exception:
            session.rollback()
            return 'error'


def sql_ban_used_code(code, now=None):
    """处罚已使用注册码，并在扣除成功后原子删除该码。

    普通码扣账号/预注册时长，直连 Pro 码扣 Pro 时长。普通码扣除后
    账号时长不足时交由调用方删号；Pro 时长不足时仅清除 Pro 资格。
    """
    now = (now or datetime.now()).replace(microsecond=0)
    with Session() as session:
        try:
            record = session.query(Code).filter(Code.code == code).with_for_update().first()
            if record is None:
                return {'status': 'not_found'}
            if record.used is None:
                return {'status': 'unused'}

            user = session.query(Emby).filter(Emby.tg == record.used).with_for_update().first()
            if user is None:
                return {'status': 'user_not_found', 'tg': record.used}

            days = int(record.us or 0)
            if days <= 0:
                return {'status': 'invalid_duration', 'tg': record.used}

            # 尚未创建 Emby 账号时，注册码时长保存在 us 中。
            if not user.embyid:
                available_days = max(int(user.us or 0), 0)
                if available_days == 0:
                    return {'status': 'no_account', 'tg': record.used}
                deducted_days = min(days, available_days)
                user.us = available_days - deducted_days
                used_tg = record.used
                session.delete(record)
                session.commit()
                return {
                    'status': 'deducted',
                    'tg': used_tg,
                    'days': deducted_days,
                    'remaining_days': user.us,
                    'expiry_kind': 'preregister',
                    'expires_at': None,
                }

            expiry_kind = 'line_pro' if record.invite == 'l' else 'account'
            expires_at = user.line_pro_ex if expiry_kind == 'line_pro' else user.ex
            new_expiry = expires_at - timedelta(days=days) if expires_at else None

            if new_expiry is None or new_expiry <= now:
                if expiry_kind == 'line_pro':
                    return {
                        'status': 'revoke_line_required',
                        'tg': record.used,
                        'days': days,
                        'embyid': user.embyid,
                    }
                return {
                    'status': 'delete_required',
                    'tg': record.used,
                    'days': days,
                    'embyid': user.embyid,
                    'name': user.name,
                    'expiry_kind': expiry_kind,
                }

            if expiry_kind == 'line_pro':
                user.line_pro_ex = new_expiry
            else:
                user.ex = new_expiry
            used_tg = record.used
            session.delete(record)
            session.commit()
            return {
                'status': 'deducted',
                'tg': used_tg,
                'days': days,
                'remaining_days': None,
                'expiry_kind': expiry_kind,
                'expires_at': new_expiry,
            }
        except Exception:
            session.rollback()
            return {'status': 'error'}


def sql_revoke_line_pro_code(code, expected_tg):
    """清除非法线路码对应的 Pro 资格，并在同一事务中删除线路码。"""
    with Session() as session:
        try:
            record = session.query(Code).filter(Code.code == code).with_for_update().first()
            if record is None:
                return 'not_found'
            if record.invite != 'l' or record.used != expected_tg:
                return 'mismatch'

            user = session.query(Emby).filter(Emby.tg == expected_tg).with_for_update().first()
            if user is None:
                return 'user_not_found'
            user.line_pro_ex = None
            session.delete(record)
            session.commit()
            return 'revoked'
        except Exception:
            session.rollback()
            return 'error'


def sql_delete_used_code(code, expected_tg):
    """账号处罚完成后删除对应的已使用注册码。"""
    with Session() as session:
        try:
            record = session.query(Code).filter(Code.code == code).with_for_update().first()
            if record is None:
                return 'not_found'
            if record.used is None or record.used != expected_tg:
                return 'mismatch'
            session.delete(record)
            session.commit()
            return 'deleted'
        except Exception:
            session.rollback()
            return 'error'


@cache.memoize(ttl=120)
def sql_count_code(tg: int = None):
    with Session() as session:
        if tg is None:
            try:
                # 查询used不为空的数量
                used_count = session.query(func.count()).filter(Code.used != None).filter(
                    _non_line_code_condition()).scalar()
                # 查询used为空时，us=30，90，180，360的数量
                us_list = [30, 90, 180, 365]  # 创建一个列表，存储us的值
                tg_mon, tg_sea, tg_half, tg_year = [
                    session.query(func.count()).filter(Code.used == None).filter(Code.us == us).filter(
                        _non_line_code_condition()).scalar() for us in
                    us_list]  # 用一个列表推导式来查询数量
                return used_count, tg_mon, tg_sea, tg_half, tg_year
            except Exception as e:
                print(e)
                return None
        else:
            try:
                used_count = session.query(func.count()).filter(Code.used != None).filter(Code.tg == tg).filter(
                    _non_line_code_condition()).scalar()
                us_list = [30, 90, 180, 365]
                tg_mon, tg_sea, tg_half, tg_year = [
                    session.query(func.count()).filter(Code.used == None).filter(Code.us == us).filter(
                        Code.tg == tg).filter(_non_line_code_condition()).scalar() for us in
                    us_list]
                return used_count, tg_mon, tg_sea, tg_half, tg_year
            except Exception as e:
                print(e)
                return None


@cache.memoize(ttl=120)
def sql_count_line_code(tg: int = None):
    with Session() as session:
        query = session.query(Code).filter(Code.invite == 'l')
        if tg is not None:
            query = query.filter(Code.tg == tg)
        unused_count = query.filter(Code.used.is_(None)).count()
        used_count = query.filter(Code.used.isnot(None)).count()
        return used_count, unused_count


@cache.memoize(ttl=120)
def sql_count_p_code(tg_id, us):
    with Session() as session:
        try:
            if us == 0:
                p = session.query(func.count()).filter(Code.used != None).filter(Code.tg == tg_id).filter(
                    _non_line_code_condition()).scalar()
            else:
                p = session.query(func.count()).filter(Code.us == us).filter(Code.tg == tg_id).filter(
                    _non_line_code_condition()).scalar()
            if p == 0:
                return None, 1
            i = math.ceil(p / 30)
            a = []
            b = 1
            # 分析出页数，将检索出 分割p（总数目）的 间隔，将间隔分段，放进【】中返回
            while b <= i:
                d = (b - 1) * 30
                if us != 0:
                    # 查询us和tg匹配的记录，按tg升序，usedtime降序排序，分页查询
                    result = session.query(Code.tg, Code.code, Code.used, Code.usedtime).filter(Code.us == us).filter(
                        Code.tg == tg_id).filter(Code.used == None).filter(_non_line_code_condition()).order_by(
                        Code.tg.asc(), Code.usedtime.desc()).limit(
                        30).offset(d).all()
                else:
                    result = session.query(Code.tg, Code.code, Code.used, Code.usedtime, Code.us).filter(
                        Code.used != None).filter(
                        Code.tg == tg_id).filter(_non_line_code_condition()).order_by(
                        Code.tg.asc(), Code.usedtime.desc()).limit(30).offset(d).all()
                x = ''
                e = 1 if d == 0 else d + 1
                for link in result:
                    if us == 0:
                        c = f'{e}. `' + f'{link[1]}`' + f'\n🎁 {link[4]}d - [{link[2]}](tg://user?id={link[0]})(__{link[3]}__)\n'
                    else:
                        c = f'{e}. `' + f'{link[1]}`\n'
                    x += c
                    e += 1
                a.append(x)
                b += 1
            # a 是数量，i是页数
            return a, i
        except Exception as e:
            # 查询失败时，打印异常信息，并返回None
            print(e)
            return None, 1


@cache.memoize(ttl=120)
def sql_count_c_code(tg_id):
    with Session() as session:
        try:
            p = session.query(func.count()).filter(Code.tg == tg_id).scalar()
            if p == 0:
                return None, 1
            i = math.ceil(p / 5)
            a = []
            b = 1
            # 分析出页数，将检索出 分割p（总数目）的 间隔，将间隔分段，放进【】中返回
            while b <= i:
                d = (b - 1) * 5
                result = session.query(Code.tg, Code.code, Code.used, Code.usedtime, Code.us).filter(
                        Code.tg == tg_id).order_by(Code.tg.asc(), Code.usedtime.desc()).limit(5).offset(d).all()
                x = ''
                e = 1 if d == 0 else d + 1
                for link in result:
                    c = f'{e}. `{link[1]}`\n' \
                        f'🎁： {link[4]} 天 | 👤[{link[2]}](tg://user?id={link[2]})\n' \
                        f'🌏：{link[3]}\n\n'
                    x += c
                    e += 1
                a.append(x)
                b += 1
            # a 是数量，i是页数
            return a, i
        except Exception as e:
            # 查询失败时，打印异常信息，并返回None
            print(e)
            return None, 1
