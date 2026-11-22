"""
直连线路配置：以 sidecar 为准（管理页修改后即时生效），本地缓存 30 秒。

sidecar 不可用时沿用上一次成功读取的结果；从未读取成功时退回 config.json 里的旧配置（仅作兜底）。
返回的线路对象带 id / name / pro 属性，与 line_access 里的函数兼容。
"""
import time
from types import SimpleNamespace

from bot import LOGGER, line_options as _config_lines, default_line_id as _config_default_line

_TTL = 30
_cache = {"at": 0.0, "lines": None, "default": None}


def _refresh(force=False):
    if not force and _cache["lines"] is not None and time.time() - _cache["at"] < _TTL:
        return
    from bot.func_helper.emby import emby
    ok, data = emby.get_lines()
    if ok:
        lines = [SimpleNamespace(id=int(l["id"]), name=l["name"], pro=bool(l.get("pro"))) for l in data.get("lines") or []]
        if lines:
            _cache.update(at=time.time(), lines=lines, default=int(data.get("defaultLineId") or lines[0].id))
            return
    if _cache["lines"] is None:
        LOGGER.warning(f"读取 sidecar 线路失败，暂用 config.json 中的线路：{data}")
        _cache.update(at=time.time(), lines=list(_config_lines), default=_config_default_line)


def current_lines():
    _refresh()
    return _cache["lines"]


def current_default_line() -> int:
    _refresh()
    return _cache["default"]


def invalidate_lines():
    _cache["at"] = 0.0
