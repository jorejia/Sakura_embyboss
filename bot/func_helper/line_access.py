from datetime import datetime, timedelta


def line_pro_active(expires_at, now=None):
    if expires_at is None:
        return False
    return expires_at > (now or datetime.now())


def line_pro_status_text(expires_at, now=None):
    if not line_pro_active(expires_at, now=now):
        return '未激活'
    return expires_at.strftime('%Y-%m-%d %H:%M:%S')


def line_pro_trial_expiry(expires_at, now=None):
    """计算一次 1 天 Pro 试用的新到期时间，不缩短现有有效时长。"""
    now = now or datetime.now()
    base = expires_at if line_pro_active(expires_at, now=now) else now
    return base + timedelta(days=1)


def line_pro_trial_available(trial_used, expires_at, now=None):
    """只有从未试用且当前没有 Pro 权限时才展示试用入口。"""
    return not bool(trial_used) and not line_pro_active(expires_at, now=now)


def configured_line(options, value):
    return next((option for option in options if option.id == value), None)


def visible_lines(options, has_pro):
    return [option for option in options if has_pro or not option.pro]


def line_requires_pro(options, value):
    option = configured_line(options, value)
    return bool(option and option.pro)


async def revoke_line_pro_access(emby_id, default_line_id, set_use_line, clear_permission):
    """先切回默认线路，再清除 Pro 权限；返回 (成功, 失败阶段, 详情)。"""
    if emby_id:
        ok, result = await set_use_line(emby_id, default_line_id)
        if not ok:
            return False, 'line', result

    if not clear_permission():
        return False, 'database', None
    return True, None, None
